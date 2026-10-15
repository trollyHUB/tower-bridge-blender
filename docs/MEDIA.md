# Media extensions

E02 is generated independently from the final silent MP4. The silent source hash is checked before and after encoding. Run:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --python tools/create_presentation.py -- --input Tower_Bridge/Tower_Bridge_Animation.mp4
```

Output: `Tower_Bridge/extensions/presentation/Tower_Bridge_Titled_Sound.mp4`. It contains Russian phase captions and original deterministic synthesized ambience: seeded river/wind noise, low distant traffic and two partial bell tones. This is an artistic soundtrack, not a recording or historical acoustic reconstruction. PCM source: `assets/audio/tower_bridge_original.wav`. Captions cover the full reference timeline and scale to the input duration. Blender loads Arial from Windows for Cyrillic text. Manifest records exact input/output/tool/audio SHA-256 and timing.

E03 is a separate ten-second, 240-frame, 24-fps, 1920×1080 daytime scene and video:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --python tools/create_day_loop.py -- --render
```

Omit `--render` to prepare the scene and seam report without GPU use. Output directory: `Tower_Bridge/extensions/day_loop/`. The original scene is opened read-only, frozen at daytime frame one, and saved as a separate derived blend. The Water camera stays constant. Nonperiodic vehicles, passing vessels and their transient wakes are hidden; architectural and bank details remain. Water/cloth shape keys cycle with smooth integer-harmonic sine drivers. Moored skiffs have periodic buoyancy motion. This intentionally uses a calm daylight composition rather than attempting to loop the main bridge-opening narrative.

The endpoint is frame 241, which is excluded from the encoded 1–240 sequence. Every driver has a 240-frame period with matching values and derivatives. The manifest checks numerical first/endpoint visible object transforms and all shape-key values, plus analytical velocity continuity. Last encoded frame 240 should differ naturally from frame 1 by one motion step; duplicating frame 1 at frame 240 would pause the seam. Main source hash is rechecked after preparation/rendering. Scene and video hashes are recorded separately.

Tests: `python -m unittest discover -s tests -p test_media_extensions.py` verifies deterministic, nonsilent PCM, caption coverage, and periodic values/velocities.

After encoding, verify every frame and stream metadata:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --python tools/verify_media_extensions.py -- --video Tower_Bridge/extensions/day_loop/Tower_Bridge_Day_Loop.mp4
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --python tools/verify_media_extensions.py -- --video Tower_Bridge/extensions/presentation/Tower_Bridge_Titled_Sound.mp4 --require-audio
```

Decoded QA frames and loop source frames remain under `research/`, outside release extensions. The loop pixel seam check compares final-to-first differences with adjacent frame differences and rejects an identical duplicated terminal image. Visible scene transform and shape-key velocity continuity are also measured numerically across the seam.

The loop MP4 uses H.264 GOP size 1 (all I frames). This keeps compression behaviour consistent at the wrap boundary. `--encode-only` rebuilds the derived scene and re-encodes the existing source-hash frame cache without GPU rendering. `python tools/check_media_pixels.py` compares all decoded loop frames with source images, checks the actual encoded seam against internal neighbours, and writes `pixel_validation.json` plus the decoded contact sheet.

Caption bus-stop timing is derived from `config/scene.json` traffic speed using `traffic.bus_stop_times`, with exactly the same rounded arrival/departure bounds as the bus camera. The bus label masks any underlying phase interval; shared boundaries preserve full coverage across supported duration/FPS changes. Disabling traffic or the bus stop removes that label. For an arbitrary external `--input` video, the tool assumes it portrays this project's configured narrative, scaled to its actual frame count; unrelated videos need a custom caption schedule.

For isolated test jobs, `--audio-output research/path.wav` keeps the canonical original WAV intact. Caption font size scales with actual video height (44 px at1080p, minimum8 px). Synthesized warning bell times scale with video duration:8/60,10/60 and14/60 of the clip. A real48-frame320×180 smoke encode and full decode is retained under `research/media_smoke/`; AAC48kHz stereo metadata and Russian title layout were checked, including a separate1080p longest-caption proof.

Final presentation QA also decodes the *actual MP4 AAC stream*: `blender -b --python tools/decode_presentation_audio.py`. Blender/Audaspace loads the MP4 as the sole sound strip and mixes it to48kHz stereo PCM16 under `research/audio_decode/`. `audio_decode_validation.json` checks duration within50ms AAC padding tolerance, nonzero RMS, no clipping, stronger warning-bell window and660/991Hz peaks. This is DSP verification rather than expert listening.

`blender -b --python tools/inspect_presentation.py` decodes each actual encoded caption interval at640×360 and frame378 at native1080p. `python tools/create_presentation_contacts.py` assembles the phase review. The release presentation folder includes `Title_Frame.png`, `Contact_Sheet.jpg`, full-video decode report, actual-audio decode report and visual-review report. The loop release folder also includes a compact decoded `Contact_Sheet.jpg`.
