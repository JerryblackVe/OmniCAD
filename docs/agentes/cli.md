# La CLI `omnicad`

Todo el catálogo de herramientas desde la terminal. Sirve para agentes que no hablan MCP, para scripts y para probar a mano.
Es la misma API que usa el servidor MCP: lo que hace una herramienta acá lo hace igual en el MCP.

## Cómo se corre

| Forma | Comando |
|---|---|
| Comando instalado | `clon/.venv/Scripts/omnicad.exe` en Windows, `clon/.venv/bin/omnicad` en Linux y macOS (en estos ejemplos, `omnicad`) |
| Sin depender del PATH | `clon/.venv/Scripts/python.exe -m omnicad.cli` (Linux y macOS: `clon/.venv/bin/python -m omnicad.cli`) |

- `omnicad --version` y `omnicad --help` arrancan al instante: la API (que tarda unos 2 s) se carga solo cuando hace falta.
- Todo el texto de la ayuda y de los errores está en español.
- Los ejemplos de abajo se corrieron de verdad (rutas absolutas y alguna línea larga recortadas con `…`). La excepción está marcada: `dev`.

## Formato de salida

| Modo | Qué sale | Dónde |
|---|---|---|
| Corto (por defecto) | `OK <herramienta>` y el resultado resumido (se recorta a 1500 caracteres), `aviso: …` y `guardado: …` | stdout |
| Corto, con error | `ERROR [KIND] mensaje` y una línea `pista:` por cada pista | stderr |
| `--json` | EXACTAMENTE el dict de `api.llamar`, en una línea | stdout, también si hay error |

Los dos dicts posibles con `--json`:

```
{"ok": true, "result": {...}, "avisos": [...]}
{"ok": false, "error_kind": "INVALID_ARGUMENTS", "mensaje": "...", "pistas": ["..."]}
```

- Una herramienta que falla trae `error_kind` fijo y en inglés: decidí con él, no con el texto del mensaje.
- Un error de uso (herramienta que no existe, archivo inexistente, JSON mal escrito) sale como `error: …` en stderr, o con `--json` como `{"ok": false, "error_kind": "CLI_USAGE", ...}`.
- Las imágenes **nunca** salen en base64: se escriben a un PNG y el resultado trae `{"path", "format", "width", "height", "size_bytes"}`.

## Códigos de salida

| Código | Significa |
|---|---|
| 0 | salió bien |
| 1 | la herramienta devolvió un error del diseño (`ok: false`), o un paso de `dev check` falló |
| 2 | error de uso: argumentos, herramienta o archivo inexistente |

(Ctrl+C sale con 130.)

## Reglas de guardado

- `--doc archivo.omnicad` abre ese proyecto. Tiene que existir: para crearlo, `omnicad new`.
- Si la herramienta **modifica** y sale bien, el archivo se guarda de vuelta (de forma atómica) salvo con `--no-save`.
- Si la herramienta falla, el archivo no cambia.
- Sin `--doc`, la herramienta corre sobre un documento vacío y no se guarda nada.
- Cada `omnicad …` es un proceso nuevo: no hay sesión entre un comando y otro. El estado vive en el archivo. Para muchos pasos seguidos, usá `batch` (un solo proceso, mucho más rápido).

## Subcomandos

| Comando | Para qué |
|---|---|
| [`tools`](#tools) | listar las herramientas del catálogo |
| [`describe`](#describe) | ver una herramienta con todos sus parámetros |
| [`call`](#call) | llamar cualquier herramienta |
| [`new`](#new) | crear un proyecto vacío |
| [`info`](#info) | resumen de un proyecto |
| [`export`](#export) | exportar a STL, STEP, OBJ… |
| [`render`](#render) | sacar un PNG de una vista |
| [`run`](#run) | correr un script de Python sobre el proyecto |
| [`batch`](#batch) | correr muchos pasos en un solo proceso |
| [`dev`](#dev) | verificar el programa (para quien lo desarrolla) |

### tools

Lista nombre, grupo, si modifica (`M`) y la primera frase.

```
$ omnicad tools --group parametros
get_parameters    parametros  -  Lista los parámetros de usuario: expresión, valor calculado, unidad (mm o deg…
create_parameter  parametros  M  Crea un parámetro de usuario.
set_parameter     parametros  M  Cambia la expresión de un parámetro existente y recalcula el modelo.
delete_parameter  parametros  M  Borra un parámetro que no use ningún paso ni otro parámetro.

4 herramienta(s). M = modifica el documento. Detalle: omnicad describe <herramienta>
```

- `--group G` (`-g`): solo un grupo (`documento`, `parametros`, `boceto`, `vectores`, `solido`, `chapa`, `malla`, `ensamble`, `material`, `inspeccion`, `avanzado`, `grafo`, `dev`).
- `--json`: lista de `{nombre, grupo, modifica, descripcion}`.
- `--markdown`: el catálogo entero como Markdown. Así se genera [herramientas.md](herramientas.md). Se combina con `--output ruta.md` (`-o`), que escribe en UTF-8 con saltos `\n`. No se combina con `--group` ni `--json`.

### describe

La descripción completa de una herramienta y sus parámetros (tipo, obligatorio u opcional con su valor por defecto).

```
$ omnicad describe set_parameter
set_parameter  [parametros]  modifica el documento
Cambia la expresión de un parámetro existente y recalcula el modelo. Si algún paso queda con error,
el cambio se descarta.

parámetros:
  name  (string; obligatorio)
      nombre exacto del parámetro.
  expression  (number|string; obligatorio)
      valor nuevo: número (en la unidad del parámetro) o expresión, p. ej. "80 mm" o "ancho * 2".

Uso: omnicad call set_parameter --doc archivo.omnicad name=… expression=…
```

`--json` devuelve la entrada completa del catálogo, con el esquema JSON de los argumentos.

### call

Llama a una herramienta del catálogo. Es el comando principal.

Los argumentos se pasan de tres maneras, que se pueden mezclar (si se repiten, gana `clave=valor`):

- `clave=valor`: el valor se lee como JSON si se puede (números, listas, `true`, `false`); si no, es texto. Si el esquema pide texto, siempre es texto (`name=123` es el texto `"123"`).
- `--args '{"clave": valor}'`: un objeto JSON.
- `--args-file f.json`: el objeto JSON desde un archivo (`-` lee de la entrada estándar).

Otras opciones: `--doc archivo.omnicad`, `--no-save`, `--image-out ruta.png` (dónde escribir la imagen del resultado; si no, un temporal) y `--json`.

```
$ omnicad call create_parameter --doc pieza.omnicad name=ancho expression="60 mm"
OK create_parameter
{"name":"ancho","expression":"60 mm","value":60.0,"unit":"mm","kind":"length","comment":"","used_by":[]}
guardado: …\pieza.omnicad

$ omnicad call create_box --doc pieza.omnicad --args '{"length": "ancho", "width": 30, "height": 10}'
OK create_box
{"feature":{"id":"op1","name":"Caja1","type":"primitiva"},"bodies_created":[{"id":"op1.c1","name":"Cuerpo1","volume":18000.0}],"bodies_modified":[],"bodies_removed":[]}
guardado: …\pieza.omnicad
```

Un argumento que falta o está mal (salida 1):

```
$ omnicad call create_box --doc pieza.omnicad width=-5
ERROR [INVALID_ARGUMENTS] Faltan argumentos obligatorios de create_box: length, height.
  pista: Firma: create_box(length: number|string, width: number|string, height: number|string, x: number|string = 0, ...)
  pista: Revisá nombres y tipos de los argumentos contra el esquema de la herramienta.

$ omnicad call create_box --doc pieza.omnicad length=10 width=-5 height=10 --json
{"ok":false,"error_kind":"INVALID_ARGUMENTS","mensaje":"width tiene que ser positivo (recibió -5.0).","pistas":["Revisá nombres y tipos de los argumentos contra el esquema de la herramienta."]}
```

Una herramienta que no existe (salida 2), con sugerencia:

```
$ omnicad call create_boxx --doc pieza.omnicad
error: No existe la herramienta 'create_boxx'.
  pista: ¿Quisiste decir: create_box, create_hole, create_torus?
```

### new

Crea un proyecto `.omnicad` vacío (`new_document` + `save_document`).

```
$ omnicad new pieza.omnicad
OK new
{"path":"…\\pieza.omnicad","name":"pieza"}
```

- El documento se llama como el archivo (como en Fusion: guardar con otro nombre lo renombra).
- `--overwrite`: reemplazar el archivo si ya existe. Sin esto, si existe falla.

### info

Resumen del proyecto (`get_scene_info`): cuerpos con su volumen y su caja, y parámetros. No modifica el archivo.

```
$ omnicad info pieza.omnicad
OK get_scene_info
Soporte  (pieza.omnicad)
1 cuerpo(s), 0 boceto(s), 1 paso(s), 1 parámetro(s)
  cuerpo op1.c1 «Cuerpo1» solid  vol=18000.0 mm³  caja=60.0 x 30.0 x 10.0 mm
  param ancho = 60 mm  (60.0 mm)
```

`omnicad info pieza.omnicad --json` trae todo: ids, áreas, cajas con `min`, `max` y `size`, bocetos, pasos y parámetros con `used_by`.

### export

Exporta cuerpos (`export`); el formato sale de la extensión: `.stl`, `.obj`, `.3mf`, `.ply`, `.step`, `.stp`, `.iges`, `.igs`, `.brep`; `.dxf` exporta el patrón plano de un cuerpo de chapa.

```
$ omnicad export pieza.omnicad pieza.stl
OK export
{"path":"…\\pieza.stl","format":"stl","bodies":["op1.c1"],"size_bytes":684,"triangles":12}
```

- `--bodies CUERPO …` (`-b`): ids o nombres; por defecto, todos.
- `--overwrite`: reemplazar la salida si ya existe.

### render

Dibuja el modelo y escribe un PNG (`get_viewport_image`, render por software, sin abrir la ventana). Siempre un archivo: nunca base64.

```
$ omnicad render pieza.omnicad vista.png --view front --size 400x300
OK get_viewport_image
{"image":{"path":"…\\vista.png","format":"png","width":400,"height":300,"size_bytes":11548},"view":"front","bodies":["op1.c1"],"seconds":1.52}
```

- `--view V` (`-v`): `iso` (por defecto), `front`, `back`, `top`, `bottom`, `left` o `right`.
- `--size ANCHOxALTO` (`-s`): por defecto `800x600`.
- La salida tiene que terminar en `.png`. Para una dirección propia de cámara, usá `omnicad call get_viewport_image direction="[1,1.5,1]" --image-out vista.png`.
- Después de renderizar, **mirá la imagen**: es la forma de comprobar que el modelo es lo que se pidió.

### run

Corre un script de Python con `api`, `sesion`, `doc` y `llamar(nombre, args)` ya definidos (herramienta `execute_code`). Todo el script es un solo paso de deshacer; si lanza una excepción, el documento queda igual. `print` va a stdout y `result = …` devuelve un valor. `run` corre sin tiempo máximo (Ctrl+C lo corta).

`llamar` devuelve el dict completo (`{"ok": ..., "result": ...}`).

```
$ cat cambio.py
r = llamar("get_physical_properties")
print("volumen total =", r["result"]["total"]["volume"], "mm3")
result = {"cuerpos": len(doc.estado_final.cuerpos)}

$ omnicad run cambio.py --doc pieza.omnicad
OK execute_code
volumen total = 19570.7963 mm3
result = {"cuerpos":2}
aviso: Sin densidad (pasá density o asignale un material): Cuerpo1, Cuerpo2.
```

- Sin `--save` el archivo no se toca. `--save` lo guarda si el script salió bien (exige `--doc`).
- Sin `--doc`, el script corre sobre un documento vacío.
- Para un script que arma una pieza entera y la guarda, mirá [`soporte_l.py`](../../ejemplos/agentes/soporte_l.py).

### batch

Muchos pasos en un solo proceso (rápido: la API se carga una sola vez). Cada línea del archivo es `{"tool": "nombre", "args": {...}}`.

```
$ omnicad batch pasos.jsonl --doc pieza.omnicad
paso 1 (línea 1) OK create_cylinder
paso 2 (línea 2) OK get_physical_properties
guardado: …\pieza.omnicad
2 ok, 0 con error, de 2 paso(s).
```

- Al final se guarda el `--doc` UNA vez (si algún paso modificó).
- Si un paso falla, el batch **se detiene y no guarda nada** (salida 1). Con `--continue-on-error` sigue con los siguientes. Con `--no-save` no guarda.
- Una herramienta que no existe o una línea que no es JSON es un error de uso (salida 2) y no se ejecuta nada.
- Con `--json`, la salida es la lista de resultados de los pasos ejecutados.
- Sin `--doc` corre sobre un documento vacío y no guarda. Ejemplo completo: [`soporte_l.jsonl`](../../ejemplos/agentes/soporte_l.jsonl).

Un paso que falla:

```
$ omnicad batch malo.jsonl --doc pieza.omnicad
paso 1 (línea 1) ERROR [AMBIGUOUS_REFERENCE] fillet: Hay 2 cuerpos (Cuerpo1, Cuerpo2): con un selector hay que decir cuál (argumento body), o usar ids de find_faces / find_edges.
  pista: Hay más de uno con ese nombre: usá el id.
Se detuvo en el paso 1 de 1: NO se guardó nada.
0 ok, 1 con error, de 1 paso(s).
```

### dev

Verificación del programa, para quien lo desarrolla. Son las herramientas `run_checks`, `app_screenshot` y `run_bench` del grupo `dev` ([herramientas.md](herramientas.md#grupo-dev)): la misma fuente que usa el MCP con `--dev`.

> `dev check --json` se corrió el 2026-10-09 (ruff limpio, 1138 passed, humo TODO OK, salida 0). El formato de texto y el de `dev screenshot` salen de leer `clon/omnicad/cli/cmd_dev.py` y `clon/omnicad/api/herramientas_dev.py`.

**`omnicad dev check`**: corre ruff (`--select F,B023,B905`), pytest y la prueba de humo, cada uno en su subproceso con tiempo máximo (ruff 120 s, pytest 900 s, humo 600 s).

```
$ omnicad dev check
ruff    OK    <última línea de ruff>
pytest  OK    <resumen de pytest>
humo    OK    <línea «Resultado: …» de la prueba de humo>
OK: <segundos> s
```

- Un paso que falla muestra `FALLA` y debajo, las primeras líneas `FAILED …` de pytest o las `FALLA …` de la prueba de humo.
- `--no-smoke`: no corre la prueba de humo (no abre la ventana; más rápido).
- `--json`: `{"ok": true, "result": {"ok", "seconds", "ruff": {"ok", "summary"}, "pytest": {"ok", "summary", "failed"}, "smoke": {"ok", "summary", "failures"} o null}, "avisos": []}`.
- Salida: 0 si todo pasa, 1 si algún paso falla.
- No se puede anidar: si ya lo lanzó otro `run_checks`, devuelve el error `NESTED_CHECKS` (existe porque una cadena de pytest anidados llenó la memoria de la PC el 2026-10-09).
- Tarda minutos y usa bastante memoria: no lo corras en paralelo con otra suite.

**`omnicad dev screenshot salida.png`**: abre la ventana REAL de OmniCAD en otro proceso, la captura entera y la cierra. No toca tus preferencias ni tus proyectos recientes.

```
$ omnicad dev screenshot ventana.png --example --size 1600x900
OK captura …\ventana.png  1600x900  <bytes> bytes
```

- `--example`: abre el modelo de ejemplo. `--project ruta.omnicad`: abre ese proyecto (no se combinan).
- `--size ANCHOxALTO`: por defecto `1600x900`.
- `--theme NOMBRE`: tema de la interfaz: `oscuro_moderno` (el de fábrica), `claro_moderno`, `azul_profesional`, `minimalista`, `clasico` o `usuario:<archivo>` (un `.json` de la carpeta de temas). Un nombre que no existe falla con `INVALID_ARGUMENTS`.
- Necesita una pantalla con OpenGL: sin eso falla con `OPERATION_FAILED`.
- Salida: 0 si salió, 1 si falló la captura, 2 si el uso es inválido (la salida no es `.png`, el tamaño está mal, el proyecto no existe).

**`omnicad dev bench`**: mide el rendimiento con la ventana REAL en otro proceso (`python -m omnicad.ui.bench`): arranque, memoria, recálculo de un modelo grande (placa con 8×8 agujeros, 73 pasos) y cuadros por segundo al girar la vista. Repite la medición y da la mediana de cada número. Corrida real del 2026-10-09 (22 s):

```
$ omnicad dev bench
Mediana de 3 corrida(s):
  arranque         1.891 s  (importar: 0.896 s)
  memoria          479.5 MB al arrancar · 517.3 MB con el modelo · pico 531.7 MB
  modelo grande    73 pasos, 19196 triángulos
  recálculo        todo 0.945 s · último paso 0.029 s · cambiar un parámetro 1.056 s
  vista 3D         3.86 ms por cuadro (259.2 cuadros/s posibles) · 60.3 cuadros/s en pantalla
```

Desde el recálculo parcial (2026-10-09), la línea «recálculo» suma el tiempo de cambiar un parámetro que lee solo el último paso, p. ej. `(uno que usa solo el último paso: 0.051 s)`.

Desde el paso 4 de rendimiento (mallas en la placa de video, 2026-10-09), la vista 3D da `1.72 ms por cuadro` en esta misma PC, y hay una línea más, «de lejos»: el modelo a 1/12 de su tamaño en pantalla, con y sin menos detalle a la distancia, p. ej. `7480 triángulos, 1.34 ms por cuadro (sin menos detalle a la distancia: 17326 triángulos, 1.31 ms)`.

Desde el paso 5 de rendimiento (arranque rápido, 2026-10-09), el arranque da `1.92 s (importar: 0.93 s)` y la memoria `493 MB al arrancar` en esta misma PC (antes del paso, con la apertura de `.f3d` sumada: 2.34 s y 531 MB).

- `--repeticiones N` (1 a 10, defecto 3), `--lado N` (agujeros por lado, 1 a 20, defecto 8), `--cuadros N` (10 a 1000, defecto 120).
- «cuadros/s posibles» es el tiempo de dibujo puro (`paintGL` + `glFinish`); «en pantalla» queda limitado por la sincronía vertical del monitor.
- `--json` devuelve todos los números (también `ms_p95` y `mostrar_modelo_s`). Necesita pantalla con OpenGL.

### setup

Registra el MCP y copia la skill `omnicad` en Claude Code y OpenCode, e instala en Fusion 360 el complemento OmniCADPuente (opcional: los `.f3d`/`.f3z` se abren sin Fusion; el complemento es el respaldo y trae los parámetros). Detalle y rutas: [conectar.md](conectar.md).

```
$ omnicad setup --cliente todos
omnicad setup: PLAN, no se escribió nada. Para aplicarlo agregá --aplicar.
…
```

- Sin `--aplicar` solo muestra el plan. Con `--aplicar` escribe, respalda cada archivo con `.bak` y no borra otros servidores; correrlo dos veces no duplica.
- `--cliente claude-code | opencode | fusion | todos` (por defecto `todos`; con `todos`, Fusion solo si está instalado).
- `--inicio CARPETA`: usa otra carpeta como la del usuario (para pruebas; nunca toca la real).

## Recetas rápidas

| Quiero | Comando |
|---|---|
| Empezar una pieza | `omnicad new pieza.omnicad` |
| Muchos pasos de una vez | `omnicad batch pasos.jsonl --doc pieza.omnicad` |
| Cambiar una medida | `omnicad call set_parameter --doc pieza.omnicad name=ancho expression="80 mm"` |
| Ver cómo quedó | `omnicad render pieza.omnicad vista.png` y mirar el PNG |
| Medir | `omnicad call get_physical_properties --doc pieza.omnicad --json` |
| Entregar a impresión 3D | `omnicad export pieza.omnicad pieza.stl` |
| Saber qué parámetros tiene una herramienta | `omnicad describe <herramienta>` |
| Verificar un cambio al programa | `omnicad dev check` |

Guía de diseño (ciclo de trabajo, selectores, errores): [guia_diseno.md](guia_diseno.md).
