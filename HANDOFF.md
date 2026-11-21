# Voyager (Unreal) – handoff

Read this first. It covers what exists, how it fits together, the owner's working rules and what's open.

## Project
| | |
|---|---|
| Engine | Unreal Engine 5.8 (launcher build, `C:\Program Files\Epic Games\UE_5.8`) |
| Location | `C:\Dev\Voyager` (moved out of OneDrive; the old OneDrive copy is obsolete) |
| Project file | `glick.uproject` (the file name is legacy; the game and C++ modules are **Voyager**) |
| Remote | `https://github.com/williamball44/glicky.git`, branch `main` |
| Reference | Unity version at `C:\Users\wball\fart` (`HANDOFF.md`, `Assets/Voyager/`). Use it for behaviour and maths only; rebuild each system the Unreal way. |
| Editor link | Unreal MCP over HTTP (`.mcp.json` → `http://127.0.0.1:8000/mcp`, plugins `ModelContextProtocol` + `AllToolsets`), plus Python remote execution (`Tools/ue_exec.py`) |
| Git | `main` branch, Git LFS for `.uasset`, `.umap`, textures, meshes and audio (`.gitattributes`). Binaries, Intermediate, Saved and DerivedDataCache are ignored. |
| Hardware | RTX 5060 (8 GB), i7-11700K, 48 GB RAM, two 1920×1080 monitors |

## Owner's working rules
- Start every reply with `+`. Direct and concise, no filler praise.
- Stress-test ideas before building. Give the most efficient path, not open questions.
- Don't write or modify code in files you haven't read word for word.
- After every change, commit and push to `main`.
- Keep this file current.
- After each build-order step: a screenshot plus `stat unit` / `stat gpu` / Insights numbers.

## Coordinates
Unreal: X north, Y east, Z up, centimetres. Unity reference: x east, y up, z north, metres. Mapping: UE (X, Y, Z) = 100 × Unity (z, x, y). Yaw has the same sense in both (north toward east), so the house yaw stays 120°.

## What exists
### C++ (`Source/`)
- **`Voyager`** (runtime, primary game module; `LogVoyager`)
  - `UVoyagerPlanetData` (`VoyagerPlanetData.h`): primary data asset per planet. Holds gravity, time rate, start hour, ground height, cloud base/top, space ceiling, fog density, morning mist, fog colour, sun tint, and space position/radius (used from step 6).
  - `UVoyagerClockSubsystem` (`VoyagerClockSubsystem.h/.cpp`): game-instance subsystem, ticks home time. The home day is 24 real minutes; `LocalHour(planet)` = start hour + home hours × time rate. Also `FormatHour` and `SurfaceSunDirection(hour)`, a port of Unity's `GameClock.SurfaceSunDirection`: rises in the east, 62° peak toward the south at noon.
  - `AVoyagerSky` (`VoyagerSky.h/.cpp`): one always-loaded actor per surface level that owns sun, moon (atmosphere light 1), Sky Atmosphere, real-time Sky Light, height fog with volumetric fog plus a second low "morning mist" layer peaking at 06:48, a Volumetric Cloud deck (altitudes from planet data), and an unbound post-process (bloom 0.6, vignette 0.3, slight saturation). Ticks in the editor as well. `EditorHour` previews the time of day and `bAnimateInEditor` runs the cycle; in game the hour comes from the clock subsystem. Sky colours come from the atmosphere simulation, not hand-painted gradients.
  - `UVoyagerTerra` (`VoyagerTerra.h/.cpp`): Terra's height function, river curve, house and ship pads, ported one for one from Unity `HomeSurface.Height` / `RiverX` (Unity Perlin [0,1] mapped from `FMath::PerlinNoise2D`). Blueprint/Python: `TerrainHeight(XY)` and `RiverY(X)`.
- **`VoyagerEditor`** (editor-only)
  - `UVoyagerTerraBuilder::BuildTerraLandscape(material, grid)`: samples `TerrainHeight` (ParallelFor) into a 4033² landscape: 32×32 components, 2×2 sections of 63 quads, 2 m spacing, 8.06 km square, centred on the origin. Z scale is chosen automatically (±585 m range → ScaleZ 240). Splits into World Partition streaming proxies (8×8 components each). Takes about 2 minutes including the save.

### Content (`Content/Voyager/`)
- `Maps/L_Terra`: World Partition level containing the VoyagerSky, Terra landscape and `PlayerStart_Meadow` (-25 m, 15 m, 23 m, yaw 70).
- `Data/DA_Terra`: Terra planet data (start 07:36, fog 0.012, mist 0.05, ground 22 m, clouds 420–620 m).
- `Materials/M_TerraPlaceholder`: temporary slope/noise ground material (replaced in step 3).
- `Materials/MI_VoyagerClouds`: child of the engine's `m_SimpleVolumetricCloud_Inst`, tuned for the thin deck (coverage 0.15, density 0.03, layout scale 24 km). **It must be parented to the `_Inst`, not the base material**: the instance supplies the texture parameters, and without them no clouds render.

### Tools (`Tools/`)
- `ue_exec.py`: run Python in the open editor (`python Tools/ue_exec.py file.py` or `-c "code"`).
- `build_terra.py`: (re)creates L_Terra, DA_Terra, the placeholder material, sky, landscape and clouds. Idempotent.
- `terra_clouds.py`: creates/updates MI_VoyagerClouds and assigns it.
- `capture.py`: decodes an MCP `CaptureViewport` result file into a PNG.

### Config
- Plugins: EnhancedInput, Water (+Landmass), PCG, PythonScriptPlugin, EditorScriptingUtilities, ModelingToolsEditorMode, ModelContextProtocol, AllToolsets.
- Renderer (template): Lumen GI and reflections, Virtual Shadow Maps, mesh distance fields, hardware ray tracing, Substrate, DX12 SM6.
- Python remote execution is on (127.0.0.1, TTL 0).

## Build order (from the owner's brief)
1. ✅ Project setup.
2. 🟡 Terra terrain, sky, sun, day/night, fog, clouds. Built and tuned; open items below.
3. Ground materials and the procedural grass plugin (RDG compute + indirect draw).
4. Trees, rocks, flowers, pebbles, house, river.
5. First-person player, ship flight, enter/exit, HUD.
6. Space: stars, nebulas, sun, planets, atmosphere transition, turbo, fuel, embryos, asteroids.
7. Thalassa: ocean, landing on water, boat, fishing, weather.
8. Placeholder planets, gravity and time systems.

## Open
- **True 1440p measurement isn't possible on this display.** A PIE "new window" at 2560×1440 is clamped to 1914×994. A standalone `-game -ResX=2560 -ResY=1440` launch hung before writing a log (probably a dialog from a second instance of the project). Options: run the standalone with the editor closed, or use `r.ScreenPercentage` emulation. Don't launch with Git Bash: it rewrites `/Game/...` arguments into Windows paths. Use PowerShell.
- **Clouds are the biggest GPU cost** (3.7 ms of 8.8 ms scene). Try lower `ViewSampleCountScale`, a shorter `TracingMaxDistance` (50 km now; the landscape is only 8 km), and fewer cloud-shadow samples.
- **The cloud material should move onto `UVoyagerPlanetData`** (a `CloudMaterial` field) so the C++ default isn't the engine instance, which shows nothing on a thin deck. Today it's set on the level's actor by `terra_clouds.py`.
- **No night sky.** Stars, the moon disk and nebulae come in step 6 (shared with space).
- The space transition (atmosphere thinning above 620 m to 1500 m) is step 6.
- The landscape edge at ±4 km is hidden by haze and hills from the ground, but visible from high altitude.
- The C++ fog defaults changed to 0.012/0.05 and aren't compiled yet (they'll compile on the next restart). The level's data asset already holds these values.
- **Command-line build** (only with the editor closed, since Live Coding blocks it):
  `"C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" glickEditor Win64 Development -Project="C:\Dev\Voyager\glick.uproject" -WaitMutex`
  Live Coding can't add modules or new UCLASSes. To restart the editor for a build: `unreal.SystemLibrary.quit_editor()` over `ue_exec.py`, build, then start `UnrealEditor.exe "C:\Dev\Voyager\glick.uproject"`.
- The old copy at `C:\Users\wball\OneDrive\Documents\Unreal Projects\glick` can be deleted.

## Measuring (how to)
- Console commands go through `ue_exec.py` → `unreal.SystemLibrary.execute_console_command(world, cmd)`. The PIE world is `UnrealEditorSubsystem.get_game_world()`.
- Each baseline is `startfpschart`, about 15 s, `stopfpschart`, then `ProfileGPU`, read from `Saved/Logs/glick.log`.
- Screenshots go to `Saved/Screenshots/Voyager/` (not committed), via MCP `CaptureViewport` plus `Tools/capture.py`.

## Performance log
| Step | Where | Res (render → output) | FPS | GPU | Game thread | Notes |
|---|---|---|---|---|---|---|
| 1 | Editor viewport, OpenWorld template, aerial | 1320×746 → 1526×862 (TSR) | 109.7 | 5.20 ms | 8.96 ms | Editor overhead dominates the game thread. 0 hitches. |
| 2 | PIE window, Terra meadow 07:36, looking east toward the sun | 1439×748 → 1914×994 (TSR) | 72.9 | 11.5 ms (scene 8.8, editor Slate 1.0) | 13.2 ms | Clouds 3.7, post 1.5, lighting 0.7, shadow depths 0.65, volumetric fog 0.5, VSM page marking 0.3 ms. 0 hitches. No grass or props yet. |
