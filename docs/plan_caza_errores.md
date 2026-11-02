# Caza automática de errores

Plan de un programa propio que busca errores de OmniCAD sin nadie mirando y que se puede volver a correr cuando haga falta.
El estado de lo que encuentre vive solo en `docs/seguimiento/`.

## Por qué

B-157 pasó 8249 tests: un empalme más grande que la pared de un vaciado deja aletas, y el paso sale `ok`. Los tests encuentran solo lo que alguien pensó. Faltan tres cosas:

- **Combinaciones:** cada operación después de cada otra.
- **Medidas relativas a la pieza:** 1,1 veces la pared, no 5 mm fijos.
- **Jueces automáticos:** que digan si la pieza quedó bien sin que nadie la mire.

**Límite honesto:** ningún programa encuentra todos los errores posibles. Este busca los que un juez automático puede detectar, y mide qué cubrió y qué falta. No juzga si algo se ve feo ni si se comporta igual que Fusion; eso sigue en las pruebas a mano y en la comparación con Fusion.

## Reglas de diseño

1. **Cero tokens mientras corre.** Es un programa, sin modelos ni APIs pagas. Solo se gastan tokens al leer el informe final y al arreglar.
2. **Sale solo del catálogo.** Las herramientas y sus parámetros se leen de `api.catalogo()` (386 hoy, 274 modifican). Una herramienta nueva entra sin tocar nada.
3. **Reproducible.** Cada caso sale de una semilla. Con la semilla se repite igual.
4. **Aislado.** Cada caso corre en su proceso, con tope de tiempo y de memoria. Un cuelgue o un cierre inesperado es un hallazgo, no el fin de la corrida.
5. **Reanudable.** El avance se guarda en disco. Si se corta la luz, sigue donde estaba.
6. **Sin ruido.** Lo que no se repite dos veces no se informa. Cada causa aparece una sola vez.
7. **Lo encontrado no vuelve.** Cada caso confirmado queda como prueba fija.

## Capas

| Capa | Qué hace | Qué encuentra |
|---|---|---|
| A. Contratos | Cada herramienta y cada parámetro con valor normal, de borde e inválido, según su esquema | Excepciones sueltas, errores sin `error_kind`, valores aceptados que no deberían |
| B. Cadenas | Historias de 3 a 12 pasos sobre piezas semilla: sólido, vaciado, chapa, malla, superficie, boceto, ensamble | Fallas de combinación, como B-157 |
| C. Archivos | Bytes alterados en `.omnicad`, STEP, STL, DXF, SVG y `.f3d` | Cuelgues y cierres con archivos rotos |
| D. Ventana | Eventos simulados al azar sobre cada comando del `CATALOGO`: clics, teclear, Enter, Esc, Tab, asas | Excepciones en slots de Qt, paneles trabados |
| E. Rendimiento | Tiempo y memoria de cada caso contra una base guardada | Lo que se volvió dos veces más lento |
| F. Fusion (opcional, última fase) | Solo con `--fusion`: repite los casos dudosos en Fusion por script | Diferencias de resultado |

### Medidas relativas

El generador mide la pieza con `find_edges`, `find_faces` y `get_physical_properties`, y arma los valores desde ahí. Para cada medida `m` (pared, arista, radio, distancia entre caras) prueba: `0,5 m`, `m − ε`, `m`, `m + ε`, `1,1 m`, `2 m` y `10 m`. Además `0`, negativos, `1e-6`, `1e6` y `nan`.

### Cobertura guiada

Guarda en `evidencias/caza/cobertura.json` qué pares «operación A después de operación B» y qué clases de valor ya corrieron. Cada corrida arranca por lo que falta y por las operaciones que más fallaron. Así, repetirla busca errores nuevos en vez de repetir lo mismo.

## Jueces automáticos

Son lo que convierte un caso en hallazgo sin mirar nada. Se corren después de cada paso que dio `ok`.

| Juez | Falla si |
|---|---|
| Contrato | `api.llamar` lanza, o el error no trae `error_kind` ni mensaje en español |
| Proceso | El proceso muere o pasa su tope de tiempo o memoria |
| Geometría | `check_geometry` da inválido, abierto o con autointersecciones |
| Números | Volumen o área negativos, `nan` o infinitos; caja imposible |
| Esperado por operación | Cortar aumenta el volumen, unir lo reduce, un empalme exterior agranda la caja |
| Identidad booleana | `V(A∪B) + V(A∩B)` no da `V(A) + V(B)` |
| Recalcular | `recompute_all` cambia volumen o caja |
| Guardar | Guardar y reabrir cambia volumen o caja por cuerpo |
| Deshacer | `undo` no vuelve al estado anterior, o `redo` no repite el resultado |
| Exportar | STEP exportado y vuelto a importar cambia el volumen |
| Editar | Subir una cota 25 % y volverla deja otra pieza |
| Mover | Mover la pieza entera cambia el volumen de una operación posterior |

## Reducción, informe y regresión

1. **Reductor:** quita pasos y simplifica valores mientras el juez siga fallando, hasta el caso mínimo.
2. **Firma:** juez + operación + `error_kind` o última línea propia de la pila. Una firma es una causa.
3. **Conocidos:** `scripts/caza/conocidos.json` asocia firmas con su ID de `docs/seguimiento/`. Lo ya anotado no se vuelve a informar.
4. **Informe:** `evidencias/caza_<fecha>/informe.md`, de una página: resumen, cobertura y a lo sumo 20 casos nuevos, ordenados por gravedad. Cada caso tiene su carpeta con `receta.json`, `repro.py` y un render.
5. **Regresión:** `clon/tests/corpus_caza/*.json` guarda los casos mínimos confirmados, y `tests/test_caza_regresion.py` los repite en la suite normal.

## Cómo se usa

Desde `clon/`, con el Python del venv:

| Comando | Para qué | Tiempo |
|---|---|---|
| `../scripts/caza/cazar.py rapida` | Antes de una versión | 10 min |
| `../scripts/caza/cazar.py noche --horas 7` | Búsqueda larga | Lo que se pida |
| `../scripts/caza/cazar.py tema empalme` | Después de tocar una operación | 5 a 15 min |
| `../scripts/caza/cazar.py repetir <firma>` | Comprobar un arreglo | Segundos |

La ventana corre minimizada, así que la PC se puede seguir usando. De a un proceso pesado por vez, respetando `scripts/turno.py`.

## Gasto de tokens

| Etapa | Modelo | Gasto |
|---|---|---|
| Correr | Ninguno | 0 |
| Leer el informe y cargar filas en `docs/seguimiento/` | Haiku o Sonnet bajo | Una página |
| Arreglar cada hallazgo | Según la tabla de `CLAUDE.md` | Lo normal |

## Fases

| Fase | Entrega | Listo cuando |
|---|---|---|
| 1 | Capa B, jueces de geometría y números, reductor, informe | Encuentra B-157 solo |
| 2 | Capa A y jueces restantes, cobertura, conocidos, regresión | `rapida` entra en 10 min y reanuda tras un corte |
| 3 | Capas C, D y E | Detecta dos errores plantados en una copia temporal |
| 4 | Una corrida real y el registro en `CLAUDE.md` | Hallazgos cargados en el seguimiento |
| 5 | Capa F, solo si Gerardo la pide | Compara casos con Fusion |

Si el cupo semanal se acaba, cada fase queda usable sola.

## Prompt para el agente

Entregado el 2026-11-02. Modelo sugerido: Opus 5, esfuerzo alto. Un solo agente, sin OpenCode.

```text
ARRIBA DE TODO, ANTES DE TOCAR NADA
Invocá con la herramienta Skill fable-method y ponytail. Usá plan-then-do, tool-calling-guard, verify-before-commit y omnicad-test.
Antes de cerrar, invocá ponytail-review y pegá en el informe su salida completa, escrita por vos.

OBJETIVO
Construir el cazador automático de errores de OmniCAD descrito en docs/plan_caza_errores.md, fases 1 a 4, listo para correrlo cuando haga falta.

CONTEXTO DEL AGENTE
- Plataforma: Claude Code en D:\PROGRAMA, sobre main. No hay otras sesiones escribiendo código ahora.
- Herramientas: archivos, Bash, Python del venv en clon/.venv, pytest, ruff, scripts/turno.py, scripts/prueba_ui/.
- Reglas del proyecto: CLAUDE.md y AGENTS.md.

TAREA PRINCIPAL
Crear scripts/caza/ con el comando cazar.py, los jueces, el generador, el reductor y el informe, y dejarlo registrado.

ENTRADAS
- Especificación: docs/plan_caza_errores.md → [PROVIDED]
- Catálogo: api.catalogo() y api.llamar en clon/omnicad/api/ → [PROVIDED]
- Revisión de geometría: clon/omnicad/nucleo/revision.py → [PROVIDED]
- Modelo de aislamiento y casos: scripts/fuzz_b39.py → [PROVIDED]
- Arnés de ventana: scripts/prueba_ui/arnes.py → [PROVIDED]
- Caso de control: B-157 en docs/seguimiento/bugs.md → [PROVIDED]
- Piezas semilla y qué herramientas excluir → [TO BE DISCOVERED BY AGENT]

PROCESO
1. Leer el plan, fuzz_b39.py, revision.py y el docstring de api/registro.py hasta poder decir cómo se llama una herramienta y cómo se mide el resultado.
2. Listar las herramientas que no se pueden correr sin riesgo: las que abren red, gastan API, escriben fuera de la carpeta temporal o tocan preferencias del usuario. Excluirlas en una lista con la razón de cada una. [REQUIERE: paso 1]
3. Fase 1: construir la capa B, los jueces de geometría y números, el reductor y el informe. Terminar cuando `tema empalme` encuentre B-157 sin recibirlo como dato y lo reduzca a 5 pasos o menos. [REQUIERE: paso 2]
4. Fase 2: sumar la capa A, los jueces restantes, la cobertura, conocidos.json, el corpus y tests/test_caza_regresion.py. Terminar cuando `rapida` tarde 10 min o menos y siga donde estaba después de matarla a la mitad. [REQUIERE: paso 3]
5. Fase 3: sumar las capas C, D y E. Plantar dos errores en una copia temporal del paquete (un resultado malo que da ok y una excepción en un slot) y terminar cuando los dos salgan en el informe. Sin dejar nada plantado en el repo. [REQUIERE: paso 4]
6. Fase 4: correr `rapida` una vez más, confirmar cada caso nuevo con omnicad-test sección 5 y cargarlo en docs/seguimiento/. Sumar sus casos mínimos al corpus. [REQUIERE: paso 5]
7. Agregar a CLAUDE.md la sección «Caza automática de errores»: qué es, los cuatro comandos, cuándo se corre (rapida antes de cada versión; noche cuando Gerardo lo pida o después de una tanda grande), dónde sale el informe y quién lo lee. Actualizar docs/README.md, AGENTS.md (mapa de scripts) y PROJECT_LOG.md. [REQUIERE: paso 6]
8. Correr ruff, los tests propios con scripts/turno.py, test_seguimiento y test_doc_agentes. [REQUIERE: paso 7]
9. Invocar ponytail-review y corregir lo que encuentre. [REQUIERE: paso 8]

REGLAS
- SÍ reusar api.catalogo, api.llamar, revision.py y el arnés. NO duplicar sus chequeos.
- SÍ dejar afuera de la capa F: la fase 5 no se hace.
- NO usar modelos, APIs pagas ni red.
- NO instalar paquetes: hypothesis y similares quedan afuera.
- NO abrir Fusion.
- NO importar Qt fuera de ui/ en código de la app. El cazador usa Qt solo en su módulo de ventana.
- NO modificar código de la app para arreglar hallazgos: se anotan. Excepción: un gancho mínimo sin cambio de conducta si un juez no puede medir sin él, explicado en el informe.
- NO tocar documentos de Gerardo: todo en carpetas temporales.
- NO mover el cursor real: eventos simulados al widget.
- SÍ guardar resultados en evidencias/, que no va a git. Solo el código, conocidos.json y el corpus van al repo.
- SÍ correr de a un proceso pesado, con tope de 3 GB por caso: la PC tiene 13 GB.
- NO correr la suite completa ni la prueba de humo.
- NO hacer commit ni push.

MANEJO DE ERRORES
- Paso 3: PARAR Y REPORTAR si tras 3 intentos no encuentra B-157: el cazador no sirve sin eso.
- Paso 5: SALTAR Y CONTINUAR con la capa que falle, marcándola con ⚠ y la causa.
- Paso 8: PARAR Y REPORTAR con la salida real si algo sigue rojo después de 2 intentos.
- Default: PARAR Y REPORTAR.

CRITERIO DE ÉXITO
`cazar.py rapida` corre en 10 min o menos sin ayuda, encuentra B-157 solo, detecta los dos errores plantados, reanuda tras un corte y deja un informe de una página. CLAUDE.md explica cómo usarlo. ruff y tests en verde.

SALIDA ESPERADA
Informe en español, corto:
- Qué capas y jueces quedaron.
- Cuántas herramientas cubre y cuáles excluye.
- Hallazgos nuevos con su ID.
- Salida real de ruff, pytest, rapida y ponytail-review.
- Una línea con ⚠ por cada cosa no verificada.

COMPORTAMIENTO DEL AGENTE
- Ejecutá las instrucciones literalmente. No parafrasees ni reinterpretes.
- Si falta una entrada, detenete y pedila. No continúes.
- No agregues contenido que no sea derivable de las entradas.
- No asumas intención más allá de lo explícitamente declarado.
- Priorizá precisión sobre velocidad.
- Si un paso falla, seguí la regla de MANEJO DE ERRORES correspondiente.
```
