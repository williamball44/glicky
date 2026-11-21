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
- **Resolution target vs hardware.** The owner's monitors are 1920×1080 and the GPU is an RTX 5060 (8 GB), with an i7-11700K. Measure "1440p" in a standalone or new-window PIE at 2560×1440. Expect to need TSR upscaling (around 67% screen percentage) for 60 fps with Lumen, VSM and volumetrics. Decide hardware vs software Lumen in step 2 using real numbers.
- Screenshots go to `Saved/Screenshots/Voyager/` (not committed). Step 1 shows the unchanged OpenWorld template map.

## Measuring (how to)
- `Tools/ue_exec.py` runs Python in the open editor through Python remote execution (on in `DefaultEngine.ini`; bound to 127.0.0.1 with TTL 0, so it's local only). Example: `python Tools/ue_exec.py -c "import unreal; ..."`. Console commands go through `unreal.SystemLibrary.execute_console_command(world, cmd)`.
- Each baseline is `startfpschart`, about 12 s, `stopfpschart`, then `ProfileGPU`, read from `Saved/Logs/glick.log` (the FPS chart is also saved under `Saved/Profiling/FPSChartStats/`).
- The MCP toolsets alone can't run console commands, hence the script.

## Performance log
| Step | Where | Res (render → output) | FPS | GPU | Render thread | Game thread | Notes |
|---|---|---|---|---|---|---|---|
| 1 | Editor viewport, OpenWorld template, aerial view | 1320×746 → 1526×862 (TSR) | 109.7 | 5.20 ms | 5.86 ms | 8.96 ms | Editor overhead dominates the game thread. 0 hitches. TSR 0.56–1.03 ms. |
- The old copy at `C:\Users\wball\OneDrive\Documents\Unreal Projects\glick` can be deleted once the new location is confirmed working.
