# Pipeline de rendimiento: qué pasa a Rust y qué no (2026-10-31)

Informe de una sola vez. **No se tocó código de la app**: solo mediciones en procesos aparte (con `scripts/turno.py`, de a
una) y dos prototipos descartables en Rust fuera del repo. Reemplaza el orden de `docs/plan_rust.md` § 7 donde difiera;
el estado de cada fila vive en [seguimiento/mejoras.md](../seguimiento/mejoras.md) (IDs `RS-X*`, más las filas `RS-R*` y
`P-11n` que se actualizaron). Scripts, registros y prototipos: `evidencias/rust_pipeline_2026-10-31/` (fuera de git).

Equipo: Windows 11, 12 hilos, 13 GB, gráficos integrados, otras sesiones usando la PC. Cada número es una corrida (las
repeticiones se indican); sirven por orden de magnitud. Python 3.12.10, `cadquery-ocp 8.0.1.1`, Rust 1.99.1.

## 1. Resumen (cinco líneas)

| # | Oportunidad | Hoy (medido) | Después (medido o estimado) | Lenguaje |
|---|---|---|---|---|
| 1 | Editar un paso en un proyecto de ≥ 60 pasos: el hijo reconstruye todo y tira la memoria por paso | `motor_impreso` (292 pasos) **24,4 s**; `gatoRL` (113) **19,7 s** | En proceso con memoria: **0,16–0,8 s** y **0,08–2,9 s** (30–150×) | **Python** (trabajador persistente) |
| 2 | BVH de triángulos (R3): `espesores`, `primer_choque`, hover sobre mallas | 2000 rayos a 50 k triángulos **2,2 s**; a 251 k **11,8 s**; un rayo de hover sobre 251 k **33 ms** | **2,75 ms** y **3,97 ms** (800× y 3000×, prototipo Rust, mismo resultado a 1e-13); hover ≈ 2 µs | **Rust** |
| 3 | Zstandard (R1) + lector SAB + escena de un `.f3d` | BINCHA **14,8 s** (Zstd 6,0 s, SAB 3,0 s, escena y resto 3,1 s) | Zstd **5,55 s → 0,089 s** (62×, byte a byte igual); con SAB y escena ≈ 4–5 s en total (estimado) | **Rust** |
| 4 | Mallas: `reducir` (R2), `remallar` (R6), base half-edge (R7) | 50 k triángulos: **4,4 s** y **8,2 s** | 20–50× estimado (sin prototipo) | **Rust** |
| 5 | Selección y pintado del boceto con cientos de curvas | **36 µs por curva**: 14 ms con 400, 56 ms con 1500; repintar 21 ms con 400; el resaltado se apaga con más de 400 | < 1 ms con una proyección por lote en numpy (estimado, sin prototipo); Rust solo si hace falta con miles | **Python** primero |

**Orden recomendado:** (1) trabajador persistente, sin permisos; (2) BVH y Zstd en Rust, con las dependencias que ya
están en caché local de cargo; (3) boceto en numpy; (4) mallas en Rust; (5) solver y C++ solo si un caso real lo pide.
**Necesita permiso de Gerardo:** agregar crates al proyecto (`ruzstd`, `rayon`; ya están en `D:/rust/cargo/registry`, se
compila sin red) y recompilar el `.pyd`; para la fase del solver, `nalgebra` o `faer` (no están en caché); para C++,
cabeceras de OpenCascade y `pybind11`. No se instaló nada hoy.

## 2. Estado de los planes anteriores

Verificado contra el código de hoy (no contra el log).

| Origen | Qué | Estado |
|---|---|---|
| plan_rust R11 | Rasterizador, sombras y SSAO | **Hecho** (`clon/rust/src/lib.rs`) |
| plan_rust R14 | Arreglo planar de perfiles | **Hecho** (`rust/src/perfiles.rs`) |
| plan_rust R5 | Geometría del boceto | **Parcial**: solo `spline_extremos` (`rust/src/spline.rs`) |
| plan_rust R1 | Zstandard | **Vigente y subió de prioridad** (`io_archivos/zstd_puro.py:40`, Python puro; el crate no tiene zstd) |
| plan_rust R3 | BVH | **Vigente, prioridad alta** (no hay BVH; `revision.py:556` usa numpy por tandas) |
| plan_rust R2, R6, R7 | Reducir, remallar, half-edge | **Vigentes** (`malla.py:1489`, `1889`, `219`) |
| plan_rust R4 | Kernel del solver | **Rebajado**: el polígono de 24 lados tardaba 5 s en el plan y hoy 75 ms; solo pesa con ≥ 200 piezas |
| plan_rust R8, R10, R12, R13 | Soldado, texto, ocultas, menores | **Baja prioridad** (ver § 4) |
| plan_rust R9 | Hit-testing del boceto | **Se hace primero en numpy**; Rust solo si sobran miles de curvas |
| plan_rust P1–P5, P7–P13 | Arreglos de Python | **Hechos** (P7 y P13 verificados hoy en el código; el resto según el log), con una excepción: P7 (memo por paso) existe pero **no se usa en documentos de ≥ 60 pasos** (§ 3, RS-X1) |
| plan_rust P6 | Previa fuera del hilo de la ventana | **Hecho para ≥ 64 caras** (previa-asincrona 10-29); falta la latencia (P-56) |
| plan_cpp P17 | Un clasificador por cuerpo | **Hecho en `fijaciones.py`** (`_dentro`, `_material`); quedan los de `geometria.py:565-575, 1042` |
| plan_cpp P18, P20 | Encadenado O(n²), un `BRepMesh` por lote | **Abiertos** (sin `cKDTree` en `superficies.py` / `solidos_crear.py`) |
| plan_cpp P19 | `SetRunParallel` | **Parcial**: falta en `unir_instancias` (`solidos_crear.py:2856`) |
| plan_cpp C1, C2, C5 | C++ en proceso | **Sin código**; ganancia de C1 re-evaluada abajo (≈ 25–40 % del teselado) |
| plan_cpp fase 1 | Proceso trabajador | **Parcial** (`nucleo/aislado.py`: un hijo por tarea, sin pool ni memoria) |
| fluidez-10-28 E1 | Previa «lo último gana» | **Hecho** (`ui/comando.py:31, 718-737`, espera adaptativa) |
| fluidez-10-28 E2 | Previa de Extruir por transformación | **Hecho** (`render_cpu.py:376`, `PrismaVisual`) |
| fluidez-10-28 E3 | Trabajador persistente | **Abierto**: es RS-X1, y pesa más de lo que se pensó |
| f3d_formato | BINCHA 23 s | **14,8 s hoy**; Zstd y SAB siguen siendo el 60 % |
| OmniKernel | Kernel propio en Rust | **No es un camino de rendimiento**: en `comparacion_motores.md` tarda más de 300 s donde OpenCascade tarda 2,7–59 s |

## 3. Mediciones de hoy

### Proyectos grandes (scripts en `evidencias/rust_pipeline_2026-10-31/b6_pesados.py` y `b9_enproceso.py`)

| Proyecto | Abrir (hijo / en proceso) | Recalcular todo (hijo / en proceso) | Editar un paso (hoy, por el hijo) | Editar un paso en proceso, con memoria |
|---|---|---|---|---|
| `motor_impreso` (292 pasos) | 23,0 s / 20,3 s | 24,3 s / 19,9 s | **24,4 s** (paso 146) | paso 73 (boceto) 0,81 s · 146 (mover) 0,22 s · 262 (combinar) 0,16 s |
| `gatoRL` (113 pasos) | 16,2 s / 13,5 s | 16,4 s / 11,5 s | **19,7 s** (paso 56) | paso 28 2,96 s · 56 2,91 s · 101 0,08 s |

Por qué: desde 60 pasos activos `Documento._prevuelo_corresponde` (`documento.py:722`) manda **toda** edición, parámetro
o recálculo a un proceso hijo que reconstruye la receta desde cero (`_prevuelo_cambio` 749, `_solicitar_calculo` 769,
`recalcular` 923). El hijo no tiene memoria por paso, así que editar un paso del medio cuesta lo mismo que
recalcular todo, más el arranque y el traspaso: 2,7 s al abrir y 4,4–4,9 s al recalcular (17–42 % más). Es la protección B-48 contra cuelgues nativos y se
puede conservar con un hijo que **quede vivo con el documento cargado y su memoria** (se mata y se reinicia si cae).
En `motor_impreso`, 72 pasos `combinar` son el 66,7 % (16,2 s, 225 ms cada uno) y el cProfile solo ve 3,9 s de los 19,9 s
(el resto es `Build()` de OpenCascade, invisible para el perfilador); de lo visible, `_integral` (662 llamadas,
0,65 s, casi todo `volumen_exacto` y cajas) y `_explorar`/`lista_occ` (0,9 s) son del propio Python.

### Abrir un `.f3d` (`b3_io.py`)

| Archivo | Total | Zstd | `sab.leer` | ACIS→OpenCascade | Escena, verificación, bocetos |
|---|---|---|---|---|---|
| ABANICO RECTO (3,9 MB, 2 componentes) | 4,96 s | 1,33 s (0,91 MB/s comprimido) | 0,86 s | 2,1 s | 0,67 s |
| BINCHA (8,2 MB) | 14,8 s | 6,0 s (5,6 s aislado; 1,08 MB/s) | 3,0 s | 2,6 s | 3,1 s |

Prototipo (`zbench/`): el crate `ruzstd` 0.9.1, que ya está en la caché local de cargo, descomprime el bloque de BINCHA
(6 052 946 → 30 339 693 bytes) en **0,089 s (341 MB/s)** contra 5,55 s de `zstd_puro`: **62×**, con la salida idéntica byte a
byte. La escena (`f3d_escena.py:65`) hace un recorrido por regex y un `struct.unpack` por posición de cada cara: datos puros.

### Mallas y rayos (`b1_malla.py`, `b11_export.py`, prototipo `bvhbench/`)

| Operación | 50 k triángulos | 251 k triángulos |
|---|---|---|
| `reducir` 50 % (`malla.py:1489`) | 4 383 ms | — |
| `remallar` (`malla.py:1889`) | 8 220 ms | — |
| `espesores`, 2000 rayos (`revision.py:605`) | 3 239 ms | — |
| `primer_choque`, 2000 rayos (`revision.py:556`) | 2 204 ms | 11 848 ms |
| BVH en Rust, mismos rayos, 1 hilo / 12 hilos | **2,75 ms / 1,11 ms** | **3,97 ms / 1,23 ms** |
| BVH en Rust, construir | 8,4 ms | 56,6 ms |
| Rayo de hover (`visor3d.rayo_triangulos`, 1 rayo) | 2,1 ms (20 k) · 10,4 ms (100 k) | 33,4 ms |
| `desde_triangulos` (`np.unique` por filas) | 67 ms | 411 ms |
| `normales_suaves` (`render_cpu.py:340`) | — | 810 ms |
| `suavizar` 10 it / 3 it | 168 ms | 847 ms |
| `analizar` / `reparar` / `generar_grupos` | 51 ms | 284 ms / 413 ms / 133 ms |
| STL binario leer / escribir · ASCII leer / escribir | 83 / 11 ms · 329 / 339 ms (15,7 MB) | — |

El prototipo del BVH (mediana por eje, hojas de 4, recorrido con pila) devuelve la misma distancia que el numpy actual con
diferencia máxima de **1e-13** en los 2000 rayos. Es descartable: la versión de producción lleva SAH, rayos por lote y
liberar el GIL.

### Bocetos y solver (`b10_hit.py`, `scripts/bench_rendimiento.py solver`, `scripts/bench_restricciones.py`)

| Medida | 100 curvas | 400 | 1500 |
|---|---|---|---|
| `Lienzo._curva_cercana` (selección bajo el cursor) | 3,7 ms | 14,3 ms | 56,4 ms |
| Repintar el lienzo (`grab`) | 6,8 ms | 20,6 ms | 78,8 ms |

`ui/editor_boceto.py:1047` recorre cada curva y cada segmento con `QPointF` (36 µs por curva) y `:4480` apaga el resaltado por
encima de 400. Solver: polígono de 24 lados 75 ms (el plan decía 5 s), 60 rectángulos 105 ms, arrastrar un punto 7,7–13 ms
por evento; 100 piezas 65 ms; **400 piezas 2,11 s** y agregar UNA restricción cuesta lo mismo (2,0 s); grados de libertad
178 ms y redundantes 240 ms con 83 restricciones. Primer `resolver` con el import de scipy: 520 ms.

### Teselado, patrones, proyecto (`b2_teselado.py`, `b7_patron.py`, `b4_proyecto.py`, `b8_abrir.py`)

| Medida | Resultado |
|---|---|
| Placa de 200 agujeros (34 412 triángulos) | `BRepMesh` (C++) 428 ms · extracción a numpy 189 ms · con `Coord()` sin `Transformed` 140 ms (1,35×) |
| `unir_instancias` de 1600 cubos | `Fuse` en serie 994 ms · con `SetRunParallel(True)` 769 ms · `unir_instancias` actual 1 499 ms · teselar el resultado 1 706 ms |
| Abrir `motor_cohete` (41 pasos, con caché) | 2,7–2,8 s en caliente (3,8 s la primera vez); recalcular todo 2,76 s: la caché no recorta casi nada |
| Guardar `motor_cohete` | 126 ms con caché de formas, 5 ms sin ella |
| Instantánea de deshacer (`a_dict` + `json.dumps`) | **4 ms** (292 pasos) y **6 ms** (113 pasos, 1,96 MB): **no es un cuello** |
| Importar `omnicad` / `geometria` / `timeline.operaciones` / `ui.ventana` | 0,05 / 0,85 / 0,93 / 1,87 s |

## 4. Candidatos, uno por uno

«Rust» solo recibe datos puros en arreglos; lo que toca objetos de OpenCascade es C++ (`plan_cpp.md`) o un arreglo de
Python. Dificultad y riesgo en la escala del seguimiento. Todas las pruebas de aceptación se corren con el banco
`evidencias/rust_pipeline_2026-10-31/` (al empezar cada fase se promueve su script a `scripts/`).

### RS-X1 · Trabajador persistente con memoria por paso (Python, no Rust)

**Hecho el 2026-11-01:** ver el Registro de `PROJECT_LOG.md`. Lo de abajo queda como el diseño y las mediciones de entonces.

- **Qué y dónde:** `nucleo/aislado.py` (un hijo nuevo por tarea, `CalculoPendiente` 172), `timeline/documento.py:722-790`
  (`_prevuelo_*`, `_solicitar_calculo`, `_aplicar_calculo`), `timeline/calculo_aislado.py`. Generaliza P-56 y fluidez E3.
- **Medición:** § 3 (24,4 s → 0,16–0,8 s en proceso; el hijo suma 4,4–4,9 s en cada recálculo y 2,7 s al abrir).
- **Parte Rust / no Rust:** nada de Rust: es estructura. Ganancia 30–150× en ediciones, y de paso arregla P-56 (la previa de
  un comando pesado también reusa la memoria del trabajador).
- **Riesgo medio-alto:** el estado del documento viaja entre procesos (solo el cambio, no la receta entera); invalidar la
  memoria si cambia el motor o un parámetro; 185 MB por proceso con 13 GB (un solo trabajador); la carrera de
  `id(forma)` (`plan_cpp.md` § 7); mantener la protección B-48 (matar y reiniciar por tiempo, tope 900 s, error claro).
- **Dificultad:** Alta. **Depende de:** nada. **Archivos:** `aislado.py`, `documento.py`, `calculo_aislado.py`.
- **Aceptación:** en `motor_impreso`, editar el paso 146 ≤ 2 s (hoy 24,4 s) y el 73 ≤ 3 s; abrir y recalcular todo no
  empeoran; para todos los cuerpos de 5 ediciones aleatorias volumen, caja y `es_valida` iguales (1e-9 relativo) a
  recalcular todo sin memoria; matar el trabajador a mitad de una edición deja la app viva con el mensaje de B-48.

### RS-R3 · BVH de triángulos en Rust (R3)

- **Qué y dónde:** nuevo `rust/src/bvh.rs`. Usuarios: `revision.py:517-605` (`_choques`, `primer_choque`, `espesores`),
  `ui/visor3d.py:150-166, 1080-1110` (hover y `elegir_entidad` 1420), `analisis.py:744` (`_rayos_chocan`),
  `malla.py` (`vaciar` 2031, proyección de `reducir`/`remallar`), y las sombras de `render_cpu.py` si se quiere sin recortar.
- **Medición:** § 3. Prototipo 800–3000× contra numpy, paridad 1e-13.
- **Rust:** construir el BVH (SAH por bins), `primer_choque`, `cualquier_choque`, punto más cercano; API por lotes con
  arreglos `float64` contiguos; suelta el GIL; caché del BVH por cuerpo en Python (clave `id(forma)` + la forma retenida).
  **No Rust:** decidir qué cuerpos entran y la tolerancia de cada llamador.
- **Ganancia:** `espesores` 3,2 s → ≈ 10 ms; hover sobre una malla de 251 k de 33 ms a microsegundos; se pueden subir las
  muestras de 2000 sin recortar rayos «por fidelidad».
- **Riesgo bajo.** Cuidar el convenio de bordes (`u ≥ −1e-9`, `t > eps`) y los empates (mismo triángulo en caras
  coplanares). **Dificultad:** Media. **Depende de:** crate `rayon` solo si se quiere multihilo (hoy 1 hilo ya sobra).
- **Aceptación:** `primer_choque` 2000 rayos a 50 k ≤ 20 ms (hoy 2 204 ms) con la misma distancia (1e-9) y el mismo
  triángulo salvo empates; `espesores` ≤ 0,1 s; hover de 251 k ≤ 1 ms; construir 251 k ≤ 100 ms; `OMNICAD_SIN_RUST=1`
  da lo mismo; `tests/test_rust_paridad.py` con semilla fija.

### RS-R1 + P-11n · Zstandard, lector SAB y escena del `.f3d` en Rust

- **Qué y dónde:** `io_archivos/zstd_puro.py:40-451` (R1), `sab.py:89` (`leer`), `f3d_escena.py:65-160` (`_leer`, `_malla_cara`).
  El armado ACIS→OpenCascade (`acis_occ.py:65`) **queda en Python/OCC** (2,6 s).
- **Medición:** § 3. Zstd medido (62×). SAB y escena sin prototipo: 3,0 s y ≈ 2–3 s a datos puros.
- **Rust:** `descomprimir(bytes, tope) -> bytes` con el tope contra zip bomb (`ruzstd` ya está en caché; o `zstd` si se
  prefiere la biblioteca C); luego `sab.leer` devolviendo columnas (tipo, punteros, números) en vez de objetos `Entidad`
  (obliga a adaptar `acis_occ.convertir`), y la escena como arreglos. Alternativa sin Rust para Zstd: `pip install
  zstandard` o Python 3.14 (`compression.zstd`), ambos fuera de lo autorizado.
- **Ganancia:** BINCHA 14,8 s → ≈ 8,9 s solo con Zstd; ≈ 4–5 s con los tres (estimado). **Riesgo bajo** (Zstd) a **medio**
  (SAB: formato propietario, `tests/test_f3d_nativo.py`, `test_f3d_reales.py`). **Dificultad:** Media (Zstd), Alta (SAB).
- **Aceptación:** los 12 miembros de los `.f3d` de `~/Desktop/f3z` salen idénticos (sha256) a `zstd_puro`; zip bomb sigue
  fallando con el tope; BINCHA `leer_componentes` ≤ 9 s con Zstd y ≤ 6 s con los tres; mismos cuerpos y avisos.

### RS-X2 · Abrir con caché no abre más rápido (Python)

- **Qué:** `motor_cohete` abre en 2,7 s y recalcula en 2,76 s: `cache/pasos.json` solo guarda los pasos lentos
  (`proyecto.py:83-110`), el resto se rehace y cada paso paga `volumen_exacto` y cajas exactas (`geometria.py:894, 934`):
  80 integrales de volumen 0,18 s, 139 `AddOptimal` 0,28 s, 205 áreas 0,08 s. En `motor_impreso`, 662 `_integral` = 0,65 s. Es P-35.
- **Arreglo:** guardar el volumen por forma en el cuerpo (invalidar al cambiar `forma`) y usar la caja barata
  (`BRepBndLib.Add_s`) donde solo se descarta. No hay Rust. **Aceptación:** abrir `motor_cohete` ≤ 1,5 s; mismos volúmenes y avisos.
  **Riesgo bajo, dificultad baja.**

### RS-X3 · Selección y pintado del boceto con numpy (Python; R9 y RS-P3)

- **Qué y dónde:** `ui/editor_boceto.py:1047` (`_curva_cercana`), `:963` (`_poli_px`), `:4480` (tope de 400 curvas), pintado.
- **Medición:** § 3: 36 µs por curva; 20,6 ms por repintado con 400 curvas (no llega a 60 fps con 300).
- **Arreglo:** proyectar todas las polilíneas visibles con un solo matmul por (cámara, geometría), distancia a segmentos por
  lotes, `QPolygonF` desde un array. **Rust** solo si con miles de curvas el lote sigue pasando de 2 ms.
- **Riesgo bajo-medio:** choca con las sesiones que editan `editor_boceto.py` (Desfase, patrones): **esperar a que se
  integren**. **Aceptación:** 400 curvas: hover ≤ 1 ms y repintado ≤ 8 ms; 1500 curvas: hover ≤ 3 ms; se quita el tope de 400.

### Mallas: RS-R7 → RS-R2 → RS-R6 (+ RS-R8)

- **Dónde:** `_Topo` `malla.py:219`, `_Editor` 1266, `reducir` 1489, `remallar` 1889, topes `TRIANGULOS_MAXIMOS_REMALLADO`.
- **Medición:** § 3 (4,4 s y 8,2 s a 50 k; el plan estimaba 45–60 s para `reducir` a 327 k).
- **Rust:** half-edge, colapso de aristas con cuádricas y remallado isótropo, sobre arreglos. Mismo diseño de un solo
  módulo `malla/`. **Ganancia** 20–50× (estimada del plan; sin prototipo) y poder quitar los topes. **Riesgo medio-alto:** no
  da el mismo resultado exacto; se prueba por propiedades (volumen, cerrada, sin degenerados), como `test_malla.py:206-224`.
- **R8** (`np.unique(axis=0)`): 0,41 s a 251 k; se arregla antes en numpy con claves enteras (como ya hace
  `visor3d.contorno_de_triangulos`) y no justifica Rust. **R10** (STL texto): el binario ya es vectorizado (83 ms); el
  ASCII (0,33 s por 15,7 MB) no justifica nada.
- **Aceptación:** `reducir` 50 k ≤ 0,3 s y `remallar` 50 k ≤ 0,5 s con volumen ±0,5 % de hoy.

### Solver: RS-S1 primero, R4 después (y solo si hace falta)

- **Medición:** § 3. Todo el costo grande es el QR denso de MINPACK (2,12 s de 2,18 s con 400 piezas).
- **Primero (Python):** RS-S1 (hecho 2026-11-13: «trf» con el jacobiano disperso y LSMR desde 200 incógnitas; 400 piezas 3,5 s → 0,35 s), `least_squares(method="trf", jac_sparsity=...)` con el patrón que ya calcula `_patron`
  (`solver.py:675`). **Después (Rust):** una lista de términos tipada (16 tipos de restricción) con jacobiano analítico y
  Levenberg-Marquardt disperso: reescribe ~780 líneas; hace falta una biblioteca de álgebra (`nalgebra`/`faer`, **no están
  en caché: pide permiso y red**). **Riesgo alto** (paridad de las direcciones libres). **Aceptación:** 400 piezas ≤ 200 ms
  y misma determinación de grados de libertad en el corpus del diario del solver.

### RS-X4 · Opciones de OpenCascade que no se probaron (Python)

- `unir_instancias` no llama a `SetRunParallel` (`solidos_crear.py:2870`): 1600 cubos 994 → 769 ms (−23 %; el plan decía ~2×).
- `combinar` es el 66,7 % de `motor_impreso`: probar `SetUseOBB(True)` y `SetGlue(BOPAlgo_GlueShift)` por defecto en piezas
  que solo se tocan (hoy son reintentos, `geometria.py:376-383`). **Sin medir:** es una hipótesis, la prueba es
  `scripts/bench_booleana.py caso <x>` con y sin la opción. **Aceptación:** −30 % en `combinar` sin cambiar volumen ni
  validez. **Riesgo medio** (B-39 existe por contactos casi tangentes).

### RS-X5 · Caché de mallas por cara demasiado chica (Python, sin verificar)

- `render_cpu.py:448` limita la caché a 32 MB: a 144 B por triángulo caben ≈ 233 mil triángulos. Un modelo más grande
  vuelve a extraer todo en cada `set_modelo`. **No se midió.** Probar con float32 y 256 MB. **Aceptación:** `set_modelo`
  de un modelo de 500 k triángulos sin cambios ≤ 50 ms la segunda vez.

### C++ (C1, C2): re-evaluado, sin urgencia

- Las clases de OCP no exponen el protocolo de buffer (`MapNodeArray`, `InternalNodes` no se convierten con
  `np.asarray`, medido hoy), así que la extracción por lote solo sale con C++. Pero en la placa de 200 agujeros la
  extracción es 189 ms contra 428 ms de `BRepMesh` (más ≈ 120 ms de normales exactas, fluidez-10-28): C1 ahorra entre el 25 y el 40 % del teselado, con el riesgo de ABI de
  `plan_cpp.md` § 3. **Se pospone** hasta que RS-X1, RS-R3 y las mallas estén hechos.

### Medido y descartado

| Qué | Por qué |
|---|---|
| Instantánea de deshacer (`a_dict` + `json.dumps`, P13) | 4–6 ms con 0,15–2 MB: no es un cuello (el resto de `Sesion.transaccion`, `deepcopy` de los espacios, no se midió) |
| Importar módulos | `ui.ventana` 1,87 s una vez; no pesa |
| Solver con < 200 piezas | 7,7–13 ms por evento, 65 ms completo con 100 piezas |
| Arrastre y orbitado | ya medidos en fluidez-10-28 |
| STL/OBJ binario | vectorizado |
| `Quitar superpuestas` del dibujo (R12) | ya descarta por caja; no se midió, queda en baja prioridad |

## 5. Pipeline por fases

| Fase | Contenido | Archivos que toca | Permiso | Medida de salida |
|---|---|---|---|---|
| 0 | RS-X1 trabajador persistente; RS-X2 abrir/volumen; RS-X4 `SetRunParallel` y opciones; RS-X5 caché de caras; R8 en numpy; CPP-P17 cerrar | `aislado.py`, `documento.py`, `calculo_aislado.py`, `geometria.py`, `proyecto.py`, `solidos_crear.py`, `render_cpu.py` | **Ninguno** | `motor_impreso` editar 24,4 → ≤ 2 s; abrir `motor_cohete` ≤ 1,5 s |
| 1 | RS-R1 Zstd + RS-R3 BVH en Rust, con registro en `lib.rs` y `nativo.py` | `rust/src/{zstd,bvh}.rs`, `Cargo.toml`, `zstd_puro.py`, `revision.py`, `visor3d.py` (rayo), `analisis.py` | **Sí**: crates `ruzstd` y `rayon` (en caché local, sin red) + recompilar el `.pyd` | Zstd ≤ 0,2 s; `primer_choque` ≤ 20 ms; hover 251 k ≤ 1 ms |
| 2 | SAB y escena del `.f3d` en Rust | `rust/src/{sab,escena}.rs`, `sab.py`, `f3d_escena.py`, `acis_occ.py` | Mismo permiso de la fase 1 | BINCHA ≤ 6 s |
| 3 | Boceto: RS-X3 en numpy (después de que se integren las sesiones del boceto); RS-S1 `trf` disperso | `editor_boceto.py`, `solver.py` | Ninguno | hover 400 curvas ≤ 1 ms; 400 piezas ≤ 1 s |
| 4 | Mallas: R7 → R2 → R6 | `rust/src/malla/*`, `malla.py` | Sí si suma crates (`rayon`); sino ninguno | `reducir` 50 k ≤ 0,3 s |
| 5 | Solver en Rust (R4) y C++ (C1/C2): solo con un caso real que lo pida | `rust/src/boceto/*`; carpeta `cxx` | **Sí**: `nalgebra`/`faer` (red); cabeceras OCCT 8.0 y `pybind11` | 400 piezas ≤ 200 ms |

**En paralelo sin pisarse:** la fase 0 (Python, procesos y OCC) y la fase 1 (Rust nuevo y envoltorios finos) no comparten
archivos, salvo `lib.rs`/`Cargo.lock`, que se integran en serie. Las fases 2 y 4 comparten crate con la 1: se hacen después
de integrarla. La fase 3 espera a que terminen las sesiones que hoy editan `editor_boceto.py`. **Una corrida pesada a la vez**
(`turno.py`); cada fase termina con ruff, pytest de sus archivos, la prueba de humo si toca la interfaz y el banco antes y
después pegado en `PROJECT_LOG.md`.

**Reglas que valen para todas las fases Rust (de `plan_rust.md` § 5–6):** el Python actual queda como referencia y
respaldo (`OMNICAD_SIN_RUST=1`); una llamada por lote; soltar el GIL; sin Qt ni OCP en Rust; la paridad se prueba con
semilla fija; si la mejora medida es menor de 3× o no cambia lo que siente el usuario, no se entrega. Con `rayon`, fijar el
número de hilos (4–6) para no competir con el `OSD_ThreadPool` de OpenCascade.

## 6. Límites de este informe

- Una sola corrida de la mayoría de los números, con la PC compartida (`turno.py` ordena las corridas pesadas, no las
  pruebas de ventana de otras sesiones). Los porcentajes de § 3 son confiables; los milisegundos, ±20 %.
- No medidos: arrastre y repintado del visor 3D con ventana (otras sesiones usan la pantalla), memoria con modelos grandes,
  `set_modelo` de modelos de 500 k triángulos, `reducir`/`remallar` en Rust (los 20–50× son del plan, no de un prototipo).
- Los prototipos de Rust (`zbench`, `bvhbench`) compilaron fuera del repo, con crates ya en caché y sin red; no modifican
  `clon/rust`. El BVH de producción tiene que cumplir los criterios de aceptación de arriba, no los del prototipo.
- `RS-X4` (opciones de OpenCascade) y `RS-X5` son hipótesis; el resto tiene medición.
