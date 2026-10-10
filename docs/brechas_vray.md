# Brechas frente a V-Ray

Fecha: 2026-10-09.
Fuentes (leídas ese día): [V-Ray para Blender — funciones](https://www.chaos.com/vray/blender/features) y
[novedades](https://www.chaos.com/vray/blender/whats-new), [novedades de V-Ray 7 para 3ds Max](https://documentation.chaos.com/space/VMAX/113586464),
página de [V-Ray](https://www.chaos.com/vray). La página de funciones de V-Ray para Rhino no devolvió contenido.

**Regla:** V-Ray es propietario. Se replican las FUNCIONES y opciones, nunca código, textos ni recursos.

V-Ray es un motor de trazado de rayos de producción: más profundo y técnico que KeyShot, con mucho control. Lo que
vale tomar para OmniCAD no es su complejidad, sino sus **herramientas de control después del render** (mezcla de
luces, ventana de postproceso) y la **calidad física** (cámara, cielo, materiales). La decisión del motor
(Cycles, trazador propio o rasterizado mejorado) está en `docs/brechas_keyshot.md`: acá se da por tomada.
Alimenta el **pendiente 4**.

## Qué hace V-Ray (verificado)

| Área | Funciones leídas |
|---|---|
| **Motor** | CPU, GPU e híbrido; render interactivo (IPR). V-Ray 7 acelera el arranque de GPU hasta 2× y suma optimizaciones de CPU. |
| **Iluminación** | Iluminación global, luces con archivos IES y caída propia, modelo de Sol y Cielo, nubes procedurales, perspectiva aérea, niebla, iluminación con HDRI, luces adaptativas, interiores con paralaje, cáusticas rápidas (y en GPU), cielo nocturno, luminarias. |
| **Materiales** | Cabello, pelo, piel, PBR; kit de texturas procedurales; generador de materiales con IA; material tipo dibujo animado (Toon); material de desplazamiento; calcomanías; render de materiales de Cycles y conversor. |
| **Cámara y efectos** | Exposición física, exposición automática, balance de blancos; bloom, resplandor, polvo, rayones; viñeta; regiones de render con forma propia. |
| **Corte y escena** | «Clipper» para cortes y secciones, proxies, biblioteca de recursos (Cosmos) con variantes, dispersión (Scatter) con grupos, nube de puntos y *gaussian splats* con relighting. |
| **Reducción de ruido** | Con Intel o NVIDIA; en V-Ray 7 también sobre el «light cache»; canales de salida del denoiser. |
| **Ventana de render (VFB)** | Mezcla de luces (Light Mix), corrección de color, composición por capas, máscaras por píxel, comparación, presets de corrección. |
| **Fuera de la app** | Render distribuido (2.ª versión), Chaos Cloud, Vantage (tiempo real con enlace vivo), Veras (ideación con IA). |

## Para hacer

### Con el motor actual (rasterizado) — se puede empezar ya

| # | Función (en V-Ray) | Cómo debe sentirse (Fusion) | Estado / dónde engancha |
|---|---|---|---|
| VR1 | **Mezcla de luces (Light Mix)**: cambiar color e intensidad de cada luz DESPUÉS de renderizar, sin volver a renderizar. | Panel «Luces» en la ventana de render con un deslizador de intensidad y un selector de color por luz; la imagen cambia al instante. | La suma de luces es lineal: se guarda un acumulado por luz y se recombina. Con el rasterizado actual es directo y barato. |
| VR2 | **Ventana de postproceso (no destructivo)**: exposición, balance de blancos, curva de tono, bloom, resplandor, viñeta, corrección de color, comparar antes/después; los cambios no tocan la imagen original. | Pestañas en la ventana de render; «Reiniciar» y «Guardar con los cambios». | Hay galería y render; falta postproceso. Se hace en numpy sobre la imagen en flotante. |
| VR3 | **Elementos de render (pases)**: difuso, reflejo, refracción, sombra, oclusión, normales, profundidad, ID de material y de objeto, con máscaras por píxel. | «Renderizar › Salidas»: casillas por pase; salen como capas o archivos aparte. Los pases de ID dan máscaras exactas de cada pieza. | Va con KS11 de `brechas_keyshot.md`. |
| VR4 | **Cámara física**: ISO, obturador, f, exposición automática, balance de blancos; DOF. | En la cámara: los mismos tres números que un fotógrafo reconoce; «Auto» recorta el brillo. | Va con KS7. |
| VR5 | **Corte en el render (Clipper)**: plano de corte con tapa del color que se elija, aplicable solo a las piezas elegidas. | «Configuración de escena › Corte»: plano + piezas + color de tapa. Es el Análisis de sección, pero dentro de la imagen final. | Hay Análisis de sección; va con RH16 de `brechas_rhino.md`. |
| VR6 | **Sol y cielo físicos**: lugar, fecha y hora calculan el sol y el cielo; nubes y niebla ajustables. | «Entorno › Sol y cielo»: mapa o campos de latitud/longitud/fecha/hora; vista previa del cielo. | Hoy los entornos son degradados. Va con KS2 (HDRI). |
| VR7 | **Regiones de render** con forma propia (rectángulo, círculo, a mano) para probar una parte. | Dibujar la región en el lienzo; solo se renderiza eso. | Nuevo; en `LienzoRender`. |
| VR8 | **Material «dibujo animado» (Toon) y de borde**: contorno y bandas de color para ilustración técnica. | Un tipo más en el panel «Aspecto». Va con los modos de pantalla de RH16. | Nuevo. |
| VR9 | **Dispersión (Scatter)**: repartir copias de una pieza sobre una superficie con densidad, escala y giro al azar; en grupos. | Parte de «Patrón» (B12 de `brechas_blender.md`); sirve para césped, tachas, tornillos. | Ampliar `patron`. |
| VR10 | **Herramienta de render en la API/MCP**: cambiar el aspecto de un cuerpo, elegir cámara y entorno, y devolver la imagen. | Para agentes y `omnicad render`. Es también lo que usa el modo por lote. | ⚠ Hoy la API solo tiene `get_viewport_image`; el registro de la lámpara de pie anotó que faltaba una herramienta de aspecto. |

### Piden trazado de rayos

| # | Función (en V-Ray) | Nota |
|---|---|---|
| VR11 | **Iluminación global y cáusticas**, luces con IES, luces adaptativas, interiores con paralaje, materiales con subsuperficie y pelo. | Lo cubre la opción A (Cycles) de `brechas_keyshot.md`. |
| VR12 | **Reducción de ruido** (OIDN de Intel es de código abierto; NVIDIA, no). | Solo si hay un trazador propio. Con Cycles ya viene. ⚠ Que OIDN tiene licencia abierta: de memoria. |
| VR13 | **Render por mosaicos en varios procesos**, que no bloquee la ventana y se pueda cancelar y pausar. | Sirve para cualquier motor. Medir antes con `omnicad dev bench`. |

### Fuera de alcance por ahora

Render en la nube (Chaos Cloud) y distribuido, Vantage (tiempo real aparte), Veras y el Enhancer (IA de pago),
*gaussian splats*, cabello y piel, árboles y personas de la biblioteca Cosmos.

## Lo que queda mejor que en KeyShot

KeyShot gana en velocidad de uso; V-Ray gana en **control posterior**. Por eso VR1 (mezcla de luces) y VR2
(postproceso) van antes que cualquier material nuevo: cambian lo que hace el usuario con el resultado.

## Sin verificar

- La página de funciones de V-Ray para Rhino no devolvió datos; las listas salen de la página de V-Ray para
  Blender y de las novedades de V-Ray 7 para 3ds Max. Pueden variar entre integraciones.
- VR12 (licencia de OIDN) de memoria.
- Formatos del render de OmniCAD: buscado en el código, hoy solo PNG; no probado en la app.
