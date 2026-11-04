#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
refine_edges.py — 角色贴图边缘羽化批处理（第一层：去毛边/锯齿）

处理三步（只作用于 RGBA 通道，不改变像素风格）：
  1. 去品红残留：品红色 (R>180, G<120, B>180) 的像素 alpha 置 0，并把 RGB 中和为邻近色，消除晕边。
  2. alpha 腐蚀 1px：去除最外圈不稳定的半透明像素，收缩主体轮廓。
  3. alpha 高斯羽化：对 alpha 通道做高斯模糊，让边缘从硬阶跃变为连续渐变。

用法：
  python tools/refine_edges.py --dry-run            # 只报告，不改动
  python tools/refine_edges.py --apply              # 处理并写回 assets/characters
  python tools/refine_edges.py --out <dir>          # 输出到指定目录（不覆盖原图）
  python tools/refine_edges.py --report             # 输出处理前后量化对比

依赖：Pillow（pip install Pillow）。不依赖 pygame/scipy。
"""
import argparse
import colorsys
import os
import sys
from PIL import Image, ImageFilter

# 角色贴图根目录（相对本脚本的上级仓库）
CHAR_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "drumbeat-m0", "assets", "characters")

# 品红判定（HSV 色相法）。纯品红底为 #FF00FF：色相 300°、饱和度 1.0、亮度 1.0。
# 残留是品红与透明/角色的 alpha 混合，归一化后仍落在「高饱和 + 高亮 + 紫红色相」区间。
# 服装阴影（深紫/暗红）虽色相相近，但饱和度/亮度低，据此区分，避免误伤。
MAGENTA_HUE_MIN = 275   # 色相下限（度）
MAGENTA_HUE_MAX = 325   # 色相上限（度）
MAGENTA_SAT_MIN = 0.85  # 饱和度下限（接近纯色）
MAGENTA_VAL_MIN = 0.80  # 亮度下限（接近纯亮）

# 羽化半径（px）。像素风素材取 0.5~0.9，过大会导致轮廓发虚、武器尖端糊掉。
BLUR_RADIUS = 0.6
# 是否先做 alpha 腐蚀
ERODE = True


def is_magenta(r, g, b):
    """判定某像素是否为品红残留。r/g/b 为归一化到不透明状态的 RGB（0-255）。"""
    mx = max(r, g, b)
    if mx == 0:
        return False
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    hue = h * 360
    return (MAGENTA_HUE_MIN <= hue <= MAGENTA_HUE_MAX
            and s >= MAGENTA_SAT_MIN and v >= MAGENTA_VAL_MIN)


def refine(img: Image.Image) -> Image.Image:
    """对单张 RGBA 图做 去品红 → 腐蚀 → 羽化 → 再去品红，返回新图。

    顺序说明：
      - 先去品红：清掉原始素材自带的品红晕边（RGB 与 alpha 一并清零，防止后续羽化渗漏）。
      - 腐蚀 + 羽化：让边缘 alpha 从硬阶跃变为连续渐变。
      - 再去品红：羽化可能把边缘色扩散，最后再清一遍，确保输出无品红残留。
    """
    img = img.convert("RGBA")

    # 第一遍去品红
    _remove_magenta(img)

    # alpha 腐蚀 1px（软腐蚀）
    if ERODE:
        alpha = img.getchannel("A")
        eroded = alpha.filter(ImageFilter.MinFilter(3))
        img.putalpha(eroded)

    # alpha 高斯羽化
    alpha = img.getchannel("A")
    alpha = alpha.filter(ImageFilter.GaussianBlur(BLUR_RADIUS))
    img.putalpha(alpha)

    # 第二遍去品红（清掉羽化渗漏）
    _remove_magenta(img)

    return img


def _remove_magenta(img: Image.Image) -> None:
    """将品红残留像素的 RGB 与 alpha 一并清零。半透明像素先归一化 RGB 再判定。"""
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a <= 0:
                continue
            if a < 255:
                rn = min(255, int(r * 255 / a))
                gn = min(255, int(g * 255 / a))
                bn = min(255, int(b * 255 / a))
                if is_magenta(rn, gn, bn):
                    px[x, y] = (0, 0, 0, 0)
            elif is_magenta(r, g, b):
                px[x, y] = (0, 0, 0, 0)


def stats(img: Image.Image):
    """统计：不透明像素数、半透明像素数、品红残留数（口径与 _remove_magenta 一致）。"""
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    total = semi = magenta = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 0:
                total += 1
                if a < 255:
                    semi += 1
                if a < 255:
                    rn = min(255, int(r * 255 / a))
                    gn = min(255, int(g * 255 / a))
                    bn = min(255, int(b * 255 / a))
                    if is_magenta(rn, gn, bn):
                        magenta += 1
                elif is_magenta(r, g, b):
                    magenta += 1
    return total, semi, magenta


def collect():
    """返回 characters 下所有 png 的 (relpath, abspath)。"""
    out = []
    for root, _, files in os.walk(CHAR_DIR):
        for f in sorted(files):
            if f.lower().endswith(".png"):
                ab = os.path.join(root, f)
                rel = os.path.relpath(ab, CHAR_DIR)
                out.append((rel, ab))
    return out


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="只报告，不改动")
    g.add_argument("--apply", action="store_true", help="处理并写回原目录")
    g.add_argument("--out", metavar="DIR", help="输出到指定目录（不覆盖原图）")
    g.add_argument("--report", action="store_true", help="输出处理前后量化对比")
    args = ap.parse_args()

    files = collect()
    if not files:
        print("未找到任何角色贴图:", CHAR_DIR)
        sys.exit(1)

    if args.dry_run:
        print(f"DRY-RUN：将处理 {len(files)} 张贴图（不做任何改动）")
        for rel, ab in files:
            img = Image.open(ab)
            t, s, m = stats(img)
            print(f"  {rel:40s} 不透明={t:5d}  半透明={s:4d}  品红={m:3d}")
        print("\n未改动任何文件。用 --apply 或 --out 实际处理。")
        return

    if args.report:
        print(f"处理前后对比（{len(files)} 张）：")
        print(f"{'文件':40s} {'前 半透明':>10s} {'后 半透明':>10s} {'前 品红':>7s} {'后 品红':>7s}")
        for rel, ab in files:
            img = Image.open(ab)
            t0, s0, m0 = stats(img)
            r = refine(img)
            t1, s1, m1 = stats(r)
            print(f"{rel:40s} {s0:10d} {s1:10d} {m0:7d} {m1:7d}")
        return

    # --apply 或 --out
    out_root = args.out if args.out else None
    for rel, ab in files:
        img = Image.open(ab)
        r = refine(img)
        if out_root:
            dst = os.path.join(out_root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            r.save(dst)
        else:
            r.save(ab)
        print(f"  已处理: {rel}")
    if out_root:
        print(f"\n完成，输出到: {out_root}（原图未改动）")
    else:
        print(f"\n完成，已写回原目录。共 {len(files)} 张。")


if __name__ == "__main__":
    main()
