using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

namespace Kit.Perf
{
    // Layout (plan §4.4): <project>/Perf/<feature>/runs/<timestamp>-<label>/{run.json, frames_timing.csv,
    // frames_recorders.csv} and one line appended to <project>/Perf/<feature>/index.jsonl.
    public static class PerfRunWriter
    {
        public static string FeatureDir(string feature)
        {
            return Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Perf", feature));
        }

        public static string Write(PerfRunResult r)
        {
            RunInfo info = r.Info;
            string stamp = DateTime.UtcNow.ToString("yyyyMMddTHHmmssfff", CultureInfo.InvariantCulture);
            string featureDir = FeatureDir(info.feature);
            string runDir = Path.Combine(featureDir, "runs", stamp + "-" + info.label);
            Directory.CreateDirectory(runDir);

            File.WriteAllText(Path.Combine(runDir, "run.json"), JsonUtility.ToJson(info, true) + "\n");
            File.WriteAllText(Path.Combine(runDir, "frames_timing.csv"),
                Csv("frame,main_ms,render_ms,gpu_ms,cpu_ms", r.MainMs, r.RenderMs, r.GpuMs, r.CpuMs));
            File.WriteAllText(Path.Combine(runDir, "frames_recorders.csv"),
                Csv("frame,feature_ms,gc_alloc_bytes", r.FeatureMs, r.GcBytes));

            var line = new IndexLine
            {
                timestamp_utc = info.timestamp_utc,
                run_dir = "runs/" + stamp + "-" + info.label,
                label = info.label,
                sweep_value = info.sweep_value,
                gpu_median_ms = Median(info, "gpu_ms"),
                main_median_ms = Median(info, "main_ms"),
                render_median_ms = Median(info, "render_ms"),
                feature_median_ms = Median(info, "feature_ms"),
            };
            File.AppendAllText(Path.Combine(featureDir, "index.jsonl"), JsonUtility.ToJson(line) + "\n");
            return runDir;
        }

        // One summary line for the test log / agent.
        public static string Summary(RunInfo info)
        {
            return string.Format(CultureInfo.InvariantCulture,
                "{0}: N={1} frames={2} main={3:F3} render={4:F3} gpu={5:F3} feature={6:F3} ms (median), gpu_valid={7}",
                info.label, info.sweep_value, info.timing_frames,
                Median(info, "main_ms"), Median(info, "render_ms"), Median(info, "gpu_ms"), Median(info, "feature_ms"),
                info.gpu_valid);
        }

        static double Median(RunInfo info, string metric)
        {
            foreach (MetricStats m in info.metrics)
            {
                if (m.name == metric)
                {
                    return m.median;
                }
            }
            return 0;
        }

        // Columns of different length are padded with empty cells, so a short series is visible, not hidden.
        static string Csv(string header, params List<double>[] columns)
        {
            int rows = 0;
            foreach (List<double> c in columns)
            {
                rows = Math.Max(rows, c.Count);
            }

            var sb = new StringBuilder(header).Append('\n');
            for (int i = 0; i < rows; i++)
            {
                sb.Append(i);
                foreach (List<double> c in columns)
                {
                    sb.Append(',');
                    if (i < c.Count)
                    {
                        sb.Append(c[i].ToString("R", CultureInfo.InvariantCulture));
                    }
                }
                sb.Append('\n');
            }
            return sb.ToString();
        }
    }
}
