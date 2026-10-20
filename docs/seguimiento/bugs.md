# Bugs

Algo que falla, da un resultado malo o un mensaje engañoso. Método y columnas: [README](README.md).

Solo lo que falta resolver: al resolverse, la fila se borra. Verificado contra el código el 2026-10-20. Total 11: Abierto 3 · Parcial 8.

## Abiertos y parciales

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| P-12c | Fuente de novedades de Fusion (la ayuda es un shell JS sin titulares) | Abierto | Baja | Revisar a mano cada mes o cambiar la fuente. | PROJECT_LOG.md:33 | 2026-10-20 |
| P-1c | Wayland nativo: menús emergentes se cierran solos | Abierto | Alta | Con QT_QPA_PLATFORM=wayland se cierran el menú radial y «Seleccionar otro»; hoy se fuerza xcb. | omnicad/ui/__init__.py:11-19 | 2026-10-20 |
| P-11j | Cuerpos «sin ubicar» (2 del Sherpa, 3 de XOX) que Fusion no tiene | Abierto | Alta | Siguen entrando con aviso porque el flujo de diseño no se decodifica de forma confiable. | omnicad/io_archivos/f3d_nativo.py:123 (sin_ubicar); tests/test_p11a_f3d_instancias.py:176 | 2026-10-20 |
| B-71 | Uniones encadenadas: el lazo cerrado con uniones «como está» no se resuelve | Parcial | Media | Los lazos con una unión «como está» (el caso del gatoRL) siguen sin resolver y solo avisan; el lazo se acciona desde su primera unión. | omnicad/timeline/ops_ensamblar.py (_resolver_lazo, aviso «Lazo cerrado no resuelto»); tests/test_b71_cadena.py (lazos de uniones normales: biela-manivela, cuadrilátero, sin solución) | 2026-10-20 |
| B-80 | MCP incompleto: faltan herramientas de la cinta DISEÑO, el visor y opciones (ANIMACIÓN, DIBUJO y RENDERIZAR ya están) | Parcial | Alta | Faltan las olas 4 a 7 (filas MCP-n de faltantes.md): cinta DISEÑO sin herramienta o solo con run_operation, visor/paneles/preferencias, opciones de diálogo. | commit 3ae4f74; api/herramientas_animacion.py (15), herramientas_dibujo*.py (18) y herramientas_render.py (5); tests/test_api_animacion.py; tests/test_api_dibujo.py; tests/test_api_dibujo_notas.py; tests/test_api_dibujo_salida.py; tests/test_api_render.py; tests/test_cobertura_ui_api.py::test_hay_herramientas_de_dibujo_y_render | 2026-10-20 |
| B-39 | join con herramienta enterrada deja arista libre y cuerpo no estanco | Parcial | Muy alta | La arista libre sigue (defecto del kernel); solo se detecta y avisa. | timeline/operaciones.py:349 y :1004 (aviso post-unión) | 2026-10-20 |
| B-48 | Crash nativo OCCT (0xc0000005) al recalcular parámetros a 148 pasos | Parcial | Muy alta | Recálculo sigue en el proceso de la app; solo el autoguardado protege. | commit d706002; nucleo/aislado.py:98; tests/test_b48_crash.py::test_b48_un_crash_nativo_del_kernel_vuelve_como_error_y_no_mata_al_padre | 2026-10-20 |
| B-52 | Unión de espiral: fusión degenerada, pérdida silenciosa y STEP en dos sólidos | Parcial | Muy alta | La fusión degenerada del kernel sigue; solo se avisa la pérdida o el corte. | timeline/operaciones.py:336,986-1005; tests/test_documento.py::test_combinar_avisa_si_la_union_pierde_material; ::test_union_de_primitiva_avisa_si_pierde_material | 2026-10-20 |
| T-04 | shell hacia afuera falla en un solevado de caras B-spline | Parcial | Muy alta | Hacia adentro anda; hacia afuera el kernel no da una pared válida | tests/test_hallazgos_tortura.py::test_t04_vaciado_exterior_bspline_falla_con_alternativa_y_sin_modificar | 2026-10-20 |

## Detalle de lo abierto

Ficha original de cada bug abierto o parcial (del PROJECT_LOG al 2026-10-20); se borra junto con su fila. La tabla
de arriba manda sobre este texto.

### B-39 · join con herramienta enterrada deja arista libre y cuerpo no estanco

`boolean_operation join` con herramienta 100 % enterrada (cilindro r2,5 en la carcasa): suma 0 (correcto) pero deja una arista libre en (27, 0, 129,5); cuerpo no estanco. Determinista: sobrevive a recalcular todo. Solo se cura borrando los pasos.

`boolean_operation`

Corregido el 2026-10-14 por el mismo aviso post-join de cuerpo partido/no estanco. Repro de la arista queda sin cura (kernel)

Reproducido

Crítico

### B-48 · Crash nativo OCCT (0xc0000005) al recalcular parámetros a 148 pasos

**Mitigado 2026-10-20** (`agente/b48`): no se reprodujo en 18 min; la caída de un hijo aislado vuelve como `TareaAislada`. Sigue abierto. **Crash nativo durante la tortura de parámetros** (±30 % a 148 pasos): APPCRASH de `pythonw.exe`, excepción 0xc0000005 en `TKernel-….dll` (OCCT 8.0.1) offset 0x78bed, 09:11:23; el puente murió a mitad de llamada (`BRIDGE_ERROR WinError 10054`). El autoguardado (receta sin caché, 18 s antes) permitió recuperar todo. Evento completo en `crash2_evento_completo.txt`.

kernel OCCT vía cadquery_ocp; recálculo

Reproducido (firma de Windows): no se puede curar desde la app; queda la protección por autoguardado

Crítico

### B-52 · Unión de espiral: fusión degenerada, pérdida silenciosa y STEP en dos sólidos

La unión de la espiral de refrigeración (bobina cónica con 0,5 mm de incrustación contra la campana) es una **fusión degenerada**: Cuerpo1 queda NO estanco (1 arista libre + 18 no manifold); suprimir el chaflán del labio (op28, ajeno) hace perder la espiral en silencio (−3.118 mm³, sin error ni aviso; vuelve al reactivar, 2 ciclos); el bbox del cuerpo mezcla las cajas de sus carcasas (xy de la campana con z de la espiral, ocultando r44,5); y el STEP exportado entra como DOS sólidos (bloque 150.657,28 + espiral 3.495,73) que suman el volumen que el .omnicad reporta como uno. Familia B-37 (tangencias) en «join».

booleana `join` con contacto en cuña; `suppress_feature`; bbox multicáscara

Corregido el 2026-10-15 en la DETECCIÓN (la degeneración del kernel no se puede curar, familia B-37): OpCombinar no tenía NINGÚN chequeo post-unión (op121 nunca avisaba) y la espiral se perdía al unir DESPUÉS una primitiva (op48 Caja3) al cuerpo compuesto: la fusión descartaba el sólido de la espiral (−3.193,74 mm³, sólidos 2→1, estanca=True: invisible para el chequeo de estanqueidad). Ahora toda unión avisa si PIERDE material (con los mm³) y OpCombinar avisa si explota en sólidos, si no fusiona lo que se tocaba o si queda abierto; unir cuerpos que no se tocan (multi-sólido legítimo, como el aro+toroide del ejemplo) sigue sin avisar. En la copia del motor recalculada: op28 activo → op121 avisa «partido/sin fusionar»; op28 suprimido → op48 avisa «perdió 3193,74 mm³». Volúmenes bit-idénticos. Regresiones en test_documento (toque sin fusión, pérdida en Combinar y en primitiva)

Crítico

### B-71 · Uniones encadenadas: el lazo cerrado con uniones «como está» no se resuelve

Uniones «como esta» encadenadas: `drive_joint` sobre una union resuelve bien el componente directo, pero el componente atado via la union del codo no sigue (lazo sin resolver, herede la «SIN LAZOS CERRADOS» de la Prueba 4) Y, peor: los drives sucesivos volvieron `REFERENCE_LOST` las uniones U_apoyo_* hasta borrarlas. Refuerza B-65.

ensamble / `drive_joint` + uniones en cadena

Parcialmente corregido el 2026-10-14: los REFERENCE_LOST de las uniones de apoyo (B-65) quedan curados por el resolver invariante de referencias; la cadena abierta sigue al componente movido (commit c853fd4). Corregido el 2026-10-20 el LAZO CERRADO de uniones normales: la unión que cierra el lazo lo resuelve con least_squares sobre los giros y deslizamientos de las demás (la primera unión del lazo es la accionada); si no alcanza, el paso queda en error «Lazo cerrado sin solución» y `drive_joint` se revierte. Sigue abierto el lazo con uniones «como está» (solo avisa) y accionar el lazo desde una unión que no sea la primera

Reproducido en gatoRL (6 uniones)

Alto

### B-80 · MCP incompleto: faltan herramientas de la cinta DISEÑO, el visor y opciones (ANIMACIÓN, DIBUJO y RENDERIZAR ya están)

**Olas 1 a 3 hechas 2026-10-20**: requisitos MCP-0a a 0e, 15 herramientas de ANIMACIÓN (`agente/b80`), 18 de DIBUJO (hoja, vistas, cotas, anotaciones, exportar DXF/SVG/PDF y la hoja como imagen) y 5 de RENDERIZAR (entornos, escena, cámara guardada e imagen final); faltan las olas 4 a 7. Quedan sin herramienta 31 claves de la cinta y 54 solo funcionan por `run_operation` (38 de 95 tipos). Rompe la regla «MCP y CLI siempre completos» de `CLAUDE.md`. Visto al pedir que se animara el rotor del motor impreso: solo se pudo mover la unión con `drive_joint`, de a pasos de 2-3 s.

`api/` frente a `ui/animacion.py`, `ui/dibujo.py`, `ui/render.py`, `ui/cinta.py`

Reproducido. Plan en `docs/brechas_mcp.md` (MCP-0a a MCP-55)

alto
