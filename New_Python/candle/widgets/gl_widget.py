"""3D OpenGL Viewport Widget for G-code and Machine Visualizer."""

import os
import math
from typing import List, Optional
from OpenGL.GL import *
from PyQt6.QtCore import Qt, QPointF, QTimer, QTime, QEasingCurve, pyqtSignal
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtOpenGL import QOpenGLShaderProgram, QOpenGLShader
from PyQt6.QtGui import (
    QSurfaceFormat, QVector3D, QMatrix4x4, QColor, QPainter
)
from ..drawers.shader_drawable import ShaderDrawable
from .overlay import Overlay


ZOOM_STEP = 1.1


class GLWidget(QOpenGLWidget):
    cameraChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.m_shaderProgram: Optional[QOpenGLShaderProgram] = None
        self.m_shaderDrawables: List[ShaderDrawable] = []

        self.m_frames: int = 0
        self.m_fps: int = 0
        self.m_targetFps: int = 60
        self.m_vsync: bool = False
        self.m_msaa: bool = False
        self.m_antialiasing: bool = True
        self.m_zBuffer: bool = True
        self.m_perspective: bool = False

        self.m_rot: QPointF = QPointF(90.0, 0.0)
        self.m_rotAnimationTarget: QPointF = QPointF(90.0, 0.0)
        self.m_rotAnimationStart: QPointF = QPointF(90.0, 0.0)
        self.m_animateView: bool = False
        self.m_animationFrame: int = 0

        self.m_zoom: float = 1.0
        self.m_distance: float = 100.0
        self.m_windowSizeWorld: float = 100.0
        self.m_pan: QPointF = QPointF(0.0, 0.0)
        self.m_lookAt: QVector3D = QVector3D(0, 0, 0)
        self.m_lastMousePos: QPointF = QPointF()

        self.m_projectionMatrix: QMatrix4x4 = QMatrix4x4()
        self.m_viewMatrix: QMatrix4x4 = QMatrix4x4()

        # Bounds & state info for Overlay HUD
        self.m_viewLowerBounds: QVector3D = QVector3D()
        self.m_viewUpperBounds: QVector3D = QVector3D()
        self.m_viewRanges: QVector3D = QVector3D()
        self.m_modelLowerBounds: QVector3D = QVector3D()
        self.m_modelUpperBounds: QVector3D = QVector3D()
        self.m_modelRanges: QVector3D = QVector3D()
        self.m_cursorPos: QVector3D = QVector3D()
        self.m_vertices: int = 0
        self.m_parserStatus: str = ""
        self.m_speedState: str = ""
        self.m_pinState: str = ""
        self.m_bufferState: str = ""
        self.m_updating: bool = False

        self.m_spendTime: QTime = QTime(0, 0, 0)
        self.m_estimatedTime: QTime = QTime(0, 0, 0)

        self.m_colorBackground: QColor = QColor(30, 30, 30)
        self.m_colorText: QColor = QColor(255, 255, 255)

        # Configure Surface Format
        fmt = QSurfaceFormat()
        fmt.setSamples(8)
        fmt.setSwapInterval(0)
        self.setFormat(fmt)

        self.m_overlay = Overlay(self)

        self.m_timerFPS = QTimer(self)
        self.m_timerFPS.timeout.connect(self._on_fps_timer)
        self.m_timerFPS.start(1000)

        self.m_timerAnimation = QTimer(self)
        self.m_timerAnimation.timeout.connect(self._on_animation_timer)

    def addDrawable(self, drawable: ShaderDrawable) -> None:
        self.m_shaderDrawables.append(drawable)

    def removeDrawable(self, drawable: ShaderDrawable) -> None:
        if drawable in self.m_shaderDrawables:
            self.m_shaderDrawables.remove(drawable)

    def initializeGL(self) -> None:
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_VERTEX_PROGRAM_POINT_SIZE)
        glEnable(GL_POINT_SMOOTH)
        glEnable(GL_LINE_SMOOTH)

        self.m_shaderProgram = QOpenGLShaderProgram(self)

        shaders_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "shaders")
        vshader_path = os.path.join(shaders_dir, "vshader.glsl")
        fshader_path = os.path.join(shaders_dir, "fshader.glsl")

        if os.path.exists(vshader_path) and os.path.exists(fshader_path):
            self.m_shaderProgram.addShaderFromSourceFile(QOpenGLShader.ShaderTypeBit.Vertex, vshader_path)
            self.m_shaderProgram.addShaderFromSourceFile(QOpenGLShader.ShaderTypeBit.Fragment, fshader_path)
            self.m_shaderProgram.link()

        self.updateProjection()
        self.updateView()

    def resizeGL(self, w: int, h: int) -> None:
        glViewport(0, 0, w, h)
        self.m_overlay.setGeometry(0, 0, w, h)
        self.updateProjection()
        self.updateView()

    def paintGL(self) -> None:
        self.m_frames += 1

        bg = self.m_colorBackground
        glClearColor(bg.redF(), bg.greenF(), bg.blueF(), 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if not self.m_shaderProgram or not self.m_shaderProgram.isLinked():
            return

        if self.m_zBuffer:
            glEnable(GL_DEPTH_TEST)
        else:
            glDisable(GL_DEPTH_TEST)

        self.m_shaderProgram.bind()
        self.m_shaderProgram.setUniformValue("p_matrix", self.m_projectionMatrix)
        self.m_shaderProgram.setUniformValue("v_matrix", self.m_viewMatrix)

        total_verts = 0
        for drawable in self.m_shaderDrawables:
            if drawable.needsUpdateGeometry():
                drawable.updateGeometry(self.m_shaderProgram)
            if drawable.visible():
                self.m_shaderProgram.setUniformValue("m_matrix", drawable.modelMatrix())
                drawable.draw(self.m_shaderProgram)
                total_verts += drawable.getVertexCount()

        self.m_vertices = total_verts
        self.m_shaderProgram.release()

    def updateProjection(self) -> None:
        w = max(1, self.width())
        h = max(1, self.height())
        aspect = float(w) / float(h)

        self.m_projectionMatrix.setToIdentity()

        if self.m_perspective:
            z_near = 0.1
            z_far = 5000.0
            fov_rad = math.radians(45.0)
            fh = math.tan(fov_rad / 2.0) * z_near
            fw = fh * aspect
            self.m_projectionMatrix.frustum(-fw, fw, -fh, fh, z_near, z_far)
        else:
            hw = (self.m_distance * 0.25) * aspect / self.m_zoom
            hh = (self.m_distance * 0.25) / self.m_zoom
            self.m_windowSizeWorld = hh * 2.0
            self.m_projectionMatrix.ortho(-hw, hw, -hh, hh, -2000.0, 2000.0)

    def updateView(self) -> None:
        self.m_viewMatrix.setToIdentity()

        if self.m_perspective:
            self.m_viewMatrix.translate(0, 0, -self.m_distance / self.m_zoom)
        else:
            self.m_viewMatrix.translate(0, 0, 0)

        self.m_viewMatrix.translate(self.m_pan.x(), self.m_pan.y(), 0)
        self.m_viewMatrix.rotate(self.m_rot.x() - 90.0, 1.0, 0.0, 0.0)
        self.m_viewMatrix.rotate(self.m_rot.y(), 0.0, 0.0, 1.0)
        self.m_viewMatrix.translate(-self.m_lookAt.x(), -self.m_lookAt.y(), -self.m_lookAt.z())

        self.update()
        self.cameraChanged.emit()

    def fitDrawable(self, drawable: Optional[ShaderDrawable] = None) -> None:
        self.stopViewAnimation()

        if drawable is not None:
            self.m_viewLowerBounds = QVector3D(drawable.getViewLowerBounds())
            self.m_viewUpperBounds = QVector3D(drawable.getViewUpperBounds())
            self.m_viewRanges = drawable.getViewRanges()

            self.m_modelLowerBounds = QVector3D(drawable.getModelLowerBounds())
            self.m_modelUpperBounds = QVector3D(drawable.getModelUpperBounds())
            self.m_modelRanges = drawable.getModelRanges()

            w = max(1, self.width())
            h = max(1, self.height())
            aspect = float(w) / float(h)

            a = (self.m_viewRanges.y() / 2.0 / 0.25 * 1.3) + self.m_viewRanges.z() / 2.0
            b = (self.m_viewRanges.x() / 2.0 / 0.25 * 1.3) / aspect + self.m_viewRanges.z() / 2.0
            self.m_distance = max(a, b)
            if self.m_distance <= 0:
                self.m_distance = 200.0

            self.m_lookAt = QVector3D(
                (self.m_viewUpperBounds.x() + self.m_viewLowerBounds.x()) / 2.0,
                (self.m_viewUpperBounds.y() + self.m_viewLowerBounds.y()) / 2.0,
                (self.m_viewUpperBounds.z() + self.m_viewLowerBounds.z()) / 2.0
            )
        else:
            self.m_distance = 200.0
            self.m_lookAt = QVector3D(0, 0, 0)
            self.m_viewLowerBounds = QVector3D()
            self.m_viewUpperBounds = QVector3D()
            self.m_viewRanges = QVector3D()
            self.m_modelLowerBounds = QVector3D()
            self.m_modelUpperBounds = QVector3D()
            self.m_modelRanges = QVector3D()

        self.m_pan = QPointF(0.0, 0.0)
        self.m_zoom = 1.0

        self.updateProjection()
        self.updateView()

    def setPresetView(self, rx: float, ry: float) -> None:
        self.m_rotAnimationStart = QPointF(self.m_rot)
        self.m_rotAnimationTarget = QPointF(rx, ry)
        self.m_animationFrame = 0
        self.m_animateView = True
        self.m_timerAnimation.start(16)

    def topView(self) -> None: self.setPresetView(0.0, 0.0)
    def frontView(self) -> None: self.setPresetView(90.0, 0.0)
    def leftView(self) -> None: self.setPresetView(90.0, 90.0)
    def isometricView(self) -> None: self.setPresetView(45.0, -45.0)

    def stopViewAnimation(self) -> None:
        self.m_animateView = False
        self.m_timerAnimation.stop()

    def _on_animation_timer(self) -> None:
        t = float(self.m_animationFrame) / max(1.0, (self.m_fps or 60) * 0.2)
        self.m_animationFrame += 1

        if t >= 1.0:
            self.m_rot = QPointF(self.m_rotAnimationTarget)
            self.stopViewAnimation()
        else:
            ec = QEasingCurve(QEasingCurve.Type.OutExpo)
            val = ec.valueForProgress(t)
            self.m_rot = self.m_rotAnimationStart + (self.m_rotAnimationTarget - self.m_rotAnimationStart) * val

        self.updateView()

    def _on_fps_timer(self) -> None:
        self.m_fps = self.m_frames
        self.m_frames = 0
        self.m_overlay.update()

    # Mouse & Touch interactions
    def mousePressEvent(self, event) -> None:
        self.stopViewAnimation()
        self.m_lastMousePos = QPointF(event.position())

    def mouseMoveEvent(self, event) -> None:
        cur_pos = QPointF(event.position())
        dx = cur_pos.x() - self.m_lastMousePos.x()
        dy = cur_pos.y() - self.m_lastMousePos.y()

        buttons = event.buttons()
        if buttons & Qt.MouseButton.LeftButton:
            # Rotate
            self.m_rot.setX(self.m_rot.x() + dy * 0.5)
            self.m_rot.setY(self.m_rot.y() + dx * 0.5)
            self.updateView()
        elif (buttons & Qt.MouseButton.RightButton) or (buttons & Qt.MouseButton.MiddleButton):
            # Pan
            pan_scale = (self.m_distance * 0.5 / self.m_zoom) / max(1, self.height())
            self.m_pan.setX(self.m_pan.x() + dx * pan_scale)
            self.m_pan.setY(self.m_pan.y() - dy * pan_scale)
            self.updateView()

        self.m_lastMousePos = cur_pos

    def wheelEvent(self, event) -> None:
        degrees = event.angleDelta().y() / 8.0
        steps = degrees / 15.0

        if steps > 0:
            self.m_zoom *= ZOOM_STEP ** steps
        elif steps < 0:
            self.m_zoom /= ZOOM_STEP ** (-steps)

        self.m_zoom = max(0.01, min(100.0, self.m_zoom))
        self.updateProjection()
        self.updateView()

    def mouseDoubleClickEvent(self, event) -> None:
        self.m_pan = QPointF(0, 0)
        self.updateView()

    # Getters & setters
    def perspective(self) -> bool: return self.m_perspective
    def setPerspective(self, p: bool): self.m_perspective = p; self.updateProjection(); self.updateView()

    def zBuffer(self) -> bool: return self.m_zBuffer
    def setZBuffer(self, z: bool): self.m_zBuffer = z; self.update()

    def setCursorPos(self, pos: QVector3D): self.m_cursorPos = QVector3D(pos); self.m_overlay.update()
    def setParserStatus(self, s: str): self.m_parserStatus = s; self.m_overlay.update()
    def setSpeedState(self, s: str): self.m_speedState = s; self.m_overlay.update()
    def setPinState(self, s: str): self.m_pinState = s; self.m_overlay.update()
    def setBufferState(self, s: str): self.m_bufferState = s; self.m_overlay.update()
    def setUpdating(self, u: bool): self.m_updating = u; self.m_overlay.update()

    def setTimes(self, elapsed: QTime, est: QTime):
        self.m_spendTime = elapsed
        self.m_estimatedTime = est
        self.m_overlay.update()

    def setColors(self, bg: QColor, text: QColor):
        self.m_colorBackground = bg
        self.m_colorText = text
        self.update()
        self.m_overlay.update()
