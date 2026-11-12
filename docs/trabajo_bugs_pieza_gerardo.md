# Bugs de la pieza de Gerardo

Trabajo de prioridad 1 pedido por Gerardo el 2026-11-11. Arranca con el cupo semanal nuevo. El estado vive en `docs/seguimiento/`; cuando el coordinador cierra el trabajo, borra este documento y su fila de «Prompts guardados».

## Prompt para el agente

Modelo sugerido: Opus 5, esfuerzo alto (geometría y kernel).

```text
Invocá con la herramienta Skill, en este orden: fable-method, ponytail, plan-then-do, tool-calling-guard,
verify-before-commit (y omnicad-test si probás la ventana). Antes de cerrar cada ítem: ponytail-review, y pegá su
salida real en el informe.

Sos una sesión de ejecución de OmniCAD (D:\PROGRAMA, leé AGENTS.md y CLAUDE.md). Tarea: arreglar, de a uno, los bugs
que Gerardo encontró usando su pieza real. Orden: B-308, B-306 (resto), B-311, B-307, B-310 (resto: la previa con
franjas con +0,1 mm). Cada fila está en docs/seguimiento/bugs.md con lo que queda y la evidencia.

Pieza: D:\DISEÑOS BLENDER\01_EN_PROCESO\soporte-papel-bano\soporte_papel_v1_cama.omnicad. NO se modifica: copiala a
una carpeta temporal y trabajá sobre la copia. Registro de uso de Gerardo con los pasos: evidencias/registro_2026-11-11.md.

Por ítem: `bash scripts/worktree_item.sh crear <ID>` (B-308 ya tiene worktree D:/PROGRAMA-B-308, rama item/B-308 en
c632089, WIP: falta tests_afectados; seguí desde ahí). Antes de tocar código, leé el artículo de Fusion con
`clon/.venv/Scripts/python.exe scripts/fusion_docs.py buscar <palabras>` (docs/fusion_docs/). Test que falla sin el
arreglo y pasa con él; `ruff check .` limpio; desde clon/, `../scripts/tests_afectados.py --correr`; prueba de humo
si tocás la UI. Commit en la rama del ítem (no en main), fila de bugs.md borrada (o Parcial con lo que queda) y
entrada en el Registro de PROJECT_LOG.md. Un ítem cerrado antes del siguiente. Avisá al coordinador al cerrar cada uno.

Límites: como mucho un pytest a la vez y siempre con scripts/turno.py. Si quedan menos de 2 GB libres de RAM,
pará y avisá. Al 60 % de contexto, nota de traspaso en PROJECT_LOG.md y avisá. IDs nuevos: desde B-326.
```
