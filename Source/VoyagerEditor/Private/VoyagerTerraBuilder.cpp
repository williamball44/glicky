#include "VoyagerTerraBuilder.h"

#include "Async/ParallelFor.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "Landscape.h"
#include "LandscapeInfo.h"
#include "LandscapeProxy.h"
#include "LandscapeSubsystem.h"
#include "Materials/MaterialInterface.h"
#include "VoyagerEditor.h"
#include "VoyagerTerra.h"

ALandscape* UVoyagerTerraBuilder::BuildTerraLandscape(UMaterialInterface* Material, int32 GridSizeInComponents)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World)
	{
		UE_LOG(LogVoyagerEditor, Error, TEXT("BuildTerraLandscape: no editor world."));
		return nullptr;
	}
	for (TActorIterator<ALandscapeProxy> It(World); It; ++It)
	{
		UE_LOG(LogVoyagerEditor, Error, TEXT("BuildTerraLandscape: level already has a landscape (%s)."), *It->GetActorLabel());
		return nullptr;
	}

	constexpr int32 QuadsPerSection = 63;
	constexpr int32 SectionsPerComponent = 2;
	constexpr int32 ComponentCount = 32;
	constexpr int32 Size = ComponentCount * QuadsPerSection * SectionsPerComponent + 1; // 4033
	constexpr double SpacingCm = 200.0;
	const double HalfExtent = (Size - 1) * SpacingCm * 0.5;

	// Sample heights (world cm) in parallel, one row per task.
	TArray<float> Heights;
	Heights.SetNumUninitialized(Size * Size);
	ParallelFor(Size, [&](int32 Row)
	{
		for (int32 Col = 0; Col < Size; ++Col)
		{
			// Landscape local X -> world X (north), local Y -> world Y (east).
			const FVector2D P(-HalfExtent + Col * SpacingCm, -HalfExtent + Row * SpacingCm);
			Heights[Row * Size + Col] = UVoyagerTerra::TerrainHeight(P);
		}
	});

	float MaxAbs = 1.f;
	for (const float H : Heights)
	{
		MaxAbs = FMath::Max(MaxAbs, FMath::Abs(H));
	}

	// uint16 heights: Z = (V - 32768) / 128 * ScaleZ. Pick the smallest scale that fits, plus 5% headroom.
	const double ScaleZ = FMath::Max(1.0, MaxAbs * 1.05 * 128.0 / 32767.0);
	TArray<uint16> HeightData;
	HeightData.SetNumUninitialized(Heights.Num());
	for (int32 I = 0; I < Heights.Num(); ++I)
	{
		const double V = 32768.0 + Heights[I] * 128.0 / ScaleZ;
		HeightData[I] = static_cast<uint16>(FMath::Clamp(FMath::RoundToInt(V), 0, 65535));
	}

	ALandscape* Landscape = World->SpawnActor<ALandscape>(FVector(-HalfExtent, -HalfExtent, 0.0), FRotator::ZeroRotator);
	Landscape->LandscapeMaterial = Material;
	Landscape->SetActorRelativeScale3D(FVector(SpacingCm, SpacingCm, ScaleZ));

	TMap<FGuid, TArray<uint16>> HeightDataPerLayer;
	HeightDataPerLayer.Add(FGuid(), MoveTemp(HeightData));
	TMap<FGuid, TArray<FLandscapeImportLayerInfo>> MaterialLayerDataPerLayer;
	MaterialLayerDataPerLayer.Add(FGuid(), TArray<FLandscapeImportLayerInfo>());

	Landscape->Import(FGuid::NewGuid(), 0, 0, Size - 1, Size - 1, SectionsPerComponent, QuadsPerSection,
		HeightDataPerLayer, TEXT(""), MaterialLayerDataPerLayer, ELandscapeImportAlphamapType::Additive,
		TArrayView<const FLandscapeLayer>());

	Landscape->SetActorLabel(TEXT("Terra_Landscape"));

	ULandscapeInfo* Info = Landscape->GetLandscapeInfo();
	check(Info);
	Info->UpdateLayerInfoMap(Landscape);

	if (ULandscapeSubsystem* LandscapeSubsystem = World->GetSubsystem<ULandscapeSubsystem>(); LandscapeSubsystem && LandscapeSubsystem->IsGridBased())
	{
		LandscapeSubsystem->ChangeGridSize(Info, static_cast<uint32>(FMath::Max(1, GridSizeInComponents)));
	}

	UE_LOG(LogVoyagerEditor, Display, TEXT("Terra landscape: %dx%d verts, %.2f km, height range +-%.1f m, ScaleZ %.2f"),
		Size, Size, (Size - 1) * SpacingCm / 100000.0, MaxAbs / 100.f, ScaleZ);
	return Landscape;
}
