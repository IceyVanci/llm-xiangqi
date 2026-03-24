"""
中国象棋3D图形界面

使用pyglet实现3D渲染，独立线程运行
"""

import os

# 强制使用基础OpenGL配置，避免ARB扩展（解决部分Windows系统OpenGL驱动问题）
os.environ["PYGLET_HEADLESS"] = "False"
os.environ["PYGLET_DEBUG_GL"] = "0"
# 禁用所有OpenGL扩展检查
os.environ["PYGLET_SHADOW_WINDOW"] = "False"

import threading
import time
import math
from typing import Optional
from ctypes import c_float

import pyglet
from pyglet import gl
from pyglet.gl import glu
from pyglet.window import mouse

from .chess_board_renderer import ChessBoardRenderer
from .piece_renderer import PieceRenderer, PIECE_LABELS
from .camera_controller import CameraController

# 棋子位置FEN映射（初始局面）
INITIAL_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR"

# ICCS坐标到棋盘坐标的转换
# ICCS: a-i (列), 1-10 (行)
# 棋盘: x (0-8, 列), z (0-9, 行, 从红方视角)
# 红方在下方(行7-9)，黑方在上方(行0-2)


class ChessGUI:
    """中国象棋3D图形界面"""

    def __init__(self, fen: str = INITIAL_FEN):
        """初始化GUI

        Args:
            fen: FEN格式的棋盘状态
        """
        self.fen = fen
        self.batch = pyglet.graphics.Batch()

        # 渲染器
        self.board_renderer = ChessBoardRenderer()
        self.piece_renderer = PieceRenderer()
        self.camera = CameraController(distance=18, elevation=55, azimuth=45)

        # 棋盘状态
        self.pieces = {}  # {(x, z): piece_char}
        self._parse_fen(fen)

        # 动画状态
        self.animating_piece = (
            None  # {'from': (x,z), 'to': (x,z), 'char': 'R', 'progress': 0}
        )
        self.animation_duration = 0.3

        # 窗口和pyglet引用
        self.window: Optional[pyglet.window.Window] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _parse_fen(self, fen: str):
        """解析FEN格式的棋盘状态"""
        self.pieces.clear()

        # FEN格式: position color castle ... move ... (we only need position)
        parts = fen.split()
        position = parts[0]

        rows = position.split("/")
        # 行0是黑方底线（最上方），行9是红方底线（最下方）
        for row_idx, row in enumerate(rows):
            col_idx = 0
            for char in row:
                if char.isdigit():
                    col_idx += int(char)
                else:
                    # 转换坐标: FEN行 -> z, FEN列 -> x
                    # FEN row 0 = 黑方底线 = z 0
                    # FEN row 9 = 红方底线 = z 9
                    z = row_idx
                    x = col_idx
                    self.pieces[(x, z)] = char
                    col_idx += 1

    def _iccs_to_coords(self, iccs_move: str) -> tuple:
        """将ICCS坐标转换为棋盘坐标

        ICCS: e2e4 格式 (列字母 + 行数字)
        列: a-i (0-8), 行: 1-10 (1=黑方底线, 10=红方底线)
        """
        if len(iccs_move) != 4:
            return None

        col1, row1 = iccs_move[0].lower(), int(iccs_move[1])
        col2, row2 = iccs_move[2].lower(), int(iccs_move[3])

        # ICCS行1=黑方底线=棋盘z0, ICCS行10=红方底线=棋盘z9
        x1, z1 = ord(col1) - ord("a"), row1 - 1
        x2, z2 = ord(col2) - ord("a"), row2 - 1

        return (x1, z1), (x2, z2)

    def update(
        self,
        move: Optional[str] = None,
        fen: Optional[str] = None,
        is_game_over: bool = False,
    ):
        """更新棋盘状态

        Args:
            move: ICCS格式的走步 (如 "h2e2")
            fen: 新的FEN状态
            is_game_over: 游戏是否结束
        """
        if fen:
            self._parse_fen(fen)

        if move and fen:
            # 启动走棋动画
            coords = self._iccs_to_coords(move)
            if coords:
                from_pos, to_pos = coords
                moving_char = self.pieces.get(from_pos)

                if moving_char:
                    # 记录被吃的棋子
                    captured = self.pieces.get(to_pos)

                    # 移除起始位置的棋子
                    del self.pieces[from_pos]

                    # 如果有吃子，动画后移除被吃棋子
                    if captured:
                        self.animating_piece = {
                            "from": from_pos,
                            "to": to_pos,
                            "char": moving_char,
                            "captured": captured,
                            "progress": 0,
                        }
                    else:
                        self.animating_piece = {
                            "from": from_pos,
                            "to": to_pos,
                            "char": moving_char,
                            "captured": None,
                            "progress": 0,
                        }

                    # 动画结束后更新位置
                    def finish_animation():
                        time.sleep(self.animation_duration)
                        self.pieces[to_pos] = moving_char
                        if captured:
                            # 移除被吃的棋子（由capture_piece处理）
                            pass
                        self.animating_piece = None

                    anim_thread = threading.Thread(target=finish_animation, daemon=True)
                    anim_thread.start()

    def capture_piece(self, x, z):
        """移除指定位置的棋子（吃子动画）"""
        key = (x, z)
        if key in self.pieces:
            del self.pieces[key]

    def _setup_lighting(self):
        """设置OpenGL光照"""
        gl.glEnable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_LIGHT0)
        gl.glEnable(gl.GL_LIGHT1)
        gl.glEnable(gl.GL_NORMALIZE)
        gl.glEnable(gl.GL_COLOR_MATERIAL)
        gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)

        gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, (c_float * 4)(4.5, 15.0, 5.0, 1.0))
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_AMBIENT, (c_float * 4)(0.4, 0.4, 0.4, 1.0))
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, (c_float * 4)(0.9, 0.9, 0.85, 1.0))
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_SPECULAR, (c_float * 4)(0.5, 0.5, 0.5, 1.0))

        gl.glLightfv(gl.GL_LIGHT1, gl.GL_POSITION, (c_float * 4)(4.5, 10.0, 5.0, 1.0))
        gl.glLightfv(gl.GL_LIGHT1, gl.GL_AMBIENT, (c_float * 4)(0.3, 0.3, 0.3, 1.0))
        gl.glLightfv(gl.GL_LIGHT1, gl.GL_DIFFUSE, (c_float * 4)(0.6, 0.6, 0.6, 1.0))

        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LEQUAL)
        gl.glShadeModel(gl.GL_SMOOTH)

        gl.glClearColor(0.15, 0.12, 0.1, 1.0)

    def _draw_board_frame(self):
        """绘制棋盘边框装饰"""
        gl.glColor4f(0.4, 0.25, 0.1, 1.0)
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)

    def on_draw(self):
        """绘制回调"""
        if not self.window:
            return
        self.window.clear()

        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluPerspective(45, self.window.width / self.window.height, 0.1, 100.0)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

        eye, target, up = self.camera.get_view_matrix()
        glu.gluLookAt(
            eye[0],
            eye[1],
            eye[2],
            target[0],
            target[1],
            target[2],
            up[0],
            up[1],
            up[2],
        )

        self._setup_lighting()

        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)
        self.board_renderer.render()

        gl.glColor4f(1.0, 1.0, 1.0, 1.0)

        anim_pos = None
        if self.animating_piece:
            prog = min(1.0, self.animating_piece["progress"])
            from_x = self.animating_piece["from"][0]
            from_z = self.animating_piece["from"][1]
            to_x = self.animating_piece["to"][0]
            to_z = self.animating_piece["to"][1]

            curr_x = from_x + (to_x - from_x) * prog
            curr_z = from_z + (to_z - from_z) * prog
            anim_pos = (curr_x, curr_z, self.animating_piece["char"])

        board_y = self.board_renderer.board_thickness

        for (x, z), char in list(self.pieces.items()):
            if anim_pos and self.animating_piece:
                if (
                    abs(x - self.animating_piece["from"][0]) < 0.1
                    and abs(z - self.animating_piece["from"][1]) < 0.1
                ):
                    continue

            gl.glPushMatrix()
            gl.glTranslatef(x, board_y, z)
            self._render_piece(char)
            gl.glPopMatrix()

        if anim_pos:
            gl.glPushMatrix()
            gl.glTranslatef(anim_pos[0], board_y, anim_pos[1])
            self._render_piece(anim_pos[2])
            gl.glPopMatrix()

        if self.animating_piece and self.animating_piece["captured"]:
            if self.animating_piece["progress"] > 0.5:
                alpha = 1.0 - (self.animating_piece["progress"] - 0.5) * 2
                gl.glColor4f(1.0, 1.0, 1.0, alpha)
                gl.glPushMatrix()
                gl.glTranslatef(
                    self.animating_piece["to"][0],
                    board_y,
                    self.animating_piece["to"][1],
                )
                self._render_piece(self.animating_piece["captured"])
                gl.glPopMatrix()

        if anim_pos:
            gl.glPushMatrix()
            gl.glTranslatef(anim_pos[0], board_y, anim_pos[1])
            gl.glScalef(0.5, 0.5, 0.5)
            self._render_piece(anim_pos[2])
            gl.glPopMatrix()

        if self.animating_piece and self.animating_piece["captured"]:
            if self.animating_piece["progress"] > 0.5:
                alpha = 1.0 - (self.animating_piece["progress"] - 0.5) * 2
                gl.glColor4f(1.0, 1.0, 1.0, alpha)
                gl.glPushMatrix()
                gl.glTranslatef(
                    self.animating_piece["to"][0],
                    board_y,
                    self.animating_piece["to"][1],
                )
                gl.glScalef(0.5, 0.5, 0.5)
                self._render_piece(self.animating_piece["captured"])
                gl.glPopMatrix()

    def _render_piece(self, char):
        """渲染单个棋子（3D圆柱体）"""
        radius = 0.4
        height = 0.15

        is_red = char.isupper()

        if is_red:
            base_color = (0.85, 0.15, 0.1)
            top_color = (0.95, 0.25, 0.15)
            label_color = (1.0, 0.9, 0.8)
        else:
            base_color = (0.1, 0.1, 0.1)
            top_color = (0.18, 0.18, 0.18)
            label_color = (0.95, 0.95, 0.95)

        wood_color = (0.7, 0.5, 0.25)

        self._draw_cylinder_3d(radius + 0.02, height * 0.3, wood_color)

        gl.glPushMatrix()
        gl.glTranslatef(0, height * 0.15, 0)
        self._draw_cylinder_3d(radius, height * 0.7, base_color)
        gl.glPopMatrix()

        gl.glPushMatrix()
        gl.glTranslatef(0, height * 0.85, 0)
        self._draw_disk_3d(radius, top_color)
        gl.glPopMatrix()

        self._draw_label_3d(char, height * 0.9, label_color, is_red)

    def _draw_cylinder_3d(self, radius, height, color):
        """绘制3D圆柱体"""
        segments = 24
        height_half = height / 2

        gl.glBegin(gl.GL_QUADS)
        for i in range(segments):
            angle1 = (i / segments) * 2 * math.pi
            angle2 = ((i + 1) / segments) * 2 * math.pi

            x1, z1 = radius * math.cos(angle1), radius * math.sin(angle1)
            x2, z2 = radius * math.cos(angle2), radius * math.sin(angle2)

            shade = 0.7 + 0.3 * math.cos(angle1)
            gl.glColor4f(color[0] * shade, color[1] * shade, color[2] * shade, 1.0)

            gl.glNormal3f(math.cos(angle1), 0, math.sin(angle1))
            gl.glVertex3f(x1, -height_half, z1)
            gl.glNormal3f(math.cos(angle2), 0, math.sin(angle2))
            gl.glVertex3f(x2, -height_half, z2)
            gl.glVertex3f(x2, height_half, z2)
            gl.glNormal3f(math.cos(angle1), 0, math.sin(angle1))
            gl.glVertex3f(x1, height_half, z1)
        gl.glEnd()

    def _draw_disk_3d(self, radius, color):
        """绘制3D圆盘"""
        segments = 24

        gl.glColor4f(*color, 1.0)
        gl.glNormal3f(0, 1, 0)

        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glVertex3f(0, 0, 0)
        for i in range(segments + 1):
            angle = (i / segments) * 2 * math.pi
            gl.glVertex3f(radius * math.cos(angle), 0, radius * math.sin(angle))
        gl.glEnd()

    def _draw_label_3d(self, char, y, color, is_red):
        """绘制棋子文字标签"""
        label = PIECE_LABELS.get(char, "?")

        gl.glColor4f(*color, 1.0)
        gl.glNormal3f(0, 1, 0)

        size = 0.2

        if label in ["帥", "將", "車", "馬", "炮"]:
            size = 0.22

        self._draw_chinese_char(label, 0, y, 0, size, is_red)

    def _draw_chinese_char(self, char, x, y, z, size, is_red):
        """使用简化的笔画绘制中文字符"""
        gl.glPushMatrix()
        gl.glTranslatef(x, y, z)
        gl.glRotatef(-90, 1, 0, 0)

        gl.glLineWidth(2.5 if is_red else 2.0)

        stroke_color = (1.0, 0.9, 0.85, 1.0) if is_red else (0.95, 0.95, 0.95, 1.0)
        gl.glColor4f(*stroke_color)

        s = size

        strokes = self._get_char_strokes(char)

        for stroke in strokes:
            if len(stroke) == 2:
                gl.glBegin(gl.GL_LINES)
                gl.glVertex3f(stroke[0][0] * s, stroke[0][1] * s, 0)
                gl.glVertex3f(stroke[1][0] * s, stroke[1][1] * s, 0)
                gl.glEnd()
            elif len(stroke) >= 3:
                gl.glBegin(gl.GL_LINE_STRIP)
                for pt in stroke:
                    gl.glVertex3f(pt[0] * s, pt[1] * s, 0)
                gl.glEnd()

        gl.glPopMatrix()

    def _get_char_strokes(self, char):
        """获取汉字的简化笔画数据"""
        strokes_map = {
            "帥": [
                [(-0.4, 0), (0.4, 0)],
                [(0, -0.4), (0, 0.4)],
                [(-0.3, -0.3), (-0.3, 0.3)],
                [(0.3, -0.3), (0.3, 0.3)],
                [(-0.2, 0.3), (0.2, 0.3)],
            ],
            "將": [
                [(-0.3, -0.4), (-0.3, 0.4)],
                [(0.3, -0.4), (0.3, 0.4)],
                [(-0.3, 0), (0.3, 0)],
                [(-0.3, -0.3), (0.3, -0.3)],
                [(-0.3, 0.3), (0.3, 0.3)],
            ],
            "仕": [
                [(0, -0.4), (0, 0.1)],
                [(-0.3, 0.1), (0.3, 0.1)],
                [(0, 0.1), (0, 0.4)],
                [(-0.2, 0.4), (0.2, 0.4)],
            ],
            "士": [
                [(-0.3, -0.4), (0.3, -0.4)],
                [(0, -0.4), (0, 0.4)],
                [(-0.3, 0.4), (0.3, 0.4)],
            ],
            "相": [
                [(-0.2, -0.4), (0.2, -0.4)],
                [(-0.4, 0), (0, -0.4)],
                [(0.4, 0), (0, -0.4)],
                [(0, 0), (0, 0.4)],
                [(-0.3, 0.4), (0.3, 0.4)],
            ],
            "象": [
                [(-0.2, -0.4), (0.2, -0.4)],
                [(-0.3, -0.2), (-0.3, 0)],
                [(0.3, -0.2), (0.3, 0)],
                [(-0.3, 0), (0.3, 0)],
                [(0, 0), (0, 0.4)],
                [(-0.2, 0.4), (0.2, 0.4)],
            ],
            "馬": [
                [(-0.3, -0.4), (0.1, -0.4)],
                [(-0.2, -0.4), (-0.2, 0.2)],
                [(-0.2, 0.2), (0.2, 0.2)],
                [(0.2, 0.2), (0.2, -0.1)],
                [(0, 0.2), (0, 0.4)],
                [(-0.2, 0.4), (0.2, 0.4)],
            ],
            "車": [
                [(-0.3, -0.4), (0.3, -0.4)],
                [(0, -0.4), (0, 0.4)],
                [(-0.3, 0.4), (0.3, 0.4)],
                [(-0.3, -0.4), (-0.3, 0.4)],
                [(0.3, -0.4), (0.3, 0.4)],
            ],
            "炮": [
                [(-0.3, -0.4), (0.3, -0.4)],
                [(-0.3, -0.2), (0.3, -0.2)],
                [(-0.2, -0.4), (-0.2, -0.2)],
                [(0.2, -0.4), (0.2, -0.2)],
                [(0, 0), (0, 0.4)],
                [(-0.25, 0.4), (0.25, 0.4)],
            ],
            "兵": [
                [(-0.2, -0.4), (0.2, -0.4)],
                [(0, -0.4), (0, 0.4)],
                [(-0.3, 0), (0.3, 0)],
                [(-0.25, 0.4), (0.25, 0.4)],
            ],
            "卒": [
                [(-0.3, -0.4), (0.3, -0.4)],
                [(0, -0.4), (0, 0.4)],
                [(-0.3, 0.1), (0.3, 0.1)],
                [(-0.25, 0.4), (0.25, 0.4)],
            ],
        }
        return strokes_map.get(char, [[(-0.2, 0), (0.2, 0)], [(0, -0.2), (0, 0.2)]])

    def on_mouse_press(self, x, y, button, modifiers):
        """鼠标按下"""
        if button == mouse.LEFT:
            self.camera.start_drag(x, y)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        """鼠标拖拽"""
        if buttons & mouse.LEFT:
            self.camera.drag(x, y)

    def on_mouse_release(self, x, y, button, modifiers):
        """鼠标释放"""
        if button == mouse.LEFT:
            self.camera.end_drag()

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        """鼠标滚轮"""
        self.camera.zoom(scroll_y)

    def update_animation(self, dt):
        """更新动画"""
        if not self._running or not self.window:
            return
        if self.animating_piece:
            self.animating_piece["progress"] += dt / self.animation_duration
            if self.animating_piece["progress"] >= 1.0:
                # 动画结束
                to_x, to_z = self.animating_piece["to"]
                char = self.animating_piece["char"]
                self.pieces[(to_x, to_z)] = char

                # 移除被吃的棋子
                captured = self.animating_piece.get("captured")
                if captured:
                    cap_x, cap_z = self.animating_piece["to"]
                    cap_key = (cap_x, cap_z)
                    if cap_key in self.pieces:
                        del self.pieces[cap_key]

                self.animating_piece = None

    def run(self):
        """运行GUI（主循环）"""
        if self._running:
            return

        self._running = True

        # 创建窗口
        try:
            # 尝试创建最简单的窗口配置
            try:
                # 首先尝试使用简单配置
                display = pyglet.display.get_display()
                screen = display.get_screens()[0]
                template = pyglet.gl.Config(
                    double_buffer=True,
                    depth_size=24,
                )
                config = screen.get_best_config(template)
            except Exception:
                # 如果失败，尝试完全默认配置
                config = None

            if config:
                self.window = pyglet.window.Window(
                    width=1024,
                    height=768,
                    caption="中国象棋 - LLM Battle",
                    resizable=True,
                    config=config,
                )
            else:
                # 使用完全默认配置（无config参数）
                self.window = pyglet.window.Window(
                    width=1024,
                    height=768,
                    caption="中国象棋 - LLM Battle",
                    resizable=True,
                )
            self.window = pyglet.window.Window(
                width=1024,
                height=768,
                caption="中国象棋 - LLM Battle",
                resizable=True,
                config=config,
            )
        except Exception as e:
            print(f"GUI初始化失败 (OpenGL不可用): {e}")
            print("将使用CLI模式继续游戏...")
            self._running = False
            self.window = None
            return

        # 设置事件处理器
        self.window.on_draw = self.on_draw
        self.window.on_mouse_press = self.on_mouse_press
        self.window.on_mouse_drag = self.on_mouse_drag
        self.window.on_mouse_release = self.on_mouse_release
        self.window.on_mouse_scroll = self.on_mouse_scroll

        # 创建时钟回调用于动画更新
        pyglet.clock.schedule_interval(self.update_animation, 1 / 60.0)

        # 运行pyglet主循环
        pyglet.app.run()

        self._running = False

    def start(self):
        """在新线程中启动GUI"""
        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def stop(self):
        """停止GUI"""
        self._running = False
        if self.window:
            self.window.close()
