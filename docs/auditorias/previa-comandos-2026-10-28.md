# Vista previa de comandos · 2026-10-28

**La complejidad del cuerpo cambiado pesa mucho más que la cantidad de cuerpos alrededor.** En la placa de
200 agujeros, Vaciado tarda unos 5 s por previa; los patrones, 1,7 s; Empalme y Chaflán, aproximadamente 1 s;
Cortar y Unir, 0,65–0,68 s; Intersecar, 108 ms. Son medianas observadas, no estimaciones. El dibujo habitual
cuesta alrededor de 1–4 ms por cuadro: no explica esos segundos. Se midieron ocho escenarios de seis claves
de comando, cuatro modelos y tres repeticiones: **32 casos y 96 corridas válidas**.

## Alcance y reproducción

Medición de la ventana real en el commit 4031def. No modifica producción ni tests.
Desde `clon/`: `.venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/medir_previa_comandos.py --modelo chico` (repetir con mediano, grande y placa200).

Arrastre rápido de 3 s con QMouseEvent, sin mover el cursor real; tres corridas válidas por caso. Primer cálculo con documento/panel nuevo separado del arrastre. Espera adaptativa y protección aislada originales.
Ventana 1900 × 1000, con la bandera siempre encima. FPS cuenta frameSwapped dentro de los 3 s; una corrida con FPS 0 se descarta. Previas/s usa la duración real del gesto: un cálculo nativo puede sobrepasar los 3 s pedidos y se registra gesto_s.
Los intervalos incluyen hasta 100 ms de presentación posterior al gesto para no esconder un bloqueo al final. paintGL mide CPU/envío de GL, no GPU aislada.

Equipo observado: Windows 11, Python 3.12.10, AMD Radeon(TM) Graphics, OpenGL 4.6 Compatibility Profile.
Preparación y cierre no entran en los tiempos del gesto. El kernel de la tabla significa
`Documento.previsualizar`, incluyendo su coordinación Python; las llamadas `_booleana`, al mallador OCC y
a validadores se cronometran además para distinguirlas. No se usó cProfile ni se alteró el temporizador.

## Catálogo con PREVIA=True

Inventario efectivo de CATALOGO (incluye PREVIA heredado). * = SIN_OP: usa mostrar, no Documento.previsualizar.

- **inspeccionar:** `accesibilidad*`, `angulo_desmoldeo*`, `buscar_similares*`, `cebra*`, `centro_masa*`, `curvatura_peine*`, `interferencia*`, `isocurva*`, `mapa_curvatura*`, `mapa_entorno*`, `medir*`, `radio_minimo*`, `reconocer_funciones*`, `seccion*`
- **crear:** `agujero`, `barrido`, `bobina`, `cuerpo_envolvente`, `labio`, `nervio`, `patron_circular_3d`, `patron_rectangular_3d`, `patron_ruta`, `red`, `relleno_contorno`, `repujado`, `rosca`, `saliente`, `simetria_3d`, `solevacion`, `tuberia`, `volumen_fluido`
- **modificar:** `alinear`, `apoyar`, `chaflan_3d`, `combinar`, `desfase`, `desfase_cara`, `desmoldeo`, `dividir_cara`, `dividir_cuerpo`, `division_silueta`, `empalme_3d`, `escala_3d`, `mover_copiar`, `pulsar_tirar`, `quitar`, `quitar_empalmes`, `reemplazar_cara`, `reticula_volumetrica`, `vaciado`
- **plastico:** `asignar_regla_plastico`, `consejos_diseno*`, `patron_geometrico`, `reglas_plastico*`
- **primitivas:** `caja`, `cilindro`, `esfera`, `toroide`
- **insertar:** `calcomania`, `insertar_dxf`, `insertar_svg`, `lienzo`, `vectorizar_imagen`
- **malla:** `combinar_mallas`, `convertir_malla`, `cortar_plano`, `escalar_malla`, `grupos_caras`, `invertir_normal_malla`, `limpiar_malla`, `malla_teselar`, `reducir_malla`, `remallar`, `reparar_malla`, `separar_malla`, `suavizar_malla`, `vaciado_malla`
- **chapa:** `convertir_chapa`, `desgarro`, `desplegar`, `dobladillo`, `patron_plano`, `pestana`, `pestana_contorno`, `plegar`, `replegar`, `unir_plegando`
- **superficie:** `coser`, `descoser`, `destrimar`, `engrosar`, `extender_sup`, `invertir_normal`, `parche`, `recortar_sup`, `reglada`, `sup_barrido`, `sup_desfase`, `sup_empalme`, `sup_extruir`, `sup_revolucion`, `sup_solevacion`
- **construir:** `eje_arista`, `eje_cilindro`, `eje_dos_planos`, `eje_dos_puntos`, `eje_perpendicular`, `plano_angulo`, `plano_desfase`, `plano_dos_aristas`, `plano_medio`, `plano_perpendicular`, `plano_ruta`, `plano_tangente`, `plano_tres_puntos`, `punto_arista_plano`, `punto_centro`, `punto_dos_aristas`, `punto_ruta`, `punto_tres_planos`, `punto_vertice`, `scu`
- **engranaje:** `eje_escalonado`, `engranaje`
- **solido:** `extruir`, `extruir_cara`, `revolucion`
- **fijacion:** `fijacion`
- **ensamblar:** `grupo_rigido`, `nuevo_componente`, `origen_union`, `union`, `union_construida`, `vinculo_movimiento`
- **derivacion:** `insertar_derivacion`
- **patrones:** `multitransformar`, `patron_puntos`
- **revision:** `reparar_cuerpo`, `revisar_geometria*`
- **malla_seccion:** `seccion_malla`

## Selección

Empalme y Chaflán cambian una arista exterior; Vaciado ahueca el cuerpo cerrado; Patrón rectangular y circular repiten el cuerpo tres veces, sin copias ligeras ni unión. Cortar/Unir/Intersecar son los tres modos booleanos del panel `caja`, variando alto. Así el modelo chico mantiene un único cuerpo de entrada. `combinar` no tiene cotas ni asas: no se midió su interfaz ni se supone equivalente su costo total.

La placa replica el contorno 400 × 400 y los 200 círculos r3 de medir_costos_previa.py, extruidos 20 mm solo para preparar el modelo; no se vuelve a medir Extruir. Mediano: caja objetivo y 19 cajas, 10 redondeadas en sus 12 aristas. Grande: caja objetivo y 69 cajas independientes.

## Tabla comando × modelo

Milisegundos. Previa = p50 / p95 / máximo de las llamadas de las tres corridas reunidas. K/M/T/D = p50 de previsualizar / set_modelo / teselado acumulado por set_modelo / paintGL. M incluye T y aristas: no sumarlos. p95 y máximos de cada etapa y repetición quedan en el JSON.

| Comando | Modelo (pasos/cuerpos/caras) | Reps | Previa p50/p95/máx | K / M / T / D | Previas/s | FPS | Retraso p50/p95 | Cuadros >33/>100 | Hijo primera/arrastre |
|---|---|---|---|---|---|---|---|---|---|
| vaciar | chico (1/1/6) | 3 | 15.4/18.6/19.7 | 9.5 / 4.8 / 4.2 / 1.1 | 19.0–20.3 | 36.3–41.0 | 34.8–43.1 / 64.6–73.2 | 66/0 | 0/0 |
| vaciar | mediano (30/20/320) | 3 | 16.3/21.1/45.7 | 9.7 / 5.2 / 4.5 / 1.9 | 15.0–19.0 | 25.7–35.7 | 35.8–51.4 / 63.9–167.9 | 164/5 | 0/0 |
| vaciar | grande (70/70/420) | 3 | 16.9/20.4/160.1 | 10.0 / 5.4 / 4.5 / 3.5 | 14.3–14.7 | 29.0–30.3 | 52.6–53.7 / 181.2–235.4 | 162/3 | 3/0 |
| vaciar | placa200 (2/1/206) | 3 | 5014.9/5449.5/5497.8 | 3725.3 / 1326.0 / 1152.7 / 1.2 | 0.2–0.2 | 1.0–1.7 | 4830.6–5572.8 / 4830.6–5574.7 | 16/5 | 0/0 |
| empalme | chico (1/1/6) | 3 | 7.6/10.3/21.1 | 3.0 / 3.6 / 3.1 / 1.2 | 29.0–41.9 | 30.7–43.3 | 35.8–36.6 / 39.3–157.7 | 23/4 | 0/0 |
| empalme | mediano (30/20/320) | 3 | 8.1/10.7/37.1 | 3.1 / 3.8 / 3.2 / 1.9 | 27.3–36.7 | 28.3–38.7 | 43.1–45.9 / 45.5–141.8 | 32/5 | 0/0 |
| empalme | grande (70/70/420) | 3 | 8.3/10.6/151.1 | 3.1 / 3.9 / 3.2 / 3.5 | 25.6–27.2 | 30.0–31.7 | 47.9–52.4 / 154.8–186.9 | 67/3 | 3/0 |
| empalme | placa200 (2/1/206) | 3 | 1025.2/1262.8/1299.1 | 142.1 / 877.3 / 773.2 / 1.1 | 0.7–0.8 | 4.0–10.3 | 1102.3–1465.3 / 1221.3–1592.0 | 13/8 | 0/0 |
| chaflan | chico (1/1/6) | 3 | 7.1/9.3/15.6 | 3.0 / 3.2 / 2.7 / 1.2 | 29.2–43.5 | 30.0–45.3 | 23.2–39.0 / 36.5–157.5 | 22/4 | 0/0 |
| chaflan | mediano (30/20/320) | 3 | 7.5/9.8/15.1 | 3.0 / 3.3 / 2.7 / 1.9 | 29.7–38.5 | 32.3–40.0 | 41.4–46.6 / 45.6–79.4 | 19/3 | 0/0 |
| chaflan | grande (70/70/420) | 3 | 7.8/11.6/150.1 | 3.0 / 3.4 / 2.7 / 3.5 | 22.8–28.2 | 29.7–33.3 | 45.2–49.6 / 155.0–206.7 | 65/3 | 3/0 |
| chaflan | placa200 (2/1/206) | 3 | 959.9/1077.5/1085.6 | 150.0 / 808.9 / 720.0 / 1.0 | 0.8–0.8 | 9.3–9.7 | 1112.0–1167.2 / 1217.4–1332.6 | 12/9 | 0/0 |
| cortar | chico (1/1/6) | 3 | 13.4/16.9/44.1 | 7.5 / 5.0 / 4.3 / 1.3 | 15.9–20.9 | 31.0–42.0 | 44.4–45.6 / 50.5–151.5 | 52/4 | 0/0 |
| cortar | mediano (30/20/320) | 3 | 13.8/19.2/46.1 | 7.4 / 5.1 / 4.4 / 2.0 | 14.5–18.6 | 28.7–37.3 | 50.8–54.8 / 54.2–118.5 | 134/6 | 0/0 |
| cortar | grande (70/70/420) | 3 | 13.9/17.3/160.7 | 7.5 / 5.2 / 4.3 / 3.6 | 13.3–14.3 | 29.7–31.3 | 55.3–55.9 / 165.6–241.4 | 160/3 | 3/0 |
| cortar | placa200 (2/1/206) | 3 | 652.1/975.7/1102.1 | 128.8 / 522.2 / 414.8 / 1.3 | 1.0–1.1 | 11.3–17.0 | 811.1–908.8 / 1039.2–1346.5 | 13/10 | 0/0 |
| unir | chico (1/1/6) | 3 | 14.5/18.3/40.1 | 8.6 / 5.0 / 4.3 / 1.3 | 14.6–19.9 | 28.7–41.0 | 41.8–46.5 / 52.5–200.0 | 60/6 | 0/0 |
| unir | mediano (30/20/320) | 3 | 15.2/21.0/37.9 | 8.7 / 5.2 / 4.4 / 2.0 | 14.6–17.9 | 29.3–36.0 | 45.4–56.9 / 57.7–115.0 | 151/3 | 0/0 |
| unir | grande (70/70/420) | 3 | 15.2/18.8/153.8 | 8.7 / 5.1 / 4.3 / 3.6 | 13.3–13.7 | 29.3–30.0 | 56.4–57.6 / 186.5–196.5 | 157/3 | 3/0 |
| unir | placa200 (2/1/206) | 3 | 680.2/1145.2/1148.6 | 172.9 / 505.8 / 413.5 / 1.3 | 0.9–1.1 | 11.3–18.3 | 821.2–908.2 / 931.2–1416.1 | 16/10 | 0/0 |
| intersecar | chico (1/1/6) | 3 | 9.9/12.5/31.4 | 5.8 / 3.0 / 2.5 / 1.3 | 24.9–37.6 | 28.0–38.7 | 33.0–42.8 / 43.7–185.0 | 32/8 | 0/0 |
| intersecar | mediano (30/20/320) | 3 | 10.2/12.7/60.4 | 5.9 / 3.1 / 2.6 / 2.0 | 23.7–32.7 | 26.3–33.7 | 48.3–48.6 / 51.9–178.0 | 49/4 | 0/0 |
| intersecar | grande (70/70/420) | 3 | 10.4/12.6/153.1 | 5.9 / 3.2 / 2.5 / 3.6 | 19.6–23.2 | 27.0–28.7 | 37.9–52.6 / 196.2–212.5 | 157/3 | 3/0 |
| intersecar | placa200 (2/1/206) | 3 | 107.7/174.8/219.9 | 58.1 / 49.6 / 2.6 / 1.3 | 3.0–4.3 | 23.7–29.7 | 196.1–255.6 / 253.0–468.5 | 44/34 | 0/0 |
| patron_rectangular | chico (1/1/6) | 3 | 8.3/10.7/12.5 | 0.9 / 6.1 / 5.3 / 1.6 | 33.0–37.5 | 34.3–38.0 | 42.3–46.8 / 51.3–76.3 | 13/1 | 0/0 |
| patron_rectangular | mediano (30/20/320) | 3 | 9.0/11.5/18.7 | 0.9 / 6.3 / 5.4 / 2.3 | 21.6–32.9 | 25.0–33.3 | 50.6–53.8 / 52.8–166.1 | 56/3 | 0/0 |
| patron_rectangular | grande (70/70/420) | 3 | 9.5/11.9/161.0 | 1.0 / 6.2 / 5.3 / 3.9 | 22.5–24.2 | 27.0–28.0 | 56.1–58.6 / 207.2–224.2 | 150/3 | 3/0 |
| patron_rectangular | placa200 (2/1/206) | 3 | 1719.7/1784.0/1789.2 | 16.3 / 1702.4 / 1566.2 / 1.5 | 0.5–0.5 | 8.0–8.7 | 1835.6–1865.8 / 1943.3–1978.4 | 6/6 | 0/0 |
| patron_circular | chico (1/1/6) | 3 | 8.3/10.3/16.8 | 0.9 / 6.1 / 5.3 / 1.4 | 27.2–39.8 | 28.3–40.3 | 40.9–44.4 / 43.4–171.5 | 12/5 | 0/0 |
| patron_circular | mediano (30/20/320) | 3 | 8.9/11.6/17.2 | 0.9 / 6.3 / 5.4 / 2.2 | 25.5–34.2 | 28.3–35.0 | 48.1–54.4 / 51.0–151.3 | 33/3 | 0/0 |
| patron_circular | grande (70/70/420) | 3 | 9.5/12.3/153.7 | 1.0 / 6.3 / 5.2 / 3.7 | 21.9–25.2 | 28.0–29.0 | 54.0–54.6 / 197.6–207.7 | 88/3 | 3/0 |
| patron_circular | placa200 (2/1/206) | 3 | 1746.0/1801.0/1805.0 | 18.1 / 1727.0 / 1581.6 / 1.3 | 0.5–0.5 | 8.0–8.7 | 1843.1–1924.4 / 1945.0–2047.4 | 8/6 | 0/0 |

## Reparto en la placa de 200 agujeros

Medias por cálculo durante el gesto, en ms (suma de tiempos / cantidad de previas). Los porcentajes tienen como denominador el tiempo total de _calcular_previa. Dibujo va aparte, por cuadro: se presenta más de un cuadro por previa y no se suma dos veces.

La columna «Booleana OCC» cronometra `geo._booleana` completa (`geometria.py:354-397`), incluida
la unificación de caras y limpieza de cables. No separa `op.Build()` ni mide C++ puro.

| Comando | Kernel | Teselado | Aristas | Resto previa | paintGL p50/p95/máx | OCC mallador / normales | Booleana OCC / revisión booleana / validar modificar |
|---|---|---|---|---|---|---|---|
| vaciar | 3648.7 (71.7 %) | 1263.6 (24.8 %) | 106.8 (2.1 %) | 68.5 (1.3 %) | 1.2/1.8/2.0 | 441.7 / 287.0 | 403.6 / 52.0 / 78.9 |
| empalme | 149.5 (14.0 %) | 806.7 (75.6 %) | 49.1 (4.6 %) | 62.4 (5.8 %) | 1.1/1.9/2.3 | 384.4 / 144.2 | — / — / 70.5 |
| chaflan | 148.8 (15.1 %) | 747.2 (75.7 %) | 39.1 (4.0 %) | 51.6 (5.2 %) | 1.0/1.8/1.9 | 375.8 / 123.2 | — / — / 76.6 |
| cortar | 137.0 (19.2 %) | 473.8 (66.3 %) | 43.2 (6.0 %) | 60.7 (8.5 %) | 1.3/2.1/2.6 | 36.5 / 134.1 | 71.6 / 29.5 / — |
| unir | 202.6 (26.3 %) | 464.5 (60.3 %) | 44.9 (5.8 %) | 58.5 (7.6 %) | 1.3/2.1/3.7 | 39.0 / 139.9 | 83.4 / 30.2 / — |
| intersecar | 64.2 (53.3 %) | 2.9 (2.4 %) | 0.3 (0.2 %) | 53.0 (44.0 %) | 1.3/1.9/2.6 | 2.4 / 0.9 | 35.4 / 1.0 / — |
| patron_rectangular | 16.6 (1.0 %) | 1570.0 (90.7 %) | 80.8 (4.7 %) | 63.4 (3.7 %) | 1.5/1.9/3.1 | 834.4 / 246.8 | — / — / — |
| patron_circular | 18.1 (1.0 %) | 1590.5 (90.7 %) | 81.6 (4.7 %) | 62.6 (3.6 %) | 1.3/1.5/3.2 | 839.4 / 245.2 | — / — / — |

## Primera previa: costo de abrir el cálculo (fuera del arrastre)

Rangos de las tres corridas; documentos nuevos. previsualizar incluye el proceso y transporte si hubo hijo. Las etapas internas del hijo no heredan estos cronómetros.

| Comando | Modelo | _calcular_previa | previsualizar | set_modelo | Hijos | Teselados/previas en arrastre |
|---|---|---|---|---|---|---|
| vaciar | chico | 28.8–32.6 | 22.9–26.5 | 4.5–5.2 | 0 | 178/178 |
| vaciar | mediano | 31.9–38.6 | 25.7–32.1 | 5.0–5.6 | 0 | 157/157 |
| vaciar | grande | 1547.1–1807.5 | 1353.3–1613.6 | 192.3–195.1 | 3 | 337/130 |
| vaciar | placa200 | 4822.7–5693.6 | 3527.8–3839.2 | 1293.9–1853.1 | 0 | 3/3 |
| empalme | chico | 20.9–24.1 | 16.5–19.5 | 3.4–3.6 | 0 | 333/333 |
| empalme | mediano | 24.0–26.5 | 19.2–21.7 | 3.5–4.4 | 0 | 293/293 |
| empalme | grande | 1588.0–1596.4 | 1394.0–1404.1 | 188.9–197.2 | 3 | 447/240 |
| empalme | placa200 | 963.1–1029.0 | 142.4–156.4 | 812.9–874.9 | 0 | 8/8 |
| chaflan | chico | 20.5–22.7 | 16.6–18.4 | 3.1–3.4 | 0 | 349/349 |
| chaflan | mediano | 22.8–31.1 | 18.3–24.5 | 3.0–4.6 | 0 | 309/309 |
| chaflan | grande | 1534.1–1547.1 | 1341.8–1351.1 | 191.1–195.0 | 3 | 443/236 |
| chaflan | placa200 | 966.7–977.1 | 160.7–178.5 | 797.7–805.2 | 0 | 9/9 |
| cortar | chico | 27.6–100.7 | 21.7–76.8 | 4.7–7.1 | 0 | 172/172 |
| cortar | mediano | 30.6–69.5 | 24.2–62.0 | 4.9–5.5 | 0 | 152/152 |
| cortar | grande | 1518.5–1775.2 | 1325.0–1581.1 | 192.1–196.0 | 3 | 332/125 |
| cortar | placa200 | 614.0–694.4 | 129.6–178.2 | 483.3–515.1 | 0 | 10/10 |
| unir | chico | 29.3–140.5 | 22.2–115.5 | 6.1–23.7 | 0 | 163/163 |
| unir | mediano | 33.0–52.1 | 26.2–43.9 | 4.7–6.6 | 0 | 146/146 |
| unir | grande | 1529.1–1554.9 | 1335.6–1362.4 | 191.0–192.8 | 3 | 329/122 |
| unir | placa200 | 677.0–819.8 | 195.5–251.3 | 480.4–567.2 | 0 | 10/10 |
| intersecar | chico | 23.9–28.2 | 19.8–23.9 | 3.2–3.2 | 0 | 264/264 |
| intersecar | mediano | 26.4–28.9 | 21.9–24.7 | 3.0–3.3 | 0 | 252/252 |
| intersecar | grande | 1523.2–1552.7 | 1327.6–1359.6 | 191.6–194.2 | 3 | 406/199 |
| intersecar | placa200 | 119.4–123.7 | 69.0–74.4 | 46.9–49.3 | 0 | 34/34 |
| patron_rectangular | chico | 24.0–132.1 | 16.0–122.5 | 6.2–7.4 | 0 | 650/325 |
| patron_rectangular | mediano | 25.8–27.4 | 18.2–19.5 | 6.0–6.4 | 0 | 520/260 |
| patron_rectangular | grande | 1525.7–1555.1 | 1331.2–1351.8 | 192.3–200.9 | 3 | 634/212 |
| patron_rectangular | placa200 | 2003.3–2374.7 | 39.2–44.6 | 1962.1–2328.1 | 0 | 12/6 |
| patron_circular | chico | 22.8–24.9 | 15.1–15.8 | 5.8–6.9 | 0 | 638/319 |
| patron_circular | mediano | 25.8–138.4 | 17.1–128.8 | 6.3–7.6 | 0 | 560/280 |
| patron_circular | grande | 1526.9–1560.5 | 1329.5–1357.8 | 195.1–200.2 | 3 | 640/215 |
| patron_circular | placa200 | 1822.2–2315.5 | 36.8–38.0 | 1783.5–2276.6 | 0 | 12/6 |

## Qué entra en 33 ms

El criterio principal es **p95 de `_calcular_previa` ≤ 33 ms**, no FPS ni una promesa sobre todos los cuadros.

- **Chico, mediano y grande:** los ocho escenarios cumplen ese p95 (en toda esa matriz, 9,3–21,1 ms).
  El objetivo modificado sigue siendo una caja sencilla; las 320/420 caras son el total de la escena.
- **Placa200:** ninguno cumple. El p95 va de 174,8 ms en Intersecar a 5449,5 ms en Vaciado.
- **Máximo estricto ≤ 33 ms:** en chico lo cumplen Empalme, Chaflán, Intersecar, Vaciado y ambos patrones;
  Cortar y Unir tuvieron picos de 44,1 y 40,1 ms. En mediano solo lo cumplen Chaflán y ambos patrones.
  En grande ninguno: todos conservan un pico de 147–161 ms en la transición desde la primera previa.
- **Cuadros presentados:** ningún caso garantiza todos los intervalos ≤ 33 ms, incluso con previa barata.
  Las columnas de cuadros lentos son sumas de las tres repeticiones, no percentiles de tiempo de cálculo.
  Las pausas de presentación no quedan explicadas solo por el kernel o por `paintGL`.

## Causas confirmadas e hipótesis

Los porcentajes de abajo son del tiempo acumulado de previa, no cocientes entre medianas. La tabla de
reparto permite comprobarlos sin sumar etapas anidadas.

| Escenario lento | Confirmado por las corridas | Qué todavía es hipótesis | Seguimiento |
|---|---|---|---|
| Empalme, placa200 | El teselado toma 75,6 %: media 806,7 ms por previa, frente a 149,5 ms de previsualizar y dibujo p50 1,1 ms. Mallador OCC 384,4 ms y normales 144,2 ms están dentro de ese teselado. | El resto del teselado no se separó entre copia a numpy y otras tareas; no se extrapola el reparto de Extruir. | P-46, relacionado con P-34 |
| Chaflán, placa200 | Teselado 75,7 %: 747,2 ms frente a 148,8 ms de previsualizar; dibujo p50 1,0 ms. Una única arista exterior fuerza la actualización de la malla del cuerpo. | No se midió una caché por cara ni un camino alternativo que pruebe cuánto ahorraría. | P-47, P-34 |
| Cortar, placa200 | Teselado 66,3 %: 473,8 ms; previsualizar 137,0 ms. La llamada booleana OCC promedia 71,6 ms y su revisión 29,5 ms, dentro de previsualizar. | No se midió cuánto del resto de teselado es copia de caras intactas. | P-48, P-34 |
| Unir, placa200 | Teselado 60,3 %: 464,5 ms; previsualizar 202,6 ms. Booleana OCC 83,4 ms y revisión 30,2 ms; no corresponde atribuirle toda la demora a la operación C++. | El resto de previsualizar incluye controles y coordinación; no se separó cada integral de volumen. | P-49, P-34/P-35 |
| Intersecar, placa200 | Previsualizar 64,2 ms (53,3 %), teselado 2,9 ms (2,4 %) y resto de previa 53,0 ms (44,0 %). set_modelo p50 49,6 ms, aunque sus mallas nuevas son baratas. | Parte importante podría estar en el armado de segmentos de boceto de set_modelo; hace falta cronometrar ese tramo. No se lo declara causa confirmada. | P-50 |
| Vaciado cerrado, placa200 | Previsualizar concentra 71,7 %: 3648,7 ms; teselado 1263,6 ms (24,8 %). Dentro del cálculo se observaron 403,6 ms de booleana OCC, 52,0 ms de revisión booleana y 78,9 ms de validación de modificación. | El desfase del cuerpo con 200 perforaciones es candidato para buena parte del tiempo restante; `_desfase_cuerpo` no se envolvió por separado y no se afirma su costo. | P-51 |
| Patrón rectangular, placa200 | Teselado 90,7 %: 1570,0 ms por previa; previsualizar 16,6 ms. Cada repetición hizo dos previas y cuatro teselados: se remallan las dos copias nuevas, mientras el original se conserva. | No se comparó contra copias ligeras, ni se midió una optimización por matrices; no se anuncia una mejora sin correrla. | P-52, P-34 |
| Patrón circular, placa200 | Teselado 90,7 %: 1590,5 ms; previsualizar 18,1 ms. También son dos cuerpos remallados por previa, con dibujo p50 1,3 ms. | Misma limitación de copias ligeras: el banco usa copias normales. | P-53, P-34 |

**Pico compartido de los ocho comandos con 70 pasos:** cada una de las 24 primeras previas llamó al hijo
una vez (1,52–1,81 s de `_calcular_previa`); los 24 arrastres llamaron al hijo **cero veces**. Para los seis
escenarios que cambian un cuerpo, cada repetición tuvo exactamente 69 teselados más que previas; para los
patrones, 70 más que dos veces las previas. Son los cuerpos sin cambio que no reutilizan la caché al pasar de
las formas devueltas por el hijo a las originales del proceso principal. Se confirma el mecanismo ya
registrado como **P-43**, con picos de previa de 147–161 ms: no se carga como ocho causas independientes.

Evidencia de código abierta en esta sesión:

- `clon/omnicad/ui/comando.py:703-753`: espera adaptativa y primera previa aislada seguida de `en_vivo=True`.
- `clon/omnicad/timeline/documento.py:823-875`: la primera previa puede adoptar el resultado del hijo;
  las siguientes copian el estado original y ejecutan el candidato en el proceso principal.
- `clon/omnicad/ui/visor3d.py:541-589`: caché por `id(c.forma)`, un teselado y aristas por cuerpo nuevo,
  y reconstrucción de segmentos de los bocetos en cada set_modelo.
- `clon/omnicad/nucleo/geometria.py::teselar_por_cara` y
  `clon/omnicad/nucleo/render_cpu.py::_mallas_por_cara`: mallado, copia a arrays y normales por nodo.
- `clon/omnicad/nucleo/geometria.py:586-638`: la booleana tiene controles y reintentos además de OCC.
- `clon/omnicad/nucleo/solidos_modificar.py:1039-1076`: Vaciado sin caras usa desfase de cuerpo,
  corte booleano y validación; no se confunde con abrir una tapa.

**Lectura recomendada para priorizar:** en seis escenarios pesa primero evitar trabajo de malla repetido;
Vaciado necesita separar el cálculo de desfase y sus controles; Intersecar necesita separar la escena y
el resto del cálculo. Esta tarea deja las mediciones y los pendientes, sin aplicar esas optimizaciones.

## Calidad de la medición y revisión del script

La primera tanda de 97 corridas se descartó completa: el envoltorio de `paintGL` se instalaba después de
crear el widget y Qt no lo llamaba. Incluía una corrida con FPS 0, descartada y repetida. También se detectó
que medir solo la diferencia temporal entre eventos de sólido y asa daba cero cuando el kernel bloqueaba
la llegada de ambos. Las tablas usan únicamente la segunda tanda de 96 corridas, todas con FPS > 0,
cronómetro de `paintGL` activo y todas las previas terminadas sin error. El script conserva el conteo y
motivo de descarte en el JSON. Durante la puesta a punto se corrigió además la selección del asa del arnés:
`Posicion` no tiene `clave`, así que se filtra el tipo antes de acceder al atributo; no se cambió OmniCAD.

`/ponytail-review` aplicado al script nuevo: revisión del recorrido conectado (panel → documento → visor),
límites de las métricas, restauración de envoltorios y cierre de ventanas, carga real de 96 corridas y
autocomprobación de percentiles/generaciones. No se agregaron dependencias. El único punto de entrada
público es `main()`: ejecuta los modelos/casos elegidos o consulta sus datos guardados (`--resumir`, de solo lectura).
Los archivos temporales de preferencias y chats viven en un directorio propio y se eliminan al salir.
Veredicto de la revisión: apto para este banco, sin hallazgos bloqueantes pendientes. Ruff del script:
`All checks passed!`; autocomprobación: percentiles, generaciones y restauración de cronómetros OK;
`tests/test_seguimiento.py`: `342 passed in 0.48s` (con turno). La consulta `--resumir` devolvió 32 casos y
96 corridas, y se comprobó con hash que conserva el informe byte a byte.

## Datos por corrida

Incluyen descartes, tiempos de la primera previa, muestras por etapa, latencia entrada→cuadro y desfase en unidades del campo. El retraso es cuadro presentado menos instante del evento que generó el sólido. edad_eventos_ms informa por separado la distancia temporal entre los eventos de asa y sólido; no se usa como latencia porque da cero cuando el kernel bloquea los dos. Los porcentajes de etapas anidadas no se suman.

Datos: `evidencias/previa_comandos_2026-10-28.json` (fuera de git). Para regenerar las tablas desde `clon/`: `.venv/Scripts/python.exe ../scripts/medir_previa_comandos.py --resumir --fecha 2026-10-28`.

## Después del paso 2 (caché por cara y malla del arrastre con ángulo 1,0)

Mismo equipo y mismo script, placa200, medianas de 3 corridas, ms. «Antes» es la tabla de arriba. Mientras se arrastra se
dibuja una malla más gruesa (deflexión × 4, ángulo 1,0 rad: ≈ 13 lados por agujero de r = 3; la fina tiene 42) y 120 ms
después de soltar vuelve la fina. El sólido que se acepta sale del kernel igual que antes.

| Comando | Teselado antes → ahora | Previa antes → ahora |
|---|---|---|
| Empalme | 773 → 224 (−71 %) | 1025 → 430 (−58 %) |
| Chaflán | 720 → 245 (−66 %) | 960 → 504 (−48 %) |
| Cortar | 415 → 229 (−45 %) | 652 → 421 (−35 %) |
| Unir | 414 → 226 (−45 %) | 680 → 468 (−31 %) |
| Patrón rectangular | 1566 → 448 (−71 %) | 1720 → 592 (−66 %) |
| Patrón circular | 1582 → 449 (−72 %) | 1746 → 593 (−66 %) |

Siguen lentos (> 33 ms) sobre la placa de 200 agujeros. Chico y mediano: previa p95 ≤ 20 ms. Grande: p95 ≤ 18 ms con picos de
81–206 ms. La caché por cara acierta con la misma forma (734 → 38 ms) pero no con el resultado de una booleana: P-34 y P-54.

## Límites: qué no se pudo medir

- **Ventana temporal:** se pidieron 3 s por gesto. Un cálculo nativo no se puede interrumpir a los 3 s:
  Vaciado/placa200 terminó en 5,020 / 5,782 / 5,339 s, con una sola previa por corrida; su p95 conjunto
  interpola únicamente tres cálculos y no estima una cola estadística robusta. Los patrones de placa
  hicieron dos previas por corrida. `gesto_s` registra todos los excesos y previas/s divide por el tiempo real.
- **Retraso:** se observa desde el evento simulado hasta la presentación y también la edad del sólido en
  cada cuadro. No es la latencia de un mouse físico. Incluye la cola del cuadro posterior al gesto; cuando
  hay bloqueo se conserva el cuadro que finalmente muestra el resultado. No se incluyen en ese percentil
  los cuadros anteriores a la primera actualización: sus pausas siguen en FPS e intervalos.
- **Cuadros lentos:** intervalos de frameSwapped durante el gesto y hasta 100 ms después de soltar, más
  el intervalo parcial desde el inicio hasta el primer cuadro. No equivalen a duración de paintGL.
  Los FPS usan solo los 3 s nominales. No se midieron oclusión parcial, carga ajena ni planificador de Windows;
  los picos de presentación de casos chicos no quedan atribuidos a una causa confirmada.
- **Dibujo:** paintGL mide CPU y envío de órdenes; faltan GPU aislada y espera del compositor/pantalla.
  Los cronómetros agregan algo de trabajo Python: su sobrecarga no se midió contra una corrida sin instrumentar.
- **Geometría:** una arista exterior en Empalme/Chaflán, Vaciado cerrado con espesor interior, tres posiciones
  por patrón y una herramienta booleana local. No cubre todos los radios, grupos de aristas, esquinas,
  variantes de Vaciado ni patrones de operaciones/caras o con unión. El objetivo chico/mediano/grande tiene
  seis caras; el grande tiene 70 pasos sencillos, no un historial industrial de 70 operaciones pesadas.
- **Cobertura:** Combinar no tiene asa/cota; se midieron las booleanas del panel caja. El catálogo completo
  está inventariado, pero el resto de los comandos parecidos no está medido. Extruir no se volvió a medir.
- **Causas internas:** quedan sin separar el desfase de Vaciado, el armado de escena de Intersecar, cada
  integral de volumen, parte de la copia de mallas y el trabajo interno/transferencia del hijo.
- **Verificación:** se exige ruff del script, la autocomprobación y `tests/test_seguimiento.py`;
  no se corrió la suite completa ni la prueba de humo general. La app y sus tests quedaron sin cambios.
