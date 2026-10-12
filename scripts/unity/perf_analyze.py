#!/usr/bin/env python3
"""perf_analyze: read a feature's perf run logs, fit cost against the sweep value, check budgets.

Input : <feature-dir>/runs/*/{run.json,frames_timing.csv,frames_recorders.csv} (written by Kit.Perf, plan 4.4)
        <feature-dir>/feature.json (optional: budgets, fit_min_n)
Output: <feature-dir>/report.json and a short summary on stdout.
Exit  : 0 ok, 1 a budget failed, 2 bad or missing data (the report lists the errors).

Pure standard library, reads files only: it never talks to the Unity bridge (D11, D23).
Definitions match Kit.Perf.PerfStats: median = mean of the two middle values for an even count,
p95 = nearest rank (ceil(0.95 * n)-th smallest). All times are ms.
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

TIMING_COLUMNS = ["main_ms", "render_ms", "gpu_ms", "cpu_ms"]
RECORDER_COLUMNS = ["feature_ms", "gc_alloc_bytes"]
ALL_METRICS = TIMING_COLUMNS + RECORDER_COLUMNS
MATCH_TOLERANCE = 1e-9


def median(values):
    s = sorted(values)
    n = len(s)
    if n == 0:
        raise ValueError("median of empty series")
    return s[n // 2] if n % 2 == 1 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def p95(values):
    s = sorted(values)
    if not s:
        raise ValueError("p95 of empty series")
    return s[max(math.ceil(0.95 * len(s)) - 1, 0)]


def read_series(path, columns):
    """Columns of a CSV as lists of floats; empty cells (padding) are skipped."""
    series = {c: [] for c in columns}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for c in columns:
                cell = row.get(c)
                if cell not in (None, ""):
                    series[c].append(float(cell))
    return series


def load_run(run_dir, errors):
    info = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    series = {}
    series.update(read_series(run_dir / "frames_timing.csv", TIMING_COLUMNS))
    series.update(read_series(run_dir / "frames_recorders.csv", RECORDER_COLUMNS))

    stats = {}
    for metric, values in series.items():
        if values:
            stats[metric] = {"median": median(values), "p95": p95(values), "count": len(values)}

    # The C# summary and the CSV must agree: a mismatch means one of the two is wrong.
    for m in info.get("metrics", []):
        name = m["name"]
        if name not in stats:
            if m.get("count", 0) > 0:
                errors.append(f"{run_dir.name}: {name} in run.json but not in the CSV")
            continue
        for key in ("median", "p95"):
            a, b = stats[name][key], m[key]
            if abs(a - b) > MATCH_TOLERANCE * max(1.0, abs(a)):
                errors.append(f"{run_dir.name}: {name} {key} differs: csv {a!r} vs run.json {b!r}")
    return info, stats


def ols(xs, ys):
    """Least squares y = a + b*x. Returns (slope, intercept, r2)."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 if ss_tot == 0 else 1 - ss_res / ss_tot
    return slope, intercept, r2


def fit_metric(points, metric, r2_min, half_ratio_max):
    xs = [p["n"] for p in points if metric in p["metrics"]]
    ys = [p["metrics"][metric]["median"] for p in points if metric in p["metrics"]]
    if len(xs) < 3:
        return None
    slope, intercept, r2 = ols(xs, ys)
    half = (len(xs) + 1) // 2
    lower = ols(xs[:half], ys[:half])[0] if half >= 2 else None
    upper = ols(xs[-half:], ys[-half:])[0] if half >= 2 else None

    verdict, note = "linear", ""
    if r2 < r2_min:
        verdict, note = "not linear", f"R^2 {r2:.3f} < {r2_min}"
    elif lower and upper and lower > 0 and upper > 0:
        ratio = upper / lower
        if ratio > half_ratio_max or ratio < 1 / half_ratio_max:
            verdict, note = "not linear", f"upper/lower slope ratio {ratio:.2f}"
    return {
        "per_1000": slope * 1000,
        "intercept": intercept,
        "r2": r2,
        "lower_half_per_1000": None if lower is None else lower * 1000,
        "upper_half_per_1000": None if upper is None else upper * 1000,
        "verdict": verdict,
        "note": note,
    }


def analyze(feature_dir, label_prefix="", r2_min=0.98, half_ratio_max=1.5, fit_min_n=None, session=None):
    feature_dir = Path(feature_dir)
    errors = []
    runs = []
    for run_dir in sorted((feature_dir / "runs").glob("*")):
        if not (run_dir / "run.json").exists():
            continue
        info, stats = load_run(run_dir, errors)
        if not info["label"].startswith(label_prefix):
            continue
        runs.append({"dir": run_dir.name, "info": info, "stats": stats})

    # One analysis = one session (one sweep). Default: the session of the newest matching run.
    if runs and session is None:
        session = max(runs, key=lambda r: r["dir"])["info"].get("session", "")
    if runs:
        runs = [r for r in runs if r["info"].get("session", "") == session]

    if fit_min_n is None:
        fit_min_n = load_feature_config(feature_dir).get("fit_min_n")
    report = {"feature": feature_dir.name, "label_prefix": label_prefix, "session": session, "runs_used": len(runs), "fit_min_n": fit_min_n,
              "errors": errors, "points": [], "fits": {}, "drift": {}, "budgets": [], "conditions": {}}
    if not runs:
        errors.append("no runs found")
        return report

    report["sweep_param"] = runs[0]["info"].get("sweep_param", "")
    for key in ("git_commit", "git_dirty", "machine", "gpu", "resolution", "quality_level", "unity_version",
                "editor", "warmup_frames", "measured_frames"):
        values = sorted({str(r["info"].get(key)) for r in runs})
        report["conditions"][key] = values
        if len(values) > 1:
            errors.append(f"runs differ in {key}: {values}")

    by_n = {}
    for r in runs:
        by_n.setdefault(r["info"]["sweep_value"], []).append(r)

    for n in sorted(by_n):
        group = by_n[n]
        point = {"n": n, "runs": len(group), "metrics": {}}
        for metric in ALL_METRICS:
            medians = [g["stats"][metric]["median"] for g in group if metric in g["stats"]]
            p95s = [g["stats"][metric]["p95"] for g in group if metric in g["stats"]]
            if not medians:
                continue
            m = median(medians)
            point["metrics"][metric] = {
                "median": m,
                "p95": median(p95s),
                "run_spread_pct": 0.0 if m == 0 else (max(medians) - min(medians)) / abs(m) * 100,
            }
        report["points"].append(point)

    # Light loads can sit in a different hardware state (GPU clocks ramp down, Spike 003), so the fit may start at
    # fit_min_n. The excluded points stay in the report.
    fit_points = [p for p in report["points"] if fit_min_n is None or p["n"] >= fit_min_n]
    if len(fit_points) < 3:
        errors.append(f"need at least 3 distinct sweep values to fit, found {len(fit_points)}"
                      + ("" if fit_min_n is None else f" with n >= {fit_min_n}"))
    else:
        for metric in ALL_METRICS:
            fit = fit_metric(fit_points, metric, r2_min, half_ratio_max)
            if fit:
                report["fits"][metric] = fit

    # Drift: the lowest sweep value is the baseline; compare its first and last run in time order.
    baseline = sorted(by_n[min(by_n)], key=lambda r: r["info"]["timestamp_utc"] + r["dir"])
    if len(baseline) >= 2:
        for metric in ("main_ms", "render_ms", "gpu_ms", "feature_ms"):
            if metric in baseline[0]["stats"] and metric in baseline[-1]["stats"]:
                first = baseline[0]["stats"][metric]["median"]
                last = baseline[-1]["stats"][metric]["median"]
                if first != 0:
                    report["drift"][metric] = {"first": first, "last": last, "pct": (last - first) / abs(first) * 100}

    check_budgets(feature_dir, report)
    return report


def load_feature_config(feature_dir):
    cfg_path = Path(feature_dir) / "feature.json"
    return json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}


def check_budgets(feature_dir, report):
    cfg = load_feature_config(feature_dir)
    for b in cfg.get("budgets", []):
        metric, kind, limit = b["metric"], b["kind"], b["max"]
        entry = {"metric": metric, "kind": kind, "max": limit}
        if kind == "per_1000":
            fit = report["fits"].get(metric)
            entry["value"] = None if fit is None else fit["per_1000"]
            entry["source"] = "fit"
        elif kind == "total_at":
            n = b["n"]
            entry["n"] = n
            exact = [p for p in report["points"] if p["n"] == n and metric in p["metrics"]]
            if exact:
                entry["value"], entry["source"] = exact[0]["metrics"][metric]["median"], "measured"
            elif metric in report["fits"]:
                fit = report["fits"][metric]
                entry["value"], entry["source"] = fit["intercept"] + fit["per_1000"] * n / 1000, "fit"
            else:
                entry["value"], entry["source"] = None, "none"
        else:
            report["errors"].append(f"unknown budget kind {kind!r}")
            continue
        entry["pass"] = entry["value"] is not None and entry["value"] <= limit
        report["budgets"].append(entry)


def summary_lines(report):
    lines = [f"perf_analyze {report['feature']} session {report.get('session') or '-'}: {report['runs_used']} runs, "
             f"{len(report['points'])} sweep points ({report.get('sweep_param', '?')})"
             + ("" if report.get("fit_min_n") is None else f", fit on n >= {report['fit_min_n']:g}")]
    for metric in ("feature_ms", "gpu_ms", "render_ms", "main_ms"):
        fit = report["fits"].get(metric)
        if fit:
            lines.append(f"  {metric:<10} {fit['per_1000']:.4f} ms per 1000 +{fit['intercept']:.3f} ms fixed, "
                         f"R^2 {fit['r2']:.3f}, {fit['verdict']}" + (f" ({fit['note']})" if fit["note"] else ""))
    for metric, d in report["drift"].items():
        if abs(d["pct"]) > 10:
            lines.append(f"  WARNING baseline drift {metric}: {d['first']:.3f} -> {d['last']:.3f} ms ({d['pct']:+.0f}%)")
    for b in report["budgets"]:
        shown = "n/a" if b["value"] is None else f"{b['value']:.4f}"
        where = f" at {b['n']}" if "n" in b else ""
        lines.append(f"  budget {b['metric']} {b['kind']}{where}: {shown} <= {b['max']} -> {'PASS' if b['pass'] else 'FAIL'}")
    for e in report["errors"]:
        lines.append(f"  ERROR {e}")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("feature_dir", help="Perf/<feature> directory")
    ap.add_argument("--label-prefix", default="sweep-", help="only runs whose label starts with this (default sweep-)")
    ap.add_argument("--r2-min", type=float, default=0.98)
    ap.add_argument("--half-ratio-max", type=float, default=1.5)
    ap.add_argument("--session", default=None, help="session id of the sweep to analyze (default: the latest)")
    ap.add_argument("--fit-min-n", type=float, default=None,
                    help="fit only sweep values >= this (default: feature.json fit_min_n, else all)")
    args = ap.parse_args(argv)

    report = analyze(args.feature_dir, args.label_prefix, args.r2_min, args.half_ratio_max, args.fit_min_n, args.session)
    out = Path(args.feature_dir) / "report.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("\n".join(summary_lines(report)))
    if report["errors"]:
        return 2
    return 1 if any(not b["pass"] for b in report["budgets"]) else 0


if __name__ == "__main__":
    sys.exit(main())
