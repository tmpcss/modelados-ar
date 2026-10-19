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
