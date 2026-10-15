using System;
using System.IO;
using System.Collections.Generic;
using UnityEngine;

[Serializable] public class SceneData { public int format, fps, end_frame; public string units, source_sha256; public MaterialData[] materials; public GroupData[] groups; }
[Serializable] public class MaterialData { public string name; public float[] color; }
[Serializable] public class PartData { public int material, offset, count; }
[Serializable] public class PoseData { public float[] p,q,s; }
[Serializable] public class GroupData { public string name, actor_type; public PartData[] parts; public PoseData[] samples; }

public class BridgeScene : MonoBehaviour {
    [NonSerialized] public SceneData data;
    [NonSerialized] public List<Transform> groups = new List<Transform>();
    public float frame = 1;
    public bool playing = true;
    public string message = "Source animation running";
    public Camera view;
    public Light sun;
    float daylight = 0.8f, yaw = -35, pitch = 25, distance = 220;
    Vector3 target = new Vector3(0,15,0);
    CharacterController walker;
    bool walking;
    bool stopBeforeLowering;
    float verticalSpeed;
    Material[] sceneMaterials;
    public static bool CanOpen(bool carOnDeck, bool personOnDeck) { return !carOnDeck && !personOnDeck; }
    public static bool CanClose(bool vesselInChannel) { return !vesselInChannel; }
    static Vector3 V(float[] a) { return new Vector3(a[0],a[1],a[2]); }
    public void Load() {
        Application.runInBackground=true;
        data = JsonUtility.FromJson<SceneData>(File.ReadAllText(Path.Combine(Application.streamingAssetsPath,"scene.json")));
        var mats = new Material[data.materials.Length];
        sceneMaterials=mats;
        var standard=Resources.Load<Material>("BridgeStandard");
        if(!Shader.Find("Standard"))throw new Exception("Standard shader missing from Player");
        for(int i=0;i<mats.Length;i++) { var d=data.materials[i]; mats[i]=standard?new Material(standard):new Material(Shader.Find("Standard")); mats[i].name=d.name; mats[i].color=new Color(d.color[0],d.color[1],d.color[2],1); }
        using(var reader = new BinaryReader(File.OpenRead(Path.Combine(Application.streamingAssetsPath,"scene.bin")))) {
            foreach(var g in data.groups) {
                var root=new GameObject(g.name); root.transform.SetParent(transform); groups.Add(root.transform);
                foreach(var part in g.parts) {
                    reader.BaseStream.Position=part.offset;
                    var vertices=new Vector3[part.count]; var triangles=new int[part.count];
                    for(int i=0;i<part.count;i++) { vertices[i]=new Vector3(reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle()); triangles[i]=i; }
                    var mesh=new Mesh(); mesh.name=g.name; if(part.count>65535) mesh.indexFormat=UnityEngine.Rendering.IndexFormat.UInt32; mesh.vertices=vertices; mesh.triangles=triangles; mesh.RecalculateNormals(); mesh.RecalculateBounds();
                    var child=new GameObject("Geometry"); child.transform.SetParent(root.transform,false); child.AddComponent<MeshFilter>().sharedMesh=mesh; child.AddComponent<MeshRenderer>().sharedMaterial=mats[part.material];
                    string materialName=mats[part.material].name.ToLowerInvariant();
                    if((g.actor_type=="static" || g.actor_type=="hinge" || g.actor_type=="barrier") && mesh.bounds.size.magnitude<500 && !materialName.Contains("water") && !materialName.Contains("foam") && !materialName.Contains("wake")) child.AddComponent<MeshCollider>().sharedMesh=mesh;
                }
            }
        }
        var cam = new GameObject("Interactive camera"); view=cam.AddComponent<Camera>(); view.nearClipPlane=.15f; view.farClipPlane=1800;
        var light=new GameObject("Daylight"); sun=light.AddComponent<Light>(); sun.type=LightType.Directional; sun.transform.rotation=Quaternion.Euler(40,-30,0); sun.shadows=LightShadows.Soft;
        RenderSettings.ambientMode=UnityEngine.Rendering.AmbientMode.Flat;
        if(RenderSettings.skybox)RenderSettings.skybox=new Material(RenderSettings.skybox);
        var player=new GameObject("Walking visitor"); walker=player.AddComponent<CharacterController>(); walker.height=1.8f; walker.radius=.32f; walker.center=new Vector3(0,.9f,0); player.transform.position=new Vector3(70,12,7);
        ApplyFrame(); UpdateCamera();
    }
    void Start() { if(data==null) Load(); if(Array.IndexOf(Environment.GetCommandLineArgs(),"-verifyRuntime")>=0) StartCoroutine(VerifyRuntime()); }
    System.Collections.IEnumerator VerifyRuntime() {
        try {RunSceneChecks();} catch(Exception e) {Debug.LogException(e);Application.Quit(4);yield break;}
        playing=false;frame=1;ApplyFrame();
        walker.enabled=false;walker.transform.position=new Vector3(70,10.5f,6.7f);walker.enabled=true;
        yield return new WaitForFixedUpdate();walker.Move(Vector3.down*.3f);
        Vector3 beforeRail=walker.transform.position;walker.Move(Vector3.forward*3);
        if(walker.transform.position.z>7.6f || walker.transform.position.y<9.9f) {Debug.LogError("Runtime visitor passed through sidewalk railing or deck");Application.Quit(5);yield break;}
        walker.enabled=false;walker.transform.position=beforeRail;walker.enabled=true;
        playing=false; frame=720; ApplyFrame(); yield return null; yield return new WaitForEndOfFrame();
        RequestClose(); if(!message.StartsWith("Rejected")) {Debug.LogError("Runtime vessel safety failed");Application.Quit(2);yield break;}
        frame=1;ApplyFrame(); RequestOpen(); if(!message.StartsWith("Rejected")) {Debug.LogError("Runtime traffic safety failed");Application.Quit(3);yield break;}
        frame=720;ApplyFrame();playing=false;
        yield return new WaitForEndOfFrame();
        try {
            walking=false;daylight=.8f;ApplyLighting();UpdateCamera();CaptureView("runtime.png");
            Vector3 overview=view.transform.position;distance=130;pitch=12;yaw=0;UpdateCamera();
            if(Vector3.Distance(overview,view.transform.position)<10)throw new Exception("River camera preset failed");CaptureView("runtime-river.png");
            daylight=.05f;ApplyLighting();if(sun.intensity>.3f)throw new Exception("Daylight control failed");CaptureView("runtime-evening.png");
            frame=1;ApplyFrame();walker.enabled=false;walker.transform.position=new Vector3(70,10.5f,6.7f);walker.enabled=true;
            walking=true;pitch=0;yaw=-90;daylight=.8f;ApplyLighting();UpdateCamera();
            if(Vector3.Distance(view.transform.position,walker.transform.position+Vector3.up*1.65f)>.01f)throw new Exception("Walking camera eye height failed");CaptureView("runtime-walk.png");
        } catch(Exception e) {Debug.LogException(e);Application.Quit(6);yield break;}
        File.WriteAllText(Path.Combine(Application.dataPath,"../runtime-verification.json"),"{\"passed\":true,\"source_sha256\":\""+data.source_sha256+"\",\"renderer\":\""+SystemInfo.graphicsDeviceName+"\",\"checks\":[\"full scene load\",\"traffic open rejection\",\"clear deck open acceptance\",\"vessel close rejection\",\"clear channel close acceptance\",\"visitor blocks lifting and lowering\",\"sidewalk support\",\"river lacks walk support\",\"vehicle blocks walking\",\"approaching car pauses for visitor\",\"CharacterController deck and railing collision\",\"river camera preset\",\"daylight control\",\"walking camera eye height\",\"four real camera renders with pixel validation\"]}");
        Application.Quit(0);
    }
    void CaptureView(string name) {
        var targetTexture=new RenderTexture(1280,720,24,RenderTextureFormat.ARGB32);var previousTarget=view.targetTexture;var previousActive=RenderTexture.active;
        var pixels=new Texture2D(1280,720,TextureFormat.RGB24,false);
        try {
            view.targetTexture=targetTexture;view.Render();RenderTexture.active=targetTexture;
            pixels.ReadPixels(new Rect(0,0,1280,720),0,0);pixels.Apply();
            int nonBlack=0,pink=0;foreach(var c in pixels.GetPixels32()) {if(c.r+c.g+c.b>20)nonBlack++;if(c.r>200&&c.g<40&&c.b>200)pink++;}
            if(nonBlack<1280*720/10 || pink>1280*720/100)throw new Exception("Invalid camera image: black or missing shader "+name);
            File.WriteAllBytes(Path.Combine(Application.dataPath,"../"+name),pixels.EncodeToPNG());
        } finally {view.targetTexture=previousTarget;RenderTexture.active=previousActive;targetTexture.Release();Destroy(targetTexture);Destroy(pixels);}
    }
    public void ApplyFrame() {
        for(int i=0;i<groups.Count;i++) { var s=data.groups[i].samples; if(s.Length==0) continue; int a=Mathf.Clamp((int)frame-1,0,s.Length-1), b=Mathf.Min(a+1,s.Length-1); float t=frame-Mathf.Floor(frame); var p=s[a]; var n=s[b];
            // Portal recycling is a discontinuity, never an interpolated drive
            // through the city. Visibility changes are discrete for the same reason.
            if(Vector3.Distance(V(p.p),V(n.p))>100 || (V(p.s)-V(n.s)).sqrMagnitude>1) t=0;
            groups[i].position=Vector3.Lerp(V(p.p),V(n.p),t); groups[i].rotation=Quaternion.Slerp(new Quaternion(p.q[0],p.q[1],p.q[2],p.q[3]),new Quaternion(n.q[0],n.q[1],n.q[2],n.q[3]),t); groups[i].localScale=Vector3.Lerp(V(p.s),V(n.s),t); }
        Physics.SyncTransforms();
        UpdateSignals();
    }
    void UpdateSignals() {
        float reference=frame*1440f/data.end_frame;bool green=reference<193 || reference>=1105;
        for(int i=0;i<sceneMaterials.Length;i++) {string name=data.materials[i].name;if(!name.StartsWith("Signal "))continue;bool on=(name.EndsWith("green")&&green)||(name.EndsWith("red")&&!green)||(name.EndsWith("amber")&&reference>=193&&reference<=216);var c=data.materials[i].color;sceneMaterials[i].color=new Color(c[0],c[1],c[2])*(on?1:.035f);}
    }
    public bool Occupied(string kind, float halfX, float halfZ) {
        for(int i=0;i<groups.Count;i++) { if(!data.groups[i].actor_type.Contains(kind)) continue; foreach(var r in groups[i].GetComponentsInChildren<Renderer>()) { var b=r.bounds; if(b.min.x<halfX && b.max.x>-halfX && b.min.z<halfZ && b.max.z>-halfZ) return true; } } return false;
    }
    public void RequestOpen() {
        bool person=VisitorOnDeck();
        if(!CanOpen(Occupied("vehicle",42,7),person)) {message="Rejected: deck occupied";return;}
        // Run the original warning/evacuation/barrier/open sequence. It keeps traffic,
        // vessels and decks on the same baked clock, including approach clearance.
        if(frame>432) {message="Opening already scheduled / bridge raised";return;}
        stopBeforeLowering=true; playing=true; message="Opening requested: clearing traffic and lowering barriers";
    }
    public void RequestClose() {
        if(!CanClose(Occupied("sailboat",12,20) || Occupied("launch",12,20))) {message="Rejected: vessel in channel";return;}
        if(frame<864) {message="Wait for scheduled vessel passage before closing";return;}
        stopBeforeLowering=false; playing=true; message="Closing after vessel clearance";
    }
    public bool VisitorOnDeck() {return walking && Mathf.Abs(walker.transform.position.x)<42 && Mathf.Abs(walker.transform.position.z)<10;}
    public bool VehicleBlocks(Vector3 feet) {
        foreach(int i in VehicleIndices()) {var b=ActorBounds(i);if(b.size.sqrMagnitude<.01f)continue;b.Expand(.8f);if(b.Contains(feet+Vector3.up))return true;} return false;
    }
    Bounds ActorBounds(int index) {var renderers=groups[index].GetComponentsInChildren<Renderer>();if(renderers.Length==0)return new Bounds(groups[index].position,Vector3.zero);var b=renderers[0].bounds;for(int i=1;i<renderers.Length;i++)b.Encapsulate(renderers[i].bounds);return b;}
    IEnumerable<int> VehicleIndices() {for(int i=0;i<groups.Count;i++)if(data.groups[i].actor_type=="vehicle")yield return i;}
    public bool HasWalkSurface(Vector3 feet) {
        RaycastHit hit;
        return Physics.Raycast(feet+Vector3.up*.6f,Vector3.down,out hit,1.3f) && hit.normal.y>.65f;
    }
    public void RunSceneChecks() {
        bool savedWalking=walking; Vector3 savedPosition=walker.transform.position; float savedFrame=frame;
        try {
            walking=false; frame=1;ApplyFrame();RequestOpen();
            if(!message.StartsWith("Rejected"))throw new Exception("Occupied deck must reject open request");
            frame=720;ApplyFrame();RequestClose();
            if(!message.StartsWith("Rejected"))throw new Exception("Vessel in channel must reject close request");
            frame=432;ApplyFrame();
            if(Occupied("vehicle",42,7))throw new Exception("Source traffic not clear at lifting boundary");
            RequestOpen();if(!playing)throw new Exception("Safe opening request did not resume");
            walker.enabled=false;walker.transform.position=new Vector3(0,10.5f,6.7f);walker.enabled=true;walking=true;
            if(Advance(1f))throw new Exception("Automatic lifting failed to stop for visitor");
            frame=900;ApplyFrame();if(Advance(.1f))throw new Exception("Lowering failed to stop for visitor");
            walking=false;frame=864;ApplyFrame();RequestClose();
            if(!playing || message.StartsWith("Rejected"))throw new Exception("Cleared channel must allow close");
            frame=1;ApplyFrame();Physics.SyncTransforms();
            if(!HasWalkSurface(new Vector3(70,10.5f,6.7f)))throw new Exception("Missing sidewalk walk collider");
            if(HasWalkSurface(new Vector3(0,3,45)))throw new Exception("River unexpectedly supports walking");
            bool vehicleFound=false;
            foreach(int i in VehicleIndices()) foreach(var r in groups[i].GetComponentsInChildren<Renderer>()) if(r.bounds.size.sqrMagnitude>.01f) {if(!VehicleBlocks(r.bounds.center-Vector3.up))throw new Exception("Vehicle walking collision missing");vehicleFound=true;break;}
            if(!vehicleFound)throw new Exception("No rendered traffic for collision test");
            // Put a stationary test visitor just outside the current vehicle hull
            // but inside its next-frame swept approach. Playback must roll back.
            int first=-1;foreach(int i in VehicleIndices()) {first=i;break;}
            var oldBounds=ActorBounds(first);frame=2;ApplyFrame();var future=ActorBounds(first);
            float direction=Mathf.Sign(future.center.x-oldBounds.center.x);
            Vector3 visitor=future.center-Vector3.up;visitor.x=direction>0?future.max.x+.39f:future.min.x-.39f;
            frame=1;ApplyFrame();walker.enabled=false;walker.transform.position=visitor;walker.enabled=true;walking=true;
            if(VehicleBlocks(visitor))throw new Exception("Approach fixture already overlaps current car");
            if(Advance(1f/data.fps))throw new Exception("Approaching car failed to pause for stationary visitor");
            walking=false;frame=1;ApplyFrame();stopBeforeLowering=false;
            if(!Advance(data.end_frame/(float)data.fps) || frame<data.end_frame)throw new Exception("Complete synchronized cycle failed safety checks");
        } finally {walking=savedWalking;walker.enabled=false;walker.transform.position=savedPosition;walker.enabled=true;frame=savedFrame;ApplyFrame();playing=false;stopBeforeLowering=false;}
    }
    public bool Advance(float seconds) {
        float goal=Mathf.Min(data.end_frame,frame+Mathf.Max(0,seconds)*data.fps);
        while(frame<goal) {
            float old=frame, next=Mathf.Min(goal,Mathf.Floor(frame)+1);
            float reference=next*1440f/data.end_frame;
            bool deckMoving=(reference>432 && reference<624)||(reference>864 && reference<1056);
            if(deckMoving && (VisitorOnDeck() || Occupied("vehicle",42,7))) {message="Paused: movable deck occupied";playing=false;return false;}
            if(reference>864 && reference<1056 && (Occupied("sailboat",12,20)||Occupied("launch",12,20))) {message="Paused: vessel in channel";playing=false;return false;}
            frame=next;ApplyFrame();
            if(walking && VehicleBlocks(walker.transform.position)) {frame=old;ApplyFrame();playing=false;message="Paused: vehicle approaching visitor";return false;}
            if(stopBeforeLowering && reference>=864) {playing=false;message="Bridge raised; vessel clear. Press Close to lower.";return true;}
        }
        return true;
    }
    void Update() {
        if(data==null) return;
        if(playing) Advance(Time.deltaTime);
        if(Input.GetKeyDown(KeyCode.Escape)) {walking=false;Cursor.lockState=CursorLockMode.None;}
        if(walking) {
            yaw+=Input.GetAxis("Mouse X")*2; pitch=Mathf.Clamp(pitch-Input.GetAxis("Mouse Y")*2,-75,75);
            var move=Quaternion.Euler(0,yaw,0)*new Vector3(Input.GetAxis("Horizontal"),0,Input.GetAxis("Vertical"));
            if(walker.isGrounded) verticalSpeed=-2; else verticalSpeed-=9.81f*Time.deltaTime;
            // Vehicle hulls block the visitor without attaching costly animated mesh colliders.
            Vector3 candidate=walker.transform.position+move*4*Time.deltaTime; bool blocked=VehicleBlocks(candidate) || (walker.isGrounded && !HasWalkSurface(candidate));
            walker.Move(((blocked?Vector3.zero:move*4)+Vector3.up*verticalSpeed)*Time.deltaTime);
            if(walker.transform.position.y < -5) walker.transform.position=new Vector3(70,12,7);
        } else { if(Input.GetMouseButton(1)) {yaw+=Input.GetAxis("Mouse X")*3;pitch=Mathf.Clamp(pitch-Input.GetAxis("Mouse Y")*3,5,85);} distance=Mathf.Clamp(distance-Input.mouseScrollDelta.y*10,35,700); }
        ApplyLighting(); UpdateCamera();
    }
    void ApplyLighting() {sun.intensity=Mathf.Lerp(.12f,1.2f,daylight);sun.color=Color.Lerp(new Color(.55f,.65f,1),Color.white,daylight);sun.transform.rotation=Quaternion.Euler(Mathf.Lerp(5,40,daylight),-30,0); RenderSettings.ambientLight=Color.Lerp(new Color(.06f,.08f,.15f),new Color(.55f,.6f,.7f),daylight);if(RenderSettings.skybox&&RenderSettings.skybox.HasProperty("_Exposure"))RenderSettings.skybox.SetFloat("_Exposure",Mathf.Lerp(.02f,1,daylight));}
    void UpdateCamera() { if(walking) {view.transform.position=walker.transform.position+Vector3.up*1.65f;view.transform.rotation=Quaternion.Euler(pitch,yaw,0);} else {view.transform.position=target+Quaternion.Euler(pitch,yaw,0)*new Vector3(0,0,-distance);view.transform.LookAt(target);} }
    void BeginWalk() {if(VehicleBlocks(walker.transform.position)||!HasWalkSurface(walker.transform.position)) {walker.enabled=false;walker.transform.position=new Vector3(70,10.5f,6.7f);walker.enabled=true;}walking=true;pitch=0;yaw=-90;Cursor.lockState=CursorLockMode.Locked;}
    void OnGUI() {
        GUI.Box(new Rect(10,10,430,235),"Tower Bridge — interactive Unity prototype");
        if(GUI.Button(new Rect(20,40,95,28),playing?"Pause":"Play")) playing=!playing;
        if(GUI.Button(new Rect(120,40,95,28),"Open")) RequestOpen();
        if(GUI.Button(new Rect(220,40,95,28),"Close")) RequestClose();
        if(GUI.Button(new Rect(320,40,105,28),"Restart")) {walking=false;stopBeforeLowering=false;Cursor.lockState=CursorLockMode.None;frame=1;playing=true;ApplyFrame();}
        GUI.Label(new Rect(20,75,400,25),message);
        GUI.Label(new Rect(20,100,400,25),"Time "+(frame/data.fps).ToString("F1")+"s   Road signal: "+(frame<193 || frame>=1105?"GREEN":"RED"));
        GUI.Label(new Rect(20,125,130,25),"Daylight"); daylight=GUI.HorizontalSlider(new Rect(125,135,290,20),daylight,0,1);
        if(GUI.Button(new Rect(20,160,95,28),"Overview")) {walking=false;distance=220;pitch=25;yaw=-35;target=new Vector3(0,15,0);}
        if(GUI.Button(new Rect(120,160,95,28),"River")) {walking=false;distance=130;pitch=12;yaw=0;target=new Vector3(0,15,0);}
        if(GUI.Button(new Rect(220,160,95,28),"Walk")) BeginWalk();
        GUI.Label(new Rect(20,195,405,40),"Orbit: right drag / wheel. Walk: WASD + mouse; Esc exits.\nBridge follows synchronized source choreography.");
    }
}
