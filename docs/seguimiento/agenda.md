# Agenda

Tareas que Gerardo programa para una fecha: revisiones, auditorías, pruebas o trabajos que quiere hacer en un momento
dado. **Solo las agrega Gerardo** (las pide en el chat y el coordinador anota la fila). Al hacerse, la fila se borra y se
anota en el Registro de `PROJECT_LOG.md`. La página de seguimiento la muestra en «Agenda».

`Para cuándo`: fecha `AAAA-MM-DD`, o «A definir» si todavía no tiene. El coordinador la mira al empezar cada sesión y
avisa lo que vence ese día o ya venció.

| ID | Tarea | Para cuándo | Pedido | Estado |
|---|---|---|---|---|
| AG-18 | PRIMERO: actualizar Claude Code en la VPS a 2.1.327 o más nuevo (cortes de SSH por reuso de PID, fuga de cupo de subagentes); entre ítems, sin tests corriendo; rige en el reemplazo del coordinador | 2026-11-19 | 2026-11-18 | Programada |
| AG-21 | Terminó la promo de GLM 5.3 (OpenCode Go): sacar `opencode-go/glm-5.3` del primer lugar de `MODELOS` en `scripts/vigia_opencode.sh` (vuelve después de `hy4-flash-free`, antes de kimi) y de la fila «0» de la tabla de docs/coordinacion.md | 2026-11-23 | Chat maestro (Gerardo), 19/11 | Programada |
| AG-2 | [3.º] Auditoría y reparación de las herramientas 3D (Agujero a Volumen de fluido) contra Fusion 360; prompt en `docs/auditoria_herramientas_3d.md` (con el anexo de ROSCAS primero) | A definir | 2026-11-07 | Programada |
| AG-3 | [7.º] Auditoría, reparación y mejora del espacio RENDERIZAR contra Fusion 360 (primero la interfaz corrupta); prompt en `docs/auditoria_renderizar.md` | A definir | 2026-11-07 | Programada |
| AG-4 | [4.º] Auditoría, reparación y paridad de las 27 herramientas de MODIFICAR (Pulsar/tirar a Lista de materiales) en todos los espacios contra Fusion 360; prompt en `docs/auditoria_modificar.md` | A definir | 2026-11-07 | Programada |
| AG-5 | [6.º] Auditoría, reparación y paridad del sistema ENSAMBLAR (componentes, uniones, solver, movimiento, contactos) contra Fusion 360; prompt en `docs/auditoria_ensamblar.md` | A definir | 2026-11-07 | Programada |
| AG-6 | [5.º] Auditoría, reparación y paridad de la sección INSERTAR (Calcomanía a Insertar derivación) en todos los espacios contra Fusion 360; prompt en `docs/auditoria_insertar.md` | A definir | 2026-11-07 | Programada |
| AG-7 | [2.º] Auditoría, reparación y paridad del sistema CONSTRUIR (SCU, planos, ejes y puntos de construcción) en todos los espacios contra Fusion 360; prompt en `docs/auditoria_construir.md` | A definir | 2026-11-07 | Programada |
| AG-9 | [8.º] Rediseño de «Apariencia y materiales» (color, aspecto, material físico, texturas PBR, colocación, «En uso»): primero una maqueta de la interfaz que Gerardo aprueba, después las fases; no es prioritario; prompt en `docs/apariencia_materiales.md` | A definir | 2026-11-09 | Programada |
| AG-10 | Auditoría completa de Sólido › Crear con Fusion abierto, herramienta por herramienta (clics, asas, topes, campos, previa, velocidad). Insumo: los reportes de la PC del 2026-11-12 en `evidencias/reportes_pc/`, empezando por la Bobina (`2026-11-12_bobina/`: centro sin elegir y bobina corrida, valor y previa que no coinciden, eje con Plano XZ, congelamientos de 0,8–4 s, asas de Ángulo y círculo base, las 4 secciones) | A definir | 2026-11-12 | Programada |
| AG-11 | Publicar OmniCAD v0.3.0 beta (pre-release en GitHub): antes, main subido con el cierre completo verde. Etiqueta v0.3.0 (en origin no hay otra), «Instaladores» una sola vez, notas con lo nuevo desde v0.2.0 por tema, fallas conocidas en 1 renglón y cómo reportar (botón «Reportar») | 2026-11-17 | 2026-11-16 (vía el chat maestro; espera el OK directo de Gerardo al coordinador) | Programada |
| AG-12 | Revisar las ~59 carpetas de trabajo con cambios sin pasar a main (`git worktree list`): integrar lo útil, archivar lo viejo. La limpieza automática de las vacías corre los domingos (`scripts/limpiar_worktrees.sh`). | 2026-11-19 | Gerardo, 17/11 | Pendiente |
| AG-13 | Al reiniciar el cupo: cada sesión cierra primero sus bugs en «Parcial» (36 de 84 el 17/11); no toma nada nuevo hasta que queden 10 o menos. E6, solo velocidad de prioridad 1. | 2026-11-19 | Gerardo, 17/11 | Pendiente |
| AG-14 | Revisar con Gerardo (1 hora) lo que prepararon los gratis en `docs/seguimiento/preparado/`: `reglas_cortas.md` (bajar las reglas de 68 KB a 20 KB) y `triage_viejos.md` (37 bugs anteriores a B-500: arreglar, cerrar o pasar a después). Decidir y aplicar. | 2026-11-19 | Gerardo, 17/11 | Pendiente |
| AG-15 | Cada lunes: E11 modela una pieza real en OmniCAD y la compara con Fusion (pedir antes la PC libre); las fallas van a `evidencias/reportes_pc/`. Al hacerse, la fila pasa al lunes siguiente. | 2026-11-23 | Gerardo, 17/11 | Pendiente |
| AG-16 | Medir qué papeleo se repite (de 1.570 commits de la semana, unos 800 no tocan código de la app) y pasar lo mecánico a un script o a los gratis. | 2026-11-20 | Gerardo, 17/11 | Pendiente |

## Orden y reparto de las auditorías

Se corren de a una, en este orden; la siguiente arranca cuando la anterior quedó cerrada y commiteada. Cada herramienta
tiene una sola auditoría dueña; las demás solo la usan en sus pruebas combinadas (el detalle está en el «AJUSTE DEL
COORDINADOR» al principio de cada prompt).

| Orden | Auditoría | Dueña además de su lista | Le saca a otra |
|---|---|---|---|
| 1 | Fluidez: [plan_fluidez.md](../plan_fluidez.md), filas FL-* (reemplaza a AG-8) | P-99 y las filas de rendimiento sin dueña | — |
| 2 | CONSTRUIR (AG-7) | Referencias persistentes a caras, aristas y vértices | — |
| 3 | Herramientas 3D (AG-2) | Patrón, Simetría, Engrosar | — |
| 4 | MODIFICAR (AG-4) | Mover/copiar, Alinear, Apoyar en el plano | Aspecto → AG-9; Lista de materiales → AG-5 |
| 5 | INSERTAR (AG-6) | Calcomanía, Lienzo | Duplicar con uniones e Insertar componente → AG-5 |
| 6 | ENSAMBLAR (AG-5) | Duplicar con uniones, Insertar componente, Lista de materiales, ítems de `brechas_ensamblar.md` | — |
| 7 | RENDERIZAR (AG-3) | Bug B-240 | Aspecto → AG-9 (AG-3 solo verifica que el render use sus asignaciones) |
| 8 | Apariencia y materiales (AG-9) | Aspecto (biblioteca, asignación, edición), material físico, texturas | — |

AG-1 («revisión solo del Boceto») se borró el 2026-11-08: la cubren la auditoría de restricciones (cerrada) y la de
CREAR y MODIFICAR del boceto (en curso); el boceto no tiene otras pestañas.
| AG-22 | Verificar los commits de ChatGPT sin verificar en la rama `trabajo/base-chatgpt-2026-11-24` (lote 3: e6c9d887 B-803, f76c9348 B-771, c899926a B-769, a3ee0a25 B-648/B-553, a2c4e03 B-552, 2d6b6077 B-550; sus filas siguen en bugs.md). Por ítem: tests fallan sin el arreglo y pasan con él, ruff, ponytail-review; después cerrar filas y refrescar la página. Sin gastar cupo antes. | 2026-11-26 | Gerardo, 24/11 (poco cupo semanal) | Pendiente |
