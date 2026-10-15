"""Bind final release evidence to the actual delivered scene and media."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scene_components.render_manifest import sha
from tools.verify_extensions import verify, read


def main():
    out = ROOT/'Tower_Bridge'
    source = sha(out/'Tower_Bridge.blend')
    video = sha(out/'Tower_Bridge_Animation.mp4')
    extension = verify()
    checks = list(extension['checks'])
    for name in ('validation', 'bascule_validation', 'stills_validation',
                 'full_video_validation', 'video_pixel_validation', 'visual_review'):
        report = read(out/(name+'.json'))
        assert report['scene_sha256'] == source, name
        if 'video_sha256' in report:
            assert report['video_sha256'] == video, name
        checks.append(name)
    pixels = read(out/'video_pixel_validation.json')
    assert pixels['frames_checked'] == 1440 and pixels['maximum_rgb_error_255'] < 8
    review = read(out/'visual_review.json')
    assert review['video_pixel_validation_sha256'] == sha(out/'video_pixel_validation.json')
    assert len(review['contact_pages']) == 15 and len(review['full_resolution_controls']) == 7
    for row in review['contact_pages'] + review['full_resolution_controls']:
        assert row['visually_reviewed'] and sha(ROOT/row['path']) == row['sha256']
    stills = read(out/'stills_validation.json')
    for name, info in stills['images'].items():
        assert sha(out/'renders'/name) == info['sha256']
    proxy = read(out/'review_proxy_validation.json')
    assert proxy['source_identity']['scene_sha256'] == source
    assert proxy['video_sha256'] == sha(out/'Tower_Bridge_ReviewProxy.mp4')
    rebuild = read(out/'reproducibility.json')
    assert rebuild['primary_file_sha256'] == source and rebuild['primary_file_unchanged']
    alternate = read(out/'configuration_validation.json')
    # The alternate run exercises these exact build/render components. Later
    # documentation/packaging edits do not imply re-rendering the smoke test.
    for name, digest in alternate['source_sha256'].items():
        if name in ('build_tower_bridge.py','render_tower_bridge.py') or name.startswith('scene_components/'):
            assert sha(ROOT/name) == digest, ('Changed core after alternate test', name)
    collage = read(out/'extensions_image_validation.json')
    assert collage['scene_sha256'] == source
    assert collage['output_sha256'] == sha(out/'renders/Extensions_v1.2.0.jpg')
    for item in collage['inputs']:
        assert sha(ROOT/item['source']) == item['sha256']
    portable = read(out/'portable_validation.json')
    assert portable['extracted_scene_sha256'] == source
    assert portable['archive_crc_check'] and portable['animation_drivers_evaluated']
    checks += ['review_contact_and_control_hashes', 'all_still_hashes', 'proxy_identity',
               'independent_rebuild', 'alternate_exact_core_source_hashes',
               'collage_input_and_output_hashes', 'portable_scene_open_and_drivers']
    result = {'passed': True, 'version': '1.2.0', 'scene_sha256': source,
              'video_sha256': video, 'frames': 1440, 'checks': checks,
              'scope': 'Actual final artefact identities and recorded checks; historical v1.0/v1.1 comparison media are not current-render evidence. Full ZIP CRC and portable Blender opening recorded separately; Unity archive was extracted and executed. Visual and prototype limitations remain as documented.'}
    (out/'delivery_validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('DELIVERY_OK', json.dumps(result))


if __name__ == '__main__':
    main()
