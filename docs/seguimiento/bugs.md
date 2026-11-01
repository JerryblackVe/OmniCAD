# Bugs

Algo que falla, da un resultado malo o un mensaje engañoso. Método y columnas: [README](README.md).

Solo lo que falta resolver: al resolverse, la fila se borra. Verificado contra el código el 2026-10-23 (Superficie y Sólido, también en la ventana real: 2026-10-24; revisión de B-39 y regresiones de B-48: 2026-10-27). Tortura de operaciones y booleanas: 2026-11-01. Total 12: Abierto 7 · Parcial 3 · Bloqueado 1 · Sin verificar 1.

## Abiertos y parciales

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| B-144 | Cortar con una esfera casi tangente a una pared puede quitar de menos sin avisar | Abierto | Media | Hueca de pared 3 (caja 60×40×20 menos 54×34 desde z = 3) y esfera r 4 en (18,537165, 20,0001, 10,0001): cortar quita 103,79 mm³ de 122,5 (antes de B-125 quitaba 0) y el común da 121,97. Las muestras de `_comun_desmentido` solo ven diferencias de 1/4 de la pieza chica. | clon/tests/test_booleanas_tortura.py::test_b125_esfera_casi_tangente_no_se_queda_sin_cortar | 2026-11-01 |
| B-138 | `sin(PI/4 rad)` da 0,000239 en lugar de 0,7071, sin ningún aviso | Abierto | Media | La unidad se pega al último número en lugar de a la expresión. Corregirlo con PAR-1. | timeline/parametros.py:46 (`_NUM_CON_UNIDAD`); ejemplo de `Parameters reference`; reproducido por API | 2026-11-01 |
| B-139 | `round(2.5)` da 2 en lugar de 3 | Abierto | Baja | La ayuda dice que .5 redondea alejándose de cero. | timeline/parametros.py:41 usa `round` de Python; `Parameters reference`; reproducido por API | 2026-11-01 |
| B-140 | Renombrar un parámetro en uso falla en lugar de actualizar lo que lo usa | Abierto | Media | Actualizar expresiones y pasos. Con otro parámetro, el error dice «Nombre desconocido: 'w'». | api/herramientas_parametros.py:90; ayuda `Parameters in Fusion` § Edit parameters; reproducido por API | 2026-11-01 |
| B-141 | Una longitud acepta `w * h` y guarda 200 mm | Abierto | Media | Validar la magnitud con PAR-2. Mientras tanto, el valor es incorrecto y no avisa. | timeline/parametros.py:82; `Parameters in Fusion`: la unidad del resultado debe coincidir; reproducido por API | 2026-11-01 |
| B-142 | El nombre `µm_x` se rechaza con un mensaje equivocado | Abierto | Baja | Habla de letra más marca combinada. Fusion admite `µ`, `$`, `°` y `"`. | timeline/parametros.py:177; `Parameters reference` § Name; reproducido por API | 2026-11-01 |
| B-143 | La tabla de parámetros muestra el valor con 4 cifras y sin unidad | Abierto | Baja | Mostrar el valor completo con la unidad del parámetro: 12345,678 sale como 1.235e+04. | ui/dialogos.py:331 (`:.4g`) | 2026-11-01 |
| B-132 | Un texto que toca otra curva se elige mal: toma H, A y el hueco de la O, y deja afuera L y el aro de la O | Abierto | Alta | Una letra elige todo el texto aunque cruce otra curva. Las letras no pueden depender de que el borde sea solo de texto, y Extruir no debe rellenar el hueco. | nucleo/perfiles.py:102 y ui/visor3d.py:1259 (`set(p.firma) <= ids`): sin el aro, el hueco de la O queda como letra; video del 2026-11-01, 1:54 a 2:26; reproducido por API | 2026-11-01 |
| B-133 | Un texto que cruza una curva deja perfiles basura, y Extruir acepta uno de área 0 con volumen 0 | Abierto | Media | No listar restos sin área y rechazar la extrusión de volumen 0 con un mensaje claro. | HOLA altura 30 sobre círculo R57: 9 perfiles; separado 2 mm: 7. Perfil de área 0,0 responde ok con volumen 0.0; perfil de área 1,29 da 12,9; reproducido por API | 2026-11-01 |
| B-134 | El disco queda mellado cuando el texto apoya sobre su borde | Abierto | Media | La ayuda no aclara si el texto parte otras curvas: comprobarlo en Fusion real y decidir. Hoy resta material. | Perfil de área 10205,74 contra 10207,03 (π·57²); volumen 102057,4 contra 102070,3; video del 2026-11-01, 1:40 a 1:44 (costuras en el canto); reproducido por API | 2026-11-01 |
| B-135 | La barra de estado queda en «Calculando Extrusión…» después de la vista previa o de Cancelar | Abierto | Baja | Limpiar el aviso al terminar la previa y al cerrar el comando. | ui/ventana.py:980 lo deja 30 s y solo `_actualizar` lo limpia; ui/comando.py `_cerrar` no lo toca; video del 2026-11-01, 1:54 al final | 2026-11-01 |
| B-136 | Al abrir Extruir aparece un instante una ventanita suelta de OmniCAD | Abierto | Baja | Buscar qué ventana se muestra sin padre. La causa no está identificada. | video del 2026-11-01, cerca de 1:37: un solo cuadro con el ícono, maximizar y cerrar | 2026-11-01 |
| B-137 | Al deslizar un texto en curva queda una sombra de las letras y se apaga el relleno del disco | Abierto | Media | Repintar los rellenos durante el arrastre. Revisar también la L oscura que queda suelta en la posición vieja. | ui/editor_boceto.py:5029 (`_deslizar_texto` solo pide `update`; causa probable, sin comprobar); video del 2026-11-01, 0:49 a 0:55 y 1:01 a 1:30 | 2026-11-01 |
| B-130 | Una construcción que no se puede calcular responde «No existe 'opN'» | Abierto | Baja | El `KeyError` de `estado_final` tapa la causa: dos aristas alabeadas, planos paralelos, tangente sobre cara plana. | api/errores.py:264; api/herramientas_construccion.py (`puntos[op.id]`); reproducido por API | 2026-11-01 |
| B-131 | Una spline donde va una línea da INTERNAL_ERROR en CONSTRUIR | Abierto | Baja | Filtrar la spline en la ventana y responder un error de argumentos en la API. | docs/brechas_construir.md § B-131; reproducido por API | 2026-11-01 |
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

### B-144 · Cortar con una esfera casi tangente a una pared puede quitar de menos sin avisar

**Gravedad:** media (hace falta un contacto casi tangente; el cuerpo sale válido y estanco). **Entorno:** OmniCAD, Windows, API sin ventana. **Estado:** reproducido; apareció comparando cortar junto y de a una en 300 casos al azar con un árbitro de puntos.

**Qué hice:** `geo.booleano(hueca, geo.esfera(4, (18.537165, 20.0001, 10.0001)), "cortar")`, con `hueca` = caja 60×40×20 en (-30, -20, 0) menos caja 54×34×20 en (-27, -17, 3).

**Esperado:** quitar 122,5 mm³ (media esfera menos el casquete que pasa al hueco). **Obtenido:** quita 103,79 mm³, válido y sin aviso; el común da 121,97.

**Causa probable (leída):** el primer reintento creíble gana. `_comun_desmentido` deja pasar lo que difiere menos de 1/4 de la pieza chica, porque con 16 muestras no se puede afirmar menos. Reordenar `_REINTENTOS_BOOLEANA` podría resolverlo, pero cambia recetas que hoy dan bien. También: en ese mismo banco, 1 caso de 300 (el 60) da mal cortando de a una, y 3 terminan en error claro. **Esquive:** mover la esfera una milésima. **Prueba propuesta:** el caso de arriba, esperando 122,5 mm³ con tolerancia 1 mm³.

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
