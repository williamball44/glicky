#include "VoyagerClockSubsystem.h"

#include "Engine/GameInstance.h"
#include "VoyagerPlanetData.h"

double UVoyagerClockSubsystem::TotalHours(const UVoyagerPlanetData* Planet) const
{
	const double StartHour = Planet ? Planet->StartHour : 0.0;
	const double Rate = Planet ? Planet->TimeRate : 1.0;
	return StartHour + HomeHoursElapsed * Rate;
}

float UVoyagerClockSubsystem::LocalHour(const UVoyagerPlanetData* Planet) const
{
	const double Total = TotalHours(Planet);
	return static_cast<float>(Total - 24.0 * FMath::Floor(Total / 24.0));
}

int32 UVoyagerClockSubsystem::LocalDay(const UVoyagerPlanetData* Planet) const
{
	return static_cast<int32>(FMath::Floor(TotalHours(Planet) / 24.0)) + 1;
}

FString UVoyagerClockSubsystem::FormatHour(float Hour)
{
	const int32 H = FMath::FloorToInt(Hour) % 24;
	const int32 M = FMath::FloorToInt((Hour - FMath::Floor(Hour)) * 60.f);
	return FString::Printf(TEXT("%02d:%02d"), H, M);
}

FVector UVoyagerClockSubsystem::SurfaceSunDirection(float Hour)
{
	constexpr float Tilt = FMath::DegreesToRadians(28.f); // arc leans south for longer, nicer shadows
	const float A = (Hour - 12.f) / 24.f * UE_TWO_PI;       // 0 at noon
	const float Up = FMath::Cos(A);
	return FVector(-Up * FMath::Sin(Tilt), -FMath::Sin(A), Up * FMath::Cos(Tilt)).GetSafeNormal();
}

void UVoyagerClockSubsystem::Tick(float DeltaTime)
{
	if (HomeDayLengthMinutes > 0.f)
	{
		HomeHoursElapsed += DeltaTime * TimeMultiplier * 24.0 / (HomeDayLengthMinutes * 60.0);
	}
}

TStatId UVoyagerClockSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UVoyagerClockSubsystem, STATGROUP_Tickables);
}

ETickableTickType UVoyagerClockSubsystem::GetTickableTickType() const
{
	return IsTemplate() ? ETickableTickType::Never : ETickableTickType::Always;
}

UWorld* UVoyagerClockSubsystem::GetTickableGameObjectWorld() const
{
	const UGameInstance* GI = GetGameInstance();
	return GI ? GI->GetWorld() : nullptr;
}
