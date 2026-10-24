# Bugs

Algo que falla, da un resultado malo o un mensaje engañoso. Método y columnas: [README](README.md).

Solo lo que falta resolver: al resolverse, la fila se borra. Verificado contra el código el 2026-10-23. Total 12: Abierto 7 · Parcial 4 · Bloqueado 1.

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
| B-96 | Curva de fusión G2 con un arco deforma el arco | Abierto | Media | Con arco r=10 y línea, el arco queda con curvatura 0,0930 (r≈10,75): los polos internos salen colineales (curvatura 0 en la unión) y el solver mueve la curva original. | omnicad/restricciones/boceto.py:2745-2749 (`curva_fusion`) | 2026-10-23 |
| B-98 | Desfase hacia adentro devuelve contornos invertidos o de largo 0 | Abierto | Media | Rectángulo 20×10: `-5` da líneas de largo 0 y `-6` un contorno invertido, con OK. Solo se controla el radio de arcos y círculos. Fallar si un segmento se invierte o llega a 0. | omnicad/restricciones/boceto.py:2331-2343 (`desfase`) | 2026-10-23 |
| B-99 | Proyectar un cuerpo cilíndrico deja círculos duplicados | Abierto | Baja | Quedan 2 círculos idénticos superpuestos; las líneas coincidentes sí se deduplican. | omnicad/restricciones/boceto.py:1425-1436 | 2026-10-23 |
| B-100 | Simetría de arcos no refleja los extremos | Abierto | Media | 2 arcos con eje: dof 14 → 11 (debía ser 9); los círculos sí dan 7. El solver solo empareja centros. | omnicad/restricciones/solver.py:430 | 2026-10-23 |
| B-101 | El solver da falsos conflictos con geometría grande | Abierto | Alta | Dos líneas con cota de ángulo 60° y largo ≥ 2e4 mm dan `SKETCH_OVERCONSTRAINED` (error 1e-5) y dof 8 en vez de 7. Una cadena rígida de 160 o más líneas H/V/igual rechaza un arrastre de 50 mm. Causa: Jacobiano por diferencias finitas con h=1e-7 y tolerancia absoluta 1e-6. | omnicad/restricciones/solver.py:28,466 | 2026-10-23 |
| B-102 | `auto_constrain` deja grados de libertad sin cerrar | Abierto | Media | Salta las distancias de valor 0: `draw_point(0,5)` más `auto_constrain` queda con dof 1; igual un arco con extremo en x=0 o una cónica con punto en y=0. | omnicad/restricciones/solver.py:838,865 | 2026-10-23 |
| B-103 | `auto_constrain` tarda minutos con boceto grande y bloquea la ventana | Abierto | Alta | Cada candidato recalcula el Jacobiano de todo el boceto: 120 entidades 4,7 s; 260 28 s; 440 114 s; 600 líneas más de 590 s. Fusion limita a 250. Calcular por bloques y poner un tope. | omnicad/restricciones/solver.py:783 | 2026-10-23 |

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

