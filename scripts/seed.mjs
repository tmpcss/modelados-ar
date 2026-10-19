// Sube los modelos de /models a Vercel Blob y crea el catálogo inicial.
// Uso: vercel env pull .env.local && npm run seed
import { readFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { basename } from 'node:path';
import { put } from '@vercel/blob';
import { readCatalog, writeCatalog } from '../lib/catalog.js';

async function upload(path, contentType) {
  const file = await readFile(new URL(`../${path}`, import.meta.url));
  return put(`models/${basename(path)}`, file, { access: 'public', contentType, addRandomSuffix: true });
}

const local = JSON.parse(await readFile(new URL('../models/catalog.json', import.meta.url)));
const catalog = await readCatalog();

for (const item of local) {
  if (catalog.models.some((m) => m.name === item.name)) {
    console.log(`Ya existe: ${item.name}`);
    continue;
  }
  const blob = await upload(item.url, 'model/gltf-binary');
  const iosBlob = item.iosUrl ? await upload(item.iosUrl, 'model/vnd.usdz+zip') : null;
  catalog.models.push({
    id: randomUUID(),
    name: item.name,
    url: blob.url,
    ...(iosBlob ? { iosUrl: iosBlob.url } : {}),
    visible: true,
    createdAt: new Date().toISOString(),
  });
  console.log(`Subido: ${item.name}`);
}

await writeCatalog(catalog);
console.log(`Catálogo con ${catalog.models.length} modelos.`);
