"""Small actual CPU rendering diagnostic; run with Blender --background --python.

Reads the finalized scene without modifying it. The memory value describes the
whole Blender process lifetime, including scene load and the diagnostic render.
"""
import ctypes
import json
import platform
import time
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Tower_Bridge'
SCENE = OUT / 'Tower_Bridge.blend'


def process_memory():
    if platform.system() == 'Windows':
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                       ('PeakWorkingSetSize', ctypes.c_size_t),
                       ('WorkingSetSize', ctypes.c_size_t),
                       ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                       ('QuotaPagedPoolUsage', ctypes.c_size_t),
                       ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                       ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                       ('PagefileUsage', ctypes.c_size_t),
                       ('PeakPagefileUsage', ctypes.c_size_t)]

        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE,
                                             ctypes.POINTER(ProcessMemoryCounters),
                                             wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return {'peak_working_set_bytes': counters.PeakWorkingSetSize,
                'working_set_bytes': counters.WorkingSetSize,
                'memory_source': 'Windows GetProcessMemoryInfo'}
    import resource
    maximum = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {'peak_working_set_bytes': maximum if platform.system() == 'Darwin' else maximum * 1024,
            'memory_source': 'resource.getrusage(RUSAGE_SELF).ru_maxrss'}


bpy.ops.wm.open_mainfile(filepath=str(SCENE))
scene = bpy.context.scene
scene.frame_set(1)
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 1
scene.cycles.use_denoising = False
scene.render.resolution_percentage = 10
scene.render.image_settings.file_format = 'PNG'
image = ROOT / 'research' / 'cpu_probe.png'
image.parent.mkdir(parents=True, exist_ok=True)
scene.render.filepath = str(image)
started = time.perf_counter()
bpy.ops.render.render(write_still=True)
elapsed = time.perf_counter() - started
meshes = [obj for obj in scene.objects if obj.type == 'MESH']
usage = {}
for obj in meshes:
    usage[obj.data.as_pointer()] = usage.get(obj.data.as_pointer(), 0) + 1
report = {'blender_version': bpy.app.version_string, 'platform': platform.platform(),
          'scene_file_bytes': SCENE.stat().st_size, 'frame': 1,
          'engine': 'CYCLES', 'device': 'CPU', 'samples': 1,
          'render_percentage': 10,
          'render_size': [scene.render.resolution_x // 10, scene.render.resolution_y // 10],
          'cpu_render_seconds': elapsed, 'output': 'research/cpu_probe.png',
          'mesh_objects': len(meshes), 'unique_mesh_datablocks': len(usage),
          'shared_mesh_datablocks': sum(count > 1 for count in usage.values()),
          'objects_using_shared_meshes': sum(count for count in usage.values() if count > 1),
          'saved_mesh_instances': sum(count - 1 for count in usage.values()),
          'memory_scope': 'Whole Blender process peak, including scene load and CPU probe'}
try:
    report.update(process_memory())
except (OSError, ImportError) as error:
    report['memory_error'] = str(error)
(OUT / 'diagnostics.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('CPU_DIAGNOSTICS_OK', json.dumps(report), flush=True)
