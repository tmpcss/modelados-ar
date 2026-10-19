import { handleUpload } from '@vercel/blob/client';
import { isAuthorized, json } from '../lib/catalog.js';

// Emite tokens para que el navegador suba el .glb o .usdz directamente a Blob,
// sin pasar por el límite de tamaño de las funciones.
export async function POST(request) {
  const body = await request.json();
  try {
    const result = await handleUpload({
      body,
      request,
      onBeforeGenerateToken: async (pathname, clientPayload) => {
        if (!isAuthorized(clientPayload)) throw new Error('Contraseña incorrecta');
        if (!/\.(glb|usdz)$/i.test(pathname)) throw new Error('Solo se admiten archivos .glb o .usdz');
        return {
          allowedContentTypes: ['model/gltf-binary', 'model/vnd.usdz+zip', 'application/octet-stream'],
          maximumSizeInBytes: 100 * 1024 * 1024,
          addRandomSuffix: true,
        };
      },
    });
    return json(result);
  } catch (err) {
    return json({ error: err.message }, 400);
  }
}
