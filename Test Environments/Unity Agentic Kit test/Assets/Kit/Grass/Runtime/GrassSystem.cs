using System;
using UnityEngine;

namespace Kit.Grass
{
    public sealed class GrassSystem : IDisposable
    {
        GrassSettings settings; // private copy; the serialized settings are never written
        GrassCuller culler;

        public GrassPass Pass { get; }
        public GrassCuller Culler => culler;
        public int BladeCount => settings.bladeCount;

        GrassSystem(in GrassSettings settings, GrassPass pass)
        {
            this.settings = settings;
            Pass = pass;
        }

        public static GrassSetupResult TryCreate(in GrassSettings settings, out GrassSystem system)
        {
            system = null;
            if (settings.mesh == null)
                return GrassSetupResult.MissingMesh;
            if (settings.material == null)
                return GrassSetupResult.MissingMaterial;
            if (settings.cullShader == null || !settings.cullShader.HasKernel("CSMain"))
                return GrassSetupResult.MissingCullShader;
            if (settings.bladeCount < 0 || settings.bladeCount > GrassCuller.MaxBlades
                || !(settings.patchSize.x > 0f) || !(settings.patchSize.y > 0f)
                || !(settings.minScale > 0f) || !(settings.minScale <= settings.maxScale)
                || settings.mesh.subMeshCount < 1 || settings.mesh.GetIndexCount(0) == 0
                || !(settings.mesh.bounds.extents.magnitude > 0f))
                return GrassSetupResult.BadSettings;

            var passInfo = new GrassPassCreateInfo
            {
                mesh = settings.mesh,
                material = settings.material,
                passEvent = settings.passEvent,
            };
            var created = new GrassSystem(in settings, GrassPass.Create(in passInfo));
            created.Place();
            system = created;
            return GrassSetupResult.Ok;
        }

        // Re-places only when the count changed.
        public void SetBladeCount(int count)
        {
            if (count < 0 || count > GrassCuller.MaxBlades)
                throw new ArgumentOutOfRangeException(nameof(count));
            if (count == settings.bladeCount)
                return;
            settings.bladeCount = count;
            Place();
        }

        void Place()
        {
            culler?.Dispose();
            culler = null;
            Pass.Culler = null;

            Bounds bounds = settings.mesh.bounds;
            var cullerInfo = new GrassCullerCreateInfo
            {
                cullShader = settings.cullShader,
                bladeCount = settings.bladeCount,
                boundCenter = bounds.center,
                boundRadius = bounds.extents.magnitude,
                indexCount = settings.mesh.GetIndexCount(0),
            };
            culler = GrassCuller.Create(in cullerInfo);

            try
            {
                var fieldInfo = new GrassFieldCreateInfo
                {
                    seed = settings.seed,
                    bladeCount = settings.bladeCount,
                    patchSize = settings.patchSize,
                    patchCenter = settings.patchCenter,
                    minScale = settings.minScale,
                    maxScale = settings.maxScale,
                };
                GrassField field = GrassField.Create(in fieldInfo);
                culler.Upload(field.Matrices, field.BladeCount);
            }
            catch
            {
                culler.Dispose();
                culler = null;
                throw;
            }
            Pass.Culler = culler; // the field goes out of scope here, so its array is not kept alive
        }

        public void Dispose()
        {
            culler?.Dispose();
            culler = null;
            Pass.Culler = null;
        }
    }
}
