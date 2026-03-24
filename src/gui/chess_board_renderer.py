"""
棋盘3D渲染器

渲染10x9格子的木质棋盘，包含楚河汉界
"""

import math
import pyglet
from pyglet import gl
from ctypes import c_float

BOARD_COLOR = (0.55, 0.35, 0.15, 1.0)
BOARD_LIGHT = (0.7, 0.5, 0.25, 1.0)
BOARD_DARK = (0.4, 0.25, 0.1, 1.0)
LINE_COLOR = (0.1, 0.05, 0.0, 1.0)
RIVER_COLOR = (0.65, 0.55, 0.4, 1.0)
FRAME_COLOR = (0.3, 0.18, 0.08, 1.0)


class ChessBoardRenderer:
    """棋盘3D渲染器"""

    def __init__(self):
        """初始化棋盘渲染器"""
        self.board_width = 9.0
        self.board_height = 10.0
        self.cell_size = 1.0
        self.board_thickness = 0.2
        self.frame_width = 0.3

    def render(self):
        """渲染棋盘"""
        self._draw_board_base()
        self._draw_board_frame()
        self._draw_grid_lines()
        self._draw_river()
        self._draw_position_markers()

    def _draw_board_base(self):
        """绘制棋盘底板"""
        w, h = self.board_width, self.board_height
        t = self.board_thickness
        fw = self.frame_width

        gl.glColor4f(*BOARD_COLOR)

        gl.glBegin(gl.GL_QUADS)
        gl.glNormal3f(0, 1, 0)
        gl.glVertex3f(-fw, t, -fw)
        gl.glVertex3f(w + fw, t, -fw)
        gl.glVertex3f(w + fw, t, h + fw)
        gl.glVertex3f(-fw, t, h + fw)
        gl.glEnd()

        gl.glColor4f(*BOARD_DARK)

        gl.glBegin(gl.GL_QUADS)
        gl.glNormal3f(0, 0, 1)
        gl.glVertex3f(-fw, 0, h + fw)
        gl.glVertex3f(w + fw, 0, h + fw)
        gl.glVertex3f(w + fw, t, h + fw)
        gl.glVertex3f(-fw, t, h + fw)

        gl.glNormal3f(0, 0, -1)
        gl.glVertex3f(-fw, 0, -fw)
        gl.glVertex3f(-fw, t, -fw)
        gl.glVertex3f(w + fw, t, -fw)
        gl.glVertex3f(w + fw, 0, -fw)

        gl.glNormal3f(-1, 0, 0)
        gl.glVertex3f(w + fw, 0, -fw)
        gl.glVertex3f(w + fw, t, -fw)
        gl.glVertex3f(w + fw, t, h + fw)
        gl.glVertex3f(w + fw, 0, h + fw)

        gl.glNormal3f(1, 0, 0)
        gl.glVertex3f(-fw, 0, -fw)
        gl.glVertex3f(-fw, 0, h + fw)
        gl.glVertex3f(-fw, t, h + fw)
        gl.glVertex3f(-fw, t, -fw)

        gl.glNormal3f(0, -1, 0)
        gl.glVertex3f(-fw, 0, -fw)
        gl.glVertex3f(w + fw, 0, -fw)
        gl.glVertex3f(w + fw, 0, h + fw)
        gl.glVertex3f(-fw, 0, h + fw)
        gl.glEnd()

    def _draw_board_frame(self):
        """绘制棋盘边框装饰"""
        w, h = self.board_width, self.board_height
        t = self.board_thickness
        y = t + 0.001

        gl.glLineWidth(3.0)
        gl.glColor4f(*LINE_COLOR)

        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex3f(0, y, 0)
        gl.glVertex3f(w, y, 0)
        gl.glVertex3f(w, y, h)
        gl.glVertex3f(0, y, h)
        gl.glEnd()

        gl.glLineWidth(1.5)
        inner = 0.1
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex3f(-inner, y, -inner)
        gl.glVertex3f(w + inner, y, -inner)
        gl.glVertex3f(w + inner, y, h + inner)
        gl.glVertex3f(-inner, y, h + inner)
        gl.glEnd()

    def _draw_grid_lines(self):
        """绘制棋盘网格线"""
        w, h = self.board_width, self.board_height
        y = self.board_thickness + 0.002

        gl.glLineWidth(1.0)
        gl.glColor4f(*LINE_COLOR)

        gl.glBegin(gl.GL_LINES)
        for col in range(10):
            x = float(col)
            gl.glVertex3f(x, y, 0)
            gl.glVertex3f(x, y, 4.5)
            gl.glVertex3f(x, y, 5.5)
            gl.glVertex3f(x, y, h)

        for row in range(10):
            z = float(row)
            gl.glVertex3f(0, y, z)
            gl.glVertex3f(w, y, z)
        gl.glEnd()

        gl.glBegin(gl.GL_LINES)
        for row in [0, 2, 7, 9]:
            gl.glVertex3f(3, y, row)
            gl.glVertex3f(5, y, row + 2 if row in [0, 7] else row - 2)
            gl.glVertex3f(5, y, row)
            gl.glVertex3f(3, y, row + 2 if row in [0, 7] else row - 2)
        gl.glEnd()

    def _draw_river(self):
        """绘制楚河汉界"""
        y = self.board_thickness + 0.003

        gl.glColor4f(*RIVER_COLOR)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex3f(0, y, 4.5)
        gl.glVertex3f(self.board_width, y, 4.5)
        gl.glVertex3f(self.board_width, y, 5.5)
        gl.glVertex3f(0, y, 5.5)
        gl.glEnd()

        gl.glColor4f(0.2, 0.1, 0.05, 1.0)
        gl.glLineWidth(2.0)

        for text, x_offset in [("楚河", 1.5), ("汉界", 6.0)]:
            self._draw_river_text(text, x_offset, y)

    def _draw_river_text(self, text, x, y):
        """绘制楚河汉界文字"""
        gl.glBegin(gl.GL_LINES)
        for char_idx, char in enumerate(text):
            cx = x + char_idx * 1.5
            cz = 5.0

            if char == "楚":
                gl.glVertex3f(cx - 0.3, y, cz - 0.3)
                gl.glVertex3f(cx + 0.3, y, cz + 0.3)
                gl.glVertex3f(cx - 0.3, y, cz + 0.3)
                gl.glVertex3f(cx + 0.3, y, cz - 0.3)
                gl.glVertex3f(cx, y, cz - 0.4)
                gl.glVertex3f(cx, y, cz + 0.4)
            elif char == "河":
                gl.glVertex3f(cx - 0.3, y, cz)
                gl.glVertex3f(cx + 0.3, y, cz)
                gl.glVertex3f(cx, y, cz - 0.3)
                gl.glVertex3f(cx, y, cz + 0.3)
                gl.glVertex3f(cx - 0.2, y, cz - 0.2)
                gl.glVertex3f(cx + 0.2, y, cz - 0.2)
            elif char == "汉":
                gl.glVertex3f(cx - 0.3, y, cz - 0.3)
                gl.glVertex3f(cx + 0.3, y, cz - 0.3)
                gl.glVertex3f(cx, y, cz - 0.3)
                gl.glVertex3f(cx, y, cz + 0.3)
                gl.glVertex3f(cx - 0.2, y, cz + 0.3)
                gl.glVertex3f(cx + 0.2, y, cz + 0.3)
            elif char == "界":
                gl.glVertex3f(cx - 0.3, y, cz - 0.3)
                gl.glVertex3f(cx + 0.3, y, cz - 0.3)
                gl.glVertex3f(cx - 0.3, y, cz + 0.3)
                gl.glVertex3f(cx + 0.3, y, cz + 0.3)
                gl.glVertex3f(cx, y, cz - 0.4)
                gl.glVertex3f(cx, y, cz + 0.4)
        gl.glEnd()

    def _draw_position_markers(self):
        """绘制炮和兵的定位标记"""
        y = self.board_thickness + 0.003

        cannon_spots = [(1, 2), (7, 2), (1, 7), (7, 7)]
        pawn_spots = [
            (0, 3),
            (2, 3),
            (4, 3),
            (6, 3),
            (8, 3),
            (0, 6),
            (2, 6),
            (4, 6),
            (6, 6),
            (8, 6),
        ]

        gl.glColor4f(*LINE_COLOR)
        gl.glLineWidth(1.0)

        for col, row in cannon_spots + pawn_spots:
            self._draw_corner_marks(col, row, y)

    def _draw_corner_marks(self, col, row, y):
        """绘制交叉点角落标记"""
        size = 0.08
        gap = 0.05

        gl.glBegin(gl.GL_LINES)
        if col > 0:
            gl.glVertex3f(col - gap - size, y, row - gap)
            gl.glVertex3f(col - gap, y, row - gap)
            gl.glVertex3f(col - gap, y, row - gap - size)
            gl.glVertex3f(col - gap, y, row - gap)

            gl.glVertex3f(col - gap - size, y, row + gap)
            gl.glVertex3f(col - gap, y, row + gap)
            gl.glVertex3f(col - gap, y, row + gap + size)
            gl.glVertex3f(col - gap, y, row + gap)

        if col < 9:
            gl.glVertex3f(col + gap + size, y, row - gap)
            gl.glVertex3f(col + gap, y, row - gap)
            gl.glVertex3f(col + gap, y, row - gap - size)
            gl.glVertex3f(col + gap, y, row - gap)

            gl.glVertex3f(col + gap + size, y, row + gap)
            gl.glVertex3f(col + gap, y, row + gap)
            gl.glVertex3f(col + gap, y, row + gap + size)
            gl.glVertex3f(col + gap, y, row + gap)
        gl.glEnd()
