using System;
using System.Collections;
using System.Globalization;
using System.IO;
using System.Text;
using NUnit.Framework;
using Unity.Profiling;
using UnityEngine;
using UnityEngine.TestTools;

namespace Kit.Spike.Perf.Tests
{
    public class SpikeWorkloadPerfTests
    {
        const int WarmupFrames = 30;
        const int MeasuredFrames = 120;

        struct Stats
        {
            public bool Valid;
            public int Count;
            public double P50;
            public double P95;
        }

        struct Run
        {
            public Stats Marker;
            public Stats GcBytes;
            public Stats MainThread;
        }

        Run _off;
        Run _on;

        [UnityTest]
        public IEnumerator Marker_OnVsOff_IsReadableByName()
        {
            var go = new GameObject("SpikeWorkload");
            var workload = go.AddComponent<SpikeWorkload>();

            try
            {
                yield return Measure(workload, false, run => _off = run);
                yield return Measure(workload, true, run => _on = run);
            }
            finally
            {
                UnityEngine.Object.Destroy(go);
            }

            WriteResult(_off, _on);

            Assert.IsTrue(_on.Marker.Valid, "ProfilerRecorder for the custom marker is not valid (ON run)");
            Assert.IsTrue(_off.Marker.Valid, "ProfilerRecorder for the custom marker is not valid (OFF run)");
            Assert.AreEqual(MeasuredFrames, _on.Marker.Count, "marker sample count ON");
            Assert.AreEqual(MeasuredFrames, _off.Marker.Count, "marker sample count OFF");
            Assert.Greater(_on.Marker.P50, 100_000.0, "ON median must exceed 0.1 ms (first-guess threshold, calibrate from real numbers)");
            Assert.Less(_off.Marker.P50, _on.Marker.P50 / 10.0, "OFF median must be far below ON median");
        }

        static IEnumerator Measure(SpikeWorkload workload, bool enabled, Action<Run> done)
        {
            workload.FeatureEnabled = enabled;

            for (int i = 0; i < WarmupFrames; i++)
            {
                yield return null;
            }

            // Recorders start after warmup, so every sample they hold is a measured frame.
            using (var marker = ProfilerRecorder.StartNew(ProfilerCategory.Scripts, SpikeWorkload.MarkerName, MeasuredFrames))
            using (var gc = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "GC Allocated In Frame", MeasuredFrames))
            using (var main = ProfilerRecorder.StartNew(ProfilerCategory.Internal, "Main Thread", MeasuredFrames))
            {
                for (int i = 0; i < MeasuredFrames; i++)
                {
                    yield return null;
                }

                done(new Run
                {
                    Marker = Summarize(marker),
                    GcBytes = Summarize(gc),
                    MainThread = Summarize(main),
                });
            }
        }

        static Stats Summarize(ProfilerRecorder recorder)
        {
            var stats = new Stats { Valid = recorder.Valid, Count = recorder.Count };
            if (!recorder.Valid || recorder.Count == 0)
            {
                return stats;
            }

            var values = new double[recorder.Count];
            for (int i = 0; i < values.Length; i++)
            {
                values[i] = recorder.GetSample(i).Value;
            }
            Array.Sort(values);
            stats.P50 = Percentile(values, 0.50);
            stats.P95 = Percentile(values, 0.95);
            return stats;
        }

        // Nearest rank on a sorted array.
        static double Percentile(double[] sorted, double p)
        {
            int rank = (int)Math.Ceiling(p * sorted.Length);
            return sorted[Math.Max(rank - 1, 0)];
        }

        static void WriteResult(Run off, Run on)
        {
            string dir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Perf", "spike-002"));
            Directory.CreateDirectory(dir);
            string path = Path.Combine(dir, "result.json");

            var sb = new StringBuilder();
            sb.Append("{\n");
            sb.Append("  \"feature\": \"").Append(SpikeWorkload.MarkerName).Append("\",\n");
            sb.Append("  \"unit\": \"ns (gc_alloc_bytes: bytes)\",\n");
            sb.Append("  \"warmup_frames\": ").Append(WarmupFrames).Append(",\n");
            sb.Append("  \"measured_frames\": ").Append(MeasuredFrames).Append(",\n");
            sb.Append("  \"resolution\": \"").Append(Screen.width).Append('x').Append(Screen.height).Append("\",\n");
            sb.Append("  \"machine\": \"").Append(SystemInfo.deviceName).Append("\",\n");
            sb.Append("  \"editor\": ").Append(Application.isEditor ? "true" : "false").Append(",\n");
            AppendRun(sb, "off", off, true);
            AppendRun(sb, "on", on, false);
            sb.Append("}\n");
            File.WriteAllText(path, sb.ToString());
            Debug.Log("Spike002 result written: " + path + "\n" + sb);
        }

        static void AppendRun(StringBuilder sb, string name, Run run, bool comma)
        {
            sb.Append("  \"").Append(name).Append("\": {\n");
            AppendStats(sb, "marker", run.Marker, true);
            AppendStats(sb, "gc_alloc_bytes", run.GcBytes, true);
            AppendStats(sb, "main_thread", run.MainThread, false);
            sb.Append("  }").Append(comma ? ",\n" : "\n");
        }

        static void AppendStats(StringBuilder sb, string name, Stats s, bool comma)
        {
            sb.Append("    \"").Append(name).Append("\": { \"valid\": ").Append(s.Valid ? "true" : "false")
              .Append(", \"count\": ").Append(s.Count)
              .Append(", \"p50\": ").Append(s.P50.ToString("R", CultureInfo.InvariantCulture))
              .Append(", \"p95\": ").Append(s.P95.ToString("R", CultureInfo.InvariantCulture))
              .Append(" }").Append(comma ? ",\n" : "\n");
        }
    }
}
