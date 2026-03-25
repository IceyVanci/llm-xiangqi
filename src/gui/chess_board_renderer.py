"""
棋盘3D渲染器

使用Pillow生成全局2D棋盘纹理，通过原始OpenGL调用创建纹理
"""

import pyglet
from pyglet import gl
from PIL import Image, ImageDraw, ImageFont

BOARD_DARK = (0.35, 0.20, 0.08, 1.0)


class ChessBoardRenderer:
    """棋盘3D渲染器"""

    def __init__(self):
        # 棋盘尺寸: 9列(x 0-8), 10行(z 0-9)
        self.board_width = 8.0
        self.board_height = 9.0
        self.board_thickness = 0.2
        self.frame_width = 0.3
        self.texture_id = None
        self._texture_obj = None

    def init_gl(self):
        """初始化纹理"""
        if self.texture_id is None:
            self.texture_id = self._generate_board_texture()

    def _generate_board_texture(self):
        img_w, img_h = 2048, 2048
        img = Image.new("RGBA", (img_w, img_h), (200, 150, 90, 255))
        draw = ImageDraw.Draw(img)

        fw = self.frame_width
        w, h = self.board_width, self.board_height
        total_w, total_h = w + 2 * fw, h + 2 * fw

        def to_px(x, z):
            px = int((x + fw) / total_w * img_w)
            py = int((z + fw) / total_h * img_h)
            return px, py

        line_color = (40, 20, 10, 255)
        line_width = 4

        # 绘制外边框
        fx1, fy1 = to_px(-0.1, -0.1)
        fx2, fy2 = to_px(w + 0.1, h + 0.1)
        draw.rectangle([fx1, fy1, fx2, fy2], outline=line_color, width=8)

        # 绘制垂直网格线（楚河汉界断开）
        for col in range(9):
            x = float(col)
            draw.line([to_px(x, 0), to_px(x, 4)], fill=line_color, width=line_width)
            draw.line([to_px(x, 5), to_px(x, 9)], fill=line_color, width=line_width)
            if col == 0 or col == 8:
                draw.line([to_px(x, 4), to_px(x, 5)], fill=line_color, width=line_width)

        # 绘制水平网格线
        for row in range(10):
            z = float(row)
            draw.line([to_px(0, z), to_px(8, z)], fill=line_color, width=line_width)

        # 绘制九宫格斜线
        for offset_z in [0, 7]:
            draw.line(
                [to_px(3, offset_z), to_px(5, offset_z + 2)],
                fill=line_color,
                width=line_width,
            )
            draw.line(
                [to_px(3, offset_z + 2), to_px(5, offset_z)],
                fill=line_color,
                width=line_width,
            )

        # 绘制兵/炮定位十字标记
        def draw_mark(cx, cz):
            gap, length = 0.08, 0.25
            for dx in [-1, 1]:
                for dz in [-1, 1]:
                    if 0 <= cx + dx * gap <= 8 and 0 <= cz + dz * gap <= 9:
                        px1, py1 = to_px(cx + dx * gap, cz + dz * gap)
                        px2, py2 = to_px(cx + dx * (gap + length), cz + dz * gap)
                        px3, py3 = to_px(cx + dx * gap, cz + dz * (gap + length))
                        draw.line(
                            [px1, py1, px2, py2], fill=line_color, width=line_width
                        )
                        draw.line(
                            [px1, py1, px3, py3], fill=line_color, width=line_width
                        )

        marks = [(1, 2), (7, 2), (1, 7), (7, 7)]
        for col in [0, 2, 4, 6, 8]:
            marks.extend([(col, 3), (col, 6)])
        for cx, cz in marks:
            draw_mark(cx, cz)

        # 绘制楚河汉界文字
        font = None
        for font_name in [
            "msyh.ttc",
            "simhei.ttf",
            "simsun.ttc",
            "C:/Windows/Fonts/simhei.ttf",
        ]:
            try:
                font = ImageFont.truetype(font_name, 120)
                break
            except IOError:
                continue
        if font is None:
            font = ImageFont.load_default()

        def draw_text(text, x, z):
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
            except:
                tw, th = 120, 120
            px, py = to_px(x, z)
            draw.text((px - tw // 2, py - th // 2), text, font=font, fill=line_color)

        draw_text("楚", 1.5, 4.5)
        draw_text("河", 2.5, 4.5)
        draw_text("汉", 5.5, 4.5)
        draw_text("界", 6.5, 4.5)

        # 不做变换，保持文字正确方向
        raw_data = img.tobytes()

        # 使用原始OpenGL创建纹理
        texture_ids = (pyglet.gl.GLuint * 1)()
        gl.glGenTextures(1, texture_ids)
        texture_id = texture_ids[0]

        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D,
            0,
            gl.GL_RGBA,
            img_w,
            img_h,
            0,
            gl.GL_RGBA,
            gl.GL_UNSIGNED_BYTE,
            raw_data,
        )
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)

        self._texture_obj = texture_id
        return texture_id

    def render(self):
        if self.texture_id is None:
            return

        w, h = self.board_width, self.board_height
        t = self.board_thickness
        fw = self.frame_width

        # 绑定贴图绘制棋盘顶面
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glColor4f(1.0, 1.0, 1.0, 1.0)

        gl.glBegin(gl.GL_QUADS)
        gl.glNormal3f(0, 1, 0)
        gl.glTexCoord2f(0.0, 0.0)
        gl.glVertex3f(-fw, t, -fw)
        gl.glTexCoord2f(1.0, 0.0)
        gl.glVertex3f(w + fw, t, -fw)
        gl.glTexCoord2f(1.0, 1.0)
        gl.glVertex3f(w + fw, t, h + fw)
        gl.glTexCoord2f(0.0, 1.0)
        gl.glVertex3f(-fw, t, h + fw)
        gl.glEnd()
        gl.glDisable(gl.GL_TEXTURE_2D)

        # 绘制侧边及底面
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
        gl.glVertex3f(-fw, 0, -fw)
        gl.glVertex3f(-fw, 0, h + fw)
        gl.glVertex3f(-fw, t, h + fw)
        gl.glVertex3f(-fw, t, -fw)

        gl.glNormal3f(1, 0, 0)
        gl.glVertex3f(w + fw, 0, -fw)
        gl.glVertex3f(w + fw, t, -fw)
        gl.glVertex3f(w + fw, t, h + fw)
        gl.glVertex3f(w + fw, 0, h + fw)

        gl.glNormal3f(0, -1, 0)
        gl.glVertex3f(-fw, 0, -fw)
        gl.glVertex3f(w + fw, 0, -fw)
        gl.glVertex3f(w + fw, 0, h + fw)
        gl.glVertex3f(-fw, 0, h + fw)
        gl.glEnd()
