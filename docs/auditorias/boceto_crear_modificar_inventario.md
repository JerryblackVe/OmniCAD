# Inventario de CREAR y MODIFICAR del boceto (fase 1, 2026-11-07)

Fase 1 de [auditoria_boceto_crear_modificar.md](../auditoria_boceto_crear_modificar.md). Fuentes: grupos «CREAR» y
«MODIFICAR» de `clon/omnicad/ui/cinta_boceto.py`, tabla de acciones de `ui/modo_boceto.py`, `ui/editor_boceto.py`, el
núcleo en `restricciones/boceto.py` (abajo, **NB**) y el MCP en `api/herramientas_*.py`. La matriz de pruebas es
[`clon/tests/test_boceto_crear_modificar_matriz.py`](../../clon/tests/test_boceto_crear_modificar_matriz.py): un caso por
clave, por la API, con números y guardar/abrir (`get_recipe` → `apply_recipe`). Resultado: `48 passed, 5 xfailed`.

Estado de cada fila: **VERIFICADO** = tiene caso en la matriz y da los números pedidos; **CUBIERTO** = sin caso en la
matriz pero con test propio (columna Test); ninguna fila está probada todavía desde la ventana como usuario (fase 6).

## 1. CREAR (42 claves)

| Clave | MCP | Núcleo | Test | Estado |
|---|---|---|---|---|
| sk_linea | `draw_line` | NB `agregar_linea` | matriz | VERIFICADO |
| sk_linea_medio | `draw_line` `midpoint=True` | NB `agregar_linea_medio` | matriz | VERIFICADO |
| sk_rectangulo | `draw_rectangle` (esquinas) | NB `agregar_rectangulo` | matriz | VERIFICADO |
| sk_rectangulo_3p | `draw_rectangle` `three_points` | NB `agregar_rectangulo_3p` | matriz | VERIFICADO |
| sk_rectangulo_centro | `draw_rectangle` centro + `center_diagonals` | NB `agregar_rectangulo_centro` | matriz | VERIFICADO |
| sk_circulo | `draw_circle` `center_radius` | NB `agregar_circulo` | matriz | VERIFICADO |
| sk_circulo_2p / _3p | `draw_circle` `two_points` / `three_points` | cálculo en ED:1783-1799 y en la API (copia) | matriz | VERIFICADO |
| sk_circulo_2t / _3t | `draw_tangent_circle` | NB `agregar_circulo_tangente` | matriz | VERIFICADO |
| sk_arco / _centro | `draw_arc` (3 puntos / centro + barrido) | NB `agregar_arco_3_puntos` / `agregar_arco_centro` | matriz | VERIFICADO |
| sk_arco_tangente | `draw_arc` `tangent_to` | ED:1635 y HB:380 (copia) | matriz | VERIFICADO |
| sk_poligono_inscrito / _circunscrito / _arista | `create_polygon` `kind` | ED:1659 y HB:445 (copia) | matriz | VERIFICADO |
| sk_elipse | `draw_ellipse` | NB `agregar_elipse` | matriz | VERIFICADO |
| sk_ranura_* (5) | `draw_slot` `kind` | NB `agregar_ranura` | matriz (áreas) | VERIFICADO |
| sk_spline_ajuste / _control | `draw_spline` `spline_type` | NB `agregar_spline` | matriz | VERIFICADO |
| sk_conica | `draw_conic` | NB `agregar_conica` | matriz | VERIFICADO |
| sk_punto | `draw_point` | NB `agregar_punto` | matriz | VERIFICADO |
| sk_texto / sk_desglosar_texto | `add_text` / `explode_text` (`herramientas_vectores.py`) | NB `agregar_texto` / `desglosar_texto` | matriz | VERIFICADO |
| sk_simetria | `mirror_sketch` | NB `simetria` | matriz | VERIFICADO |
| sk_patron_circular / _rectangular | `sketch_circular_pattern` / `sketch_rectangular_pattern` | NB `patron_circular` / `patron_rectangular` | matriz | VERIFICADO |
| sk_editar_patron | `edit_sketch_pattern` | NB `editar_patron` | matriz | VERIFICADO |
| sk_cota | `add_dimension` | NB `agregar_cota` | matriz | VERIFICADO |
| sk_espiral | `draw_spiral` | NB `puntos_espiral` + `agregar_spline` | matriz | VERIFICADO |
| sk_proyectar / sk_intersecar | `project_to_sketch` `mode` | NB `agregar_proyeccion` | `test_api_boceto_herramientas.py` | CUBIERTO |
| sk_incluir_3d | `include_3d_geometry` | `boceto3d.agregar_desde_mundo` | `test_proyeccion_seccion.py` | CUBIERTO |
| sk_perfil_giratorio | `project_spun_profile` | `nucleo/perfiles.proyectar_giro_forma` | `test_boceto_fase6.py` | CUBIERTO |
| sk_isoparametrica | `isoparametric_curve` | `curvas3d.isoparametricas` | `test_isoparametrica.py` | CUBIERTO |
| sk_proyectar_eje | `project_to_sketch` `references=["Z"]` | NB `agregar_proyeccion` | `test_boceto_fase9_ui2.py` | CUBIERTO (ver hallazgo 8) |
| sk_romper_vinculo | `break_projection_link` | NB `romper_vinculo` | `test_boceto_fase6.py` | CUBIERTO |
| sk_proyecciones_perdidas | `manage_lost_projections` | NB `eliminar_proyeccion` / `revincular` | `test_boceto_fase6.py` | CUBIERTO |

## 2. MODIFICAR (13 claves)

| Clave | MCP | Núcleo | Test | Estado |
|---|---|---|---|---|
| sk_empalme | `sketch_fillet` | NB `empalme` | matriz | VERIFICADO |
| sk_chaflan / _dist_angulo / _dos_dist | `sketch_chamfer` (`distance`, `angle`, `distance2`) | NB `chaflan` | matriz | VERIFICADO |
| sk_curva_fusion | `draw_blend_curve` | NB `curva_fusion` | matriz | VERIFICADO |
| sk_desfase | `offset_sketch_curves` | NB `desfasar` / `desfase` | matriz | VERIFICADO |
| sk_soltar_desfase | `release_offset` | NB `soltar_desfase` | matriz | VERIFICADO |
| sk_recortar | `trim_sketch_curve` | NB `recortar` | matriz | VERIFICADO (alargar: B-237) |
| sk_alargar | `extend_sketch_curve` y `trim_sketch_curve mode=extend` | NB `alargar` | matriz | VERIFICADO |
| sk_partir | `split_sketch_curve` y `trim_sketch_curve mode=break` | NB `partir` | matriz | VERIFICADO |
| sk_escala | `transform_sketch` `scale` | NB `escalar` | matriz | VERIFICADO |
| sk_mover (y copiar) | `transform_sketch` `dx/dy/angle/copy` | NB `transformar` | matriz | VERIFICADO (copiar: B-236) |
| parametros | `create_parameter` / `set_parameter` | `timeline/documento.aplicar_parametros` | matriz | VERIFICADO |

Qué hace MODIFICAR con las restricciones de la curva original (leído en el código y reproducido donde dice):
- **Recortar / Partir / Alargar** conservan el id del tramo que queda. Los tramos nuevos solo quedan ligados con
  `colineal` o `igual`. Las cotas de largo y los `punto_medio` se borran (`_sin_cotas_de_largo`). Lo puesto sobre el
  extremo que se va queda en un punto suelto (B-233, reproducido).
- **Empalme** línea-línea re-apunta las cotas de largo a un «vértice virtual»; en paralelas y en el caso general las borra.
- **Desfase** no toca la original; **Soltar desfase** borra el desfase, la paralela y la cota del par.
- El editor avisa «Las restricciones o las cotas se han eliminado…» si desaparece un id; el MCP no avisa (P-68).

## 3. Fusion contra OmniCAD (opciones del diálogo)

Fuente: `docs/fusion_docs/contenido/fusion-sketch/` (`scripts/fusion_docs.py ver …`). Casi ningún artículo trae la
lista del diálogo; se compararon los datos que pide cada comando. Sin diferencias en: rectángulos, círculos, arcos,
polígonos, elipse, ranuras, cónica, punto, texto, simetría, patrones, proyecciones, cota, curva de fusión, desfase,
recortar, alargar, partir y escala. Diferencias:

| Comando | Fusion | OmniCAD | Fila |
|---|---|---|---|
| Spline de puntos de control | Grado 5 por defecto (`spline-degree-control-reference-…md`) | Grado 3 por defecto (ED:647, `draw_spline degree=3`) | P-67 |
| Empalme y chaflán | Se puede elegir el vértice (un punto en dos líneas) | Pide las dos curvas | H-107 |
| Línea | Arco tangente arrastrando desde el extremo, dentro de la misma cadena | Arco tangente aparte (`draw_arc tangent_to`) | H-108 |
| Mover/Copiar | Puede sacar la geometría del plano (boceto 3D) | Solo en el plano (`transform_sketch`); 3D aparte en `transform_sketch_3d` | sin fila: Fusion no da más detalle |
| SOLIDWORKS | — | — | sin dato comprobado |

## 4. Hallazgos

| # | Hallazgo | Evidencia | Fila |
|---|---|---|---|
| 1 | Escalar ×2 un rectángulo de 40 × 20 con chaflán 2: área 2707,75 en vez de 3192. Moverlo +100 en x: área 282 en vez de 798 (se deforma). El vértice virtual del chaflán no entra en `puntos_de(ids)` (NB `escalar` y `transformar`) | `test_b232_…` | CORREGIDO (B-232, 2026-11-07); gemelo al copiar: B-236 |
| 2 | Recortar una línea cuyo extremo tenía «fijo»: la línea termina en un punto nuevo y el «fijo» queda en el punto viejo, suelto | `test_b233_…` | CORREGIDO (B-233, 2026-11-07); gemelo en Alargar: B-237 |
| 3 | `puntos_espiral` acepta 5000 vueltas (40 001 puntos); el tope de 24,875 vueltas está solo en `draw_spiral`: desde la ventana se puede colgar | `test_b234_…` | CORREGIDO (B-234, 2026-11-07) |
| 4 | `sketch_chamfer(angle="ang")` guarda la cota de ángulo como «30»: pierde el parámetro (la distancia sí conserva la expresión) | `test_b235_…` | CORREGIDO (B-235, 2026-11-07) |
| 5 | El MCP borra restricciones y cotas sin decirlo (empalme, chaflán, recortar, mover con giro) y no revierte cuando la edición sobre-restringe (solo `extend_sketch_curve` y `split_sketch_curve` usan `_exigir_sin_conflicto`) | lectura: `herramientas_boceto.py:597-614`, `herramientas_boceto_extra.py:55` | P-68 |
| 6 | Tres caminos del MCP para alargar y partir con validaciones distintas (`trim_sketch_curve mode=extend/break` no comprueba el punto ni el conflicto) | lectura: `herramientas_boceto_extra.py:40-55` | P-69 |
| 7 | Lógica repetida entre la ventana y la API: polígono (ED:1659 / HB:445), arco tangente (ED:1635 / HB:380), círculo 2p/3p; tope de lados en dos lugares | lectura | P-70 |
| 8 | `tests/test_cobertura_ui_api.py` asocia `sk_proyectar_eje` a `project_spun_profile`, que exige un perfil; lo que hace el botón es `project_to_sketch(references=["Z"])` | lectura: `test_cobertura_ui_api.py:143` | P-70 |
| 9 | Otros, sin verificar todavía: el editor ignora el radio en un empalme entre paralelas sin avisar (el MCP avisa); el editor no ofrece «conservar cota» al soltar un desfase (`release_offset keep_dimension`); escala sin punto base en el MCP usa el centro de la caja | lectura del lector de MODIFICAR | P-71 |
| 10 | Etiqueta muerta en inglés `_i("Helix / Spiral", "sk_espiral")` en `cinta_boceto.py:35` (la cinta muestra «Espiral» de `modo_boceto.py`; `ui/cinta.py:423-426` ignora el texto cuando hay clave) | lectura | CORREGIDO en esta fase (texto «Espiral») |
