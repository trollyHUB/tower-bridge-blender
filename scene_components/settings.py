"""Validated configuration shared by build, render, scripts and packaging."""
import json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def load_config(path=None):
    cfg=json.loads(Path(path or ROOT/'config/scene.json').read_text(encoding='utf-8-sig'))
    frame_count(cfg)
    if not 0<=cfg['wind']['strength']<=.5:raise ValueError('wind.strength must be between 0 and .5')
    if len(cfg['wind']['direction'])<2 or not all(math.isfinite(v) for v in cfg['wind']['direction']):raise ValueError('Invalid wind direction')
    if cfg['wind']['strength'] and math.hypot(*cfg['wind']['direction'][:2])==0:raise ValueError('Nonzero wind needs an XY direction')
    if not .5<=cfg['water']['level']<=1.5:raise ValueError('water.level must remain .5..1.5m for the dock and bridge datum')
    if not 0<=cfg['water']['amplitude']<=.15:raise ValueError('Invalid wave amplitude')
    traffic=cfg['traffic']
    if not 13<=traffic['speed']<=26 or not 2<=traffic['minimum_gap']<=8 or not 55<=traffic['stop_line']<=65:raise ValueError('Traffic calibration: speed13..26, gap2..8, stop_line55..65')
    if not 0<=cfg['people']['bank_walkers']<=12:raise ValueError('bank_walkers must be 0..12')
    for key,limit in [('bank_walkers',12),('passengers_per_stop',5),('cafe_visitors',4)]:
        if not isinstance(cfg['people'][key],int) or not 0<=cfg['people'][key]<=limit:raise ValueError('Invalid people count: '+key)
    if not .25<=cfg['people']['stride_length']<=.45:raise ValueError('stride_length must be .25.. .45m for the articulated legs')
    if not 55<=cfg['opening_degrees']<=68:raise ValueError('opening_degrees must be 55..68 for vessel and walkway clearance')
    if len(cfg['water']['current'])!=2 or not all(math.isfinite(v) and abs(v)<=1 for v in cfg['water']['current']):raise ValueError('Invalid water current')
    if not .5<=cfg['water']['wake_lifetime']<=10:raise ValueError('wake_lifetime must be .5..10 seconds')
    for key,value in cfg['lighting'].items():
        if key!='mode' and (not math.isfinite(value) or value<0):raise ValueError('Invalid lighting power: '+key)
    if not math.isfinite(traffic['headlight_power']) or traffic['headlight_power']<0:raise ValueError('Invalid headlight power')
    if cfg['lighting']['mode'] not in ('animated','day','evening'):raise ValueError('Unknown lighting mode')
    for key in ['width','height']:
        if not isinstance(cfg['render'][key],int) or cfg['render'][key]<16 or cfg['render'][key]%2:raise ValueError('H264 dimensions must be positive even integers')
    if cfg['render']['device'] not in ('auto','cpu','gpu'):raise ValueError('Unknown render device')
    for key in ('samples','preview_samples','still_samples'):
        if not isinstance(cfg['render'][key],int) or cfg['render'][key]<1:raise ValueError('Invalid render samples')
    if cfg['render']['engine'] not in ('EEVEE','CYCLES'):raise ValueError('Unknown render engine')
    scale=cfg['render']['preview_scale']
    if not isinstance(scale,int) or isinstance(scale,bool) or not 1<=scale<=100:raise ValueError('preview_scale must be an integer percentage from 1 to 100')
    preview_size=[cfg['render'][key]*scale//100 for key in ('width','height')]
    if any(size<2 or size%2 for size in preview_size):raise ValueError('Actual preview H264 dimensions must be positive even integers')
    return cfg

def frame_count(cfg):
    fps=cfg['fps'];duration=cfg['duration_seconds'];count=fps*duration
    if not isinstance(fps,int) or not 1<=fps<=120 or not math.isfinite(duration) or duration<=0 or count<2 or abs(count-round(count))>1e-7:raise ValueError('fps/duration must define at least two whole frames')
    return int(round(count))
