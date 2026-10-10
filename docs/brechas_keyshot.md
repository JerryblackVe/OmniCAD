# Brechas frente a KeyShot

Fecha: 2026-10-09.
Fuentes (leídas ese día): [keyshot.com](https://www.keyshot.com/), manual de KeyShot
([iluminación](https://manual.keyshot.com/manual/lighting), [materiales y su índice](https://manuals.keyshot.com/kss2025/en-us/manual/materials.html),
[animación](https://manual.keyshot.com/manual/animation), [exportar y formatos de salida](https://manual.keyshot.com/manual/models-tab/export),
cola de render, configurador), [AI Shots en KeyShot 2026.1](https://www.keyshot.com/blog/ai-shots-2026-1-introduction/) y
[KeyShot Studio AI](https://www.keyshot.com/blog/introducing-ai-keyshot-studio/).

**Regla:** KeyShot es propietario. Se replican las FUNCIONES y opciones, nunca código, textos ni recursos
(biblioteca de materiales y de entornos incluidas: los nuestros se hacen desde cero).

KeyShot es lo que se mira cuando se quiere «imagen de producto en minutos»: arrastrar un material a una pieza, ver
el resultado ya trazado en el lienzo, tocar pocos controles. Esa idea de uso es la misma que la del espacio
RENDERIZAR de Fusion, así que acá la experiencia de Fusion y la de KeyShot casi coinciden.
Esta lista alimenta el **pendiente 4** (motor de render, materiales, colores e iluminación). V-Ray va en
`docs/brechas_vray.md`; lo que se repite entre los dos queda en un solo lugar.

## Qué tiene hoy OmniCAD (verificado en `ui/render.py`)

Espacio RENDERIZAR con cinta, lienzo, paneles «Aspecto» y «Configuración de escena» y galería de renders. Dos
motores que dan el mismo resultado: OpenGL con sombreado por píxel (Fresnel + Blinn-Phong, reflejo del entorno,
barniz, vetas de madera, mapa de sombras, plano de suelo, oclusión ambiental, anti-alias) y CPU
(`nucleo/render_cpu.py`). El aspecto es por CUERPO: color, metálico, rugosidad, transparencia, barniz, patrón.
Entornos = degradados de cielo (`ENTORNOS`), no imágenes HDRI. **Es rasterizado, no trazado de rayos.**

## Decisión que hay que tomar primero: el motor

| Opción | Qué es | Pros | Contras |
|---|---|---|---|
| **A. Cycles de Blender** como motor externo | Exporta la escena, `blender -b` en segundo plano, vuelve la imagen. Es B1 de `brechas_blender.md`. | Calidad de trazado de rayos YA; HDRI, vidrio, subsuperficie, ruido reducido. Costo de programar: bajo. | Necesita Blender instalado. No es «en vivo» en el lienzo. |
| B. Trazador propio progresivo | Camino de rayos en CPU (con mosaicos y varios núcleos) o en la placa; la imagen se refina sola. | Vive en la app, estilo KeyShot (se ve converger). | Mucho trabajo; en Python puro es lento; puede pedir una biblioteca de rayos nueva (ej. Embree). |
| C. Mejorar el rasterizado | HDRI como luz de imagen, materiales PBR, luces de área aproximadas. | Rápido, sin dependencias. | Sin vidrio grueso, cáusticas ni rebote de luz. |

**DECIDIDO por el usuario (2026-10-09): los tres motores, en este orden** — 1) escena común + OpenGL mejorado
(ítems «con el motor actual»), 2) Cycles de Blender (B1), 3) trazador propio.
**Se pueden tener varios a la vez** (2026-10-09): ya hay dos (OpenGL y CPU) con selector de motor en el render.
Hace falta una escena común (geometría, aspectos, luces, cámara) que cada motor traduzca; el usuario elige en el
combo «Motor». **Recomendación:** C ahora (los ítems de «Con el motor actual» de abajo), A como puente para imágenes finales, y B
solo si el usuario quiere el modo «en vivo». Es decisión del usuario: cuesta dependencias y tiempo.

## Para hacer

### Con el motor actual (rasterizado) — se puede empezar ya

| # | Función (en KeyShot) | Cómo debe sentirse (Fusion) | Estado / dónde engancha |
|---|---|---|---|
| KS1 | **Preajustes de iluminación y calidad**: Rendimiento, Básico, Producto, Interior, Joyería (cada uno cambia rebotes, sombras, suelo y cáusticas). | Un selector en «Configuración de escena» con 5 opciones y un texto de ayuda de una línea cada una. | Hay presets de gráficos en Preferencias (paso 2 del pendiente 10); falta el de render. |
| KS2 | **Entornos HDRI**: cargar un `.hdr`, girarlo, subir el brillo, usar o no de fondo; biblioteca propia de entornos. | «Configuración de escena › Entorno»: lista con miniaturas + deslizadores de giro y brillo; arrastrar un `.hdr` a la ventana. | Hoy los entornos son degradados (`visor3d.ENTORNOS`). El `.hdr` (Radiance) se lee con numpy; `.exr` pediría una biblioteca nueva: preguntar. |
| KS3 | **Material más completo**: índice de refracción, color de absorción, subsuperficie simple, anisotropía, emisivo, pintura metálica con escamas; mapas de textura (color, relieve, normal, rugosidad). | Panel «Aspecto» con las mismas pestañas y vista previa en una esfera; mismos controles en el boceto de material de Fusion. | Hay `acabado {metalico, rugosidad, transparencia, barniz, patron, color2}`. Ampliar `render_cpu.color_y_acabado`. |
| KS4 | **Aspecto por cara o región** (multimaterial). | Clic en una cara con «Aspecto» abierto y arrastrar el material; las caras sin aspecto heredan el del cuerpo. | Hoy es por cuerpo, guardado en el documento. |
| KS5 | **Biblioteca de materiales**: buscar, arrastrar y soltar sobre una pieza, favoritos, «materiales del proyecto», copiar y pegar el aspecto entre piezas. Categorías de KeyShot: básicos, avanzados, fuentes de luz, especiales. | Panel «Aspecto» con buscador (como la tecla S) y arrastrar a la vista; menú contextual «Copiar aspecto». | Hay panel de aspecto y lista de materiales; falta biblioteca ampliable (archivos `.json` de la carpeta del usuario). |
| KS6 | **Calcomanías y etiquetas**: una imagen sobre una cara con tamaño, giro y mezcla; varias a la vez. | INSERTAR › «Calcomanía»: cara + imagen + tamaño con manipulador en la vista; transparencia (alfa) respetada. | No existe. Muy útil para logos en piezas de producto. ⚠ Que KeyShot trae «Labels»: de memoria, no leído hoy. |
| KS7 | **Cámaras guardadas y profundidad de campo**: lista de cámaras con nombre, apertura y distancia de enfoque, perspectiva u ortográfica, desplazamiento de lente. | «Configuración de escena › Cámaras»: lista con «Guardar vista actual como cámara», miniatura y campos. | Hay cámara guardada con la escena (`a_dict()`); falta la lista y el desenfoque. |
| KS8 | **Giratoria (turntable) y vistas explosionadas en un clic**. Hecho en Animación con «explosión automática» según el ensamblaje. | ANIMACIÓN › «Giratoria»: ángulo, duración, cuadros; sale una animación lista. | Hay explosión, transformar, visibilidad y publicar video GIF/PNG. Buscado en el código: los tipos de `animacion.py` son transformar, restaurar, explosión, visibilidad, vista y anotación; no hay giratoria. |
| KS9 | **Cola de render y lotes**: encolar trabajos (imagen, animación) con resolución y cuadros; correr en segundo plano. | «Galería de renders» con pestaña «Cola»: orden, estado, cancelar, abrir carpeta. | Hay galería; buscado en el código: no hay cola. |
| KS10 | **Variantes y configurador**: renderizar TODAS las combinaciones de configuración × aspecto × cámara a una carpeta, con nombres por variante. | «Renderizar variantes»: tilda configuraciones, aspectos y cámaras; la cola hace el resto. Para fotos de catálogo. | OmniCAD ya tiene `configuraciones` en el documento (`administrar.py`): falta unirlas con el render y la cola. |
| KS11 | **Salida con alfa y por pases**: PNG con fondo transparente y sombra, EXR/TIFF 32 bits, PSD por capas (sombras, reflejos, oclusión, ID de material). Es parte de lo que KeyShot guarda como formatos. | En el diálogo de render: «Formato» y «Capas»; el archivo sale listo para componer. | Buscado en el código: el render hoy guarda solo PNG (`ui/render.py`, «Imagen PNG (*.png)»). Pases y máscaras: VR3 de `brechas_vray.md`. |

### Piden trazado de rayos (A o B de arriba)

| # | Función (en KeyShot) | Nota |
|---|---|---|
| KS12 | **Materiales de fuente de luz**: cualquier geometría como luz de área, de punto, con perfil IES o foco; con potencia y temperatura de color. | Con el rasterizador se aproxima; el resultado real pide rayos. |
| KS13 | **Vidrio grueso, gemas, cáusticas, subsuperficie y rebote de luz** (iluminación global). | Joyería e interior de KeyShot los usan. |
| KS14 | **Imagen que se refina sola en el lienzo** (muestreo progresivo con contador de muestras). | Es la experiencia central de KeyShot. Solo con la opción B. |

### Con IA — decisión del usuario

| # | Función | Nota |
|---|---|---|
| KS15 | **«AI Shots»**: restilizar la imagen, generar fondos, imaginar variantes y transformar, usando los datos 3D del modelo para no inventar piezas. El de KeyShot corre LOCAL con un modelo de edición de imágenes. | ⚠ Regla del proyecto: no gastar en APIs pagas sin pedido. Hoy se hace por fuera con las skills de imagen. Un equivalente local pide un modelo grande: no hacer sin preguntar. |

## Salida e intercambio

| Función | Estado |
|---|---|
| Exportar a **GLB** y **USD** para web, AR y comercio electrónico. | B3 de `brechas_blender.md` (hoy no hay). |
| **Configurador web**: variantes en una página. | Pendiente a futuro; sigue de KS10 y de B3. |
| **Complementos de CAD** (KeyShot trae plugin para Blender y otros). | OmniCAD ya tiene puente en vivo (`ui/puente.py`) y MCP: un «Enviar a KeyShot» exportaría a glTF/USD con materiales. ⚠ De memoria: no leído hoy. |

## Descartado a propósito

Render en la nube y en red de KeyShot (servicios de pago de ellos), biblioteca de pinturas de Axalta, tutoriales y
certificaciones.

## Sin verificar

- KS6, KS8, KS9, KS11: buscado en el código (2026-10-09), no probado en la app.
- Los nombres exactos de los tipos de material de KeyShot: el manual solo mostró las cuatro categorías.
- Detalle de KS15: las páginas describen el flujo pero no el precio ni los límites.
