"""Creates the Terra level: planet data, placeholder ground material, sky actor and landscape.

Run inside the editor:  python Tools/ue_exec.py Tools/build_terra.py
Safe to re-run: existing assets are reused, and the landscape is only built if the level has none.
"""
import unreal

MAP = "/Game/Voyager/Maps/L_Terra"
DATA = "/Game/Voyager/Data/DA_Terra"
GROUND_MAT = "/Game/Voyager/Materials/M_TerraPlaceholder"

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary


def split(path):
    return path.rsplit("/", 1)[0], path.rsplit("/", 1)[1]


def planet_data():
    if eal.does_asset_exist(DATA):
        da = eal.load_asset(DATA)
    else:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property("data_asset_class", unreal.VoyagerPlanetData)
        folder, name = split(DATA)
        da = tools.create_asset(name, folder, unreal.VoyagerPlanetData, factory)
    values = {
        "display_name": unreal.Text("Terra"),
        "kind": unreal.VoyagerSurfaceKind.HOME,
        "landable": True,
        "description": unreal.Text("Home. A quiet valley with a river and an old house."),
        "gravity": 9.81, "time_rate": 1.0, "start_hour": 7.6,
        "ground_height": 22.0, "cloud_base": 420.0, "cloud_top": 620.0, "space_ceiling": 1500.0,
        "fog_density": 0.012, "morning_mist_density": 0.05,
        "fog_color": unreal.LinearColor(0.74, 0.81, 0.88, 1.0),
        "space_position": unreal.Vector(40000.0, 0.0, 0.0), "radius": 1500.0,
    }
    for k, v in values.items():
        da.set_editor_property(k, v)
    eal.save_loaded_asset(da)
    return da


def ground_material():
    """Temporary slope-based ground until the real scanned-material landscape material (step 3)."""
    if eal.does_asset_exist(GROUND_MAT):
        return eal.load_asset(GROUND_MAT)
    folder, name = split(GROUND_MAT)
    m = tools.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    E = unreal.MaterialExpressionConstant3Vector
    grass = mel.create_material_expression(m, E, -900, -200)
    grass.set_editor_property("constant", unreal.LinearColor(0.11, 0.17, 0.045, 1))
    dry = mel.create_material_expression(m, E, -900, -60)
    dry.set_editor_property("constant", unreal.LinearColor(0.2, 0.19, 0.08, 1))
    rock = mel.create_material_expression(m, E, -900, 80)
    rock.set_editor_property("constant", unreal.LinearColor(0.26, 0.24, 0.21, 1))

    # Large-scale dry/lush variation from world-space noise.
    noise = mel.create_material_expression(m, unreal.MaterialExpressionNoise, -1100, -140)
    noise.set_editor_property("scale", 0.0004)
    noise.set_editor_property("levels", 3)
    noise.set_editor_property("output_min", 0.0)
    noise.set_editor_property("output_max", 1.0)
    lush = mel.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -650, -150)
    mel.connect_material_expressions(grass, "", lush, "A")
    mel.connect_material_expressions(dry, "", lush, "B")
    mel.connect_material_expressions(noise, "", lush, "Alpha")

    # Rock on slopes: saturate((0.82 - normal.z) * 8)
    normal = mel.create_material_expression(m, unreal.MaterialExpressionVertexNormalWS, -1100, 160)
    mask = mel.create_material_expression(m, unreal.MaterialExpressionComponentMask, -950, 160)
    mask.set_editor_property("r", False)
    mask.set_editor_property("g", False)
    mask.set_editor_property("b", True)
    mel.connect_material_expressions(normal, "", mask, "")
    sub = mel.create_material_expression(m, unreal.MaterialExpressionSubtract, -800, 160)
    sub.set_editor_property("const_a", 0.82)
    mel.connect_material_expressions(mask, "", sub, "B")
    mul = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -680, 160)
    mul.set_editor_property("const_b", 8.0)
    mel.connect_material_expressions(sub, "", mul, "A")
    sat = mel.create_material_expression(m, unreal.MaterialExpressionSaturate, -560, 160)
    mel.connect_material_expressions(mul, "", sat, "")
    final = mel.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -400, 0)
    mel.connect_material_expressions(lush, "", final, "A")
    mel.connect_material_expressions(rock, "", final, "B")
    mel.connect_material_expressions(sat, "", final, "Alpha")
    mel.connect_material_property(final, "", unreal.MaterialProperty.MP_BASE_COLOR)

    rough = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -400, 200)
    rough.set_editor_property("r", 0.95)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    spec = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -400, 280)
    spec.set_editor_property("r", 0.2)
    mel.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    return m


les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

if eal.does_asset_exist(MAP):
    les.load_level(MAP)
else:
    les.new_level(MAP, True)

da = planet_data()
mat = ground_material()

sky = next((a for a in eas.get_all_level_actors() if isinstance(a, unreal.VoyagerSky)), None)
if sky is None:
    sky = eas.spawn_actor_from_class(unreal.VoyagerSky, unreal.Vector(0, 0, 0))
    sky.set_actor_label("VoyagerSky")
sky.set_editor_property("planet", da)
sky.apply_planet()
sky.apply_hour(sky.get_editor_property("editor_hour"))

if not any(isinstance(a, unreal.LandscapeProxy) for a in eas.get_all_level_actors()):
    ls = unreal.VoyagerTerraBuilder.build_terra_landscape(mat, 8)
    print("landscape", ls)

les.save_current_level()
print("Terra level ready:", ues.get_editor_world().get_path_name())

# Cloud deck material tuned for the thin 420-620 m layer.
exec(open(unreal.Paths.project_dir() + "Tools/terra_clouds.py").read())
les.save_current_level()
