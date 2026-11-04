# Proceso de trabajo y estado de los modelos

Este documento explica cómo se preparan los modelos de esta web, por qué están como están y cómo
se trabaja en el proyecto. Sirve para retomar el trabajo, tanto a una persona como a una IA.
La estructura del código y el despliegue están en el [README](README.md).

## Cómo trabajamos

- **Idioma:** todo en español: conversación, mensajes de commit y comentarios del código.
- **Antes de subir a git, preguntar.** Quien diseña los modelos prueba los cambios en local y en
  el móvil, y solo con su aprobación se hace commit y `git push` a `main`. Vercel publica solo en
  https://modelados-ar.vercel.app.
- **Comprobar el despliegue** después de cada push: descargar el archivo de producción y
  comparar su tamaño con el local.
- **Originales:** llegan a `~/Desktop/Portal_RA/`, normalmente como `.glb` de unos 20–27 MB. Nunca se modifican: todo se genera aparte y se copia a `models/`.
- **Antes de dar algo por bueno:**
  - Hacer capturas del preview con Chrome sin ventana (ver «Herramientas»).
  - Medir la caja de la escena y la posición de la figura en Blender.
  - Comprobar que cada bucle termina como empieza.
  - Comprobar que el `.usdz` tiene las mismas animaciones que el `.glb`.
- **Caché del navegador:** si el móvil o el navegador muestran una versión anterior, recargar
  sin caché. Si el problema persiste, renombrar el archivo (por eso pasaron de `portal*` a
  `visitante1-3`).
- **La carpeta del proyecto termina en un espacio** (`Modelados `): las rutas en la terminal
  van siempre entre comillas.

## Modelos actuales

| Menú | Archivos | Original | En RA |
|---|---|---|---|
| Visitante 1 | `models/visitante1.glb` / `.usdz` | `visitante1_v2.glb` | Flota: punto más bajo a 2,5 m; borde delantero a 5 m del punto de colocación |
| Visitante 2 | `models/visitante2.glb` / `.usdz` | «Portal 07» (preparado antes con otra herramienta) | Flota: punto más bajo a 3 m, sobre el punto de colocación |
| Visitante 3 | `models/visitante3.glb` / `.usdz` | `portal_07.2_gato.glb` | En el suelo |

Decisiones que se mantienen en todos:
- **Sin nubes:** se quitaron los planos con material `m_nube`.
- **Una sola animación en el `.glb`:** model-viewer solo reproduce la primera, así que
  `usd2glb.py` las une todas en un bucle continuo.
- **Texturas en JPEG de 1024 px:** cada `.glb` queda en unos 5,5–6,6 MB, frente a 19–27 MB del
  original.
- **El preview no muestra el hueco bajo las figuras que flotan:** `cameraTarget` y
  `cameraOrbit` de `models/catalog.json` encuadran solo la escena.

### Visitante 1

- Figura con animación `idle` (8,3 s) delante de un portal sobre una escalera, y 12 objetos
  animados (16,7 s).
- El bucle dura 16,7 s y la figura repite su animación dos veces.
- Mira de frente al espectador.

Receta (`$S` = carpeta temporal):

```
B=/Applications/Blender.app/Contents/MacOS/Blender
$B -b -P scripts/usd2glb.py -- ~/Desktop/Portal_RA/visitante1_v2.glb $S/a.glb escala=1 elevar=2.5 bucle=Armature duracion=16.6667
# script puntual: Escena.z -= (2.674 + 5), y un nodo «ancla_delante» con la malla de «ancla» en z = 2·2.674 + 5
python3 scripts/optimizar_glb.py $S/b.glb 1024 85
python3 scripts/marcador.py $S/b.glb models/visitante1.glb 0.125 -6.651
$B -b -P scripts/glb2usdz.py -- models/visitante1.glb models/visitante1.usdz duracion=120 marcador=4 fps=12
```

Por qué `ancla_delante`: Quick Look y los visores centran la caja del modelo en el punto donde se
coloca. Las dos anclas invisibles forman una caja simétrica, y así la escena queda 5 m por
detrás de ese punto, en vez de encima del móvil. 2,674 m es la mitad de la profundidad de la
escena.

### Visitante 2

- Mujer sentada (8,33 s) con anillos y cilindros.
- Se partió del `.glb` que ya estaba en el repo y se hizo lo siguiente:
  - Se quitaron las nubes.
  - Se elevó con un ancla para que el punto más bajo quede a 3 m.
  - Se pasaron las texturas a JPEG de 1024 px con `optimizar_glb.py`.
  - Se añadió el marcador en `x=0.01 z=0.46`.
- Su `.usdz` se genera igual que el de Visitante 1: `duracion=120 marcador=4 fps=12`.

### Visitante 3 (gato)

- El gato solo se lame la pata, en un bucle de 18 s: el gato 3 veces y los anillos 2.
- Está girado −90° para que mire al espectador y apoyado sobre la esfera verde.
- No tiene marcador, porque no flota.
- Se descartó la versión `portal_07.3_gato` por estar mal exportada: venía girada 90°, con una
  escala de 1,0335 y con los pies deslizándose.

```
$B -b -P scripts/usd2glb.py -- ~/Desktop/Portal_RA/portal_07.2_gato.glb $S/gato.glb escala=1 \
  rotar=GLTF_created_0.001:z:-90 clip=GLTF_created_0.001:gato duracion=18 \
  bucle=GLTF_created_0.001,bola.002,bola,cilindro.005,cilindro.001,cilindro.002,cilindro.003,cilindro,Cylinder.003,Cylinder.001,Sphere.001,Sphere.004
python3 scripts/optimizar_glb.py $S/gato.glb
$B -b -P scripts/glb2usdz.py -- $S/gato.glb models/visitante3.usdz
```

## El marcador del suelo (Visitante 1 y 2)

Las figuras flotan, y cuesta encontrarlas al apuntar al suelo. Por eso debajo de cada una hay un
anillo blanco con una onda que se expande, al 10 % de opacidad. Lo crea `scripts/marcador.py`
con un material llamado `marcador`. Antes llevaba también una línea vertical de luz, pero se
quitó a petición de quien diseña los modelos.

- **Android (WebXR):** `js/app.js` espera el evento `object-placed`. Cuatro segundos después,
  desvanece el marcador en 0,5 s bajando la opacidad y también el brillo (emisivo), y ya no
  vuelve a aparecer.
- **iPhone (Quick Look):** allí no se ejecuta JavaScript ni se anima la opacidad. El `.usdz`
  encoge el marcador a 0 entre los 4 y los 4,5 s. Como Quick Look repite toda la línea de tiempo
  en bucle, esta se alarga a unos 2 minutos repitiendo la animación (`duracion=120`), y el
  marcador reaparece solo una vez en cada vuelta.

## Herramientas

- **Blender 4.1** sin ventana (`-b -P`):
  - `usd2glb.py` prepara la escena: escala, eleva, rota, une animaciones y ajusta los bucles.
    Las opciones están en la cabecera del script.
  - `glb2usdz.py` genera el `.usdz` para iPhone.
- **Python 3** para editar el `.glb` directamente (JSON y binario):
  - `optimizar_glb.py` (usa `sips` de macOS).
  - `marcador.py`.
  - Scripts puntuales para quitar nodos, mover la escena y añadir anclas.
- **Capturas del preview:** Chrome sin ventana con `--headless=new --use-angle=swiftshader
  --enable-unsafe-swiftshader --virtual-time-budget=30000 --screenshot`, abriendo una página
  local con `<model-viewer>`. Para ver una pose concreta: `autoplay`, y en el evento `load`,
  `pause()` y `currentTime = t`.
- Herramientas que no funcionan aquí:
  - `qlmanage` (vista previa de Quick Look) se queda colgado.
  - `npx gltf-transform` está bloqueado.

## Trampas conocidas

- **El importador de glTF de Blender solo deja activa la primera animación;** el resto quedan
  en pistas NLA y no se exportan. `usd2glb.py` ya activa la de cada objeto. Si faltan
  animaciones, revisa esto primero.
- **La duración de la escena importada no es fiable** (en Visitante 1 salía de 10,4 s en vez de
  16,7 s). Fíjala con `duracion=` para que `bucle=` no estire las animaciones.
- **Materiales sin sombreado (`KHR_materials_unlit`):** el exportador USD los deja sin color.
  `glb2usdz.py` los convierte a emisión.
- **Al editar el `.usdc` con `pxr`:** guardar sobre el mismo archivo no recupera el espacio de
  lo borrado, así que hay que exportarlo a un archivo nuevo.
- **Peso del `.usdz`:** el formato USD guarda una sola vez las mallas idénticas. Por eso el
  `.usdz` de Visitante 1 (8,1 MB) pesa más que su `.glb` (6,6 MB): sus anillos son parecidos
  pero no idénticos.

## Pendiente

- **iPhone (sin confirmar):** se reporta que en Visitante 1 y 2 la cámara se abre pero el
  modelo «no aparece». Lo más probable es que la figura quede por encima y por detrás de donde
  apunta la cámara. Además, los 4 s del marcador empiezan a contar al abrir el archivo, no al
  colocar el modelo, y puede haber desaparecido ya. Hay que confirmarlo mirando hacia arriba
  tras colocar. Posibles arreglos:
  - Mantener el marcador visible más tiempo solo en iPhone.
  - Acercar o bajar las figuras solo en iPhone.
