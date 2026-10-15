// Sube los modelos de /models a Vercel Blob y crea el catálogo inicial.
// Uso: vercel env pull .env.local && npm run seed
import { readFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { basename } from 'node:path';
import { put } from '@vercel/blob';
import { readCatalog, writeCatalog } from '../lib/catalog.js';

const local = JSON.parse(await readFile(new URL('../models/catalog.json', import.meta.url)));
const catalog = await readCatalog();

for (const item of local) {
  if (catalog.models.some((m) => m.name === item.name)) {
    console.log(`Ya existe: ${item.name}`);
    continue;
  }
  const file = await readFile(new URL(`../${item.url}`, import.meta.url));
  const blob = await put(`models/${basename(item.url)}`, file, {
    access: 'public',
    contentType: 'model/gltf-binary',
    addRandomSuffix: true,
  });
  catalog.models.push({
    id: randomUUID(),
    name: item.name,
    url: blob.url,
    visible: true,
    createdAt: new Date().toISOString(),
  });
  console.log(`Subido: ${item.name}`);
}

await writeCatalog(catalog);
console.log(`Catálogo con ${catalog.models.length} modelos.`);
