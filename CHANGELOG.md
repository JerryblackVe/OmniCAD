# Changelog

Cambios destacados de cada versión publicada de OmniCAD, en español. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [No publicada]

### Corregido
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
