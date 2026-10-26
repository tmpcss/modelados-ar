# Convierte un .glb a .usdz conservando las animaciones, para Quick Look (iPhone).
# Uso: /Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/glb2usdz.py -- entrada.glb salida.usdz
import os
import sys
import tempfile

import bpy
from pxr import Usd, UsdGeom, UsdUtils

src, dst = [os.path.abspath(p) for p in sys.argv[sys.argv.index('--') + 1:][:2]]
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
stage.GetRootLayer().Save()

if not UsdUtils.CreateNewARKitUsdzPackage(usdc, dst):
    sys.exit(f'Error al empaquetar {dst}')
print(f'OK {dst} animaciones={len(actions)} fotogramas={bpy.context.scene.frame_start}-{bpy.context.scene.frame_end}')
