# Changelog

Cambios destacados de cada versión publicada de OmniCAD, en español. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [No publicada]

### Agregado
- **Preferencias › «Asas y superposiciones»**: color, tamaño y opacidad de lo que se dibuja sobre el visor (asas, flechas
  y superposiciones), también por MCP/CLI.
- **Anillo de ángulo como el de Fusion** para el ángulo de Extruir, la torsión del Barrido, el giro de la Revolución y el
  ángulo de despegue de la Solevación (anillo de 360° con marcas cada 90° y caja de valor al pasar el ratón).
- **Asas nuevas y más parecidas a Fusion**: flecha del Peso de despegue en cada perfil de la Solevación, asa-puntero azul
  para el radio del Empalme, asas para los desfases y el giro del Repujado, y flechas del manipulador ámbar con contorno
  oscuro que salen hacia afuera de la cara. La caja de valor de las asas tiene el «⋮» de parámetros y los sugiere al
  teclear.
- **Timeline**: elegir varios pasos y borrarlos de una vez (menú «Eliminar N pasos» o Supr), en un solo paso de
  deshacer; `delete_feature` acepta una lista.
- **Boceto**: Cota de una línea sola horizontal, vertical o alineada según dónde se ubique; Recortar arrastrando sobre
  varios tramos; Empalme y Chaflán por vértice; botones para Proyectar a superficie y Curva de intersección;
  Buscar subrestringidos y Calcular boceto en la Paleta; arrastrar filas del árbol a un grupo; patrones con
  expresiones que siguen a los parámetros; spline de control hasta grado 5 y arco tangente con radio y barrido.
- **Sólido**: Extruir «Dos lados» con tipo de extensión propio en el lado 2, «Desfase de inicio» con Inicio › Objeto,
  conicidad desde planos inclinados, «Ángulo de conicidad» a la vista; Nervio y Red toman el desmoldeo y el espesor de
  la regla de plástico; el Barrido sólido ofrece Estirar.
- **Superficie**: Extruir y Revolución de superficie eligen perfiles cerrados y caras planas en la ventana; Tubo sigue
  curvas de Boceto 3D.
- **Ensamblar**: restricciones de componentes Alinear, Ángulo, Centro y Tangente (planos, cilindros, esferas, conos,
  toros, aristas y «Todas las caras»), con tabla de filas, nombre y desfase por fila, límites de desfase y «Usar desfase
  como apoyo».
- **Construir**: `get_scene_info` informa planos, ejes, puntos y SCU; la curva de fusión toma aristas del modelo.
- **Rosca**: tolerancias con las tablas de Fusion (incluidas las métricas poco comunes), tamaño inicial con tabla para
  ANSI, GB y GOST, y previa que deja en azul la cara elegida y las crestas, con la hélice como en Fusion.
- **Linux**: la app y las pruebas andan en Linux (tipografías sustitutas para Arial y Times New Roman, cierre completo
  con `xvfb-run`).
- **Importar**: un STEP o IGES se lee en un proceso aparte; un archivo alterado da un error claro en vez de cerrar la
  app, y cada ocurrencia «Nombre:N» de un STEP de Fusion es un componente.
- **Caza automática de errores**, con temas nuevos como «pieza real», y `probar_todo` para correr todas las pruebas
  automáticas con un solo comando.
- MCP/CLI: 421 herramientas en 17 grupos (eran 386).
- Los `.omnicad` muestran la vista del modelo en el Explorador de Windows.

### Cambiado
- **Velocidad**: el solver del boceto 3D resuelve tangentes en 11,5 ms (antes 214 a 371 ms); un patrón de 1000 copias en
  un boceto pasa de 104 s a 16 ms; Extruir con muchos perfiles arma la previa una sola vez y no se traba; el análisis de
  sección de una rosca modelada pasa de 32 s a 0,3 s; la hélice larga de la rosca se barre de una vez; Aceptar o Cancelar
  un comando redibuja el visor una sola vez.
- **Ventana más fluida**: abrir un STEP pesado deja de congelarla (de 616 s a 91 s en una impresora completa); las
  previas de Engrosar, Desfase de superficie y desfase de caras con rosca modelada van a un proceso aparte.
- Extruir con el perfil dibujado sobre la cara de un cuerpo arranca en «Unir», como Fusion; el tamaño de la Rosca pone
  el diámetro de toda la cara, también fuera del tramo roscado.
- Las asas de Empalme, Chaflán, Vaciado, Engrosar, Pulsar/tirar, Desfases, Inclinación y Extruir frenan en el límite de
  la pieza y avisan dónde y por qué.
- Con el boceto abierto, el panel del comando va a la izquierda de la paleta y no tapa el Aceptar.
- Los deslizadores de Isocurva y Curvatura en peine topan en 20 y aceptan decimales tecleados.
- Los textos que ve el usuario (errores, ayudas y sugerencias) ya no nombran a Fusion.
- Los análisis de INSPECCIONAR no cortan, rayan ni pintan cuerpos ocultos.

### Corregido
- **Boceto**: arrastrar un punto totalmente restringido ya no deforma el perfil; el desfase de splines, elipses y
  ranuras queda totalmente restringido; Escala, Mover, Copiar/Pegar y Recortar ya no rompen un perfil con chaflán ni
  dejan restricciones sueltas; las cotas de ángulo y de distancia entre líneas no paralelas se rechazan como en Fusion;
  Supr borra el resto cuando el recuadro toma el origen.
- **Sólido**: Vaciado con un espesor que cruza la pared, Barrido con una conicidad que hace crecer el perfil, un agujero
  que vacía el cuerpo y empalmes o chaflanes que rellenan la cavidad dan un error claro en vez de un resultado malo o un
  cierre de la app; Repujado con Envolver ya no da otra vuelta; el desfase de cara ya no mueve la otra mitad de una cara
  partida.
- **Extruir**: la caja de selección elige todos los perfiles; un clic sobre el borde elige el perfil, no la curva; una
  extrusión ya no pierde perfiles al agregar líneas al boceto; una cara de otro plano pasa a ser «Hasta objeto».
- **Superficie**: la solevación de splines cerrados ya no sale plegada, Nervio y Red llegan a caras oblicuas, y el
  desmoldeo con ángulo negativo inclina la pared ya recortada.
- **Ensamblar**: las uniones en arista circular y las de inicio/fin de una arista recta siguen al cuerpo al girar el
  padre; el componente hijo y el agujero creados después de una unión la siguen al accionarla.
- **Rosca**: sobre un eje más fino que el núcleo o una cara más gruesa que la rosca se comporta como Fusion; la clase sin
  tabla modela el diámetro mayor en el centro de la tolerancia; un tamaño extremo o una holgura negativa dan un mensaje
  claro.
- **Construir**: un plano en ángulo no salta al girar la arista, un SCU con X paralelo a Z y un punto entre aristas que
  no se cortan dan error, y una construcción que se referencia a sí misma se rechaza.
- **Archivos y MCP**: un nombre con carácter inválido ya no aborta el guardado ni la exportación glTF; una receta con ids
  repetidos o mal formados se rechaza al cargarla; una referencia que no existe nombra el argumento y sugiere parecidos.

## [0.2.0] — 2026-11-02

### Agregado
- **Reconstruir sólido desde una malla, sin IA** (`reconstruct_from_mesh`): convierte un STL, OBJ o 3MF de extrusiones,
  revoluciones, agujeros, empalmes, chaflanes y patrones en una pieza con historial. Trae un banco de 30 piezas con
  respuesta conocida, `compare_to_mesh` y un Mapa de desviación (INSPECCIONAR) para ver dónde la pieza difiere de la
  malla.
- **Parámetros** con lector propio de expresiones (sin `eval`), 35 familias de unidades, funciones y constantes como
  Fusion, parámetros del modelo y de usuario, y diálogo nuevo; renombrar un parámetro actualiza pasos, cotas, textos y
  configuraciones.
- **CONSTRUIR** completo: planos, ejes y puntos con todos sus modos en un panel común, con el panel de información
  compartido.
- **INSPECCIONAR** con las 15 herramientas: Medir con filtro, precisión y unidades secundarias, Interferencia con tabla
  y quitar volumen (`remove_interference`), Desmoldeo, Accesibilidad, Radio mínimo, Cebra, Curvatura, Sección, mapas de
  entorno y centro de masa. Incluye **Sustainability Insights** (huella de carbono con materiales propios) y grupos de
  caras.
- **Texto sobre una curva** y su extrusión: cada letra y cada curva forman sus perfiles aparte, con espaciado y altura
  por fuente como Fusion (`Text_height` queda como parámetro).
- **Boceto**: ayudas de dibujo («sketch inteligente»: alineaciones, intersecciones, paralela y colineal, alternar y
  bloquear), paneles de Simetría, Desfase con signo y vista previa viva, Escala, Mover/copiar y patrones circular y
  rectangular; restricciones auditadas y tangente con arcos en 2D y 3D; «Atenuar el resto» en proyecciones perdidas.
- **Sólido**: Editar cara por el contorno, solevación de superficie, Dividir cara, patrones de sólido revisados
  (rectangular, circular, trayectoria, puntos y multitransformación; «Optimizado» patronea caras de verdad), clase de
  rosca y Análisis de sección con color y rayado.
- **Ensamblar**: arrastrar componentes con Capturar y Revertir, modos de origen «Entre dos caras» e «Intersección de dos
  aristas», bola y vínculo, **subensamblajes** (componentes con padre y grupo rígido con hijos).
- **Superficie**: barrido con guías, solevación con condiciones, primitivas, tabla de Coser y avisos de esquina sin
  cortar.
- **Interfaz**: paneles movibles y preajustes en la cabecera, paneles de herramienta con un sistema común, paneles de
  Render y Carácter con barra en ventanas bajas, y asas de arrastre bien definidas (flecha inclinada hacia la cámara,
  contorno oscuro, cajas de valor que no se pisan, tríada de la Sección).
- **Rendimiento con Rust**: Zstandard para el `.f3d` y BVH de rayos; un **trabajador persistente** que edita con muchos
  pasos sin rehacer todo el documento, y vista previa de piezas pesadas en ese mismo trabajador (primera previa como
  antes; las siguientes en 0,05 a 0,22 s en una placa de 76 caras, contra 1,3 a 1,5 s).
- MCP/CLI: 386 herramientas en 17 grupos (eran 349), con las de Reconstruir, comparar contra malla, quitar
  interferencia, grupos de caras, Editar cara y huella de carbono.
- **Registro de uso local**, apagado de fábrica y sin envío a la red: escribe un JSONL con tiempos de comandos y
  operaciones, errores, bloqueos de la interfaz, cuadros del visor y memoria; lo resume en un detector de problemas
  y permite seguirlo en vivo con `omnicad registro --seguir --json`. Se prende en Preferencias › General, con
  `--registro` o con `set_usage_logging`; el informe queda en la carpeta del registro y nunca escribe solo en
  `docs/seguimiento/`. No guarda chat, contenido de archivos, rutas fuera del proyecto ni texto libre.

### Cambiado
- Las booleanas (Unir, Cortar, Intersecar) comprueban cuánto comparten las piezas y avisan o fallan en vez de dar un
  resultado malo en silencio; el volumen de formas libres finas (una lente de dos esferas) se integra con más precisión.
- El texto nuevo mide su altura como la «A» de su fuente, como Fusion.
- Un error de geometría llega entero al panel («No se pudo calcular la vista previa: …») y no se corta a 200 caracteres.
- Cancelar una vista previa pesada ya no mata el proceso de cálculo: la respuesta se descarta y la siguiente espera su
  turno.

### Corregido
- Escribir un ángulo enorme en un comando con asa de giro ya no traba la ventana.
- Cortes, roscas, patrones, normales y curvas medidos contra Fusion real (B-118, B-122, B-151, BOC-50, BOC-76, PAT-1 y
  SUP-23, entre otros); un cuerpo que pasa a otro componente ya no se mueve dos veces con la unión (B-108).
- Texto en curva: una letra tocada por otra curva sigue siendo letra y las cintas diminutas que sobran ya no se
  extruyen (B-132 a B-137).
- Volumen de una lente de dos esferas (B-129), booleanas que daban mal sin avisar (B-125, B-126, B-128, B-127) y
  fallas menores de la prueba de tortura de la API.
- Fugas de archivos y sockets cerradas en toda la suite (P-58); varios rojos de interfaz (panel que crecía al cambiar
  de modo, B-113; clic sobre un eje de la tríada con una herramienta de dibujo, B-120; ícono del repujado, B-112).
- Un boceto grande ya no congela la ventana al editarse (B-111).

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
