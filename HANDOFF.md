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
  - `UVoyagerPlanetData` (`VoyagerPlanetData.h`): primary data asset per planet. Holds gravity, time rate, start hour, ground height, cloud base/top, space ceiling, fog density, morning mist, fog colour, sun tint, cloud material, and space position/radius (used from step 6).
  - `UVoyagerClockSubsystem` (`VoyagerClockSubsystem.h/.cpp`): game-instance subsystem, ticks home time. The home day is 24 real minutes; `LocalHour(planet)` = start hour + home hours × time rate. Also `FormatHour` and `SurfaceSunDirection(hour)`, a port of Unity's `GameClock.SurfaceSunDirection`: rises in the east, 62° peak toward the south at noon.
  - `AVoyagerSky` (`VoyagerSky.h/.cpp`): the sun and moon turn in `LightStepMinutes` steps (default 1 local minute, 0.25°) instead of every frame. Any directional-light rotation invalidates the whole VSM cache; per-frame turning cost 1.7 ms. One always-loaded actor per surface level that owns sun, moon (atmosphere light 1), Sky Atmosphere, real-time Sky Light, height fog with volumetric fog plus a second low "morning mist" layer peaking at 06:48, a Volumetric Cloud deck (altitudes and material from planet data; cloud shadow and sky AO limited to a 12 km extent at half resolution and samples, the measured 3.6 → 0.7 ms win; the moon casts no cloud shadow), and an unbound post-process (bloom 0.6, vignette 0.3, slight saturation). Ticks in the editor as well. `EditorHour` previews the time of day and `bAnimateInEditor` runs the cycle; in game the hour comes from the clock subsystem. Sky colours come from the atmosphere simulation, not hand-painted gradients.
  - `UVoyagerTerra` (`VoyagerTerra.h/.cpp`): Terra's height function, river curve, house and ship pads, ported one for one from Unity `HomeSurface.Height` / `RiverX` (Unity Perlin [0,1] mapped from `FMath::PerlinNoise2D`). Blueprint/Python: `TerrainHeight(XY)` and `RiverY(X)`.
- **`VoyagerEditor`** (editor-only)
  - `UVoyagerTerraBuilder::BuildTerraLandscape(material, grid)`: samples `TerrainHeight` (ParallelFor) into a 4033² landscape: 32×32 components, 2×2 sections of 63 quads, 2 m spacing, 8.06 km square, centred on the origin. Z scale is chosen automatically (±585 m range → ScaleZ 240). Splits into World Partition streaming proxies (8×8 components each). Takes about 2 minutes including the save.
  - `UVoyagerGrassBuilder::BuildGrassPatch(path, material, seed, blades=120, size=100, baseHeight=38, halfWidth=0.9, bNanite)`: **the current grass.** A 1 m tile of straight blade strips, roots on a jittered grid (shuffled, so coarser LODs stay even). Per-blade data lives in UVs (exact floats): UV0 = (across 0..1, t), UV1 = root (local cm), UV2 = (unit height cm, random), UV3 = facing. The material rebuilds every blade's shape. bNanite gives one Nanite LOD (Voxelize); otherwise 3 classic LODs (all blades × 6 segments; 1/3 × 3 segments × 1.8 width; 1/8 × 1 segment × 3 width).
  - `UVoyagerGrassBuilder::BuildGrassClump(...)`: the superseded clump builder (no assets use it now). Note for any mesh build: **vertex colours are stored sRGB-encoded**; the patches avoid that by using UVs.
  - `UVoyagerGrassBuilder::BuildLandscapeNanite()`: builds Nanite for all *loaded* landscape proxies (run `Tools/load_terrain.py` first).

### Content (`Content/Voyager/`)
- `Maps/L_Terra`: World Partition level containing the VoyagerSky, Terra landscape and `PlayerStart_Meadow` (-25 m, 15 m, 23 m, yaw 70).
- `Data/DA_Terra`: Terra planet data (start 07:36, fog 0.012, mist 0.05, ground 22 m, clouds 420–620 m).
- `Materials/M_TerraGround`: the landscape material. A single Custom node runs `Tools/shaders/TerraGround.hlsl`, a port of Unity StylizedTerrain:
  - layers: turf (Moss002), dry turf (Ground109), dirt (Ground081), rock (Rock062) and riverbed (dirt, darker)
  - procedural weights: rock on 27–38° slopes, riverbed below 19.8 m, dry turf from noise
  - bare patches from the grass mask
  - 2-sample anti-tiling with the seam biased by height, height blending, triplanar rock, macro colour variation
  - a short-grass "carpet" colour that ramps in over the last half of `GrassEndDistance`
  - roughness 0.93 and specular 0.25, so it is never glossy
- `Materials/M_TerraPlaceholder`: the old slope/noise placeholder (unused).
- `Materials/MPC_VoyagerGrass`: shared grass colours (root, tip, lush, dry, gust); wind (direction, strength, speed, weather multiplier `Wind`); `GustScale`/`GustScroll`; `ClumpSize` (0.9 m); `GrassEndDistance` (80 m); and `PlayerPos` (world cm)/`PlayerRadius` (1.5 m) for the player push. **The player must write `PlayerPos` each frame (step 5).** Used by both the ground and the grass. **`build_ground_material.py` updates parameters in place**: replacing the list mints new GUIDs, and every material referencing the collection then loads its nodes as "None" and falls back to the default material.
- `Textures/Ground/<Set>/`: the CC0 ambientCG 2K sets (colour sRGB; NormalGL imported with green flipped; displacement linear, used for height blending).
- `Textures/T_TerraGrassMask`: 2048² at 1 m/texel over 2048 m centred on the origin (R = grass density, G = tall patches, B = bare dirt), baked by `Tools/bake_grass_mask.py` (column = world X, row = world Y). Read by both the ground material (B) and PCG (R, G), so grass never grows on bare dirt. Stored as uncompressed RGBA8 with no mips.
- **Grass (Ghost of Tsushima style, owner's request 2026-11-21).** Unreal-native (PCG + Nanite), but each blade is shaped in the vertex shader with the Unity grass maths:
  - `Grass/M_GrassPatch`: two-sided foliage, world-space normal (tangent-space normal off), max WPO 110 cm.
    - Vertex: `Tools/shaders/GrassBladeWPO.hlsl`
      - world-space Voronoi clumps (`ClumpSize`): shared height, tallest in the middle, lean outward, 5% long floppy blades
      - the grass mask: R thins blades, G gives tall patches, B shortens blades and hides them on bare dirt
      - **gradient culling**: each blade shrinks away at its own fraction (50–100%) of `GrassEndDistance`, so there's no ring
      - quadratic Bézier spine (length-preserving) bent by lean, wind (`T_GustNoise` scrolling along `WindDir` plus sway and flutter) and the player push
      - edge-on thickening, and blades widen with distance
      - bent and rounded normals, transformed to world and passed through a vertex interpolator
    - Pixel: `GrassPatchColor.hlsl`: `pow(t, 1.5)` root-to-tip ramp, dry/lush/tuft/patch tones (shared with the ground carpet), clump tone, gust highlight, backlit subsurface colour, root AO.
    - Graph helpers: `RootWS` = WorldPosition − LocalToWorld(LP − root); `CamL`, `AxL` and `AyL` convert world directions to local space.
  - `Grass/SM_GrassPatchN_0..5`: Nanite patches, 120 blades each.
  - `Textures/T_GustNoise`: 256² tileable fbm (`Tools/bake_gust_noise.py`).
  - **Why Nanite:** A/B in PIE with 157k patches: Nanite grass about 3.6 ms GPU against about 6 ms for classic LODs, whose WPO forces a separate velocity pass (2.5 ms). Rebuild the classic set with `GRASS_CLASSIC = True`.
- `Grass/PCG_TerraGrass` and the `PCG_TerraGrass` volume (2048 m square):
  - graph: landscape → surface sampler (1 point/m², exact grid, no jitter) → sample mask R → keep R ≥ 0.05 → Static Mesh Spawner (6 patches, equal weights). No rotation: clumping is computed in world space, so it runs seamlessly across patches.
  - ISMs: cull from 80 to 85 m (all blades have shrunk away by then), WPO always on, **no shadow casting** (the sun has contact shadows, length 0.06), not in ray tracing or distance fields.
  - **generated at runtime**: 64 m partition cells (PCG world actor grid size 6400), generation radius 95 m, about 157k patches alive
  - the PCG landscape cache is set to *Always Serialize* and built with `pcg.BuildLandscapeCache`, which runtime generation needs
  - The editor viewport doesn't show runtime grass. Use PIE, or a temporary volume set to *Generate On Demand*.
- `Materials/MI_VoyagerClouds` (assigned through `DA_Terra.CloudMaterial`): child of the engine's `m_SimpleVolumetricCloud_Inst`, tuned for the thin deck (coverage 0.15, density 0.03, layout scale 24 km). **It must be parented to the `_Inst`, not the base material**: the instance supplies the texture parameters, and without them no clouds render.

### Tools (`Tools/`)
- `ue_exec.py`: run Python in the open editor (`python Tools/ue_exec.py file.py` or `-c "code"`).
- `build_terra.py`: (re)creates L_Terra, DA_Terra, the placeholder material, sky, landscape and clouds. Idempotent.
- `terra_clouds.py`: creates/updates MI_VoyagerClouds and assigns it.
- `capture.py`: decodes an MCP `CaptureViewport` result file into a PNG.
- `gpu_passes.py`: prints the last `ProfileGPU` pass tree from the editor log.
- `csv_summary.py`: summarises a CSV profiler capture (see Measuring).
- `load_terrain.py`: loads all landscape streaming proxies in the editor. World Partition leaves them unloaded, so the editor shows no terrain until you run it.
- `import_ground.py`: imports the ambientCG sets from the Unity project.
- `build_ground_material.py`: builds MPC_VoyagerGrass (in place) and M_TerraGround, and assigns it to the landscape.
- `bake_grass_mask.py`: **run with normal Python** (not in the editor); writes `Tools/out/T_TerraGrassMask.png` (about 2 minutes). Then reimport it (uncompressed RGBA8, no mips, no sRGB).
- `bake_gust_noise.py`: **normal Python**; writes `Tools/out/T_GustNoise.png` (`build_grass.py` imports it).
- `build_grass.py`: T_GustNoise, M_GrassPatch and the Nanite patches. `build_grass_pcg.py`: PCG_TerraGrass plus the runtime volume (prefix with `GRASS_NANITE = False` for the classic set; see its docstring). After rebuilding, run `pcg.BuildLandscapeCache` and save. **It sets the runtime trigger before assigning the graph**: assigning first queues an editor refresh that asserts in `UPCGComponent::OnRefresh` (`!IsManagedByRuntimeGenSystem`) when PIE starts, which crashed the editor once. Every edge is checked: the range filter's outputs are `InsideFilter`/`OutsideFilter`, and a wrong pin name fails silently.
- `shaders/*.hlsl`: Custom-node bodies (TerraGround, GrassColor, GrassWind). Edit these, then re-run the build script.

### Config
- Plugins: EnhancedInput, Water (+Landmass), PCG, PythonScriptPlugin, EditorScriptingUtilities, ModelingToolsEditorMode, ModelContextProtocol, AllToolsets.
- Renderer (template): Lumen GI and reflections, Virtual Shadow Maps, mesh distance fields, hardware ray tracing, Substrate, DX12 SM6.
- Python remote execution is on (127.0.0.1, TTL 0).

## Build order (from the owner's brief)
1. ✅ Project setup.
2. ✅ Terra terrain, sky, sun, day/night, fog, clouds. 102 fps at true 2560×1440. Night sky and space transition are deferred to step 6.
3. ✅ Ground materials and grass. Unreal-native (PCG + Nanite), chosen by the owner over a custom compute plugin. Reworked to Ghost of Tsushima style on request (1 m patches, every blade shaped in the vertex shader with the Unity maths). 81 fps at true 2560×1440.
4. Trees, rocks, flowers, pebbles, house, river.
5. First-person player, ship flight, enter/exit, HUD.
6. Space: stars, nebulas, sun, planets, atmosphere transition, turbo, fuel, embryos, asteroids.
7. Thalassa: ocean, landing on water, boat, fishing, weather.
8. Placeholder planets, gravity and time systems.

## Open
- **Still limited by the render thread** (12.3 ms vs GPU 11.2 ms at 1440p). Suspects: about 264 grass ISM components (PCG makes one per mesh per 64 m cell) and VSM bookkeeping. Profile with Unreal Insights (`-trace=cpu,gpu,frame`) before step 4 adds props. Fewer components: bigger partition cells or fewer patch variants.
- **Grass still missing versus the Unity system:** budget-driven density (Unity's `adaptiveDensity`) and the player push hookup (the MPC is ready; step 5). Gradient culling, clumps, the mask and per-blade wind are in. Look ideas not done yet: golden/dry swathes like Ghost of Tsushima's fields (raise `DryColor` influence), and a soft specular sheen in the wind.
- TSR is the largest GPU pass at 1440p (2.0 ms). It's expected and buys the upscale.
- **Repo size:** Nanite landscape data is large (the step 3 commit pushed 1.8 GB of LFS).
- Flowers and pebbles (step 4) should reuse the PCG pattern and the grass mask (flowers avoid B, pebbles favour B).
- **No night sky.** Stars, the moon disk and nebulae come in step 6 (shared with space).
- The space transition (atmosphere thinning above 620 m to 1500 m) is step 6.
- The landscape edge at ±4 km is hidden by haze and hills from the ground, but visible from high altitude.
- **Command-line build** (only with the editor closed, since Live Coding blocks it):
  `"C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" glickEditor Win64 Development -Project="C:\Dev\Voyager\glick.uproject" -WaitMutex`
  Live Coding can't add modules or new UCLASSes. To restart the editor for a build: `unreal.SystemLibrary.quit_editor()` over `ue_exec.py`, build, then start `UnrealEditor.exe "C:\Dev\Voyager\glick.uproject"`.
- The old copy at `C:\Users\wball\OneDrive\Documents\Unreal Projects\glick` can be deleted.

## Measuring (how to)
- **Real 1440p numbers (preferred):** close the editor, then in PowerShell (not Git Bash, which rewrites `/Game/...` into a Windows path):
  `Start-Process "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" -ArgumentList '"C:\Dev\Voyager\glick.uproject" /Game/Voyager/Maps/L_Terra -game -windowed -ResX=2560 -ResY=1440 -ForceRes -csvCaptureFrames=2400 -csvExitOnCompletion -nosound -log=TerraBench.log -ExecCmds="t.MaxFPS 0,r.VSync 0,r.GPUCsvStatsEnabled 1"'`
  - `-ForceRes` allows a window larger than the 1080p desktop.
  - Standalone runs from the launcher engine write to `%LOCALAPPDATA%\UnrealEngine\5.8\Saved\` (logs and `Profiling\CSV\`), not the project's `Saved`.
  - `-csvExitOnCompletion` doesn't close the window, so stop the process once the log shows "Capture Ended". **Delete the old `TerraBench.log` first**, or a wait loop finds the previous run's "Capture Ended" and kills the new run.
  - Use `-csvCaptureFrames=3000` and skip 600 frames, so runtime grass generation has finished.
  - The first run compiles game shaders (about 8 minutes); later runs are quick.
  - Summarise with `python Tools/csv_summary.py "<Profile.csv>" 300` (skips 300 warm-up frames; prints frame/thread/GPU times, fps, 1% low and the top GPU passes).
- **Quick A/B in the editor:** console commands go through `ue_exec.py` → `unreal.SystemLibrary.execute_console_command(world, cmd)` (the PIE world is `UnrealEditorSubsystem.get_game_world()`). Run `ProfileGPU`, then `python Tools/gpu_passes.py [min_ms] [filter]` to print the pass tree from `Saved/Logs/glick.log`. A PIE window is clamped to the 1080p desktop.
- Screenshots go to `Saved/Screenshots/Voyager/` (not committed), via MCP `CaptureViewport` plus `Tools/capture.py` (editor view, no runtime grass). For in-game shots, start PIE and run `HighResShot 1920x1080` in the PIE world; the file lands in `Saved/Screenshots/WindowsEditor/`.

## Performance log
| Step | Where | Res (render → output) | FPS | GPU | Game thread | Notes |
|---|---|---|---|---|---|---|
| 1 | Editor viewport, OpenWorld template, aerial | 1320×746 → 1526×862 (TSR) | 109.7 | 5.20 ms | 8.96 ms | Editor overhead dominates the game thread. 0 hitches. |
| 2 | PIE window, Terra meadow 07:36, looking east toward the sun | 1439×748 → 1914×994 (TSR) | 72.9 | 11.5 ms (scene 8.8, editor Slate 1.0) | 13.2 ms | Before cloud tuning. Clouds 3.7, post 1.5, lighting 0.7, shadow depths 0.65, volumetric fog 0.5 ms. |
| 2 | Editor viewport A/B, same view | 1320×746 → 1526×862 | – | 9.4 → 7.1 ms | – | Cloud tuning: cloud shadow + sky AO 3.63 → 0.69 ms (extent 150 → 12 km, map res and ray samples ×0.5, no moon cloud shadow). |
| 2 | **Standalone 2560×1440**, meadow start view, 2100 frames | 2560×1440 output (TSR) | **102.3** (1% low 81.6) | 8.66 ms (p95 9.35) | 2.46 ms | Render thread 9.77 ms is the limit; RHI thread 4.6 ms. GPU: TSR 2.0, deferred lighting 1.3, shadow depths 1.1, volumetric fog 0.76, cloud shadow 0.57 ms. |
| 3 | PIE A/B, 73k grass clumps | 1320×746 → 1526×862 | – | shadow depths 3.5 → 3.2 → 1.5 ms | – | All grass casting → short clumps not casting → sun frozen. Led to `LightStepMinutes`. |
| 3 | **Standalone 2560×1440**, meadow with grass and Nanite landscape, 2400 frames | 2560×1440 output (TSR) | **81.4** (1% low 64.7) | 11.19 ms (p95 11.89) | 2.32 ms | Old clump grass. Render thread 12.27 ms is the limit. GPU: TSR 2.05, shadow depths 1.92, shadow projection 1.04, Nanite base pass 0.96, Nanite vis buffer 0.81, volumetric fog 0.74, lighting 0.64, cloud shadow 0.60 ms. |
| 3b | PIE A/B, Ghost of Tsushima patches, 157k patches | 1320×746 → 1526×862 | classic LODs 64.1 vs **Nanite 75.1** | 13.45 vs 10.40 ms | – | Classic: base pass 3.3 + separate velocity pass 2.5 ms. Nanite: vis buffer 1.95 + base pass 1.24 + depth/velocity 0.34 ms. |
| 3b | **Standalone 2560×1440**, Ghost of Tsushima Nanite patches (about 120 blades/m², continuous carpet), 2400 frames | 2560×1440 output (TSR) | **81.4** (1% low 66.9) | 11.17 ms (p95 11.75) | 2.26 ms | Render thread 12.28 ms is the limit. GPU: TSR 1.98, Nanite base pass 1.77, Nanite vis buffer 1.60, lighting 1.09, volumetric fog 0.73, cloud shadow 0.67, **shadow depths 0.53** (was 1.92), shadow projection 0.42 ms. |
