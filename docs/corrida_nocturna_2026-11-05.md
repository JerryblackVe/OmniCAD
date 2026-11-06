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
