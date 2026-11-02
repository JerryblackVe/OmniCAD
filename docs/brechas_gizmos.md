# Asas de la ventana: que se vean y se entiendan

Especificación de H-60. El estado vive solo en `docs/seguimiento/`.

## Qué pasa

Gerardo lo vio el 2026-11-01 en Análisis de sección, con Plano XZ:

- La flecha queda como una mancha azul chica, porque apunta casi hacia la cámara.
- Las cajas de valor `0 mm` y `0 deg` caen encima del asa.
- No se entiende qué se arrastra ni para qué.

**Referencia pedida:** la tríada de Mover, con ejes de colores, arcos de giro, cuadrados de plano y punto central, bien definida
y sin nada encima.

Sospecha sin medir: puede pasar igual en otros comandos que usan `Flecha`, `Angulo` o `Posicion`.

## Dónde está

- `clon/omnicad/ui/manipuladores.py`: `Flecha`, `Angulo`, `Posicion`, `AsaRadial`, `Triada`, `CajaValor`, `GestorManipuladores`.
- `clon/omnicad/ui/comandos/asas_extra.py` y `comandos/modificar.py`: los que ya usan `Triada`.
- `clon/omnicad/ui/comandos/`: unos 25 comandos definen `manipuladores`.

## Prompt para el agente

Entregado el 2026-11-01. Modelo sugerido: Sol en OpenCode, esfuerzo alto. Comando: `openai/gpt-6.1-sol --variant high`. Se lanza después de los commits del cierre y de B-155.

```text
ARRIBA DE TODO, ANTES DE TOCAR NADA
Invocá /fable-method y /ponytail. Usá plan-then-do, tool-calling-guard, verify-before-commit y omnicad-test.
Antes de cerrar, invocá /ponytail-review y pegá en el informe su salida completa, escrita por vos.

OBJETIVO
Hacer que las asas de todos los comandos se vean bien definidas, sin nada encima, con la tríada de Mover como referencia: cerrar H-60.

CONTEXTO DEL AGENTE
- Plataforma: OpenCode en D:\PROGRAMA, sobre main.
- Herramientas: archivos, Bash, Python del venv en clon/.venv, pytest, ruff, scripts/turno.py, scripts/prueba_ui/ y scripts/fusion_docs.py.
- Reglas del proyecto: CLAUDE.md y AGENTS.md.

TAREA PRINCIPAL
Auditar con capturas el asa de cada comando, corregir lo común en manipuladores.py y dejar Análisis de sección como la tríada.

ENTRADAS
- Especificación: docs/brechas_gizmos.md → [PROVIDED]
- Código: clon/omnicad/ui/manipuladores.py, clon/omnicad/ui/comandos/asas_extra.py, clon/omnicad/ui/comandos/modificar.py, clon/omnicad/ui/comandos/inspeccionar.py → [PROVIDED]
- Pieza de partida: scripts/prueba_ui/asas.py → [PROVIDED]
- Ayuda de Fusion: clon/.venv/Scripts/python.exe scripts/fusion_docs.py buscar section analysis -s fusion-model → [PROVIDED]
- Lista de comandos con asas → [TO BE DISCOVERED BY AGENT]

PROCESO
1. Correr git status y confirmar que manipuladores.py, asas_extra.py e inspeccionar.py no tienen cambios sin commitear.
2. Leer la especificación, el artículo de Fusion y el código hasta poder explicar por qué la flecha de Sección se ve como una mancha. [REQUIERE: paso 1]
3. Listar cada comando que define manipuladores y qué asas usa. [REQUIERE: paso 2]
4. Sacar una captura de cada comando en 4 vistas: de frente al eje, de costado, iso y con la cámara alineada al asa. Escribir docs/auditorias/asas_2026-11-01.md con una tabla: comando, se ve bien / a medias / mal, evidencia. [REQUIERE: paso 3]
5. Corregir en manipuladores.py lo común: largo mínimo visible en pantalla aunque el eje apunte a la cámara, dibujo por encima del modelo y de la grilla, y contorno que separe el asa del fondo. Terminar cuando la captura con la cámara alineada muestre un asa reconocible. [REQUIERE: paso 4]
6. Hacer que ninguna CajaValor tape su asa ni otra caja. Terminar cuando un test mida que los rectángulos en pantalla no se solapan en las 4 vistas. [REQUIERE: paso 5]
7. Dejar Análisis de sección con la tríada de Mover: arrastrar eje mueve Distancia, y arrastrar arco gira Ángulo. Sumar lo que corresponda según la ayuda. Comparar la captura contra la tríada de Mover y decir en una línea qué se parece y qué no. [REQUIERE: paso 6]
8. Corregir cada comando marcado a medias o mal en el paso 4. [REQUIERE: paso 7]
9. Repetir las capturas del paso 4, mirarlas y actualizar la tabla. [REQUIERE: paso 8]
10. Probar con eventos simulados: arrastrar cada asa, pasar por cero, teclear en la caja al lado, Esc y deshacer, en 1024x640 y 800x520. Sumar lo que falte a scripts/prueba_ui/asas.py. [REQUIERE: paso 9]
11. Correr ruff, los tests tocados con scripts/turno.py, test_gizmo_construir, test_manipuladores y test_seguimiento, y las piezas asas e inspeccionar. [REQUIERE: paso 10]
12. Borrar H-60, anotar ID y prueba en el Registro de PROJECT_LOG.md y actualizar docs/auditorias/prueba_nocturna_2026-10-31.md. [REQUIERE: paso 11]
13. Invocar /ponytail-review y corregir lo que encuentre. [REQUIERE: paso 12]

REGLAS
- SÍ corregir primero lo común: un arreglo en manipuladores.py antes que uno por comando.
- SÍ mirar cada captura: un test verde no prueba que se vea bien.
- SÍ conservar los colores por eje de la tríada.
- SÍ probar con eventos simulados al widget.
- NO mover el cursor real.
- NO cambiar qué valor produce cada asa ni la API.
- NO importar Qt fuera de ui/.
- NO instalar paquetes.
- NO correr la suite completa ni la prueba de humo.
- NO hacer commit ni push.
- SÍ correr de a un comando pesado con scripts/turno.py: la PC tiene 13 GB. todo.py va sin turno.py.

MANEJO DE ERRORES
- Paso 1: PARAR Y REPORTAR si alguno de esos archivos tiene cambios sin commitear.
- Paso 4: SALTAR Y CONTINUAR si un comando no se puede abrir, marcándolo con ⚠ y la causa.
- Paso 11: PARAR Y REPORTAR con la salida real si algo sigue rojo después de 2 intentos.
- Default: PARAR Y REPORTAR.

CRITERIO DE ÉXITO
Toda asa se reconoce en las 4 vistas, ninguna caja la tapa, y Análisis de sección usa la tríada. La tabla de la auditoría queda sin filas a medias o mal, con capturas miradas. ruff, tests y piezas en verde.

SALIDA ESPERADA
Informe en español, corto:
- Tabla por comando: antes y después.
- Comparación de Sección contra la tríada, en una línea.
- Salida real de ruff, pytest, las piezas y /ponytail-review.
- Una línea con ⚠ por cada cosa no verificada.

COMPORTAMIENTO DEL AGENTE
- Ejecutá las instrucciones literalmente. No parafrasees ni reinterpretes.
- Si falta una entrada, detenete y pedila. No continúes.
- No agregues contenido que no sea derivable de las entradas.
- No asumas intención más allá de lo explícitamente declarado.
- Priorizá precisión sobre velocidad.
- Si un paso falla, seguí la regla de MANEJO DE ERRORES correspondiente.
```
