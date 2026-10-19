import { readCatalog, json } from '../lib/catalog.js';

// Catálogo público: solo modelos visibles, en el orden definido en el panel.
export async function GET() {
  try {
    const { models } = await readCatalog();
    const visible = models
      .filter((m) => m.visible)
      .map(({ id, name, url, iosUrl }) => ({ id, name, url, iosUrl }));
    return json(visible, 200, {
      'cache-control': 'public, s-maxage=10, stale-while-revalidate=60',
    });
  } catch (err) {
    console.error(err);
    return json({ error: 'No se pudo leer el catálogo' }, 500);
  }
}
