# Arreglos con Qwen3.8-Flash en OpenCode (tandas)

Pedido de Gerardo (2026-11-05): seguir con Qwen3.8-Flash (Extra High, 1M de contexto; gratis por ahora) con prompts
hechos a su medida. Los bugs salen de las auditorías de [Revolución, Barrido y Solevación](auditoria_revolucion_barrido_solevacion.md)
y de [Nervio, Red y Repujado](auditoria_nervio_red_repujado.md), y de [Extruir](auditoria_extruir.md).

## Por qué el prompt es así (lo que se vio de Qwen el 2026-11-05)

En los arreglos de Extruir resolvió 3 de 4 bugs, con buen diagnóstico y buen informe, pero:
1. **Cambió una regla en el núcleo y no en su gemelo** (la previa rápida): 3 casos de `test_previa_prisma.py` en rojo.
2. **Corrió solo los tests que eligió**, no todos los que usan lo que tocó.
3. **Dejó sin arreglar un «Should fix» de su propio `ponytail-review`** (una línea).

El prompt lo ataja con tres cosas obligatorias: buscar gemelos antes de editar, una lista de tests fija más los que
salen de `grep`, y arreglar todo lo que marque su `ponytail-review`. Tandas de dos bugs, uno por vez. La geometría
difícil (B-208, B-212, B-213, B-215 y el resto de B-206) no va a Qwen: va a Opus.

## Tandas

Se corren de a una y en orden. El coordinador revisa y commitea cada tanda antes de la siguiente.

| Tanda | Bugs | Archivos probables | Gemelos a revisar | Tests obligatorios |
|---|---|---|---|---|
| 1 | B-211, B-210 | `nucleo/solidos_crear.py`, `nucleo/superficies.py`, `timeline/ops_solido.py`, `timeline/ops_superficie.py`, `ui/comandos/crear.py`, `ui/comandos/superficie.py` | la previa de Revolución y de Barrido (`grep -rn "revol\|barrido" clon/omnicad/ui/comando.py clon/omnicad/nucleo/previa*`), OmniKernel (`nucleo/omnikernel/solidos_crear.py`), `edit_feature` | `test_sol07_revolucion.py`, `test_sol08_barrido.py`, `test_barrido_tipos.py`, `test_api_barrido.py`, `test_gizmo_barrido.py`, `test_solidos_crear.py`, `test_superficies.py`, `test_api_solido.py`, `test_api_superficie.py`, `test_comandos.py`, `test_comandos_superficie.py`, `test_previa_*.py` |
| 2 | B-216, B-214 | `nucleo/solidos_crear.py` (`red`, `nervio`), `timeline/ops_solido.py` | `nucleo/plastico.py` (Nervio y Red de PLÁSTICO), las asas de `ui/comandos/asas_extra.py` | `test_sol10_nervio_red.py`, `test_sol21_reglas_plastico.py`, `test_solidos_crear.py`, `test_api_solido_extra.py`, `test_comandos.py` |
| 3 | B-217, B-209 | `nucleo/solidos_crear.py` (repujado, barrido), `ui/comandos/crear.py` | Barrido de superficie (`nucleo/superficies.py`), la previa | `test_repujado_alineacion.py`, `test_sol08_barrido.py`, `test_barrido_tipos.py`, `test_api_barrido.py`, `test_solidos_crear.py`, `test_superficies.py`, `test_api_solido*.py`, `test_comandos*.py`, `test_previa_*.py` |
| 4 | H-92, H-86 | `ui/comandos/crear.py`, `ui/comandos/solido.py`, `ui/comandos/superficie.py`, `api/herramientas_solido.py`, `api/herramientas_superficie.py` | el valor por defecto en la ventana, en la API y en `PARAMS` de la operación: los tres iguales | `test_comandos*.py`, `test_api_*.py`, `test_doc_agentes.py` |
| 5 | H-99, H-94 | `ui/comandos/crear.py`, el aviso flotante de `ui/ventana.py` | el asa de Profundidad del Repujado, el panel en 800×520 | `test_repujado_alineacion.py`, `test_comandos*.py`, `test_b105_panel_chico.py`, piezas `nervio_red_repujado` y `revolucion_barrido_solevacion` |
| C1 | B-189, H-87 | `nucleo/solidos_crear.py` (`_trozos`, ~3868), `timeline/operaciones.py` (espesor de Extruir delgada, ~1117), `timeline/ops_solido.py` (la regla de plástico, ~1534), `ui/comandos/crear.py` | OmniKernel (`nucleo/omnikernel/`), la API (`api/herramientas_solido.py`, `assign_plastic_rule`), el valor por defecto en ventana, API y `PARAMS` (los tres iguales); Nervio, Red, Vaciado y Engrosar también deberían leer la regla: si no entran, fila nueva | `test_motor.py`, `test_paridad_motor.py`, `test_sol21_reglas_plastico.py`, `test_api_solido.py`, `test_cinta_plastico.py`, `test_comandos.py`, `test_revision_lotes_sol.py` |
| C2 | H-100 | `ui/comandos/crear.py` (~313-316: Ángulo de desmoldeo y radio de Nervio y Red), `timeline/ops_solido.py` | la API (`api/herramientas_solido*.py`: `create_rib`, `create_web`), los `PARAMS` de las operaciones, y `espesor_plastico` en `timeline/operaciones.py` como modelo a copiar (H-87) | `test_sol10_nervio_red.py`, `test_sol21_reglas_plastico.py`, `test_api_solido_extra.py`, `test_comandos.py`, `test_comandos_crear.py` |
| C3 | H-102 | `timeline/ops_solido.py` (Nervio, Red, Vaciado, Engrosar), `ui/comandos/crear.py` y los comandos de Vaciado y Engrosar, `timeline/operaciones.py` (`_regla_plastico`, ya hecho en C1 y C2) | la API (`api/herramientas_solido*.py`: `create_rib`, `create_web`, `shell`, `thicken`), los `PARAMS`, el valor por defecto en ventana, API y operación (los tres iguales) | `test_sol10_nervio_red.py`, `test_sol21_reglas_plastico.py`, `test_api_solido.py`, `test_api_solido_extra.py`, `test_comandos.py`, `test_comandos_crear.py`, `test_doc_agentes.py` |
| C4 | H-93 | `timeline/ops_solido.py` (~149, el aviso de «Selección de cadena» del Barrido) | la previa del Barrido, la API (`api/herramientas_solido.py`: `sweep`), el Barrido de superficie (`timeline/ops_superficie.py`), el valor por defecto de la casilla en ventana, API y `PARAMS` | `test_sol08_barrido.py`, `test_barrido_tipos.py`, `test_api_barrido.py`, `test_comandos.py`, `test_comandos_crear.py`, `test_doc_agentes.py` |
| C5 | H-74 | `ui/aspectos_ui.py` (menú contextual de «En este diseño») | la API (`api/herramientas_aspecto.py`: `manage_appearance` con `remove_users`, que ya lo hace: reusarla, no duplicar), `docs/brechas_aspecto.md`, deshacer en un solo paso | `test_aspecto_panel.py`, `test_aspectos_api.py`, `test_formulario_paneles.py`, `test_render_aspecto.py`, `test_comandos.py` |
| C6 | H-103 | `timeline/aspectos_doc.py` (`quitar` ~140 y `_limpiar_usos` ~224) | la API (`api/herramientas_aspecto.py`: `manage_appearance` › `suprimir`), el panel (`ui/aspectos_ui.py`), el caso `quitar_caras` | `test_aspecto_panel.py`, `test_aspectos_api.py`, `test_render_aspecto.py`, `test_formulario_paneles.py` |
| C7 | CF-11 | `ui/cinta_boceto.py` o la paleta de boceto (`ui/modo_boceto.py`), `restricciones/` (grados de libertad que ya calcula el solver), `api/herramientas_boceto*.py` | la ayuda de Fusion (`fusion_docs.py buscar under constrained -s fusion-sketch` y `buscar compute sketch`), el diálogo de restricciones automáticas que ya existe (`auto_constrain`, `suggest_auto_constraints`), la herramienta del MCP y la CLI (receta C), el ícono y la clave de la cinta (receta B) | `test_api_boceto.py`, `test_api_boceto_herramientas.py`, `test_boceto_fase2.py`, `test_boceto_fase4.py`, `test_cobertura_ui_api.py`, `test_restricciones_matematica.py`, `test_claves_comandos.py`, `test_doc_agentes.py` |
| C8 | H-71 | `ui/navegador_boceto.py` (arrastrar filas entre grupos y teclado en el árbol), el menú radial del visor en modo boceto | `docs/plan_boceto_organizar.md` (secciones 9.5 y 10), la herramienta del MCP que ya organiza el boceto (`get_sketch_organization` y la que cambia de grupo: reusarla), deshacer en un solo paso | `test_boceto_organizar_ui.py`, `test_boceto_organizar.py` (si existe), `test_cobertura_ui_api.py`, `test_comandos.py` |

En cada tanda, además de esa lista: todos los archivos que da
`grep -l "<cada función que tocaste>" clon/tests/test_*.py`.

## Informe tanda 1

Corrida del 2026-11-05 (pasó la medianoche al 11-06). OpenCode con Qwen3.8-Flash en Qoder. Bugs: B-211 y B-210, de a uno y en ese orden.

### B-211 · Barrido: la Distancia mayor que 1 se recorta a 1 sin avisar — **Resuelto**

**Qué dice la ayuda de Fusion** (`fusion_docs.py ver "Sweep reference" -s fusion-model`, desde `clon/`):

> ### Distance
> Specify the distance to sweep along the path.
> Value is measured in percentage of the total distance.
> Range: 0.00-1.00

O sea: 1,5 no es «casi dos vueltas» ni «la ruta entera»: está fuera de rango y hay que rechazarlo. La regla ya estaba escrita en el gemelo de superficie (`nucleo/superficies.py:698`: `0 < valor <= 1`), pero no en el compartido.

**Qué cambié** — `clon/omnicad/nucleo/solidos_crear.py:249` (`_recortar_alambre`), tres líneas:

```python
if not math.isfinite(fraccion) or fraccion > 1.0 + 1e-9:
    raise geo.ErrorGeometria("La distancia sobre la ruta va de 0 a 1 (fracción del total); "
                             f"recibió {fraccion:g}.")
```

Se eligió el compartido y no cada comando porque `_recortar_alambre` es el único que recorta la ruta: un punto cierra el recorte silencioso `min(fraccion, 1.0)` para las cuatro entradas. La tolerancia de 1e-9 deja pasar una expresión que da 1 por coma flotante, que es lo que ya aceptaba la línea siguiente.

**Gemelos revisados** (regla 1; `grep -rn "_recortar_alambre" clon/omnicad`, `grep -rn "distancia"` por archivo y `grep -rn "min(fraccion"`):

| Gemelo | Qué hice |
|---|---|
| `nucleo/solidos_crear.py:904` `barrer` (Barrido, y su superficie con `solido=False`) | pasa por el compartido → arreglado |
| `nucleo/solidos_crear.py:938` `barrer_cuerpo` (Barrido sólido) | pasa por el compartido → arreglado |
| `nucleo/solidos_crear.py:2899` `tuberia` (Tubería, con `distancia2`) | pasa por el compartido → arreglado; su validación previa solo mira NaN/∞ y el inicio, así que quedó |
| `nucleo/superficies.py:582, 595, 710, 724` (corte del riel y de la espina) | ya llegaban con una fracción ≤ 1: `barrer_superficie` rechaza antes (`:698`) y `_recortar_perpendicular` usa `_primer_cruce`, que devuelve (0, 1]. Sin cambio |
| `nucleo/solidos_crear.py:815` (ruta cerrada con torsión: `0.5` y `1.0` fijos) | constantes internas. Sin cambio |
| `timeline/ops_solido.py:162, 181, 585` (`OpBarrido`, `OpTuberia`) | solo evalúan la expresión y la bajan al núcleo. Sin cambio |
| `ui/comandos/crear.py:67` (Distancia del Barrido) y `:1019-1022` (Distancia inicial/final de la Tubería) | la ayuda de los tres campos ya dice «de 0 a 1» / «fracción entre 0 y 1»; con el error del núcleo la previa se pone roja sola. Sin cambio |
| `api/herramientas_solido.py:452` (`sweep`, `path_distance`) | **lo dejé**, aunque el `ponytail-audit` decía «the check in the API can then go»: da `INVALID_ARGUMENTS` antes de calcular y es el patrón de la casa (el `twist_angle` de tres líneas más abajo hace exactamente eso con `TORSION_MAXIMA`); el test que lo exige sigue verde |
| `api/herramientas_superficie.py:169` (`create_surface_sweep`) | sin chequeo propio: depende del núcleo, que ahora rechaza. Sin cambio |
| `nucleo/omnikernel/solidos_crear.py` | no tiene barrido ni recorte de ruta (`grep -n "barrer\|recortar\|distancia"` → nada). Sin cambio |
| la previa rápida (`ui/comando.py`) | `tramo_previa` es solo del prisma de Extruir; Barrido y Tubería calculan la previa con el núcleo. Sin cambio |
| `edit_feature` (`api/herramientas_documento.py:709`) | recalcula y descarta el cambio con el error del paso → test nuevo |
| MCP / CLI | mismo catálogo `api/`, nada que duplicar. No cambió ninguna firma: no se regenera `docs/agentes/herramientas.md` |

**Test nuevo y su salida.** `tests/test_solidos_crear.py::test_barrido_distancia_mayor_que_una_da_error` (5 caminos × 2 valores, más NaN/∞), `tests/test_api_opciones_solido2.py` (con `path_distance="1.5"` y con `edit_feature {"distancia": "2"}`) y `tests/test_comandos_crear.py::test_barrido_distancia_fuera_de_rango_error_en_el_dialogo`.

ROJO antes del arreglo (con el arreglo revertido un momento, para tomar la salida de cada capa):

```
$ pytest tests/test_solidos_crear.py -q -k "distancia_mayor_que_una"
E   Failed: DID NOT RAISE ErrorGeometria
FAILED tests/test_solidos_crear.py::test_barrido_distancia_mayor_que_una_da_error[1.5]
FAILED tests/test_solidos_crear.py::test_barrido_distancia_mayor_que_una_da_error[2.0]
FAILED tests/test_solidos_crear.py::test_barrido_distancia_mayor_que_una_da_error[nan]
FAILED tests/test_solidos_crear.py::test_barrido_distancia_mayor_que_una_da_error[inf]
4 failed, 63 deselected in 1.04s

$ pytest tests/test_api_opciones_solido2.py -q -k "distancia_parcial"
E   AssertionError: {'ok': True, 'result': {'feature': {'id': 'op4', 'name': 'Barrido2', 'type': 'barrido'},
    'bodies_created': [{'id': 'op4.c1', 'name': 'Cuerpo2', 'volume': 251.3274}], ...}}
1 failed, 6 deselected in 1.15s

$ pytest tests/test_comandos_crear.py tests/test_api_opciones_solido2.py -q -k "sweep or distancia_fuera"
E   AssertionError: La selección de cadena solo suma aristas de cuerpos: las curvas de boceto se usan tal cual.
E     assert ('aviso' == 'error'  - error  + aviso)
1 failed, 24 deselected in 1.77s
```

El de la API es el bug entero en una línea: `ok` con 251,33 mm³, que es π·4·20 — la ruta completa. (En la primera versión del test los cuatro valores se probaban juntos; al separar NaN/∞ se vio que `tuberia` ya los rechaza con su propio mensaje «Las distancias deben ser finitas…», así que el test quedó en dos parametrizaciones con la cuenta del rango y un bloque aparte que solo exige `ErrorGeometria`.)

VERDE después: `2 passed, 63 deselected in 0.92s` en el núcleo, y los grupos completos de la tabla de abajo, todos verdes.

### B-210 · Revolución «Dos lados» con un ángulo negativo: sólido contra superficie — **Resuelto**

**Qué dice la ayuda de Fusion** («Revolve reference»): `Two Sides: Revolves profile on each side of the profile plane`, y nada sobre el signo del ángulo. ⚠ Fusion real no se abrió; la regla no sale de la ayuda sino de los tres gemelos que ya la tenían escrita, que es lo que pedía la fila («falta una sola regla para los dos»).

**Estado del código antes de decidir** (medido, no supuesto — `evidencias/ui_2026-11-05/sondas_rbs.py dos_lados`):

```
rev_dos_lados_90_45      | ok | op2.c1:solid    V=3534.29  [-0.00,0.00,-20.00]..[20.00,10.00,14.14]
rev_dos_lados_90_menos45 | ok | op2.c1:solid    V=2356.19  [0.00,0.00,-20.00]..[20.00,10.00,0.00]
srev_dos_lados           | ok | op2.c1:surface  A=235.62
srev_dos_lados_neg       | ok | op2.c1:surface  A=235.62
```

El sólido con −45 da lo mismo que sin lado 2 (la caja no pasa de z = 0) y la superficie con −45 da lo mismo que con +45: **la superficie ya tomaba la magnitud y el sólido no.** (El `1570,80` de la fila había envejecido; medido hoy, eran 2356,19.)

**Qué cambié** — `clon/omnicad/timeline/operaciones.py:1316` (`OpRevolucion.ejecutar`):

```python
forma = geo.unir_todos([geo.revolver(caras, punto, direccion, abs(a1)),
                        geo.revolver(caras, punto, -direccion, abs(a2))])
```

Antes `a1` y `a2` entraban con su signo, así que −45° sobre `-direccion` era +45° sobre `direccion`: el lado 2 caía adentro del lado 1 y se perdía en la unión. Va `abs` también en `a1` porque con −90 pasaba lo mismo al revés. El control de la línea 1311 ya sumaba `abs(a1) + abs(a2)`: la geometría estaba peleada con su propio control.

Y su consecuencia en la ventana — `clon/omnicad/ui/comandos/solido.py:357-365` (`Revolucion.manipuladores`): con `abs`, arrastrar el asa del lado 2 por debajo de 0 no cambiaba nada, así que las dos asas de ángulo se frenan en 0 con «Dos lados» y siguen libres en «Un lado», donde el signo sí significa:

```python
dos = v.get("direccion") == "dos_lados"
salida = [mp.Angulo("angulo", pie, d, centro - pie, radio, minimo=0.0 if dos else -360.0)]
if dos:
    salida.append(mp.Angulo("angulo2", pie, -d, centro - pie, radio, minimo=0.0))
```

**Gemelos revisados** (regla 1; `grep -rn "dos_lados" clon/omnicad` → 70 sitios; los que calculan una geometría con el lado 2 son estos):

| Gemelo | Regla hoy | Qué hice |
|---|---|---|
| `nucleo/solidos_crear.py:676` `revolver_avanzado` | `[(0.0, abs(angulo1)), (0.0, -abs(angulo2 or 0.0))]` | ya era magnitud → de acá saqué la regla |
| `nucleo/superficies.py:475` `revolver_superficie` | `[(0.0, abs(angulo))] + [(0.0, -abs(a2))]` | ya magnitud; sin cambio |
| `timeline/operaciones.py:1316` `OpRevolucion` | usaba el signo | **arreglado** |
| `timeline/operaciones.py:1242` `_extrusion_basica` (el hermano de B-205) | `unir_todos([extruir(..., abs(d1)), extruir(..., -n, abs(d2))])`, con el comentario «el número es una magnitud, su signo no invierte el lado» | precedente directo; sin cambio |
| `nucleo/solidos_crear.py:604` `extruir_avanzado` | `[(abs(distancia1), …), (-abs(distancia2), …)]` | ya magnitud; sin cambio |
| `nucleo/superficies.py:276` y `:389` (extrusión de superficie) | `abs(distancia), abs(distancia2)` | ya magnitud; sin cambio |
| `ui/comando.py:719` `tramo_previa` (previa rápida de Extruir) | `a, b = -abs(d2), abs(d1)` | ya magnitud, y **no toca la Revolución** (es del prisma de Extruir): la previa de Revolución se calcula con el núcleo, así que el arreglo la cubre sola |
| `ui/comandos/solido.py:357` (asas de Revolución) | el asa podía bajar de 0 sin efecto | **arreglado** (tope en 0) |
| `ui/comandos/solido.py:102` (flechas de Extruir) | B-205 ya las frenaba en 0 | referencia del criterio; sin cambio |
| `timeline/ops_superficie.py:202` (`OpSupRevolucion`) | pasa `angulo2` con signo al núcleo, que hace `abs` | sin cambio |
| `ui/comandos/solido.py:307-309` y `ui/comandos/superficie.py:103-105` (campos «Ángulo del lado 1 / del lado 2») | los dos diálogos ya se llaman igual y no prometen signo | sin cambio |
| `api/herramientas_solido.py:388` y `api/herramientas_superficie.py:150` (`revolve`, `create_surface_revolve`) | `angle2` vacío = `angle`; el docstring dice «angle hacia un lado y angle2 hacia el otro», que es la regla de magnitud | sin cambio de texto → no se regenera `docs/agentes/herramientas.md` |
| `nucleo/chapa.py:1111` (pestaña de contorno de CHAPA: `(-distancia2, distancia)`) | con valores negativos tira «Dirección o distancias de la pestaña de contorno inválidas» (`:1112`): no hay forma muda | revisado y **no aplica** (otro comando, y ya avisa) |
| `nucleo/omnikernel/geometria.py:170` (`revolver` del otro motor) | `abs(angulo)` por cara | coincide con la nueva regla; sin cambio |

**Test nuevo y su salida.** `tests/test_api_solido.py::test_revolucion` (90/−45, −90/45 y −90/−45 dan 135/360), `tests/test_api_superficie.py::test_revolucion_segmento_alrededor_de_z` (45 y −45 dan la misma área) y `tests/test_manipuladores.py::test_dos_lados_de_la_revolucion_cada_asa_es_la_magnitud_de_su_lado` (la previa con −45 es igual a la de +45 y las asas no bajan de 0).

ROJO antes del arreglo:

```
$ pytest tests/test_api_solido.py::test_revolucion tests/test_api_superficie.py::test_revolucion_segmento_alrededor_de_z -q
E   AssertionError: {'angle': 90, 'angle2': -45}
E     assert 9387.0788 == 14080.618274999999 ± 0.0140806
1 failed, 1 passed in 1.46s        (falla el sólido; la superficie ya pasaba: el test es la comparación de los dos)

$ pytest "tests/test_manipuladores.py::test_dos_lados_de_la_revolucion_cada_asa_es_la_magnitud_de_su_lado" -q
E   assert (-360.0 == 0.0)
1 failed in 1.69s
```

VERDE después:

```
2 passed in 1.30s      (los dos de revolución)
6 passed in 2.06s      (los cinco tests nuevos de la tanda, corridos por nombre)
```

### `/ponytail-review` (salida completa, sobre el diff de los tres archivos)

`What this change does:` dos reglas de una línea. El recorte de ruta del barrido y la tubería deja de tragarse los valores mayores que 1 (y NaN/∞) y avisa; y el «Dos lados» de la Revolución deja de mirar el signo de cada ángulo, como ya hacían su núcleo, su superficie y la Extrusión. Además las asas del diálogo de Revolución se frenan en 0 con «Dos lados». Carga esperada: una persona o un agente sobre un documento (el criterio del repo); nada de esto corre en un bucle.

**Must fix:** nada.

**Should fix:**

1. **El asa del lado 2 queda inerte por debajo de cero** (`ui/comandos/solido.py:357-365`)
   - **What this is:** Con «Dos lados» el diálogo muestra dos arcos con asa, uno por lado, girando sobre `d` y `-d`.
   - **Problem:** Al tomar `abs` en el paso, un valor negativo tecleado o arrastrado sigue escribiéndose pero ya no cambia la forma: el usuario mueve el asa y el cuerpo no se mueve. Extruir tuvo exactamente esto y se cerró con un tope en 0 (B-205).
   - **Fix:** `minimo=0.0` en las dos asas cuando `direccion == "dos_lados"`, dejando `-360.0` en «Un lado», donde el signo sí significa. Tres líneas, sin clase nueva.
   - **If we skip it:** La ventana ofrece un arrastre que no hace nada, contra la regla de honestidad del repo.

**Nice to have:**

2. **`min(fraccion, 1.0)` sigue en `_recortar_alambre`** (`nucleo/solidos_crear.py:259`)
   - **What this is:** El recorte que causaba el B-211.
   - **Problem:** Después del rechazo solo se alcanza con un valor entre 1 y 1+1e-9 (la tolerancia): es código casi muerto.
   - **Fix:** **no lo toqué** — con `inicio` distinto de 0 (Tubería) esa banda existe y el `min` es lo que la mantiene dentro de la ruta. Sacarlo cambia comportamiento para ganar dos caracteres.
   - **If we skip it:** Nada.

**Arreglé de la revisión:** el ítem 1 (el tope del asa), con su test y su salida ROJA tomada revirtiendo el cambio. El ítem 2 queda como está, con la razón arriba.

**Verdict: Ship.**

### Verificación

`ruff check .` desde `clon/`: `All checks passed!`

Tests: todos con `turno`, `-p no:cacheprovider`, en primer plano y de a un grupo (la lista es la obligatoria de la tanda más los archivos que da `grep -l` de cada función tocada: `barrer`, `barrer_cuerpo`, `tuberia`, `barrer_superficie`, `revolver`, `Revolucion`; `_recortar_alambre` y `OpRevolucion` no aparecen en ningún test). 48 archivos, 2505 comprobaciones, ninguna corrida cortada por tiempo:

| Grupo | Archivos | Salida final |
|---|---|---|
| 1 · núcleo | test_solidos_crear, test_superficies, test_superficie_fusion, test_geometria, test_b52_espiral, test_bugs_solido, test_paridad_motor | `243 passed in 151.78s (0:02:31)` |
| 2 · barrido y tubería | test_sol08_barrido, test_barrido_tipos, test_api_barrido, test_gizmo_barrido, test_superficie_guias, test_tuberia_cadena, test_topes, test_rosca_diametros_tabla, test_rosca_clases_tablas, test_boceto_fase8_3d, test_iconos_extra | `469 passed in 89.06s (0:01:29)` |
| 3 · API sólido/superficie | test_sol07_revolucion, test_api_solido, test_api_solido_extra, test_api_superficie, test_api_opciones_solido1, test_api_opciones_solido2, test_herramientas_solido, test_sup29_encadenado_superficie, test_opciones_operaciones, test_resultados_vacios, test_referencias_mal_formadas, test_graficos_rendimiento | `704 passed in 123.43s (0:02:03)` |
| 4a · diálogos y asas | test_comandos, test_comandos_superficie, test_comandos_crear, test_manipuladores, test_b105_panel_chico | `83 passed in 11.93s` |
| 4b · previa, catálogo y cobertura UI | test_previa_prisma, test_previa_aislada_comandos, test_previa_trabajador, test_previa_vaciado_aislada, test_asas_superficie, test_busqueda_comandos, test_claves_comandos, test_cobertura_ui_api, test_manipuladores (otra vez, ya con el tope del asa) | `495 passed in 324.01s (0:05:24)` |
| 5 · seguimiento y doc | test_seguimiento, test_doc_agentes, test_api_documento, test_api_catalogo, test_api_convenciones | `511 passed in 18.02s` |

Suite completa y prueba de humo: no corridas (regla 10; las toma el coordinador).

Después de editar `PROJECT_LOG.md`, `docs/seguimiento/bugs.md` y este informe, se volvieron a correr los tres archivos que leen esa documentación: `test_seguimiento.py`, `test_doc_agentes.py` y `test_claves_comandos.py` → `450 passed in 5.94s`, y `ruff check .` → `All checks passed!`.

Ventana (regla 9, porque toqué `ui/comandos/solido.py` y cambió la previa del Barrido): la pieza `revolucion_barrido_solevacion` en minimizada. `todo.py` la corta a los 900 s de su `turno` interno (dos intentos), así que se corrió derecho con `../scripts/turno.py --plazo 2700 -- .venv/Scripts/python.exe ../scripts/prueba_ui/revolucion_barrido_solevacion.py` desde `clon/`, con `OMNICAD_PRUEBA_VENTANA=minimizada`:

```
=== 40 comprobaciones, 8 con ✗ ===
```

Los dos checks que hablan de estos bugs pasaron, y son justo los que estaban ✗ en la auditoría (10 ✗ → 8 ✗):

```
[OK ] · Enter acepta la revolución y crea UN paso
[OK ] · Revolución dos lados 90 / −45°: o aviso o 2356,19 mm³ (como la superficie), no el lado 2 perdido — volumen 2356.19 sin aviso «»
[OK ] · reabrir la revolución trae «Dos lados» y −45° — {'direccion': 'dos_lados', 'angulo2': '-45 deg'}
[OK ] · Barrido › Distancia «0,5»: previa
[OK ] · Barrido › Distancia «0»: aviso — ⚠ La distancia sobre la ruta debe ser mayor que cero.
[OK ] · Barrido › Distancia «1,5»: aviso — ⚠ La distancia sobre la ruta va de 0 a 1 (fracción del total); recibió 1.5.
[OK ] · Barrido › Distancia «»: aviso — ⚠ Expresión vacía.
```

O sea: en la ventana real, teclear «1,5» en Distancia ahora **avisa** (antes dejaba la previa en verde), y el lado 2 con −45° da el cuerpo de 135° en vez de perderse. Las 8 ✗ que quedan son todas ítems ya anotados, ninguno de esta tanda: H-88 (2: «A objeto» no muestra Dirección, en sólido y en superficie), H-92 (2: «Proyectar eje» con nombre y valor por defecto distintos), B-209 (Estirar no está en la lista), H-89 (sin Extensión con carril), B-208 (el carril paralelo da 784,02 en vez de 800) y H-90 (la fila del punto solo ofrece «Aguda»).

Capturas miradas con Read: `capturas/barrido_carril.png` (la app entera, con el aviso flotante y el árbol de cuerpos; sin nada roto) y las de tamaño de panel `barrido_1024x640.png` / `barrido_800x520.png`, que la pieza pide en sus dos checks de «Aceptar se ve».

Evidencia: `evidencias/ui_2026-11-05/revolucion_barrido_solevacion.json` y `.log` (la corrida de las 23:42, cortada por el plazo, dejó el `.log` de la auditoría en 63 bytes; se restauró con la salida completa de esta corrida, que es la que está arriba).

### Seguimiento

- `docs/seguimiento/bugs.md`: borradas la fila y la sección «Detalle» de B-211 y de B-210; recuento del encabezado 25 → 23 (Abierto 19 · Parcial 4).
- `docs/seguimiento/README.md`: no tenía filas de esos dos IDs (`grep -n "B-210\|B-211"` → nada), así que no había qué borrar.
- `README.md` y `README.en.md` (hoja de ruta): sin mención de estos dos bugs (`grep` → nada); no se tocó.
- Dos viñetas en «## Registro» de `PROJECT_LOG.md` y una lección en «## Lecciones aprendidas».

### Archivos fuera de mi tanda

La tabla de la tanda 1 no lista `timeline/operaciones.py` (donde está `OpRevolucion.ejecutar`, que es justo la línea que nombra la fila de B-210) ni `ui/comandos/solido.py` (el tope del asa, consecuencia del `abs`). Los dos se tocaron por eso, y nada más. No se tocó `nucleo/superficies.py`, `timeline/ops_solido.py`, `timeline/ops_superficie.py`, `ui/comandos/crear.py` ni `ui/comandos/superficie.py`: los gemelos de esos archivos ya tenían la regla.

### Lo que no pude verificar

- ⚠ **Fusion real no se abrió** para B-210: la ayuda no dice qué hace un ángulo negativo en Two Sides. La regla elegida es la que ya estaba en `revolver_avanzado`, `revolver_superficie` y la Extrusión (B-205), no una observación de Fusion. Si al abrirlo resultara que Fusion rechaza el negativo, el cambio vuelve a ser una línea en cada lado (los tres están juntos).
- ⚠ No verifiqué en la ventana el **arrastre** del asa con el tope nuevo: el test pytest mira el `minimo` del manipulador y el volumen de la previa, no el arrastre con el ratón, y la pieza `revolucion_barrido_solevacion` teclea los ángulos (el arrastre de la Revolución con valores positivos lo prueba `test_angulo_de_la_revolucion`, que quedó verde en el grupo 4b).
- ⚠ El check de ventana de B-210 mide el **sólido** contra los 135° esperados; la igualdad con la superficie en la ventana no se volvió a medir ahí (sale del pytest `test_api_superficie.py::test_revolucion_segmento_alrededor_de_z` y de que la superficie nunca usó el signo).
- ⚠ Proyectos `.omnicad` guardados con una Distancia de barrido mayor que 1 ahora dan error al abrir en vez del cuerpo recortado. En `ejemplos/` no hay ninguno (`grep -rln "barrido" ejemplos/` → nada), pero una pieza del usuario puede tenerlo.

## Informe tanda 2

Corrida del 2026-11-06 (01:30 a 03:00). OpenCode con Qwen3.8-Flash en Qoder. Bugs: B-216 y B-214, de a uno y en ese orden.

### B-216 · Red › «Cambiar dirección» no invierte el sentido — **Resuelto**

**Qué dice la ayuda de Fusion** (`fusion_docs.py ver "Web reference" -s fusion-model`, desde `clon/`):

> ## Flip Direction
> Flips the direction in which the web feature is extruded.

Y en `Rib reference`, la misma frase para el Nervio. O sea: el botón gira la extrusión, no el espesor.

**Estado del código antes de decidir** (medido con `../evidencias/ui_2026-11-05/sondas_nrr.py`, caja 40³ cerrada vaciada 2 mm, boceto en y = 15 con la línea z = 20):

```
red_adentro_normal    | ok | V=18280.00      red_abierta_y15            | ok | V=16408.00
red_adentro_invertir  | ok | V=18280.00      red_abierta_y15_invertir   | ok | V=16408.00
```

18280 = 17344 + 36·13·2: la red siempre iba a la pared de enfrente (a 13 mm), con y sin invertir. La otra pared está a 23, así que invertida tenía que dar 17344 + 36·23·2 = **19000**.

**Qué cambié** — `clon/omnicad/timeline/ops_solido.py:287` (`OpRed.ejecutar`): se deja de negar la normal y se baja el `invertir` del `PARAMS`, que `red()` ya recibía sin ningún llamador.

```python
forma = _sc().red(cuerpo.forma, aristas, plano.normal, ctx.evaluar(self.p["espesor"]), prof,
                  direccion=self.p["direccion"], invertir=self.p["invertir"], extender=self.p["extender"],
                  angulo_desmoldeo=ctx.evaluar(self.p["angulo_desmoldeo"], ANGULO))
```

Antes la normal negada entraba en `_sentido_hacia_cuerpo`, que prueba `(-n, n)` y elige la que choca antes: la negación se deshacía sola y el botón no movía nada (solo cambiaba el lado de «Un lado», porque de ahí sale `s`).

**El arreglo de la revisión** (regla 3; detalle abajo) — `clon/omnicad/nucleo/solidos_crear.py:1387` (`_sentido_hacia_cuerpo`): con `invertir` devuelve el sentido contrario **sin mirar si ese lado tiene cara**, así que la red invertida hacia la boca abierta terminaba recortada contra la caja del cuerpo (+1080 mm³ colgando, el mismo recorte de B-213). Ahora, con `exigir_cara` (Al siguiente; con «Distancia» no, porque ahí la banda al aire es el resultado pedido), avisa:

```python
    opuesto = -mejor[1]
    if exigir_cara and not [h for h in _rayo(cuerpo, medio, opuesto) if h > 1e-7]:
        raise geo.ErrorGeometria("El sentido invertido no llega al cuerpo: desactivá «Cambiar dirección»"
                                 " o mové el boceto.")
    return opuesto
```

Con esto se cumple la segunda mitad de la fila («con la boca abierta, Fusion avisaría») y cae de paso el primer síntoma de **B-213**: el Nervio invertido hacia afuera, que antes rellenaba hasta la caja (+1950 → 27450 mm³), ahora da el aviso. B-213 sigue abierto con lo demás (medido hoy: `nervio_borde_simetrico` 26100, `nervio_borde_lado1` «la curva queda dentro del cuerpo», `nervio_espesor_enorme` 61500).

**Gemelos revisados** (regla 1; `grep -rn "invertir" clon/omnicad` filtrado por nervio/red, `grep -rn "plano.normal"`, `grep -rn "nervio\|red" clon/omnicad/nucleo/omnikernel/`):

| Gemelo | Regla hoy | Qué hice |
|---|---|---|
| `timeline/ops_solido.py:287` `OpRed` | negaba la normal | **arreglado** (pasa `invertir`) |
| `nucleo/solidos_crear.py:1488` `red(invertir=)` | el parámetro existía sin llamador | ahora tiene llamador; sin cambio en su firma |
| `nucleo/solidos_crear.py:1387` `_sentido_hacia_cuerpo` | invertía sin mirar la cara | **arreglado** (el aviso nuevo, con `exigir_cara`) |
| `nucleo/solidos_crear.py:1449` `nervio(invertir=)` | usa el mismo helper | cubierto por el arreglo del helper; medido: `nervio_invertir` pasa de 27450 a avisar |
| `api/herramientas_solido_extra.py:161` `_nervio` | ya pasaba `invertir=reverse` a las dos operaciones | sin cambio de código; texto de `create_web` › `reverse` («invertía la normal usada por el comando Red» → «invierte el sentido de extrusión… va a la otra pared») y regenerado `docs/agentes/herramientas.md` (1 línea) |
| `ui/comandos/crear.py:312` `Alternar("invertir", "Cambiar dirección")` | el mismo campo para Nervio y Red | sin cambio |
| `ui/comandos/asas_extra.py:295` `_asas_nervio` | la flecha de «Distancia» se dibuja sobre `normal × (−1 si invertir)`, no sobre el sentido que eligió el núcleo | revisado con medición (`evidencias/ui_2026-11-06/sonda_asas_red.py`) y **no lo toco**: es otro bug → fila nueva **B-219** |
| `nucleo/plastico.py` | sin geometría de Nervio/Red (la regla de plástico es H-87 / H-100 / H-102); PLÁSTICO abre los mismos `OpNervio`/`OpRed` | no aplica; la pieza verifica los botones de PLÁSTICO |
| `nucleo/omnikernel/` | `grep "nervio\|def red"` → nada | no aplica |
| la previa (`ui/comando.py`) | la del Nervio y la Red corre la operación (`_previa_pesada`), no una regla copiada | cubierta sin cambio |
| `edit_feature` (`api/herramientas_documento.py`) | recalcula el paso con el mismo `ejecutar` | cubierto |
| `timeline/ops_superficie.py`, `nucleo/superficies.py` | Superficie no tiene Nervio ni Red (índice `fusion-patch`, visto en la auditoría) | no aplica |
| `nucleo/analisis.py:1294` (`-plano.normal if invertir`) | es «Voltear» del corte de sección | otro comando; sin cambio |

**Tests nuevos y su salida.** `tests/test_sol10_nervio_red.py::test_red_invertir_cambia_de_pared` (parametrizado 18280 / 19000, con la caja `y` de la red cortada contra el cuerpo antes) y `::test_red_invertir_hacia_la_boca_abierta_avisa` (16408 sin invertir; invertida, aviso y el documento intacto).

ROJO antes del arreglo:

```
$ pytest tests/test_sol10_nervio_red.py -q -p no:cacheprovider -k "invertir"
E   assert 18279.999999999993 == 19000.0 ± 1.9
E     comparison failed
E     Obtained: 18279.999999999993
E     Expected: 19000.0 ± 1.9
FAILED tests/test_sol10_nervio_red.py::test_red_invertir_cambia_de_pared[True-19000.0]
1 failed, 1 passed, 10 deselected in 1.36s
```

ROJO del arreglo de la revisión (con el chequeo nuevo desactivado un momento, `if False and exigir_cara …`):

```
$ pytest tests/test_sol10_nervio_red.py -q -p no:cacheprovider -k "invertir"
E   AssertionError: {'ok': True, 'result': {'feature': {'id': 'op5', 'name': 'Red1', 'type': 'red'},
    'bodies_modified': [{'id': 'op1.c1', 'name': 'Cuerpo1', 'volume': 15832.0, 'previous_volume': 14752.0}], ...}}
1 failed, 2 passed, 12 deselected in 1.71s
```

O sea: `ok` con una placa de 1080 mm³ colgando de la boca abierta, en vez del aviso.

VERDE después: `3 passed, 12 deselected` (los dos de invertir y el control), y los grupos completos de la tabla de abajo.

### B-214 · Nervio con dos curvas sueltas — **Resuelto**

**Qué dice la ayuda de Fusion**: `Rib reference` dice «Select an open sketch profile» (uno), pero la imagen de «Create a rib» (`fusion_docs.py ver "Create a rib" -s fusion-model`, recurso `34082c91a878d5eec1ea.png`, mirada con Read) muestra **cuatro curvas sueltas en un boceto y sus cuatro nervios en un solo paso**. La Red ya lo hacía: `red()` recorre `_cadenas` (`nucleo/solidos_crear.py:1496`).

**Qué cambié** — `clon/omnicad/nucleo/solidos_crear.py:1449` (`nervio`): sale el `_alambre` (que exigía una sola cadena y daba el mensaje de Barrido) y entra el mismo recorrido de `red()`: por cada cadena se saca su cuerda, su sentido hacia el cuerpo (`_sentido_hacia_cuerpo`, con su `invertir`) y su desmoldeo; las brutas se unen y se recortan contra el cuerpo una vez, con **todas** las cadenas como referencia de «tocan la curva». La validación de `direccion` subió antes del bucle (el mismo mensaje, sin calcular geometría para nada). Con una sola cadena el camino es idéntico al de antes: `_unir([x])` devuelve `x` sin unificar.

**Gemelos revisados** (regla 1; `grep -rn "_alambre(\|_cadenas(" clon/omnicad`, `grep -rn "nervio" clon/omnicad/api clon/omnicad/ui clon/omnicad/timeline`):

| Gemelo | Qué hice |
|---|---|
| `nucleo/solidos_crear.py:1488` `red()` | ya recorría `_cadenas`: de acá saqué la regla; sin cambio |
| `nucleo/solidos_crear.py:1449` `nervio()` | **arreglado** |
| `_alambre` (`nucleo/solidos_crear.py:213`) | sigue en la ruta del Barrido y la Tubería (`:907`, `:941`) y en las secciones del Solevado (`:1001`, `:1030`, `:1221`): ahí sí hay UNA cadena; sin cambio |
| `timeline/ops_solido.py:261` `OpNervio.ejecutar` | `_aristas` (`:61`) devuelve la lista plana de aristas elegidas y ya las mandaba todas; sin cambio |
| `ui/comandos/crear.py:303` `Seleccion("curvas", "Perfil", …, maximo=None)` | ya permitía varias curvas; sin cambio. `Nervio.AYUDA`: «una curva» → «una o varias curvas» |
| `api/herramientas_solido_extra.py:174` `_curvas` | ya pasa todas las curvas del boceto (o las `curves` dadas); sin cambio de código ni de texto (`curves` ya decía «ids de curvas») |
| `nucleo/plastico.py`, `nucleo/omnikernel/` | sin geometría de nervio propia (los botones de PLÁSTICO abren el mismo comando) | no aplica |
| la previa y `edit_feature` | corren la operación | cubiertos sin cambio |
| `timeline/ops_superficie.py` | no hay Nervio de superficie | no aplica |

**Tests nuevos y su salida.** `tests/test_solidos_crear.py::test_nervio_con_dos_curvas_sueltas_hace_un_nervio_por_curva` (en el canal en U, dos líneas sueltas sin alargar = 2 × 5·6·2 = 120 mm³ y la cuenta cuadra con la unión de los dos nervios por separado; más dos guardas: dos aristas encadenadas siguen siendo UN perfil con su caja exacta, y una circunferencia cerrada sigue con «necesita una curva abierta») y `tests/test_sol10_nervio_red.py::test_nervio_con_varias_curvas_sueltas_hace_un_nervio_por_curva` (escuadra de la auditoría, parametrizado con una y con dos líneas: 26700 mm³ y **un** paso de tipo `nervio`).

ROJO antes del arreglo:

```
$ pytest tests/test_solidos_crear.py -q -p no:cacheprovider -k "dos_curvas_sueltas"
E           omnicad.nucleo.geometria.ErrorGeometria: La ruta debe ser una sola cadena continua de aristas.
FAILED tests/test_solidos_crear.py::test_nervio_con_dos_curvas_sueltas_hace_un_nervio_por_curva
1 failed, 65 deselected in 1.28s

$ pytest tests/test_sol10_nervio_red.py -q -p no:cacheprovider -k "varias_curvas"
E       AssertionError: {'ok': False, 'error_kind': 'OPERATION_FAILED', 'mensaje': 'El paso «Nervio1» (op4) falló y se
    deshizo (el documento quedó como estaba): …'}
FAILED tests/test_sol10_nervio_red.py::test_nervio_con_varias_curvas_sueltas_hace_un_nervio_por_curva[lineas1]
1 failed, 1 passed, 12 deselected in 1.37s
```

El `1 passed` de la segunda corrida es la parametrización de una sola curva: el control de que no rompí el caso que ya andaba.

VERDE después: `16 passed, 64 deselected in 4.02s` (todos los tests con la palabra `nervio` en los dos archivos) y los grupos de abajo.

### `/ponytail-review` (salida completa, sobre el diff de los cinco archivos)

`What this change does:` dos reglas de una línea cada una. La Red deja de «invertir» negando la normal del plano —que el núcleo deshacía al elegir la pared más cercana— y baja el `invertir` que su núcleo ya tenía; y el Nervio deja de exigir una sola cadena continua, haciendo un nervio por curva como su gemelo la Red. Además el sentido invertido, cuando del otro lado no hay cara, avisa en vez de dejar una placa recortada contra la caja del cuerpo. Carga esperada: una persona o un agente sobre un documento (el criterio del repo); nada de esto corre en un bucle, y el recorrido extra es una ray-cast por cadena.

**Must fix:** nada.

**Should fix:**

1. **El sentido invertido no mira si del otro lado hay cara** (`nucleo/solidos_crear.py:1387`)
   - **What this is:** `_sentido_hacia_cuerpo` elige el sentido que choca antes con el cuerpo y, con `invertir`, devuelve el contrario.
   - **Problem:** Si el otro lado no toca nada (la caja abierta hacia ese lado), la placa igual se arma y `_hasta_el_cuerpo` la recorta contra la caja del cuerpo: `red_abierta_y15_invertir` daba 15832 mm³, una placa de 1080 mm³ colgando de la boca, sin aviso. Con el botón roto (antes de este arreglo) nadie llegaba a ese caso.
   - **Fix:** un ray-cast más sobre el sentido elegido: si no da con ninguna cara, `ErrorGeometria` claro. Solo con «Al siguiente» (`exigir_cara=profundidad is None`), porque con «Distancia» la banda al aire es el resultado pedido. Cuatro líneas en el compartido, cubre Nervio y Red.
   - **If we skip it:** El botón nuevo hace geometría muda; es el mismo fallo que B-213 pero alcanzable desde ya.
   - **Arreglé:** sí, con su test (`test_red_invertir_hacia_la_boca_abierta_avisa`) y su salida ROJA tomada revirtiendo el cambio.

2. **La flecha de «Distancia» del Nervio y la Red no sigue el sentido que eligió el núcleo** (`ui/comandos/asas_extra.py:295`)
   - **What this is:** Con «Distancia», el diálogo dibuja un asa sobre `normal del plano × (−1 si invertir)`.
   - **Problem:** Medido (`evidencias/ui_2026-11-06/sonda_asas_red.py`): caja 40³ cerrada, boceto en y = 30 (paredes a 8 y a 28) → la red crece hacia +Y y la flecha apunta −Y, con y sin invertir (MISMATCH en los dos). En el Nervio la flecha es perpendicular al crecimiento, que va dentro del plano del boceto.
   - **Fix:** **no lo hice**: pide resolver el cuerpo objetivo y el sentido real en el camino de las asas (que corre con cada movimiento del mouse), o sea la referencia del «Cuerpo» más una ray-cast en la UI — otro bug, otro día.
   - **If we skip it:** La ventana ofrece un arrastre cuya dirección miente; lo pide la regla de honestidad del repo.
   - **Fila nueva:** **B-219** en `docs/seguimiento/bugs.md` (Abierto, Baja) con la reproducción medida. B-218 no lo usé: está tomado en `codebuddy-nocturna` (`64eb920`).

**Nice to have:**

3. **`nervio` validaba `direccion` después de prismatizar la curva** (`nucleo/solidos_crear.py:1455`)
   - **What this is:** El chequeo «Dirección de espesor desconocida» estaba en el medio del cálculo.
   - **Problem:** Con un `direccion` inválido se armaba el prisma entero para tirarlo después.
   - **Fix:** subirlo antes del bucle. Mismo mensaje, menos trabajo.
   - **If we skip it:** Nada grave; solo geometría de más en un caso que no anda.
   - **Arreglé:** sí, incluido en el cambio de B-214.

**Verdict: Ship** (con el ítem 1 ya arreglado y el 2 derivado a B-219).

### Verificación

`ruff check .` desde `clon/`: `All checks passed!` (antes y después del arreglo de la revisión).

Tests: todos con `turno`, `-p no:cacheprovider`, en primer plano y de a un grupo (la lista obligatoria de la tanda más los archivos que da `grep -l` de lo tocado: `nervio`, `red`, `_sentido_hacia_cuerpo`, `_cadenas`, `OpNervio`, `OpRed`, `create_rib`, `create_web`; `_alambre` y `_hasta_el_cuerpo` no aparecen en ningún test por su nombre). Ninguna corrida cortada por tiempo:

| Grupo | Archivos | Salida final |
|---|---|---|
| 1 · núcleo y plástico | test_solidos_crear, test_sol10_nervio_red, test_sol21_reglas_plastico | `84 passed in 39.52s` |
| 2 · API | test_api_solido, test_api_solido_extra, test_cobertura_ui_api, test_herramientas_solido, test_sol27_preajustes | `630 passed in 105.83s (0:01:45)` |
| 3 · diálogos, asas y lotes | test_comandos, test_manipuladores, test_iconos_extra, test_revision_lotes_sol | `278 passed in 10.16s` |
| 4 · tras el arreglo de la revisión (núcleo) | test_sol10_nervio_red, test_solidos_crear | `81 passed in 58.89s` |
| 5 · tras el arreglo (API + UI + plástico juntos) | los 10 archivos de los grupos 2 y 3 más test_sol21_reglas_plastico | `912 passed in 114.77s (0:01:54)` |
| 6 · seguimiento y doc | test_seguimiento, test_doc_agentes, test_claves_comandos, test_api_catalogo, test_api_convenciones | `479 passed in 12.23s` |

Suite completa y prueba de humo: no corridas (regla 10; las toma el coordinador).

Sondas de la auditoría, corridas de nuevo (`../evidencias/ui_2026-11-05/sondas_nrr.py`, contra su `.txt` del 2026-11-05):

| Caso | Antes | Después |
|---|---|---|
| `nervio_dos_curvas_sueltas` | ERR «La ruta debe ser una sola cadena…» | ok 26700 |
| `nervio_base` / `nervio_polilinea` | 26700 / 26700 | 26700 / 26700 (sin cambio) |
| `nervio_invertir` | ok 27450 (+1950 hasta la caja) | ERR «El sentido invertido no llega al cuerpo…» |
| `nervio_invertir_prof` (Distancia 5) | ok 26041,67 | ok 26041,67 (sin cambio: con «Distancia» no se exige cara) |
| `nervio_borde_simetrico` / `_lado1` / `_lado2` | 26100 / ERR / 26700 | iguales (B-213 sigue) |
| `nervio_espesor_enorme` | ok 61500 | ok 61500 (B-213 sigue) |
| `red_adentro_normal` / `red_adentro_invertir` | 18280 / 18280 | **18280 / 19000** |
| `red_abierta_y15` / `red_abierta_y15_invertir` | 16408 / 16408 | 16408 / **ERR con aviso claro** |
| `red_invertir_sin_cara` | ok 20072 | ERR con el mismo aviso |
| `red_base`, `red_sin_extender`, `red_profundidad`, `red_lado1`, `red_lado2`, `red_empalme`, `red_desmoldeo` | 20072, 17640, 16152, 20072, 20072, 20197,61, 23411,72 | iguales |

Ventana (regla 9, porque cambió el comportamiento de los diálogos de Nervio y Red y toqué el texto del comando): la pieza `nervio_red_repujado` en minimizada, con `PYTHONIOENCODING=utf-8` y `--plazo 2700` (la primera corrida, sin el `PYTHONIOENCODING`, se cortaba imprimiendo el `✗` con cp1252):

```
=== 84 comprobaciones, 6 con ✗ ===
```

En la auditoría eran 82 comprobaciones con 9 ✗. Pasaron los checks de esta tanda y el de B-213 que dependía del mismo botón:

```
[OK ] · Nervio con dos curvas sueltas: vista previa
[OK ] · Nervio con dos curvas sueltas: aceptar — cambiados={'op1.c1': ('solido', 26700.0)}
[OK ] · Nervio con dos curvas sueltas: deshacer vuelve al estado anterior (1 paso/s)
[OK ] · Nervio invertido: se rechaza con un aviso claro — «⚠ El sentido invertido no llega al cuerpo: desactivá «Cambiar dirección» o mové el boceto.»
[OK ] · Red dentro de la caja: resultado = 1656 — obtenido 1656.0
[OK ] · Red invertida hacia la boca abierta: se rechaza con un aviso claro — «⚠ El sentido invertido no llega al cuerpo…»
```

(84 vs 82: el caso de las dos curvas ahora corre y suma sus checks de aceptar y deshacer, que antes se cortaban en la previa.)

Las 6 ✗ que quedan son ítems ya anotados, ninguno de esta tanda: B-215 (2: desmoldeo −1° y 1° con extracción), H-95 (el Nervio no tiene Radio del empalme), B-217 (cadena tangente 437,12), H-99 (profundidad negativa no pasa el Efecto a Grabado) y H-97 (asas de alineación del Repujado).

Capturas miradas con Read: `capturas/red_invertida.png` (el panel RED con «Cambiar dirección» activo, el aviso visible y el cuerpo intacto) y `capturas/red_caja.png`. Evidencia: `evidencias/ui_2026-11-06/nervio_red_repujado.log` y `.json`, y la sonda `evidencias/ui_2026-11-06/sonda_asas_red.py`.

### Seguimiento

- `docs/seguimiento/bugs.md`: borradas la fila y la sección «Detalle» de B-216 y de B-214; recuento del encabezado 23 → 22 (Abierto 19 → 18, con la fila nueva B-219 · Parcial 4).
- B-213: actualizado. Su primer síntoma («invertido rellena hasta la caja, +1950») ya avisa, medido; quedan el borde (+600 y el error falso de un lado), el `thickness=1e6` y la Red delante de la caja. Su `archivo:línea` pasó a `solidos_crear.py:1419` (`_hasta_el_cuerpo`), que es donde está ahora.
- Fila nueva **B-219** (con su ficha de «Detalle»): la flecha de «Distancia» del Nervio y la Red, ítem 2 de mi `ponytail-review`.
- `docs/seguimiento/README.md`: no tenía filas de B-214 ni B-216 (`grep -n "B-214\|B-216"` → nada), así que no había qué borrar.
- `README.md` y `README.en.md` (hoja de ruta): sin mención de estos bugs ni de Nervio/Red (`grep` → nada); no se tocaron.
- Dos viñetas en «## Registro» de `PROJECT_LOG.md` y una lección en «## Lecciones aprendidas» (parámetro del núcleo sin llamador = botón roto).

### Archivos fuera de mi tanda

La tabla de la tanda 2 lista `nucleo/solidos_crear.py` y `timeline/ops_solido.py`. También toqué, una línea de texto en cada uno: `api/herramientas_solido_extra.py` (el `reverse` de `create_web` decía «invertir la normal usada por el comando Red», que era la descripción del botón roto) con su regeneración de `docs/agentes/herramientas.md`, y `ui/comandos/crear.py` (la ayuda del comando Nervio decía «una curva»). No se tocó `ui/comandos/asas_extra.py` (de ahí B-219) ni `nucleo/plastico.py` (sin geometría de Nervio/Red). `docs/corrida_nocturna_2026-11-05.md` aparece modificado en el árbol: es de otra corrida, no lo miré ni lo cambié.

### Lo que no pude verificar

- ⚠ **Fusion real no se abrió.** La regla del Flip sale del texto de la ayuda («Flips the direction in which the web feature is extruded») y la de varias curvas de la imagen de «Create a rib» (leída con Read: cuatro curvas, cuatro nervios). No se comparó con el programa: si Fusion en la boca abierta hiciera otra cosa que avisar (por ejemplo ir igual a la cara más lejana del sólido), el aviso nuevo vuelve a ser una línea en `_sentido_hacia_cuerpo`.
- ⚠ **El asa de «Distancia» no se probó arrastrándola** con el nuevo sentido: ese arreglo quedó derivado a B-219 y la pieza solo teclea «Cambiar dirección»; sus checks de arrastre (`red › arrastrar «profundidad» 3 mm`) pasaron porque miden el valor, no la dirección de la flecha.
- ⚠ **Desmoldeo + varias curvas**: cada cadena toma su propio `m` para el `pull` del desmoldeo, que es la única lectura razonable, pero no hay test que lo mida — el desmoldeo del Nervio con ángulo negativo o extracción que no coincide sigue roto (B-215, para Opus).
- ⚠ **Nervio con curvas de dos bocetos distintos**: `OpNervio` usa el plano del primer boceto (`timeline/ops_solido.py:262`); con varias cadenas de bocetos de planos diferentes no lo probé (la Red ya aceptaba varias cadenas y tiene la misma regla, así que no es un cambio mío).
- ⚠ **Proyectos guardados con una Red invertida**: antes daban la misma red que sin invertir; ahora pueden dar el aviso nuevo (boca abierta) o la otra pared (caja cerrada). En `ejemplos/` no hay recetas de nervio ni red (`grep -rln "nervio\|red" ejemplos/` → nada), pero una pieza del usuario puede cambiar de forma al abrir.
- ⚠ **B-213 sigue abierto** y es vecino directo: el recorte contra la caja del cuerpo aparece en los dos caminos que arreglé (el invertido sin cara lo esquivé con el aviso; el `thickness=1e6` y el boceto en el borde quedan).

## Prompt para el agente

Entregado el 2026-11-05. Modelo sugerido: Qwen Flash en OpenCode, esfuerzo Extra High (1M de contexto). Versión: Qwen3.8-Flash. Se pega con el número de tanda.

```text
TANDA = (el número que te dio Gerardo: 1, 2, 3, 4 o 5)

PASO 0 (obligatorio, antes de leer código): invocá con la herramienta skill /fable-method y /ponytail. Usá también /plan-then-do, /tool-calling-guard y /verify-before-commit. Al final, /ponytail-review. Si una skill no existe, seguí igual las reglas de abajo.

PROYECTO
OmniCAD: CAD 3D paramétrico en Python (PySide6 + OpenCascade vía cadquery-ocp) que copia Fusion 360. Repo D:\PROGRAMA, código en clon/. Leé AGENTS.md antes de tocar código. Todo en español. Unidades: mm y grados.

QUÉ HACER
Leé docs/arreglos_qwen.md, fila de tu TANDA en la tabla «Tandas». Arreglá esos dos bugs o mejoras, DE A UNO: terminás y verificás el primero antes de empezar el segundo. El detalle de cada uno está en docs/seguimiento/bugs.md o mejoras.md (fila y sección «Detalle»: causa probable con archivo:línea y prueba propuesta) y en el informe de la auditoría que lo encontró.

REGLAS QUE TENÉS QUE CUMPLIR (en tu corrida anterior fallaste en las tres primeras)
1. GEMELOS ANTES DE EDITAR. Antes de cambiar una regla o un cálculo, buscá dónde más se calcula lo mismo: la previa rápida (ui/comando.py, nucleo/previa*), la versión de superficie (timeline/ops_superficie.py, nucleo/superficies.py), OmniKernel (nucleo/omnikernel/), la API (clon/omnicad/api/) y la columna «Gemelos a revisar» de tu tanda. Usá grep con el nombre de la función y de los parámetros. Escribí la lista de gemelos en el informe y cambiá todos los que correspondan. La vez pasada cambiaste el núcleo y no la previa: se rompieron 3 tests.
2. TESTS: LA LISTA ENTERA, NO LOS QUE ELIJAS. Corré los «Tests obligatorios» de tu tanda MÁS todos los archivos que salen de: grep -l "<cada función que tocaste>" clon/tests/test_*.py. Desde clon/, siempre con turno y en grupos que terminen en menos de 900 s:
   .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe -m pytest <archivos> -q -p no:cacheprovider
   Si turno corta por tiempo, partí el grupo y seguí: no cuenta como verde.
3. TU REVIEW SE ARREGLA. Todo lo que /ponytail-review marque como «Must fix» o «Should fix» lo arreglás antes de cerrar (y volvés a correr los tests). Solo puede quedar sin arreglar lo que sea otro bug: entonces fila nueva en docs/seguimiento/ con el siguiente ID libre.
4. TEST ROJO PRIMERO. Para cada bug: escribí el test de la «Prueba propuesta», corrélo y pegá que FALLA; recién ahí arreglá y pegá que PASA.
5. Antes de decidir cómo debe comportarse algo, leé la ayuda oficial de Fusion: clon/.venv/Scripts/python.exe scripts/fusion_docs.py buscar <palabras> -s fusion-model (o -s fusion-patch para superficie) y ver "<título>" -s <carpeta>. No adivines.
6. Si la geometría (OpenCascade) se pone dudosa o no sale en dos intentos, PARÁ: dejá la fila en «Parcial» con lo que falta y explicalo. No inventes.
7. Tocá solo lo necesario para tus dos bugs. Nada de git stash, git checkout ni git reset. No commitees ni hagas push. Si necesitás cambiar un archivo que no es de tu tanda, decilo en el informe.
8. Toda opción o comportamiento que cambie en la ventana tiene que quedar igual en el MCP y la CLI (clon/omnicad/api/, receta C de AGENTS.md); si cambia una firma, regenerá docs/agentes/herramientas.md con: omnicad tools --markdown --output docs/agentes/herramientas.md
9. Si tocaste la ventana: .venv/Scripts/python.exe ../scripts/prueba_ui/todo.py <pieza> --ventana minimizada (la pieza de tu tanda) y mirá la captura con Read.
10. NO corras la suite completa ni la prueba de humo: las corre el coordinador.

AL RESOLVER CADA BUG
Borrá su fila de docs/seguimiento/bugs.md (o mejoras.md), su sección «Detalle» y su ID en las tablas de docs/seguimiento/README.md. Sumá una viñeta en «## Registro» de PROJECT_LOG.md: «2026-11-05 · <ID> (OpenCode con Qwen3.8-Flash)» con qué cambiaste y el test que lo cubre. Si queda a medias: fila en «Parcial» con lo que falta.

INFORME (obligatorio)
En docs/arreglos_qwen.md, una sección «## Informe tanda <N>» ARRIBA de «## Prompt para el agente» (no borres el prompt ni la tabla), con:
- por cada bug: estado (Resuelto / Parcial / No), qué dice la ayuda de Fusion, qué cambiaste (archivo:línea), la lista de gemelos que revisaste y qué hiciste con cada uno, el test nuevo con su salida ROJA antes y VERDE después;
- la salida real de ruff check . y de cada grupo de tests (la línea final «N passed»);
- la salida completa de /ponytail-review y qué arreglaste de ella;
- lo que no pudiste verificar, con ⚠.
```
