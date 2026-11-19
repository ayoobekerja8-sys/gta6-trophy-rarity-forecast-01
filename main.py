import json
import math
import os
import re
import sys
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


def stamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def line_fit(xs, ys):
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else 0.0
    return my - slope * mx, slope


def safe_logit(p):
    p = min(1.0 - 1e-12, max(1e-12, p))
    return math.log(p / (1.0 - p))


def round4(value):
    return float(Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def forecast(case):
    release = datetime.combine(date.fromisoformat(case["game"]["release_date"]), datetime.min.time(), timezone.utc)
    target = stamp(case["target"])
    target_h = max(0.0, (target - release).total_seconds() / 3600.0)
    history = case["history"]
    snapshots = []
    for read in history:
        read = dict(read)
        read["hours"] = max(0.0, (stamp(read["at"]) - release).total_seconds() / 3600.0)
        if snapshots and read["players_tracked"] == snapshots[-1]["players_tracked"] and read["rates"] == snapshots[-1]["rates"]:
            snapshots[-1] = read
        else:
            snapshots.append(read)

    px = [math.log1p(s["hours"]) for s in snapshots]
    players = [float(s["players_tracked"]) for s in snapshots]
    if len(set(players)) >= 2:
        intercept, slope = line_fit(px, [math.log(p) for p in players])
        flat_players = False
    else:
        last_h = snapshots[-1]["hours"]
        slope = 4.0 if last_h < 12 else (1.0 if last_h < 48 else 0.5)
        intercept = math.log(players[-1]) - slope * math.log1p(last_h)
        flat_players = True
    last_players = players[-1]
    pred_players = math.exp(intercept + slope * math.log1p(target_h))
    pred_players = min(50.0 * last_players, max(last_players, pred_players))

    horizon_days = case["horizon_minutes"] / 1440.0
    horizon = case["horizon_minutes"]
    trophies = case["trophies"]
    rows = []
    for i, trophy in enumerate(trophies):
        obs = []
        for s in snapshots:
            rate = s["rates"][i]
            if rate is not None:
                obs.append((s["hours"], float(rate) * s["players_tracked"] / 100.0))
        if not obs:
            obs = [(snapshots[-1]["hours"], 0.0)]
        vals = [e for _, e in obs]
        max_e = max(vals)
        fallback = len(obs) < 3 or all(e == vals[0] for e in vals)
        fit_sd = 0.7
        if not fallback:
            fit_x = [math.log1p(t) for t, e in obs if e > 0]
            fit_e = [e for _, e in obs if e > 0]
            if len(fit_x) < 2:
                fallback = True
            else:
                lower = max(max_e * 1.2, 1e-9)
                upper = max(pred_players, lower)
                best = None
                for k in range(12):
                    c = lower if upper == lower else math.exp(math.log(lower) + (math.log(upper) - math.log(lower)) * k / 11.0)
                    ys = [safe_logit((e + 0.5) / (c + 0.5)) for e in fit_e]
                    a, b = line_fit(fit_x, ys)
                    residuals = [y - (a + b * x) for x, y in zip(fit_x, ys)]
                    sse = sum(r * r for r in residuals)
                    if best is None or sse < best[0]:
                        best = (sse, c, a, b, residuals)
                sse, c, a, b, residuals = best
                fit_sd = math.sqrt(sse / len(residuals)) if residuals else 0.0
                e_target = c / (1.0 + math.exp(max(-700.0, min(700.0, -(a + b * math.log1p(target_h))))))
        if fallback:
            last_e = vals[-1]
            e_target = last_e * (1.0 + 0.5 * horizon_days)
        e_target = min(pred_players, max(0.0, e_target))
        last_rate = snapshots[-1]["rates"][i]
        if last_rate == 100:
            rowq = [98.0, 99.5, 100.0, 100.0, 100.0]
        else:
            median = min(99.99, max(0.01, 100.0 * e_target / pred_players))
            s_rw = 0.5 * math.sqrt(horizon_days)
            s_prior = 0.5 if flat_players or fallback else 0.3
            spread = min(2.0, max(0.8, math.sqrt(s_rw * s_rw + fit_sd * fit_sd + s_prior * s_prior)))
            last_earners = float(last_rate) * snapshots[-1]["players_tracked"] / 100.0 if last_rate is not None else 0.0
            if last_earners < 10:
                spread = max(1.2, spread)
            z = (-1.645, -0.674, 0.0, 0.674, 1.645)
            ml = safe_logit(median / 100.0)
            rowq = [round4(100.0 / (1.0 + math.exp(max(-700.0, min(700.0, -(ml + v * spread)))))) for v in z]
            rowq.sort()
        rows.append({"id": int(trophy["id"]), "q": rowq})

    by_id = {int(t["id"]): idx for idx, t in enumerate(trophies)}

    def cap_row(idx, bounds):
        rows[idx]["q"] = [min(v, bound) for v, bound in zip(rows[idx]["q"], bounds)]
        rows[idx]["q"].sort()

    chapter = []
    for idx, t in enumerate(trophies):
        m = re.fullmatch(r"Complete Chapter (\d+)", t.get("description", ""))
        if m:
            chapter.append((int(m.group(1)), idx))
    chapter.sort()
    for j in range(1, len(chapter)):
        cap_row(chapter[j][1], rows[chapter[j - 1][1]]["q"])
    final_idxs = [idx for idx, t in enumerate(trophies) if t.get("description", "").lower() == "complete the final mission."]
    if chapter:
        for idx in final_idxs:
            cap_row(idx, rows[chapter[-1][1]]["q"])
    completion = [idx for idx, t in enumerate(trophies) if t.get("description", "").lower() == "attain 100% completion."]
    platinums = [idx for idx, t in enumerate(trophies) if t.get("tier") == "platinum"]
    for idx in completion:
        if platinums:
            cap_row(idx, rows[platinums[0]]["q"])
    for idx in platinums:
        peers = [r["q"] for j, r in enumerate(rows) if j != idx]
        if peers:
            cap_row(idx, [min(q[level] for q in peers) for level in range(5)])
    return {"trophies": rows}


def main():
    input_dir = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    for source in sorted(input_dir.glob("*.in"), key=lambda p: p.name):
        case = json.loads(source.read_text(encoding="utf-8"))
        result = forecast(case)
        payload = json.dumps(result, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        (output_dir / (source.stem + ".out")).write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
