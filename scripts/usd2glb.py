# Convierte una escena .usd/.usdc/.usdz a .glb: centrada, apoyada en el suelo y escalada
# para que su lado mayor mida el ancho indicado (en metros). Conserva las animaciones.
# Uso: /Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/usd2glb.py -- escena.usdc escena.glb [opciones]
#   ancho=1.0          lado mayor de la escena en metros
#   excluir=obj1,obj2  objetos auxiliares que no deben verse
#   apoyar             baja al suelo los objetos estáticos que flotan
import json
import os
import struct
import sys

import bpy
from mathutils import Vector
from pxr import Usd

args = sys.argv[sys.argv.index('--') + 1:]
src, dst = os.path.abspath(args[0]), os.path.abspath(args[1])
options = dict(a.split('=', 1) if '=' in a else (a, '1') for a in args[2:])
width = float(options.get('ancho', 1.0))
exclude = set(filter(None, options.get('excluir', '').split(',')))
ground = 'apoyar' in options

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.usd_import(filepath=src, import_lights=False, import_cameras=False, set_frame_range=True)
scene = bpy.context.scene
# Respeta los fotogramas por segundo del archivo original
scene.render.fps = round(Usd.Stage.Open(src).GetTimeCodesPerSecond())
scene.render.fps_base = 1

# Esqueletos sin pesos no deforman nada y en glTF pueden colapsar la malla: se eliminan
for obj in [o for o in scene.objects if o.type == 'MESH']:
    for mod in [m for m in obj.modifiers if m.type == 'ARMATURE']:
        if not obj.vertex_groups:
            obj.modifiers.remove(mod)
used = {m.object for o in scene.objects for m in o.modifiers if m.type == 'ARMATURE'}
for arm in [o for o in scene.objects if o.type == 'ARMATURE' and o not in used]:
    bpy.data.objects.remove(arm)

# Objetos auxiliares que no deben verse (se eliminan con sus hijos)
for obj in [o for o in scene.objects if o.name in exclude]:
    for child in obj.children_recursive:
        bpy.data.objects.remove(child)
    bpy.data.objects.remove(obj)

# Mallas duplicadas en la misma posición (se solapan y parpadean)
seen = set()
for obj in [o for o in scene.objects if o.type == 'MESH']:
    key = (len(obj.data.vertices), tuple(round(v, 4) for row in obj.matrix_world for v in row))
    if key in seen:
        bpy.data.objects.remove(obj)
    else:
        seen.add(key)

# Nodos vacíos sin contenido (luces descartadas, carpetas de materiales)
for obj in [o for o in scene.objects if o.type == 'EMPTY' and not o.children]:
    bpy.data.objects.remove(obj)

scene.frame_set(scene.frame_start)
bpy.context.view_layer.update()


def is_animated(obj):
    return any(o.animation_data and o.animation_data.action for o in [obj, *obj.children_recursive])


def min_z(obj):
    meshes = [o for o in [obj, *obj.children_recursive] if o.type == 'MESH']
    return min((o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box) if meshes else None


if ground:
    for obj in [o for o in scene.objects if o.parent is None and not is_animated(o)]:
        z = min_z(obj)
        if z is not None and z > 0.01:
            obj.location.z -= z

# Todo cuelga de un único nodo raíz para poder centrar y escalar sin tocar las animaciones
roots = [o for o in scene.objects if o.parent is None]
pivot = bpy.data.objects.new('Escena', None)
scene.collection.objects.link(pivot)
for obj in roots:
    obj.parent = pivot

bpy.context.view_layer.update()
corners = [o.matrix_world @ Vector(c) for o in scene.objects if o.type == 'MESH' for c in o.bound_box]
lo = Vector(min(c[i] for c in corners) for i in range(3))
hi = Vector(max(c[i] for c in corners) for i in range(3))
factor = width / max(hi.x - lo.x, hi.y - lo.y)

pivot.scale = (factor,) * 3
pivot.location = (-(lo.x + hi.x) / 2 * factor, -(lo.y + hi.y) / 2 * factor, -lo.z * factor)

bpy.ops.export_scene.gltf(
    filepath=dst,
    export_format='GLB',
    export_animations=True,
    export_frame_range=True,
    export_force_sampling=True,
    export_animation_mode='SCENE',
    export_lights=False,
    export_cameras=False,
)


def merge_animations(path):
    """Une todas las animaciones del .glb en una: los visores reproducen solo la primera."""
    with open(path, 'rb') as f:
        data = f.read()
    json_len = struct.unpack('<I', data[12:16])[0]
    gltf = json.loads(data[20:20 + json_len])
    anims = gltf.get('animations', [])
    if len(anims) < 2:
        return len(anims)
    merged = {'name': 'Escena', 'channels': [], 'samplers': []}
    for anim in anims:
        offset = len(merged['samplers'])
        merged['samplers'] += anim['samplers']
        merged['channels'] += [{**c, 'sampler': c['sampler'] + offset} for c in anim['channels']]
    gltf['animations'] = [merged]
    chunk = json.dumps(gltf, separators=(',', ':')).encode()
    chunk += b' ' * (-len(chunk) % 4)
    rest = data[20 + json_len:]
    total = 12 + 8 + len(chunk) + len(rest)
    with open(path, 'wb') as f:
        f.write(data[:8] + struct.pack('<I', total))  # magic + versión + longitud total
        f.write(struct.pack('<I', len(chunk)) + b'JSON' + chunk + rest)
    return len(anims)


merged = merge_animations(dst)
size = (hi - lo) * factor
print(f'OK {dst} tamaño={size.x:.2f}x{size.y:.2f}x{size.z:.2f} m acciones={len(bpy.data.actions)} '
      f'fotogramas={scene.frame_start}-{scene.frame_end} fps={scene.render.fps} animaciones_unidas={merged}')
