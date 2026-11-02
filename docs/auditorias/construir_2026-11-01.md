# CONSTRUIR en la ventana: auditoría del 2026-11-01

Las 20 herramientas probadas como persona con `scripts/prueba_ui/construir.py` (clic en el menú de la cinta, elegir con el
visor, teclear, vista previa, Enter, medir, reabrir, deshacer, Esc, Tab, asas y ventana chica). Fuente del comportamiento:
las 20 capturas de `analisis/capturas_fusion` (solo quedan las pendientes) y la sección «Construction geometry» de `docs/fusion_docs`.
Especificación: [brechas_construir.md](../brechas_construir.md).

## Punto de partida (antes de cambiar nada)

Corrida: 298 comprobaciones, 10 con ✗ (`evidencias/construir_2026-11-01/antes/construir.log`). Las 20 abren, eligen con el
visor, calculan bien lo que ya tenían, reabren y deshacen, sin excepciones en un slot de Qt. Lo que falla son las filas del
panel contra las capturas (6 ✗: CON-1) y la API (4 ✗: B-130, B-131). «A medias» = lo que hay anda y falta lo de la columna.

| Herramienta | Antes | Evidencia medida | Falta |
|---|---|---|---|
| Plano de desfase | A medias | z = 12, normal Z; asa 10 → 25 | Al objeto, Desfase, Redimensionar |
| Plano en el ángulo | A medias | contiene la arista, normal.z = cos 30°; asa 0 → 50 | Desfase, Tipo de extensión, Redimensionar |
| Plano tangente | A medias | a 10 mm del eje; asa 0 → 70 | Desfase, Tipo de extensión, Redimensionar |
| Plano medio | A medias | z = 10 | Tipo de extensión, Redimensionar |
| Plano perpendicular | A medias | pasa por el vértice, normal ⟂ Z; asa 0 → 10 | Lugar tocado, U/V, Objeto de referencia, Extensión |
| Plano a través de dos aristas | A medias | contiene las dos, normal Z | Desfase, Tipo de extensión, Redimensionar |
| Plano a través de tres puntos | A medias | z = 20 con vértices | Puntos de forzado, Desfase, Tipo de extensión, Redimensionar |
| Plano en ruta | A medias | (105, −30, 0), normal X; asa 0,5 → 1,25 | Absoluto, Al objeto, eje como ruta, cadena |
| Eje a través de cilindro/cono/toroide | A medias | pasa por (−160, 0), dirección Z | Tipo de extensión, Redimensionar |
| Eje perpendicular a la cara | A medias | pasa por el vértice, dirección Z | Lugar tocado, puntos de forzado, Tipo de extensión, Redimensionar |
| Eje a través de dos planos | A medias | X por el origen | Tipo de extensión, Redimensionar |
| Eje a través de dos puntos | A medias | diagonal correcta | Puntos de forzado, Tipo de extensión, Redimensionar |
| Eje a través de arista | A medias | dirección Y por el vértice | Tipo de extensión, Redimensionar |
| Punto en vértice | A medias | el vértice exacto | Puntos de forzado |
| Punto a través de dos aristas | Anda | (100, −30, 0) | Panel único |
| Punto a través de tres planos | Anda | (0, 0, 0) | Panel único |
| Punto en el centro | Anda | esfera (−40, 60, 10), círculo (160, 0, 0) | Panel único |
| Punto en arista y plano | Anda | (0, −15, 20) | Panel único |
| Punto a lo largo de la ruta | A medias | (110, −30, 0); asa 0,5 → 1,25 | Físico, cadena |
| SCU | A medias | origen y desfase correctos; solo con origen acepta, aunque la fila Eje X figuraba obligatoria | Forzar, Alineación Z y X, panel de información |

Todas las de arriba, además: 19 paneles distintos en vez de uno (CON-1) y sin nombres de plano en el lienzo (CON-8).

## Estado final

Corrida: 635 comprobaciones, 0 con ✗ (`evidencias/construir_2026-11-01/despues/construir.log`), también en 1024x640 y 800x520
y con la pieza real. Las 20 andan. Todas abren el mismo panel GEOMETRÍA DE CONSTRUCCIÓN (el SCU el suyo, como Fusion); los
puntos de forzado valen en Punto en vértice, Eje a través de dos puntos, Plano a través de tres puntos, Eje perpendicular y SCU.

| Herramienta | Antes | Después | Medido en la ventana |
|---|---|---|---|
| Plano de desfase | A medias | Anda | z = 12; Al objeto z = 20 y sigue al punto; Desfase 3 → z = 15; asa 10 → 25 |
| Plano en el ángulo | A medias | Anda | contiene la arista, normal.z = cos 30°; Desfase 4 a 4 mm de la arista |
| Plano tangente | A medias | Anda | a 10 mm del eje; Desfase 2 a 12 mm |
| Plano medio | A medias | Anda | z = 10 |
| Plano perpendicular | A medias | Anda | cara plana U normal X, V normal Y; cara curva contiene la normal del lugar; Distancia a 7 mm |
| Plano a través de dos aristas | A medias | Anda | contiene las dos; Desfase 5 → z = 25 |
| Plano a través de tres puntos | A medias | Anda | z = 20 con vértices y puntos de forzado; Desfase −5 → z = 15 |
| Plano en ruta | A medias | Anda | Proporcional y Absoluto x = 105; Al objeto x = 100, con Desfase 103; cadena 230, sin cadena 215; pasa del final 250 |
| Eje a través de cilindro/cono/toroide | A medias | Anda | pasa por (−160, 0), dirección Z |
| Eje perpendicular a la cara | A medias | Anda | lugar tocado (−105, 5, 20); cara curva dirección radial; con punto, el vértice |
| Eje a través de dos planos | A medias | Anda | X por el origen |
| Eje a través de dos puntos | A medias | Anda | diagonal correcta, también con puntos de forzado |
| Eje a través de arista | A medias | Anda | dirección Y; Al objeto llega a la esfera (límites −3 a 83) |
| Punto en vértice | A medias | Anda | (−115, −15, 20) y centros, tangenciales y puntos de arista |
| Punto a través de dos aristas | Anda | Anda | (100, −30, 0) |
| Punto a través de tres planos | Anda | Anda | (0, 0, 0); acepta un boceto |
| Punto en el centro | Anda | Anda | esfera (−40, 60, 10), círculo (160, 0, 0) |
| Punto en arista y plano | Anda | Anda | (0, −15, 20) |
| Punto a lo largo de la ruta | A medias | Anda | Proporcional (110, −30, 0); Físico y cadena |
| SCU | A medias | Anda | Forzar solo al abrir; origen (−115, −15, 25) con X = Y del diseño; solo origen, ejes del diseño; panel de información |

**Pieza real:** boceto en un plano a 30°, extrusión y cambio de la cota 20 → 35: la tapa y el plano apoyado en ella se
movieron 15,000 mm por la normal (esperado 15). Captura `construir_pieza_real.png`.

## Comparación contra las capturas de Fusion

| Panel | Captura | Se parece | No se parece |
|---|---|---|---|
| Desfase | `Fusion360_1KqLnDOhMJ` | Título, Tipo, Método, Plano con Seleccionar, Extensión con ícono y sus dos opciones | Arte de íconos, ancho, tema oscuro |
| En el ángulo | `Fusion360_JvvEDbgtiD` | Tipo, Método, Arista | Lo mismo |
| Tangente | `Fusion360_qdZmlhYKdO` | Tipo, Método, Cara, Objeto de referencia | Lo mismo |
| Plano perpendicular | `Fusion360_yFmceMLWXX` | Cara, Dirección con 2 botones (U rayas inclinadas, V verticales), Extensión | Lo mismo |
| Eje a través de cilindro | `Fusion360_q1eMpSVKc9` | Tipo Eje marcado, Método, Cara | Lo mismo |
| Punto en vértice | `Fusion360_H4umkbMhwA` | Tipo Punto marcado, Método, Punto | Lo mismo |
| Listas de Método | `Fusion360_5v1z5ILYVi`, `6QaYOrdq6z`, `QnOgP8cHDT` | Mismos métodos, mismo orden, cada uno con ícono | Arte de íconos |
| SCU e información | `Fusion360_VOC2mD8BlU` | Fila Forzar, panel aparte con el texto de la captura, Consejos plegable y Cerrar | Aviso de Ctrl en el panel, que Fusion no muestra |

Diferencias que quedan a propósito, por el estilo de la casa: ancho 320 contra unos 240 px, Aceptar naranja y siempre activo
(Fusion lo tiene gris hasta que está todo elegido; acá el clic explica qué falta), preajustes «⋯» y ayuda «?». Lo que difería y se
arregló: botón «Elegir…» → «Seleccionar», íconos U/V ilegibles, título del SCU cortado, información que tapaba Comentarios y
quedaba debajo del navegador en 800x520.

## Decisiones tomadas por inferencia

La ayuda no alcanza para estos casos y Fusion real quedó cerrado. Se comparan en la pasada con Fusion
(`prueba_nocturna_2026-10-31.md`, sección 0b).

- Objeto de referencia plano en Plano perpendicular: el plano pasa por la recta donde se corta con la cara.
- Plano perpendicular en cara curva: contiene la normal del lugar, con su normal en la dirección U de la superficie. La
  [nota de soporte de Autodesk](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/How-to-create-a-construction-plane-perpendicular-normal-to-axis-in-Fusion-360.html)
  confirma Cara, U o V y Objeto de referencia opcional, sin más detalle.
- Puntos tangenciales: cuatro cuadrantes a media altura en cilindro y cono, ecuador y polos en esfera, anillos exterior y
  superior en toroide.
- SCU: orden de giros X, Y, Z sobre sus propios ejes.
- Sentido de U y V en cada cara.
- Tipo de extensión en los métodos sin captura, y tamaño de Predeterminado y Extendido.
- Tipo bloqueado al editar: un plano editado sigue siendo plano, para no romper los pasos que lo usan.
