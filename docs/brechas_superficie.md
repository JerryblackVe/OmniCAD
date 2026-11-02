# SUPERFICIE: capturas de Fusion contra OmniCAD

Especificación de SUP-27 a SUP-31. El estado vive solo en `docs/seguimiento/`.

**Fuentes:** 88 capturas de `analisis/capturas_fusion (solo quedan las pendientes; ver su INDICE.md)`, los artículos de `fusion-patch` y una
prueba por API. Se comparó el 2026-11-01 contra los campos reales de cada comando.

**Límites:** no se probó en la ventana. La ayuda de Empalme y Chaflán de superficie no trae opciones: salen de las capturas.

## Estado por herramienta

| Herramienta | Estado | Qué falta |
|---|---|---|
| Extruir · Revolución | Casi | Encadenado (SUP-29) y Proyectar eje encendido (SUP-30) |
| Barrido · Solevación | Completos en campos | Comprobar en la ventana |
| Superficie de contorno | Casi | Nombre, encadenado y Agrupar apagado por defecto |
| Reglada · Desfase | Casi | Selección de cadena (SUP-29) |
| Patrones · Simetría · Engrosar | Completos | Sumarlos a la cinta (SUP-27) |
| Llenado de contorno · Origen de la unión | Completos | Sumarlos a la cinta (SUP-27) |
| Empalme · Chaflán | **Muy reducidos** | SUP-28 |
| Recortar · Dividir cara · Dividir cuerpo | Completos | Nada |
| Anular recorte · Alargar | Casi | Nombres, orden y valores por defecto |
| Coser | **A medias** | SUP-29 y SUP-31 |
| Descoser | Casi | Un solo campo y cadena (SUP-29) |
| Escala · Mover/copiar · Alinear | Completos | Nada |
| Material físico · Aspecto · Navegador | **A medias** | P-25d y SUP-30 |
| Crear forma | No existe | Bloqueado por RH19 |

OmniCAD suma Caja, Cilindro, Esfera, Toroide, Bobina, Tubería, Cara de desfase y Reemplazar cara. Se quedan.

## SUP-27 · Cinta

**CREAR:** Crear boceto · Crear forma · Derivar · Extruir · Revolución · Barrido · Solevación · Superficie de contorno · Reglada ·
Desfase · Patrón (rectangular, circular, sobre ruta) · Simetría · Engrosar (Mayús+C) · Llenado de contorno · Origen de la unión.

**MODIFICAR:** Pulsar/Tirar (Q) · Empalme (F) · Chaflán (Ctrl+\) · Recortar · Anular recorte · Alargar · Coser · Descoser · Invertir la
normal · Escala · Dividir cara · Dividir cuerpo · Mover/copiar (M) · Alinear (Alt+Mayús+A) · Suprimir · Quitar · Material físico · Aspecto (A) ·
Administrar materiales · Cambiar parámetros · Calcular todo (Ctrl+B) · Lista de materiales.

Renombrar en pantalla: Parche → Superficie de contorno · Destrimar → Anular recorte · Extender → Alargar · Invertir normal → Invertir la
normal. Los nombres de la API no cambian.

## SUP-28 · Empalme y Chaflán de superficie

Hoy `sup_empalme` tiene Aristas, Tipo y Radio, y `fillet_surface` solo acepta tamaño y tipo.

| Comando | Fila | Control |
|---|---|---|
| Empalme | Tipo | Empalme · Empalme estándar · Empalme redondo completo |
| Empalme | Lista | Aristas elegidas, con + y × |
| Empalme | Tipo de radio | Constante · Longitud de cuerda · Variable · Asimétrico |
| Empalme | Selección | Aristas/caras/operaciones · Cadena tangente encendida |
| Empalme | Tipo de esquina | Empalme curvo bitangente · Esquina plana |
| Chaflán | Lista · Tipo | Distancia igual · Dos distancias · Distancia y ángulo |
| Chaflán | Selección | Aristas/caras/operaciones · Cadena tangente encendida |
| Chaflán | Tipo de esquina | Chaflán · Bisel · Fusión |

`empalme_3d` y `chaflan_3d` ya tienen casi todo: se reutiliza lo que sirva para superficies. Comprobar en Fusion qué opciones actúan
sobre una superficie abierta. En Chaflán, Inglete y Mezcla pasan a llamarse Bisel y Fusión.

## SUP-29 · Encadenado y selección

| Comando | Control | Por defecto |
|---|---|---|
| Extruir · Revolución | Encadenando | Encendido |
| Superficie de contorno | Activar el encadenado | Encendido |
| Reglada · Desfase · Descoser | Selección de cadena | Encendido |
| Alargar | Cadena tangente | Encendido |

Descoser usa un solo campo: Caras o cuerpos.

## SUP-30 · Valores por defecto y material

- Superficie de contorno: Agrupar las aristas apagado. Comprobar antes que no cambie recetas guardadas.
- Revolución: Eje de proyecto encendido.
- Anular recorte: Todas las aristas primero y por defecto; orden Todas · Internas · Externas · Manual.
- Alargar: orden Natural · Perpendicular · Tangente. Alineación Aristas sueltas · Alinear aristas (junto con SUP-17).
- Dividir cara: A lo largo del vector.
- Material físico y Aspecto: panel con En este diseño y Biblioteca con carpetas y búsqueda. Aspecto suma Aplicar a,
  y las pestañas Aspectos de Fusion, Mis aspectos y Favoritos.
- Administrar materiales abre el Navegador con Propiedades físicas y Aspecto (P-25d).

## SUP-31 · Coser

- Tolerancia por defecto 0,10 mm con deslizador. Hoy es 0,01 mm.
- Sección Resultado del cosido.
- Tabla Aristas no cosidas: Arista y Separación máxima, con Buscar arista en la ventana y Establecer la separación máxima como tolerancia.
- Aristas dentro de tolerancia en verde.

Medido por API: dos superficies a 0,05 mm, con la tolerancia por defecto, responden ok con 0 aristas cosidas y 8 bordes libres.
Comprobar en Fusion qué hace si nada queda cosido.


## Prompt para el agente

Modelo sugerido el 2026-11-01: Opus 5, esfuerzo alto. Antes de usarlo, revisar que los IDs y las rutas sigan vigentes.

```text
ARRIBA DE TODO, ANTES DE TOCAR NADA
Invocá con la herramienta Skill: fable-method, ponytail, plan-then-do, tool-calling-guard, verify-before-commit y omnicad-test.
Antes de cerrar, invocá ponytail-review con la herramienta Skill y pegá su salida real en el informe.

OBJETIVO
Dejar la pestaña SUPERFICIE igual a las capturas de Fusion.

CONTEXTO DEL AGENTE
- Plataforma: Claude Code en D:\PROGRAMA, sobre main.
- Herramientas: archivos, Bash, Python del venv en clon/.venv, pytest, ruff, MCP de OmniCAD, MCP de Fusion 360, scripts/fusion_docs.py, scripts/turno.py y scripts/prueba_ui/.
- Reglas del proyecto: CLAUDE.md y AGENTS.md. Otros agentes pueden estar trabajando en la misma carpeta.

TAREA PRINCIPAL
Cerrar SUP-27 a SUP-31, con su herramienta en la API, sus tests y prueba como usuario.

ENTRADAS
- Especificación: docs/brechas_superficie.md → [PROVIDED]
- Capturas: analisis/capturas_fusion (solo quedan las pendientes; ver su INDICE.md)→ [PROVIDED]
- Filas: docs/seguimiento/faltantes.md y mejoras.md (SUP-13, SUP-14, SUP-17, SUP-27 a SUP-31, P-25d) → [PROVIDED]
- Ayuda: docs/fusion_docs/contenido/fusion-patch y scripts/fusion_docs.py → [PROVIDED]
- Código: ui/cinta.py, ui/comandos/superficie*.py, ui/comandos/solido.py, api/herramientas_superficie*.py → [TO BE DISCOVERED BY AGENT]
- Respuestas de Fusion real en lo marcado para comprobar → [TO BE DISCOVERED BY AGENT]

PROCESO
1. Leer la especificación, las capturas, los artículos y el código de ENTRADAS hasta poder citar qué pide cada fila.
2. Comparar en Fusion real lo marcado para comprobar. Abrir Fusion si está cerrado, usar un documento temporal, cerrarlo sin guardar y cerrar Fusion si lo abriste vos. [REQUIERE: paso 1]
3. SUP-27: ordenar la cinta y los nombres. Terminar cuando cada ítem de las capturas abra su comando, salvo Crear forma, que sigue grisado.
4. SUP-28: completar Empalme y Chaflán de superficie, reutilizando empalme_3d y chaflan_3d. Terminar con volumen o área comprobados en cada opción que Fusion admita.
5. SUP-29: agregar el encadenado a cada comando de la tabla.
6. SUP-31: rehacer Coser con su tabla de aristas y el mensaje cuando no se cose nada.
7. SUP-30: ajustar valores por defecto y paneles de material, sin cambiar recetas guardadas.
8. Dar a cada función su herramienta en clon/omnicad/api/ y regenerar docs/agentes/herramientas.md.
9. Agregar tests con resultado numérico y probar en la ventana como una persona: clics en la cinta y el visor, teclear valores, Enter, Esc, Tab, Aceptar, reabrir y deshacer, en 1024x640 y 800x520.
10. Correr ruff, los tests tocados con scripts/turno.py y la pieza con la ventana minimizada. Mirar las capturas y compararlas con las de Fusion.
11. Borrar de docs/seguimiento/ las filas cerradas, anotar en PROJECT_LOG.md cada ID con su prueba y actualizar docs/auditorias/prueba_nocturna_2026-10-31.md.
12. Invocar ponytail-review con la herramienta Skill y corregir lo que encuentre.

REGLAS
- NO hacer el espacio FORMA: sigue bloqueado por RH19.
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
- Cada captura tiene su control en OmniCAD, o una razón escrita.
- Coser avisa con claridad si nada queda cosido.
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
