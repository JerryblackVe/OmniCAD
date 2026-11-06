# Auditoría de Extruir en todos los espacios (2026-11-05)

Pedido de Gerardo (2026-11-05): auditar la herramienta Extruir y todas sus opciones, comparar con Fusion 360 y buscar
bugs, mal funcionamiento y faltantes en SÓLIDO, SUPERFICIE, PLÁSTICO, CHAPA y el resto de los espacios donde exista.
Lo ejecuta una sesión aparte (Opus 5, esfuerzo alto). Los prompts de la auditoría y de los arreglos ya se cerraron (2026-11-05).

## Resultado (2026-11-05)

Extruir anda bien en lo común: 50 casos por la API y 18 comprobaciones en la ventana dan los números de la cuenta a
mano. Se encontraron **2 bugs** (B-205, B-206), **5 faltantes** (H-81 a H-85) y **2 mejoras** (H-86, H-87). No se
tocó código de la app. Evidencia: `evidencias/ui_2026-11-05/` (`sondas_extruir.py` y sus salidas `.txt`, el registro
`extruir_espacios.json` y las capturas).

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
| Enter, Esc, reabrir el paso, deshacer, rehacer, guardar y reabrir | ✔ | ✔ | ✔ | pieza `extruir_espacios`; `guardar_y_reabrir` da igual |
| Panel en 1024×640 y 800×520 (delgada + dos lados + cortar + desfase) | ✔ | — | ✔ | Aceptar dentro de la ventana en los dos tamaños |
| PLÁSTICO: espesor de la regla en la delgada | ≈ | ≈ | Mejora | H-87: anda solo escribiendo `PlasticThickness` |
| SUPERFICIE: curva abierta, perfil cerrado, cara plana | ✘ perfil y cara | ✔ | Falta en la ventana | H-85; API: 200 / 600 / 600 mm² |
| SUPERFICIE: Simétrica, Dos lados, Al objeto, Todo, Conicidad | ✔ | ✔ | ✔ | 400 / 300 mm², 700 mm² hasta z=35, conicidad 10° = 203,09 mm² |
| SUPERFICIE: Al objeto con Extend / Chain Faces | ✘ | ✘ | Falta | H-82 |
| Botón Extruir en SÓLIDO, SUPERFICIE, PLÁSTICO; ninguno en CHAPA | ✔ | — | ✔ | pieza `extruir_espacios` |

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

What this change does: Agrega una pieza de prueba de ventana para Extruir (`extruir_espacios.py`, sumada a
`todo.py`), el informe de auditoría con matriz y salida de `ponytail-audit`, y anota los hallazgos en el seguimiento
(B-205, B-206, H-81 a H-87), la lista nocturna §3o y el Registro. No toca código de la app. Carga asumida: una persona
corriendo la prueba en la PC.

**Should fix**

1. **Los dos clics de SUPERFICIE pueden seguir en ✗ aunque se arregle H-85** (`scripts/prueba_ui/extruir_espacios.py:70-84`)
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
- Capturas `evidencias/ui_2026-11-05/capturas/extruir_*.png` miradas por el coordinador: Aceptar entra en 1024×640 y
  800×520; las cajas de valor de la distancia y del desfase se pisan (B-207).
- ⚠ La pieza nueva corrió solo en `--ventana minimizada`; no corrieron la suite completa ni la prueba de humo (las
  corre el coordinador).
- ⚠ Pulsar/Tirar sobre un perfil y Objetos para cortar «# cuerpos» al editar no se probaron.

## Informe de arreglos (OpenCode)

Ejecutado el 2026-11-05 sobre `main` (sin commitear). Los cuatro bugs se trabajaron de a uno, en el orden del prompt,
cada uno con su verificación antes de pasar al siguiente. Regla de Fusion leída en la ayuda oficial antes de cada
arreglo (`scripts/fusion_docs.py ver "Extrude reference" -s fusion-model` y `Extrude a solid body`).

### B-205 · «Dos lados» con distancia negativa — **Resuelto**

- **Qué dice la ayuda:** `Two Sides: Creates a unique extrusion on each side of the profile plane`. Cada lado va al
  suyo; el número es una magnitud hacia ese lado, no un selector de sentido (el sentido se invierte con «Invertir
  dirección»). La ayuda no menciona valores negativos en esta dirección, así que la regla se decidió por lo que ya
  hacían los dos núcleos y por la pieza `extruir_espacios`, que esperaba 3000 mm³.
- **Qué cambió:** una sola regla — magnitud por lado — en los dos sitios que discrepaban:
  `clon/omnicad/timeline/operaciones.py:1239` (`_extrusion_basica`: `abs(d1)` y `abs(d2)`) y
  `clon/omnicad/ui/comando.py:1632` (la previa en arrastre: `a, b = -abs(d2), abs(d1)`). `extruir_avanzado`
  (`nucleo/solidos_crear.py:595`) y `_altos` (`nucleo/superficies.py:278`) ya usaban `abs`: no se tocó. Ventana, MCP
  (`extrude`, `create_surface_extrude`) y CLI salen por el mismo `OpExtrusion`, así que dan lo mismo.
- **Test:** `clon/tests/test_api_opciones_solido1.py::test_dos_lados_con_distancia_negativa_da_lo_mismo_con_y_sin_conicidad`
  (10/−5 y −10/5, con y sin conicidad, más la superficie).
  Salida: `10 passed in 1.49s` (antes del arreglo, esa receta daba 2000 mm³ y caja z 0..10 sin aviso).

### B-207 · las cajas de valor del Extruir se pisan — **Resuelto**

- **Diagnóstico (no era lo que decía la fila):** `_ubicar_cajas` ya rechazaba la intersección entre cajas, pero solo
  el `intersects` exacto. Con el perfil chico dentro de una escena grande — el caso de la captura — las puntas de las
  asas de «Distancia» y «Desfase de inicio» caen a pocos píxeles, y la caja siguiente se posaba a **1 px** de la
  anterior (medido con `evidencias/ui_2026-11-05/b207_sonda.py`: `separación dy=1`). Con el DPI y el encuadre reales
  ese píxel se volcaba encima.
- **Qué cambió:** `clon/omnicad/ui/manipuladores.py:61` (constante nueva `AIRE_CAJAS_PX = 6.0`) y
  `clon/omnicad/ui/manipuladores.py:1556`: al puntuar los candidatos se hincha la caja ya colocada con ese aire, así
  que una posición a 1 px deja de ganarle a una libre. La misma sonda después del arreglo: `separación dy=18`.
- **Test:** `clon/tests/test_manipuladores.py::test_las_cajas_de_dos_lados_con_desfase_no_se_pisan` (4 vistas, exige
  ≥ 6 px de aire entre cada par y al menos una vista con las tres cajas). Comprobado en las dos direcciones: con el
  arreglo pasa; con el arreglo revertido falla con `('desfase_inicio', 'distancia', -92, 2)` (2 px).
- **Captura nueva:** `evidencias/ui_2026-11-05/capturas/extruir_1024x640.png` (re-corrida por la pieza): «10 mm» y
  «0 mm» ya no se solapan.

### B-206 · Inicio › Objeto en un plano inclinado — **Parcial**

- **Qué dice la ayuda:** `Start › Object: Starts extrusion from a face or plane that you select`. La base de la
  extrusión queda sobre la cara o el plano elegido.
- **Qué cambió:** el perfil se proyecta oblicuamente sobre el plano de inicio a lo largo de la dirección de extrusión
  y esa cara es la base: `clon/omnicad/nucleo/geometria.py:269` (`geo.proyectar_sobre_plano`, transformación afín con
  `BRepBuilderAPI_GTransform`; la cara se rehace sobre el plano objetivo para que siga reconociéndose como plana).
  En sólido, `clon/omnicad/timeline/operaciones.py:1168`; en superficie, `clon/omnicad/timeline/ops_superficie.py:133`.
  Con el objeto **paralelo** se queda el camino viejo del desfase, igual que antes. Con una **cara curva** sigue el
  error claro de siempre («Elegí una cara plana o un plano…»), no queda nada mudo.
- **Test:** `test_inicio_objeto_en_un_plano_inclinado_arranca_sobre_el`: plano a 30° sobre X, rectángulo 20×10,
  distancia 10 → los vértices de la base sobre el plano (desvío < 1e-6), caja z 0..15,77 y volumen 2000 mm³ exactos;
  en superficie la misma caja; y el objeto paralelo sigue dando z mínimo 4.
- **Por qué queda en Parcial (anotado en `docs/seguimiento/bugs.md`):**
  1. **Delgada con perfil cerrado:** el desfase del contorno (`_desfase_alambre`) no resuelve sobre las aristas
     B-spline de la cara proyectada; antes daba un cuerpo que ignoraba la inclinación. Ahora avisa
     (`timeline/operaciones.py:1166`) y el test lo cubre con `falla(...)`.
  2. **Perfiles con curvas:** la proyección es exacta de posición pero OCC aproxima la elipse: círculo r5 a 10 mm con
     plano a 30° da **788,63 mm³ contra 785,40** (0,41 %) y las rectas proyectadas dejan de ser `GeomAbs_Line`
     (medido con sonda: área 91,0762 contra 90,6900 mm²). El arreglo sería convertir las aristas proyectadas con
     `GeomConvert_CurveToAnaCurve` antes de rehacer la cara; con eso se destraba también el punto 1.
  3. **Conicidad + inicio inclinado:** da «Con inclinación, la extrusión debe ser perpendicular al perfil» (antes
     ignoraba la inclinación en silencio).

### B-197 · tronco de pirámide y cono con conicidad — **Resuelto (el test tenía razón)**

- **La cuenta a mano.** Perfil cuadrado 10×10, altura 10, conicidad ±5° (ángulo respecto de la dirección de
  extrusión, plano neutro en el perfil). Cada cara lateral se corre `z·tan5°`, así que el lado a la altura z es
  `10 ± 2·z·t`, con `t = tan 5° = 0,0874887`:
  - lado que ensancha: `10 + 20t = 11,74977` → `V₁ = 10/3·(100 + 138,0572 + 117,4977) = 1185,18 mm³`
  - lado que cierra: `10 − 20t = 8,25023` → `V₂ = 10/3·(100 + 68,0663 + 82,5023) = 835,23 mm³`
  - fórmula del prismatoide `V = h/3·(A₁ + A₂ + √(A₁A₂))`, y **los dos lados son dos extrusiones independientes**:
    `V₁ + V₂ = 2020,41 mm³` ← lo que esperaba el test.
  - lo que daba la app: **2185,18 = 1000 + 1185,18**, o sea el lado 2 como prisma recto: `conicidad2` se tiraba.
- **Qué dice la ayuda:** `Two Sides: Creates a unique extrusion on each side of the profile plane` +
  `Adjust the settings in step 6 independently for each side` (paso 6 = extensión y conicidad por lado). Cada lado con
  su conicidad; el colapso no es Fusion.
- **Qué cambió:** borrado el colapso en `clon/omnicad/nucleo/solidos_crear.py:474` (`_herramienta_extrusion`): sin él
  cada lado arma su prisma con su conicidad y los dos comparten el plano neutro (el plano del perfil movido `base`),
  que era la justificación del bloque. De paso queda bien la simétrica con conicidad, antes asimétrica por el mismo
  motivo.
- **Test:** el que estaba rojo, `clon/tests/test_solidos_crear.py::test_extrusion_con_inclinacion_tronco_de_piramide_y_cono`.
  Salida: `63 passed in 37.80s` (antes: `1 failed` con `Obtained: 2185.1830153792516 / Expected: 2020.4113766548062`).

### Verificación real

```
$ .venv/Scripts/python.exe -m ruff check .
All checks passed!

$ .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe -m pytest \
      tests/test_api_opciones_solido1.py tests/test_solidos_crear.py tests/test_opciones_operaciones.py \
      tests/test_manipuladores.py tests/test_b105_panel_chico.py tests/test_api_solido.py \
      tests/test_api_superficie.py tests/test_extruir_cara.py tests/test_extruir_cara_api.py \
      tests/test_comandos.py tests/test_comandos_superficie.py tests/test_seguimiento.py tests/test_doc_agentes.py -q
934 passed in 63.41s (0:01:03)

$ .venv/Scripts/python.exe ../scripts/prueba_ui/todo.py extruir_espacios --ventana minimizada
extruir_espacios     18 comprobaciones,   2 con ✗   (extruir_espacios.log)
```

Las dos ✗ de la pieza son **H-85** (en SUPERFICIE, clic dentro de un perfil cerrado y sobre una cara plana: el visor
devuelve `None`), que no es de esta tanda. Las cuatro ✗ de la corrida de la auditoría bajaron a esas dos:
`Dos lados 10 / -5 mm: volumen 3000` ✓ y `Inicio en plano inclinado 30°: la base sigue el plano` ✓ (caja z
−0,00..15,77).

### Seguimiento y registro

Filas borradas de `docs/seguimiento/bugs.md`: B-205, B-207 y B-197 (con sus fichas de detalle). B-206 pasó a
**Parcial** con las tres cosas que faltan. Recontado: Total 28: Abierto 21 · Parcial 6 · Bloqueado 1. Se actualizaron
`docs/seguimiento/README.md`, `docs/README.md` y `PROJECT_LOG.md` (Registro + dos lecciones: la opción que se tira
deja el test rojo, y la condición de un bug de cajas es la separación en píxeles de las puntas, no el tamaño de
ventana). No se tocó `docs/agentes/herramientas.md`: ninguna firma de herramienta cambió (pasa `test_doc_agentes.py`).
No se comiteó nada.

### Salida completa de `/ponytail-review`

**Qué hace este cambio:** arregla cuatro bugs abiertos de Extruir — una sola regla para la distancia del lado 2 en
«Dos lados» (`timeline/operaciones.py:1239`, `ui/comando.py:1632`), aire entre las cajas de valor del visor
(`ui/manipuladores.py:1556`), Inicio › Objeto con el plano inclinado proyectando el perfil sobre él
(`nucleo/geometria.py:269`, usado en sólido y superficie), y cada lado conservando su propia conicidad
(`nucleo/solidos_crear.py:474`). Carga asumida: una persona o un agente, un documento (AGENTS.md).

**Should fix**

1. **La flecha de «Distancia» sigue el signo aunque el cuerpo ya no** (`ui/comandos/solido.py:101`)
   - **Qué es:** en Dos lados el asa de la distancia se dibuja hacia donde apunta el valor con signo.
   - **Problema:** con Distancia = −10 mm el cuerpo va 10 mm hacia arriba (regla nueva, magnitud) pero la flecha
     apunta hacia abajo, al lado 2. Antes el cuerpo sí bajaba, así que la flecha decía verdad.
   - **Arreglo:** `mp.Flecha("distancia", centro, n, minimo=0.0)` cuando `direccion == "dos_lados"`, igual que ya
     tiene la del lado 2 (línea 103). Una línea.
   - **Si lo salteamos:** el que teclea un valor negativo ve una flecha que no coincide con el sólido.
2. **Inicio › Objeto inclinado con perfil curvo da un volumen 0,41 % alto** (`nucleo/geometria.py:288`)
   - **Qué es:** `BRepBuilderAPI_GTransform` reconvierte hasta las rectas en B-spline; la cara se rehace plana sobre
     el plano objetivo.
   - **Problema:** círculo r5, plano a 30°, distancia 10 → 788,63 mm³ contra 785,40 (medido; la posición y la caja son
     exactas). Antes el cuerpo era exacto pero estaba mal ubicado.
   - **Arreglo:** pasar las aristas proyectadas por `GeomConvert_CurveToAnaCurve` (línea/círculo/elipse) y
     `BRep_Builder.UpdateEdge(e, c, tol)` antes de rehacer la cara; baja a cero el error y devuelve el tipo analítico
     (con eso también se destraba la delgada de perfil cerrado, hoy bloqueada con aviso).
   - **Si lo salteamos:** un cuerpo con arcos o círculos queda un pelado más gordo sin aviso. Ya está anotado en la
     fila Parcial de B-206.

**Nice to have**

3. **El aviso de la delgada con perfil cerrado es un parche de honestidad, no un arreglo** (`timeline/operaciones.py:1166`)
   - **Qué es:** con el perfil proyectado, `_desfase_alambre` parte el contorno en varios lazos y el error hablaba del
     espesor.
   - **Problema:** la combinación dejó de dar cuerpo (antes daba uno ignorando la inclinación); ahora dice «todavía no
     se combina… usá Desfase».
   - **Arreglo:** el punto 2 lo habilita de verdad; borrar entonces este `raise`.
   - **Si lo salteamos:** quien use delgada + plano inclinado tiene que pasar a Desfase a mano.

Veredicto: ship con 1 y 2 anotados (1 es una línea; 2 ya está en el seguimiento como Parcial).
Lean: −5 líneas posibles (el colapso de `_herramienta_extrusion` borrado); el `"llega"` muerto de `_recortar_hasta`
sigue ahí, fuera de esta tanda.
No comprobado: la previa en arrastre (`ui/comando.py:1632`) no tiene test — necesita visor OpenGL en movimiento.

### Lo que no pude verificar (⚠)

- ⚠ **Fusion real no se abrió** (no está en esta PC): la regla de magnitud de B-205 y el «cada lado con su conicidad»
  de B-197 se apoyan en el texto de la ayuda citada arriba, no en una corrida de Fusion. En B-205 la ayuda no dice
  nada de valores negativos; en B-197 no da la fórmula del tronco por lado.
- ⚠ **Suite completa y prueba de humo**: no las corrí (por memoria; las corre el coordinador). Quedan pendientes para
  confirmar que el colapso borrado y la proyección no mueven nada más.
- ⚠ **Previa en arrastre** (`ui/comando.py:1632`): el cambio sale de leer el código y de la coherencia con el núcleo;
  no hay test que arrastre el asa con un lado 2 negativo.
- ⚠ **DPI y encuadres distintos** para B-207: probé 4 vistas en el test y la pieza real en 1024×640 y 800×520; no barrí
  todos los encuadres posibles.
- ⚠ **Pulsar/Tirar sobre un perfil** y las demás combinaciones de la matriz (H-81 a H-87) no se tocaron.

## Revisión del coordinador y cierre (Opus)

Hecho el 2026-11-05 por una sesión de Claude Opus 5.5, encima del trabajo de OpenCode con Qwen3.8-Flash (sin `stash`, sin commitear).

### Qué cambié

1. **Regresión de la previa (B-205).** `test_previa_prisma.py::test_veinte_distancias_con_huecos_coinciden_con_el_kernel`
   fallaba en [5], [11] y [17] porque **el test tenía su propia copia** de la regla de la previa (la vieja,
   `min(0, d1, −d2)..max(0, d1, −d2)`); la previa real (`ui/comando.py`) ya usaba la nueva. Arreglo de raíz: la regla
   sale a `tramo_previa(modo, d1, d2, medida, invertir)` en `clon/omnicad/ui/comando.py` (antes de `PanelComando`) y la
   usan la ventana y el test. Así no puede volver a separarse. 20/20 OK.
2. **Flechas en «Dos lados»** (`clon/omnicad/ui/comandos/solido.py`, `Extruir.manipuladores`): cada flecha queda a
   |valor| de su lado y no cruza el cero (`minimo=0.0`; con el valor tecleado negativo el eje se da vuelta y el tope pasa a
   `maximo=0.0`, así la flecha se dibuja donde está el cuerpo y no salta a 0 al arrastrarla). Mismo gemelo en las asas de
   conicidad: en «Dos lados» ya no siguen el signo (`conicidad` hacia +n, `conicidad2` hacia −n, como el núcleo). Test:
   `tests/test_manipuladores.py::test_dos_lados_la_flecha_de_distancia_no_cruza_el_cero_y_sigue_al_cuerpo` (10 y −10 mm).
3. **B-206, aristas analíticas.** `clon/omnicad/nucleo/geometria.py`: `_arista_analitica` pasa cada arista proyectada
   por `GeomConvert_CurveToAnaCurve.ComputeCurve_s` (recta, círculo, elipse; tolerancia 1e-6 mm), con el sentido de la
   original y los mismos vértices, y `proyectar_sobre_plano` la aplica con `BRepTools_ReShape` **después** de rehacer
   la cara plana (si se hace antes, `OuterWire_s` elige mal el lazo exterior porque las aristas nuevas no traen curva
   2D: una banda de 64 mm² daba 535). Círculo r5 a 10 mm sobre plano a 30°: **785,398 mm³ exactos** (antes 788,63).
4. **B-206, delgada con perfil cerrado.** Saqué el `raise`. Proyectar la cara y después hacer la pared medía el
   espesor en el plano inclinado (pared de 0,87 mm en Y: 546 mm³ en vez de 600). Ahora la proyección se hace en el núcleo,
   después de las bandas: `extruir_avanzado(..., inicio_plano=...)` (`clon/omnicad/nucleo/solidos_crear.py`).
   `OpExtrusion` pasa el plano (`inclinado`) y solo proyecta él mismo en el camino básico
   (`clon/omnicad/timeline/operaciones.py`). Rectángulo 20×10, pared 1 al centro: 600 mm³, caja X/Y ±0,5, base sobre el plano.
5. **B-206, «Al objeto» y «Todo» con base inclinada** (hallado en la revisión): el atajo «plano paralelo = una
   distancia desde el centro» dejaba la tapa inclinada, y «Todo» no llegaba al final desde el punto más bajo de la base
   (tapa en 33,1 con la caja hasta 35). Con `inicio_plano`, el atajo se saltea y el margen de las herramientas largas suma
   la altura de la base (`holgura` en `extruir_avanzado`). Tope a z=30: caja z 0..30 y 200·(30 − 5·tan30°) mm³ exactos;
   «Todo» cortando una caja: el volumen quitado exacto.
6. **Conicidad + inicio inclinado:** sigue sin hacerse; ahora con un error claro en `OpExtrusion` («La conicidad todavía
   no se combina con Inicio › Objeto en un plano inclinado: sacá la conicidad o usá «Desfase» como inicio.») en vez del
   mensaje interno del núcleo. B-206 queda **Parcial solo por esto**.
7. **Faltante nuevo H-101:** la ayuda dice «Offset (Offset or Object start only)»: con Inicio › Objeto Fusion también
   corre el arranque; OmniCAD no. Anotado en `docs/seguimiento/faltantes.md`.
8. Seguimiento: el encabezado de `bugs.md` decía 28 (21 · 6 · 1) y hay 25 filas: 21 abiertos y 4 parciales.

### Verificación real (desde `clon/`)

```
$ .venv/Scripts/python.exe -m ruff check .
All checks passed!
$ ../scripts/turno.py -- pytest tests/test_previa_prisma.py tests/test_api_opciones_solido1.py tests/test_solidos_crear.py
    tests/test_manipuladores.py tests/test_comandos.py tests/test_api_superficie.py tests/test_gizmo_pestana.py
    tests/test_superficie_fusion.py tests/test_extruir_cara.py tests/test_extruir_cara_api.py tests/test_api_solido.py -q
353 passed in 95.75s (0:01:35)
$ ../scripts/prueba_ui/todo.py extruir_espacios --ventana minimizada
extruir_espacios     18 comprobaciones,   2 con ✗
```

Las dos ✗ de la pieza son H-85 (SUPERFICIE › Extruir en la ventana no elige perfil cerrado ni cara plana), ya anotado y
fuera de esta tanda. «Dos lados 10 / −5» da 3000 mm³ y «plano inclinado 30°» da caja z 0..15,77. Captura
`evidencias/ui_2026-11-05/capturas/extruir_1024x640.png` mirada: las dos flechas de «Dos lados», cajas «10 mm», «0 mm»
y «10 mm» separadas, Aceptar visible. `tests/test_seguimiento.py tests/test_doc_agentes.py -q`: `451 passed in 7.87s`.

### Salida de `ponytail-review` (cambios sin commitear de OpenCode con Qwen3.8-Flash + los míos)

What this change does: Extruir «Dos lados» trata cada distancia como una magnitud en el núcleo, la previa y ahora
también en las flechas. Inicio › Objeto en un plano inclinado proyecta el perfil sobre ese plano con curvas exactas, y la
delgada, «Al objeto» y «Todo» funcionan desde esa base. Las cajas de valor dejan aire entre sí y el tronco con
conicidad usa la conicidad de cada lado. Carga supuesta: una persona usando la app o un agente por MCP, de a un paso.

**Must fix**

1. **«Todo» con base inclinada no llega al final** (`nucleo/solidos_crear.py`, `extruir_avanzado`, rama `hasta_caja`)
   - **What this is:** «Todo» arma una herramienta larga desde el centro de la base hasta pasar los cuerpos por 1 mm.
   - **Problem:** con la base inclinada, el punto más bajo arranca más abajo que el centro; caja hasta z=35 y base de
     0 a 5,77: la herramienta termina en 33,1 del lado bajo y deja material sin cortar.
   - **Fix:** sumar al margen la altura de la base sobre la dirección (`holgura`), solo con `inicio_plano`.
   - **If we skip it:** un corte «Todo» deja una cuña sin cortar, sin aviso. → **Arreglado** (test con volumen exacto).
2. **«Al objeto» paralelo con base inclinada deja la tapa inclinada** (`extruir_avanzado`, rama `hasta`)
   - **What this is:** si el objeto es un plano paralelo al perfil, el código extruye una distancia fija desde el centro.
   - **Problem:** desde una base inclinada esa distancia fija hace una tapa inclinada que no toca el plano elegido.
   - **Fix:** con `inicio_plano`, ir por la herramienta larga recortada en el objeto (el camino que ya existe).
   - **If we skip it:** el cuerpo no termina en el plano que eligió el usuario. → **Arreglado** (caja z 0..30).

**Should fix**

3. **El test de la previa copiaba la regla en vez de usarla** (`tests/test_previa_prisma.py:49-57`)
   - **What this is:** el test compara la previa rápida contra el sólido del núcleo en 20 casos al azar.
   - **Problem:** tenía su propia copia de la cuenta de la previa; cuando la regla cambió (B-205) el test probaba su
     copia vieja, no la ventana, y falló aunque la ventana estaba bien.
   - **Fix:** una función `tramo_previa` en `ui/comando.py`, usada por la ventana y por el test.
   - **If we skip it:** el próximo cambio de regla vuelve a dar un rojo falso, o un verde falso. → **Arreglado** (−8 líneas).

Verdict: Ship (los tres arreglados en este cierre).
Lean: −8 líneas (la copia de la regla en el test).
Not checked: la suite completa y la prueba de humo (las corre el coordinador); Fusion real no se abrió.

### Lo que no pude verificar (⚠)

- ⚠ No corrí la suite completa ni la prueba de humo (pedido del coordinador). La previa en arrastre (`tramo_previa`)
  la cubre el test de 20 casos; un arrastre real del asa con lado 2 negativo no.
- ⚠ Fusion real no se abrió: la regla de la pared de la delgada medida en el plano del perfil sale de la ayuda
  («Thin Extrude: Extrudes a thin wall along selected … profiles»), no de una corrida.
