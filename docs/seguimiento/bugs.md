# Bugs

Algo que falla, da un resultado malo o un mensaje engañoso. Método y columnas: [README](README.md).

Solo lo que falta resolver: al resolverse, la fila se borra. Verificado contra el código el 2026-10-23 (Superficie y Sólido, también en la ventana real: 2026-10-24; revisión de B-39 y regresiones de B-48: 2026-10-27). Total 9: Abierto 4 · Parcial 3 · Bloqueado 1 · Sin verificar 1.

## Abiertos y parciales

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| B-122 | Las clases de las tablas de Fusion no modelan el Ø mayor del agujero ni el Ø menor del eje | Abierto | Media | `desfases_rosca` solo da flancos y menor del agujero: el Ø mayor sale de `diametro/2 + desfase`. Tr12x3 7H: la tabla dice 12,5 y se modela 12,15; 7e: Ø menor 8,3175 y se modela 8,803. Afecta a todo tipo de `tablas_rosca.CLASES`. Falta confirmar en Fusion real (el MCP no conecta) qué diámetro usa la rosca modelada y pasarlo a `_surco_rosca` | clon/omnicad/nucleo/tolerancias.py:333 | 2026-11-01 |
| B-121 | Volver a resolver un boceto con una tangente general (spline) corre la geometría un poco cada vez | Abierto | Media | En `_tangencia` el contacto arranca de una muestra de 96 puntos, no del contacto exacto: el solver no parte de la solución y reparte el error entre la curva y el parámetro. Medido 2026-10-31 con arco de radio 10 y spline ya tangentes: 10,0000 → 10,0091 → 10,0175 → 10,0254 → 10,0326 por pasada. Arreglarlo cambia lo que dan las recetas guardadas con esas tangentes: decidir antes de tocar el solver (idea: afinar los dos parámetros con la geometría quieta y usarlos solo si el residuo ya es cero) | `tests/test_restricciones_matematica.py::test_tangente_con_el_comando_no_cambia_el_radio_del_arco`; `omnicad/restricciones/solver.py` (`_tangencia`) | 2026-10-31 |
| B-119 | Proyectar un cuerpo curvo visto de costado no da su silueta | Abierto | Alta | Fusion promete perfiles cerrados con el filtro Cuerpos («closed profiles»), pero `proyectar_forma` proyecta solo aristas: un cilindro R14 sobre XZ da 3 líneas abiertas (falta el lado opuesto a la costura) y 0 perfiles; una esfera da una línea o un arco. Hace falta sumar la silueta (HLR de `nucleo/dibujo.py`), con cuidado: un vínculo a un cuerpo la recalcularía en cada paso del timeline, y sobre roscas tarda más de 90 s. Mirado de frente anda bien (cilindro sobre XY: 1 círculo, 1 perfil). | omnicad/nucleo/perfiles.py (`proyectar_forma`); tests/test_proyectar_tarjeta.py::test_cambiar_de_filtro_saca_lo_incompatible_y_lo_dice | 2026-10-31 |
| B-118 | Un corte sin objetivo elegido también corta los cuerpos ocultos | Abierto | Media | Con Objetos vacío se cortan todos los sólidos que toca, también los ocultos. Extruir (B-117) y `operation="auto"` ya ignoran lo oculto al decidir, pero el paso no: falta decidir si la herramienta se queda con los visibles al crear el paso, como la extensión Todo de Fusion (`Extrude reference`: «all visible bodies»). | timeline/operaciones.py:345 | 2026-10-31 |
| B-108 | Un cuerpo reasignado después de una unión se mueve mal al girar el componente anterior | Abierto | Alta | Al girar el padre, un cuerpo del hijo se desplaza respecto de otro del mismo hijo; preservar la posición relativa al reasignar componentes. | omnicad/timeline/ops_ensamblar.py:228-240; omnicad/timeline/ops_ensamblar.py:257-270 | 2026-10-28 |
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
