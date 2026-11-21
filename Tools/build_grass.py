"""Ghost of Tsushima style grass: builds T_GustNoise (import), M_GrassPatch and the grass patch meshes.

Each patch is a 1 m tile of ~120 straight blade strips (UVoyagerGrassBuilder::BuildGrassPatch); the material rebuilds
every blade (Tools/shaders/GrassBladeWPO.hlsl: world-space clumps, grass mask, gradient culling, quadratic Bezier
wind bend, gust texture, player push, edge-on thickening, bent/rounded normals) and colours it
(GrassPatchColor.hlsl). Two mesh sets for an A/B: SM_GrassPatch_* (3 classic LODs) and SM_GrassPatchN_* (Nanite).
Run Tools/bake_gust_noise.py first (normal Python)."""
import unreal

PROJECT = unreal.Paths.project_dir()
MAT = "/Game/Voyager/Grass/M_GrassPatch"
MPC = "/Game/Voyager/Materials/MPC_VoyagerGrass"
MASK = "/Game/Voyager/Textures/T_TerraGrassMask"
GUST = "/Game/Voyager/Textures/T_GustNoise"
PATCHES = 6
BLADES = 120
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mpc = eal.load_asset(MPC)

# ---- Gust noise texture (tileable, linear, wraps) ----
t = unreal.AssetImportTask()
t.filename = PROJECT + "Tools/out/T_GustNoise.png"
t.destination_path = "/Game/Voyager/Textures"
t.destination_name = "T_GustNoise"
t.automated = True
t.replace_existing = True
tools.import_asset_tasks([t])
gust_tex = eal.load_asset(GUST)
gust_tex.set_editor_property("srgb", False)
gust_tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE)
eal.save_loaded_asset(gust_tex)

F3, F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT3, unreal.CustomMaterialOutputType.CMOT_FLOAT1


def node(cls, x, y, **props):
    n = mel.create_material_expression(m, cls, x, y)
    for k, v in props.items():
        n.set_editor_property(k, v)
    return n


def link(a, b, a_out="", b_in=""):
    mel.connect_material_expressions(a, a_out, b, b_in)


def custom(x, y, hlsl, inputs, outputs=()):
    c = node(unreal.MaterialExpressionCustom, x, y)
    c.set_editor_property("code", open(PROJECT + "Tools/shaders/" + hlsl, encoding="utf-8").read())
    c.set_editor_property("output_type", F3)
    c.set_editor_property("description", hlsl)
    ins = []
    for nm in inputs:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", nm)
        ins.append(ci)
    c.set_editor_property("inputs", ins)
    outs = []
    for nm, ty in outputs:
        co = unreal.CustomOutput()
        co.set_editor_property("output_name", nm)
        co.set_editor_property("output_type", ty)
        outs.append(co)
    c.set_editor_property("additional_outputs", outs)
    return c


def mpc_param(x, y, name):
    return node(unreal.MaterialExpressionCollectionParameter, x, y, collection=mpc, parameter_name=name)


def transform(x, y, src, dst):
    return node(unreal.MaterialExpressionTransform, x, y, transform_source_type=src, transform_type=dst)


def interp(x, y, src):
    vi = node(unreal.MaterialExpressionVertexInterpolator, x, y)
    link(src[0], vi, src[1], "")
    return vi


LOCAL = unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL
WORLD_S = unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD
TO_WORLD = unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD
TO_LOCAL = unreal.MaterialVectorCoordTransform.TRANSFORM_LOCAL

if eal.does_asset_exist(MAT):
    m = eal.load_asset(MAT)
    mel.delete_all_material_expressions(m)
else:
    m = tools.create_asset("M_GrassPatch", "/Game/Voyager/Grass", unreal.Material, unreal.MaterialFactoryNew())
m.set_editor_property("two_sided", True)
m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
m.set_editor_property("tangent_space_normal", False)
m.set_editor_property("used_with_instanced_static_meshes", True)
m.set_editor_property("used_with_nanite", True)
m.set_editor_property("max_world_position_offset_displacement", 110.0)

# ---- Vertex: per-blade rebuild ----
X = -2200
lp = node(unreal.MaterialExpressionLocalPosition, X, 0)
uv = [node(unreal.MaterialExpressionTextureCoordinate, X, 100 + i * 80, coordinate_index=i) for i in range(4)]
wp = node(unreal.MaterialExpressionWorldPosition, X, 450,
          world_position_shader_offset=unreal.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
zero = node(unreal.MaterialExpressionConstant, X, 530)
root3 = node(unreal.MaterialExpressionAppendVector, X + 200, 180)
link(uv[1], root3, "", "A"); link(zero, root3, "", "B")
rel = node(unreal.MaterialExpressionSubtract, X + 400, 100)
link(lp, rel, "", "A"); link(root3, rel, "", "B")
relw = transform(X + 600, 100, LOCAL, TO_WORLD)
link(rel, relw)
root_ws = node(unreal.MaterialExpressionSubtract, X + 800, 300)
link(wp, root_ws, "", "A"); link(relw, root_ws, "", "B")
cam = node(unreal.MaterialExpressionCameraPositionWS, X, 620)
tocam = node(unreal.MaterialExpressionSubtract, X + 200, 620)
link(cam, tocam, "", "A"); link(wp, tocam, "", "B")
tocam_l = transform(X + 400, 620, WORLD_S, TO_LOCAL)
link(tocam, tocam_l)
cam_l = node(unreal.MaterialExpressionNormalize, X + 600, 620)
link(tocam_l, cam_l)
axes = []
for i, vec in enumerate([(1, 0, 0), (0, 1, 0)]):
    c3 = node(unreal.MaterialExpressionConstant3Vector, X, 720 + i * 100, constant=unreal.LinearColor(vec[0], vec[1], vec[2], 1))
    tl = transform(X + 200, 720 + i * 100, WORLD_S, TO_LOCAL)
    link(c3, tl)
    axes.append(tl)
tm = node(unreal.MaterialExpressionTime, X, 940)
mask = node(unreal.MaterialExpressionTextureObject, X, 1020, texture=eal.load_asset(MASK))
gust = node(unreal.MaterialExpressionTextureObject, X, 1100, texture=gust_tex)

wpo_inputs = ["LP", "UV0", "UV1", "UV2", "UV3", "RootWS", "CamWS", "CamL", "AxL", "AyL", "Time", "Mask", "Gust",
              "WindDir", "WindStrength", "WindSpeed", "Wind", "GustScale", "GustScroll", "ClumpSize", "GrassEnd",
              "PlayerPos", "PlayerRadius"]
wpo = custom(-1000, 300, "GrassBladeWPO.hlsl", wpo_inputs, [("NormalL", F3), ("Shade", F1), ("GustOut", F1)])
for nm, src in [("LP", lp), ("UV0", uv[0]), ("UV1", uv[1]), ("UV2", uv[2]), ("UV3", uv[3]), ("RootWS", root_ws),
                ("CamWS", cam), ("CamL", cam_l), ("AxL", axes[0]), ("AyL", axes[1]), ("Time", tm), ("Mask", mask),
                ("Gust", gust)]:
    link(src, wpo, "", nm)
yy = 1200
for nm, pn in [("WindDir", "WindDir"), ("WindStrength", "WindStrength"), ("WindSpeed", "WindSpeed"), ("Wind", "Wind"),
               ("GustScale", "GustScale"), ("GustScroll", "GustScroll"), ("ClumpSize", "ClumpSize"),
               ("GrassEnd", "GrassEndDistance"), ("PlayerPos", "PlayerPos"), ("PlayerRadius", "PlayerRadius")]:
    link(mpc_param(X, yy, pn), wpo, "", nm)
    yy += 70
wpo_w = transform(-700, 300, LOCAL, TO_WORLD)
link(wpo, wpo_w)
mel.connect_material_property(wpo_w, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)

# Bent normal: local -> world in the vertex shader, interpolated, flipped on back faces.
n_w = transform(-700, 450, LOCAL, TO_WORLD)
link(wpo, n_w, "NormalL", "")
n_ps = interp(-500, 450, (n_w, ""))
sign = node(unreal.MaterialExpressionTwoSidedSign, -500, 550)
n_final = node(unreal.MaterialExpressionMultiply, -300, 450)
link(n_ps, n_final, "", "A"); link(sign, n_final, "", "B")
mel.connect_material_property(n_final, "", unreal.MaterialProperty.MP_NORMAL)

# ---- Pixel colour ----
shade_ps = interp(-700, -300, (wpo, "Shade"))
gust_ps = interp(-700, -220, (wpo, "GustOut"))
root_ps = interp(-700, -140, (root_ws, ""))
t_mask = node(unreal.MaterialExpressionComponentMask, -700, -520, r=False, g=True, b=False, a=False)
link(uv[0], t_mask)
rnd_mask = node(unreal.MaterialExpressionComponentMask, -700, -440, r=False, g=True, b=False, a=False)
link(uv[2], rnd_mask)
col = custom(-300, -300, "GrassPatchColor.hlsl",
             ["T", "Rnd", "RootWS", "Shade", "Gust", "RootCol", "TipCol", "LushCol", "DryCol", "GustCol"],
             [("SSS", F3), ("AO", F1)])
for nm, src in [("T", t_mask), ("Rnd", rnd_mask), ("RootWS", root_ps), ("Shade", shade_ps), ("Gust", gust_ps)]:
    link(src, col, "", nm)
yy = -700
for nm, pn in [("RootCol", "RootColor"), ("TipCol", "TipColor"), ("LushCol", "LushColor"), ("DryCol", "DryColor"),
               ("GustCol", "GustColor")]:
    link(mpc_param(-700, yy, pn), col, "", nm)
    yy -= 70
mel.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
mel.connect_material_property(col, "SSS", unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
mel.connect_material_property(col, "AO", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
mel.connect_material_property(node(unreal.MaterialExpressionConstant, -100, 100, r=0.55), "", unreal.MaterialProperty.MP_ROUGHNESS)
mel.connect_material_property(node(unreal.MaterialExpressionConstant, -100, 180, r=0.35), "", unreal.MaterialProperty.MP_SPECULAR)
mel.recompile_material(m)
eal.save_loaded_asset(m)
print("M_GrassPatch built")

# Nanite won the A/B (PIE, 157k patches): grass ~3.6 ms GPU vs ~6 ms for classic LODs, whose WPO also forces a
# separate velocity pass. Set GRASS_CLASSIC = True before exec'ing this file to build the classic set again.
SETS = (("SM_GrassPatchN_", True),) + ((("SM_GrassPatch_", False),) if globals().get("GRASS_CLASSIC", False) else ())
for i in range(PATCHES):
    for prefix, nanite in SETS:
        mesh = unreal.VoyagerGrassBuilder.build_grass_patch(f"/Game/Voyager/Grass/{prefix}{i}", m, 300 + i * 13, BLADES, 100.0, 38.0, 0.9, nanite)
        eal.save_loaded_asset(mesh)
print("patches built:", PATCHES, "x", len(SETS))
