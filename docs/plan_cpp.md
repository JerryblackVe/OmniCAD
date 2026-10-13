# Plan de C++ para OmniCAD (Python + Rust + C++)

Segunda pasada de la auditoría de rendimiento del 2026-10-12. La primera (`docs/plan_rust.md`) buscó lo que pasa a
Rust. Esta busca **qué gana con C++** y reparte el trabajo entre los tres lenguajes. Las mediciones son de esta PC
(12 hilos lógicos, Windows 11, Python 3.12.10, `cadquery-ocp 8.0.1.1` = OpenCascade 8.0).

Estado: **solo diseño y mediciones. No hay código C++.** Un bug latente hallado en el camino ya está corregido
(sección 7).

## 1. Cómo se reparte el trabajo

| Lenguaje | Es para… | Ejemplos de OmniCAD |
|---|---|---|
| **Python** | Orquestar, la interfaz, caché/memo, y **arreglar primero** casi todo el lag de OpenCascade | referencias, memo por paso, `SetRunParallel`, batch de `BRepMesh`, vistas previas |
| **Rust** | Datos puros en arreglos (sin tocar OpenCascade): rápido y seguro | solver de bocetos, reducir/remallar mallas, BVH, Zstandard |
| **C++** | Lo que **tiene que tocar objetos de OpenCascade** (`TopoDS_*`, `Poly_Triangulation`, `SLProps`) sin el costo de cruzar por elemento, o soltar el GIL | malla en bloque con id de cara, evaluación de superficies por lote, ejecutor de hojas OCC sin GIL |

Regla simple: *¿la función recibe formas de OpenCascade y recorre muchos elementos?* → C++ (si Python no alcanza).
*¿recibe arreglos numpy?* → Rust. *¿es decidir qué llamar y cuándo?* → Python. Rust **no** puede reemplazar a C++
en la frontera con OpenCascade: no puede leer un `TopoDS_Shape` de OCP, y enlazarlo desde Rust
(`opencascade-rs`) no está maduro.

## 2. Hechos medidos que deciden

| Hecho | Medición | Consecuencia |
|---|---|---|
| **OCP retiene el GIL**: 2 hilos mallando 2 esferas no son más rápidos que en serie | secuencial 1.827 ms, 2 hilos 1.903 ms | Ningún hilo Python acelera ni libera la ventana mientras OpenCascade trabaja |
| Cruzar la frontera cuesta ~1 µs por llamada; leer una triangulación nodo a nodo son 3–5 llamadas por nodo | `tri.Node(i)` 100 k llamadas = 112 ms; 5,5 µs por triángulo | Extraer 100 k triángulos = 326 ms, más que muchas operaciones reales |
| Mallar (`BRepMesh`) ya es C++ y paralelo por dentro | 100 k triángulos finos 1,7 s; `parallel=True` da 3,1× sobre `False` | C++ no acelera el mallado: acelera lo que lo rodea |
| La extracción es 15–30 % de «mallar + extraer» | motor_cohete: 241 ms = BRepMesh 84 + extracción 136 + aristas 21 | Ganancia real pero acotada |
| El truco «STL binario a disco + `np.fromfile`» da el mismo resultado exacto (7 cuerpos, triángulos y triángulos por cara idénticos) pero **no es estable en Windows** | 13 ms en una placa de 38 k triángulos; 125–139 ms en 7 cuerpos chicos (crear/leer/borrar archivo; el antivirus domina, no el algoritmo) | No sirve como base: depende del disco. Una función C++ en memoria es determinista |
| Iterar una colección de OCP (`for x in List_TopoDS_Shape`) cuesta 470 µs fijos por recorrido | `list(itertools.islice(l, l.Size()))` = 4,6 µs | Es un arreglo **de Python**, 100× (ver P14) |
| Las booleanas no usan `SetRunParallel(True)` salvo la rosca | placa de 400 agujeros 0,55 → 0,29 s; 900 agujeros 1,6 → 0,85 s | Arreglo **de Python**, ~2× |
| 4 hilos Python clasificando puntos en cuerpos distintos | 592 ms contra 146 ms de un hilo (serie 584 ms) | Confirma que el paralelismo de OCC necesita salir del GIL |

## 3. Qué hace falta para compilar C++ aquí (factibilidad)

| Requisito | Estado en esta PC |
|---|---|
| Compilador | **Hay**: Visual Studio 2022 Build Tools, MSVC 14.44 (`cl.exe`) |
| CMake | **Hay** (`C:\Program Files\CMake\bin\cmake`) |
| Cabeceras de OpenCascade 8.0 | **Faltan.** `cadquery-ocp` trae solo las DLL (`TKMesh-<hash>.dll`, …), sin `.hxx` ni `.lib`. Hay que bajar el código fuente de OCCT 8.0 (solo cabeceras; no hace falta compilarlo) |
| Librerías de importación (`.lib`) | **Faltan.** Se generan desde las DLL con `dumpbin /exports` + `lib /def` (los nombres con hash son los que ya carga OCP) |
| `pybind11` ≥ 3 | **Falta.** OCP usa internals `v5` (`_pybind11_internals_v5_msvc_mscver1951__`) |
| Mismo ABI que OCP | **Riesgo principal.** OCP se compiló con MSVC 19.51; aquí hay 19.44. Para que un `TopoDS_Shape` de OCP pase a mi módulo sin copiar, ambos deben compartir el registro de tipos de pybind11 (mismo id de internals). Se puede forzar con `PYBIND11_INTERNALS_ID`, pero es un acople frágil frente a cada actualización de `cadquery-ocp` |

### Dos formas de integrarlo

| | A) Módulo en proceso (`omnicad._cxx`) | B) Proceso trabajador (`omnicad-trabajador.exe`) |
|---|---|---|
| Cómo | `.pyd` con pybind11 que comparte DLL y tipos con OCP | Ejecutable propio (o `multiprocessing` de Python) que recibe BREP y devuelve arreglos |
| Pasar una forma | Sin copia (si el ABI coincide) | Serializada: 7 cuerpos = 48 ms (medido) |
| Paralelismo | Hilos sin GIL | Varios procesos |
| Cancelar | `Message_ProgressIndicator` (OCP no lo deja subclasear) | **Matar el proceso**: funciona aun con `HLRBRep_Algo`, que no tiene progreso |
| Memoria | Una sola copia de OCP | ~185 MB por trabajador (importar OCP) |
| Riesgo | Alto (ABI, versión de OCP) | Bajo (sin acople binario) |

**Recomendación:** empezar por **B hecho en Python** (`ProcessPoolExecutor` con OCP en los trabajadores, BREP por
`BinTools`): da paralelismo real entre cuerpos y cancelación de HLR/secciones **sin escribir C++** y sin acople de ABI.
C++ en proceso (A) queda solo para lo que B no puede dar: la **malla en bloque** (C1) y la **evaluación por lote**
(C2), donde el costo es el cruce por elemento y no la espera.

## 4. Candidatos a C++

Orden = valor ÷ riesgo. «Python primero» indica el arreglo sin C++ que hay que probar antes.

| # | Candidato | Dónde (hoy) | Evidencia medida | Ganancia esperada (estimada) | Python primero |
|---|---|---|---|---|---|
| C1 | **Malla en bloque**: `BRepMesh` + extracción a `float32 Nx3` / `int32` con **id de cara**, de varios cuerpos en una llamada | `geometria.py:466-486` (`teselar_por_cara`), `visor3d.py:456-496` y `831-845`, `analisis.py:487-491`, `render_cpu.py:305`, glTF | 5,5 µs por triángulo; `set_modelo` de motor_cohete 241 ms (136 de extracción); placa de 900 agujeros 6,7 s (1,15 de extracción); la malla se extrae 2–4 veces (dibujo, pick, LOD, render, otro visor) | extracción 10–20×; `set_modelo` −50 %; mallar N cuerpos con `parallel` y sin GIL | Un solo `BRepMesh` por lote/compuesto (4 placas: 5,5 → 2,1 s); extraer una vez y compartir entre visores (P20) |
| C2 | **Evaluación de superficies por lote**: normales y curvatura por nodo en B-spline, isocurvas, peine de curvatura, silueta | `analisis.py:519-527` (`_props_nodos`), `1011-1062` (`isocurvas`), `965-1007`, `solidos_modificar.py:1013-1040` | 5,8 µs por nodo (9 con curvatura); `isocurvas` 3,55 s con 306 caras donde `Perform` solo cuesta 2,1 µs por punto; peine 311 ms con 912 aristas; silueta 56 ms por cara | 10–30× y paralelo por cara | Normal/curvatura de caras **analíticas** en numpy (cerrado); C++ solo para B-spline |
| C3 | **Ejecutor sin GIL de hojas OCC independientes**: interferencias por par, HLR por vista, revisión de impresión por cuerpo | `analisis.py:391-424` (107 ms por par), `dibujo.py:1104-1113` (frontal 279 ms, isométrica 1,33 s), `revision.py:279-300` (430 ms) | Los hilos Python no escalan (ver sección 2) | Hasta ~N× con N cuerpos/vistas independientes (12 hilos lógicos; la RAM de 13 GB limita) | **Proceso trabajador en Python** (sección 3-B) y las banderas `SetRunParallel` |
| C4 | **Hojas cancelables**: booleana, sección, `ArgumentAnalyzer` con `Message_ProgressRange` | `geometria.py:268`, `analisis.py:580-615`, `revision.py:279-292` | camisa del motor: sección 11,6 s, revisión 15 s, HLR exacto 143,6 s, sin forma de cortar | Cancelar en < 100 ms | **Matar el proceso trabajador** |
| C5 | **Clasificación masiva de puntos** contra sólidos | `fijaciones.py:622-662`, `geometria.py:449-462`, `manipuladores.py:1078` | 3,7 ms por punto; reusando el clasificador 0,53 ms (7×); `apoyo_arista` 160 ms por fijación → patrón de 50 agujeros ≈ 8 s | otro 5–10× y paralelo | Reusar un `BRepClass3d_SolidClassifier` (P17) |

### Descartados para C++

| Qué | Por qué |
|---|---|
| Booleanas, roscas, agujeros, empalmes, chapa, superficies | Una sola llamada a OCC: el tiempo ya es C++. Lo que se gana es paralelizarlas (`SetRunParallel`, Python) |
| Polilíneas de aristas (`geometria.py:523-551`) | 50 ms por 912 aristas (7 de OCC): rectas con 2 puntos y círculos con `np.linspace` en Python |
| Referencias topológicas (`referencias.py`) | Caché de firmas por forma + distancia matricial: 37× en Python |
| Abrir `.f3d`, `intercambio.py` (XCAF), `perfiles._detectar`, `chapa`, `engranajes`, `construccion`, `vectores` | Una vez, o pocas caras; el costo está en el parseo SAB (Rust R1) o en OCC |
| Pintado con Qt y OpenGL | Sin OpenCascade; el límite es Qt |

## 5. Arreglos de Python que van antes (sumados a `docs/plan_rust.md` sección 4)

Son de esta pasada y siguen la numeración de la sección 4 de `plan_rust.md` (P1–P13). P15 es la caché de firmas de
`referencias.py` y está en P8 de ese documento: con 29–36 ms por referencia y un empalme de 20 aristas en 612 ms por
recálculo, las firmas de todas las aristas una vez cuestan 16,5 ms (37×).

| # | Qué | Dónde | Medido |
|---|---|---|---|
| P14 | Iterar colecciones OCP con `list(islice(l, l.Size()))` | `revision.py:162-168`, `solidos_modificar.py:76-84` y `778`, `superficies.py:191-194` y `694`, `perfiles.py:236` y `262`, `analisis.py:818-823` | `_topologia` 445 → 13 ms; `_fusionar_costuras` 454 → 31 ms; `revisar()` 630 ms, 70 % es esto |
| P16 | `_es_concava` cuadrático: un mapa `{arista: orientación}` por cara | `analisis.py:818-871`, `revision.py:656` | 612 llamadas = 594–619 ms |
| P17 | Reusar el `BRepClass3d_SolidClassifier` | `fijaciones.py:622-662`, `geometria.py:449-462` | 3,7 → 0,53 ms por punto |
| P18 | Encadenado de aristas O(n²): extremos una vez + `cKDTree`/union-find | `superficies.py:126-170`, `solidos_crear.py:149-185` | 1000 aristas 4,2 s (7 ms de OCC) |
| P19 | `SetRunParallel(True)` en `geo.booleano`, `unir_instancias`, `es_valida`, BOPAlgo de revisión (y quitar el `False` de `quitar_caras`) | `geometria.py:268` y `417`, `solidos_crear.py:2151`, `acis_occ.py:493`, `revision.py:279`, `solidos_modificar.py:1131` | 1,9–2,0× en booleanas; `es_valida` 125 → 68 ms; revisión 430 → 362 ms. Ojo con sobresuscribir hilos si luego hay un pool propio |
| P20 | Un solo `BRepMesh` por lote y caché de teselado compartida entre visores (vistas múltiples repiten ×4) | `visor3d.py:377`, `456-496` | 4 placas 5,5 → 2,1 s |
| P21 | Sección del análisis: contorno de la cara de corte que `seccion` ya calcula | `analisis.py:580-615`, `analisis_vista.py:70` | camisa 11,6 s contra 0,42 s |
| P22 | Autointersecciones **bajo demanda**: hoy la casilla viene activa y corre al abrir el panel | `ui/comandos/revision.py:79`, `96-114` | camisa 15 s |
| P23 | HLR: elegir `exacto`/`rapido` por **tipo de superficie**, no fijo. El rápido gana con B-spline (camisa 0,31 s contra 143,6 s) y pierde con placas de muchas caras analíticas (306 caras: 8,2 s contra 1,3 s) | `dibujo.py:322-330`, `965` | ver arriba |
| P24 | La vista previa recalcula todos los análisis visibles en cada tick | `ventana.py:836-837` | multiplica el costo de la previa |

## 6. Plan por fases (C++)

| Fase | Contenido | Entregable medible |
|---|---|---|
| 0 | P14–P24 en Python (sin dependencias nuevas) y `plan_rust.md` fase 0 | `revisar()` 630 → < 200 ms; booleana de 900 agujeros 1,6 → 0,85 s; `set_modelo` de 4 placas −60 % |
| 1 | Proceso trabajador en Python (sección 3-B): teselado por cuerpo y HLR por vista en paralelo, con botón Cancelar | Camisa HLR cancelable; vistas ortogonales en paralelo; ventana no se congela |
| 2 | **Spike C++** (medio día): módulo vacío que (a) carga `TKMesh-<hash>.dll` y (b) recibe un `TopoDS_Shape` de OCP. Decide A o B | Informe «ABI compartido: sí/no» y tiempo de una función de ida y vuelta |
| 3 | Si el spike pasa: C1 (malla en bloque con id de cara, cuerpos en paralelo) | extracción de 100 k triángulos 326 → < 30 ms; `set_modelo` de motor_cohete 241 → ~110 ms |
| 4 | C2 (evaluación por lote en B-spline) y C5 si hace falta | `isocurvas` 3,55 s → < 0,5 s |

Cada paso con el mismo criterio de `plan_rust.md` sección 6: paridad contra el Python de referencia, números
antes/después con `scripts/bench_rendimiento.py`, ruff + pytest + humo, y fallback a Python si el módulo no carga.

## 7. Concurrencia: riesgos antes de cualquier hilo o proceso

1. **La malla vive dentro de la forma.** `Cuerpo.copia` comparte `forma`; `BRepMesh` y `BRepTools.Clean_s` escriben
   la triangulación en las caras compartidas (`teselar_cuerpo(rehacer=True)`, `hit_desde_ref`, `set_resaltado`…).
   Un hilo sin GIL produce una carrera. Regla: trabajar sobre `BRepBuilderAPI_Copy(forma, False, False)`
   (patrón de `teselar_aparte`). `analisis._malla` lee `Triangulation_s` dos veces (`:588`, `:598`).
2. **Booleanas destructivas por defecto**: OCCT puede actualizar tolerancias de las formas de entrada si no se
   pide `SetNonDestructive(True)` (documentado en OCCT; no probado aquí).
3. **Identidad por `id(forma)`**: el trabajador debe devolver la clave junto con una referencia fuerte y la interfaz
   verificar con `is` o una generación antes de instalar el resultado.
4. **Estado Python**: `Operacion._usados` y `Contexto.usados` se mutan al calcular; `Documento` y `EstadoModelo` se
   tocan solo desde el hilo de interfaz, con una copia inmutable hacia el trabajador.
5. **Sobresuscripción**: OCC ya usa su `OSD_ThreadPool` interno sobre los 12 hilos; con trabajadores propios,
   `SetRunParallel(False)` dentro de cada uno o un único pool.
6. **`ops_malla._CANDADO`** protege solo el diccionario de memo; el cálculo queda fuera y `warnings.catch_warnings`
   (`ops_malla.py:63`) no es seguro entre hilos.

### Bug hallado y corregido en esta pasada

`ui/analisis_vista.py:43-48`: la caché de análisis usaba `id(forma)` como clave **sin retener la forma**. Si Python
reciclaba ese id en un cuerpo nuevo, el visor le mostraba los colores del descartado. Corregido: `_con_cache` guarda
la forma junto al resultado. Prueba: `tests/test_hallazgos_ui.py::test_cache_de_analisis_retiene_la_forma_de_su_clave`.

## 8. Qué hay que autorizar

- **Fase 0 y 1: nada** (Python puro; `multiprocessing` es de la biblioteca estándar).
- **Fase 2 (spike C++)**, con permiso: bajar las cabeceras de OpenCascade 8.0 (código fuente, solo `.hxx`) y
  `pybind11` ≥ 3. El compilador y CMake ya están.
- **Rust**: ver `docs/plan_rust.md` sección 8 (`rustup`, `maturin`, crates).
- Distribución: cada módulo nativo agrega un `.pyd` por plataforma al instalador (`instalador/windows/omnicad.iss`);
  sin él, la app sigue funcionando con el Python actual, más lenta.

## 9. Riesgos honestos

- **El acople con `cadquery-ocp` es lo más frágil del plan.** Cada actualización del paquete (otra versión de OCCT u
  otro MSVC) puede romper el módulo C++ en proceso. Por eso el proceso trabajador (B) es la vía por defecto y el
  módulo en proceso se limita a C1 y C2.
- **C++ no acelera lo que ya es C++.** El tiempo de booleanas, roscas y HLR está dentro de OpenCascade; lo que se
  gana es no esperar (hilos/procesos), cancelar y no cruzar la frontera por elemento.
- **La RAM manda.** 13 GB y 185 MB por trabajador de OCP: limitar a 2–3 trabajadores, no a los 12 hilos lógicos.
- **Mantenimiento**: tres lenguajes. Mitigación: cada función nativa tiene su par Python de referencia, pruebas de
  paridad y fallback automático (`omnicad/nativo.py`).
