import importlib.util, math, tempfile, unittest, wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/f'{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class MediaTests(unittest.TestCase):
    def test_audio_is_deterministic_and_non_silent(self):
        m=module('create_presentation')
        with tempfile.TemporaryDirectory(dir=ROOT/"research") as tmp:
            a=Path(tmp)/'a.wav';b=Path(tmp)/'b.wav';m.synthesize(a,2);m.synthesize(b,2)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            with wave.open(str(a)) as w:self.assertEqual(w.getnframes(),48000);self.assertGreater(len(set(w.readframes(48000))),100)
    def test_captions_cover_whole_story(self):
        rows=module('create_presentation').CAPTIONS;self.assertEqual(rows[0][0],0);self.assertEqual(rows[-1][1],60)
        for a,b in zip(rows,rows[1:]):self.assertEqual(a[1],b[0])
    def test_scaled_caption_frames_have_no_gap(self):
        m=module('create_presentation')
        for count in (480,1272,1440,2880):
            rows=m.caption_frames(count);self.assertEqual(rows[0][0],1);self.assertEqual(rows[-1][1],count+1)
            for a,b in zip(rows,rows[1:]):self.assertEqual(a[1],b[0])
    def test_periodic_values_and_velocity(self):
        f=module('create_day_loop').periodic
        for h in (1,2,3):
            for x in (1,13.7,122):
                self.assertAlmostEqual(f(x,240,h),f(x+240,240,h),places=12)
                eps=.001;self.assertAlmostEqual((f(x+eps,240,h)-f(x-eps,240,h))/(2*eps),(f(x+240+eps,240,h)-f(x+240-eps,240,h))/(2*eps),places=10)
if __name__=='__main__':unittest.main()

