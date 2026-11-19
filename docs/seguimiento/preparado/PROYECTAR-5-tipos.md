# PROYECTAR · los 5 tipos del diálogo del boceto

Preparado el 2026-11-19 para la prueba E7. Nada de la app se tocó: solo se agregaron tests de cobertura y este resumen.

## Los 5 tipos y dónde viven

El diálogo es la tarjeta de la paleta: `clon/omnicad/ui/modo_boceto.py:109` (`TIPOS_POR_FAMILIA["proyectar"]`), opciones en
`OPCIONES_HERRAMIENTA`, `NUMEROS_HERRAMIENTA`, `ENTEROS_HERRAMIENTA` y `CASILLAS_HERRAMIENTA` del mismo archivo.

| Tipo (paleta) | Herramienta de la API | Implementación |
|---|---|---|
| Proyectar | `project_to_sketch` (`mode=project`) | `api/herramientas_boceto.py:3027`; tarjeta en `ui/editor_boceto_proyeccion.py` |
| Intersecar | `project_to_sketch` (`mode=intersect`) | ídem |
| Incluir geometría 3D | `include_3d_geometry` | `api/herramientas_boceto3d.py:550` |
| Perfil giratorio | `project_spun_profile` | `api/herramientas_boceto.py:3088` |
| Curva isoparamétrica | `isoparametric_curve` | `api/herramientas_boceto3d.py:596`; núcleo `nucleo/curvas3d.py:265` |

Fuera de la tarjeta, en la cinta, están los dos comandos de boceto 3D que replican otros dos diálogos de Fusion:
`sk_proyectar_superficie` (`project_to_surface`) y `sk_curva_interseccion` (`intersect_curves`), en
`ui/comandos/proyectar_boceto.py`. No son parte de los 5 tipos, pero comparten `aristas_de_origen`
(`timeline/operaciones.py:1029`) y se cubren acá porque el pedido los nombra.

## Opciones según Fusion (`scripts/fusion_docs.py ver …`)

Búsquedas: `project geometry onto a sketch plane`, `reference project dialog` (`project-reference`),
`reference intersect dialog`, `include 3d geometry`, `project the spun profile of geometry`,
`isoparametric curve`.

### 1. Proyectar (Project)

Fusion (`project-reference-cc9ffb559f9.md`):
- **Geometry**: cuerpos, caras, aristas o puntos a proyectar.
- **Selection Filter**: *Specified Entities* (caras, aristas, puntos) o *Bodies* (cuerpos enteros).
- **Projection Link**: con tilde, asociativo; sin tilde, congelado.

OmniCAD: `filtro_proyectar` = `entidades` / `cuerpos` (equivalente), `vinculo_proyeccion` (equivalente). Extra:
`references` acepta planos, ejes y puntos de trabajo y curvas/puntos de otro boceto (`project_to_sketch`, argumento
`references`). Con filtro Cuerpos, Fusion da perfiles cerrados listos para extruir; OmniCAD hace lo mismo con
`silueta_forma` (B-119).

### 2. Intersecar (Intersect)

Fusion (`reference-intersect-dialog-d412d5704c3.md`):
- **Geometry**: objeto a intersecar con el plano del boceto.
- **Selection Filter**: *Specified entities* (caras y aristas) o *Bodies*.

OmniCAD: mismas dos opciones (`filtro_proyectar`) y además `vinculo_proyeccion`; el diálogo de Fusion no documenta
un Projection Link para Intersect (la geometría de intersección queda asociativa). Decisión a confirmar con Gerardo:
la tarjeta de OmniCAD sí ofrece el vínculo para Intersecar.

### 3. Incluir geometría 3D (Include 3D Geometry)

Fusion (`include-3d-geometry-6a3576fee0a.md`): **Objects to include** = caras, aristas y puntos; sin filtro ni
casilla de vínculo en el artículo (la geometría incluida es asociativa, violeta).

OmniCAD: `edges`, `faces`, `vertices` (por coordenadas, a 0,001 mm) y `link` (true por defecto). Extra respecto de
Fusion: poder apagarlo.

### 4. Perfil giratorio (Spun Profile)

Fusion (`project-the-spun-profile-of-geometry-1c6b2f7ff87.md`):
- **Selection Filter**: *Specified Entities* (caras, aristas, puntos) o *Bodies*.
- **Projection Link** (opcional).
- **Axis** (se elige en el lienzo).
- **Project Axis** (opcional).
- **Tolerance** (mm entre la geometría y el perfil).
- **Flip** (opcional).

OmniCAD: `axis`, `edges`/`faces`/`bodies`/`vertices`, `tolerance` (0,001–10 mm en la paleta), `flip`,
`link`, `project_axis`, `outer_contour` (Solo contorno exterior, extra: Fusion no lo documenta) y `construction`.
El eje admite X/Y/Z, eje de construcción, arista recta, línea de boceto o cara cilíndrica.

### 5. Curva isoparamétrica (Isoparametric Curve)

Fusion (`isoparametric-curve-4089a59d7f6.md`):
- **Face** y **Point** sobre la cara.
- **Direction**: U, V o Both.
- **Type**: Single o Distributed; con Distributed, **Distance** o **Quantity**.
- **Projection Link** (opcional).
- **Manage Lost Projections** para re-vincular (Re-Link, Break Link, Delete Geometry).

OmniCAD: `face`, `point`, `direction`, `type`, `distance` / `quantity` (tope 200), `link`; la edición posterior es
`edit_isoparametric_curve` (BOC-76) y el re-vínculo, `manage_lost_projections`.

## Cobertura de tests que ya existía (grep en `clon/tests`)

| Tipo | Tests |
|---|---|
| Proyectar | `test_proyeccion_seccion.py:61` (cuerpo curvo, guardar, deshacer), `:207`/`:214` (plano desplazado e inclinado), `:227` (vértice y arista); `test_proyectar_tarjeta.py` (tarjeta, filtros, vínculo, B-119, undo/redo, guardar/reabrir); `test_b393_proyectar_superficie.py`; `test_b619_silueta_revolucion.py` (barril) |
| Intersecar | `test_api_boceto_herramientas.py:526` (`mode="intersect"`, incluido el INVALID_GEOMETRY cuando el plano no corta); `test_proyectar_tarjeta.py:739` (la tarjeta sigue cortando y no proyecta); `test_b619_silueta_revolucion.py:66` (corte por el eje) |
| Incluir 3D | `test_proyeccion_seccion.py:101` (aristas donde están, sigue al modelo, vértice 3D), `:232` (H-79, el vértice sigue al cuerpo); `test_faltantes_bocetos.py:68-100` (aristas + vértices, caras, `link=false`, pedido vacío); `test_proyectar_tarjeta.py:642` (clic deja curva 3D vinculada) |
| Perfil giratorio | `test_proyeccion_seccion.py:87` (cilindro: área 300 y perfil que cierra con el eje); `test_boceto_fase6.py:345` (sigue al modelo, `flip`, sin vínculo) y `:366` (errores: sin nada que girar, sin cuerpos, tolerancia 0); `test_boceto_fase9_nucleo.py:139-180` (solo contorno exterior, `project_axis`, re-vínculo) |
| Isoparamétrica | `test_isoparametrica.py` (U/V/Both, Single/Distributed por distancia y cantidad, recorte por agujero, validaciones, vínculo, edición, undo); `test_isoparametrica_ui.py` (previa, errores, cinta) |

## Huecos y tests nuevos (`clon/tests/test_prep_proyectar_cobertura.py`)

Ninguno de estos estaba cubierto; todos son de valores raros pedidos (vacío, 0, negativos, cuerpo oculto):

1. `project_to_surface` con `faces=[]` → `INVALID_ARGUMENTS`.
2. `project_to_surface` con `direction=[0, 0, 0]` → `INVALID_ARGUMENTS` (vector nulo).
3. `intersect_curves` sin nada elegido → `INVALID_ARGUMENTS`.
4. `intersect_curves` con una cara cilíndrica como `references` (no plana) → `INVALID_ARGUMENTS`.
5. `include_3d_geometry` con un vértice a 999 mm de todo → `ELEMENT_NOT_FOUND` y el boceto no cambia.
6. `project_spun_profile` con `tolerance=-1` → `INVALID_ARGUMENTS`.
7. `isoparametric_curve` con `quantity=201` (tope 200) → `INVALID_GEOMETRY` y ninguna curva.
8. Cuerpo oculto (ventana): con el cuerpo oculto, un clic donde estaba su cara no agrega referencia a la tarjeta; con
   el cuerpo visible, el mismo clic sí agrega una.

## Hallazgos

- Los 8 tests pasan: las validaciones de los 5 tipos ya rechazan vacío, cero, negativos y el tope de isoparamétricas.
  No se abrió ningún bug nuevo.
- Un cuerpo oculto no se puede elegir con el clic (el visor no lo dibuja ni lo deja seleccionar), pero la API sí lo
  proyecta si se lo nombra (`project_to_sketch(bodies=[…])`): se dejó como comportamiento actual, sin fila de bug,
  porque Fusion tampoco permite elegirlo a mano y la API no documenta el caso.
- Sigue abierto lo de B-619: **B-619b** (Incluir 3D e isoparamétrica del barril dan splines de 33 polos donde el
  perfil tiene 5) y **B-619c** (Perfil giratorio del barril da 23 rectas). No se duplicó la fila.
