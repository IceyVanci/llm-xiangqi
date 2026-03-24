"""
3D相机控制器

支持鼠标拖拽旋转和滚轮缩放
"""

import math


class CameraController:
    """3D相机控制器"""

    def __init__(self, distance=15.0, elevation=45.0, azimuth=45.0):
        """初始化相机控制器

        Args:
            distance: 相机距离目标点的距离
            elevation: 仰角（度），0=水平，90=俯视
            azimuth: 方位角（度），绕Y轴旋转
        """
        self.distance = distance
        self.elevation = elevation  # degrees
        self.azimuth = azimuth  # degrees
        self.target = [4.5, 0.0, 5.0]  # 棋盘中心

        # 鼠标拖拽状态
        self._is_dragging = False
        self._last_mouse_x = 0
        self._last_mouse_y = 0

        # 缩放限制
        self.min_distance = 5.0
        self.max_distance = 30.0

        # 旋转限制
        self.min_elevation = 10.0
        self.max_elevation = 85.0

    def start_drag(self, x, y):
        """开始拖拽"""
        self._is_dragging = True
        self._last_mouse_x = x
        self._last_mouse_y = y

    def drag(self, x, y):
        """拖拽旋转"""
        if not self._is_dragging:
            return

        dx = x - self._last_mouse_x
        dy = y - self._last_mouse_y

        # 水平移动控制方位角
        self.azimuth += dx * 0.5

        # 垂直移动控制仰角
        self.elevation = max(
            self.min_elevation, min(self.max_elevation, self.elevation - dy * 0.5)
        )

        self._last_mouse_x = x
        self._last_mouse_y = y

    def end_drag(self):
        """结束拖拽"""
        self._is_dragging = False

    def zoom(self, delta):
        """滚轮缩放

        Args:
            delta: 缩放增量，正值放大，负值缩小
        """
        self.distance = max(
            self.min_distance, min(self.max_distance, self.distance + delta * 0.5)
        )

    def get_view_matrix(self):
        """获取观察矩阵（eye, target, up）

        Returns:
            tuple: (eye, target, up)
        """
        # 将角度转换为弧度
        elev_rad = math.radians(self.elevation)
        azim_rad = math.radians(self.azimuth)

        # 计算相机位置
        cos_elev = math.cos(elev_rad)
        sin_elev = math.sin(elev_rad)
        cos_azim = math.cos(azim_rad)
        sin_azim = math.sin(azim_rad)

        x = self.target[0] + self.distance * cos_elev * sin_azim
        y = self.target[1] + self.distance * sin_elev
        z = self.target[2] + self.distance * cos_elev * cos_azim

        eye = (x, y, z)
        up = (0.0, 1.0, 0.0) if self.elevation < 89 else (0.0, 0.0, -1.0)

        return eye, self.target, up

    def reset(self):
        """重置相机到默认位置"""
        self.distance = 15.0
        self.elevation = 45.0
        self.azimuth = 45.0
