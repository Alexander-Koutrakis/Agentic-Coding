using UnityEngine;

namespace Kit.Grass
{
    // Render Graph pass data for the compute pass: references only, filled by assignment each frame.
    public sealed class GrassCullData
    {
        public GrassCuller culler;
        public Vector4[] planes;
    }
}
