import { timingSafeEqual } from 'node:crypto';
import { get, put } from '@vercel/blob';

const CATALOG_PATH = 'catalog.json';

export async function readCatalog() {
  const result = await get(CATALOG_PATH, { access: 'public', useCache: false });
  if (!result || result.statusCode !== 200) return { models: [] };
  const text = await new Response(result.stream).text();
  return JSON.parse(text);
}

export async function writeCatalog(catalog) {
  await put(CATALOG_PATH, JSON.stringify(catalog), {
    access: 'public',
    contentType: 'application/json',
    addRandomSuffix: false,
    allowOverwrite: true,
    cacheControlMaxAge: 60,
  });
}

export function isAuthorized(password) {
  const expected = process.env.ADMIN_PASSWORD;
  if (!expected || typeof password !== 'string') return false;
  const a = Buffer.from(password);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

export function json(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'content-type': 'application/json', ...headers },
  });
}
