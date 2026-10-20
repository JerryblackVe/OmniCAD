# Brechas MCP: lo que la app hace y un agente no puede

> Este archivo es la especificación. Lo que falta de cada ID está en [docs/seguimiento/](seguimiento/README.md); si un ID no figura allá, ya está resuelto. Si algo de acá no coincide con el seguimiento, vale el seguimiento.

Fecha: 2026-10-18. Origen: bug B-80. Pedido del usuario: un agente que quería animar el motor no tenía herramientas para el
espacio ANIMACIÓN. Regla que se rompe: `CLAUDE.md` › «MCP y CLI siempre completos».

Base al escribir (2026-10-18): 190 herramientas en 13 grupos y 95 tipos de operación. Hoy son 211 herramientas en 14 grupos (`docs/agentes/herramientas.md`) y 96 tipos de operación; la ola 1 ya está hecha. Se revisaron 4 zonas, cada una contra el catálogo
(`api/registro.py` › `_CATALOGO`): la cinta DISEÑO con sus comandos, DIBUJO, RENDERIZAR con ANIMACIÓN, y los paneles y
menús. Cada fila cita el archivo y la línea leídos. Rutas relativas a `clon/omnicad/`.

## Resumen

> Medición del 2026-10-18. ANIMACIÓN (ola 1) quedó hecha el 2026-10-20.

| Zona | Funciones sin herramienta | Qué tan difícil | Por qué |
|---|---|---|---|
| ANIMACIÓN | 14 (todo el espacio) | alta | La lógica está dentro de un módulo con Qt. Hay que sacarla a `nucleo/animacion.py` antes. |
| DIBUJO | 20 (todo el espacio) | baja | `nucleo/dibujo.py` ya existe y no usa Qt. Solo el PDF depende de Qt. |
| RENDERIZAR | 9 (todo salvo Aspecto) | baja a media | `nucleo/render_cpu.py` ya renderiza sin ventana. La lista de entornos está en Qt. |
| Cinta DISEÑO: sin ninguna herramienta | 31 claves (de 236) | baja a media | Análisis, configuraciones, Calcular todo, espiral, restricción Polígono. |
| Cinta DISEÑO: solo con `run_operation` | 54 claves (38 tipos de op) | baja | La operación ya existe. Falta la herramienta con nombre propio. |
| Opciones de diálogo que la herramienta no acepta (ola 7) | 101 opciones (MCP-56 a MCP-90) | baja a media | El comando tiene herramienta, pero le faltan parámetros. |
| Visor, navegador, paneles, preferencias | 18 | baja a alta | Las que cambian lo que ve `get_viewport_image` (estilo, corte) son altas. |

## Antes de crear herramientas (requisitos)

| ID | Requisito | Evidencia |
|---|---|---|
| MCP-0a | **Test de cobertura UI → API.** Debe fallar si una clave de la cinta, o un ítem de DIBUJO, RENDER o ANIMACIÓN, no tiene herramienta ni una excusa escrita. Sin este test, el hueco vuelve a abrirse. | **Hecho:** `tests/test_cobertura_ui_api.py::test_cada_clave_tiene_herramienta_o_excusa`. Antes `tests/test_api_catalogo.py` solo validaba esquemas. |
| MCP-0b | **`doc.espacios` dentro de la transacción y del deshacer.** Hoy, si una herramienta escribe ahí y después falla, el cambio no se revierte. | **Hecho:** `api/sesion.py` restaura los espacios en la transacción y en el deshacer (`tests/test_api_animacion.py::test_una_herramienta_que_falla_deja_los_espacios_iguales`). Antes restauraba solo si se agregaba un paso de deshacer (`sesion.py:140`). |
| MCP-0c | **La ventana tiene que releer lo que escribe una herramienta.** Con la app abierta, la copia de la ventana pisa lo que haya escrito una herramienta. Pasa con guiones, dibujo y escena de render. | **Hecho:** el callback está en `ui/puente.py` y la ventana relee con `releer_espacios` (`ui/ventana.py`; `tests/test_api_animacion.py::test_la_transaccion_avisa_cambio_de_espacios`). Antes: `ui/animacion.py:1045` (`self.guiones`), `ui/ventana.py:1131-1164` (`_guardar_espacio`). |
| MCP-0d | **Extraer `nucleo/animacion.py`.** `Guion`, `evaluar`, `invertir`, explosión y GIF no usan Qt, pero viven en un módulo que sí la importa. | **Hecho:** `nucleo/animacion.py` existe y no importa Qt. Antes: `ui/animacion.py:40-51` y `:133` (`centros_de` importa `ui.visor3d`). |
| MCP-0e | **Pasar `ENTORNOS` a `nucleo/`.** | **Hecho:** `ENTORNOS` vive en `nucleo/render_cpu.py` y `ui/visor3d.py` lo reexporta. Antes: `ui/visor3d.py:82`, `ui/render.py:65` (`cielo_de`). |

## Ola 1: ANIMACIÓN (cierra B-80) — HECHA el 2026-10-20 (MCP-1 a MCP-10 y MCP-86)

Datos: `doc.espacios["animacion"]` = `{version, actual, guiones[]}` (`ui/animacion.py:1525`; formato en `:14-27`).

| ID | Herramienta | Función en la interfaz | Dónde | Dificultad |
|---|---|---|---|---|
| MCP-1 (hecho) | `create_storyboard` | Nuevo guion (limpio o desde el final) | `ui/animacion.py:1397`, `:318` | media |
| MCP-2 (hecho) | `list_storyboards`, `get_storyboard` | Elegir guion, duración | `:1418`, `:205` | baja |
| MCP-3 (hecho) | `rename_storyboard`, `copy_storyboard`, `delete_storyboard`, `reverse_storyboard` | Renombrar, copiar, eliminar, invertir | `:1425`, `:1433`, `:1446`, `:1440` | baja (invertir: media) |
| MCP-4 (hecho) | `add_animation_action` (`type`: transform, restore, visibility) | Transformar (mover XYZ en mm, girar XYZ en grados), restaurar, mostrar/ocultar | `:1278`, `:851-860`, `:286`, `:301` | media |
| MCP-5 (hecho) | `edit_animation_action`, `delete_animation_action` | Editar, mover o estirar barras, borrar | `:1303`, `:1320`, `:1327` | baja |
| MCP-6 (hecho) | `auto_explode` | Explosión automática (un nivel o todos, escala, secuencial) | `:1258-1262`, `:145`, `:167` | media |
| MCP-7 (hecho) | `set_animation_camera` | VISTA: guardar la cámara | `:1299`, `:1110` | baja |
| MCP-8 (hecho) | `add_animation_annotation` | ANOTACIÓN | `:1341` | media |
| MCP-9 (hecho) | `get_animation_frame` | Reproducir o ir a un tiempo: estado y una imagen del cuadro | `:1162-1230` | media |
| MCP-10 (hecho) | `export_animation_video` | PUBLICAR (GIF o PNG, resolución, fps, bucle) | `:1466`, `:929-1019` | alta: hay que cambiar `LienzoRender` (`:1501`) por `rc.renderizar` |

## Ola 2: DIBUJO (planos 2D)

Datos: `doc.espacios["dibujo"]` (`timeline/documento.py:136`, guardado en `:661`, restaurado en `:687`). Modelo sin Qt:
`nucleo/dibujo.py` (`Vista` en 916, `Dibujo` en 981, `proyectar` en 331). Ya se usa sin ventana: `tests/test_dibujo.py:34`.

| ID | Herramienta | Función en la interfaz | Dónde (UI · núcleo) | Dificultad |
|---|---|---|---|---|
| MCP-11 | `create_drawing`, `get_drawing` | Abrir o crear el plano y consultarlo (vistas, anotaciones, valores de cota) | `ui/ventana.py:1131` · `nucleo/dibujo.py:1515`, `:1676` | baja |
| MCP-12 | `set_drawing_sheet` | Hoja y cajetín (norma, tamaño, orientación, método, campos) | `ui/dibujo.py:1355`, `:1724` · `:984` | baja |
| MCP-13 | `add_drawing_view` (`type`: base, projected, section, detail) | Vista base, proyectada, de sección y de detalle | `ui/dibujo.py:740`, `:784`, `:813`, `:875` · `:1177-1228` | baja (sección: media) |
| MCP-14 | `edit_drawing_view` | Propiedades (estilo, escala, tangentes, nombre) y girar | `ui/dibujo.py:1696-1703`, `:1254` · `:1241`, `:1413` | baja |
| MCP-15 | `move_drawing_element`, `delete_drawing_element` | Mover y borrar | `ui/dibujo.py:638`, `:1245` · `:1394`, `:1418` | baja |
| MCP-16 | `add_drawing_dimension` (`subtype`: linear, aligned, radius, diameter, angle, ordinate) | Cotas | `ui/dibujo.py:918`, `:1042`, `:1059`, `:1087` · `:1267` | media: las cotas van en coordenadas 2D de la vista. Hay que enganchar al punto más cercano. |
| MCP-17 | `add_drawing_centerline`, `add_drawing_center_mark` | Línea y marca de centro | `ui/dibujo.py:1208`, `:1235` · `:1320`, `:1326` | baja |
| MCP-18 | `add_drawing_text`, `add_drawing_note`, `add_drawing_balloon`, `add_drawing_table` | Texto, nota con directriz, globo, tabla de piezas | `ui/dibujo.py:1129`, `:1139`, `:1177`, `:1166` · `:1289-1348` | baja. La tabla no debe duplicar `get_bill_of_materials`. |
| MCP-19 | `edit_drawing_annotation` | Editar el texto de una cota, nota o globo | `ui/dibujo.py:1705-1716` | baja |
| MCP-20 | `export_drawing` (`format`: dxf, svg, pdf) | Exportar DXF, SVG, PDF | `ui/dibujo.py:1762`, `:1766`, `:1740` | DXF y SVG: baja (`io_archivos/dxf.py:453`, `svg_salida.py:145`). PDF: alta, usa `QPdfWriter`. |
| MCP-21 | `get_drawing_image` | Ver la hoja como imagen | `ui/dibujo.py:57` (`Pintura`) | alta |

Nota: el deshacer del dibujo vive en la ventana (`ui/dibujo.py:1629-1670`). Las herramientas de esta ola dependen de MCP-0b.

## Ola 3: RENDERIZAR

Datos: `doc.espacios["render"]` = `{version, escena, camara, lienzo}` (`ui/render.py:2194`). Sin Qt:
`nucleo/render_cpu.py` (`ESCENA_DEFECTO` en 142, `escena_normalizada` en 160, `renderizar` en 897, `guardar_png` en 942).
Hoy `get_viewport_image` llama siempre a `escena_normalizada(None)` (`api/herramientas_inspeccion.py:152`): ignora la
escena del documento.

| ID | Herramienta | Función en la interfaz | Dónde | Dificultad |
|---|---|---|---|---|
| MCP-22 | `get_render_scene`, `set_render_scene` | Entorno, brillo, giro, exposición, fondo, suelo, reflejos, rugosidad, sombras, cámara orto/persp y focal, oclusión ambiental, opciones del lienzo | `ui/render.py:1371-1414`, `:2081` | baja |
| MCP-23 | `list_render_environments` | Biblioteca de entornos | `ui/render.py:1414`; `ui/visor3d.py:82` | media (MCP-0e) |
| MCP-24 | `set_render_camera` | Cámara guardada del render | `ui/render.py:529`, `:2197` | baja |
| MCP-25 | `render_image` | Renderizar y Capturar imagen (presets, calidad 1× a 3×, fondo transparente, PNG) usando la escena del documento | `ui/render.py:2100-2111` | media. La CPU no dibuja calcomanías (B-75). |

Aspecto (`ui/render.py:1996`, `:2021`) ya está cubierto por `set_appearance`, `edit_appearance`, `manage_appearance` y
`list_appearances`.

## Ola 4: cinta DISEÑO sin ninguna herramienta

| ID | Herramienta | Claves | Qué hace hoy | Dificultad |
|---|---|---|---|---|
| MCP-26 | `manage_analysis`, `analyze_geometry` | `seccion`, `cebra`, `mapa_entorno`, `angulo_desmoldeo`, `mapa_curvatura`, `curvatura_peine`, `isocurva`, `accesibilidad`, `radio_minimo` | Guarda el análisis en `doc.analisis` y lo pinta en el visor (`ui/comandos/inspeccionar.py:291-450`, `ui/analisis_vista.py:50`) | media. La parte numérica es pura (`nucleo/analisis.py`). Dibujarla en la imagen es alta. |
| MCP-27 | `manage_configurations` | `configurar`, `mostrar_configuracion` | Tabla de variantes (`ui/ventana.py:1173`, `ui/administrar.py:123`, `timeline/documento.py:373`) | media |
| MCP-28 (hecho) | `recompute_all` | `calcular` | `doc.recalcular(0)` (`ui/ventana.py:2023`). La herramienta ya existe (`api/herramientas_documento.py`; `tests/test_rendimiento_arreglos.py`). | baja |
| MCP-29 | `draw_spiral` | `sk_espiral` | Espiral en el editor (`ui/editor_boceto.py:894`) | baja: sacar la cuenta a una función pura |
| MCP-30 | `add_constraint(type="polygon")` | `sk_r_poligono` | `ui/editor_boceto.py:123`, `restricciones/boceto.py:1583` | baja |
| MCP-31 | Opción `component_colors` en `get_viewport_image` | `colores_componente` | `ui/ventana.py:1275` | media |

No necesitan herramienta, porque un agente elige por id y no por clic: modos, filtros y prioridad de selección
(`ui/ventana.py:1313-1336`), Terminar boceto y Activar patrón plano. Ya están cubiertos por `get_viewport_image(bodies=…)`.

Huecos parciales, que se pueden armar con otras herramientas: `draw_rectangle` no hace rectángulos rotados
(`sk_rectangulo_3p`, MCP-74), `draw_arc` no tiene la forma tangente (MCP-94), y a `select_bodies` le faltan `by_name`, `by_size` e `invert` (MCP-93; no son MCP-50, que es `get_selection`).

## Ola 5: cinta DISEÑO solo con `run_operation`

La operación existe y funciona por `run_operation`. Falta la herramienta con nombre propio. Eran 38 tipos de 95 el 2026-10-18 (hoy hay 96 tipos; no se recontaron los que no tienen herramienta).

| ID | Herramientas propuestas | Tipos de operación |
|---|---|---|
| MCP-32 | `create_coil`, `create_pipe` | `bobina`, `tuberia` |
| MCP-33 | `create_rib`, `create_web`, `create_emboss`, `create_boss`, `create_lip_groove` | `nervio`, `red`, `repujado`, `saliente`, `labio` |
| MCP-34 | `create_boundary_fill`, `create_bounding_solid`, `thicken` | `relleno_contorno`, `solido_envolvente`, `engrosar` |
| MCP-35 | `create_surface_extrude`, `create_surface_revolve`, `create_surface_sweep`, `create_surface_loft`, `offset_surface`, `fillet_surface`, `create_patch`, `create_ruled_surface` | `sup_*` (6), `parche`, `reglada` |
| MCP-36 | `extend_surface`, `trim_surface`, `untrim_surface`, `stitch_surfaces`, `unstitch_surfaces`, `reverse_surface_normal` | `extender_sup`, `recortar_sup`, `destrimar`, `coser`, `descoser`, `invertir_normal` |
| MCP-37 | `align_bodies`, `scale_body` | `alinear`, `escala` (hoy solo existe `scale_mesh`) |
| MCP-38 | `split_face`, `split_body`, `silhouette_split`, `replace_face`, `remove_bodies`, `delete_faces` | `dividir_cara`, `dividir_cuerpo`, `division_silueta`, `reemplazar_cara`, `quitar`, `borrar_caras` |
| MCP-39 | Agregar `type` a `create_construction_plane` (ángulo, tangente, medio, perpendicular, dos aristas, tres puntos, en ruta) | `plano` (hoy solo desfase: `api/herramientas_boceto.py:640`) |
| MCP-40 | `create_construction_axis`, `create_construction_point`, `create_ucs` | `eje` (5 variantes), `punto` (6), `scu` |
| MCP-41 | `insert_fastener`, `insert_canvas`, `create_base_feature` | `fijacion`, `lienzo` (`set_decal` lo rechaza), `operacion_base` |

## Ola 6: visor, navegador, paneles y preferencias

| ID | Herramienta | Función en la interfaz | Dónde | Dificultad |
|---|---|---|---|---|
| MCP-42 | `set_view` (y `camera` en `get_viewport_image`) | Vistas estándar, órbita, Ajustar, Mirar a, cámara orto/persp | `ui/visor3d.py:693-756`, `ui/superposiciones.py:337-345` | baja: `rc.camara(ortografica=)` ya existe (`nucleo/render_cpu.py:418`) |
| MCP-43 | `manage_named_views` (y `view="<nombre>"` en la imagen) | Vistas guardadas | `ui/ventana.py:1993-2021` | baja |
| MCP-44 | `set_visual_style` | 6 estilos visuales, entorno, efectos, colores de componente | `ui/superposiciones.py:280-323`, `ui/visor3d.py:70` | media en vivo. En la imagen es alta: la CPU no tiene alámbrico. |
| MCP-45 | `section_view` | Análisis de sección en la vista | `ui/analisis_vista.py:61-78` | alta en la imagen: la CPU no corta con planos |
| MCP-46 | `capture_viewport` | Capturar la ventana real (estilo, corte, bocetos) | `ui/ventana.py:2391`, `ui/visor3d.py:2192` | media: necesita un callback en el puente |
| MCP-47 | `set_object_visibility`, y ampliar `set_browser_visibility` | Planos, ejes, origen, componentes, bocetos, análisis | `ui/superposiciones.py:324-336`, `ui/ventana.py:1279-1291` | baja |
| MCP-48 | `set_body_opacity`, `isolate_bodies` | Control de opacidad, Aislar | `ui/ventana.py:1706-1715` | baja. La imagen ya lee la opacidad (`api/herramientas_inspeccion.py:73`). |
| MCP-49 | `set_grid` | Rejilla, forzar a la rejilla, 4 vistas | `ui/superposiciones.py:356-380` | baja |
| MCP-50 | `get_selection`, `select_entities` | Leer la selección del usuario; elegir caras, aristas o perfiles | `ui/ventana.py:1390-1425` | baja / media |
| MCP-51 | `manage_comments` | Comentarios | `ui/comentarios.py:56-83`, `timeline/documento.py:642-652` | baja |
| MCP-52 | `list_recent_documents` | Proyectos recientes | `ui/panel_datos.py:93-114` | baja |
| MCP-53 | `set_flat_pattern_view` | Activar o terminar el patrón plano | `ui/ventana.py:1968` | baja |
| MCP-54 | `get_preferences`, `set_preference` (con lista blanca) | Cámara, órbita, gráficos, teselado, autoguardado | `ui/preferencias.py:160-221` | media. Nunca `puente_agentes` ni `puente_codigo`: un agente no debe darse permisos solo (`:180-182`). |
| MCP-55 | Ampliar `sketch_view` | Paleta del boceto: rejilla, forzar, corte, puntos, restricciones | `ui/modo_boceto.py:135-139` | baja |
| MCP-93 | Ampliar `select_bodies` | Opciones `invert`, `by_name` y `by_size` (claves de cinta `invertir_seleccion`, `seleccion_nombre`, `seleccion_tamano`). No es MCP-50 | `ui/ventana.py:420-421` | baja |

Se descartan porque no le sirven a un agente: tema, paneles, pantalla completa, atajos, caja de herramientas, menú
radial, sugerencias, búsqueda de comandos, manipuladores, opciones del ratón y del ViewCube, ayuda.

## Ola 7: opciones de diálogo que la herramienta no tiene (segunda pasada, 2026-10-18)

La primera pasada miró si cada comando tenía herramienta. Esta mira **opción por opción**: el comando tiene herramienta,
pero al diálogo le sobran opciones que la herramienta no acepta. `run_operation` y `edit_feature` no cuentan como
cubierta. Se confirmó que nada de las olas 1 a 6 se agregó desde la primera pasada (seguían siendo 190 herramientas el 2026-10-18; hoy son 211).

### Sólido: 83 opciones en 22 comandos

| ID | Herramienta a ampliar | Opciones que faltan | Dónde (UI) | Dificultad |
|---|---|---|---|---|
| MCP-56 | `extrude` | Extrusión delgada (espesor, ubicación de pared); inicio en desfase o en objeto; media longitud; extensión «al objeto» y «todo» con cara/cuerpo/a través y desfase; conicidad propia del lado 2; cara plana o curva abierta como perfil | `ui/comandos/solido.py:29-51` | media |
| MCP-57 | `revolve` | Eje = eje de construcción, arista recta, cara cilíndrica o línea de otro boceto; cara plana como perfil | `ui/comandos/solido.py:135-136` | baja |
| MCP-58 | `sweep` | Tipo ruta + carril guía, carril, escala del perfil, distancia parcial de la ruta, cara plana como perfil, aristas de cuerpo como ruta | `ui/comandos/crear.py:39-45` | media |
| MCP-59 | `loft` | Tipo de guía, carriles, línea central; caras, aristas, vértices o puntos como perfiles | `ui/comandos/crear.py:71-75` | media |
| MCP-60 | `create_hole` | Ubicar en vértice o punto de construcción (asociativo), ángulo de la punta (hoy fijo 118°), invertir dirección en todas las ubicaciones (`flip` existe, pero solo con `sketch_points`), varios cuerpos | `ui/comandos/crear.py:325-367` | baja |
| MCP-61 | `rectangular_pattern`, `circular_pattern`, `path_pattern`, `point_pattern`, `multi_transform` | **Parcial:** `path_pattern` ya tiene distribución por extensión (`spacing_mode`), simétrico y ruta por curvas (`path_curves`, desde 2026-10-10). Sigue pendiente: dirección o eje = arista, eje de construcción, plano o cara (`rectangular_pattern` acepta solo x/y/z); distribución por extensión o ángulo entre copias y simétrico en los demás patrones; suprimir copias; ruta = aristas de cuerpo; puntos sueltos, vértices o puntos de construcción; punto de referencia asociativo; plano de simetría = cara | `ui/comandos/crear.py:720-746`, `ui/comandos/patrones.py:60-66` | media |
| MCP-62 | `mirror` | Cara plana como plano de simetría | `ui/comandos/crear.py:805` | baja |
| MCP-63 | `fillet` | Empalme de reglas (caras A/B, regla, topología), radio variable (radio final), por cuerda (longitud), cadena tangente | `ui/comandos/modificar.py:74-92` | media |
| MCP-64 | `chamfer` | Dos distancias, distancia y ángulo, voltear, cadena tangente | `ui/comandos/modificar.py:127-133` | baja |
| MCP-65 | `shell` | Cadena tangente, espesor exterior distinto del interior, esquinas afiladas o redondeadas | `ui/comandos/modificar.py:150-165` | baja |
| MCP-66 | `draft` | Plano fijo = plano de construcción, dos lados o simétrico, ángulo 2 | `ui/comandos/modificar.py:201-206` | baja |
| MCP-67 | `offset_edges` | Plano opcional = plano de construcción | `ui/comandos/modificar.py:336` | baja |
| MCP-68 | `move_body` | Tipo de movimiento (hoy siempre libre): trasladar por dirección y distancia, girar alrededor de eje o arista con ángulo, punto a punto (origen y destino); pivote en vértice o punto | `ui/comandos/modificar.py:472-492` | baja |
| MCP-69 | `remove_fillets` | Varios cuerpos (hoy uno) | `ui/comandos/modificar.py:727` | baja |
| MCP-70 | `create_construction_plane` | Cara plana como base del desfase (se suma a MCP-39) | `ui/comandos/construir.py:16` | baja |
| MCP-71 | `create_gear`, `create_gear_pair`, `create_rack`, `create_sprocket`, `create_shaft` | Plano = cara plana; centro o comienzo = punto o vértice asociativo (hoy solo [x, y]) | `ui/comandos/engranaje.py:88-89`, `:181-182` | baja |

100 % cubiertos: caja, cilindro, esfera, toroide, rosca, combinar, apoyar y desfase de cara.

### Boceto: 9 opciones

| ID | Herramienta a ampliar | Opciones que faltan | Dónde (UI) | Dificultad |
|---|---|---|---|---|
| MCP-72 | `draw_circle` | Círculo por 2 puntos (diámetro) y por 3 puntos | `ui/editor_boceto.py:964-979` | baja |
| MCP-73 | `create_polygon` | Polígono por arista (`kind="edge"`) | `ui/editor_boceto.py:1026-1037` | baja |
| MCP-74 | `draw_line`, `draw_rectangle` | Línea de punto medio con su restricción; rectángulo central con diagonales de construcción y punto central | `ui/editor_boceto.py:921-953` | baja |
| MCP-75 | `project_to_sketch` | Proyectar, intersecar e incluir **vértices** del modelo (`mode="intersect"` ya existe para aristas, caras y cuerpos; faltan los vértices) | `ui/editor_boceto.py:1361-1366` | baja |
| MCP-76 | `edit_dimension` o nueva | Cambiar el radio de un círculo libre sin agregar cota (lo que hace arrastrarlo) | `ui/editor_boceto.py:2847-2899` | baja |
| MCP-77 | `sketch_view` | Acción «terminar» (salir del editor en vivo y guardar el boceto) | `ui/modo_boceto.py:679` | baja |
| MCP-78 | `redefine_sketch_plane` (nueva) | Redefinir el plano de un boceto sobre una cara, sin pasar `marco` y `cara` internos por `edit_feature` | `ui/acciones_navegador.py:193`, `ui/ventana.py:2065-2068` | baja |
| MCP-91 | `extend_sketch_curve` (nueva, nombre propuesto) | Alargar curvas del boceto (clave de cinta `sk_alargar`, Shift+V); sin herramienta hoy | `ui/cinta_boceto.py:37`, `ui/modo_boceto.py:69` | baja |
| MCP-92 | `split_sketch_curve` (nueva, nombre propuesto) | Partir curvas del boceto (clave de cinta `sk_partir`); sin herramienta hoy | `ui/cinta_boceto.py:38`, `ui/modo_boceto.py:70` | baja |
| MCP-94 | `draw_arc` | Forma tangente (clave de cinta `sk_arco_tangente`) | `ui/modo_boceto.py:38` | baja |

### Inspección, parámetros, archivo y espacios: 12 opciones

| ID | Herramienta | Opciones que faltan | Dónde (UI) | Dificultad |
|---|---|---|---|---|
| MCP-79 | `measure_distance` | Centro a centro | `ui/comandos/inspeccionar.py:61` | baja |
| MCP-80 | `check_interference` | Incluir caras coincidentes | `ui/comandos/inspeccionar.py:210` | baja |
| MCP-81 | `create_parameter`, `set_parameter` | Parámetro sin unidad (cantidades de patrón); renombrar; comentario | `ui/dialogos.py:182-183` | baja |
| MCP-82 | `export_parameters`, `import_parameters` (nuevas) | CSV de parámetros, formato de Fusion | `ui/dialogos.py:207-270` | baja |
| MCP-83 | `get_bill_of_materials` | **Hecho (2026-10-10):** exporta a CSV con `csv_path` (`api/herramientas_material.py`, `tests/test_api_material.py`) | `ui/administrar.py:95-120` | baja |
| MCP-84 | `new_document` | Abrir el modelo de ejemplo | `ui/ventana.py:336`, `:2428` | baja |
| MCP-85 | MCP-13 y MCP-14 (DIBUJO) | Marcas y líneas de centro automáticas de la vista | `ui/dibujo.py:1313`, `:1357` | baja |
| MCP-86 | MCP-10 (ANIMACIÓN) | **Hecho** (ola 1, `3ae4f74`): publica todos los guiones (`all_storyboards`) con el estilo de render (`rc.renderizar`) | `ui/animacion.py:939-968` | baja |
| MCP-87 | `export` o `export_mesh` | **Hecho (2026-10-19):** `export_mesh` (`api/herramientas_guardar_malla.py`) cubre el diálogo «Guardar como malla» de Fusion (refinado, STL ASCII, unidad, un archivo por cuerpo) | `ui/ventana.py:2363` | media |

### Chapa, superficie, malla, ensamble, insertar, aspecto y revisión

| ID | Herramienta | Opciones que faltan | Dónde (UI) | Dificultad |
|---|---|---|---|---|
| MCP-88 | `plane_cut_mesh` | Cara plana como plano de corte | `ui/comandos/malla.py:133` | baja |
| MCP-89 | `create_joint`, `create_as_built_joint`, `create_joint_origin` | Origen de la unión en un vértice o en una curva de boceto (hoy solo cara, arista o construcción) | `ui/comandos/ensamblar.py:11`, `:86`, `:91`, `:131` | baja |
| MCP-90 | `rip` | Punto de construcción como punto del desgarro | `ui/comandos/chapa.py:476` | baja |

100 % cubiertos: toda la chapa salvo el desgarro, toda la malla salvo el corte, nuevo componente, grupo rígido,
accionar uniones, vínculo de movimiento, fijar componente, insertar DXF/SVG, vectorizar, calcomanía, aspecto, material,
centro de masa, revisar y reparar. Las superficies ya estaban en la ola 5.
Nota: `insert_svg`, `insert_dxf` y `trace_image` piden números y no aceptan expresiones con parámetros, como sí hace
la UI. No se cuenta como faltante, porque el boceto queda con los mismos valores calculados.

Se descartan, porque no le sirven a un agente:
- Secuencias de comandos: las cubre `execute_code`.
- Biblioteca de roscas: la cubre `thread_info`.
- Galería de renders: la cubre MCP-25.
- Precisión y ceros de las unidades: solo cambian lo que se ve en pantalla.
- Reproducir el timeline, Repetir último comando, Buscar en navegador, ventana o timeline, y Acerca de.

## Hallazgos de la auditoría

| Hallazgo | Estado |
|---|---|
| B-81: el menú del cuerpo en el navegador reusaba el del grupo. La opacidad no se podía cambiar desde ningún lado, y Mover/copiar, Aspecto, Material, Aislar, Quitar y Buscar en el timeline quedaron como código muerto (`ui/navegador.py:368-413`). | Corregido el 2026-10-18 |
| B-82: lo que oculta `set_browser_visibility` no se guarda. `self.ocultos` se vacía al abrir un documento (`ui/ventana.py:876`). | Corregido el 2026-10-19 (`tests/test_p23_navegador.py::test_cuerpo_oculto_persiste_al_guardar_y_reabrir`) |
| El menú del boceto (P23e, 19 opciones de Fusion) ya no ofrece «Guardar como SVG» ni «Limpiar geometría». Los manejadores siguen en `ui/ventana.py:1726-1729`. Las herramientas `export_sketch` y `clean_sketch` existen. | Lo decide el usuario: agregarlos rompe la lista exacta de Fusion |
| `docs/plan_mcp_cli.md:286` decía «93 tipos sin herramienta propia» y 167 herramientas. | Corregido el 2026-10-18: 38 de 95 y 190. Hoy: 211 herramientas y 96 tipos |

## Orden sugerido

1. MCP-0a a MCP-0e (requisitos). Sin ellos, las herramientas nuevas se pisan con la ventana abierta.
2. Ola 1, ANIMACIÓN: cierra B-80.
3. Ola 2, DIBUJO, y Ola 3, RENDER: el núcleo ya está, son rápidas.
4. Olas 4 y 6, de lo más barato a lo más caro.
5. Ola 5: son mecánicas y se pueden repartir entre varios agentes.

Cada herramienta sigue la receta C de `AGENTS.md`: un test con resultado numérico y la doc regenerada
(`omnicad tools --markdown --output docs/agentes/herramientas.md`).
