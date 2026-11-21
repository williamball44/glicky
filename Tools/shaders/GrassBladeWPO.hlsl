// Vertex (World Position Offset) Custom node of M_GrassPatch, inserted by Tools/build_grass.py.
// Ghost of Tsushima style grass: every blade of a patch is a straight strip in the mesh; this rebuilds it per blade
// with the Unity grass maths (GrassBlades.compute + VoyagerClumps.hlsl), now in the vertex shader:
//   - world-space Voronoi clumps (0.9 m): shared height, tallest in the middle, lean outward, 5% long flopping blades
//   - grass mask (R density, G tall patches, B bare dirt) thins, shortens and hides blades
//   - gradient culling: each blade shrinks away at its own fraction of the grass distance (no visible ring)
//   - quadratic Bezier spine bent by wind (scrolling gust texture + sway + flutter) and the player's push,
//     keeping the blade's length
//   - view-space thickening so edge-on blades don't vanish, and wider blades with distance
// Everything is in the mesh's local space; AxL/AyL are world X/Y in local space, so world directions convert.
// Inputs: LP (local position), UV0 (across01, t), UV1 (root local cm), UV2 (unit height cm, random), UV3 (facing),
// RootWS (blade root, world cm), CamWS (camera, world cm), CamL (direction to camera, local, normalised),
// AxL, AyL, Time, Mask/MaskSampler, Gust/GustSampler, WindDir, WindStrength, WindSpeed, Wind, GustScale, GustScroll,
// ClumpSize, GrassEnd, PlayerPos, PlayerRadius.
// Returns the local offset. Outputs: NormalL (bent, rounded normal, local), Shade (clump tone 0..1), GustOut (0..1).
struct VGB
{
    uint Pcg(uint v)
    {
        uint s = v * 747796405u + 2891336453u;
        uint w = ((s >> ((s >> 28u) + 4u)) ^ s) * 277803737u;
        return (w >> 22u) ^ w;
    }
    float Rand(inout uint s) { s = Pcg(s); return s * (1.0 / 4294967296.0); }
    // Nearest jittered point among the 3x3 clump cells (VoyagerClumps.hlsl VoyagerClumpAt).
    void Clump(float2 xz, float size, out float2 centre, out float fromCentre, out float heightRand, out float cutRand)
    {
        float2 cp = xz / size;
        int2 ci = (int2)floor(cp);
        float best = 1e9; centre = cp; uint seed = 0;
        for (int y = -1; y <= 1; y++)
            for (int x = -1; x <= 1; x++)
            {
                int2 cc = ci + int2(x, y);
                uint hc = Pcg((uint)(cc.x + (1 << 20)) * 1597334677u ^ Pcg((uint)(cc.y + (1 << 20)) + 7u));
                float2 fp = cc + float2(hc & 0xffffu, hc >> 16) / 65535.0;
                float d = dot(cp - fp, cp - fp);
                if (d < best) { best = d; centre = fp; seed = hc; }
            }
        fromCentre = saturate(sqrt(best) / 0.8);
        heightRand = Rand(seed);
        cutRand = Rand(seed);
        centre *= size;
    }
};
VGB g;
const float3 up = float3(0, 0, 1);
float t = UV0.y;
float across = UV0.x * 2.0 - 1.0;
float2 rootL = UV1;
float unitH = UV2.x;
float rnd = UV2.y;
float3 side = float3(-UV3.y, UV3.x, 0.0);
float3 widthOff = LP - float3(rootL, t * unitH);            // this vertex's offset across the strip
float2 pm = RootWS.xy / 100.0;                               // blade root, metres
float dist = length(CamWS - RootWS) / 100.0;

// More per-blade randoms from the stored one.
uint bs = (uint)(rnd * 16777215.0) + 1u;
float r1 = g.Rand(bs), r2 = g.Rand(bs), r3 = g.Rand(bs), r4 = g.Rand(bs), r5 = g.Rand(bs);

// Grass mask.
float2 muv = (pm + 1024.0) / 2048.0;
float4 mask = all(muv > 0.0) && all(muv < 1.0) ? Texture2DSampleLevel(Mask, MaskSampler, muv, 0) : float4(0, 0, 0, 0);
float keep = r1 < mask.r * (1.0 - 0.93 * mask.b) ? 1.0 : 0.0;

// Clump.
float2 centre; float fromCentre, hR, cutR;
g.Clump(pm, ClumpSize, centre, fromCentre, hR, cutR);
float clumpH = lerp(0.5, 1.8, hR * hR);                      // most clumps short, a few tall
float tallMul = lerp(1.0, mask.g * 2.0, 0.5);
float h = unitH * (0.6 + 0.6 * r2) * tallMul * clumpH * (1.0 - 0.45 * fromCentre) * (1.0 - 0.55 * mask.b);
float leanAmt = 0.12 + 0.3 * r3 + fromCentre * 0.45;
if (r4 < 0.05) { h *= 1.6; leanAmt += 0.35; }                // the odd long blade that flops over

// Gradient culling: the blade ends at its own fraction of the grass distance and shrinks before it.
float cut = GrassEnd * lerp(0.5, 1.0, saturate(0.35 * cutR + 0.65 * r5));
float alive = keep * (1.0 - smoothstep(cut * 0.65, cut, dist));
h *= alive;

// Lean: away from the clump centre, with some scatter (world), converted to local.
float2 away = pm - centre;
float ang = atan2(away.y, away.x + 1e-5) + (r3 - 0.5) * 1.4;
float2 leanW = float2(cos(ang), sin(ang)) * leanAmt * h;

// Wind: a gust texture scrolling along the wind, plus a slow sway and per-blade flutter.
float2 dirW = normalize(WindDir.xy + 1e-5);
float tm = Time * WindSpeed;
float gustN = Texture2DSampleLevel(Gust, GustSampler, pm * GustScale - dirW * tm * GustScroll, 0).r;
float gust = pow(saturate(gustN * 1.5 - 0.3), 2.0);
float flutter = sin(tm * 2.3 + rnd * 6.28 + pm.x * 0.7 + pm.y * 0.5) * 0.25;
float sway = sin(tm + pm.x * 0.15 + pm.y * 0.11) * 0.3;
float bend = (sway + flutter + gust * 1.8 + 0.25) * WindStrength * max(Wind, 0.05);
float2 windW = dirW * bend * h;

// Player push: blades flatten outward around the player (MPC PlayerPos, world cm).
float2 toBlade = pm - PlayerPos.xy / 100.0;
float pd = length(toBlade);
float2 pushW = (pd > 1e-3 ? toBlade / pd : float2(0, 0)) * saturate(1.0 - pd / max(PlayerRadius, 0.01)) * h * 1.2;

float2 tipW = leanW + windW + pushW;
float3 tipL = tipW.x * AxL + tipW.y * AyL;
float horiz = length(tipL.xy);
if (horiz > 0.9 * h) { tipL.xy *= 0.9 * h / horiz; horiz = 0.9 * h; }
float tipZ = sqrt(max(h * h - horiz * horiz, 0.0));         // keep the blade's length while it bends

// Quadratic Bezier spine.
float3 P0 = float3(rootL, 0.0);
float3 P1 = P0 + up * h * 0.5;                               // stiff base
float3 P2 = P0 + float3(tipL.xy, tipZ);
float u = 1.0 - t;
float3 spine = u * u * P0 + 2.0 * u * t * P1 + t * t * P2;
float3 tangent = normalize(2.0 * u * (P1 - P0) + 2.0 * t * (P2 - P1) + float3(0, 0, 1e-4));

// Width: wider with distance (fewer blades survive in the coarser LODs), then edge-on thickening.
float widthMul = (1.0 + smoothstep(12.0, 30.0, dist) * 0.6 + smoothstep(30.0, 60.0, dist) * 1.0) * (alive > 0.0 ? 1.0 : 0.0);
float3 w = widthOff * widthMul;
float3 N0 = normalize(cross(tangent, side));
float edgeOn = 1.0 - abs(dot(N0, CamL));
float3 camSide = normalize(cross(up, CamL) + 1e-5);
float3 pos = spine + w + camSide * across * length(w) * edgeOn * 0.6 * (dot(camSide, side) >= 0.0 ? 1.0 : -1.0);

// Rounded, slightly upward normal (the field reads as a surface, not a fence).
float3 N = normalize(N0 + side * across * 0.5);
NormalL = normalize(lerp(N, up, 0.3));
Shade = saturate(hR * 0.6 + (1.0 - fromCentre) * 0.4);
GustOut = gust * min(Wind, 1.0);
return pos - LP;
