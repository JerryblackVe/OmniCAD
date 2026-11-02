# Herramientas de SÓLIDO: capturas de Fusion contra OmniCAD

Especificación de las filas CAP-n de `docs/seguimiento/`. El estado vive solo allá.

**Fuente:** 120 capturas de la interfaz de Fusion en español, en `analisis/capturas_fusion (solo quedan las pendientes; ver su INDICE.md)`.
Se miraron todas el 2026-10-31. La comparación salió de los campos reales de cada comando (`CATALOGO`, `campos()`)
y de la firma de la API. Las capturas muestran el panel recién abierto: lo que Fusion agrega después de elegir
geometría se saca de `docs/fusion_docs/` con `scripts/fusion_docs.py`.

**Carpetas mal rotuladas (no confiar en el nombre):**

| Carpeta | Qué tiene de verdad |
|---|---|
| `PRISMA` | Cilindro. No hay ninguna captura de Prisma (Box): usar `create-a-solid-box` de la ayuda |
| `ESFERA` | Vacía |
| `TOROIDE` | Esfera |
| `BOBINA` | Toroide (4 capturas) y Bobina (4) |
| `EDITAR CARAS` | Editar cara, más 2 copias exactas de Llenado de contorno |
| `OTROS` | División de silueta, Alinear, Dividir cara, Mover/Copiar, Reemplazar cara, Cara de desfase, Dividir cuerpo |

## Resumen por herramienta

| Herramienta | Estado en OmniCAD | Qué falta |
|---|---|---|
| Editar cara | **No existe** (ni comando, ni operación, ni API) | CAP-1 |
| Rosca | Existe | 13 de 18 tipos, tamaños chicos, Designación automática, biblioteca: CAP-2 |
| Agujero | Existe, completo en geometría | 4 cónicas de 6 y los tipos de CAP-2; botones con ícono; sección plegable |
| Barrido | Existe | Pestaña Análisis (CAP-3); Selección de cadena apagada por defecto (CAP-12) |
| Solevación | Existe | Pestaña Análisis, tabla de perfiles, Aristas tangentes, Selección de cadena: CAP-3, CAP-6, CAP-7 |
| Toroide | Existe | Posición y diámetros como Fusion: CAP-4 |
| Llenado de contorno | Existe | Eliminar herramientas y elegir celdas sin teclear: CAP-5 |
| Engrosar, Desmoldeo, Reemplazar cara, Dividir cara | Existen | Selección de cadena o Cadena tangente: CAP-6 |
| Cilindro, Esfera, Toroide, Bobina, Prisma | Existen | Dibujar con el mouse sobre el plano: CAP-8 |
| Mover/Copiar, Escala, Alinear, Simetría | Existen | Detalles de selección: CAP-9 |
| Extruir, Revolución, Nervio, Red, Tubería, Vaciado, Combinar, División de silueta, Cara de desfase, Dividir cuerpo | Completos en función | Solo presentación: CAP-10, CAP-11, CAP-12 |

Estado al 2026-11-01: CAP-1 a CAP-14 resueltos. Las columnas «En OmniCAD» de abajo describen el punto de partida.

## CAP-1 · Editar cara (Edit Face)

Ayuda: `Edit Face reference` y `Edit a face using T-Splines` (`fusion-model`). Fusion convierte UNA cara del
cuerpo en T-Splines, deja moverla y al aceptar vuelve a ser una cara del sólido o la superficie.

**Decisión:** no se hace un motor T-Spline. La cara se aproxima con una superficie B-spline y su grilla de
puntos de control se edita con el manipulador; al aceptar se recorta y se cose al cuerpo. Es el resultado que ve
la persona y no necesita paquetes nuevos. El espacio FORMA completo (P-25j, RH19) sigue aparte.

La operación va al timeline y guarda los desplazamientos de los puntos de control, para que se pueda reabrir.

Panel, de arriba abajo:

| Fila | Controles | Atajo |
|---|---|---|
| Cara | Selección de una cara | |
| Modo de transformación | Multi · Traslación · Giro · Escala | Alt+W · Alt+E · Alt+R |
| Espacio de coordenadas | Universal · Vista · Selección · Local por entidad | Alt+Z · Alt+X · Alt+C · Alt+V |
| Filtro de selección | Vértice · Arista · Cara · Todo | Alt+A · Alt+S · Alt+D · Alt+F |
| Comprobación de vista preliminar | Botón: muestra la forma final | |
| Opciones de selección (plegable) | Aumentar · Contraer | Shift+Arriba · Shift+Abajo |
| | Contorno · Aumentar contorno · Disminuir contorno | Alt+P · Alt+O · Alt+I |
| | Anilla · Aumentar anilla · Disminuir anilla | Alt+L · Alt+K · Alt+J |
| | Invertir selección · Selección de rango | Alt+N · Alt+M |
| Dividir caras (plegable) | Factor de longitud · Factor de anchura (enteros con flechas, desde 1) | |
| Curvatura en peines (plegable) | Longitud · Anchura (casillas) | |
| Simetría (plegable) | Longitud · Anchura (casillas) | |
| Entradas numéricas (plegable) | Valores del manipulador | |

Sugerencia de Fusion en el panel: seleccionar un vértice, una arista o una cara y pulsar Alt para extruir. El primer
ícono de Modo de transformación no tiene captura de su nombre; se usa «Multi» hasta confirmarlo.

## CAP-2 · Tipos de rosca

Lista completa de Rosca, en el orden del desplegable de Fusion. Sus tablas están en
`D:\Autodesk\webdeploy\production\9c5312dfff2e4569cd1d269973ddf11cb999f782\Fusion\Server\Fusion\Configuration\`
(`D:\Autodesk` es solo lectura).

| Tipo en Fusion | Archivo en `ThreadData/` | En OmniCAD |
|---|---|---|
| Perfil en M métrico ANSI | `ANSIMetricMProfile.xml` | Falta |
| Perfil métrico GB | `GBMetricprofile.xml` | Falta |
| Perfil métrico ISO | `ISOMetricprofile.xml` | Hay, M1.6 a M64. Fusion arranca en 0.25 mm |
| Rosca de tornillo autorroscante GOST | `GOSTSelf-tappingScrewThread.xml` | Falta |
| Rosca de tornillo para madera DIN | `DINWoodScrewThread.xml` | Falta |
| Roscas autorroscantes en pulgadas | `InchTappingThreads.xml` | Falta |
| Roscas autorroscantes en pulgadas para plásticos | `InchTappingThreadsForPlastics.xml` | Falta |
| Roscas autorroscantes métricas para plásticos | `MetricTappingThreadsForPlastics.xml` | Falta |
| Roscas de tornillo ACME | `ACMEScrewThreads.xml` | Hay |
| Roscas de tornillo unificadas ANSI | `ANSIUnifiedScrewThreads.xml` | Hay |
| Roscas de tubería BSP | `BSPPipeThreads.xml` | Hay |
| Roscas de tubería DIN | `DINPipeThreads.xml` | Falta |
| Roscas de tubería GB | `GBPipeThreadswithoutseal.xml` | Falta |
| Roscas de tubería ISO | `ISOPipeThreads.xml` | Falta |
| Roscas de tubería JIS | `JISPipeThreads.xml` | Falta |
| Roscas métricas de tornillo | `MetricFormingScrewThreads.xml` (formado; mapeo deducido del nombre, confirmar) | Falta |
| Roscas trapezoidales métricas ISO | `ISOMetricTrapezoidalThreads.xml` | Hay |
| Tuercas de bloqueo estándar AFBMA | `AFBMAStandardLocknuts.xml` | Falta |

Roscado cónico de Agujero (`TaperThreadData/`): BSP, DIN, ISO, JIS, NPT y NPT para PVC. OmniCAD tiene BSPT y NPT.

Reglas de los datos: se generan tablas en formato propio, sin copiar los XML al repo. Un tipo marcado `ExternalOnly`
no se ofrece en una cara interior. Rosca y Agujero usan la misma tabla.

Otros puntos: Designación también con «Automático»; Biblioteca («Pública» y el menú «más» que abre la ventana de la
biblioteca, según `Thread reference`).

## CAP-3 · Pestaña Análisis

Barrido y Solevación tienen dos pestañas: Operación y Análisis. Es la misma tarea que SUP-20 (diálogos de superficie).
Tipo de análisis, con cuatro íconos:

| Tipo | Opciones |
|---|---|
| Ninguno | Cuerpos |
| Cebra | Cuerpos · Dirección (2 íconos) · Repetición 20 · Opacidad 100 · Bloquear rayas · Calidad alta |
| Mapa de curvatura | Cuerpos · Tipo (3 íconos) · Visualizar (2 íconos) · Escala 1.000 · Opacidad 100 · Calidad alta |
| Isocurva | Cuerpos · Tipo (3 íconos) · Isocurvas 5 · Curvatura en peines → Densidad 50 y Escala 10.000 |

Repetición, Opacidad, Isocurvas, Escala y Densidad llevan número y deslizador. Los comandos sueltos `cebra`,
`mapa_curvatura` e `isocurva` tienen que ganar las mismas opciones: hoy traen 2 campos cada uno.

## CAP-4 · Toroide

Fusion: Perfil · Diámetro interior · Diámetro del toroide · Posición (Interior / En el centro / Exterior) · Operación.
OmniCAD: Diámetro mayor · Diámetro del tubo, sin Posición. Ver `create-a-solid-torus`. La API gana el mismo
parámetro y `major_radius` / `minor_radius` siguen funcionando.

## CAP-5 · Llenado de contorno

Fusion: Seleccionar herramientas · Seleccionar celdas · Operación · Eliminar herramientas (casilla).
OmniCAD no tiene Eliminar herramientas y las celdas se teclean como texto. Tienen que elegirse con clic en el visor
y con una lista de casillas, con resalte de cada celda.

## CAP-6 · Cadena

| Comando | Casilla de Fusion | Por defecto |
|---|---|---|
| Engrosar | Selección de cadena | Encendida |
| Dividir cara | Selección de cadena | Encendida |
| Solevación | Selección de cadena | Encendida |
| Desmoldeo | Cadena tangente | Encendida |
| Reemplazar cara | Cadena tangente | Apagada |

Reusar lo que ya hacen `cadena` (Barrido, Tubería) y `tangente` (Vaciado, Cara de desfase). La API gana el mismo parámetro.

## CAP-7 · Solevación

Perfiles y Raíles son listas con filas, botones + y ✕; hoy son una selección y un texto `n.º:ángulo:peso;…`.
Cada perfil tiene su condición en su fila, según `Loft reference`. Tipo de guía: dos íconos. Aristas tangentes: dos
íconos, Fusionar (por defecto) y Mantener; hoy es una casilla apagada dentro de «Más opciones».

## CAP-8 · Dibujar primitivas con el mouse

Fusion: elegir plano, clic en el centro, mover para el diámetro, clic; después ajustar con asas. Los valores de las
capturas (97.767, 102.655, 107.33 mm) salieron de ahí. En OmniCAD el clic solo ubica el centro. Vale para Prisma,
Cilindro, Esfera, Toroide y Bobina; Bobina en Fusion tiene una sola fila Plano, no Plano + Centro. Ver
`create-a-solid-cylinder`, `create-a-solid-box`, `create-a-solid-sphere`, `create-a-solid-torus`, `coil-reference-solid`.

## CAP-9 · Selección

- **Mover/Copiar:** Definir punto de giro es un botón que entra a un modo y se cierra con Terminado (✓). Objeto:
  «Objetos del boceto» elige entidades sueltas. Una sola fila Selección que cambia con el objeto.
- **Escala:** una sola fila Entidades que acepta cuerpos y bocetos; hoy son dos.
- **Alinear:** fila Objeto como en Fusion.
- **Simetría:** las operaciones se eligen con clic en el timeline; hoy se teclean sus nombres.

## CAP-10 · Campo de botones con ícono

Fusion usa filas de íconos donde OmniCAD solo tiene desplegables. Falta un campo nuevo en `ui/comando.py`
(mismo valor que `Opciones`, un botón por opción, tooltip con el nombre) y dibujar los íconos en `ui/iconos_extra.py`.

Usarlo en: Agujero (Colocación, Tipo de agujero, Tipo de rosca, Punto de taladro) · Nervio y Red (Dirección del
espesor) · Solevación (Tipo de guía, Aristas tangentes) · Engrosar y Vaciado (Tipo) · Combinar (Operación) · Mover/Copiar
(Tipo de desplazamiento) · Desmoldeo (Tipo) · Extruir (Tipo) · Análisis y Editar cara.

Los desplegables también llevan ícono en Fusion: Dirección, Tipo de extensión, Inicio, Sección, Posición, Tipo de
barrido. De 96 listas revisadas en 9 comandos, 7 tienen ícono hoy.

## CAP-11 · Textos

Usar el texto de Fusion en español. Cambia solo el texto: claves y valores de la receta quedan igual.

| Hoy | Fusion |
|---|---|
| Intersecar · Nuevo cuerpo | Intersección · Cuerpo nuevo |
| Ruta única · Ruta + carril guía · Ruta + superficie guía · Cuerpo sólido | Ruta individual · Ruta + Rail guía · Trayectoria + Superficie guía · Barrido sólido |
| Carriles | Raíles |
| Paralela | Paralelo |
| Simétrica | Simétrico |
| Abocardado | Escariado |
| Con holgura | Espacio libre |
| Punta del taladro · En ángulo · Plana | Punto de taladro · Ángulo · Plano |
| Hasta (Agujero) | A |
| Afilado (Engrosar, Vaciado) | Agudo |
| Extensión | Tipo de extensión |
| Curvas (Nervio, Red) | Perfil |
| Hasta el siguiente · Profundidad | Al siguiente · Distancia |
| Extender curvas | Alargar curvas |
| Extender herramienta (Dividir cara) | Alargar herramienta de división |
| Extender herramienta (Dividir cuerpo) | Extender las herramientas de división |
| Mantener herramientas | Conservar herramientas |
| Método (Desmoldeo) | Tipo |
| Lados (Desmoldeo) | Lados del dibujo |
| Tipo de movimiento · Movimiento libre · Girar | Tipo de desplazamiento · Desplazamiento libre · Rotar |
| Bocetos (Mover/Copiar) | Objetos del boceto |
| Hasta (Alinear) | A |
| Sobre · Dentro · Fuera (Bobina) | En el centro · Interior · Exterior |
| Herramientas · Celdas a rellenar | Seleccionar herramientas · Seleccionar celdas |
| Plano / punto | Colocación (Cilindro) · Punto (Esfera) · Perfil (Toroide) |

Antes de cambiar uno, buscarlo en `tests/` y `scripts/prueba_ui/`: varios buscan por texto.

## CAP-12 · Valores por defecto y orden

Cambia solo el panel de un comando nuevo. Los `PARAMS` de la operación y los valores por defecto de la API no se tocan:
una receta vieja se tiene que abrir igual.

| Comando | Cambio |
|---|---|
| Barrido | Selección de cadena encendida |
| Rosca | Modelada apagada (cosmética) |
| Revolución | Eje de proyecto visible y encendido |
| Extruir | Inicio visible, entre Perfiles y Dirección |
| Agujero | Punto de taladro visible; sección plegable «Configuración de la forma» |
| Bobina | Giro, Ángulo y Posición de sección visibles, en el orden de Fusion; un solo Giro |
| Red | Alargar curvas visible y encendida |
| Nervio y Red | Cambiar dirección como botón, no casilla |
| División de silueta | Dividir cuerpo vaciado por defecto |
| Rosca | Orden: Caras, Modelada, Longitud completa, Biblioteca, Tipo, Tamaño, Designación, Clase, Dirección, Recordar tamaño |

Esto corrige en esos comandos la regla «Más opciones» de `docs/auditorias/ui_paneles_2026-10-31.md`: en estas herramientas
manda lo que muestra Fusion. El resto de esa auditoría sigue vigente.
