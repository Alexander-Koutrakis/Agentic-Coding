using System;
using System.Collections;
using Unity.Profiling;
using UnityEngine;

namespace Kit.Perf
{
    // Collects raw per-frame samples for one sweep point: warmup frames are discarded, then MeasuredFrames are
    // recorded. Writes nothing; PerfRunWriter does. Run it from a Play Mode test (run_tests), not manage_editor play.
    public static class PerfRunner
    {
        // FrameTimingManager results arrive 4 frames late (Unity manual, "Frame timing manager").
        const int FrameTimingLag = 4;
        const int DrainFrames = 8;
        const double NsToMs = 1e-6;

        public static IEnumerator Run(PerfRunConfig cfg, Action<PerfRunResult> done)
        {
            int oldVSync = QualitySettings.vSyncCount;
            int oldTarget = Application.targetFrameRate;
            QualitySettings.vSyncCount = 0;
            Application.targetFrameRate = -1;

            try
            {
                for (int i = 0; i < cfg.WarmupFrames; i++)
                {
                    FrameTimingManager.CaptureFrameTimings();
                    yield return null;
                }

                var result = new PerfRunResult();
                var buf = new FrameTiming[1];
                ulong lastStart = ulong.MaxValue;
                var timings = new System.Collections.Generic.List<FrameTiming>();

                ProfilerRecorder feature = default;
                if (!string.IsNullOrEmpty(cfg.FeatureMarker))
                {
                    feature = ProfilerRecorder.StartNew(ProfilerCategory.Scripts, cfg.FeatureMarker, RecorderCapacity(cfg));
                }
                ProfilerRecorder gc = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "GC Allocated In Frame", RecorderCapacity(cfg));

                try
                {
                    // The drain frames only let the delayed FrameTiming results for the last measured frames
                    // arrive. The recorders keep running through them and only their first MeasuredFrames
                    // samples are read.
                    for (int f = 0; f < cfg.MeasuredFrames + DrainFrames; f++)
                    {
                        FrameTimingManager.CaptureFrameTimings();
                        if (FrameTimingManager.GetLatestTimings(1, buf) > 0 && buf[0].frameStartTimestamp != lastStart)
                        {
                            lastStart = buf[0].frameStartTimestamp;
                            timings.Add(buf[0]);
                        }
                        yield return null;
                    }

                    // A recorder that reaches its capacity does not keep its oldest samples (Spike 002 and 003: Count
                    // fell back to a small number). Capacity has headroom; a wrapped recorder is a failed run.
                    if (gc.WrappedAround || (feature.Valid && feature.WrappedAround))
                    {
                        throw new InvalidOperationException("ProfilerRecorder wrapped around: capacity too small");
                    }
                    // Sample 0 is the partial frame in which the recorder started (Spike 003: feature 0 ms,
                    // GC about half of the steady value), so the window is samples 1..MeasuredFrames.
                    int featureEnd = Math.Min(feature.Valid ? feature.Count : 0, cfg.MeasuredFrames + 1);
                    for (int i = 1; i < featureEnd; i++)
                    {
                        result.FeatureMs.Add(feature.GetSample(i).Value * NsToMs);
                    }
                    int gcEnd = Math.Min(gc.Count, cfg.MeasuredFrames + 1);
                    for (int i = 1; i < gcEnd; i++)
                    {
                        result.GcBytes.Add(gc.GetSample(i).Value);
                    }
                }
                finally
                {
                    if (feature.Valid) feature.Dispose();
                    gc.Dispose();
                }

                // The first FrameTimingLag records are frames from before the window opened.
                for (int i = FrameTimingLag; i < timings.Count && result.MainMs.Count < cfg.MeasuredFrames; i++)
                {
                    result.MainMs.Add(timings[i].cpuMainThreadFrameTime);
                    result.RenderMs.Add(timings[i].cpuRenderThreadFrameTime);
                    result.GpuMs.Add(timings[i].gpuFrameTime);
                    result.CpuMs.Add(timings[i].cpuFrameTime);
                }

                result.Info = BuildInfo(cfg, result);
                done(result);
            }
            finally
            {
                QualitySettings.vSyncCount = oldVSync;
                Application.targetFrameRate = oldTarget;
            }
        }

        static int RecorderCapacity(PerfRunConfig cfg)
        {
            return cfg.MeasuredFrames + DrainFrames + 16;
        }

        static RunInfo BuildInfo(PerfRunConfig cfg, PerfRunResult r)
        {
            var info = new RunInfo
            {
                feature = cfg.Feature,
                label = cfg.Label,
                session = cfg.Session,
                sweep_param = cfg.SweepParam,
                sweep_value = cfg.SweepValue,
                warmup_frames = cfg.WarmupFrames,
                measured_frames = cfg.MeasuredFrames,
                seed = cfg.Seed,
                notes = cfg.Notes,
                timestamp_utc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                unity_version = Application.unityVersion,
                machine = SystemInfo.deviceName,
                gpu = SystemInfo.graphicsDeviceName,
                resolution = Screen.width + "x" + Screen.height,
                quality_level = QualitySettings.names[QualitySettings.GetQualityLevel()],
                editor = Application.isEditor,
                vsync_count_set = 0,
                target_frame_rate_set = -1,
                frame_timing_enabled = FrameTimingManager.IsFeatureEnabled(),
                timing_frames = r.MainMs.Count,
                recorder_frames = r.GcBytes.Count,
            };

            GitInfo.Get(out info.git_commit, out info.git_dirty);

            double gpuMax = 0;
            foreach (double g in r.GpuMs)
            {
                gpuMax = Math.Max(gpuMax, g);
            }
            info.gpu_valid = gpuMax > 0;

            info.metrics.Add(PerfStats.Summarize("main_ms", "ms", r.MainMs));
            info.metrics.Add(PerfStats.Summarize("render_ms", "ms", r.RenderMs));
            info.metrics.Add(PerfStats.Summarize("gpu_ms", "ms", r.GpuMs));
            info.metrics.Add(PerfStats.Summarize("cpu_ms", "ms", r.CpuMs));
            if (r.FeatureMs.Count > 0)
            {
                info.metrics.Add(PerfStats.Summarize("feature_ms", "ms", r.FeatureMs));
            }
            info.metrics.Add(PerfStats.Summarize("gc_alloc_bytes", "bytes", r.GcBytes));
            return info;
        }
    }
}
