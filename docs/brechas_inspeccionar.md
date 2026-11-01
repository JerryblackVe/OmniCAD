# INSPECCIONAR: capturas de Fusion contra OmniCAD

Especificación de las filas INS-n de `docs/seguimiento/` y de la parte de P-25f que se ve en las capturas. El estado vive
solo allá.

**Fuentes:** 38 capturas de Fusion en español en `C:\Users\mosos\Desktop\DISEÑO FUSION 360\inspeccionar` y la sección
«Analysis tools» de `docs/fusion_docs` (`fusion-model`; árbol en `docs/fusion_docs/indice/fusion-model.md`, líneas 116 a 139).
Se comparó el 2026-11-01 contra los campos reales de cada comando y con pruebas por API.

**Límites de esta revisión:**

- Ninguna herramienta se probó en la ventana, y `todo.py` no tiene una pieza de INSPECCIONAR.
- Por API, los 9 tipos de análisis se crean, se listan, se ocultan y se quitan. Eso no prueba que se dibujen bien.
- No hay captura del panel de Interferencia. Sale de la ayuda.
- Sustainability Insights no está en la ayuda local: sale solo de las capturas.

## Estado por herramienta

| Herramienta | Estado | Qué falta |
|---|---|---|
| Medir | **A medias** | INS-2 |
| Interferencia | **A medias** | INS-3 |
| Análisis de curvatura en peine | Casi | Valores por defecto y deslizadores: INS-6 |
| Análisis cebra | Completo en campos | Nada |
| Análisis de mapas de entorno | **Panel vacío** | INS-1 |
| Análisis de ángulo de desmoldeo | **A medias** | INS-4 |
| Análisis del mapa de curvatura | Completo en campos | Comprobar Límite máximo y mínimo en la ventana |
| Análisis de la isocurva | Casi | Elegir caras: INS-6 |
| Análisis de accesibilidad | **A medias** | INS-5 |
| Análisis de radio mínimo | **A medias** | INS-5 |
| Análisis de sección | Casi | INS-6, INS-8 |
| Centro de masa | **A medias** | INS-7 |
| Sustainability Insights | **No existe** | P-25f, sección propia abajo |
| Mostrar colores de componente | Anda con Mayús+N | Color del componente de ciclo: INS-7 |
| Mostrar grupos de caras de malla | **Grisado** | P-25f, sección propia abajo |

El menú de OmniCAD suma Revisar geometría, Reparar cuerpo y Buscar componentes similares. Se quedan: Fusion tiene equivalentes.

## INS-1 · Análisis de mapas de entorno

Hoy el panel no tiene ningún campo y la API no acepta opciones.

| Fila | Control |
|---|---|
| Cuerpos | Selección |
| Entorno | Campo · Campo de nieve · Claraboya · Cruce · Fotomatón · Lecho de lago seco · Luz cálida · Luz de rejilla · Luz fría · Luz suave (por defecto) · Plaza · Resaltado de cerco · Resaltado nítido |
| Rotar | Grados, con deslizador; 0.0 deg |
| Aplicar simet… | Casilla encendida. La ayuda la llama Mirror finish; el texto de la captura está cortado |

Comportamiento según `Analyze surface reflections with environment map`: aplica un cromo temporal a los cuerpos. Con la
casilla encendida refleja el entorno; apagada queda el cromo sin reflejo. Cancelar devuelve el aspecto del diseño. Aceptar deja
el análisis en la carpeta Análisis. Base que ya existe: `colores_mapa_entorno` en `nucleo/analisis.py`, con `rotacion`.

## INS-2 · Medir

| Fila | Control |
|---|---|
| Filtro de selección | 3 botones: caras, aristas o vértices · cuerpos · componentes |
| Precisión | 0 · 0.1 · 0.12 · 0.123 (por defecto) · 0.1234 · 0.12345 · 0.123456 · 0.1234567 · 0.12345678 |
| Unidades secundarias | Ninguno · cm · m · pulg. · ft. Se recuerda entre sesiones y va entre paréntesis |
| Borrar selección | Botón |
| Mostrar puntos de forzado | Casilla. Ctrl fija al punto; Mayús los oculta |
| Resultados | Según la tabla de `Measure reference` |
| XYZ Delta | Ninguno · Sistema del componente 1 · del componente 2 · global. Solo con vértices |

También: pasar sobre un valor lo resalta en el lienzo; clic en un valor lo copia. Panel alto, con botón Cerrar.
Hoy hay dos filas de selección y una casilla Centro a centro: esa casilla se conserva como extra.

## INS-3 · Interferencia

Ayuda: `Interference reference` y `Detect interferences and coincident faces`.

- Selección de cuerpos o componentes, casilla Incluir caras coincidentes y botón Calcular.
- Sin resultados: mensaje «No se detectaron interferencias».
- Con resultados: diálogo con tabla ordenable por columna, grupos con su volumen, y Mostrar todas las interferencias.
- Modo directo: columna Quitar volumen, cambio de Objetivo y Herramienta, y Aceptar corta. La ayuda dice cuándo aparece.

## INS-4 · Análisis de ángulo de desmoldeo

| Fila | Control |
|---|---|
| Cuerpo · Dirección | Selección |
| Ángulo de desmoldeo | Dos valores, −2.0 y 2.0 deg, con deslizador de dos topes; rango hasta ±90 |
| Zona de tolerancia | Casilla encendida |
| Tolerancia | Dos valores, −0.5 y 0.5 deg, con deslizador de dos topes |
| Opacidad | 100, con deslizador |
| Calidad alta | Casilla |

Hoy son Ángulo mínimo 0 y máximo 3 e Invertir dirección. No hay campo de dos topes: hay que crearlo en `ui/comando.py`.

## INS-5 · Accesibilidad y Radio mínimo

**Accesibilidad:** Cuerpo, Dirección, Opacidad (100, deslizador) y Cambiar dirección: Dirección 1, Dirección 2 o Ambas.
Hoy no hay Opacidad y es una casilla Invertir.

**Radio mínimo:** Cuerpo, Radio máximo de la herramienta (25.00 mm), Radio mínimo (0.000 mm, con flechas y deslizador),
Opacidad (100) y Bordes afilados (casilla). Hoy hay un solo Radio de la herramienta.

## INS-6 · Ajustes menores

- **Curvatura en peine:** Densidad 50 con deslizador, rango 2 a 100; Escala 10.000 con deslizador. Hoy 30 y 1.
- **Isocurva:** Cuerpos/Caras: la selección acepta caras. Hoy solo cuerpos.
- **Sección:** Color de sección por defecto Desde el componente (hoy Personalizado). Mostrar rayado encendido (hoy apagado).

Los valores por defecto cambian solo en el panel: los análisis guardados y la API quedan como están.

## INS-7 · Centro de masa y colores de componente

**Centro de masa:** hoy es un resultado que se va al cerrar. Tiene que quedar en la carpeta Análisis, ser asociativo, y
poder medirse desde él, ocultarse y borrarse. Selección acepta cuerpos o componentes. Ver `Center of mass`.

**Colores de componente:** agregar clic derecho › Color del componente de ciclo, y el color en lienzo, navegador y timeline.

## INS-8 · Paneles de información

Fusion abre un panel aparte con texto, sección plegable Consejos, Más información y Cerrar. Capturas: Análisis de sección y
Mapa de curvatura. Comparte componente con el del SCU (CON-6): se hace uno solo.

**Sección:** «Cree varios análisis de sección y, a continuación, ajuste su visibilidad en el navegador para alternar entre
ellos.» Consejo: «La opción Color de sección se establece por defecto en Desde el componente, y muestra el color de la vista
en sección codificado por componente. Defínalo como Personalizado para cambiar toda la vista en sección a un único color que
usted especifique.»

**Mapa de curvatura:** el texto de la captura `Fusion360_YNTu6tcUab.png`, con el consejo sobre la carpeta Análisis.

Más información abre el artículo local si existe. Nunca una página de Autodesk.

## P-25f · Mostrar grupos de caras de malla

Mayús+F muestra u oculta los grupos de caras de los cuerpos de malla y oculta colores de componente, materiales y aspectos.
`generate_face_groups` ya existe: falta la clave en la cinta, el atajo y su herramienta en la API.

## P-25f · Sustainability Insights

En Fusion es un complemento de un tercero (Gravity), con sus Términos de servicio.

**Decisión:** se hace una versión local, sin cuenta ni internet. Cada factor de CO₂ lleva su fuente; el resultado se muestra
como estimación. Si un factor no tiene fuente, se deja vacío y se avisa.

**Pestaña Percepciones**

| Fila | Control |
|---|---|
| Seleccionar cuerpo | Selección |
| Tipo de manufactura | Texto; «Seleccione un cuerpo…» sin selección |
| Material del cuerpo | Texto; «No hay cuerpo seleccionado» sin selección |
| Material más cercano | ABS · ASA · Aluminio · Cobre · Nylon · PTFE · PVC · Policarbonato · Polietileno · Polipropileno · Acero inoxidable · Acero · Titanio · Personalizado |
| Sobrescritura de volumen del stock | Sin sobrescritura · Valores manuales · Seleccionar un cuerpo |
| Región de manufactura | África · Asia · Australia · Europa · Norteamérica · Sudamérica |
| País de manufactura | Gris hasta elegir región |

**Pestaña Materiales personalizados:** Nombre del material · CO2 por kg (1.00) · Densidad g/cm³ (1.00) · Material más parecido ·
Información · Crear material · Importar materiales · Exportar materiales · Materiales personalizados · Información.

Las capturas no muestran el resultado con un cuerpo elegido: la salida es decisión del agente, kg de CO₂ con el cálculo a la vista.

Pila de fijadores (Fastener Stack Analysis) no aparece en las capturas y queda fuera de esta tanda.
