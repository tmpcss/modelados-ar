# Reduce el peso de las texturas de un .glb: tamaño máximo y JPEG para las que no usan transparencia.
# Usa `sips` (incluido en macOS). Uso: python3 scripts/optimizar_glb.py modelo.glb [max_px=1024] [calidad=85]
import json
import os
import struct
import subprocess
import sys
import tempfile

path = sys.argv[1]
max_px = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
quality = sys.argv[3] if len(sys.argv) > 3 else '85'

with open(path, 'rb') as f:
    data = f.read()
json_len = struct.unpack('<I', data[12:16])[0]
gltf = json.loads(data[20:20 + json_len])
bin_start = 20 + json_len + 8
binary = data[bin_start:bin_start + struct.unpack('<I', data[20 + json_len:24 + json_len])[0]]

# Imágenes usadas por materiales con transparencia: se quedan en PNG
textures = gltf.get('textures', [])
alpha_images = set()
for material in gltf.get('materials', []):
    if material.get('alphaMode', 'OPAQUE') != 'OPAQUE':
        pbr = material.get('pbrMetallicRoughness', {})
        for ref in (pbr.get('baseColorTexture'), material.get('emissiveTexture')):
            if ref:
                alpha_images.add(textures[ref['index']]['source'])

views = gltf['bufferViews']
replacements = {}
work = tempfile.mkdtemp()
for i, image in enumerate(gltf.get('images', [])):
    view = views[image['bufferView']]
    raw = binary[view.get('byteOffset', 0):view.get('byteOffset', 0) + view['byteLength']]
    keep_png = i in alpha_images
    src = os.path.join(work, f'{i}.{"jpg" if image["mimeType"] == "image/jpeg" else "png"}')
    dst = os.path.join(work, f'{i}-out.{"png" if keep_png else "jpg"}')
    open(src, 'wb').write(raw)
    cmd = ['sips', '-Z', str(max_px), '-s', 'format', 'png' if keep_png else 'jpeg']
    if not keep_png:
        cmd += ['-s', 'formatOptions', quality]
    subprocess.run(cmd + [src, '--out', dst], check=True, capture_output=True)
    new = open(dst, 'rb').read()
    if len(new) < len(raw):
        replacements[image['bufferView']] = new
        image['mimeType'] = 'image/png' if keep_png else 'image/jpeg'
    print(f'{image.get("name", i)}: {len(raw) / 1e6:.2f} MB -> {len(replacements.get(image["bufferView"], raw)) / 1e6:.2f} MB')

# Reconstruye el buffer binario con las nuevas imágenes (alineado a 4 bytes)
out = bytearray()
for index, view in enumerate(views):
    chunk = replacements.get(index)
    if chunk is None:
        chunk = binary[view.get('byteOffset', 0):view.get('byteOffset', 0) + view['byteLength']]
    out += b'\0' * (-len(out) % 4)
    view['byteOffset'] = len(out)
    view['byteLength'] = len(chunk)
    out += chunk
out += b'\0' * (-len(out) % 4)
gltf['buffers'][0]['byteLength'] = len(out)

chunk = json.dumps(gltf, separators=(',', ':')).encode()
chunk += b' ' * (-len(chunk) % 4)
with open(path, 'wb') as f:
    f.write(data[:8] + struct.pack('<I', 12 + 8 + len(chunk) + 8 + len(out)))
    f.write(struct.pack('<I', len(chunk)) + b'JSON' + chunk)
    f.write(struct.pack('<I', len(out)) + b'BIN\0' + bytes(out))
print(f'{path}: {len(data) / 1e6:.1f} MB -> {os.path.getsize(path) / 1e6:.1f} MB')
