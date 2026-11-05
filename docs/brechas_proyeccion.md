# Proyectar/Incluir del boceto: Fusion contra OmniCAD

Revisión del 2026-11-05 (subagente proyeccion), a partir de B-119 (video de Gerardo: Proyectar un cuerpo de revolución
en un plano por su eje daba 28 curvas sueltas; Fusion da la silueta cerrada). Lo pendiente vive solo en
`docs/seguimiento/`; acá queda la comparación y en qué quedó cada herramienta.

**Fuentes:** `docs/fusion_docs/contenido/fusion-sketch/` (buscado con `scripts/fusion_docs.py buscar project|intersect|
include 3D geometry|project to surface|break link -s fusion-sketch`): «Project reference», «Project geometry onto a sketch
plane», «Project and include geometry in sketches», «Intersect geometry» y su «Reference», «Include 3D geometry»,
«Project to surface» y su «Reference», «Intersection curve» y su «Reference», «Project the spun profile of geometry» y
«Break link and association to projected geometry» (solo video). Cuadros de los videos en
`evidencias/proyeccion_2026-11-05/`. Pruebas: `clon/tests/test_proyeccion_seccion.py`, `clon/tests/test_proyectar_tarjeta.py`
y la sonda `evidencias/proyeccion_2026-11-05/sonda_api.py`.

| Fusion | Qué hace en Fusion | OmniCAD (API) | Estado 2026-11-05 |
|---|---|---|---|
| Project › Specified Entities | Proyecta caras, aristas y puntos; asociativo con Projection Link | `project_to_sketch` (edges, faces, vertices, references); tarjeta con vista previa | Anda: caja con empalmes desde arriba, 8 curvas y un perfil (792,3 mm²) |
| Project › Bodies | «Projects closed profiles that are ready for constraints and downstream features» | `project_to_sketch(bodies=…)`; tarjeta con el filtro Cuerpos | **Arreglado (B-119):** da la silueta cerrada del cuerpo (`perfiles.silueta_forma`, HLR + unión de regiones), también curvo y de costado: cilindro acostado → rectángulo, bala → 13 líneas y un perfil, toro de costado → estadio. Asociativa (modo `silhouette`). Si el cuerpo cambia y la silueta tiene otros tramos, se rehace sola y las restricciones pasan al tramo nuevo que pasa por el mismo lugar (H-77). Formas libres: HLR exacto aparte (curvas exactas) o, si no termina, contorno de la malla con B-splines a 0,01 mm; con caché por forma (H-78) |
| Projection Link | Casilla: asociativa o congelada | `link` en `project_to_sketch`; casilla de la tarjeta | Anda (sigue al cambiar un parámetro; sin vínculo queda congelada) |
| Intersect (Specified / Bodies) | Curvas donde lo elegido corta el plano del boceto; con Bodies, el perfil entero | `project_to_sketch(mode="intersect")`; herramienta Intersecar con su tarjeta | Anda: esfera R10 cortada a z = 5 da un perfil de 235,6 mm² |
| Include 3D Geometry | Incluye caras, aristas y puntos como geometría 3D del boceto | `include_3d_geometry` (nueva); herramienta Incluir geometría 3D | **Arreglado (B-204):** antes los llevaba al plano (igual que Proyectar). Ahora quedan donde están, como curvas 3D asociativas; los vértices, como puntos 3D que también siguen al modelo (H-79) |
| Project To Surface | Curvas de boceto sobre caras: Closest Point o Along Vector | `project_to_surface` (mode closest / vector) | Anda. Along Vector proyecta solo hacia donde apunta la dirección (con el eje Z sobre una esfera de abajo no deja nada: usar `[0, 0, -1]`) |
| Intersection Curve | Curva 3D donde la curva de boceto (extruida) corta caras o curvas | `intersect_curves` | Anda: un círculo sobre una esfera da 2 curvas 3D |
| Spun Profile | Perfil girado de cuerpos, caras, aristas o puntos alrededor de un eje; Project Axis, Tolerance, Flip | `project_spun_profile` (outer_contour, project_axis, tolerance, flip) | **Arreglado (B-203):** las tapas no llegaban al eje (un cilindro daba solo la línea del costado). Ahora llegan, y con Project Axis el perfil cierra (cilindro R10 × 30: 300 mm²) |
| Isoparametric Curve | Curvas U/V de una cara, única o distribuidas, con vínculo | `isoparametric_curve` | No se revisó a fondo esta vez (BOC-76 sigue Parcial) |
| Break Link | Rompe el vínculo: la geometría queda donde está y editable | `break_projection_link`; Romper vínculo en el menú del boceto | Anda (también con siluetas) |
| Manage Lost Projections (Re-Link, Break Link, Delete Geometry, Fade Other Geometry) | Al editar un paso anterior, lo perdido se re-vincula, se rompe o se borra | `manage_lost_projections` (relink, break, delete); diálogo con «Atenuar el resto» | Anda (tests/test_boceto_fase6.py). Re-vincular desde la ventana pasa ahora el tipo de lo elegido: la silueta lo necesita |
| Show Projected Geometries | Casilla de la paleta del boceto | `sketch_view(action="projected")`; casilla «Geometrías proyectadas» | Anda (tests/test_p23_bocetos.py) |
| Proyectado como perfil | La geometría proyectada sirve para extruir o girar | `extrude` / `revolve` sobre el perfil | Anda: la silueta del cilindro se extruye |

## Resuelto después (2026-11-05, pedido de Gerardo)

- **H-77:** una silueta que cambia de cantidad de tramos ya no queda perdida: `Boceto.rehacer_proyeccion` la rehace
  (los tramos que no se movieron conservan su id; las restricciones y cotas pasan al tramo nuevo del mismo tipo que
  pasa por su punto medio; las demás se quitan con aviso). También al re-vincular. Al editar el boceto (API, ventana o
  parámetros) la silueta rehecha se guarda: sus tramos se pueden restringir con el id que muestra `get_sketch`.
- **H-78:** formas libres en curvas exactas (HLR exacto en un proceso aparte, tope 3 s) o, si no termina, B-splines
  ajustadas a la sombra de su malla (a menos de 0,05 mm). Rosca modelada M8: 16,0 s (XZ) y 16,8 s (XY, sin perfil)
  por cada recálculo antes; la caché usa el texto BREP de la forma, así que no repite nada mientras la forma no cambie,
  también con «Recalcular todo» (de 19,5 s a 4,4 s, lo que tarda la rosca misma). La primera vez, ver H-80.
- **H-79:** los vértices de Incluir geometría 3D siguen al modelo (tabla `vinculos` del boceto 3D; `get_sketch` les da
  `source`). Movidos a mano (herramienta o tríada) dejan de seguirlo, igual que las curvas incluidas.
- **H-80:** una forma libre pesada (más de 300 polos B-spline, como una rosca modelada) ya no pasa por el HLR exacto
  (no tiene tope): su sombra sale de la malla, unida en 2D con manifold3d, y el borde se ajusta con curvas a 0,01 mm.
  Rosca M8 vista desde su eje: de 13,7 s a menos de 1 s. Las formas libres chicas (empalmes, solevados) siguen
  exactas.

## Lo que queda (en `docs/seguimiento/`)

- **RH18:** falta Contour (cortes paralelos) y Pull.
