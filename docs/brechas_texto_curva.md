# Texto en curva y extrusión del texto

Especificación de B-132 a B-137, TXT-8 y TXT-9. El estado vive solo en `docs/seguimiento/`.

**Fuente:** video `C:\Users\mosos\Videos\2026-11-01 08-06-01.mp4`, la ayuda de `fusion-sketch` y `fusion-model`, y una prueba por API.

**Límite:** en el video, las tres extrusiones terminan en Cancelar. No se comprobó en Fusion real si el texto parte otras curvas.

## Prompt para el agente

Entregado el 2026-11-01. Modelo sugerido: Opus 5, esfuerzo alto. Antes de usarlo, revisar que los IDs y las rutas sigan vigentes.

```text
ARRIBA DE TODO, ANTES DE TOCAR NADA
Invocá con la herramienta Skill: fable-method, ponytail, plan-then-do, tool-calling-guard, verify-before-commit y omnicad-test.
Antes de cerrar, invocá ponytail-review con la herramienta Skill y pegá su salida real en el informe.

OBJETIVO
Arreglar en OmniCAD el texto en curva y su extrusión: cerrar B-132, B-133, B-135, B-136, B-137, TXT-8 y TXT-9, y dejar B-134 resuelto o documentado.

CONTEXTO DEL AGENTE
- Plataforma: Claude Code en D:\PROGRAMA, sobre main.
- Herramientas: archivos, Bash, Python del venv en clon/.venv, pytest, ruff, MCP de OmniCAD, scripts/fusion_docs.py y scripts/prueba_ui/.
- Reglas del proyecto: CLAUDE.md y AGENTS.md. Otros agentes pueden estar trabajando en la misma carpeta.

TAREA PRINCIPAL
Corregir que un texto que toca o cruza otra curva se elija entero, se extruya bien y no deje perfiles basura. Corregir también los avisos y restos visuales de la ventana.

ENTRADAS
- Filas con el detalle: docs/seguimiento/bugs.md (B-132 a B-137), faltantes.md (TXT-8), mejoras.md (TXT-9) → [PROVIDED]
- Video: C:\Users\mosos\Videos\2026-11-01 08-06-01.mp4 → [PROVIDED]
- Ayuda de Fusion: docs/fusion_docs/, carpeta fusion-sketch: Reference: Text dialog, Create text in a sketch, Text in sketches. Carpeta fusion-model: Extrude reference → [PROVIDED]
- Código de partida: nucleo/perfiles.py:93 (letras_de_texto), ui/visor3d.py:1212 a 1273 (_huecos_texto, hits_texto), ui/ventana.py:975 a 982 y 1041, ui/comando.py (_cerrar), ui/editor_boceto.py:4982 y 5029, ui/modo_boceto.py (panel Carácter), api/herramientas_vectores.py → [PROVIDED]
- Confirmación de si en Fusion real el texto parte otras curvas → [REQUIRED FROM USER]
- Causa de B-136 → [TO BE DISCOVERED BY AGENT]

REPRODUCCIÓN (por API, antes de cambiar nada)
create_sketch(plane="XZ", name="b")
draw_circle(sketch="b", center_x=0, center_y=0, radius=57)
add_text(sketch="b", text="HOLA", font="Arial", height=30, path_entity=<id del círculo>, path_side="right", path_position=0.25)
get_sketch(sketch="b") y extrude(sketch="b", profile=i, distance=10) para cada perfil, con undo entre uno y otro.
Valores de hoy:
- 9 perfiles; con path_offset=2, 7 perfiles.
- Un perfil de área 0,0 responde ok con volumen 0.0.
- Un perfil de área 1,29 da volumen 12,9.
- Disco de área 10205,74 contra 10207,03 esperado; volumen 102057,4 contra 102070,3.

PROCESO
1. Leer los artículos de la ayuda y el código de ENTRADAS hasta poder citar qué pide Fusion en cada fila.
2. Reproducir por API los valores de arriba y por ventana, con eventos simulados, el arrastre y la selección del video. Terminar con un registro de cada falla. [REQUIERE: paso 1]
3. B-132: en nucleo/perfiles.py y ui/visor3d.py, reemplazar el filtro `set(p.firma) <= ids`, que descarta la L y el aro de la O por tocar el círculo y deja el hueco de la O como letra. Terminar cuando un clic en cualquier letra de HOLA elija las 4 letras con sus huecos vacíos, apoyado o no sobre el círculo. Revisar que hits_texto siga sin elegir huecos y que no rompa test_letras_de_texto_deja_afuera_los_huecos. [REQUIERE: paso 2]
4. B-133: filtrar los perfiles sin área real en la detección y rechazar en Extruir una extrusión de volumen 0 con un mensaje en español. Terminar cuando el perfil de área 0,0 no se liste y extrude nunca responda ok con volumen 0. [REQUIERE: paso 3]
5. B-134: probar en Fusion real si el texto parte otras curvas, usando el MCP fusion360 si conecta. Si no conecta, dejar la fila abierta con lo probado y no cambiar el comportamiento del disco. Si Fusion no parte el círculo, hacer que el disco conserve 10207,03 de área. [REQUIERE: paso 3]
6. B-135: limpiar «Calculando…» al terminar la vista previa y al cerrar el comando. Terminar cuando, al Cancelar, la barra vuelva al estado normal sin esperar 30 s.
7. B-136: encontrar qué ventana sin padre se muestra al abrir Extruir, corregirla y comprobar que no vuelve a aparecer.
8. B-137: repintar los rellenos mientras se desliza un texto en curva. Terminar cuando no quede sombra, el disco conserve el relleno y no quede una L oscura en la posición vieja. Confirmar la causa antes de cambiar código.
9. Comprobar por qué un clic en la L dio «Curva 4» (video, ~2:10). Si un clic dentro de la letra elige una curva en vez del perfil, corregirlo; si fue por tocar el borde, anotarlo en el informe.
10. TXT-8: con un campo de perfiles activo, elegir un boceto en el navegador o el timeline debe tomar todos sus perfiles, texto incluido, como dice Extrude reference. Agregar lo mismo a la API si falta.
11. TXT-9: cambiar en el panel Carácter a Arriba y Abajo y la separación a porcentaje, con recetas viejas que sigan abriendo. Comprobar por qué dice «Sin parámetro ligado» si Fusion crea Text y Text height solos. Probar Voltear, Ajustar a la curva y cambiar la curva después de crear el texto.
12. Dar a cada función nueva o cambiada su herramienta en clon/omnicad/api/ y regenerar docs/agentes/herramientas.md.
13. Agregar tests con resultado numérico en clon/tests/ y sumar la prueba como usuario a la pieza de boceto de scripts/prueba_ui/: texto sobre círculo, deslizar, elegir el texto, extruir, Cancelar, Aceptar, reabrir y deshacer.
14. Correr ruff, los tests tocados con scripts/turno.py y la pieza de ventana con la ventana minimizada. Mirar las capturas y compararlas con el video.
15. Borrar de docs/seguimiento/ las filas resueltas, anotar en el Registro de PROJECT_LOG.md cada ID con su prueba, actualizar docs/auditorias/prueba_nocturna_2026-10-31.md y anotar la lección si hubo un error verificable.
16. Invocar ponytail-review con la herramienta Skill y corregir lo que encuentre.

DEPENDENCIAS
- 3 va antes de 4, 5, 9 y 10.
- 6, 7, 8 y 11 no dependen entre sí.
- 12 a 16 van después de todos los arreglos.

REGLAS
- SÍ leer el artículo de la ayuda antes de cambiar cada comportamiento.
- SÍ hacer el cambio más chico que resuelve cada fila.
- SÍ probar como una persona: clics, arrastres y teclado con eventos simulados.
- SÍ escribir todo en español, con nombres de herramientas y parámetros de la API en inglés.
- SÍ mantener Qt solo en ui/.
- NO decir que Aceptar pierde la extrusión: en el video el cursor termina en Cancelar.
- NO cambiar el disco de B-134 sin una prueba en Fusion real o el OK de Gerardo.
- NO correr el cierre completo ni la suite entera: va de noche, cuando Gerardo lo diga.
- NO tocar archivos ajenos a estas filas. Si hace falta, anotarlo en el informe.
- NO hacer commit ni push sin que Gerardo lo pida.
- NO gastar en APIs pagas ni instalar paquetes sin permiso.
- NO usar `git add -f` ni subir privado/, analisis/ ni evidencias/.

MANEJO DE ERRORES
- Paso 2: PARAR Y REPORTAR si los valores no coinciden con los de REPRODUCCIÓN.
- Paso 5: SALTAR Y CONTINUAR si Fusion real no está disponible, dejando B-134 abierto.
- Paso 7: SALTAR Y CONTINUAR si la ventana no se reproduce tras 3 intentos, dejando la fila abierta con lo probado.
- Paso 14: PARAR Y REPORTAR con la salida real si algo sigue rojo después de 2 intentos de arreglo.
- Default: PARAR Y REPORTAR.

CRITERIO DE ÉXITO
- HOLA sobre el círculo se elige con un clic y extruye 4 letras separadas, con los huecos vacíos.
- Ningún perfil basura se lista y ninguna extrusión responde ok con volumen 0.
- Cancelar deja limpia la barra de estado.
- Deslizar el texto no deja sombra.
- Elegir un boceto en Extruir toma todo su contenido.
- ruff y los tests tocados están en verde, con la pieza de ventana corrida y las capturas revisadas.
- Seguimiento, PROJECT_LOG y lista nocturna quedan al día.
- La salida real de ponytail-review está pegada en el informe.

SALIDA ESPERADA
Informe en español, corto:
- Tabla: ID, cerrado o abierto, prueba que lo cubre.
- Firma de cada función pública nueva y qué hace.
- Salida real de ruff, pytest, la pieza de ventana y ponytail-review.
- Una línea con ⚠ por cada cosa no verificada.
- Una línea sobre si el modelo alcanzó.

COMPORTAMIENTO DEL AGENTE
- Ejecutá las instrucciones literalmente. No parafrasees ni reinterpretes.
- Si falta una entrada marcada como REQUIRED, seguí la regla del paso que la usa.
- No agregues contenido que no sea derivable de las entradas.
- No asumas intención más allá de lo explícitamente declarado.
- Priorizá precisión sobre velocidad.
- Si un paso falla, seguí la regla de MANEJO DE ERRORES correspondiente.
```
