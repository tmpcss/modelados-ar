# Convierte una escena .usd/.usdc/.usdz a .glb: centrada, apoyada en el suelo y escalada
# para que su lado mayor mida el ancho indicado (en metros). Conserva las animaciones.
# Uso: /Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/usd2glb.py -- escena.usdc escena.glb [opciones]
#   ancho=1.0          lado mayor de la escena en metros
#   excluir=obj1,obj2  objetos auxiliares que no deben verse
#   apoyar             baja al suelo los objetos estáticos que flotan
#   alto=obj:1.8       escala la escena para que ese objeto mida esos metros de alto (en vez de ancho)
#   elevar=obj:3       deja la base de ese objeto a esa altura del suelo y añade un ancla invisible
#                      a ras de suelo para que los visores de RA respeten el hueco
#   bucle=obj          repite el ciclo de ese objeto para que llene toda la animación sin cortes
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


def object_and_value(option):
    if option not in options:
        return None, None
    name, value = options[option].rsplit(':', 1)
    return name, float(value)


height_obj, height_m = object_and_value('alto')
lift_obj, lift_m = object_and_value('elevar')
loop_obj = options.get('bucle')

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


def z_range(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    meshes = [o.evaluated_get(depsgraph) for o in [obj, *obj.children_recursive] if o.type == 'MESH']
    zs = [(o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box]
    return (min(zs), max(zs)) if zs else (None, None)


def min_z(obj):
    return z_range(obj)[0]


# Bucle: escala el tiempo del ciclo para que quepa un número entero de veces en la escena
if loop_obj:
    action = scene.objects[loop_obj].animation_data.action
    start, end = action.frame_range
    closed = max(abs(fc.evaluate(start) - fc.evaluate(end)) for fc in action.fcurves) < 0.01
    period = end - start if closed else end - start + 1
    scene_len = scene.frame_end - scene.frame_start
    cycles = max(1, round(scene_len / period))
    k = scene_len / cycles / period
    for fc in action.fcurves:
        if not closed:
            fc.keyframe_points.insert(start + period, fc.evaluate(start))
        for kp in fc.keyframe_points:
            for attr in ('co', 'handle_left', 'handle_right'):
                getattr(kp, attr).x = start + (getattr(kp, attr).x - start) * k
        fc.modifiers.new('CYCLES')
    print(f'BUCLE {loop_obj}: {cycles} ciclos de {period * k:.2f} fotogramas (velocidad x{1 / k:.3f})')
    scene.frame_set(scene.frame_start)


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
if height_obj:
    z0, z1 = z_range(scene.objects[height_obj])
    factor = height_m / (z1 - z0)
else:
    factor = width / max(hi.x - lo.x, hi.y - lo.y)

pivot.scale = (factor,) * 3
pivot.location = (-(lo.x + hi.x) / 2 * factor, -(lo.y + hi.y) / 2 * factor, -lo.z * factor)

if lift_obj:
    bpy.context.view_layer.update()
    pivot.location.z += lift_m - min_z(scene.objects[lift_obj])
    # Ancla invisible en el suelo: los visores apoyan la caja que envuelve el modelo,
    # así que sin ella la escena bajaría al suelo
    mesh = bpy.data.meshes.new('ancla')
    mesh.from_pydata([(-0.005, -0.005, 0), (0.005, -0.005, 0), (0, 0.005, 0)], [], [(0, 1, 2)])
    material = bpy.data.materials.new('ancla')
    material.use_nodes = True
    material.blend_method = 'BLEND'
    material.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0
    mesh.materials.append(material)
    scene.collection.objects.link(bpy.data.objects.new('ancla', mesh))

bpy.context.view_layer.update()
scene_corners = [o.matrix_world @ Vector(c) for o in scene.objects if o.type == 'MESH' and o.name != 'ancla'
                 for c in o.bound_box]
lo_w = Vector(min(c[i] for c in scene_corners) for i in range(3))
hi_w = Vector(max(c[i] for c in scene_corners) for i in range(3))
center = (lo_w + hi_w) / 2
# glTF usa Y arriba: (x, z, -y) de Blender
print(f'ENCUADRE camera-target="{center.x:.2f}m {center.z:.2f}m {-center.y:.2f}m" '
      f'radio={(hi_w - lo_w).length * 1.1:.1f}m altura={lo_w.z:.2f}-{hi_w.z:.2f}m')

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
