# Changelog

Cambios destacados de cada versión publicada de OmniCAD, en español. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [No publicada]

### Agregado
- **Registro de uso local**, apagado de fábrica y sin envío a la red: escribe un JSONL con tiempos de comandos y
  operaciones, errores, bloqueos de la interfaz, cuadros del visor y memoria; lo resume en un detector de problemas
  y permite seguirlo en vivo con `omnicad registro --seguir --json`. Se prende en Preferencias › General, con
  `--registro` o con `set_usage_logging`; el informe queda en la carpeta del registro y nunca escribe solo en
  `docs/seguimiento/`. No guarda chat, contenido de archivos, rutas fuera del proyecto ni texto libre.

## [0.1.4] — 2026-10-26

### Agregado
- **Asistente IA** dentro de OmniCAD (panel a la derecha, ícono, atajo y Ayuda › Asistente): chat que diseña y modifica
  la pieza con las herramientas de la app. Funciona con API (Anthropic y compatibles con OpenAI) o con tu suscripción
  (Claude Code, Codex y OpenCode). Modos Guiar, Hacer y más, biblioteca de prompts, historial de chats, adjuntos
  (PDF, PNG, JPG, SVG, DXF; clip, Ctrl+V o arrastrar), permisos con «Aplicar», «Deshacer este pedido» y cancelar con
  vuelta atrás, «esto» = lo que tenés seleccionado, vistas «Antes» y «Después», instrucciones propias (generales y por
  proyecto), acceso a todas las herramientas sin gastar contexto, modelos y esfuerzo automáticos en Preferencias,
  tres puntos animados mientras piensa y respuestas a «¿cómo se hace…?» con la ayuda local (`search_help`).
- **Boceto** (fases 0 a 9 del plan, como Fusion): rehacer propio, Suprimir y Voltear; AutoConstrain completo con su
  diálogo (conflictos visibles en rojo, F5 «Qué choca»); cotas como Fusion (driven, nombres, entre curvas, modo
  centro/tangente, cuadrante del ángulo, menú previo con clic derecho, todas arrastrables); dibujar con precisión,
  modificar, patrones y proyección asociativa; splines con manijas y peine de curvatura; sección de malla y Boceto 3D;
  inferencia de tangentes, perpendiculares y horizontales en más herramientas; clic derecho para salir de la herramienta.
- **Sólido** (tandas A a D): Revolución «A objeto», Nervio y Red con desmoldeo, Barrido con superficie guía, Solevación
  y Empalme con condición suave G2, chaflán con esquina «Inglete», Patrón y Simetría de caras, componentes y operaciones,
  mover caras, Dividir cara por vector o punto más cercano, Sólido envolvente, Volumen de fluido, reglas de plástico,
  retícula volumétrica (gyroid, Schwarz P/D), reconocer funciones, buscar componentes similares, conjuntos de selección,
  preajustes de comandos, Consejos de diseño y primitivas sobre cualquier plano o cara.
- **OmniKernel** como segundo motor geométrico, elegible en Preferencias.
- Insertar derivación asociativa (`insert_derive`), Guardar como malla como Fusion (`export_mesh`), menús del
  navegador como Fusion (componente raíz y opciones del cuerpo), opacidad, aislar, Aspecto y material desde el menú
  del cuerpo; ola ANIMACIÓN del MCP/CLI.
- Tubería, Bobina (tipo Espiral) y Repujado como Fusion (cadena tangente, alineación, invertir normal).
- Rendimiento: detección de perfiles en Rust (un boceto con 200 «W»: 3,9 s → 0,3 s), render CPU que tesela según los
  píxeles (80 álabes: 17,9 s → 2,7 s), unión de cuerpos que mide por cajas y caras (booleanas de 3-8 s → ~10 ms),
  solver de bocetos más rápido, memoria por paso y autoguardado en hilo.
- MCP/CLI: 349 herramientas en 17 grupos (eran 190 en 13), con `list_assistant_models`, `search_help`,
  `find_features`, `move_faces`, `manage_command_presets`, `manage_selection_sets` y más.

### Corregido
- Sólido: rosca externa a izquierdas, vaciado sin caras que dejar, agujero con punto fuera de la cara, unión sin
  contacto, revolución de más de 360°, inglete lejos del origen, Desfase que reabre pasos de cara (SOL-1 a SOL-6,
  SOL-31 a SOL-33, SOL-37 y los de la revisión de las tandas).
- Boceto: validación de entradas y de la API (B-88 a B-93), solver y geometría (B-96 a B-103), perfiles de un boceto con
  mucho texto, tope de memoria por fuente SHX.
- Bobina: flecha de altura y asa de diámetro alineadas con el plano elegido; calcomanía centrada en el rango real de
  una cara cilíndrica (B-75); ocultos que se guardan y encuadre por caja proyectada (B-82, B-73).
- `execute_code` en vivo ya no congela la ventana y se puede cancelar; el autoguardado no guarda mientras corre (B-16);
  una caída nativa del kernel en una tarea aislada vuelve como error claro (B-48); la cadena de uniones sigue al
  componente movido (B-71); extruir cara, cota de boceto movible y asas de Extruir superficie (B-83).
- Chaflán: el error informa la distancia máxima posible.
- Roscas modeladas: un tornillo (Rosca) y su tuerca (Agujero roscado) sobre el mismo eje encajan sin girar ninguno,
  aunque una cara tenga el eje al revés. ⚠ Las roscas interiores de documentos viejos quedan medio paso corridas al
  recalcularse: si se había girado una pieza para compensar, hay que sacar ese giro.
- `check_printability`: ya no marca paredes finas falsas en aristas agudas (un álabe inclinado cortado a ras daba
  «Pared de 0,01 mm» e «Imprimible: NO»).
- `sketch_from_spec`: las líneas seguidas comparten la esquina; mover un vértice con `move_sketch_point` ya no abre
  el perfil.
- Modo en vivo: el MCP espera 300 s a la app (antes 120 s); un `motion_study` largo con choques ya no corta con
  `APP_NOT_RESPONDING` mientras la app sigue calculando.

## [0.1.3] — 2026-10-17

### Agregado
- Render y materiales: render en Rust opcional (PyO3) para `get_viewport_image` (rasterizador, sombras y oclusión;
  imágenes idénticas byte a byte, caja 2,13 → 1,14 s; sin el módulo compilado cae al numpy de siempre); panel
  **Aspecto** con «Aplicar a» cuerpos o caras, biblioteca por familias con buscador, Mis aspectos, Favoritos,
  «En este diseño» y editor de materiales, en Diseño y en RENDERIZAR; la veta de la madera se ve y corre a lo largo
  de cada pieza.
- **Calcomanías**: sobre caras curvas (cilindro desarrollado por arco, caras tangentes), panel completo y gizmo de
  seis controles como Fusion; atadas a su cuerpo (se mueven, se ocultan y se suprimen con él), con carpeta propia en
  el navegador y herramientas MCP/CLI (`set_decal`, `decal_view`); ahora también se dibujan en RENDERIZAR.
- Roscas y tolerancias: familias de rosca, clases ISO 965 / ASME B1.1, ajustes ISO 286 y Agujero con holgura,
  cónico, Hasta y Referencias.
- Engranajes, cremallera, rueda de cadena ISO 606 y eje escalonado; revisión de geometría e impresión 3D y Reparar
  cuerpo; grafo de nodos sin ventana (tipo Grasshopper; `run_graph` / `bake_graph`).
- Grupo «malla» del MCP/CLI, Limpiar malla y exportar glTF/GLB; patrones avanzados (en puntos, en ruta con giro,
  multitransformar, patrón de operaciones) y copias ligeras (instancias) con `realize_copies`.
- Desfase de caras, aristas y curvas de boceto, Quitar empalmes, reordenar pasos (`move_feature`), repujado en varias
  caras, Apoyar en el plano y exportar líneas ocultas a SVG.
- Texto: panel Carácter (kerning, inclinación, escalas, versalitas, subrayado/tachado) y editor de texto con cursor.
- Navegador: selección sincronizada con la vista, menús contextuales de grupo, boceto y calcomanía como Fusion,
  buscador por nombre; tira de comandos sugeridos, globo de ayuda con imagen, menú «Más» y buscador en Preferencias.
- Abrir `.f3d` de Fusion con cada componente en su lugar y las copias como instancias.
- Guardado y recuperación: pregunta «¿Guardar los cambios?» al cerrar, crear o abrir; autoguardado que se borra al
  guardar bien; diálogo «Documentos recuperados»; informes de error por sesión.
- MCP/CLI: boceto completo, ensamble, chapa y materiales; 190 herramientas en 13 grupos (eran 80 en 8 grupos).
- Ejemplo en el README: un motor turbofán a escala 1:1 armado por un agente de IA en la app en vivo, con su render.

### Corregido
- Prueba de tortura: 18 hallazgos (T-01 a T-18); el cálculo que podía colgar la app (autointersección y líneas
  ocultas de formas B-spline) corre ahora en un proceso aparte con tope de tiempo.
- Tanda de bugs de los reportes: asociatividad de perfiles (re-vinculado con aviso), uniones robustas, booleanas con
  avisos de tangencia y coplanaridad, repair que no empeora, roscas largas y chicas, deflexión por pieza en el
  render, fold en pestaña base y mensaje de versión al abrir una receta con operación desconocida; las uniones ya no
  pierden material ni dejan el cuerpo partido en silencio (B-52, B-28).
- Al elegir un color en Aspecto, la selección se marca solo con el contorno y deja ver el color real.

### Seguridad
- MCP `--http`: token Bearer obligatorio (`mcp_http.json` + middleware); tope de 512 MB por miembro del ZIP al
  leer proyectos (`io_archivos/proyecto.py`) y topes también en 3MF y F3D; permisos 0o600 en los JSON de información.
- CI: un job de tests (pytest y ruff) y un escaneo de secretos corren antes de publicar los instaladores; permisos
  del workflow acotados y actions pineadas a SHA.

## [0.1.2] — 2026-10-10

### Agregado
- Texto y vectores: catálogo de fuentes completo (sistema, usuario, variables) y texto sobre una curva.
- Insertar SVG/DXF e imagen vectorizada en el boceto abierto; unir/restar/intersecar perfiles, desfase y
  marco para mover, escalar, girar y espejar.

## [0.1.1] — 2026-10-10

### Corregido
- Ola 1 de bugs de la Prueba 10 y de las pruebas de uso.
- Normal de caras planas con ejes indirectos; pivote de Mover en mallas; deshacer incremental.
- Aviso de cotas por parámetro.

### Cambiado
- El patrón plano de chapa pasa a su propio modo, como en Fusion.
- README con cómo descargar los instaladores y listas de brechas de otros programas.

## [0.1.0] — 2026-10-09

Primera versión pública (alfa), probada en Windows y en Ubuntu 24.04 sobre WSL2.

### Agregado
- CAD 3D paramétrico con timeline de pasos, parámetros con unidades y expresiones, bocetos 2D con solver de
  restricciones, sólidos, superficies, chapa metálica, mallas y ensamblaje básico (kernel OpenCascade).
- Instaladores: Windows (.exe, Inno Setup) y Linux (AppImage), armados y publicados por GitHub Actions en
  cada etiqueta `v*`; portada al abrir e ícono de la app.
- Capa para agentes IA: servidor MCP y CLI `omnicad` desde un catálogo único de herramientas, con modo en
  vivo sobre la ventana abierta.
- Rendimiento: arranque rápido (scipy y la malla se cargan al usarlos) y mallas en la placa una sola vez con
  menos detalle a la distancia.

---

El registro de desarrollo detallado (bitácora por sesión, con verificaciones) está en
[PROJECT_LOG.md](PROJECT_LOG.md).
