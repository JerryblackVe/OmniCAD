# P-137 flechas del manipulador (cierra antes P-136)

Trabajo de prioridad 1 pedido por Gerardo el 2026-11-11. Arranca con el cupo semanal nuevo. El estado vive en `docs/seguimiento/`; cuando el coordinador cierra el trabajo, borra este documento y su fila de «Prompts guardados».

## Prompt para el agente

Modelo sugerido: Sonnet 5, esfuerzo medio (UI).

```text
Invocá con la herramienta Skill, en este orden: fable-method, ponytail, plan-then-do, tool-calling-guard,
verify-before-commit, omnicad-test. Antes de cerrar: ponytail-review, y pegá su salida real en el informe.

Sos una sesión de ejecución de OmniCAD (D:\PROGRAMA, leé AGENTS.md y CLAUDE.md). Trabajás en el worktree
D:/PROGRAMA-P-136 (rama item/P-136), que tiene sin commitear el trabajo de Sol para P-136 (distancias del
manipulador en 0 mm; 12 archivos, toca la UI; fila Parcial en docs/seguimiento/mejoras.md).

Paso 1, cerrar P-136: revisá el diff, corré su test con y sin el cambio, `ruff check .`, desde clon/
`../scripts/tests_afectados.py --correr --desde 345d230` y la prueba de humo. Arreglá lo que falle y commiteá en la rama.

Paso 2, P-137 (fila en docs/seguimiento/mejoras.md, pedido de Gerardo con captura): flechas del manipulador que
siempre se ven — color que contraste con la selección y el fondo, con borde o sombra; dibujadas encima y de tamaño
constante en pantalla; salen hacia afuera de la superficie y se acomodan si la vista las deja de punta; el cuadro del
valor no las tapa. Antes, mirá cómo lo hace Fusion: `clon/.venv/Scripts/python.exe scripts/fusion_docs.py buscar
manipulator` y `... buscar offset face` (docs/fusion_docs/, con imágenes). Probá como usuario (CLAUDE.md, «toda prueba
se hace como un usuario humano»): Desfase sobre un cilindro, Extruir y Pulsar/tirar, con capturas que mirás de verdad,
en ventana chica (1024x640) también. Test, ruff, tests_afectados y humo; commit en la rama; fila borrada o Parcial;
entrada en PROJECT_LOG.md. Avisá al coordinador.

Límites: pytest y humo de a uno, siempre con scripts/turno.py. Menos de 2 GB libres de RAM: pará y avisá. Al 60 % de
contexto, nota de traspaso y avisá.
```
