const screens = {
  intro: document.getElementById('intro'),
  menu: document.getElementById('menu'),
  viewer: document.getElementById('viewer'),
};
const list = document.getElementById('list');
const count = document.getElementById('count');
const menuStatus = document.getElementById('menu-status');
const mv = document.getElementById('mv');
const viewerTitle = document.getElementById('viewer-title');
const viewerNote = document.getElementById('viewer-note');
const progressFill = document.getElementById('progress-fill');

let models = [];

async function fetchList(source) {
  try {
    const res = await fetch(source, { cache: 'no-store' });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data)) return data;
    }
  } catch {}
  return null;
}

// El menú junta los modelos del panel (Vercel Blob) con los del repositorio (models/catalog.json).
// Si un nombre está en los dos, manda el del panel.
async function loadCatalog() {
  const [panel, repo] = await Promise.all([fetchList('/api/models'), fetchList('models/catalog.json')]);
  if (!panel && !repo) throw new Error('Sin catálogo');
  const names = new Set((panel || []).map((m) => m.name.toLowerCase()));
  return [...(panel || []), ...(repo || []).filter((m) => !names.has(m.name.toLowerCase()))];
}

function show(name) {
  for (const [key, el] of Object.entries(screens)) el.hidden = key !== name;
  window.scrollTo(0, 0);
}

function renderMenu() {
  list.replaceChildren(
    ...models.map((model, i) => {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = `#m/${encodeURIComponent(model.id)}`;

      const thumb = document.createElement('model-viewer');
      thumb.className = 'thumb';
      thumb.src = model.url;
      thumb.loading = 'lazy';
      thumb.setAttribute('interaction-prompt', 'none');
      thumb.setAttribute('camera-orbit', model.cameraOrbit || '30deg 75deg auto');
      if (model.cameraTarget) thumb.setAttribute('camera-target', model.cameraTarget);
      if (model.cameraOrbit) thumb.setAttribute('min-camera-orbit', 'auto auto 1m');
      thumb.setAttribute('aria-hidden', 'true');

      const index = document.createElement('span');
      index.className = 'index';
      index.textContent = String(i + 1).padStart(2, '0');

      const name = document.createElement('span');
      name.className = 'name';
      name.textContent = model.name;

      a.append(thumb, index, name);
      li.append(a);
      return li;
    })
  );
  count.textContent = models.length ? String(models.length) : '';
  menuStatus.textContent = models.length ? '' : 'Todavía no hay modelos disponibles.';
}

function openModel(id) {
  const model = models.find((m) => m.id === id);
  if (!model) return route('#menu');
  viewerTitle.textContent = model.name;
  viewerNote.hidden = true;
  if (mv.src !== new URL(model.url, location.href).href) mv.src = model.url;
  // Con un .usdz propio, Quick Look (iPhone) conserva las animaciones
  if (model.iosUrl) mv.setAttribute('ios-src', model.iosUrl);
  else mv.removeAttribute('ios-src');
  // Encuadre propio para escenas que flotan sobre el suelo (el hueco solo cuenta en RA)
  const framing = [
    ['camera-target', model.cameraTarget],
    ['camera-orbit', model.cameraOrbit],
    // Las anclas invisibles agrandan la caja del modelo y el visor alejaría la cámara
    ['min-camera-orbit', model.cameraOrbit && 'auto auto 1m'],
    ['max-camera-orbit', model.cameraOrbit && 'auto auto 60m'],
  ];
  for (const [attr, value] of framing) {
    if (value) mv.setAttribute(attr, value);
    else mv.removeAttribute(attr);
  }
  mv.alt = model.name;
  show('viewer');
}

function route(hash = location.hash) {
  if (hash !== location.hash) {
    location.hash = hash;
    return;
  }
  if (hash.startsWith('#m/')) openModel(decodeURIComponent(hash.slice(3)));
  else if (hash === '#menu') show('menu');
  else show('intro');
}

function note(text) {
  viewerNote.textContent = text;
  viewerNote.hidden = !text;
}

mv.addEventListener('progress', (e) => {
  progressFill.style.transform = `scaleX(${e.detail.totalProgress})`;
  progressFill.parentElement.classList.toggle('done', e.detail.totalProgress >= 1);
});

// Marcador del suelo (scripts/marcador.py): ayuda a encontrar las figuras que flotan.
// En RA de Android se ve unos segundos tras colocar el modelo y se desvanece para siempre.
// Quick Look no ejecuta este código: allí lo oculta la animación del propio .usdz.
const MARKER_MATERIALS = ['marcador'];
const MARKER_VISIBLE_MS = 4000;
const MARKER_FADE_MS = 500;
let markerTimer = null;

function fadeOutMarker() {
  const materials = (mv.model?.materials || []).filter((m) => MARKER_MATERIALS.includes(m.name));
  const from = materials.map((m) => [[...m.pbrMetallicRoughness.baseColorFactor], [...m.emissiveFactor]]);
  let start = null;
  const step = (now) => {
    start ??= now;
    const k = Math.min(1, Math.max(0, 1 - (now - start) / MARKER_FADE_MS));
    // El brillo (emisivo) se suma aunque la opacidad sea 0: se apagan los dos a la vez
    materials.forEach((m, i) => {
      const [[r, g, b, a], emissive] = from[i];
      m.pbrMetallicRoughness.setBaseColorFactor([r, g, b, a * k]);
      m.setEmissiveFactor(emissive.map((c) => c * k));
    });
    if (k > 0) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

mv.addEventListener('load', () => {
  clearTimeout(markerTimer);
  markerTimer = null;
  if (!mv.canActivateAR) note('Abre esta página en un móvil compatible para verlo en tu espacio.');
});

mv.addEventListener('ar-status', (e) => {
  if (e.detail.status === 'object-placed' && !markerTimer) {
    markerTimer = setTimeout(fadeOutMarker, MARKER_VISIBLE_MS);
  }
  if (e.detail.status === 'failed') {
    note('No se pudo detectar el suelo. Prueba con más luz o sobre una superficie con textura.');
  }
});

document.getElementById('start').addEventListener('click', () => route('#menu'));
window.addEventListener('hashchange', () => route());

try {
  models = await loadCatalog();
} catch {
  menuStatus.textContent = 'No se pudo cargar el catálogo.';
}
renderMenu();
route();
