# Bugs

Algo que falla, da un resultado malo o un mensaje engañoso. Método y columnas: [README](README.md).

Solo lo que falta resolver: al resolverse, la fila se borra. Verificado contra el código el 2026-10-23 (Superficie y Sólido, también en la ventana real: 2026-10-24; revisión de B-39 y regresiones de B-48: 2026-10-27). Tortura de operaciones y booleanas: 2026-11-01. Total 14: Abierto 9 · Parcial 3 · Bloqueado 1 · Sin verificar 1.

## Abiertos y parciales

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| B-129 | El volumen de una lente (esfera ∩ esfera) tiene hasta 0,5 mm³ de error; unir y cortar dan exacto | Abierto | Baja | Dos esferas de radio 20 con los centros a 20,6 mm: la fórmula de la lente da 9897,866 mm³ y `intersect` da 9898,405 (+5,4e-5 relativo); a 10 mm da −0,532; a 30 mm +0,172. `volumen` y `volumen_exacto` coinciden entre sí, y la unión (57122,777) y el corte (23612,455) cierran con la fórmula al milésimo. Falta saber si es la geometría de la lente o la integración sobre sus dos casquetes. Con centros a 7,07 y 39 mm el error es 0. | clon/omnicad/nucleo/geometria.py:890 (`volumen`) | 2026-11-01 |
| B-128 | Cortar o unir con un cuerpo de ~1 µm deja autointersecciones sin avisar | Abierto | Media | Una caja de 1e-6 mm centrada en una arista o cara de otra de 40 mm: `boolean_operation` cortar o unir da ok, sin avisos y `valid: true`, pero `check_geometry` cuenta 1 a 6 autointersecciones (con 3e-7 y unir, 36). Con 1e-4 y 1e-5 solo salen advertencias de arista diminuta. | clon/omnicad/nucleo/geometria.py:478 (`_problema_booleana` mira aristas libres, no manifold y validez; no las autointersecciones) | 2026-11-01 |
| B-127 | Una herramienta repetida en `boolean_operation` da «Error inesperado: 'op2.c1'» | Abierto | Baja | `tools=["B","B"]` (o `["B","b"]`) falla con un KeyError sin explicar; el documento queda como estaba. Tiene que decir «la herramienta B está repetida» o ignorar el duplicado. | clon/omnicad/timeline/operaciones.py:1264 | 2026-11-01 |
| B-126 | Intersecar deja aristas no múltiples sin avisar | Abierto | Media | Una caja vaciada contra otra con 9 agujeros pasantes, con caras coplanares: el resultado trae 3 aristas no manifold, `valid: true` y ningún aviso (unir sí avisa con «dejó el cuerpo partido»). El volumen cierra con el de cortar. | clon/omnicad/nucleo/geometria.py:478 (`_problema_booleana`) | 2026-11-01 |
| B-125 | Unir dos toros con ≤ 1e-4 mm de solape pierde uno entero sin avisar | Abierto | Media | Dos toros iguales (R 14, r 6) con el borde exterior casi tangente: `unir` devuelve UN toro (9948,56 mm³ en vez de ~19897) sin aviso. Con 1e-3 de solape anda. El rango de volumen que el kernel da por creíble para «unir» empieza en max(VA, VB), así que «B desapareció» pasa. | clon/omnicad/nucleo/geometria.py:478 (`limites` de `_problema_booleana`) | 2026-11-01 |
| B-123 | Un cuerpo que pasa a otro componente sigue a la unión del componente anterior | Abierto | Media | Si TODOS los cuerpos de un componente nuevo vienen del mismo componente movido por una unión, el nuevo hereda ese movimiento (`_matriz_de_cuerpos`): no salta de lugar, pero al accionar después esa unión el cuerpo se sigue moviendo, aunque ya no pertenece a ese componente y el aviso de ASM-7 diga que sus uniones ya no mueven nada. En Fusion el cuerpo queda donde estaba al reasignarlo. Hace falta guardar en la receta la pose del momento de reasignar. Ya pasaba antes de B-108. | omnicad/timeline/ops_ensamblar.py (`_matriz_de_cuerpos`); tests/test_posicion_asm.py::test_b108_todos_del_mismo_componente_el_nuevo_hereda_su_movimiento_y_no_gira_dos_veces | 2026-11-01 |
| B-122 | Las clases de las tablas de Fusion no modelan el Ø mayor del agujero ni el Ø menor del eje | Abierto | Media | `desfases_rosca` solo da flancos y menor del agujero: el Ø mayor sale de `diametro/2 + desfase`. Tr12x3 7H: la tabla dice 12,5 y se modela 12,15; 7e: Ø menor 8,3175 y se modela 8,803. Afecta a todo tipo de `tablas_rosca.CLASES`. Falta confirmar en Fusion real (el MCP no conecta) qué diámetro usa la rosca modelada y pasarlo a `_surco_rosca` | clon/omnicad/nucleo/tolerancias.py:333 | 2026-11-01 |
| B-121 | Volver a resolver un boceto con una tangente general (spline) corre la geometría un poco cada vez | Abierto | Media | En `_tangencia` el contacto arranca de una muestra de 96 puntos, no del contacto exacto: el solver no parte de la solución y reparte el error entre la curva y el parámetro. Medido 2026-10-31 con arco de radio 10 y spline ya tangentes: 10,0000 → 10,0091 → 10,0175 → 10,0254 → 10,0326 por pasada. Arreglarlo cambia lo que dan las recetas guardadas con esas tangentes: decidir antes de tocar el solver (idea: afinar los dos parámetros con la geometría quieta y usarlos solo si el residuo ya es cero) | `tests/test_restricciones_matematica.py::test_tangente_con_el_comando_no_cambia_el_radio_del_arco`; `omnicad/restricciones/solver.py` (`_tangencia`) | 2026-10-31 |
| B-119 | Proyectar un cuerpo curvo visto de costado no da su silueta | Abierto | Alta | Fusion promete perfiles cerrados con el filtro Cuerpos («closed profiles»), pero `proyectar_forma` proyecta solo aristas: un cilindro R14 sobre XZ da 3 líneas abiertas (falta el lado opuesto a la costura) y 0 perfiles; una esfera da una línea o un arco. Hace falta sumar la silueta (HLR de `nucleo/dibujo.py`), con cuidado: un vínculo a un cuerpo la recalcularía en cada paso del timeline, y sobre roscas tarda más de 90 s. Mirado de frente anda bien (cilindro sobre XY: 1 círculo, 1 perfil). | omnicad/nucleo/perfiles.py (`proyectar_forma`); tests/test_proyectar_tarjeta.py::test_cambiar_de_filtro_saca_lo_incompatible_y_lo_dice | 2026-10-31 |
| B-118 | Un corte sin objetivo elegido también corta los cuerpos ocultos | Abierto | Media | Con Objetos vacío se cortan todos los sólidos que toca, también los ocultos. Extruir (B-117) y `operation="auto"` ya ignoran lo oculto al decidir, pero el paso no: falta decidir si la herramienta se queda con los visibles al crear el paso, como la extensión Todo de Fusion (`Extrude reference`: «all visible bodies»). | timeline/operaciones.py:345 | 2026-10-31 |
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

### B-129 · El volumen de una lente (esfera ∩ esfera) tiene hasta 0,5 mm³ de error

**Gravedad:** baja (5e-5 relativo; el volumen de unir y de cortar cierra). **Entorno:** OmniCAD 2d8212e, Windows, API sin ventana. **Estado:** reproducido (la matriz de booleanas, celda esfera × esfera «cruza», y una cuenta directa con `geo.booleano` en 6 distancias).

**Qué hice:** `create_sphere radius=20 x=0 z=10 name=A`; `create_sphere radius=20 x=20 z=15 name=B`; `boolean_operation target=A tools=["B"] operation=intersect`; `get_physical_properties`.

**Esperado:** la lente de dos casquetes con centros a d = 20,6155 mm: π(4r + d)(2r − d)² / 12 = 9897,866 mm³. **Obtenido:** 9898,405 mm³ (+0,539). Unir da 57122,777 y cortar 23612,455: los dos cierran con la fórmula. Distancias de 10, 20, 30 mm: −0,532, +0,094, +0,172; de 7,07 y 39 mm: 0.

**Causa:** sin leer. `volumen` y `volumen_exacto` dan lo mismo, así que si el error es de la integración de las dos caras trimadas, está en las dos. **Esquive:** ninguno hace falta; para comprobar, medir con una malla. **Prueba propuesta:** la lente de arriba contra la fórmula, tolerancia 1e-6.

### B-128 · Cortar o unir con un cuerpo de ~1 µm deja autointersecciones sin avisar

**Gravedad:** baja (cuerpos de 1 µm son raros; pasa si una cota paramétrica cae casi a cero). **Entorno:** OmniCAD 2d8212e, Windows, API sin ventana. **Estado:** reproducido 2 veces (`evidencias/tortura_2026-11-01/repro3.py`).

**Qué hice:** `create_box length=40 width=40 height=40 name=A`; `create_box length=1e-6 width=1e-6 height=1e-6 x=20 y=20 z=20 name=B` (en medio de una arista vertical de A); `boolean_operation target=A tools=["B"] operation=cut` (y otra vez con `join`); `check_geometry`.

**Esperado:** un cuerpo limpio, o un aviso. **Obtenido:** ok, `avisos: []`, volumen 64000, `valid: true`, `self_intersections: 1`. Con B en (20, 0, 20) y `join`: 6 autointersecciones; con B en (0, 0, 20) y `join`: sí avisa («dejó el cuerpo partido»). Con 1e-4 y 1e-5: solo advertencias `tiny_edge`.

**Causa probable (leída):** `_problema_booleana` compara volúmenes, aristas libres / no manifold y validez, no autointersecciones. **Esquive:** no usar cuerpos menores de 1e-4 mm; correr `check_geometry` tras la operación. **Prueba propuesta:** el caso de arriba en `tests/`, esperando un aviso o un error.

### B-127 · Una herramienta repetida en `boolean_operation` da «Error inesperado: 'op2.c1'»

**Gravedad:** baja (el documento no se toca). **Entorno:** OmniCAD 2d8212e, Windows, API sin ventana. **Estado:** reproducido 2 veces (`repro4.py`).

**Qué hice:** `create_box length=40 width=40 height=40 name=A`; `create_box length=10 width=10 height=10 x=20 name=B`; `boolean_operation target=A tools=["B","B"] operation=join` (y con `["B","b"]`, `operation=cut`).

**Esperado:** un error claro («la herramienta B está repetida») o que ignore el duplicado. **Obtenido:** `OPERATION_FAILED … Error inesperado: 'op2.c1'` y un `KeyError` en el log.

**Causa probable (leída):** `operaciones.py:1264` hace `del estado.cuerpos[h.id]` por cada herramienta; con la lista repetida borra dos veces la misma. **Esquive:** no repetir. **Prueba propuesta:** el caso de arriba, esperando el mismo resultado que con `["B"]`.

### B-126 · Intersecar deja aristas no múltiples sin avisar

**Gravedad:** media (el sólido sigue las operaciones siguientes con una arista que une más de dos caras). **Entorno:** OmniCAD 2d8212e, Windows, API sin ventana. **Estado:** reproducido 2 veces (`repro6.py`, y la celda hueca × agujeros / coplanar de la matriz en `resultados/bool.json`).

**Qué hice:** `create_box length=40 width=40 height=20 x=0 z=0 name=A`; `shell body=A faces=">Z" thickness=3`; `create_box length=40 width=40 height=20 x=20 z=0 name=B`; `create_hole face=">Z" body=B diameter=6 through_all=True points=[[8,-12],[8,0],[8,12],[20,-12],[20,0],[20,12],[32,-12],[32,0],[32,12]]`; `boolean_operation target=A tools=["B"] operation=intersect`.

**Esperado:** un sólido sin aristas compartidas por más de dos caras, o un aviso. **Obtenido:** ok, `avisos: []`, 1 cuerpo de 5071,301 mm³ (cortar da 7276,699 = 12348 − 5071,301, el volumen cierra), `check_geometry`: `valid: true`, `non_manifold_edges: 3`.

**Causa:** sin leer. **Esquive:** `check_geometry` tras intersecar. **Prueba propuesta:** el caso de arriba, esperando un aviso o 0 aristas no manifold.

### B-125 · Unir dos toros con ≤ 1e-4 mm de solape pierde uno entero sin avisar

**Gravedad:** media (pierde material sin error, pero hace falta un contacto casi tangente; con 1e-3 de solape anda). **Entorno:** OmniCAD 2d8212e, Windows, API sin ventana. **Estado:** reproducido 2 veces y en la matriz de booleanas (`repro6.py`, `resultados/repro6.txt`).

**Qué hice:** `create_torus major_radius=14 minor_radius=6 x=0 z=10 name=A`; `create_torus major_radius=14 minor_radius=6 x=39.9999 z=10 name=B`; `boolean_operation target=A tools=["B"] operation=join`.

**Esperado:** ~19897,12 mm³ (la suma menos una lente casi nula). **Obtenido:** ok, `avisos: []`, 1 cuerpo, 9948,561 mm³ (un toro), `valid: true`. Con solapes de 1e-6, 1e-5 y 1e-4 igual; con 1e-3, 19897,119 correcto. Cilindros y cajas tangentes sí avisan.

**Causa probable (leída):** `_problema_booleana` da por creíble para «unir» todo volumen entre max(VA, VB) y VA + VB: un resultado igual a un solo cuerpo cae justo en el borde de ese rango. **Esquive:** solapar ≥ 0,001 mm o comparar el volumen tras unir. **Prueba propuesta:** el caso de arriba, esperando el volumen de la suma (o error / aviso).

### B-122 · Las clases de las tablas de Fusion no modelan el Ø mayor del agujero ni el Ø menor del eje

**Gravedad:** baja (el tornillo y la tuerca de la misma clase no chocan: el agujero queda con menos fondo que el de la tabla). **Entorno:** OmniCAD, Windows, API sin ventana. **Estado:** reproducido por cuenta y con el kernel.

**Qué hice:** tuerca hexagonal de 22 mm entre caras y 10 mm de alto, `create_hole` con `hole_tap="modeled"`, `thread="Tr12x3"`, `through_all=True`, `print_clearance=0.15` y la clase «auto» (7H).

**Esperado:** la tabla de Fusion para 7H da Ø mayor 12,5, Ø flancos 10,65 y Ø menor 9,1575. Con los tres en su valor, la cuenta da 3210,61 mm³. ⚠ Fusion real no conectó: falta confirmar que la rosca modelada use ese Ø mayor. **Obtenido:** flancos y menor al valor de la tabla, Ø mayor 12,15 + holgura: 3234,93 mm³ (0,75 % más).

**Causa:** `desfases_rosca` devuelve `flancos` y `menor`; `_surco_en_origen` calcula el fondo con `diametro / 2 + desfase`, y `_limites_tabla` ni devuelve el Ø menor del eje. **Esquive:** ninguno hace falta para que encastre. **Prueba propuesta:** el volumen de una losa de 1 mm de esa tuerca contra la cuenta con el Ø mayor de la tabla (`tests/test_b70_pasante.py`, cambiando el área del hueco a 98,0951 mm²).

### B-119 · Proyectar un cuerpo curvo visto de costado no da su silueta

**Gravedad:** media. **Entorno:** OmniCAD, Windows, núcleo sin ventana. **Estado:** reproducido.

**Qué hice:** `proyectar_forma(g.cilindro(14, 47), g.Plano("XZ"))` y la esfera `g.esfera(10)` sobre XY y XZ, y `detectar` sobre el boceto.

**Esperado:** Fusion, filtro Bodies: «projects closed profiles that are ready for constraints and downstream features» (`project-geometry-onto-a-sketch-plane`). ⚠ Fusion real no conectó: la silueta exacta no se comparó en la app. **Obtenido:** cilindro: 3 líneas abiertas, 0 perfiles. Esfera: 1 línea (XY) o 1 arco (XZ), 0 perfiles. La caja y el cilindro de frente andan bien.

**Causa:** `proyectar_forma` recorre solo las aristas reales de la forma; la silueta de una cara curva no es una arista. **Esquive:** proyectar sobre un plano donde el cuerpo tenga aristas reales, o dibujar el perfil. **Prueba propuesta:** cilindro sobre XZ da un rectángulo con un perfil de 28 × 47; medir el costo con una rosca modelada antes de vincularlo al timeline.

### B-118 · Un corte sin objetivo elegido también corta los cuerpos ocultos

**Gravedad:** media. **Entorno:** OmniCAD, Windows, API sin ventana. **Estado:** reproducido.

**Qué hice:** caja de 20 × 20 × 10 oculta (`__navegador__`, `ocultos`), y `create_box` de 4 × 4 × 20 con `z=-5` y `operation="cut"`, sin `target`.

**Esperado:** a confirmar en Fusion real: la ayuda solo dice «all visible bodies» para la extensión Todo, y «Objects To Cut» no aclara lo oculto. **Obtenido:** la caja oculta pasa de 4000 a 3840 mm³.

**Causa:** `aplicar_resultado` toma todos los sólidos del estado: el timeline no sabe qué está oculto (timeline/operaciones.py:345). **Esquive:** elegir Objetos a mano. **Prueba propuesta:** la de arriba, comparando el volumen del cuerpo oculto.

### B-48 · Crash nativo OCCT (0xc0000005) al recalcular parámetros a 148 pasos

**Mitigado 2026-10-20** (`agente/b48`): no se reprodujo en 18 min; la caída de un hijo aislado vuelve como `TareaAislada`. Sigue Parcial. **Crash nativo durante la tortura de parámetros** (±30 % a 148 pasos): APPCRASH de `pythonw.exe`, excepción 0xc0000005 en `TKernel-….dll` (OCCT 8.0.1) offset 0x78bed, 09:11:23; el puente murió a mitad de llamada (`BRIDGE_ERROR WinError 10054`). El autoguardado (receta sin caché, 18 s antes) permitió recuperar todo. Evento completo en `crash2_evento_completo.txt`.

kernel OCCT vía cadquery_ocp; recálculo

Reproducido (firma de Windows): no se puede curar desde la app; queda la protección por autoguardado

Crítico

**2026-10-27 (agente nocturno)**: se armó una tortura sintética de 141 pasos y 46 cuerpos (booleanas, empalmes, chaflanes, patrones y simetrías; `evidencias/b48_2026-10-27/`) y se corrieron 300 rondas de 4 cambios ±30 % cada una en procesos aparte con faulthandler: 0 caídas y 0 pasos con error; 60 rondas más con `OMNICAD_SIN_PARALELO=1` tampoco cayeron (9,98 s/ronda contra 9,23 s con paralelismo: apagarlo cuesta ~8 %). El motor RL-1 real, con el estado mixto del crash original, tampoco cayó en 3 rondas (abrir 78-85 s; r_camara/largo_camara ~105-109 s por recálculo; d_eje ~21 s). El paralelismo no es la causa demostrable; queda el interruptor `OMNICAD_SIN_PARALELO` para diagnosticar. Se extendió el prevuelo aislado a `reemplazar`, `suprimir` y `eliminar` pasos y a `abrir` archivos de 60 pasos o más (el RL-1: 155,6 s con prevuelo contra ~80 s sin él); si el hijo cae, el documento no se toca y sale un `ErrorDocumento`/`ErrorProyecto` claro. Segunda ronda (2026-10-27): el padre adopta el cálculo del hijo (`timeline/calculo_aislado.py`: grafo + BREP, sin pickle) en vez de repetirlo con el kernel; deshacer, rehacer, mover paso, mover marcador y configuraciones también calculan en el hijo; la ventana avisa «Calculando…» pasado 1 s. Sigue Parcial porque la caída nativa no se reprodujo ni curó.

**2026-11-01 (tortura de operaciones, `main` en 2d8212e):** otro documento sintético propio, de 146 pasos y 48 cuerpos (24 bloques de caja, empalme |Z, agujero pasante, saliente cilíndrico unido, saliente en caja y espejo, más un corte), armado en 307,6 s sin errores. 47 rondas de 8 cambios de parámetro (L ×1,3, H ×0,7, r ×1,3, W ×0,7 y vuelta a los valores base): 376 cambios, 0 caídas, 0 errores, `pasos_con_error` 0, volumen final igual al inicial y RSS pico 524 MB; con `faulthandler` encendido, `b48_fault.txt` quedó vacío. Cada cambio tardó ~3,4 s: el hijo aislado se encarga solo (≥ 60 pasos). Tampoco se reprodujo.
