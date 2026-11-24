#!/usr/bin/env python3
"""Render the report's UML-style interaction sequence using Matplotlib."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


OUT = Path(__file__).resolve().parents[1] / "rendered"
OUT.mkdir(parents=True, exist_ok=True)

participants = ["Користувач", "main()", "FileProcessor", "ShapeFactory",
                "Shape3D / похідний", "ResultWriter"]
x = [0.6, 2.2, 3.8, 5.4, 7.0, 8.6]
fig, ax = plt.subplots(figsize=(11, 6.4))
ax.set_xlim(0, 9.2)
ax.set_ylim(0, 7.2)
ax.axis("off")
for px, label in zip(x, participants):
    ax.add_patch(Rectangle((px-0.62, 6.55), 1.24, 0.42, fill=False, linewidth=1.0))
    ax.text(px, 6.76, label, ha="center", va="center", fontsize=11)
    ax.plot([px, px], [0.45, 6.55], linestyle=(0, (4, 3)), color="#64748b", linewidth=0.8)

def msg(src: int, dst: int, y: float, label: str, *, ret: bool = False) -> None:
    ax.annotate("", xy=(x[dst], y), xytext=(x[src], y),
                arrowprops={"arrowstyle": "->", "lw": 0.9,
                            "linestyle": "dashed" if ret else "solid", "color": "#334155"})
    ax.text((x[src]+x[dst])/2, y+0.10, label, ha="center", va="bottom", fontsize=10)

msg(0, 1, 6.1, "ввести шляхи до TXT")
msg(1, 2, 5.45, "process(inputPath)")
msg(2, 3, 4.8, "тип і параметри")
msg(3, 4, 4.15, "створити unique_ptr")
msg(2, 4, 3.5, "ratio(): віртуальні volume()/surfaceArea()")
msg(2, 2, 2.85, "перевірити й перейти до наступного рядка")
msg(2, 1, 2.2, "vector<RecordResult>", ret=True)
msg(1, 5, 1.55, "write(results, outputPath)")
msg(5, 0, 0.9, "однаковий звіт: консоль і файл", ret=True)
fig.tight_layout()
fig.savefig(OUT / "sequence-diagram.png", dpi=260, bbox_inches="tight", facecolor="white")
fig.savefig(OUT / "sequence-diagram.svg", bbox_inches="tight", facecolor="white")
plt.close(fig)
