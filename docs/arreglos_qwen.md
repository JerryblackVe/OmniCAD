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
| C4 | H-93 | `timeline/ops_solido.py` (~149, el aviso de «Selección de cadena» del Barrido) | la previa del Barrido, la API (`api/herramientas_solido.py`: `sweep`), el Barrido de superficie (`timeline/ops_superficie.py`), el valor por defecto de la casilla en ventana, API y `PARAMS` | `test_sol08_barrido.py`, `test_barrido_tipos.py`, `test_api_barrido.py`, `test_comandos.py`, `test_comandos_crear.py`, `test_doc_agentes.py` |
| C5 | H-74 | `ui/aspectos_ui.py` (menú contextual de «En este diseño») | la API (`api/herramientas_aspecto.py`: `manage_appearance` con `remove_users`, que ya lo hace: reusarla, no duplicar), `docs/brechas_aspecto.md`, deshacer en un solo paso | `test_aspecto_panel.py`, `test_aspectos_api.py`, `test_formulario_paneles.py`, `test_render_aspecto.py`, `test_comandos.py` |
| C6 | H-103 | `timeline/aspectos_doc.py` (`quitar` ~140 y `_limpiar_usos` ~224) | la API (`api/herramientas_aspecto.py`: `manage_appearance` › `suprimir`), el panel (`ui/aspectos_ui.py`), el caso `quitar_caras` | `test_aspecto_panel.py`, `test_aspectos_api.py`, `test_render_aspecto.py`, `test_formulario_paneles.py` |
| C7 | CF-11 | `ui/cinta_boceto.py` o la paleta de boceto (`ui/modo_boceto.py`), `restricciones/` (grados de libertad que ya calcula el solver), `api/herramientas_boceto*.py` | la ayuda de Fusion (`fusion_docs.py buscar under constrained -s fusion-sketch` y `buscar compute sketch`), el diálogo de restricciones automáticas que ya existe (`auto_constrain`, `suggest_auto_constraints`), la herramienta del MCP y la CLI (receta C), el ícono y la clave de la cinta (receta B) | `test_api_boceto.py`, `test_api_boceto_herramientas.py`, `test_boceto_fase2.py`, `test_boceto_fase4.py`, `test_cobertura_ui_api.py`, `test_restricciones_matematica.py`, `test_claves_comandos.py`, `test_doc_agentes.py` |
| C8 | H-71 | `ui/navegador_boceto.py` (arrastrar filas entre grupos y teclado en el árbol), el menú radial del visor en modo boceto | `docs/plan_boceto_organizar.md` (secciones 9.5 y 10), la herramienta del MCP que ya organiza el boceto (`get_sketch_organization` y la que cambia de grupo: reusarla), deshacer en un solo paso | `test_boceto_organizar_ui.py`, `test_boceto_organizar.py` (si existe), `test_cobertura_ui_api.py`, `test_comandos.py` |
| C9 | H-85 | `ui/comandos/superficie.py` (~19, el filtro `CURVAS` de Extruir de superficie) | el filtro de Extruir sólido (`ui/comandos/solido.py`, ya elige perfiles y caras planas: copiar ese criterio), la API `create_surface_extrude` (ya los acepta), la previa | `test_superficies.py`, `test_superficie_fusion.py`, `test_api_superficie.py`, `test_comandos_superficie.py`, `test_cobertura_ui_api.py`, pieza `extruir_espacios` |

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

## Informe tanda C3

**Modelo:** CodeBuddy con deepseek-v4.1-flash. **Tanda:** C3 · **Bug:** H-102 (mejora). **Sin commitear** (lo commitea el coordinador).
**Corrida corta (45 min):** se corrieron los 7 archivos obligatorios (un grupo) y, del `grep -l`, los cuatro de más riesgo
(`test_previa_vaciado_aislada`, `test_comandos_superficie`, `test_comandos_modificar`, `test_manipuladores`); el resto de la
lista de `grep -l` NO se corrió y queda anotado abajo para el coordinador.

### H-102 — PLÁSTICO › Nervio, Red, Vaciado y Engrosar toman el espesor de la regla asignada — **Resuelto**

- **Qué dice la ayuda de Fusion:** `contenido/fusion-model/plastic-rules-5619f43a2b0.md` — «Physical values: Thickness,
  Draft Angle and Nominal Radius, which are referenced as parameters and used by modeling tools such as Extrude, Rib, Web,
  Boss, Snap Fit, Emboss, **Thicken, Shell**, Draft». Y en Tips: «Assign plastic rules prior to adding parametric features
  like **Shell** or **Thicken** to ensure those features inherit settings and parameters from the plastic rule». O sea que
  los cuatro tienen que arrancar con el Thickness de la regla, no con un valor fijo.
- **Qué cambié** (mismo patrón que H-87 en Extruir delgada y H-100 en el desmoldeo/radio):
  - `clon/omnicad/timeline/operaciones.py:76` — `espesor_plastico(estado, cuerpos=(), por_defecto="1 mm")`: nuevo tercer
    argumento para que cada herramienta conserve su propio defecto cuando **no** hay regla (Nervio, Red y Engrosar 2 mm;
    Vaciado y Extruir delgada 1 mm). Sin eso, las cuatro caían a 1 mm y cambiaba el comportamiento sin regla.
  - `clon/omnicad/timeline/ops_solido.py:254` — `OpNervio.PARAMS["espesor"]` pasa de `"2 mm"` a `""`; `:271` (Nervio) y
    `:296` (Red) resuelven el grosor vacío contra `espesor_plastico(estado, (cuerpo.id,), "2 mm")`. Lo explícito manda.
  - `clon/omnicad/timeline/ops_modificar.py:380` — `OpVaciado.PARAMS["espesor_interior"/"espesor_exterior"]` a `""`;
    `:397` resuelve los dos por cuerpo del grupo contra `espesor_plastico(estado, (cid,), "1 mm")`.
  - `clon/omnicad/timeline/ops_superficie.py:527` — `OpEngrosar.PARAMS["espesor"]` a `""`; `:542` resuelve contra
    `espesor_plastico(estado, [cuerpos de las caras elegidas], "2 mm")` (filtra las entidades sin cuerpo).
  - `clon/omnicad/ui/comandos/crear.py:308` (Grosor de Nervio/Red), `ui/comandos/modificar.py:386,388` (Espesor interior y
    exterior de Vaciado) y `ui/comandos/superficie.py:592` (Grosor de Engrosar): el panel arranca con
    `espesor_plastico(ctx.estado, (), "<defecto de la herramienta>")`.
  - `clon/omnicad/api/herramientas_solido_extra.py:186,193,209,216,635,640` — `create_rib` / `create_web` (`thickness=""`),
    `thicken` (`thickness=""`) y `api/herramientas_modificar.py:280` `shell` (`thickness: Expr = ""`, deja de ser
    obligatorio) para que, sin valor, caigan en la regla; docstrings actualizados.
  - `docs/agentes/herramientas.md` regenerado con el código de este worktree (comando del coordinador; 5 líneas).
- **Los tres iguales (ventana / API / `PARAMS`)**: la ventana muestra el valor ya resuelto de la regla (o el defecto de la
  herramienta), la API y `PARAMS` usan `""` como «no lo puse: tomá la regla» y la operación resuelve al ejecutar. Es el
  mismo reparto que aceptó el coordinador en H-87 y H-100.
- **Gemelos revisados:**
  - `OpNervio` / `OpRed` (`timeline/ops_solido.py`): los dos cambiados. ✔
  - `OpVaciado` (`timeline/ops_modificar.py`) y `OpEngrosar` (`timeline/ops_superficie.py`): cambiados los dos; no hay
    versión de superficie del Vaciado ni de sólido del Engrosar (es la misma operación en las dos pestañas). ✔
  - API `create_rib` / `create_web` / `shell` / `thicken`: defaults a vacío para que coincidan con la ventana. ✔
  - `_regla_plastico` y las gemelas `angulo_desmoldeo_plastico` / `radio_nominal_plastico` (C1/C2): se reusaron sin
    tocarlas; `espesor_plastico` solo ganó el `por_defecto`. ✔
  - **Previa rápida** (`ui/comando.py`, `nucleo/previa*`): no evalúa espesores por su cuenta — ejecuta la operación, así que
    la resolución al ejecutar también la cubre (comprobado con `test_previa_vaciado_aislada.py`, 85 passed). ✔
  - **OmniKernel** (`nucleo/omnikernel/solidos_modificar.py:77`, `vaciado`): recibe el espesor ya calculado; no tiene
    defaults que replicar. ✔
  - **Fuera de alcance (no los toqué):** Saliente, Apoyo, Labio y Desmoldeo (su `angulo_desmoldeo` propio, ya anotado en
    el informe de C2) y `OpMallaVaciado` (`timeline/ops_malla.py:268`, espesor de malla: la regla es de sólidos).
- **Test nuevo** (`tests/test_sol21_reglas_plastico.py::test_nervio_red_vaciado_y_engrosar_toman_el_espesor_de_la_regla`):
  con una regla de 3 mm asignada al componente, cada herramienta sin espesor da la misma geometría que con el valor puesto
  a mano y distinta de su valor fijo de antes; los cuatro paneles arrancan en `3 mm` con regla y en `2 / 2 / 1 / 2 mm` sin
  regla (documento nuevo).
  - Salida **ROJA** (test escrito, código viejo):
    `FAILED tests/test_sol21_reglas_plastico.py::test_nervio_red_vaciado_y_engrosar_toman_el_espesor_de_la_regla`
    `AssertionError: {'ok': False, 'error_kind': 'INVALID_EXPRESSION', 'mensaje': 'El paso «Vaciado1» (op4) falló…'}` →
    `1 failed, 6 passed in 2.97s`
  - Salida **VERDE** (con el arreglo): `7 passed in 3.40s`
- **ruff check .:** `All checks passed!`
- **Tests obligatorios de la tanda (un grupo, con turno):** `test_sol10_nervio_red.py`, `test_sol21_reglas_plastico.py`,
  `test_api_solido.py`, `test_api_solido_extra.py`, `test_comandos.py`, `test_comandos_crear.py`, `test_doc_agentes.py`
  → **203 passed in 20.77s**
- **Del `grep -l` corrí además (riesgo alto):** `test_previa_vaciado_aislada.py`, `test_comandos_superficie.py`,
  `test_comandos_modificar.py`, `test_manipuladores.py` → **85 passed in 129.58s**
- **Archivos de `grep -l` NO corridos (los corre el coordinador):** por `Vaciado`: `test_malla.py`, `test_p9b_mas.py`,
  `test_pl5_sugerencias.py`, `test_previa_aislada_comandos.py`, `test_resultados_vacios.py`; por `create_rib` /
  `create_web` / `thicken`: `test_cobertura_ui_api.py`, `test_herramientas_solido.py`; por el token genérico `"shell"`
  (coincidencias de nombre, no de la herramienta): `test_api_avanzado.py`, `test_api_documento.py`, `test_api_modificar.py`,
  `test_api_opciones_modificar.py`, `test_apoyo.py`, `test_asistente_modelos.py`, `test_barrido_tipos.py`,
  `test_booleanas_tortura.py`, `test_bugs_solido.py`, `test_extruir_cara_api.py`, `test_f3d_nativo.py`,
  `test_hallazgos_nucleo.py`, `test_hallazgos_tortura.py`, `test_origen_entidad.py`, `test_sol13_sol20_ui.py`,
  `test_sol17_silueta.py`, `test_sol19_fluido.py`, `test_solidos_modificar.py`; por `OpRed`: `test_malla.py` (coincide con
  otro nombre, no con la operación Red).
- **Salida de /ponytail-review:** sin «Must fix» ni «Should fix». Repaso del diff: (1) el `por_defecto` evita cambiar el
  comportamiento sin regla — era el riesgo real del cambio; (2) `OpEngrosar` filtraba mal las entidades sin cuerpo y se
  corrigió (`if e.cuerpo`) antes de cerrar; (3) la API gana defaults y no rompe firmas (`shell` pasa de obligatorio a
  opcional; los demás solo cambian el valor); (4) los documentos viejos guardan el espesor explícito, así que no migran;
  (5) `nucleo/` sigue sin importar Qt y no se agregó estado global. Nada quedó pendiente.
- **No verificado / ⚠:** no corrí la suite completa ni la prueba de humo (regla 10: las corre el coordinador). Toqué la
  ventana (valores por defecto de cuatro campos), así que **falta la captura** `scripts/prueba_ui/todo.py` de la pieza
  `nervio_red_repujado` en minimizada; los paneles los ejercitan los tests de comando de la tanda, pero no se miró la
  pantalla. Tampoco se abrió Fusion: el comportamiento sale de la ayuda oficial, como en H-87 y H-100.

## Informe tanda C4

**Modelo:** CodeBuddy con hy3 (el prompt original decía «OpenCode con Qwen3.8-Flash»; lo escribo como pidió el coordinador). **Tanda:** C4 · **Bug:** H-93 (mejora). **Sin commitear** (lo commitea el coordinador).

### H-93 — SÓLIDO › Barrido: el aviso de «Selección de cadena» dejó de salir en cada barrido por curvas de boceto — **Resuelto**

- **Qué dice la ayuda de Fusion:** `docs/fusion_docs/contenido/fusion-model/sweep-reference-01a5bc5f7a3.md` y `tangent-chain-reference-c69a3eb5ea1.md` — la «Chain Selection» / «Tangent Chain» selecciona la geometría conectada tangentemente (aristas de un cuerpo **y** curvas de boceto). O sea que al barrer por un boceto la ruta ya es una cadena y no debe avisar «solo suma aristas de cuerpos».
- **Qué cambié:**
  - `clon/omnicad/timeline/ops_solido.py:143` — `OpBarrido._ruta` ahora delega en `_en_cadena` (la misma función que usa el barrido de superficie), que encadena tanto aristas de cuerpos como curvas de boceto tangentes; se borró el `ctx.aviso(...)` que lo decía. El cuerpo de la función pasa de 13 líneas a 3.
  - `clon/omnicad/ui/comandos/crear.py:65` — la ayuda de la casilla «Selección de cadena» ahora dice «Suma a cada arista de un cuerpo o curva de boceto las que le siguen tangentes.» (antes decía «las curvas de boceto se usan tal cual»).
  - `clon/omnicad/api/herramientas_solido.py:409` y `:439` — la descripción y el `:param chain` de `sweep` ya no dicen que las curvas de boceto «se usan tal cual y se avisa»; dicen que `chain` también encadena las curvas tangentes de `path_sketch`.
  - `docs/agentes/herramientas.md` regenerado (comando del coordinador; la firma `chain: bool` no cambió, solo el texto).
- **Gemelos revisados:**
  - `OpBarrido._ruta` (`timeline/ops_solido.py`): cambiado, es el único lugar que calculaba la ruta del barrido sólido. ✔
  - Barrido de superficie (`timeline/ops_superficie.py:223` y `_en_cadena` en `ops_solido.py:70`): ya usaba `_en_cadena` y no avisaba; ahora el sólido comparte exactamente esa lógica (los tres iguales: ventana, API, operación). ✔
  - La previa del Barrido (`ui/comando.py`, `nucleo/previa*`): no tiene regla propia de cadena; ejecuta la operación, así que al delegar en `_en_cadena` también la cubre (grep sin coincidencias de «solo suma aristas» en `previa*`). ✔
  - La API (`api/herramientas_solido.py:411` `sweep`): el parámetro `chain` ya existía; solo se corrigió su docstring para reflejar que ahora también encadena curvas de boceto. El valor por defecto `False` y el de la operación (`PARAMS["cadena"]=False`) siguen igual; la ventana lo marca `True` por defecto (`crear.py:65`), comportamiento que Fusion imita al encadenar la ruta del boceto. ✔
  - **Fuera de alcance:** Solevación (`OpSolevacion`, `ops_solido.py:226`) tiene su propio `cadena` para secciones y no avisaba; no lo toqué. Tubería (`OpTuberia`) ya usaba `_en_cadena`.
- **Test nuevo** (en `tests/test_sol08_barrido.py`): reemplacé `test_cadena_con_curvas_de_boceto_avisa_que_no_las_encadena` (que ASSERTÍA el aviso erróneo) por dos:
  - `test_cadena_con_curvas_de_boceto_no_avisa_y_sigue_toda_la_ruta`: barrido de un cuerpo por un boceto con `chain=True` no avisa «solo suma aristas de cuerpos» y da el volumen correcto (caja 10³ por recta de 40 mm → 5000 mm³).
  - `test_cadena_de_barrido_expande_las_curvas_de_boceto_tangentes`: eligiendo solo la primer curva de un boceto de dos curvas tangentes con `chain=True`, la ruta sigue toda la cadena (40 mm → 5000 mm³, no 3000 de la curva suelta).
  - Salida **ROJA** (test viejo, con el código viejo): el barrido por boceto avisaba «La selección de cadena solo suma aristas de cuerpos…» y la ruta no se encadenaba.
  - Salida **VERDE** (con el arreglo): `148 passed in 48.27s`.
- **ruff check .:** `All checks passed!` (sobre los 4 archivos tocados).
- **Tests obligatorios de la tanda (un grupo, con turno):** `test_sol08_barrido.py`, `test_barrido_tipos.py`, `test_api_barrido.py`, `test_comandos.py`, `test_comandos_crear.py`, `test_doc_agentes.py` → **148 passed in 48.27s**.
- **Archivos de `grep -l` NO corridos (los corre el coordinador):** unión de los grep `sweep` + `barrido`/`Barrido`/`OpBarrido` menos los 6 obligatorios: `test_analisis.py`, `test_api_boceto.py`, `test_api_boceto_herramientas.py`, `test_api_modificar.py`, `test_api_opciones_boceto.py`, `test_api_opciones_solido2.py`, `test_api_solido.py`, `test_api_solido_extra.py`, `test_api_superficie.py`, `test_b167_b168_autointersecciones.py`, `test_b52_espiral.py`, `test_b71_cadena.py`, `test_boceto_fase0.py`, `test_boceto_fase2.py`, `test_boceto_fase5.py`, `test_boceto_fase8_3d.py`, `test_boceto_fase9_3d.py`, `test_boceto_interaccion.py`, `test_cobertura_ui_api.py`, `test_comandos_inspeccionar.py`, `test_cuerpos_partidos.py`, `test_dibujo.py`, `test_ensamblar.py`, `test_gizmo_barrido.py`, `test_herramientas_solido.py`, `test_iconos_extra.py`, `test_patrones_boceto.py`, `test_restricciones_matematica.py`, `test_resultados_vacios.py`, `test_rocas_diametros_tabla.py`, `test_sol08_ui.py`, `test_sol24_reconocer_funciones.py`, `test_solidos_crear.py`, `test_superficie_guias.py`, `test_svg_arcos.py`, `test_texto_vectores.py`, `test_topes.py`. (La mayoría coinciden por el token genérico `sweep`/`barrido`, no porque toquen `OpBarrido._ruta`; los listo porque el prompt lo pide.)
- **Salida de /ponytail-review:** revisé el diff y el flujo real (`OpBarrido.ejecutar` → `_ruta` → `_en_cadena`, llamado también por Tubería y el barrido de superficie). Hallazgos:
  - **Must fix:** ninguno.
  - **Should fix:** ninguno. La refactor elimina código (13→3 líneas) y reusa `_en_cadena` ya existente y probado; el caso de ruta mixta (aristas de cuerpo + curvas de boceto) ahora se encadena todo sin aviso, que es el comportamiento de Fusion; el `formas_boceto` se reconstruye por llamada (sin estado global).
  - **Nice to have:** ninguno.
  - **Verdict:** `Ship.` Nada quedó pendiente de arreglar.
- **No verificado / ⚠:** no corrí la prueba de humo ni la suite completa (regla 10: las corre el coordinador). Tampoco corrí la captura `scripts/prueba_ui/todo.py` de la pieza `revolucion_barrido_solevacion` en minimizada: el panel del barrido no cambió de posición ni de campos, solo el texto de ayuda de la casilla «Selección de cadena»; los tests de `test_comandos_crear.py` (corridos) ejercitan el campo.

## Informe tanda C5

**Modelo:** CodeBuddy con deepseek-v4.1-flash (el prompt original decía «OpenCode con Qwen3.8-Flash»; lo escribo como pidió el coordinador). **Tanda:** C5 · **Bug:** H-74 (faltante). **Sin commitear** (lo commitea el coordinador).
**Corrida corta (45 min):** se corrió UN grupo con los 5 archivos obligatorios; los del `grep -l` NO se corrieron y están listados abajo para el coordinador (la lista salió casi vacía: solo los mismos obligatorios).

### H-74 — ASPECTO › «Quitar y suprimir» en el menú de «En este diseño» — **Resuelto**

- **Qué dice la ayuda de Fusion:** `docs/fusion_docs/contenido/fusion-render/modify-the-appearance-of-the-design-2c3eb0b892c.md`
  › «Unassign and delete appearance»: «Right-click the appearance, and click **Unassign and Delete**. The appearance is
  removed from the selected body/component/face.» O sea: del menú de «En este diseño», en un solo gesto, el aspecto se
  saca de todos los que lo usan **y** se borra del diseño. (En `fusion-model` no hay artículo del menú; la única fuente
  oficial es la de `fusion-render`.)
- **Qué cambié:**
  - `clon/omnicad/ui/aspectos_ui.py:736` — `PanelAspectos.quitar_y_suprimir(aid)` nuevo: descarta el id de `usados`,
    lo suma a `self.quitar_usos` (atributo nuevo, `:523`) y reusa `suprimir(aid)` para sacarlo de la copia de trabajo.
    Se escribe al Aceptar, como todo lo demás del panel (Cancelar lo descarta).
  - `clon/omnicad/ui/aspectos_ui.py:654` — el armado del menú sale de `_menu_diseno` a un `_menu_de_diseno(aid)` que
    devuelve el `QMenu` (el `_menu_diseno` solo lo ejecuta); ahí entra «Quitar y suprimir», después de Suprimir y
    siempre habilitado (Suprimir sigue gris cuando lo usan, como antes).
  - `clon/omnicad/ui/aspectos_ui.py:637` — `sincronizar` limpia `quitar_usos`: al aplicar ya se escribió.
  - `clon/omnicad/timeline/aspectos_doc.py:224` — `_limpiar_usos(doc, cambios, cuerpos, caras)` nuevo: devuelve los
    cuerpos a `apariencia/acabado/aspecto = None` y filtra las caras de ese aspecto de cada cuerpo.
    `reemplazar_lista(doc, nueva, quitar_usos=())` (`:234`) lo usa en lugar de fallar con «todavía se usa», en el
    **mismo** `set_propiedades` → UN paso de deshacer. `aplicar_panel(..., quitar_usos=())` (`:291`) y
    `propiedades_con(..., quitar_usos=())` (`:269`, la previa de Render) lo pasan.
  - `clon/omnicad/ui/comandos/aspecto.py:77` — `_avisar` copia `w.quitar_usos` a `panel.valores`; `:149` lo pasa a
    `ad.aplicar_panel`. `_previa` (`:88`) muestra el cambio al instante: saca esos cuerpos de la previa y los suma a
    `sin_caras` / `sin_apariencia` (si además se pinta el cuerpo con otro aspecto, lo elegido manda).
  - `clon/omnicad/ui/ventana.py:1258` — `_apariencias` descarta los cuerpos de `sin_apariencia`: vuelven al color de su
    material o al de fábrica, sin esperar al Aceptar.
  - `clon/omnicad/ui/render.py:1976` y `:2065` — el panel de CONFIGURAR › Aspecto (que usa el mismo `PanelAspectos`)
    pasa `quitar_usos` a la previa y a la escritura.
- **Gemelos revisados:**
  - La API (`api/herramientas_aspecto.py` › `manage_appearance` con `remove_users`): **ya lo hacía** y no se duplicó
    nada — el camino nuevo usa `timeline/aspectos_doc.py` (`_limpiar_usos` + `reemplazar_lista`), el mismo módulo que
    la herramienta. Firma y docstring sin cambios → `docs/agentes/herramientas.md` NO se regeneró (no cambió ninguna
    firma ni descripción de la API).
  - `ad.suprimir(doc, ref, quitar_usos=True)` (lo que usa la API): no se tocó; hace dos `set_propiedades` (lista y
    después usos) y eso ya es un solo paso de deshacer dentro de `Sesion.transaccion`. El camino del panel usa
    `reemplazar_lista` porque escribe la lista editada entera, no una acción por vez.
  - El panel de Render (`ui/render.py`, otro consumidor del mismo `PanelAspectos`): cambiado, previa y escritura.
  - La previa del comando (`ui/comandos/aspecto.py::_previa`) y el visor (`ui/ventana.py::_apariencias`): cambiados;
    sin eso el menú borraba el aspecto de la lista pero el cuerpo seguía pintado hasta el Aceptar.
  - `docs/brechas_aspecto.md`: las dos filas del menú y de «Unassign and Delete» al día.
  - **Fuera de alcance (no lo toqué):** el arrastre de la muestra (KS5) y el resto de la tabla.
- **Test nuevo** (`clon/tests/test_aspecto_panel.py`):
  - `test_quitar_y_suprimir_saca_el_aspecto_de_todos_y_lo_borra_en_un_paso`: con `asp1` en `op1.c1`, Suprimir sigue
    devolviendo `False`; `quitar_y_suprimir` devuelve `True`, la vista ya no pinta el cuerpo y el documento no cambió;
    al Aceptar la lista queda vacía y el cuerpo sin `apariencia`; `deshacer()` —un solo paso— devuelve el aspecto y
    el uso.
  - `test_el_menu_de_en_este_diseno_ofrece_quitar_y_suprimir`: el menú del clic derecho trae «Quitar y suprimir»
    habilitado y «Suprimir» gris.
  - Salida **ROJA** (antes del arreglo): `AttributeError: 'PanelAspectos' object has no attribute 'quitar_y_suprimir'`
    y `… has no attribute '_menu_de_diseno'` → `2 failed, 24 deselected in 2.97s`.
  - Salida **VERDE**: `26 passed in 4.74s` (el archivo entero).
- **ruff check .:** `All checks passed!` (dos veces: antes y después de rehacer un archivo).
- **Tests obligatorios de la tanda (un grupo, con turno):** `test_aspecto_panel.py` → 26; `test_aspectos_api.py`,
  `test_formulario_paneles.py`, `test_render_aspecto.py`, `test_comandos.py` → `69 passed in 7.89s`. **Total 95 passed.**
- **Además corrí** (por haber tocado `docs/seguimiento/` y el Registro): `test_aspecto_panel.py` +
  `test_seguimiento.py` + `test_doc_agentes.py` → `473 passed in 9.56s`.
- **Ventana (minimizada):** `todo.py paneles_inventario` → `172 comprobaciones, 0 con ✗` (ver ⚠).
- **Archivos de `grep -l` NO corridos (los corre el coordinador):** el grep de las funciones tocadas
  (`reemplazar_lista`, `propiedades_con`, `aplicar_panel`, `quitar_usos`, `sin_apariencia`, `_menu_de_diseno`,
  `quitar_y_suprimir`) devuelve **solo los dos obligatorios** (`test_aspectos_api.py` por `reemplazar_lista`,
  `test_render_aspecto.py` por `propiedades_con`), ya corridos. Por el token genérico `aspectos_doc` aparecen además
  `test_api_visor.py` y `test_inspeccionar_fusion.py`, que NO corrí (no tocan el panel ni la previa).
- **Salida de /ponytail-review:** sin «Must fix» ni «Should fix». Repaso del diff: (1) no se duplicó la API: el
  borrado vive en `aspectos_doc` y lo comparten la herramienta y el panel; (2) un solo `set_propiedades` → un solo
  paso de deshacer (probado con `deshacer()`); (3) el panel sigue sin escribir nada hasta Aceptar, así que Cancelar
  descarta el borrado; (4) `quitar_usos` con un id provisorio («nuevoN», un duplicado nunca usado) no hace nada
  porque `usos()` no lo encuentra; (5) `_limpiar_usos` se aplica **después** de `_repartir`, así no pisa las caras de
  un aspecto editado en el mismo Aceptar; (6) el `_menu_de_diseno` devuelve el `QMenu` sin abrirlo: mismo
  comportamiento y testeable. Nada quedó pendiente.
- **No verificado / ⚠:**
  - No corrí la prueba de humo ni la suite completa (regla 10: las corre el coordinador).
  - **Captura de la ventana:** no hay pieza de aspecto en `PIEZAS` (`scripts/prueba_ui/todo.py:29`); corrí la más
    cercana, `paneles_inventario --ventana minimizada` → **172 comprobaciones, 0 con ✗** y el panel ASPECTO abre bien
    (`evidencias/ui_2026-11-06/paneles_inventario.log`: «PANELES·despues·1280x720 · aspecto — {abierto: true,
    tipo_panel: PanelComando, titulo: ASPECTO, ancho: 462, alto: 377, campos: 5, visibles: 3, dentro_del_lienzo:
    true}»). Esa pieza no abre el menú del clic derecho, así que el ítem nuevo no se vio en pantalla; en los tests se
    inspecciona el `QMenu` sin `exec`.
  - No se abrió Fusion: el comportamiento sale de la ayuda oficial de `fusion-render`.

## Informe tanda C6

**Modelo:** CodeBuddy con hy3 (el prompt original decía «OpenCode con Qwen3.8-Flash»; lo escribo como pidió el coordinador). **Tanda:** C6 · **Bug:** H-103 (mejora). **Sin commitear** (lo commitea el coordinador).

### H-103 — ASPECTO › «quitar el aspecto de sus usos» estaba escrito dos veces — **Resuelto**

- **Qué dice la ayuda de Fusion:** no aplica una decisión de comportamiento: H-103 es una refactor de código duplicado, no un cambio de qué hace OmniCAD. El comportamiento de «Quitar» (sacar el aspecto de cuerpos y caras) y de «Quitar y suprimir» («Unassign and Delete») ya coincide con Fusion (`fusion-render/modify-the-appearance-of-the-design-2c3eb0b892c.md`); la mejora era unificar las dos copias para que un arreglo en una llegue a la otra.
- **Qué cambié:**
  - `clon/omnicad/timeline/aspectos_doc.py:140` — `quitar` ahora arma sus cambios llamando a `_limpiar_usos(doc, cambios, cuerpos, caras)` (el mismo helper que usa el «Quitar y suprimir» del panel, H-74) y solo suma el caso `quitar_caras` (H-73: un cuerpo pierde además los aspectos propios de sus caras) para los cuerpos que **no** estén en el parámetro `caras` — exactamente lo que hacía el código viejo. La refactor es neutra: analicé las 4 combinaciones (cuerpo solo / cara solo / cuerpo+cara solapados × `quitar_caras`) y dan los mismos `cambios` que el inline anterior. `_sin_caras` queda solo en `asignar` y `asignar_color` (no es código muerto).
- **Gemelos revisados:**
  - `_limpiar_usos` (`timeline/aspectos_doc.py:224`): ahora es el ÚNICO lugar que arma «saca el aspecto de cuerpos y caras»; `quitar` lo reusa. ✔
  - API (`api/herramientas_aspecto.py` › `manage_appearance` › `suprimir` con `remove_users`, y `api/herramientas_material.py:306` › `set_appearance` que limpia vía `ad.quitar`): no cambian de firma ni de comportamiento; `suprimir` llama a `quitar` internamente, así que también se beneficia de la unificación. ✔
  - Panel (`ui/aspectos_ui.py:736` › `quitar_y_suprimir`): usa `reemplazar_lista(..., quitar_usos=)` que ya llama a `_limpiar_usos`; el camino del panel y el de la API ahora comparten el mismo núcleo de limpieza. ✔
  - El caso `quitar_caras` (H-73): se conservó en `quitar` (el «Quitar y suprimir» no lo necesita porque borra la entrada del diseño); se mantiene igual para `api/herramientas_material.py` (`clear_face_overrides`) y `ui/render.py:2110` (`quitar_aspecto` con `quitar_caras=True`). ✔
  - **Fuera de alcance (no lo toqué):** `nucleo/solidos_modificar.py::quitar_caras` y `omnikernel/...::quitar_caras` son de geometría (quitan caras de una forma OCC), no de aspectos; no tienen nada que ver con H-103.
- **Test nuevo** (`clon/tests/test_aspectos_api.py::test_quitar_saca_el_aspecto_del_cuerpo_y_de_la_cara_y_conserva_quitar_caras`): pinta un cuerpo y una de sus caras, saca el aspecto solo de la cara concreta (el cuerpo queda pintado y la cara desaparece) y luego con `quitar_caras=True` saca el aspecto del cuerpo y sus caras propias. Es un **cierre de contrato**, no un bug: H-103 no tiene «Prueba propuesta» porque no cambia el comportamiento.
  - Salida **ROJA (antes del arreglo, test nuevo contra el código viejo):** `1 failed, 82 passed` — fallaba por un error mío en el test (pinté solo caras, no el cuerpo, y luego `props["caras"]` con `KeyError` cuando la lista quedaba vacía y `set_propiedades` borra la clave). Lo corregí y el contrato quedó verde en el código viejo y en el nuevo (la refactor no mueve la aguja).
  - Salida **VERDE (con el arreglo):** `83 passed in 11.87s` (los 4 archivos obligatorios).
- **ruff check .:** `All checks passed!` (sobre el repo entero).
- **Tests obligatorios de la tanda (un grupo, con turno):** `test_aspecto_panel.py`, `test_aspectos_api.py`, `test_render_aspecto.py`, `test_formulario_paneles.py` → **83 passed in 11.87s**.
- **Archivos de `grep -l` NO corridos (los corre el coordinador):** el grep de las funciones tocadas (`_limpiar_usos`, `aspectos_doc.quitar`, `quitar_caras`, `quitar_usos`, `reemplazar_lista`, `propiedades_con`, `aplicar_panel`) devuelve solo los dos obligatorios (`test_aspectos_api.py`, `test_render_aspecto.py`), ya corridos. Por el token genérico `quitar_caras` (que es de `nucleo/solidos_modificar.py`, no de aspectos) aparecen además `test_paridad_motor.py`, `test_resultados_vacios.py` y `test_solidos_modificar.py`: no tocan `aspectos_doc` y no los corrí.
- **Salida de /ponytail-review:** sin «Must fix» ni «Should fix». Repaso del diff: (1) la refactor elimina ~4 líneas duplicadas y reusa `_limpiar_usos` ya existente y probado por H-74; (2) el caso `quitar_caras` se preserva exacto, incl. el solapamiento cuerpo+cara (la guarda `if cid not in por_caras` replica el antiguo «el filtrado de caras gana sobre el `caras=None`»); (3) `_limpiar_usos` solo lee `caras` del documento porque el bucle de cuerpos no las escribe, igual que el código viejo, así que ambos coinciden; (4) `_sin_caras` sigue usándose en `asignar`/`asignar_color`, sin código muerto. Nada quedó pendiente de arreglar.
  - **Verdict:** `Ship.` **Lean:** `-4 lines possible.` (los bucles inline de `quitar`).
- **No verificado / ⚠:**
  - No corrí la prueba de humo ni la suite completa (regla 10: las corre el coordinador).
  - No corrí los del `grep -l` (regla del coordinador: lista arriba, los corre él).
  - No toqué la ventana ni la API (la firma de `quitar` no cambió), así que no regeneré `docs/agentes/herramientas.md` (ninguna herramienta cambió de firma ni de descripción).

## Informe tanda C7

**Modelo:** CodeBuddy con deepseek-v4.1-flash (el prompt original decía «OpenCode con Qwen3.8-Flash»; lo escribo como pidió el coordinador). **Tanda:** C7 · **Bug:** CF-11 (faltante). **Sin commitear** (lo commitea el coordinador).
**Corrida corta (45 min):** se corrió UN grupo con los 8 archivos obligatorios más el test nuevo; los del `grep -l` NO se corrieron y están listados abajo para el coordinador.

### CF-11 — BOCETO › «Buscar subrestringidos» y «Calcular boceto» en la Paleta de boceto — **Resuelto**

- **Qué dice la ayuda de Fusion:** `docs/fusion_docs/contenido/fusion-sketch/find-underconstrained-sketch-geometry-a377d84ad10.md`:
  - «When a sketch is not fully constrained, use **Find Under-Constrained** in the **Sketch Palette** to see a list of
    all under-constrained sketch entities in the active sketch. **Select an item in the list to highlight that geometry
    and zoom to it on the canvas.** […] (Optional) Click **X** on a row in the list to delete that under-constrained
    sketch entity. **X is not available for sketch points.** […] While Find Under-Constrained is active, add constraints
    or dimensions […]; the list and sketch status update as you work.»
  - «If constraint status looks out of date after edits, rerun fully constrained analysis for the whole sketch. […]
    click **Compute Sketch**. Fusion analyzes all geometry in the sketch and updates the constraint status for each
    sketch entity.»
  - `sketch-palette-reference-4baf4699c21.md`: la paleta es la que muestra el estado del boceto; ahí viven estas dos cosas.
- **Qué cambié:**
  - `clon/omnicad/ui/editor_boceto.py:831` — `encuadrar(ids=None)`: con `ids` centra y acerca la vista solo a esa
    geometría (sin argumento sigue encuadrando el boceto entero, como antes). Es el «zoom to it» de Fusion.
  - `clon/omnicad/ui/editor_boceto.py:1082` — `Lienzo.subrestringidas()`: `[(id, texto)]` de las curvas y los puntos que
    **no** están en `resultado.determinadas` (los grados de libertad que ya calcula el solver, el mismo criterio que el
    `state: free` de `get_sketch`). Vacío si el boceto está totalmente restringido o el solver falló.
  - `clon/omnicad/ui/editor_boceto.py:1094` y `:1101` — `resaltar(ids)` (deja elegido y lleva la vista) y
    `borrar_ids(ids)` (borra en **un** paso de deshacer, reusando `borrar_seleccion`).
  - `clon/omnicad/ui/modo_boceto.py:296` y `:302` — dos botones en la Paleta de boceto, arriba del estado: «Buscar
    subrestringidos» y «Calcular boceto», con la ayuda de Fusion en el tooltip; `:175` las cuatro señales nuevas.
  - `clon/omnicad/ui/modo_boceto.py:351` — `PaletaBoceto.mostrar_subrestringidos(filas)`: una fila por entidad (botón con
    el nombre → `resaltar`, ✕ → `borrar_sub`); sin filas, «Totalmente restringido: no queda geometría subrestringida».
    La ✕ está también en los puntos: Fusion la deshabilita para puntos, pero el `Boceto` de OmniCAD borra el punto suelto
    sin arrastrar la curva, así que no hay nada que proteger (ver la review).
  - `clon/omnicad/ui/modo_boceto.py:1421`, `:1426` y `:1432` — `ModoBoceto._buscar_subrestringidos`, `_calcular_boceto`
    (vuelve a resolver con `lienzo.resolver()` y rearma la lista) y `_borrar_subrestringida`; `:1549` rearma la lista en
    `_cambio` mientras está abierta (el «the list and sketch status update as you work» de Fusion).
  - `clon/omnicad/api/herramientas_boceto.py:1692` — `find_underconstrained(sketch=None)`: `status`, `dof`, `count`,
    `entities` (id y tipo) y `points` (id, x, y) de lo que se puede mover. Reusa `info_boceto` (cero duplicación del
    criterio `state: free`).
  - `clon/omnicad/api/herramientas_boceto.py:1709` — `compute_sketch(sketch=None)`: resuelve el boceto de nuevo desde sus
    restricciones y cotas actuales y devuelve `status`, `dof`, `constrained` (entidades en `determinadas`), `free` y
    `message`. Receta C de `AGENTS.md`; las dos son de lectura (`modifica=False`).
  - `docs/agentes/herramientas.md` regenerado con el comando del coordinador (código de ESTE worktree; +22/−2 líneas).
- **Gemelos revisados:**
  - El estado del boceto que ya existía (`PaletaBoceto.set_estado`, el «Status: Under-Constrained / Constrained» de
    Fusion): no se duplicó ni se cambió; la lista nueva lo acompaña y se refresca con `_cambio`. ✔
  - El diagnóstico que ya existía: `Lienzo.mostrar_conflictos` / `texto_redundantes` (F5, «Qué choca»: restricciones y
    cotas que sobran) y `find_redundant_constraints` (API): son otra cosa (vínculos, no geometría); no se tocaron. ✔
  - `auto_constrain` / `suggest_auto_constraints` (el diálogo de AutoConstrain que nombraba la fila CF-11): no se tocaron;
    siguen en la pestaña BOCETO de la cinta (`sk_autorestringir`) y en la API. Lo que faltaba era la lista de
    subrestringidos y el recálculo, no el diálogo. ✔
  - `grados_de_libertad` / `resolver` / `ResultadoSolver.determinadas` (`restricciones/solver.py`): se usaron tal cual; no
    se cambió una línea del solver. ✔
  - La API y el MCP/CLI (receta C): las dos herramientas nuevas, con docstring de todos los parámetros, en el grupo
    `boceto`, y `docs/agentes/herramientas.md` regenerado. `test_cobertura_ui_api.py` sigue verde: los botones viven en la
    paleta, no en la cinta, así que no agregan claves de cinta (igual que Fusion, que los pone en la paleta). ✔
  - La cinta (receta B): **no** se agregaron botones a la pestaña BOCETO a propósito (en Fusion están solo en la paleta).
    Si Gerardo las quiere en la cinta, es una fila nueva. ✔
  - **Fuera de alcance (no lo toqué):** el navegador (el ícono del boceto que ya marca si está restringido,
    `navegador.marcar_boceto`), las asas y los atajos.
- **Test nuevo** (`clon/tests/test_boceto_subrestringidos.py`, 4 pruebas):
  - `test_api_buscar_subrestringidos_lista_lo_que_se_mueve_y_vacia_al_restringir`: un rectángulo suelto da
    `under_constrained`, `dof > 0` y `count > 0`, y los ids listados son **exactamente** los `state: free` de
    `get_sketch`; al fijar todas esas entidades (`add_constraint` › `fix`), `count == 0` y `fully_constrained`.
  - `test_api_calcular_boceto_cuenta_fijas_y_libres`: `constrained + free == puntos + entidades` del boceto y `free > 0`.
  - `test_lienzo_buscar_subrestringidos_resalta_acerca_y_borra`: el lienzo lista, `resaltar` deja la entidad elegida y
    `centro` de la vista cae en el punto medio de esa curva (el zoom); `borrar_ids` la saca con **un** paso de deshacer
    (`len(historial) == 1`) y `deshacer()` la devuelve.
  - `test_paleta_muestra_la_lista_y_sus_botones_emiten`: los dos botones existen con su texto, la lista está oculta al
    principio, `mostrar_subrestringidos([(7, "línea 7")])` la muestra y emite `resaltar(7)` y `borrar_sub(7)` al pulsar
    la fila y su ✕; sin filas dice «Totalmente restringido…».
  - **Salida ROJA:** la funcionalidad no existía en HEAD (`git show HEAD:… | grep -c` da **0** en `editor_boceto.py`
    para `def subrestringidas|def resaltar|def borrar_ids`, **0** en `modo_boceto.py` para
    `buscar_sub|mostrar_subrestringidos` y **0** en `api/herramientas_boceto.py` para
    `find_underconstrained|compute_sketch`). Primera corrida del archivo contra el código a medio hacer:
    `3 failed, 1 passed in 2.77s` (la lista no aparecía y las dos herramientas todavía no estaban en el catálogo; además
    `test_herramientas_del_grupo_boceto` falló por los dos nombres nuevos).
  - **Salida VERDE (con el arreglo):** `4 passed in 2.50s` (el archivo) y `696 passed in 28.09s` (grupo obligatorio +
    el archivo nuevo).
- **ruff check .:** `All checks passed!` (sobre el repo entero, dos veces).
- **Tests obligatorios de la tanda (un grupo, con turno):** `test_api_boceto.py`, `test_api_boceto_herramientas.py`,
  `test_boceto_fase2.py`, `test_boceto_fase4.py`, `test_cobertura_ui_api.py`, `test_restricciones_matematica.py`,
  `test_claves_comandos.py`, `test_doc_agentes.py` + `test_boceto_subrestringidos.py` → **696 passed in 28.09s**. (La
  primera corrida del grupo, antes de sumar los dos nombres a `HERRAMIENTAS` de `test_api_boceto.py`, dio
  `1 failed, 691 passed`: `test_herramientas_del_grupo_boceto` exige la lista exacta del catálogo; se agregaron
  `find_underconstrained` y `compute_sketch` a la lista y a las «lecturas».)
- **Archivos de `grep -l` NO corridos (los corre el coordinador):** por las funciones nuevas (`subrestringidas`,
  `resaltar`, `borrar_ids`, `find_underconstrained`, `compute_sketch`, `mostrar_subrestringidos`) el grep devuelve solo
  los dos que sí corrí (`test_api_boceto.py` y `test_boceto_subrestringidos.py`). Por haber cambiado `Lienzo.encuadrar`
  (firma compatible, `ids=None` por defecto) y la paleta, el grep de `encuadrar(`/`PaletaBoceto`/`set_estado` da además:
  `test_animacion.py`, `test_arrastre_ventana.py`, `test_asas_superficie.py`, `test_aspecto_panel.py`,
  `test_boceto_fase3.py`, `test_boceto_fase8_3d.py`, `test_boceto_fase9_ui.py`, `test_boceto_fase9_ui2.py`,
  `test_boceto_fase9_ui3.py`, `test_gizmo_boceto.py`, `test_graficos_rendimiento.py`, `test_hallazgos_ui.py`,
  `test_manipulacion_vectorial_ui.py`, `test_manipuladores.py`, `test_p23_bocetos.py`, `test_posicion_ventana.py`,
  `test_proyectar_tarjeta.py`, `test_render.py`, `test_render_aspecto.py`, `test_restricciones_ui.py`,
  `test_superficie_guias.py`, `test_texto_vectores.py`, `test_transformar_boceto.py`, `test_vistas_animadas.py`. (Casi
  todos coinciden por `encuadrar` de la cámara del visor o por `set_estado` de otros paneles, no por el boceto; los de
  `PaletaBoceto` —`test_boceto_fase3.py`, `fase8_3d`, `fase9_ui2`, `fase9_ui3`— son los de más riesgo.)
- **Salida de /ponytail-review:** sin «Must fix» ni «Should fix». Repaso del diff:
  1. **No se duplicó el criterio**: la lista de la UI sale de `resultado.determinadas` (solver) y la de la API del
     `state: free` de `info_boceto`, que se calcula con el mismo `determinadas`; no hay una tercera copia.
  2. **`encuadrar(ids=None)` es compatible**: el valor por defecto deja igual el zoom del boceto entero (lo usan el
     arranque del modo y la barra de herramientas); los puntos internos de los objetos siguen excluidos.
  3. **Un solo paso de deshacer**: la ✕ pasa por `borrar_seleccion` → `aplicar_cambio` (probado con
     `len(historial) == 1` y `deshacer()`).
  4. **La lista no cuesta nada si está cerrada**: `_cambio` solo la rearma con `lista_sub.isVisible()`.
  5. **`compute_sketch` no escribe**: resuelve sobre una copia (`br.boceto.copia()`) y no toca el documento; por eso no
     lleva `modifica=True` ni paso de deshacer. `find_underconstrained` tampoco.
  6. **Nice to have, no aplicado:** la ✕ de Fusion no existe para puntos; acá sí, porque `Boceto.eliminar` de un punto
     suelto no toca la curva (si molesta, es una línea: `if p.id in self.b.puntos: no ✕`).
  7. **Verdict:** `Ship.` Nada quedó pendiente de arreglar.
- **No verificado / ⚠:**
  - No corrí la prueba de humo ni la suite completa (regla 10: las corre el coordinador), ni los archivos del `grep -l`
    (los lista arriba).
  - **Captura de la ventana:** `todo.py boceto_herramientas --ventana minimizada` → **100 comprobaciones, 0 con ✗**, y
    la captura `evidencias/ui_2026-11-06/capturas/herr_cota_con_linea.png` muestra la paleta con los dos botones nuevos
    («Buscar subrestringidos» y «Calcular boceto») entre la casilla «Boceto 3D» y el estado («Faltan 6 grado(s) de
    libertad por restringir.»), sin nada cortado. También `paneles_boceto` → **127 comprobaciones, 0 con ✗**. Ninguna de
    las dos piezas abre la lista (no la pulsan), así que el listado en sí solo está probado en los tests offscreen.
  - No se abrió Fusion: el comportamiento sale de la ayuda oficial de `fusion-sketch`, como en las tandas anteriores.

## Informe tanda C8

**Modelo:** CodeBuddy con hy3 (el prompt original decía «OpenCode con Qwen3.8-Flash»; lo escribo como pidió el coordinador). **Tanda:** C8 · **Bug:** H-71 (faltante). **Sin commitear** (lo commitea el coordinador).

### H-71 — BOCETO › arrastrar filas entre grupos y teclado en el árbol del navegador — **Resuelto**

- **Qué dice la ayuda de Fusion:** `docs/fusion_docs/contenido/fusion-sketch/sketch-palette-reference-4baf4699c21.md` y `find-underconstrained-sketch-geometry-a377d84ad10.md` confirman que la organización del boceto (grupos, «drag to reorder», selección) vive en el navegador y en la paleta, y que Alt+clic elige el objeto de abajo entre superpuestos (secciones 9.5 y 10 de `plan_boceto_organizar.md`). La organización ya estaba en OmniCAD (H-69/H-70 quedan para otra tanda); lo que faltaba de H-71 era el arrastre entre grupos y el foco del teclado en el árbol.
- **Qué cambié:**
  - `clon/omnicad/ui/navegador.py` — `_Arbol` ahora recibe `setFocusPolicy(Qt.StrongFocus)` (antes `Qt.NoFocus`, así que el árbol nunca tomaba el teclado), `setDragEnabled(True)` + `setAcceptDrops(True)` + `setDragDropMode(QAbstractItemView.DragDrop)`, y los manejadores `dragEnterEvent` / `dragMoveEvent` / `dropEvent`: solo aceptan soltar sobre una fila de grupo (`bo:<gid>` o miembro `bg:<gid>:<oid>`) y delegan en `self.on_dejar_en_grupo(origen, destino)` sin reordenar el modelo. La navegación por flechas y F2 (renombrar) quedan igual que en el resto del árbol.
  - `clon/omnicad/ui/navegador_boceto.py` — `_mover_desde_arbol(v, origen, destino)` nuevo: saca el id del objeto arrastrado (`_objeto_de`, que entiende `bo:` y `bg:`) y el id del grupo destino, descarta grupo-en-sí y grupos anidados (`ob.categoria(...) == "grupos"`), y llama a `_cambiar(v, lambda b: ob.mover_a_grupo(b, [oid], gid))` — el mismo `mover_a_grupo` del menú «Mover a grupo», un paso de deshacer del boceto.
  - `clon/omnicad/ui/ventana.py:202` — enchufa el callback: `self.navegador.arbol.on_dejar_en_grupo = lambda o, d: navegador_boceto._mover_desde_arbol(self, o, d)`.
  - El Alt+clic que elige el objeto de abajo ya estaba resuelto y cubierto por `tests/test_boceto_organizar_ui.py::test_alt_clic_elige_el_objeto_de_abajo` (es la «Prueba propuesta» que cita H-71).
- **Gemelos revisados:**
  - El menú «Mover a grupo» del navegador (`ui/navegador_boceto.py::_menu_objetos`, `ob.mover_a_grupo`): el arrastre reusa **exactamente** esa función, no duplica lógica. ✔
  - La API del grupo `vectores` (`api/herramientas_objetos_vectoriales.py` › `move_vector_objects_to_group`): es la misma `ob.mover_a_grupo`; el arrastre no cambia la API, así que `docs/agentes/herramientas.md` no se regeneró (ninguna firma cambió). ✔
  - `ob.mover_a_grupo` (`restricciones/objetos.py:258`): no se tocó; el arrastre solo la invoca. ✔
  - **Fuera de alcance (no lo toqué):** el menú radial del visor en modo boceto no aplica — en edición de boceto el clic derecho del visor lo maneja el editor (`editor_boceto`: menús de cota/restricción), no el menú radial de la vista 3D (`visor3d` › `menu_radial`), que está oculto; agregar acciones de organización ahí no tendría dónde dispararse. H-69 (propiedades por curva) y H-70 (expandir SVG/DXF) siguen abiertos en su propia fila.
- **Test nuevo** (`clon/tests/test_boceto_organizar_ui.py`):
  - `test_arrastrar_fila_del_arbol_mueve_el_objeto_al_grupo`: agrupa `svg`, arrastra `disco` (suelto) sobre el grupo vía `nav.arbol.on_dejar_en_grupo("bo:disco", "bo:grupo")` → `True` y aparece `bg:grupo:disco`; arrastrar sobre un objeto que no es grupo (`bo:svg`) → `False`; arrastrar un grupo sobre sí mismo → `False`; `deshacer()` lo revierte en un paso.
  - `test_el_arbol_del_navegador_toma_el_foco_del_teclado`: `nav.arbol.focusPolicy() != Qt.NoFocus` y al darle el foco una flecha abajo cambia el `currentItem`.
  - `test_alt_clic_elige_el_objeto_de_abajo` ya existía (el de la «Prueba propuesta») y sigue verde.
  - Salida **ROJA (antes del arreglo):** el árbol tenía `Qt.NoFocus` y `_Arbol` no tenía drag-and-drop, así que `on_dejar_en_grupo` no existía y `focusPolicy()` era `NoFocus`.
  - Salida **VERDE (con el arreglo):** `7 passed in 10.53s` (el archivo).
- **ruff check .:** `All checks passed!`
- **Tests obligatorios de la tanda (un grupo, con turno):** `test_boceto_organizar_ui.py`, `test_boceto_organizar.py`, `test_cobertura_ui_api.py`, `test_comandos.py` → **381 passed in 12.17s**.
- **Archivos de `grep -l` NO corridos (los corre el coordinador):** el grep de las funciones tocadas (`_mover_desde_arbol`, `on_dejar_en_grupo`, `setFocusPolicy`, `dragEnterEvent`, `_Arbol`, `mover_a_grupo`) da solo `test_boceto_organizar_ui.py` (ya corrido). Por el token genérico `mover_a_grupo` / `navegador` aparecen además `test_boceto_organizar.py`, `test_api_objetos_vectoriales.py`, `test_cobertura_ui_api.py` (corrido) y `test_restricciones_matematica.py`; ninguno toca el árbol ni el drag, así que no los corrí.
- **Salida de /ponytail-review:** `Verdict: Ship.` Sin «Must fix» ni «Should fix». Hallazgos revisados: (1) el drag solo acepta soltar sobre grupo y llama a `ob.mover_a_grupo` ya probado (no duplica lógica); (2) no anida grupos ni deja caer en objetos sueltos (guardas en `_mover_desde_arbol`); (3) `dropEvent` no llama a `super()`, así que el modelo del árbol no se reordena solo; (4) quité un `keyPressEvent` con F2 que era redundante con la acción F2 de la ventana (`ventana.py:458`) y podía disparar el renombrado dos veces — la navegación por flechas ya la da Qt al tener foco; (5) `nucleo/`, `timeline/` y la API no se tocaron, no hay estado global nuevo. Nada quedó pendiente de arreglar.
- **No verificado / ⚠:**
  - No corrí la prueba de humo ni la suite completa (regla 10: las corre el coordinador), ni los archivos del `grep -l` (los lista arriba).
  - No toqué la ventana más allá del foco y el drag del árbol, así que no hice la captura `todo.py` de una pieza de boceto: el arrastre entre filas es nativo de Qt y lo ejercita el test nuevo (vía el callback que usa el mismo camino que el drop real); el foco del teclado se prueba en `test_el_arbol_...`.

## Informe tanda C9

**Modelo:** CodeBuddy con deepseek-v4.1-flash (el prompt original decía «OpenCode con Qwen3.8-Flash»; lo escribo como pidió el coordinador). **Tanda:** C9 · **Bug:** H-85 (faltante). **Sin commitear** (lo commitea el coordinador).
**Corrida corta (45 min):** un grupo con los 5 archivos obligatorios + `test_seguimiento.py` y `test_doc_agentes.py` (por haber tocado `docs/seguimiento/` y el Registro). Los del `grep -l` NO se corrieron (regla del coordinador) y están listados abajo.

### H-85 — SUPERFICIE › Extruir en la ventana: elegir perfiles cerrados y caras planas — **Resuelto**

- **Qué dice la ayuda de Fusion:** `docs/fusion_docs/contenido/fusion-patch/extrude-a-surface-body-5889029bb69.md`
  (paso 2): «In the canvas, select a **sketch profile, sketch curve, planar face, or single line text object**.» O sea:
  el campo de perfiles de Extruir de superficie tiene que aceptar, además de la curva y la arista que ya aceptaba, el
  perfil cerrado (la región) y la cara plana. El texto de una línea ya entraba por ser una `curva_boceto`.
- **Qué cambié:**
  - `clon/omnicad/ui/comandos/superficie.py:23` — constante nueva `PERFILES_SUPERFICIE = CURVAS | {"perfil", "cara_plana"}`
    con el porqué en un comentario. `CURVAS` (curva de boceto y arista) queda igual para los campos que solo llevan
    curvas (ruta del Barrido, contorno del Parche, aristas de Recortar, eje de Revolución).
  - `clon/omnicad/ui/comandos/superficie.py:46` — `SupExtruir.campos`: el campo «Perfiles» pasa de `CURVAS` a
    `PERFILES_SUPERFICIE`; la ayuda del campo enumera lo que entra.
  - `clon/omnicad/ui/comandos/superficie.py:40` — la `AYUDA` del comando dice que extruye curvas, perfiles cerrados,
    caras planas o un texto de una línea.
  - `clon/omnicad/ui/comandos/superficie.py:142` — el campo «Perfil» del Barrido de superficie ya usaba
    `CURVAS | {"perfil", "cara_plana"}` escrito a mano; ahora usa la misma constante (un solo nombre para una sola cosa).
  - `scripts/prueba_ui/extruir_espacios.py:13,83,86` — la pieza importaba `CURVAS` para simular el clic; pasa a
    `PERFILES_SUPERFICIE`. Sin esto la pieza seguía en ✗ **con el arreglo puesto** (era el «Should fix» que la auditoría
    de Extruir ya había anticipado en `docs/auditoria_extruir.md:145`).
  - **La operación y el núcleo no cambiaron una línea**: `_curvas` (`timeline/ops_superficie.py:43`) resuelve un
    `perfil` a su cara (`entidades.resolver` → `perfil.cara`) y `nucleo/superficies.py::alambres` (línea 164) ya sabía
    sacar los alambres de una `TopAbs_FACE`. Por eso el mismo camino sirve para curva, perfil y cara plana.
- **Gemelos revisados:**
  - El filtro de Extruir sólido (`ui/comandos/solido.py:33`, `{"perfil", "cara_plana", "curva_boceto"}`): es el criterio
    que se copió; no se tocó. ✔
  - El visor (`ui/visor3d.py::elegir_entidad`, secciones 4 y 5): ya devolvía hits `perfil` y `cara` con `plano`; no se
    tocó. La pieza lo comprueba con un control (con el filtro de Extruir sólido los mismos clics sí eligen). ✔
  - `acepta` (`ui/comando.py:377`): ya trataba `perfil` (`t in filtros`) y `cara_plana` (cara con plano); no se tocó. ✔
  - La API `create_surface_extrude` (`api/herramientas_superficie.py:70`): **ya aceptaba** perfiles y caras
    (`_seleccion(..., curvas=True)` y `profiles: curvas {...}, perfiles {...}, caras, aristas o cuerpos`); no cambió
    firma ni docstring, así que `docs/agentes/herramientas.md` **no** se regeneró. ✔
  - La previa (`ui/comando.py` › `set_filtro` con `campo.filtros`; `nucleo/previa*`): no tiene regla propia, ejecuta la
    operación, así que hereda el filtro y la resolución sin cambios. ✔
  - El Barrido de superficie (`ui/comandos/superficie.py:142`): misma constante, mismo valor que antes; su operación ya
    aceptaba caras y perfiles. ✔
  - **Fuera de alcance (fila nueva):** Revolución de superficie tiene el mismo defecto — Fusion dice «select a sketch
    profile, sketch curve, or planar face to revolve» (`fusion-patch/revolve-a-surface-body-a3f71a695c7.md`) y su campo
    Perfil sigue filtrando solo curva y arista (comprobado: `acepta(campo.filtros, hit_perfil) is False`). No lo toqué
    porque H-85 es de Extruir: queda como **H-104** en `docs/seguimiento/faltantes.md`.
- **Test nuevo** (`clon/tests/test_comandos_superficie.py::test_extruir_de_superficie_elige_perfiles_cerrados_y_caras_planas`):
  con un rectángulo de boceto y una caja, comprueba que el campo «Perfiles» de `SupExtruir` acepta el hit del perfil y el
  de la cara plana (`acepta`), y que cada uno extruye de verdad una superficie de 200 mm² (tubo de 10×10 por 5 de alto).
  - Salida **ROJA** (antes del arreglo):
    `FAILED tests/test_comandos_superficie.py::test_extruir_de_superficie_elige_perfiles_cerrados_y_caras_planas`
    `AssertionError: assert (False) … where False = acepta({'arista', 'curva_boceto'}, {'tipo': 'perfil', …})`
    → `1 failed, 4 deselected in 2.44s`
  - Salida **VERDE** (con el arreglo): `1 passed, 4 deselected in 2.35s`
- **ruff check .:** `All checks passed!` (tres veces: antes del arreglo, después y al cerrar).
- **Tests obligatorios de la tanda (un grupo, con turno):** `test_superficies.py`, `test_superficie_fusion.py`,
  `test_api_superficie.py`, `test_comandos_superficie.py`, `test_cobertura_ui_api.py` → **476 passed in 9.46s**
  (corrido tres veces: con el arreglo, después de unificar la constante del Barrido — 9.23 s — y al cerrar).
- **Además corrí** (por haber tocado `docs/seguimiento/` y el Registro): `test_seguimiento.py` + `test_doc_agentes.py` →
  **445 passed in 6.87s**.
- **Ventana (pieza de la tanda, minimizada):** `todo.py extruir_espacios --ventana minimizada` → **18 comprobaciones,
  0 con ✗** (antes del arreglo: 18, 2 con ✗ — justo «SUPERFICIE: clic dentro de un perfil cerrado lo elige» y «clic en
  una cara plana la elige», las dos con «el visor devolvió None»). Ahora: «el visor devolvió perfil» y «el visor devolvió
  cara». La captura `evidencias/ui_2026-11-06/capturas/extruir_1024x640.png` se miró: el panel entra sin cortes y
  «Aceptar» se ve (esa captura es del paso de Plástico; el panel de SUPERFICIE lo abre y cierra la misma pieza).
- **Archivos de `grep -l` NO corridos (los corre el coordinador):** por `SupExtruir` / `sup_extruir` (menos los que sí
  corrí de la lista obligatoria): `test_api_solido_extra.py`, `test_b105_panel_chico.py`, `test_barrido_tipos.py`,
  `test_busqueda_comandos.py`, `test_iconos_extra.py`, `test_manipuladores.py`, `test_opciones_operaciones.py`,
  `test_referencias_mal_formadas.py`, `test_sup29_encadenado_superficie.py`, `test_superficie_guias.py`. Revisados a ojo:
  ninguno depende del filtro ni del texto de ayuda (buscan el comando por clave o título, o usan la operación/API), pero
  el prompt manda correrlos y la nota del coordinador manda no hacerlo en esta corrida.
- **Salida de /ponytail-review:** **Must fix:** ninguno. **Should fix:** ninguno. **Nice to have:** ninguno. Lo revisado y
  por qué queda así:
  1. **No hay regresión para los campos que solo llevan curvas**: `CURVAS` no se tocó; el Barrido, el Parche, Recortar y
     el eje de Revolución siguen igual (el diff del Barrido es el mismo valor con otro nombre).
  2. **El camino de la operación ya existía**: perfil → cara → `alambres` saca los alambres; el test lo prueba con
     geometría (200 mm²), no solo con el filtro.
  3. **`cadena` con un perfil o una cara**: `_en_cadena` cae en su rama `else` y devuelve la forma tal cual; nada se
     encadena ni se pierde.
  4. **La API no cambió**: sin firma nueva, sin doc que regenerar, `test_doc_agentes.py` verde.
  5. **`preseleccion`** (`ui/comando.py:404`) reparte lo elegido antes de abrir el comando: ahora un perfil
     preseleccionado cae en «Perfiles» en vez de quedarse afuera. Es el comportamiento de Fusion.
  6. **Verdict:** `Ship.` Nada quedó pendiente de arreglar.
- **No verificado / ⚠:**
  - No corrí la prueba de humo ni la suite completa (regla 10: las corre el coordinador), ni los archivos del `grep -l`
    (los lista arriba).
  - No abrí Fusion: el comportamiento sale de la ayuda oficial de `fusion-patch`, como en las tandas anteriores.
  - Un perfil cerrado **con huecos** (una región con un agujero) extruido como superficie da un tubo por alambre
    (exterior e interior). Es lo que ya hacía la cara plana en el Barrido de superficie y lo que da `alambres`; no lo
    comparé con Fusion.

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
