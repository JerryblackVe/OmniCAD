# Bugs

Algo que falla, da un resultado malo o un mensaje engañoso. Método y columnas: [README](README.md).

Solo lo que falta resolver: al resolverse, la fila se borra. Verificado contra el código el 2026-10-23 (Superficie y Sólido, también en la ventana real: 2026-10-24; revisión de B-39 y regresiones de B-48: 2026-10-27). Tortura de operaciones y booleanas: 2026-11-01. Total 38: Abierto 30 · Parcial 5 · Bloqueado 1 · Sin verificar 2 (recontado por fila el 2026-11-08) (2026-11-08: sumaron B-265 a B-269 del video de Extruir, 1 sin verificar; sumó B-264 del SVG de Affinity; sumaron B-257 a B-263 del juez de CONSTRUIR; recontado 2026-11-07 por fila: se cerraron B-236 y B-237; sumaron B-232 a B-235 de la fase 1 de CREAR y MODIFICAR y B-231 — desfase de spline con grados de libertad de más — de la fase E; se cerraron B-223 a B-230 de la auditoría de restricciones; antes se cerraron B-210 y B-211 de la tanda 1, B-214 y B-216 de la tanda 2 y B-209 y B-217 de la tanda 3, y sumaron B-219 — la flecha de «Distancia» del Nervio y la Red — y B-220 — Envolver del Repujado fuera de zona).

## Abiertos y parciales

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| B-265 | Extruir › al sumar un clic sobre el ala de la mariposa, la selección pasa de «10 perfiles» a «11 objetos» y desaparece la vista previa de todo | Abierto | Media | Boceto del SVG «LAS VALIENTES» con base ya extruida; Extruir con 10 letras elegidas como perfiles y vista previa bien. Un clic más (ala) cambia el campo a «11 objetos», todas las letras vuelven a planas y sale «Las curvas abiertas solo se extruyen con «Extrusión delgada»», aunque las letras son cerradas. Un clic que cae en una curva no debe convertir los perfiles ya elegidos en curvas: o suma el perfil de abajo o se ignora (mirar qué hace Fusion) | Video de Gerardo `2026-11-08 20-07-53.mp4`; cuadros en `evidencias/video_extrusion_2026-11-08/` (2:24–2:30) | 2026-11-08 |
| B-266 | Extruir › con la selección en «objetos», cambiar la distancia (flecha o campo) no actualiza la vista previa | Abierto | Media | Tras B-265, arrastrar la flecha da 16,79; 6,69; −38,34 y 27,24 mm en el campo, pero el visor sigue sin sólido de vista previa | Video de Gerardo `2026-11-08 20-07-53.mp4`; cuadros en `evidencias/video_extrusion_2026-11-08/` (2:30–3:00) | 2026-11-08 |
| B-267 | Extruir › la distancia pasa de 10 mm a 0 al arrastrar sobre el campo, y así queda para los perfiles que se suman | Sin verificar | Baja | A los 0:52 el campo «10 mm» se selecciona, aparece el cartel «Drag» y queda «0» con el error «tiene que ser de al menos 0.000001 mm». Ver si el arrastre sobre el campo cambia el valor (Fusion no lo hace) y si se puede volver al valor anterior sin reescribirlo | Video de Gerardo `2026-11-08 20-07-53.mp4`; cuadros en `evidencias/video_extrusion_2026-11-08/` (0:50–0:56) | 2026-11-08 |
| B-268 | Extruir › no se pueden elegir todos los perfiles de una vez: la caja de selección en el visor no elige ninguno | Abierto | Media | Gerardo confirmó (2026-11-08) que de 0:03 a 0:14 intentaba seleccionar todo arrastrando una caja: el campo Perfiles siguió en «Elegir en la vista» y al cerrar Extruir la caja eligió el objeto vectorial. Tuvo que hacer 17 clics de a uno. Fusion elige perfiles con caja de ventana (izquierda a derecha) y de cruce (derecha a izquierda) dentro del comando; ver también Ctrl+A | Video de Gerardo `2026-11-08 20-07-53.mp4`; cuadros en `evidencias/video_extrusion_2026-11-08/` (0:03–0:14) | 2026-11-08 |
| B-269 | Extruir › durante la vista previa el navegador lista los cuerpos que todavía no existen (Cuerpo1 … Cuerpo10) | Abierto | Baja | Mientras el panel está abierto, cada perfil sumado agrega un «CuerpoN» al navegador; al cancelar o cambiar la selección desaparecen. Fusion muestra la vista previa sin tocar el navegador | Video de Gerardo `2026-11-08 20-07-53.mp4`; cuadros en `evidencias/video_extrusion_2026-11-08/` (2:00–2:24) | 2026-11-08 |
| B-264 | SVG › al importar «LAS VALIENTES 1.svg» (Affinity Designer) en la ventana aparecen rectas largas que cruzan el dibujo uniendo el borde exterior | Abierto | Media | Capturas de Gerardo (2026-11-08): rectas de varios mm que unen, en orden alrededor del contorno, los puntos donde el archivo tiene 24 recortes casi transparentes (ver P-96). Por API (`insert_svg` sobre el mismo archivo) NO pasa: 565 curvas, la recta más larga mide 0,6 mm y 41 perfiles. Falta reproducirlo en la ventana (qué comando y opciones usó), encontrar qué une esos puntos y arreglarlo | `evidencias/svg_valientes_2026-11-08/` (`valientes.svg`, `repro.py`) | 2026-11-08 |
| B-231 | Boceto › el desfase de una spline (o elipse) totalmente restringida no queda totalmente restringido | Abierto | Media | Spline de 4 puntos fijos, `desfase(s, 3)` con su cota: `grados_de_libertad` da 48 (uno por punto de la copia) en vez de 0. Causa: `solver.py` `_desfase_normal` (~547-560) da a cada punto de la copia su parámetro `t` propio y libre, así el punto se desliza sobre la curva desfasada. En Fusion, el desfase de una curva fija con su cota queda fijo. Arreglo: atar cada `t` (p. ej. a la normal desde el punto de ajuste de la madre) sin perder la convergencia de las splines giradas | `tests/test_restricciones_escenarios.py::test_b231_desfase_de_una_spline_fija_queda_totalmente_restringido` (xfail estricto) | 2026-11-07 |
| B-238 | Test › `test_posicion_ventana::test_otro_comando_pregunta_como_fusion[Cancelar-False-True-0]` falla bajo carga | Abierto | Baja | En el cierre del 2026-11-07 (de día, `-n 2`, memoria libre hasta 291 MB y otra sesión con tests en la fila) falló en la tanda `parte_07`; corrido solo, `test_posicion_ventana.py` da 20 OK. Es un test que depende del tiempo o del foco: ver qué espera y hacerlo determinista, sin saltearlo (`evidencias/cierre_2026-11-07/parte_07.txt`). | tests/test_posicion_ventana.py | 2026-11-07 |
| B-240 | RENDERIZAR › la interfaz se ve corrupta: controles invertidos y duplicados, visor negro | Sin verificar | Media | Gerardo lo vio en una captura (2026-11-07): textos y botones invertidos verticalmente y repetidos, el área de herramientas en otro lugar, el visor casi todo negro y el ViewCube en varias posiciones. Falta reproducirlo y hallar la causa (FBO, eje Y, `devicePixelRatio`, estados de OpenGL sin restaurar). Lo toma la auditoría de RENDERIZAR (AG-3) como primer ítem. | `docs/auditoria_renderizar.md` | 2026-11-08 |
| B-254 | Test intermitente: `test_get_usage_log_informa_la_pausa_por_disco` falla en tandas grandes y pasa solo | Abierto | Baja | Falló 3 veces el 2026-11-08 dentro de `tests_afectados` (B-243, B-247, H-112) y pasa al correrlo solo. El disco C tenía 6–8 GB libres (tope 2 GB), así que no es falta de disco real: sospecha de estado compartido entre tests (`ru.activo`, `_libre` cacheado en `registro_uso/__init__.py:232`) o carpeta temporal compartida. Aislar el estado en el test o en el fixture. | `clon/tests/test_api_registro_uso_settings.py` | 2026-11-08 |
| B-250 | Rosca con clase exterior deja el Ø mayor nominal; Fusion modela el de la clase | Abierto | Media | Medido en Fusion el 2026-11-08: M20 6g Ø mayor 19,79 (OmniCAD 20), M3 6g 2,927 (3,0), 3/4-10 UNC 2A 18,839 (19,05); por eso el volumen de OmniCAD sale 0,8 % mayor. AFBMA 3A ya coincide (19,769). Falta que las clases exteriores de ISO, UNC y las demás sin tabla de Fusion modelen el Ø mayor (como B-122 hizo con las de tabla). | `evidencias/fusion_2026-11-08/` (medir_roscas.py/.txt de Fusion, omni_casos.py/.txt de OmniCAD); `nucleo/solidos_crear.py` › `_perfil_clase` | 2026-11-08 |
| B-251 | Rosca parcial sobre una cara de otro Ø ajusta solo el tramo roscado; Fusion cambia el Ø de toda la cara | Abierto | Media | Medido en Fusion el 2026-11-08: AFBMA N 04 de 10 mm desde 5 sobre Ø20 deja toda la cara en Ø 19,769 (8 caras, volumen 9062,6); OmniCAD tornea solo el tramo (Ø 20 fuera de él, volumen 9205,9). Vale para el torneado (B-247) y el relleno (B-248). | `evidencias/fusion_2026-11-08/` (medir_roscas.py/.txt de Fusion, omni_casos.py/.txt de OmniCAD); `nucleo/solidos_crear.py` › `rosca` | 2026-11-08 |
| B-221 | Patrón en trayectoria › la copia suprimida ya no se ve como silueta roja en la vista previa | Abierto | Baja | En el cierre del 2026-11-06 la pieza `patrones_ensamble_rosca` marca ✗ en «PAT-3: la copia suprimida se ve como una silueta roja»: `suprimir` queda en «1» pero `previa_vista` no devuelve una sola primitiva roja (0.88, 0.18, 0.15). El 2026-10-31 la misma pieza dio 0 ✗. Falta ver si cambió la previa o la prueba (`evidencias/ui_2026-11-06/patrones_ensamble_rosca.log`, captura `patron_ruta_inicio_porcentaje.png`). | scripts/prueba_ui/patrones_ensamble_rosca.py:151 | 2026-11-06 |
| B-222 | Test de rosca con tope de tiempo cae cuando la PC está cargada | Abierto | Baja | `test_rosca_en_varios_agujeros_iguales_reusa_el_surco` exige `tiempo < 10` s para 4 roscas M3: el 2026-11-06 falló dentro de una corrida de 4 archivos (con la línea Sol usando la PC) y pasó solo (1 passed en 19,77 s). El tope mide la máquina, no el arreglo L138; lo que importa ya lo cubre `len(llamadas) == 1` (el barrido se arma una sola vez). | clon/tests/test_solidos_crear.py:604 | 2026-11-06 |
| B-220 | Repujado con «Envolver» en un cilindro lejos del perfil: la lámina da vueltas y repuja al otro lado | Abierto | Media | Placa 60×40×10 con las aristas de arriba empalmadas r3 y cuadro 10×10 en el centro de la tapa: `create_emboss faces="Cuerpo1/F3" wrap=true depth=1` sobre el empalme izquierdo (a 19 mm del cuadro) suma **+39,71 mm³** en ese empalme, y con los cuatro (+287,14). `_envolver_en_cilindro` pasa la coordenada tangencial del perfil a ángulo sin tope (`a_uv`, arco/radio ≈ 6,7 rad), así que la lámina envuelve el cilindro más de una vuelta y `recortar` la recorta contra la cara justo donde no debía. Fusion no repuja ahí. Arreglo: exigir que el arco del perfil quede dentro de ±π/2 de la generatriz que lo mira (o recortar contra el prisma del perfil). | clon/omnicad/nucleo/solidos_crear.py (`_envolver_en_cilindro`, `a_uv`); evidencia local `evidencias/ui_2026-11-06/sonda_b217_caras.py` | 2026-11-06 |
| B-219 | Nervio y Red › la flecha de «Distancia» no apunta al sentido que elige el núcleo | Abierto | Baja | El Nervio y la Red van a la cara **más cercana** del cuerpo (`_sentido_hacia_cuerpo`), pero la flecha del asa de Distancia se dibuja sobre ±normal del plano del boceto, girada con «Cambiar dirección»: en una caja 40³ cerrada con el boceto en y = 30 (paredes a 8 y a 28) la red crece hacia +Y y la flecha apunta −Y, con y sin invertir (`evidencias/ui_2026-11-06/sonda_asas_red.py`). En el Nervio la flecha es además perpendicular al crecimiento (el nervio crece en el plano del boceto). Arreglo: pedir el sentido al núcleo con el cuerpo objetivo, o dibujar la flecha desde la forma ya calculada de la previa. | clon/omnicad/ui/comandos/asas_extra.py:295 (`_asas_nervio`) | 2026-11-06 |
| B-196 | Barrer y el sector del labio pierden la autointersección sin avisar | Abierto | Media | `barrer` (dos sitios) y `_sector_labio` no pasan por el aviso de autointersección que ya tienen Tubo y Patrón geométrico (B-167, B-168). Hallado en la revisión del 2026-11-05. | nucleo/solidos_crear.py | 2026-11-05 |
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
| B-257 | Construir › «Plano en el ángulo» salta 90° cuando la arista pasa ~25,8° de la vertical | Abierto | Media | `_plano_por_eje` (`timeline/ops_construir.py` ~60) elige el 0° con el umbral fijo `abs(d[2]) < 0.9`: con una caja girada por parámetro, la normal pasa de (0,1,0) a (-0.899,0,0.438) entre 25° y 26°. Un parámetro no debe mover el plano a saltos. Medir en Fusion con la arista inclinada qué plano toma como 0° y dar una regla continua | `evidencias/juez_construir_2026-11-08/h_orientado.py` (sección «salto») | 2026-11-08 |
| B-258 | Construir › «Punto a través de dos aristas» con aristas alabeadas inventa el punto medio entre las rectas | Abierto | Baja | `edges:>Z and >X` + `edges:<Z and >Y` devuelve (20,20,5), que no está en ninguna arista, sin aviso. La ayuda de Fusion pide intersección (o extendida): debe dar error, como ya hace el plano por dos aristas | `evidencias/juez_construir_2026-11-08/c_ataque2.py` (sección 6) | 2026-11-08 |
| B-259 | Construir › SCU con `x_axis` paralelo a `z_axis` se acepta y descarta el X sin avisar | Abierto | Baja | x=Z, z=Z da x=(1,0,0); x=X, z=X da x=(0,0,-1); `avisos` vacío, también al cargar receta. X≡Y sí da `OPERATION_FAILED`: dar el mismo error | `evidencias/juez_construir_2026-11-08/c_ataque2.py` (sección 5) | 2026-11-08 |
| B-260 | Construir › un plano que se referencia a sí mismo (`objeto_extension`, vía `edit_feature` o receta) no se puede borrar ni mover | Abierto | Baja | `OpPlano.dependencias` (`timeline/operaciones.py` ~693) resta `{self.id}` solo de `refs`, no de `objeto`, `lugar` ni `objeto_extension`: `delete_feature` da `FEATURE_IN_USE: la usan Plano1` (él mismo). Rechazar el ciclo al editar o cargar | `evidencias/juez_construir_2026-11-08/f_dependencias.py` (sección 3) | 2026-11-08 |
| B-261 | Construir › `edit_feature` se saltea las validaciones de crear plano y da error crudo | Abierto | Media | `tipo="angulo"` sobre una cara plana da `ok:true` y un plano sin sentido (crear lo rechaza); `distancia=[1]` o `None` se guarda y al recalcular sale `Error inesperado: 'dict' object has no attribute 'strip'` con traceback (`timeline/parametros.py` ~489). Validar igual que la herramienta de creación | `evidencias/juez_construir_2026-11-08/e_receta.py` (edit_feature y f22) | 2026-11-08 |
| B-262 | Recetas › `apply_recipe` acepta ids de paso duplicados (el plano queda tapado por el punto), SCU `origen:null` y nombres de 100 000 caracteres | Abierto | Baja | Rechazar al cargar: id repetido, referencia obligatoria nula y nombres sin tope | `evidencias/juez_construir_2026-11-08/e_receta.py` (f21, f12, f18) | 2026-11-08 |
| B-263 | Construir › los planos de un SCU (`op2_xy`) no sirven como texto en `create_sketch` ni `create_construction_plane` | Abierto | Baja | `create_ucs` y `get_scene_info` los anuncian, pero `plane="op2_xy"` da `PLANE_NOT_FOUND`; `create_sketch` solo acepta texto, así que no hay forma de dibujar en un plano del SCU. En ejes y puntos el texto sí anda | `evidencias/juez_construir_2026-11-08/g_scu_refs.py` | 2026-11-08 |

## Ensamblar (auditoría contra Fusion, 2026-10-25)

Cada fila salió de comparar ENSAMBLAR (uniones, componentes, grupo rígido, vínculos, estudio de movimiento) con los artículos de la ayuda de Fusion (carpeta `fusion-assemble`), de probar unas 60 llamadas por API (`evidencias/ensamble_2026-10-25/a*.py`) y de usar la ventana real como una persona (`scripts/prueba_ui/ensamblar.py`, 224 comprobaciones). Lo que ya estaba cargado (P-25e, P-25e2, SC6, SC7, SC8, SC15, H-4, H-5, H-19, F8, P-6d) no se repite.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
## Detalle de lo abierto

Ficha original de cada bug abierto o parcial (del PROJECT_LOG al 2026-10-20); se borra junto con su fila. La tabla
de arriba manda sobre este texto.

### B-220 · Repujado con «Envolver» en un cilindro lejos del perfil repuja dando una vuelta de más

- **Qué:** placa 60×40×10 con las cuatro aristas de arriba empalmadas r 3 (`fillet edges=">Z" radius=3`), cuadro
  10×10 en (20..30, 15..25) en un plano a z = 10; `create_emboss faces="Cuerpo1/F3" depth=1 wrap=true` eligiendo el
  empalme izquierdo (su centro está en x = 1, el cuadro a 19 mm de ahí). En la ventana: Repujado › Envolver, cara =
  ese empalme. Sin cadena tangente: la cara la eligió el usuario.
- **Esperado (Fusion):** «Emboss … by a specified depth and direction» sobre la cara elegida; lo que no cae sobre
  la cara se pierde (la ayuda de `Emboss reference` no promete envolver alrededor del cilindro). Ahí no va material.
- **Obtenido:** +39,71 mm³ en ese empalme (caja x 0,7..5,6), y +287,14 mm³ repartidos en los cuatro (`evidencias/ui_2026-11-06/sonda_b217_caras.py`).
- **Causa (leída):** `_envolver_en_cilindro` arma la coordenada U con `u0 + giro · (distancia tangencial)/radio`
  (`nucleo/solidos_crear.py`, `a_uv`), sin tope: 20 mm sobre un radio 3 dan 6,7 rad, o sea más de una vuelta, y la
  superficie cilíndrica es periódica, así que la lámina vuelve a pasar por el sector de la cara. El `recortar`
  posterior corta contra la cara y deja la parte que ya había dado la vuelta.
- **Prueba propuesta:** envolver en una cara cilíndrica que no está bajo el perfil no agrega material (o avisa);
  envolver en la cara que sí está bajo el perfil sigue dando el mismo volumen que hoy (caso `test_repujado_envolviendo_un_cilindro`).

### B-219 · La flecha de «Distancia» del Nervio y la Red no muestra el sentido que elige el núcleo

- **Qué:** caja 40³ cerrada, vaciada 2 mm; plano XZ desplazado −30 (boceto en y = 30, paredes a 8 y a 28) con la línea
  z = 20 de x 10 a 30; Red › Tipo de extensión «Distancia» y «Cambiar dirección». Lo mismo con Nervio.
- **Esperado (Fusion):** el manipulador de distancia sigue la extrusión real; «Flip Direction» lo gira con ella.
- **Obtenido:** la red crece hacia +Y (la pared más cercana) y la flecha apunta −Y; con «Cambiar dirección» crece hacia
  −Y y la flecha apunta +Y (`evidencias/ui_2026-11-06/sonda_asas_red.py`, MISMATCH en los dos). En el Nervio la flecha
  va por la normal del plano, o sea perpendicular al crecimiento, que es dentro del plano.
- **Causa (leída):** `_asas_nervio` arma la flecha con `normal del plano × (−1 si invertir)`
  (`ui/comandos/asas_extra.py:295`), mientras `_sentido_hacia_cuerpo` elige el sentido por la cara más cercana.
- **Prueba propuesta:** con el boceto a y = 30 la flecha de Distancia apunta +Y sin invertir y −Y invertida, igual que
  la previa.

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
