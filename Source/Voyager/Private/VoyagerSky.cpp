#include "VoyagerSky.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"
#include "VoyagerClockSubsystem.h"
#include "VoyagerPlanetData.h"

namespace
{
	float Smooth01(float A, float B, float X)
	{
		const float T = FMath::Clamp((X - A) / (B - A), 0.f, 1.f);
		return T * T * (3.f - 2.f * T);
	}
}

AVoyagerSky::AVoyagerSky()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PrePhysics;
	SetIsSpatiallyLoaded(false); // always loaded in World Partition

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;
	Root->SetMobility(EComponentMobility::Movable);

	Sun = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("Sun"));
	Sun->SetupAttachment(Root);
	Sun->SetMobility(EComponentMobility::Movable);
	Sun->Intensity = SunIlluminance;
	Sun->bAtmosphereSunLight = true;
	Sun->AtmosphereSunLightIndex = 0;
	Sun->bCastCloudShadows = true;
	Sun->bCastShadowsOnClouds = true;
	Sun->bCastShadowsOnAtmosphere = true;
	Sun->LightSourceAngle = 0.75f; // slightly larger, softer sun for the hazy golden look
	Sun->AtmosphereSunDiskColorScale = FLinearColor(1.f, 0.93f, 0.82f);
	Sun->VolumetricScatteringIntensity = 1.2f;
	// Cloud shadow map: the default 150 km footprint wastes resolution on an 8 km world. Measured on Terra:
	// cloud shadow + sky AO 3.63 ms -> 0.69 ms with these and the sky light settings below.
	Sun->CloudShadowExtent = 12.f;
	Sun->CloudShadowMapResolutionScale = 0.5f;
	Sun->CloudShadowRaySampleCountScale = 0.5f;

	Moon = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("Moon"));
	Moon->SetupAttachment(Root);
	Moon->SetMobility(EComponentMobility::Movable);
	Moon->Intensity = MoonIlluminance;
	Moon->LightColor = FColor(158, 184, 255);
	Moon->bAtmosphereSunLight = true;
	Moon->AtmosphereSunLightIndex = 1;
	Moon->LightSourceAngle = 0.55f;
	Moon->AtmosphereSunDiskColorScale = FLinearColor(0.3f, 0.32f, 0.36f);
	Moon->bCastCloudShadows = false; // a second cloud shadow map isn't worth it for moonlight

	Atmosphere = CreateDefaultSubobject<USkyAtmosphereComponent>(TEXT("SkyAtmosphere"));
	Atmosphere->SetupAttachment(Root);

	SkyLight = CreateDefaultSubobject<USkyLightComponent>(TEXT("SkyLight"));
	SkyLight->SetupAttachment(Root);
	SkyLight->SetMobility(EComponentMobility::Movable);
	SkyLight->bRealTimeCapture = true;
	SkyLight->bCloudAmbientOcclusion = true;
	SkyLight->CloudAmbientOcclusionExtent = 12.f;
	SkyLight->CloudAmbientOcclusionMapResolutionScale = 0.5f;

	HeightFog = CreateDefaultSubobject<UExponentialHeightFogComponent>(TEXT("HeightFog"));
	HeightFog->SetupAttachment(Root);
	HeightFog->FogDensity = 0.012f;
	HeightFog->FogHeightFalloff = 0.2f; // halves every 50 m
	HeightFog->bEnableVolumetricFog = true;
	HeightFog->VolumetricFogScatteringDistribution = 0.75f; // strong forward scattering: god rays toward the sun
	HeightFog->VolumetricFogAlbedo = FColor(255, 246, 232);
	HeightFog->VolumetricFogDistance = 12000.f;
	HeightFog->DirectionalInscatteringExponent = 6.f;
	HeightFog->DirectionalInscatteringStartDistance = 3000.f;

	Clouds = CreateDefaultSubobject<UVolumetricCloudComponent>(TEXT("Clouds"));
	Clouds->SetupAttachment(Root);
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> CloudMat(TEXT("/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst.m_SimpleVolumetricCloud_Inst"));
	if (CloudMat.Succeeded())
	{
		Clouds->Material = CloudMat.Object;
	}

	PostProcess = CreateDefaultSubobject<UPostProcessComponent>(TEXT("PostProcess"));
	PostProcess->SetupAttachment(Root);
	PostProcess->bUnbound = true;
	FPostProcessSettings& S = PostProcess->Settings;
	S.bOverride_BloomIntensity = true;
	S.BloomIntensity = 0.6f;
	S.bOverride_VignetteIntensity = true;
	S.VignetteIntensity = 0.3f;
	S.bOverride_ColorSaturation = true;
	S.ColorSaturation = FVector4(1.f, 1.f, 1.f, 1.06f);
}

void AVoyagerSky::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	ApplyPlanet();
	LightHour = -100.f; // an edited hour always moves the lights
	ApplyHour(EditorHour);
}

void AVoyagerSky::BeginPlay()
{
	Super::BeginPlay();
	ApplyPlanet();
	ApplyHour(ResolveHour(0.f));
}

void AVoyagerSky::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	ApplyHour(ResolveHour(DeltaSeconds));
}

float AVoyagerSky::ResolveHour(float DeltaSeconds)
{
	const UWorld* World = GetWorld();
	if (World && World->IsGameWorld())
	{
		if (const UGameInstance* GI = World->GetGameInstance())
		{
			if (const UVoyagerClockSubsystem* Clock = GI->GetSubsystem<UVoyagerClockSubsystem>(); Clock && Planet)
			{
				return Clock->LocalHour(Planet);
			}
		}
		return EditorHour;
	}

	if (bAnimateInEditor)
	{
		EditorHour = FMath::Fmod(EditorHour + DeltaSeconds * EditorHoursPerSecond, 24.f);
	}
	return EditorHour;
}

void AVoyagerSky::ApplyPlanet()
{
	const float GroundM = Planet ? Planet->GroundHeight : 0.f;
	const float BaseM = Planet ? Planet->CloudBase : 420.f;
	const float TopM = Planet ? Planet->CloudTop : 620.f;

	// Cloud layer altitudes are in km above the atmosphere's ground (world Z = 0).
	Clouds->SetLayerBottomAltitude((GroundM + BaseM) / 1000.f);
	Clouds->SetLayerHeight(FMath::Max(TopM - BaseM, 10.f) / 1000.f);
	if (Planet && Planet->CloudMaterial)
	{
		Clouds->SetMaterial(Planet->CloudMaterial);
	}

	// Fog layers are measured from the fog component; keep it on the field.
	HeightFog->SetWorldLocation(FVector(GetActorLocation().X, GetActorLocation().Y, GroundM * 100.f));
}

void AVoyagerSky::ApplyHour(float Hour)
{
	CurrentHour = Hour;
	SunDirection = UVoyagerClockSubsystem::SurfaceSunDirection(Hour);
	const float E = SunDirection.Z;
	DayAmount = Smooth01(-0.14f, 0.22f, E);
	const float Golden = (1.f - Smooth01(0.f, 0.5f, FMath::Abs(E - 0.06f))) * Smooth01(-0.12f, 0.f, E);

	// Sun: the atmosphere colours it; we only fade it out below the horizon.
	const FLinearColor Tint = Planet ? Planet->SunTint : FLinearColor::White;
	const float SunI = SunIlluminance * Smooth01(-0.06f, 0.04f, E);
	Sun->SetIntensity(SunI);
	Sun->SetLightColor(Tint);
	Sun->SetVisibility(SunI > 0.f);

	// Moon roughly opposite the sun, offset so it isn't on the same arc.
	const FVector MoonDir = FQuat(FVector::XAxisVector, FMath::DegreesToRadians(25.f)).RotateVector(-SunDirection);
	const float MoonI = MoonIlluminance * Smooth01(0.f, 0.25f, MoonDir.Z) * (1.f - Smooth01(-0.1f, 0.05f, E));

	// Turn the lights only in LightStepMinutes steps so the virtual shadow map cache survives between steps.
	float Since = FMath::Abs(Hour - LightHour);
	Since = FMath::Min(Since, 24.f - Since); // across midnight
	if (LightHour < -50.f || Since * 60.f >= LightStepMinutes)
	{
		LightHour = Hour;
		Sun->SetWorldRotation((-SunDirection).Rotation());
		Moon->SetWorldRotation((-MoonDir).Rotation());
	}
	Moon->SetIntensity(MoonI);
	Moon->SetVisibility(MoonI > 0.f);

	// Fog: base haze that dims at night, a warm glow toward the sun, and low morning mist.
	const float BaseDensity = Planet ? Planet->FogDensity : 0.012f;
	const float MistPeak = Planet ? Planet->MorningMistDensity : 0.05f;
	const float Mist = FMath::Exp(-FMath::Square((Hour - MistHour) / MistWidthHours));
	HeightFog->SetFogDensity(BaseDensity * (1.f + 0.6f * Mist));

	const FLinearColor FogCol = Planet ? Planet->FogColor : FLinearColor(0.74f, 0.81f, 0.88f);
	const FLinearColor NightFog(0.004f, 0.006f, 0.012f);
	HeightFog->SetFogInscatteringColor(FMath::Lerp(NightFog, FogCol * 0.35f, DayAmount));
	const FLinearColor SunHaze = FMath::Lerp(FLinearColor(1.f, 0.85f, 0.65f), FLinearColor(1.f, 0.62f, 0.32f), Golden);
	HeightFog->SetDirectionalInscatteringColor(SunHaze * (0.25f + 0.35f * Golden) * DayAmount);

	FExponentialHeightFogData MistLayer;
	MistLayer.FogDensity = MistPeak * Mist;
	MistLayer.FogHeightFalloff = FMath::Clamp(1000.f / (FMath::Max(MistHalfHeight, 5.f) * 100.f), 0.f, 2.f);
	MistLayer.FogHeightOffset = 0.f;
	HeightFog->SetSecondFogData(MistLayer);
}
