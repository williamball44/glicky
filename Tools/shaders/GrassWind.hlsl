// Body of the World Position Offset Custom node in M_Grass (inserted by Tools/build_grass.py). Port of the
// Unity GrassBlades.shader wind: rolling gusts, per-blade flutter and a slow sway bend each blade from the root,
// growing with the square of the height along it, and drop the tip so the blade keeps roughly its length.
// Inputs: VC (vertex colour, sRGB-encoded), WP (vertex world cm), Time (s), WindDir (xy), WindStrength,
// WindSpeed, Wind (weather multiplier). Returns the offset in cm.
struct VGW
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
VGW g;
float t = g.Lin(VC.r);
float rnd = g.Lin(VC.g);
float heightCm = g.Lin(VC.b) * 100.0;
float2 pm = WP.xy / 100.0;
float2 dir = normalize(WindDir.xy + 1e-5);
float tm = Time * WindSpeed;
float wave = dot(pm, dir) * 0.045 - tm * 0.9;
float gust = pow(saturate(sin(wave) * 0.5 + 0.5), 3.0) * (0.6 + 0.4 * g.Noise(pm * 0.02 + tm * 0.1));
float flutter = sin(tm * 2.3 + rnd * 6.28 + pm.x * 0.7 + pm.y * 0.5) * 0.25;
float sway = sin(tm + pm.x * 0.15 + pm.y * 0.11) * 0.3;
float bend = min((sway + flutter + gust * 1.6 + 0.25) * WindStrength * max(Wind, 0.05), 1.2);
float k = bend * t * t;
return float3(dir * k * heightCm, -0.35 * k * bend * heightCm);
