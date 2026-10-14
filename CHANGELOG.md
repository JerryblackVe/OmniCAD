# Changelog

Cambios destacados de cada versión publicada de OmniCAD, en español. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [No publicada]

### Agregado / Cambiado
- Seguridad del MCP `--http`: token Bearer obligatorio (`mcp_http.json` + middleware) y tope de 512 MB por
  miembro del ZIP al leer proyectos (`io_archivos/proyecto.py`); permisos 0o600 en los JSON de información.
- CI: un job de tests (pytest y ruff) corre antes de publicar los instaladores; permisos del workflow
  acotados y actions pineadas a SHA; escaneo de secretos.
- Corrección de bugs de los reportes: asociatividad de perfiles (re-vinculado con aviso), uniones robustas,
  booleanas con avisos de tangencia/coplanaridad, repair que no empeora, roscas largas y chicas, deflexión por
  pieza en el render, fold en pestaña base y mensaje de versión al abrir una receta con operación desconocida.

## [0.1.2] — 2026-10-10

### Agregado
- Texto y vectores: catálogo de fuentes completo (sistema, usuario, variables), texto sobre una curva,
  panel Carácter (kerning, inclinación, escalas, versalitas, subrayado/tachado) y editor de texto con cursor.
- Insertar SVG/DXF e imagen vectorizada en el boceto abierto; unir/restar/intersecar perfiles, desfase y
  marco para mover, escalar, girar y espejar.
- Roscas y tolerancias: familias de rosca, clases ISO 965 / ASME B1.1, ajustes ISO 286 y Agujero con holgura,
  cónico, Hasta y Referencias.
- Grafo de nodos sin ventana (tipo Grasshopper; `run_graph` / `bake_graph`), engranajes, cremallera, rueda de
  cadena ISO 606 y eje escalonado; revisión de geometría e impresión 3D y Reparar cuerpo.
- Grupo «malla» del MCP/CLI, Limpiar malla y exportar glTF/GLB; patrones avanzados (en puntos, en ruta con
  giro, multitransformar, patrón de operaciones).

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
