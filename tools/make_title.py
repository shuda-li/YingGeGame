"""生成主菜单像素风标题字图「踏鼓」。

用系统中文字体（黑体优先）以高分辨率渲染标题，再降采样回像素网格（最近邻），
得到像素化标题；主色为中国红，叠加深色描边 + 高光，输出透明背景 PNG。

用法：在仓库根目录执行
    .venv/Scripts/python.exe tools/make_title.py

输出：drumbeat-m0/assets/ui/title.png
"""
from __future__ import annotations

import os
import sys

import pygame

# 运行目录定位到仓库根，保证 assets 路径稳定
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "drumbeat-m0", "assets", "ui")
OUT_PATH = os.path.join(OUT_DIR, "title.png")

TITLE = "踏鼓"
# 像素网格：最终每个字约 96px 高，网格越粗像素感越强
PIXEL_CELL = 5          # 每个像素块最终占 5px
# 高分辨率渲染尺寸（将被缩放到像素网格）
NATIVE_H = 128


def pick_font() -> str | None:
    """优先黑体（笔画粗、硬朗），其次新魏体（书法感）。"""
    for name in ("simhei", "simsunb", "msyhbd", "stxinwei"):
        path = pygame.font.match_font(name)
        if path:
            return path
    return pygame.font.match_font("simsun")


def make_title() -> pygame.Surface:
    pygame.init()
    pygame.display.set_mode((1, 1))  # 需要 display surface 才能 convert_alpha
    path = pick_font()
    if path is None:
        raise RuntimeError("找不到可用中文字体")

    # 1. 高分辨率渲染（抗锯齿），再最近邻缩小到像素网格
    font_big = pygame.font.Font(path, NATIVE_H)
    txt = font_big.render(TITLE, True, (255, 255, 255))  # 先渲染白色做模板
    w, h = txt.get_size()

    # 像素网格尺寸：按 PIXEL_CELL 缩
    grid_w = max(1, w // PIXEL_CELL)
    grid_h = max(1, h // PIXEL_CELL)
    grid = pygame.transform.scale(txt, (grid_w, grid_h))  # 最近邻降采样 → 像素化

    # 2. 放大回原尺寸，得到硬边像素字
    pix = pygame.transform.scale(grid, (w, h))

    # 3. 上色 + 描边：以白色模板的 alpha 为 mask
    main = (200, 16, 46)      # 中国红
    edge = (40, 6, 12)        # 深红描边
    highlight = (255, 120, 130)  # 顶部高光（可选叠加）

    # 描边：把白色像素向四周扩展 3px 作为描边底色
    pad = 4
    canvas_w, canvas_h = w + pad * 2, h + pad * 2
    outline = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)
    # 先复制主体做描边（向 8 方向偏移绘制深色）
    for dx in range(-pad, pad + 1):
        for dy in range(-pad, pad + 1):
            if dx == 0 and dy == 0:
                continue
            outline.blit(pix, (pad + dx, pad + dy))
    # 描边着色：把非透明像素刷成 edge 色
    outline_px = pygame.surfarray.pixels_alpha(outline)
    outline_px[outline_px > 0] = 255
    del outline_px
    edge_surf = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)
    edge_surf.fill((*edge, 255))
    # 用 outline 的 alpha 作 mask 把 edge_surf 裁出来
    outline_mask = pygame.mask.from_surface(outline)
    edge_surf = outline_mask.to_surface(setcolor=(*edge, 255), unsetcolor=(0, 0, 0, 0))

    # 主体：白字模板 → 红色
    main_surf = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)
    mask = pygame.mask.from_surface(pix)
    main_surf = mask.to_surface(setcolor=(*main, 255), unsetcolor=(0, 0, 0, 0))
    # 主体向右下偏移，模拟立体
    main_surf_offset = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)
    main_surf_offset.blit(main_surf, (2, 2))

    # 合成：描边在下，主体在上
    result = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)
    result.blit(edge_surf, (0, 0))
    result.blit(main_surf_offset, (0, 0))

    return result


def main() -> int:
    surf = make_title()
    os.makedirs(OUT_DIR, exist_ok=True)
    pygame.image.save(surf, OUT_PATH)
    print(f"标题图已生成：{OUT_PATH}  ({surf.get_width()}x{surf.get_height()})")
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
