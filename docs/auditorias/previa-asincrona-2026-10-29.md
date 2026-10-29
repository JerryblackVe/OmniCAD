# Previa en proceso aparte para todos los comandos pesados (2026-10-29)

Cierra P-34, P-45, P-50, P-51, P-54 y P-55. Medido con `scripts/medir_previa_comandos.py` (datos crudos en
`evidencias/previa_comandos_2026-10-29.json`, fuera de git), commit `4769b54` + cambios sin commitear de esta fase.
Mismo equipo de siempre: 13 GB de RAM, gráficos integrados, otros agentes usando la PC (ver «Ruido»).

## Qué cambió

- Las previas de **Empalme, Chaflán, Cortar/Unir/Intersecar (primitiva con objetivo), Patrón y Vaciado** se calculan en
  un proceso aparte cuando algún cuerpo que nombran tiene **64 caras o más** (`comando.TIPOS_PESADOS`, `CARAS_PESADAS`).
  Con cuerpos chicos siguen en el proceso, como antes. Un solo cálculo en vuelo; se muestra el último pedido.
- El hijo devuelve también los cuerpos **nuevos** (copias de un patrón): `previa_visual` / `leer_previa_visual`.
- Lo que se **acepta** sale siempre del kernel en el padre: la malla del hijo solo se dibuja.
- Asas: la flecha de Empalme y Chaflán nace de la arista elegida y se reutiliza mientras solo cambia el valor
  (`GestorManipuladores.actualizar`); disco y cono se arman con numpy; las cajas de valor ya no vuelven a pulirse
  (`setStyleSheet`) en cada movimiento.

## Criterios (placa de 200 agujeros, 206 caras, gesto de 8 s, 3 corridas válidas por comando)

| Comando | Previa en el hilo de la ventana, p50 (ms): antes → ahora | Intervalo entre cuadros p99 (ms) | Cuadro máximo (ms) | Asas p95 por cambio de valor (ms) |
|---|---|---|---|---|
| Empalme | 933–1247 → 0,07–0,09 | 40–48 | 50–58 | 1,2 (antes 15–20) |
| Chaflán | 955–1018 → 0,06–0,07 | 35–41 | 46–69 | 1,2 (antes 16–19) |
| Cortar | 606–660 → 0,10–0,13 | 28–45 | 45–58 | 3,0–3,2 |
| Unir | 659–735 → 0,10–0,13 | 26–31 | 36–68 | 3,1–3,2 |
| Intersecar | 105–122 → 0,10 | 26–27 | 44–55 | 3,0–3,1 |
| Vaciar | 4 751–5 498 → 0,04–0,05 | 24–39 | 45–62 | 1,1–1,2 |
| Patrón rectangular | 1 714–1 743 → 0,08–0,11 | 37–47 | 46–65 | 3,9–4,1 |
| Patrón circular | 1 715–1 797 → 0,08 | 28–30 | 59–85 | 4,5 |

Meta: ningún cuadro > 150 ms (máximo medido 85), p99 de intervalos ≤ 50 ms (máximo 48), asas p95 ≤ 5 ms (máximo 4,5).
Antes cada previa bloqueaba la ventana lo que dice la primera columna (el cuadro máximo era ese tiempo).

## Latencia hasta el resultado exacto (el costo de la solución)

Tiempo desde que se pide la primera previa hasta que se ve el sólido calculado, mediana de cada corrida:

| Comando | Antes (en el proceso) | Ahora (proceso aparte) |
|---|---|---|
| Intersecar | 0,1 s | 1,5–1,7 s |
| Empalme | 1,0 s | 2,5–3,1 s |
| Chaflán | 1,0 s | 2,6–4,2 s |
| Cortar | 0,6–0,7 s | 2,4–7,7 s |
| Unir | 0,7–0,8 s | 2,4–3,5 s |
| Patrón rectangular | 2,0–2,4 s | 3,2–10,3 s |
| Patrón circular | 1,8–2,3 s | 3,3–7,5 s |
| Vaciar | 4,8–5,7 s | 7,4–10,5 s |

Durante un arrastre el sólido que se ve va 3–8 s detrás del asa (el cálculo en vuelo termina y se pide el último
valor). Se acumula en P-56: cada previa arranca un Python nuevo (~1,5 s de arranque + reconstruir la receta).
La dispersión grande (Cortar 2,4–7,7 s) es carga ajena en la PC, no del programa.

## Cuerpos chicos: sin cambios

Chico (6 caras), mediano (20 cuerpos × 16) y grande (70 cuerpos × 6): ningún comando usa el hijo
(`hijo_arrastre` = 0 en las tres) y la previa p95 queda en 10–28 ms (Chaflán/Empalme/Patrón/Intersecar 10–17 ms,
Cortar/Unir 18–24, Vaciar 22–29 con el espesor 2 ± 1 mm que ahora usa el banco). Los p95 de 50–90 ms que aparecieron
en una primera pasada de mediano/grande eran carga ajena: repetidos aparte, todos quedaron en 12–28 ms.

## P-55: el «piso» de 33–110 ms del Vaciado era el banco, no el programa

El gesto del banco movía el espesor ± 0,12 mm: menos de un píxel en la placa de 400 mm. El texto del valor se
redondea al píxel, así que la mayoría de los movimientos no cambiaba nada, no había nada que dibujar y no se
presentaba cuadro. Pruebas (placa200, 5 s): `paintGL` 1,4 ms (3,5 ms con `glFinish`: no es la GPU); el hilo nunca
se bloqueó más de 30 ms; con amplitud de 1 mm (cada evento cambia el valor) el mismo gesto da p99 25,5 ms y
máximo 25,8 ms. El banco usa ahora espesor 2 mm ± 1 mm.

## Ruido y validez de las corridas

- Una corrida es **válida** si presentó al menos la mitad de los cuadros que valores cambiaron. Las que no
  (ventana tapada por otra: Windows no entrega `frameSwapped`) se descartan y se cuentan en «Reps válidas/intentos».
  En esta medición todas fueron válidas al primer intento.
- Hay otros agentes corriendo pruebas en la misma PC: los extremos (Cortar 7,7 s, Patrón 10,3 s) son de ahí.

## Pruebas

`tests/test_previa_aislada_comandos.py` (decisión de proceso aparte para los 8 comandos, cuerpos nuevos, patrón real
con hijo y aceptar exacto, asa reutilizada, dibujos vectorizados contra la versión de lazo) y
`tests/test_previa_vaciado_aislada.py`.
