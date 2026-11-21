"""Loads every landscape streaming proxy of the current World Partition level in the editor
(World Partition leaves them unloaded until a region is loaded)."""
import unreal
wpl = unreal.WorldPartitionBlueprintLibrary
descs = wpl.get_actor_descs()
guids = [d.guid for d in descs if "LandscapeStreamingProxy" in str(d.native_class)]
wpl.load_actors(guids)
print("loaded landscape proxies:", len(guids))
