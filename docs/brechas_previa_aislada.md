# Vista previa en proceso aparte: error oculto y demora

Especificación de B-155 y del punto 1 de RS-X6. El estado vive solo en `docs/seguimiento/`.

## Qué pasa

Gerardo lo vio el 2026-11-01 en Empalme y Chaflán, sobre la arista de un agujero, con cuerpos de 64 caras o más:

- El panel dice «El proceso de la vista previa falló (código 0x1)».
- Con un valor bueno, queda «Calculando vista previa en un proceso aparte…» y tarda.

## Causa

- Con 64 caras o más, `ui/comando.py` (`_previa_pesada`) manda la previa a `CalculoPendiente`.
- Un valor imposible hace que el hijo termine con salida 1. El motivo queda en `errores.txt`.
- `CalculoPendiente.sondear` (`nucleo/aislado.py:419`) no lo lee, a diferencia de `_caida`.
- Cada previa arranca un Python nuevo, con prioridad baja, y rehace el documento (P-56 y RS-X6).

## Medido

Placa de 400 × 400 × 10 mm con 70 agujeros de Ø 20, dos pasos, con el cierre completo corriendo:

| Radio | Salida del hijo | Tiempo | Mensaje |
|---|---|---|---|
| 5 mm | 0 | 1,81 s | Previa correcta |
| 9,9 mm | 0 | 1,81 s | Previa correcta |
| 32,329 mm | 1 | 1,34 s | `errores.txt` tiene «El empalme falló: el radio es demasiado grande…»; el panel muestra `código 0x1` |

Script: `evidencias/empalme_previa_2026-11-01/repro.py`.

## Prompt para el agente

Entregado el 2026-11-01. Modelo sugerido: Sol en OpenCode, esfuerzo alto. Comando: `openai/gpt-6.1-sol --variant high`. Se lanza después de los commits del cierre.

```text
ARRIBA DE TODO, ANTES DE TOCAR NADA
Invocá /fable-method y /ponytail. Usá plan-then-do, tool-calling-guard, verify-before-commit y omnicad-test.
Antes de cerrar, invocá /ponytail-review y pegá en el informe su salida completa, escrita por vos.

OBJETIVO
Hacer que la vista previa pesada de OmniCAD muestre el error real y responda más rápido: cerrar B-155 y el punto 1 de RS-X6.

CONTEXTO DEL AGENTE
- Plataforma: OpenCode en D:\PROGRAMA, sobre main.
- Herramientas: archivos, Bash, Python del venv en clon/.venv, pytest, ruff, scripts/turno.py, scripts/prueba_ui/ y scripts/fusion_docs.py.
- Reglas del proyecto: CLAUDE.md y AGENTS.md.

TAREA PRINCIPAL
Corregir CalculoPendiente y su uso en la ventana, sin cambiar el resultado de ninguna previa correcta.

ENTRADAS
- Diagnóstico: docs/brechas_previa_aislada.md → [PROVIDED]
- Filas: docs/seguimiento/bugs.md (B-155) y mejoras.md (RS-X6, P-56) → [PROVIDED]
- Reproducción: evidencias/empalme_previa_2026-11-01/repro.py → [PROVIDED]
- Código: clon/omnicad/nucleo/aislado.py, clon/omnicad/timeline/calculo_aislado.py, clon/omnicad/ui/comando.py → [PROVIDED]
- Ayuda de Fusion: clon/.venv/Scripts/python.exe scripts/fusion_docs.py buscar fillet -s fusion-model → [PROVIDED]

PROCESO
1. Correr git status y confirmar que aislado.py, calculo_aislado.py y comando.py no tienen cambios sin commitear.
2. Leer las filas, el diagnóstico y los tres archivos de código hasta poder citar dónde nace cada falla. [REQUIERE: paso 1]
3. Correr repro.py y copiar su salida como medida de partida. [REQUIERE: paso 2]
4. B-155: hacer que un error de geometría del hijo llegue completo al panel, sin el nombre de la excepción y sin cortarlo a 200 caracteres. Terminar cuando el radio 32,329 mm muestre el mismo texto que da la previa en el proceso principal. [REQUIERE: paso 3]
5. B-155: mantener un mensaje claro para una caída nativa o un hijo que no deja detalle, reusando _caida. Terminar cuando una salida distinta de 0 sin detalle no muestre un código suelto. [REQUIERE: paso 4]
6. RS-X6 punto 1: servir previa_visual desde el trabajador persistente de RS-X1, con su documento vivo. Terminar cuando la segunda previa del mismo documento no reconstruya el documento y un valor nuevo cancele el cálculo anterior sin congelar la ventana. [REQUIERE: paso 5]
7. Agregar tests con resultado numérico o de texto: mensaje de radio imposible, de chaflán imposible, caída sin detalle, valor bueno después de uno malo, y cancelar seguido de otra previa. [REQUIERE: paso 6]
8. Probar en la ventana con eventos simulados: Empalme y Chaflán sobre un agujero, en un cuerpo de 64 caras o más, tecleando 5, 32,329, 9,9, vacío y arrastrando el asa. Aceptar, deshacer, Esc y mirar las capturas. Sumar la pieza a scripts/prueba_ui/todo.py. [REQUIERE: paso 7]
9. Repetir repro.py y comparar los tiempos con el paso 3. [REQUIERE: paso 8]
10. Correr ruff y los tests tocados con scripts/turno.py, más test_b48_prevuelo_ui, test_seguimiento y test_doc_agentes. [REQUIERE: paso 9]
11. Borrar B-155, dejar en RS-X6 solo lo que falte, anotar ID y prueba en el Registro de PROJECT_LOG.md y actualizar docs/auditorias/prueba_nocturna_2026-10-31.md. [REQUIERE: paso 10]
12. Invocar /ponytail-review y corregir lo que encuentre. [REQUIERE: paso 11]

REGLAS
- SÍ hacer el cambio más chico que resuelve cada punto.
- SÍ tratar el hijo como proceso que puede caer: su error nunca rompe la ventana ni el documento.
- SÍ conservar el proceso aparte para los cuerpos pesados: la ventana no se congela.
- NO cambiar CARAS_PESADAS ni TIPOS_PESADOS.
- NO cambiar el cálculo de Empalme ni de Chaflán.
- NO cambiar qué hace Aceptar cuando la previa falló.
- NO importar Qt fuera de ui/.
- NO instalar paquetes ni el toolchain de Rust.
- NO correr la suite completa ni la prueba de humo.
- NO hacer commit ni push.
- NO tocar archivos ajenos a estas filas. Anotarlos en el informe.
- SÍ correr de a un comando pesado con scripts/turno.py: la PC tiene 13 GB. todo.py va sin turno.py.

MANEJO DE ERRORES
- Paso 1: PARAR Y REPORTAR si alguno de los tres archivos tiene cambios sin commitear.
- Paso 6: PARAR Y REPORTAR si servir la previa desde el trabajador cambia el resultado de una previa correcta. Dejar B-155 terminado y RS-X6 sin tocar.
- Paso 10: PARAR Y REPORTAR con la salida real si algo sigue rojo después de 2 intentos.
- Default: PARAR Y REPORTAR.

CRITERIO DE ÉXITO
Un radio imposible muestra el motivo real en el panel. Ninguna previa muestra un código suelto. La segunda previa de un mismo documento no rearma el documento. ruff, tests y pieza en verde, con capturas revisadas.

SALIDA ESPERADA
Informe en español, corto:
- Tabla: ID, cerrado o abierto, prueba que lo cubre.
- Tiempos antes y después.
- Firma de cada función pública nueva.
- Salida real de ruff, pytest, la pieza y /ponytail-review.
- Una línea con ⚠ por cada cosa no verificada.

COMPORTAMIENTO DEL AGENTE
- Ejecutá las instrucciones literalmente. No parafrasees ni reinterpretes.
- Si falta una entrada, detenete y pedila. No continúes.
- No agregues contenido que no sea derivable de las entradas.
- No asumas intención más allá de lo explícitamente declarado.
- Priorizá precisión sobre velocidad.
- Si un paso falla, seguí la regla de MANEJO DE ERRORES correspondiente.
```
