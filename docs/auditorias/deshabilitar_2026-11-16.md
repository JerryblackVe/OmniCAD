# Candidatos a «No disponible» (P-169 (2), regla 16)

E7, 2026-11-16. Criterio de entrada: solo lo que **rompe, pierde trabajo o no hace nada en el uso común**, y lo más chico posible (la opción, no el comando). Lo lento y los casos raros quedan afuera.

Cruce hecho: las filas de `bugs.md` (76 tras B-603), las 28 de `faltantes.md` y las 47 de `mejoras.md` (Abierto y Parcial, prioridad 1 primero), las auditorías de `docs/auditorias/`, los mensajes «todavía no está» del código y la cinta real (`cinta.no_disponibles`, medido con la ventana abierta: 15 acciones, 8 ítems distintos).

Resultado corto: **casi todo lo abierto ya funciona o falla con un error claro**; la lista honesta es corta. Lo que falta no es grisar más, sino ponerle motivo a lo que ya está en gris.

## A. Ya están en gris, solo falta el motivo (la cinta hoy dice «No disponible en OmniCAD 1.x.» sin motivo)

| Clave / ítem de la cinta | Motivo de 1 renglón | ID |
|---|---|---|
| Crear forma (SÓLIDO › Crear) | Todavía no se puede crear una forma libre | P-25i (despues.md) |
| Crear placa de circuito impreso (submenú vacío) | La placa de circuito no está hecha | P-25i |
| Administrar materiales (SÓLIDO › Modificar) | Los materiales se cambian desde Aspecto | P-25d |
| Crear reglas de configuración (CONFIGURAR, 5 veces) | Las reglas de configuración no están hechas | CFG-1 |
| Edición directa (MALLA) | La edición directa de mallas no está hecha | MAL-2 |
| Alinear (MALLA) | Alinear mallas no está hecho | MAL-2 |
| Extruir textura (MALLA) | Extruir textura no está hecho | MAL-2 |
| Pestaña solevada (CHAPA) | La pestaña solevada no está hecha | CHA-1 |
| Cierre de esquina (CHAPA) | El cierre de esquina no está hecho | CHA-1 |
| Grupos anidados del Navegador (menú Mover) | Los grupos dentro de grupos no están hechos | `acciones_navegador.py:135` (sin fila) |
| Copiar con referencias (Navegador) | Copiar cuerpos con sus referencias no está hecho | `acciones_navegador.py:159` (sin fila) |
| Conjuntos de contactos (hoy activos) | — | SC6: la fila dice «el botón sigue grisado», pero los ítems de la cinta están activos con acción real (`ventana.py:476-480`); no probé que hagan efecto: E11 o la próxima pasada; la fila puede estar desactualizada |

## B. Candidatos nuevos (hoy están activos y fallan o no hacen nada)

| Clave / opción | Motivo de 1 renglón | ID | Por qué entra |
|---|---|---|---|
| `restr_perpendicular` con una spline y una línea | Perpendicular no funciona con splines | B-586 | Con el mouse queda «elegí dos líneas» y nada más: no hace nada. Se grisa solo ese par, no la restricción |
| `mover_copiar` › Objeto «Boceto 3D» | Mover un boceto 3D no está hecho | `ops_modificar.py:94` (sin fila) | Se elige, se acepta y recién ahí avisa «todavía no está» |
| `alinear` › combinaciones cara–eje, cara–punto y eje–punto | Alinear: las dos cosas tienen que ser del mismo tipo | `ops_ensamblar.py:1327` (sin fila) | El panel deja elegir cualquier par y falla al aceptar. Mejor: grisar el segundo campo que no sirve, no el comando |
| `restr_concentrica` sobre dos círculos que ya tienen Tangente externa | — | B-582 | Pierde geometría (los círculos colapsan a radio ~0) sin aviso. **Mejor arreglarla que grisarla**; si no entra en el día, grisar solo esa combinación |

## C. Revisadas y descartadas (para que nadie las vuelva a mirar)

| ID | Por qué no entra |
|---|---|
| B-592, B-591, B-488, B-48, B-172 | Se arreglan o se confirman (Windows o E11); grisar Extruir o el boceto dejaría la app sin uso |
| B-363 (.f3d de Prusa) | Ya avisa que no encontró geometría; es un archivo concreto |
| B-503, H-118 (Cara de desfase en letras o roscas) | Caso raro, con error propio |
| B-477, B-478, B-486 (valores que se rechazan) | Dan un error claro; el uso común anda |
| B-575, B-594, B-546, B-461 (lentitud) | Lento no entra |
| B-465 (doble clic en Solevación) | No se reproduce; falta el mouse real (E11) |
| B-467 (Empalme en aristas tangentes) | Ya entra salvo todas lisas, con mensaje claro (B-454) |
| B-552 (sección en XY a distancia 0) | Caso borde, prioridad 2 |
| H-83, SOL-39, SOL-40, SUP-32, SUP-28, H-117 | La opción no está en la pantalla: no hay nada que grisar |
| SOL-8 (Barrido de cuerpo aproximado), SUP-13, SUP-14, H-91, SOL-22, SOL-24, ASM-17, ASM-18, F8, SC8 | Funcionan en parte y no rompen; el motivo va en la ayuda, no en un gris |
| `operaciones.py:1326` y `:1444` («todavía no está disponible») | Solo salen si al kernel le falta el método avanzado (`kernel is None or not hasattr`); no lo vi salir en el uso común, pero no lo probé con la ventana |
| API: `move_faces` sobre caras curvas, `measure` de mallas | Ya devuelven un error claro; en la API alcanza el kind |

## Carga en `deshabilitado.py` (hecha con el mecanismo de main, 50aea22)

**Resultado: la lista queda vacía, a propósito.** Ninguna candidata se puede expresar con el mecanismo sin apagar algo que anda:
- **Sección A (ya en gris):** son ítems sin comando (`_i("Texto")`), sin clave que apagar; y sus IDs viven en `despues.md`, que `tests/test_deshabilitado.py` no cuenta como «abierto». Lo que falta es que el tooltip diga el motivo: es un cambio de `cinta.py` (los ítems grises con texto), no una entrada de la lista.
- **B-586 (Perpendicular spline–línea), Alinear con tipos mezclados, B-582:** son combinaciones de dos elecciones. El mecanismo apaga un comando, un campo o una opción; apagar `restr_perpendicular` o `alinear` entero quita lo que anda (línea–línea, cara–cara). No lo hago (regla 15). B-582 se arregla.
- **Mover un boceto 3D:** sin fila de seguimiento (el ID es obligatorio) y es un caso raro; si se quiere, crear la fila y apagar la opción de objeto «Bocetos 3D» de `mover_copiar`.

Propuesta (para el coordinador): (1) que la cinta muestre «No disponible: <motivo>» también en los ítems grises sin comando, con el motivo de la sección A; (2) darle fila a «Mover boceto 3D» y a «Alinear con tipos mezclados» si se quieren apagar esas opciones.

## No cubierto

- No recorrí botón por botón la cinta completa con el mouse para encontrar «botones activos que no hacen nada» que nadie anotó; lo que sale acá viene de las filas, los mensajes del código y la cinta medida. Eso lo cubre E11 con la PC.
