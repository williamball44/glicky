// Body of the colour Custom node in M_Grass (inserted by Tools/build_grass.py). Port of the Unity
// GrassBlades.shader fragment colour. Shares Noise() and the dry/lush/tuft/patch fields with TerraGround.hlsl's
// carpet colour, so the ground under and beyond the grass matches it.
// Inputs: VC (vertex colour, sRGB-encoded by the mesh build), WP (world cm), Rnd (per-instance random),
// RootCol, TipCol, LushCol, DryCol. Outputs: return = base colour; SSS = subsurface (backlit) colour; AO.
struct VGC
{
    float Hash(float2 p) { p = frac(p * float2(123.34, 456.21)); p += dot(p, p + 45.32); return frac(p.x * p.y); }
    float Noise(float2 p)
    {
        float2 i = floor(p), f = frac(p);
        float2 u = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(Hash(i), Hash(i + float2(1, 0)), u.x), lerp(Hash(i + float2(0, 1)), Hash(i + float2(1, 1)), u.x), u.y);
    }
    float Lin(float s) { return s <= 0.04045 ? s / 12.92 : pow((s + 0.055) / 1.055, 2.4); }
};
VGC g;
float h = g.Lin(VC.r);         // height along the blade, 0 root .. 1 tip
float blade = g.Lin(VC.g);     // per-blade random
float2 p = WP.xy / 100.0;

float dry = smoothstep(0.55, 0.75, g.Noise(p * 0.018 + 3.1) * 0.7 + g.Noise(p * 0.07 + 7.7) * 0.3);
float lush = smoothstep(0.5, 0.75, g.Noise(p * 0.025 + 40.0));
float3 tip = lerp(TipCol, LushCol, lush);
tip = lerp(tip, DryCol, saturate(dry * 0.85 + (blade - 0.85) * 3.0));
tip *= 0.8 + 0.4 * blade;
tip *= lerp(0.93, 1.07, Rnd);
// Tufts and patches: some clumps darker and bluer, some lighter, so the field isn't one flat green.
float tuft = g.Noise(p * 0.9 + 5.3);
float patch = g.Noise(p * 0.12 + 9.1) * 0.6 + g.Noise(p * 0.04 + 2.7) * 0.4;
tip *= lerp(0.74, 1.12, saturate(patch * 0.8 + tuft * 0.4));
tip = lerp(tip, tip * float3(0.85, 0.95, 1.05), saturate(0.6 - patch));

SSS = tip * 0.55 * smoothstep(0.2, 1.0, h);            // blades glow when backlit
AO = lerp(0.32, 1.0, smoothstep(0.0, 0.7, h));          // darker roots between the blades
return lerp(RootCol, tip, smoothstep(0.0, 0.85, h));
