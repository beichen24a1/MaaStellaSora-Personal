"""
调试用的agent截图保存功能，会把截图以png格式保存到项目目录的 debug/agent_image 目录下
由于打包后的便携版python没有安装PIL模块，请不要在打包后的环境中使用该功能

使用方法：
    from utils.image_handler import save_image

    save_image(image, "说明信息")
"""

from pathlib import Path
from datetime import datetime

import numpy as np
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    Image = None
    HAS_PIL = False


save_dir = Path(__file__).resolve().parents[2] / "debug" / "agent_image"
save_dir.mkdir(parents=True, exist_ok=True)


def save_image(image: np.ndarray, comment: str) -> bool:
    if not HAS_PIL:
        print("PIL模块未安装，无法保存图片")
        return False

    # 生成文件名
    current_time = datetime.now()
    timestamp = current_time.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # %f是微秒，取前3位得到毫秒
    filename = f"{timestamp}-{comment}.png"
    file_path = save_dir / filename

    # 处理截图
    # 由于OpenCV截图默认是BGR格式，需要转换为RGB格式
    img = Image.fromarray(image[:, :, ::-1], mode='RGB')

    # 保存截图
    img.save(file_path)
    return True


# ===== 识别截图留档（不依赖 PIL，直接写 BMP）=====
import os
import struct
import time as _time

_rec_dir = Path(__file__).resolve().parents[2] / "debug" / "识别截图"
_rec_dir.mkdir(parents=True, exist_ok=True)


def _cleanup_old_snapshots(max_count: int = 100):
    """保留最近 max_count 张识别截图，超出则删除最旧的。"""
    try:
        files = [f for f in _rec_dir.iterdir() if f.is_file() and f.suffix.lower() in (".bmp", ".png")]
        if len(files) > max_count:
            files.sort(key=lambda f: f.stat().st_mtime, reverse=False)
            for f in files[:len(files) - max_count]:
                try:
                    f.unlink()
                except Exception:
                    pass
    except Exception:
        pass


def save_rec_screenshot(image, tag: str = "") -> str:
    """把识别用的截图保存到 debug/识别截图/，按 年月日时分秒 命名，BMP 格式（无需 PIL）。

    Args:
        image: MAA 截图（numpy, BGR）。
        tag: 备注（如节点名），用于区分。

    Returns:
        str: 保存路径；失败返回说明。
    """
    try:
        import numpy as np
        from PIL import Image
        _cleanup_old_snapshots()
        ts = datetime.now().strftime("%Y.%m.%d.%H.%M.%S")
        name = f"{ts}_{tag}.png" if tag else f"{ts}.png"
        path = _rec_dir / name
        # MAA 截图通常为 BGR，转 RGB 后存 PNG
        img = Image.fromarray(image[:, :, :3][:, :, ::-1], mode="RGB")
        img.save(path)
        return str(path)
    except Exception as exc:
        return f"<save failed: {exc}>"
