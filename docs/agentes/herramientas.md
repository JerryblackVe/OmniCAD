<!-- ARCHIVO GENERADO: no editar a mano. Regenerar con: omnicad tools --markdown --output docs/agentes/herramientas.md -->

# Herramientas de OmniCAD

> Archivo generado: no editar a mano. Regenerar con `omnicad tools --markdown --output docs/agentes/herramientas.md` (desde la raíz del repo).
> Sale del catálogo de `omnicad.api`, la misma fuente del servidor MCP y de la CLI. Un test avisa si queda viejo.

163 herramientas en 13 grupos. Unidades: mm y grados. Nombres, parámetros y claves del resultado en inglés; textos en español.
Cada llamada devuelve `{"ok": true, "result": ..., "avisos": [...]}` o `{"ok": false, "error_kind": ..., "mensaje": ..., "pistas": [...]}`.

El servidor MCP en modo en vivo o auto suma `get_mode`, que no está en el catálogo (ver `puente.md`).

| Grupo | Herramientas | Para qué |
|---|---|---|
| [documento](#grupo-documento) | 15 | Archivo, escena, timeline y deshacer. |
| [parametros](#grupo-parametros) | 4 | Medidas con nombre que gobiernan el modelo. |
| [boceto](#grupo-boceto) | 29 | Bocetos 2D: geometría, restricciones y cotas. |
| [vectores](#grupo-vectores) | 16 | Texto y vectores: fuentes, texto de boceto, SVG, DXF e imágenes vectorizadas. |
| [solido](#grupo-solido) | 25 | Sólidos: extruir, revolucionar, primitivas, empalmes, agujeros y patrones. |
| [chapa](#grupo-chapa) | 17 | Chapa metálica: reglas, pestañas, dobladillo, plegar, desplegar, desgarro, patrón plano y DXF. |
| [malla](#grupo-malla) | 15 | Mallas de triángulos: teselar, reparar, limpiar, reducir, remallar, suavizar, vaciar, cortar, combinar, separar y convertir a sólido (traer un .stl/.obj/.3mf/.ply: insert_file). |
| [ensamble](#grupo-ensamble) | 11 | Ensamble: componentes, uniones, accionar, límites, grupos rígidos, vínculos y estudio de movimiento. |
| [material](#grupo-material) | 6 | Materiales físicos (densidad para la masa), materiales propios y aspecto de los cuerpos. |
| [inspeccion](#grupo-inspeccion) | 12 | Ver y medir el resultado. |
| [avanzado](#grupo-avanzado) | 7 | Cualquier operación, receta, código y guía. |
| [grafo](#grupo-grafo) | 3 | Programación visual sin ventana (tipo Grasshopper): correr grafos de nodos y hornearlos en el timeline. |
| [dev](#grupo-dev) | 3 | Desarrollo del programa (en el MCP, solo con --dev; en la CLI, `omnicad dev`). |

## Grupo documento

Archivo, escena, timeline y deshacer.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`get_scene_info`](#get_scene_info) | no | Resumen del documento: nombre, archivo, cambios sin guardar, unidades, cuerpos (id, nombre, tipo, volumen mm³, área mm², caja envolvente), bocetos (plano y perfiles), componentes (id, nombre, fijo, cuerpos, matriz 4×4 en mm), uniones (tipo, componente 1 que se mueve y 2, valores: rotation en grados, slide en mm), grupos rígidos, cantidad de pasos del timeline y parámetros. |
| [`new_document`](#new_document) | sí | Empieza un documento vacío en lugar del actual. |
| [`open_document`](#open_document) | sí | Abre un archivo y lo deja como documento activo: proyecto .omnicad (o .fclone), o como documento nuevo con un paso de importación STEP (.step/.stp, con nombres, colores y componentes), IGES (.iges/.igs), malla (.stl, .obj, .3mf, .ply), DXF (boceto en XY), BREP (.brep/.brp, como operación base) o Fusion 360 (.f3d, .f3z: se leen sus cuerpos SIN Fusion, como operación base; el historial, los parámetros y los nombres de los cuerpos no se leen). |
| [`insert_file`](#insert_file) | sí | Inserta un archivo en el documento ACTUAL como un paso nuevo del timeline (Insertar de Fusion): STEP .step/.stp (con nombres, colores y componentes), IGES .iges/.igs, malla .stl/.obj/.3mf/.ply, Fusion 360 .f3d/.f3z (sus cuerpos, leídos sin Fusion) u otro diseño .omnicad/.fclone (entra como componente). |
| [`save_document`](#save_document) | no | Guarda el documento como proyecto .omnicad. |
| [`export`](#export) | no | Exporta cuerpos a un archivo; el formato sale de la extensión: .stl, .obj, .3mf, .ply (mallas), .glb/.gltf (glTF 2.0 para web y realidad aumentada: malla con el color y el acabado de cada cuerpo como material PBR, en metros y con Y arriba), .step/.stp, .iges/.igs, .brep (sólidos exactos) o .dxf (patrón plano de un cuerpo de chapa). |
| [`undo`](#undo) | sí | Deshace el último cambio del documento (cada herramienta que modifica es un paso). |
| [`redo`](#redo) | sí | Rehace el último cambio deshecho. |
| [`get_timeline`](#get_timeline) | no | Lista los pasos del timeline en orden: índice, id, tipo, nombre, si está suprimido, estado (ok, warning, error, suppressed, rolled_back), mensaje, parámetros tal como se guardaron (params: expresiones como «5 * placa»), cuánto da cada expresión con los parámetros actuales (values, en mm o grados) y, en primitivas y Mover, qué campo guardado corresponde a cada argumento de la herramienta (aliases: length → ancho = X, width → largo = Y…), que edit_feature también acepta. |
| [`edit_feature`](#edit_feature) | sí | Cambia parámetros de un paso del timeline (conserva su id) y recalcula. |
| [`suppress_feature`](#suppress_feature) | sí | Suprime o reactiva un paso del timeline (suprimido = no se calcula). |
| [`delete_feature`](#delete_feature) | sí | Borra un paso del timeline. |
| [`rename`](#rename) | sí | Renombra un paso del timeline o un cuerpo. |
| [`set_marker`](#set_marker) | sí | Mueve el marcador del timeline (Fusion: «Rodar marcador aquí» del menú contextual). |
| [`get_profile_sketches`](#get_profile_sketches) | no | Bocetos que usa un paso del timeline (perfiles de una extrusión o revolución, ruta de un barrido…), en orden: lo mismo que abre «Editar boceto de perfil» en el timeline. |

### `get_scene_info`

Resumen del documento: nombre, archivo, cambios sin guardar, unidades, cuerpos (id, nombre, tipo, volumen mm³, área mm², caja envolvente), bocetos (plano y perfiles), componentes (id, nombre, fijo, cuerpos, matriz 4×4 en mm), uniones (tipo, componente 1 que se mueve y 2, valores: rotation en grados, slide en mm), grupos rígidos, cantidad de pasos del timeline y parámetros.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call get_scene_info --doc pieza.omnicad`

### `new_document`

Empieza un documento vacío en lugar del actual. Si el actual tiene cambios sin guardar falla con UNSAVED_CHANGES, salvo discard=true (los descarta).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `name` (texto; opcional, por defecto `"Sin título"`): nombre del documento nuevo.
  - `discard` (true/false; opcional, por defecto `false`): true para descartar los cambios sin guardar del documento actual.
- CLI: `omnicad call new_document --doc pieza.omnicad`

### `open_document`

Abre un archivo y lo deja como documento activo: proyecto .omnicad (o .fclone), o como documento nuevo con un paso de importación STEP (.step/.stp, con nombres, colores y componentes), IGES (.iges/.igs), malla (.stl, .obj, .3mf, .ply), DXF (boceto en XY), BREP (.brep/.brp, como operación base) o Fusion 360 (.f3d, .f3z: se leen sus cuerpos SIN Fusion, como operación base; el historial, los parámetros y los nombres de los cuerpos no se leen). Si el actual tiene cambios sin guardar falla con UNSAVED_CHANGES, salvo discard=true (los descarta). Para meter el archivo en el documento actual: insert_file.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `path` (texto; obligatorio): ruta del archivo.
  - `mesh_units` ("mm" | "cm" | "m" | "in" | "ft"; opcional, por defecto `"mm"`): unidades de un .stl, .obj o .ply (no las guardan); el .3mf trae las suyas.
  - `discard` (true/false; opcional, por defecto `false`): true para descartar los cambios sin guardar del documento actual.
- CLI: `omnicad call open_document --doc pieza.omnicad path=…`

### `insert_file`

Inserta un archivo en el documento ACTUAL como un paso nuevo del timeline (Insertar de Fusion): STEP .step/.stp (con nombres, colores y componentes), IGES .iges/.igs, malla .stl/.obj/.3mf/.ply, Fusion 360 .f3d/.f3z (sus cuerpos, leídos sin Fusion) u otro diseño .omnicad/.fclone (entra como componente). El contenido se copia dentro de la receta. Para abrirlo como documento nuevo: open_document.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `path` (texto; obligatorio): ruta del archivo a insertar.
  - `mesh_units` ("mm" | "cm" | "m" | "in" | "ft"; opcional, por defecto `"mm"`): unidades de un .stl, .obj o .ply (no las guardan); el .3mf trae las suyas.
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = «Importar archivo.ext» / «Insertar archivo».
- CLI: `omnicad call insert_file --doc pieza.omnicad path=…`

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

### `set_marker`

Mueve el marcador del timeline (Fusion: «Rodar marcador aquí» del menú contextual). Lo que queda a la derecha del marcador no se calcula (estado rolled_back) hasta volver a moverlo. Indicá UNO: position, after (el marcador queda justo después de ese paso, que sí se calcula) o before (justo antes). undo lo vuelve a donde estaba. Si al avanzar un paso queda con error, se avisa (errors) pero el marcador se mueve igual (como en la app).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `position` (entero; opcional, por defecto `null`): índice del marcador: 0 = antes del primer paso; la cantidad de pasos = al final (todo calculado).
  - `after` (texto; opcional, por defecto `null`): id o nombre de un paso: el marcador queda justo después (como «Rodar marcador aquí» sobre ese paso).
  - `before` (texto; opcional, por defecto `null`): id o nombre de un paso: el marcador queda justo antes (ni ese paso ni los siguientes se calculan).
- CLI: `omnicad call set_marker --doc pieza.omnicad`

### `get_profile_sketches`

Bocetos que usa un paso del timeline (perfiles de una extrusión o revolución, ruta de un barrido…), en orden: lo mismo que abre «Editar boceto de perfil» en el timeline. Sus ids sirven como «sketch» de las herramientas de boceto (get_sketch, draw_line…).

- Modifica el documento: no.
- Parámetros:
  - `feature` (texto; obligatorio): id o nombre del paso (p. ej. una extrusión).
- CLI: `omnicad call get_profile_sketches --doc pieza.omnicad feature=…`

## Grupo parametros

Medidas con nombre que gobiernan el modelo.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`get_parameters`](#get_parameters) | no | Lista los parámetros de usuario: expresión, valor calculado, unidad (mm o deg) y qué pasos del timeline los usan. |
| [`create_parameter`](#create_parameter) | sí | Crea un parámetro de usuario. |
| [`set_parameter`](#set_parameter) | sí | Cambia la expresión de un parámetro existente y recalcula el modelo. |
| [`delete_parameter`](#delete_parameter) | sí | Borra un parámetro que no use ningún paso ni otro parámetro. |

### `get_parameters`

Lista los parámetros de usuario: expresión, valor calculado, unidad (mm o deg) y qué pasos del timeline los usan.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call get_parameters --doc pieza.omnicad`

### `create_parameter`

Crea un parámetro de usuario. La magnitud sale de la expresión: con unidad de ángulo (deg, rad, °) es un ángulo; si no, una longitud en mm.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `name` (texto; obligatorio): nombre del parámetro (letras, números y '_', sin empezar con número), p. ej. "ancho".
  - `expression` (número o expresión; obligatorio): valor: número (mm) o expresión con unidades y otros parámetros, p. ej. "60 mm", "ancho / 2", "30 deg".
  - `comment` (texto; opcional, por defecto `""`): comentario opcional que se ve en la tabla de parámetros.
- CLI: `omnicad call create_parameter --doc pieza.omnicad name=… expression=…`

### `set_parameter`

Cambia la expresión de un parámetro existente y recalcula el modelo. Si algún paso queda con error, el cambio se descarta.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `name` (texto; obligatorio): nombre exacto del parámetro.
  - `expression` (número o expresión; obligatorio): valor nuevo: número (en la unidad del parámetro) o expresión, p. ej. "80 mm" o "ancho * 2".
- CLI: `omnicad call set_parameter --doc pieza.omnicad name=… expression=…`

### `delete_parameter`

Borra un parámetro que no use ningún paso ni otro parámetro.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `name` (texto; obligatorio): nombre exacto del parámetro.
- CLI: `omnicad call delete_parameter --doc pieza.omnicad name=…`

## Grupo boceto

Bocetos 2D: geometría, restricciones y cotas.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`create_construction_plane`](#create_construction_plane) | sí | Crea un plano de construcción desfasado de un plano de origen (XY, XZ, YZ) o de otro plano de construcción. |
| [`create_sketch`](#create_sketch) | sí | Crea un boceto vacío sobre un plano o sobre una cara plana. |
| [`draw_line`](#draw_line) | sí | Dibuja una línea en el boceto (un paso de deshacer). |
| [`draw_rectangle`](#draw_rectangle) | sí | Dibuja un rectángulo (4 líneas con restricciones horizontal y vertical). |
| [`draw_circle`](#draw_circle) | sí | Dibuja un círculo por centro y radio (un paso de deshacer). |
| [`draw_arc`](#draw_arc) | sí | Dibuja un arco. |
| [`create_polygon`](#create_polygon) | sí | Dibuja un polígono regular de n lados (líneas iguales sobre un círculo guía de construcción, como la interfaz). |
| [`draw_spline`](#draw_spline) | sí | Dibuja una spline: de ajuste (pasa por los puntos) o de puntos de control (grado 3 o 5, necesita al menos grado+1 puntos). |
| [`add_constraint`](#add_constraint) | sí | Agrega una restricción geométrica entre entidades del boceto (ids de get_sketch: curvas y puntos). |
| [`add_dimension`](#add_dimension) | sí | Agrega una cota (dimensión) que maneja la geometría. |
| [`get_sketch`](#get_sketch) | no | Informe de un boceto: plano y su marco 3D, entidades con ids estables (coordenadas ya resueltas por el solver), puntos, restricciones, cotas con su valor, perfiles (índice, área mm², centroide, caja [min/max en coordenadas del boceto] y curvas del borde) y estado (fully_constrained, under_constrained, over_constrained) con los grados de libertad. |
| [`sketch_from_spec`](#sketch_from_spec) | sí | Crea un boceto COMPLETO en una sola llamada (un paso de deshacer): geometría, restricciones y cotas. entities: lista de {type, ...}: line{start,end}, rectangle{corner1,corner2 \| center,width,height \| origin,width,height}, circle{center,radius}, arc{center,start,sweep \| start,mid,end}, polygon{sides,radius,center,rotation,kind,fully_constrained}, ellipse{center,major_radius,minor_radius,angle}, slot{kind,points,width} (kind como en draw_slot), spline{points,spline_type,degree,closed}, point{at}; todas aceptan id (nombre propio para citarla) y construction. |
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
| [`mirror_sketch`](#mirror_sketch) | sí | Simetría de boceto (Fusion: Simetría): copia espejada de curvas y puntos respecto de una línea del boceto, con restricciones de simetría (si la geometría original cambia, la copia la sigue). |
| [`sketch_rectangular_pattern`](#sketch_rectangular_pattern) | sí | Patrón rectangular de boceto (Fusion: Patrón rectangular en el boceto): copias de curvas y puntos en una o dos direcciones, atadas al original con la restricción de patrón (si el original cambia, las copias lo siguen). |
| [`sketch_circular_pattern`](#sketch_circular_pattern) | sí | Patrón circular de boceto (Fusion: Patrón circular en el boceto): copias de curvas y puntos alrededor de un centro, atadas al original con la restricción de patrón. total_angle = 360 reparte la cantidad en la vuelta entera; otro ángulo pone la primera y la última copia en sus extremos. |
| [`project_to_sketch`](#project_to_sketch) | sí | Proyecta aristas, caras o cuerpos del modelo sobre el plano del boceto (Fusion: Proyectar) o agrega donde cortan ese plano (mode=intersect; Fusion: Intersecar). |
| [`set_line_type`](#set_line_type) | sí | Cambia el tipo de línea de curvas del boceto (Fusion: Construcción / Línea central de la paleta): normal (forma perfiles), construction (de construcción: guía, no forma perfiles) o centerline (eje: forma perfiles y sirve de eje de revolución). |
| [`edit_dimension`](#edit_dimension) | sí | Cambia el valor de una cota que ya existe (Fusion: doble clic en la cota): número o expresión con parámetros. |
| [`auto_constrain`](#auto_constrain) | sí | Restringe automáticamente el boceto (Fusion: Restringir automáticamente): agrega coincidencias, horizontales, verticales e igualdades que ya se cumplen y después cotas (largos, radios, ángulos y posiciones desde un punto fijo en el origen) con las medidas actuales, hasta dejarlo totalmente restringido si se puede. |

### `create_construction_plane`

Crea un plano de construcción desfasado de un plano de origen (XY, XZ, YZ) o de otro plano de construcción. Sirve para dibujar bocetos fuera del origen. Va en el grupo «boceto» porque su uso típico es create_sketch(plane=<este plano>). El desfase es sobre la normal del plano base.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `plane` (texto; opcional, por defecto `"XY"`): plano base: "XY", "XZ", "YZ" o el id/nombre de otro plano de construcción.
  - `offset` (número o expresión; opcional, por defecto `"10 mm"`): desfase en mm sobre la normal del plano base (número o expresión con parámetros, p. ej. "alto / 2").
  - `name` (texto; opcional, por defecto `null`): nombre del plano; vacío = "Plano1", "Plano2"…
- CLI: `omnicad call create_construction_plane --doc pieza.omnicad`

### `create_sketch`

Crea un boceto vacío sobre un plano o sobre una cara plana. Coordenadas del boceto (mm): en XY x→X e y→Y (normal +Z); en XZ x→X e y→Z (normal −Y: una extrusión positiva avanza hacia −Y); en YZ x→Y e y→Z (normal +X). Un plano de construcción usa el marco de su plano base. SOBRE UNA CARA (plane = selector como '>Z' o id de find_faces como 'Cuerpo1/F6'; tiene que ser UNA cara plana): el boceto queda sobre la cara con la normal exterior como normal (extruir con join crece hacia afuera; con cut entra al material solo, como Fusion). Ejes: en caras horizontales x→+X; en las demás y→+Z (hacia arriba) y x = y × normal; el origen es la proyección del origen del mundo sobre el plano de la cara, no una esquina (plane_frame lo da y find_faces trae center_uv, el centro de cada cara en estos ejes). El boceto queda asociado a la cara, como en Fusion: si un parámetro la mueve o la gira, el boceto la sigue; si la cara desaparece, el paso da error. Con varios cuerpos, body dice en cuál se evalúa el selector de la cara.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `plane` (texto; opcional, por defecto `"XY"`): "XY", "XZ", "YZ", el id/nombre de un plano de construcción, o una cara plana: selector (">Z") o id ("Cuerpo1/F6").
  - `name` (texto; opcional, por defecto `null`): nombre del boceto; vacío = "Boceto1", "Boceto2"…
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo donde se evalúa el selector de cara de plane; vacío = el único cuerpo. No se usa con un plano ni con un id de cara.
- CLI: `omnicad call create_sketch --doc pieza.omnicad`

### `draw_line`

Dibuja una línea en el boceto (un paso de deshacer). Coordenadas en mm sobre el plano del boceto. Devuelve los ids creados (línea y puntos) y la cantidad de perfiles.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `start_x` (número; obligatorio): x del punto inicial (mm).
  - `start_y` (número; obligatorio): y del punto inicial (mm).
  - `end_x` (número; obligatorio): x del punto final (mm).
  - `end_y` (número; obligatorio): y del punto final (mm).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para una línea de construcción (no forma perfiles).
- CLI: `omnicad call draw_line --doc pieza.omnicad start_x=… start_y=… end_x=… end_y=…`

### `draw_rectangle`

Dibuja un rectángulo (4 líneas con restricciones horizontal y vertical). Tres formas de darlo: dos esquinas opuestas (x1, y1, x2, y2); centro y tamaño (center_x, center_y, width, height); o esquina mínima y tamaño (origin_x, origin_y, width, height). width es el tamaño en x del boceto y height en y.

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
- CLI: `omnicad call draw_rectangle --doc pieza.omnicad`

### `draw_circle`

Dibuja un círculo por centro y radio (un paso de deshacer). Un círculo cerrado forma un perfil; dentro de un rectángulo da dos perfiles (el anillo y el disco).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `radius` (número; obligatorio): radio en mm (positivo).
  - `center_x` (número; opcional, por defecto `0.0`): x del centro (mm).
  - `center_y` (número; opcional, por defecto `0.0`): y del centro (mm).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para un círculo de construcción (no forma perfiles).
- CLI: `omnicad call draw_circle --doc pieza.omnicad radius=…`

### `draw_arc`

Dibuja un arco. Dos formas: centro + punto inicial + ángulo de barrido (center_x, center_y, start_x, start_y, sweep_angle; positivo = antihorario) o tres puntos (start_x, start_y, mid_x, mid_y, end_x, end_y). Un arco solo forma un perfil si se cierra con otras curvas.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `start_x` (número; obligatorio): x del punto inicial (mm).
  - `start_y` (número; obligatorio): y del punto inicial (mm).
  - `center_x` (número; opcional, por defecto `null`): x del centro (forma centro + barrido).
  - `center_y` (número; opcional, por defecto `null`): y del centro.
  - `sweep_angle` (número; opcional, por defecto `null`): ángulo de barrido en grados, entre -360 y 360 sin incluirlos; positivo = antihorario.
  - `mid_x` (número; opcional, por defecto `null`): x de un punto intermedio del arco (forma de tres puntos).
  - `mid_y` (número; opcional, por defecto `null`): y del punto intermedio.
  - `end_x` (número; opcional, por defecto `null`): x del punto final (forma de tres puntos).
  - `end_y` (número; opcional, por defecto `null`): y del punto final.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para un arco de construcción (no forma perfiles).
- CLI: `omnicad call draw_arc --doc pieza.omnicad start_x=… start_y=…`

### `create_polygon`

Dibuja un polígono regular de n lados (líneas iguales sobre un círculo guía de construcción, como la interfaz). Inscrito: los vértices están sobre el círculo de radio `radius`; circunscrito: los lados son tangentes a ese círculo (radius = medio entrecaras). Sin más, le quedan 4 grados de libertad (centro, tamaño y giro); con fully_constrained=true queda TOTALMENTE acotado: cota de radio del círculo guía (guarda la expresión de radius, así sigue a un parámetro), giro fijado (restricción horizontal/vertical o cota de ángulo) y centro acotado desde un punto fijo en el origen del boceto (dof 0).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sides` (entero; obligatorio): cantidad de lados (3 a 64).
  - `radius` (número o expresión; obligatorio): radio del círculo guía en mm (circunradio si es inscrito, apotema si es circunscrito); número o expresión con parámetros ("entrecaras / 2").
  - `center_x` (número; opcional, por defecto `0.0`): x del centro (mm).
  - `center_y` (número; opcional, por defecto `0.0`): y del centro (mm).
  - `rotation` (número; opcional, por defecto `0.0`): ángulo en grados del primer vértice respecto del eje x del boceto.
  - `kind` ("inscribed" | "circumscribed"; opcional, por defecto `"inscribed"`): "inscribed" (vértices sobre el círculo) o "circumscribed" (lados tangentes al círculo).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para un polígono de construcción (no forma perfiles).
  - `fully_constrained` (true/false; opcional, por defecto `false`): true para dejarlo totalmente acotado (radio, giro y posición del centro): dof 0.
- CLI: `omnicad call create_polygon --doc pieza.omnicad sides=… radius=…`

### `draw_spline`

Dibuja una spline: de ajuste (pasa por los puntos) o de puntos de control (grado 3 o 5, necesita al menos grado+1 puntos).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `points` (lista de lista de número; obligatorio): lista de puntos [x, y] en mm sobre el plano del boceto.
  - `spline_type` ("fit_points" | "control_points"; opcional, por defecto `"fit_points"`): "fit_points" (pasa por los puntos) o "control_points" (los puntos son los polos).
  - `degree` (entero; opcional, por defecto `3`): grado de la spline de puntos de control (3 o 5); se ignora en la de ajuste.
  - `closed` (true/false; opcional, por defecto `false`): true para cerrar la spline de ajuste (forma un perfil).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para una spline de construcción (no forma perfiles).
- CLI: `omnicad call draw_spline --doc pieza.omnicad points=…`

### `add_constraint`

Agrega una restricción geométrica entre entidades del boceto (ids de get_sketch: curvas y puntos). Si choca con las que ya hay, falla y el boceto queda como estaba. Entidades por tipo: horizontal y vertical: una línea o dos puntos; parallel, perpendicular, collinear y equal: dos líneas (equal también dos círculos/arcos); coincident: un punto y otro punto o una curva; midpoint: un punto y una línea o arco; tangent y concentric: dos curvas; fix: una o más entidades; symmetry: dos entidades y la línea eje.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): id o nombre del boceto.
  - `type` ("coincident" | "horizontal" | "vertical" | "parallel" | "perpendicular" | "equal" | "tangent" | "concentric" | "midpoint" | "fix" | "collinear" | "symmetry" | "curvature"; obligatorio): tipo de restricción.
  - `entities` (lista de entero; obligatorio): ids de las entidades (curvas o puntos), en el orden que pide el tipo.
- CLI: `omnicad call add_constraint --doc pieza.omnicad sketch=… type=… entities=…`

### `add_dimension`

Agrega una cota (dimensión) que maneja la geometría. El valor es un número (mm o grados) o una expresión con parámetros ('ancho / 2'); si se omite, usa la medida actual. Las cotas de largo, radio, diámetro y desfase tienen que ser mayores que cero y de hasta 1.000.000 mm (1 km). Entidades por tipo: distance: dos puntos, una línea, un punto y una línea, o dos líneas; horizontal y vertical: dos puntos o una línea; radius y diameter: un círculo o arco; angle: dos líneas; offset: dos líneas o dos círculos/arcos.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): id o nombre del boceto.
  - `type` ("distance" | "horizontal" | "vertical" | "radius" | "diameter" | "angle" | "offset"; obligatorio): tipo de cota.
  - `entities` (lista de entero; obligatorio): ids de las entidades acotadas (curvas o puntos), en el orden que pide el tipo.
  - `value` (número o expresión; opcional, por defecto `null`): valor: número (mm; grados en angle) o expresión con parámetros, p. ej. "radio_agujero * 2". Vacío = medida actual.
- CLI: `omnicad call add_dimension --doc pieza.omnicad sketch=… type=… entities=…`

### `get_sketch`

Informe de un boceto: plano y su marco 3D, entidades con ids estables (coordenadas ya resueltas por el solver), puntos, restricciones, cotas con su valor, perfiles (índice, área mm², centroide, caja [min/max en coordenadas del boceto] y curvas del borde) y estado (fully_constrained, under_constrained, over_constrained) con los grados de libertad.

- Modifica el documento: no.
- Parámetros:
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call get_sketch --doc pieza.omnicad`

### `sketch_from_spec`

Crea un boceto COMPLETO en una sola llamada (un paso de deshacer): geometría, restricciones y cotas. entities: lista de {type, ...}: line{start,end}, rectangle{corner1,corner2 | center,width,height | origin,width,height}, circle{center,radius}, arc{center,start,sweep | start,mid,end}, polygon{sides,radius,center,rotation,kind,fully_constrained}, ellipse{center,major_radius,minor_radius,angle}, slot{kind,points,width} (kind como en draw_slot), spline{points,spline_type,degree,closed}, point{at}; todas aceptan id (nombre propio para citarla) y construction. Las coordenadas son [x, y] en mm del plano. constraints: [{type, entities:[citas]}]; dimensions: [{type, entities:[citas], value}] (value puede ser una expresión con parámetros). Citas: 'id' (la curva), 'id.start', 'id.end', 'id.center', en un rectángulo 'id.bottom/right/top/left' (líneas) y 'id.c1..c4' (esquinas), en un polígono 'id.side1..', 'id.v1..' y 'id.circle', en una elipse 'id.major' y 'id.major_axis/minor_axis', en una ranura 'id.side1/side2/end1/end2/axis/center1/center2'; un entero cita un id de entidad ya existente. Sin id, la entidad se cita 'e0', 'e1'… según su posición en la lista. plane es un plano o una cara plana (selector '>Z' o id de find_faces), con los mismos ejes que create_sketch sobre esa cara (find_faces da center_uv); con varios cuerpos, body dice en cuál se evalúa el selector. Devuelve handles (cita → id real), perfiles, estado y plane_frame (origen y ejes del plano).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `plane` (texto; opcional, por defecto `"XY"`): "XY", "XZ", "YZ", el id/nombre de un plano de construcción, o una cara plana: selector (">Z") o id ("Cuerpo1/F6").
  - `entities` (lista de objeto o null; opcional, por defecto `null`): geometría del boceto (ver la descripción de la herramienta).
  - `constraints` (lista de objeto o null; opcional, por defecto `null`): restricciones, cada una {"type": ..., "entities": [citas]}.
  - `dimensions` (lista de objeto o null; opcional, por defecto `null`): cotas, cada una {"type": ..., "entities": [citas], "value": número o expresión}.
  - `name` (texto; opcional, por defecto `null`): nombre del boceto; vacío = "Boceto1", "Boceto2"…
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo donde se evalúa el selector de cara de plane; vacío = el único cuerpo. No se usa con un plano ni con un id de cara.
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

Desfase de boceto (Fusion: Desfase): copia paralela de la CADENA de líneas y arcos unida a entity (o de un círculo), con las esquinas resueltas, la restricción de desfase y su cota (paramétrico: si la cadena cambia, el desfase la sigue). Por defecto una cadena cerrada crece hacia afuera y una abierta va a la izquierda de su recorrido; distance negativa va al otro lado, y side_x/side_y eligen el lado con un punto. Para letras, splines o cualquier contorno (sin parámetros) está offset_profiles.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entity` (entero; obligatorio): id de una curva de la cadena (línea o arco) o de un círculo.
  - `distance` (número o expresión; obligatorio): separación en mm, número o expresión con parámetros; negativa = al lado contrario.
  - `side_x` (número; opcional, por defecto `null`): x de un punto del lado donde va el desfase; vacío = el lado por defecto.
  - `side_y` (número; opcional, por defecto `null`): y de ese punto.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call offset_sketch_curves --doc pieza.omnicad entity=… distance=…`

### `mirror_sketch`

Simetría de boceto (Fusion: Simetría): copia espejada de curvas y puntos respecto de una línea del boceto, con restricciones de simetría (si la geometría original cambia, la copia la sigue). Lo que está sobre el eje se comparte. Los textos no se espejan (para eso: transform_sketch o edit_text).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entities` (lista de entero; obligatorio): ids de las curvas o puntos a reflejar (get_sketch).
  - `axis` (entero; obligatorio): id de la línea de simetría (puede ser de construcción).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call mirror_sketch --doc pieza.omnicad entities=… axis=…`

### `sketch_rectangular_pattern`

Patrón rectangular de boceto (Fusion: Patrón rectangular en el boceto): copias de curvas y puntos en una o dos direcciones, atadas al original con la restricción de patrón (si el original cambia, las copias lo siguen). La dirección 1 sale del ángulo angle y la 2 es perpendicular (+90°). Con spacing=extent la distancia es la total (de la primera a la última copia); con spacing la de cada paso. Tope: 200 puntos copiados (copias × puntos de la selección; un rectángulo tiene 4), para que el boceto no se vuelva lento.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entities` (lista de entero; obligatorio): ids de las curvas o puntos a repetir (get_sketch).
  - `count1` (entero; obligatorio): cantidad en la dirección 1, contando el original.
  - `distance1` (número; obligatorio): distancia en la dirección 1 (mm; total o por paso según spacing; negativa = sentido contrario).
  - `count2` (entero; opcional, por defecto `1`): cantidad en la dirección 2 (1 = una sola fila).
  - `distance2` (número; opcional, por defecto `0.0`): distancia en la dirección 2 (mm).
  - `angle` (número; opcional, por defecto `0.0`): dirección 1 en grados respecto del eje x del boceto; la dirección 2 queda a +90°.
  - `spacing` ("extent" | "spacing"; opcional, por defecto `"extent"`): extent (distancia total) o spacing (distancia entre copias).
  - `symmetric` (true/false; opcional, por defecto `false`): true para repartir las copias a los dos lados del original.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call sketch_rectangular_pattern --doc pieza.omnicad entities=… count1=… distance1=…`

### `sketch_circular_pattern`

Patrón circular de boceto (Fusion: Patrón circular en el boceto): copias de curvas y puntos alrededor de un centro, atadas al original con la restricción de patrón. total_angle = 360 reparte la cantidad en la vuelta entera; otro ángulo pone la primera y la última copia en sus extremos. Tope: 200 puntos copiados (copias × puntos de la selección; un círculo tiene 1).

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
- CLI: `omnicad call sketch_circular_pattern --doc pieza.omnicad entities=… count=…`

### `project_to_sketch`

Proyecta aristas, caras o cuerpos del modelo sobre el plano del boceto (Fusion: Proyectar) o agrega donde cortan ese plano (mode=intersect; Fusion: Intersecar). La geometría queda proyectada: fija (violeta en la interfaz), sirve para restricciones, cotas y perfiles, y NO sigue al modelo si después cambia. edges y faces aceptan selectores (con body si hay varios cuerpos) o ids de find_edges / find_faces.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `edges` (lista de texto o texto o null; opcional, por defecto `null`): aristas a proyectar: selector ('|Z', '%CIRCLE and >Z') o ids ('Cuerpo1/E3'); vacío = ninguna.
  - `faces` (lista de texto o texto o null; opcional, por defecto `null`): caras a proyectar (su contorno): selector o ids ('Cuerpo1/F6'); vacío = ninguna.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de cuerpos enteros; vacío = ninguno.
  - `mode` ("project" | "intersect"; opcional, por defecto `"project"`): project (proyección ortogonal) o intersect (corte con el plano del boceto).
  - `body` (texto; opcional, por defecto `null`): cuerpo donde se evalúan los selectores de edges y faces; vacío = el único cuerpo.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call project_to_sketch --doc pieza.omnicad`

### `set_line_type`

Cambia el tipo de línea de curvas del boceto (Fusion: Construcción / Línea central de la paleta): normal (forma perfiles), construction (de construcción: guía, no forma perfiles) o centerline (eje: forma perfiles y sirve de eje de revolución).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entities` (lista de entero; obligatorio): ids de las curvas (get_sketch).
  - `line_type` ("normal" | "construction" | "centerline"; obligatorio): normal, construction o centerline (centerline solo en curvas que no son texto).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call set_line_type --doc pieza.omnicad entities=… line_type=…`

### `edit_dimension`

Cambia el valor de una cota que ya existe (Fusion: doble clic en la cota): número o expresión con parámetros. La geometría se mueve para cumplirla. Si choca con las otras restricciones y cotas, falla y el boceto queda como estaba. Para borrar una cota o una restricción: delete_sketch_entities con su id.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `dimension` (entero; obligatorio): id de la cota (get_sketch la lista en dimensions).
  - `value` (número o expresión; obligatorio): valor nuevo: número (mm; grados en una cota de ángulo) o expresión con parámetros ("ancho / 2").
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call edit_dimension --doc pieza.omnicad dimension=… value=…`

### `auto_constrain`

Restringe automáticamente el boceto (Fusion: Restringir automáticamente): agrega coincidencias, horizontales, verticales e igualdades que ya se cumplen y después cotas (largos, radios, ángulos y posiciones desde un punto fijo en el origen) con las medidas actuales, hasta dejarlo totalmente restringido si se puede. Cada agregado se prueba solo: nada entra en conflicto. Las cotas quedan como números (cambialas con edit_dimension).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call auto_constrain --doc pieza.omnicad`

## Grupo vectores

Texto y vectores: fuentes, texto de boceto, SVG, DXF e imágenes vectorizadas.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`list_fonts`](#list_fonts) | no | Lista las fuentes que puede usar el texto de boceto: todas las instaladas (sistema, usuario y carpetas sumadas con add_font_folder), TrueType, OpenType, colecciones y variables. |
| [`add_font_folder`](#add_font_folder) | no | Suma una carpeta de fuentes (.ttf, .otf, .ttc) a las que ve OmniCAD en esta sesión. |
| [`add_text`](#add_text) | sí | Escribe un texto en el boceto (un paso de deshacer). |
| [`edit_text`](#edit_text) | sí | Cambia un texto existente del boceto (un paso de deshacer): lo que no se pasa queda como estaba. |
| [`explode_text`](#explode_text) | sí | Desglosa un texto del boceto (Fusion: Explode Text): el texto pasa a ser líneas y splines fijas, que se pueden editar curva por curva. |
| [`inspect_svg`](#inspect_svg) | no | Mira un archivo SVG antes de insertarlo: tamaño en mm, y qué capas (grupos) y colores trae, con la cantidad de trazos de cada uno. |
| [`insert_svg`](#insert_svg) | sí | Inserta un dibujo SVG en un boceto (Fusion: Insertar > Insertar SVG) y lo deja como curvas editables (las curvas Bézier pasan a splines de control; círculos y arcos quedan exactos). |
| [`insert_dxf`](#insert_dxf) | sí | Inserta la geometría 2D de un archivo DXF en un boceto (Fusion: Insertar > Insertar DXF): líneas, arcos, círculos, polilíneas, splines y textos. |
| [`trace_image`](#trace_image) | sí | Vectoriza una imagen (PNG, JPG, BMP, GIF, WEBP) y la inserta en un boceto como contornos cerrados (logos, siluetas, dibujos en blanco y negro). |
| [`export_sketch`](#export_sketch) | no | Guarda un boceto como archivo 2D para corte láser, vinilo o CNC (Fusion: Guardar como DXF); el formato sale de la extensión: .dxf o .svg. |
| [`combine_profiles`](#combine_profiles) | sí | Une, resta o interseca perfiles (regiones cerradas) del boceto y deja el contorno resultante como curvas nuevas, sin las líneas internas: juntar letras que se pisan, restar un marco, quedarse con lo común. |
| [`offset_profiles`](#offset_profiles) | sí | Desfase (offset) del contorno de perfiles del boceto, con agujeros incluidos: distance > 0 agranda, < 0 achica. |
| [`transform_sketch`](#transform_sketch) | sí | Mueve, gira, escala y/o espeja curvas de un boceto (un paso de deshacer): lo importado de un SVG, un texto, una selección. |
| [`clean_sketch`](#clean_sketch) | sí | Limpia geometría importada (SVG, DXF, imagen vectorizada): borra curvas repetidas, une extremos sueltos a menos de tolerance mm (cierra huecos para que los contornos formen perfiles) y junta líneas seguidas alineadas en una sola. |
| [`move_sketch_point`](#move_sketch_point) | sí | Mueve un punto del boceto (edición de nodos): extremos de líneas y arcos, puntos de control de splines (las curvas Bézier de un SVG), centros. |
| [`delete_sketch_entities`](#delete_sketch_entities) | sí | Borra curvas, puntos, restricciones o cotas del boceto (un paso de deshacer); lo que dependa de ellos se borra también (un punto se lleva sus curvas). |

### `list_fonts`

Lista las fuentes que puede usar el texto de boceto: todas las instaladas (sistema, usuario y carpetas sumadas con add_font_folder), TrueType, OpenType, colecciones y variables. Usá el nombre de la familia en add_text(font=...); font también acepta la ruta a un .ttf/.otf.

- Modifica el documento: no.
- Parámetros:
  - `query` (texto; opcional, por defecto `null`): texto a buscar dentro del nombre de la familia (sin distinguir mayúsculas); vacío = todas.
  - `limit` (entero; opcional, por defecto `100`): cuántas familias devolver como máximo (1 a 1000).
  - `include_styles` (true/false; opcional, por defecto `false`): true para incluir los estilos de cada familia (peso, cursiva y archivo).
- CLI: `omnicad call list_fonts --doc pieza.omnicad`

### `add_font_folder`

Suma una carpeta de fuentes (.ttf, .otf, .ttc) a las que ve OmniCAD en esta sesión. Para que quede fija, definí la variable de entorno OMNICAD_FUENTES con la carpeta.

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; obligatorio): carpeta con las fuentes (se busca también en sus subcarpetas).
- CLI: `omnicad call add_font_folder --doc pieza.omnicad path=…`

### `add_text`

Escribe un texto en el boceto (un paso de deshacer). Sus letras forman perfiles que se pueden extruir o cortar. (x, y) es el ancla: por defecto la esquina izquierda de la línea base. Varias líneas con '\n'; con box_width > 0 las líneas se parten en palabras. Fuente: cualquier familia instalada (list_fonts) o la ruta a un .ttf/.otf. TEXTO EN CURVA: con path_entity (una línea, arco, círculo, elipse o spline del boceto) las letras siguen esa curva y (x, y, angle) no se usan; para un círculo, texto arriba por fuera = path_side right + path_position 0.25, abajo por dentro = left + 0.75.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `text` (texto; obligatorio): el texto; '\n' separa líneas. Con {parámetro} o {expresión:formato} (p. ej. 'Ancho {ancho:.1f} mm') muestra el valor del parámetro y se actualiza solo.
  - `x` (número; opcional, por defecto `0.0`): x del ancla (mm).
  - `y` (número; opcional, por defecto `0.0`): y del ancla (mm).
  - `height` (número; opcional, por defecto `5.0`): tamaño de la fuente en mm (positivo).
  - `angle` (número; opcional, por defecto `0.0`): giro del texto en grados alrededor del ancla (antihorario).
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
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
- CLI: `omnicad call add_text --doc pieza.omnicad text=…`

### `edit_text`

Cambia un texto existente del boceto (un paso de deshacer): lo que no se pasa queda como estaba. Los perfiles de las letras se recalculan; lo que dependa de ellos (extrusiones) sigue al texto.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `entity` (entero; obligatorio): id de la curva de texto (get_sketch).
  - `text` (texto; opcional, por defecto `null`): texto nuevo ('\n' separa líneas; {parámetro} muestra su valor).
  - `x` (número; opcional, por defecto `null`): x nueva del ancla (mm).
  - `y` (número; opcional, por defecto `null`): y nueva del ancla (mm).
  - `height` (número; opcional, por defecto `null`): tamaño nuevo de la fuente en mm.
  - `angle` (número; opcional, por defecto `null`): giro nuevo en grados.
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
  - `scale` (número; opcional, por defecto `1.0`): factor de escala (positivo; 1 = igual).
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

Mueve un punto del boceto (edición de nodos): extremos de líneas y arcos, puntos de control de splines (las curvas Bézier de un SVG), centros. Como arrastrar en la interfaz: el punto va a (x, y) y el resto se acomoda para seguir cumpliendo restricciones y cotas; si ellas no lo dejan llegar (por ejemplo, una cota fija su distancia), queda lo más cerca posible: reached dice si llegó y point dónde quedó.

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
| [`extrude`](#extrude) | sí | Extruye perfiles de un boceto. profile: índice, lista de índices, 'all' o 'largest' (el perfil de mayor área, p. ej. la placa con sus agujeros). distance acepta un número (mm) o una expresión con parámetros. |
| [`revolve`](#revolve) | sí | Revoluciona perfiles de un boceto alrededor de un eje. axis: 'sketch_x' o 'sketch_y' (ejes del plano del boceto que pasan por su origen), 'x', 'y', 'z' (ejes del origen del diseño) o el id de una línea del boceto (get_sketch; puede ser de construcción). |
| [`sweep`](#sweep) | sí | Barre un perfil a lo largo de una ruta de otro boceto (o del mismo). |
| [`loft`](#loft) | sí | Solevación: un sólido que pasa por los perfiles de varios bocetos, en el orden dado (mínimo dos). profiles elige un perfil por boceto (índice o 'largest'); vacío = el perfil 0 de cada uno. ruled usa tramos rectos entre secciones y closed une la última con la primera. |
| [`create_box`](#create_box) | sí | Crea una caja alineada con los ejes. length es el tamaño en X, width en Y y height en Z (mm). (x, y, z) es el centro de la cara de abajo: la caja queda centrada en X e Y y apoyada en z. |
| [`create_cylinder`](#create_cylinder) | sí | Crea un cilindro con el eje en Z (para otro eje, girarlo con move_body). (x, y, z) es el centro de la base; la altura crece hacia +Z. La medida va como radius o como diameter (uno solo). |
| [`create_sphere`](#create_sphere) | sí | Crea una esfera. (x, y, z) es su centro. |
| [`create_torus`](#create_torus) | sí | Crea un toroide con el eje en Z (para otro eje, girarlo con move_body). (x, y, z) es su centro. |
| [`boolean_operation`](#boolean_operation) | sí | Combina cuerpos: join (unir), cut (restar las herramientas al objetivo) o intersect (quedarse con lo común). |
| [`mirror`](#mirror) | sí | Refleja cuerpos respecto de un plano (origen o de construcción). |
| [`rectangular_pattern`](#rectangular_pattern) | sí | Patrón rectangular de cuerpos: copias en una o dos direcciones (ejes del origen), con la separación entre copias consecutivas. |
| [`circular_pattern`](#circular_pattern) | sí | Patrón circular de cuerpos alrededor de un eje del origen (x, y o z). |
| [`move_body`](#move_body) | sí | Mueve (o copia) cuerpos, como Mover › Movimiento libre de Fusion: primero gira rotate = [rx, ry, rz] grados alrededor del pivote (en ese orden) y después DESPLAZA translate = [dx, dy, dz] mm, que se SUMA a la posición actual (no es una posición absoluta: un cuerpo con el centro en z = 2 y translate [0, 0, 15] queda en z = 17). |
| [`fillet`](#fillet) | sí | Redondea aristas (empalme de radio constante). |
| [`chamfer`](#chamfer) | sí | Achaflana aristas (distancia igual en las dos caras). |
| [`shell`](#shell) | sí | Vacía un cuerpo dejando paredes de un espesor dado; las caras elegidas se quitan (quedan abiertas). |
| [`create_hole`](#create_hole) | sí | Hace agujeros redondos hacia adentro del material: simples, abocardados (counterbore) o avellanados (countersink), ciegos (depth), pasantes (through_all) o hasta una cara, plano o cuerpo (to). |
| [`create_thread`](#create_thread) | sí | Rosca sobre caras cilíndricas (ejes o agujeros: se detecta solo), como el comando Rosca de Fusion. |
| [`draft`](#draft) | sí | Desmoldeo: inclina caras un ángulo respecto de un plano neutro (la cara o el plano que no se mueve), para poder sacar la pieza del molde. |
| [`gear_info`](#gear_info) | no | Calcula las medidas de un engranaje cilíndrico de evolvente sin modelarlo (ISO 21771, perfil de referencia ISO 53): diámetros primitivo, base, exterior y de fondo, paso, espesor del diente, dientes mínimos sin socavado (criterio estricto: 18 con 20°; el límite teórico, 17,1, va en min_teeth_theoretical) y desplazamiento mínimo. |
| [`create_gear`](#create_gear) | sí | Crea un engranaje cilíndrico de evolvente (perfil de referencia ISO 53), recto o, con helix_angle, helicoidal, como un paso del timeline (tipo «engranaje»; medidas como expresiones con parámetros). |
| [`create_gear_pair`](#create_gear_pair) | sí | Crea dos engranajes de evolvente que engranan, en UN paso del timeline: el segundo a la distancia entre centros de trabajo (m·(z1+z2)/2 sin desplazamientos), en la dirección dada y girado medio diente para que los dientes entren en los huecos (con hélice, el segundo es de la mano contraria). |
| [`create_rack`](#create_rack) | sí | Crea una cremallera recta con el perfil de referencia ISO 53 (paso π·módulo, flancos rectos al ángulo de presión) como un paso del timeline. |
| [`create_sprocket`](#create_sprocket) | sí | Crea una rueda dentada para cadena de rodillos con la forma de diente de ISO 606 (hueco medio) como un paso del timeline. chain elige la cadena (05B…16B, 08A…16A = ANSI 40…80) o 'custom' con pitch y roller_diameter propios; sin width, el ancho del diente sale de la norma (0,93 o 0,95 × ancho interior de la cadena). |
| [`create_shaft`](#create_shaft) | sí | Asistente de ejes: crea un eje escalonado de revolución a partir de una tabla de tramos (diámetro, largo y, en cada extremo, chaflán a 45° o empalme) como un paso del timeline (tipo «eje_escalonado»). |

### `extrude`

Extruye perfiles de un boceto. profile: índice, lista de índices, 'all' o 'largest' (el perfil de mayor área, p. ej. la placa con sus agujeros). distance acepta un número (mm) o una expresión con parámetros. El sentido positivo es la normal del plano del boceto (en XZ es −Y); reverse lo invierte. Como en Fusion, un cut desde un boceto sobre una cara entra al material sin pedirlo (reverse vacío). direction: one_side, two_sides (distance y distance2) o symmetric (distance es el largo TOTAL, mitad a cada lado). taper_angle inclina las paredes (grados; positivo ensancha el sólido hacia el final, negativo lo estrecha). operation: new_body, join, cut o intersect.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): id o nombre del boceto.
  - `profile` (entero o lista de entero o texto; opcional, por defecto `0`): perfil(es): índice (get_sketch los lista), lista de índices, "all" o "largest".
  - `distance` (número o expresión; opcional, por defecto `"10 mm"`): distancia de extrusión: número en mm o expresión, p. ej. "espesor" o "2 * radio".
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `direction` ("one_side" | "two_sides" | "symmetric"; opcional, por defecto `"one_side"`): "one_side", "two_sides" o "symmetric".
  - `taper_angle` (número o expresión; opcional, por defecto `0`): conicidad en grados (número o expresión): positivo ensancha hacia el final, negativo estrecha; 0 = recto.
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
  - `distance2` (número o expresión; opcional, por defecto `null`): distancia del segundo lado con direction="two_sides"; vacío = igual a distance.
  - `reverse` (true/false; opcional, por defecto `null`): true para extruir hacia el lado contrario de la normal del plano. Vacío = automático: solo un cut desde un boceto sobre una cara se invierte (entra al material, como Fusion).
- CLI: `omnicad call extrude --doc pieza.omnicad sketch=…`

### `revolve`

Revoluciona perfiles de un boceto alrededor de un eje. axis: 'sketch_x' o 'sketch_y' (ejes del plano del boceto que pasan por su origen), 'x', 'y', 'z' (ejes del origen del diseño) o el id de una línea del boceto (get_sketch; puede ser de construcción). El perfil no debe cruzar el eje. angle acepta número (grados) o expresión. direction: one_side, two_sides (angle y angle2) o symmetric.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): id o nombre del boceto.
  - `profile` (entero o lista de entero o texto; obligatorio): perfil(es): índice, lista de índices, "all" o "largest".
  - `axis` (entero o texto; obligatorio): "sketch_x", "sketch_y", "x", "y", "z" o el id de una línea del boceto.
  - `angle` (número o expresión; opcional, por defecto `"360 deg"`): ángulo de giro: número en grados o expresión, p. ej. "270 deg" o "giro".
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `direction` ("one_side" | "two_sides" | "symmetric"; opcional, por defecto `"one_side"`): "one_side", "two_sides" o "symmetric" (el ángulo se reparte a los dos lados).
  - `angle2` (número o expresión; opcional, por defecto `null`): ángulo del segundo lado con direction="two_sides"; vacío = igual a angle.
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
  - `reverse` (true/false; opcional, por defecto `false`): true para girar en el sentido contrario.
- CLI: `omnicad call revolve --doc pieza.omnicad sketch=… profile=… axis=…`

### `sweep`

Barre un perfil a lo largo de una ruta de otro boceto (o del mismo). La ruta es una cadena continua de curvas: path_curves da sus ids (get_sketch) o, vacío, se usan todas las curvas no de construcción del boceto de la ruta. El perfil tiene que estar en el plano perpendicular al inicio de la ruta.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketch` (texto; obligatorio): id o nombre del boceto con el perfil.
  - `profile` (entero o lista de entero o texto; obligatorio): perfil(es): índice, lista de índices, "all" o "largest".
  - `path_sketch` (texto; obligatorio): id o nombre del boceto con la ruta.
  - `path_curves` (lista de entero o null; opcional, por defecto `null`): ids de las curvas de la ruta; vacío = todas las curvas no de construcción de path_sketch.
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `orientation` ("perpendicular" | "parallel"; opcional, por defecto `"perpendicular"`): "perpendicular" (el perfil sigue la tangente de la ruta) o "parallel" (mantiene su orientación).
  - `taper_angle` (número o expresión; opcional, por defecto `0`): ángulo de conicidad en grados.
  - `twist_angle` (número o expresión; opcional, por defecto `0`): torsión total en grados (máximo ±3600; ±1800 en rutas cerradas; la ruta no puede tener esquinas).
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
- CLI: `omnicad call sweep --doc pieza.omnicad sketch=… profile=… path_sketch=…`

### `loft`

Solevación: un sólido que pasa por los perfiles de varios bocetos, en el orden dado (mínimo dos). profiles elige un perfil por boceto (índice o 'largest'); vacío = el perfil 0 de cada uno. ruled usa tramos rectos entre secciones y closed une la última con la primera.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sketches` (lista de texto; obligatorio): ids o nombres de los bocetos, en el orden de las secciones.
  - `profiles` (lista de entero o texto o null; opcional, por defecto `null`): un perfil por boceto (índice o "largest"); vacío = el perfil 0 de cada boceto.
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `ruled` (true/false; opcional, por defecto `false`): true para tramos rectos entre secciones.
  - `closed` (true/false; opcional, por defecto `false`): true para cerrar el sólido uniendo la última sección con la primera.
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
- CLI: `omnicad call loft --doc pieza.omnicad sketches=…`

### `create_box`

Crea una caja alineada con los ejes. length es el tamaño en X, width en Y y height en Z (mm). (x, y, z) es el centro de la cara de abajo: la caja queda centrada en X e Y y apoyada en z. Medidas y posición aceptan expresiones con parámetros. En el timeline el paso guarda x, y, z con el mismo significado (caja_centrada) y edit_feature acepta length, width y height.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `length` (número o expresión; obligatorio): tamaño en X (mm, positivo).
  - `width` (número o expresión; obligatorio): tamaño en Y (mm, positivo).
  - `height` (número o expresión; obligatorio): tamaño en Z (mm, positivo).
  - `x` (número o expresión; opcional, por defecto `0`): x del centro de la base (mm).
  - `y` (número o expresión; opcional, por defecto `0`): y del centro de la base (mm).
  - `z` (número o expresión; opcional, por defecto `0`): z de la base (mm).
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo afectado por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
- CLI: `omnicad call create_box --doc pieza.omnicad length=… width=… height=…`

### `create_cylinder`

Crea un cilindro con el eje en Z (para otro eje, girarlo con move_body). (x, y, z) es el centro de la base; la altura crece hacia +Z. La medida va como radius o como diameter (uno solo).

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
- CLI: `omnicad call create_sphere --doc pieza.omnicad`

### `create_torus`

Crea un toroide con el eje en Z (para otro eje, girarlo con move_body). (x, y, z) es su centro. Medidas como radios (major_radius, minor_radius) o diámetros (major_diameter, minor_diameter), uno de cada par.

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

Refleja cuerpos respecto de un plano (origen o de construcción). Crea cuerpos nuevos, o con combine=true une cada reflejo a su cuerpo original.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): cuerpo(s) a reflejar (id o nombre).
  - `plane` (texto; opcional, por defecto `"YZ"`): plano de simetría: "XY", "XZ", "YZ" o el id/nombre de un plano de construcción.
  - `combine` (true/false; opcional, por defecto `false`): true para unir el reflejo al cuerpo original en vez de crear un cuerpo nuevo.
- CLI: `omnicad call mirror --doc pieza.omnicad bodies=…`

### `rectangular_pattern`

Patrón rectangular de cuerpos: copias en una o dos direcciones (ejes del origen), con la separación entre copias consecutivas. Las copias son cuerpos nuevos (o se unen al original con combine). Cantidades incluyen el original.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): cuerpo(s) a repetir (id o nombre).
  - `x_count` (entero; opcional, por defecto `1`): cantidad de instancias en la dirección 1, original incluido (1 = sin copias; x_count × y_count ≤ 10.000).
  - `x_spacing` (número o expresión; opcional, por defecto `"10 mm"`): separación entre instancias consecutivas en la dirección 1 (mm o expresión). Se guarda como d1 con distribucion="espaciado": edit_feature d1 sigue siendo la separación.
  - `y_count` (entero; opcional, por defecto `1`): cantidad de instancias en la dirección 2, original incluido (x_count × y_count ≤ 10.000).
  - `y_spacing` (número o expresión; opcional, por defecto `"10 mm"`): separación entre instancias consecutivas en la dirección 2 (se guarda como d2).
  - `axis1` ("x" | "y" | "z"; opcional, por defecto `"x"`): eje de la dirección 1 ("x", "y" o "z").
  - `axis2` ("x" | "y" | "z"; opcional, por defecto `"y"`): eje de la dirección 2.
  - `combine` (true/false; opcional, por defecto `false`): true para unir las copias al cuerpo original.
- CLI: `omnicad call rectangular_pattern --doc pieza.omnicad bodies=…`

### `circular_pattern`

Patrón circular de cuerpos alrededor de un eje del origen (x, y o z). Con 360° las copias se reparten en toda la vuelta; con menos, entre el original y el ángulo total. count incluye el original.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): cuerpo(s) a repetir (id o nombre).
  - `count` (entero; obligatorio): cantidad de instancias, original incluido (2 a 10.000).
  - `axis` ("x" | "y" | "z"; opcional, por defecto `"z"`): eje de giro del origen: "x", "y" o "z".
  - `total_angle` (número o expresión; opcional, por defecto `360`): ángulo total en grados (número o expresión); 360 = vuelta completa. Se guarda como angulo con distribucion="extension".
  - `combine` (true/false; opcional, por defecto `false`): true para unir las copias al cuerpo original.
- CLI: `omnicad call circular_pattern --doc pieza.omnicad bodies=… count=…`

### `move_body`

Mueve (o copia) cuerpos, como Mover › Movimiento libre de Fusion: primero gira rotate = [rx, ry, rz] grados alrededor del pivote (en ese orden) y después DESPLAZA translate = [dx, dy, dz] mm, que se SUMA a la posición actual (no es una posición absoluta: un cuerpo con el centro en z = 2 y translate [0, 0, 15] queda en z = 17). Para llevarlo a una posición absoluta usá position = [x, y, z]: el centro de la caja de los cuerpos (después del giro) queda ahí. pivot='center' es el promedio de los centros de las cajas de los cuerpos y se RECALCULA con la geometría (si la pieza es asimétrica o se edita, el giro cambia de lugar); pivot='origin' gira alrededor del origen y da un giro estable. El resultado trae center.before y center.after.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `body` (texto o lista de texto; obligatorio): cuerpo(s) a mover (id o nombre).
  - `translate` (lista de número o expresión o null; opcional, por defecto `null`): DESPLAZAMIENTO [dx, dy, dz] en mm que se suma a la posición actual (números o expresiones); vacío = sin desplazamiento.
  - `rotate` (lista de número o expresión o null; opcional, por defecto `null`): giro [rx, ry, rz] en grados (números o expresiones); vacío = sin giro.
  - `pivot` ("center" | "origin"; opcional, por defecto `"center"`): centro del giro: "center" (centro de las cajas de los cuerpos, se recalcula) u "origin" (origen, estable).
  - `copy` (true/false; opcional, por defecto `false`): true para dejar el original y crear cuerpos nuevos con el movimiento.
  - `position` (lista de número o expresión o null; opcional, por defecto `null`): posición ABSOLUTA [x, y, z] en mm (números o expresiones) del centro de la caja de los cuerpos; no se combina con translate. El paso guarda el desplazamiento que hace falta ahora (position − centro, con los parámetros de position): si después cambia la forma de la pieza, el centro se corre con ella.
- CLI: `omnicad call move_body --doc pieza.omnicad body=…`

### `fillet`

Redondea aristas (empalme de radio constante). Se elige con un selector estilo CadQuery (p. ej. '|Z'; get_guide topic=selectores), con ids de find_edges (p. ej. 'Cuerpo1/E7', válidos hasta el próximo cambio del documento) o con una lista de ambos. Guarda referencias persistentes: sobrevive a un cambio de parámetros del modelo. El empalme sigue las aristas tangentes encadenadas. Si el radio no cabe, falla con OPERATION_FAILED y el documento queda igual. radius acepta número (mm) o expresión.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `edges` (texto o lista de texto; obligatorio): aristas a redondear: selector ("|Z", ">Z"), id de find_edges ("Cuerpo1/E7") o lista de ids y selectores.
  - `radius` (número o expresión; obligatorio): radio en mm (número o expresión con parámetros, p. ej. "espesor / 2").
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
- CLI: `omnicad call fillet --doc pieza.omnicad edges=… radius=…`

### `chamfer`

Achaflana aristas (distancia igual en las dos caras). Se elige con un selector estilo CadQuery (p. ej. '|Z'; get_guide topic=selectores), con ids de find_edges (p. ej. 'Cuerpo1/E7', válidos hasta el próximo cambio del documento) o con una lista de ambos. Guarda referencias persistentes: sobrevive a un cambio de parámetros del modelo. distance acepta número (mm) o expresión.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `edges` (texto o lista de texto; obligatorio): aristas a achaflanar: selector ("|Z", ">Z"), id de find_edges ("Cuerpo1/E7") o lista de ids y selectores.
  - `distance` (número o expresión; obligatorio): distancia del chaflán en mm sobre cada cara (número o expresión con parámetros).
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
- CLI: `omnicad call chamfer --doc pieza.omnicad edges=… distance=…`

### `shell`

Vacía un cuerpo dejando paredes de un espesor dado; las caras elegidas se quitan (quedan abiertas). Se elige con un selector estilo CadQuery (p. ej. '>Z'; get_guide topic=selectores), con ids de find_faces (p. ej. 'Cuerpo1/F6', válidos hasta el próximo cambio del documento) o con una lista de ambos. Guarda referencias persistentes: sobrevive a un cambio de parámetros del modelo. direction: inside (las paredes quedan hacia adentro: el cuerpo no crece), outside (hacia afuera) o both. Con faces=[] (lista vacía) el cuerpo queda hueco y cerrado. Si el espesor es igual o mayor que el radio de un empalme de las caras vaciadas, el kernel no puede (radio interior cero o negativo): OPERATION_FAILED. thickness acepta número (mm) o expresión.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `body` (texto; obligatorio): id o nombre del cuerpo a vaciar.
  - `faces` (texto o lista de texto; obligatorio): caras a quitar: selector (">Z" = la tapa), id de find_faces ("Cuerpo1/F6") o lista; [] = hueco cerrado.
  - `thickness` (número o expresión; obligatorio): espesor de pared en mm (número o expresión con parámetros).
  - `direction` ("inside" | "outside" | "both"; opcional, por defecto `"inside"`): "inside", "outside" o "both".
- CLI: `omnicad call shell --doc pieza.omnicad body=… faces=… thickness=…`

### `create_hole`

Hace agujeros redondos hacia adentro del material: simples, abocardados (counterbore) o avellanados (countersink), ciegos (depth), pasantes (through_all) o hasta una cara, plano o cuerpo (to). Tres formas de ubicarlos: (1) ASOCIATIVA, en puntos de un boceto: sketch + sketch_points (ids de get_sketch, p. ej. el centro de un círculo); el agujero sigue al punto si el boceto o sus cotas cambian, perpendicular al plano del boceto y hacia el lado del material (flip lo invierte); face es opcional (elige el cuerpo). (2) FIJA, sobre una cara plana: face con un selector (p. ej. '>Z') o un id de find_faces ('Cuerpo1/F6'; UNA cara plana) y points: [u, v] en mm en los ejes x,y de un boceto sobre esa cara (find_faces da el center_uv) o [x, y, z] del mundo (se proyecta sobre la cara); sin points, el centro de la cara. Esos puntos quedan fijos en el espacio aunque la cara se mueva. (3) REFERENCIAS: face + reference_edges y reference_distances ubican el agujero a esas distancias de dos aristas rectas (paramétrico). hole_tap: simple, clearance (agujero de paso ISO 273 para el tornillo thread='M8' con fit close/normal/loose), cosmetic (rosca solo informativa; diámetro = diameter o la broca de roscar), modeled (rosca real: thread, thread_class '6H', '2B', 'auto' o '' y print_clearance para imprimir en 3D) o taper (rosca cónica de tubería R/NPT: agujero cónico 1:16, rosca cosmética). El fondo es plano salvo drill_tip=true (cono de 118°). Medidas en número (mm) o expresión.

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
  - `drill_tip` (true/false; opcional, por defecto `false`): true deja el fondo en cono de 118° como una broca; false, fondo plano.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que se evalúan los selectores (y que se agujerea con sketch_points); vacío = el único cuerpo del documento.
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto de sketch_points; vacío = el último boceto.
  - `sketch_points` (lista de entero o null; opcional, por defecto `null`): ids de puntos del boceto (get_sketch los lista; el centro de un círculo también es un punto): un agujero asociativo en cada uno.
  - `flip` (true/false; opcional, por defecto `false`): con sketch_points, true invierte el sentido automático (hacia el material).
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

Desmoldeo: inclina caras un ángulo respecto de un plano neutro (la cara o el plano que no se mueve), para poder sacar la pieza del molde. Las caras que se alejan del plano neutro se angostan (ángulo positivo). Se elige con un selector estilo CadQuery (p. ej. '#Z'; get_guide topic=selectores), con ids de find_faces (p. ej. 'Cuerpo1/F2', válidos hasta el próximo cambio del documento) o con una lista de ambos. Guarda referencias persistentes: sobrevive a un cambio de parámetros del modelo. angle acepta número (grados) o expresión.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `faces` (texto o lista de texto; obligatorio): caras a inclinar: selector ("#Z" = las laterales de una caja), id de find_faces o lista.
  - `angle` (número o expresión; obligatorio): ángulo de desmoldeo en grados (número o expresión), p. ej. 3.
  - `neutral` (texto; opcional, por defecto `"XY"`): plano neutro: "XY", "XZ", "YZ" o una cara plana (selector o id, p. ej. "<Z"); define la dirección de extracción.
  - `reverse` (true/false; opcional, por defecto `false`): true invierte la dirección de extracción.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
- CLI: `omnicad call draft --doc pieza.omnicad faces=… angle=…`

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
  - `plane` (texto; opcional, por defecto `"XY"`): plano donde se apoya: "XY", "XZ", "YZ" o el id/nombre de un plano de construcción.
  - `center` (lista de número o expresión o null; opcional, por defecto `null`): [x, y] del centro sobre el plano, en mm; vacío = el origen del plano.
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
  - `plane` (texto; opcional, por defecto `"XY"`): plano donde se apoyan: "XY", "XZ", "YZ" o el id/nombre de un plano de construcción.
  - `center` (lista de número o expresión o null; opcional, por defecto `null`): [x, y] del centro del primero sobre el plano, en mm; vacío = el origen del plano.
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
  - `plane` (texto; opcional, por defecto `"XY"`): plano donde se apoya: "XY", "XZ", "YZ" o el id/nombre de un plano de construcción.
  - `center` (lista de número o expresión o null; opcional, por defecto `null`): [x, y] del inicio de la línea primitiva sobre el plano, en mm; vacío = el origen del plano.
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
  - `plane` (texto; opcional, por defecto `"XY"`): plano donde se apoya: "XY", "XZ", "YZ" o el id/nombre de un plano de construcción.
  - `center` (lista de número o expresión o null; opcional, por defecto `null`): [x, y] del centro sobre el plano, en mm; vacío = el origen del plano.
- CLI: `omnicad call create_sprocket --doc pieza.omnicad teeth=…`

### `create_shaft`

Asistente de ejes: crea un eje escalonado de revolución a partir de una tabla de tramos (diámetro, largo y, en cada extremo, chaflán a 45° o empalme) como un paso del timeline (tipo «eje_escalonado»). El eje sale de center por la normal del plano (en XY, hacia +Z), con los tramos en orden. Un chaflán o empalme va sobre la esquina de ese tramo: convexa en la punta o en un escalón que baja, cóncava en uno que sube. operation cut hace un agujero escalonado.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `segments` (lista de objeto; obligatorio): tramos en orden, cada uno {"diameter": mm, "length": mm, "start": "none"|"chamfer"|"fillet", "start_size": mm, "end": "none"|"chamfer"|"fillet", "end_size": mm}; diameter y length son obligatorios y todos aceptan expresiones.
  - `plane` (texto; opcional, por defecto `"XY"`): plano de donde sale el eje: "XY", "XZ", "YZ" o el id/nombre de un plano de construcción.
  - `center` (lista de número o expresión o null; opcional, por defecto `null`): [x, y] del comienzo del eje sobre el plano, en mm; vacío = el origen del plano.
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
- CLI: `omnicad call create_shaft --doc pieza.omnicad segments=…`

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
| [`rip`](#rip) | sí | Desgarro (CHAPA › Desgarro): mode=face quita la cara elegida (un pliegue —cara curva— o una parte plana); mode=points corta una ranura de ancho gap entre dos puntos del borde de la cara elegida (vértices [x, y, z] de la chapa o puntos de un boceto {"sketch", "point"}), del lado side. |
| [`join_by_bend`](#join_by_bend) | sí | Unir plegando (CHAPA › Unir plegando): une dos cuerpos de chapa del MISMO espesor con un pliegue entre dos aristas rectas paralelas (una de cada cuerpo, del borde de la cara de arriba o de abajo); quedan en un solo cuerpo. |
| [`set_sheet_metal_rule`](#set_sheet_metal_rule) | sí | Cambia la regla de un cuerpo de chapa (CHAPA › Reglas de chapa): otra regla de la biblioteca y/o valores que la anulan (espesor, radio, K, alivios, separación). |
| [`export_flat_pattern_dxf`](#export_flat_pattern_dxf) | no | Exporta el patrón plano de un cuerpo de chapa (o de su patrón plano) a DXF en mm para corte láser o plegadora (CHAPA › Exportar DXF del patrón plano): capas CONTORNO_EXTERIOR, CONTORNOS_INTERIORES, LINEAS_PLIEGUE (centros de pliegue) y EXTENSION_PLIEGUE (límites de cada pliegue). |

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
  - `profile` (entero o lista de entero o texto; opcional, por defecto `0`): perfil(es): índice (get_sketch los lista), lista de índices, "all" o "largest".
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

Desgarro (CHAPA › Desgarro): mode=face quita la cara elegida (un pliegue —cara curva— o una parte plana); mode=points corta una ranura de ancho gap entre dos puntos del borde de la cara elegida (vértices [x, y, z] de la chapa o puntos de un boceto {"sketch", "point"}), del lado side. Si la pieza queda partida, cada pedazo es un cuerpo de chapa (bodies_created).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `face` (texto; obligatorio): con mode="face", la cara a quitar; con mode="points", la cara cuyo borde tiene los dos puntos (selector o id).
  - `mode` ("face" | "points"; opcional, por defecto `"face"`): "face" o "points".
  - `points` (lista de lista de número o objeto o null; opcional, por defecto `null`): con mode="points", dos puntos del borde: [x, y, z] de un vértice o {"sketch": id, "point": id}.
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
| [`remesh`](#remesh) | sí | Rehace los triángulos de mallas con un tamaño parejo (MALLA › MODIFICAR › Remallar de Fusion). density > 1 da más triángulos (el largo de arista objetivo es el largo medio / √density). |
| [`smooth_mesh`](#smooth_mesh) | sí | Suaviza mallas sin encogerlas (MALLA › MODIFICAR › Suavizar de Fusion; filtro de Taubin). |
| [`shell_mesh`](#shell_mesh) | sí | Ahueca mallas cerradas con un espesor de pared (MALLA › MODIFICAR › Vaciado de Fusion): suma una cáscara interior desplazada thickness mm hacia adentro. |
| [`plane_cut_mesh`](#plane_cut_mesh) | sí | Corta mallas con un plano (MALLA › MODIFICAR › Corte de plano de Fusion). kind: trim (queda el lado hacia donde apunta la normal del plano; flip conserva el otro), split_body (dos cuerpos, uno por lado) o split_faces (una malla con los triángulos partidos sobre el plano). fill tapa el corte (un grupo de caras nuevo). |
| [`combine_meshes`](#combine_meshes) | sí | Combina cuerpos de malla (MALLA › MODIFICAR › Combinar de Fusion). operation: join, cut o intersect (booleanas reales: las mallas tienen que ser cerradas; repair_mesh o clean_mesh antes si no) o merge (junta los triángulos sin tocarlos). |
| [`separate_mesh`](#separate_mesh) | sí | Separa mallas en varios cuerpos (MALLA › MODIFICAR › Separar de Fusion): by shells, un cuerpo por parte conexa; by face_groups, uno por grupo de caras (generate_face_groups los crea). |
| [`reverse_mesh_normals`](#reverse_mesh_normals) | sí | Da vuelta la orientación de todos los triángulos de mallas (MALLA › MODIFICAR › Invertir normal de Fusion): el volumen cambia de signo. |
| [`scale_mesh`](#scale_mesh) | sí | Escala mallas desde el origen (MALLA › MODIFICAR › Escalar malla de Fusion): uniforme con factor_x solo, o distinto en cada eje. |
| [`convert_mesh`](#convert_mesh) | sí | Convierte mallas en cuerpos B-rep (MALLA › MODIFICAR › Convertir malla de Fusion): sólido si la malla es cerrada, superficie si no. method: faceted (una cara plana por triángulo) o prismatic (une las caras coplanares vecinas del mismo grupo; no reconoce cilindros). |

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

Rehace los triángulos de mallas con un tamaño parejo (MALLA › MODIFICAR › Remallar de Fusion). density > 1 da más triángulos (el largo de arista objetivo es el largo medio / √density). Tiene un tope de 100.000 triángulos: si se pasaría, falla antes de calcular y dice cuánto bajar.

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
  - `plane` (texto; obligatorio): "XY", "XZ", "YZ" o el id o nombre de un plano de construcción.
  - `kind` ("trim" | "split_body" | "split_faces"; opcional, por defecto `"trim"`): "trim", "split_body" o "split_faces".
  - `fill` (true/false; opcional, por defecto `true`): true tapa el corte con triángulos.
  - `flip` (true/false; opcional, por defecto `false`): true invierte el lado que se conserva (en trim) o el orden de las partes (en split_body).
  - `name` (texto; opcional, por defecto `null`): nombre del paso en el timeline; vacío = automático.
- CLI: `omnicad call plane_cut_mesh --doc pieza.omnicad bodies=… plane=…`

### `combine_meshes`

Combina cuerpos de malla (MALLA › MODIFICAR › Combinar de Fusion). operation: join, cut o intersect (booleanas reales: las mallas tienen que ser cerradas; repair_mesh o clean_mesh antes si no) o merge (junta los triángulos sin tocarlos). El resultado queda en target; las herramientas se borran salvo keep_tools=true.

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

Une dos componentes (ENSAMBLAR › Unión): mueve el componente de origin1 hasta que su marco coincide con el de origin2 (caras planas enfrentadas; dos ejes —perno en agujero— en el mismo sentido) y define cómo se mueve después. Cada origen es una cara o arista (selector evaluado sobre body1 / body2, o id de find_faces / find_edges: 'Cuerpo1/F3', 'Cuerpo1/E5'; para aristas con selector, prefijo 'edges:'), un origen de unión (create_joint_origin), un plano, eje o punto de construcción (id o nombre) o XY, XZ, YZ. joint_type: rigid (sin movimiento), revolute (gira alrededor de rotation_axis), slider (desliza sobre slide_axis), cylindrical (gira y desliza sobre rotation_axis), pin_slot (gira sobre rotation_axis y desliza sobre slide_axis), planar (desliza en el plano normal a rotation_axis y gira alrededor de él) o ball (tres giros). angle gira el componente 1 alrededor del Z del marco, offset lo corre [dx, dy, dz] y flip lo da vuelta. Los valores (rotation, slide…) y los límites aceptan número (grados o mm) o expresión. Devuelve la unión y los componentes que se movieron con su traslación y caja envolvente.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `origin1` (texto; obligatorio): dónde se toma el componente que SE MUEVE: cara o arista (selector o id), del cuerpo body1.
  - `origin2` (texto; obligatorio): dónde va: cara o arista de otro componente (o de la raíz), origen de unión, plano, eje o punto de construcción.
  - `joint_type` ("rigid" | "revolute" | "slider" | "cylindrical" | "pin_slot" | "planar" | "ball"; opcional, por defecto `"rigid"`): "rigid", "revolute", "slider", "cylindrical", "pin_slot", "planar" o "ball".
  - `body1` (texto; opcional, por defecto `null`): cuerpo (o componente de un solo cuerpo) donde se evalúa el selector de origin1; con un id no hace falta.
  - `body2` (texto; opcional, por defecto `null`): cuerpo (o componente de un solo cuerpo) donde se evalúa el selector de origin2.
  - `snap1` ("center" | "start" | "end"; opcional, por defecto `"center"`): punto del origen 1 en una arista o cilindro: "center" (medio), "start" o "end".
  - `snap2` ("center" | "start" | "end"; opcional, por defecto `"center"`): punto del origen 2: "center", "start" o "end".
  - `angle` (número o expresión; opcional, por defecto `0`): giro del componente 1 alrededor del eje Z del marco de la unión, en grados.
  - `offset` (lista de número o expresión o null; opcional, por defecto `null`): desfase [dx, dy, dz] en mm en el marco de la unión (Z = normal o eje).
  - `flip` (true/false; opcional, por defecto `false`): true da vuelta el componente 1 (caras en el mismo sentido o ejes opuestos).
  - `rotation_axis` ("X" | "Y" | "Z"; opcional, por defecto `"Z"`): eje del marco para girar (revolute, cylindrical, pin_slot) o normal del plano (planar).
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
  - `origin` (texto; obligatorio): cara o arista del componente que se mueve (selector evaluado sobre body, o id); define el marco del movimiento.
  - `component2` (texto; opcional, por defecto `null`): componente al que queda ligado (id, nombre o uno de sus cuerpos); vacío = la raíz.
  - `joint_type` ("rigid" | "revolute" | "slider" | "cylindrical" | "pin_slot" | "planar" | "ball"; opcional, por defecto `"revolute"`): "rigid", "revolute", "slider", "cylindrical", "pin_slot", "planar" o "ball".
  - `body` (texto; opcional, por defecto `null`): cuerpo (o componente de un solo cuerpo) donde se evalúa el selector de origin.
  - `snap` ("center" | "start" | "end"; opcional, por defecto `"center"`): punto del origen en una arista o cilindro: "center", "start" o "end".
  - `rotation_axis` ("X" | "Y" | "Z"; opcional, por defecto `"Z"`): eje del marco para girar (o normal del plano en planar).
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
  - `geometry` (texto; obligatorio): cara o arista donde va el origen (selector evaluado sobre body, o id de find_faces / find_edges).
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
| [`set_appearance`](#set_appearance) | sí | Cambia cómo se ven cuerpos (MODIFICAR › Aspecto): un aspecto de la biblioteca (appearance, p. ej. |

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

Cambia cómo se ven cuerpos (MODIFICAR › Aspecto): un aspecto de la biblioteca (appearance, p. ej. 'Aluminio - Anodizado (rojo)'; list_materials los lista por categoría) y/o un color propio (color «#rrggbb» o [r, g, b]). Con los dos, el acabado del aspecto con ese color. Sin ninguno, quita el aspecto (vuelve al color del material). No cambia la masa.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (lista de texto; obligatorio): ids o nombres de los cuerpos.
  - `appearance` (texto; opcional, por defecto `null`): nombre de un aspecto de la biblioteca (sin distinguir mayúsculas); vacío = solo el color.
  - `color` (texto o lista de número o null; opcional, por defecto `null`): color propio «#rrggbb» o [r, g, b] (0..1 o 0..255); vacío = el del aspecto.
- CLI: `omnicad call set_appearance --doc pieza.omnicad bodies=…`

## Grupo inspeccion

Ver y medir el resultado.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`thread_info`](#thread_info) | no | Datos de roscas normalizadas (no cambia el documento). |
| [`fit_tolerance`](#fit_tolerance) | no | Ajuste ISO 286 entre un agujero y un eje (no cambia el documento): desviaciones y medidas límite de cada uno, juego máximo y mínimo (negativo = apriete) y tipo de ajuste (clearance, transition o interference). |
| [`get_viewport_image`](#get_viewport_image) | no | Renderiza el modelo y devuelve una imagen PNG (sombreado, sombras y suelo) desde una vista estándar o una dirección propia. |
| [`get_physical_properties`](#get_physical_properties) | no | Volumen (mm³), área (mm²), masa (g), centro de masa y caja envolvente de cada cuerpo y del total. |
| [`measure_distance`](#measure_distance) | no | Distancia mínima entre dos cosas, cada una un cuerpo, una cara, una arista o un punto. |
| [`check_interference`](#check_interference) | no | Busca pares de cuerpos sólidos que se superponen y devuelve cada par con el volumen común (mm³) y su caja envolvente. |
| [`find_faces`](#find_faces) | no | Lista las caras de un cuerpo (o de todos), opcionalmente filtradas por un selector. |
| [`find_edges`](#find_edges) | no | Lista las aristas de un cuerpo (o de todos), opcionalmente filtradas por un selector. |
| [`measure_angle`](#measure_angle) | no | Ángulo (grados) entre dos caras planas, dos aristas rectas, o una cara y una arista. |
| [`check_geometry`](#check_geometry) | no | Revisa la geometría de un cuerpo (o de todos), como Check Geometry de FreeCAD: si el kernel lo da por válido (y qué falla si no), si es estanco, aristas libres (abiertas) y no manifold, autointersecciones, caras degeneradas, aristas diminutas y tolerancias máximas; en mallas, bordes abiertos, no manifold, normales invertidas y triángulos degenerados. |
| [`check_printability`](#check_printability) | no | Revisión de impresión 3D de un cuerpo (o de todos), como la caja de herramientas de impresión 3D de Blender: si es estanco, espesor mínimo de pared (rayos hacia adentro desde la superficie; zonas más finas que min_thickness), zonas en voladizo que necesitan soportes (más de overhang_angle desde la vertical, sin contar la cara apoyada en la cama: el plano Z más bajo del cuerpo) y aristas filosas (ángulo interior menor que sharp_angle). printable = estanco y sin paredes finas. |
| [`repair_body`](#repair_body) | sí | Repara un cuerpo y deja un paso «Reparar cuerpo» en el timeline (editable; un paso de deshacer): cose las aristas abiertas (si queda estanco pasa a sólido), baja las tolerancias mayores que tolerance, corrige con ShapeFix (orientación de caras, contornos) y refina (une caras coplanares). |

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

### `get_viewport_image`

Renderiza el modelo y devuelve una imagen PNG (sombreado, sombras y suelo) desde una vista estándar o una dirección propia. Es la forma de VER el resultado.

- Modifica el documento: no.
- Parámetros:
  - `view` ("iso" | "front" | "back" | "top" | "bottom" | "left" | "right"; opcional, por defecto `"iso"`): vista estándar: las caras del ViewCube de Fusion con Z arriba, nombradas por los ejes del MUNDO (no por el frente de la pieza). "front": cámara en -Y, se ve la cara -Y con +X a la derecha; "back": cámara en +Y; "right": cámara en +X, se ve la cara +X con +Y a la derecha; "left": cámara en -X; "top": cámara en +Z, X a la derecha e Y hacia arriba; "bottom": cámara en -Z; "iso": esquina frente-derecha-arriba. Si la pieza mira hacia otro eje, usá direction.
  - `width` (entero; opcional, por defecto `640`): ancho de la imagen en píxeles (16 a 2048).
  - `height` (entero; opcional, por defecto `480`): alto de la imagen en píxeles (16 a 2048).
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos a dibujar; vacío = todos.
  - `fit` (true/false; opcional, por defecto `true`): true encuadra los cuerpos dibujados; false encuadra TODA la escena aunque se dibuje solo una parte (sirve para comparar imágenes con el mismo encuadre).
  - `direction` (lista de número o null; opcional, por defecto `null`): [x, y, z] vector desde el modelo HACIA la cámara (Z es arriba); si se pasa, reemplaza a view.
- CLI: `omnicad call get_viewport_image --doc pieza.omnicad`

### `get_physical_properties`

Volumen (mm³), área (mm²), masa (g), centro de masa y caja envolvente de cada cuerpo y del total. La masa necesita una densidad: la que se pasa, o la del material físico asignado al cuerpo.

- Modifica el documento: no.
- Parámetros:
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos; vacío = todos.
  - `density` (número; opcional, por defecto `null`): densidad en g/cm³ para todos los cuerpos con volumen; vacío = la de su material físico.
- CLI: `omnicad call get_physical_properties --doc pieza.omnicad`

### `measure_distance`

Distancia mínima entre dos cosas, cada una un cuerpo, una cara, una arista o un punto. Caras y aristas se dan por id (find_faces / find_edges) o por selector (>Z elige sobre las caras; edges:|Z sobre las aristas; con varios cuerpos, body dice en cuál se evalúan los selectores). Devuelve la distancia (mm), los dos puntos más cercanos y el desfase XYZ de a hacia b.

- Modifica el documento: no.
- Parámetros:
  - `a` (texto o lista de número; obligatorio): cuerpo (id o nombre), cara o arista (id "Cuerpo1/F3" o selector ">Z", "edges:|Z") o punto [x, y, z] en mm.
  - `b` (texto o lista de número; obligatorio): cuerpo (id o nombre), cara o arista (id "Cuerpo1/F3" o selector ">Z", "edges:|Z") o punto [x, y, z] en mm.
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo donde se evalúan los selectores de a y b; vacío = el único cuerpo. Los ids y los nombres de cuerpo no lo necesitan.
- CLI: `omnicad call measure_distance --doc pieza.omnicad a=… b=…`

### `check_interference`

Busca pares de cuerpos sólidos que se superponen y devuelve cada par con el volumen común (mm³) y su caja envolvente. Los que solo se tocan por una cara no cuentan.

- Modifica el documento: no.
- Parámetros:
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos a comparar entre sí; vacío = todos los sólidos.
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

### `check_geometry`

Revisa la geometría de un cuerpo (o de todos), como Check Geometry de FreeCAD: si el kernel lo da por válido (y qué falla si no), si es estanco, aristas libres (abiertas) y no manifold, autointersecciones, caras degeneradas, aristas diminutas y tolerancias máximas; en mallas, bordes abiertos, no manifold, normales invertidas y triángulos degenerados. Cada problema trae kind, severity (error o warning), un mensaje y su posición [x, y, z]; max_tolerance es la mayor tolerancia del kernel por tipo. No cambia el documento: para arreglar, repair_body.

- Modifica el documento: no.
- Parámetros:
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo; vacío = todos los cuerpos del modelo.
  - `self_intersection` (true/false; opcional, por defecto `true`): true busca caras que se cortan entre sí (análisis booleano, lo más lento en piezas grandes).
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

Ejecuta código Python con api, sesion, doc y llamar(nombre, args) ya definidos. Devuelve lo impreso (stdout) y la variable `result` si el código la define. Todo es un paso de deshacer; si el código lanza una excepción, el documento queda intacto. Corre como mucho `timeout` segundos (60 por defecto): al vencer se corta con CODE_TIMEOUT y el documento vuelve a como estaba.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `code` (texto; obligatorio): código Python. Definidos: api (el paquete omnicad.api), sesion, doc (el documento activo) y llamar (atajo de api.llamar(sesion, nombre, args)). Asigná `result = ...` para devolver un valor.
  - `timeout` (número; opcional, por defecto `60.0`): segundos como máximo (60 por defecto); al vencer se corta el código, el documento vuelve a como estaba y responde CODE_TIMEOUT. null = sin límite (en vivo no se acepta; el máximo es 100 s). Solo se vigila tu código: una llamada larga a una herramienta termina antes del corte.
- CLI: `omnicad call execute_code --doc pieza.omnicad code=…`

### `get_guide`

Guía corta para agentes (ciclo de trabajo, unidades, cómo leer errores). Sin tema devuelve el índice.

- Modifica el documento: no.
- Parámetros:
  - `topic` (texto; opcional, por defecto `null`): tema de la guía (el índice los lista), p. ej. "flujo"; vacío = el índice.
- CLI: `omnicad call get_guide --doc pieza.omnicad`

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

## Grupo dev

Desarrollo del programa (en el MCP, solo con --dev; en la CLI, `omnicad dev`).

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`run_checks`](#run_checks) | no | Corre la verificación del proyecto (ruff, pytest y, si se pide, la prueba de humo de la interfaz) y devuelve un resumen por paso. |
| [`app_screenshot`](#app_screenshot) | no | Abre la ventana REAL de OmniCAD en otro proceso, espera a que dibuje, captura la ventana entera y la cierra. |
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

### `run_bench`

Mide el rendimiento de OmniCAD con la ventana real: arranque, memoria, recálculo de un modelo grande (placa con N×N agujeros) y cuadros por segundo al girar la vista. Repite la medición y devuelve la mediana de cada número. Sirve para comparar antes y después de optimizar.

- Modifica el documento: no.
- Parámetros:
  - `repetitions` (entero; opcional, por defecto `3`): cuántas veces medir (1 a 10); el resultado es la mediana de cada número.
  - `side` (entero; opcional, por defecto `8`): agujeros por lado del modelo grande (1 a 20; 8 = 64 agujeros y 73 pasos).
  - `frames` (entero; opcional, por defecto `120`): cuadros de la órbita para medir los cuadros por segundo (10 a 1000).
  - `preset` ("rendimiento" | "equilibrado" | "calidad" | "personalizar" o null; opcional, por defecto `null`): valor predefinido de gráficos con el que medir; vacío = el de fábrica (personalizar).
- CLI: `omnicad call run_bench --doc pieza.omnicad`
