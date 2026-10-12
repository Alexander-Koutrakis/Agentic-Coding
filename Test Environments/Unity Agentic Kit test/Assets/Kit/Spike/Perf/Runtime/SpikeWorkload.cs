using Unity.Profiling;
using UnityEngine;

namespace Kit.Spike.Perf
{
    // Fixed CPU workload wrapped in a named ProfilerMarker. Stands in for "the feature" in Spike 002.
    public class SpikeWorkload : MonoBehaviour
    {
        public const string MarkerName = "Kit.Spike.Workload";
        public const int Iterations = 200_000;

        static readonly ProfilerMarker Marker = new ProfilerMarker(ProfilerCategory.Scripts, MarkerName);

        public bool FeatureEnabled;

        // Written so the compiler cannot drop the loop.
        public float Sink { get; private set; }

        void Update()
        {
            if (!FeatureEnabled)
            {
                return;
            }

            using (Marker.Auto())
            {
                float acc = 0f;
                for (int i = 0; i < Iterations; i++)
                {
                    acc += Mathf.Sin(i * 0.001f);
                }
                Sink = acc;
            }
        }
    }
}
