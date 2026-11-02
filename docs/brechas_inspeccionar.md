# INSPECCIONAR: capturas de Fusion contra OmniCAD

Especificación de lo que se resolvió el 2026-11-01 (INS-1 a INS-8 y la parte de P-25f que se ve en las capturas). Lo que dice
«hoy» describe el punto de partida. Resultado, mediciones y comparación por panel:
[auditorias/inspeccionar_2026-11-01.md](auditorias/inspeccionar_2026-11-01.md). Lo pendiente vive solo en `docs/seguimiento/`.

**Fuentes:** 38 capturas de Fusion en español en `analisis/capturas_fusion (solo quedan las pendientes; ver su INDICE.md)` y la sección
«Analysis tools» de `docs/fusion_docs` (`fusion-model`; árbol en `docs/fusion_docs/indice/fusion-model.md`, líneas 116 a 139).
Se comparó el 2026-11-01 contra los campos reales de cada comando y con pruebas por API.

No hay captura del panel de Interferencia: sale de la ayuda. Sustainability Insights no está en la ayuda local: sale solo de las capturas.

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

## Prompt para el agente

Entregado el 2026-11-01. Modelo sugerido: Opus 5, esfuerzo alto. Antes de usarlo, revisar que los IDs y las rutas sigan vigentes.

```text
ANTES DE TODO, invocá con la herramienta Skill: fable-method y ponytail al empezar; plan-then-do, tool-calling-guard, verify-before-commit y omnicad-test durante el trabajo; ponytail-review antes de cerrar. Pegá la salida real de ponytail-review en el informe.

OBJETIVO
Dejar INSPECCIONAR de OmniCAD igual a Fusion 360 y funcionando completo, resolviendo INS-1 a INS-8 y la parte de P-25f que corresponde a Sustainability Insights y grupos de caras de malla.

CONTEXTO DEL AGENTE
- Plataforma: Claude Code, en D:\PROGRAMA, rama main, sin worktree.
- Herramientas: archivos, shell, Python del venv (clon/.venv), MCP omnicad, ayuda local de Fusion, web.

TAREA PRINCIPAL
Probar las 15 herramientas de INSPECCIONAR como persona, clasificarlas en anda, a medias o no anda, y completar lo que falte en interfaz, cálculo, API (MCP y CLI), tests y documentación.

ENTRADAS
- Especificación: docs/brechas_inspeccionar.md → [PROVIDED]
- Filas pendientes: docs/seguimiento/faltantes.md (INS-1 a INS-8, P-25f) → [PROVIDED]
- Capturas: analisis/capturas_fusion (solo quedan las pendientes; ver su INDICE.md)→ [PROVIDED]
- Ayuda de Fusion: sección «Analysis tools» en docs/fusion_docs/indice/fusion-model.md; buscar con clon/.venv/Scripts/python.exe scripts/fusion_docs.py buscar <palabras> -s fusion-model y ver "<título>" -s fusion-model → [PROVIDED]
- Código: clon/omnicad/ui/comandos/inspeccionar.py, ui/comando.py, ui/cinta.py, ui/navegador.py, ui/ventana.py, nucleo/analisis.py, api/herramientas_analisis.py, api/herramientas_inspeccion.py → [PROVIDED]
- Comportamiento en la ventana de cada herramienta → [TO BE DISCOVERED BY AGENT]
- Factores de CO₂ por material, con fuente → [TO BE DISCOVERED BY AGENT]

PROCESO
1. Leer CLAUDE.md, AGENTS.md, Lecciones aprendidas de PROJECT_LOG.md, la especificación, las 38 capturas con Read y todos los artículos de la sección «Analysis tools», mirando sus imágenes.
2. Crear scripts/prueba_ui/inspeccionar.py y sumarla a PIEZAS de todo.py. Por cada herramienta: clic en la cinta, elegir en el visor, teclear valores, mover deslizadores, vista previa, Aceptar, reabrir desde la carpeta Análisis, ocultar, borrar, Enter, Esc, Tab, y ventana de 1024x640 y 800x520.
3. Correr esa pieza antes de cambiar nada y escribir docs/auditorias/inspeccionar_2026-11-01.md con una tabla: herramienta, anda / a medias / no anda, evidencia. Anotar en docs/seguimiento/ cada falla nueva con el siguiente ID libre. [REQUIERE: 2]
4. INS-1: hacer el panel de Mapas de entorno con los 13 entornos, Rotar, casilla de reflejo y cromo temporal que Cancelar revierte. La API acepta las mismas opciones.
5. INS-2: rehacer Medir con filtro, Precisión, Unidades secundarias recordadas, Borrar selección, puntos de forzado, XYZ Delta, resaltar y copiar valores. Conservar Centro a centro.
6. INS-3: agregar Calcular, tabla ordenable, Mostrar todas, componentes y Quitar volumen según la ayuda.
7. INS-4 e INS-5: crear en ui/comando.py el campo de dos topes y completar Desmoldeo, Accesibilidad y Radio mínimo, con cálculo real de cada opción.
8. INS-6: aplicar los ajustes de Curvatura en peine, Isocurva y Sección.
9. INS-7: pasar Centro de masa a la carpeta Análisis, asociativo, medible, ocultable y borrable; agregar Color del componente de ciclo con clic derecho.
10. INS-8: agregar los paneles de información. Reusar el del SCU si ya existe; si no existe, crearlo como componente compartido.
11. P-25f: activar Mostrar grupos de caras de malla con Mayús+F y crear Sustainability Insights local con sus dos pestañas, factores con fuente citada y resultado marcado como estimación. Dejar la fila P-25f con solo la pila de fijadores.
12. Volver a correr la pieza completa con una pieza real de varios cuerpos, cambiando una cota y comprobando que Centro de masa y los análisis se actualizan. Mirar las capturas y comparar cada panel con su imagen de Fusion, diciendo en una línea qué se parece y qué no. Arreglar lo que difiera. [REQUIERE: 4 a 11]
13. Regenerar docs/agentes/herramientas.md con omnicad tools --markdown --output docs/agentes/herramientas.md y scripts/claves_comandos.py si cambió alguna clave.
14. Verificar desde clon/: ruff check . y los tests tocados con ../scripts/turno.py, incluidos tests/test_analisis.py, test_api_analisis.py, test_api_inspeccion.py, test_comandos_inspeccionar.py, test_medir_previa_comandos.py, test_seguimiento.py y test_doc_agentes.py. Pegar la salida real.
15. Actualizar la auditoría con el estado final, borrar las filas resueltas, anotar ID y prueba en el Registro de PROJECT_LOG.md, y dejar en docs/auditorias/prueba_nocturna_2026-10-31.md (sección 3e) lo que falte probar.

DEPENDENCIAS
Los pasos 2 y 3 van antes de cualquier cambio. Los pasos 12 a 15 van al final.

REGLAS
- SÍ leer el artículo de la ayuda antes de cambiar cada herramienta. NO programar de memoria.
- SÍ consultar la web si un artículo no alcanza, y citar la fuente en la auditoría.
- NO inventar un factor de CO₂: sin fuente, el material queda vacío con aviso.
- NO conectar Sustainability Insights a ningún servicio externo. NO pedir cuenta.
- NO cambiar un análisis ya guardado: un documento viejo se abre y se ve igual. Probarlo con un test.
- NO cambiar los valores por defecto de la API.
- SÍ medir cada resultado con números y mirar la imagen: que se cree el análisis no prueba que se dibuje bien.
- SÍ dar a toda opción nueva su parámetro en clon/omnicad/api/, con test.
- NO commitear. NO hacer push.
- SÍ trabajar sobre los cambios sin commitear de main. NO pisarlos ni revertirlos.
- NO instalar paquetes.
- NO importar Qt en nucleo/, timeline/, restricciones/ ni io_archivos/.
- SÍ escribir todo en español.
- SÍ editar con Python en binario los archivos con finales de línea mixtos o CRLF y comparar git diff --numstat con --ignore-space-at-eol.
- NO correr la suite completa, la prueba de humo ni scripts/cierre_completo.sh: quedan para la noche.
- SÍ probar con eventos simulados al widget. NO mover el cursor real.

MANEJO DE ERRORES
- Paso 2: si una herramienta no se puede probar en la ventana, SALTAR Y CONTINUAR, marcándola con ⚠ y la causa.
- Paso 11: si un material no tiene fuente, SALTAR Y CONTINUAR con ese material y seguir con los demás.
- Paso 14: si falla un test lejano, tratarlo como regresión y arreglarlo antes de seguir.
- Default: PARAR Y REPORTAR.

CRITERIO DE ÉXITO
Las 15 herramientas figuran como «anda» en la auditoría, con prueba de ventana, números medidos y capturas miradas. Cada fila INS-n quedó borrada, o Parcial con lo que falta. ruff limpio, tests en verde y ponytail-review pegada.

SALIDA ESPERADA
Informe en español con: tabla de las 15 herramientas (antes y después), filas resueltas o parciales, fuentes de los factores de CO₂, firma de cada función pública nueva, comparación contra Fusion por panel, salida real de ruff y pytest, lo que queda para la noche y la salida de ponytail-review.

COMPORTAMIENTO DEL AGENTE
- Ejecutá las instrucciones literalmente. No parafrasees ni reinterpretes.
- Si falta una entrada marcada como REQUIRED, detenete y pedila. No continúes.
- No agregues contenido que no sea derivable de las entradas.
- No asumas intención más allá de lo explícitamente declarado.
- Mantené estructura idéntica en todos los outputs.
- Priorizá precisión sobre velocidad.
- Si un paso falla, seguí la regla de MANEJO DE ERRORES correspondiente.
```
