# Parámetros: Fusion contra OmniCAD

Especificación de las filas PAR-n y B-138 a B-143 de `docs/seguimiento/`. El estado vive solo allá.

**Fuentes:** 5 capturas de Fusion en español y estos artículos de `docs/fusion_docs/contenido/fusion-model`:
`parameters-in-fusion`, `create-or-edit-parameters`, `import-or-export-parameters`, `parameters-reference` y `unit-types`.
Se comparó el 2026-11-01 con el diálogo real y con 76 expresiones por API.

**Límites de esta revisión:**

- El diálogo de OmniCAD se leyó en el código: no se probó en la ventana.
- La comparación en Fusion real quedó pendiente: el diálogo Parámetros estaba abierto y bloquea los scripts.

## Estado de cada parte

| Parte | Estado | Fila |
|---|---|---|
| Operadores, constantes y funciones | **A medias** | PAR-1 |
| Unidades | **A medias**: 7 unidades en 4 de las 35 familias de la ayuda | PAR-2 |
| Tabla con grupos | **No existe**: tabla plana | PAR-3 |
| Parámetros del modelo | **No existen** | PAR-4 |
| Favoritos | **No existen** | PAR-5 |
| Filtros, búsqueda y orden | **No existen** | PAR-6 |
| Cálculo automático y Aplicar | **No existen**: se aplica al Aceptar | PAR-7 |
| Agregar parámetro de usuario | **A medias** | PAR-8 |
| Crear en cualquier campo y autocompletar | **Solo en cotas de boceto** | PAR-9 |
| Importar y exportar CSV | **A medias** | PAR-10 |
| Parámetros de texto | **A medias** | PAR-11 |
| Texto de boceto con `{parámetro}` | Anda | Nada |
| Coma decimal, paréntesis y `+ - * /` | Anda | Nada |
| Detección de ciclos | Anda | Nada |

## PAR-1 · Expresiones

Hoy `timeline/parametros.py` usa `ast` de Python: no puede leer `;`, `^`, `%`, `<>` ni `if(`. Hace falta un lector propio,
sin `eval`, con tope de anidado y la misma caché.

| Grupo | Falta |
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

Hoy: mm, cm, m, in, ft, deg, rad, y °. El artículo `Unit types` lista 35 familias. Falta, por lo menos en Longitud:
hm, micron, yd, mi, nauticalMile, mil y `"`; en Ángulo: grad. Las familias se toman completas del artículo.

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

Hoy las columnas son Nombre, Expresión, Tipo, Valor y Comentario, sin grupos.

## PAR-4 · Parámetros del modelo

Cada operación y cada cota crean su parámetro automático. Hoy, después de extruir 15 mm, `get_parameters` no muestra nada: las
expresiones viven dentro de cada paso y solo las cotas de boceto tienen `dN`.

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

La ayuda dice que Apply aparece con la casilla encendida, y las capturas con la casilla encendida no lo muestran. Se
comprueba en Fusion antes de programarlo.

## PAR-8 · Diálogo y botones

- **+** abre el diálogo aparte Agregar parámetro de usuario: Nombre, Unidad, Expresión, Valor calculado y Comentarios.
- A la derecha: +, un ícono de copiar (gris sin selección, sin nombre en la ayuda), papelera, importar, exportar.
- Abajo: ícono de información y **Aceptar**. Con cálculo automático no hay Cancelar. Definir qué pasa con deshacer.
- Hoy: botones de texto Agregar, Quitar, Importar y Exportar, más Aceptar y Cancelar.

## PAR-9 · Crear parámetros mientras se modela

- `Ancho=50` o `Largo=Ancho*2` en cualquier campo de expresión crea el parámetro y lo marca favorito.
- Hoy solo en cotas de boceto (`ui/editor_boceto.py`). En Extruir, `alto=15 mm` falla con «Sintaxis inválida».
- Escribir el nombre de un favorito lo ofrece en una lista.
- Ícono para alternar expresión y valor en el campo.

## PAR-10 · Importar y exportar

- Importar abre **Parámetros seleccionados** con una casilla por parámetro. Hoy importa todo de una.
- Exportar lleva solo los de usuario.
- `import_parameters` suma la selección por nombres.
- Tiene que aceptar todas las unidades de PAR-2.

## PAR-11 · Parámetros de texto

`Pieza {PartNumber}` en la expresión de un parámetro de texto tiene que mostrar el valor resuelto. Hoy queda literal.

## Pendiente de comparar en Fusion real

Se junta en una pasada, sin ningún diálogo abierto y en un documento temporal que se cierra sin guardar:

1. Todas las expresiones de PAR-1 y PAR-2, sobre todo `sign`, `log`, `random` y `2 w`.
2. Qué nombres admite: `E`, `PI`, `mm`, `sin`, `µm_x`.
3. Qué rechaza: `w * h` en una longitud, `w + 1 deg`, `10 mm * 2` sin unidad.
4. Qué hace Apply, el ícono de copiar y la selección dentro del diálogo.
5. Si `Parámetros del modelo` nombra d1, d2… y por componente.
6. B-134: HOLA sobre un círculo de R57, cuántos perfiles salen y si el disco conserva su área.
