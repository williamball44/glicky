"""Imports the CC0 ambientCG ground sets from the Unity project into /Game/Voyager/Textures/Ground/<Set>.
Colour = sRGB; NormalGL -> normal map with green flipped (Unreal is DirectX-style); Displacement = linear mask
(used for height blending)."""
import os
import unreal

SRC = r"C:\Users\wball\fart\Assets\Voyager\Resources\Ground"
DST = "/Game/Voyager/Textures/Ground"
SETS = {"Turf": "Moss002", "DryTurf": "Ground109", "Dirt": "Ground081", "Rock": "Rock062"}

tasks = []
for layer, name in SETS.items():
    folder = os.path.join(SRC, layer)
    for f in sorted(os.listdir(folder)):
        if not f.lower().endswith(".jpg"):
            continue
        t = unreal.AssetImportTask()
        t.filename = os.path.join(folder, f)
        t.destination_path = f"{DST}/{name}"
        t.destination_name = "T_" + os.path.splitext(f)[0].replace("_2K-JPG", "")
        t.automated = True
        t.replace_existing = True
        t.save = False
        tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

for t in tasks:
    for path in t.imported_object_paths:
        tex = unreal.EditorAssetLibrary.load_asset(path)
        n = tex.get_name()
        if n.endswith("_NormalGL"):
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            tex.set_editor_property("flip_green_channel", True)
            tex.set_editor_property("srgb", False)
        elif n.endswith("_Displacement"):
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE)
            tex.set_editor_property("srgb", False)
        else:
            tex.set_editor_property("srgb", True)
        unreal.EditorAssetLibrary.save_loaded_asset(tex)
        print("imported", path)
