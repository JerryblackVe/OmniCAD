# Parámetros: Fusion contra OmniCAD

Especificación de las filas PAR-n y B-138 a B-143 de `docs/seguimiento/`. El estado vive solo allá.

**Fuentes:** 5 capturas de Fusion en español y estos artículos de `docs/fusion_docs/contenido/fusion-model`:
`parameters-in-fusion`, `create-or-edit-parameters`, `import-or-export-parameters`, `parameters-reference` y `unit-types`.
Se comparó el 2026-11-01 con el diálogo real y con 76 expresiones por API.

Lo que sigue es qué pide cada fila y qué midió Fusion real. Lo decidido al construirlo está en «Decisiones».

## PAR-1 · Expresiones

Lector propio en `timeline/parametros.py`, sin `eval`, con tope de anidado y caché. Sintaxis de Fusion:

| Grupo | Qué |
|---|---|
| Operadores | `%` `^` y `;` entre argumentos |
| Constantes | `E`, `Gravity` (980.665 cm/s²), `SpeedOfLight` (29979245800 cm/s) |
| Comparar | `>` `<` `>=` `<=` `==` `<>` |
| Lógica | `if(a; b; c)` anidable, `and`, `or`, `not` |
| Funciones | `acos` `asin` `atan` `acosh` `asinh` `atanh` `cosh` `sinh` `tanh` `sign` `exp` `ln` `log` `pow` `random` |
| Dos argumentos | `max(a; b)` y `min(a; b)` |
| Nombres | Símbolos `"` `$` `°` `µ` |

Reglas de compatibilidad:

- `max(w, h)` tiene que seguir andando, porque hay recetas viejas.
- Con `;`, la coma es decimal: `max(1,5 mm; 2 mm)` da 2 mm.
- Un parámetro llamado `E` o `Gravity` en una receta vieja gana sobre la constante.

## PAR-2 · Unidades

Las 35 familias del artículo `Unit types`, en `timeline/unidades.py`, más lo que aceptó Fusion real (dm, km, `'`).

- La columna Unidad ofrece la lista de Fusion, con No unit y Text.
- Cada parámetro valida la magnitud del resultado: `w * h` en una longitud es error. Ver B-141.
- Solo longitud, ángulo y sin unidad alimentan pasos del modelo; el resto sirve para calcular y comentar.

## PAR-3 · Tabla

| Columna | Contenido |
|---|---|
| Parámetro | Ícono y a qué operación pertenece; primera columna, con orden |
| Nombre · Unidad · Expresión | Editables, con Unidad en lista |
| Valor | Calculado, solo lectura |
| Comentarios | Editable |

Filas fijas, aunque estén vacías: **Favoritos**, **Parámetros de usuario** (ícono fx) y **Parámetros del modelo** (ícono de
cubo). Debajo del modelo: componente › operación › parámetro, plegables.

## PAR-4 · Parámetros del modelo

Cada operación y cada cota crean su parámetro automático.

- Listar operación por operación con nombre estable.
- Editar desde la tabla actualiza el paso, y citarlo desde otra expresión funciona.
- Recetas viejas: se abren sin cambios. Los nombres se generan al abrir o se guardan en la receta sin romper la lectura.

## PAR-5 · Favoritos

Estrella por parámetro de usuario o de modelo, grupo arriba y filtro. Nombrar un parámetro mientras se modela lo agrega solo.
Se guarda en el documento y sale en la API.

## PAR-6 · Barra superior

- **Ordenar en secuencia temporal** (ícono fx, encendido por defecto), texto de la captura: «Ordenar entradas de tabla de
  parámetros en orden de secuencia temporal».
- **Filtrar parámetros de usuario** y **Filtrar parámetros favoritos**, con los textos de las capturas.
- **Filtrar todos los parámetros:** caja de búsqueda.
- Clic en la cabecera ordena: Nombre y Unidad por letras; Expresión y Comentario por letras y número; Valor por número.

## PAR-7 · Cálculo automático

Casilla **Cálculo automático**, encendida por defecto. Encendida, el diseño se actualiza de fondo mientras se edita.
Apagada, se pausa. Hace falta un diálogo no modal, y el cálculo no puede congelar la tabla.

La ayuda dice que Apply aparece con la casilla encendida, y las capturas con la casilla encendida no lo muestran. Se siguen
las capturas: Aplicar aparece con la casilla apagada.

## PAR-8 · Diálogo y botones

- **+** abre el diálogo aparte Agregar parámetro de usuario: Nombre, Unidad, Expresión, Valor calculado y Comentarios.
- A la derecha: +, un ícono de copiar (gris sin selección, sin nombre en la ayuda), papelera, importar, exportar.
- Abajo: ícono de información y **Aceptar**. Con cálculo automático no hay Cancelar.

## PAR-9 · Crear parámetros mientras se modela

- `Ancho=50` o `Largo=Ancho*2` en cualquier campo de expresión crea el parámetro y lo marca favorito.
- Escribir el nombre de un favorito lo ofrece en una lista.
- Ícono para alternar expresión y valor en el campo.

## PAR-10 · Importar y exportar

- Importar abre **Parámetros seleccionados** con una casilla por parámetro.
- Exportar lleva solo los de usuario.
- `import_parameters` suma la selección por nombres.
- Tiene que aceptar todas las unidades de PAR-2.

## PAR-11 · Parámetros de texto

`Pieza {PartNumber}` en la expresión de un parámetro de texto muestra el valor resuelto.

## Comparado en Fusion real (2026-11-01)

Por script, con la API de Fusion, en documentos temporales cerrados sin guardar. Scripts y salidas: `evidencias/fusion_2026-11-01/`.

| Tema | Fusion real |
|---|---|
| Operadores | `5 % 3` = 2; `5 mm % 3 mm` = 2 mm; `2 ^ 3` = 8. `^` no admite unidades: `2 mm ^ 2` y `w ^ 2` son inválidos |
| Comparar | `>` `<` `>=` `<=` `==` `<>` dan 1 o 0; `!=` es inválido |
| Lógica | `and` y `or` van entre valores: `(1>0) and (2>1)`, `1 and 0`. `and(1;0)` es inválido. `not(1>0)` vale, `not 1` no |
| `if` | `if(c; a; b)`, anidable, y 1 o 0 sirven de condición. Con comas es inválido |
| Argumentos | `max(1;2)`; `max(1,5 mm; 2 mm)` = 2 mm; `1,5 mm` vale. `max(1,2)` es inválido en Fusion: OmniCAD lo sigue aceptando por las recetas viejas |
| Constantes | `E` y `PI`, solo en mayúsculas. `Gravity` y `SpeedOfLight` solo valen con unidad de aceleración o velocidad: en mm o sin unidad son inválidas |
| `sign` | **Negativo y cero dan 0**, positivo da 1: `sign(-3)` = 0. Conserva la unidad: `sign(3 mm)` = 1 mm |
| Logaritmos | `log(100)` = 2, en base 10; `ln(E)` = 1; `exp(1)` = 2,718 |
| `pow` | `pow(2;3)` = 8; `pow(2 mm;2)` es inválido |
| `random` | `random()`, de 0 a 1, distinto en cada lectura. Sin paréntesis es inválido |
| Redondeo | `round(2.5)` = 3, `round(-2.5)` = -3: se aleja del cero. `round`, `ceil`, `floor` y `abs` conservan la unidad |
| `sqrt` | `sqrt(4 mm * 4 mm)` = 4 mm |
| Trigonometría | Sin unidad toma grados: `sin(45)` = 0,7071, `tan(45)` = 1 y `sin(PI/4)` = 0,0137. `sin(1 rad)` = 0,8415 |
| `1/2 mm` | **Rechazado por inferencia, falta medirlo en Fusion**: con la misma gramática que `sin(PI/4 rad)` se lee `1 / (2 mm)`, que da `1/mm` y no longitud. OmniCAD lo rechaza con «La unidad '1/mm' es de 1/mm, se esperaba longitud.»; sin unidad, `1/2` vale 0,5 |
| `sin(PI/4 rad)` | **Inválido**: lee `PI / (4 rad)`. Valen `sin(PI rad / 4)` y `sin(PI/4 * 1 rad)`, que dan 0,7071. Reemplaza lo que pedía el paso 3 del pedido |
| Inversas | `asin` `acos` `atan` `acosh` `asinh` `atanh` dan ángulo: solo valen en un campo de ángulo; `asin(1)` = 90°. En mm o sin unidad son inválidas |
| Hiperbólicas | `sinh` `cosh` `tanh` valen sin unidad |
| Sin operador | `2 w`, `2w` y `w h` son inválidos. `2 mm 3` también |
| Unidades | Valen in, `"`, ft, `'`, yd, mi, mil, micron, dm, hm, km, nauticalMile y grad (100 grad = 90 deg) |
| Número suelto | Toma la unidad del campo: `5` en mm queda `5 mm`, y `10 mm + 2` queda `10 mm + 2 mm` |
| Magnitud | Rechaza `w * h` en mm, `w + 1 deg` en mm y `5 mm` en deg. `w * h` vale en mm^2. `w / h` en mm se reescribe `( w / h ) * 1 mm` |
| Longitud sin unidad | Por API, `10 mm * 2` o `5 mm` sin unidad se aceptan y el valor queda en 0 |
| Nombres rechazados | `E`, `PI`, `mm`, `sin`, `max`, `if`, `Gravity`, espacios, inicio con número, `.`, `-`, `'` y repetidos sin distinguir mayúsculas (`w` y `W`) |
| Nombres aceptados | `_a`, `a_1`, `a$b`, `a"b`, `d1`. `µ`, `°` y `ñ` llegaron mal codificados: quedan sin confirmar |
| Parámetro de texto | Unidad `Text`, expresión `'hola'` |
| Parámetros del modelo | `dN`, con numeración única para todo el diseño, compartida entre componentes. La cota crea uno; cada extrusión crea dos, `AlongDistance` y `TaperAngle` |
| Texto de boceto | Crea dos del modelo, roles `Text1-Height` (`30.00 mm`) y `Text1-Text` (`'HOLA'`). Borrar el texto los borra |
| Citar y renombrar | `d21 * 2` en un parámetro de usuario funciona. Renombrar `d21` a `alto_ext` actualiza esa expresión |

**No se pudo por script:** qué hace Apply, el ícono de copiar y la selección dentro del diálogo. Se programa como en las capturas: con Cálculo automático encendido no hay Apply.

## Decisiones

- **Dos modos de `evaluar`.** Lo que se teclea o se importa va con `estricto=True` y rechaza lo que Fusion rechaza. Una
  receta guardada se evalúa sin mirar magnitudes, porque tiene que abrir con los mismos valores; un paso con una magnitud
  rara calcula igual y deja un aviso en su resultado. `sin(PI/4 rad)` en una receta vieja sigue dando lo de antes, con aviso.
- **`^` con unidades.** La ayuda y `w ^ 2` inválido sugerían que no admite unidades, pero `w^2 / w` en mm vale. La regla que
  cumple todo lo medido: `^` multiplica la dimensión, y `w ^ 2` falla en mm porque da mm². En mm² vale.
- **`5 mm` sin unidad.** Fusion lo acepta y deja el valor en 0: es un valor incorrecto sin aviso, así que acá es error.
  Es la única diferencia a propósito, además de las comas de `max(w, h)` y `round(x, n)`, que quedan por las recetas viejas.
- **Parámetros del modelo.** La expresión sigue viviendo en `Operacion.p`; la tabla tiene una copia con `op` y `clave`, igual
  que las cotas. Los nombres se generan en `Documento._tabla_cotas`: al abrir una receta vieja, con el contador `contador_cotas`
  compartido con las cotas (numeración única, como Fusion), y quedan guardados en `parametros`. Un lector viejo ignora las
  claves nuevas. Un paso con una expresión que no calcula falla él solo: su fila queda sin valor y la tabla sigue.
- **Qué se lista.** `Operacion.claves_modelo`: las `EXPRESIONES` del paso. La extrusión muestra solo lo que usa con sus
  opciones; un boceto, solo sus cotas. La magnitud sale de `tipo_de_clave`, por el nombre de la clave.
- **Renombrar.** Vale para usuario, cotas y valores de pasos, y actualiza parámetros, pasos, cotas, textos y configuraciones.
- **Deshacer.** Todo lo hecho con el diálogo abierto es un paso. Con Cálculo automático no hay Cancelar, como en las capturas;
  apagado aparece Aplicar, y cerrar sin aplicar descarta lo pendiente.
- **Ícono de copiar.** Fusion no dice qué hace y no se pudo medir: duplica el parámetro de usuario seleccionado.
- **Fijado sin medir en Fusion.** `%` con negativos usa el resto de C; `sinh`, `cosh` y `tanh` toman grados sin unidad, como
  `sin`; un nombre puede empezar con `µ`. Otras unidades, como `A` o `H`, siguen valiendo como nombre de parámetro.

## Prompt para el agente

Entregado el 2026-11-01. Modelo sugerido: Opus 5, esfuerzo alto. Antes de usarlo, revisar que los IDs y las rutas sigan vigentes.

```text
ARRIBA DE TODO, ANTES DE TOCAR NADA
Invocá con la herramienta Skill: fable-method, ponytail, plan-then-do, tool-calling-guard, verify-before-commit y omnicad-test.
Antes de cerrar, invocá ponytail-review con la herramienta Skill y pegá su salida real en el informe.

OBJETIVO
Dejar Parámetros de OmniCAD igual a Fusion 360: cerrar B-138 a B-143 y PAR-1 a PAR-11.

CONTEXTO DEL AGENTE
- Plataforma: Claude Code en D:\PROGRAMA, sobre main.
- Herramientas: archivos, Bash, Python del venv en clon/.venv, pytest, ruff, MCP de OmniCAD, MCP de Fusion 360, scripts/fusion_docs.py y scripts/prueba_ui/.
- Reglas del proyecto: CLAUDE.md y AGENTS.md. Otros agentes pueden estar trabajando en la misma carpeta.

TAREA PRINCIPAL
Reemplazar el motor de expresiones y rehacer el diálogo Parámetros como en Fusion, con su herramienta en la API y sin romper recetas viejas.

ENTRADAS
- Especificación: docs/brechas_parametros.md → [PROVIDED]
- Filas: docs/seguimiento/bugs.md (B-138 a B-143) y faltantes.md (PAR-1 a PAR-11) → [PROVIDED]
- Ayuda de Fusion: docs/fusion_docs/contenido/fusion-model: parameters-in-fusion, create-or-edit-parameters, import-or-export-parameters, parameters-reference, unit-types → [PROVIDED]
- Código de partida: timeline/parametros.py, ui/dialogos.py:183, ui/ventana.py:2684, ui/comando.py, ui/editor_boceto.py (separar_nombre), api/herramientas_parametros.py, api/herramientas_parametros_csv.py → [PROVIDED]
- Tests de partida: tests/test_parametros.py y tests/test_api_parametros.py → [PROVIDED]
- Respuestas de Fusion real → [TO BE DISCOVERED BY AGENT]

PROCESO
1. Leer la especificación, los artículos y el código de ENTRADAS hasta poder citar qué pide cada fila.
2. Hacer en Fusion real la comparación de la sección «Pendiente de comparar» en una sola pasada. Abrir Fusion si está cerrado, usar un documento temporal, cerrarlo sin guardar y cerrar Fusion al terminar si lo abriste vos. Si un diálogo abierto bloquea los scripts, avisar a Gerardo en una línea. Anotar los resultados en la especificación. [REQUIERE: paso 1]
3. PAR-1, B-138, B-139, B-141 y B-142: reescribir el lector de expresiones sin `eval`, con tope de anidado y caché. Terminar cuando todas las expresiones de la ayuda den el valor que dio Fusion, `sin(PI/4 rad)` dé 0,7071 y `round(2.5)` dé 3. [REQUIERE: paso 2]
4. PAR-2: agregar las 35 familias de unit-types y el control de magnitud. Terminar cuando `w * h` en una longitud dé un error claro y yd, mi, mil, micron y grad se conviertan bien. [REQUIERE: paso 3]
5. B-140: renombrar un parámetro actualiza otros parámetros, pasos y cotas. Terminar cuando el modelo dé igual después de renombrar y el deshacer lo revierta en un paso. [REQUIERE: paso 3]
6. PAR-4: crear los parámetros del modelo por operación, editables desde la tabla y citables en expresiones. Diseñar primero los nombres y cómo se abren las recetas viejas, y anotar la decisión en la especificación. [REQUIERE: paso 5]
7. PAR-3, B-143, PAR-5, PAR-6 y PAR-8: rehacer el diálogo con las columnas, los grupos, los favoritos, los filtros, el orden, la búsqueda y los botones de las capturas. Comparar cada captura con la ventana. [REQUIERE: paso 6]
8. PAR-7: agregar Cálculo automático con diálogo no modal, sin congelar la tabla. [REQUIERE: paso 7]
9. PAR-9: admitir `Nombre=valor`, autocompletar y alternar expresión y valor en todos los campos de expresión. [REQUIERE: paso 7]
10. PAR-10 y PAR-11: agregar Parámetros seleccionados al importar y resolver llaves dentro de parámetros de texto. [REQUIERE: paso 7]
11. Dar a cada función su herramienta en clon/omnicad/api/ y regenerar docs/agentes/herramientas.md.
12. Agregar tests con resultado numérico y una pieza nueva en scripts/prueba_ui/todo.py: teclear en cada campo, ordenar, filtrar, renombrar, importar, Aceptar, deshacer y reabrir. Probar en 1024x640 y 800x520.
13. Correr ruff, los tests tocados y los de boceto con scripts/turno.py, y la pieza con la ventana minimizada. Mirar las capturas.
14. Borrar de docs/seguimiento/ las filas resueltas, anotar en PROJECT_LOG.md cada ID con su prueba, actualizar docs/auditorias/prueba_nocturna_2026-10-31.md y la hoja de ruta de los dos README.
15. Invocar ponytail-review con la herramienta Skill y corregir lo que encuentre.

DEPENDENCIAS
- 2 va antes de todo el código.
- 3 va antes de 4, 5, 6 y 10.
- 6 va antes de 7; 7 va antes de 8, 9 y 10.
- 11 a 15 van después de todos los arreglos.

REGLAS
- SÍ leer el artículo antes de cambiar cada comportamiento.
- SÍ hacer el cambio más chico que resuelve cada fila.
- SÍ conservar `max(w, h)`, `1,5 mm` y los parámetros viejos llamados `E` o `Gravity`.
- SÍ dar un mensaje en español a cada error.
- SÍ probar como una persona: clics y teclado con eventos simulados.
- NO usar `eval` ni `exec` en expresiones.
- NO importar Qt fuera de ui/.
- NO guardar documentos en Fusion ni tocar D:\Autodesk.
- NO correr el cierre completo ni la suite entera: va de noche, cuando Gerardo lo diga.
- NO hacer commit ni push sin que Gerardo lo pida.
- NO gastar en APIs pagas ni instalar paquetes sin permiso.
- NO tocar archivos ajenos a estas filas. Si hace falta, anotarlo en el informe.

MANEJO DE ERRORES
- Paso 2: SALTAR Y CONTINUAR con lo que dice la ayuda si Fusion no se puede usar, marcando cada dato sin confirmar con ⚠.
- Paso 3: PARAR Y REPORTAR si una receta vieja cambia de valor.
- Paso 6: PARAR Y REPORTAR si el diseño obliga a romper recetas viejas.
- Paso 13: PARAR Y REPORTAR con la salida real si algo sigue rojo después de 2 intentos.
- Default: PARAR Y REPORTAR.

CRITERIO DE ÉXITO
- Todas las expresiones de la especificación dan lo mismo que Fusion.
- Ninguna fórmula devuelve un valor incorrecto sin aviso.
- El diálogo coincide con las 5 capturas.
- Una extrusión aparece en Parámetros del modelo y se puede editar ahí.
- Las recetas viejas abren con los mismos valores.
- MCP, CLI y docs generadas quedan completos.
- ruff, tests tocados y pieza nueva están en verde, con capturas revisadas.
- La salida real de ponytail-review está pegada en el informe.

SALIDA ESPERADA
Informe en español, corto:
- Tabla: ID, cerrado o abierto, prueba que lo cubre.
- Firma de cada función pública nueva y qué hace.
- Tabla corta de lo que respondió Fusion real.
- Salida real de ruff, pytest, la pieza de ventana y ponytail-review.
- Una línea con ⚠ por cada cosa no verificada.
- Una línea sobre si el modelo alcanzó.

COMPORTAMIENTO DEL AGENTE
- Ejecutá las instrucciones literalmente. No parafrasees ni reinterpretes.
- No agregues contenido que no sea derivable de las entradas.
- No asumas intención más allá de lo explícitamente declarado.
- Priorizá precisión sobre velocidad.
- Si un paso falla, seguí la regla de MANEJO DE ERRORES correspondiente.
```
