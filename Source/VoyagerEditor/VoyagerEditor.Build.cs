using UnrealBuildTool;

public class VoyagerEditor : ModuleRules
{
	public VoyagerEditor(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });

		PrivateDependencyModuleNames.AddRange(new string[] { "UnrealEd", "Landscape", "Voyager" });
	}
}
