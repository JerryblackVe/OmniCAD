<!-- ARCHIVO GENERADO: no editar a mano. Regenerar con: omnicad tools --markdown --output docs/agentes/herramientas.md -->

# Herramientas de OmniCAD

> Archivo generado: no editar a mano. Regenerar con `omnicad tools --markdown --output docs/agentes/herramientas.md` (desde la raíz del repo).
> Sale del catálogo de `omnicad.api`, la misma fuente del servidor MCP y de la CLI. Un test avisa si queda viejo.

349 herramientas en 17 grupos. Unidades: mm y grados. Nombres, parámetros y claves del resultado en inglés; textos en español.
Cada llamada devuelve `{"ok": true, "result": ..., "avisos": [...]}` o `{"ok": false, "error_kind": ..., "mensaje": ..., "pistas": [...]}`.

El servidor MCP en modo en vivo o auto suma `get_mode`, que no está en el catálogo (ver `puente.md`).

| Grupo | Herramientas | Para qué |
|---|---|---|
| [documento](#grupo-documento) | 47 | Archivo, escena, timeline y deshacer. |
| [parametros](#grupo-parametros) | 6 | Medidas con nombre que gobiernan el modelo. |
| [boceto](#grupo-boceto) | 61 | Bocetos 2D: geometría, restricciones y cotas. |
| [vectores](#grupo-vectores) | 17 | Texto y vectores: fuentes, texto de boceto, SVG, DXF e imágenes vectorizadas. |
| [solido](#grupo-solido) | 75 | Sólidos: extruir, revolucionar, primitivas, empalmes, agujeros y patrones. |
| [chapa](#grupo-chapa) | 18 | Chapa metálica: reglas, pestañas, dobladillo, plegar, desplegar, desgarro, patrón plano y DXF. |
| [malla](#grupo-malla) | 17 | Mallas de triángulos: teselar, reparar, limpiar, reducir, remallar, suavizar, vaciar, cortar, combinar, separar y convertir a sólido (traer un .stl/.obj/.3mf/.ply: insert_file). |
| [ensamble](#grupo-ensamble) | 11 | Ensamble: componentes, uniones, accionar, límites, grupos rígidos, vínculos y estudio de movimiento. |
| [material](#grupo-material) | 12 | Materiales físicos (densidad para la masa), materiales propios y aspecto de los cuerpos. |
| [inspeccion](#grupo-inspeccion) | 23 | Ver y medir el resultado. |
| [animacion](#grupo-animacion) | 15 | Espacio ANIMACIÓN: guiones gráficos, acciones, explosión automática, cámara, cuadros y video. |
| [dibujo](#grupo-dibujo) | 18 | Espacio DIBUJO: hoja y cajetín, vistas (base, proyectada, sección, detalle), cotas, notas y exportación. |
| [render](#grupo-render) | 5 | Espacio RENDERIZAR: entornos, escena, cámara guardada e imagen final del render. |
| [avanzado](#grupo-avanzado) | 8 | Cualquier operación, receta, código y guía. |
| [grafo](#grupo-grafo) | 3 | Programación visual sin ventana (tipo Grasshopper): correr grafos de nodos y hornearlos en el timeline. |
| [asistente](#grupo-asistente) | 8 | Asistente IA: su configuración, pedidos sin ventana (gastan en la API) y el historial de chats (en el MCP, solo con --toolsets; en la CLI, `omnicad assistant_ask`). |
| [dev](#grupo-dev) | 5 | Desarrollo del programa (en el MCP, solo con --dev; en la CLI, `omnicad dev`). |

## Grupo documento

Archivo, escena, timeline y deshacer.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`get_scene_info`](#get_scene_info) | no | Resumen del documento: nombre, archivo, cambios sin guardar, unidades, cuerpos (id, nombre, tipo, volumen mm³, área mm², caja envolvente), bocetos (plano y perfiles), componentes (id, nombre, fijo, cuerpos, matriz 4×4 en mm), uniones (tipo, componente 1 que se mueve y 2, valores: rotation en grados, slide en mm), grupos rígidos, cantidad de pasos del timeline y parámetros. |
| [`select_bodies`](#select_bodies) | no | Selecciona cuerpos en la ventana y los revela en el navegador. |
| [`set_document_units`](#set_document_units) | sí | Elige las unidades con que la app MUESTRA las medidas del documento (el menú «Unidades» de la barra de abajo): longitud en mm, cm, m, in o ft y masa en g, kg o lb. |
| [`recompute_all`](#recompute_all) | sí | Calcular todo (Ctrl+B; Compute All de Fusion): vuelve a ejecutar TODOS los pasos del timeline, sin reusar los resultados guardados de los pasos que no cambiaron. |
| [`set_geometry_engine`](#set_geometry_engine) | sí | Elige el motor geométrico (Preferencias › Geometría): «opencascade» (el de siempre) u «omnikernel» (nativo, en Rust). |
| [`new_document`](#new_document) | sí | Empieza un documento vacío (o el modelo de ejemplo con example=true) en lugar del actual. |
| [`open_document`](#open_document) | sí | Abre un archivo y lo deja como documento activo: proyecto .omnicad (o .fclone), o como documento nuevo con un paso de importación STEP (.step/.stp, con nombres, colores y componentes), IGES (.iges/.igs), malla (.stl, .obj, .3mf, .ply), DXF (boceto en XY), BREP (.brep/.brp, como operación base) o Fusion 360 (.f3d, .f3z: se leen sus cuerpos SIN Fusion, como operación base, cada componente en su lugar del ensamblaje y con una copia ligera por cada repetición; el historial, los parámetros y los nombres de los cuerpos no se leen; inspect_f3d cuenta qué trae). |
| [`insert_file`](#insert_file) | sí | Inserta un archivo en el documento ACTUAL como un paso nuevo del timeline (Insertar de Fusion): STEP .step/.stp (con nombres, colores y componentes), IGES .iges/.igs, malla .stl/.obj/.3mf/.ply, B-rep de OpenCascade .brep/.brp, Fusion 360 .f3d/.f3z (sus cuerpos, leídos sin Fusion y con cada componente en su lugar) u otro diseño .omnicad/.fclone (entra como componente). |
| [`insert_derive`](#insert_derive) | sí | Deriva de OTRO proyecto .omnicad al documento actual (Insert Derive de Fusion): los cuerpos, bocetos y parámetros elegidos entran como UN paso del timeline que guarda la ruta del origen y qué se derivó; al recalcular vuelve a leer el origen (si cambió, se actualiza; si falta, el paso queda con error). |
| [`inspect_f3d`](#inspect_f3d) | no | Mira un archivo de Fusion 360 (.f3d o .f3z) SIN abrirlo: cuántos cuerpos guarda su geometría tal cual (bodies_stored, cada uno en las coordenadas de su componente) y cuántos salen al poner cada componente en su lugar del ensamblaje (bodies_placed), con el volumen de uno y otro (mm³), qué componentes se mueven y cuáles tienen copias (instancias que comparten la geometría), y lo que se vio en la escena del archivo. open_document e insert_file abren el archivo con los cuerpos ya ubicados. |
| [`save_document`](#save_document) | no | Guarda el documento como proyecto .omnicad. |
| [`export`](#export) | no | Exporta cuerpos a un archivo; el formato sale de la extensión: .stl, .obj, .3mf, .ply (mallas), .glb/.gltf (glTF 2.0 para web y realidad aumentada: malla con el color y el acabado de cada cuerpo como material PBR, en metros y con Y arriba), .step/.stp, .iges/.igs, .brep (sólidos exactos) o .dxf (patrón plano de un cuerpo de chapa). |
| [`undo`](#undo) | sí | Deshace el último cambio del documento (cada herramienta que modifica es un paso). |
| [`redo`](#redo) | sí | Rehace el último cambio deshecho. |
| [`get_timeline`](#get_timeline) | no | Lista los pasos del timeline en orden: índice, id, tipo, nombre, si está suprimido, estado (ok, warning, error, suppressed, rolled_back), mensaje, parámetros tal como se guardaron (params: expresiones como «5 * placa»), cuánto da cada expresión con los parámetros actuales (values, en mm o grados) y, en primitivas y Mover, qué campo guardado corresponde a cada argumento de la herramienta (aliases: length → ancho = X, width → largo = Y…), que edit_feature también acepta. |
| [`edit_feature`](#edit_feature) | sí | Cambia parámetros de un paso del timeline (conserva su id) y recalcula. |
| [`suppress_feature`](#suppress_feature) | sí | Suprime o reactiva un paso del timeline (suprimido = no se calcula). |
| [`delete_feature`](#delete_feature) | sí | Borra un paso del timeline. |
| [`rename`](#rename) | sí | Renombra un paso del timeline o un cuerpo. |
| [`list_recoverable_documents`](#list_recoverable_documents) | no | Lista los autoguardados pendientes de recuperar (cambios que no se llegaron a guardar): los de documentos «Sin título» y, si se pasan `recent`, el autoguardado más nuevo de cada uno de esos proyectos. |
| [`recover_document`](#recover_document) | sí | Recupera una copia de autoguardado y la deja como documento activo, como el botón Abrir de «Documentos recuperados»: huérfanos entran como «Recuperado» sin ruta; con project, guardar a mano pisa el proyecto original. |
| [`discard_recoverable_document`](#discard_recoverable_document) | no | Suprime una copia de autoguardado de la lista de documentos recuperables (el botón Suprimir de «Documentos recuperados»). |
| [`get_preferences`](#get_preferences) | no | Consulta las preferencias autorizadas, sus valores por defecto y opciones válidas. |
| [`set_preference`](#set_preference) | sí | Valida y guarda una preferencia autorizada. |
| [`set_decal`](#set_decal) | sí | Crea o edita una calcomanía sobre una cara, con tamaño, proporción, caras tangentes, opacidad, posición, giro y volteos. |
| [`decal_view`](#decal_view) | no | Opera una calcomanía como el menú de su fila en el navegador: edit reabre su panel con sus valores (Editar calcomanía), find_in_window la encuadra, find_in_timeline la encuentra en la secuencia temporal y replace_image cambia su archivo de imagen (queda embebido) sin tocar el resto. |
| [`manage_configurations`](#manage_configurations) | sí | Consulta y edita la tabla de variantes de CONFIGURAR. Solo apply aplica parámetros y supresiones; cada edición o aplicación es un deshacer. |
| [`manage_comments`](#manage_comments) | sí | Lista, agrega o borra comentarios del proyecto. |
| [`list_recent_documents`](#list_recent_documents) | no | Lista los proyectos recientes existentes, en el orden del panel de datos. |
| [`export_mesh`](#export_mesh) | no | Guardar como malla: 3MF, STL binario/ASCII u OBJ, unidades, un archivo o uno por cuerpo y refinado con recuento de triángulos. |
| [`get_browser_state`](#get_browser_state) | no | Lista los grupos y conjuntos de selección guardados en el navegador y los bocetos con su estado, como los marca el navegador: status (fully_constrained = candado, over_constrained = marca roja de conflicto, under_constrained) y dof (grados de libertad). |
| [`manage_browser`](#manage_browser) | sí | Organiza cuerpos, bocetos y calcomanías: crea grupos y conjuntos de selección, mueve elementos entre grupos, renombra o suprime un grupo (sin borrar su contenido). |
| [`set_browser_visibility`](#set_browser_visibility) | no | Muestra u oculta cuerpos, componentes, bocetos, calcomanías o grupos en vivo, y los análisis (por su nombre: se guarda en el documento, sin ventana). |
| [`set_object_visibility`](#set_object_visibility) | sí | Muestra u oculta tipos de objetos de trabajo en la vista, como Visibilidad del objeto del menú de visualización: planos, ejes y punto de origen, planos, ejes y puntos de usuario, bocetos, sistemas de coordenadas, orígenes y ejes de unión y uniones. |
| [`find_in_window`](#find_in_window) | no | Selecciona cuerpos, los encuadra en la ventana y resalta su paso creador en el timeline, como Buscar en la ventana del navegador. |
| [`set_body_opacity`](#set_body_opacity) | sí | Cambia el Control de opacidad de cuerpos del navegador. |
| [`isolate_bodies`](#isolate_bodies) | sí | Muestra solo los cuerpos elegidos; restore vuelve a mostrar todos. |
| [`sketch_view`](#sketch_view) | no | Opera el boceto en la ventana: editar, seleccionar su plano, mirar de frente, encuadrar, encontrar en el timeline, terminar el boceto (finish: sale del editor y guarda; finish_with_auto_constrain: lo restringe automáticamente antes, y si no puede lo termina igual) o mostrar/ocultar las opciones de la paleta del boceto (perfil, cotas, proyectadas, construcción, rejilla, forzar a la rejilla, corte, puntos y restricciones). |
| [`manage_command_presets`](#manage_command_presets) | no | Preajustes de los diálogos de comandos (Nervio, Red, Agujero…; Fusion: Create and use presets): valores guardados con un nombre para volver a usarlos. |
| [`manage_selection_sets`](#manage_selection_sets) | sí | Conjuntos de selección guardados en el diseño (Seleccionar › Crear conjunto de selección): guarda cuerpos, caras o aristas bajo un nombre, los vuelve a elegir, les suma objetos (update) o los borra. |
| [`select_by_boundary`](#select_by_boundary) | no | Elige los objetos que quedan dentro o fuera de un límite 3D (Seleccionar › Herramientas de selección › Por límite): una caja, un cilindro (eje X) o una esfera centrada en un cuerpo o en un punto. |
| [`select_by_seed_and_boundary`](#select_by_seed_and_boundary) | no | Elige las caras de un cuerpo que hay entre unos objetos límite y una cara semilla (Seleccionar › Herramientas de selección › Semilla y límite): desde la semilla se avanza de cara en cara sin cruzar las caras ni las aristas límite. |
| [`move_feature`](#move_feature) | sí | Mueve un paso del timeline a otro índice (como arrastrarlo en la app). |
| [`set_marker`](#set_marker) | sí | Mueve el marcador del timeline (Fusion: «Rodar marcador aquí» del menú contextual). |
| [`get_profile_sketches`](#get_profile_sketches) | no | Bocetos que usa un paso del timeline (perfiles de una extrusión o revolución, ruta de un barrido…), en orden: lo mismo que abre «Editar boceto de perfil» en el timeline. |
| [`get_selection`](#get_selection) | no | Lee lo que la persona tiene elegido en la ventana: cuerpos, caras, aristas, perfiles, bocetos, planos… Cada elemento trae su referencia persistente (ref), que sirve como argumento de las herramientas que reciben referencias. |
| [`select_entities`](#select_entities) | no | Elige en la ventana cuerpos, caras, aristas o perfiles de boceto, por el mismo camino que el clic: quedan resaltados y en el navegador. |

### `get_scene_info`

Resumen del documento: nombre, archivo, cambios sin guardar, unidades, cuerpos (id, nombre, tipo, volumen mm³, área mm², caja envolvente), bocetos (plano y perfiles), componentes (id, nombre, fijo, cuerpos, matriz 4×4 en mm), uniones (tipo, componente 1 que se mueve y 2, valores: rotation en grados, slide en mm), grupos rígidos, cantidad de pasos del timeline y parámetros. Con summary=true devuelve solo nombres y cantidades (corto, para modelos grandes).

- Modifica el documento: no.
- Parámetros:
  - `summary` (true/false; opcional, por defecto `false`): true devuelve solo nombre, ruta, unidades, cuerpos (id, nombre, tipo), bocetos (id, nombre) y cantidades.
- CLI: `omnicad call get_scene_info --doc pieza.omnicad`

### `select_bodies`

Selecciona cuerpos en la ventana y los revela en el navegador. Solo en vivo; una lista vacía limpia la selección. No cambia el documento.

- Modifica el documento: no.
- Parámetros:
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos; [] limpia la selección. Omitido con filtros = todos; sin filtros = ninguno.
  - `by_name` (texto; opcional, por defecto `null`): parte del nombre o patrón con * y ?, sin distinguir mayúsculas; se combina con los demás filtros.
  - `by_size` (objeto; opcional, por defecto `null`): límites inclusivos {"min": mm, "max": mm} de la diagonal de la caja envolvente; ambos opcionales.
  - `invert` (true/false; opcional, por defecto `false`): true selecciona el complemento de los cuerpos elegidos por bodies y los filtros.
- CLI: `omnicad call select_bodies --doc pieza.omnicad`

### `set_document_units`

Elige las unidades con que la app MUESTRA las medidas del documento (el menú «Unidades» de la barra de abajo): longitud en mm, cm, m, in o ft y masa en g, kg o lb. Se guardan con el proyecto. No cambia el modelo ni los números de la API, que siguen en mm y g; get_scene_info las informa en display_units. Sin parámetros solo las consulta.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `length` ("mm" | "cm" | "m" | "in" | "ft" o null; opcional, por defecto `null`): unidad de longitud para mostrar (omitido o null = no cambia).
  - `mass` ("g" | "kg" | "lb" o null; opcional, por defecto `null`): unidad de masa para mostrar (omitido o null = no cambia).
- CLI: `omnicad call set_document_units --doc pieza.omnicad`

### `recompute_all`

Calcular todo (Ctrl+B; Compute All de Fusion): vuelve a ejecutar TODOS los pasos del timeline, sin reusar los resultados guardados de los pasos que no cambiaron. Sirve si algo se ve mal o para medir cuánto tarda el modelo entero. No cambia la receta.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros: ninguno.
- CLI: `omnicad call recompute_all --doc pieza.omnicad`

### `set_geometry_engine`

Elige el motor geométrico (Preferencias › Geometría): «opencascade» (el de siempre) u «omnikernel» (nativo, en Rust). Al cambiarlo el documento se recalcula entero con el motor nuevo; lo que OmniKernel no hace todavía queda con error MOTOR_SIN_SOPORTE en su paso. Sin parámetros solo informa el motor activo y la versión de OmniKernel.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `engine` ("opencascade" | "omnikernel" o null; opcional, por defecto `null`): motor a usar desde ahora (omitido o null = no cambia).
- CLI: `omnicad call set_geometry_engine --doc pieza.omnicad`

### `new_document`

Empieza un documento vacío (o el modelo de ejemplo con example=true) en lugar del actual. Si el actual tiene cambios sin guardar falla con UNSAVED_CHANGES, salvo discard=true (los descarta).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `name` (texto; opcional, por defecto `"Sin título"`): nombre del documento nuevo (con example, vacío = «Ejemplo»).
  - `discard` (true/false; opcional, por defecto `false`): true para descartar los cambios sin guardar del documento actual.
  - `example` (true/false; opcional, por defecto `false`): true abre el modelo de ejemplo (placa con agujero, aro, parámetros y booleanos) en lugar de uno vacío, como Ayuda › Cargar ejemplo.
- CLI: `omnicad call new_document --doc pieza.omnicad`

### `open_document`

Abre un archivo y lo deja como documento activo: proyecto .omnicad (o .fclone), o como documento nuevo con un paso de importación STEP (.step/.stp, con nombres, colores y componentes), IGES (.iges/.igs), malla (.stl, .obj, .3mf, .ply), DXF (boceto en XY), BREP (.brep/.brp, como operación base) o Fusion 360 (.f3d, .f3z: se leen sus cuerpos SIN Fusion, como operación base, cada componente en su lugar del ensamblaje y con una copia ligera por cada repetición; el historial, los parámetros y los nombres de los cuerpos no se leen; inspect_f3d cuenta qué trae). Si el actual tiene cambios sin guardar falla con UNSAVED_CHANGES, salvo discard=true (los descarta). Para meter el archivo en el documento actual: insert_file.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `path` (texto; obligatorio): ruta del archivo.
  - `mesh_units` ("mm" | "cm" | "m" | "in" | "ft"; opcional, por defecto `"mm"`): unidades de un .stl, .obj o .ply (no las guardan); el .3mf trae las suyas.
  - `discard` (true/false; opcional, por defecto `false`): true para descartar los cambios sin guardar del documento actual.
  - `summary` (true/false; opcional, por defecto `false`): true devuelve solo nombres y cantidades (como get_scene_info con summary=true), no el detalle de todo.
- CLI: `omnicad call open_document --doc pieza.omnicad path=…`

### `insert_file`

Inserta un archivo en el documento ACTUAL como un paso nuevo del timeline (Insertar de Fusion): STEP .step/.stp (con nombres, colores y componentes), IGES .iges/.igs, malla .stl/.obj/.3mf/.ply, B-rep de OpenCascade .brep/.brp, Fusion 360 .f3d/.f3z (sus cuerpos, leídos sin Fusion y con cada componente en su lugar) u otro diseño .omnicad/.fclone (entra como componente). El contenido se copia dentro de la receta. Para abrirlo como documento nuevo: open_document.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `path` (texto; obligatorio): ruta del archivo a insertar.
  - `mesh_units` ("mm" | "cm" | "m" | "in" | "ft"; opcional, por defecto `"mm"`): unidades de un .stl, .obj o .ply (no las guardan); el .3mf trae las suyas.
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = «Importar archivo.ext» / «Insertar archivo».
- CLI: `omnicad call insert_file --doc pieza.omnicad path=…`

### `insert_derive`

Deriva de OTRO proyecto .omnicad al documento actual (Insert Derive de Fusion): los cuerpos, bocetos y parámetros elegidos entran como UN paso del timeline que guarda la ruta del origen y qué se derivó; al recalcular vuelve a leer el origen (si cambió, se actualiza; si falta, el paso queda con error). Los parámetros derivados se copian también al documento. A diferencia de insert_file con un .omnicad (que copia el diseño adentro), la derivación queda asociada al archivo de origen.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `source_path` (texto; obligatorio): ruta del proyecto .omnicad (o .fclone) de origen.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos del origen a derivar (get_scene_info del origen los lista).
  - `sketches` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los bocetos del origen a derivar.
  - `parameters` (lista de texto o null; opcional, por defecto `null`): nombres de los parámetros del origen a derivar; quedan también como parámetros del documento.
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = «Derivación de <archivo>».
- CLI: `omnicad call insert_derive --doc pieza.omnicad source_path=…`

### `inspect_f3d`

Mira un archivo de Fusion 360 (.f3d o .f3z) SIN abrirlo: cuántos cuerpos guarda su geometría tal cual (bodies_stored, cada uno en las coordenadas de su componente) y cuántos salen al poner cada componente en su lugar del ensamblaje (bodies_placed), con el volumen de uno y otro (mm³), qué componentes se mueven y cuáles tienen copias (instancias que comparten la geometría), y lo que se vio en la escena del archivo. open_document e insert_file abren el archivo con los cuerpos ya ubicados. Los cuerpos que no se pueden ubicar quedan donde están guardados (unplaced_bodies); los cuerpos viejos del historial que Fusion deja en el archivo y la escena no muestra no se importan (discarded_bodies). components[].name es el nombre del componente, si el archivo lo dice; components[].hidden marca los cuerpos que el diseño tiene ocultos (sin malla en la escena: open_document los abre con el ojo cerrado) y bodies_hidden los cuenta. sketches cuenta los bocetos que se leen de los perfiles del archivo (count, y curves por tipo): open_document los abre como pasos Boceto. history.operations lista las operaciones del historial de Fusion que trae el archivo (tipo, nombre en español y cantidad): NO se traducen, el modelo entra como su forma final.

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; obligatorio): ruta del archivo .f3d o .f3z.
- CLI: `omnicad call inspect_f3d --doc pieza.omnicad path=…`

### `save_document`

Guarda el documento como proyecto .omnicad. Sin path, guarda en su archivo actual. Crea las carpetas que falten (create_folders=false para que falle con FILE_NOT_FOUND). No reemplaza otro archivo existente salvo con overwrite=true.

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; opcional, por defecto `null`): ruta del archivo; si no termina en .omnicad se le agrega. Vacío = el archivo actual del documento.
  - `overwrite` (true/false; opcional, por defecto `false`): true para reemplazar un archivo existente que no es el actual.
  - `create_folders` (true/false; opcional, por defecto `true`): true (por defecto) crea las carpetas de la ruta que no existen (se avisa); false = FILE_NOT_FOUND.
- CLI: `omnicad call save_document --doc pieza.omnicad`

### `export`

Exporta cuerpos a un archivo; el formato sale de la extensión: .stl, .obj, .3mf, .ply (mallas), .glb/.gltf (glTF 2.0 para web y realidad aumentada: malla con el color y el acabado de cada cuerpo como material PBR, en metros y con Y arriba), .step/.stp, .iges/.igs, .brep (sólidos exactos) o .dxf (patrón plano de un cuerpo de chapa). Crea las carpetas que falten (create_folders=false para que falle con FILE_NOT_FOUND).

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; obligatorio): ruta del archivo a escribir.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos; vacío = todos los cuerpos del final del timeline. En .dxf, un solo cuerpo de chapa o su patrón plano (vacío = el único cuerpo de chapa que haya).
  - `overwrite` (true/false; opcional, por defecto `false`): true para reemplazar el archivo si ya existe.
  - `create_folders` (true/false; opcional, por defecto `true`): true (por defecto) crea las carpetas de la ruta que no existen (se avisa); false = FILE_NOT_FOUND.
- CLI: `omnicad call export --doc pieza.omnicad path=…`

### `undo`

Deshace el último cambio del documento (cada herramienta que modifica es un paso).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros: ninguno.
- CLI: `omnicad call undo --doc pieza.omnicad`

### `redo`

Rehace el último cambio deshecho.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros: ninguno.
- CLI: `omnicad call redo --doc pieza.omnicad`

### `get_timeline`

Lista los pasos del timeline en orden: índice, id, tipo, nombre, si está suprimido, estado (ok, warning, error, suppressed, rolled_back), mensaje, parámetros tal como se guardaron (params: expresiones como «5 * placa»), cuánto da cada expresión con los parámetros actuales (values, en mm o grados) y, en primitivas y Mover, qué campo guardado corresponde a cada argumento de la herramienta (aliases: length → ancho = X, width → largo = Y…), que edit_feature también acepta.

- Modifica el documento: no.
- Parámetros:
  - `include_params` (true/false; opcional, por defecto `true`): false para omitir los parámetros de cada paso (respuesta más corta).
- CLI: `omnicad call get_timeline --doc pieza.omnicad`

### `edit_feature`

Cambia parámetros de un paso del timeline (conserva su id) y recalcula. Si el paso u otro posterior queda con error, el cambio se descarta. Usa los nombres de get_timeline; en primitivas también acepta los de las herramientas: length (= ancho, X), width (= largo, Y), height (= alto, Z), radius (= radio), major_radius, minor_radius. En pasos Mover, pivot/pivote acepta 'center' u 'origin'. Devuelve params (lo guardado, con sus expresiones) y values (cuánto da cada una, en mm o grados). Los campos que guardan una referencia (pivote, eje, plano, cara…) aceptan la referencia guardada o las formas cortas que no dependen de la pieza terminada: "XY", "Z", "O", construcción y bocetos por id o nombre, {"sketch": …, "point" | "curve" | "profile": …}, {"body": …} y nombres de cuerpo en los campos de ids de cuerpo; no aceptan ids de find_faces ni selectores.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `feature` (texto; obligatorio): id (p. ej. "op3") o nombre del paso.
  - `params` (objeto; obligatorio): parámetros a cambiar, con los nombres que muestra get_timeline, p. ej. {"distancia": "15 mm"}.
- CLI: `omnicad call edit_feature --doc pieza.omnicad feature=… params=…`

### `suppress_feature`

Suprime o reactiva un paso del timeline (suprimido = no se calcula).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `feature` (texto; obligatorio): id o nombre del paso.
  - `suppressed` (true/false; opcional, por defecto `true`): true para suprimir, false para reactivar.
- CLI: `omnicad call suppress_feature --doc pieza.omnicad feature=…`

### `delete_feature`

Borra un paso del timeline. No se puede si otro paso lo usa.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `feature` (texto; obligatorio): id o nombre del paso.
- CLI: `omnicad call delete_feature --doc pieza.omnicad feature=…`

### `rename`

Renombra un paso del timeline o un cuerpo.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `target` (texto; obligatorio): id o nombre actual del paso o del cuerpo.
  - `new_name` (texto; obligatorio): nombre nuevo (no vacío).
  - `kind` ("auto" | "feature" | "body"; opcional, por defecto `"auto"`): "feature" o "body" para desambiguar; "auto" busca primero entre los pasos y después entre los cuerpos.
- CLI: `omnicad call rename --doc pieza.omnicad target=… new_name=…`

### `list_recoverable_documents`

Lista los autoguardados pendientes de recuperar (cambios que no se llegaron a guardar): los de documentos «Sin título» y, si se pasan `recent`, el autoguardado más nuevo de cada uno de esos proyectos.

- Modifica el documento: no.
- Parámetros:
  - `recent` (lista de texto o null; opcional, por defecto `null`): rutas de proyectos propios que también revisar; vacío = solo los «Sin título» huérfanos.
- CLI: `omnicad call list_recoverable_documents --doc pieza.omnicad`

### `recover_document`

Recupera una copia de autoguardado y la deja como documento activo, como el botón Abrir de «Documentos recuperados»: huérfanos entran como «Recuperado» sin ruta; con project, guardar a mano pisa el proyecto original. Si el actual tiene cambios sin guardar falla con UNSAVED_CHANGES, salvo discard=true.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `path` (texto; obligatorio): ruta de la copia de autoguardado (de list_recoverable_documents).
  - `project` (texto; opcional, por defecto `null`): ruta del proyecto original si la copia era de un proyecto con ruta; vacío = huérfano.
  - `discard` (true/false; opcional, por defecto `false`): true para descartar los cambios sin guardar del documento actual.
- CLI: `omnicad call recover_document --doc pieza.omnicad path=…`

### `discard_recoverable_document`

Suprime una copia de autoguardado de la lista de documentos recuperables (el botón Suprimir de «Documentos recuperados»). Borra SOLO la copia (*.autoguardado.omnicad), nunca el proyecto guardado ni otro archivo; no cambia el documento abierto.

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; obligatorio): ruta de la copia de autoguardado (de list_recoverable_documents).
- CLI: `omnicad call discard_recoverable_document --doc pieza.omnicad path=…`

### `get_preferences`

Consulta las preferencias autorizadas, sus valores por defecto y opciones válidas.

- Modifica el documento: no.
- Parámetros:
  - `keys` (lista de texto o null; opcional, por defecto `null`): claves a consultar; omitido devuelve toda la lista blanca de preferencias.
- CLI: `omnicad call get_preferences --doc pieza.omnicad`

### `set_preference`

Valida y guarda una preferencia autorizada. No modifica el documento ni entra en deshacer; los ajustes se usan cuando la aplicación los relee.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `key` (texto; obligatorio): clave autorizada devuelta por get_preferences; permisos, motor, temas y rutas están prohibidos.
  - `value` (texto o entero o true/false; obligatorio): valor del tipo y de las opciones indicados por get_preferences.
- CLI: `omnicad call set_preference --doc pieza.omnicad key=… value=…`

### `set_decal`

Crea o edita una calcomanía sobre una cara, con tamaño, proporción, caras tangentes, opacidad, posición, giro y volteos. La imagen queda embebida. El factor de escala multiplica uniformemente anchura y altura. En cilindros usa el desarrollo por arco; en otras caras, proyección tangente.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `image` (texto; opcional, por defecto `null`): ruta de imagen PNG/JPEG/BMP/TIFF; omitida al editar conserva la embebida.
  - `face` (texto; opcional, por defecto `null`): selector o id de UNA cara; omitida al editar conserva su referencia.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que se evalúa el selector de face.
  - `feature` (texto; opcional, por defecto `null`): id o nombre del paso a editar; vacío crea uno.
  - `width` (número o expresión; opcional, por defecto `null`): anchura en mm; omitida al crear ajusta la imagen dentro de la cara.
  - `height` (número o expresión; opcional, por defecto `null`): altura en mm; con keep_aspect ajusta también la anchura.
  - `keep_aspect` (true/false; opcional, por defecto `null`): conserva la proporción de la imagen; por defecto true al crear.
  - `chain_faces` (true/false; opcional, por defecto `null`): incluye las caras tangentes encadenadas.
  - `opacity` (entero; opcional, por defecto `null`): porcentaje de opacidad (0 a 100).
  - `use_opacity` (true/false; opcional, por defecto `null`): false ignora el porcentaje y usa 100 por ciento.
  - `x` (número o expresión; opcional, por defecto `null`): distancia X sobre la cara, en mm.
  - `y` (número o expresión; opcional, por defecto `null`): distancia Y sobre la cara, en mm.
  - `angle` (número o expresión; opcional, por defecto `null`): ángulo Z en grados.
  - `flip_h` (true/false; opcional, por defecto `null`): volteo horizontal de imagen.
  - `flip_v` (true/false; opcional, por defecto `null`): volteo vertical de imagen.
  - `scale` (número o expresión; opcional, por defecto `null`): factor uniforme positivo sobre anchura y altura; 1 conserva el tamaño (también con keep_aspect=false).
  - `name` (texto; opcional, por defecto `null`): nombre en el navegador (carpeta Calcomanías); omitido al crear toma el de la imagen, como Fusion.
- CLI: `omnicad call set_decal --doc pieza.omnicad`

### `decal_view`

Opera una calcomanía como el menú de su fila en el navegador: edit reabre su panel con sus valores (Editar calcomanía), find_in_window la encuadra, find_in_timeline la encuentra en la secuencia temporal y replace_image cambia su archivo de imagen (queda embebido) sin tocar el resto. Para suprimirla usá delete_feature, para renombrarla rename, para ocultarla set_browser_visibility.

- Modifica el documento: no.
- Parámetros:
  - `decal` (texto; obligatorio): id o nombre de la calcomanía.
  - `action` ("edit" | "find_in_window" | "find_in_timeline" | "replace_image"; obligatorio): edit, find_in_window, find_in_timeline o replace_image.
  - `image` (texto; opcional, por defecto `null`): ruta de la imagen nueva (solo con replace_image).
- CLI: `omnicad call decal_view --doc pieza.omnicad decal=… action=…`

### `manage_configurations`

Consulta y edita la tabla de variantes de CONFIGURAR. Solo apply aplica parámetros y supresiones; cada edición o aplicación es un deshacer.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `action` ("get" | "set" | "add_row" | "delete_row" | "apply" | "clear"; opcional, por defecto `"get"`): get consulta; set reemplaza; add_row agrega; delete_row borra; apply activa; clear vacía la tabla.
  - `columns` (lista de objeto o null; opcional, por defecto `null`): columnas para set: {"type": "parameter", "name": parámetro} o {"type": "suppress", "feature": id o nombre de paso}.
  - `rows` (lista de objeto o null; opcional, por defecto `null`): filas para set: [{"name": nombre, "values": [expresión o sí/no por columna]}].
  - `row` (texto; opcional, por defecto `null`): nombre de la fila a agregar, borrar o aplicar.
  - `values` (lista; opcional, por defecto `null`): valores por columna para add_row.
  - `active` (texto; opcional, por defecto `null`): nombre activo al guardar set; omitido = sin fila activa. set solo guarda la tabla, no aplica la fila.
- CLI: `omnicad call manage_configurations --doc pieza.omnicad`

### `manage_comments`

Lista, agrega o borra comentarios del proyecto. Se guardan con el diseño, pero no entran en deshacer.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `action` ("list" | "add" | "delete"; opcional, por defecto `"list"`): list consulta, add agrega texto y delete borra por índice.
  - `text` (texto; opcional, por defecto `null`): texto no vacío del comentario para add.
  - `index` (entero; opcional, por defecto `null`): índice del comentario para delete (desde cero).
- CLI: `omnicad call manage_comments --doc pieza.omnicad`

### `list_recent_documents`

Lista los proyectos recientes existentes, en el orden del panel de datos.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call list_recent_documents --doc pieza.omnicad`

### `export_mesh`

Guardar como malla: 3MF, STL binario/ASCII u OBJ, unidades, un archivo o uno por cuerpo y refinado con recuento de triángulos. Las mallas existentes conservan sus facetas; los controles personalizados de arista y aspecto también las subdividen. Con purpose=print_utility abre además el archivo en una utilidad de impresión (slicer) instalada.

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; obligatorio): archivo de destino con extensión correspondiente al formato (.3mf, .stl u .obj).
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos; vacío = todos los del modelo, sin patrones planos.
  - `format` ("3mf" | "stl_binario" | "stl_ascii" | "obj"; opcional, por defecto `"stl_binario"`): 3mf, stl_binario, stl_ascii u obj.
  - `units` ("mm" | "cm" | "m" | "in" | "ft"; opcional, por defecto `"mm"`): unidad del archivo: mm, cm, m, in o ft; el modelo sigue en mm.
  - `structure` ("un_archivo" | "uno_por_cuerpo"; opcional, por defecto `"un_archivo"`): un_archivo o uno_por_cuerpo; los separados llevan índice y nombre del cuerpo.
  - `refinement` ("bajo" | "medio" | "alto" | "personalizado"; opcional, por defecto `"personalizado"`): bajo, medio, alto o personalizado; solo este último usa los cuatro controles numéricos.
  - `surface_deviation` (número; opcional, por defecto `0.02`): desviación máxima de superficie en mm (por defecto 0,02).
  - `normal_deviation` (número; opcional, por defecto `17.188733853924695`): desviación angular en grados (por defecto 0,3 radianes expresados en grados).
  - `maximum_edge_length` (número; opcional, por defecto `0.0`): longitud máxima de arista en mm; 0 = sin límite.
  - `aspect_ratio` (número; opcional, por defecto `0.0`): arista mayor / altura menor, mayor que 1,154701; 0 = sin límite.
  - `overwrite` (true/false; opcional, por defecto `false`): true permite reemplazar archivos existentes; se comprueban todos antes de escribir.
  - `create_folders` (true/false; opcional, por defecto `true`): true crea las carpetas que faltan; false falla si la carpeta no existe.
  - `purpose` ("export" | "print_utility"; opcional, por defecto `"export"`): export solo guarda el archivo; print_utility lo guarda y lo abre en la utilidad de impresión.
  - `application` (texto; opcional, por defecto `""`): con print_utility, nombre de una utilidad instalada (OrcaSlicer, PrusaSlicer, Bambu Studio, UltiMaker Cura, Creality Print) o ruta de un programa (Personalizada); vacío = la primera instalada. Sin ninguna, solo guarda y avisa.
- CLI: `omnicad call export_mesh --doc pieza.omnicad path=…`

### `get_browser_state`

Lista los grupos y conjuntos de selección guardados en el navegador y los bocetos con su estado, como los marca el navegador: status (fully_constrained = candado, over_constrained = marca roja de conflicto, under_constrained) y dof (grados de libertad). Qué choca: get_sketch › conflicts.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call get_browser_state --doc pieza.omnicad`

### `manage_browser`

Organiza cuerpos, bocetos y calcomanías: crea grupos y conjuntos de selección, mueve elementos entre grupos, renombra o suprime un grupo (sin borrar su contenido). Se guarda en el proyecto y admite deshacer.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `action` ("create_group" | "create_set" | "move" | "rename_group" | "delete_group"; obligatorio): create_group, create_set, move, rename_group o delete_group.
  - `items` (lista de texto o null; opcional, por defecto `null`): ids de cuerpos, bocetos o calcomanías; los cuerpos también aceptan nombres.
  - `name` (texto; opcional, por defecto `""`): nombre del grupo o conjunto que se crea, o nombre nuevo con rename_group.
  - `group` (texto; opcional, por defecto `null`): id del grupo destino; vacío con move devuelve los elementos a su carpeta original.
- CLI: `omnicad call manage_browser --doc pieza.omnicad action=…`

### `set_browser_visibility`

Muestra u oculta cuerpos, componentes, bocetos, calcomanías o grupos en vivo, y los análisis (por su nombre: se guarda en el documento, sin ventana). Sin items, muestra todo. No modifica geometría.

- Modifica el documento: no.
- Parámetros:
  - `items` (lista de texto o null; opcional, por defecto `null`): ids de cuerpos, componentes, bocetos, calcomanías o grupos, o nombres de análisis (get_scene_info / manage_analysis los lista); vacío muestra todo.
  - `visible` (true/false; opcional, por defecto `true`): true muestra; false oculta los elementos pedidos.
- CLI: `omnicad call set_browser_visibility --doc pieza.omnicad`

### `set_object_visibility`

Muestra u oculta tipos de objetos de trabajo en la vista, como Visibilidad del objeto del menú de visualización: planos, ejes y punto de origen, planos, ejes y puntos de usuario, bocetos, sistemas de coordenadas, orígenes y ejes de unión y uniones. El estado se guarda con el documento (doc.espacios['visor']) y la ventana en vivo lo aplica. Admite deshacer.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `types` (lista de "planos_origen" | "ejes_origen" | "punto_origen" | "planos_usuario" | "ejes_usuario" | "puntos_usuario" | "bocetos" | "scu" | "origenes_union" | "ejes_union" | "uniones" | "all" o null; opcional, por defecto `null`): tipos de objeto: planos_origen, ejes_origen, punto_origen, planos_usuario, ejes_usuario, puntos_usuario, bocetos, scu, origenes_union, ejes_union, uniones, o "all" (todos); vacío = solo consulta el estado.
  - `visible` (true/false; opcional, por defecto `true`): true muestra esos tipos; false los oculta.
- CLI: `omnicad call set_object_visibility --doc pieza.omnicad`

### `find_in_window`

Selecciona cuerpos, los encuadra en la ventana y resalta su paso creador en el timeline, como Buscar en la ventana del navegador. Necesita la app en vivo.

- Modifica el documento: no.
- Parámetros:
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de cuerpos; omitido o vacío busca todos los cuerpos del componente raíz.
- CLI: `omnicad call find_in_window --doc pieza.omnicad`

### `set_body_opacity`

Cambia el Control de opacidad de cuerpos del navegador. Sin cuerpos, se aplica a todos los del componente raíz. Admite deshacer.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `opacity` (número; obligatorio): porcentaje de opacidad entre 0 y 100; 100 quita la anulación de opacidad.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de cuerpos; omitido o vacío cambia todos los cuerpos del componente raíz.
- CLI: `omnicad call set_body_opacity --doc pieza.omnicad opacity=…`

### `isolate_bodies`

Muestra solo los cuerpos elegidos; restore vuelve a mostrar todos. Guarda la visibilidad del navegador y admite deshacer.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (lista de texto o null; opcional, por defecto `null`): nombres o ids de los cuerpos que deben quedar visibles.
  - `restore` (true/false; opcional, por defecto `false`): true vuelve a mostrar todos los cuerpos.
- CLI: `omnicad call isolate_bodies --doc pieza.omnicad`

### `sketch_view`

Opera el boceto en la ventana: editar, seleccionar su plano, mirar de frente, encuadrar, encontrar en el timeline, terminar el boceto (finish: sale del editor y guarda; finish_with_auto_constrain: lo restringe automáticamente antes, y si no puede lo termina igual) o mostrar/ocultar las opciones de la paleta del boceto (perfil, cotas, proyectadas, construcción, rejilla, forzar a la rejilla, corte, puntos y restricciones). Las opciones y finish solo están disponibles mientras se edita ese boceto.

- Modifica el documento: no.
- Parámetros:
  - `sketch` (texto; obligatorio): id o nombre del boceto.
  - `action` ("edit" | "select_plane" | "look_at" | "find_in_window" | "find_in_timeline" | "finish" | "finish_with_auto_constrain" | "profile" | "dimensions" | "projected" | "construction" | "grid" | "snap" | "cut" | "points" | "constraints"; obligatorio): edit, select_plane, look_at, find_in_window, find_in_timeline, finish (terminar el boceto), finish_with_auto_constrain (AutoConstrain y terminar), o una opción de la paleta: profile, dimensions, projected, construction, grid (rejilla del boceto), snap (forzar), cut (corte), points o constraints.
  - `visible` (true/false; opcional, por defecto `null`): estado de la opción de la paleta; omitido la alterna (solo las acciones de opción).
- CLI: `omnicad call sketch_view --doc pieza.omnicad sketch=… action=…`

### `manage_command_presets`

Preajustes de los diálogos de comandos (Nervio, Red, Agujero…; Fusion: Create and use presets): valores guardados con un nombre para volver a usarlos. Se guardan solo en esta PC, no en el diseño. Cada preajuste es un dict {campo del diálogo: valor} con texto, números o casillas; lo que se elige en la vista no se guarda. action=list muestra los nombres y el predeterminado; get devuelve los valores de uno (para pasarlos a la herramienta del comando); save crea o actualiza; rename y delete; set_default elige qué trae el diálogo al abrirse (factory, last_used o el nombre de un preajuste).

- Modifica el documento: no.
- Parámetros:
  - `command` (texto; obligatorio): clave del comando de la ventana (la de la cinta: "nervio", "red", "agujero", "saliente"…).
  - `action` ("list" | "get" | "save" | "rename" | "delete" | "set_default"; obligatorio): list, get, save, rename, delete o set_default.
  - `name` (texto; opcional, por defecto `""`): nombre del preajuste (get, save, rename, delete).
  - `values` (objeto; opcional, por defecto `null`): con save, los valores del diálogo {campo: valor}; los que no son texto, número o casilla se descartan.
  - `new_name` (texto; opcional, por defecto `""`): con rename, el nombre nuevo.
  - `default` (texto; opcional, por defecto `""`): con set_default: factory, last_used o el nombre de un preajuste existente.
- CLI: `omnicad call manage_command_presets --doc pieza.omnicad command=… action=…`

### `manage_selection_sets`

Conjuntos de selección guardados en el diseño (Seleccionar › Crear conjunto de selección): guarda cuerpos, caras o aristas bajo un nombre, los vuelve a elegir, les suma objetos (update) o los borra. Se guardan con el proyecto y cada cambio es un paso de deshacer. Una cara o arista cuya geometría cambió demasiado se cuenta en missing.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `action` ("list" | "create" | "update" | "select" | "rename" | "delete"; obligatorio): list, create (nuevo), update (suma objetos al conjunto), select (devuelve lo guardado y marca en la ventana solo los cuerpos), rename o delete.
  - `name` (texto; opcional, por defecto `""`): nombre del conjunto (en list se ignora).
  - `faces` (lista de texto o texto o null; opcional, por defecto `null`): caras a guardar: selector, ids de find_faces o lista de ambos.
  - `edges` (lista de texto o texto o null; opcional, por defecto `null`): aristas a guardar: selector, ids de find_edges o lista de ambos.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): cuerpos a guardar (ids o nombres).
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de caras y aristas; vacío = el único cuerpo.
  - `new_name` (texto; opcional, por defecto `""`): con rename, el nombre nuevo.
- CLI: `omnicad call manage_selection_sets --doc pieza.omnicad action=…`

### `select_by_boundary`

Elige los objetos que quedan dentro o fuera de un límite 3D (Seleccionar › Herramientas de selección › Por límite): una caja, un cilindro (eje X) o una esfera centrada en un cuerpo o en un punto. Cuerpos: dentro = entero dentro, intersected suma los que lo cruzan; fuera = ninguna parte dentro. Caras y aristas se deciden por su centro y sus vértices. No cambia el documento.

- Modifica el documento: no.
- Parámetros:
  - `shape` ("box" | "cylinder" | "sphere"; obligatorio): box (x_size, y_size, z_size), cylinder (length sobre X y radius) o sphere (radius).
  - `center` (texto o lista de número; obligatorio): cuerpo (id o nombre) cuyo centro de masa es el centro del límite, o un punto [x, y, z] en mm.
  - `selection` ("inside" | "outside"; opcional, por defecto `"inside"`): inside (objetos dentro) u outside (objetos fuera).
  - `intersected` (true/false; opcional, por defecto `false`): true suma también los objetos que quedan parcialmente dentro.
  - `kind` ("body" | "face" | "edge"; opcional, por defecto `"body"`): qué se elige: body, face o edge.
  - `x_size` (número; opcional, por defecto `null`): caja: largo en X, en mm.
  - `y_size` (número; opcional, por defecto `null`): caja: largo en Y, en mm.
  - `z_size` (número; opcional, por defecto `null`): caja: largo en Z, en mm.
  - `radius` (número; opcional, por defecto `null`): cilindro o esfera: radio en mm.
  - `length` (número; opcional, por defecto `null`): cilindro: largo sobre el eje X, en mm.
  - `body` (texto; opcional, por defecto `null`): con face o edge, el cuerpo donde se buscan; vacío = todos.
- CLI: `omnicad call select_by_boundary --doc pieza.omnicad shape=… center=…`

### `select_by_seed_and_boundary`

Elige las caras de un cuerpo que hay entre unos objetos límite y una cara semilla (Seleccionar › Herramientas de selección › Semilla y límite): desde la semilla se avanza de cara en cara sin cruzar las caras ni las aristas límite. Si hay agujeros entre un lado y otro, pasan los dos a menos que se incluyan sus aristas como límite. Se puede guardar con manage_selection_sets. No cambia el documento.

- Modifica el documento: no.
- Parámetros:
  - `seed` (texto; obligatorio): cara semilla (selector o id de find_faces).
  - `boundary_faces` (lista de texto o texto o null; opcional, por defecto `null`): caras límite: selector, ids o lista; la selección no las incluye ni las cruza.
  - `boundary_edges` (lista de texto o texto o null; opcional, por defecto `null`): aristas límite: selector, ids o lista; la selección no las cruza.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
- CLI: `omnicad call select_by_seed_and_boundary --doc pieza.omnicad seed=…`

### `move_feature`

Mueve un paso del timeline a otro índice (como arrastrarlo en la app). Si no se puede (un paso que depende de otro quedaría antes), falla con OPERATION_FAILED y el motivo. Es lo que usa la pista del error de empalme: reordenar los empalmes de mayor a menor radio.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `feature` (texto; obligatorio): id o nombre del paso a mover.
  - `index` (entero; obligatorio): índice nuevo (0 = primero, se recorta al final del timeline).
- CLI: `omnicad call move_feature --doc pieza.omnicad feature=… index=…`

### `set_marker`

Mueve el marcador del timeline (Fusion: «Rodar marcador aquí» del menú contextual). Lo que queda a la derecha del marcador no se calcula (estado rolled_back) hasta volver a moverlo. Indicá UNO: position, after (el marcador queda justo después de ese paso, que sí se calcula) o before (justo antes). undo lo vuelve a donde estaba. Si al avanzar un paso queda con error, se avisa (errors) pero el marcador se mueve igual (como en la app).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `position` (entero; opcional, por defecto `null`): índice del marcador: 0 = antes del primer paso; la cantidad de pasos = al final (todo calculado).
  - `after` (texto; opcional, por defecto `null`): id o nombre de un paso: el marcador queda justo después (como «Rodar marcador aquí» sobre ese paso).
  - `before` (texto; opcional, por defecto `null`): id o nombre de un paso: el marcador queda justo antes (ni ese paso ni los siguientes se calculan).
- CLI: `omnicad call set_marker --doc pieza.omnicad`

### `get_profile_sketches`

Bocetos que usa un paso del timeline (perfiles de una extrusión o revolución, ruta de un barrido…), en orden: lo mismo que abre «Editar boceto de perfil» en el timeline. Sus ids sirven como «sketch» de las herramientas de boceto (get_sketch, draw_line…); los derivados externos son de solo lectura.

- Modifica el documento: no.
- Parámetros:
  - `feature` (texto; obligatorio): id o nombre del paso (p. ej. una extrusión).
- CLI: `omnicad call get_profile_sketches --doc pieza.omnicad feature=…`

### `get_selection`

Lee lo que la persona tiene elegido en la ventana: cuerpos, caras, aristas, perfiles, bocetos, planos… Cada elemento trae su referencia persistente (ref), que sirve como argumento de las herramientas que reciben referencias. Solo en vivo; no cambia el documento.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call get_selection --doc pieza.omnicad`

### `select_entities`

Elige en la ventana cuerpos, caras, aristas o perfiles de boceto, por el mismo camino que el clic: quedan resaltados y en el navegador. Solo en vivo; no cambia el documento. Las caras y aristas se eligen con selectores (">Z", "|Z") o ids de find_faces / find_edges.

- Modifica el documento: no.
- Parámetros:
  - `kind` ("body" | "face" | "edge" | "profile"; obligatorio): body (cuerpos), face (caras), edge (aristas) o profile (perfiles de un boceto).
  - `selector` (texto o lista de texto o null; opcional, por defecto `null`): body: ids o nombres de cuerpos; face y edge: selector o ids de find_faces / find_edges (o lista). No se usa con profile.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de face y edge; vacío = el único cuerpo.
  - `sketch` (texto; opcional, por defecto `null`): profile: id o nombre del boceto.
  - `profile` (entero o lista de entero o texto; opcional, por defecto `"all"`): profile: índice, lista de índices, "all" o "largest".
  - `mode` ("replace" | "add" | "remove"; opcional, por defecto `"replace"`): replace (por defecto) cambia la selección; add suma a la actual; remove la resta.
- CLI: `omnicad call select_entities --doc pieza.omnicad kind=…`

## Grupo parametros

Medidas con nombre que gobiernan el modelo.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`get_parameters`](#get_parameters) | no | Lista los parámetros de usuario y de cotas: expresión, valor calculado, unidad (mm o deg) y qué pasos del timeline los usan. |
| [`create_parameter`](#create_parameter) | sí | Crea un parámetro de usuario. |
| [`set_parameter`](#set_parameter) | sí | Cambia la expresión, el comentario o el nombre de un parámetro existente y recalcula el modelo. |
| [`delete_parameter`](#delete_parameter) | sí | Borra un parámetro que no use ningún paso ni otro parámetro. |
| [`export_parameters`](#export_parameters) | no | Exporta parámetros a CSV (Name, Unit, Expression, Value, Comments), compatible con la tabla de parámetros de la ventana. |
| [`import_parameters`](#import_parameters) | sí | Importa parámetros CSV con validación de expresiones y unidades. merge agrega o actualiza por nombre; replace reemplaza la tabla. |

### `get_parameters`

Lista los parámetros de usuario y de cotas: expresión, valor calculado, unidad (mm o deg) y qué pasos del timeline los usan. Las cotas tienen source=sketch, sketch (id del boceto) y dimension (id de cota); sus nombres d1, d2… se pueden citar en cualquier expresión.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call get_parameters --doc pieza.omnicad`

### `create_parameter`

Crea un parámetro de usuario. Con kind=auto la magnitud sale de la expresión: con unidad de ángulo (deg, rad, °) es un ángulo; si no, una longitud en mm. kind=scalar crea un parámetro sin unidad (cantidades de un patrón, factores); kind=text guarda texto literal.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `name` (texto; obligatorio): nombre del parámetro (letras, números y '_', sin empezar con número), p. ej. "ancho".
  - `expression` (texto o entero o número; obligatorio): valor: número (mm) o expresión con unidades y otros parámetros, p. ej. "60 mm", "ancho / 2", "30 deg"; con kind=text es una cadena literal, incluidas comillas y saltos de línea.
  - `comment` (texto; opcional, por defecto `""`): comentario opcional que se ve en la tabla de parámetros.
  - `kind` ("auto" | "length" | "angle" | "scalar" | "text"; opcional, por defecto `"auto"`): auto (longitud o ángulo según la expresión), length, angle, scalar (número sin unidad) o text (texto literal; no se puede usar en expresiones numéricas).
- CLI: `omnicad call create_parameter --doc pieza.omnicad name=… expression=…`

### `set_parameter`

Cambia la expresión, el comentario o el nombre de un parámetro existente y recalcula el modelo. Si algún paso queda con error (p. ej. renombrar un parámetro que usa un paso), el cambio se descarta. Con un parámetro dN de boceto también cambia la cota y mueve su geometría; los nombres de cota son estables y no se pueden renombrar. El valor de una cota de referencia (driven) es medido y no se puede editar; se puede citar en otras expresiones.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `name` (texto; obligatorio): nombre exacto del parámetro.
  - `expression` (texto o entero o número; opcional, por defecto `null`): valor nuevo: número o expresión, p. ej. "80 mm" o "ancho * 2"; para parámetros text, cadena literal ("" la vacía); null = no cambia.
  - `comment` (texto; opcional, por defecto `null`): comentario nuevo ("" lo borra); vacío = no cambia.
  - `new_name` (texto; opcional, por defecto `null`): nombre nuevo (letras, números y '_'); falla si algún paso u otro parámetro usa el nombre actual, porque quedarían apuntando a un parámetro que ya no existe; vacío = no cambia.
- CLI: `omnicad call set_parameter --doc pieza.omnicad name=…`

### `delete_parameter`

Borra un parámetro que no use ningún paso ni otro parámetro. Para quitar un dN de boceto, borrá su cota con delete_sketch_entities; falla si una expresión ajena la usa.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `name` (texto; obligatorio): nombre exacto del parámetro.
- CLI: `omnicad call delete_parameter --doc pieza.omnicad name=…`

### `export_parameters`

Exporta parámetros a CSV (Name, Unit, Expression, Value, Comments), compatible con la tabla de parámetros de la ventana.

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; obligatorio): ruta del archivo CSV a escribir.
  - `overwrite` (true/false; opcional, por defecto `false`): true para reemplazar un archivo existente.
  - `create_folders` (true/false; opcional, por defecto `true`): true crea las carpetas que falten; false devuelve FILE_NOT_FOUND.
- CLI: `omnicad call export_parameters --doc pieza.omnicad path=…`

### `import_parameters`

Importa parámetros CSV con validación de expresiones y unidades. merge agrega o actualiza por nombre; replace reemplaza la tabla. Un solo deshacer.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `path` (texto; obligatorio): archivo CSV UTF-8, hasta 2 MB, 1000 filas y 4096 caracteres por campo; acepta las cabeceras de la ventana.
  - `mode` ("merge" | "replace"; opcional, por defecto `"merge"`): merge conserva los parámetros ajenos al CSV; replace los elimina salvo que los use el modelo.
- CLI: `omnicad call import_parameters --doc pieza.omnicad path=…`

## Grupo boceto

Bocetos 2D: geometría, restricciones y cotas.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`create_construction_plane`](#create_construction_plane) | sí | Crea un plano de construcción (CONSTRUIR › Plano). type=offset (por defecto): desfasado de un plano de origen (XY, XZ, YZ), de otro plano de construcción o de una CARA PLANA (selector o id de find_faces), sobre su normal. |
| [`create_sketch`](#create_sketch) | sí | Crea un boceto vacío sobre un plano o sobre una cara plana. |
| [`draw_line`](#draw_line) | sí | Dibuja una línea en el boceto (un paso de deshacer). |
| [`draw_rectangle`](#draw_rectangle) | sí | Dibuja un rectángulo (4 líneas con restricciones horizontal y vertical). |
| [`draw_circle`](#draw_circle) | sí | Dibuja un círculo (un paso de deshacer): por centro y radio (por defecto), por 2 puntos (los extremos de un diámetro) o por 3 puntos (points). |
| [`draw_arc`](#draw_arc) | sí | Dibuja un arco. |
| [`create_polygon`](#create_polygon) | sí | Dibuja un polígono regular de n lados (líneas iguales sobre un círculo guía de construcción, como la interfaz). |
| [`draw_spline`](#draw_spline) | sí | Dibuja una spline: de ajuste (pasa por los puntos) o de puntos de control (grado 3 o 5, necesita al menos grado+1 puntos). |
| [`add_constraint`](#add_constraint) | sí | Agrega una restricción geométrica entre entidades del boceto (ids de get_sketch: curvas y puntos). |
| [`add_dimension`](#add_dimension) | sí | Agrega una cota (dimensión) que maneja la geometría. |
| [`get_sketch`](#get_sketch) | no | Informe de un boceto: plano y su marco 3D, entidades con ids estables (coordenadas ya resueltas por el solver), puntos, restricciones, cotas con su valor, perfiles (índice, área mm², centroide, caja [min/max en coordenadas del boceto] y curvas del borde) y estado del solver en la clave `status` (fully_constrained, under_constrained, over_constrained) con los grados de libertad en `dof`. Cada punto y curva trae state: free, determined o fixed. conflicts lista los ids de restricciones/cotas cuya retirada individual resuelve el conflicto (vacía sin conflicto o si hacen falta varias retiradas). origin=0 y axes={x:-1,y:-2} son ids reservados citables en add_constraint/add_dimension; las referencias se materializan como construcción fija al citarlas y no forman perfiles. dimensions incluye name (dN), el parámetro de cada cota, sincronizado con get_parameters/set_parameter, y reference: true indica una cota driven cuyo value es la medida actual y no aporta restricciones ni reduce dof. |
| [`sketch_from_spec`](#sketch_from_spec) | sí | Crea un boceto COMPLETO en una sola llamada (un paso de deshacer): geometría, restricciones y cotas. entities: lista de {type, ...}: line{start,end}, rectangle{corner1,corner2 \| center,width,height \| origin,width,height}, circle{center,radius}, arc{center,start,sweep \| start,mid,end}, polygon{sides,radius,center,rotation,kind,fully_constrained}, ellipse{center,major_radius,minor_radius,angle}, slot{kind,points,width} (kind como en draw_slot), spline{points,spline_type,degree,closed}, point{at}, conic{start,end,vertex,rho}, text{text,...} (opciones de add_text, path_entity admite cita), midpoint_line{center,end}, polygon{kind:edge,start,end,sides,edge_points?} (sin edge_points crece a la izquierda de start→end; edge_points permite elegir el lado como create_polygon), tangent_circle{lines:[citas],x?,y?,radius?}, tangent_arc{from:cita de extremo de línea,end}. Boceto 3D (como draw_*_3d, coordenadas [x, y, z]): line_3d{start,end}, spline_3d{points,closed?}, point_3d{at}, arc_3d{start,through,end}, circle_3d{center,radius,normal?}, ellipse_3d{center,major_end,minor_radius,normal?}, rectangle_3d{corner,opposite,plane?} (citas 'id.l1..l4'), conic_3d{start,shoulder,end,rho?}, text_3d{text,origin,height?,plane?,font?}; normal vacía = [0, 0, 1], plane = xy, yz o zx (por defecto xy). |
| [`draw_ellipse`](#draw_ellipse) | sí | Dibuja una elipse (Fusion: Elipse) por centro, radio mayor, radio menor y giro del eje mayor. |
| [`draw_slot`](#draw_slot) | sí | Dibuja una ranura (Fusion: Ranura): dos lados y dos extremos redondos tangentes, más el eje de construcción. kind y points (cada uno [x, y] en mm): center_to_center = [centro de un extremo, centro del otro]; overall = [punta de un extremo, punta del otro] (largo total); center_point = [centro de la ranura, centro de un extremo]; arc_three_points = [centro de un extremo, centro del otro, un punto del arco del eje]; arc_center = [centro del arco, centro de un extremo, punto en la dirección del otro extremo] (antihorario). width es el ancho total. |
| [`draw_point`](#draw_point) | sí | Agrega un punto suelto al boceto (Fusion: Punto): sirve de referencia para cotas, restricciones, agujeros o el centro de un patrón circular. |
| [`draw_conic`](#draw_conic) | sí | Dibuja una curva cónica (Fusion: Curva cónica) entre dos extremos, con el vértice (donde se cruzan las tangentes de los extremos) y Rho: 0.5 = parábola, menos = elipse, más = hipérbola. |
| [`draw_tangent_circle`](#draw_tangent_circle) | sí | Dibuja un círculo tangente a 2 o 3 líneas del boceto (Fusion: Círculo de 2 / 3 tangentes) y le agrega las restricciones de tangencia. |
| [`draw_blend_curve`](#draw_blend_curve) | sí | Une los extremos de dos curvas abiertas con una spline suave (Fusion: Curva de fusión), tangente (G1) o con curvatura continua (G2) en las dos uniones. |
| [`sketch_fillet`](#sketch_fillet) | sí | Empalme de boceto (Fusion: Empalme en el boceto): redondea la esquina entre dos curvas (líneas, arcos o círculos) con un arco tangente; recorta las curvas, agrega las tangencias y la cota de radio. radius puede ser una expresión con parámetros (queda en la cota). |
| [`sketch_chamfer`](#sketch_chamfer) | sí | Chaflán de boceto (Fusion: Chaflán en el boceto) entre dos líneas: de distancias iguales (distance), de dos distancias (distance y distance2) o de distancia y ángulo (distance y angle). |
| [`trim_sketch_curve`](#trim_sketch_curve) | sí | Recortar, alargar o partir una curva del boceto (Fusion: Recortar / Alargar / Partir). (x, y) es el lugar del clic, sobre la curva o cerca: trim quita el tramo de la curva que contiene ese punto, hasta los cruces más cercanos (si no cruza nada, borra la curva entera); extend lleva el extremo más cercano de una línea o un arco hasta la próxima curva; break la parte en los cruces más cercanos. |
| [`offset_sketch_curves`](#offset_sketch_curves) | sí | Desfase de boceto (Fusion: Desfase): copia paralela de la CADENA de líneas y arcos unida a entity (o de un círculo), con las esquinas resueltas, la restricción de desfase y su cota (paramétrico: si la cadena cambia, el desfase la sigue). |
| [`release_offset`](#release_offset) | sí | Suelta la asociación de un desfase (Fusion: borrar el glifo de desfase): la copia deja de seguir a la original, pero las curvas quedan. |
| [`edit_sketch_spline`](#edit_sketch_spline) | sí | Edita una spline ya dibujada (Fusion: manijas, Open/Close Spline, Insert Fit/Control Point y Change Spline Degree). |
| [`get_spline_curvature`](#get_spline_curvature) | no | Peine de curvatura de una curva del boceto (Fusion: Toggle Curvature Display): curvatura con signo en muestras repartidas por el parámetro, con el punto y la punta de cada púa (salen del lado opuesto al centro de curvatura, con largo curvatura × factor). |
| [`copy_sketch_entities`](#copy_sketch_entities) | sí | Copia y pega elementos entre bocetos (Fusion: Copiar y Pegar en el boceto): copia las curvas y puntos de source_sketch en sketch (el último boceto por defecto; puede ser el mismo), corridos (dx, dy), con las restricciones y cotas que quedan enteras dentro de la selección. |
| [`mirror_sketch`](#mirror_sketch) | sí | Simetría de boceto (Fusion: Simetría): copia espejada de curvas y puntos respecto de una línea del boceto, con restricciones de simetría (si la geometría original cambia, la copia la sigue). |
| [`sketch_rectangular_pattern`](#sketch_rectangular_pattern) | sí | Patrón rectangular de boceto (Fusion: Patrón rectangular en el boceto): copias de curvas y puntos en una o dos direcciones, atadas al original con la restricción de patrón (si el original cambia, las copias lo siguen). |
| [`sketch_circular_pattern`](#sketch_circular_pattern) | sí | Patrón circular de boceto (Fusion: Patrón circular en el boceto): copias de curvas y puntos alrededor de un centro, atadas al original con la restricción de patrón. total_angle = 360 reparte la cantidad en la vuelta entera; otro ángulo pone la primera y la última copia en sus extremos. suppress omite copias por índice; después se edita con edit_sketch_pattern. |
| [`edit_sketch_pattern`](#edit_sketch_pattern) | sí | Edita un patrón de boceto ya hecho (Fusion: doble clic en el glifo del patrón): cantidades, distancias, direcciones, simetría y copias suprimidas. |
| [`project_to_sketch`](#project_to_sketch) | sí | Proyecta aristas, caras, cuerpos, planos, ejes y puntos de trabajo, o curvas y puntos de otro boceto, sobre el plano del boceto (Fusion: Proyectar) o agrega donde cortan ese plano (mode=intersect; Fusion: Intersecar). |
| [`project_spun_profile`](#project_spun_profile) | sí | Proyecta el perfil giratorio de la geometría (Fusion: Proyectar › Spun Profile): gira aristas, caras, cuerpos o vértices alrededor de un eje y deja su perfil sobre el plano del boceto, para referenciarlo en el boceto o en operaciones de revolución y torneado. |
| [`break_projection_link`](#break_projection_link) | sí | Rompe el vínculo de una proyección (Fusion: Break Link): la geometría proyectada queda donde está como geometría normal, editable y ya no fija, y no sigue más al modelo. |
| [`manage_lost_projections`](#manage_lost_projections) | sí | Administra las proyecciones perdidas de un boceto (Fusion: Manage Lost Projections): las que ya no coinciden con el modelo (get_sketch › projections las marca con lost). relink las vuelve a vincular a otra selección (misma forma que la original: edges, faces, bodies, vertices o references); break les rompe el vínculo y delete borra su geometría. |
| [`set_line_type`](#set_line_type) | sí | Cambia el tipo de línea de curvas del boceto (Fusion: Construcción / Línea central de la paleta): normal (forma perfiles), construction (de construcción: guía, no forma perfiles) o centerline (eje: forma perfiles y sirve de eje de revolución). |
| [`edit_dimension`](#edit_dimension) | sí | Cambia el valor de una cota que ya existe (Fusion: doble clic en la cota): número o expresión con parámetros. |
| [`auto_constrain`](#auto_constrain) | sí | Restringe automáticamente el boceto (Fusion: AutoConstrain): detecta lo que ya se cumple y lo agrega como restricción (coincidente, concéntrica, horizontal, vertical, colineal, paralela, perpendicular, tangente, igual, punto medio, simetría respecto de una línea central o de construcción) y después cotas con las medidas actuales (largos, radios, ángulos y posiciones desde un punto fijo en el origen o desde el datum) hasta dejarlo totalmente restringido si se puede. |
| [`suggest_auto_constraints`](#suggest_auto_constraints) | no | Calcula alternativas de AutoConstrain SIN cambiar el boceto (Fusion: el diálogo con varios resultados). |
| [`create_construction_axis`](#create_construction_axis) | sí | Crea un eje con cualquiera de las cinco variantes de CONSTRUIR. |
| [`create_construction_point`](#create_construction_point) | sí | Crea un punto con las seis variantes de CONSTRUIR. |
| [`create_ucs`](#create_ucs) | sí | Crea un sistema de coordenadas de usuario con origen, ejes, giros y desfases. |
| [`draw_line_3d`](#draw_line_3d) | sí | Boceto 3D: dibuja una línea en el espacio (Fusion: 3D Sketch › Línea). |
| [`draw_spline_3d`](#draw_spline_3d) | sí | Boceto 3D: spline de ajuste en el espacio que pasa por points (Fusion: 3D Sketch › Spline), en coordenadas del boceto (x, y sobre el plano, z sobre la normal). |
| [`draw_point_3d`](#draw_point_3d) | sí | Boceto 3D: punto suelto en el espacio (Fusion: 3D Sketch › Punto), en coordenadas del boceto. |
| [`add_constraint_3d`](#add_constraint_3d) | sí | Boceto 3D: restricción entre entidades 3D (ids de get_sketch). type: coincident (punto–punto o punto sobre línea), axis (la Horizontal/Vertical de Fusion en 3D: alinea una línea con el eje axis), parallel, perpendicular, equal y collinear (dos líneas), tangent (línea o spline + spline que empieza o termina en un extremo de la otra; entre dos splines deja continuidad G1), midpoint (punto + línea), concentric (dos arcos, círculos o elipses: mismo centro) y fix (fija los puntos de las entidades). |
| [`add_dimension_3d`](#add_dimension_3d) | sí | Boceto 3D: cota en el espacio. type=distance: el largo de una línea (un id) o la distancia entre dos puntos 3D, en mm. type=angle: el ángulo entre dos líneas 3D, en grados (0 < ángulo < 180). value: número o expresión con parámetros (sigue al parámetro al recalcular). |
| [`delete_sketch_entities_3d`](#delete_sketch_entities_3d) | sí | Boceto 3D: borra entidades, restricciones o cotas 3D por id. |
| [`draw_arc_3d`](#draw_arc_3d) | sí | Boceto 3D: arco de 3 puntos en el espacio (Fusion: 3D Sketch › Arco): va de start a end pasando por through, en coordenadas del boceto. |
| [`draw_circle_3d`](#draw_circle_3d) | sí | Boceto 3D: círculo de centro y radio en el plano perpendicular a normal (Fusion: 3D Sketch › Círculo; normal = la del plano de la tríada), en coordenadas del boceto. |
| [`draw_ellipse_3d`](#draw_ellipse_3d) | sí | Boceto 3D: elipse de centro, extremo del eje mayor y radio menor en el plano perpendicular a normal (Fusion: 3D Sketch › Elipse). major_end se proyecta a ese plano. |
| [`draw_rectangle_3d`](#draw_rectangle_3d) | sí | Boceto 3D: rectángulo de 2 puntos (Fusion: 3D Sketch › Rectángulo) en el plano de la tríada xy, yz o zx que pasa por corner; opposite se proyecta a ese plano. |
| [`draw_conic_3d`](#draw_conic_3d) | sí | Boceto 3D: curva cónica (Fusion: 3D Sketch › Curva cónica): de start a end, con shoulder como vértice (cruce de las tangentes de los extremos) y rho (0 < rho < 1: menos de 0,5 elipse, 0,5 parábola, más hipérbola). |
| [`draw_text_3d`](#draw_text_3d) | sí | Boceto 3D: texto de una línea en el plano de la tríada (Fusion: 3D Sketch › Texto): la base empieza en origin; en xy corre por x y sube por y, en yz por y y z, en zx por x y z. |
| [`transform_sketch_3d`](#transform_sketch_3d) | sí | Boceto 3D: mover, rotar, escalar o copiar entidades 3D (Fusion: Mover/copiar y Escalar sobre el boceto 3D). |
| [`intersect_curves`](#intersect_curves) | sí | Boceto 3D: Intersection Curve de Fusion. |
| [`project_to_surface`](#project_to_surface) | sí | Boceto 3D: Project To Surface de Fusion: proyecta curvas de boceto sobre caras. mode=closest (Closest Point): cada punto de la curva va al punto más cercano de las caras (spline por 49 puntos); mode=vector (Along Vector): proyecta a lo largo de direction (vector [x, y, z] del mundo o un eje: 'X', 'Y', 'Z', id de un eje o una arista recta), hacia donde apunta. |
| [`draw_spiral`](#draw_spiral) | sí | Dibuja la espiral plana del editor como spline cúbica de ajuste abierta. |
| [`set_circle_radius`](#set_circle_radius) | sí | Cambia el radio de un círculo o arco libre, sin cota (lo que hace arrastrarlo en el editor): el círculo toma el radio nuevo y en un arco se corren sus extremos libres. |
| [`extend_sketch_curve`](#extend_sketch_curve) | sí | Alarga una línea o arco hasta la siguiente intersección, desde el extremo más cercano al punto. |
| [`split_sketch_curve`](#split_sketch_curve) | sí | Parte una curva en las intersecciones más cercanas al punto, como el editor; el punto debe caer sobre la curva. |
| [`redefine_sketch_plane`](#redefine_sketch_plane) | sí | Redefine el plano o la cara de un boceto existente conservando curvas, restricciones y cotas. |

### `create_construction_plane`

Crea un plano de construcción (CONSTRUIR › Plano). type=offset (por defecto): desfasado de un plano de origen (XY, XZ, YZ), de otro plano de construcción o de una CARA PLANA (selector o id de find_faces), sobre su normal. Los demás tipos usan references en orden: angle (un eje o arista + angle), tangent (una cara curva + angle, y opcional un plano de referencia), middle (dos planos o caras), two_edges (dos aristas o ejes), three_points (tres puntos o vértices), perpendicular (una arista, curva o plano + un punto) y path (una arista o curva + position entre 0 y 1). Sirve para dibujar bocetos fuera del origen: va en el grupo «boceto» porque su uso típico es create_sketch(plane=<este plano>).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `plane` (texto; opcional, por defecto `"XY"`): type=offset: plano base: "XY", "XZ", "YZ", el id/nombre de otro plano de construcción, o una cara plana (selector ">Z" o id de find_faces).
  - `offset` (número o expresión; opcional, por defecto `"10 mm"`): type=offset: desfase en mm sobre la normal del plano base (número o expresión con parámetros, p. ej. "alto / 2").
  - `name` (texto; opcional, por defecto `null`): nombre del plano; vacío = "Plano1", "Plano2"…
  - `type` ("offset" | "angle" | "tangent" | "middle" | "two_edges" | "three_points" | "perpendicular" | "path"; opcional, por defecto `"offset"`): "offset" (desfase), "angle" (en ángulo), "tangent" (tangente a una cara curva), "middle" (plano medio), "two_edges" (por dos aristas), "three_points" (por tres puntos), "perpendicular" (perpendicular a una curva en un punto) o "path" (en un punto de una ruta).
  - `references` (lista de texto o objeto o lista de número o null; opcional, por defecto `null`): referencias en orden según type (ver la descripción): planos de origen o de construcción, ejes, caras, aristas, selectores, ids de find_faces / find_edges, puntos de construcción, vértices [x, y, z] o {sketch, point | curve}.
  - `angle` (número o expresión; opcional, por defecto `0`): type=angle o tangent: ángulo en grados (número o expresión).
  - `position` (número o expresión; opcional, por defecto `0.5`): type=path: posición sobre la ruta entre 0 (inicio) y 1 (fin).
  - `distance` (número o expresión; opcional, por defecto `0`): type=perpendicular: corre el plano sobre su normal, en mm (número o expresión).
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de references y de plane (cara); vacío = el único cuerpo.
- CLI: `omnicad call create_construction_plane --doc pieza.omnicad`

### `create_sketch`

Crea un boceto vacío sobre un plano o sobre una cara plana. Coordenadas del boceto (mm): en XY x→X e y→Y (normal +Z); en XZ x→X e y→Z (normal −Y: una extrusión positiva avanza hacia −Y); en YZ x→Y e y→Z (normal +X). Un plano de construcción usa el marco de su plano base. SOBRE UNA CARA (plane = selector como '>Z' o id de find_faces como 'Cuerpo1/F6'; tiene que ser UNA cara plana): el boceto queda sobre la cara con la normal exterior como normal (extruir con join crece hacia afuera; con cut entra al material solo, como Fusion). Ejes: en caras horizontales x→+X e y = normal × x (y→+Y con normal +Z; y→−Y con normal −Z, como en Fusion la vista queda espejada al mirarla desde abajo); en las demás y→+Z (hacia arriba) y x = y × normal; el origen es la proyección del origen del mundo sobre el plano de la cara, no una esquina (plane_frame lo da y find_faces trae center_uv, el centro de cada cara en estos ejes). El boceto queda asociado a la cara, como en Fusion: si un parámetro la mueve o la gira, el boceto la sigue; si la cara desaparece, el paso da error. Con varios cuerpos, body dice en cuál se evalúa el selector de la cara.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `plane` (texto; opcional, por defecto `"XY"`): "XY", "XZ", "YZ", el id/nombre de un plano de construcción, o una cara plana: selector (">Z") o id ("Cuerpo1/F6").
  - `name` (texto; opcional, por defecto `null`): nombre del boceto; vacío = "Boceto1", "Boceto2"…
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo donde se evalúa el selector de cara de plane; vacío = el único cuerpo. No se usa con un plano ni con un id de cara.
  - `project_edges` (true/false; opcional, por defecto `false`): true (solo sobre una cara) proyecta sus aristas de forma asociativa, como Fusion al crear el boceto; false la deja vacía.
- CLI: `omnicad call create_sketch --doc pieza.omnicad`

### `draw_line`

Dibuja una línea en el boceto (un paso de deshacer). Coordenadas en mm sobre el plano del boceto. Con midpoint=true es una línea de punto medio: el primer punto es su punto medio y el segundo un extremo (el otro es el simétrico) y queda con la restricción de punto medio. Un extremo que cae sobre el de otra línea comparte su punto (cadena); si no, queda suelto. Devuelve los ids creados (línea y puntos) y la cantidad de perfiles.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `start_x` (número; obligatorio): x del punto inicial (mm); con midpoint, x del punto medio.
  - `start_y` (número; obligatorio): y del punto inicial (mm); con midpoint, y del punto medio.
  - `end_x` (número; obligatorio): x del punto final (mm); con midpoint, x de un extremo.
  - `end_y` (número; obligatorio): y del punto final (mm); con midpoint, y de un extremo.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para una línea de construcción (no forma perfiles).
  - `midpoint` (true/false; opcional, por defecto `false`): true dibuja la línea desde su punto medio (start) y un extremo (end), con la restricción de punto medio.
  - `centerline` (true/false; opcional, por defecto `false`): true para geometría central (forma perfiles); incompatible con construction=true.
- CLI: `omnicad call draw_line --doc pieza.omnicad start_x=… start_y=… end_x=… end_y=…`

### `draw_rectangle`

Dibuja un rectángulo (4 líneas con restricciones horizontal y vertical). Tres formas de darlo: dos esquinas opuestas (x1, y1, x2, y2); centro y tamaño (center_x, center_y, width, height); o esquina mínima y tamaño (origin_x, origin_y, width, height). width es el tamaño en x del boceto y height en y. Con center_diagonals=true, la forma centro y tamaño agrega las dos diagonales de construcción y deja el centro como punto medio de una (el «Rectángulo central» de la interfaz). Con three_points=[A, B, C] es el rectángulo de 3 puntos: el lado A→B y un punto C que da el ancho, perpendicular al lado (queda girado si A→B no es horizontal). Un punto nuevo sobre (0,0) queda anclado al origen, como en la interfaz.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `x1` (número; opcional, por defecto `null`): x de la primera esquina (forma de dos esquinas).
  - `y1` (número; opcional, por defecto `null`): y de la primera esquina.
  - `x2` (número; opcional, por defecto `null`): x de la esquina opuesta.
  - `y2` (número; opcional, por defecto `null`): y de la esquina opuesta.
  - `center_x` (número; opcional, por defecto `null`): x del centro (forma centro + tamaño).
  - `center_y` (número; opcional, por defecto `null`): y del centro.
  - `origin_x` (número; opcional, por defecto `null`): x de la esquina mínima (forma esquina + tamaño; 0 si solo se da origin_y).
  - `origin_y` (número; opcional, por defecto `null`): y de la esquina mínima.
  - `width` (número; opcional, por defecto `null`): tamaño en x del boceto (mm, mayor que cero), para las formas con tamaño.
  - `height` (número; opcional, por defecto `null`): tamaño en y del boceto (mm, mayor que cero), para las formas con tamaño.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para un rectángulo de construcción (no forma perfiles).
  - `center_diagonals` (true/false; opcional, por defecto `false`): true (con center_x/center_y y tamaño) agrega las diagonales de construcción y el punto central con restricción de punto medio.
  - `three_points` (lista de lista de número o null; opcional, por defecto `null`): [[ax, ay], [bx, by], [cx, cy]]: lado A→B y punto C que da el ancho; no se combina con las otras formas.
  - `centerline` (true/false; opcional, por defecto `false`): true para geometría central (forma perfiles); incompatible con construction=true.
- CLI: `omnicad call draw_rectangle --doc pieza.omnicad`

### `draw_circle`

Dibuja un círculo (un paso de deshacer): por centro y radio (por defecto), por 2 puntos (los extremos de un diámetro) o por 3 puntos (points). Un círculo cerrado forma un perfil; dentro de un rectángulo da dos perfiles (el anillo y el disco).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `radius` (número; opcional, por defecto `null`): radio en mm (positivo); obligatorio con kind=center_radius.
  - `center_x` (número; opcional, por defecto `0.0`): x del centro (mm); solo con kind=center_radius.
  - `center_y` (número; opcional, por defecto `0.0`): y del centro (mm); solo con kind=center_radius.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para un círculo de construcción (no forma perfiles).
  - `kind` ("center_radius" | "two_points" | "three_points"; opcional, por defecto `"center_radius"`): "center_radius" (centro y radio), "two_points" (extremos de un diámetro) o "three_points" (pasa por tres puntos).
  - `points` (lista de lista de número o null; opcional, por defecto `null`): [[x, y], …] con dos puntos (two_points) o tres (three_points), en mm sobre el plano del boceto.
  - `centerline` (true/false; opcional, por defecto `false`): true para geometría central (forma perfiles); incompatible con construction=true.
- CLI: `omnicad call draw_circle --doc pieza.omnicad`

### `draw_arc`

Dibuja un arco. Tres formas: centro + punto inicial + ángulo de barrido (center_x, center_y, start_x, start_y, sweep_angle; positivo = antihorario) o tres puntos (start_x, start_y, mid_x, mid_y, end_x, end_y), o tangente a una curva (tangent_to, start_x/start_y y end_x/end_y). La forma tangente comparte el extremo y agrega la restricción de tangencia. Un arco solo forma un perfil si se cierra con otras curvas.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `start_x` (número; obligatorio): x del punto inicial (mm).
  - `start_y` (número; obligatorio): y del punto inicial (mm).
  - `center_x` (número; opcional, por defecto `null`): x del centro (forma centro + barrido).
  - `center_y` (número; opcional, por defecto `null`): y del centro.
  - `sweep_angle` (número; opcional, por defecto `null`): ángulo de barrido en grados, entre -360 y 360 sin incluirlos; positivo = antihorario.
  - `mid_x` (número; opcional, por defecto `null`): x de un punto intermedio del arco (forma de tres puntos).
  - `mid_y` (número; opcional, por defecto `null`): y del punto intermedio.
  - `end_x` (número; opcional, por defecto `null`): x del punto final (forma de tres puntos o tangente).
  - `end_y` (número; opcional, por defecto `null`): y del punto final.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para un arco de construcción (no forma perfiles).
  - `tangent_to` (entero; opcional, por defecto `null`): id de la línea, arco, arco de elipse, spline abierta o cónica de partida; start_x/start_y debe coincidir con uno de sus extremos. También acepta una elipse cerrada si el inicio está sobre ella. No se combina con centro, barrido ni punto intermedio.
  - `centerline` (true/false; opcional, por defecto `false`): true para geometría central (forma perfiles); incompatible con construction=true.
- CLI: `omnicad call draw_arc --doc pieza.omnicad start_x=… start_y=…`

### `create_polygon`

Dibuja un polígono regular de n lados (líneas iguales sobre un círculo guía de construcción, como la interfaz). Inscrito: los vértices están sobre el círculo de radio `radius`; circunscrito: los lados son tangentes a ese círculo (radius = medio entrecaras). Sin más, le quedan 4 grados de libertad (centro, tamaño y giro); con fully_constrained=true queda TOTALMENTE acotado: cota de radio del círculo guía (guarda la expresión de radius, así sigue a un parámetro), giro fijado (restricción horizontal/vertical o cota de ángulo) y centro acotado desde un punto fijo en el origen del boceto (dof 0).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sides` (entero; obligatorio): cantidad de lados (3 a 64; tope propio igual al de la interfaz: la ayuda de Fusion no publica un máximo).
  - `radius` (número o expresión; opcional, por defecto `null`): radio del círculo guía en mm (circunradio si es inscrito, apotema si es circunscrito); número o expresión con parámetros ("entrecaras / 2"). No se usa con kind=edge.
  - `center_x` (número; opcional, por defecto `0.0`): x del centro (mm).
  - `center_y` (número; opcional, por defecto `0.0`): y del centro (mm).
  - `rotation` (número; opcional, por defecto `0.0`): ángulo en grados del primer vértice respecto del eje x del boceto.
  - `kind` ("inscribed" | "circumscribed" | "edge"; opcional, por defecto `"inscribed"`): "inscribed" (vértices sobre el círculo), "circumscribed" (lados tangentes al círculo) o "edge" (polígono por arista: se da un lado con edge_points).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para un polígono de construcción (no forma perfiles).
  - `fully_constrained` (true/false; opcional, por defecto `false`): true para dejarlo totalmente acotado (radio, giro y posición del centro): dof 0.
  - `edge_points` (lista de lista de número o null; opcional, por defecto `null`): kind=edge: [[x, y], [x, y], [x, y]] = extremos A y B del primer lado y un punto del lado hacia donde crece el polígono.
  - `centerline` (true/false; opcional, por defecto `false`): true para geometría central (forma perfiles); incompatible con construction=true.
- CLI: `omnicad call create_polygon --doc pieza.omnicad sides=…`

### `draw_spline`

Dibuja una spline: de ajuste (pasa por los puntos) o de puntos de control (grado 3 o 5, necesita al menos grado+1 puntos). Con tangent_to, una spline de ajuste abierta comparte el extremo de otra curva y agrega tangencia; el solver ajusta los puntos libres.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `points` (lista de lista de número; obligatorio): lista de puntos [x, y] en mm sobre el plano del boceto.
  - `spline_type` ("fit_points" | "control_points"; opcional, por defecto `"fit_points"`): "fit_points" (pasa por los puntos) o "control_points" (los puntos son los polos).
  - `degree` (entero; opcional, por defecto `3`): grado de la spline de puntos de control (3 o 5); se ignora en la de ajuste.
  - `closed` (true/false; opcional, por defecto `false`): true para cerrar la spline de ajuste (forma un perfil).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para una spline de construcción (no forma perfiles).
  - `centerline` (true/false; opcional, por defecto `false`): true para geometría central (forma perfiles); incompatible con construction=true.
  - `tangent_to` (entero; opcional, por defecto `null`): id de la curva de partida (línea, arco, arco de elipse, spline abierta, cónica o elipse); solo para una spline de ajuste abierta. El primer punto debe coincidir con su extremo (o estar sobre la elipse cerrada).
  - `tangent_end` ("start" | "end"; opcional, por defecto `"end"`): extremo de la curva de partida, "start" o "end"; se ignora en una elipse cerrada. El solver puede ajustar los puntos libres para cumplir la tangencia.
- CLI: `omnicad call draw_spline --doc pieza.omnicad points=…`

### `add_constraint`

Agrega una restricción geométrica entre entidades del boceto (ids de get_sketch: curvas y puntos). Si choca con las que ya hay, falla y el boceto queda como estaba. Entidades por tipo: horizontal y vertical: una línea o dos puntos; parallel, perpendicular, collinear y equal: dos líneas (equal también dos círculos/arcos); coincident: un punto y otro punto o una curva; midpoint: un punto y una línea o arco; tangent y concentric: dos curvas; fix: una o más entidades; symmetry: dos entidades y la línea eje; polygon: al menos tres líneas que comparten vértices y forman una cadena cerrada, o un solo lado para tomar automáticamente su cadena cerrada de líneas. Referencias reservadas: origen 0, eje X -1, eje Y -2 (origin/axes de get_sketch). Repetir fix sobre las mismas entidades devuelve el fix existente.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): id o nombre del boceto.
  - `type` ("coincident" | "horizontal" | "vertical" | "parallel" | "perpendicular" | "equal" | "tangent" | "concentric" | "midpoint" | "fix" | "collinear" | "symmetry" | "curvature" | "polygon"; obligatorio): tipo de restricción.
  - `entities` (lista de entero; obligatorio): ids de las entidades (curvas o puntos), en el orden que pide el tipo; origen 0, eje X -1 y eje Y -2 son referencias fijas reservadas.
- CLI: `omnicad call add_constraint --doc pieza.omnicad sketch=… type=… entities=…`

### `add_dimension`

Agrega una cota (dimensión) que maneja la geometría. El valor es un número (mm o grados) o una expresión con parámetros ('ancho / 2'); si se omite, usa la medida actual. Las cotas de largo, radio, diámetro y desfase tienen que ser mayores que cero y de hasta 1.000.000 mm (1 km). Entidades por tipo: distance: dos puntos, una línea, un punto y una línea, o dos líneas; horizontal y vertical: dos puntos o una línea; radius y diameter: un círculo o arco (diameter también acepta un punto o una línea con una línea central: mide el doble de la distancia al eje, como Fusion); angle: dos líneas; offset: dos líneas o dos círculos/arcos. distance también acepta un círculo o arco con un punto, una línea u otro círculo o arco (`mode`: center mide al centro, tangent al borde más cercano; entre círculos, de borde a borde) y un punto con una spline (la distancia a la curva). En una cota lineal (distance, horizontal o vertical de una línea o de dos puntos), `offset` y `text_offset` fijan dónde se dibuja: no cambian el valor ni la geometría; `position` [x, y] (mm) hace lo mismo que arrastrar la cota con el ratón y vale en todas: en las lineales fija offset y text_offset, en un ángulo el radio del arco, en un radio o diámetro hacia dónde sale la línea y en las demás dónde va el texto. Referencias fijas reservadas: origen 0, eje X -1 y eje Y -2 (origin/axes de get_sketch). Cada cota recibe un name dN único en el documento, visible en get_parameters y citable en expresiones de otras cotas, parámetros y operaciones. reference=true crea una cota de referencia: mide sin restringir e ignora value. Una cota driving redundante o en conflicto se crea como referencia con aviso y converted_to_reference=true. En angle, `near` [x, y] elige qué ángulo se mide, como el cursor en Fusion: el del cuadrante entre las dos rectas que contiene ese punto (45° o 135° en la misma figura); sin near mide entre las líneas tal como se dibujaron. El cuadrante (0..3) se guarda y get_sketch lo muestra como quadrant.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): id o nombre del boceto.
  - `type` ("distance" | "horizontal" | "vertical" | "radius" | "diameter" | "angle" | "offset"; obligatorio): tipo de cota.
  - `entities` (lista de entero; obligatorio): ids de las entidades acotadas (curvas o puntos), en el orden que pide el tipo; origen 0, eje X -1 y eje Y -2 son referencias fijas reservadas.
  - `value` (número o expresión; opcional, por defecto `null`): valor: número (mm; grados en angle) o expresión con parámetros, p. ej. "radio_agujero * 2". Vacío = medida actual.
  - `offset` (número; opcional, por defecto `null`): mm que se separa la línea de cota de la medida (con signo, hacia +Y en horizontal, +X en vertical, a la izquierda de la línea en distance); vacío = lo automático.
  - `text_offset` (número; opcional, por defecto `null`): mm que se corre el texto a lo largo de la línea de cota desde su centro; vacío = centrado.
  - `reference` (true/false; opcional, por defecto `false`): true = cota de referencia (driven): mide la geometría sin restringirla; ignora value.
  - `mode` ("center" | "tangent"; opcional, por defecto `"center"`): en una distancia con un círculo o arco: "center" (al centro) o "tangent" (al borde más cercano).
  - `near` (lista de número o null; opcional, por defecto `null`): [x, y] en mm, solo en angle: el ángulo medido es el del cuadrante entre las dos rectas que contiene este punto; vacío = entre las líneas tal como se dibujaron.
  - `position` (lista de número o null; opcional, por defecto `null`): [x, y] en mm: donde queda la cota, como si se la arrastrara con el ratón (no cambia el valor ni la geometría); no se combina con offset ni text_offset; vacío = lo automático.
- CLI: `omnicad call add_dimension --doc pieza.omnicad sketch=… type=… entities=…`

### `get_sketch`

Informe de un boceto: plano y su marco 3D, entidades con ids estables (coordenadas ya resueltas por el solver), puntos, restricciones, cotas con su valor, perfiles (índice, área mm², centroide, caja [min/max en coordenadas del boceto] y curvas del borde) y estado del solver en la clave `status` (fully_constrained, under_constrained, over_constrained) con los grados de libertad en `dof`. Cada punto y curva trae state: free, determined o fixed. conflicts lista los ids de restricciones/cotas cuya retirada individual resuelve el conflicto (vacía sin conflicto o si hacen falta varias retiradas). origin=0 y axes={x:-1,y:-2} son ids reservados citables en add_constraint/add_dimension; las referencias se materializan como construcción fija al citarlas y no forman perfiles. dimensions incluye name (dN), el parámetro de cada cota, sincronizado con get_parameters/set_parameter, y reference: true indica una cota driven cuyo value es la medida actual y no aporta restricciones ni reduce dof. Si el boceto tiene geometría 3D (draw_line_3d y las demás *_3d) trae además entities_3d, points_3d (x, y, z), constraints_3d, dimensions_3d, status_3d y dof_3d.

- Modifica el documento: no.
- Parámetros:
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call get_sketch --doc pieza.omnicad`

### `sketch_from_spec`

Crea un boceto COMPLETO en una sola llamada (un paso de deshacer): geometría, restricciones y cotas. entities: lista de {type, ...}: line{start,end}, rectangle{corner1,corner2 | center,width,height | origin,width,height}, circle{center,radius}, arc{center,start,sweep | start,mid,end}, polygon{sides,radius,center,rotation,kind,fully_constrained}, ellipse{center,major_radius,minor_radius,angle}, slot{kind,points,width} (kind como en draw_slot), spline{points,spline_type,degree,closed}, point{at}, conic{start,end,vertex,rho}, text{text,...} (opciones de add_text, path_entity admite cita), midpoint_line{center,end}, polygon{kind:edge,start,end,sides,edge_points?} (sin edge_points crece a la izquierda de start→end; edge_points permite elegir el lado como create_polygon), tangent_circle{lines:[citas],x?,y?,radius?}, tangent_arc{from:cita de extremo de línea,end}. Boceto 3D (como draw_*_3d, coordenadas [x, y, z]): line_3d{start,end}, spline_3d{points,closed?}, point_3d{at}, arc_3d{start,through,end}, circle_3d{center,radius,normal?}, ellipse_3d{center,major_end,minor_radius,normal?}, rectangle_3d{corner,opposite,plane?} (citas 'id.l1..l4'), conic_3d{start,shoulder,end,rho?}, text_3d{text,origin,height?,plane?,font?}; normal vacía = [0, 0, 1], plane = xy, yz o zx (por defecto xy). Todas aceptan id (nombre propio para citarla), construction y centerline (mutuamente excluyentes; texto no admite centerline, los puntos sueltos no tienen tipo de línea). Las coordenadas son [x, y] en mm del plano. constraints: [{type, entities:[citas]}]; dimensions: [{type, entities:[citas], value, reference?}] (value puede ser una expresión con parámetros). Citas: 'id' (la curva), 'id.start', 'id.end', 'id.center', en un rectángulo 'id.bottom/right/top/left' (líneas) y 'id.c1..c4' (esquinas), en un polígono 'id.side1..', 'id.v1..' y 'id.circle', en una elipse 'id.major' y 'id.major_axis/minor_axis', en una ranura 'id.side1/side2/end1/end2/axis/center1/center2'; un entero cita un id de entidad ya existente. Sin id, la entidad se cita 'e0', 'e1'… según su posición en la lista. plane es un plano o una cara plana (selector '>Z' o id de find_faces), con los mismos ejes que create_sketch sobre esa cara (find_faces da center_uv); con varios cuerpos, body dice en cuál se evalúa el selector. Devuelve handles (cita → id real), perfiles, estado y plane_frame (origen y ejes del plano). Sin entities crea un boceto vacío y devuelve un aviso. reference=true mide sin restringir.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `plane` (texto; opcional, por defecto `"XY"`): "XY", "XZ", "YZ", el id/nombre de un plano de construcción, o una cara plana: selector (">Z") o id ("Cuerpo1/F6").
  - `entities` (lista de objeto o null; opcional, por defecto `null`): geometría del boceto (ver la descripción de la herramienta).
  - `constraints` (lista de objeto o null; opcional, por defecto `null`): restricciones, cada una {"type": ..., "entities": [citas]}.
  - `dimensions` (lista de objeto o null; opcional, por defecto `null`): cotas, cada una {"type": ..., "entities": [citas], "value": número o expresión, "reference": false}; reference=true mide sin restringir y permite omitir value.
  - `name` (texto; opcional, por defecto `null`): nombre del boceto; vacío = "Boceto1", "Boceto2"…
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo donde se evalúa el selector de cara de plane; vacío = el único cuerpo. No se usa con un plano ni con un id de cara.
  - `project_edges` (true/false; opcional, por defecto `false`): true (solo sobre una cara) proyecta además el contorno de la cara de forma asociativa; false no proyecta nada.
- CLI: `omnicad call sketch_from_spec --doc pieza.omnicad`

### `draw_ellipse`

Dibuja una elipse (Fusion: Elipse) por centro, radio mayor, radio menor y giro del eje mayor. Como la interfaz, suma sus ejes mayor y menor como líneas de construcción, con el centro en su punto medio (sirven para acotarla). Una elipse cerrada forma un perfil.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `major_radius` (número; obligatorio): semieje mayor en mm (positivo): distancia del centro al extremo del eje mayor.
  - `minor_radius` (número; obligatorio): semieje menor en mm (positivo).
  - `center_x` (número; opcional, por defecto `0.0`): x del centro (mm).
  - `center_y` (número; opcional, por defecto `0.0`): y del centro (mm).
  - `angle` (número; opcional, por defecto `0.0`): giro del eje mayor en grados respecto del eje x del boceto (antihorario).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para una elipse de construcción (no forma perfiles).
  - `centerline` (true/false; opcional, por defecto `false`): true para geometría central (forma perfiles); incompatible con construction=true.
- CLI: `omnicad call draw_ellipse --doc pieza.omnicad major_radius=… minor_radius=…`

### `draw_slot`

Dibuja una ranura (Fusion: Ranura): dos lados y dos extremos redondos tangentes, más el eje de construcción. kind y points (cada uno [x, y] en mm): center_to_center = [centro de un extremo, centro del otro]; overall = [punta de un extremo, punta del otro] (largo total); center_point = [centro de la ranura, centro de un extremo]; arc_three_points = [centro de un extremo, centro del otro, un punto del arco del eje]; arc_center = [centro del arco, centro de un extremo, punto en la dirección del otro extremo] (antihorario). width es el ancho total. Forma un perfil cerrado.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `points` (lista de lista de número; obligatorio): 2 puntos [x, y] (ranuras rectas) o 3 (ranuras de arco), en mm; qué es cada uno depende de kind.
  - `width` (número; obligatorio): ancho total de la ranura en mm (positivo; en una de arco, menor que el doble del radio del eje).
  - `kind` ("center_to_center" | "overall" | "center_point" | "arc_three_points" | "arc_center"; opcional, por defecto `"center_to_center"`): center_to_center, overall, center_point, arc_three_points o arc_center.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para una ranura de construcción (no forma perfiles).
  - `centerline` (true/false; opcional, por defecto `false`): true para geometría central (forma perfiles); incompatible con construction=true.
- CLI: `omnicad call draw_slot --doc pieza.omnicad points=… width=…`

### `draw_point`

Agrega un punto suelto al boceto (Fusion: Punto): sirve de referencia para cotas, restricciones, agujeros o el centro de un patrón circular.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `x` (número; obligatorio): x del punto (mm).
  - `y` (número; obligatorio): y del punto (mm).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call draw_point --doc pieza.omnicad x=… y=…`

### `draw_conic`

Dibuja una curva cónica (Fusion: Curva cónica) entre dos extremos, con el vértice (donde se cruzan las tangentes de los extremos) y Rho: 0.5 = parábola, menos = elipse, más = hipérbola.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `start_x` (número; obligatorio): x del primer extremo (mm).
  - `start_y` (número; obligatorio): y del primer extremo (mm).
  - `end_x` (número; obligatorio): x del otro extremo (mm).
  - `end_y` (número; obligatorio): y del otro extremo (mm).
  - `vertex_x` (número; obligatorio): x del vértice (mm); no puede estar alineado con los extremos.
  - `vertex_y` (número; obligatorio): y del vértice (mm).
  - `rho` (número; opcional, por defecto `0.5`): forma de la curva, entre 0 y 1 sin incluirlos.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para una cónica de construcción.
  - `centerline` (true/false; opcional, por defecto `false`): true para geometría central (forma perfiles); incompatible con construction=true.
- CLI: `omnicad call draw_conic --doc pieza.omnicad start_x=… start_y=… end_x=… end_y=… vertex_x=… vertex_y=…`

### `draw_tangent_circle`

Dibuja un círculo tangente a 2 o 3 líneas del boceto (Fusion: Círculo de 2 / 3 tangentes) y le agrega las restricciones de tangencia. Con 2 líneas, (x, y) dice en qué ángulo de las dos va y, sin radius, también su tamaño (el círculo pasa cerca de ese punto); entre dos paralelas el diámetro es la separación. Con 3 líneas sale el inscrito, o el que tenga sus tangencias más cerca de (x, y).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `lines` (lista de entero; obligatorio): ids de 2 o 3 líneas del boceto (get_sketch).
  - `x` (número; opcional, por defecto `null`): x de un punto que ubica el círculo (mm); vacío = automático.
  - `y` (número; opcional, por defecto `null`): y de ese punto (mm).
  - `radius` (número; opcional, por defecto `null`): radio en mm (solo con 2 líneas no paralelas); vacío = el que pasa por (x, y).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para un círculo de construcción.
- CLI: `omnicad call draw_tangent_circle --doc pieza.omnicad lines=…`

### `draw_blend_curve`

Une los extremos de dos curvas abiertas con una spline suave (Fusion: Curva de fusión), tangente (G1) o con curvatura continua (G2) en las dos uniones. Sin point1/point2 une los dos extremos más cercanos.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entity1` (entero; obligatorio): id de la primera curva (línea, arco, spline o cónica; abierta).
  - `entity2` (entero; obligatorio): id de la segunda curva.
  - `point1` (lista de número o null; opcional, por defecto `null`): [x, y] cerca del extremo de entity1 que se une; vacío = automático.
  - `point2` (lista de número o null; opcional, por defecto `null`): [x, y] cerca del extremo de entity2 que se une; vacío = automático.
  - `continuity` ("G1" | "G2"; opcional, por defecto `"G1"`): G1 (tangente) o G2 (curvatura continua).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call draw_blend_curve --doc pieza.omnicad entity1=… entity2=…`

### `sketch_fillet`

Empalme de boceto (Fusion: Empalme en el boceto): redondea la esquina entre dos curvas (líneas, arcos o círculos) con un arco tangente; recorta las curvas, agrega las tangencias y la cota de radio. radius puede ser una expresión con parámetros (queda en la cota). Con point1/point2 se elige qué parte de cada curva se conserva (útil si se cruzan); sin ellos, la parte más larga.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entity1` (entero; obligatorio): id de la primera curva (get_sketch).
  - `entity2` (entero; obligatorio): id de la segunda curva.
  - `radius` (número o expresión; obligatorio): radio del empalme en mm: número o expresión con parámetros.
  - `point1` (lista de número o null; opcional, por defecto `null`): [x, y] sobre entity1, del lado que se conserva; vacío = automático.
  - `point2` (lista de número o null; opcional, por defecto `null`): [x, y] sobre entity2, del lado que se conserva; vacío = automático.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call sketch_fillet --doc pieza.omnicad entity1=… entity2=… radius=…`

### `sketch_chamfer`

Chaflán de boceto (Fusion: Chaflán en el boceto) entre dos líneas: de distancias iguales (distance), de dos distancias (distance y distance2) o de distancia y ángulo (distance y angle). Recorta las líneas, agrega la línea del chaflán y sus cotas (las distancias pueden ser expresiones con parámetros).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `line1` (entero; obligatorio): id de la primera línea.
  - `line2` (entero; obligatorio): id de la segunda línea.
  - `distance` (número o expresión; obligatorio): distancia del chaflán sobre line1 (y sobre line2 si no hay distance2 ni angle), en mm o expresión.
  - `distance2` (número o expresión; opcional, por defecto `null`): distancia sobre line2 (chaflán de dos distancias); vacío = igual a distance.
  - `angle` (número o expresión; opcional, por defecto `null`): ángulo en grados del chaflán respecto de line1 (chaflán de distancia y ángulo); no va con distance2.
  - `point1` (lista de número o null; opcional, por defecto `null`): [x, y] sobre line1, del lado que se conserva; vacío = automático.
  - `point2` (lista de número o null; opcional, por defecto `null`): [x, y] sobre line2, del lado que se conserva; vacío = automático.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call sketch_chamfer --doc pieza.omnicad line1=… line2=… distance=…`

### `trim_sketch_curve`

Recortar, alargar o partir una curva del boceto (Fusion: Recortar / Alargar / Partir). (x, y) es el lugar del clic, sobre la curva o cerca: trim quita el tramo de la curva que contiene ese punto, hasta los cruces más cercanos (si no cruza nada, borra la curva entera); extend lleva el extremo más cercano de una línea o un arco hasta la próxima curva; break la parte en los cruces más cercanos.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entity` (entero; obligatorio): id de la curva (get_sketch).
  - `x` (número; obligatorio): x del punto que elige el tramo (mm).
  - `y` (número; obligatorio): y del punto (mm).
  - `mode` ("trim" | "extend" | "break"; opcional, por defecto `"trim"`): trim (recortar), extend (alargar) o break (partir).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call trim_sketch_curve --doc pieza.omnicad entity=… x=… y=…`

### `offset_sketch_curves`

Desfase de boceto (Fusion: Desfase): copia paralela de la CADENA de líneas y arcos unida a entity (o de un círculo), con las esquinas resueltas, la restricción de desfase y su cota (paramétrico: si la cadena cambia, el desfase la sigue). Por defecto una cadena cerrada crece hacia afuera y una abierta va a la izquierda de su recorrido; distance negativa va al otro lado, y side_x/side_y eligen el lado con un punto. direction=two desfasa distance a un lado y distance2 al otro; direction=symmetric, distance a los dos lados. match_topology=true (Fusion: Match Topology) limita la distancia para que el desfase conserve la topología de la curva madre (ningún segmento desaparece) y avisa la distancia usada. Una spline, una elipse o un arco de elipse dan una spline libre (sin asociación). Para soltar la asociación: release_offset. Para letras o cualquier contorno (sin parámetros): offset_profiles.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entity` (entero; obligatorio): id de una curva de la cadena (línea o arco), de un círculo, elipse o spline.
  - `distance` (número o expresión; obligatorio): separación en mm, número o expresión con parámetros; negativa = al lado contrario.
  - `side_x` (número; opcional, por defecto `null`): x de un punto del lado donde va el desfase; vacío = el lado por defecto.
  - `side_y` (número; opcional, por defecto `null`): y de ese punto.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `direction` ("one" | "two" | "symmetric"; opcional, por defecto `"one"`): one (un lado), two (distance a un lado y distance2 al contrario) o symmetric (distance a los dos lados).
  - `distance2` (número o expresión; opcional, por defecto `null`): separación del segundo lado con direction=two (obligatoria en ese caso).
  - `match_topology` (true/false; opcional, por defecto `false`): true = si la distancia haría desaparecer un segmento (o anular un radio), se usa la mayor que conserva la topología, como número fijo, y se avisa.
- CLI: `omnicad call offset_sketch_curves --doc pieza.omnicad entity=… distance=…`

### `release_offset`

Suelta la asociación de un desfase (Fusion: borrar el glifo de desfase): la copia deja de seguir a la original, pero las curvas quedan. Con keep_dimension=true se conserva la cota del desfase.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entity` (entero; obligatorio): id de la curva original o de su copia desfasada (get_sketch).
  - `keep_dimension` (true/false; opcional, por defecto `false`): true = deja la cota de desfase; false = la borra junto con la asociación.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call release_offset --doc pieza.omnicad entity=…`

### `edit_sketch_spline`

Edita una spline ya dibujada (Fusion: manijas, Open/Close Spline, Insert Fit/Control Point y Change Spline Degree). Acciones: activate_handle (manija de tangente en un punto de ajuste: una línea de construcción que se puede acotar; con angle, length y curvature), edit_handle, deactivate_handle, open / close (solo la de ajuste), insert_point (punto de ajuste sobre la curva o punto de control sin cambiar la forma, cerca de x, y) y set_degree (3 o 5, solo la de puntos de control). Las manijas van en splines de ajuste abiertas. El peine de curvatura: get_spline_curvature.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entity` (entero; obligatorio): id de la spline (get_sketch).
  - `action` ("activate_handle" | "edit_handle" | "deactivate_handle" | "open" | "close" | "insert_point" | "set_degree"; obligatorio): qué hacer (ver la descripción de la herramienta).
  - `point` (entero; opcional, por defecto `null`): id del punto de ajuste de la manija (vertices / points de get_sketch); para las acciones de manija.
  - `angle` (número; opcional, por defecto `null`): dirección de la tangente en grados (antihoraria desde +x); vacío = la tangente actual.
  - `length` (número; opcional, por defecto `null`): largo de la manija en mm (más largo = la curva sigue más esa dirección); vacío = el natural.
  - `curvature` (número; opcional, por defecto `null`): curvatura en ese punto, en 1/mm (1 / radio; positiva gira a la izquierda); vacío = sin cambio (al activar: libre).
  - `x` (número; opcional, por defecto `null`): x del punto a insertar (insert_point), en mm; se usa el punto de la curva más cercano.
  - `y` (número; opcional, por defecto `null`): y del punto a insertar (insert_point), en mm.
  - `degree` (entero; opcional, por defecto `null`): grado nuevo de la spline de puntos de control (3 o 5) para set_degree.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call edit_sketch_spline --doc pieza.omnicad entity=… action=…`

### `get_spline_curvature`

Peine de curvatura de una curva del boceto (Fusion: Toggle Curvature Display): curvatura con signo en muestras repartidas por el parámetro, con el punto y la punta de cada púa (salen del lado opuesto al centro de curvatura, con largo curvatura × factor). No cambia el documento.

- Modifica el documento: no.
- Parámetros:
  - `entity` (entero; obligatorio): id de la curva (spline, cónica, arco, círculo, elipse o línea) en get_sketch.
  - `density` (entero; opcional, por defecto `30`): cuántas púas (2 a 200).
  - `scale` (número; opcional, por defecto `1.0`): escala del largo de las púas (1 = la más larga mide el 20 % del tamaño de la curva).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call get_spline_curvature --doc pieza.omnicad entity=…`

### `copy_sketch_entities`

Copia y pega elementos entre bocetos (Fusion: Copiar y Pegar en el boceto): copia las curvas y puntos de source_sketch en sketch (el último boceto por defecto; puede ser el mismo), corridos (dx, dy), con las restricciones y cotas que quedan enteras dentro de la selección. Lo pegado es geometría normal y nueva: no queda asociada al original. Para copiar dentro del mismo boceto con vínculo: transform_sketch con copy.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entities` (lista de entero; obligatorio): ids de las curvas o puntos de source_sketch a copiar (get_sketch).
  - `source_sketch` (texto; obligatorio): id o nombre del boceto de origen.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto de destino; vacío = el último boceto del timeline.
  - `dx` (número; opcional, por defecto `0.0`): corrimiento en x del pegado, en mm; 0 = en el mismo lugar.
  - `dy` (número; opcional, por defecto `0.0`): corrimiento en y del pegado, en mm.
- CLI: `omnicad call copy_sketch_entities --doc pieza.omnicad entities=… source_sketch=…`

### `mirror_sketch`

Simetría de boceto (Fusion: Simetría): copia espejada de curvas y puntos respecto de una línea del boceto, con restricciones de simetría (si la geometría original cambia, la copia la sigue). Lo que está sobre el eje se comparte. Los textos no se espejan (para eso: transform_sketch o edit_text).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entities` (lista de entero; obligatorio): ids de las curvas o puntos a reflejar (get_sketch).
  - `axis` (entero; obligatorio): id de la línea de simetría (puede ser de construcción).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call mirror_sketch --doc pieza.omnicad entities=… axis=…`

### `sketch_rectangular_pattern`

Patrón rectangular de boceto (Fusion: Patrón rectangular en el boceto): copias de curvas y puntos en una o dos direcciones, atadas al original con la restricción de patrón (si el original cambia, las copias lo siguen). La dirección 1 sale del ángulo angle (o de la línea direction1_line) y la 2 de angle2 (por defecto perpendicular, +90°) o de direction2_line. Con spacing=extent la distancia es la total (de la primera a la última copia); con spacing la de cada paso. suppress omite copias por índice (get_sketch › patterns); después se edita con edit_sketch_pattern. Tope: 200 puntos copiados (copias × puntos de la selección; un rectángulo tiene 4) y 200 copias, para que el boceto no se vuelva lento: tope propio, la ayuda de Fusion no publica un máximo.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entities` (lista de entero; obligatorio): ids de las curvas o puntos a repetir (get_sketch).
  - `count1` (entero; obligatorio): cantidad en la dirección 1, contando el original.
  - `distance1` (número; obligatorio): distancia en la dirección 1 (mm; total o por paso según spacing; negativa = sentido contrario).
  - `count2` (entero; opcional, por defecto `1`): cantidad en la dirección 2 (1 = una sola fila).
  - `distance2` (número; opcional, por defecto `0.0`): distancia en la dirección 2 (mm).
  - `angle` (número; opcional, por defecto `0.0`): dirección 1 en grados respecto del eje x del boceto.
  - `spacing` ("extent" | "spacing"; opcional, por defecto `"extent"`): extent (distancia total) o spacing (distancia entre copias).
  - `symmetric` (true/false; opcional, por defecto `false`): true para repartir las copias a los dos lados del original.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `angle2` (número; opcional, por defecto `null`): dirección 2 en grados respecto del eje x; vacío = angle + 90°.
  - `direction1_line` (entero; opcional, por defecto `null`): id de una línea del boceto que da la dirección 1 (de su inicio a su fin); pisa a angle.
  - `direction2_line` (entero; opcional, por defecto `null`): id de una línea del boceto que da la dirección 2; pisa a angle2.
  - `suppress` (lista de entero o null; opcional, por defecto `null`): índices de las copias que no se crean (get_sketch › patterns las lista).
- CLI: `omnicad call sketch_rectangular_pattern --doc pieza.omnicad entities=… count1=… distance1=…`

### `sketch_circular_pattern`

Patrón circular de boceto (Fusion: Patrón circular en el boceto): copias de curvas y puntos alrededor de un centro, atadas al original con la restricción de patrón. total_angle = 360 reparte la cantidad en la vuelta entera; otro ángulo pone la primera y la última copia en sus extremos. suppress omite copias por índice; después se edita con edit_sketch_pattern. Tope: 200 puntos copiados (copias × puntos de la selección; un círculo tiene 1) y 200 copias: tope propio, la ayuda de Fusion no publica un máximo.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entities` (lista de entero; obligatorio): ids de las curvas o puntos a repetir (get_sketch).
  - `count` (entero; obligatorio): cantidad total, contando el original (2 o más).
  - `center_x` (número; opcional, por defecto `0.0`): x del centro (mm), si no se da center_point.
  - `center_y` (número; opcional, por defecto `0.0`): y del centro (mm).
  - `center_point` (entero; opcional, por defecto `null`): id de un punto del boceto que hace de centro (las copias lo siguen); pisa center_x/center_y.
  - `total_angle` (número; opcional, por defecto `360.0`): ángulo total en grados (360 = vuelta entera; negativo = sentido horario).
  - `symmetric` (true/false; opcional, por defecto `false`): true para repartir las copias a los dos lados del original (si total_angle no es 360).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `suppress` (lista de entero o null; opcional, por defecto `null`): índices de las copias que no se crean (get_sketch › patterns las lista).
- CLI: `omnicad call sketch_circular_pattern --doc pieza.omnicad entities=… count=…`

### `edit_sketch_pattern`

Edita un patrón de boceto ya hecho (Fusion: doble clic en el glifo del patrón): cantidades, distancias, direcciones, simetría y copias suprimidas. Regenera las copias: las restricciones y cotas puestas sobre una copia pasan a la copia nueva del mismo índice; las de copias que ya no existen se borran y se listan en lost_references (con aviso). pattern es el id que devolvió la herramienta que lo creó (o get_sketch › patterns). Los parámetros count1, distance1, count2, distance2, angle, angle2, spacing, direction1_line y direction2_line son de un patrón rectangular; count y total_angle, de uno circular. suppress reemplaza la lista de copias suprimidas ([] = ninguna).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `pattern` (entero; obligatorio): id del patrón (lo devuelve la herramienta que lo creó; get_sketch › patterns lo lista).
  - `count1` (entero; opcional, por defecto `null`): cantidad en la dirección 1 (rectangular).
  - `distance1` (número; opcional, por defecto `null`): distancia en la dirección 1 (rectangular).
  - `count2` (entero; opcional, por defecto `null`): cantidad en la dirección 2 (rectangular).
  - `distance2` (número; opcional, por defecto `null`): distancia en la dirección 2 (rectangular).
  - `angle` (número; opcional, por defecto `null`): dirección 1 en grados (rectangular); si no se da angle2, la dirección 2 pasa a angle + 90°.
  - `angle2` (número; opcional, por defecto `null`): dirección 2 en grados (rectangular).
  - `spacing` ("extent" | "spacing" o null; opcional, por defecto `null`): extent o spacing (rectangular).
  - `symmetric` (true/false; opcional, por defecto `null`): repartir las copias a los dos lados del original.
  - `direction1_line` (entero; opcional, por defecto `null`): id de una línea que da la dirección 1 (rectangular).
  - `direction2_line` (entero; opcional, por defecto `null`): id de una línea que da la dirección 2 (rectangular).
  - `count` (entero; opcional, por defecto `null`): cantidad total, contando el original (circular).
  - `total_angle` (número; opcional, por defecto `null`): ángulo total en grados (circular).
  - `suppress` (lista de entero o null; opcional, por defecto `null`): índices de copias suprimidas; reemplaza la lista actual ([] = ninguna).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call edit_sketch_pattern --doc pieza.omnicad pattern=…`

### `project_to_sketch`

Proyecta aristas, caras, cuerpos, planos, ejes y puntos de trabajo, o curvas y puntos de otro boceto, sobre el plano del boceto (Fusion: Proyectar) o agrega donde cortan ese plano (mode=intersect; Fusion: Intersecar). La geometría queda proyectada: fija (violeta en la interfaz), sirve para restricciones, cotas y perfiles, y con link=true (por defecto) sigue al modelo si después cambia; con link=false queda congelada. Si el vínculo se pierde: manage_lost_projections; para soltarlo: break_projection_link. Un eje o la traza de un plano (infinitos) se dibujan como una línea que llega al 110 % de lo más lejano entre el modelo y la geometría del boceto, y crece con el boceto al recalcular (±100 mm si no hay nada alrededor). edges y faces aceptan selectores (con body si hay varios cuerpos) o ids de find_edges / find_faces; vertices, las coordenadas [x, y, z] de vértices del modelo (proyecta o interseca puntos).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `edges` (lista de texto o texto o null; opcional, por defecto `null`): aristas a proyectar: selector ('|Z', '%CIRCLE and >Z') o ids ('Cuerpo1/E3'); vacío = ninguna.
  - `faces` (lista de texto o texto o null; opcional, por defecto `null`): caras a proyectar (su contorno): selector o ids ('Cuerpo1/F6'); vacío = ninguna.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de cuerpos enteros; vacío = ninguno.
  - `mode` ("project" | "intersect"; opcional, por defecto `"project"`): project (proyección ortogonal) o intersect (corte con el plano del boceto).
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de edges y faces; vacío = el único cuerpo.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true = la geometría proyectada queda como línea de construcción (no forma perfiles).
  - `vertices` (lista de lista de número o null; opcional, por defecto `null`): vértices del modelo por sus coordenadas [[x, y, z], …] (a menos de 0,001 mm de un vértice; con body, solo los de ese cuerpo): se proyectan (o intersecan) como puntos del boceto.
  - `link` (true/false; opcional, por defecto `true`): true = asociativa (sigue al modelo); false = congelada, sin vínculo.
  - `references` (lista de texto o objeto o null; opcional, por defecto `null`): planos ("XY", id o nombre), ejes ("X", id o nombre), puntos de trabajo ("O", id o nombre), y curvas o puntos de otro boceto ({"sketch": "Boceto1", "curve": 3} o {"sketch": …, "point": 2}).
- CLI: `omnicad call project_to_sketch --doc pieza.omnicad`

### `project_spun_profile`

Proyecta el perfil giratorio de la geometría (Fusion: Proyectar › Spun Profile): gira aristas, caras, cuerpos o vértices alrededor de un eje y deja su perfil sobre el plano del boceto, para referenciarlo en el boceto o en operaciones de revolución y torneado. El eje se proyecta en el plano; cada punto va a su posición a lo largo del eje y su distancia a él (hacia +u del boceto, o al otro lado con flip). Las curvas se aproximan con segmentos a tolerance mm. Por defecto queda solo el contorno exterior (la silueta de radio máximo y los frentes de sus extremos, sin las aristas que caen dentro); outer_contour=false gira todas las aristas. project_axis=true (Fusion: Project Axis) proyecta también el eje como línea, con vínculo (axis_projection). Con link=true (por defecto) sigue al modelo, igual que project_to_sketch (break_projection_link, manage_lost_projections, incluido relink).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `axis` (texto o objeto; obligatorio): eje de giro: "X", "Y", "Z", un eje de construcción (id o nombre), una arista recta, una línea de boceto ({"sketch", "curve"}) o una cara cilíndrica.
  - `edges` (lista de texto o texto o null; opcional, por defecto `null`): aristas a girar: selector o ids ('Cuerpo1/E3').
  - `faces` (lista de texto o texto o null; opcional, por defecto `null`): caras a girar: selector o ids ('Cuerpo1/F6').
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de cuerpos enteros.
  - `vertices` (lista de lista de número o null; opcional, por defecto `null`): vértices del modelo por sus coordenadas [[x, y, z], …].
  - `tolerance` (número; opcional, por defecto `0.1`): distancia máxima en mm entre la curva y los segmentos del perfil (mayor que cero).
  - `flip` (true/false; opcional, por defecto `false`): true pone el perfil del otro lado del eje.
  - `link` (true/false; opcional, por defecto `true`): true = asociativo (sigue al modelo); false = congelado.
  - `construction` (true/false; opcional, por defecto `false`): true = el perfil queda como líneas de construcción.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `outer_contour` (true/false; opcional, por defecto `true`): true = solo el contorno exterior; false = todas las aristas giradas, también las internas.
  - `project_axis` (true/false; opcional, por defecto `false`): true = proyecta también el eje de giro al boceto (otra proyección, con el mismo link).
- CLI: `omnicad call project_spun_profile --doc pieza.omnicad axis=…`

### `break_projection_link`

Rompe el vínculo de una proyección (Fusion: Break Link): la geometría proyectada queda donde está como geometría normal, editable y ya no fija, y no sigue más al modelo.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `projection` (entero; obligatorio): id de la proyección (lo devuelve project_to_sketch; get_sketch › projections lo lista).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call break_projection_link --doc pieza.omnicad projection=…`

### `manage_lost_projections`

Administra las proyecciones perdidas de un boceto (Fusion: Manage Lost Projections): las que ya no coinciden con el modelo (get_sketch › projections las marca con lost). relink las vuelve a vincular a otra selección (misma forma que la original: edges, faces, bodies, vertices o references); break les rompe el vínculo y delete borra su geometría. Con break y delete, sin projection actúa sobre todas las perdidas (Break Link All / Delete All).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `action` ("relink" | "break" | "delete"; obligatorio): relink, break o delete.
  - `projection` (entero; opcional, por defecto `null`): id de la proyección; vacío = todas las perdidas (solo con break y delete).
  - `edges` (lista de texto o texto o null; opcional, por defecto `null`): relink: aristas nuevas (selector o ids).
  - `faces` (lista de texto o texto o null; opcional, por defecto `null`): relink: caras nuevas.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): relink: cuerpos nuevos.
  - `vertices` (lista de lista de número o null; opcional, por defecto `null`): relink: vértices nuevos por coordenadas [x, y, z].
  - `references` (lista de texto o objeto o null; opcional, por defecto `null`): relink: planos, ejes, puntos de trabajo o curvas de otro boceto, como en project_to_sketch.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call manage_lost_projections --doc pieza.omnicad action=…`

### `set_line_type`

Cambia el tipo de línea de curvas del boceto (Fusion: Construcción / Línea central de la paleta): normal (forma perfiles), construction (de construcción: guía, no forma perfiles) o centerline (eje: forma perfiles y sirve de eje de revolución).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entities` (lista de entero; obligatorio): ids de las curvas (get_sketch).
  - `line_type` ("normal" | "construction" | "centerline"; obligatorio): normal, construction o centerline (centerline solo en curvas que no son texto).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call set_line_type --doc pieza.omnicad entities=… line_type=…`

### `edit_dimension`

Cambia el valor de una cota que ya existe (Fusion: doble clic en la cota): número o expresión con parámetros. La geometría se mueve para cumplirla. Si choca con las otras restricciones y cotas, falla y el boceto queda como estaba. Con `offset` y `text_offset` mueve la línea de cota y su texto sin cambiar el valor (cotas lineales); `position` [x, y] la mueve como el arrastre con el ratón, en cualquier cota. Mantiene sincronizado el parámetro dN; rechaza dependencias circulares. reference alterna driving/driven. Al pasar a referencia se pierde la expresión y se mide la geometría; su valor no es editable. Si volver a driving sobre-restringiría, sigue de referencia con aviso y el documento queda como estaba. `type` alterna radius ↔ diameter conservando el valor equivalente (la geometría no cambia). `mode` cambia una distancia con un círculo o arco entre center y tangent: la expresión queda y la geometría se mueve para cumplirla. `near` [x, y] cambia qué ángulo mide una cota de ángulo (el del cuadrante que contiene el punto): igual que mode, la expresión queda. Para borrar una cota o una restricción: delete_sketch_entities con su id.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `dimension` (entero; obligatorio): id de la cota (get_sketch la lista en dimensions).
  - `value` (número o expresión; opcional, por defecto `null`): valor nuevo: número (mm; grados en una cota de ángulo) o expresión con parámetros ("ancho / 2"); vacío = no cambia el valor.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `offset` (número; opcional, por defecto `null`): mm que se separa la línea de cota de la medida (con signo); vacío = no cambia.
  - `text_offset` (número; opcional, por defecto `null`): mm que se corre el texto a lo largo de la línea de cota desde su centro; vacío = no cambia.
  - `reference` (true/false; opcional, por defecto `null`): true = convertir a referencia (driven); false = driving; vacío = no cambia. Una alternancia redundante o en conflicto avisa y conserva la referencia sin modificar el documento.
  - `type` ("radius" | "diameter" o null; opcional, por defecto `null`): radius o diameter: pasa una cota de radio a diámetro (o al revés) con el valor equivalente; vacío = no cambia.
  - `mode` ("center" | "tangent" o null; opcional, por defecto `null`): center o tangent en una distancia con un círculo o arco; vacío = no cambia.
  - `near` (lista de número o null; opcional, por defecto `null`): [x, y] en mm, solo en una cota de ángulo: pasa a medir el ángulo del cuadrante que contiene este punto; vacío = no cambia.
  - `position` (lista de número o null; opcional, por defecto `null`): [x, y] en mm: mueve la cota ahí, como arrastrarla con el ratón (no cambia el valor ni la geometría); no se combina con offset ni text_offset; vacío = no cambia.
- CLI: `omnicad call edit_dimension --doc pieza.omnicad dimension=…`

### `auto_constrain`

Restringe automáticamente el boceto (Fusion: AutoConstrain): detecta lo que ya se cumple y lo agrega como restricción (coincidente, concéntrica, horizontal, vertical, colineal, paralela, perpendicular, tangente, igual, punto medio, simetría respecto de una línea central o de construcción) y después cotas con las medidas actuales (largos, radios, ángulos y posiciones desde un punto fijo en el origen o desde el datum) hasta dejarlo totalmente restringido si se puede. Cada agregado se prueba solo: nada entra en conflicto ni mueve la geometría fuera de las tolerancias. Con suggest_auto_constraints se ven las alternativas antes de aplicar; acá las cotas quedan como números (cambialas con edit_dimension).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `tolerance_angle` (número; opcional, por defecto `1.0`): grados (0 a 45) dentro de los cuales una línea cuenta como horizontal, vertical, paralela o perpendicular.
  - `tolerance_distance` (número; opcional, por defecto `0.001`): mm (hasta 10) dentro de los cuales dos cosas cuentan como coincidentes, tangentes, colineales, concéntricas, en el punto medio o simétricas.
  - `types` (lista de texto o null; opcional, por defecto `null`): familias a inferir: coincident, concentric, horizontal, vertical, collinear, parallel, perpendicular, tangent, equal, midpoint, symmetry y dimensions (dato y cotas); vacío = todas.
  - `max_items` (entero; opcional, por defecto `null`): tope de restricciones y cotas a agregar (las primeras por prioridad); vacío = sin tope.
  - `datum` (entero; opcional, por defecto `null`): id de un punto del boceto desde el que se miden las posiciones (como Set datum de Fusion); vacío = el origen.
  - `exclude` (lista de objeto o null; opcional, por defecto `null`): sugerencias a no agregar, como los items de la respuesta: {kind: constraint o dimension, type, entities}.
- CLI: `omnicad call auto_constrain --doc pieza.omnicad`

### `suggest_auto_constraints`

Calcula alternativas de AutoConstrain SIN cambiar el boceto (Fusion: el diálogo con varios resultados). Cada resultado trae lo que agregaría (items, en orden de prioridad, con los grados de libertad que quedan tras cada uno) y si deja el boceto totalmente restringido: «Completo», «Solo restricciones», «Estricto» (tolerancias 10 veces menores) y una por cada punto elegido como datum. Para aplicar una, llamá a auto_constrain con las mismas opciones (max_items = cuántos items querés; exclude = los que sacás; datum). Las alternativas que dan lo mismo que otra anterior se saltean.

- Modifica el documento: no.
- Parámetros:
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `results` (entero; opcional, por defecto `1`): cuántas alternativas pedir (1 a 12); pedir más es «Generate more».
  - `tolerance_angle` (número; opcional, por defecto `1.0`): grados (0 a 45) dentro de los cuales una línea cuenta como horizontal, vertical, paralela o perpendicular.
  - `tolerance_distance` (número; opcional, por defecto `0.001`): mm (hasta 10) dentro de los cuales dos cosas cuentan como coincidentes, tangentes, colineales, concéntricas, en el punto medio o simétricas.
  - `types` (lista de texto o null; opcional, por defecto `null`): familias a inferir: coincident, concentric, horizontal, vertical, collinear, parallel, perpendicular, tangent, equal, midpoint, symmetry y dimensions (dato y cotas); vacío = todas.
  - `max_items` (entero; opcional, por defecto `null`): tope de restricciones y cotas por resultado (las primeras por prioridad); vacío = sin tope.
  - `datum` (entero; opcional, por defecto `null`): id de un punto del boceto desde el que se miden las posiciones; vacío = el origen.
  - `exclude` (lista de objeto o null; opcional, por defecto `null`): sugerencias a no incluir, como los items de una respuesta anterior: {kind: constraint o dimension, type, entities}.
- CLI: `omnicad call suggest_auto_constraints --doc pieza.omnicad`

### `create_construction_axis`

Crea un eje con cualquiera de las cinco variantes de CONSTRUIR.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `type` ("cilindro" | "perpendicular_cara" | "dos_planos" | "dos_puntos" | "arista"; obligatorio): variante de TIPOS_EJE: cilindro, perpendicular_cara, dos_planos, dos_puntos o arista.
  - `references` (lista de texto o objeto o lista de número; obligatorio): referencias en orden: cara de revolución; cara/plano y punto; dos planos; dos puntos; arista/eje. Acepta XY/XZ/YZ, X/Y/Z, O, construcción por id/nombre, selectores, ids de find_faces/find_edges, {sketch, point} o {sketch, curve}; edges: selecciona aristas, faces: caras.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
  - `name` (texto; opcional, por defecto `null`): nombre del eje; vacío = automático.
- CLI: `omnicad call create_construction_axis --doc pieza.omnicad type=… references=…`

### `create_construction_point`

Crea un punto con las seis variantes de CONSTRUIR.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `type` ("vertice" | "dos_aristas" | "tres_planos" | "centro" | "arista_plano" | "ruta"; obligatorio): variante de TIPOS_PUNTO: vertice, dos_aristas, tres_planos, centro, arista_plano o ruta.
  - `references` (lista de texto o objeto o lista de número; obligatorio): referencias en orden: punto/vértice; dos aristas/ejes; tres planos; círculo/esfera/toroide; arista/eje y plano; curva de ruta. Formatos como create_construction_axis, incluidos puntos de boceto.
  - `position` (número o expresión; opcional, por defecto `0.5`): proporción del largo de la ruta entre 0 y 1, número o expresión; solo con ruta.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
  - `name` (texto; opcional, por defecto `null`): nombre del punto; vacío = automático.
- CLI: `omnicad call create_construction_point --doc pieza.omnicad type=… references=…`

### `create_ucs`

Crea un sistema de coordenadas de usuario con origen, ejes, giros y desfases.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `origin` (texto o objeto o lista de número; obligatorio): punto/vértice de origen: O, construcción o {sketch, point}.
  - `x_axis` (texto o objeto o lista de número; opcional, por defecto `"X"`): dirección X: eje, arista recta o línea de boceto; por defecto X.
  - `y_axis` (texto o objeto o lista de número o null; opcional, por defecto `null`): dirección Y opcional; se ortogonaliza respecto de X.
  - `dx` (número o expresión; opcional, por defecto `0`): desfase local X en mm o expresión.
  - `dy` (número o expresión; opcional, por defecto `0`): desfase local Y en mm o expresión.
  - `dz` (número o expresión; opcional, por defecto `0`): desfase local Z en mm o expresión.
  - `rx` (número o expresión; opcional, por defecto `0`): giro X en grados o expresión.
  - `ry` (número o expresión; opcional, por defecto `0`): giro Y en grados o expresión.
  - `rz` (número o expresión; opcional, por defecto `0`): giro Z en grados o expresión.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
  - `name` (texto; opcional, por defecto `null`): nombre del sistema; vacío = automático.
- CLI: `omnicad call create_ucs --doc pieza.omnicad origin=…`

### `draw_line_3d`

Boceto 3D: dibuja una línea en el espacio (Fusion: 3D Sketch › Línea). Coordenadas del boceto en mm: x, y sobre su plano y z a lo largo de su normal (en un boceto sobre XY son las del mundo). Bloqueos de la tríada: axis + length dibuja desde start a lo largo de x, y o z (largo con signo) y deja la restricción de eje; plane = xy, yz o zx deja el final en el plano por start paralelo a ese (copia la coordenada normal de start). Un extremo que cae sobre un punto 3D existente lo comparte (cadena).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `start` (lista de número; obligatorio): punto inicial [x, y, z] en mm (coordenadas del boceto).
  - `end` (lista de número o null; opcional, por defecto `null`): punto final [x, y, z]; vacío si se usa axis + length.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `axis` ("x" | "y" | "z" o null; opcional, por defecto `null`): bloqueo de eje de la tríada: la línea va de start a lo largo de x, y o z (necesita length, sin end).
  - `length` (número; opcional, por defecto `null`): con axis, largo en mm con signo (negativo = sentido contrario del eje).
  - `plane` ("xy" | "yz" | "zx" o null; opcional, por defecto `null`): bloqueo de plano de la tríada: el final queda en el plano xy, yz o zx que pasa por start.
  - `construction` (true/false; opcional, por defecto `false`): true para una línea de construcción (no forma rutas por defecto).
- CLI: `omnicad call draw_line_3d --doc pieza.omnicad start=…`

### `draw_spline_3d`

Boceto 3D: spline de ajuste en el espacio que pasa por points (Fusion: 3D Sketch › Spline), en coordenadas del boceto (x, y sobre el plano, z sobre la normal). Si empieza o termina en el extremo de una línea 3D comparte el punto, y add_constraint_3d type=tangent la deja tangente a esa línea.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `points` (lista de lista de número; obligatorio): puntos de paso [[x, y, z], …] en mm, al menos dos.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para una spline de construcción.
- CLI: `omnicad call draw_spline_3d --doc pieza.omnicad points=…`

### `draw_point_3d`

Boceto 3D: punto suelto en el espacio (Fusion: 3D Sketch › Punto), en coordenadas del boceto. Sirve de referencia para restricciones y cotas 3D.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `x` (número; obligatorio): x en mm (sobre el plano del boceto).
  - `y` (número; obligatorio): y en mm (sobre el plano del boceto).
  - `z` (número; obligatorio): z en mm (a lo largo de la normal del boceto).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call draw_point_3d --doc pieza.omnicad x=… y=… z=…`

### `add_constraint_3d`

Boceto 3D: restricción entre entidades 3D (ids de get_sketch). type: coincident (punto–punto o punto sobre línea), axis (la Horizontal/Vertical de Fusion en 3D: alinea una línea con el eje axis), parallel, perpendicular, equal y collinear (dos líneas), tangent (línea o spline + spline que empieza o termina en un extremo de la otra; entre dos splines deja continuidad G1), midpoint (punto + línea), concentric (dos arcos, círculos o elipses: mismo centro) y fix (fija los puntos de las entidades). Son las de Fusion en 3D; las demás (simetría, curvatura, horizontal/vertical del plano) Fusion no las ofrece en 3D.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `type` ("coincident" | "axis" | "parallel" | "perpendicular" | "tangent" | "equal" | "midpoint" | "fix" | "concentric" | "collinear"; obligatorio): tipo de restricción (ver la descripción).
  - `entities` (lista de entero; obligatorio): ids de las entidades 3D, en cualquier orden.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `axis` ("x" | "y" | "z" o null; opcional, por defecto `null`): con type=axis, el eje con el que se alinea la línea: x, y o z.
- CLI: `omnicad call add_constraint_3d --doc pieza.omnicad type=… entities=…`

### `add_dimension_3d`

Boceto 3D: cota en el espacio. type=distance: el largo de una línea (un id) o la distancia entre dos puntos 3D, en mm. type=angle: el ángulo entre dos líneas 3D, en grados (0 < ángulo < 180). value: número o expresión con parámetros (sigue al parámetro al recalcular).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entities` (lista de entero; obligatorio): [id de una línea 3D] o [id de punto, id de punto]; con type=angle, [id de línea, id de línea].
  - `value` (número o expresión; obligatorio): medida en mm (o en grados con type=angle): número o expresión con parámetros, p. ej. "largo / 2" o "30 deg".
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `type` ("distance" | "angle"; opcional, por defecto `"distance"`): distance (distancia o largo) o angle (ángulo entre dos líneas).
- CLI: `omnicad call add_dimension_3d --doc pieza.omnicad entities=… value=…`

### `delete_sketch_entities_3d`

Boceto 3D: borra entidades, restricciones o cotas 3D por id. Con una curva se borran sus restricciones y cotas y los puntos que ninguna otra curva usa; con un punto, las curvas que pasan por él.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entities` (lista de entero; obligatorio): ids 3D a borrar (de get_sketch: entities_3d, points_3d, constraints_3d o dimensions_3d).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call delete_sketch_entities_3d --doc pieza.omnicad entities=…`

### `draw_arc_3d`

Boceto 3D: arco de 3 puntos en el espacio (Fusion: 3D Sketch › Arco): va de start a end pasando por through, en coordenadas del boceto. Sus extremos se encadenan con los puntos 3D que ya estén ahí.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `start` (lista de número; obligatorio): punto inicial [x, y, z] en mm.
  - `through` (lista de número; obligatorio): un punto del arco entre start y end [x, y, z].
  - `end` (lista de número; obligatorio): punto final [x, y, z].
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para un arco de construcción.
- CLI: `omnicad call draw_arc_3d --doc pieza.omnicad start=… through=… end=…`

### `draw_circle_3d`

Boceto 3D: círculo de centro y radio en el plano perpendicular a normal (Fusion: 3D Sketch › Círculo; normal = la del plano de la tríada), en coordenadas del boceto.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `center` (lista de número; obligatorio): centro [x, y, z] en mm.
  - `radius` (número; obligatorio): radio en mm (mayor que 0).
  - `normal` (lista de número o null; opcional, por defecto `null`): normal del plano del círculo [x, y, z]; vacío = [0, 0, 1] (el plano del boceto).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para un círculo de construcción.
- CLI: `omnicad call draw_circle_3d --doc pieza.omnicad center=… radius=…`

### `draw_ellipse_3d`

Boceto 3D: elipse de centro, extremo del eje mayor y radio menor en el plano perpendicular a normal (Fusion: 3D Sketch › Elipse). major_end se proyecta a ese plano.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `center` (lista de número; obligatorio): centro [x, y, z] en mm.
  - `major_end` (lista de número; obligatorio): extremo del eje mayor [x, y, z] (fija su dirección y el semieje mayor).
  - `minor_radius` (número; obligatorio): semieje menor en mm (mayor que 0).
  - `normal` (lista de número o null; opcional, por defecto `null`): normal del plano de la elipse [x, y, z]; vacío = [0, 0, 1].
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para una elipse de construcción.
- CLI: `omnicad call draw_ellipse_3d --doc pieza.omnicad center=… major_end=… minor_radius=…`

### `draw_rectangle_3d`

Boceto 3D: rectángulo de 2 puntos (Fusion: 3D Sketch › Rectángulo) en el plano de la tríada xy, yz o zx que pasa por corner; opposite se proyecta a ese plano. Deja cuatro líneas encadenadas con perpendicular y paralelas (sigue siendo rectángulo al acotarlo).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `corner` (lista de número; obligatorio): esquina [x, y, z] en mm.
  - `opposite` (lista de número; obligatorio): esquina opuesta [x, y, z] (se proyecta al plano).
  - `plane` ("xy" | "yz" | "zx"; opcional, por defecto `"xy"`): plano de la tríada por corner: xy, yz o zx.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para líneas de construcción.
- CLI: `omnicad call draw_rectangle_3d --doc pieza.omnicad corner=… opposite=…`

### `draw_conic_3d`

Boceto 3D: curva cónica (Fusion: 3D Sketch › Curva cónica): de start a end, con shoulder como vértice (cruce de las tangentes de los extremos) y rho (0 < rho < 1: menos de 0,5 elipse, 0,5 parábola, más hipérbola).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `start` (lista de número; obligatorio): extremo inicial [x, y, z] en mm.
  - `shoulder` (lista de número; obligatorio): vértice de control [x, y, z] (donde se cruzan las tangentes de los extremos).
  - `end` (lista de número; obligatorio): extremo final [x, y, z].
  - `rho` (número; opcional, por defecto `0.5`): forma de la cónica, entre 0 y 1 sin incluirlos.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para una cónica de construcción.
- CLI: `omnicad call draw_conic_3d --doc pieza.omnicad start=… shoulder=… end=…`

### `draw_text_3d`

Boceto 3D: texto de una línea en el plano de la tríada (Fusion: 3D Sketch › Texto): la base empieza en origin; en xy corre por x y sube por y, en yz por y y z, en zx por x y z.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `text` (texto; obligatorio): el texto.
  - `origin` (lista de número; obligatorio): inicio de la línea base [x, y, z] en mm.
  - `height` (número; opcional, por defecto `5.0`): altura del texto en mm (mayor que 0).
  - `plane` ("xy" | "yz" | "zx"; opcional, por defecto `"xy"`): plano de la tríada donde queda el texto: xy, yz o zx.
  - `font` (texto; opcional, por defecto `"Arial"`): fuente instalada (list_fonts la lista).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call draw_text_3d --doc pieza.omnicad text=… origin=…`

### `transform_sketch_3d`

Boceto 3D: mover, rotar, escalar o copiar entidades 3D (Fusion: Mover/copiar y Escalar sobre el boceto 3D). Cada punto p va a center + scale·R·(p − center) + translation, con R el giro de rotation_angle grados alrededor de rotation_axis. Con copy deja el original y devuelve las copias. Las restricciones siguen: si el movimiento las contradice, el paso queda en conflicto (SKETCH_OVERCONSTRAINED).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entities` (lista de entero; obligatorio): ids de curvas o puntos 3D.
  - `translation` (lista de número o null; opcional, por defecto `null`): desplazamiento [x, y, z] en mm; vacío = sin mover.
  - `rotation_axis` (lista de número o null; opcional, por defecto `null`): eje del giro [x, y, z]; vacío = [0, 0, 1].
  - `rotation_angle` (número; opcional, por defecto `0.0`): giro en grados alrededor de rotation_axis, por center.
  - `scale` (número; opcional, por defecto `1.0`): factor de escala uniforme (mayor que 0), desde center.
  - `center` (lista de número o null; opcional, por defecto `null`): centro del giro y de la escala [x, y, z]; vacío = el origen del boceto.
  - `copy` (true/false; opcional, por defecto `false`): true copia las entidades (el original queda).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call transform_sketch_3d --doc pieza.omnicad entities=…`

### `intersect_curves`

Boceto 3D: Intersection Curve de Fusion. Con curves: cada curva de boceto se extruye a lo largo de la normal de su boceto y se corta con las caras, cuerpos o planos elegidos; sin curves: las curvas donde se cortan entre sí las caras, cuerpos y planos elegidos (al menos dos). El resultado queda como curvas 3D del boceto (líneas, arcos, círculos y elipses exactos; lo demás, spline por 33 puntos). Si el modelo cambia, se recalculan (source anota de dónde salió); si la referencia se pierde, quedan congeladas con aviso.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `faces` (lista de texto o texto o null; opcional, por defecto `null`): caras a cortar: selector ('%CYLINDER') o ids de find_faces.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de cuerpos enteros.
  - `references` (lista de texto o objeto o null; opcional, por defecto `null`): planos de construcción o de origen ("XY", id o nombre).
  - `curves` (lista de entero o objeto o null; opcional, por defecto `null`): curvas de boceto a extruir y cortar: id de una curva del boceto activo o {"sketch": …, "curve": id}.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de faces; vacío = el único cuerpo.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto 3D donde quedan las curvas; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true deja las curvas como construcción.
- CLI: `omnicad call intersect_curves --doc pieza.omnicad`

### `project_to_surface`

Boceto 3D: Project To Surface de Fusion: proyecta curvas de boceto sobre caras. mode=closest (Closest Point): cada punto de la curva va al punto más cercano de las caras (spline por 49 puntos); mode=vector (Along Vector): proyecta a lo largo de direction (vector [x, y, z] del mundo o un eje: 'X', 'Y', 'Z', id de un eje o una arista recta), hacia donde apunta. El resultado queda como curvas 3D del boceto; si el modelo cambia, se recalculan (source anota de dónde salió); si la referencia se pierde, quedan congeladas con aviso.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `faces` (lista de texto o texto; obligatorio): caras donde proyectar: selector ('>Z') o ids de find_faces.
  - `curves` (lista de entero o objeto; obligatorio): curvas a proyectar: id de una curva del boceto activo (2D o 3D) o {"sketch": …, "curve": id}.
  - `mode` ("closest" | "vector"; opcional, por defecto `"closest"`): closest (punto más cercano) o vector (a lo largo de direction).
  - `direction` (lista de número o texto o null; opcional, por defecto `null`): con mode=vector, la dirección: [x, y, z] del mundo o un eje ('X', 'Y', 'Z', id de eje o arista recta).
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de faces; vacío = el único cuerpo.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto 3D donde quedan las curvas; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true deja las curvas como construcción.
- CLI: `omnicad call project_to_surface --doc pieza.omnicad faces=… curves=…`

### `draw_spiral`

Dibuja la espiral plana del editor como spline cúbica de ajuste abierta. El radio crece pitch mm por vuelta antihoraria. Hasta 200 puntos de ajuste.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): id o nombre del boceto.
  - `center` (lista de número; obligatorio): centro [x, y] en mm sobre el plano del boceto.
  - `start` (lista de número; obligatorio): inicio [x, y] en mm; su distancia al centro es el radio inicial.
  - `turns` (número; obligatorio): cantidad positiva de vueltas, admite fracciones; hasta 200 puntos (8 tramos por vuelta).
  - `pitch` (número; obligatorio): incremento de radio por vuelta en mm, admite valores negativos como el editor.
  - `construction` (true/false; opcional, por defecto `false`): true para una spline de construcción (no forma perfiles).
- CLI: `omnicad call draw_spiral --doc pieza.omnicad sketch=… center=… start=… turns=… pitch=…`

### `set_circle_radius`

Cambia el radio de un círculo o arco libre, sin cota (lo que hace arrastrarlo en el editor): el círculo toma el radio nuevo y en un arco se corren sus extremos libres. Si tiene una cota de radio o diámetro, o las demás restricciones lo impiden, falla (para eso, edit_dimension).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): id o nombre del boceto.
  - `curve` (entero; obligatorio): id del círculo o arco (get_sketch).
  - `radius` (número; obligatorio): radio nuevo en mm, entre 0,000001 y 1.000.000 (1 km).
- CLI: `omnicad call set_circle_radius --doc pieza.omnicad sketch=… curve=… radius=…`

### `extend_sketch_curve`

Alarga una línea o arco hasta la siguiente intersección, desde el extremo más cercano al punto. Falla si no hay una curva que alcanzar.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): id o nombre del boceto.
  - `curve` (entero; obligatorio): id de la línea o arco (get_sketch).
  - `point` (lista de número; obligatorio): [x, y] en mm del plano, cerca del extremo que se quiere alargar.
- CLI: `omnicad call extend_sketch_curve --doc pieza.omnicad sketch=… curve=… point=…`

### `split_sketch_curve`

Parte una curva en las intersecciones más cercanas al punto, como el editor; el punto debe caer sobre la curva. Devuelve los ids en pieces.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): id o nombre del boceto.
  - `curve` (entero; obligatorio): id de la curva (get_sketch); no admite textos ni geometría proyectada.
  - `point` (lista de número; obligatorio): [x, y] en mm sobre la curva (tolerancia 1e-7 mm); elige las intersecciones donde partir.
- CLI: `omnicad call split_sketch_curve --doc pieza.omnicad sketch=… curve=… point=…`

### `redefine_sketch_plane`

Redefine el plano o la cara de un boceto existente conservando curvas, restricciones y cotas. Los perfiles fuera del contorno de la cara se conservan y se informan.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): id o nombre del boceto existente.
  - `plane` (texto; obligatorio): plano XY, XZ, YZ, id/nombre de plano de construcción, selector de cara plana o id de find_faces.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde evaluar el selector de cara; omitido usa el único cuerpo, como create_sketch.
- CLI: `omnicad call redefine_sketch_plane --doc pieza.omnicad sketch=… plane=…`

## Grupo vectores

Texto y vectores: fuentes, texto de boceto, SVG, DXF e imágenes vectorizadas.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`list_fonts`](#list_fonts) | no | Lista las fuentes que puede usar el texto de boceto: todas las instaladas (sistema, usuario y carpetas sumadas con add_font_folder), TrueType, OpenType, colecciones y variables. |
| [`add_font_folder`](#add_font_folder) | no | Suma una carpeta de fuentes (.ttf, .otf, .ttc y las de una línea .shx de AutoCAD) a las que ve OmniCAD en esta sesión. |
| [`add_text`](#add_text) | sí | Escribe un texto en el boceto (un paso de deshacer). |
| [`edit_text`](#edit_text) | sí | Cambia un texto existente del boceto (un paso de deshacer): lo que no se pasa queda como estaba. |
| [`explode_text`](#explode_text) | sí | Desglosa un texto del boceto (Fusion: Explode Text): el texto pasa a ser líneas y splines fijas, que se pueden editar curva por curva. |
| [`inspect_svg`](#inspect_svg) | no | Mira un archivo SVG antes de insertarlo: tamaño en mm, y qué capas (grupos) y colores trae, con la cantidad de trazos de cada uno. |
| [`insert_svg`](#insert_svg) | sí | Inserta un dibujo SVG en un boceto (Fusion: Insertar > Insertar SVG) y lo deja como curvas editables (las curvas Bézier pasan a splines de control; círculos y arcos quedan exactos). |
| [`insert_dxf`](#insert_dxf) | sí | Inserta la geometría 2D de un archivo DXF en un boceto (Fusion: Insertar > Insertar DXF): líneas, arcos, círculos, polilíneas, splines y textos. |
| [`trace_image`](#trace_image) | sí | Vectoriza una imagen (PNG, JPG, BMP, GIF, WEBP) y la inserta en un boceto como contornos cerrados (logos, siluetas, dibujos en blanco y negro). |
| [`export_hidden_line_svg`](#export_hidden_line_svg) | no | Guarda un SVG de líneas ocultas de los cuerpos vistos desde una vista estándar («Export Hidden Line» de Plasticity): las aristas visibles en línea continua gruesa y, con hidden="dashed", las tapadas en trazos finos, en milímetros reales (por scale) y con la Y hacia arriba; cada tipo de línea va en su grupo (VISIBLE, OCULTA, TANGENTE). |
| [`export_sketch`](#export_sketch) | no | Guarda un boceto como archivo 2D para corte láser, vinilo o CNC (Fusion: Guardar como DXF); el formato sale de la extensión: .dxf o .svg. |
| [`combine_profiles`](#combine_profiles) | sí | Une, resta o interseca perfiles (regiones cerradas) del boceto y deja el contorno resultante como curvas nuevas, sin las líneas internas: juntar letras que se pisan, restar un marco, quedarse con lo común. |
| [`offset_profiles`](#offset_profiles) | sí | Desfase (offset) del contorno de perfiles del boceto, con agujeros incluidos: distance > 0 agranda, < 0 achica. |
| [`transform_sketch`](#transform_sketch) | sí | Mueve, gira, escala y/o espeja curvas de un boceto (un paso de deshacer): lo importado de un SVG, un texto, una selección. |
| [`clean_sketch`](#clean_sketch) | sí | Limpia geometría importada (SVG, DXF, imagen vectorizada): borra curvas repetidas, une extremos sueltos a menos de tolerance mm (cierra huecos para que los contornos formen perfiles) y junta líneas seguidas alineadas en una sola. |
| [`move_sketch_point`](#move_sketch_point) | sí | Mueve un punto del boceto (edición de nodos): extremos de líneas y arcos, puntos de control de splines (las curvas Bézier de un SVG), centros. |
| [`delete_sketch_entities`](#delete_sketch_entities) | sí | Borra curvas, puntos, restricciones o cotas del boceto (un paso de deshacer); lo que dependa de ellos se borra también (un punto se lleva sus curvas). |

### `list_fonts`

Lista las fuentes que puede usar el texto de boceto: todas las instaladas (sistema, usuario y carpetas sumadas con add_font_folder), TrueType, OpenType, colecciones y variables. Usá el nombre de la familia en add_text(font=...); font también acepta la ruta a un .ttf/.otf. Las de un trazo (single_line, nombre terminado en SHX, como en Fusion) van primero: sus letras son líneas abiertas para grabar o marcar, no forman perfiles; hay tres propias (Trazo, Cursiva, Extendida) y las .shx de usuario.

- Modifica el documento: no.
- Parámetros:
  - `query` (texto; opcional, por defecto `null`): texto a buscar dentro del nombre de la familia (sin distinguir mayúsculas); vacío = todas.
  - `limit` (entero; opcional, por defecto `100`): cuántas familias devolver como máximo (1 a 1000).
  - `include_styles` (true/false; opcional, por defecto `false`): true para incluir los estilos de cada familia (peso, cursiva y archivo).
- CLI: `omnicad call list_fonts --doc pieza.omnicad`

### `add_font_folder`

Suma una carpeta de fuentes (.ttf, .otf, .ttc y las de una línea .shx de AutoCAD) a las que ve OmniCAD en esta sesión. Para que quede fija, definí la variable de entorno OMNICAD_FUENTES con la carpeta.

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; obligatorio): carpeta con las fuentes (se busca también en sus subcarpetas).
- CLI: `omnicad call add_font_folder --doc pieza.omnicad path=…`

### `add_text`

Escribe un texto en el boceto (un paso de deshacer). Sus letras forman perfiles que se pueden extruir o cortar. (x, y) es el ancla: por defecto la esquina izquierda de la línea base. Varias líneas con '\n'; con box_width > 0 las líneas se parten en palabras. Fuente: cualquier familia instalada (list_fonts) o la ruta a un .ttf/.otf. TEXTO EN CURVA: con path_entity (una línea, arco, círculo, elipse o spline del boceto) las letras siguen esa curva y (x, y, angle) no se usan; para un círculo, texto arriba por fuera = path_side right + path_position 0.25, abajo por dentro = left + 0.75. Opciones de carácter como un panel de diseño: kerning, skew (inclinación), scale_x / scale_y (%), baseline_shift, case (mayúsculas, minúsculas, título, versalitas), underline / strikethrough (simple o doble, forman perfiles) con decoration_thickness, y no_wrap. MARCO (Fusion: el rectángulo de Text): frame=true dibuja 4 líneas de construcción desde (x, y) (esquina de abajo a la izquierda) que se acotan y restringen; el texto se acomoda adentro según align y anchor. height acepta un parámetro («h_texto») y lo sigue. Crea un parámetro de texto Text, Text_1… ligado al contenido. Dentro de {…} vale 'texto' + parámetro, p. ej. {'Rev ' + rev}.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `text` (texto; obligatorio): contenido del parámetro automático Text (Text_1… si ya existe); '\n' separa líneas. Con {parámetro} o {expresión:formato} (p. ej. 'Ancho {ancho:.1f} mm') muestra el valor y se actualiza solo; {'Rev ' + rev} junta texto y valores.
  - `x` (número; opcional, por defecto `0.0`): x del ancla (mm).
  - `y` (número; opcional, por defecto `0.0`): y del ancla (mm).
  - `height` (número o expresión; opcional, por defecto `5.0`): tamaño de la fuente en mm (positivo), o una expresión con parámetros que queda ligada.
  - `angle` (número; opcional, por defecto `0.0`): giro del texto en grados alrededor de pivot (antihorario; por defecto, el ancla).
  - `font` (texto; opcional, por defecto `"Arial"`): familia (Arial, Segoe UI…) o ruta a un archivo de fuente.
  - `bold` (true/false; opcional, por defecto `false`): negrita (el peso más cercano a 700 de la familia).
  - `italic` (true/false; opcional, por defecto `false`): cursiva.
  - `letter_spacing` (número; opcional, por defecto `0.0`): mm extra entre letras (negativo junta).
  - `line_spacing` (número; opcional, por defecto `1.0`): factor del salto de línea de la fuente (1 = el de la fuente).
  - `align` ("left" | "center" | "right" o null; opcional, por defecto `null`): alineación de cada línea dentro de la caja (left, center o right); en curva, qué parte del texto cae en path_position. Vacío = left (recto) o center (en curva).
  - `anchor` ("baseline" | "top" | "middle" | "bottom"; opcional, por defecto `"baseline"`): qué parte del bloque cae sobre (x, y): baseline (línea base de la primera), top, middle o bottom.
  - `box_width` (número; opcional, por defecto `0.0`): ancho de la caja en mm; 0 = sin caja (el bloque mide lo que mide su línea más larga).
  - `flip_h` (true/false; opcional, por defecto `false`): espejo horizontal del texto dentro de su bloque.
  - `flip_v` (true/false; opcional, por defecto `false`): espejo vertical del texto dentro de su bloque.
  - `path_entity` (entero; opcional, por defecto `null`): id de la curva (get_sketch) que sigue el texto; vacío = texto recto.
  - `path_side` ("left" | "right"; opcional, por defecto `"left"`): left = letras a la izquierda del sentido de la curva; right = la recorre al revés (letras del otro lado, se siguen leyendo derechas).
  - `path_position` (número; opcional, por defecto `0.5`): fracción 0-1 del largo de la curva (en su sentido propio) donde cae el texto; un círculo empieza a la derecha y gira antihorario (0.25 = arriba).
  - `path_offset` (número; opcional, por defecto `0.0`): mm entre la curva y la línea base (positivo = hacia el lado de las letras).
  - `fit_path` (true/false; opcional, por defecto `false`): true reparte el texto en todo el largo de la curva.
  - `kerning` (true/false; opcional, por defecto `true`): false ignora los pares de letras (kerning) de la fuente.
  - `skew` (número; opcional, por defecto `0.0`): inclinación de las letras en grados (-80 a 80; no es la cursiva de la fuente).
  - `scale_x` (número; opcional, por defecto `100.0`): ancho de las letras en % del normal (1 a 1000).
  - `scale_y` (número; opcional, por defecto `100.0`): alto de las letras en % del normal (1 a 1000).
  - `baseline_shift` (número; opcional, por defecto `0.0`): mm que sube (+) o baja (-) todo el texto.
  - `case` ("none" | "upper" | "lower" | "title" | "small_caps"; opcional, por defecto `"none"`): none, upper (mayúsculas), lower (minúsculas), title (Título) o small_caps (versalitas); no cambia lo escrito.
  - `underline` ("none" | "single" | "double"; opcional, por defecto `"none"`): none, single o double: barras bajo cada línea, que forman perfiles. No se aplica en curva.
  - `strikethrough` ("none" | "single" | "double"; opcional, por defecto `"none"`): none, single o double: barras a media altura. No se aplica en curva.
  - `decoration_thickness` (número; opcional, por defecto `0.0`): grosor en mm de esas barras (0 = el de la fuente).
  - `no_wrap` (true/false; opcional, por defecto `false`): true hace que box_width no parta las líneas en palabras.
  - `kerning_pairs` (lista de lista de número o null; opcional, por defecto `null`): kerning a mano entre letras: lista de [posición, mm]; la posición i es el hueco entre la letra i-1 y la i (1 = entre la 1.ª y la 2.ª); mm positivo separa, negativo junta.
  - `frame` (true/false; opcional, por defecto `false`): true dibuja el marco del texto (4 líneas de construcción acotables); no va con path_entity.
  - `frame_height` (número; opcional, por defecto `0.0`): alto del marco en mm; 0 = el del texto. El ancho es box_width (0 = el del texto).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `pivot` (lista de número o texto o null; opcional, por defecto `null`): [x, y] en mm o corner:tl, corner:tr, corner:bl, corner:br, corner:center (requiere frame); vacío = el ancla. El marco se crea sin giro antes de elegir su pivote.
- CLI: `omnicad call add_text --doc pieza.omnicad text=…`

### `edit_text`

Cambia un texto existente del boceto (un paso de deshacer): lo que no se pasa queda como estaba. Los perfiles de las letras se recalculan; lo que dependa de ellos (extrusiones) sigue al texto.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entity` (entero; obligatorio): id de la curva de texto (get_sketch).
  - `text` (texto; opcional, por defecto `null`): texto nuevo ('\n' separa líneas; {parámetro} muestra su valor); actualiza su parámetro Text si lo tiene.
  - `x` (número; opcional, por defecto `null`): x nueva del ancla (mm).
  - `y` (número; opcional, por defecto `null`): y nueva del ancla (mm).
  - `height` (número o expresión; opcional, por defecto `null`): tamaño nuevo de la fuente en mm, o una expresión con parámetros que queda ligada.
  - `angle` (número; opcional, por defecto `null`): giro nuevo en grados (el texto y su marco giran alrededor de pivot).
  - `font` (texto; opcional, por defecto `null`): familia o ruta de la fuente nueva.
  - `bold` (true/false; opcional, por defecto `null`): negrita.
  - `italic` (true/false; opcional, por defecto `null`): cursiva.
  - `letter_spacing` (número; opcional, por defecto `null`): mm extra entre letras.
  - `line_spacing` (número; opcional, por defecto `null`): factor del salto de línea.
  - `align` ("left" | "center" | "right" o null; opcional, por defecto `null`): left, center o right.
  - `anchor` ("baseline" | "top" | "middle" | "bottom" o null; opcional, por defecto `null`): baseline, top, middle o bottom.
  - `box_width` (número; opcional, por defecto `null`): ancho de la caja en mm (0 = sin caja).
  - `flip_h` (true/false; opcional, por defecto `null`): espejo horizontal.
  - `flip_v` (true/false; opcional, por defecto `null`): espejo vertical.
  - `path_entity` (entero; opcional, por defecto `null`): id de la curva que sigue el texto; 0 = quitar la curva (texto recto otra vez).
  - `path_side` ("left" | "right" o null; opcional, por defecto `null`): left o right (lado de la curva).
  - `path_position` (número; opcional, por defecto `null`): fracción 0-1 del largo de la curva.
  - `path_offset` (número; opcional, por defecto `null`): mm entre la curva y la línea base.
  - `fit_path` (true/false; opcional, por defecto `null`): repartir el texto en todo el largo.
  - `kerning` (true/false; opcional, por defecto `null`): false ignora los pares de letras de la fuente.
  - `skew` (número; opcional, por defecto `null`): inclinación de las letras en grados (-80 a 80).
  - `scale_x` (número; opcional, por defecto `null`): ancho de las letras en % (1 a 1000).
  - `scale_y` (número; opcional, por defecto `null`): alto de las letras en % (1 a 1000).
  - `baseline_shift` (número; opcional, por defecto `null`): mm que sube (+) o baja (-) todo el texto.
  - `case` ("none" | "upper" | "lower" | "title" | "small_caps" o null; opcional, por defecto `null`): none, upper, lower, title o small_caps.
  - `underline` ("none" | "single" | "double" o null; opcional, por defecto `null`): none, single o double.
  - `strikethrough` ("none" | "single" | "double" o null; opcional, por defecto `null`): none, single o double.
  - `decoration_thickness` (número; opcional, por defecto `null`): grosor en mm de las barras (0 = el de la fuente).
  - `no_wrap` (true/false; opcional, por defecto `null`): true hace que box_width no parta las líneas.
  - `kerning_pairs` (lista de lista de número o null; opcional, por defecto `null`): kerning a mano entre letras: lista de [posición, mm] (reemplaza la anterior; [] la borra).
  - `pivot` (lista de número o texto o null; opcional, por defecto `null`): [x, y] en mm o corner:tl, corner:tr, corner:bl, corner:br, corner:center del marco actual; vacío = el ancla del texto.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call edit_text --doc pieza.omnicad entity=…`

### `explode_text`

Desglosa un texto del boceto (Fusion: Explode Text): el texto pasa a ser líneas y splines fijas, que se pueden editar curva por curva. Ya no se puede cambiar la fuente ni el contenido.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entity` (entero; obligatorio): id de la curva de texto (get_sketch).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call explode_text --doc pieza.omnicad entity=…`

### `inspect_svg`

Mira un archivo SVG antes de insertarlo: tamaño en mm, y qué capas (grupos) y colores trae, con la cantidad de trazos de cada uno. Sirve para elegir layers o colors de insert_svg.

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; obligatorio): ruta del archivo .svg.
- CLI: `omnicad call inspect_svg --doc pieza.omnicad path=…`

### `insert_svg`

Inserta un dibujo SVG en un boceto (Fusion: Insertar > Insertar SVG) y lo deja como curvas editables (las curvas Bézier pasan a splines de control; círculos y arcos quedan exactos). Con plane crea un boceto nuevo sobre ese plano o cara; sin plane suma el dibujo al boceto sketch (por defecto el último). Orden: voltear, escalar (o ajustar a width), girar y mover. Con layers o colors importa solo esa parte del archivo (inspect_svg dice cuáles hay).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `path` (texto; obligatorio): ruta del archivo .svg.
  - `plane` (texto; opcional, por defecto `null`): "XY", "XZ", "YZ", un plano de construcción o una cara plana: crea un boceto nuevo ahí. Vacío = usar sketch.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto donde sumar el dibujo (sin plane); vacío = el último boceto.
  - `scale` (número; opcional, por defecto `1.0`): factor de escala sobre el tamaño del archivo (1 = tal cual, en mm reales).
  - `width` (número; opcional, por defecto `null`): ancho final del dibujo en mm (pisa a scale); el alto sigue la proporción.
  - `x` (número; opcional, por defecto `0.0`): desplazamiento en X del boceto (mm), después de escalar y girar.
  - `y` (número; opcional, por defecto `0.0`): desplazamiento en Y del boceto (mm).
  - `angle` (número; opcional, por defecto `0.0`): giro en grados (antihorario) alrededor del origen del boceto.
  - `flip_h` (true/false; opcional, por defecto `false`): espejo horizontal alrededor del centro del dibujo.
  - `flip_v` (true/false; opcional, por defecto `false`): espejo vertical alrededor del centro del dibujo.
  - `layers` (lista de texto o null; opcional, por defecto `null`): solo los grupos con estos ids o etiquetas (inkscape:label); vacío = todo.
  - `colors` (lista de texto o null; opcional, por defecto `null`): solo los trazos o rellenos de estos colores, como '#rrggbb'; vacío = todo.
  - `name` (texto; opcional, por defecto `null`): nombre del boceto nuevo (con plane); vacío = "BocetoN".
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúa el selector de cara de plane.
- CLI: `omnicad call insert_svg --doc pieza.omnicad path=…`

### `insert_dxf`

Inserta la geometría 2D de un archivo DXF en un boceto (Fusion: Insertar > Insertar DXF): líneas, arcos, círculos, polilíneas, splines y textos. Mismo manejo de plane / sketch / transformación que insert_svg. Las unidades del DXF se pasan a mm.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `path` (texto; obligatorio): ruta del archivo .dxf.
  - `plane` (texto; opcional, por defecto `null`): "XY", "XZ", "YZ", un plano de construcción o una cara plana: crea un boceto nuevo ahí. Vacío = usar sketch.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto donde sumar el dibujo (sin plane); vacío = el último boceto.
  - `scale` (número; opcional, por defecto `1.0`): factor de escala (1 = tal cual).
  - `width` (número; opcional, por defecto `null`): ancho final del dibujo en mm (pisa a scale).
  - `x` (número; opcional, por defecto `0.0`): desplazamiento en X (mm).
  - `y` (número; opcional, por defecto `0.0`): desplazamiento en Y (mm).
  - `angle` (número; opcional, por defecto `0.0`): giro en grados alrededor del origen del boceto.
  - `flip_h` (true/false; opcional, por defecto `false`): espejo horizontal alrededor del centro del dibujo.
  - `flip_v` (true/false; opcional, por defecto `false`): espejo vertical alrededor del centro del dibujo.
  - `name` (texto; opcional, por defecto `null`): nombre del boceto nuevo (con plane).
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúa el selector de cara de plane.
- CLI: `omnicad call insert_dxf --doc pieza.omnicad path=…`

### `trace_image`

Vectoriza una imagen (PNG, JPG, BMP, GIF, WEBP) y la inserta en un boceto como contornos cerrados (logos, siluetas, dibujos en blanco y negro). Mismo manejo de plane / sketch / transformación que insert_svg. Los agujeros salen como contornos aparte (forman perfiles anillo). Con curves=true cada contorno es UNA spline suave; con false, una polilínea simplificada. El tamaño sale de width (mm) o, si falta, de dpi.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `path` (texto; obligatorio): ruta de la imagen.
  - `plane` (texto; opcional, por defecto `null`): "XY", "XZ", "YZ", un plano de construcción o una cara plana: crea un boceto nuevo ahí. Vacío = usar sketch.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto donde sumar el dibujo (sin plane); vacío = el último boceto.
  - `width` (número; opcional, por defecto `null`): ancho final en mm; vacío = el ancho de la imagen en píxeles según dpi.
  - `dpi` (número; opcional, por defecto `96.0`): píxeles por pulgada para el tamaño cuando no hay width.
  - `threshold` (número; opcional, por defecto `null`): umbral de la tinta (1 a 254); vacío = automático (Otsu).
  - `invert` (true/false; opcional, por defecto `false`): true si la tinta es lo claro (letras blancas sobre fondo oscuro).
  - `smoothing` (número; opcional, por defecto `1.0`): suavizado previo en píxeles (0 = ninguno); quita el ruido y el dentado.
  - `tolerance` (número; opcional, por defecto `0.5`): desvío máximo al simplificar los contornos, en píxeles (más alto = menos puntos).
  - `min_area` (número; opcional, por defecto `4.0`): los contornos de menos píxeles² se descartan como ruido.
  - `channel` ("auto" | "luminance" | "alpha"; opcional, por defecto `"auto"`): auto (usa la transparencia si la hay), luminance o alpha.
  - `curves` (true/false; opcional, por defecto `false`): true = una spline suave por contorno; false = polilínea.
  - `x` (número; opcional, por defecto `0.0`): desplazamiento en X (mm).
  - `y` (número; opcional, por defecto `0.0`): desplazamiento en Y (mm).
  - `angle` (número; opcional, por defecto `0.0`): giro en grados alrededor del origen del boceto.
  - `flip_h` (true/false; opcional, por defecto `false`): espejo horizontal alrededor del centro del dibujo.
  - `flip_v` (true/false; opcional, por defecto `false`): espejo vertical alrededor del centro del dibujo.
  - `name` (texto; opcional, por defecto `null`): nombre del boceto nuevo (con plane).
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúa el selector de cara de plane.
- CLI: `omnicad call trace_image --doc pieza.omnicad path=…`

### `export_hidden_line_svg`

Guarda un SVG de líneas ocultas de los cuerpos vistos desde una vista estándar («Export Hidden Line» de Plasticity): las aristas visibles en línea continua gruesa y, con hidden="dashed", las tapadas en trazos finos, en milímetros reales (por scale) y con la Y hacia arriba; cada tipo de línea va en su grupo (VISIBLE, OCULTA, TANGENTE). Las vistas son las del ViewCube, con Z arriba y nombradas por los ejes del MUNDO (front: cámara en -Y, se ve la cara -Y con +X a la derecha). Dibuja con eliminación exacta de líneas ocultas de OpenCascade; con roscas modeladas o superficies B-spline el método exacto tiene tope de tiempo (15 s) y, si no termina, sigue con el rápido (aristas curvas poligonales) y lo avisa. Las mallas no se proyectan.

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; obligatorio): ruta del archivo .svg a escribir.
  - `view` ("front" | "back" | "top" | "bottom" | "right" | "left" | "iso"; opcional, por defecto `"front"`): vista estándar: front, back, top, bottom, right, left o iso (esquina frente-derecha-arriba).
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos a dibujar; vacío = todos los sólidos y superficies.
  - `hidden` ("dashed" | "none"; opcional, por defecto `"dashed"`): dashed = las aristas tapadas salen en trazos; none = no se dibujan.
  - `scale` (número; opcional, por defecto `1.0`): factor de escala del dibujo (1 = 1 mm del modelo es 1 mm del SVG; 0,5 = a la mitad).
  - `overwrite` (true/false; opcional, por defecto `false`): true para reemplazar el archivo si ya existe.
  - `method` ("auto" | "exact" | "fast"; opcional, por defecto `"auto"`): auto = exacto y, si pasa el tope de tiempo, rápido; exact = solo exacto (falla si no termina); fast = rápido siempre (aristas curvas poligonales).
- CLI: `omnicad call export_hidden_line_svg --doc pieza.omnicad path=…`

### `export_sketch`

Guarda un boceto como archivo 2D para corte láser, vinilo o CNC (Fusion: Guardar como DXF); el formato sale de la extensión: .dxf o .svg. Las letras del texto salen como curvas. En SVG el dibujo queda con su esquina inferior izquierda en el origen y en milímetros reales; la geometría de construcción va en un grupo aparte (DXF: capa CONSTRUCCION) y solo si include_construction.

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; obligatorio): ruta del archivo a escribir (.dxf o .svg).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `include_construction` (true/false; opcional, por defecto `false`): true para incluir las curvas de construcción.
  - `overwrite` (true/false; opcional, por defecto `false`): true para reemplazar el archivo si ya existe.
- CLI: `omnicad call export_sketch --doc pieza.omnicad path=…`

### `combine_profiles`

Une, resta o interseca perfiles (regiones cerradas) del boceto y deja el contorno resultante como curvas nuevas, sin las líneas internas: juntar letras que se pisan, restar un marco, quedarse con lo común. Con keep_original=false (por defecto) se borran las curvas de los perfiles usados (un texto usado se borra entero). Índices de perfil: get_sketch.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `profiles` (lista de entero o texto; obligatorio): índices de los perfiles (o "all"); en subtract e intersect son los que se cortan.
  - `operation` ("union" | "subtract" | "intersect"; opcional, por defecto `"union"`): union (todo junto), subtract (profiles menos tool_profiles) o intersect (lo común).
  - `tool_profiles` (lista de entero o null; opcional, por defecto `null`): índices de los perfiles herramienta (subtract e intersect); en union se suman a profiles.
  - `keep_original` (true/false; opcional, por defecto `false`): true para dejar las curvas originales además del resultado.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call combine_profiles --doc pieza.omnicad profiles=…`

### `offset_profiles`

Desfase (offset) del contorno de perfiles del boceto, con agujeros incluidos: distance > 0 agranda, < 0 achica. Sirve con cualquier curva (letras, splines de un SVG), no solo líneas y arcos encadenados. Esquinas redondas o vivas. Las curvas originales quedan (keep_original=true por defecto).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `profiles` (lista de entero o texto; obligatorio): índices de los perfiles (get_sketch) o "all".
  - `distance` (número; obligatorio): mm; positivo agranda la región, negativo la achica.
  - `corners` ("round" | "sharp"; opcional, por defecto `"round"`): round (arcos en las esquinas) o sharp (las esquinas se prolongan hasta cortarse).
  - `keep_original` (true/false; opcional, por defecto `true`): false para borrar las curvas de los perfiles usados.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call offset_profiles --doc pieza.omnicad profiles=… distance=…`

### `transform_sketch`

Mueve, gira, escala y/o espeja curvas de un boceto (un paso de deshacer): lo importado de un SVG, un texto, una selección. Orden: espejo, escala, giro y desplazamiento, todo alrededor del centro (por defecto el de la caja de la selección). Con copy=true trabaja sobre una copia. Las cotas de largo de lo escalado se multiplican por el factor.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entities` (lista de entero o null; opcional, por defecto `null`): ids de curvas o puntos (get_sketch); vacío = todas las curvas del boceto.
  - `dx` (número; opcional, por defecto `0.0`): desplazamiento en X (mm).
  - `dy` (número; opcional, por defecto `0.0`): desplazamiento en Y (mm).
  - `angle` (número; opcional, por defecto `0.0`): giro en grados (antihorario) alrededor del centro.
  - `scale` (número o expresión; opcional, por defecto `1.0`): factor de escala, número o expresión con parámetros ("ancho / 20"), entre 1e-6 y 1.000.000 (1 = igual); el resultado no puede pasar de 1 km del origen.
  - `mirror` ("none" | "horizontal" | "vertical"; opcional, por defecto `"none"`): horizontal (izquierda ↔ derecha), vertical (arriba ↔ abajo) o none.
  - `center_x` (número; opcional, por defecto `null`): x del centro de giro, escala y espejo; vacío = centro de la caja de la selección.
  - `center_y` (número; opcional, por defecto `null`): y del centro; vacío = centro de la caja de la selección.
  - `copy` (true/false; opcional, por defecto `false`): true para transformar una copia y dejar el original.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call transform_sketch --doc pieza.omnicad`

### `clean_sketch`

Limpia geometría importada (SVG, DXF, imagen vectorizada): borra curvas repetidas, une extremos sueltos a menos de tolerance mm (cierra huecos para que los contornos formen perfiles) y junta líneas seguidas alineadas en una sola. No toca nada que tenga restricciones o cotas.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `tolerance` (número; opcional, por defecto `0.01`): distancia máxima en mm para considerar dos puntos iguales o tres puntos alineados.
  - `remove_duplicates` (true/false; opcional, por defecto `true`): borrar curvas repetidas.
  - `close_gaps` (true/false; opcional, por defecto `true`): unir extremos sueltos cercanos.
  - `merge_collinear` (true/false; opcional, por defecto `true`): juntar líneas seguidas alineadas.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call clean_sketch --doc pieza.omnicad`

### `move_sketch_point`

Mueve un punto del boceto (edición de nodos): extremos de líneas y arcos, puntos de control de splines (las curvas Bézier de un SVG), centros. Como arrastrar en la interfaz: el punto va a (x, y) y el resto se acomoda para seguir cumpliendo restricciones y cotas; si ellas no lo dejan llegar (por ejemplo, una cota fija su distancia), queda lo más cerca posible: reached indica si quedó a menos de 0,001 mm del destino pedido y point dónde quedó.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `point` (entero; obligatorio): id del punto (get_sketch lista los puntos de cada curva en 'points').
  - `x` (número; obligatorio): x nueva (mm).
  - `y` (número; obligatorio): y nueva (mm).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call move_sketch_point --doc pieza.omnicad point=… x=… y=…`

### `delete_sketch_entities`

Borra curvas, puntos, restricciones o cotas del boceto (un paso de deshacer); lo que dependa de ellos se borra también (un punto se lleva sus curvas).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entities` (lista de entero; obligatorio): ids a borrar (get_sketch).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call delete_sketch_entities --doc pieza.omnicad entities=…`

## Grupo solido

Sólidos: extruir, revolucionar, primitivas, empalmes, agujeros y patrones.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`extrude`](#extrude) | sí | Extruye perfiles de un boceto. profile: índice, lista de índices, 'all', 'largest' (el perfil de mayor área, p. ej. la placa con sus agujeros) o 'text' (las letras de los textos, sin los huecos de la «o»; 'text:<id>' para uno solo). distance acepta un número (mm) o una expresión con parámetros. |
| [`revolve`](#revolve) | sí | Revoluciona perfiles de un boceto alrededor de un eje. axis: 'sketch_x' o 'sketch_y' (ejes del plano del boceto que pasan por su origen), 'x', 'y', 'z' (ejes del origen del diseño) o el id de una línea del boceto (get_sketch; puede ser de construcción); también un eje de construcción (id o nombre), una arista recta o una cara cilíndrica (selector o id de find_edges / find_faces) o una línea de OTRO boceto ({"sketch": id, "curve": n}). |
| [`sweep`](#sweep) | sí | Barre un perfil a lo largo de una ruta de otro boceto (o del mismo). |
| [`loft`](#loft) | sí | Solevación: un sólido que pasa por los perfiles de varios bocetos, en el orden dado (mínimo dos). profiles elige un perfil por boceto (índice o 'largest'); vacío = el perfil 0 de cada uno. ruled usa tramos rectos entre secciones y closed une la última con la primera. |
| [`create_box`](#create_box) | sí | Crea una caja alineada con los ejes. length es el tamaño en X, width en Y y height en Z (mm). (x, y, z) es el centro de la cara de abajo con anchor=center (por defecto), o la esquina mínima con anchor=corner. |
| [`create_cylinder`](#create_cylinder) | sí | Crea un cilindro con el eje en Z (con plane, sobre la normal de un plano o una cara cualquiera). (x, y, z) es el centro de la base; la altura crece hacia +Z. La medida va como radius o como diameter (uno solo). |
| [`create_sphere`](#create_sphere) | sí | Crea una esfera. (x, y, z) es su centro. |
| [`create_torus`](#create_torus) | sí | Crea un toroide con el eje en Z (con plane, sobre la normal de un plano o una cara cualquiera). (x, y, z) es su centro. |
| [`boolean_operation`](#boolean_operation) | sí | Combina cuerpos: join (unir), cut (restar las herramientas al objetivo) o intersect (quedarse con lo común). |
| [`mirror`](#mirror) | sí | Refleja cuerpos respecto de un plano (origen, de construcción o una CARA PLANA de un cuerpo: selector o id de find_faces). |
| [`realize_copies`](#realize_copies) | sí | Vuelve copias de verdad las copias ligeras (instancias) de un patrón o de Mover/copiar («Realizar instancias» de Plasticity): cada copia pasa a tener su propia geometría y deja de seguir a la original. |
| [`rectangular_pattern`](#rectangular_pattern) | sí | Patrón rectangular de cuerpos (bodies) o de operaciones del timeline (features: un agujero, una extrusión que corta… se repiten sobre la pieza, como el patrón de features de Fusion): copias en una o dos direcciones (ejes del origen), con la separación entre copias consecutivas. |
| [`circular_pattern`](#circular_pattern) | sí | Patrón circular de cuerpos (bodies) o de operaciones del timeline (features) alrededor de un eje del origen (x, y o z). |
| [`point_pattern`](#point_pattern) | sí | Patrón en puntos (Point Pattern de FreeCAD; en Fusion, los agujeros en varios puntos de boceto): copia cuerpos (bodies) —o repite operaciones del timeline (features), p. ej. un agujero o una extrusión que corta— en cada punto. |
| [`path_pattern`](#path_pattern) | sí | Patrón en ruta (Pattern on Path de Fusion; con twist, el Twisted Path Array de FreeCAD): copias de cuerpos (bodies) —o de operaciones del timeline (features)— a lo largo de curvas de un boceto. count incluye el original. distance es el largo TOTAL de la primera a la última (spacing_mode="extent") o la separación entre copias ("spacing"). start ubica el original sobre la ruta (0 a 1). orientation="path_direction" gira cada copia con la ruta; twist además la gira alrededor de la ruta, de a poco, hasta ese ángulo total en la última. |
| [`multi_transform`](#multi_transform) | sí | Multitransformación (MultiTransform de FreeCAD): patrón + simetría + patrón… en UN paso. transforms es una lista ordenada y cada transformación se aplica a TODAS las instancias de las anteriores (rectangular de 3 + mirror = 6). |
| [`drop_to_plane`](#drop_to_plane) | sí | Apoya cuerpos en el plano del piso (Z = 0): los baja o sube en Z hasta que lo más bajo toque Z = 0. |
| [`move_body`](#move_body) | sí | Mueve (o copia) cuerpos, como Mover › Movimiento libre de Fusion: primero gira rotate = [rx, ry, rz] grados alrededor del pivote (en ese orden) y después DESPLAZA translate = [dx, dy, dz] mm, que se SUMA a la posición actual (no es una posición absoluta: un cuerpo con el centro en z = 2 y translate [0, 0, 15] queda en z = 17). |
| [`insert_fastener`](#insert_fastener) | sí | Inserta fijaciones normalizadas sobre agujeros o puntos, con tamaño automático. |
| [`insert_canvas`](#insert_canvas) | sí | Embebe una imagen de referencia sobre un plano o cara plana (máximo 32 MB). |
| [`create_base_feature`](#create_base_feature) | sí | Congela cuerpos sólidos o superficies como B-rep en un paso del timeline. |
| [`fillet`](#fillet) | sí | Redondea aristas: empalme de radio constante (por defecto), de longitud de cuerda (radius_type=chord) o de radio variable entre el inicio y el final de la arista (radius_type=variable, end_radius). |
| [`chamfer`](#chamfer) | sí | Achaflana aristas: distancia igual en las dos caras (por defecto), dos distancias (type=two_distances, distance2) o distancia y ángulo (type=distance_angle, angle); flip pasa la primera distancia a la otra cara. |
| [`shell`](#shell) | sí | Vacía un cuerpo dejando paredes de un espesor dado; las caras elegidas se quitan (quedan abiertas). |
| [`remove_fillets`](#remove_fillets) | sí | Quita de una vez todos los redondeos (empalmes) de un cuerpo con radio hasta max_radius («Remove Fillets» de Plasticity: defeaturing + unión de la topología que queda). |
| [`offset_faces`](#offset_faces) | sí | Mueve caras de un cuerpo a lo largo de su normal (la mitad «cara» del comando Desfase; «Cara de desfase» de Fusion): distance > 0 agrega material, < 0 lo quita. |
| [`offset_edges`](#offset_edges) | sí | Desfase de aristas o de curvas de un boceto («Offset Edge» y «Offset Face Loop» de Plasticity): crea un boceto NUEVO con curvas a `distance` de las elegidas, sin tocar ni cortar el cuerpo. |
| [`create_hole`](#create_hole) | sí | Hace agujeros redondos hacia adentro del material: simples, abocardados (counterbore) o avellanados (countersink), ciegos (depth), pasantes (through_all) o hasta una cara, plano o cuerpo (to). |
| [`create_thread`](#create_thread) | sí | Rosca sobre caras cilíndricas (ejes o agujeros: se detecta solo), como el comando Rosca de Fusion. |
| [`draft`](#draft) | sí | Desmoldeo: inclina caras un ángulo respecto de un plano neutro (la cara o el plano que no se mueve), para poder sacar la pieza del molde. |
| [`create_clearance_test`](#create_clearance_test) | sí | Crea la pieza de calibración de holguras para impresión 3D (como la tira de tolerancias de Cura): una placa con count agujeros pasantes de Ø diameter + 2·holgura, con la holgura radial creciente desde start_clearance en saltos de step y su valor grabado junto a cada agujero, más un peine con los pernos de Ø diameter a la misma distancia. |
| [`split_face`](#split_face) | sí | Divide caras con un plano, cara, arista o curva de boceto. split_type: surface (proyecta la herramienta sobre la cara, por defecto), vector (la proyecta a lo largo de direction y parte una vez por cada cruce) o closest_point (cada punto de la herramienta va al más cercano de la cara). |
| [`split_body`](#split_body) | sí | Parte un cuerpo en varios con un plano, una cara u otro cuerpo. |
| [`silhouette_split`](#silhouette_split) | sí | Divide un cuerpo por su silueta vista desde una dirección. operation: faces_only (solo parte las caras; el cuerpo sigue siendo uno), shelled_body (parte en dos un cuerpo vaciado) o solid_body (parte en dos un sólido). |
| [`replace_face`](#replace_face) | sí | Lleva caras de un cuerpo hasta otra cara o un plano. |
| [`remove_bodies`](#remove_bodies) | sí | Quita cuerpos del diseño conservando la operación en el timeline. |
| [`delete_faces`](#delete_faces) | sí | Borra caras y cierra el hueco extendiendo sus vecinas. |
| [`gear_info`](#gear_info) | no | Calcula las medidas de un engranaje cilíndrico de evolvente sin modelarlo (ISO 21771, perfil de referencia ISO 53): diámetros primitivo, base, exterior y de fondo, paso, espesor del diente, dientes mínimos sin socavado (criterio estricto: 18 con 20°; el límite teórico, 17,1, va en min_teeth_theoretical) y desplazamiento mínimo. |
| [`create_gear`](#create_gear) | sí | Crea un engranaje cilíndrico de evolvente (perfil de referencia ISO 53), recto o, con helix_angle, helicoidal, como un paso del timeline (tipo «engranaje»; medidas como expresiones con parámetros). |
| [`create_gear_pair`](#create_gear_pair) | sí | Crea dos engranajes de evolvente que engranan, en UN paso del timeline: el segundo a la distancia entre centros de trabajo (m·(z1+z2)/2 sin desplazamientos), en la dirección dada y girado medio diente para que los dientes entren en los huecos (con hélice, el segundo es de la mano contraria). |
| [`create_rack`](#create_rack) | sí | Crea una cremallera recta con el perfil de referencia ISO 53 (paso π·módulo, flancos rectos al ángulo de presión) como un paso del timeline. |
| [`create_sprocket`](#create_sprocket) | sí | Crea una rueda dentada para cadena de rodillos con la forma de diente de ISO 606 (hueco medio) como un paso del timeline. chain elige la cadena (05B…16B, 08A…16A = ANSI 40…80) o 'custom' con pitch y roller_diameter propios; sin width, el ancho del diente sale de la norma (0,93 o 0,95 × ancho interior de la cadena). |
| [`create_shaft`](#create_shaft) | sí | Asistente de ejes: crea un eje escalonado de revolución a partir de una tabla de tramos (diámetro, largo y, en cada extremo, chaflán a 45° o empalme) como un paso del timeline (tipo «eje_escalonado»). |
| [`assign_plastic_rule`](#assign_plastic_rule) | sí | Asigna una regla de plástico a un componente (PLÁSTICO › Asignar regla de plástico): el material físico de la regla pasa a todos sus cuerpos y la regla queda guardada en el componente (list_plastic_rules dice cuáles). |
| [`rebuild_features`](#rebuild_features) | sí | Find Features que rehace: reconoce los agujeros (también abocardados), empalmes y chaflanes de un cuerpo sin historial y los vuelve pasos paramétricos del timeline, uno por uno: borra las caras de la función (delete_faces, las vecinas cierran el hueco) y la crea de nuevo con create_hole, fillet o chamfer y las medidas reconocidas; después vuelve a reconocer sobre el cuerpo nuevo. |
| [`create_coil`](#create_coil) | sí | Crea una bobina o espiral con las opciones del comando Bobina. |
| [`create_pipe`](#create_pipe) | sí | Crea una tubería maciza o hueca sobre curvas de boceto o aristas. |
| [`create_rib`](#create_rib) | sí | Crea un nervio paralelo al plano del boceto, hasta el cuerpo o a profundidad. direction: symmetric, o un solo lado empezando abajo (side1, Start: Bottom) o arriba (side2, Start: Top). draft_angle afina el nervio hacia su borde libre; pull_direction (plano, cara o eje) es la dirección de extracción del desmoldeo (por defecto, del cuerpo hacia la curva). |
| [`create_web`](#create_web) | sí | Crea una red de nervios perpendicular al plano del boceto. draft_angle afina la red hacia su borde libre, fillet_radius redondea las aristas cóncavas donde se junta con el cuerpo y extend_curves=false la deja terminar donde terminan las curvas. |
| [`create_emboss`](#create_emboss) | sí | Repuja o graba perfiles en una o varias caras, con envoltura opcional. |
| [`create_boss`](#create_boss) | sí | Crea columnas para tornillo en puntos de boceto o vértices. |
| [`create_lip_groove`](#create_lip_groove) | sí | Crea un labio o una ranura a lo largo del borde de una pared. |
| [`create_boundary_fill`](#create_boundary_fill) | sí | Rellena celdas encerradas por cuerpos, caras y planos. |
| [`create_volumetric_lattice`](#create_volumetric_lattice) | sí | Llena un sólido o una malla cerrada con una estructura interna por celdas (SÓLIDO › MODIFICAR › Retícula volumétrica). cell_shape: cross (tres barras por celda), x_cell (las cuatro diagonales), x_cell_25d (las diagonales en XY como paredes extruidas en Z) y custom (barras a medida, custom_bars) quedan como sólido; gyroid, schwarz_p y schwarz_d (superficies mínimas) quedan como cuerpo de malla (resolution muestras por celda; el borde del cuerpo sale interpolado). solidity es el porcentaje de material; con solidity_end y gradient_path varía a lo largo de la ruta. offset_distance/offset_blend arman la zona de desfase (otra solidez cerca de caras, aristas o puntos). cell_offset y cell_rotation mueven y giran las celdas. |
| [`create_geometric_pattern`](#create_geometric_pattern) | sí | Reparte esferas, cilindros, cajas u objetos a medida sobre caras planas con un gradiente de tamaño (PLÁSTICO › CREAR › Patrón geométrico). |
| [`create_bounding_solid`](#create_bounding_solid) | sí | Crea una caja, un cilindro o un tubo envolvente de los cuerpos elegidos (SÓLIDO › CREAR › Sólido envolvente). orientation: model (ejes del modelo), automatic (la menor), z_x / z_y / x_y (dos ejes dados en axis_a y axis_b; el primero manda) o ucs (un sistema de coordenadas de usuario). |
| [`create_fluid_volume`](#create_fluid_volume) | sí | Crea el volumen de fluido de un diseño (SÓLIDO › CREAR › Volumen de fluido): el sólido del interior (internal, que copia las caras del modelo) o del exterior (external, una caja, cilindro o semiesfera que rodea el modelo menos el modelo). |
| [`thicken`](#thicken) | sí | Da espesor a caras o cuerpos de superficie y crea un sólido. |
| [`align_bodies`](#align_bodies) | sí | Alinea puntos, planos enfrentados o ejes de los cuerpos, con copia opcional. |
| [`move_faces`](#move_faces) | sí | Mueve o copia caras planas de un cuerpo (SÓLIDO › MODIFICAR › Mover/copiar › Caras): las caras vecinas se extienden o se recortan para seguirlas. type=translate con direction (eje, arista recta, cara plana o plano) y distance, o con translate [dx, dy, dz]; type=rotate alrededor de axis un angle. |
| [`scale_body`](#scale_body) | sí | Escala sólidos o componentes (con todos sus cuerpos) respecto de un punto, uniforme o con un factor por eje. sketches escala bocetos enteros (solo uniforme). |
| [`create_surface_extrude`](#create_surface_extrude) | sí | Extruye curvas abiertas o cerradas en una superficie. |
| [`create_surface_revolve`](#create_surface_revolve) | sí | Gira curvas alrededor de un eje para crear una superficie. |
| [`create_surface_sweep`](#create_surface_sweep) | sí | Barre curvas por una ruta con orientación, torsión y distancia sobre la ruta. |
| [`create_surface_loft`](#create_surface_loft) | sí | Crea una superficie entre secciones ordenadas, abiertas o cerradas. |
| [`offset_surface`](#offset_surface) | sí | Crea una superficie paralela a caras o cuerpos. |
| [`fillet_surface`](#fillet_surface) | sí | Redondea o bisela aristas entre superficies. |
| [`create_patch`](#create_patch) | sí | Tapa un contorno cerrado con continuidad G0, G1 o G2. |
| [`create_ruled_surface`](#create_ruled_surface) | sí | Crea superficies rectas desde aristas, con dirección y ángulo. |
| [`extend_surface`](#extend_surface) | sí | Alarga bordes libres de superficies. |
| [`trim_surface`](#trim_surface) | sí | Recorta una superficie y quita la región indicada por un punto. |
| [`untrim_surface`](#untrim_surface) | sí | Restaura límites naturales de caras recortadas. |
| [`stitch_surfaces`](#stitch_surfaces) | sí | Cose superficies; un cierre completo produce un sólido. |
| [`unstitch_surfaces`](#unstitch_surfaces) | sí | Separa cada cara en un cuerpo de superficie independiente. |
| [`reverse_surface_normal`](#reverse_surface_normal) | sí | Invierte la orientación de cuerpos de superficie. |

### `extrude`

Extruye perfiles de un boceto. profile: índice, lista de índices, 'all', 'largest' (el perfil de mayor área, p. ej. la placa con sus agujeros) o 'text' (las letras de los textos, sin los huecos de la «o»; 'text:<id>' para uno solo). distance acepta un número (mm) o una expresión con parámetros. El sentido positivo es la normal del plano del boceto (en XZ es −Y); reverse lo invierte. Como en Fusion, un cut entra al material sin pedirlo con reverse vacío (sobre una cara va contra la normal exterior; en un boceto flotante va hacia el lado que tiene material). direction: one_side, two_sides (distance y distance2) o symmetric (distance es el largo TOTAL, mitad a cada lado). taper_angle inclina las paredes (grados; positivo ensancha el sólido hacia el final, negativo lo estrecha). operation: new_body, join, cut o intersect. Opciones de Extruir de Fusion: faces (caras planas como perfil, con o sin sketch), thin (extrusión delgada: wall_thickness, wall_location; con open_curves se extruyen curvas abiertas), start (profile_plane, offset u object: el inicio no es el plano del perfil), symmetric_measure (media longitud o largo total), extent (distance, to_object: hasta una cara, plano o cuerpo con to, to_mode y to_offset, o all: atraviesa todo) y taper_angle2 (conicidad propia del lado 2).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto de los perfiles; vacío si el perfil son solo caras (faces).
  - `profile` (entero o lista de entero o texto; opcional, por defecto `0`): perfil(es): índice (get_sketch los lista), lista de índices, "all", "largest", "text" (las letras de los textos, sin sus huecos) o "text:<id>". Se ignora con open_curves.
  - `distance` (número o expresión; opcional, por defecto `"10 mm"`): distancia de extrusión: número en mm o expresión, p. ej. "espesor" o "2 * radio".
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `direction` ("one_side" | "two_sides" | "symmetric"; opcional, por defecto `"one_side"`): "one_side", "two_sides" o "symmetric".
  - `taper_angle` (número o expresión; opcional, por defecto `0`): conicidad en grados (número o expresión): positivo ensancha hacia el final, negativo estrecha; 0 = recto.
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
  - `distance2` (número o expresión; opcional, por defecto `null`): distancia del segundo lado con direction="two_sides"; vacío = igual a distance.
  - `reverse` (true/false; opcional, por defecto `null`): true para extruir hacia el lado contrario de la normal del plano. Vacío = automático: un cut entra al material (sobre una cara, o con faces como único perfil, va contra la normal exterior; en un boceto flotante va hacia el lado que tiene material, como Fusion).
  - `faces` (texto o lista de texto o null; opcional, por defecto `null`): caras planas (selector o id de find_faces, o lista) usadas como perfil, solas o junto con los perfiles de sketch; tienen que ser coplanares. Extruir solo una cara de un cuerpo: operation="join" la empuja hacia afuera (agrega material); operation="cut" la empuja hacia adentro (corta; ver reverse).
  - `thin` (true/false; opcional, por defecto `false`): true hace una extrusión delgada (pared de wall_thickness) en lugar de sólida.
  - `wall_thickness` (número o expresión; opcional, por defecto `1`): espesor de la pared en mm (número o expresión); solo con thin.
  - `wall_location` ("side1" | "side2" | "center"; opcional, por defecto `"side1"`): lado del contorno donde va la pared: "side1", "side2" o "center"; solo con thin.
  - `start` ("profile_plane" | "offset" | "object"; opcional, por defecto `"profile_plane"`): dónde empieza la extrusión: "profile_plane" (el plano del perfil), "offset" (a start_offset de él) o "object" (en la cara plana o plano start_object).
  - `start_offset` (número o expresión; opcional, por defecto `0`): desfase del inicio en mm (número o expresión); con start=offset.
  - `start_object` (texto; opcional, por defecto `null`): cara plana (selector o id) o plano de construcción donde empieza; con start=object.
  - `symmetric_measure` ("total" | "half"; opcional, por defecto `"total"`): con direction=symmetric, "total" (distance es el largo total) o "half" (distance es la mitad, a cada lado).
  - `extent` ("distance" | "to_object" | "all"; opcional, por defecto `"distance"`): hasta dónde llega: "distance" (distance, por defecto), "to_object" (hasta to) o "all" (atraviesa todos los cuerpos).
  - `to` (texto; opcional, por defecto `null`): con extent=to_object: cara (selector o id), plano o cuerpo hasta donde llega.
  - `to_mode` ("face" | "body" | "through"; opcional, por defecto `"face"`): con to_object: "face" (hasta la cara), "body" (hasta el cuerpo) o "through" (a través del cuerpo).
  - `to_offset` (número o expresión; opcional, por defecto `0`): desfase en mm sobre el «hasta» (positivo = más lejos); con extent=to_object.
  - `taper_angle2` (número o expresión; opcional, por defecto `null`): conicidad del lado 2 en grados con direction=two_sides; vacío = la misma que taper_angle.
  - `open_curves` (lista de entero o null; opcional, por defecto `null`): ids de curvas ABIERTAS de sketch (get_sketch) para extruir con thin=true; reemplazan a profile.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de faces, start_object y to; vacío = el único cuerpo.
- CLI: `omnicad call extrude --doc pieza.omnicad`

### `revolve`

Revoluciona perfiles de un boceto alrededor de un eje. axis: 'sketch_x' o 'sketch_y' (ejes del plano del boceto que pasan por su origen), 'x', 'y', 'z' (ejes del origen del diseño) o el id de una línea del boceto (get_sketch; puede ser de construcción); también un eje de construcción (id o nombre), una arista recta o una cara cilíndrica (selector o id de find_edges / find_faces) o una línea de OTRO boceto ({"sketch": id, "curve": n}). El perfil no debe cruzar el eje; puede ser una cara plana (faces). angle acepta número (grados) o expresión. direction: one_side, two_sides (angle y angle2) o symmetric. to_object (Extent Type › To Object) gira el perfil hasta un vértice, un plano, una cara plana o un cuerpo en lugar de un ángulo (solo con one_side). project_axis lleva el eje al plano del perfil (Project Axis).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto de los perfiles; vacío si el perfil son solo caras (faces).
  - `profile` (entero o lista de entero o texto; opcional, por defecto `0`): perfil(es): índice, lista de índices, "all", "largest", "text" o "text:<id>".
  - `axis` (entero o texto o objeto; opcional, por defecto `null`): "sketch_x", "sketch_y", "x", "y", "z", el id de una línea del boceto, un eje de construcción (id o nombre), una arista recta o una cara cilíndrica (selector o id) o {"sketch": id, "curve": n} (línea de otro boceto).
  - `angle` (número o expresión; opcional, por defecto `"360 deg"`): ángulo de giro: número en grados o expresión, p. ej. "270 deg" o "giro".
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `direction` ("one_side" | "two_sides" | "symmetric"; opcional, por defecto `"one_side"`): "one_side", "two_sides" o "symmetric" (el ángulo se reparte a los dos lados).
  - `angle2` (número o expresión; opcional, por defecto `null`): ángulo del segundo lado con direction="two_sides"; vacío = igual a angle.
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
  - `reverse` (true/false; opcional, por defecto `false`): true para girar en el sentido contrario.
  - `faces` (texto o lista de texto o null; opcional, por defecto `null`): caras planas (selector o id de find_faces, o lista) usadas como perfil, solas o junto con los perfiles de sketch.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de faces y de axis (arista o cara); vacío = el único cuerpo.
  - `to_object` (texto o objeto o lista de número o null; opcional, por defecto `null`): vértice ([x, y, z] o selector), plano (XY/XZ/YZ o de construcción), cara plana (selector o id) o cuerpo (id o nombre) hasta donde gira el perfil; reemplaza a angle.
  - `project_axis` (true/false; opcional, por defecto `false`): true proyecta el eje al plano del perfil; false lo deja donde está.
- CLI: `omnicad call revolve --doc pieza.omnicad`

### `sweep`

Barre un perfil a lo largo de una ruta de otro boceto (o del mismo). La ruta es una cadena continua de curvas: path_curves da sus ids (get_sketch) o, vacío, se usan todas las curvas no de construcción del boceto de la ruta. El perfil tiene que estar en el plano perpendicular al inicio de la ruta. Opciones: faces (una cara plana como perfil), path_edges (aristas de un cuerpo como ruta, en lugar de path_sketch), rail_sketch y rail_curves (ruta + carril guía; rail_scale elige cómo sigue el perfil al carril: scale, stretch o none) y path_distance (fracción de la ruta que se barre, de 0 a 1). orientation=aligned mantiene el perfil con el eje align_axis como binormal (eje, arista recta, plano o cara plana). guide_surface (caras sobre las que va la ruta) es el tipo Ruta + Superficie guía: el perfil sigue la normal de la superficie. sweep_bodies barre un cuerpo sólido (Solid Sweep) en lugar de un perfil: lo que recorre el cuerpo al moverse a lo largo de la ruta (aproximado con copias del cuerpo: el borde de un barrido curvo queda escalonado). chain=true suma a cada arista de path_edges las que le siguen tangentes (Chain Selection).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto con el perfil; vacío si el perfil es una cara (faces).
  - `profile` (entero o lista de entero o texto; opcional, por defecto `0`): perfil(es): índice, lista de índices, "all", "largest", "text" o "text:<id>".
  - `path_sketch` (texto; opcional, por defecto `null`): id o nombre del boceto con la ruta; vacío si la ruta son aristas de un cuerpo (path_edges).
  - `path_curves` (lista de entero o null; opcional, por defecto `null`): ids de las curvas de la ruta; vacío = todas las curvas no de construcción de path_sketch.
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `orientation` ("perpendicular" | "parallel" | "aligned"; opcional, por defecto `"perpendicular"`): "perpendicular" (sigue la tangente), "parallel" (mantiene su orientación) o "aligned" (align_axis como binormal).
  - `taper_angle` (número o expresión; opcional, por defecto `0`): ángulo de conicidad en grados.
  - `twist_angle` (número o expresión; opcional, por defecto `0`): torsión total en grados (máximo ±3600; ±1800 en rutas cerradas; la ruta no puede tener esquinas).
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
  - `faces` (texto o lista de texto o null; opcional, por defecto `null`): cara plana (selector o id de find_faces) usada como perfil, sola o junto con los perfiles de sketch.
  - `path_edges` (texto o lista de texto o null; opcional, por defecto `null`): aristas de un cuerpo (selector "edges:…" o ids de find_edges, o lista) como ruta continua, en lugar de path_sketch.
  - `rail_sketch` (texto; opcional, por defecto `null`): id o nombre del boceto del carril guía (tipo «ruta + carril»); vacío = sin carril.
  - `rail_curves` (lista de entero o null; opcional, por defecto `null`): ids de las curvas del carril; vacío = todas las no de construcción.
  - `rail_scale` ("scale" | "stretch" | "none"; opcional, por defecto `"scale"`): cómo sigue el perfil al carril: "scale", "stretch" o "none".
  - `path_distance` (número o expresión; opcional, por defecto `1`): fracción de la ruta que se barre (>0 hasta 1); 1 = toda.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de faces y path_edges; vacío = el único cuerpo.
  - `align_axis` (texto o objeto; opcional, por defecto `null`): con orientation=aligned, el eje: eje de construcción, arista recta, plano o cara plana (id o selector).
  - `guide_surface` (texto o lista de texto o null; opcional, por defecto `null`): caras (selector o ids) sobre las que va la ruta; el perfil sigue su normal; sin carril ni torsión.
  - `sweep_bodies` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) (id o nombre) que se barren por la ruta (Solid Sweep) en vez de un perfil; sin carril, superficie guía, torsión ni conicidad.
  - `chain` (true/false; opcional, por defecto `false`): true suma a path_edges las aristas tangentes que le siguen (Chain Selection); las curvas de boceto se usan tal cual y se avisa.
- CLI: `omnicad call sweep --doc pieza.omnicad`

### `loft`

Solevación: un sólido que pasa por los perfiles de varios bocetos, en el orden dado (mínimo dos). profiles elige un perfil por boceto (índice o 'largest'); vacío = el perfil 0 de cada uno. ruled usa tramos rectos entre secciones y closed une la última con la primera. Opciones: sections (en lugar de sketches: cada sección es un perfil {"sketch", "profile"}, una cara o arista (selector o id), un vértice [x, y, z] o un punto de construcción: sirve para terminar en punta), rails (curvas guía: {"sketch", "curve"} o aristas) o center_line (una línea central), sin combinar las dos. start_condition y end_condition fijan cómo sale la superficie de la primera y la última sección: {"type": "free"} o {"type": "direction", "angle": grados desde el plano de la sección (90 = perpendicular), "weight": 1} o {"type": "tangent" | "smooth", "face": cara, "weight": 1} (tangente a esa cara, que tiene la sección en su borde); aproximado con una sección auxiliar, solo en la solevación lisa (sin rails, center_line, ruled ni closed). section_conditions pone una condición direction en secciones intermedias. merge_tangent_edges une las caras tangentes. smooth (G2) es como tangent y sigue también la curvatura de la cara.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketches` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los bocetos, en el orden de las secciones; vacío si se da sections.
  - `profiles` (lista de entero o texto o null; opcional, por defecto `null`): un perfil por boceto (índice o "largest"); vacío = el perfil 0 de cada boceto.
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `ruled` (true/false; opcional, por defecto `false`): true para tramos rectos entre secciones.
  - `closed` (true/false; opcional, por defecto `false`): true para cerrar el sólido uniendo la última sección con la primera.
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
  - `sections` (lista de texto o objeto o lista de número o null; opcional, por defecto `null`): secciones en orden, en lugar de sketches: {"sketch": id, "profile": índice} (profile 0 por defecto), una cara o arista (selector o id de find_faces / find_edges), un vértice [x, y, z] o un punto de construcción (id o nombre). Mínimo dos.
  - `rails` (lista de texto o objeto o null; opcional, por defecto `null`): curvas guía {"sketch": id, "curve": n} o aristas (selector o id), una lista por carril.
  - `center_line` (lista de texto o objeto o null; opcional, por defecto `null`): la línea central de la solevación: {"sketch": id, "curve": n} o aristas; no se combina con rails.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de sections, rails y center_line; vacío = el único cuerpo.
  - `start_condition` (objeto; opcional, por defecto `null`): condición de borde de la primera sección: {"type": "free" | "direction" | "tangent" | "smooth", "angle": grados (90 por defecto), "weight": número (1 por defecto), "face": cara (selector o id; solo con tangent)}.
  - `end_condition` (objeto; opcional, por defecto `null`): lo mismo para la última sección.
  - `merge_tangent_edges` (true/false; opcional, por defecto `false`): true une las caras que quedan tangentes entre sí (Tangent Edges › Merge).
  - `section_conditions` (objeto; opcional, por defecto `null`): condiciones direction en secciones intermedias: {"2": {"type": "direction", "angle": 60}} (el número es la posición de la sección, 1 = la primera; no vale tangent).
- CLI: `omnicad call loft --doc pieza.omnicad`

### `create_box`

Crea una caja alineada con los ejes. length es el tamaño en X, width en Y y height en Z (mm). (x, y, z) es el centro de la cara de abajo con anchor=center (por defecto), o la esquina mínima con anchor=corner. Medidas y posición aceptan expresiones con parámetros. En el timeline el paso guarda x, y, z con el mismo significado (caja_centrada) y edit_feature acepta length, width y height. Con plane la crea sobre un plano o una cara plana cualquiera, también inclinada.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `length` (número o expresión; obligatorio): tamaño en X (mm, positivo).
  - `width` (número o expresión; obligatorio): tamaño en Y (mm, positivo).
  - `height` (número o expresión; obligatorio): tamaño en Z (mm, positivo).
  - `x` (número o expresión; opcional, por defecto `0`): x del centro de la base o de la esquina mínima, según anchor (mm).
  - `y` (número o expresión; opcional, por defecto `0`): y del centro de la base o de la esquina mínima, según anchor (mm).
  - `z` (número o expresión; opcional, por defecto `0`): z de la base (mm).
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo afectado por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
  - `name` (texto; opcional, por defecto `null`): nombre del cuerpo creado (vacío = el automático «CuerpoN»); solo con operation "new_body".
  - `anchor` ("center" | "corner"; opcional, por defecto `"center"`): "center" sitúa (x, y, z) en el centro de la base; "corner", en la esquina mínima (crece hacia +X, +Y, +Z).
  - `plane` (texto o objeto; opcional, por defecto `null`): plano (XY/XZ/YZ o de construcción) o cara plana (selector o id) sobre el que se crea; vacío = el mundo. Con plane, x e y son coordenadas en el plano, z la distancia sobre su normal y la altura crece por la normal.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúa el selector de plane; vacío = el único cuerpo.
- CLI: `omnicad call create_box --doc pieza.omnicad length=… width=… height=…`

### `create_cylinder`

Crea un cilindro con el eje en Z (con plane, sobre la normal de un plano o una cara cualquiera). (x, y, z) es el centro de la base; la altura crece hacia +Z. La medida va como radius o como diameter (uno solo).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `height` (número o expresión; obligatorio): altura en mm (positiva).
  - `radius` (número o expresión; opcional, por defecto `null`): radio en mm (positivo). Alternativa: diameter.
  - `x` (número o expresión; opcional, por defecto `0`): x del centro de la base (mm).
  - `y` (número o expresión; opcional, por defecto `0`): y del centro de la base (mm).
  - `z` (número o expresión; opcional, por defecto `0`): z de la base (mm).
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo afectado por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
  - `diameter` (número o expresión; opcional, por defecto `null`): diámetro en mm, en vez de radius (como el panel Cilindro de la app); el paso guarda la mitad.
  - `name` (texto; opcional, por defecto `null`): nombre del cuerpo creado (vacío = el automático «CuerpoN»); solo con operation "new_body".
  - `plane` (texto o objeto; opcional, por defecto `null`): plano (XY/XZ/YZ o de construcción) o cara plana (selector o id) sobre el que se crea; vacío = el mundo. Con plane, x e y son coordenadas en el plano, z la distancia sobre su normal y el eje va por la normal.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúa el selector de plane; vacío = el único cuerpo.
- CLI: `omnicad call create_cylinder --doc pieza.omnicad height=…`

### `create_sphere`

Crea una esfera. (x, y, z) es su centro. La medida va como radius o como diameter (uno solo).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `radius` (número o expresión; opcional, por defecto `null`): radio en mm (positivo). Alternativa: diameter.
  - `x` (número o expresión; opcional, por defecto `0`): x del centro (mm).
  - `y` (número o expresión; opcional, por defecto `0`): y del centro (mm).
  - `z` (número o expresión; opcional, por defecto `0`): z del centro (mm).
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo afectado por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
  - `diameter` (número o expresión; opcional, por defecto `null`): diámetro en mm, en vez de radius (como el panel Esfera de la app); el paso guarda la mitad.
  - `name` (texto; opcional, por defecto `null`): nombre del cuerpo creado (vacío = el automático «CuerpoN»); solo con operation "new_body".
  - `plane` (texto o objeto; opcional, por defecto `null`): plano (XY/XZ/YZ o de construcción) o cara plana (selector o id) sobre el que se crea; vacío = el mundo. Con plane, x e y son coordenadas en el plano, z la distancia sobre su normal y el centro queda a esa altura.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúa el selector de plane; vacío = el único cuerpo.
- CLI: `omnicad call create_sphere --doc pieza.omnicad`

### `create_torus`

Crea un toroide con el eje en Z (con plane, sobre la normal de un plano o una cara cualquiera). (x, y, z) es su centro. Medidas como radios (major_radius, minor_radius) o diámetros (major_diameter, minor_diameter), uno de cada par.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `major_radius` (número o expresión; opcional, por defecto `null`): radio mayor en mm (del centro al centro del tubo); tiene que ser mayor que minor_radius.
  - `minor_radius` (número o expresión; opcional, por defecto `null`): radio menor en mm (del tubo).
  - `x` (número o expresión; opcional, por defecto `0`): x del centro (mm).
  - `y` (número o expresión; opcional, por defecto `0`): y del centro (mm).
  - `z` (número o expresión; opcional, por defecto `0`): z del centro (mm).
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo afectado por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
  - `major_diameter` (número o expresión; opcional, por defecto `null`): diámetro del círculo que recorre el centro del tubo, en vez de major_radius (panel Toroide).
  - `minor_diameter` (número o expresión; opcional, por defecto `null`): diámetro del tubo, en vez de minor_radius.
  - `name` (texto; opcional, por defecto `null`): nombre del cuerpo creado (vacío = el automático «CuerpoN»); solo con operation "new_body".
  - `plane` (texto o objeto; opcional, por defecto `null`): plano (XY/XZ/YZ o de construcción) o cara plana (selector o id) sobre el que se crea; vacío = el mundo. Con plane, x e y son coordenadas en el plano, z la distancia sobre su normal y el eje va por la normal.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúa el selector de plane; vacío = el único cuerpo.
- CLI: `omnicad call create_torus --doc pieza.omnicad`

### `boolean_operation`

Combina cuerpos: join (unir), cut (restar las herramientas al objetivo) o intersect (quedarse con lo común). El resultado queda en el cuerpo objetivo; las herramientas se consumen salvo keep_tools.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `target` (texto; obligatorio): cuerpo objetivo (id o nombre).
  - `tools` (lista de texto; obligatorio): cuerpos herramienta (ids o nombres).
  - `operation` ("join" | "cut" | "intersect"; opcional, por defecto `"join"`): "join", "cut" o "intersect".
  - `keep_tools` (true/false; opcional, por defecto `false`): true para conservar los cuerpos herramienta.
- CLI: `omnicad call boolean_operation --doc pieza.omnicad target=… tools=…`

### `mirror`

Refleja cuerpos respecto de un plano (origen, de construcción o una CARA PLANA de un cuerpo: selector o id de find_faces). Crea cuerpos nuevos, o con combine=true une cada reflejo a su cuerpo original. En vez de cuerpos puede reflejar caras (faces: cada reflejo queda como una superficie nueva), componentes (components: copias reflejadas) u operaciones del timeline (features: su herramienta se refleja y se aplica con la misma operación).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) a reflejar (id o nombre).
  - `plane` (texto; opcional, por defecto `"YZ"`): plano de simetría: "XY", "XZ", "YZ", el id/nombre de un plano de construcción, o una cara plana (selector ">X" o id de find_faces).
  - `combine` (true/false; opcional, por defecto `false`): true para unir el reflejo al cuerpo original en vez de crear un cuerpo nuevo (solo con bodies).
  - `plane_body` (texto; opcional, por defecto `null`): cuerpo donde se evalúa el selector de cara de plane; vacío = el único cuerpo.
  - `features` (texto o lista de texto o null; opcional, por defecto `null`): pasos anteriores del timeline (id o nombre) cuyo efecto se refleja en vez de cuerpos. No se combina con bodies.
  - `faces` (texto o lista de texto o null; opcional, por defecto `null`): caras a reflejar (selector, ids de find_faces o lista): cada reflejo queda como un cuerpo de superficie nuevo. No se combina con bodies, features ni components.
  - `components` (lista de texto o null; opcional, por defecto `null`): componentes a reflejar (id o nombre): cada reflejo es un componente nuevo con copias reflejadas de sus cuerpos. No se combina con bodies, features ni faces.
  - `construction` (lista de texto o null; opcional, por defecto `null`): planos, ejes o puntos de construcción a repetir (id o nombre): cada copia es una entidad nueva. No se combina con bodies, features, faces ni components.
  - `compute` ("identical" | "optimized" | "adjust"; opcional, por defecto `"identical"`): cálculo de las copias de features (Compute Type): optimized e identical repiten la herramienta del paso tal cual (mismo resultado); adjust omite las copias cuya herramienta no toca al cuerpo.
- CLI: `omnicad call mirror --doc pieza.omnicad`

### `realize_copies`

Vuelve copias de verdad las copias ligeras (instancias) de un patrón o de Mover/copiar («Realizar instancias» de Plasticity): cada copia pasa a tener su propia geometría y deja de seguir a la original. Las posiciones y los volúmenes no cambian. Falla con INVALID_ARGUMENTS si el paso no tiene copias ligeras (lightweight=true en el patrón o en move_body).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `feature` (texto; obligatorio): id (p. ej. "op3") o nombre del paso (patrón, multitransformación o mover) con copias ligeras.
- CLI: `omnicad call realize_copies --doc pieza.omnicad feature=…`

### `rectangular_pattern`

Patrón rectangular de cuerpos (bodies) o de operaciones del timeline (features: un agujero, una extrusión que corta… se repiten sobre la pieza, como el patrón de features de Fusion): copias en una o dos direcciones (ejes del origen), con la separación entre copias consecutivas. Con bodies las copias son cuerpos nuevos (o se unen al original con combine). Cantidades incluyen el original.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) a repetir (id o nombre).
  - `x_count` (entero; opcional, por defecto `1`): cantidad de instancias en la dirección 1, original incluido (1 = sin copias; x_count × y_count ≤ 10.000).
  - `x_spacing` (número o expresión; opcional, por defecto `"10 mm"`): separación entre instancias consecutivas en la dirección 1 (mm o expresión). Se guarda como d1 con distribucion="espaciado": edit_feature d1 sigue siendo la separación.
  - `y_count` (entero; opcional, por defecto `1`): cantidad de instancias en la dirección 2, original incluido (x_count × y_count ≤ 10.000).
  - `y_spacing` (número o expresión; opcional, por defecto `"10 mm"`): separación entre instancias consecutivas en la dirección 2 (se guarda como d2).
  - `axis1` (texto; opcional, por defecto `"x"`): dirección 1: "x", "y", "z", o un eje de construcción (id o nombre), una arista recta, una cara plana (su normal) o un plano (selector o id).
  - `axis2` (texto; opcional, por defecto `"y"`): dirección 2 (mismas formas que axis1).
  - `combine` (true/false; opcional, por defecto `false`): true para unir las copias al cuerpo original (solo con bodies).
  - `features` (texto o lista de texto o null; opcional, por defecto `null`): pasos anteriores del timeline (id o nombre) cuyo efecto se repite en vez de cuerpos: su herramienta (el agujero, la extrusión que corta o une…) se copia y se aplica con la misma operación a los mismos cuerpos, como el patrón de features de Fusion. No se combina con bodies.
  - `faces` (texto o lista de texto o null; opcional, por defecto `null`): caras a repetir (selector, ids de find_faces o lista): cada copia queda como un cuerpo de superficie nuevo. No se combina con bodies, features ni components.
  - `components` (lista de texto o null; opcional, por defecto `null`): componentes a repetir (id o nombre): cada copia es un componente nuevo con copias de sus cuerpos. No se combina con bodies, features ni faces.
  - `construction` (lista de texto o null; opcional, por defecto `null`): planos, ejes o puntos de construcción a repetir (id o nombre): cada copia es una entidad nueva. No se combina con bodies, features, faces ni components.
  - `compute` ("identical" | "optimized" | "adjust"; opcional, por defecto `"identical"`): cálculo de las copias de features (Compute Type): optimized e identical repiten la herramienta del paso tal cual (mismo resultado); adjust omite las copias cuya herramienta no toca al cuerpo.
  - `lightweight` (true/false; opcional, por defecto `false`): true hace copias ligeras (instancias): comparten la geometría del original, cada una con su propia posición, y editar la original las cambia a todas. Solo con bodies y sin combine; realize_copies las vuelve copias de verdad.
  - `distribution` ("spacing" | "extent"; opcional, por defecto `"spacing"`): "spacing" (x_spacing e y_spacing son la separación entre copias consecutivas) o "extent" (son la distancia TOTAL de la primera a la última).
  - `symmetric` (true/false; opcional, por defecto `false`): true reparte las copias a los dos lados del original.
  - `suppress` (lista de entero o null; opcional, por defecto `null`): copias a suprimir de la primera fila, por su posición en la dirección 1 (1 a x_count−1; 0 es el original; con symmetric también negativos, hacia el otro lado).
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de axis1 y axis2; vacío = el único cuerpo.
- CLI: `omnicad call rectangular_pattern --doc pieza.omnicad`

### `circular_pattern`

Patrón circular de cuerpos (bodies) o de operaciones del timeline (features) alrededor de un eje del origen (x, y o z). Con 360° las copias se reparten en toda la vuelta; con menos, entre el original y el ángulo total. count incluye el original.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `count` (entero; obligatorio): cantidad de instancias, original incluido (2 a 10.000).
  - `bodies` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) a repetir (id o nombre).
  - `axis` (texto; opcional, por defecto `"z"`): eje de giro: "x", "y", "z", o un eje de construcción (id o nombre), una arista recta o una cara cilíndrica (selector o id).
  - `total_angle` (número o expresión; opcional, por defecto `360`): ángulo en grados (número o expresión): con distribution=extent, el total (360 = vuelta completa); con spacing, el ángulo entre copias consecutivas.
  - `combine` (true/false; opcional, por defecto `false`): true para unir las copias al cuerpo original (solo con bodies).
  - `features` (texto o lista de texto o null; opcional, por defecto `null`): pasos anteriores del timeline (id o nombre) cuyo efecto se repite en vez de cuerpos (agujeros, cortes…; ver rectangular_pattern). No se combina con bodies.
  - `faces` (texto o lista de texto o null; opcional, por defecto `null`): caras a repetir (selector, ids de find_faces o lista): cada copia queda como un cuerpo de superficie nuevo. No se combina con bodies, features ni components.
  - `components` (lista de texto o null; opcional, por defecto `null`): componentes a repetir (id o nombre): cada copia es un componente nuevo con copias de sus cuerpos. No se combina con bodies, features ni faces.
  - `construction` (lista de texto o null; opcional, por defecto `null`): planos, ejes o puntos de construcción a repetir (id o nombre): cada copia es una entidad nueva. No se combina con bodies, features, faces ni components.
  - `compute` ("identical" | "optimized" | "adjust"; opcional, por defecto `"identical"`): cálculo de las copias de features (Compute Type): optimized e identical repiten la herramienta del paso tal cual (mismo resultado); adjust omite las copias cuya herramienta no toca al cuerpo.
  - `lightweight` (true/false; opcional, por defecto `false`): true hace copias ligeras (instancias): comparten la geometría del original, cada una con su propia posición, y editar la original las cambia a todas. Solo con bodies y sin combine; realize_copies las vuelve copias de verdad.
  - `distribution` ("extent" | "spacing"; opcional, por defecto `"extent"`): "extent" (total_angle es el ángulo TOTAL entre la primera y la última copia) o "spacing" (es el ángulo entre copias consecutivas).
  - `symmetric` (true/false; opcional, por defecto `false`): true reparte las copias a los dos lados del original.
  - `suppress` (lista de entero o null; opcional, por defecto `null`): copias a suprimir por su posición (1 a count−1; 0 es el original; con symmetric también negativos, hacia el otro lado).
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de axis; vacío = el único cuerpo.
- CLI: `omnicad call circular_pattern --doc pieza.omnicad count=…`

### `point_pattern`

Patrón en puntos (Point Pattern de FreeCAD; en Fusion, los agujeros en varios puntos de boceto): copia cuerpos (bodies) —o repite operaciones del timeline (features), p. ej. un agujero o una extrusión que corta— en cada punto. Los puntos son coordenadas (points) y/o todos los puntos sueltos de un boceto (sketch). Cada copia lleva el punto de referencia (reference; por defecto el origen) a uno de los puntos: para repetir un agujero, reference es el punto donde está el agujero. Un punto igual a la referencia no repite la copia.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) a repetir (id o nombre).
  - `features` (texto o lista de texto o null; opcional, por defecto `null`): pasos anteriores del timeline (id o nombre) cuyo efecto se repite en vez de cuerpos (agujeros, cortes…; ver rectangular_pattern). No se combina con bodies.
  - `faces` (texto o lista de texto o null; opcional, por defecto `null`): caras a repetir (selector, ids de find_faces o lista): cada copia queda como un cuerpo de superficie nuevo. No se combina con bodies, features ni components.
  - `components` (lista de texto o null; opcional, por defecto `null`): componentes a repetir (id o nombre): cada copia es un componente nuevo con copias de sus cuerpos. No se combina con bodies, features ni faces.
  - `construction` (lista de texto o null; opcional, por defecto `null`): planos, ejes o puntos de construcción a repetir (id o nombre): cada copia es una entidad nueva. No se combina con bodies, features, faces ni components.
  - `compute` ("identical" | "optimized" | "adjust"; opcional, por defecto `"identical"`): cálculo de las copias de features (Compute Type): optimized e identical repiten la herramienta del paso tal cual (mismo resultado); adjust omite las copias cuya herramienta no toca al cuerpo.
  - `points` (lista de lista de número o expresión o null; opcional, por defecto `null`): puntos [[x, y, z], …] en mm (números o expresiones) donde va cada copia.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre de un boceto: se usan todos sus puntos sueltos (los que no son de ninguna curva) y siguen al boceto si se edita.
  - `reference` (lista de número o expresión o null; opcional, por defecto `null`): punto [x, y, z] que se lleva a cada punto; vacío = el origen [0, 0, 0].
  - `combine` (true/false; opcional, por defecto `false`): true para unir las copias al cuerpo original (solo con bodies).
  - `lightweight` (true/false; opcional, por defecto `false`): true hace copias ligeras (instancias): comparten la geometría del original, cada una con su propia posición, y editar la original las cambia a todas. Solo con bodies y sin combine; realize_copies las vuelve copias de verdad.
  - `point_refs` (lista de texto o objeto o lista de número o null; opcional, por defecto `null`): puntos asociativos: vértices [x, y, z] del modelo, puntos de construcción (id o nombre) o {"sketch", "point"}; siguen al modelo si cambia.
  - `reference_point` (texto o objeto o lista de número o null; opcional, por defecto `null`): punto de referencia asociativo (vértice [x, y, z], punto de construcción o de boceto) en lugar de reference.
  - `suppress` (lista de entero o null; opcional, por defecto `null`): índices de las copias a suprimir (1 a N−1; 0 es el original), en este orden de puntos: primero los de point_refs y sketch y al final los de points.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se buscan los vértices de point_refs y reference_point; vacío = todos.
- CLI: `omnicad call point_pattern --doc pieza.omnicad`

### `path_pattern`

Patrón en ruta (Pattern on Path de Fusion; con twist, el Twisted Path Array de FreeCAD): copias de cuerpos (bodies) —o de operaciones del timeline (features)— a lo largo de curvas de un boceto. count incluye el original. distance es el largo TOTAL de la primera a la última (spacing_mode="extent") o la separación entre copias ("spacing"). start ubica el original sobre la ruta (0 a 1). orientation="path_direction" gira cada copia con la ruta; twist además la gira alrededor de la ruta, de a poco, hasta ese ángulo total en la última.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `path_sketch` (texto; opcional, por defecto `null`): id o nombre del boceto con la ruta; vacío si la ruta son aristas de un cuerpo (path_edges).
  - `count` (entero; opcional, por defecto `0`): cantidad de instancias, original incluido (2 a 10.000).
  - `distance` (número o expresión; opcional, por defecto `null`): largo total (extent) o separación entre copias (spacing), en mm o expresión.
  - `bodies` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) a repetir (id o nombre).
  - `features` (texto o lista de texto o null; opcional, por defecto `null`): pasos anteriores del timeline (id o nombre) cuyo efecto se repite en vez de cuerpos (agujeros, cortes…; ver rectangular_pattern). No se combina con bodies.
  - `faces` (texto o lista de texto o null; opcional, por defecto `null`): caras a repetir (selector, ids de find_faces o lista): cada copia queda como un cuerpo de superficie nuevo. No se combina con bodies, features ni components.
  - `components` (lista de texto o null; opcional, por defecto `null`): componentes a repetir (id o nombre): cada copia es un componente nuevo con copias de sus cuerpos. No se combina con bodies, features ni faces.
  - `construction` (lista de texto o null; opcional, por defecto `null`): planos, ejes o puntos de construcción a repetir (id o nombre): cada copia es una entidad nueva. No se combina con bodies, features, faces ni components.
  - `compute` ("identical" | "optimized" | "adjust"; opcional, por defecto `"identical"`): cálculo de las copias de features (Compute Type): optimized e identical repiten la herramienta del paso tal cual (mismo resultado); adjust omite las copias cuya herramienta no toca al cuerpo.
  - `path_curves` (lista de entero o null; opcional, por defecto `null`): ids de las curvas de la ruta (get_sketch); vacío = todas las curvas no de construcción del boceto.
  - `spacing_mode` ("extent" | "spacing"; opcional, por defecto `"extent"`): "extent" (distance es el largo total) o "spacing" (distance es la separación).
  - `start` (número o expresión; opcional, por defecto `0`): dónde está el original sobre la ruta, de 0 (inicio) a 1 (fin).
  - `orientation` ("identical" | "path_direction"; opcional, por defecto `"identical"`): "identical" (las copias solo se trasladan) o "path_direction" (giran con la tangente de la ruta).
  - `twist` (número o expresión; opcional, por defecto `0`): giro total alrededor de la ruta en grados (número o expresión): la copia k gira twist · k / (count − 1).
  - `symmetric` (true/false; opcional, por defecto `false`): true para repartir count copias hacia cada lado del original.
  - `combine` (true/false; opcional, por defecto `false`): true para unir las copias al cuerpo original (solo con bodies).
  - `lightweight` (true/false; opcional, por defecto `false`): true hace copias ligeras (instancias): comparten la geometría del original, cada una con su propia posición, y editar la original las cambia a todas. Solo con bodies y sin combine; realize_copies las vuelve copias de verdad.
  - `path_edges` (texto o lista de texto o null; opcional, por defecto `null`): aristas de un cuerpo (selector "edges:…" o ids de find_edges, o lista) como ruta continua, en lugar de path_sketch.
  - `suppress` (lista de entero o null; opcional, por defecto `null`): copias a suprimir por su posición sobre la ruta (1 a count−1; 0 es el original; con symmetric también negativos).
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de path_edges; vacío = el único cuerpo.
- CLI: `omnicad call path_pattern --doc pieza.omnicad`

### `multi_transform`

Multitransformación (MultiTransform de FreeCAD): patrón + simetría + patrón… en UN paso. transforms es una lista ordenada y cada transformación se aplica a TODAS las instancias de las anteriores (rectangular de 3 + mirror = 6). Tipos: {"type": "rectangular", "axis": "x", "count": 3, "spacing": 20} (y axis2, count2, spacing2, symmetric), {"type": "circular", "axis": "z", "count": 6, "total_angle": 360}, {"type": "mirror", "plane": "YZ"}, {"type": "points", "points": [[x, y, z]], "sketch": …, "reference": [x, y, z]} y {"type": "path", "path_sketch": …, "count": 4, "distance": 60, "twist": 90} (las mismas opciones que path_pattern). Repite cuerpos (bodies) u operaciones del timeline (features).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `transforms` (lista de objeto; obligatorio): lista ordenada de transformaciones (dicts con "type": rectangular, circular, mirror, points o path; ver la descripción).
  - `bodies` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) a repetir (id o nombre).
  - `features` (texto o lista de texto o null; opcional, por defecto `null`): pasos anteriores del timeline (id o nombre) cuyo efecto se repite en vez de cuerpos (agujeros, cortes…; ver rectangular_pattern). No se combina con bodies.
  - `combine` (true/false; opcional, por defecto `false`): true para unir las copias al cuerpo original (solo con bodies).
  - `lightweight` (true/false; opcional, por defecto `false`): true hace copias ligeras (instancias): comparten la geometría del original, cada una con su propia posición, y editar la original las cambia a todas. Solo con bodies y sin combine; realize_copies las vuelve copias de verdad.
  - `faces` (texto o lista de texto o null; opcional, por defecto `null`): caras a repetir (selector, ids de find_faces o lista): cada copia queda como un cuerpo de superficie nuevo. No se combina con bodies, features ni components.
  - `components` (lista de texto o null; opcional, por defecto `null`): componentes a repetir (id o nombre): cada copia es un componente nuevo con copias de sus cuerpos. No se combina con bodies, features ni faces.
  - `construction` (lista de texto o null; opcional, por defecto `null`): planos, ejes o puntos de construcción a repetir (id o nombre): cada copia es una entidad nueva. No se combina con bodies, features, faces ni components.
  - `compute` ("identical" | "optimized" | "adjust"; opcional, por defecto `"identical"`): cálculo de las copias de features (Compute Type): optimized e identical repiten la herramienta del paso tal cual (mismo resultado); adjust omite las copias cuya herramienta no toca al cuerpo.
- CLI: `omnicad call multi_transform --doc pieza.omnicad transforms=…`

### `drop_to_plane`

Apoya cuerpos en el plano del piso (Z = 0): los baja o sube en Z hasta que lo más bajo toque Z = 0. No es 'ground_component' (eso fija una pieza del ensamble). Sin body, apoya todos los cuerpos. El paso se recalcula con el modelo. El resultado trae z_min.before y z_min.after.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `body` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) a apoyar (id o nombre); vacío = todos los cuerpos del diseño.
  - `keep_relative` (true/false; opcional, por defecto `true`): true mueve todo junto (conserva las posiciones relativas); false apoya cada cuerpo por su cuenta.
- CLI: `omnicad call drop_to_plane --doc pieza.omnicad`

### `move_body`

Mueve (o copia) cuerpos, como Mover › Movimiento libre de Fusion: primero gira rotate = [rx, ry, rz] grados alrededor del pivote (en ese orden) y después DESPLAZA translate = [dx, dy, dz] mm, que se SUMA a la posición actual (no es una posición absoluta: un cuerpo con el centro en z = 2 y translate [0, 0, 15] queda en z = 17). Para llevarlo a una posición absoluta usá position = [x, y, z]: el centro de la caja de los cuerpos (después del giro) queda ahí. pivot='center' es el promedio de los centros de las cajas de los cuerpos y se RECALCULA con la geometría (si la pieza es asimétrica o se edita, el giro cambia de lugar); pivot='origin' gira alrededor del origen y da un giro estable. El resultado trae center.before y center.after. type: translate (direction + distance), rotate (axis + angle), point_to_point (origin_point a destination_point); pivot_point fija el pivote del giro libre.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `body` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) a mover (id o nombre); vacío si solo se mueven bocetos.
  - `translate` (lista de número o expresión o null; opcional, por defecto `null`): DESPLAZAMIENTO [dx, dy, dz] en mm que se suma a la posición actual (números o expresiones); vacío = sin desplazamiento.
  - `rotate` (lista de número o expresión o null; opcional, por defecto `null`): giro [rx, ry, rz] en grados (números o expresiones); vacío = sin giro.
  - `pivot` ("center" | "origin"; opcional, por defecto `"center"`): centro del giro: "center" (centro de las cajas de los cuerpos, se recalcula) u "origin" (origen, estable).
  - `copy` (true/false; opcional, por defecto `false`): true para dejar el original y crear cuerpos nuevos con el movimiento.
  - `position` (lista de número o expresión o null; opcional, por defecto `null`): posición ABSOLUTA [x, y, z] en mm del centro de la caja de los cuerpos; sin translate. Guarda el desplazamiento de ahora (position − centro): si la pieza cambia, el centro se corre con ella.
  - `lightweight` (true/false; opcional, por defecto `false`): true (con copy=true): copia ligera que comparte la geometría del original; realize_copies la vuelve real.
  - `type` ("free" | "translate" | "rotate" | "point_to_point"; opcional, por defecto `"free"`): "free" (por defecto), "translate" (direction + distance, o translate), "rotate" (axis + angle) o "point_to_point".
  - `direction` (texto o objeto; opcional, por defecto `null`): type=translate: eje, arista recta, cara plana o plano (selector, id o nombre); se mueve distance por él.
  - `distance` (número o expresión; opcional, por defecto `10`): type=translate con direction: desplazamiento en mm (número o expresión).
  - `axis` (texto o objeto; opcional, por defecto `null`): type=rotate: eje de construcción (id o nombre), arista recta o línea de boceto {"sketch", "curve"}.
  - `angle` (número o expresión; opcional, por defecto `90`): type=rotate: ángulo en grados (número o expresión).
  - `origin_point` (texto o objeto o lista de número o null; opcional, por defecto `null`): type=point_to_point: punto de partida (vértice [x, y, z], punto de construcción o {"sketch", "point"}).
  - `destination_point` (texto o objeto o lista de número o null; opcional, por defecto `null`): type=point_to_point: punto de llegada (mismas formas que origin_point).
  - `pivot_point` (texto o objeto o lista de número o null; opcional, por defecto `null`): type=free: pivote del giro (vértice [x, y, z], punto de construcción o {"sketch", "point"}); reemplaza a pivot.
  - `ref_body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de direction, axis y los puntos; vacío = el único cuerpo.
  - `sketches` (lista de texto o null; opcional, por defecto `null`): bocetos enteros a mover o copiar (id o nombre); quedan derivados (sin edición a mano); no con position.
- CLI: `omnicad call move_body --doc pieza.omnicad`

### `insert_fastener`

Inserta fijaciones normalizadas sobre agujeros o puntos, con tamaño automático.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `positions` (lista de texto o objeto o lista de número; obligatorio): aristas circulares, caras cilíndricas/cónicas, puntos o ejes; ids, selectores o {sketch, point}. En un eje se usa su origen y dirección.
  - `family` ("screw" | "nut" | "washer" | "rod" | "stud"; opcional, por defecto `"screw"`): screw (tornillo), nut (tuerca), washer (arandela), rod (varilla) o stud (espárrago).
  - `standard` (texto; opcional, por defecto `null`): norma ISO/DIN de la familia; vacío = la primera de su catálogo.
  - `size` (texto; opcional, por defecto `"auto"`): tamaño nominal, por ejemplo M6, o auto según el agujero; se corrige al tamaño normalizado más cercano.
  - `length` (número o expresión; opcional, por defecto `"auto"`): largo nominal en mm o auto según el espesor; se corrige al largo normalizado más cercano.
  - `thread` ("cosmetic" | "modeled"; opcional, por defecto `"cosmetic"`): cosmetic o modeled (filete helicoidal real).
  - `similar` (true/false; opcional, por defecto `true`): agrega agujeros iguales de la misma cara.
  - `direction` (texto o objeto o lista de número o null; opcional, por defecto `null`): dirección en puntos: eje, arista recta, plano o cara plana; vacío = normal del boceto o Z.
  - `flip` (true/false; opcional, por defecto `false`): invierte la colocación; sobre una cara usa el otro extremo.
  - `material` (texto; opcional, por defecto `"Acero"`): Acero, Acero inoxidable, Latón, Aluminio 6061, Titanio o Nylon.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
- CLI: `omnicad call insert_fastener --doc pieza.omnicad positions=…`

### `insert_canvas`

Embebe una imagen de referencia sobre un plano o cara plana (máximo 32 MB).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `path` (texto; obligatorio): ruta de una imagen PNG, JPG o BMP; se copia embebida y no depende del archivo original.
  - `plane` (texto o objeto o lista de número; opcional, por defecto `"XY"`): plano XY/XZ/YZ, construcción por id/nombre o una cara plana (selector o id).
  - `width` (número o expresión; opcional, por defecto `100`): ancho real en mm, positivo; con keep_aspect la altura conserva la proporción de la imagen.
  - `dx` (número o expresión; opcional, por defecto `0`): desplazamiento X sobre el plano, en mm o expresión.
  - `dy` (número o expresión; opcional, por defecto `0`): desplazamiento Y sobre el plano, en mm o expresión.
  - `angle` (número o expresión; opcional, por defecto `0`): giro sobre el plano en grados o expresión.
  - `opacity` (entero; opcional, por defecto `50`): opacidad de 0 a 100 por ciento.
  - `flip` (true/false; opcional, por defecto `false`): volteo horizontal de la imagen.
  - `flip_v` (true/false; opcional, por defecto `false`): volteo vertical de la imagen.
  - `height` (número o expresión; opcional, por defecto `null`): altura en mm, positiva; solo cuenta con keep_aspect=false (vacío = la del ancho y la proporción).
  - `keep_aspect` (true/false; opcional, por defecto `true`): la altura sale del ancho y la proporción de la imagen (como el candado del gizmo).
  - `scale` (número o expresión; opcional, por defecto `1`): factor uniforme positivo sobre ancho y altura; 1 conserva el tamaño.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
  - `name` (texto; opcional, por defecto `null`): nombre del lienzo; vacío = automático.
- CLI: `omnicad call insert_canvas --doc pieza.omnicad path=…`

### `create_base_feature`

Congela cuerpos sólidos o superficies como B-rep en un paso del timeline.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): cuerpos a congelar (id, nombre o lista); conservan su geometría aunque cambien pasos anteriores.
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = automático.
- CLI: `omnicad call create_base_feature --doc pieza.omnicad bodies=…`

### `fillet`

Redondea aristas: empalme de radio constante (por defecto), de longitud de cuerda (radius_type=chord) o de radio variable entre el inicio y el final de la arista (radius_type=variable, end_radius). Con faces_a hace un EMPALME DE REGLAS: todas las aristas de esas caras, o solo las que están entre faces_a y faces_b; rounds elige redondeos (aristas convexas), empalmes (cóncavas) o ambos. Se elige con un selector estilo CadQuery (p. ej. '|Z'; get_guide topic=selectores), con ids de find_edges (p. ej. 'Cuerpo1/E7', válidos hasta el próximo cambio del documento) o con una lista de ambos. Guarda referencias persistentes: sobrevive a un cambio de parámetros del modelo. Con tangent_chain (por defecto) el empalme sigue las aristas tangentes encadenadas. Si el radio no cabe, falla con OPERATION_FAILED y el documento queda igual. radius acepta número (mm) o expresión. radius_points suma puntos intermedios al radio variable. sets suma otros conjuntos de selección con sus propios radios en el mismo paso. type=full_round redondea del todo una cara central entre dos laterales planas, paralelas y perpendiculares (media caña de radio la mitad del ancho). asymmetric (radius y radius2, uno por cara) y continuity=g2 solo en aristas rectas entre caras planas, sin cadena tangente; corner_type=setback + setback (mm): el radio crece hacia las esquinas de tres aristas.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `edges` (texto o lista de texto o null; opcional, por defecto `null`): aristas a redondear: selector ("|Z"), id de find_edges ("Cuerpo1/E7") o lista. No con faces_a.
  - `radius` (número o expresión; opcional, por defecto `null`): radio en mm (número o expresión, p. ej. "espesor / 2"); con radius_type=variable es el inicial.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
  - `radius_type` ("constant" | "chord" | "variable" | "asymmetric"; opcional, por defecto `"constant"`): "constant", "chord" (chord_length), "variable" (de radius a end_radius) o "asymmetric" (radius y radius2).
  - `end_radius` (número o expresión; opcional, por defecto `null`): radio final en mm (número o expresión); obligatorio con radius_type=variable.
  - `chord_length` (número o expresión; opcional, por defecto `null`): longitud de cuerda en mm (número o expresión); obligatoria con radius_type=chord.
  - `tangent_chain` (true/false; opcional, por defecto `true`): true (por defecto) suma las aristas tangentes encadenadas; false empalma solo las elegidas.
  - `faces_a` (texto o lista de texto o null; opcional, por defecto `null`): empalme de reglas: caras (selector, ids o lista) cuyas aristas se redondean; reemplaza a edges.
  - `faces_b` (texto o lista de texto o null; opcional, por defecto `null`): empalme de reglas «entre»: segundo grupo; solo las aristas entre faces_a y faces_b; vacío = todas las de faces_a.
  - `rounds` ("both" | "rounds" | "fillets"; opcional, por defecto `"both"`): empalme de reglas: "both" (por defecto), "rounds" (solo aristas convexas) o "fillets" (solo cóncavas).
  - `radius_points` (lista de objeto o null; opcional, por defecto `null`): con radius_type=variable, puntos intermedios [{"position": 0..1, "radius": mm}].
  - `sets` (lista de objeto o null; opcional, por defecto `null`): otros conjuntos del mismo paso: [{"edges", "radius", "radius_type", "end_radius", "chord_length", "radius_points", "radius2", "continuity", "corner_type", "setback"}].
  - `type` ("fillet" | "full_round"; opcional, por defecto `"fillet"`): fillet (por defecto) o full_round (redondeo completo con center_face y side_faces).
  - `center_face` (texto; opcional, por defecto `null`): con full_round, la cara que se vuelve media caña (selector o id).
  - `side_faces` (lista de texto o null; opcional, por defecto `null`): con full_round, las dos caras laterales (selectores o ids).
  - `radius2` (número o expresión; opcional, por defecto `null`): radio sobre la segunda cara con radius_type=asymmetric.
  - `continuity` ("g1" | "g2"; opcional, por defecto `"g1"`): "g1" (por defecto) o "g2"; con radio constante o asimétrico.
  - `corner_type` ("rolling_ball" | "setback"; opcional, por defecto `"rolling_ball"`): "rolling_ball" (por defecto) o "setback" (pide setback).
  - `setback` (número o expresión; opcional, por defecto `null`): distancia en mm desde la esquina a la que el radio vuelve al pedido.
- CLI: `omnicad call fillet --doc pieza.omnicad`

### `chamfer`

Achaflana aristas: distancia igual en las dos caras (por defecto), dos distancias (type=two_distances, distance2) o distancia y ángulo (type=distance_angle, angle); flip pasa la primera distancia a la otra cara. Se elige con un selector estilo CadQuery (p. ej. '|Z'; get_guide topic=selectores), con ids de find_edges (p. ej. 'Cuerpo1/E7', válidos hasta el próximo cambio del documento) o con una lista de ambos. Guarda referencias persistentes: sobrevive a un cambio de parámetros del modelo. Con tangent_chain (por defecto) sigue las aristas tangentes encadenadas. distance, distance2 y angle aceptan número (mm o grados) o expresión. corner_type: chamfer (donde se juntan tres chaflanes queda una cara chica que los une, por defecto) o miter (los chaflanes se cortan en un punto; solo chaflanes planos y vértices con tres chaflanes) o blend (como miter, con la unión de los chaflanes redondeada).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `edges` (texto o lista de texto; obligatorio): aristas a achaflanar: selector ("|Z", ">Z"), id de find_edges ("Cuerpo1/E7") o lista de ids y selectores.
  - `distance` (número o expresión; obligatorio): distancia del chaflán en mm sobre cada cara (número o expresión con parámetros); con two_distances o distance_angle, la primera distancia.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
  - `type` ("equal" | "two_distances" | "distance_angle"; opcional, por defecto `"equal"`): "equal" (distancia igual), "two_distances" (distance y distance2) o "distance_angle" (distance y angle).
  - `distance2` (número o expresión; opcional, por defecto `null`): segunda distancia en mm; obligatoria con type=two_distances.
  - `angle` (número o expresión; opcional, por defecto `null`): ángulo en grados (entre 0 y 90, excluidos); obligatorio con type=distance_angle.
  - `flip` (true/false; opcional, por defecto `false`): true pasa la primera distancia a la otra cara (no hace nada con type=equal).
  - `tangent_chain` (true/false; opcional, por defecto `true`): true (por defecto) suma las aristas tangentes encadenadas; false achaflana solo las elegidas.
  - `corner_type` ("chamfer" | "miter" | "blend"; opcional, por defecto `"chamfer"`): "chamfer" (cara de unión en las esquinas, por defecto) o "miter" (las caras de los chaflanes se cortan en un punto) o "blend" (miter con la unión redondeada).
- CLI: `omnicad call chamfer --doc pieza.omnicad edges=… distance=…`

### `shell`

Vacía un cuerpo dejando paredes de un espesor dado; las caras elegidas se quitan (quedan abiertas). Se elige con un selector estilo CadQuery (p. ej. '>Z'; get_guide topic=selectores), con ids de find_faces (p. ej. 'Cuerpo1/F6', válidos hasta el próximo cambio del documento) o con una lista de ambos. Guarda referencias persistentes: sobrevive a un cambio de parámetros del modelo. direction: inside (las paredes quedan hacia adentro: el cuerpo no crece), outside (hacia afuera) o both. Con faces=[] (lista vacía) el cuerpo queda hueco y cerrado. Si el espesor es igual o mayor que el radio de un empalme de las caras vaciadas, el kernel no puede (radio interior cero o negativo): OPERATION_FAILED. En algunas caras B-spline el vaciado hacia afuera no se puede calcular: el error indica cómo armar dos solevaciones y restarlas. thickness acepta número (mm) o expresión.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `body` (texto; obligatorio): id o nombre del cuerpo a vaciar.
  - `faces` (texto o lista de texto; obligatorio): caras a quitar: selector (">Z" = la tapa), id de find_faces ("Cuerpo1/F6") o lista; [] = hueco cerrado.
  - `thickness` (número o expresión; obligatorio): espesor de pared en mm (número o expresión con parámetros); es el interior, y también el exterior si no se da outside_thickness.
  - `direction` ("inside" | "outside" | "both"; opcional, por defecto `"inside"`): "inside", "outside" o "both".
  - `tangent_chain` (true/false; opcional, por defecto `true`): true (por defecto) quita también las caras tangentes encadenadas a las elegidas.
  - `outside_thickness` (número o expresión; opcional, por defecto `null`): espesor exterior en mm distinto del interior (con direction=both u outside); vacío = el mismo que thickness.
  - `corners` ("sharp" | "rounded"; opcional, por defecto `"sharp"`): "sharp" (desfase afilado, por defecto) o "rounded" (desfase redondeado en las esquinas).
- CLI: `omnicad call shell --doc pieza.omnicad body=… faces=… thickness=…`

### `remove_fillets`

Quita de una vez todos los redondeos (empalmes) de un cuerpo con radio hasta max_radius («Remove Fillets» de Plasticity: defeaturing + unión de la topología que queda). No toca los agujeros taladrados. Deja un paso editable en el timeline; si no hay empalmes con ese filtro, falla con OPERATION_FAILED y el documento queda igual.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `body` (texto o lista de texto; obligatorio): id o nombre del cuerpo (o lista de cuerpos) al que sacarle los empalmes.
  - `max_radius` (número o expresión; obligatorio): radio máximo en mm (número o expresión): se quitan los redondeos con radio hasta ese valor.
- CLI: `omnicad call remove_fillets --doc pieza.omnicad body=… max_radius=…`

### `offset_faces`

Mueve caras de un cuerpo a lo largo de su normal (la mitad «cara» del comando Desfase; «Cara de desfase» de Fusion): distance > 0 agrega material, < 0 lo quita. Con tangent=true la cadena de caras tangentes se mueve junta. Se elige con un selector estilo CadQuery (p. ej. '>Z'; get_guide topic=selectores), con ids de find_faces (p. ej. 'Cuerpo1/F6', válidos hasta el próximo cambio del documento) o con una lista de ambos. Guarda referencias persistentes: sobrevive a un cambio de parámetros del modelo. Si el desfase no se puede calcular, falla con OPERATION_FAILED y el documento queda igual.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `faces` (texto o lista de texto; obligatorio): caras a mover: selector (">Z"), id de find_faces ("Cuerpo1/F6") o lista de ids y selectores.
  - `distance` (número o expresión; obligatorio): desplazamiento en mm sobre la normal exterior (número o expresión); negativo = hacia adentro.
  - `tangent` (true/false; opcional, por defecto `true`): true mueve también las caras tangentes encadenadas.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
- CLI: `omnicad call offset_faces --doc pieza.omnicad faces=… distance=…`

### `offset_edges`

Desfase de aristas o de curvas de un boceto («Offset Edge» y «Offset Face Loop» de Plasticity): crea un boceto NUEVO con curvas a `distance` de las elegidas, sin tocar ni cortar el cuerpo. Las aristas (edges: selector, ids de find_edges o lista) y las curvas de boceto (curves + sketch) se unen en cadenas y se desfasan sobre un plano: `plane` ("XY", "XZ", "YZ" o UNA cara plana: selector o id de find_faces) o, si no se da, el plano que las contiene a todas (una recta sola o aristas en línea no lo definen: falla y pide plane). distance > 0 va a la derecha del recorrido de la cadena (el sentido de la primera arista elegida) y las cadenas cerradas crecen; negativa, al otro lado; symmetric hace los dos lados. Las curvas quedan como geometría fija del boceto nuevo (sirve para extruir). Guarda referencias persistentes: sobrevive a un cambio de parámetros del modelo.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `distance` (número o expresión; obligatorio): separación en mm (número o expresión con parámetros); negativa = al lado contrario.
  - `edges` (texto o lista de texto o null; opcional, por defecto `null`): aristas a desfasar: selector ("|Z", ">Z"), id de find_edges ("Cuerpo1/E7") o lista; vacío = ninguna.
  - `curves` (lista de entero o null; opcional, por defecto `null`): ids de curvas de un boceto (get_sketch) a desfasar; piden `sketch`.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto de `curves`; vacío = el último boceto del timeline.
  - `plane` (texto; opcional, por defecto `null`): plano del desfase: "XY", "XZ", "YZ", el id o nombre de un plano de construcción o una cara plana (selector o id); vacío = el que contiene a todas.
  - `symmetric` (true/false; opcional, por defecto `false`): true hace el desfase a los dos lados (distance se toma en valor absoluto).
  - `corners` ("round" | "sharp"; opcional, por defecto `"round"`): round (arcos en las esquinas) o sharp (las esquinas se prolongan hasta cortarse).
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de edges y de plane; vacío = el único cuerpo.
- CLI: `omnicad call offset_edges --doc pieza.omnicad distance=…`

### `create_hole`

Hace agujeros redondos hacia adentro del material: simples, abocardados (counterbore) o avellanados (countersink), ciegos (depth), pasantes (through_all) o hasta una cara, plano o cuerpo (to). Tres formas de ubicarlos: (1) ASOCIATIVA, en puntos de un boceto: sketch + sketch_points (ids de get_sketch, p. ej. el centro de un círculo); el agujero sigue al punto si el boceto o sus cotas cambian, perpendicular al plano del boceto y hacia el lado del material (flip lo invierte); face es opcional (elige el cuerpo). (2) FIJA, sobre una cara plana: face con un selector (p. ej. '>Z') o un id de find_faces ('Cuerpo1/F6'; UNA cara plana) y points: [u, v] en mm en los ejes x,y de un boceto sobre esa cara (find_faces da el center_uv) o [x, y, z] del mundo (se proyecta sobre la cara); sin points, el centro de la cara. Esos puntos quedan fijos en el espacio aunque la cara se mueva. (3) REFERENCIAS: face + reference_edges y reference_distances ubican el agujero a esas distancias de dos aristas rectas (paramétrico). hole_tap: simple, clearance (agujero de paso ISO 273 para el tornillo thread='M8' con fit close/normal/loose), cosmetic (rosca solo informativa; diámetro = diameter o la broca de roscar), modeled (rosca real: thread, thread_class '6H', '2B', 'auto' o '' y print_clearance para imprimir en 3D) o taper (rosca cónica de tubería R/NPT: agujero cónico 1:16, rosca cosmética). El fondo es plano salvo drill_tip=true (cono de tip_angle, 118° por defecto). Una cuarta forma, ASOCIATIVA: positions con vértices [x, y, z] del modelo o puntos de construcción (el agujero entra hacia −Z; flip lo invierte). flip vale en todas las formas y bodies agujerea varios cuerpos a la vez. Medidas en número (mm) o expresión.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `diameter` (número o expresión; opcional, por defecto `null`): diámetro del agujero en mm (número o expresión); obligatorio con hole_tap simple, opcional con cosmetic.
  - `face` (texto; opcional, por defecto `null`): la cara plana donde se empieza: selector (">Z"), id de find_faces ("Cuerpo1/F6"). Tiene que dar UNA cara. Obligatoria con points, con reference_edges o sin sketch_points; con sketch_points es opcional y solo elige el cuerpo.
  - `points` (lista de lista de número o null; opcional, por defecto `null`): posiciones fijas sobre face: lista de [u, v] (ejes x,y de un boceto sobre la cara) o [x, y, z] (mundo); vacío = centro de la cara. No se combina con sketch_points ni con reference_edges.
  - `depth` (número o expresión; opcional, por defecto `null`): profundidad en mm hasta el fondo plano; obligatoria salvo con through_all o to.
  - `through_all` (true/false; opcional, por defecto `false`): true atraviesa todo el cuerpo (ignora depth).
  - `hole_type` ("simple" | "counterbore" | "countersink"; opcional, por defecto `"simple"`): "simple", "counterbore" (abocardado) o "countersink" (avellanado).
  - `counterbore_diameter` (número o expresión; opcional, por defecto `null`): diámetro del abocardado en mm (mayor que diameter); solo con counterbore.
  - `counterbore_depth` (número o expresión; opcional, por defecto `null`): profundidad del abocardado en mm; solo con counterbore.
  - `countersink_diameter` (número o expresión; opcional, por defecto `null`): diámetro del avellanado en la superficie en mm; solo con countersink.
  - `countersink_angle` (número o expresión; opcional, por defecto `90`): ángulo total del avellanado en grados; solo con countersink.
  - `drill_tip` (true/false; opcional, por defecto `false`): true deja el fondo en cono como una broca (ángulo tip_angle); false, fondo plano.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que se evalúan los selectores (y que se agujerea con sketch_points); vacío = el único cuerpo del documento.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto de sketch_points; vacío = el último boceto.
  - `sketch_points` (lista de entero o null; opcional, por defecto `null`): ids de puntos del boceto (get_sketch los lista; el centro de un círculo también es un punto): un agujero asociativo en cada uno.
  - `flip` (true/false; opcional, por defecto `false`): true invierte el sentido del agujero: con sketch_points el automático (hacia el material); con las demás formas, el normal (hacia adentro de la cara, o −Z con positions).
  - `hole_tap` ("simple" | "clearance" | "cosmetic" | "modeled" | "taper"; opcional, por defecto `"simple"`): "simple", "clearance" (paso libre ISO 273), "cosmetic", "modeled" (rosca real) o "taper" (tubería cónica).
  - `thread` (texto; opcional, por defecto `null`): rosca: "M8", "M8x1", "1/4-20 UNC", "Tr20x4", "G1/2" (taper: "R1/2" o "1/2 NPT"); con clearance, el tornillo ("M8").
  - `thread_class` (texto; opcional, por defecto `"auto"`): clase de la rosca modelada: "6H"/"6G" (métrica), "2B"/"3B" (unificada), "auto" (6H o 2B si hay datos) o "" (perfil básico).
  - `fit` ("close" | "normal" | "loose"; opcional, por defecto `"normal"`): ajuste del agujero de paso (clearance): "close" (serie fina), "normal" (media) o "loose" (gruesa).
  - `print_clearance` (número o expresión; opcional, por defecto `0`): holgura radial extra en mm de la rosca modelada (flancos y agujero), para imprimir en 3D.
  - `left_hand` (true/false; opcional, por defecto `false`): true = rosca a izquierdas (solo modeled).
  - `to` (texto; opcional, por defecto `null`): extensión «hasta»: "XY"/"XZ"/"YZ" o un plano de construcción, un cuerpo (id o nombre) o UNA cara (selector o id).
  - `to_offset` (número o expresión; opcional, por defecto `0`): desfase en mm sobre el «hasta» (positivo = más hondo).
  - `reference_edges` (lista de texto o null; opcional, por defecto `null`): posición por referencias: DOS aristas rectas (selector o id de find_edges), no paralelas.
  - `reference_distances` (lista de número o expresión o null; opcional, por defecto `null`): las DOS distancias en mm del centro del agujero a cada arista de reference_edges.
  - `positions` (lista de texto o objeto o lista de número o null; opcional, por defecto `null`): posición asociativa en puntos del modelo: vértices [x, y, z] (a menos de 0,001 mm de un vértice), puntos de construcción (id o nombre) o {"sketch", "point"}; el agujero va hacia −Z. No se combina con points, sketch_points ni reference_edges.
  - `tip_angle` (número o expresión; opcional, por defecto `118`): ángulo total de la punta de broca en grados (con drill_tip); 118 por defecto.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): cuerpos extra que se agujerean con el mismo agujero (ids o nombres), además del de face/body; vacío = solo ese.
- CLI: `omnicad call create_hole --doc pieza.omnicad`

### `create_thread`

Rosca sobre caras cilíndricas (ejes o agujeros: se detecta solo), como el comando Rosca de Fusion. Se elige con un selector estilo CadQuery (p. ej. '%CYLINDER'; get_guide topic=selectores), con ids de find_faces (p. ej. 'Cuerpo1/F3', válidos hasta el próximo cambio del documento) o con una lista de ambos. Guarda referencias persistentes: sobrevive a un cambio de parámetros del modelo. thread: designación ('M10', 'M10x1.25', '1/4-20 UNC', 'Tr20x4', '1/2-10 ACME', 'G1/2'); vacío = el tamaño de family más cercano al diámetro de la cara. thread_class: '6g'/'6h'/'6H'/'6G' (métrica, ISO 965-1), '2A'/'3A'/'2B'/'3B' (unificada, ASME B1.1), 'auto' (la de Fusion: 6H/6g o 2B/2A, si hay datos del tamaño) o '' (perfil básico): corre los flancos al centro de la tolerancia. print_clearance agrega holgura radial para imprimir en 3D. modeled=false = cosmética (no cambia la geometría; las roscas cónicas R/NPT siempre quedan cosméticas sobre una cara cilíndrica). length vacío = largo completo; offset corre el inicio. Perfil según el tipo: 60° (M, UN), 55° (G), 30° (Tr) o 29° (ACME).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `faces` (texto o lista de texto; obligatorio): caras cilíndricas a roscar: selector ("%CYLINDER"), id de find_faces ("Cuerpo1/F3") o lista.
  - `thread` (texto; opcional, por defecto `null`): designación de la rosca ("M10", "M10x1.25", "1/4-20 UNC", "Tr20x4", "G1/2"…); vacío = automática según la cara.
  - `family` ("iso_metric" | "unified" | "trapezoidal" | "acme" | "bsp_parallel" | "bsp_taper" | "npt"; opcional, por defecto `"iso_metric"`): tipo de rosca para el tamaño automático: iso_metric, unified, trapezoidal, acme, bsp_parallel, bsp_taper o npt.
  - `thread_class` (texto; opcional, por defecto `"auto"`): clase de tolerancia: "6g", "6H", "2A", "2B"…, "auto" (la de Fusion) o "" (perfil básico).
  - `modeled` (true/false; opcional, por defecto `true`): true corta el filete real; false = rosca cosmética (la geometría no cambia).
  - `length` (número o expresión; opcional, por defecto `null`): largo roscado en mm (número o expresión); vacío = toda la cara.
  - `offset` (número o expresión; opcional, por defecto `0`): distancia en mm desde el extremo de la cara hasta donde empieza la rosca (con length).
  - `left_hand` (true/false; opcional, por defecto `false`): true = rosca a izquierdas.
  - `reverse` (true/false; opcional, por defecto `false`): true mide length y offset desde el otro extremo de la cara.
  - `print_clearance` (número o expresión; opcional, por defecto `0`): holgura radial extra en mm (flancos), para piezas impresas en 3D.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
- CLI: `omnicad call create_thread --doc pieza.omnicad faces=…`

### `draft`

Desmoldeo: inclina caras un ángulo respecto de un plano neutro (la cara o el plano que no se mueve), para poder sacar la pieza del molde. Las caras que se alejan del plano neutro se angostan (ángulo positivo). type=parting_line toma la dirección de extracción de pull_direction y la línea de partición de parting_tool (plano, cara plana o curva plana) en lugar de neutral; con parting_line_type=move: cada cara gira entera alrededor de su borde del lado contrario (move_direction above/below) o de fixed_edges; both deja la línea. angle_mode: absolute (por defecto, desde la dirección de extracción) o relative (se suma al desmoldeo de la cara; falla en conos, toros y cilindros inclinados). Se elige con un selector estilo CadQuery (p. ej. '#Z'; get_guide topic=selectores), con ids de find_faces (p. ej. 'Cuerpo1/F2', válidos hasta el próximo cambio del documento) o con una lista de ambos. Guarda referencias persistentes: sobrevive a un cambio de parámetros del modelo. angle acepta número (grados) o expresión.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `faces` (texto o lista de texto; obligatorio): caras a inclinar: selector ("#Z" = las laterales de una caja), id de find_faces o lista.
  - `angle` (número o expresión; obligatorio): ángulo de desmoldeo en grados (número o expresión), p. ej. 3.
  - `neutral` (texto; opcional, por defecto `"XY"`): plano neutro: "XY", "XZ", "YZ", el id o nombre de un plano de construcción, o una cara plana (selector o id, p. ej. "<Z"); define la dirección de extracción.
  - `reverse` (true/false; opcional, por defecto `false`): true invierte la dirección de extracción.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
  - `sides` ("one" | "two" | "symmetric"; opcional, por defecto `"one"`): "one" (un lado, por defecto), "two" (dos lados: angle y angle2) o "symmetric" (simétrico: el mismo ángulo a los dos lados del plano neutro).
  - `angle2` (número o expresión; opcional, por defecto `null`): ángulo del segundo lado en grados; obligatorio con sides=two.
  - `type` ("fixed_plane" | "parting_line"; opcional, por defecto `"fixed_plane"`): fixed_plane (plano neutro en neutral) o parting_line (pull_direction y parting_tool).
  - `angle_mode` ("relative" | "absolute"; opcional, por defecto `"absolute"`): absolute (por defecto: se mide desde la dirección de extracción) o relative (se suma al desmoldeo que la cara ya tiene).
  - `pull_direction` (texto o objeto; opcional, por defecto `null`): con parting_line, la dirección de extracción: plano de construcción, cara plana (id o selector) o eje.
  - `parting_tool` (texto o objeto; opcional, por defecto `null`): con parting_line, la línea de partición: plano, cara plana o curva plana (arista o curva de boceto).
  - `parting_line_type` ("fixed" | "move"; opcional, por defecto `"fixed"`): con parting_line, "fixed" (por defecto) o "move" (la línea se mueve).
  - `move_direction` ("above" | "both" | "below"; opcional, por defecto `"both"`): con move: "above" (bisagra en el borde más atrás de la extracción), "below" (el más adelante) o "both".
  - `fixed_edges` (texto o lista de texto o null; opcional, por defecto `null`): con move, la arista bisagra (selector o ids).
- CLI: `omnicad call draft --doc pieza.omnicad faces=… angle=…`

### `create_clearance_test`

Crea la pieza de calibración de holguras para impresión 3D (como la tira de tolerancias de Cura): una placa con count agujeros pasantes de Ø diameter + 2·holgura, con la holgura radial creciente desde start_clearance en saltos de step y su valor grabado junto a cada agujero, más un peine con los pernos de Ø diameter a la misma distancia. Se imprimen los dos (quedan lado a lado en el plano XY, apoyados en Z = 0), se prueba cuál agujero encaja bien y ese valor es el print_clearance de create_hole y create_thread. Es UN paso del timeline con dos cuerpos nuevos.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `diameter` (número o expresión; obligatorio): diámetro del perno en mm; los agujeros miden diameter + 2·holgura.
  - `start_clearance` (número o expresión; opcional, por defecto `0.1`): holgura radial del primer agujero en mm (0 o más).
  - `step` (número o expresión; opcional, por defecto `0.1`): lo que sube la holgura de un agujero al siguiente, en mm (positivo).
  - `count` (entero; opcional, por defecto `5`): cantidad de agujeros (de 1 a 20).
  - `thickness` (número o expresión; opcional, por defecto `3`): espesor de la placa en mm; el peine tiene un perno que la atraviesa.
  - `labels` (true/false; opcional, por defecto `true`): true para grabar la holgura de cada agujero (0,4 mm de profundidad).
- CLI: `omnicad call create_clearance_test --doc pieza.omnicad diameter=…`

### `split_face`

Divide caras con un plano, cara, arista o curva de boceto. split_type: surface (proyecta la herramienta sobre la cara, por defecto), vector (la proyecta a lo largo de direction y parte una vez por cada cruce) o closest_point (cada punto de la herramienta va al más cercano de la cara).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `faces` (texto o lista de texto; obligatorio): caras a dividir: selector, ids de find_faces o lista de ambos.
  - `tool` (texto o objeto o lista de número; obligatorio): plano, cara, arista o {sketch, curve}; acepta id/nombre de construcción, selector o id de find_faces/find_edges.
  - `extend` (true/false; opcional, por defecto `true`): extiende la herramienta de división (solo con split_type=surface).
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
  - `split_type` ("surface" | "vector" | "closest_point"; opcional, por defecto `"surface"`): surface, vector o closest_point; vector y closest_point necesitan curvas, aristas o una cara como tool.
  - `direction` (texto o objeto o lista de número o null; opcional, por defecto `null`): dirección de proyección con split_type=vector: eje X/Y/Z, eje o arista recta de construcción, plano o cara plana (su normal).
- CLI: `omnicad call split_face --doc pieza.omnicad faces=… tool=…`

### `split_body`

Parte un cuerpo en varios con un plano, una cara u otro cuerpo.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `body` (texto; obligatorio): id o nombre del cuerpo a dividir.
  - `tool` (texto o objeto o lista de número; obligatorio): plano de origen/construcción, una cara (selector o id), o cuerpo herramienta por id/nombre o {body: nombre}.
  - `extend` (true/false; opcional, por defecto `true`): extiende la herramienta de división.
- CLI: `omnicad call split_body --doc pieza.omnicad body=… tool=…`

### `silhouette_split`

Divide un cuerpo por su silueta vista desde una dirección. operation: faces_only (solo parte las caras; el cuerpo sigue siendo uno), shelled_body (parte en dos un cuerpo vaciado) o solid_body (parte en dos un sólido). Las dos últimas necesitan que la línea de partición sea plana.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `body` (texto; obligatorio): id o nombre del cuerpo de destino.
  - `direction` (texto o objeto o lista de número; opcional, por defecto `"Z"`): eje, arista recta, plano o cara plana: X/Y/Z, XY/XZ/YZ, construcción, selector o id.
  - `operation` ("faces_only" | "shelled_body" | "solid_body"; opcional, por defecto `"faces_only"`): faces_only, shelled_body (cuerpo vaciado) o solid_body (cuerpo sólido).
- CLI: `omnicad call silhouette_split --doc pieza.omnicad body=…`

### `replace_face`

Lleva caras de un cuerpo hasta otra cara o un plano.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `faces` (texto o lista de texto; obligatorio): caras de origen: selector, ids de find_faces o lista.
  - `target` (texto o objeto o lista de número; obligatorio): una cara o plano de destino: selector, id de find_faces, XY/XZ/YZ o construcción por id/nombre.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
- CLI: `omnicad call replace_face --doc pieza.omnicad faces=… target=…`

### `remove_bodies`

Quita cuerpos del diseño conservando la operación en el timeline.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): id, nombre o lista de cuerpos a quitar.
- CLI: `omnicad call remove_bodies --doc pieza.omnicad bodies=…`

### `delete_faces`

Borra caras y cierra el hueco extendiendo sus vecinas.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `faces` (texto o lista de texto; obligatorio): caras a borrar: selector, ids de find_faces o lista.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
- CLI: `omnicad call delete_faces --doc pieza.omnicad faces=…`

### `gear_info`

Calcula las medidas de un engranaje cilíndrico de evolvente sin modelarlo (ISO 21771, perfil de referencia ISO 53): diámetros primitivo, base, exterior y de fondo, paso, espesor del diente, dientes mínimos sin socavado (criterio estricto: 18 con 20°; el límite teórico, 17,1, va en min_teeth_theoretical) y desplazamiento mínimo. Con teeth2, también el par exterior: distancia entre centros, relación, ángulo de presión de trabajo, grado de recubrimiento e interferencia.

- Modifica el documento: no.
- Parámetros:
  - `module` (número; obligatorio): módulo normal en mm (en un engranaje recto, el módulo).
  - `teeth` (entero; obligatorio): cantidad de dientes.
  - `pressure_angle` (número; opcional, por defecto `20`): ángulo de presión en grados (20 es el normal de ISO 53).
  - `helix_angle` (número; opcional, por defecto `0`): ángulo de hélice en grados (0 = recto; positivo = hélice a derechas).
  - `profile_shift` (número; opcional, por defecto `0`): coeficiente de desplazamiento de perfil x (0 = sin desplazar).
  - `clearance` (número; opcional, por defecto `0.25`): holgura de fondo como fracción del módulo (0.25 en ISO 53).
  - `backlash` (número; opcional, por defecto `0`): juego circunferencial del par en el primitivo, en mm (cada rueda adelgaza la mitad).
  - `teeth2` (entero; opcional, por defecto `null`): dientes del segundo engranaje para calcular el par; vacío = solo este engranaje.
  - `profile_shift2` (número; opcional, por defecto `0`): desplazamiento de perfil del segundo engranaje.
- CLI: `omnicad call gear_info --doc pieza.omnicad module=… teeth=…`

### `create_gear`

Crea un engranaje cilíndrico de evolvente (perfil de referencia ISO 53), recto o, con helix_angle, helicoidal, como un paso del timeline (tipo «engranaje»; medidas como expresiones con parámetros). El eje sigue la normal del plano y el primer diente apunta al eje x del plano. Devuelve también sus diámetros (gear). Para dos que engranan, create_gear_pair.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `module` (número o expresión; obligatorio): módulo normal en mm (número o expresión).
  - `teeth` (número o expresión; obligatorio): cantidad de dientes (entero, o expresión que dé un entero).
  - `width` (número o expresión; opcional, por defecto `10`): ancho del engranaje a lo largo del eje, en mm.
  - `pressure_angle` (número o expresión; opcional, por defecto `20`): ángulo de presión en grados (20 es el normal).
  - `helix_angle` (número o expresión; opcional, por defecto `0`): ángulo de hélice en grados; 0 = recto, positivo = a derechas.
  - `profile_shift` (número o expresión; opcional, por defecto `0`): coeficiente de desplazamiento de perfil x.
  - `clearance` (número o expresión; opcional, por defecto `0.25`): holgura de fondo como fracción del módulo (0.25 en ISO 53).
  - `backlash` (número o expresión; opcional, por defecto `0`): juego del par en el primitivo, en mm (este engranaje adelgaza la mitad).
  - `bore` (número o expresión; opcional, por defecto `0`): diámetro del agujero central en mm; 0 = macizo.
  - `rotation` (número o expresión; opcional, por defecto `0`): giro del engranaje alrededor de su eje, en grados.
  - `plane` (texto; opcional, por defecto `"XY"`): plano donde se apoya: "XY", "XZ", "YZ" o el id/nombre de un plano de construcción, o una cara plana (selector o id de find_faces).
  - `center` (lista de número o expresión o null; opcional, por defecto `null`): [x, y] del centro sobre el plano, en mm; vacío = el origen del plano.
  - `center_point` (texto o objeto o lista de número o null; opcional, por defecto `null`): punto asociativo donde va el centro (o el comienzo): vértice (id de find_in_window o selector), punto de construcción (id o nombre) o {sketch, point}; [x, y] de center se suma a partir de él sobre el plano; vacío = el origen del plano.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de plane y center_point; vacío = el único cuerpo.
- CLI: `omnicad call create_gear --doc pieza.omnicad module=… teeth=…`

### `create_gear_pair`

Crea dos engranajes de evolvente que engranan, en UN paso del timeline: el segundo a la distancia entre centros de trabajo (m·(z1+z2)/2 sin desplazamientos), en la dirección dada y girado medio diente para que los dientes entren en los huecos (con hélice, el segundo es de la mano contraria). Con assembly (por defecto) agrega además, con las operaciones de ENSAMBLAR, un componente por engranaje, una unión de revolución «como está» en cada eje y el vínculo de movimiento con la relación de dientes (giran en sentidos contrarios): todo es un solo paso de deshacer.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `module` (número o expresión; obligatorio): módulo normal en mm de los dos engranajes.
  - `teeth1` (número o expresión; obligatorio): dientes del primer engranaje (el del centro).
  - `teeth2` (número o expresión; obligatorio): dientes del segundo engranaje.
  - `width` (número o expresión; opcional, por defecto `10`): ancho de los dos engranajes, en mm.
  - `pressure_angle` (número o expresión; opcional, por defecto `20`): ángulo de presión en grados.
  - `helix_angle` (número o expresión; opcional, por defecto `0`): ángulo de hélice del primero en grados (el segundo lleva el contrario); 0 = rectos.
  - `profile_shift1` (número o expresión; opcional, por defecto `0`): desplazamiento de perfil x del primero.
  - `profile_shift2` (número o expresión; opcional, por defecto `0`): desplazamiento de perfil x del segundo (con x1 + x2 ≠ 0 cambia la distancia entre centros).
  - `clearance` (número o expresión; opcional, por defecto `0.25`): holgura de fondo como fracción del módulo.
  - `backlash` (número o expresión; opcional, por defecto `0`): juego del par en el primitivo, en mm (cada engranaje adelgaza la mitad).
  - `bore1` (número o expresión; opcional, por defecto `0`): diámetro del agujero central del primero en mm; 0 = macizo.
  - `bore2` (número o expresión; opcional, por defecto `0`): diámetro del agujero central del segundo en mm; 0 = macizo.
  - `direction` (número o expresión; opcional, por defecto `0`): dirección del centro del segundo vista desde el primero, en grados desde el eje x del plano.
  - `rotation` (número o expresión; opcional, por defecto `0`): giro del primero alrededor de su eje, en grados (el segundo gira lo que le corresponde para engranar).
  - `plane` (texto; opcional, por defecto `"XY"`): plano donde se apoyan: "XY", "XZ", "YZ" o el id/nombre de un plano de construcción, o una cara plana (selector o id de find_faces).
  - `center` (lista de número o expresión o null; opcional, por defecto `null`): [x, y] del centro del primero sobre el plano, en mm; vacío = el origen del plano.
  - `center_point` (texto o objeto o lista de número o null; opcional, por defecto `null`): punto asociativo donde va el centro (o el comienzo): vértice (id de find_in_window o selector), punto de construcción (id o nombre) o {sketch, point}; [x, y] de center se suma a partir de él sobre el plano; vacío = el origen del plano.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de plane y center_point; vacío = el único cuerpo.
  - `assembly` (true/false; opcional, por defecto `true`): true para crear además los componentes, las uniones de revolución y el vínculo de movimiento.
- CLI: `omnicad call create_gear_pair --doc pieza.omnicad module=… teeth1=… teeth2=…`

### `create_rack`

Crea una cremallera recta con el perfil de referencia ISO 53 (paso π·módulo, flancos rectos al ángulo de presión) como un paso del timeline. La línea primitiva va sobre el eje x del plano desde center, los dientes hacia +y del plano y el ancho por la normal; los extremos caen en el medio de un hueco.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `module` (número o expresión; obligatorio): módulo en mm.
  - `teeth` (número o expresión; obligatorio): cantidad de dientes (el largo es teeth × π × module).
  - `width` (número o expresión; opcional, por defecto `10`): ancho a lo largo de la normal del plano, en mm.
  - `height` (número o expresión; opcional, por defecto `10`): alto de la base a la línea primitiva, en mm (mayor que 1.25 × module).
  - `pressure_angle` (número o expresión; opcional, por defecto `20`): ángulo de presión (de los flancos) en grados.
  - `clearance` (número o expresión; opcional, por defecto `0.25`): holgura de fondo como fracción del módulo.
  - `backlash` (número o expresión; opcional, por defecto `0`): juego en la línea primitiva, en mm (el diente adelgaza la mitad).
  - `rotation` (número o expresión; opcional, por defecto `0`): giro alrededor de la normal del plano, en grados.
  - `plane` (texto; opcional, por defecto `"XY"`): plano donde se apoya: "XY", "XZ", "YZ" o el id/nombre de un plano de construcción, o una cara plana (selector o id de find_faces).
  - `center` (lista de número o expresión o null; opcional, por defecto `null`): [x, y] del inicio de la línea primitiva sobre el plano, en mm; vacío = el origen del plano.
  - `center_point` (texto o objeto o lista de número o null; opcional, por defecto `null`): punto asociativo donde va el centro (o el comienzo): vértice (id de find_in_window o selector), punto de construcción (id o nombre) o {sketch, point}; [x, y] de center se suma a partir de él sobre el plano; vacío = el origen del plano.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de plane y center_point; vacío = el único cuerpo.
- CLI: `omnicad call create_rack --doc pieza.omnicad module=… teeth=…`

### `create_sprocket`

Crea una rueda dentada para cadena de rodillos con la forma de diente de ISO 606 (hueco medio) como un paso del timeline. chain elige la cadena (05B…16B, 08A…16A = ANSI 40…80) o 'custom' con pitch y roller_diameter propios; sin width, el ancho del diente sale de la norma (0,93 o 0,95 × ancho interior de la cadena).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `teeth` (número o expresión; obligatorio): cantidad de dientes (6 o más).
  - `chain` ("05B" | "06B" | "08B" | "10B" | "12B" | "16B" | "08A" | "10A" | "12A" | "16A" | "custom"; opcional, por defecto `"08B"`): designación ISO 606 de la cadena ("08B", "10A"…) o "custom".
  - `pitch` (número o expresión; opcional, por defecto `null`): paso de la cadena en mm (solo con chain="custom").
  - `roller_diameter` (número o expresión; opcional, por defecto `null`): diámetro del rodillo en mm (solo con chain="custom").
  - `width` (número o expresión; opcional, por defecto `null`): ancho del diente en mm; vacío = el de ISO 606 para la cadena (obligatorio con "custom").
  - `bore` (número o expresión; opcional, por defecto `0`): diámetro del agujero central en mm; 0 = macizo.
  - `rotation` (número o expresión; opcional, por defecto `0`): giro alrededor del eje, en grados.
  - `plane` (texto; opcional, por defecto `"XY"`): plano donde se apoya: "XY", "XZ", "YZ" o el id/nombre de un plano de construcción, o una cara plana (selector o id de find_faces).
  - `center` (lista de número o expresión o null; opcional, por defecto `null`): [x, y] del centro sobre el plano, en mm; vacío = el origen del plano.
  - `center_point` (texto o objeto o lista de número o null; opcional, por defecto `null`): punto asociativo donde va el centro (o el comienzo): vértice (id de find_in_window o selector), punto de construcción (id o nombre) o {sketch, point}; [x, y] de center se suma a partir de él sobre el plano; vacío = el origen del plano.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de plane y center_point; vacío = el único cuerpo.
- CLI: `omnicad call create_sprocket --doc pieza.omnicad teeth=…`

### `create_shaft`

Asistente de ejes: crea un eje escalonado de revolución a partir de una tabla de tramos (diámetro, largo y, en cada extremo, chaflán a 45° o empalme) como un paso del timeline (tipo «eje_escalonado»). El eje sale de center por la normal del plano (en XY, hacia +Z), con los tramos en orden. Un chaflán o empalme va sobre la esquina de ese tramo: convexa en la punta o en un escalón que baja, cóncava en uno que sube. operation cut hace un agujero escalonado.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `segments` (lista de objeto; obligatorio): tramos en orden, cada uno {"diameter": mm, "length": mm, "start": "none"|"chamfer"|"fillet", "start_size": mm, "end": "none"|"chamfer"|"fillet", "end_size": mm}; diameter y length son obligatorios y todos aceptan expresiones.
  - `plane` (texto; opcional, por defecto `"XY"`): plano de donde sale el eje: "XY", "XZ", "YZ", el id/nombre de un plano de construcción, o una cara plana (selector o id de find_faces).
  - `center` (lista de número o expresión o null; opcional, por defecto `null`): [x, y] del comienzo del eje sobre el plano, en mm; vacío = el origen del plano.
  - `center_point` (texto o objeto o lista de número o null; opcional, por defecto `null`): punto asociativo donde va el centro (o el comienzo): vértice (id de find_in_window o selector), punto de construcción (id o nombre) o {sketch, point}; [x, y] de center se suma a partir de él sobre el plano; vacío = el origen del plano.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de plane y center_point; vacío = el único cuerpo.
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
- CLI: `omnicad call create_shaft --doc pieza.omnicad segments=…`

### `assign_plastic_rule`

Asigna una regla de plástico a un componente (PLÁSTICO › Asignar regla de plástico): el material físico de la regla pasa a todos sus cuerpos y la regla queda guardada en el componente (list_plastic_rules dice cuáles). Con create_parameters=true sus valores quedan además como parámetros del diseño (PlasticThickness, PlasticDraftAngle y PlasticNominalRadius) para usarlos en Extruir, Nervio, Red, Vaciado, Desmoldeo… Una regla distinta, asignada después al mismo componente, reemplaza a la anterior. delete_feature quita la asignación.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `component` (texto; obligatorio): id o nombre del componente (get_assembly).
  - `rule` (texto; opcional, por defecto `"ABS 2 mm"`): nombre de la regla (list_plastic_rules); vacío = "ABS 2 mm".
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Regla de plástico<n>».
  - `create_parameters` (true/false; opcional, por defecto `false`): true crea (o actualiza) los parámetros PlasticThickness (mm), PlasticDraftAngle (deg) y PlasticNominalRadius (mm) con los valores de la regla.
- CLI: `omnicad call assign_plastic_rule --doc pieza.omnicad component=…`

### `rebuild_features`

Find Features que rehace: reconoce los agujeros (también abocardados), empalmes y chaflanes de un cuerpo sin historial y los vuelve pasos paramétricos del timeline, uno por uno: borra las caras de la función (delete_faces, las vecinas cierran el hueco) y la crea de nuevo con create_hole, fillet o chamfer y las medidas reconocidas; después vuelve a reconocer sobre el cuerpo nuevo. Cada función rehecha se verifica: el volumen y la caja del cuerpo tienen que seguir iguales a los del original (1e-3 relativo); si no, ese cambio se deshace y la función queda en not_rebuilt con el motivo. Extrusiones, revoluciones, simetrías y patrones solo se informan (find_features). Todo es UN paso de deshacer.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo sólido; vacío = el único cuerpo.
  - `types` (lista de "hole" | "fillet" | "chamfer" | "extrude" o null; opcional, por defecto `null`): qué rehacer: hole, fillet, chamfer o extrude; vacío = hole, fillet y chamfer. extrude solo para un cuerpo prisma (agujeros pasantes en su perfil): lo rehace como boceto + extrusión y reemplaza al cuerpo; va primero.
  - `max_features` (entero; opcional, por defecto `50`): tope de funciones a intentar (cada una deja dos pasos en el timeline).
- CLI: `omnicad call rebuild_features --doc pieza.omnicad`

### `create_coil`

Crea una bobina o espiral con las opciones del comando Bobina.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `diameter` (número o expresión; opcional, por defecto `20`): diámetro de la bobina en mm o expresión.
  - `coil_type` ("revolutions_height" | "revolutions_pitch" | "height_pitch" | "spiral"; opcional, por defecto `"revolutions_height"`): revolutions_height, revolutions_pitch, height_pitch o spiral.
  - `revolutions` (número o expresión; opcional, por defecto `5`): cantidad de vueltas (número o expresión escalar).
  - `height` (número o expresión; opcional, por defecto `30`): altura axial en mm para los modos con altura.
  - `pitch` (número o expresión; opcional, por defecto `6`): paso axial o radial de la espiral en mm.
  - `angle` (número o expresión; opcional, por defecto `0`): ángulo de conicidad en grados; no se usa en espiral.
  - `section` ("circular" | "square" | "triangle_external" | "triangle_internal"; opcional, por defecto `"circular"`): circular, square, triangle_external o triangle_internal.
  - `section_size` (número o expresión; opcional, por defecto `3`): diámetro del círculo circunscrito de la sección en mm.
  - `position` ("on" | "inside" | "outside"; opcional, por defecto `"on"`): sección on (sobre), inside (dentro) u outside (fuera).
  - `clockwise` (true/false; opcional, por defecto `false`): true invierte el sentido helicoidal.
  - `rotate` (true/false; opcional, por defecto `false`): true gira 90 grados alrededor del eje Y local.
  - `plane` (texto o objeto; opcional, por defecto `"XY"`): plano XY/XZ/YZ, nombre/id de plano de construcción o selector/id de una cara plana.
  - `center` (texto o objeto; opcional, por defecto `null`): punto del centro; O, nombre/id de punto, {"sketch": nombre, "point": id} o {"body": nombre, "vertex": índice}.
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): new_body, join, cut o intersect.
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpos afectados por la booleana, por nombre o id; vacío = automático.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan selectores del plano o del centro.
- CLI: `omnicad call create_coil --doc pieza.omnicad`

### `create_pipe`

Crea una tubería maciza o hueca sobre curvas de boceto o aristas.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `path_sketch` (texto; opcional, por defecto `null`): nombre/id del boceto de ruta; se combina con aristas si se dan ambas fuentes.
  - `path_curves` (lista de entero o null; opcional, por defecto `null`): ids de curvas; vacío = todas las no constructivas; requiere path_sketch.
  - `edges` (texto o lista de texto o null; opcional, por defecto `null`): selector o ids de find_edges, o lista, como ruta adicional.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de aristas.
  - `chain` (true/false; opcional, por defecto `true`): true incluye la cadena tangente conectada a la ruta seleccionada.
  - `end` (número o expresión; opcional, por defecto `1`): fracción final de la ruta, entre 0 y 1.
  - `start` (número o expresión; opcional, por defecto `0`): fracción inicial de la ruta, entre 0 y 1, menor que end.
  - `section` ("circular" | "square" | "triangle"; opcional, por defecto `"circular"`): circular, square o triangle.
  - `section_size` (número o expresión; opcional, por defecto `5`): diámetro exterior del círculo circunscrito de la sección en mm.
  - `hollow` (true/false; opcional, por defecto `false`): true crea una sección hueca.
  - `thickness` (número o expresión; opcional, por defecto `0.5`): espesor de la pared en mm cuando hollow=true.
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): new_body, join, cut o intersect.
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpos afectados por la booleana; vacío = automático.
- CLI: `omnicad call create_pipe --doc pieza.omnicad`

### `create_rib`

Crea un nervio paralelo al plano del boceto, hasta el cuerpo o a profundidad. direction: symmetric, o un solo lado empezando abajo (side1, Start: Bottom) o arriba (side2, Start: Top). draft_angle afina el nervio hacia su borde libre; pull_direction (plano, cara o eje) es la dirección de extracción del desmoldeo (por defecto, del cuerpo hacia la curva).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): nombre/id del boceto con curvas abiertas.
  - `curves` (lista de entero o null; opcional, por defecto `null`): ids de curvas; vacío = todas las no constructivas.
  - `thickness` (número o expresión; opcional, por defecto `2`): grosor en mm.
  - `extension` ("to_next" | "depth"; opcional, por defecto `"to_next"`): to_next (hasta el siguiente cuerpo) o depth (profundidad).
  - `depth` (número o expresión; opcional, por defecto `10`): profundidad en mm con extension=depth.
  - `direction` ("symmetric" | "side1" | "side2"; opcional, por defecto `"symmetric"`): grosor symmetric, side1 (un lado, empieza abajo) o side2 (un lado, empieza arriba).
  - `reverse` (true/false; opcional, por defecto `false`): true invierte la dirección de crecimiento.
  - `target` (texto; opcional, por defecto `null`): nombre/id del cuerpo objetivo; vacío = el más cercano.
  - `draft_angle` (número o expresión; opcional, por defecto `0`): ángulo de desmoldeo en grados (entre -45 y 45; positivo = más fino en el borde libre), número o expresión.
  - `pull_direction` (texto o objeto; opcional, por defecto `null`): plano, cara o eje que da la dirección de extracción; vacío = del cuerpo hacia la curva del nervio.
- CLI: `omnicad call create_rib --doc pieza.omnicad sketch=…`

### `create_web`

Crea una red de nervios perpendicular al plano del boceto. draft_angle afina la red hacia su borde libre, fillet_radius redondea las aristas cóncavas donde se junta con el cuerpo y extend_curves=false la deja terminar donde terminan las curvas.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): nombre/id del boceto con curvas abiertas.
  - `curves` (lista de entero o null; opcional, por defecto `null`): ids de curvas; vacío = todas las no constructivas.
  - `thickness` (número o expresión; opcional, por defecto `2`): grosor en mm.
  - `extension` ("to_next" | "depth"; opcional, por defecto `"to_next"`): to_next (hasta el siguiente cuerpo) o depth (profundidad).
  - `depth` (número o expresión; opcional, por defecto `10`): profundidad en mm con extension=depth.
  - `direction` ("symmetric" | "side1" | "side2"; opcional, por defecto `"symmetric"`): grosor symmetric, side1 o side2.
  - `reverse` (true/false; opcional, por defecto `false`): true invierte la normal usada por el comando Red.
  - `target` (texto; opcional, por defecto `null`): nombre/id del cuerpo objetivo; vacío = el más cercano.
  - `draft_angle` (número o expresión; opcional, por defecto `0`): ángulo de desmoldeo en grados (entre -45 y 45; positivo = más fina en el borde libre), número o expresión.
  - `fillet_radius` (número o expresión; opcional, por defecto `0`): radio en mm del empalme entre la red y el cuerpo (0 = sin empalme), número o expresión.
  - `extend_curves` (true/false; opcional, por defecto `true`): true prolonga las curvas hasta el cuerpo; false deja la red del largo de las curvas.
- CLI: `omnicad call create_web --doc pieza.omnicad sketch=…`

### `create_emboss`

Repuja o graba perfiles en una o varias caras, con envoltura opcional.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): nombre/id del boceto de perfiles o textos.
  - `faces` (texto o lista de texto; obligatorio): selector, ids de find_faces o lista de ambos.
  - `profile` (entero o lista de entero o texto; opcional, por defecto `0`): índice, lista, all, largest, text o text:<id>, como extrude.
  - `depth` (número o expresión; opcional, por defecto `1`): profundidad firmada en mm; negativa invierte relieve/grabado.
  - `emboss_type` ("emboss" | "deboss"; opcional, por defecto `"emboss"`): emboss (relieve) o deboss (grabado).
  - `wrap` (true/false; opcional, por defecto `false`): true envuelve sobre la cara.
  - `tangent_chain` (true/false; opcional, por defecto `false`): true incluye las caras tangentes.
  - `horizontal_offset` (número o expresión; opcional, por defecto `0`): desplazamiento horizontal en mm.
  - `vertical_offset` (número o expresión; opcional, por defecto `0`): desplazamiento vertical en mm.
  - `rotation` (número o expresión; opcional, por defecto `0`): giro de los perfiles en grados.
  - `reverse` (true/false; opcional, por defecto `false`): true invierte la normal.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan selectores; vacío = el único cuerpo.
- CLI: `omnicad call create_emboss --doc pieza.omnicad sketch=… faces=…`

### `create_boss`

Crea columnas para tornillo en puntos de boceto o vértices.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `positions` (lista de texto o objeto; obligatorio): puntos O o de construcción, {"sketch": nombre, "point": id} o {"body": nombre, "vertex": índice desde 1}.
  - `outer_diameter` (número o expresión; opcional, por defecto `8`): diámetro exterior en mm.
  - `hole_diameter` (número o expresión; opcional, por defecto `3`): diámetro del agujero en mm, positivo y menor que outer_diameter.
  - `height` (número o expresión; opcional, por defecto `null`): altura en mm; vacío = hasta el cuerpo.
  - `draft_angle` (número o expresión; opcional, por defecto `0`): ángulo de desmoldeo en grados.
  - `reverse` (true/false; opcional, por defecto `false`): true invierte el sentido automático respecto al material.
- CLI: `omnicad call create_boss --doc pieza.omnicad positions=…`

### `create_lip_groove`

Crea un labio o una ranura a lo largo del borde de una pared.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `edges` (texto o lista de texto; obligatorio): selector o ids de find_edges, o lista; todas deben pertenecer al mismo cuerpo.
  - `lip_type` ("lip" | "groove"; opcional, por defecto `"lip"`): lip (labio) o groove (ranura).
  - `width` (número o expresión; opcional, por defecto `1`): ancho en mm.
  - `height` (número o expresión; opcional, por defecto `1.5`): alto en mm.
  - `clearance` (número o expresión; opcional, por defecto `0.1`): holgura en mm para groove.
  - `direction` (texto o objeto; opcional, por defecto `null`): eje X/Y/Z, plano XY/XZ/YZ, geometría de construcción o selector/id de cara plana o arista recta; vacío = Z.
  - `reverse` (true/false; opcional, por defecto `false`): true invierte la dirección de tirado.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores.
- CLI: `omnicad call create_lip_groove --doc pieza.omnicad edges=…`

### `create_boundary_fill`

Rellena celdas encerradas por cuerpos, caras y planos.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `tools` (texto o lista de texto; obligatorio): nombres/ids de cuerpos o planos, XY/XZ/YZ y selectores/ids de caras, solos o en lista.
  - `cells` (lista de entero o null; opcional, por defecto `null`): números de celda desde 1, ordenadas por centroide XYZ como el diálogo; vacío = celda 1.
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): new_body, join, cut o intersect.
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpos afectados por la booleana; vacío = automático.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan selectores de caras.
- CLI: `omnicad call create_boundary_fill --doc pieza.omnicad tools=…`

### `create_volumetric_lattice`

Llena un sólido o una malla cerrada con una estructura interna por celdas (SÓLIDO › MODIFICAR › Retícula volumétrica). cell_shape: cross (tres barras por celda), x_cell (las cuatro diagonales), x_cell_25d (las diagonales en XY como paredes extruidas en Z) y custom (barras a medida, custom_bars) quedan como sólido; gyroid, schwarz_p y schwarz_d (superficies mínimas) quedan como cuerpo de malla (resolution muestras por celda; el borde del cuerpo sale interpolado). solidity es el porcentaje de material; con solidity_end y gradient_path varía a lo largo de la ruta. offset_distance/offset_blend arman la zona de desfase (otra solidez cerca de caras, aristas o puntos). cell_offset y cell_rotation mueven y giran las celdas. El cuerpo queda reemplazado por la retícula (deshacer lo devuelve).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo sólido o de la malla cerrada; vacío = el único cuerpo.
  - `cell_shape` ("cross" | "x_cell" | "x_cell_25d" | "custom" | "gyroid" | "schwarz_p" | "schwarz_d"; opcional, por defecto `"gyroid"`): cross, x_cell, x_cell_25d, custom, gyroid, schwarz_p o schwarz_d.
  - `cell_size` (número o expresión; opcional, por defecto `5`): tamaño de la celda en mm (en X, y en Y y Z si no se dan).
  - `cell_size_y` (número o expresión; opcional, por defecto `null`): tamaño en Y, en mm, para celdas no uniformes; vacío = cell_size.
  - `cell_size_z` (número o expresión; opcional, por defecto `null`): tamaño en Z, en mm, para celdas no uniformes; vacío = cell_size.
  - `solidity` (número o expresión; opcional, por defecto `30`): porcentaje de material, de 1 a 99 (al principio de la ruta si hay gradiente).
  - `resolution` (entero; opcional, por defecto `8`): gyroid, schwarz_p y schwarz_d: muestras por celda (mínimo 4, por defecto 8); más es más fino y más lento.
  - `custom_bars` (lista de lista de número o null; opcional, por defecto `null`): celda custom: barras [x1, y1, z1, x2, y2, z2] en fracciones de la celda (0 a 1).
  - `solidity_end` (número o expresión; opcional, por defecto `null`): solidez al final de la ruta (1 a 99); vacío = solidez uniforme.
  - `gradient_path` (lista de texto o objeto o null; opcional, por defecto `null`): ruta del gradiente: una arista o curva de boceto, o dos o más puntos o vértices (en orden).
  - `offset_distance` (número o expresión; opcional, por defecto `0`): ancho en mm de la zona de desfase alrededor de offset_zones; 0 = sin zona.
  - `offset_solidity` (número o expresión; opcional, por defecto `100`): solidez de la zona de desfase, de 0 a 100 (100 = macizo con superficies mínimas, 0 = sin retícula).
  - `offset_blend` (número o expresión; opcional, por defecto `0`): distancia de mezcla en mm entre la zona de desfase y el resto.
  - `offset_zones` (lista de texto o objeto o null; opcional, por defecto `null`): caras, aristas, puntos o cuerpos de la zona; vacío = todas las caras del cuerpo.
  - `cell_offset` (lista de número o null; opcional, por defecto `null`): [dx, dy, dz] en mm: mueve las celdas.
  - `cell_rotation` (lista de número o null; opcional, por defecto `null`): [rx, ry, rz] en grados: gira las celdas (primero en X, después Y, después Z).
- CLI: `omnicad call create_volumetric_lattice --doc pieza.omnicad`

### `create_geometric_pattern`

Reparte esferas, cilindros, cajas u objetos a medida sobre caras planas con un gradiente de tamaño (PLÁSTICO › CREAR › Patrón geométrico). El tamaño va de size1 (en el centro del patrón) a size2 (en la esquina de la caja de la cara) con la curva de spread. Distribuciones: rectangular, triangular (filas desfasadas), hexagonal (panal), circular (anillos) y radial (rayos). clear_perimeter descarta los objetos que se salen de la cara u ocupan el borde. Con operation=cut o intersect los cilindros y cajas entran en el material; con join o new_body salen de la cara. Máximo 2000 objetos.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `faces` (texto o lista de texto; obligatorio): caras planas donde va el patrón (selector, ids de find_faces o lista).
  - `object_type` ("sphere" | "cylinder" | "box" | "custom"; opcional, por defecto `"sphere"`): sphere (size = diámetro), cylinder (diámetro y altura = size), box (lado = size) o custom (custom_body; size = su mayor dimensión).
  - `size1` (número o expresión; opcional, por defecto `2`): tamaño en el centro del patrón, en mm.
  - `size2` (número o expresión; opcional, por defecto `4`): tamaño en la esquina de la caja de la cara, en mm.
  - `spread` (número o expresión; opcional, por defecto `1`): exponente de la transición entre size1 y size2 (1 = lineal; mayor, los objetos grandes llegan más tarde).
  - `distribution` ("rectangular" | "triangular" | "hexagonal" | "circular" | "radial"; opcional, por defecto `"rectangular"`): rectangular, triangular, hexagonal, circular o radial.
  - `spacing_type` ("increment" | "extent"; opcional, por defecto `"increment"`): rectangular: increment (cada distance) o extent (quantity_u × quantity_v repartidos de borde a borde).
  - `distance` (número o expresión; opcional, por defecto `6`): separación entre objetos vecinos, en mm (rectangular, triangular y hexagonal).
  - `quantity_u` (entero; opcional, por defecto `5`): con extent, objetos a lo largo de U.
  - `quantity_v` (entero; opcional, por defecto `5`): con extent, objetos a lo largo de V (rectangular).
  - `radial_distance` (número o expresión; opcional, por defecto `6`): circular y radial: separación entre anillos u objetos de un rayo, en mm.
  - `spokes` (entero; opcional, por defecto `8`): radial: cantidad de rayos.
  - `orientation` ("parallel" | "face"; opcional, por defecto `"face"`): face (los objetos siguen los ejes U y V de la cara) o parallel (sin rotación, ejes del modelo).
  - `u_alignment` ("left" | "center" | "right"; opcional, por defecto `"center"`): left, center o right: dónde se apoya la rejilla respecto de U.
  - `u_offset` (número o expresión; opcional, por defecto `0`): desfase en U desde el borde (o desde el centro), en mm.
  - `v_alignment` ("bottom" | "middle" | "top"; opcional, por defecto `"middle"`): bottom, middle o top.
  - `v_offset` (número o expresión; opcional, por defecto `0`): desfase en V, en mm.
  - `clear_perimeter` (true/false; opcional, por defecto `true`): true quita los objetos que no entran enteros en la cara.
  - `perimeter_offset` (número o expresión; opcional, por defecto `0`): distancia mínima al borde de la cara, en mm.
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"cut"`): new_body, join, cut o intersect.
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpos afectados; vacío = automático.
  - `custom_body` (texto; opcional, por defecto `null`): con object_type=custom, el cuerpo que se repite.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de caras.
- CLI: `omnicad call create_geometric_pattern --doc pieza.omnicad faces=…`

### `create_bounding_solid`

Crea una caja, un cilindro o un tubo envolvente de los cuerpos elegidos (SÓLIDO › CREAR › Sólido envolvente). orientation: model (ejes del modelo), automatic (la menor), z_x / z_y / x_y (dos ejes dados en axis_a y axis_b; el primero manda) o ucs (un sistema de coordenadas de usuario). Con component=true queda en un componente nuevo, como en Fusion, y rigid_group=true lo liga a los componentes de los cuerpos envueltos.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): nombres/ids de los cuerpos a envolver.
  - `shape` ("box" | "cylinder" | "tube"; opcional, por defecto `"box"`): box (caja), cylinder (cilindro) o tube (cilindro hueco).
  - `axis` ("x" | "y" | "z"; opcional, por defecto `"z"`): eje del cilindro o tubo x, y o z cuando orientation=model.
  - `margin` (número o expresión; opcional, por defecto `0`): desfase de la envolvente en mm.
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): new_body, join, cut o intersect.
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpos afectados por la booleana; vacío = automático.
  - `orientation` ("model" | "automatic" | "z_x" | "z_y" | "x_y" | "ucs"; opcional, por defecto `"model"`): model, automatic, z_x, z_y, x_y o ucs; con z_x, z_y y x_y hacen falta axis_a y axis_b.
  - `axis_a` (texto o objeto; opcional, por defecto `null`): primer eje de la orientación (eje de construcción, arista recta o línea de boceto; selector o id).
  - `axis_b` (texto o objeto; opcional, por defecto `null`): segundo eje de la orientación; se ortogonaliza respecto del primero.
  - `ucs` (texto; opcional, por defecto `null`): id o nombre del sistema de coordenadas de usuario cuando orientation=ucs.
  - `tube_wall` (número o expresión; opcional, por defecto `null`): espesor de pared del tubo en mm (número o expresión); vacío = la décima parte del radio.
  - `component` (true/false; opcional, por defecto `false`): true deja el sólido en un componente nuevo.
  - `rigid_group` (true/false; opcional, por defecto `false`): true liga el sólido a los componentes de los cuerpos envueltos (solo vale si los cuerpos están en componentes).
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de los ejes.
  - `origin` ("model" | "center" | "corner"; opcional, por defecto `"model"`): dónde queda el origen del componente (Origin Mode): model (el del documento), center (centro del sólido) o corner (su esquina mínima); solo con component=true o rigid_group=true; get_assembly lo informa.
- CLI: `omnicad call create_bounding_solid --doc pieza.omnicad bodies=…`

### `create_fluid_volume`

Crea el volumen de fluido de un diseño (SÓLIDO › CREAR › Volumen de fluido): el sólido del interior (internal, que copia las caras del modelo) o del exterior (external, una caja, cilindro o semiesfera que rodea el modelo menos el modelo). Las aberturas del modelo se tapan con cuerpos de superficie (caps); sin tapas el interior no queda cerrado y falla. split_faces deja una cara por superficie del modelo (Split Result). El resultado queda en un componente nuevo.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): nombres/ids de los cuerpos sólidos del diseño.
  - `volume_type` ("internal" | "external"; opcional, por defecto `"internal"`): internal (interior del modelo) o external (el aire alrededor).
  - `caps` (texto o lista de texto o null; opcional, por defecto `null`): cuerpos de superficie que cubren las aberturas; vacío = ninguno.
  - `outer_shape` ("box" | "cylinder" | "hemisphere"; opcional, por defecto `"box"`): forma que rodea al modelo con volume_type=external: box, cylinder (eje Z) o hemisphere (mitad superior).
  - `margin` (número o expresión; opcional, por defecto `10`): distancia en mm entre el modelo y la forma exterior (número o expresión); no cuenta en el interno.
  - `split_faces` (true/false; opcional, por defecto `false`): true deja una cara por cada superficie del modelo (Split Result); false funde las caras tangentes.
- CLI: `omnicad call create_fluid_volume --doc pieza.omnicad bodies=…`

### `thicken`

Da espesor a caras o cuerpos de superficie y crea un sólido.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `faces` (texto o lista de texto; obligatorio): selector/ids de caras o nombres/ids de cuerpos de superficie, solos o en lista.
  - `thickness` (número o expresión; opcional, por defecto `2`): grosor firmado en mm; negativo invierte el lado.
  - `direction` ("one_side" | "symmetric"; opcional, por defecto `"one_side"`): one_side (un lado) o symmetric (mitad a cada lado).
  - `thicken_type` ("sharp" | "rounded"; opcional, por defecto `"sharp"`): sharp (afilado) o rounded (redondeado).
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): new_body, join, cut o intersect.
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpos afectados por la booleana; vacío = automático.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan selectores de caras.
- CLI: `omnicad call thicken --doc pieza.omnicad faces=…`

### `align_bodies`

Alinea puntos, planos enfrentados o ejes de los cuerpos, con copia opcional.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): nombres/ids de los cuerpos a mover o copiar.
  - `source` (texto o objeto; obligatorio): plano/eje/punto de origen, nombre/id de construcción, selector/id de cara o arista; {"sketch": nombre, "point": id} o {"body": nombre, "vertex": índice}.
  - `destination` (texto o objeto; obligatorio): geometría de destino, con el mismo formato que source.
  - `flip` (true/false; opcional, por defecto `false`): true voltea 180 grados la alineación.
  - `copy` (true/false; opcional, por defecto `false`): true crea copias; false mueve los originales.
  - `source_body` (texto; opcional, por defecto `null`): cuerpo donde se evalúa el selector de source.
  - `destination_body` (texto; opcional, por defecto `null`): cuerpo donde se evalúa el selector de destination.
- CLI: `omnicad call align_bodies --doc pieza.omnicad bodies=… source=… destination=…`

### `move_faces`

Mueve o copia caras planas de un cuerpo (SÓLIDO › MODIFICAR › Mover/copiar › Caras): las caras vecinas se extienden o se recortan para seguirlas. type=translate con direction (eje, arista recta, cara plana o plano) y distance, o con translate [dx, dy, dz]; type=rotate alrededor de axis un angle. Con copy=true el cuerpo no cambia y cada cara movida queda como un cuerpo de superficie nuevo. Mover caras que no son planas todavía no está.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `faces` (texto o lista de texto; obligatorio): caras a mover: selector, ids de find_faces o lista de ambos.
  - `type` ("translate" | "rotate"; opcional, por defecto `"translate"`): "translate" o "rotate".
  - `translate` (lista de número o expresión o null; opcional, por defecto `null`): con type=translate y sin direction: desplazamiento [dx, dy, dz] en mm (números o expresiones).
  - `direction` (texto o objeto; opcional, por defecto `null`): con type=translate: eje de construcción, arista recta, cara plana o plano; se mueve distance a lo largo de él.
  - `distance` (número o expresión; opcional, por defecto `10`): con direction: desplazamiento en mm (número o expresión).
  - `axis` (texto o objeto; opcional, por defecto `null`): con type=rotate: eje de construcción (id o nombre), arista recta o línea de boceto {"sketch", "curve"}.
  - `angle` (número o expresión; opcional, por defecto `90`): con type=rotate: ángulo en grados (número o expresión).
  - `copy` (true/false; opcional, por defecto `false`): true deja el cuerpo como está y crea una superficie con cada cara movida.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
- CLI: `omnicad call move_faces --doc pieza.omnicad faces=…`

### `scale_body`

Escala sólidos o componentes (con todos sus cuerpos) respecto de un punto, uniforme o con un factor por eje. sketches escala bocetos enteros (solo uniforme).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto o null; opcional, por defecto `null`): nombres/ids de los sólidos a escalar; un componente (id o nombre) escala todos sus cuerpos. Vacío si solo se escalan bocetos.
  - `factor` (número o expresión; opcional, por defecto `1`): factor escalar uniforme, número o expresión.
  - `scale_type` ("uniform" | "non_uniform"; opcional, por defecto `"uniform"`): uniform o non_uniform.
  - `factor_x` (número o expresión; opcional, por defecto `1`): factor del eje X para non_uniform.
  - `factor_y` (número o expresión; opcional, por defecto `1`): factor del eje Y para non_uniform.
  - `factor_z` (número o expresión; opcional, por defecto `1`): factor del eje Z para non_uniform.
  - `point` (texto o objeto; opcional, por defecto `null`): punto base O o de construcción, {"sketch": nombre, "point": id} o {"body": nombre, "vertex": índice}; vacío = origen.
  - `sketches` (lista de texto o null; opcional, por defecto `null`): bocetos enteros a escalar (id o nombre), solo uniform.
- CLI: `omnicad call scale_body --doc pieza.omnicad`

### `create_surface_extrude`

Extruye curvas abiertas o cerradas en una superficie.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `profiles` (texto o objeto o lista de texto o objeto; obligatorio): curvas {"sketch": "Boceto1", "curve": [1, 2]}, perfiles {"sketch": "Boceto1", "profile": 0}, caras, aristas o cuerpos; admite listas, ids y selectores.
  - `distance` (número o expresión; opcional, por defecto `"10 mm"`): distancia en mm o expresión; negativa invierte el sentido.
  - `direction` (texto o objeto; opcional, por defecto `null`): eje, plano, cara plana o arista lineal; vacío = normal del boceto (o Z).
  - `symmetric` (true/false; opcional, por defecto `false`): reparte la distancia total a ambos lados.
  - `taper_angle` (número o expresión; opcional, por defecto `0`): ángulo de conicidad en grados o expresión.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que evaluar selectores sin cuerpo explícito.
- CLI: `omnicad call create_surface_extrude --doc pieza.omnicad profiles=…`

### `create_surface_revolve`

Gira curvas alrededor de un eje para crear una superficie.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `profiles` (texto o objeto o lista de texto o objeto; obligatorio): curvas o perfiles de boceto ({"sketch": "Boceto1", "curve": 1} o "profile": 0), caras, aristas o cuerpos; admite listas, ids y selectores.
  - `axis` (texto o objeto; obligatorio): eje X, Y, Z, eje de construcción o referencia a una línea de boceto/arista lineal.
  - `angle` (número o expresión; opcional, por defecto `"360 deg"`): ángulo en grados o expresión.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que evaluar selectores.
- CLI: `omnicad call create_surface_revolve --doc pieza.omnicad profiles=… axis=…`

### `create_surface_sweep`

Barre curvas por una ruta con orientación, torsión y distancia sobre la ruta.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `profiles` (texto o objeto o lista de texto o objeto; obligatorio): curvas o perfiles {"sketch": "Boceto1", "curve": 1} o {"sketch": "Boceto1", "profile": 0}; también caras, aristas o cuerpos.
  - `path` (texto o objeto o lista de texto o objeto; obligatorio): cadena de curvas de boceto, aristas (ids o selectores), caras o cuerpos.
  - `orientation` ("perpendicular" | "parallel"; opcional, por defecto `"perpendicular"`): perpendicular sigue la ruta; parallel mantiene la orientación.
  - `twist_angle` (número o expresión; opcional, por defecto `0`): torsión total en grados o expresión; solo con orientación perpendicular.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que evaluar selectores.
  - `path_distance` (número o expresión; opcional, por defecto `1`): hasta dónde llega el barrido sobre la ruta, fracción de 0 (sin incluir) a 1 (toda la ruta).
- CLI: `omnicad call create_surface_sweep --doc pieza.omnicad profiles=… path=…`

### `create_surface_loft`

Crea una superficie entre secciones ordenadas, abiertas o cerradas.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `profiles` (lista de texto o objeto; obligatorio): secciones ordenadas: curvas o perfiles {"sketch": "Boceto1", "profile": 0}, caras, aristas, cuerpos o puntos de boceto {"sketch": "Boceto1", "point": 1}.
  - `closed` (true/false; opcional, por defecto `false`): une la última sección con la primera.
  - `ruled` (true/false; opcional, por defecto `false`): usa tramos rectos entre secciones.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que evaluar selectores.
- CLI: `omnicad call create_surface_loft --doc pieza.omnicad profiles=…`

### `offset_surface`

Crea una superficie paralela a caras o cuerpos.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `faces` (texto o objeto o lista de texto o objeto; obligatorio): caras (ids o selectores) o cuerpos por id, nombre o {"body": "Cuerpo1"}; admite listas.
  - `distance` (número o expresión; opcional, por defecto `"2 mm"`): desfase en mm o expresión; admite valores negativos.
  - `offset_type` ("sharp" | "rounded"; opcional, por defecto `"sharp"`): sharp para esquinas agudas; rounded para redondeadas.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que evaluar selectores.
- CLI: `omnicad call offset_surface --doc pieza.omnicad faces=…`

### `fillet_surface`

Redondea o bisela aristas entre superficies.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `edges` (texto o objeto o lista de texto o objeto; obligatorio): aristas por id o selector; admite listas y {"body": "Cuerpo1", "edges": "|Z"}.
  - `size` (número o expresión; opcional, por defecto `"1 mm"`): radio del empalme o distancia del chaflán en mm o expresión.
  - `fillet_type` ("fillet" | "chamfer"; opcional, por defecto `"fillet"`): fillet (empalme) o chamfer (chaflán).
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que evaluar selectores.
- CLI: `omnicad call fillet_surface --doc pieza.omnicad edges=…`

### `create_patch`

Tapa un contorno cerrado con continuidad G0, G1 o G2.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `boundary` (texto o objeto o lista de texto o objeto; obligatorio): curvas o perfiles {"sketch": "Boceto1", "profile": 0}, aristas, caras o cuerpos; admite listas, ids y selectores.
  - `continuity` ("G0" | "G1" | "G2"; opcional, por defecto `"G0"`): G0 conexión, G1 tangencia o G2 curvatura; G1/G2 necesitan caras de soporte.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que evaluar selectores.
- CLI: `omnicad call create_patch --doc pieza.omnicad boundary=…`

### `create_ruled_surface`

Crea superficies rectas desde aristas, con dirección y ángulo.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `edges` (texto o objeto o lista de texto o objeto; obligatorio): curvas o perfiles de boceto, aristas, caras o cuerpos; admite listas, ids y selectores.
  - `distance` (número o expresión; opcional, por defecto `"10 mm"`): largo en mm o expresión.
  - `surface_type` ("normal" | "tangent" | "direction"; opcional, por defecto `"normal"`): normal, tangent o direction.
  - `direction` (texto o objeto; opcional, por defecto `null`): eje, plano, cara plana o arista lineal; obligatorio con surface_type=direction.
  - `angle` (número o expresión; opcional, por defecto `0`): giro de la dirección en grados o expresión.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que evaluar selectores.
- CLI: `omnicad call create_ruled_surface --doc pieza.omnicad edges=…`

### `extend_surface`

Alarga bordes libres de superficies.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `edges` (texto o objeto o lista de texto o objeto; obligatorio): bordes libres por id o selector; admite listas y {"body": "Cuerpo1", "edges": ">X"}.
  - `distance` (número o expresión; opcional, por defecto `"5 mm"`): extensión en mm o expresión.
  - `extension_type` ("natural" | "tangent" | "perpendicular"; opcional, por defecto `"natural"`): natural, tangent o perpendicular.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que evaluar selectores.
- CLI: `omnicad call extend_surface --doc pieza.omnicad edges=…`

### `trim_surface`

Recorta una superficie y quita la región indicada por un punto.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `surface` (texto; obligatorio): id o nombre del cuerpo de superficie que se recorta.
  - `tool` (texto o objeto; obligatorio): plano, cara, cuerpo o curva de boceto {"sketch": "Boceto1", "curve": 1} que corta la superficie.
  - `remove_point` (lista de número; obligatorio): punto [x, y, z] en mm sobre la región que se quita.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que evaluar el selector de tool.
- CLI: `omnicad call trim_surface --doc pieza.omnicad surface=… tool=… remove_point=…`

### `untrim_surface`

Restaura límites naturales de caras recortadas.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `faces` (texto o objeto o lista de texto o objeto; obligatorio): caras por id o selector; admite listas y {"body": "Cuerpo1", "faces": "all"}.
  - `boundaries` ("outer" | "inner" | "all"; opcional, por defecto `"outer"`): outer exteriores, inner interiores o all todos los contornos.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que evaluar selectores.
- CLI: `omnicad call untrim_surface --doc pieza.omnicad faces=…`

### `stitch_surfaces`

Cose superficies; un cierre completo produce un sólido.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): ids o nombres de los cuerpos que se cosen; se conserva el primero y se consumen los demás.
  - `tolerance` (número o expresión; opcional, por defecto `"0.01 mm"`): tolerancia de costura en mm o expresión.
- CLI: `omnicad call stitch_surfaces --doc pieza.omnicad bodies=…`

### `unstitch_surfaces`

Separa cada cara en un cuerpo de superficie independiente.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): ids o nombres de cuerpos; cada cara pasa a ser un cuerpo nuevo.
- CLI: `omnicad call unstitch_surfaces --doc pieza.omnicad bodies=…`

### `reverse_surface_normal`

Invierte la orientación de cuerpos de superficie.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): ids o nombres de superficies cuya normal se invierte.
- CLI: `omnicad call reverse_surface_normal --doc pieza.omnicad bodies=…`

## Grupo chapa

Chapa metálica: reglas, pestañas, dobladillo, plegar, desplegar, desgarro, patrón plano y DXF.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`list_sheet_metal_rules`](#list_sheet_metal_rules) | no | Reglas de chapa disponibles con todos sus valores (espesor, radio de plegado, factor K, alivios, separación y material): las de fábrica (builtin), las propias del usuario (user) y las propias copiadas en este documento (document), y qué pasos usa cada una. |
| [`create_sheet_metal_rule`](#create_sheet_metal_rule) | no | Crea una regla de chapa propia (Reglas de chapa › Nueva regla): espesor, factor K, radio de plegado, material y, si hace falta, alivios y separación; lo que no se da sigue al espesor como en las de fábrica (radio = t, alivio t × t/2, esquina 4·t, separación t). |
| [`delete_sheet_metal_rule`](#delete_sheet_metal_rule) | no | Borra una regla propia de la biblioteca del usuario (las de fábrica no se borran). |
| [`get_sheet_metal_info`](#get_sheet_metal_info) | no | Cuerpos de chapa (y patrones planos) con su regla (espesor, radio, K, material), el paso que la define, cantidad de pliegues y desplegados, y el tamaño (ancho × alto, mm) y el área del patrón plano. |
| [`create_base_flange`](#create_base_flange) | sí | Pestaña base (CHAPA › Pestaña, tipo base): convierte perfiles cerrados de un boceto en una placa de chapa con la regla elegida (crea un cuerpo de chapa nuevo por perfil). side: side1 (el espesor hacia la normal del boceto), side2 (hacia el otro lado) o center. thickness, bend_radius y k_factor anulan la regla (vacío = el de la regla; aceptan número o expresión). |
| [`create_contour_flange`](#create_contour_flange) | sí | Pestaña de contorno (CHAPA › Pestaña de contorno): un perfil ABIERTO de líneas y arcos de un boceto se extruye como chapa plegada, con el radio de la regla en cada esquina viva. direction: one_side (distance hacia la normal del boceto), two_sides (distance y distance2) o symmetric. side: de qué lado del perfil queda el espesor. thickness, bend_radius y k_factor anulan la regla (vacío = el de la regla; aceptan número o expresión). |
| [`create_edge_flange`](#create_edge_flange) | sí | Pestaña de arista (CHAPA › Pestaña en aristas de chapa): levanta una pestaña con pliegue en cada arista recta del borde de la cara de arriba o de abajo de la chapa; las aristas se elige con un selector (evaluado sobre body) o un id de find_faces / find_edges. height_reference: outer (altura hasta las caras exteriores), inner o tangent (hasta donde termina el pliegue). bend_position: inside (la pestaña queda dentro del contorno), outside, adjacent o tangent. width: full (toda la arista), symmetric (width_distance centrado) o two_sides (width1 y width2 desde los extremos). bend_radius y los alivios anulan la regla. |
| [`create_hem`](#create_hem) | sí | Dobladillo (CHAPA › Dobladillo): dobla el borde de la chapa sobre sí mismo en las aristas rectas elegidas; las aristas se elige con un selector (evaluado sobre body) o un id de find_faces / find_edges. hem_type: closed (plano, sin separación), open (con separación gap) o teardrop (lágrima, con radio). position: adjacent (el pliegue fuera del borde) o tangent. |
| [`fold`](#fold) | sí | Plegar (CHAPA › Plegar): pliega la chapa por líneas rectas de un boceto dibujado sobre la cara (create_sketch con plane = la cara). face es la cara estacionaria (se elige con un selector (evaluado sobre body) o un id de find_faces / find_edges.); fixed_point dice qué lado de la línea queda quieto (un punto [x, y, z] sobre la cara; vacío = un punto de la cara). line_position: start, center o end (dónde cae la línea respecto del pliegue). |
| [`unfold`](#unfold) | sí | Desplegar (CHAPA › Desplegar): endereza pliegues de la chapa, todos o los elegidos (caras curvas de los pliegues), con la cara estacionaria quieta. |
| [`refold`](#refold) | sí | Volver a plegar (CHAPA › Volver a plegar): vuelve a plegar los pliegues desplegados del cuerpo. face (opcional) es la cara que queda quieta; sin ella, la misma que al desplegar. |
| [`create_flat_pattern`](#create_flat_pattern) | sí | Crear patrón plano (CHAPA › Crear patrón plano): cuerpo nuevo con la pieza desplegada (desarrollo exacto con el factor K) sobre la cara estacionaria (in_place) o al lado de la pieza sin tocar otros cuerpos (beside). |
| [`convert_to_sheet_metal`](#convert_to_sheet_metal) | sí | Convertir a chapa (CHAPA › Convertir a chapa): una placa plana de espesor constante (p. ej. una caja delgada) pasa a ser de chapa; el espesor se mide desde la cara elegida y reemplaza al de la regla, que aporta radio, K, alivios y material. |
| [`rip`](#rip) | sí | Desgarro (CHAPA › Desgarro): mode=face quita la cara elegida (un pliegue —cara curva— o una parte plana); mode=points corta una ranura de ancho gap entre dos puntos del borde de la cara elegida (vértices [x, y, z] de la chapa, puntos de un boceto {"sketch", "point"} o puntos de construcción por id o nombre), del lado side. |
| [`join_by_bend`](#join_by_bend) | sí | Unir plegando (CHAPA › Unir plegando): une dos cuerpos de chapa del MISMO espesor con un pliegue entre dos aristas rectas paralelas (una de cada cuerpo, del borde de la cara de arriba o de abajo); quedan en un solo cuerpo. |
| [`set_sheet_metal_rule`](#set_sheet_metal_rule) | sí | Cambia la regla de un cuerpo de chapa (CHAPA › Reglas de chapa): otra regla de la biblioteca y/o valores que la anulan (espesor, radio, K, alivios, separación). |
| [`export_flat_pattern_dxf`](#export_flat_pattern_dxf) | no | Exporta el patrón plano de un cuerpo de chapa (o de su patrón plano) a DXF en mm para corte láser o plegadora (CHAPA › Exportar DXF del patrón plano): capas CONTORNO_EXTERIOR, CONTORNOS_INTERIORES, LINEAS_PLIEGUE (centros de pliegue) y EXTENSION_PLIEGUE (límites de cada pliegue). |
| [`set_flat_pattern_view`](#set_flat_pattern_view) | sí | Activa solo el desarrollo de chapa o vuelve al modelo plegado. |

### `list_sheet_metal_rules`

Reglas de chapa disponibles con todos sus valores (espesor, radio de plegado, factor K, alivios, separación y material): las de fábrica (builtin), las propias del usuario (user) y las propias copiadas en este documento (document), y qué pasos usa cada una.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call list_sheet_metal_rules --doc pieza.omnicad`

### `create_sheet_metal_rule`

Crea una regla de chapa propia (Reglas de chapa › Nueva regla): espesor, factor K, radio de plegado, material y, si hace falta, alivios y separación; lo que no se da sigue al espesor como en las de fábrica (radio = t, alivio t × t/2, esquina 4·t, separación t). Queda en la biblioteca del usuario (save=true) para todos los documentos; los pasos que la usan guardan una copia en la receta. No pisa las de fábrica. No cambia el documento.

- Modifica el documento: no.
- Parámetros:
  - `name` (texto; obligatorio): nombre de la regla (p. ej. "Latón 0.8 mm").
  - `thickness` (número; obligatorio): espesor de la chapa en mm.
  - `k_factor` (número; opcional, por defecto `0.44`): factor K de 0 a 1 (posición de la fibra neutra); 0,44 por defecto.
  - `bend_radius` (número; opcional, por defecto `null`): radio interior de plegado en mm; vacío = igual al espesor.
  - `material` (texto; opcional, por defecto `null`): material físico de la chapa (list_materials); vacío = sin material.
  - `relief_shape` ("round" | "straight" | "tear" o null; opcional, por defecto `null`): alivio de plegado: "round", "straight" o "tear"; vacío = round.
  - `relief_width` (número; opcional, por defecto `null`): ancho del alivio de plegado en mm; vacío = el espesor.
  - `relief_depth` (número; opcional, por defecto `null`): profundidad del alivio en mm; vacío = la mitad del espesor.
  - `corner_relief` ("trim" | "round" | "square" | "tear" o null; opcional, por defecto `null`): alivio de esquina entre dos pliegues: "trim", "round", "square" o "tear"; vacío = trim.
  - `corner_size` (número; opcional, por defecto `null`): tamaño del alivio de esquina en mm; vacío = 4 × espesor.
  - `gap` (número; opcional, por defecto `null`): separación de desgarros y esquinas en mm; vacío = el espesor.
  - `overwrite` (true/false; opcional, por defecto `false`): true para reemplazar una regla propia que ya existe con ese nombre.
  - `save` (true/false; opcional, por defecto `true`): true la guarda en la biblioteca del usuario para las próximas sesiones; false, solo en esta sesión.
- CLI: `omnicad call create_sheet_metal_rule --doc pieza.omnicad name=… thickness=…`

### `delete_sheet_metal_rule`

Borra una regla propia de la biblioteca del usuario (las de fábrica no se borran). Los pasos que ya la usan siguen igual: tienen la regla copiada en la receta.

- Modifica el documento: no.
- Parámetros:
  - `name` (texto; obligatorio): nombre de la regla propia.
  - `save` (true/false; opcional, por defecto `true`): true también la saca del archivo de la biblioteca; false, solo de esta sesión.
- CLI: `omnicad call delete_sheet_metal_rule --doc pieza.omnicad name=…`

### `get_sheet_metal_info`

Cuerpos de chapa (y patrones planos) con su regla (espesor, radio, K, material), el paso que la define, cantidad de pliegues y desplegados, y el tamaño (ancho × alto, mm) y el área del patrón plano. Sirve para verificar el desarrollo antes de exportar el DXF.

- Modifica el documento: no.
- Parámetros:
  - `body` (texto; opcional, por defecto `null`): id o nombre de un cuerpo de chapa o de un patrón plano; vacío = todos.
- CLI: `omnicad call get_sheet_metal_info --doc pieza.omnicad`

### `create_base_flange`

Pestaña base (CHAPA › Pestaña, tipo base): convierte perfiles cerrados de un boceto en una placa de chapa con la regla elegida (crea un cuerpo de chapa nuevo por perfil). side: side1 (el espesor hacia la normal del boceto), side2 (hacia el otro lado) o center. thickness, bend_radius y k_factor anulan la regla (vacío = el de la regla; aceptan número o expresión).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): id o nombre del boceto.
  - `profile` (entero o lista de entero o texto; opcional, por defecto `0`): perfil(es): índice (get_sketch los lista), lista de índices, "all", "largest" o "text" (las letras de los textos).
  - `rule` (texto; opcional, por defecto `null`): regla de chapa (list_sheet_metal_rules); vacío = "Acero 1 mm".
  - `side` ("side1" | "side2" | "center"; opcional, por defecto `"side1"`): "side1", "side2" o "center".
  - `thickness` (número o expresión; opcional, por defecto `null`): espesor en mm que anula el de la regla (número o expresión).
  - `bend_radius` (número o expresión; opcional, por defecto `null`): radio de plegado en mm que anula el de la regla.
  - `k_factor` (número o expresión; opcional, por defecto `null`): factor K que anula el de la regla (0 a 1).
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Pestaña<n>».
- CLI: `omnicad call create_base_flange --doc pieza.omnicad sketch=…`

### `create_contour_flange`

Pestaña de contorno (CHAPA › Pestaña de contorno): un perfil ABIERTO de líneas y arcos de un boceto se extruye como chapa plegada, con el radio de la regla en cada esquina viva. direction: one_side (distance hacia la normal del boceto), two_sides (distance y distance2) o symmetric. side: de qué lado del perfil queda el espesor. thickness, bend_radius y k_factor anulan la regla (vacío = el de la regla; aceptan número o expresión).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): id o nombre del boceto con el perfil abierto.
  - `curves` (lista de entero o null; opcional, por defecto `null`): ids de las curvas del perfil (get_sketch), en cadena abierta; vacío = todas las no de construcción.
  - `distance` (número o expresión; opcional, por defecto `20`): largo de la extrusión en mm (número o expresión).
  - `rule` (texto; opcional, por defecto `null`): regla de chapa (list_sheet_metal_rules); vacío = "Acero 1 mm".
  - `side` ("side1" | "side2" | "center"; opcional, por defecto `"side1"`): "side1", "side2" o "center".
  - `direction` ("one_side" | "two_sides" | "symmetric"; opcional, por defecto `"one_side"`): "one_side", "two_sides" o "symmetric".
  - `distance2` (número o expresión; opcional, por defecto `null`): largo del segundo lado con direction="two_sides"; vacío = 10 mm.
  - `thickness` (número o expresión; opcional, por defecto `null`): espesor en mm que anula el de la regla.
  - `bend_radius` (número o expresión; opcional, por defecto `null`): radio de plegado en mm que anula el de la regla.
  - `k_factor` (número o expresión; opcional, por defecto `null`): factor K que anula el de la regla (0 a 1).
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Pestaña<n>».
- CLI: `omnicad call create_contour_flange --doc pieza.omnicad sketch=…`

### `create_edge_flange`

Pestaña de arista (CHAPA › Pestaña en aristas de chapa): levanta una pestaña con pliegue en cada arista recta del borde de la cara de arriba o de abajo de la chapa; las aristas se elige con un selector (evaluado sobre body) o un id de find_faces / find_edges. height_reference: outer (altura hasta las caras exteriores), inner o tangent (hasta donde termina el pliegue). bend_position: inside (la pestaña queda dentro del contorno), outside, adjacent o tangent. width: full (toda la arista), symmetric (width_distance centrado) o two_sides (width1 y width2 desde los extremos). bend_radius y los alivios anulan la regla.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `edges` (texto o lista de texto; obligatorio): aristas rectas de la chapa: selector (p. ej. ">Y and >Z" = la de arriba del lado +Y), id de find_edges o lista.
  - `height` (número o expresión; opcional, por defecto `20`): altura de la pestaña en mm (número o expresión).
  - `angle` (número o expresión; opcional, por defecto `90`): ángulo de plegado en grados (90 = a escuadra).
  - `height_reference` ("outer" | "inner" | "tangent"; opcional, por defecto `"outer"`): "outer", "inner" o "tangent".
  - `bend_position` ("inside" | "outside" | "adjacent" | "tangent"; opcional, por defecto `"inside"`): "inside", "outside", "adjacent" o "tangent".
  - `width` ("full" | "symmetric" | "two_sides"; opcional, por defecto `"full"`): "full", "symmetric" o "two_sides".
  - `width_distance` (número o expresión; opcional, por defecto `20`): ancho de la pestaña con width="symmetric", en mm.
  - `width1` (número o expresión; opcional, por defecto `10`): distancia desde el inicio de la arista con width="two_sides", en mm.
  - `width2` (número o expresión; opcional, por defecto `10`): distancia desde el final de la arista con width="two_sides", en mm.
  - `flip` (true/false; opcional, por defecto `false`): true pliega hacia el otro lado.
  - `bend_radius` (número o expresión; opcional, por defecto `null`): radio de plegado en mm que anula el de la regla; vacío = el de la regla.
  - `relief_shape` ("round" | "straight" | "tear" o null; opcional, por defecto `null`): forma del alivio de plegado que anula la regla: "round", "straight" o "tear".
  - `relief_width` (número o expresión; opcional, por defecto `null`): ancho del alivio en mm que anula la regla.
  - `relief_depth` (número o expresión; opcional, por defecto `null`): profundidad del alivio en mm que anula la regla.
  - `body` (texto; opcional, por defecto `null`): cuerpo de chapa sobre el que se evalúan los selectores; vacío = el único cuerpo.
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Pestaña<n>».
- CLI: `omnicad call create_edge_flange --doc pieza.omnicad edges=…`

### `create_hem`

Dobladillo (CHAPA › Dobladillo): dobla el borde de la chapa sobre sí mismo en las aristas rectas elegidas; las aristas se elige con un selector (evaluado sobre body) o un id de find_faces / find_edges. hem_type: closed (plano, sin separación), open (con separación gap) o teardrop (lágrima, con radio). position: adjacent (el pliegue fuera del borde) o tangent.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `edges` (texto o lista de texto; obligatorio): aristas rectas del borde de la chapa: selector, id de find_edges o lista.
  - `hem_type` ("closed" | "open" | "teardrop"; opcional, por defecto `"closed"`): "closed", "open" o "teardrop".
  - `length` (número o expresión; opcional, por defecto `10`): largo del tramo doblado en mm (número o expresión).
  - `gap` (número o expresión; opcional, por defecto `null`): separación entre la chapa y el tramo doblado en mm (open y teardrop); vacío = la de la regla.
  - `radius` (número o expresión; opcional, por defecto `null`): radio de la lágrima en mm (teardrop); vacío = el de la regla.
  - `position` ("adjacent" | "tangent"; opcional, por defecto `"adjacent"`): "adjacent" o "tangent".
  - `flip` (true/false; opcional, por defecto `false`): true dobla hacia el otro lado.
  - `body` (texto; opcional, por defecto `null`): cuerpo de chapa sobre el que se evalúan los selectores; vacío = el único cuerpo.
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Dobladillo<n>».
- CLI: `omnicad call create_hem --doc pieza.omnicad edges=…`

### `fold`

Plegar (CHAPA › Plegar): pliega la chapa por líneas rectas de un boceto dibujado sobre la cara (create_sketch con plane = la cara). face es la cara estacionaria (se elige con un selector (evaluado sobre body) o un id de find_faces / find_edges.); fixed_point dice qué lado de la línea queda quieto (un punto [x, y, z] sobre la cara; vacío = un punto de la cara). line_position: start, center o end (dónde cae la línea respecto del pliegue).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `face` (texto; obligatorio): cara estacionaria (la de arriba o la de abajo de una parte plana): selector o id de find_faces.
  - `sketch` (texto; obligatorio): id o nombre del boceto con las líneas de plegado.
  - `lines` (lista de entero o null; opcional, por defecto `null`): ids de las líneas del boceto (get_sketch); vacío = todas las líneas no de construcción.
  - `angle` (número o expresión; opcional, por defecto `90`): ángulo de plegado en grados.
  - `line_position` ("start" | "center" | "end"; opcional, por defecto `"center"`): "start", "center" o "end".
  - `flip` (true/false; opcional, por defecto `false`): true pliega hacia el otro lado.
  - `bend_radius` (número o expresión; opcional, por defecto `null`): radio de plegado en mm que anula el de la regla; vacío = el de la regla.
  - `fixed_point` (lista de número o null; opcional, por defecto `null`): punto [x, y, z] en mm sobre la cara, del lado que queda quieto; vacío = un punto de la cara.
  - `body` (texto; opcional, por defecto `null`): cuerpo de chapa sobre el que se evalúa el selector de face.
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Plegado<n>».
- CLI: `omnicad call fold --doc pieza.omnicad face=… sketch=…`

### `unfold`

Desplegar (CHAPA › Desplegar): endereza pliegues de la chapa, todos o los elegidos (caras curvas de los pliegues), con la cara estacionaria quieta. Es un paso del timeline: lo que se agregue después (p. ej. agujeros que crucen un pliegue) se hace sobre la pieza desplegada; refold la vuelve a plegar.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `face` (texto; obligatorio): cara estacionaria (la de arriba o la de abajo de una parte plana): selector o id de find_faces.
  - `bends` (texto o lista de texto o null; opcional, por defecto `null`): caras curvas de los pliegues a desplegar (selector como "%CYLINDER", id o lista); vacío = todos.
  - `fixed_point` (lista de número o null; opcional, por defecto `null`): punto [x, y, z] en mm sobre la cara estacionaria (desempata si hay varias); vacío = un punto de la cara.
  - `body` (texto; opcional, por defecto `null`): cuerpo de chapa sobre el que se evalúan los selectores.
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Desplegado<n>».
- CLI: `omnicad call unfold --doc pieza.omnicad face=…`

### `refold`

Volver a plegar (CHAPA › Volver a plegar): vuelve a plegar los pliegues desplegados del cuerpo. face (opcional) es la cara que queda quieta; sin ella, la misma que al desplegar.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo de chapa; vacío = el único cuerpo de chapa.
  - `face` (texto; opcional, por defecto `null`): cara estacionaria (selector o id); vacío = la del desplegado.
  - `fixed_point` (lista de número o null; opcional, por defecto `null`): punto [x, y, z] en mm sobre esa cara; vacío = un punto de la cara.
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Replegado<n>».
- CLI: `omnicad call refold --doc pieza.omnicad`

### `create_flat_pattern`

Crear patrón plano (CHAPA › Crear patrón plano): cuerpo nuevo con la pieza desplegada (desarrollo exacto con el factor K) sobre la cara estacionaria (in_place) o al lado de la pieza sin tocar otros cuerpos (beside). Como en Fusion, no cuenta como pieza del modelo (propiedades, interferencias y exportar «todo» lo ignoran). Devuelve el tamaño del desarrollo.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `face` (texto; obligatorio): cara estacionaria (la de arriba o la de abajo de una parte plana): selector o id de find_faces.
  - `location` ("in_place" | "beside"; opcional, por defecto `"in_place"`): "in_place" (sobre la cara estacionaria) o "beside" (al lado de la pieza).
  - `fixed_point` (lista de número o null; opcional, por defecto `null`): punto [x, y, z] en mm sobre la cara (desempata); vacío = un punto de la cara.
  - `body` (texto; opcional, por defecto `null`): cuerpo de chapa sobre el que se evalúa el selector.
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Patrón plano<n>».
- CLI: `omnicad call create_flat_pattern --doc pieza.omnicad face=…`

### `convert_to_sheet_metal`

Convertir a chapa (CHAPA › Convertir a chapa): una placa plana de espesor constante (p. ej. una caja delgada) pasa a ser de chapa; el espesor se mide desde la cara elegida y reemplaza al de la regla, que aporta radio, K, alivios y material.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `face` (texto; obligatorio): una cara plana ANCHA de la placa (la de arriba o la de abajo): selector o id de find_faces.
  - `rule` (texto; opcional, por defecto `null`): regla plantilla (list_sheet_metal_rules); vacío = "Acero 1 mm".
  - `bend_radius` (número o expresión; opcional, por defecto `null`): radio de plegado en mm que anula el de la regla.
  - `k_factor` (número o expresión; opcional, por defecto `null`): factor K que anula el de la regla (0 a 1).
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que se evalúa el selector.
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Convertir a chapa<n>».
- CLI: `omnicad call convert_to_sheet_metal --doc pieza.omnicad face=…`

### `rip`

Desgarro (CHAPA › Desgarro): mode=face quita la cara elegida (un pliegue —cara curva— o una parte plana); mode=points corta una ranura de ancho gap entre dos puntos del borde de la cara elegida (vértices [x, y, z] de la chapa, puntos de un boceto {"sketch", "point"} o puntos de construcción por id o nombre), del lado side. Si la pieza queda partida, cada pedazo es un cuerpo de chapa (bodies_created).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `face` (texto; obligatorio): con mode="face", la cara a quitar; con mode="points", la cara cuyo borde tiene los dos puntos (selector o id).
  - `mode` ("face" | "points"; opcional, por defecto `"face"`): "face" o "points".
  - `points` (lista de lista de número o objeto o texto o null; opcional, por defecto `null`): con mode="points", dos puntos del borde: [x, y, z] de un vértice, {"sketch": id, "point": id} o el id o nombre de un punto de construcción (create_construction_point).
  - `side` ("side1" | "side2" | "center"; opcional, por defecto `"center"`): con mode="points", de qué lado de la línea p1→p2 va la ranura: "side1", "side2" o "center".
  - `gap` (número o expresión; opcional, por defecto `null`): ancho de la ranura en mm; vacío = la separación de la regla.
  - `body` (texto; opcional, por defecto `null`): cuerpo de chapa sobre el que se evalúa el selector.
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Desgarro<n>».
- CLI: `omnicad call rip --doc pieza.omnicad face=…`

### `join_by_bend`

Unir plegando (CHAPA › Unir plegando): une dos cuerpos de chapa del MISMO espesor con un pliegue entre dos aristas rectas paralelas (una de cada cuerpo, del borde de la cara de arriba o de abajo); quedan en un solo cuerpo. Cada arista: selector evaluado sobre body1 / body2 o id de find_edges.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `edge1` (texto; obligatorio): arista del primer cuerpo de chapa (queda con el id del cuerpo resultante).
  - `edge2` (texto; obligatorio): arista del segundo cuerpo de chapa (ese cuerpo se une al primero).
  - `body1` (texto; opcional, por defecto `null`): cuerpo sobre el que se evalúa el selector de edge1.
  - `body2` (texto; opcional, por defecto `null`): cuerpo sobre el que se evalúa el selector de edge2.
  - `bend_radius` (número o expresión; opcional, por defecto `null`): radio de plegado en mm que anula el de la regla.
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Unión por pliegue<n>».
- CLI: `omnicad call join_by_bend --doc pieza.omnicad edge1=… edge2=…`

### `set_sheet_metal_rule`

Cambia la regla de un cuerpo de chapa (CHAPA › Reglas de chapa): otra regla de la biblioteca y/o valores que la anulan (espesor, radio, K, alivios, separación). Se edita el paso que creó el cuerpo y se recalcula todo lo que sigue. reset=true vuelve a los valores de la regla. En una chapa convertida el espesor es el medido: no se cambia.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo de chapa; vacío = el único cuerpo de chapa.
  - `rule` (texto; opcional, por defecto `null`): regla nueva (list_sheet_metal_rules); vacío = la que tiene.
  - `thickness` (número o expresión; opcional, por defecto `null`): espesor en mm que anula el de la regla (número o expresión).
  - `bend_radius` (número o expresión; opcional, por defecto `null`): radio de plegado en mm.
  - `k_factor` (número o expresión; opcional, por defecto `null`): factor K (0 a 1).
  - `relief_shape` ("round" | "straight" | "tear" o null; opcional, por defecto `null`): forma del alivio de plegado: "round", "straight" o "tear".
  - `relief_width` (número o expresión; opcional, por defecto `null`): ancho del alivio de plegado en mm.
  - `relief_depth` (número o expresión; opcional, por defecto `null`): profundidad del alivio de plegado en mm.
  - `corner_relief` ("trim" | "round" | "square" | "tear" o null; opcional, por defecto `null`): alivio de esquina: "trim", "round", "square" o "tear".
  - `corner_size` (número o expresión; opcional, por defecto `null`): tamaño del alivio de esquina en mm.
  - `gap` (número o expresión; opcional, por defecto `null`): separación de desgarros y esquinas en mm.
  - `reset` (true/false; opcional, por defecto `false`): true borra los valores anulados antes (vuelve a los de la regla).
- CLI: `omnicad call set_sheet_metal_rule --doc pieza.omnicad`

### `export_flat_pattern_dxf`

Exporta el patrón plano de un cuerpo de chapa (o de su patrón plano) a DXF en mm para corte láser o plegadora (CHAPA › Exportar DXF del patrón plano): capas CONTORNO_EXTERIOR, CONTORNOS_INTERIORES, LINEAS_PLIEGUE (centros de pliegue) y EXTENSION_PLIEGUE (límites de cada pliegue).

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; obligatorio): ruta del .dxf a escribir (si no termina en .dxf se le agrega).
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo de chapa o de su patrón plano; vacío = el único cuerpo de chapa.
  - `bend_centerlines` (true/false; opcional, por defecto `true`): true dibuja la línea de centro de cada pliegue.
  - `bend_extensions` (true/false; opcional, por defecto `false`): true dibuja las líneas de inicio y fin de cada pliegue.
  - `overwrite` (true/false; opcional, por defecto `false`): true para reemplazar el archivo si ya existe.
- CLI: `omnicad call export_flat_pattern_dxf --doc pieza.omnicad path=…`

### `set_flat_pattern_view`

Activa solo el desarrollo de chapa o vuelve al modelo plegado. Admite deshacer.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `active` (true/false; opcional, por defecto `true`): true activa el patrón plano; false termina su visualización.
  - `body` (texto; opcional, por defecto `null`): cuerpo de chapa o su patrón por nombre o id; vacío elige el último patrón.
- CLI: `omnicad call set_flat_pattern_view --doc pieza.omnicad`

## Grupo malla

Mallas de triángulos: teselar, reparar, limpiar, reducir, remallar, suavizar, vaciar, cortar, combinar, separar y convertir a sólido (traer un .stl/.obj/.3mf/.ply: insert_file).

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`get_mesh_info`](#get_mesh_info) | no | Información de los cuerpos de malla (uno o todos): triángulos, vértices, grupos de caras, cáscaras (partes conexas), si es cerrada (estanca) y orientada, si el volumen es positivo (normales hacia afuera), aristas de borde (agujeros) y no manifold, triángulos degenerados, volumen (mm³), área (mm²) y caja envolvente. |
| [`tessellate`](#tessellate) | sí | Convierte sólidos o superficies en cuerpos de malla (MALLA › Malla de cuerpo B-Rep de Fusion): un grupo de caras por cara del B-rep. refinement: low, medium o high (desvío de 0,2 % / 0,05 % / 0,01 % de la diagonal de la caja y 30° / 15° / 8°). keep_original=false borra el cuerpo B-rep. |
| [`repair_mesh`](#repair_mesh) | sí | Repara mallas (MALLA › PREPARAR › Reparar de Fusion). kind: close_holes (une vértices idénticos, orienta las normales y tapa los agujeros), merge_vertices (solo une los vértices casi coincidentes), stitch_and_remove (además cose, corrige triángulos degenerados, quita caras dobles y partes diminutas) o rebuild (lo anterior y un remallado uniforme). |
| [`clean_mesh`](#clean_mesh) | sí | Limpia mallas paso por paso (Malla › Limpiar de Blender), en este orden y cada uno con su casilla: merge_by_distance (une los vértices a distance mm o menos), dissolve_degenerate (colapsa aristas de distance o menos y arregla triángulos sin área y caras dobles), delete_loose (vértices sin caras, triángulos aislados y, con min_shell_fraction, partes chicas), recalculate_normals (orientación consistente y hacia afuera) y fill_holes (tapa los agujeros de hasta max_hole_sides lados; 0 = todos). |
| [`generate_face_groups`](#generate_face_groups) | sí | Agrupa las caras de mallas por ángulo (MALLA › PREPARAR › Generar grupos de caras de Fusion): las vecinas cuyas normales difieren menos de angle quedan en el mismo grupo. |
| [`reduce_mesh`](#reduce_mesh) | sí | Baja la cantidad de triángulos de mallas (MALLA › MODIFICAR › Reducir de Fusion; colapso de aristas con error cuadrático). mode: proportion (fracción de los triángulos actuales), face_count (cantidad objetivo) o tolerance (desvío máximo en mm). |
| [`remesh`](#remesh) | sí | Rehace los triángulos de mallas con un tamaño parejo (MALLA › MODIFICAR › Remallar de Fusion). density > 1 da más triángulos (el largo de arista objetivo es el largo medio / √density; si la malla original tiene triángulos mucho más chicos que el promedio, el total puede bajar igual). |
| [`smooth_mesh`](#smooth_mesh) | sí | Suaviza mallas sin encogerlas (MALLA › MODIFICAR › Suavizar de Fusion; filtro de Taubin). |
| [`shell_mesh`](#shell_mesh) | sí | Ahueca mallas cerradas con un espesor de pared (MALLA › MODIFICAR › Vaciado de Fusion): suma una cáscara interior desplazada thickness mm hacia adentro. |
| [`plane_cut_mesh`](#plane_cut_mesh) | sí | Corta mallas con un plano (MALLA › MODIFICAR › Corte de plano de Fusion). kind: trim (queda el lado hacia donde apunta la normal del plano; flip conserva el otro), split_body (dos cuerpos, uno por lado) o split_faces (una malla con los triángulos partidos sobre el plano). fill tapa el corte (un grupo de caras nuevo). |
| [`combine_meshes`](#combine_meshes) | sí | Combina cuerpos de malla (MALLA › MODIFICAR › Combinar de Fusion). operation: join, cut o intersect (booleanas reales: las mallas tienen que ser cerradas; repair_mesh o clean_mesh antes si no) o merge (junta los triángulos sin tocarlos). |
| [`separate_mesh`](#separate_mesh) | sí | Separa mallas en varios cuerpos (MALLA › MODIFICAR › Separar de Fusion): by shells, un cuerpo por parte conexa; by face_groups, uno por grupo de caras (generate_face_groups los crea). |
| [`reverse_mesh_normals`](#reverse_mesh_normals) | sí | Da vuelta la orientación de todos los triángulos de mallas (MALLA › MODIFICAR › Invertir normal de Fusion): el volumen cambia de signo. |
| [`scale_mesh`](#scale_mesh) | sí | Escala mallas desde el origen (MALLA › MODIFICAR › Escalar malla de Fusion): uniforme con factor_x solo, o distinto en cada eje. |
| [`convert_mesh`](#convert_mesh) | sí | Convierte mallas en cuerpos B-rep (MALLA › MODIFICAR › Convertir malla de Fusion): sólido si la malla es cerrada, superficie si no. method: faceted (una cara plana por triángulo) o prismatic (une las caras coplanares vecinas del mismo grupo; no reconoce cilindros). |
| [`create_mesh_section_sketch`](#create_mesh_section_sketch) | sí | Crea un boceto de sección de malla (MALLA › CREAR › Crear boceto de sección de malla de Fusion): un boceto nuevo sobre el plano con la línea donde el plano corta la malla, como spline fija de construcción (una por lazo). offset desplaza el plano de sección sobre su normal. |
| [`fit_curves_to_mesh_section`](#fit_curves_to_mesh_section) | sí | Ajusta curvas a la sección de malla de un boceto (BOCETO › CREAR › Ajustar curvas a sección de malla de Fusion). curve_type: line, arc o spline (abiertas: de start a end sobre la sección, por el camino short o long), closed_spline, circle o ellipse (siguen toda la sección), o lines_and_arcs (no está en Fusion: líneas y arcos dentro de max_deviation, toda la sección o de start a end). |

### `get_mesh_info`

Información de los cuerpos de malla (uno o todos): triángulos, vértices, grupos de caras, cáscaras (partes conexas), si es cerrada (estanca) y orientada, si el volumen es positivo (normales hacia afuera), aristas de borde (agujeros) y no manifold, triángulos degenerados, volumen (mm³), área (mm²) y caja envolvente. No cambia el documento.

- Modifica el documento: no.
- Parámetros:
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo de malla; vacío = todos los cuerpos de malla del documento.
- CLI: `omnicad call get_mesh_info --doc pieza.omnicad`

### `tessellate`

Convierte sólidos o superficies en cuerpos de malla (MALLA › Malla de cuerpo B-Rep de Fusion): un grupo de caras por cara del B-rep. refinement: low, medium o high (desvío de 0,2 % / 0,05 % / 0,01 % de la diagonal de la caja y 30° / 15° / 8°). keep_original=false borra el cuerpo B-rep.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): id o nombre de los cuerpos sólidos o de superficie (uno o una lista).
  - `refinement` ("low" | "medium" | "high"; opcional, por defecto `"medium"`): finura de los triángulos: "low", "medium" o "high".
  - `keep_original` (true/false; opcional, por defecto `true`): true conserva el cuerpo B-rep además de la malla nueva.
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = automático.
- CLI: `omnicad call tessellate --doc pieza.omnicad bodies=…`

### `repair_mesh`

Repara mallas (MALLA › PREPARAR › Reparar de Fusion). kind: close_holes (une vértices idénticos, orienta las normales y tapa los agujeros), merge_vertices (solo une los vértices casi coincidentes), stitch_and_remove (además cose, corrige triángulos degenerados, quita caras dobles y partes diminutas) o rebuild (lo anterior y un remallado uniforme). Para elegir cada paso de limpieza por separado: clean_mesh.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): id o nombre de los cuerpos de malla.
  - `kind` ("close_holes" | "merge_vertices" | "stitch_and_remove" | "rebuild"; opcional, por defecto `"close_holes"`): "close_holes", "merge_vertices", "stitch_and_remove" o "rebuild".
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = automático.
- CLI: `omnicad call repair_mesh --doc pieza.omnicad bodies=…`

### `clean_mesh`

Limpia mallas paso por paso (Malla › Limpiar de Blender), en este orden y cada uno con su casilla: merge_by_distance (une los vértices a distance mm o menos), dissolve_degenerate (colapsa aristas de distance o menos y arregla triángulos sin área y caras dobles), delete_loose (vértices sin caras, triángulos aislados y, con min_shell_fraction, partes chicas), recalculate_normals (orientación consistente y hacia afuera) y fill_holes (tapa los agujeros de hasta max_hole_sides lados; 0 = todos). Triángulos a cuadriláteros no existe: la malla es solo de triángulos.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): id o nombre de los cuerpos de malla.
  - `merge_by_distance` (true/false; opcional, por defecto `true`): true une los vértices que están a distance o menos.
  - `distance` (número o expresión; opcional, por defecto `"0.001 mm"`): umbral en mm (número o expresión) para unir vértices y colapsar aristas cortas; 0 = solo los idénticos.
  - `dissolve_degenerate` (true/false; opcional, por defecto `true`): true colapsa las aristas cortas y arregla los triángulos sin área.
  - `delete_loose` (true/false; opcional, por defecto `true`): true borra vértices sin caras y triángulos que no comparten aristas con otros.
  - `min_shell_fraction` (número; opcional, por defecto `0.0`): con delete_loose, borra también las partes conexas con menos de esta fracción (0 a 1) del área total (p. ej. 0.01 = 1 %); 0 = no.
  - `recalculate_normals` (true/false; opcional, por defecto `true`): true orienta los triángulos de forma consistente y hacia afuera.
  - `fill_holes` (true/false; opcional, por defecto `false`): true tapa los agujeros (cada tapa es un grupo de caras nuevo).
  - `max_hole_sides` (entero; opcional, por defecto `0`): con fill_holes, solo los agujeros de hasta esta cantidad de lados; 0 = todos.
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = automático.
- CLI: `omnicad call clean_mesh --doc pieza.omnicad bodies=…`

### `generate_face_groups`

Agrupa las caras de mallas por ángulo (MALLA › PREPARAR › Generar grupos de caras de Fusion): las vecinas cuyas normales difieren menos de angle quedan en el mismo grupo. Sirve para separate_mesh by=face_groups y para convertir con method=prismatic.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): id o nombre de los cuerpos de malla.
  - `angle` (número o expresión; opcional, por defecto `30`): ángulo límite entre caras vecinas, en grados (número o expresión), entre 0 y 180.
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = automático.
- CLI: `omnicad call generate_face_groups --doc pieza.omnicad bodies=…`

### `reduce_mesh`

Baja la cantidad de triángulos de mallas (MALLA › MODIFICAR › Reducir de Fusion; colapso de aristas con error cuadrático). mode: proportion (fracción de los triángulos actuales), face_count (cantidad objetivo) o tolerance (desvío máximo en mm).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): id o nombre de los cuerpos de malla.
  - `mode` ("proportion" | "face_count" | "tolerance"; opcional, por defecto `"proportion"`): "proportion", "face_count" o "tolerance".
  - `proportion` (número o expresión; opcional, por defecto `0.5`): con mode=proportion, fracción de triángulos que queda (mayor que 0 y hasta 1).
  - `face_count` (entero; opcional, por defecto `1000`): con mode=face_count, cantidad de triángulos objetivo (al menos 4).
  - `tolerance` (número o expresión; opcional, por defecto `0.1`): con mode=tolerance, desvío máximo en mm (número o expresión).
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = automático.
- CLI: `omnicad call reduce_mesh --doc pieza.omnicad bodies=…`

### `remesh`

Rehace los triángulos de mallas con un tamaño parejo (MALLA › MODIFICAR › Remallar de Fusion). density > 1 da más triángulos (el largo de arista objetivo es el largo medio / √density; si la malla original tiene triángulos mucho más chicos que el promedio, el total puede bajar igual). Tiene un tope de 100.000 triángulos: si se pasaría, falla antes de calcular y dice cuánto bajar.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): id o nombre de los cuerpos de malla.
  - `density` (número o expresión; opcional, por defecto `1`): densidad relativa de triángulos (mayor que 0; 1 = parecida a la actual).
  - `preserve_boundaries` (true/false; opcional, por defecto `true`): true no toca los bordes abiertos.
  - `preserve_sharp_edges` (true/false; opcional, por defecto `true`): true conserva las aristas vivas (más de 30° entre caras) y los bordes entre grupos.
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = automático.
- CLI: `omnicad call remesh --doc pieza.omnicad bodies=…`

### `smooth_mesh`

Suaviza mallas sin encogerlas (MALLA › MODIFICAR › Suavizar de Fusion; filtro de Taubin). Los bordes abiertos quedan fijos; redondea las aristas vivas (avisa si el volumen de una malla cerrada cambia más de 1 %).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): id o nombre de los cuerpos de malla.
  - `strength` (número o expresión; opcional, por defecto `0.5`): intensidad del suavizado, de 0 a 1.
  - `iterations` (entero; opcional, por defecto `10`): cantidad de pasadas (al menos 1).
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = automático.
- CLI: `omnicad call smooth_mesh --doc pieza.omnicad bodies=…`

### `shell_mesh`

Ahueca mallas cerradas con un espesor de pared (MALLA › MODIFICAR › Vaciado de Fusion): suma una cáscara interior desplazada thickness mm hacia adentro. Aproximado: avisa si la pared interior se pliega o se cruza (usá un espesor menor).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): id o nombre de los cuerpos de malla (tienen que ser cerrados).
  - `thickness` (número o expresión; opcional, por defecto `2`): espesor de la pared en mm (número o expresión, mayor que cero).
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = automático.
- CLI: `omnicad call shell_mesh --doc pieza.omnicad bodies=…`

### `plane_cut_mesh`

Corta mallas con un plano (MALLA › MODIFICAR › Corte de plano de Fusion). kind: trim (queda el lado hacia donde apunta la normal del plano; flip conserva el otro), split_body (dos cuerpos, uno por lado) o split_faces (una malla con los triángulos partidos sobre el plano). fill tapa el corte (un grupo de caras nuevo). Normales: XY = +Z, YZ = +X, XZ = −Y; kept_side_normal en el resultado dice cuál quedó.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): id o nombre de los cuerpos de malla.
  - `plane` (texto; obligatorio): "XY", "XZ", "YZ", el id o nombre de un plano de construcción, o UNA cara plana de un sólido (selector como ">Z" o id de find_faces, p. ej. "Cuerpo1/F6": el plano de la cara).
  - `kind` ("trim" | "split_body" | "split_faces"; opcional, por defecto `"trim"`): "trim", "split_body" o "split_faces".
  - `fill` (true/false; opcional, por defecto `true`): true tapa el corte con triángulos.
  - `flip` (true/false; opcional, por defecto `false`): true invierte el lado que se conserva (en trim) o el orden de las partes (en split_body).
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = automático.
  - `plane_body` (texto; opcional, por defecto `null`): cuerpo sólido donde se evalúa el selector de cara de plane; vacío = el único sólido del documento.
  - `offset` (número o expresión; opcional, por defecto `0`): desfase del plano en mm sobre su normal (número o expresión).
  - `angle` (número o expresión; opcional, por defecto `0`): giro del plano en grados (número o expresión) alrededor de su eje u, después del offset.
- CLI: `omnicad call plane_cut_mesh --doc pieza.omnicad bodies=… plane=…`

### `combine_meshes`

Combina cuerpos de malla (MALLA › MODIFICAR › Combinar de Fusion). operation: join, cut o intersect (booleanas reales: las mallas tienen que ser cerradas; repair_mesh o clean_mesh antes si no) o merge (junta los triángulos sin tocarlos). El resultado queda en target; las herramientas se borran salvo keep_tools=true. Si join conserva las tapas internas de un contacto sin solape, reintenta con el kernel B-rep para soldarlas (hasta 50.000 triángulos por entrada; regenera los grupos de caras).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `target` (texto; obligatorio): id o nombre del cuerpo de malla de destino.
  - `tools` (texto o lista de texto; obligatorio): id o nombre de los cuerpos de malla herramienta (uno o una lista).
  - `operation` ("join" | "cut" | "intersect" | "merge"; opcional, por defecto `"join"`): "join", "cut", "intersect" o "merge".
  - `keep_tools` (true/false; opcional, por defecto `false`): true conserva los cuerpos herramienta.
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = automático.
- CLI: `omnicad call combine_meshes --doc pieza.omnicad target=… tools=…`

### `separate_mesh`

Separa mallas en varios cuerpos (MALLA › MODIFICAR › Separar de Fusion): by shells, un cuerpo por parte conexa; by face_groups, uno por grupo de caras (generate_face_groups los crea). Si una malla tiene una sola parte, avisa y no cambia.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): id o nombre de los cuerpos de malla.
  - `by` ("shells" | "face_groups"; opcional, por defecto `"shells"`): "shells" (partes conexas) o "face_groups" (grupos de caras).
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = automático.
- CLI: `omnicad call separate_mesh --doc pieza.omnicad bodies=…`

### `reverse_mesh_normals`

Da vuelta la orientación de todos los triángulos de mallas (MALLA › MODIFICAR › Invertir normal de Fusion): el volumen cambia de signo. Para orientar bien una malla con normales mezcladas: clean_mesh con recalculate_normals.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): id o nombre de los cuerpos de malla.
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = automático.
- CLI: `omnicad call reverse_mesh_normals --doc pieza.omnicad bodies=…`

### `scale_mesh`

Escala mallas desde el origen (MALLA › MODIFICAR › Escalar malla de Fusion): uniforme con factor_x solo, o distinto en cada eje. Un factor negativo espeja (las normales siguen hacia afuera).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): id o nombre de los cuerpos de malla.
  - `factor_x` (número o expresión; opcional, por defecto `1`): factor de escala en X (número o expresión, distinto de cero); sin factor_y ni factor_z, en los tres ejes.
  - `factor_y` (número o expresión; opcional, por defecto `null`): factor en Y; vacío = el de factor_x.
  - `factor_z` (número o expresión; opcional, por defecto `null`): factor en Z; vacío = el de factor_x.
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = automático.
- CLI: `omnicad call scale_mesh --doc pieza.omnicad bodies=…`

### `convert_mesh`

Convierte mallas en cuerpos B-rep (MALLA › MODIFICAR › Convertir malla de Fusion): sólido si la malla es cerrada, superficie si no. method: faceted (una cara plana por triángulo) o prismatic (une las caras coplanares vecinas del mismo grupo; no reconoce cilindros). Máximo 50.000 triángulos: reduce_mesh antes si hay más. keep_original=true conserva la malla.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): id o nombre de los cuerpos de malla.
  - `method` ("faceted" | "prismatic"; opcional, por defecto `"faceted"`): "faceted" o "prismatic".
  - `keep_original` (true/false; opcional, por defecto `false`): true conserva el cuerpo de malla además del B-rep nuevo.
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = automático.
- CLI: `omnicad call convert_mesh --doc pieza.omnicad bodies=…`

### `create_mesh_section_sketch`

Crea un boceto de sección de malla (MALLA › CREAR › Crear boceto de sección de malla de Fusion): un boceto nuevo sobre el plano con la línea donde el plano corta la malla, como spline fija de construcción (una por lazo). offset desplaza el plano de sección sobre su normal. Después, fit_curves_to_mesh_section dibuja curvas que la siguen. Coordenadas del boceto como en create_sketch.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `body` (texto; obligatorio): id o nombre del cuerpo de malla.
  - `plane` (texto; opcional, por defecto `"XY"`): "XY", "XZ", "YZ", el id o nombre de un plano de construcción, o una cara plana de un sólido (selector como ">Z" o id de find_faces).
  - `offset` (número o expresión; opcional, por defecto `0`): distancia en mm del plano de sección al plano elegido, sobre su normal (número o expresión).
  - `name` (texto; opcional, por defecto `null`): nombre del boceto; vacío = "Boceto1", "Boceto2"…
  - `plane_body` (texto; opcional, por defecto `null`): cuerpo sólido donde se evalúa el selector de cara de plane; vacío = el único sólido.
  - `angle` (número o expresión; opcional, por defecto `0`): giro en grados (número o expresión) del plano de sección alrededor de su eje u, después del offset.
- CLI: `omnicad call create_mesh_section_sketch --doc pieza.omnicad body=…`

### `fit_curves_to_mesh_section`

Ajusta curvas a la sección de malla de un boceto (BOCETO › CREAR › Ajustar curvas a sección de malla de Fusion). curve_type: line, arc o spline (abiertas: de start a end sobre la sección, por el camino short o long), closed_spline, circle o ellipse (siguen toda la sección), o lines_and_arcs (no está en Fusion: líneas y arcos dentro de max_deviation, toda la sección o de start a end). Las curvas son geometría normal del boceto: un extremo que cae en un punto ya dibujado lo comparte (la curva siguiente arranca donde terminó la anterior) y un lazo cerrado da perfil. Sin restricciones (como Fusion, salvo la tangencia). Devuelve la desviación real de cada curva; avisa si pasa de max_deviation.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): id o nombre del boceto de sección de malla (create_mesh_section_sketch).
  - `curve_type` ("line" | "arc" | "spline" | "closed_spline" | "circle" | "ellipse" | "lines_and_arcs"; obligatorio): "line", "arc", "spline", "closed_spline", "circle", "ellipse" o "lines_and_arcs".
  - `section` (entero; opcional, por defecto `null`): id de la línea de sección (sections de create_mesh_section_sketch); vacío = la más cercana a start, o todas las cerradas para las curvas cerradas sin start.
  - `start` (lista de número o null; opcional, por defecto `null`): [x, y] del primer punto sobre la sección (mm, coordenadas del boceto); se toma el punto de la sección más cercano.
  - `end` (lista de número o null; opcional, por defecto `null`): [x, y] del segundo punto sobre la sección.
  - `path` ("short" | "long"; opcional, por defecto `"short"`): "short" (camino corto) o "long" (camino largo) entre start y end en una sección cerrada.
  - `tolerance` (número o expresión; opcional, por defecto `0.1`): tolerancia de ajuste de spline en mm: más chica, más puntos y mejor ajuste.
  - `max_deviation` (número o expresión; opcional, por defecto `0.1`): desviación máxima en mm entre cada curva y la sección (límite de lines_and_arcs; si una curva lo pasa, avisa).
- CLI: `omnicad call fit_curves_to_mesh_section --doc pieza.omnicad sketch=… curve_type=…`

## Grupo ensamble

Ensamble: componentes, uniones, accionar, límites, grupos rígidos, vínculos y estudio de movimiento.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`get_assembly`](#get_assembly) | no | Ensamble del documento: componentes (id, nombre, fijo, cuerpos, posición: traslación y rotación respecto de donde se modelaron, caja envolvente), uniones (tipo, componentes, valores actuales de giro en grados y deslizamiento en mm, límites, ejes, estado), orígenes de unión, grupos rígidos, vínculos de movimiento y los cuerpos sueltos en la raíz. |
| [`create_component`](#create_component) | sí | Crea un componente con los cuerpos dados (ENSAMBLAR › Nuevo componente desde cuerpos). |
| [`ground_component`](#ground_component) | sí | Fija o libera un componente (ENSAMBLAR › Fijar). |
| [`create_joint`](#create_joint) | sí | Une dos componentes (ENSAMBLAR › Unión): mueve el componente de origin1 hasta que su marco coincide con el de origin2 (caras planas enfrentadas; dos ejes —perno en agujero— en el mismo sentido) y define cómo se mueve después. |
| [`create_as_built_joint`](#create_as_built_joint) | sí | Unión como está (ENSAMBLAR › Unión como está): liga el componente de `origin` al componente `component2` SIN moverlo de donde está y define su movimiento alrededor del marco de `origin` (p. ej. el eje de un agujero para una bisagra). |
| [`create_joint_origin`](#create_joint_origin) | sí | Origen de unión (ENSAMBLAR › Origen de la unión): guarda un marco (punto con orientación) sobre una cara o arista, con giro y desfase, para usarlo después como origin2 de create_joint. |
| [`drive_joint`](#drive_joint) | sí | Acciona una unión (ENSAMBLAR › Accionar uniones): cambia su giro o deslizamiento y el mecanismo se recalcula (las uniones y vínculos que dependen de ella la siguen). |
| [`set_joint_limits`](#set_joint_limits) | sí | Límites de movimiento de una unión (Joint Limits de Fusion) sobre su movimiento principal: el giro (grados) si gira, si no el deslizamiento (mm). |
| [`create_rigid_group`](#create_rigid_group) | sí | Grupo rígido (ENSAMBLAR › Grupo rígido): los componentes se mueven juntos; una unión que mueve a uno mueve a todos. |
| [`create_motion_link`](#create_motion_link) | sí | Vínculo de movimiento (ENSAMBLAR › Vínculo de movimiento): la unión 2 se mueve en proporción a la 1 (engranajes, cremallera y piñón). |
| [`motion_study`](#motion_study) | no | Estudio de movimiento (ENSAMBLAR › Estudio de movimiento): recorre una unión por varios valores y, para cada uno, dice dónde quedan los componentes y, con check_interference, qué cuerpos chocan. |

### `get_assembly`

Ensamble del documento: componentes (id, nombre, fijo, cuerpos, posición: traslación y rotación respecto de donde se modelaron, caja envolvente), uniones (tipo, componentes, valores actuales de giro en grados y deslizamiento en mm, límites, ejes, estado), orígenes de unión, grupos rígidos, vínculos de movimiento y los cuerpos sueltos en la raíz.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call get_assembly --doc pieza.omnicad`

### `create_component`

Crea un componente con los cuerpos dados (ENSAMBLAR › Nuevo componente desde cuerpos). Las uniones mueven componentes, no cuerpos sueltos. grounded=true lo fija en su lugar (ninguna unión puede moverlo; suele ser la base). Un cuerpo que ya estaba en otro componente pasa al nuevo.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (lista de texto; obligatorio): ids o nombres de los cuerpos del componente (al menos uno).
  - `name` (texto; opcional, por defecto `null`): nombre del componente; vacío = «Componente<n>».
  - `grounded` (true/false; opcional, por defecto `false`): true para fijarlo (Ground): ninguna unión lo mueve.
- CLI: `omnicad call create_component --doc pieza.omnicad bodies=…`

### `ground_component`

Fija o libera un componente (ENSAMBLAR › Fijar). Un componente fijo no se mueve con ninguna unión.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `component` (texto; obligatorio): id, nombre o un cuerpo del componente.
  - `grounded` (true/false; opcional, por defecto `true`): true lo fija; false lo libera.
- CLI: `omnicad call ground_component --doc pieza.omnicad component=…`

### `create_joint`

Une dos componentes (ENSAMBLAR › Unión): mueve el componente de origin1 hasta que su marco coincide con el de origin2 (caras planas enfrentadas; dos ejes —perno en agujero— en el mismo sentido) y define cómo se mueve después. Cada origen es una cara o arista (selector evaluado sobre body1 / body2, o id de find_faces / find_edges: 'Cuerpo1/F3', 'Cuerpo1/E5'; para aristas con selector, prefijo 'edges:'), un origen de unión (create_joint_origin), un plano, eje o punto de construcción (id o nombre) o XY, XZ, YZ. joint_type: rigid (sin movimiento), revolute (gira alrededor de rotation_axis), slider (desliza sobre slide_axis), cylindrical (gira y desliza sobre rotation_axis), pin_slot (gira sobre rotation_axis y desliza sobre slide_axis), planar (desliza en el plano normal a rotation_axis y gira alrededor de él) o ball (tres giros). angle gira el componente 1 alrededor del Z del marco, offset lo corre [dx, dy, dz] y flip lo da vuelta. Los valores (rotation, slide…) y los límites aceptan número (grados o mm) o expresión. Devuelve la unión y los componentes que se movieron con su traslación y caja envolvente. En uniones con deslizamiento avisa si el componente se movió (snap al centro de cada cara).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `origin1` (texto o lista de número; obligatorio): dónde se toma el componente que SE MUEVE: cara o arista (selector o id), o un vértice por sus coordenadas [x, y, z], del cuerpo body1.
  - `origin2` (texto o lista de número o objeto; obligatorio): dónde va: cara o arista de otro componente (o de la raíz), un vértice [x, y, z], un punto o una curva de boceto {"sketch", "point" | "curve"}, origen de unión, plano, eje o punto de construcción.
  - `joint_type` ("rigid" | "revolute" | "slider" | "cylindrical" | "pin_slot" | "planar" | "ball"; opcional, por defecto `"rigid"`): "rigid", "revolute", "slider", "cylindrical", "pin_slot", "planar" o "ball".
  - `body1` (texto; opcional, por defecto `null`): cuerpo (o componente de un solo cuerpo) donde se evalúa el selector de origin1; con un id no hace falta.
  - `body2` (texto; opcional, por defecto `null`): cuerpo (o componente de un solo cuerpo) donde se evalúa el selector de origin2.
  - `snap1` ("center" | "start" | "end"; opcional, por defecto `"center"`): punto del origen 1 en una arista o cilindro: "center" (medio), "start" o "end".
  - `snap2` ("center" | "start" | "end"; opcional, por defecto `"center"`): punto del origen 2: "center", "start" o "end".
  - `angle` (número o expresión; opcional, por defecto `0`): giro del componente 1 alrededor del eje Z del marco de la unión, en grados.
  - `offset` (lista de número o expresión o null; opcional, por defecto `null`): desfase [dx, dy, dz] en mm en el marco de la unión (Z = normal o eje).
  - `flip` (true/false; opcional, por defecto `false`): true da vuelta el componente 1 (caras en el mismo sentido o ejes opuestos).
  - `rotation_axis` ("X" | "Y" | "Z"; opcional, por defecto `"Z"`): eje del marco para girar (revolute, cylindrical, pin_slot) o normal del plano (planar); "Z" es el eje de un marco de cilindro/arista circular (ver el módulo: marcos de eje).
  - `slide_axis` ("X" | "Y" | "Z"; opcional, por defecto `"X"`): eje del marco para deslizar (slider, pin_slot).
  - `rotation` (número o expresión; opcional, por defecto `null`): giro inicial en grados (revolute, cylindrical, pin_slot, planar, ball).
  - `rotation2` (número o expresión; opcional, por defecto `null`): segundo giro (cabeceo) en grados; solo ball.
  - `rotation3` (número o expresión; opcional, por defecto `null`): tercer giro (guiñada) en grados; solo ball.
  - `slide` (número o expresión; opcional, por defecto `null`): deslizamiento inicial en mm (slider, cylindrical, pin_slot, planar).
  - `slide2` (número o expresión; opcional, por defecto `null`): segundo deslizamiento en mm; solo planar.
  - `minimum` (número o expresión; opcional, por defecto `null`): límite mínimo del movimiento principal (grados si gira, mm si solo desliza); vacío = sin límite.
  - `maximum` (número o expresión; opcional, por defecto `null`): límite máximo del movimiento principal; vacío = sin límite.
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Unión<n>».
- CLI: `omnicad call create_joint --doc pieza.omnicad origin1=… origin2=…`

### `create_as_built_joint`

Unión como está (ENSAMBLAR › Unión como está): liga el componente de `origin` al componente `component2` SIN moverlo de donde está y define su movimiento alrededor del marco de `origin` (p. ej. el eje de un agujero para una bisagra). Cuando el componente 2 se mueve, el 1 lo sigue. Sin component2, la unión es contra la raíz. joint_type: rigid (sin movimiento), revolute (gira alrededor de rotation_axis), slider (desliza sobre slide_axis), cylindrical (gira y desliza sobre rotation_axis), pin_slot (gira sobre rotation_axis y desliza sobre slide_axis), planar (desliza en el plano normal a rotation_axis y gira alrededor de él) o ball (tres giros).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `origin` (texto o lista de número; obligatorio): cara o arista del componente que se mueve (selector evaluado sobre body, o id), o un vértice por sus coordenadas [x, y, z]; define el marco del movimiento.
  - `component2` (texto; opcional, por defecto `null`): componente al que queda ligado (id, nombre o uno de sus cuerpos); vacío = la raíz.
  - `joint_type` ("rigid" | "revolute" | "slider" | "cylindrical" | "pin_slot" | "planar" | "ball"; opcional, por defecto `"revolute"`): "rigid", "revolute", "slider", "cylindrical", "pin_slot", "planar" o "ball".
  - `body` (texto; opcional, por defecto `null`): cuerpo (o componente de un solo cuerpo) donde se evalúa el selector de origin.
  - `snap` ("center" | "start" | "end"; opcional, por defecto `"center"`): punto del origen en una arista o cilindro: "center", "start" o "end".
  - `rotation_axis` ("X" | "Y" | "Z"; opcional, por defecto `"Z"`): eje del marco para girar (o normal del plano en planar); "Z" es el eje de un marco de cilindro/arista circular (ver el módulo: marcos de eje).
  - `slide_axis` ("X" | "Y" | "Z"; opcional, por defecto `"X"`): eje del marco para deslizar (slider, pin_slot).
  - `rotation` (número o expresión; opcional, por defecto `null`): giro en grados.
  - `rotation2` (número o expresión; opcional, por defecto `null`): segundo giro en grados (ball).
  - `rotation3` (número o expresión; opcional, por defecto `null`): tercer giro en grados (ball).
  - `slide` (número o expresión; opcional, por defecto `null`): deslizamiento en mm.
  - `slide2` (número o expresión; opcional, por defecto `null`): segundo deslizamiento en mm (planar).
  - `minimum` (número o expresión; opcional, por defecto `null`): límite mínimo del movimiento principal; vacío = sin límite.
  - `maximum` (número o expresión; opcional, por defecto `null`): límite máximo del movimiento principal; vacío = sin límite.
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Unión<n>».
- CLI: `omnicad call create_as_built_joint --doc pieza.omnicad origin=…`

### `create_joint_origin`

Origen de unión (ENSAMBLAR › Origen de la unión): guarda un marco (punto con orientación) sobre una cara o arista, con giro y desfase, para usarlo después como origin2 de create_joint. Sobre un cilindro o una arista circular sigue siendo un marco de eje.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `geometry` (texto o lista de número o objeto; obligatorio): cara o arista donde va el origen (selector evaluado sobre body, o id de find_faces / find_edges), un vértice [x, y, z] o un punto o una curva de boceto {"sketch", "point" | "curve"}.
  - `body` (texto; opcional, por defecto `null`): cuerpo (o componente de un solo cuerpo) donde se evalúa el selector.
  - `snap` ("center" | "start" | "end"; opcional, por defecto `"center"`): punto en una arista o cilindro: "center", "start" o "end".
  - `angle` (número o expresión; opcional, por defecto `0`): giro del marco alrededor de su Z, en grados.
  - `offset` (lista de número o expresión o null; opcional, por defecto `null`): desfase [dx, dy, dz] en mm en el marco.
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Origen de unión<n>».
- CLI: `omnicad call create_joint_origin --doc pieza.omnicad geometry=…`

### `drive_joint`

Acciona una unión (ENSAMBLAR › Accionar uniones): cambia su giro o deslizamiento y el mecanismo se recalcula (las uniones y vínculos que dependen de ella la siguen). Los límites recortan el valor y avisan. Cada valor acepta número (grados o mm) o expresión.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `joint` (texto; obligatorio): id o nombre de la unión.
  - `rotation` (número o expresión; opcional, por defecto `null`): giro en grados (revolute, cylindrical, pin_slot, planar, ball).
  - `slide` (número o expresión; opcional, por defecto `null`): deslizamiento en mm (slider, cylindrical, pin_slot, planar).
  - `rotation2` (número o expresión; opcional, por defecto `null`): segundo giro en grados (ball).
  - `rotation3` (número o expresión; opcional, por defecto `null`): tercer giro en grados (ball).
  - `slide2` (número o expresión; opcional, por defecto `null`): segundo deslizamiento en mm (planar).
- CLI: `omnicad call drive_joint --doc pieza.omnicad joint=…`

### `set_joint_limits`

Límites de movimiento de una unión (Joint Limits de Fusion) sobre su movimiento principal: el giro (grados) si gira, si no el deslizamiento (mm). Un valor vacío quita ese límite. Si el valor actual queda afuera, la unión se recorta al límite y avisa.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `joint` (texto; obligatorio): id o nombre de la unión.
  - `minimum` (número o expresión; opcional, por defecto `null`): límite mínimo (número o expresión); vacío = sin límite mínimo.
  - `maximum` (número o expresión; opcional, por defecto `null`): límite máximo (número o expresión); vacío = sin límite máximo.
- CLI: `omnicad call set_joint_limits --doc pieza.omnicad joint=…`

### `create_rigid_group`

Grupo rígido (ENSAMBLAR › Grupo rígido): los componentes se mueven juntos; una unión que mueve a uno mueve a todos.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `components` (lista de texto; obligatorio): componentes del grupo (id, nombre o uno de sus cuerpos); al menos dos distintos.
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Grupo rígido<n>».
- CLI: `omnicad call create_rigid_group --doc pieza.omnicad components=…`

### `create_motion_link`

Vínculo de movimiento (ENSAMBLAR › Vínculo de movimiento): la unión 2 se mueve en proporción a la 1 (engranajes, cremallera y piñón). El valor de la unión 2 pasa a ser ratio × el de la unión 1 (con reverse, el opuesto); se acciona la unión 1 con drive_joint.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `joint1` (texto; obligatorio): unión que manda (id o nombre).
  - `joint2` (texto; obligatorio): unión que la sigue (id o nombre).
  - `ratio` (número o expresión; opcional, por defecto `1`): relación unión 2 / unión 1 (número o expresión): grados por grado, mm por grado, etc.
  - `reverse` (true/false; opcional, por defecto `false`): true invierte el sentido de la unión 2.
  - `name` (texto; opcional, por defecto `null`): nombre del paso; vacío = «Vínculo de movimiento<n>».
- CLI: `omnicad call create_motion_link --doc pieza.omnicad joint1=… joint2=…`

### `motion_study`

Estudio de movimiento (ENSAMBLAR › Estudio de movimiento): recorre una unión por varios valores y, para cada uno, dice dónde quedan los componentes y, con check_interference, qué cuerpos chocan. NO cambia el documento. values da los valores (grados o mm); si no, de start a end en steps pasos (una unión que gira va de 0 a 360 si no se dan).

- Modifica el documento: no.
- Parámetros:
  - `joint` (texto; obligatorio): id o nombre de la unión a recorrer.
  - `values` (lista de número o null; opcional, por defecto `null`): valores a probar (grados si es un giro, mm si es un deslizamiento); vacío = de start a end.
  - `start` (número; opcional, por defecto `null`): primer valor (con values vacío); en una unión que gira, 0 si no se da.
  - `end` (número; opcional, por defecto `null`): último valor (con values vacío); en una unión que gira, 360 si no se da.
  - `steps` (entero; opcional, por defecto `13`): cantidad de valores entre start y end, ambos incluidos (2 a 360).
  - `motion` ("rotation" | "rotation2" | "rotation3" | "slide" | "slide2" o null; opcional, por defecto `null`): movimiento a recorrer: "rotation", "slide", "rotation2", "rotation3" o "slide2"; vacío = el principal.
  - `check_interference` (true/false; opcional, por defecto `false`): true busca choques entre los cuerpos sólidos en cada valor (más lento).
  - `bodies` (lista de texto o null; opcional, por defecto `null`): con check_interference, los cuerpos a revisar (ids o nombres); vacío = todos los sólidos del modelo.
- CLI: `omnicad call motion_study --doc pieza.omnicad joint=…`

## Grupo material

Materiales físicos (densidad para la masa), materiales propios y aspecto de los cuerpos.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`list_materials`](#list_materials) | no | Materiales físicos disponibles con su densidad (g/cm³) y su color: los de fábrica (metales, plásticos, gomas, silicona, TPU, madera, vidrio…) y los propios (define_material). |
| [`define_material`](#define_material) | no | Define un material físico propio (nombre, densidad en g/cm³ y color) para usarlo con set_material. |
| [`delete_material`](#delete_material) | no | Borra un material propio de la biblioteca (los de fábrica no se borran). |
| [`set_material`](#set_material) | sí | Asigna el material físico a cuerpos (MODIFICAR › Material físico): da la densidad para la masa (get_physical_properties) y, si el cuerpo no tiene aspecto, su color. material=null quita la asignación (vuelve al material que le dio su operación, p. ej. el de la regla de chapa). list_materials lista los nombres. |
| [`get_bill_of_materials`](#get_bill_of_materials) | no | Lista de materiales (ADMINISTRAR › Lista de materiales): las piezas sólidas del modelo agrupadas (cuerpos iguales del mismo componente y material = una fila con su cantidad), con material, masa (g) y volumen (mm³) por unidad. |
| [`set_appearance`](#set_appearance) | sí | Cambia cómo se ven cuerpos o CARAS (MODIFICAR › Aspecto, «Aplicar a»: Cuerpos/componentes o Caras): un aspecto del diseño, de la biblioteca o de Mis aspectos (appearance, p. ej. |
| [`list_appearances`](#list_appearances) | no | Lista aspectos con todas sus propiedades: los del diseño («En este diseño», con id y quién los usa), los de la biblioteca (por familia: Metal, Plástico, Cristal, Madera, Piedra, Hormigón…), «Mis aspectos» o los favoritos. |
| [`edit_appearance`](#edit_appearance) | sí | Edita un aspecto (el «Editor de materiales» de Fusion) o crea uno nuevo: color, reflectancia, aspereza, metálico, transparencia, translucidez, emisividad, relieve, corte y resaltes. |
| [`manage_appearance`](#manage_appearance) | sí | Administra un aspecto como el menú de «En este diseño» de Fusion: duplicate (copia con nombre «X (1)»), delete (Suprimir; si lo usan cuerpos o caras pide remove_users=true), rename, copy_to_mine (Copiar en Mis aspectos), add_favorite / remove_favorite (Añadir a Favoritos) y delete_mine (borra uno de Mis aspectos). |
| [`list_plastic_rules`](#list_plastic_rules) | no | Reglas de plástico (PLÁSTICO › Administrar reglas) con todos sus valores: material, espesor, ángulo de desmoldeo, radio nominal y los valores de Design Advice (rango de espesor, variación, ángulo mínimo, umbral de filo). |
| [`create_plastic_rule`](#create_plastic_rule) | no | Crea una regla de plástico propia (PLÁSTICO › Administrar reglas › Nueva regla) y la deja en la biblioteca del usuario. |
| [`delete_plastic_rule`](#delete_plastic_rule) | no | Borra una regla de plástico propia de la biblioteca del usuario (las de fábrica no se borran). |

### `list_materials`

Materiales físicos disponibles con su densidad (g/cm³) y su color: los de fábrica (metales, plásticos, gomas, silicona, TPU, madera, vidrio…) y los propios (define_material). Dice también qué material tiene cada cuerpo y la lista de aspectos (set_appearance).

- Modifica el documento: no.
- Parámetros:
  - `query` (texto; opcional, por defecto `null`): texto a buscar en el nombre del material (sin distinguir mayúsculas); vacío = todos.
- CLI: `omnicad call list_materials --doc pieza.omnicad`

### `define_material`

Define un material físico propio (nombre, densidad en g/cm³ y color) para usarlo con set_material. Queda en la biblioteca del usuario (save=true: materiales.json de la carpeta de datos de OmniCAD) y sirve en todos los documentos y sesiones de esta PC. No pisa los de fábrica; uno propio con el mismo nombre se reemplaza solo con overwrite=true. No cambia el documento.

- Modifica el documento: no.
- Parámetros:
  - `name` (texto; obligatorio): nombre del material (p. ej. "Goma EPDM 70 Shore").
  - `density` (número; obligatorio): densidad en g/cm³ (agua = 1; acero = 7,85), mayor que 0.
  - `color` (texto o lista de número o null; opcional, por defecto `null`): color con que se ve: «#rrggbb» o [r, g, b] (0..1 o 0..255); vacío = gris.
  - `overwrite` (true/false; opcional, por defecto `false`): true para reemplazar un material propio que ya existe con ese nombre.
  - `save` (true/false; opcional, por defecto `true`): true lo guarda en la biblioteca del usuario para las próximas sesiones; false, solo en esta sesión.
- CLI: `omnicad call define_material --doc pieza.omnicad name=… density=…`

### `delete_material`

Borra un material propio de la biblioteca (los de fábrica no se borran). Los cuerpos que lo tenían conservan el nombre pero quedan sin densidad hasta que se vuelva a definir.

- Modifica el documento: no.
- Parámetros:
  - `name` (texto; obligatorio): nombre del material propio.
  - `save` (true/false; opcional, por defecto `true`): true también lo saca del archivo de la biblioteca; false, solo de esta sesión.
- CLI: `omnicad call delete_material --doc pieza.omnicad name=…`

### `set_material`

Asigna el material físico a cuerpos (MODIFICAR › Material físico): da la densidad para la masa (get_physical_properties) y, si el cuerpo no tiene aspecto, su color. material=null quita la asignación (vuelve al material que le dio su operación, p. ej. el de la regla de chapa). list_materials lista los nombres.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (lista de texto; obligatorio): ids o nombres de los cuerpos.
  - `material` (texto; obligatorio): nombre del material (sin distinguir mayúsculas), p. ej. "Aluminio 6061" o "Silicona"; null lo quita.
- CLI: `omnicad call set_material --doc pieza.omnicad bodies=… material=…`

### `get_bill_of_materials`

Lista de materiales (ADMINISTRAR › Lista de materiales): las piezas sólidas del modelo agrupadas (cuerpos iguales del mismo componente y material = una fila con su cantidad), con material, masa (g) y volumen (mm³) por unidad. Como en la ventana, un cuerpo sin material cuenta como Acero (default_material=true). El patrón plano de una chapa no es una pieza. Con csv_path, la escribe además en CSV.

- Modifica el documento: no.
- Parámetros:
  - `csv_path` (texto; opcional, por defecto `null`): ruta de un .csv donde escribir la lista (columnas como la de la ventana); vacío = no escribe.
  - `overwrite` (true/false; opcional, por defecto `false`): true para reemplazar el .csv si ya existe.
- CLI: `omnicad call get_bill_of_materials --doc pieza.omnicad`

### `set_appearance`

Cambia cómo se ven cuerpos o CARAS (MODIFICAR › Aspecto, «Aplicar a»: Cuerpos/componentes o Caras): un aspecto del diseño, de la biblioteca o de Mis aspectos (appearance, p. ej. 'Aluminio - Anodizado (rojo)', 'Hormigón - Liso'; list_appearances los lista) y/o un color propio (color «#rrggbb» o [r, g, b]). Con los dos, el acabado del aspecto con ese color. Con solo el color, pinta con un color suelto. Sin ninguno, quita el aspecto (vuelve al color del material, o al del cuerpo en las caras). No cambia la masa.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos (Aplicar a: Cuerpos/componentes).
  - `appearance` (texto; opcional, por defecto `null`): nombre o id de un aspecto del diseño, de la biblioteca o de Mis aspectos (sin distinguir mayúsculas); vacío = solo el color.
  - `color` (texto o lista de número o null; opcional, por defecto `null`): color propio «#rrggbb» o [r, g, b] (0..1 o 0..255); vacío = el del aspecto.
  - `faces` (texto o lista de texto o null; opcional, por defecto `null`): caras en vez de cuerpos (Aplicar a: Caras): selector (">Z"), id de find_faces ("Cuerpo1/F6") o lista de ellos.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que se evalúan los selectores de faces; vacío = el único cuerpo del documento.
- CLI: `omnicad call set_appearance --doc pieza.omnicad`

### `list_appearances`

Lista aspectos con todas sus propiedades: los del diseño («En este diseño», con id y quién los usa), los de la biblioteca (por familia: Metal, Plástico, Cristal, Madera, Piedra, Hormigón…), «Mis aspectos» o los favoritos. No cambia el documento.

- Modifica el documento: no.
- Parámetros:
  - `scope` ("design" | "library" | "mine" | "favorites" | "all"; opcional, por defecto `"design"`): design (En este diseño), library (biblioteca de OmniCAD), mine (Mis aspectos), favorites o all.
  - `query` (texto; opcional, por defecto `null`): texto a buscar en el nombre o la familia (sin distinguir mayúsculas); vacío = todos.
- CLI: `omnicad call list_appearances --doc pieza.omnicad`

### `edit_appearance`

Edita un aspecto (el «Editor de materiales» de Fusion) o crea uno nuevo: color, reflectancia, aspereza, metálico, transparencia, translucidez, emisividad, relieve, corte y resaltes. En el diseño, todos los cuerpos y caras que lo usan se ven con el cambio al instante. Con un aspecto de la biblioteca o de Mis aspectos, hace una copia en el diseño («X (1)») sin tocar el original. create=true crea uno nuevo (partiendo de base). scope=mine lo guarda en Mis aspectos.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `appearance` (texto; obligatorio): nombre o id del aspecto a editar (o el nombre del nuevo con create=true).
  - `scope` ("design" | "mine"; opcional, por defecto `"design"`): design (En este diseño, por defecto) o mine (Mis aspectos).
  - `create` (true/false; opcional, por defecto `false`): true crea un aspecto nuevo llamado appearance; falla si ya existe.
  - `base` (texto; opcional, por defecto `null`): con create, el aspecto del que parte (diseño, Mis aspectos o biblioteca); vacío = gris liso.
  - `name` (texto; opcional, por defecto `null`): nombre nuevo (renombra).
  - `color` (texto o lista de número o null; opcional, por defecto `null`): color «#rrggbb» o [r, g, b] (0..1 o 0..255).
  - `reflectance` (número; opcional, por defecto `null`): reflectancia de 0 a 1 (Fresnel: 0,05 en plásticos).
  - `roughness` (número; opcional, por defecto `null`): aspereza de 0 (espejo) a 1 (mate).
  - `metallic` (número; opcional, por defecto `null`): 0 a 1.
  - `transparency` (número; opcional, por defecto `null`): 0 (opaco) a 1 (transparente).
  - `varnish` (número; opcional, por defecto `null`): capa de barniz de 0 a 1.
  - `translucency` (true/false; opcional, por defecto `null`): activa la translucidez.
  - `translucency_depth` (número; opcional, por defecto `null`): profundidad de la translucidez en mm.
  - `translucency_color` (texto o lista de número o null; opcional, por defecto `null`): color del grosor translúcido.
  - `emissive` (true/false; opcional, por defecto `null`): activa la emisividad (el material emite luz).
  - `luminance` (número; opcional, por defecto `null`): luminancia en cd/m².
  - `filter_color` (texto o lista de número o null; opcional, por defecto `null`): color de filtro de la emisividad.
  - `bump_image` (texto; opcional, por defecto `null`): ruta de la imagen del patrón de relieve; "" la quita.
  - `bump_amount` (número; opcional, por defecto `null`): intensidad del relieve de 0 a 10.
  - `cutout_image` (texto; opcional, por defecto `null`): ruta de la imagen del patrón de corte; "" la quita.
  - `anisotropy` (número; opcional, por defecto `null`): anisotropía de los resaltes de 0 a 1.
  - `orientation` (número; opcional, por defecto `null`): orientación de los resaltes en grados.
  - `highlight_color` (texto o lista de número o null; opcional, por defecto `null`): color de los resaltes.
  - `highlight_shape` ("Difuminación larga" | "Difuminación corta" | "Nítida" o null; opcional, por defecto `null`): forma del resalte: Difuminación larga, Difuminación corta o Nítida.
  - `category` (texto; opcional, por defecto `null`): familia de la biblioteca (Metal, Plástico, Cristal, Madera, Piedra, Hormigón, Otro…).
- CLI: `omnicad call edit_appearance --doc pieza.omnicad appearance=…`

### `manage_appearance`

Administra un aspecto como el menú de «En este diseño» de Fusion: duplicate (copia con nombre «X (1)»), delete (Suprimir; si lo usan cuerpos o caras pide remove_users=true), rename, copy_to_mine (Copiar en Mis aspectos), add_favorite / remove_favorite (Añadir a Favoritos) y delete_mine (borra uno de Mis aspectos).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `action` ("duplicate" | "delete" | "rename" | "copy_to_mine" | "add_favorite" | "remove_favorite" | "delete_mine"; obligatorio): duplicate, delete, rename, copy_to_mine, add_favorite, remove_favorite o delete_mine.
  - `appearance` (texto; obligatorio): nombre o id del aspecto (del diseño; los favoritos y delete_mine usan el nombre de la biblioteca o de Mis aspectos).
  - `name` (texto; opcional, por defecto `null`): nombre nuevo (rename) o del duplicado (duplicate).
  - `remove_users` (true/false; opcional, por defecto `false`): con delete, true saca también el aspecto de los cuerpos y caras que lo usan.
- CLI: `omnicad call manage_appearance --doc pieza.omnicad action=… appearance=…`

### `list_plastic_rules`

Reglas de plástico (PLÁSTICO › Administrar reglas) con todos sus valores: material, espesor, ángulo de desmoldeo, radio nominal y los valores de Design Advice (rango de espesor, variación, ángulo mínimo, umbral de filo). Las de fábrica (builtin), las propias del usuario (user) y a qué componentes de este documento está asignada cada una.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call list_plastic_rules --doc pieza.omnicad`

### `create_plastic_rule`

Crea una regla de plástico propia (PLÁSTICO › Administrar reglas › Nueva regla) y la deja en la biblioteca del usuario. Lo que no se da sigue al espesor como en las de fábrica (radio nominal = espesor / 2, rango de espesor de 0,5 a 1,5 veces, umbral de filo = un cuarto). No pisa las de fábrica. No cambia el documento.

- Modifica el documento: no.
- Parámetros:
  - `name` (texto; obligatorio): nombre de la regla (p. ej. "ABS 2.5 mm").
  - `thickness` (número; obligatorio): espesor de pared en mm.
  - `material` (texto; opcional, por defecto `null`): material físico (list_materials); vacío = sin material.
  - `draft_angle` (número; opcional, por defecto `1.0`): ángulo de desmoldeo en grados (0 a 45).
  - `nominal_radius` (número; opcional, por defecto `null`): radio nominal de los empalmes en mm; vacío = espesor / 2.
  - `min_thickness` (número; opcional, por defecto `null`): espesor mínimo que acepta Design Advice, en mm; vacío = la mitad del espesor.
  - `max_thickness` (número; opcional, por defecto `null`): espesor máximo, en mm; vacío = 1,5 veces el espesor.
  - `thickness_variation` (número; opcional, por defecto `25.0`): variación de espesor tolerada, en porcentaje.
  - `min_draft_angle` (número; opcional, por defecto `0.5`): ángulo de desmoldeo mínimo, en grados.
  - `knife_edge` (número; opcional, por defecto `null`): umbral de filo en mm; vacío = un cuarto del espesor.
  - `overwrite` (true/false; opcional, por defecto `false`): true para reemplazar una regla propia que ya existe con ese nombre.
  - `save` (true/false; opcional, por defecto `true`): true la guarda en la biblioteca del usuario para las próximas sesiones; false, solo en esta sesión.
- CLI: `omnicad call create_plastic_rule --doc pieza.omnicad name=… thickness=…`

### `delete_plastic_rule`

Borra una regla de plástico propia de la biblioteca del usuario (las de fábrica no se borran). Los componentes que ya la tienen asignada conservan su copia.

- Modifica el documento: no.
- Parámetros:
  - `name` (texto; obligatorio): nombre de la regla propia.
  - `save` (true/false; opcional, por defecto `true`): true también la saca del archivo de la biblioteca; false, solo de esta sesión.
- CLI: `omnicad call delete_plastic_rule --doc pieza.omnicad name=…`

## Grupo inspeccion

Ver y medir el resultado.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`thread_info`](#thread_info) | no | Datos de roscas normalizadas (no cambia el documento). |
| [`fit_tolerance`](#fit_tolerance) | no | Ajuste ISO 286 entre un agujero y un eje (no cambia el documento): desviaciones y medidas límite de cada uno, juego máximo y mínimo (negativo = apriete) y tipo de ajuste (clearance, transition o interference). |
| [`manage_analysis`](#manage_analysis) | sí | Carpeta «Análisis» del documento: agrega, lista, muestra, oculta y quita análisis de INSPECCIONAR: sección, cebra, mapa de entorno, desmoldeo, curvatura, peine de curvatura, isocurvas, accesibilidad y radio mínimo. |
| [`analyze_geometry`](#analyze_geometry) | no | Mide con un análisis de INSPECCIONAR sin guardarlo: section (área y contorno), curvature (mínimo, máximo, media y percentiles), draft (ángulos y porcentaje de caras con desmoldeo suficiente), accessibility (porcentaje accesible), min_radius (porcentaje que la fresa no alcanza) e isocurve. |
| [`section_view`](#section_view) | sí | Análisis de sección: corta con un plano (XY, XZ, YZ, un plano de construcción o una cara plana), lo guarda en la carpeta «Análisis» y devuelve el área y el contorno de cada cuerpo. get_viewport_image dibuja la parte de atrás del plano con su tapa. show=false lo deja oculto; manage_analysis (hide o remove) lo apaga. |
| [`set_visual_style`](#set_visual_style) | sí | Guarda el estilo visual del visor: uno de los seis de Fusion (shaded, shaded_hidden_edges, shaded_visible_edges, wireframe, wireframe_hidden_edges, wireframe_visible_edges), el entorno de iluminación y los efectos (sombras, reflejos, oclusión ambiental y suelo). get_viewport_image lo usa cuando no se le pide otro estilo. |
| [`get_viewport_image`](#get_viewport_image) | no | Renderiza el modelo y devuelve una imagen PNG (sombreado, sombras y suelo) desde una vista estándar o una dirección propia. |
| [`get_physical_properties`](#get_physical_properties) | no | Volumen (mm³), área (mm²), masa (g), centro de masa y caja envolvente de cada cuerpo y del total. |
| [`measure_distance`](#measure_distance) | no | Distancia mínima entre dos cosas, cada una un cuerpo, una cara, una arista o un punto. |
| [`check_interference`](#check_interference) | no | Busca pares de cuerpos sólidos que se superponen y devuelve cada par con el volumen común (mm³) y su caja envolvente. |
| [`find_faces`](#find_faces) | no | Lista las caras de un cuerpo (o de todos), opcionalmente filtradas por un selector. |
| [`find_edges`](#find_edges) | no | Lista las aristas de un cuerpo (o de todos), opcionalmente filtradas por un selector. |
| [`measure_angle`](#measure_angle) | no | Ángulo (grados) entre dos caras planas, dos aristas rectas, o una cara y una arista. |
| [`design_advice`](#design_advice) | no | Consejos de diseño para moldeo por inyección (Plástico › Inspeccionar › Design Advice): revisa un cuerpo contra una regla de plástico y la dirección de extracción del molde. |
| [`find_features`](#find_features) | no | Reconoce las funciones que forman un cuerpo sin historial, por ejemplo uno importado (SÓLIDO › CREAR › Reconocer funciones): agujeros (diámetro, profundidad, pasante, avellanado, punto de entrada), empalmes (radio, convexo o cóncavo), chaflanes (ancho, ángulo y distancia), extrusión (el cuerpo entero es un prisma: dirección, distancia y área del perfil), revolución (todas las caras giran alrededor de un eje: eje y ángulo) y grupos de agujeros, empalmes o chaflanes iguales: patrón rectangular (direcciones, cantidad y paso), circular (eje, cantidad y paso angular) o simetría (plano X, Y o Z por el centro de la caja del cuerpo). |
| [`check_geometry`](#check_geometry) | no | Revisa la geometría de un cuerpo (o de todos), como Check Geometry de FreeCAD: si el kernel lo da por válido (y qué falla si no), si es estanco, aristas libres (abiertas) y no manifold, autointersecciones, caras degeneradas, aristas diminutas y tolerancias máximas; en mallas, bordes abiertos, no manifold, normales invertidas y triángulos degenerados. |
| [`check_printability`](#check_printability) | no | Revisión de impresión 3D de un cuerpo (o de todos), como la caja de herramientas de impresión 3D de Blender: si es estanco, espesor mínimo de pared (rayos hacia adentro desde la superficie; zonas más finas que min_thickness), zonas en voladizo que necesitan soportes (más de overhang_angle desde la vertical, sin contar la cara apoyada en la cama: el plano Z más bajo del cuerpo) y aristas filosas (ángulo interior menor que sharp_angle). printable = estanco y sin paredes finas. |
| [`repair_body`](#repair_body) | sí | Repara un cuerpo y deja un paso «Reparar cuerpo» en el timeline (editable; un paso de deshacer): cose las aristas abiertas (si queda estanco pasa a sólido), baja las tolerancias mayores que tolerance, corrige con ShapeFix (orientación de caras, contornos) y refina (une caras coplanares). |
| [`find_similar_components`](#find_similar_components) | no | Busca componentes con geometría parecida (INSPECCIONAR › Buscar componentes similares). |
| [`set_view`](#set_view) | sí | Guarda la cámara del visor: vista, órbita, proyección, zoom y objetivo. |
| [`manage_named_views`](#manage_named_views) | sí | Lista, guarda, aplica, renombra o elimina vistas con nombre compatibles con el navegador de la ventana. |
| [`set_grid`](#set_grid) | sí | Guarda mostrar rejilla, forzar a la rejilla y cuatro vistas. |
| [`capture_viewport`](#capture_viewport) | no | Captura la vista 3D REAL de la ventana de OmniCAD tal como la ve la persona: cámara, estilo visual, entorno, selección y análisis mostrados. |

### `thread_info`

Datos de roscas normalizadas (no cambia el documento). Sin argumentos: los tipos (familias) con su norma, ángulo de perfil y clases. Con family: sus tamaños y designaciones. Con thread: diámetro mayor, paso, diámetros de flancos y menor básicos, broca para roscar, agujero de paso ISO 273 (métricas) y, con thread_class, los diámetros límite de la clase (ISO 965-1 o ASME B1.1; 'auto' da los de las dos clases por defecto). Todo en mm.

- Modifica el documento: no.
- Parámetros:
  - `thread` (texto; opcional, por defecto `null`): designación ("M10", "M10x1.25", "1/4-20 UNC", "Tr20x4", "1/2-10 ACME", "G1/2", "R1/2", "1/2 NPT").
  - `family` ("iso_metric" | "unified" | "trapezoidal" | "acme" | "bsp_parallel" | "bsp_taper" | "npt" o null; opcional, por defecto `null`): tipo de rosca cuyos tamaños listar: iso_metric, unified, trapezoidal, acme, bsp_parallel, bsp_taper o npt.
  - `thread_class` (texto; opcional, por defecto `null`): clase para los diámetros límite: "6g", "6H", "2A", "2B"…, o "auto" (las dos por defecto).
- CLI: `omnicad call thread_info --doc pieza.omnicad`

### `fit_tolerance`

Ajuste ISO 286 entre un agujero y un eje (no cambia el documento): desviaciones y medidas límite de cada uno, juego máximo y mínimo (negativo = apriete) y tipo de ajuste (clearance, transition o interference). Hay grados IT5 a IT11 hasta 500 mm; agujeros D, E, F, G, H y ejes d, e, f, g, h, j6, k, n, p, s. Ej.: nominal=25, hole='H7', shaft='g6'. Todo en mm.

- Modifica el documento: no.
- Parámetros:
  - `nominal` (número; obligatorio): medida nominal en mm (más de 0 y hasta 500).
  - `hole` (texto; opcional, por defecto `"H7"`): clase del agujero, letra mayúscula y grado: "H7", "H8", "H11", "G7", "F8"…
  - `shaft` (texto; opcional, por defecto `"g6"`): clase del eje, letra minúscula y grado: "g6", "h6", "h7", "f7", "k6", "n6", "p6", "s6", "j6"…
- CLI: `omnicad call fit_tolerance --doc pieza.omnicad nominal=…`

### `manage_analysis`

Carpeta «Análisis» del documento: agrega, lista, muestra, oculta y quita análisis de INSPECCIONAR: sección, cebra, mapa de entorno, desmoldeo, curvatura, peine de curvatura, isocurvas, accesibilidad y radio mínimo. Los visibles se dibujan en get_viewport_image. Para los números (áreas, ángulos, curvaturas) usá analyze_geometry. Admite deshacer.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `action` ("list" | "add" | "remove" | "show" | "hide"; opcional, por defecto `"list"`): list (los del documento), add (crea uno), remove, show o hide (por name).
  - `type` ("section" | "zebra" | "environment_map" | "draft" | "curvature" | "comb" | "isocurve" | "accessibility" | "min_radius" o null; opcional, por defecto `null`): con add: section (corte con plano), zebra, environment_map, draft (desmoldeo), curvature, comb (peine de curvatura de aristas), isocurve, accessibility o min_radius (fresa).
  - `name` (texto; opcional, por defecto `null`): nombre del análisis (con add, vacío = automático, p. ej. «Sección1»).
  - `bodies` (lista de texto o null; opcional, por defecto `null`): cuerpos que se analizan (id o nombre); vacío = todos los sólidos. Para section, draft, curvature, isocurve, accessibility y min_radius.
  - `plane` (texto o objeto; opcional, por defecto `null`): section: XY, XZ, YZ, un plano de construcción (id o nombre) o una cara plana (selector).
  - `offset` (número; opcional, por defecto `null`): section: desfase del plano en mm sobre su normal; 0 por defecto.
  - `flip` (true/false; opcional, por defecto `null`): section: conserva el otro lado; draft y accessibility: invierte la dirección.
  - `frequency` (entero; opcional, por defecto `null`): zebra: cantidad de franjas (1 a 100); 8 por defecto.
  - `orientation` ("horizontal" | "vertical" o null; opcional, por defecto `null`): zebra: horizontal (por defecto) o vertical.
  - `direction` (texto o objeto; opcional, por defecto `null`): draft y accessibility: "x", "y", "z", un eje, una arista recta o una cara plana (hacia afuera del material); vacío = +Z.
  - `min_angle` (número; opcional, por defecto `null`): draft: ángulo en grados bajo el cual la cara se pinta de rojo; 0 por defecto.
  - `max_angle` (número; opcional, por defecto `null`): draft: ángulo en grados desde el cual la cara se pinta de verde; 3 por defecto.
  - `curvature_type` ("gaussian" | "mean" | "max" | "min" o null; opcional, por defecto `null`): curvature: gaussian (por defecto), mean, max o min.
  - `edges` (texto o lista de texto o null; opcional, por defecto `null`): comb: aristas (selector o ids de find_edges, o lista).
  - `density` (entero; opcional, por defecto `null`): comb: púas por arista (30 por defecto); isocurve: curvas por dirección (10 por defecto).
  - `scale` (número; opcional, por defecto `null`): comb: largo de las púas (1 por defecto).
  - `radius` (número; opcional, por defecto `null`): min_radius: radio de la fresa en mm (3 por defecto).
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de plane, direction y edges; vacío = el único cuerpo.
- CLI: `omnicad call manage_analysis --doc pieza.omnicad`

### `analyze_geometry`

Mide con un análisis de INSPECCIONAR sin guardarlo: section (área y contorno), curvature (mínimo, máximo, media y percentiles), draft (ángulos y porcentaje de caras con desmoldeo suficiente), accessibility (porcentaje accesible), min_radius (porcentaje que la fresa no alcanza) e isocurve. Por cuerpo. Los análisis puramente visuales (zebra, environment_map, comb) se ven con manage_analysis y get_viewport_image.

- Modifica el documento: no.
- Parámetros:
  - `type` ("section" | "curvature" | "draft" | "accessibility" | "min_radius" | "isocurve"; obligatorio): section, curvature, draft, accessibility, min_radius o isocurve.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): cuerpos a medir (id o nombre); vacío = todos los sólidos.
  - `plane` (texto o objeto; opcional, por defecto `null`): section: XY, XZ, YZ, un plano de construcción o una cara plana.
  - `offset` (número; opcional, por defecto `null`): section: desfase del plano en mm; 0 por defecto.
  - `flip` (true/false; opcional, por defecto `null`): draft y accessibility: invierte la dirección.
  - `direction` (texto o objeto; opcional, por defecto `null`): draft y accessibility: "x", "y", "z", un eje, una arista recta o una cara plana; vacío = +Z.
  - `min_angle` (número; opcional, por defecto `null`): draft: ángulo en grados bajo el cual el desmoldeo es insuficiente; 0 por defecto.
  - `max_angle` (número; opcional, por defecto `null`): draft: ángulo en grados desde el cual es suficiente; 3 por defecto.
  - `curvature_type` ("gaussian" | "mean" | "max" | "min" o null; opcional, por defecto `null`): curvature: gaussian (por defecto), mean, max o min.
  - `density` (entero; opcional, por defecto `null`): isocurve: curvas por dirección; 10 por defecto.
  - `radius` (número; opcional, por defecto `null`): min_radius: radio de la fresa en mm; 3 por defecto.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de plane y direction; vacío = el único cuerpo.
- CLI: `omnicad call analyze_geometry --doc pieza.omnicad type=…`

### `section_view`

Análisis de sección: corta con un plano (XY, XZ, YZ, un plano de construcción o una cara plana), lo guarda en la carpeta «Análisis» y devuelve el área y el contorno de cada cuerpo. get_viewport_image dibuja la parte de atrás del plano con su tapa. show=false lo deja oculto; manage_analysis (hide o remove) lo apaga.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `plane` (texto o objeto; obligatorio): XY, XZ, YZ, un plano de construcción (id o nombre) o una cara plana (selector).
  - `offset` (número; opcional, por defecto `0`): desfase del plano en mm sobre su normal.
  - `flip` (true/false; opcional, por defecto `false`): true conserva el lado de la normal en vez del lado de atrás.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): cuerpos a cortar (id o nombre); vacío = todos los sólidos.
  - `name` (texto; opcional, por defecto `null`): nombre del análisis; vacío = automático (Sección1…).
  - `show` (true/false; opcional, por defecto `true`): false deja el análisis creado pero oculto.
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúa el selector de plane; vacío = el único cuerpo.
  - `angle` (número; opcional, por defecto `0`): giro del plano en grados (entre −360 y 360) alrededor de su eje u, después del desfase.
- CLI: `omnicad call section_view --doc pieza.omnicad plane=…`

### `set_visual_style`

Guarda el estilo visual del visor: uno de los seis de Fusion (shaded, shaded_hidden_edges, shaded_visible_edges, wireframe, wireframe_hidden_edges, wireframe_visible_edges), el entorno de iluminación y los efectos (sombras, reflejos, oclusión ambiental y suelo). get_viewport_image lo usa cuando no se le pide otro estilo. Sin parámetros solo lo consulta; clear=true vuelve a los valores de fábrica. Admite deshacer.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `style` ("shaded" | "shaded_hidden_edges" | "shaded_visible_edges" | "wireframe" | "wireframe_hidden_edges" | "wireframe_visible_edges" o null; opcional, por defecto `null`): shaded, shaded_hidden_edges (sombreado con aristas ocultas), shaded_visible_edges (sombreado con solo aristas visibles), wireframe, wireframe_hidden_edges o wireframe_visible_edges.
  - `environment` (texto; opcional, por defecto `null`): entorno de iluminación (clave de render_cpu.ENTORNOS, p. ej. fotomaton o tema).
  - `shadows` (true/false; opcional, por defecto `null`): sombras del suelo.
  - `reflections` (true/false; opcional, por defecto `null`): reflejos en el suelo.
  - `ambient_occlusion` (true/false; opcional, por defecto `null`): oclusión ambiental.
  - `ground_plane` (true/false; opcional, por defecto `null`): plano de suelo que recibe las sombras.
  - `clear` (true/false; opcional, por defecto `false`): true borra el estilo guardado y vuelve a los valores de fábrica.
- CLI: `omnicad call set_visual_style --doc pieza.omnicad`

### `get_viewport_image`

Renderiza el modelo y devuelve una imagen PNG (sombreado, sombras y suelo) desde una vista estándar o una dirección propia. Usa Rust si está disponible, con respaldo Python (OMNICAD_SIN_RUST=1 lo fuerza). Es la forma de VER el resultado.

- Modifica el documento: no.
- Parámetros:
  - `view` (texto; opcional, por defecto `null`): vista estándar: las caras del ViewCube de Fusion con Z arriba, nombradas por los ejes del MUNDO (no por el frente de la pieza). "front": cámara en -Y, se ve la cara -Y con +X a la derecha; "back": cámara en +Y; "right": cámara en +X, se ve la cara +X con +Y a la derecha; "left": cámara en -X; "top": cámara en +Z, X a la derecha e Y hacia arriba; "bottom": cámara en -Z; "iso": esquina frente-derecha-arriba. Si la pieza mira hacia otro eje, usá direction. También acepta nombres de vistas guardadas; omitida usa set_view o iso.
  - `width` (entero; opcional, por defecto `640`): ancho de la imagen en píxeles (16 a 2048).
  - `height` (entero; opcional, por defecto `480`): alto de la imagen en píxeles (16 a 2048).
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos a dibujar (también los ocultos); vacío = todos los visibles.
  - `fit` (true/false; opcional, por defecto `true`): true encuadra los cuerpos dibujados; false encuadra TODA la escena aunque se dibuje solo una parte (sirve para comparar imágenes con el mismo encuadre).
  - `direction` (lista de número o null; opcional, por defecto `null`): [x, y, z] vector desde el modelo HACIA la cámara (Z es arriba); si se pasa, reemplaza a view.
  - `lighting` ("three_point" | "key_only"; opcional, por defecto `"three_point"`): "three_point" (por defecto) = iluminación de tres puntos (luz principal, relleno y contorno); "key_only" = solo la luz principal. No depende de Preferencias › Gráficos › «Iluminación de la vista» (esa opción es la del visor de la ventana).
  - `camera` ("perspective" | "orthographic" o null; opcional, por defecto `null`): perspective u orthographic; omitida conserva la cámara guardada o usa perspectiva.
  - `component_colors` (true/false; opcional, por defecto `false`): pinta cada componente con un color de la paleta del visor; las piezas sueltas conservan su aspecto.
  - `style` ("shaded" | "shaded_hidden_edges" | "shaded_visible_edges" | "wireframe" | "wireframe_hidden_edges" | "wireframe_visible_edges" o null; opcional, por defecto `null`): estilo visual (los seis de Fusion: shaded, shaded_hidden_edges, shaded_visible_edges, wireframe, wireframe_hidden_edges, wireframe_visible_edges); omitido usa el de set_visual_style (shaded de fábrica). Las aristas son las exactas de los cuerpos: una malla no las tiene.
  - `analysis` (lista de texto o null; opcional, por defecto `null`): nombres de los análisis a dibujar (manage_analysis los lista); [] ninguno; omitido dibuja los visibles del documento, como la ventana.
- CLI: `omnicad call get_viewport_image --doc pieza.omnicad`

### `get_physical_properties`

Volumen (mm³), área (mm²), masa (g), centro de masa y caja envolvente de cada cuerpo y del total. La masa necesita una densidad: la que se pasa, o la del material físico asignado al cuerpo.

- Modifica el documento: no.
- Parámetros:
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos; vacío = todos.
  - `density` (número; opcional, por defecto `null`): densidad en g/cm³ para todos los cuerpos con volumen; vacío = la de su material físico.
- CLI: `omnicad call get_physical_properties --doc pieza.omnicad`

### `measure_distance`

Distancia mínima entre dos cosas, cada una un cuerpo, una cara, una arista o un punto. Caras y aristas se dan por id (find_faces / find_edges) o por selector (>Z elige sobre las caras; edges:|Z sobre las aristas; con varios cuerpos, body dice en cuál se evalúan los selectores). Devuelve la distancia (mm), los dos puntos más cercanos y el desfase XYZ de a hacia b; con center_to_center, la de centro a centro.

- Modifica el documento: no.
- Parámetros:
  - `a` (texto o lista de número; obligatorio): cuerpo (id o nombre), cara o arista (id "Cuerpo1/F3" o selector ">Z", "edges:|Z") o punto [x, y, z] en mm.
  - `b` (texto o lista de número; obligatorio): cuerpo (id o nombre), cara o arista (id "Cuerpo1/F3" o selector ">Z", "edges:|Z") o punto [x, y, z] en mm.
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo donde se evalúan los selectores de a y b; vacío = el único cuerpo. Los ids y los nombres de cuerpo no lo necesitan.
  - `center_to_center` (true/false; opcional, por defecto `false`): true mide de centro a centro (opción «Centro a centro» de Fusion): a y b tienen que ser círculos, arcos o cilindros; distance y los puntos son entonces los de los centros, y se agrega center_to_center con las distancias mínima y máxima según los diámetros.
- CLI: `omnicad call measure_distance --doc pieza.omnicad a=… b=…`

### `check_interference`

Busca pares de cuerpos sólidos que se superponen y devuelve cada par con el volumen común (mm³) y su caja envolvente. Los que solo se tocan por una cara no cuentan, salvo con coincident_faces.

- Modifica el documento: no.
- Parámetros:
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos a comparar entre sí; vacío = todos los sólidos.
  - `coincident_faces` (true/false; opcional, por defecto `false`): true también informa los pares que solo se tocan por caras coincidentes (opción «Incluir caras coincidentes»): volume 0, area de contacto y coincident=true.
- CLI: `omnicad call check_interference --doc pieza.omnicad`

### `find_faces`

Lista las caras de un cuerpo (o de todos), opcionalmente filtradas por un selector. Selector estilo CadQuery: >Z <Z (centro más alto/bajo), |Z (aristas paralelas al eje; caras con la normal paralela), #Z (perpendicular), +Z -Z (normal de caras planas), |Z~3 #Z~3 (lo mismo con 3° de tolerancia, para lo apenas inclinado, p. ej. tras un desmoldeo), %PLANE %CYLINDER %CIRCLE %LINE (tipo), nearest:[x,y,z], combinables con and, or, not y paréntesis (get_guide topic=selectores). Cada elemento trae un id corto (p. ej. 'Cuerpo1/F3') VÁLIDO HASTA EL PRÓXIMO CAMBIO DEL DOCUMENTO (un id viejo da STALE_ID); fillet, chamfer, shell, create_hole y create_sketch lo aceptan, o aceptan el selector directamente. Sin coincidencias da NO_MATCH. Cada cara trae tipo (plane, cylinder, cone, sphere, torus, bspline), área (mm²), centro, normal (planas) o eje (cilindros y conos), radio y, en las planas, center_uv: el centro en los ejes x,y de un boceto sobre esa cara.

- Modifica el documento: no.
- Parámetros:
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo; vacío = todos los cuerpos.
  - `selector` (texto; opcional, por defecto `null`): filtro estilo CadQuery, p. ej. ">Z" (la tapa), "#Z" (las laterales), "%CYLINDER"; vacío = todas.
- CLI: `omnicad call find_faces --doc pieza.omnicad`

### `find_edges`

Lista las aristas de un cuerpo (o de todos), opcionalmente filtradas por un selector. Selector estilo CadQuery: >Z <Z (centro más alto/bajo), |Z (aristas paralelas al eje; caras con la normal paralela), #Z (perpendicular), +Z -Z (normal de caras planas), |Z~3 #Z~3 (lo mismo con 3° de tolerancia, para lo apenas inclinado, p. ej. tras un desmoldeo), %PLANE %CYLINDER %CIRCLE %LINE (tipo), nearest:[x,y,z], combinables con and, or, not y paréntesis (get_guide topic=selectores). Cada elemento trae un id corto (p. ej. 'Cuerpo1/F3') VÁLIDO HASTA EL PRÓXIMO CAMBIO DEL DOCUMENTO (un id viejo da STALE_ID); fillet, chamfer, shell, create_hole y create_sketch lo aceptan, o aceptan el selector directamente. Sin coincidencias da NO_MATCH. Cada arista trae tipo (line, circle, ellipse, bspline), largo (mm), centro, dirección (rectas) y radio (círculos).

- Modifica el documento: no.
- Parámetros:
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo; vacío = todos los cuerpos.
  - `selector` (texto; opcional, por defecto `null`): filtro estilo CadQuery, p. ej. "|Z" (las verticales), ">Z" (las de arriba), "%CIRCLE"; vacío = todas.
- CLI: `omnicad call find_edges --doc pieza.omnicad`

### `measure_angle`

Ángulo (grados) entre dos caras planas, dos aristas rectas, o una cara y una arista. Cara-cara: ángulo entre las normales exteriores (0 a 180; dos caras de una caja que se tocan en una arista dan 90), más acute_angle (0 a 90). Arista-arista y cara-arista: ángulo agudo (0 a 90), porque una arista no tiene sentido. Cada lado es un id de find_faces / find_edges o un selector (sobre caras; edges:|Z para aristas) que elija UNA sola; con varios cuerpos, body dice en cuál se evalúan los selectores.

- Modifica el documento: no.
- Parámetros:
  - `a` (texto; obligatorio): cara o arista: id ("Cuerpo1/F3") o selector (">Z", "edges:|Z").
  - `b` (texto; obligatorio): cara o arista: id ("Cuerpo1/F3") o selector (">X", "edges:|X").
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo donde se evalúan los selectores de a y b; vacío = el único cuerpo. Los ids no lo necesitan.
- CLI: `omnicad call measure_angle --doc pieza.omnicad a=… b=…`

### `design_advice`

Consejos de diseño para moldeo por inyección (Plástico › Inspeccionar › Design Advice): revisa un cuerpo contra una regla de plástico y la dirección de extracción del molde. Devuelve alertas por cara de espesor (too_thin, too_thick, variation), contrasalidas (undercut), desmoldeo insuficiente (draft) y filos (knife_edge), cada una con su consejo, y un resumen por tipo. Usa la regla asignada al componente del cuerpo, o la de rule, o «ABS 2 mm». Mide con rayos sobre 3×3 puntos por cara: es una revisión por regiones, no una simulación. No cambia el documento.

- Modifica el documento: no.
- Parámetros:
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo sólido; vacío = el único cuerpo.
  - `pull_direction` ("X" | "Y" | "Z"; opcional, por defecto `"Z"`): eje del origen que define la dirección de extracción: X, Y o Z.
  - `flip` (true/false; opcional, por defecto `false`): true invierte la dirección de extracción.
  - `rule` (texto; opcional, por defecto `null`): nombre de la regla de plástico (list_plastic_rules) si el componente del cuerpo no tiene una asignada; vacío = "ABS 2 mm".
  - `ignore` (lista de "thickness" | "undercut" | "draft" | "knife_edge" o null; opcional, por defecto `null`): tipos de alerta que se omiten del resultado (thickness agrupa too_thin, too_thick y variation).
- CLI: `omnicad call design_advice --doc pieza.omnicad`

### `find_features`

Reconoce las funciones que forman un cuerpo sin historial, por ejemplo uno importado (SÓLIDO › CREAR › Reconocer funciones): agujeros (diámetro, profundidad, pasante, avellanado, punto de entrada), empalmes (radio, convexo o cóncavo), chaflanes (ancho, ángulo y distancia), extrusión (el cuerpo entero es un prisma: dirección, distancia y área del perfil), revolución (todas las caras giran alrededor de un eje: eje y ángulo) y grupos de agujeros, empalmes o chaflanes iguales: patrón rectangular (direcciones, cantidad y paso), circular (eje, cantidad y paso angular) o simetría (plano X, Y o Z por el centro de la caja del cuerpo). Cada función trae los ids de sus caras (find_faces). Solo lee: rebuild_features rehace en el timeline los agujeros, empalmes y chaflanes. No cambia el documento.

- Modifica el documento: no.
- Parámetros:
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo sólido; vacío = el único cuerpo.
  - `types` (lista de "hole" | "fillet" | "chamfer" | "extrude" | "revolve" | "mirror" | "circular_pattern" | "rectangular_pattern" o null; opcional, por defecto `null`): qué reconocer: hole, fillet, chamfer, extrude, revolve, mirror, circular_pattern, rectangular_pattern; vacío = todo.
- CLI: `omnicad call find_features --doc pieza.omnicad`

### `check_geometry`

Revisa la geometría de un cuerpo (o de todos), como Check Geometry de FreeCAD: si el kernel lo da por válido (y qué falla si no), si es estanco, aristas libres (abiertas) y no manifold, autointersecciones, caras degeneradas, aristas diminutas y tolerancias máximas; en mallas, bordes abiertos, no manifold, normales invertidas y triángulos degenerados. Cada problema trae kind, severity (error o warning), un mensaje y su posición [x, y, z]; max_tolerance es la mayor tolerancia del kernel por tipo. La búsqueda de autointersecciones en cuerpos con superficies B-spline (roscas modeladas) corre con tope de tiempo: si no termina, self_intersections queda en null y sale el aviso self_intersection_skipped. No cambia el documento: para arreglar, repair_body.

- Modifica el documento: no.
- Parámetros:
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo; vacío = todos los cuerpos del modelo.
  - `self_intersection` (true/false; opcional, por defecto `true`): true busca caras que se cortan entre sí (análisis booleano, lo más lento en piezas grandes; con superficies B-spline tiene tope de 10 s por cuerpo y 30 s en total).
  - `tolerance_limit` (número; opcional, por defecto `0.01`): tolerancia en mm de vértice, arista o cara por encima de la cual se avisa (high_tolerance).
  - `max_issues` (entero; opcional, por defecto `50`): cuántos problemas devolver por cuerpo como máximo; los conteos son siempre completos.
- CLI: `omnicad call check_geometry --doc pieza.omnicad`

### `check_printability`

Revisión de impresión 3D de un cuerpo (o de todos), como la caja de herramientas de impresión 3D de Blender: si es estanco, espesor mínimo de pared (rayos hacia adentro desde la superficie; zonas más finas que min_thickness), zonas en voladizo que necesitan soportes (más de overhang_angle desde la vertical, sin contar la cara apoyada en la cama: el plano Z más bajo del cuerpo) y aristas filosas (ángulo interior menor que sharp_angle). printable = estanco y sin paredes finas. Cada zona trae su posición. No cambia el documento.

- Modifica el documento: no.
- Parámetros:
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo; vacío = todos los cuerpos del modelo.
  - `min_thickness` (número; opcional, por defecto `0.8`): espesor de pared mínimo en mm (p. ej. 2 veces el diámetro de la boquilla); 0 no marca paredes.
  - `overhang_angle` (número; opcional, por defecto `45.0`): ángulo de voladizo en grados desde la vertical que se imprime sin soportes (0 a 90; 45 es lo habitual).
  - `sharp_angle` (número; opcional, por defecto `20.0`): ángulo interior en grados por debajo del cual una arista convexa es filosa (0 a 180).
  - `samples` (entero; opcional, por defecto `2000`): cantidad de rayos para medir el espesor (1 a 20000; más = más lento y más fino).
  - `max_issues` (entero; opcional, por defecto `50`): cuántos problemas devolver por cuerpo como máximo; los conteos son siempre completos.
- CLI: `omnicad call check_printability --doc pieza.omnicad`

### `repair_body`

Repara un cuerpo y deja un paso «Reparar cuerpo» en el timeline (editable; un paso de deshacer): cose las aristas abiertas (si queda estanco pasa a sólido), baja las tolerancias mayores que tolerance, corrige con ShapeFix (orientación de caras, contornos) y refina (une caras coplanares). En mallas: une vértices a menos de tolerance, corrige triángulos degenerados, orienta las normales y cierra agujeros. Devuelve el estado antes y después (valid, closed, free_edges, non_manifold_edges, max_tolerance); si sigue con problemas, lo dice en avisos.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `body` (texto; obligatorio): id o nombre del cuerpo a reparar.
  - `tolerance` (número o expresión; opcional, por defecto `"0.01 mm"`): tolerancia de reparación en mm (número o expresión): distancia para coser y tope de las tolerancias; 0 = sin tope.
  - `sew` (true/false; opcional, por defecto `true`): true cose las aristas libres (abiertas); en mallas siempre se cose.
  - `refine` (true/false; opcional, por defecto `true`): true une las caras coplanares y las aristas colineales (Refine Shape).
  - `fix` (true/false; opcional, por defecto `true`): true corrige con ShapeFix (orientación de caras, contornos, curvas sobre las caras).
- CLI: `omnicad call repair_body --doc pieza.omnicad body=…`

### `find_similar_components`

Busca componentes con geometría parecida (INSPECCIONAR › Buscar componentes similares). Compara volumen, área y momentos de inercia, que no cambian al mover o girar la pieza. Cada coincidencia trae status: duplicate (la misma geometría), highly_similar (hasta 5 % de diferencia) o similar (hasta 20 %). Sin component devuelve cada componente que tiene coincidencias; con component, solo las de ese. No cambia el documento.

- Modifica el documento: no.
- Parámetros:
  - `component` (texto; opcional, por defecto `null`): id o nombre del componente a comparar; vacío = todos los que tengan coincidencias.
- CLI: `omnicad call find_similar_components --doc pieza.omnicad`

### `set_view`

Guarda la cámara del visor: vista, órbita, proyección, zoom y objetivo. Admite deshacer y clear vuelve al encuadre automático.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `view` (texto; opcional, por defecto `"iso"`): vista estándar o nombre de una vista guardada.
  - `direction` (lista de número o null; opcional, por defecto `null`): vector [x, y, z] hacia la cámara; reemplaza a view.
  - `projection` ("perspective" | "orthographic"; opcional, por defecto `"perspective"`): perspective u orthographic.
  - `azimuth` (número; opcional, por defecto `0`): órbita horizontal en grados relativa a la vista indicada.
  - `elevation` (número; opcional, por defecto `0`): órbita vertical en grados relativa a la vista indicada.
  - `zoom` (número; opcional, por defecto `1`): factor positivo sobre la distancia de encuadre; mayor que uno acerca.
  - `look_at` (lista de número o null; opcional, por defecto `null`): objetivo [x, y, z] en mm; vacío usa el centro de los cuerpos.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): cuerpos a encuadrar por nombre o id; vacío encuadra todos.
  - `clear` (true/false; opcional, por defecto `false`): borra la cámara guardada y vuelve al encuadre automático.
- CLI: `omnicad call set_view --doc pieza.omnicad`

### `manage_named_views`

Lista, guarda, aplica, renombra o elimina vistas con nombre compatibles con el navegador de la ventana. Como en la ventana, no entran en deshacer.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `action` ("list" | "save" | "apply" | "rename" | "delete"; obligatorio): list, save, apply, rename o delete.
  - `name` (texto; opcional, por defecto `""`): nombre de la vista guardada.
  - `new_name` (texto; opcional, por defecto `""`): nombre nuevo para rename.
- CLI: `omnicad call manage_named_views --doc pieza.omnicad action=…`

### `set_grid`

Guarda mostrar rejilla, forzar a la rejilla y cuatro vistas. La imagen dibuja la rejilla del suelo cuando está visible.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `show` (true/false; opcional, por defecto `null`): muestra u oculta la rejilla del suelo.
  - `snap` (true/false; opcional, por defecto `null`): activa o desactiva forzar a la rejilla.
  - `four_views` (true/false; opcional, por defecto `null`): activa o desactiva la opción de cuatro vistas.
- CLI: `omnicad call set_grid --doc pieza.omnicad`

### `capture_viewport`

Captura la vista 3D REAL de la ventana de OmniCAD tal como la ve la persona: cámara, estilo visual, entorno, selección y análisis mostrados. Solo en vivo. Para una imagen sin ventana, con la cámara que pidas, usá get_viewport_image.

- Modifica el documento: no.
- Parámetros:
  - `width` (entero; opcional, por defecto `null`): ancho en píxeles de la imagen devuelta (16 a 4096); con height. Vacío = el tamaño de la vista en pantalla.
  - `height` (entero; opcional, por defecto `null`): alto en píxeles de la imagen devuelta (16 a 4096); con width.
- CLI: `omnicad call capture_viewport --doc pieza.omnicad`

## Grupo animacion

Espacio ANIMACIÓN: guiones gráficos, acciones, explosión automática, cámara, cuadros y video.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`create_storyboard`](#create_storyboard) | sí | Crea un guion gráfico (storyboard) del espacio ANIMACIÓN: limpio o que continúa desde el final del actual, como Nuevo guion gráfico. |
| [`list_storyboards`](#list_storyboards) | no | Lista los guiones gráficos (storyboards) del documento con su duración y su cantidad de acciones. |
| [`get_storyboard`](#get_storyboard) | no | Devuelve un guion gráfico completo: estado inicial (posición de los cuerpos y cámara) y la lista de acciones con sus tiempos (para edit_animation_action y delete_animation_action). |
| [`rename_storyboard`](#rename_storyboard) | sí | Cambia el nombre de un guion gráfico. |
| [`copy_storyboard`](#copy_storyboard) | sí | Duplica un guion gráfico con todas sus acciones (Copia de la ventana; el nuevo se llama «… (copia)»). |
| [`delete_storyboard`](#delete_storyboard) | sí | Elimina un guion gráfico. |
| [`reverse_storyboard`](#reverse_storyboard) | sí | Invierte un guion gráfico (Invertir de la ventana): empieza donde terminaba y hace las acciones al revés. |
| [`add_animation_action`](#add_animation_action) | sí | Agrega una acción al guion gráfico: transform (mover y girar componentes), restore (volver a la posición del diseño) o visibility (mostrar/ocultar), como TRANSFORMAR de ANIMACIÓN. |
| [`edit_animation_action`](#edit_animation_action) | sí | Edita una acción del guion gráfico: moverla o estirar su barra (start, duration) y sus valores (movimiento, visibilidad, texto, cámara). |
| [`delete_animation_action`](#delete_animation_action) | sí | Elimina una acción del guion gráfico. |
| [`auto_explode`](#auto_explode) | sí | Explosión automática (EXPLOSIÓN AUTOMÁTICA de ANIMACIÓN): agrega una acción que separa las piezas hacia afuera del centro, de un nivel o de todos los niveles. |
| [`set_animation_camera`](#set_animation_camera) | sí | Agrega una acción Vista al guion: la cámara va (con la misma vista orbital de la ventana) desde la cámara inicial hasta la nueva. |
| [`add_animation_annotation`](#add_animation_annotation) | sí | Agrega una anotación (globo con texto) al guion gráfico: fija en un punto del mundo o pegada a un cuerpo, a la que sigue si se mueve. |
| [`get_animation_frame`](#get_animation_frame) | no | Devuelve el estado de la escena en un instante del guion gráfico (matrices y visibilidad de cada cuerpo, cámara, anotaciones) y una imagen renderizada del cuadro, sin abrir la ventana (como Ir a de ANIMACIÓN). |
| [`export_animation_video`](#export_animation_video) | no | Publica la animación como GIF animado o secuencia de imágenes PNG, renderizando cada cuadro con el renderizador por software (como PUBLICAR de ANIMACIÓN, sin abrir la ventana). |

### `create_storyboard`

Crea un guion gráfico (storyboard) del espacio ANIMACIÓN: limpio o que continúa desde el final del actual, como Nuevo guion gráfico.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `name` (texto; opcional, por defecto `null`): nombre del guion nuevo; vacío = «Guion gráficoN» sin repetir (como la ventana).
  - `from_final` (true/false; opcional, por defecto `false`): true arranca donde termina el guion actual (posición de los cuerpos y cámara); false = limpio.
- CLI: `omnicad call create_storyboard --doc pieza.omnicad`

### `list_storyboards`

Lista los guiones gráficos (storyboards) del documento con su duración y su cantidad de acciones.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call list_storyboards --doc pieza.omnicad`

### `get_storyboard`

Devuelve un guion gráfico completo: estado inicial (posición de los cuerpos y cámara) y la lista de acciones con sus tiempos (para edit_animation_action y delete_animation_action).

- Modifica el documento: no.
- Parámetros:
  - `storyboard` (texto o entero; opcional, por defecto `null`): nombre del guion gráfico, índice (desde 0) o vacío = el actual (list_storyboards los lista).
- CLI: `omnicad call get_storyboard --doc pieza.omnicad`

### `rename_storyboard`

Cambia el nombre de un guion gráfico.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `storyboard` (texto o entero; opcional, por defecto `null`): nombre del guion gráfico, índice (desde 0) o vacío = el actual.
  - `new_name` (texto; opcional, por defecto `""`): nombre nuevo (no puede repetirse).
- CLI: `omnicad call rename_storyboard --doc pieza.omnicad`

### `copy_storyboard`

Duplica un guion gráfico con todas sus acciones (Copia de la ventana; el nuevo se llama «… (copia)»).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `storyboard` (texto o entero; opcional, por defecto `null`): nombre del guion gráfico a copiar, índice (desde 0) o vacío = el actual.
- CLI: `omnicad call copy_storyboard --doc pieza.omnicad`

### `delete_storyboard`

Elimina un guion gráfico. Si es el único, queda uno limpio con el mismo nombre (como la ventana).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `storyboard` (texto o entero; opcional, por defecto `null`): nombre del guion gráfico a eliminar, índice (desde 0) o vacío = el actual.
- CLI: `omnicad call delete_storyboard --doc pieza.omnicad`

### `reverse_storyboard`

Invierte un guion gráfico (Invertir de la ventana): empieza donde terminaba y hace las acciones al revés.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `storyboard` (texto o entero; opcional, por defecto `null`): nombre del guion gráfico a invertir, índice (desde 0) o vacío = el actual.
- CLI: `omnicad call reverse_storyboard --doc pieza.omnicad`

### `add_animation_action`

Agrega una acción al guion gráfico: transform (mover y girar componentes), restore (volver a la posición del diseño) o visibility (mostrar/ocultar), como TRANSFORMAR de ANIMACIÓN.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `storyboard` (texto o entero; opcional, por defecto `null`): nombre del guion gráfico, índice (desde 0) o vacío = el actual.
  - `type` ("transform" | "restore" | "visibility"; opcional, por defecto `"transform"`): "transform" mueve y gira; "restore" vuelve a la posición del diseño; "visibility" muestra u oculta.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos (get_scene_info); obligatorio en los tres tipos.
  - `translation` (lista de número o null; opcional, por defecto `null`): [x, y, z] en mm (solo transform).
  - `rotation` (lista de número o null; opcional, por defecto `null`): [rx, ry, rz] ángulos en grados, primero X después Y después Z (solo transform).
  - `visible` (true/false; opcional, por defecto `false`): true muestra, false oculta (solo visibility); con duration > 0 se desvanece.
  - `start` (número; opcional, por defecto `0.0`): instante en que empieza la acción, en segundos.
  - `duration` (número; opcional, por defecto `1.0`): cuánto dura, en segundos (0 = instantáneo).
- CLI: `omnicad call add_animation_action --doc pieza.omnicad`

### `edit_animation_action`

Edita una acción del guion gráfico: moverla o estirar su barra (start, duration) y sus valores (movimiento, visibilidad, texto, cámara). Solo cambian los parámetros pasados.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `storyboard` (texto o entero; opcional, por defecto `null`): nombre del guion gráfico, índice (desde 0) o vacío = el actual.
  - `action` (texto; opcional, por defecto `""`): id de la acción (a1, a2, …; lo lista get_storyboard).
  - `start` (número; opcional, por defecto `null`): nuevo instante de inicio, en segundos.
  - `duration` (número; opcional, por defecto `null`): nueva duración, en segundos (0 = instantáneo).
  - `translation` (lista de número o null; opcional, por defecto `null`): [x, y, z] en mm (solo acciones transform).
  - `rotation` (lista de número o null; opcional, por defecto `null`): [rx, ry, rz] ángulos en grados (solo acciones transform).
  - `visible` (true/false; opcional, por defecto `null`): true muestra, false oculta (solo acciones visibility).
  - `text` (texto; opcional, por defecto `null`): texto nuevo (solo anotaciones).
  - `camera` (objeto; opcional, por defecto `null`): cámara nueva, {"R", "objetivo", "distancia", "fov"} (solo acciones vista).
- CLI: `omnicad call edit_animation_action --doc pieza.omnicad`

### `delete_animation_action`

Elimina una acción del guion gráfico.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `storyboard` (texto o entero; opcional, por defecto `null`): nombre del guion gráfico, índice (desde 0) o vacío = el actual.
  - `action` (texto; opcional, por defecto `""`): id de la acción a eliminar (a1, a2, …; lo lista get_storyboard).
- CLI: `omnicad call delete_animation_action --doc pieza.omnicad`

### `auto_explode`

Explosión automática (EXPLOSIÓN AUTOMÁTICA de ANIMACIÓN): agrega una acción que separa las piezas hacia afuera del centro, de un nivel o de todos los niveles.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `storyboard` (texto o entero; opcional, por defecto `null`): nombre del guion gráfico, índice (desde 0) o vacío = el actual.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos a separar; vacío = todo el modelo.
  - `level` ("one" | "all"; opcional, por defecto `"one"`): "one" = un nivel (los cuerpos de un mismo componente van juntos); "all" = todos los niveles (cada cuerpo por su lado).
  - `distance` (número; opcional, por defecto `null`): escala de la explosión en mm: cuánto se aparta la pieza más lejana; vacío = 60 % del tamaño del modelo (como la ventana).
  - `sequential` (true/false; opcional, por defecto `false`): true = las piezas explotan una después de la otra; false = todas a la vez.
  - `start` (número; opcional, por defecto `0.0`): instante en que empieza la acción, en segundos.
  - `duration` (número; opcional, por defecto `1.0`): cuánto dura, en segundos.
- CLI: `omnicad call auto_explode --doc pieza.omnicad`

### `set_animation_camera`

Agrega una acción Vista al guion: la cámara va (con la misma vista orbital de la ventana) desde la cámara inicial hasta la nueva.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `storyboard` (texto o entero; opcional, por defecto `null`): nombre del guion gráfico, índice (desde 0) o vacío = el actual.
  - `camera` (objeto; opcional, por defecto `null`): cámara completa {"R": 3x3, "objetivo": [x, y, z], "distancia", "fov", "ortografica"} (la guarda el guion); si no se pasa, se arma una que encuadra todo el modelo.
  - `view` ("iso" | "front" | "back" | "right" | "left" | "top" | "bottom"; opcional, por defecto `"iso"`): vista estándar para la cámara cuando no se pasa camera: iso, front, back, right, left, top o bottom.
  - `start` (número; opcional, por defecto `0.0`): instante en que empieza la acción, en segundos.
  - `duration` (número; opcional, por defecto `1.0`): cuánto dura el viaje de cámara, en segundos.
- CLI: `omnicad call set_animation_camera --doc pieza.omnicad`

### `add_animation_annotation`

Agrega una anotación (globo con texto) al guion gráfico: fija en un punto del mundo o pegada a un cuerpo, a la que sigue si se mueve.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `storyboard` (texto o entero; opcional, por defecto `null`): nombre del guion gráfico, índice (desde 0) o vacío = el actual.
  - `text` (texto; opcional, por defecto `""`): texto de la anotación.
  - `point` (lista de número o null; opcional, por defecto `null`): [x, y, z] en mm donde va el alfiler de la anotación.
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo al que se pega (la anotación lo sigue); con body, point va en coordenadas del cuerpo; vacío = fija en el mundo.
  - `start` (número; opcional, por defecto `0.0`): instante en que aparece, en segundos.
  - `duration` (número; opcional, por defecto `2.0`): cuánto dura visible, en segundos (0 = hasta el final del guion).
- CLI: `omnicad call add_animation_annotation --doc pieza.omnicad`

### `get_animation_frame`

Devuelve el estado de la escena en un instante del guion gráfico (matrices y visibilidad de cada cuerpo, cámara, anotaciones) y una imagen renderizada del cuadro, sin abrir la ventana (como Ir a de ANIMACIÓN).

- Modifica el documento: no.
- Parámetros:
  - `storyboard` (texto o entero; opcional, por defecto `null`): nombre del guion gráfico, índice (desde 0) o vacío = el actual.
  - `time` (número; opcional, por defecto `0.0`): instante en segundos (0 = comienzo; get_storyboard dice la duración total).
  - `width` (entero; opcional, por defecto `640`): ancho de la imagen en píxeles (16 a 2048).
  - `height` (entero; opcional, por defecto `480`): alto de la imagen en píxeles (16 a 2048).
- CLI: `omnicad call get_animation_frame --doc pieza.omnicad`

### `export_animation_video`

Publica la animación como GIF animado o secuencia de imágenes PNG, renderizando cada cuadro con el renderizador por software (como PUBLICAR de ANIMACIÓN, sin abrir la ventana).

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; obligatorio): archivo .gif a escribir, o carpeta para la secuencia de PNG (se crea si no existe).
  - `storyboard` (texto o entero; opcional, por defecto `null`): nombre del guion gráfico a publicar, índice (desde 0) o vacío = el actual.
  - `all_storyboards` (true/false; opcional, por defecto `false`): true publica todos los guiones del documento, uno tras otro.
  - `format` ("gif" | "png"; opcional, por defecto `"gif"`): "gif" = GIF animado que se repite; "png" = secuencia de imágenes PNG (cuadro_0001.png, …).
  - `width` (entero; opcional, por defecto `640`): ancho del video en píxeles (16 a 2048).
  - `height` (entero; opcional, por defecto `360`): alto del video en píxeles (16 a 2048).
  - `fps` (entero; opcional, por defecto `15`): cuadros por segundo (1 a 60).
- CLI: `omnicad call export_animation_video --doc pieza.omnicad path=…`

## Grupo dibujo

Espacio DIBUJO: hoja y cajetín, vistas (base, proyectada, sección, detalle), cotas, notas y exportación.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`create_drawing`](#create_drawing) | sí | Crea el dibujo (plano 2D) del documento, como DIBUJO › Nuevo dibujo desde el diseño: hoja y cajetín vacíos, o ya con la vista base frontal de los cuerpos que pidas. |
| [`get_drawing`](#get_drawing) | no | Devuelve el dibujo del documento: hoja (tamaño, norma, área útil), cajetín, cada vista (tipo, padre, escala, posición y recuadro en la hoja) y cada anotación (cotas con su valor, notas, globos, líneas y marcas de centro), más la lista de piezas. |
| [`set_drawing_sheet`](#set_drawing_sheet) | sí | Cambia la hoja del dibujo y los campos del cajetín, como DIBUJO › Hoja y cajetín: norma (ISO/ASME, que fija el diedro), tamaño, orientación, método de cálculo de las vistas y los textos del cajetín. |
| [`add_drawing_view`](#add_drawing_view) | sí | Agrega una vista al dibujo: base (de cuerpos, con orientación), proyectada (de una vista padre; la posición elige la dirección: a la derecha, arriba, en diagonal = isométrica…), de sección (corte por una línea sobre la vista padre) o de detalle (un círculo ampliado de la padre). |
| [`edit_drawing_view`](#edit_drawing_view) | sí | Cambia las propiedades de una vista del dibujo (escala, estilo de aristas, tangentes, marcas de centro, nombre/etiqueta) o la gira. |
| [`get_drawing_geometry`](#get_drawing_geometry) | no | Puntos clave, circunferencias y aristas rectas visibles de una vista, en mm de la hoja. |
| [`add_drawing_dimension`](#add_drawing_dimension) | sí | Agrega una cota asociada a una vista; puntos y colocación en mm de la hoja. |
| [`add_drawing_centerline`](#add_drawing_centerline) | sí | Agrega una línea de centro entre puntos enganchados de una vista. |
| [`add_drawing_center_mark`](#add_drawing_center_mark) | sí | Agrega una marca de centro en la circunferencia más cercana (3 mm). |
| [`add_drawing_text`](#add_drawing_text) | sí | Agrega texto libre a la hoja del plano. |
| [`add_drawing_note`](#add_drawing_note) | sí | Agrega una nota con directriz, asociada a la vista bajo la flecha si no se indica otra. |
| [`add_drawing_balloon`](#add_drawing_balloon) | sí | Agrega un globo de pieza con número automático o propio. |
| [`add_drawing_table`](#add_drawing_table) | sí | Agrega la lista de piezas del plano (parts_list de get_drawing). |
| [`edit_drawing_annotation`](#edit_drawing_annotation) | sí | Edita el texto de una cota, nota, texto libre o el número de un globo. |
| [`move_drawing_element`](#move_drawing_element) | sí | Mueve una vista o anotación y devuelve el desplazamiento real permitido por su alineación. |
| [`delete_drawing_element`](#delete_drawing_element) | sí | Borra una anotación o una vista con todas sus hijas y anotaciones asociadas. |
| [`export_drawing`](#export_drawing) | no | Exporta la hoja del dibujo (vistas, cotas, marco y cajetín) a DXF (capas por tipo de línea, en mm), SVG (mm, una capa por tipo de línea) o PDF vectorial a escala real; el formato sale de la extensión o de format. |
| [`get_drawing_image`](#get_drawing_image) | no | Devuelve la hoja del dibujo como imagen PNG (fondo blanco, líneas negras con los grosores y tipos de línea reales, cotas, texto, marco y cajetín): es la forma de VER el plano. |

### `create_drawing`

Crea el dibujo (plano 2D) del documento, como DIBUJO › Nuevo dibujo desde el diseño: hoja y cajetín vacíos, o ya con la vista base frontal de los cuerpos que pidas. Un dibujo por documento; con replace=true se reemplaza el que haya.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `size` (texto; opcional, por defecto `"A3"`): tamaño de hoja: ISO "A4", "A3", "A2", "A1", "A0" o ASME "ANSI A" a "ANSI E" (nd.TAMANOS_HOJA).
  - `orientation` ("horizontal" | "vertical"; opcional, por defecto `"horizontal"`): "horizontal" o "vertical".
  - `standard` ("ISO" | "ASME"; opcional, por defecto `"ISO"`): "ISO" (primer diedro) o "ASME" (tercer diedro).
  - `title` (texto; opcional, por defecto `null`): título del cajetín; vacío = el nombre del documento.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de cuerpos; si se pasa, agrega la vista base frontal de esos cuerpos (la escala se elige sola para que entre en la hoja). Vacío = hoja sin vistas (add_drawing_view agrega las vistas).
  - `replace` (true/false; opcional, por defecto `false`): true reemplaza el dibujo que ya tenga el documento; false lo rechaza (DRAWING_EXISTS).
- CLI: `omnicad call create_drawing --doc pieza.omnicad`

### `get_drawing`

Devuelve el dibujo del documento: hoja (tamaño, norma, área útil), cajetín, cada vista (tipo, padre, escala, posición y recuadro en la hoja) y cada anotación (cotas con su valor, notas, globos, líneas y marcas de centro), más la lista de piezas.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call get_drawing --doc pieza.omnicad`

### `set_drawing_sheet`

Cambia la hoja del dibujo y los campos del cajetín, como DIBUJO › Hoja y cajetín: norma (ISO/ASME, que fija el diedro), tamaño, orientación, método de cálculo de las vistas y los textos del cajetín. Solo cambia lo que pasás.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `standard` ("ISO" | "ASME" o null; opcional, por defecto `null`): "ISO" (primer diedro) o "ASME" (tercer diedro).
  - `size` (texto; opcional, por defecto `null`): tamaño de hoja: "A4" a "A0" o "ANSI A" a "ANSI E".
  - `orientation` ("horizontal" | "vertical" o null; opcional, por defecto `null`): "horizontal" o "vertical".
  - `method` ("exact" | "fast" o null; opcional, por defecto `null`): cálculo de las vistas: "exact" (HLR exacto, más lento) o "fast" (aproximado).
  - `title` (texto; opcional, por defecto `null`): título del cajetín.
  - `part_number` (texto; opcional, por defecto `null`): número de pieza del cajetín.
  - `author` (texto; opcional, por defecto `null`): quién dibujó (cajetín).
  - `material` (texto; opcional, por defecto `null`): material (cajetín y lista de piezas).
  - `sheet` (texto; opcional, por defecto `null`): hoja, p. ej. "1 / 1".
  - `date` (texto; opcional, por defecto `null`): fecha (texto libre, p. ej. "20/10/2026").
  - `scale` (texto; opcional, por defecto `null`): texto de escala del cajetín; vacío ("") = la de la vista base.
- CLI: `omnicad call set_drawing_sheet --doc pieza.omnicad`

### `add_drawing_view`

Agrega una vista al dibujo: base (de cuerpos, con orientación), proyectada (de una vista padre; la posición elige la dirección: a la derecha, arriba, en diagonal = isométrica…), de sección (corte por una línea sobre la vista padre) o de detalle (un círculo ampliado de la padre). Las posiciones, líneas y círculos van en mm de la HOJA (get_drawing da el tamaño y el recuadro de cada vista).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `type` ("base" | "projected" | "section" | "detail"; opcional, por defecto `"base"`): "base" (cuerpos + orientación), "projected" (sale de parent), "section" (corte de parent), "detail" (círculo ampliado de parent).
  - `bodies` (lista de texto o null; opcional, por defecto `null`): base: ids o nombres de los cuerpos de la vista; vacío = todos los sólidos. Las demás vistas toman los de su padre.
  - `orientation` ("front" | "back" | "top" | "bottom" | "right" | "left" | "iso_se" | "iso_sw" | "iso_ne" | "iso_nw"; opcional, por defecto `"front"`): base: "front" (cámara en -Y), "back", "top", "bottom", "right", "left" o isométricas "iso_se", "iso_sw", "iso_ne", "iso_nw".
  - `parent` (texto; opcional, por defecto `null`): projected, section y detail: id de la vista padre («v1», de get_drawing).
  - `position` (lista de número o null; opcional, por defecto `null`): [x, y] mm de la hoja donde va el CENTRO de la vista. Base: vacío = arriba a la izquierda del área útil. Projected: obligatorio, respecto de la padre (a la derecha, abajo, arriba…). Section y detail: obligatorio.
  - `section_line` (lista de lista de número o null; opcional, por defecto `null`): section: [[x1, y1], [x2, y2]] mm de la hoja, la línea de corte sobre la vista padre. Se muestra el lado donde está position.
  - `detail_center` (lista de número o null; opcional, por defecto `null`): detail: [x, y] mm de la hoja, centro del círculo de detalle sobre la vista padre.
  - `detail_radius` (número; opcional, por defecto `null`): detail: radio del círculo de detalle en mm de la hoja.
  - `scale` (número o expresión; opcional, por defecto `null`): razón de escala (0.5 = 1:2, 2 = 2:1) o texto "1:2", "2:1", "1/2". Base: vacío = la normalizada mayor que entra en la hoja. Projected y section heredan la de la padre. Detail: vacío = el doble de la padre.
  - `style` ("visible" | "visible_hidden"; opcional, por defecto `"visible_hidden"`): "visible" (solo aristas visibles) o "visible_hidden" (con las ocultas, en trazos). Solo en la base.
  - `tangents` ("full" | "shortened" | "off" o null; opcional, por defecto `null`): "full", "shortened" u "off": cómo se muestran las aristas tangentes. Vacío = "full" en la base y lo de la vista padre en las demás.
  - `center_marks` (true/false; opcional, por defecto `null`): true/false las marcas de centro de las circunferencias. Vacío = true en la base y lo de la padre en las demás.
- CLI: `omnicad call add_drawing_view --doc pieza.omnicad`

### `edit_drawing_view`

Cambia las propiedades de una vista del dibujo (escala, estilo de aristas, tangentes, marcas de centro, nombre/etiqueta) o la gira. Las vistas proyectadas y de sección heredan la escala nueva; las alineadas con su padre se vuelven a alinear.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `view` (texto; obligatorio): id de la vista («v1», de get_drawing).
  - `scale` (número o expresión; opcional, por defecto `null`): nueva escala: razón (0.5 = 1:2) o texto "1:2", "2:1".
  - `style` ("visible" | "visible_hidden" o null; opcional, por defecto `null`): "visible" o "visible_hidden" (aristas ocultas en trazos).
  - `tangents` ("full" | "shortened" | "off" o null; opcional, por defecto `null`): "full", "shortened" u "off".
  - `center_marks` (true/false; opcional, por defecto `null`): true/false las marcas de centro de las circunferencias.
  - `label` (texto; opcional, por defecto `null`): nombre/letra de la vista («A»; las secciones y detalles la usan en su rótulo).
  - `rotate` (número; opcional, por defecto `null`): grados que se SUMAN al giro actual de la vista, antihorario (el giro queda entre 0 y 360).
- CLI: `omnicad call edit_drawing_view --doc pieza.omnicad view=…`

### `get_drawing_geometry`

Puntos clave, circunferencias y aristas rectas visibles de una vista, en mm de la hoja.

- Modifica el documento: no.
- Parámetros:
  - `view` (texto; obligatorio): id de la vista.
  - `limit` (entero; opcional, por defecto `200`): máximo de puntos, círculos y segmentos por separado; entero no negativo.
- CLI: `omnicad call get_drawing_geometry --doc pieza.omnicad view=…`

### `add_drawing_dimension`

Agrega una cota asociada a una vista; puntos y colocación en mm de la hoja.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `view` (texto; obligatorio): id de la vista.
  - `type` ("horizontal" | "vertical" | "aligned" | "radius" | "diameter" | "angle" | "ordinate_x" | "ordinate_y"; obligatorio): horizontal, vertical, aligned, radius, diameter, angle, ordinate_x u ordinate_y.
  - `points` (lista de lista de número; obligatorio): dos puntos; radial: uno sobre la circunferencia; angular: dos sobre aristas o cuatro extremos explícitos.
  - `place` (lista de número; obligatorio): posición de la cota [x, y] en mm de la hoja.
  - `text` (texto; opcional, por defecto `null`): texto propio que reemplaza el valor; vacío restaura el valor medido.
  - `snap` (true/false; opcional, por defecto `true`): enganchar puntos a puntos clave de esta vista dentro de 3 mm de hoja.
- CLI: `omnicad call add_drawing_dimension --doc pieza.omnicad view=… type=… points=… place=…`

### `add_drawing_centerline`

Agrega una línea de centro entre puntos enganchados de una vista.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `view` (texto; obligatorio): id de la vista.
  - `start` (lista de número; obligatorio): primer punto [x, y] en mm de hoja; enganche a 3 mm.
  - `end` (lista de número; obligatorio): segundo punto [x, y] en mm de hoja; enganche a 3 mm.
- CLI: `omnicad call add_drawing_centerline --doc pieza.omnicad view=… start=… end=…`

### `add_drawing_center_mark`

Agrega una marca de centro en la circunferencia más cercana (3 mm).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `view` (texto; obligatorio): id de la vista.
  - `point` (lista de número; obligatorio): punto [x, y] de hoja sobre el borde del círculo o arco.
- CLI: `omnicad call add_drawing_center_mark --doc pieza.omnicad view=… point=…`

### `add_drawing_text`

Agrega texto libre a la hoja del plano.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `position` (lista de número; obligatorio): posición [x, y] en mm de hoja.
  - `text` (texto; obligatorio): texto no vacío, admite varias líneas.
  - `height` (número; opcional, por defecto `3.5`): altura positiva y finita del texto en mm.
- CLI: `omnicad call add_drawing_text --doc pieza.omnicad position=… text=…`

### `add_drawing_note`

Agrega una nota con directriz, asociada a la vista bajo la flecha si no se indica otra.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `arrow` (lista de número; obligatorio): punto señalado [x, y] en mm de hoja, con enganche a 3 mm.
  - `position` (lista de número; obligatorio): posición del texto [x, y] en mm de hoja.
  - `text` (texto; obligatorio): texto no vacío de la nota.
  - `view` (texto; opcional, por defecto `null`): id de vista; vacío deduce la vista bajo la flecha.
- CLI: `omnicad call add_drawing_note --doc pieza.omnicad arrow=… position=… text=…`

### `add_drawing_balloon`

Agrega un globo de pieza con número automático o propio.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `view` (texto; obligatorio): id de la vista.
  - `point` (lista de número; obligatorio): punto señalado [x, y] en mm de hoja, con enganche a 3 mm.
  - `position` (lista de número; obligatorio): posición del globo [x, y] en mm de hoja.
  - `number` (texto; opcional, por defecto `null`): número propio; vacío usa el elemento de la lista de piezas.
- CLI: `omnicad call add_drawing_balloon --doc pieza.omnicad view=… point=… position=…`

### `add_drawing_table`

Agrega la lista de piezas del plano (parts_list de get_drawing). La lista de materiales del MODELO es get_bill_of_materials; esta tabla no la duplica.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `position` (lista de número; obligatorio): posición [x, y] en mm de hoja de la tabla de piezas del plano.
- CLI: `omnicad call add_drawing_table --doc pieza.omnicad position=…`

### `edit_drawing_annotation`

Edita el texto de una cota, nota, texto libre o el número de un globo.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `annotation` (texto; obligatorio): id de la anotación editable.
  - `text` (texto; obligatorio): texto nuevo; en cotas, vacío restaura el valor medido.
- CLI: `omnicad call edit_drawing_annotation --doc pieza.omnicad annotation=… text=…`

### `move_drawing_element`

Mueve una vista o anotación y devuelve el desplazamiento real permitido por su alineación.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `element` (texto; obligatorio): id de vista o anotación.
  - `delta` (lista de número; obligatorio): desplazamiento [dx, dy] en mm de hoja.
- CLI: `omnicad call move_drawing_element --doc pieza.omnicad element=… delta=…`

### `delete_drawing_element`

Borra una anotación o una vista con todas sus hijas y anotaciones asociadas.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `element` (texto; obligatorio): id de vista o anotación a borrar.
- CLI: `omnicad call delete_drawing_element --doc pieza.omnicad element=…`

### `export_drawing`

Exporta la hoja del dibujo (vistas, cotas, marco y cajetín) a DXF (capas por tipo de línea, en mm), SVG (mm, una capa por tipo de línea) o PDF vectorial a escala real; el formato sale de la extensión o de format. Crea las carpetas que falten (create_folders=false para que falle con FILE_NOT_FOUND).

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; obligatorio): ruta del archivo a escribir; si no tiene la extensión del formato, se la agrega.
  - `format` ("dxf" | "svg" | "pdf" o null; opcional, por defecto `null`): "dxf", "svg" o "pdf"; vacío = el de la extensión de path.
  - `overwrite` (true/false; opcional, por defecto `false`): true para reemplazar el archivo si ya existe.
  - `create_folders` (true/false; opcional, por defecto `true`): true (por defecto) crea las carpetas de la ruta que no existen (se avisa); false = FILE_NOT_FOUND.
  - `dxf_version` ("2000" | "R12"; opcional, por defecto `"2000"`): solo para DXF: "2000" (AC1015) o "R12" (AC1009).
- CLI: `omnicad call export_drawing --doc pieza.omnicad path=…`

### `get_drawing_image`

Devuelve la hoja del dibujo como imagen PNG (fondo blanco, líneas negras con los grosores y tipos de línea reales, cotas, texto, marco y cajetín): es la forma de VER el plano.

- Modifica el documento: no.
- Parámetros:
  - `width` (entero; opcional, por defecto `1200`): ancho de la imagen en píxeles (200 a 4000); el alto sale de la proporción de la hoja.
- CLI: `omnicad call get_drawing_image --doc pieza.omnicad`

## Grupo render

Espacio RENDERIZAR: entornos, escena, cámara guardada e imagen final del render.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`list_render_environments`](#list_render_environments) | no | Lista la biblioteca de entornos del render y el entorno inicial. |
| [`get_render_scene`](#get_render_scene) | no | Devuelve la escena, las opciones del lienzo y la cámara guardada. |
| [`set_render_scene`](#set_render_scene) | sí | Cambia solo las propiedades indicadas de la escena del render. |
| [`set_render_camera`](#set_render_camera) | sí | Guarda o borra la cámara del espacio RENDERIZAR. |
| [`render_image`](#render_image) | no | Renderiza un PNG por CPU con la escena y la cámara guardadas del documento. |

### `list_render_environments`

Lista la biblioteca de entornos del render y el entorno inicial.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call list_render_environments --doc pieza.omnicad`

### `get_render_scene`

Devuelve la escena, las opciones del lienzo y la cámara guardada.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call get_render_scene --doc pieza.omnicad`

### `set_render_scene`

Cambia solo las propiedades indicadas de la escena del render.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `environment` (texto; opcional, por defecto `null`): id del entorno de list_render_environments.
  - `brightness` (número; opcional, por defecto `null`): intensidad de las luces, acotada a 0..4.
  - `rotation` (número; opcional, por defecto `null`): giro del entorno en grados, normalizado a 0..360.
  - `background` ("environment" | "color" o null; opcional, por defecto `null`): fondo del entorno (environment) o color uniforme (color).
  - `background_color` (lista de número o null; opcional, por defecto `null`): tres componentes sRGB, acotadas a 0..1.
  - `ground` (true/false; opcional, por defecto `null`): activa el plano de suelo.
  - `reflections` (true/false; opcional, por defecto `null`): activa los reflejos sobre el suelo.
  - `ground_roughness` (número; opcional, por defecto `null`): rugosidad del suelo, acotada a 0..1.
  - `shadows` (true/false; opcional, por defecto `null`): activa las sombras.
  - `ambient_occlusion` (true/false; opcional, por defecto `null`): activa la oclusión ambiental.
  - `camera_type` ("perspective" | "orthographic" o null; opcional, por defecto `null`): proyección perspectiva (perspective) u ortográfica (orthographic).
  - `focal_length` (número; opcional, por defecto `null`): distancia focal en mm, acotada a 8..300.
  - `exposure` (número; opcional, por defecto `null`): exposición en EV, acotada a -6..6.
  - `canvas_high_quality` (true/false; opcional, por defecto `null`): activa la alta calidad en el lienzo.
  - `canvas_supersampling` (entero; opcional, por defecto `null`): supermuestreo del lienzo, de 1 a 3.
- CLI: `omnicad call set_render_scene --doc pieza.omnicad`

### `set_render_camera`

Guarda o borra la cámara del espacio RENDERIZAR.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `view` ("iso" | "front" | "back" | "top" | "bottom" | "left" | "right"; opcional, por defecto `"iso"`): vista estándar desde la que encuadrar los cuerpos.
  - `direction` (lista de número o null; opcional, por defecto `null`): vector [x, y, z] hacia la cámara; reemplaza a view.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos a encuadrar; vacío = todos.
  - `distance` (número; opcional, por defecto `null`): distancia al objetivo en mm; vacío = encuadre automático.
  - `clear` (true/false; opcional, por defecto `false`): true borra la cámara guardada y vuelve al encuadre automático.
- CLI: `omnicad call set_render_camera --doc pieza.omnicad`

### `render_image`

Renderiza un PNG por CPU con la escena y la cámara guardadas del documento.

- Modifica el documento: no.
- Parámetros:
  - `width` (entero; opcional, por defecto `1280`): ancho de la imagen, de 16 a 4096 píxeles.
  - `height` (entero; opcional, por defecto `720`): alto de la imagen, de 16 a 4096 píxeles.
  - `preset` ("web" | "hd" | "full_hd" o null; opcional, por defecto `null`): tamaño predefinido web, hd o full_hd; reemplaza a width y height.
  - `quality` ("draft" | "standard" | "final"; opcional, por defecto `"standard"`): draft (1×), standard (2×) o final (3×) de supermuestreo.
  - `transparent_background` (true/false; opcional, por defecto `false`): true genera un PNG RGBA con fondo transparente.
  - `path` (texto; opcional, por defecto `null`): ruta .png opcional, en una carpeta existente.
  - `overwrite` (true/false; opcional, por defecto `false`): true permite reemplazar un archivo existente.
  - `view` ("iso" | "front" | "back" | "top" | "bottom" | "left" | "right" o null; opcional, por defecto `null`): vista estándar; reemplaza la cámara guardada solo para esta imagen.
  - `direction` (lista de número o null; opcional, por defecto `null`): vector [x, y, z] hacia la cámara; reemplaza a view y a la cámara guardada.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos a renderizar; vacío = todos.
- CLI: `omnicad call render_image --doc pieza.omnicad`

## Grupo avanzado

Cualquier operación, receta, código y guía.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`list_operation_types`](#list_operation_types) | no | Lista todos los tipos de operación del timeline que acepta run_operation: tipo, etiqueta y una línea que dice qué hace. |
| [`describe_operation`](#describe_operation) | no | Explica un tipo de operación: parámetros con su valor por defecto, tipo, si aceptan expresiones, en los de lista cerrada sus valores válidos (choices), en los que guardan referencias qué esperan y en qué formas cortas (format, reference_formats), aclaraciones (notes); el docstring completo y un ejemplo de llamada a run_operation. |
| [`run_operation`](#run_operation) | sí | Agrega al timeline cualquier operación por su tipo y sus parámetros nativos (claves en español, las de describe_operation). |
| [`get_recipe`](#get_recipe) | no | Devuelve la receta JSON completa del documento (parámetros, timeline y propiedades): es lo que guarda el archivo .omnicad y lo que acepta apply_recipe. |
| [`apply_recipe`](#apply_recipe) | sí | Carga una receta JSON (la de get_recipe): 'replace' reemplaza todo el documento; 'append' agrega sus pasos y parámetros al final. |
| [`execute_code`](#execute_code) | sí | Ejecuta código Python con api, sesion, doc y llamar(nombre, args) ya definidos. |
| [`get_guide`](#get_guide) | no | Guía corta para agentes (ciclo de trabajo, unidades, cómo leer errores). |
| [`search_help`](#search_help) | no | Busca en la ayuda LOCAL de OmniCAD (catálogo de herramientas, guía para agentes y documentación del repo si está) y devuelve fragmentos cortos con su fuente, para responder «¿cómo se hace…?» citando de dónde sale. |

### `list_operation_types`

Lista todos los tipos de operación del timeline que acepta run_operation: tipo, etiqueta y una línea que dice qué hace.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call list_operation_types --doc pieza.omnicad`

### `describe_operation`

Explica un tipo de operación: parámetros con su valor por defecto, tipo, si aceptan expresiones, en los de lista cerrada sus valores válidos (choices), en los que guardan referencias qué esperan y en qué formas cortas (format, reference_formats), aclaraciones (notes); el docstring completo y un ejemplo de llamada a run_operation.

- Modifica el documento: no.
- Parámetros:
  - `type` (texto; obligatorio): tipo de operación (list_operation_types los lista), p. ej. "primitiva".
- CLI: `omnicad call describe_operation --doc pieza.omnicad type=…`

### `run_operation`

Agrega al timeline cualquier operación por su tipo y sus parámetros nativos (claves en español, las de describe_operation). En los campos que guardan referencias acepta formas cortas y las traduce: ids de find_faces / find_edges ("Cuerpo1/F3"), selectores ("faces:>Z"), "XY", "Z", "O", planos/ejes/puntos de construcción y bocetos por id o nombre, {"sketch": …, "point" | "curve" | "profile": …}, {"body": …} y nombres de cuerpo en los campos de ids de cuerpo (describe_operation los lista). Lo que no reconoce llega igual al paso, que dice qué campo está mal. Una llamada = un paso de deshacer; si el paso falla, el documento queda intacto.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `type` (texto; obligatorio): tipo de operación (list_operation_types los lista).
  - `params` (objeto; opcional, por defecto `null`): parámetros a cambiar respecto de los valores por defecto, con las claves de describe_operation. Las referencias pueden ir en forma corta (ver reference_formats de describe_operation).
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = el automático.
- CLI: `omnicad call run_operation --doc pieza.omnicad type=…`

### `get_recipe`

Devuelve la receta JSON completa del documento (parámetros, timeline y propiedades): es lo que guarda el archivo .omnicad y lo que acepta apply_recipe.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call get_recipe --doc pieza.omnicad`

### `apply_recipe`

Carga una receta JSON (la de get_recipe): 'replace' reemplaza todo el documento; 'append' agrega sus pasos y parámetros al final. Es un paso de deshacer; si algo falla, el documento queda intacto.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `recipe` (objeto; obligatorio): la receta de get_recipe: su resultado {"recipe": …} tal cual o el objeto de adentro (con 'operaciones', 'parametros', etc.).
  - `mode` ("replace" | "append"; opcional, por defecto `"replace"`): "replace" reemplaza el contenido del documento (conserva su archivo); "append" suma al final del timeline los pasos y parámetros de la receta (renumera los ids que chocan; un parámetro con el mismo nombre y otra expresión es un error) y deja el marcador al final.
- CLI: `omnicad call apply_recipe --doc pieza.omnicad recipe=…`

### `execute_code`

Ejecuta código Python con api, sesion, doc y llamar(nombre, args) ya definidos. Devuelve lo impreso (stdout) y la variable `result` si el código la define. Todo es un paso de deshacer; si el código lanza una excepción, el documento queda intacto. Corre como mucho `timeout` segundos (60 por defecto): al vencer se corta con CODE_TIMEOUT y el documento vuelve a como estaba. En vivo se puede cancelar mientras corre (botón Cancelar del diálogo): responde CODE_CANCELLED y el documento también vuelve a como estaba.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `code` (texto; obligatorio): código Python. Definidos: api (el paquete omnicad.api), sesion, doc (el documento activo) y llamar (atajo de api.llamar(sesion, nombre, args); NUNCA lanza: devuelve un dict con ok y, si falló, error_kind). Si alguna llamada falla, el resultado trae failed_calls y un aviso; si fallan TODAS, el resultado es CODE_ERROR y el documento vuelve a como estaba.
  - `timeout` (número; opcional, por defecto `60.0`): segundos como máximo (60 por defecto); al vencer se corta el código, el documento vuelve a como estaba y responde CODE_TIMEOUT. null = sin límite (en vivo no se acepta; el máximo es 100 s). Solo se vigila tu código: una llamada larga a una herramienta termina antes del corte. También se puede cancelar desde afuera (en vivo, el botón Cancelar): responde CODE_CANCELLED con el mismo rollback.
- CLI: `omnicad call execute_code --doc pieza.omnicad code=…`

### `get_guide`

Guía corta para agentes (ciclo de trabajo, unidades, cómo leer errores). Sin tema devuelve el índice.

- Modifica el documento: no.
- Parámetros:
  - `topic` (texto; opcional, por defecto `null`): tema de la guía (el índice los lista), p. ej. "flujo"; vacío = el índice.
- CLI: `omnicad call get_guide --doc pieza.omnicad`

### `search_help`

Busca en la ayuda LOCAL de OmniCAD (catálogo de herramientas, guía para agentes y documentación del repo si está) y devuelve fragmentos cortos con su fuente, para responder «¿cómo se hace…?» citando de dónde sale. Acepta palabras con o sin tildes, en español o inglés.

- Modifica el documento: no.
- Parámetros:
  - `query` (texto; obligatorio): qué se busca, en pocas palabras (p. ej. "empalme", "agujero roscado", "fillet").
  - `limit` (entero; opcional, por defecto `5`): cuántos resultados como máximo, de 1 a 20.
- CLI: `omnicad call search_help --doc pieza.omnicad query=…`

## Grupo grafo

Programación visual sin ventana (tipo Grasshopper): correr grafos de nodos y hornearlos en el timeline.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`list_graph_nodes`](#list_graph_nodes) | no | Lista los tipos de nodo para armar grafos de programación visual (tipo Grasshopper) que corren sin ventana con run_graph y se hornean con bake_graph: tipo, categoría, descripción y cada entrada y salida con su tipo de dato, acceso (item, lista o árbol), unidad y valor por defecto. |
| [`run_graph`](#run_graph) | no | Evalúa un grafo de nodos (programación visual tipo Grasshopper: flujo de datos con listas y árboles) SIN tocar el documento. |
| [`bake_graph`](#bake_graph) | sí | Hornea un grafo en el documento: agrega UN paso «Grafo» al timeline que guarda el grafo y sus entradas y lo vuelve a evaluar en cada recálculo (paramétrico: una entrada como "ancho / 2" o un nodo «parametro» siguen a los parámetros del documento, y el paso se edita con edit_feature). |

### `list_graph_nodes`

Lista los tipos de nodo para armar grafos de programación visual (tipo Grasshopper) que corren sin ventana con run_graph y se hornean con bake_graph: tipo, categoría, descripción y cada entrada y salida con su tipo de dato, acceso (item, lista o árbol), unidad y valor por defecto. Trae también el formato JSON del grafo con un ejemplo.

- Modifica el documento: no.
- Parámetros:
  - `category` ("entrada" | "matematica" | "listas" | "arboles" | "vectores" | "curvas" | "solidos" | "salida" o null; opcional, por defecto `null`): categoría de nodos: entrada, matematica, listas, arboles, vectores, curvas, solidos o salida; vacío = todas.
  - `query` (texto; opcional, por defecto `null`): texto a buscar en el tipo, el título o la descripción (sin distinguir mayúsculas); vacío = todos.
  - `include_format` (true/false; opcional, por defecto `true`): true para incluir el formato JSON del grafo, las reglas de emparejado y un ejemplo.
- CLI: `omnicad call list_graph_nodes --doc pieza.omnicad`

### `run_graph`

Evalúa un grafo de nodos (programación visual tipo Grasshopper: flujo de datos con listas y árboles) SIN tocar el documento. Devuelve el valor de cada nodo «salida» (los cuerpos con volumen, área y caja), las entradas usadas y el estado y el tiempo de cada nodo; con export guarda los cuerpos de las salidas (.step, .stl, .3mf, .obj…). Las entradas se cambian por nombre en inputs (también con expresiones de parámetros del documento). Llamar de nuevo con el mismo grafo recalcula solo los nodos que dependen de lo que cambió. list_graph_nodes trae los nodos y el formato.

- Modifica el documento: no.
- Parámetros:
  - `graph` (objeto o texto; obligatorio): el grafo (objeto con "nodos"; ver list_graph_nodes), su texto JSON o la ruta a un archivo .json con el grafo o con {"graph", "inputs"}.
  - `inputs` (objeto; opcional, por defecto `null`): valores de entrada por nombre, p. ej. {"lado": 20, "alto": "espesor * 2"}: el nombre (o id) de un nodo de entrada cambia su valor; "nodo.entrada" cambia cualquier entrada de un nodo. Acepta números, expresiones con parámetros del documento, listas y puntos [x, y, z].
  - `outputs` (lista de texto o null; opcional, por defecto `null`): nombres de las salidas a devolver y exportar; vacío = todas.
  - `export` (texto; opcional, por defecto `null`): ruta del archivo donde guardar los cuerpos de las salidas (.step/.stp, .stl, .obj, .3mf, .ply, .iges/.igs, .brep); vacío = no exporta.
  - `overwrite` (true/false; opcional, por defecto `false`): true para reemplazar el archivo de export si ya existe.
  - `include_nodes` (true/false; opcional, por defecto `true`): true para incluir el estado, los mensajes y el tiempo de cada nodo.
- CLI: `omnicad call run_graph --doc pieza.omnicad graph=…`

### `bake_graph`

Hornea un grafo en el documento: agrega UN paso «Grafo» al timeline que guarda el grafo y sus entradas y lo vuelve a evaluar en cada recálculo (paramétrico: una entrada como "ancho / 2" o un nodo «parametro» siguen a los parámetros del documento, y el paso se edita con edit_feature). Los cuerpos salen de los nodos «salida»; operation los aplica como cuerpo nuevo, unir, cortar o intersecar. Con fixed=true deja cuerpos fijos (operación base, sin el grafo).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `graph` (objeto o texto; obligatorio): el grafo (objeto con "nodos"; ver list_graph_nodes), su texto JSON o la ruta a un archivo .json con el grafo o con {"graph", "inputs"}.
  - `inputs` (objeto; opcional, por defecto `null`): valores de entrada por nombre (como en run_graph); las expresiones con parámetros del documento quedan enlazadas: al cambiar el parámetro, el paso se recalcula.
  - `outputs` (lista de texto o null; opcional, por defecto `null`): nombres de las salidas cuyos cuerpos se hornean; vacío = todas.
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect" (con fixed=true, solo new_body).
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) para join, cut o intersect (id o nombre); vacío = los sólidos que toca.
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = el automático.
  - `fixed` (true/false; opcional, por defecto `false`): true para hornear cuerpos fijos (operación base) en vez del grafo paramétrico.
- CLI: `omnicad call bake_graph --doc pieza.omnicad graph=…`

## Grupo asistente

Asistente IA: su configuración, pedidos sin ventana (gastan en la API) y el historial de chats (en el MCP, solo con --toolsets; en la CLI, `omnicad assistant_ask`).

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`get_assistant_config`](#get_assistant_config) | no | Configuración del Asistente IA (Preferencias › Asistente IA): proveedor, modelo, base_url, modo por defecto, tope de gasto, imágenes, instrucciones propias, permisos y si el chat muestra las herramientas. |
| [`set_assistant_config`](#set_assistant_config) | sí | Cambia la configuración del Asistente IA (solo los campos pasados). |
| [`get_project_instructions`](#get_project_instructions) | no | Instrucciones de este proyecto para el Asistente IA: van dentro del .omnicad y se suman a las propias (get_assistant_config). |
| [`set_project_instructions`](#set_project_instructions) | sí | Cambia las instrucciones de este proyecto para el Asistente IA. Se guardan con el diseño (save_document) pero no entran en deshacer, como los comentarios. |
| [`list_assistant_models`](#list_assistant_models) | no | Modelos que se pueden elegir para el Asistente IA, como el combo «Modelo» de Preferencias: los de OpenCode y Codex los pregunta a su CLI; los de Claude Code son sus alias y nombres; por API, GET /models (no gasta). |
| [`assistant_ask`](#assistant_ask) | sí | Corre un pedido al Asistente IA SIN ventana, sobre el documento de esta sesión, con el proveedor configurado (get_assistant_config). |
| [`list_assistant_chats`](#list_assistant_chats) | no | Lista los chats guardados del Asistente (el más nuevo primero): id, título, fecha, modo, proveedor, modelo y cantidad de mensajes. |
| [`get_assistant_chat`](#get_assistant_chat) | no | Lee un chat guardado del Asistente: los textos de la conversación y las herramientas que usó, sin imágenes. |

### `get_assistant_config`

Configuración del Asistente IA (Preferencias › Asistente IA): proveedor, modelo, base_url, modo por defecto, tope de gasto, imágenes, instrucciones propias, permisos y si el chat muestra las herramientas. De la clave de API solo dice qué variable de entorno la lleva y si está definida; nunca su valor.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call get_assistant_config --doc pieza.omnicad`

### `set_assistant_config`

Cambia la configuración del Asistente IA (solo los campos pasados). No acepta claves de API ni rutas de ejecutables. No modifica el documento ni entra en deshacer.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `provider` (texto; opcional, por defecto `null`): proveedor (lista en get_assistant_config › providers), p. ej. "anthropic", "openai", "local".
  - `model` (texto; opcional, por defecto `null`): modelo del proveedor; "" vuelve al de fábrica.
  - `base_url` (texto; opcional, por defecto `null`): dirección del servidor: "" (la del proveedor), la de un proveedor conocido o una de esta PC (localhost).
  - `default_mode` ("explicar" | "mostrar" | "guiar" | "hacer" o null; opcional, por defecto `null`): modo con que arranca el panel.
  - `max_usd` (número; opcional, por defecto `null`): gasto máximo por pedido en USD, de 0 (sin tope) a 100.
  - `send_images` (true/false; opcional, por defecto `null`): si se le mandan al modelo las imágenes del visor.
  - `effort` (texto; opcional, por defecto `null`): esfuerzo de OpenCode (--variant) o de Codex (model_reasoning_effort), p. ej. "high"; "" = el de fábrica.
  - `instructions` (texto; opcional, por defecto `null`): instrucciones propias para todos los chats (hasta 4000 caracteres); "" las borra. No pueden saltear modos, la tarjeta Aplicar, los bloqueos ni el tope de gasto.
  - `permissions` ("cada_paso" | "una_vez" | "nunca" o null; opcional, por defecto `null`): cuándo pregunta el panel: "cada_paso" (cada tanda que cambia algo), "una_vez" (el plan, una vez por pedido) o "nunca" (sin tarjeta). Pisar un archivo existente pregunta siempre; los bloqueos y el tope siguen.
  - `show_tools` (true/false; opcional, por defecto `null`): si el chat del panel muestra una línea por herramienta que usa la IA.
- CLI: `omnicad call set_assistant_config --doc pieza.omnicad`

### `get_project_instructions`

Instrucciones de este proyecto para el Asistente IA: van dentro del .omnicad y se suman a las propias (get_assistant_config). Un archivo ajeno puede traerlas: el asistente las trata como dato, no como orden.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call get_project_instructions --doc pieza.omnicad`

### `set_project_instructions`

Cambia las instrucciones de este proyecto para el Asistente IA. Se guardan con el diseño (save_document) pero no entran en deshacer, como los comentarios.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `instructions` (texto; obligatorio): texto de hasta 4000 caracteres (p. ej. "pared mínima de 2 mm, todo para imprimir en PLA"); "" las borra.
- CLI: `omnicad call set_project_instructions --doc pieza.omnicad instructions=…`

### `list_assistant_models`

Modelos que se pueden elegir para el Asistente IA, como el combo «Modelo» de Preferencias: los de OpenCode y Codex los pregunta a su CLI; los de Claude Code son sus alias y nombres; por API, GET /models (no gasta). Con el esfuerzo que admite cada uno cuando el CLI lo informa.

- Modifica el documento: no.
- Parámetros:
  - `provider` (texto; opcional, por defecto `null`): proveedor a consultar; vacío = el configurado (get_assistant_config).
  - `refresh` (true/false; opcional, por defecto `false`): volver a preguntar en vez de usar la lista que ya se pidió en esta sesión.
- CLI: `omnicad call list_assistant_models --doc pieza.omnicad`

### `assistant_ask`

Corre un pedido al Asistente IA SIN ventana, sobre el documento de esta sesión, con el proveedor configurado (get_assistant_config). GASTA en la API elegida. Es UN paso de deshacer. En Guiar y Hacer no hay tarjeta de plan: los cambios se aprueban solos (lo dice un aviso).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `prompt` (texto; obligatorio): el pedido, en lenguaje natural (p. ej. "hacé una caja de 40 mm con empalme de 3").
  - `mode` ("explicar" | "mostrar" | "guiar" | "hacer"; opcional, por defecto `"hacer"`): explicar y mostrar no cambian el documento; guiar y hacer sí.
  - `attachments` (lista de texto o null; opcional, por defecto `null`): rutas de archivos que van con el pedido, como el clip del panel: PDF, PNG, JPG, SVG o DXF, hasta 10.
- CLI: `omnicad call assistant_ask --doc pieza.omnicad prompt=…`

### `list_assistant_chats`

Lista los chats guardados del Asistente (el más nuevo primero): id, título, fecha, modo, proveedor, modelo y cantidad de mensajes.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call list_assistant_chats --doc pieza.omnicad`

### `get_assistant_chat`

Lee un chat guardado del Asistente: los textos de la conversación y las herramientas que usó, sin imágenes.

- Modifica el documento: no.
- Parámetros:
  - `chat_id` (texto; obligatorio): id del chat (list_assistant_chats).
- CLI: `omnicad call get_assistant_chat --doc pieza.omnicad chat_id=…`

## Grupo dev

Desarrollo del programa (en el MCP, solo con --dev; en la CLI, `omnicad dev`).

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`run_checks`](#run_checks) | no | Corre la verificación del proyecto (ruff, pytest y, si se pide, la prueba de humo de la interfaz) y devuelve un resumen por paso. |
| [`app_screenshot`](#app_screenshot) | no | Abre la ventana REAL de OmniCAD en otro proceso, espera a que dibuje, captura la ventana entera y la cierra. |
| [`list_error_reports`](#list_error_reports) | no | Lista los informes de error guardados por las sesiones de OmniCAD (uno por sesión, del más nuevo al más viejo). |
| [`read_error_report`](#read_error_report) | no | Devuelve el contenido de un informe de error (versión, sistema y la traza de cada error de esa sesión). |
| [`run_bench`](#run_bench) | no | Mide el rendimiento de OmniCAD con la ventana real: arranque, memoria, recálculo de un modelo grande (placa con N×N agujeros) y cuadros por segundo al girar la vista. |

### `run_checks`

Corre la verificación del proyecto (ruff, pytest y, si se pide, la prueba de humo de la interfaz) y devuelve un resumen por paso. Es lo que hay que correr antes de dar un cambio por bueno.

- Modifica el documento: no.
- Parámetros:
  - `include_smoke` (true/false; opcional, por defecto `true`): true corre también la prueba de humo (abre la ventana real; tarda 1 a 2 minutos).
  - `pytest_args` (texto; opcional, por defecto `""`): argumentos de pytest separados por espacios, p. ej. "tests/test_parametros.py -k ancho"; vacío = toda la suite.
- CLI: `omnicad call run_checks --doc pieza.omnicad`

### `app_screenshot`

Abre la ventana REAL de OmniCAD en otro proceso, espera a que dibuje, captura la ventana entera y la cierra. Es la forma de ver la interfaz tal como la ve una persona.

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; opcional, por defecto `null`): ruta del PNG donde guardar la captura además de devolverla; vacío = no se guarda en disco.
  - `example` (true/false; opcional, por defecto `false`): true abre el modelo de ejemplo.
  - `project` (texto; opcional, por defecto `null`): ruta de un proyecto .omnicad a abrir; no se combina con example.
  - `width` (entero; opcional, por defecto `1600`): ancho de la captura en píxeles (320 a 4000).
  - `height` (entero; opcional, por defecto `900`): alto de la captura en píxeles (240 a 3000).
  - `theme` (texto; opcional, por defecto `null`): tema de la interfaz: oscuro_moderno, claro_moderno, azul_profesional, minimalista, clasico o usuario:<archivo>; vacío = el de fábrica.
- CLI: `omnicad call app_screenshot --doc pieza.omnicad`

### `list_error_reports`

Lista los informes de error guardados por las sesiones de OmniCAD (uno por sesión, del más nuevo al más viejo).

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call list_error_reports --doc pieza.omnicad`

### `read_error_report`

Devuelve el contenido de un informe de error (versión, sistema y la traza de cada error de esa sesión).

- Modifica el documento: no.
- Parámetros:
  - `name` (texto; opcional, por defecto `""`): nombre del archivo del informe (de list_error_reports); vacío = el más reciente.
- CLI: `omnicad call read_error_report --doc pieza.omnicad`

### `run_bench`

Mide el rendimiento de OmniCAD con la ventana real: arranque, memoria, recálculo de un modelo grande (placa con N×N agujeros) y cuadros por segundo al girar la vista. Repite la medición y devuelve la mediana de cada número. Sirve para comparar antes y después de optimizar.

- Modifica el documento: no.
- Parámetros:
  - `repetitions` (entero; opcional, por defecto `3`): cuántas veces medir (1 a 10); el resultado es la mediana de cada número.
  - `side` (entero; opcional, por defecto `8`): agujeros por lado del modelo grande (1 a 20; 8 = 64 agujeros y 73 pasos).
  - `frames` (entero; opcional, por defecto `120`): cuadros de la órbita para medir los cuadros por segundo (10 a 1000).
  - `preset` ("rendimiento" | "equilibrado" | "calidad" | "personalizar" o null; opcional, por defecto `null`): valor predefinido de gráficos con el que medir; vacío = el de fábrica (personalizar).
- CLI: `omnicad call run_bench --doc pieza.omnicad`
