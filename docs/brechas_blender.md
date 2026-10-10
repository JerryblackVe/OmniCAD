# Brechas frente a Blender

Fecha: 2026-10-09.
Fuentes (manual oficial de Blender 5.2 LTS, leído ese día): [modificadores](https://docs.blender.org/manual/en/latest/modeling/modifiers/index.html),
[edición de mallas](https://docs.blender.org/manual/en/latest/modeling/meshes/editing/index.html),
[nodos de geometría](https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/index.html),
[imán / snapping](https://docs.blender.org/manual/en/latest/editors/3dview/controls/snapping.html),
[importar y exportar](https://docs.blender.org/manual/en/latest/files/import_export/index.html),
[cuerpo rígido](https://docs.blender.org/manual/en/latest/physics/rigid_body/index.html),
[texto](https://docs.blender.org/manual/en/latest/modeling/texts/index.html),
[3D Print Toolbox](https://docs.blender.org/manual/en/4.0/addons/mesh/3d_print_toolbox.html),
[trazar imagen](https://docs.blender.org/manual/en/latest/grease_pencil/modes/object/trace_image.html).

**Licencia:** Blender es GPL-2.0 o posterior y OmniCAD es GPL-3.0 o posterior: SÍ se puede tomar código y algoritmos,
citando el archivo y conservando su aviso de copyright (es la regla ya escrita en `PROJECT_LOG.md`). Los add-ons y
extensiones traen su propia licencia: mirar el encabezado de cada uno antes de copiar. Blender es C/C++: en la
práctica se porta la matemática a Python sobre OCP y numpy.

Misma idea que en `brechas_freecad.md`, `brechas_rhino.md` y `brechas_plasticity.md`: sacar funciones de acá, con el manejo de
Fusion 360 (botón en la cinta, panel con vista previa viva, manipuladores, un paso editable en el timeline,
equivalente en API/MCP/CLI y prueba). Esta lista alimenta los pendientes 3, 4, 5 y 6 de `PROJECT_LOG.md`.

## Ya está en OmniCAD (no repetir)

Booleanas, matriz y simetría (≈ Array/Mirror/Boolean), empalme y chaflán (≈ Bevel), engrosar (≈ Solidify), reducir
y remallar (≈ Decimate/Remesh), suavizar, reparar, corte con plano, vaciado de malla, bobina y revolución
(≈ Screw), tubería, explosión y animación con publicación en GIF/PNG, render local por CPU o por OpenGL, análisis
(cebra, peine y mapa de curvatura, mapa de entorno, isocurva, desmoldeo, accesibilidad, radio mínimo, sección,
centro de masa), «Secuencias de comandos y complementos…»
(ejecuta scripts de una carpeta), búsqueda en la tecla S, menú radial, API/MCP/CLI.

## Para hacer

### Prioridad 1

| # | Herramienta (en Blender) | Cómo debe sentirse (Fusion) | Estado / dónde engancha |
|---|---|---|---|
| B1 | **Render con Cycles de Blender** como motor externo (como el «render en la nube» de Fusion): la escena sale con sus aspectos, Blender corre en segundo plano y vuelve la imagen. | RENDERIZAR › motor «Blender (Cycles)»: calidad, entorno HDRI, fondo transparente, reducción de ruido; barra de progreso y la imagen aparece en la ventana de render. | Hoy solo hay motor local CPU/OpenGL (`ui/render.py`). Une los pendientes 3 y 4; la decisión del motor está en `brechas_keyshot.md`. Detecta un Blender ya instalado: no instala nada. |
| B2 | **Revisión de impresión 3D**: sólido cerrado, intersecciones, distorsión, espesor mínimo, voladizos, aristas filosas, y «Hacer manifold / limpiar». *3D Print Toolbox.* | ANALIZAR › «Revisar impresión»: material/boquilla/ángulo de voladizo como campos, mapa de color sobre la pieza, lista con clic que resalta, botón «Reparar». | Hay accesibilidad, radio mínimo y desmoldeo; en la lista de análisis de `ui/cinta.py` no hay voladizo ni espesor mínimo. Es el mismo informe que F2 de `brechas_freecad.md` y RH13 de `brechas_rhino.md`: hacerlo una vez. |
| B3 | **Exportar glTF/GLB, FBX y USD** con colores y aspectos. *Blender: Alembic, OBJ, PLY, STL, FBX, USD…* | Archivo › Exportar: tipo en la lista, opciones (unidades, aspectos, Y arriba). Para la web, AR y otros programas. | `io_archivos/exportar.py` hoy: STL, OBJ, 3MF, PLY, STEP, IGES, BREP. ⚠ glTF en Blender: de memoria, no leído hoy. |
| B4 | **Vectorizar imagen** (trazar contorno de una imagen y sacar curvas de boceto). *Trace Image.* | INSERTAR › «Vectorizar»: imagen, umbral, suavizado, ignorar manchas, esquinas; vista previa de las curvas; sale un boceto editable. | Hay lienzo y SVG; falta el trazado. Pendiente 5. ⚠ Un paquete tipo `potrace` sería nuevo: pedir permiso. |
| B5 | **Complementos de usuario**: carpeta con un manifiesto que registra operaciones, comandos y herramientas, con instalar/activar/desactivar. *Extensiones de Blender (manifest).* | «Secuencias de comandos y complementos…» con pestaña «Complementos»: lista con interruptor, versión, autor y error si falla. | Hoy ejecuta scripts sueltos (`DialogoScripts`). Las recetas A, B y C de `AGENTS.md` ya definen cómo se registra algo: falta cargarlas desde afuera del repo. |

### Prioridad 2

| # | Herramienta (en Blender) | Cómo debe sentirse (Fusion) | Estado / dónde engancha |
|---|---|---|---|
| B6 | **Video MP4**, cámara que sigue una ruta e interpolación editable (entrada/salida suave). | PUBLICAR › Video: formato MP4; en la animación, curva de suavizado por tramo y «cámara en ruta». | `animacion.py` publica solo GIF o secuencia PNG. ⚠ MP4 pide ffmpeg: detectar el instalado o preguntar. Pendiente 6. |
| B7 | **Imán (snapping) completo**: a vértice, arista, cara, volumen, centro de arista, perpendicular; «con qué punto» (más cercano, centro, mediana, activo); alinear rotación a la normal; varios a la vez con Mayús. | Barra de imanes en el visor; el marcador del cursor dice qué tipo. Va junto con RH12 de `brechas_rhino.md`: es la misma tarea. | Buscado en el código: el visor 3D no tiene imanes (solo Ensamblar y Dibujo). |
| B8 | **Orientaciones y pivotes**: global, local, normal, vista, cursor; pivote en mediana, caja o elemento activo; cursor 3D. | En Mover/copiar y Alinear: selector de orientación y de pivote junto a la tríada. ⚠ De memoria, no leído hoy. | Hay tríada de Mover/copiar en `ui/manipuladores.py`. |
| B9 | **Limpieza de malla ampliada**: fusionar por distancia, disolver por ángulo, disolver degenerados, borrar sueltos, rellenar huecos (grilla), recalcular normales, hacer plano, triángulos a cuadriláteros, simetrizar. *Clean Up, Dissolve, Grid Fill, Triangles to Quads, Symmetrize.* | MALLA › «Limpiar»: lista de pasos con casillas y umbrales; vista previa del cambio de triángulos. | Hay `reparar_malla`; extenderlo. |
| B10 | **Ajustar a superficie**: llevar curvas, mallas o puntos al punto más cercano de una superficie o proyectarlos a lo largo de un eje/normal, con desfase. *Shrinkwrap.* ⚠ Los métodos (más cercano, a lo largo de un eje, normal): de memoria; el manual solo dio el nombre. | MODIFICAR › «Ajustar a superficie»: objeto + superficie destino + método + desfase. Base de logos y trazados sobre piezas curvas. | Nuevo. Parte de la misma familia que «Deformar» (RH7 de `brechas_rhino.md`). |
| B11 | **Varillas desde aristas** (jaulas, marcos, celosías): cada arista se vuelve una varilla con sección elegida. *Wireframe, Skin, Curve to Tube.* | CREAR › «Varillas»: elegir aristas o cuerpo, diámetro, redondeo de nudos. | Hay `tuberia` (una ruta). |
| B12 | **Esparcir copias sobre una superficie** con densidad y semilla (decoración, texturas, tachas). *Scatter on Surface; Distribute Points on Faces.* | Parte de «Patrón»: tipo «Sobre superficie». Mismo lugar que F3 de `brechas_freecad.md` (en puntos). | Ampliar `patron`. |
| B13 | **Relieve por textura en caras** (desplazar con ruido o imagen: cuero, panal, agarre). *Displace.* | MODIFICAR › «Textura de relieve»: caras + patrón + escala + profundidad. Sigue a RH10 de `brechas_rhino.md` (relieve desde imagen). | Hay `repujado`. |
| B14 | **Texto avanzado**: párrafos y cajas de texto, interlineado, kerning, versalitas, texto sobre ruta. ⚠ «Texto sobre ruta» en Blender: de memoria (el índice del manual no lo nombra). | En el boceto, panel de texto con las mismas opciones. | Ya hay `sk_texto` con fuente, altura, ángulo, negrita y cursiva (`restricciones/boceto.py`) y desglosar texto en curvas. Falta lo de la lista. Pendiente 5. |
| B15 | **Nodos de geometría como segunda referencia de GH1–GH12**: campos (evaluación por elemento), atributos, instancias y «realizar instancias», zonas de repetición y de simulación, horneado. | Ver `brechas_grasshopper.md`. Lo nuevo de Blender: los CAMPOS y las instancias; Grasshopper aporta los árboles. | El código es GPL: se puede leer y portar. Después de GH2. |

### Prioridad 3 — grandes, piden decisión

| # | Herramienta (en Blender) | Nota |
|---|---|---|
| B16 | **Modo edición de malla**: mover vértices/aristas/caras con edición proporcional; extruir (a lo largo de normales, individual), inset, biselar, corte en bucle y deslizar, puentear bucles, cuchillo, bisecar. | Es modelado de malla, no de sólidos: más allá de lo que hace Fusion. Solo si el usuario lo pide. |
| B17 | **Simulación de cuerpo rígido**: gravedad, colisiones, restricciones (⚠ tipos bisagra, deslizador…: de memoria; el manual dio solo el índice), horneado a animación. | Espacio SIMULACIÓN grisado. Pide un motor de física: preguntar antes de sumar una dependencia. Pendiente 6. |
| B18 | **Mapeo UV** (desenvolver, proyección caja/cilindro/esfera) y texturas. | Va con el pendiente 4 (render). Misma tarea que RH21 de `brechas_rhino.md`. |
| B19 | **Normales y sombreado** (suavizar por ángulo, normales ponderadas) al exportar mallas. | Detalle de B3. |

## Descartado a propósito

Escultura digital (pinceles, multirresolución), pelo y partículas, fluidos, tela y cuerpo blando, océano, edición de
video, Grease Pencil como herramienta de dibujo, rigging y armaduras. No son CAD.

## Sin verificar

- B3 (glTF), B8 y la parte de «Blender usa Bullet para física»: de memoria, no leído hoy.
- Qué hace hoy OmniCAD en B2, B7, B8 y B14: buscado en el código (revisado el 2026-10-09), no probado en la app.
- Las páginas de Cycles y de modificadores del manual devolvieron solo el índice, sin descripciones: la lista de
  modificadores sale de los títulos.
