# Patrones de sólido: auditoría y corrección (2026-10-31)

Herramientas: **Patrón rectangular**, **Patrón circular**, **Patrón en trayectoria** (las tres con equivalente en Fusion),
**Patrón en puntos** y **Multitransformación** (propias de OmniCAD, nacidas de FreeCAD; no se comparan con Fusion).
Fuentes: video `2026-10-31 07-09-15.mp4` (10:42; demostración de uso y casos de reproducción, no límite de la tarea), ayuda
local de Fusion (`pattern-reference`, `create-a-rectangular-pattern`, `create-a-circular-pattern`,
`create-a-pattern-on-a-path`) y el código. Los patrones **dentro de un boceto** son otra sesión y no se tocaron.

## Qué dice la ayuda de Fusion (lo único que se declara equivalente)

| Tema | Fusion (ayuda local) | OmniCAD ahora |
|---|---|---|
| Direcciones del rectangular | «After you select directions, two perpendicular quantity manipulators display… Select a second edge to change the angle of the second direction.» Con Cantidad 2 = 1 queda una sola dirección | Dirección 2 vacía = perpendicular derivada a la 1 (flecha verde, texto en el panel); elegir otra referencia la reemplaza; Cantidad 2 = 1 oculta Distancia 2 y Simétrico 2 |
| Distribución | Extensión = distancia total; Espaciado = separación | Igual (`distribucion`) |
| Dirección | Una dirección / Simétrico, **por eje** | `simetrico` y `simetrico2` por separado (antes una casilla para las dos) |
| Circular | Completo (360°) · Parcial (un lado, hasta el ángulo) · Simétrico (a los dos lados hasta el ángulo) | Los tres modos, más «Ángulo entre copias» aparte; las recetas viejas (`extension`, `espaciado`) siguen igual |
| Trayectoria | Ruta, Cantidad, Distancia (arrastrable en la vista), Punto de inicio (porcentaje, arrastrable), Distribución, Dirección, Orientación | Todo, con el asa de distancia **sobre el recorrido**; el inicio se escribe en porcentaje (la receta guarda la fracción de 0 a 1) |
| Supresión | Casilla sobre cada instancia en la vista | `CasillasCopias`: casilla sobre cada copia, clic para suprimir y restaurar |
| Cambiar de tipo al vuelo | Sí (Tips) | Diálogo único con «Tipo de patrón»: rectangular, circular, trayectoria y puntos; las selecciones compatibles se conservan |
| Compute Type | Optimizado / Idéntico / Ajustar | Optimizado patronea las caras de una copia (mismo resultado que Idéntico, más rápido); si las copias no son intercambiables, usa la herramienta como Idéntico, sin el error que Fusion da con operaciones divididas; solo Ajustar recalcula |

**No verificado** (la ayuda no lo define; PAT-1): si «Cantidad» simétrica es el total de instancias o las de cada lado, y si el
ángulo simétrico es el total o el de cada lado. OmniCAD conserva su convención (n copias a cada lado, 2n − 1, y hasta ± el
ángulo). **No se declara equivalencia con Fusion en la simetría.**

## Matriz por herramienta

Clasificación: **V** observado en el video · **R** confirmado por reproducción · **L** lectura del código · **D** diferencia
funcional documentada · **M** mejora de interacción.

### Patrón rectangular

| Problema | Clase | Evidencia | Causa | Corrección | Prueba | Pendiente |
|---|---|---|---|---|---|---|
| Cantidad 2 y Distancia 2 editables sin Dirección 2 y sin efecto (video 5:15–6:15) | V R | `OpPatron` daba n2 = 1 si faltaba `dir2` y no avisaba | El panel mostraba siempre los campos de la dirección 2 | `dir2_derivada` (dirección perpendicular estable, `entidades.direccion_perpendicular`); campos de la 2 ocultos con Cantidad 2 = 1; receta vieja con n2 sin dir2: mismo resultado y aviso | `test_cantidad_2_sin_direccion_2_se_avisa_y_con_la_derivada_se_usa`, `test_la_direccion_derivada_es_perpendicular_y_estable`, UI `test_rectangular_la_direccion_2_derivada_se_ve_y_se_aplica` | — (el plano de referencia de la derivada ya se elige: `plano_dir2`) |
| La misma casilla Simétrico valía para los dos ejes | L R | `OpPatron` pasaba `simetrico` a `simetrico1` y `simetrico2` | Un solo parámetro | `simetrico2` (None = como antes) | `test_rectangular_dos_direcciones_con_simetria_independiente`, `test_receta_vieja_la_simetria_global_vale_para_las_dos_direcciones` | PAT-1 |
| Direcciones paralelas no se rechazaban | L R | Copias de la 2 caían sobre las de la 1 | Sin validación en el núcleo | `exigir_no_paralelas`: error «Las direcciones 1 y 2 son paralelas» | `test_direcciones_paralelas_o_nulas_dan_un_error_claro`, `test_direcciones_oblicuas_se_aceptan` | — |
| Suprimir solo la primera fila (video 6:20–6:50) | V R | El panel guardaba enteros, el núcleo los leía como (i, 0) | Identificador no estable | Par `[i, j]` (pasos desde el original en cada dirección; con simetría hay negativos), campo `i:j`, casilla en la vista; entero viejo = `[i, 0]` | `test_suprimir_una_copia_fuera_de_la_primera_fila`, `test_la_exclusion_conserva_su_posicion_al_cambiar_cantidades_y_distancias`, UI `test_rectangular_supresion_con_clic_en_la_casilla_y_estabilidad` | — (silueta roja de la copia suprimida; casillas también con caras, componentes y construcción) |
| Exclusión que queda fuera tras bajar la cantidad | L R | Se descartaba o se aplicaba a otra copia sin aviso | — | Se conserva, no se reasigna y avisa «ya no existen en el patrón» | `test_exclusion_fuera_del_patron_se_conserva_se_avisa_y_no_se_reasigna` | — |

### Patrón circular

| Problema | Clase | Evidencia | Causa | Corrección | Prueba | Pendiente |
|---|---|---|---|---|---|---|
| «Completo» dejaba editar el ángulo total (video 7:15–8:05); no había Parcial ni Simétrico | V | Combo «Completo / Ángulo entre copias» | Dos modos en un combo | `modo`: Completo (360° sin repetir el cierre, ángulo oculto), Parcial, Simétrico y Ángulo entre copias | `test_circular_completo_de_seis_separa_60_grados_sin_duplicar_el_cierre`, `test_circular_parcial_de_tres_sobre_120_grados_es_0_60_y_120`, `test_circular_simetrico_reparte_a_los_dos_lados`, UI `test_circular_modos_completo_parcial_simetrico_y_el_asa_coincide_con_la_copia` | PAT-1 |
| El manipulador usaba total/n y el cálculo total/(n − 1) | L R | Con 3 copias sobre 120° el asa quedaba a 40° | Dos fórmulas | `solidos_crear.paso_angular` compartida por cálculo, asa e información del panel | UI `test_circular_modos…` compara el asa con el centro de la copia a 120° | — |
| Eje: el filtro `{"eje"}` no deja elegir aristas circulares ni círculos de boceto | L R | `visor3d` solo da aristas lineales con «eje»; `como_eje` no convertía círculos | Filtro y conversión | Filtro `{eje, arista_circular, curva_boceto}` y `como_eje` → `eje_de_curva_circular` | `test_circular_con_el_eje_de_un_circulo_de_boceto` | — |
| Pasar de Completo a Parcial dejaba 360° (= Completo) sin explicar | M | — | — | El ángulo baja a 180° / 90° al cambiar el tipo y el panel lista los ángulos de las copias | UI `test_circular_pasar_de_completo_a_parcial_no_deja_los_360_sin_explicar` | — |
| Cantidades 1 y 2, sentido negativo, ángulos límite | R | — | — | Se conservan los errores («distinto de cero y no más de una vuelta»); n = 1 avisa «no crea copias» | `test_circular_sentido_cantidades_uno_y_dos_y_limites` | — |

### Patrón en trayectoria

| Problema | Clase | Evidencia | Causa | Corrección | Prueba | Pendiente |
|---|---|---|---|---|---|---|
| Cantidad y distancia colgaban de la tangente inicial y se alejaban de las copias (video 8:35–9:15) | V L | `_asas_patron_ruta` | Asas en línea recta desde el inicio | `AsaRecorrido` (distancia por longitud de arco real) y `AsaCantidad` sobre la ruta; el inicio es el disco que se desliza por ella | UI `test_ruta_compuesta_las_asas_recorren_toda_la_cadena`, `test_ruta_insuficiente_avisa_y_el_inicio_se_ve_en_la_ruta` | — (inicio en porcentaje) |
| Las asas usaban solo la primera arista; el cálculo, la cadena | L R | `_forma_de(ctx, v["ruta"][0])` | Dos recorridos distintos | Las asas llaman a `_aristas` de `OpPatron` y a `solidos_crear.perfil_ruta`/`recorrido_ruta` | `test_ruta_compuesta_reparte_sobre_la_longitud_de_toda_la_cadena` | — |
| Ruta cerrada, vuelta completa **negativa**: la última copia caía sobre el original | R | Con el commit base (`472777a`): `distancia = −160` en un cuadrado de 160 → 3 posiciones distintas de 4 | `abs(distancia − largo)` solo cubría el sentido positivo | `recorrido_ruta` usa `abs(distancia)`; las repetidas se omiten con aviso | `test_ruta_cerrada_vuelta_completa_positiva_y_negativa_no_duplica_el_cierre` | — |
| Instancias más allá del extremo de una ruta abierta se omitían sin decirlo | L R | `transformaciones_en_ruta` hacía `continue` | — | Política: **no se extrapola**; se crean las que caben y el panel/la API avisan «La ruta no alcanza: N instancias caerían pasado su extremo» | `test_ruta_insuficiente_crea_menos_y_lo_dice`, API `test_ruta_que_no_alcanza_avisa_en_vez_de_extrapolar` | — |
| ¿Se fuerza el centro del cuerpo sobre la curva? | L | — | — | No: el original queda donde está (en la fracción `inicio`) y cada copia es una traslación `p_k − p_0`, orden de composición con el giro | `test_ruta_inicio_intermedio_y_cuerpo_lejos_de_la_curva_conserva_su_posicion_relativa` | Cómo lo hace Fusion con un cuerpo lejos de la ruta no está en la ayuda |

### Patrón en puntos

| Problema | Clase | Evidencia | Causa | Corrección | Prueba | Pendiente |
|---|---|---|---|---|---|---|
| Referencia vacía = origen sin decirlo y sin marcadores (video 9:20–9:55) | V | Panel sin explicación | — | Texto fijo en el panel, cruz verde en la referencia, cruces azules en los destinos y líneas de la referencia a cada destino (`previa_vista`) | UI `test_puntos_marcadores_explicacion_y_traslacion_exacta` | — |
| Un boceto entero aporta solo sus puntos sueltos | D | `_puntos_de` | Diseño | Se explica en el panel y en la ayuda del campo | UI (mismo) y `test_patron_en_puntos_un_boceto_entero_toma_solo_sus_puntos_sueltos` | — |
| Traslación = destino − referencia, repetidos, coincidentes, supresión, puntos que se mueven | R | Las «traslaciones extrañas» del video salen de usar el origen como referencia | — | Sin cambios de cálculo; instancias con estado `repetida`/`suprimida`, aviso de los puntos repetidos | `test_patron_en_puntos_traslacion_igual_a_destino_menos_referencia`, `…destinos_repetidos_coincidentes_y_supresion`, `…referencia_xyz…`, `…sigue_al_punto_del_boceto_si_se_mueve` | — |

### Multitransformación

| Problema | Clase | Evidencia | Causa | Corrección | Prueba | Pendiente |
|---|---|---|---|---|---|---|
| Abrir y aceptar perdía `simetrico` y `suprimir` (y todo lo no mostrado) | L R | `_ranura_desde` / `construir` reconstruían solo `dir1, n1, d1…` | Cuatro ranuras fijas | Lista de transformaciones: cada elemento guarda su receta **completa**; el editor se fusiona sobre ella | `test_multitransformar_conserva_simetria_y_supresion_en_cada_transformacion`, UI `test_multitransformar_abrir_y_aceptar_sin_tocar_conserva_simetria_y_supresion` | — |
| Máximo cuatro ranuras | L | `RANURAS = 4` | — | Lista de hasta 12 con Agregar (menú de 5 tipos), Quitar, ▲ y ▼; admite rectangular en dos direcciones, circular, trayectoria, puntos y simetría | UI `test_multitransformar_lista_agregar_reordenar_quitar_y_aceptar_sin_cambios` | — (asas y copias «hasta la etapa k» de la transformación elegida) |
| Errores sin decir qué etapa | M | Mensaje genérico | — | «Transformación 2 (Simetría): …» y «Falta completar la transformación 2…»; la etapa elegida se ve en la lista y en «Editando la transformación k de n» | UI (mismo) | — |

### Comportamientos compartidos

| Tema | Resultado | Prueba |
|---|---|---|
| Tipos de objeto (cuerpos, caras, operaciones, componentes, construcción) | Ya existían; se conservan y los patrones de caras, componentes y construcción siguen verdes | `test_simetria_patrones.py`, `test_patrones_avanzados.py` |
| Compute Type | Idéntico = Optimizado; Ajustar omite las copias que no tocan el cuerpo y lo avisa | `test_identico_y_optimizado_dan_lo_mismo_y_ajustar_omite_las_copias_que_no_tocan` |
| Deshacer/rehacer, guardar y reabrir | Un paso de deshacer por operación; `simetrico2`, `dir2_derivada` y `suprimir` sobreviven al `.omnicad` | `test_un_patron_se_deshace_y_rehace_de_una_vez_y_sobrevive_a_guardar_y_reabrir` |
| Recetas viejas | Abrir y aceptar en el diálogo da el mismo resultado (rectangular con n2 sin dir2, simétrico, circular `extension`/`espaciado` con simetría, 360°, ruta con giro) | UI `test_abrir_y_aceptar_un_patron_viejo_da_el_mismo_resultado` |
| Límite de instancias | 10.000; el panel lo dice y no se cuelga | UI `test_el_limite_de_instancias_se_explica_y_no_cuelga_el_panel` |
| Previa pesada en proceso aparte | `multitransformar` se suma a los tipos pesados (antes solo `patron`) | `tests/test_previa_aislada_comandos.py` |
| MCP / CLI | `rectangular_pattern` (`symmetric2`, `suppress` con pares), `circular_pattern` (`distribution`: full / partial / symmetric), `multi_transform` con las mismas opciones; `docs/agentes/herramientas.md` regenerada | `tests/test_api_patrones_solidos.py`, `tests/test_doc_agentes.py` |

## Archivos tocados

Núcleo `nucleo/solidos_crear.py`, `nucleo/consultas.py`; timeline `ops_solido.py` (OpPatron, OpMultitransformar), `entidades.py`;
interfaz `ui/comandos/crear.py` (diálogo del patrón), `patrones.py`, `asas_patron.py` (nuevo), `asas_extra.py` (se quitaron las
asas viejas de patrones), `ui/manipuladores.py` (`RecorridoRuta`, `AsaRecorrido`, `CasillasCopias`), `ui/comando.py` (ganchos
genéricos `al_cambiar`, `set_valores`); API `api/herramientas_solido.py`; pruebas `test_patrones_solidos_semantica.py`,
`test_patrones_solidos_ui.py`, `test_api_patrones_solidos.py` y las claves nuevas del diálogo en `test_comandos_crear.py`,
`test_gizmo_cantidad.py`, `test_manipuladores.py`, `scripts/prueba_ui/asas.py`.

Cambio de claves del diálogo (no de las recetas): el circular usa `modo`, `angulo`, `angulo_paso`; la trayectoria usa `rn`, `rd`
(antes `n1`, `d1`); la Multitransformación se arma desde `_lista` y los campos `t_…`. Las recetas guardadas no cambian.
