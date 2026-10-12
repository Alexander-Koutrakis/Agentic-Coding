using System;
using System.Collections;
using System.Collections.Generic;
using Kit.Perf.Toy;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace Kit.Perf.Tests
{
    public class ToyInstancesSweepTests
    {
        const string Feature = "toy-instances";
        const int Seed = 12345;

        static readonly int[] SweepPoints = { 1000, 3000, 6000, 10000, 50000, 100000 };
        const int Repeats = 3;

        // Probe: does the Editor return GPU / render-thread timing at all? Two points, one run each.
        [UnityTest, Timeout(300000)]
        public IEnumerator Probe_FrameTimingAvailable()
        {
            yield return RunPoints(new[] { 0, 100000 }, "probe");

            foreach (RunInfo info in _infos)
            {
                Debug.Log(PerfRunWriter.Summary(info) + " frame_timing_enabled=" + info.frame_timing_enabled);
            }
            Assert.AreEqual(2, _infos.Count);
            foreach (RunInfo info in _infos)
            {
                Assert.AreEqual(info.measured_frames, info.timing_frames, info.label + ": timing frames");
                Assert.AreEqual(info.measured_frames, info.recorder_frames, info.label + ": recorder frames");
            }
        }

        // The sweep: baseline (N = 0, feature on) first and last, the sweep points repeated and shuffled in between.
        [UnityTest, Timeout(1800000)]
        public IEnumerator Sweep_ToyInstances()
        {
            var points = new List<int>();
            for (int r = 0; r < Repeats; r++)
            {
                points.AddRange(SweepPoints);
            }
            Shuffle(points, new System.Random(Seed));
            points.Insert(0, 0);
            points.Add(0);

            yield return RunPoints(points.ToArray(), "sweep");

            foreach (RunInfo info in _infos)
            {
                Debug.Log(PerfRunWriter.Summary(info));
                Assert.AreEqual(info.measured_frames, info.timing_frames, info.label + ": timing frames");
                Assert.AreEqual(info.measured_frames, info.recorder_frames, info.label + ": recorder frames");
            }
            Assert.AreEqual(points.Count, _infos.Count);
        }

        readonly List<RunInfo> _infos = new List<RunInfo>();

        IEnumerator RunPoints(int[] points, string tag)
        {
            _infos.Clear();
            string session = DateTime.UtcNow.ToString("yyyyMMddTHHmmss");

            var cam = new GameObject("PerfCamera").AddComponent<Camera>();
            cam.tag = "MainCamera";
            cam.transform.position = new Vector3(0, 0, -15);
            cam.fieldOfView = 60;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = Color.black;

            var go = new GameObject("ToyInstances");
            var toy = go.AddComponent<ToyInstances>();
            toy.Init(Seed);

            try
            {
                for (int i = 0; i < points.Length; i++)
                {
                    toy.SetCount(points[i]);
                    var cfg = new PerfRunConfig
                    {
                        Feature = Feature,
                        Label = tag + "-n" + points[i] + "-i" + i,
                        Session = session,
                        SweepParam = "instances",
                        SweepValue = points[i],
                        Seed = Seed,
                        FeatureMarker = ToyInstances.MarkerName,
                    };

                    PerfRunResult result = null;
                    yield return PerfRunner.Run(cfg, r => result = r);
                    Assert.IsNotNull(result, "run produced no result");
                    PerfRunWriter.Write(result);
                    _infos.Add(result.Info);
                }
            }
            finally
            {
                UnityEngine.Object.Destroy(go);
                UnityEngine.Object.Destroy(cam.gameObject);
            }
        }

        static void Shuffle(List<int> list, System.Random rng)
        {
            for (int i = list.Count - 1; i > 0; i--)
            {
                int j = rng.Next(i + 1);
                (list[i], list[j]) = (list[j], list[i]);
            }
        }
    }
}
