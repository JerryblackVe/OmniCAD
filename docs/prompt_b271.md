# B-271: Parámetros toca un árbol ya borrado

El diálogo de Parámetros (`clon/omnicad/ui/dialogo_parametros.py`) deja llamadas diferidas a `_poblar`
(`QTimer.singleShot(0, self._poblar)`, líneas ~341, 362 y 392) y señales del documento conectadas a `_recalcular`
(línea ~110). Si el diálogo se cierra antes de que lleguen, `_poblar` toca el `QTreeWidget` ya borrado y
«RuntimeError: Internal C++ object (QTreeWidget) already deleted» se escapa de un slot de Qt. Fila en
`docs/seguimiento/bugs.md` (B-271).

## Prompt para el agente

Guardado el 2026-11-10. Modelo sugerido: Claude Sonnet 5 con esfuerzo bajo, u OpenCode con GLM (gratis); es un arreglo chico de interfaz con su test.

```text
Sos un agente de código en OmniCAD (D:\PROGRAMA, CAD 3D en Python con PySide6). Tarea: arreglar el bug B-271.

ANTES DE EMPEZAR, invocá con la herramienta Skill (si tu entorno las tiene): `fable-method` y `ponytail`.
Aplicá `plan-then-do` (leé el archivo real antes de editar), `tool-calling-guard` y `verify-before-commit`.
Antes de terminar, invocá `ponytail-review` y pegá su salida real en el reporte.
Si tu entorno no tiene skills: hacé el cambio más chico que resuelva el bug, leé antes de editar y no digas
«listo» sin pegar la salida real de los comandos.

REGLAS
- Todo en español (código, comentarios, mensajes).
- NO hagas commit ni push. NO toques otros archivos que los de esta tarea.
- Trabajá en una carpeta aparte: desde D:\PROGRAMA corré `bash scripts/worktree_item.sh crear B-271`
  (crea D:\PROGRAMA-B-271 en la rama item/B-271). Todo el trabajo va ahí, no en D:\PROGRAMA.
- Python: `D:\PROGRAMA\clon\.venv\Scripts\python.exe` (no uses `python` del PATH).

EL BUG
- Archivo: `clon/omnicad/ui/dialogo_parametros.py`, método `_poblar` (~línea 273).
- El diálogo programa llamadas diferidas `QTimer.singleShot(0, self._poblar)` (~líneas 341, 362, 392) y
  conecta señales del documento a `_recalcular` (~línea 110). Si el diálogo se cierra antes de que lleguen,
  `_poblar` toca `self.arbol` (un QTreeWidget ya borrado) y sale
  «RuntimeError: Internal C++ object (QTreeWidget) already deleted» desde un slot de Qt.
- Arreglo esperado (el más chico que lo resuelva): que esas llamadas no lleguen a un diálogo muerto.
  Por ejemplo, usar la forma de QTimer.singleShot con objeto de contexto (`QTimer.singleShot(0, self, self._poblar)`)
  para que Qt la cancele sola, y desconectar las señales del documento al cerrar el diálogo.
  Si encontrás una forma más chica y correcta, usala y explicá por qué.

TEST (obligatorio)
- Agregá un test en `clon/tests/` (buscá el test que ya cubre el diálogo de parámetros con
  `grep -rl "dialogo_parametros" clon/tests` y sumalo ahí). Debe: abrir el diálogo, dejar una llamada diferida o
  un recálculo pendiente, cerrar y borrar el diálogo, procesar eventos, y comprobar que no escapa ninguna excepción
  (por ejemplo, con `sys.excepthook` capturado o el patrón que ya use ese archivo de tests).
- El test tiene que FALLAR con el código viejo y PASAR con el arreglo. Probalo las dos veces y anotá las dos salidas.

VERIFICACIÓN (desde D:\PROGRAMA-B-271\clon)
1. `D:\PROGRAMA\clon\.venv\Scripts\python.exe -m ruff check .` → limpio.
2. `D:\PROGRAMA\clon\.venv\Scripts\python.exe ../scripts/tests_afectados.py --correr` → 0 fallidos.
   Si hay un rojo, decí si ya fallaba antes de tu cambio (corré ese test solo en D:\PROGRAMA).
3. NO corras la suite completa ni la prueba de humo.

AL TERMINAR
- En `docs/seguimiento/bugs.md` (del worktree): borrá la fila B-271 y actualizá el conteo del encabezado.
- En `PROJECT_LOG.md` (del worktree), sección `## Registro`, agregá una viñeta arriba:
  `- **2026-11-10 · B-271.** Qué se hizo, archivos, test que lo cubre, verificación (ruff, tests_afectados).`
- Escribí el REPORTE en `D:\PROGRAMA\evidencias\manual\B-271_2026-11-10.md` (creá la carpeta si no existe) con:
  1. Qué cambiaste y por qué (2-4 líneas).
  2. Archivos tocados (lista).
  3. Salida real del test nuevo con el código viejo (falla) y con el arreglo (pasa).
  4. Salida real de ruff y de tests_afectados.
  5. Salida real de ponytail-review (o tu revisión línea por línea si no tenés la skill).
  6. Lo que no pudiste hacer o dudas, con ⚠.
- No commitees: el coordinador revisa el reporte y el diff, y commitea él.
```
