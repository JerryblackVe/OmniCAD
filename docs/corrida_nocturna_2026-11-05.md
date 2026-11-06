# Corrida nocturna del 2026-11-05

Pedido de Gerardo (2026-11-05, noche): que trabajen solos Qwen3.8-Flash (Qoder CLI, gratis) y GPT-6.1 Sol (OpenCode;
tiene un tope de 5 horas y puede no terminar). Una sesión de Claude (Opus 5, esfuerzo alto) hace de coordinador
nocturno: lanza, revisa, commitea lo verde y deja el informe para la mañana.

## Plan

| Línea | Quién | Dónde | Qué | Cómo se lanza |
|---|---|---|---|---|
| A | Qwen3.8-Flash en Qoder CLI | `main`, en `D:\PROGRAMA` | las 5 tandas de [arreglos_qwen.md](arreglos_qwen.md), en orden | `qodercli -p --dangerously-skip-permissions -m Qwen3.8-Flash -w D:/PROGRAMA "<texto>"` |
| B | GPT-6.1 Sol en OpenCode | rama `sol-geometria-nocturna`, worktree `D:\PROGRAMA-sol` | bugs de geometría difícil, uno por corrida: B-212, B-215, B-213, B-208 | `opencode run -m openai/gpt-6.1-sol --variant high "<texto>"` con la carpeta del worktree |

Las dos líneas corren en paralelo porque no comparten árbol de trabajo. Los comandos pesados de las dos pasan por
`scripts/turno.py`, que los pone en fila en toda la PC. La rama de Sol **no se fusiona de noche**: la revisa y la
fusiona el coordinador de día, con el «sí» de Gerardo.

### Texto para Qwen (línea A), una vez por tanda

```
TANDA = <N>
Leé docs/arreglos_qwen.md y seguí al pie de la letra la sección «## Prompt para el agente» (el bloque de texto completo) para esa tanda.
```

### Texto para Sol (línea B), una vez por bug

```
BUG = <ID>
ANTES DE TODO: invocá las skills /fable-method y /ponytail (y /plan-then-do, /tool-calling-guard, /verify-before-commit); al final /ponytail-review. Si no existen, seguí igual: el cambio más chico que arregla el bug entero, sin dependencias nuevas, leé antes de editar, nunca "listo" sin la salida real.
PROYECTO: OmniCAD, CAD 3D paramétrico en Python + OpenCascade que copia Fusion 360. Estás en un worktree de git (rama sol-geometria-nocturna); el código está en clon/. Leé AGENTS.md. Todo en español; mm y grados.
QUÉ: arreglá BUG. Detalle en docs/seguimiento/bugs.md (fila y sección «Detalle»: causa probable con archivo:línea, cómo reproducir y prueba propuesta) y en el informe de la auditoría que lo encontró (docs/auditoria_revolucion_barrido_solevacion.md o docs/auditoria_nervio_red_repujado.md). Antes de decidir el comportamiento, leé la ayuda de Fusion: D:/PROGRAMA/clon/.venv/Scripts/python.exe scripts/fusion_docs.py buscar <palabras> -s fusion-model (o -s fusion-patch), y ver "<título>" -s <carpeta>.
REGLAS: (1) test de la «Prueba propuesta» primero, con su salida en rojo; después el arreglo y la salida en verde. (2) Buscá los gemelos antes de editar: la previa (ui/comando.py, nucleo/previa*), la versión de superficie (nucleo/superficies.py, timeline/ops_superficie.py), OmniKernel (nucleo/omnikernel/) y la API (clon/omnicad/api/); listalos en el informe. (3) Tests: los del área MÁS todos los que salen de grep -l "<función que tocaste>" clon/tests/test_*.py; desde clon/: D:/PROGRAMA/clon/.venv/Scripts/python.exe ../scripts/turno.py -- D:/PROGRAMA/clon/.venv/Scripts/python.exe -m pytest <archivos> -q -p no:cacheprovider, en grupos de menos de 900 s. (4) Arreglá lo que marque tu /ponytail-review. (5) Si OpenCascade no sale en dos intentos, pará y dejá la fila en «Parcial» con lo que falta. (6) No commitees, no hagas git stash, checkout ni reset; no corras la suite completa ni la prueba de humo.
AL RESOLVER: borrá la fila de bugs.md, su «Detalle» y su ID en docs/seguimiento/README.md; viñeta en «## Registro» de PROJECT_LOG.md: «2026-11-05 · BUG (OpenCode con GPT-6.1 Sol, noche)».
INFORME: en docs/corrida_nocturna_2026-11-05.md, sección «## Informe Sol · BUG» arriba de «## Prompt para el agente»: estado, ayuda de Fusion, cambios (archivo:línea), gemelos, test rojo y verde, salida de ruff y de los grupos de tests, salida completa de /ponytail-review, ⚠ lo no verificado.
```

## Informe Sol · B-212

**Estado: resuelto en `sol-geometria-nocturna`, sin commit.** El caso de la auditoría produce ahora un sólido
válido y estanco de **2333,333333 mm³**, con caja (−10, −10, 0) → (10, 10, 10). El primer intento de arreglo
pasó la regresión; no fue necesario un segundo intento de OpenCascade. Siete casos de regresión y todos los
consumidores encontrados están en verde: **598 passed, 1 skipped** en tres grupos, más la verificación documental
indicada debajo. Sin dependencias nuevas.

### Ayuda de Fusion y decisión

Se ejecutó `D:/PROGRAMA/clon/.venv/Scripts/python.exe scripts/fusion_docs.py buscar Loft -s fusion-model`
y `... scripts/fusion_docs.py ver "Loft reference" -s fusion-model`, desde `D:\PROGRAMA`.
El intento inicial desde el worktree respondió `Falta el índice: correr primero fusion_docs.py construir`:
`docs/fusion_docs/` está fuera de git. Se leyó la copia existente sin reconstruirla ni copiarla.

Artículo: `D:/PROGRAMA/docs/fusion_docs/contenido/fusion-model/loft-reference-8029ab6fc24.md`, apartados
**Guide Type** y **Closed profiles with matching corners**. Dice «Rails must intersect each section, and must
terminate on or beyond the first and last sections» y que Fusion empareja las esquinas correspondientes.
Los cuadrados de la reproducción cumplen ambas condiciones. La cuenta independiente es
`10/3 × (100 + 400 + √(100×400)) = 2333,333333 mm³`; el lateral mide `60√125 = 670,820393 mm²`.

INTENT: el código falla al cerrar con `MakePipeShell` los perfiles con esquinas; la prueba exige un tronco válido de 2333,33 mm³; la ayuda de Fusion exige que el carril toque cada sección y que las esquinas correspondientes se conserven.

### Cambios y firmas

- `clon/omnicad/nucleo/solidos_crear.py:1282`, firma pública conservada:
  `solevar(secciones, *, carriles=(), linea_central=None, cerrada=False, solido=True, reglada=False, condicion_inicio=None, condicion_fin=None, fusionar_tangentes=False, condiciones_medias=None)`.
  Con carril usa las secciones intermedias del camino de superficie y valida el resultado como antes;
  `:1324-1326` reemplaza la guía de contacto de `MakePipeShell`. Línea central sigue con su constructor anterior.
  `:1309-1310` rechaza mezclar ambas guías también en llamadas directas al núcleo. Se quitó el import de contacto sin usos.
- `clon/omnicad/nucleo/superficies.py:1032`, helper privado:
  `_solevar_con_rieles(secs, rieles, inicio=None, fin=None, medias=None, cerrada=False, exacta=False, *, solido=False)`.
  Solo se agregó el argumento nombrado `solido`; en `:1199`, `ThruSections(solido, False)` cierra con las mismas
  secciones reconstruidas. Los consumidores de superficie conservan `False` por defecto.
- `clon/tests/test_sol09_solevacion.py:38-110`: siete casos B-212. API con carril en ambos sentidos; núcleo
  como superficie y sólido (área, volumen, tipo y estanqueidad); carril curvo (volumen 1000 y corte intermedio
  con x −2..8); error si el carril no toca el perfil; error si se mezclan guías.
- `docs/seguimiento/bugs.md`: borradas fila y ficha de B-212. Cabecera recontada: **27 = 20 abiertos + 6
  parciales + 1 bloqueado**; la cabecera anterior omitía filas del recuento. `docs/seguimiento/README.md` no
  contenía B-212, por lo que no había un ID que retirar allí. Se conserva el prompt del coordinador.
- `PROJECT_LOG.md`: entrada en Registro con la fecha/modelo pedidos y una lección respaldada por el rojo/verde.

### Gemelos y consumidores revisados

TWINS: searched `BRepFill_ContactOnBorder` and the `solevar` / `solevacion` flow - found 0 other sites with that solid-loft contact mode; related paths are listed below.

| Camino | Evidencia y conclusión |
|---|---|
| Previa | `ui/comando.py:1515-1574` construye la operación y llama `Documento.previsualizar` (`timeline/documento.py:1064`); termina en el mismo `OpSolevacion.ejecutar`. No hay copia geométrica específica de solevación ni archivos `nucleo/previa*` en este árbol. Revisión por código; no se probó el gesto real de previa. |
| Timeline sólido | `timeline/ops_solido.py:222-244`: resuelve secciones y carriles, llama `solevar` y aplica el resultado. Lo cubre la regresión por API. |
| Superficie | `nucleo/superficies.py:1247-1325` → `_solevar_con_rieles`; `timeline/ops_superficie.py:280-293`; `api/herramientas_superficie.py:234-272`. Misma interpolación, abierta por defecto; 203 tests del grupo de superficie verdes. |
| OmniKernel | `nucleo/omnikernel/solidos_crear.py` no implementa `solevar`; `nucleo/omnikernel/superficies.py` declara operaciones pendientes. `nucleo/motor.py:107-154` mantiene el despacho MOTOR_SIN_SOPORTE para operaciones OCC sin adaptador. Inspeccionado, no ejecutado en esta corrida. |
| API/MCP/CLI | `api/herramientas_solido.py:548-620` traduce `loft` al paso; ya rechaza rails + center_line. No duplica el cálculo. El test rojo/verde entra por esta API real. |
| Barrido | `solidos_crear._barrido_alambre` y `superficies.barrer_superficie` usan sus propios modos de `MakePipeShell`, sin el modo de contacto de esta solevación. Sus bugs B-208/B-209 siguen fuera de B-212. |

Búsqueda literal de consumidores, desde la raíz (también incluye el inicializador cuyo import se limpió):

```console
grep -l -E 'solevar|_solevar_con_rieles|_iniciar_opencascade' clon/tests/test_*.py
clon/tests/test_herramientas_solido.py
clon/tests/test_render.py
clon/tests/test_render_rapido.py
clon/tests/test_sol09_solevacion.py
clon/tests/test_solidos_crear.py
clon/tests/test_superficie_guias.py
clon/tests/test_superficies.py
```

Todos están en los grupos de abajo. La verificación de importación, desde `clon/`, devolvió
`D:\PROGRAMA-sol\clon\omnicad\__init__.py`: los tests usan el worktree, no el código de `main`.

### Test rojo y verde reales

Antes del arreglo se agregó y ejecutó primero la prueba propuesta por API. Comando desde `clon/`:

```console
D:/PROGRAMA/clon/.venv/Scripts/python.exe ../scripts/turno.py -- D:/PROGRAMA/clon/.venv/Scripts/python.exe -m pytest tests/test_sol09_solevacion.py -k b212 -q -p no:cacheprovider
```

Salida roja (extracto literal; pytest abrevia el diccionario del error):

```console
F                                                                        [100%]
____ test_b212_carril_recto_conserva_las_esquinas_y_el_volumen_del_tronco _____
>       llamar(s, "loft", sketches=["Base", "Tapa"], rails=[{"sketch": "Carril", "curve": curva}])
>       assert r["ok"], r
E       assert False
FAILED tests/test_sol09_solevacion.py::test_b212_carril_recto_conserva_las_esquinas_y_el_volumen_del_tronco
1 failed, 11 deselected in 2.45s
```

El diccionario observado tenía `ok=False`, `error_kind='OPERATION_FAILED'`. Tras el cambio, el mismo comando:

```console
.                                                                        [100%]
1 passed, 11 deselected in 2.41s
```

Luego se amplió a los siete casos descritos, sin cambiar el volumen ni aflojar tolerancias.

### Ruff y grupos de tests

Ruff, desde `clon/`: `D:/PROGRAMA/clon/.venv/Scripts/python.exe -m ruff check .`

```console
All checks passed!
```

Los tres grupos usan este prefijo y sufijo exactos desde `clon/`:
`D:/PROGRAMA/clon/.venv/Scripts/python.exe ../scripts/turno.py -- D:/PROGRAMA/clon/.venv/Scripts/python.exe -m pytest <archivos> -q -p no:cacheprovider`.
Se ejecutaron de a uno, con salida 0, todos por debajo de 900 s.

**Grupo 1:** `tests/test_sol09_solevacion.py tests/test_solidos_crear.py tests/test_api_solido.py tests/test_api_opciones_solido2.py`

```console
........................................................................ [ 44%]
........................................................................ [ 88%]
..................                                                       [100%]
162 passed in 40.55s
```

**Grupo 2:** `tests/test_superficie_guias.py tests/test_superficies.py tests/test_api_superficie.py tests/test_superficie_fusion.py tests/test_comandos_superficie.py`

```console
........................................................................ [ 35%]
........................................................................ [ 70%]
...........................................................              [100%]
203 passed in 20.81s
```

**Grupo 3:** `tests/test_herramientas_solido.py tests/test_render.py tests/test_render_rapido.py tests/test_comandos_crear.py tests/test_resultados_vacios.py`

```console
........................................................................ [ 30%]
........................................................................ [ 61%]
..............................s......................................... [ 92%]
..................                                                       [100%]
233 passed, 1 skipped in 125.93s (0:02:05)
```

**Grupo 4 (documentación):** `tests/test_seguimiento.py tests/test_doc_agentes.py`.
La primera pasada encontró un fallo del informe, no del núcleo:

```console
_________ test_cada_prompt_guardado_esta_en_la_tabla_y_se_puede_leer __________
>       assert all("fable-method" in p["texto"] and "esfuerzo" in p["modelo"] for p in guardados)
E       assert False
FAILED tests/test_seguimiento.py::test_cada_prompt_guardado_esta_en_la_tabla_y_se_puede_leer
1 failed, 449 passed in 6.77s
```

`scripts/seguimiento_json.py:66-67` parte desde la primera mención del encabezado y lee el primer bloque
`text`. Una mención anterior del encabezado en el texto para Sol hacía que eligiera un bloque de comandos del
informe nuevo. Se marcaron las salidas como `console`, conservando el prompt del coordinador y el extractor.
Ruff y ambos archivos se repitieron:

```console
All checks passed!
........................................................................ [ 16%]
........................................................................ [ 32%]
........................................................................ [ 48%]
........................................................................ [ 64%]
........................................................................ [ 80%]
........................................................................ [ 96%]
..................                                                       [100%]
450 passed in 6.48s
```

Total final de los cuatro grupos: **1048 passed, 1 skipped**. También se restauraron los finales CRLF
de `superficies.py` con `scripts/restaurar_finales_de_linea.py`; `PROJECT_LOG.md` conservó los suyos.
La última repetición del grupo documental dio `450 passed in 7.74s`, con ruff limpio.
`git diff --check` sin opciones señaló los tres CRLF nuevos como espacio final; se verificó conservando
el formato original con `git -c core.whitespace=cr-at-eol diff --check` (sin salida, código 0), sin cambiar
la configuración de git. El diff final contiene solo los seis archivos declarados en este informe.

### Salida completa de /ponytail-review

What this change does: Solid lofts with a rail now use the existing surface-loft sections. The same
OpenCascade builder adds their end caps. Assumed load: one person or agent working on one CAD document.

**Should fix**

1. **The new core guard needs its own test** (`clon/omnicad/nucleo/solidos_crear.py:1309-1310`).
   - **What this is:** Direct core calls now reject a rail together with a centerline.
   - **Problem:** The old API test rejects that input before reaching the core. It does not test this new guard.
   - **Fix:** Add a direct core call with both guides and require the clear geometry error.
   - **If we skip it:** This guard could disappear while the API test stays green.
2. **The docstring promises exact curves on a sampled path** (`clon/omnicad/nucleo/solidos_crear.py:1295-1299`).
   - **What this is:** The reused helper samples curved profiles and rails before fitting the sections.
   - **Problem:** The previous blanket claim that circular edges are analytic is too strong for this new path.
   - **Fix:** State the sampling limit and say analytic shapes are recovered only within the canonicalization tolerance.
   - **If we skip it:** A caller may rely on an exact circle where the result is a fitted curve.

Verdict: fix 1 and 2 first.
Not checked: the live preview gesture, a large rail-loft performance benchmark, Fusion itself, and OmniKernel execution.

Revisión adicional del informe, tras ejecutar el grupo documental:

**Must fix**

3. **Evidence blocks are read as the saved agent prompt** (`docs/corrida_nocturna_2026-11-05.md`, bloques del informe).
   - **What this is:** The prompt extractor reads the first `text` block after its heading marker.
   - **Problem:** An earlier quoted marker makes it read the new evidence block. The tracking test fails.
   - **Fix:** Mark terminal output as `console` and keep the actual prompt as `text`.
   - **If we skip it:** The saved prompt contains a test command instead of the coordinator instructions.

Verdict: fix 3 before closing the report.

**Aplicación y relectura:** 1 corregido en `test_b212_nucleo_no_mezcla_carril_y_linea_central`; 2 corregido en el
docstring citado. El grupo 1 final volvió a pasar completo después de ambos cambios. El carril curvo también
tiene una prueba numérica del corte intermedio, para que ignorar el carril no pueda dar verde. Los errores
siguen llegando por `geo.ErrorGeometria` y la transacción de la API; no se agregan escrituras ni dependencias.
El argumento nuevo del helper es nombrado y por defecto falso: sus dos consumidores están revisados y el grupo
de superficie conserva el verde. El hallazgo 3 quedó corregido y el grupo 4 pasó: 450 aprobados.
Revisión final: sin hallazgos pendientes; **Verdict: Ship.**

### ⚠ Lo no verificado y límites

- No se ejecutaron la suite completa ni la prueba de humo, por pedido. No se abrió Fusion real ni se probó
  la interacción del panel en una ventana; la previa se trazó por código y los comandos existentes pasaron sus tests.
- La única omisión observada está en `test_render.py` (rama sin OpenGL de `:420`); no cuenta como test aprobado.
- No se ejecutó OmniKernel: no hay implementación de esta solevación en sus adaptadores. B-189 sigue abierto.
- No hay un banco de rendimiento con muchas secciones. Se reutilizan las 721 muestras por perfil y seis pasos
  por tramo del helper existente; perfiles/carriles curvos quedan aproximados, como en superficie.
- Se mantienen los límites sólidos anteriores: un solo carril, sin combinarlo con condiciones de borde ni
  solevación cerrada. No se evaluaron perfiles con agujeros guiados ni tolerancias extremas de curvas.
- Sin type-check configurado en `clon/pyproject.toml`; no se construyó un instalador. No se crearon archivos
  temporales de prueba ni se tocó el índice de git.

## Informe Sol · B-215

**Estado: resuelto en `sol-geometria-nocturna`, sin commit.** La prueba propuesta de la escuadra produce un
solo sólido válido: **26532,431377 mm³ con −1°**, **26839,640519 mm³ con +1° y extracción XY o Z**.
El control de +5° con extracción por defecto conserva **27539,891170 mm³**. Son 14 regresiones nuevas y
**1590 tests aprobados** en cuatro grupos completos de área/consumidores. El primer arreglo de OpenCascade
pasó la prueba propuesta; no se necesitó otro intento de geometría ni dependencias nuevas.

### Ayuda de Fusion y decisión

Desde `D:/PROGRAMA`, con `D:/PROGRAMA/clon/.venv/Scripts/python.exe`:

```console
scripts/fusion_docs.py buscar Rib -s fusion-model
scripts/fusion_docs.py ver "Rib reference" -s fusion-model
scripts/fusion_docs.py ver "Create a rib" -s fusion-model
```

Leídos `docs/fusion_docs/contenido/fusion-model/rib-reference-74df3f99244.md` y
`create-a-rib-b1cf2b2623b.md` de esa copia local; mirada la ilustración `recursos/34082c91a878d5eec1ea.png`.
La referencia admite **Draft Angle** y **Draft Pull Direction**: «Select a face or plane to define the pull
direction». El procedimiento confirma que se aplican al nervio. La ayuda no precisa el plano donde conserva
el grosor: se mantiene el plano neutro existente, normal a la extracción y por el punto medio de la curva.

INTENT: el código desmoldea el prisma auxiliar antes de recortarlo; la prueba exige un nervio válido con −1° y con extracción Z; la ayuda de Fusion admite ángulo de desmoldeo y una cara o plano para definir la extracción.

La pared auxiliar se extiende mucho más allá del cuerpo: un ángulo que es viable en el nervio final puede
cruzar sus caras fuera de él y hacer fallar `DraftAngle`. El arreglo recorta primero y conserva como candidatos
solo los laterales originales que sobrevivieron. Así no inclina las caras nuevas de apoyo en x = 5 y z = 5.
No se cambió el filtro por normal ni la orientación forzada de extracción: no fueron necesarios para la
prueba propuesta. La conjetura inicial de la auditoría sobre ese filtro no era la causa completa.

Cuenta independiente: triángulo 30 × 40 / 2 = 600 mm², espesor 2 mm. La profundidad media hasta la diagonal
es 8 mm; hasta el plano z = 25 es 20/3 mm. Por tanto, el aumento es `1200 + 9600·tan(ángulo)` con extracción
por defecto y `1200 + 8000·tan(ángulo)` con extracción Z. La base mide 25500 mm³.

### Cambios (firmas y líneas)

- `clon/omnicad/nucleo/solidos_crear.py:1414-1430`: helper privado
  `_desmoldear_pared(bruto, direccion, angulo, origen, *, recortado)`.
  Selecciona laterales en el bruto y los reconoce en el recorte con `_cara_dentro_de` existente; desmoldea
  solo ese recorte. Se reutilizan la validación y los errores de `solidos_modificar.desmoldeo`.
- `:1433-1467`: firma pública conservada
  `nervio(cuerpo, aristas_curva, normal_plano, espesor, *, profundidad=None, direccion="simetrica", invertir=False, extender=True, angulo_desmoldeo=0.0, direccion_desmoldeo=None)`.
  Recorta antes del desmoldeo y entrega ambos sólidos al helper. Docstring precisa signo y plano neutro.
- `:1470-1500`: firma pública conservada
  `red(cuerpo, aristas_curvas, normal_plano, espesor, profundidad=None, *, direccion="simetrica", invertir=False, extender=True, angulo_desmoldeo=0.0)`.
  Mismo orden para el gemelo; sin ángulo devuelve el recorte como antes.
- `clon/tests/test_sol10_nervio_red.py:55-70,93-117`: 12 casos de Nervio (−1° por defecto, +1° con XY y Z,
  +5° por defecto, cada uno simétrico y a ambos lados), Red negativa por API y Red curva por núcleo. Verifican
  volumen, validez, un solo sólido y dos laterales cónicos en la curva. Los 10 tests anteriores siguen pasando.
- `docs/seguimiento/bugs.md`: borradas fila y ficha; cabecera **26 = 19 abiertos + 6 parciales + 1 bloqueado**.
  `docs/seguimiento/README.md` no tenía B-215: no había un ID que retirar allí.
- `PROJECT_LOG.md`: Registro con fecha/modelo pedidos y lección respaldada por el rojo/verde.

### Gemelos y consumidores

TWINS: searched `_desmoldear_pared(` and draft-before-trim in `nervio` / `red` - found 1 other site: `red` in `clon/omnicad/nucleo/solidos_crear.py`; fixed with the same helper.

| Camino | Evidencia y conclusión |
|---|---|
| Previa | `ui/comando.py:1515-1574` → `Documento.previsualizar` (`timeline/documento.py:1064-1127`) → `OpNervio`/`OpRed`. El atajo `ui/comando.py:1591-1599` solo vale para extrusión. No hay archivos `nucleo/previa*`. Comparte el arreglo; el gesto del panel no se ejecutó. |
| Timeline | `timeline/ops_solido.py:260-271,279-289` pasa ángulo y dirección al núcleo. La API real de los tests recorre este camino y une el nervio al cuerpo. |
| Superficie | Búsqueda en `nucleo/superficies.py` y `timeline/ops_superficie.py`: no tienen Nervio, Red ni una copia de este desmoldeo. La auditoría de Fusion confirma que esas herramientas no están en SUPERFICIE. |
| OmniKernel | `nucleo/omnikernel/solidos_crear.py` no implementa Nervio ni Red; `omnikernel/superficies.py` solo declara pendientes. `omnikernel/solidos_modificar.py:89-103` tiene el desmoldeo genérico, sin este prisma auxiliar. `motor.py:107-154` informa falta de soporte de las operaciones sin adaptador. Inspección, sin ejecutarlo. |
| API/MCP/CLI | `api/herramientas_solido_extra.py:161-227` valida −45..45 y traduce a `OpNervio`/`OpRed`; no duplica geometría. API, previa y aceptación consumen el mismo núcleo. |
| Desmoldeo genérico | `solidos_modificar.py:1158-1217` conserva su constructor y validación; `_cara_dentro_de` de `:1220-1225` ya identifica caras procedentes de un corte en ese módulo. No se modificó. |

Búsqueda literal por símbolos, desde la raíz:

```console
grep -l -E '_desmoldear_pared|\bnervio\b|\bred\b' clon/tests/test_*.py
```

Devolvió 32 archivos, todos incluidos en los grupos siguientes. Se conservaron incluso las coincidencias
de `red` ajenas a geometría (asistentes, colores). Se agregaron `test_api_solido.py` y `test_comandos_crear.py`
por el área. Se comprobó la importación desde `clon/`: `D:\PROGRAMA-sol\clon\omnicad\__init__.py`.

### Rojo y verde reales

Primero se agregaron solo −1° por defecto, +1° con XY y +1° con Z y se ejecutaron antes de tocar el núcleo:

```console
D:/PROGRAMA/clon/.venv/Scripts/python.exe ../scripts/turno.py -- D:/PROGRAMA/clon/.venv/Scripts/python.exe -m pytest tests/test_sol10_nervio_red.py -k b215 -q -p no:cacheprovider
FFF                                                                      [100%]
E       AssertionError: {'ok': False, 'error_kind': 'OPERATION_FAILED', ...}
FAILED tests/test_sol10_nervio_red.py::test_b215_nervio_diagonal_con_desmoldeo_negativo_o_extraccion_z[-1-None]
FAILED tests/test_sol10_nervio_red.py::test_b215_nervio_diagonal_con_desmoldeo_negativo_o_extraccion_z[1-XY]
FAILED tests/test_sol10_nervio_red.py::test_b215_nervio_diagonal_con_desmoldeo_negativo_o_extraccion_z[1-Z]
3 failed, 10 deselected in 1.89s
```

Tras el arreglo, archivo completo (mismo prefijo, sin `-k b215`):

```console
.............                                                            [100%]
13 passed in 3.14s
```

Después se amplió a 14 regresiones. La primera prueba de Red curva tenía solo un piso: B-213 recortaba
el nervio entero contra su caja. Salida real: `Red: la curva queda dentro del cuerpo`,
`1 failed, 23 passed in 4.38s`. Se agregó una pared alta a la **pieza de prueba**, sin cambiar el núcleo.
El caso curva pasó (`1 passed, 23 deselected in 1.72s`) y el grupo 1 de abajo pasó el archivo final completo.

### Ruff y grupos completos

Desde `clon/`, `D:/PROGRAMA/clon/.venv/Scripts/python.exe -m ruff check .`:

```console
All checks passed!
```

Cada grupo usa exactamente este prefijo y sufijo, desde `clon/`:
`D:/PROGRAMA/clon/.venv/Scripts/python.exe ../scripts/turno.py -- D:/PROGRAMA/clon/.venv/Scripts/python.exe -m pytest <archivos> -q -p no:cacheprovider`.
De a uno, sin ampliar el tope de 900 s de ejecución del turno.

**Grupo 1:** `tests/test_sol10_nervio_red.py tests/test_solidos_crear.py tests/test_solidos_modificar.py tests/test_api_solido_extra.py tests/test_api_solido.py`

```console
........................................................................ [ 30%]
........................................................................ [ 61%]
........................................................................ [ 92%]
.................                                                        [100%]
233 passed in 46.35s
```

**Grupo 2:** `tests/test_herramientas_solido.py tests/test_barrido_tipos.py tests/test_comandos_crear.py`

```console
........................................................................ [ 32%]
........................................................................ [ 64%]
........................................................................ [ 96%]
.......                                                                  [100%]
223 passed in 141.32s (0:02:21)
```

**Grupo 3:** `tests/test_api_asistente.py tests/test_asistente_adjuntos.py tests/test_asistente_alcance.py tests/test_asistente_historial.py tests/test_asistente_modelos.py tests/test_asistente_nucleo.py tests/test_asistente_prompt.py tests/test_asistente_proveedores.py tests/test_asistente_ui.py`

```console
........................................................................ [ 36%]
........................................................................ [ 72%]
........................................................                 [100%]
200 passed in 16.38s
```

**Grupo 4:** `tests/test_boceto_fase4.py tests/test_boceto_interaccion.py tests/test_cobertura_ui_api.py tests/test_dev.py tests/test_gizmo_lienzo.py tests/test_iconos_extra.py tests/test_insertar_2d.py tests/test_interaccion_fusion.py tests/test_malla.py tests/test_manipuladores.py tests/test_novedades.py tests/test_p23_calcomania.py tests/test_revision_lotes_sol.py tests/test_sol27_preajustes.py tests/test_svg_salida.py tests/test_temas.py tests/test_tipografia_ui.py`

```console
........................................................................ [  7%]
........................................................................ [ 15%]
........................................................................ [ 23%]
........................................................................ [ 30%]
........................................................................ [ 38%]
........................................................................ [ 46%]
........................................................................ [ 53%]
........................................................................ [ 61%]
........................................................................ [ 69%]
........................................................................ [ 77%]
........................................................................ [ 84%]
........................................................................ [ 92%]
......................................................................   [100%]
934 passed in 687.11s (0:11:27)
```

**Corridas incompletas:** la primera tanda reunía los grupos 1 y 2; el timeout de la herramienta fue 300 s,
incluyendo 122 s de cola, y cortó antes del resumen. Se repitió partida: ambas verdes arriba. El primer envío
del grupo 4 se interrumpió por el tope de la sesión mientras esperaba turno. Al retomar se comprobó que no
quedaban procesos de ese grupo; se repitió y terminó con salida 0. Ninguna corrida incompleta se cuenta como verde.
`rg -l` tampoco estaba instalado (`rg: command not found`); se ejecutó la búsqueda pedida con `grep -l`.

### Salida completa de /ponytail-review

What this change does: Rib and Web now trim their long helper wall before applying draft. Only side faces
from the original wall are tilted. Assumed load: one person or agent editing one CAD document.

**Should fix**

1. **The docstrings promise constant thickness along the whole curve** (`clon/omnicad/nucleo/solidos_crear.py:1415-1417,1439-1441`).
   - **What this is:** The draft uses a plane normal to the pull direction, through the middle of the curve.
   - **Problem:** With a diagonal curve and pull Z, that plane only crosses the curve at its midpoint. The old text says the whole free edge keeps its thickness. It also describes negative angles as if they were positive.
   - **Fix:** State the neutral plane and explain that a negative angle reverses the taper.
   - **If we skip it:** A caller may expect a thickness that the geometry does not preserve away from that plane.

Verdict: fix 1 first.
Not checked: the live panel gesture, Fusion itself, OmniKernel execution, and a large multi-curve draft benchmark.

**Aplicación y relectura:** hallazgo 1 corregido en los dos docstrings; no cambió la geometría después de los
grupos completos. Ambos consumidores pasan el nuevo argumento nombrado; el caso sin ángulo conserva su
recorte. Las nuevas regresiones de Red comprueban el signo negativo y los dos conos de la curva. Los errores
siguen pasando por `geo.ErrorGeometria` y la transacción existente de la API. No hay escrituras de datos nuevas,
ni dependencias, ni cachés. El filtro de caras reutiliza el helper existente, con costo proporcional a caras del
recorte por laterales originales; no corre durante el dibujo de cada cuadro.
Revisión final: sin hallazgos pendientes; **Verdict: Ship.**

### ⚠ Lo no verificado y límites

- Sin suite completa ni prueba de humo por pedido. No se abrió Fusion ni se ejercitó la previa con clics en
  la ventana; se trazó el camino real por código y pasaron los tests existentes de comandos.
- La ayuda no confirma dónde Fusion conserva el grosor con extracción oblicua. Se mantuvo la convención
  existente de OmniCAD (plano por el punto medio); no se declara equivalencia visual exacta con Fusion.
- No se barrió todo −45..45 ni todas las orientaciones de extracción. −5° y +5° con extracción Z sobre la
  misma pared de 2 mm no forman parte del verde: la pared puede agotarse dentro del nervio real, y no solo
  en su prolongación auxiliar. No se aflojaron las validaciones del kernel para aceptar cruces físicos.
- B-213 (recorte contra la caja), B-214 (curvas sueltas), B-216 (Invertir de Red) y H-95 (opciones de extracción
  y empalme) siguen siendo tareas independientes. No se ejecutó OmniKernel, que no implementa Nervio/Red.
- Sin banco grande de rendimiento ni instalador; `clon/pyproject.toml` no configura type-check separado.

## Informe Sol · B-213

**Estado: Parcial; no integrar como arreglo completo.** La prueba propuesta de Nervio está verde: invertido
sin cara devuelve error y conserva el cuerpo; simétrico, side1 y side2 en el borde suman 1200 mm³ cada uno.
Red conserva su implementación original: se retiró el cambio completo de Red al detectar que rompía la cruz
de dos curvas de `test_red_hasta_el_piso`. Sus dos variantes exteriores siguen pendientes.
Se paró la geometría tras dos intentos, según el límite del pedido. Se conservan fila y detalle en Parcial;
`docs/seguimiento/README.md` no contiene B-213 y no necesita cambios. Sin commit ni cambios de rama.

### Ayuda de Fusion y decisión

El worktree no tiene el índice local de ayuda: el primer comando devolvió
`Falta el índice: correr primero fusion_docs.py construir`. Se consultó la copia existente en `D:/PROGRAMA`,
con el mismo Python pedido, sin construir ni modificar el índice:

```console
D:/PROGRAMA/clon/.venv/Scripts/python.exe scripts/fusion_docs.py buscar rib -s fusion-model
1. Create a rib
2. Rib reference
D:/PROGRAMA/clon/.venv/Scripts/python.exe scripts/fusion_docs.py ver "Rib reference" -s fusion-model
D:/PROGRAMA/clon/.venv/Scripts/python.exe scripts/fusion_docs.py ver "Web reference" -s fusion-model
```

Leídos `rib-reference-74df3f99244.md` y `web-reference-f26b3821965.md`, en
`docs/fusion_docs/contenido/fusion-model/`: To Next llega a las caras más cercanas del sólido;
Symmetric pone la mitad del grosor a cada lado y One Direction el grosor entero a un lado.
Extend Curves prolonga hasta las caras del cuerpo. Se leyó también la auditoría original de Nervio/Red/Repujado.

INTENT: code does recorte del sólido contra la caja del cuerpo; the failing check/task expects grosor entero en el borde y error sin cara de llegada; the spec (README/docs/docstring) says Al siguiente llega a caras del sólido y respeta el grosor elegido.

### Cambios y gemelos

- `clon/omnicad/nucleo/solidos_crear.py:1414`: `_lamina_hasta_el_cuerpo(lamina, cuerpo, curvas, finales, que, profundidad)`
  recorta caras contra el cuerpo, conserva las que nacen de la curva y rechaza el extremo auxiliar en To Next.
  Es un helper privado nuevo, solo de Nervio; devuelve un compuesto de caras.
- `clon/omnicad/nucleo/solidos_crear.py:1447`: `nervio(cuerpo, aristas_curva, normal_plano, espesor, *,
  profundidad=None, direccion="simetrica", invertir=False, extender=True, angulo_desmoldeo=0.0,
  direccion_desmoldeo=None)` conserva la firma pública; engrosa después del recorte y quita el solape real.
- `clon/omnicad/nucleo/solidos_crear.py:1487`: `red(cuerpo, aristas_curvas, normal_plano, espesor,
  profundidad=None, *, direccion="simetrica", invertir=False, extender=True, angulo_desmoldeo=0.0)` conserva
  la implementación original: el intento de recortar por cadena se retiró para no romper cruces.
- `_hasta_el_cuerpo` y `_caja_de` originales siguen usados por Red. No se añadieron dependencias.
- `clon/tests/test_sol10_nervio_red.py:37-78`: seis casos nuevos por API real, validez y volumen; rechazo
  atómico del invertido. Las dos variantes exteriores de Red quedan rojas, sin ocultarlas con xfail.

TWINS: searched `_hasta_el_cuerpo`, `_caja_de`, `nervio`, `red`, `create_rib`, `create_web` - found 1 other affected consumer: Red compartía el recorte de Nervio; tras fallar dos intentos, Red conserva el recorte original y queda pendiente en B-213.

| Superficie revisada | Resultado |
|---|---|
| Previa `ui/comando.py:1665` y camino normal de `Documento.previsualizar` | Ejecuta la misma operación; sin fórmula de Nervio/Red duplicada. No hay archivos `nucleo/previa*` en este worktree. |
| `nucleo/superficies.py`, `timeline/ops_superficie.py` | Sin Nervio/Red; coincide con la ausencia de estas herramientas en SUPERFICIE de Fusion. |
| `nucleo/omnikernel/solidos_crear.py` | No implementa Nervio/Red; no se inventó un adaptador ni se declaró probado. |
| `api/herramientas_solido_extra.py:161-227` | `create_rib`/`create_web` → `_nervio` → `OpNervio`/`OpRed`; mismo núcleo. |
| `timeline/ops_solido.py:260-290` | Ambos consumidores usan las firmas públicas intactas. B-216 sigue independiente. |
| `ui/comandos/crear.py:297-347` | `_NervioRed` crea esas operaciones; no recorta geometría por su cuenta. |
| `_recortar_hasta` en el mismo núcleo | Extruir usa piezas que tocan el inicio, pero no `_caja_de`; no se cambió. |

### Rojo, intentos y verde observado

Python importado comprobado: `D:\PROGRAMA-sol\clon\omnicad\__init__.py`.
Todos los pytest se lanzaron desde `clon/` con el Python compartido y `../scripts/turno.py --`,
`-q -p no:cacheprovider`. Las esperas de turno no son tiempo de cálculo del kernel.

**Antes del arreglo**, `tests/test_sol10_nervio_red.py -k b213`:

```console
[turno] arranca tras 66 s de espera
FF.FFF
Obtained: 599.9999999999709
Expected: 1200 ± 0.0012
Nervio invertido: ok=True, volume=27450.0, previous_volume=25500.0
FAILED ...test_b213_nervio_en_el_borde_conserva_todo_el_espesor[symmetric]
FAILED ...test_b213_nervio_en_el_borde_conserva_todo_el_espesor[side1]
FAILED ...test_b213_nervio_invertido_sin_cara_da_error_y_conserva_el_cuerpo
FAILED ...test_b213_red_delante_de_la_boca_conserva_el_inicio[False]
FAILED ...test_b213_red_delante_de_la_boca_conserva_el_inicio[True]
5 failed, 1 passed, 24 deselected in 2.26s
```

La primera versión del test de error decía `message`; se corrigió a la clave real `mensaje` al observar
la respuesta de la API. No influyó en el rojo inicial: fallaba antes porque devolvía ok=True.
El oráculo inicial de Red extendida (3096 mm³) se sustituyó por validez, aumento >1720 y caja y mínima −5:
la ayuda no fija qué pasa con el tramo exterior sobre los labios y no se midió en Fusion. No se aflojó
el punto que falla: crear la Red extendida debe tener éxito y sigue sin tenerlo.

**Intento 1**, recorte de lámina antes de engrosar:

```console
[turno] arranca tras 16 s de espera
.....F........................
FAILED tests/test_sol10_nervio_red.py::test_b213_red_delante_de_la_boca_conserva_el_inicio[True]
1 failed, 29 passed in 3.33s
```

**Intento 2**, separar las prolongaciones con Splitter y planos de las caras laterales tocadas:

```console
[turno] arranca tras 54 s de espera
.....F........................
FAILED tests/test_sol10_nervio_red.py::test_b213_red_delante_de_la_boca_conserva_el_inicio[True]
1 failed, 29 passed in 3.39s
```

El segundo intento se retiró con parche preciso; no quedó un Splitter sin utilidad. Hipótesis para retomar:
el corte/unificación posterior puede volver a unir caras coplanares separadas, y la región frente a la boca
sigue conectando las prolongaciones. No se verificó esa causa interna. No se hizo un tercer intento.

**Prueba propuesta en verde**, tras retirar el segundo intento:

```console
PYTHONIOENCODING=utf-8 D:/PROGRAMA/clon/.venv/Scripts/python.exe ../scripts/turno.py -- D:/PROGRAMA/clon/.venv/Scripts/python.exe -m pytest tests/test_sol10_nervio_red.py -k 'b213 and not red_delante' -q -p no:cacheprovider
[turno] arranca tras 102 s de espera
....                                                                     [100%]
4 passed, 26 deselected in 1.98s
D:/PROGRAMA/clon/.venv/Scripts/python.exe -m ruff check .
All checks passed!
```

**Área antes de retirar el cambio de Red** (mismo prefijo de Python/turno):

```console
-m pytest tests/test_sol10_nervio_red.py tests/test_solidos_crear.py tests/test_api_solido_extra.py -k 'nervio or red' -q -p no:cacheprovider
[turno] arranca tras 18 s de espera
FAILED tests/test_sol10_nervio_red.py::test_b213_red_delante_de_la_boca_conserva_el_inicio[True]
FAILED tests/test_solidos_crear.py::test_red_hasta_el_piso
omnicad.nucleo.geometria.ErrorGeometria: Red: no llega al cuerpo (revisá el sentido o usá una profundidad).
2 failed, 32 passed, 103 deselected in 3.87s
```

La cruz extiende una de las curvas hasta el borde abierto del canal: al recortar cada lámina por separado
se perdía la unión que permitía limitar la cruz completa. Se retiraron los cambios de Red y se restauró
su helper original; el helper nuevo solo queda en Nervio. Esto es retirada de la regresión, no tercer intento.
La repetición final posterior a esa retirada agotó 120 s **esperando turno**, sin arrancar pytest.
No se contó como verde. Se repitió con transporte de 180 s (sin cambiar el plazo de turno de 900 s):

```console
PYTHONIOENCODING=utf-8 D:/PROGRAMA/clon/.venv/Scripts/python.exe ../scripts/turno.py -- D:/PROGRAMA/clon/.venv/Scripts/python.exe -m pytest tests/test_sol10_nervio_red.py tests/test_solidos_crear.py tests/test_api_solido_extra.py -k 'nervio or red' -q -p no:cacheprovider
[turno] arranca tras 93 s de espera
....FF............................                                       [100%]
FAILED tests/test_sol10_nervio_red.py::test_b213_red_delante_de_la_boca_conserva_el_inicio[False]
FAILED tests/test_sol10_nervio_red.py::test_b213_red_delante_de_la_boca_conserva_el_inicio[True]
2 failed, 32 passed, 103 deselected in 5.55s
D:/PROGRAMA/clon/.venv/Scripts/python.exe -m ruff check .
All checks passed!
git diff --check
(sin salida, código 0)
```

La cruz existente volvió a verde, los cuatro casos propuestos de Nervio permanecen verdes y solo fallan
las dos regresiones exteriores nuevas de Red. El diff confirma que `red`, `_hasta_el_cuerpo` y `_caja_de`
son los originales de HEAD. No se ejecutaron grupos amplios completos, solo estos tests del área filtrados.

### Grupos amplios para el coordinador

Se buscó antes de editar con codebase-memory y se repitió sobre disco. `rg` no está instalado;
el comando literal solicitado se obtuvo con `grep -l -E '_hasta_el_cuerpo|nervio|red' clon/tests/test_*.py`.
No se corrieron esos grupos por la nota de tiempo. Todos los nombres siguientes son `clon/tests/test_<nombre>.py`;
`red` sin límites de palabra también encuentra colores, red de internet y palabras como pared/predeterminado:

```console
analisis animacion api_animacion api_asistente api_boceto api_boceto_herramientas api_catalogo
api_construccion api_dibujo api_documento api_ensamble api_grafo api_malla api_material api_misc
api_opciones_modificar api_opciones_solido1 api_render api_revision api_solido api_solido_extra
api_superficie apoyo arrastre_ventana asistente_adjuntos asistente_agente_local asistente_alcance
asistente_historial asistente_modelos asistente_nucleo asistente_prompt asistente_proveedores asistente_ui
aspectos_api auditoria_boceto b105_panel_chico b165_agujero_tangente b167_b168_autointersecciones
b39_enterrada b39_fuzz b70_pasante b71_cadena barrido_tipos boceto3d_tangente boceto_fase0
boceto_fase3 boceto_fase4 boceto_fase7 boceto_fase8_malla boceto_fase9_3d boceto_fase9_3d_ui
boceto_fase9_fuentes boceto_fase9_nucleo boceto_fase9_tangente boceto_fase9_texto boceto_interaccion
boceto_organizar booleanas_tortura caja_herramientas caza_regresion chapa cinta_plastico cinta_textos
cobertura_ui_api comandos_inspeccionar comandos_malla comandos_modificar comandos_superficie comparar_malla
corte_visibles cotas_segmento cuerpos_partidos derivacion desfase_boceto desfase_equivalencia dev
dialogo_parametros dibujo ejemplos_agentes engranajes ensamblar ensamblar_asm ensamblar_asm9
ensamblar_bola_y_vinculo extruir_cara_api f3d_nativo f3d_reales geometria gizmo_lienzo graficos_rendimiento
grampa guardado_sesion hallazgos_nucleo hallazgos_tortura herramientas_solido iconos_extra iconos_interfaz
inferencia3d insertar_2d inspeccionar_fusion interaccion_fusion interfaz malla manipuladores nombres_ids
novedades objetos_vectoriales origen_entidad p11a_f3d_instancias p23_bocetos p23_calcomania p9_ui
panel_movible patrones_boceto patrones_solidos_semantica perfiles_interior pl7_desfase_aristas plasticidad
posicion_asm proyeccion_seccion puente reconstruir_malla registro_uso_mas render render_motor resalte_contorno
restricciones_matematica restricciones_ui resultados_vacios revision revision_lotes_sol servidor_mcp setup
simetria_boceto simetria_patrones sol07_revolucion sol08_barrido sol10_nervio_red sol11_empalme
sol12_esquina_chaflan sol13_desmoldeo sol15_bocetos sol15_mover_caras_y_escalar sol18_envolvente sol22_reticula
sol24_reconocer_funciones sol25_consejos_diseno sol26_similares sol27_preajustes solidos_crear solidos_modificar
solver_splines superficie_fusion superficies svg_salida temas teselado_cache texto_vectores tipografia_ui
topes tortura_menores transformar_boceto tuberia_cadena
```

Prioridad funcional de esa lista: `test_sol10_nervio_red.py`, `test_solidos_crear.py`,
`test_api_solido_extra.py`, `test_barrido_tipos.py`, `test_herramientas_solido.py`, `test_manipuladores.py`.
El helper original queda con un consumidor (Red); el nuevo, con uno (Nervio). Ningún test llama al original directamente.

### Salida completa de /ponytail-review

What this change does: It trims the thin surface against the real body before adding thickness.
It fixes the four proposed Rib cases. The Web change was withdrawn after an existing cross test failed. Assumed load:
one user editing a local CAD document; a wrong solid matters more than a small speed gain.

**Must fix**

1. **The Web attempt breaks a cross and does not finish B-213** (`clon/omnicad/nucleo/solidos_crear.py::red`).
   - **What this is:** The long surface must stop on body faces before it becomes a solid.
   - **Problem:** The outside extended Web failed in both attempts. The area tests also found a regression
     on two crossing curves: `test_red_hasta_el_piso` failed while processing the second curve alone.
   - **Fix:** Applied: withdraw the entire Web change, retain its original helper, keep both outside Web
     regressions and B-213 partial. Resume geometry only in a new run; no third attempt was made.
   - **If we skip it:** An existing valid cross would stop working. After withdrawal, the original outside
     Web bug remains; the complete fix cannot be shipped.

**Should fix**

2. **The raw wall is built even when draft is zero** (`nucleo/solidos_crear.py`, initial patch).
   - **What this is:** Draft needs the original side faces; a straight wall does not.
   - **Problem:** The first patch built a full raw solid and a trimmed solid on every ordinary call.
   - **Fix:** Build the raw solid only inside the nonzero draft branch. Applied in Rib; Web was restored.
   - **If we skip it:** Common calls do unnecessary OpenCascade work.

3. **The old box helper has no caller** (`nucleo/solidos_crear.py::_caja_de`, initial patch).
   - **What this is:** This helper made the artificial clipping box removed by the fix.
   - **Problem:** After updating both callers, its only former use is gone.
   - **Fix:** Initially deleted. Restored when Web was withdrawn, because Web still needs it.
   - **If we skip it:** Deleting it from the final partial patch would break the restored Web.

Verdict: fix 1 first. Its cross regression was removed by restoring Web, but B-213 remains incomplete
under the explicit two-attempt stop. Findings 2 and 3 were reconciled with that withdrawal.
Not checked: live window, Fusion itself, OmniKernel, oblique body faces across thickness, huge thickness,
and the broad grep groups. No new dependency, file input, network path or transaction bypass was added.

### ⚠ Lo no verificado

- El arreglo completo **no** está verde: se conservan dos regresiones exteriores de Red y B-213 en Parcial.
- Una repetición agotó el transporte esperando turno; la siguiente sí corrió y confirmó la retirada de
  la regresión de la cruz. Las esperas observadas llegaron a 102 s; no se eludió el candado.
- No se abrió Fusion ni la ventana; sin suite completa, humo ni grupos amplios por pedido.
- El recorte central seguido del grosor aún debe contrastarse con caras del cuerpo inclinadas respecto del
  espesor; no se afirma equivalencia general. El caso de grosor 1e6 no se ejecutó en esta corrida.
- No se configura type-check separado en `clon/pyproject.toml`; no se construyó instalador.
- B-214 y B-216 siguen fuera del alcance de esta corrida. La revisión funcional amplia queda al coordinador.

## Prompt para el agente

Entregado el 2026-11-05. Modelo sugerido: Opus 5, esfuerzo alto (coordinador nocturno; la geometría de Sol se revisa a fondo).

```text
ARRIBA DE TODO: invocá con la herramienta Skill fable-method y ponytail; usá plan-then-do, tool-calling-guard y verify-before-commit; ponytail-review sobre cada tanda o bug antes de commitear. Sos el COORDINADOR NOCTURNO de OmniCAD (repo D:\PROGRAMA). Gerardo duerme: no le preguntes nada; decidí con estas reglas y dejá todo escrito. Leé CLAUDE.md y AGENTS.md (las reglas del coordinador valen para vos esta noche).

TU TRABAJO: correr las dos líneas de docs/corrida_nocturna_2026-11-05.md (sección «Plan»), revisar cada entrega como coordinador, commitear lo verde y dejar el informe de la mañana. Gerardo te autoriza a commitear esta noche lo que verifiques (git add explícito, archivo por archivo; nunca privado/, analisis/, evidencias/, docs/fusion_docs/, PROJECT_CONTEXT.md ni .agents/). Nunca push.

PREPARAR
1. git status limpio en main (si no, anotalo y seguí con lo tuyo). Creá el worktree de Sol: git worktree add D:/PROGRAMA-sol -b sol-geometria-nocturna main. Comprobá que los tests del worktree importan su propio código: desde D:/PROGRAMA-sol/clon, D:/PROGRAMA/clon/.venv/Scripts/python.exe -c "import omnicad; print(omnicad.__file__)" tiene que mostrar D:\PROGRAMA-sol. Si no, anotalo y corré la línea B igual, pero con PYTHONPATH apuntando al worktree.
2. Carpeta de registros: evidencias/nocturna_2026-11-05/ (un .log por corrida).

LÍNEA A (Qwen, main): para N = 1 a 5, en orden:
- Lanzá en segundo plano (run_in_background), con tope de 90 minutos: timeout 5400 qodercli -p --dangerously-skip-permissions -m Qwen3.8-Flash -w D:/PROGRAMA "<Texto para Qwen con TANDA = N>" > evidencias/nocturna_2026-11-05/qwen_tanda_N.log 2>&1. Si acepta --reasoning-effort, usá el nivel más alto que liste --help.
- Cuando termine, revisá como coordinador: git diff; el «## Informe tanda N» de docs/arreglos_qwen.md (gemelos listados, test rojo y verde, salida de /ponytail-review con sus arreglos); ruff check .; los «Tests obligatorios» de la tanda MÁS todos los archivos de clon/tests que usan lo tocado (grep -l con cada función cambiada), con ../scripts/turno.py en grupos que terminen en menos de 900 s (si uno se corta, partilo: un corte no es verde); si tocó la ventana, la pieza en --ventana minimizada y mirá la captura con Read.
- Verde: commit con mensaje «Qwen tanda N: <IDs> (...)» y los IDs. Rojo: una sola vuelta de arreglo: timeout 3600 qodercli -p --dangerously-skip-permissions -c -m Qwen3.8-Flash -w D:/PROGRAMA "<qué falló, con la salida real>". Si sigue rojo: guardá git diff > evidencias/nocturna_2026-11-05/qwen_tanda_N_rechazada.patch, restaurá SOLO los archivos de esa tanda con git checkout -- <archivo> (nunca stash ni reset), anotá en el informe y seguí con la tanda siguiente.
- Si Qoder no responde (log en 0 bytes, sin CPU ni archivos tocados durante 25 minutos), cortá ese proceso y seguí.

LÍNEA B (Sol, worktree D:/PROGRAMA-sol), en paralelo con la A:
- Para BUG = B-212, B-215, B-213, B-208, en ese orden, uno por corrida: en segundo plano, con la carpeta del worktree como directorio de trabajo, timeout 1500 opencode run -m openai/gpt-6.1-sol --variant high "<Texto para Sol con BUG = ...>" > D:/PROGRAMA/evidencias/nocturna_2026-11-05/sol_<BUG>.log 2>&1. Antes de cada corrida, copiá los archivos que va a tocar (cp a evidencias/nocturna_2026-11-05/respaldo_<BUG>/).
- Si se corta por tiempo con avance real, una segunda corrida «seguí con BUG desde donde quedaste». Si el log dice que se acabó el cupo o el límite de uso, la línea B termina: anotalo.
- Revisión igual que en la A, pero dentro del worktree (los tests desde D:/PROGRAMA-sol/clon con el Python de D:/PROGRAMA/clon/.venv). Verde: commit en la rama sol-geometria-nocturna. Rojo: una vuelta de arreglo con el mismo texto más lo que falló; si sigue rojo, guardá el parche, restaurá esos archivos y anotalo.
- NO fusiones la rama en main.

CIERRE (cuando terminen las dos líneas, o a las 07:00 si siguen corriendo)
1. En main: el cierre completo con scripts/cierre_completo.sh (suite completa, prueba de humo y piezas; una sola corrida pesada a la vez). Lo rojo va a docs/seguimiento/ con su ID; lo verde se borra de docs/auditorias/prueba_nocturna_2026-10-31.md.
2. PROJECT_LOG.md (Registro): una viñeta por tanda y bug con su commit, y si el modelo alcanzó.
3. Refrescá la página de seguimiento (CLAUDE.md › «Página de seguimiento», pasos 1 a 3). Cuando cierres este prompt, borrá esta sección «## Prompt para el agente» y su fila de «Prompts guardados» en docs/seguimiento/README.md, y refrescá datasets/prompts.
4. Informe de la mañana en este documento, sección «## Informe de la mañana» arriba de las demás: tabla corta (tanda o bug · estado · commit · tests), lo rechazado y por qué, cómo quedó la rama de Sol (commits, qué falta para fusionar), resultado del cierre completo, y ⚠ lo que no se pudo. Máximo una pantalla.
5. Commit final de docs. Contexto: si llegás al 60 %, cerrá con el informe y pará (regla de CLAUDE.md).

PROHIBIDO: push, git stash, git reset --hard, borrar ramas o worktrees ajenos, gastar en APIs pagas, tocar archivos fuera de D:\PROGRAMA y D:\PROGRAMA-sol.
```
