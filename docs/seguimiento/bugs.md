# Bugs

Algo que falla, da un resultado malo o un mensaje engañoso. Método y columnas: [README](README.md).

Solo lo que falta resolver: al resolverse, la fila se borra. Verificado contra el código el 2026-10-23 (Superficie y Sólido, también en la ventana real: 2026-10-24; revisión de B-39 y regresiones de B-48: 2026-10-27). Tortura de operaciones y booleanas: 2026-11-01. Total 22: Abierto 16 · Parcial 5 · Bloqueado 1 (recontado 2026-11-06 tras resolver B-213, B-195 y B-206).

## Abiertos y parciales

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| B-209 | Barrido sólido con escala «Estirar» hace «Escalar» sin avisar | Abierto | Media | `sweep rail_scale="stretch"` usa la misma ley uniforme que `scale`; debería estirar en una sola dirección. La auditoría previa a B-208 midió 3364,59 mm³ en ambos; falta actualizar esa medida tras B-208 (sonda sin turno). La superficie sí estira (400 mm² exactos). La ventana del sólido ni ofrece Estirar. | nucleo/solidos_crear.py:877 | 2026-11-05 |
| B-210 | Revolución «Dos lados» con un ángulo negativo da otra forma en sólido que en superficie | Abierto | Baja | Lado 1 = 90°, lado 2 = −45°: el sólido toma el signo y el lado 2 vuelve sobre el lado 1 (1570,80 mm³, como sin lado 2, sin aviso); la superficie toma el valor absoluto (235,62 mm², igual que +45°). Falta una sola regla para los dos. | timeline/operaciones.py:1305 (`OpRevolucion.ejecutar`) y nucleo/superficies.py:475 | 2026-11-05 |
| B-211 | Barrido: la Distancia mayor que 1 se acepta y se recorta a 1 sin avisar | Abierto | Baja | En la ventana «1,5» deja la vista previa en verde y `edit_feature` con `distancia="2"` sale ok: el cuerpo es el de 1 (628,32 mm³). La API solo rechaza números sueltos (`path_distance=1.5`). Fusion: Range 0.00-1.00. | nucleo/solidos_crear.py:256 | 2026-11-05 |
| B-214 | Nervio con dos curvas sueltas falla con un mensaje de «ruta» | Abierto | Baja | La ventana deja elegir varias curvas, pero dos líneas sueltas dan «La ruta debe ser una sola cadena continua de aristas». Fusion hace un nervio por curva en un solo paso (la ayuda muestra cuatro). La Red sí las acepta. | nucleo/solidos_crear.py:1439 (`nervio`: un solo `_alambre`) | 2026-11-05 |
| B-216 | Red › «Cambiar dirección» no invierte el sentido de la red | Abierto | Baja | Caja hueca con el boceto adentro: sin invertir y con invertir dan lo mismo (18280 mm³; invertida debería ir a la otra pared y dar 19000). Con la boca abierta del otro lado, Fusion avisaría; OmniCAD crea la misma red. Solo cambia el lado de «Un lado». | timeline/ops_solido.py:286 (`OpRed`: niega la normal, pero `red()` elige el lado más cercano de los dos) | 2026-11-05 |
| B-217 | Repujado con «Cadena tangente» repuja también en los costados | Abierto | Media | Placa con las aristas de arriba empalmadas, cuadro 10×10 encima, relieve 1 mm con cadena tangente: +437,12 mm³ en vez de +100, caja 1 mm más ancha a cada lado. La cadena suma los costados (tangentes a los empalmes) y el cuadro se «adapta» y se repuja en cada uno. Se ve en la captura `repujado_cadena.png`. | nucleo/solidos_crear.py:1548 (cadena) y 1608 (`_perfiles_en_zona` con `adaptar`) | 2026-11-05 |
| B-196 | Barrer y el sector del labio pierden la autointersección sin avisar | Abierto | Media | `barrer` (dos sitios) y `_sector_labio` no pasan por el aviso de autointersección que ya tienen Tubo y Patrón geométrico (B-167, B-168). Hallado en la revisión del 2026-11-05. | nucleo/solidos_crear.py | 2026-11-05 |
| B-189 | OmniKernel no arranca: un argumento por defecto usa un enum de OCC sin inicializar | Abierto | Baja | `_trozos(..., tipo=TopAbs_SOLID)` evalúa el enum al importar `solidos_crear`, pero `_iniciar_opencascade` no corre al elegir OmniKernel. Reproducido en `test_motor` y los 68 casos de `test_paridad_motor`: todos fallan antes de modelar con `NameError: name 'TopAbs_SOLID' is not defined`. También está en HEAD (`solidos_crear.py:3868`), independiente del arreglo de perfiles. Integrar la corrección en ese módulo y repetir las pruebas de ambos motores. | clon/tests/test_motor.py::test_prueba_humo_arranca_con_omnikernel_y_ocp_bloqueado; clon/omnicad/nucleo/solidos_crear.py (`_trozos`) | 2026-11-04 |
| B-188 | Investigar la cara sin triangulación del proyecto REMOVEDOR | Parcial | Media | Corregido el supuesto que hacía `argmax` sobre una malla vacía, con recuperación por B-rep y errores de geometría claros; pruebas sin malla, visor, terminar, extruir, recalcular y persistencia. Falta el `.omnicad` o receta exacta con el boceto/SVG y los movimientos op22/op23/op55 para explicar por qué esa cara concreta quedó sin malla. El STEP REMOVEDOR DE TRAGO disponible se importa y proyecta sin reproducir el fallo; no se atribuye a archivo dañado ni a cara inválida. | clon/tests/test_perfiles_interior.py::test_sin_huecos_preserva_el_svg_valido_sin_malla; clon/omnicad/nucleo/geometria.py (`punto_dentro`) | 2026-11-04 |
| B-184 | Dividir un cuerpo importado de STEP deja una mitad con volumen negativo y el paso sale ok | Abierto | Alta | Cuerpo7 quedó en −46.885 mm³ y −33.256 mm², y Cuerpo3 en 65.205 mm³. `check_geometry` en vivo sobre ese documento trabó la ventana más de 5 min. Falta reproducirlo en proceso aparte. | omnicad/nucleo/solidos_modificar.py:1564 | 2026-11-02 |
| B-177 | El sentido de una unión con origen en arista circular se invierte si el padre gira | Abierto | Alta | Con el padre a más de unos 45° el mismo valor mueve al revés: −207,9 mm en vez de −56,9. Con origen en cara plana no pasa. | omnicad/api/herramientas_ensamble.py:725 | 2026-11-02 |
| B-178 | Lo creado después de una unión no la sigue al accionarla | Abierto | Alta | Agujeros y fijaciones con puntos absolutos salen corridos y el recálculo da REFERENCE_LOST. Esquive: uniones al final del timeline. | omnicad/api/herramientas_ensamble.py:650 | 2026-11-02 |
| B-172 | Pedir propiedades de un cuerpo recién solevado cerró la app | Abierto | Alta | Violación de acceso en TKernel dentro de `_por_malla`, una vez en vivo; no se repite abriendo el autoguardado. Falta aislar esa medición o validar el sólido antes. | omnicad/nucleo/geometria.py:1034 | 2026-11-02 |
| B-173 | Solevación de 3 splines cerrados sale ok con el sólido plegado, y check_geometry da válido | Abierto | Alta | Da 40 % del volumen esperado y el orden de las secciones cambia el resultado sin avisar. `valid` y `all_valid` siguen en true con un problema de severidad error. | omnicad/api/herramientas_revision.py:74 | 2026-11-02 |
| B-170 | La vista previa de Solevación cierra la app | Abierto | Alta | Con perfiles elegidos, `BRepOffsetAPI_MakePipeShell` da una violación de acceso dentro de la previa, en `solevar`: se cae la ventana entera. La previa tiene que correr aislada o validar antes. | nucleo/solidos_crear.py:1321 | 2026-11-02 |
| B-159 | Un empalme chico sobre un vaciado cierra la app | Abierto | Alta | Caja 60 × 50 × 40, vaciado de 1 mm quitando la base y empalme de 1 mm en E10: `BRepFilletAPI_MakeFillet.Build` da una violación de acceso y se cae todo el programa. Hay que ver por qué no lo frena el `try`: un cierre nativo no es una excepción de Python; correrlo aislado o validar antes. | nucleo/solidos_modificar.py:548 | 2026-11-02 |
| B-160 | Un STEP con bytes alterados cierra la app | Abierto | Alta | `STEPCAFControl_Reader.ReadFile` da una violación de acceso con el archivo de `tests/corpus_caza/`. Abrir STEP de otros tiene que correr en el proceso aislado (`nucleo/aislado.py`), o la app cae con un archivo ajeno. | nucleo/intercambio.py:225 | 2026-11-02 |
| B-167 | El patrón geométrico sobre chapa da autointersecciones y sale ok | Parcial | Media | Ahora avisa la autointersección (tests/test_b167_b168_autointersecciones.py, 2026-11-04). Falta la lentitud: con 2 mm sobre una cara grande tarda más de 40 s y no se puede cortar. | api/herramientas_solido_extra.py | 2026-11-02 |
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

### B-209 · Barrido sólido con «Estirar» hace «Escalar»

- **Qué:** cuadrado 4×4 centrado en YZ, ruta X de 0 a 50 y carril en XZ de (0, 2) a (50, 6): `sweep rail_scale="stretch"` y `rail_scale="scale"`.
- **Esperado (Fusion):** «Stretch: use path - guide rail distance to scale profile in X» (ayuda `Sweep reference`): el perfil crece solo hacia el carril, 4·(4+12)/2·50 = 1600 mm³ (la superficie da sus 400 mm² exactos).
- **Obtenido en la auditoría original, antes de B-208:** 3364,59 mm³ en los dos modos, sin aviso. El arreglo de B-208 corrige la deformación de las secciones, no la equivalencia incorrecta entre Estirar y Escalar; falta volver a medir Estirar (la sonda posterior esperó turno y agotó el plazo sin ejecutar). El docstring de `barrer` dice que «estirar» no existe en OCC y se hace como «escalar» (`nucleo/solidos_crear.py:877`), pero `superficies._estirar` (`nucleo/superficies.py:617`) ya lo resuelve.
- **Reproducir:** `evidencias/ui_2026-11-05/sonda_carril.py`.
- **Esquive:** ninguno en sólido; superficie y después Engrosar o Coser.
- **Prueba propuesta:** estirar ≠ escalar y da 1600 mm³ con el carril de 2 a 6; la ventana ofrece Estirar.

### B-210 · Revolución «Dos lados» con ángulo negativo: sólido y superficie distintos

- **Qué:** rectángulo x 10..20, y 0..10 en XY, eje Y; `revolve direction=two_sides angle=90 angle2=-45` y `create_surface_revolve` con la línea x=10 y los mismos ángulos. En la ventana: Dos lados, teclear «90 deg» y «-45 deg», Enter.
- **Esperado:** el mismo criterio en los dos (Fusion no dice qué hace con un ángulo negativo en Dos lados: ⚠ sin abrir Fusion).
- **Obtenido:** sólido 2356,19 mm³ (el lado 2 se pierde en la unión, sin aviso); superficie 235,62 mm² (toma −45 como +45, `abs` en `nucleo/superficies.py:475`).
- **Reproducir:** `evidencias/ui_2026-11-05/sondas_rbs.py rev_dos_lados_90_menos45 srev_dos_lados_neg`.
- **Prueba propuesta:** lado 2 negativo da lo mismo (o el mismo error) en sólido y en superficie.

### B-211 · Barrido: Distancia mayor que 1 se recorta sin avisar

- **Qué:** círculo r 2 en YZ y ruta de 50 en X; `sweep` y después `edit_feature feature=op3 params={"distancia": "2"}`; en la ventana, teclear «1,5» en Distancia.
- **Esperado (Fusion):** «Value is measured in percentage of the total distance. Range: 0.00-1.00» (ayuda `Sweep reference`): un error claro, como «0».
- **Obtenido:** `ok`, el cuerpo de la ruta entera (628,32 mm³) y la previa en verde; `_recortar_alambre` hace `min(fraccion, 1.0)` (`nucleo/solidos_crear.py:256`). La API rechaza solo `path_distance` numérico (`api/herramientas_solido.py:452`).
- **Prueba propuesta:** distancia 1,5 da error en la ventana, en `edit_feature` y en la API.

### B-214 · Nervio con varias curvas sueltas

- **Qué:** la escuadra (piso x 0..40, y −30..30, z 0..5 y pared x 0..5, z 0..50) y, en el mismo boceto, dos líneas sueltas: (35, 5) → (5, 45) y (30, 5) → (5, 38,33); `create_rib thickness=2`. En la ventana: elegir las dos curvas con el visor.
- **Esperado (Fusion):** un nervio por curva en un paso (imágenes de `Create a rib`: cuatro curvas, cuatro nervios).
- **Obtenido:** «La ruta debe ser una sola cadena continua de aristas»: el mensaje habla de una ruta que el nervio no tiene. Dos líneas encadenadas sí andan (26700 mm³).
- **Reproducir:** `sondas_nrr.py nervio_dos_curvas_sueltas`; pieza `nervio_red_repujado` («Nervio con dos curvas sueltas»).
- **Causa probable (leída):** `nervio` arma un solo alambre (`_alambre`, `nucleo/solidos_crear.py:1439`); `red` ya recorre `_cadenas`.
- **Prueba propuesta:** dos curvas sueltas = la unión de los dos nervios, en un paso.

### B-216 · Red › Cambiar dirección no invierte

- **Qué:** caja 40³ vaciada 2 mm y cerrada, boceto en un plano a y = 15 con la línea z = 20, x 10..30; `create_web thickness=2` y `create_web thickness=2 reverse=true`. Con la caja abierta en y = 0 (boca hacia −Y), lo mismo. En la ventana: Red › Cambiar dirección.
- **Esperado (Fusion):** «Flip Direction: Flips the direction in which the web feature is extruded» (ayuda `Web reference`): la red va hacia la otra pared (19000 mm³) o, con la boca abierta, avisa.
- **Obtenido:** 18280 mm³ en los dos casos cerrados y 16408 en los dos abiertos: el botón no cambia nada (salvo el lado de «Un lado»).
- **Reproducir:** `sondas_nrr.py red_adentro red_abierta`; pieza `nervio_red_repujado` («Red invertida hacia la boca abierta»).
- **Causa probable (leída):** `OpRed` niega la normal (`timeline/ops_solido.py:286`), pero `red()` prueba los dos sentidos y se queda con el más cercano (`nucleo/solidos_crear.py:1477`); su parámetro `invertir` nunca se pasa.
- **Prueba propuesta:** caja cerrada con el boceto en y = 15: 18280 sin invertir y 19000 invertida.

### B-217 · Repujado con cadena tangente se repite en los costados

- **Qué:** placa 60×40×10, `fillet edges=">Z" radius=3`, cuadro 10×10 en (20..30, 15..25) sobre la cara de arriba; `create_emboss faces=">Z" depth=1 tangent_chain=true`. En la ventana: Repujado › Más opciones › Cadena tangente.
- **Esperado (Fusion):** «Tangent Chain: Check to automatically select tangentially connected geometry» (ayuda `Emboss reference`); el perfil se repuja donde cae: +100 mm³.
- **Obtenido:** +437,12 mm³ y la caja de x −1..61, y −1..41: un cuadro achicado en cada costado. Captura `evidencias/ui_2026-11-05/capturas/repujado_cadena.png`.
- **Reproducir:** `sondas_nrr.py rep_cadena_tangente` (la placa sola: `rep_cadena_tangente_base`, 23624,07); pieza `nervio_red_repujado` («Repujado con cadena tangente»).
- **Causa probable (leída):** la cadena suma los costados planos (tangentes a los empalmes, `nucleo/solidos_crear.py:1548`) y cada grupo de caras paralelas pasa por `_perfiles_en_zona` con `adaptar`, que gira y achica el perfil para que entre.
- **Prueba propuesta:** este caso da +100 y la caja no crece en x ni en y.

### B-188 · Reproducción exacta pendiente de REMOVEDOR

- **Fallo confirmado:** `_punto_adentro` suponía que `geo.teselar(cara)` siempre devolvía triángulos. Con malla vacía, `sin_huecos → _tinta_svg → _punto_adentro` daba `ValueError: attempt to get argmax of an empty sequence`. La misma regresión con la función anterior falla; con la corrección pasa.
- **Corrección comprobada:** `geometria.punto_dentro` verifica en UV el centro del mayor triángulo útil y, si falta/falla el mallado o el punto quedó fuera por el redondeo float32, valida la cara y usa `BRepClass3d_SolidExplorer.FindAPointInTheFace_s` con clasificación de pertenencia. Las caras diminutas se consultan en una copia escalada. No se reconstruyen contornos ni se convierte la malla en geometría CAD.
- **Geometría inválida:** un hueco que cruza el exterior es un caso sintético inválido, no el caso real. Se rechaza con `ErrorGeometria`; encontrar un punto que el clasificador dé por interior no basta para declarar válida esa cara.
- **Caso disponible:** STEP REMOVEDOR DE TRAGO, cuerpo Cuerpo5, 6 caras, volumen 2697,2602 mm³; importar, crear bocetos en las caras y proyectar sus aristas no reprodujo el fallo. Falta la receta del documento con su boceto/SVG y movimientos, no solo la forma final del STEP.
- **Banco reproducible:** `scripts/bench_perfiles_interior.py`, 1008 perfiles de texto y 1000 de SVG: 0 diferencias de clasificación con malla normal o vacía, 2008 puntos interiores comprobados y recetas intactas. Evidencia local: `evidencias/perfiles_interior_2026-11-04.json`.
- **Costo de la verificación adicional:** medianas de tres corridas alternadas, cachés calientes: texto 3735 → 4288 ms (+14,8 %), SVG 398 → 449 ms (+12,8 %). Con todos los mallados vacíos, recuperación en 5833/454 ms. No es una mejora de velocidad; queda evaluar el costo en el proyecto original y optimizarlo conservando la comprobación de pertenencia.
- **Para cerrar:** reproducir la cara concreta del documento original, registrar su validez y estado del mallado, y comprobar el flujo de la ventana sobre una copia del proyecto.


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

### B-159 · Un empalme chico sobre un vaciado cierra la app

- **Qué:** `create_box(60, 50, 40)`, `shell(body="Cuerpo1", thickness=1, faces="<Z")`, `find_edges`, `fillet(body="op1.c1", edges=["Cuerpo1/E10"], radius=1)`.
- **Esperado:** El empalme, o un error.
- **Obtenido:** Violación de acceso en `mf.Build()`: se cae el proceso entero, sin error ni autoguardado.
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

### B-167 · El patrón geométrico sobre chapa da autointersecciones y sale ok

- **Qué:** Pestaña de chapa de 80 × 50 y `create_geometric_pattern(faces=["Cuerpo1/F5", "Cuerpo1/F6"])`.
- **Esperado:** Una forma sin autointersecciones.
- **Obtenido:** Paso ok, válido y estanco, con 2 autointersecciones.
- **Cómo reproducir:** caso del cazador en `clon/tests/corpus_caza/`; `cazar.py repetir <firma>` lo repite. Firma en `scripts/caza/conocidos.json`.
- **Entorno:** Windows, versión 0.2.0, API sin ventana, 2026-11-02.
- **Prueba propuesta:** `tests/test_caza_regresion.py` pasa de xfail a verde al borrar esta fila.

### B-48 · Crash nativo OCCT (0xc0000005) al recalcular parámetros a 148 pasos

**Mitigado 2026-10-20** (`agente/b48`): no se reprodujo en 18 min; la caída de un hijo aislado vuelve como `TareaAislada`. Sigue Parcial. **Crash nativo durante la tortura de parámetros** (±30 % a 148 pasos): APPCRASH de `pythonw.exe`, excepción 0xc0000005 en `TKernel-….dll` (OCCT 8.0.1) offset 0x78bed, 09:11:23; el puente murió a mitad de llamada (`BRIDGE_ERROR WinError 10054`). El autoguardado (receta sin caché, 18 s antes) permitió recuperar todo. Evento completo en `crash2_evento_completo.txt`.

kernel OCCT vía cadquery_ocp; recálculo

Reproducido (firma de Windows): no se puede curar desde la app; queda la protección por autoguardado

Crítico

**2026-10-27 (agente nocturno)**: se armó una tortura sintética de 141 pasos y 46 cuerpos (booleanas, empalmes, chaflanes, patrones y simetrías; `evidencias/b48_2026-10-27/`) y se corrieron 300 rondas de 4 cambios ±30 % cada una en procesos aparte con faulthandler: 0 caídas y 0 pasos con error; 60 rondas más con `OMNICAD_SIN_PARALELO=1` tampoco cayeron (9,98 s/ronda contra 9,23 s con paralelismo: apagarlo cuesta ~8 %). El motor RL-1 real, con el estado mixto del crash original, tampoco cayó en 3 rondas (abrir 78-85 s; r_camara/largo_camara ~105-109 s por recálculo; d_eje ~21 s). El paralelismo no es la causa demostrable; queda el interruptor `OMNICAD_SIN_PARALELO` para diagnosticar. Se extendió el prevuelo aislado a `reemplazar`, `suprimir` y `eliminar` pasos y a `abrir` archivos de 60 pasos o más (el RL-1: 155,6 s con prevuelo contra ~80 s sin él); si el hijo cae, el documento no se toca y sale un `ErrorDocumento`/`ErrorProyecto` claro. Segunda ronda (2026-10-27): el padre adopta el cálculo del hijo (`timeline/calculo_aislado.py`: grafo + BREP, sin pickle) en vez de repetirlo con el kernel; deshacer, rehacer, mover paso, mover marcador y configuraciones también calculan en el hijo; la ventana avisa «Calculando…» pasado 1 s. Sigue Parcial porque la caída nativa no se reprodujo ni curó.

**2026-11-01 (tortura de operaciones, `main` en 2d8212e):** otro documento sintético propio, de 146 pasos y 48 cuerpos (24 bloques de caja, empalme |Z, agujero pasante, saliente cilíndrico unido, saliente en caja y espejo, más un corte), armado en 307,6 s sin errores. 47 rondas de 8 cambios de parámetro (L ×1,3, H ×0,7, r ×1,3, W ×0,7 y vuelta a los valores base): 376 cambios, 0 caídas, 0 errores, `pasos_con_error` 0, volumen final igual al inicial y RSS pico 524 MB; con `faulthandler` encendido, `b48_fault.txt` quedó vacío. Cada cambio tardó ~3,4 s: el hijo aislado se encarga solo (≥ 60 pasos). Tampoco se reprodujo.
