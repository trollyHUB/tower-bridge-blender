"""Reject scene settings that break geometric or encoding contracts."""
import copy,json,unittest
from unittest.mock import patch
from pathlib import Path
from scene_components.settings import load_config,frame_count

class SettingsTests(unittest.TestCase):
    def setUp(self):self.cfg=load_config()
    def read(self,cfg):
        with patch.object(Path,'read_text',return_value=json.dumps(cfg)):
            return load_config('scene.json')
    def test_fractional_duration_preserves_integral_frame_count(self):
        self.cfg.update(fps=50,duration_seconds=.58)
        self.assertEqual(frame_count(self.read(self.cfg)),29)
    def test_geometrically_unsafe_settings_rejected(self):
        for section,key,value in [('people','stride_length',1),('people','cafe_visitors',20),('water','level',8),('water','amplitude',2),('traffic','speed',3),('traffic','stop_line',30)]:
            cfg=copy.deepcopy(self.cfg);cfg[section][key]=value
            with self.subTest(section=section,key=key),self.assertRaises(ValueError):self.read(cfg)
    def test_empty_or_nonintegral_timeline_rejected(self):
        for fps,duration in [(24,0),(24,.01),(24,1.01),(0,60)]:
            with self.subTest(fps=fps,duration=duration),self.assertRaises(ValueError):frame_count({'fps':fps,'duration_seconds':duration})
    def test_all_supported_light_modes_and_zero_wind(self):
        for mode in ['animated','day','evening']:
            cfg=copy.deepcopy(self.cfg);cfg['lighting']['mode']=mode;cfg['wind'].update(strength=0,direction=[0,0,0])
            self.assertEqual(self.read(cfg)['lighting']['mode'],mode)
