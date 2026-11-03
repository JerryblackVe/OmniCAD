# Bugs

Algo que falla, da un resultado malo o un mensaje engañoso. Método y columnas: [README](README.md).

Solo lo que falta resolver: al resolverse, la fila se borra. Verificado contra el código el 2026-10-23 (Superficie y Sólido, también en la ventana real: 2026-10-24; revisión de B-39 y regresiones de B-48: 2026-10-27). Tortura de operaciones y booleanas: 2026-11-01. Total 33: Abierto 27 · Parcial 4 · Bloqueado 1 · Sin verificar 1 (recontado 2026-11-02).

## Abiertos y parciales

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| B-184 | Dividir un cuerpo importado de STEP deja una mitad con volumen negativo y el paso sale ok | Abierto | Alta | Cuerpo7 quedó en −46.885 mm³ y −33.256 mm², y Cuerpo3 en 65.205 mm³. `check_geometry` en vivo sobre ese documento trabó la ventana más de 5 min. Falta reproducirlo en proceso aparte. | omnicad/nucleo/solidos_modificar.py:1564 | 2026-11-02 |
| B-177 | El sentido de una unión con origen en arista circular se invierte si el padre gira | Abierto | Alta | Con el padre a más de unos 45° el mismo valor mueve al revés: −207,9 mm en vez de −56,9. Con origen en cara plana no pasa. | omnicad/api/herramientas_ensamble.py:725 | 2026-11-02 |
| B-178 | Lo creado después de una unión no la sigue al accionarla | Abierto | Alta | Agujeros y fijaciones con puntos absolutos salen corridos y el recálculo da REFERENCE_LOST. Esquive: uniones al final del timeline. | omnicad/api/herramientas_ensamble.py:650 | 2026-11-02 |
| B-179 | La suma de filas de la lista de materiales no da la masa total | Abierto | Media | Filas 77,41 kg contra total 79,54 kg, con todos los cuerpos en alguna fila. | omnicad/api/herramientas_material.py:200 | 2026-11-02 |
| B-181 | Un spline cerrado con control_points da PROFILE_NOT_CLOSED | Abierto | Media | Reproducido: `closed` se ignora en `control_points` (aviso al crearla), quedan 0 perfiles y `extrude` da PROFILE_NOT_CLOSED. El docstring de `draw_spline` dice que `closed` cierra solo la de ajuste. | omnicad/api/herramientas_boceto.py:1950 | 2026-11-02 |
| B-183 | section_view no aparece en render_image | Abierto | Media | Reproducido: `section_view` da área 1600 mm² sobre una caja de 40³, pero `render_image` sale idéntico con la sección visible u oculta (0 de 76 800 píxeles distintos). | omnicad/api/herramientas_analisis.py:439 | 2026-11-02 |
| B-172 | Pedir propiedades de un cuerpo recién solevado cerró la app | Abierto | Alta | Violación de acceso en TKernel dentro de `_por_malla`, una vez en vivo; no se repite abriendo el autoguardado. Falta aislar esa medición o validar el sólido antes. | omnicad/nucleo/geometria.py:1034 | 2026-11-02 |
| B-173 | Solevación de 3 splines cerrados sale ok con el sólido plegado, y check_geometry da válido | Abierto | Alta | Da 40 % del volumen esperado y el orden de las secciones cambia el resultado sin avisar. `valid` y `all_valid` siguen en true con un problema de severidad error. | omnicad/api/herramientas_revision.py:74 | 2026-11-02 |
| B-176 | export_sketch a SVG invertiría el sentido de los arcos | Sin verificar | Baja | No se reproduce con arcos simples: el flag del SVG es correcto por cuenta y por ida y vuelta. Falta probar el boceto original de la cartera, donde salieron cóncavos. | omnicad/io_archivos/svg.py:410 | 2026-11-02 |
| B-170 | La vista previa de Solevación cierra la app | Abierto | Alta | Con perfiles elegidos, `BRepOffsetAPI_MakePipeShell` da una violación de acceso dentro de la previa, en `solevar`: se cae la ventana entera. La previa tiene que correr aislada o validar antes. | nucleo/solidos_crear.py:1321 | 2026-11-02 |
| B-171 | Un desfase grande da autointersecciones y sale ok | Abierto | Media | `offset_edges` de 15 mm y `offset_surface` de 400 mm dejan el cuerpo nuevo con autointersecciones. Falta ver qué hace Fusion y si corresponde un aviso. | api/herramientas_solido.py | 2026-11-02 |
| B-168 | Un tubo por aristas con esquinas da autointersecciones y sale ok | Abierto | Media | `create_pipe` sobre tres aristas de un cuerpo que forman esquinas: 1 autointersección en el cuerpo nuevo. Falta ver cómo resuelve Fusion las esquinas y si corresponde un aviso. | api/herramientas_solido_extra.py | 2026-11-02 |
| B-159 | Un empalme chico sobre un vaciado cierra la app | Abierto | Alta | Caja 60 × 50 × 40, vaciado de 1 mm quitando la base y empalme de 1 mm en E10: `BRepFilletAPI_MakeFillet.Build` da una violación de acceso y se cae todo el programa. Hay que ver por qué no lo frena el `try`: un cierre nativo no es una excepción de Python; correrlo aislado o validar antes. | nucleo/solidos_modificar.py:548 | 2026-11-02 |
| B-158 | Labio sobre una esfera cierra la app | Abierto | Media | `create_lip_groove` sobre la arista de costura de una esfera mide un alambre sin largo y da una violación de acceso. Falta rechazar esa arista con un error claro. | nucleo/solidos_crear.py:236 | 2026-11-02 |
| B-160 | Un STEP con bytes alterados cierra la app | Abierto | Alta | `STEPCAFControl_Reader.ReadFile` da una violación de acceso con el archivo de `tests/corpus_caza/`. Abrir STEP de otros tiene que correr en el proceso aislado (`nucleo/aislado.py`), o la app cae con un archivo ajeno. | nucleo/intercambio.py:225 | 2026-11-02 |
| B-162 | Un chaflán mayor que el radio deja el sólido abierto y el paso sale ok | Abierto | Media | Cilindro de radio 10 y chaflán de 15 en su arista: cuerpo sólido y no estanco, sin error. Falta rechazarlo o cerrar la forma, comparando con Fusion. | nucleo/solidos_modificar.py | 2026-11-02 |
| B-163 | Extender superficie sobre un sólido lo deja abierto | Abierto | Media | `extend_surface` en una arista de una caja da ok; el cuerpo sigue como sólido, no estanco, y en cadenas llegó a volumen negativo. `untrim_surface` sobre un sólido hace lo mismo. Falta rechazarlo en sólidos o pasarlo a superficie. | api/herramientas_superficie.py | 2026-11-02 |
| B-164 | Extruir varias caras a la vez deja un cuerpo roto | Abierto | Media | Con caras de distinta orientación el cuerpo nuevo sale con volumen 0 o con autointersecciones, y el STEP exportado pierde ese cuerpo. Falta rechazarlo o extruir cada cara aparte. | timeline/operaciones.py | 2026-11-02 |
| B-165 | Un agujero tangente a dos paredes deja aristas no manifold y sale ok | Abierto | Media | Agujero de 60 mm en una cara de 60 mm de ancho: pasa justo por las dos paredes. Falta decidir si da error o aviso, comparando con Fusion. | nucleo/solidos_crear.py | 2026-11-02 |
| B-166 | Desfasar caras de una superficie la deja inválida y sale ok | Abierto | Media | `offset_surface` y después `offset_faces` de 40 mm sobre la cara nueva: `check_geometry` da inválido. El paso tendría que fallar o avisar. | nucleo/solidos_modificar.py | 2026-11-02 |
| B-167 | El patrón geométrico sobre chapa da autointersecciones y sale ok | Abierto | Media | Dos caras de una pestaña con los valores por defecto: 2 autointersecciones. Falta ver si las copias se pisan y si tiene que unirlas o avisar. Con una distancia de 2 mm sobre una cara grande tarda más de 40 s y no se puede cortar. | api/herramientas_solido_extra.py | 2026-11-02 |
| B-157 | Un empalme o chaflán más grande que la pared de un vaciado deja aletas y el paso sale ok | Abierto | Alta | El corte exterior atraviesa la pared y las caras de la cavidad quedan sueltas por fuera. El cuerpo da válido y estanco, pero con 16 autointersecciones: falta detectarlo y decidir qué hace cada caso comparando con Fusion. | omnicad/nucleo/solidos_modificar.py:496 | 2026-11-02 |
| B-153 | Teselar deja abiertas las caras muy finas que OpenCascade abandona a medio mallar | Abierto | Media | Rugged Box `obj_3`: unas 25 de 1088 caras quedan con menos triángulos que nodos (cara 708: 67 nodos y 2 triángulos). El nodo sin llenar ya no llega a la malla (B-151), pero la malla sale abierta y `compare_to_mesh` da `closed: false`. Falta rellenar esas caras con sus aristas o reintentar con otro parámetro. | nucleo/geometria.py `_nodos_de_la_cara`; tests/test_geometria.py::test_b151_un_nodo_sin_llenar_de_una_cara_a_medio_mallar_no_llega_a_los_triangulos | 2026-11-01 |
| B-149 | Radio mínimo sin radio mínimo pinta de rojo las paredes enteras de un vaciado | Parcial | Baja | El panel y `min_radius` de la API ya pintan una banda junto al rincón. Un análisis guardado antes, y la API sin `min_radius`, siguen igual para que un documento viejo se vea igual: decidir si también cambian. | nucleo/analisis.py (`colores_radio_minimo`); tests/test_inspeccionar_fusion.py | 2026-11-01 |
| B-144 | Cortar con una esfera casi tangente a una pared puede quitar de menos sin avisar | Abierto | Media | Hueca de pared 3 (caja 60×40×20 menos 54×34 desde z = 3) y esfera r 4 en (18,537165, 20,0001, 10,0001): cortar quita 103,79 mm³ de 122,5 (antes de B-125 quitaba 0) y el común da 121,97. Las muestras de `_comun_desmentido` solo ven diferencias de 1/4 de la pieza chica. | clon/tests/test_booleanas_tortura.py::test_b125_esfera_casi_tangente_no_se_queda_sin_cortar | 2026-11-01 |
| B-154 | Un paso viejo con un pedazo de letra partida, elegido a mano, ya no calcula | Abierto | Media | Volver a elegir el texto en ese paso. Ese pedazo dejó de existir con B-134 y la referencia no guarda con qué distinguir la letra de su hueco. | clon/omnicad/nucleo/perfiles.py › `buscar_por_firma_tolerante` | 2026-11-01 |
| B-123 | Un cuerpo que pasa a otro componente sigue a la unión del componente anterior | Abierto | Media | Si TODOS los cuerpos de un componente nuevo vienen del mismo componente movido por una unión, el nuevo hereda ese movimiento (`_matriz_de_cuerpos`): no salta de lugar, pero al accionar después esa unión el cuerpo se sigue moviendo, aunque ya no pertenece a ese componente y el aviso de ASM-7 diga que sus uniones ya no mueven nada. En Fusion el cuerpo queda donde estaba al reasignarlo. Hace falta guardar en la receta la pose del momento de reasignar. Ya pasaba antes de B-108. | omnicad/timeline/ops_ensamblar.py (`_matriz_de_cuerpos`); tests/test_posicion_asm.py::test_b108_todos_del_mismo_componente_el_nuevo_hereda_su_movimiento_y_no_gira_dos_veces | 2026-11-01 |
| B-121 | Volver a resolver un boceto con una tangente general (spline) corre la geometría un poco cada vez | Abierto | Media | En `_tangencia` el contacto arranca de una muestra de 96 puntos, no del contacto exacto: el solver no parte de la solución y reparte el error entre la curva y el parámetro. Medido 2026-10-31 con arco de radio 10 y spline ya tangentes: 10,0000 → 10,0091 → 10,0175 → 10,0254 → 10,0326 por pasada. Arreglarlo cambia lo que dan las recetas guardadas con esas tangentes: decidir antes de tocar el solver (idea: afinar los dos parámetros con la geometría quieta y usarlos solo si el residuo ya es cero) | `tests/test_restricciones_matematica.py::test_tangente_con_el_comando_no_cambia_el_radio_del_arco`; `omnicad/restricciones/solver.py` (`_tangencia`) | 2026-10-31 |
| B-119 | Proyectar un cuerpo curvo visto de costado no da su silueta | Abierto | Alta | Fusion promete perfiles cerrados con el filtro Cuerpos («closed profiles»), pero `proyectar_forma` proyecta solo aristas: un cilindro R14 sobre XZ da 3 líneas abiertas (falta el lado opuesto a la costura) y 0 perfiles; una esfera da una línea o un arco. Hace falta sumar la silueta (HLR de `nucleo/dibujo.py`), con cuidado: un vínculo a un cuerpo la recalcularía en cada paso del timeline, y sobre roscas tarda más de 90 s. Mirado de frente anda bien (cilindro sobre XY: 1 círculo, 1 perfil). | omnicad/nucleo/perfiles.py (`proyectar_forma`); tests/test_proyectar_tarjeta.py::test_cambiar_de_filtro_saca_lo_incompatible_y_lo_dice | 2026-10-31 |
| P-12c | Fuente de novedades de Fusion (la ayuda es un shell JS sin titulares) | Parcial | Baja | Autodesk le responde 403 a los scripts: ahora se lee la última copia de archive.org del blog «What's New» (hoy del 2026-05-16, 5 meses atrás) y el informe lo avisa; falta una fuente al día que no bloquee (feed o API) o seguir revisando a mano. | scripts/novedades.py (`bajar`, `COPIAS`); tests/test_novedades.py::test_fusion_apunta_al_blog_y_cae_a_archive_org_si_autodesk_bloquea | 2026-10-20 |
| P-1c | Wayland nativo: menús emergentes se cierran solos | Bloqueado | Alta | Necesita PC con Linux nativo (ver P-1b): el fallo solo aparece con Wayland y esta PC es Windows, así que no se pudo reproducir ni probar un arreglo; hoy se fuerza xcb y no molesta. | omnicad/ui/__init__.py:11-19 | 2026-10-20 |
| P-11j | Cuerpos «sin ubicar» de XOX (3) que quizá Fusion no tiene | Parcial | Alta | Sherpa resuelto (2026-10-21): comparado con Fusion, no tiene los 2 cuerpos (1593 y 952 mm³) y todos sus componentes con cuerpos están emparejados; ahora se descartan los bloques sin dueño cuando ningún componente de la escena queda sin bloque. Queda XOX: 3 componentes de la escena sin bloque y 3 bloques sin dueño (152,9; 494,8 y 4365,4 mm³): no se pueden descartar sin ver Fusion, y la versión en la nube (v35, 202 componentes) no es la del .f3z local (72 cuerpos): hace falta abrir en Fusion ese mismo archivo. | omnicad/io_archivos/f3d_escena.py (huerfanos); tests/test_p11a_f3d_instancias.py; tests/test_f3d_reales.py | 2026-10-21 |
| B-48 | Crash nativo OCCT (0xc0000005) al recalcular parámetros a 148 pasos | Parcial | Muy alta | La caída no se reprodujo: 300 rondas de una tortura sintética de 141 pasos (paralelismo de OCCT encendido), 60 con el paralelismo apagado y 3 rondas del motor RL-1 con el estado mixto original (r_camara y largo_camara a +30 % y d_eje 6→7,8→6) dieron 0 caídas; apagar el paralelismo no cambió la tasa y costó ~8 % más tiempo. Ya se ensayan en proceso aparte los cambios de parámetros, editar/suprimir/eliminar pasos (también sus vistas previas y la reactivación que alcanza el umbral) y abrir archivos de 60 pasos o más, antes de cargar el BREP; abrir el RL-1 pasó de ~80 a 155,6 s por el ensayo. Segunda ronda (RL-1, 148 pasos: abrir 85,5 s; cambiar d_eje 82,1 s; deshacer 79,7 s; rehacer 78,4 s): el padre ya no repite el cálculo, adopta el resultado del hijo (modelo, estados, dependencias, parámetros derivados; si el hijo cae el documento queda intacto) y la ventana avisa «Calculando en un proceso aparte…» pasado 1 s sin dejar de repintar; Tampoco cayó con el RL-1 abierto en la ventana real, el visor repintando y 23 cambios de d_eje, r_camara y largo_camara de ±30 % en el mismo proceso, sin ensayo en hijo (evidencias/b48_2026-10-27/b48_ventana.py): 0 caídas, 0 pasos con error. Con 60 pasos o más ningún recálculo corre ya en el proceso de la app, así que una caída del kernel ahí solo mata al hijo; queda sin curar la causa en OpenCascade (no reproducida) y lo que corra en el proceso de la app con menos de 60 pasos o fuera del recálculo (visor, exportar). Cuarta tanda (2026-11-01, `evidencias/tortura_2026-11-01/b48.py`): documento propio de 146 pasos y 48 cuerpos (cajas, empalmes, agujeros, uniones, espejos), 47 rondas de 8 cambios de L, H, r y W (±30 % y vuelta) por la API: 0 caídas, 0 pasos con error, el volumen vuelve al inicial en cada ronda (2473289,198), ~3,4 s por cambio, RSS pico 524 MB. | nucleo/aislado.py (prevuelo_parametros, prevuelo_cambio, prevuelo_abrir); timeline/documento.py (_prevuelo_parametros, _prevuelo_cambio); io_archivos/proyecto.py (abrir); nucleo/geometria.py (PARALELO, OMNICAD_SIN_PARALELO); timeline/calculo_aislado.py; tests/test_b48_prevuelo.py; tests/test_b48_calculo_aislado.py; tests/test_b48_prevuelo_ui.py; tests/test_b48_crash.py | 2026-10-27 |

## Boceto (auditoría contra Fusion, 2026-10-23)

Cada fila se reprodujo con una prueba real (scripts de la auditoría, no incluidos en el repo). Plan: [plan_boceto.md](../plan_boceto.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|

## Superficie (auditoría contra Fusion, 2026-10-24)

Cada fila salió de comparar la pestaña SUPERFICIE con los artículos de la ayuda de Fusion (sección Fusion-Patch de `docs/fusion_docs/`) y de probar las 14 herramientas por MCP/CLI. Los bugs se reprodujeron; los scripts de prueba (`sonda*.py`) están en `evidencias/superficie_2026-10-24/`, fuera de git.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|

## Sólido (auditoría contra Fusion, 2026-10-24)

Cada fila salió de comparar la pestaña SÓLIDO (y PLÁSTICO, CONSTRUIR, INSPECCIONAR, INSERTAR, SELECCIONAR) con los artículos de la ayuda de Fusion (carpeta `fusion-model`) y de probar unas 70 herramientas por API con valores normales, de borde e inválidos. Los bugs se reprodujeron; los scripts (`s*.py`) están en `evidencias/solido_2026-10-24/`, fuera de git. Lo que ya estaba cargado (SC12, SC3, P-25d, P-25f, P-25g2, P-25i, P-25j) no se repite.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|

## Ensamblar (auditoría contra Fusion, 2026-10-25)

Cada fila salió de comparar ENSAMBLAR (uniones, componentes, grupo rígido, vínculos, estudio de movimiento) con los artículos de la ayuda de Fusion (carpeta `fusion-assemble`), de probar unas 60 llamadas por API (`evidencias/ensamble_2026-10-25/a*.py`) y de usar la ventana real como una persona (`scripts/prueba_ui/ensamblar.py`, 224 comprobaciones). Lo que ya estaba cargado (P-25e, P-25e2, SC6, SC7, SC8, SC15, H-4, H-5, H-19, F8, P-6d) no se repite.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
## Detalle de lo abierto

Ficha original de cada bug abierto o parcial (del PROJECT_LOG al 2026-10-20); se borra junto con su fila. La tabla
de arriba manda sobre este texto.

### B-184 · Dividir un cuerpo importado de STEP deja una mitad con volumen negativo y el paso sale ok

- **Qué:** 0.2.0 en vivo. `Configuración 1.step` importado, Mover1 con rx = 90, Apoyar1 y Apoyar2, Boceto1 en una cara y Dividir1 de `op1.c2` con el plano YZ y `extender=true`.
- **Esperado:** dos mitades con volumen positivo que sumen el cuerpo original, o un error claro.
- **Obtenido:** paso `ok`. Cuerpo7 (`op1.c2`): −46.885 mm³ y −33.256 mm²; Cuerpo3 (`op26.c1`): 65.205 mm³. En la ventana una mitad se ve como cáscara. Los dos tienen la misma caja salvo el lado.
- **Cómo reproducir:** falta probarlo con ese STEP en un proceso aparte; el documento está sin guardar.
- **Causa probable:** sin confirmar. La cara del corte o la orientación del sólido queda invertida en una de las mitades.
- **Prueba propuesta:** cada cuerpo que sale de Dividir tiene volumen positivo y la suma da el original.
- **Evidencia:** documento vivo «Configuración 1» del 2026-11-02. `check_geometry` sobre él trabó la ventana más de 5 min.

### B-177 · El sentido de una unión con origen en arista circular se invierte si el padre gira

- **Qué:** `create_as_built_joint` con `origin` en una arista circular de `A2_eje_principal`, `joint_type="revolute"`, `rotation_axis="Z"`, y `drive_joint` con `J_A1` a 50°.
- **Esperado:** el giro relativo no depende de la rotación del padre.
- **Obtenido:** avance de −207,9 mm en vez de −56,9. Con origen en cara plana da −56,9 a 60°.
- **Esquive:** origen en una cara plana centrada en el eje.
- **Prueba propuesta:** mismo avance con el padre a 0°, 50° y 90°.
- **Evidencia:** `D:\DISEÑOS BLENDER\01_EN_PROCESO\brazo-robotico\REPORTE_OMNICAD_brazo-robotico.md`, sección de uniones, y `herramientas\paso_06b_juntas.py`.

### B-178 · Lo creado después de una unión no la sigue al accionarla

- **Qué:** unión, componente hijo nuevo y `drive_joint`; también `create_hole` e `insert_fastener` con puntos absolutos sobre cuerpos anteriores a la unión.
- **Esperado:** el hijo acompaña y el recálculo anda.
- **Obtenido:** el hijo no sigue la unión, los agujeros salen corridos y el recálculo da REFERENCE_LOST (Fijación2 y 3 de `06_TORNILLERIA_A5`).
- **Esquive:** las uniones al final del timeline con `move_feature`.
- **Prueba propuesta:** unión, hijo nuevo y `drive_joint`: el hijo acompaña.
- **Evidencia:** `D:\DISEÑOS BLENDER\01_EN_PROCESO\brazo-robotico\REPORTE_OMNICAD_brazo-robotico.md`.

### B-179 · La suma de filas de la lista de materiales no da la masa total

- **Qué:** `get_bill_of_materials` sobre `brazo_robotico.omnicad` (426 pasos, 257 cuerpos).
- **Esperado:** la suma de `rows[].mass_g` da `total_mass_g`, salvo redondeo.
- **Obtenido:** cerca de 77,41 kg contra 79,54 kg.
- **Prueba propuesta:** suma de filas igual al total.
- **Evidencia:** `D:\DISEÑOS BLENDER\01_EN_PROCESO\brazo-robotico\REPORTE_OMNICAD_brazo-robotico.md`.

### B-172 · Pedir propiedades de un cuerpo recién solevado cerró la app

- **Qué:** 0.2.0 en vivo, `execute_code`: 3 × `sketch_from_spec` (spline cerrado con `fit_points`, planos Y = 41, XZ e Y = −41), `loft` de los tres con `operation="new_body"` y `get_physical_properties` de ese cuerpo.
- **Esperado:** el volumen, o un error claro.
- **Obtenido:** la app se cerró el 2026-11-02 a las 16:10:37: `pythonw.exe`, TKernel 8.0.1.0, 0xc0000005. Pila: `geometria.py:1034 _por_malla`, `_propiedades`, `volumen`, `_info_cuerpo`, `get_physical_properties`.
- **Cómo reproducir:** pasó una vez. Abrir el autoguardado de un minuto antes en otro proceso da 1.873.616 mm³ sin caerse: no es determinista desde ese estado.
- **Causa probable:** sin confirmar. `_por_malla` llama a OpenCascade sobre el sólido plegado de B-173 sin validarlo ni aislarlo; puede compartir causa con B-170.
- **Esquive:** guardar antes de cada paso.
- **Prueba propuesta:** propiedades de un sólido autointersectado dan resultado o error, y una violación de acceso ahí no cierra la app (`nucleo/aislado.py`).
- **Evidencia:** `D:\DISEÑOS BLENDER\01_EN_PROCESO\brazo-robotico\bugs_omnicad\` (autoguardado, traza y script). Reportado por la sesión del brazo robótico. Reporte completo: `D:\DISEÑOS BLENDER\01_EN_PROCESO\brazo-robotico\REPORTE_OMNICAD_brazo-robotico.md`. El `shell` del script nunca corrió. `siluetas_mm.json` se regeneró después: el actual puede dar otra forma.

### B-173 · Solevación de 3 splines cerrados sale ok con el sólido plegado, y check_geometry da válido

- **Qué:** la misma solevación de B-172; después `check_geometry(body="A3_brazo_superior_fundicion")`.
- **Esperado:** cerca de 4 L, sin depender del orden de las secciones, o un aviso. `valid` en false si hay un problema de severidad error.
- **Obtenido:** 1.873.616 mm³, cerca del 40 %, con una cara plegada y paso `ok`. Con el orden p, m, n el volumen da negativo. `self_intersections: 1` con severidad error en [12,26; −23,33; 754,77], pero `valid`, `closed` y `all_valid` en true.
- **Causa probable:** hipótesis sin analizar: `fit_points` normaliza la cuerda y los puntos enfrentados se corren hasta 50 mm.
- **Prueba propuesta:** solevación con secciones del mismo número de puntos conserva el área o avisa; `check_geometry` da inválido si hay un error.
- **Evidencia:** la misma carpeta de B-172. Sin volver a probar acá: spline cerrado con `control_points` daría `PROFILE_NOT_CLOSED`.

### B-170 · La vista previa de Solevación cierra la app

- **Qué:** ventana real, comando `solevacion`, semilla `69704464-D-6` de la capa D (perfiles elegidos con el visor).
- **Esperado:** La previa o un error en el panel.
- **Obtenido:** Violación de acceso en `solevar`, llamada desde `_calcular_previa_ahora`: se cierra la ventana.
- **Cómo reproducir:** `cazar.py repetir "proceso||cierre_c0000005@solidos_crear.py:1321"`. No está en el corpus: necesita la ventana.
- **Entorno:** Windows, versión 0.2.0, 2026-11-02.
- **Prueba propuesta:** `tests/test_caza_regresion.py` pasa de xfail a verde al borrar esta fila.

### B-171 · Un desfase grande da autointersecciones y sale ok

- **Qué:** Las recetas `b171_desfase_aristas` y `b171_desfase_superficie`.
- **Esperado:** Un cuerpo sin autointersecciones, o un aviso.
- **Obtenido:** Paso ok, con 1 y con 6 autointersecciones.
- **Cómo reproducir:** `clon/tests/corpus_caza/b171_*.json`.
- **Entorno:** Windows, versión 0.2.0, 2026-11-02.
- **Prueba propuesta:** `tests/test_caza_regresion.py` pasa de xfail a verde al borrar esta fila.

### B-168 · Un tubo por aristas con esquinas da autointersecciones y sale ok

- **Qué:** cuerpo con caras extruidas y `create_pipe(edges=["Cuerpo2/E9", "Cuerpo2/E4", "Cuerpo2/E8"])`.
- **Esperado:** un tubo sin autointersecciones, o un aviso.
- **Obtenido:** paso ok, cuerpo nuevo con 1 autointersección.
- **Cómo reproducir:** `clon/tests/corpus_caza/b168_tubo_esquinas.json`; `cazar.py repetir <firma>`.
- **Entorno:** Windows, versión 0.2.0, API sin ventana, 2026-11-02.
- **Prueba propuesta:** `tests/test_caza_regresion.py` pasa de xfail a verde al borrar esta fila.

### B-159 · Un empalme chico sobre un vaciado cierra la app

- **Qué:** `create_box(60, 50, 40)`, `shell(body="Cuerpo1", thickness=1, faces="<Z")`, `find_edges`, `fillet(body="op1.c1", edges=["Cuerpo1/E10"], radius=1)`.
- **Esperado:** El empalme, o un error.
- **Obtenido:** Violación de acceso en `mf.Build()`: se cae el proceso entero, sin error ni autoguardado.
- **Cómo reproducir:** caso del cazador en `clon/tests/corpus_caza/`; `cazar.py repetir <firma>` lo repite. Firma en `scripts/caza/conocidos.json`.
- **Entorno:** Windows, versión 0.2.0, API sin ventana, 2026-11-02.
- **Prueba propuesta:** `tests/test_caza_regresion.py` pasa de xfail a verde al borrar esta fila.

### B-158 · Labio sobre una esfera cierra la app

- **Qué:** `create_sphere(radius=10)`, `find_edges`, `create_lip_groove(edges=["Cuerpo1/E3"])`.
- **Esperado:** Un error claro: esa arista no sirve para un labio.
- **Obtenido:** Violación de acceso en `_punto_en`: se cae el proceso.
- **Cómo reproducir:** caso del cazador en `clon/tests/corpus_caza/`; `cazar.py repetir <firma>` lo repite. Firma en `scripts/caza/conocidos.json`.
- **Entorno:** Windows, versión 0.2.0, API sin ventana, 2026-11-02.
- **Prueba propuesta:** `tests/test_caza_regresion.py` pasa de xfail a verde al borrar esta fila.

### B-160 · Un STEP con bytes alterados cierra la app

- **Qué:** `open_document` con `tests/corpus_caza/b160_step_roto.step`, un STEP de la app con bytes alterados.
- **Esperado:** Error «No se pudo leer el archivo STEP».
- **Obtenido:** Violación de acceso dentro de `ReadFile`: se cae el proceso.
- **Cómo reproducir:** caso del cazador en `clon/tests/corpus_caza/`; `cazar.py repetir <firma>` lo repite. Firma en `scripts/caza/conocidos.json`.
- **Entorno:** Windows, versión 0.2.0, API sin ventana, 2026-11-02.
- **Prueba propuesta:** `tests/test_caza_regresion.py` pasa de xfail a verde al borrar esta fila.

### B-162 · Un chaflán mayor que el radio deja el sólido abierto y el paso sale ok

- **Qué:** `create_cylinder(radius=10, height=30)`, `chamfer(edges=["Cuerpo1/E1"], distance=15)`.
- **Esperado:** Un error, o una forma cerrada.
- **Obtenido:** Paso ok y `check_geometry` no estanco.
- **Cómo reproducir:** caso del cazador en `clon/tests/corpus_caza/`; `cazar.py repetir <firma>` lo repite. Firma en `scripts/caza/conocidos.json`.
- **Entorno:** Windows, versión 0.2.0, API sin ventana, 2026-11-02.
- **Prueba propuesta:** `tests/test_caza_regresion.py` pasa de xfail a verde al borrar esta fila.

### B-163 · Extender superficie sobre un sólido lo deja abierto

- **Qué:** `create_box(80, 60, 40)`, `extend_surface(edges=["Cuerpo1/E4"], extension_type="tangent")`.
- **Esperado:** Un error: un sólido no se extiende, o el cuerpo pasa a superficie.
- **Obtenido:** Paso ok, tipo sólido y no estanco.
- **Cómo reproducir:** caso del cazador en `clon/tests/corpus_caza/`; `cazar.py repetir <firma>` lo repite. Firma en `scripts/caza/conocidos.json`.
- **Entorno:** Windows, versión 0.2.0, API sin ventana, 2026-11-02.
- **Prueba propuesta:** `tests/test_caza_regresion.py` pasa de xfail a verde al borrar esta fila.

### B-164 · Extruir varias caras a la vez deja un cuerpo roto

- **Qué:** Caja hueca, `extrude(faces=["Cuerpo1/F2"])` y `extrude(faces=["Cuerpo1/F2", "Cuerpo1/F3"])`.
- **Esperado:** Un cuerpo válido por cara, o un error.
- **Obtenido:** Cuerpo4 con volumen 0; en otra pieza, 4 autointersecciones.
- **Cómo reproducir:** caso del cazador en `clon/tests/corpus_caza/`; `cazar.py repetir <firma>` lo repite. Firma en `scripts/caza/conocidos.json`.
- **Entorno:** Windows, versión 0.2.0, API sin ventana, 2026-11-02.
- **Prueba propuesta:** `tests/test_caza_regresion.py` pasa de xfail a verde al borrar esta fila.

### B-165 · Un agujero tangente a dos paredes deja aristas no manifold y sale ok

- **Qué:** `create_box(80, 60, 40)`, `create_hole(diameter=60, face="Cuerpo1/F5", depth=60)`.
- **Esperado:** Sin aristas compartidas por más de dos caras, o un aviso.
- **Obtenido:** Paso ok y una arista no manifold.
- **Cómo reproducir:** caso del cazador en `clon/tests/corpus_caza/`; `cazar.py repetir <firma>` lo repite. Firma en `scripts/caza/conocidos.json`.
- **Entorno:** Windows, versión 0.2.0, API sin ventana, 2026-11-02.
- **Prueba propuesta:** `tests/test_caza_regresion.py` pasa de xfail a verde al borrar esta fila.

### B-166 · Desfasar caras de una superficie la deja inválida y sale ok

- **Qué:** Caja, vaciado de 2 mm, `offset_surface(faces=["Cuerpo1/F7"])`, `offset_faces(faces=["Cuerpo2/F1"], distance=40)`.
- **Esperado:** Una superficie válida o un error.
- **Obtenido:** Paso ok y `check_geometry` inválido.
- **Cómo reproducir:** caso del cazador en `clon/tests/corpus_caza/`; `cazar.py repetir <firma>` lo repite. Firma en `scripts/caza/conocidos.json`.
- **Entorno:** Windows, versión 0.2.0, API sin ventana, 2026-11-02.
- **Prueba propuesta:** `tests/test_caza_regresion.py` pasa de xfail a verde al borrar esta fila.

### B-167 · El patrón geométrico sobre chapa da autointersecciones y sale ok

- **Qué:** Pestaña de chapa de 80 × 50 y `create_geometric_pattern(faces=["Cuerpo1/F5", "Cuerpo1/F6"])`.
- **Esperado:** Una forma sin autointersecciones.
- **Obtenido:** Paso ok, válido y estanco, con 2 autointersecciones.
- **Cómo reproducir:** caso del cazador en `clon/tests/corpus_caza/`; `cazar.py repetir <firma>` lo repite. Firma en `scripts/caza/conocidos.json`.
- **Entorno:** Windows, versión 0.2.0, API sin ventana, 2026-11-02.
- **Prueba propuesta:** `tests/test_caza_regresion.py` pasa de xfail a verde al borrar esta fila.

### B-157 · Un empalme o chaflán más grande que la pared de un vaciado deja aletas y el paso sale ok

- **Qué:** versión 0.2.0, en vivo. Boceto en XZ, trapecio de 82,74 × 71,14 mm; Extrusión 43,66 mm con conicidad −31,5°; Vaciado interior 1,91 mm quitando la cara de y = −43,66; Empalme 16,05 mm en la arista de (0, 0) y Chaflán 20,28 mm en la de (−82,74, 0), las dos en la cara de y = 0.
- **Esperado:** quitar la esquina también abre o corta la cavidad, sin caras sueltas, o un error claro si no se puede. Falta comparar con Fusion.
- **Obtenido:** los pasos dan `ok`, pero las esquinas interiores de la cavidad quedan afuera como dos aletas. `check_geometry`: válido, estanco y 16 autointersecciones. La caja da 75,92 mm de ancho, y esa medida la marcan las aletas.
- **Cómo reproducir:** los pasos de arriba en un documento nuevo; mirar la vista superior en alambre o correr `check_geometry`.
- **Causa probable:** sin leer en detalle. `BRepFilletAPI_MakeFillet` solo mira las caras vecinas de la arista y no ve la cavidad; el paso acepta su salida porque `es_valida` no busca autointersecciones.
- **También:** el cazador la encontró solo (2026-11-02): desde 5 veces la pared aparecen autointersecciones, y con un chaflán de 48,4 mm sobre una pared de 2 el volumen da negativo (−16 579 mm³). Casos en `clon/tests/corpus_caza/b157_*.json`.
- **Esquive:** empalme y chaflán antes del vaciado, o un tamaño menor que la pared.
- **Prueba propuesta:** caja vaciada con empalme mayor que la pared: el resultado sin autointersecciones, o un error claro.
- **Evidencia:** los tres renders y la captura de esta revisión quedaron en la sesión; `check_geometry` del 2026-11-02 sobre `op159.c1`.

### B-154 · Un paso viejo con un pedazo de letra partida, elegido a mano, ya no calcula

- **Qué:** documento guardado antes de B-134, con una curva que cruza una letra y una Extrusión que eligió a mano un pedazo de esa letra. Referencia de firma `{círculo, texto}` y centro (-8,8; 67,3).
- **Esperado:** que el paso encuentre la letra entera.
- **Obtenido:** «Un perfil seleccionado ya no existe en el boceto (cambió su contorno)». La referencia al disco cortado sí encuentra el disco, con aviso.
- **Reproducir:** `pf.detectar(boceto.geometria(), plano)` da los pedazos viejos (158,96 y 1,29 mm²); `pf.buscar_por_firma_tolerante(br.perfiles, firma, centro)` devuelve `(None, None)`.
- **Causa probable:** la O y su hueco tienen el mismo centro y la misma firma, y la referencia vieja no guarda con qué desempatar.
- **Esquive:** volver a elegir el texto en ese paso.
- **Prueba propuesta:** una referencia vieja a un pedazo de letra encuentra la letra entera.

### B-149 · Radio mínimo sin radio mínimo pinta de rojo las paredes enteras de un vaciado

- **Qué:** `analyze_geometry(type="min_radius", radius=25)` o un análisis guardado antes del 2026-11-01 sobre una caja vaciada.
- **Esperado:** rojo solo junto a los rincones.
- **Obtenido:** las paredes y el piso interiores enteros en rojo: una cara plana con sus cuatro esquinas sobre aristas cóncavas queda marcada completa.
- **Esquive:** dar `min_radius`, o reabrir el análisis desde el panel y aceptar.
- **Prueba propuesta:** extender `test_radio_minimo_degrade_entre_dos_radios` al modo viejo si se decide cambiarlo.
- **Evidencia:** `evidencias/inspeccionar_2026-11-01/despues/capturas/inspeccionar_radio_minimo_cerca.png`.

### B-144 · Cortar con una esfera casi tangente a una pared puede quitar de menos sin avisar

**Gravedad:** media (hace falta un contacto casi tangente; el cuerpo sale válido y estanco). **Entorno:** OmniCAD, Windows, API sin ventana. **Estado:** reproducido; apareció comparando cortar junto y de a una en 300 casos al azar con un árbitro de puntos.

**Qué hice:** `geo.booleano(hueca, geo.esfera(4, (18.537165, 20.0001, 10.0001)), "cortar")`, con `hueca` = caja 60×40×20 en (-30, -20, 0) menos caja 54×34×20 en (-27, -17, 3).

**Esperado:** quitar 122,5 mm³ (media esfera menos el casquete que pasa al hueco). **Obtenido:** quita 103,79 mm³, válido y sin aviso; el común da 121,97.

**Causa probable (leída):** el primer reintento creíble gana. `_comun_desmentido` deja pasar lo que difiere menos de 1/4 de la pieza chica, porque con 16 muestras no se puede afirmar menos. Reordenar `_REINTENTOS_BOOLEANA` podría resolverlo, pero cambia recetas que hoy dan bien. También: en ese mismo banco, 1 caso de 300 (el 60) da mal cortando de a una, y 3 terminan en error claro. **Esquive:** mover la esfera una milésima. **Prueba propuesta:** el caso de arriba, esperando 122,5 mm³ con tolerancia 1 mm³.

### B-119 · Proyectar un cuerpo curvo visto de costado no da su silueta

**Gravedad:** media. **Entorno:** OmniCAD, Windows, núcleo sin ventana. **Estado:** reproducido.

**Qué hice:** `proyectar_forma(g.cilindro(14, 47), g.Plano("XZ"))` y la esfera `g.esfera(10)` sobre XY y XZ, y `detectar` sobre el boceto.

**Esperado:** Fusion, filtro Bodies: «projects closed profiles that are ready for constraints and downstream features» (`project-geometry-onto-a-sketch-plane`). ⚠ Fusion real no conectó: la silueta exacta no se comparó en la app. **Obtenido:** cilindro: 3 líneas abiertas, 0 perfiles. Esfera: 1 línea (XY) o 1 arco (XZ), 0 perfiles. La caja y el cilindro de frente andan bien.

**Causa:** `proyectar_forma` recorre solo las aristas reales de la forma; la silueta de una cara curva no es una arista. **Esquive:** proyectar sobre un plano donde el cuerpo tenga aristas reales, o dibujar el perfil. **Prueba propuesta:** cilindro sobre XZ da un rectángulo con un perfil de 28 × 47; medir el costo con una rosca modelada antes de vincularlo al timeline.

### B-48 · Crash nativo OCCT (0xc0000005) al recalcular parámetros a 148 pasos

**Mitigado 2026-10-20** (`agente/b48`): no se reprodujo en 18 min; la caída de un hijo aislado vuelve como `TareaAislada`. Sigue Parcial. **Crash nativo durante la tortura de parámetros** (±30 % a 148 pasos): APPCRASH de `pythonw.exe`, excepción 0xc0000005 en `TKernel-….dll` (OCCT 8.0.1) offset 0x78bed, 09:11:23; el puente murió a mitad de llamada (`BRIDGE_ERROR WinError 10054`). El autoguardado (receta sin caché, 18 s antes) permitió recuperar todo. Evento completo en `crash2_evento_completo.txt`.

kernel OCCT vía cadquery_ocp; recálculo

Reproducido (firma de Windows): no se puede curar desde la app; queda la protección por autoguardado

Crítico

**2026-10-27 (agente nocturno)**: se armó una tortura sintética de 141 pasos y 46 cuerpos (booleanas, empalmes, chaflanes, patrones y simetrías; `evidencias/b48_2026-10-27/`) y se corrieron 300 rondas de 4 cambios ±30 % cada una en procesos aparte con faulthandler: 0 caídas y 0 pasos con error; 60 rondas más con `OMNICAD_SIN_PARALELO=1` tampoco cayeron (9,98 s/ronda contra 9,23 s con paralelismo: apagarlo cuesta ~8 %). El motor RL-1 real, con el estado mixto del crash original, tampoco cayó en 3 rondas (abrir 78-85 s; r_camara/largo_camara ~105-109 s por recálculo; d_eje ~21 s). El paralelismo no es la causa demostrable; queda el interruptor `OMNICAD_SIN_PARALELO` para diagnosticar. Se extendió el prevuelo aislado a `reemplazar`, `suprimir` y `eliminar` pasos y a `abrir` archivos de 60 pasos o más (el RL-1: 155,6 s con prevuelo contra ~80 s sin él); si el hijo cae, el documento no se toca y sale un `ErrorDocumento`/`ErrorProyecto` claro. Segunda ronda (2026-10-27): el padre adopta el cálculo del hijo (`timeline/calculo_aislado.py`: grafo + BREP, sin pickle) en vez de repetirlo con el kernel; deshacer, rehacer, mover paso, mover marcador y configuraciones también calculan en el hijo; la ventana avisa «Calculando…» pasado 1 s. Sigue Parcial porque la caída nativa no se reprodujo ni curó.

**2026-11-01 (tortura de operaciones, `main` en 2d8212e):** otro documento sintético propio, de 146 pasos y 48 cuerpos (24 bloques de caja, empalme |Z, agujero pasante, saliente cilíndrico unido, saliente en caja y espejo, más un corte), armado en 307,6 s sin errores. 47 rondas de 8 cambios de parámetro (L ×1,3, H ×0,7, r ×1,3, W ×0,7 y vuelta a los valores base): 376 cambios, 0 caídas, 0 errores, `pasos_con_error` 0, volumen final igual al inicial y RSS pico 524 MB; con `faulthandler` encendido, `b48_fault.txt` quedó vacío. Cada cambio tardó ~3,4 s: el hijo aislado se encarga solo (≥ 60 pasos). Tampoco se reprodujo.
