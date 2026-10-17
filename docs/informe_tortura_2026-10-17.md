# Informe de prueba de tortura — 2026-10-17

Qué se hizo: se diseñó **a mano, con la app abierta en modo en vivo** (puente MCP, OmniCAD 0.1.2), un reductor de
engranajes completo, y después se castigaron las herramientas con valores extremos y archivos hostiles en
procesos aparte (con tope de tiempo). Este archivo es la lista de trabajo para corregir los bugs después.

- Modelo de la prueba: `evidencias/tortura_2026-10-17/reductor_tortura.omnicad` (53+ pasos, 37 cuerpos). No se sube a git.
- Captura de la ventana: `evidencias/tortura_2026-10-17/ventana_final.png`.
- Exportaciones de prueba: `evidencias/tortura_2026-10-17/export/` (STEP, STL, 3MF, OBJ, PLY, IGES, BREP, GLB, SVG, DXF, BOM).
- Scripts para reproducir: `evidencias/tortura_2026-10-17/scripts/` (`medir_autoint.py`, `medir_hlr.py`, `repro_ref2.py`,
  `fuzz_ops.py`, `fuzz2.py`, `fuzz3.py`, `graph_stress.py`, `roundtrip.py`, `foto_ventana.ps1` que captura la ventana Qt).
  Se corren con el Python del venv (`clon/.venv/Scripts/python.exe`), cada caso en su proceso y con tope de tiempo.

## Estado de las correcciones (2026-10-17, misma sesión)

Tests de cada uno: `clon/tests/test_hallazgos_tortura.py` (más `test_api_ensamble.py` y `test_recuperados.py`).

Verificado en vivo con el mismo reductor (app abierta con `--puente`, con autoguardados pendientes y sin diálogo modal): `check_geometry` de los 37 cuerpos respondió; `export_hidden_line_svg` de la Caja terminó en ~20 s con el método rápido y el aviso. pytest 2784 OK, humo TODO OK, ruff limpio.

| ID | Estado | Qué se hizo |
|---|---|---|
| T-01 | **Corregido** | `nucleo/aislado.py`: las formas con caras B-spline (roscas, solevados) hacen la autointersección en un proceso aparte que se mata a los 10 s por cuerpo y 30 s en total; queda `self_intersections: null` y el aviso `self_intersection_skipped`. La ventana sigue bloqueada hasta ese tope (≤ 30 s), ya no 11 min. **No hecho:** un tope general para cualquier herramienta de lectura: el kernel no se puede cortar desde Python, solo aislando cada caso. |
| T-02 | **Corregido** | `export_hidden_line_svg(method="auto"\|"exact"\|"fast")`: el exacto de una forma libre corre aparte con tope de 15 s y, si no termina, sigue con el rápido y lo avisa (Caja: 19 s con respaldo, antes >10 min). También protege la vista de dibujo (`nd.proyectar`). |
| T-03 | **Corregido** | Las referencias nuevas guardan su posición entre las subformas del cuerpo (`indice` / `de`); si la firma geométrica no alcanza y la topología es la misma, vale la que ocupa esa posición. Los dos casos del informe pasan (ancho 155–160; boss de 46,5 a 10 mm). Las referencias viejas (sin posición) siguen como antes. |
| T-04 | **Adentro corregido; afuera diagnosticado** | El plan B interior sigue funcionando. Se probaron uniones y tolerancias para outside sin encontrar una salida robusta; ahora el error identifica las B-spline y propone dos solevaciones + `boolean_operation(cut)`. Test de rollback y mensaje. |
| T-05 | **Corregido con respaldo** | Se mantienen los avisos. En auto, join detecta volumen sumado con área interna intacta o cáscaras aún separadas que comparten vértices; reintenta con B-rep, que elimina tapas con triangulaciones diferentes. Límite del respaldo: 50.000 triángulos por entrada; regenera grupos. Tests de esfera partida por plano horizontal e inclinado, y por API. |
| T-06 | **Corregido** | Tope de 1000 caracteres y 10 m de altura (`Boceto.agregar_texto` y `edit_text`). El costo por letra (7–13 ms, está en la detección de perfiles) no cambió. |
| T-07 | **Corregido** | `parametros.evaluar` rechaza longitudes de más de 1 km y ángulos de más de 1e6° (cubre `set_parameter`, `extrude`, `move_body`); mínimo 1e-4 mm en `fillet` y `chamfer`; aviso si un parámetro de longitud queda negativo. `create_gear(module=1000)` es válido (3 m), no se tocó. |
| T-08 | **Corregido** | `proyecto._json`: JSON roto o anidado a más no poder → `INVALID_PROJECT`. |
| T-09 | **Corregido** | `create_joint` y `create_as_built_joint` avisan que el componente ya tenía otra unión (nombrándola). |
| T-10 | **Corregido** | Con `curves=true`, un contorno de menos de 12 vértices queda polilínea (el spline cerrado por 4–8 vértices se pasaba de largo). `invert=true`: 45 × 30 exacto. |
| T-11 | **Corregido** | `drive_joint` sobre una unión que sigue un vínculo ya no guarda el valor ignorado; `motion_study` lista también al componente que sigue el vínculo. |
| T-12 | **Corregido y probado** | `reached` usa tolerancia 1e-3 mm. Caso determinista sin simular solver: extremo de una línea horizontal de 10 mm, inicio fijo y largo acotado; destino 10,0005 → true, 10,002 → false. Ayuda actualizada con el umbral. |
| T-13 | **Corregido** (mensaje) | Si el vaciado falla y la cara quitada tiene un chaflán o empalme más angosto que el espesor, el mensaje dice «hacé el chaflán o el empalme DESPUÉS del vaciado». El kernel no puede desfasar ese bisel. |
| T-14 | **Corregido** | `insert_file` acepta `.brep`/`.brp`. El 3MF exportado lleva un objeto por cuerpo; al traerlo entra como UN cuerpo de malla con un grupo por objeto (así lo documenta el lector) y `insert_file` avisa cómo separarlo (`separate_mesh by=face_groups`). |
| T-15 | **Corregido** | Con `--puente` la app arranca con un mensaje en la barra («Hay N documento(s) recuperable(s)») en vez del diálogo modal; «Archivo › Recuperar documentos…» sigue abriéndolo. |
| T-16 | **Corregido** | `export` con ruta vacía o de carpeta → `INVALID_ARGUMENTS`; DXF con `nan`/`inf`/coordenadas de más de 1 km → `IMPORT_FAILED` con mensaje claro; copias numeradas («X (copia)», «X (copia 2)»…, sin «(copia) (copia)»). Un paso que se llama igual que un cuerpo no es ambiguo (cada herramienta busca en lo suyo): no se cambió. |
| T-17 | **Corregido** salvo uno | `-0.0` → `0.0`; `-(-4)` → `4`; `realize_copies` cuenta solo las copias de su paso; la ayuda de `remesh` aclara que `density` no garantiza más triángulos. **No se cambia** `"18.0"`: es el formato de las expresiones numéricas y 15 tests lo fijan. |
| T-18 | **Acelerado en Rust** | Rasterizador/z-buffer, visibilidad y SSAO por PyO3, con referencia numpy y `OMNICAD_SIN_RUST=1`. Mediana API 900×640: caja 2,129 → 1,139 s; reductor de 37 cuerpos 4,928 → 4,313 s. PNG antes/después byte-idénticos; seis pruebas de paridad. Detalle abajo. |

### Continuación: los seis pendientes (2026-10-17)

1. **Render CPU.** Perfil por `api.llamar`, tres corridas por modelo, misma vista iso e iluminación por defecto.
   Script: `evidencias/tortura_2026-10-17/scripts/perfilar_render.py`; PNG, perfiles cProfile y resúmenes en
   `render_antes/` y `render_despues/`. Rasterización de la caja: 0,855 → 0,050 s (17×); SSAO 0,381 → 0,058 s;
   visibilidad 0,260 → 0,105 s. El tiempo total baja 47 % en la caja y 12 % en el reductor; no se promete 17× para
   la llamada entera. Rust 1.99.1 ya estaba instalado; el usuario autorizó maturin (1.15.0 en el venv) y crates.
   Código: `clon/rust/`, `omnicad/nativo.py`, tres derivaciones internas de `render_cpu.py`; API sin cambio de firma.
   SHA-256 PNG caja: `f7a53f9da888608e7aa519b211c0307543bef93be56830950c1f326f76c6efa2`;
   reductor: `dc87b5e17196be112bb2575f5af7c93c9dd1f79e49bbce60eda0969d25de9e84` (iguales antes y después).
2. **Shell outside.** 27 combinaciones: MakeThickSolid/MakeOffsetShape/forma invertida × Arc/Intersection/Tangent ×
   tolerancias 1e-7/1e-5/1e-3, ninguna válida. Engrosar la cavidad interior llegó a dar un sólido válido pero con
   medidas/aberturas distintas: descartado. No se entrega una pared equivocada como arreglo. Evidencia:
   `vaciado_exterior.json` y `scripts/probar_vaciado_exterior.py`.
3. **Ejecutable empaquetado probado.** PyInstaller 6.22.3, receta `instalador/omnicad.spec`, salida separada
   `instalador/dist/tortura_20261017/OmniCAD/`. Primer build agotó los 3 GB del turno por reservas de OpenBLAS;
   con `OPENBLAS_NUM_THREADS=1` terminó (214 s). Bug real corregido: desde CLI/MCP, `sys.executable` es SU ejecutable,
   que no atiende `--tarea-aislada`; ahora se llama al `OmniCAD.exe` vecino. Test para las tres entradas.
   `omnicad-cli.exe run scripts/verificar_empaquetado.py --json` (ruta completa bajo evidencias): frozen=true,
   Rust disponible, dos hijos reales de OmniCAD.exe. Perno Ø10×12 con M10×1,5 clase 6g, longitud 6: válido, estanco,
   0 autointersecciones, 0 errores/avisos. SVG 65.317 bytes: el exacto se cortó a los 15 s, rápido correcto y aviso.
   No se ejecutó el asistente Inno ni se reemplazó la app instalada. El primer caso de sondeo M4 a largo completo
   falló en la construcción de la rosca, antes del aislamiento; se usó el caso M10 ya cubierto por la suite.
4. **Contacto coplanar de mallas.** Repro limpia: esfera teselada partida y vuelta a unir. Antes quedaban ambas
   tapas (área 1826,001 mm²); respaldo B-rep: 1215,896 mm², volumen 3942,877 mm³ conservado, una cáscara estanca.
   Se prueba también un plano (1,1,1), que conserva parte de las tapas aunque el área total baja un poco.
   Merge mantiene su significado; join con motor manifold explícito no activa el respaldo automático.
5. **HLR: medido y diferido.** Tres vistas del mismo solevado: frontal 0,016 s directo / 0,954 s aislado;
   superior 0,006 / 0,932; derecha 0,008 / 1,102. Evidencia `hlr_antes.json` y `scripts/medir_hlr_pendiente.py`.
   El arranque domina, pero un hijo persistente ahorra como máximo unos 2 s en una hoja de tres vistas tras pagar
   el primer arranque. Decisión de esta tanda: conservar hijos descartables; el persistente retendría OpenCascade
   en memoria (~185 MB del perfil previo) y requiere protocolo, cierre de la app, detección de huérfanos y reinicio
   tras fallo/timeout, también en la app sin consola. Retomar si se mide un flujo de muchas vistas donde ese costo
   absoluto justifique mantener otro proceso vivo. No se implementó ni se declara una aceleración del HLR.
6. **Reached.** Test determinista `test_t12_reached_distingue_un_residuo_submilimetrico_de_un_destino_imposible`.
   Comprueba el umbral actual y conserva la posición acotada, sin depender de un residuo fortuito de scipy.

**Verificación final de esta continuación (salida real):**

```text
ruff check .
All checks passed!

pytest -q --showlocals  (con turno.py --plazo 3000)
2798 passed, 8 warnings in 879.57s (0:14:39)

OmniCAD.py --prueba-humo  (con turno, PYTHONIOENCODING=utf-8)
Resultado: TODO OK — archivos en C:\Users\mosos\AppData\Local\Temp\omnicad_humo_gvgngpzf

cargo clippy -- -D warnings
Finished `dev` profile [unoptimized + debuginfo] target(s) in 1.92s

cargo test
test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
```

La paridad Rust se prueba desde Python: `tests/test_render_nativo.py`, seis pruebas, todas ejecutadas (no
salteadas) en esta PC. Primera suite completa: `1 failed, 2797 passed, 8 warnings in 1010.96s`;
`test_dev.py::test_run_checks_marca_sus_subprocesos` recibió -1 al intentar arrancar un subproceso. Su archivo
aislado dio `29 passed in 29.27s`; luego la suite completa pasó sin modificar código ni tests para esa falla.
La causa de ese primer fallo no quedó confirmada. Sigue el mensaje residual conocido de OCC
«File was not written with this version of the topology», sin afectar el código de salida verde.
Doc regenerada: 185 herramientas; numstat normal y sin finales de línea coinciden. Ponytail-review sin
hallazgos bloqueantes después de ajustar la detección del contacto oblicuo y la ruta empaquetada.

**Interfaces usadas (firmas públicas conservadas):**

- `get_viewport_image(sesion, view="iso", width=640, height=480, bodies=None, fit=True, direction=None,
  lighting="three_point")`: PNG; selecciona Rust disponible o numpy sin opciones nuevas.
- `shell(sesion, body, faces, thickness, direction="inside")`: mismo vaciado; error accionable para outside B-spline.
- `combine_meshes(sesion, target, tools, operation="join", keep_tools=False, name=None)`: mismo comando;
  respaldo B-rep del núcleo para el contacto no soldado.
- `move_sketch_point(sesion, point, x, y, sketch=None)`: mismo movimiento; umbral de reached explícito y probado.
- `combinar(mallas, *, operacion="unir", motor="auto")`: punto único del núcleo para UI/timeline/API;
  el respaldo solo entra en automático, con los límites descritos arriba.
- `nativo.disponible()`: selección interna del módulo opcional para el render; devuelve el módulo o None.

## Qué se diseñó (cobertura)

Caja de aluminio con vaciado, chaflán, 4 bosses con **agujeros roscados M4 modelados** y patrón; ejes y rodamientos
(cortes simétricos) sobre bocetos por especificación; **par de engranajes de evolvente** (z16/z24) con componentes,
uniones y vínculo de movimiento; tapa con ranuras, hexágono, elipse y spline, agujeros abocardados, **texto
paramétrico** `{ancho}`, asa por **barrido**; **tornillos** con asistente de ejes + rosca modelada + patrón;
perilla por **revolución** (eje como línea central); embudo por **solevación**; esfera y cilindro con booleanas;
simetría, patrón rectangular/circular/en puntos/en ruta/multitransformación (con copias ligeras y `realize_copies`);
desmoldeo, desfase de caras y aristas, quitar empalmes; **chapa** (pestaña base, 2 pestañas de arista, dobladillo,
agujeros, patrón plano, DXF, desplegar/replegar); **mallas** (teselar, reducir, suavizar, remallar, vaciar, corte de
plano, combinar, limpiar, reparar); grafo (`run_graph` y `bake_graph` paramétrico); calcomanía; SVG/DXF/imagen
vectorizada; cremallera y rueda de cadena; materiales, aspectos, lista de materiales; grupos del navegador;
uniones deslizante/rótula/revolución con límites y estudio de movimiento; exportación y reimportación en 8 formatos.

Todo lo anterior anduvo, con los volúmenes que cierran contra la cuenta a mano (se verificó Pappus en la revolución,
volumen de agujeros, texto, barrido, chapa y desarrollo plano). Los 37 cuerpos salieron `valid` y `closed`.

## Resumen: bugs por prioridad

| ID | Gravedad | Qué pasa | Dónde |
|---|---|---|---|
| T-01 | **ALTA** | `check_geometry` (autointersección, por defecto) cuelga la app más de 11 min con roscas modeladas | `nucleo/revision.py:279`, `api/herramientas_revision.py:93` |
| T-02 | **ALTA** | `export_hidden_line_svg` cuelga la app más de 10 min con roscas modeladas | `api/herramientas_vectores.py:585`, `nucleo/dibujo.py:305` |
| T-03 | MEDIA | Las referencias persistentes se pierden con cambios de cota de ~25 % (chaflán de borde tras un vaciado) o al editar la altura de un cilindro (agujero posterior) | `nucleo/referencias.py:168` |
| T-04 | MEDIA | `shell` falla en un solevado cuadrado→círculo con cualquier espesor | `nucleo/solidos_modificar.py:509`, `api/herramientas_modificar.py:91` |
| T-05 | MEDIA | `repair_mesh`/`clean_mesh` devuelven `ok` sin aviso aunque la malla queda abierta o no manifold | `api/herramientas_malla.py:168` y `:184` |
| T-06 | MEDIA | `add_text` con 100 000 letras no termina en 60 s (sin tope de largo) | `api/herramientas_vectores.py:174` |
| T-07 | MEDIA | Sin validación de rango: `move_body` 1e300, `set_parameter` 1e308, `extrude` 1e12, `fillet` 1e-9 | `api/herramientas_solido.py:128` y `:869`, `api/herramientas_parametros.py:64` |
| T-08 | BAJA | `open_document` con JSON profundo: `INTERNAL_ERROR` con `RecursionError` pelado | `io_archivos/proyecto.py:172` |
| T-09 | BAJA | `create_joint` no avisa si el componente ya tiene otra unión (la nueva pisa a la vieja en silencio) | `api/herramientas_ensamble.py:432` |
| T-10 | BAJA | `trace_image` con `invert=true` y tinta que toca el borde da splines que se pasan (53×45 en vez de 45×30) | `io_archivos/vectorizar.py:92` |
| T-11 | BAJA | `drive_joint` sobre unión seguida por vínculo guarda el valor pedido aunque lo ignora; `motion_study` no lista al seguidor | `api/herramientas_ensamble.py:557` y `:683` |
| T-12 | BAJA | `move_sketch_point` dice `reached:false` aunque el punto quedó exacto donde se pidió | `api/herramientas_vectores.py:836` |
| T-13 | BAJA | `shell` tras un chaflán previo falla y la pista culpa a «cortes o agujeros» | `nucleo/solidos_modificar.py:509`, `api/herramientas_modificar.py:91` |
| T-14 | BAJA | `insert_file` no acepta `.brep` (export y `open_document` sí); 3MF de 2 cuerpos reimporta como 1 malla | `api/herramientas_documento.py:225` |
| T-15 | BAJA | Tras matar la app queda el diálogo «Documentos recuperados», que bloquea el puente (`APP_BUSY`) hasta que alguien hace clic | UI |
| T-16 | BAJA | Mensajes y nombres: `export` con ruta vacía dice `FILE_EXISTS`; `insert_dxf` filtra «cannot convert float NaN to integer»; nombres repetidos | varias |
| T-17 | BAJA | Cosméticos: `-(-4)`, `18.0`, `-0.0`, `realize_copies` cuenta 6 en vez de 3, `remallar density=2` baja triángulos | varias |
| T-18 | BAJA | Rendimiento: `get_viewport_image` 6–19 s; `get_scene_info`/`open_document` devuelven todo sin filtro | API |

---

## T-01 · ALTA — `check_geometry` cuelga la app con roscas modeladas

- **Repro (en vivo):** documento con 20 cuerpos (engranajes, tornillos con rosca M4 modelada, caja con 8 agujeros
  roscados M4 modelados). `check_geometry` sin `body`.
- **Qué pasó:** el MCP devolvió `APP_NOT_RESPONDING` a los 120 s, pero la **ventana quedó «No responde»** (CPU ~0,8 núcleos)
  más de 11 minutos, sin cancelación; la llamada siguiente (`check_printability`) quedó en cola. Hubo que matar el proceso:
  se perdieron los cambios sin guardar.
- **Medido por cuerpo, en proceso aparte** (`self_intersection=true`, tope 90 s):

  | Cuerpo | sin autointersección | con autointersección |
  |---|---|---|
  | Caja (4 agujeros M4 modelados) | 6,2 s | **> 90 s** |
  | Tornillo (rosca M4 modelada) | 1,3 s | **> 90 s** |
  | Tapa, Embudo, Engranajes, Soporte, Perilla | 0,01–0,8 s | 0,01–1,7 s |

- **Causa:** `_autointersecciones` (`nucleo/revision.py:279-300`) corre `BOPAlgo_ArgumentAnalyzer.Perform()` en el hilo de la
  interfaz, sin tope de tiempo ni progreso. Las caras helicoidales de la rosca (decenas de caras B-spline pegadas) lo hacen explotar.
- **Es la misma familia que el cuelgue del 2026-10-09** (`PROJECT_LOG.md`, Hallazgos: `execute_code` sin tope congeló la app 12 min).
  `execute_code` ya tiene `CODE_TIMEOUT` (verificado hoy: corta a los 3 s y la app sigue viva); las herramientas de análisis no.
- **Arreglo sugerido:** (1) correrlo fuera del hilo de la UI con tope y cancelación (`Message_ProgressRange` o proceso aparte);
  (2) por defecto saltear la autointersección en cuerpos con roscas modeladas y avisarlo en `avisos`;
  (3) un tope global para toda herramienta de solo lectura en vivo (la app no puede quedar congelada por una lectura).
- **Test a agregar:** documento con un agujero roscado modelado y `check_geometry` con tope de 30 s.

## T-02 · ALTA — `export_hidden_line_svg` cuelga la app con roscas modeladas

- **Repro (en vivo):** `export_hidden_line_svg(path, bodies=["Caja"], view="top")` → `APP_NOT_RESPONDING` a los 120 s y la app
  colgada más de 10 minutos (hubo que matarla otra vez).
- **Medido en proceso aparte** (tope 90 s): Tapa 0,4 s, Perilla 0,02 s, Soporte 0,03 s, Engranaje 0,13 s, Embudo 0,03 s;
  **Caja y Tornillo: > 90 s**.
- **Causa:** `nucleo/dibujo.py:305` `proyectar(..., metodo="exacto")` usa `HLRBRep_Algo` (exacto) y la herramienta
  (`api/herramientas_vectores.py:585`) **nunca** pasa `metodo="rapido"`, que ya existe en el código.
- **Verificado:** `proyectar(Caja, vista top, metodo="rapido")` tarda **3,2 s** (contra más de 10 min).
- **Arreglo sugerido:** parámetro `method: Literal["exact","fast"]` en la herramienta y caída automática a `fast` si el cuerpo
  tiene muchas caras o roscas; más el tope de T-01.

## T-03 · MEDIA — Referencias persistentes se pierden con cambios moderados

Dos casos reproducidos:

1. **Chaflán del borde tras un vaciado.** Caja con esquinas redondeadas por `sketch_fillet` (`radio = ancho/20`), extruida,
   `shell` de la tapa (4 mm) y `chamfer(">Z", 1)`. `set_parameter(ancho)`:
   120→110 OK, →145 OK, →150 OK, **→155 `REFERENCE_LOST`**, →160/170 `REFERENCE_LOST`.
   Sin el vaciado (caso D del script) aguanta hasta 200. Un parámetro de ancho que sube un 29 % rompe el chaflán.
2. **Agujero sobre la cara de un cilindro.** `create_cylinder` (boss, op6) unido a la caja vaciada, patrón de 4 bosses +
   `create_hole` en la cara superior de uno (`face="nearest:[48,33,23.5]"`) + patrón del agujero. `edit_feature(op6, {"alto": "46.5 mm"})`
   (subir la cara 26,5 mm) → `REFERENCE_LOST: Se perdió la referencia a una cara de Caja`, aunque la cara existe y solo se movió.
   Reproducido otra vez sobre el modelo guardado (boss de 46,5 mm, agujero `op24`): bajar a 40 mm OK, a 30 mm OK, **a 20 mm
   `REFERENCE_LOST` en `Agujero3`**, y volver a 46,5 mm OK. O sea: la cara aguanta ~16 mm de desplazamiento y se pierde a ~26 mm
   (≈17 % de la diagonal de la caja, 160 mm). En una placa simple de 100×100 el mismo cambio **no** falla (`escala` más grande):
   el umbral depende del tamaño del cuerpo, no de la identidad de la cara.

- **Causa:** `nucleo/referencias.py` guarda una **firma geométrica** y busca la mejor candidata (`resolver`, umbral 0,35 o
  «mejor < 0,5 × segunda», líneas 168-196). Con el vaciado hay dos lazos de aristas casi iguales (borde interior y exterior) y la
  regla de ventaja clara falla; en el caso del cilindro la cara se mueve más que el umbral.
- **Arreglo sugerido:** guardar la **historia topológica** de cada operación (`BRepTools_History` / `Modified()` de cada
  algoritmo) y resolver por identidad; la firma geométrica queda de respaldo. Mientras tanto, mejorar el mensaje: decir qué cota
  provocó el cambio y ofrecer volver al valor anterior.
- **Repro mínimo:** `repro_ref2.py` (caso E). Sale en 0,3 s por caso.

## T-04 · MEDIA — `shell` imposible en un solevado cuadrado→círculo

- `loft` de un rectángulo 24×24 (z=0) a un círculo r=7 (z=30): cuerpo válido, estanco (`check_geometry` OK, 7 caras).
- `shell` con `[>Z,<Z]` a 1,2 y a 0,6 (`inside`), 1,2 `outside`, solo `>Z` a 1,2 y a 0,2, y `faces=[]` a 1: **todos**
  `OPERATION_FAILED`, con mensajes distintos pero ninguno útil.
- **Arreglo sugerido:** si el kernel falla en una cara B-spline, probar el desfase por `BRepOffsetAPI_MakeOffsetShape` con
  `GeomAbs_Intersection`, o sugerir en la pista «solevar el perfil interior y restar con `boolean_operation`» (que sí anda).

## T-05 · MEDIA — Las herramientas de reparación de malla dicen `ok` sin avisar

Cadena: `tessellate` → `reduce_mesh` → `smooth_mesh` → `remesh` ×2 → `shell_mesh` (avisó: 365 caras invertidas) → `plane_cut_mesh`
(split) → `combine_meshes(join)` de las dos mitades → `clean_mesh(min_shell_fraction=0.001)` → `repair_mesh`.

- `combine_meshes(join)` de dos mitades que comparten el plano de corte: **14 cáscaras, 17 triángulos degenerados**, área mayor
  (3446 contra 3318: quedaron caras internas). El volumen sí cerró.
- `clean_mesh`: 1 cáscara pero **`closed:false`, 9 bordes abiertos y 30 aristas no manifold**.
- `repair_mesh(stitch_and_remove)`: bordes 9→0 pero degenerados **0→5**, no manifold **30 sin cambio**, `avisos` vacío.
- `repair_mesh(rebuild)`: 6 bordes abiertos, 33 no manifold, `ok:true`, `avisos` vacío.
- **Arreglo sugerido:** si el resultado no es cerrado/manifold, `avisos` tiene que decirlo (hoy solo lo hacen suavizar, remallar y
  vaciar); y la unión de mallas debería soldar las caras coplanares del contacto.
- (Parte de una entrada mala —vaciado autointersecado con aviso—, pero un `ok` mudo sobre una malla rota es el problema.)

## T-06 · MEDIA — `add_text` sin tope de largo

- `add_text(text="W"*100000, height=5)`: **> 60 s sin terminar** (proceso aparte, tope 60 s). En vivo congelaría la ventana.
- Escalado medido (la letra repetida «W», `fuzz3.py`): 100 letras 1,0 s · 1000 letras **13,4 s** · 3000 letras **44,8 s**.
  Es lineal, ~14 ms por letra: 100 000 letras serían unos 25 minutos. Con 500 letras (un párrafo corto) ya son ~7 s de ventana congelada.
- **Arreglo sugerido:** (1) cachear el contorno de cada glifo por (fuente, carácter, estilo): una letra repetida se calcula una sola
  vez; (2) tope de caracteres (p. ej. 5000) con `INVALID_ARGUMENTS`; (3) el cálculo fuera del hilo de la UI.

## T-07 · MEDIA — Validación de rango incompleta

Las primitivas rechazan más de 1 000 000 mm («1 km») con un mensaje claro, pero:

| Llamada | Resultado |
|---|---|
| `extrude(distance=1e12)` | `ok:true` |
| `move_body(translate=[1e300,0,0])` | `ok:true` |
| `move_body(rotate=[1e9,1e9,1e9])` | `ok:true` |
| `set_parameter("p", "1e308 mm")` | `ok:true` |
| `fillet(radius=1e-9)` | `ok:true` |
| `set_parameter(alto, "-10 mm")` | `ok:true`: la caja se extruye hacia −Z, solo avisos de unión |
| `add_text(height=1e6)` | `ok:true` |
| `create_gear(module=1000, teeth=3)` | `ok:true` |

- **Arreglo sugerido:** el mismo tope de 1 000 000 mm en `extrude`, `move_body`, `set_parameter` (longitudes) y texto; avisar
  cuando un parámetro de longitud pasa a negativo.

## T-08 a T-18 — baja prioridad

- **T-08** `open_document` con una receta de JSON anidado a 100 000 niveles: `INTERNAL_ERROR` con
  `RecursionError: maximum recursion depth exceeded while decoding a JSON array`. Sin caída, pero tendría que ser
  `INVALID_PROJECT` (`io_archivos/proyecto.py:172`, envolver `json.loads` en `except RecursionError`).
- **T-09** `create_joint(rigid/revolute)` entre `Perilla2` y el embudo, cuando `Perilla2` ya tenía una rótula
  (`RotulaPerilla2`, valores 20/35/50): la unión nueva movió el componente a su marco y la rótula sigue mostrando
  `rotation 20/35/50` que no se cumplen. Ningún aviso de sobrerrestricción.
- **T-10** `trace_image(logo.png, width=45, curves=true)`: con `invert=false` el bbox es 45,09×27,83 (bien); con `invert=true`
  (el contorno es el borde de la imagen) sale **53,37×45,02** y con coordenadas negativas (−3,12): los splines de un rectángulo
  de 4 vértices se pasan de largo. Falta detectar esquinas en el borde de la imagen.
- **T-11** `drive_joint(op18, rotation=6)` sobre una unión que sigue a un vínculo: avisa, `moved_components=[]`, pero
  `get_assembly` queda con `requested.rotation="6.0"` mientras `values.rotation=-10`. Si después se suprime el vínculo, la unión
  usa 6. `motion_study` lista solo el componente de la unión recorrida; `drive_joint` lista los dos.
- **T-12** `move_sketch_point(point=34, x=235, y=30)` sobre el centro de un círculo con tres tangencias: `reached:false`, pero
  `get_sketch` muestra el punto exactamente en (235, 30) (las rectas se movieron para seguirlo). La bandera es engañosa.
- **T-13** `chamfer(">Z", 1.5)` y después `shell(">Z", 4)` → `OPERATION_FAILED «¿cortes o agujeros que cruzan la cara
  quitada?»`. La causa era el chaflán; la pista debería decir «hacé el chaflán después del vaciado» (que sí anda).
- **T-14** `export` escribe `.brep`/`.brp` y `open_document` los abre, pero `insert_file` responde
  `UNSUPPORTED_FILE_TYPE`. Y `engranajes.3mf` (2 cuerpos exportados) se reimporta como **1** cuerpo de malla.
- **T-15** Tras matar la app, al reabrirla aparece **«Documentos recuperados»** y mientras esté abierto cada llamada del
  MCP responde `APP_BUSY`; hubo que hacer clic con el ratón. La lista incluye autoguardados de otros documentos del usuario
  (no se tocaron). Ideal: una herramienta `list_recoverable_documents` ya existe; falta poder descartar o ignorar el diálogo.
- **T-16** `export(path="")` → `FILE_EXISTS «Ya existe el archivo: .»` (debería ser `INVALID_ARGUMENTS`); `insert_dxf` con
  `nan` → `INVALID_GEOMETRY «cannot convert float NaN to integer»` (mensaje de Python sin traducir); un paso nuevo se llama
  igual que un cuerpo del usuario (paso `Eje1` op27 contra cuerpo `Eje1`); copias de patrón `X (copia)` repetidas y
  `Banco (copia) (copia)`.
- **T-17** Dimensión de desfase con expresión `-(-4)`; `edit_dimension` guarda `"18.0"` aunque se pasó `18`; juntas con
  `rotation: -0.0`; `realize_copies(op73)` devuelve `realized: 6` y lista cuerpos de `op74` (otro patrón) como modificados;
  `remesh(density=2)` bajó de 568 a 494 triángulos (la ayuda dice «>1 da más») y el aviso dice «subí la densidad».
- **T-18** `get_viewport_image`: 6–7 s con 1 pieza chica y 19 s con 10 cuerpos (900×640). `get_scene_info`, `open_document`
  y `check_geometry` sin `body` devuelven decenas de KB; conviene un modo resumido para agentes.

## Lo que aguantó bien (para no volver a probarlo)

- 95 tipos de operación con parámetros vacíos o claves inventadas: **cero excepciones**, errores claros (`fuzz_ops.py`).
- Primitivas: límites de 1 km, `nan`/`inf`, toro con radios inválidos, engranajes con dientes fuera de 3–1000 o hélice > 45°.
- Parámetros: nombres inválidos/reservados (`1x`, `rad`), duplicados, circulares, `1/0`, `__import__(...)`, `9**9**9`, 5000 dígitos.
- Archivos hostiles: ZIP de 600 MB descomprimido rechazado por el tope (629 145 652 > 536 870 912); SVG con **billion laughs y
  XXE** (`file:///C:/Windows/win.ini`) rechazado; STL/PLY que mienten en el conteo, OBJ con índices imposibles, STEP basura,
  PNG roto, imagen 1×1, PNG de 8000×8000 (con mensaje claro).
- `.omnicad` con miembros `../../x`, `/abs_x` y `C:\x`: se abre y **no se extrae nada** (se verificaron las 3 rutas).
- Texto con `{__import__('os').system('calc')}`: «Expresión no permitida».
- `execute_code` con bucle infinito: `CODE_TIMEOUT` a los 3 s y la app siguió viva. 12 `undo` seguidos desde `execute_code`
  dejaron el timeline consistente.
- Rollback atómico: cada fallo de `set_parameter`/`edit_feature`/`shell` dejó el documento intacto.
- Exportación → reimportación: IGES exacto; mallas dentro de ±0,2 % por la teselación; STEP con 19 cuerpos, suma de
  volúmenes exacta (230 183,177).
- Cálculos numéricos verificados a mano: engranaje (módulo transversal, diámetros), rosca M8x1.25 (flancos y tolerancias 6g/6H),
  ajuste H7/p6 (ISO 286), cremallera y rueda de cadena (diámetro primitivo), desarrollo plano de la chapa (62,71 y 75,42 mm).
