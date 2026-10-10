# Brechas frente a Grasshopper (programación visual)

Fecha: 2026-10-09.
Fuentes (leídas ese día): [Grasshopper 2 — documentación](https://www.rhino3d.com/docs/grasshopper2/) (glosario, temas y
los **1385 componentes** de [specs](https://www.rhino3d.com/docs/grasshopper2/specs/)),
[guías de Grasshopper para desarrolladores](https://developer.rhino3d.com/guides/grasshopper/),
[guías de Compute y Hops](https://developer.rhino3d.com/guides/compute/), lista de comandos de Rhino
(`GrasshopperPlayer` figura ahí). Rhino va en `docs/brechas_rhino.md`.

**Regla:** Grasshopper es propietario. Se replican los CONCEPTOS y las funciones, no su pantalla, código ni textos.
⚠ Si Grasshopper 2 ya salió o sigue en desarrollo: no verificado. Por las dudas, tomar de ahí el modelo de datos, no la interfaz.
Como segunda referencia, Blender tiene un sistema equivalente con código GPL: ver B15 de `brechas_blender.md`.

## Qué es, en una línea

Un programa de grafo: cada nodo (componente) toma datos, hace una operación y entrega datos; los cables los conectan;
al cambiar un deslizador todo el grafo se recalcula y la geometría se ve en vivo. Sirve para diseños que dependen de
reglas (patrones, familias, fachadas, joyería, celosías), no para dibujar a mano.

## Lo que muestra la documentación (hechos leídos)

| Tema | Qué dice |
|---|---|
| **Árboles de datos** | Los datos viajan en árboles. Cada «rama» tiene una ruta de enteros (`{0;1}`). Modificadores: **Aplanar** (todo en una lista), **Injertar** (un elemento por rama), **Simplificar** (saca enteros comunes de las rutas), **Invertir**. Grasshopper 2 suma componentes de «sitios» (`Site From Index/Offset/Path`, `Tree Sites`); qué son exactamente no se leyó. |
| **Componentes** | 1385, en 11 categorías: Curve 210, Data 156, Display 92, Intersect 78, Maths 180, Mesh 121, Params 103, Surface 152, Text 38, Transform 87, Vector 168. |
| **Datos auxiliares** | Tuplas y conjuntos (`Cartesian Product`, `Set Intersection`…), **metadatos** que viajan con la geometría (color, nombre, capa de Rhino, densidad, material) y recorte por patrón (`Cull By Pattern`, `Dispatch`, `Weave`). |
| **Bucles y campos** | `Loop Repeat`, `Loop Break`, `Loop Iteration` (repetir hasta cumplir). 40 componentes de **campos** (escalares y vectoriales, isosuperficies, ruido, trayectorias). |
| **Scripts** | `C# Script`, `Python 3 Script`, `IronPython 2 Script`, `Evaluate Expression`. |
| **Utilidades** | `Data Recorder`, `Timer`, `Relay`, `Scribble`, `Panel`, `Slider`, `Value List`, `Geometry Stash`, `Read 3dm File`, `Rhino Pipeline`. |
| **Para quien programa** | Guías de componentes propios, tipos de datos, parámetros, componentes en paralelo («task capable»), opciones propias en archivos `.gh`, entrada/salida de archivos por código. |
| **Fuera de la ventana** | **Rhino.Compute**: servicio REST sin estado que corre definiciones. ⚠ De aquí en adelante, de memoria (las guías solo dieron los títulos): **Hops**: un componente que llama a una definición como función. **Grasshopper Player** (el comando `GrasshopperPlayer` existe en la lista de Rhino): ejecuta una definición como un comando, con un panel simple de entradas. |

## Cómo encaja con OmniCAD (y con Fusion)

Fusion 360 no tiene programación visual: lo más cercano son los **parámetros** y las configuraciones. Entonces la
experiencia de Fusion se aplica al ENVOLTORIO: un panel de comando con buscador (como la tecla S), vista previa viva,
Aceptar/Cancelar, y que lo que sale sea **pasos del timeline editables**.

Decisión de diseño que conviene tomar antes de programar:

| Opción | Qué es | Veredicto |
|---|---|---|
| A | El grafo escribe pasos del timeline y listo. | Se queda corto: el timeline no tiene listas, árboles ni bucles. |
| **B** | El grafo se evalúa como flujo de datos puro y produce cuerpos; «Hornear» los pasa al timeline. | **Recomendada.** Mantiene la receta y suma lo que le falta a Grasshopper. |
| C | Los dos a la vez. | Es B más tiempo: queda para después. |

Lo que ya existe y baja el costo: el catálogo único `api/` (unas 60 herramientas con nombre, parámetros tipados y
docstring) y las 86 operaciones del timeline. Casi todos los primeros nodos salen SOLOS de ahí.

## Para hacer

| # | Pieza | Cómo debe sentirse (Fusion) | Estado / dónde engancha |
|---|---|---|---|
| GH1 | **Modelo de datos**: `Arbol`, `Ruta`, emparejado de listas (más larga, más corta, producto cruzado), nulos y errores por nodo; aplanar, injertar, simplificar, invertir. | Sin pantalla: módulo puro `nucleo/flujo/` (sin Qt, sin OCP), con pruebas pytest antes de cualquier interfaz. | Nuevo. Es el corazón: sin esto no hay patrones paramétricos reales. |
| GH2 | **Motor de evaluación**: grafo sin ciclos, recálculo solo de lo que cambió, orden topológico, caché por nodo, JSON dentro del `.omnicad`. | `omnicad grafo correr` por CLI; mide tiempos por nodo (como `dev bench`). | Nuevo. Reusa la idea de recálculo parcial del timeline. |
| GH3 | **Catálogo de nodos**: generado desde `api/` y las operaciones; tipos de puerto (número, punto, vector, plano, curva, cuerpo, lista, árbol). Primera tanda ≈ 80: entradas (deslizador, interruptor, panel, lista de valores), matemática y trigonometría, secuencias y rango, aleatorio, vectores y planos, listas y árboles, curvas básicas, divisiones, extrusión/solevación/revolución/barrido, mover/girar/escalar/simetría/matriz, booleanas. | Buscador de nodos como la caja de la tecla S: escribir y elegir; ayuda en un globo con el nombre y el tipo de cada puerto. | `api/registro.py` ya describe los parámetros: generar nodos es mecánico. |
| GH4 | **Lienzo de nodos**: arrastrar, cables, zoom y paneo, grupos, aislar, vista previa en el visor (se resalta lo del nodo elegido), errores en rojo con el mensaje. Pestaña «DISEÑO ALGORÍTMICO». | Mismo tema (claro/oscuro) y los mismos atajos que el resto de la app. | Nuevo, en `ui/`. Lleva Qt: va DESPUÉS de GH1 y GH2. |
| GH5 | **Hornear y enlazar**: convertir el resultado en pasos del timeline o en cuerpos fijos; deslizadores enlazados a parámetros del documento. | «Hornear» como botón de Aceptar; los parámetros se ven en la tabla de siempre. | Hay parámetros y expresiones (`timeline/parametros.py`). |
| GH6 | **Nodo de script** (Python) con editor y autocompletado de la API; nodo de expresión. | Panel de código dentro del nodo. | Hay `execute_code` en la API y «Secuencias de comandos…». |
| GH7 | **Grafo como comando** (estilo Grasshopper Player): publicar un grafo y que aparezca en la caja de la tecla S con un panel de campos armado con sus entradas. | Es lo más Fusion: el usuario ve un comando normal con campos y vista previa, sin saber que hay un grafo. | Se apoya en `ui/comando.py` (Receta B). |
| GH8 | **Correr sin ventana**: herramienta `run_graph` en la API/MCP/CLI, con entradas por nombre y salida a STEP/STL. | Para agentes: «hacé 20 variantes de este grafo». | Se arma sobre la API. Estilo Hops/Compute, pero local. |
| GH9 | **Clústeres**: un grupo de nodos pasa a ser un nodo propio, reutilizable y compartible. | Seleccionar → «Agrupar en nodo». | Después de GH4. |
| GH10 | **Bucles y campos**: repetir hasta cumplir una condición; campos escalares para modular geometría. | Nodos «Repetir» y «Campo»; vista de isolíneas en el visor. | Después de GH3. Referencia: nodos de geometría de Blender (B15). |
| GH11 | **Optimizador de parámetros**: elegir un número de salida (volumen, masa, distancia) y pedir que lo minimice o maximice cambiando parámetros dentro de un rango. ⚠ En Grasshopper se hace con un complemento (Galapagos): de memoria, no leído hoy. | ANALIZAR › «Optimizar»: parámetros + rangos + objetivo; barra de progreso y botón «Aplicar el mejor». Sirve SIN grafo, sobre el timeline. | `scipy` ya es dependencia (`restricciones/solver.py`). |
| GH12 | **Nodos de terceros**: un complemento registra nodos nuevos (como en las guías de «componentes propios»). | Mismo gestor de complementos que B5 de `brechas_blender.md`. | Va con ese pendiente. |

### Orden sugerido

GH1 → GH2 → GH3 (con pruebas, sin pantalla) → GH5 → GH8 (ya sirve a los agentes) → GH4 → GH7 → GH6 → GH9, GH10 →
GH11 aparte cuando se quiera. Cada paso deja algo usable: tras GH8 un agente ya puede correr grafos sin ventana.

## Cuidados

- ⚠ **Hilos:** las guías hablan de componentes en paralelo. OpenCascade no es seguro entre hilos para formas que se
  comparten: paralelizar por proceso, o evaluar secuencial al principio. Medir antes de decidir.
- **Tolerancias y unidades:** Grasshopper tiene pines de tolerancia y de sistema de unidades. OmniCAD trabaja en mm y
  grados: un solo sistema, sin esos pines.
- **Datos que no son geometría** (texto, fechas, sol, escena con autos y gente): no copiar. Sirve el 20 % del catálogo.

## Descartado a propósito

Categoría «Display › Scene» (multitudes, vehículos, figurines), componentes de fecha y sol, `Rhino Pipeline` y capas
de Rhino, la pantalla de Grasshopper 2 (todavía cambia).

## Sin verificar

- Cuántos de los 1385 componentes se pueden cubrir con el catálogo de `api/`: es una estimación (≈ 30 %), no medida.
- Las reglas de emparejado de listas (más larga, más corta, cruzado) son las de Grasshopper 1 de mi conocimiento:
  la página de árboles que leí no las detalla.
- GH11 (Galapagos) y los complementos clásicos (Kangaroo, Ladybug…): de memoria.
- Qué hacen Hops y Grasshopper Player, y el estado de Grasshopper 2: de memoria o no verificado.
