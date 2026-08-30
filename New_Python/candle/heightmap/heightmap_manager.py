"""Heightmap Manager - handles probing cycles, .map file IO, and G-code Z-offset transformation."""

import math
from typing import List, Tuple, Optional
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QVector3D
from .interpolation import Interpolation
from .heightmap_model import HeightMapTableModel
from ..parser.line_segment import LineSegment
from ..models.gcode_table_model import GCodeItem


class HeightMapData:
    def __init__(self):
        self.borderRect: QRectF = QRectF(0, 0, 100, 100)
        self.origin: QVector3D = QVector3D(0, 0, 0)
        self.gridX: int = 5
        self.gridY: int = 5
        self.zBottom: float = -2.0
        self.zTop: float = 2.0
        self.probeFeed: float = 20.0
        self.interpolationType: int = 0
        self.interpolationStepX: float = 2.0
        self.interpolationStepY: float = 2.0
        self.gridValues: List[List[float]] = []


class HeightMapManager:
    @staticmethod
    def generateProbeProgram(border_rect: QRectF, grid_x: int, grid_y: int,
                             z_top: float, z_bottom: float, probe_feed: float,
                             origin_x: float, origin_y: float) -> List[str]:
        """Generates G-code routine for heightmap probing grid."""
        lines: List[str] = []
        lines.append(f"G21G90F{probe_feed:.1f}")
        lines.append(f"G0X{origin_x:.3f}Y{origin_y:.3f}")
        lines.append(f"G0Z{z_top:.3f}")
        lines.append(f"G38.2Z{z_bottom:.3f}")
        lines.append(f"G0Z{z_top:.3f}")

        grid_step_x = border_rect.width() / (grid_x - 1) if grid_x > 1 else 0.0
        grid_step_y = border_rect.height() / (grid_y - 1) if grid_y > 1 else 0.0

        for i in range(grid_y):
            y = border_rect.top() + grid_step_y * i
            for j in range(grid_x):
                x = border_rect.left() + grid_step_x * (grid_x - 1 - j if (i % 2) else j)
                lines.append(f"G0X{x:.3f}Y{y:.3f}")
                lines.append(f"G38.2Z{z_bottom:.3f}")
                lines.append(f"G0Z{z_top:.3f}")

        return lines

    @staticmethod
    def saveHeightMap(file_path: str, data: HeightMapData, model: HeightMapTableModel) -> bool:
        """Saves heightmap to Candle v3 format."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("candle map v3\n")
                f.write(f"{data.borderRect.x():.3f};{data.borderRect.y():.3f};{data.borderRect.width():.3f};{data.borderRect.height():.3f}\n")
                f.write(f"{data.origin.x():.3f};{data.origin.y():.3f}\n")
                f.write(f"{data.gridX};{data.gridY};{data.zBottom:.3f};{data.zTop:.3f};{data.probeFeed:.1f}\n")
                f.write(f"{data.interpolationType};{data.interpolationStepX:.3f};{data.interpolationStepY:.3f}\n")

                for row in model.getRawData():
                    row_strs = ["nan" if math.isnan(val) else f"{val:.4f}" for val in row]
                    f.write(";".join(row_strs) + "\n")
            return True
        except Exception:
            return False

    @staticmethod
    def loadHeightMap(file_path: str) -> Optional[Tuple[HeightMapData, List[List[float]]]]:
        """Loads Candle v3 heightmap file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]

            if not lines:
                return None

            header = lines[0]
            if "candle map" not in header.lower():
                return None

            data = HeightMapData()
            # Line 1: borderRect (X; Y; Width; Height)
            p1 = lines[1].split(';')
            data.borderRect = QRectF(float(p1[0]), float(p1[1]), float(p1[2]), float(p1[3]))

            # Line 2: Origin (X; Y)
            p2 = lines[2].split(';')
            data.origin = QVector3D(float(p2[0]), float(p2[1]), 0.0)

            # Line 3: Grid (X; Y; ZBottom; ZTop; Feed)
            p3 = lines[3].split(';')
            data.gridX = int(p3[0])
            data.gridY = int(p3[1])
            data.zBottom = float(p3[2])
            data.zTop = float(p3[3])
            data.probeFeed = float(p3[4])

            # Line 4: Interpolation (Type; StepX; StepY)
            p4 = lines[4].split(';')
            data.interpolationType = int(p4[0])
            data.interpolationStepX = float(p4[1])
            data.interpolationStepY = float(p4[2])

            grid_values = []
            for line in lines[5:]:
                row = []
                for v in line.split(';'):
                    v_str = v.strip()
                    if not v_str or v_str.lower() == 'nan':
                        row.append(float('nan'))
                    else:
                        row.append(float(v_str))
                grid_values.append(row)

            return data, grid_values
        except Exception:
            return None

    @staticmethod
    def generateInterpolationMesh(border_rect: QRectF, model: HeightMapTableModel,
                                 step_x: float, step_y: float) -> List[List[float]]:
        """Generates high-density interpolated elevation matrix for visualizer surface rendering."""
        if model.columnCount() < 2 or model.rowCount() < 2:
            return []

        cols = max(2, int(border_rect.width() / (step_x or 2.0)) + 1)
        rows = max(2, int(border_rect.height() / (step_y or 2.0)) + 1)

        dx = border_rect.width() / (cols - 1) if cols > 1 else 0.0
        dy = border_rect.height() / (rows - 1) if rows > 1 else 0.0

        mesh: List[List[float]] = []
        for i in range(rows):
            row: List[float] = []
            y = border_rect.y() + i * dy
            for j in range(cols):
                x = border_rect.x() + j * dx
                z = Interpolation.bicubicInterpolate(border_rect, model, x, y)
                row.append(z)
            mesh.append(row)

        return mesh

    @staticmethod
    def subdivideSegment(segment: LineSegment, border_rect: QRectF,
                         interp_step_x: float, interp_step_y: float) -> List[LineSegment]:
        """Subdivides a linear segment into smaller subsegments matching the heightmap resolution."""
        vec = segment.getEnd() - segment.getStart()
        vec_len = vec.length()
        if math.isnan(vec_len) or vec_len == 0:
            return []

        step_x = border_rect.width() / max(1.0, interp_step_x - 1.0)
        step_y = border_rect.height() / max(1.0, interp_step_y - 1.0)

        vx = abs(vec.x())
        vy = abs(vec.y())

        if (vx / (vy or 1e-9)) < (step_x / (step_y or 1e-9)):
            length = step_y / (abs(vec.y()) / vec_len) if vec.y() != 0 else step_y
        else:
            length = step_x / (abs(vec.x()) / vec_len) if vec.x() != 0 else step_x

        length = abs(length)
        if math.isnan(length) or length == 0:
            return []

        count = int(vec_len / length)
        if count == 0:
            return []

        seg = vec.normalized() * length
        sub_segments: List[LineSegment] = []

        for i in range(count):
            line = segment.copy()
            line.setStart(segment.getStart() if i == 0 else sub_segments[i - 1].getEnd())
            line.setEnd(line.getStart() + seg)
            sub_segments.append(line)

        if sub_segments and sub_segments[-1].getEnd() != segment.getEnd():
            line = segment.copy()
            line.setStart(sub_segments[-1].getEnd())
            line.setEnd(segment.getEnd())
            sub_segments.append(line)

        return sub_segments
