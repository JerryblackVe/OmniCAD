# Faltantes

Funciones que todavía no existen. La especificación de cada ID está en el `docs/brechas_*.md` que nombra cada sección. Método y columnas: [README](README.md).

Solo lo que falta resolver: al resolverse, la fila se borra. Verificado contra el código el 2026-10-20. Total 171: Abierto 122 · Parcial 29 · Bloqueado 17 · Sin verificar 3.

## Pendientes generales

Abierto 54 · Parcial 2 · Bloqueado 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| P-25c2 | c) «Guardar como malla»: Tipo (Fabricación/Exportar/Utilidad de impresión) y Aplicación | Abierto | Baja | Siguen sin hacer. | omnicad/ui/guardar_malla.py | 2026-10-20 |
| P-29-6 | Pieza de calibración de holguras | Abierto | Baja | Sin programar. | sin función en omnicad/ | 2026-10-20 |
| P-2d | Selector de idioma en Preferencias y test de cadenas sin traducir | Abierto | Media | Sin selector ni test que falle por cadena sin traducción; AGENTS.md aún exige TODO en español. | omnicad/ui/preferencias.py sin clave de idioma | 2026-10-20 |
| P-8c | Primer arranque guiado dentro de la app (idioma, conectar agentes con un botón) | Abierto | Media | Hoy conectar agentes es una tarea opcional del instalador; la app no tiene asistente de primer arranque. | instalador/windows/omnicad.iss:62,79 (tarea «agentes»); grep de «primer arranque» en omnicad/: sin resultados | 2026-10-20 |
| P-9f | Temas con tipografía propia y fondo con imagen en el visor | Abierto | Media | Los temas solo definen colores; la fuente está fija en el QSS y no hay imagen de fondo. | omnicad/ui/temas.py:208 (font-family fija «Segoe UI») | 2026-10-20 |
| P-12e | Página web del proyecto y GitHub Actions que la actualice con cada versión | Abierto | Media | No existe la página; comparte las Actions por versión con el pendiente 8. | .github/workflows/instaladores.yml (solo instaladores) | 2026-10-20 |
| P-12j | Grupos en la línea de tiempo | Abierto | Media | Los grupos existen solo en el navegador de cuerpos; el timeline no tiene carpetas. | omnicad/ui/panel_timeline.py sin grupos (grep «grupo»: solo TIPOS_UNION); coincide con SC9 | 2026-10-20 |
| P-22a | Modo seguro (contador de arranques fallidos) | Abierto | Media | Sin programar. | grep «modo seguro» y «arranques fallidos» en omnicad/: sin resultados | 2026-10-20 |
| P-22b | Diario del solver de bocetos (grabar y reproducir) | Abierto | Media | Sin programar; serviría de corpus para R4. | omnicad/restricciones/ sin diario | 2026-10-20 |
| P-23c3 | c) Grupos anidados (mover un grupo dentro de otro) | Abierto | Media | Opción grisada: sin grupos anidados. | omnicad/ui/acciones_navegador.py | 2026-10-20 |
| P-23e2 | e) Ocultar perfil, Mostrar cota, Ocultar proyectadas y construcción fuera del editor | Abierto | Media | El visor general no dibuja esas cuatro capas; grisadas fuera del editor. | omnicad/ui/acciones_navegador.py:281-288 | 2026-10-20 |
| P-25d | d) SÓLIDO > MODIFICAR: Organizar, Simplificar (submenú vacío), Administrar materiales | Abierto | Media | Organizar no existe; Simplificar y Administrar materiales siguen grisados. | omnicad/ui/cinta.py:105-106 (_sub vacío, _i sin clave) | 2026-10-20 |
| P-25f | f) INSPECCIONAR: Sustainability Insights, análisis de pila de fijadores, grupos de caras de malla (grisado) | Abierto | Media | Los dos primeros no existen; el tercero está grisado aunque generate_face_groups existe. | omnicad/ui/cinta.py; herramienta generate_face_groups | 2026-10-20 |
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
| P-25e | e) ENSAMBLAR: Duplicar con uniones, Restricción de componentes, Relación de tangente | Abierto | Alta | No existen en la cinta. | omnicad/ui/cinta.py (grep: sin resultados) | 2026-10-20 |
| P-25e2 | e) Conjuntos de contacto y «Activar todos los contactos» (grisados) | Abierto | Alta | Botones grisados; misma brecha que SC6. | omnicad/ui/cinta.py:62 | 2026-10-20 |
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
| P-11h | d) Historial de operaciones del .f3d (traducir el timeline de Fusion) | Abierto | Muy alta | Hoy los cuerpos entran como operación base; el historial no se lee. | omnicad/io_archivos/abrir_externo.py:119 | 2026-10-20 |
| P-11i | Referencias externas de un .f3z (diseños hijos referenciados) | Abierto | Muy alta | Se identifican las ocurrencias externas pero no se decodifica su disposición interna. | PROJECT_LOG.md:32 (upgrades3, SIN RESOLVER) | 2026-10-20 |
| P-25i | i) SÓLIDO > CREAR: Crear forma, Derivar y placa de circuito impreso (grisados) | Abierto | Muy alta | Siguen grisados; Forma depende de P-25j y la placa pide espacio ELECTRÓNICA. | omnicad/ui/cinta.py:83,96 | 2026-10-20 |
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

## Hallazgos de pruebas de uso

Abierto 1 · Parcial 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| H-19 | Vínculo de movimiento solo lineal | Abierto | Alta | Vínculo no lineal para biela-manivela; depende de resolver los lazos cerrados (H-18). | api/herramientas_ensamble.py:642-659 (valor unión 2 = ratio × unión 1) | 2026-10-20 |
| H-4 | Insertar: derivación hecha; faltan Duplicar con uniones y catálogo | Parcial | Media | Falta «Duplicar con uniones» y un catálogo local de piezas estándar (sin servicios en línea). | ui/cinta.py:56; ui/comandos/derivacion.py:16; api/herramientas_documento.py:322 (insert_derive); tests/test_derivacion.py; sin «duplicar con uniones» en omnicad/ | 2026-10-20 |
| H-6 | Menú del timeline: faltan Configurar, Desactivar, conjunto y Buscar en ventana | Parcial | Media | Faltan Crear conjunto de selección, Configurar, Desactivar operaciones y Buscar en la ventana. | ui/panel_timeline.py:196-232; tests/test_hallazgos_ui.py::test_menu_del_timeline_es_distinto_para_boceto_operacion_y_union (marca Configurar y Desactivar fuera de alcance) | 2026-10-20 |

## Fusion 360

Abierto 3 · Bloqueado 1. Especificación: [brechas_fusion.md](../brechas_fusion.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| FU-7 | Configuración del timeline (engranaje abajo a la derecha) | Abierto | Baja | Menú de configuración de la línea de tiempo | ui/panel_timeline.py: sin ajustes ni engranaje (grep) | 2026-10-20 |
| FU-1 | Boceto 3D con tríada para dibujar fuera del plano | Abierto | Muy alta | Curvas con marco 3D propio, solver y perfiles por plano; la opción sigue grisada | ui/modo_boceto.py:139 (opción «Boceto 3D» con False,False); PROJECT_LOG.md:40 | 2026-10-20 |
| FU-8 | Historial de pasos al abrir un .f3d | Abierto | Muy alta | Descifrar el flujo de diseño de Fusion o traducirlo con su API pública | io_archivos/f3d_nativo.py:24 (no trae historial); integraciones/fusion/OmniCADPuente (parámetros con Fusion) | 2026-10-20 |
| FU-12 | Simulación, Fabricación y Forma (T-Splines) | Bloqueado | Muy alta | Decidir dependencias (CalculiX, Gmsh) y alcance antes de empezar | ui/cinta.py:244 (espacios grisados); sin código FEM, CAM ni T-Splines (grep) | 2026-10-20 |

## FreeCAD

Abierto 5 · Parcial 7 · Bloqueado 4. Especificación: [brechas_freecad.md](../brechas_freecad.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| F6 | Rebanar: N cortes paralelos como curvas, caras o láminas | Abierto | Media | Operación y comando de serie de cortes paralelos con salida a bocetos o cuerpos finos | sin código (grep rebanar/slice); existen dividir_cuerpo y cortar_plano de malla | 2026-10-20 |
| F10 | Mapa de desviación entre cuerpos o contra una malla | Abierto | Media | Comando INSPECCIONAR con escala de color, mín/máx y punto bajo el cursor | sin código (grep desviación solo halla parámetros de teselado) | 2026-10-20 |
| F15 | Parámetros desde hoja CSV/XLSX | Abierto | Media | Importar y exportar parámetros y familias de piezas desde hoja de cálculo | sin código de importación (api/herramientas_parametros.py); ui/administrar.py solo exporta la lista de materiales; timeline/documento.py:168 tabla de configuraciones | 2026-10-20 |
| F11 | Ajustar primitivas a una malla escaneada | Abierto | Alta | Detectar planos, cilindros y esferas y rearmar un sólido paramétrico | sin código (grep); existen grupos_caras y convertir_malla como base | 2026-10-20 |
| F13 | Estructura de perfiles con ingletes y lista de cortes | Abierto | Alta | Perfiles estándar a lo largo de rutas con ingletes automáticos y lista de cortes | sin código (grep); nucleo/superficies.py:525 aclara que no hay esquinas a inglete | 2026-10-20 |
| F1 | Engranajes, cremallera y rueda de cadena | Parcial | Baja | Polea dentada (correa); valores ISO 606 de la rueda de cadena por verificar | ed0c4dc; nucleo/engranajes.py; timeline/ops_engranaje.py; ui/comandos/engranaje.py; api create_gear, create_gear_pair, create_rack, create_sprocket; tests/test_engranajes.py; tests/test_api_engranajes.py | 2026-10-20 |
| F3 | Patrón en puntos y en ruta con giro | Parcial | Baja | Vista previa de las copias como fantasmas | c606f26; api point_pattern, path_pattern; ui/comandos/patrones.py; tests/test_patrones_avanzados.py::test_transformaciones_en_puntos; ::test_ruta_con_giro_progresivo | 2026-10-20 |
| F18 | Multitransformación | Parcial | Baja | Transformación de escala (Scaled de FreeCAD) | c606f26; timeline/ops_solido.py:667 OpMultitransformar; api multi_transform; tests/test_patrones_avanzados.py::test_multitransformar_cuerpos_patron_y_simetria | 2026-10-20 |
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
| B4 | Vectorizar imagen: vista previa y esquinas | Parcial | Baja | Detección de esquinas e ignorar manchas en el diálogo; vista previa propia de las curvas | 32c9e2d; io_archivos/vectorizar.py:93; ui/comandos/insertar.py:125; api trace_image; tests/test_texto_vectores.py | 2026-10-20 |
| B2 | Revisión de impresión 3D (espesor, voladizos, aristas filosas) | Parcial | Media | Lista con clic por problema y mapa de color sobre la pieza | 4fca4c7; nucleo/revision.py revisar_impresion; api check_printability; tests/test_revision.py; tests/test_api_revision.py | 2026-10-20 |
| B3 | Exportar FBX y USD (glTF ya está) | Parcial | Alta | Escritor de FBX (sin especificación pública) y de USD (pide la biblioteca pxr) | 8e1a1fe; io_archivos/gltf.py (docstring: FBX y USD no se escriben); tests/test_gltf.py | 2026-10-20 |
| B7 | Imán (snapping) completo en el visor | Parcial | Alta | Barra de imanes: vértice, arista, cara, centro de arista, perpendicular, varios a la vez | ui/manipuladores.py:51,297-347 (enganche a centro de cara, esquinas y puntos medios al ubicar) | 2026-10-20 |
| B15 | Nodos de geometría: campos, atributos, instancias, zonas de repetición | Parcial | Muy alta | Campos, atributos, instancias con realizar y zonas de repetición y simulación | omnicad/grafo/ (árboles de datos, nodos, horneado); docs/grafo.md; api run_graph, bake_graph, list_graph_nodes; tests/test_grafo.py; tests/test_api_grafo.py | 2026-10-20 |
| B16 | Modo edición de malla (extruir, inset, bisel, cuchillo) | Bloqueado | Muy alta | Solo si el usuario lo pide: modelado de malla, fuera de lo que hace Fusion | sin código (grep); la malla es solo de triángulos (nucleo/malla.py:2405) | 2026-10-20 |
| B17 | Simulación de cuerpo rígido | Bloqueado | Muy alta | Elegir un motor de física (dependencia nueva, pedir permiso) y hornear a animación | sin código de física (grep); espacio SIMULACIÓN grisado (ui/cinta.py:244) | 2026-10-20 |

## Rhino 8

Abierto 9 · Parcial 3 · Bloqueado 4 · Sin verificar 3. Especificación: [brechas_rhino.md](../brechas_rhino.md).

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

Abierto 10 · Parcial 3 · Bloqueado 1. Especificación: [brechas_keyshot.md](../brechas_keyshot.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| KS1 | Preajustes de iluminación y calidad del render | Abierto | Media | Selector de 5 preajustes en Configuración de escena. | omnicad/ui/render.py:1558 (PRESETS solo de tamaño) | 2026-10-20 |
| KS2 | Entornos HDRI (.hdr), giro, brillo y biblioteca propia | Abierto | Media | Leer .hdr, lista con miniaturas, giro y brillo; hoy son degradados. | omnicad/nucleo/render_cpu.py:175-179 (ENTORNOS = degradados); grep hdr sin lector | 2026-10-20 |
| KS7 | Cámaras guardadas con apertura, enfoque y desenfoque (DOF) | Abierto | Media | Lista de cámaras con nombre del render, apertura, enfoque y desenfoque. | omnicad/ui/render.py:1404-1409 (solo perspectiva/ortográfica y focal); las vistas guardadas son del visor de DISEÑO (ui/ventana.py:2031) | 2026-10-20 |
| KS9 | Cola de render y lotes en segundo plano | Abierto | Media | Pestaña Cola en la galería: orden, estado, cancelar, abrir carpeta. | omnicad/ui/render.py (galería sin cola; grep cola sin resultados) | 2026-10-20 |
| KS10 | Variantes y configurador: renderizar todas las combinaciones | Abierto | Media | Unir configuraciones × aspectos × cámaras con el render y la cola. | omnicad/timeline/documento.py:168-170 (configuraciones existen); no están unidas al render | 2026-10-20 |
| KS-S3 | Enviar a KeyShot (export glTF/USD con materiales) | Abierto | Media | Comando que exporte con materiales y abra KeyShot (no verificado qué formatos lee). | omnicad/ui/puente.py existe; sin comando de envío | 2026-10-20 |
| KS-S2 | Configurador web: variantes en una página | Abierto | Alta | Todo; sigue de KS10 y de la salida GLB. | docs/brechas_keyshot.md:79 (pendiente a futuro); sin código | 2026-10-20 |
| KS12 | Materiales de fuente de luz (área, IES, foco) | Abierto | Muy alta | Pide trazado de rayos: no hay trazador (render rasterizado). | grep cycles/embree/pathtrac sin resultados en clon/omnicad | 2026-10-20 |
| KS13 | Vidrio grueso, gemas, cáusticas, subsuperficie, iluminación global | Abierto | Muy alta | Pide trazado de rayos o Cycles de Blender. | grep cycles/embree sin resultados; render_cpu.py es rasterizador (docstring l.1-12) | 2026-10-20 |
| KS14 | Imagen que se refina sola en el lienzo (muestreo progresivo) | Abierto | Muy alta | Pide trazador propio progresivo. | render_cpu.py renderiza por mosaicos una sola pasada | 2026-10-20 |
| KS5 | Biblioteca de materiales: arrastrar, favoritos, copiar aspecto | Parcial | Media | Faltan arrastrar y soltar sobre la pieza y «Copiar aspecto» entre piezas. | omnicad/nucleo/aspectos.py (biblioteca, Mis aspectos, favoritos); tests/test_aspectos_api.py::test_menu_de_en_este_diseno_duplicar_renombrar_suprimir_mis_aspectos_y_favoritos; grep dragEnter/copiar_aspecto sin resultados | 2026-10-20 |
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

## SolidCraft

Abierto 12 · Parcial 3 · Bloqueado 1. Especificación: [brechas_solidcraft.md](../brechas_solidcraft.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| SC9 | Timeline: carpetas de pasos y copiar/pegar pasos | Abierto | Media | Todo. | grep carpeta/copiar/pegar en ui/panel_timeline.py sin resultados | 2026-10-20 |
| SC13 | Comparar cuerpos: desviación con mapa de color | Abierto | Media | Todo. | grep comparar/desviación entre cuerpos sin resultados | 2026-10-20 |
| SC14 | Importar .FCStd de FreeCAD | Abierto | Media | Leer el ZIP y los .brp con BRepTools.Read, con topes de seguridad. | grep FCStd sin resultados | 2026-10-20 |
| SC15 | Exportar URDF desde un ensamble con uniones | Abierto | Media | Eslabones, masa, inercia y juntas con límites. | grep urdf sin resultados en clon/omnicad | 2026-10-20 |
| SC2 | Robustez con semilla: generador de diseños y minimizador | Abierto | Alta | Generador aleatorio, chequeo de volumen, CLI omnicad fuzz. | grep fuzz sin resultados; solo tortura manual (tests/test_hallazgos_tortura.py) | 2026-10-20 |
| SC6 | Conjuntos de contacto en uniones y estudio de movimiento | Abierto | Alta | Implementar el contacto; el botón sigue grisado. | omnicad/ui/cinta.py:62 (grisado) | 2026-10-20 |
| SC8 | Uniones con relación: leva y tornillo | Abierto | Alta | Leva (cuchilla, rodillo, plano) y tornillo; hoy solo engranaje y cremallera. | omnicad/api/herramientas_ensamble.py:645 (create_motion_link solo ratio) | 2026-10-20 |
| SC11 | Ratón 3D (SpaceMouse) con preferencias por eje | Abierto | Alta | Leer HID (hidapi pide permiso o ctypes) y mapear desplazar, zoom, giro. | grep spacemouse/hidapi sin resultados | 2026-10-20 |
| SC12 | Plástico: Snap Fit y Reposo; Chapa: Perforar | Abierto | Alta | Tres operaciones nuevas; Encaje a presión figura grisado. | omnicad/ui/cinta.py:150 (Encaje a presión grisado); grep perforar sin resultados | 2026-10-20 |
| SC17 | Mallado estanco y rápido, con evaluación en GPU | Abierto | Alta | Medir primero; si es cuello de botella, pasar a Rust. | nucleo/malla.py:952 (BRepMesh de OpenCascade) | 2026-10-20 |
| SC3 | Nombres persistentes por historia del kernel | Abierto | Muy alta | Usar Modified/Generated de OpenCascade para nombrar caras y aristas. | omnicad/timeline/entidades.py (firma geométrica tolerante); sin BRepTools_History | 2026-10-20 |
| SC4 | Solver de bocetos constructivo antes del numérico | Abierto | Muy alta | Colocación exacta por construcción y grupos rígidos antes de Levenberg-Marquardt. | omnicad/restricciones/solver.py:14,687-690 (solo least_squares lm) | 2026-10-20 |
| SC1 | Suite de piezas de referencia con valores analíticos | Parcial | Media | Faltan esperado.json con fórmulas cerradas (Pappus, Steiner) y la herramienta run_reference_tests. | tests/test_paridad_motor.py (paridad OpenCascade vs OmniKernel, ~55 casos); caso_paridad_motor.py | 2026-10-20 |
| SC5 | Configuraciones: tabla de filas con parámetros, supresiones y material | Parcial | Media | Falta material/aspecto por cuerpo en la fila y robustez al renombrar (la herramienta manage_configurations ya existe). | omnicad/timeline/documento.py:168-170,403; tests/test_administrar.py::test_configuraciones_aplican_parametros_y_supresion | 2026-10-20 |
| SC7 | Análisis del estudio de movimiento: gráficos, rastro, choques | Parcial | Media | Faltan gráficos de valor, velocidad y aceleración y el rastro de un punto. | omnicad/api/herramientas_ensamble.py:703-714 (motion_study con check_interference por valor); tests/test_api_ensamble.py:230 | 2026-10-20 |
| SC16 | Pruebas de mutación (mutmut) juzgadas por SC1 y SC2 | Bloqueado | Media | Espera permiso para instalar mutmut y que existan SC1 y SC2. | sin mutmut en pyproject.toml | 2026-10-20 |

## Otros CAD libres

Abierto 2. Especificación: [brechas_cad_libres.md](../brechas_cad_libres.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| CL1 | Cambio de agente con vista previa y control de revisión | Abierto | Media | Comparar la revisión del documento antes de aplicar en modo en vivo. | grep revision/expected_revision sin resultados en api/protocolo_puente.py y ui/puente.py | 2026-10-20 |
| CL3 | Tutoriales reproducibles con capítulos y cámara | Abierto | Media | Todo. | grep tutorial sin resultados | 2026-10-20 |

## C++

Bloqueado 1. Especificación: [plan_cpp.md](../plan_cpp.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| CPP-F2 | Fase 2 spike C++: módulo que recibe un TopoDS_Shape de OCP | Bloqueado | Media | Falta permiso para bajar cabeceras OCCT 8.0 y pybind11 >= 3. | docs/plan_cpp.md:75-82 | 2026-10-20 |
