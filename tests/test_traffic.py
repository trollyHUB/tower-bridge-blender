"""Full-frame schedule checks; these do not import Blender."""
import math
import unittest

from scene_components.traffic import (
    LAST_FRAME, VEHICLE_TYPES, barrier_angle, longitudinal_position,
    signal_state, vehicle_position, vehicle_specs, vehicle_sample,
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
        b = dict(a)
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
            self.assertGreater(vehicle_sample(spec,1440)[1], 0)

    def test_recycled_arrivals_join_closed_queue(self):
        for spec in vehicle_specs():
            if spec['mode'] != 'through':
                continue
            values = [longitudinal_position(spec,f) for f in range(1,1105)]
            first_wrap = next(i for i in range(1,len(values)) if values[i] < values[i-1])
            for frame in range(max(first_wrap+1,193),1105):
                self.assertLessEqual(bumper_interval(spec,frame)[1],-56.5+1e-7)
            self.assertGreater(longitudinal_position(spec,1440),values[-1])

    def test_configured_schedule_extremes_remain_safe(self):
        from unittest.mock import patch
        from scene_components.scenario import CONFIG
        from scene_components.traffic import _schedule
        for speed in (13,18,26):
            for gap in (2,4,8):
                for stop_line in (55,65):
                    settings = dict(speed=speed,minimum_gap=gap,stop_line=stop_line,recycle=True)
                    with patch.dict(CONFIG, {'traffic':settings}):
                        specs = vehicle_specs()
                        rows = _schedule(speed,gap,stop_line,True)
                        recycled = set()
                        for f,(positions,odometers) in enumerate(rows,1):
                            if f > 1:
                                recycled.update(i for i,p in enumerate(positions) if p < rows[f-2][0][i])
                            for direction in (-1,1):
                                indices = sorted((i for i,spec in enumerate(specs) if spec['direction']==direction),key=lambda i:positions[i],reverse=True)
                                for front,back in zip(indices,indices[1:]):
                                    clearance = positions[front]-VEHICLE_TYPES[specs[front]['kind']][0]/2-positions[back]-VEHICLE_TYPES[specs[back]['kind']][0]/2
                                    self.assertGreaterEqual(clearance,gap-1e-7,(settings,f))
                            for i,spec in enumerate(specs):
                                half=VEHICLE_TYPES[spec['kind']][0]/2
                                rear,front=positions[i]-half,positions[i]+half
                                if 193 <= f <1105 and (spec['mode']=='queue' or i in recycled):
                                    self.assertLessEqual(front,-stop_line,(settings,f,spec))
                                if 337 <= f <1105:
                                    self.assertTrue(front<=-30.5 or rear>=30.5,(settings,f,spec))
                        self.assertGreaterEqual(len(recycled),6)
        _schedule.cache_clear()

    def test_signal_and_barrier_interlock(self):
        self.assertEqual(signal_state(192), 'green')
        self.assertEqual(signal_state(193), 'red')
        self.assertEqual(signal_state(1104), 'red')
        self.assertEqual(signal_state(1105), 'green')
        for frame in range(433, 1057):
            self.assertAlmostEqual(barrier_angle(frame), 0)
        self.assertAlmostEqual(barrier_angle(1104), math.pi/2)

    def test_recycling_is_hidden_and_odometer_never_reverses(self):
        wraps = 0
        for spec in vehicle_specs():
            half = VEHICLE_TYPES[spec['kind']][0]/2
            samples = [vehicle_sample(spec,f) for f in range(1,LAST_FRAME+1)]
            for (a,da),(b,db) in zip(samples,samples[1:]):
                self.assertGreaterEqual(db-da,-1e-7)
                self.assertLessEqual(db-da,.90)
                if b < a:
                    wraps += 1
                    self.assertGreater(abs(a)-half,199)
                    self.assertGreater(abs(b)-half,199)
                else:
                    self.assertAlmostEqual(db-da,b-a)
        self.assertGreaterEqual(wraps,6)


if __name__ == '__main__':
    unittest.main()
