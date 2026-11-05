# Auditoría de Extruir en todos los espacios (2026-11-05)

Pedido de Gerardo (2026-11-05): auditar la herramienta Extruir y todas sus opciones, comparar con Fusion 360 y buscar
bugs, mal funcionamiento y faltantes en SÓLIDO, SUPERFICIE, PLÁSTICO, CHAPA y el resto de los espacios donde exista.
Lo ejecuta una sesión aparte (Opus 5, esfuerzo alto). El prompt ya se cerró (2026-11-05).

## Resultado (2026-11-05)

Extruir anda bien en lo común: 50 casos por la API y 18 comprobaciones en la ventana dan los números de la cuenta a
mano. Se encontraron **2 bugs** (B-205, B-206), **5 faltantes** (H-81 a H-85) y **2 mejoras** (H-86, H-87). No se
tocó código de la app. Evidencia: `evidencias/ui_2026-11-05/` (`sondas_extruir.py` y sus salidas `.txt`, el registro
`pieza_extruir_espacios.json` y las capturas).

### Referencia de Fusion por espacio

| Espacio de Fusion | ¿Tiene Extruir? | Artículo (`scripts/fusion_docs.py ver`) | En OmniCAD |
|---|---|---|---|
| SÓLIDO | Sí: tipo normal o delgada, Inicio, Dirección, Medida, Extensión, Extender, Desfase, Conicidad, Pared, Operación, Objetos para cortar | `Extrude reference`, `Extrude a solid body` (`-s fusion-model`) | Comando `extruir` (tecla E) |
| SUPERFICIE | Sí: perfil, curva, cara plana o texto de una línea; Chaining; Inicio, Dirección, Extensión (Al objeto con Extend/Chain Faces), Conicidad; Cuerpo o Componente nuevo | `Extrude a surface body` (`-s fusion-patch`) | Comando `sup_extruir` |
| PLÁSTICO | El mismo Extruir de SÓLIDO; la regla de plástico da el espesor como parámetro («used by modeling tools such as Extrude») | `Plastic rules` (`-s fusion-model`) | El mismo `extruir`, en el menú CREAR |
| CHAPA | No: el índice `docs/fusion_docs/indice/fusion-sheet-metal.md` no tiene ningún artículo de Extrude. La ayuda pide hacer las ranuras con Extruir de SÓLIDO sobre la chapa desplegada (`Unfold sheet metal bodies`) | — | Sin botón en CHAPA (bien). Cortar con Extruir una pestaña base anda: 2400 → 2200 mm³ |
| FORMA (T-Splines) | Sí: distancia, espaciado uniforme o por curvatura, caras, ángulo, dirección, caras frontales, mantener pliegues | `Extrude a T-Spline body` (`-s fusion-sculpt`) | No existe el espacio FORMA: ya está como P-25j |
| MALLA | Solo «Extrude Texture» (relieve desde una imagen) | `Extrude texture on a mesh body` (`-s fusion-mesh`) | Botón grisado: ya está como MAL-2 |
| Presionar/Tirar | Sobre un perfil de boceto abre Extruir | `Create solids with Press Pull` | Pulsar/Tirar existe; sobre perfil no se probó (⚠) |

Nota: el prompt nombra la extensión «Entre»; la ayuda actual de Fusion no la tiene (solo Distancia, Al objeto y Todo).

### Matriz de opciones

Leyenda: ✔ igual que Fusion · ✘ falla o falta · ≈ parecido. «CLI» es el mismo catálogo que el MCP: se probó
`extrude` por la CLI y da lo mismo (B-205 incluido).

| Opción (Fusion) | Ventana | MCP / CLI | Estado | Evidencia |
|---|---|---|---|---|
| Perfiles cerrados y caras planas coplanares | ✔ | ✔ `sketch`+`profile`, `faces` | ✔ | `cara_de_cuerpo_unir` 3000 mm³; cara curva da «Solo se pueden usar caras planas» |
| Elegir un boceto entero en el navegador | ✔ (`acciones_navegador.extruir_boceto`) | ✔ `profile="sketch"` | ✔ | código |
| Tipo Extruir | ✔ | ✔ | ✔ | 20×10×10 = 2000 mm³ |
| Tipo Delgada, perfil cerrado, Lado 1 / Lado 2 / Centro | ✔ | ✔ `thin`, `wall_location` | ✔ | 640 / 560 / 600 mm³ = cuenta |
| Delgada con perfil abierto | ✔ | ✔ `open_curves` | ✔ | línea 20, pared 2, 10 de alto = 400 mm³ |
| Delgada: Cadena tangente | ✘ | ✘ | Falta | H-84 |
| Delgada abierta con conicidad | ✘ error | ✘ error | Falta (confirmar en Fusion) | H-84 |
| Inicio: Plano de perfil / Desfase | ✔ | ✔ `start`, `start_offset` | ✔ | desfase 5 → z 5..15 |
| Inicio: Objeto paralelo | ✔ | ✔ `start_object` | ✔ | plano a 7 mm → z 7..17 |
| Inicio: Objeto inclinado | ✘ | ✘ | Bug | B-206 (también en superficie) |
| Dirección: Un lado (+ y −) | ✔ | ✔ | ✔ | −10 → z −10..0 |
| Dirección: Simétrica, Media longitud / Longitud total | ✔ | ✔ `symmetric_measure` | ≈ | 4000 / 2000 mm³; el defecto difiere entre ventana y API: H-86 |
| Dirección: Dos lados | ✔ | ✔ `distance2` | ✔ | 10 + 5 = 3000 mm³ |
| Dos lados con distancia negativa | ✘ | ✘ | Bug | B-205: 2000 o 3000 según la conicidad |
| Dos lados con lado 2 = 0 | ✔ error claro | ✔ | ✔ | «tiene que ser de al menos 0.000001 mm» |
| Dos lados: extensión propia del lado 2 | ✘ | ✘ | Falta | H-81 |
| Extensión: Distancia (0, enorme, «1 cm», «2,5», «alto + 5 mm», «45 deg») | ✔ | ✔ | ✔ | 0 y 1e7 dan error claro; «45 deg» da UNIT_MISMATCH; el tecleo lo cubre la pieza `teclear` |
| Extensión: Al objeto, Hasta la cara seleccionada / Hasta el cuerpo / A través | ✔ | ✔ `to`, `to_mode` | ✔ | hasta z=35, 37 con desfase 2, 45 a través |
| Extensión: Al objeto, Hasta caras adyacentes | ✘ | ✘ | Falta | H-82 |
| Al objeto + Simétrica | ✔ error claro | ✔ | ✔ | «no se combina con la dirección simétrica» |
| Al objeto + Dos lados (lado 2 distancia) | ✔ | ✔ | ✔ | z −5..35, 8000 mm³ |
| Extensión: Todo, Invertir | ✔ | ✔ `extent="all"`, `reverse` | ✔ | corte del techo 16000 → 14000; invertido sin cuerpos: error claro |
| Conicidad (lado 1 y 2), ±89° | ✔ | ✔ | ✔ | −10° en 20×10×10 = 1512,47 mm³ = fórmula del prismatoide; 90° da error claro (B-197 sigue aparte) |
| Operación: Unir, Cortar, Intersecar, Cuerpo nuevo, auto | ✔ | ✔ | ✔ | intersecar = 1000 mm³; `auto` sobre una cara apoyada da cuerpo nuevo |
| Operación: Componente nuevo | ✘ | ✘ | Falta | H-83 |
| Objetos para cortar (vacío = automático) | ✔ | ✔ `target` | ≈ | Fusion congela los cuerpos al crear y ofrece Auto-select al editar; OmniCAD queda automático si no se eligen |
| Asas: distancia, lado 2, conicidad 1 y 2, desfase de inicio | ✔ | — | ✔ | `ui/comandos/solido.py:79-113`; probadas en la pieza `asas` |
| Previa en rojo al cortar y paso solo a Cortar | ✔ | — | ✔ | `ui/comandos/solido.py:127-190` |
| Enter, Esc, reabrir el paso, deshacer, rehacer, guardar y reabrir | ✔ | ✔ | ✔ | pieza `pieza_extruir_espacios`; `guardar_y_reabrir` da igual |
| Panel en 1024×640 y 800×520 (delgada + dos lados + cortar + desfase) | ✔ | — | ✔ | Aceptar dentro de la ventana en los dos tamaños |
| PLÁSTICO: espesor de la regla en la delgada | ≈ | ≈ | Mejora | H-87: anda solo escribiendo `PlasticThickness` |
| SUPERFICIE: curva abierta, perfil cerrado, cara plana | ✘ perfil y cara | ✔ | Falta en la ventana | H-85; API: 200 / 600 / 600 mm² |
| SUPERFICIE: Simétrica, Dos lados, Al objeto, Todo, Conicidad | ✔ | ✔ | ✔ | 400 / 300 mm², 700 mm² hasta z=35, conicidad 10° = 203,09 mm² |
| SUPERFICIE: Al objeto con Extend / Chain Faces | ✘ | ✘ | Falta | H-82 |
| Botón Extruir en SÓLIDO, SUPERFICIE, PLÁSTICO; ninguno en CHAPA | ✔ | — | ✔ | pieza `pieza_extruir_espacios` |

### Bugs y cómo reproducirlos

- **B-205.** Boceto XY con rectángulo 20×10; `extrude direction=two_sides distance=10 distance2=-5` → 2000 mm³ y caja
  z 0..10 (el lado 2 desaparece). Con `taper_angle=0.001` → 3000 mm³. En la ventana: Dos lados, teclear 10 mm y −5 mm,
  Enter → 2000 mm³ sin aviso.
- **B-206.** Plano de construcción a 30° sobre X por el origen, `extrude start=object start_object=<plano> distance=10`
  → caja z 0..10, igual que sin Inicio. Igual en `create_surface_extrude` y en la ventana.

Fichas completas en `docs/seguimiento/bugs.md`.

### Salida de `ponytail-audit` (código de Extruir)

What this repo does: OmniCAD is a parametric 3D CAD in Python. Extrude turns a sketch profile or a flat face into a
solid or a surface; it lives in the timeline step (`OpExtrusion`, `OpSupExtruir`), the geometry core
(`extruir_avanzado`), the window panel and the agent tools. Load assumed: one person or one agent, one document.

**Must fix**

1. **Two sides with a negative distance gives two different answers** (`timeline/operaciones.py:1229`, `nucleo/solidos_crear.py:595`)
   - **What this is:** «Two sides» extrudes one distance up and another down.
   - **Problem:** Without taper, the simple path uses the signed value, so −5 goes up and vanishes in the union (2000 mm³). With any taper, the advanced path uses `abs` (3000 mm³).
   - **Fix:** Decide the rule once in `geo.exigir_distancias_extrusion`, which both paths already call: reject a negative side-2 distance, or take `abs` there.
   - **If we skip it:** The same recipe changes shape when someone adds 0.001° of taper. (B-205)
2. **Start › Object on a tilted plane is silently ignored** (`timeline/operaciones.py:1161`, `timeline/ops_superficie.py:131`)
   - **What this is:** The extrusion should start on the chosen face or plane.
   - **Problem:** Only the distance of the plane origin along the normal is used. A 30° plane through the sketch gives the same body as no start at all, with no warning.
   - **Fix:** Until real support exists, raise a clear error when the object is not parallel to the profile (`abs(n·n_obj) < 1 − 1e-9`). Same check in both files.
   - **If we skip it:** A user gets a body in the wrong place and does not know it. (B-206)
3. **Side-2 options are accepted and ignored** (`timeline/operaciones.py:1133`, `:1169`)
   - **What this is:** `OPCIONES["extension2"]` lists distance, object and all.
   - **Problem:** `run_operation` with `extension2="todo"`, or `"objeto"` without `hasta2`, passes validation and `ejecutar` silently uses `distancia2` (tested: z −3..10).
   - **Fix:** Leave only `("distancia",)` in `OPCIONES["extension2"]` until H-81 is built.
   - **If we skip it:** An agent believes it extruded «to all» on side 2 and got 3 mm.

**Should fix**

4. **The side and length rules are written three times** (`timeline/operaciones.py:1222-1230`, `nucleo/solidos_crear.py:592-600`, `ui/comando.py:1623-1634`)
   - **What this is:** Each place turns direction, measure, d1 and d2 into the spans to extrude.
   - **Problem:** They already disagree (finding 1); the fast drag preview is a third copy that can drift too.
   - **Fix:** One small function in `nucleo/geometria.py` that returns the signed spans; the three places call it.
   - **If we skip it:** Every rule change must be made three times, and the preview can show another shape than the result.
5. **No test for the cases that broke** (`tests/test_api_opciones_solido1.py:69` only tries a parallel start plane)
   - **What this is:** Tests check volumes of the normal options.
   - **Problem:** Nothing checks two sides with a negative value, or a non-parallel start object.
   - **Fix:** Two tests with numbers: «two sides 10/−5 gives the same with and without taper» and «tilted start object fails or starts on the plane».
   - **If we skip it:** Findings 1 and 2 come back after any refactor.
6. **New recipes still write the old `simetrica` flag** (`api/herramientas_solido.py:290`)
   - **What this is:** Old recipes stored «symmetric total» as `simetrica=True`; new ones use `direccion` and `medida`.
   - **Problem:** The API keeps writing the old flag, so two fields describe one choice and every reader (`desde_op`, the preview) must translate it.
   - **Fix:** Write `direccion="simetrica", medida="total", simetrica=False`, like the «half» branch two lines above.
   - **If we skip it:** The legacy path can never be removed.

**Nice to have**

7. **Dead «llega» mode** (`nucleo/solidos_crear.py:624-631`)
   - **What this is:** A mode of `_recortar_hasta` that stops the extrusion inside the body.
   - **Problem:** No caller passes it (grep: only the function itself; the boss passes «cuerpo»).
   - **Fix:** Delete the branch and its name in the check.
   - **If we skip it:** Five lines nobody runs and nobody tests.

Verdict: fix 1 and 2 first (wrong shapes without warning), then 3.
Lean: −25 lines, −0 dependencies possible.
Not checked: the T-Spline path (does not exist), Press/Pull on a profile, `reconocer_funciones` and `reconstruir`
(they call `extrude` but were not read), the OmniKernel engine (`nucleo/omnikernel/geometria.py`).

### Salida de `ponytail-review`

What this change does: Agrega una pieza de prueba de ventana para Extruir (`pieza_extruir_espacios.py`, sumada a
`todo.py`), el informe de auditoría con matriz y salida de `ponytail-audit`, y anota los hallazgos en el seguimiento
(B-205, B-206, H-81 a H-87), la lista nocturna §3o y el Registro. No toca código de la app. Carga asumida: una persona
corriendo la prueba en la PC.

**Should fix**

1. **Los dos clics de SUPERFICIE pueden seguir en ✗ aunque se arregle H-85** (`scripts/prueba_ui/pieza_extruir_espacios.py:70-84`)
   - **What this is:** La prueba hace clic en el centro del rectángulo «Rect» (20×10) y en la tapa de la caja con el filtro de Extruir superficie.
   - **Problem:** Con toda la escena en pantalla, el borde del rectángulo y la arista de la caja quedan a pocos píxeles del clic, y el visor prefiere curvas y aristas dentro de 9 px (TXT-9). Aunque el filtro sume perfiles y caras, el clic puede devolver el borde y la prueba sigue roja.
   - **Fix:** Crear en la pieza un rectángulo y una caja grandes (200 mm) y hacer clic en su centro, lejos de todo borde.
   - **If we skip it:** Quien arregle H-85 ve la pieza en rojo y no sabe si su arreglo anda.

Verdict: fix 1 first.
Not checked: las capturas no se miraron a ojo (el filtro de contexto bloquea imágenes).

Aplicado después de la revisión: la pieza suma «Grande» y «Losa» y un control (con el filtro de Extruir sólido esos
clics eligen perfil y cara: OK). Re-corrida en minimizada: 18 comprobaciones, 4 ✗ de la app.

### Lo que no se pudo verificar (⚠)

- ⚠ Fusion real no se abrió: B-206 y la conicidad de la delgada abierta (H-84) se apoyan solo en la ayuda.
- ⚠ Las capturas `evidencias/ui_2026-11-05/capturas/extruir_*.png` no se miraron a ojo: el filtro de contexto de esta
  sesión no deja leer imágenes. El botón Aceptar se comprobó por geometría.
- ⚠ La pieza nueva corrió solo en `--ventana minimizada`; no corrieron la suite completa ni la prueba de humo (las
  corre el coordinador).
- ⚠ Pulsar/Tirar sobre un perfil y Objetos para cortar «# cuerpos» al editar no se probaron.
