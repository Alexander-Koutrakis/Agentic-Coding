Shader "Kit/GrassInstanced"
{
    Properties
    {
        [MainColor] _BaseColor ("Base Color", Color) = (0.3, 0.6, 0.2, 1)
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            Cull Off // blade mesh is a single-sided strip; both faces must draw

            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _BaseColor;
            CBUFFER_END

            StructuredBuffer<float4x4> _Blades;
            StructuredBuffer<uint> _Visible;

            struct Attributes
            {
                float3 positionOS : POSITION;
                float3 normalOS : NORMAL;
                uint instanceID : SV_InstanceID;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                half3 color : TEXCOORD0;
            };

            Varyings Vert(Attributes input)
            {
                float4x4 m = _Blades[_Visible[input.instanceID]];
                float3 positionWS = mul(m, float4(input.positionOS, 1.0)).xyz;
                half3 normalWS = normalize((half3)mul((float3x3)m, input.normalOS));

                Light light = GetMainLight();
                half3 lit = light.color * abs(dot(normalWS, light.direction)) + SampleSH(normalWS);

                Varyings output;
                output.positionCS = TransformWorldToHClip(positionWS);
                output.color = lit;
                return output;
            }

            half4 Frag(Varyings input) : SV_Target
            {
                return half4(input.color * _BaseColor.rgb, 1.0h);
            }
            ENDHLSL
        }
    }
}
