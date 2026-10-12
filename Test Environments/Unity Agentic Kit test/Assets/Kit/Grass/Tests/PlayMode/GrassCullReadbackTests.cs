using System;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
#if UNITY_EDITOR
using UnityEditor;
#endif

namespace Kit.Grass.Tests
{
    // Renders a temporary camera through a URP asset built in code (the project's renderer asset is not touched)
    // and reads the indirect-args instance count back. The readback exists only here.
    public class GrassCullReadbackTests
    {
        const int N = 10000;
        const float Height = 60f;
        const float HalfWidth = 34.641f; // Height * tan(30 deg): the camera sees 69 m across at the ground
        static readonly Vector3 Down = new Vector3(90f, 0f, 0f);
        static readonly Vector3 Up = new Vector3(-90f, 0f, 0f);

        UniversalRenderPipelineAsset pipelineAsset;
        UniversalRendererData rendererData;
        GrassFeature feature;
        RenderPipelineAsset previousPipeline;
        Camera camera;
        RenderTexture target;
        Material material;
        Mesh mesh;
        ComputeShader cullShader;
        string meshSource;

        [SetUp]
        public void SetUp()
        {
            material = new Material(Shader.Find("Kit/GrassInstanced"));
            LoadAssets();

            feature = ScriptableObject.CreateInstance<GrassFeature>();
            feature.settings = new GrassSettings
            {
                bladeCount = N,
                patchSize = new Vector2(50f, 50f),
                patchCenter = Vector3.zero,
                seed = 12345,
                minScale = 0.8f,
                maxScale = 1.2f,
                mesh = mesh,
                material = material,
                cullShader = cullShader,
                passEvent = RenderPassEvent.AfterRenderingOpaques,
            };

            rendererData = ScriptableObject.CreateInstance<UniversalRendererData>();
            rendererData.rendererFeatures.Add(feature);
            pipelineAsset = UniversalRenderPipelineAsset.Create(rendererData);
            previousPipeline = QualitySettings.renderPipeline;
            QualitySettings.renderPipeline = pipelineAsset;

            target = new RenderTexture(256, 256, 24);
            var go = new GameObject("GrassTestCamera");
            camera = go.AddComponent<Camera>();
            camera.enabled = false;
            camera.fieldOfView = 60f;
            camera.targetTexture = target;
            camera.nearClipPlane = 0.3f;
            camera.farClipPlane = 500f;

            // The first render builds the renderer, which calls GrassFeature.Create.
            camera.transform.SetPositionAndRotation(WholePose, Quaternion.Euler(Down));
            camera.Render();
            Assert.AreEqual(GrassSetupResult.Ok, feature.SetupResult);
        }

        [TearDown]
        public void TearDown()
        {
            QualitySettings.renderPipeline = previousPipeline;
            if (camera != null)
                UnityEngine.Object.DestroyImmediate(camera.gameObject);
            UnityEngine.Object.DestroyImmediate(target);
            UnityEngine.Object.DestroyImmediate(pipelineAsset); // disposes the renderer and so the feature
            UnityEngine.Object.DestroyImmediate(rendererData);
            UnityEngine.Object.DestroyImmediate(feature);
            UnityEngine.Object.DestroyImmediate(material);
        }

        void LoadAssets()
        {
#if UNITY_EDITOR
            cullShader = AssetDatabase.LoadAssetAtPath<ComputeShader>("Assets/Kit/Grass/Shaders/GrassCull.compute");
            mesh = AssetDatabase.LoadAssetAtPath<Mesh>("Assets/GrassBlade.fbx");
#endif
            meshSource = "GrassBlade.fbx";
            if (mesh == null)
            {
                GameObject quad = GameObject.CreatePrimitive(PrimitiveType.Quad);
                mesh = quad.GetComponent<MeshFilter>().sharedMesh;
                UnityEngine.Object.DestroyImmediate(quad);
                meshSource = "primitive quad";
            }
            Assert.IsNotNull(cullShader, "GrassCull.compute not loaded");
        }

        // Renders one frame from the pose and returns the instance count the cull pass wrote into the draw args.
        int Visible(Vector3 position, Vector3 euler)
        {
            camera.transform.SetPositionAndRotation(position, Quaternion.Euler(euler));
            camera.Render();
            var args = new uint[5];
            feature.Culler.Args.GetData(args);
            return (int)args[1];
        }

        Vector3 WholePose => new Vector3(0f, Height, 0f);
        Vector3 HalfPose => new Vector3(-HalfWidth, Height, 0f); // right frustum edge on x = 0

        [Test]
        public void WholePatchInView_ReadsAllBlades()
        {
            int visible = Visible(WholePose, Down);
            TestContext.Out.WriteLine($"readback whole-patch pose: {visible} of {N} (mesh: {meshSource})");
            Assert.AreEqual(N, visible);
        }

        [Test]
        public void CameraTurnedAway_ReadsZero()
        {
            int visible = Visible(WholePose, Up);
            TestContext.Out.WriteLine($"readback away pose: {visible} of {N}");
            Assert.AreEqual(0, visible);
        }

        [Test]
        public void HalfView_ReadsAboutHalf()
        {
            int visible = Visible(HalfPose, Down);
            TestContext.Out.WriteLine($"readback half-view pose: {visible} of {N} ({100f * visible / N:F1} percent)");
            Assert.That(visible, Is.InRange(N * 40 / 100, N * 60 / 100));
        }

        [Test]
        public void ConsecutiveFramesWithDifferentPoses_CounterResetsEachFrame()
        {
            int whole1 = Visible(WholePose, Down);
            int away = Visible(WholePose, Up);
            int half = Visible(HalfPose, Down);
            int whole2 = Visible(WholePose, Down);
            int away2 = Visible(WholePose, Up);
            TestContext.Out.WriteLine($"readback sequence whole,away,half,whole,away: {whole1},{away},{half},{whole2},{away2}");
            Assert.AreEqual(N, whole1);
            Assert.AreEqual(0, away);
            Assert.That(half, Is.InRange(N * 40 / 100, N * 60 / 100));
            Assert.AreEqual(N, whole2, "counter was not reset: count accumulated");
            Assert.AreEqual(0, away2);
        }

        [Test]
        public void BladesJustOutsideAndInsideFrustumEdge_CulledAndKeptCorrectly()
        {
            // Right frustum plane at the ground: outward distance of a sphere centre (x, 0, z) is cos(30 deg) * x.
            const float cos30 = 0.8660254f;
            feature.SetBladeCount(6);
            Bounds b = mesh.bounds;
            float r = b.extents.magnitude;
            Vector3 c = b.center;

            Matrix4x4 Blade(float outDist, float scale)
            {
                Vector3 centre = new Vector3(outDist / cos30, 0f, 0f);
                return Matrix4x4.TRS(centre - scale * c, Quaternion.identity, Vector3.one * scale);
            }

            var m = new Matrix4x4[]
            {
                Blade(-5f, 1f),             // well inside: kept
                Blade(r - 0.02f, 1f),       // centre outside the plane, sphere overlaps it: kept
                Blade(r + 0.05f, 1f),       // sphere fully outside: culled
                Blade(30f, 1f),             // far outside: culled
                Blade(1.5f * r, 2f),        // scale 2 doubles the radius: kept only if the scaled radius is used
                Blade(2f * r + 0.05f, 2f),  // scale 2, fully outside: culled
            };
            feature.Culler.Upload(m, m.Length);

            int visible = Visible(HalfPose, Down);
            TestContext.Out.WriteLine($"readback edge blades (expect 3: inside, just-inside, scaled-just-inside): {visible}, radius {r:F3}");
            Assert.AreEqual(3, visible);
        }

        [Test]
        public void CreateAndDisposeCullerTwice_NoConsoleMessage()
        {
            var info = new GrassCullerCreateInfo
            {
                cullShader = cullShader,
                bladeCount = 100,
                boundCenter = Vector3.zero,
                boundRadius = 1f,
                indexCount = 3,
            };
            for (int i = 0; i < 2; i++)
            {
                GrassCuller culler = GrassCuller.Create(in info);
                culler.Dispose();
            }
            GC.Collect();
            GC.WaitForPendingFinalizers();
            UnityEngine.TestTools.LogAssert.NoUnexpectedReceived();
        }
    }
}
