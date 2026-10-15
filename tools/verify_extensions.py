"""Fail closed on stale/missing extension outputs before a complete release."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scene_components.render_manifest import sha, png_size
from scene_components.settings import load_config, frame_count


def read(path, passed=True):
    result = json.loads(path.read_text(encoding='utf-8-sig'))
    if passed:
        assert result.get('passed') is True, ('Report did not pass', str(path))
    return result


def verify(root=ROOT):
    out = root/'Tower_Bridge'
    cfg = load_config(root/'config/scene.json')
    source = sha(out/'Tower_Bridge.blend')
    frames = frame_count(cfg)
    checks = []
    scene = read(out/'validation.json')
    assert scene['scene_sha256'] == source and scene['frames_checked'] == frames
    assert 'bus_stop_doors' in scene['traffic']['checks']
    assert cfg['traffic']['bus_stop'] is True
    checks.append('E01_actual_scene_all_frames_doors_traffic')
    presentation = out/'extensions/presentation'
    film = presentation/'Tower_Bridge_Titled_Sound.mp4'
    media = read(presentation/'manifest.json')
    decode = read(presentation/'Tower_Bridge_Titled_Sound_validation.json')
    assert media['source_sha256'] == sha(out/'Tower_Bridge_Animation.mp4')
    assert media['output_sha256'] == decode['video_sha256'] == sha(film)
    assert media['audio_sha256'] == sha(root/'assets/audio/tower_bridge_original.wav')
    assert media['tool_sha256'] == sha(root/'tools/create_presentation.py')
    assert media['caption_config']['config_sha256'] == sha(root/'config/scene.json')
    assert decode['decoded_count'] == frames and decode['size'] == [1920,1080]
    assert decode['audio_metadata']['sample_rate'] == 48000
    from tools.create_presentation import caption_frames
    assert media['caption_frames'] == [list(row) for row in caption_frames(frames, cfg)]
    audio = read(presentation/'audio_decode_validation.json')
    assert audio['source_scene_sha256'] == source and audio['video_sha256'] == sha(film)
    assert audio['sample_rate'] == 48000 and audio['channels'] == 2
    assert abs(audio['seconds'] - frames/cfg['fps']) < .05
    assert 0 < audio['rms'] and audio['peak'] < 1
    review = read(presentation/'visual_review.json')
    assert review['source_scene_sha256'] == source and review['video_sha256'] == sha(film)
    assert review['title_frame_sha256'] == sha(presentation/'Title_Frame.png')
    assert review['contact_sheet_sha256'] == sha(presentation/'Contact_Sheet.jpg')
    checks.append('E02_source_sound_captions_hashes_and_full_decode')
    loop = out/'extensions/day_loop'
    manifest = read(loop/'manifest.json')
    assert manifest['source_sha256'] == source
    assert manifest['derived_sha256'] == sha(loop/'Tower_Bridge_Day_Loop.blend')
    assert manifest['tool_sha256'] == sha(root/'tools/create_day_loop.py')
    assert manifest['frames'] == 240 and manifest['fps'] == 24
    assert manifest['endpoint_state_max_error'] < 1e-5 and manifest['endpoint_velocity_max_error'] < 1e-4
    assert manifest['pixel_seam']['no_duplicate_terminal_frame']
    assert manifest['pixel_seam']['ratio'] < 3
    loop_sha = sha(loop/'Tower_Bridge_Day_Loop.mp4')
    assert manifest['video_sha256'] == loop_sha
    pixels = read(loop/'pixel_validation.json')
    assert pixels['video_sha256'] == loop_sha and pixels['decoded_frames_compared'] == 240
    assert pixels['maximum_rgb_error_255'] < 8 and pixels['encoded_seam_ratio'] < 3
    decoded_loop = read(loop/'Tower_Bridge_Day_Loop_validation.json')
    assert decoded_loop['decoded_count'] == 240 and decoded_loop['video_sha256'] == loop_sha
    portable = read(loop/'portable_validation.json')
    assert portable['derived_sha256'] == manifest['derived_sha256'] and portable['reopened_in_fresh_process']
    assert read(loop/'visual_review.json')['video_sha256'] == loop_sha
    checks.append('E03_value_velocity_pixel_seams_decode_and_portable_reopen')
    weather = out/'extensions/weather'
    for variant, count in [('clear_standard',10),('overcast_sparse',6)]:
        folder = weather/variant
        proof = read(folder/'preset_validation.json')
        assert proof['scene_sha256'] == sha(folder/'Tower_Bridge.blend')
        assert proof['counts']['vehicles'] == count
        actual = read(folder/'validation.json')
        assert actual['frames_checked'] == frames and actual['scene_sha256'] == proof['scene_sha256']
    previews = read(weather/'previews_validation.json')
    sources = {'Clear_Busy': source,
               'Clear_Standard': sha(weather/'clear_standard/Tower_Bridge.blend'),
               'Overcast_Sparse': sha(weather/'overcast_sparse/Tower_Bridge.blend')}
    for image in previews['images']:
        assert image['scene_sha256'] == sources[image['label']]
        path = weather/(image['label']+'.png')
        assert png_size(path) == [1920,1080] and sha(path) == image['image_sha256']
    checks.append('E04_weather_populations_all_frame_variants_and_image_hashes')
    unity = read(root/'Unity/verification-status.json', passed=False)
    assert unity['status'] == 'E05_VERIFIED'
    assert unity['source_sha256'] == source
    assert unity['editor_passed'] and unity['runtime_passed'] and unity['walk_controls_passed']
    exported = read(root/'Unity/Assets/StreamingAssets/scene.json', passed=False)
    assert exported['source_sha256'] == source
    build = root/'Unity/Build'
    assert (build/'TowerBridge.exe').stat().st_size > 10000
    shipped = read(build/'TowerBridge_Data/StreamingAssets/scene.json', passed=False)
    assert shipped['source_sha256'] == source
    assert sha(root/'Unity/Assets/StreamingAssets/scene.bin') == sha(build/'TowerBridge_Data/StreamingAssets/scene.bin')
    assert read(build/'verification.json')['passed']
    assert read(build/'runtime-verification.json')['passed']
    for filename in ('runtime.png','runtime-river.png','runtime-evening.png','runtime-walk.png'):
        assert png_size(build/filename) == [1280,720]
    portable_unity = read(root/'Unity/Verification/portable-validation.json')
    assert portable_unity['source_sha256'] == source
    assert portable_unity['archive_sha256'] == sha(root/'Tower_Bridge_Unity_Windows.zip')
    assert portable_unity['extracted_player_executed'] and portable_unity['archive_crc_check']
    checks.append('E05_current_export_editor_player_walk_controls_and_real_render')
    result = {'passed': True, 'version': cfg['version'], 'scene_sha256': source,
              'tasks': {name: 'completed' for name in ('E01','E02','E03','E04','E05')},
              'checks': checks,
              'scope': 'Verified release artefact identities and actual recorded tests. Unity prototype uses simplified materials; software-rendered Player images do not establish hardware performance.'}
    return result


if __name__ == '__main__':
    result = verify()
    (ROOT/'Tower_Bridge/extensions_validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('EXTENSIONS_OK', json.dumps(result))
