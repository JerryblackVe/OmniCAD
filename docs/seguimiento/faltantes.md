# Faltantes

Funciones que todavía no existen. La especificación de cada ID está en el `docs/brechas_*.md` que nombra cada sección. Método y columnas: [README](README.md).

Solo lo que falta resolver: al resolverse, la fila se borra. Verificado contra el código el 2026-10-20 (secciones Boceto, Superficie y Sólido: 2026-10-24). Total 239: Abierto 155 · Parcial 50 · Bloqueado 30 · Sin verificar 4 (2026-11-10: entraron H-113 y H-114 de los videos de roscas; 2026-11-07: +H-110 de la fase 2 de CREAR y MODIFICAR; H-109 y H-111 ya cerrados).

## Pendientes generales

Abierto 53 · Parcial 3 · Bloqueado 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| P-2d | Selector de idioma en Preferencias y test de cadenas sin traducir | Abierto | Media | Sin selector ni test que falle por cadena sin traducción; AGENTS.md aún exige TODO en español. | omnicad/ui/preferencias.py sin clave de idioma | 2026-10-20 |
| P-8c | Primer arranque guiado dentro de la app (idioma, conectar agentes con un botón) | Abierto | Media | Hoy conectar agentes es una tarea opcional del instalador; la app no tiene asistente de primer arranque. | instalador/windows/omnicad.iss:62,79 (tarea «agentes»); grep de «primer arranque» en omnicad/: sin resultados | 2026-10-20 |
| P-9f | Temas con tipografía propia y fondo con imagen en el visor | Abierto | Media | Los temas solo definen colores; la fuente está fija en el QSS y no hay imagen de fondo. | omnicad/ui/temas.py:208 (font-family fija «Segoe UI») | 2026-10-20 |
| P-12e | Página web del proyecto y GitHub Actions que la actualice con cada versión | Abierto | Media | No existe la página; comparte las Actions por versión con el pendiente 8. | .github/workflows/instaladores.yml (solo instaladores) | 2026-10-20 |
| P-22a | Modo seguro (contador de arranques fallidos) | Abierto | Media | Sin programar. | grep «modo seguro» y «arranques fallidos» en omnicad/: sin resultados | 2026-10-20 |
| P-22b | Diario del solver de bocetos (grabar y reproducir) | Abierto | Media | Sin programar; serviría de corpus para R4. | omnicad/restricciones/ sin diario | 2026-10-20 |
| P-23c3 | c) Grupos anidados (mover un grupo dentro de otro) | Abierto | Media | Opción grisada: sin grupos anidados. | omnicad/ui/acciones_navegador.py | 2026-10-20 |
| P-23e2 | e) Ocultar perfil, Mostrar cota, Ocultar proyectadas y construcción fuera del editor | Abierto | Media | El visor general no dibuja esas cuatro capas; grisadas fuera del editor. | omnicad/ui/acciones_navegador.py:281-288 | 2026-10-20 |
| P-25d | d) SÓLIDO > MODIFICAR: Organizar y Administrar materiales | Abierto | Media | Organizar no existe; Administrar materiales sigue grisado. Simplificar pasó a PLA-9. | omnicad/ui/cinta.py:114 (_i sin clave) | 2026-11-01 |
| P-25f | f) INSPECCIONAR: análisis de pila de fijadores (Fastener Stack Analysis) | Abierto | Media | No existe. No aparece en las capturas de INSPECCIONAR. | docs/brechas_inspeccionar.md | 2026-11-01 |
| P-25h | h) SELECCIONAR: arrastre de componentes (casilla) | Abierto | Media | No existe la casilla. | grep «Arrastre de componentes» en omnicad/ui: sin resultados | 2026-10-20 |
| P-27-13 | Disposición en la cama y abrir directo en el slicer | Abierto | Media | Sin programar. | grep en omnicad/ nucleo/api/timeline: sin función equivalente | 2026-10-20 |
| P-27-14 | Vista en realidad aumentada con código QR | Abierto | Media | Sin programar. | grep en omnicad/ nucleo/api/timeline: sin función equivalente | 2026-10-20 |
| P-27-15 | Video de presentación: giro 360° y recorrido de cámara en MP4 | Abierto | Media | Sin programar. | omnicad/api/herramientas_animacion.py:487 (solo gif/png); sin turntable | 2026-10-20 |
| P-28b | Galería con imágenes de referencia y explicación corta por tipo, con vista en vivo | Abierto | Media | Hay un diálogo de engranaje pero sin galería de tipos ni explicaciones. | omnicad/ui/comandos/engranaje.py | 2026-10-20 |
| P-29-1 | Perfil de impresora y material (cama aviso «no entra», holguras, encogimiento) | Abierto | Media | Sin programar. | grep «impresora/cama/boquilla» en omnicad/: sin perfil | 2026-10-20 |
| P-29-4 | Bolsillos de armado (imanes, insertos, tuercas, rodamientos) | Abierto | Media | Sin programar. | omnicad/nucleo/fijaciones.py sin bolsillos de armado | 2026-10-20 |
| P-29-5 | Agujeros que imprimen bien (gota, puentes, compensación) | Abierto | Media | Sin programar. | omnicad/api/herramientas_solido.py create_hole sin gota | 2026-10-20 |
| P-2a | Traducir la interfaz Qt al inglés (.ts / QTranslator) | Abierto | Alta | No hay catálogos .ts/.qm ni selector de idioma; solo textos en español. | omnicad/ui/captura.py es el único uso de QTranslator (botones estándar de Qt); sin archivos *.ts ni *.qm en clon/ | 2026-10-20 |
| P-2b | Mensajes de API, errores/pistas, CLI y MCP en los dos idiomas (--lang) | Abierto | Alta | Catálogo de mensajes para api/errores.py y descripciones del catálogo; opción --lang en CLI y MCP. | omnicad/api/errores.py (PISTAS solo en español); omnicad/cli y servidor_mcp sin --lang | 2026-10-20 |
| P-11g | d) Nombres de los cuerpos del .f3d (panel, aro_izq, perno_1) | Abierto | Alta | Están en el flujo de diseño pero no se encontró cómo ligarlos a cada cuerpo del SAB. | PROJECT_LOG.md:32; notas en privado/reportes/upgrades3/notas_flujo_diseno.md | 2026-10-20 |
| P-23c2 | c) Copiar y Cortar en el navegador (hoy grisados) | Abierto | Alta | No hay portapapeles paramétrico de cuerpos/pasos. | omnicad/ui/acciones_navegador.py:92 | 2026-10-20 |
| P-25e | e) ENSAMBLAR: Restricción de componentes y Relación de tangente | Abierto | Alta | No existen en la cinta. | omnicad/ui/cinta.py (grep «Restricción de componentes» y «tangente» en ENSAMBLAR: sin resultados) | 2026-10-31 |
| P-25e2 | e) Conjuntos de contacto y «Activar todos los contactos» (grisados) | Abierto | Alta | Botones grisados; misma brecha que SC6. | omnicad/ui/cinta.py:65 | 2026-10-20 |
| P-27-1 | Cortar y dividir con conectores (cubo, octágono, cola de milano, puzzle, pestaña elástica) | Abierto | Alta | Sin programar. | grep en omnicad/ nucleo/api/timeline: sin función equivalente | 2026-10-20 |
| P-27-2 | Moldes simples, por cajas y molde madre con colada y venteos | Abierto | Alta | Sin programar. | grep en omnicad/ nucleo/api/timeline: sin función equivalente | 2026-10-20 |
| P-27-3 | Canales internos autoportantes con diámetro variable | Abierto | Alta | Sin programar. | grep en omnicad/ nucleo/api/timeline: sin función equivalente | 2026-10-20 |
| P-27-4 | Jarrones, macetas y organizadores paramétricos | Abierto | Alta | Sin programar. | grep en omnicad/ nucleo/api/timeline: sin función equivalente | 2026-10-20 |
| P-27-5 | Articulaciones (rótula, pasador, bisagra, captura orgánica) | Abierto | Alta | Sin programar. | grep en omnicad/ nucleo/api/timeline: sin función equivalente | 2026-10-20 |
| P-27-7 | Corte por contorno con curva cerrada (2D y sobre la superficie) | Abierto | Alta | Sin programar. | grep en omnicad/ nucleo/api/timeline: sin función equivalente | 2026-10-20 |
| P-27-8 | Ajuste a superficie (curvar una insignia sobre una pieza) | Abierto | Alta | Sin programar. | grep en omnicad/ nucleo/api/timeline: sin función equivalente | 2026-10-20 |
| P-27-9 | Relieve desde imagen y pintura en capas de filamento | Abierto | Alta | Sin programar. | grep en omnicad/ nucleo/api/timeline: sin función equivalente | 2026-10-20 |
| P-27-10 | Texturas desde imagen aplicadas a caras | Abierto | Alta | Sin programar. | grep en omnicad/ nucleo/api/timeline: sin función equivalente | 2026-10-20 |
| P-27-11 | Color para impresión: pintar regiones, separar por color y 3MF multicolor | Abierto | Alta | Sin programar. | grep en omnicad/ nucleo/api/timeline: sin función equivalente | 2026-10-20 |
| P-27-16 | Importar OBJ o GLB con textura como color real sobre la malla | Abierto | Alta | Sin programar. | omnicad/io_archivos/gltf.py solo exporta | 2026-10-20 |
| P-28c | Cilíndricos faltantes (doble hélice, espina de pescado, interno, cicloidal, asimétrico, cremalleras helicoidales) | Abierto | Alta | Sin programar. | omnicad/nucleo/engranajes.py (solo evolvente recto/helicoidal) | 2026-10-20 |
| P-28h | Piñón y cremallera helicoidal, inclinada, doble hélice y curva | Abierto | Alta | Solo cremallera recta. | omnicad/nucleo/engranajes.py:430 cremallera | 2026-10-20 |
| P-29-2 | Orientación recomendada y estimación de filamento, peso y tiempo | Abierto | Alta | Sin programar. | omnicad/nucleo/revision.py no estima ni orienta | 2026-10-20 |
| P-29-3 | Cajas, tapas y organizadores paramétricos (encastre, rosca, bisagra) | Abierto | Alta | Solo existe create_box. | omnicad/api/herramientas_solido.py:327 | 2026-10-20 |
| P-3a | Add-on de Blender que hable con el puente en vivo (cuerpos, mallas, materiales) | Abierto | Muy alta | El puente existe; falta el add-on de Blender y el intercambio en los dos sentidos. | omnicad/ui/puente.py (127.0.0.1 + token) existe; sin código de add-on en el repo; solo exporta glTF (io_archivos/gltf.py) | 2026-10-20 |
| P-4c | Motor 3: trazador de rayos propio progresivo | Abierto | Muy alta | Decidido por el usuario como tercer motor; no existe nada de trazado de rayos. | grep de trazador/path tracing en omnicad/: sin resultados; docs/brechas_keyshot.md:64-66 (KS12-KS14) | 2026-10-20 |
| P-11h | d) Historial de operaciones del .f3d (traducir el timeline de Fusion) | Parcial | Muy alta | Los cuerpos entran como operación base y los bocetos como pasos; la tabla de tipos del flujo (BINCHA: 44 extrusiones, 14 empalmes, 9 chaflanes…) se declara al abrir. Las operaciones no se descifran: qué perfil usa cada extrusión y qué aristas toca cada empalme son recetas de nombre persistente que solo Fusion resuelve, y el archivo guarda solo el B-rep final (`docs/f3d_formato.md`: dos caminos probados). | tests/test_f3d_historial.py::test_abrir_un_f3d_con_historial_avisa_lo_que_no_se_tradujo; omnicad/io_archivos/f3d_historial.py | 2026-10-26 |
| P-11l | Bocetos de un .f3d con varios componentes | Abierto | Alta | El bloque `.smb` de bocetos no dice de qué componente es y la caja de los cuerpos no alcanza (415 de 418 perfiles de CARTERA GOTICA caen en más de un componente): hoy no se importan y se avisa. Hay que ligar cada `BREP.*.smb` con su componente leyendo los registros del flujo de diseño. | omnicad/io_archivos/f3d_nativo.py (_bocetos_ubicados); tests/test_f3d_bocetos.py::test_con_varios_componentes_los_bocetos_no_se_importan_y_se_avisa | 2026-10-26 |
| P-11m | Trazos abiertos, construcción, cotas, restricciones y nombres de los bocetos de un .f3d | Abierto | Muy alta | El `.smb` solo guarda las regiones cerradas: los bocetos importados no traen los trazos que no cierran región, la geometría de construcción, las cotas («4 mm», «120 mm»…) ni las restricciones, y se llaman Boceto1… Todo eso está en el flujo de diseño propietario. | omnicad/io_archivos/f3d_bocetos.py | 2026-10-26 |
| P-11i | Referencias externas de un .f3z (diseños hijos referenciados) | Abierto | Muy alta | Se identifican las ocurrencias externas pero no se decodifica su disposición interna. | PROJECT_LOG.md:32 (upgrades3, SIN RESOLVER) | 2026-10-20 |
| P-25i | i) SÓLIDO > CREAR: Crear forma y placa de circuito impreso (grisados) | Abierto | Muy alta | Siguen grisados; Forma depende de P-25j y la placa pide espacio ELECTRÓNICA. | omnicad/ui/cinta.py:90,103 | 2026-11-02 |
| P-25j | j) Espacio FORMA completo (T-splines): crear, modificar, simetría, utilidades | Abierto | Muy alta | No existe nada; necesita núcleo de subdivisión propio y decidir el motor. | Sin módulo de subdivisión en omnicad/nucleo/ | 2026-10-20 |
| P-27-12 | Soportes fáciles de sacar (cintas curvas, jaula) | Abierto | Muy alta | Sin programar. | omnicad/nucleo/revision.py:725-791 solo detecta voladizos, no genera soportes | 2026-10-20 |
| P-28d | Cónicos (recto, espiral, Zerol, hipoide, inglete, espirocónico) | Abierto | Muy alta | Sin programar. | omnicad/nucleo/engranajes.py | 2026-10-20 |
| P-28e | Tornillo sin fin y corona (cilíndrico, globoidal, perfiles ZA/ZN/ZI/ZK) | Abierto | Muy alta | Sin programar. | omnicad/nucleo/engranajes.py | 2026-10-20 |
| P-28f | Planetarios y epicicloidales con armado de trenes en un comando | Abierto | Muy alta | Sin programar. | omnicad/nucleo/engranajes.py | 2026-10-20 |
| P-28g | Especiales (no circulares, Hirth, armónico, cicloidal de pernos, esférico…) | Abierto | Muy alta | Sin programar. | omnicad/nucleo/engranajes.py | 2026-10-20 |
| P-28i | Mecanismos relacionados (Ginebra, trinquete, escape, reductores cicloidal/armónico) | Abierto | Muy alta | Sin programar. | omnicad/nucleo/engranajes.py | 2026-10-20 |
| P-12h | Hélice de boceto | Parcial | Media | Existe la espiral 2D; falta la hélice 3D (barrer/roscar a lo largo de ella). | omnicad/ui/modo_boceto.py:54; omnicad/ui/editor_boceto.py:1154; omnicad/ui/cinta_boceto.py:32 | 2026-10-20 |
| P-27-6 | Booleanas con holgura y formas listas para insertar (cono, pirámide, cuña, cápsula…) | Parcial | Media | Existen create_box/cylinder/sphere/torus; faltan holgura en booleanas y las demás formas. | omnicad/api/herramientas_solido.py:327 (create_box); herramientas create_cylinder/sphere/torus | 2026-10-20 |
| P-26d | .app firmada y notarizada (Apple Developer, USD 99 al año) | Bloqueado | Media | Pide cuenta de Apple Developer del usuario. | Sin carpeta instalador/macos | 2026-10-20 |
| P-25g2 | g) McMaster-Carr, pieza de fabricante y TraceParts | Bloqueado | Alta | Dependen de servicios en línea: decidir si se hacen. | PROJECT_LOG.md:71 | 2026-10-20 |
| MP1 | Mini programas: el usuario crea scripts Python con panel de campos armado solo (distancia, ángulo, cuerpo), pestaña «Mini programas» en la cinta para crear, guardar, correr y compartir | Abierto | Media | Todo. Base ya hecha: `execute_code` (transacción, timeout, deshacer) y el motor de grafos. Se junta con GH7, B5 y PAQ-H5. Un mini programa ajeno puede romper el trabajo: mostrar qué hace y pedir confirmación antes de correrlo. Después, el lienzo de nodos (GH4) para quien no programa. | `omnicad/api/` (`execute_code`); `docs/grafo.md` «Pendiente»; sin pestaña ni panel de campos en `omnicad/ui/` | 2026-10-20 |

## Hallazgos de pruebas de uso

Abierto 16 · Parcial 1 · Sin verificar 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| H-105 | Extruir superficie «Dos lados»: tipo de extensión propio del lado 2 (Al objeto, Todo) | Sin verificar | Media | Gemelo de H-81 (resuelto en el sólido el 2026-11-06). En superficie el lado 2 sigue siendo solo una distancia: `OpSupExtruir`, el panel y `create_surface_extrude` no tienen `extension2`/`hasta2`. La ayuda de Fusion para superficie dice «distances for each side independently» y no aclara si la extensión también va por lado: confirmarlo en Fusion antes de construir. | timeline/ops_superficie.py:100-151; ui/comandos/superficie.py:53-58; api/herramientas_superficie.py:75-125; docs/fusion_docs (Extrude a surface body) | 2026-11-06 |
| H-82 | Extruir › Al objeto sobre una cara: «Hasta caras adyacentes» (sólido) y «Extend Faces / Chain Faces» (superficie) | Abierto | Media | Sólido: Extender tiene cara, cuerpo y a través; falta To Adjacent Faces. Superficie: no tiene ninguna opción de Extender. | timeline/operaciones.py:1133 (`hasta_modo`); ui/comandos/superficie.py:55; ayuda `Extrude reference` y `Extrude a surface body` | 2026-11-05 |
| H-83 | Extruir, Revolución, Barrido y Solevación: operación «Componente nuevo» (sólido y superficie) | Abierto | Media | Fusion crea el cuerpo en un componente nuevo (diseño híbrido) en las cuatro herramientas (ayudas `Revolve reference`, `Sweep reference` y `Loft reference`, también en superficie). Hoy hay cuerpo nuevo, unir, cortar e intersecar; el componente se arma después con `create_component`. | timeline/operaciones.py:32 (`OPERACIONES_CUERPO`); api/herramientas_solido.py:183 | 2026-11-05 |
| H-84 | Extrusión delgada: Cadena tangente y conicidad con perfil abierto | Abierto | Baja | Falta la casilla Tangent Chain (elegir de una vez las curvas tangentes). La conicidad con perfil abierto da error; la ayuda no la restringe al tipo: confirmarlo en Fusion antes de hacerla. | ui/comandos/solido.py:33-35; nucleo/solidos_crear.py:487 | 2026-11-05 |
| H-88 | Revolución «A objeto» con «Dos lados» (sólido y superficie) | Abierto | Media | Fusion: con Tipo de extensión «To Object» la Dirección ofrece One Side y Two Sides. En OmniCAD la ventana esconde la Dirección y `revolve` / `create_surface_revolve` con `to_object` y `direction="two_sides"` dan INVALID_ARGUMENTS («to_object gira hacia un solo lado»). | timeline/operaciones.py:1294 (`OpRevolucion.ejecutar`); timeline/ops_superficie.py:195 | 2026-11-05 |
| H-89 | Barrido sólido › Ruta + Rail guía: Extensión «Perpendicular a la ruta» o «Extensión completa» con la fracción del rail | Abierto | Media | La ayuda de Fusion (`Sweep reference`) la tiene en el sólido; OmniCAD solo la tiene en el barrido de superficie (`extent`, `rail_distance`). Falta en `OpBarrido`, en `sweep` y en la ventana. | timeline/ops_solido.py:125 (`PARAMS` sin `extension`) | 2026-11-05 |
| H-90 | Solevación sólida: condición «Punto tangente» en un perfil punto | Abierto | Baja | Fusion ofrece Sharp y Point Tangent (cúpula). La ventana del sólido solo ofrece «Aguda» y `loft end_condition={"type": "point_tangent"}` da «type es free, direction, tangent o smooth». La superficie ya lo hace (157,12 mm² contra la media esfera de 157,08). | ui/comandos/crear.py:144 (`_condiciones_de`) | 2026-11-05 |
| H-91 | Solevación sólida: condiciones de borde junto con carriles, línea central, cerrada o reglada, y exactas | Abierto | Alta | En el sólido, Dirección, Tangente y Suave son aproximadas con una sección auxiliar y dan «no se combinan con carriles, línea central, solevado cerrado ni reglado». Fusion las combina, y la superficie ya lo hace con la derivada exacta (SUP-13). | nucleo/solidos_crear.py:1307 | 2026-11-05 |
| H-95 | Nervio: Radio de empalme e Invertir la dirección de extracción | Abierto | Media | Fusion Rib tiene Fillet Radius (redondea la base) y Flip Direction de la extracción. OmniCAD guarda `radio_empalme` en el paso pero el Nervio lo ignora (une sin empalme), la ventana lo muestra solo en la Red y `create_rib` no tiene `fillet_radius`; la extracción siempre se fuerza del cuerpo hacia la curva. Pieza `nervio_red_repujado` («Nervio › tiene Radio del empalme»). | timeline/ops_solido.py:271 (une sin `unir_con_empalme`); nucleo/solidos_crear.py:1457 | 2026-11-05 |
| H-96 | Repujado sobre caras que no son planas ni cilíndricas (esfera, cono, forma libre) | Abierto | Alta | Fusion repuja sobre cualquier cara del cuerpo. OmniCAD da «El repujado admite caras planas o cilíndricas (envolviendo)»: cuadro 6×6 sobre el polo de una esfera r 20 (`sondas_nrr.py rep_esfera`). | nucleo/solidos_crear.py:1571 | 2026-11-05 |
| H-97 | Repujado: asas de alineación (desplazamiento horizontal, vertical y giro) en la vista | Abierto | Media | Fusion: «Use the distance manipulator… / angle manipulator in the canvas» para Horizontal Distance, Vertical Distance y Rotation Angle. OmniCAD tiene los tres campos (en Más opciones) pero solo el asa de Profundidad. Pieza `nervio_red_repujado` («asas de alineación»). | ui/comandos/asas_extra.py:308 (`_asas_repujado`) | 2026-11-05 |
| H-19 | Vínculo de movimiento solo lineal | Abierto | Alta | Vínculo no lineal para biela-manivela; depende de resolver los lazos cerrados (H-18). | api/herramientas_ensamble.py:642-659 (valor unión 2 = ratio × unión 1) | 2026-10-20 |
| H-4 | Insertar: derivación y Duplicar con uniones hechos; falta el catálogo de piezas | Parcial | Media | Falta un catálogo local de piezas estándar más allá de las fijaciones (rodamientos, perfiles, pasadores…; sin servicios en línea): hay que decidir qué piezas y sus medidas. Duplicar con uniones copia un componente por vez, las copias son independientes (sin instancias asociativas) y no tiene los modos de destino «Entre dos caras» e «Intersección de dos aristas» ni «Borrar último duplicado». | ui/cinta.py:59 (Duplicar con uniones); api/herramientas_ensamble.py (duplicate_with_joints); ui/comandos/derivacion.py:16; api/herramientas_documento.py:322 (insert_derive); tests/test_derivacion.py; tests/test_duplicar_con_uniones.py; nucleo/fijaciones.py (solo fijaciones) | 2026-10-31 |
| H-69 | Organización del boceto: la geometría suelta no tiene nombre, ocultar, bloquear ni «en perfiles» propios | Abierto | Media | Hoy cada curva suelta se lista en Geometrías y su menú ofrece Seleccionar, Convertir en objeto (queda rígido, fuera del solver) y Eliminar. Falta guardar esas propiedades por curva sin sacarla del solver ni duplicar el modelo de objetos (plan_boceto_organizar.md, secciones 4 y 8). | clon/omnicad/ui/navegador_boceto.py (menú de `curva_boceto`); clon/tests/test_boceto_organizar.py::test_categorias_salen_del_dato_y_un_grupo_no_cambia_la_de_sus_miembros | 2026-11-05 |
| H-70 | Organización del boceto: expandir el contenido interno de un SVG o DXF (capas y formas) en el navegador | Abierto | Media | El SVG/DXF se lista como una unidad y sus partes solo se cuentan. Falta listar capas y formas bajo demanda (sin crear miles de filas) y poder elegir una pieza interna sin romper el contorno ni el relleno (plan_boceto_organizar.md, secciones 2 y 7). | clon/omnicad/ui/navegador.py (`_ramas_boceto`); clon/omnicad/restricciones/objetos.py (`unidades`) | 2026-11-05 |
| H-76 | Exportar STEP y OBJ con los colores (cuerpos y caras pintadas) | Abierto | Media | El STEP se escribe sin colores (`escribir_step` usa STEPControl, no la versión con XCAF) y el OBJ sin .mtl; el glTF sí los lleva. Comprobar en Fusion qué colores guarda su STEP antes de construir. El 3MF multicolor es P-27-11. Ver docs/brechas_aspecto.md. | clon/omnicad/nucleo/intercambio.py (`escribir_step`); clon/omnicad/io_archivos/exportar.py (`exportar_obj`) | 2026-11-05 |
| H-113 | Rosca › flecha en el visor para cambiar el tamaño de la rosca (arrastrar cambia Tamaño, Designación y el cilindro) | Abierto | Media | Asa de arrastre sobre la cara, como Fusion (0:36–0:56). Gerardo (2:30): «DEBERÍA PODER VER LAS FLECHAS PARA ADAPTAR EL TAMAÑO» | Ayuda de Fusion «Thread reference» (`scripts/fusion_docs.py ver "Thread reference" -s fusion-model`); `evidencias/videos_roscas_2026-11-10/informe.md`; captura `Fusion_0m40_cara_elegida_flechas_y_vista_previa.png` | 2026-11-10 |
| H-114 | Rosca › vista previa de la rosca cosmética (anillos sobre la cara) | Abierto | Media | Fusion dibuja los surcos aunque «Modelado» esté sin tildar; OmniCAD muestra el cilindro liso | `clon/omnicad/ui/comandos/crear.py` (Rosca); `evidencias/videos_roscas_2026-11-10/informe.md`; capturas `Fusion_0m33_dialogo_vacio_aceptar_gris.png`, `OmniCAD_0m30_dialogo_rosca_cosmetica_aviso.png` | 2026-11-10 |

## Boceto (auditoría contra la ayuda de Fusion, 2026-10-23)

Abierto 1 (H-110 de la fase 2 de CREAR y MODIFICAR). Plan por fases: [plan_boceto.md](../plan_boceto.md). Cada ID incluye su herramienta MCP/CLI, su test y la doc regenerada.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|

## Superficie (auditoría contra Fusion, 2026-10-24)

Cada fila salió de comparar la pestaña SUPERFICIE con los artículos de la ayuda de Fusion (sección Fusion-Patch de `docs/fusion_docs/`) y de probar las 14 herramientas por MCP/CLI. Los bugs se reprodujeron; los scripts de prueba (`sonda*.py`) están en `evidencias/superficie_2026-10-24/`, fuera de git.

Parcial 3.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| SUP-13 | Solevación de superficie: condiciones de borde, guías y pesos | Parcial | Alta | Hecho: condición por sección, alineación de bordes, rieles (también hasta un perfil punto, y en lazo con solevación cerrada), línea central, «Fusionar» y cadena; las condiciones se combinan con rieles y con línea central; Dirección, Tangente y Suave de los extremos fijan la derivada de salida con el peso como velocidad (medido: desvío de la salida de Tangente 5e-4 contra 0,106; Suave se separa de la cara 2e-4 mm contra 1,2e-3; con peso 2, unos 0,4°), también con rieles. Los pasos guardados antes siguen con secciones auxiliares (`condicion_exacta` falso) y dan lo mismo. Queda aproximado, con secciones auxiliares: Dirección en un perfil de en medio, Punto tangente, las condiciones con línea central y las de perfiles que no se emparejan (distinta cantidad de esquinas, como rectángulo a círculo: repartir el contorno redondearía las esquinas). Queda sin combinar: solevación cerrada con línea central (`MakePipeShell` de OCC no lo hace) y tramos rectos con guías o condiciones. ⚠ Qué valor de peso equivale a cada peso de Fusion no se pudo comparar: el MCP de Fusion no conecta. Ayuda: Loft reference (Surface). | omnicad/nucleo/superficies.py (`solevar_superficie`, `_solevar_con_rieles`, `_derivadas`, `_exacta_posible`); tests/test_superficie_guias.py::test_tangente_exacta_sale_con_la_direccion_de_la_cara | 2026-11-01 |
| SUP-14 | Parche: peso de tangencia por arista | Parcial | Media | Hecho: continuidad por arista (Agrupar aristas), rieles y puntos interiores e Invertir normal (`create_patch`: group_edges, edge_continuity, interior, flip). Falta el peso de tangencia (Tangency Weight, G1 y G2) por arista. Intento acotado (2026-10-31): `MakeFilling.Add`, `GeomPlate_*Constraint` y `GeomFill_ConstrainedFilling` no tienen peso (los criterios G0/G1/G2 son tolerancias; Coons es de 3 o 4 lados y calcula solo el largo de la derivada). `Plate_Plate` sí acepta una derivada con valor explícito, pero la placa es una altura sobre un plano medio: con G1 la pendiente la fija la cara de soporte y el largo de la tangente no existe en esa parametrización. Un peso real pide un relleno parametrizado por el borde; el atajo (puntos o secciones auxiliares sobre la tangente, como en la solevación) es una aproximación y no se simuló. Ayuda: Patch open areas on a surface body. Evidencia local: `evidencias/sup14_peso_2026-10-31/` (fuera de git). | omnicad/nucleo/superficies.py (`parche`); tests/test_superficie_fusion.py::test_parche_continuidad_por_arista_y_guias_interiores | 2026-10-31 |
| SUP-17 | Extender: alineación libre en caras curvas y valor por defecto de Fusion | Parcial | Baja | Hecho: Alineación de bordes del tipo Natural (`edge_alignment`): «alinear» (G1, lo de siempre y el valor por defecto) y «libre» (G0: además extiende una cara no rectangular en UV; plana con una franja tangente, curva —esfera, cilindro, cono, toroide, B-spline— sobre su propia superficie; un parche de relleno plegado fuera de sus límites cae a la franja tangente plana). Falta solo que el valor por defecto sea el de Fusion (Free Edges): se dejó «alinear» a propósito, porque cambiarlo haría que las recetas viejas den otro resultado (decisión de la tanda 1). Ayuda: Extend a surface body. | omnicad/nucleo/superficies.py (`extender`, `_extension_libre`); tests/test_superficie_fusion.py::test_extender_alineacion_libre_en_una_cara_curva_no_rectangular | 2026-10-31 |

## Sólido (auditoría contra Fusion, 2026-10-24)

Cada fila salió de comparar la pestaña SÓLIDO (y PLÁSTICO, CONSTRUIR, INSPECCIONAR, INSERTAR, SELECCIONAR) con los artículos de la ayuda de Fusion (carpeta `fusion-model`) y de probar unas 70 herramientas por API con valores normales, de borde e inválidos. Los bugs se reprodujeron; los scripts (`s*.py`) están en `evidencias/solido_2026-10-24/`, fuera de git. Lo que ya estaba cargado (SC12, SC3, P-25d, P-25f, P-25g2, P-25i, P-25j) no se repite.

Parcial 3.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| SOL-8 | Barrido sólido: Ruta + Superficie guía, Barrido de cuerpo, orientación Alineada y cadena tangente | Parcial | Alta | El barrido de un cuerpo sólido es aproximado: une copias del cuerpo a lo largo de la ruta (error de escalonado ≈2 % en un arco). Probé dos caminos exactos y ninguno anda: (1) `BRepOffsetAPI_MakePipe` de cada cara del cuerpo más el cuerpo inicial devuelve un sólido nulo e inválido para las caras que contienen la tangente de la ruta (en un cuarto de arco da 535,6 contra 566,65 exactos); (2) `MakePipeShell` con la cara como perfil recoloca el perfil de forma impredecible según la orientación de la cara (se ve en las cajas envolventes de los barridos). Test que lo muestra: `test_barrido_de_cuerpo_en_arco_se_acerca_al_volumen_exacto_y_la_via_por_caras_se_queda_corta`. Ya están Ruta + Superficie guía, orientación Alineada, `sweep_bodies` (aproximado) y la selección encadenada de aristas de cuerpo. | omnicad/nucleo/solidos_crear.py › `barrer`; tests/test_sol08_barrido.py | 2026-10-25 |
| SOL-22 | Retícula volumétrica (giroide o cruz) dentro de un cuerpo | Parcial | Alta | Ya están Cruz, Celda X, X 2.5D y a medida (sólido; solidez hasta donde la geometría de la celda llega: la Celda X llega a 99 %, la Cruz a 90 % y no a 95 %), Gyroid, Schwarz P y Schwarz D (malla, también sobre una malla cerrada), solidez en gradiente por una ruta, zona de desfase con mezcla y mover/girar las celdas. Quedan aproximaciones con su salida: la malla achaflana las aristas vivas un paso de grilla (≈3 % de volumen en un cilindro a 2 mm; se afina con `resolution` a costa de tiempo y memoria); en 2.5D con solidez variable el espesor cambia por capa de celdas, no de forma continua; con solidez variable las barras no se unen punta a punta y se llega antes al tope de 800 barras (subir la celda). Comparado con las capturas de Fusion: faltan OctetoTruss y Panal, las pestañas Configuración, Solidez y Desfase, el manipulador para mover y girar, y Restablecer. | omnicad/nucleo/reticula.py; tests/test_sol22_reticula.py; docs/brechas_extensiones.md | 2026-11-01 |
| SOL-24 | Reconocer funciones (Find Features) en cuerpos importados | Parcial | Muy alta | Rehace como pasos del timeline (`rebuild_features`, verificado por volumen y caja) los agujeros, empalmes y chaflanes. La extrusión (un prisma, con sus agujeros pasantes en el perfil) también se rehace como boceto + extrusión (`rebuild_features types=[extrude]`). Revoluciones, simetrías y patrones se reconocen y se informan, pero no se rehacen: la revolución necesita cortar el perfil por el eje (un sólido que contiene al eje da un perfil que lo cruza y `revolve` lo rechaza) y los patrones exigirían quitar copias y rearmarlas con su patrón. Faltan simetría en planos que no sean X, Y o Z por el centro, patrones radiales y extrusiones escalonadas. | omnicad/nucleo/reconocer_funciones.py; tests/test_sol24_reconocer_funciones.py | 2026-10-25 |

## Reconstruir sólido desde una malla (2026-11-01)

Plan: [plan_reconstruir_solido.md](../plan_reconstruir_solido.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| RI-2 | Reconstruir un sólido desde una malla, sin IA | Parcial | Alta | Las piezas de extrusiones, revoluciones, agujeros, empalmes, chaflanes y patrones ya salen (`reconstruct_from_mesh`: las 30 del banco cumplen todas las metas). Faltan las piezas reales que combinan direcciones: cortes con planos oblicuos (vaso inclinado), revolución más prisma, esquinas redondeadas con esferas (hoy el perfil trae los arcos y el empalme no entra) y moleteados. | tests/test_reconstruir_malla.py::test_un_bloque_vuelve_como_boceto_y_extrusion; scripts/bench_reconstruir.py reales | 2026-11-01 |
| RI-3 | Comando Reconstruir sólido en MALLA | Abierto | Alta | Los 3 estados aprobados: configurar, calculando y resultado, con Otra vuelta. | docs/plan_reconstruir_solido.md § Interfaz aprobada | 2026-11-01 |
| RI-4 | Resultado paramétrico en la reconstrucción | Abierto | Alta | Bocetos acotados, parámetros con nombre, patrones y simetrías. | docs/plan_reconstruir_solido.md § Opción del usuario | 2026-11-01 |
| RI-5 | IA en la reconstrucción | Abierto | Alta | Ficha, vistas y cortes a la IA, vueltas de corrección y tope de gasto. | docs/plan_reconstruir_solido.md § Idea central; omnicad/asistente/ | 2026-11-01 |
| RI-6 | Superficies libres en la reconstrucción | Abierto | Muy alta | Se decide con datos del banco. | docs/plan_reconstruir_solido.md § Fases | 2026-11-01 |

## Escanear con el celular (2026-11-01)

Upgrade a futuro: no se empieza hasta que Gerardo lo pida. Plan y prompt: [plan_escaneo_celular.md](../plan_escaneo_celular.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| ESC-1 | Prueba real de escaneo con celular | Bloqueado | Baja | 3 piezas conocidas con una app gratis, medidas contra calibre. Decide si la función sigue. | docs/plan_escaneo_celular.md § Fases | 2026-11-01 |
| ESC-2 | Importar un escaneo: fondo y escala | Bloqueado | Media | Comando Escanear pieza con archivos del celular, quitar fondo y escalar con una medida. | docs/plan_escaneo_celular.md § Fases; `insert_file` ya abre .stl, .obj, .3mf y .ply (api/herramientas_documento.py:345) | 2026-11-01 |
| ESC-3 | Hoja de escaneo con marcadores | Bloqueado | Media | PDF desde OmniCAD y detección automática de escala. | docs/plan_escaneo_celular.md § Lo que el celular no resuelve | 2026-11-01 |
| ESC-4 | Video a cuadros nítidos con aviso de faltantes | Bloqueado | Media | Elegir cuadros, rechazar video movido y juntar dos pasadas. | docs/plan_escaneo_celular.md § Fases | 2026-11-01 |
| ESC-5 | Motor local de video a malla | Bloqueado | Alta | Descarga opcional, proceso aparte y medición en esta PC. | docs/plan_escaneo_celular.md § Herramientas revisadas | 2026-11-01 |
| ESC-6 | IA para guiar el escaneo | Bloqueado | Media | Guía de captura, medidas a confirmar con calibre y redondeo. | docs/plan_escaneo_celular.md § Lo que el celular no resuelve; depende de RI-5 | 2026-11-01 |
| ESC-7 | Pasar el video del celular con QR | Bloqueado | Alta | Exige aprobar un servidor en la red local: los de hoy escuchan solo en 127.0.0.1 (AGENTS.md § Seguridad). | docs/plan_escaneo_celular.md § Decisiones | 2026-11-01 |

## SUPERFICIE contra capturas de Fusion (2026-11-01)

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| SUP-27 | Cinta de SUPERFICIE como Fusion: ítems y nombres | Abierto | Media | Faltan Derivar, Patrón, Simetría, Llenado, Origen de la unión, Chaflán, Quitar, Material físico, Administrar y Lista de materiales. | docs/brechas_superficie.md § SUP-27; ui/cinta.py:128 | 2026-11-01 |
| SUP-28 | Empalme y Chaflán de superficie completos | Abierto | Alta | Tipos, tipo de radio, cadena tangente y esquina; hoy son 3 campos. | docs/brechas_superficie.md § SUP-28; `fillet_surface` rechaza radius_type y tangent_chain, por API | 2026-11-01 |
| SUP-30 | Valores por defecto de superficie y paneles de material | Abierto | Media | Agrupar, Eje de proyecto, Anular recorte, Alargar y biblioteca de Material físico (el panel Aspecto ya está completo: `tests/test_aspecto_panel.py`). | docs/brechas_superficie.md § SUP-30 | 2026-11-01 |

## ENSAMBLAR contra capturas de Fusion (2026-11-01)

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| ASM-17 | Restricción de componentes: Alinear, Ángulo, Centro y Tangente | Parcial | Muy alta | Hechos Alinear, Ángulo, Centro y Tangente (2026-11-12): paso `restriccion` del timeline (`OpRestriccion`), herramienta `constrain_components` (`type` align, angle, center o tangent; `angle_reference`, `geometry1b`/`geometry2b`), comando y botón de ENSAMBLAR: caras coplanares, ejes concéntricos y puntos coincidentes con desfase y voltear; ángulo entre caras, aristas o ejes, con referencia de ángulo opcional; centro de una cara (o del plano medio de dos) entre las dos caras del otro componente, con voltear; tangente entre caras planas, cilíndricas, esféricas, cónicas y toroidales, aristas rectas y circulares, ejes y vértices, con «Todas las caras» (apagado exige que las caras se toquen); tabla de filas (`rows` en la API, «+ Agregar restricción» en el panel): se resuelven todas a la vez y el conflicto se avisa; cada fila lleva su nombre y su desfase (editables en la lista del panel y en `rows`), y un parámetro que solo cita el desfase de una fila extra recalcula el paso. Falta: Tangente con curvas libres (hoy error claro) y cono, toro o círculo con otra cosa que un plano, los límites de desfase y «Utilizar desfase como apoyo», la vista previa al pasar el cursor, resolver todas las restricciones a la vez y avisar los conflictos con las uniones. | docs/brechas_ensamblar.md § ASM-17; `tests/test_asm17_alinear.py`; `clon/omnicad/timeline/ops_ensamblar.py` (`OpRestriccion`) | 2026-11-12 |
| ASM-18 | Nuevo componente vacío y con opciones de Fusion | Abierto | Alta | Padre, Externo, tipos, nombre, A partir de cuerpos y Activar. | docs/brechas_ensamblar.md § ASM-18; `create_component` exige cuerpos, por API | 2026-11-01 |
| ASM-19 | Menú ENSAMBLAR y paneles como Fusion | Abierto | Media | Orden, nombres, atajo Mayús+J, pestañas de Unión e Incluir hijos encendido. | docs/brechas_ensamblar.md § ASM-19; ui/cinta.py:57 | 2026-11-01 |

## ANIMACIÓN contra capturas de Fusion (2026-11-01)

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| ANI-1 | Navegador y Comentarios en ANIMACIÓN | Abierto | Alta | Elegir, ocultar y transformar desde el Navegador. | docs/brechas_animacion.md § ANI-1; ui/animacion.py (`VentanaAnimacion`) | 2026-11-01 |
| ANI-2 | Explosión manual y barra de explosión | Abierto | Alta | Eje por componente, escala y secuencia en la barra. | docs/brechas_animacion.md § ANI-2; ui/animacion.py:695 (grisado) | 2026-11-01 |
| ANI-3 | Aspecto y trayectorias en la animación | Abierto | Media | Guardados en el guion, con herramienta. | docs/brechas_animacion.md § ANI-3; ui/animacion.py:696 (grisados); `add_animation_action` rechaza appearance, por API | 2026-11-01 |
| ANI-5 | Pieza de ANIMACIÓN en la prueba de ventana | Abierto | Media | Guion completo con publicación. | docs/brechas_animacion.md § ANI-5 | 2026-11-01 |

## Botones grisados sin fila (2026-11-01)

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| MAL-2 | MALLA: Alinear, Extruir textura y Edición directa | Abierto | Alta | Tres botones grisados y sin comando. | ui/cinta.py:175 y 178; ayuda `Extrude texture on a mesh body` | 2026-11-01 |
| CHA-1 | CHAPA: Pestaña solevada y Cierre de esquina | Abierto | Alta | Dos botones grisados y sin comando. | ui/cinta.py:148 y 151; ayuda `Create lofted flange` | 2026-11-01 |
| CFG-1 | Reglas de configuración | Abierto | Media | Botón grisado en CONFIGURAR. | ui/cinta.py:27; ayuda `Configuration Rules` | 2026-11-01 |

## Capturas de Fusion sin clasificar (2026-11-02)

Salen de las 674 capturas del escritorio, ya ordenadas en `analisis/capturas_fusion/` (índice: `INDICE.md`; las ya hechas se borraron, ver `borradas.tsv`). Abierto 10 · Bloqueado 2. Especificación: mirar las capturas de su sección y `scripts/fusion_docs.py buscar`.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| CF-1 | DIBUJO: diálogo Crear dibujo completo | Abierto | Media | Modo Automático, contenido (todo, visible, selección), creación de planos por nivel, documento base, unidades, recuento de planos y tamaño personalizado. | ui/dibujo.py (solo `DialogoHoja`); capturas `DIBUJO/Crear_dibujo` | 2026-11-02 |
| CF-2 | DIBUJO: panel Vista de dibujo | Abierto | Alta | Estilos sombreados, mejorar calidad, aristas de interferencia y de rosca, aristas tangentes (longitud completa, acortado), marcas y líneas de centro por tipo (agujero, cortes redondos, extrusiones redondas, patrón, empalme), orientación con vistas guardadas y referencia/instancia/representación. RH14 solo cubre estilos importables. | ui/dibujo.py; capturas `DIBUJO/Vista_de_dibujo` y `DIBUJO/Vista_base` | 2026-11-02 |
| CF-3 | DIBUJO: menú COTAS completo | Parcial | Media | Hechas Línea base y Longitud de arco (2026-11-04, tests/test_dibujo.py). Faltan cota automática, ordenar, organizar, igualar, voltear flechas, recodo y máx/mín. | nucleo/dibujo.py; capturas `DIBUJO/Menu_de_cotas` y `DIBUJO/Ordenar` | 2026-11-02 |
| CF-4 | DIBUJO: notas, tablas y símbolos | Abierto | Media | Nota de agujero y rosca, de pliegue, panel de Texto con formato; tablas de plegado, agujeros, personalizada, revisiones y nube; símbolos de rectángulo de tolerancia, identificador de referencia, ángulo, inclinación, arista y boceto; extensión de arista. F9 cubre solo soldadura y acabado. | ui/dibujo.py; capturas `DIBUJO/Tablas`, `Simbolos_de_dibujo`, `Texto_y_notas` | 2026-11-02 |
| CF-5 | DIBUJO: navegador, hojas, cinta y exportar | Abierto | Media | Navegador de dibujo con hojas múltiples, pestañas ADMINISTRAR y UTILIDADES, grupos SÍMBOLOS, INSERTAR e INSPECCIONAR, Exportar DWG y CSV, vista de sección parcial y recortada, boceto de dibujo, patrón de marcas de centro. | ui/dibujo.py; capturas `DIBUJO/Navegador_de_dibujo`, `Exportar_dibujo` | 2026-11-02 |
| CF-6 | Diálogo «¿Qué desea diseñar?» al crear un diseño | Abierto | Media | Tipo (piezas, ensamblaje, híbrido, dibujo), sistema de unidades y plantilla. Hoy `nuevo()` crea siempre un diseño vacío. Relacionada con H-5. | grep «Qué desea» en omnicad/: sin resultados; capturas `INTERFAZ/Nuevo_diseno*` | 2026-11-02 |
| CF-7 | Preferencias: páginas que no existen | Abierto | Media | Páginas Dibujo, Configuraciones, Renderizar (valores por defecto), Material, Diseños híbridos y de ensamblaje, Unidades por defecto (Diseño) y Visualización de unidad y valor (faltan 10 de 13 ajustes). | omnicad/ui/preferencias.py; capturas `INTERFAZ/Preferencias_*` | 2026-11-02 |
| CF-8 | Preferencias: opciones sueltas de General y Gráficos | Parcial | Baja | Hechas: el tamaño del ViewCube (cinco tamaños como Fusion, en Preferencias › General y en el clic derecho del ViewCube, API incluida) y la barra espaciadora que repite el último comando (`general/espacio_repite`) — tanda C11, 2026-11-06; el tema del sistema (`general/tema` = `sistema`: sigue al claro/oscuro de Windows, como «Match Device Theme» de Fusion; el tema queda fuera del MCP, como manda CLAUDE.md) y los presets de ratón Alias, Inventor, PowerMill y SOLIDWORKS (`general/raton`, también en la API; con Inventor, F2/F3/F4 navegan en el visor en vez de Renombrar) — tanda C13, 2026-11-06. Faltan: (a) orientación Y o Z hacia arriba: el combo «Orientación de modelado por defecto» solo ofrece «Z hacia arriba», y darlo vuelta toca el marco de la cámara en 15 lugares de 6 archivos (`ui/visor3d.py`: `ojo`, `desplazar`, `encuadrar`, `mirar_a_plano`, `primitivas_centro_giro` y el sombreado; `ui/render.py` › `u_atras`; `ui/manipuladores.py`; `ui/comandos/comunes.py`, `editar_cara.py` e `inspeccionar.py`) porque hoy todos leen `visor.R` como dirección del mundo, y sin verlo en pantalla no se puede dar por bueno; (b) tipo de diseño por defecto: OmniCAD no tiene tipos de diseño (Pieza/Ensamblaje/Híbrido), es una función que falta (ver CF-6); (c) finalidad de uso: en Fusion solo elige qué sugiere la puesta en marcha, que OmniCAD no tiene; (d) experiencia de puesta en marcha: no hay asistente ni tour de primer arranque; (e) controlador de gráficos: Fusion elige DirectX/Metal/OpenGL para la interfaz y OmniCAD usa el de Qt, sin una opción que se pueda cumplir de verdad. P-2d cubre el idioma. | tests/test_preferencias.py; omnicad/ui/preferencias.py; capturas `INTERFAZ/Preferencias_General` | 2026-11-06 |
| CF-9 | MALLA: Suavizar contorno, Puente e Insertar malla completo | Abierto | Media | Suavizar contorno (suavidad, iteraciones, anillos) y Puente no existen; Insertar malla solo pregunta la unidad: faltan Voltear dirección, Centro, Mover a suelo, entradas numéricas y Restablecer. MAL-2 y MAL-3 no nombran la paleta de pincel. | grep sin resultados en api/ y ui/comandos/; capturas `MALLA/` e `INSERTAR/Insertar_malla` | 2026-11-02 |
| CF-10 | MATERIALES: Explorador de materiales y propiedades | Abierto | Media | Propiedades térmicas y mecánicas, favoritos, materiales nuevos y bibliotecas personales. P-25d cubre solo Administrar. | capturas `MATERIALES/` | 2026-11-02 |
| CF-13 | SÓLIDO: Modelado automatizado | Bloqueado | Muy alta | Genera alternativas entre geometrías a conectar y a evitar; emparentado con EXT-3 (diseño generativo). Espera el alcance. | sin herramienta; capturas `SOLIDO/Modelado_automatizado` | 2026-11-02 |
| CF-14 | ELECTRÓNICA: esquemas, placas y biblioteca de componentes | Bloqueado | Muy alta | Diseño de electrónica 2D y 3D, biblioteca de componentes y leyenda de taladro. P-25i solo nombra la placa. Espera el alcance. | sin código; capturas `ELECTRONICA/` | 2026-11-02 |

## Plástico y extensiones contra capturas de Fusion (2026-11-01)

Especificación y prompt: [brechas_extensiones.md](../brechas_extensiones.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| PLA-1 | Grampa de fijación (Snap Fit): gancho y ranurado paralelos o perpendiculares, gancho y contorno | Parcial | Alta | Hecho (2026-11-03): los 3 tipos con puntos manuales, giro Uniforme, extensión Hasta el siguiente o Distancia, API y botón. Faltan selección Automática, giro Independiente o Alineado, Flip y radio de empalme de la base; cabeza y ranura son cajas simples. | ui/cinta.py:160 (botón gris); docs/brechas_extensiones.md | 2026-11-01 |
| PLA-3 | Saliente de fijación de dos lados, con fijador y nervios | Parcial | Alta | Hoy es un solo lado: exterior, agujero, alto y desmoldeo. Falta Lado 2, escariado, escalón, fijador y pestaña de nervios. | api create_boss: volumen 30681,51 en la caja medida; docs/brechas_extensiones.md | 2026-11-01 |
| PLA-4 | Labio: tipo Labio y acanalado sobre dos cuerpos | Parcial | Media | Hecho (2026-11-03): labio y ranura base con validación de aristas (B-158). Faltan Cadena tangente, Guía de cara y Avanzado (extensiones, Flip). | api create_lip_groove: lip_type solo lip o groove; docs/brechas_extensiones.md | 2026-11-01 |
| PLA-5 | Reglas de plástico: árbol, editar, biblioteca y quitar la regla | Parcial | Media | Crear, asignar y borrar andan. Falta el árbol, Editar, Nueva desde otra, elegir en el lienzo, quitar desde el navegador y las reglas de fábrica de Fusion. | ui/comandos/plastico.py; docs/brechas_extensiones.md | 2026-11-01 |
| PLA-7 | Patrón geométrico: objeto personalizado y caras curvas | Parcial | Media | Faltan Dirección perpendicular, Cambiar y Expandir. Comprobar en Fusion real si acepta caras curvas: hoy OmniCAD las rechaza. | api create_geometric_pattern: «necesita una cara plana»; docs/brechas_extensiones.md | 2026-11-01 |
| PLA-8 | Sólido delimitador: tipos fijos, desfases, redondeo, origen y cotas | Parcial | Media | Hoy tres formas y un margen. Faltan seis tipos, modo de desfase, redondeo, cuatro orígenes y cotas en vivo. | ui/cinta.py:102; api create_bounding_solid; docs/brechas_extensiones.md | 2026-11-01 |
| PLA-9 | Simplificar: Eliminar operaciones, Eliminar caras y Reemplazar con primitivas | Parcial | Alta | Eliminar caras, Eliminar operaciones (empalmes, chaflanes y agujeros por tamaño) y Reemplazar con primitivas (caja, cilindro, esfera) andan. Faltan: en Reemplazar, el modo Componentes y las asas; en Eliminar operaciones, elegir a mano y los tipos Extruir, Revolución y Otros; en Eliminar caras, que elija solas las caras vecinas. El defeaturing no quita un chaflán pegado a un empalme ni dos chaflanes contiguos. | tests/test_reemplazar_primitivas.py; tests/test_simplificar.py; tests/test_comandos_modificar.py::test_eliminar_caras_borra_la_cara_de_un_empalme; docs/brechas_extensiones.md | 2026-11-03 |
| PLA-10 | Insertar fijador: panel de biblioteca | Parcial | Alta | Hay 5 familias y 14 normas ISO y DIN. Falta buscador, 16 organizaciones, imperial, árbol, favoritos, vistas, columnas, filtros por medida, remaches e inserciones. | nucleo/fijaciones.py NORMAS; docs/brechas_extensiones.md | 2026-11-01 |
| PLA-11 | Timeline: Convertir en operación de DM | Abierto | Media | No figura en la ayuda local: comprobar en Fusion real qué hace antes de construirla. | ui/panel_timeline.py:338 (entradas_menu); docs/brechas_extensiones.md | 2026-11-01 |
| PLA-12 | Convertir malla: método Orgánico | Abierto | Muy alta | Hoy solo facetado y prismático. Falta Orgánico, Paramétrica o Base, resolución y Preprocesar agujeros. Se relaciona con F10, F11 y RI-1. | api convert_mesh; docs/brechas_extensiones.md | 2026-11-01 |
| PLA-13 | PMI: notas 3D de agujero o rosca y nota libre | Abierto | Alta | No existe. Va en Utilidades › Crear PMI. | sin código (grep pmi); docs/brechas_extensiones.md | 2026-11-01 |
| EXT-1 | Anidación y fabricación (Manufacturing Extension) | Bloqueado | Muy alta | Decidir el alcance: hojas, materiales, estudios y exportar DXF. Se relaciona con Organizar de P-25d. | sin código (grep anidaci); docs/brechas_extensiones.md | 2026-11-01 |
| EXT-2 | Simulación avanzada: térmica, modal, pandeo, no lineal, eventos, moldeo y refrigeración | Bloqueado | Muy alta | Depende de F19, que es solo estática. | sin código FEM (grep); docs/brechas_extensiones.md | 2026-11-01 |
| EXT-3 | Diseño generativo | Bloqueado | Muy alta | Decidir el alcance. Depende de F19. | ui/cinta.py:255 (espacios grisados); docs/brechas_extensiones.md | 2026-11-01 |
| EXT-4 | Fusion Manage: PLM en la nube | Bloqueado | Muy alta | Decidir si se hace: el proyecto trabaja sin nube. | sin código; docs/brechas_extensiones.md | 2026-11-01 |

## Ensamblar (auditoría contra Fusion, 2026-10-25)

Cada fila salió de comparar ENSAMBLAR (uniones, componentes, grupo rígido, vínculos, estudio de movimiento) con los artículos de la ayuda de Fusion (carpeta `fusion-assemble`), de probar unas 60 llamadas por API (`evidencias/ensamble_2026-10-25/a*.py`) y de usar la ventana real como una persona (`scripts/prueba_ui/ensamblar.py`, 224 comprobaciones). Lo que ya estaba cargado (P-25e, P-25e2, SC6, SC7, SC8, SC15, H-4, H-5, H-19, F8, P-6d) no se repite.

Abierto 1 · Parcial 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| ASM-9 | Activar componente (lo que queda de los subensamblajes) | Parcial | Alta | Hecho el 2026-11-01: Nuevo componente con «Padre», navegador en árbol, mover o unir al padre arrastra a sus hijos (uniones, vínculos, posición inicial, Capturar y Revertir, estudio y arrastre del visor), «Incluir componentes secundarios» del grupo rígido, copiar y patronear subensamblajes enteros, `parent`/`children`/`path` en `get_assembly` y la lista de materiales. Falta Activar componente (Activate a component): el timeline muestra solo los pasos del componente activo (lo espera FU-14), padre y hermanos translúcidos, y lo que se crea entra al componente activo (uniones y estudios siguen en la raíz). | tests/test_ensamblar_asm9.py; scripts/prueba_ui/subensamblaje.py | 2026-11-01 |
| ASM-16 | Arrastrar componentes: lazos cerrados, rotar libre y varios a la vez | Abierto | Alta | El arrastre del visor (ASM-15, resuelto) sigue los grados de libertad de una unión y traslada los libres. Falta: resolver un lazo cerrado de uniones mientras se arrastra (hoy lo rechaza con un mensaje que manda a Accionar uniones), rotar un componente libre con el mouse (hoy, Editar posición inicial) y arrastrar varios componentes elegidos a la vez. Con algo sin capturar, elegir en el visor queda en pausa hasta Capturar o Revertir (en Fusion se sigue eligiendo). Ayuda: Capture or revert position of components. | omnicad/timeline/posicion.py (`que_arrastra`); tests/test_posicion_ventana.py::test_sin_capturar_ni_el_resaltado_ni_el_clic_eligen_la_posicion_vieja | 2026-11-01 |


## Asas de arrastre (gizmos) contra la ayuda de Fusion (auditoría 2026-10-26)

Se recorrieron los 148 comandos del catálogo y las cintas: 44 tienen asas (`Comando.manipuladores`) y 104 no. Acá solo están los que **la ayuda de Fusion dice que tienen manipulador** y OmniCAD no (o los tiene incompletos). Los comandos sin asa en Fusion (Alinear, Simetría, Combinar, Dividir, ejes, planos por puntos, análisis de color, etc.) quedan fuera a propósito. Las asas se arman con `ui/manipuladores.py` (Flecha, Angulo, AsaRadial, Posicion, Triada y las de calcomanía: giro, codo de escala y volteos). Cada gizmo lleva su prueba en `tests/` y en la pieza `asas` de `scripts/prueba_ui/`. Ya resueltos (están en el Registro): Lienzo, Calcomanía, las asas de Revolución de superficie y Reglada (SUP-25) y el tope de Extender (SUP-26). El que ya tiene fila propia: FU-4 (asas de Extruir).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|

## Fusion 360

Abierto 1 · Parcial 1 · Bloqueado 1. Especificación: [brechas_fusion.md](../brechas_fusion.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| FU-14 | Engranaje del timeline: «Ocultar pasos inactivos» y «Cambiar a modelado directo» | Abierto | Alta | Hace falta un componente activo (que filtre el timeline) y un modo sin historial; el engranaje ya existe con «Muestra de color por componente» | ui/panel_timeline.py (engranaje con una sola opción); ui/acciones_navegador.py:164 («Cambiar al modelado directo» grisado) | 2026-10-21 |
| FU-8 | Historial de pasos al abrir un .f3d | Parcial | Muy alta | Los bocetos entran como pasos y el historial se declara al abrir (P-11h). Falta descifrar el flujo de diseño de Fusion o traducirlo con su API pública (el puente con Fusion abierto). | omnicad/io_archivos/f3d_historial.py; integraciones/fusion/OmniCADPuente (parámetros con Fusion) | 2026-10-26 |
| FU-12 | Simulación, Fabricación y Forma (T-Splines) | Bloqueado | Muy alta | Decidir dependencias (CalculiX, Gmsh) y alcance antes de empezar | ui/cinta.py:244 (espacios grisados); sin código FEM, CAM ni T-Splines (grep) | 2026-10-20 |

## FreeCAD

Abierto 3 · Parcial 5 · Bloqueado 4. Especificación: [brechas_freecad.md](../brechas_freecad.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| F6 | Rebanar: N cortes paralelos como curvas, caras o láminas | Abierto | Media | Operación y comando de serie de cortes paralelos con salida a bocetos o cuerpos finos | sin código (grep rebanar/slice); existen dividir_cuerpo y cortar_plano de malla | 2026-10-20 |
| F15 | Parámetros desde XLSX y familias de piezas desde hoja | Abierto | Media | El CSV ya anda: falta XLSX y las familias de piezas. | api/herramientas_parametros_csv.py y ui/dialogos.py:254 ya importan CSV; timeline/documento.py:168 tabla de configuraciones | 2026-11-01 |
| F13 | Estructura de perfiles con ingletes y lista de cortes | Abierto | Alta | Perfiles estándar a lo largo de rutas con ingletes automáticos y lista de cortes | sin código (grep); nucleo/superficies.py:525 aclara que no hay esquinas a inglete | 2026-10-20 |
| F1 | Engranajes, cremallera y rueda de cadena | Parcial | Baja | Polea dentada (correa); valores ISO 606 de la rueda de cadena por verificar | ed0c4dc; nucleo/engranajes.py; timeline/ops_engranaje.py; ui/comandos/engranaje.py; api create_gear, create_gear_pair, create_rack, create_sprocket; tests/test_engranajes.py; tests/test_api_engranajes.py | 2026-10-20 |
| F2 | Revisar geometría con botón Reparar | Parcial | Media | Lista con clic por problema que resalta la pieza; mapa de color del espesor | 4fca4c7; nucleo/revision.py; ui/comandos/revision.py; api check_geometry, repair_body; tests/test_revision.py; tests/test_api_revision.py | 2026-10-20 |
| F8 | Uniones de transmisión (engranaje, cremallera-piñón, tornillo, correa) | Parcial | Media | Tipos de unión propios que calculen la relación solos (cremallera-piñón, tornillo, correa) | timeline/ops_ensamblar.py:461 OpVinculoMovimiento (factor manual); api/herramientas_ensamble.py:642 create_motion_link; create_gear_pair crea el vínculo con la relación de dientes | 2026-10-20 |
| F9 | Dibujo: vista interrumpida, soldadura, acabado, ajuste, cotas en cadena | Parcial | Media | Vista interrumpida, símbolos de soldadura y acabado, ajuste, cotas en cadena y de chaflán | nucleo/dibujo.py (rayado:520, cota de diámetro ⌀:659; sin esos símbolos); io_archivos/svg_salida.py | 2026-10-20 |
| F23 | Curva sobre malla y relleno con continuidad G2 | Parcial | Alta | Curva sobre malla | timeline/ops_superficie.py:104-117 OpParche G0/G1/G2; nucleo/superficies.py:472; tests/test_superficies.py:138 (parche G1 con soporte) | 2026-10-20 |
| F21 | Fragmentos booleanos, XOR, conectar e incrustar forma | Bloqueado | Media | Solo si el usuario lo pide: fragmentos, XOR y conectar/incrustar/recortar forma | sin código (grep xor/fragmento) | 2026-10-20 |
| F22 | Nube de puntos e importar .scad | Bloqueado | Media | Importar PLY/XYZ como nube de puntos; .scad pide OpenSCAD instalado (decisión del usuario) | io_archivos/abrir_externo.py solo importa PLY como malla; sin código de nube de puntos ni OpenSCAD | 2026-10-20 |
| F19 | Simulación estática FEM (CalculiX + Gmsh) | Bloqueado | Muy alta | Decidir las dependencias externas y construir la simulación estática | sin código FEM (grep); ui/cinta.py:244 espacio SIMULACIÓN grisado | 2026-10-20 |
| F20 | Fabricación CAM (contorno, bolsillo, taladrado, G-code) | Bloqueado | Muy alta | Decidir el alcance de un proyecto aparte y construir el CAM | sin código CAM ni G-code (grep); ui/cinta.py:244 espacio FABRICACIÓN grisado | 2026-10-20 |

## Plasticity

Abierto 1 · Parcial 1 · Bloqueado 1. Especificación: [brechas_plasticity.md](../brechas_plasticity.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| PL10 | Puente en vivo con Blender | Abierto | Alta | Add-on de Blender, botón «Enviar a Blender» y refresco al cambiar un parámetro | sin código de Blender (grep); ui/puente.py es el puente de agentes MCP, no transmite mallas a Blender | 2026-10-20 |
| PL8 | Instancias que comparten geometría y Realizar instancias | Parcial | Media | Instancias de curvas de boceto y de operaciones del timeline | 4b50c6f; nucleo/solidos_crear.py:2793; api realize_copies; tests/test_pl8_instancias.py | 2026-10-20 |
| PL12 | Soporte de SpaceMouse (3Dconnexion) | Bloqueado | Media | Requiere el dispositivo 3Dconnexion para probar y su biblioteca de entrada | sin código SpaceMouse ni 3Dconnexion (grep) | 2026-10-20 |

## Blender

Abierto 8 · Parcial 5 · Bloqueado 2. Especificación: [brechas_blender.md](../brechas_blender.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| B6 | Video MP4, cámara en ruta y suavizado editable | Abierto | Media | MP4 (ffmpeg, pedir permiso), cámara en ruta y suavizado editable por tramo | api/herramientas_animacion.py:484 (solo gif o png); nucleo/animacion.py:42 (suavizado fijo) | 2026-10-20 |
| B11 | Varillas desde aristas (jaulas, marcos, celosías) | Abierto | Media | Cada arista a una varilla con sección elegida y nudos redondeados | sin código (grep); solo existe tuberia sobre una ruta | 2026-10-20 |
| B12 | Esparcir copias sobre una superficie | Abierto | Media | Tipo «Sobre superficie» del Patrón con densidad y semilla | timeline/ops_solido.py OpPatron: rectangular, circular, ruta, puntos; sin esparcir | 2026-10-20 |
| B1 | Render con Cycles de Blender como motor externo | Abierto | Alta | Exportar la escena, correr Blender en segundo plano y mostrar la imagen | sin código Cycles (grep); ui/render.py solo motores gl y cpu; orden decidido en brechas_keyshot.md:35 | 2026-10-20 |
| B5 | Complementos de usuario con manifiesto | Abierto | Alta | Cargar operaciones, comandos y herramientas desde una carpeta con manifiesto, con interruptor y errores | ui/administrar.py:262 (solo ejecuta scripts sueltos); ui/cinta.py:174 | 2026-10-20 |
| B10 | Ajustar a superficie (Shrinkwrap) | Abierto | Alta | Llevar curvas, mallas o puntos a una superficie (más cercano, eje o normal) | sin código (grep shrinkwrap/ajustar a superficie) | 2026-10-20 |
| B13 | Relieve por textura en caras (Displace) | Abierto | Alta | Desplazar caras con ruido o imagen: cuero, panal, agarre | sin código (grep); existe repujado de perfiles y texto (timeline/ops_solido.py:156) | 2026-10-20 |
| B18 | Mapeo UV y texturas | Abierto | Alta | Desenvolver y proyecciones caja, cilindro y esfera; va con el render y con RH21 | sin código UV (grep); existe calcomanía sobre cilindro (tests/test_calcomania_cilindro.py) | 2026-10-20 |
| B4 | Vectorizar imagen: vista previa y esquinas | Parcial | Baja | Vista previa propia de las curvas. Las esquinas ya andan (Ángulo de esquina); un contorno con una sola punta no se parte. | tests/test_texto_vectores.py::test_el_angulo_de_esquina_parte_el_contorno_en_tramos_abiertos; 32c9e2d; io_archivos/vectorizar.py:93; ui/comandos/insertar.py:125; api trace_image; tests/test_texto_vectores.py | 2026-10-20 |
| B2 | Revisión de impresión 3D (espesor, voladizos, aristas filosas) | Parcial | Media | Lista con clic por problema y mapa de color sobre la pieza | 4fca4c7; nucleo/revision.py revisar_impresion; api check_printability; tests/test_revision.py; tests/test_api_revision.py | 2026-10-20 |
| B3 | Exportar FBX y USD (glTF ya está) | Parcial | Alta | Escritor de FBX (sin especificación pública) y de USD (pide la biblioteca pxr) | 8e1a1fe; io_archivos/gltf.py (docstring: FBX y USD no se escriben); tests/test_gltf.py | 2026-10-20 |
| B7 | Imán (snapping) completo en el visor | Parcial | Alta | Barra de imanes: vértice, arista, cara, centro de arista, perpendicular, varios a la vez | ui/manipuladores.py:51,297-347 (enganche a centro de cara, esquinas y puntos medios al ubicar) | 2026-10-20 |
| B15 | Nodos de geometría: campos, atributos, instancias, zonas de repetición | Parcial | Muy alta | Campos, atributos, instancias con realizar y zonas de repetición y simulación | omnicad/grafo/ (árboles de datos, nodos, horneado); docs/grafo.md; api run_graph, bake_graph, list_graph_nodes; tests/test_grafo.py; tests/test_api_grafo.py | 2026-10-20 |
| B16 | Modo edición de malla (extruir, inset, bisel, cuchillo) | Bloqueado | Muy alta | Solo si el usuario lo pide: modelado de malla, fuera de lo que hace Fusion | sin código (grep); la malla es solo de triángulos (nucleo/malla.py:2405) | 2026-10-20 |
| B17 | Simulación de cuerpo rígido | Bloqueado | Muy alta | Elegir un motor de física (dependencia nueva, pedir permiso) y hornear a animación | sin código de física (grep); espacio SIMULACIÓN grisado (ui/cinta.py:244) | 2026-10-20 |

## Rhino 8

Abierto 9 · Parcial 3 · Bloqueado 4. Especificación: [brechas_rhino.md](../brechas_rhino.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| RH10 | Relieve desde imagen (mapa de altura a superficie) | Abierto | Media | Comando con imagen, tamaño, altura máxima y resolución | sin código (grep heightfield/mapa de altura); existe repujado con perfiles y texto | 2026-10-20 |
| RH15 | Colocar y repartir sobre superficies | Abierto | Media | Orientar sobre superficie o curva, matriz sobre superficie y repartir con separación pareja | sin código (grep); existen alinear, mover y patrón en ruta | 2026-10-20 |
| RH1 | Mezcla de superficies con continuidad G0 a G3 | Abierto | Alta | Mezclar bordes con continuidad por lado y radio o tensión variable | sin código (grep mezclar/blend en superficies); existen parche, reglada y sup_empalme | 2026-10-20 |
| RH2 | Igualar superficie o curva (Match) | Abierto | Alta | Mover un borde hasta coincidir en posición, tangencia o curvatura con otro | sin código (grep); solo reemplazar_cara sin continuidad | 2026-10-20 |
| RH4 | Desenrollar y solevación desarrollable | Abierto | Alta | Aplanar superficies desarrollables con mapa de distorsión y exportar a DXF | nucleo/chapa.py:609 patron_plano (solo chapa); sin Unroll ni Squish (grep) | 2026-10-20 |
| RH5 | Editar agujeros y caras de un cuerpo sin historial | Abierto | Alta | Mover, copiar y cambiar Ø o profundidad de un agujero existente; mover cara o arista | existen desfase_cara y borrar_caras; sin edición de agujeros existentes (grep) | 2026-10-20 |
| RH11 | ShrinkWrap: malla estanca alrededor de objetos | Abierto | Alta | Envolver mallas, NURBS o nubes con celda y cierre de huecos (puede pedir dependencia) | nucleo/solidos_crear.py:2911 solido_envolvente es una caja o cilindro, no un shrinkwrap; reparar_malla | 2026-10-20 |
| RH21 | Mapeo UV y texturas (cajas, esfera, editor UV) | Abierto | Alta | Proyecciones caja, cilindro, esfera y editor de UV; misma tarea que B18 | sin código UV (grep) | 2026-10-20 |
| RH7 | Deformar: fluir, doblar, torcer, cónico, jaula, caída suave | Abierto | Muy alta | Operación Deformar con tipos, vista previa viva y manipulador | sin código (grep deformar/flow/bend/twist) | 2026-10-20 |
| RH6 | Seleccionar por criterio (duplicados, no manifold, planos, color) | Parcial | Media | Duplicados, objetos chicos, malos, no manifold, planos, por color o material | ui/ventana.py:420-421 (Seleccionar por nombre y por tamaño); ui/cinta.py:69-70; api find_edges, find_faces con selectores | 2026-10-20 |
| RH8 | Más superficies: red de curvas, entre curvas, cortina, por puntos | Parcial | Alta | Red de curvas, entre curvas, extrusión a un punto, cortina, superficie por puntos | timeline/ops_superficie.py:104 OpParche (cubre algo de EdgeSrf); ui/comandos/superficie.py:311; tests/test_comandos_superficie.py | 2026-10-20 |
| RH9 | Editar por puntos de control (curvas y caras) | Parcial | Alta | Mover CV de curvas 3D y caras, insertar nudo, cambiar grado, reconstruir, caída suave | restricciones/boceto.py:198 (spline de control en bocetos con pesos y nudos); ui/editor_boceto.py:2654 | 2026-10-20 |
| RH3 | Abrir y guardar .3dm con capas, colores y bloques | Bloqueado | Media | Pedir permiso para instalar rhino3dm (paquete nuevo) y escribir el lector y escritor | sin código .3dm (grep); decisión del usuario (README › Decisiones) | 2026-10-20 |
| RH22 | Nube de puntos: reducir, contornos y secciones | Bloqueado | Media | Depende de F22 (importar nube de puntos), que espera decisión del usuario | sin código de nube de puntos (grep) | 2026-10-20 |
| RH19 | Modelado por subdivisión (SubD) | Bloqueado | Muy alta | Proyecto aparte: decidir alcance (junto con PolySplines y Forma de Fusion) antes de empezar | sin código SubD (grep) | 2026-10-20 |
| RH20 | Quad remesh y cuadrangulación | Bloqueado | Muy alta | Decidir si se hace; algoritmo pesado, base inversa de SubD | sin código (grep) | 2026-10-20 |
| NOV-brechas_rhino-1 | Notilus Composite para Rhino 8 (novedad automática) | Sin verificar | Media | Clasificar: complemento de terceros (naval o tuberías) sin equivalente en OmniCAD; decidir si importa | sin código relacionado; novedad agregada por scripts/novedades.py sin clasificar | 2026-10-20 |
| NOV-brechas_rhino-2 | Notilus Scantling para Rhino 8 (novedad automática) | Sin verificar | Media | Clasificar: complemento de terceros (naval o tuberías) sin equivalente en OmniCAD; decidir si importa | sin código relacionado; novedad agregada por scripts/novedades.py sin clasificar | 2026-10-20 |
| NOV-brechas_rhino-3 | Notilus Piping: tuberías y HVAC en Rhino (novedad automática) | Sin verificar | Media | Clasificar: complemento de terceros (naval o tuberías) sin equivalente en OmniCAD; decidir si importa | sin código relacionado; novedad agregada por scripts/novedades.py sin clasificar | 2026-10-20 |

## Grasshopper

Abierto 6 · Parcial 2. Especificación: [brechas_grasshopper.md](../brechas_grasshopper.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| GH7 | Publicar un grafo como comando con panel de campos | Abierto | Media | Todo: publicar el grafo en la tecla S con panel de entradas. | docs/grafo.md «Pendiente»; sin comando de grafo en omnicad/ui/comandos/ | 2026-10-20 |
| GH11 | Optimizador de parámetros (minimizar o maximizar un resultado) | Abierto | Media | Todo: ANALIZAR › Optimizar con rangos, objetivo y barra de progreso. | grep optimiz/galapagos sin coincidencias en clon/omnicad (scipy solo en restricciones/solver.py) | 2026-10-20 |
| GH4 | Lienzo de nodos en la interfaz (pestaña DISEÑO ALGORÍTMICO) | Abierto | Alta | Todo: arrastrar nodos, cables, vista previa, errores en rojo. | docs/grafo.md:4 y «Pendiente»; sin módulo de lienzo en omnicad/ui/ | 2026-10-20 |
| GH9 | Clústeres: agrupar nodos en un nodo propio reutilizable | Abierto | Alta | Todo; depende del lienzo (GH4). | docs/grafo.md «Pendiente»; sin código de clústeres en grafo/ | 2026-10-20 |
| GH10 | Bucles y campos escalares en el grafo | Abierto | Alta | Todo: nodos Repetir, campos y vista de isolíneas. | docs/grafo.md «Pendiente»; grep de bucle/campo en grafo/ sin resultados | 2026-10-20 |
| GH12 | Nodos de terceros mediante complementos | Abierto | Alta | Todo; depende del gestor de complementos B5 (no encontrado en el código). | grep complemento/plugin en clon/omnicad sin gestor de nodos | 2026-10-20 |
| GH3 | Catálogo de nodos (≈80 previstos) con tipos de puerto | Parcial | Media | Faltan solevación, revolución, barrido, divisiones de curva, matrices y lista de valores (64 nodos hoy). | omnicad/grafo/nodos_basicos.py, nodos_geometria.py, nodos_vectores.py (64 @nodo); tests/test_grafo.py::test_catalogo_por_categoria_y_bien_descripto; test_nodos_de_curvas_y_solidos | 2026-10-20 |
| GH6 | Nodo de script Python y nodo de expresión | Parcial | Media | Falta el nodo de script Python con editor; el de expresión ya existe. | omnicad/grafo/nodos_basicos.py:207 (nodo expresion); docs/grafo.md «Pendiente» | 2026-10-20 |

## KeyShot

Abierto 9 · Parcial 3 · Bloqueado 1. Especificación: [brechas_keyshot.md](../brechas_keyshot.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| KS2 | Entornos HDRI (.hdr), giro, brillo y biblioteca propia | Abierto | Media | Leer .hdr, lista con miniaturas, giro y brillo; hoy son degradados. | omnicad/nucleo/render_cpu.py:175-179 (ENTORNOS = degradados); grep hdr sin lector | 2026-10-20 |
| KS7 | Cámaras guardadas con apertura, enfoque y desenfoque (DOF) | Abierto | Media | Lista de cámaras con nombre del render, apertura, enfoque y desenfoque. | omnicad/ui/render.py:1404-1409 (solo perspectiva/ortográfica y focal); las vistas guardadas son del visor de DISEÑO (ui/ventana.py:2031) | 2026-10-20 |
| KS9 | Cola de render y lotes en segundo plano | Abierto | Media | Pestaña Cola en la galería: orden, estado, cancelar, abrir carpeta. | omnicad/ui/render.py (galería sin cola; grep cola sin resultados) | 2026-10-20 |
| KS10 | Variantes y configurador: renderizar todas las combinaciones | Abierto | Media | Unir configuraciones × aspectos × cámaras con el render y la cola. | omnicad/timeline/documento.py:168-170 (configuraciones existen); no están unidas al render | 2026-10-20 |
| KS-S3 | Enviar a KeyShot (export glTF/USD con materiales) | Abierto | Media | Comando que exporte con materiales y abra KeyShot (no verificado qué formatos lee). | omnicad/ui/puente.py existe; sin comando de envío | 2026-10-20 |
| KS-S2 | Configurador web: variantes en una página | Abierto | Alta | Todo; sigue de KS10 y de la salida GLB. | docs/brechas_keyshot.md:79 (pendiente a futuro); sin código | 2026-10-20 |
| KS12 | Materiales de fuente de luz (área, IES, foco) | Abierto | Muy alta | Pide trazado de rayos: no hay trazador (render rasterizado). | grep cycles/embree/pathtrac sin resultados en clon/omnicad | 2026-10-20 |
| KS13 | Vidrio grueso, gemas, cáusticas, subsuperficie, iluminación global | Abierto | Muy alta | Pide trazado de rayos o Cycles de Blender. | grep cycles/embree sin resultados; render_cpu.py es rasterizador (docstring l.1-12) | 2026-10-20 |
| KS14 | Imagen que se refina sola en el lienzo (muestreo progresivo) | Abierto | Muy alta | Pide trazador propio progresivo. | render_cpu.py renderiza por mosaicos una sola pasada | 2026-10-20 |
| KS5 | Biblioteca de materiales: arrastrar, favoritos, copiar aspecto | Parcial | Media | Faltan arrastrar y soltar la muestra sobre la pieza (en la vista y en el navegador) y «Copiar aspecto» entre piezas. En Fusion arrastrar es LA forma de aplicar un aspecto: cada suelta se aplica al instante (docs/brechas_aspecto.md). | omnicad/nucleo/aspectos.py (biblioteca, Mis aspectos, favoritos); tests/test_aspectos_api.py::test_menu_de_en_este_diseno_duplicar_renombrar_suprimir_mis_aspectos_y_favoritos; grep dragEnter/copiar_aspecto sin resultados | 2026-11-05 |
| KS8 | Giratoria (turntable) y explosionada en un clic | Parcial | Media | Falta la acción Giratoria (ángulo, duración, cuadros) en ANIMACIÓN. | omnicad/api/herramientas_animacion.py (auto_explode hecho); grep giratoria/turntable sin resultados | 2026-10-20 |
| KS-S1 | Exportar a GLB y USD para web y AR | Parcial | Alta | Falta USD (necesita escritor propio o pxr). | omnicad/io_archivos/gltf.py; io_archivos/exportar.py:19-20; commit c1c40f2 (2026-10-10) | 2026-10-20 |
| KS15 | «AI Shots»: restilizar y generar variantes con modelo local | Bloqueado | Muy alta | Espera decisión del usuario: no gastar en APIs y exige un modelo local grande. | docs/brechas_keyshot.md:72 (decisión del usuario); sin código | 2026-10-20 |

## V-Ray

Abierto 10 · Parcial 1. Especificación: [brechas_vray.md](../brechas_vray.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| VR1 | Mezcla de luces (Light Mix) después del render | Abierto | Media | Panel Luces con intensidad y color por luz sin re-renderizar. | render_cpu.py:993 (n_luces = 1 o 3 fijas, sin acumulado por luz) | 2026-10-20 |
| VR2 | Postproceso no destructivo (exposición, curva, bloom, viñeta) | Abierto | Media | Todo el postproceso sobre la imagen en flotante; la exposición hoy es parámetro previo. | render_cpu.py:172,235 (exposicion EV y ACES dentro del render, no posterior) | 2026-10-20 |
| VR6 | Sol y cielo físicos por lugar, fecha y hora | Abierto | Media | Cálculo de sol/cielo, nubes y niebla; hoy los entornos son degradados. | render_cpu.py:175-179 | 2026-10-20 |
| VR7 | Regiones de render con forma propia | Abierto | Media | Dibujar una región en el lienzo y renderizar solo eso. | grep region en ui/render.py sin resultados | 2026-10-20 |
| VR8 | Material dibujo animado (Toon) y de borde | Abierto | Media | Tipo de material con contorno y bandas de color. | grep toon sin resultados en clon/omnicad | 2026-10-20 |
| VR9 | Dispersión (Scatter) de copias sobre una superficie | Abierto | Media | Reparto aleatorio con densidad, escala y giro; ampliar el patrón. | grep scatter/dispersión sin resultados | 2026-10-20 |
| VR3 | Elementos de render (pases) y máscaras por píxel | Abierto | Alta | Pases difuso, reflejo, sombra, oclusión, normales, profundidad e ID. | grep de pases en render_cpu.py sin resultados | 2026-10-20 |
| VR5 | Corte en el render (Clipper) con tapa de color | Abierto | Alta | Control «Clipper» en RENDERIZAR (ventana y render_image) con tapa de color; el motor de CPU ya recorta por planos y dibuja la tapa. | omnicad/nucleo/render_estilos.py (recortar, capas_a_objetos) y get_viewport_image con section_view; grep clipper en ui/render.py sin resultados | 2026-10-20 |
| VR12 | Reducción de ruido (OIDN) | Abierto | Alta | Solo con trazador propio; con Cycles ya viene. | sin trazador de rayos: no hay ruido que reducir | 2026-10-20 |
| VR11 | Iluminación global, cáusticas, IES, subsuperficie, pelo | Abierto | Muy alta | Pide trazado de rayos (Cycles de Blender o trazador propio). | grep cycles sin resultados | 2026-10-20 |
| VR4 | Cámara física: ISO, obturador, f, auto-exposición, DOF | Parcial | Media | Faltan ISO, obturador, f, exposición automática, balance de blancos y DOF. | render_cpu.py:171-172 (focal y exposición EV ya existen) | 2026-10-20 |

## Capa para agentes (paquetes del plan)

Abierto 1. Especificación: [plan_mcp_cli.md](../plan_mcp_cli.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| PAQ-H5 | Hito 5: carpeta complementos/ con registrar(api) | Abierto | Alta | Opcional; solo si el usuario lo pide. Es la misma tarea que B5/GH12. | no existe complementos/ en el repo | 2026-10-20 |

## Asistente IA (chat dentro de la app)

Parcial 2. Especificación: [plan_asistente_ia.md](../plan_asistente_ia.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| IA-2 | Proveedores por API: Anthropic Messages y OpenAI compatible (OpenAI, OpenRouter, Ollama) | Parcial | Media | Queda: streaming SSE (hoy la respuesta llega completa); prueba real con Ollama (no está instalado en esta PC); devolver los bloques de pensamiento de Claude entre vueltas; prueba paga solo con OK de Gerardo. | omnicad/asistente/proveedores/anthropic.py; omnicad/asistente/proveedores/openai_compat.py; tests/test_asistente_proveedores.py | 2026-10-25 |
| IA-11 | Todas las herramientas desde el chat del asistente, de forma eficiente (índice en el prompt, buscar_herramientas por consulta, find_tools/call_tool en el MCP de los CLI, caché del prompt) | Parcial | Alta | Queda: medir los tokens por paso con el uso que reporta la API (Anthropic u OpenAI: gasta, solo con OK de Gerardo); Codex informa 56,8 mil de entrada en un pedido de una vuelta, que suma su propio prompt de sistema (lo nuestro mide 19,2 mil). | omnicad/asistente/herramientas.py; omnicad/servidor_mcp/servidor.py; tests/test_asistente_alcance.py; prueba real con Codex del 2026-10-25 | 2026-10-25 |

## SolidCraft

Abierto 9 · Parcial 3 · Bloqueado 1. Especificación: [brechas_solidcraft.md](../brechas_solidcraft.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| SC14 | Importar .FCStd de FreeCAD | Abierto | Media | Leer el ZIP y los .brp con BRepTools.Read, con topes de seguridad. | grep FCStd sin resultados | 2026-10-20 |
| SC15 | Exportar URDF desde un ensamble con uniones | Abierto | Media | Eslabones, masa, inercia y juntas con límites. | grep urdf sin resultados en clon/omnicad | 2026-10-20 |
| SC2 | Robustez con semilla: generador de diseños y minimizador | Abierto | Alta | Generador aleatorio, chequeo de volumen, CLI omnicad fuzz. | grep fuzz sin resultados; solo tortura manual (tests/test_hallazgos_tortura.py) | 2026-10-20 |
| SC6 | Conjuntos de contacto en uniones y estudio de movimiento | Abierto | Alta | Implementar el contacto; el botón sigue grisado. | omnicad/ui/cinta.py:65 (grisado) | 2026-10-20 |
| SC8 | Uniones con relación: leva y tornillo | Abierto | Alta | Leva (cuchilla, rodillo, plano) y tornillo; hoy solo engranaje y cremallera. | omnicad/api/herramientas_ensamble.py:645 (create_motion_link solo ratio) | 2026-10-20 |
| SC11 | Ratón 3D (SpaceMouse) con preferencias por eje | Abierto | Alta | Leer HID (hidapi pide permiso o ctypes) y mapear desplazar, zoom, giro. | grep spacemouse/hidapi sin resultados | 2026-10-20 |
| SC12 | Chapa: Perforar | Abierto | Alta | Operación nueva. Snap Fit y Apoyo pasaron a PLA-1 y PLA-2. | grep perforar sin resultados | 2026-11-01 |
| SC17 | Mallado estanco y rápido, con evaluación en GPU | Abierto | Alta | Medir primero; si es cuello de botella, pasar a Rust. | nucleo/malla.py:952 (BRepMesh de OpenCascade) | 2026-10-20 |
| SC3 | Nombres persistentes por historia del kernel | Abierto | Muy alta | Usar Modified/Generated de OpenCascade para nombrar caras y aristas. Ejemplo (2026-10-24): borrar un agujero rompe el empalme de las aristas paralelas a Z que viene después (REFERENCE_LOST). | omnicad/timeline/entidades.py (firma geométrica tolerante); sin BRepTools_History | 2026-10-20 |
| SC1 | Suite de piezas de referencia con valores analíticos | Parcial | Media | Faltan esperado.json con fórmulas cerradas (Pappus, Steiner) y la herramienta run_reference_tests. | tests/test_paridad_motor.py (paridad OpenCascade vs OmniKernel, ~55 casos); caso_paridad_motor.py | 2026-10-20 |
| SC5 | Configuraciones: tabla de filas con parámetros, supresiones y material | Parcial | Media | Falta material/aspecto por cuerpo en la fila y robustez al renombrar (la herramienta manage_configurations ya existe). | omnicad/timeline/documento.py:168-170,403; tests/test_administrar.py::test_configuraciones_aplican_parametros_y_supresion | 2026-10-20 |
| SC7 | Análisis del estudio de movimiento: gráficos, rastro, choques | Parcial | Media | Faltan gráficos de valor, velocidad y aceleración y el rastro de un punto. | omnicad/api/herramientas_ensamble.py:703-714 (motion_study con check_interference por valor); tests/test_api_ensamble.py:230 | 2026-10-20 |
| SC16 | Pruebas de mutación (mutmut) juzgadas por SC1 y SC2 | Bloqueado | Media | Espera permiso para instalar mutmut y que existan SC1 y SC2. | sin mutmut en pyproject.toml | 2026-10-20 |

## Otros CAD libres

Abierto 1 · Parcial 1. Especificación: [brechas_cad_libres.md](../brechas_cad_libres.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| CL1 | Cambio de agente con vista previa y control de revisión | Parcial | Media | Queda: control de revisión del documento (expected_revision) para los agentes externos del puente en vivo. El Asistente de la app ya muestra el plan y pide Aplicar antes de cambiar (IA-5). | omnicad/ui/asistente.py (_Tarjeta); tests/test_asistente_ui.py; grep revision/expected_revision sin resultados en api/protocolo_puente.py y ui/puente.py | 2026-10-25 |
| CL3 | Tutoriales reproducibles con capítulos y cámara | Abierto | Media | Todo. | grep tutorial sin resultados | 2026-10-20 |

## C++

Bloqueado 1. Especificación: [plan_cpp.md](../plan_cpp.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| CPP-F2 | Fase 2 spike C++: módulo que recibe un TopoDS_Shape de OCP | Bloqueado | Media | Falta permiso para bajar cabeceras OCCT 8.0 y pybind11 >= 3. | docs/plan_cpp.md:75-82 | 2026-10-20 |
