# Agenda

Tareas que Gerardo programa para una fecha: revisiones, auditorías, pruebas o trabajos que quiere hacer en un momento
dado. **Solo las agrega Gerardo** (las pide en el chat y el coordinador anota la fila). Al hacerse, la fila se borra y se
anota en el Registro de `PROJECT_LOG.md`. La página de seguimiento la muestra en «Agenda».

`Para cuándo`: fecha `AAAA-MM-DD`, o «A definir» si todavía no tiene. El coordinador la mira al empezar cada sesión y
avisa lo que vence ese día o ya venció.

| ID | Tarea | Para cuándo | Pedido | Estado |
|---|---|---|---|---|
| AG-2 | [2.º] Auditoría y reparación de las herramientas 3D (Agujero a Volumen de fluido) contra Fusion 360; prompt en `docs/auditoria_herramientas_3d.md` (con el anexo de ROSCAS primero) | A definir | 2026-11-07 | Programada |
| AG-3 | [6.º] Auditoría, reparación y mejora del espacio RENDERIZAR contra Fusion 360 (primero la interfaz corrupta); prompt en `docs/auditoria_renderizar.md` | A definir | 2026-11-07 | Programada |
| AG-4 | [3.º] Auditoría, reparación y paridad de las 27 herramientas de MODIFICAR (Pulsar/tirar a Lista de materiales) en todos los espacios contra Fusion 360; prompt en `docs/auditoria_modificar.md` | A definir | 2026-11-07 | Programada |
| AG-5 | [5.º] Auditoría, reparación y paridad del sistema ENSAMBLAR (componentes, uniones, solver, movimiento, contactos) contra Fusion 360; prompt en `docs/auditoria_ensamblar.md` | A definir | 2026-11-07 | Programada |
| AG-6 | [4.º] Auditoría, reparación y paridad de la sección INSERTAR (Calcomanía a Insertar derivación) en todos los espacios contra Fusion 360; prompt en `docs/auditoria_insertar.md` | A definir | 2026-11-07 | Programada |
| AG-7 | [1.º] Auditoría, reparación y paridad del sistema CONSTRUIR (SCU, planos, ejes y puntos de construcción) en todos los espacios contra Fusion 360; prompt en `docs/auditoria_construir.md` | A definir | 2026-11-07 | Programada |

## Orden y reparto de las auditorías

Se corren de a una, en este orden; la siguiente arranca cuando la anterior quedó cerrada y commiteada. Cada herramienta
tiene una sola auditoría dueña; las demás solo la usan en sus pruebas combinadas (el detalle está en el «AJUSTE DEL
COORDINADOR» al principio de cada prompt).

| Orden | Auditoría | Dueña además de su lista | Le saca a otra |
|---|---|---|---|
| 1 | CONSTRUIR (AG-7) | Referencias persistentes a caras, aristas y vértices | — |
| 2 | Herramientas 3D (AG-2) | Patrón, Simetría, Engrosar | — |
| 3 | MODIFICAR (AG-4) | Mover/copiar, Alinear, Apoyar en el plano | Aspecto → AG-3; Lista de materiales → AG-5 |
| 4 | INSERTAR (AG-6) | Calcomanía, Lienzo | Duplicar con uniones e Insertar componente → AG-5 |
| 5 | ENSAMBLAR (AG-5) | Duplicar con uniones, Insertar componente, Lista de materiales, ítems de `brechas_ensamblar.md` | — |
| 6 | RENDERIZAR (AG-3) | Aspecto, bug B-240 | — |

AG-1 («revisión solo del Boceto») se borró el 2026-11-08: la cubren la auditoría de restricciones (cerrada) y la de
CREAR y MODIFICAR del boceto (en curso); el boceto no tiene otras pestañas.
