using System;
using System.Collections.Generic;

namespace Kit.Perf
{
    // What to measure and how. Defaults follow plan §4.4 (D14).
    public sealed class PerfRunConfig
    {
        public string Feature;
        public string Label;
        // Groups the runs of one sweep; perf_analyze uses the latest session by default.
        public string Session = "";
        public string SweepParam = "";
        public double SweepValue;
        public int WarmupFrames = 100;
        public int MeasuredFrames = 300;
        public int Seed;
        // Name of the feature's own ProfilerMarker (category Scripts). Empty: not measured.
        public string FeatureMarker = "";
        public string Notes = "";
    }

    public sealed class PerfRunResult
    {
        public RunInfo Info;
        // FrameTiming series (ms). Same row = same frame.
        public List<double> MainMs = new List<double>();
        public List<double> RenderMs = new List<double>();
        public List<double> GpuMs = new List<double>();
        public List<double> CpuMs = new List<double>();
        // ProfilerRecorder series, a separate series (not row-aligned with the FrameTiming series).
        public List<double> FeatureMs = new List<double>();
        public List<double> GcBytes = new List<double>();
    }

    // Written to run.json (JsonUtility: public fields, no dictionaries).
    [Serializable]
    public sealed class MetricStats
    {
        public string name;
        public string unit;
        public int count;
        public double median;
        public double p95;
        public double min;
        public double max;
    }

    [Serializable]
    public sealed class RunInfo
    {
        public string feature;
        public string label;
        public string session;
        public string sweep_param;
        public double sweep_value;
        public int warmup_frames;
        public int measured_frames;
        public int seed;
        public string notes;
        public string timestamp_utc;
        public string git_commit;
        public bool git_dirty;
        public string unity_version;
        public string machine;
        public string gpu;
        public string resolution;
        public string quality_level;
        public bool editor;
        public int vsync_count_set;
        public int target_frame_rate_set;
        public bool frame_timing_enabled;
        public int timing_frames;
        public int recorder_frames;
        public bool gpu_valid;
        public List<MetricStats> metrics = new List<MetricStats>();
    }

    [Serializable]
    public sealed class IndexLine
    {
        public string timestamp_utc;
        public string run_dir;
        public string label;
        public double sweep_value;
        public double gpu_median_ms;
        public double main_median_ms;
        public double render_median_ms;
        public double feature_median_ms;
    }
}
