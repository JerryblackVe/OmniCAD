# Auditoría de Revolución, Barrido y Solevación en todos los espacios (2026-11-05)

Pedido de Gerardo (2026-11-05): la misma auditoría que se hizo con Extruir ([auditoria_extruir.md](auditoria_extruir.md)),
ahora con las herramientas Revolución, Barrido y Solevación: comparar con Fusion 360 y buscar bugs, mal funcionamiento y faltantes en SÓLIDO, SUPERFICIE,
PLÁSTICO, CHAPA, FORMA y donde más existan. Lo ejecuta una sesión aparte (Opus 5, esfuerzo alto). Tanda 1 de 2.
El informe se escribe en este mismo documento, arriba del prompt.

## Prompt para el agente

Entregado el 2026-11-05. Modelo sugerido: Opus 5, esfuerzo alto. Antes de usarlo, revisar que los IDs y las rutas sigan vigentes.

```text
ARRIBA DE TODO, antes de leer o tocar nada: invocá con la herramienta Skill, en este orden, fable-method, ponytail, plan-then-do, tool-calling-guard, verify-before-commit y omnicad-test. Durante la auditoría del código invocá ponytail-audit. Antes de cerrar invocá ponytail-review sobre todo lo que cambiaste. Pegá en ESTE documento la salida REAL y completa de ponytail-audit y de ponytail-review (no en una nota aparte): sin eso el coordinador no acepta el trabajo.

TAREA
Auditá las herramientas Revolución, Barrido y Solevación de OmniCAD, con TODAS sus opciones, en cada espacio donde Fusion 360 las tiene: SÓLIDO, SUPERFICIE, PLÁSTICO, CHAPA, FORMA (T-Splines) y cualquier otro (asas, MCP y CLI). Para cada herramienta y espacio: ¿actúa igual que Fusion? ¿Qué falla? ¿Qué falta? Es una AUDITORÍA: no arregles código de la app (clon/omnicad/). Lo que encuentres se documenta.
Modelo a seguir: la auditoría de Extruir, docs/auditoria_extruir.md (misma estructura de informe y matriz).

FUENTE DE VERDAD DE FUSION (leer ANTES de probar)
clon/.venv/Scripts/python.exe scripts/fusion_docs.py buscar <palabras> -s <carpeta>, con revolve, sweep y loft, en las carpetas fusion-model (SÓLIDO y PLÁSTICO), fusion-patch (SUPERFICIE), fusion-sculpt (FORMA) y fusion-sheet-metal (CHAPA). Leé cada artículo con ver "<título>" -s <carpeta> y mirá sus imágenes con Read (las imágenes ya se pueden leer). Si un espacio de Fusion NO tiene la herramienta, decilo citando docs/fusion_docs/indice/<carpeta>.md. Fusion real (MCP fusion360) está cerrado: solo si la ayuda no alcanza, abrilo, compará y cerralo.

DÓNDE ESTÁ EL CÓDIGO
Operaciones: clon/omnicad/timeline/ops_solido.py y ops_superficie.py. Núcleo: clon/omnicad/nucleo/solidos_crear.py y superficies.py. Interfaz: clon/omnicad/ui/comandos/crear.py, superficie.py, comunes.py y asas_extra.py; botones en ui/cinta.py. MCP y CLI: clon/omnicad/api/herramientas_solido.py, herramientas_superficie.py y herramientas_barrido.py.
Antecedentes (no repetir lo ya anotado): buscá en docs/seguimiento/*.md las palabras revol, barrido, solev, sweep y loft; mirá también docs/brechas_herramientas_solido.md y docs/brechas_superficie.md.

QUÉ REVISAR (matriz por herramienta)
Para cada opción de Fusion de cada herramienta (Revolución: perfil, eje, tipo de ángulo, completo, dos lados, al objeto, operación; Barrido: tipo (un recorrido, recorrido y guía, dos rieles), orientación, distancia, conicidad y giro, operación; Solevación: perfiles, rieles, línea central, condiciones de borde (conexión, tangencia, curvatura), tangencia de punta, cerrada, ajuste de aristas, operación) completá una fila: Fusion | OmniCAD ventana | MCP | CLI | estado | evidencia.

CÓMO PROBAR (regla de CLAUDE.md: como usuario humano)
- Ventana: desde clon/, .venv/Scripts/python.exe ../scripts/prueba_ui/todo.py <pieza> --ventana minimizada (Gerardo usa la PC). Si no hay pieza que cubra estas herramientas en todos los espacios, creá scripts/prueba_ui/revolucion_barrido_solevacion.py y sumala a PIEZAS de todo.py (nombre sin prefijo, como las demás). Cubrí: botón de la cinta en cada pestaña, elegir en el visor, teclear en cada campo (unidades, coma, expresiones, vacío, 0, negativo, enorme, pegar), asas (arrastrar, pasar por cero), previa, Aceptar, reabrir y editar desde el timeline, deshacer/rehacer, Enter, Esc, Tab, ventana 1024×640 y 800×520, guardar y reabrir, y que no se escape ninguna excepción en un slot de Qt.
- Mirá de verdad las capturas que saques (Read sobre el PNG) y decí qué se ve.
- MCP/CLI: toda opción de la ventana tiene que estar en la herramienta (regla estricta). Lo que falte es un faltante.
- Comandos pesados de a uno con ../scripts/turno.py. NO corras la suite completa ni la prueba de humo (las corre el coordinador de noche). Solo ruff check . y tus tests puntuales.

QUÉ ENTREGAR
1. En ESTE documento (docs/auditoria_revolucion_barrido_solevacion.md), arriba de «## Prompt para el agente», una sección «## Resultado (2026-11-05)»: referencia de Fusion por herramienta y espacio, la matriz, los bugs con pasos para reproducirlos, la salida de ponytail-audit, la de ponytail-review y lo que no se pudo verificar (⚠).
2. Cada bug, faltante o mejora nueva: fila en docs/seguimiento/bugs.md, faltantes.md o mejoras.md con el siguiente ID libre (mirá el más alto en docs/seguimiento/*.md y PROJECT_LOG.md), sin duplicar filas que ya existen (si ya está, citá su ID en la matriz).
3. Si creaste una pieza de prueba: anotala en docs/auditorias/prueba_nocturna_2026-10-31.md, sección «3q».
4. Una viñeta en «## Registro» de PROJECT_LOG.md.
5. Informe final corto: IDs creados (cuántos bugs, faltantes, mejoras), archivos tocados, salida real de ruff y de los tests que corriste.

REGLAS
Todo en español. No commitees ni hagas push: commitea el coordinador. No borres la sección del prompt. No toques clon/omnicad/; solo docs, seguimiento y la pieza de prueba. Nada de archivos sueltos: capturas y registros en evidencias/ui_2026-11-05/.
```
