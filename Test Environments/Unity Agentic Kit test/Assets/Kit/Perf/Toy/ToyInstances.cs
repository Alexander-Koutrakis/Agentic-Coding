using Unity.Profiling;
using UnityEngine;

namespace Kit.Perf.Toy
{
    // Toy rendering feature for proving the perf harness: N GPU-instanced quads, positions from a fixed seed so
    // every sweep point sees the same layout rule. Not a real feature; the point is a cost that scales with N.
    public class ToyInstances : MonoBehaviour
    {
        public const string MarkerName = "Kit.Toy.Instances";
        public const int MaxCount = 100_000;

        static readonly ProfilerMarker Marker = new ProfilerMarker(ProfilerCategory.Scripts, MarkerName);

        // Visible area at the test camera (z = -15, 60 degree vertical fov, 16:9) is about 31 x 17 units.
        const float HalfWidth = 15f;
        const float HalfHeight = 8f;
        const float QuadSize = 0.15f;

        Matrix4x4[] _matrices;
        Mesh _mesh;
        Material _material;
        int _count;

        public int Count => _count;

        public void Init(int seed)
        {
            // Quad mesh from a primitive; the temporary object is destroyed at once.
            GameObject tmp = GameObject.CreatePrimitive(PrimitiveType.Quad);
            _mesh = tmp.GetComponent<MeshFilter>().sharedMesh;
            Destroy(tmp);

            Shader shader = Shader.Find("Universal Render Pipeline/Unlit");
            if (shader == null)
            {
                throw new System.InvalidOperationException("Shader 'Universal Render Pipeline/Unlit' not found");
            }
            _material = new Material(shader) { enableInstancing = true };

            var rng = new System.Random(seed);
            _matrices = new Matrix4x4[MaxCount];
            for (int i = 0; i < MaxCount; i++)
            {
                var pos = new Vector3(
                    (float)(rng.NextDouble() * 2 - 1) * HalfWidth,
                    (float)(rng.NextDouble() * 2 - 1) * HalfHeight,
                    (float)rng.NextDouble());
                _matrices[i] = Matrix4x4.TRS(pos, Quaternion.identity, Vector3.one * QuadSize);
            }
        }

        public void SetCount(int count)
        {
            _count = Mathf.Clamp(count, 0, MaxCount);
        }

        void Update()
        {
            if (_count == 0)
            {
                return;
            }

            using (Marker.Auto())
            {
                var rp = new RenderParams(_material);
                Graphics.RenderMeshInstanced(rp, _mesh, 0, _matrices, _count, 0);
            }
        }

        void OnDestroy()
        {
            if (_material != null)
            {
                Destroy(_material);
            }
        }
    }
}
