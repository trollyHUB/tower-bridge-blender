import math
import unittest
from scene_components.people_math import route_state, foot_target, leg_angles


class PeopleTests(unittest.TestCase):
    def test_route_endpoints_and_distance(self):
        keys=[(1,(0,0,0)),(25,(0,3,0)),(50,(0,3,0)),(75,(4,3,0))]
        self.assertEqual(route_state(keys,1),((0,0,0),0))
        self.assertEqual(route_state(keys,75),((4,3,0),7))
        self.assertEqual(route_state(keys,35),((0,3,0),3))

    def test_stance_world_drift(self):
        for cycle in [.95,1.3]:
            for side in [-1,1]:
                shift=cycle*.5 if side>0 else 0
                positions=[foot_target(2*cycle-shift+t*cycle,side,cycle=cycle)[0]
                           for t in [0,.1,.3,.599999]]
                self.assertLess(max(positions)-min(positions),1e-9)
                # Reconstruct the planted point from root distance and IK chain.
                for t in [0,.1,.3,.599999]:
                    d=2*cycle-shift+t*cycle
                    target,lift=foot_target(d,side,cycle=cycle)
                    a,b=leg_angles(target-d,lift)
                    actual=d+.43*(math.sin(a)+math.sin(a+b))
                    self.assertAlmostEqual(actual,positions[0],places=8)

    def test_wait_halts_both_feet(self):
        keys=[(1,(0,0,0)),(10,(0,3,0)),(50,(0,3,0))]
        for side in [-1,1]:
            self.assertEqual(foot_target(route_state(keys,10)[1],side),
                             foot_target(route_state(keys,40)[1],side))

    def test_analytic_leg_reaches_target(self):
        for forward,lift in [(-.28,0),(.28,0),(0,.13)]:
            a,b=leg_angles(forward,lift)
            self.assertAlmostEqual(.43*(math.sin(a)+math.sin(a+b)),forward)
            self.assertAlmostEqual(.43*(math.cos(a)+math.cos(a+b)),.76-lift)
