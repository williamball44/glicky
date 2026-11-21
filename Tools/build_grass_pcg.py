"""Builds PCG_TerraGrass and a runtime-generated PCG volume over the Terra valley.

Graph:  Landscape -> Surface Sampler (2.5 clumps/m^2, 0.9 m clumps)
          -> Sample mask G (tall patches) -> split by density: tall | short
          -> each: Sample mask R (grass density) -> keep R >= 0.3 -> random yaw/scale -> Static Mesh Spawner
The mask (T_TerraGrassMask) is the same texture the ground material reads for bare patches.
Runtime generation: the world is cut into 64 m cells, generated within 160 m of the camera, so only
about 100-150k clumps exist at once. Instances end at MPC GrassEndDistance (120 m), where the ground's
grass-coloured carpet takes over.
Re-run to rebuild: the graph is recreated and the volume regenerated."""
import unreal

GRAPH = "/Game/Voyager/Grass/PCG_TerraGrass"
MASK = "/Game/Voyager/Textures/T_TerraGrassMask"
eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

TALL = [("SM_GrassClump_M0", 3), ("SM_GrassClump_M1", 3), ("SM_GrassClump_T0", 2), ("SM_GrassClump_T1", 1)]
SHORT = [("SM_GrassClump_S0", 3), ("SM_GrassClump_S1", 3), ("SM_GrassClump_S2", 3), ("SM_GrassClump_S3", 2), ("SM_GrassClump_M0", 1)]
END_CULL = 12000.0   # cm, matches MPC GrassEndDistance
START_CULL = 9000.0

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
    before = len(graph.get_all_edges()) if hasattr(graph, "get_all_edges") else None
    graph.add_edge(a, a_pin, b, b_pin)
    if before is not None and len(graph.get_all_edges()) <= before:
        raise RuntimeError(f"PCG edge failed: {a.get_name()}.{a_pin} -> {b.get_name()}.{b_pin}")

mask_tex = eal.load_asset(MASK)
mask_xform = unreal.Transform(location=[0, 0, 0], rotation=[0, 0, 0], scale=[102400.0, 102400.0, 1.0])

def texture_node(channel):
    n, s = add(unreal.PCGTextureSamplerSettings)
    s.set_editor_property("texture", mask_tex)
    s.set_editor_property("color_channel", channel)
    s.set_editor_property("transform", mask_xform)
    s.set_editor_property("use_absolute_transform", True)
    s.set_editor_property("filter", unreal.PCGTextureFilter.BILINEAR)
    return n

land, _ = add(unreal.PCGGetLandscapeSettings)
sampler, ss = add(unreal.PCGSurfaceSamplerSettings, points_per_squared_meter=2.5, looseness=1.0)
ss.set_editor_property("point_extents", unreal.Vector(45.0, 45.0, 30.0))
edge(land, sampler, "Out", "Surface")

tall_tex = texture_node(unreal.PCGTextureColorChannel.GREEN)
sample_tall, st = add(unreal.PCGSampleTextureSettings)
edge(sampler, sample_tall, "Out", "Point")
edge(tall_tex, sample_tall, "Out", "BaseTexture")

def branch(lo, hi, meshes, label):
    split, fs = add(unreal.PCGAttributeFilteringRangeSettings)
    edge(sample_tall, split)
    _set_range(fs, lo, hi)
    dens_tex = texture_node(unreal.PCGTextureColorChannel.RED)
    sample_d, _ = add(unreal.PCGSampleTextureSettings)
    edge(split, sample_d, "InsideFilter", "Point")
    edge(dens_tex, sample_d, "Out", "BaseTexture")
    keep, ks = add(unreal.PCGAttributeFilteringRangeSettings)
    edge(sample_d, keep)
    _set_range(ks, 0.3, 1.01)
    xf, xs = add(unreal.PCGTransformPointsSettings)
    xs.set_editor_property("rotation_min", unreal.Rotator(0, 0, 0))
    xs.set_editor_property("rotation_max", unreal.Rotator(0, 0, 360))
    xs.set_editor_property("scale_min", unreal.Vector(0.85, 0.85, 0.8))
    xs.set_editor_property("scale_max", unreal.Vector(1.2, 1.2, 1.25))
    xs.set_editor_property("uniform_scale", False)
    xs.set_editor_property("offset_min", unreal.Vector(-35.0, -35.0, -3.0))   # break up the sampler grid
    xs.set_editor_property("offset_max", unreal.Vector(35.0, 35.0, 0.0))
    edge(keep, xf, "InsideFilter", "In")
    spawn, sp = add(unreal.PCGStaticMeshSpawnerSettings)
    sel = sp.get_editor_property("mesh_selector_parameters")
    entries = []
    for name, w in meshes:
        d = unreal.PCGSoftISMComponentDescriptor()
        d.set_editor_property("static_mesh", eal.load_asset(f"/Game/Voyager/Grass/{name}"))
        d.set_editor_property("instance_start_cull_distance", int(START_CULL))
        d.set_editor_property("instance_end_cull_distance", int(END_CULL))
        d.set_editor_property("cast_shadow", True)
        d.set_editor_property("cast_contact_shadow", True)
        d.set_editor_property("world_position_offset_disable_distance", 3000)  # static beyond 30 m: VSM can cache it
        d.set_editor_property("visible_in_ray_tracing", False)
        d.set_editor_property("affect_distance_field_lighting", False)
        e = unreal.PCGMeshSelectorWeightedEntry()
        e.set_editor_property("descriptor", d)
        e.set_editor_property("weight", w)
        entries.append(e)
    sel.set_editor_property("mesh_entries", entries)
    edge(xf, spawn)
    print(label, "branch:", len(entries), "meshes")

def _set_range(settings, lo, hi):
    """Keep points whose $Density (the default target) is in [lo, hi], using constant thresholds."""
    for prop, value in (("min_threshold", lo), ("max_threshold", hi)):
        t = settings.get_editor_property(prop)
        t.import_text(f"(bInclusive=True,bUseConstantThreshold=True,AttributeTypes=(Type=Double,DoubleValue={value}))")
        settings.set_editor_property(prop, t)

branch(0.5, 1.01, TALL, "tall")
branch(-0.01, 0.5, SHORT, "short")
eal.save_loaded_asset(graph)

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
r = radii.get_editor_property("radius6400"); r.set_editor_property("default", 16000.0); radii.set_editor_property("radius6400", r)
pcg.set_editor_property("generation_radii", radii)
gi = pcg.get_editor_property("graph_instance")
gi.set_editor_property("graph", graph)   # property path (PostEditChange), not SetGraph()
# 64 m partition cells (the PCG world actor owns the grid size).
for a in eas.get_all_level_actors():
    if isinstance(a, unreal.PCGWorldActor):
        a.set_editor_property("partition_grid_size", 6400)
        print("PCG partition grid:", a.get_editor_property("partition_grid_size"))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
print("PCG_TerraGrass volume:", vol.get_path_name())
