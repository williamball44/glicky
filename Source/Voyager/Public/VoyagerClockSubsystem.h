#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "VoyagerClockSubsystem.generated.h"

class UVoyagerPlanetData;

/**
 * Game-wide time. The home planet is the reference clock; each planet runs at TimeRate x home time.
 * Lives on the game instance so it keeps running across planet/space level changes.
 */
UCLASS()
class VOYAGER_API UVoyagerClockSubsystem : public UGameInstanceSubsystem, public FTickableGameObject
{
	GENERATED_BODY()

public:
	/** Real minutes for one full home-planet day. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voyager|Clock")
	float HomeDayLengthMinutes = 24.f;

	/** Debug time speed ([ and ] keys). 1 = normal. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voyager|Clock")
	float TimeMultiplier = 1.f;

	UFUNCTION(BlueprintPure, Category = "Voyager|Clock")
	double GetHomeHoursElapsed() const { return HomeHoursElapsed; }

	UFUNCTION(BlueprintCallable, Category = "Voyager|Clock")
	void SetHomeHoursElapsed(double Hours) { HomeHoursElapsed = Hours; }

	/** Hours since the planet's day 1 00:00. */
	UFUNCTION(BlueprintPure, Category = "Voyager|Clock")
	double TotalHours(const UVoyagerPlanetData* Planet) const;

	/** Local hour of day, 0-24. */
	UFUNCTION(BlueprintPure, Category = "Voyager|Clock")
	float LocalHour(const UVoyagerPlanetData* Planet) const;

	/** Local day number, starting at 1. */
	UFUNCTION(BlueprintPure, Category = "Voyager|Clock")
	int32 LocalDay(const UVoyagerPlanetData* Planet) const;

	/** "HH:MM". */
	UFUNCTION(BlueprintPure, Category = "Voyager|Clock")
	static FString FormatHour(float Hour);

	/**
	 * Unit vector towards the sun in a planet-surface frame (X north, Y east, Z up) for a local hour.
	 * The sun rises in the east, peaks at 62 degrees elevation to the south at noon, sets in the west.
	 */
	UFUNCTION(BlueprintPure, Category = "Voyager|Clock")
	static FVector SurfaceSunDirection(float Hour);

	// FTickableGameObject
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	virtual ETickableTickType GetTickableTickType() const override;
	virtual UWorld* GetTickableGameObjectWorld() const override;

private:
	double HomeHoursElapsed = 0.0;
};
