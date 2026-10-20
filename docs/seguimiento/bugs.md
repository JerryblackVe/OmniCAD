# Bugs

Algo que falla, da un resultado malo o un mensaje engañoso. Método y columnas: [README](README.md).

Verificado contra el código el 2026-10-20 (suite: 3500 tests en verde). Total 108: Abierto 3 · Parcial 9 · Corregido 82 · No reproducido 9 · Retirado 5.

## Abiertos y parciales

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| P-12c | Fuente de novedades de Fusion (la ayuda es un shell JS sin titulares) | Abierto | Baja | Revisar a mano cada mes o cambiar la fuente. | PROJECT_LOG.md:33 | 2026-10-20 |
| P-1c | Wayland nativo: menús emergentes se cierran solos | Abierto | Alta | Con QT_QPA_PLATFORM=wayland se cierran el menú radial y «Seleccionar otro»; hoy se fuerza xcb. | omnicad/ui/__init__.py:11-19 | 2026-10-20 |
| P-11j | Cuerpos «sin ubicar» (2 del Sherpa, 3 de XOX) que Fusion no tiene | Abierto | Alta | Siguen entrando con aviso porque el flujo de diseño no se decodifica de forma confiable. | omnicad/io_archivos/f3d_nativo.py:123 (sin_ubicar); tests/test_p11a_f3d_instancias.py:176 | 2026-10-20 |
| B-50 | create_joint snapea por centro de cara y desplaza componentes | Parcial | Media | Slider con caras de distinto largo sigue moviendo el vástago (snap al centro). | tests/test_api_ensamble.py::test_union_contra_cara_anular_partida_engancha_el_circulo | 2026-10-20 |
| B-05 | Barrido con torsión 90° pierde 2,1 % de volumen | Parcial | Alta | Rutas cerradas o con quiebres >tolerancia siguen en modo curvilíneo con pérdida de volumen. | solidos_crear.py:733 (_guia_plana_posible); tests/test_solidos_crear.py::test_barrido_con_torsion_gira_el_perfil (rel 2e-3, ruta recta) | 2026-10-20 |
| B-09 | Boceto sobre cara no asociativo: el corte queda en el aire | Parcial | Alta | El corte no sigue al material al editar el cuerpo; solo avisa. | tests/test_api_solido.py::test_el_corte_que_no_toca_avisa_en_el_timeline; tests/test_hallazgos_tortura.py::test_t03_el_agujero_sobre_la_cara_de_un_boss_sigue_a_la_cara_cuando_el_boss_se_achica (solo agujero) | 2026-10-20 |
| B-71 | Uniones encadenadas: el lazo cerrado biela-manivela no se resuelve | Parcial | Alta | Falta resolver el lazo cerrado: las uniones se aplican de a una. | commit c853fd4; tests/test_b71_cadena.py (xfail estricto en :100 y :239; cadena abierta sin xfail en :33) | 2026-10-20 |
| B-80 | MCP sin herramientas para ANIMACIÓN, DIBUJO ni RENDERIZAR | Parcial | Alta | Faltan las olas 2 a 7: DIBUJO, RENDER, cinta, run_operation, visor/paneles, opciones. | commit 3ae4f74; api/herramientas_animacion.py (15 herramientas); tests/test_cobertura_ui_api.py:226; tests/test_api_animacion.py | 2026-10-20 |
| B-39 | join con herramienta enterrada deja arista libre y cuerpo no estanco | Parcial | Muy alta | La arista libre sigue (defecto del kernel); solo se detecta y avisa. | timeline/operaciones.py:349 y :1004 (aviso post-unión) | 2026-10-20 |
| B-48 | Crash nativo OCCT (0xc0000005) al recalcular parámetros a 148 pasos | Parcial | Muy alta | Recálculo sigue en el proceso de la app; solo el autoguardado protege. | commit d706002; nucleo/aislado.py:98; tests/test_b48_crash.py::test_b48_un_crash_nativo_del_kernel_vuelve_como_error_y_no_mata_al_padre | 2026-10-20 |
| B-52 | Unión de espiral: fusión degenerada, pérdida silenciosa y STEP en dos sólidos | Parcial | Muy alta | La fusión degenerada del kernel sigue; solo se avisa la pérdida o el corte. | timeline/operaciones.py:336,986-1005; tests/test_documento.py::test_combinar_avisa_si_la_union_pierde_material; ::test_union_de_primitiva_avisa_si_pierde_material | 2026-10-20 |
| T-04 | shell hacia afuera falla en un solevado de caras B-spline | Parcial | Muy alta | Hacia adentro anda; hacia afuera el kernel no da una pared válida | tests/test_hallazgos_tortura.py::test_t04_vaciado_exterior_bspline_falla_con_alternativa_y_sin_modificar | 2026-10-20 |

## Cerrados

Corregidos, no reproducidos (se reabren si vuelven) y retirados (no eran bugs).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| B-01 | coser/descoser/engrosar con dict dan «unhashable»; no validan tipo | Corregido | — | — | tests/test_referencias_mal_formadas.py::test_parametro_mal_formado_nombra_el_campo; ::test_descoser_y_coser_con_referencias | 2026-10-20 |
| B-02 | Loft entre círculos deja aristas bspline en vez de círculo | Corregido | — | — | omnicad/nucleo/solidos_crear.py:982 (_canonizar); tests/test_solidos_crear.py::test_solevado_entre_circulos_da_aristas_circulares | 2026-10-20 |
| B-03 | Loft entre octógonos: caras planas salen bspline sin normal | Corregido | — | — | solidos_crear.py:982; tests/test_solidos_crear.py::test_solevado_entre_poligonos_da_caras_planas | 2026-10-20 |
| B-04 | Vaciado del loft: caras equivalentes con tipos distintos (plane/other) | Corregido | — | — | tests/test_solidos_crear.py::test_solevado_entre_poligonos_da_caras_planas (vaciado: 19 caras planas) | 2026-10-20 |
| B-07 | check_interference reporta contacto cara con cara como interferencia | Corregido | — | — | api/herramientas_inspeccion.py:412 (espesor medio); tests/test_analisis.py::test_interferencias_ignora_contacto_con_error_de_redondeo | 2026-10-20 |
| B-08 | Labio sin lado: queda dentro del contorno y pisa la pared | Corregido | — | — | solidos_crear.py:2984-2993 (prueba ambos lados del tirado); tests/test_solidos_crear.py::test_saliente_y_labio_ranura (genérico) | 2026-10-20 |
| B-10 | extrude cut con boceto fuera del cuerpo no cambia el volumen | Corregido | — | — | api/herramientas_solido.py:164; tests/test_api_solido.py::test_extrude_cut_flotante_va_hacia_el_material | 2026-10-20 |
| B-13 | Franjas claras en superficies de solevación (normales del teselado) | Corregido | — | — | ui/visor3d.py:186 (rc.malla_suave); tests/test_render.py::test_malla_suave_solevacion_sin_franjas_dentadas | 2026-10-20 |
| B-15 | Cilindro Ø28 facetado en el render | Corregido | — | — | nucleo/render_cpu.py:34-59 (deflexion_para por pieza); tests/test_render_rapido.py::test_deflexion_depende_de_pixeles_y_conserva_el_primer_plano; tests/test_graficos_rendimiento.py::test_deflexion_automatica_sigue_al_tamano_con_topes | 2026-10-20 |
| B-16 | execute_code en vivo congela la ventana sin poder cancelar | Corregido | — | — | commits a5b356a, 7514dd6 (en motor-omnikernel); tests/test_b16_cancelar.py::test_latido_que_cancela_corta_revierte_y_respeta_el_intervalo; ::test_execute_code_en_vivo_dialogo_cancela_y_la_cola_espera; api/herramientas_avanzado.py:840 (CODE_CANCELLED) | 2026-10-20 |
| B-20 | Render de 2048×2048 tarda 18 s | Corregido | — | — | commit 3ec54fa; tests/test_b20_raster.py::test_triangulo_fino_no_reserva_profundidad_de_toda_su_caja | 2026-10-20 |
| B-21 | omnicad.log se pisa en cada arranque | Corregido | — | — | clon/OmniCAD.py:24-38 (RotatingFileHandler); tests/test_io.py::test_log_se_enroula_y_no_se_pisa | 2026-10-20 |
| B-22 | Autoguardados de documentos sin título se pisan entre sí | Corregido | — | — | io_archivos/proyecto.py:282,328; timeline/documento.py:136; tests/test_io.py (autoguardado por token, línea 292) | 2026-10-20 |
| B-23 | create_* no aceptan name | Corregido | — | — | api/herramientas_solido.py:319; tests/test_api_solido.py (líneas 644 y 655) | 2026-10-20 |
| B-24 | rename no actualiza Cuerpo.nombre del estado | Corregido | — | — | tests/test_api_documento.py:484 (rename cambia Cuerpo.nombre) | 2026-10-20 |
| B-25 | Reglas de chapa propias no aparecen en la interfaz | Corregido | — | — | ui/comandos/chapa.py; tests/test_comandos.py:166 | 2026-10-20 |
| B-27 | set_parameter rompe la revolución: el perfil ya no existe | Corregido | — | — | nucleo/perfiles.py:345 (buscar_por_firma_tolerante); tests/test_api_solido.py::test_perfil_se_reenlaza_cuando_el_contorno_cambia | 2026-10-20 |
| B-28 | join tangente deja aristas libres: cuerpo no cerrado | Corregido | — | — | nucleo/geometria.py:337 (_quitar_cables_colgados); tests/test_geometria.py::test_union_tangente_no_deja_aristas_libres | 2026-10-20 |
| B-29 | create_hole en cara −Z: eje Y del boceto contradice la doc | Corregido | — | — | api/herramientas_boceto.py:659 y api/guia/selectores.md:28 (corregida la doc; el marco no cambia por diseño) | 2026-10-20 |
| B-30 | Herramienta que no corta nada deja el paso ok sin aviso | Corregido | — | — | timeline/operaciones.py:358,367 y 982; tests/test_api_documento.py:507; tests/test_api_solido.py::test_el_corte_que_no_toca_avisa_en_el_timeline | 2026-10-20 |
| B-31 | create_thread auto dice sin datos aunque thread_info lista clases | Corregido | — | — | api/herramientas_modificar.py:611; tests/test_api_modificar.py:454 | 2026-10-20 |
| B-32 | Copia de patrón de cuerpos no hereda el nombre | Corregido | — | — | tests/test_api_solido.py (líneas 663 y 671: «nombre (copia)») | 2026-10-20 |
| B-33 | get_sketch: clave status contra descripción «estado» | Corregido | — | — | api/herramientas_boceto.py:929 (descripción dice «clave status») | 2026-10-20 |
| B-34 | get_sheet_metal_info muestra nombre de regla que no corresponde | Corregido | — | — | api/herramientas_chapa.py:241; tests/test_api_chapa.py:302-304 | 2026-10-20 |
| B-35 | CSV de lista de materiales sin BOM: Excel muestra Âº y mmÂ³ | Corregido | — | — | api/herramientas_material.py:250; ui/administrar.py:119 (utf-8-sig); tests/test_api_material.py:141-148 | 2026-10-20 |
| B-36 | execute_code con llamar a herramienta inexistente da ok sin efecto | Corregido | — | — | api/herramientas_avanzado.py:810,850; tests/test_api_avanzado.py:467 y :477 | 2026-10-20 |
| B-37 | join tangente: ok pero aristas no manifold sin aviso | Corregido | — | — | timeline/operaciones.py:349 (aviso partido/abierto) y :1004; tests/test_documento.py::test_combinar_avisa_si_la_union_no_fusiona_lo_que_se_toca | 2026-10-20 |
| B-38 | join con tope coplanar absorbe un cuerpo ajeno en silencio | Corregido | — | — | timeline/operaciones.py:335; tests/test_api_solido.py:124 (aviso «solo una cara») | 2026-10-20 |
| B-40 | repair_body puede empeorar el cuerpo sin avisar | Corregido | — | — | timeline/ops_revision.py:46; tests/test_revision.py::test_paso_reparar_no_empeora_en_silencio | 2026-10-20 |
| B-42 | fillet con lista de un id da INVALID_SELECTOR | Corregido | — | — | api/selectores.py:417; tests/test_api_selectores.py:349-359 | 2026-10-20 |
| B-44 | create_thread modelada en perno Ø5×50 falla con surco mal armado | Corregido | — | — | tests/test_api_modificar.py::test_create_thread_m5_largo_completo_no_empuja_al_kernel_al_mal_surco | 2026-10-20 |
| B-45 | Selector %CIRCLE and nearest: da NO_MATCH | Corregido | — | — | api/selectores.py:33; tests/test_api_selectores.py:387 | 2026-10-20 |
| B-46 | drive_joint informa traslaciones que no cuadran con el giro | Corregido | — | — | api/herramientas_ensamble.py:278 (delta_translation); tests/test_api_ensamble.py:246-256 | 2026-10-20 |
| B-47 | Build instalado no abre proyectos del build del repo | Corregido | — | — | io_archivos/proyecto.py:252-258 (mensaje «versión más nueva aunque comparta el número»); tests/test_regresiones.py::test_receta_con_operacion_desconocida_da_error_de_proyecto (solo comprueba el tipo de error) | 2026-10-20 |
| B-51 | Eje de giro de unión «como está» depende de marco sin documentar | Corregido | — | — | api/herramientas_ensamble.py:16 (docstring con el marco); solo documentación | 2026-10-20 |
| B-53 | create_cylinder acepta height=1e9 | Corregido | — | — | api/herramientas_solido.py:97; tests/test_api_solido.py:631; tests/test_resultados_vacios.py:114 | 2026-10-20 |
| B-54 | rename permite nombres duplicados | Corregido | — | — | api/herramientas_documento.py:712; tests/test_api_documento.py:494 (avisa AMBIGUOUS_REFERENCE) | 2026-10-20 |
| B-55 | sketch_circular_pattern materializa un punto extra en el centro | Corregido | — | — | restricciones/boceto.py:2530; tests/test_api_boceto_herramientas.py:527 y :539 | 2026-10-20 |
| B-56 | add_dimension distance depende del orden línea-punto | Corregido | — | — | tests/test_api_boceto.py:536-542 | 2026-10-20 |
| B-57 | Argumentos numéricos opcionales llegan como texto desde OpenCode | Corregido | — | — | api/registro.py:169,216; tests/test_api_avanzado.py:501 | 2026-10-20 |
| B-59 | Rosca M5 modelada deja 33 aristas no manifold | Corregido | — | — | tests/test_api_modificar.py::test_create_thread_m5_salientes_sin_aristas_no_manifold | 2026-10-20 |
| B-62 | labio con invertir=false no agrega nada y no avisa | Corregido | — | — | timeline/ops_solido.py:890; tests/test_api_modificar.py::test_labio_que_no_cambia_nada_avisa | 2026-10-20 |
| B-63 | descoser/destrimar con listas vacías dan ok sin efecto | Corregido | — | — | tests/test_api_avanzado.py:454-464 | 2026-10-20 |
| B-64 | set_joint_limits acepta mínimo mayor que máximo | Corregido | — | — | api/herramientas_ensamble.py:395; tests/test_api_ensamble.py:246-256 | 2026-10-20 |
| B-65 | Origen de unión por nearest: bloquea todo drive_joint | Corregido | — | — | tests/test_api_ensamble.py::test_origen_de_union_sobrevive_al_drive_del_componente | 2026-10-20 |
| B-66 | parche con curva abierta devuelve el error crudo del kernel | Corregido | — | — | nucleo/superficies.py:485; tests/test_superficies.py:282 | 2026-10-20 |
| B-67 | convert_to_sheet_metal informa altura como «espesor medido» | Corregido | — | — | nucleo/chapa.py:1191; tests/test_chapa.py:345 | 2026-10-20 |
| B-68 | Exportar a STEP omite cuerpos de malla sin avisar | Corregido | — | — | api/herramientas_documento.py:505; io_archivos/exportar.py:45; tests/test_api_documento.py:468 | 2026-10-20 |
| B-69 | find_faces con %PLANE and >Z da NO_MATCH | Corregido | — | — | api/selectores.py:33; tests/test_api_selectores.py:370 | 2026-10-20 |
| B-70 | create_hole roscado Tr12×3 falla por el eje ajeno en el documento | Corregido | — | — | commit c91a6da; tests/test_b70_pasante.py::test_pasante_roscado_no_se_alarga_por_un_cuerpo_ajeno | 2026-10-20 |
| B-72 | La prueba de humo falla en «Tecla S dentro del boceto» | Corregido | — | — | prueba_humo.py:279; commit 6049c70 (humo 2/2 según la ficha, no re-corrida acá) | 2026-10-20 |
| B-73 | encuadrar() deja la pieza larga chica en imagen apaisada | Corregido | — | — | commit 885106c; tests/test_hallazgos_ui.py::test_encuadrar_pieza_larga_respeta_el_aspecto_de_la_ventana | 2026-10-20 |
| B-74 | get_viewport_image tarda 10-19 s con 85 cuerpos | Corregido | — | — | commit 8ed55c0 (en motor-omnikernel); tests/test_render_rapido.py (límite 5,95 s) | 2026-10-20 |
| B-75 | set_decal en cara cilíndrica recortada queda corrido; render CPU no la dibuja | Corregido | — | — | commit b93f278 (en motor-omnikernel); tests/test_calcomania_cilindro.py | 2026-10-20 |
| B-76 | check_printability marca paredes finas falsas en aristas agudas | Corregido | — | — | nucleo/revision.py:774; tests/test_revision.py:144; commit 2f686fa (también en main) | 2026-10-20 |
| B-77 | sketch_from_spec: líneas en cadena no comparten esquina | Corregido | — | — | tests/test_api_boceto.py::test_spec_lineas_seguidas_comparten_la_esquina; commit 2f686fa | 2026-10-20 |
| B-78 | El cliente del puente corta a los 120 s en motion_study largo | Corregido | — | — | servidor_mcp/puente_cliente.py:20-22 (300 s); tests/test_puente_mcp.py:148; commit 2f686fa | 2026-10-20 |
| B-79 | Rosca interior y exterior no encajan (medio paso corrido) | Corregido | — | — | nucleo/solidos_crear.py:2116,2203; tests/test_api_modificar.py:344; tests/test_solidos_crear.py:552; commit 2f686fa | 2026-10-20 |
| B-81 | Menú del cuerpo en el navegador sin opacidad, aislar ni aspecto | Corregido | — | — | ui/acciones_navegador.py; tests/test_p23_navegador.py::test_menu_del_cuerpo_trae_opacidad_aislar_y_aspecto | 2026-10-20 |
| B-82 | Lo que oculta set_browser_visibility no se guarda | Corregido | — | — | commit 885106c; tests/test_p23_navegador.py::test_cuerpo_oculto_persiste_al_guardar_y_reabrir | 2026-10-20 |
| AUD-14 | Lectura de ZIP del complemento Fusion sin tope de tamaño | Corregido | — | — | tests/test_abrir_externo.py::test_f3z_con_un_miembro_gigante_no_se_extrae | 2026-10-20 |
| P-10b-k | Bug latente de la caché de ui/analisis_vista.py (id sin retener la forma) | Corregido | — | — | omnicad/ui/analisis_vista.py:39-47; tests/test_hallazgos_ui.py::test_cache_de_analisis_retiene_la_forma_de_su_clave | 2026-10-20 |
| P-11b | Descartar cuerpos viejos del historial que Fusion no tiene | Corregido | — | — | omnicad/io_archivos/f3d_escena.py:322-348 (descartados); tests/test_p11a_f3d_instancias.py:194,206,221 | 2026-10-20 |
| P-11c | Piezas espejo con la misma caja y volumen no se cruzan | Corregido | — | — | tests/test_p11a_f3d_instancias.py::test_dos_piezas_espejo_con_la_misma_caja_y_volumen_no_se_cruzan; Límite: Límite: piezas quirales con el mismo centro de masa siguen indistinguibles. | 2026-10-20 |
| P-11d | b) Caras inválidas (cono con ápice, spline con polo) en la cartera gótica | Corregido | — | — | tests/test_f3d_nativo.py; omnicad/nucleo/acis_occ.py (_cerrar); PROJECT_LOG.md:32 (11 cuerpos válidos) | 2026-10-20 |
| P-11e | c) Cuerpos con aristas de 4 caras y toro de una sola cara entran como sólido | Corregido | — | — | omnicad/nucleo/acis_occ.py:532 (BOPAlgo_MakerVolume); tests/test_f3d_nativo.py:451; Límite: Sin ejemplo a mano de mallas convertidas (BINCHA): no probado con ese archivo. | 2026-10-20 |
| T-01 | check_geometry colgaba la app con roscas modeladas | Corregido | — | — | tests/test_hallazgos_tortura.py::test_t01_el_hijo_se_mata_al_pasar_el_tope | 2026-10-20 |
| T-02 | export_hidden_line_svg colgaba la app con roscas | Corregido | — | — | tests/test_hallazgos_tortura.py::test_t02_si_el_exacto_no_termina_sigue_el_rapido_o_falla_si_se_pidio_exacto | 2026-10-20 |
| T-03 | Referencias perdidas con cambios de cota moderados | Corregido | — | — | tests/test_hallazgos_tortura.py::test_t03_el_chaflan_del_borde_tras_un_vaciado_sobrevive_a_un_cambio_de_cota_del_29_por_ciento | 2026-10-20 |
| T-05 | repair_mesh y clean_mesh decían ok con la malla abierta | Corregido | — | — | tests/test_hallazgos_tortura.py::test_t05_reparar_o_limpiar_una_malla_que_sigue_abierta_lo_avisa | 2026-10-20 |
| T-06 | add_text sin tope de largo | Corregido | — | — | tests/test_hallazgos_tortura.py::test_t06_un_texto_demasiado_largo_o_gigante_se_rechaza | 2026-10-20 |
| T-07 | Sin validación de rango en longitudes y ángulos | Corregido | — | — | tests/test_hallazgos_tortura.py::test_t07_valores_absurdos_se_rechazan_sin_tocar_el_documento | 2026-10-20 |
| T-08 | JSON anidado al abrir daba INTERNAL_ERROR | Corregido | — | — | tests/test_hallazgos_tortura.py::test_t08_un_json_roto_tambien | 2026-10-20 |
| T-09 | create_joint pisaba otra unión sin avisar | Corregido | — | — | api/herramientas_ensamble.py (aviso); informe T-09 | 2026-10-20 |
| T-10 | trace_image invertido se pasaba del contorno | Corregido | — | — | tests/test_hallazgos_tortura.py::test_t10_trace_image_con_tinta_invertida_pegada_al_borde_no_se_pasa_de_largo | 2026-10-20 |
| T-11 | drive_joint guardaba un valor que ignoraba | Corregido | — | — | api/herramientas_ensamble.py; informe T-11 | 2026-10-20 |
| T-12 | move_sketch_point decía reached:false estando exacto | Corregido | — | — | tests/test_hallazgos_tortura.py::test_t12_reached_distingue_un_residuo_submilimetrico_de_un_destino_imposible | 2026-10-20 |
| T-13 | shell tras un chaflán culpaba a cortes o agujeros | Corregido | — | — | tests/test_hallazgos_tortura.py::test_t13_vaciar_despues_de_un_chaflan_en_el_borde_dice_que_el_chaflan_va_despues | 2026-10-20 |
| T-14 | insert_file no aceptaba .brep; 3MF de 2 cuerpos volvía en 1 | Corregido | — | — | tests/test_hallazgos_tortura.py::test_t14_insert_file_acepta_brep | 2026-10-20 |
| T-15 | Diálogo de recuperados bloqueaba el puente (APP_BUSY) | Corregido | — | — | OmniCAD.py --puente; informe T-15 | 2026-10-20 |
| T-16 | Mensajes engañosos en export e insert_dxf; nombres repetidos | Corregido | — | — | tests/test_hallazgos_tortura.py::test_t16_export_con_ruta_vacia_o_de_carpeta_es_un_argumento_invalido | 2026-10-20 |
| T-17 | Cosméticos: -0.0, -(-4), conteo de realize_copies | Corregido | — | — | tests/test_hallazgos_tortura.py::test_t17_realize_copies_cuenta_solo_las_copias_de_su_paso | 2026-10-20 |
| B-06 | fillet quita 1,4 % más volumen que la cuenta, sin avisar | No reproducido | — | Reabrir si vuelve, con el modelo de la Prueba 9. | Medición del 2026-10-13 citada en la ficha (−3,35 %, correcto); sin test propio | 2026-10-20 |
| B-11 | Corte desde cara de cuerpo partido no quita material, sin error | No reproducido | — | Reabrir si reaparece el caso del reporte. | Verificación del 2026-10-13 citada en la ficha (REFERENCE_LOST avisa); sin test propio | 2026-10-20 |
| B-17 | Bucle de 20 create_box en vivo supera los 100 s | No reproducido | — | No se midió el repintado OpenGL en el escritorio real del usuario. | Medición 2026-10-15 en la ficha: 0,50 s por 20 llamadas; sin código nuevo | 2026-10-20 |
| B-18 | Rosca M3 modelada tarda 7,5 s por agujero y bloquea | No reproducido | — | Falta el modelo exacto de Prueba 2 y probar cancelar desde la interfaz. | Medición 2026-10-15 en la ficha: 1,18 s/agujero; privado/reportes/b18_*.txt | 2026-10-20 |
| B-19 | .omnicad de 55 pasos tarda 44 s al abrir | No reproducido | — | No se halló el modelo original de 55 pasos. | Medición 2026-10-15 en la ficha: reabrir con caché 0,38 s; 7 pasos cacheados no se ejecutan | 2026-10-20 |
| B-26 | Llamada MCP fantasma con argumentos fusionados en payloads largos | No reproducido | — | No se probó el cliente Cline original. | tests/test_servidor_mcp.py::test_payloads_largos_consecutivos_no_mezclan_argumentos (memoria y stdio) | 2026-10-20 |
| B-49 | fold rechaza la cara superior de una pestaña base | No reproducido | — | Reabrir si reaparece con el soporte exacto. | tests/test_api_chapa.py::test_plegar_pestana_base_sobre_la_cara_de_arriba | 2026-10-20 |
| B-58 | Agujeros de brida a r=29,57 en vez de 30,5 en el motor | No reproducido | — | Si reaparece, guardar el .omnicad del momento exacto. | Recálculo y repro mínima exactas (r=30,5) según la ficha; commit db0f0cf | 2026-10-20 |
| B-61 | sup_barrido produce superficie 12 veces mayor en el gabinete | No reproducido | — | Si reaparece, guardar el .omnicad del momento exacto. | Repro guardada da área exacta 1973,92 mm² (commit fa39b03) | 2026-10-20 |
| B-12 | create_hole con face no resuelve el id dentro de execute_code | Retirado | — | — | tests/test_api_avanzado.py::test_create_hole_resuelve_ids_de_cara_dentro_de_execute_code | 2026-10-20 |
| B-14 | Vista right del render muestra la trasera del auto | Retirado | — | — | tests/test_api_inspeccion.py::test_vistas_estandar_como_el_viewcube_de_fusion (decisión: eje de cámara como ViewCube) | 2026-10-20 |
| B-41 | Lista de materiales no agrupa cuerpos sueltos | Retirado | — | — | Retirada por el propio reporte (tanda 3): sí agrupa componentes | 2026-10-20 |
| B-43 | check_interference da 242 mm³ en contacto cara con cara | Retirado | — | — | Verificado 2026-10-13 en la ficha: el solape es real; filtro del falso positivo = B-07 (tests/test_analisis.py:94) | 2026-10-20 |
| B-60 | bbox de cuerpo multicáscara mezcla las cajas | Retirado | — | — | Verificado 2026-10-13 en la ficha: la bbox por eje es correcta; causa real = B-52 | 2026-10-20 |

## Detalle de lo abierto

Ficha original de cada bug abierto o parcial (del PROJECT_LOG al 2026-10-20). Lo que diga la tabla
de arriba manda sobre este texto.

### B-05 · Barrido con torsión 90° pierde 2,1 % de volumen

Barrido con torsión de 90°: pierde 2,1 % de volumen (391,67 contra 400 mm³).

barrido

Corregido en rutas abiertas (el modo plano exacto manda; el fallback curvilíneo persiste y queda documentado en `_guia_plana_posible`)

Prueba 10

### B-09 · Boceto sobre cara no asociativo: el corte queda en el aire

Boceto sobre cara no es asociativo. Si cambia `ancho`, el corte queda en el aire: sale el aviso «La herramienta no toca ningún cuerpo» y la abertura desaparece, sin error.

boceto sobre cara

Verificado con la máquina: ese corte ya queda en warning en el paso (regresión `test_el_corte_que_no_toca_avisa_en_el_timeline`); la asociatividad completa (el corte sigue al material al editar el cuerpo) es el cambio de diseño registrado en el estado

Prueba 2

### B-39 · join con herramienta enterrada deja arista libre y cuerpo no estanco

`boolean_operation join` con herramienta 100 % enterrada (cilindro r2,5 en la carcasa): suma 0 (correcto) pero deja una arista libre en (27, 0, 129,5); cuerpo no estanco. Determinista: sobrevive a recalcular todo. Solo se cura borrando los pasos.

`boolean_operation`

Corregido el 2026-10-14 por el mismo aviso post-join de cuerpo partido/no estanco. Repro de la arista queda sin cura (kernel)

Reproducido

Crítico

### B-48 · Crash nativo OCCT (0xc0000005) al recalcular parámetros a 148 pasos

**Mitigado 2026-10-20** (`agente/b48`): no se reprodujo en 18 min; la caída de un hijo aislado vuelve como `TareaAislada`. Sigue abierto. **Crash nativo durante la tortura de parámetros** (±30 % a 148 pasos): APPCRASH de `pythonw.exe`, excepción 0xc0000005 en `TKernel-….dll` (OCCT 8.0.1) offset 0x78bed, 09:11:23; el puente murió a mitad de llamada (`BRIDGE_ERROR WinError 10054`). El autoguardado (receta sin caché, 18 s antes) permitió recuperar todo. Evento completo en `crash2_evento_completo.txt`.

kernel OCCT vía cadquery_ocp; recálculo

Reproducido (firma de Windows): no se puede curar desde la app; queda la protección por autoguardado

Crítico

### B-50 · create_joint snapea por centro de cara y desplaza componentes

`create_joint` (normal) snapea por centro de cara y desplaza componentes: slider con caras de distinta longitud movió el vástago −4 mm (quedó dentro de la brida); revolute con origen en un agujero pasante PARTIDO (sin segmento centrado) movió TODA la Ferretería +13,99 mm en X. Esquive: uniones «como está» + `drive_joint` corrector.

ensamble / `create_joint`

Corregido el 2026-10-14 en el anclaje: un contorno plano partido por arcos concéntricos + líneas radiales toma el centro del círculo (no el centroide corrido). Regresión: `test_union_contra_cara_anular_partida_engancha_el_circulo`. Caras de distinto largo con slider: sigue (el snap al centro es la semántica elegida)

Reproducido

Medio

### B-52 · Unión de espiral: fusión degenerada, pérdida silenciosa y STEP en dos sólidos

La unión de la espiral de refrigeración (bobina cónica con 0,5 mm de incrustación contra la campana) es una **fusión degenerada**: Cuerpo1 queda NO estanco (1 arista libre + 18 no manifold); suprimir el chaflán del labio (op28, ajeno) hace perder la espiral en silencio (−3.118 mm³, sin error ni aviso; vuelve al reactivar, 2 ciclos); el bbox del cuerpo mezcla las cajas de sus carcasas (xy de la campana con z de la espiral, ocultando r44,5); y el STEP exportado entra como DOS sólidos (bloque 150.657,28 + espiral 3.495,73) que suman el volumen que el .omnicad reporta como uno. Familia B-37 (tangencias) en «join».

booleana `join` con contacto en cuña; `suppress_feature`; bbox multicáscara

Corregido el 2026-10-15 en la DETECCIÓN (la degeneración del kernel no se puede curar, familia B-37): OpCombinar no tenía NINGÚN chequeo post-unión (op121 nunca avisaba) y la espiral se perdía al unir DESPUÉS una primitiva (op48 Caja3) al cuerpo compuesto: la fusión descartaba el sólido de la espiral (−3.193,74 mm³, sólidos 2→1, estanca=True: invisible para el chequeo de estanqueidad). Ahora toda unión avisa si PIERDE material (con los mm³) y OpCombinar avisa si explota en sólidos, si no fusiona lo que se tocaba o si queda abierto; unir cuerpos que no se tocan (multi-sólido legítimo, como el aro+toroide del ejemplo) sigue sin avisar. En la copia del motor recalculada: op28 activo → op121 avisa «partido/sin fusionar»; op28 suprimido → op48 avisa «perdió 3193,74 mm³». Volúmenes bit-idénticos. Regresiones en test_documento (toque sin fusión, pérdida en Combinar y en primitiva)

Crítico

### B-71 · Uniones encadenadas: el lazo cerrado biela-manivela no se resuelve

Uniones «como esta» encadenadas: `drive_joint` sobre una union resuelve bien el componente directo, pero el componente atado via la union del codo no sigue (lazo sin resolver, herede la «SIN LAZOS CERRADOS» de la Prueba 4) Y, peor: los drives sucesivos volvieron `REFERENCE_LOST` las uniones U_apoyo_* hasta borrarlas. Refuerza B-65.

ensamble / `drive_joint` + uniones en cadena

Parcialmente corregido el 2026-10-14: los REFERENCE_LOST de las uniones de apoyo (B-65) quedan curados por el resolver invariante de referencias; la parte del «lazo en cadena» (la física de una unión que sigue a otra posterior en el timeline) queda abierta como limitación documentada

Reproducido en gatoRL (6 uniones)

Alto

### B-80 · MCP sin herramientas para ANIMACIÓN, DIBUJO ni RENDERIZAR

**Ola 1 hecha 2026-10-20** (`agente/b80`): requisitos MCP-0a a 0e y 15 herramientas de ANIMACIÓN; faltan las olas 2 a 7. Un agente no puede usar ANIMACIÓN, DIBUJO ni RENDERIZAR: ninguna de las 190 herramientas los toca. Además, 31 claves de la cinta no tienen herramienta y 54 solo funcionan por `run_operation` (38 de 95 tipos). Rompe la regla «MCP y CLI siempre completos» de `CLAUDE.md`. Visto al pedir que se animara el rotor del motor impreso: solo se pudo mover la unión con `drive_joint`, de a pasos de 2-3 s.

`api/` frente a `ui/animacion.py`, `ui/dibujo.py`, `ui/render.py`, `ui/cinta.py`

Reproducido. Plan en `docs/brechas_mcp.md` (MCP-0a a MCP-55)

alto
