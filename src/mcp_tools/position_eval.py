"""
局面评估工具 (Pikafish)

使用Pikafish引擎评估局面
"""

import subprocess
import threading
import time
from typing import Dict, Any, Optional, Tuple, List


class PikafishEngine:
    """Pikafish引擎接口

    使用UCCI协议与Pikafish引擎通信
    """

    _instance: Optional['PikafishEngine'] = None
    _lock = threading.Lock()

    def __init__(self, path: str = "pikafish.exe", depth: int = 15):
        self.path = path
        self.depth = depth
        self.process: Optional[subprocess.Popen] = None
        self._initialized = False
        self._init()

    @classmethod
    def get_instance(cls, path: str = "pikafish.exe", depth: int = 15) -> 'PikafishEngine':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(path, depth)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """重置单例（用于测试或重新初始化）"""
        if cls._instance and cls._instance.process:
            try:
                cls._instance.process.stdin.write("quit\n")
                cls._instance.process.stdin.flush()
                cls._instance.process.wait(timeout=2)
            except:
                pass
        cls._instance = None

    def _init(self):
        """初始化引擎"""
        try:
            self.process = subprocess.Popen(
                [self.path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            self._send("ucci")
            self._read_until("ucciok", timeout=10)
            self._send("setoption name Threads value 4")
            self._send("setoption name Hash value 128")
            self._send("isready")
            self._read_until("readyok", timeout=10)
            self._initialized = True
        except Exception as e:
            print(f"Warning: Pikafish initialization failed: {e}")
            self.process = None
            self._initialized = False

    def _send(self, cmd: str):
        """发送命令"""
        if self.process and self.process.stdin:
            self.process.stdin.write(cmd + "\n")
            self.process.stdin.flush()

    def _read_line(self, timeout: float = 5.0) -> str:
        """读取一行"""
        if not self.process:
            return ""
        import select
        start = time.time()
        while time.time() - start < timeout:
            if select.select([self.process.stdout], [], [], 0.1)[0]:
                line = self.process.stdout.readline()
                if line:
                    return line.strip()
        return ""

    def _read_until(self, keyword: str, timeout: float = 5.0) -> str:
        """读取直到包含关键词"""
        lines = []
        start = time.time()
        while time.time() - start < timeout:
            line = self._read_line(timeout=1)
            if not line:
                break
            lines.append(line)
            if keyword in line:
                break
        return "\n".join(lines)

    def is_available(self) -> bool:
        """检查引擎是否可用"""
        return self._initialized and self.process is not None

    def evaluate(self, fen: str, depth: int = None) -> Dict[str, Any]:
        """评估局面

        Args:
            fen: FEN字符串
            depth: 搜索深度

        Returns:
            {"score": int, "bestmove": str, "pv": [...], "depth": int}
        """
        if not self.is_available():
            return {
                "score": 0,
                "bestmove": None,
                "pv": [],
                "depth": 0,
                "error": "Engine not available"
            }

        depth = depth or self.depth

        try:
            self._send(f"position fen {fen}")
            self._send(f"go depth {depth}")

            info_lines = []
            bestmove = None
            score = 0

            # 读取直到收到bestmove
            while True:
                line = self._read_line(timeout=10)
                if not line:
                    break
                info_lines.append(line)

                if "bestmove" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        bestmove = parts[1]
                    break

                # 解析score
                if "score" in line:
                    if "cp" in line:
                        try:
                            idx = line.index("cp") + 3
                            score = int(line[idx:].split()[0])
                        except:
                            score = 0
                    elif "mate" in line:
                        try:
                            idx = line.index("mate") + 5
                            mate_score = int(line[idx:].split()[0])
                            # 将杀分数用大数值表示
                            score = 10000 if mate_score > 0 else -10000
                        except:
                            score = 0

            # 解析pv (principal variation)
            pv = []
            for line in info_lines:
                if " pv " in line:
                    try:
                        pv_idx = line.index("pv") + 3
                        pv = line[pv_idx:].split()[:5]  # 只取前5步
                    except:
                        pass
                    break

            return {
                "score": score,
                "bestmove": bestmove,
                "pv": pv,
                "depth": depth,
                "evaluation": self._interpret_score(score)
            }

        except Exception as e:
            return {
                "score": 0,
                "bestmove": None,
                "pv": [],
                "depth": depth,
                "error": str(e)
            }

    def _interpret_score(self, score: int) -> str:
        """解释评分"""
        if score > 500:
            return "大优"
        elif score > 200:
            return "优势"
        elif score > 50:
            return "略优"
        elif score > -50:
            return "均势"
        elif score > -200:
            return "略劣"
        elif score > -500:
            return "劣势"
        else:
            return "大劣"

    def get_legal_moves_scored(self, fen: str, depth: int = 12) -> List[Tuple[str, int]]:
        """获取按评分排序的合法走步

        Args:
            fen: FEN字符串
            depth: 搜索深度

        Returns:
            [(move, centipawn_score), ...] 按评分降序
        """
        # 这个功能需要更复杂的实现
        # 暂时返回空列表
        return []

    def close(self):
        """关闭引擎"""
        if self.process:
            try:
                self._send("quit")
                self.process.wait(timeout=2)
            except:
                pass
            self.process = None
            self._initialized = False


class PositionEvalTool:
    """局面评估工具"""

    def __init__(self, pikafish_path: str = "pikafish.exe", depth: int = 15):
        self.engine = PikafishEngine.get_instance(pikafish_path, depth)

    async def execute(self, fen: str, depth: int = 15) -> Dict[str, Any]:
        """执行局面评估

        Args:
            fen: FEN字符串
            depth: 搜索深度

        Returns:
            评估结果
        """
        result = self.engine.evaluate(fen, depth)
        return {
            "success": True,
            "fen": fen,
            "score": result.get("score", 0),
            "best_move": result.get("bestmove"),
            "principal_variation": result.get("pv", []),
            "depth": result.get("depth", depth),
            "evaluation": result.get("evaluation", "未知"),
            "error": result.get("error")
        }

    def is_available(self) -> bool:
        """检查工具是否可用"""
        return self.engine.is_available()
