# Brechas frente a Fusion 360

Fecha: 2026-10-09.
Fuentes: la ayuda pública de Fusion 360, cómo se usa Fusion en la práctica (videos y cursos públicos) y la propia
app. Se comparan funciones, no se copia nada.

Este documento solo lista lo que **falta** o lo que **se hizo distinto**. El resto ya está en la app y se prueba con
`pytest` y con `OmniCAD.py --prueba-humo`.

## Hecho en esta pasada (video + curso)

| Comportamiento de Fusion | Dónde está |
|---|---|
| Arrastrar con el izquierdo hace la ventana de selección: de izquierda a derecha es naranja con borde y elige lo que queda adentro; de derecha a izquierda es amarilla y elige lo que toca | `ui/visor3d.py` (`BandaSeleccion`) |
| El ratón funciona como en Fusion por defecto: botón del medio desplaza, Mayús + medio orbita, la rueda hace zoom y doble clic en la rueda ajusta | `ui/preferencias.py` |
| Menú radial con clic derecho: 8 comandos más el segundo nivel de boceto y la lista de contexto debajo. También gestos: clic derecho, arrastrar y soltar. Dentro de un comando muestra Aceptar y Cancelar | `ui/menu_radial.py`, `ventana._items_radial` |
| "Seleccionar otro": mantener apretado el clic muestra lo que hay bajo el cursor, también lo tapado | `visor3d.entidades_bajo_cursor`, `ventana._seleccion_otra` |
| Medidas de lo elegido abajo a la derecha, por ejemplo "1 Cara \| Área: …" | `ui/medidas.py` |
| Aviso flotante "1 advertencia(s)" con "Más información" | `ui/avisos.py` |
| Ctrl+/ muestra la ayuda del comando que está bajo el ratón, y los tooltips con el pie de Fusion | `ventana.ayuda_comando` |
| Renombrar en el navegador con doble clic o F2. Candado en los bocetos totalmente restringidos | `ui/navegador.py` |
| Panel COMENTARIOS abajo a la izquierda, guardado con el proyecto | `ui/comentarios.py`, `doc.comentarios` |
| Los íconos fijos de la cinta son los del video | `ui/cinta.py` |
| Cuerpos gris medio (medidos del video), fondo #2d323f y panel de datos cerrado al abrir | `visor3d.py`, `temas.py` (tema «Clásico») |
| Cotas en vivo al dibujar con candado, arrastrar líneas y círculos, ventana en el boceto y cotas sin caja | agente del boceto (`ui/editor_boceto.py`) |
| Flechas y caja de valor en la vista para Extruir, Empalme, Agujero y los demás; tríada de Mover/copiar | agente de manipuladores (`ui/manipuladores.py`) |

## Hecho: abrir archivos de otros programas (2026-10-09)

| Comportamiento de Fusion | Dónde está |
|---|---|
| Abrir STEP, IGES, STL, OBJ, 3MF, PLY y DXF crea un diseño nuevo con su paso de importación; del STEP vienen nombres de cuerpos, colores y componentes | `io_archivos/abrir_externo.py`, `nucleo/intercambio.py` (`leer_step_estructura`) |
| Abrir `.f3d` y `.f3z` SIN Fusion (2026-10-10): se lee el B-rep que trae el archivo (bloques SAB de ShapeManager comprimidos con Zstandard) y entra como operación base | `io_archivos/f3d_nativo.py`, `sab.py`, `acis_occ.py`, `zstd_puro.py` |
| Respaldo con Fusion instalado: si la lectura propia falla, lo convierte Fusion por su API pública con el complemento OmniCADPuente (trae también los parámetros de usuario) | `integraciones/fusion/OmniCADPuente/`, `io_archivos/puente_fusion.py` |

## Lo que falta

| Falta | Por qué no está todavía |
|---|---|
| **Boceto 3D** con la tríada de boceto 3D: girar el plano de dibujo y dibujar fuera del plano, como el círculo inclinado 8,5° del video | Hoy el boceto es 2D sobre un plano. Hace falta curvas con su propio marco 3D, solver y perfiles por plano. Es una fase propia. |
| Imagen del agujero con cotas editables dentro del diálogo de Agujero | Hoy los campos son de texto. |
| Cota de ángulo de la primera línea contra el eje X y barrido del arco de centro escrito | El modelo de cotas no tiene ángulo contra un eje; con 0° o 90° se pone horizontal o vertical. |
| Asas para la conicidad del lado 2 y para el desfase de inicio de Extruir | Solo hay asa de distancia y de conicidad del lado 1. |
| Relleno azul del perfil en la vista previa mientras se dibuja | La geometría aparece rellena recién al crearse. |
| Tabla de grupos de aristas en Empalme (radios distintos por grupo) | Hoy hay un solo radio por operación. |
| Configuración del timeline (engranaje abajo a la derecha) | No implementado. |
| Historial de pasos al abrir un `.f3d` (hoy entran los cuerpos sin historial; con Fusion abierto, además los parámetros de usuario) | El historial vive en el flujo de diseño propietario de Fusion (`FusionDesignSegmentType1/BulkStream.dat`, clases por GUID sin nombres): hay que descifrarlo o traducirlo por la API pública con Fusion. Es una fase propia. |
| Instancias y componentes movidos al abrir un `.f3d` sin Fusion: cada componente entra donde está guardado su B-rep; faltan las copias (p. ej. las piezas acomodadas en las camas de impresión del sello) y la posición de los componentes movidos | Las matrices de posición están en el flujo de diseño y en la escena `OGS/DefaultScene/world` (nodos `Instance`/`TransformAttribute`), pero falta saber a qué bloque `BREP.*.smbh` corresponde cada una. |
| `.f3z` con referencias externas: se abre el diseño de arriba del paquete; los diseños referenciados pueden no venir | La importación de archivo de Fusion solo acepta `.f3d` sueltos. |
| Electrónica y Diseño generativo | Fuera del alcance por ahora: quedaron afuera desde el recorte del MVP. Un optimizador de parámetros simple está en GH11 de `brechas_grasshopper.md`. |
| Simulación, Fabricación y Forma (T-Splines) | Pendientes de prioridad 3 desde el 2026-10-09 (antes, fuera del alcance por el recorte del MVP): F19 y F20 de `brechas_freecad.md`, B17 de `brechas_blender.md`, RH19 de `brechas_rhino.md`. Antes de empezar hay que decidir las dependencias (p. ej. CalculiX y Gmsh). |
| **Recuperación de trabajo** al arrancar tras un cierre inesperado: lista de documentos recuperados con «Abrir» y «Suprimir», y «Archivo › Recuperar documentos» | Hoy el arranque solo ofrece un autoguardado de documento sin título (Sí/No); los proyectos con ruta se ofrecen solo al reabrirlos. Pendiente 21 de `PROJECT_LOG.md`. |
