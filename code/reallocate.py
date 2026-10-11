"""저상버스를 더 사지 않고 **옮기기만** 하면 얼마나 좋아지는가.

analyze.py 가 보여 주는 것은 「어디가 나쁜가」까지다. 거기서 멈추면 지도 한 장으로
끝난다. 그래서 한 걸음 더 간다 — 이미 굴러다니는 저상버스를 노선 사이에서 옮겼을 때,
기다리는 시간이 가장 많이 줄어드는 배치를 찾는다.

옮기는 규칙은 현실을 따른다.
  · 차량 총수는 그대로다. 한 노선에서 저상차를 한 대 빼면 다른 노선에 한 대 넣는다.
  · **같은 운수회사 안에서만** 옮긴다. 차고지와 정비·인력이 회사에 묶여 있어서다.
  · 보유율이 1 을 넘거나 0 밑으로 내려가게는 옮기지 않는다.

줄이려는 값은 「기다림의 초과분」이다.

    J = Σ_정류장 max(0, 저상 유효배차 − 15분)

15분은 교통약자가 버스를 놓쳤을 때 견딜 만하다고 보는 선으로 잡았다. 이 값이 줄면
오래 기다리던 정류장이 실제로 줄어든다.

실행: python projects/koreashe_traffic_2026/reallocate.py
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze as A                           # noqa: E402

TOL = 15.0          # 이 분(分)을 넘는 기다림만 센다
CAP = 60.0          # 저상차가 아예 없는 정류장의 기다림을 이 값으로 끊는다
LIMIT = 400         # 옮겨 볼 최대 대수
SAME_OWNER = True   # False 면 회사 경계를 넘어서도 옮긴다(비교용)


def build():
    low, routes = A.load_lowfloor(), A.load_routes()
    info, served = A.load_stops()

    # 노선별 운수회사 (공동배차는 여럿)
    owner = defaultdict(set)
    for r in A.sheet(A.data / "d03_인가현황_202609.xlsx").iter_rows(min_row=2, values_only=True):
        if r[1] is None:
            continue
        owner[A.norm(r[1])].add(r[0])

    keys = sorted(set(low) & set(routes))
    idx = {k: i for i, k in enumerate(keys)}
    n = [low[k]["인가"] for k in keys]
    k_lf = [low[k]["저상"] for k in keys]
    h = [routes[k]["최소배차"] for k in keys]

    # 커버리지를 넘긴 정류장만 쓴다
    stops, stop_routes = [], []
    for node, rset in served.items():
        hit = [idx[r] for r in rset if r in idx]
        if not hit:
            continue
        cov_all = sum(1 / routes[r]["최소배차"] for r in rset if r in routes)
        cov_hit = sum(1 / h[i] for i in hit)
        if not cov_all or cov_hit / cov_all < A.MIN_COVER:
            continue
        stops.append(node)
        stop_routes.append(hit)

    by_route = defaultdict(list)
    for s, hit in enumerate(stop_routes):
        for i in hit:
            by_route[i].append(s)
    return keys, idx, n, k_lf, h, stops, stop_routes, by_route, owner, info


def wait(s, stop_routes, k_lf, n, h):
    rate = 0.0
    for i in stop_routes[s]:
        if k_lf[i]:
            rate += (k_lf[i] / n[i]) / h[i]
    return CAP if rate <= 0 else min(CAP, 1.0 / rate)


def main() -> None:
    global SAME_OWNER
    if "--any-owner" in sys.argv:
        SAME_OWNER = False
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    keys, idx, n, k_lf, h, stops, stop_routes, by_route, owner, info = build()
    print(f"노선 {len(keys)}개 · 정류장 {len(stops):,}곳")

    w = [wait(s, stop_routes, k_lf, n, h) for s in range(len(stops))]

    def excess(ws):
        return sum(max(0.0, x - TOL) for x in ws)

    def over(ws, t=30.0):
        return sum(1 for x in ws if x >= t)

    base_J, base_30 = excess(w), over(w)
    print(f"지금 — 15분 초과 기다림 합계 {base_J:,.0f}분 · "
          f"30분 이상 기다리는 정류장 {base_30:,}곳")

    def delta(i, dk):
        """노선 i 의 저상차를 dk 대 바꿨을 때 줄어드는 초과 기다림(+면 좋아짐)."""
        if not (0 <= k_lf[i] + dk <= n[i]):
            return None
        before = after = 0.0
        k_lf[i] += dk
        for s in by_route[i]:
            after += max(0.0, wait(s, stop_routes, k_lf, n, h) - TOL)
        k_lf[i] -= dk
        for s in by_route[i]:
            before += max(0.0, w[s] - TOL)
        return before - after

    moves = []
    for step in range(LIMIT):
        gains = [(delta(i, +1), i) for i in range(len(keys))]
        gains = [(g, i) for g, i in gains if g is not None and g > 0]
        if not gains:
            break
        gains.sort(reverse=True)
        best_g, dst = gains[0]

        harms = []
        for src in range(len(keys)):
            if src == dst or k_lf[src] < 1:
                continue
            if SAME_OWNER and not (owner[keys[src]] & owner[keys[dst]]):
                continue                      # 회사가 다르면 못 옮긴다
            d = delta(src, -1)
            if d is None:
                continue
            harms.append((-d, src))           # -d 가 손해(작을수록 좋다)
        if not harms:
            break
        harms.sort()
        harm, src = harms[0]
        if best_g - harm <= 1e-9:
            break

        k_lf[src] -= 1
        k_lf[dst] += 1
        for s in set(by_route[src]) | set(by_route[dst]):
            w[s] = wait(s, stop_routes, k_lf, n, h)
        moves.append({"순서": step + 1, "준노선": keys[src], "받은노선": keys[dst],
                      "회사": (sorted(owner[keys[src]] & owner[keys[dst]]) or [""])[0],
                      "줄인분": round(best_g - harm, 1),
                      "남은초과": round(excess(w), 0),
                      "30분이상": over(w)})
        if (step + 1) % 25 == 0:
            print(f"  {step + 1:3d}대 옮김 — 초과 {excess(w):,.0f}분 · "
                  f"30분 이상 {over(w):,}곳")

    print(f"\n옮긴 대수 {len(moves)}대 "
          f"(서울 시내버스 저상 {sum(A.load_lowfloor()[k]['저상'] for k in keys):,}대의 "
          f"{len(moves) / sum(A.load_lowfloor()[k]['저상'] for k in keys):.1%})")
    print(f"15분 초과 기다림 합계 {base_J:,.0f}분 → {excess(w):,.0f}분 "
          f"({1 - excess(w) / base_J:.1%} 줄어듦)")
    print(f"30분 이상 기다리는 정류장 {base_30:,}곳 → {over(w):,}곳")

    A.out_dir.mkdir(exist_ok=True)
    tag = "" if SAME_OWNER else "_anyowner"
    with (A.out_dir / f"reallocation{tag}.csv").open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(moves[0].keys()))
        wr.writeheader()
        wr.writerows(moves)
    print(f"-> reallocation{tag}.csv")

    got = defaultdict(int)
    gave = defaultdict(int)
    for m in moves:
        got[m["받은노선"]] += 1
        gave[m["준노선"]] += 1
    print("\n가장 많이 받은 노선")
    for rn, c in sorted(got.items(), key=lambda x: -x[1])[:8]:
        print(f"  {rn:<8} +{c}대")
    print("가장 많이 내준 노선")
    for rn, c in sorted(gave.items(), key=lambda x: -x[1])[:8]:
        print(f"  {rn:<8} -{c}대")


if __name__ == "__main__":
    main()
