# `scripts/probar_todo.py`: todas las pruebas automáticas en un comando

Trabajo de prioridad 1 pedido por Gerardo el 2026-11-11. Arranca con el cupo semanal nuevo. El estado vive en `docs/seguimiento/`; cuando el coordinador cierra el trabajo, borra este documento y su fila de «Prompts guardados».

## Prompt para el agente

Modelo sugerido: Sonnet 5, esfuerzo medio.

```text
Invocá con la herramienta Skill, en este orden: fable-method, ponytail, plan-then-do, tool-calling-guard,
verify-before-commit. Antes de cerrar: ponytail-review, y pegá su salida real en el informe. Antes de editar, leé los
archivos reales que vas a llamar. Corré el test con scripts/turno.py y commiteá en la rama item/probar-todo.

Repo OmniCAD (CAD en Python), estás en el worktree D:/PROGRAMA-probar-todo. Leé AGENTS.md.

Tarea: crear scripts/probar_todo.py, UN comando que corre todas las pruebas automáticas de a una y deja UN informe.
Modos:
  --rapido : caza rápida (`scripts/caza/cazar.py rapida`) + `scripts/tests_afectados.py --correr`.
  --noche  : registros de uso (`scripts/registro_bugs.py`, si existe; si no, se saltea con aviso), caza de noche
             (`scripts/caza/cazar.py noche --horas N`, N por `--horas`, por defecto 6), prueba de la ventana
             (`scripts/prueba_ui/todo.py`, con OMNICAD_PRUEBA_VENTANA=minimizada) y el cierre completo
             (`scripts/cierre_completo.sh`).
Reglas:
- Cada paso corre con `scripts/turno.py` (uno a la vez en toda la PC), desde clon/ y con el Python del venv
  (clon/.venv/Scripts/python.exe en Windows, clon/.venv/bin/python si no). Mirá cómo los llama cierre_completo.sh.
- Si un paso falla o se corta, se anota y se sigue con el siguiente. Si se corta todo, al volver a correrlo con
  --seguir retoma desde el paso que faltaba (estado en un JSON dentro de la carpeta del informe).
- Informe: evidencias/probar_todo_<AAAA-MM-DD>/informe.md, en español, corto: una tabla paso | resultado | duración
  | dónde está el detalle (la ruta del log o del informe de cada paso), y al final la lista de lo que falló.
- Código, nombres, comentarios y mensajes en español. Solo biblioteca estándar.
- Test chico en clon/tests/test_probar_todo.py que reemplaza los pasos por comandos falsos (no corre nada pesado) y
  comprueba: orden de los pasos por modo, que un fallo no corta el resto, que --seguir retoma y que el informe sale.
- Agregá una línea a la tabla de scripts de AGENTS.md (Mapa de carpetas › scripts/).
Al terminar, escribí evidencias/manual/probar_todo_2026-11-12.md con: archivos tocados, cómo se usa, qué no probaste.
```
