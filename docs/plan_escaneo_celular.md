# Escanear una pieza con el celular

Filmar una pieza con el celular y recibir en OmniCAD una pieza limpia y paramétrica. El celular captura, OmniCAD arma la malla
y [Reconstruir sólido](plan_reconstruir_solido.md) la convierte en una pieza con timeline.

**Upgrade a futuro:** no se empieza hasta que Gerardo lo pida. Cuando lo pida, se usa el prompt del final.

Estado por fila en `docs/seguimiento/faltantes.md` (ESC-1 a ESC-7). Revisado el 2026-11-01. No hay prototipo ni pruebas propias.

## Se puede, con límites

| Camino | Estado | Sirve para |
|---|---|---|
| **App gratis en el celular** y exportar OBJ, STL o PLY | Existe hoy | Empezar sin programar |
| **Video o fotos procesados en la PC** | Posible; falta medir en esta PC | Tenerlo dentro de OmniCAD, sin nube |
| **Escáner de luz estructurada** | Mejor precisión | No es el pedido; queda como referencia |

**Precisión.** Depende más de cómo se captura que del celular. Una comparación industrial contra máquina de medir dio
0,040 mm con marcadores, 0,231 mm con una estrategia sin marcadores y 1,721 mm con otra afectada por cambios de foco. Son
promedios con cámaras y método controlados, no resultados de celular.
Fuente: [3D Mag, 2026](https://www.3dmag.com/3d-scanners/how-accurate-is-photogrammetry/).

**Lo que manda:** marcadores, foco fijo, buena luz y medir contra un calibre. Por eso el primer paso es una prueba real.

## Lo que el celular no resuelve

| Problema | Respuesta |
|---|---|
| Escala: una cámara sola no sabe cuánto mide algo | Hoja impresa con marcadores, o una medida con calibre |
| Piezas brillantes, negras, transparentes o de un solo color | Luz difusa y spray opaco. KIRI ofrece un modo para esto, en su plan Pro |
| Lo que la cámara no vio: abajo, adentro, huecos profundos | Dos pasadas con la pieza dada vuelta; lo oculto no se inventa |
| Roscas y detalles chicos | Se reconocen por su medida y se modelan, no se copian de la malla |

**La IA no agrega precisión que el video no tiene.** Decide la intención: 19,7 mm es un agujero de 20, y esto es un M6. Las
medidas críticas las confirma una persona con calibre.

## Herramientas revisadas

| Herramienta | Decisión | Por qué |
|---|---|---|
| KIRI Engine, RealityScan, Scaniverse, Polycam | **Usar para empezar** | Apps gratuitas para capturar. Exportación según app y plan: [comparación](https://www.3dmag.com/3d-scanners/best-3d-scanning-apps/) |
| [COLMAP](https://colmap.github.io/license.html) | **Primer candidato** | Licencia BSD y corre también en CPU |
| [OpenMVS](https://github.com/cdcseacave/openMVS) | **Candidato para la malla** | AGPL-3.0: solo como programa aparte; confirmar compatibilidad y rendimiento sin CUDA |
| [Meshroom](https://github.com/alicevision/meshroom/releases) | **Descartado** | Sin GPU NVIDIA solo hace Draft Meshing, y esta PC tiene gráficos integrados |
| VGGT, DUSt3R y parecidos | **Descartados por ahora** | Sin escala real y pesos por defecto con restricciones: [listado](https://github.com/gmberton/awesome-3D-vision) |
| Servicio en la nube | **Descartado** | Cobra y saca la pieza de la PC |

## Cómo sería para el usuario

1. **Imprime** la hoja de escaneo desde OmniCAD y apoya la pieza encima.
2. **Filma** dando la vuelta completa, en tres alturas.
3. **Da vuelta** la pieza y filma de nuevo.
4. **Pasa el video** a la PC por cable, Drive o la vía que use.
5. **Abre** INSERTAR › Escanear pieza y elige el video o los archivos.
6. **OmniCAD avisa** si faltan ángulos o hay fotos movidas.
7. **Calcula** la malla y la lleva al tamaño real con la hoja.
8. **Pregunta** dos o tres medidas para confirmar con calibre.
9. **Reconstruir sólido** arma la pieza, con su mapa de desviación e informe.

## Decisiones

- **Primero se mide.** ESC-1 no lleva código y decide si conviene seguir.
- **Depende de Reconstruir sólido:** sin RI-2 solo se obtiene una malla.
- **Sin app propia para celular.** Dos apps nativas son otro proyecto; el celular filma con su cámara.
- **Sin servidor en la red por ahora.** Un QR exige abrir un puerto a la red local, y los servidores del proyecto escuchan solo
  en 127.0.0.1. Queda para ESC-7.
- **Motor opcional.** Se descarga aparte y se corre como proceso separado: OmniCAD sigue liviano.
- **Local por defecto.** El video no sale de la PC. La IA recibe medidas e imágenes elegidas, y el panel lo avisa.
- **Video y archivos son entrada ajena:** tope de tamaño y duración, y validación antes de procesar.

## Fases

| Fase | Fila | Qué se hace | Terminada cuando |
|---|---|---|---|
| 1 · Prueba real | ESC-1 | 3 piezas conocidas con una app gratis, sin código | Tabla de error contra calibre; se decide si sigue |
| 2 · Importar | ESC-2 | Abrir el escaneo, quitar el fondo y dar escala con una medida | Un escaneo llega a RI-2 en tamaño real |
| 3 · Hoja | ESC-3 | PDF con marcadores y detección automática de escala | Mide una pieza conocida dentro de lo medido en ESC-1 |
| 4 · Video | ESC-4 | Elegir cuadros nítidos, avisar faltantes y juntar dos pasadas | Rechaza un video movido y explica por qué |
| 5 · Motor | ESC-5 | Video a malla en la PC, en proceso aparte | Tiempo y memoria medidos en esta PC |
| 6 · IA | ESC-6 | Guía de captura, medidas para confirmar y redondeo | Mejora el error del banco contra ESC-1 |
| 7 · Celular directo | ESC-7 | Pasar el video con QR, si se aprueba el cambio de seguridad | Con token, solo por pedido y con cierre solo |

## Metas propuestas

Para ajustar con ESC-1.

| Medida | Meta |
|---|---|
| Error general | Hasta 0,5 mm en piezas de 20 a 200 mm con hoja de marcadores |
| Medida confirmada con calibre | Queda igual a la medida del calibre |
| Tiempo | Hasta 30 minutos por video en esta PC |
| Memoria | Dentro del tope de `scripts/turno.py`; si no entra, el motor no se aprueba para esta PC |
| Pieza final | Metas de Reconstruir sólido |

## Prompt para el agente

Modelo sugerido el 2026-11-01: Opus 5, esfuerzo alto. Antes de usarlo, revisar que los IDs y las rutas sigan vigentes.

```text
ARRIBA DE TODO, ANTES DE TOCAR NADA
Invocá con la herramienta Skill: fable-method, ponytail, plan-then-do, tool-calling-guard, verify-before-commit y omnicad-test.
Antes de cerrar, invocá ponytail-review con la herramienta Skill y pegá su salida real en el informe.

OBJETIVO
Construir Escanear pieza: de archivos o video del celular a una malla en tamaño real, lista para Reconstruir sólido.

CONTEXTO DEL AGENTE
- Plataforma: Claude Code en D:\PROGRAMA, sobre main.
- Herramientas: archivos, Bash, Python del venv en clon/.venv, pytest, ruff, MCP de OmniCAD, scripts/turno.py y scripts/prueba_ui/.
- Reglas del proyecto: CLAUDE.md y AGENTS.md. Otros agentes pueden estar trabajando en la misma carpeta.

TAREA PRINCIPAL
Cerrar ESC-2 a ESC-5 con su herramienta en la API, respetando el resultado de la prueba real de ESC-1.

ENTRADAS
- Plan: docs/plan_escaneo_celular.md → [PROVIDED]
- Plan previo: docs/plan_reconstruir_solido.md → [PROVIDED]
- Filas: docs/seguimiento/faltantes.md (ESC-1 a ESC-7, RI-2) → [PROVIDED]
- Código de partida: api/herramientas_documento.py (insert_file), api/herramientas_malla.py (scale_mesh y reparación), nucleo/malla.py, io_archivos/pdf_salida.py, nucleo/aislado.py → [PROVIDED]
- Resultado de ESC-1: tabla de error contra calibre → [REQUIRED FROM USER]
- Permiso para instalar paquetes y descargar el motor → [REQUIRED FROM USER]
- Licencias y compatibilidad de COLMAP, OpenMVS y sus dependencias con GPL-3.0 → [TO BE DISCOVERED BY AGENT]

PROCESO
1. Comprobar en el código y en seguimiento que RI-2 esté cerrado y que ESC-1 tenga su tabla. Terminar con la lista de lo que falta.
2. Leer el plan y el código de ENTRADAS hasta poder citar qué existe y qué falta. [REQUIERE: paso 1]
3. ESC-2: crear el comando INSERTAR › Escanear pieza con OBJ, STL, PLY y GLB. Agregar quitar fondo y escalar con una medida. Terminar cuando un escaneo llegue a Reconstruir sólido en tamaño real. [REQUIERE: paso 2]
4. ESC-3: crear el PDF de la hoja de escaneo y la detección de sus marcadores. Terminar cuando mida una pieza conocida dentro del error de ESC-1. [REQUIERE: paso 3]
5. ESC-4: abrir video y fotos, elegir cuadros nítidos, avisar faltantes y juntar dos pasadas. Terminar cuando rechace un video movido y explique por qué. [REQUIERE: paso 3]
6. ESC-5: probar el motor local en un proceso aparte y medir tiempo y memoria en esta PC. Terminar con una tabla que apruebe o rechace el motor contra las metas del plan. [REQUIERE: paso 5]
7. Dar a cada función su herramienta en clon/omnicad/api/ y regenerar docs/agentes/herramientas.md.
8. Agregar tests con resultado numérico y una pieza de ventana con clics, teclado, Cancelar, Aceptar y deshacer. Probar archivos enormes, vacíos y dañados.
9. Correr ruff, los tests tocados con scripts/turno.py y la pieza con la ventana minimizada. Mirar las capturas.
10. Borrar de docs/seguimiento/ las filas cerradas, anotar en PROJECT_LOG.md cada ID con su prueba, y actualizar la lista nocturna y la hoja de ruta de los dos README.
11. Invocar ponytail-review con la herramienta Skill y corregir lo que encuentre.

DEPENDENCIAS
- 1 va antes de todo.
- 3 va antes de 4 y 5; 5 va antes de 6.
- 7 a 11 van después de los arreglos.

REGLAS
- SÍ tratar video, fotos y mallas como archivos ajenos, con tope de tamaño y duración.
- SÍ correr el motor como programa aparte y descarga opcional.
- SÍ mostrar lo que falta en la captura y lo que no se pudo medir.
- SÍ mantener todo local: el video no sale de la PC.
- SÍ mantener funciones puras en nucleo/, sin Qt.
- NO hacer ESC-6 ni ESC-7: son otra etapa.
- NO crear una app de celular ni un servidor en la red local.
- NO usar servicios en la nube ni APIs pagas.
- NO usar Meshroom ni modelos con licencia no comercial.
- NO empaquetar programas AGPL dentro de OmniCAD.
- NO instalar paquetes ni descargar el motor sin permiso de Gerardo.
- NO correr el cierre completo ni la suite entera: va de noche, cuando Gerardo lo diga.
- NO hacer commit ni push sin que Gerardo lo pida.
- NO tocar archivos ajenos a estas filas. Si hace falta, anotarlo en el informe.

MANEJO DE ERRORES
- Paso 1: PARAR Y REPORTAR si RI-2 sigue abierto o falta la tabla de ESC-1.
- Paso 6: PARAR Y REPORTAR si el motor no entra en la memoria de esta PC, o si Gerardo no dio permiso.
- Paso 9: PARAR Y REPORTAR con la salida real si algo sigue rojo después de 2 intentos.
- Default: PARAR Y REPORTAR.

CRITERIO DE ÉXITO
- Un escaneo de celular llega a Reconstruir sólido en tamaño real.
- La hoja de escaneo da la escala.
- Un video malo se rechaza con una explicación clara.
- La tabla del motor dice si sirve en esta PC.
- MCP, CLI y docs generadas quedan completos.
- ruff, tests tocados y pieza de ventana están en verde, con capturas revisadas.
- La salida real de ponytail-review está pegada en el informe.

SALIDA ESPERADA
Informe en español, corto:
- Tabla: ID, cerrado o abierto, prueba que lo cubre.
- Error medido por pieza, tiempo y memoria.
- Firma de cada función pública nueva y qué hace.
- Salida real de ruff, pytest, la pieza de ventana y ponytail-review.
- Una línea con ⚠ por cada riesgo real.
- Una línea sobre si el modelo alcanzó.

COMPORTAMIENTO DEL AGENTE
- Ejecutá las instrucciones literalmente. No parafrasees ni reinterpretes.
- Si falta una entrada marcada como REQUIRED, detenete y pedila. No continúes.
- No agregues contenido que no sea derivable de las entradas.
- No asumas intención más allá de lo explícitamente declarado.
- Priorizá precisión sobre velocidad.
- Si un paso falla, seguí la regla de MANEJO DE ERRORES correspondiente.
```
