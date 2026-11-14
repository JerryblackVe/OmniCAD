# Después

Prioridad 2, **congelada** (Gerardo, 2026-11-13): render, animación, simulación, malla, plástico, chapa, dibujo, asistente de IA, escaneo, extensiones y parecidos. No se toma ningún ítem de acá salvo que Gerardo lo descongele o lo pida por nombre. Las ideas nuevas de prioridad 2 entran directo, con ID y sin sesión. Excepción: un bug que cierra la app o rompe algo de prioridad 1 va a `bugs.md`.

Mismas columnas que las otras listas ([README](README.md)); no ordena nada: la cola es [ahora.md](ahora.md). Al resolverse, la fila se borra.

Total 224: Abierto 138 · Parcial 47 · Bloqueado 32 · Sin verificar 7 (2026-11-13: lote de E11, B-414, B-415 y P-155; 2026-11-13: creado por el cambio 3 de la reorganización).

## Bugs › Abiertos y parciales

Abierto 1 · Bloqueado 1 · Sin verificar 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| B-414 | Registro de uso › con poco disco se pausa sin ningún aviso en pantalla (la PC de Gerardo ya pasó de 0,26 a 7,96 GB libres) | Abierto | Baja | Avisar en pantalla cuando se pausa | evidencias/reportes_pc/2026-11-13_tanda1/06 (E11) | 2026-11-13 |
| B-415 | Arranque › OmniCAD arrancó minimizado las 2 veces que E11 lo lanzó desde su shell; con doble clic no pasa | Sin verificar | Baja | Solo anotado; confirmar | evidencias/reportes_pc/2026-11-13_tanda1 (E11) | 2026-11-13 |
| P-155 | Proceso aparte › si el trabajador no puede escribir (disco lleno), mostrar un error en vez de «Calculando…» para siempre (la rosca quedó colgada) | Abierto | Baja | Error claro y salida del estado «Calculando» | evidencias/reportes_pc/2026-11-13_tanda1/01, tanda2/03 (E11) | 2026-11-13 |
| B-240 | RENDERIZAR › interfaz corrupta, controles invertidos y visor negro | Sin verificar | Media | Reproducir y hallar la causa en AG-3. | `docs/auditoria_renderizar.md` | 2026-11-08 |
| P-1c | Wayland nativo: menús emergentes se cierran solos | Bloqueado | Alta | Reproducir y probar el arreglo en Linux nativo (P-1b). | omnicad/ui/__init__.py:11-19 | 2026-10-20 |
| B-378 | Retícula volumétrica lenta con valores por defecto | Abierto | Media | Perfilar y acelerar o estimar el tiempo antes de calcular. | `clon/tests/corpus_caza/b378_reticula_lenta.json`; `omnicad/api/herramientas_solido_extra.py:412` | 2026-11-13 |
| B-482 | Plástico (P2, prioridad 2): Saliente D100 en una pared de 60 y h1000 sin aviso; Nervio de grosor 100 sin aviso; desmoldeo de nervio −3° falla con «¿ángulo demasiado grande?» (con flip entra: signo inconsistente); la regla creada como «R1» aparece como «ABS 2 mm» | Abierto | Media | Validar y nombrar como Fusion | E11, `evidencias/reportes_pc/2026-11-14_e11_esfuerzo_empalme_chaflan/resumen.md` | 2026-11-14 |
| B-483 | Chapa (P2, prioridad 2): la regla acepta radio de plegado 0 pero la Pestaña base lo rechaza; relieve de 100 mm en una placa de 60 sin aviso; profundidad de relieve 0 entra; espesor 1000 y separación 100 sin aviso | Abierto | Baja | Validar como Fusion | E11, `evidencias/reportes_pc/2026-11-14_e11_esfuerzo_empalme_chaflan/resumen.md` (Tanda 3) | 2026-11-14 |

## Faltantes › Pendientes generales

Abierto 40 · Bloqueado 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| P-2d | Selector de idioma en Preferencias y test de cadenas sin traducir | Abierto | Media | Sin selector ni test que falle por cadena sin traducción; AGENTS.md aún exige TODO en español. | omnicad/ui/preferencias.py sin clave de idioma | 2026-10-20 |
| P-8c | Primer arranque guiado: idioma y conexión de agentes | Abierto | Media | Crear el asistente de primer arranque. | instalador/windows/omnicad.iss:62,79 (tarea «agentes»); sin asistente en omnicad/ | 2026-10-20 |
| P-9f | Temas con tipografía propia y fondo con imagen en el visor | Abierto | Media | Los temas solo definen colores; la fuente está fija en el QSS y no hay imagen de fondo. | omnicad/ui/temas.py:208 (font-family fija «Segoe UI») | 2026-10-20 |
| P-12e | Página web del proyecto y GitHub Actions que la actualice con cada versión | Abierto | Media | No existe la página; comparte las Actions por versión con el pendiente 8. | .github/workflows/instaladores.yml (solo instaladores) | 2026-10-20 |
| P-25d | d) SÓLIDO > MODIFICAR: Organizar y Administrar materiales | Abierto | Media | Organizar no existe; Administrar materiales sigue grisado. Simplificar pasó a PLA-9. | omnicad/ui/cinta.py:114 (_i sin clave) | 2026-11-01 |
| P-27-13 | Disposición en la cama y abrir directo en el slicer | Abierto | Media | Sin programar. | grep en omnicad/ nucleo/api/timeline: sin función equivalente | 2026-10-20 |
| P-27-14 | Vista en realidad aumentada con código QR | Abierto | Media | Sin programar. | grep en omnicad/ nucleo/api/timeline: sin función equivalente | 2026-10-20 |
| P-27-15 | Video de presentación: giro 360° y recorrido de cámara en MP4 | Abierto | Media | Sin programar. | omnicad/api/herramientas_animacion.py:487 (solo gif/png); sin turntable | 2026-10-20 |
| P-28b | Galería con imágenes de referencia y explicación corta por tipo, con vista en vivo | Abierto | Media | Hay un diálogo de engranaje pero sin galería de tipos ni explicaciones. | omnicad/ui/comandos/engranaje.py | 2026-10-20 |
| P-29-1 | Perfil de impresora y material (cama aviso «no entra», holguras, encogimiento) | Abierto | Media | Sin programar. | grep «impresora/cama/boquilla» en omnicad/: sin perfil | 2026-10-20 |
| P-29-4 | Bolsillos de armado (imanes, insertos, tuercas, rodamientos) | Abierto | Media | Sin programar. | omnicad/nucleo/fijaciones.py sin bolsillos de armado | 2026-10-20 |
| P-29-5 | Agujeros que imprimen bien (gota, puentes, compensación) | Abierto | Media | Sin programar. | omnicad/api/herramientas_solido.py create_hole sin gota | 2026-10-20 |
| P-2a | Traducir la interfaz Qt al inglés (.ts / QTranslator) | Abierto | Alta | No hay catálogos .ts/.qm ni selector de idioma; solo textos en español. | omnicad/ui/captura.py es el único uso de QTranslator (botones estándar de Qt); sin archivos *.ts ni *.qm en clon/ | 2026-10-20 |
| P-2b | Mensajes de API, errores/pistas, CLI y MCP en los dos idiomas (--lang) | Abierto | Alta | Traducir mensajes y descripciones; agregar --lang en CLI y MCP. | omnicad/api/errores.py (PISTAS solo en español); omnicad/cli y servidor_mcp sin --lang | 2026-10-20 |
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
| P-28c | Engranajes cilíndricos: variantes faltantes | Abierto | Alta | Implementar las variantes detalladas en la ficha. | omnicad/nucleo/engranajes.py (solo evolvente recto/helicoidal) | 2026-10-20 |
| P-28h | Piñón y cremallera helicoidal, inclinada, doble hélice y curva | Abierto | Alta | Solo cremallera recta. | omnicad/nucleo/engranajes.py:430 cremallera | 2026-10-20 |
| P-29-2 | Orientación recomendada y estimación de filamento, peso y tiempo | Abierto | Alta | Sin programar. | omnicad/nucleo/revision.py no estima ni orienta | 2026-10-20 |
| P-29-3 | Cajas, tapas y organizadores paramétricos (encastre, rosca, bisagra) | Abierto | Alta | Solo existe create_box. | omnicad/api/herramientas_solido.py:327 | 2026-10-20 |
| P-3a | Add-on de Blender para cuerpos, mallas y materiales | Abierto | Muy alta | Crear el add-on y el intercambio bidireccional. | omnicad/ui/puente.py; omnicad/io_archivos/gltf.py | 2026-10-20 |
| P-4c | Motor 3: trazador de rayos propio progresivo | Abierto | Muy alta | Decidido por el usuario como tercer motor; no existe nada de trazado de rayos. | grep de trazador/path tracing en omnicad/: sin resultados; docs/referencia/brechas_keyshot.md:64-66 (KS12-KS14) | 2026-10-20 |
| P-25i | i) SÓLIDO > CREAR: Crear forma y placa de circuito impreso (grisados) | Abierto | Muy alta | Siguen grisados; Forma depende de P-25j y la placa pide espacio ELECTRÓNICA. | omnicad/ui/cinta.py:90,103 | 2026-11-02 |
| P-25j | j) Espacio FORMA completo (T-splines): crear, modificar, simetría, utilidades | Abierto | Muy alta | No existe nada; necesita núcleo de subdivisión propio y decidir el motor. | Sin módulo de subdivisión en omnicad/nucleo/ | 2026-10-20 |
| P-27-12 | Soportes fáciles de sacar (cintas curvas, jaula) | Abierto | Muy alta | Sin programar. | omnicad/nucleo/revision.py:725-791 solo detecta voladizos, no genera soportes | 2026-10-20 |
| P-28d | Cónicos (recto, espiral, Zerol, hipoide, inglete, espirocónico) | Abierto | Muy alta | Sin programar. | omnicad/nucleo/engranajes.py | 2026-10-20 |
| P-28e | Tornillo sin fin y corona (cilíndrico, globoidal, perfiles ZA/ZN/ZI/ZK) | Abierto | Muy alta | Sin programar. | omnicad/nucleo/engranajes.py | 2026-10-20 |
| P-28f | Planetarios y epicicloidales con armado de trenes en un comando | Abierto | Muy alta | Sin programar. | omnicad/nucleo/engranajes.py | 2026-10-20 |
| P-28g | Especiales (no circulares, Hirth, armónico, cicloidal de pernos, esférico…) | Abierto | Muy alta | Sin programar. | omnicad/nucleo/engranajes.py | 2026-10-20 |
| P-28i | Mecanismos relacionados (Ginebra, trinquete, escape, reductores cicloidal/armónico) | Abierto | Muy alta | Sin programar. | omnicad/nucleo/engranajes.py | 2026-10-20 |
| P-26d | .app firmada y notarizada (Apple Developer, USD 99 al año) | Bloqueado | Media | Pide cuenta de Apple Developer del usuario. | Sin carpeta instalador/macos | 2026-10-20 |
| P-25g2 | g) McMaster-Carr, pieza de fabricante y TraceParts | Bloqueado | Alta | Dependen de servicios en línea: decidir si se hacen. | PROJECT_LOG.md:71 | 2026-10-20 |
| MP1 | Mini programas Python con panel de campos y pestaña propia | Abierto | Media | Crear, guardar, compartir y ejecutar con confirmación; integrar GH7/B5/PAQ-H5. | `omnicad/api/` (`execute_code`); `docs/grafo.md` «Pendiente» | 2026-10-20 |

## Faltantes › Reconstruir sólido desde una malla (2026-11-01)

Plan: [plan_reconstruir_solido.md](../plan_reconstruir_solido.md).

Abierto 4 · Parcial 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| RI-2 | Reconstruir un sólido desde una malla, sin IA | Parcial | Alta | Resolver cortes oblicuos, revolución más prisma, esquinas esféricas y moleteados. | tests/test_reconstruir_malla.py; scripts/bench_reconstruir.py reales | 2026-11-01 |
| RI-3 | Comando Reconstruir sólido en MALLA | Abierto | Alta | Los 3 estados aprobados: configurar, calculando y resultado, con Otra vuelta. | docs/plan_reconstruir_solido.md § Interfaz aprobada | 2026-11-01 |
| RI-4 | Resultado paramétrico en la reconstrucción | Abierto | Alta | Bocetos acotados, parámetros con nombre, patrones y simetrías. | docs/plan_reconstruir_solido.md § Opción del usuario | 2026-11-01 |
| RI-5 | IA en la reconstrucción | Abierto | Alta | Ficha, vistas y cortes a la IA, vueltas de corrección y tope de gasto. | docs/plan_reconstruir_solido.md § Idea central; omnicad/asistente/ | 2026-11-01 |
| RI-6 | Superficies libres en la reconstrucción | Abierto | Muy alta | Se decide con datos del banco. | docs/plan_reconstruir_solido.md § Fases | 2026-11-01 |

## Faltantes › Escanear con el celular (2026-11-01)

Upgrade a futuro: no se empieza hasta que Gerardo lo pida. Plan y prompt: [plan_escaneo_celular.md](../plan_escaneo_celular.md).

Bloqueado 7.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| ESC-1 | Prueba real de escaneo con celular | Bloqueado | Baja | 3 piezas conocidas con una app gratis, medidas contra calibre. Decide si la función sigue. | docs/plan_escaneo_celular.md § Fases | 2026-11-01 |
| ESC-2 | Importar un escaneo: fondo y escala | Bloqueado | Media | Comando Escanear pieza con archivos del celular, quitar fondo y escalar con una medida. | docs/plan_escaneo_celular.md § Fases; `insert_file` ya abre .stl, .obj, .3mf y .ply (api/herramientas_documento.py:345) | 2026-11-01 |
| ESC-3 | Hoja de escaneo con marcadores | Bloqueado | Media | PDF desde OmniCAD y detección automática de escala. | docs/plan_escaneo_celular.md § Lo que el celular no resuelve | 2026-11-01 |
| ESC-4 | Video a cuadros nítidos con aviso de faltantes | Bloqueado | Media | Elegir cuadros, rechazar video movido y juntar dos pasadas. | docs/plan_escaneo_celular.md § Fases | 2026-11-01 |
| ESC-5 | Motor local de video a malla | Bloqueado | Alta | Descarga opcional, proceso aparte y medición en esta PC. | docs/plan_escaneo_celular.md § Herramientas revisadas | 2026-11-01 |
| ESC-6 | IA para guiar el escaneo | Bloqueado | Media | Guía de captura, medidas a confirmar con calibre y redondeo. | docs/plan_escaneo_celular.md § Lo que el celular no resuelve; depende de RI-5 | 2026-11-01 |
| ESC-7 | Pasar el video del celular con QR | Bloqueado | Alta | Exige aprobar un servidor en la red local: los de hoy escuchan solo en 127.0.0.1 (AGENTS.md § Seguridad). | docs/plan_escaneo_celular.md § Decisiones | 2026-11-01 |

## Faltantes › ANIMACIÓN contra capturas de Fusion (2026-11-01)

Abierto 4.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| ANI-1 | Navegador y Comentarios en ANIMACIÓN | Abierto | Alta | Elegir, ocultar y transformar desde el Navegador. | docs/brechas_animacion.md § ANI-1; ui/animacion.py (`VentanaAnimacion`) | 2026-11-01 |
| ANI-2 | Explosión manual y barra de explosión | Abierto | Alta | Eje por componente, escala y secuencia en la barra. | docs/brechas_animacion.md § ANI-2; ui/animacion.py:695 (grisado) | 2026-11-01 |
| ANI-3 | Aspecto y trayectorias en la animación | Abierto | Media | Guardados en el guion, con herramienta. | docs/brechas_animacion.md § ANI-3; ui/animacion.py:696 (grisados); `add_animation_action` rechaza appearance, por API | 2026-11-01 |
| ANI-5 | Pieza de ANIMACIÓN en la prueba de ventana | Abierto | Media | Guion completo con publicación. | docs/brechas_animacion.md § ANI-5 | 2026-11-01 |

## Faltantes › Botones grisados sin fila (2026-11-01)

Abierto 3.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| MAL-2 | MALLA: Alinear, Extruir textura y Edición directa | Abierto | Alta | Tres botones grisados y sin comando. | ui/cinta.py:175 y 178; ayuda `Extrude texture on a mesh body` | 2026-11-01 |
| CHA-1 | CHAPA: Pestaña solevada y Cierre de esquina | Abierto | Alta | Dos botones grisados y sin comando. | ui/cinta.py:148 y 151; ayuda `Create lofted flange` | 2026-11-01 |
| CFG-1 | Reglas de configuración | Abierto | Media | Botón grisado en CONFIGURAR. | ui/cinta.py:27; ayuda `Configuration Rules` | 2026-11-01 |

## Faltantes › Capturas de Fusion sin clasificar (2026-11-02)

Salen de las 674 capturas del escritorio, ya ordenadas en `analisis/capturas_fusion/` (índice: `INDICE.md`; las ya hechas se borraron, ver `borradas.tsv`). Abierto 10 · Bloqueado 2. Especificación: mirar las capturas de su sección y `scripts/fusion_docs.py buscar`.

Abierto 7 · Parcial 2 · Bloqueado 2. Especificación: mirar las capturas de su sección y `scripts/fusion_docs.py buscar`.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| CF-1 | DIBUJO: diálogo Crear dibujo completo | Abierto | Media | Agregar automático, contenido, planos por nivel, base, unidades, recuento y tamaño propio. | ui/dibujo.py (solo `DialogoHoja`); capturas `DIBUJO/Crear_dibujo` | 2026-11-02 |
| CF-2 | DIBUJO: panel Vista de dibujo | Abierto | Alta | Completar estilos, calidad, aristas, centros, vistas guardadas y referencias. | ui/dibujo.py; capturas `DIBUJO/Vista_de_dibujo` y `DIBUJO/Vista_base` | 2026-11-02 |
| CF-3 | DIBUJO: menú COTAS completo | Parcial | Media | Cota automática, ordenar, organizar, igualar, voltear flechas, recodo y máx/mín. | nucleo/dibujo.py; capturas `DIBUJO/Menu_de_cotas` y `DIBUJO/Ordenar` | 2026-11-02 |
| CF-4 | DIBUJO: notas, tablas y símbolos | Abierto | Media | Completar notas, texto con formato, tablas, símbolos y extensión de arista. | ui/dibujo.py; capturas `DIBUJO/Tablas`, `Simbolos_de_dibujo`, `Texto_y_notas` | 2026-11-02 |
| CF-5 | DIBUJO: navegador, hojas, cinta y exportar | Abierto | Media | Completar hojas, cinta, DWG/CSV, vistas, boceto y patrón de centros. | ui/dibujo.py; capturas `DIBUJO/Navegador_de_dibujo`, `Exportar_dibujo` | 2026-11-02 |
| CF-7 | Preferencias: páginas que no existen | Abierto | Media | Agregar las páginas y los diez ajustes faltantes detallados en la ficha. | omnicad/ui/preferencias.py; capturas `INTERFAZ/Preferencias_*` | 2026-11-02 |
| CF-8 | Preferencias: opciones sueltas de General y Gráficos | Parcial | Baja | Resolver eje vertical, tipo de diseño, finalidad, puesta en marcha y controlador. | tests/test_preferencias.py; omnicad/ui/preferencias.py | 2026-11-06 |
| CF-9 | MALLA: Suavizar contorno, Puente e Insertar malla completo | Abierto | Media | Crear Suavizar/Puente y completar la colocación de Insertar malla. | grep sin resultados en api/ y ui/comandos/; capturas `MALLA/` e `INSERTAR/Insertar_malla` | 2026-11-02 |
| CF-10 | MATERIALES: Explorador de materiales y propiedades | Abierto | Media | Propiedades térmicas y mecánicas, favoritos, materiales nuevos y bibliotecas personales. P-25d cubre solo Administrar. | capturas `MATERIALES/` | 2026-11-02 |
| CF-13 | SÓLIDO: Modelado automatizado | Bloqueado | Muy alta | Genera alternativas entre geometrías a conectar y a evitar; emparentado con EXT-3 (diseño generativo). Espera el alcance. | sin herramienta; capturas `SOLIDO/Modelado_automatizado` | 2026-11-02 |
| CF-14 | ELECTRÓNICA: esquemas, placas y biblioteca de componentes | Bloqueado | Muy alta | Diseño de electrónica 2D y 3D, biblioteca de componentes y leyenda de taladro. P-25i solo nombra la placa. Espera el alcance. | sin código; capturas `ELECTRONICA/` | 2026-11-02 |

## Faltantes › Plástico y extensiones contra capturas de Fusion (2026-11-01)

Especificación y prompt: [brechas_extensiones.md](../brechas_extensiones.md).

Abierto 3 · Parcial 8 · Bloqueado 4.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| PLA-1 | Grampa de fijación (Snap Fit): gancho, ranurado y contorno | Parcial | Alta | Agregar selección y giro faltantes, Flip y radio de base; mejorar cabeza y ranura. | ui/cinta.py:160 (botón gris); docs/brechas_extensiones.md | 2026-11-01 |
| PLA-3 | Saliente de fijación de dos lados, con fijador y nervios | Parcial | Alta | Agregar Lado 2, escariado, escalón, fijador y nervios. | api create_boss; docs/brechas_extensiones.md | 2026-11-01 |
| PLA-4 | Labio: tipo Labio y acanalado sobre dos cuerpos | Parcial | Media | Agregar Cadena tangente, Guía de cara y Avanzado (extensiones, Flip). | api create_lip_groove: lip_type solo lip o groove; docs/brechas_extensiones.md | 2026-11-01 |
| PLA-5 | Reglas de plástico: árbol, editar, biblioteca y quitar la regla | Parcial | Media | Agregar árbol, edición, copia, selección en lienzo, quitar en navegador y reglas de fábrica. | ui/comandos/plastico.py; docs/brechas_extensiones.md | 2026-11-01 |
| PLA-7 | Patrón geométrico: objeto personalizado y caras curvas | Parcial | Media | Agregar Dirección perpendicular, Cambiar y Expandir; comprobar caras curvas en Fusion. | api create_geometric_pattern; docs/brechas_extensiones.md | 2026-11-01 |
| PLA-8 | Sólido delimitador: tipos fijos, desfases, redondeo, origen y cotas | Parcial | Media | Hoy tres formas y un margen. Faltan seis tipos, modo de desfase, redondeo, cuatro orígenes y cotas en vivo. | ui/cinta.py:102; api create_bounding_solid; docs/brechas_extensiones.md | 2026-11-01 |
| PLA-9 | Simplificar: eliminar operaciones/caras y reemplazar | Parcial | Alta | Completar componentes, asas, selección, tipos y caras vecinas; corregir chaflanes contiguos. | tests/test_reemplazar_primitivas.py; tests/test_simplificar.py | 2026-11-03 |
| PLA-10 | Insertar fijador: panel de biblioteca | Parcial | Alta | Agregar búsqueda, organizaciones, imperial, árbol, favoritos, vistas, filtros y familias. | nucleo/fijaciones.py NORMAS; docs/brechas_extensiones.md | 2026-11-01 |
| PLA-11 | Timeline: Convertir en operación de DM | Abierto | Media | No figura en la ayuda local: comprobar en Fusion real qué hace antes de construirla. | ui/panel_timeline.py:338 (entradas_menu); docs/brechas_extensiones.md | 2026-11-01 |
| PLA-12 | Convertir malla: método Orgánico | Abierto | Muy alta | Hoy solo facetado y prismático. Falta Orgánico, Paramétrica o Base, resolución y Preprocesar agujeros. Se relaciona con F10, F11 y RI-1. | api convert_mesh; docs/brechas_extensiones.md | 2026-11-01 |
| PLA-13 | PMI: notas 3D de agujero o rosca y nota libre | Abierto | Alta | No existe. Va en Utilidades › Crear PMI. | sin código (grep pmi); docs/brechas_extensiones.md | 2026-11-01 |
| EXT-1 | Anidación y fabricación (Manufacturing Extension) | Bloqueado | Muy alta | Decidir el alcance: hojas, materiales, estudios y exportar DXF. Se relaciona con Organizar de P-25d. | sin código (grep anidaci); docs/brechas_extensiones.md | 2026-11-01 |
| EXT-2 | Simulación avanzada: térmica, modal, pandeo, no lineal, eventos, moldeo y refrigeración | Bloqueado | Muy alta | Depende de F19, que es solo estática. | sin código FEM (grep); docs/brechas_extensiones.md | 2026-11-01 |
| EXT-3 | Diseño generativo | Bloqueado | Muy alta | Decidir el alcance. Depende de F19. | ui/cinta.py:255 (espacios grisados); docs/brechas_extensiones.md | 2026-11-01 |
| EXT-4 | Fusion Manage: PLM en la nube | Bloqueado | Muy alta | Decidir si se hace: el proyecto trabaja sin nube. | sin código; docs/brechas_extensiones.md | 2026-11-01 |

## Faltantes › Fusion 360

Bloqueado 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| FU-12 | Simulación, Fabricación y Forma (T-Splines) | Bloqueado | Muy alta | Decidir dependencias (CalculiX, Gmsh) y alcance antes de empezar | ui/cinta.py:244 (espacios grisados); sin código FEM, CAM ni T-Splines (grep) | 2026-10-20 |

## Faltantes › FreeCAD

Abierto 2 · Parcial 3 · Bloqueado 3.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| F15 | Parámetros desde XLSX y familias de piezas desde hoja | Abierto | Media | El CSV ya anda: falta XLSX y las familias de piezas. | api/herramientas_parametros_csv.py y ui/dialogos.py:254 ya importan CSV; timeline/documento.py:168 tabla de configuraciones | 2026-11-01 |
| F13 | Estructura de perfiles con ingletes y lista de cortes | Abierto | Alta | Perfiles estándar a lo largo de rutas con ingletes automáticos y lista de cortes | sin código (grep); nucleo/superficies.py:525 aclara que no hay esquinas a inglete | 2026-10-20 |
| F1 | Engranajes, cremallera y rueda de cadena | Parcial | Baja | Polea dentada (correa); valores ISO 606 de la rueda de cadena por verificar | tests/test_engranajes.py; tests/test_api_engranajes.py | 2026-10-20 |
| F9 | Dibujo: vista interrumpida, soldadura, acabado, ajuste, cotas en cadena | Parcial | Media | Vista interrumpida, símbolos de soldadura y acabado, ajuste, cotas en cadena y de chaflán | nucleo/dibujo.py; io_archivos/svg_salida.py | 2026-10-20 |
| F23 | Curva sobre malla y relleno con continuidad G2 | Parcial | Alta | Curva sobre malla | timeline/ops_superficie.py:104-117 OpParche G0/G1/G2; nucleo/superficies.py:472; tests/test_superficies.py:138 (parche G1 con soporte) | 2026-10-20 |
| F22 | Nube de puntos e importar .scad | Bloqueado | Media | Importar PLY/XYZ como nube de puntos; .scad pide OpenSCAD instalado (decisión del usuario) | io_archivos/abrir_externo.py solo importa PLY como malla; sin código de nube de puntos ni OpenSCAD | 2026-10-20 |
| F19 | Simulación estática FEM (CalculiX + Gmsh) | Bloqueado | Muy alta | Decidir las dependencias externas y construir la simulación estática | sin código FEM (grep); ui/cinta.py:244 espacio SIMULACIÓN grisado | 2026-10-20 |
| F20 | Fabricación CAM (contorno, bolsillo, taladrado, G-code) | Bloqueado | Muy alta | Decidir el alcance de un proyecto aparte y construir el CAM | sin código CAM ni G-code (grep); ui/cinta.py:244 espacio FABRICACIÓN grisado | 2026-10-20 |

## Faltantes › Plasticity

Abierto 1 · Bloqueado 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| PL10 | Puente en vivo con Blender | Abierto | Alta | Add-on de Blender, botón «Enviar a Blender» y refresco al cambiar un parámetro | sin código de Blender (grep); ui/puente.py es el puente de agentes MCP, no transmite mallas a Blender | 2026-10-20 |
| PL12 | Soporte de SpaceMouse (3Dconnexion) | Bloqueado | Media | Requiere el dispositivo 3Dconnexion para probar y su biblioteca de entrada | sin código SpaceMouse ni 3Dconnexion (grep) | 2026-10-20 |

## Faltantes › Blender

Abierto 6 · Parcial 3 · Bloqueado 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| B6 | Video MP4, cámara en ruta y suavizado editable | Abierto | Media | MP4 (ffmpeg, pedir permiso), cámara en ruta y suavizado editable por tramo | api/herramientas_animacion.py:484 (solo gif o png); nucleo/animacion.py:42 (suavizado fijo) | 2026-10-20 |
| B11 | Varillas desde aristas (jaulas, marcos, celosías) | Abierto | Media | Cada arista a una varilla con sección elegida y nudos redondeados | sin código (grep); solo existe tuberia sobre una ruta | 2026-10-20 |
| B1 | Render con Cycles de Blender como motor externo | Abierto | Alta | Exportar la escena, correr Blender en segundo plano y mostrar la imagen | sin código Cycles (grep); ui/render.py solo motores gl y cpu; orden decidido en brechas_keyshot.md:35 | 2026-10-20 |
| B5 | Complementos de usuario con manifiesto | Abierto | Alta | Cargar operaciones, comandos y herramientas desde una carpeta con manifiesto, con interruptor y errores | ui/administrar.py:262 (solo ejecuta scripts sueltos); ui/cinta.py:174 | 2026-10-20 |
| B13 | Relieve por textura en caras (Displace) | Abierto | Alta | Desplazar caras con ruido o imagen: cuero, panal, agarre | sin código (grep); existe repujado de perfiles y texto (timeline/ops_solido.py:156) | 2026-10-20 |
| B18 | Mapeo UV y texturas | Abierto | Alta | Desenvolver y proyecciones caja, cilindro y esfera; va con el render y con RH21 | sin código UV (grep); existe calcomanía sobre cilindro (tests/test_calcomania_cilindro.py) | 2026-10-20 |
| B4 | Vectorizar imagen: vista previa y esquinas | Parcial | Baja | Crear vista previa de curvas y resolver el contorno con una sola punta. | tests/test_texto_vectores.py; io_archivos/vectorizar.py:93 | 2026-10-20 |
| B3 | Exportar FBX y USD (glTF ya está) | Parcial | Alta | Escritor de FBX (sin especificación pública) y de USD (pide la biblioteca pxr) | 8e1a1fe; io_archivos/gltf.py (docstring: FBX y USD no se escriben); tests/test_gltf.py | 2026-10-20 |
| B15 | Nodos de geometría: campos, atributos, instancias, zonas de repetición | Parcial | Muy alta | Campos, atributos, instancias con realizar y zonas de repetición y simulación | tests/test_grafo.py; tests/test_api_grafo.py | 2026-10-20 |
| B16 | Modo edición de malla (extruir, inset, bisel, cuchillo) | Bloqueado | Muy alta | Solo si el usuario lo pide: modelado de malla, fuera de lo que hace Fusion | sin código (grep); la malla es solo de triángulos (nucleo/malla.py:2405) | 2026-10-20 |
| B17 | Simulación de cuerpo rígido | Bloqueado | Muy alta | Elegir un motor de física (dependencia nueva, pedir permiso) y hornear a animación | sin código de física (grep); espacio SIMULACIÓN grisado (ui/cinta.py:244) | 2026-10-20 |

## Faltantes › Rhino 8

Abierto 4 · Bloqueado 4 · Sin verificar 3.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| RH10 | Relieve desde imagen (mapa de altura a superficie) | Abierto | Media | Comando con imagen, tamaño, altura máxima y resolución | sin código (grep heightfield/mapa de altura); existe repujado con perfiles y texto | 2026-10-20 |
| RH15 | Colocar y repartir sobre superficies | Abierto | Media | Orientar sobre superficie o curva, matriz sobre superficie y repartir con separación pareja | sin código (grep); existen alinear, mover y patrón en ruta | 2026-10-20 |
| RH11 | ShrinkWrap: malla estanca alrededor de objetos | Abierto | Alta | Envolver mallas, NURBS o nubes con celda y cierre de huecos (puede pedir dependencia) | nucleo/solidos_crear.py:2911 solido_envolvente es una caja o cilindro, no un shrinkwrap; reparar_malla | 2026-10-20 |
| RH21 | Mapeo UV y texturas (cajas, esfera, editor UV) | Abierto | Alta | Proyecciones caja, cilindro, esfera y editor de UV; misma tarea que B18 | sin código UV (grep) | 2026-10-20 |
| RH3 | Abrir y guardar .3dm con capas, colores y bloques | Bloqueado | Media | Pedir permiso para instalar rhino3dm (paquete nuevo) y escribir el lector y escritor | sin código .3dm (grep); decisión del usuario (README › Decisiones) | 2026-10-20 |
| RH22 | Nube de puntos: reducir, contornos y secciones | Bloqueado | Media | Depende de F22 (importar nube de puntos), que espera decisión del usuario | sin código de nube de puntos (grep) | 2026-10-20 |
| RH19 | Modelado por subdivisión (SubD) | Bloqueado | Muy alta | Proyecto aparte: decidir alcance (junto con PolySplines y Forma de Fusion) antes de empezar | sin código SubD (grep) | 2026-10-20 |
| RH20 | Quad remesh y cuadrangulación | Bloqueado | Muy alta | Decidir si se hace; algoritmo pesado, base inversa de SubD | sin código (grep) | 2026-10-20 |
| NOV-brechas_rhino-1 | Notilus Composite para Rhino 8 (novedad automática) | Sin verificar | Media | Clasificar el complemento y decidir si importa. | sin código relacionado; novedad agregada por scripts/novedades.py sin clasificar | 2026-10-20 |
| NOV-brechas_rhino-2 | Notilus Scantling para Rhino 8 (novedad automática) | Sin verificar | Media | Clasificar el complemento y decidir si importa. | sin código relacionado; novedad agregada por scripts/novedades.py sin clasificar | 2026-10-20 |
| NOV-brechas_rhino-3 | Notilus Piping: tuberías y HVAC en Rhino (novedad automática) | Sin verificar | Media | Clasificar el complemento y decidir si importa. | sin código relacionado; novedad agregada por scripts/novedades.py sin clasificar | 2026-10-20 |

## Faltantes › Grasshopper

Abierto 6 · Parcial 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| GH7 | Publicar un grafo como comando con panel de campos | Abierto | Media | Todo: publicar el grafo en la tecla S con panel de entradas. | docs/grafo.md «Pendiente»; sin comando de grafo en omnicad/ui/comandos/ | 2026-10-20 |
| GH11 | Optimizador de parámetros (minimizar o maximizar un resultado) | Abierto | Media | Todo: ANALIZAR › Optimizar con rangos, objetivo y barra de progreso. | grep optimiz/galapagos sin coincidencias en clon/omnicad (scipy solo en restricciones/solver.py) | 2026-10-20 |
| GH4 | Lienzo de nodos en la interfaz (pestaña DISEÑO ALGORÍTMICO) | Abierto | Alta | Todo: arrastrar nodos, cables, vista previa, errores en rojo. | docs/grafo.md:4 y «Pendiente»; sin módulo de lienzo en omnicad/ui/ | 2026-10-20 |
| GH9 | Clústeres: agrupar nodos en un nodo propio reutilizable | Abierto | Alta | Todo; depende del lienzo (GH4). | docs/grafo.md «Pendiente»; sin código de clústeres en grafo/ | 2026-10-20 |
| GH10 | Bucles y campos escalares en el grafo | Abierto | Alta | Todo: nodos Repetir, campos y vista de isolíneas. | docs/grafo.md «Pendiente»; grep de bucle/campo en grafo/ sin resultados | 2026-10-20 |
| GH12 | Nodos de terceros mediante complementos | Abierto | Alta | Todo; depende del gestor de complementos B5 (no encontrado en el código). | grep complemento/plugin en clon/omnicad sin gestor de nodos | 2026-10-20 |
| GH3 | Catálogo de nodos (≈80 previstos) con tipos de puerto | Parcial | Media | Agregar solevación, revolución, barrido, divisiones de curva, matrices y lista de valores. | tests/test_grafo.py; omnicad/grafo/nodos_basicos.py | 2026-10-20 |
| GH6 | Nodo de script Python y nodo de expresión | Parcial | Media | Falta el nodo de script Python con editor; el de expresión ya existe. | omnicad/grafo/nodos_basicos.py:207 (nodo expresion); docs/grafo.md «Pendiente» | 2026-10-20 |

## Faltantes › KeyShot

Abierto 9 · Parcial 3 · Bloqueado 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| KS2 | Entornos HDRI (.hdr), giro, brillo y biblioteca propia | Abierto | Media | Leer .hdr, lista con miniaturas, giro y brillo; hoy son degradados. | omnicad/nucleo/render_cpu.py:175-179 (ENTORNOS = degradados); grep hdr sin lector | 2026-10-20 |
| KS7 | Cámaras guardadas con apertura, enfoque y desenfoque (DOF) | Abierto | Media | Lista de cámaras con nombre del render, apertura, enfoque y desenfoque. | omnicad/ui/render.py:1404-1409; ui/ventana.py:2031 | 2026-10-20 |
| KS9 | Cola de render y lotes en segundo plano | Abierto | Media | Pestaña Cola en la galería: orden, estado, cancelar, abrir carpeta. | omnicad/ui/render.py (galería sin cola; grep cola sin resultados) | 2026-10-20 |
| KS10 | Variantes y configurador: renderizar todas las combinaciones | Abierto | Media | Unir configuraciones × aspectos × cámaras con el render y la cola. | omnicad/timeline/documento.py:168-170 (configuraciones existen); no están unidas al render | 2026-10-20 |
| KS-S3 | Enviar a KeyShot (export glTF/USD con materiales) | Abierto | Media | Comando que exporte con materiales y abra KeyShot (no verificado qué formatos lee). | omnicad/ui/puente.py existe; sin comando de envío | 2026-10-20 |
| KS-S2 | Configurador web: variantes en una página | Abierto | Alta | Todo; sigue de KS10 y de la salida GLB. | docs/referencia/brechas_keyshot.md:79 (pendiente a futuro); sin código | 2026-10-20 |
| KS12 | Materiales de fuente de luz (área, IES, foco) | Abierto | Muy alta | Pide trazado de rayos: no hay trazador (render rasterizado). | grep cycles/embree/pathtrac sin resultados en clon/omnicad | 2026-10-20 |
| KS13 | Vidrio grueso, gemas, cáusticas, subsuperficie, iluminación global | Abierto | Muy alta | Pide trazado de rayos o Cycles de Blender. | grep cycles/embree sin resultados; render_cpu.py es rasterizador (docstring l.1-12) | 2026-10-20 |
| KS14 | Imagen que se refina sola en el lienzo (muestreo progresivo) | Abierto | Muy alta | Pide trazador propio progresivo. | render_cpu.py renderiza por mosaicos una sola pasada | 2026-10-20 |
| KS5 | Biblioteca de materiales: arrastrar, favoritos, copiar aspecto | Parcial | Media | Arrastrar muestras a piezas en vista/navegador y copiar aspecto entre piezas. | omnicad/nucleo/aspectos.py; tests/test_aspectos_api.py | 2026-11-05 |
| KS8 | Giratoria (turntable) y explosionada en un clic | Parcial | Media | Falta la acción Giratoria (ángulo, duración, cuadros) en ANIMACIÓN. | omnicad/api/herramientas_animacion.py (auto_explode hecho); grep giratoria/turntable sin resultados | 2026-10-20 |
| KS-S1 | Exportar a GLB y USD para web y AR | Parcial | Alta | Falta USD (necesita escritor propio o pxr). | omnicad/io_archivos/gltf.py; io_archivos/exportar.py:19-20; commit c1c40f2 (2026-10-10) | 2026-10-20 |
| KS15 | «AI Shots»: restilizar y generar variantes con modelo local | Bloqueado | Muy alta | Espera decisión del usuario: no gastar en APIs y exige un modelo local grande. | docs/referencia/brechas_keyshot.md:72 (decisión del usuario); sin código | 2026-10-20 |

## Faltantes › V-Ray

Abierto 10 · Parcial 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| VR1 | Mezcla de luces (Light Mix) después del render | Abierto | Media | Panel Luces con intensidad y color por luz sin re-renderizar. | render_cpu.py:993 (n_luces = 1 o 3 fijas, sin acumulado por luz) | 2026-10-20 |
| VR2 | Postproceso no destructivo (exposición, curva, bloom, viñeta) | Abierto | Media | Todo el postproceso sobre la imagen en flotante; la exposición hoy es parámetro previo. | render_cpu.py:172,235 (exposicion EV y ACES dentro del render, no posterior) | 2026-10-20 |
| VR6 | Sol y cielo físicos por lugar, fecha y hora | Abierto | Media | Cálculo de sol/cielo, nubes y niebla; hoy los entornos son degradados. | render_cpu.py:175-179 | 2026-10-20 |
| VR7 | Regiones de render con forma propia | Abierto | Media | Dibujar una región en el lienzo y renderizar solo eso. | grep region en ui/render.py sin resultados | 2026-10-20 |
| VR8 | Material dibujo animado (Toon) y de borde | Abierto | Media | Tipo de material con contorno y bandas de color. | grep toon sin resultados en clon/omnicad | 2026-10-20 |
| VR9 | Dispersión (Scatter) de copias sobre una superficie | Abierto | Media | Reparto aleatorio con densidad, escala y giro; ampliar el patrón. | grep scatter/dispersión sin resultados | 2026-10-20 |
| VR3 | Elementos de render (pases) y máscaras por píxel | Abierto | Alta | Pases difuso, reflejo, sombra, oclusión, normales, profundidad e ID. | grep de pases en render_cpu.py sin resultados | 2026-10-20 |
| VR5 | Corte en el render (Clipper) con tapa de color | Abierto | Alta | Agregar Clipper con tapa de color en la ventana y render_image. | omnicad/nucleo/render_estilos.py; ui/render.py (sin clipper) | 2026-10-20 |
| VR12 | Reducción de ruido (OIDN) | Abierto | Alta | Solo con trazador propio; con Cycles ya viene. | sin trazador de rayos: no hay ruido que reducir | 2026-10-20 |
| VR11 | Iluminación global, cáusticas, IES, subsuperficie, pelo | Abierto | Muy alta | Pide trazado de rayos (Cycles de Blender o trazador propio). | grep cycles sin resultados | 2026-10-20 |
| VR4 | Cámara física: ISO, obturador, f, auto-exposición, DOF | Parcial | Media | Faltan ISO, obturador, f, exposición automática, balance de blancos y DOF. | render_cpu.py:171-172 (focal y exposición EV ya existen) | 2026-10-20 |

## Faltantes › Capa para agentes (paquetes del plan)

Abierto 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| PAQ-H5 | Hito 5: carpeta complementos/ con registrar(api) | Abierto | Alta | Opcional; solo si el usuario lo pide. Es la misma tarea que B5/GH12. | no existe complementos/ en el repo | 2026-10-20 |

## Faltantes › Asistente IA (chat dentro de la app)

Parcial 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| IA-2 | Proveedores API: Anthropic y OpenAI compatibles | Parcial | Media | Agregar SSE, probar Ollama y devolver pensamiento de Claude; prueba paga con OK. | tests/test_asistente_proveedores.py; omnicad/asistente/proveedores/anthropic.py | 2026-10-25 |
| IA-11 | Herramientas eficientes desde el chat del asistente | Parcial | Alta | Medir tokens por paso con el uso de API, solo con OK de Gerardo. | omnicad/asistente/herramientas.py; tests/test_asistente_alcance.py | 2026-10-25 |

## Faltantes › SolidCraft

Abierto 6 · Parcial 1 · Bloqueado 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| SC14 | Importar .FCStd de FreeCAD | Abierto | Media | Leer el ZIP y los .brp con BRepTools.Read, con topes de seguridad. | grep FCStd sin resultados | 2026-10-20 |
| SC15 | Exportar URDF desde un ensamble con uniones | Abierto | Media | Eslabones, masa, inercia y juntas con límites. | grep urdf sin resultados en clon/omnicad | 2026-10-20 |
| SC2 | Robustez con semilla: generador de diseños y minimizador | Abierto | Alta | Generador aleatorio, chequeo de volumen, CLI omnicad fuzz. | grep fuzz sin resultados; solo tortura manual (tests/test_hallazgos_tortura.py) | 2026-10-20 |
| SC11 | Ratón 3D (SpaceMouse) con preferencias por eje | Abierto | Alta | Leer HID (hidapi pide permiso o ctypes) y mapear desplazar, zoom, giro. | grep spacemouse/hidapi sin resultados | 2026-10-20 |
| SC12 | Chapa: Perforar | Abierto | Alta | Operación nueva. Snap Fit y Apoyo pasaron a PLA-1 y PLA-2. | grep perforar sin resultados | 2026-11-01 |
| SC17 | Mallado estanco y rápido, con evaluación en GPU | Abierto | Alta | Medir primero; si es cuello de botella, pasar a Rust. | nucleo/malla.py:952 (BRepMesh de OpenCascade) | 2026-10-20 |
| SC7 | Análisis del estudio de movimiento: gráficos, rastro, choques | Parcial | Media | Faltan gráficos de valor, velocidad y aceleración y el rastro de un punto. | omnicad/api/herramientas_ensamble.py:703-714; tests/test_api_ensamble.py:230 | 2026-10-20 |
| SC16 | Pruebas de mutación (mutmut) juzgadas por SC1 y SC2 | Bloqueado | Media | Espera permiso para instalar mutmut y que existan SC1 y SC2. | sin mutmut en pyproject.toml | 2026-10-20 |

## Faltantes › Otros CAD libres

Abierto 1 · Parcial 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| CL1 | Cambio de agente con vista previa y control de revisión | Parcial | Media | Agregar expected_revision para agentes externos del puente en vivo. | omnicad/ui/asistente.py (_Tarjeta); tests/test_asistente_ui.py | 2026-10-25 |
| CL3 | Tutoriales reproducibles con capítulos y cámara | Abierto | Media | Todo. | grep tutorial sin resultados | 2026-10-20 |

## Mejoras › Pendientes generales

Abierto 6 · Parcial 4 · Bloqueado 3.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| P-12b | Registrar la tarea programada de Windows para el informe mensual | Abierto | Baja | La tarea no se registra sola; el comando está en el docstring del script. | scripts/novedades.py | 2026-10-20 |
| P-26a | CI en macOS (ruff + pytest + humo) para ver qué falla | Abierto | Baja | El workflow solo tiene jobs de Windows y Ubuntu. | .github/workflows/instaladores.yml | 2026-10-20 |
| P-8d | Paquetes .deb o Flatpak para Linux (dicho como «quizás») | Abierto | Media | Sin empezar; hoy solo AppImage. | instalador/linux/ solo tiene armar_appimage.sh | 2026-10-20 |
| P-12d | Cada mes elegir 3 funciones útiles, programarlas y sacar versión nueva | Abierto | Media | Proceso recurrente sin ejecutar; anotar y subir cada versión a GitHub. | docs/novedades/ solo tiene 2026-10.md | 2026-10-20 |
| P-26b | OpenGL 4.1 core en macOS (shaders GLSL 410, contexto core) | Abierto | Media | Los shaders usan #version 120. | omnicad/ui/render.py:124,133,221 | 2026-10-20 |
| P-26c | Compilar el módulo Rust para arm64 y x86_64 | Abierto | Media | Solo hay .pyd de Windows. | omnicad/_rs.cp312-win_amd64.pyd | 2026-10-20 |
| P-2c | Documentación y README en inglés | Parcial | Media | Traducir docs/ y docs/agentes; solo el README tiene versión inglesa. | README.en.md existe; docs/*.md solo en español | 2026-10-20 |
| P-5b | Mejoras de vectores, SVG, edición y texto según Blender | Parcial | Alta | Completar vista previa de trazos, esquinas y texto avanzado según brechas_blender.md. | tests/test_texto_vectores.py; docs/referencia/brechas_blender.md | 2026-10-20 |
| P-6d | Revisar ensamblaje, animación, mallado, historial y movimiento de piezas | Parcial | Alta | Agregar contactos, uniones leva/tornillo y gráficos de movimiento. | tests/test_api_animacion.py; tests/test_ensamblar.py | 2026-10-20 |
| P-4a | Revisar entero el motor de render, materiales, colores e iluminación | Parcial | Muy alta | Completar revisión y listas KeyShot/V-Ray. | tests/test_render.py; tests/test_render_aspecto.py | 2026-10-20 |
| P-8b | Validar el .exe armado por GitHub en una PC limpia | Bloqueado | Baja | Hace falta una máquina limpia (el armado local sí se probó). | README.md:74 avisa de SmartScreen; sin registro de prueba en PC limpia | 2026-10-20 |
| P-30-dec | Decidir FreeCAD como oráculo externo de SC1 y los paquetes hidapi y mutmut | Bloqueado | Baja | Decisiones del usuario; no instalar sin permiso. | PROJECT_LOG.md:112 | 2026-10-20 |
| P-1b | Probar en Linux nativo (GNOME/KDE, GPU real, atajos, diálogos de archivo) | Bloqueado | Media | Falta una PC con Linux nativo para probar a mano atajos y diálogos de archivo. | Solo hay corridas en WSL2 (Registro); el CI de Linux arma AppImage pero no prueba la interfaz | 2026-10-20 |

## Mejoras › Hallazgos de pruebas de uso

Abierto 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| H-75 | Cuerpos negros planos y letras negras invisibles sobre placas negras | Abierto | Media | Probar reflejo de entorno o luz mínima y comparar con Fusion. | clon/omnicad/ui/visor3d.py (LUZ_AMBIENTE, LUZ_BRILLO, GL_SPECULAR) | 2026-11-05 |
| H-55 | Sustainability Insights: la región y el país no cambian el cálculo | Abierto | Media | Sumar la energía de fabricación por región con un factor de red eléctrica con fuente. Hoy el resultado lo avisa. | nucleo/sustentabilidad.py | 2026-11-01 |

## Mejoras › FreeCAD

Parcial 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| F14 | Piezas estándar ampliadas (rodamientos, pasadores, insertos) | Parcial | Media | Rodamientos, pasadores e insertos roscados (hay tornillos, tuercas, arandelas, varilla y espárragos) | nucleo/fijaciones.py:52 FAMILIAS; tests/test_fijaciones.py | 2026-10-20 |

## Mejoras › Plasticity

Parcial 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| PL13 | Modo Render en el visor con HDRI integrados | Parcial | Media | HDRI integrados (hoy los entornos son degradés de cielo) | ui/render.py:399 (visor con aspectos, entorno y sombras); nucleo/render_cpu.py ENTORNOS; sin HDRI (grep) | 2026-10-20 |

## Mejoras › Blender

Parcial 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| B19 | Normales y sombreado al exportar mallas | Parcial | Baja | Elegir suavizado por ángulo y normales ponderadas al exportar mallas | io_archivos/gltf.py:10,46 (normales por vértice con ángulo de pliegue) | 2026-10-20 |
| B9 | Limpieza de malla ampliada | Parcial | Media | Disolver por ángulo, hacer plano y simetrizar (triángulos a cuadriláteros no cabe) | nucleo/malla.py:2403-2420; tests/test_api_malla.py | 2026-10-20 |

## Mejoras › Rhino 8

Abierto 1 · Parcial 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| RH14 | Dibujo: cotas de curva, área y volumen; estilos; plantillas de hoja | Abierto | Media | Cotas de longitud de curva, área y volumen; estilos importables; plantillas de hoja | nucleo/dibujo.py: sin esas cotas, estilos ni plantillas (grep) | 2026-10-20 |
| RH16 | Modos de pantalla por objeto y poses guardadas | Parcial | Media | Modos de pantalla por objeto (Pluma, Técnico, Fantasma), selecciones con nombre y disposición de ventana | ui/visor3d.py:70; ui/ventana.py:2031 | 2026-10-20 |
| RH17 | Bloques vinculados a un archivo que se recarga | Parcial | Media | Vínculo a un archivo externo que se recarga si cambió («Actualizar si cambió el archivo») | timeline/ops_ensamblar.py:499; tests/test_pl8_instancias.py | 2026-10-20 |

## Mejoras › KeyShot

Parcial 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| KS3 | Material completo: refracción, subsuperficie, anisotropía, emisivo, mapas | Parcial | Alta | Aplicar translucidez, emisividad, relieve y resalte; agregar IOR, subsuperficie y mapas. | omnicad/nucleo/aspectos.py:5-11,35-43 | 2026-10-20 |
| KS11 | Salida con alfa y por pases (EXR, TIFF, PSD) | Parcial | Alta | Faltan EXR/TIFF/PSD y pases (difuso, reflejo, sombra, ID); el PNG con alfa ya existe. | omnicad/ui/render.py:1595 (Fondo transparente), :1647 (solo PNG); nucleo/render_cpu.py:993 (fondo_transparente) | 2026-10-20 |

## Mejoras › V-Ray

Parcial 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| VR13 | Render por mosaicos en varios procesos, cancelable y pausable | Parcial | Alta | Faltan varios procesos, pausa y no bloquear la ventana. | render_cpu.py:736,992-1030 (mosaicos, RenderCancelado); ui/render.py:2131 (QProgressDialog con Cancelar) | 2026-10-20 |

## Mejoras › Capa para agentes (paquetes del plan)

Parcial 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| PAQ-K | Paquete K: prueba real con agentes (Claude Code, OpenCode, solo CLI, modo en vivo) | Parcial | Media | Según el log solo Claude Code pasó; faltan OpenCode, solo CLI y modo en vivo (no verificable desde el código). | PROJECT_LOG.md:11; tests/test_setup.py | 2026-10-20 |

## Mejoras › SolidCraft

Abierto 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| SC19 | Borrador de issue de GitHub desde un error, con contexto y captura | Abierto | Baja | Crear borrador editable desde error/Ayuda, revisado por la persona y sin envío automático. | grep issue/borrador en clon/omnicad/ui sin resultados | 2026-10-26 |

## Mejoras › Otros CAD libres

Abierto 1 · Parcial 3.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| CL2 | Resultado con efecto observado en cada herramienta | Abierto | Media | Campo applied/moved/revisión final en la respuesta de llamar(). | omnicad/api/registro.py:310 (devuelve solo ok, result, avisos) | 2026-10-20 |
| CL4 | Elegir caras por descripción con candidatos y motivo | Parcial | Media | Faltan selectores por intención, propiedades devueltas y aviso de ambigüedad. | omnicad/api/herramientas_inspeccion.py:367-382 (find_faces, find_edges con selectores) | 2026-10-20 |
| CL5 | Diagnóstico para el agente: registro de operaciones y fallos | Parcial | Media | Registro de operaciones y contexto de restricciones y kernel. | omnicad/api/herramientas_dev.py:201-209 (list_error_reports, read_error_report) | 2026-10-20 |
| CL8 | Importar declarando qué se reconstruyó y qué quedó fijo | Parcial | Alta | Agregar el informe de importación en STEP, IGES, mallas y DXF. | omnicad/io_archivos/f3d_historial.py; tests/test_f3d_historial.py | 2026-10-26 |

## Mejoras › Texto y vectores

Parcial 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| TXT-7 | Fase 7 velocidad (SVG de 5000 nodos en menos de 1 s) | Parcial | Media | Lograr menos de 1 s con el SVG de 5000 nodos. | tests/test_texto_vectores.py | 2026-10-20 |
| TXT-8 | Vectores SVG/DXF y texto como objetos transformables y agrupables | Parcial | Media | Resolver >5000 curvas, deshacer individual en grupos y regiones de Unir perfiles; sin editor de nodos. | tests/test_objetos_vectoriales.py; scripts/bench_objetos_vectoriales.py | 2026-11-04 |

## Mejoras › Rust

Abierto 6.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| RS-R8 | R8 dedupe de filas, soldado y normales suaves | Abierto | Media | Sin empezar. | omnicad/nucleo/malla.py | 2026-10-20 |
| RS-R10 | R10 lectura y escritura de mallas en texto | Abierto | Media | Sin empezar. | omnicad/nucleo/malla.py | 2026-10-20 |
| RS-R12 | R12 quitar aristas ocultas superpuestas (dibujo) | Abierto | Media | Sin empezar. | omnicad/nucleo/dibujo.py:269 | 2026-10-20 |
| RS-R2 | R2 reducir malla (QEM) en Rust | Abierto | Alta | Implementar QEM en Rust; depende de R7. | omnicad/nucleo/malla.py _Editor; clon/rust/src/lib.rs sin malla | 2026-10-20 |
| RS-R6 | R6 remallar isótropo en Rust | Abierto | Alta | Implementar el remallado isótropo en Rust. | omnicad/nucleo/malla.py | 2026-10-20 |
| RS-R7 | R7 núcleo half-edge / topología de malla | Abierto | Alta | Base de R2 y R6. | omnicad/nucleo/malla.py _Topo | 2026-10-20 |

## Mejoras › Auditoría del 2026-10-14

Abierto 8 · Sin verificar 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| AUD-1 | Sin medición de cobertura de tests (pytest-cov) | Abierto | Baja | Agregar pytest-cov como dependencia de desarrollo y medir sin umbral. | grep de pytest-cov/--cov en clon/requirements*.txt, pyproject.toml y .github: sin resultados | 2026-10-20 |
| AUD-2 | Sin lockfile (requirements pineado con == pero sin lock) | Abierto | Baja | Generar un lock (uv pip compile) y usarlo en CI e instaladores. | clon/ no tiene lockfile; clon/requirements.txt pineado con == | 2026-10-20 |
| AUD-3 | Sin verificador de tipos (mypy o pyright) | Abierto | Media | Empezar mypy no estricto sobre nucleo/. | Sin mypy/pyright en clon/pyproject.toml, requirements*.txt ni .github; sin mypy.ini | 2026-10-20 |
| AUD-5 | Seis funciones con complejidad mayor a 20 | Abierto | Media | Reemplazar los if/elif por tablas tipo→función en las funciones señaladas. | registro._convertir; svg._recorrer (conteos completos en ficha) | 2026-10-20 |
| AUD-7 | add_text/edit_text con 33 y 34 parámetros | Abierto | Media | Agrupar las opciones de texto en un dict de opciones documentado. | api/herramientas_vectores.py:185 (conteo por ast: add_text 33, edit_text 34) | 2026-10-20 |
| AUD-8 | Instalador de Windows sin firma de código | Abierto | Media | Comprar certificado y firmar el .exe; hoy solo se documenta el aviso de SmartScreen. | README.md:74 (aviso «Windows protegió su PC») | 2026-10-20 |
| AUD-11 | La CI corre ruff y pytest pero no la prueba de humo | Abierto | Media | Agregar paso de humo offscreen al job test, si corre estable en windows-latest. | .github/workflows/instaladores.yml: job test con escaneo de secretos, ruff y pytest; sin --prueba-humo | 2026-10-20 |
| AUD-4 | Archivos gigantes: 20 módulos pasan las 1000 líneas | Abierto | Alta | Partir de a poco al tocar cada uno (editor_boceto, solidos_crear, boceto, malla, ventana). | wc -l sobre clon/omnicad: 20 archivos >1000 líneas; editor_boceto.py 3800 líneas | 2026-10-20 |
| AUD-9 | Dependencias sin escaneo de CVE (pip-audit nunca corrido) | Sin verificar | Baja | Correr pip-audit una vez cuando el usuario autorice instalarlo. | Sin rastro de pip-audit en .github ni en PROJECT_LOG | 2026-10-20 |
| AUD-10 | El .exe publicado sin probar en una máquina limpia sin Python | Sin verificar | Media | Instalar la Release en una VM limpia y abrir un proyecto. | uar-loop-2026-10-14.md:28 lo deja «pendiente de usuario» | 2026-10-20 |

## Mejoras › Prueba de tortura

Parcial 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| T-18 | Render y respuestas grandes lentas en la API | Parcial | Media | Pasar HLR a un proceso persistente. | tests/test_hallazgos_tortura.py::test_t18_get_scene_info_y_open_document_tienen_modo_resumido | 2026-10-20 |

## Mejoras › Tipografía de la interfaz (2026-10-28)

Abierto 3.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| NOV-tip-2 | Fuente de interfaz: buscador, recomendadas y muestra en combo cerrado | Abierto | Media | Agregar búsqueda, grupo Recomendadas y letra propia en el combo cerrado. | omnicad/ui/preferencias.py (`_combo_fuentes`, `_agregar_familia`) | 2026-10-29 |
| NOV-tip-3 | Colores de texto: selector temático y alternativas legibles | Abierto | Media | Agregar selector temático, alternativa legible y comparación elegido/aplicado. | omnicad/ui/preferencias.py (`CampoColor`, `_Muestra`, `_mostrar_aviso_apariencia`) | 2026-10-29 |
| NOV-tip-4 | Apariencia: vista previa y tamaños de interfaz unificados | Abierto | Alta | Crear muestras vivas y tamaños comunes; validar escalas y ventanas de la ficha. | omnicad/ui/preferencias.py, omnicad/ui/temas.py, omnicad/ui/cinta.py | 2026-10-29 |

## Detalle de lo abierto

### B-240 · RENDERIZAR › interfaz corrupta, controles invertidos y visor negro

- **Historia (movida de la fila, 2026-11-13):** **Qué:** RENDERIZAR › la interfaz se ve corrupta: controles invertidos y duplicados, visor negro **Queda:** Gerardo lo vio en una captura (2026-11-07): textos y botones invertidos verticalmente y repetidos, el área de herramientas en otro lugar, el visor casi todo negro y el ViewCube en varias posiciones. Falta reproducirlo y hallar la causa (FBO, eje Y, `devicePixelRatio`, estados de OpenGL sin restaurar). Lo toma la auditoría de RENDERIZAR (AG-3) como primer ítem. **Evidencia:** `docs/auditoria_renderizar.md`

### P-1c · Wayland nativo: menús emergentes se cierran solos

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Wayland nativo: menús emergentes se cierran solos **Queda:** Necesita PC con Linux nativo (ver P-1b): el fallo solo aparece con Wayland y esta PC es Windows, así que no se pudo reproducir ni probar un arreglo; hoy se fuerza xcb y no molesta. **Evidencia:** omnicad/ui/__init__.py:11-19

### B-378 · Retícula volumétrica lenta con valores por defecto

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Retícula volumétrica › `create_volumetric_lattice` con los valores por defecto (gyroid, celda 5 mm) sobre una caja 80×50×20 tarda 95 s: la caza la marca «colgado» a los 40 s **Queda:** Medido en la VPS (2026-11-13, 2 de 2 en la caza; tiempos con `api.llamar` suelto): celda 20 mm y resolución 6 = 0,9 s; celda 10 mm = 5,4 s; celda 5 mm (defecto) = 95,1 s, así que el tiempo crece más rápido que la cantidad de celdas (x17 al achicar la celda a la mitad). Perfilar dónde se va el tiempo y bajarlo (Rust si hace falta) o avisar antes con una estimación; hoy en la ventana congela sin cancelar **Evidencia:** `clon/tests/corpus_caza/b378_reticula_lenta.json`; `omnicad/api/herramientas_solido_extra.py:412`

### P-8c · Primer arranque guiado: idioma y conexión de agentes

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Primer arranque guiado dentro de la app (idioma, conectar agentes con un botón) **Queda:** Hoy conectar agentes es una tarea opcional del instalador; la app no tiene asistente de primer arranque. **Evidencia:** instalador/windows/omnicad.iss:62,79 (tarea «agentes»); grep de «primer arranque» en omnicad/: sin resultados

### P-2b · Mensajes de API, errores/pistas, CLI y MCP en los dos idiomas (--lang)

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Mensajes de API, errores/pistas, CLI y MCP en los dos idiomas (--lang) **Queda:** Catálogo de mensajes para api/errores.py y descripciones del catálogo; opción --lang en CLI y MCP. **Evidencia:** omnicad/api/errores.py (PISTAS solo en español); omnicad/cli y servidor_mcp sin --lang

### P-28c · Engranajes cilíndricos: variantes faltantes

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Cilíndricos faltantes (doble hélice, espina de pescado, interno, cicloidal, asimétrico, cremalleras helicoidales) **Queda:** Sin programar. **Evidencia:** omnicad/nucleo/engranajes.py (solo evolvente recto/helicoidal)

### P-3a · Add-on de Blender para cuerpos, mallas y materiales

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Add-on de Blender que hable con el puente en vivo (cuerpos, mallas, materiales) **Queda:** El puente existe; falta el add-on de Blender y el intercambio en los dos sentidos. **Evidencia:** omnicad/ui/puente.py (127.0.0.1 + token) existe; sin código de add-on en el repo; solo exporta glTF (io_archivos/gltf.py)

### MP1 · Mini programas Python con panel de campos y pestaña propia

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Mini programas: el usuario crea scripts Python con panel de campos armado solo (distancia, ángulo, cuerpo), pestaña «Mini programas» en la cinta para crear, guardar, correr y compartir **Queda:** Todo. Base ya hecha: `execute_code` (transacción, timeout, deshacer) y el motor de grafos. Se junta con GH7, B5 y PAQ-H5. Un mini programa ajeno puede romper el trabajo: mostrar qué hace y pedir confirmación antes de correrlo. Después, el lienzo de nodos (GH4) para quien no programa. **Evidencia:** `omnicad/api/` (`execute_code`); `docs/grafo.md` «Pendiente»; sin pestaña ni panel de campos en `omnicad/ui/`

### RI-2 · Reconstruir un sólido desde una malla, sin IA

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Reconstruir un sólido desde una malla, sin IA **Queda:** Las piezas de extrusiones, revoluciones, agujeros, empalmes, chaflanes y patrones ya salen (`reconstruct_from_mesh`: las 30 del banco cumplen todas las metas). Faltan las piezas reales que combinan direcciones: cortes con planos oblicuos (vaso inclinado), revolución más prisma, esquinas redondeadas con esferas (hoy el perfil trae los arcos y el empalme no entra) y moleteados. **Evidencia:** tests/test_reconstruir_malla.py::test_un_bloque_vuelve_como_boceto_y_extrusion; scripts/bench_reconstruir.py reales

### CF-1 · DIBUJO: diálogo Crear dibujo completo

- **Historia (movida de la fila, 2026-11-13):** **Qué:** DIBUJO: diálogo Crear dibujo completo **Queda:** Modo Automático, contenido (todo, visible, selección), creación de planos por nivel, documento base, unidades, recuento de planos y tamaño personalizado. **Evidencia:** ui/dibujo.py (solo `DialogoHoja`); capturas `DIBUJO/Crear_dibujo`

### CF-2 · DIBUJO: panel Vista de dibujo

- **Historia (movida de la fila, 2026-11-13):** **Qué:** DIBUJO: panel Vista de dibujo **Queda:** Estilos sombreados, mejorar calidad, aristas de interferencia y de rosca, aristas tangentes (longitud completa, acortado), marcas y líneas de centro por tipo (agujero, cortes redondos, extrusiones redondas, patrón, empalme), orientación con vistas guardadas y referencia/instancia/representación. RH14 solo cubre estilos importables. **Evidencia:** ui/dibujo.py; capturas `DIBUJO/Vista_de_dibujo` y `DIBUJO/Vista_base`

### CF-3 · DIBUJO: menú COTAS completo

- **Historia (movida de la fila, 2026-11-13):** **Qué:** DIBUJO: menú COTAS completo **Queda:** Hechas Línea base y Longitud de arco (2026-11-04, tests/test_dibujo.py). Faltan cota automática, ordenar, organizar, igualar, voltear flechas, recodo y máx/mín. **Evidencia:** nucleo/dibujo.py; capturas `DIBUJO/Menu_de_cotas` y `DIBUJO/Ordenar`

### CF-4 · DIBUJO: notas, tablas y símbolos

- **Historia (movida de la fila, 2026-11-13):** **Qué:** DIBUJO: notas, tablas y símbolos **Queda:** Nota de agujero y rosca, de pliegue, panel de Texto con formato; tablas de plegado, agujeros, personalizada, revisiones y nube; símbolos de rectángulo de tolerancia, identificador de referencia, ángulo, inclinación, arista y boceto; extensión de arista. F9 cubre solo soldadura y acabado. **Evidencia:** ui/dibujo.py; capturas `DIBUJO/Tablas`, `Simbolos_de_dibujo`, `Texto_y_notas`

### CF-5 · DIBUJO: navegador, hojas, cinta y exportar

- **Historia (movida de la fila, 2026-11-13):** **Qué:** DIBUJO: navegador, hojas, cinta y exportar **Queda:** Navegador de dibujo con hojas múltiples, pestañas ADMINISTRAR y UTILIDADES, grupos SÍMBOLOS, INSERTAR e INSPECCIONAR, Exportar DWG y CSV, vista de sección parcial y recortada, boceto de dibujo, patrón de marcas de centro. **Evidencia:** ui/dibujo.py; capturas `DIBUJO/Navegador_de_dibujo`, `Exportar_dibujo`

### CF-7 · Preferencias: páginas que no existen

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Preferencias: páginas que no existen **Queda:** Páginas Dibujo, Configuraciones, Renderizar (valores por defecto), Material, Diseños híbridos y de ensamblaje, Unidades por defecto (Diseño) y Visualización de unidad y valor (faltan 10 de 13 ajustes). **Evidencia:** omnicad/ui/preferencias.py; capturas `INTERFAZ/Preferencias_*`

### CF-8 · Preferencias: opciones sueltas de General y Gráficos

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Preferencias: opciones sueltas de General y Gráficos **Queda:** Hechas: el tamaño del ViewCube (cinco tamaños como Fusion, en Preferencias › General y en el clic derecho del ViewCube, API incluida) y la barra espaciadora que repite el último comando (`general/espacio_repite`) — tanda C11, 2026-11-06; el tema del sistema (`general/tema` = `sistema`: sigue al claro/oscuro de Windows, como «Match Device Theme» de Fusion; el tema queda fuera del MCP, como manda CLAUDE.md) y los presets de ratón Alias, Inventor, PowerMill y SOLIDWORKS (`general/raton`, también en la API; con Inventor, F2/F3/F4 navegan en el visor en vez de Renombrar) — tanda C13, 2026-11-06. Faltan: (a) orientación Y o Z hacia arriba: el combo «Orientación de modelado por defecto» solo ofrece «Z hacia arriba», y darlo vuelta toca el marco de la cámara en 15 lugares de 6 archivos (`ui/visor3d.py`: `ojo`, `desplazar`, `encuadrar`, `mirar_a_plano`, `primitivas_centro_giro` y el sombreado; `ui/render.py` › `u_atras`; `ui/manipuladores.py`; `ui/comandos/comunes.py`, `editar_cara.py` e `inspeccionar.py`) porque hoy todos leen `visor.R` como dirección del mundo, y sin verlo en pantalla no se puede dar por bueno; (b) tipo de diseño por defecto: OmniCAD no tiene tipos de diseño (Pieza/Ensamblaje/Híbrido), es una función que falta (ver CF-6); (c) finalidad de uso: en Fusion solo elige qué sugiere la puesta en marcha, que OmniCAD no tiene; (d) experiencia de puesta en marcha: no hay asistente ni tour de primer arranque; (e) controlador de gráficos: Fusion elige DirectX/Metal/OpenGL para la interfaz y OmniCAD usa el de Qt, sin una opción que se pueda cumplir de verdad. P-2d cubre el idioma. **Evidencia:** tests/test_preferencias.py; omnicad/ui/preferencias.py; capturas `INTERFAZ/Preferencias_General`

### CF-9 · MALLA: Suavizar contorno, Puente e Insertar malla completo

- **Historia (movida de la fila, 2026-11-13):** **Qué:** MALLA: Suavizar contorno, Puente e Insertar malla completo **Queda:** Suavizar contorno (suavidad, iteraciones, anillos) y Puente no existen; Insertar malla solo pregunta la unidad: faltan Voltear dirección, Centro, Mover a suelo, entradas numéricas y Restablecer. MAL-2 y MAL-3 no nombran la paleta de pincel. **Evidencia:** grep sin resultados en api/ y ui/comandos/; capturas `MALLA/` e `INSERTAR/Insertar_malla`

### PLA-1 · Grampa de fijación (Snap Fit): gancho, ranurado y contorno

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Grampa de fijación (Snap Fit): gancho y ranurado paralelos o perpendiculares, gancho y contorno **Queda:** Hecho (2026-11-03): los 3 tipos con puntos manuales, giro Uniforme, extensión Hasta el siguiente o Distancia, API y botón. Faltan selección Automática, giro Independiente o Alineado, Flip y radio de empalme de la base; cabeza y ranura son cajas simples. **Evidencia:** ui/cinta.py:160 (botón gris); docs/brechas_extensiones.md

### PLA-3 · Saliente de fijación de dos lados, con fijador y nervios

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Saliente de fijación de dos lados, con fijador y nervios **Queda:** Hoy es un solo lado: exterior, agujero, alto y desmoldeo. Falta Lado 2, escariado, escalón, fijador y pestaña de nervios. **Evidencia:** api create_boss: volumen 30681,51 en la caja medida; docs/brechas_extensiones.md

### PLA-4 · Labio: tipo Labio y acanalado sobre dos cuerpos

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Labio: tipo Labio y acanalado sobre dos cuerpos **Queda:** Hecho (2026-11-03): labio y ranura base con validación de aristas (B-158). Faltan Cadena tangente, Guía de cara y Avanzado (extensiones, Flip). **Evidencia:** api create_lip_groove: lip_type solo lip o groove; docs/brechas_extensiones.md

### PLA-5 · Reglas de plástico: árbol, editar, biblioteca y quitar la regla

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Reglas de plástico: árbol, editar, biblioteca y quitar la regla **Queda:** Crear, asignar y borrar andan. Falta el árbol, Editar, Nueva desde otra, elegir en el lienzo, quitar desde el navegador y las reglas de fábrica de Fusion. **Evidencia:** ui/comandos/plastico.py; docs/brechas_extensiones.md

### PLA-7 · Patrón geométrico: objeto personalizado y caras curvas

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Patrón geométrico: objeto personalizado y caras curvas **Queda:** Faltan Dirección perpendicular, Cambiar y Expandir. Comprobar en Fusion real si acepta caras curvas: hoy OmniCAD las rechaza. **Evidencia:** api create_geometric_pattern: «necesita una cara plana»; docs/brechas_extensiones.md

### PLA-9 · Simplificar: eliminar operaciones/caras y reemplazar

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Simplificar: Eliminar operaciones, Eliminar caras y Reemplazar con primitivas **Queda:** Eliminar caras, Eliminar operaciones (empalmes, chaflanes y agujeros por tamaño) y Reemplazar con primitivas (caja, cilindro, esfera) andan. Faltan: en Reemplazar, el modo Componentes y las asas; en Eliminar operaciones, elegir a mano y los tipos Extruir, Revolución y Otros; en Eliminar caras, que elija solas las caras vecinas. El defeaturing no quita un chaflán pegado a un empalme ni dos chaflanes contiguos. **Evidencia:** tests/test_reemplazar_primitivas.py; tests/test_simplificar.py; tests/test_comandos_modificar.py::test_eliminar_caras_borra_la_cara_de_un_empalme; docs/brechas_extensiones.md

### PLA-10 · Insertar fijador: panel de biblioteca

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Insertar fijador: panel de biblioteca **Queda:** Hay 5 familias y 14 normas ISO y DIN. Falta buscador, 16 organizaciones, imperial, árbol, favoritos, vistas, columnas, filtros por medida, remaches e inserciones. **Evidencia:** nucleo/fijaciones.py NORMAS; docs/brechas_extensiones.md

### F1 · Engranajes, cremallera y rueda de cadena

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Engranajes, cremallera y rueda de cadena **Queda:** Polea dentada (correa); valores ISO 606 de la rueda de cadena por verificar **Evidencia:** ed0c4dc; nucleo/engranajes.py; timeline/ops_engranaje.py; ui/comandos/engranaje.py; api create_gear, create_gear_pair, create_rack, create_sprocket; tests/test_engranajes.py; tests/test_api_engranajes.py

### F9 · Dibujo: vista interrumpida, soldadura, acabado, ajuste, cotas en cadena

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Dibujo: vista interrumpida, soldadura, acabado, ajuste, cotas en cadena **Queda:** Vista interrumpida, símbolos de soldadura y acabado, ajuste, cotas en cadena y de chaflán **Evidencia:** nucleo/dibujo.py (rayado:520, cota de diámetro ⌀:659; sin esos símbolos); io_archivos/svg_salida.py

### B4 · Vectorizar imagen: vista previa y esquinas

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Vectorizar imagen: vista previa y esquinas **Queda:** Vista previa propia de las curvas. Las esquinas ya andan (Ángulo de esquina); un contorno con una sola punta no se parte. **Evidencia:** tests/test_texto_vectores.py::test_el_angulo_de_esquina_parte_el_contorno_en_tramos_abiertos; 32c9e2d; io_archivos/vectorizar.py:93; ui/comandos/insertar.py:125; api trace_image; tests/test_texto_vectores.py

### B15 · Nodos de geometría: campos, atributos, instancias, zonas de repetición

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Nodos de geometría: campos, atributos, instancias, zonas de repetición **Queda:** Campos, atributos, instancias con realizar y zonas de repetición y simulación **Evidencia:** omnicad/grafo/ (árboles de datos, nodos, horneado); docs/grafo.md; api run_graph, bake_graph, list_graph_nodes; tests/test_grafo.py; tests/test_api_grafo.py

### NOV-brechas_rhino-1 · Notilus Composite para Rhino 8 (novedad automática)

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Notilus Composite para Rhino 8 (novedad automática) **Queda:** Clasificar: complemento de terceros (naval o tuberías) sin equivalente en OmniCAD; decidir si importa **Evidencia:** sin código relacionado; novedad agregada por scripts/novedades.py sin clasificar

### NOV-brechas_rhino-2 · Notilus Scantling para Rhino 8 (novedad automática)

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Notilus Scantling para Rhino 8 (novedad automática) **Queda:** Clasificar: complemento de terceros (naval o tuberías) sin equivalente en OmniCAD; decidir si importa **Evidencia:** sin código relacionado; novedad agregada por scripts/novedades.py sin clasificar

### NOV-brechas_rhino-3 · Notilus Piping: tuberías y HVAC en Rhino (novedad automática)

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Notilus Piping: tuberías y HVAC en Rhino (novedad automática) **Queda:** Clasificar: complemento de terceros (naval o tuberías) sin equivalente en OmniCAD; decidir si importa **Evidencia:** sin código relacionado; novedad agregada por scripts/novedades.py sin clasificar

### GH3 · Catálogo de nodos (≈80 previstos) con tipos de puerto

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Catálogo de nodos (≈80 previstos) con tipos de puerto **Queda:** Faltan solevación, revolución, barrido, divisiones de curva, matrices y lista de valores (64 nodos hoy). **Evidencia:** omnicad/grafo/nodos_basicos.py, nodos_geometria.py, nodos_vectores.py (64 @nodo); tests/test_grafo.py::test_catalogo_por_categoria_y_bien_descripto; test_nodos_de_curvas_y_solidos

### KS7 · Cámaras guardadas con apertura, enfoque y desenfoque (DOF)

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Cámaras guardadas con apertura, enfoque y desenfoque (DOF) **Queda:** Lista de cámaras con nombre del render, apertura, enfoque y desenfoque. **Evidencia:** omnicad/ui/render.py:1404-1409 (solo perspectiva/ortográfica y focal); las vistas guardadas son del visor de DISEÑO (ui/ventana.py:2031)

### KS5 · Biblioteca de materiales: arrastrar, favoritos, copiar aspecto

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Biblioteca de materiales: arrastrar, favoritos, copiar aspecto **Queda:** Faltan arrastrar y soltar la muestra sobre la pieza (en la vista y en el navegador) y «Copiar aspecto» entre piezas. En Fusion arrastrar es LA forma de aplicar un aspecto: cada suelta se aplica al instante (docs/brechas_aspecto.md). **Evidencia:** omnicad/nucleo/aspectos.py (biblioteca, Mis aspectos, favoritos); tests/test_aspectos_api.py::test_menu_de_en_este_diseno_duplicar_renombrar_suprimir_mis_aspectos_y_favoritos; grep dragEnter/copiar_aspecto sin resultados

### VR5 · Corte en el render (Clipper) con tapa de color

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Corte en el render (Clipper) con tapa de color **Queda:** Control «Clipper» en RENDERIZAR (ventana y render_image) con tapa de color; el motor de CPU ya recorta por planos y dibuja la tapa. **Evidencia:** omnicad/nucleo/render_estilos.py (recortar, capas_a_objetos) y get_viewport_image con section_view; grep clipper en ui/render.py sin resultados

### IA-2 · Proveedores API: Anthropic y OpenAI compatibles

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Proveedores por API: Anthropic Messages y OpenAI compatible (OpenAI, OpenRouter, Ollama) **Queda:** Queda: streaming SSE (hoy la respuesta llega completa); prueba real con Ollama (no está instalado en esta PC); devolver los bloques de pensamiento de Claude entre vueltas; prueba paga solo con OK de Gerardo. **Evidencia:** omnicad/asistente/proveedores/anthropic.py; omnicad/asistente/proveedores/openai_compat.py; tests/test_asistente_proveedores.py

### IA-11 · Herramientas eficientes desde el chat del asistente

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Todas las herramientas desde el chat del asistente, de forma eficiente (índice en el prompt, buscar_herramientas por consulta, find_tools/call_tool en el MCP de los CLI, caché del prompt) **Queda:** Queda: medir los tokens por paso con el uso que reporta la API (Anthropic u OpenAI: gasta, solo con OK de Gerardo); Codex informa 56,8 mil de entrada en un pedido de una vuelta, que suma su propio prompt de sistema (lo nuestro mide 19,2 mil). **Evidencia:** omnicad/asistente/herramientas.py; omnicad/servidor_mcp/servidor.py; tests/test_asistente_alcance.py; prueba real con Codex del 2026-10-25

### SC7 · Análisis del estudio de movimiento: gráficos, rastro, choques

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Análisis del estudio de movimiento: gráficos, rastro, choques **Queda:** Faltan gráficos de valor, velocidad y aceleración y el rastro de un punto. **Evidencia:** omnicad/api/herramientas_ensamble.py:703-714 (motion_study con check_interference por valor); tests/test_api_ensamble.py:230

### CL1 · Cambio de agente con vista previa y control de revisión

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Cambio de agente con vista previa y control de revisión **Queda:** Queda: control de revisión del documento (expected_revision) para los agentes externos del puente en vivo. El Asistente de la app ya muestra el plan y pide Aplicar antes de cambiar (IA-5). **Evidencia:** omnicad/ui/asistente.py (_Tarjeta); tests/test_asistente_ui.py; grep revision/expected_revision sin resultados en api/protocolo_puente.py y ui/puente.py

### P-5b · Mejoras de vectores, SVG, edición y texto según Blender

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Resto de mejoras de vectores, SVG, edición y texto según el manual de Blender **Queda:** Sigue la lista priorizada de docs/referencia/brechas_blender.md (vista previa de trazos, esquinas, texto avanzado). **Evidencia:** tests/test_texto_vectores.py (64 pruebas); B4 queda con vista previa y esquinas pendientes

### P-6d · Revisar ensamblaje, animación, mallado, historial y movimiento de piezas

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Revisar ensamblaje, animación, mallado, historial y movimiento de piezas **Queda:** Revisión general sin cerrar: faltan conjuntos de contacto, uniones leva/tornillo y gráficos del estudio de movimiento. **Evidencia:** omnicad/api/herramientas_animacion.py (15 herramientas); herramientas_ensamble.py:621,703 (create_rigid_group, motion_study); tests/test_api_animacion.py; tests/test_ensamblar.py

### P-4a · Revisar entero el motor de render, materiales, colores e iluminación

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Revisar entero el motor de render, materiales, colores e iluminación **Queda:** Hoy solo hay motor local OpenGL (GLSL 120) y CPU (con Rust); falta revisión completa y las listas KeyShot/V-Ray. **Evidencia:** omnicad/ui/render.py:1589-1590 (combo Motor: GL y CPU); omnicad/nucleo/render_cpu.py; tests/test_render.py; tests/test_render_aspecto.py

### H-75 · Cuerpos negros planos y letras negras invisibles sobre placas negras

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Un cuerpo negro se ve plano en el visor: arriba y costados del mismo negro, y una letra negra sobre una placa negra desaparece **Queda:** El visor ilumina con luces fijas (difuso × color, brillo chico); con color 0 solo queda el brillo especular en ángulos justos. Fusion ilumina con el entorno y el negro brillante refleja. Probar un reflejo de entorno simple o un mínimo de luz en el visor, y compararlo con Fusion. Visto en el video de Gerardo del 2026-11-05 (docs/brechas_aspecto.md). **Evidencia:** clon/omnicad/ui/visor3d.py (LUZ_AMBIENTE, LUZ_BRILLO, GL_SPECULAR)

### B9 · Limpieza de malla ampliada

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Limpieza de malla ampliada **Queda:** Disolver por ángulo, hacer plano y simetrizar (triángulos a cuadriláteros no cabe) **Evidencia:** c1c40f2; nucleo/malla.py:2403-2420; api clean_mesh; timeline OpLimpiarMalla; tests/test_api_malla.py::test_limpiar_deja_una_malla_cerrada_y_es_editable

### RH16 · Modos de pantalla por objeto y poses guardadas

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Modos de pantalla por objeto y poses guardadas **Queda:** Modos de pantalla por objeto (Pluma, Técnico, Fantasma), selecciones con nombre y disposición de ventana **Evidencia:** ui/visor3d.py:70 ESTILOS (global); ui/navegador.py:221 y ui/ventana.py:2031 (vistas guardadas); api set_body_opacity

### RH17 · Bloques vinculados a un archivo que se recarga

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Bloques vinculados a un archivo que se recarga **Queda:** Vínculo a un archivo externo que se recarga si cambió («Actualizar si cambió el archivo») **Evidencia:** 4b50c6f; api realize_copies («Hacer única»); timeline/ops_ensamblar.py:499 OpInsertarDiseno; tests/test_pl8_instancias.py

### KS3 · Material completo: refracción, subsuperficie, anisotropía, emisivo, mapas

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Material completo: refracción, subsuperficie, anisotropía, emisivo, mapas **Queda:** El render ignora translucidez, emisividad, relieve y resalte; faltan IOR, subsuperficie y mapas. **Evidencia:** omnicad/nucleo/aspectos.py:5-11,35-43 (el modelo los guarda, el render usa solo color, metálico, aspereza, transparencia, barniz, patrón)

### SC19 · Borrador de issue de GitHub desde un error, con contexto y captura

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Un error de operación abre un borrador de reporte (issue de GitHub) con el contexto y una captura **Queda:** SolidCraft arma, desde un error o la Ayuda, un borrador editable con versión, paso que falló, parámetros y una captura opcional que la persona revisa; abrir GitHub no lo envía. Acá hay informes de error (herramienta de revisión) pero ningún borrador listo para publicar. Nunca se envía solo (regla de salida hacia afuera). **Evidencia:** grep issue/borrador en clon/omnicad/ui sin resultados

### CL8 · Importar declarando qué se reconstruyó y qué quedó fijo

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Importar declarando qué se reconstruyó y qué quedó fijo **Queda:** El .f3d ya declara al abrir su historial sin traducir y los bocetos que reconstruyó; falta el mismo informe en STEP, IGES, mallas y DXF. **Evidencia:** omnicad/io_archivos/f3d_historial.py; tests/test_f3d_historial.py::test_abrir_un_f3d_con_historial_avisa_lo_que_no_se_tradujo

### TXT-7 · Fase 7 velocidad (SVG de 5000 nodos en menos de 1 s)

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Fase 7 velocidad (SVG de 5000 nodos en menos de 1 s) **Queda:** Bajar de 2,5 s a menos de 1 s el SVG de 5000 nodos. **Evidencia:** El log midió 2,5 s; la meta < 1 s no se cumple. tests/test_texto_vectores.py

### TXT-8 · Vectores SVG/DXF y texto como objetos transformables y agrupables

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Los vectores importados (SVG/DXF) y el texto se manejan como un objeto: mover, escalar, rotar, alinear, agrupar, pivotear, desfasear, unir y separar **Queda:** Hecho 2026-11-04: el objeto es una matriz afín sobre las curvas (los ids y las firmas no cambian), con panel de tiradores y medidas exactas, API/MCP/CLI de 15 herramientas y formato de proyecto 2. Queda: editar el trazado nodo a nodo (decidido no hacerlo), más de 5000 curvas por objeto (ver TXT-7), deshacer/rehacer de un objeto dentro de un grupo desde la API (hoy se deshace el grupo entero) y «Unir perfiles» deja los originales ocultos pero con su geometría (sus regiones siguen existiendo: hay que elegir la región combinada al extruir). **Evidencia:** clon/omnicad/restricciones/objetos.py; clon/omnicad/ui/objetos_vectoriales.py; clon/omnicad/api/herramientas_objetos_vectoriales.py; tests/test_objetos_vectoriales.py::test_api_transformacion_parametrica_extruye_y_sobrevive_guardar_undo; scripts/bench_objetos_vectoriales.py

### RS-R2 · R2 reducir malla (QEM) en Rust

- **Historia (movida de la fila, 2026-11-13):** **Qué:** R2 reducir malla (QEM) en Rust **Queda:** Depende de R7. Medido 2026-10-31: reducir 50 % a 50 k triángulos 4,4 s. **Evidencia:** omnicad/nucleo/malla.py _Editor; clon/rust/src/lib.rs sin malla

### RS-R6 · R6 remallar isótropo en Rust

- **Historia (movida de la fila, 2026-11-13):** **Qué:** R6 remallar isótropo en Rust **Queda:** Sin empezar. Medido 2026-10-31: remallar a 50 k triángulos 8,2 s. **Evidencia:** omnicad/nucleo/malla.py

### AUD-5 · Seis funciones con complejidad mayor a 20

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Seis funciones con complejidad mayor a 20 **Queda:** Reemplazar los if/elif por tablas tipo→función en las funciones señaladas. **Evidencia:** Conteo propio por ast (aprox.): registro._convertir 40, svg._recorrer 46, solver.auto_restringir 39, entidades.resolver 29, boceto_desde_primitivas 33, fuentes._tabla_kern 24

### T-18 · Render y respuestas grandes lentas en la API

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Render y respuestas grandes lentas en la API **Queda:** HLR en un proceso persistente: medido y diferido **Evidencia:** tests/test_hallazgos_tortura.py::test_t18_get_scene_info_y_open_document_tienen_modo_resumido

### NOV-tip-2 · Fuente de interfaz: buscador, recomendadas y muestra en combo cerrado

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Fuente de la interfaz: la lista no tiene buscador ni grupo de recomendadas, y el combo cerrado no muestra la forma de la letra elegida **Queda:** Hecho el 2026-10-29: cada familia de la lista se escribe con su propia letra y la lista abre acotada (14 filas con barra). Falta: caja de búsqueda dentro de la lista, grupo «Recomendadas» arriba (hoy solo van primero las de lectura fácil) y la fuente elegida mostrada con su letra en el combo cerrado. Pedido de Gerardo del 2026-10-29 (captura de Preferencias a 109 % y video 09-38-04), para una sesión nocturna. **Evidencia:** omnicad/ui/preferencias.py (`_combo_fuentes`, `_agregar_familia`)

### NOV-tip-3 · Colores de texto: selector temático y alternativas legibles

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Colores de texto: el selector es el de Qt, sin el tema de la app, y un color rechazado solo avisa «probá uno más claro» **Queda:** Hecho el 2026-10-29: cada fila muestra el color real (nunca el código), marca en rojo el rechazado y el aviso va en criollo. Falta: selector de color con el tema de la app, proponer con un clic un color parecido que sí se lea, y mostrar «elegido» frente a «aplicado» cuando se rechaza. **Evidencia:** omnicad/ui/preferencias.py (`CampoColor`, `_Muestra`, `_mostrar_aviso_apariencia`)

### NOV-tip-4 · Apariencia: vista previa y tamaños de interfaz unificados

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Preferencias › Apariencia no tiene vista previa propia, y los espacios y tamaños de la interfaz no están en un solo lugar **Queda:** Un panel de muestras (botón, campo, texto normal y secundario, acento y una cota del boceto) que cambie al instante con fuente, tamaño y colores; y valores comunes (espacios, radios, alturas) en un solo lugar para que todo escale parejo con letra grande. Validar a 100, 125 y 150 % y en 1024×640 y 800×520, con capturas antes y después. Pedido de Gerardo del 2026-10-29, para una sesión nocturna. **Evidencia:** omnicad/ui/preferencias.py, omnicad/ui/temas.py, omnicad/ui/cinta.py
