using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace Kit.Grass
{
    public sealed class GrassCuller : IDisposable
    {
        public const int GroupSize = 64; // must match [numthreads(64,1,1)] in GrassCull.compute
        public const int MaxBlades = 65535 * GroupSize;
        const string KernelName = "CSMain";
        const uint ArgsInstanceCountOffsetBytes = sizeof(uint); // instanceCount is the second uint of the indirect args

        static readonly int BladesId = Shader.PropertyToID("_Blades");
        static readonly int VisibleId = Shader.PropertyToID("_Visible");
        static readonly int PlanesId = Shader.PropertyToID("_FrustumPlanes");
        static readonly int CountId = Shader.PropertyToID("_BladeCount");
        static readonly int CenterId = Shader.PropertyToID("_BoundCenter");
        static readonly int RadiusId = Shader.PropertyToID("_BoundRadius");

        readonly ComputeShader shader;
        readonly int kernel;
        readonly Vector4 boundCenter;
        readonly float boundRadius;

        public int BladeCount { get; }
        public GraphicsBuffer Blades { get; }
        public GraphicsBuffer Visible { get; }
        public GraphicsBuffer Args { get; }

        GrassCuller(in GrassCullerCreateInfo info, int kernel)
        {
            shader = info.cullShader;
            this.kernel = kernel;
            boundCenter = info.boundCenter;
            boundRadius = info.boundRadius;
            BladeCount = info.bladeCount;

            int slots = Mathf.Max(1, info.bladeCount); // a GraphicsBuffer needs at least one element
            try
            {
                Blades = new GraphicsBuffer(GraphicsBuffer.Target.Structured, slots, 64);
                Visible = new GraphicsBuffer(GraphicsBuffer.Target.Append, slots, sizeof(uint));
                Args = new GraphicsBuffer(GraphicsBuffer.Target.IndirectArguments, 5, sizeof(uint));
                Args.SetData(new uint[] { info.indexCount, 0, 0, 0, 0 });
            }
            catch
            {
                // Construction failed halfway: release what exists, then let the caller see the error.
                Blades?.Dispose();
                Visible?.Dispose();
                Args?.Dispose();
                throw;
            }
        }

        public static GrassCuller Create(in GrassCullerCreateInfo info)
        {
            if (info.cullShader == null)
                throw new ArgumentException("cullShader is required", nameof(info));
            if (!info.cullShader.HasKernel(KernelName))
                throw new ArgumentException("cullShader has no kernel " + KernelName, nameof(info));
            if (info.bladeCount < 0 || info.bladeCount > MaxBlades)
                throw new ArgumentException("bladeCount must be in 0.." + MaxBlades, nameof(info));
            if (!(info.boundRadius >= 0f))
                throw new ArgumentException("boundRadius must be >= 0", nameof(info));
            if (info.indexCount == 0)
                throw new ArgumentException("indexCount must be > 0", nameof(info));

            return new GrassCuller(in info, info.cullShader.FindKernel(KernelName));
        }

        // Once per placement, never per frame.
        public void Upload(Matrix4x4[] matrices, int count)
        {
            if (matrices == null)
                throw new ArgumentNullException(nameof(matrices));
            if (count < 0 || count > BladeCount || count > matrices.Length)
                throw new ArgumentException("count must be in 0..BladeCount and <= matrices.Length", nameof(count));
            if (count > 0)
                Blades.SetData(matrices, 0, 0, count);
        }

        // The only per-frame work: reset the counter, bind, dispatch, copy the counter into the draw args.
        public void Record(ComputeCommandBuffer cmd, GrassCullData data)
        {
            cmd.SetBufferCounterValue(Visible, 0);
            int groups = (BladeCount + GroupSize - 1) / GroupSize;
            if (groups > 0)
            {
                cmd.SetComputeBufferParam(shader, kernel, BladesId, Blades);
                cmd.SetComputeBufferParam(shader, kernel, VisibleId, Visible);
                cmd.SetComputeVectorArrayParam(shader, PlanesId, data.planes);
                cmd.SetComputeIntParam(shader, CountId, BladeCount);
                cmd.SetComputeVectorParam(shader, CenterId, boundCenter);
                cmd.SetComputeFloatParam(shader, RadiusId, boundRadius);
                cmd.DispatchCompute(shader, kernel, groups, 1, 1);
            }
            cmd.CopyCounterValue(Visible, Args, ArgsInstanceCountOffsetBytes);
        }

        public void Dispose()
        {
            Blades.Dispose();
            Visible.Dispose();
            Args.Dispose();
        }
    }
}
