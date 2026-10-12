"""Tests for perf_analyze.py: synthetic run logs with known answers.

Run: python -I -m unittest discover -s scripts/unity -p 'test_*.py'
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perf_analyze as pa  # noqa: E402


def run_main(args):
    """perf_analyze.main without its stdout summary, so test output stays readable."""
    with contextlib.redirect_stdout(io.StringIO()):
        return pa.main(args)


def write_run(feature_dir, label, n, stamp, gpu_ms, feature_ms=None, tamper=None, commit="abc", session="s1"):
    """One run with 300 frames: every frame of a metric is the metric's value +-0.01 (a fixed, symmetric pattern)."""
    run_dir = Path(feature_dir) / "runs" / f"{stamp}-{label}"
    run_dir.mkdir(parents=True)
    wobble = [(-0.01 if i % 2 else 0.01) for i in range(300)]
    cols = {"main_ms": 2 * gpu_ms, "render_ms": gpu_ms + 0.5, "gpu_ms": gpu_ms, "cpu_ms": 3 * gpu_ms}
    series = {k: [v + w for w in wobble] for k, v in cols.items()}
    rec = {"gc_alloc_bytes": [20000.0] * 300}
    if feature_ms is not None:
        rec["feature_ms"] = [feature_ms + w for w in wobble]

    (run_dir / "frames_timing.csv").write_text(
        "frame," + ",".join(pa.TIMING_COLUMNS) + "\n"
        + "".join(f"{i}," + ",".join(repr(series[c][i]) for c in pa.TIMING_COLUMNS) + "\n" for i in range(300)),
        encoding="utf-8")
    rec_cols = [c for c in pa.RECORDER_COLUMNS if c in rec]
    (run_dir / "frames_recorders.csv").write_text(
        "frame," + ",".join(rec_cols) + "\n"
        + "".join(f"{i}," + ",".join(repr(rec[c][i]) for c in rec_cols) + "\n" for i in range(300)),
        encoding="utf-8")

    metrics = []
    for name, values in {**series, **rec}.items():
        metrics.append({"name": name, "unit": "ms", "count": 300, "median": pa.median(values), "p95": pa.p95(values),
                        "min": min(values), "max": max(values)})
    if tamper:
        for m in metrics:
            if m["name"] == tamper:
                m["median"] += 0.5
    info = {"feature": Path(feature_dir).name, "label": label, "session": session, "sweep_param": "instances", "sweep_value": float(n),
            "warmup_frames": 100, "measured_frames": 300, "timestamp_utc": f"2026-10-12T08:00:{stamp[-2:]}Z",
            "git_commit": commit, "git_dirty": False, "unity_version": "6000.3.10f1", "machine": "m", "gpu": "g",
            "resolution": "1920x1080", "quality_level": "PC", "editor": True, "metrics": metrics}
    (run_dir / "run.json").write_text(json.dumps(info), encoding="utf-8")


def make_sweep(feature_dir, cost, points=(0, 1000, 3000, 6000, 10000, 50000, 100000), repeats=3, base_gpu=None):
    """gpu_ms = cost(n); baseline (n=0) first and last; the rest in a fixed interleaved order."""
    order = [0] + [n for _ in range(repeats) for n in points if n != 0] + [0]
    for i, n in enumerate(order):
        gpu = cost(n)
        if base_gpu and n == 0 and i == len(order) - 1:
            gpu = base_gpu
        write_run(feature_dir, f"sweep-n{n}-i{i}", n, f"{i:08d}", gpu, feature_ms=gpu / 2)


class StatsDefinitions(unittest.TestCase):
    def test_median_odd_even(self):
        self.assertEqual(pa.median([3, 1, 2]), 2)
        self.assertEqual(pa.median([4, 1, 3, 2]), 2.5)

    def test_p95_nearest_rank(self):
        values = list(range(1, 101))
        self.assertEqual(pa.p95(values), 95)
        self.assertEqual(pa.p95([5]), 5)
        self.assertEqual(pa.p95(list(range(1, 21))), 19)  # ceil(0.95 * 20) = 19

    def test_ols_exact_line(self):
        slope, intercept, r2 = pa.ols([0, 1, 2, 3], [1, 3, 5, 7])
        self.assertAlmostEqual(slope, 2)
        self.assertAlmostEqual(intercept, 1)
        self.assertAlmostEqual(r2, 1)


class Analysis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "toy"

    def tearDown(self):
        self.tmp.cleanup()

    def test_recovers_known_slope_and_fixed_cost(self):
        make_sweep(self.dir, lambda n: 0.5 + 0.02 * n / 1000)
        report = pa.analyze(self.dir, "sweep-")
        self.assertEqual(report["errors"], [])
        fit = report["fits"]["gpu_ms"]
        self.assertAlmostEqual(fit["per_1000"], 0.02, places=4)
        self.assertAlmostEqual(fit["intercept"], 0.5, places=3)
        self.assertGreater(fit["r2"], 0.999)
        self.assertEqual(fit["verdict"], "linear")
        self.assertEqual(report["runs_used"], 3 * 6 + 2)
        self.assertEqual(len(report["points"]), 7)
        self.assertAlmostEqual(report["fits"]["feature_ms"]["per_1000"], 0.01, places=4)

    def test_quadratic_cost_is_reported_not_linear(self):
        make_sweep(self.dir, lambda n: 0.5 + 0.02 * n / 1000 + 4e-7 * n * n / 1000)
        fit = pa.analyze(self.dir, "sweep-")["fits"]["gpu_ms"]
        self.assertEqual(fit["verdict"], "not linear")
        self.assertGreater(fit["upper_half_per_1000"], 1.5 * fit["lower_half_per_1000"])

    def test_csv_and_runjson_mismatch_is_an_error(self):
        make_sweep(self.dir, lambda n: 0.5 + 0.02 * n / 1000)
        write_run(self.dir, "sweep-n500-i99", 500, "00000099", 0.51, feature_ms=0.25, tamper="gpu_ms")
        report = pa.analyze(self.dir, "sweep-")
        self.assertTrue(any("gpu_ms median differs" in e for e in report["errors"]))
        self.assertEqual(run_main([str(self.dir)]), 2)

    def test_mixed_commits_is_an_error(self):
        make_sweep(self.dir, lambda n: 0.5 + 0.02 * n / 1000)
        write_run(self.dir, "sweep-n500-i98", 500, "00000098", 0.51, feature_ms=0.25, commit="other")
        self.assertTrue(any("git_commit" in e for e in pa.analyze(self.dir, "sweep-")["errors"]))

    def test_too_few_points_is_an_error(self):
        make_sweep(self.dir, lambda n: 1.0, points=(0, 1000), repeats=1)
        self.assertTrue(any("at least 3" in e for e in pa.analyze(self.dir, "sweep-")["errors"]))

    def test_fit_min_n_ignores_light_load_points(self):
        # Light-load points sit above the line (a GPU that has not ramped its clocks up); the loaded range is exact.
        def cost(n):
            return 0.5 + 0.02 * n / 1000 + (1.0 if n < 10000 else 0.0)
        make_sweep(self.dir, cost)
        self.assertEqual(pa.analyze(self.dir, "sweep-")["fits"]["gpu_ms"]["verdict"], "not linear")
        fit = pa.analyze(self.dir, "sweep-", fit_min_n=10000)["fits"]["gpu_ms"]
        self.assertAlmostEqual(fit["per_1000"], 0.02, places=4)
        self.assertEqual(fit["verdict"], "linear")
        self.assertEqual(len(pa.analyze(self.dir, "sweep-", fit_min_n=10000)["points"]), 7)

    def test_fit_min_n_from_feature_json_and_too_few_points(self):
        make_sweep(self.dir, lambda n: 0.5 + 0.02 * n / 1000)
        (self.dir / "feature.json").write_text(json.dumps({"fit_min_n": 50000}), encoding="utf-8")
        report = pa.analyze(self.dir, "sweep-")
        self.assertEqual(report["fit_min_n"], 50000)
        self.assertTrue(any("to fit" in e for e in report["errors"]))

    def test_latest_session_is_analyzed_by_default(self):
        make_sweep(self.dir, lambda n: 0.5 + 0.02 * n / 1000)  # session s1, runs 00000000..
        for i, n in enumerate((0, 10000, 20000, 30000)):
            write_run(self.dir, f"sweep-n{n}-i{i}", n, f"1{i:07d}", 1.0 + 0.1 * n / 1000, feature_ms=0.5,
                      commit="newer", session="s2")
        latest = pa.analyze(self.dir, "sweep-")
        self.assertEqual(latest["session"], "s2")
        self.assertEqual(latest["runs_used"], 4)
        self.assertAlmostEqual(latest["fits"]["gpu_ms"]["per_1000"], 0.1, places=4)
        self.assertEqual(latest["errors"], [])
        older = pa.analyze(self.dir, "sweep-", session="s1")
        self.assertEqual(older["runs_used"], 20)
        self.assertAlmostEqual(older["fits"]["gpu_ms"]["per_1000"], 0.02, places=4)

    def test_baseline_drift_is_reported(self):
        make_sweep(self.dir, lambda n: 0.5 + 0.02 * n / 1000, base_gpu=0.8)
        drift = pa.analyze(self.dir, "sweep-")["drift"]["gpu_ms"]
        self.assertAlmostEqual(drift["pct"], 60, places=0)

    def test_label_prefix_filters_runs(self):
        make_sweep(self.dir, lambda n: 0.5 + 0.02 * n / 1000)
        write_run(self.dir, "probe-n0-i0", 0, "00000097", 5.0, feature_ms=1.0)
        self.assertEqual(pa.analyze(self.dir, "sweep-")["runs_used"], 20)
        self.assertEqual(pa.analyze(self.dir, "")["runs_used"], 21)

    def test_budgets_pass_and_fail_and_exit_codes(self):
        make_sweep(self.dir, lambda n: 0.5 + 0.02 * n / 1000)
        budget = {"budgets": [{"metric": "gpu_ms", "kind": "per_1000", "max": 0.03},
                              {"metric": "gpu_ms", "kind": "total_at", "n": 50000, "max": 2.0}]}
        (self.dir / "feature.json").write_text(json.dumps(budget), encoding="utf-8")
        report = pa.analyze(self.dir, "sweep-")
        self.assertEqual([b["pass"] for b in report["budgets"]], [True, True])
        self.assertEqual(report["budgets"][1]["source"], "measured")
        self.assertEqual(run_main([str(self.dir)]), 0)

        budget["budgets"][0]["max"] = 0.01
        (self.dir / "feature.json").write_text(json.dumps(budget), encoding="utf-8")
        self.assertEqual(run_main([str(self.dir)]), 1)

    def test_total_at_uses_the_fit_when_the_point_was_not_measured(self):
        make_sweep(self.dir, lambda n: 0.5 + 0.02 * n / 1000)
        (self.dir / "feature.json").write_text(json.dumps(
            {"budgets": [{"metric": "gpu_ms", "kind": "total_at", "n": 20000, "max": 1.0}]}), encoding="utf-8")
        b = pa.analyze(self.dir, "sweep-")["budgets"][0]
        self.assertEqual(b["source"], "fit")
        self.assertAlmostEqual(b["value"], 0.9, places=2)
        self.assertTrue(b["pass"])


if __name__ == "__main__":
    unittest.main()
