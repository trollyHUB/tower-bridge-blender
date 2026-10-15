import unittest
from scene_components import scenario as s

class ScenarioTests(unittest.TestCase):
    def test_opening_is_monotonic_and_bounded_in_each_phase(self):
        values=[s.opening(f) for f in range(1,s.END+1)]
        self.assertGreaterEqual(min(values),0)
        self.assertLessEqual(max(values),s.CONFIG['opening_degrees'])
        rise=values[s.frame(18)-1:s.frame(26)]
        fall=values[s.frame(36)-1:s.frame(44)]
        self.assertTrue(all(a<=b for a,b in zip(rise,rise[1:])))
        self.assertTrue(all(a>=b for a,b in zip(fall,fall[1:])))

    def test_tall_boat_waits_and_clears_before_lowering(self):
        self.assertLess(s.boat_y(s.frame(26))+8,-8)
        self.assertGreater(s.boat_y(s.frame(36))-6,8)

    def test_duration_scaling_preserves_event_states(self):
        original=s.END
        baseline=[s.opening(s.frame(t)) for t in [0,18,22,26,30,36,40,44,60]]
        try:
            s.END=2880
            self.assertEqual(baseline,[s.opening(s.frame(t)) for t in [0,18,22,26,30,36,40,44,60]])
            self.assertEqual(s.frame(60),2880)
        finally:s.END=original

if __name__=='__main__':unittest.main()
