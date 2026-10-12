using System;
using System.Collections;
using System.Collections.Generic;
using Kit.Perf;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;
#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
#endif

namespace Kit.Grass.Tests
{
    // Perf sweep over blade count in the reference scene (plan T6). Run through run_tests, Game view only.
    public class GrassPerfSweepTests
    {
        const string Feature = "grass";
        const int Seed = 12345;
        const int Repeats = 3;
        const int FullCount = 100000;
        const float BaselineTolerance = 0.15f;
        const string ScenePath = "Assets/Kit/Grass/GrassReference.unity";
        const string RendererPath = "Assets/Settings/PC_Renderer.asset";
        const string Marker = "Kit.Grass.Draw";

        static readonly int[] SweepPoints = { 1000, 3000, 6000, 10000, 50000, 100000 };
        static readonly Pose WholePose = new Pose(new Vector3(0f, 45f, -50f), Quaternion.Euler(42f, 0f, 0f));
        static readonly Pose HalfPose = new Pose(new Vector3(0f, 8f, -12f), Quaternion.Euler(30f, 0f, 0f));

        readonly List<RunInfo> infos = new List<RunInfo>();
        GrassFeature feature;
        Camera cam;

        [SetUp]
        public void SetUp()
        {
            infos.Clear(); // the fixture instance is shared between tests
        }

        // One point, one run: proves the test wiring and that timing_frames == measured_frames.
        [UnityTest, Timeout(300000)]
        public IEnumerator Smoke_OnePoint()
        {
            yield return LoadScene();
            yield return RunPoints(new[] { 1000 }, WholePose, "sweep");

            Assert.AreEqual(1, infos.Count);
            LogAndCheck(infos[0]);
            Debug.Log("resolution " + infos[0].resolution + " scene " + SceneManager.GetActiveScene().name);
        }

        // The full sweep: baseline N = 0 first and last, 3 shuffled repeats in between, then the half view and the OFF run.
        [UnityTest, Timeout(3600000)]
        public IEnumerator Sweep_Grass()
        {
            yield return LoadScene();

            var points = new List<int>();
            for (int r = 0; r < Repeats; r++)
                points.AddRange(SweepPoints);
            Shuffle(points, new System.Random(Seed));
            points.Insert(0, 0);
            points.Add(0);

            yield return RunPoints(points.ToArray(), WholePose, "sweep");
            yield return RunPoints(new[] { FullCount }, HalfPose, "cull-half");

            bool wasActive = feature.isActive;
            feature.SetActive(false);
            try
            {
                yield return RunPoints(new[] { FullCount }, WholePose, "off");
            }
            finally
            {
                feature.SetActive(wasActive);
            }

            foreach (RunInfo info in infos)
                LogAndCheck(info);
            Assert.AreEqual(points.Count + 2, infos.Count);

            double first = Gpu(infos[0]);
            double last = Gpu(infos[points.Count - 1]);
            Assert.AreEqual(first, last, BaselineTolerance * Math.Max(first, last), "baseline N=0 gpu_ms drifted");
        }

        IEnumerator LoadScene()
        {
#if UNITY_EDITOR
            yield return EditorSceneManager.LoadSceneInPlayMode(ScenePath, new LoadSceneParameters(LoadSceneMode.Single));

            var rendererData = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(RendererPath);
            Assert.IsNotNull(rendererData, "renderer asset not found");
            foreach (ScriptableRendererFeature f in rendererData.rendererFeatures)
            {
                if (f is GrassFeature g)
                    feature = g;
            }
            Assert.IsNotNull(feature, "no GrassFeature on " + RendererPath);
            cam = Camera.main;
            Assert.IsNotNull(cam, "no main camera in the scene");

            // The renderer builds the feature on the first rendered frame; SetBladeCount does nothing before that.
            for (int i = 0; i < 3; i++)
                yield return null;
            Assert.AreEqual(GrassSetupResult.Ok, feature.SetupResult);
#else
            Assert.Ignore("Editor only");
            yield break;
#endif
        }

        IEnumerator RunPoints(int[] points, Pose pose, string tag)
        {
            string session = DateTime.UtcNow.ToString("yyyyMMddTHHmmss");
            SetPose(pose);
            for (int i = 0; i < points.Length; i++)
            {
                SetCount(points[i]);
                var cfg = new PerfRunConfig
                {
                    Feature = Feature,
                    Label = tag + "-n" + points[i] + "-i" + (infos.Count),
                    Session = session,
                    SweepParam = "blades",
                    SweepValue = points[i],
                    Seed = Seed,
                    FeatureMarker = Marker,
                };

                PerfRunResult result = null;
                yield return PerfRunner.Run(cfg, r => result = r);
                Assert.IsNotNull(result, "run produced no result");
                PerfRunWriter.Write(result);
                infos.Add(result.Info);
            }
        }

        void SetCount(int count)
        {
            feature.SetBladeCount(count);
            Assert.AreEqual(count, feature.BladeCount);
        }

        void SetPose(Pose pose)
        {
            cam.transform.SetPositionAndRotation(pose.position, pose.rotation);
        }

        static void LogAndCheck(RunInfo info)
        {
            Debug.Log(PerfRunWriter.Summary(info));
            Assert.IsTrue(info.gpu_valid, info.label + ": gpu_valid");
            Assert.AreEqual(info.measured_frames, info.timing_frames, info.label + ": timing frames");
            Assert.AreEqual(info.measured_frames, info.recorder_frames, info.label + ": recorder frames");
        }

        static double Gpu(RunInfo info)
        {
            foreach (MetricStats m in info.metrics)
            {
                if (m.name == "gpu_ms")
                    return m.median;
            }
            return 0;
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
