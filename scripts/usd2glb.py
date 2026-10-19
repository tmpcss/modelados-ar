# Convierte una escena .usd/.usdc/.usdz a .glb: centrada, apoyada en el suelo y escalada
# para que su lado mayor mida el ancho indicado (en metros). Conserva las animaciones.
# Uso: /Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/usd2glb.py -- escena.usdc escena.glb [ancho=1.0]
import os
import sys

import bpy
from mathutils import Vector
from pxr import Usd

args = sys.argv[sys.argv.index('--') + 1:]
src, dst = os.path.abspath(args[0]), os.path.abspath(args[1])
width = float(args[2]) if len(args) > 2 else 1.0

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

# Nodos vacíos sin contenido (luces descartadas, carpetas de materiales)
for obj in [o for o in scene.objects if o.type == 'EMPTY' and not o.children]:
    bpy.data.objects.remove(obj)

scene.frame_set(scene.frame_start)

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
size = (hi - lo) * factor
print(f'OK {dst} tamaño={size.x:.2f}x{size.y:.2f}x{size.z:.2f} m acciones={len(bpy.data.actions)} '
      f'fotogramas={scene.frame_start}-{scene.frame_end} fps={scene.render.fps}')
