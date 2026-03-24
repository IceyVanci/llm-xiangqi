"""
棋子3D渲染器

使用圆柱体+顶部文字纹理渲染棋子
"""

import pyglet
from pyglet import gl
from pyglet.text import Label

# 棋子文字映射（大写=红方，小写=黑方）
PIECE_LABELS = {
    'K': '帥', 'k': '將',
    'A': '仕', 'a': '士',
    'B': '相', 'b': '象',
    'N': '馬', 'n': '馬',
    'R': '車', 'r': '車',
    'C': '炮', 'c': '炮',
    'P': '兵', 'p': '卒',
}

# 棋子颜色
RED_COLOR = (0.9, 0.2, 0.2, 1.0)  # 红色
BLACK_COLOR = (0.15, 0.15, 0.15, 1.0)  # 黑色
WOOD_COLOR = (0.85, 0.65, 0.4, 1.0)  # 木质颜色
LABEL_RED = (1.0, 0.0, 0.0, 1.0)  # 红色标签
LABEL_BLACK = (0.0, 0.0, 0.0, 1.0)  # 黑色标签


class PieceRenderer:
    """棋子3D渲染器"""

    def __init__(self, radius=0.35, height=0.15):
        """初始化棋子渲染器

        Args:
            radius: 棋子半径
            height: 棋子高度
        """
        self.radius = radius
        self.height = height
        self._pieces = {}  # 缓存渲染好的棋子批处理
        self.batch = pyglet.graphics.Batch()

        # 创建字体
        try:
            self.font_size = 24
            self.font = 'SimHei'
        except:
            self.font = None
            self.font_size = 18

    def get_piece_color(self, piece_char):
        """获取棋子颜色"""
        if piece_char.isupper():
            return RED_COLOR, LABEL_RED
        return BLACK_COLOR, LABEL_BLACK

    def render_piece(self, x, z, piece_char, batch=None):
        """渲染单个棋子

        Args:
            x, z: 棋子位置（3D坐标）
            piece_char: 棋子字符
            batch: 批处理对象
        """
        if batch is None:
            batch = self.batch

        side_color, label_color = self.get_piece_color(piece_char)
        label_text = PIECE_LABELS.get(piece_char, '?')

        # 绘制底座圆柱（木质色）
        self._draw_cylinder(
            x, 0, z,
            self.radius + 0.02, self.height * 0.3,
            WOOD_COLOR, batch
        )

        # 绘制主体圆柱（红/黑色）
        self._draw_cylinder(
            x, self.height * 0.15, z,
            self.radius, self.height * 0.7,
            side_color, batch
        )

        # 绘制顶部圆盘（红色或黑色）
        self._draw_disk(
            x, self.height * 0.85, z,
            self.radius,
            side_color, batch
        )

        # 绘制标签（使用 billboard 模式确保始终面向相机）
        self._draw_label(
            x, self.height * 0.9, z,
            label_text, label_color, batch
        )

    def _draw_cylinder(self, x, y, z, radius, height, color, batch):
        """绘制圆柱体（使用多边形模拟）"""
        segments = 16
        height_half = height / 2

        # 侧面
        vertices = []
        for i in range(segments):
            angle1 = (i / segments) * 2 * 3.14159
            angle2 = ((i + 1) / segments) * 2 * 3.14159

            x1 = x + radius * math.cos(angle1)
            z1 = z + radius * math.sin(angle1)
            x2 = x + radius * math.cos(angle2)
            z2 = z + radius * math.sin(angle2)

            vertices.extend([x1, y - height_half, z1])
            vertices.extend([x2, y - height_half, z2])
            vertices.extend([x2, y + height_half, z2])
            vertices.extend([x1, y - height_half, z1])
            vertices.extend([x2, y + height_half, z2])
            vertices.extend([x1, y + height_half, z1])

        if vertices:
            batch.add(len(vertices) // 3, gl.GL_TRIANGLES, None,
                     ('v3f', vertices),
                     ('c4f', color * (len(vertices) // 3)))

    def _draw_disk(self, x, y, z, radius, color, batch):
        """绘制圆盘"""
        segments = 16
        vertices = [x, y, z]  # 中心点

        for i in range(segments):
            angle = (i / segments) * 2 * 3.14159
            vertices.extend([
                x + radius * math.cos(angle),
                y,
                z + radius * math.sin(angle)
            ])

        indices = []
        for i in range(1, segments + 1):
            indices.extend([0, i, (i % segments) + 1])

        if len(vertices) >= 9:
            vertices_list = vertices
            colors = [color[0], color[1], color[2], color[3]] * (segments + 1)
            batch.add_indexed(len(vertices_list) // 3, gl.GL_TRIANGLES, None,
                           indices, ('v3f', vertices_list), ('c4f', colors))

    def _draw_label(self, x, y, z, text, color, batch):
        """绘制文字标签"""
        label = Label(
            text,
            font_name=self.font,
            font_size=self.font_size,
            color=(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255), int(color[3] * 255)),
            x=int(x * 100),  # 转换到窗口坐标（示例）
            y=int(y * 100),
            anchor_x='center',
            anchor_y='center'
        )
        return label


import math
