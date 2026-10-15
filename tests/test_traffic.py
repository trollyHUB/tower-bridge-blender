"""Full-frame schedule checks; these do not import Blender."""
import math
import unittest

from scene_components.traffic import (
    LAST_FRAME, VEHICLE_TYPES, barrier_angle, longitudinal_position,
    signal_state, vehicle_position, vehicle_specs,
)


def bumper_interval(spec, frame):
    p = longitudinal_position(spec, frame)
    half = VEHICLE_TYPES[spec['kind']][0]/2
    return p-half, p+half


def lane_clearance(specs, frame, direction):
    lane = sorted((bumper_interval(s, frame) for s in specs
                   if s['direction'] == direction), reverse=True)
    return min((a[0]-b[1] for a, b in zip(lane, lane[1:])), default=math.inf)


class TrafficScheduleTests(unittest.TestCase):
    def test_all_frames_keep_four_metre_body_clearance(self):
        specs = vehicle_specs()
        for frame in range(1, LAST_FRAME+1):
            for direction in (-1, 1):
                self.assertGreaterEqual(lane_clearance(specs, frame, direction), 4-1e-7)

    def test_collision_checker_rejects_deliberate_overlap(self):
        a = vehicle_specs()[0]
        b = dict(a, name='deliberately colliding duplicate')
        self.assertLess(lane_clearance([a, b], 100, a['direction']), 0)

    def test_full_bodies_clear_before_barrier_and_bridge_motion(self):
        for frame in range(337, 1105):
            for spec in vehicle_specs():
                rear, front = bumper_interval(spec, frame)
                self.assertTrue(front <= -30.5 or rear >= 30.5, (frame, spec))

    def test_queued_fronts_stay_before_stop_line_until_green(self):
        for frame in range(193, 1105):
            for spec in vehicle_specs():
                if spec['mode'] == 'queue':
                    self.assertLessEqual(bumper_interval(spec, frame)[1], -56.5+1e-7)

    def test_left_hand_lanes_and_both_directions(self):
        specs = vehicle_specs()
        self.assertEqual({s['kind'] for s in specs}, set(VEHICLE_TYPES))
        for spec in specs:
            self.assertEqual(vehicle_position(spec, 1)[1], spec['direction']*2.8)
            self.assertGreater(longitudinal_position(spec, 1440), longitudinal_position(spec, 1))

    def test_signal_and_barrier_interlock(self):
        self.assertEqual(signal_state(192), 'green')
        self.assertEqual(signal_state(193), 'red')
        self.assertEqual(signal_state(1104), 'red')
        self.assertEqual(signal_state(1105), 'green')
        for frame in range(433, 1057):
            self.assertAlmostEqual(barrier_angle(frame), 0)
        self.assertAlmostEqual(barrier_angle(1104), math.pi/2)

    def test_no_teleport_or_reverse_at_any_frame(self):
        for spec in vehicle_specs():
            values = [longitudinal_position(spec, f) for f in range(1, LAST_FRAME+1)]
            for a, b in zip(values, values[1:]):
                self.assertGreaterEqual(b-a, -1e-7)
                self.assertLessEqual(b-a, .90)
            if spec['mode'] == 'queue':
                self.assertAlmostEqual(values[335], values[1103])


if __name__ == '__main__':
    unittest.main()
