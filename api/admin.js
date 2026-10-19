import { randomUUID } from 'node:crypto';
import { del } from '@vercel/blob';
import { readCatalog, writeCatalog, isAuthorized, json } from '../lib/catalog.js';

function unauthorized() {
  return json({ error: 'Contraseña incorrecta' }, 401);
}

export async function GET(request) {
  if (!isAuthorized(request.headers.get('x-admin-password'))) return unauthorized();
  const catalog = await readCatalog();
  return json(catalog.models, 200, { 'cache-control': 'no-store' });
}

export async function POST(request) {
  if (!isAuthorized(request.headers.get('x-admin-password'))) return unauthorized();

  const body = await request.json();
  const catalog = await readCatalog();
  const models = catalog.models;
  const index = models.findIndex((m) => m.id === body.id);

  switch (body.action) {
    case 'add': {
      if (!body.url || !body.name) return json({ error: 'Faltan datos' }, 400);
      models.push({
        id: randomUUID(),
        name: String(body.name).trim(),
        url: body.url,
        ...(body.iosUrl ? { iosUrl: body.iosUrl } : {}),
        visible: true,
        createdAt: new Date().toISOString(),
      });
      break;
    }
    case 'update': {
      if (index === -1) return json({ error: 'Modelo no encontrado' }, 404);
      if (typeof body.name === 'string' && body.name.trim()) models[index].name = body.name.trim();
      if (typeof body.visible === 'boolean') models[index].visible = body.visible;
      // iosUrl: string para asignar un .usdz, null para quitarlo
      if (body.iosUrl !== undefined) {
        const previous = models[index].iosUrl;
        if (previous && previous !== body.iosUrl) await del(previous).catch((err) => console.error(err));
        if (body.iosUrl) models[index].iosUrl = body.iosUrl;
        else delete models[index].iosUrl;
      }
      break;
    }
    case 'move': {
      if (index === -1) return json({ error: 'Modelo no encontrado' }, 404);
      const target = index + (body.direction === 'up' ? -1 : 1);
      if (target >= 0 && target < models.length) {
        [models[index], models[target]] = [models[target], models[index]];
      }
      break;
    }
    case 'delete': {
      if (index === -1) return json({ error: 'Modelo no encontrado' }, 404);
      const [removed] = models.splice(index, 1);
      await del([removed.url, removed.iosUrl].filter(Boolean)).catch((err) => console.error(err));
      break;
    }
    default:
      return json({ error: 'Acción desconocida' }, 400);
  }

  await writeCatalog(catalog);
  return json(models, 200, { 'cache-control': 'no-store' });
}
