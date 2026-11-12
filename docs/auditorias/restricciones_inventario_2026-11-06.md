# Inventario de restricciones y cotas del boceto 2D (fase A, 2026-11-06)

Fase A de la auditoría de restricciones ([especificación](../auditoria_restricciones.md)). Hecho leyendo el código de
`main` en `c63f2a4` (archivo:línea de ese commit) y comprobado con `clon/tests/test_restricciones_matriz.py`: cada
restricción y cota cumple su relación con números, persiste al guardar y quita los grados de libertad (GDL) de la tabla.
Los GDL marcados «(M)» los confirma esa matriz. Lo pendiente vive en `docs/seguimiento/`; las «Sospechas» del final se
verifican en la fase B.

Archivos: `boceto.py` = `clon/omnicad/restricciones/boceto.py`; `solver.py` = `clon/omnicad/restricciones/solver.py`;
`editor` = `clon/omnicad/ui/editor_boceto.py`; `api` = `clon/omnicad/api/herramientas_boceto.py`.

Resumen: 16 claves de restricción (`TIPOS_RESTRICCION`, `boceto.py:31`), 10 cambiables entre sí (`CAMBIABLES`, `:40`) y
7 tipos de cota (`TIPOS_COTA`, `:42`). Validación en `_validar_restriccion` (`:2566`) y `_validar_cota` (`:2609`). La
cinta (`ui/cinta_boceto.py:45-47`) trae 12 botones de Fusion más `sk_r_poligono` y `sk_autorestringir`.

## 1. Restricciones

| Clave | Entidades (orden exigido por la validación) | Ecuación en `solver.py` | GDL | Botón | MCP `add_constraint` | Observaciones |
|---|---|---|---|---|---|---|
| `coincidente` | `[punto, punto]` o `[punto, curva]`, punto primero (`boceto.py:2570`) | pp: fusiona incógnitas (`:177`); p-línea: distancia con signo (`:339`); p-círculo: `‖p−C‖−R` (`:341`); p-elipse (`:343`); p-spline: t auxiliar (`:572`) | pp 2 (M), p-curva 1 (M) | sí | `coincident` | La ventana pone el punto primero (`editor:4799`); la API no (B-224) |
| `horizontal` / `vertical` | `[línea]` o `[punto, punto]` | misma y / misma x (`:349`), fusiona incógnitas (`:179`) | 1 (M) | uno solo (`horizontal_vertical`) | `horizontal`, `vertical` | La ventana elige por `|dx|≥|dy|`; la API pide el tipo |
| `paralela` | `[línea, línea]` | cruz normalizada (`:352`) | 1 (M) | sí | `parallel` | |
| `perpendicular` | `[línea, línea]` | producto escalar normalizado (`:361`) | 1 (M) | sí | `perpendicular` | `_salir_del_paralelismo` (`:878`) gira 90° si ya son paralelas |
| `igual` | 2 líneas, 2 circulares o 2 elípticas | largos (`:365`), radios (`:370`), semiejes (`:367`) | 1 (M); elipses 2 | sí | `equal` | Fusion se ajusta al primero; OmniCAD mueve lo que convenga |
| `tangente` | dos geometrías salvo línea-línea (`:2577`) | encadenadas (`:585`), línea-círculo (`:596`), círculo-círculo (`:601`), línea-elipse (`:613`), general con t auxiliares (`:626`) | 1 (M) | sí | `tangent` | La ventana pone la línea primero y desliza a la tangente |
| `concentrica` | 2 entre círculo, arco, elipse, arco de elipse | centros iguales (`:381`) | 2 (M) | sí | `concentric` | Fusion acepta dos o más |
| `punto_medio` | `[punto, línea]` o `[punto, arco]`, punto primero | `p−(a+b)/2` (`:389`); arco `C(t/2)` (`:383`) | 2 (M) | sí | `midpoint` | B-224 |
| `fijo` | cualquier entidad (`:2580`) | coordenadas a constantes (`_fijos :850`) | 2 por punto; línea 4 (M) | sí | `fix` | Repetido sobre el mismo conjunto devuelve el id existente |
| `colineal` | `[línea, línea]` | extremos de l2 sobre l1 (`:395`) | 2 (M) | sí | `collinear` | Fusion acepta dos o más |
| `simetrica` | par de puntos, líneas, cónicas, circulares, elípticas o splines + eje último (`:2584`) | medio en el eje y segmento normal (`_simetria :690`) | pp 2 (M) | sí | `symmetry` | La ventana no reordena: el eje va último, como en Fusion |
| `curvatura` | spline o cónica + curva abierta encadenada (`:2591`) | `[cruz·10, (k_a+k_b)·100]` (`:373`) | 2 (M) | sí | `curvature` | La matriz mide GDL y persistencia; la G2 la miden los tests de fase 7 |
| `poligono` | ≥3 líneas en cadena cerrada (`:2593`) | vértices en círculo (`_poligono :640`) | `2m−4`; triángulo 2 (M) | sí | `polygon` | Un lado toma su cadena |
| `desfase` | 4 geometrías, `[geom, punto, punto]` o 2 curvas libres (`:2594`) | `:410`, `:413`, `_desfase_libre :527` | 1 | herramienta Desfase | `offset_sketch_curves` | Tests: `test_boceto_fase9_desfase.py` |
| `patron` | `[punto, punto]` o 3 puntos | traslación o giro (`:424`) | 2 | herramientas de patrón | `sketch_*_pattern` | Tope 1000 copias (`boceto.py:55`; BOC-61: las copias no son incógnitas del solver) |

## 2. Cotas

| Clave | Entidades | Ecuación | GDL | MCP `add_dimension` | Observaciones |
|---|---|---|---|---|---|
| `distancia` | pp, línea, p-línea, línea-p, línea-línea, p-spline, círculo/arco con punto, línea o circular (`boceto.py:2612`) | pp `:485`, largo `:487`, p-línea `:488`, línea-línea `:494`, círculo `:499`, p-spline `:513` | 1 (M) | `distance` | Modo centro/tangente con círculos (`admite_modo :2069`) |
| `distancia_h` / `distancia_v` | `[punto, punto]` o `[línea]` | `s·Δx−v` / `s·Δy−v` (`:473`) | 1 (M) | `horizontal`, `vertical` | La ventana solo las crea con 2 puntos |
| `radio` / `diametro` | círculo o arco | `R−v` / `2R−v` (`:449`) | 1 (M) | `radius`, `diameter` | `cambiar_cota` pasa una a la otra (`boceto.py:2073`) |
| `angulo` | dos líneas no paralelas | `atan2(|cruz|,dot)−v` con cuadrante (`:464`) | 1 (M) | `angle` | La API exige 0<v<180 (`api:2118`) |
| `desfase` | dos líneas, dos circulares, spline/elipse con spline, elipse-elipse (`:2621`) | `:452` | 1 | `offset` | Negativo pasa al otro lado |

Cotas de referencia (`referencia=True`): miden sin restringir; el solver las saltea (`solver.py:443`). Una cota que
sobre-restringiría pasa sola a referencia (`api:1617`).

## 3. Restricciones automáticas

- **Al dibujar** (`restricciones/inferencia.py`, familias en `TIPOS_INFERENCIA :15`): horizontal/vertical, coincidente
  (punto, sobre curva, intersección), punto medio, tangente, perpendicular, paralela/colineal, igual.
- **Herramientas que dejan restricciones:** rectángulo (2 H + 2 V, `boceto.py:1443`), rectángulo central (punto medio),
  de 3 puntos (perpendicular + 2 paralelas), elipse, ranuras (tangente + igual), polígono, empalme y chaflán (tangente),
  espejo (simetría + igual), patrones, y el primer punto en el origen (`fijo` con `origen`, `:2023`).
- **AutoConstrain** (`auto_restringir`, `solver.py:1442`; etapas en `auto_candidatos.py:338`): coincidente/concéntrica →
  H/V → colineal → paralela → perpendicular → tangente → igual → punto medio → simetría; cada candidato entra solo si baja
  los GDL (`probar :1365`); después las cotas (`_cotas_auto :1403`). Tope 500 entidades. API: `auto_constrain`,
  `suggest_auto_constraints`; diagnóstico: `find_redundant_constraints`, `find_underconstrained`.

## 4. Fusion vs OmniCAD

Ayuda en `docs/fusion_docs/contenido/fusion-sketch/` (buscar con `scripts/fusion_docs.py buscar … -s fusion-sketch`).
SOLIDWORKS: sin dato comprobado en esta fase.

| Restricción | Fusion (artículo) | Diferencia con OmniCAD |
|---|---|---|
| Coincident | dos puntos, o punto y curva (`add-a-coincident-constraint-to-a-sketch-1d724724c9a.md`) | La API exige el punto primero (B-224) |
| Collinear | dos o más objetos (`add-a-collinear-…-d17ea191931.md`) | OmniCAD: solo dos |
| Concentric | dos o más arcos, círculos o elipses (`add-a-concentric-…-81d14885fa2.md`) | OmniCAD: solo dos |
| Midpoint | punto u objeto al medio de otro (`add-a-midpoint-…-89a700c4908.md`) | OmniCAD: punto con línea o arco. La ayuda no confirma que Coincidente tome el medio de una línea |
| Fix/Unfix | elegir de nuevo desfija (`add-a-fixed-…-fe87081770f.md`) | La API desfija borrando la restricción |
| Parallel | dos líneas | Sin diferencia |
| Perpendicular | dos objetos a 90° | OmniCAD: solo líneas |
| Horizontal/Vertical | toma el eje más cercano | La API no tiene el modo automático |
| Tangent | curva y objeto se tocan sin cruzarse | Sin diferencia visible |
| Curvature | G2 spline-spline o spline-curva | Sin diferencia; falta en la descripción de la API |
| Equal | se ajusta al primero elegido | OmniCAD no prioriza el primero |
| Symmetry | dos o más objetos respecto de una línea | OmniCAD: de a pares |
| Offset / Pattern | un lado, dos lados, simétrico / rectangular y circular | Equivalente |
| Sketch Dimension | líneas paralelas: lineal; no paralelas: angular | La API acepta `distance` entre líneas no paralelas (S2) |
| AutoConstrain | tope 250 entidades, requiere conexión | OmniCAD: tope 500, local |

## 5. Sospechas (para la fase B)

| N.º | Sospecha | Dónde |
|---|---|---|
| S1 | La ventana no valida el rango de la cota de ángulo (la API sí, 0<v<180): 200° o −30° no se pueden cumplir | `boceto.py:189`; `editor:4402`, `:4653`; `api:2118`; `solver.py:471` |
| S2 | `distancia` entre dos líneas mide solo `p1` de la segunda; la API la acepta aunque no sean paralelas | `boceto.py:2462`, `:2612`; `solver.py:494` |
| S3 | AutoConstrain agrega un punto en (0,0) y un `fijo` fuera de `probar`: no cuenta para el límite ni aparece en `added` | `solver.py:1406-1412` |
| S4 | `_pares_simetricos` usa `puntos()` (con manijas) con `zip(strict=True)`; la validación compara `.pts` | `solver.py:669`; `boceto.py:2588` |
| S5 | El desfase libre de spline/elipse deja t auxiliares sin fijar: GDL de más | `solver.py:547-560` |
| S6 | Un tipo desconocido da `KeyError` en vez de `ErrorBoceto`; solo `fijo` se deduplica | `boceto.py:1990`, `:2600` |
| S7 | Las descripciones de `add_constraint`/`add_dimension` omiten tipos que sí aceptan | `api:1423-1437`, `:1538-1543` |
| S8 | La ventana alterna `fijo` comparando listas con orden; el modelo compara conjuntos | `editor:4793`; `boceto.py:1992` |
| S9 | `grados_de_libertad` arma el sistema sin `fusionar` ni `_salir_del_paralelismo`: perpendicular entre paralelas exactas puede dar GDL de más | `solver.py:1213` frente a `:919` |
| S10 | AutoConstrain no acota elipses ni splines | `solver.py:1405-1426` |
| S11 | Sin test de API para `add_constraint` con `midpoint`, `symmetry`, `curvature`, ni `add_dimension` con `offset` | grep en `clon/tests/` |
| S12 | La ventana no crea `distancia_h`/`distancia_v` de una línea sola | `editor:4701`, `:4716` |
| S13 | Simetría con el eje primero falla con un mensaje que no orienta | `editor:4803` |

Bugs ya confirmados (en `docs/seguimiento/bugs.md`): B-224, B-225, B-226. Los tres tienen un caso `xfail` estricto en
`test_restricciones_matriz.py`, que se pone rojo cuando se arreglan.

## 6. Resultado de la fase B (diagnóstico, 2026-11-06)

Comprobado con casos mínimos sin ventana (`Boceto` + `solver`), sobre `main` en `049b9ab`.

| Sospecha | Resultado | Fila |
|---|---|---|
| S1 ángulo fuera de rango | CONFIRMADA: 200° y −30° entran y `resolver` da `ok=False` | B-227 |
| S2 distancia entre líneas no paralelas | CONFIRMADA: `ok=True`, solo el `p1` de la segunda línea queda a la distancia | B-228 |
| S3 AutoConstrain y el origen | CONFIRMADA: crea un punto suelto nuevo en (0,0) con `fijo` | B-229 |
| S4 simetría de splines con manijas | NO REPRODUCIDA (spline de ajuste contra spline de control: `ok=True`) | — |
| S5 desfase libre y GDL | NO VERIFICADA (falta un caso mínimo de desfase de spline) | — |
| S6 tipo desconocido | CONFIRMADA: `KeyError: 'inventada'`. Además, una `horizontal` repetida sobre la misma línea entra dos veces en el modelo (los GDL quedan bien; la ventana la rechaza por no quitar GDL) | B-230 |
| S7 descripciones de la API | CONFIRMADA al leer: `add_constraint` no nombra `curvature` ni las elipses en `equal`; `add_dimension` no nombra spline ni elipse en `offset` | Se corrige en la fase C |
| S8 desfijar con otro orden | NO VERIFICADA (es de la ventana) | — |
| S9 GDL de perpendicular entre paralelas | NO REPRODUCIDA: baja de 8 a 7, `ok=True` | — |
| S10 AutoConstrain sin cotas de elipse ni spline | Faltante, no bug: queda para la fase F | — |
| S11 cobertura de la API | En parte cubierta por la matriz; los tests de API de `midpoint`, `symmetry`, `curvature` y `offset` se suman en la fase C | — |
| S12 cota H/V de una línea sola en la ventana | NO VERIFICADA (es de la ventana) | — |
| S13 mensaje de simetría con el eje primero | NO VERIFICADA (es de la ventana) | — |
