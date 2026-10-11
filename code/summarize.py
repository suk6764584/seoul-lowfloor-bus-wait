"""보고서와 그림이 쓸 숫자를 한 군데서 만들어 JSON 으로 떨군다.

본문에 숫자를 손으로 옮겨 적으면 분석을 고칠 때마다 어긋난다. 여기서 한 번 계산해
`out/facts.json` 에 두고, 보고서도 그림도 그 파일만 읽는다.

실행: python projects/koreashe_traffic_2026/summarize.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze as A                           # noqa: E402

CITY_HALL = (126.9784, 37.5667)


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * p))]


def km(lon, lat):
    dx = (lon - CITY_HALL[0]) * 88.8          # 위도 37.5도에서 경도 1도 ≈ 88.8km
    dy = (lat - CITY_HALL[1]) * 111.0
    return math.hypot(dx, dy)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    low, routes = A.load_lowfloor(), A.load_routes()
    both = sorted(set(low) & set(routes))

    rows = []
    with (A.out_dir / "stop_lowfloor.csv").open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            r["커버리지"] = float(r["커버리지"])
            if r["커버리지"] < A.MIN_COVER:
                continue
            r["lon"], r["lat"] = float(r["lon"]), float(r["lat"])
            r["혼잡_전체"] = float(r["혼잡_전체"])
            r["한산_전체"] = float(r["한산_전체"])
            r["혼잡_저상"] = float(r["혼잡_저상"]) if r["혼잡_저상"] else None
            r["한산_저상"] = float(r["한산_저상"]) if r["한산_저상"] else None
            r["도심거리"] = km(r["lon"], r["lat"])
            rows.append(r)

    live = [r for r in rows if r["혼잡_저상"] is not None]
    dead = [r for r in rows if r["혼잡_저상"] is None]
    over30 = [r for r in live if r["혼잡_저상"] >= 30]

    f = {}
    f["기준"] = {"저상자료": "2025-04-25", "노선·정류소": "2026-09",
                 "허용오차분": A.MIN_COVER}
    f["노선"] = {
        "맞물린노선": len(both),
        "인가대수": sum(low[k]["인가"] for k in both),
        "저상대수": sum(low[k]["저상"] for k in both),
        "보유율": sum(low[k]["저상"] for k in both) / sum(low[k]["인가"] for k in both),
        "보유율0": sum(1 for k in both if low[k]["보유율"] == 0),
        "보유율50미만": sum(1 for k in both if low[k]["보유율"] < .5),
        "보유율100": sum(1 for k in both if low[k]["보유율"] >= .999),
        "보유율중앙": pct([low[k]["보유율"] for k in both], .5),
    }
    f["정류장"] = {
        "계산": len(rows), "저상없음": len(dead),
        "혼잡30분이상": len(over30),
        "불리한정류장": len(dead) + len(over30),
        "불리비율": (len(dead) + len(over30)) / len(rows),
    }
    rp = [r["혼잡_저상"] / r["혼잡_전체"] for r in live]
    f["배수"] = {"중앙": pct(rp, .5), "상위25": pct(rp, .75), "상위10": pct(rp, .9),
                 "상위5": pct(rp, .95), "상위1": pct(rp, .99), "최대": max(rp)}
    f["배차"] = {
        "혼잡_전체_중앙": pct([r["혼잡_전체"] for r in live], .5),
        "혼잡_저상_중앙": pct([r["혼잡_저상"] for r in live], .5),
        "혼잡_저상_상위10": pct([r["혼잡_저상"] for r in live], .9),
        "한산_저상_중앙": pct([r["한산_저상"] for r in live if r["한산_저상"]], .5),
        "한산_저상_상위10": pct([r["한산_저상"] for r in live if r["한산_저상"]], .9),
    }

    # 도심에서 멀어질수록. 좌표만으로 가르므로 다른 자료가 필요 없다.
    band, bad = defaultdict(list), defaultdict(int)
    for r in live:
        band[min(5, int(r["도심거리"] // 3))].append(r)
        if r["혼잡_저상"] >= 30:
            bad[min(5, int(r["도심거리"] // 3))] += 1
    for r in dead:
        bad[min(5, int(r["도심거리"] // 3))] += 1
        band[min(5, int(r["도심거리"] // 3))]
    f["도심거리"] = {
        (f"{i*3}~{i*3+3}km" if i < 5 else "15km 밖"): {
            "정류장": len(v) + 0,
            "저상중앙": pct([x["혼잡_저상"] for x in v], .5) if v else None,
            "배수중앙": pct([x["혼잡_저상"] / x["혼잡_전체"] for x in v], .5) if v else None,
            "불리": bad[i],
            "불리비율": bad[i] / (len(v) + bad[i] - sum(1 for x in v if x["혼잡_저상"] >= 30))
            if v else None,
        } for i, v in sorted(band.items())
    }

    # 자치구별. 정류소 고유번호 앞 세 자리가 자치구다(analyze.GU).
    g, gd = defaultdict(list), defaultdict(int)
    for r in live:
        g[r["gu"]].append(r)
    for r in dead:
        gd[r["gu"]] += 1
    f["자치구"] = {
        k: {"정류장": len(v) + gd[k],
            "저상중앙": pct([x["혼잡_저상"] for x in v], .5),
            "배수중앙": pct([x["혼잡_저상"] / x["혼잡_전체"] for x in v], .5),
            "불리": gd[k] + sum(1 for x in v if x["혼잡_저상"] >= 30)}
        for k, v in g.items()
    }
    f["자치구"] = dict(sorted(f["자치구"].items(),
                              key=lambda kv: -kv[1]["불리"] / kv[1]["정류장"]))

    # 정류장에 서는 노선이 몇 개인가. 한 노선뿐이면 기댈 데가 없다.
    nb = defaultdict(list)
    for r in live:
        nb[min(5, int(r["노선수"]))].append(r)
    nbd = defaultdict(int)
    for r in dead:
        nbd[min(5, int(r["노선수"]))] += 1
    f["노선수별"] = {
        (f"{k}개" if k < 5 else "5개 이상"): {
            "정류장": len(v) + nbd[k],
            "저상중앙": pct([x["혼잡_저상"] for x in v], .5),
            "불리": nbd[k] + sum(1 for x in v if x["혼잡_저상"] >= 30),
            "불리비율": (nbd[k] + sum(1 for x in v if x["혼잡_저상"] >= 30))
            / (len(v) + nbd[k]),
        } for k, v in sorted(nb.items())
    }

    worst = sorted(live, key=lambda r: -r["혼잡_저상"])[:15]
    f["최악정류장"] = [
        {"이름": r["name"], "노선수": int(r["노선수"]),
         "전체": r["혼잡_전체"], "저상": r["혼잡_저상"],
         "자치구": r["gu"], "도심거리": round(r["도심거리"], 1)} for r in worst]
    f["저상없음정류장"] = [
        {"이름": r["name"], "노선수": int(r["노선수"]),
         "전체": r["혼잡_전체"], "도심거리": round(r["도심거리"], 1)}
        for r in sorted(dead, key=lambda r: r["혼잡_전체"])[:10]]

    # 재배치
    for tag, name in (("", "같은회사"), ("_anyowner", "회사무관")):
        p = A.out_dir / f"reallocation{tag}.csv"
        if not p.exists():
            continue
        with p.open(encoding="utf-8-sig") as fh:
            mv = list(csv.DictReader(fh))
        base = float(mv[0]["남은초과"]) + float(mv[0]["줄인분"])
        f.setdefault("재배치", {})[name] = {
            "옮긴대수": len(mv),
            "비율": len(mv) / f["노선"]["저상대수"],
            "처음초과": round(base),
            "남은초과": float(mv[-1]["남은초과"]),
            "초과감소": 1 - float(mv[-1]["남은초과"]) / base,
            "처음30분이상": f["정류장"]["불리한정류장"],
            "끝30분이상": int(mv[-1]["30분이상"]),
        }

    (A.out_dir / "facts.json").write_text(
        json.dumps(f, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(f, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
