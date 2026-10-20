# Plan de Rust para OmniCAD

> Estado de cada ID: [docs/seguimiento/](seguimiento/README.md). Este archivo es la especificación; si un estado de acá no coincide con el seguimiento, vale el seguimiento.

Auditoría de rendimiento del 2026-10-12, pedida por el usuario: «todo lo que se pueda escribir en Rust para mejorar el
rendimiento, que se haga; a veces la app se siente laggy». Este documento dice **qué** pasa a Rust, **qué no** (y por
qué), **en qué orden** y **cómo se prueba**. Es el desarrollo del paso 6 del pendiente 10 del `PROJECT_LOG.md`, que
quedó «en espera porque los números no lo justifican»: con los bocetos y las mallas medidos, ahora sí lo justifican.

Segunda pasada (C++ y reparto entre Python, Rust y C++): [plan_cpp.md](plan_cpp.md) (resumen en la sección 10). Allí quedó además la regla
de qué lenguaje va dónde y los arreglos P14–P24 de OpenCascade.

Estado (2026-10-17): **primer módulo Rust implementado: R11**, rasterizador, sombras y SSAO del render CPU,
en `clon/rust/` con PyO3/numpy; respaldo Python. Rust 1.99.1 ya estaba instalado; el usuario autorizó instalar
maturin y descargar los crates. Medición: rasterizador 17×, API caja 2,129 → 1,139 s, reductor 4,928 → 4,313 s,
PNG byte-idénticos. Detalle en `informe_tortura_2026-10-17.md`; comandos en `clon/rust/README.md`.
El resto de este documento sigue siendo el plan de las próximas migraciones; R1 no se implementó: hoy el crate es un solo `clon/rust/src/lib.rs` (sin `src/zstd.rs`) y el descompresor sigue en Python puro (`io_archivos/zstd_puro.py`).

Estado (2026-10-19): **fases 0 y 5 hechas en Python** (sección 4): P1–P5, P10–P12, P14, P19, P22 y P6–P9, P13; P16 y
P24 quedaron cubiertos. Medido con `scripts/bench_rendimiento.py` (modos nuevos `memoria` e `interfaz`): arrastrar un
punto del polígono de 24 en el editor 56 → 14 ms, hover de 1000 aristas 62 → 1 ms, editar un paso independiente de 4
roscas M3 1,3 s → 1 ms. Faltan: P6 en un proceso aparte, P17, P18, P20, P21, P23 (detalle en `PROJECT_LOG.md`).

## 1. Resumen en una pantalla

| Verdad | Consecuencia |
|---|---|
| La geometría pesada ya es C++ (OpenCascade). En el proyecto de ejemplo (`motor_cohete`, 41 pasos) recalcular tarda 2,6–3,0 s y los pasos lentos son roscas, agujeros y booleanas. | Rust **no** acelera eso. Reescribir la app en Rust no sirve. |
| Lo que sí es Python puro y lento: el **solver de bocetos**, las **operaciones de malla** (reducir, remallar), el **descompresor Zstandard** y los **rayos contra triángulos**. | Ahí Rust gana de verdad: son bucles de intérprete sobre datos puros. |
| Buena parte del «lag» no es falta de Rust: es trabajo repetido en el hilo de la interfaz (repintado punto a punto, evaluar parámetros por cada cota, previsualizar síncrono). | Se arregla **primero y más barato** en Python (sección 4). Rust después, sobre lo que quede. |

Lo que más se siente al usar la app, en orden: arrastrar un punto de un boceto (70 ms por evento cuando el cuadro de
60 Hz da 16 ms), el hover sobre aristas y caras con modelos grandes, y las vistas previas de comandos que congelan la
ventana.

## 2. Mediciones (base, esta PC, 2026-10-12)

Reproducibles con `scripts/bench_rendimiento.py` (ver sección 7). Cada número se corrió dos veces con diferencias
de ±15 %; son órdenes de magnitud, no microbenchmarks.

### Solver de bocetos (`restricciones/solver.py`)

| Caso | Tiempo |
|---|---|
| Primer `resolver` de la sesión (incluye importar scipy) | ~360–410 ms |
| 5 / 20 / 60 rectángulos acotados (20 / 80 / 240 puntos) | 4 / 17–20 / 52 ms |
| Polígono de 6 / 12 / 24 lados con cotas y coincidencias | 41 / 220 / **5.070–5.280 ms** |
| Arrastrar un punto del polígono de 24 lados, por evento de ratón | **70–72 ms** |
| Auditoría aparte: cadena de 60 tramos / 120 tramos, por movimiento | 164 ms / ~1 s |
| Auditoría aparte: 20 rectángulos con 99 restricciones + 40 cotas | 147 ms (98 ms al arrastrar) |

Por qué: `least_squares` corre dos veces (la segunda es un «pulido»), con jacobiano por diferencias finitas sobre ~139
closures Python (41.000 llamadas a `P()` en un solo solve), y después otro jacobiano más para el rango y el SVD. El
crecimiento es superlineal (6→12→24 lados: ×5, ×23).

### Operaciones de malla (`nucleo/malla.py`, esfera sintética)

| Operación | ~10 k triángulos | ~50 k triángulos |
|---|---|---|
| `reducir` al 50 % | 0,7–1,3 s | **4,0–4,7 s** |
| `remallar` | 1,5–2,1 s | **7,8–10,3 s** |
| `suavizar` (10 iteraciones) | 40–74 ms | 315 ms |
| `analizar` | 14–34 ms | 120–165 ms |
| `reparar` / `cortar_plano` | 11–18 ms / 12–21 ms | 70 ms / 41–55 ms |

Auditoría aparte, con mallas de 82 k y 327 k triángulos: `reducir` 82 k→20 k tarda 10,4 s (estimado 45–60 s a 327 k);
`espesores` (espesor de pared para impresión) con 2000 rayos tarda 1,2 s a 20 k triángulos y 5,1 s a 82 k (lineal);
`normales_suaves` 1,8 s y `es_cerrada` 0,86 s a 327 k; leer un STL ASCII de 327 k triángulos 2,1 s y escribirlo 2,8 s.

### Lo que NO es Rust (medido)

| Qué | Tiempo | Quién lo domina |
|---|---|---|
| Recalcular `motor_cohete.omnicad` (41 pasos) | 2,6–3,0 s | OpenCascade: roscas 0,45–0,58 s, agujeros 0,45 s, booleanas 0,2–0,33 s |
| Teselar 7 cuerpos (30.636 triángulos) | 0,22–0,31 s | `BRepMesh` (C++); la extracción a numpy es ~3 µs por triángulo |
| Aristas de los 7 cuerpos (306 polilíneas) | 0,03 s | — |
| `desde_brep` (B-rep a malla) | 0,4–1,2 s | OCC; casi constante con el tamaño |
| Abrir el proyecto | 0,76–1,16 s | zip + JSON + importar OCP |

## 3. Candidatos a Rust, priorizados

Orden = valor ÷ riesgo, juntando las tres auditorías (bocetos, malla/núcleo, visor/UI). «Ganancia esperada» es una
**estimación** de oficio (bucle Python → Rust con arreglos contiguos suele dar 10–100×); se confirma con el bench de
cada paso antes de darlo por bueno. «Cruce» = costo de la frontera Python↔Rust: si la función se llama miles de veces
por cuadro con datos chicos, la ganancia se la come el cruce y hay que pasarle lotes.

| # | Candidato | Dónde (hoy) | Hoy | Ganancia esperada | Riesgo | Depende de |
|---|---|---|---|---|---|---|
| R1 | **Descompresor Zstandard** (abierto: sigue en Python puro) | `io_archivos/zstd_puro.py:40-435`, lo llama `f3d_nativo.py:123-136` | Python puro, 1 MB/s comprimido; un `.f3d` de 20 MB ≈ 20 s. El venv es 3.12: nunca usa `compression.zstd` (3.14+) | 50–100× | Bajo (función `bytes→bytes`, crate `zstd`) | — |
| R2 | **Reducir malla (QEM)** | `malla.py:1363-1420`, `_Editor` 1140-1305, `_optimo_qem` 1308, `_cuadricas` 1331 | `heapq` + sets + numpy sobre arreglos de 3–12 elementos por colapso (~300 µs/colapso) | 20–100× | Medio (replicar penalización de bordes de grupo, condición de enlace, umbral anti-pliegue) | Núcleo half-edge (R7) |
| R3 | **BVH de triángulos**: primer choque, cualquier choque, punto más cercano | `revision.py:477-588` (`espesores`, `primer_choque`), `analisis.py:705-787`, `malla.py:1472-1495`, `vaciar` 1944; picking en `ui/visor3d.py:151-164` | Möller-Trumbore en numpy, O(rayos × triángulos de la caja) | 20–100× y sin recortar rayos por fidelidad | Bajo (BVH estándar con SAH, una sola pieza para 4 usos) | — |
| R4 | **Kernel del solver**: residuos + jacobiano analítico + trf/LM | `solver.py:437`, `181-334` (`_armar`), `454` (`_jacobiano`), `591-616`, `619` | scipy `least_squares` con diferencias finitas sobre closures | 10–50× por evento de arrastre | **Medio-alto** (16 tipos de restricción; paridad numérica 1e-6; conteo de GDL por rango) | Primero los arreglos de Python (sección 4) |
| R5 | **Geometría de boceto**: de Boor, interpolación, `mas_cercano`, intersecciones, cajas | `boceto.py:320-367`, `394-434`, `454`, `507-597`, `613-656`, `1526-1563` | Python puro (27 µs/punto evaluado; `mas_cercano` en spline 2,9 ms; 1 spline contra 500 splines: 1,7 s) | 20–50× con API por lotes | Bajo (numérico puro) | Prerrequisito de R4 y R9 |
| R6 | **Remallar isótropo** | `malla.py:1763-1824`, `_remallar_nucleo` 1536, `_relajar` 1498, `_Referencia` 1472 | Bucles Python por arista sobre `_Editor`; 0,4 ms por triángulo de resultado; topes `TRIANGULOS_MAXIMOS_REMALLADO=100.000`, `TECHO_REMALLADO=130.000`, `PICO_MAXIMO=150.000` | 20–50× y subir o quitar los topes | Medio-alto (heurísticas de rasgos y valencia; no da el mismo resultado exacto) | R7, R3 |
| R7 | **Núcleo half-edge / topología de malla** | `malla.py:206-231` `_Topo`, `139-150` `es_cerrada`, `244-256`, `312-335`, `506-529`, `178-193` | numpy (`unique`, `isin`) sobre 3 M de medias aristas; ya vectorizado | 5–10× | Bajo | Base de R2, R6 |
| R8 | **Dedupe de filas, soldado y normales suaves** | `render_cpu.py:269-290`, `malla.py:90-99`, `948-969`, `1008`, `2275-2294`, `geometria.py:513-520`, `gltf.py:45-74` | `np.unique(axis=0)` (ordena filas como `void`) + `np.add.at` | 10–30× (absoluto: 1–2 s por 300 k triángulos) | Bajo | — |
| R9 | **Hit-testing del boceto** (punto/curva más cercano, selección por ventana) | `ui/editor_boceto.py:631`, `642`, `2612`, `2740` | Doble bucle Python con `QPointF`; 400 curvas = 17,5 ms por movimiento (50–60 ms en 3D, estimado); el resaltado se apaga con más de 400 curvas | 20–50× | Bajo-medio (hay que mantener el índice sincronizado con Qt) | R5 |
| R10 | **Lectura/escritura de mallas en texto** (STL ASCII, OBJ, PLY ASCII, 3MF) | `malla.py:562-681`, `696-798`, `exportar.py:58-109` | Bucles por línea/triángulo, `struct.pack` por triángulo | 10–30× | Bajo | — |
| R11 | **Rasterizador CPU y mapa de sombras** (**HECHO 2026-10-17**, sin BVH) | `render_cpu.py:401-529` | numpy por tandas con `lexsort` para el z-buffer; 1280×720 con 327 k triángulos = 2,6 s | 10–30× en esa parte | Medio (centro de píxel, tolerancia −1e-7, desempate estable: `test_render.py:80`) | R3 (previsto; se hizo sin BVH) |
| R12 | **Quitar aristas ocultas superpuestas** (vistas de dibujo) | `nucleo/dibujo.py:269-306` | Broadcast denso k×m×2; 1500 ocultas × 1500 visibles = 1,6 s | 10–30× | Bajo | — |
| R13 | **Menores**: RDP del vectorizador, lectores DXF/SVG, `recortar_a_circulo`, `generar_grupos` con tamaño mínimo (cuadrático: 20 k triángulos = 85 s, pero hoy inalcanzable desde timeline/MCP) | `vectorizar.py:49-84`, `dxf.py:467-804`, `svg.py:104-194`, `dibujo.py:507-540`, `malla.py:1092-1111` | Python puro | 5–30×, ganancia absoluta ≤ 1 s | Bajo | — |

Notas sobre el orden:

- **R1 primero** porque es el mejor valor por esfuerzo y la única pieza sin riesgo de paridad. Ojo: `pip install
  zstandard` (o Python 3.14) da lo mismo sin escribir Rust. Si el objetivo fuera solo abrir `.f3d` rápido, esa es la
  vía; en un plan Rust, R1 sirve de **prueba de punta a punta** del empaquetado (maturin → `.pyd` → PyInstaller →
  instalador) con una función chica y de fácil verificación.
- **R2, R3, R7, R8** comparten tipos (malla indexada, half-edge, BVH): se hacen en **un solo crate** con módulos.
- **R4 va tarde a propósito**: es lo que más se siente, pero también lo más riesgoso (780 líneas con muchos casos de
  tolerancia y ~10 pruebas en `tests/test_solver.py`). Primero se baja el costo en Python (sección 4) y recién después
  se mide cuánto Rust hace falta.

### Candidatos descartados (no vale Rust)

| Qué | Por qué |
|---|---|
| Teselado y extracción `OCC→numpy` (`geometria.py:466-486`, `visor3d.py:456-496`) | El costo es el cruce Python↔OCP por elemento (3–5 llamadas pybind por nodo). Rust no puede leer un objeto OCP; solo se evitaría enlazando OpenCascade desde Rust (`opencascade-rs`), que no está maduro. Se arregla extrayendo en bloque una vez por forma. |
| Booleanas, roscas, agujeros, empalmes, chapa, superficies, `perfiles`, fijaciones, engranajes | Una sola llamada a OCC cada una: el tiempo es C++. |
| Referencias topológicas (`referencias.py:168-198`) | Integrales y adaptadores de OCC; se arregla con caché de firmas y una matriz de distancias. |
| Pintado con Qt (`paintEvent`, `QPainterPath`, íconos) | El techo es Qt; Rust solo sirve para proyectar por lote (R9). |
| Dibujo OpenGL | Ya usa VBO, LOD y modo dinámico (`PROJECT_LOG.md` paso 4). |
| `suavizar`, `cortar_plano`, triangulación por orejas, `reparar` | 0,1–0,3 s con 327 k triángulos; ya vectorizado. |

## 4. Primero, sin Rust (cabo suelto que pesa más que Rust)

Cada fila se mide antes y después con el bench. Son arreglos de Python que **dan la mayor mejora por esfuerzo** y
varios son prerrequisito de Rust (si la estructura de datos es mala, pasarla a Rust no la arregla).

| # | Qué | Dónde | Medido o estimado | Arreglo |
|---|---|---|---|---|
| P1 | `valores()` evalúa **todos** los parámetros con `ast.parse` por cada cota en cada evento de arrastre | `editor_boceto.py:552` → `timeline/parametros.py:227` | 32 ms por evento con 40 cotas × 20 parámetros (medido) | Evaluar `valores()` una vez por evento |
| P2 | Solver: resuelve **todos** los grupos aunque se arrastre uno, corre el «pulido», el rango y el SVD en cada movimiento, y el primer solve paga el import de scipy (~0,4–0,8 s) | `solver.py:552-616`, `editor_boceto.py:555-567` | 40 grupos independientes = 38 ms aunque se mueva uno (medido) | Resolver solo el grupo arrastrado; saltar pulido/rango/SVD mientras se arrastra (GDL al soltar); `jac_sparsity`; precalentar scipy en un hilo |
| P3 | Repintado del boceto punto por punto: `a_px` = numpy de 3 elementos + `QPointF` | `editor_boceto.py:481-488`, `620-625`, `3021-3098` | 5 µs/punto → 10.000 puntos = 50 ms por repintado, contra 0,78 ms vectorizado (medido) | Proyectar cada curva en bloque con la MVP, cachear por (cámara, primitiva), `QPolygonF` desde un array |
| P4 | Hover de aristas: ~25 llamadas numpy **por arista** | `visor3d.py:1092-1103`, `965-997` | 83 µs/arista: 1000 aristas = 83 ms, 3000 = 236 ms por movimiento (medido) | Concatenar polilíneas del cuerpo una vez, un solo matmul, `reduceat` |
| P5 | Rayo contra **todos** los triángulos de todos los cuerpos, sin AABB por cuerpo; `.astype(float)` de toda la malla por hover | `visor3d.py:151-164`, `861-875`, `ui/render.py:519` | 2 / 10 / 49 ms para 20 k / 100 k / 400 k triángulos (medido) | Culling por caja de cada cuerpo; BVH (R3) si no alcanza |
| P6 | Vista previa de comandos síncrona: cada tecla (debounce 220 ms) corre una booleana/empalme completa en el hilo de UI y re-tesela | `ui/comando.py:548-602`, `documento.py:474-486`, `manipuladores.py:682-711` | ~4–5 veces por segundo con la ventana congelada | Caché por (paso, entradas); teselado grueso en la previa; ojo: importar OCP retiene el GIL (`PROJECT_LOG.md:89`), un hilo puede no alcanzar y haría falta un proceso |
| P7 | Recálculo sin memo por paso: editar el paso i re-ejecuta i..fin aunque sean independientes | `documento.py:488-539` | El log midió 30 s de 34 s en 4 roscas M3 | Memo con clave (`a_dict` del paso, identidad de formas de entrada, parámetros leídos); booleana n-aria; caché de rosca |
| P8 | Referencias topológicas: firmas (GProp + BRepAdaptor) recalculadas por referencia, sin caché | `nucleo/referencias.py:168-198` | 40 aristas elegidas en un cuerpo de 300 ≈ 12.000 firmas por paso (estimado) | Firmas por cuerpo una vez (clave `id(forma)`), puntuación matricial |
| P9 | Animación: `v @ R.T + t` de toda la malla por cuadro, arrays nuevos que rompen la caché de VBO (`id(array)`) | `ui/animacion.py:1217-1262` | Subida a GPU de cada cuerpo movido, por cuadro | Matriz de modelo (`u_modelo` ya existe en `render.py:660`) |
| P10 | `camara_cambiada` se emite en cada `paintGL`, aunque la cámara no cambie; el ViewCube se repinta y crea `QFont` cada vez; el navegador y el timeline se reconstruyen enteros en cada notificación | `visor3d.py:1638`, `ventana.py:763-854`, `navegador.py:169-223` | Tormenta de refrescos | Emitir solo si cambia la firma de cámara (patrón en `manipuladores.py:743-749`); diff antes de reconstruir |
| P11 | `exportar_stl` binario: `struct.pack` por triángulo | `io_archivos/exportar.py:77-78` | 1,57 s a 327 k triángulos | Dtype estructurado, como ya hace `malla.escribir_stl` 590-595 |
| P12 | `es_cerrada` (`np.isin` cuesta 0,75 s a 327 k) y `_corregir_degenerados` (dict de 3 M entradas aunque haya una cara degenerada) | `malla.py:139-150`, `988` | 1,7 s de los 3,5 s de `suavizar` (medido por la auditoría) | Reusar los conteos de `_Topo`; armar el dict solo para lo necesario |
| P13 | Autoguardado y deshacer hacen `json.dumps` de toda la receta (mallas en base64) en el hilo de UI | `ventana.py:2024-2031`, `documento.py:188-196` | Esporádico, pero bloquea | Instantánea ya serializada, escritura en un hilo |
| P14–P24 | Arreglos de Python sobre OpenCascade de la 2ª pasada: iterar colecciones OCP (470 µs fijos por recorrido), `_es_concava` cuadrático, clasificador reusado, encadenado O(n²), `SetRunParallel`, un `BRepMesh` por lote, sección por contorno, autointersecciones bajo demanda, HLR por tipo de superficie | Ver [plan_cpp.md](plan_cpp.md) sección 5 | `revisar()` 630 → < 200 ms; booleana de 900 agujeros 1,6 → 0,85 s (medido) | Ver tabla |

## 5. Arquitectura propuesta

**Un solo crate, un solo `.pyd`**, con fallback a Python:

```
clon/rust/                     # nuevo; el resto del repo no cambia
  Cargo.toml                   # workspace
  omnicad_rs/                  # crate PyO3 + rust-numpy (arreglos sin copia)
    src/lib.rs                 # #[pymodule] omnicad_rs
    src/zstd.rs                # R1 (previsto; hoy no existe: el crate es un solo src/lib.rs)
    src/malla/{halfedge,qem,remallado,io,soldado}.rs   # R2, R6, R7, R8, R10
    src/bvh.rs                 # R3
    src/boceto/{solver,spline,cortes,golpe}.rs         # R4, R5, R9
  pyproject.toml               # maturin: módulo `omnicad._rs`
clon/omnicad/nativo.py         # carga el módulo; si no está, expone None
```

Reglas de diseño:

1. **El Python actual NO se borra.** Cada función Rust tiene su par Python, que queda como referencia de las pruebas
   de paridad y como fallback cuando el módulo no está (Linux, macOS, un wheel que falla, desarrollo sin toolchain).
   El selector es una línea: `nativo.disponible("reducir")`. Variable de entorno `OMNICAD_SIN_RUST=1` fuerza Python.
2. **Interfaz por lotes y arreglos numpy contiguos**: `float64`/`int32` en C-order, sin objetos por elemento. Una
   llamada por operación, no una por punto (el cruce cuesta ~1 µs).
3. **Se suelta el GIL** (`py.allow_threads`) en las funciones largas (reducir, remallar, BVH): permite mover esas
   operaciones a un hilo sin congelar la interfaz.
4. **Errores**: Rust devuelve `Result`; el wrapper Python los convierte en `geo.ErrorGeometria` / `ErrorOperacion`
   con el mismo mensaje en español de hoy. Rust no entra en pánico hacia Python.
5. **Sin Qt y sin OCP en Rust**: solo datos puros (arreglos). Mantiene la regla de AGENTS.md (`nucleo/`, `timeline/`,
   `restricciones/` no importan Qt).
6. **Determinismo**: mismo resultado entre corridas (sin `HashMap` de orden aleatorio en lo que decide el resultado;
   semillas fijas).
7. **Regla del MCP y la CLI** (CLAUDE.md): optimizar por dentro no agrega herramientas. Si un paso cambia la firma
   pública o suma una opción (p. ej. quitar el tope de triángulos del remallado), esa herramienta se actualiza y se
   regenera `docs/agentes/herramientas.md` en el mismo turno.

## 6. Cómo se prueba cada paso (definición de terminado)

Cada ítem Rust entra solo si cumple **todo**:

1. **Paridad**: `tests/test_rust_paridad.py` compara la salida Rust con la del Python de referencia en entradas
   fijas y aleatorias con semilla: igualdad exacta en enteros/bytes (Zstandard, soldado), tolerancia explícita en
   floats (1e-9 relativo en geometría; en el solver, residuo ≤ 1e-6 y mismos GDL y mismas entidades determinadas).
   Se omiten con `pytest.mark.skipif(not nativo.disponible)`, y CI corre las dos variantes.
2. **Propiedades** donde el resultado no es idéntico (remallar, reducir): volumen dentro de la tolerancia de hoy,
   malla cerrada, sin triángulos degenerados, tamaño objetivo respetado (lo que ya miden `test_malla.py:206-224`).
3. **Corpus del solver**: grabar con el «diario del solver» (pendiente 22b del `PROJECT_LOG.md`) las llamadas reales
   de un par de sesiones y reproducirlas contra scipy y contra Rust.
4. **Números**: `scripts/bench_rendimiento.py` antes y después, pegados en el `PROJECT_LOG.md`. Si la mejora medida
   es menor a 3× o no cambia lo que siente el usuario, **no se entrega** (se queda el Python).
5. **Verificación de siempre**: `ruff check --select F,B023,B905`, `pytest -q`, prueba de humo. Más `cargo clippy
   -- -D warnings` y `cargo test` del crate.
6. **Empaquetado**: el instalador de Windows (`instalador/windows/omnicad.iss`, PyInstaller en el venv) incluye el
   `.pyd` y arranca sin Rust instalado; en Linux/macOS sin wheel la app funciona con el fallback.

## 7. Plan por fases

| Fase | Contenido | Entregable medible | Estimación |
|---|---|---|---|
| 0 | Sección 4 (P1–P5, P10–P12): arreglos de Python sin dependencias nuevas. **No necesita permiso.** | Arrastrar un punto: de 70 ms a < 16 ms en el polígono de 24; hover de aristas < 5 ms con 1000 aristas; repintado de 10 k puntos < 5 ms | Corto |
| 1 | Andamiaje: toolchain, crate vacío, `nativo.py`, empaquetado de punta a punta con **R1 (Zstandard)** | `.f3d` grande abre 50× más rápido; el instalador lleva el `.pyd`; CI con y sin Rust | Corto |
| 2 | Malla: R7 → R2 (reducir) → R8 → R10, con R3 (BVH) en paralelo | `reducir` 50 k en < 0,3 s; `espesores` con 2000 rayos en < 0,1 s a 82 k | Medio |
| 3 | Boceto: R5 → solver R4 con jacobiano analítico → R9 (hit-testing) | Arrastre del polígono de 24 en < 5 ms; sin tope de 400 curvas para el resaltado | Medio-largo |
| 4 | Remallar R6 y subir los topes; rasterizador R11 (ya hecho); R12–R13 | `remallar` 50 k en < 0,5 s; render 1280×720 a 327 k triángulos < 0,5 s | Largo |
| 5 | Sección 4 restante (P6–P9, P13): previa asíncrona, memo por paso, firmas | Editar un paso al final de un timeline largo no recalcula lo anterior ni lo independiente | Medio |

La fase 0 y la fase 5 no dependen de Rust y se pueden hacer en cualquier momento; las fases 1–4 van en orden porque
cada una reutiliza tipos de la anterior.

## 8. Qué hay que autorizar (AGENTS.md: «no instalar paquetes sin permiso»)

Al medir el 2026-10-12 no estaban instalados. Actualización 2026-10-17: `cargo`/`rustc` 1.99.1 encontrados en
`D:/rust/cargo/bin`; maturin 1.15.0 instalado en el venv con permiso explícito, igual que los crates PyO3/numpy
de R11. Las demás dependencias de esta lista no se instalaron en esta tanda:

- `rustup` (toolchain estable de Rust, target `x86_64-pc-windows-msvc`; requiere las Build Tools de MSVC).
- `maturin` en el venv de `clon/` (o `pip install maturin` global).
- Crates: `pyo3`, `numpy` (rust-numpy), `zstd` (o `ruzstd`, Rust puro), `rayon`, `nalgebra`, `ordered-float`.
- Ningún servicio pago ni de red en tiempo de ejecución: todo es compilación local y el `.pyd` resultante.

## 9. Riesgos honestos

- **Paridad numérica del solver**: el criterio actual (tolerancia 1e-6, regularización 1e-4, segunda corrida de
  pulido, conteo de GDL por rango) es empírico. Un jacobiano analítico puede converger a otra solución válida en
  croquis subdeterminados. Mitigación: corpus grabado y comparación de GDL y entidades determinadas, no solo de
  coordenadas.
- **Cruce Python↔Rust**: una función de microsegundos llamada 10.000 veces por cuadro pierde. Por eso la API es
  por lotes y se mide antes de integrar.
- **Mantenimiento**: dos implementaciones por función (Python de referencia + Rust). Es el precio del fallback y de
  poder probar paridad; se acota a las ~13 funciones de la tabla.
- **Plataformas**: hay que publicar un wheel por plataforma (Windows, Linux, macOS). Con el fallback, una plataforma
  sin wheel anda igual que hoy, más lenta.
- **No es magia**: el lag de OpenCascade (booleanas, roscas) y de Qt sigue igual. Los pasos de la sección 4 son los
  que más se sienten en el uso diario; Rust los complementa, no los reemplaza.
- **Contradicción corregida**: el `PROJECT_LOG.md` (paso 5, 2026-10-09) concluyó «ningún cuello que quede es código
  Python propio». Valía solo para lo que medía `ui/bench.py` (arranque, giro de cámara, recálculo sintético). No
  cubre arrastre de bocetos, hover, picking, vistas previas ni operaciones de malla: ahí están los cuellos de este
  documento.

## 10. Reparto con C++ (resumen de [plan_cpp.md](plan_cpp.md))

Segunda pasada del 2026-10-12: qué gana con C++ y qué queda en Python o Rust. Detalle, mediciones y fases en `plan_cpp.md`.

| Lenguaje | Es para | Ejemplos |
|---|---|---|
| Python | Orquestar, interfaz, caché/memo y arreglar primero el lag de OpenCascade | P1–P24 de la sección 4, `SetRunParallel`, un `BRepMesh` por lote |
| Rust | Datos puros en arreglos numpy (R1–R13 de la sección 3) | solver, reducir/remallar, BVH, Zstandard |
| C++ | Lo que toca objetos de OpenCascade sin cruzar por elemento | C1 malla en bloque con id de cara, C2 evaluación de superficies por lote, C3–C5 |

- **OCP retiene el GIL**: dos hilos mallando no son más rápidos que en serie (1.827 ms contra 1.903 ms). Los hilos Python no sirven; sí procesos.
- **Primero, proceso trabajador en Python** (`ProcessPoolExecutor`, BREP serializado): paralelismo real y botón Cancelar (matar el proceso) sin escribir C++.
- **C++ en proceso solo para C1 y C2**, y solo si un spike de medio día confirma que el ABI de `cadquery-ocp` se comparte (MSVC 19.51 de OCP contra 19.44 aquí).
- **Faltan para el spike**: cabeceras de OpenCascade 8.0 y `pybind11` ≥ 3 (con permiso). Compilador y CMake ya están.
- **Bug corregido de paso**: la caché de `ui/analisis_vista.py` usaba `id(forma)` sin retener la forma; prueba en `tests/test_hallazgos_ui.py`.
- **Riesgos de concurrencia** (la malla vive dentro de la forma, `id()` reciclable, RAM de 185 MB por trabajador) están en la sección 7 de `plan_cpp.md`.
