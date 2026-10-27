# Bugs

Algo que falla, da un resultado malo o un mensaje engañoso. Método y columnas: [README](README.md).

Solo lo que falta resolver: al resolverse, la fila se borra. Verificado contra el código el 2026-10-23 (Superficie y Sólido, también en la ventana real: 2026-10-24). Total 13: Abierto 8 · Parcial 4 · Bloqueado 1.

## Abiertos y parciales

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| P-12c | Fuente de novedades de Fusion (la ayuda es un shell JS sin titulares) | Parcial | Baja | Autodesk le responde 403 a los scripts: ahora se lee la última copia de archive.org del blog «What's New» (hoy del 2026-05-16, 5 meses atrás) y el informe lo avisa; falta una fuente al día que no bloquee (feed o API) o seguir revisando a mano. | scripts/novedades.py (`bajar`, `COPIAS`); tests/test_novedades.py::test_fusion_apunta_al_blog_y_cae_a_archive_org_si_autodesk_bloquea | 2026-10-20 |
| P-1c | Wayland nativo: menús emergentes se cierran solos | Bloqueado | Alta | Necesita PC con Linux nativo (ver P-1b): el fallo solo aparece con Wayland y esta PC es Windows, así que no se pudo reproducir ni probar un arreglo; hoy se fuerza xcb y no molesta. | omnicad/ui/__init__.py:11-19 | 2026-10-20 |
| P-11j | Cuerpos «sin ubicar» de XOX (3) que quizá Fusion no tiene | Parcial | Alta | Sherpa resuelto (2026-10-21): comparado con Fusion, no tiene los 2 cuerpos (1593 y 952 mm³) y todos sus componentes con cuerpos están emparejados; ahora se descartan los bloques sin dueño cuando ningún componente de la escena queda sin bloque. Queda XOX: 3 componentes de la escena sin bloque y 3 bloques sin dueño (152,9; 494,8 y 4365,4 mm³): no se pueden descartar sin ver Fusion, y la versión en la nube (v35, 202 componentes) no es la del .f3z local (72 cuerpos): hace falta abrir en Fusion ese mismo archivo. | omnicad/io_archivos/f3d_escena.py (huerfanos); tests/test_p11a_f3d_instancias.py; tests/test_f3d_reales.py | 2026-10-21 |
| B-39 | join con herramienta enterrada deja arista libre y cuerpo no estanco | Parcial | Muy alta | El caso original (cilindro r2,5 en la carcasa, arista libre en (27, 0, 129,5)) sigue sin reproducirse: 4 000 casos de fuzzing (6 herramientas × 4 bases, tangencias de 0 a 1e-3 mm, de 1 a 4 uniones) no dieron ninguna arista libre con la herramienta enterrada. Sí dieron fallos silenciosos del kernel con contacto casi tangente (unión que devolvía solo la herramienta, un toro que «no tocaba» la pared, unión vacía por 1e-6 mm de solape): `geo.booleano` ahora verifica el resultado y reintenta o rechaza con error claro (graves 2,5 % → 0,6 %). Queda ese 0,6 %: esfera o toro casi tangentes que dejan aristas no manifold o un sólido inválido que OCCT no cura, y uniones con superficies libres, cuyo volumen no se puede verificar. Siguiente paso: P-32 (probar el motor omnikernel como segunda opinión). | nucleo/geometria.py (`booleano`, `_problema_booleana`, `_REINTENTOS_BOOLEANA`, `_union_general_creible`); scripts/fuzz_b39.py; tests/test_b39_enterrada.py; tests/test_b39_fuzz.py; timeline/operaciones.py:349 y :1004 (aviso post-unión); `_quitar_cables_colgados` (B-28) | 2026-10-21 |
| B-48 | Crash nativo OCCT (0xc0000005) al recalcular parámetros a 148 pasos | Parcial | Muy alta | La causa en OCCT sigue sin reproducirse ni curarse. El cambio de parámetros en documentos de 60 pasos o más ya se ensaya antes en un proceso aparte (si el kernel cae, no se aplica y la app sigue); no cubre editar/suprimir pasos ni abrir archivos. | nucleo/aislado.py (`correr_json`, `UMBRAL_PREVUELO_PARAMETROS`); timeline/documento.py `_prevuelo_parametros`; tests/test_b48_prevuelo.py; tests/test_b48_crash.py | 2026-10-20 |

## Boceto (auditoría contra Fusion, 2026-10-23)

Cada fila se reprodujo con una prueba real (scripts de la auditoría, no incluidos en el repo). Plan: [plan_boceto.md](../plan_boceto.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|

## Superficie (auditoría contra Fusion, 2026-10-24)

Cada fila salió de comparar la pestaña SUPERFICIE con los artículos de la ayuda de Fusion (sección Fusion-Patch de `docs/fusion_docs/`) y de probar las 14 herramientas por MCP/CLI. Los bugs se reprodujeron; los scripts de prueba (`sonda*.py`) están en `evidencias/superficie_2026-10-24/`, fuera de git.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| SUP-1 | Parche G1 y G2 sobre un contorno de cuerpo falla con error crudo del kernel | Abierto | Alta | G1 sobre la boca de una caja de superficies da «Geom_RectangularTrimmedSurface::V1==V2». G2 da siempre «BRepFill : The continuity is not G0 G1 or G2», también sobre el borde de un cilindro donde G1 sí anda. El usuario ve «Error inesperado». Hay que cubrir G2 y los vecinos planos, o traducir el error. | omnicad/nucleo/superficies.py:494-509; tests/test_superficies.py::test_parche_plano_relleno_y_g1 (solo cubre G1 curvo con un punto interior) | 2026-10-24 |
| SUP-2 | Dividir cuerpo no funciona sobre un cuerpo de superficie | Abierto | Media | `split_body` con un plano que corta por la mitad un tubo de superficie (z=10 de 0 a 20, con o sin extend) responde «La herramienta no divide el cuerpo». Fusion parte una superficie en dos cuerpos de superficie. | omnicad/nucleo/solidos_modificar.py:1138 (`geo.solidos` descarta lo que no es sólido) | 2026-10-24 |
| SUP-3 | Barrido de superficie por una ruta con esquina viva sale deformado y sin aviso | Abierto | Media | Perfil circular r2 por dos líneas en L de 20 mm: área 412,67 en vez de 502,65 (−18 %). El tramo horizontal queda aplastado (el perfil no gira en la esquina: caja z 0 a 20 en vez de 0 a 22). Poner un modo de transición en la esquina o rechazar rutas no tangentes con un error claro; la ayuda de Fusion solo describe el encadenado tangente. El barrido sólido de la misma L sí da 502,65: se puede reusar su método. | omnicad/nucleo/superficies.py:399 (`BRepOffsetAPI_MakePipeShell` sin `SetTransitionMode`) | 2026-10-24 |
| SUP-4 | Solevación de superficie con 3 o más secciones de distinto tipo falla | Abierto | Media | Rectángulo y círculo andan con 2 secciones; 3 círculos o 3 rectángulos andan; pero RCC, CCR, RRC, CRC y RCR responden «El solevado falló en el kernel» (distinta cantidad de aristas por sección). Fusion lo resuelve y la solevación sólida RCC también anda (8413,96 mm³). | omnicad/nucleo/superficies.py:432-467 (`BRepOffsetAPI_ThruSections`) | 2026-10-24 |
| SUP-5 | Destrimar después de Recortar no devuelve nada y no avisa | Abierto | Media | Tubo de superficie de 20 mm recortado con un plano a 10 mm: Destrimar (exteriores, interiores o todos) deja el área en 628,32 en vez de recuperar 1256,64 (la ayuda dice que Untrim extiende las superficies recortadas). Sobre superficies infinitas usa los límites de la cara ya recortada, así que no puede recuperar lo recortado, y no avisa. | omnicad/nucleo/superficies.py:740-777 (`_limites_naturales`) | 2026-10-24 |
| SUP-24 | Previsualizar Reglada tangente o dirección en la ventana deja dañada la superficie de origen: después Recortar falla | Abierto | Alta | En la ventana: Reglada → arista de arriba de un tubo de superficie → Tipo tangente (o dirección) → Cancelar. Después Recortar con un plano que SÍ cruza el tubo responde «La herramienta no corta la superficie»; pasa también si se acepta y se deshace, sigue igual tras recalcular y `trim_surface` por la API también falla. Con tipo normal no pasa, y sin la ventana (previsualizar + API) tampoco. Causa sin confirmar; sospecha: `BRepFill.Face_s(ef, otra)` comparte la arista de origen. | omnicad/nucleo/superficies.py:590; omnicad/ui/comando.py:680 | 2026-10-24 |

## Sólido (auditoría contra Fusion, 2026-10-24)

Cada fila salió de comparar la pestaña SÓLIDO (y PLÁSTICO, CONSTRUIR, INSPECCIONAR, INSERTAR, SELECCIONAR) con los artículos de la ayuda de Fusion (carpeta `fusion-model`) y de probar unas 70 herramientas por API con valores normales, de borde e inválidos. Los bugs se reprodujeron; los scripts (`s*.py`) están en `evidencias/solido_2026-10-24/`, fuera de git. Lo que ya estaba cargado (SC12, SC3, P-25d, P-25f, P-25g2, P-25i, P-25j) no se repite.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|

## Ensamblar (auditoría contra Fusion, 2026-10-25)

Cada fila salió de comparar ENSAMBLAR (uniones, componentes, grupo rígido, vínculos, estudio de movimiento) con los artículos de la ayuda de Fusion (carpeta `fusion-assemble`), de probar unas 60 llamadas por API (`evidencias/ensamble_2026-10-25/a*.py`) y de usar la ventana real como una persona (`scripts/prueba_ui/ensamblar.py`, 224 comprobaciones). Lo que ya estaba cargado (P-25e, P-25e2, SC6, SC7, SC8, SC15, H-4, H-5, H-19, F8, P-6d) no se repite.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| ASM-2 | El vínculo de movimiento acepta relaciones imposibles | Abierto | Media | Se aceptan un vínculo 2→1 sobre uno 1→2, un segundo vínculo sobre el mismo par y la relación 0 (o 1e9, -2 en la ventana): las dos uniones quedan seguidoras una de la otra, `drive_joint` devuelve ok con un aviso y no se mueve nada. Rechazarlo al crear: una unión que ya sigue a otra, ciclo o relación 0. | omnicad/timeline/ops_ensamblar.py:670-693 (`OpVinculoMovimiento.ejecutar` no mira los vínculos anteriores ni el factor) | 2026-10-25 |
| ASM-3 | Borrar un componente con uniones se acepta (o falla sin explicar) | Abierto | Media | Borrar el componente fijo Base (que usa Unión1) responde OK: la unión pasa en silencio a «(raíz)», el cuerpo queda suelto y ya no hay nada fijo. Borrar el componente Eje falla con OPERATION_FAILED «El componente 1 tiene que ser un componente (no la raíz)…» sin nombrar qué lo usa. Esperado: FEATURE_IN_USE «la usan Unión1, Unión2», como al borrar el paso del cuerpo. | omnicad/timeline/ops_ensamblar.py:474-475 (`OpUnion.dependencias` mira los cuerpos, no el componente) | 2026-10-25 |

## Detalle de lo abierto

Ficha original de cada bug abierto o parcial (del PROJECT_LOG al 2026-10-20); se borra junto con su fila. La tabla
de arriba manda sobre este texto.

### B-39 · join con herramienta enterrada deja arista libre y cuerpo no estanco

`boolean_operation join` con herramienta 100 % enterrada (cilindro r2,5 en la carcasa): suma 0 (correcto) pero deja una arista libre en (27, 0, 129,5); cuerpo no estanco. Determinista: sobrevive a recalcular todo. Solo se cura borrando los pasos.

`boolean_operation`

Corregido el 2026-10-14 por el mismo aviso post-join de cuerpo partido/no estanco. Repro de la arista queda sin cura (kernel)

Reproducido

Crítico

### B-48 · Crash nativo OCCT (0xc0000005) al recalcular parámetros a 148 pasos

**Mitigado 2026-10-20** (`agente/b48`): no se reprodujo en 18 min; la caída de un hijo aislado vuelve como `TareaAislada`. Sigue abierto. **Crash nativo durante la tortura de parámetros** (±30 % a 148 pasos): APPCRASH de `pythonw.exe`, excepción 0xc0000005 en `TKernel-….dll` (OCCT 8.0.1) offset 0x78bed, 09:11:23; el puente murió a mitad de llamada (`BRIDGE_ERROR WinError 10054`). El autoguardado (receta sin caché, 18 s antes) permitió recuperar todo. Evento completo en `crash2_evento_completo.txt`.

kernel OCCT vía cadquery_ocp; recálculo

Reproducido (firma de Windows): no se puede curar desde la app; queda la protección por autoguardado

Crítico

### SUP-1 · Parche G1 y G2 sobre un contorno de cuerpo falla con error crudo del kernel

Cómo reproducir: `create_box 20x20x10` → `unstitch_surfaces` → `stitch_surfaces` de 5 caras (queda una boca abierta) → `create_patch boundary={body, edges: ">Z"} continuity=G1`. Obtenido: OPERATION_FAILED «Error inesperado: Geom_RectangularTrimmedSurface::V1==V2». Con `G2`: «BRepFill : The continuity is not G0 G1 or G2». El mismo G2 falla sobre el borde superior de un tubo extruido de un círculo r10, donde G0 y G1 sí funcionan. Esquive: G0 y mezclar a mano. Prueba propuesta: parche G1 y G2 sobre la caja de 5 caras y sobre el tubo, con área y `es_valida`.

Evidencia: `evidencias/superficie_2026-10-24/` (sonda1 a sonda14).

### SUP-2 · Dividir cuerpo no funciona sobre un cuerpo de superficie

Cómo reproducir: círculo r10 en XY → `create_surface_extrude distance=20` → plano de construcción z=10 → `split_body body=<tubo> tool=<plano>` (también con `extend=true`). Esperado: dos cuerpos de superficie de 628,32. Obtenido: OPERATION_FAILED «La herramienta no divide el cuerpo (probá extenderla)». `split_face` con el mismo plano sí parte la cara (2 caras). Causa probable: `dividir_cuerpo` solo cuenta sólidos. Prueba propuesta: dividir un tubo y una caja abierta; 2 cuerpos y áreas que sumen el original.

Evidencia: `evidencias/superficie_2026-10-24/` (sonda1 a sonda14).

### SUP-3 · Barrido de superficie por una ruta con esquina viva sale deformado y sin aviso

Cómo reproducir: círculo r2 en XY; boceto en XZ con las líneas (0,0)-(0,20) y (0,20)-(20,20); `create_surface_sweep profiles=<círculo> path=[las dos líneas]`. Esperado: dos tubos de 251,33 (502,65 en total). Obtenido: 412,67; el segundo tramo suma solo 161,35 (una tira plana: el perfil no rota en la esquina) y la caja termina en z=20. Sin error ni aviso. Prueba propuesta: barrido por un camino en L con el área de los dos tubos, o error explícito.

Evidencia: `evidencias/superficie_2026-10-24/` (sonda1 a sonda14).

### SUP-4 · Solevación de superficie con 3 o más secciones de distinto tipo falla

Cómo reproducir: planos XY a z=0, 20 y 40; secciones rectángulo, círculo, círculo; `create_surface_loft profiles=[S0,S1,S2]`. Obtenido: «El solevado falló en el kernel». De 9 combinaciones, RC, CR, CCC y RRR andan; RCC, CCR, RRC, CRC y RCR fallan. Prueba propuesta: solevar esas combinaciones y chequear área > 0 y `es_valida`.

Evidencia: `evidencias/superficie_2026-10-24/` (sonda1 a sonda14).

### SUP-5 · Destrimar después de Recortar no devuelve nada y no avisa

Cómo reproducir: círculo r10 → `create_surface_extrude distance=20` → plano z=10 → `trim_surface` quitando la parte de arriba (queda 628,32) → `untrim_surface faces={body, faces: all} boundaries=outer|inner|all`. Obtenido: OK y el área sigue en 628,32 las tres veces, sin aviso. Esperado según la ayuda de Fusion: la superficie recortada se extiende. Prueba propuesta: recortar y destrimar un tubo y comprobar el área; si no se puede recuperar, avisarlo.

Evidencia: `evidencias/superficie_2026-10-24/` (sonda1 a sonda14).

### SUP-24 · Previsualizar Reglada tangente o dirección en la ventana deja dañada la superficie de origen: después Recortar falla

Cómo reproducir (ventana real, escena de `evidencias/ui_2026-10-24/escena.py`): círculo r5 → superficie extruida de 20 mm (tubo) → plano de construcción z=10. 1) Recortar con ese plano y clic en el tubo: la vista previa anda (queda la mitad, 314,16). 2) SUPERFICIE › Reglada → elegir la arista circular de arriba → Tipo «Tangente» (o «Dirección») → distancia 5 mm → Cancelar. 3) Repetir el paso 1: «La herramienta no corta la superficie». Con Tipo «Normal» el paso 3 sigue andando.

Qué se comprobó: pasa igual si en el paso 2 se acepta y se deshace; sigue pasando tras `Documento.recalcular(0)`; `trim_surface` por la API (mismos datos) también falla después de la vista previa. En cambio la secuencia solo con API (crear Reglada tangente, deshacer, `trim_surface`) y `Documento.previsualizar` sin ventana NO lo reproducen. El área del tubo (628,32) y su validez no cambian: el daño no se ve a simple vista. Causa sin confirmar; `reglada` arma cada cara con `BRepFill.Face_s(ef, otra)` usando la arista original (superficies.py:590) y es lo primero a mirar (¿deja datos en la arista compartida?). Un intento de pasarle una copia no sirvió de prueba (el segundo documento del mismo proceso ya salió dañado).

Prueba propuesta: tras previsualizar y cancelar una Reglada tangente, Recortar sobre la misma superficie da la misma mitad (314,16) que antes.

Evidencia: `evidencias/ui_2026-10-24/` (`p5_repro.py`, `p6_repro.py`, `p7_repro.py`, `p9_nucleo.py`, `u1_superficie.log`).

### ASM-2 · El vínculo de movimiento acepta relaciones imposibles

Cómo reproducir (API): Eje y Brazo con dos uniones revolute (Unión1 y Unión2); `create_motion_link joint1=Unión1 joint2=Unión2 ratio=2` y luego `create_motion_link joint1=Unión2 joint2=Unión1 ratio=2` → OK. `drive_joint joint=Unión1 rotation=30` → ok con aviso «La unión Unión1 la mueve el vínculo…», valores [0, 0]. También se aceptan un tercer vínculo sobre el mismo par, `ratio=0` (el seguidor queda en 0) y, en la ventana, 1e9 y -2. Esperado: error al crear. Esquive: no repetir uniones en vínculos. Prueba propuesta: en `tests/test_api_ensamble.py`.

Evidencia: `evidencias/ensamble_2026-10-25/a3_profundo.py`, `evidencias/ui_2026-10-25/ensamblar.log`.

### ASM-3 · Borrar un componente con uniones se acepta (o falla sin explicar)

Cómo reproducir (API): escena con Base fija, Eje y Brazo y dos uniones (Eje→Base, Brazo→Eje); `delete_feature feature=<Base>` → OK, y `get_assembly` muestra Unión1 con componente 2 «(raíz)»; deshacer lo trae de vuelta. `delete_feature feature=<Eje>` → OPERATION_FAILED «El componente 1 tiene que ser un componente (no la raíz)…». Esperado: FEATURE_IN_USE nombrando Unión1 y Unión2, como pasa con el paso del cuerpo. Prueba propuesta: en `tests/test_api_ensamble.py`.

Evidencia: `evidencias/ensamble_2026-10-25/a4_borrar.py`.

