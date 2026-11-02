# ENSAMBLAR: capturas de Fusion contra OmniCAD

Especificación de ASM-17 a ASM-20, y detalle de SC6 y P-25e2. El estado vive solo en `docs/seguimiento/`.

**Fuentes:** 26 capturas de `C:\Users\mosos\Desktop\DISEÑO FUSION 360\ENSAMBLAR`, los artículos de `fusion-assemble` y una prueba
por API. Se comparó el 2026-11-01.

**Límite:** no se probó en la ventana.

## Estado por herramienta

| Herramienta | Estado | Qué falta |
|---|---|---|
| Insertar componente | Existe | Pasarlo primero en el menú |
| Nuevo componente | **A medias** | ASM-18 |
| Duplicar con uniones | Existe | Comprobar en la ventana |
| Restricción de componentes | **No existe** | ASM-17 |
| Unión · Unión conforme a obra | Casi | Pestañas y nombres: ASM-19 |
| Grupo rígido | Casi | Incluir hijos encendido: ASM-19 |
| Relación de tangente | **No existe** | ASM-17 |
| Origen de la unión | Completo | Nada |
| Uniones de animación · Vínculo · Estudio | Existen | Nombre: ASM-19 |
| Conjuntos de contacto | **No existen** | SC6 y P-25e2 |

OmniCAD suma Fijar, Anclar, Editar posición inicial, Capturar posición y Revertir posición. Se quedan.

## ASM-17 · Restricción de componentes

Ayuda: `Constraints reference`, `Assembly Constraints` y `Constrain Components`. La ayuda aclara que Tangent reemplaza a Tangent
Relationship y que se recrea con All Faces, por eso va en una sola fila.

| Fila | Control |
|---|---|
| Tipo | Alinear · Ángulo · Centro · Tangente, con tooltips de las capturas |
| Componente 1 y 2 | Geometría: selección de caras, aristas o vértices |
| Referencia de ángulo | Solo Ángulo: arista o línea como eje |
| Todas las caras | Solo Tangente, encendida en la captura |
| Tabla | Nombre · Tipo · Geometría · Desfase · Cambiar, con + y × |
| Geometría de la tabla | `Sin definir`, o el par elegido, como Cara-Arista |
| Límites de desfase | Mínimo, Máximo y Utilizar desfase como apoyo |
| Vista preliminar al pasar el cursor | Casilla |
| Resolver todas las restricciones | Casilla encendida |

Crea un paso del timeline, reduce grados de libertad y convive con uniones. Hace falta un resolvedor con las uniones ya existentes.
Tiene que decir cuándo hay un conflicto. Va con herramienta en la API.

## ASM-18 · Nuevo componente

| Fila | Control |
|---|---|
| Padre | Selección, con el nombre debajo |
| Externo | Casilla |
| Tipo de diseño | Pieza · Ensamblaje · Híbrido · PCB; solo con Externo |
| Tipo de componente | Estándar · Chapa |
| Nombre del componente | Componente1 |
| A partir de cuerpos | Casilla apagada |
| Activar | Casilla encendida |

Hoy no se puede crear un componente vacío: `create_component` exige cuerpos. Activar depende de ASM-9. Externo crea otro archivo:
decidir el alcance al programarlo.

## ASM-19 · Menú y paneles

**Menú:** Insertar componente · Nuevo componente · Duplicar con uniones · Restricción de componentes · Unión (J) · Unión conforme a obra
(Mayús+J) · Grupo rígido · Relación de tangente · Origen de la unión · Uniones de animación · Vínculo de movimiento · Estudio de
movimiento · Activar conjuntos de contactos · Activar todos los contactos.

**Nombres de movimiento:** Rígida · Revolución · Corredera · Cilíndrica · Polo-ranura · Plana · Bola.

**Unión:** pestañas Posición y Movimiento. Componente 1 y 2 plegables, con Modo de origen en tres botones y Forzar.

**Unión conforme a obra:** Componentes y Movimiento › Tipo.

**Grupo rígido:** Incluir componentes hijo encendido.

## ASM-20 · Estado de los paneles

`create_joint` y los paneles de unión tienen muchos campos sueltos. Revisar que respeten el orden de la captura y el `visible_si`.

## Conjuntos de contacto: detalle de SC6 y P-25e2

- Navegador: nodo Contacto: conjuntos, con botones.
- Comandos: Activar conjuntos de contactos · Activar todos los contactos · Desactivar contacto · Nuevo conjunto de contactos.
- Los componentes no se atraviesan al moverse. Es más lento que una unión: necesita medir rendimiento.


## Prompt para el agente

Modelo sugerido el 2026-11-01: Opus 5, esfuerzo alto. Antes de usarlo, revisar que los IDs y las rutas sigan vigentes.

```text
ARRIBA DE TODO, ANTES DE TOCAR NADA
Invocá con la herramienta Skill: fable-method, ponytail, plan-then-do, tool-calling-guard, verify-before-commit y omnicad-test.
Antes de cerrar, invocá ponytail-review con la herramienta Skill y pegá su salida real en el informe.

OBJETIVO
Dejar ENSAMBLAR igual a las capturas de Fusion, con Restricción de componentes.

CONTEXTO DEL AGENTE
- Plataforma: Claude Code en D:\PROGRAMA, sobre main.
- Herramientas: archivos, Bash, Python del venv en clon/.venv, pytest, ruff, MCP de OmniCAD, MCP de Fusion 360, scripts/fusion_docs.py, scripts/turno.py y scripts/prueba_ui/.
- Reglas del proyecto: CLAUDE.md y AGENTS.md. Otros agentes pueden estar trabajando en la misma carpeta.

TAREA PRINCIPAL
Cerrar ASM-17 a ASM-20, con su herramienta en la API, sus tests y prueba como usuario.

ENTRADAS
- Especificación: docs/brechas_ensamblar.md → [PROVIDED]
- Capturas: C:\Users\mosos\Desktop\DISEÑO FUSION 360\ENSAMBLAR → [PROVIDED]
- Filas: docs/seguimiento/faltantes.md (ASM-9, ASM-16 a ASM-20, SC6, P-25e2) → [PROVIDED]
- Ayuda: docs/fusion_docs/contenido/fusion-assemble y scripts/fusion_docs.py → [PROVIDED]
- Código: ui/comandos/ensamblar.py, ui/cinta.py, api/herramientas_ensamble.py, timeline/ops_*.py → [TO BE DISCOVERED BY AGENT]
- Alcance de los componentes externos → [REQUIRED FROM USER]
- Respuestas de Fusion real en lo marcado para comprobar → [TO BE DISCOVERED BY AGENT]

PROCESO
1. Leer la especificación, las capturas, los artículos y el código de ENTRADAS hasta poder citar qué pide cada fila.
2. Comparar en Fusion real lo marcado para comprobar. Abrir Fusion si está cerrado, usar un documento temporal, cerrarlo sin guardar y cerrar Fusion si lo abriste vos. [REQUIERE: paso 1]
3. ASM-19: ordenar menú, nombres y paneles. Terminar cuando Unión tenga sus dos pestañas.
4. ASM-18: permitir el componente vacío y los campos de la captura. Dejar Externo para el final y pedir el alcance a Gerardo.
5. ASM-20: revisar orden y visibilidad de los campos de Unión.
6. ASM-17: diseñar y anotar en la especificación cómo se resuelven juntas restricciones y uniones. Después programar los 4 tipos, con su paso, conflictos y límites.
7. SC6 y P-25e2: medir primero el costo del contacto; programarlo solo si entra en la meta que acuerdes con Gerardo.
8. Dar a cada función su herramienta en clon/omnicad/api/ y regenerar docs/agentes/herramientas.md.
9. Agregar tests con resultado numérico y probar en la ventana como una persona: clics en la cinta y el visor, teclear valores, Enter, Esc, Tab, Aceptar, reabrir y deshacer, en 1024x640 y 800x520.
10. Correr ruff, los tests tocados con scripts/turno.py y la pieza con la ventana minimizada. Mirar las capturas y compararlas con las de Fusion.
11. Borrar de docs/seguimiento/ las filas cerradas, anotar en PROJECT_LOG.md cada ID con su prueba y actualizar docs/auditorias/prueba_nocturna_2026-10-31.md.
12. Invocar ponytail-review con la herramienta Skill y corregir lo que encuentre.

REGLAS
- SÍ decir con un mensaje claro cuándo dos restricciones se contradicen.
- NO romper uniones existentes.
- SÍ leer el artículo de Fusion antes de cambiar cada comportamiento.
- SÍ hacer el cambio más chico que resuelve cada fila.
- SÍ mantener Qt solo en ui/.
- SÍ conservar las recetas guardadas y los nombres de la API.
- NO correr el cierre completo ni la suite entera: va de noche, cuando Gerardo lo diga.
- NO hacer commit ni push sin que Gerardo lo pida.
- NO gastar en APIs pagas ni instalar paquetes sin permiso.
- NO guardar documentos en Fusion ni tocar D:\Autodesk.
- NO tocar archivos ajenos a estas filas. Si hace falta, anotarlo en el informe.

MANEJO DE ERRORES
- Paso 2: SALTAR Y CONTINUAR con la ayuda y las capturas si Fusion no se puede usar, marcando con ⚠ cada dato sin confirmar.
- Si una receta vieja cambia de resultado: PARAR Y REPORTAR.
- Si algo sigue rojo después de 2 intentos: PARAR Y REPORTAR con la salida real.
- Default: PARAR Y REPORTAR.

CRITERIO DE ÉXITO
- Las 4 restricciones posicionan componentes con resultado medido.
- Un componente vacío se crea y recibe un cuerpo después.
- MCP, CLI y docs generadas quedan completos.
- ruff, tests tocados y prueba de ventana están en verde, con capturas revisadas.
- La salida real de ponytail-review está pegada en el informe.

SALIDA ESPERADA
Informe en español, corto:
- Tabla: ID, cerrado o abierto, prueba que lo cubre.
- Firma de cada función pública nueva y qué hace.
- Tabla corta de lo que respondió Fusion real.
- Salida real de ruff, pytest, la pieza de ventana y ponytail-review.
- Una línea con ⚠ por cada riesgo real.
- Una línea sobre si el modelo alcanzó.

COMPORTAMIENTO DEL AGENTE
- Ejecutá las instrucciones literalmente. No parafrasees ni reinterpretes.
- No agregues contenido que no sea derivable de las entradas.
- No asumas intención más allá de lo explícitamente declarado.
- Priorizá precisión sobre velocidad.
- Si un paso falla, seguí la regla de MANEJO DE ERRORES correspondiente.
```
