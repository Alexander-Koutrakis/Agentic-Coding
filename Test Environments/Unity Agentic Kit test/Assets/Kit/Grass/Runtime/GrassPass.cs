using System;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.RenderGraphModule;
using UnityEngine.Rendering.Universal;

namespace Kit.Grass
{
    public sealed class GrassPass : ScriptableRenderPass
    {
        const string CullName = "Kit.Grass.Cull";
        const string DrawName = "Kit.Grass.Draw";
        const int PlaneCount = 6;

        static readonly int BladesId = Shader.PropertyToID("_Blades");
        static readonly int VisibleId = Shader.PropertyToID("_Visible");

        readonly Mesh mesh;
        readonly Material material;
        readonly Plane[] planes = new Plane[PlaneCount];
        readonly Vector4[] planeVectors = new Vector4[PlaneCount];
        readonly ProfilingSampler cullSampler = new ProfilingSampler(CullName);
        readonly ProfilingSampler drawSampler = new ProfilingSampler(DrawName);
        readonly BaseRenderFunc<GrassCullData, ComputeGraphContext> cullFunc;
        readonly BaseRenderFunc<GrassPassData, RasterGraphContext> drawFunc;

        // Set by GrassSystem whenever it replaces the culler. The pass never disposes it.
        public GrassCuller Culler { get; set; }

        GrassPass(in GrassPassCreateInfo info)
        {
            mesh = info.mesh;
            material = info.material;
            renderPassEvent = info.passEvent;
            cullFunc = ExecuteCull;
            drawFunc = ExecuteDraw;
        }

        public static GrassPass Create(in GrassPassCreateInfo info)
        {
            if (info.mesh == null)
                throw new ArgumentException("mesh is required", nameof(info));
            if (info.material == null)
                throw new ArgumentException("material is required", nameof(info));
            return new GrassPass(in info);
        }

        public override void RecordRenderGraph(RenderGraph renderGraph, ContextContainer frameData)
        {
            GrassCuller culler = Culler;
            if (culler == null)
                return;

            UniversalCameraData cameraData = frameData.Get<UniversalCameraData>();
            UniversalResourceData resources = frameData.Get<UniversalResourceData>();

            GeometryUtility.CalculateFrustumPlanes(cameraData.camera, planes);
            for (int i = 0; i < PlaneCount; i++)
            {
                Vector3 n = planes[i].normal;
                planeVectors[i] = new Vector4(n.x, n.y, n.z, planes[i].distance);
            }

            BufferHandle blades = renderGraph.ImportBuffer(culler.Blades);
            BufferHandle visible = renderGraph.ImportBuffer(culler.Visible);
            BufferHandle args = renderGraph.ImportBuffer(culler.Args);

            using (var builder = renderGraph.AddComputePass(CullName, out GrassCullData cullData, cullSampler))
            {
                cullData.culler = culler;
                cullData.planes = planeVectors;
                builder.UseBuffer(blades, AccessFlags.Read);
                builder.UseBuffer(visible, AccessFlags.ReadWrite);
                builder.UseBuffer(args, AccessFlags.Write);
                builder.AllowPassCulling(false);
                builder.SetRenderFunc(cullFunc);
            }

            using (var builder = renderGraph.AddRasterRenderPass(DrawName, out GrassPassData drawData, drawSampler))
            {
                drawData.blades = culler.Blades;
                drawData.visible = culler.Visible;
                drawData.args = culler.Args;
                drawData.mesh = mesh;
                drawData.material = material;
                builder.UseBuffer(blades, AccessFlags.Read);
                builder.UseBuffer(visible, AccessFlags.Read);
                builder.UseBuffer(args, AccessFlags.Read);
                builder.SetRenderAttachment(resources.activeColorTexture, 0, AccessFlags.ReadWrite);
                builder.SetRenderAttachmentDepth(resources.activeDepthTexture, AccessFlags.ReadWrite);
                builder.AllowPassCulling(false);
                builder.AllowGlobalStateModification(true); // SetGlobalBuffer for _Blades and _Visible
                builder.SetRenderFunc(drawFunc);
            }
        }

        static void ExecuteCull(GrassCullData data, ComputeGraphContext context)
        {
            data.culler.Record(context.cmd, data);
        }

        static void ExecuteDraw(GrassPassData data, RasterGraphContext context)
        {
            RasterCommandBuffer cmd = context.cmd;
            cmd.SetGlobalBuffer(BladesId, data.blades);
            cmd.SetGlobalBuffer(VisibleId, data.visible);
            cmd.DrawMeshInstancedIndirect(data.mesh, 0, data.material, 0, data.args, 0);
        }
    }
}
