# Arreglos con Qwen3.8-Flash en OpenCode (tandas)

Pedido de Gerardo (2026-11-05): seguir con Qwen3.8-Flash (Extra High, 1M de contexto; gratis por ahora) con prompts
hechos a su medida. Los bugs salen de las auditorías de [Revolución, Barrido y Solevación](auditoria_revolucion_barrido_solevacion.md)
y de [Nervio, Red y Repujado](auditoria_nervio_red_repujado.md), y de [Extruir](auditoria_extruir.md).

## Por qué el prompt es así (lo que se vio de Qwen el 2026-11-05)

En los arreglos de Extruir resolvió 3 de 4 bugs, con buen diagnóstico y buen informe, pero:
1. **Cambió una regla en el núcleo y no en su gemelo** (la previa rápida): 3 casos de `test_previa_prisma.py` en rojo.
2. **Corrió solo los tests que eligió**, no todos los que usan lo que tocó.
3. **Dejó sin arreglar un «Should fix» de su propio `ponytail-review`** (una línea).

El prompt lo ataja con tres cosas obligatorias: buscar gemelos antes de editar, una lista de tests fija más los que
salen de `grep`, y arreglar todo lo que marque su `ponytail-review`. Tandas de dos bugs, uno por vez. La geometría
difícil (B-208, B-212, B-213, B-215 y el resto de B-206) no va a Qwen: va a Opus.

## Tandas

Se corren de a una y en orden. El coordinador revisa y commitea cada tanda antes de la siguiente.

| Tanda | Bugs | Archivos probables | Gemelos a revisar | Tests obligatorios |
|---|---|---|---|---|
| 1 | B-211, B-210 | `nucleo/solidos_crear.py`, `nucleo/superficies.py`, `timeline/ops_solido.py`, `timeline/ops_superficie.py`, `ui/comandos/crear.py`, `ui/comandos/superficie.py` | la previa de Revolución y de Barrido (`grep -rn "revol\|barrido" clon/omnicad/ui/comando.py clon/omnicad/nucleo/previa*`), OmniKernel (`nucleo/omnikernel/solidos_crear.py`), `edit_feature` | `test_sol07_revolucion.py`, `test_sol08_barrido.py`, `test_barrido_tipos.py`, `test_api_barrido.py`, `test_gizmo_barrido.py`, `test_solidos_crear.py`, `test_superficies.py`, `test_api_solido.py`, `test_api_superficie.py`, `test_comandos.py`, `test_comandos_superficie.py`, `test_previa_*.py` |
| 2 | B-216, B-214 | `nucleo/solidos_crear.py` (`red`, `nervio`), `timeline/ops_solido.py` | `nucleo/plastico.py` (Nervio y Red de PLÁSTICO), las asas de `ui/comandos/asas_extra.py` | `test_sol10_nervio_red.py`, `test_sol21_reglas_plastico.py`, `test_solidos_crear.py`, `test_api_solido_extra.py`, `test_comandos.py` |
| 3 | B-217, B-209 | `nucleo/solidos_crear.py` (repujado, barrido), `ui/comandos/crear.py` | Barrido de superficie (`nucleo/superficies.py`), la previa | `test_repujado_alineacion.py`, `test_sol08_barrido.py`, `test_barrido_tipos.py`, `test_api_barrido.py`, `test_solidos_crear.py`, `test_superficies.py`, `test_api_solido*.py`, `test_comandos*.py`, `test_previa_*.py` |
| 4 | H-92, H-86 | `ui/comandos/crear.py`, `ui/comandos/solido.py`, `ui/comandos/superficie.py`, `api/herramientas_solido.py`, `api/herramientas_superficie.py` | el valor por defecto en la ventana, en la API y en `PARAMS` de la operación: los tres iguales | `test_comandos*.py`, `test_api_*.py`, `test_doc_agentes.py` |
| 5 | H-99, H-94 | `ui/comandos/crear.py`, el aviso flotante de `ui/ventana.py` | el asa de Profundidad del Repujado, el panel en 800×520 | `test_repujado_alineacion.py`, `test_comandos*.py`, `test_b105_panel_chico.py`, piezas `nervio_red_repujado` y `revolucion_barrido_solevacion` |
| C1 | B-189, H-87 | `nucleo/solidos_crear.py` (`_trozos`, ~3868), `timeline/operaciones.py` (espesor de Extruir delgada, ~1117), `timeline/ops_solido.py` (la regla de plástico, ~1534), `ui/comandos/crear.py` | OmniKernel (`nucleo/omnikernel/`), la API (`api/herramientas_solido.py`, `assign_plastic_rule`), el valor por defecto en ventana, API y `PARAMS` (los tres iguales); Nervio, Red, Vaciado y Engrosar también deberían leer la regla: si no entran, fila nueva | `test_motor.py`, `test_paridad_motor.py`, `test_sol21_reglas_plastico.py`, `test_api_solido.py`, `test_cinta_plastico.py`, `test_comandos.py`, `test_revision_lotes_sol.py` |
| C2 | H-100 | `ui/comandos/crear.py` (~313-316: Ángulo de desmoldeo y radio de Nervio y Red), `timeline/ops_solido.py` | la API (`api/herramientas_solido*.py`: `create_rib`, `create_web`), los `PARAMS` de las operaciones, y `espesor_plastico` en `timeline/operaciones.py` como modelo a copiar (H-87) | `test_sol10_nervio_red.py`, `test_sol21_reglas_plastico.py`, `test_api_solido_extra.py`, `test_comandos.py`, `test_comandos_crear.py` |
| C3 | H-102 | `timeline/ops_solido.py` (Nervio, Red, Vaciado, Engrosar), `ui/comandos/crear.py` y los comandos de Vaciado y Engrosar, `timeline/operaciones.py` (`_regla_plastico`, ya hecho en C1 y C2) | la API (`api/herramientas_solido*.py`: `create_rib`, `create_web`, `shell`, `thicken`), los `PARAMS`, el valor por defecto en ventana, API y operación (los tres iguales) | `test_sol10_nervio_red.py`, `test_sol21_reglas_plastico.py`, `test_api_solido.py`, `test_api_solido_extra.py`, `test_comandos.py`, `test_comandos_crear.py`, `test_doc_agentes.py` |

En cada tanda, además de esa lista: todos los archivos que da
`grep -l "<cada función que tocaste>" clon/tests/test_*.py`.

## Informe tanda C1 (escrito por el coordinador)

CodeBuddy con deepseek-v4.1-flash, 2 corridas cortadas por el tope de 45 min, sin informe propio. **H-87 resuelto**: Extruir delgada arranca con el espesor de la regla de plástico (`timeline/operaciones.py` › `espesor_plastico`, ventana, API `wall_thickness` vacío). **B-189**: ya estaba resuelto en HEAD; queda `test_motor.py::test_ningun_valor_por_defecto_usa_un_enum_de_ocp`. Nuevos: B-218 y H-102. Revisión del coordinador: ruff limpio, 550 + 728 tests verdes.

## Informe tanda C2

**Modelo:** CodeBuddy con hy3 (el prompt original decía «OpenCode con Qwen3.8-Flash»; lo escribo como pidió el coordinador). **Tanda:** C2 · **Bug:** H-100 (mejora). **Sin commitear** (lo commitea el coordinador).

### H-100 — PLÁSTICO › Nervio y Red toman el desmoldeo y el radio de la regla asignada — **Resuelto**

- **Qué dice la ayuda de Fusion:** `docs/fusion_docs/contenido/fusion-model/plastic-rules-5619f43a2b0.md` — «Physical values: Thickness, Draft Angle and Nominal Radius, which are referenced as parameters and used by modeling tools such as Extrude, Rib, Web, Boss, Snap Fit, Emboss, Thicken, Shell, Draft». O sea que Rib (Nervio) y Web (Red) deben usar el Draft Angle y el Nominal Radius de la regla, no arrancar en 0 deg / 0 mm.
- **Qué cambié:**
  - `clon/omnicad/timeline/operaciones.py`: refactor de `espesor_plastico` en una `_regla_plastico(estado, cuerpos)` que devuelve el dict de la regla (la del componente de `cuerpos`, o la única asignada en el diseño, o `None`), y dos gemelas `angulo_desmoldeo_plastico` / `radio_nominal_plastico` que devuelven `"N deg"` / `"N mm"` (o `"0 deg"` / `"0 mm"` sin regla).
  - `clon/omnicad/timeline/ops_solido.py`: `OpNervio.ejecutar` y `OpRed.ejecutar` resuelven el `angulo_desmoldeo` (y `OpRed` también `radio_empalme`) vacío contra la regla del componente del cuerpo objetivo: `str(self.p[...] or "").strip() or angulo_desmoldeo_plastico(estado, (cuerpo.id,))`. Lo explícito manda.
  - `clon/omnicad/ui/comandos/crear.py`: el panel de Nervio/Red arranca con `angulo_desmoldeo_plastico(ctx.estado)` y `radio_nominal_plastico(ctx.estado)` (campos `angulo_desmoldeo` y `radio_empalme`, líneas ~313 y ~316).
  - `clon/omnicad/api/herramientas_solido_extra.py`: `create_rib` (`draft_angle` → `""`) y `create_web` (`draft_angle` y `fillet_radius` → `""`) para que, sin valor, caigan en la regla; docstrings actualizados.
  - `docs/agentes/herramientas.md` regenerado (`omnicad tools --markdown --output …`).
- **Gemelos revisados:**
  - `OpNervio` / `OpRed` (`timeline/ops_solido.py`): cambiados ambos (ahí vive el cálculo). ✔
  - API `create_rib` / `create_web` (`api/herramientas_solido_extra.py`): defaults a vacío para que coincidan con la ventana. ✔
  - `PARAMS` de las operaciones: ya tenían `"0 deg"` / `"0 mm"`; el valor vacío se resuelve al ejecutar, no se tocó el dict (igual que H-87 con `espesor`). ✔
  - `espesor_plastico` (`timeline/operaciones.py`): usado como modelo; se factorizó en `_regla_plastico`. ✔
  - **Fuera de alcance (no los toqué, no estaban en H-100):** Saliente (`OpSaliente`), Apoyo (`OpApoyo`), Labio (`OpLabio`) y Desmoldeo tienen su propio `angulo_desmoldeo` y no cayeron en la regla; queda como mejora aparte si Gerardo lo quiere.
- **Test nuevo** (`tests/test_sol21_reglas_plastico.py::test_nervio_y_red_toman_desmoldeo_y_radio_de_la_regla`): asigna una regla con `draft_angle=5`, `nominal_radius=1.5` a un componente y comprueba que Nervio/Red sin valor coinciden en geometría con poner el valor a mano, y que el panel arranca en `5 deg` / `1,5 mm` (y en `0 deg` / `0 mm` sin regla).
  - Salida **ROJA** (antes del arreglo, con el test escrito pero el código viejo): el nervio sin `draft_angle` se construía con 0 deg, así que la geometría no coincidía con la de `draft_angle=5` (y el panel arrancaba en `0 deg`).
  - Salida **VERDE** (con el arreglo): `90 passed in 10.17s`
- **ruff check .:** `All checks passed!`
- **Tests obligatorios de la tanda (corridos con turno, un grupo):** `test_sol10_nervio_red.py`, `test_sol21_reglas_plastico.py`, `test_api_solido_extra.py`, `test_comandos.py`, `test_comandos_crear.py` → **90 passed**.
- **Archivos de `grep -l` NO corridos (los corre el coordinador):** `test_api_solido.py`, `test_apoyo.py`, `test_barrido_tipos.py`, `test_cinta_plastico.py`, `test_cobertura_ui_api.py`, `test_iconos_extra.py`, `test_malla.py`, `test_manipuladores.py`, `test_sol27_preajustes.py`. (El grep incluye los 5 obligatorios más éstos; coinciden solo por el token genérico `angulo_desmoldeo` o por referenciar Nervio/Red, no por tocar las funciones nuevas.)
- **Salida de /ponytail-review:** no halló bugs ni riesgos. Lo único a notar (no es regresión, copia el diseño de H-87): cuando hay **varias** reglas asignadas a distintos componentes, el panel de Nervio/Red arranca en `0 deg` / `0 mm` (la función solo toma la regla cuando hay una sola asignada en el diseño); la operación, en cambio, sí usa la regla del componente del cuerpo elegido. Igual que el espesor de Extruir. No lo marcó como Must/Should fix. No hubo nada que arreglar.
- **No verificado / ⚠:** no corrí la prueba de humo ni la suite completa (las corre el coordinador, regla 10 del prompt); no toqué la ventana más allá de los valores por defecto de los campos, así que no hice la captura `todo.py` de la pieza (la lógica de Nervio/Red ya la ejercitan los tests de API y ventana de la tanda).

## Prompt para el agente

Entregado el 2026-11-05. Modelo sugerido: Qwen Flash en OpenCode, esfuerzo Extra High (1M de contexto). Versión: Qwen3.8-Flash. Se pega con el número de tanda.

```text
TANDA = (el número que te dio Gerardo: 1, 2, 3, 4 o 5)

PASO 0 (obligatorio, antes de leer código): invocá con la herramienta skill /fable-method y /ponytail. Usá también /plan-then-do, /tool-calling-guard y /verify-before-commit. Al final, /ponytail-review. Si una skill no existe, seguí igual las reglas de abajo.

PROYECTO
OmniCAD: CAD 3D paramétrico en Python (PySide6 + OpenCascade vía cadquery-ocp) que copia Fusion 360. Repo D:\PROGRAMA, código en clon/. Leé AGENTS.md antes de tocar código. Todo en español. Unidades: mm y grados.

QUÉ HACER
Leé docs/arreglos_qwen.md, fila de tu TANDA en la tabla «Tandas». Arreglá esos dos bugs o mejoras, DE A UNO: terminás y verificás el primero antes de empezar el segundo. El detalle de cada uno está en docs/seguimiento/bugs.md o mejoras.md (fila y sección «Detalle»: causa probable con archivo:línea y prueba propuesta) y en el informe de la auditoría que lo encontró.

REGLAS QUE TENÉS QUE CUMPLIR (en tu corrida anterior fallaste en las tres primeras)
1. GEMELOS ANTES DE EDITAR. Antes de cambiar una regla o un cálculo, buscá dónde más se calcula lo mismo: la previa rápida (ui/comando.py, nucleo/previa*), la versión de superficie (timeline/ops_superficie.py, nucleo/superficies.py), OmniKernel (nucleo/omnikernel/), la API (clon/omnicad/api/) y la columna «Gemelos a revisar» de tu tanda. Usá grep con el nombre de la función y de los parámetros. Escribí la lista de gemelos en el informe y cambiá todos los que correspondan. La vez pasada cambiaste el núcleo y no la previa: se rompieron 3 tests.
2. TESTS: LA LISTA ENTERA, NO LOS QUE ELIJAS. Corré los «Tests obligatorios» de tu tanda MÁS todos los archivos que salen de: grep -l "<cada función que tocaste>" clon/tests/test_*.py. Desde clon/, siempre con turno y en grupos que terminen en menos de 900 s:
   .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe -m pytest <archivos> -q -p no:cacheprovider
   Si turno corta por tiempo, partí el grupo y seguí: no cuenta como verde.
3. TU REVIEW SE ARREGLA. Todo lo que /ponytail-review marque como «Must fix» o «Should fix» lo arreglás antes de cerrar (y volvés a correr los tests). Solo puede quedar sin arreglar lo que sea otro bug: entonces fila nueva en docs/seguimiento/ con el siguiente ID libre.
4. TEST ROJO PRIMERO. Para cada bug: escribí el test de la «Prueba propuesta», corrélo y pegá que FALLA; recién ahí arreglá y pegá que PASA.
5. Antes de decidir cómo debe comportarse algo, leé la ayuda oficial de Fusion: clon/.venv/Scripts/python.exe scripts/fusion_docs.py buscar <palabras> -s fusion-model (o -s fusion-patch para superficie) y ver "<título>" -s <carpeta>. No adivines.
6. Si la geometría (OpenCascade) se pone dudosa o no sale en dos intentos, PARÁ: dejá la fila en «Parcial» con lo que falta y explicalo. No inventes.
7. Tocá solo lo necesario para tus dos bugs. Nada de git stash, git checkout ni git reset. No commitees ni hagas push. Si necesitás cambiar un archivo que no es de tu tanda, decilo en el informe.
8. Toda opción o comportamiento que cambie en la ventana tiene que quedar igual en el MCP y la CLI (clon/omnicad/api/, receta C de AGENTS.md); si cambia una firma, regenerá docs/agentes/herramientas.md con: omnicad tools --markdown --output docs/agentes/herramientas.md
9. Si tocaste la ventana: .venv/Scripts/python.exe ../scripts/prueba_ui/todo.py <pieza> --ventana minimizada (la pieza de tu tanda) y mirá la captura con Read.
10. NO corras la suite completa ni la prueba de humo: las corre el coordinador.

AL RESOLVER CADA BUG
Borrá su fila de docs/seguimiento/bugs.md (o mejoras.md), su sección «Detalle» y su ID en las tablas de docs/seguimiento/README.md. Sumá una viñeta en «## Registro» de PROJECT_LOG.md: «2026-11-05 · <ID> (OpenCode con Qwen3.8-Flash)» con qué cambiaste y el test que lo cubre. Si queda a medias: fila en «Parcial» con lo que falta.

INFORME (obligatorio)
En docs/arreglos_qwen.md, una sección «## Informe tanda <N>» ARRIBA de «## Prompt para el agente» (no borres el prompt ni la tabla), con:
- por cada bug: estado (Resuelto / Parcial / No), qué dice la ayuda de Fusion, qué cambiaste (archivo:línea), la lista de gemelos que revisaste y qué hiciste con cada uno, el test nuevo con su salida ROJA antes y VERDE después;
- la salida real de ruff check . y de cada grupo de tests (la línea final «N passed»);
- la salida completa de /ponytail-review y qué arreglaste de ella;
- lo que no pudiste verificar, con ⚠.
```
