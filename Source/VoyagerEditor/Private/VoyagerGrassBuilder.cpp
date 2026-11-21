#include "VoyagerGrassBuilder.h"

#include "AssetRegistry/AssetRegistryModule.h"
#include "Editor.h"
#include "Engine/StaticMesh.h"
#include "LandscapeEditTypes.h"
#include "LandscapeSubsystem.h"
#include "Materials/MaterialInterface.h"
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#include "UObject/Package.h"
#include "VoyagerEditor.h"

namespace
{
	struct FRng
	{
		uint32 State;
		explicit FRng(uint32 Seed) : State(Seed * 747796405u + 2891336453u) {}
		float Next()
		{
			// PCG hash, as in the Unity grass (VoyagerClumps.hlsl).
			State = State * 747796405u + 2891336453u;
			uint32 Word = ((State >> ((State >> 28u) + 4u)) ^ State) * 277803737u;
			return static_cast<float>((Word >> 22u) ^ Word) * (1.f / 4294967296.f);
		}
	};

	FVector3f Bezier(const FVector3f& P0, const FVector3f& P1, const FVector3f& P2, const FVector3f& P3, float T)
	{
		const float U = 1.f - T;
		return U * U * U * P0 + 3.f * U * U * T * P1 + 3.f * U * T * T * P2 + T * T * T * P3;
	}

	FVector3f BezierTangent(const FVector3f& P0, const FVector3f& P1, const FVector3f& P2, const FVector3f& P3, float T)
	{
		const float U = 1.f - T;
		return 3.f * U * U * (P1 - P0) + 6.f * U * T * (P2 - P1) + 3.f * T * T * (P3 - P2);
	}
}

UStaticMesh* UVoyagerGrassBuilder::BuildGrassClump(const FString& AssetPath, UMaterialInterface* Material, int32 Seed,
	float ClumpHeight, int32 BladeCount, float ClumpRadius, float BaseHeight, float HalfWidth)
{
	const FString PackageName = FPackageName::ObjectPathToPackageName(AssetPath);
	const FString AssetName = FPackageName::GetLongPackageAssetName(PackageName);
	UPackage* Package = CreatePackage(*PackageName);
	Package->FullyLoad();

	UStaticMesh* Mesh = FindObject<UStaticMesh>(Package, *AssetName);
	const bool bNew = Mesh == nullptr;
	if (bNew)
	{
		Mesh = NewObject<UStaticMesh>(Package, *AssetName, RF_Public | RF_Standalone | RF_Transactional);
	}
	Mesh->Modify();
	Mesh->GetStaticMaterials().Reset();
	Mesh->GetStaticMaterials().Add(FStaticMaterial(Material, TEXT("Grass"), TEXT("Grass")));
	Mesh->SetNumSourceModels(1);
	FStaticMeshSourceModel& Source = Mesh->GetSourceModel(0);
	Source.BuildSettings.bRecomputeNormals = false;
	Source.BuildSettings.bRecomputeTangents = true;
	Source.BuildSettings.bGenerateLightmapUVs = false;
	Source.BuildSettings.bRemoveDegenerates = false;

	FMeshDescription* MD = Mesh->CreateMeshDescription(0);
	FStaticMeshAttributes Attributes(*MD);
	Attributes.Register();
	TVertexAttributesRef<FVector3f> Positions = Attributes.GetVertexPositions();
	TVertexInstanceAttributesRef<FVector3f> Normals = Attributes.GetVertexInstanceNormals();
	TVertexInstanceAttributesRef<FVector2f> UVs = Attributes.GetVertexInstanceUVs();
	TVertexInstanceAttributesRef<FVector4f> Colors = Attributes.GetVertexInstanceColors();
	UVs.SetNumChannels(1);
	const FPolygonGroupID Group = MD->CreatePolygonGroup();
	Attributes.GetPolygonGroupMaterialSlotNames()[Group] = TEXT("Grass");

	FRng Rng(static_cast<uint32>(Seed) * 2654435761u + 17u);
	const FVector3f Up(0.f, 0.f, 1.f);
	constexpr float ShortHeight = 20.f; // cm: shorter blades use 2 segments (vertex donation)

	for (int32 B = 0; B < BladeCount; ++B)
	{
		// Root: uniform in the clump disc; fromCentre drives height, lean and the outward facing.
		const float R = ClumpRadius * FMath::Sqrt(Rng.Next());
		const float A = Rng.Next() * UE_TWO_PI;
		const FVector3f Root(R * FMath::Cos(A), R * FMath::Sin(A), -8.f);
		const float FromCentre = FMath::Clamp(R / ClumpRadius, 0.f, 1.f);

		float Height = BaseHeight * (0.6f + 0.6f * Rng.Next()) * ClumpHeight * (1.f - 0.45f * FromCentre);
		const float Facing = A + (Rng.Next() - 0.5f) * 1.4f;   // lean out of the clump
		float Lean = 0.12f + 0.3f * Rng.Next() + FromCentre * 0.45f;
		if (Rng.Next() < 0.05f)
		{
			Height *= 1.6f; // the odd long blade that flops over
			Lean += 0.35f;
		}
		const float Half = HalfWidth * (0.75f + 0.5f * Rng.Next());
		const float BladeRand = Rng.Next();
		const int32 Segs = Height < ShortHeight ? 2 : 8;

		// Bezier control points (no wind: the material bends the blade).
		const FVector3f F(FMath::Cos(Facing), FMath::Sin(Facing), 0.f);
		const FVector3f Side(-F.Y, F.X, 0.f);
		FVector3f TipOff = F * Lean * Height;
		float Horiz = TipOff.Size();
		if (Horiz > 0.9f * Height)
		{
			TipOff *= 0.9f * Height / Horiz;
			Horiz = 0.9f * Height;
		}
		const float TipZ = FMath::Sqrt(FMath::Max(Height * Height - Horiz * Horiz, 0.f)); // keep the blade's length
		const FVector3f P0 = Root;
		const FVector3f P1 = Root + Up * Height * 0.45f;
		const FVector3f P2 = Root + Up * TipZ * 0.8f + TipOff * 0.45f;
		const FVector3f P3 = Root + Up * TipZ + TipOff;

		// Rows 0..Segs-1 have a left and right vertex; row Segs is the tip point.
		TArray<FVertexInstanceID, TInlineAllocator<17>> Row;
		for (int32 I = 0; I <= Segs; ++I)
		{
			const float T = static_cast<float>(I) / Segs;
			const FVector3f C = Bezier(P0, P1, P2, P3, T);
			const FVector3f Tan = BezierTangent(P0, P1, P2, P3, T).GetSafeNormal();
			const FVector3f N0 = FVector3f::CrossProduct(Tan, Side).GetSafeNormal();
			const float Width = I == Segs ? 0.f : Half * (1.f - T * T * 0.85f);
			const int32 Count = I == Segs ? 1 : 2;
			for (int32 S = 0; S < Count; ++S)
			{
				const float Across = Count == 1 ? 0.f : (S == 0 ? -1.f : 1.f);
				const FVertexID V = MD->CreateVertex();
				Positions[V] = C + Side * Across * Width;
				const FVertexInstanceID VI = MD->CreateVertexInstance(V);
				// Rounded blade, and biased upward so the field reads as a surface rather than a fence.
				FVector3f N = (N0 + Side * Across * 0.45f).GetSafeNormal();
				N = FMath::Lerp(N, Up, 0.35f).GetSafeNormal();
				Normals[VI] = N;
				UVs.Set(VI, 0, FVector2f(Across * 0.5f + 0.5f, T));
				Colors[VI] = FVector4f(T, BladeRand, FMath::Clamp(Height / 100.f, 0.f, 1.f), FromCentre);
				Row.Add(VI);
			}
		}
		for (int32 S = 0; S < Segs - 1; ++S)
		{
			const FVertexInstanceID L0 = Row[S * 2], R0 = Row[S * 2 + 1], L1 = Row[S * 2 + 2], R1 = Row[S * 2 + 3];
			MD->CreateTriangle(Group, { L0, L1, R0 });
			MD->CreateTriangle(Group, { R0, L1, R1 });
		}
		const int32 Last = (Segs - 1) * 2;
		MD->CreateTriangle(Group, { Row[Last], Row[Last + 2], Row[Last + 1] });
	}

	Mesh->CommitMeshDescription(0);
	FMeshNaniteSettings Nanite = Mesh->GetNaniteSettings();
	Nanite.bEnabled = true;
	Nanite.ShapePreservation = ENaniteShapePreservation::Voxelize;
	Mesh->SetNaniteSettings(Nanite);
	Mesh->Build(false);
	Mesh->PostEditChange();
	Mesh->MarkPackageDirty();
	if (bNew)
	{
		FAssetRegistryModule::AssetCreated(Mesh);
	}
	UE_LOG(LogVoyagerEditor, Display, TEXT("Grass clump %s: %d blades, height x%.2f"), *AssetPath, BladeCount, ClumpHeight);
	return Mesh;
}

namespace
{
	struct FPatchBlade
	{
		FVector2f Root;
		float Height;
		float Rand;
		FVector2f Facing;
	};

	/** Appends one LOD's blades (straight strips) to a mesh description. */
	void WritePatchLOD(FMeshDescription& MD, const TArray<FPatchBlade>& Blades, int32 Stride, int32 Segs, float HalfWidth)
	{
		FStaticMeshAttributes Attributes(MD);
		Attributes.Register();
		TVertexAttributesRef<FVector3f> Positions = Attributes.GetVertexPositions();
		TVertexInstanceAttributesRef<FVector3f> Normals = Attributes.GetVertexInstanceNormals();
		TVertexInstanceAttributesRef<FVector2f> UVs = Attributes.GetVertexInstanceUVs();
		UVs.SetNumChannels(4);
		const FPolygonGroupID Group = MD.CreatePolygonGroup();
		Attributes.GetPolygonGroupMaterialSlotNames()[Group] = TEXT("Grass");

		for (int32 B = 0; B < Blades.Num(); B += Stride)
		{
			const FPatchBlade& Blade = Blades[B];
			const FVector3f Side(-Blade.Facing.Y, Blade.Facing.X, 0.f);
			const FVector3f Normal(Blade.Facing.X, Blade.Facing.Y, 0.f);
			TArray<FVertexInstanceID, TInlineAllocator<16>> Row;
			for (int32 I = 0; I <= Segs; ++I)
			{
				const float T = static_cast<float>(I) / Segs;
				const float Width = I == Segs ? 0.f : HalfWidth * (1.f - T * T * 0.85f);
				const int32 Count = I == Segs ? 1 : 2;
				for (int32 S = 0; S < Count; ++S)
				{
					const float Across = Count == 1 ? 0.f : (S == 0 ? -1.f : 1.f);
					const FVertexID V = MD.CreateVertex();
					Positions[V] = FVector3f(Blade.Root.X, Blade.Root.Y, T * Blade.Height) + Side * Across * Width;
					const FVertexInstanceID VI = MD.CreateVertexInstance(V);
					Normals[VI] = Normal; // the material computes the real (bent, rounded) normal
					UVs.Set(VI, 0, FVector2f(Across * 0.5f + 0.5f, T));
					UVs.Set(VI, 1, Blade.Root);
					UVs.Set(VI, 2, FVector2f(Blade.Height, Blade.Rand));
					UVs.Set(VI, 3, Blade.Facing);
					Row.Add(VI);
				}
			}
			for (int32 S = 0; S < Segs - 1; ++S)
			{
				const FVertexInstanceID L0 = Row[S * 2], R0 = Row[S * 2 + 1], L1 = Row[S * 2 + 2], R1 = Row[S * 2 + 3];
				MD.CreateTriangle(Group, { L0, L1, R0 });
				MD.CreateTriangle(Group, { R0, L1, R1 });
			}
			const int32 Last = (Segs - 1) * 2;
			MD.CreateTriangle(Group, { Row[Last], Row[Last + 2], Row[Last + 1] });
		}
	}
}

UStaticMesh* UVoyagerGrassBuilder::BuildGrassPatch(const FString& AssetPath, UMaterialInterface* Material, int32 Seed,
	int32 BladeCount, float PatchSize, float BaseHeight, float HalfWidth, bool bNanite)
{
	const FString PackageName = FPackageName::ObjectPathToPackageName(AssetPath);
	const FString AssetName = FPackageName::GetLongPackageAssetName(PackageName);
	UPackage* Package = CreatePackage(*PackageName);
	Package->FullyLoad();

	UStaticMesh* Mesh = FindObject<UStaticMesh>(Package, *AssetName);
	const bool bNew = Mesh == nullptr;
	if (bNew)
	{
		Mesh = NewObject<UStaticMesh>(Package, *AssetName, RF_Public | RF_Standalone | RF_Transactional);
	}
	Mesh->Modify();
	Mesh->GetStaticMaterials().Reset();
	Mesh->GetStaticMaterials().Add(FStaticMaterial(Material, TEXT("Grass"), TEXT("Grass")));

	// Stratified roots: one blade per cell of a jittered grid, shuffled so LODs that keep every Nth blade
	// still cover the patch evenly.
	FRng Rng(static_cast<uint32>(Seed) * 2654435761u + 91u);
	const int32 Grid = FMath::CeilToInt(FMath::Sqrt(static_cast<float>(BladeCount)));
	const float Cell = PatchSize / Grid;
	TArray<FPatchBlade> Blades;
	for (int32 Y = 0; Y < Grid; ++Y)
	{
		for (int32 X = 0; X < Grid; ++X)
		{
			FPatchBlade Blade;
			Blade.Root = FVector2f(-PatchSize * 0.5f + (X + Rng.Next()) * Cell, -PatchSize * 0.5f + (Y + Rng.Next()) * Cell);
			Blade.Height = BaseHeight;
			Blade.Rand = Rng.Next();
			const float A = Rng.Next() * UE_TWO_PI;
			Blade.Facing = FVector2f(FMath::Cos(A), FMath::Sin(A));
			Blades.Add(Blade);
		}
	}
	for (int32 I = Blades.Num() - 1; I > 0; --I)
	{
		Blades.Swap(I, FMath::Min(static_cast<int32>(Rng.Next() * (I + 1)), I));
	}
	Blades.SetNum(FMath::Min(BladeCount, Blades.Num()));

	struct FLodSpec { int32 Stride; int32 Segs; float WidthMul; float ScreenSize; };
	const TArray<FLodSpec> Lods = bNanite
		? TArray<FLodSpec>{ { 1, 6, 1.f, 1.f } }
		: TArray<FLodSpec>{ { 1, 6, 1.f, 1.f }, { 3, 3, 1.8f, 0.12f }, { 8, 1, 3.0f, 0.04f } };

	Mesh->SetNumSourceModels(Lods.Num());
	Mesh->SetAutoComputeLODScreenSize(false);
	for (int32 L = 0; L < Lods.Num(); ++L)
	{
		FStaticMeshSourceModel& Source = Mesh->GetSourceModel(L);
		Source.BuildSettings.bRecomputeNormals = false;
		Source.BuildSettings.bRecomputeTangents = true;
		Source.BuildSettings.bGenerateLightmapUVs = false;
		Source.BuildSettings.bRemoveDegenerates = false;
		Source.ScreenSize.Default = Lods[L].ScreenSize;
		FMeshDescription* MD = Mesh->CreateMeshDescription(L);
		WritePatchLOD(*MD, Blades, Lods[L].Stride, Lods[L].Segs, HalfWidth * Lods[L].WidthMul);
		Mesh->CommitMeshDescription(L);
	}

	FMeshNaniteSettings Nanite = Mesh->GetNaniteSettings();
	Nanite.bEnabled = bNanite;
	Nanite.ShapePreservation = ENaniteShapePreservation::Voxelize;
	Mesh->SetNaniteSettings(Nanite);
	Mesh->Build(false);
	Mesh->PostEditChange();
	Mesh->MarkPackageDirty();
	if (bNew)
	{
		FAssetRegistryModule::AssetCreated(Mesh);
	}
	UE_LOG(LogVoyagerEditor, Display, TEXT("Grass patch %s: %d blades, %d LODs, Nanite %d"), *AssetPath, Blades.Num(), Lods.Num(), bNanite ? 1 : 0);
	return Mesh;
}

void UVoyagerGrassBuilder::BuildLandscapeNanite()
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (ULandscapeSubsystem* Subsystem = World ? World->GetSubsystem<ULandscapeSubsystem>() : nullptr)
	{
		Subsystem->BuildNanite(UE::Landscape::EBuildFlags::WriteFinalLog | UE::Landscape::EBuildFlags::ForceRebuild);
	}
}
