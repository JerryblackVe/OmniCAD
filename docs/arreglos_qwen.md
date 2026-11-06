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
| C9 | H-85 | `ui/comandos/superficie.py` (~19, el filtro `CURVAS` de Extruir de superficie) | el filtro de Extruir sólido (`ui/comandos/solido.py`, ya elige perfiles y caras planas: copiar ese criterio), la API `create_surface_extrude` (ya los acepta), la previa | `test_superficies.py`, `test_superficie_fusion.py`, `test_api_superficie.py`, `test_comandos_superficie.py`, `test_cobertura_ui_api.py`, pieza `extruir_espacios` |
| C10 | H-104 | `ui/comandos/superficie.py` (el filtro de Revolución de superficie) | `PERFILES_SUPERFICIE` de C9 (reusarlo), Revolución sólida, la API `create_surface_revolve`, la previa | `test_comandos_superficie.py`, `test_superficies.py`, `test_superficie_fusion.py`, `test_api_superficie.py`, `test_sol07_revolucion.py`, `test_cobertura_ui_api.py` |
| C11 | CF-8 (solo dos opciones: «barra espaciadora repite el último comando» y «tamaño del ViewCube»; la fila queda Parcial con el resto) | `ui/preferencias.py`, `ui/ventana.py` (atajo), el ViewCube del visor | la ayuda de Fusion (`fusion_docs.py buscar preferences general -s fusion-getstarted`), las herramientas del MCP de preferencias (`get_preferences`, `set_preference`: que las dos opciones nuevas estén ahí), el guardado de preferencias | `test_preferencias*.py`, `test_api_*preferenc*.py` (los que existan), `test_cobertura_ui_api.py`, `test_comandos.py`, `test_doc_agentes.py` |

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

## Informe tanda 3

Corrida del 2026-11-06. OpenCode con Qwen3.8-Flash en Qoder. Bugs: B-217 y B-209, de a uno y en ese orden.

### B-217 · Repujado con «Cadena tangente» repuja también en los costados — **Resuelto**

**Qué dice la ayuda de Fusion** (`fusion_docs.py buscar "Emboss"` → `contenido/fusion-model/emboss-reference-a3f0ac82148.md`):

> ## Tangent Chain
> Check to automatically select tangentially connected geometry.

y en `emboss-a-solid-body`: «Uncheck **Tangent Chain** if you don't want to automatically select tangentially connected geometry.» La ayuda no dice que el perfil se copie en esas caras; lo que rige en OmniCAD para las caras elegidas es la proyección («cada cara recibe solo la parte que le cae encima»), y la auditoría dejó anotada la única diferencia deliberada: «REP · cara perpendicular al boceto: OmniCAD «adapta» el perfil (decisión del 2026-10-13 en PROJECT_LOG); Fusion lo proyecta». ⚠ Fusion real no se abrió.

**Estado del código antes de decidir** (medido con `../evidencias/ui_2026-11-06/sonda_tanda3.py`; placa 60×40×10 con las cuatro aristas de arriba empalmadas r 3, cuadro 10×10 en el centro de la tapa, relieve 1 mm):

```
placa: 23624.07  caras tangentes de la tapa: 9        (tapa + 4 empalmes + 4 costados)
cadena_tangente=False: +100.00  caja [20,15,10]..[30,25,11]
cadena_tangente=True:  +437.12  caja [-1,-1,0.35]..[61,41,11]
```

El 437,12 de la fila salió tal cual. Al desglosarlo por tipo de cara (`sonda_b217_caras.py`) apareció **más de lo que decía la fila**: no eran solo los cuatro costados adaptados; los cuatro empalmes cilíndricos también recibían material (+278,36 con los costados ya descartados), porque el envoltorio le da vueltas al cilindro (empalme izquierdo, a 19 mm del cuadro: +39,71). La regla había que escribirla antes de las dos ramas, no en una.

**INTENT:** el código adaptaba/envolvió el perfil en TODAS las caras de la cadena y sumaba 437,12 mm³; la fila B-217 y su prueba propuesta piden +100 mm³ y la caja sin crecer; la decisión documentada del 2026-10-13 (`PROJECT_LOG.md` › «Repujado en varias caras a la vez», y sus tests `test_repujado_en_varias_caras_a_la_vez_adaptandose_a_cada_una` / `test_repujado_adaptado_se_achica_si_no_entra_en_la_cara`) dice que una cara **elegida a mano** perpendicular al perfil se adapta. Los dos conviven: la regla nueva alcanza solo a las caras que agregó la cadena.

**Qué cambié** — `clon/omnicad/nucleo/solidos_crear.py:1579-1597` (`repujado_en_cuerpos`, la expansión de la cadena):

```python
    for k, cara in enumerate(cadena):
        if k and not _cajas_se_tocan(_caja_2d([cara], pl_perfil), caja_perfil):
            continue
        if not any(j == i and cara.IsSame(otra) for j, otra in caras):
            caras.append((i, TopoDS.Face(cara)))
```

`k == 0` es la cara que el usuario eligió (sigue adaptando/envolviendo como hasta ahora); las demás son regaladas por la cadena y se descartan si su caja proyectada sobre el plano del perfil no toca la del perfil. Es la misma cuenta en 2D que usa el reparto entre caras paralelas dos líneas más abajo (`_caja_2d` / `_cajas_se_tocan`, en `_repujado_en_grupo`), así que cubre planas y cilíndricas con una sola regla sin tocar ninguna de las dos ramas. `pl_perfil` es el `geo.plano_de_cara(perfiles[0])` que la rama cilíndrica ya calculaba (subido, no duplicado). La lección del 2026-10-13 («misma regla para uno y para varios») se respeta: la regla no depende de cuántas caras hay ni de su tipo.

**Gemelos revisados** (regla 1; `grep -rn "cadena_tangente" clon/omnicad`, `grep -rn "caras_tangentes(" clon/omnicad`, `grep -rln "repuj\|emboss" clon/tests`):

| Gemelo | Regla hoy | Qué hice |
|---|---|---|
| `nucleo/solidos_crear.py:1551` `repujado_en_cuerpos` | adaptaba toda la cadena | **arreglado** (el filtro, un punto) |
| `_repujado_en_grupo` / `_perfiles_en_zona` (la adaptación) | gira, centra y achica | sin cambio: rige para las caras elegidas a mano (decisión 2026-10-13, tests verdes) |
| `_envolver_en_cilindro(..., recortar=cadena_tangente)` | la cadena sumaba cilindros lejos del perfil | el filtro los descarta antes de llegar; **su vuelta de más con una cara elegida a mano queda como fila nueva B-220** (medida) |
| `nucleo/solidos_crear.py:1542` `repujado` (la firma de un cuerpo) | pasa a `repujado_en_cuerpos` | cubierto por el mismo punto; sin cambio |
| `timeline/ops_solido.py:319` `OpRepujado` | baja `cadena_tangente` del `PARAMS` | sin cambio (ninguna clave nueva: la receta vieja abre igual) |
| `api/herramientas_solido_extra.py:230` `create_emboss` | «tangent_chain: true incluye las caras tangentes» | sigue siendo cierto (las incluye; reciben lo que cae) → **no se regenera** `docs/agentes/herramientas.md` |
| `ui/comandos/crear.py:363` Casilla «Cadena tangente» | mismo campo | sin cambio |
| `nucleo/calcomanias.py:43` (`encadenar` de la Calcomanía) | usa `caras_tangentes` | revisado y **no aplica**: proyecta la imagen con el marco UV de cada cara y la recorta contra esa cara; no adapta ni copia un perfil |
| `nucleo/solidos_modificar.py:1097` (Desmoldeo con cadena) y `:1385` (Reemplazar cara) | suman la cadena | **no aplica**: transforman las caras de la cadena, no reparten un perfil |
| `nucleo/omnikernel/` | `grep "repuj\|emboss"` → nada | no aplica (el otro motor no tiene Repujado) |
| la previa (`ui/comando.py`) | `tramo_previa` es del prisma de Extruir; el Repujado corre la operación | cubierta sin cambio |
| `edit_feature` (`api/herramientas_documento.py`) | recalcula el paso con el mismo `ejecutar` | cubierto |

**Test nuevo y su salida.** `tests/test_repujado_alineacion.py::test_cadena_tangente_no_copia_el_perfil_en_los_costados` (+100 exactos y la caja del material 10×10×1) y `tests/test_api_solido_extra.py::test_create_emboss_cadena_tangente_no_copia_el_perfil_en_los_costados` (la repro de la fila por la API: `create_box` 60×40×10, `fillet edges=">Z" radius=3`, `create_emboss ... tangent_chain=true`). Auxiliares del primer archivo: `_rectangulo` ahora toma coordenadas (con los valores de siempre por defecto) y se sumó `_aristas_en_z`.

ROJO antes del arreglo:

```
$ pytest tests/test_repujado_alineacion.py -q -p no:cacheprovider -k "cadena_tangente"
E   assert 437.1154520899279 == 100 ± 1.0e-04
1 failed, 1 passed, 13 deselected in 1.65s

$ pytest tests/test_api_solido_extra.py -q -p no:cacheprovider -k "cadena_tangente"
E   assert 24061.186141919094 == 23724.070689958793 ± 0.237241
1 failed, 44 deselected in 1.79s
```

El `1 passed` de la primera corrida es el control que ya existía (`test_cadena_tangente_agrega_el_empalme_sin_duplicar_caras`), y `24061,19 − 23724,07 = 337,12` del rojo por la API es el mismo exceso visto desde la otra capa.

VERDE después: `28 passed` con `-k "cadena or repujado or emboss"` sobre los tres archivos del área, y los grupos completos de la tabla abajo. Con la regla puesta a medias (solo para las caras planas) los dos tests nuevos Y el control viejo fallaban: ese fue el hallazgo que llevó a escribir la regla en la expansión de la cadena y no en cada rama.

### B-209 · Barrido sólido con «Estirar» hace «Escalar» — **Resuelto**

**Qué dice la ayuda de Fusion** (`fusion_docs.py ver "Sweep reference" -s fusion-model`):

> #### Stretch
> Stretch: use path - guide rail distance to scale profile in X

o sea: el perfil crece **solo hacia el carril** y conserva la otra dimensión. La propia auditoría ya decía el arreglo en su `ponytail-audit` (ítems 2 y 7 de `docs/auditoria_revolucion_barrido_solevacion.md`): «Reuse the surface `_estirar` path» y «Add `"estirar": "Estirar"` once finding 2 is done».

**Estado del código antes de decidir** (medido con la sonda de la auditoría, `evidencias/ui_2026-11-05/sonda_carril.py`: cuadrado 4×4 en YZ, ruta X 0..50, carril en XZ de (0, 2) a (50, 6)):

```
solido stretch: V=3364.59 caja y −6.44..6.44    <- idéntico a scale
superf stretch: A=1201.28 caja y −2.00..2.00, z −6..6    <- estira bien
solido scale: V=3364.59      solido none: V=784.03
```

La superficie ya lo resolvía con `_barrido_estirado` (`nucleo/superficies.py:630`: secciones deformadas en el plano perpendicular a la ruta, solevadas entre ellas); el sólido caía a la ley de escala de `MakePipeShell`, que es uniforme en las dos direcciones del perfil. El docstring de `barrer` lo contaba conforme: ««estirar» (escala en una sola dirección) no existe en OCC y se hace como «escalar»». No era cierto: el gemelo lo tenía hecho.

**Qué cambié** — `clon/omnicad/nucleo/superficies.py:630` y `:650` (el gemelo gana un parámetro, no una copia) y `clon/omnicad/nucleo/solidos_crear.py:821-831`:

```python
    if carril is not None:
        if abs(torsion) > 1e-9 or abs(conicidad) > 1e-9:
            raise geo.ErrorGeometria("La torsión y la inclinación no se combinan con un carril guía.")
        if escala_carril not in ("escalar", "estirar", "ninguna"):
            raise geo.ErrorGeometria(f"Escala de carril desconocida: {escala_carril}")
        if escala_carril == "estirar":
            from . import superficies as sfc        # Estirar: lo resuelven las secciones deformadas del gemelo
    ...
        if carril is not None and escala_carril == "estirar":
            partes.append(sfc._barrido_estirado([perfil], tramo, carril, solido=solido))
            continue
```

`_barrido_estirado` pasa `solido` a `BRepOffsetAPI_ThruSections(solido, False)`, que es quien tapa los extremos (el mismo primer argumento con el que `_loft` hace sólida la Solevación, `solidos_crear.py:1127`). Va en `_barrido_alambre` y no en `barrer` porque es el único punto por el que pasan el perfil exterior y cada agujero: con un perfil anillado el hueco se estira igual que su contorno y se corta después (test abajo: 80 − 20 = 60 mm³). Las validaciones del carril subieron antes del bucle de tramos (mismos mensajes, sin armar el `MakePipeShell` para tirarlo después).

**Gemelos revisados** (regla 1; `grep -rn "escala_carril\|_barrido_estirado\|carril=" clon/omnicad`):

| Gemelo | Regla hoy | Qué hice |
|---|---|---|
| `nucleo/solidos_crear.py:827-831` `_barrido_alambre` (el Barrido, `barrer(solido=False)` y cada agujero) | hacía escalar | **arreglado** (delega) |
| `nucleo/superficies.py:630` `_barrido_estirado` | firme, pero solo superficie | **arreglado** (`solido=`, por defecto `False`: la firma vieja sigue valiendo) |
| `nucleo/superficies.py:727` `barrer_superficie` con `escala="estirar"` | llama al estirado sin `solido` | sin cambio: idéntico (medido A=1201,28 antes y después) |
| `nucleo/superficies.py:728` (riel con escalar/ninguna → `sc.barrer(solido=False)`) | `escala_carril != "estirar"` | sin cambio (el estirar no llega) |
| `nucleo/solidos_crear.py:798` `_ley_escala_carril` | la escala uniforme | sigue para «escalar»; sin cambio |
| `nucleo/solidos_crear.py:2924` `tuberia` | `_barrido_alambre(w, None, …, "escalar", …)` | sin carril → no aplica |
| `nucleo/solidos_crear.py:937` `barrer_cuerpo` (Solid Sweep) | sin carril | no aplica |
| `timeline/ops_solido.py:129` `OpBarrido.OPCIONES` | ya tenía «estirar» | sin cambio (el `PARAMS` sigue en «escalar»: recetas viejas idénticas) |
| `timeline/ops_superficie.py:216` `OpSupBarrido` | ya lo tenía y la superficie ya estiraba | sin cambio |
| `ui/comandos/crear.py:75-78` (Barrido › Escala del perfil) | ofrecía solo Escalar/Ninguna | **arreglado**: «Estirar» con la misma ayuda que su par de superficie |
| `ui/comandos/superficie.py:150` | ofrece los tres | referencia del texto; sin cambio |
| `api/herramientas_solido.py:483` `sweep` (`rail_scale`) | mapea `stretch → "estirar"` y su texto no promete escalar | sin cambio de texto → no se regenera la doc |
| `api/herramientas_superficie.py:192` `create_surface_sweep` | `profile_scaling` ídem | sin cambio |
| `nucleo/omnikernel/` | `grep "barrer\|carril\|recortar"` → nada | no aplica |
| la previa rápida (`ui/comando.py::tramo_previa`) | es del prisma de Extruir | no aplica: el Barrido calcula la previa con el núcleo (lo confirman el test del diálogo y el check de la pieza) |
| `edit_feature` | recalcula el paso con el mismo `ejecutar` | cubierto por el arreglo del núcleo |

**Tests nuevos y su salida.** `tests/test_solidos_crear.py::test_barrido_carril_estirar_no_es_escalar` (carril abierto de 1 a 3 sobre ruta de 10: 80 mm³ con caja ±3/±1 — el trapecio de sección media 8 sobre 10 mm —, distinto de los 173,33 de Escalar, y el agujero 80 − 20), `tests/test_api_opciones_solido2.py::test_barrido_con_carril_estirar_no_es_escalar` (la repro de la fila: 1600 mm³ y caja [50, 4, 12] contra 3364,59 de `scale`) y `tests/test_comandos_crear.py::test_barrido_dialogo_estirar_hacia_el_carril` (la lista de opciones del diálogo + 1600 mm³ y 3364,59 por el comando).

ROJO antes del arreglo:

```
$ pytest tests/test_solidos_crear.py -q -p no:cacheprovider -k "estirar_no_es_escalar"
E   assert 173.29644426000885 == 80 ± 0.08
1 failed, 66 deselected in 0.98s

$ pytest tests/test_api_opciones_solido2.py::test_barrido_con_carril_estirar_no_es_escalar tests/test_comandos_crear.py::test_barrido_dialogo_estirar_hacia_el_carril -q
E   assert 3364.5884 == 1600 ± 1.6
E   AssertionError: assert ['escalar', 'ninguna'] == ['escalar', '...', 'ninguna']
2 failed in 1.91s
```

El 173,30 del primer rojo ES el volumen de Escalar en el mismo caso: la prueba de que el modo no existía. VERDE después: `5 passed` (los tres nuevos más los dos controles de carril que ya había) y los grupos completos de abajo.

### `/ponytail-review` (salida completa, sobre el diff de los tres archivos de código y cinco de test)

`What this change does:` dos reglas cortas. El Repujado con «Cadena tangente» ya no copia el perfil en las caras que agregó la cadena si el perfil no cae sobre ellas (decide la caja proyectada, y decide igual para planas y cilíndricas), y el «Estirar» del Barrido sólido pasa por las secciones deformadas de su gemelo de superficie en vez de por la escala uniforme de `MakePipeShell`, con su opción visible en el diálogo. Carga esperada: una persona o un agente sobre un documento (el criterio del repo); nada de esto corre en un bucle, y el filtro de la cadena cuesta una teselación por cara agregada — malla ya cacheada y que el reparto en 2D calculaba de todos modos.

**Must fix:** nada.

**Should fix:**

1. **La caja de la cadena se mide en el plano del primer perfil** (`nucleo/solidos_crear.py:1581-1584`)
   - **What this is:** `pl_perfil = geo.plano_de_cara(perfiles[0])` y `caja_perfil = _caja_2d(perfiles, pl_perfil)`; cada cara de la cadena se proyecta sobre ese plano y se descarta si no toca la caja.
   - **Problem:** Con perfiles de dos bocetos en planos distintos en el MISMO repujado, la caja de todos se mide en el plano del primero: un perfil lejano puede colarse o quedarse afuera.
   - **Fix:** un comentario `shortcut:` que nombra el límite y cuándo subir de nivel, no un cambio de comportamiento: el alineado (`_alinear_repujado`) y el envoltorio ya usan `perfiles[0]` como marco, así que la regla nueva no introduce la suposición, la hereda de lo que reutiliza.
   - **If we skip it:** Mañana alguien mezcla bocetos, la cadena filtra de más y no queda ninguna pista en el código.
   - **Arreglé:** sí, con el `shortcut:` (dos líneas de comentario sobre una de código).

2. **Envolver en un cilindro lejos del perfil pone material dando una vuelta de más** (`nucleo/solidos_crear.py`, `a_uv` dentro de `_envolver_en_cilindro`)
   - **What this is:** El envoltorio pasa la coordenada tangencial del perfil a ángulo: `u0 + giro · (distancia al eje)/radio`.
   - **Problem:** Medido (`evidencias/ui_2026-11-06/sonda_b217_caras.py` y por la API): en la placa empalmada con el cuadro en el centro, elegir a mano el empalme izquierdo (`create_emboss faces="Cuerpo1/F3" wrap=true depth=1`) da **+39,71 mm³** sobre ese empalme, 19 mm lejos del cuadro; los cuatro dan +287,14. 19 mm sobre un radio 3 son 6,7 rad: la lámina le da más de una vuelta al cilindro y el `recortar` contra la cara justo la recorta donde no debía. Con la cadena este caso ya no se alcanza (el filtro descarta esas caras), pero con la cara elegida a mano sigue ahí, y esa es la rama que la decisión de 2026-10-13 decidió conservar.
   - **Fix:** **no lo hice**: es otra regla (tope del arco envuelto, o recortar contra el prisma del perfil), en un camino que este bug no toca.
   - **If we skip it:** El usuario ve relieve al lado contrario de donde apuntó.
   - **Fila nueva:** **B-220** en `docs/seguimiento/bugs.md` (Abierto, Media) con su ficha y la medición.

3. **El `import` del gemelo estaba dentro del bucle de tramos** (`nucleo/solidos_crear.py:821-825`)
   - **What this is:** `from . import superficies as sfc` escrito dentro de `for tramo in rutas:`.
   - **Problem:** Se repite por tramo y queda en medio del cálculo; `superficies` hace exactamente lo mismo una sola vez arriba.
   - **Fix:** subirlo al bloque de validación del carril (mismo import diferido: ninguno de los dos módulos importa al otro a nivel de módulo, así que no hay ciclo).
   - **If we skip it:** Nada, solo lectura.
   - **Arreglé:** sí, antes de la verificación final.

**Arreglé de la revisión:** los ítems 1 y 3 (el `shortcut:` y el import subido), con el grupo de tests vuelto a correr después (`184 passed`). El ítem 2 sale de la tanda como B-220.

**Verdict: Ship** (con 1 y 3 ya aplicados y 2 derivado con fila).

### Verificación

`ruff check .` desde `clon/`: `All checks passed!` (antes y después del arreglo de la revisión).

Tests: todos con `turno`, `-p no:cacheprovider`, en primer plano y de a un grupo (la lista obligatoria de la tanda más los archivos que da `grep -l` de lo tocado: `barrer`, `barrer_superficie`, `repujado`, `repujado_en_cuerpos`, `caras_tangentes`, `escala_carril`, `Barrido`, `emboss`; `_barrido_alambre`, `_barrido_estirado`, `_caja_2d` y `_cajas_se_tocan` no aparecen en ningún test por su nombre). Ninguna corrida cortada por tiempo:

| Grupo | Archivos | Salida final |
|---|---|---|
| 1 · núcleo | test_solidos_crear, test_superficies, test_superficie_fusion, test_geometria, test_b52_espiral, test_bugs_solido, test_paridad_motor | `245 passed in 151.74s (0:02:31)` |
| 2 · barrido, riel y tubería | test_sol08_barrido, test_barrido_tipos, test_api_barrido, test_gizmo_barrido, test_sol08_ui, test_superficie_guias, test_tuberia_cadena, test_topes, test_sup29_encadenado_superficie, test_graficos_rendimiento, test_rosca_diametros_tabla | `267 passed in 79.40s (0:01:19)` |
| 3 · API sólido/superficie | test_api_solido, test_api_solido_extra, test_api_superficie, test_api_opciones_solido1, test_api_opciones_solido2, test_api_avanzado, test_herramientas_solido | `500 passed in 159.61s (0:02:39)` |
| 4a · diálogos y repujado | test_comandos, test_comandos_superficie, test_comandos_crear, test_repujado_alineacion | `51 passed in 8.51s` |
| 4b · asas, paneles y cobertura UI | test_manipuladores, test_b105_panel_chico, test_iconos_extra, test_comandos_inspeccionar, test_cobertura_ui_api | `625 passed in 8.42s` |
| 5a · previa y calcomanías | test_previa_aislada_comandos, test_previa_prisma, test_previa_trabajador, test_previa_vaciado_aislada, test_p23_calcomania | `112 passed in 251.22s (0:04:11)` |
| 5b · modificar, texto, plástico y lotes | test_solidos_modificar, test_texto_vectores, test_opciones_operaciones, test_resultados_vacios, test_referencias_mal_formadas, test_herramientas_solido, test_sup29_encadenado_superficie, test_sol21_reglas_plastico, test_revision_lotes_sol, test_cinta_plastico | `612 passed in 122.03s (0:02:02)` |
| 6 · tras el arreglo de la revisión | test_repujado_alineacion, test_solidos_crear, test_api_opciones_solido2, test_comandos_crear, test_superficie_guias | `184 passed in 54.67s` |
| 7 · seguimiento y doc (después de editar los tres docs) | test_seguimiento, test_doc_agentes, test_claves_comandos, test_api_documento, test_api_catalogo, test_api_convenciones | `510 passed in 18.43s` |

Suite completa y prueba de humo: no corridas (regla 10; las toma el coordinador).

Terminados `PROJECT_LOG.md`, `docs/seguimiento/bugs.md` y este informe, se volvieron a correr los tres archivos que leen esa documentación — `test_seguimiento.py`, `test_doc_agentes.py` y `test_claves_comandos.py` → `448 passed in 5.92s`, y `ruff check .` siguió `All checks passed!`.

Sondas de la auditoría, corridas de nuevo:

| Caso | Antes | Después |
|---|---|---|
| `sonda_carril.py` sólido stretch (carril 2→6) | V=3364,59, caja y ±6,44 | **V=1600,00, caja y ±2,00 / z −6..6** (la misma caja que su superficie) |
| `sonda_carril.py` sólido scale / none | 3364,59 / 784,03 | 3364,59 / 784,03 (sin cambio) |
| `sonda_carril.py` superficie stretch / scale / none | 1201,28 / 1667,89 / 797,57 mm² | iguales (sin cambio) |
| Repujado placa cadena=True (`sonda_tanda3.py`) | +437,12, caja −1..61 / −1..41 | **+100,00, caja 20..30 / 15..25** |
| Repujado placa cadena=False | +100,00 | +100,00 (control) |
| Cadena en la caja 40×30×10 con un empalme, perfil cruzando el borde | +54,51 (solo +16 sin cadena) | +54,51 idéntico: ahí el perfil (x 33..41) sí cae sobre el empalme (x 37..40) y sobre el costado (x = 40), así que los dos siguen recibiendo |
| Caras elegidas a mano (tapa + base + costado) | +450,00 | +450,00 (la decisión del 2026-10-13 intacta) |
| Envolver a mano un empalme lejos del perfil (`sonda_b217_caras.py`) | +39,71 ese empalme (+287,14 los cuatro) | igual → **fila nueva B-220** |

Ventana (regla 9, porque cambiaron el diálogo de Barrido y el comportamiento del Repujado): las dos piezas de la tanda, en minimizada, con `PYTHONIOENCODING=utf-8` y `--plazo 2700` por `turno` (la pieza entera pasa del tope interno de 900 s de `todo.py`):

```
$ ../scripts/turno.py --plazo 2700 -- .venv/Scripts/python.exe ../scripts/prueba_ui/revolucion_barrido_solevacion.py
=== 40 comprobaciones, 7 con ✗ ===        (8 ✗ después de la tanda 1)
[OK ] · Barrido sólido › Escala del perfil ofrece Estirar (Fusion: Scale, Stretch, None) — ofrece ['escalar', 'estirar', 'ninguna']
[OK ] · Barrido › Distancia «1,5»: aviso — ⚠ La distancia sobre la ruta va de 0 a 1 (fracción del total); recibió 1.5.
[OK ] · Revolución dos lados 90 / −45°: o aviso o 2356,19 mm³ (como la superficie), no el lado 2 perdido — volumen 2356.19 sin aviso «»
[OK ] · ventana 1024x640: Aceptar se ve con el Barrido con carril — esquina 921,564 en 1024x640
[OK ] · ventana 800x520: Aceptar se ve con el Barrido con carril — esquina 697,463 en 800x520
```

Pasó el check que la auditoría tenía en ✗ (B-209: «Estirar no está en la lista»). Las 7 ✗ que quedan son ítems ya anotados, ninguno de esta tanda: H-88 (2: «A objeto» no muestra Dirección, en sólido y en superficie), H-92 (2: «Proyectar eje» con nombre y valor por defecto distintos), H-89 (sin Extensión con carril), B-208 (el carril paralelo da 784,02 en vez de 800) y H-90 (la fila del punto solo ofrece «Aguda»).

```
$ ../scripts/turno.py --plazo 2700 -- .venv/Scripts/python.exe ../scripts/prueba_ui/nervio_red_repujado.py
=== 84 comprobaciones, 5 con ✗ ===        (6 ✗ después de la tanda 2; 9 en la auditoría)
[OK ] · Repujado con cadena tangente: vista previa
[OK ] · Repujado con cadena tangente: resultado = 100 — obtenido 100.0; nuevos={} cambiados={'op9.c1': ('solido', 23724.071)}
[OK ] · Repujado con cadena tangente: deshacer vuelve al estado anterior (1 paso/s)
[OK ] · Repujado placa: resultado = 100 — obtenido 100.0; nuevos={} cambiados={'op9.c1': ('solido', 23724.071)}
```

Cerró el check de B-217 en la ventana real (23724,071 = la placa de 23624,07 + los 100 exactos; en la tanda 2 daba 24061,186). Las 5 ✗ que quedan son ítems ya anotados: B-215 (2: desmoldeo −1° y 1° con extracción), H-95 (el Nervio no tiene Radio del empalme), H-99 (profundidad negativa no pasa el Efecto a Grabado) y H-97 (asas de alineación del Repujado).

Capturas miradas con Read: `capturas/barrido_carril.png` (la app entera con el aviso conocido de la selección de cadena; sin nada roto), las de tamaño de panel `barrido_1024x640.png` / `barrido_800x520.png` (los dos checks de «Aceptar se ve» de la primera pieza) y `capturas/repujado_cadena.png` (el panel REPUJADO con «Cadena tangente» activa: el relieve azul solo en la cara de arriba de la placa, los cuatro costados limpios — la imagen que la auditoría mostraba con cuatro cuadros achicados).

Evidencia: `evidencias/ui_2026-11-06/revolucion_barrido_solevacion.log` y `.json`, `nervio_red_repujado.log` y `.json` (el `.log` de esta pieza quedó reconstruido desde su `.json` de la corrida porque el stdout se cortaba en el pipe de la consola; la línea de arriba del archivo lo aclara), y las sondas `sonda_tanda3.py` (con su salida `sonda_tanda3_despues.txt`), `sonda_b217_caras.py` y la re-corrida `../evidencias/ui_2026-11-05/sonda_carril.py`.

### Seguimiento

- `docs/seguimiento/bugs.md`: borradas la fila y la ficha de «Detalle» de B-217 y de B-209; fila y ficha nuevas de **B-220** (el envoltorio que da una vuelta de más); recuento del encabezado 22 → 21 (Abierto 18 → 17 · Parcial 4).
- `docs/seguimiento/README.md`: no tenía filas de B-209 ni B-217 (`grep -n "B-209\|B-217"` → nada), así que no había qué borrar.
- `README.md` y `README.en.md` (hoja de ruta): sin mención de «Estirar» ni de la cadena tangente (`grep` → nada); no se tocaron.
- `docs/auditoria_revolucion_barrido_solevacion.md` y `docs/auditoria_nervio_red_repujado.md`: son el informe de esa corrida (histórico); no se cambiaron.
- Dos viñetas en «## Registro» de `PROJECT_LOG.md` y dos lecciones en «## Lecciones aprendidas» (una selección automática no hereda el trato de la elección manual; un docstring que declara imposible un cálculo no es evidencia).

### Archivos fuera de mi tanda

La tabla de la tanda 3 lista `nucleo/solidos_crear.py` y `ui/comandos/crear.py`. También toqué `nucleo/superficies.py` — es la columna «Gemelos a revisar» de la misma fila (el Barrido de superficie), y ahí cambió solo `_barrido_estirado`: un parámetro nuevo con valor por defecto que su llamador de superficie ni pasa. No se tocaron `timeline/ops_solido.py`, `timeline/ops_superficie.py`, `api/herramientas_*.py`, `ui/comandos/superficie.py` ni `ui/comandos/asas_extra.py`: los gemelos ya tenían la regla o el parámetro. `docs/corrida_nocturna_2026-11-05.md` aparece modificado en el árbol: es de otra corrida, no lo miré ni lo cambié.

### Lo que no pude verificar

- ⚠ **Fusion real no se abrió** para ninguno de los dos. La regla del Stretch sale del texto de la ayuda («use path - guide rail distance to scale profile in X») y de que la superficie del propio OmniCAD ya la aplicaba; la de la cadena sale de la ayuda del Emboss y de la fila B-217, y **convive** con la decisión del 2026-10-13 (cara elegida a mano: adaptar). Si al abrir Fusion resultara que la cadena tampoco recibe lo que cae sobre un empalme —en el control de la caja 40×30×10 hoy recibe su parte—, la regla nueva pasa a mirar el tipo de cara en el filtro: una línea.
- ⚠ **El estirar con `distancia` menor que 1** no mejoró: el sólido empareja la ruta recortada con el carril **entero** (fracción contra fracción), así que con 0,5 la sección final ya está al 3× — medido 40,00 mm³ con caja ±3 en z 0..5. Es la convención que ya tenía «escalar» (`_ley_escala_carril` hace el mismo emparejamiento; midió 146,78 mm³) y el sólido no tiene la opción `distancia_carril`/Extensión que la superficie sí (eso es H-89, ya anotado). Cambiarlo es otra decisión de producto, no este bug.
- ⚠ **B-208 sigue abierto** y es vecino: con carril paralelo la forma todavía se tuerce en el medio (784,03 en vez de 800) en sólido y en superficie; el check de la pieza sigue ✗.
- ⚠ **Perfil anillado (con agujero) estirado en la ventana**: lo mide el test del núcleo (80 − 20 = 60 mm³); el diálogo y la API se probaron sin agujero.
- ⚠ **`edit_feature` con `escala_carril="estirar"`** no tiene test propio: recalcula el paso con el mismo `ejecutar` que el test de `sweep`, así que queda cubierto por el arreglo del núcleo, no por una corrida.
- ⚠ **Proyectos `.omnicad` guardados con «Estirar»**: al abrir, el cuerpo cambia de forma (del tronco de 3364,59 al estirado de 1600 en el caso de la fila). En `ejemplos/` no hay recetas con `escala_carril` (`grep -rln "escala_carril" ejemplos/` → nada), pero una pieza del usuario puede tenerla. Con la cadena tangente pasa lo mismo a la inversa: el repujado pierde las copias de los costados.
- ⚠ **B-220 queda abierto** y es el mismo síntoma por la otra puerta (cara elegida a mano): medido, con ficha, sin arreglo.

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
