# Comparación de motores: OpenCascade y OmniKernel

Generado por `scripts/comparar_motores.py` el 2026-10-19 01:49. Cada medición corre en un proceso aparte con un solo motor; el lado OmniKernel con `OMNICAD_BLOQUEAR_OCP=1`. Los tiempos de operación incluyen construir la entrada (caja, boceto). «Resultado igual» = la prueba de paridad de `clon/tests/test_paridad_motor.py` (volumen, área, conteos, validez y firmas).

## Operaciones

| Operación | OCC (ms) | OmniKernel (ms) | Resultado igual |
|---|---|---|---|
| caja | 1.0 | 4.2 | sí |
| cilindro | 0.7 | 3.6 | sí |
| toroide | 0.6 | 3.5 | sí |
| trasladar | 1.0 | 4.2 | sí |
| rotar | 1.1 | 4.5 | sí |
| unir | 12.0 | 18.0 | sí |
| cortar | 10.7 | 16.4 | sí |
| intersecar | 10.9 | 17.4 | sí |
| unir_l | 16.2 | 15.8 | sí |
| extruir_rectangulo | 317.2 | 6.1 | sí |
| extruir_simetrica | 317.9 | 5.7 | sí |
| extruir_xz | 313.0 | 5.4 | sí |
| extruir_dos | 332.6 | 15.4 | sí |
| extruir_sobre_cara | 346.6 | 45.3 | sí |
| empalme | 5.3 | 21.5 | sí |
| empalme_dos | 7.8 | 26.6 | sí |
| chaflan | 5.2 | 36.3 | sí |
| vaciado | 11.0 | 42.2 | sí |
| cara_l | 16.5 | 22.2 | sí |
| perfil_rectangulo | 317.4 | 4.0 | sí |
| perfil_elipse_vertical | 315.0 | 2.3 | sí |
| perfil_con_curva_rota | 314.5 | 2.8 | sí |
| vaciado_dos_caras | 13.4 | 48.0 | sí |
| desfasar_caras | 7.3 | 351.8 | sí |
| desmoldeo | 2.6 | 306.0 | sí |
| quitar_caras | 13.8 | 326.1 | sí |
| caja@step | 21.9 | 10.5 | sí |
| cilindro@step | 20.4 | 10.8 | sí |
| caja@iges | 16.5 | 19.6 | sí |
| cilindro@iges | 14.3 | 18.4 | sí |
| unir_l@step | 39.6 | 31.3 | sí |
| esfera | 0.6 | 3.4 | sí |
| extruir_circulo | 315.6 | 4.3 | sí |
| revolver_rectangulo | 311.2 | 5.0 | sí |
| revolver_arco | 309.0 | 5.4 | sí |
| cortar_cilindro | 11.9 | 222.0 | sí |
| agujero_pasante | 12.0 | 309.8 | sí |
| unir_cilindro | 11.7 | 235.1 | sí |
| intersecar_cilindro | 9.1 | 169.6 | sí |
| empalme_esquina | 11.2 | 33.7 | sí |
| chaflan_esquina | 10.2 | 109.3 | sí |
| extruir_con_agujero | 315.2 | 6.7 | sí |
| unir_dos_cuerpos | 37.0 | 40.6 | sí |
| revolver_negativo | 327.8 | 5.1 | sí |
| cremallera | 64.8 | 133.9 | sí |
| simetria | 16.0 | 18.9 | sí |
| patron_rectangular | 5.7 | 41.6 | sí |
| patron_circular | 5.7 | 91.2 | sí |
| patron_puntos | 3.9 | 18.7 | sí |
| multitransformacion | 5.0 | 26.1 | sí |
| agujero_punta | 1.4 | 15.2 | sí |
| agujero_plano | 1.4 | 9.0 | sí |
| agujero_abocardado | 1.7 | 17.2 | sí |
| agujero_avellanado | 2.0 | 15.3 | sí |
| agujero_en_caja | 13.5 | 174.1 | sí |
| empalme_cilindro | 2.4 | — | no (MOTOR_SIN_SOPORTE) |
| chaflan_cilindro | 3.9 | — | no (MOTOR_SIN_SOPORTE) |
| vaciado_cilindro | 6.4 | — | no (MOTOR_SIN_SOPORTE) |
| desfasar_cilindro | 21.5 | — | no (MOTOR_SIN_SOPORTE) |
| desfasar_lateral | 7.5 | — | no (MOTOR_SIN_SOPORTE) |
| desmoldeo_cilindro | 2.3 | — | no (MOTOR_SIN_SOPORTE) |

## Documentos guardados

Recálculo completo (`Documento.recalcular(0)`) de cada `.omnicad` de `evidencias/`.

| Documento | Pasos | OCC (s) | OmniKernel (s) | Resultado con OmniKernel |
|---|---|---|---|---|
| `evidencias/barrido/barrido_funciones.omnicad` | 4 | 0.00 | 0.00 | OK |
| `evidencias/barrido_total/op999.omnicad` | 8 | 0.00 | 0.00 | OK |
| `evidencias/barrido_total/x.omnicad` | 8 | 0.00 | 0.01 | OK |
| `evidencias/barrido_total/x_suelto.omnicad` | 8 | 0.00 | 0.00 | OK |
| `evidencias/barrido_total/zzz.omnicad` | 8 | 0.00 | 0.00 | OK |
| `evidencias/caja/caja_electronica.omnicad` | 55 | 9.15 | 54.94 | MOTOR_SIN_SOPORTE (8 pasos; primero op8 saliente: consultas.vertice) |
| `evidencias/campana_vivo_2026-10-11/Botella_Asa_Loft_Sweep.autoguardado.omnicad` | 11 | 0.25 | 0.01 | MOTOR_SIN_SOPORTE (2 pasos; primero op6 solevacion: solidos_crear.solevar) |
| `evidencias/campana_vivo_2026-10-11/Botella_Asa_Loft_Sweep.omnicad` | 11 | 0.26 | 0.01 | MOTOR_SIN_SOPORTE (2 pasos; primero op6 solevacion: solidos_crear.solevar) |
| `evidencias/campana_vivo_2026-10-11/Caja_Tapa_Ventilada.omnicad` | 7 | 0.12 | 1.84 | FALLA (op6 agujero: booleana curva: el resultado no cierra (685 aristas sueltas: [-1.0000, -0.2500, 3.0000]→[-1.0000, -0.7500, 3.0000], [-1.) |
| `evidencias/campana_vivo_2026-10-11/Copa_Revolucion.omnicad` | 2 | 0.01 | 0.01 | OK |
| `evidencias/campana_vivo_2026-10-11/Ensamblaje_Crank.omnicad` | 8 | 0.01 | 0.03 | MOTOR_SIN_SOPORTE (2 pasos; primero op7 union: consultas.contorno_exterior) |
| `evidencias/campana_vivo_2026-10-11/Pieza_Malla.omnicad` | 2 | 0.00 | 0.00 | MOTOR_SIN_SOPORTE (1 pasos; primero op2 teselar: malla.desde_brep) |
| `evidencias/campana_vivo_2026-10-11/Soporte_Chapa.omnicad` | 4 | 0.04 | 0.00 | MOTOR_SIN_SOPORTE (1 pasos; primero op2 pestana: geometria.transformar (Transformar una cara, arista o vértice suelto.)) |
| `evidencias/campana_vivo_2026-10-11/Soporte_L.autoguardado.omnicad` | 5 | 0.10 | 42.91 | FALLA (op4 agujero: intersección cancelada) |
| `evidencias/campana_vivo_2026-10-11/Soporte_L.omnicad` | 5 | 0.10 | 42.50 | FALLA (op4 agujero: intersección cancelada) |
| `evidencias/chapa/soporte_chapa.omnicad` | 18 | 0.41 | 0.09 | MOTOR_SIN_SOPORTE (4 pasos; primero op2 pestana: geometria.transformar (Transformar una cara, arista o vértice suelto.)) |
| `evidencias/g_class/g_class.autoguardado.omnicad` | 57 | 2.70 | 32.69 | MOTOR_SIN_SOPORTE (4 pasos; primero op54 union: consultas.eje_cara) |
| `evidencias/g_class/g_class.omnicad` | 61 | 2.70 | 32.80 | MOTOR_SIN_SOPORTE (4 pasos; primero op54 union: consultas.eje_cara) |
| `evidencias/gabineteRL_2026-10-12/casos_gabineteRL.omnicad` | 32 | 0.31 | 0.08 | MOTOR_SIN_SOPORTE (6 pasos; primero op2 labio: solidos_crear.labio_ranura) |
| `evidencias/gabineteRL_2026-10-12/gabinete.autoguardado.omnicad` | 99 | 5.65 | 0.10 | MOTOR_SIN_SOPORTE (17 pasos; primero op2 pestana: geometria.transformar (Transformar una cara, arista o vértice suelto.)) |
| `evidencias/gabineteRL_2026-10-12/gabinete.omnicad` | 99 | 5.68 | 0.12 | MOTOR_SIN_SOPORTE (17 pasos; primero op2 pestana: geometria.transformar (Transformar una cara, arista o vértice suelto.)) |
| `evidencias/gatoRL_2026-10-12/gatoRL.autoguardado.omnicad` | 113 | 59.12 | TIEMPO | TIEMPO: más de 300 s |
| `evidencias/gatoRL_2026-10-12/gatoRL.omnicad` | 113 | 58.97 | TIEMPO | TIEMPO: más de 300 s |
| `evidencias/k/claude_1_soporte/soporte.omnicad` | 4 | 0.05 | 0.96 | MOTOR_SIN_SOPORTE (1 pasos; primero op4 empalme: empalme sobre un cuerpo con caras curvas) |
| `evidencias/k/claude_2_caja/caja.omnicad` | 6 | 0.06 | 0.17 | OK |
| `evidencias/k/claude_3_brida/brida.omnicad` | 4 | 0.07 | 8.76 | MOTOR_SIN_SOPORTE (1 pasos; primero op2 chaflan: chaflán sobre un cuerpo con caras curvas) |
| `evidencias/lampara/lampara_onda.omnicad` | 17 | 0.16 | 0.06 | MOTOR_SIN_SOPORTE (2 pasos; primero op3 empalme: empalme sobre un cuerpo con caras curvas) |
| `evidencias/mecanismo/mecanismo_biela_manivela.omnicad` | 25 | 0.11 | 2.56 | MOTOR_SIN_SOPORTE (4 pasos; primero op19 union: consultas.eje_cara) |
| `evidencias/mesa_regulable/extras_omnikernel.omnicad` | 160 | 0.69 | 11.24 | OK |
| `evidencias/mesa_regulable/extras_opencascade.omnicad` | 168 | 2.53 | 49.22 | MOTOR_SIN_SOPORTE (3 pasos; primero op126 engranaje: engranajes.engranaje) |
| `evidencias/mesa_regulable/mesa_omnikernel.omnicad` | 152 | 0.63 | 10.60 | OK |
| `evidencias/mesa_regulable/mesa_opencascade.omnicad` | 159 | 2.44 | 48.91 | MOTOR_SIN_SOPORTE (2 pasos; primero op126 engranaje: engranajes.engranaje) |
| `evidencias/minifigura/minifigura.omnicad` | 36 | 0.24 | 109.68 | MOTOR_SIN_SOPORTE (2 pasos; primero op9 empalme: empalme sobre un cuerpo con caras curvas) |
| `evidencias/moka/cafetera_moka.omnicad` | 35 | 0.52 | 32.81 | MOTOR_SIN_SOPORTE (4 pasos; primero op6 solevacion: solidos_crear.solevar) |
| `evidencias/motor/motor.omnicad` | 174 | 7.30 | TIEMPO | TIEMPO: más de 300 s |
| `evidencias/motor_cohete/motor_cohete.omnicad` | 41 | 2.75 | TIEMPO | TIEMPO: más de 300 s |
| `evidencias/motor_impreso/motor_impreso.omnicad` | 292 | 24.67 | TIEMPO | TIEMPO: más de 300 s |
| `evidencias/mueble/mueble.omnicad` | 21 | 0.11 | 2.65 | OK |
| `evidencias/superficies/superficies_malla.omnicad` | 41 | 4.22 | 0.56 | MOTOR_SIN_SOPORTE (5 pasos; primero op8 sup_solevacion: perfiles.aristas_boceto) |
| `evidencias/tormenta_rl_test_2026-10-11/motor-rl-test.autoguardado.omnicad` | 70 | 37.61 | TIEMPO | TIEMPO: más de 300 s |
| `evidencias/tormenta_rl_test_2026-10-11/motor-rl-test.omnicad` | 72 | 37.68 | TIEMPO | TIEMPO: más de 300 s |
| `evidencias/tortura_2026-10-17/reductor_tortura.autoguardado.omnicad` | 82 | 11.01 | 6.93 | MOTOR_SIN_SOPORTE (13 pasos; primero op4 vaciado: vaciado sobre un cuerpo con caras curvas) |
| `evidencias/tortura_2026-10-17/reductor_tortura.omnicad` | 82 | 10.96 | 7.16 | MOTOR_SIN_SOPORTE (13 pasos; primero op4 vaciado: vaciado sobre un cuerpo con caras curvas) |
| `evidencias/torturaRL_2026-10-11/caso_patron_agujeros.omnicad` | 10 | 0.99 | 106.43 | MOTOR_SIN_SOPORTE (1 pasos; primero op7 agujero: geometria.booleano (pcurve sin imagen exacta bajo el cambio de parámetro)) |
| `evidencias/torturaRL_2026-10-11/motor-rl-tortura.autoguardado.autoguardado.omnicad` | — | TIEMPO | TIEMPO | TIEMPO: más de 300 s |
| `evidencias/torturaRL_2026-10-11/motor-rl-tortura.autoguardado.omnicad` | — | TIEMPO | TIEMPO | TIEMPO: más de 300 s |
| `evidencias/torturaRL_2026-10-11/motor-rl-tortura.omnicad` | — | TIEMPO | TIEMPO | TIEMPO: más de 300 s |

## Las 5 diferencias de tiempo más grandes

| Qué | OCC (s) | OmniKernel (s) | OmniKernel − OCC (s) |
|---|---|---|---|
| documento evidencias/mesa_regulable/extras_omnikernel.omnicad | 0.688 | 11.237 | +10.549 |
| documento evidencias/mesa_regulable/mesa_omnikernel.omnicad | 0.625 | 10.598 | +9.972 |
| documento evidencias/mueble/mueble.omnicad | 0.105 | 2.654 | +2.549 |
| operación desfasar_caras | 0.007 | 0.352 | +0.344 |
| operación revolver_negativo | 0.328 | 0.005 | -0.323 |
