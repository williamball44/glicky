#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "VoyagerPlanetData.generated.h"

class UMaterialInterface;

UENUM(BlueprintType)
enum class EVoyagerSurfaceKind : uint8
{
	Home,
	Ocean,
	Placeholder
};

/**
 * Everything that defines a planet. All planets share the same mechanics; only these numbers differ.
 * Distances are in metres unless the name says otherwise.
 */
UCLASS(BlueprintType)
class VOYAGER_API UVoyagerPlanetData : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Planet")
	FText DisplayName;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Planet")
	EVoyagerSurfaceKind Kind = EVoyagerSurfaceKind::Placeholder;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Planet")
	bool bLandable = true;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Planet", meta = (MultiLine = true))
	FText Description;

	/** Surface gravity in m/s^2. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Rules", meta = (ClampMin = "0"))
	float Gravity = 9.81f;

	/** Local hours that pass per home-planet hour. 4 = one home hour is four hours here. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Rules", meta = (ClampMin = "0"))
	float TimeRate = 1.f;

	/** Local hour of day when the game starts. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Rules", meta = (ClampMin = "0", ClampMax = "24"))
	float StartHour = 8.f;

	/** Height of the main walkable ground (the field) above world Z = 0. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Atmosphere")
	float GroundHeight = 0.f;

	/** Cloud deck, in metres above GroundHeight. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Atmosphere")
	float CloudBase = 420.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Atmosphere")
	float CloudTop = 620.f;

	/** Altitude above GroundHeight where the sky has thinned out and you pass into space. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Atmosphere")
	float SpaceCeiling = 1500.f;

	/** Exponential height fog density at ground level in clear weather. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Atmosphere", meta = (ClampMin = "0"))
	float FogDensity = 0.012f;

	/** Extra low-lying fog at its peak (around MistHour). 0 = no morning mist. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Atmosphere", meta = (ClampMin = "0"))
	float MorningMistDensity = 0.05f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Atmosphere")
	FLinearColor FogColor = FLinearColor(0.74f, 0.81f, 0.88f);

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Atmosphere")
	FLinearColor SunTint = FLinearColor::White;

	/**
	 * Volumetric cloud material for the deck. Must suit a thin layer (CloudTop - CloudBase); the engine's
	 * default instance is tuned for a multi-km layer and shows almost nothing here.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Atmosphere")
	TObjectPtr<UMaterialInterface> CloudMaterial;

	/** Position of the planet sphere in space (metres). Used from step 6. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Space")
	FVector SpacePosition = FVector::ZeroVector;

	/** Radius of the planet sphere in space (metres). Used from step 6. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Space", meta = (ClampMin = "1"))
	float Radius = 1500.f;
};
