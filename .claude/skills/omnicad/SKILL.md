---
name: omnicad
description: "Diseñar, modelar o modificar piezas 3D con OmniCAD, el CAD paramétrico de este proyecto (bocetos, extruir, empalmes, agujeros, vaciado, parámetros, exportar a STL o STEP), usando su servidor MCP o la CLI omnicad. Usala siempre que el pedido sea crear o cambiar una pieza o un modelo 3D, aunque no diga OmniCAD: 'diseñá un soporte en L', 'modelá una caja con tapa vaciada', 'hacé una brida con agujeros en círculo', 'agregale un empalme de 3 mm', 'exportame esto a STL', 'design a bracket', 'model a 3D part', 'make a CAD model', 'export to STEP'. También cuando pidan mejorar, arreglar o agregar una función al propio programa OmniCAD (código en este repo). NO usarla para Fusion 360 real (otro MCP), Blender o Rhino, editar mallas de IA, imágenes o planos 2D, ni slicers de impresión 3D."
---

# OmniCAD: diseñar piezas 3D (y mejorar el programa)

OmniCAD guarda el diseño como una receta (parámetros + pasos del timeline) que se recalcula entera
cada vez que algo cambia. Unidades: milímetros y grados. Cada herramienta que modifica es UN paso de
deshacer y es atómica: si falla, el documento queda igual (no hace falta deshacer).

## Qué usar: el MCP, y si no está, la CLI

1. **MCP conectado** (en Claude Code las herramientas se llaman `mcp__omnicad__<herramienta>`; en
   OpenCode llevan el nombre del servidor como prefijo): usá las herramientas directo. Con la app abierta
   y los agentes permitidos, el MCP trabaja en vivo sobre la ventana (`--modo auto`).
2. **Sin MCP**: la CLI, siempre con `--json` para leer el resultado. Si `omnicad` no está en el PATH:
   `python -m omnicad.cli` con el Python del venv de OmniCAD.
   - `omnicad tools` lista las herramientas y `omnicad describe <herramienta>` explica una.
   - `omnicad new pieza.omnicad` crea el archivo. Después, cada llamada lleva `--doc pieza.omnicad`
     (sin `--doc` el documento es temporal y se pierde): `omnicad call fillet --doc pieza.omnicad --json --args '{"edges": "|Z", "radius": 3}'`.
   - Para argumentos con `|`, `>` o comillas usá `--args` con JSON (la terminal de Windows los rompe).
   - Muchos pasos: `omnicad batch pasos.jsonl --doc pieza.omnicad` (una línea `{"tool", "args"}` por
     paso, un solo proceso, guarda una vez al final) o `omnicad run script.py --doc pieza.omnicad --save`.
   - Salida: 0 bien, 1 la herramienta falló (con `--json` trae `error_kind`), 2 error de uso.
3. Si no hay ni MCP ni CLI, no inventes: avisá que OmniCAD no está instalado (`omnicad setup` lo conecta).

## El ciclo de trabajo

Vueltas cortas. Un cambio, mirar el resultado, recién entonces el siguiente.

| Paso | Herramienta (CLI: `omnicad call <herramienta>`) |
|---|---|
| 1. Mirar | `get_scene_info` (cuerpos, bocetos, parámetros), `get_timeline` (pasos y estado). CLI: `omnicad info pieza.omnicad` |
| 2. Hacer | Medidas como parámetros (`create_parameter`; después `set_parameter`). Sólidos: `create_box`, `create_cylinder`. Con perfil: `create_sketch` o `sketch_from_spec` (boceto entero en una llamada) y `extrude` o `revolve`. Después `fillet`, `chamfer`, `shell`, `create_hole`, `rectangular_pattern`, `circular_pattern`, `point_pattern`, `path_pattern`, `multi_transform`, `mirror`, `boolean_operation`, `move_body`. Los patrones repiten cuerpos (argumento bodies) o pasos (argumento features: el agujero o el corte se repite sobre la pieza, sin booleanas aparte). Cualquier otra operación: `list_operation_types`, `describe_operation` y `run_operation` |
| 2b. Grupos especiales | Boceto completo: `draw_ellipse`, `draw_slot`, `sketch_fillet`, `trim_sketch_curve`, `offset_sketch_curves`, `mirror_sketch`, `sketch_*_pattern`, `edit_dimension`. Ensamble: `create_component`, `create_joint`, `drive_joint`, `motion_study`, `get_assembly`. Chapa: `create_base_flange`, `create_edge_flange`, `unfold`, `create_flat_pattern`, `export_flat_pattern_dxf`. Material: `set_material`, `set_appearance`, `define_material`. Malla: `tessellate`, `repair_mesh`, `clean_mesh`, `remesh`, `convert_mesh`. Engranajes y ejes: `gear_info`, `create_gear`, `create_gear_pair`, `create_shaft`. Revisar: `check_geometry`, `check_printability`, `repair_body`. Grafo (programación visual): `list_graph_nodes`, `run_graph`, `bake_graph`. `omnicad tools --group <grupo>` lista cada grupo |
| 3. Ver la imagen | `get_viewport_image` (vistas `iso`, `front`, `top`, `right`...; mirá 2 o 3 ángulos). CLI: `omnicad render pieza.omnicad vista.png --view iso` y ABRÍ el PNG con tu herramienta de lectura de imágenes |
| 4. Medir | `get_physical_properties` (volumen, caja envolvente), `measure_distance`, `measure_angle`, `check_interference` con varias piezas |
| 5. Guardar | `save_document` con ruta absoluta (la CLI guarda sola con `--doc`). Exportar: `export` o `omnicad export pieza.omnicad pieza.stl` (también `.step`, `.obj`, `.3mf`) |

Reglas que evitan rehacer trabajo:
- Comparé la imagen con lo que se pidió ANTES de seguir, y decí en una línea qué se parece y qué no.
- Verificá el número: el volumen o la caja envolvente tienen que coincidir con la cuenta que hiciste a mano.
- Boceto sobre XZ: la normal es −Y, así que extruir positivo avanza hacia −Y (`reverse` lo invierte).
- Sobre una cara, `extrude` con `cut` entra al material solo, y con `join` crece hacia afuera.
- Dos o más pasos seguidos en una sola llamada: `execute_code` con `llamar("nombre", {...})`.
- Si te equivocás en un paso que sí se aplicó: `undo` (y `redo`).
- Para la receta completa del documento: `get_recipe` y `apply_recipe`.

## Selectores de caras y aristas (estilo CadQuery)

Valen en `find_faces`, `find_edges`, `fillet`, `chamfer`, `shell`, `create_hole`, `draft`, `create_sketch`,
`sketch_from_spec`, `measure_distance` y `measure_angle`. Se evalúan sobre UN cuerpo (`body`, o el único):
con varios cuerpos, pasá `body`.

| Selector | Elige |
|---|---|
| `>Z` `<Z` | lo de más arriba o más abajo (también X e Y) |
| `\|Z` | aristas paralelas al eje; en caras, la normal paralela (tapa y base) |
| `#Z` | lo perpendicular (en una caja, las 4 caras laterales) |
| `+Z` `-Z` | caras planas con esa normal |
| `\|Z~3` `#Z~3` | lo mismo con 3° de tolerancia: lo apenas inclinado (tras un desmoldeo) |
| `%PLANE` `%CYLINDER` | tipo de CARA. Tipo de ARISTA: `%LINE` `%CIRCLE` |
| `nearest:[x,y,z]` | la más cercana a un punto |

Se combinan con `and`, `or`, `not` y paréntesis: `|Z and >X`. Ejemplos: `fillet(edges="|Z", radius=2)`,
`shell(body="Cuerpo1", faces=">Z", thickness=2)`, `create_hole(face=">Z", diameter=6, through_all=true)`.
Los ids de `find_faces` y `find_edges` (`Cuerpo1/F3`) valen solo hasta el próximo cambio del documento.

## Errores más comunes (`error_kind`)

Decidí por `error_kind`, leé `mensaje` y probá las `pistas`.

| error_kind | Qué hacer |
|---|---|
| `INVALID_ARGUMENTS` | Nombre o tipo mal puesto: `describe_operation` o `omnicad describe <herramienta>` da la firma |
| `INVALID_SELECTOR` | No se entiende el selector (o mezcla tipo de cara con tipo de arista): releé la tabla de arriba |
| `NO_MATCH` | El selector es válido pero no eligió nada: listá con `find_faces` o `find_edges` sin selector |
| `STALE_ID` | El id venció: volvé a listar o usá un selector |
| `REFERENCE_LOST` | Una cara o arista guardada ya no existe tras recalcular: volvé a elegirla con `edit_feature` |
| `PROFILE_NOT_CLOSED` | El boceto no tiene regiones cerradas: los extremos de las curvas tienen que coincidir |
| `SKETCH_OVERCONSTRAINED` | La restricción choca con otras: `get_sketch` muestra los grados de libertad |
| `NO_TARGET_BODY` | `join` o `cut` sin cuerpo donde actuar: creá uno antes o usá `new_body` |
| `OPERATION_FAILED` | Esos valores no se pueden calcular (radio que no cabe, espesor excesivo): bajalos |
| `SKETCH_NOT_FOUND` `BODY_NOT_FOUND` `FEATURE_NOT_FOUND` | La referencia no existe: `get_scene_info` o `get_timeline` listan los nombres e ids |
| `CODE_ERROR` | Falló tu código de `execute_code`: el mensaje trae la línea |
| `CODE_TIMEOUT` | Tu código de `execute_code` pasó su tiempo máximo, timeout (60 s por defecto) y se cortó; el documento no cambió |
| `APP_BUSY` | (en vivo) el usuario está en un comando: esperá unos segundos y repetí |
| `APP_NOT_RUNNING` | (en vivo) la app no escucha: abrila con los agentes permitidos o usá `--modo sin_ventana` |

## Más ayuda (no se copia acá: hay una sola versión)

- `get_guide` (con `topic` = `flujo` o `selectores`): la guía que sirve el propio programa.
- `docs/agentes/guia_diseno.md` del repo: flujo, selectores y unidades con ejemplos de piezas.
- `docs/agentes/conectar.md`: cómo conectar OmniCAD a cada cliente. `omnicad setup` lo hace por vos
  (muestra el plan y no escribe nada hasta que le pasás `--aplicar`).

## Si el pedido es mejorar el programa OmniCAD

Leé `AGENTS.md` en la raíz del repo, que manda sobre todo lo demás: reglas absolutas y mapa de carpetas.
- Operación nueva en el timeline: Receta A. Comando de la interfaz: Receta B. Herramienta nueva para
  agentes (MCP y CLI a la vez): Receta C.
- Todo en español; `nucleo`, `timeline`, `restricciones` e `io_archivos` no importan Qt.
- No digas "listo" sin correr la verificación y pegar su salida real: `omnicad dev check` (con `--json`
  trae el resumen) o la herramienta `run_checks`, que corren ruff, pytest y la prueba de humo.
- Anotá el trabajo en `PROJECT_LOG.md`. Git solo local: nada de `push` ni commits sin que te lo pidan.
