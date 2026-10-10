# Texto y vectores en el boceto

Grupo `vectores`. Todo entra al boceto como curvas: lo que forma una región cerrada da perfiles para extruir.

## Texto

- `list_fonts(query="seg")` busca entre TODAS las fuentes instaladas (sistema, usuario, variables). `font` también
  acepta la ruta a un `.ttf` / `.otf`; `add_font_folder` suma una carpeta en la sesión.
- `add_text(text, x, y, height, font, bold, italic, ...)`: `(x, y)` es el ancla. Opciones: **letter_spacing** (mm entre
  letras), **line_spacing** (factor), `align` (left/center/right dentro de la caja), `anchor` (qué parte del bloque cae
  sobre el ancla: baseline/top/middle/bottom), **box_width** (>0 parte las líneas en palabras), **flip_h** / **flip_v**.
  `\n` en el texto separa líneas.
- `edit_text(entity, ...)` cambia lo que se pase; `explode_text(entity)` lo vuelve líneas y splines fijas.
- `get_sketch` muestra el texto con todas sus opciones (`type: "text"`).
- Parámetros dentro del texto: `{ancho}`, `{largo / 2}` o con formato `{ancho:.1f}`. Se recalculan solos al cambiar
  el parámetro y el parámetro queda protegido contra borrado. `explode_text` congela el valor de ese momento.
- Texto en curva: **path_entity** (id de una línea, arco, círculo, elipse o spline del boceto) hace que las
  letras sigan la curva. **path_side** right recorre la curva al revés (letras del otro lado, derechas);
  **path_position** 0-1 ubica el texto (en un círculo 0.25 = arriba); **path_offset** separa la base de la curva;
  **fit_path** lo reparte en todo el largo. En un círculo: arriba por fuera = right + 0.25; abajo por dentro =
  left + 0.75. Si se borra la curva, el texto vuelve a ser recto.
- Limitación: no hay ligaduras ni formas contextuales (árabe, devanagari): cada carácter es un glifo.

## Archivos 2D

- `insert_svg`, `insert_dxf`, `trace_image` (imagen → contornos). Con `plane` crean un boceto nuevo en ese plano o
  cara; sin `plane` suman al boceto `sketch` (por defecto el último). Orden: voltear, escalar (o `width` en mm),
  girar, mover.
- `inspect_svg(path)` dice tamaño, capas (grupos) y colores: después `insert_svg(layers=[...], colors=["#ff0000"])`
  importa solo esa parte (cortar vs. grabar).
- `trace_image`: `threshold` vacío = automático, `invert` si la tinta es lo claro, `curves=true` da una spline por
  contorno (menos entidades, más suave), `tolerance` y `smoothing` en píxeles. El tamaño sale de `width` (mm) o `dpi`.
- `export_sketch(path)` guarda el boceto como `.dxf` o `.svg` (mm reales) para láser, vinilo o CNC; con
  **include_construction** suma la construcción en un grupo/capa aparte.
- Todas devuelven **entities_added**, `profiles` y `status`; con muchas curvas conviene `get_sketch` solo si hace falta.

## Editar vectores

- `transform_sketch(entities, dx, dy, angle, scale, mirror, copy)`: mover, girar, escalar y espejar lo elegido (o
  todo el boceto) alrededor del centro de su caja. Al girar algo que no sea múltiplo de 180°, se quitan sus
  restricciones horizontal / vertical (si no, la geometría colapsa).
- `combine_profiles(profiles, operation, tool_profiles)`: unir (contorno limpio, sin líneas internas), restar o
  intersecar perfiles. Por defecto borra las curvas usadas (un texto usado se borra entero).
- `offset_profiles(profiles, distance, corners)`: contorno a X mm de cualquier perfil (letras, splines de un SVG),
  con agujeros; positivo agranda, negativo achica.
- `clean_sketch(tolerance)`: después de importar un SVG / DXF o vectorizar, borra repetidas, une extremos a
  menos de la tolerancia y junta líneas alineadas (no toca lo que tiene restricciones o cotas).
- Nodos: `move_sketch_point(point, x, y)` mueve un extremo o un punto de control (los ids están en **points**
  de cada curva de `get_sketch`); `delete_sketch_entities(entities)` borra curvas, puntos, restricciones o cotas.
- Índices de perfil: los de `get_sketch` (cambian cuando cambia el boceto: volvé a mirarlos después de editar).

