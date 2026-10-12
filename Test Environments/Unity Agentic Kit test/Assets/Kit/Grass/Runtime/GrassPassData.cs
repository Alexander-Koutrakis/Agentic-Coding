using UnityEngine;

namespace Kit.Grass
{
    // Render Graph pass data for the raster pass: references only, filled by assignment each frame.
    public sealed class GrassPassData
    {
        public GraphicsBuffer blades;
        public GraphicsBuffer visible;
        public GraphicsBuffer args;
        public Mesh mesh;
        public Material material;
    }
}
