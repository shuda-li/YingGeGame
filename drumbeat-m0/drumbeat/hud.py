"""渲染层：世界、HUD、节拍可视化、判定调试面板与手感调节面板。

对应任务：T-D03（节拍可视化与合拍反馈）、T-E01（判定调试面板）、T-B03（手感面板的显示部分）。
M1 改造：M1-2 接入像素素材（缺图回退程序绘制）、M1-4 接入视差背景。
"""
from __future__ import annotations

import math

import pygame

from .assets import Assets
from .config import DATA, PIXELS_PER_UNIT, SCREEN_H, SCREEN_W

# 英歌脸谱配色：红 / 黑 / 白 / 金
RED = (200, 16, 46)
DARK = (18, 18, 20)
INK = (26, 26, 30)
WHITE = (242, 240, 230)
GOLD = (184, 134, 11)
GREY = (150, 150, 150)
DIM = (96, 96, 104)
ORANGE = (230, 110, 40)
BLUE = (70, 130, 180)
GREEN = (60, 160, 90)

GROUND_SCREEN_Y = SCREEN_H * 0.76

# 视差层配置：(素材键, 视差系数, 缩放, 锚点模式, 锚点参数, 平铺间距 px)
#   锚点 top  ：参数 = 内容顶部距屏幕顶的比例（0–1）
#   锚点 ground：参数 = 内容底部相对地面线的偏移（世界单位，正值抬高）
#   间距 None = 按自身宽度连续平铺
PARALLAX_LAYERS = [
    ("cloud1", 0.06, 1.00, "top", 0.06, None),
    ("far_new", 0.30, 0.50, "top", -0.50, None),
    ("mid", 0.55, 1.15, "ground", 0.35, None),
]
# L2「双龙出海」环境：far_L2 整幅暮色天空（走 far* 不裁剪分支）+ 抠天后的骑楼中景
PARALLAX_LAYERS_L2 = [
    ("far_L2", 0.30, 0.50, "top", -0.50, None),
    ("mid_L2", 0.55, 0.39, "ground", 0.35, None),
]
FOREGROUND_LAYER = ("fore", 1.35, 0.20, "top", 0.02, 760)


def load_font(size: int) -> pygame.font.Font:
    for name in ("microsoftyaheiui", "microsoftyahei", "simhei", "simsun", "notosanscjksc", "arialunicodems"):
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.SysFont(None, size)


class Camera:
    def __init__(self) -> None:
        self.x = 0.0

    def update(self, player, ratio: float) -> None:
        target = player.x + player.vx * ratio
        self.x += (target - self.x) * 0.12

    def to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        return int((wx - self.x) * PIXELS_PER_UNIT + SCREEN_W / 2), int(GROUND_SCREEN_Y - wy * PIXELS_PER_UNIT)


class Renderer:
    def __init__(self) -> None:
        self.font_s = load_font(16)
        self.font_m = load_font(20)
        self.font_l = load_font(30)
        self.font_xl = load_font(46)
        self.cam = Camera()
        self.assets = Assets()
        self._sky: pygame.Surface | None = None
        self._layers: dict[str, tuple | None] = {}
        self._anim_dist = 0.0
        self._last_px = 0.0

    # ------------------------------------------------------------------ 世界
    def draw_world(self, surf: pygame.Surface, level, player, combat) -> None:
        surf.fill((16, 14, 18))                       # 兜底底色：地平线以下与关卡范围外不留黑
        surf.blit(self._sky_surface(), (0, 0))
        layers = PARALLAX_LAYERS_L2 if getattr(level, "raw", {}).get("env") == "L2" else PARALLAX_LAYERS
        for cfg in layers:
            self._blit_layer(surf, self._prep_layer(*cfg))

        self._draw_tiled_solids(surf, level.ground_rects + level.platform_rects)
        for r in level.low_wall_rects:
            self._rect(surf, r.x, r.y, r.w, r.h, (120, 44, 40), (190, 70, 60))
        for r in level.hazard_rects:
            self._draw_spikes(surf, r)

        # 终点
        gx, gy = self.cam.to_screen(level.goal_x, 0.0)
        pygame.draw.rect(surf, GOLD, pygame.Rect(gx - 6, gy - 180, 12, 180))
        pygame.draw.polygon(surf, RED, [(gx + 6, gy - 180), (gx + 66, gy - 156), (gx + 6, gy - 132)])

        for e in level.enemies:
            self._draw_enemy(surf, e)
        self._draw_player(surf, player, combat)

        # 前景层画在角色之后，形成纵深遮挡
        self._blit_layer(surf, self._prep_layer(*FOREGROUND_LAYER))

    # ------------------------------------------------------------------ 背景
    def _sky_surface(self) -> pygame.Surface:
        """用天空素材的取色生成整屏竖直渐变（素材本身只有中间一条带）。"""
        if self._sky is not None:
            return self._sky
        h = int(GROUND_SCREEN_Y) + 4
        s = pygame.Surface((SCREEN_W, h))
        base = self.assets.env("sky")
        if base is None:
            s.fill((30, 30, 36))
            self._sky = s
            return s
        box = base.get_bounding_rect(1)
        top = self._row_color(base, box.top + 3, box)
        bot = self._row_color(base, box.bottom - 3, box)
        for y in range(h):
            t = y / max(1, h - 1)
            col = (int(top[0] + (bot[0] - top[0]) * t),
                   int(top[1] + (bot[1] - top[1]) * t),
                   int(top[2] + (bot[2] - top[2]) * t))
            pygame.draw.line(s, col, (0, y), (SCREEN_W, y))
        self._sky = s
        return s

    @staticmethod
    def _row_color(surf: pygame.Surface, y: int, box: pygame.Rect) -> tuple[int, int, int]:
        n = 5
        r = g = b = 0
        for i in range(n):
            x = box.left + int((i + 0.5) * box.width / n)
            c = surf.get_at((x, y))
            r += c[0]
            g += c[1]
            b += c[2]
        return (r // n, g // n, b // n)

    def _prep_layer(self, key: str, factor: float, scale: float, mode: str, param: float, spacing=None):
        """裁剪到内容范围并按需缩放，结果缓存（只在首次调用时计算）。"""
        if key in self._layers:
            return self._layers[key]
        rec = None
        src = self.assets.env(key)
        if src is not None:
            if key.startswith("far"):
                # 远景层是带透明天空的整幅背景，保留原画布位置，避免裁剪后变成浮空横条
                box = src.get_rect()
                crop = src
            else:
                box = src.get_bounding_rect(1)
                crop = src.subsurface(box) if box.width > 0 and box.height > 0 else None
            if crop is not None and box.width > 0 and box.height > 0:
                tile = self.assets.scaled(crop, int(crop.get_width() * scale), int(crop.get_height() * scale))
                if mode == "top":
                    y = int(param * SCREEN_H)
                else:
                    y = int(GROUND_SCREEN_Y - tile.get_height() + param * PIXELS_PER_UNIT)
                step = int(spacing) if spacing else tile.get_width()
                rec = (tile, y, factor, max(1, step))
        self._layers[key] = rec
        return rec

    def _blit_layer(self, surf: pygame.Surface, rec) -> None:
        """按视差滚动绘制背景层。

        相邻瓦片左右镜像拼接：拼接处两列像素来自同一图像数据，内容连续，因此看不出接缝。
        镜像奇偶用「世界锚定的瓦片序号」判断，保证镜头移动时不会突然翻转。
        """
        if rec is None:
            return
        tile, y, factor, step = rec
        if tile.get_width() < 1:
            return
        flip = self.assets.flipped(tile)
        off = self.cam.x * PIXELS_PER_UNIT * factor      # 该层对应的世界坐标偏移
        x = int((-off) % step) - step
        while x < SCREEN_W:
            k = math.floor((off + x) / step)
            surf.blit(flip if k % 2 else tile, (x, y))
            x += step

    def _draw_tiled_solids(self, surf: pygame.Surface, rects) -> None:
        tile = self.assets.env("ground")
        for r in rects:
            x, y = self.cam.to_screen(r.x, r.y + r.h)
            w = int(r.w * PIXELS_PER_UNIT)
            h = int(r.h * PIXELS_PER_UNIT)
            if w <= 0 or h <= 0:
                continue
            if tile is None:
                pygame.draw.rect(surf, (54, 48, 44), pygame.Rect(x, y, w, h))
                pygame.draw.rect(surf, (86, 76, 66), pygame.Rect(x, y, w, h), 2)
                continue
            tw = max(1, int(tile.get_width() * h / tile.get_height()))
            t = self.assets.scaled(tile, tw, h)
            clip = surf.get_clip()
            surf.set_clip(pygame.Rect(x, y, w, h))
            tx = x
            while tx < x + w:
                surf.blit(t, (tx, y))
                tx += tw
            surf.set_clip(clip)
            pygame.draw.rect(surf, (96, 120, 140), pygame.Rect(x, y, w, 3))

    def _rect(self, surf, wx, wy, ww, wh, fill, edge) -> None:
        x, y = self.cam.to_screen(wx, wy + wh)
        pygame.draw.rect(surf, fill, pygame.Rect(x, y, int(ww * PIXELS_PER_UNIT), int(wh * PIXELS_PER_UNIT)))
        pygame.draw.rect(surf, edge, pygame.Rect(x, y, int(ww * PIXELS_PER_UNIT), int(wh * PIXELS_PER_UNIT)), 2)

    def _draw_spikes(self, surf, r) -> None:
        n = max(2, int(r.w / 0.4))
        step = r.w / n
        for i in range(n):
            x0, y0 = self.cam.to_screen(r.x + i * step, r.y)
            x1, y1 = self.cam.to_screen(r.x + (i + 0.5) * step, r.y + r.h)
            x2, y2 = self.cam.to_screen(r.x + (i + 1) * step, r.y)
            pygame.draw.polygon(surf, ORANGE, [(x0, y0), (x1, y1), (x2, y2)])

    # ------------------------------------------------------------------ 角色
    def _blit_actor(self, surf: pygame.Surface, spr, x: int, y: int,
                    facing: int = 1, yscale: float = 1.0, tint=None) -> bool:
        """以「脚底中心」对齐绘制角色贴图；返回是否成功（False 表示缺图，需回退）。"""
        if spr is None:
            return False
        img = spr
        if yscale != 1.0:
            img = self.assets.scaled(img, img.get_width(), int(img.get_height() * yscale))
        if facing < 0:
            img = self.assets.flipped(img)
        if tint is not None:
            img = self.assets.tinted(img, tint)
        surf.blit(img, img.get_rect(midbottom=(x, y)))
        return True

    def _player_state(self, player, combat) -> tuple[str | None, int]:
        if player.dead:
            return "death", 0
        if combat.attack_id:
            return "attack", 0
        if not player.on_ground:
            return "air", 0
        if player.sliding:
            return "run", 0
        self._anim_dist += abs(player.x - self._last_px)
        self._last_px = player.x
        if abs(player.vx) > 0.4:
            return "run", int(self._anim_dist / 0.45) % 4
        return "run", 0        # 缺 idle 素材，暂以跑动首帧站立

    def _draw_player(self, surf: pygame.Surface, player, combat) -> None:
        x, y = self.cam.to_screen(player.x, player.y)
        state, frame = self._player_state(player, combat)
        spr = self.assets.player(state, frame) if state else None
        tint = (70, 55, 0) if player.invincible else None
        yscale = 0.55 if player.sliding else 1.0
        if not self._blit_actor(surf, spr, x, y, player.facing, yscale, tint):
            self._draw_player_fallback(surf, player)

        # 攻击判定框提示（便于调参）
        if combat.attack_id and combat.phase in ("active", "startup"):
            box = combat.hitbox(player)
            bx, by = self.cam.to_screen(box.x, box.y + box.h)
            color = GOLD if combat.phase == "active" else DIM
            pygame.draw.rect(surf, color, pygame.Rect(bx, by, int(box.w * PIXELS_PER_UNIT), int(box.h * PIXELS_PER_UNIT)), 2)

    def _draw_player_fallback(self, surf: pygame.Surface, player) -> None:
        x, y = self.cam.to_screen(player.x, player.y + player.height)
        w = int(player.WIDTH * PIXELS_PER_UNIT)
        h = int(player.height * PIXELS_PER_UNIT)
        body = WHITE
        if player.invincible:
            body = (255, 230, 160) if int(player.invincible_t * 20) % 2 == 0 else WHITE
        pygame.draw.rect(surf, body, pygame.Rect(x - w // 2, y, w, h), border_radius=4)
        pygame.draw.rect(surf, DARK, pygame.Rect(x - w // 2, y, w, h), 2, border_radius=4)
        pygame.draw.rect(surf, RED, pygame.Rect(x - w // 2, y, w, int(h * 0.22)))
        f = 1 if player.facing > 0 else -1
        pygame.draw.circle(surf, GOLD, (x + f * int(w * 0.22), y + int(h * 0.38)), 3)

    def _draw_enemy(self, surf: pygame.Surface, e) -> None:
        x, y = self.cam.to_screen(e.x, e.y)
        if e.dead:
            if e.death_t > 0.8:
                return
            self._blit_actor(surf, self.assets.enemy("defeat", int(e.death_t / 0.12)), x, y, e.facing)
            return

        state = {"patrol": "walk", "startup": "attack1", "active": "attack2",
                 "recovery": "attack1", "stun": "block"}.get(e.state)
        tint = (140, 20, 20) if e.hit_flash_t > 0 else None
        if not self._blit_actor(surf, self.assets.enemy(state) if state else None, x, y, e.facing, 1.0, tint):
            self._draw_enemy_fallback(surf, e)

        w = int(e.w * PIXELS_PER_UNIT)
        # 血条
        bw = w + 12
        pygame.draw.rect(surf, (60, 20, 20), pygame.Rect(x - bw // 2, y - 160, bw, 5))
        pygame.draw.rect(surf, RED, pygame.Rect(x - bw // 2, y - 160, int(bw * e.hp / e.max_hp), 5))
        # 攻击前摇警示
        if e.state == "startup":
            prog = e.t / max(1e-6, e.startup_s)
            pygame.draw.rect(surf, ORANGE, pygame.Rect(x - 16, y - 186, int(32 * prog), 4))
            pygame.draw.circle(surf, ORANGE, (x, y - 196), 5)
        elif e.state == "active":
            hb = e.attack_hitbox()
            hx, hy = self.cam.to_screen(hb.x, hb.y + hb.h)
            pygame.draw.rect(surf, ORANGE, pygame.Rect(hx, hy, int(hb.w * PIXELS_PER_UNIT), int(hb.h * PIXELS_PER_UNIT)), 2)

    def _draw_enemy_fallback(self, surf: pygame.Surface, e) -> None:
        x, y = self.cam.to_screen(e.x, e.y + e.h)
        w = int(e.w * PIXELS_PER_UNIT)
        h = int(e.h * PIXELS_PER_UNIT)
        col = (200, 60, 60) if e.hit_flash_t > 0 else (168, 168, 172)
        if e.state == "stun":
            col = (120, 120, 200)
        pygame.draw.rect(surf, col, pygame.Rect(x - w // 2, y, w, h), border_radius=4)
        pygame.draw.rect(surf, DARK, pygame.Rect(x - w // 2, y, w, h), 2, border_radius=4)

    # ------------------------------------------------------------------ HUD
    def draw_hud(self, surf, player, energy, judgement, combat, music, elapsed, level) -> None:
        self._bar(surf, 24, 24, 240, 16, player.hp / float(DATA.combat["player_hp"]), RED, "生命")
        self._bar(surf, 24, 54, 240, 16, energy.ratio, GOLD, "鼓劲")
        if energy.full:
            pygame.draw.rect(surf, GOLD, pygame.Rect(22, 52, 244, 20), 2)

        t1 = self.font_m.render(f"槌花 {combat.hit_count}", True, WHITE)
        surf.blit(t1, (SCREEN_W - 40 - t1.get_width(), 24))
        t2 = self.font_m.render(f"用时 {elapsed:5.1f}s / 目标 {level.target_time_s:.0f}s", True, WHITE)
        surf.blit(t2, (SCREEN_W - 40 - t2.get_width(), 52))

        # 板式与合拍连段
        lay = self.font_m.render(f"{music.layer_name}  {music.bpm:.0f} BPM", True, GOLD if music.switch_flashing else WHITE)
        surf.blit(lay, (SCREEN_W - 40 - lay.get_width(), 80))
        st = self.font_m.render(f"合拍连段 {judgement.streak}", True, GOLD if judgement.streak >= 4 else GREY)
        surf.blit(st, (SCREEN_W - 40 - st.get_width(), 108))

        if energy.can_finish(judgement.streak):
            hint = self.font_m.render("满堂彩就绪 — 按 F", True, GOLD)
            surf.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 92))

        self._draw_beat_strip(surf, music)
        self._draw_judge_circle(surf, music, judgement)

    def _bar(self, surf, x, y, w, h, ratio, color, label) -> None:
        pygame.draw.rect(surf, (40, 40, 44), pygame.Rect(x, y, w, h), border_radius=3)
        pygame.draw.rect(surf, color, pygame.Rect(x, y, int(w * max(0.0, min(1.0, ratio))), h), border_radius=3)
        pygame.draw.rect(surf, (90, 90, 96), pygame.Rect(x, y, w, h), 1, border_radius=3)
        lab = self.font_s.render(label, True, WHITE)
        surf.blit(lab, (x + w + 10, y))

    def _draw_beat_strip(self, surf, music) -> None:
        """小节内 4 拍指示：第 1、3 拍为判定点（描金）。"""
        cx = SCREEN_W // 2
        y = 28
        gap = 46
        b = music.beat_in_bar(music.beat_pos)
        for i in range(DATA.bar_beats):
            x = cx - gap * 1.5 + i * gap
            is_judge = i in DATA.judge_offsets_in_bar
            near = abs(b - i) < 0.5 or abs(b - i - DATA.bar_beats) < 0.5
            r = 13 if is_judge else 9
            col = GOLD if is_judge else DIM
            if near:
                col = WHITE
                r += 3
            pygame.draw.circle(surf, col, (int(x), y), r, 2 if is_judge else 1)
            if is_judge:
                pygame.draw.circle(surf, GOLD, (int(x), y), 3)

    def _draw_judge_circle(self, surf, music, judgement) -> None:
        """锣钹形判定圈：随鼓点收缩，命中时闪反馈色。"""
        b = music.beat_pos
        beat_ms = 60000.0 / music.bpm
        base = int(b)
        cands = [c for c in (base, base + 1, base + 2, base + 3) if c % DATA.bar_beats in DATA.judge_offsets_in_bar]
        nxt = min(cands) if cands else base
        if nxt < b:
            nxt += DATA.bar_beats
        t_to = (nxt - b) * beat_ms / 1000.0
        interval = beat_ms * 2 / 1000.0
        prog = max(0.0, min(1.0, 1.0 - t_to / interval))

        cx, cy = SCREEN_W // 2, int(SCREEN_H * 0.62)
        r_out = 78
        r = int(r_out - (r_out - 26) * prog)
        col = GOLD
        flash = getattr(judgement, "_flash", None)
        if flash and flash[0] > 0:
            col = {"perfect": GOLD, "good": WHITE, "off": ORANGE}.get(flash[1], GOLD)
        pygame.draw.circle(surf, col, (cx, cy), r, 3)
        pygame.draw.circle(surf, DIM, (cx, cy), 22, 2)
        pygame.draw.circle(surf, col, (cx, cy), 8)

        if judgement.last is not None and getattr(judgement, "_flash", None) and judgement._flash[0] > 0:
            txt = {"perfect": "完美合拍", "good": "合拍", "off": "未合拍"}[judgement.last.grade]
            lab = self.font_l.render(txt, True, col)
            surf.blit(lab, (cx - lab.get_width() // 2, cy + 96))

    # ------------------------------------------------------------------ 面板
    def draw_debug_panel(self, surf, lines: list[str], title: str = "判定调试面板") -> None:
        pad = 10
        w = 470
        h = 24 + len(lines) * 20
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 185))
        surf.blit(panel, (16, SCREEN_H - h - 16))
        t = self.font_m.render(title, True, GOLD)
        surf.blit(t, (16 + pad, SCREEN_H - h - 16 + 4))
        for i, ln in enumerate(lines):
            s = self.font_s.render(ln, True, WHITE)
            surf.blit(s, (16 + pad, SCREEN_H - h - 16 + 26 + i * 20))

    def draw_feel_panel(self, surf, rows: list[tuple[str, str]], selected: int) -> None:
        w = 430
        h = 30 + len(rows) * 22
        x = SCREEN_W - w - 16
        y = 140
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 190))
        surf.blit(panel, (x, y))
        t = self.font_m.render("手感参数面板  [↑↓ 选择  ←→ 调整]", True, GOLD)
        surf.blit(t, (x + 10, y + 6))
        for i, (name, val) in enumerate(rows):
            col = WHITE if i == selected else GREY
            mark = "▶" if i == selected else " "
            s = self.font_s.render(f"{mark} {name:<22} {val}", True, col)
            surf.blit(s, (x + 10, y + 32 + i * 22))

    def draw_center_text(self, surf, main: str, sub: str = "", color=WHITE) -> None:
        m = self.font_xl.render(main, True, color)
        surf.blit(m, (SCREEN_W // 2 - m.get_width() // 2, SCREEN_H // 2 - 60))
        if sub:
            s = self.font_m.render(sub, True, GREY)
            surf.blit(s, (SCREEN_W // 2 - s.get_width() // 2, SCREEN_H // 2 + 6))

    def draw_help(self, surf, lines: list[str]) -> None:
        for i, ln in enumerate(lines):
            s = self.font_s.render(ln, True, GREY)
            surf.blit(s, (16, 150 + i * 20))
