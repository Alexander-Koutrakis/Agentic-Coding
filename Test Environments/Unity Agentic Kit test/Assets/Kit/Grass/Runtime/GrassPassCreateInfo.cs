using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace Kit.Grass
{
    public struct GrassPassCreateInfo
    {
        public Mesh mesh;
        public Material material;
        public RenderPassEvent passEvent;
    }
}
