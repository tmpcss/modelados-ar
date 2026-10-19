# Modelados

Web app para ver modelos 3D (.glb) en realidad aumentada desde el móvil, anclados al suelo.
Funciona en Android (WebXR / Scene Viewer) e iPhone (Quick Look) sin instalar nada.

- `/` — intro, menú de modelos, vista 3D y botón «Ver en tu espacio».
- `/admin.html` — panel para subir, renombrar, ordenar, ocultar y eliminar modelos.

## Estructura

```
index.html, admin.html     páginas
css/ js/                   interfaz (sin build)
api/models.js              catálogo público (GET)
api/admin.js               gestión del catálogo (requiere contraseña)
api/upload.js              tokens de subida directa a Vercel Blob
lib/catalog.js             lectura/escritura de catalog.json en Blob
models/                    modelos iniciales + catálogo local de respaldo
scripts/seed.mjs           sube los modelos iniciales a Blob
scripts/glb2usdz.py        convierte .glb a .usdz con animaciones (Blender)
scripts/usd2glb.py         convierte una escena .usd/.usdc a .glb centrada y a escala (Blender)
                           opciones: ancho=1.0  excluir=obj1,obj2  apoyar
```

## Despliegue

1. Sube la carpeta a un repositorio de GitHub.
2. En Vercel: **Add New → Project**, importa el repo. Framework preset: **Other**. Sin build command.
3. En el proyecto de Vercel: **Storage → Create → Blob**, con acceso **Public**, y conéctalo al proyecto
   (crea la variable `BLOB_READ_WRITE_TOKEN`).
4. **Settings → Environment Variables**: añade `ADMIN_PASSWORD` con la contraseña del panel.
5. Redespliega (Deployments → Redeploy) para que las variables tengan efecto.
6. Carga los 5 modelos iniciales desde tu ordenador:

   ```
   npm install
   npx vercel link
   npx vercel env pull .env.local
   npm run seed
   ```

   (O súbelos a mano desde `/admin.html`.)

## Probar en local

- Solo interfaz: `python3 -m http.server` y abre `http://localhost:8000`. Usa `models/catalog.json`.
- Con panel y API: `npx vercel dev` (necesita `.env.local` del paso 6).

La RA necesita HTTPS, así que para probarla en el móvil usa la URL de Vercel.

## Notas

- El menú junta dos fuentes: los modelos del panel (Vercel Blob) y los de `models/catalog.json`
  en el repo. Para añadir uno por git: copia el .glb (y .usdz) a `models/`, añádelo a
  `catalog.json` y haz push. Los del repo no se pueden ocultar ni borrar desde el panel.

- Si un .glb trae animación, se reproduce (la primera, en bucle) en la vista 3D y en RA en Android.
  Para que también se anime en iPhone, el modelo necesita un .usdz: súbelo junto al .glb en el panel
  o con «Añadir USDZ» en un modelo existente. Sin .usdz, Quick Look convierte el .glb al vuelo y lo
  muestra sin animación. Para generar el .usdz:

  ```
  /Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/glb2usdz.py -- modelo.glb modelo.usdz
  ```
- Hacer foto: en iPhone, con el botón de Quick Look; en Android, con la captura de pantalla del sistema.
