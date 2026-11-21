#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "VoyagerGrassBuilder.generated.h"

class UMaterialInterface;
class UStaticMesh;

/**
 * Builds grass-clump static meshes from the Unity grass maths (GrassBlades.compute/.shader): one clump is a
 * Voronoi cell about 0.9 m across whose blades share a height, are tallest in the middle and lean outward,
 * with about 5% long blades that flop over. Each blade is a cubic Bezier curve swept into a thin strip
 * (about 2 cm wide), 8 segments, or 2 for blades under 20 cm. Meshes are Nanite with Voxelize shape
 * preservation, so distant grass keeps its volume instead of thinning out.
 *
 * Vertex colour: R = height along the blade (0 root, 1 tip), G = per-blade random, B = blade height / 1 m,
 * A = distance from the clump centre (0..1). UV0 = (across 0..1, height along blade). The grass material
 * uses these for colour gradients and wind.
 */
UCLASS()
class VOYAGEREDITOR_API UVoyagerGrassBuilder : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Creates or rebuilds a clump mesh at AssetPath (e.g. /Game/Voyager/Grass/SM_GrassClump_00).
	 * ClumpHeight scales every blade (Unity range 0.5-1.8); BladeCount is the number of blades in the clump.
	 * The caller saves the asset.
	 */
	UFUNCTION(BlueprintCallable, Category = "Voyager|Grass", meta = (DevelopmentOnly))
	static UStaticMesh* BuildGrassClump(const FString& AssetPath, UMaterialInterface* Material, int32 Seed,
		float ClumpHeight = 1.f, int32 BladeCount = 90, float ClumpRadius = 45.f, float BaseHeight = 38.f, float HalfWidth = 1.1f);

	/** Builds Nanite data for every loaded landscape proxy in the editor world (load them first). */
	UFUNCTION(BlueprintCallable, Category = "Voyager|Terra", meta = (DevelopmentOnly))
	static void BuildLandscapeNanite();
};
