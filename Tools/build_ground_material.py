"""Builds MPC_VoyagerGrass (shared grass/ground colours and wind) and M_TerraGround (the Terra landscape
material: one Custom node running Tools/shaders/TerraGround.hlsl), then assigns M_TerraGround to the landscape.
Re-run after editing the HLSL: the material is rebuilt from scratch."""
import unreal

PROJECT = unreal.Paths.project_dir()
MAT = "/Game/Voyager/Materials/M_TerraGround"
MPC = "/Game/Voyager/Materials/MPC_VoyagerGrass"
TEX = "/Game/Voyager/Textures/Ground"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

# ---- Material parameter collection: one source of truth for grass colours and wind ----
GRASS_VECTORS = {
    "RootColor": (0.06, 0.14, 0.03),
    "TipColor": (0.45, 0.62, 0.18),
    "LushColor": (0.28, 0.55, 0.16),
    "DryColor": (0.72, 0.66, 0.32),
    "GustColor": (0.85, 0.9, 0.55),
    "WindDir": (1.0, 0.35, 0.0),
    "PlayerPos": (0.0, 0.0, -100000.0),   # world cm; set by the player each frame (step 5); far away until then
}
GRASS_SCALARS = {
    "GrassEndDistance": 80.0,   # m: blades shrink away by here (gradient culling); the ground carpet takes over
    "WindStrength": 0.45, "WindSpeed": 1.3, "Wind": 1.0,
    "GustScale": 0.02,          # gust texture tiles every 50 m
    "GustScroll": 0.06,         # texture widths per second at WindSpeed 1
    "ClumpSize": 0.9,           # m, Voronoi clump size
    "PlayerRadius": 1.5,        # m, grass push radius around the player
}

if eal.does_asset_exist(MPC):
    mpc = eal.load_asset(MPC)
else:
    mpc = tools.create_asset("MPC_VoyagerGrass", "/Game/Voyager/Materials", unreal.MaterialParameterCollection,
                             unreal.MaterialParameterCollectionFactoryNew())
# Update parameters IN PLACE. Each parameter has a GUID that materials store; replacing the list mints new
# GUIDs and silently breaks every material that references the collection (its nodes load as "None").
def upsert(list_prop, cls, values, make_value):
    params = list(mpc.get_editor_property(list_prop))
    by_name = {str(p.get_editor_property("parameter_name")): i for i, p in enumerate(params)}
    for k, v in values.items():
        if k in by_name:
            p = params[by_name[k]]
        else:
            p = cls()
            p.set_editor_property("parameter_name", k)
            params.append(p)
            by_name[k] = len(params) - 1
        p.set_editor_property("default_value", make_value(v))
        params[by_name[k]] = p
    mpc.set_editor_property(list_prop, params)

upsert("vector_parameters", unreal.CollectionVectorParameter, GRASS_VECTORS, lambda v: unreal.LinearColor(v[0], v[1], v[2], 1.0))
upsert("scalar_parameters", unreal.CollectionScalarParameter, GRASS_SCALARS, float)
eal.save_loaded_asset(mpc)

# ---- Landscape material ----
if eal.does_asset_exist(MAT):
    m = eal.load_asset(MAT)
    mel.delete_all_material_expressions(m)
else:
    m = tools.create_asset("M_TerraGround", "/Game/Voyager/Materials", unreal.Material, unreal.MaterialFactoryNew())

X = -1400
def node(cls, x, y):
    return mel.create_material_expression(m, cls, x, y)

custom = node(unreal.MaterialExpressionCustom, -500, 0)
custom.set_editor_property("code", open(PROJECT + "Tools/shaders/TerraGround.hlsl", encoding="utf-8").read())
custom.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
custom.set_editor_property("description", "TerraGround")
names = ["WP", "Ng", "Cam", "RootCol", "TipCol", "LushCol", "DryCol", "GrassFar", "Params"]
layers = [("Turf", "Moss002"), ("Dry", "Ground109"), ("Dirt", "Ground081"), ("Rock", "Rock062")]
for short, _ in layers:
    names += [short + "C", short + "N", short + "H"]
names.append("Mask")
inputs = []
for nm in names:
    ci = unreal.CustomInput()
    ci.set_editor_property("input_name", nm)
    inputs.append(ci)
custom.set_editor_property("inputs", inputs)
outs = []
for nm, t in [("NormalTS", unreal.CustomMaterialOutputType.CMOT_FLOAT3), ("Bare", unreal.CustomMaterialOutputType.CMOT_FLOAT1)]:
    co = unreal.CustomOutput()
    co.set_editor_property("output_name", nm)
    co.set_editor_property("output_type", t)
    outs.append(co)
custom.set_editor_property("additional_outputs", outs)

y = -900
wp = node(unreal.MaterialExpressionWorldPosition, X, y); y += 80
mel.connect_material_expressions(wp, "", custom, "WP")
ng = node(unreal.MaterialExpressionVertexNormalWS, X, y); y += 80
mel.connect_material_expressions(ng, "", custom, "Ng")
cam = node(unreal.MaterialExpressionCameraPositionWS, X, y); y += 80
mel.connect_material_expressions(cam, "", custom, "Cam")
for nm, pname in [("RootCol", "RootColor"), ("TipCol", "TipColor"), ("LushCol", "LushColor"), ("DryCol", "DryColor"), ("GrassFar", "GrassEndDistance")]:
    cp = node(unreal.MaterialExpressionCollectionParameter, X, y); y += 80
    cp.set_editor_property("collection", mpc)
    cp.set_editor_property("parameter_name", pname)
    mel.connect_material_expressions(cp, "", custom, nm)
params = node(unreal.MaterialExpressionVectorParameter, X, y); y += 120
params.set_editor_property("parameter_name", "BlendAntiTileNormalCarpet")
params.set_editor_property("default_value", unreal.LinearColor(0.2, 1.0, 0.8, 0.9))
mel.connect_material_expressions(params, "RGBA", custom, "Params")
for short, set_name in layers:
    for suffix, tex_suffix in [("C", "Color"), ("N", "NormalGL"), ("H", "Displacement")]:
        to = node(unreal.MaterialExpressionTextureObject, X, y); y += 80
        to.set_editor_property("texture", eal.load_asset(f"{TEX}/{set_name}/T_{set_name}_{tex_suffix}"))
        mel.connect_material_expressions(to, "", custom, short + suffix)
mask = node(unreal.MaterialExpressionTextureObject, X, y); y += 80
mask.set_editor_property("texture", eal.load_asset("/Game/Voyager/Textures/T_TerraGrassMask"))
mel.connect_material_expressions(mask, "", custom, "Mask")

mel.connect_material_property(custom, "", unreal.MaterialProperty.MP_BASE_COLOR)
mel.connect_material_property(custom, "NormalTS", unreal.MaterialProperty.MP_NORMAL)
rough = node(unreal.MaterialExpressionConstant, -200, 200)
rough.set_editor_property("r", 0.93)
mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
spec = node(unreal.MaterialExpressionConstant, -200, 280)
spec.set_editor_property("r", 0.25)   # matte: never glossy, even in rain
mel.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)

mel.recompile_material(m)
eal.save_loaded_asset(m)

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if isinstance(a, unreal.LandscapeProxy):
        a.set_editor_property("landscape_material", m)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
print("M_TerraGround built and assigned")
