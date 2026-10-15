"""Blender checks for the completed water, wake, people and practical-light work.

Checks evaluate baked objects, including random-access-compatible per-frame poses.
Water ray casts sample the visible triangulated mesh, not an analytic substitute.
"""
import json
import math
from .scenario import CONFIG, FPS, END, boat_y, dusk
from .water_math import surface_height, vessel_pose, wake_state


def validate(scene):
    import bpy
    from mathutils import Vector
    assert json.loads(scene['Configuration']) == CONFIG, 'Saved scene configuration differs from build configuration'
    original=scene.frame_current
    vessels=[o for o in scene.objects if o.get('actor_type') in ('sailboat','launch','moored')]
    walkers=[o for o in scene.objects if o.get('role')=='walker']
    wakes=[o for o in scene.objects if o.get('world_space_wake')]
    water=next(o for o in scene.objects if o.get('surface_contract')) if CONFIG['features'].get('river') else None
    stats={'configuration_roundtrip':True,'water_mesh_samples':0,'vessel_pose_frames':0,
           'max_water_mesh_height_error_m':0.,'max_buoyancy_contact_error_m':0.,
           'max_foot_target_error_m':0.,'max_stance_slide_m':0.,'planted_foot_frame_checks':0,
           'wake_age_samples':0,'headlight_count':0,
           'scope':'Vessel buoyancy and foot contact every integer frame; evaluated triangulated water and wake age sampled every 6 frames plus endpoint; no subframe swept collision proof'}
    feet={o:[bpy.data.objects[o.name+' foot '+str(side)] for side in (-1,1)] for o in walkers}
    previous={}
    headlights=[o for o in scene.objects if o.type=='LIGHT' and 'headlight ' in o.name]
    stats['headlight_count']=len(headlights)
    if CONFIG['features'].get('traffic'):assert len(headlights)==4*CONFIG['traffic'].get('vehicles_per_direction',7), ('actual headlight count',len(headlights))
    if CONFIG['features'].get('city'):
        people=CONFIG.get('people',{})
        waiting=[o for o in scene.objects if o.get('role')=='bus_stop_waiting']
        cafe=[o for o in scene.objects if o.get('role')=='cafe_seated']
        assert len(waiting)==2*people.get('passengers_per_stop',3), 'Bus stop passenger count'
        assert len(cafe)==people.get('cafe_visitors',4), 'Cafe visitor count'
        assert len(walkers)==scene['Pedestrian walking count'], 'Walker count metadata'
        offsets=[round(o['gait_phase_offset_m'],6) for o in walkers]
        assert len(set(offsets))==len(offsets), 'Pedestrians must have individual gait phases'
        stats['distinct_gait_phases']=len(set(offsets))
        assert len([o for o in scene.objects if o.get('seat_owner')])==len(cafe), 'Cafe seating ownership'
        stats.update(walking_people=len(walkers),waiting_passengers=len(waiting),cafe_visitors=len(cafe))
    if CONFIG['features'].get('lighting'):
        roles={role:len([o for o in scene.objects if o.type=='LIGHT' and o.get('lighting_role')==role]) for role in ('lantern','tower','walkway','dock','bus_stop','cafe')}
        assert all(count>0 for count in roles.values()), ('Missing actual practical light role',roles)
        stats['practical_light_roles']=roles
    if water:
        assert len([o for o in vessels if o.get('actor_type')=='moored'])==2, 'Two dock skiffs required'
        assert any(o.type=='MESH' and 'skiff mooring lines' in o.name for o in scene.objects), 'Missing skiff mooring ropes'
        assert any(o.type=='MESH' and 'mooring ropes and piles' in o.name for o in scene.objects), 'Missing mooring piles'
        assert wakes and all(o.parent is None for o in wakes), 'Wake patches must be independent in world space'
    try:
        for f in range(1,scene.frame_end+1):
            scene.frame_set(f); bpy.context.view_layer.update(); t=(f-1)/FPS
            if water:
                evaluated=water.evaluated_get(bpy.context.evaluated_depsgraph_get()) if f%6==1 or f==END else None
                for vessel in vessels:
                    x,y,z=vessel.location; heading=math.pi if vessel.get('actor_type')=='launch' else 0.
                    expected_z,expected_rot=vessel_pose(x,y,t,heading,CONFIG)
                    error=abs(z-expected_z); stats['max_buoyancy_contact_error_m']=max(stats['max_buoyancy_contact_error_m'],error)
                    assert error<1e-5, ('vessel waterline',vessel.name,f,error)
                    assert max(abs(a-b) for a,b in zip(vessel.rotation_euler,expected_rot))<1e-5, ('vessel sampled pitch/roll',vessel.name,f)
                    stats['vessel_pose_frames']+=1
                    if evaluated:
                        hit,point,normal,index=evaluated.ray_cast(Vector((x,y,20)),Vector((0,0,-1)))
                        assert hit, ('Water mesh missing under vessel',vessel.name,f)
                        error=abs(point.z-surface_height(x,y,t,CONFIG))
                        stats['max_water_mesh_height_error_m']=max(stats['max_water_mesh_height_error_m'],error)
                        assert error<.01, ('Water mesh/buoyancy disagreement',vessel.name,f,error)
                        stats['water_mesh_samples']+=1
                if f%6==1 or f==END:
                    for patch in wakes:
                        birth=patch['wake_birth_frame']; age=(f-birth)/FPS
                        dx,dy,fade=wake_state(age,patch['wake_speed'],CONFIG)
                        if age<0 or age>=CONFIG['water'].get('wake_lifetime',4):
                            assert max(abs(v) for v in patch.scale)<1e-4 or (age>=0 and max(abs(v) for v in patch.scale)<.0011), ('Wake visible outside lifetime',patch.name,f)
                        elif age>=0:
                            sail=patch.name.startswith('Sailing boat')
                            x=0 if sail else 16; y=boat_y(birth) if sail else 52-104*(birth-1)/(END-1)
                            direction=1 if sail else -1; side=-1 if 'side -1' in patch.name else 1
                            expected=(x+side*(1.3+age*.65)+dx,y-direction*((5.8 if sail else 3.8)+age*.25)+dy)
                            assert math.dist(tuple(patch.location)[:2],expected)<1e-4, ('Wake does not follow historical world position',patch.name,f)
                            meshchildren=[o for o in patch.children if o.type=='MESH']
                            assert meshchildren, ('Wake geometry missing',patch.name)
                            mat=meshchildren[0].data.materials[0]
                            alpha=mat.node_tree.nodes.get('Principled BSDF').inputs['Alpha'].default_value
                            assert abs(alpha-fade)<1e-4, ('Wake age opacity',patch.name,f,alpha,fade)
                        stats['wake_age_samples']+=1
                    for vessel in vessels:
                        if vessel.get('actor_type')!='sailboat':continue
                        lo=max(1,f-1);hi=min(END,f+1);speed=abs(boat_y(hi)-boat_y(lo))*FPS/(hi-lo)
                        if speed<1e-8:
                            foam=next(o for o in vessel.children if o.name.endswith('| bow foam'))
                            assert abs(foam.scale.x)<1e-6 and abs(foam.scale.y)<1e-6, ('Stationary vessel bow foam',f)
            for actor,actor_feet in feet.items():
                distance=float(actor['route_distance'])
                for side,foot in zip((-1,1),actor_feet):
                    actual=foot.matrix_world.translation.copy(); local=Vector((side*.12,float(foot['stance_anchor'])-distance,float(foot['lift'])))
                    expected=actor.matrix_world @ local
                    error=(actual-expected).length;stats['max_foot_target_error_m']=max(stats['max_foot_target_error_m'],error)
                    assert error<2e-4, ('Actual foot fails baked target',actor.name,side,f,error)
                    if foot['stance']:
                        stats['planted_foot_frame_checks']+=1
                        assert abs(actual.z-actor.matrix_world.translation.z)<2e-4, ('Stance foot above/below ground',foot.name,f)
                        if foot.name in previous:
                            old_anchor,old_position=previous[foot.name]
                            if abs(old_anchor-float(foot['stance_anchor']))<1e-6:
                                slide=(actual-old_position).length;stats['max_stance_slide_m']=max(stats['max_stance_slide_m'],slide)
                                assert slide<2e-4, ('Planted foot slides',foot.name,f,slide)
                        previous[foot.name]=(float(foot['stance_anchor']),actual)
                    else:previous.pop(foot.name,None)
        for f in (1,END):
            scene.frame_set(f)
            expected=CONFIG.get('traffic',{}).get('headlight_power',120)*CONFIG['lighting']['night_strength']*dusk(f)
            for lamp in headlights:
                assert abs(lamp.data.energy-expected)<.01, ('Headlight configured day/dusk energy',lamp.name,f,lamp.data.energy,expected)
            for lamp in [o for o in scene.objects if o.type=='LIGHT' and o.get('lighting_role') and o.get('lighting_role')!='headlight']:
                role=lamp['lighting_role']; power_key={'lantern':'lantern_power','tower':'tower_power','walkway':'walkway_power','dock':'dock_power','bus_stop':'stop_power','cafe':'cafe_power'}[role]
                power=CONFIG['lighting'][power_key]*(1.55 if lamp.name.startswith('Upper tower wash') else 1.)
                expected_power=power*CONFIG['lighting']['night_strength']*dusk(f)
                assert abs(lamp.data.energy-expected_power)<.02, ('Practical configured day/dusk energy',lamp.name,f,lamp.data.energy,expected_power)
    finally:
        scene.frame_set(original); bpy.context.view_layer.update()
    return stats
