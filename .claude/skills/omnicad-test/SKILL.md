---
name: omnicad-test
description: "Probar OmniCAD a fondo y anotar cada hallazgo en docs/seguimiento/: pruebas de tortura, cazar bugs de una herramienta o comando, usarlo como un usuario (MCP en vivo, CLI o botones de la ventana real) y juntar datos de rendimiento. Usala con /omnicad-test, 'prueba de tortura de OmniCAD', 'buscá bugs en OmniCAD', 'probalo como usuario', 'probá esta herramienta a fondo', 'juntá información de rendimiento'. NO la uses para diseñar una pieza para el usuario (eso es la skill omnicad) ni para arreglar bugs: esta skill prueba y documenta."
metadata:
  opencode/slash: "true"
---

# OmniCAD a prueba: tortura, bugs e información

Esta skill **prueba y documenta**. No toca el código del programa: cada **hallazgo** (bug, faltante o mejora)
queda anotado para que lo arregle otra sesión. Para manejar el programa (herramientas, selectores, `error_kind`)
usá la skill `omnicad`; esta suma el método de prueba y dónde se anota cada cosa.

## 1. Antes de la primera llamada

- Leé `AGENTS.md` (reglas, memoria, verificación) y `docs/seguimiento/README.md` (columnas y estados).
- `git branch --show-current` y `git status`: otra sesión puede estar trabajando en la misma carpeta.
- Versión: `omnicad --version` (CLI) o `get_mode` (MCP en vivo). Va en cada ficha.
- Carpeta de evidencia: `evidencias/<tema>_<AAAA-MM-DD>/`. Ahí van scripts, `.omnicad`, capturas y mediciones.
  Está en `.gitignore`: nunca `git add -f`.
- Documentos de prueba propios, nunca el del usuario. Antes de cada corrida, copia del `.omnicad`; después,
  comparar volumen y caja por cuerpo contra la copia.

## 2. Elegir la vía

| Vía | Cómo se arranca | Cubre |
|---|---|---|
| MCP en vivo | App abierta con el puente: `clon/.venv/Scripts/python.exe clon/OmniCAD.py --puente`. Primera llamada: `get_mode`. | El puente, la ventana que se refresca, `capture_viewport`, `select_entities`, `find_in_window`, `APP_BUSY`. `execute_code` está apagado salvo la preferencia `general/puente_codigo` |
| MCP sin ventana o CLI | MCP con `--modo sin_ventana`, o la CLI desde `clon/`: `.venv/Scripts/python.exe -m omnicad.cli call <herramienta> --doc x.omnicad --json --args '{...}'`; muchos pasos: `batch pasos.jsonl --doc x.omnicad --continue-on-error --json` | La API entera, la geometría, guardar y reabrir. La CLI **no tiene modo en vivo**: siempre trabaja sobre el archivo |
| Usuario (botones) | Script QTest sobre la ventana real (modelos: `scripts/capturas_ui.py`, `scripts/auditoria_ui.py`), o computer use en Claude Code de escritorio (OpenCode no lo tiene). Foto de la ventana: `omnicad dev screenshot ventana.png` | La cinta, menús, diálogos, atajos, lo que ve la persona |

- En vivo, mirá los `avisos` de cada respuesta: el MCP en `auto` pasa solo de sin ventana a vivo cuando se abre
  la app, y desde ahí toca **otro documento**.
- Script QTest: preferencias en un `.ini` temporal (como `capturas_ui.py`), `QT_QPA_PLATFORM=windows` para que
  las fuentes sean las reales, fotos con `widget.grab()` y movimientos simulados como `_mover` de
  `clon/omnicad/prueba_humo.py`.

## 3. Elegir el modo

| Modo | Qué se hace | Listo cuando |
|---|---|---|
| Diseño en vivo | Armar una pieza real que use al menos 4 familias (boceto, sólido, modificar, patrón, ensamble, chapa…). Tras cada paso: imagen en 2 o 3 vistas y un número (volumen, caja) contra la cuenta a mano. Al final, cambiar una cota un 25 % y ver que todo recalcula | Pieza terminada, cada paso con imagen y número revisados, y guardar → reabrir da los mismos volúmenes |
| Tortura | Valores extremos (0, negativos, 1e-6, 1e6, `nan`), archivos hostiles (ZIP roto, JSON anidado, DXF con `inf`), historiales largos (100+ pasos), deshacer y rehacer en cadena, guardar y reabrir, exportar a cada formato e importarlo de vuelta. Cada caso pesado en su propio proceso con `subprocess.run(timeout=…)` (modelo: `scripts/fuzz_b39.py`) | Cada caso de la lista quedó con su resultado: ok, error claro, resultado malo o colgado (con el tiempo medido) |
| Cazador de bugs | Una herramienta o comando a fondo: `omnicad describe <herramienta>` y cada parámetro con un valor normal, uno de borde y uno inválido; combinaciones entre opciones; deshacer; en vivo y sin ventana | Cada parámetro de `describe` probado en normal, borde e inválido |
| Recolector de información | Tiempos (`omnicad dev bench`, el `seconds` de las respuestas, cronómetro por llamada), memoria, mensajes que confunden y diferencias contra Fusion según `analisis auto/` | Tabla de mediciones con la mediana de 3 corridas, guardada en la carpeta de evidencia |

## 4. Reglas que evitan perder la prueba

- **Lectura pesada en vivo** (`check_geometry`, `export_hidden_line_svg` sobre roscas modeladas o solevados):
  medila antes por cuerpo en un proceso aparte con tope. En la ventana puede congelarla más de 10 min sin
  cancelación.
- **Booleanas**: medí el volumen de cada entrada ANTES y el resultado después. El kernel puede devolver un
  resultado imposible sin error (unión = solo la herramienta, vacío, «sin contacto»).
- **Proyecto viejo**: un `.omnicad` abierto trae guardados los pasos lentos. Para probar el núcleo sobre él,
  editá el paso afectado (cambiá un valor y volvelo).
- **Memoria**: la PC tiene 13 GB. Comandos pesados de a uno, con
  `.venv/Scripts/python.exe ../scripts/turno.py -- <comando>` (corta a los 900 s; `--plazo` para más).
  Nunca dos suites a la vez. Un «access violation» en lugares distintos es falta de memoria: repetilo con
  memoria libre antes de anotarlo.
- **Diálogos modales**: un `QMessageBox` cuelga un script; parchealo antes. En vivo, `APP_BUSY` con una captura
  sin nada raro suele ser un diálogo abierto: sacá la pantalla completa, no la ventana.
- **Ratón**: no lo uses sobre la prueba de humo ni sobre un script QTest que está corriendo.
- **`BRIDGE_ERROR`**: no se sabe si se aplicó. Mirá `get_timeline` antes de repetir.

## 4b. REGLA FIJA: probar como una persona que usa la app todos los días

En TODA prueba (cualquier vía y modo), la ventana se maneja como lo haría un usuario humano habitual. No alcanza con llamar a la API ni con `set_valor`.

- **Mouse**: elegir con clics reales del visor (`visor.elegir_entidad`), arrastrar las asas (press, varios movimientos, release), pasar el cursor por encima (hover), doble clic en el timeline para editar, clic derecho, rueda y órbita. Eventos simulados al widget (`_mover`, `QMouseEvent`), nunca el cursor real. Modelos: `evidencias/ui_2026-10-24/u3_asas.py`, `arnes.py`.
- **Botones y teclas**: pulsar cada botón (Aceptar, Cancelar, X, flechas del timeline, deshacer/rehacer), Enter, Esc, Tab y Shift+Tab entre campos, y comprobar qué pasa con cada uno (se cierra, avisa, no hace nada).
- **Dónde se escriben los valores y textos**: escribir en el campo real (tecleando: `QTest.keyClicks`, borrar, pegar), no solo `setText`. Revisar en cada campo: que acepte lo que acepta Fusion (unidades «15 mm», «45 deg», expresiones, parámetros), qué pasa con texto, vacío, 0, negativo, enormes y coma decimal; que el valor se vea donde se escribió (campo, caja flotante junto al asa, barra de estado); que el rojo y el mensaje aparezcan donde la persona mira; que al reabrir el paso vuelva lo escrito; que Enter confirme y Esc descarte.
- **Lo que ve la persona**: una captura de la ventana tras cada paso importante (se mira de verdad, no solo se guarda) y comprobar que etiquetas, mensajes y orden de los campos se lean bien.
- Lo que no se pudo hacer así se anota con ⚠ en el informe final, con la razón.
- **Ya está automatizado**: `scripts/prueba_ui/` (arnés `arnes.py`, `corredor.py`, `teclado.py`, escena de prueba y un script por pieza: `cinta_completa`, `superficie`, `solido_crear`, `solido_modificar`, `asas`, `teclear`, `ventana_uso`, `ensamblar`, `boceto_cotas`). `todo.py` los corre de a uno. Lista completa de qué cubre una prueba completa: `CLAUDE.md`, «toda prueba se hace como un usuario humano habitual». Para un comando nuevo, sumar su receta a la pieza que corresponda en vez de escribir un script suelto.

## 5. ¿Es un hallazgo?

Antes de anotar, descartá lo falso:

1. **Servidor viejo**: un MCP levantado hace rato no tiene las herramientas nuevas. Compará con `omnicad tools`.
2. **Uso mal hecho**: verificá los argumentos con `omnicad describe` o `describe_operation`.
3. **Caso mínimo**: reproducilo dos veces en un documento nuevo con los pasos mínimos. Muchos «bugs» reportados
   por agentes eran la herramienta mal usada.
4. **Medidor que miente**: reproducilo con el modelo de evidencia antes de culpar a la medición (B-43 y B-60
   eran el medidor andando bien).
5. **Ya cargado**: buscá una palabra clave en `docs/seguimiento/*.md` y en el Registro de `PROJECT_LOG.md`.

Después, clasificalo:

| Tipo | Cuándo | Dónde va | Serie del ID |
|---|---|---|---|
| Bug | Falla, cuelgue, crash, resultado que no da la cuenta, aviso donde iba un error, mensaje que engaña, doc que no coincide | `docs/seguimiento/bugs.md`, «Abiertos y parciales», más su ficha en «Detalle de lo abierto» | B-n |
| Faltante | Una función que no existe | `docs/seguimiento/faltantes.md`, «Hallazgos de pruebas de uso» | H-n |
| Faltante de la capa de agentes | Algo de la app que no tiene herramienta MCP/CLI | `faltantes.md`, «Hallazgos de pruebas de uso» | MCP-n |
| Mejora | Existe y anda, pero se puede mejor: lento, mensaje pobre, interfaz | `docs/seguimiento/mejoras.md`: «Prueba de tortura» si salió de una tortura, si no «Hallazgos de pruebas de uso» | T-n o H-n |

Una ficha por hallazgo. Dos fallas con la misma causa: una sola.

## 6. Anotarlo

1. **ID**: el siguiente libre de su serie. Lo resuelto se borra de las listas, así que el más alto se busca
   también en el log y en git (desde la raíz del repo, en Bash; cambiá `B` por `H`, `T` o `MCP`):

   ```bash
   { git log --format=%B; cat PROJECT_LOG.md docs/seguimiento/*.md; } | grep -oE '\bB-[0-9]+\b' | sort -t- -k2 -n -u | tail -1
   ```

   El número que sale, más uno. Un ID nunca se reusa.
2. **Fila** con las 7 columnas: `| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |`.
   - Estado `Abierto`, o `Sin verificar` si no se pudo reproducir.
   - Evidencia: `archivo:línea` o un test que exista (`tests/test_seguimiento.py` falla si nombra uno que no
     existe). La ruta de `evidencias/` va en la ficha, porque no está en git.
   - Verificado: la fecha de hoy.
   - Sin barra vertical dentro de una celda, ni escapada (`|Z` se escribe «aristas paralelas a Z»): el test
     parte la fila por ahí y la saltea sin avisar (H-51).
3. **Ficha del bug** en «Detalle de lo abierto», con los campos de la ficha de la skill `omnicad`
   (`.claude/skills/omnicad/SKILL.md`, «Si encontrás un bug de OmniCAD», punto 4): qué hiciste con los
   argumentos exactos, esperado y obtenido, cómo reproducir, entorno, causa probable solo si la leíste en el
   código, esquive y prueba propuesta.
4. **Contadores**: la línea «Total N: …» de la cabecera del archivo y, en faltantes y mejoras, la línea de
   conteo de la sección (p. ej. «Abierto 1 · Parcial 2.»).
5. **Comprobá** desde `clon/`:
   `.venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe -m pytest tests/test_seguimiento.py -q`

La lista de pendientes vive **solo** en `docs/seguimiento/`: nada de informes aparte con hallazgos. Las
mediciones crudas quedan en la carpeta de evidencia.

## 7. Cerrar la sesión de prueba

- **Registro** de `PROJECT_LOG.md` (sección `## Registro`, una viñeta):
  `- **AAAA-MM-DD · Prueba omnicad-test: <tema>.** Vía y modo, qué se probó, hallazgos con sus IDs, evidencia en evidencias/<carpeta>/, verificación (test_seguimiento N OK).`
- **Lección** en «Lecciones aprendidas» solo con señal verificable (un test que falló, un caso reproducido),
  con el formato de `AGENTS.md`.
- `PROJECT_LOG.md` y `AGENTS.md` tienen finales CRLF: editalos con la herramienta de edición y mirá
  `git diff --stat` (dos o tres líneas por viñeta, no cientos).
- Sin commits ni push salvo que te lo pidan.
- **Mensaje al usuario**, 3 a 5 líneas, el resultado primero: cuántos bugs, faltantes y mejoras, con sus IDs y
  dónde quedaron. Lo que no se pudo probar, en una línea con ⚠.
