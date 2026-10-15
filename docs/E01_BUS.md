# E01: bank bus stop

The initial eastbound (+1) bus pauses at the existing north pavement shelter centered at x=157, y=9.5. Its lane center stays y=2.8. The 10.8 m body occupies x=151.6..162.4 at rest, within the marked x=151..163 stop footprint and well outside the moving span.

The deterministic reference timeline uses the configured road speed until x=139, an 18 m quadratic deceleration, a 48-frame (two-second) dwell, an 18 m quadratic acceleration and normal cruise. Position and velocity are continuous. At the default 18 m/s arrival is reference frame 354.33 and departure 402.33. Two gold framed pavement-side door panels slide open only inside the stationary interval; two stationary margin frames bracket eight-frame door opening/closing ramps. Brake lamps illuminate during approach and dwell. Wheel rotation uses the solver odometer, including deceleration and acceleration; portal teleports add no odometer distance.

`traffic.bus_stop` defaults to true; false restores through movement. The existing ordered-lane solver clips following traffic to the configured full-body gap during the pause. Speed presets 13/18/26 m/s, gaps 2/4/8 m, stop lines 55/65 m and density presets 3/5/7 retain their safety checks. Timeline samples are baked per output frame and support arbitrary seeking.

Camera 09 uses position (177, 27, 22), look at (157, 3, 12); view the default stop around reference frame 378. The camera component derives its editing markers from the configured bus arrival/departure, including alternate traffic speeds and fps/duration. The default cut spans frames352–407.

Verification: `python -m unittest tests.test_traffic -q`; the Blender validator checks evaluated door positions against the deterministic schedule and requires x=157 whenever doors open, in addition to existing mesh clearance, wheel, signal, barrier and hidden recycle checks.
