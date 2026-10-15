"""Story cameras and named editing bookmarks."""
import math
from .scenario import frame, END

def build(g):
    scene=g['scene'];camera=g['camera'];aim=g['aim']
    hero=g['hero'];hero.location=(285,-400,255);hero.data.ortho_scale=485;aim(hero,(0,0,16))
    anim=g['anim'];anim.animation_data_clear();anim.location=hero.location;anim.data.ortho_scale=485;aim(anim,(0,0,16))
    city=camera('05 | City camera',(-240,-170,133),(-145,8,14),48,ortho=190)
    water=camera('06 | Water camera',(94,-125,53),(0,0,21),48,ortho=150)
    evening=camera('07 | Evening camera',(285,-400,255),(0,0,16),48,ortho=485)
    traffic=camera('08 | Traffic camera',(-73,-70,36),(-57,0,13),48,ortho=105)
    bus=camera('09 | Bus stop camera',(177,27,22),(157,3,12),48,ortho=29)
    for seconds,cam in [(0,anim),(8,traffic),(18,hero),(26,water),(36,hero),(44,traffic),(50,city),(55,evening)]:
        marker=scene.timeline_markers.new('SHOT | '+cam.name,frame=max(1,frame(seconds)+ (1 if seconds else 0)));marker.camera=cam
    if g['CONFIG']['traffic'].get('bus_stop',True):
        from .traffic import bus_stop_times
        _,arrival,departure,_=bus_stop_times()
        start=max(1,round((arrival-2.5)*END/1440))
        end=min(END,math.ceil((departure+5)*END/1440))
        marker=scene.timeline_markers.new('SHOT | Bus dwell and doors',frame=start);marker.camera=bus
        marker=scene.timeline_markers.new('SHOT | Gates closing',frame=end);marker.camera=traffic if departure+5<432 else hero
    scene.camera=anim
