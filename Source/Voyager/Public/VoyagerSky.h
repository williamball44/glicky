#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "VoyagerSky.generated.h"

class UDirectionalLightComponent;
class UExponentialHeightFogComponent;
class UPostProcessComponent;
class USkyAtmosphereComponent;
class USkyLightComponent;
class UVolumetricCloudComponent;
class UVoyagerPlanetData;

/**
 * One actor per planet surface level that owns the whole sky: sun and moon, physical sky atmosphere,
 * real-time sky light, height fog with volumetric fog and morning mist, volumetric cloud deck and the
 * base post-process grade. Drives the day/night cycle from the game clock (or EditorHour in the editor).
 *
 * Colours of sky, sunrise and sunset come from the Sky Atmosphere simulation instead of hand-painted
 * gradients; this actor only sets sun/moon direction, light levels and fog.
 */
UCLASS()
class VOYAGER_API AVoyagerSky : public AActor
{
	GENERATED_BODY()

public:
	AVoyagerSky();

	virtual void Tick(float DeltaSeconds) override;
	virtual bool ShouldTickIfViewportsOnly() const override { return true; }
	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void BeginPlay() override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voyager|Sky")
	TObjectPtr<UVoyagerPlanetData> Planet;

	/** Hour shown in the editor (and in game when there is no planet/clock). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voyager|Sky", meta = (ClampMin = "0", ClampMax = "24"))
	float EditorHour = 7.6f;

	/** Run the day/night cycle in the editor viewport. */
	UPROPERTY(EditAnywhere, Category = "Voyager|Sky")
	bool bAnimateInEditor = false;

	UPROPERTY(EditAnywhere, Category = "Voyager|Sky", meta = (EditCondition = "bAnimateInEditor"))
	float EditorHoursPerSecond = 0.5f;

	/** Sun illuminance at full day (lux). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voyager|Sky|Lights")
	float SunIlluminance = 6.f;

	/** Moon illuminance at full night (lux). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voyager|Sky|Lights")
	float MoonIlluminance = 0.35f;

	/**
	 * The sun and moon turn in steps of this many local minutes instead of every frame. Any rotation of a
	 * directional light invalidates its whole virtual shadow map cache; per-frame turning cost 1.7 ms of shadow
	 * rendering on Terra. 1 minute = 0.25 degrees, too small to see.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voyager|Sky|Lights", meta = (ClampMin = "0"))
	float LightStepMinutes = 1.f;

	/** Hour of peak morning mist, and how long (std. dev., hours) it lasts. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voyager|Sky|Fog")
	float MistHour = 6.8f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voyager|Sky|Fog")
	float MistWidthHours = 1.6f;

	/** Thickness of the ground mist layer (metres to fall to half density). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voyager|Sky|Fog")
	float MistHalfHeight = 12.f;

	UFUNCTION(BlueprintPure, Category = "Voyager|Sky")
	float GetLocalHour() const { return CurrentHour; }

	/** Unit vector towards the sun (world space). */
	UFUNCTION(BlueprintPure, Category = "Voyager|Sky")
	FVector GetSunDirection() const { return SunDirection; }

	/** 0 at night, 1 in full day. */
	UFUNCTION(BlueprintPure, Category = "Voyager|Sky")
	float GetDayAmount() const { return DayAmount; }

	/** Re-read the planet data (cloud deck, fog). */
	UFUNCTION(BlueprintCallable, Category = "Voyager|Sky")
	void ApplyPlanet();

	/** Set sun, moon and fog for a local hour. */
	UFUNCTION(BlueprintCallable, Category = "Voyager|Sky")
	void ApplyHour(float Hour);

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> Root;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UDirectionalLightComponent> Sun;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UDirectionalLightComponent> Moon;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USkyAtmosphereComponent> Atmosphere;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USkyLightComponent> SkyLight;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UExponentialHeightFogComponent> HeightFog;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UVolumetricCloudComponent> Clouds;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UPostProcessComponent> PostProcess;

private:
	float ResolveHour(float DeltaSeconds);

	float CurrentHour = 7.6f;
	float LightHour = -100.f; // hour the sun/moon rotation was last applied for
	FVector SunDirection = FVector::UpVector;
	float DayAmount = 1.f;
};
