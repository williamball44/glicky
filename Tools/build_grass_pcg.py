"""Builds PCG_TerraGrass and a runtime-generated PCG volume over the Terra valley.

Ghost of Tsushima style carpet: one 1 m grass patch (Tools/build_grass.py) per square metre on an exact grid, so
patches tile into a continuous field. Everything per blade (clumps, density, bare dirt, tall patches, gradient
culling, wind) happens in M_GrassPatch, so the graph only lays the carpet:
    Landscape -> Surface Sampler (1/m^2, exact grid) -> Sample mask R -> keep R >= 0.05 -> Static Mesh Spawner
Patches are not rotated: clumping is computed in world space in the shader, so it runs seamlessly across patches.
Grass casts no shadow-map shadows (contact shadows on the sun instead).
Runtime generation: 64 m cells within 95 m of the camera; every blade has shrunk away by GrassEndDistance (80 m).

Set GRASS_NANITE = True before exec'ing this file to use the Nanite patch set (A/B):
    python Tools/ue_exec.py -c "GRASS_NANITE = True; exec(open(unreal.Paths.project_dir() + 'Tools/build_grass_pcg.py').read())"
Re-run to rebuild: the graph is recreated and the volume regenerated."""
import unreal

NANITE = globals().get("GRASS_NANITE", False)
GRAPH = "/Game/Voyager/Grass/PCG_TerraGrass"
MASK = "/Game/Voyager/Textures/T_TerraGrassMask"
PATCHES = [f"SM_GrassPatch{'N' if NANITE else ''}_{i}" for i in range(6)]
END_CULL = 8500.0     # cm: just past GrassEndDistance, by which every blade has shrunk to nothing
START_CULL = 8000.0
eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

if eal.does_asset_exist(GRAPH):
    graph = eal.load_asset(GRAPH)
    io = (graph.get_input_node(), graph.get_output_node())
    for n in [n for n in graph.get_editor_property("nodes") if n not in io]:
        graph.remove_node(n)
else:
    graph = unreal.AssetToolsHelpers.get_asset_tools().create_asset("PCG_TerraGrass", "/Game/Voyager/Grass", unreal.PCGGraph, unreal.PCGGraphFactory())

pos = [0]
def add(cls, **props):
    node, settings = graph.add_node_of_type(cls)
    for k, v in props.items():
        settings.set_editor_property(k, v)
    node.set_node_position(pos[0], 0)
    pos[0] += 260
    return node, settings

def edge(a, b, a_pin="Out", b_pin="In"):
    before = len(graph.get_all_edges())
    graph.add_edge(a, a_pin, b, b_pin)
    if len(graph.get_all_edges()) <= before:
        raise RuntimeError(f"PCG edge failed: {a.get_name()}.{a_pin} -> {b.get_name()}.{b_pin}")

def set_range(settings, lo, hi):
    """Keep points whose $Density (the default target) is in [lo, hi], using constant thresholds."""
    for prop, value in (("min_threshold", lo), ("max_threshold", hi)):
        t = settings.get_editor_property(prop)
        t.import_text(f"(bInclusive=True,bUseConstantThreshold=True,AttributeTypes=(Type=Double,DoubleValue={value}))")
        settings.set_editor_property(prop, t)

land, _ = add(unreal.PCGGetLandscapeSettings)
sampler, ss = add(unreal.PCGSurfaceSamplerSettings, points_per_squared_meter=1.0, looseness=0.0)
ss.set_editor_property("point_extents", unreal.Vector(50.0, 50.0, 30.0))
edge(land, sampler, "Out", "Surface")

tex, ts = add(unreal.PCGTextureSamplerSettings)
ts.set_editor_property("texture", eal.load_asset(MASK))
ts.set_editor_property("color_channel", unreal.PCGTextureColorChannel.RED)
ts.set_editor_property("transform", unreal.Transform(location=[0, 0, 0], rotation=[0, 0, 0], scale=[102400.0, 102400.0, 1.0]))
ts.set_editor_property("use_absolute_transform", True)
ts.set_editor_property("filter", unreal.PCGTextureFilter.BILINEAR)
sample, _ = add(unreal.PCGSampleTextureSettings)
edge(sampler, sample, "Out", "Point")
edge(tex, sample, "Out", "BaseTexture")
keep, ks = add(unreal.PCGAttributeFilteringRangeSettings)
edge(sample, keep)
set_range(ks, 0.05, 1.01)   # the shader thins blades by density; only drop patches with no grass at all

spawn, sp = add(unreal.PCGStaticMeshSpawnerSettings)
sel = sp.get_editor_property("mesh_selector_parameters")
entries = []
for name in PATCHES:
    d = unreal.PCGSoftISMComponentDescriptor()
    d.set_editor_property("static_mesh", eal.load_asset(f"/Game/Voyager/Grass/{name}"))
    d.set_editor_property("instance_start_cull_distance", int(START_CULL))
    d.set_editor_property("instance_end_cull_distance", int(END_CULL))
    d.set_editor_property("cast_shadow", False)            # contact shadows + root AO instead (Ghost of Tsushima)
    d.set_editor_property("cast_contact_shadow", True)
    d.set_editor_property("world_position_offset_disable_distance", 0)   # the shader shapes every blade: keep WPO on
    d.set_editor_property("visible_in_ray_tracing", False)
    d.set_editor_property("affect_distance_field_lighting", False)
    e = unreal.PCGMeshSelectorWeightedEntry()
    e.set_editor_property("descriptor", d)
    e.set_editor_property("weight", 1)
    entries.append(e)
sel.set_editor_property("mesh_entries", entries)
edge(keep, spawn, "InsideFilter", "In")
eal.save_loaded_asset(graph)
print("graph:", len(entries), "patch meshes, Nanite" if NANITE else "patch meshes, classic LODs")

# Volume over the valley, generated at runtime around the camera.
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "PCG_TerraGrass":
        eas.destroy_actor(a)
vol = eas.spawn_actor_from_class(unreal.PCGVolume, unreal.Vector(0, 0, 5000))
vol.set_actor_label("PCG_TerraGrass")
vol.set_actor_scale3d(unreal.Vector(2048.0, 2048.0, 400.0))   # 2048 m square (brush is 200 units), matching the mask
pcg = vol.get_component_by_class(unreal.PCGComponent)
# Order matters: switch to runtime generation BEFORE assigning the graph. SetGraph() queues an editor refresh,
# and if the component becomes runtime-managed while that refresh is pending, PCG asserts
# (UPCGComponent::OnRefresh: !IsManagedByRuntimeGenSystem) the moment PIE starts.
pcg.set_editor_property("generation_trigger", unreal.PCGComponentGenerationTrigger.GENERATE_AT_RUNTIME)
pcg.set_editor_property("is_component_partitioned", True)
pcg.set_editor_property("override_generation_radii", True)
radii = pcg.get_editor_property("generation_radii")
r = radii.get_editor_property("radius6400"); r.set_editor_property("default", 9500.0); radii.set_editor_property("radius6400", r)
pcg.set_editor_property("generation_radii", radii)
gi = pcg.get_editor_property("graph_instance")
gi.set_editor_property("graph", graph)   # property path (PostEditChange), not SetGraph()
# 64 m partition cells (the PCG world actor owns the grid size).
for a in eas.get_all_level_actors():
    if isinstance(a, unreal.PCGWorldActor):
        a.set_editor_property("partition_grid_size", 6400)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
print("PCG_TerraGrass volume:", vol.get_path_name())
