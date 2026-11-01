# Desfase del boceto contra Fusion: matriz de equivalencia (2026-10-31)

Alcance: el comando **Desfase dentro de un boceto** (no el desfase de caras, aristas ni superficies).
Archivos: `restricciones/boceto.py` (`desfasar`, `desfase`), `api/herramientas_boceto.py` (`offset_sketch_curves`),
`ui/editor_boceto.py` (barra, vista previa, clics), `ui/asas_boceto.py` (`asas_desfase`), `ui/modo_boceto.py` (paleta).
Pruebas: `tests/test_desfase_equivalencia.py` (nueva), `test_desfase_boceto.py`, `test_boceto_fase7_ui.py`,
`test_boceto_fase9_desfase.py`; recorrido con la ventana real: `scripts/prueba_ui/desfase_boceto.py`.

## Cómo se distingue la evidencia

| Marca | Significa |
|---|---|
| **[V]** | Se ve en el video `2026-10-31 06-46-25.mp4` (Fusion hasta ~1:15, OmniCAD desde ~1:20). Es una observación, no una especificación. |
| **[D]** | Lo dice la ayuda oficial: `offset-sketch-geometry-c7750d70285.md` o `sketch-modification-tools-a217fee171a.md`. |
| **[C]** | Hallazgo en el código. |
| **[R]** | Reproducido en OmniCAD (script o prueba). |
| **[?]** | **No verificado en Fusion.** No hay acceso a Fusion en esta sesión (el MCP `fusion360` no conectó: `ECONNREFUSED`). Es decisión de diseño, no compatibilidad. |

## Lo que muestra el Fusion del video [V]

- Diálogo «Desfase»: **Curvas** (1 seleccionada), **Selección de cadena** (casilla), **Dirección** (Un lado / Dos lados / Simétrico),
  **Distancia** (o Distancia 1 y 2), **Cambiar**, Aceptar y Cancelar.
- Al elegir la curva aparece **de inmediato** la vista previa y **una flecha (asa)** sobre la curva; la distancia se mueve **al
  arrastrar la flecha** (valores 14,962; 21,35; 16,425 mm: salen del arrastre, no de una fórmula). Con el cursor sin botón no cambia nada.
- Un campo flotante junto al asa muestra el valor, con el texto seleccionado, para escribirlo.
- Un lado: positivo = el lado de la flecha (afuera en un círculo), negativo (p. ej. −74,775) = el otro.
- Dos lados: Distancia 1 = 21,35 daba una copia afuera y **Distancia 2 = −20,556** otra adentro. Las dos llevan **signo sobre la misma normal**;
  Distancia 2 arranca en 0,00 y con 0 no hay segunda copia.
- Simétrico: una sola distancia y una sola flecha, con las dos copias a la vista.
- Con «Selección de cadena» apagada se ofrece desfasar solo la curva tocada.
- Aceptar cierra el comando y deja las curvas, con cotas y glifos.

## Matriz

Prioridad: **P0** rompe el uso habitual · **P1** diferencia visible · **P2** caso raro. Estado: ✅ corregido y probado · ⚠ queda diferencia (con fila de seguimiento) · ❓ sin verificar en Fusion.

| # | Escenario | Fusion (evidencia) | OmniCAD antes | Diferencia y corrección | Pri. | Prueba de aceptación | Estado |
|---|---|---|---|---|---|---|---|
| 1 | Activar con la curva ya elegida | El diálogo abre con «1 seleccionada» y vista previa **[V]** | Pedía otro clic **[R]** | `_desfase_con_seleccion`: arranca solo | P1 | `test_con_la_curva_ya_elegida_el_desfase_arranca_sin_otro_clic` | ✅ |
| 2 | Elegir una curva suelta | **[D]** curva, cadena o perfil | Siempre la cadena entera **[C]** | Casilla «Selección de cadena» en la paleta y `chain` en la API | P1 | `test_seleccion_de_cadena_apagada_en_la_ventana`, `test_api_chain_false_en_un_rectangulo` | ✅ |
| 3 | Elegir un perfil (clic adentro de la región) | **[D]** se puede elegir un perfil | Solo curvas **[C]** | Un clic dentro de una región cerrada elige su contorno y el de sus huecos (`desfasar_perfil`; API `profile`) | P2 | `test_desfasar_perfil_crece_afuera_y_achica_el_hueco`, `test_ventana_clic_dentro_de_un_perfil_abre_el_desfase_y_se_acepta`, `test_api_offset_de_un_perfil` | ✅ (cierra BOC-70) |
| 4 | Corregir o reemplazar la selección | Botón × en «Curvas»; reemplazo con otro clic **[?]** | Un clic con la barra abierta la cerraba **[C]** `editor_boceto.py` mousePress | Clic sobre otra curva pasa el desfase a ella con los mismos valores; clic en el vacío no hace nada; Enter acepta y Esc cancela | P0 | `test_clic_en_el_lienzo_no_cierra_cambia_de_curva_y_enter_acepta` | ✅ ❓ (el reemplazo es decisión de diseño) |
| 5 | Resaltado | La curva elegida en azul **[V]** | Igual | — | — | `test_con_la_curva_ya_elegida…` (se suelta al cerrar) | ✅ |
| 6 | Un lado: signo | Positivo = lado de la flecha; negativo = otro **[V]** | Positivo = **hacia el cursor** **[C]** | El lado lo da solo el signo (afuera por defecto en cerradas), «⇄» y el asa. El cursor ya no interviene: lo confirmado dependía de dónde estaba el ratón | P0 | `test_asa_arrastrar_escribe_el_valor_con_signo_y_el_hover_no`, `test_tabla_del_circulo_del_video` | ✅ |
| 7 | Dos lados: convención | D1 = 21,35 afuera, **D2 = −20,556 adentro**, misma normal; 0 = sin copia **[V]** | D2 positivo = «al contrario de D1» **[C]** | Misma normal con signo; una de las dos puede ser 0. **Cambia el significado de `distance2`** en la API/CLI | P0 | `test_tabla_del_circulo_del_video` (20 y −10 → 87,125 y 57,125) | ✅ (solo con el video como evidencia) |
| 8 | Simétrico | Una distancia, dos copias **[V]** | Dos cotas independientes: editar una dejaba la otra **[R]** | La 2.ª cota queda ligada a la 1.ª (`igual_a`, como el chaflán de distancias iguales); editar una mueve las dos | P0 | `test_simetrico_queda_ligado_y_editar_una_cota_mueve_las_dos` | ✅ ❓ (cómo ata Fusion las dos cotas no se vio) |
| 9 | Distancia inicial | Sale del asa: 15–21 mm **[V]** | `_radio_sugerido`: largo/5 → **80 mm en el círculo de 67,125** (imposible hacia adentro) **[R]** | Distancia redonda de ~48 px sin pasar de ¼ del tamaño de lo elegido; `_radio_sugerido` queda para Empalme y Chaflán | P0 | `test_el_valor_inicial_entra_para_los_dos_lados_aunque_la_curva_sea_chica` | ✅ |
| 10 | Arrastrar el asa | Hace falta **arrastrar**; pasar el cursor no cambia nada **[V]** | Sin asa; el cursor solo cambiaba el lado **[C]** | Asa por distancia sobre la normal de la curva; escribe el valor **con signo** en la caja | P0 | ídem 6; `scripts/prueba_ui/desfase_boceto.py` (sección 5b) | ✅ |
| 11 | Entrada exacta y ajuste visual | El campo flotante y el del diálogo van juntos **[V]** | — | Lo escrito manda y el movimiento no lo pisa; se vuelve al ajuste visual tirando del asa (la pista lo dice) | P0 | ídem 6 | ✅ |
| 12 | Cambiar de dirección con el comando abierto | Cambia al instante **[V]** | La paleta decía Simétrico y la barra seguía con Dos lados **[C]** | `cambiar_opcion_desfase` rearma barra, asas, vista previa y Aceptar; conserva selección y valores (Un lado→Dos: d y 0; Simétrico→Dos: d y −d) | P0 | `test_cambiar_la_direccion_con_la_barra_abierta_rearma_todo`, `test_cambiar_de_modo_con_un_error_no_deja_campos_viejos`, recorrido real con el combo de la paleta | ✅ |
| 13 | Vista previa válida | Rosa, curvas enteras **[V]** | Igual | — | — | `test_la_previa_dibuja_exactamente_lo_que_se_crea` | ✅ |
| 14 | Previa inválida y recuperación | No se vio un caso **[?]** | Todos los campos en rojo **[C]** `_al_cambiar_desfase` | Cada error en su campo: lo escrito, el lado que falla en Dos lados, o el conjunto; la barra sigue y los valores buenos se conservan. Atómico: si un lado falla no se crea el otro | P1 | `test_dos_lados_marca_solo_el_campo_que_falla_y_conserva_el_valido`, `test_interior_de_80_dice_por_que…` | ✅ |
| 15 | Mensajes y barra junto a los bordes | — | Nota de una línea sin límite; barra sin acotar **[C]** | Nota partida en líneas dentro de la zona útil (sin la paleta), barra acotada y reubicada al cambiar el tamaño; campos de ancho fijo; etiquetas sin cortar | P1 | `test_barra_y_nota_quedan_a_la_vista…` (1280×720, 1024×640, 800×520, 640×400), `test_la_paleta_a_la_derecha_no_tapa_la_barra` | ✅ |
| 16 | Confirmar y cancelar | Botones Aceptar y Cancelar **[V]** | Solo Enter y Esc **[C]** | Botones ✓ y ✕ en la barra con su atajo en el aviso; la pista dice que el boceto sigue abierto | P1 | `test_esc_cancela_sin_tocar_nada_y_el_boton_cancelar_tambien` | ✅ |
| 17 | Después de aceptar | El comando termina **[V]** | La herramienta sigue activa (como todas las de boceto) | Se deja: repetir sin volver a pulsar el botón | P2 | — | ⚠ diferencia aceptada |
| 18 | Un paso de deshacer | — | Igual | — | — | `test_la_previa_coincide_con_lo_confirmado_y_nada_cambia_antes`, `test_api_deshacer_rehacer_y_guardar_reabrir` | ✅ |
| 19 | Circulos y arcos | **[D]** concéntrico | Igual | Compartir el centro; rechazo con causa si el radio llega a 0 | — | `test_arco_concentrico_y_radio_resultante`, `test_tabla_del_circulo_del_video` | ✅ |
| 20 | Líneas y cadenas abiertas | **[D]** paralela y encadenada | Igual | — | — | `test_linea_suelta_paralela_a_su_distancia`, `test_cadena_abierta_linea_arco_linea_sigue_continua` | ✅ |
| 21 | Cadenas cerradas (convexa y cóncava) | **[D]** esquinas resueltas | Igual | — | — | `test_cadena_cerrada_convexa_y_concava` | ✅ |
| 22 | Elipse | **[D]** cerca de un eje → **elipse**; lejos → **óvalo** a distancia constante | Siempre una spline libre de 48 puntos, sin asociación **[R]** | Lejos de un eje: la spline a la distancia pedida (±1,5 %); cerca de un eje (12 px): otra elipse de semiejes a±d y b±d, atada con restricción y cota (API `ellipse_result`) | P2 | `test_elipse_da_una_curva_a_distancia_constante`, `test_desfase_de_elipse_da_otra_elipse_con_los_semiejes_a_mas_menos_d`, `test_ventana_elipse_cerca_del_eje_da_elipse_y_lejos_un_ovalo` | ✅ (cierra BOC-71) |
| 23 | Spline | **[D]** | Spline libre de 48 puntos con cota asociativa | Se rechaza si la distancia pasa el radio de curvatura | — | `test_spline_cerrada_y_abierta_a_distancia_constante` | ✅ |
| 24 | Curva de construcción | **[?]** | Las copias heredan «construcción» | — | — | `test_curva_de_construccion_conserva_su_tipo_en_todas_las_copias` | ❓ |
| 25 | Distancias 0, grandes, cercanas al colapso | **[?]** | Rechazo con causa (cero; más del radio; segmento a largo cero o al revés; 1e9) | — | — | `test_interior_de_80_se_rechaza_sin_tocar_el_boceto`, tests previos | ✅ ❓ |
| 26 | Match Topology | **[D]** limita la distancia para igualar la topología de la madre; **no aparece en el diálogo del video** | Limita y avisa | La opción ahora también rearma la barra abierta; el significado no se pudo comprobar en vivo | P2 | `test_match_topology_limita_y_avisa` | ❓ |
| 27 | Editar la distancia / el original | **[D]** asociativo | Igual | — | — | `test_editar_el_original_y_la_distancia_mueve_el_desfase…` | ✅ |
| 28 | Borrar la cota / soltar la asociación | **[D]** borrar la cota deja la relación sin distancia; borrar el glifo la quita | Cadenas y líneas: sí. Círculo: queda el centro común. Spline y elipse: sin cota ya no hay relación | La spline y la elipse también la conservan: una restricción de desfase con la distancia como incógnita común sobrevive a la cota | P2 | `test_borrar_la_cota_libera_la_distancia_y_soltar_conserva_las_curvas`, `test_circulo_sin_cota_sigue_concentrico`, `test_borrar_la_cota_de_la_spline_conserva_la_relacion_y_libera_la_distancia` | ✅ (cierra BOC-72) |
| 29 | Cota negativa al editar | **[?]** | Se rechaza con explicación | Ya abierto: la ayuda no lo dice y Fusion no estuvo disponible (2026-10-31) | P2 | — | ⚠ BOC-50 (Sin verificar) |
| 30 | Guardar y reabrir | — | Igual | — | — | `test_editar_el_original…` (abre otra sesión) | ✅ |
| 31 | Rendimiento de la previa | — | Se recalculaba en cada pintada **[R]** | Se recuerda el último resultado | P2 | `test_repintar_sin_cambiar_nada_no_recalcula_la_previa` | ✅ (cierra BOC-51) |

## Qué no se pudo verificar y por qué

- **Fusion en vivo**: sin acceso. Todo lo marcado ❓ es decisión de diseño o se apoya solo en el video.
- La convención de Dos lados (fila 7) sale de **un solo** caso del video (D1 = 21,35 y D2 = −20,556); falta confirmarla con otros signos.
- Qué hace Fusion con la cota de un Simétrico, con un clic en el vacío, con Aceptar sobre distancias inválidas, con curvas de construcción y con la cota negativa.
- Match Topology: está en la ayuda pero no en el diálogo del video.

## Diferencias visibles que quedan

La vista es parecida y no igual: OmniCAD muestra el asa como un círculo y la vista previa en azul; Fusion usa una flecha y rosa, y
tiene un diálogo flotante aparte (OmniCAD usa la barra junto a la curva y la paleta de boceto). Las pruebas de ventana están en
`evidencias/ui_<hoy>/capturas/desfase_*.png` (fuera de git).
