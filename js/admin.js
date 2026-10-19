import { upload } from 'https://cdn.jsdelivr.net/npm/@vercel/blob@2.8.0/dist/client.js/+esm';

const loginScreen = document.getElementById('login');
const panelScreen = document.getElementById('panel');
const loginForm = document.getElementById('login-form');
const loginStatus = document.getElementById('login-status');
const passwordInput = document.getElementById('password');
const uploadForm = document.getElementById('upload-form');
const fileInput = document.getElementById('file');
const iosFileInput = document.getElementById('ios-file');
const rowIosFileInput = document.getElementById('row-ios-file');
const nameInput = document.getElementById('name');
const uploadButton = document.getElementById('upload-button');
const list = document.getElementById('admin-list');
const panelStatus = document.getElementById('panel-status');

const STORAGE_KEY = 'modelados-admin';
let password = '';

function readStored() {
  try { return sessionStorage.getItem(STORAGE_KEY) || ''; } catch { return ''; }
}

function store(value) {
  try {
    if (value) sessionStorage.setItem(STORAGE_KEY, value);
    else sessionStorage.removeItem(STORAGE_KEY);
  } catch {}
}

function setStatus(el, text, isError = false) {
  el.textContent = text;
  el.classList.toggle('error', isError);
}

async function api(method, body) {
  const res = await fetch('/api/admin', {
    method,
    headers: { 'content-type': 'application/json', 'x-admin-password': password },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) {
    logout();
    throw new Error('Sesión caducada');
  }
  if (!res.ok) throw new Error(data.error || 'Error del servidor');
  return data;
}

function render(models) {
  list.replaceChildren(
    ...models.map((model, i) => {
      const li = document.createElement('li');
      li.classList.toggle('is-hidden', !model.visible);

      const name = document.createElement('input');
      name.className = 'input';
      name.value = model.name;
      name.setAttribute('aria-label', 'Nombre');
      name.addEventListener('change', () => {
        if (name.value.trim()) act({ action: 'update', id: model.id, name: name.value });
      });
      name.addEventListener('keydown', (e) => { if (e.key === 'Enter') name.blur(); });

      const actions = document.createElement('div');
      actions.className = 'admin-actions';
      actions.append(
        button('↑', 'Subir en el orden', i === 0, () => act({ action: 'move', id: model.id, direction: 'up' })),
        button('↓', 'Bajar en el orden', i === models.length - 1, () => act({ action: 'move', id: model.id, direction: 'down' })),
        button(model.visible ? 'Ocultar' : 'Mostrar', null, false, () => act({ action: 'update', id: model.id, visible: !model.visible })),
        model.iosUrl
          ? button('Quitar USDZ', 'Quitar el archivo .usdz de iPhone', false, () => act({ action: 'update', id: model.id, iosUrl: null }))
          : button('Añadir USDZ', 'Añadir un archivo .usdz para iPhone', false, () => pickUsdz(model.id)),
        button('Eliminar', null, false, () => {
          if (confirm(`¿Eliminar «${model.name}»? No se puede deshacer.`)) act({ action: 'delete', id: model.id });
        }, 'danger'),
      );

      li.append(name, actions);
      return li;
    })
  );
  if (!models.length) setStatus(panelStatus, 'Todavía no hay modelos.');
}

function button(label, ariaLabel, disabled, onClick, extraClass = '') {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = `text-button ${extraClass}`.trim();
  b.textContent = label;
  if (ariaLabel) b.setAttribute('aria-label', ariaLabel);
  b.disabled = disabled;
  b.addEventListener('click', onClick);
  return b;
}

function uploadFile(file, contentType, label) {
  return upload(`models/${file.name}`, file, {
    access: 'public',
    handleUploadUrl: '/api/upload',
    clientPayload: password,
    contentType,
    onUploadProgress: ({ percentage }) => setStatus(panelStatus, `Subiendo ${label} ${Math.round(percentage)} %`),
  });
}

let usdzTarget = null;

function pickUsdz(id) {
  usdzTarget = id;
  rowIosFileInput.value = '';
  rowIosFileInput.click();
}

rowIosFileInput.addEventListener('change', async () => {
  const file = rowIosFileInput.files[0];
  if (!file || !usdzTarget) return;
  if (!/\.usdz$/i.test(file.name)) {
    setStatus(panelStatus, 'Selecciona un archivo .usdz', true);
    return;
  }
  try {
    const blob = await uploadFile(file, 'model/vnd.usdz+zip', '.usdz');
    await act({ action: 'update', id: usdzTarget, iosUrl: blob.url });
  } catch (err) {
    setStatus(panelStatus, err.message, true);
  }
});

async function act(body) {
  setStatus(panelStatus, 'Guardando…');
  try {
    render(await api('POST', body));
    setStatus(panelStatus, 'Guardado');
  } catch (err) {
    setStatus(panelStatus, err.message, true);
  }
}

async function enter(value) {
  password = value;
  const models = await api('GET');
  store(password);
  loginScreen.hidden = true;
  panelScreen.hidden = false;
  render(models);
}

function logout() {
  password = '';
  store('');
  panelScreen.hidden = true;
  loginScreen.hidden = false;
}

loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  setStatus(loginStatus, 'Comprobando…');
  try {
    await enter(passwordInput.value);
    setStatus(loginStatus, '');
    passwordInput.value = '';
  } catch (err) {
    setStatus(loginStatus, err.message === 'Sesión caducada' ? 'Contraseña incorrecta' : err.message, true);
  }
});

document.getElementById('logout').addEventListener('click', logout);

fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (file && !nameInput.value) {
    nameInput.value = file.name.replace(/\.glb$/i, '').replace(/[_-]+/g, ' ').trim();
  }
});

uploadForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const file = fileInput.files[0];
  if (!file || !/\.glb$/i.test(file.name)) {
    setStatus(panelStatus, 'Selecciona un archivo .glb', true);
    return;
  }
  const iosFile = iosFileInput.files[0];
  if (iosFile && !/\.usdz$/i.test(iosFile.name)) {
    setStatus(panelStatus, 'El archivo de iPhone debe ser .usdz', true);
    return;
  }
  uploadButton.disabled = true;
  try {
    const blob = await uploadFile(file, 'model/gltf-binary', '.glb');
    const iosBlob = iosFile ? await uploadFile(iosFile, 'model/vnd.usdz+zip', '.usdz') : null;
    render(await api('POST', { action: 'add', name: nameInput.value, url: blob.url, iosUrl: iosBlob?.url }));
    uploadForm.reset();
    setStatus(panelStatus, 'Modelo añadido');
  } catch (err) {
    setStatus(panelStatus, err.message, true);
  } finally {
    uploadButton.disabled = false;
  }
});

const saved = readStored();
if (saved) enter(saved).catch(() => logout());
