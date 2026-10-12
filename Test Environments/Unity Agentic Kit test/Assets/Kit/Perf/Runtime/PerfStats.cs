using System;
using System.Collections.Generic;

namespace Kit.Perf
{
    // Definitions are shared with scripts/unity/perf_analyze.py: median = mean of the two middle values for an
    // even count; p95 = nearest rank (ceil(0.95 * n)-th smallest).
    public static class PerfStats
    {
        public static MetricStats Summarize(string name, string unit, IReadOnlyList<double> values)
        {
            var stats = new MetricStats { name = name, unit = unit, count = values.Count };
            if (values.Count == 0)
            {
                return stats;
            }

            var sorted = new double[values.Count];
            for (int i = 0; i < sorted.Length; i++)
            {
                sorted[i] = values[i];
            }
            Array.Sort(sorted);

            int n = sorted.Length;
            stats.median = n % 2 == 1 ? sorted[n / 2] : 0.5 * (sorted[n / 2 - 1] + sorted[n / 2]);
            stats.p95 = sorted[Math.Max((int)Math.Ceiling(0.95 * n) - 1, 0)];
            stats.min = sorted[0];
            stats.max = sorted[n - 1];
            return stats;
        }
    }
}
