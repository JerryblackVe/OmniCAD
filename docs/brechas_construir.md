# CONSTRUIR: capturas de Fusion contra OmniCAD

Especificación de CON-1 a CON-8, B-130 y B-131, resueltos el 2026-11-01.

**Fuentes:** 20 capturas de Fusion en español en `analisis/capturas_fusion (solo quedan las pendientes; ver su INDICE.md)`, y la sección
«Construction geometry» de `docs/fusion_docs` (carpeta `fusion-model`; árbol en `docs/fusion_docs/indice/fusion-model.md`).
Se comparó el 2026-11-01 contra los campos reales de cada comando y con pruebas por API.

**Resultado:** tabla por herramienta, medidas y comparación contra las capturas en
[auditorias/construir_2026-11-01.md](auditorias/construir_2026-11-01.md).

## CON-1 · Panel único «Geometría de construcción»

Fusion usa un solo panel para planos, ejes y puntos. OmniCAD abre 19 paneles distintos.

| Fila | Controles |
|---|---|
| Tipo | 3 botones con ícono: Plano · Eje · Punto |
| Método (Plano) | Desfase · En el ángulo · Tangente · Plano medio · Plano perpendicular · A través de dos aristas · A través de tres puntos · A lo largo de la ruta |
| Método (Eje) | A través de cilindro/cono/toroide · Perpendicular a la cara · A través de dos planos · A través de dos puntos · A través de arista |
| Método (Punto) | En vértice · A través de dos aristas · A través de tres planos · En el centro de círculo/esfera/toroide · En arista y plano · A lo largo de la ruta |
| Siguientes | Las entradas de cada método |

- Cada entrada del menú abre este panel con Tipo y Método ya puestos. Las 19 claves siguen existiendo.
- El título es siempre GEOMETRÍA DE CONSTRUCCIÓN.
- Cambiar Tipo o Método dentro del panel cambia las entradas y conserva lo que sirva.
- Editar un paso desde el timeline abre el mismo panel con su método.
- Cada Método lleva su ícono, como en la captura.

Primeras filas por método según las capturas: Desfase: Plano, Extensión · En el ángulo: Arista · Tangente: Cara, Objeto de
referencia · Plano perpendicular: Cara, Dirección, Extensión · En vértice: Punto · A través de cilindro: Cara.

## CON-2 · Plano de desfase y Desfase

- Extensión: Distancia o Al objeto. Al objeto elige un punto de boceto o un vértice, y el plano queda asociado: si el punto
  se mueve, el plano lo sigue.
- Campo Desfase (Offset) en todos los métodos de plano menos Plano medio y Plano perpendicular. Queda guardado en el paso.

## CON-3 · Tamaño de planos y ejes

Dos controles separados, según la ayuda:

- **Redimensionar (Resize):** Predeterminado ajusta el dibujo a la geometría elegida; Extendido llena la vista. Va en
  planos y ejes, se guarda en el paso y solo cambia cómo se ve.
- **Tipo de extensión (Extent Type):** fija el largo del eje o las medidas del plano: Distancia o Al objeto.

Los valores concretos de cada método salen de su artículo y, si no está, de Fusion Help en la web.

## CON-4 · Plano perpendicular y Eje perpendicular

Ayuda: `Create a perpendicular plane` y `Create an axis perpendicular to a face`.

| Entrada | Cara plana o plano | Cara curva |
|---|---|---|
| Ubicación | Donde se toca | Donde se toca; el plano sigue la normal ahí |
| Dirección del plano | U o V, 2 botones con ícono | No aplica |
| Objeto de referencia, opcional | Punto, cara plana o plano | Solo punto |
| Distancia | Campo y asa | Campo y asa |
| Tipo de extensión | Distancia · Al objeto | Distancia · Al objeto |

El Eje perpendicular tiene que aceptar el lugar tocado en la cara, no solo un punto ya creado.
Un paso viejo de `perpendicular` (cara o arista + punto) sigue dando lo mismo.

## CON-5 · Rutas

| Herramienta | Tipo de extensión |
|---|---|
| Plano en ruta | Proporcional · Absoluto · Al objeto |
| Punto a lo largo de la ruta | Proporcional · Físico |

- Ruta: arista, línea de boceto, cadena de aristas y, en Plano en ruta, eje de construcción. Hoy el eje da error.
- Casilla Cadena tangente, encendida por defecto.
- Al objeto: Objeto de referencia (vértice, punto de construcción o punto de boceto) y Desfase.
- Se puede pasar del final de la ruta y volver arrastrando el asa. Una cadena sigue por la normal del último tramo.

## CON-6 · Sistema de coordenadas de usuario

Captura: fila Forzar con Seleccionar, y un panel aparte «Información del sistema de coordenadas» con el texto
«Seleccione el punto de referencia para el sistema de coordenadas. A continuación, ajuste el ángulo y el desfase desde
la posición original.», sección plegable Consejos y botón Cerrar.

- Forzar es la única entrada al abrir: un punto de forzado.
- Después aparecen Ángulo X, Y, Z y Desfase X, Y, Z, con asas en el lienzo.
- Eje Z y Eje X, opcionales: una arista o una cara alinea ese eje. Hoy son Eje X y Eje Y.
- Consejo de la ayuda: con el puntero sobre una cara, mantener Ctrl fuerza a puntos de esa cara.
- Contradicción a resolver: el panel exige Eje X y `construir` y la API no.

## CON-7 · Puntos de forzado

Según la ayuda: vértices, centros de cara y de arista, puntos de boceto y puntos tangenciales en caras curvas, que se calculan
al pasar el puntero. Van en Punto en vértice, Eje a través de dos puntos, Plano a través de tres puntos, Eje perpendicular y SCU.
La API acepta el mismo punto de forzado que la ventana.

## CON-8 · Nombres de planos en el lienzo

Ayuda: `Show or hide plane names on the canvas`. Cada plano de construcción y de origen muestra su nombre en el lienzo.
En Configuración de pantalla › Visibilidad de objetos hay dos casillas: nombres de planos de construcción y de origen. Ocultar
el nombre no oculta el plano. Renombrar actualiza la etiqueta.

## B-130 · Error engañoso al fallar una construcción

`create_construction_plane`, `_axis` y `_point` responden `NOT_FOUND: No existe 'op5'` cuando el paso no se puede calcular.
Pasa con dos aristas alabeadas, dos planos paralelos, tres planos sin cruce y tangente sobre cara plana. El paso falla, la
herramienta busca su resultado en `estado_final` y el `KeyError` tapa la causa real.

## B-131 · Error interno con una spline donde va una línea

Una spline pasa el filtro `curva_boceto` en Dos aristas y Arista y plano, y responde `INTERNAL_ERROR: ErrorReferencia`.
Tiene que ser un error claro de argumentos, y el visor no tiene que dejar elegirla.
