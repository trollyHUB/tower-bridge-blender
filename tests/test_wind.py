"""The same field drives tree, cloth and river animation."""
import math
import unittest
from scene_components.wind import wind_vector, wind_time


class WindTests(unittest.TestCase):
    def test_zero_strength_means_no_displacement_at_any_time(self):
        config={'wind':{'strength':0,'direction':[1,.3,0]}}
        for t in [0,.1,4,23,60]:
            self.assertEqual(wind_vector(t,config),(0,0))

    def test_direction_and_magnitude_are_configuration_driven(self):
        config={'wind':{'strength':.4,'direction':[0,-5,0]}}
        for t in [0,4,20,60]:
            x,y=wind_vector(t,config)
            self.assertEqual(x,0)
            self.assertLess(y,0)
            gust=1+.18*math.sin(.7*t)+.08*math.sin(1.9*t)
            self.assertAlmostEqual(abs(y),.4*gust)

    def test_integrated_phase_matches_gust_velocity(self):
        config={'wind':{'strength':1,'direction':[1,0,0]}}
        for t in [.1,7,23,59]:
            dt=1e-5
            derivative=(wind_time(t+dt)-wind_time(t-dt))/(2*dt)
            self.assertAlmostEqual(derivative,wind_vector(t,config)[0],places=7)

    def test_degenerate_direction_is_still(self):
        self.assertEqual(wind_vector(8,{'wind':{'strength':1,'direction':[0,0,1]}}),(0,0))
