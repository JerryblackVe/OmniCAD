# Guía de OmniCAD para agentes

OmniCAD es un CAD 3D paramétrico: el documento es una receta (parámetros + pasos de un timeline) que se
recalcula entera cada vez que cambia algo. Las herramientas se agrupan así:

| Grupo | Para qué | Ejemplos |
|---|---|---|
| documento | archivo, escena, timeline, deshacer | `get_scene_info`, `get_timeline`, `save_document`, `undo` |
| parametros | medidas con nombre que gobiernan el modelo | `get_parameters`, `set_parameter` |
| inspeccion | ver y medir el resultado | `get_viewport_image`, `get_physical_properties`, `measure_distance`, `check_interference` |
| boceto | dibujar, modificar, restringir y acotar bocetos 2D | `sketch_from_spec`, `draw_slot`, `sketch_fillet`, `trim_sketch_curve`, `edit_dimension` |
| vectores | fuentes, texto de boceto, insertar SVG / DXF, imagen → vector | `add_text`, `list_fonts`, `insert_svg`, `trace_image` |
| chapa | chapa metálica: reglas (también propias), pestañas, dobladillo, plegar, desplegar, desgarro, patrón plano y DXF | `create_base_flange`, `create_edge_flange`, `create_sheet_metal_rule`, `export_flat_pattern_dxf` |
| ensamble | componentes, uniones, accionar, límites, grupos rígidos, vínculos y estudio de movimiento | `get_assembly`, `create_component`, `create_joint`, `drive_joint`, `motion_study` |
| material | material físico (densidad → masa), materiales propios y aspecto | `list_materials`, `set_material`, `define_material`, `set_appearance` |
| avanzado | cualquier operación, receta, código, guía | `run_operation`, `describe_operation`, `get_recipe`, `execute_code` |

Hay más grupos (sólidos, modificar…): el catálogo de herramientas del servidor es la lista completa y
cada una trae su descripción y sus argumentos.

## Temas

- `flujo`: el ciclo de trabajo (mirar, hacer, ver la imagen, medir, guardar), unidades, ids y errores.
- `selectores`: elegir caras y aristas (`>Z`, `|Z`, `%CIRCLE`…) para empalmes, chaflanes, vaciados, agujeros y bocetos sobre cara.
- **texto_vectores**: fuentes, texto de boceto con todas sus opciones, insertar SVG / DXF y vectorizar imágenes.

Pedí un tema con `get_guide(topic="flujo")`.

## Bocetos (grupo boceto), lo mismo que el editor de la interfaz

- Dibujar: líneas, rectángulo, círculo, arco, spline, `draw_point`, `draw_conic`, `draw_ellipse`, `draw_slot`,
  `draw_tangent_circle`, `draw_blend_curve`; `create_polygon` con **fully_constrained** queda con dof 0.
- Modificar (sobre lo que muestra `get_sketch`): `sketch_fillet`, `sketch_chamfer`, `trim_sketch_curve`
  (trim / extend / break), `offset_sketch_curves` (desfase con cota), `mirror_sketch`, `sketch_rectangular_pattern`,
  `sketch_circular_pattern`, `project_to_sketch`, `set_line_type` (construcción / línea central).
- Acotar: `add_constraint`, `add_dimension`, `edit_dimension` (cambiar una cota), `auto_constrain`;
  `move_sketch_point` y `delete_sketch_entities` (también borra restricciones y cotas).

## Reglas que valen siempre

- Unidades: milímetros y grados. Un número solo se toma como mm o grados según el campo.
- Una herramienta que modifica es UN paso de deshacer y es atómica: si falla, el documento queda igual.
- Ante la duda de qué operación usar o cómo se llaman sus parámetros: `list_operation_types` y
  `describe_operation`.
