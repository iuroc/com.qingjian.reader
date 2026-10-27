#!/usr/bin/env python3
"""离线生成 iApp 工程图标（纯标准库，不联网、不依赖 Pillow）。

风格：圆角渐变底 + 大字徽章（标题里的数字/英文）。
中文等无 ASCII 的标题退回品类符号（计算器/文件夹/地球/笔记/聊天…）。

用法：
  python make_icon.py --out icon.png --title 2048 --package com.demo.game2048
  python make_icon.py --project-dir D:/iAppWorkspace/sync/ProjectApp/com.demo.calc
  python make_icon.py --all D:/iAppWorkspace/sync/ProjectApp

可覆盖：
  --category auto|game|calc|browser|file|note|chat|camera|music|video|weather|shop|health|tool|default
  --text auto|none|2048
  --color '#BBADA0'
  --size 512
"""
import argparse
import math
import os
import re
import struct
import sys
import zlib
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------- PNG

def _chunk(typ, data):
    return (struct.pack(">I", len(data)) + typ + data
            + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))


def write_png(path, size, buf):
    stride = size * 4
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        raw += buf[y * stride:(y + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------- 颜色

def hex_rgb(s):
    s = s.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def darken(c, f):
    return tuple(int(round(v * f)) for v in c)


def luminance(c):
    return (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255.0


PALETTES = {
    # category: (bg 顶, bg 底, 前景)
    "game":    ("#EDE0C8", "#D9C3A0", "#776E65"),
    "calc":    ("#1B1B20", "#0B0B0D", "#F5D67B"),
    "browser": ("#3B82F6", "#1E40AF", "#FFFFFF"),
    "file":    ("#38BDF8", "#0369A1", "#FFFFFF"),
    "note":    ("#FBBF24", "#D97706", "#3B2A12"),
    "chat":    ("#34D399", "#047857", "#FFFFFF"),
    "camera":  ("#8B5CF6", "#5B21B6", "#FFFFFF"),
    "music":   ("#F472B6", "#BE185D", "#FFFFFF"),
    "video":   ("#F87171", "#B91C1C", "#FFFFFF"),
    "weather": ("#38BDF8", "#1D4ED8", "#FFFFFF"),
    "shop":    ("#FB923C", "#C2410C", "#FFFFFF"),
    "health":  ("#F87171", "#B91C1C", "#FFFFFF"),
    "tool":    ("#94A3B8", "#475569", "#FFFFFF"),
    "default": ("#6366F1", "#3730A3", "#FFFFFF"),
}

KEYWORDS = [
    ("game",    ["game", "2048", "游戏", "棋", "puzzle", "play"]),
    ("calc",    ["calc", "计算", "算"]),
    ("browser", ["browser", "浏览", "web", "http"]),
    ("file",    ["file", "文件", "folder", "目录", "管理器", "mgr"]),
    ("note",    ["note", "笔记", "记事", "便签"]),
    ("chat",    ["chat", "聊天", "消息", "message"]),
    ("camera",  ["camera", "相机", "拍照", "photo"]),
    ("music",   ["music", "音乐", "audio", "播放器"]),
    ("video",   ["video", "视频", "movie", "影视"]),
    ("weather", ["weather", "天气"]),
    ("shop",    ["shop", "购物", "商城", "store"]),
    ("health",  ["health", "健康", "运动", "fitness"]),
    ("tool",    ["tool", "工具", "设置", "setting", "选择", "selector"]),
]


def detect_category(title, package):
    hay = ((title or "") + " " + (package or "")).lower()
    for cat, keys in KEYWORDS:
        for k in keys:
            if k in hay:
                return cat
    return "default"


def pick_text(title):
    s = title or ""
    runs = re.findall(r"\d+", s)
    if runs:
        return max(runs, key=len)[:4]
    words = re.findall(r"[A-Za-z]+", s)
    if words:
        if len(words) == 1 and len(words[0]) <= 4:
            return words[0].upper()
        initials = "".join(w[0] for w in words[:4]).upper()
        if len(initials) >= 2:
            return initials[:4]
        return words[0][:4].upper()
    return ""


def normalize_text(s):
    s = (s or "").upper()
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s[:4]


# ---------------------------------------------------------------- 几何

def clamp01(v):
    if v <= 0.0:
        return 0.0
    if v >= 1.0:
        return 1.0
    return v


def seg_dist2(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    l2 = vx * vx + vy * vy
    if l2 <= 0.0:
        return wx * wx + wy * wy
    t = (wx * vx + wy * vy) / l2
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    dx, dy = px - (ax + t * vx), py - (ay + t * vy)
    return dx * dx + dy * dy


def sd_circle(x, y, cx, cy, r):
    return math.hypot(x - cx, y - cy) - r


def sd_rrect(x, y, cx, cy, hw, hh, r):
    qx = abs(x - cx) - (hw - r)
    qy = abs(y - cy) - (hh - r)
    return (math.hypot(max(qx, 0.0), max(qy, 0.0))
            + min(max(qx, qy), 0.0) - r)


def sd_seg(x, y, ax, ay, bx, by, half):
    return math.sqrt(seg_dist2(x, y, ax, ay, bx, by)) - half


def sd_tri(x, y, ax, ay, bx, by, cx, cy):
    d1 = sd_seg(x, y, ax, ay, bx, by, 0.0)
    d2 = sd_seg(x, y, bx, by, cx, cy, 0.0)
    d3 = sd_seg(x, y, cx, cy, ax, ay, 0.0)
    d = min(d1, d2, d3)
    s1 = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
    s2 = (cx - bx) * (y - by) - (cy - by) * (x - bx)
    s3 = (ax - cx) * (y - cy) - (ay - cy) * (x - cx)
    if (s1 >= 0 and s2 >= 0 and s3 >= 0) or (s1 <= 0 and s2 <= 0 and s3 <= 0):
        return -d
    return d


def sd_ellipse(x, y, cx, cy, rx, ry):
    return (math.hypot((x - cx) / rx, (y - cy) / ry) - 1.0) * min(rx, ry)


def stroke_seg(mask, w, h, ax, ay, bx, by, half):
    x0 = max(0, int(math.floor(min(ax, bx) - half - 1)))
    x1 = min(w - 1, int(math.ceil(max(ax, bx) + half + 1)))
    y0 = max(0, int(math.floor(min(ay, by) - half - 1)))
    y1 = min(h - 1, int(math.ceil(max(ay, by) + half + 1)))
    for y in range(y0, y1 + 1):
        py = y + 0.5
        base = y * w
        for x in range(x0, x1 + 1):
            d = math.sqrt(seg_dist2(x + 0.5, py, ax, ay, bx, by))
            c = clamp01(half + 0.5 - d)
            if c > 0.0:
                i = base + x
                if c > mask[i]:
                    mask[i] = c


# ---------------------------------------------------------------- 笔画字体
# 坐标网格：x 0..4，y 0..6（0=顶，6=基线）
GLYPHS = {
    "0": [[(0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 1), (3, 0), (1, 0), (0, 1)]],
    "1": [[(0.8, 1.2), (1.7, 0.2), (1.7, 6)], [(0.6, 6), (2.8, 6)]],
    "2": [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 2.2), (0, 6), (4, 6)]],
    "3": [[(0, 0), (4, 0), (4, 2), (2, 2)], [(2, 2), (4, 2.2), (4, 5), (3, 6), (1, 6), (0, 5)]],
    "4": [[(3.2, 6), (3.2, 0.2), (0.2, 4.2), (3.9, 4.2)]],
    "5": [[(4, 0), (0, 0), (0, 2.4), (3, 2.4), (4, 3.4), (4, 5), (3, 6), (1, 6), (0, 5)]],
    "6": [[(4, 0.6), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 3.4), (3, 2.4), (0, 2.4)]],
    "7": [[(0, 0), (4, 0), (4, 1), (1.4, 6)]],
    "8": [[(1, 0), (3, 0), (4, 1), (4, 2), (3, 3), (1, 3), (0, 2), (0, 1), (1, 0)],
          [(1, 3), (3, 3), (4, 4), (4, 5), (3, 6), (1, 6), (0, 5), (0, 4), (1, 3)]],
    "9": [[(0, 5.4), (1, 6), (3, 6), (4, 5), (4, 1), (3, 0), (1, 0), (0, 1), (0, 2.6), (1, 3.6), (4, 3.6)]],
    "A": [[(0, 6), (0, 2), (2, 0), (4, 2), (4, 6)], [(0, 4), (4, 4)]],
    "B": [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)],
          [(3, 3), (4, 2), (4, 1), (3, 0), (0, 0)]],
    "C": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5)]],
    "D": [[(0, 0), (0, 6), (2, 6), (4, 4), (4, 2), (2, 0), (0, 0)]],
    "E": [[(4, 0), (0, 0), (0, 6), (4, 6)], [(0, 3), (3, 3)]],
    "F": [[(4, 0), (0, 0), (0, 6)], [(0, 3), (3, 3)]],
    "G": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 3), (2, 3)]],
    "H": [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    "I": [[(1, 0), (3, 0)], [(2, 0), (2, 6)], [(1, 6), (3, 6)]],
    "J": [[(4, 0), (4, 5), (3, 6), (1, 6), (0, 5)]],
    "K": [[(0, 0), (0, 6)], [(4, 0), (0, 3), (4, 6)]],
    "L": [[(0, 0), (0, 6), (4, 6)]],
    "M": [[(0, 6), (0, 0), (2, 2), (4, 0), (4, 6)]],
    "N": [[(0, 6), (0, 0), (4, 6), (4, 0)]],
    "O": [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)]],
    "P": [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)]],
    "Q": [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)],
          [(2.2, 4.2), (4.2, 6.2)]],
    "R": [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)], [(2, 3), (4, 6)]],
    "S": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 2), (1, 3), (3, 3), (4, 4), (4, 5), (3, 6), (1, 6), (0, 5)]],
    "T": [[(0, 0), (4, 0)], [(2, 0), (2, 6)]],
    "U": [[(0, 0), (0, 5), (1, 6), (3, 6), (4, 5), (4, 0)]],
    "V": [[(0, 0), (2, 6), (4, 0)]],
    "W": [[(0, 0), (1, 6), (2, 3), (3, 6), (4, 0)]],
    "X": [[(0, 0), (4, 6)], [(4, 0), (0, 6)]],
    "Y": [[(0, 0), (2, 3), (4, 0)], [(2, 3), (2, 6)]],
    "Z": [[(0, 0), (4, 0), (0, 6), (4, 6)]],
}


def text_mask(size, text):
    mask = [0.0] * (size * size)
    chars = [c for c in text if c in GLYPHS]
    if not chars:
        return mask, 0, 0, 0, 0
    gw, gh, gap = 4.0, 6.0, 1.15
    total_w = len(chars) * gw + (len(chars) - 1) * gap
    max_w = 0.72 * size
    max_h = 0.40 * size
    scale = min(max_w / total_w, max_h / gh)
    stroke_units = 0.95
    half = stroke_units * scale * 0.5
    x0 = (size - total_w * scale) * 0.5
    y0 = (size - gh * scale) * 0.5 - 0.015 * size

    for ci, ch in enumerate(chars):
        ox = x0 + ci * (gw + gap) * scale
        for poly in GLYPHS[ch]:
            pts = [(ox + px * scale, y0 + py * scale) for px, py in poly]
            for k in range(len(pts) - 1):
                ax, ay = pts[k]
                bx, by = pts[k + 1]
                stroke_seg(mask, size, size, ax, ay, bx, by, half)
    pad = int(half + 3)
    bx0 = max(0, int(x0 - pad))
    by0 = max(0, int(y0 - pad))
    bx1 = min(size - 1, int(x0 + total_w * scale + pad))
    by1 = min(size - 1, int(y0 + gh * scale + pad))
    return mask, bx0, by0, bx1, by1


# ---------------------------------------------------------------- 品类符号

def symbol_mask(size, cat):
    mask = [0.0] * (size * size)
    S = size * 0.56
    cx = cy = size * 0.5

    def P(u):
        return cx + (u - 0.5) * S

    def Q(v):
        return cy + (v - 0.5) * S

    def L(v):
        return v * S

    def sd(x, y):
        if cat == "game":
            return min(
                sd_rrect(x, y, P(0.33), Q(0.33), L(0.13), L(0.13), L(0.04)),
                sd_rrect(x, y, P(0.67), Q(0.33), L(0.13), L(0.13), L(0.04)),
                sd_rrect(x, y, P(0.33), Q(0.67), L(0.13), L(0.13), L(0.04)),
                sd_rrect(x, y, P(0.67), Q(0.67), L(0.13), L(0.13), L(0.04)),
            )
        if cat == "calc":
            w = L(0.030)
            body = abs(sd_rrect(x, y, cx, cy, L(0.34), L(0.38), L(0.08))) - w
            display = sd_rrect(x, y, P(0.5), Q(0.25), L(0.23), L(0.07), L(0.02))
            keys = min(
                sd_rrect(x, y, P(u), Q(v), L(0.055), L(0.045), L(0.015))
                for v in (0.47, 0.63) for u in (0.36, 0.50, 0.64)
            )
            wide = sd_rrect(x, y, P(0.5), Q(0.79), L(0.24), L(0.05), L(0.02))
            return min(body, display, keys, wide)
        if cat == "browser":
            w = L(0.030)
            ring = abs(sd_circle(x, y, cx, cy, L(0.34))) - w
            horiz = sd_seg(x, y, P(0.16), Q(0.5), P(0.84), Q(0.5), L(0.028))
            vert = abs(sd_ellipse(x, y, cx, cy, L(0.16), L(0.30))) - L(0.028)
            return min(ring, horiz, vert)
        if cat == "file":
            body = sd_rrect(x, y, P(0.5), Q(0.60), L(0.34), L(0.24), L(0.06))
            tab = sd_rrect(x, y, P(0.34), Q(0.32), L(0.19), L(0.08), L(0.05))
            return min(body, tab)
        if cat == "note":
            w = L(0.030)
            page = abs(sd_rrect(x, y, cx, cy, L(0.26), L(0.34), L(0.05))) - w
            l1 = sd_seg(x, y, P(0.36), Q(0.38), P(0.64), Q(0.38), L(0.028))
            l2 = sd_seg(x, y, P(0.36), Q(0.52), P(0.64), Q(0.52), L(0.028))
            l3 = sd_seg(x, y, P(0.36), Q(0.66), P(0.56), Q(0.66), L(0.028))
            return min(page, l1, l2, l3)
        if cat == "chat":
            bubble = sd_rrect(x, y, P(0.5), Q(0.44), L(0.32), L(0.22), L(0.10))
            tail = sd_tri(x, y, P(0.30), Q(0.60), P(0.24), Q(0.82), P(0.46), Q(0.64))
            return min(bubble, tail)
        if cat == "camera":
            w = L(0.030)
            body = abs(sd_rrect(x, y, P(0.5), Q(0.56), L(0.34), L(0.22), L(0.07))) - w
            lens = abs(sd_circle(x, y, P(0.5), Q(0.56), L(0.13))) - w
            bump = sd_rrect(x, y, P(0.42), Q(0.30), L(0.10), L(0.05), L(0.02))
            flash = sd_circle(x, y, P(0.72), Q(0.40), L(0.03))
            return min(body, lens, bump, flash)
        if cat == "music":
            head = sd_circle(x, y, P(0.38), Q(0.72), L(0.12))
            stem = sd_seg(x, y, P(0.50), Q(0.72), P(0.50), Q(0.22), L(0.030))
            flag = sd_seg(x, y, P(0.50), Q(0.22), P(0.70), Q(0.30), L(0.030))
            return min(head, stem, flag)
        if cat == "video":
            w = L(0.030)
            box = abs(sd_rrect(x, y, cx, cy, L(0.34), L(0.24), L(0.08))) - w
            tri = sd_tri(x, y, P(0.42), Q(0.34), P(0.42), Q(0.66), P(0.66), Q(0.50))
            return min(box, tri)
        if cat == "weather":
            sun = sd_circle(x, y, cx, cy, L(0.16))
            rays = min(
                sd_seg(x, y, P(0.5 + math.cos(a) * 0.25), Q(0.5 + math.sin(a) * 0.25),
                       P(0.5 + math.cos(a) * 0.36), Q(0.5 + math.sin(a) * 0.36), L(0.030))
                for a in [k * math.pi / 4 for k in range(8)]
            )
            return min(sun, rays)
        if cat == "shop":
            bag = sd_rrect(x, y, P(0.5), Q(0.62), L(0.28), L(0.22), L(0.05))
            handle = abs(sd_ellipse(x, y, P(0.5), Q(0.40), L(0.14), L(0.14))) - L(0.032)
            return min(bag, handle)
        if cat == "health":
            return min(
                sd_rrect(x, y, cx, cy, L(0.08), L(0.30), L(0.03)),
                sd_rrect(x, y, cx, cy, L(0.30), L(0.08), L(0.03)),
            )
        if cat == "tool":
            lines = min(
                sd_seg(x, y, P(0.20), Q(v), P(0.80), Q(v), L(0.028))
                for v in (0.30, 0.50, 0.70)
            )
            knobs = min(
                sd_circle(x, y, P(u), Q(v), L(0.07))
                for u, v in ((0.35, 0.30), (0.62, 0.50), (0.45, 0.70))
            )
            return min(lines, knobs)
        # default: 3x3 网格
        return min(
            sd_rrect(x, y, P(u), Q(v), L(0.065), L(0.065), L(0.018))
            for v in (0.28, 0.50, 0.72) for u in (0.28, 0.50, 0.72)
        )

    pad = int(S * 0.5) + 4
    x0 = max(0, int(cx - pad))
    x1 = min(size - 1, int(cx + pad))
    y0 = max(0, int(cy - pad))
    y1 = min(size - 1, int(cy + pad))
    for y in range(y0, y1 + 1):
        py = y + 0.5
        base = y * size
        for x in range(x0, x1 + 1):
            d = sd(x + 0.5, py)
            c = clamp01(0.5 - d)
            if c > 0.0:
                mask[base + x] = c
    return mask, x0, y0, x1, y1


# ---------------------------------------------------------------- 合成

def blend_px(buf, idx, r, g, b, a):
    o = idx * 4
    da = buf[o + 3] / 255.0
    oa = a + da * (1.0 - a)
    if oa <= 0.0:
        return
    buf[o] = int((r * a + buf[o] * da * (1.0 - a)) / oa)
    buf[o + 1] = int((g * a + buf[o + 1] * da * (1.0 - a)) / oa)
    buf[o + 2] = int((b * a + buf[o + 2] * da * (1.0 - a)) / oa)
    buf[o + 3] = int(oa * 255.0)


def draw_mask(buf, size, mask, x0, y0, x1, y1, fg):
    # 阴影：偏移 (3,4)px，黑色 18%
    for y in range(y0, y1 + 1):
        sy = y - 4
        if sy < 0 or sy >= size:
            continue
        for x in range(x0, x1 + 1):
            sx = x - 3
            if sx < 0 or sx >= size:
                continue
            a = mask[sy * size + sx] * 0.18
            if a > 0.0:
                blend_px(buf, y * size + x, 0, 0, 0, a)
    # 前景
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            a = mask[y * size + x]
            if a > 0.0:
                blend_px(buf, y * size + x, fg[0], fg[1], fg[2], a)


def generate_icon(out, title="", package="", category="auto", text="auto",
                  color=None, size=512):
    size = max(96, int(size))
    cat = category if category and category != "auto" else detect_category(title, package)
    if cat not in PALETTES:
        cat = "default"
    bg1s, bg2s, fgs = PALETTES[cat]
    if color:
        bg1 = hex_rgb(color)
        bg2 = darken(bg1, 0.72)
        fg = (255, 255, 255) if luminance(bg1) < 0.62 else (58, 58, 58)
    else:
        bg1, bg2, fg = hex_rgb(bg1s), hex_rgb(bg2s), hex_rgb(fgs)

    if text is None or (isinstance(text, str) and text.lower() == "auto"):
        txt = pick_text(title)
    elif isinstance(text, str) and text.lower() in ("none", "symbol", ""):
        txt = ""
    else:
        txt = normalize_text(text)

    # 背景
    buf = bytearray(size * size * 4)
    radius = 0.22 * size
    for y in range(size):
        t = y / (size - 1)
        base = lerp(bg1, bg2, t)
        for x in range(size):
            cov = clamp01(0.5 - sd_rrect(x + 0.5, y + 0.5, size / 2, size / 2,
                                         size / 2, size / 2, radius))
            if cov <= 0.0:
                continue
            hx = (x + 0.5 - 0.28 * size) / (0.60 * size)
            hy = (y + 0.5 - 0.18 * size) / (0.60 * size)
            hl = max(0.0, 1.0 - (hx * hx + hy * hy)) * 0.10
            o = (y * size + x) * 4
            buf[o] = min(255, int(base[0] + 255 * hl))
            buf[o + 1] = min(255, int(base[1] + 255 * hl))
            buf[o + 2] = min(255, int(base[2] + 255 * hl))
            buf[o + 3] = int(cov * 255)

    # 内容
    if txt:
        mask, x0, y0, x1, y1 = text_mask(size, txt)
    else:
        mask, x0, y0, x1, y1 = symbol_mask(size, cat)
    draw_mask(buf, size, mask, x0, y0, x1, y1, fg)

    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    write_png(out, size, buf)
    return {"out": out, "category": cat, "text": txt, "size": size}


# ---------------------------------------------------------------- 工程模式

def read_project_meta(project_dir):
    manifest = os.path.join(project_dir, "AndroidManifest.xml")
    title, pkg = "", os.path.basename(os.path.normpath(project_dir))
    if os.path.exists(manifest):
        try:
            root = ET.parse(manifest).getroot()
            title = (root.findtext("title") or "").strip()
            pkg = (root.findtext("packageName") or pkg).strip()
        except Exception as e:
            print(f"warn: 读 manifest 失败 {manifest}: {e}", file=sys.stderr)
    return title, pkg


def icon_for_project(project_dir, category="auto", text="auto", color=None, size=512):
    title, pkg = read_project_meta(project_dir)
    out = os.path.join(project_dir, "icon.png")
    info = generate_icon(out, title=title, package=pkg, category=category,
                         text=text, color=color, size=size)
    print(f"icon -> {out}  title={title!r} pkg={pkg} "
          f"category={info['category']} text={info['text']!r}")
    return info


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="离线生成 iApp 工程图标")
    ap.add_argument("--out", help="输出 PNG 路径")
    ap.add_argument("--title", default="", help="工程显示名")
    ap.add_argument("--package", default="", help="包名")
    ap.add_argument("--category", default="auto", help="品类或 auto")
    ap.add_argument("--text", default="auto", help="徽章文字或 auto/none")
    ap.add_argument("--color", default=None, help="背景色 #RRGGBB")
    ap.add_argument("--size", type=int, default=512, help="边长，默认 512")
    ap.add_argument("--project-dir", help="从工程目录读取 manifest 并写入 icon.png")
    ap.add_argument("--all", help="批量处理目录下的所有 iApp 工程")
    a = ap.parse_args()

    if a.all:
        root = a.all
        for name in sorted(os.listdir(root)):
            d = os.path.join(root, name)
            if os.path.isdir(d) and os.path.exists(os.path.join(d, "AndroidManifest.xml")):
                icon_for_project(d, a.category, a.text, a.color, a.size)
        return

    if a.project_dir:
        icon_for_project(a.project_dir, a.category, a.text, a.color, a.size)
        return

    if not a.out:
        ap.error("需要 --out / --project-dir / --all 之一")
    info = generate_icon(a.out, title=a.title, package=a.package,
                         category=a.category, text=a.text,
                         color=a.color, size=a.size)
    print(f"icon -> {info['out']}  category={info['category']} "
          f"text={info['text']!r} size={info['size']}")


if __name__ == "__main__":
    main()
