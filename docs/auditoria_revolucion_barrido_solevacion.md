# Auditoría de Revolución, Barrido y Solevación en todos los espacios (2026-11-05)

Pedido de Gerardo (2026-11-05): la misma auditoría que se hizo con Extruir ([auditoria_extruir.md](auditoria_extruir.md)),
ahora con las herramientas Revolución, Barrido y Solevación: comparar con Fusion 360 y buscar bugs, mal funcionamiento y faltantes en SÓLIDO, SUPERFICIE,
PLÁSTICO, CHAPA, FORMA y donde más existan. Lo ejecuta una sesión aparte (Opus 5, esfuerzo alto). Tanda 1 de 2.
El prompt ya se cerró (2026-11-05).

## Resultado (2026-11-05)

Revolución, Barrido y Solevación andan bien en lo común: 78 casos por la API (53 dan el número de la cuenta a mano y
la mayoría de los 25 errores son los errores claros que corresponden) y 40 comprobaciones en la ventana. Se encontraron
**5 bugs** (B-208 a B-212), **4 faltantes** (H-88 a H-91, más H-83 ampliada a las tres herramientas) y **3 mejoras**
(H-92 a H-94). No se tocó código de la app. Evidencia en `evidencias/ui_2026-11-05/`: `sondas_rbs.py` y su salida
`sondas_rbs.txt`, `sonda_carril.py` / `.txt`, `sonda_carril_solevacion.py` / `.txt`, el registro
`revolucion_barrido_solevacion.json` / `.log` y las capturas `capturas/barrido_*.png` y `solevacion_punta.png`.

### Referencia de Fusion por herramienta y espacio

| Espacio de Fusion | Revolución | Barrido | Solevación | En OmniCAD |
|---|---|---|---|---|
| SÓLIDO | Sí: perfil, eje, Proyectar eje, Parcial / A objeto / Completo, Un lado / Dos lados / Simétrica, operación (`Revolve reference`) | Sí: Ruta individual, Ruta + Rail guía, Ruta + Superficie guía, Barrido sólido; Distancia 0-1, conicidad, torsión, Extensión, Escala (Escalar / Estirar / Ninguna), Orientación (`Sweep reference`) | Sí: perfiles en orden, condiciones Libre / Dirección / Tangente / Suave / Aguda / Punto tangente con pesos, Raíles o Línea central, Cerrado, Aristas tangentes (`Loft reference`) | `revolucion`, `barrido`, `solevacion` en CREAR |
| SUPERFICIE | Sí, más curvas sueltas y Chaining; solo Cuerpo o Componente nuevo (`Revolve a surface body`) | Sí, los tres tipos de ruta (`Sweep a surface body`) | Sí, más Continuidad G0/G1/G2 y alineación de bordes (`Loft reference (Surface)`) | `sup_revolucion`, `sup_barrido`, `sup_solevacion` |
| PLÁSTICO | El mismo menú CREAR de SÓLIDO | ídem | ídem | Los mismos tres botones (pieza: ✔) |
| CHAPA | No (índice `docs/fusion_docs/indice/fusion-sheet-metal.md`: ningún Revolve ni Sweep) | No | Solo «Lofted Flange» (`Lofted flange reference`) | Sin botones (bien); Pestaña solevada grisada: ya está como CHA-1 |
| FORMA (T-Splines) | Sí: Tipo, Espaciado, Soldar, Simetría circular (`Revolve a T-Spline body`) | Sí: caras, espaciado, orientación (`Sweep a profile along a path`) | Sí: espaciado y desvío (`Loft reference (Form)`) | No existe el espacio: ya está como P-25j |

Nota: la ayuda de Revolución no dice si el ángulo de «Simétrica» es el total o el de cada lado; OmniCAD reparte el
ángulo (90° simétrica = ±45°) en sólido, superficie y asa. ⚠ Sin abrir Fusion no se pudo confirmar.

### Matriz de opciones

Leyenda: ✔ igual que Fusion · ✘ falla o falta · ≈ parecido. «CLI» es el mismo catálogo que el MCP (`omnicad call`).

| Herramienta · opción (Fusion) | Ventana | MCP / CLI | Estado | Evidencia |
|---|---|---|---|---|
| REV · perfil de boceto, cara plana | ✔ | ✔ `profile`, `faces` | ✔ | 9424,78 = π(20²−10²)·10; cara: 2356,19 |
| REV · eje: eje de boceto, de origen, línea, de otro boceto | ✔ | ✔ | ✔ | eje en x=30: 9424,78, caja x 10..50 |
| REV · Proyectar eje | ≈ | ≈ | Mejora | H-92 (nombre «Eje de proyecto», valor por defecto distinto); proyectado y sin proyectar dan las cuentas (9424,78; sin proyectar, el anillo de radios 22,36 a 28,28) |
| REV · Parcial, ángulo (90, −90, «giro * 2», «1.5707963 rad») | ✔ | ✔ | ✔ | 2356,19 en todos; −90 va al otro lado |
| REV · ángulo 0, 400°, «10 mm» | ✔ error | ✔ error | ✔ | «no puede ser cero», «no puede pasar de 360°», UNIT_MISMATCH; la pieza `solido_crear` teclea los inválidos |
| REV · Completo | ✔ | ✔ | ✔ | 9424,78 |
| REV · Dos lados (90 + 45; sin ángulo 2) | ✔ | ✔ | ✔ | 3534,29; sin angle2 = igual al lado 1: 4712,39 |
| REV · Dos lados con un ángulo negativo | ✘ | ✘ | Bug | B-210: el sólido pierde el lado 2, la superficie toma el valor absoluto |
| REV · Simétrica | ✔ | ✔ | ≈ | 90° = ±45°, 2356,19; ⚠ criterio de Fusion sin confirmar |
| REV · Invertir | ✔ | ✔ `reverse` | ✔ | misma caja que −90 |
| REV · A objeto (plano, punto) | ✔ | ✔ `to_object` | ✔ | hasta YZ: 2356,19; hasta el punto (0, 0, 15): 270°, 7068,58 |
| REV · A objeto + Dos lados | ✘ | ✘ | Falta | H-88 (sólido y superficie) |
| REV · perfil que cruza el eje | ✔ error | ✔ error | ✔ | «El perfil cruza el eje de revolución» |
| REV · Operación Unir, Cortar, Intersecar | ✔ | ✔ | ✔ | 40712,39 / 31287,61 en dos cuerpos / 4712,39 |
| REV · Componente nuevo | ✘ | ✘ | Falta | H-83 (ampliada) |
| REV · Objetos para cortar | ✔ | ✔ `target` | ≈ | igual que en Extruir: sin «# cuerpos» al editar |
| REV · asa de ángulo, Enter, Esc, reabrir, deshacer, rehacer | ✔ | — | ✔ | asa: pieza `asas`; resto: pieza `revolucion_barrido_solevacion` |
| BAR · Ruta individual recta y en arco | ✔ | ✔ | ✔ | 628,32 = π·4·50; arco de r 30: 592,18 |
| BAR · Distancia 0,5 / 0 / −0,5 | ✔ | ✔ | ✔ | 314,16; errores claros |
| BAR · Distancia mayor que 1 | ✘ | ≈ | Bug | B-211: la ventana y `edit_feature` la recortan a 1 sin aviso; `sweep` con un número la rechaza |
| BAR · Conicidad 5° / −2° / −5° | ✔ | ✔ | ✔ | 3004,53 y 239,41 = fórmula del tronco de cono; −5° cierra el cono: error claro |
| BAR · Torsión 90° / 4000° | ✔ | ✔ | ✔ | 800 (cuadrado 4×4); 4000° error claro |
| BAR · Orientación Perpendicular / Paralela / Alineada | ✔ | ✔ | ✔ | paralela en un arco: 376,99 (no gira); alineada: pieza `herramientas_solido` |
| BAR · Ruta + Rail guía, escala Ninguna y Escalar | ✘ | ✘ | Bug | B-208: carril paralelo da 784,03 en vez de 800 (sólido) y 797,57 mm² (superficie); Escalar 3364,59 contra 3466,67 |
| BAR · Ruta + Rail guía, escala Estirar | ✘ (no la ofrece) | ✘ | Bug | B-209: el sólido hace Escalar; la superficie sí estira (400 mm²) |
| BAR · Ruta + Rail guía, Extensión y fracción del rail | ✘ | ✘ | Falta | H-89 (solo la tiene la superficie) |
| BAR · carril + torsión o conicidad | ✔ error | ✔ error | ✔ | «no se combinan con un carril guía» (Fusion tampoco las muestra con rail) |
| BAR · Ruta + Superficie guía, Barrido sólido, cadena | ≈ | ≈ | Parcial | SOL-8 (ya anotado); el aviso de cadena sale en cada barrido por boceto: H-93 |
| BAR · perfil paralelo a la ruta | ✔ error | ✔ error | ✔ | «El barrido no encierra volumen» |
| BAR · Cortar | ✔ | ✔ | ✔ | 3748,67 = 4000 − medio tubo |
| BAR · panel con carril en 1024×640 y 800×520 | ✔ | — | ≈ | Aceptar entra; el aviso flotante tapa campos: H-94 |
| SOL · dos perfiles, liso y reglado | ✔ | ✔ | ✔ | 2333,33 = prismatoide |
| SOL · un perfil, perfiles coplanares | ✔ error | ✔ error | ✔ | errores claros |
| SOL · punta (Aguda) | ✔ | ✔ | ✔ | pirámide 333,33 |
| SOL · Punto tangente | ✘ | ✘ | Falta | H-90 (la superficie lo hace: 157,12 mm²) |
| SOL · Dirección con ángulo y peso; peso 0 o negativo | ✔ | ✔ | ✔ | 1674,31; peso ≤ 0: error claro |
| SOL · Tangente / Suave contra una cara | ≈ | ≈ | Falta | H-91: aproximadas y no se combinan con carriles, línea central, cerrada ni reglada (la superficie sí: SUP-13) |
| SOL · condición en un perfil del medio | ✔ | ✔ | ✔ | 7012,52 |
| SOL · Raíles | ✘ | ✘ | Bug | B-212: carril recto da «sólido inválido»; la superficie sale bien (670,82 mm²) |
| SOL · Línea central | ✔ | ✔ | ✔ | 2333,33 |
| SOL · Raíles y línea central juntos | ✔ | ✔ error | ✔ | «Pasá rails o center_line, no los dos» |
| SOL · Cerrado (tres círculos alrededor de Z) | ✔ | ✔ | ✔ | sólido 2975,08 mm³ y superficie 2134,98 mm² con la misma forma (spline cerrado por 3 secciones, no un toro) |
| SOL · Aristas tangentes Fusionar / Mantener | ✔ | ✔ | ✔ | código |
| SOL · Cortar | ✔ | ✔ | ✔ | 7458,33 = 9000 − 1541,67 |
| SOL · Enter, Esc, previa | ✔ | — | ✔ | pieza `revolucion_barrido_solevacion` |
| SOL · Componente nuevo | ✘ | ✘ | Falta | H-83 |
| Botones en SÓLIDO, SUPERFICIE y PLÁSTICO; ninguno en CHAPA | ✔ | — | ✔ | pieza: 18 botones abren su comando y Esc no crea pasos |
| Guardar y reabrir (revolución + barrido + solevación) | — | ✔ | ✔ | mismos volúmenes al reabrir |

### Bugs y cómo reproducirlos

- **B-208.** YZ: cuadrado 4×4 centrado; ruta X 0..50; carril en XZ de (0, 2) a (50, 2); `sweep rail_scale="none"` →
  784,03 mm³, caja y ±2,31 (debería ser 800 y ±2). En la ventana: Barrido › Ruta + Rail guía › Ninguna, Enter → 784,02.
- **B-209.** Igual con el carril de (0, 2) a (50, 6): `rail_scale="stretch"` y `"scale"` dan 3364,59 los dos.
- **B-210.** Rectángulo x 10..20, y 0..10, eje Y: `revolve direction=two_sides angle=90 angle2=-45` → 2356,19;
  `create_surface_revolve` con la línea x=10 y los mismos ángulos → 235,62 mm² (como +45°).
- **B-211.** Barrido por una ruta de 50: en la ventana teclear «1,5» en Distancia → previa en verde; `edit_feature
  params={"distancia": "2"}` → ok y 628,32 mm³.
- **B-212.** Cuadros 10×10 (z 0) y 20×20 (z 10), carril de (5, 0) a (10, 10) en XZ: `loft rails=[…]` → «el kernel
  produjo un sólido inválido»; `create_surface_loft` igual → 670,82 mm².

Fichas completas en `docs/seguimiento/bugs.md`.

### Salida de `ponytail-audit` (código de las tres herramientas)

What this repo does: OmniCAD is a parametric 3D CAD in Python. Revolve, Sweep and Loft turn sketch profiles (or faces, curves, points) into solids or surfaces. The code lives in the timeline steps (`OpRevolucion`, `OpBarrido`, `OpSolevacion` and their `OpSup*` twins), the geometry core (`solidos_crear`, `superficies`), the window panels and the agent tools. Assumed load: one person or one agent, one document.

**Must fix**

1. **A sweep with a guide rail bends the profile** (`nucleo/solidos_crear.py:822`)
   - **What this is:** «Path + Guide Rail» moves the profile along the path. The rail sets the profile's size and turn.
   - **Problem:** A 4×4 square swept 50 mm with a rail parallel to the path and scale «None» gives 784.03 mm³. The answer should be 800. The box is ±2.31 instead of ±2. The surface version is wrong the same way (797.57 mm² instead of 800). Both ends are correct; the middle twists.
   - **Fix:** The likely cause is the rail mode (`SetMode(carril, True, BRepFill_NoContact)`). Check the profile frame there against a parallel rail, then add the test from finding 8.
   - **If we skip it:** Every swept part with a rail comes out a little wrong, and nobody is told.
2. **Solid sweep «stretch» silently does «scale»** (`nucleo/solidos_crear.py:880`, `:818-824`)
   - **What this is:** `rail_scale="stretch"` should grow the profile in one direction only.
   - **Problem:** The docstring says stretch «does not exist in OCC» and runs scale instead. The solid gives 3364.59 for both modes. The surface sweep stretches correctly (400 mm², `superficies.py:617`, `:725`), so it can be done.
   - **Fix:** Reuse the surface `_estirar` path. Until then, raise a clear error for «estirar» on solids.
   - **If we skip it:** An agent asks for stretch, gets a different shape, and sees no warning.
3. **«Two sides» with a negative angle works differently in solid and surface** (`timeline/operaciones.py:1298-1306`, `nucleo/superficies.py:475`)
   - **What this is:** Revolve «Two sides» turns one angle each way.
   - **Problem:** The solid uses the sign, so −45° folds back onto side 1 and disappears (1570.80, where 2356.19 is expected). The surface takes `abs` of both angles, so it gives 235.62 mm², the same as +45°.
   - **Fix:** Decide the rule once (reject negative values, or take `abs`) and use it in both places.
   - **If we skip it:** The same values make two different shapes, depending on the tab.
4. **Sweep distance above 1 is accepted and silently cut to 1** (`nucleo/solidos_crear.py:256`, `api/herramientas_solido.py:452`)
   - **What this is:** Distance is the fraction of the path, 0 to 1 (Fusion: «Range 0.00-1.00»).
   - **Problem:** The API rejects only plain numbers. The window, `edit_feature` and expressions accept «1,5» or «2» with no message and use `min(fraccion, 1.0)`.
   - **Fix:** In `_recortar_alambre`, raise `ErrorGeometria` when `fraccion > 1`. The check in the API can then go.
   - **If we skip it:** The user types 1.5 and believes the value was taken.

**Should fix**

5. **The «To object» and «Project axis» code is written twice** (`timeline/operaciones.py:1262-1285`, `timeline/ops_superficie.py:160-190`)
   - **What this is:** Both revolve steps resolve the limit object and project the axis onto the profile plane.
   - **Problem:** The two copies are line for line the same. A fix in one (for example two sides with «To object», H-89) has to be made twice.
   - **Fix:** One helper in `timeline/entidades.py` (or `geo`) that returns `(tipo, valor)` and the projected axis. Both steps call it.
   - **If we skip it:** They drift apart, like finding 3.
6. **Defaults and labels disagree for the same option** (`ui/comandos/solido.py:310`, `ui/comandos/superficie.py`, `api/herramientas_superficie.py`)
   - **What this is:** «Project Axis» and «Chain Selection».
   - **Problem:** The solid window shows «Eje de proyecto», on by default. The surface window shows «Proyectar eje», off. The API defaults to off. `create_surface_revolve` defaults `chain=True`, but its step defaults to `False`.
   - **Fix:** Use one default (Fusion's) and one label, «Proyectar eje», everywhere.
   - **If we skip it:** The same click in two tabs gives different bodies.
7. **The solid window hides «Estirar»** (`ui/comandos/crear.py`, `escala_carril` options)
   - **What this is:** The «Escala del perfil» drop-down.
   - **Problem:** It offers only Escalar and Ninguna. The step and the API take «estirar».
   - **Fix:** Add `"estirar": "Estirar"` once finding 2 is done.
   - **If we skip it:** The window offers less than the agent tools (strict MCP rule in CLAUDE.md).
8. **No test for the cases that broke** (`tests/test_solidos_crear.py:218`)
   - **What this is:** One rail test with scale «None» and a rail that moves away from the path.
   - **Problem:** Nothing checks a parallel rail (800), stretch versus scale, two sides with a negative angle in solid against surface, or distance above 1.
   - **Fix:** Four tests with numbers: 800 mm³; stretch ≠ scale; the same answer in solid and surface; an error for 1.5.
   - **If we skip it:** Findings 1 to 4 come back after any refactor.
9. **A warning on every sweep along a sketch path** (`timeline/ops_solido.py:139`)
   - **What this is:** «Selección de cadena» is on by default in the window.
   - **Problem:** Every normal sweep along sketch curves shows «La selección de cadena solo suma aristas de cuerpos…». Fusion also chains tangent sketch curves.
   - **Fix:** Drop the warning when every path item is a sketch curve (they are already one chain).
   - **If we skip it:** A useless message on every sweep teaches people to ignore messages.

Verdict: fix 1 first (wrong volumes with no message), then 2 and 3.
Lean: −25 lines, −0 dependencies possible.
Not checked: the inside of `solevar` (conditions, rails, closed loft), `barrer_cuerpo`, `barrer_superficie` beyond the rail modes, the OmniKernel engine, the handles (`asas`), and the full `herramientas_superficie.py`.

Correspondencia con el seguimiento (agregada después de la auditoría): 1 = B-208, 2 y 7 = B-209, 3 = B-210,
4 = B-211, 6 = H-92, 9 = H-93; la «H-89» del punto 5 es H-88 (el número se fijó al anotar). Las líneas citadas se
movieron: `operaciones.py` tiene cambios sin commitear de OpenCode (`OpRevolucion.ejecutar` está hoy cerca de la 1294)
y `ops_solido.py:139` es hoy la 149; en `solidos_crear.py` (también con cambios de OpenCode) la 822 es hoy la 819 y la 880, la 877.

### Salida de `ponytail-review` (lo cambiado en esta sesión)

What this change does: It adds a window test piece for Revolve, Sweep and Loft (`revolucion_barrido_solevacion.py`) and registers it in `todo.py`. It also adds API probe scripts and loads 4 bugs, 4 missing features and 3 improvements into the tracking lists. No app code was changed. Assumed load: one person running the test on one PC.

**Should fix**

1. **Expected values in the probe comments are wrong for boxes** (`evidencias/ui_2026-11-05/sondas_rbs.py`, cases `rev_cortar`, `rev_unir`, `bar_cortar`, `sol_cortar`)
   - **What this is:** Each probe has a comment with the hand-computed answer.
   - **Problem:** The comments assume `create_box` centers the box in Z. It actually starts the box at `z`. So `rev_cortar` says 26575.22, while the right answer for that box is 31287.61 (36000 − half ring 4712.39). The tool gave exactly that answer.
   - **Fix:** Rewrite those four comments with the real box (z from base) and the numbers that match.
   - **If we skip it:** Whoever reruns the probes thinks a correct result is a bug.
2. **One probe tests my selector, not the app** (`sondas_rbs.py`, `bar_aristas_ruta`)
   - **What this is:** A sweep along the edges of a box.
   - **Problem:** `edges:|X` picks all 4 edges parallel to X. They do not form one chain, so the error «La ruta debe ser una sola cadena» is correct. The probe proves nothing.
   - **Fix:** Pick one edge (`find_edges` and its id), or delete the case.
   - **If we skip it:** A useless ERR line in the evidence.

**Nice to have**

3. **Line numbers in `operaciones.py` will move** (`docs/seguimiento/bugs.md` B-210, `faltantes.md` H-88)
   - **What this is:** The evidence cites `timeline/operaciones.py:1305` and `:1294`.
   - **Problem:** OpenCode has uncommitted changes in that file. The lines already moved by 7 during this session.
   - **Fix:** Keep the function name next to the line (already done: `OpRevolucion.ejecutar`). Nothing else.
   - **If we skip it:** Someone opens the wrong line. The function name still finds it.

Verdict: fix 1 and 2 first.
Lean: −8 lines possible.
Not checked: the piece ran only in `--ventana minimizada`.

Aplicado después de la revisión: 1 y 2 (comentarios corregidos y `bar_aristas_ruta` borrado; sondas re-corridas: 78
casos). Después de la revisión salió B-212 (solevación sólida con carril), con su sonda aparte.

### Lo que no se pudo verificar (⚠)

- ⚠ Fusion real no se abrió: el criterio de «Simétrica», el ángulo negativo en «Dos lados» (B-210) y el valor por
  defecto de «Proyectar eje» (H-92) se apoyan solo en la ayuda.
- ⚠ La pieza corrió solo en `--ventana minimizada`; no corrieron la suite completa ni la prueba de humo (las corre el
  coordinador).
- ⚠ No se probaron a fondo: Barrido de cuerpo y Ruta + Superficie guía (están en SOL-8), Tangente contra una cara
  cuando la sección es la cara entera (la sonda `sol_tangente_cara` estaba mal armada: la sección no estaba en el borde
  de la cara elegida), reordenar perfiles de la solevación y las asas de las tres (las cubre la pieza `asas`).
- ⚠ `timeline/operaciones.py` tiene cambios de OpenCode sin commitear (Extruir); ningún hallazgo de acá depende de ese
  código, salvo los números de línea de `OpRevolucion`.
- Capturas miradas: en 800×520 el panel de Barrido con carril entra (con barra de desplazamiento), pero el aviso
  flotante tapa Distancia y Escala; en 1900×1000 el aviso tapa medio Aceptar de Solevación (H-94). La fila de la punta
  de la Solevación muestra solo «Aguda» (H-90).
