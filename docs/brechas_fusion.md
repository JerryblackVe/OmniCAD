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
| Cuerpos gris medio (medidos del video), fondo #2d323f y panel de datos cerrado al abrir | `visor3d.py`, `estilo.py` |
| Cotas en vivo al dibujar con candado, arrastrar líneas y círculos, ventana en el boceto y cotas sin caja | agente del boceto (`ui/editor_boceto.py`) |
| Flechas y caja de valor en la vista para Extruir, Empalme, Agujero y los demás; tríada de Mover/copiar | agente de manipuladores (`ui/manipuladores.py`) |

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
| Electrónica, Diseño generativo, Simulación, Fabricación y Forma (T-Splines) | Fuera del alcance del clon, igual que antes. |
