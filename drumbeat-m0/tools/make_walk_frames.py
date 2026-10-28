"""生成玩家左右腿交替的跑动补帧（run_4 / run_5）。

原理：现有 run_0..3 由 AI 生成，均为同一侧腿领先的跑姿。
把「腰带以下的腿部区域」水平镜像后贴回原帧，即得到对侧腿领先的变体：
  run_4 = run_0 的对侧腿版本
  run_5 = run_2 的对侧腿版本
镜像只作用于裁切线以下，风格、调色板、画布尺寸与原素材完全一致。

运行：python tools/make_walk_frames.py
重复运行安全（覆盖生成同一结果）。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

import drumbeat.assets  # noqa: F401,E402  触发 Windows 下图像解码 DLL 预加载

ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "characters", "player")

# (源帧, 输出帧, 裁切线高度比例)：裁切线以下为腿部区域，做水平镜像
# 线取在袍摆处（长飘带居中不受影响），并避开手持英歌槌的位置
SPECS = [
    ("run_0.png", "run_4.png", 0.70),
    ("run_2.png", "run_5.png", 0.72),
]


def mirror_legs(src: pygame.Surface, cut_frac: float) -> pygame.Surface:
    w, h = src.get_size()
    cut = int(h * cut_frac)
    out = src.copy()
    legs = src.subsurface(pygame.Rect(0, cut, w, h - cut)).copy()
    mirrored = pygame.transform.flip(legs, True, False)
    out.blit(mirrored, (0, cut))
    return out


def main() -> int:
    pygame.init()
    pygame.display.set_mode((1, 1))
    for src_name, out_name, frac in SPECS:
        src = pygame.image.load(os.path.join(ASSET_DIR, src_name))
        out = mirror_legs(src, frac)
        path = os.path.join(ASSET_DIR, out_name)
        pygame.image.save(out, path)
        print(f"{src_name} -> {out_name}  (cut@{frac:.0%}, {out.get_size()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
