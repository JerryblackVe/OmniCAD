# Comparación de motores: OpenCascade y OmniKernel

Generado por `scripts/comparar_motores.py` el 2026-10-18 16:31. Cada medición corre en un proceso aparte con un solo motor; el lado OmniKernel con `OMNICAD_BLOQUEAR_OCP=1`. Los tiempos de operación incluyen construir la entrada (caja, boceto). «Resultado igual» = la prueba de paridad de `clon/tests/test_paridad_motor.py` (volumen, área, conteos, validez y firmas).

## Operaciones

| Operación | OCC (ms) | OmniKernel (ms) | Resultado igual |
|---|---|---|---|
| caja | 1.0 | 4.5 | sí |
| cilindro | 0.7 | 4.0 | sí |
| toroide | 0.6 | 4.3 | sí |
| trasladar | 1.0 | 4.6 | sí |
| rotar | 1.1 | 5.0 | sí |
| unir | 11.8 | 25.6 | sí |
| cortar | 10.4 | 26.4 | sí |
| intersecar | 12.1 | 27.4 | sí |
| unir_l | 16.6 | 27.4 | sí |
| extruir_rectangulo | 332.8 | 8.4 | sí |
| extruir_simetrica | 342.3 | 8.4 | sí |
| extruir_xz | 325.1 | 7.8 | sí |
| extruir_dos | 350.6 | 27.8 | sí |
| extruir_sobre_cara | 402.8 | 81.0 | sí |
| empalme | 5.8 | 23.0 | sí |
| empalme_dos | 11.3 | 28.4 | sí |
| chaflan | 5.6 | 36.9 | sí |
| vaciado | 11.3 | 41.0 | sí |
| cara_l | 15.7 | 30.9 | sí |
| perfil_rectangulo | 345.8 | 4.9 | sí |
| perfil_elipse_vertical | 313.6 | 3.2 | sí |
| perfil_con_curva_rota | 336.1 | 3.6 | sí |
| vaciado_dos_caras | 13.6 | 50.0 | sí |
| desfasar_caras | 7.5 | 416.2 | sí |
| desmoldeo | 2.9 | 359.4 | sí |
| quitar_caras | 14.7 | 385.8 | sí |
| caja@step | 25.1 | 11.5 | sí |
| cilindro@step | 20.7 | 12.6 | sí |
| caja@iges | 16.5 | 18.0 | sí |
| cilindro@iges | 21.9 | 18.7 | sí |
| unir_l@step | 39.9 | 38.0 | sí |
| esfera | 0.6 | — | no (MOTOR_SIN_SOPORTE) |
| extruir_circulo | 346.6 | — | no (MOTOR_SIN_SOPORTE) |
| revolver_rectangulo | 338.2 | — | no (MOTOR_SIN_SOPORTE) |
| cortar_cilindro | 10.9 | — | no (MOTOR_SIN_SOPORTE) |
| agujero_pasante | 11.9 | — | no (MOTOR_SIN_SOPORTE) |
| unir_cilindro | 12.0 | — | no (MOTOR_SIN_SOPORTE) |
| intersecar_cilindro | 10.1 | — | no (MOTOR_SIN_SOPORTE) |
| empalme_esquina | 10.2 | — | no (MOTOR_SIN_SOPORTE) |
| chaflan_esquina | 9.7 | — | no (MOTOR_SIN_SOPORTE) |
| extruir_con_agujero | 375.9 | — | no (MOTOR_SIN_SOPORTE) |
| empalme_cilindro | 2.3 | — | no (MOTOR_SIN_SOPORTE) |

## Documentos guardados

Recálculo completo (`Documento.recalcular(0)`) de cada `.omnicad` de `evidencias/`.

| Documento | Pasos | OCC (s) | OmniKernel (s) | Resultado con OmniKernel |
|---|---|---|---|---|
| `evidencias/barrido/barrido_funciones.omnicad` | 4 | 0.00 | 0.00 | OK |
| `evidencias/barrido_total/op999.omnicad` | 8 | 0.00 | 0.00 | OK |
| `evidencias/barrido_total/x.omnicad` | 8 | 0.00 | 0.01 | OK |
| `evidencias/barrido_total/x_suelto.omnicad` | 8 | 0.00 | 0.00 | OK |
| `evidencias/barrido_total/zzz.omnicad` | 8 | 0.00 | 0.00 | OK |
| `evidencias/caja/caja_electronica.omnicad` | 55 | 9.60 | 4.08 | MOTOR_SIN_SOPORTE (19 pasos; primero op8 saliente: consultas.vertice) |
| `evidencias/campana_vivo_2026-10-11/Botella_Asa_Loft_Sweep.autoguardado.omnicad` | 11 | 0.29 | 0.01 | MOTOR_SIN_SOPORTE (2 pasos; primero op6 solevacion: solidos_crear.solevar) |
| `evidencias/campana_vivo_2026-10-11/Botella_Asa_Loft_Sweep.omnicad` | 11 | 0.28 | 0.01 | MOTOR_SIN_SOPORTE (2 pasos; primero op6 solevacion: solidos_crear.solevar) |
| `evidencias/campana_vivo_2026-10-11/Caja_Tapa_Ventilada.omnicad` | 7 | 0.12 | 0.11 | MOTOR_SIN_SOPORTE (4 pasos; primero op4 primitiva: revision._exigir_forma) |
| `evidencias/campana_vivo_2026-10-11/Copa_Revolucion.omnicad` | 2 | 0.01 | 0.01 | MOTOR_SIN_SOPORTE (1 pasos; primero op2 revolucion: geometria.revolver) |
| `evidencias/campana_vivo_2026-10-11/Ensamblaje_Crank.omnicad` | 8 | 0.01 | 0.02 | MOTOR_SIN_SOPORTE (2 pasos; primero op7 union: consultas.contorno_exterior) |
| `evidencias/campana_vivo_2026-10-11/Pieza_Malla.omnicad` | 2 | 0.00 | 0.00 | MOTOR_SIN_SOPORTE (1 pasos; primero op2 teselar: malla.desde_brep) |
| `evidencias/campana_vivo_2026-10-11/Soporte_Chapa.omnicad` | 4 | 0.04 | 0.00 | MOTOR_SIN_SOPORTE (1 pasos; primero op2 pestana: geometria.transformar (Transformar una cara, arista o vértice suelto.)) |
| `evidencias/campana_vivo_2026-10-11/Soporte_L.autoguardado.omnicad` | 5 | 0.11 | 0.15 | MOTOR_SIN_SOPORTE (3 pasos; primero op2 primitiva: revision._exigir_forma) |
| `evidencias/campana_vivo_2026-10-11/Soporte_L.omnicad` | 5 | 0.10 | 0.17 | MOTOR_SIN_SOPORTE (3 pasos; primero op2 primitiva: revision._exigir_forma) |
| `evidencias/chapa/soporte_chapa.omnicad` | 18 | 0.38 | 0.03 | MOTOR_SIN_SOPORTE (5 pasos; primero op2 pestana: geometria.transformar (Transformar una cara, arista o vértice suelto.)) |
| `evidencias/g_class/g_class.autoguardado.omnicad` | 57 | 2.78 | 2.69 | MOTOR_SIN_SOPORTE (17 pasos; primero op12 combinar: geometria.se_tocan) |
| `evidencias/g_class/g_class.omnicad` | 61 | 2.77 | 2.72 | MOTOR_SIN_SOPORTE (17 pasos; primero op12 combinar: geometria.se_tocan) |
| `evidencias/gabineteRL_2026-10-12/casos_gabineteRL.omnicad` | 32 | 0.32 | 0.06 | MOTOR_SIN_SOPORTE (6 pasos; primero op2 labio: solidos_crear.labio_ranura) |
| `evidencias/gabineteRL_2026-10-12/gabinete.autoguardado.omnicad` | 99 | 5.80 | 0.09 | MOTOR_SIN_SOPORTE (17 pasos; primero op2 pestana: geometria.transformar (Transformar una cara, arista o vértice suelto.)) |
| `evidencias/gabineteRL_2026-10-12/gabinete.omnicad` | 99 | 5.96 | 0.10 | MOTOR_SIN_SOPORTE (17 pasos; primero op2 pestana: geometria.transformar (Transformar una cara, arista o vértice suelto.)) |
| `evidencias/gatoRL_2026-10-12/gatoRL.autoguardado.omnicad` | 113 | 61.60 | 2.74 | MOTOR_SIN_SOPORTE (24 pasos; primero op2 eje_escalonado: engranajes._linea) |
| `evidencias/gatoRL_2026-10-12/gatoRL.omnicad` | 113 | 61.77 | 2.69 | MOTOR_SIN_SOPORTE (24 pasos; primero op2 eje_escalonado: engranajes._linea) |
| `evidencias/k/claude_1_soporte/soporte.omnicad` | 4 | 0.06 | 0.04 | MOTOR_SIN_SOPORTE (2 pasos; primero op2 primitiva: geometria.se_tocan) |
| `evidencias/k/claude_2_caja/caja.omnicad` | 6 | 0.07 | 0.15 | MOTOR_SIN_SOPORTE (1 pasos; primero op7 combinar: geometria.se_tocan) |
| `evidencias/k/claude_3_brida/brida.omnicad` | 4 | 0.08 | 0.03 | MOTOR_SIN_SOPORTE (3 pasos; primero op2 chaflan: chaflán sobre un cuerpo con caras curvas) |
| `evidencias/lampara/lampara_onda.omnicad` | 17 | 0.16 | 0.03 | MOTOR_SIN_SOPORTE (3 pasos; primero op2 extrusion: extruir un perfil con arcos, círculos o curvas) |
| `evidencias/mecanismo/mecanismo_biela_manivela.omnicad` | 25 | 0.11 | 0.08 | MOTOR_SIN_SOPORTE (8 pasos; primero op2 primitiva: geometria.se_tocan) |
| `evidencias/minifigura/minifigura.omnicad` | 36 | 0.24 | 0.15 | MOTOR_SIN_SOPORTE (11 pasos; primero op9 empalme: empalme sobre un cuerpo con caras curvas) |
| `evidencias/moka/cafetera_moka.omnicad` | 35 | 0.51 | 0.12 | MOTOR_SIN_SOPORTE (7 pasos; primero op6 solevacion: solidos_crear.solevar) |
| `evidencias/motor/motor.omnicad` | 174 | 7.55 | 0.18 | MOTOR_SIN_SOPORTE (65 pasos; primero op2 revolucion: geometria.revolver) |
| `evidencias/motor_cohete/motor_cohete.omnicad` | 41 | 3.05 | 0.17 | MOTOR_SIN_SOPORTE (18 pasos; primero op2 revolucion: geometria.revolver) |
| `evidencias/motor_impreso/motor_impreso.omnicad` | 292 | 25.83 | 0.75 | MOTOR_SIN_SOPORTE (97 pasos; primero op2 revolucion: geometria.revolver) |
| `evidencias/mueble/mueble.omnicad` | 21 | 0.16 | 0.04 | MOTOR_SIN_SOPORTE (4 pasos; primero op17 primitiva: booleanas entre cuerpos con caras curvas) |
| `evidencias/superficies/superficies_malla.omnicad` | 41 | 4.73 | 0.56 | MOTOR_SIN_SOPORTE (5 pasos; primero op8 sup_solevacion: perfiles.aristas_boceto) |
| `evidencias/tormenta_rl_test_2026-10-11/motor-rl-test.autoguardado.omnicad` | 70 | 39.28 | 0.36 | MOTOR_SIN_SOPORTE (32 pasos; primero op2 revolucion: geometria.revolver) |
| `evidencias/tormenta_rl_test_2026-10-11/motor-rl-test.omnicad` | 72 | 38.59 | 0.12 | MOTOR_SIN_SOPORTE (32 pasos; primero op2 revolucion: geometria.revolver) |
| `evidencias/tortura_2026-10-17/reductor_tortura.autoguardado.omnicad` | 82 | 11.64 | 3.81 | MOTOR_SIN_SOPORTE (23 pasos; primero op2 extrusion: extruir un perfil con arcos, círculos o curvas) |
| `evidencias/tortura_2026-10-17/reductor_tortura.omnicad` | 82 | 11.52 | 3.84 | MOTOR_SIN_SOPORTE (23 pasos; primero op2 extrusion: extruir un perfil con arcos, círculos o curvas) |
| `evidencias/torturaRL_2026-10-11/caso_patron_agujeros.omnicad` | 10 | 1.01 | 0.07 | MOTOR_SIN_SOPORTE (9 pasos; primero op2 agujero: solidos_crear.herramienta_agujero) |
| `evidencias/torturaRL_2026-10-11/motor-rl-tortura.autoguardado.autoguardado.omnicad` | 148 | 269.22 | 0.19 | MOTOR_SIN_SOPORTE (58 pasos; primero op2 revolucion: geometria.revolver) |
| `evidencias/torturaRL_2026-10-11/motor-rl-tortura.autoguardado.omnicad` | 148 | 280.80 | 0.19 | MOTOR_SIN_SOPORTE (58 pasos; primero op2 revolucion: geometria.revolver) |
| `evidencias/torturaRL_2026-10-11/motor-rl-tortura.omnicad` | 148 | 267.00 | 2.46 | MOTOR_SIN_SOPORTE (58 pasos; primero op2 revolucion: geometria.revolver) |

## Las 5 diferencias de tiempo más grandes

| Qué | OCC (s) | OmniKernel (s) | OmniKernel − OCC (s) |
|---|---|---|---|
| operación desfasar_caras | 0.007 | 0.416 | +0.409 |
| operación quitar_caras | 0.015 | 0.386 | +0.371 |
| operación desmoldeo | 0.003 | 0.359 | +0.356 |
| operación perfil_rectangulo | 0.346 | 0.005 | -0.341 |
| operación extruir_simetrica | 0.342 | 0.008 | -0.334 |
