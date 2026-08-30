"""Bicubic and Bilinear interpolation algorithms for surface heightmaps."""

import math
from typing import List, Union
from PyQt6.QtCore import QRectF, QAbstractTableModel, Qt


class Interpolation:
    @staticmethod
    def cubicInterpolate(p: List[float], x: float) -> float:
        """1D Catmull-Rom cubic interpolation across 4 sample points."""
        return p[1] + 0.5 * x * (
            p[2] - p[0] + x * (
                2.0 * p[0] - 5.0 * p[1] + 4.0 * p[2] - p[3] +
                x * (3.0 * (p[1] - p[2]) + p[3] - p[0])
            )
        )

    @staticmethod
    def bicubicInterpolatePoints(p: List[List[float]], x: float, y: float) -> float:
        """2D Bicubic interpolation across a 4x4 matrix of sample points."""
        arr = [
            Interpolation.cubicInterpolate(p[0], x),
            Interpolation.cubicInterpolate(p[1], x),
            Interpolation.cubicInterpolate(p[2], x),
            Interpolation.cubicInterpolate(p[3], x),
        ]
        return Interpolation.cubicInterpolate(arr, y)

    @staticmethod
    def bicubicInterpolate(border_rect: QRectF, base_points: Union[QAbstractTableModel, List[List[float]]],
                           x: float, y: float) -> float:
        """Interpolates Z elevation at coordinate (x, y) given a grid within border_rect."""
        if isinstance(base_points, QAbstractTableModel):
            cols = base_points.columnCount()
            rows = base_points.rowCount()
            def get_val(r: int, c: int) -> float:
                v = base_points.data(base_points.index(r, c), Qt.ItemDataRole.UserRole)
                try:
                    return float(v) if v is not None and not math.isnan(float(v)) else 0.0
                except (ValueError, TypeError):
                    return 0.0
        else:
            rows = len(base_points)
            cols = len(base_points[0]) if rows > 0 else 0
            def get_val(r: int, c: int) -> float:
                v = base_points[r][c]
                return float(v) if not math.isnan(v) else 0.0

        if cols < 2 or rows < 2:
            return 0.0

        grid_step_x = border_rect.width() / (cols - 1) if cols > 1 else 0.0
        grid_step_y = border_rect.height() / (rows - 1) if rows > 1 else 0.0

        if grid_step_x == 0 or grid_step_y == 0:
            return 0.0

        rel_x = x - border_rect.x()
        rel_y = y - border_rect.y()

        ix = int(rel_x / grid_step_x)
        iy = int(rel_y / grid_step_y)

        ix = max(0, min(ix, cols - 2))
        iy = max(0, min(iy, rows - 2))

        # Sample 4x4 surrounding grid points
        p = [[0.0] * 4 for _ in range(4)]

        # Row 0
        r0 = iy - 1 if iy > 0 else iy
        p[0][0] = get_val(r0, ix - 1 if ix > 0 else ix)
        p[0][1] = get_val(r0, ix)
        p[0][2] = get_val(r0, ix + 1)
        p[0][3] = get_val(r0, ix + 2 if ix < cols - 2 else ix + 1)

        # Row 1
        r1 = iy
        p[1][0] = get_val(r1, ix - 1 if ix > 0 else ix)
        p[1][1] = get_val(r1, ix)
        p[1][2] = get_val(r1, ix + 1)
        p[1][3] = get_val(r1, ix + 2 if ix < cols - 2 else ix + 1)

        # Row 2
        r2 = iy + 1
        p[2][0] = get_val(r2, ix - 1 if ix > 0 else ix)
        p[2][1] = get_val(r2, ix)
        p[2][2] = get_val(r2, ix + 1)
        p[2][3] = get_val(r2, ix + 2 if ix < cols - 2 else ix + 1)

        # Row 3
        r3 = iy + 2 if iy < rows - 2 else iy + 1
        p[3][0] = get_val(r3, ix - 1 if ix > 0 else ix)
        p[3][1] = get_val(r3, ix)
        p[3][2] = get_val(r3, ix + 1)
        p[3][3] = get_val(r3, ix + 2 if ix < cols - 2 else ix + 1)

        norm_x = rel_x / grid_step_x - ix
        norm_y = rel_y / grid_step_y - iy

        return Interpolation.bicubicInterpolatePoints(p, norm_x, norm_y)
