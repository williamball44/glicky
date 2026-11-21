#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "VoyagerTerra.generated.h"

/**
 * Terra (home planet) layout maths, ported from the Unity HomeSurface.
 *
 * World axes: X north, Y east, Z up, centimetres. Internally the formulas work in the Unity frame
 * (metres, x east, z north) so the numbers match the reference one for one.
 */
UCLASS()
class VOYAGER_API UVoyagerTerra : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	static constexpr float WaterLevelM = 18.f;
	static constexpr float FieldHeightM = 22.f;
	static constexpr float HouseYawDeg = 120.f;

	/** House and ship pads, world cm (X north, Y east). */
	static FVector2D HouseXY() { return FVector2D(2500.0, -3000.0); }
	static FVector2D ShipXY() { return FVector2D(-2200.0, 3200.0); }

	/** Ground height (world Z, cm) of the generated Terra landscape at a world XY (cm). */
	UFUNCTION(BlueprintPure, Category = "Voyager|Terra")
	static float TerrainHeight(FVector2D WorldXY);

	/** River centre line: world Y (east, cm) of the river at world X (north, cm). */
	UFUNCTION(BlueprintPure, Category = "Voyager|Terra")
	static float RiverY(float WorldX);

	// Unity-frame helpers (metres; x east, z north).
	static float HeightM(float X, float Z);
	static float RiverXM(float Z);
	static float Fbm(float X, float Y, int32 Octaves);
	static float Ridged(float X, float Y, int32 Octaves);
	static float Smooth01(float A, float B, float X);
};
