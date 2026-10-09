<!-- ARCHIVO GENERADO: no editar a mano. Regenerar con: omnicad tools --markdown --output docs/agentes/herramientas.md -->

# Herramientas de OmniCAD

> Archivo generado: no editar a mano. Regenerar con `omnicad tools --markdown --output docs/agentes/herramientas.md` (desde la raíz del repo).
> Sale del catálogo de `omnicad.api`, la misma fuente del servidor MCP y de la CLI. Un test avisa si queda viejo.

63 herramientas en 7 grupos. Unidades: mm y grados. Nombres, parámetros y claves del resultado en inglés; textos en español.
Cada llamada devuelve `{"ok": true, "result": ..., "avisos": [...]}` o `{"ok": false, "error_kind": ..., "mensaje": ..., "pistas": [...]}`.

El servidor MCP en modo en vivo o auto suma `get_mode`, que no está en el catálogo (ver `puente.md`).

| Grupo | Herramientas | Para qué |
|---|---|---|
| [documento](#grupo-documento) | 12 | Archivo, escena, timeline y deshacer. |
| [parametros](#grupo-parametros) | 4 | Medidas con nombre que gobiernan el modelo. |
| [boceto](#grupo-boceto) | 12 | Bocetos 2D: geometría, restricciones y cotas. |
| [solido](#grupo-solido) | 18 | Sólidos: extruir, revolucionar, primitivas, empalmes, agujeros y patrones. |
| [inspeccion](#grupo-inspeccion) | 7 | Ver y medir el resultado. |
| [avanzado](#grupo-avanzado) | 7 | Cualquier operación, receta, código y guía. |
| [dev](#grupo-dev) | 3 | Desarrollo del programa (en el MCP, solo con --dev; en la CLI, `omnicad dev`). |

## Grupo documento

Archivo, escena, timeline y deshacer.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`get_scene_info`](#get_scene_info) | no | Resumen del documento: nombre, archivo, cambios sin guardar, unidades, cuerpos (id, nombre, tipo, volumen mm³, área mm², caja envolvente), bocetos (plano y perfiles), cantidad de pasos del timeline y parámetros. |
| [`new_document`](#new_document) | sí | Empieza un documento vacío (descarta el actual de la sesión sin guardarlo). |
| [`open_document`](#open_document) | sí | Abre un proyecto .omnicad (o .fclone) y lo deja como documento activo. |
| [`save_document`](#save_document) | no | Guarda el documento como proyecto .omnicad. |
| [`export`](#export) | no | Exporta cuerpos a un archivo; el formato sale de la extensión: .stl, .obj, .3mf, .ply (mallas) o .step/.stp, .iges/.igs, .brep (sólidos exactos). |
| [`undo`](#undo) | sí | Deshace el último cambio del documento (cada herramienta que modifica es un paso). |
| [`redo`](#redo) | sí | Rehace el último cambio deshecho. |
| [`get_timeline`](#get_timeline) | no | Lista los pasos del timeline en orden: índice, id, tipo, nombre, si está suprimido, estado (ok, warning, error, suppressed, rolled_back), mensaje y parámetros. |
| [`edit_feature`](#edit_feature) | sí | Cambia parámetros de un paso del timeline (conserva su id) y recalcula. |
| [`suppress_feature`](#suppress_feature) | sí | Suprime o reactiva un paso del timeline (suprimido = no se calcula). |
| [`delete_feature`](#delete_feature) | sí | Borra un paso del timeline. |
| [`rename`](#rename) | sí | Renombra un paso del timeline o un cuerpo. |

### `get_scene_info`

Resumen del documento: nombre, archivo, cambios sin guardar, unidades, cuerpos (id, nombre, tipo, volumen mm³, área mm², caja envolvente), bocetos (plano y perfiles), cantidad de pasos del timeline y parámetros.

- Modifica el documento: no.
- Parámetros: ninguno.
- CLI: `omnicad call get_scene_info --doc pieza.omnicad`

### `new_document`

Empieza un documento vacío (descarta el actual de la sesión sin guardarlo).

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `name` (texto; opcional, por defecto `"Sin título"`): nombre del documento nuevo.
- CLI: `omnicad call new_document --doc pieza.omnicad`

### `open_document`

Abre un proyecto .omnicad (o .fclone) y lo deja como documento activo.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `path` (texto; obligatorio): ruta del archivo de proyecto.
- CLI: `omnicad call open_document --doc pieza.omnicad path=…`

### `save_document`

Guarda el documento como proyecto .omnicad. Sin path, guarda en su archivo actual. No reemplaza otro archivo existente salvo con overwrite=true.

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; opcional, por defecto `null`): ruta del archivo; si no termina en .omnicad se le agrega. Vacío = el archivo actual del documento.
  - `overwrite` (true/false; opcional, por defecto `false`): true para reemplazar un archivo existente que no es el actual.
- CLI: `omnicad call save_document --doc pieza.omnicad`

### `export`

Exporta cuerpos a un archivo; el formato sale de la extensión: .stl, .obj, .3mf, .ply (mallas) o .step/.stp, .iges/.igs, .brep (sólidos exactos).

- Modifica el documento: no.
- Parámetros:
  - `path` (texto; obligatorio): ruta del archivo a escribir.
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos; vacío = todos los cuerpos del final del timeline.
  - `overwrite` (true/false; opcional, por defecto `false`): true para reemplazar el archivo si ya existe.
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

Lista los pasos del timeline en orden: índice, id, tipo, nombre, si está suprimido, estado (ok, warning, error, suppressed, rolled_back), mensaje y parámetros.

- Modifica el documento: no.
- Parámetros:
  - `include_params` (true/false; opcional, por defecto `true`): false para omitir los parámetros de cada paso (respuesta más corta).
- CLI: `omnicad call get_timeline --doc pieza.omnicad`

### `edit_feature`

Cambia parámetros de un paso del timeline (conserva su id) y recalcula. Si el paso u otro posterior queda con error, el cambio se descarta.

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
| [`sketch_from_spec`](#sketch_from_spec) | sí | Crea un boceto COMPLETO en una sola llamada (un paso de deshacer): geometría, restricciones y cotas. entities: lista de {type, ...}: line{start,end}, rectangle{corner1,corner2 \| center,width,height \| origin,width,height}, circle{center,radius}, arc{center,start,sweep \| start,mid,end}, polygon{sides,radius,center,rotation,kind}, spline{points,spline_type,degree,closed}, point{at}; todas aceptan id (nombre propio para citarla) y construction. |

### `create_construction_plane`

Crea un plano de construcción desfasado de un plano de origen (XY, XZ, YZ) o de otro plano de construcción. Sirve para dibujar bocetos fuera del origen. Va en el grupo «boceto» porque su uso típico es create_sketch(plane=<este plano>). El desfase es sobre la normal del plano base.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `plane` (texto; opcional, por defecto `"XY"`): plano base: "XY", "XZ", "YZ" o el id/nombre de otro plano de construcción.
  - `offset` (número o expresión; opcional, por defecto `"10 mm"`): desfase en mm sobre la normal del plano base (número o expresión con parámetros, p. ej. "alto / 2").
  - `name` (texto; opcional, por defecto `null`): nombre del plano; vacío = "Plano1", "Plano2"…
- CLI: `omnicad call create_construction_plane --doc pieza.omnicad`

### `create_sketch`

Crea un boceto vacío sobre un plano o sobre una cara plana. Coordenadas del boceto (mm): en XY x→X e y→Y (normal +Z); en XZ x→X e y→Z (normal −Y: una extrusión positiva avanza hacia −Y); en YZ x→Y e y→Z (normal +X). Un plano de construcción usa el marco de su plano base. SOBRE UNA CARA (plane = selector como '>Z' o id de find_faces como 'Cuerpo1/F6'; tiene que ser UNA cara plana): el boceto queda sobre la cara con la normal exterior como normal (extruir con join crece hacia afuera; con cut entra al material solo, como Fusion). Ejes: en caras horizontales x→+X; en las demás y→+Z (hacia arriba) y x = y × normal; el origen es la proyección del origen del mundo sobre el plano de la cara, no una esquina (plane_frame lo da y find_faces trae center_uv, el centro de cada cara en estos ejes). El marco de la cara se congela al crear el boceto: si después cambia un parámetro que mueve la cara, el boceto no la sigue.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `plane` (texto; opcional, por defecto `"XY"`): "XY", "XZ", "YZ", el id/nombre de un plano de construcción, o una cara plana: selector (">Z") o id ("Cuerpo1/F6").
  - `name` (texto; opcional, por defecto `null`): nombre del boceto; vacío = "Boceto1", "Boceto2"…
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
  - `width` (número; opcional, por defecto `null`): tamaño en x del boceto (mm), para las formas con tamaño.
  - `height` (número; opcional, por defecto `null`): tamaño en y del boceto (mm), para las formas con tamaño.
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

Dibuja un polígono regular de n lados (líneas iguales sobre un círculo guía de construcción, como la interfaz). Inscrito: los vértices están sobre el círculo de radio `radius`; circunscrito: los lados son tangentes a ese círculo.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `sides` (entero; obligatorio): cantidad de lados (3 o más).
  - `radius` (número; obligatorio): radio del círculo guía en mm (circunradio si es inscrito, apotema si es circunscrito).
  - `center_x` (número; opcional, por defecto `0.0`): x del centro (mm).
  - `center_y` (número; opcional, por defecto `0.0`): y del centro (mm).
  - `rotation` (número; opcional, por defecto `0.0`): ángulo en grados del primer vértice respecto del eje x del boceto.
  - `kind` ("inscribed" | "circumscribed"; opcional, por defecto `"inscribed"`): "inscribed" (vértices sobre el círculo) o "circumscribed" (lados tangentes al círculo).
  - `sketch` (texto; opcional, por defecto `null`): id o nombre del boceto; vacío = el último boceto del timeline.
  - `construction` (true/false; opcional, por defecto `false`): true para un polígono de construcción (no forma perfiles).
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

Agrega una cota (dimensión) que maneja la geometría. El valor es un número (mm o grados) o una expresión con parámetros ('ancho / 2'); si se omite, usa la medida actual. Entidades por tipo: distance: dos puntos, una línea, un punto y una línea, o dos líneas; horizontal y vertical: dos puntos o una línea; radius y diameter: un círculo o arco; angle: dos líneas; offset: dos líneas o dos círculos/arcos.

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

Crea un boceto COMPLETO en una sola llamada (un paso de deshacer): geometría, restricciones y cotas. entities: lista de {type, ...}: line{start,end}, rectangle{corner1,corner2 | center,width,height | origin,width,height}, circle{center,radius}, arc{center,start,sweep | start,mid,end}, polygon{sides,radius,center,rotation,kind}, spline{points,spline_type,degree,closed}, point{at}; todas aceptan id (nombre propio para citarla) y construction. Las coordenadas son [x, y] en mm del plano. constraints: [{type, entities:[citas]}]; dimensions: [{type, entities:[citas], value}] (value puede ser una expresión con parámetros). Citas: 'id' (la curva), 'id.start', 'id.end', 'id.center', y en un rectángulo 'id.bottom/right/top/left' (líneas) y 'id.c1..c4' (esquinas); un entero cita un id de entidad ya existente. Sin id, la entidad se cita 'e0', 'e1'… según su posición en la lista. Devuelve handles (cita → id real), perfiles y estado.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `plane` (texto; opcional, por defecto `"XY"`): "XY", "XZ", "YZ" o el id/nombre de un plano de construcción.
  - `entities` (lista de objeto o null; opcional, por defecto `null`): geometría del boceto (ver la descripción de la herramienta).
  - `constraints` (lista de objeto o null; opcional, por defecto `null`): restricciones, cada una {"type": ..., "entities": [citas]}.
  - `dimensions` (lista de objeto o null; opcional, por defecto `null`): cotas, cada una {"type": ..., "entities": [citas], "value": número o expresión}.
  - `name` (texto; opcional, por defecto `null`): nombre del boceto; vacío = "Boceto1", "Boceto2"…
- CLI: `omnicad call sketch_from_spec --doc pieza.omnicad`

## Grupo solido

Sólidos: extruir, revolucionar, primitivas, empalmes, agujeros y patrones.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`extrude`](#extrude) | sí | Extruye perfiles de un boceto. profile: índice, lista de índices, 'all' o 'largest' (el perfil de mayor área, p. ej. la placa con sus agujeros). distance acepta un número (mm) o una expresión con parámetros. |
| [`revolve`](#revolve) | sí | Revoluciona perfiles de un boceto alrededor de un eje. axis: 'sketch_x' o 'sketch_y' (ejes del plano del boceto que pasan por su origen), 'x', 'y', 'z' (ejes del origen del diseño) o el id de una línea del boceto (get_sketch; puede ser de construcción). |
| [`sweep`](#sweep) | sí | Barre un perfil a lo largo de una ruta de otro boceto (o del mismo). |
| [`loft`](#loft) | sí | Solevación: un sólido que pasa por los perfiles de varios bocetos, en el orden dado (mínimo dos). profiles elige un perfil por boceto (índice o 'largest'); vacío = el perfil 0 de cada uno. ruled usa tramos rectos entre secciones y closed une la última con la primera. |
| [`create_box`](#create_box) | sí | Crea una caja alineada con los ejes. length es el tamaño en X, width en Y y height en Z (mm). (x, y, z) es el centro de la cara de abajo: la caja queda centrada en X e Y y apoyada en z. |
| [`create_cylinder`](#create_cylinder) | sí | Crea un cilindro con el eje en Z (para otro eje, girarlo con move_body). (x, y, z) es el centro de la base; la altura crece hacia +Z. |
| [`create_sphere`](#create_sphere) | sí | Crea una esfera. (x, y, z) es su centro. |
| [`create_torus`](#create_torus) | sí | Crea un toroide con el eje en Z (para otro eje, girarlo con move_body). (x, y, z) es su centro. |
| [`boolean_operation`](#boolean_operation) | sí | Combina cuerpos: join (unir), cut (restar las herramientas al objetivo) o intersect (quedarse con lo común). |
| [`mirror`](#mirror) | sí | Refleja cuerpos respecto de un plano (origen o de construcción). |
| [`rectangular_pattern`](#rectangular_pattern) | sí | Patrón rectangular de cuerpos: copias en una o dos direcciones (ejes del origen), con la separación entre copias consecutivas. |
| [`circular_pattern`](#circular_pattern) | sí | Patrón circular de cuerpos alrededor de un eje del origen (x, y o z). |
| [`move_body`](#move_body) | sí | Mueve (o copia) cuerpos: primero gira rotate = [rx, ry, rz] grados alrededor del pivote (en ese orden) y después traslada translate = [x, y, z] mm. |
| [`fillet`](#fillet) | sí | Redondea aristas (empalme de radio constante). |
| [`chamfer`](#chamfer) | sí | Achaflana aristas (distancia igual en las dos caras). |
| [`shell`](#shell) | sí | Vacía un cuerpo dejando paredes de un espesor dado; las caras elegidas se quitan (quedan abiertas). |
| [`create_hole`](#create_hole) | sí | Hace agujeros redondos desde una cara plana hacia adentro del material: simples, abocardados (counterbore) o avellanados (countersink), ciegos (depth) o pasantes (through_all). |
| [`draft`](#draft) | sí | Desmoldeo: inclina caras un ángulo respecto de un plano neutro (la cara o el plano que no se mueve), para poder sacar la pieza del molde. |

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
  - `twist_angle` (número o expresión; opcional, por defecto `0`): ángulo de torsión total en grados.
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

Crea una caja alineada con los ejes. length es el tamaño en X, width en Y y height en Z (mm). (x, y, z) es el centro de la cara de abajo: la caja queda centrada en X e Y y apoyada en z. Medidas y posición aceptan expresiones con parámetros.

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

Crea un cilindro con el eje en Z (para otro eje, girarlo con move_body). (x, y, z) es el centro de la base; la altura crece hacia +Z.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `radius` (número o expresión; obligatorio): radio en mm (positivo).
  - `height` (número o expresión; obligatorio): altura en mm (positiva).
  - `x` (número o expresión; opcional, por defecto `0`): x del centro de la base (mm).
  - `y` (número o expresión; opcional, por defecto `0`): y del centro de la base (mm).
  - `z` (número o expresión; opcional, por defecto `0`): z de la base (mm).
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo afectado por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
- CLI: `omnicad call create_cylinder --doc pieza.omnicad radius=… height=…`

### `create_sphere`

Crea una esfera. (x, y, z) es su centro.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `radius` (número o expresión; obligatorio): radio en mm (positivo).
  - `x` (número o expresión; opcional, por defecto `0`): x del centro (mm).
  - `y` (número o expresión; opcional, por defecto `0`): y del centro (mm).
  - `z` (número o expresión; opcional, por defecto `0`): z del centro (mm).
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo afectado por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
- CLI: `omnicad call create_sphere --doc pieza.omnicad radius=…`

### `create_torus`

Crea un toroide con el eje en Z (para otro eje, girarlo con move_body). (x, y, z) es su centro.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `major_radius` (número o expresión; obligatorio): radio mayor en mm (del centro al centro del tubo); tiene que ser mayor que minor_radius.
  - `minor_radius` (número o expresión; obligatorio): radio menor en mm (del tubo).
  - `x` (número o expresión; opcional, por defecto `0`): x del centro (mm).
  - `y` (número o expresión; opcional, por defecto `0`): y del centro (mm).
  - `z` (número o expresión; opcional, por defecto `0`): z del centro (mm).
  - `operation` ("new_body" | "join" | "cut" | "intersect"; opcional, por defecto `"new_body"`): "new_body", "join", "cut" o "intersect".
  - `target` (texto o lista de texto o null; opcional, por defecto `null`): cuerpo afectado por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
- CLI: `omnicad call create_torus --doc pieza.omnicad major_radius=… minor_radius=…`

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
  - `x_count` (entero; opcional, por defecto `1`): cantidad de instancias en la dirección 1, original incluido (1 = sin copias).
  - `x_spacing` (número o expresión; opcional, por defecto `"10 mm"`): separación entre instancias consecutivas en la dirección 1 (mm o expresión).
  - `y_count` (entero; opcional, por defecto `1`): cantidad de instancias en la dirección 2, original incluido.
  - `y_spacing` (número o expresión; opcional, por defecto `"10 mm"`): separación entre instancias consecutivas en la dirección 2.
  - `axis1` ("x" | "y" | "z"; opcional, por defecto `"x"`): eje de la dirección 1 ("x", "y" o "z").
  - `axis2` ("x" | "y" | "z"; opcional, por defecto `"y"`): eje de la dirección 2.
  - `combine` (true/false; opcional, por defecto `false`): true para unir las copias al cuerpo original.
- CLI: `omnicad call rectangular_pattern --doc pieza.omnicad bodies=…`

### `circular_pattern`

Patrón circular de cuerpos alrededor de un eje del origen (x, y o z). Con 360° las copias se reparten en toda la vuelta; con menos, entre el original y el ángulo total. count incluye el original.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `bodies` (texto o lista de texto; obligatorio): cuerpo(s) a repetir (id o nombre).
  - `count` (entero; obligatorio): cantidad de instancias, original incluido (2 o más).
  - `axis` ("x" | "y" | "z"; opcional, por defecto `"z"`): eje de giro del origen: "x", "y" o "z".
  - `total_angle` (número o expresión; opcional, por defecto `360`): ángulo total en grados (número o expresión); 360 = vuelta completa.
  - `combine` (true/false; opcional, por defecto `false`): true para unir las copias al cuerpo original.
- CLI: `omnicad call circular_pattern --doc pieza.omnicad bodies=… count=…`

### `move_body`

Mueve (o copia) cuerpos: primero gira rotate = [rx, ry, rz] grados alrededor del pivote (en ese orden) y después traslada translate = [x, y, z] mm. El pivote es el centro de la caja de los cuerpos o el origen del diseño.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `body` (texto o lista de texto; obligatorio): cuerpo(s) a mover (id o nombre).
  - `translate` (lista de número o expresión o null; opcional, por defecto `null`): desplazamiento [x, y, z] en mm (números o expresiones); vacío = sin desplazamiento.
  - `rotate` (lista de número o expresión o null; opcional, por defecto `null`): giro [rx, ry, rz] en grados (números o expresiones); vacío = sin giro.
  - `pivot` ("center" | "origin"; opcional, por defecto `"center"`): centro del giro: "center" (centro de los cuerpos) u "origin" (origen del diseño).
  - `copy` (true/false; opcional, por defecto `false`): true para dejar el original y crear cuerpos nuevos con el movimiento.
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

Hace agujeros redondos desde una cara plana hacia adentro del material: simples, abocardados (counterbore) o avellanados (countersink), ciegos (depth) o pasantes (through_all). La cara se elige con un selector (p. ej. '>Z'), un id de find_faces o 'Cuerpo1/F6'; tiene que ser UNA sola cara plana. points son las posiciones: [u, v] en mm en los ejes x,y de un boceto sobre esa cara (find_faces da el center_uv de la cara; create_sketch describe los ejes) o [x, y, z] del mundo (se proyecta sobre la cara); sin points, un agujero en el centro de la cara. El fondo es plano salvo drill_tip=true (cono de 118°). diameter y depth aceptan número (mm) o expresión. La cara se guarda como referencia persistente, pero la posición de los puntos es fija en el espacio.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `face` (texto; obligatorio): la cara plana donde se empieza: selector (">Z"), id de find_faces ("Cuerpo1/F6"). Tiene que dar UNA cara.
  - `diameter` (número o expresión; obligatorio): diámetro del agujero en mm (número o expresión).
  - `points` (lista de lista de número o null; opcional, por defecto `null`): posiciones: lista de [u, v] (ejes x,y de un boceto sobre la cara) o [x, y, z] (mundo); vacío = centro de la cara.
  - `depth` (número o expresión; opcional, por defecto `null`): profundidad en mm hasta el fondo plano; obligatoria salvo con through_all.
  - `through_all` (true/false; opcional, por defecto `false`): true atraviesa todo el cuerpo (ignora depth).
  - `hole_type` ("simple" | "counterbore" | "countersink"; opcional, por defecto `"simple"`): "simple", "counterbore" (abocardado) o "countersink" (avellanado).
  - `counterbore_diameter` (número o expresión; opcional, por defecto `null`): diámetro del abocardado en mm (mayor que diameter); solo con counterbore.
  - `counterbore_depth` (número o expresión; opcional, por defecto `null`): profundidad del abocardado en mm; solo con counterbore.
  - `countersink_diameter` (número o expresión; opcional, por defecto `null`): diámetro del avellanado en la superficie en mm; solo con countersink.
  - `countersink_angle` (número o expresión; opcional, por defecto `90`): ángulo total del avellanado en grados; solo con countersink.
  - `drill_tip` (true/false; opcional, por defecto `false`): true deja el fondo en cono de 118° como una broca; false, fondo plano.
  - `body` (texto; opcional, por defecto `null`): cuerpo sobre el que se evalúan los selectores; vacío = el único cuerpo del documento.
- CLI: `omnicad call create_hole --doc pieza.omnicad face=… diameter=…`

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

## Grupo inspeccion

Ver y medir el resultado.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`get_viewport_image`](#get_viewport_image) | no | Renderiza el modelo y devuelve una imagen PNG (sombreado, sombras y suelo) desde una vista estándar o una dirección propia. |
| [`get_physical_properties`](#get_physical_properties) | no | Volumen (mm³), área (mm²), masa (g), centro de masa y caja envolvente de cada cuerpo y del total. |
| [`measure_distance`](#measure_distance) | no | Distancia mínima entre dos cosas, cada una un cuerpo, una cara, una arista o un punto. |
| [`check_interference`](#check_interference) | no | Busca pares de cuerpos sólidos que se superponen y devuelve cada par con el volumen común (mm³) y su caja envolvente. |
| [`find_faces`](#find_faces) | no | Lista las caras de un cuerpo (o de todos), opcionalmente filtradas por un selector. |
| [`find_edges`](#find_edges) | no | Lista las aristas de un cuerpo (o de todos), opcionalmente filtradas por un selector. |
| [`measure_angle`](#measure_angle) | no | Ángulo (grados) entre dos caras planas, dos aristas rectas, o una cara y una arista. |

### `get_viewport_image`

Renderiza el modelo y devuelve una imagen PNG (sombreado, sombras y suelo) desde una vista estándar o una dirección propia. Es la forma de VER el resultado.

- Modifica el documento: no.
- Parámetros:
  - `view` ("iso" | "front" | "back" | "top" | "bottom" | "left" | "right"; opcional, por defecto `"iso"`): vista estándar. "iso" es la isométrica; "front" mira hacia +Y (cámara en -Y); "right" mira hacia -X.
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

Distancia mínima entre dos cosas, cada una un cuerpo, una cara, una arista o un punto. Caras y aristas se dan por id (find_faces / find_edges) o por selector (>Z elige sobre las caras; edges:|Z sobre las aristas). Devuelve la distancia (mm), los dos puntos más cercanos y el desfase XYZ de a hacia b.

- Modifica el documento: no.
- Parámetros:
  - `a` (texto o lista de número; obligatorio): cuerpo (id o nombre), cara o arista (id "Cuerpo1/F3" o selector ">Z", "edges:|Z") o punto [x, y, z] en mm.
  - `b` (texto o lista de número; obligatorio): cuerpo (id o nombre), cara o arista (id "Cuerpo1/F3" o selector ">Z", "edges:|Z") o punto [x, y, z] en mm.
- CLI: `omnicad call measure_distance --doc pieza.omnicad a=… b=…`

### `check_interference`

Busca pares de cuerpos sólidos que se superponen y devuelve cada par con el volumen común (mm³) y su caja envolvente. Los que solo se tocan por una cara no cuentan.

- Modifica el documento: no.
- Parámetros:
  - `bodies` (lista de texto o null; opcional, por defecto `null`): ids o nombres de los cuerpos a comparar entre sí; vacío = todos los sólidos.
- CLI: `omnicad call check_interference --doc pieza.omnicad`

### `find_faces`

Lista las caras de un cuerpo (o de todos), opcionalmente filtradas por un selector. Selector estilo CadQuery: >Z <Z (centro más alto/bajo), |Z (aristas paralelas al eje; caras con la normal paralela), #Z (perpendicular), +Z -Z (normal de caras planas), %PLANE %CYLINDER %CIRCLE %LINE (tipo), nearest:[x,y,z], combinables con and, or, not y paréntesis (get_guide topic=selectores). Cada elemento trae un id corto (p. ej. 'Cuerpo1/F3') VÁLIDO HASTA EL PRÓXIMO CAMBIO DEL DOCUMENTO (un id viejo da STALE_ID); fillet, chamfer, shell, create_hole y create_sketch lo aceptan, o aceptan el selector directamente. Sin coincidencias da NO_MATCH. Cada cara trae tipo (plane, cylinder, cone, sphere, torus, bspline), área (mm²), centro, normal (planas) o eje (cilindros y conos), radio y, en las planas, center_uv: el centro en los ejes x,y de un boceto sobre esa cara.

- Modifica el documento: no.
- Parámetros:
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo; vacío = todos los cuerpos.
  - `selector` (texto; opcional, por defecto `null`): filtro estilo CadQuery, p. ej. ">Z" (la tapa), "#Z" (las laterales), "%CYLINDER"; vacío = todas.
- CLI: `omnicad call find_faces --doc pieza.omnicad`

### `find_edges`

Lista las aristas de un cuerpo (o de todos), opcionalmente filtradas por un selector. Selector estilo CadQuery: >Z <Z (centro más alto/bajo), |Z (aristas paralelas al eje; caras con la normal paralela), #Z (perpendicular), +Z -Z (normal de caras planas), %PLANE %CYLINDER %CIRCLE %LINE (tipo), nearest:[x,y,z], combinables con and, or, not y paréntesis (get_guide topic=selectores). Cada elemento trae un id corto (p. ej. 'Cuerpo1/F3') VÁLIDO HASTA EL PRÓXIMO CAMBIO DEL DOCUMENTO (un id viejo da STALE_ID); fillet, chamfer, shell, create_hole y create_sketch lo aceptan, o aceptan el selector directamente. Sin coincidencias da NO_MATCH. Cada arista trae tipo (line, circle, ellipse, bspline), largo (mm), centro, dirección (rectas) y radio (círculos).

- Modifica el documento: no.
- Parámetros:
  - `body` (texto; opcional, por defecto `null`): id o nombre del cuerpo; vacío = todos los cuerpos.
  - `selector` (texto; opcional, por defecto `null`): filtro estilo CadQuery, p. ej. "|Z" (las verticales), ">Z" (las de arriba), "%CIRCLE"; vacío = todas.
- CLI: `omnicad call find_edges --doc pieza.omnicad`

### `measure_angle`

Ángulo (grados) entre dos caras planas, dos aristas rectas, o una cara y una arista. Cara-cara: ángulo entre las normales exteriores (0 a 180; dos caras de una caja que se tocan en una arista dan 90), más acute_angle (0 a 90). Arista-arista y cara-arista: ángulo agudo (0 a 90), porque una arista no tiene sentido. Cada lado es un id de find_faces / find_edges o un selector (sobre caras; edges:|Z para aristas) que elija UNA sola.

- Modifica el documento: no.
- Parámetros:
  - `a` (texto; obligatorio): cara o arista: id ("Cuerpo1/F3") o selector (">Z", "edges:|Z").
  - `b` (texto; obligatorio): cara o arista: id ("Cuerpo1/F3") o selector (">X", "edges:|X").
- CLI: `omnicad call measure_angle --doc pieza.omnicad a=… b=…`

## Grupo avanzado

Cualquier operación, receta, código y guía.

| Herramienta | Modifica | Resumen |
|---|---|---|
| [`list_operation_types`](#list_operation_types) | no | Lista todos los tipos de operación del timeline que acepta run_operation: tipo, etiqueta y una línea que dice qué hace. |
| [`describe_operation`](#describe_operation) | no | Explica un tipo de operación: parámetros con su valor por defecto, tipo y si aceptan expresiones; el docstring completo y un ejemplo de llamada a run_operation. |
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

Explica un tipo de operación: parámetros con su valor por defecto, tipo y si aceptan expresiones; el docstring completo y un ejemplo de llamada a run_operation.

- Modifica el documento: no.
- Parámetros:
  - `type` (texto; obligatorio): tipo de operación (list_operation_types los lista), p. ej. "primitiva".
- CLI: `omnicad call describe_operation --doc pieza.omnicad type=…`

### `run_operation`

Agrega al timeline cualquier operación por su tipo y sus parámetros nativos (claves en español, las de describe_operation). Una llamada = un paso de deshacer; si el paso falla, el documento queda intacto.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `type` (texto; obligatorio): tipo de operación (list_operation_types los lista).
  - `params` (objeto; opcional, por defecto `null`): parámetros a cambiar respecto de los valores por defecto, con las claves de describe_operation.
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
  - `recipe` (objeto; obligatorio): receta como la devuelve get_recipe (objeto con 'operaciones', 'parametros', etc.).
  - `mode` ("replace" | "append"; opcional, por defecto `"replace"`): "replace" reemplaza el contenido del documento (conserva su archivo); "append" suma al final del timeline los pasos y parámetros de la receta (renumera los ids que chocan; un parámetro con el mismo nombre y otra expresión es un error) y deja el marcador al final.
- CLI: `omnicad call apply_recipe --doc pieza.omnicad recipe=…`

### `execute_code`

Ejecuta código Python con api, sesion, doc y llamar(nombre, args) ya definidos. Devuelve lo impreso (stdout) y la variable `result` si el código la define. Todo es un paso de deshacer; si el código lanza una excepción, el documento queda intacto.

- Modifica el documento: sí, es un paso de deshacer.
- Parámetros:
  - `code` (texto; obligatorio): código Python. Definidos: api (el paquete omnicad.api), sesion, doc (el documento activo) y llamar (atajo de api.llamar(sesion, nombre, args)). Asigná `result = ...` para devolver un valor.
- CLI: `omnicad call execute_code --doc pieza.omnicad code=…`

### `get_guide`

Guía corta para agentes (ciclo de trabajo, unidades, cómo leer errores). Sin tema devuelve el índice.

- Modifica el documento: no.
- Parámetros:
  - `topic` (texto; opcional, por defecto `null`): tema de la guía (el índice los lista), p. ej. "flujo"; vacío = el índice.
- CLI: `omnicad call get_guide --doc pieza.omnicad`

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
- CLI: `omnicad call run_bench --doc pieza.omnicad`
