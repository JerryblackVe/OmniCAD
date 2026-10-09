# Guía de OmniCAD para agentes

OmniCAD es un CAD 3D paramétrico: el documento es una receta (parámetros + pasos de un timeline) que se
recalcula entera cada vez que cambia algo. Las herramientas se agrupan así:

| Grupo | Para qué | Ejemplos |
|---|---|---|
| documento | archivo, escena, timeline, deshacer | `get_scene_info`, `get_timeline`, `save_document`, `undo` |
| parametros | medidas con nombre que gobiernan el modelo | `get_parameters`, `set_parameter` |
| inspeccion | ver y medir el resultado | `get_viewport_image`, `get_physical_properties`, `measure_distance`, `check_interference` |
| avanzado | cualquier operación, receta, código, guía | `run_operation`, `describe_operation`, `get_recipe`, `execute_code` |

Hay más grupos (bocetos, sólidos…): el catálogo de herramientas del servidor es la lista completa y
cada una trae su descripción y sus argumentos.

## Temas

- `flujo`: el ciclo de trabajo (mirar, hacer, ver la imagen, medir, guardar), unidades, ids y errores.
- `selectores`: elegir caras y aristas (`>Z`, `|Z`, `%CIRCLE`…) para empalmes, chaflanes, vaciados, agujeros y bocetos sobre cara.

Pedí un tema con `get_guide(topic="flujo")`.

## Reglas que valen siempre

- Unidades: milímetros y grados. Un número solo se toma como mm o grados según el campo.
- Una herramienta que modifica es UN paso de deshacer y es atómica: si falla, el documento queda igual.
- Ante la duda de qué operación usar o cómo se llaman sus parámetros: `list_operation_types` y
  `describe_operation`.
