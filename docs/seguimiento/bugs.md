# Bugs

Algo que falla, da un resultado malo o un mensaje engañoso. Método y columnas: [README](README.md).

Solo lo que falta resolver: al resolverse, la fila se borra. Verificado contra el código el 2026-10-23 (Superficie y Sólido, también en la ventana real: 2026-10-24; revisión de B-39 y regresiones de B-48: 2026-10-27). Total 7: Abierto 2 · Parcial 3 · Bloqueado 1 · Sin verificar 1.

## Abiertos y parciales

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| B-112 | El campo «factor» de Escalar acepta un valor con unidad («2 mm») como si fuera 2 | Abierto | Baja | `prueba_ui/teclear.py` (2026-10-29): al teclear «2 mm» en el factor de `escala_3d` el programa entiende 2,0 sin rojo ni mensaje, y la prueba espera que lo rechace (un factor no tiene unidad). Falta decidir si se rechaza o se ignora la unidad avisando, y que el campo lo diga. No lo causó ningún cambio de esta noche. | scripts/prueba_ui/teclear.py; evidencias/n2_A_ui2/teclear.log | 2026-10-29 |
| B-108 | Un cuerpo reasignado después de una unión se mueve mal al girar el componente anterior | Abierto | Alta | Al girar el padre, un cuerpo del hijo se desplaza respecto de otro del mismo hijo; preservar la posición relativa al reasignar componentes. | omnicad/timeline/ops_ensamblar.py:228-240; omnicad/timeline/ops_ensamblar.py:257-270 | 2026-10-28 |
| B-110 | Un boceto sobre una cara acumula proyecciones «perdidas» repetidas y muestra ⚠ en el navegador | Sin verificar | Media | En el abanico de Gerardo, Boceto3 (op47) tiene 5 proyecciones, 4 «perdidas» con arcos repetidos, y Boceto2 y Boceto3 muestran ⚠ en el navegador (video 2026-10-28 10-18-28). No se reprodujo desde cero: revisar si crear o editar un boceto sobre una cara apila proyecciones cuando la cara cambia, y si la marca ⚠ es correcta. | get_sketch op47 en vivo (2026-10-28); omnicad/restricciones/boceto.py (`agregar_proyeccion`, `proyecciones`) | 2026-10-28 |
| B-111 | Editar un boceto sobre el Lienzo de la raqueta congela la ventana ~9-10 s por acción (sobre todo al deshacer) | Abierto | Alta | En vivo (2026-10-28, «Sin título» con Lienzo PALETA.jpg de 126 140 caracteres y un boceto abierto, 0 cuerpos): 4 bloqueos de la interfaz de 10,2 · 8,7 · 9,0 · 10,1 s, tres justo después de Ctrl+Z, más otros de ~0,45 s; el visor sigue a ~1300 fps y la RAM estable (~700 MB), o sea que se traba el hilo de la ventana, no el dibujo. Más un bloqueo de 76 s al tocar «Seleccionar» (sesión 2026-10-28_194809). Causa medida fuera de la app (2026-10-28, contorno cerrado de splines encadenadas con tangentes): (1) `resolver()` tarda 1,2 s con 10 splines, 3,9 s con 60 y 14,2 s con 120 (sin tangentes: 0,1 ms); el costo está en `_Sistema.extremo` → `prim` → `primitivas_entidad`, que rearma la spline en cada residuo (20 640 llamadas). (2) Con el boceto en conflicto, `Lienzo.conflictos` llama `restricciones_en_conflicto`, que resuelve una vez POR vínculo, en el hilo de la ventana y al pintar: 0,8 s con 6 splines, 3,6 s con 12, 10,5 s con 20 (crece al cuadrado: un trazo de raqueta llega a minutos). Hacer: cachear el extremo de cada spline por sus coordenadas, y sacar el diagnóstico de conflictos del hilo de la ventana (a pedido o con tope de vínculos). | scripts de medición en el scratchpad de la sesión; omnicad/restricciones/solver.py:222 (`extremo`), :470-479 (`_tangencia`), :767-782 (`restricciones_en_conflicto`); omnicad/ui/editor_boceto.py:703-713, 4399, 4489, 4592 | 2026-10-28 |
| P-12c | Fuente de novedades de Fusion (la ayuda es un shell JS sin titulares) | Parcial | Baja | Autodesk le responde 403 a los scripts: ahora se lee la última copia de archive.org del blog «What's New» (hoy del 2026-05-16, 5 meses atrás) y el informe lo avisa; falta una fuente al día que no bloquee (feed o API) o seguir revisando a mano. | scripts/novedades.py (`bajar`, `COPIAS`); tests/test_novedades.py::test_fusion_apunta_al_blog_y_cae_a_archive_org_si_autodesk_bloquea | 2026-10-20 |
| P-1c | Wayland nativo: menús emergentes se cierran solos | Bloqueado | Alta | Necesita PC con Linux nativo (ver P-1b): el fallo solo aparece con Wayland y esta PC es Windows, así que no se pudo reproducir ni probar un arreglo; hoy se fuerza xcb y no molesta. | omnicad/ui/__init__.py:11-19 | 2026-10-20 |
| P-11j | Cuerpos «sin ubicar» de XOX (3) que quizá Fusion no tiene | Parcial | Alta | Sherpa resuelto (2026-10-21): comparado con Fusion, no tiene los 2 cuerpos (1593 y 952 mm³) y todos sus componentes con cuerpos están emparejados; ahora se descartan los bloques sin dueño cuando ningún componente de la escena queda sin bloque. Queda XOX: 3 componentes de la escena sin bloque y 3 bloques sin dueño (152,9; 494,8 y 4365,4 mm³): no se pueden descartar sin ver Fusion, y la versión en la nube (v35, 202 componentes) no es la del .f3z local (72 cuerpos): hace falta abrir en Fusion ese mismo archivo. | omnicad/io_archivos/f3d_escena.py (huerfanos); tests/test_p11a_f3d_instancias.py; tests/test_f3d_reales.py | 2026-10-21 |
| B-48 | Crash nativo OCCT (0xc0000005) al recalcular parámetros a 148 pasos | Parcial | Muy alta | La caída no se reprodujo: 300 rondas de una tortura sintética de 141 pasos (paralelismo de OCCT encendido), 60 con el paralelismo apagado y 3 rondas del motor RL-1 con el estado mixto original (r_camara y largo_camara a +30 % y d_eje 6→7,8→6) dieron 0 caídas; apagar el paralelismo no cambió la tasa y costó ~8 % más tiempo. Ya se ensayan en proceso aparte los cambios de parámetros, editar/suprimir/eliminar pasos (también sus vistas previas y la reactivación que alcanza el umbral) y abrir archivos de 60 pasos o más, antes de cargar el BREP; abrir el RL-1 pasó de ~80 a 155,6 s por el ensayo. Segunda ronda (RL-1, 148 pasos: abrir 85,5 s; cambiar d_eje 82,1 s; deshacer 79,7 s; rehacer 78,4 s): el padre ya no repite el cálculo, adopta el resultado del hijo (modelo, estados, dependencias, parámetros derivados; si el hijo cae el documento queda intacto) y la ventana avisa «Calculando en un proceso aparte…» pasado 1 s sin dejar de repintar; Tampoco cayó con el RL-1 abierto en la ventana real, el visor repintando y 23 cambios de d_eje, r_camara y largo_camara de ±30 % en el mismo proceso, sin ensayo en hijo (evidencias/b48_2026-10-27/b48_ventana.py): 0 caídas, 0 pasos con error. Con 60 pasos o más ningún recálculo corre ya en el proceso de la app, así que una caída del kernel ahí solo mata al hijo; queda sin curar la causa en OpenCascade (no reproducida) y lo que corra en el proceso de la app con menos de 60 pasos o fuera del recálculo (visor, exportar). | nucleo/aislado.py (prevuelo_parametros, prevuelo_cambio, prevuelo_abrir); timeline/documento.py (_prevuelo_parametros, _prevuelo_cambio); io_archivos/proyecto.py (abrir); nucleo/geometria.py (PARALELO, OMNICAD_SIN_PARALELO); timeline/calculo_aislado.py; tests/test_b48_prevuelo.py; tests/test_b48_calculo_aislado.py; tests/test_b48_prevuelo_ui.py; tests/test_b48_crash.py | 2026-10-27 |

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

### B-108 · La reasignación de un cuerpo posterior a una unión rompe el movimiento rígido

**Gravedad:** alta. **Entorno:** OmniCAD 0.1.4, Windows, API sin ventana y MCP en vivo con OpenCode. **Estado:** reproducido 2/2 en cada vía.

**Qué hice:** creé `Padre` con `Base`, `Tubo` y una mitad de `Tubo` generada por `split_body`; luego `create_as_built_joint` de revolución `Giro` sobre `Base`. Después creé `Pin`, reasigné ambas mitades de tubo y `Pin` a `Hijo` y agregué `create_as_built_joint` de revolución `Elevacion` con `component2="Padre"`. Finalmente ejecuté `drive_joint` con `{"joint":"Giro","rotation":10}`. Las llamadas y argumentos completos están en `evidencias/grove_2026-10-28/repro_reasignacion_giro.py`; modelo original en `evidencias/grove_2026-10-28/interferencia_giro_10.omnicad`.

**Esperado:** la distancia entre la mitad dividida y `Pin`, dos cuerpos del mismo componente, permanece en 11,64 mm durante el giro rígido. **Obtenido:** 11,64 mm a 0° y 0 mm a 10°; `check_interference` detecta volumen común 10,3536 mm³. La misma secuencia sin asignar inicialmente el tubo a `Padre` conserva 11,64 mm y no produce interferencias en ambas corridas. La aplicación no informa error; el análisis y la medida concuerdan.

**Causa:** sin analizar; la reasignación observada ocurre en `OpComponente.ejecutar` y el movimiento en `_mover_componentes`, pero no se demostró aún el mecanismo exacto. **Esquive:** no incorporar los cuerpos de la pluma al componente padre antes de crear el componente hijo. **Prueba propuesta:** conservar la distancia y ausencia de interferencia tras girar el padre, con y sin reasignación y con cuerpos divididos; repetir tras guardar y reabrir.

### B-48 · Crash nativo OCCT (0xc0000005) al recalcular parámetros a 148 pasos

**Mitigado 2026-10-20** (`agente/b48`): no se reprodujo en 18 min; la caída de un hijo aislado vuelve como `TareaAislada`. Sigue Parcial. **Crash nativo durante la tortura de parámetros** (±30 % a 148 pasos): APPCRASH de `pythonw.exe`, excepción 0xc0000005 en `TKernel-….dll` (OCCT 8.0.1) offset 0x78bed, 09:11:23; el puente murió a mitad de llamada (`BRIDGE_ERROR WinError 10054`). El autoguardado (receta sin caché, 18 s antes) permitió recuperar todo. Evento completo en `crash2_evento_completo.txt`.

kernel OCCT vía cadquery_ocp; recálculo

Reproducido (firma de Windows): no se puede curar desde la app; queda la protección por autoguardado

Crítico

**2026-10-27 (agente nocturno)**: se armó una tortura sintética de 141 pasos y 46 cuerpos (booleanas, empalmes, chaflanes, patrones y simetrías; `evidencias/b48_2026-10-27/`) y se corrieron 300 rondas de 4 cambios ±30 % cada una en procesos aparte con faulthandler: 0 caídas y 0 pasos con error; 60 rondas más con `OMNICAD_SIN_PARALELO=1` tampoco cayeron (9,98 s/ronda contra 9,23 s con paralelismo: apagarlo cuesta ~8 %). El motor RL-1 real, con el estado mixto del crash original, tampoco cayó en 3 rondas (abrir 78-85 s; r_camara/largo_camara ~105-109 s por recálculo; d_eje ~21 s). El paralelismo no es la causa demostrable; queda el interruptor `OMNICAD_SIN_PARALELO` para diagnosticar. Se extendió el prevuelo aislado a `reemplazar`, `suprimir` y `eliminar` pasos y a `abrir` archivos de 60 pasos o más (el RL-1: 155,6 s con prevuelo contra ~80 s sin él); si el hijo cae, el documento no se toca y sale un `ErrorDocumento`/`ErrorProyecto` claro. Segunda ronda (2026-10-27): el padre adopta el cálculo del hijo (`timeline/calculo_aislado.py`: grafo + BREP, sin pickle) en vez de repetirlo con el kernel; deshacer, rehacer, mover paso, mover marcador y configuraciones también calculan en el hijo; la ventana avisa «Calculando…» pasado 1 s. Sigue Parcial porque la caída nativa no se reprodujo ni curó.
