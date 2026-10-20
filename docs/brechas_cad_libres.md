# Brechas frente a otros CAD libres de GitHub

> Estado de cada ID: [docs/seguimiento/](seguimiento/README.md). Este archivo es la especificación; si un estado de acá no coincide con el seguimiento, vale el seguimiento.

Fecha: 2026-10-19. Fuente: búsqueda profunda en GitHub, corrida en OpenCode con GPT-6.1 Sol y verificada después
(estrellas, licencias y 2 afirmaciones de contenido contrastadas con `gh api`). Informe completo, fuera del repo:
`D:\IA\DEEP RESEACH\2026-10-19_cad-parametrico-open-source-similares-omnicad.md` (45 repos, 44 README leídos).

**Regla:** se toman ideas y se escriben desde cero. Antes de copiar código, mirar la licencia de cada proyecto: hay MIT,
Apache-2.0, GPL-3.0 y AGPL-3.0 (esta última no se puede incorporar a OmniCAD sin cambiar su licencia).

No se repiten las ideas ya cargadas en otros pendientes: nombres estables de caras (SC3), misma batería de piezas para
los dos motores (SC1), guardado atómico (ya existe: `io_archivos/proyecto.py:207`) y tolerancia de impresión (pendiente 29.1).

Cada ítem lleva su herramienta MCP/CLI (receta C de `AGENTS.md`), test y doc regenerada.

| # | Idea | Sale de | Qué hay hoy en OmniCAD | Esfuerzo |
|---|---|---|---|---|
| CL1 | **Cambio de agente con revisión.** El agente prueba la operación aparte (vista previa), y se aplica solo si el documento sigue en la revisión que leyó. Si una persona cambió algo mientras tanto, se rechaza. Un cambio aplicado se deshace en un paso. | [PartMode](https://github.com/BOMWiki/partmode/blob/main/README.md#browser-approved-local-projects) (AGPL-3.0) | Las herramientas son atómicas (`Sesion.transaccion`), pero no comparan la revisión en el modo en vivo. | medio |
| CL2 | **Resultado con efecto observado.** Además de `ok`, cada herramienta dice qué cambió de verdad (`applied`, `moved`, `bytes_written`, revisión final). Así una operación que no hizo nada no pasa por trabajo hecho. | [fusion-cad-mcp](https://github.com/Mfrostbutter/fusion-cad-mcp/blob/main/README.md#every-tool-returns-the-same-envelope) | Devuelven `{"ok", "result", "avisos"}`, sin campo de efecto. | medio |
| CL3 | **Tutoriales reproducibles.** Recetas con capítulos, explicación y cámara, que se reproducen paso a paso y se pueden retocar. | [Limo CAD](https://github.com/limo-cad/Limo-CAD/blob/main/README.md#make-your-first-part) (LGPL-2.1) | Hay animación y recetas (`get_recipe`), pero no tutoriales con capítulos. | medio |
| CL4 | **Elegir caras por descripción.** Selectores por propiedades e intención («las caras cilíndricas del agujero de montaje»), que devuelven candidatos, propiedades y por qué coinciden, y avisan si es ambiguo. | [SimpleCADAPI](https://github.com/PhySpace/SimpleCADAPI/blob/master/README.md#3--code-first-editor) | En parte: `find_faces` y `find_edges`. | medio |
| CL5 | **Diagnóstico para el agente.** Registro de operaciones y captura de fallos con contexto (restricciones, error del kernel) que el agente puede consultar. | [freecad-mcp](https://github.com/blwfish/freecad-mcp/blob/main/README.md#built-in-diagnostics) | En parte: `list_error_reports` y `read_error_report`. | medio |
| CL6 | **Ver qué se mueve en el boceto.** Colores según los grados de libertad que quedan (espacio nulo del jacobiano) y detección de restricciones en conflicto. | [DATUM](https://github.com/Artis-98/datum/blob/main/README.md#what-it-does) (MIT, Python + OpenCascade como nosotros) | **Hecho (CL6):** el solver usa el espacio nulo del jacobiano (SVD) para saber qué entidades quedan determinadas y el editor las pinta (`restricciones/solver.py`, `ui/editor_boceto.py`); el conflicto de restricciones se detecta (`tests/test_solver.py::test_conflicto_se_detecta`). | medio |
| CL7 | **Ayuda del MCP según la versión.** El servidor entrega la guía de la misma versión que está corriendo. | [FluidCAD](https://github.com/Fluid-CAD/FluidCAD/blob/main/README.md#ai-agents) (MIT) | En parte: `get_guide` y la skill `omnicad`. | bajo |
| CL8 | **Importar con cobertura declarada.** Al abrir un archivo de otro programa, decir qué pasos se reconstruyeron y cuáles quedaron como cuerpo fijo. | [Extrudo](https://github.com/zoltanf/extrudo/blob/main/README.md#what-it-does) (GPL-3.0), [cadmpeg](https://github.com/cadmpeg/cadmpeg) | En parte: se abre `.f3d` con historial (`inspect_f3d`). | alto |

Orden sugerido: CL2 y CL7 primero (baratos y mejoran a todos los agentes), después CL1, CL6, CL4 y CL5, y al final CL3 y CL8.
