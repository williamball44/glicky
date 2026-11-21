#include "VoyagerTerra.h"

namespace
{
	/** Unity's Mathf.PerlinNoise is ~[0,1]; FMath::PerlinNoise2D is ~[-1,1]. */
	FORCEINLINE float Perlin01(float X, float Y)
	{
		return 0.5f + 0.5f * FMath::PerlinNoise2D(FVector2D(X, Y));
	}
}

float UVoyagerTerra::Smooth01(float A, float B, float X)
{
	const float T = FMath::Clamp((X - A) / (B - A), 0.f, 1.f);
	return T * T * (3.f - 2.f * T);
}

float UVoyagerTerra::Fbm(float X, float Y, int32 Octaves)
{
	float Sum = 0.f, Amp = 0.5f, Norm = 0.f;
	for (int32 I = 0; I < Octaves; ++I)
	{
		Sum += Amp * Perlin01(X + 1000.3f + I * 31.7f, Y + 1000.7f + I * 17.3f);
		Norm += Amp;
		Amp *= 0.5f;
		X *= 2.03f;
		Y *= 2.03f;
	}
	return Sum / Norm;
}

float UVoyagerTerra::Ridged(float X, float Y, int32 Octaves)
{
	float Sum = 0.f, Amp = 0.5f, Norm = 0.f;
	for (int32 I = 0; I < Octaves; ++I)
	{
		const float N = 1.f - FMath::Abs(Perlin01(X + 500.1f + I * 13.1f, Y + 500.9f + I * 7.7f) * 2.f - 1.f);
		Sum += Amp * N * N;
		Norm += Amp;
		Amp *= 0.5f;
		X *= 2.1f;
		Y *= 2.1f;
	}
	return Sum / Norm;
}

float UVoyagerTerra::RiverXM(float Z)
{
	return 110.f + 55.f * FMath::Sin(Z * 0.0045f) + 18.f * FMath::Sin(Z * 0.013f + 1.3f);
}

float UVoyagerTerra::HeightM(float X, float Z)
{
	const float R = FMath::Sqrt(X * X + Z * Z);
	const float Rolling = (Fbm(X * 0.004f, Z * 0.004f, 4) - 0.5f) * 9.f + (Fbm(X * 0.03f, Z * 0.03f, 2) - 0.5f) * 1.2f;
	const float HillMask = Smooth01(200.f, 850.f, R);
	const float Hills = HillMask * (50.f + 230.f * Fbm(X * 0.0015f + 7.f, Z * 0.0015f + 3.f, 5));
	const float Ridges = HillMask * Ridged(X * 0.003f, Z * 0.003f, 4) * 90.f;
	const float DRiver = FMath::Abs(X - RiverXM(Z));
	const float Valley = Smooth01(30.f, 280.f, DRiver);
	const float Rim = Smooth01(1150.f, 1480.f, R) * 260.f;
	float H = FieldHeightM + Rolling * (0.35f + HillMask * 1.5f) + (Hills + Ridges) * Valley + Rim * FMath::Max(Valley, 0.4f);

	// Small bumps and hollows (about 9 m across, +-0.35 m) so the meadow isn't a flat sheet.
	H += (Fbm(X * 0.11f + 3.f, Z * 0.11f - 5.f, 3) - 0.5f) * 0.7f;

	// River channel
	const float Channel = 1.f - Smooth01(8.f, 26.f, DRiver);
	const float Bed = 13.5f + Fbm(X * 0.05f, Z * 0.05f, 2) * 1.5f;
	H = FMath::Lerp(H, Bed, Channel);

	// Gentle banks
	const float Bank = 1.f - Smooth01(26.f, 45.f, DRiver);
	H = FMath::Lerp(H, FMath::Min(H, FieldHeightM - 0.5f), Bank * (1.f - Channel));

	// Flat pads for the house and the parked ship (Unity frame: x = world Y, z = world X).
	const FVector2D House = HouseXY() / 100.0;
	const FVector2D Ship = ShipXY() / 100.0;
	const float DH = FVector2D::Distance(FVector2D(X, Z), FVector2D(House.Y, House.X));
	H = FMath::Lerp(H, FieldHeightM + 0.25f, 1.f - Smooth01(9.f, 22.f, DH));
	const float DS = FVector2D::Distance(FVector2D(X, Z), FVector2D(Ship.Y, Ship.X));
	H = FMath::Lerp(H, FieldHeightM + 0.1f, 1.f - Smooth01(8.f, 20.f, DS));
	return H;
}

float UVoyagerTerra::TerrainHeight(FVector2D WorldXY)
{
	return HeightM(WorldXY.Y / 100.f, WorldXY.X / 100.f) * 100.f;
}

float UVoyagerTerra::RiverY(float WorldX)
{
	return RiverXM(WorldX / 100.f) * 100.f;
}
