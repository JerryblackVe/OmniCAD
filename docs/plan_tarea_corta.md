# Tarea corta para OpenCode

Una sola tarea, el resto de B4 (esquinas en Vectorizar imagen), para MiniMax en OpenCode. Corre junto con otros agentes
(KS1 en el render, H-59 en el deshacer): no tocan los mismos archivos, ni `docs/seguimiento/` ni `PROJECT_LOG.md` (eso
lo hace el coordinador). Al terminar se borran este documento y sus dos filas de índice (`docs/README.md` y
`docs/seguimiento/README.md`).

## Prompt para el agente

Entregado el 2026-11-03. Modelo sugerido: MiniMax Flash en OpenCode, esfuerzo medio. Es la versión M3.1, gratis por NVIDIA. Comando: `opencode -m nvidia/minimax-m3.1-flash`.

```text
ARRIBA DE TODO, ANTES DE TOCAR NADA
Invocá las skills fable-method, ponytail, plan-then-do, tool-calling-guard y verify-before-commit. Si no aparecen como
skills, leé su SKILL.md en C:\Users\mosos\.claude\skills\<nombre>\ y seguilo.

OBJETIVO
B4 (lo que falta): en Vectorizar imagen con «Curvas suaves», respetar las esquinas filosas del dibujo.

CONTEXTO
- Repo D:\PROGRAMA, rama main. Leé AGENTS.md (receta B y receta C). Trabajá desde clon/ con clon/.venv.
- Otros agentes trabajan en la misma carpeta (ui/render.py, api/herramientas_render.py, timeline/documento.py,
  ui/dialogo_parametros.py, archivos de malla, ui/visor3d.py, ui/cinta.py). Tocá solo los archivos de esta tarea. Si
  ves cambios sin commitear en otros archivos, son suyos: no los toques ni los reviertas.
- Vectorizar imagen no existe en Fusion. La idea sale de Blender: docs/brechas_blender.md (buscá «esquina»).

QUÉ PASA HOY
- clon/omnicad/io_archivos/vectorizar.py, `vectorizar_imagen` (cerca de la línea 145): con curvas=True cada contorno
  cerrado sale como UNA spline cerrada ('curva', puntos, True). La spline redondea las esquinas: un logo con puntas
  (estrella, letra «A», un cuadrado grande) sale con las puntas romas.
- Los contornos de menos de MIN_PUNTOS_CURVA vértices quedan polilínea (comentario T-10): no lo cambies.
- Las primitivas pasan a un boceto en clon/omnicad/io_archivos/boceto_archivos.py, `boceto_desde_primitivas`. Leé
  cómo trata 'curva' y 'polilinea', y si acepta tramos abiertos (el tercer valor en False).

QUÉ TIENE QUE QUEDAR
1. Un ángulo de esquina nuevo (en grados). En un vértice donde el contorno dobla más que ese ángulo, hay una esquina.
   Con curvas=True, el contorno se parte en sus esquinas: entre esquina y esquina, una spline abierta (o un segmento
   recto si el tramo tiene solo 2 puntos). Los tramos comparten sus puntas, así el perfil sigue cerrado.
2. Un contorno sin esquinas sigue igual que hoy: una spline cerrada.
3. Valor por defecto que no cambie nada para quien no lo toca: 0 = sin detección (todo como hoy). Elegí el nombre y
   explicá el valor en el docstring.
4. Con curvas=False (polilínea) el ángulo no hace nada.
5. Llega a los tres lugares, con el mismo nombre de concepto:
   - `vectorizar_imagen` (parámetro nuevo),
   - el diálogo `VectorizarImagen` en clon/omnicad/ui/comandos/insertar.py (un campo avanzado, con `visible_si`
     solo cuando «Curvas suaves» está tildada, y sumado a `clave_filtro` para que la vista previa se rehaga),
   - la herramienta `trace_image` en clon/omnicad/api/herramientas_vectores.py (parámetro en inglés, `corner_angle`,
     con su línea en el docstring).
6. Regenerá la doc de herramientas, desde la raíz del repo:
   `clon/.venv/Scripts/python.exe -m omnicad.cli tools --markdown --output docs/agentes/herramientas.md`
   (si ese comando no anda desde la raíz, mirá AGENTS.md › Receta C, punto 9).

TEST (en clon/tests/test_texto_vectores.py, al lado de los tests de vectorizar que ya hay)
- Una imagen generada en el test (numpy o Pillow, sin archivos) con una forma de puntas filosas, grande (por ejemplo
  un triángulo o una estrella de 200 px). Con el ángulo activado, salen varios tramos abiertos y sus puntas caen sobre
  las esquinas reales (tolerancia de pocos píxeles). Sin el ángulo, sale una sola spline cerrada como hoy.
- Un círculo grande con el ángulo activado sigue saliendo como una spline cerrada.
- `trace_image` con `corner_angle` crea un boceto con un perfil cerrado (se puede extruir o el boceto da 1 perfil).
- Los tests nuevos tienen que fallar sin el arreglo.

VERIFICACIÓN (desde clon/)
- .venv/Scripts/python.exe -m ruff check .
- .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe -m pytest tests/test_texto_vectores.py -q -W error
- También: tests/test_doc_agentes.py, tests/test_cobertura_ui_api.py y tests/test_api_vectores.py si existe
  (con turno, uno por uno).

REVISIÓN FINAL OBLIGATORIA: ponytail-review
El coordinador rechaza el trabajo si este paso falta o viene en otro formato. No alcanza con decir que la invocaste.
1. Invocá la skill ponytail-review. Si no aparece, leé ENTERO C:\Users\mosos\.claude\skills\ponytail-review\SKILL.md.
2. Revisá tu diff siguiendo esa skill paso por paso: leé los llamadores de lo que cambiaste y buscá casos borde.
3. Pegá el resultado con ESTE formato exacto, en este orden:
   What this change does: <dos o tres frases>
   Luego los hallazgos numerados, en grupos «Must fix», «Should fix», «Nice to have» (saltá los grupos vacíos).
   Cada hallazgo lleva sus cuatro partes: What this is, Problem, Fix, If we skip it.
   Al final: «Verdict: Ship.» o «Verdict: fix N first.», y «Not checked:» si algo no pudiste ver.
4. Si un hallazgo es «Must fix», arreglalo, volvé a correr los tests y decilo.
Formatos como «net: 0 lines», «shrink:» o «delete:» son de OTRA skill y no sirven.

REGLAS
- SÍ: el cambio más chico que resuelve la tarea, en español, con sus tests.
- NO: alias, parámetros o conversiones que nadie pidió. No toques la vista previa del diálogo más allá de clave_filtro.
- NO: commit, push, instalar paquetes ni gastar en APIs.
- NO: tocar docs/seguimiento/, PROJECT_LOG.md, ui/render.py, timeline/documento.py, ui/dialogo_parametros.py,
  ui/visor3d.py, ui/cinta.py ni los archivos de malla.
- NO: correr la suite completa, la prueba de humo ni cazar.py.
- NO: abrir ni tocar una app de OmniCAD abierta. No abrir Fusion.
- NO: leer privado/, analisis/, archivos .env ni nada fuera del repo, salvo los SKILL.md nombrados.
- NO: borrar archivos fuera de los que vos creaste, ni comandos de git que cambien el historial o descarten cambios
  (reset, checkout de archivos, stash, clean).
- NO: convertir finales de línea.
- Si no sale después de dos intentos, pará y explicá por qué.

INFORME FINAL
Resuelto o no, el nombre y el valor por defecto del ángulo, archivos tocados, tests agregados, la salida real de pytest
antes (falla) y después (pasa), ruff, y la revisión ponytail-review con el formato de arriba.
```
