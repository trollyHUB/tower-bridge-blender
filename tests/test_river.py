import copy
import math
import unittest
from scene_components.scenario import CONFIG
from scene_components.wind import wind_time
from scene_components.water_math import surface_height, surface_slope, wave_modes, vessel_pose, wake_state


class RiverTests(unittest.TestCase):
    def test_shape_key_decomposition_matches_surface(self):
        for x,y,t in [(0,0,0),(16,-37,17.25),(-90,35,59.9)]:
            result=CONFIG['water']['level']
            for a,kx,ky,w,p in wave_modes(CONFIG):
                s=kx*x+ky*y+p
                result+=a*(math.sin(s)*math.cos(w*wind_time(t))-math.cos(s)*math.sin(w*wind_time(t)))
            self.assertAlmostEqual(result,surface_height(x,y,t,CONFIG),places=12)

    def test_level_amplitude_and_wind_propagate(self):
        config=copy.deepcopy(CONFIG); base=surface_height(13,22,7,config)
        config['water']['level']+=2
        self.assertAlmostEqual(surface_height(13,22,7,config),base+2)
        config['water']['amplitude']=0
        self.assertEqual(surface_height(13,22,7,config),config['water']['level'])
        config=copy.deepcopy(CONFIG); config['wind']['strength']=0
        self.assertEqual(surface_height(13,22,7,config),config['water']['level'])
        config=copy.deepcopy(CONFIG); config['wind']['direction']=[0,1,0]
        self.assertNotAlmostEqual(surface_height(13,22,7,config),base)

    def test_slope_matches_numeric_derivative_and_contact(self):
        x,y,t=16,-22,13; epsilon=1e-5
        dx,dy=surface_slope(x,y,t,CONFIG)
        height=lambda x,y:surface_height(x,y,t,CONFIG)
        self.assertAlmostEqual(dx,(height(x+epsilon,y)-height(x-epsilon,y))/(2*epsilon),places=8)
        self.assertAlmostEqual(dy,(height(x,y+epsilon)-height(x,y-epsilon))/(2*epsilon),places=8)
        z,rotation=vessel_pose(x,y,t,math.pi,CONFIG)
        self.assertAlmostEqual(z+.9,height(x,y))
        self.assertLess(max(abs(v) for v in rotation[:2]),.05)

    def test_wake_ages_and_advects_in_world_space(self):
        config=copy.deepcopy(CONFIG); config['water']['wake_lifetime']=4
        first=wake_state(0,3,config); middle=wake_state(2,3,config); last=wake_state(4,3,config)
        self.assertEqual(first[2],1); self.assertEqual(last[2],0)
        self.assertGreater(first[2],middle[2]); self.assertGreater(middle[2],last[2])
        self.assertNotEqual(middle[:2],first[:2])
        self.assertEqual(wake_state(1,0,config)[2],0)
        self.assertEqual(wake_state(-1,3,config)[2],0)
        config['water']['current']=[1,2]
        config_zero=copy.deepcopy(config); config_zero['water']['current']=[0,0]
        shifted=wake_state(2,3,config); still=wake_state(2,3,config_zero)
        self.assertAlmostEqual(shifted[0]-still[0],2)
        self.assertAlmostEqual(shifted[1]-still[1],4)


if __name__=='__main__':unittest.main()
