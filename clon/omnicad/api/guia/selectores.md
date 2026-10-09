# Selectores de caras y aristas

Al estilo CadQuery. Sirven en `find_faces`, `find_edges`, `fillet`, `chamfer`, `shell`, `create_hole`,
`draft`, `create_sketch`, `measure_distance` y `measure_angle`. Se evalúan sobre UN cuerpo (`body`, o el único).

| Selector | Elige |
|---|---|
| `>Z` `<Z` (y X, Y) | las de centro más alto / más bajo en ese eje (pueden ser varias); `>Z[1]` = el segundo nivel |
| `\|Z` | aristas rectas paralelas al eje; caras con la normal paralela (caja: tapa y base) |
| `#Z` | lo perpendicular: aristas perpendiculares; caras con la normal perpendicular (caja: las 4 laterales) |
| `+Z` `-Z` | caras planas con la normal en ese sentido |
| `%PLANE` `%CYLINDER` `%CONE` `%SPHERE` `%TORUS` | tipo de cara |
| `%LINE` `%CIRCLE` `%ELLIPSE` `%BSPLINE` | tipo de arista |
| `nearest:[x,y,z]` | la más cercana al punto (una sola) |

Se combinan con `and`, `or`, `not` y paréntesis: `|Z and >X`, `#Z and not <X`, `(>Z or <Z) and %PLANE`.
Cada término se evalúa sobre todas y después se combinan los resultados.

## Ejemplos

- Redondear las 4 aristas verticales de una caja: `fillet(edges="|Z", radius=2)`.
- Vaciar abriendo la tapa: `shell(body="Cuerpo1", faces=">Z", thickness=2)`.
- Agujero pasante en la tapa: `create_hole(face=">Z", diameter=6, through_all=true)`.
- Boceto sobre la tapa: `create_sketch(plane=">Z")`. Ejes: en caras horizontales x→+X; en las demás y→+Z.
  El origen es la proyección del origen del mundo; `find_faces` da center_uv (el centro de la cara en esos ejes).
  `extrude` va hacia la normal exterior: `join` crece hacia afuera y `cut` entra al material solo (como Fusion); `reverse` fuerza el sentido.
- Ángulo entre la tapa y una lateral: `measure_angle(a=">Z", b=">X")` da 90.

## Ids efímeros

`find_faces` y `find_edges` devuelven un `id` por elemento (`Cuerpo1/F3` cara, `Cuerpo1/E7` arista), tipo,
área o largo, centro y normal o dirección. El id vale HASTA EL PRÓXIMO CAMBIO del documento (`STALE_ID` si
se vence): después, volvé a listar o usá un selector. Una lista mezcla ids y selectores (se unen).
Donde se espera un solo elemento (medir, boceto) el selector va sobre caras; para aristas: `edges:|Z` o un id.

## Errores

- `INVALID_SELECTOR`: no se entiende el texto (el mensaje dice dónde).
- `NO_MATCH`: es válido pero no eligió nada (el mensaje cuenta las caras o aristas y sus tipos).
- `REFERENCE_LOST`: al recalcular, una cara o arista guardada ya no existe; el documento queda igual.
