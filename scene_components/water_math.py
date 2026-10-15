"""Deterministic wind-driven water and wake mathematics, independent of Blender."""
import math
from .wind import wind_time


def wind_vector(config):
    d=config['wind']['direction']; n=math.hypot(d[0],d[1])
    return (d[0]/n,d[1]/n) if n else (1.,0.)


def wave_modes(config):
    """(amplitude, kx, ky, angular speed, phase); two orthogonal swell modes."""
    dx,dy=wind_vector(config); strength=max(0.,config['wind']['strength'])
    a=config['water']['amplitude']*strength/.12
    return [(a*.65,dx*.23,dy*.23,.9+strength,0.),
            (a*.35,-dy*.37,dx*.37,1.3+strength,1.1)]


def surface_height(x,y,t,config):
    return config['water']['level']+sum(a*math.sin(kx*x+ky*y-w*wind_time(t)+p) for a,kx,ky,w,p in wave_modes(config))


def surface_slope(x,y,t,config):
    return (
        sum(a*kx*math.cos(kx*x+ky*y-w*wind_time(t)+p) for a,kx,ky,w,p in wave_modes(config)),
        sum(a*ky*math.cos(kx*x+ky*y-w*wind_time(t)+p) for a,kx,ky,w,p in wave_modes(config)))


def vessel_pose(x,y,t,heading,config):
    h=lambda xx,yy:surface_height(xx,yy,t,config)
    # Finite footprint samples avoid exaggerated response to short ripples.
    dx=(h(x+1.5,y)-h(x-1.5,y))/3
    dy=(h(x,y+3)-h(x,y-3))/6
    local_x=dx*math.cos(heading)+dy*math.sin(heading)
    local_y=-dx*math.sin(heading)+dy*math.cos(heading)
    return h(x,y)-.9,(math.atan(local_y),-math.atan(local_x),heading)


def wake_state(age,speed,config):
    life=config['water'].get('wake_lifetime',4.); fade=max(0.,1-age/life) if age>=0 else 0.
    dx,dy=wind_vector(config); drift=.22+config['wind']['strength']
    current=config['water'].get('current',[0.,.12])
    return ((dx*drift+current[0])*max(age,0),(dy*drift+current[1])*max(age,0),fade*fade*min(1.,speed/2.5))
