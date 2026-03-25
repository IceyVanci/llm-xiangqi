"""
棋子3D渲染器

使用Pillow生成高清动态纹理，通过原始OpenGL调用创建纹理
"""

import math
import io
import pyglet
from pyglet import gl
from PIL import Image, ImageDraw, ImageFont

PIECE_LABELS = {
    "K": "帥",
    "k": "將",
    "A": "仕",
    "a": "士",
    "B": "相",
    "b": "象",
    "N": "馬",
    "n": "馬",
    "R": "車",
    "r": "車",
    "C": "炮",
    "c": "炮",
    "P": "兵",
    "p": "卒",
}


class PieceRenderer:
    """棋子3D渲染器"""

    def __init__(self, radius=0.4, height=0.15):
        self.radius = radius
        self.height = height
        self._textures = {}
        self._texture_objs = {}

    def init_gl(self):
        """初始化OpenGL纹理"""
        if self._textures:
            return

        font = None
        for font_name in [
            "msyh.ttc",
            "simhei.ttf",
            "simsun.ttc",
            "C:/Windows/Fonts/simhei.ttf",
        ]:
            try:
                font = ImageFont.truetype(font_name, 160)
                break
            except IOError:
                continue
        if font is None:
            font = ImageFont.load_default()

        for char, label in PIECE_LABELS.items():
            is_red = char.isupper()
            color = (220, 40, 40, 255) if is_red else (40, 40, 40, 255)

            img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            try:
                bbox = draw.textbbox((0, 0), label, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                x = (256 - w) / 2
                y = (256 - h) / 2 - bbox[1]
            except AttributeError:
                x, y = 48, 48

            draw.text((x, y), label, font=font, fill=color)

            # 黑色棋子旋转180度（因为黑方棋子是倒过来看的）
            if not is_red:
                img = img.rotate(180)
            raw_data = img.tobytes()

            # 生成纹理
            texture_ids = (pyglet.gl.GLuint * 1)()
            gl.glGenTextures(1, texture_ids)
            texture_id = texture_ids[0]

            gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
            gl.glTexImage2D(
                gl.GL_TEXTURE_2D,
                0,
                gl.GL_RGBA,
                256,
                256,
                0,
                gl.GL_RGBA,
                gl.GL_UNSIGNED_BYTE,
                raw_data,
            )
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(
                gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE
            )
            gl.glTexParameteri(
                gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE
            )

            self._textures[char] = texture_id
            self._texture_objs[char] = texture_id  # 保持引用

    def render_piece(self, piece_char):
        """渲染单个棋子"""
        is_red = piece_char.isupper()
        base_color = (0.85, 0.15, 0.1) if is_red else (0.1, 0.1, 0.1)
        top_color = (0.95, 0.25, 0.15) if is_red else (0.18, 0.18, 0.18)
        wood_color = (0.7, 0.5, 0.25)

        self._draw_cylinder_3d(self.radius + 0.02, self.height * 0.3, wood_color, 0)
        self._draw_cylinder_3d(
            self.radius, self.height * 0.7, base_color, self.height * 0.15
        )

        texture_id = self._textures.get(piece_char) if self._textures else None
        self._draw_textured_disk_top(
            self.radius, top_color, self.height * 0.85, texture_id
        )

    def _draw_cylinder_3d(self, radius, height, color, y_offset):
        segments = 24
        h_half = height / 2

        gl.glPushMatrix()
        gl.glTranslatef(0, y_offset, 0)
        gl.glBegin(gl.GL_QUADS)
        for i in range(segments):
            a1 = (i / segments) * 2 * math.pi
            a2 = ((i + 1) / segments) * 2 * math.pi
            x1, z1 = radius * math.cos(a1), radius * math.sin(a1)
            x2, z2 = radius * math.cos(a2), radius * math.sin(a2)

            shade = 0.7 + 0.3 * math.cos(a1)
            gl.glColor4f(color[0] * shade, color[1] * shade, color[2] * shade, 1.0)

            gl.glNormal3f(math.cos(a1), 0, math.sin(a1))
            gl.glVertex3f(x1, -h_half, z1)
            gl.glNormal3f(math.cos(a2), 0, math.sin(a2))
            gl.glVertex3f(x2, -h_half, z2)
            gl.glVertex3f(x2, h_half, z2)
            gl.glNormal3f(math.cos(a1), 0, math.sin(a1))
            gl.glVertex3f(x1, h_half, z1)
        gl.glEnd()
        gl.glPopMatrix()

    def _draw_textured_disk_top(self, radius, color, y_offset, texture_id):
        segments = 24
        gl.glPushMatrix()
        gl.glTranslatef(0, y_offset, 0)

        # 绘制底部圆盘
        gl.glColor4f(*color, 1.0)
        gl.glNormal3f(0, 1, 0)
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glVertex3f(0, 0, 0)
        for i in range(segments + 1):
            a = (i / segments) * 2 * math.pi
            gl.glVertex3f(radius * math.cos(a), 0, radius * math.sin(a))
        gl.glEnd()

        # 抬高0.005绘制纹理四边形，避免深度冲突
        if texture_id:
            gl.glTranslatef(0, 0.005, 0)
            gl.glEnable(gl.GL_TEXTURE_2D)
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
            gl.glEnable(gl.GL_BLEND)
            gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

            gl.glColor4f(1.0, 1.0, 1.0, 1.0)
            gl.glBegin(gl.GL_QUADS)
            gl.glNormal3f(0, 1, 0)
            size = radius * 0.8
            gl.glTexCoord2f(0.0, 0.0)
            gl.glVertex3f(-size, 0, -size)
            gl.glTexCoord2f(1.0, 0.0)
            gl.glVertex3f(size, 0, -size)
            gl.glTexCoord2f(1.0, 1.0)
            gl.glVertex3f(size, 0, size)
            gl.glTexCoord2f(0.0, 1.0)
            gl.glVertex3f(-size, 0, size)
            gl.glEnd()

            gl.glDisable(gl.GL_BLEND)
            gl.glDisable(gl.GL_TEXTURE_2D)

        gl.glPopMatrix()
