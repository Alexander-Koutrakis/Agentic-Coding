using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace Kit.Grass.Tests
{
    public class GrassFeatureTests
    {
        const string ComputePath = "Assets/Kit/Grass/Shaders/GrassCull.compute";

        GrassFeature feature;
        Material material;

        [SetUp]
        public void SetUp()
        {
            material = new Material(Shader.Find("Kit/GrassInstanced"));
            feature = ScriptableObject.CreateInstance<GrassFeature>();
            feature.settings = new GrassSettings
            {
                bladeCount = 100,
                patchSize = new Vector2(10f, 10f),
                seed = 1,
                minScale = 0.5f,
                maxScale = 1.5f,
                mesh = Resources.GetBuiltinResource<Mesh>("Cube.fbx"),
                material = material,
                cullShader = AssetDatabase.LoadAssetAtPath<ComputeShader>(ComputePath),
                passEvent = RenderPassEvent.AfterRenderingOpaques,
            };
        }

        [TearDown]
        public void TearDown()
        {
            feature.Dispose();
            Object.DestroyImmediate(feature);
            Object.DestroyImmediate(material);
        }

        [Test]
        public void Create_ValidSettings_ResultOk()
        {
            feature.Create();
            Assert.AreEqual(GrassSetupResult.Ok, feature.SetupResult);
        }

        [TestCase(GrassSetupResult.MissingMesh)]
        [TestCase(GrassSetupResult.MissingMaterial)]
        [TestCase(GrassSetupResult.MissingCullShader)]
        [TestCase(GrassSetupResult.BadSettings)]
        public void Create_BadSettings_SetsResultAndAddRenderPassesSkips(GrassSetupResult expected)
        {
            GrassSettings s = feature.settings;
            switch (expected)
            {
                case GrassSetupResult.MissingMesh: s.mesh = null; break;
                case GrassSetupResult.MissingMaterial: s.material = null; break;
                case GrassSetupResult.MissingCullShader: s.cullShader = null; break;
                default: s.minScale = 3f; break; // minScale > maxScale
            }
            feature.settings = s;

            feature.Create();
            Assert.AreEqual(expected, feature.SetupResult);

            // With a null renderer any attempt to enqueue would throw, so a clean return means it skipped.
            RenderingData renderingData = default;
            Assert.DoesNotThrow(() => feature.AddRenderPasses(null, ref renderingData));
            Assert.IsNull(feature.Culler);
        }

        [Test]
        public void SetBladeCount_ChangesRuntimeCount_SerializedSettingUnchanged()
        {
            feature.Create();
            GrassCuller before = feature.Culler;
            Assert.AreEqual(100, feature.BladeCount);

            feature.SetBladeCount(250);

            Assert.AreEqual(250, feature.BladeCount);
            Assert.AreEqual(250, feature.Culler.BladeCount);
            Assert.AreEqual(100, feature.settings.bladeCount);
            Assert.AreNotSame(before, feature.Culler);
        }

        [Test]
        public void SetBladeCount_SameCount_KeepsCuller()
        {
            feature.Create();
            GrassCuller before = feature.Culler;

            feature.SetBladeCount(100);

            Assert.AreSame(before, feature.Culler);
        }
    }
}
