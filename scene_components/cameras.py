"""Story cameras and named editing bookmarks."""
from .scenario import frame, END

def build(g):
    scene=g['scene'];camera=g['camera'];aim=g['aim']
    hero=g['hero'];hero.location=(285,-400,255);hero.data.ortho_scale=485;aim(hero,(0,0,16))
    anim=g['anim'];anim.animation_data_clear();anim.location=hero.location;anim.data.ortho_scale=485;aim(anim,(0,0,16))
    city=camera('05 | City camera',(-240,-170,133),(-145,8,14),48,ortho=190)
    water=camera('06 | Water camera',(94,-125,53),(0,0,21),48,ortho=150)
    evening=camera('07 | Evening camera',(285,-400,255),(0,0,16),48,ortho=485)
    traffic=camera('08 | Traffic camera',(-111,-49,37),(-43,0,13),48,ortho=105)
    for seconds,cam in [(0,anim),(8,traffic),(18,hero),(26,water),(36,hero),(44,traffic),(50,city),(55,evening)]:
        marker=scene.timeline_markers.new('SHOT | '+cam.name,frame=max(1,frame(seconds)+ (1 if seconds else 0)));marker.camera=cam
    scene.camera=anim
