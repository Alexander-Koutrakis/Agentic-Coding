using UnityEngine;

namespace Kit.Grass
{
    public struct GrassFieldCreateInfo
    {
        public int seed;
        public int bladeCount;
        public Vector2 patchSize;
        public Vector3 patchCenter;
        public float minScale;
        public float maxScale;
    }
}
