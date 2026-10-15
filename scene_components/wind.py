"""One world-space wind field shared by cloth, vegetation and the river."""
import math
from .scenario import CONFIG

def wind_time(t):
    return t+.18*(1-math.cos(.7*t))/.7+.08*(1-math.cos(1.9*t))/1.9

def wind_vector(t, config=None):
    config=CONFIG if config is None else config
    wind=config['wind'];x,y,*_=wind['direction']
    norm=math.hypot(x,y)
    if norm<1e-12 or wind['strength']==0:return (0.,0.)
    gust=1+.18*math.sin(.7*t)+.08*math.sin(1.9*t)
    strength=wind['strength']*gust
    return (x/norm*strength,y/norm*strength)
