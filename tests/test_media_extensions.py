import importlib.util, math, tempfile, unittest, wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/f'{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class MediaTests(unittest.TestCase):
    def test_audio_is_deterministic_and_non_silent(self):
        m=module('create_presentation')
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            a=Path(tmp)/'a.wav';b=Path(tmp)/'b.wav';m.synthesize(a,2);m.synthesize(b,2)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            with wave.open(str(a)) as w:self.assertEqual(w.getnframes(),48000);self.assertGreater(len(set(w.readframes(48000))),100)
    def test_captions_cover_whole_story(self):
        rows=module('create_presentation').CAPTIONS;self.assertEqual(rows[0][0],0);self.assertEqual(rows[-1][1],60)
        for a,b in zip(rows,rows[1:]):self.assertEqual(a[1],b[0])
    def test_scaled_caption_frames_have_no_gap(self):
        m=module('create_presentation')
        for count in (48,480,1272,1440,2880):
            rows=m.caption_frames(count);self.assertEqual(rows[0][0],1);self.assertEqual(rows[-1][1],count+1)
            for a,b in zip(rows,rows[1:]):self.assertEqual(a[1],b[0])
    def test_configured_bus_caption_matches_camera_mask(self):
        from copy import deepcopy
        from scene_components.settings import load_config
        from scene_components.traffic import bus_stop_times
        m=module('create_presentation')
        for speed in (13,18,26):
            for fps,duration in ((24,60),(30,40),(12,80)):
                cfg=deepcopy(load_config());cfg['traffic']['speed']=speed;cfg['fps']=fps;cfg['duration_seconds']=duration;count=fps*duration
                rows=m.caption_frames(count,cfg);bus=[r for r in rows if r[2] not in [x[2] for x in m.CAPTIONS]]
                _,arrival,departure,_=bus_stop_times(speed)
                self.assertEqual([(r[0],r[1]) for r in bus],[(max(1,round((arrival-2.5)*count/1440)),min(count,math.ceil((departure+5)*count/1440)))])
                self.assertEqual(rows[0][0],1);self.assertEqual(rows[-1][1],count+1)
                for a,b in zip(rows,rows[1:]):self.assertEqual(a[1],b[0])
        cfg['traffic']['bus_stop']=False
        self.assertTrue(all(r[2] in [x[2] for x in m.CAPTIONS] for r in m.caption_frames(1440,cfg)))
    def test_aac_metadata_reads_sample_entry_not_media_payload(self):
        import struct
        m=module('verify_media_extensions')
        def box(kind,body):return struct.pack('>I4s',len(body)+8,kind)+body
        entry=bytearray(28);struct.pack_into('>H',entry,16,2);struct.pack_into('>I',entry,24,48000<<16)
        payload=box(b'stsd',bytes(8)+box(b'mp4a',entry))
        for kind in (b'stbl',b'minf',b'mdia',b'trak',b'moov'):payload=box(kind,payload)
        payload=box(b'mdat',b'mp4a'+bytes(40))+payload
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            path=Path(tmp)/'audio.mp4';path.write_bytes(payload);self.assertEqual(m.mp4_audio(path),{'codec':'AAC/mp4a','channels':2,'sample_rate':48000})
    def test_periodic_values_and_velocity(self):
        f=module('create_day_loop').periodic
        for h in (1,2,3):
            for x in (1,13.7,122):
                self.assertAlmostEqual(f(x,240,h),f(x+240,240,h),places=12)
                eps=.001;self.assertAlmostEqual((f(x+eps,240,h)-f(x-eps,240,h))/(2*eps),(f(x+240+eps,240,h)-f(x+240-eps,240,h))/(2*eps),places=10)
if __name__=='__main__':unittest.main()

