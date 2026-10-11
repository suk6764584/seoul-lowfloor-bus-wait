"""분석보고서에 넣을 그림 넉 장.

  그림 1  보유율이 정류장에서 갈라지는 길 (좁혀 들어가는 단계와 숫자)
  그림 2  서울 정류장의 저상 유효 배차 지도
  그림 3  정류장에 서는 노선이 몇 개인가 — 하나뿐인 정류장이 다 떠안는다
  그림 4  차를 더 사지 않고 옮기기만 할 때 불리한 정류장이 줄어드는 모습

숫자는 전부 out/facts.json 과 out/*.csv 에서 읽는다. 손으로 옮겨 적지 않는다.

실행: python projects/koreashe_traffic_2026/build_figures.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch   # noqa: E402

base = Path(__file__).resolve().parents[1]
out = base / "figures"
src = base / "out"

INK = "#15243A"
DIM = "#64748B"
ACC = "#1F6F8B"
WARM = "#C2410C"
GOOD = "#15803D"
LINE = "#CBD5E1"
BAND = "#EEF4F8"
BAND2 = "#FDF3EC"

for f in ("Malgun Gothic", "AppleGothic", "NanumGothic"):
    if any(f == x.name for x in matplotlib.font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = f
        break
plt.rcParams.update({"axes.unicode_minus": False, "savefig.facecolor": "white",
                     "figure.dpi": 200, "savefig.dpi": 200})

NL = chr(10)


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, fill="white", edge=LINE, lw=1.1, pad=0.008):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad={pad}",
                                linewidth=lw, edgecolor=edge, facecolor=fill))


def arrow(ax, x1, y1, x2, y2, color=ACC, lw=1.7):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=13, linewidth=lw, color=color,
                                 shrinkA=1, shrinkB=1))


def save(fig, name):
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / name, bbox_inches="tight", pad_inches=.15)
    plt.close(fig)
    print(f"-> {name}")


# ──────────────────────────────────────────────────────────────────────────
def fig1(F):
    """한 숫자에서 시작해 불리한 정류장까지 좁혀 들어가는 단계."""
    n, s, b = F["노선"], F["정류장"], F["배차"]
    fig, ax = canvas(9.4, 7.0)
    ax.text(.012, .978, f"「보유율 {n['보유율']:.1%}」는 어디서 갈라지는가",
            fontsize=15.5, fontweight="bold", color=INK, va="top")
    ax.text(.012, .926,
            "차량 → 노선 → 정류장으로 내려갈 때마다 숨어 있던 차이가 드러난다",
            fontsize=9.8, color=DIM, va="top")

    steps = [
        ("① 차량으로 세면",
         f"서울 시내버스 저상버스 보유율   {n['보유율']:.1%}" + NL
         + f"저상 {n['저상대수']:,}대 / 인가 {n['인가대수']:,}대 · "
           f"노선 {n['맞물린노선']}개",
         BAND, ACC),
        ("② 노선으로 내려가면",
         "노선별 보유율은  0% 에서 100% 까지" + NL
         + f"중앙 {n['보유율중앙']:.0%} · 100% 인 노선 {n['보유율100']}개 · "
           f"50% 미만 {n['보유율50미만']}개 · 0% 인 노선 {n['보유율0']}개",
         BAND, ACC),
        ("③ 이용자가 서는 정류장에서 재면",
         f"저상버스 유효 배차(출퇴근 시간)   중앙 {b['혼잡_저상_중앙']:.1f}분" + NL
         + f"전체 버스는 {b['혼잡_전체_중앙']:.1f}분인데 저상은 "
           f"{F['배수']['중앙']:.2f}배 · 상위 10% 정류장은 "
           f"{b['혼잡_저상_상위10']:.0f}분",
         BAND, ACC),
        ("④ 30분을 넘거나 아예 없는 곳",
         f"불리한 정류장   {s['불리한정류장']}곳 "
         f"(전체 {s['계산']:,}곳의 {s['불리비율']:.1%})" + NL
         + f"30분 이상 {s['혼잡30분이상']}곳 · "
           f"저상이 한 대도 서지 않는 곳 {s['저상없음']}곳",
         BAND2, WARM),
    ]
    y, hb, gap = .876, .118, .032
    for k, (tag, text, fill, edge) in enumerate(steps):
        y -= hb
        box(ax, .012, y, .976, hb, fill=fill, edge=edge, lw=1.2)
        ax.text(.034, y + hb - .028, tag, fontsize=9.4, color=edge,
                fontweight="bold", va="center")
        ax.text(.034, y + hb * .35, text, fontsize=10.4, color=INK,
                va="center", linespacing=1.8)
        if k < len(steps) - 1:
            arrow(ax, .075, y - .004, .075, y - gap + .006, color=edge)
            y -= gap

    one = F["노선수별"]["1개"]
    rb = F["재배치"]["같은회사"]
    y -= .072
    hc = .178
    box(ax, .012, y - hc, .478, hc, edge=WARM, lw=1.3)
    ax.text(.036, y - hc / 2,
            f"그 {s['불리한정류장']}곳 가운데 "
            f"{one['불리']}곳({one['불리'] / s['불리한정류장']:.0%})은" + NL
            + "정류장에 서는 노선이 하나뿐인 곳이다." + NL
            + "옆에 기댈 다른 노선이 없다.",
            fontsize=10.6, color=INK, va="center", linespacing=1.9)
    box(ax, .510, y - hc, .478, hc, edge=GOOD, lw=1.3)
    ax.text(.534, y - hc / 2,
            "차를 더 사지 않고 같은 운수회사 안에서" + NL
            + f"저상차 {rb['옮긴대수']}대(전체의 {rb['비율']:.1%})만 옮기면" + NL
            + f"불리한 정류장 {rb['처음30분이상']}곳 → {rb['끝30분이상']}곳",
            fontsize=10.6, color=INK, va="center", linespacing=1.9)

    ax.text(.012, y - hc - .044,
            "자료  서울시 저상버스 노선별 보유율(2025-04) · 서울시 버스노선별 정류소 "
            "정보(2026-09) · 서울 TOPIS 버스 인가현황(2026-09)",
            fontsize=8.6, color=DIM)
    save(fig, "그림1_보유율이_갈라지는_길.png")


def fig2(F, rows):
    """정류장 지도. 색이 짙을수록 저상버스를 오래 기다린다."""
    fig, ax = plt.subplots(figsize=(9.4, 7.0))
    live = [r for r in rows if r["혼잡_저상"]]
    dead = [r for r in rows if not r["혼잡_저상"]]
    ok = [r for r in live if r["혼잡_저상"] < 30]
    bad = [r for r in live if r["혼잡_저상"] >= 30]

    sc = ax.scatter([r["lon"] for r in ok], [r["lat"] for r in ok],
                    c=[min(r["혼잡_저상"], 20) for r in ok], s=7,
                    cmap="YlGnBu", vmin=0, vmax=20, linewidths=0, alpha=.85)
    ax.scatter([r["lon"] for r in bad], [r["lat"] for r in bad],
               s=26, facecolor="none", edgecolor=WARM, linewidths=1.0,
               label=f"출퇴근 시간에도 30분 이상 {len(bad)}곳")
    ax.scatter([r["lon"] for r in dead], [r["lat"] for r in dead],
               s=34, marker="x", color="#7F1D1D", linewidths=1.3,
               label=f"저상버스가 한 대도 서지 않음 {len(dead)}곳")

    cb = fig.colorbar(sc, ax=ax, fraction=.030, pad=.012)
    cb.set_label("저상버스 유효 배차(분)" + NL + "20분에서 끊음",
                 fontsize=9.0, color=INK, labelpad=8)
    cb.ax.tick_params(labelsize=8.6)
    ax.set_title(f"서울 정류장 {F['정류장']['계산']:,}곳 — "
                 "탈 수 있는 버스는 몇 분마다 오는가",
                 fontsize=14.2, fontweight="bold", color=INK, pad=12, loc="left")
    ax.legend(loc="lower left", fontsize=9.2, frameon=True, framealpha=.95)
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color(LINE)
    ax.set_aspect(1 / 0.79)
    gu = F["자치구"]
    top = list(gu.items())[:3]
    zero = [k for k, v in gu.items() if v["불리"] == 0][:4]
    ax.text(.012, -.042,
            "불리한 정류장이 몰린 곳   "
            + " · ".join(f"{k} {v['불리']}/{v['정류장']}곳" for k, v in top)
            + "        없는 곳   " + " · ".join(zero),
            transform=ax.transAxes, fontsize=9.2, color=DIM)
    save(fig, "그림2_정류장_지도.png")


def fig3(F):
    """노선 수가 적을수록 불리하다."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.4, 3.9))
    d = F["노선수별"]
    ks = list(d)
    mid = [d[k]["저상중앙"] for k in ks]
    rat = [d[k]["불리비율"] * 100 for k in ks]
    cnt = [d[k]["정류장"] for k in ks]

    bars = a1.bar(ks, mid, color=[WARM if m >= 10 else ACC for m in mid], width=.62)
    for bb, m, c in zip(bars, mid, cnt):
        a1.text(bb.get_x() + bb.get_width() / 2, m + .35, f"{m:.1f}분",
                ha="center", fontsize=9.6, color=INK, fontweight="bold")
        a1.text(bb.get_x() + bb.get_width() / 2, .35, f"{c:,}곳",
                ha="center", fontsize=8.4, color="white")
    a1.set_title("저상버스 유효 배차 (중앙값)", fontsize=11.4, color=INK, loc="left")
    a1.set_ylabel("분", fontsize=9.6, color=DIM, rotation=0, labelpad=12)

    bars = a2.bar(ks, rat, color=[WARM if r > 1 else "#A7C3D4" for r in rat],
                  width=.62)
    for bb, r in zip(bars, rat):
        a2.text(bb.get_x() + bb.get_width() / 2, r + .35,
                f"{r:.1f}%" if r else "0", ha="center", fontsize=9.6,
                color=INK, fontweight="bold")
    a2.set_title("불리한 정류장의 비율", fontsize=11.4, color=INK, loc="left")
    a2.set_ylabel("%", fontsize=9.6, color=DIM, rotation=0, labelpad=12)

    for ax in (a1, a2):
        ax.set_xlabel("정류장에 서는 노선 수", fontsize=9.6, color=DIM)
        ax.grid(axis="y", color=LINE, linewidth=.6, alpha=.7)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=9.2, colors=INK)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(LINE)
    fig.suptitle("노선이 하나뿐인 정류장이 불리한 자리를 거의 다 떠안는다",
                 fontsize=14.0, fontweight="bold", color=INK, x=.012, ha="left",
                 y=1.04)
    save(fig, "그림3_노선수별.png")


def fig4(F, same, anyo):
    """옮긴 대수에 따라 불리한 정류장이 줄어드는 모습."""
    fig, ax = plt.subplots(figsize=(9.4, 4.0))
    start = F["정류장"]["불리한정류장"]
    for mv, color, label, z, dash in (
            (anyo, ACC, "회사 경계를 넘어 옮길 때", 2, None),
            (same, GOOD, "같은 운수회사 안에서만 옮길 때", 4, (0, (5, 2)))):
        xs = [0] + [int(m["순서"]) for m in mv]
        ys = [start] + [int(m["30분이상"]) for m in mv]
        ax.plot(xs, ys, color=color, linewidth=2.3, label=label, zorder=z,
                **({"linestyle": dash} if dash else {}))
        ax.scatter([xs[-1]], [ys[-1]], color=color, s=40, zorder=z + 1)
        ax.annotate(f"{xs[-1]}대 → {ys[-1]}곳", (xs[-1], ys[-1]),
                    textcoords="offset points",
                    xytext=(-104, 26) if color == ACC else (10, 10),
                    fontsize=10.4, color=color, fontweight="bold")
    ax.axhline(start, color=WARM, linewidth=1.1, linestyle=(0, (4, 3)))
    ax.text(3, start + 3, f"지금  {start}곳", fontsize=10.0, color=WARM,
            fontweight="bold")
    ax.set_xlabel(f"옮긴 저상버스 대수 (서울 시내버스 저상차 "
                  f"{F['노선']['저상대수']:,}대 가운데)", fontsize=9.8, color=DIM)
    ax.set_ylabel("불리한 정류장 수", fontsize=9.8, color=DIM)
    ax.set_title("차를 더 사지 않고 옮기기만 해도 줄어든다",
                 fontsize=14.0, fontweight="bold", color=INK, loc="left", pad=11)
    ax.legend(fontsize=9.6, frameon=False, loc="center right",
              bbox_to_anchor=(1.0, .62))
    ax.grid(color=LINE, linewidth=.6, alpha=.7)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=9.2, colors=INK)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(LINE)
    ax.set_ylim(0, start * 1.14)
    ax.set_xlim(-4, max(len(same), len(anyo)) * 1.06)
    save(fig, "그림4_재배치_효과.png")


def fig5(F):
    """한 장으로 보는 요약. 숫자 넉 장과 전·후."""
    n, s, b, r = F["노선"], F["정류장"], F["배차"], F["재배치"]
    one = F["노선수별"]["1개"]
    fig, ax = canvas(9.4, 3.6)
    ax.text(.012, .965, "한 장으로 보는 요약", fontsize=14.6, fontweight="bold",
            color=INK, va="top")
    ax.text(.012, .885, "서울 시내버스 저상버스를 정류장에서 다시 쟀다",
            fontsize=9.8, color=DIM, va="top")

    cards = [
        (f"{n['보유율']:.1%}", "서울 시내버스" + NL + "저상버스 보유율", ACC),
        (f"{b['혼잡_저상_중앙']:.1f}분", "정류장에서 저상버스를 기다리는" + NL
         + f"시간(중앙) · 전체 버스는 {b['혼잡_전체_중앙']:.1f}분", ACC),
        (f"{s['불리한정류장']}곳", "30분을 넘거나" + NL + "저상이 아예 서지 않는 정류장", WARM),
        (f"{one['불리'] / s['불리한정류장']:.0%}", "그 가운데" + NL
         + "노선이 하나뿐인 정류장", WARM),
    ]
    w, gapx = .228, .020
    for i, (big, small, col) in enumerate(cards):
        x = .012 + i * (w + gapx)
        box(ax, x, .315, w, .455, fill=BAND if col == ACC else BAND2,
            edge=col, lw=1.2)
        ax.text(x + w / 2, .655, big, ha="center", va="center", fontsize=21,
                fontweight="bold", color=col)
        ax.text(x + w / 2, .440, small, ha="center", va="center", fontsize=8.7,
                color=INK, linespacing=1.7)

    rb, ra = r["같은회사"], r["회사무관"]
    box(ax, .012, .055, .976, .205, fill="white", edge=GOOD, lw=1.3)
    ax.text(.034, .158,
            f"차를 더 사지 않고 옮기기만 하면   같은 운수회사 안에서 "
            f"{rb['옮긴대수']}대 → {rb['처음30분이상']}곳이 {rb['끝30분이상']}곳으로",
            fontsize=11.0, color=INK, va="center", fontweight="bold")
    ax.text(.034, .092,
            f"회사 경계를 넘어 교환까지 허용하면   {ra['옮긴대수']}대 → "
            f"{ra['끝30분이상']}곳 (저상차 {n['저상대수']:,}대의 {ra['비율']:.1%})",
            fontsize=10.2, color=DIM, va="center")
    save(fig, "그림5_요약.png")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    F = json.loads((src / "facts.json").read_text(encoding="utf-8"))
    with (src / "stop_lowfloor.csv").open(encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if float(r["커버리지"]) >= .7]
    for r in rows:
        r["lon"], r["lat"] = float(r["lon"]), float(r["lat"])
        r["혼잡_저상"] = float(r["혼잡_저상"]) if r["혼잡_저상"] else None
    with (src / "reallocation.csv").open(encoding="utf-8-sig") as f:
        same = list(csv.DictReader(f))
    with (src / "reallocation_anyowner.csv").open(encoding="utf-8-sig") as f:
        anyo = list(csv.DictReader(f))

    fig1(F)
    fig2(F, rows)
    fig3(F)
    fig4(F, same, anyo)
    fig5(F)


if __name__ == "__main__":
    main()
