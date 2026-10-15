using System;
using System.IO;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public static class BridgeBuild {
    [MenuItem("Tower Bridge/Verify export and build Windows")]
    public static void VerifyAndBuild() {
        var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
        var app=new GameObject("Tower Bridge application").AddComponent<BridgeScene>(); app.Load();
        string sourceHash=app.data.source_sha256;
        app.RunSceneChecks();
        if(app.data.units!="metres" || app.data.format!=1) throw new Exception("Invalid coordinate/units contract");
        if(app.groups.Count<5) throw new Exception("Missing scene geometry / actors");
        int hinges=0, vehicles=0; float maxHeight=0;
        foreach(var g in app.data.groups) {if(g.name.Contains("bascule hinge")) hinges++; if(g.actor_type=="vehicle") vehicles++;}
        if(hinges!=2 || vehicles<2) throw new Exception("Missing articulated decks or traffic");
        if(BridgeScene.CanOpen(true,false)||BridgeScene.CanOpen(false,true)||!BridgeScene.CanOpen(false,false)||BridgeScene.CanClose(true)||!BridgeScene.CanClose(false)) throw new Exception("Safety gate truth table failed");
        app.frame=1; app.ApplyFrame();
        foreach(var g in app.groups) foreach(var r in g.GetComponentsInChildren<Renderer>()) maxHeight=Mathf.Max(maxHeight,r.bounds.max.y);
        if(maxHeight<40 || maxHeight>500) throw new Exception("Metre scale / vertical axis sanity failed: "+maxHeight);
        app.RequestOpen(); // Initial traffic must reject an unsafe immediate command.
        app.frame=720; app.ApplyFrame(); app.RequestClose();
        if(!app.message.StartsWith("Rejected")) throw new Exception("Vessel channel close gate not exercised");
        app.frame=1; app.ApplyFrame(); app.playing=true;
        Directory.CreateDirectory("Assets/Scenes"); EditorSceneManager.SaveScene(scene,"Assets/Scenes/TowerBridge.unity");
        // Runtime loads generated geometry once; do not serialize generated meshes/materials.
        UnityEngine.Object.DestroyImmediate(app.gameObject);
        UnityEngine.Object.DestroyImmediate(UnityEngine.Object.FindAnyObjectByType<Camera>().gameObject);
        UnityEngine.Object.DestroyImmediate(UnityEngine.Object.FindAnyObjectByType<Light>().gameObject);
        var visitor=GameObject.Find("Walking visitor"); if(visitor) UnityEngine.Object.DestroyImmediate(visitor);
        new GameObject("Tower Bridge application").AddComponent<BridgeScene>();
        EditorSceneManager.SaveScene(scene,"Assets/Scenes/TowerBridge.unity");
        PlayerSettings.productName="Tower Bridge Interactive"; PlayerSettings.companyName="Tower Bridge Project";
        // Mono without stripping also avoids Unity Linker's comma-separated
        // assembly-list parsing bug when the project lives in a path with commas.
        PlayerSettings.SetScriptingBackend(UnityEditor.Build.NamedBuildTarget.Standalone,ScriptingImplementation.Mono2x);
        PlayerSettings.SetManagedStrippingLevel(UnityEditor.Build.NamedBuildTarget.Standalone,ManagedStrippingLevel.Disabled);
        PlayerSettings.defaultScreenWidth=1280; PlayerSettings.defaultScreenHeight=720; PlayerSettings.fullScreenMode=FullScreenMode.Windowed;
        // A Resources material keeps the Standard shader in the player even though
        // geometry/material instances are generated from StreamingAssets at run time.
        Directory.CreateDirectory("Assets/Resources");
        if(!AssetDatabase.LoadAssetAtPath<Material>("Assets/Resources/BridgeStandard.mat")) AssetDatabase.CreateAsset(new Material(Shader.Find("Standard")),"Assets/Resources/BridgeStandard.mat");
        AssetDatabase.SaveAssets();
        Directory.CreateDirectory("Build");
        var report=BuildPipeline.BuildPlayer(new[]{"Assets/Scenes/TowerBridge.unity"},"Build/TowerBridge.exe",BuildTarget.StandaloneWindows64,BuildOptions.None);
        if(report.summary.result!=UnityEditor.Build.Reporting.BuildResult.Succeeded) throw new Exception("Windows build failed");
        File.WriteAllText("Build/verification.json","{\"passed\":true,\"source_sha256\":\""+sourceHash+"\",\"full_cycle_passed\":true,\"hinges\":"+hinges+",\"vehicles\":"+vehicles+",\"max_height_m\":"+maxHeight.ToString(System.Globalization.CultureInfo.InvariantCulture)+"}");
        Debug.Log("UNITY_VERIFICATION_PASSED");
    }
}
