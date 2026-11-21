// Pixel colour Custom node of M_GrassPatch, inserted by Tools/build_grass.py. Port of the Unity GrassBlades.shader
// colour with the Ghost of Tsushima root-to-tip ramp (pow(t, 1.5)). Shares Noise() and the dry/lush/tuft/patch fields
// with TerraGround.hlsl's carpet colour, so the ground beyond the grass matches it.
// Inputs: T (height along blade), Rnd (blade random), RootWS (world cm), Shade (clump tone), Gust (0..1 at the blade),
// RootCol, TipCol, LushCol, DryCol, GustCol. Outputs: return = base colour; SSS = subsurface (backlit) colour; AO.
struct VGP
{
    float Hash(float2 p) { p = frac(p * float2(123.34, 456.21)); p += dot(p, p + 45.32); return frac(p.x * p.y); }
    float Noise(float2 p)
    {
        float2 i = floor(p), f = frac(p);
        float2 u = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(Hash(i), Hash(i + float2(1, 0)), u.x), lerp(Hash(i + float2(0, 1)), Hash(i + float2(1, 1)), u.x), u.y);
    }
};
VGP g;
float2 p = RootWS.xy / 100.0;
float dry = smoothstep(0.55, 0.75, g.Noise(p * 0.018 + 3.1) * 0.7 + g.Noise(p * 0.07 + 7.7) * 0.3);
float lush = smoothstep(0.5, 0.75, g.Noise(p * 0.025 + 40.0));
float3 tip = lerp(TipCol, LushCol, lush);
tip = lerp(tip, DryCol, saturate(dry * 0.85 + (Rnd - 0.85) * 3.0));
tip *= 0.8 + 0.4 * Rnd;
float tuft = g.Noise(p * 0.9 + 5.3);
float patch = g.Noise(p * 0.12 + 9.1) * 0.6 + g.Noise(p * 0.04 + 2.7) * 0.4;
tip *= lerp(0.74, 1.12, saturate(patch * 0.8 + tuft * 0.4));
tip = lerp(tip, tip * float3(0.85, 0.95, 1.05), saturate(0.6 - patch));
tip *= lerp(0.9, 1.08, Shade);                                 // clumps differ slightly in tone
float3 albedo = lerp(RootCol, tip, pow(saturate(T), 1.5));
albedo = lerp(albedo, GustCol, Gust * T * 0.2);                // gusts flash the tips lighter
SSS = tip * 0.6 * smoothstep(0.15, 1.0, T);
AO = lerp(0.3, 1.0, smoothstep(0.0, 0.7, T));
return albedo;
