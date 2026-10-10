# Brechas frente a FreeCAD

Fecha: 2026-10-09.
Fuentes (ayuda oficial de FreeCAD, leída ese día): [Workbenches](https://wiki.freecad.org/Workbenches),
[PartDesign](https://wiki.freecad.org/PartDesign_Workbench), [Part](https://wiki.freecad.org/Part_Workbench),
[Sketcher](https://wiki.freecad.org/Sketcher_Workbench), [Surface](https://wiki.freecad.org/Surface_Workbench),
[TechDraw](https://wiki.freecad.org/TechDraw_Workbench), [Draft](https://wiki.freecad.org/Draft_Workbench),
notas de versión [1.0](https://wiki.freecad.org/Release_notes_1.0) y [1.1](https://wiki.freecad.org/Release_notes_1.1).

Idea: tomar de FreeCAD las FUNCIONES que a OmniCAD le faltan, pero con la facilidad de manejo de Fusion 360
(panel de comando, selección directa en la vista, vista previa viva, manipuladores, un paso editable en el timeline).

**Licencia ⚠** FreeCAD es LGPL-2.1 (archivo `LICENSE` del repo). OmniCAD es GPL-3.0 o posterior: se puede tomar
código y algoritmos citando archivo y aviso, pero FreeCAD es C++/Qt, así que en la práctica se **reescribe** la
matemática en Python sobre OCP. Revisar el encabezado de cada archivo antes de copiar nada. Los talleres
EXTERNOS (Gear, Frames, Fasteners…) tienen su propia licencia: mirar la de cada uno.

## Receta de experiencia que lleva TODA herramienta de esta lista (la de Fusion)

1. Botón en la cinta (pestaña que corresponda) con ícono y texto; también en la caja de la tecla S.
2. Panel de comando con campos; se elige en la vista (cara, arista, plano, punto) con contador «n seleccionados».
3. Vista previa viva mientras se escriben los valores; flechas/manipuladores con caja de valor en la vista.
4. Aceptar / Cancelar (Enter / Esc). Un solo paso en el timeline, editable con doble clic, con parámetros y expresiones.
5. Globo de ayuda (texto + imagen), atajo y menú radial si aplica.
6. Equivalente en la API/MCP/CLI (receta C de `AGENTS.md`) y prueba con resultado numérico.

## Ya está en OmniCAD (no repetir)

Boceto completo (polígonos, elipse, ranuras, spline, cónica, texto, proyectar/intersecar/incluir 3D, curva de fusión,
desfase, restricciones y cotas); 86 operaciones del timeline (sólidos, superficies completas, chapa, malla,
ensamblar, fijación, rosca, bobina, nervio, red, repujado…); explosión en Animación; lista de materiales; dibujos
con vistas base/proyectada/sección/detalle, cotas, ordenada, notas, globos y lista de piezas; análisis; temas;
selección «otro»; búsqueda en la tecla S.

## Para hacer

### Prioridad 1 — mucho valor, engancha en lo que ya hay

| # | Herramienta (en FreeCAD) | Cómo debe sentirse (Fusion) | Estado / dónde engancha |
|---|---|---|---|
| F1 | **Engranajes y ruedas dentadas**: engranaje de evolvente (recto y helicoidal), cremallera, rueda de cadena, polea dentada. *PartDesign › Involute Gear, Sprocket; taller externo Gear.* | CREAR › «Engranaje»: plano + punto centro, módulo, nº de dientes, ángulo de presión, ancho, hélice; vista previa viva; opción «par de engranajes» que pone la distancia entre centros y crea la unión + el vínculo de movimiento con la relación de dientes. | No existe generador. Sí existen `union` y `vinculo_movimiento` (`ops_ensamblar.py`). |
| F2 | **Revisar geometría**: diagnóstico de un cuerpo (sólido inválido, caras que se cruzan, aristas libres, tolerancias) con botón «Reparar». *Part › Check Geometry, Set Tolerance, Refine Shape.* | INSPECCIONAR › «Revisar geometría»: lista de problemas; clic en uno resalta la pieza en la vista; «Reparar» aplica refinar/tolerancia y deja un paso. | `geo.es_valida` y `UnifySameDomain` ya se usan por dentro; falta el comando y el informe. Muy útil tras importar STEP/mallas. Hacerlo UNA vez junto con B2 de `brechas_blender.md` (revisión de impresión) y RH13 de `brechas_rhino.md` (aristas abiertas y no manifold): es el mismo informe. |
| F3 | **Patrón en puntos y en ruta con giro**: copias en cada punto de un boceto/cuerpo; copias a lo largo de una ruta que van girando. *PartDesign › Point Pattern; Draft › Twisted Path Array.* | Nuevos tipos en el comando Patrón existente: «En puntos» y «En ruta (con giro)»; vista previa de las copias. | Ampliar `patron` (rectangular, circular, ruta ya están). |
| F4 | **Referencias perdidas**: que editar un boceto o una cota temprana no suelte empalmes, agujeros ni patrones, y que si se pierde una referencia se pueda **reparar** en el acto. *FreeCAD 1.0: mitigación del nombre topológico.* | Paso con error en rojo en el timeline; al abrirlo, «Falta una cara: elegí la nueva» y el resto se recalcula. Es el punto fuerte de Fusion. | Buscado en el código: `firma_cara` (`nucleo/referencias.py`) resuelve las referencias y hay pruebas sueltas en los tests de comandos; cuando una referencia se pierde, el panel la muestra sin resaltar (`ui/comando.py`) y no hay forma de reelegirla. Falta un juego de pruebas «editar el paso 1 y ver que todo sigue pegado». |
| F5 | **Diagnóstico del boceto**: seleccionar restricciones en conflicto, redundantes y elementos sin restringir; validar y reparar un boceto roto. *Sketcher › Validate Sketch, Select Conflicting / Redundant / Under-constrained.* | Aviso «2 restricciones en conflicto» con «Más información» (ya existe el globo de avisos): al clic se resaltan en el boceto y se pueden borrar desde la lista. | Buscado en el código: el solver detecta el conflicto (`restricciones/solver.py`), el boceto deshace solo la restricción que sobre-restringe (`ui/editor_boceto.py`) y avisa al salir (`ui/modo_boceto.py`). Falta DECIR cuáles chocan o sobran, y elegirlas desde la lista. |

### Prioridad 2 — valor medio o esfuerzo medio

| # | Herramienta (en FreeCAD) | Cómo debe sentirse (Fusion) | Estado / dónde engancha |
|---|---|---|---|
| F6 | **Rebanar**: N cortes paralelos de un cuerpo como curvas, caras o láminas (para láser, cartón, CNC). *Part › Cross-Sections, Slice Apart, Slice to Compound.* | CREAR › «Rebanar»: plano de referencia, dirección, espesor/separación, salida (bocetos / cuerpos finos). | Hay `dividir_cuerpo` y `cortar_plano` de malla; falta la serie. |
| F7 | **Asistente de ejes**: tabla de tramos (diámetro, largo, chaflán) que arma el eje por revolución. *PartDesign › Shaft Design Wizard.* | Diálogo con tabla editable y vista previa; deja un boceto + revolución editables. | Nuevo. Bajo esfuerzo. |
| F8 | **Uniones de transmisión**: engranajes, cremallera-piñón, tornillo, correa con la relación calculada sola. *Assembly 1.0 › joints.* ⚠ Estos cuatro tipos de unión de FreeCAD: de memoria (las notas de 1.0 leídas solo nombran ángulo, perpendicular y paralela). | En «Unión»: tipos nuevos; elegís dos uniones giratorias y la relación sale de los dientes. | Se apoya en `vinculo_movimiento`; va junto con F1. |
| F9 | **Dibujo: lo que falta**: vista interrumpida (Broken View), símbolo de soldadura, acabado superficial, ajuste agujero/eje, cotas en cadena y de chaflán, prefijos ⌀ □ n×, rayado geométrico, corte complejo, exportar página a SVG. *TechDraw.* | Mismo flujo de dibujo actual: botón, clic en la vista, panel con opciones. | `nucleo/dibujo.py` solo tiene base/proyectada/sección/detalle, cotas, ordenada, nota, globo, tabla y línea de centro. Va junto con RH14 de `brechas_rhino.md` (cotas de longitud, área y volumen). |
| F10 | **Mapa de desviación**: comparar un cuerpo contra otro o contra una malla escaneada y colorear la distancia. *Inspection.* | INSPECCIONAR › «Desviación»: elegís los dos, escala de color con mín/máx y punto bajo el cursor. | Hay `analisis_vista.py` con mapas de color (cebra, curvatura…): reusar el visor. Incluye la desviación entre curvas y puntos de RH13 (`brechas_rhino.md`). |
| F11 | **Ajustar primitivas a una malla**: detectar planos, cilindros y esferas en un escaneo y rearmar un sólido paramétrico. *Reverse Engineering.* | MALLA › «Ajustar a sólido»: muestra los grupos detectados con color y tolerancia; el usuario acepta o ajusta. | Se apoya en `grupos_caras` y `convertir_malla` (hoy solo facetado). |
| F12 | **Herramientas de B-spline**: polígono de control, insertar nudo, subir/bajar grado, unir curvas, convertir a B-spline. *Sketcher › B-spline tools.* | Conmutadores en la paleta del boceto y manijas en los puntos de control. | Hay spline por ajuste y por control, y el peine de curvatura ya existe como análisis (`curvatura_peine` en `ui/cinta.py`). Va junto con RH9 de `brechas_rhino.md` (puntos de control en 3D). |
| F13 | **Estructura de perfiles**: perfiles estándar (tubo, ángulo, aluminio 20×20) a lo largo de rutas con ingletes y recortes automáticos. *Taller externo Frames / BIM Structure.* | Elegís perfil + ruta del boceto; las uniones se cortan solas; lista de cortes. | Nuevo; apoyarse en `barrido`. Pariente de B11 de `brechas_blender.md` (varillas desde aristas). |
| F14 | **Piezas estándar ampliadas**: rodamientos, arandelas, tuercas, pasadores, insertos. *Talleres externos Fasteners / Parts Library.* | INSERTAR › «Fijación» con más familias; la posición se elige en aristas circulares como hoy. | Ampliar `nucleo/fijaciones.py`. |
| F15 | **Parámetros desde hoja**: importar/exportar parámetros y familias de piezas desde CSV/XLSX con nombre propio por celda. *Spreadsheet; VarSets de 1.1.* | Administrar › Parámetros › «Importar de hoja»; la tabla se vuelve configuraciones. | Hay parámetros y configuraciones (`administrar.py`). |
| F16 | **Pulidos de uso**: buscador dentro de Preferencias, iluminación de tres puntos en el visor, indicador del centro de giro, más estilos de navegación. *FreeCAD 1.0/1.1.* | Chicos y sueltos; cada uno con su opción en Preferencias. | Buscado en el código: no hay buscador en Preferencias ni indicador del centro de giro; hay 3 estilos de ratón (OmniCAD, Fusion, Tinkercad) en `ui/preferencias.py`. La iluminación de tres puntos: sin verificar. |
| F17 | **Copias ligeras** (enlaces): muchas copias de una pieza compartiendo la geometría. *App Link / Link Arrays.* | Invisible para el usuario: un patrón de 200 tornillos no pesa 200 veces. | Medir con `omnicad dev bench` antes de decidir. Es la misma tarea que RH17 (`brechas_rhino.md`) y PL8 (`brechas_plasticity.md`). |
| F18 | **Multitransformación**: combinar patrón + simetría + patrón en un solo paso. *PartDesign › Multi-Transform.* | Lista de transformaciones apilables dentro del mismo panel. | Ampliar `patron`/`simetria`. |

### Prioridad 3 — grandes, piden una decisión del usuario antes

| # | Herramienta (en FreeCAD) | Nota |
|---|---|---|
| F19 | **Simulación estática** (tensión, desplazamiento, factor de seguridad) con CalculiX + Gmsh. *FEM.* | Espacio SIMULACIÓN ya aparece grisado en la cinta. Pide dependencias externas: preguntar antes de sumarlas. Pasó de «fuera de alcance» a prioridad 3 el 2026-10-09 (`brechas_fusion.md`). |
| F20 | **Fabricación (CAM)**: contorno 2.5D, bolsillo, taladrado, adaptativo, V-carve, simulador y post-procesadores G-code. *CAM.* | Espacio FABRICACIÓN ya grisado. Proyecto aparte. Prioridad 3 desde el 2026-10-09 (`brechas_fusion.md`). |
| F21 | **Fragmentos booleanos, XOR, conectar / incrustar / recortar forma.** *Part.* | Nicho; solo si hay un pedido real. |
| F22 | **Nube de puntos** (importar PLY/XYZ) e **importar .scad** (necesita OpenSCAD instalado). *Points, OpenSCAD.* | Nicho. El .scad pide un programa externo. |
| F23 | **Curva sobre malla** y **relleno con continuidad G2.** *Surface › Curve on Mesh, Filling.* | Ver si `parche` ya cubre la continuidad. |

## Descartado a propósito

BIM/Arch (arquitectura), Robot, Test Framework, Raytracing (FreeCAD usa un Render externo; OmniCAD tiene el suyo),
Web, Start, Drawing viejo (lo reemplaza TechDraw), Material (ya hay materiales y densidad), Spreadsheet como hoja
completa (solo F15).

## Sin verificar

- F4, F5, F12 y F16: no se probó en la app qué hace hoy; el estado de la tabla sale de buscar en el código
  (revisado el 2026-10-09 en la revisión de la sesión).
- La página del taller Assembly de FreeCAD no devolvió su lista de tools; las uniones salen de las notas de versión 1.0.
