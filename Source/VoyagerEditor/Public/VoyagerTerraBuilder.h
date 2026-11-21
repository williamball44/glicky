#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "VoyagerTerraBuilder.generated.h"

class ALandscape;
class UMaterialInterface;

/** Editor-only tools that generate Terra's content. Callable from Python (unreal.VoyagerTerraBuilder). */
UCLASS()
class VOYAGEREDITOR_API UVoyagerTerraBuilder : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Generates the Terra landscape in the current editor level from UVoyagerTerra::TerrainHeight.
	 * 32x32 components of 2x2 sections x 63 quads = 4033^2 vertices at 2 m spacing (8.06 km square),
	 * centred on the world origin. In a World Partition level it is split into streaming proxies of
	 * GridSizeInComponents^2 components. Fails if the level already has a landscape.
	 */
	UFUNCTION(BlueprintCallable, Category = "Voyager|Terra", meta = (DevelopmentOnly))
	static ALandscape* BuildTerraLandscape(UMaterialInterface* Material, int32 GridSizeInComponents = 8);
};
