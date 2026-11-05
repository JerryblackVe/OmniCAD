# Auditoría de Nervio, Red y Repujado en todos los espacios (2026-11-05)

Pedido de Gerardo (2026-11-05): la misma auditoría que se hizo con Extruir ([auditoria_extruir.md](auditoria_extruir.md)),
ahora con las herramientas Nervio (Rib), Red (Web) y Repujado (Emboss): comparar con Fusion 360 y buscar bugs, mal funcionamiento y faltantes en SÓLIDO, SUPERFICIE,
PLÁSTICO, CHAPA, FORMA y donde más existan. Lo ejecuta una sesión aparte (Opus 5, esfuerzo alto). Tanda 2 de 2.
El prompt ya se cerró (2026-11-05).

## Resultado (2026-11-05)

Nervio, Red y Repujado andan bien en lo común: 61 casos por la API (39 dan el número de la cuenta a mano; la mayoría
de los 22 errores son los errores claros que corresponden) y 82 comprobaciones en la ventana. Se encontraron **5 bugs**
(B-213 a B-217), **3 faltantes** (H-95 a H-97) y **3 mejoras** (H-98 a H-100). No se tocó código de la app. Evidencia
en `evidencias/ui_2026-11-05/`: `sondas_nrr.py` y su salida `sondas_nrr.txt`, el registro `nervio_red_repujado.json` /
`.log` y las capturas `capturas/nervio_*.png`, `red_*.png`, `repujado_*.png` y `asas_*.png`.

### Referencia de Fusion por herramienta y espacio

| Espacio de Fusion | Nervio (Rib) | Red (Web) | Repujado (Emboss) | En OmniCAD |
|---|---|---|---|---|
| SÓLIDO | Sí: perfil abierto, Simétrico / Un lado, Inicio Abajo / Arriba, Grosor, Al siguiente / Profundidad, Invertir, Ángulo de desmoldeo, Dirección de extracción con su Invertir, Radio de empalme, preajustes (`Rib reference`, `Create a rib`) | Sí: lo mismo sin dirección de extracción, más Alargar curvas (`Web reference`, `Create a web`) | Sí: perfiles y texto, Caras, Cadena tangente, Efecto Relieve / Grabado, Invertir normal, Profundidad (negativa = grabado), Alineación horizontal, vertical y giro con asas (`Emboss reference`, `Emboss a solid body`) | `nervio`, `red`, `repujado` en CREAR (pieza: ✔) |
| PLÁSTICO | El mismo menú CREAR; la regla de plástico da Espesor, Desmoldeo y Radio nominal «used by … Rib, Web, … Emboss» (`Plastic rules`) | ídem | ídem | Los mismos tres botones (pieza: ✔); la regla no se toma: H-87 (espesor) y H-100 (desmoldeo y radio) |
| SUPERFICIE | No (índice `docs/fusion_docs/indice/fusion-patch.md`: ni Rib, ni Web, ni Emboss) | No | No | Sin botones (bien) |
| CHAPA | No (índice `fusion-sheet-metal.md`) | No | No | Sin botones (bien) |
| FORMA (T-Splines) | No (índice `fusion-sculpt.md`) | No | No | No existe el espacio (P-25j) |
| MALLA | No (índice `fusion-mesh.md`) | No | No | Sin botones (bien) |

En Fusion, el desmoldeo, la dirección de extracción y el radio del Nervio y la Red son de la «Design Extension». La
ayuda no dice dónde queda el grosor con desmoldeo; OmniCAD lo deja en la curva y engorda hacia la base (el test
`test_nervio_con_desmoldeo_es_mas_fino_en_el_borde_libre` lo fija). ⚠ Sin abrir Fusion no se pudo confirmar.

### Matriz de opciones

Leyenda: ✔ igual que Fusion · ✘ falla o falta · ≈ parecido. «CLI» es el mismo catálogo que el MCP (`omnicad call`).
Escuadra de las sondas: 25500 mm³; el nervio de la línea (35, 5) → (5, 45) con 2 mm suma 1200.

| Herramienta · opción (Fusion) | Ventana | MCP / CLI | Estado | Evidencia |
|---|---|---|---|---|
| NER · perfil abierto: línea, dos líneas encadenadas, arco | ✔ | ✔ `curves` | ✔ | 26700; 26700; arco 26418,27 |
| NER · curva cerrada, curva dentro del cuerpo, sin cuerpo | ✔ error | ✔ error | ✔ | «necesita una curva abierta», «la curva queda dentro del cuerpo», «No hay un cuerpo sólido» |
| NER · varias curvas sueltas | ✘ | ✘ | Bug | B-214 (mensaje de «ruta») |
| NER · Simétrico / Un lado desde abajo / desde arriba | ✔ | ✔ `direction` | ✔ | 26700 los tres; el lado: `test_nervio_inicio_abajo_o_arriba` |
| NER · Grosor: «2,5», «e * 2», pegar «3 mm», Enter | ✔ | ✔ | ✔ | «e * 2» = 27300; pegado 3 mm y Enter: +1800 |
| NER · Grosor vacío, 0, −2, «abc», «10 deg» | ✔ aviso | ✔ error | ✔ | «Expresión vacía», INVALID_ARGUMENTS, UNIT_MISMATCH |
| NER · Al siguiente | ✔ | ✔ | ✔ | +1200 |
| NER · Profundidad 5 / 100 / 0 | ✔ | ✔ | ✔ | 25947,92 = 600·(1 − (19/24)²)·2; 100 = Al siguiente; 0: error |
| NER · Invertir (Flip) | ✘ | ✘ | Bug | B-213: hacia afuera rellena hasta la caja del cuerpo (+1950) en vez de avisar |
| NER · boceto en el borde del cuerpo; grosor 1e6 | ✘ | ✘ | Bug | B-213: simétrico +600 (la mitad), un lado «la curva queda dentro»; 1e6 recortado al ancho |
| NER · Ángulo de desmoldeo 5° / ±60° | ✔ | ✔ `draft_angle` | ✔ | 27539,89; ±60: INVALID_ARGUMENTS |
| NER · Ángulo de desmoldeo negativo | ✘ | ✘ | Bug | B-215 (−1° y −5°: «El desmoldeo falló en el kernel») |
| NER · Dirección de extracción | ✘ | ✘ | Bug | B-215 (plano XY con 1° y 5°: mismo error) |
| NER · Invertir la extracción; Radio de empalme | ✘ | ✘ | Falta | H-95 |
| NER · Cuerpo (objetivo) | ✔ | ✔ `target` | ✔ | pieza: elegido con el visor |
| NER · reabrir y editar, `edit_feature` | ✔ | ✔ | ✔ | Grosor 4 = 27900 |
| NER · deshacer / rehacer | ✔ | ✔ | ✔ | 25500 ↔ 26700 |
| NER · asas de Grosor y Profundidad | ✔ | — | ✔ | +3 mm (grosor ×2 en simétrico); más allá del cero: tope en 0 y la previa vuelve al escribir |
| NER · preajustes | ✔ | ✔ `manage_command_presets` | ✔ | `test_sol27_preajustes.py` |
| RED · cruz Al siguiente con Alargar curvas | ✔ | ✔ | ✔ | caja hueca 14752 → 20072 (5320 = 2·36·38·2 − 152) |
| RED · Alargar curvas apagado | ✔ | ✔ `extend_curves` | ✔ | 17640 |
| RED · Profundidad 10 | ✔ | ✔ | ✔ | 16152 |
| RED · Un lado (los dos) | ✔ | ✔ | ✔ | 20072 |
| RED · Invertir | ✘ | ✘ | Bug | B-216: 18280 con y sin invertir (debería 19000) |
| RED · boceto delante del cuerpo | ✘ | ✘ | Bug | B-213: «la curva queda dentro del cuerpo» |
| RED · Ángulo de desmoldeo 2° | ✔ | ✔ | ✔ | 23411,72 (engorda hacia el fondo, como el Nervio) |
| RED · Radio de empalme 1 / −1 / 30 | ✔ | ✔ `fillet_radius` | ✔ | 20197,61; error; «radio demasiado grande» |
| RED · grosor 0, curva cerrada | ✔ error | ✔ error | ✔ | errores claros |
| RED · panel con Más opciones en 1024×640 y 800×520 | ✔ | — | ✔ | Aceptar entra (scroll); capturas `red_1024x640.png`, `red_800x520.png` |
| REP · Relieve / Grabado en cara plana | ✔ | ✔ `emboss_type` | ✔ | 24100 / 23900 |
| REP · profundidad negativa | ≈ | ✔ | Mejora | graba bien (23900); el panel sigue en Relieve: H-99 |
| REP · profundidad 0, vacía, «2 deg» | ✔ aviso | ✔ error | ✔ | errores claros |
| REP · Invertir normal | ✔ | ✔ `reverse` | ≈ | relieve invertido queda adentro: 24000 (sin cambio visible) |
| REP · Alineación horizontal, vertical, giro | ✔ campos | ✔ | ✔ | 5, 5, 45°: 24100 |
| REP · asas de alineación | ✘ | — | Falta | H-97 (solo el asa de Profundidad) |
| REP · perfil fuera de la cara | ✔ error | ✔ error | ✔ | «Los perfiles no caen sobre las caras elegidas…» |
| REP · texto | ✔ | ✔ `profile="text"` | ✔ | «AB» de 5 mm: +17,53 |
| REP · cara perpendicular al boceto | ≈ | ≈ | ≈ | OmniCAD «adapta» el perfil (decisión del 2026-10-13 en PROJECT_LOG); Fusion lo proyecta |
| REP · varias caras y varios cuerpos | ✔ | ✔ | ✔ | PROJECT_LOG 2026-10-13; `test_repujado_alineacion.py` |
| REP · cilindro con Envolver | ✔ | ✔ `wrap` | ✔ | +37,80 = 6·6·1·(1 + 1/20) |
| REP · cilindro sin marcar Envolver | ✘ error | ✘ error | Mejora | H-98 (Fusion envuelve solo) |
| REP · esfera, cono, cara libre | ✘ | ✘ | Falta | H-96 |
| REP · Cadena tangente | ✘ | ✘ | Bug | B-217: +437,12 en vez de +100 (repuja en los costados) |
| REP · asa de Profundidad | ✔ | — | ✔ | +3 mm; tope en 0 |
| Botones en SÓLIDO y PLÁSTICO; ninguno en SUPERFICIE, CHAPA y MALLA | ✔ | — | ✔ | pieza: 6 botones abren su comando y Esc no crea pasos |
| Guardar y reabrir (los tres) | ✔ | ✔ | ✔ | mismos volúmenes (ventana y API) |
| Excepciones en slots de Qt | ✔ | — | ✔ | ninguna en 82 comprobaciones |

Todas las opciones de la ventana tienen su parámetro en `create_rib`, `create_web` y `create_emboss` (y `edit_feature`),
salvo el Radio de empalme del Nervio, que no está en ninguno de los dos (H-95).

### Bugs y cómo reproducirlos

- **B-213.** Escuadra (piso x 0..40, y −30..30, z 0..5; pared x 0..5, z 0..50), boceto XZ con la línea (35, 5) → (5, 45):
  `create_rib thickness=2 reverse=true` → 27450 (debería avisar). Con la escuadra en y 0..60: simétrico → 26100 (debería
  26700) y `direction="side1"` → «la curva queda dentro del cuerpo».
- **B-214.** Misma escuadra, dos líneas sueltas en el boceto: `create_rib` → «La ruta debe ser una sola cadena continua».
- **B-215.** Misma escuadra: `create_rib draft_angle=-1` y `draft_angle=1 pull_direction="XY"` → «El desmoldeo falló en el kernel».
- **B-216.** Caja 40³ vaciada 2 mm cerrada, plano XZ desplazado −15 (y = 15) con la línea z = 20: `create_web` y
  `create_web reverse=true` → 18280 los dos.
- **B-217.** Placa 60×40×10 con las aristas de arriba empalmadas r 3, cuadro 10×10 encima: `create_emboss faces=">Z"
  depth=1 tangent_chain=true` → +437,12 y caja −1..61.

Fichas completas en `docs/seguimiento/bugs.md`. Todo se repite con `sondas_nrr.py <nombre del caso>` desde `clon/`.

### Salida de `ponytail-audit` (código de las tres herramientas)

What this repo does: OmniCAD is a parametric 3D CAD in Python. Rib (`nervio`) grows a thin wall from an open sketch
curve, parallel to the sketch, until it meets the body. Web (`red`) does the same perpendicular to the sketch. Emboss
(`repujado`) raises or cuts sketch profiles or text on body faces. The code lives in the timeline steps (`OpNervio`,
`OpRed`, `OpRepujado`), the geometry core (`nucleo/solidos_crear.py`), the window command (`ui/comandos/crear.py`,
`asas_extra.py`) and the agent tools (`api/herramientas_solido_extra.py`). Assumed load: one person editing one
document; the cost that matters is a wrong shape with no warning.

**Must fix**

1. **Rib and Web are clipped to the body's bounding box** (`nucleo/solidos_crear.py:1402`)
   - **What this is:** `_hasta_el_cuerpo` trims the long raw wall so it stops at the body ("To Next").
   - **Problem:** It first intersects the wall with the body's bounding box (the smallest box around the body). A flipped rib that points away from the body fills that box up to its edge (+1950 mm³) instead of failing. A rib drawn on the body's edge loses the half that sticks out (+600 instead of +1200), and a one-side rib there fails with "the curve is inside the body", which is false.
   - **Fix:** Drop the box clip. After cutting the body away, keep only the pieces that touch the curve, and for "To Next" check that the piece does not reach the far end of the raw prism (it must stop on a face). Clip only in the growth direction, never across the thickness.
   - **If we skip it:** Users get phantom walls or half ribs with no message.
2. **Web "Flip" does nothing** (`timeline/ops_solido.py:286`, `nucleo/solidos_crear.py:1477`)
   - **What this is:** `OpRed` flips by negating the sketch normal.
   - **Problem:** `red()` tries both directions `(-n, n)` and keeps the nearest wall, so the negated normal changes nothing. A web 13 mm from one wall and 23 mm from the other gives 18280 mm³ with and without Flip. `red()` already has an `invertir` parameter that no caller passes.
   - **Fix:** In `OpRed.ejecutar` pass `plano.normal` and `invertir=self.p["invertir"]` to `red()`. One line.
   - **If we skip it:** The button looks broken; the user cannot pick the other wall.
3. **Rib with several separate curves fails with a wrong message** (`nucleo/solidos_crear.py:1439`)
   - **What this is:** `nervio()` joins all chosen edges into one wire (`_alambre`).
   - **Problem:** The window lets the user pick several curves. Two separate lines give "The path must be one continuous chain" — the rib has no path. Fusion makes one rib per curve.
   - **Fix:** Loop over `_cadenas(aristas)` like `red()` does and unite the results.
   - **If we skip it:** Users must make one rib step per curve, and the error confuses them.
4. **Rib draft fails with a negative angle or a pull direction** (`nucleo/solidos_crear.py:1412`, `:1457`)
   - **What this is:** `_desmoldear_pared` tilts the side walls of the raw rib.
   - **Problem:** −1° and 1° with pull direction "XY" both end in "draft failed in the kernel" on a diagonal rib. The API advertises −45..45 and the pull direction. The only test with a pull direction uses the growth direction itself, so it never sees this.
   - **Fix:** Not confirmed in code. First add the two failing cases as tests, then check which faces `_desmoldear_pared` passes when the pull is not the growth direction.
   - **If we skip it:** Two documented options do not work at all.
5. **Emboss "tangent chain" embosses on the side walls too** (`nucleo/solidos_crear.py:1548`, `:1608`)
   - **What this is:** Tangent chain adds faces that touch the chosen face smoothly.
   - **Problem:** On a plate with filleted top edges, the chain reaches the side walls. Each side wall group then goes through `_perfiles_en_zona` with `adaptar`, which turns and shrinks the profile to fit. Result: +437.12 mm³ instead of +100, with small squares on every side.
   - **Fix:** Do not "adapt" profiles onto faces that only came from the chain; those faces get only what falls on them.
   - **If we skip it:** Every emboss with tangent chain near rounded edges is wrong.

**Should fix**

6. **`radio_empalme` is stored but ignored by the Rib** (`timeline/ops_solido.py:271`)
   - **What this is:** `OpNervio.PARAMS` has `radio_empalme`; Fusion Rib has "Fillet Radius".
   - **Problem:** `OpNervio` unites with a plain boolean, so the stored value is dead for ribs. The window hides it for ribs and `create_rib` has no `fillet_radius`.
   - **Fix:** Use `unir_con_empalme` in `OpNervio` (it already exists for the Web) and show the field and the API argument.
   - **If we skip it:** A parameter that does nothing sits in every rib step.
7. **No test for Web Flip or for negative draft** (`tests/test_sol10_nervio_red.py`)
   - **What this is:** The Rib/Web test file covers draft, start side, fillet and extend.
   - **Problem:** Findings 2 and 4 would have been caught by one test each.
   - **Fix:** Add `red` inside a closed box with and without Flip (18280 / 19000) and `nervio` with −1°.
   - **If we skip it:** The same bugs come back after the next refactor.
8. **Emboss on a cylinder demands a "wrap" checkbox** (`nucleo/solidos_crear.py:1573`)
   - **What this is:** A cylindrical face without `envolver` raises an error.
   - **Problem:** Fusion has no such checkbox; it always wraps on curved faces. The branch only exists to tell the user to tick a box.
   - **Fix:** Wrap automatically on cylindrical faces and delete the error branch (and later the checkbox).
   - **If we skip it:** One extra click and one confusing error for every emboss on a cylinder.

**Nice to have**

9. **The "Type" field does not follow a negative depth** (`ui/comandos/crear.py:356`)
   - **What this is:** The core turns a negative emboss depth into a deboss.
   - **Problem:** The panel still says "Relieve" after typing −1 mm (Fusion flips the Effect).
   - **Fix:** When the depth turns negative, set `tipo` to the other value and the depth to its absolute value.
   - **If we skip it:** The panel shows the wrong effect.

Verdict: fix 1 and 2 first (1 is the root of three wrong results; 2 is one line).
Lean: −6 lines possible (finding 8 deletes the error branch).
Not checked: `_perfiles_en_zona`, `_envolver_en_cilindro` and the text-hole handling were read only where the findings
needed them; the desmoldeo kernel path (`desmoldeo` in `solidos_modificar.py`) was not traced to the failing face.

### Salida de `ponytail-review` (lo cambiado en esta sesión)

What this change does: It adds a window test piece for Rib, Web and Emboss (`nervio_red_repujado.py`) and registers
it in `todo.py`. It adds an API probe script (`sondas_nrr.py`, outside git), loads 5 bugs, 3 missing features and 3
improvements into the tracking lists, and writes the audit report. No app code was changed. Assumed load: one person
running the test pieces at night, one at a time.

**Should fix**

1. **The check counts in the docs go stale** (`docs/auditoria_nervio_red_repujado.md`, `prueba_nocturna_2026-10-31.md` 3r, `PROJECT_LOG.md`)
   - **What this is:** The docs say the piece ran "83 checks, 9 ✗".
   - **Problem:** After the last edit, the Tab check is skipped with ⚠ when the window has no focus (minimized mode). The next run gives 82 checks. The docs count the old run.
   - **Fix:** Run the piece once more and write the real numbers in the three places.
   - **If we skip it:** The coordinator compares the night run with a number that never appears again.
2. **Two comments in the probes are wrong** (`evidencias/ui_2026-11-05/sondas_nrr.py`: `SZ`, `nervio_dos_curvas_sueltas`)
   - **What this is:** Each probe has a comment with the expected result.
   - **Problem:** `SZ = 1` still says "fixed in nervio_base if z comes out negative", but it is a fixed value now. The two-curves comment ends in "~2033·…", which is not a number.
   - **Fix:** `SZ`: "sketch y on XZ = world Z". Two curves: "Fusion: one rib per curve, union of both; OmniCAD: error (B-214)".
   - **If we skip it:** Whoever reruns the probes reads a half-written expectation.

**Nice to have**

3. **The bug total in the header no longer matches the table** (`docs/seguimiento/bugs.md:5`)
   - **What this is:** The header says "Total 27: Open 21 · Partial 5 · Blocked 1".
   - **Problem:** While I worked, the OpenCode session put B-206 back as Partial. The table now has 28 rows (Partial 6). My edit wrote the count before that.
   - **Fix:** The coordinator (or the OpenCode session that owns B-206) recounts when it integrates. The brief says not to touch rows from others.
   - **If we skip it:** One off-by-one count in the header until the next recount.

Verdict: fix 1 and 2 first.
Lean: 0 lines.
Not checked: the piece only ran with `--ventana minimizada`.

Aplicado después de la revisión: 1 y 2 (pieza re-corrida: 82 comprobaciones, las mismas 9 ✗ de la app y el Tab con ⚠;
conteos corregidos en los tres documentos; comentarios de las sondas corregidos). El 3 queda para el coordinador.

### Lo que no se pudo verificar (⚠)

- ⚠ Fusion real no se abrió: dónde queda el grosor con desmoldeo (en la curva o en la base), si «Invertir» del Nervio
  sin cara da error y si un Nervio con varias curvas es un solo paso se apoyan solo en la ayuda y sus imágenes.
- ⚠ La pieza corrió solo en `--ventana minimizada`: el chequeo de Tab necesita el foco real (sale con ⚠). No corrieron
  la suite completa ni la prueba de humo (las corre el coordinador).
- ⚠ No se probaron a fondo: el texto con huecos sobre varias caras (tiene historia y tests propios del 2026-10-13), el
  repujado en varios cuerpos a la vez y la regla de plástico más allá de leer el código (H-87 y H-100).
- ⚠ `solidos_crear.py`, `operaciones.py`, `comando.py` y `manipuladores.py` tienen cambios de OpenCode sin commitear
  (Extruir): las pruebas corrieron con ese código. Ningún hallazgo de acá toca lo que cambió Extruir, pero los
  números de línea de `solidos_crear.py` pueden moverse.
