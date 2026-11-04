# Convierte un .glb a .usdz conservando las animaciones, para Quick Look (iPhone).
# Uso: /Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/glb2usdz.py -- entrada.glb salida.usdz [opciones]
#   duracion=120   repite el bucle de la escena hasta durar al menos esos segundos
#   marcador=4     el marcador del suelo (scripts/marcador.py) se ve esos segundos y luego se encoge
#                  hasta desaparecer; con duracion= queda oculto el resto de la línea de tiempo
#   fps=12         guarda menos fotogramas por segundo (archivo más ligero; Quick Look interpola)
import math
import os
import sys
import tempfile

import bpy
from pxr import Usd, UsdGeom, UsdUtils

args = sys.argv[sys.argv.index('--') + 1:]
src, dst = [os.path.abspath(p) for p in args[:2]]
options = dict(a.split('=', 1) for a in args[2:])
work = tempfile.mkdtemp()

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)

# Las texturas del .glb vienen empaquetadas; el exportador USD necesita que existan en disco
for i, image in enumerate(bpy.data.images):
    if image.packed_file or not os.path.exists(bpy.path.abspath(image.filepath)):
        ext = '.jpg' if image.file_format == 'JPEG' else '.png'
        image.filepath_raw = os.path.join(work, f'tex{i}{ext}')
        image.save()

# Materiales sin sombreado (KHR_materials_unlit): el importador los monta con nodos de emisión
# que el exportador USD no traduce y quedan sin color. Se convierten a Principled BSDF con color
# base negro y la textura como emisión, que en Quick Look se ve igual: color plano sin luces.
for material in bpy.data.materials:
    nodes = material.node_tree.nodes if material.use_nodes else []
    emission = next((n for n in nodes if n.bl_idname == 'ShaderNodeEmission'), None)
    if not emission or any(n.bl_idname == 'ShaderNodeBsdfPrincipled' for n in nodes):
        continue
    links = material.node_tree.links
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0, 0, 0, 1)
    bsdf.inputs['Emission Strength'].default_value = 1.0
    color = emission.inputs['Color']
    if color.is_linked:
        links.new(color.links[0].from_socket, bsdf.inputs['Emission Color'])
    else:
        bsdf.inputs['Emission Color'].default_value = color.default_value
    output = next(n for n in nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

# Rango de la escena = duración total de las animaciones
actions = list(bpy.data.actions)
if actions:
    bpy.context.scene.frame_start = int(min(a.frame_range[0] for a in actions))
    bpy.context.scene.frame_end = int(round(max(a.frame_range[1] for a in actions)))

scene = bpy.context.scene
fps = scene.render.fps
# Duración: Quick Look repite toda la línea de tiempo; se alarga repitiendo el bucle dentro
if actions and 'duracion' in options:
    loop = scene.frame_end - scene.frame_start
    reps = max(1, math.ceil(float(options['duracion']) * fps / loop))
    for action in actions:
        for fc in action.fcurves:
            fc.modifiers.new('CYCLES')
    scene.frame_end = scene.frame_start + loop * reps
    print(f'DURACION {reps} repeticiones de {loop / fps:.2f} s = {loop * reps / fps:.1f} s')

# Marcador: visible unos segundos, luego se encoge hacia el suelo y queda oculto
marker = bpy.data.objects.get('marcador')
if marker and 'marcador' in options:
    visible = scene.frame_start + round(float(options['marcador']) * fps)
    for frame, s in ((scene.frame_start, 1), (visible, 1), (visible + round(fps / 2), 0.0001), (scene.frame_end, 0.0001)):
        marker.scale = (s, s, s)
        marker.keyframe_insert('scale', frame=frame)
    for fc in marker.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    actions = list(bpy.data.actions)
    print(f'MARCADOR visible {options["marcador"]} s')

usdc = os.path.join(work, 'model.usdc')
bpy.ops.wm.usd_export(
    filepath=usdc,
    export_animation=bool(actions),
    export_materials=True,
    generate_preview_surface=True,
    export_textures=True,
    relative_paths=True,
    export_uvmaps=True,
    export_normals=True,
    export_armatures=True,
    export_shapekeys=True,
)

# Blender exporta con Z arriba; Quick Look espera Y arriba
stage = Usd.Stage.Open(usdc)
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
root = stage.GetDefaultPrim()
UsdGeom.Xformable(root).AddRotateXOp().Set(-90.0)

# Aligera la animación (Blender guarda todos los fotogramas, y con duracion= son miles):
# los valores que no cambian quedan fijos y con fps= se guardan menos fotogramas por segundo;
# Quick Look interpola entre los que quedan
step = round(fps / float(options['fps'])) if 'fps' in options else 1
start, end = stage.GetStartTimeCode(), stage.GetEndTimeCode()
for prim in stage.Traverse():
    for attr in prim.GetAttributes():
        times = attr.GetTimeSamples()
        if len(times) < 2:
            continue
        values = [attr.Get(t) for t in times]
        if all(v == values[0] for v in values):
            attr.Clear()
            attr.Set(values[0])
        elif step > 1:
            for t in times:
                if (t - start) % step and t != end:
                    attr.ClearAtTime(t)
# Exportar a un archivo nuevo: guardar sobre el mismo .usdc no recupera el espacio de lo borrado
packed = os.path.join(work, 'scene.usdc')
stage.GetRootLayer().Export(packed)

if not UsdUtils.CreateNewARKitUsdzPackage(packed, dst):
    sys.exit(f'Error al empaquetar {dst}')
print(f'OK {dst} animaciones={len(actions)} fotogramas={scene.frame_start}-{scene.frame_end}')
