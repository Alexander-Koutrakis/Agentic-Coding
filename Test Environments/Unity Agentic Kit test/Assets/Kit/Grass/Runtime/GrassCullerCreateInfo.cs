using UnityEngine;

namespace Kit.Grass
{
    public struct GrassCullerCreateInfo
    {
        public ComputeShader cullShader;
        public int bladeCount;
        public Vector3 boundCenter;
        public float boundRadius;
        public uint indexCount;
    }
}
