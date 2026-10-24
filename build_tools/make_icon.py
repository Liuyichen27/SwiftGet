"""生成应用图标 app.ico（开发期一次性脚本）。"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "app.ico"

SIZE = 256
BLUE = (47, 107, 255, 255)
BLUE_DARK = (30, 87, 224, 255)
WHITE = (255, 255, 255, 255)


def rounded_rect(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def make_icon() -> Image.Image:
    scale = 4
    s = SIZE * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    # 背景：垂直渐变 + 圆角遮罩
    pad = int(s * 0.045)
    grad = Image.new("RGBA", (s, s))
    gd = ImageDraw.Draw(grad)
    top, bottom = (88, 146, 255), (36, 92, 226)
    for y in range(s):
        t = y / max(1, s - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        gd.line([(0, y), (s, y)], fill=(*color, 255))

    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (pad, pad, s - pad, s - pad), radius=int(s * 0.24), fill=255
    )
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)

    # 向下箭头（速降）
    cx = s // 2
    head_top = int(s * 0.22)
    head_bottom = int(s * 0.50)
    shaft_w = int(s * 0.115)
    head_w = int(s * 0.30)

    d.rectangle(
        (cx - shaft_w // 2, head_top, cx + shaft_w // 2, int(s * 0.44)), fill=WHITE
    )
    d.polygon(
        [
            (cx - head_w // 2, head_bottom - int(s * 0.09)),
            (cx + head_w // 2, head_bottom - int(s * 0.09)),
            (cx, head_bottom),
        ],
        fill=WHITE,
    )

    # 底部速度条
    bar_y = int(s * 0.66)
    bar_h = int(s * 0.075)
    bar_r = bar_h // 2
    d.rounded_rectangle(
        (int(s * 0.26), bar_y, int(s * 0.74), bar_y + bar_h), radius=bar_r, fill=WHITE
    )
    d.rounded_rectangle(
        (int(s * 0.26), bar_y + int(s * 0.135), int(s * 0.56), bar_y + int(s * 0.135) + bar_h),
        radius=bar_r, fill=(255, 255, 255, 150),
    )

    return img.resize((SIZE, SIZE), Image.LANCZOS)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    icon = make_icon()
    icon.save(
        OUT,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    png = OUT.with_suffix(".png")
    icon.save(png)
    print(f"icon written: {OUT} ({OUT.stat().st_size} bytes)")
    print(f"preview: {png}")


if __name__ == "__main__":
    main()
