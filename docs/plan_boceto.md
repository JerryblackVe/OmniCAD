# Plan del boceto: llevarlo al nivel de Fusion 360

Origen: auditoría del 2026-10-23 de la sección «Design: Sketch» de la ayuda de Fusion (`analisis/fusion_doc/paginas/SKT-*`)
contra el código, con pruebas reales por API. Cinco auditores: formas, curvas y texto, modificar y proyectar, cotas y
solver, entorno y paridad MCP.

El estado de cada ítem vive en `docs/seguimiento/` (bugs `B-88…B-103`, faltantes `BOC-1…26`, mejoras `BOC-27…30`).
Este documento solo ordena el trabajo. Al resolver un ítem se borra su fila y se anota en el Registro del `PROJECT_LOG.md`.

## Resultado de la auditoría

| Zona | OK | Bugs | Faltantes o parciales |
|---|---|---|---|
| Formas básicas (línea, rectángulo, círculo, arco, polígono, elipse, ranura) | 27 | 5 | 8 |
| Splines, cónicas, puntos, texto | 16 | 4 | 15 |
| Modificar, patrones, simetría, proyección | 9 | 3 | 20 |
| Cotas, restricciones, solver, AutoConstrain | 28 | 6 | 10 |
| Entorno, paleta, Boceto 3D, paridad MCP/CLI | 40 | 3 | 8 |

La paridad con MCP/CLI está completa para lo que ya existe (301 pruebas pasan). Los huecos de herramienta son los
de los propios faltantes.

## Reglas para todas las fases

- Cada ítem incluye su herramienta en `clon/omnicad/api/` (receta C), su test y la doc regenerada
  (`omnicad tools --markdown --output docs/agentes/herramientas.md`).
- Se arregla un bug **con el test que lo reproduce primero**. Los scripts de la auditoría están en el scratchpad de la
  sesión de planificación y no están en el repo: cada fase reproduce con su propio test.
- Los archivos se pisan (`restricciones/boceto.py`, `ui/editor_boceto.py`, `api/herramientas_boceto.py`): **un solo
  escritor por archivo a la vez**. Las fases van en orden; dentro de una fase solo se paraleliza lo que toca archivos
  distintos.
- Verificación por fase: `ruff`, el `pytest` de las áreas tocadas y la prueba de humo si se tocó la UI. La suite completa
  la corre una sola sesión a la vez.
- Antes de cada fase, la sesión revisa que los IDs sigan abiertos (grep en el código y en `docs/seguimiento/`).

## Fases

| # | Fase | Ítems | Archivos principales | Modelo y esfuerzo | Listo cuando |
|---|---|---|---|---|---|
| 0 | Validación de entradas y API | B-88, B-89, B-90, B-91, B-92, B-93 | `api/herramientas_boceto.py`, `herramientas_boceto_plano.py`, `herramientas_vectores.py`, `restricciones/boceto.py` (solo validación) | Sonnet, medio | Cada entrada inválida devuelve error claro, nunca `INTERNAL_ERROR`; `draw_line` encadena; un test por bug |
| 1 | Errores de la UI del boceto | B-94, B-95, B-97, BOC-23 | `ui/editor_boceto.py`, `ui/ventana.py` | Sonnet, medio | Rehacer vuelve a 3 curvas; Suprimir borra la selección sin salir; humo OK |
| 2 | Geometría y solver correctos | B-96, B-98, B-99, B-100, B-101, B-102, B-103 | `restricciones/solver.py`, `restricciones/boceto.py` | Opus, alto | Tests nuevos: arcos simétricos dan dof 9, ángulo con largo 1e5 sin falso conflicto, `auto_constrain` de 440 entidades en menos de 10 s, desfase colapsado falla |
| 3 | Intención de diseño: cotas | BOC-1, BOC-2, BOC-3, BOC-25, BOC-6, BOC-7 | `restricciones/boceto.py`, `ui/editor_boceto.py`, `api/herramientas_boceto.py` | Opus, alto | Cota redundante pasa a referencia sola; `d1` usable en expresiones; cota entre círculos; `get_sketch` con estado por entidad |
| 4 | AutoConstrain completo | BOC-4, BOC-5 | `restricciones/solver.py`, `ui/editor_boceto.py` | Opus, alto | Infiere los 7 tipos que faltan; diálogo con resultados y «Finish with AutoConstrain»; tope de 250 entidades |
| 5 | Dibujar con precisión | BOC-9, BOC-12, BOC-24, BOC-13, BOC-19, BOC-15, BOC-26 | `ui/editor_boceto.py`, `api/herramientas_boceto.py`, `ui/modo_boceto.py` | Opus, alto para BOC-9; Sonnet para el resto | Snaps de punto medio, curva, tangente y perpendicular con guías; valores tipeables en todas las herramientas; línea central como eje |
| 6 | Modificar, patrones y proyección | BOC-14, BOC-16, BOC-17, BOC-10, BOC-8, BOC-18, BOC-30 | `restricciones/boceto.py`, `api/herramientas_boceto.py`, `timeline/operaciones.py` | Opus, alto | Desfase de dos lados y de spline; patrones editables; romper vínculo de proyección; copiar y pegar entre bocetos |
| 7 | Splines y texto | BOC-11, BOC-20, BOC-21, BOC-28 | `restricciones/boceto.py`, `nucleo/fuentes.py`, `ui/editor_boceto.py` | Opus, alto para BOC-11; Sonnet para el resto | Manijas, peine, insertar punto y cambiar grado con herramienta de API; parámetros de texto automáticos |
| 8 | Grandes | FU-1 (Boceto 3D), BOC-22 (curvas a malla), BOC-27 (rendimiento), SC4, P-10b-f | varios | Fable, alto, una sesión por ítem | Cada uno con su propio plan; BOC-18 (intersección y proyección a superficie) espera a FU-1 |

## Orden y dependencias

- **0 y 1 primero**: son baratos, sacan errores que ven los agentes y los usuarios, y no dependen de nada.
- **2 antes que 3 y 4**: cotas y AutoConstrain se apoyan en el solver; hoy da falsos conflictos con geometría grande.
- **3 antes que 4**: AutoConstrain usa las cotas de referencia y el estado por entidad de BOC-6.
- **5, 6 y 7** pueden ir en cualquier orden entre sí, pero tocan los mismos archivos: de a una.
- **8** al final. BOC-27, SC4 y P-10b-f son el mismo problema (rendimiento del solver) y se deciden juntos.

## Limpieza que va con la fase 0

- `docs/brechas_mcp.md:181-190` lista MCP-72, 73, 74 y 94 como pendientes, pero la auditoría los encontró implementados
  (círculo por 2 y 3 puntos, polígono por arista, línea de punto medio, arco tangente). Verificar y corregir el documento.
- Decisión del usuario ya abierta: MCP-HAL3 (agregar «Guardar como SVG» y «Limpiar geometría» al menú del boceto).

## Fuera de alcance de este plan

- Stretch, Rotate y Align de boceto: no existen en el Modify de Fusion.
- Tolerancias de cota y longitud de arco como cota: la ayuda de boceto de Fusion no los documenta.

## Estado

Fases 0 a 8 ejecutadas el 2026-10-24 (commits `33058e8` a la Fase 8). Lo que queda de cada ítem vive en `docs/seguimiento/` (filas `Parcial` con su «Queda»); la Fase 9 los cierra.
