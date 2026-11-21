"""Creates/updates MI_VoyagerClouds (child of the engine's simple volumetric cloud material),
tuned for Terra's thin 420-620 m deck, and assigns it to the level's VoyagerSky."""
import unreal

PATH = "/Game/Voyager/Materials/MI_VoyagerClouds"
PARENT = "/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary

if eal.does_asset_exist(PATH):
    mi = eal.load_asset(PATH)
else:
    f = unreal.MaterialInstanceConstantFactoryNew()
    mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset("MI_VoyagerClouds", "/Game/Voyager/Materials", unreal.MaterialInstanceConstant, f)
    pass
mel.set_material_instance_parent(mi, eal.load_asset(PARENT))

S = {"Cloud_GlobalCoverage": 0.15, "Cloud_GlobalDensity": 0.03, "Layout_CloudGlobalScale": 24.0}
for k, v in S.items():
    mel.set_material_instance_scalar_parameter_value(mi, k, v)
mel.set_material_instance_vector_parameter_value(mi, "Cloud_AlbedoColor", unreal.LinearColor(1.0, 0.98, 0.96, 0.5))
mel.update_material_instance(mi)
eal.save_loaded_asset(mi)

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
sky = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.VoyagerSky)][0]
sky.get_editor_property("clouds").set_material(mi)
print("clouds ->", mi.get_path_name())
