# ANIMACIÓN: capturas de Fusion contra OmniCAD

Especificación de ANI-1 a ANI-5. El estado vive solo en `docs/seguimiento/`.

**Fuentes:** 15 capturas de `C:\Users\mosos\Desktop\DISEÑO FUSION 360\ANIMACION`, los artículos de `fusion-animate` y una prueba por API.
Se comparó el 2026-11-01.

**Límite:** no se probó en la ventana.

## Estado por herramienta

| Herramienta | Estado | Qué falta |
|---|---|---|
| Guiones gráficos: crear, copiar, invertir | Completo | Nada |
| Transformar componentes | Completo | Atajo M |
| Restablecer inicio | Completo | Nombre |
| Explosión automática: un nivel y todos | Casi | Barra de explosión: ANI-2 |
| Explosión manual | **Grisado** | ANI-2 |
| Mostrar/ocultar | Completo | Nada |
| Aspecto | **Grisado** | ANI-3 |
| Trayectorias | **Grisado** | ANI-3 |
| Crear llamada | Casi | ANI-4 |
| Vista | Completo | Atajo Ctrl+R |
| Publicar video | **Solo GIF y PNG** | B6 y B-145 |
| Navegador · Comentarios | **No existen** | ANI-1 |

## ANI-1 · Navegador y comentarios

El espacio de Fusion muestra Navegador (documento › Componentes) y Comentarios. Hoy la ventana tiene cinta, vista y línea de tiempo.

- Clic elige, ojo oculta y se abre desde ahí Transformar, por clic derecho.
- El panel de acciones sigue en la línea de tiempo.

## ANI-2 · Explosión

**Barra flotante:** deslizador Escala de explosión, Explosión en un paso, Explosión secuencial, ✓ y ×.

**Explosión manual (E):** elegir un componente y su eje, repetir por componente y usar la misma barra.

Falta su opción en API: `auto_explode` tiene escala y secuencia, pero no eje por componente.

## ANI-3 · Aspecto y trayectorias

**Aspecto:** Alcance entre todo el documento o el guion activo; se abre también por clic derecho. No cambia propiedades físicas.

**Trayectorias:** clic derecho › Visibilidad de trayectoria. Línea desde el centro actual del componente al centro de la posición inicial.

Las dos llevan herramienta en la API.

## ANI-4 · Llamada y detalles

- Crear llamada: alfiler, barra ✓ y ×, y caja de texto en el lienzo. Rojo sin pieza y verde sobre una pieza.
- Doble clic edita el texto.
- Nombres: Restablecer inicio · Crear llamada · Vista · Nuevo guion gráfico.
- Atajos: M · U · E · P · Ctrl+R.
- Línea de tiempo: comprobar contra la captura la regla, el zoom 1.0, las pestañas de guion con + y los botones de reproducción.

## ANI-5 · Prueba de animación

Sumar una pieza en `scripts/prueba_ui/` que arme un guion completo y lo publique. Nunca se listó una pieza de ANIMACIÓN.

## Publicar

MP4 sigue en B6, que pide permiso para ffmpeg. B-145: mientras tanto, pedir `.mp4` responde INTERNAL_ERROR en lugar de un mensaje claro.
Las opciones Alcance, Resolución y bloqueo de relación ya están en la ventana.


## Prompt para el agente

Modelo sugerido el 2026-11-01: Opus 5, esfuerzo alto. Antes de usarlo, revisar que los IDs y las rutas sigan vigentes.

```text
ARRIBA DE TODO, ANTES DE TOCAR NADA
Invocá con la herramienta Skill: fable-method, ponytail, plan-then-do, tool-calling-guard, verify-before-commit y omnicad-test.
Antes de cerrar, invocá ponytail-review con la herramienta Skill y pegá su salida real en el informe.

OBJETIVO
Dejar el espacio ANIMACIÓN igual a las capturas de Fusion.

CONTEXTO DEL AGENTE
- Plataforma: Claude Code en D:\PROGRAMA, sobre main.
- Herramientas: archivos, Bash, Python del venv en clon/.venv, pytest, ruff, MCP de OmniCAD, MCP de Fusion 360, scripts/fusion_docs.py, scripts/turno.py y scripts/prueba_ui/.
- Reglas del proyecto: CLAUDE.md y AGENTS.md. Otros agentes pueden estar trabajando en la misma carpeta.

TAREA PRINCIPAL
Cerrar ANI-1 a ANI-5 y B-145, con su herramienta en la API, sus tests y prueba como usuario.

ENTRADAS
- Especificación: docs/brechas_animacion.md → [PROVIDED]
- Capturas: C:\Users\mosos\Desktop\DISEÑO FUSION 360\ANIMACION → [PROVIDED]
- Filas: docs/seguimiento/faltantes.md y bugs.md (ANI-1 a ANI-5, B6, B-145) → [PROVIDED]
- Ayuda: docs/fusion_docs/contenido/fusion-animate y scripts/fusion_docs.py → [PROVIDED]
- Código: ui/animacion.py, nucleo/animacion.py, api/herramientas_animacion.py → [TO BE DISCOVERED BY AGENT]
- Respuestas de Fusion real en lo marcado para comprobar → [TO BE DISCOVERED BY AGENT]

PROCESO
1. Leer la especificación, las capturas, los artículos y el código de ENTRADAS hasta poder citar qué pide cada fila.
2. Comparar en Fusion real lo marcado para comprobar. Abrir Fusion si está cerrado, usar un documento temporal, cerrarlo sin guardar y cerrar Fusion si lo abriste vos. [REQUIERE: paso 1]
3. B-145: pedir un formato no admitido responde un error claro, con test.
4. ANI-1: agregar Navegador y Comentarios. Terminar cuando se pueda elegir, ocultar y transformar desde el Navegador.
5. ANI-2: agregar la barra de explosión y Explosión manual, con eje por componente.
6. ANI-3: agregar Aspecto y trayectorias, guardados en el guion.
7. ANI-4: completar llamada, nombres y atajos; comparar la línea de tiempo con la captura.
8. ANI-5: sumar la pieza de ANIMACIÓN a scripts/prueba_ui/todo.py.
9. Dar a cada función su herramienta en clon/omnicad/api/ y regenerar docs/agentes/herramientas.md.
10. Agregar tests con resultado numérico y probar en la ventana como una persona: clics en la cinta y el visor, teclear valores, Enter, Esc, Tab, Aceptar, reabrir y deshacer, en 1024x640 y 800x520.
11. Correr ruff, los tests tocados con scripts/turno.py y la pieza con la ventana minimizada. Mirar las capturas y compararlas con las de Fusion.
12. Borrar de docs/seguimiento/ las filas cerradas, anotar en PROJECT_LOG.md cada ID con su prueba y actualizar docs/auditorias/prueba_nocturna_2026-10-31.md.
13. Invocar ponytail-review con la herramienta Skill y corregir lo que encuentre.

REGLAS
- NO instalar ffmpeg sin permiso: MP4 sigue en B6.
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
- Un guion con explosión manual, aspecto, trayectoria y llamada se guarda, se reabre y se publica en GIF.
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
