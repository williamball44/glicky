"""Builds M_Grass (two-sided foliage, colour + wind from Tools/shaders/Grass*.hlsl, MPC_VoyagerGrass params)
and the grass-clump Nanite meshes (UVoyagerGrassBuilder, the Unity blade maths) under /Game/Voyager/Grass."""
import unreal

PROJECT = unreal.Paths.project_dir()
MAT = "/Game/Voyager/Grass/M_Grass"
MPC = "/Game/Voyager/Materials/MPC_VoyagerGrass"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mpc = eal.load_asset(MPC)

# Clump variants: (name, clump height, blades). Most clumps short and dense (the short clumps carry the extra
# "filler" blades Unity paid for with vertex donation), a few medium and tall.
CLUMPS = [
    ("SM_GrassClump_S0", 0.75, 260), ("SM_GrassClump_S1", 0.85, 240), ("SM_GrassClump_S2", 0.95, 220),
    ("SM_GrassClump_S3", 1.05, 200), ("SM_GrassClump_M0", 1.20, 160), ("SM_GrassClump_M1", 1.35, 150),
    ("SM_GrassClump_T0", 1.60, 130), ("SM_GrassClump_T1", 1.90, 120),
]


def custom_node(m, x, y, hlsl, out_type, inputs, outputs=()):
    c = mel.create_material_expression(m, unreal.MaterialExpressionCustom, x, y)
    c.set_editor_property("code", open(PROJECT + "Tools/shaders/" + hlsl, encoding="utf-8").read())
    c.set_editor_property("output_type", out_type)
    c.set_editor_property("description", hlsl)
    ins = []
    for nm in inputs:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", nm)
        ins.append(ci)
    c.set_editor_property("inputs", ins)
    outs = []
    for nm, t in outputs:
        co = unreal.CustomOutput()
        co.set_editor_property("output_name", nm)
        co.set_editor_property("output_type", t)
        outs.append(co)
    c.set_editor_property("additional_outputs", outs)
    return c


def mpc_param(m, x, y, name):
    n = mel.create_material_expression(m, unreal.MaterialExpressionCollectionParameter, x, y)
    n.set_editor_property("collection", mpc)
    n.set_editor_property("parameter_name", name)
    return n


if eal.does_asset_exist(MAT):
    m = eal.load_asset(MAT)
    mel.delete_all_material_expressions(m)
else:
    m = tools.create_asset("M_Grass", "/Game/Voyager/Grass", unreal.Material, unreal.MaterialFactoryNew())
m.set_editor_property("two_sided", True)
m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
m.set_editor_property("used_with_instanced_static_meshes", True)
m.set_editor_property("used_with_nanite", True)
m.set_editor_property("max_world_position_offset_displacement", 80.0)

F3, F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT3, unreal.CustomMaterialOutputType.CMOT_FLOAT1
col = custom_node(m, -500, -200, "GrassColor.hlsl", F3,
                  ["VC", "WP", "Rnd", "RootCol", "TipCol", "LushCol", "DryCol"], [("SSS", F3), ("AO", F1)])
vc = mel.create_material_expression(m, unreal.MaterialExpressionVertexColor, -900, -400)
mel.connect_material_expressions(vc, "", col, "VC")
wp = mel.create_material_expression(m, unreal.MaterialExpressionWorldPosition, -900, -320)
mel.connect_material_expressions(wp, "", col, "WP")
rnd = mel.create_material_expression(m, unreal.MaterialExpressionPerInstanceRandom, -900, -240)
mel.connect_material_expressions(rnd, "", col, "Rnd")
yy = -160
for nm, pn in [("RootCol", "RootColor"), ("TipCol", "TipColor"), ("LushCol", "LushColor"), ("DryCol", "DryColor")]:
    mel.connect_material_expressions(mpc_param(m, -900, yy, pn), "", col, nm)
    yy += 80
mel.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
mel.connect_material_property(col, "SSS", unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
mel.connect_material_property(col, "AO", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
rough = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 100)
rough.set_editor_property("r", 0.62)
mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
spec = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 180)
spec.set_editor_property("r", 0.3)
mel.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)

wind = custom_node(m, -500, 400, "GrassWind.hlsl", F3,
                   ["VC", "WP", "Time", "WindDir", "WindStrength", "WindSpeed", "Wind"])
vc2 = mel.create_material_expression(m, unreal.MaterialExpressionVertexColor, -900, 300)
mel.connect_material_expressions(vc2, "", wind, "VC")
wp2 = mel.create_material_expression(m, unreal.MaterialExpressionWorldPosition, -900, 380)
wp2.set_editor_property("world_position_shader_offset", unreal.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
mel.connect_material_expressions(wp2, "", wind, "WP")
tm = mel.create_material_expression(m, unreal.MaterialExpressionTime, -900, 460)
mel.connect_material_expressions(tm, "", wind, "Time")
yy = 540
for nm in ["WindDir", "WindStrength", "WindSpeed", "Wind"]:
    mel.connect_material_expressions(mpc_param(m, -900, yy, nm), "", wind, nm)
    yy += 80
mel.connect_material_property(wind, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
mel.recompile_material(m)
eal.save_loaded_asset(m)
print("M_Grass built")

for i, (name, height, blades) in enumerate(CLUMPS):
    mesh = unreal.VoyagerGrassBuilder.build_grass_clump(f"/Game/Voyager/Grass/{name}", m, 101 + i * 7, height, blades, 45.0, 38.0, 1.5)
    eal.save_loaded_asset(mesh)
    print("clump", name, mesh.get_num_triangles(0) if hasattr(mesh, "get_num_triangles") else "")
