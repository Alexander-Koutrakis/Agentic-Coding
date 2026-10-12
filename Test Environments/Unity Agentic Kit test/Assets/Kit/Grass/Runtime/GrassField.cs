using System;
using UnityEngine;
using Random = System.Random;

namespace Kit.Grass
{
    public sealed class GrassField
    {
        public Matrix4x4[] Matrices { get; }
        public int BladeCount => Matrices.Length;

        GrassField(Matrix4x4[] matrices)
        {
            Matrices = matrices;
        }

        public static GrassField Create(in GrassFieldCreateInfo info)
        {
            if (info.bladeCount < 0)
                throw new ArgumentException("bladeCount must be >= 0", nameof(info));
            if (!(info.patchSize.x > 0f) || !(info.patchSize.y > 0f))
                throw new ArgumentException("patchSize must be > 0 on both axes", nameof(info));
            if (!(info.minScale > 0f) || !(info.minScale <= info.maxScale))
                throw new ArgumentException("scale range must satisfy 0 < minScale <= maxScale", nameof(info));

            var rng = new Random(info.seed);
            var matrices = new Matrix4x4[info.bladeCount];
            for (int i = 0; i < matrices.Length; i++)
            {
                float x = info.patchCenter.x + ((float)rng.NextDouble() - 0.5f) * info.patchSize.x;
                float z = info.patchCenter.z + ((float)rng.NextDouble() - 0.5f) * info.patchSize.y;
                float yaw = (float)rng.NextDouble() * 360f;
                float scale = Mathf.Lerp(info.minScale, info.maxScale, (float)rng.NextDouble());
                matrices[i] = Matrix4x4.TRS(
                    new Vector3(x, info.patchCenter.y, z),
                    Quaternion.AngleAxis(yaw, Vector3.up),
                    new Vector3(scale, scale, scale));
            }
            return new GrassField(matrices);
        }
    }
}
