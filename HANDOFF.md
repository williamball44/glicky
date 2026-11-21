# Voyager (Unreal) – handoff

Read this first. It covers what exists, how it fits together, the owner's working rules and what's open.

## Project
| | |
|---|---|
| Engine | Unreal Engine 5.8 (launcher build, `C:\Program Files\Epic Games\UE_5.8`) |
| Location | `C:\Dev\Voyager` (moved out of OneDrive; the old OneDrive copy is obsolete) |
| Project file | `glick.uproject` (the file name is legacy; the game and C++ module are **Voyager**) |
| Remote | `https://github.com/williamball44/glicky.git`, branch `main` |
| Reference | Unity version at `C:\Users\wball\fart` (`HANDOFF.md`, `Assets/Voyager/`). Use it for behaviour and maths only; rebuild each system the Unreal way. |
| Editor link | Unreal MCP over HTTP (`.mcp.json` → `http://127.0.0.1:8000/mcp`, plugins `ModelContextProtocol` + `AllToolsets`) |
| Git | `main` branch, Git LFS for `.uasset`, `.umap`, textures, meshes and audio (`.gitattributes`). Binaries, Intermediate, Saved and DerivedDataCache are ignored. |

## Owner's working rules
- Start every reply with `+`. Direct and concise, no filler praise.
- Stress-test ideas before building. Give the most efficient path, not open questions.
- Don't write or modify code in files you haven't read word for word.
- After every change, commit and push to `main`.
- Keep this file current.
- After each build-order step: a screenshot plus `stat unit` / `stat gpu` / Insights numbers.

## What exists
- **C++ module `Voyager`** (`Source/Voyager/`): primary game module, `LogVoyager` log category. Depends on Core, CoreUObject, Engine, InputCore, EnhancedInput. Targets `glick` / `glickEditor` (`Source/*.Target.cs`).
- **Plugins** (`glick.uproject`): EnhancedInput, Water (pulls in Landmass), PCG, PythonScriptPlugin, EditorScriptingUtilities, ModelingToolsEditorMode, ModelContextProtocol, AllToolsets.
- **Renderer** (`Config/DefaultEngine.ini`, from the template): Lumen GI and reflections, Virtual Shadow Maps, mesh distance fields, hardware ray tracing, Substrate, DX12 SM6. Default map is the engine's OpenWorld template (World Partition).
- **Content:** nothing yet.

## Build order (from the owner's brief)
1. ✅ Project setup: module, plugins, git/LFS. Builds clean. *(The first screenshot/perf baseline is still pending, see Open.)*
2. Terra terrain, sky, sun, day/night, fog, clouds.
3. Ground materials and the procedural grass plugin (RDG compute + indirect draw).
4. Trees, rocks, flowers, pebbles, house, river.
5. First-person player, ship flight, enter/exit, HUD.
6. Space: stars, nebulas, sun, planets, atmosphere transition, turbo, fuel, embryos, asteroids.
7. Thalassa: ocean, landing on water, boat, fishing, weather.
8. Placeholder planets, gravity and time systems.

## Open
- **Command-line build** (only with the editor closed, since Live Coding blocks it):
  `"C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" glickEditor Win64 Development -Project="C:\Dev\Voyager\glick.uproject" -WaitMutex`
  With the editor open, use Live Coding (Ctrl+Alt+F11) for .cpp-only changes.
- No performance baseline yet: it needs the editor reopened with the Python plugin loaded.
- The old copy at `C:\Users\wball\OneDrive\Documents\Unreal Projects\glick` can be deleted once the new location is confirmed working.
