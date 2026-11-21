// Body of the Custom node in M_TerraGround (inserted by Tools/build_ground_material.py).
// Port of the Unity StylizedTerrain shader: procedural layer weights, 2-sample anti-tiling, height blending,
// triplanar rock, macro colour variation and the short-grass "carpet" where the PCG grass ends.
// Inputs: WP (world cm), Ng (vertex normal), Cam (camera world cm), Root/Tip/Lush/DryCol (grass colours,
// MPC_VoyagerGrass), GrassFar (x = grass end distance m), Params (x = blend depth, y = anti-tile, z = normal
// strength, w = carpet strength), texture objects {Turf,Dry,Dirt,Rock}{C,N,H}, and Mask (T_TerraGrassMask).
// Outputs: return = base colour; NormalTS; Bare (0..1, bare dirt).
struct VG
{
    float Hash(float2 p) { p = frac(p * float2(123.34, 456.21)); p += dot(p, p + 45.32); return frac(p.x * p.y); }
    float Noise(float2 p)
    {
        float2 i = floor(p), f = frac(p);
        float2 u = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(Hash(i), Hash(i + float2(1, 0)), u.x), lerp(Hash(i + float2(0, 1)), Hash(i + float2(1, 1)), u.x), u.y);
    }
    float Fbm(float2 p, int o)
    {
        float s = 0, a = 0.5, n = 0;
        for (int k = 0; k < o; k++) { s += a * Noise(p); n += a; a *= 0.5; p = p * 2.03 + 17.1; }
        return s / n;
    }
    float3 UnpackN(float4 s, float strength)
    {
        float2 xy = (s.xy * 2.0 - 1.0) * strength;
        return float3(xy, sqrt(saturate(1.0 - dot(xy, xy))));
    }
    // Anti-tiling (Inigo Quilez technique 3): a slow noise picks between offset copies and cross-fades two,
    // biased by the height map so the seam follows the texture's own detail.
    void Layer(Texture2D C, SamplerState CS, Texture2D N, SamplerState NS, Texture2D H, SamplerState HS,
               float2 p, float tile, float k, float anti, float ns, out float3 col, out float3 nrm, out float hgt)
    {
        float2 uv = p / tile, dx = ddx(uv), dy = ddy(uv);
        float l = k * 8.0, ia = floor(l);
        float s = smoothstep(0.25, 0.75, frac(l)) * anti;
        float2 ua = uv + sin(float2(3.0, 7.0) * ia);
        float4 a = Texture2DSampleGrad(C, CS, ua, dx, dy);
        float4 na = Texture2DSampleGrad(N, NS, ua, dx, dy);
        float ha = Texture2DSampleGrad(H, HS, ua, dx, dy).r;
        if (s > 0.001)
        {
            float2 ub = uv + sin(float2(3.0, 7.0) * (ia + 1.0));
            float4 b = Texture2DSampleGrad(C, CS, ub, dx, dy);
            float4 nb = Texture2DSampleGrad(N, NS, ub, dx, dy);
            float hb = Texture2DSampleGrad(H, HS, ub, dx, dy).r;
            float t = saturate(s + (hb - ha) * 0.5);
            a = lerp(a, b, t); na = lerp(na, nb, t); ha = lerp(ha, hb, t);
        }
        col = a.rgb; nrm = UnpackN(na, ns); hgt = ha;
    }
    float3 Carpet(float2 p, float3 root, float3 tip, float3 lush, float3 dry)
    {
        float d = smoothstep(0.55, 0.75, Noise(p * 0.018 + 3.1) * 0.7 + Noise(p * 0.07 + 7.7) * 0.3);
        float l = smoothstep(0.5, 0.75, Noise(p * 0.025 + 40.0));
        float3 t = lerp(tip, lush, l);
        t = lerp(t, dry, saturate(d * 0.85));
        float tuft = Noise(p * 0.9 + 5.3);
        float patch = Noise(p * 0.12 + 9.1) * 0.6 + Noise(p * 0.04 + 2.7) * 0.4;
        t *= lerp(0.74, 1.12, saturate(patch * 0.8 + tuft * 0.4));
        return lerp(root, t, 0.55);
    }
};
VG g;
float2 p = WP.xy / 100.0;                 // metres, X north / Y east
float hM = WP.z / 100.0;
float3 n = normalize(Ng);
float dist = length(Cam - WP) / 100.0;
float far = smoothstep(40.0, 220.0, dist);

// Layer weights: 0 turf, 1 dry turf, 2 dirt, 3 rock, 4 riverbed (dirt, darker and wet-toned).
float dryW = smoothstep(0.52, 0.68, g.Fbm(p * 0.008, 3));
float w[5];
w[0] = 1.0 - dryW; w[1] = dryW; w[2] = 0; w[3] = 0; w[4] = 0;
// Bare patches come from the shared grass mask (T_TerraGrassMask.b, 1 m texels over 2048 m), the same
// texture PCG reads, so grass never grows on them. A little noise breaks up the texel-smooth edges.
float2 muv = (p + 1024.0) / 2048.0;   // u = X (north), v = Y (east), as PCG samples it
float inside = all(muv > 0.0) && all(muv < 1.0) ? 1.0 : 0.0;
float maskB = Texture2DSampleLevel(Mask, MaskSampler, muv, 0).b * inside;
float edge = (g.Noise(p * 2.2 + 8.7) - 0.5) * 0.35;
float bare = smoothstep(0.15, 0.6, saturate(maskB + edge * step(0.02, maskB))) * smoothstep(0.9, 0.96, n.z);
w[0] *= 1.0 - bare; w[1] *= 1.0 - bare; w[2] += bare;
float rock = smoothstep(0.89, 0.78, n.z);  // about 27-38 degrees, as in Unity
for (int i0 = 0; i0 < 5; i0++) w[i0] *= 1.0 - rock;
w[3] += rock;
float bed = 1.0 - smoothstep(18.2, 19.8, hM);
for (int i1 = 0; i1 < 5; i1++) w[i1] *= 1.0 - bed;
w[4] += bed;

float k = g.Noise(p * 0.09 + 2.2);
float anti = Params.y, ns = Params.z;
float3 c[5]; float3 nt[5]; float h[5];
for (int i2 = 0; i2 < 5; i2++) { c[i2] = 0; nt[i2] = float3(0, 0, 1); h[i2] = 0; }
if (w[0] > 0.005) g.Layer(TurfC, TurfCSampler, TurfN, TurfNSampler, TurfH, TurfHSampler, p, 2.5, k, anti, ns, c[0], nt[0], h[0]);
if (w[1] > 0.005) g.Layer(DryC, DryCSampler, DryN, DryNSampler, DryH, DryHSampler, p, 3.0, k, anti, ns, c[1], nt[1], h[1]);
if (w[2] > 0.005 || w[4] > 0.005)
{
    g.Layer(DirtC, DirtCSampler, DirtN, DirtNSampler, DirtH, DirtHSampler, p, 2.5, k, anti, ns, c[2], nt[2], h[2]);
    nt[4] = nt[2]; h[4] = h[2];
}
if (w[3] > 0.005)
{
    g.Layer(RockC, RockCSampler, RockN, RockNSampler, RockH, RockHSampler, p, 4.0, k, anti, ns, c[3], nt[3], h[3]);
    // Triplanar colour on cliffs so the rock doesn't stretch.
    float3 bw = pow(abs(n), 4.0); bw /= (bw.x + bw.y + bw.z);
    float2 pxz = float2(p.x, hM), pyz = float2(p.y, hM);
    c[3] = Texture2DSample(RockC, RockCSampler, pyz / 4.0).rgb * bw.x + Texture2DSample(RockC, RockCSampler, pxz / 4.0).rgb * bw.y + c[3] * bw.z;
}
// Tints: turf (moss scan) toward a muted olive so it continues the grass roots; dirt darker and browner.
float l0 = dot(c[0], float3(0.3, 0.59, 0.11));
c[0] = lerp(float3(l0, l0, l0), c[0], 0.6) * float3(0.72, 0.74, 0.5);
float l2 = dot(c[2], float3(0.3, 0.59, 0.11));
c[2] = lerp(float3(l2, l2, l2), c[2], 0.75) * float3(0.56, 0.47, 0.37);
c[4] = c[2] * float3(0.7, 0.68, 0.66);

// Height blending: where layers meet, the higher surface wins.
float hw[5]; float top = -10.0;
for (int i3 = 0; i3 < 5; i3++) { hw[i3] = w[i3] > 0.005 ? h[i3] + w[i3] : -10.0; top = max(top, hw[i3]); }
float total = 0;
for (int i4 = 0; i4 < 5; i4++) { hw[i4] = max(hw[i4] - (top - Params.x), 0.0); total += hw[i4]; }
float3 albedo = 0, nrm = 0;
for (int i5 = 0; i5 < 5; i5++) { float f = hw[i5] / max(total, 1e-4); albedo += c[i5] * f; nrm += nt[i5] * f; }

// Large-scale variation: sunny swathes and darker patches.
float m = g.Fbm(p * 0.006, 4), m2 = g.Noise(p * 0.024 + 5.0);
albedo *= lerp(0.86, 1.12, m * 0.7 + m2 * 0.3);
albedo = lerp(albedo, albedo * float3(1.12, 1.06, 0.78), smoothstep(0.5, 0.8, m) * (w[0] + w[1]) * 0.6);

// Short-grass carpet: beyond the PCG grass's reach the turf takes on the grass's colour, ramping in over the
// last half of the grass distance so the end of the grass can't be told apart by colour.
float carpet = smoothstep(GrassFar.x * 0.45, GrassFar.x, dist) * (w[0] + w[1]) * Params.w;
albedo = lerp(albedo, g.Carpet(p, RootCol, TipCol, LushCol, DryCol), carpet);

nrm.xy *= 1.0 - far * 0.7;
NormalTS = normalize(float3(nrm.xy, max(nrm.z, 0.2)));
Bare = bare;
return albedo;
