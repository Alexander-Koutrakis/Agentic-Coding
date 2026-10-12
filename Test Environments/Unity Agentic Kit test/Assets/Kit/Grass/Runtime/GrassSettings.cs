using System;
using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace Kit.Grass
{
    [Serializable]
    public struct GrassSettings
    {
        public int bladeCount;
        public Vector2 patchSize;
        public Vector3 patchCenter;
        public int seed;
        public float minScale;
        public float maxScale;
        public Mesh mesh;
        public Material material;
        public ComputeShader cullShader;
        public RenderPassEvent passEvent;
    }
}
