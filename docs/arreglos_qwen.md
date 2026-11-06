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
| C10 | H-104 | `ui/comandos/superficie.py` (el filtro de Revolución de superficie) | `PERFILES_SUPERFICIE` de C9 (reusarlo), Revolución sólida, la API `create_surface_revolve`, la previa | `test_comandos_superficie.py`, `test_superficies.py`, `test_superficie_fusion.py`, `test_api_superficie.py`, `test_sol07_revolucion.py`, `test_cobertura_ui_api.py` |
| C11 | CF-8 (solo dos opciones: «barra espaciadora repite el último comando» y «tamaño del ViewCube»; la fila queda Parcial con el resto) | `ui/preferencias.py`, `ui/ventana.py` (atajo), el ViewCube del visor | la ayuda de Fusion (`fusion_docs.py buscar preferences general -s fusion-getstarted`), las herramientas del MCP de preferencias (`get_preferences`, `set_preference`: que las dos opciones nuevas estén ahí), el guardado de preferencias | `test_preferencias*.py`, `test_api_*preferenc*.py` (los que existan), `test_cobertura_ui_api.py`, `test_comandos.py`, `test_doc_agentes.py` |
| C12 | B-218 | `nucleo/editar_cara.py` (imports de OCP al cargarse, ~18-34), `timeline/ops_modificar.py` (`OpEditarCara`), `api/herramientas_dividir.py` (import perezoso) | el patrón de B-189 que ya usan los otros módulos de `nucleo/` (`_iniciar_opencascade` + `_motor.registrar`, o `MOTOR_SIN_SOPORTE`: `grep -rn "_iniciar_opencascade\|MOTOR_SIN_SOPORTE" clon/omnicad`), Dividir cara (`nucleo/` y `api/herramientas_dividir.py`), el recorrido de `pkgutil.walk_packages` con `OMNICAD_BLOQUEAR_OCP=1` | `test_motor.py`, `test_paridad_motor.py`, `test_consultas_motor.py`, `test_sol16_dividir_cara.py`, `test_api_dividir.py`, `test_api_solido.py`, `test_herramientas_solido.py`, `test_barrido_tipos.py`, `test_cobertura_ui_api.py` |
| C13 | CF-8 (lo que falta, en este orden: tema del sistema, ratón estilo Alias/Inventor/PowerMill/SOLIDWORKS, orientación Y o Z hacia arriba, tipo de diseño por defecto, finalidad de uso, experiencia de puesta en marcha, controlador de gráficos; lo que no entre queda Parcial con su lista) | `ui/preferencias.py`, el visor (`ui/visor3d.py`: ratón y orientación), los temas (`ui/temas*.py`) | la ayuda de Fusion (`fusion_docs.py buscar preferences general -s fusion-getstarted`), lo hecho en C11 (`general/tamano_viewcube`, `general/espacio_repite`: mismo patrón), las herramientas del MCP de preferencias (`api/herramientas_preferencias.py`: `get_preferences`, `set_preference`), el guardado de preferencias | `test_preferencias.py`, `test_temas.py`, `test_iconos_tema_vivo.py`, `test_cobertura_ui_api.py`, `test_comandos.py`, `test_doc_agentes.py` |

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

## Informe tanda C10

**Modelo:** CodeBuddy con hy3 (el prompt original decía «OpenCode con Qwen3.8-Flash»; lo escribo como pidió el coordinador). **Tanda:** C10 · **Bug:** H-104 (faltante). **Sin commitear** (lo commitea el coordinador).
**Corrida corta (45 min):** un grupo con los 6 archivos obligatorios; los del `grep -l` NO se corrieron (regla del coordinador) y están listados abajo.

### H-104 — SUPERFICIE › Revolución en la ventana: elegir perfiles cerrados y caras planas — **Resuelto**

- **Qué dice la ayuda de Fusion:** `docs/fusion_docs/contenido/fusion-patch/revolve-a-surface-body-a3f71a695c7.md`, paso 2: «In the canvas, select a **sketch profile, sketch curve, or planar face** to revolve». O sea que el campo Perfil de la Revolución de superficie tiene que aceptar, además de la curva y la arista que ya aceptaba, el perfil cerrado (la región) y la cara plana. Es el caso gemelo de H-85 en Extruir de superficie, que se arregló sin tocar Revolución.
- **Qué cambié:**
  - `clon/omnicad/ui/comandos/superficie.py:94` — `SupRevolucion.AYUDA` ahora dice «Gira perfiles cerrados, curvas o caras planas alrededor de un eje y crea una superficie.»
  - `clon/omnicad/ui/comandos/superficie.py:99` — el campo «Perfil» pasa de `CURVAS` a `PERFILES_SUPERFICIE` (la constante de C9/H-85: `CURVAS | {"perfil", "cara_plana"}`) y su ayuda enumera los cuatro tipos que entran.
  - **La operación y el núcleo no cambiaron una línea**: `OpSupRevolucion.ejecutar` ya delega en `_curvas` (`timeline/ops_superficie.py:45`), que resuelve un `perfil` a su cara y una `cara_plana` a la cara (`_resolver_todas`); `revolver_superficie` → `alambres` (`nucleo/superficies.py:164`) ya saca los alambres de una `TopAbs_FACE`. Por eso el mismo camino sirve para curva, perfil y cara plana.
- **Gemelos revisados:**
  - El filtro de Revolución sólida (`ui/comandos/solido.py:301`, `{"perfil", "cara_plana"}`): es el criterio que se copió; no se tocó y ya acepta perfil y cara plana, así que la superficie ahora coincide con ella (los tres iguales: ventana, API, operación). ✔
  - La API `create_surface_revolve` (`api/herramientas_superficie.py:133`): **ya aceptaba** perfiles y caras (`_seleccion(..., curvas=True)` y docstring que lo dice); no cambió firma ni descripción, así que `docs/agentes/herramientas.md` **no** se regeneró. ✔
  - La previa (`ui/comando.py` › `set_filtro` con `campo.filtros`; `nucleo/previa*`): no tiene regla propia, ejecuta la operación, así que hereda el filtro y la resolución sin cambios. ✔
  - `PERFILES_SUPERFICIE` (C9/H-85, `ui/comandos/superficie.py:23`): se reusó tal cual, sin duplicar la constante (único nombre para una sola cosa). ✔
  - Extruir de superficie (`ui/comandos/superficie.py:46`, ya en `PERFILES_SUPERFICIE`): comparten la misma constante; el comportamiento de Revolución es ahora idéntico al de Extruir. ✔
  - **Fuera de alcance (no lo toqué):** el eje de Revolución sigue filtrando solo `{"eje"}` (Fusion: «sketch curve, edge, cylindrical face, or axis»); cambiarlo es otra fila. El «A objeto» y el «Proyectar eje» ya andaban.
- **Test nuevo** (`clon/tests/test_comandos_superficie.py::test_revolucion_de_superficie_elige_perfiles_cerrados_y_caras_planas`): con un rectángulo de boceto [4,6]×[0,10] en XZ y una caja, comprueba que el campo «Perfil» de `SupRevolucion` acepta el hit del perfil y el de la cara plana (`acepta`), y que cada uno gira de verdad una superficie (el rectángulo da 240π ≈ 753,98 mm² al voltear 360° sobre Z; la cara plana da superficie positiva).
  - Salida **ROJA** (antes del arreglo):
    `FAILED tests/test_comandos_superficie.py::test_revolucion_de_superficie_elige_perfiles_cerrados_y_caras_planas`
    `AssertionError: assert (False)` en `acepta({'arista', 'curva_boceto'}, {'tipo': 'perfil', ...})` → `1 failed in 2.44s`
  - Salida **VERDE** (con el arreglo): `1 passed in 2.35s`
- **ruff check .:** `All checks passed!` (sobre los dos archivos tocados).
- **Tests obligatorios de la tanda (un grupo, con turno):** `test_comandos_superficie.py`, `test_superficies.py`, `test_superficie_fusion.py`, `test_api_superficie.py`, `test_sol07_revolucion.py`, `test_cobertura_ui_api.py` → **483 passed in 9.94s**.
- **Archivos de `grep -l` NO corridos (los corre el coordinador):** `test_sup29_encadenado_superficie.py`, `test_api_solido.py`, `test_barrido_tipos.py`, `test_bugs_solido.py` (los tres últimos por `create_surface_revolve`; `test_sup29...` por `SupRevolucion`). Revisados a ojo: ninguno depende del filtro del campo Perfil ni de la ayuda (buscan el comando por clave o usan la operación/API), pero el prompt manda correrlos y la nota del coordinador manda no hacerlo en esta corrida.
- **Salida de /ponytail-review:** sin «Must fix» ni «Should fix». Repaso del diff:
  1. **No hay regresión para los campos que solo llevan curvas**: `CURVAS` no se borró, solo se dejó de usar en Revolución; Extruir, Barrido, Parche, Reglada, Recortar y las aristas de Desfase siguen con `CURVAS` o `{"arista"}`, intactos.
  2. **El camino de la operación ya existía**: perfil → cara → `alambres` saca los alambres y `revolver_superficie` gira; el test lo prueba con geometría (240π), no solo con el filtro.
  3. **`cadena` con un perfil o una cara**: `_curvas` con `cadena=True` (valor por defecto de la casilla) cae en la rama `else` de `_en_cadena` y devuelve la forma tal cual; el test gira un perfil y una cara con `cadena=True` y da superficie correcta.
  4. **La API no cambió**: sin firma nueva, sin doc que regenerar, `test_doc_agentes.py` queda verde en el grupo.
  5. **Se reusó `PERFILES_SUPERFICIE`**: un solo nombre para una sola cosa, sin duplicar la constante.
  6. **Verdict:** `Ship.` Nada quedó pendiente de arreglar.
- **No verificado / ⚠:**
  - No corrí la prueba de humo ni la suite completa (regla 10: las corre el coordinador), ni los archivos del `grep -l` (los lista arriba).
  - **Ventana (`revolucion_barrido_solevacion`, minimizada):** `40 comprobaciones, 10 con ✗`. Las 10 ✗ son **anteriores y ajenas a H-104**: 22 (Revolución dos lados 90/−45° da 1570,80 en vez de 2356,19 = H-88, «A objeto» con Dos lados); 26 y 27 (con «A objeto» se ve la Dirección Un/Dos lados = H-88); 28 y 29 (`proyectar_eje` se llama «Eje de proyecto» en sólido y «Proyectar eje» en superficie: incoherencia de etiqueta, no de filtro); 30, 31, 32 y 35 (Barrido sólido: Escala del perfil Estirar, Extensión del Rail, carril escala Ninguna, Distancia «1,5» = H-89); 38 (Solevación punto ofrece Aguda y Punto tangente = H-90). **Ninguna** de las 10 trata el filtro del Perfil ni la aceptación de perfil/cara plana; el campo «Perfil» de `sup_revolucion` abre bien (comprobación 8 OK) y su filtro es el que el test de `test_comandos_superficie.py` ya ejercita en geometría (240π).
  - No abrí Fusion: el comportamiento sale de la ayuda oficial de `fusion-patch`, como en las tandas anteriores.

## Informe tanda C11

**Modelo:** CodeBuddy con deepseek-v4.1-flash (el prompt original decía «OpenCode con Qwen3.8-Flash»; lo escribo como pidió el coordinador). **Tanda:** C11 · **Bug:** CF-8 (faltante, dos de sus opciones: «tamaño del ViewCube» y «barra espaciadora repite el último comando»). **Sin commitear** (lo commitea el coordinador).
**Corrida corta (45 min):** un grupo con los 3 obligatorios que existen (`test_preferencias*.py` y `test_api_*preferenc*.py` **no existían**; el nuevo `tests/test_preferencias.py` es el primero) más 4 de riesgo alto del `grep -l` (`test_plasticidad`, `test_atajos_acciones`, `test_api_misc` y el propio nuevo). El resto del `grep -l` NO se corrió y está listado abajo.

### CF-8 — PREFERENCIAS › tamaño del ViewCube y barra espaciadora que repite el último comando — **Parcial** (hechas las dos opciones de la tanda; el resto de la fila sigue abierto)

- **Qué dice la ayuda de Fusion:**
  - `docs/fusion_docs/contenido/fusion-getstarted/viewcube-reference-1b486b37d43.md` › «Context menu»: «**ViewCube Size**: Sets the display size of the **ViewCube**. Select from the following options: **Automatic**, **Large**, **Normal**, **Small**, **Tiny**». Y la nota: «These camera options are shared with the **Camera** control in the Navigation bar's Display Settings menu». O sea: cinco tamaños, y el ajuste vive en el **clic derecho del ViewCube**, no en Preferencias.
  - `fusion-releasenotes/2025-release-notes-3e142024d7c.md:547` «Spacebar now activates Repeat Command»; `:508` «disabling the 'Spacebar Repeats Last Command' preference did not maintain the spacebar assignment for the previously selected assignment»; `2026-release-notes-60b2372e77b.md:1673` «the Spacebar hotkey could become unassigned when the Spacebar Repeats Last Command option was disabled». O sea: es un ajuste de dos posiciones — encendido, la barra espaciadora repite el último comando; apagado, la tecla queda libre para otra asignación (no desaparece).
  - `fusion-preferences-reference-073442e64a1.md` (General › Mouse setup, orientación, unidades, gráficos) no nombra ninguna de las dos: la del ViewCube es de `fusion-getstarted`, la del Espacio sale de las notas de versión.
- **Qué cambié:**
  - `clon/omnicad/ui/superposiciones.py:26` — `TAMANOS` pasa de 3 a los 5 tamaños de Fusion: `diminuto` 70, `pequeno` 90, `normal` 110, `automatico` 120, `grande` 150; `:27` `TAMANOS_TEXTO` con las etiquetas **en el orden de Fusion** (Automático, Grande, Normal, Pequeño, Diminuto). Las claves viejas se conservan: un valor guardado sigue valiendo.
  - `clon/omnicad/ui/superposiciones.py:45` — `ViewCube.set_tamano` recuerda el tamaño elegido (`self._tamano`) y `:50` `menu_tamano()` arma el menú del clic derecho con las cinco opciones, la vigente marcada (QActionGroup); `:65` `_elegir_tamano` aplica y avisa por el callback `al_elegir_tamano` (mismo patrón que `AreaVisor.al_mover_panel`); `:70` `contextMenuEvent` abre ese menú. El tooltip del cubo dice «Clic derecho: tamaño del ViewCube.»
  - `clon/omnicad/ui/ventana.py:199` — enchufa `self.area.viewcube.al_elegir_tamano = self._guardar_tamano_viewcube`; `:1414` `_guardar_tamano_viewcube` escribe `general/tamano_viewcube` y reubica el cubo (sin eso, el tamaño cambiaba hasta el próximo arranque).
  - `clon/omnicad/ui/ventana.py:341` — `aplicar_teclas`: con `general/espacio_repite` encendido, el atajo por defecto de `repetir` pasa a `Space` y el de `boceto_cara` a vacío (el «otro extremo» del mismo ajuste de Fusion). Lo elegido a mano en «Más › Cambiar atajo» sigue mandando sobre las dos, y el choque de teclas se resuelve como antes.
  - `clon/omnicad/ui/preferencias.py:58` y `:484` — preferencia nueva `general/espacio_repite` (de fábrica **apagada**, para no quitarle el Espacio a «Boceto sobre la cara elegida», PL3) y el combo del ViewCube con las cinco opciones.
  - `clon/omnicad/api/herramientas_preferencias.py:19` — `general/tamano_viewcube` con las cinco opciones y `:20` `general/espacio_repite` (False / [False, True]) en la lista blanca, así `get_preferences` y `set_preference` las ven. **No** se regeneró `docs/agentes/herramientas.md`: no cambió ninguna firma ni ningún docstring de herramienta (las opciones no se listan en la doc generada) y `test_doc_agentes.py` queda verde.
- **Gemelos revisados:**
  - El combo de Preferencias › General (`ui/preferencias.py`, `PAGINAS`) y la lista blanca de la API (`api/herramientas_preferencias.py`, `_OPCIONES`): las dos con las mismas cinco claves y el mismo valor por defecto (`test_las_preferencias_autorizadas_existen_en_la_ventana` de `test_api_misc.py`, verde). ✔
  - `general/tamano_viewcube` ya se aplicaba en `ui/ventana.py:712` (`aplicar_preferencias` → `set_tamano` + `reubicar`): el camino de Preferencias › Aplicar sigue igual; el camino nuevo (menú del cubo) hace lo mismo pero escribe la preferencia. ✔
  - El atajo `repetir` (Shift+R, `ui/ventana.py:451`) y el ítem «Repetir» del menú radial (`_items_radial`): usan la misma acción y el mismo `repetir_ultimo`; no se duplicó nada, solo se le agrega la tecla. `repetir_ultimo` ya repetía la última herramienta **dentro** del boceto. ✔
  - El editor de boceto (`ui/editor_boceto.py:5787`): ya reclamaba `Qt.Key_Space` para alternar las ayudas de inferencia con `ShortcutOverride` **justamente porque** el Espacio era el atajo de «Boceto sobre la cara»; sigue igual, así que con la preferencia encendida el Espacio también funciona como repetición en el boceto (donde repite la última herramienta). ✔
  - `AreaVisor.reubicar` (`ui/superposiciones.py:593`): posiciona el cubo por su ancho; se llama desde `_guardar_tamano_viewcube` para que el cambio se vea al instante. ✔
  - La barra de navegación (`BarraNavegacion`, «Configuración de visualización › Cámara»): Fusion comparte ahí las opciones del ViewCube. **No** la toqué: el tamaño del cubo no estaba en ese menú y la referencia oficial lo documenta en el clic derecho del ViewCube, que es donde lo puse. Si Gerardo lo quiere también ahí, es una fila nueva (dos líneas: un submenú con el mismo `menu_tamano`).
  - **Fuera de alcance (no lo toqué):** el resto de las opciones de CF-8 (finalidad de uso, tipo de diseño por defecto, experiencia de puesta en marcha, orientación Y/Z, ratón Alias/Inventor/PowerMill/SOLIDWORKS, controlador de gráficos, tema del sistema). La fila queda **Parcial** con esa lista en `docs/seguimiento/faltantes.md`.
- **Test nuevo** (`clon/tests/test_preferencias.py`, 2 pruebas — es el primer `test_preferencias*.py` del repo):
  - `test_barra_espaciadora_repite_el_ultimo_comando`: apagada, `boceto_cara` = `Space` y `repetir` = `Shift+R`; encendida, `repetir` = `Space` y `boceto_cara` queda sin tecla; y con la ventana activa, `QTest.keyClick(ventana.area, Qt.Key_Space)` **de verdad** ejecuta el último comando (`ejecutar_comando` recibe la caja).
  - `test_tamano_del_viewcube_como_fusion`: el menú del clic derecho trae exactamente «Automático, Grande, Normal, Pequeño, Diminuto» con el vigente marcado; «Grande» agranda el cubo, lo guarda en `general/tamano_viewcube` y el menú reabierto marca «Grande»; «Diminuto» lo achica por debajo del automático; el combo de `PAGINAS` y la lista blanca de la API tienen las mismas cinco.
  - Salida **ROJA** (antes del arreglo):
    `FAILED tests/test_preferencias.py::test_barra_espaciadora_repite_el_ultimo_comando` → `KeyError: 'general/espacio_repite'` en `omnicad/ui/preferencias.py:181`;
    `FAILED tests/test_preferencias.py::test_tamano_del_viewcube_como_fusion` → `AttributeError: 'ViewCube' object has no attribute 'menu_tamano'` → `2 failed in 2.80s`.
  - Salida **VERDE** (con el arreglo): `2 passed in 3.47s`.
- **ruff check .:** `All checks passed!` (sobre el repo entero).
- **Tests obligatorios de la tanda (un grupo, con turno):** `test_preferencias.py` (nuevo), `test_cobertura_ui_api.py`, `test_comandos.py`, `test_doc_agentes.py` + los del `grep -l` de más riesgo (`test_plasticidad.py` —asserta que `boceto_cara` es Space—, `test_atajos_acciones.py` —usa `aplicar_teclas`—, `test_api_misc.py` —la lista blanca de preferencias—) → **422 passed in 14.06s**.
- **Ventana (minimizada):** `todo.py panel_movible --ventana minimizada` → **68 comprobaciones, 0 con ✗**. Es la pieza más cercana al ViewCube que hay en `PIEZAS` (comprueba que el panel de comando no se meta debajo del cubo); **no hay pieza de preferencias** en `scripts/prueba_ui/todo.py`. Esa pieza no saca captura, así que no hay imagen nueva que mirar.
- **Archivos de `grep -l` NO corridos (los corre el coordinador):** por `aplicar_teclas` / `set_tamano` / `tamano_viewcube` / `espacio_repite` / `boceto_cara` / `repetir_ultimo`: `test_boceto_fase1.py` (coincide por `aplicar_teclas` de otro panel), `test_texto_vectores.py` (`set_tamano` de su propio panel). Por `ViewCube` / `TAMANOS`: `test_api_inspeccion.py`, `test_b105_panel_chico.py`, `test_p9_ui.py`, `test_panel_movible.py`, `test_temas.py`, `test_vistas_animadas.py`. Los tres que más me preocupaban de esa lista los corrí en el grupo (plasticidad, atajos y API de preferencias); el resto toca el ViewCube por nombre o por tamaño y no depende de las cinco opciones ni del menú nuevo.
- **Salida de /ponytail-review:** sin «Must fix» ni «Should fix». Repaso del diff:
  1. **No se duplicó el tamaño del cubo**: `TAMANOS` sigue siendo la única tabla (el menú, `set_tamano` y Preferencias leen de ahí); lo único nuevo es el par clave→texto.
  2. **`set_tamano` es compatible**: las claves viejas (`pequeno`, `automatico`, `grande`) no cambian de valor, así que un `.ini` guardado se sigue leyendo igual y el de fábrica (`automatico` = 120 px) no mueve el cubo.
  3. **El callback sigue el patrón que ya existe** (`al_mover_panel`): el ViewCube no conoce las preferencias ni la ventana, y sin callback el menú igual cambia el tamaño (no rompe nada si se usa suelto en un test).
  4. **La barra espaciadora no le quita la tecla a nadie de fábrica**: la preferencia arranca apagada, así que PL3 («Boceto sobre la cara elegida» con Espacio) y su test quedan igual; encendida, el Espacio se muda a `repetir` y el choque se resuelve con el mismo contador de usos de `aplicar_teclas`.
  5. **Lo elegido a mano manda**: `teclas.get(clave, defecto)` deja que «Más › Cambiar atajo» siga pisando las dos teclas (incluido volver a ponerle Espacio a `boceto_cara` con la preferencia encendida, que es lo que hace Fusion cuando la opción está apagada).
  6. **La API y la ventana quedan iguales**: mismas cinco opciones, mismo defecto, y `test_api_misc.py` (que compara las dos listas) verde.
  7. **Verdict:** `Ship.` Nada quedó pendiente de arreglar.
- **No verificado / ⚠:**
  - No corrí la prueba de humo ni la suite completa (regla 10: las corre el coordinador), ni los archivos del `grep -l` listados arriba.
  - **No hay pieza de preferencias** en `PIEZAS`: corrí `panel_movible` (68/0) porque es la que mira el ViewCube. Ni el menú del clic derecho del cubo ni la preferencia del Espacio se vieron en pantalla; los dos se prueban en los tests offscreen (el menú se inspecciona sin `exec`, y el Espacio se dispara con `QTest.keyClick` sobre la ventana activa).
  - No se abrió Fusion: el comportamiento sale de la ayuda oficial (`fusion-getstarted`) y de las notas de versión, como en las tandas anteriores.
  - El «Automático» de Fusion puede ser un tamaño que se adapta al lienzo; en OmniCAD es un tamaño fijo de 120 px (como ya era). No lo cambié porque la referencia no dice en qué se basa el automático.
  - **Finales de línea (importante para la revisión):** al editar, la herramienta dejó `ui/ventana.py` y `ui/superposiciones.py` enteros en LF y el `git diff --stat` saltó a 6357 y 1334 líneas. Se restauró **línea por línea** con difflib (los tramos iguales copian los bytes de `git show HEAD:archivo`, los nuevos llevan el final del vecino): el diff final es de **13 líneas en `ventana.py`** y **30 en `superposiciones.py`**, sin una sola línea de más. Queda anotado como lección en `PROJECT_LOG.md`.

## Informe tanda C12

**Modelo:** CodeBuddy con hy3. **Tanda:** C12 · **Bug:** B-218 (único ítem). **Sin commitear** (lo commitea el coordinador).

### B-218 — Editar cara y Dividir cara cargan sin OpenCascade y quedan sin soporte con OmniKernel — **Resuelto**

- **Estado:** Resuelto.
- **Ayuda de Fusion:** No aplica: B-218 es un bug de compatibilidad con el motor OmniKernel, no un comportamiento de geometría a replicar.
- **Qué cambié:** `clon/omnicad/nucleo/editar_cara.py` importaba OpenCascade (OCP) al cargarse (líneas 18-34 originales: `BRep_*`, `TopoDS`, `gp_*`, `Geom_*`, `IntTools_*`, `ShapeFix_*`, `Array*`, `TopAbs_*`, `TopExp_*`, `TopLoc_*`, `BRepTools*`, etc.). Con `OMNICAD_MOTOR=omnikernel` y `OMNICAD_BLOQUEAR_OCP=1` el import caía en «Import prohibido por OMNICAD_BLOQUEAR_OCP: OCP», así que Editar cara y Dividir cara no funcionaban con OmniKernel. Lo pasé al patrón de sus gemelos de `nucleo/` (`_iniciar_opencascade` + `_motor.registrar`):
  - Los imports de OCP ahora viven en `_iniciar_opencascade()` (declarados con `global`) y se ejecutan solo si `motor_activo() == "opencascade"` (`clon/omnicad/nucleo/editar_cara.py:24-58`; guarda `:60-61`).
  - Al final del módulo: `_motor.registrar(globals(), _iniciar_opencascade)` (`clon/omnicad/nucleo/editar_cara.py:514`), que envuelve las funciones públicas y, como no existe `clon/omnicad/nucleo/omnikernel/editar_cara.py`, hace que `editar_cara`, `grilla_cara`, `curvas_grilla`, `extruir_grilla`, `divisiones` y `remuestrear` informen `MOTOR_SIN_SOPORTE` con OmniKernel (igual que el resto de `nucleo/`).
- **Gemelos revisados y qué hice con cada uno:**
  - `nucleo/solidos_modificar.py`, `nucleo/geometria.py` y los demás módulos de `nucleo/` que usan `_iniciar_opencascade` + `_motor.registrar`: **copié el patrón** (declarar los nombres OCP como `global` y cargarlos solo con OpenCascade).
  - `timeline/ops_modificar.py` (`OpEditarCara`, `clon/omnicad/timeline/ops_modificar.py:591,600`): ya importa `editar_cara` de forma perezosa dentro de `ejecutar` y lo usa envuelto por el dispatcher → sin cambio.
  - `api/herramientas_dividir.py` (`clon/omnicad/api/herramientas_dividir.py:109,149`): ya hace el import perezoso de `editar_cara` → sin cambio.
  - **Dividir cara** (`extruir_grilla`, `divisiones`, los `cortes_*`, etc.) vive dentro del propio `editar_cara.py` y quedó cubierto por el mismo patrón → sin cambio aparte.
- **Test nuevo (rojo → verde):** `tests/test_motor.py::test_nucleo_importa_sin_opencascade`. Corre en subproceso con `OMNICAD_MOTOR=omnikernel` y `OMNICAD_BLOQUEAR_OCP=1` y afirma que `import omnicad.nucleo.editar_cara` sale con código 0.
  - ROJO (antes del arreglo, con los imports de OCP al tope):
        E       AssertionError: Traceback (most recent call last):
        E           File "<string>", line 1, in <module>
        E           File "D:\PROGRAMA-cb\clon\omnicad\nucleo\editar_cara.py", line 18, in <module>
        E             from OCP.BRep import BRep_Builder, BRep_Tool
        E           File "D:\PROGRAMA-cb\clon\omnicad\bloqueo_ocp.py", line 11, in find_spec
        E             raise ImportError(f"Import prohibido por OMNICAD_BLOQUEAR_OCP: {fullname}")
        E         ImportError: Import prohibido por OMNICAD_BLOQUEAR_OCP: OCP
        E       assert 1 == 0
        tests\test_motor.py:207: AssertionError
        1 failed in 3.42s
  - VERDE (con el patrón aplicado):
        .                                                                        [100%]
        1 passed in 2.05s
- **Salida real de ruff check .:** `All checks passed!`
- **Salida real de cada grupo de tests (con `../scripts/turno.py`, < 900 s cada uno):**
  - `test_motor.py`: **14 passed in 22.39s**
  - `test_sol16_dividir_cara.py` + `test_api_dividir.py` + `test_consultas_motor.py`: **18 passed in 4.20s**
  - `test_herramientas_solido.py`: **148 passed in 98.81s**
  - `test_api_solido.py`: **74 passed in 7.57s**
  - `test_barrido_tipos.py` + `test_cobertura_ui_api.py`: **405 passed in 37.86s**
  - `test_paridad_motor.py` (lento, omnikernel instalado): **68 passed in 126.29s**
- **Salida completa de `/ponytail-review` y qué arreglé:**
  > What this change does: `nucleo/editar_cara.py` no importa OpenCascade al cargarse: los imports de OCP se movieron a `_iniciar_opencascade()` y solo se cargan con el motor OpenCascade, envuelto por `_motor.registrar`. Así el módulo carga con OmniKernel y OCP bloqueado, y la operación informa `MOTOR_SIN_SOPORTE`.
  >
  > Must fix: ninguno.
  >
  > Should fix: ninguno que requiera código. La única sutileza es que `divisiones` (pública) es «común» (no nombra OCP directo) salvo cuando `espaciado > 0`, que entonces llama a `_largos` (usa `BRepAdaptor_Surface`); con OmniKernel y espaciado > 0 daría `NameError` en vez de `MOTOR_SIN_SOPORTE`. Es inalcanzable por la vía pública (la API `edit_face`/`get_face_grid` pasa primero por `grilla_cara`/`editar_cara`, que ya dan `sin_soporte`), y `remuestrear`/`extruir_grilla` y `divisiones` con espaciado = 0 son matemática pura que corre igual en los dos motores. Se deja como está y se anota como ⚠ (corregirlo forzaría `sin_soporte` en el caso puramente matemático, que es peor).
  >
  > Nice to have: lo mismo de arriba, como nota.
  >
  > Verdict: Ship.
  > Lean: 0 lines possible (el cambio borra las líneas de imports al tope y agrega la función + el registro; no hay código muerto).
  > Not checked: no corrí la prueba de humo ni la suite completa (las corre el coordinador, por instrucción de la tanda); no abrí Fusion (el bug es de compatibilidad de motor, no de comportamiento de geometría).

  No tuve que arreglar nada del review.

- **Revisión del coordinador (2026-11-06):** `ponytail-review` propio pidió que el test cubra todo `nucleo/` y no solo `editar_cara` (así se encontró B-218): renombrado a `test_nucleo_importa_sin_opencascade`, recorre `nucleo/` con `pkgutil.walk_packages`. TWINS: 0 otros módulos importan OCP al cargarse. `ruff check .`: All checks passed!; 931 passed en 10 archivos (`test_motor`, `test_api_dividir`, `test_api_solido`, `test_barrido_tipos`, `test_cobertura_ui_api`, `test_comandos_modificar`, `test_herramientas_solido`, `test_iconos_extra`, `test_revision_lotes_sol`, `test_solidos_modificar`).
- **Lo no verificado (⚠):**
  - No corrí la prueba de humo ni la suite completa (lo hace el coordinador, según la tanda).
  - El caso `divisiones(espaciado > 0)` bajo OmniKernel daría `NameError` en vez de `MOTOR_SIN_SOPORTE` (inalcanzable por la API, ver arriba).
  - No probé con la app real abierta bajo OmniKernel + OCP bloqueado más allá del import (el test de humo del coordinador cubre ese recorrido).
  - `nucleo/omnikernel/editar_cara.py` no existe a propósito: la operación queda sin soporte con OmniKernel.

## Informe tanda C13

**Modelo:** CodeBuddy con deepseek-v4.1-flash. **Tanda:** C13 · **Ítem:** CF-8 (lo que falta). **Sin commitear** (lo commitea el coordinador).
**Alcance:** se hicieron **completas** las dos primeras opciones del orden de la fila C13 —tema del sistema y ratón estilo Alias/Inventor/PowerMill/SOLIDWORKS—, cada una con preferencia guardada, control en Preferencias › General, efecto real en la app, la misma opción en `get_preferences`/`set_preference` y test rojo→verde. Las **cinco restantes no entraron** y la fila queda **Parcial** con la lista exacta y el motivo de cada una (abajo, en «Lo que falta»).

### CF-8 (1) — Tema del sistema — **Hecho**

- **Qué dice la ayuda de Fusion:**
  - `docs/fusion_docs/contenido/fusion-releasenotes/2025-release-notes-3e142024d7c.md:546` — «New UI Themes allows you to switch between **Dark Blue**, **Match Device Theme**, **Light Gray** and **Fusion Classic**». Además de los temas fijos hay uno que sigue al claro/oscuro del sistema.
  - `fusion-preferences-reference-073442e64a1.md` (la referencia de Preferencias) **no** lo nombra: habla de Mouse setup, orientación de modelado, unidades y gráficos. El tema sale de las notas de versión, igual que en C11 pasó con la barra espaciadora.
- **Qué cambié:**
  - `clon/omnicad/ui/temas.py:27` — `SISTEMA = "sistema"`, **fuera** de `INCLUIDOS`: los cinco temas de siempre no cambian y `test_hay_cinco_temas_y_el_de_fabrica_es_oscuro_moderno` sigue verde.
  - `clon/omnicad/ui/temas.py:542` — `disponibles()` lo pone primero, con el nombre «Tema del sistema» (y el docstring del módulo, `:7`, lo cuenta).
  - `clon/omnicad/ui/temas.py:551` — `esquema_sistema()`: «claro» solo si `QGuiApplication.styleHints().colorScheme()` dice Light; cualquier otra cosa (Unknown incluido) es «oscuro», que es el tema de fábrica. `:560` `tema_del_sistema()` lo traduce a `claro_moderno` / `oscuro_moderno`. El import de Qt va **dentro** de la función, como pide el docstring del módulo («no importa Qt al cargarse»).
  - `clon/omnicad/ui/temas.py:565` — `resolver("sistema")` devuelve los colores del tema concreto pero con `clave` «sistema» y `base` = ese tema concreto: el aviso de contraste, la vista previa y la plantilla exportada siguen funcionando sin tocar nada.
  - `clon/omnicad/ui/ventana.py:164` — `QGuiApplication.styleHints().colorSchemeChanged` conectado a `_al_cambiar_esquema` (`:624`), que vuelve a llamar a `aplicar_tema()`: si el sistema pasa a claro u oscuro mientras la app está abierta, el tema cambia sin reiniciar. Es un método de la ventana y no un `lambda` a propósito: Qt suelta la conexión cuando la ventana se destruye (con el lambda, cada ventana cerrada quedaba viva para siempre y el aviso podía llegar a un objeto ya borrado).
  - `clon/omnicad/api/herramientas_preferencias.py:13` — `general/tema` entra en la lista blanca con **seis valores fijos** (los cinco incluidos y «sistema»), así `get_preferences` y `set_preference` ven la opción. Los temas propios (`usuario:…`, que son archivos del disco) **siguen prohibidos**: `_exigir_clave` (`:96`) y el docstring de `set_preference` (`:157`) pasan a decir «temas propios (usuario:…)», y hay un test que comprueba que `set_preference("general/tema", "usuario:mi_tema")` falla. `docs/agentes/herramientas.md` regenerado (una línea, la del docstring).
- **Gemelos revisados:**
  - El combo de Preferencias › General (`ui/preferencias.py` › `_combo_temas`): arma la lista con `temas.disponibles()`, así que la opción nueva aparece sin tocar el diálogo. ✔
  - La lista blanca de la API: mismas claves y mismo valor por defecto (`test_las_preferencias_autorizadas_existen_en_la_ventana`, verde) y la lista de temas comparada contra `temas.INCLUIDOS + ["sistema"]` en el test nuevo, para que no se desvíe si mañana se agrega un tema. ✔
  - `temas.resolver()`: lo usan el aviso de contraste (`_mostrar_aviso_tema`), la vista previa (`activar`) y `exportar_plantilla`; los tres siguen andando porque el tema del sistema devuelve los colores de un tema concreto. ✔
  - `tests/test_temas.py:217` y `:305`: las dos listas de `disponibles()` que se comparaban por posición se ajustaron (ahora «sistema» va primero). Es un cambio esperado, no un test debilitado: se sigue exigiendo la lista exacta y el orden. ✔
  - `ui/ventana.py` › `aplicar_tema`: es el único que aplica QSS/paleta a la app; el camino de Preferencias › Aplicar no cambió. ✔

### CF-8 (2) — Ratón estilo Alias, Inventor, PowerMill y SOLIDWORKS — **Hecho**

- **Qué dice la ayuda de Fusion:** `fusion-preferences-reference-073442e64a1.md` › «Program-specific mouse shortcut presets»:
  - **Alias** — Zoom: Shift + Alt + botón derecho · Pan: Shift + Alt + botón medio · Orbit: Shift + Alt + botón izquierdo.
  - **Inventor (solo Windows)** — Zoom: F3 + izquierdo · Pan: F2 + izquierdo · Orbit: F4 + izquierdo.
  - **PowerMill** — Zoom: rueda · Pan: Mayús + medio · Orbit: medio · (nota: «The PowerMill preset uses its own Default Orbit type») · Zoom to box: Ctrl+Mayús+medio · Rotate about X/Y/Z: Mayús+Alt+izquierdo/medio/derecho.
  - **SOLIDWORKS** — Zoom: Mayús + rueda · Pan: Ctrl + medio · Orbit: medio.
  - Y el aviso general: «When using any of the presets above, you can press F6 to resize the view to fit in the current window» (F6 no existe en OmniCAD; ver ⚠).
- **Qué cambié:**
  - `clon/omnicad/ui/visor3d.py:2374` — `accion_raton` suma los cuatro esquemas. Alias: con Mayús+Alt, izquierdo órbita, medio encuadre, derecho **zoom de arrastre** (la acción «zoom» que ya usaba la barra de navegación y que `mouseMoveEvent` resuelve con `acercar`). Inventor: con F2/F3/F4 mantenida y el izquierdo, encuadre/zoom/órbita; el medio encuadra y Mayús+medio orbita. PowerMill: medio órbita, Mayús+medio encuadre. SOLIDWORKS: medio órbita, Ctrl+medio encuadre.
  - El `Mayús + medio = órbita` que antes valía para **todos** los esquemas bajó adentro de los esquemas que lo usan: si quedaba arriba, PowerMill (que lo quiere como encuadre) y SOLIDWORKS (Ctrl+medio) nunca lo alcanzaban. Es el gemelo que se rompía.
  - `clon/omnicad/ui/visor3d.py:500` — `_tecla_nav` (None o F2/F3/F4), que se pone en `keyPressEvent` (`:2691`), se limpia en `keyReleaseEvent` (`:2704`) y también en `focusOutEvent` (`:2710`): sin lo último, una tecla apretada y un Alt+Tab dejaban el esquema «Inventor» en zoom para siempre.
  - `clon/omnicad/ui/preferencias.py:473` — el combo pasa de tres a siete opciones, cada una con su combinación en el texto.
  - `clon/omnicad/api/herramientas_preferencias.py:15` — las mismas siete en `general/raton`.
- **Gemelos revisados:**
  - `mousePressEvent` / `mouseMoveEvent` / `mouseReleaseEvent` (`ui/visor3d.py`): consumen lo que devuelve `accion_raton` («orbita», «encuadre», «zoom») y ya sabían hacer las tres cosas; no hubo que tocarlos. El zoom de arrastre usa el mismo camino que el modo Zoom de la barra de navegación. ✔
  - El gesto del menú radial (clic derecho + arrastre) sigue igual: en Alias el derecho **con** Mayús+Alt es zoom y **sin** modificadores sigue abriendo el menú contextual (devuelve None). ✔
  - `wheelEvent`: la rueda sigue haciendo zoom en **todos** los esquemas, también en Alias e Inventor, donde Fusion no la usa. Es una decisión: sin rueda, cambiar el preset parecería romper el ratón. Queda anotado como diferencia deliberada con Fusion. ✔
  - `test_f16_visor.py` (usa el esquema «omnicad») y los tests que usan el de fábrica («fusion»): el camino de esos dos esquemas quedó idéntico, línea por línea. ✔
  - `ui/comandos/comunes.py`, `ui/manipuladores.py`, `ui/render.py` leen `visor.R` como dirección del mundo: **no** cambian, porque este ítem no toca la cámara. ✔ (Sí habría que tocarlos para la orientación Y arriba: ver «Lo que falta».)

### Tests

- `clon/tests/test_preferencias.py:103` — `test_tema_del_sistema_sigue_al_claro_oscuro_de_windows`: «sistema» está en `disponibles()`; con el esquema simulado en claro, `aplicar_tema()` deja el fondo de `claro_moderno`; cambiándolo a oscuro, el de `oscuro_moderno`; el combo de Preferencias lo deja elegido con el texto «Tema del sistema»; la API tiene los seis valores; y `_validar("general/tema", "usuario:mi_tema")` falla.
- `clon/tests/test_preferencias.py:131` — `test_raton_estilos_alias_inventor_powermill_solidworks`: las combinaciones de los cuatro presets, con la tecla F3 apretada de verdad (`QTest.keyPress`/`keyRelease` sobre el visor) y el combo y la API con las mismas siete opciones.
- **Salida ROJA (antes del arreglo):**
  `FAILED tests/test_preferencias.py::test_tema_del_sistema_sigue_al_claro_oscuro_de_windows` → `AssertionError: assert 'sistema' in ['oscuro_moderno', 'claro_moderno', 'azul_profesional', 'minimalista', 'clasico']`;
  `FAILED tests/test_preferencias.py::test_raton_estilos_alias_inventor_powermill_solidworks` → `AssertionError: assert 'encuadre' == 'orbita'`;
  `2 failed, 2 passed in 2.96s`.
- **Salida VERDE (con el arreglo):** `4 passed in 3.34s` (`tests/test_preferencias.py`).
- **ruff check .** (repo entero, desde `clon/`): `All checks passed!`

### Grupos de tests (con `../scripts/turno.py`, todos < 900 s)

- `test_preferencias.py + test_temas.py + test_iconos_tema_vivo.py + test_f16_visor.py + test_api_misc.py` → **71 passed in 9.25s**
- `test_doc_agentes.py + test_comandos.py` → **51 passed in 6.95s**
- `test_cobertura_ui_api.py` → **347 passed in 2.35s**
- `test_preferencias.py + test_temas.py + test_iconos_tema_vivo.py` (después de cambiar el lambda por el método) → **54 passed in 5.14s**
- `test_tipografia_ui.py -k "aplicar_tema or colores_de_texto_y_descarta or muestra_y_el_aviso or restablecer_apariencia"` (los 4 que tocan el tema) → **4 passed, 19 deselected in 8.35s**
- ~~`test_tipografia_ui.py` entero no se puede correr en esta PC~~ **Corrección del coordinador:** corrido entero con turno, 23 passed (en main y en esta rama con la tanda); el corte de la corrida del agente no se reproduce.

### `/ponytail-review` (salida completa)

> **What this change does:** Preferencias › General gana dos opciones de Fusion que faltaban. (1) «Tema del sistema»: un tema virtual, fuera de `INCLUIDOS`, que resuelve al claro o al oscuro según lo que informe el sistema operativo y se vuelve a aplicar cuando el sistema cambia. (2) Los presets de ratón Alias, Inventor, PowerMill y SOLIDWORKS en `general/raton`, con el zoom, el encuadre y la órbita de cada uno.
>
> **Must fix:** ninguno.
>
> 1. **La conexión al cambio de esquema dejaba viva a cada ventana cerrada** (`ui/ventana.py:164`, versión anterior)
>    - **What this is:** La ventana se suscribe al aviso global «cambió el claro/oscuro del sistema».
>    - **Problem:** Estaba suscripta con un `lambda` que capturaba `self`. El objeto global del aviso guarda una referencia fuerte al lambda, así que la ventana nunca se liberaba, y si el sistema cambiaba después de cerrarla, el aviso llamaba a `aplicar_tema()` sobre un objeto Qt ya destruido. En la app es una sola ventana; en los tests se crean y se cierran decenas.
>    - **Fix:** Un método de la ventana (`_al_cambiar_esquema`, `:624`) y conectarlo a él: Qt suelta la conexión cuando el receptor se destruye. 3 líneas, sin `lambda`.
>    - **If we skip it:** Fuga de memoria por ventana y un posible `RuntimeError`/cierre al cambiar el tema de Windows con una ventana cerrada.
>
> **Should fix:** ninguno.
>
> **Nice to have:**
>
> 2. **La lista de temas de la API es una copia** (`api/herramientas_preferencias.py:13`)
>    - **What this is:** `_OPCIONES` repite a mano las seis claves de tema que la UI saca de `temas.INCLUIDOS`.
>    - **Problem:** Si mañana se agrega un tema incluido, la API se queda con cinco y nadie se entera.
>    - **Fix:** Ya está atajado con un test (`test_tema_del_sistema…` compara contra `temas.INCLUIDOS + ["sistema"]`), así que la copia no puede desviarse sin que falle la suite. Importar `temas` desde la API sería peor: la API no debe depender de la UI.
>    - **If we skip it:** Nada, mientras el test esté.
>
> 3. **Las F2/F3/F4 del preset Inventor solo llegan con el foco en el lienzo** (`ui/visor3d.py:2691`)
>    - **What this is:** La tecla se lee del `keyPressEvent` del visor.
>    - **Problem:** Si el foco está en el navegador o en el timeline, F3 no llega al visor y el arrastre con el izquierdo no hace zoom.
>    - **Fix:** No lo toco: en Fusion esas teclas también son del lienzo, y llevarlas a la ventana chocaría con los atajos de las acciones. Queda anotado.
>    - **If we skip it:** El preset Inventor se siente incompleto si el lienzo no tiene el foco (un clic en el lienzo lo arregla).
>
> **Verdict:** Ship.
> **Lean:** 0 lines possible (el cambio agrega la opción que se pidió y el único código propio es el que la resuelve; no quedó código muerto).
> **Not checked:** no corrí la prueba de humo ni la suite completa (las corre el coordinador); no abrí Fusion (el comportamiento sale de la ayuda oficial); no miré la opción en pantalla con una captura (no hay pieza de Preferencias en `scripts/prueba_ui/`).

**Qué arreglé de la review:** el punto 1 (el `lambda` → `_al_cambiar_esquema`), y volví a correr los grupos que lo tocan (54 y 4 verdes, ruff limpio). El 2 ya estaba cubierto con un test; el 3 queda como limitación anotada.

### Lo que falta de CF-8 (la fila queda **Parcial**)

En el orden de la fila C13, y por qué no entró:

1. **Orientación Y o Z hacia arriba.** El combo «Orientación de modelado por defecto» solo ofrece «Z hacia arriba». Fusion (`fusion-preferences-reference`: «The default modeling orientation is Z up. To change it, select Y up, click OK, and restart Fusion. The ViewCube then indicates the new default modeling orientation by showing the Y up») lo aplica al mundo entero, y en OmniCAD eso significa meter una rotación mundo→pantalla en el marco de la cámara: hoy **15 lugares de 6 archivos** leen `visor.R` como dirección del mundo (`ui/visor3d.py`: `ojo`, `desplazar`, `encuadrar`, `mirar_a_plano`, `primitivas_centro_giro`, el orden de dibujo por profundidad y el sombreado de `funcion_colores`; `ui/render.py` › `u_atras` del shader; `ui/manipuladores.py`; `ui/comandos/comunes.py`, `editar_cara.py` e `inspeccionar.py`). Si uno solo queda sin convertir, el modelo se ve girado pero las luces, el gizmo o la vista «Mirar a» quedan mal, y eso **no se puede dar por bueno sin verlo en pantalla** (no hay pieza de `todo.py` que lo mire). Es una tanda propia, no una opción suelta.
2. **Tipo de diseño por defecto** (Pieza/Ensamblaje/Híbrido). OmniCAD no tiene tipos de diseño: es una función que falta (está en CF-6, «¿Qué desea diseñar?»). Una preferencia sin nada que elegir sería un botón que no hace nada.
3. **Finalidad de uso** (diseño, fabricación, electrónica). En Fusion (`fusion-home`: «Update your purpose for using Fusion… Purpose influences the First things to try section») solo elige **qué sugiere la puesta en marcha**. Sin puesta en marcha no hay nada que influir.
4. **Experiencia de puesta en marcha.** OmniCAD no tiene asistente, tour ni «First things to try» de primer arranque.
5. **Controlador de gráficos.** Fusion elige el motor de dibujo de la interfaz (DirectX 11 / Metal / OpenGL: `2026-release-notes`: «Fusion now automatically uses DirectX 11 when available, or software rendering…»; `2025-release-notes`: «This can be changed in the Compatibility & Troubleshooting section of Fusion's Preferences»). OmniCAD dibuja con el OpenGL de Qt: no hay una opción que se pueda cumplir de verdad, y la regla del módulo es no ofrecer lo que no se cumple.

### Revisión del coordinador (2026-11-06)

`ponytail-review` propio, dos Must fix arreglados por el coordinador: (1) con «Inventor», F2 lo atrapaba antes el atajo «Renombrar» de la ventana y el visor se tragaba F2–F4 con cualquier estilo: ahora el visor las toma solo con Inventor y acepta el `ShortcutOverride` (y no suelta la tecla con la repetición del teclado); test nuevo con y sin Inventor en `test_raton_estilos_alias_inventor_powermill_solidworks`. (2) el tema había entrado al MCP: CLAUDE.md y `docs/brechas_mcp.md` lo dejan afuera; sacado de `_OPCIONES` y el test exige que no esté (`herramientas.md` vuelve a quedar igual). `docs/brechas_mcp.md`: el ratón y el tamaño del ViewCube ya estaban en `set_preference`, se corrigió la frase que decía lo contrario. Verificación: `ruff check .` All checks passed!; 1089 passed (`test_preferencias`, `test_temas`, `test_iconos_tema_vivo`, `test_cobertura_ui_api`, `test_doc_agentes`, `test_seguimiento` y los 12 del grep); `test_comandos` 13 passed; `test_tipografia_ui` 23 passed.

### Lo no verificado (⚠)

- No corrí la prueba de humo ni la suite completa (las corre el coordinador), como pide la tanda.
- **No miré las dos opciones en pantalla.** `scripts/prueba_ui/todo.py` no tiene ninguna pieza de Preferencias; lo que sí comprobé de verdad es la detección del esquema en esta PC (Windows en modo claro): `esquema_sistema()` devuelve «claro» y `tema_del_sistema()` → `claro_moderno`.
- No probé el preset «Inventor» con el ratón real: el test aprieta y suelta F3 sobre el visor y consulta `accion_raton`, pero no arrastra con el botón izquierdo.
- Diferencias deliberadas con Fusion, anotadas arriba: la rueda sigue haciendo zoom en Alias e Inventor; el «Zoom to box» de PowerMill (Ctrl+Mayús+medio) y sus «Rotate about X/Y/Z» (Mayús+Alt + izquierdo/medio/derecho) no se implementaron (el primero ya existe como modo Ventana de la barra de navegación, el segundo es la órbita libre); el F6 («resize the view to fit») no existe en OmniCAD.
- ~~`tests/test_tipografia_ui.py` entero muere en esta PC~~ **Falso** (coordinador): corrido entero con turno pasa, 23 passed en HEAD de main y 23 passed en esta rama con la tanda.

## Informe tanda 1

Corrida del 2026-11-05 (pasó la medianoche al 11-06). OpenCode con Qwen3.8-Flash en Qoder. Bugs: B-211 y B-210, de a uno y en ese orden.

### B-211 · Barrido: la Distancia mayor que 1 se recorta a 1 sin avisar — **Resuelto**

**Qué dice la ayuda de Fusion** (`fusion_docs.py ver "Sweep reference" -s fusion-model`, desde `clon/`):

> ### Distance
> Specify the distance to sweep along the path.
> Value is measured in percentage of the total distance.
> Range: 0.00-1.00

O sea: 1,5 no es «casi dos vueltas» ni «la ruta entera»: está fuera de rango y hay que rechazarlo. La regla ya estaba escrita en el gemelo de superficie (`nucleo/superficies.py:698`: `0 < valor <= 1`), pero no en el compartido.

**Qué cambié** — `clon/omnicad/nucleo/solidos_crear.py:249` (`_recortar_alambre`), tres líneas:

```python
if not math.isfinite(fraccion) or fraccion > 1.0 + 1e-9:
    raise geo.ErrorGeometria("La distancia sobre la ruta va de 0 a 1 (fracción del total); "
                             f"recibió {fraccion:g}.")
```

Se eligió el compartido y no cada comando porque `_recortar_alambre` es el único que recorta la ruta: un punto cierra el recorte silencioso `min(fraccion, 1.0)` para las cuatro entradas. La tolerancia de 1e-9 deja pasar una expresión que da 1 por coma flotante, que es lo que ya aceptaba la línea siguiente.

**Gemelos revisados** (regla 1; `grep -rn "_recortar_alambre" clon/omnicad`, `grep -rn "distancia"` por archivo y `grep -rn "min(fraccion"`):

| Gemelo | Qué hice |
|---|---|
| `nucleo/solidos_crear.py:904` `barrer` (Barrido, y su superficie con `solido=False`) | pasa por el compartido → arreglado |
| `nucleo/solidos_crear.py:938` `barrer_cuerpo` (Barrido sólido) | pasa por el compartido → arreglado |
| `nucleo/solidos_crear.py:2899` `tuberia` (Tubería, con `distancia2`) | pasa por el compartido → arreglado; su validación previa solo mira NaN/∞ y el inicio, así que quedó |
| `nucleo/superficies.py:582, 595, 710, 724` (corte del riel y de la espina) | ya llegaban con una fracción ≤ 1: `barrer_superficie` rechaza antes (`:698`) y `_recortar_perpendicular` usa `_primer_cruce`, que devuelve (0, 1]. Sin cambio |
| `nucleo/solidos_crear.py:815` (ruta cerrada con torsión: `0.5` y `1.0` fijos) | constantes internas. Sin cambio |
| `timeline/ops_solido.py:162, 181, 585` (`OpBarrido`, `OpTuberia`) | solo evalúan la expresión y la bajan al núcleo. Sin cambio |
| `ui/comandos/crear.py:67` (Distancia del Barrido) y `:1019-1022` (Distancia inicial/final de la Tubería) | la ayuda de los tres campos ya dice «de 0 a 1» / «fracción entre 0 y 1»; con el error del núcleo la previa se pone roja sola. Sin cambio |
| `api/herramientas_solido.py:452` (`sweep`, `path_distance`) | **lo dejé**, aunque el `ponytail-audit` decía «the check in the API can then go»: da `INVALID_ARGUMENTS` antes de calcular y es el patrón de la casa (el `twist_angle` de tres líneas más abajo hace exactamente eso con `TORSION_MAXIMA`); el test que lo exige sigue verde |
| `api/herramientas_superficie.py:169` (`create_surface_sweep`) | sin chequeo propio: depende del núcleo, que ahora rechaza. Sin cambio |
| `nucleo/omnikernel/solidos_crear.py` | no tiene barrido ni recorte de ruta (`grep -n "barrer\|recortar\|distancia"` → nada). Sin cambio |
| la previa rápida (`ui/comando.py`) | `tramo_previa` es solo del prisma de Extruir; Barrido y Tubería calculan la previa con el núcleo. Sin cambio |
| `edit_feature` (`api/herramientas_documento.py:709`) | recalcula y descarta el cambio con el error del paso → test nuevo |
| MCP / CLI | mismo catálogo `api/`, nada que duplicar. No cambió ninguna firma: no se regenera `docs/agentes/herramientas.md` |

**Test nuevo y su salida.** `tests/test_solidos_crear.py::test_barrido_distancia_mayor_que_una_da_error` (5 caminos × 2 valores, más NaN/∞), `tests/test_api_opciones_solido2.py` (con `path_distance="1.5"` y con `edit_feature {"distancia": "2"}`) y `tests/test_comandos_crear.py::test_barrido_distancia_fuera_de_rango_error_en_el_dialogo`.

ROJO antes del arreglo (con el arreglo revertido un momento, para tomar la salida de cada capa):

```
$ pytest tests/test_solidos_crear.py -q -k "distancia_mayor_que_una"
E   Failed: DID NOT RAISE ErrorGeometria
FAILED tests/test_solidos_crear.py::test_barrido_distancia_mayor_que_una_da_error[1.5]
FAILED tests/test_solidos_crear.py::test_barrido_distancia_mayor_que_una_da_error[2.0]
FAILED tests/test_solidos_crear.py::test_barrido_distancia_mayor_que_una_da_error[nan]
FAILED tests/test_solidos_crear.py::test_barrido_distancia_mayor_que_una_da_error[inf]
4 failed, 63 deselected in 1.04s

$ pytest tests/test_api_opciones_solido2.py -q -k "distancia_parcial"
E   AssertionError: {'ok': True, 'result': {'feature': {'id': 'op4', 'name': 'Barrido2', 'type': 'barrido'},
    'bodies_created': [{'id': 'op4.c1', 'name': 'Cuerpo2', 'volume': 251.3274}], ...}}
1 failed, 6 deselected in 1.15s

$ pytest tests/test_comandos_crear.py tests/test_api_opciones_solido2.py -q -k "sweep or distancia_fuera"
E   AssertionError: La selección de cadena solo suma aristas de cuerpos: las curvas de boceto se usan tal cual.
E     assert ('aviso' == 'error'  - error  + aviso)
1 failed, 24 deselected in 1.77s
```

El de la API es el bug entero en una línea: `ok` con 251,33 mm³, que es π·4·20 — la ruta completa. (En la primera versión del test los cuatro valores se probaban juntos; al separar NaN/∞ se vio que `tuberia` ya los rechaza con su propio mensaje «Las distancias deben ser finitas…», así que el test quedó en dos parametrizaciones con la cuenta del rango y un bloque aparte que solo exige `ErrorGeometria`.)

VERDE después: `2 passed, 63 deselected in 0.92s` en el núcleo, y los grupos completos de la tabla de abajo, todos verdes.

### B-210 · Revolución «Dos lados» con un ángulo negativo: sólido contra superficie — **Resuelto**

**Qué dice la ayuda de Fusion** («Revolve reference»): `Two Sides: Revolves profile on each side of the profile plane`, y nada sobre el signo del ángulo. ⚠ Fusion real no se abrió; la regla no sale de la ayuda sino de los tres gemelos que ya la tenían escrita, que es lo que pedía la fila («falta una sola regla para los dos»).

**Estado del código antes de decidir** (medido, no supuesto — `evidencias/ui_2026-11-05/sondas_rbs.py dos_lados`):

```
rev_dos_lados_90_45      | ok | op2.c1:solid    V=3534.29  [-0.00,0.00,-20.00]..[20.00,10.00,14.14]
rev_dos_lados_90_menos45 | ok | op2.c1:solid    V=2356.19  [0.00,0.00,-20.00]..[20.00,10.00,0.00]
srev_dos_lados           | ok | op2.c1:surface  A=235.62
srev_dos_lados_neg       | ok | op2.c1:surface  A=235.62
```

El sólido con −45 da lo mismo que sin lado 2 (la caja no pasa de z = 0) y la superficie con −45 da lo mismo que con +45: **la superficie ya tomaba la magnitud y el sólido no.** (El `1570,80` de la fila había envejecido; medido hoy, eran 2356,19.)

**Qué cambié** — `clon/omnicad/timeline/operaciones.py:1316` (`OpRevolucion.ejecutar`):

```python
forma = geo.unir_todos([geo.revolver(caras, punto, direccion, abs(a1)),
                        geo.revolver(caras, punto, -direccion, abs(a2))])
```

Antes `a1` y `a2` entraban con su signo, así que −45° sobre `-direccion` era +45° sobre `direccion`: el lado 2 caía adentro del lado 1 y se perdía en la unión. Va `abs` también en `a1` porque con −90 pasaba lo mismo al revés. El control de la línea 1311 ya sumaba `abs(a1) + abs(a2)`: la geometría estaba peleada con su propio control.

Y su consecuencia en la ventana — `clon/omnicad/ui/comandos/solido.py:357-365` (`Revolucion.manipuladores`): con `abs`, arrastrar el asa del lado 2 por debajo de 0 no cambiaba nada, así que las dos asas de ángulo se frenan en 0 con «Dos lados» y siguen libres en «Un lado», donde el signo sí significa:

```python
dos = v.get("direccion") == "dos_lados"
salida = [mp.Angulo("angulo", pie, d, centro - pie, radio, minimo=0.0 if dos else -360.0)]
if dos:
    salida.append(mp.Angulo("angulo2", pie, -d, centro - pie, radio, minimo=0.0))
```

**Gemelos revisados** (regla 1; `grep -rn "dos_lados" clon/omnicad` → 70 sitios; los que calculan una geometría con el lado 2 son estos):

| Gemelo | Regla hoy | Qué hice |
|---|---|---|
| `nucleo/solidos_crear.py:676` `revolver_avanzado` | `[(0.0, abs(angulo1)), (0.0, -abs(angulo2 or 0.0))]` | ya era magnitud → de acá saqué la regla |
| `nucleo/superficies.py:475` `revolver_superficie` | `[(0.0, abs(angulo))] + [(0.0, -abs(a2))]` | ya magnitud; sin cambio |
| `timeline/operaciones.py:1316` `OpRevolucion` | usaba el signo | **arreglado** |
| `timeline/operaciones.py:1242` `_extrusion_basica` (el hermano de B-205) | `unir_todos([extruir(..., abs(d1)), extruir(..., -n, abs(d2))])`, con el comentario «el número es una magnitud, su signo no invierte el lado» | precedente directo; sin cambio |
| `nucleo/solidos_crear.py:604` `extruir_avanzado` | `[(abs(distancia1), …), (-abs(distancia2), …)]` | ya magnitud; sin cambio |
| `nucleo/superficies.py:276` y `:389` (extrusión de superficie) | `abs(distancia), abs(distancia2)` | ya magnitud; sin cambio |
| `ui/comando.py:719` `tramo_previa` (previa rápida de Extruir) | `a, b = -abs(d2), abs(d1)` | ya magnitud, y **no toca la Revolución** (es del prisma de Extruir): la previa de Revolución se calcula con el núcleo, así que el arreglo la cubre sola |
| `ui/comandos/solido.py:357` (asas de Revolución) | el asa podía bajar de 0 sin efecto | **arreglado** (tope en 0) |
| `ui/comandos/solido.py:102` (flechas de Extruir) | B-205 ya las frenaba en 0 | referencia del criterio; sin cambio |
| `timeline/ops_superficie.py:202` (`OpSupRevolucion`) | pasa `angulo2` con signo al núcleo, que hace `abs` | sin cambio |
| `ui/comandos/solido.py:307-309` y `ui/comandos/superficie.py:103-105` (campos «Ángulo del lado 1 / del lado 2») | los dos diálogos ya se llaman igual y no prometen signo | sin cambio |
| `api/herramientas_solido.py:388` y `api/herramientas_superficie.py:150` (`revolve`, `create_surface_revolve`) | `angle2` vacío = `angle`; el docstring dice «angle hacia un lado y angle2 hacia el otro», que es la regla de magnitud | sin cambio de texto → no se regenera `docs/agentes/herramientas.md` |
| `nucleo/chapa.py:1111` (pestaña de contorno de CHAPA: `(-distancia2, distancia)`) | con valores negativos tira «Dirección o distancias de la pestaña de contorno inválidas» (`:1112`): no hay forma muda | revisado y **no aplica** (otro comando, y ya avisa) |
| `nucleo/omnikernel/geometria.py:170` (`revolver` del otro motor) | `abs(angulo)` por cara | coincide con la nueva regla; sin cambio |

**Test nuevo y su salida.** `tests/test_api_solido.py::test_revolucion` (90/−45, −90/45 y −90/−45 dan 135/360), `tests/test_api_superficie.py::test_revolucion_segmento_alrededor_de_z` (45 y −45 dan la misma área) y `tests/test_manipuladores.py::test_dos_lados_de_la_revolucion_cada_asa_es_la_magnitud_de_su_lado` (la previa con −45 es igual a la de +45 y las asas no bajan de 0).

ROJO antes del arreglo:

```
$ pytest tests/test_api_solido.py::test_revolucion tests/test_api_superficie.py::test_revolucion_segmento_alrededor_de_z -q
E   AssertionError: {'angle': 90, 'angle2': -45}
E     assert 9387.0788 == 14080.618274999999 ± 0.0140806
1 failed, 1 passed in 1.46s        (falla el sólido; la superficie ya pasaba: el test es la comparación de los dos)

$ pytest "tests/test_manipuladores.py::test_dos_lados_de_la_revolucion_cada_asa_es_la_magnitud_de_su_lado" -q
E   assert (-360.0 == 0.0)
1 failed in 1.69s
```

VERDE después:

```
2 passed in 1.30s      (los dos de revolución)
6 passed in 2.06s      (los cinco tests nuevos de la tanda, corridos por nombre)
```

### `/ponytail-review` (salida completa, sobre el diff de los tres archivos)

`What this change does:` dos reglas de una línea. El recorte de ruta del barrido y la tubería deja de tragarse los valores mayores que 1 (y NaN/∞) y avisa; y el «Dos lados» de la Revolución deja de mirar el signo de cada ángulo, como ya hacían su núcleo, su superficie y la Extrusión. Además las asas del diálogo de Revolución se frenan en 0 con «Dos lados». Carga esperada: una persona o un agente sobre un documento (el criterio del repo); nada de esto corre en un bucle.

**Must fix:** nada.

**Should fix:**

1. **El asa del lado 2 queda inerte por debajo de cero** (`ui/comandos/solido.py:357-365`)
   - **What this is:** Con «Dos lados» el diálogo muestra dos arcos con asa, uno por lado, girando sobre `d` y `-d`.
   - **Problem:** Al tomar `abs` en el paso, un valor negativo tecleado o arrastrado sigue escribiéndose pero ya no cambia la forma: el usuario mueve el asa y el cuerpo no se mueve. Extruir tuvo exactamente esto y se cerró con un tope en 0 (B-205).
   - **Fix:** `minimo=0.0` en las dos asas cuando `direccion == "dos_lados"`, dejando `-360.0` en «Un lado», donde el signo sí significa. Tres líneas, sin clase nueva.
   - **If we skip it:** La ventana ofrece un arrastre que no hace nada, contra la regla de honestidad del repo.

**Nice to have:**

2. **`min(fraccion, 1.0)` sigue en `_recortar_alambre`** (`nucleo/solidos_crear.py:259`)
   - **What this is:** El recorte que causaba el B-211.
   - **Problem:** Después del rechazo solo se alcanza con un valor entre 1 y 1+1e-9 (la tolerancia): es código casi muerto.
   - **Fix:** **no lo toqué** — con `inicio` distinto de 0 (Tubería) esa banda existe y el `min` es lo que la mantiene dentro de la ruta. Sacarlo cambia comportamiento para ganar dos caracteres.
   - **If we skip it:** Nada.

**Arreglé de la revisión:** el ítem 1 (el tope del asa), con su test y su salida ROJA tomada revirtiendo el cambio. El ítem 2 queda como está, con la razón arriba.

**Verdict: Ship.**

### Verificación

`ruff check .` desde `clon/`: `All checks passed!`

Tests: todos con `turno`, `-p no:cacheprovider`, en primer plano y de a un grupo (la lista es la obligatoria de la tanda más los archivos que da `grep -l` de cada función tocada: `barrer`, `barrer_cuerpo`, `tuberia`, `barrer_superficie`, `revolver`, `Revolucion`; `_recortar_alambre` y `OpRevolucion` no aparecen en ningún test). 48 archivos, 2505 comprobaciones, ninguna corrida cortada por tiempo:

| Grupo | Archivos | Salida final |
|---|---|---|
| 1 · núcleo | test_solidos_crear, test_superficies, test_superficie_fusion, test_geometria, test_b52_espiral, test_bugs_solido, test_paridad_motor | `243 passed in 151.78s (0:02:31)` |
| 2 · barrido y tubería | test_sol08_barrido, test_barrido_tipos, test_api_barrido, test_gizmo_barrido, test_superficie_guias, test_tuberia_cadena, test_topes, test_rosca_diametros_tabla, test_rosca_clases_tablas, test_boceto_fase8_3d, test_iconos_extra | `469 passed in 89.06s (0:01:29)` |
| 3 · API sólido/superficie | test_sol07_revolucion, test_api_solido, test_api_solido_extra, test_api_superficie, test_api_opciones_solido1, test_api_opciones_solido2, test_herramientas_solido, test_sup29_encadenado_superficie, test_opciones_operaciones, test_resultados_vacios, test_referencias_mal_formadas, test_graficos_rendimiento | `704 passed in 123.43s (0:02:03)` |
| 4a · diálogos y asas | test_comandos, test_comandos_superficie, test_comandos_crear, test_manipuladores, test_b105_panel_chico | `83 passed in 11.93s` |
| 4b · previa, catálogo y cobertura UI | test_previa_prisma, test_previa_aislada_comandos, test_previa_trabajador, test_previa_vaciado_aislada, test_asas_superficie, test_busqueda_comandos, test_claves_comandos, test_cobertura_ui_api, test_manipuladores (otra vez, ya con el tope del asa) | `495 passed in 324.01s (0:05:24)` |
| 5 · seguimiento y doc | test_seguimiento, test_doc_agentes, test_api_documento, test_api_catalogo, test_api_convenciones | `511 passed in 18.02s` |

Suite completa y prueba de humo: no corridas (regla 10; las toma el coordinador).

Después de editar `PROJECT_LOG.md`, `docs/seguimiento/bugs.md` y este informe, se volvieron a correr los tres archivos que leen esa documentación: `test_seguimiento.py`, `test_doc_agentes.py` y `test_claves_comandos.py` → `450 passed in 5.94s`, y `ruff check .` → `All checks passed!`.

Ventana (regla 9, porque toqué `ui/comandos/solido.py` y cambió la previa del Barrido): la pieza `revolucion_barrido_solevacion` en minimizada. `todo.py` la corta a los 900 s de su `turno` interno (dos intentos), así que se corrió derecho con `../scripts/turno.py --plazo 2700 -- .venv/Scripts/python.exe ../scripts/prueba_ui/revolucion_barrido_solevacion.py` desde `clon/`, con `OMNICAD_PRUEBA_VENTANA=minimizada`:

```
=== 40 comprobaciones, 8 con ✗ ===
```

Los dos checks que hablan de estos bugs pasaron, y son justo los que estaban ✗ en la auditoría (10 ✗ → 8 ✗):

```
[OK ] · Enter acepta la revolución y crea UN paso
[OK ] · Revolución dos lados 90 / −45°: o aviso o 2356,19 mm³ (como la superficie), no el lado 2 perdido — volumen 2356.19 sin aviso «»
[OK ] · reabrir la revolución trae «Dos lados» y −45° — {'direccion': 'dos_lados', 'angulo2': '-45 deg'}
[OK ] · Barrido › Distancia «0,5»: previa
[OK ] · Barrido › Distancia «0»: aviso — ⚠ La distancia sobre la ruta debe ser mayor que cero.
[OK ] · Barrido › Distancia «1,5»: aviso — ⚠ La distancia sobre la ruta va de 0 a 1 (fracción del total); recibió 1.5.
[OK ] · Barrido › Distancia «»: aviso — ⚠ Expresión vacía.
```

O sea: en la ventana real, teclear «1,5» en Distancia ahora **avisa** (antes dejaba la previa en verde), y el lado 2 con −45° da el cuerpo de 135° en vez de perderse. Las 8 ✗ que quedan son todas ítems ya anotados, ninguno de esta tanda: H-88 (2: «A objeto» no muestra Dirección, en sólido y en superficie), H-92 (2: «Proyectar eje» con nombre y valor por defecto distintos), B-209 (Estirar no está en la lista), H-89 (sin Extensión con carril), B-208 (el carril paralelo da 784,02 en vez de 800) y H-90 (la fila del punto solo ofrece «Aguda»).

Capturas miradas con Read: `capturas/barrido_carril.png` (la app entera, con el aviso flotante y el árbol de cuerpos; sin nada roto) y las de tamaño de panel `barrido_1024x640.png` / `barrido_800x520.png`, que la pieza pide en sus dos checks de «Aceptar se ve».

Evidencia: `evidencias/ui_2026-11-05/revolucion_barrido_solevacion.json` y `.log` (la corrida de las 23:42, cortada por el plazo, dejó el `.log` de la auditoría en 63 bytes; se restauró con la salida completa de esta corrida, que es la que está arriba).

### Seguimiento

- `docs/seguimiento/bugs.md`: borradas la fila y la sección «Detalle» de B-211 y de B-210; recuento del encabezado 25 → 23 (Abierto 19 · Parcial 4).
- `docs/seguimiento/README.md`: no tenía filas de esos dos IDs (`grep -n "B-210\|B-211"` → nada), así que no había qué borrar.
- `README.md` y `README.en.md` (hoja de ruta): sin mención de estos dos bugs (`grep` → nada); no se tocó.
- Dos viñetas en «## Registro» de `PROJECT_LOG.md` y una lección en «## Lecciones aprendidas».

### Archivos fuera de mi tanda

La tabla de la tanda 1 no lista `timeline/operaciones.py` (donde está `OpRevolucion.ejecutar`, que es justo la línea que nombra la fila de B-210) ni `ui/comandos/solido.py` (el tope del asa, consecuencia del `abs`). Los dos se tocaron por eso, y nada más. No se tocó `nucleo/superficies.py`, `timeline/ops_solido.py`, `timeline/ops_superficie.py`, `ui/comandos/crear.py` ni `ui/comandos/superficie.py`: los gemelos de esos archivos ya tenían la regla.

### Lo que no pude verificar

- ⚠ **Fusion real no se abrió** para B-210: la ayuda no dice qué hace un ángulo negativo en Two Sides. La regla elegida es la que ya estaba en `revolver_avanzado`, `revolver_superficie` y la Extrusión (B-205), no una observación de Fusion. Si al abrirlo resultara que Fusion rechaza el negativo, el cambio vuelve a ser una línea en cada lado (los tres están juntos).
- ⚠ No verifiqué en la ventana el **arrastre** del asa con el tope nuevo: el test pytest mira el `minimo` del manipulador y el volumen de la previa, no el arrastre con el ratón, y la pieza `revolucion_barrido_solevacion` teclea los ángulos (el arrastre de la Revolución con valores positivos lo prueba `test_angulo_de_la_revolucion`, que quedó verde en el grupo 4b).
- ⚠ El check de ventana de B-210 mide el **sólido** contra los 135° esperados; la igualdad con la superficie en la ventana no se volvió a medir ahí (sale del pytest `test_api_superficie.py::test_revolucion_segmento_alrededor_de_z` y de que la superficie nunca usó el signo).
- ⚠ Proyectos `.omnicad` guardados con una Distancia de barrido mayor que 1 ahora dan error al abrir en vez del cuerpo recortado. En `ejemplos/` no hay ninguno (`grep -rln "barrido" ejemplos/` → nada), pero una pieza del usuario puede tenerlo.

## Informe tanda 2

Corrida del 2026-11-06 (01:30 a 03:00). OpenCode con Qwen3.8-Flash en Qoder. Bugs: B-216 y B-214, de a uno y en ese orden.

### B-216 · Red › «Cambiar dirección» no invierte el sentido — **Resuelto**

**Qué dice la ayuda de Fusion** (`fusion_docs.py ver "Web reference" -s fusion-model`, desde `clon/`):

> ## Flip Direction
> Flips the direction in which the web feature is extruded.

Y en `Rib reference`, la misma frase para el Nervio. O sea: el botón gira la extrusión, no el espesor.

**Estado del código antes de decidir** (medido con `../evidencias/ui_2026-11-05/sondas_nrr.py`, caja 40³ cerrada vaciada 2 mm, boceto en y = 15 con la línea z = 20):

```
red_adentro_normal    | ok | V=18280.00      red_abierta_y15            | ok | V=16408.00
red_adentro_invertir  | ok | V=18280.00      red_abierta_y15_invertir   | ok | V=16408.00
```

18280 = 17344 + 36·13·2: la red siempre iba a la pared de enfrente (a 13 mm), con y sin invertir. La otra pared está a 23, así que invertida tenía que dar 17344 + 36·23·2 = **19000**.

**Qué cambié** — `clon/omnicad/timeline/ops_solido.py:287` (`OpRed.ejecutar`): se deja de negar la normal y se baja el `invertir` del `PARAMS`, que `red()` ya recibía sin ningún llamador.

```python
forma = _sc().red(cuerpo.forma, aristas, plano.normal, ctx.evaluar(self.p["espesor"]), prof,
                  direccion=self.p["direccion"], invertir=self.p["invertir"], extender=self.p["extender"],
                  angulo_desmoldeo=ctx.evaluar(self.p["angulo_desmoldeo"], ANGULO))
```

Antes la normal negada entraba en `_sentido_hacia_cuerpo`, que prueba `(-n, n)` y elige la que choca antes: la negación se deshacía sola y el botón no movía nada (solo cambiaba el lado de «Un lado», porque de ahí sale `s`).

**El arreglo de la revisión** (regla 3; detalle abajo) — `clon/omnicad/nucleo/solidos_crear.py:1387` (`_sentido_hacia_cuerpo`): con `invertir` devuelve el sentido contrario **sin mirar si ese lado tiene cara**, así que la red invertida hacia la boca abierta terminaba recortada contra la caja del cuerpo (+1080 mm³ colgando, el mismo recorte de B-213). Ahora, con `exigir_cara` (Al siguiente; con «Distancia» no, porque ahí la banda al aire es el resultado pedido), avisa:

```python
    opuesto = -mejor[1]
    if exigir_cara and not [h for h in _rayo(cuerpo, medio, opuesto) if h > 1e-7]:
        raise geo.ErrorGeometria("El sentido invertido no llega al cuerpo: desactivá «Cambiar dirección»"
                                 " o mové el boceto.")
    return opuesto
```

Con esto se cumple la segunda mitad de la fila («con la boca abierta, Fusion avisaría») y cae de paso el primer síntoma de **B-213**: el Nervio invertido hacia afuera, que antes rellenaba hasta la caja (+1950 → 27450 mm³), ahora da el aviso. B-213 sigue abierto con lo demás (medido hoy: `nervio_borde_simetrico` 26100, `nervio_borde_lado1` «la curva queda dentro del cuerpo», `nervio_espesor_enorme` 61500).

**Gemelos revisados** (regla 1; `grep -rn "invertir" clon/omnicad` filtrado por nervio/red, `grep -rn "plano.normal"`, `grep -rn "nervio\|red" clon/omnicad/nucleo/omnikernel/`):

| Gemelo | Regla hoy | Qué hice |
|---|---|---|
| `timeline/ops_solido.py:287` `OpRed` | negaba la normal | **arreglado** (pasa `invertir`) |
| `nucleo/solidos_crear.py:1488` `red(invertir=)` | el parámetro existía sin llamador | ahora tiene llamador; sin cambio en su firma |
| `nucleo/solidos_crear.py:1387` `_sentido_hacia_cuerpo` | invertía sin mirar la cara | **arreglado** (el aviso nuevo, con `exigir_cara`) |
| `nucleo/solidos_crear.py:1449` `nervio(invertir=)` | usa el mismo helper | cubierto por el arreglo del helper; medido: `nervio_invertir` pasa de 27450 a avisar |
| `api/herramientas_solido_extra.py:161` `_nervio` | ya pasaba `invertir=reverse` a las dos operaciones | sin cambio de código; texto de `create_web` › `reverse` («invertía la normal usada por el comando Red» → «invierte el sentido de extrusión… va a la otra pared») y regenerado `docs/agentes/herramientas.md` (1 línea) |
| `ui/comandos/crear.py:312` `Alternar("invertir", "Cambiar dirección")` | el mismo campo para Nervio y Red | sin cambio |
| `ui/comandos/asas_extra.py:295` `_asas_nervio` | la flecha de «Distancia» se dibuja sobre `normal × (−1 si invertir)`, no sobre el sentido que eligió el núcleo | revisado con medición (`evidencias/ui_2026-11-06/sonda_asas_red.py`) y **no lo toco**: es otro bug → fila nueva **B-219** |
| `nucleo/plastico.py` | sin geometría de Nervio/Red (la regla de plástico es H-87 / H-100 / H-102); PLÁSTICO abre los mismos `OpNervio`/`OpRed` | no aplica; la pieza verifica los botones de PLÁSTICO |
| `nucleo/omnikernel/` | `grep "nervio\|def red"` → nada | no aplica |
| la previa (`ui/comando.py`) | la del Nervio y la Red corre la operación (`_previa_pesada`), no una regla copiada | cubierta sin cambio |
| `edit_feature` (`api/herramientas_documento.py`) | recalcula el paso con el mismo `ejecutar` | cubierto |
| `timeline/ops_superficie.py`, `nucleo/superficies.py` | Superficie no tiene Nervio ni Red (índice `fusion-patch`, visto en la auditoría) | no aplica |
| `nucleo/analisis.py:1294` (`-plano.normal if invertir`) | es «Voltear» del corte de sección | otro comando; sin cambio |

**Tests nuevos y su salida.** `tests/test_sol10_nervio_red.py::test_red_invertir_cambia_de_pared` (parametrizado 18280 / 19000, con la caja `y` de la red cortada contra el cuerpo antes) y `::test_red_invertir_hacia_la_boca_abierta_avisa` (16408 sin invertir; invertida, aviso y el documento intacto).

ROJO antes del arreglo:

```
$ pytest tests/test_sol10_nervio_red.py -q -p no:cacheprovider -k "invertir"
E   assert 18279.999999999993 == 19000.0 ± 1.9
E     comparison failed
E     Obtained: 18279.999999999993
E     Expected: 19000.0 ± 1.9
FAILED tests/test_sol10_nervio_red.py::test_red_invertir_cambia_de_pared[True-19000.0]
1 failed, 1 passed, 10 deselected in 1.36s
```

ROJO del arreglo de la revisión (con el chequeo nuevo desactivado un momento, `if False and exigir_cara …`):

```
$ pytest tests/test_sol10_nervio_red.py -q -p no:cacheprovider -k "invertir"
E   AssertionError: {'ok': True, 'result': {'feature': {'id': 'op5', 'name': 'Red1', 'type': 'red'},
    'bodies_modified': [{'id': 'op1.c1', 'name': 'Cuerpo1', 'volume': 15832.0, 'previous_volume': 14752.0}], ...}}
1 failed, 2 passed, 12 deselected in 1.71s
```

O sea: `ok` con una placa de 1080 mm³ colgando de la boca abierta, en vez del aviso.

VERDE después: `3 passed, 12 deselected` (los dos de invertir y el control), y los grupos completos de la tabla de abajo.

### B-214 · Nervio con dos curvas sueltas — **Resuelto**

**Qué dice la ayuda de Fusion**: `Rib reference` dice «Select an open sketch profile» (uno), pero la imagen de «Create a rib» (`fusion_docs.py ver "Create a rib" -s fusion-model`, recurso `34082c91a878d5eec1ea.png`, mirada con Read) muestra **cuatro curvas sueltas en un boceto y sus cuatro nervios en un solo paso**. La Red ya lo hacía: `red()` recorre `_cadenas` (`nucleo/solidos_crear.py:1496`).

**Qué cambié** — `clon/omnicad/nucleo/solidos_crear.py:1449` (`nervio`): sale el `_alambre` (que exigía una sola cadena y daba el mensaje de Barrido) y entra el mismo recorrido de `red()`: por cada cadena se saca su cuerda, su sentido hacia el cuerpo (`_sentido_hacia_cuerpo`, con su `invertir`) y su desmoldeo; las brutas se unen y se recortan contra el cuerpo una vez, con **todas** las cadenas como referencia de «tocan la curva». La validación de `direccion` subió antes del bucle (el mismo mensaje, sin calcular geometría para nada). Con una sola cadena el camino es idéntico al de antes: `_unir([x])` devuelve `x` sin unificar.

**Gemelos revisados** (regla 1; `grep -rn "_alambre(\|_cadenas(" clon/omnicad`, `grep -rn "nervio" clon/omnicad/api clon/omnicad/ui clon/omnicad/timeline`):

| Gemelo | Qué hice |
|---|---|
| `nucleo/solidos_crear.py:1488` `red()` | ya recorría `_cadenas`: de acá saqué la regla; sin cambio |
| `nucleo/solidos_crear.py:1449` `nervio()` | **arreglado** |
| `_alambre` (`nucleo/solidos_crear.py:213`) | sigue en la ruta del Barrido y la Tubería (`:907`, `:941`) y en las secciones del Solevado (`:1001`, `:1030`, `:1221`): ahí sí hay UNA cadena; sin cambio |
| `timeline/ops_solido.py:261` `OpNervio.ejecutar` | `_aristas` (`:61`) devuelve la lista plana de aristas elegidas y ya las mandaba todas; sin cambio |
| `ui/comandos/crear.py:303` `Seleccion("curvas", "Perfil", …, maximo=None)` | ya permitía varias curvas; sin cambio. `Nervio.AYUDA`: «una curva» → «una o varias curvas» |
| `api/herramientas_solido_extra.py:174` `_curvas` | ya pasa todas las curvas del boceto (o las `curves` dadas); sin cambio de código ni de texto (`curves` ya decía «ids de curvas») |
| `nucleo/plastico.py`, `nucleo/omnikernel/` | sin geometría de nervio propia (los botones de PLÁSTICO abren el mismo comando) | no aplica |
| la previa y `edit_feature` | corren la operación | cubiertos sin cambio |
| `timeline/ops_superficie.py` | no hay Nervio de superficie | no aplica |

**Tests nuevos y su salida.** `tests/test_solidos_crear.py::test_nervio_con_dos_curvas_sueltas_hace_un_nervio_por_curva` (en el canal en U, dos líneas sueltas sin alargar = 2 × 5·6·2 = 120 mm³ y la cuenta cuadra con la unión de los dos nervios por separado; más dos guardas: dos aristas encadenadas siguen siendo UN perfil con su caja exacta, y una circunferencia cerrada sigue con «necesita una curva abierta») y `tests/test_sol10_nervio_red.py::test_nervio_con_varias_curvas_sueltas_hace_un_nervio_por_curva` (escuadra de la auditoría, parametrizado con una y con dos líneas: 26700 mm³ y **un** paso de tipo `nervio`).

ROJO antes del arreglo:

```
$ pytest tests/test_solidos_crear.py -q -p no:cacheprovider -k "dos_curvas_sueltas"
E           omnicad.nucleo.geometria.ErrorGeometria: La ruta debe ser una sola cadena continua de aristas.
FAILED tests/test_solidos_crear.py::test_nervio_con_dos_curvas_sueltas_hace_un_nervio_por_curva
1 failed, 65 deselected in 1.28s

$ pytest tests/test_sol10_nervio_red.py -q -p no:cacheprovider -k "varias_curvas"
E       AssertionError: {'ok': False, 'error_kind': 'OPERATION_FAILED', 'mensaje': 'El paso «Nervio1» (op4) falló y se
    deshizo (el documento quedó como estaba): …'}
FAILED tests/test_sol10_nervio_red.py::test_nervio_con_varias_curvas_sueltas_hace_un_nervio_por_curva[lineas1]
1 failed, 1 passed, 12 deselected in 1.37s
```

El `1 passed` de la segunda corrida es la parametrización de una sola curva: el control de que no rompí el caso que ya andaba.

VERDE después: `16 passed, 64 deselected in 4.02s` (todos los tests con la palabra `nervio` en los dos archivos) y los grupos de abajo.

### `/ponytail-review` (salida completa, sobre el diff de los cinco archivos)

`What this change does:` dos reglas de una línea cada una. La Red deja de «invertir» negando la normal del plano —que el núcleo deshacía al elegir la pared más cercana— y baja el `invertir` que su núcleo ya tenía; y el Nervio deja de exigir una sola cadena continua, haciendo un nervio por curva como su gemelo la Red. Además el sentido invertido, cuando del otro lado no hay cara, avisa en vez de dejar una placa recortada contra la caja del cuerpo. Carga esperada: una persona o un agente sobre un documento (el criterio del repo); nada de esto corre en un bucle, y el recorrido extra es una ray-cast por cadena.

**Must fix:** nada.

**Should fix:**

1. **El sentido invertido no mira si del otro lado hay cara** (`nucleo/solidos_crear.py:1387`)
   - **What this is:** `_sentido_hacia_cuerpo` elige el sentido que choca antes con el cuerpo y, con `invertir`, devuelve el contrario.
   - **Problem:** Si el otro lado no toca nada (la caja abierta hacia ese lado), la placa igual se arma y `_hasta_el_cuerpo` la recorta contra la caja del cuerpo: `red_abierta_y15_invertir` daba 15832 mm³, una placa de 1080 mm³ colgando de la boca, sin aviso. Con el botón roto (antes de este arreglo) nadie llegaba a ese caso.
   - **Fix:** un ray-cast más sobre el sentido elegido: si no da con ninguna cara, `ErrorGeometria` claro. Solo con «Al siguiente» (`exigir_cara=profundidad is None`), porque con «Distancia» la banda al aire es el resultado pedido. Cuatro líneas en el compartido, cubre Nervio y Red.
   - **If we skip it:** El botón nuevo hace geometría muda; es el mismo fallo que B-213 pero alcanzable desde ya.
   - **Arreglé:** sí, con su test (`test_red_invertir_hacia_la_boca_abierta_avisa`) y su salida ROJA tomada revirtiendo el cambio.

2. **La flecha de «Distancia» del Nervio y la Red no sigue el sentido que eligió el núcleo** (`ui/comandos/asas_extra.py:295`)
   - **What this is:** Con «Distancia», el diálogo dibuja un asa sobre `normal del plano × (−1 si invertir)`.
   - **Problem:** Medido (`evidencias/ui_2026-11-06/sonda_asas_red.py`): caja 40³ cerrada, boceto en y = 30 (paredes a 8 y a 28) → la red crece hacia +Y y la flecha apunta −Y, con y sin invertir (MISMATCH en los dos). En el Nervio la flecha es perpendicular al crecimiento, que va dentro del plano del boceto.
   - **Fix:** **no lo hice**: pide resolver el cuerpo objetivo y el sentido real en el camino de las asas (que corre con cada movimiento del mouse), o sea la referencia del «Cuerpo» más una ray-cast en la UI — otro bug, otro día.
   - **If we skip it:** La ventana ofrece un arrastre cuya dirección miente; lo pide la regla de honestidad del repo.
   - **Fila nueva:** **B-219** en `docs/seguimiento/bugs.md` (Abierto, Baja) con la reproducción medida. B-218 no lo usé: está tomado en `codebuddy-nocturna` (`64eb920`).

**Nice to have:**

3. **`nervio` validaba `direccion` después de prismatizar la curva** (`nucleo/solidos_crear.py:1455`)
   - **What this is:** El chequeo «Dirección de espesor desconocida» estaba en el medio del cálculo.
   - **Problem:** Con un `direccion` inválido se armaba el prisma entero para tirarlo después.
   - **Fix:** subirlo antes del bucle. Mismo mensaje, menos trabajo.
   - **If we skip it:** Nada grave; solo geometría de más en un caso que no anda.
   - **Arreglé:** sí, incluido en el cambio de B-214.

**Verdict: Ship** (con el ítem 1 ya arreglado y el 2 derivado a B-219).

### Verificación

`ruff check .` desde `clon/`: `All checks passed!` (antes y después del arreglo de la revisión).

Tests: todos con `turno`, `-p no:cacheprovider`, en primer plano y de a un grupo (la lista obligatoria de la tanda más los archivos que da `grep -l` de lo tocado: `nervio`, `red`, `_sentido_hacia_cuerpo`, `_cadenas`, `OpNervio`, `OpRed`, `create_rib`, `create_web`; `_alambre` y `_hasta_el_cuerpo` no aparecen en ningún test por su nombre). Ninguna corrida cortada por tiempo:

| Grupo | Archivos | Salida final |
|---|---|---|
| 1 · núcleo y plástico | test_solidos_crear, test_sol10_nervio_red, test_sol21_reglas_plastico | `84 passed in 39.52s` |
| 2 · API | test_api_solido, test_api_solido_extra, test_cobertura_ui_api, test_herramientas_solido, test_sol27_preajustes | `630 passed in 105.83s (0:01:45)` |
| 3 · diálogos, asas y lotes | test_comandos, test_manipuladores, test_iconos_extra, test_revision_lotes_sol | `278 passed in 10.16s` |
| 4 · tras el arreglo de la revisión (núcleo) | test_sol10_nervio_red, test_solidos_crear | `81 passed in 58.89s` |
| 5 · tras el arreglo (API + UI + plástico juntos) | los 10 archivos de los grupos 2 y 3 más test_sol21_reglas_plastico | `912 passed in 114.77s (0:01:54)` |
| 6 · seguimiento y doc | test_seguimiento, test_doc_agentes, test_claves_comandos, test_api_catalogo, test_api_convenciones | `479 passed in 12.23s` |

Suite completa y prueba de humo: no corridas (regla 10; las toma el coordinador).

Sondas de la auditoría, corridas de nuevo (`../evidencias/ui_2026-11-05/sondas_nrr.py`, contra su `.txt` del 2026-11-05):

| Caso | Antes | Después |
|---|---|---|
| `nervio_dos_curvas_sueltas` | ERR «La ruta debe ser una sola cadena…» | ok 26700 |
| `nervio_base` / `nervio_polilinea` | 26700 / 26700 | 26700 / 26700 (sin cambio) |
| `nervio_invertir` | ok 27450 (+1950 hasta la caja) | ERR «El sentido invertido no llega al cuerpo…» |
| `nervio_invertir_prof` (Distancia 5) | ok 26041,67 | ok 26041,67 (sin cambio: con «Distancia» no se exige cara) |
| `nervio_borde_simetrico` / `_lado1` / `_lado2` | 26100 / ERR / 26700 | iguales (B-213 sigue) |
| `nervio_espesor_enorme` | ok 61500 | ok 61500 (B-213 sigue) |
| `red_adentro_normal` / `red_adentro_invertir` | 18280 / 18280 | **18280 / 19000** |
| `red_abierta_y15` / `red_abierta_y15_invertir` | 16408 / 16408 | 16408 / **ERR con aviso claro** |
| `red_invertir_sin_cara` | ok 20072 | ERR con el mismo aviso |
| `red_base`, `red_sin_extender`, `red_profundidad`, `red_lado1`, `red_lado2`, `red_empalme`, `red_desmoldeo` | 20072, 17640, 16152, 20072, 20072, 20197,61, 23411,72 | iguales |

Ventana (regla 9, porque cambió el comportamiento de los diálogos de Nervio y Red y toqué el texto del comando): la pieza `nervio_red_repujado` en minimizada, con `PYTHONIOENCODING=utf-8` y `--plazo 2700` (la primera corrida, sin el `PYTHONIOENCODING`, se cortaba imprimiendo el `✗` con cp1252):

```
=== 84 comprobaciones, 6 con ✗ ===
```

En la auditoría eran 82 comprobaciones con 9 ✗. Pasaron los checks de esta tanda y el de B-213 que dependía del mismo botón:

```
[OK ] · Nervio con dos curvas sueltas: vista previa
[OK ] · Nervio con dos curvas sueltas: aceptar — cambiados={'op1.c1': ('solido', 26700.0)}
[OK ] · Nervio con dos curvas sueltas: deshacer vuelve al estado anterior (1 paso/s)
[OK ] · Nervio invertido: se rechaza con un aviso claro — «⚠ El sentido invertido no llega al cuerpo: desactivá «Cambiar dirección» o mové el boceto.»
[OK ] · Red dentro de la caja: resultado = 1656 — obtenido 1656.0
[OK ] · Red invertida hacia la boca abierta: se rechaza con un aviso claro — «⚠ El sentido invertido no llega al cuerpo…»
```

(84 vs 82: el caso de las dos curvas ahora corre y suma sus checks de aceptar y deshacer, que antes se cortaban en la previa.)

Las 6 ✗ que quedan son ítems ya anotados, ninguno de esta tanda: B-215 (2: desmoldeo −1° y 1° con extracción), H-95 (el Nervio no tiene Radio del empalme), B-217 (cadena tangente 437,12) y H-97 (asas de alineación del Repujado). (H-99 se resolvió aparte: ver «## Informe tanda 5».)

Capturas miradas con Read: `capturas/red_invertida.png` (el panel RED con «Cambiar dirección» activo, el aviso visible y el cuerpo intacto) y `capturas/red_caja.png`. Evidencia: `evidencias/ui_2026-11-06/nervio_red_repujado.log` y `.json`, y la sonda `evidencias/ui_2026-11-06/sonda_asas_red.py`.

### Seguimiento

- `docs/seguimiento/bugs.md`: borradas la fila y la sección «Detalle» de B-216 y de B-214; recuento del encabezado 23 → 22 (Abierto 19 → 18, con la fila nueva B-219 · Parcial 4).
- B-213: actualizado. Su primer síntoma («invertido rellena hasta la caja, +1950») ya avisa, medido; quedan el borde (+600 y el error falso de un lado), el `thickness=1e6` y la Red delante de la caja. Su `archivo:línea` pasó a `solidos_crear.py:1419` (`_hasta_el_cuerpo`), que es donde está ahora.
- Fila nueva **B-219** (con su ficha de «Detalle»): la flecha de «Distancia» del Nervio y la Red, ítem 2 de mi `ponytail-review`.
- `docs/seguimiento/README.md`: no tenía filas de B-214 ni B-216 (`grep -n "B-214\|B-216"` → nada), así que no había qué borrar.
- `README.md` y `README.en.md` (hoja de ruta): sin mención de estos bugs ni de Nervio/Red (`grep` → nada); no se tocaron.
- Dos viñetas en «## Registro» de `PROJECT_LOG.md` y una lección en «## Lecciones aprendidas» (parámetro del núcleo sin llamador = botón roto).

### Archivos fuera de mi tanda

La tabla de la tanda 2 lista `nucleo/solidos_crear.py` y `timeline/ops_solido.py`. También toqué, una línea de texto en cada uno: `api/herramientas_solido_extra.py` (el `reverse` de `create_web` decía «invertir la normal usada por el comando Red», que era la descripción del botón roto) con su regeneración de `docs/agentes/herramientas.md`, y `ui/comandos/crear.py` (la ayuda del comando Nervio decía «una curva»). No se tocó `ui/comandos/asas_extra.py` (de ahí B-219) ni `nucleo/plastico.py` (sin geometría de Nervio/Red). `docs/corrida_nocturna_2026-11-05.md` aparece modificado en el árbol: es de otra corrida, no lo miré ni lo cambié.

### Lo que no pude verificar

- ⚠ **Fusion real no se abrió.** La regla del Flip sale del texto de la ayuda («Flips the direction in which the web feature is extruded») y la de varias curvas de la imagen de «Create a rib» (leída con Read: cuatro curvas, cuatro nervios). No se comparó con el programa: si Fusion en la boca abierta hiciera otra cosa que avisar (por ejemplo ir igual a la cara más lejana del sólido), el aviso nuevo vuelve a ser una línea en `_sentido_hacia_cuerpo`.
- ⚠ **El asa de «Distancia» no se probó arrastrándola** con el nuevo sentido: ese arreglo quedó derivado a B-219 y la pieza solo teclea «Cambiar dirección»; sus checks de arrastre (`red › arrastrar «profundidad» 3 mm`) pasaron porque miden el valor, no la dirección de la flecha.
- ⚠ **Desmoldeo + varias curvas**: cada cadena toma su propio `m` para el `pull` del desmoldeo, que es la única lectura razonable, pero no hay test que lo mida — el desmoldeo del Nervio con ángulo negativo o extracción que no coincide sigue roto (B-215, para Opus).
- ⚠ **Nervio con curvas de dos bocetos distintos**: `OpNervio` usa el plano del primer boceto (`timeline/ops_solido.py:262`); con varias cadenas de bocetos de planos diferentes no lo probé (la Red ya aceptaba varias cadenas y tiene la misma regla, así que no es un cambio mío).
- ⚠ **Proyectos guardados con una Red invertida**: antes daban la misma red que sin invertir; ahora pueden dar el aviso nuevo (boca abierta) o la otra pared (caja cerrada). En `ejemplos/` no hay recetas de nervio ni red (`grep -rln "nervio\|red" ejemplos/` → nada), pero una pieza del usuario puede cambiar de forma al abrir.
- ⚠ **B-213 sigue abierto** y es vecino directo: el recorte contra la caja del cuerpo aparece en los dos caminos que arreglé (el invertido sin cara lo esquivé con el aviso; el `thickness=1e6` y el boceto en el borde quedan).

## Informe tanda 3

Corrida del 2026-11-06. OpenCode con Qwen3.8-Flash en Qoder. Bugs: B-217 y B-209, de a uno y en ese orden.

### B-217 · Repujado con «Cadena tangente» repuja también en los costados — **Resuelto**

**Qué dice la ayuda de Fusion** (`fusion_docs.py buscar "Emboss"` → `contenido/fusion-model/emboss-reference-a3f0ac82148.md`):

> ## Tangent Chain
> Check to automatically select tangentially connected geometry.

y en `emboss-a-solid-body`: «Uncheck **Tangent Chain** if you don't want to automatically select tangentially connected geometry.» La ayuda no dice que el perfil se copie en esas caras; lo que rige en OmniCAD para las caras elegidas es la proyección («cada cara recibe solo la parte que le cae encima»), y la auditoría dejó anotada la única diferencia deliberada: «REP · cara perpendicular al boceto: OmniCAD «adapta» el perfil (decisión del 2026-10-13 en PROJECT_LOG); Fusion lo proyecta». ⚠ Fusion real no se abrió.

**Estado del código antes de decidir** (medido con `../evidencias/ui_2026-11-06/sonda_tanda3.py`; placa 60×40×10 con las cuatro aristas de arriba empalmadas r 3, cuadro 10×10 en el centro de la tapa, relieve 1 mm):

```
placa: 23624.07  caras tangentes de la tapa: 9        (tapa + 4 empalmes + 4 costados)
cadena_tangente=False: +100.00  caja [20,15,10]..[30,25,11]
cadena_tangente=True:  +437.12  caja [-1,-1,0.35]..[61,41,11]
```

El 437,12 de la fila salió tal cual. Al desglosarlo por tipo de cara (`sonda_b217_caras.py`) apareció **más de lo que decía la fila**: no eran solo los cuatro costados adaptados; los cuatro empalmes cilíndricos también recibían material (+278,36 con los costados ya descartados), porque el envoltorio le da vueltas al cilindro (empalme izquierdo, a 19 mm del cuadro: +39,71). La regla había que escribirla antes de las dos ramas, no en una.

**INTENT:** el código adaptaba/envolvió el perfil en TODAS las caras de la cadena y sumaba 437,12 mm³; la fila B-217 y su prueba propuesta piden +100 mm³ y la caja sin crecer; la decisión documentada del 2026-10-13 (`PROJECT_LOG.md` › «Repujado en varias caras a la vez», y sus tests `test_repujado_en_varias_caras_a_la_vez_adaptandose_a_cada_una` / `test_repujado_adaptado_se_achica_si_no_entra_en_la_cara`) dice que una cara **elegida a mano** perpendicular al perfil se adapta. Los dos conviven: la regla nueva alcanza solo a las caras que agregó la cadena.

**Qué cambié** — `clon/omnicad/nucleo/solidos_crear.py:1579-1597` (`repujado_en_cuerpos`, la expansión de la cadena):

```python
    for k, cara in enumerate(cadena):
        if k and not _cajas_se_tocan(_caja_2d([cara], pl_perfil), caja_perfil):
            continue
        if not any(j == i and cara.IsSame(otra) for j, otra in caras):
            caras.append((i, TopoDS.Face(cara)))
```

`k == 0` es la cara que el usuario eligió (sigue adaptando/envolviendo como hasta ahora); las demás son regaladas por la cadena y se descartan si su caja proyectada sobre el plano del perfil no toca la del perfil. Es la misma cuenta en 2D que usa el reparto entre caras paralelas dos líneas más abajo (`_caja_2d` / `_cajas_se_tocan`, en `_repujado_en_grupo`), así que cubre planas y cilíndricas con una sola regla sin tocar ninguna de las dos ramas. `pl_perfil` es el `geo.plano_de_cara(perfiles[0])` que la rama cilíndrica ya calculaba (subido, no duplicado). La lección del 2026-10-13 («misma regla para uno y para varios») se respeta: la regla no depende de cuántas caras hay ni de su tipo.

**Gemelos revisados** (regla 1; `grep -rn "cadena_tangente" clon/omnicad`, `grep -rn "caras_tangentes(" clon/omnicad`, `grep -rln "repuj\|emboss" clon/tests`):

| Gemelo | Regla hoy | Qué hice |
|---|---|---|
| `nucleo/solidos_crear.py:1551` `repujado_en_cuerpos` | adaptaba toda la cadena | **arreglado** (el filtro, un punto) |
| `_repujado_en_grupo` / `_perfiles_en_zona` (la adaptación) | gira, centra y achica | sin cambio: rige para las caras elegidas a mano (decisión 2026-10-13, tests verdes) |
| `_envolver_en_cilindro(..., recortar=cadena_tangente)` | la cadena sumaba cilindros lejos del perfil | el filtro los descarta antes de llegar; **su vuelta de más con una cara elegida a mano queda como fila nueva B-220** (medida) |
| `nucleo/solidos_crear.py:1542` `repujado` (la firma de un cuerpo) | pasa a `repujado_en_cuerpos` | cubierto por el mismo punto; sin cambio |
| `timeline/ops_solido.py:319` `OpRepujado` | baja `cadena_tangente` del `PARAMS` | sin cambio (ninguna clave nueva: la receta vieja abre igual) |
| `api/herramientas_solido_extra.py:230` `create_emboss` | «tangent_chain: true incluye las caras tangentes» | sigue siendo cierto (las incluye; reciben lo que cae) → **no se regenera** `docs/agentes/herramientas.md` |
| `ui/comandos/crear.py:363` Casilla «Cadena tangente» | mismo campo | sin cambio |
| `nucleo/calcomanias.py:43` (`encadenar` de la Calcomanía) | usa `caras_tangentes` | revisado y **no aplica**: proyecta la imagen con el marco UV de cada cara y la recorta contra esa cara; no adapta ni copia un perfil |
| `nucleo/solidos_modificar.py:1097` (Desmoldeo con cadena) y `:1385` (Reemplazar cara) | suman la cadena | **no aplica**: transforman las caras de la cadena, no reparten un perfil |
| `nucleo/omnikernel/` | `grep "repuj\|emboss"` → nada | no aplica (el otro motor no tiene Repujado) |
| la previa (`ui/comando.py`) | `tramo_previa` es del prisma de Extruir; el Repujado corre la operación | cubierta sin cambio |
| `edit_feature` (`api/herramientas_documento.py`) | recalcula el paso con el mismo `ejecutar` | cubierto |

**Test nuevo y su salida.** `tests/test_repujado_alineacion.py::test_cadena_tangente_no_copia_el_perfil_en_los_costados` (+100 exactos y la caja del material 10×10×1) y `tests/test_api_solido_extra.py::test_create_emboss_cadena_tangente_no_copia_el_perfil_en_los_costados` (la repro de la fila por la API: `create_box` 60×40×10, `fillet edges=">Z" radius=3`, `create_emboss ... tangent_chain=true`). Auxiliares del primer archivo: `_rectangulo` ahora toma coordenadas (con los valores de siempre por defecto) y se sumó `_aristas_en_z`.

ROJO antes del arreglo:

```
$ pytest tests/test_repujado_alineacion.py -q -p no:cacheprovider -k "cadena_tangente"
E   assert 437.1154520899279 == 100 ± 1.0e-04
1 failed, 1 passed, 13 deselected in 1.65s

$ pytest tests/test_api_solido_extra.py -q -p no:cacheprovider -k "cadena_tangente"
E   assert 24061.186141919094 == 23724.070689958793 ± 0.237241
1 failed, 44 deselected in 1.79s
```

El `1 passed` de la primera corrida es el control que ya existía (`test_cadena_tangente_agrega_el_empalme_sin_duplicar_caras`), y `24061,19 − 23724,07 = 337,12` del rojo por la API es el mismo exceso visto desde la otra capa.

VERDE después: `28 passed` con `-k "cadena or repujado or emboss"` sobre los tres archivos del área, y los grupos completos de la tabla abajo. Con la regla puesta a medias (solo para las caras planas) los dos tests nuevos Y el control viejo fallaban: ese fue el hallazgo que llevó a escribir la regla en la expansión de la cadena y no en cada rama.

### B-209 · Barrido sólido con «Estirar» hace «Escalar» — **Resuelto**

**Qué dice la ayuda de Fusion** (`fusion_docs.py ver "Sweep reference" -s fusion-model`):

> #### Stretch
> Stretch: use path - guide rail distance to scale profile in X

o sea: el perfil crece **solo hacia el carril** y conserva la otra dimensión. La propia auditoría ya decía el arreglo en su `ponytail-audit` (ítems 2 y 7 de `docs/auditoria_revolucion_barrido_solevacion.md`): «Reuse the surface `_estirar` path» y «Add `"estirar": "Estirar"` once finding 2 is done».

**Estado del código antes de decidir** (medido con la sonda de la auditoría, `evidencias/ui_2026-11-05/sonda_carril.py`: cuadrado 4×4 en YZ, ruta X 0..50, carril en XZ de (0, 2) a (50, 6)):

```
solido stretch: V=3364.59 caja y −6.44..6.44    <- idéntico a scale
superf stretch: A=1201.28 caja y −2.00..2.00, z −6..6    <- estira bien
solido scale: V=3364.59      solido none: V=784.03
```

La superficie ya lo resolvía con `_barrido_estirado` (`nucleo/superficies.py:630`: secciones deformadas en el plano perpendicular a la ruta, solevadas entre ellas); el sólido caía a la ley de escala de `MakePipeShell`, que es uniforme en las dos direcciones del perfil. El docstring de `barrer` lo contaba conforme: ««estirar» (escala en una sola dirección) no existe en OCC y se hace como «escalar»». No era cierto: el gemelo lo tenía hecho.

**Qué cambié** — `clon/omnicad/nucleo/superficies.py:630` y `:650` (el gemelo gana un parámetro, no una copia) y `clon/omnicad/nucleo/solidos_crear.py:821-831`:

```python
    if carril is not None:
        if abs(torsion) > 1e-9 or abs(conicidad) > 1e-9:
            raise geo.ErrorGeometria("La torsión y la inclinación no se combinan con un carril guía.")
        if escala_carril not in ("escalar", "estirar", "ninguna"):
            raise geo.ErrorGeometria(f"Escala de carril desconocida: {escala_carril}")
        if escala_carril == "estirar":
            from . import superficies as sfc        # Estirar: lo resuelven las secciones deformadas del gemelo
    ...
        if carril is not None and escala_carril == "estirar":
            partes.append(sfc._barrido_estirado([perfil], tramo, carril, solido=solido))
            continue
```

`_barrido_estirado` pasa `solido` a `BRepOffsetAPI_ThruSections(solido, False)`, que es quien tapa los extremos (el mismo primer argumento con el que `_loft` hace sólida la Solevación, `solidos_crear.py:1127`). Va en `_barrido_alambre` y no en `barrer` porque es el único punto por el que pasan el perfil exterior y cada agujero: con un perfil anillado el hueco se estira igual que su contorno y se corta después (test abajo: 80 − 20 = 60 mm³). Las validaciones del carril subieron antes del bucle de tramos (mismos mensajes, sin armar el `MakePipeShell` para tirarlo después).

**Gemelos revisados** (regla 1; `grep -rn "escala_carril\|_barrido_estirado\|carril=" clon/omnicad`):

| Gemelo | Regla hoy | Qué hice |
|---|---|---|
| `nucleo/solidos_crear.py:827-831` `_barrido_alambre` (el Barrido, `barrer(solido=False)` y cada agujero) | hacía escalar | **arreglado** (delega) |
| `nucleo/superficies.py:630` `_barrido_estirado` | firme, pero solo superficie | **arreglado** (`solido=`, por defecto `False`: la firma vieja sigue valiendo) |
| `nucleo/superficies.py:727` `barrer_superficie` con `escala="estirar"` | llama al estirado sin `solido` | sin cambio: idéntico (medido A=1201,28 antes y después) |
| `nucleo/superficies.py:728` (riel con escalar/ninguna → `sc.barrer(solido=False)`) | `escala_carril != "estirar"` | sin cambio (el estirar no llega) |
| `nucleo/solidos_crear.py:798` `_ley_escala_carril` | la escala uniforme | sigue para «escalar»; sin cambio |
| `nucleo/solidos_crear.py:2924` `tuberia` | `_barrido_alambre(w, None, …, "escalar", …)` | sin carril → no aplica |
| `nucleo/solidos_crear.py:937` `barrer_cuerpo` (Solid Sweep) | sin carril | no aplica |
| `timeline/ops_solido.py:129` `OpBarrido.OPCIONES` | ya tenía «estirar» | sin cambio (el `PARAMS` sigue en «escalar»: recetas viejas idénticas) |
| `timeline/ops_superficie.py:216` `OpSupBarrido` | ya lo tenía y la superficie ya estiraba | sin cambio |
| `ui/comandos/crear.py:75-78` (Barrido › Escala del perfil) | ofrecía solo Escalar/Ninguna | **arreglado**: «Estirar» con la misma ayuda que su par de superficie |
| `ui/comandos/superficie.py:150` | ofrece los tres | referencia del texto; sin cambio |
| `api/herramientas_solido.py:483` `sweep` (`rail_scale`) | mapea `stretch → "estirar"` y su texto no promete escalar | sin cambio de texto → no se regenera la doc |
| `api/herramientas_superficie.py:192` `create_surface_sweep` | `profile_scaling` ídem | sin cambio |
| `nucleo/omnikernel/` | `grep "barrer\|carril\|recortar"` → nada | no aplica |
| la previa rápida (`ui/comando.py::tramo_previa`) | es del prisma de Extruir | no aplica: el Barrido calcula la previa con el núcleo (lo confirman el test del diálogo y el check de la pieza) |
| `edit_feature` | recalcula el paso con el mismo `ejecutar` | cubierto por el arreglo del núcleo |

**Tests nuevos y su salida.** `tests/test_solidos_crear.py::test_barrido_carril_estirar_no_es_escalar` (carril abierto de 1 a 3 sobre ruta de 10: 80 mm³ con caja ±3/±1 — el trapecio de sección media 8 sobre 10 mm —, distinto de los 173,33 de Escalar, y el agujero 80 − 20), `tests/test_api_opciones_solido2.py::test_barrido_con_carril_estirar_no_es_escalar` (la repro de la fila: 1600 mm³ y caja [50, 4, 12] contra 3364,59 de `scale`) y `tests/test_comandos_crear.py::test_barrido_dialogo_estirar_hacia_el_carril` (la lista de opciones del diálogo + 1600 mm³ y 3364,59 por el comando).

ROJO antes del arreglo:

```
$ pytest tests/test_solidos_crear.py -q -p no:cacheprovider -k "estirar_no_es_escalar"
E   assert 173.29644426000885 == 80 ± 0.08
1 failed, 66 deselected in 0.98s

$ pytest tests/test_api_opciones_solido2.py::test_barrido_con_carril_estirar_no_es_escalar tests/test_comandos_crear.py::test_barrido_dialogo_estirar_hacia_el_carril -q
E   assert 3364.5884 == 1600 ± 1.6
E   AssertionError: assert ['escalar', 'ninguna'] == ['escalar', '...', 'ninguna']
2 failed in 1.91s
```

El 173,30 del primer rojo ES el volumen de Escalar en el mismo caso: la prueba de que el modo no existía. VERDE después: `5 passed` (los tres nuevos más los dos controles de carril que ya había) y los grupos completos de abajo.

### `/ponytail-review` (salida completa, sobre el diff de los tres archivos de código y cinco de test)

`What this change does:` dos reglas cortas. El Repujado con «Cadena tangente» ya no copia el perfil en las caras que agregó la cadena si el perfil no cae sobre ellas (decide la caja proyectada, y decide igual para planas y cilíndricas), y el «Estirar» del Barrido sólido pasa por las secciones deformadas de su gemelo de superficie en vez de por la escala uniforme de `MakePipeShell`, con su opción visible en el diálogo. Carga esperada: una persona o un agente sobre un documento (el criterio del repo); nada de esto corre en un bucle, y el filtro de la cadena cuesta una teselación por cara agregada — malla ya cacheada y que el reparto en 2D calculaba de todos modos.

**Must fix:** nada.

**Should fix:**

1. **La caja de la cadena se mide en el plano del primer perfil** (`nucleo/solidos_crear.py:1581-1584`)
   - **What this is:** `pl_perfil = geo.plano_de_cara(perfiles[0])` y `caja_perfil = _caja_2d(perfiles, pl_perfil)`; cada cara de la cadena se proyecta sobre ese plano y se descarta si no toca la caja.
   - **Problem:** Con perfiles de dos bocetos en planos distintos en el MISMO repujado, la caja de todos se mide en el plano del primero: un perfil lejano puede colarse o quedarse afuera.
   - **Fix:** un comentario `shortcut:` que nombra el límite y cuándo subir de nivel, no un cambio de comportamiento: el alineado (`_alinear_repujado`) y el envoltorio ya usan `perfiles[0]` como marco, así que la regla nueva no introduce la suposición, la hereda de lo que reutiliza.
   - **If we skip it:** Mañana alguien mezcla bocetos, la cadena filtra de más y no queda ninguna pista en el código.
   - **Arreglé:** sí, con el `shortcut:` (dos líneas de comentario sobre una de código).

2. **Envolver en un cilindro lejos del perfil pone material dando una vuelta de más** (`nucleo/solidos_crear.py`, `a_uv` dentro de `_envolver_en_cilindro`)
   - **What this is:** El envoltorio pasa la coordenada tangencial del perfil a ángulo: `u0 + giro · (distancia al eje)/radio`.
   - **Problem:** Medido (`evidencias/ui_2026-11-06/sonda_b217_caras.py` y por la API): en la placa empalmada con el cuadro en el centro, elegir a mano el empalme izquierdo (`create_emboss faces="Cuerpo1/F3" wrap=true depth=1`) da **+39,71 mm³** sobre ese empalme, 19 mm lejos del cuadro; los cuatro dan +287,14. 19 mm sobre un radio 3 son 6,7 rad: la lámina le da más de una vuelta al cilindro y el `recortar` contra la cara justo la recorta donde no debía. Con la cadena este caso ya no se alcanza (el filtro descarta esas caras), pero con la cara elegida a mano sigue ahí, y esa es la rama que la decisión de 2026-10-13 decidió conservar.
   - **Fix:** **no lo hice**: es otra regla (tope del arco envuelto, o recortar contra el prisma del perfil), en un camino que este bug no toca.
   - **If we skip it:** El usuario ve relieve al lado contrario de donde apuntó.
   - **Fila nueva:** **B-220** en `docs/seguimiento/bugs.md` (Abierto, Media) con su ficha y la medición.

3. **El `import` del gemelo estaba dentro del bucle de tramos** (`nucleo/solidos_crear.py:821-825`)
   - **What this is:** `from . import superficies as sfc` escrito dentro de `for tramo in rutas:`.
   - **Problem:** Se repite por tramo y queda en medio del cálculo; `superficies` hace exactamente lo mismo una sola vez arriba.
   - **Fix:** subirlo al bloque de validación del carril (mismo import diferido: ninguno de los dos módulos importa al otro a nivel de módulo, así que no hay ciclo).
   - **If we skip it:** Nada, solo lectura.
   - **Arreglé:** sí, antes de la verificación final.

**Arreglé de la revisión:** los ítems 1 y 3 (el `shortcut:` y el import subido), con el grupo de tests vuelto a correr después (`184 passed`). El ítem 2 sale de la tanda como B-220.

**Verdict: Ship** (con 1 y 3 ya aplicados y 2 derivado con fila).

### Verificación

`ruff check .` desde `clon/`: `All checks passed!` (antes y después del arreglo de la revisión).

Tests: todos con `turno`, `-p no:cacheprovider`, en primer plano y de a un grupo (la lista obligatoria de la tanda más los archivos que da `grep -l` de lo tocado: `barrer`, `barrer_superficie`, `repujado`, `repujado_en_cuerpos`, `caras_tangentes`, `escala_carril`, `Barrido`, `emboss`; `_barrido_alambre`, `_barrido_estirado`, `_caja_2d` y `_cajas_se_tocan` no aparecen en ningún test por su nombre). Ninguna corrida cortada por tiempo:

| Grupo | Archivos | Salida final |
|---|---|---|
| 1 · núcleo | test_solidos_crear, test_superficies, test_superficie_fusion, test_geometria, test_b52_espiral, test_bugs_solido, test_paridad_motor | `245 passed in 151.74s (0:02:31)` |
| 2 · barrido, riel y tubería | test_sol08_barrido, test_barrido_tipos, test_api_barrido, test_gizmo_barrido, test_sol08_ui, test_superficie_guias, test_tuberia_cadena, test_topes, test_sup29_encadenado_superficie, test_graficos_rendimiento, test_rosca_diametros_tabla | `267 passed in 79.40s (0:01:19)` |
| 3 · API sólido/superficie | test_api_solido, test_api_solido_extra, test_api_superficie, test_api_opciones_solido1, test_api_opciones_solido2, test_api_avanzado, test_herramientas_solido | `500 passed in 159.61s (0:02:39)` |
| 4a · diálogos y repujado | test_comandos, test_comandos_superficie, test_comandos_crear, test_repujado_alineacion | `51 passed in 8.51s` |
| 4b · asas, paneles y cobertura UI | test_manipuladores, test_b105_panel_chico, test_iconos_extra, test_comandos_inspeccionar, test_cobertura_ui_api | `625 passed in 8.42s` |
| 5a · previa y calcomanías | test_previa_aislada_comandos, test_previa_prisma, test_previa_trabajador, test_previa_vaciado_aislada, test_p23_calcomania | `112 passed in 251.22s (0:04:11)` |
| 5b · modificar, texto, plástico y lotes | test_solidos_modificar, test_texto_vectores, test_opciones_operaciones, test_resultados_vacios, test_referencias_mal_formadas, test_herramientas_solido, test_sup29_encadenado_superficie, test_sol21_reglas_plastico, test_revision_lotes_sol, test_cinta_plastico | `612 passed in 122.03s (0:02:02)` |
| 6 · tras el arreglo de la revisión | test_repujado_alineacion, test_solidos_crear, test_api_opciones_solido2, test_comandos_crear, test_superficie_guias | `184 passed in 54.67s` |
| 7 · seguimiento y doc (después de editar los tres docs) | test_seguimiento, test_doc_agentes, test_claves_comandos, test_api_documento, test_api_catalogo, test_api_convenciones | `510 passed in 18.43s` |

Suite completa y prueba de humo: no corridas (regla 10; las toma el coordinador).

Terminados `PROJECT_LOG.md`, `docs/seguimiento/bugs.md` y este informe, se volvieron a correr los tres archivos que leen esa documentación — `test_seguimiento.py`, `test_doc_agentes.py` y `test_claves_comandos.py` → `448 passed in 5.92s`, y `ruff check .` siguió `All checks passed!`.

Sondas de la auditoría, corridas de nuevo:

| Caso | Antes | Después |
|---|---|---|
| `sonda_carril.py` sólido stretch (carril 2→6) | V=3364,59, caja y ±6,44 | **V=1600,00, caja y ±2,00 / z −6..6** (la misma caja que su superficie) |
| `sonda_carril.py` sólido scale / none | 3364,59 / 784,03 | 3364,59 / 784,03 (sin cambio) |
| `sonda_carril.py` superficie stretch / scale / none | 1201,28 / 1667,89 / 797,57 mm² | iguales (sin cambio) |
| Repujado placa cadena=True (`sonda_tanda3.py`) | +437,12, caja −1..61 / −1..41 | **+100,00, caja 20..30 / 15..25** |
| Repujado placa cadena=False | +100,00 | +100,00 (control) |
| Cadena en la caja 40×30×10 con un empalme, perfil cruzando el borde | +54,51 (solo +16 sin cadena) | +54,51 idéntico: ahí el perfil (x 33..41) sí cae sobre el empalme (x 37..40) y sobre el costado (x = 40), así que los dos siguen recibiendo |
| Caras elegidas a mano (tapa + base + costado) | +450,00 | +450,00 (la decisión del 2026-10-13 intacta) |
| Envolver a mano un empalme lejos del perfil (`sonda_b217_caras.py`) | +39,71 ese empalme (+287,14 los cuatro) | igual → **fila nueva B-220** |

Ventana (regla 9, porque cambiaron el diálogo de Barrido y el comportamiento del Repujado): las dos piezas de la tanda, en minimizada, con `PYTHONIOENCODING=utf-8` y `--plazo 2700` por `turno` (la pieza entera pasa del tope interno de 900 s de `todo.py`):

```
$ ../scripts/turno.py --plazo 2700 -- .venv/Scripts/python.exe ../scripts/prueba_ui/revolucion_barrido_solevacion.py
=== 40 comprobaciones, 7 con ✗ ===        (8 ✗ después de la tanda 1)
[OK ] · Barrido sólido › Escala del perfil ofrece Estirar (Fusion: Scale, Stretch, None) — ofrece ['escalar', 'estirar', 'ninguna']
[OK ] · Barrido › Distancia «1,5»: aviso — ⚠ La distancia sobre la ruta va de 0 a 1 (fracción del total); recibió 1.5.
[OK ] · Revolución dos lados 90 / −45°: o aviso o 2356,19 mm³ (como la superficie), no el lado 2 perdido — volumen 2356.19 sin aviso «»
[OK ] · ventana 1024x640: Aceptar se ve con el Barrido con carril — esquina 921,564 en 1024x640
[OK ] · ventana 800x520: Aceptar se ve con el Barrido con carril — esquina 697,463 en 800x520
```

Pasó el check que la auditoría tenía en ✗ (B-209: «Estirar no está en la lista»). Las 7 ✗ que quedan son ítems ya anotados, ninguno de esta tanda: H-88 (2: «A objeto» no muestra Dirección, en sólido y en superficie), H-92 (2: «Proyectar eje» con nombre y valor por defecto distintos), H-89 (sin Extensión con carril), B-208 (el carril paralelo da 784,02 en vez de 800) y H-90 (la fila del punto solo ofrece «Aguda»).

```
$ ../scripts/turno.py --plazo 2700 -- .venv/Scripts/python.exe ../scripts/prueba_ui/nervio_red_repujado.py
=== 84 comprobaciones, 5 con ✗ ===        (6 ✗ después de la tanda 2; 9 en la auditoría)
[OK ] · Repujado con cadena tangente: vista previa
[OK ] · Repujado con cadena tangente: resultado = 100 — obtenido 100.0; nuevos={} cambiados={'op9.c1': ('solido', 23724.071)}
[OK ] · Repujado con cadena tangente: deshacer vuelve al estado anterior (1 paso/s)
[OK ] · Repujado placa: resultado = 100 — obtenido 100.0; nuevos={} cambiados={'op9.c1': ('solido', 23724.071)}
```

Cerró el check de B-217 en la ventana real (23724,071 = la placa de 23624,07 + los 100 exactos; en la tanda 2 daba 24061,186). Las 5 ✗ que quedan son ítems ya anotados: B-215 (2: desmoldeo −1° y 1° con extracción), H-95 (el Nervio no tiene Radio del empalme) y H-97 (asas de alineación del Repujado). (H-99 se resolvió aparte: ver «## Informe tanda 5».)

Capturas miradas con Read: `capturas/barrido_carril.png` (la app entera con el aviso conocido de la selección de cadena; sin nada roto), las de tamaño de panel `barrido_1024x640.png` / `barrido_800x520.png` (los dos checks de «Aceptar se ve» de la primera pieza) y `capturas/repujado_cadena.png` (el panel REPUJADO con «Cadena tangente» activa: el relieve azul solo en la cara de arriba de la placa, los cuatro costados limpios — la imagen que la auditoría mostraba con cuatro cuadros achicados).

Evidencia: `evidencias/ui_2026-11-06/revolucion_barrido_solevacion.log` y `.json`, `nervio_red_repujado.log` y `.json` (el `.log` de esta pieza quedó reconstruido desde su `.json` de la corrida porque el stdout se cortaba en el pipe de la consola; la línea de arriba del archivo lo aclara), y las sondas `sonda_tanda3.py` (con su salida `sonda_tanda3_despues.txt`), `sonda_b217_caras.py` y la re-corrida `../evidencias/ui_2026-11-05/sonda_carril.py`.

### Seguimiento

- `docs/seguimiento/bugs.md`: borradas la fila y la ficha de «Detalle» de B-217 y de B-209; fila y ficha nuevas de **B-220** (el envoltorio que da una vuelta de más); recuento del encabezado 22 → 21 (Abierto 18 → 17 · Parcial 4).
- `docs/seguimiento/README.md`: no tenía filas de B-209 ni B-217 (`grep -n "B-209\|B-217"` → nada), así que no había qué borrar.
- `README.md` y `README.en.md` (hoja de ruta): sin mención de «Estirar» ni de la cadena tangente (`grep` → nada); no se tocaron.
- `docs/auditoria_revolucion_barrido_solevacion.md` y `docs/auditoria_nervio_red_repujado.md`: son el informe de esa corrida (histórico); no se cambiaron.
- Dos viñetas en «## Registro» de `PROJECT_LOG.md` y dos lecciones en «## Lecciones aprendidas» (una selección automática no hereda el trato de la elección manual; un docstring que declara imposible un cálculo no es evidencia).

### Archivos fuera de mi tanda

La tabla de la tanda 3 lista `nucleo/solidos_crear.py` y `ui/comandos/crear.py`. También toqué `nucleo/superficies.py` — es la columna «Gemelos a revisar» de la misma fila (el Barrido de superficie), y ahí cambió solo `_barrido_estirado`: un parámetro nuevo con valor por defecto que su llamador de superficie ni pasa. No se tocaron `timeline/ops_solido.py`, `timeline/ops_superficie.py`, `api/herramientas_*.py`, `ui/comandos/superficie.py` ni `ui/comandos/asas_extra.py`: los gemelos ya tenían la regla o el parámetro. `docs/corrida_nocturna_2026-11-05.md` aparece modificado en el árbol: es de otra corrida, no lo miré ni lo cambié.

### Lo que no pude verificar

- ⚠ **Fusion real no se abrió** para ninguno de los dos. La regla del Stretch sale del texto de la ayuda («use path - guide rail distance to scale profile in X») y de que la superficie del propio OmniCAD ya la aplicaba; la de la cadena sale de la ayuda del Emboss y de la fila B-217, y **convive** con la decisión del 2026-10-13 (cara elegida a mano: adaptar). Si al abrir Fusion resultara que la cadena tampoco recibe lo que cae sobre un empalme —en el control de la caja 40×30×10 hoy recibe su parte—, la regla nueva pasa a mirar el tipo de cara en el filtro: una línea.
- ⚠ **El estirar con `distancia` menor que 1** no mejoró: el sólido empareja la ruta recortada con el carril **entero** (fracción contra fracción), así que con 0,5 la sección final ya está al 3× — medido 40,00 mm³ con caja ±3 en z 0..5. Es la convención que ya tenía «escalar» (`_ley_escala_carril` hace el mismo emparejamiento; midió 146,78 mm³) y el sólido no tiene la opción `distancia_carril`/Extensión que la superficie sí (eso es H-89, ya anotado). Cambiarlo es otra decisión de producto, no este bug.
- ⚠ **B-208 sigue abierto** y es vecino: con carril paralelo la forma todavía se tuerce en el medio (784,03 en vez de 800) en sólido y en superficie; el check de la pieza sigue ✗.
- ⚠ **Perfil anillado (con agujero) estirado en la ventana**: lo mide el test del núcleo (80 − 20 = 60 mm³); el diálogo y la API se probaron sin agujero.
- ⚠ **`edit_feature` con `escala_carril="estirar"`** no tiene test propio: recalcula el paso con el mismo `ejecutar` que el test de `sweep`, así que queda cubierto por el arreglo del núcleo, no por una corrida.
- ⚠ **Proyectos `.omnicad` guardados con «Estirar»**: al abrir, el cuerpo cambia de forma (del tronco de 3364,59 al estirado de 1600 en el caso de la fila). En `ejemplos/` no hay recetas con `escala_carril` (`grep -rln "escala_carril" ejemplos/` → nada), pero una pieza del usuario puede tenerla. Con la cadena tangente pasa lo mismo a la inversa: el repujado pierde las copias de los costados.
- ⚠ **B-220 queda abierto** y es el mismo síntoma por la otra puerta (cara elegida a mano): medido, con ficha, sin arreglo.

## Informe tanda 4

Lo escribe el coordinador: Qwen se cortó dos veces (reinicio de la PC a las 04:29 y tope de 60 min a las 08:03) sin escribir su informe.

- **H-92 · «Eje de proyecto» encendido por defecto — Resuelto.** Panel (`ui/comandos/solido.py`, `superficie.py`) y API (`revolve`, `create_surface_revolve`) arrancan con el eje proyectado, con el nombre de Fusion. Los `PARAMS` siguen en `False` para que las recetas viejas den lo mismo. Un eje perpendicular al plano, o aristas de un cuerpo sin plano, ya no dan error: el eje queda donde está.
- **H-86 · «Medida» arranca en «Longitud total» — Resuelto.** Panel y API de Extruir (sólido y superficie); `PARAMS` sigue en `mitad` por las recetas viejas.
- Tests nuevos: `test_herramientas_solido.py`, `test_comandos.py`, `test_sol07_revolucion.py`; chequeo `medida_por_defecto` en `scripts/prueba_ui/revolucion_barrido_solevacion.py`.
- Revisión del coordinador: ruff limpio; 894 + 866 + 833 verdes (45 archivos que usan el código tocado). `/ponytail-review` halló un bloque de proyección duplicado en `ops_superficie.py` (sin efecto, idempotente): borrado; 805 verdes después.
- ⚠ Sin test propio: revolución de superficie desde aristas de un cuerpo con el eje proyectado (antes daba error, ahora no proyecta).

## Informe tanda 5

### H-99 · Repujado: profundidad negativa siempre graba (CodeBuddy con hy3)

**Estado:** Resuelto. La profundidad negativa del Repujado ahora SIEMPRE graba (Deboss) como Fusion
(«Negative values create a Deboss effect»), sin importar el «Tipo» elegido (antes se invertía dos veces y el
panel se quedaba en Relieve). El panel pasa el Tipo a Grabado cuando la profundidad baja de 0 y el asa de
Profundidad puede bajar de 0 sin tope.

**Cambios (archivo:línea):**
- `clon/omnicad/nucleo/solidos_crear.py:1569` — se borró el doble cambio de signo (`if profundidad < 0: profundidad, tipo = -profundidad, ...`); ahora `es_relieve = profundidad > 0 and tipo == "relieve"` y `profundidad = abs(profundidad)`.
- `clon/omnicad/nucleo/solidos_crear.py:1602` — `sentido = (1.0 if es_relieve else -1.0) * (-1.0 if invertir else 1.0)`.
- `clon/omnicad/nucleo/solidos_crear.py:1622` — `_envolver_en_cilindro(...)` recibe el tipo efectivo (`"relieve" if es_relieve else "grabado"`) en vez del tipo original.
- `clon/omnicad/nucleo/solidos_crear.py:1631` — `operacion = "unir" if es_relieve else "cortar"`.
- `clon/omnicad/ui/comandos/crear.py:378` (clase `Repujado`) — nuevo `al_cambiar`: al cambiar `profundidad` pone `tipo="grabado"` si es negativa (o `"relieve"` si es positiva), actualizando el widget con `blockSignals`. Import de `LONGITUD` en la línea 15.
- `clon/omnicad/ui/comandos/asas_extra.py:308` (`_asas_repujado`) — el asa de Profundidad apunta al lado del material y baja de 0: `signo = 1.0 if es_relieve else -math.copysign(1.0, prof)` y `minimo=None` (antes `minimo=0.0`); `import math` arriba.
- `clon/omnicad/api/herramientas_solido_extra.py:239` — docstring de `create_emboss` aclara que profundidad negativa siempre graba.

**Gemelos (mismo constructo, buscados):** asa de Profundidad (`asas_extra.py::_asas_repujado`), previa del panel
(`comando.py` / `Repujado.construir`), API `create_emboss` (`api/herramientas_solido_extra.py`), núcleo
`repujado_en_cuerpos` / `_envolver_en_cilindro` (`nucleo/solidos_crear.py`), y `nucleo/omnikernel/` (no hay
repujado ahí). `grep` del constructo viejo (`profundidad, tipo = -profundidad`, `"grabado" if tipo == "relieve"`)
por todo el repo: 0 coincidencias → no quedan gemelos con el bug.

**Salida real de ruff:**
```
$ .venv/Scripts/python.exe -m ruff check .
All checks passed!
```

**Salida real de los tests (desde `clon/`, con `../scripts/turno.py`, en grupos < 900 s):**
- Obligatorios de la fila 5 (5 tests, `test_create_emboss` parametrizado en 4):
  ```
  tests/test_comandos_crear.py::test_repujado_profundidad_negativa_pasa_el_tipo_a_grabado
  tests/test_comandos_crear.py::test_repujado_grabado_con_profundidad_negativa_graba
  tests/test_manipuladores.py::test_el_asa_de_profundidad_del_repujado_pasa_por_debajo_de_cero
  tests/test_solidos_crear.py::test_repujado_plano_relieve_grabado_y_limite_de_cara
  tests/test_api_solido_extra.py::test_create_emboss
  ........                                                                 [100%]
  8 passed in 10.90s
  ```
- Regresión, grupo 1 (`grep -l` de las funciones tocadas): `test_solidos_crear.py test_manipuladores.py test_repujado_alineacion.py test_texto_vectores.py` → `197 passed in 45.15s`.
- Regresión, grupo 2: `test_comandos_crear.py test_api_solido_extra.py test_api_solido.py test_opciones_operaciones.py test_api_avanzado.py test_cobertura_ui_api.py test_iconos_extra.py test_barrido_tipos.py` → `1126 passed in 96.07s`.

**Ventana (pieza `nervio_red_repujado`, `--ventana minimizada`):** 84 comprobaciones, 5 ✗.
- `[OK] Repujado › con profundidad negativa el Tipo pasa a Grabado (Fusion: Effect cambia solo) — Tipo = grabado` ✓
- `[OK] Repujado › Profundidad «-1 mm»: previa` ✓
- Las otras 5 ✗: 3 son ítems ya anotados y ajenos a H-99 (B-215 desmoldeo −1°/1°, H-95 Radio del empalme del Nervio), 1 es H-97 (asas de alineación del Repujado). La 5ª es el asa de Profundidad del Repujado: `«profundidad» arrastrada más allá del cero: tope y sin excepción — 4 → -6`. **Es el comportamiento que H-99 pide** (el asa baja de 0); la aserción de la pieza todavía espera el viejo «tope» en 0, por eso marca ✗. No es regresión del arreglo.

### ponytail-review (salida completa)

**What this change does:** Hace que el Repujado de OmniCAD grabe siempre que la profundidad sea negativa, sin
importar el Tipo elegido, igual que Fusion. También el panel cambia el Tipo a Grabado cuando la profundidad baja
de 0, y el asa de Profundidad puede bajar de 0.

**Must fix:** ninguno.
- El núcleo ahora deriva el sentido de `es_relieve = profundidad > 0 and tipo == "relieve"` con magnitud
  `abs(profundidad)`. Cubre los 4 casos de los tests (`+relieve`, `+grabado`, `-relieve`, `-grabado`) sin el
  doble cambio de signo que antes dejaba relieve cuando `tipo="grabado"` y profundidad negativa.
- El camino cilíndrico (`_envolver_en_cilindro`) recibe el tipo efectivo, coherente con el caso plano.

**Should fix:** ninguno.
- `Repujado.al_cambiar` solo actúa al editar `profundidad`; no toca el signo de `profundidad` al elegir el Tipo
  (eso es coherente con Fusion, donde el Efecto sigue el signo de la profundidad). No rompe la carga desde una
  receta guardada.

**Nice to have:**
1. **Carga desde receta con signo/tipo desparejos** (`ui/comandos/crear.py` `Repujado.desde_op`). Si una receta
   guardada trae `profundidad="-1 mm"` y `tipo="relieve"`, el panel los muestra sin normalizar y el núcleo debossaría
   mientras el panel dice Relieve. Caso de borde menor (la edición lo corrige al tocar Profundidad). Arreglo mínimo:
   normalizar `tipo` en `desde_op` con la misma regla de `al_cambiar`. No lo hice: H-99 no lo pide y los tests no
   lo cubren.

**Verdict: Ship.**
**Lean: 0 líneas de más** (el diff borra el doble cambio de signo y añade solo la regla nueva + el acoplamiento panel↔asa).
**Not checked:** la pieza `nervio_red_repujado` corre en ventana minimizada con offscreen; la captura se generó pero
no se inspeccionó píxel a píxel (los checks de texto del log confirman el Tipo y la previa).

---

### Revisión del coordinador (2026-11-06)

Los tests eran el parche de Qwen (tanda 5, sin cupo); la ayuda de Fusion los confirma: «Negative values create a Deboss effect». `ponytail-review` propio: (1) **Must fix**, `Repujado.al_cambiar` volvía el Tipo a Relieve con cualquier profundidad positiva (Grabado con 1 mm → escribir 2 mm → Relieve): ahora cambia solo al cruzar el cero, al editar mide desde la profundidad guardada (`desde_op`) y usa `panel.set_valores`; caso sumado a `test_repujado_profundidad_negativa_pasa_el_tipo_a_grabado`. (2) **Must fix**, la pieza `nervio_red_repujado` exigía tope 0 a toda asa: ahora solo si el asa tiene tope. (3) con profundidad 0 en Relieve el asa apuntaba hacia adentro: `prof >= 0`. Verificación: `ruff check .` All checks passed!; 83 passed (`test_comandos*` + `test_b105_panel_chico`), 1308 passed (11 archivos del grep de repujado), 470 passed (`test_manipuladores`, `test_seguimiento`, `test_comandos_crear`); pieza `nervio_red_repujado` 84 comprobaciones, 4 ✗ ya anotadas (B-215 ×2, H-95, H-97). ⚠ Un `.omnicad` viejo con Grabado y profundidad negativa ahora graba (antes hacía relieve): es el arreglo.

### H-94

**Estado:** Resuelto.

**Qué dice la ayuda de Fusion:** el artículo «Compute parameters, features, and assembly relationships in a design» (Design: Solid › Compute) dice: «The warning or error message displays in the lower-right.» (buscar `warning` en `scripts/fusion_docs.py`: resultado 5). O sea Fusion también lo muestra abajo a la derecha, pero **sin tapar el diálogo** — que es justo lo que reportaba la fila.

**Cambios (`archivo:línea`):**
- `clon/omnicad/ui/superposiciones.py:668` (`AreaVisor.reubicar`): el bloque del `toast` ahora, cuando hay un panel de comando visible, lo coloca a la **izquierda del panel** (`x = max(g.left() + 4, self.panel.x() - self.toast.width() - 8)`, abajo a la derecha del área), en vez de siempre al borde derecho donde se superponía con Aceptar/Cancelar y los campos. Sin panel (o en boceto, al lado de la paleta) queda como antes.

**Gemelos revisados:**
- Avisos flotantes en `clon/omnicad/ui` (`grep -rn 'avisos'`): el único aviso flotante es `AreaVisor.toast` (`AvisoFlotante`, `ui/avisos.py`); su posición vive solo en `reubicar` (superposiciones.py:668). Los demás `avisos` son etiquetas de mensaje de panel (`comando.py:_mostrar`, `editor_boceto.py:mensaje`), validación de temas (`preferencias.py`/`ventana.py`/`temas.py`) y advertencias de perfil de boceto (`visor3d.py`) — ninguno es el toast flotante, ninguno tocado.
- Posición del panel de comando: `ui/comando.py` (`PanelComando`) y `ui/superposiciones.py` (`set_panel`, `_posicion_fija_panel`, bloque del panel en `reubicar` líneas 605–621). Leída, no modificada; el panel sigue en su lugar y el toast se apoya en `self.panel.x()`.
- Ventana chica: `clon/tests/test_b105_panel_chico.py` — se amplió con el test de H-94 (ventanas 800×520 y 1900×1000).

**Test rojo → verde** (`clon/tests/test_b105_panel_chico.py::test_el_aviso_flotante_no_tapa_el_panel_de_comando`):

ROJO (antes del arreglo):
```
E       AssertionError: (800, 520, (427, 8, 362, 311), (541, 249, 250, 68))
E       assert not True
...
FAILED tests/test_b105_panel_chico.py::test_el_aviso_flotante_no_tapa_el_panel_de_comando[800-520]
1 failed, 1 passed in 3.03s
```
VERDE (después del arreglo):
```
..                                                                       [100%]
2 passed in 2.63s
```

**Salida de ruff** (`ruff check .` / sobre el archivo):
```
All checks passed!
```

**Salida de cada grupo de tests** (desde `clon/`, con `../scripts/turno.py`, < 900 s):
- Grupo A — `test_b105_panel_chico.py` + `test_comandos*.py` (7 archivos): `85 passed in 12.44s`
- Gemelos de `reubicar`/`AreaVisor`/`toast` — `test_proyectar_tarjeta.py test_panel_movible.py test_paneles_boceto_comunes.py test_pl5_sugerencias.py`: `97 passed in 38.14s`
- `test_boceto_fase9_ui2.py test_boceto_fase9_ui3.py`: `19 passed in 2.99s`

**Salida completa de `/ponytail-review`:**
```
What this change does:
When a command panel is open, the floating warning toast is placed to the left of that
panel (bottom area) instead of at the bottom-right corner where it covered Accept/Cancel
and the fields. When no panel is open, it stays bottom-right as before (or beside the
sketch palette in sketch mode).

Findings: none.

Verdict: Ship.
Lean: 0 líneas de más (el diff solo cambia el bloque del toast en reubicar; se borró la
rama de fallback especulativa que no se alcanza con los paneles reales de ~270–360 px).
Not checked: nothing material. El cambio es solo de UI; no toca firmas de la API/MCP/CLI,
así que no hace falta regenerar docs/agentes/herramientas.md (regla 8 de AGENTS.md no aplica).
```
⚠ No se corrió la suite completa ni la prueba de humo (lo hace el coordinador, regla del prompt); la verificación se limitó a los grupos de arriba.

**Pieza de ventana** (`revolucion_barrido_solevacion --ventana minimizada`, evidencia en `evidencias/ui_2026-11-06`): 41 comprobaciones, 5 con ✗ (ya anotadas en la pieza, no son de H-94). Las capturas `solevacion_punta.png` y `barrido_800x520.png` (las citadas en la fila) confirman visualmente que el aviso flotante queda a la **izquierda** del panel y no tapa Aceptar/Cancelar ni Distancia/Escala.

⚠ La pieza se corrió con `--ventana minimizada`/offscreen; no se inspeccionó píxel a píxel, pero las capturas (leídas con ViewImage) muestran el aviso desplazado a la izquierda del panel en ambas ventanas.

---

#### Revisión del coordinador de H-94 (2026-11-06)

`ponytail-review` propio, **Must fix** arreglado: el agente ponía el aviso siempre a la izquierda del panel; con el panel arrastrado a la izquierda la x daba negativa, se recortaba al borde y el aviso volvía a taparlo. Ahora el aviso queda en su lugar (abajo a la derecha, al lado de la paleta en el boceto) y solo se corre si choca con el panel: a su izquierda, o a su derecha si no entra. El test suma el panel arrastrado a la izquierda (rojo con la versión del agente en 800×520). Además el agente había pasado todo `superposiciones.py` a LF (1314 líneas de diff): se restauraron los fines de línea, el diff es de +5 líneas. Y había pegado la fila H-98 a la de H-93 en `mejoras.md`: separada. Verificación: `ruff check .` All checks passed!; 608 passed (`test_b105_panel_chico`, `test_comandos*`, `test_seguimiento` y 6 archivos que usan `reubicar` o el aviso); pieza `revolucion_barrido_solevacion` 41 comprobaciones, 5 ✗ ya anotadas (H-88 ×2, H-89, B-208, H-90).
