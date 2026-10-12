using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace Kit.Grass
{
    public sealed class GrassFeature : ScriptableRendererFeature
    {
        // Source of truth. Serialized; nothing in the runtime writes it.
        public GrassSettings settings = new GrassSettings
        {
            bladeCount = 10000,
            patchSize = new Vector2(50f, 50f),
            seed = 12345,
            minScale = 0.8f,
            maxScale = 1.2f,
            passEvent = RenderPassEvent.AfterRenderingOpaques,
        };

        GrassSystem system;

        public GrassSetupResult SetupResult { get; private set; } = GrassSetupResult.BadSettings;
        public GrassCuller Culler => system?.Culler;
        public int BladeCount => system?.BladeCount ?? 0;

        public override void Create()
        {
            system?.Dispose();
            SetupResult = GrassSystem.TryCreate(in settings, out system);
        }

        public override void AddRenderPasses(ScriptableRenderer renderer, ref RenderingData renderingData)
        {
            if (SetupResult != GrassSetupResult.Ok)
                return;
            if (renderingData.cameraData.cameraType != CameraType.Game)
                return;
            renderer.EnqueuePass(system.Pass);
        }

        public void SetBladeCount(int count)
        {
            system?.SetBladeCount(count);
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                system?.Dispose();
                system = null;
                SetupResult = GrassSetupResult.BadSettings;
            }
        }
    }
}
