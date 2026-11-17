# Plan de fluidez de OmniCAD

Fecha: 2026-11-13. Pedido de Gerardo: «tomá como prioridad mejorar el rendimiento, debe ir todo fluido».
Armado en el chat de la PC (solo plan; ejecuta la VPS). Base: `vps/main` 71d6045b. Estado de cada paquete: filas FL-* de
[mejoras.md](seguimiento/mejoras.md) (F6 es P-78; F7 es RS-X4; F9 › huérfanos es B-396). Registro de uso de origen:
`evidencias/reportes_pc/2026-11-13_plan_fluidez/`.

**Objetivo:** que la ventana nunca se congele y que cada cambio se vea al instante.

## 1. Lo medido

### 1.1 Congelamientos reales de Gerardo (registro de uso de su PC)

22 sesiones del 10 al 13 de noviembre, evento `bloqueo_ui` (más de 250 ms sin responder):
**541 congelamientos, 2002 s en total (33 minutos mirando una ventana trabada).**

| Comando | Veces | Total | El peor |
|---|---|---|---|
| abrir | 17 | 658 s | 554,6 s ⚠ a verificar |
| preferencias | 120 | 565 s | 61,1 s ⚠ a verificar |
| asistente | 83 | 184 s | 11,2 s |
| desfase | 3 | 171 s | 116,4 s |
| rosca | 66 | 97 s | 25,3 s |
| sección | 6 | 62 s | 14,1 s |
| extruir | 48 | 48 s | 3,5 s |
| (sin nombre) | 18 | 36 s | 5,7 s |
| bobina | 13 | 26 s | 4,0 s |
| barrido | 27 | 26 s | 5,9 s |
| combinar | 12 | 21 s | 5,6 s |
| Eliminar (paso) | 11 | 15 s | 6,7 s |
| solevación | 34 | 15 s | 1,1 s |
| sk_terminar | 13 | 11 s | 4,7 s |
| sk_rectangulo | 6 | 10 s | 2,6 s |
| panel_datos | 5 | 10 s | 3,8 s |
| chaflán 3D | 2 | 8,5 s | 5,1 s |
| empalme 3D | 1 | 5,2 s | 5,2 s |

⚠ «abrir» 554 s y parte de «preferencias» pueden ser falsos: la PC suspendida o un diálogo de Windows abierto.
El paquete F0 lo comprueba antes de usar esos dos números.

Cómo repetirlo: los `sesion_*.jsonl` de `%LOCALAPPDATA%/OmniCAD/registro/`, sumando `duracion_ms` de `bloqueo_ui`
por `comando` (o `accion`). El evento sale de `omnicad/ui/registro_uso.py:239-241`.

### 1.2 Fusion contra OmniCAD (misma pieza, cilindro Ø40 × 30, rosca M40x3 modelada)

| Acción | Fusion | OmniCAD por API | OmniCAD en la ventana |
|---|---|---|---|
| Crear la rosca | 0,04 s | 0,6 s | 2 a 6 s |
| Cambiar el tamaño | 0,04 s | 0,4 s | 2 a 6 s |
| Cambiar largo o desfase | 0,03 s | 0,2 a 0,3 s | 2 a 6 s |

El cálculo es unas 10 veces más lento. La ventana, entre 50 y 150 veces. **El grueso de la espera no es el
kernel: es cómo se lo llama.**

### 1.3 Causa confirmada en el código (caso «EMILIA», B-403)

- `omnicad/ui/comando.py:1843` `_previa_pesada`: manda la previa al proceso aparte solo si es rosca modelada, o si
  el tipo está en `TIPOS_PESADOS` (línea 42: vaciado, empalme, chaflán, primitiva, patrón, multitransformar,
  desfase de cara, engrosar, sup_desfase) **y** un cuerpo nombrado tiene 64 caras o más.
- Extrusión, barrido, bobina, solevación, combinar y sección **no están en la lista**. Su previa corre en la ventana:
  `comando.py:1729` (`self.ctx.doc.previsualizar(...)` dentro de `_calcular_previa_ahora`).
- La previa barata del prisma (`_previsualizar_prisma`, línea 1772) sale solo mientras se arrastra el asa
  (línea 1789). Al teclear un valor o usar las flechas, va al kernel exacto en la ventana.
- Medido en vivo: proceso principal 3 s de CPU en 3 s y «No responde»; el trabajador aparte, quieto (6 MB, 0 CPU).

### 1.4 Lo que ya se sabía (docs del repo)

- OCP retiene el GIL: un hilo de Python no libera la ventana (`docs/plan_cpp.md` sección 2). Solo sirve un proceso.
- El trabajador persistente ya existe (RS-X1, `omnicad/nucleo/aislado.py`, `omnicad/timeline/calculo_aislado.py`).
- P-78: la rosca crece con el documento (M20 sola 1,1 s; después de tres M8, 8,2 s). Ya no se reproduce (2026-11-13, por API: M20×60 sola 1,67 s y después de tres M8 1,45 s; M40x3 igual con 0 y 20 pasos antes).
- RS-X4: 72 pasos «combinar» son el 66,7 % del recálculo de `motor_impreso` (16,2 s). Medido el 2026-11-13: el kernel es solo el 10 % de combinar; el resto era la verificación (`_parte_afuera` y `se_tocan`). OBB y modo paralelo no ganan y Glue da volúmenes equivocados con piezas que se cruzan.
- RS-X2, RS-X6, CPP-P20, CPP-C3, CPP-C4, CPP-F1: abiertos o parciales.

## 2. Metas (se miden con el mismo `bloqueo_ui` y con el banco de F0)

| Meta | Hoy | Objetivo |
|---|---|---|
| M1. Congelamientos de más de 250 ms en comandos de prioridad 1 | 541 en 4 días | 0. Tope duro: nada pasa de 1 s |
| M2. Tiempo hasta ver la previa al teclear o usar las flechas | 2 a 6 s | Menos de 0,3 s (la barata, menos de 50 ms) |
| M3. Arrastrar un asa o un punto de boceto | — | 30 cuadros por segundo o más |
| M4. Aceptar en una pieza típica | segundos, ventana trabada | Menos de 1 s; si tarda más, barra y Cancelar con la ventana viva |
| M5. Rosca modelada M20 × 60 por API | 8,4 s | Menos de 0,5 s |
| M6. Abrir un proyecto | 2,7 s (`motor_cohete`) | Menos de 1,5 s y sin trabar la ventana |

## 3. Principios, en este orden

1. **Nada de geometría en el hilo de la ventana.**
2. **Mostrar algo barato ya; lo exacto llega después y lo reemplaza.**
3. **Calcular solo lo que cambió.**
4. **Recién entonces acelerar el núcleo** (opciones de OpenCascade, Rust, C++).

Los tres primeros no dependen de lo rápido que sea OpenCascade. Son los que más se sienten.

## 4. Paquetes

### F0. Banco de fluidez y vigilante
- **Qué:** `scripts/bench_fluidez.py`, con escenarios como usuario (eventos simulados) que devuelven el bloqueo máximo
  del hilo de la ventana, el tiempo hasta la primera previa y el tiempo de Aceptar:
  a) extruir texto de 8 perfiles con Unir en un documento de 11 cuerpos, tecleando 0,5 → 1 → 2;
  b) rosca M20 × 60 modelada, cambiando tamaño y largo con las flechas;
  c) empalme de 2 mm en un cuerpo de 200 caras; d) desfase de cara; e) barrido, bobina y solevación;
  f) combinar; g) eliminar un paso; h) abrir `motor_impreso`; i) preferencias, mover un control;
  j) arrastrar un punto de un boceto de 200 entidades; k) órbita con 300 mil triángulos.
  `tests/test_fluidez.py` falla si un escenario pasa su presupuesto (arranca en el valor de hoy y baja con cada paquete).
  En `scripts/prueba_ui/`, toda pieza falla si hay un `bloqueo_ui` de más de 1 s. Bajar el umbral del evento a 100 ms.
  Comprobar si «abrir 554 s» y «preferencias» son reales o falsos (suspensión, diálogo nativo) y filtrarlos.
- **Hecho en F0 (E7, 2026-11-13) · vigilante y filtro de falsos:**
  - `bloqueo_ui` ahora se anota desde **100 ms** (`UMBRAL_BLOQUEO_MS` en `ui/registro_uso.py`; antes 250) y trae `cpu_ms` (CPU que gastó el proceso
    durante la demora) y `dialogo` (la clase del diálogo modal propio abierto, si había).
  - **Falsos:** una demora de más de 30 s (`SUSPENSION_MS`) en la que el proceso gastó menos del 2 % de CPU se marca `suspension_probable`:
    es la PC suspendida o una espera de la persona en un diálogo nativo, no un congelamiento. El detector (`registro_uso/detector.py`) no la
    cuenta como hallazgo; el evento queda en el registro para verlo. Una demora larga CON CPU (la ventana calculando) sigue contando.
    Limitación: una espera real del proceso aparte (el kernel en otro proceso) también gasta poca CPU del lado de la ventana; por eso el filtro
    solo vale para demoras de más de 30 s. «abrir 554 s» y la mayoría de «preferencias» de la tabla 1.1 son de este tipo si traen `cpu_ms` bajo;
    los registros viejos no traen `cpu_ms`: hasta que haya registros nuevos de la PC de Gerardo no se pueden clasificar.
  - **Piezas de `prueba_ui`:** `scripts/prueba_ui/sonda.py` se instala sola desde `arnes.iniciar` y mide cuánto tarda cada acción simulada
    (`QTest.mouseClick`, `keyClicks`, `sendEvent`…; el manejador de la app corre adentro de la llamada) y cuánto se pasa cada `qWait`. Toda pieza
    que termina con `guardar_registro` suma la comprobación «ninguna acción dejó la ventana sin responder más de 1 s» y falla si alguna lo hace
    (`OMNICAD_FLUIDEZ=aviso` solo informa, `=apagado` no mide). Lo que el guion hace entre llamadas no se mide. Ejemplo hoy: `pieza_completa`, 16 acciones
    de más de 100 ms, 0 de más de 1 s, la peor 250 ms.

### F0 › Tabla hoy / meta (medido el 2026-11-13 en la VPS, 8 núcleos)

Tiempos en **milisegundos**. HOY es la mediana de tres corridas aisladas por escenario; cada corrida toma
el máximo de las acciones medidas (en e, el máximo entre barrido, bobina y solevación). «Primera previa»
mide hasta la primera señal de previa válida de cada cambio, no hasta `frameSwapped`. «—» significa que
la métrica no aplica; **error** significa que no se completó el escenario y no hay presupuesto válido.

| Escenario | Bloqueo máx. HOY | Bloqueo máx. META | Primera previa HOY | Primera previa META | Aceptar HOY | Aceptar META |
|---|---:|---|---:|---:|---:|---:|
| a · Texto, 8 perfiles, Unir, 11 cuerpos | 333,00 | < 250 (tope 1000) | 524,70 | < 300 | 107,53 | < 1000 |
| b · Rosca M20 × 60 modelada | 1824,00 | < 250 (tope 1000) | 3665,45 | < 300 | 1880,15 | < 1000 |
| c · Empalme R2, 200 caras (estrella de 198 lados) | 196,00 | < 250 (tope 1000) | 2272,70 | < 300 | 231,41 | < 1000 |
| d · Desfase de cara | 131,00 | < 250 (tope 1000) | 135,09 | < 300 | 70,26 | < 1000 |
| e · Barrido / bobina / solevación | 1473,00 | < 250 (tope 1000) | 1582,30 | < 300 | 1249,17 | < 1000 |
| f · Combinar dos cuerpos | 54,00 | < 250 (tope 1000) | 115,65 | < 300 | 89,45 | < 1000 |
| g · Eliminar un paso de 20 | 50,00 | < 250 (tope 1000) | — | — | — | — |
| h · Abrir proyecto pesado, sustituto² | 5689,00 | < 250 (tope 1000) | — | — | — | — |
| i · Preferencias, deslizador y combo | 598,00 | < 250 (tope 1000) | — | — | — | — |
| j · Arrastrar punto, 200 entidades | 71,00 | < 33 por evento | — | — | — | — |
| k · Órbita, 300 000 triángulos | 107,96 | < 33 por evento | — | — | — | — |
| l · Abrir `motor_impreso` (real, 292 pasos) | 57534,00 | < 250 (tope 1000) | — | — | — | — |
| m · Abrir `motor_cohete` (real, 41 pasos) | 12492,00 | < 250 (tope 1000) | — | — | — | — |
| n · Abrir `gatoRL` (real, 113 pasos) | 66583,00 | < 250 (tope 1000) | — | — | — | — |
| o · Abrir `ABANICO EMILIA` (real, 3 pasos) | 3735,00 | < 250 (tope 1000) | — | — | — | — |

¹ (2026-11-13, E7) b y c eran errores del guion, no de la app: en b el cuadrito de «Modelado» se marca con un clic
en su esquina (con la barra espaciadora no se marca: B-420); en c un polígono de 198 lados casi liso no se puede
empalmar y la app avisó bien en menos de 1 s («Las aristas elegidas no pertenecen al cuerpo»), por eso c usa una
estrella de 198 lados. Los escenarios l a o abren las piezas reales de Gerardo (copias; se omiten con aviso si falta el archivo):
abrir `motor_impreso` real tarda 57,5 s (el sustituto, 5,8 s), `gatoRL` 66,6 s y `motor_cohete` 12,5 s: son el peor cuello de la fila FL.

² Sustituto de `motor_impreso` (h; el real es el escenario l) reproducible: 217 pasos, 72 uniones, 71 empalmes y
una rosca modelada; archivo de unos 7,12 MB. **Abrir HOY: 5835,00 ms; META: < 1500 ms** (mediana de
7602,65 / 5581,16 / 5835,00 ms). No equivale a medir el archivo original. Otras submedidas: eliminar
el paso, 96,66 ms; abrir Preferencias, 405,50 ms. Los máximos por evento de j y k son 71,00 y 107,96 ms
respectivamente (medianas de los máximos de 30 y 40 movimientos, incluido el repintado).

**Repetir desde `clon/`:**
```bash
QT_QPA_PLATFORM=xcb OMNICAD_PRUEBA_VENTANA=minimizada xvfb-run -a /home/mosos/OmniCAD/clon/.venv/bin/python ../scripts/turno.py --plazo 1500 -- /home/mosos/OmniCAD/clon/.venv/bin/python ../scripts/bench_fluidez.py --rep 3 --json /tmp/fl0.json
```

La corrida completa se ejecutó una vez; el JSON conserva las 33 corridas, errores y submedidas.
`clon/tests/fluidez_presupuestos.json` fija para las tres métricas principales
`round(max(50, HOY × 1,5))` en ms; los `null` sin motivo de omisión son métricas no aplicables.
Son presupuestos de regresión del estado actual, **no** las metas de fluidez de esta tabla.

### F0 › Medición 2026-11-17 (VPS)

Banco F0 `a–k`, 8 núcleos, tres repeticiones por escenario y mediana. Se ordenan los diez escenarios
completados por el mayor exceso relativo de su medida más fallada sobre la meta. La medida elegida es la que
más se aparta de su meta: primera previa (M2), bloqueo máximo (M1), apertura total (M6) o evento (M3).

| Comando | Medida | ms medido | Meta | Repetir |
|---|---|---:|---|---|
| e · Barrido / bobina / solevación | Primera previa de bobina | 4174,64 | < 300 ms (M2) | `bench_fluidez.py e --rep 3` |
| k · Órbita, 300 000 triángulos | Evento más lento | 128,41 | < 33 ms por evento (M3) | `bench_fluidez.py k --rep 3` |
| j · Arrastrar punto, 200 entidades | Evento más lento | 117,54 | < 33 ms por evento (M3) | `bench_fluidez.py j --rep 3` |
| h · Abrir proyecto pesado (sustituto) | Apertura total | 5130,96 | < 1500 ms (M6) | `bench_fluidez.py h --rep 3` |
| i · Preferencias, deslizador y combo | Bloqueo máximo | 507,00 | < 250 ms (M1) | `bench_fluidez.py i --rep 3` |
| c · Empalme R2, 200 caras | Primera previa | 595,04 | < 300 ms (M2) | `bench_fluidez.py c --rep 3` |
| a · Texto, 8 perfiles, Unir, 11 cuerpos | Primera previa | 398,49 | < 300 ms (M2) | `bench_fluidez.py a --rep 3` |
| g · Eliminar un paso de 20 | Bloqueo máximo | 139,00 | < 250 ms (M1) | `bench_fluidez.py g --rep 3` |
| d · Desfase de cara | Primera previa | 127,42 | < 300 ms (M2) | `bench_fluidez.py d --rep 3` |
| f · Combinar dos cuerpos | Primera previa | 95,99 | < 300 ms (M2) | `bench_fluidez.py f --rep 3` |

Repetir cada fila desde `clon/` con este prefijo y cambiar `<letra>` por `a`, `c`, `d`, `e`, `f`, `g`, `h`, `i`, `j` o `k`:

```bash
QT_QPA_PLATFORM=xcb OMNICAD_PRUEBA_VENTANA=minimizada xvfb-run -a \
  /home/mosos/OmniCAD/clon/.venv/bin/python ../scripts/turno.py --plazo 1500 -- \
  /home/mosos/OmniCAD/clon/.venv/bin/python ../scripts/bench_fluidez.py <letra> --rep 3 --json /tmp/fl0.json
```

El escenario `b` (rosca modelada M20 × 60) no aporta cifra: las tres corridas terminaron con
`RuntimeError: No está el asa tam_iso_metrica; longitud completa=False; asas=['desfase', 'longitud']`.

- **Listo cuando:** la tabla «hoy / meta» de los 11 escenarios está commiteada y el test corre con turno.
- **Ejecutor:** E7 (Sonnet medio) arma el banco; E6 revisa la medición. Es mecánico y no decide geometría.

### F1. Toda previa que toca el kernel, al proceso aparte
- **Qué:** cambiar `_previa_pesada` (`comando.py:1843`) de «lista de tipos» a «por defecto aparte». En la ventana
  queda solo lo que la última vez tardó menos de 30 ms para ese comando (ya se mide `ms` en `_calcular_previa`).
  «Última gana»: ya existe `_pendiente_hijo`; falta cortar el cálculo viejo cuando llega un valor nuevo (hoy
  espera `PACIENCIA_PREVIA`). El panel tiene que seguir aceptando teclas mientras calcula. Cubre B-403, B-306 y RS-P6.
- **Listo cuando:** escenarios a, b, d, e y f con bloqueo máximo menor a 250 ms, y un test que teclea tres valores
  seguidos y comprueba que solo se muestra el último.
- **Ejecutor:** E6 (Opus alto). Toca concurrencia y el trabajador: es lo delicado del plan.

### F2. Previa barata inmediata
- **Qué:** que `_previsualizar_prisma` (`comando.py:1772`) salga también al teclear y con las flechas, no solo al
  arrastrar (hoy lo corta la línea 1789). El prisma se ve al instante; la unión exacta llega del proceso aparte y lo
  reemplaza. Extender a Cortar (herramienta en rojo translúcido, como Fusion) y a revolución. Rosca: previa cosmética
  inmediata y la modelada aparte. Mallado grueso en la previa y fino al aceptar.
- **Listo cuando:** en a y b el tiempo hasta la primera previa es menor a 50 ms, y Aceptar usa siempre la forma exacta
  (test que compara el volumen con el de la API).
- **Ejecutor:** E2 (Opus alto) para crear; E3 (Opus alto) para Cortar y modificar.

### F3. Aceptar y recalcular fuera de la ventana
- **Qué:** si la previa exacta ya llegó, Aceptar la reusa (ya existe). Si no, el cálculo corre aparte con barra de
  progreso y botón Cancelar. Lo mismo para eliminar o editar un paso, deshacer y rehacer que recalculan, y abrir un
  proyecto (la ventana aparece enseguida y los cuerpos llegan después). Cubre CPP-F1, CPP-C4 y RS-X2.
- **Listo cuando:** g y h con bloqueo máximo menor a 250 ms; Cancelar deja el documento como estaba (test).
- **También (E11, tanda 13, 2026-11-14):** con Rosca modelada la ventana se traba de 350 a 670 ms aunque la previa va aparte: lee el B-Rep del filete y lo malla en el hilo de la ventana (`leer_previa_visual`). Una traba de 1430 ms (2375 ms de CPU), 25 s después de cerrar el comando, coincide con el autoguardado, que guarda la caché B-Rep del cuerpo roscado (sin comprobar). Candidatos: mallar la previa en el hijo y guardar en otro hilo. **Medido en Linux (FL-3b, 2026-11-14):** recibir la previa de la Rosca tarda 16 ms en la ventana (la malla ya viene del hijo) y el autoguardado no escribe la caché B-Rep (`autoguardar_en_hilo` solo guarda la receta): en la ventana quedan la captura y la receta, 85 ms con la rosca. Lo que trababa era Aceptar: mallar el filete (2,15 s en una sola llamada de OpenCascade que retiene el GIL); ahora reusa la malla de la previa. Falta medirlo en Windows (E11).
- **Ejecutor:** E6 (Opus alto).

### F4. Unir y Cortar solo contra lo que se toca
- **Qué:** comprobar la sospecha de B-403: con «Objetos» vacío, contra cuántos cuerpos se hace la booleana. Filtrar
  primero por caja envolvente (barata) y operar solo con los que intersecan. Mirar antes la ayuda de Fusion
  (`scripts/fusion_docs.py buscar extrude join`).
- **Listo cuando:** el escenario (a) por API tarda lo mismo con 1 cuerpo que con 11 (±20 %), con el mismo resultado.
- **Ejecutor:** E2 (Opus alto).

### F5. El costo que crece con el documento
- **Qué:** hallar por qué una operación local cuesta más cuanto más largo es el documento (P-78: 1,1 s → 8,2 s).
  Candidatos sin confirmar: copiar el estado entero, volumen y cajas exactas por paso (RS-X2), mandar todo el estado
  al trabajador en cada previa (RS-X6). Relojes por función con documentos de 10, 40 y 80 pasos.
- **Listo cuando:** la misma operación no sube más de 20 % entre el documento de 10 pasos y el de 80.
- **Ejecutor:** E6 (Opus alto). Primero medir; no tocar nada sin el reloj que lo pruebe.

### F6. Rosca modelada
- **Qué:** P-78. Girar el cuerpo en vez del surco, un solo corte, y guardar en la sesión la herramienta helicoidal
  por designación, clase y largo, para que cambiar el largo o el desfase la reuse.
- **Listo cuando:** meta M5, con los volúmenes iguales a los de hoy (tolerancia 1e-3) y la suite de roscas verde.
- **Ejecutor:** E6 (Opus alto).

### F7. Booleanas del kernel
- **Qué:** RS-X4 y CPP-P17. Probar `SetRunParallel`, OBB y Glue donde las piezas solo se tocan. Medir con
  `scripts/bench_booleana.py` antes y después.
- **Listo cuando:** `motor_impreso` recalcula al menos 30 % más rápido y la suite de booleanas sigue verde.
- **Ejecutor:** E3 (Opus alto).

### F8. Lo que congela y no es geometría
- **Qué:** preferencias (120 congelamientos), asistente (83), sección, `panel_datos` y el arranque de las herramientas
  de boceto (`sk_rectangulo` 2,6 s, `sk_poligono_circunscrito` 3,3 s, `sk_terminar` 4,7 s). Perfilar cada uno.
  Hipótesis: trabajo repetido en la ventana y, en el asistente, una llamada de red que espera en el hilo.
- **Listo cuando:** ninguno aparece entre los diez primeros del registro, y el escenario (i) queda bajo 100 ms.
- **Ejecutor:** E8 (Sonnet medio) preferencias, asistente y panel; E1 (Opus alto) las herramientas de boceto.
  Son otros archivos: puede ir en paralelo desde el primer día.

### F9. Procesos
- **Qué:** B-396 (trabajadores huérfanos al 100 % de CPU). Arrancar el trabajador durante la portada, para que la
  primera previa no pague el arranque. Un segundo trabajador solo con 8 GB libres o más (CPP-C3).
- **Listo cuando:** al matar al padre el trabajador sale en menos de 5 s (test), y la primera previa de la sesión
  tarda lo mismo que la segunda (±20 %).
- **Ejecutor:** E8 (Sonnet medio) B-396; E6 el precalentado.

### F10. Visor y malla
- **Qué:** no volver a mallar lo que no cambió (RS-X6, CPP-P20). Extracción de la malla en bloque (CPP-C1).
- **Listo cuando:** tras una previa rechazada, la edición siguiente no vuelve a mallar los cuerpos intactos (test).
- **Ejecutor:** E6 (Opus alto).
- ⚠ CPP-C1 pide el OK de Gerardo: bajar las cabeceras de OpenCascade y pybind11 (CPP-F2). Es gratis.

### F11. Regla permanente
- **Qué:** sumar a «Definición de terminado» de `AGENTS.md`: ningún comando deja la ventana sin responder más de
  250 ms y `test_fluidez` queda verde. El chat de la PC manda cada mañana los diez peores congelamientos del
  registro real de Gerardo.
- **Listo cuando:** la regla está escrita y el primer informe diario llegó.
- **Ejecutor:** coordinador.

## 5. Orden

1. F0 (sin baseline no se puede probar ninguna mejora) y, a la vez, F9 › B-396 y F8.
2. F1, y enseguida F2. **Con estos dos desaparece la mayor parte de lo que Gerardo siente.**
3. F4 y F3.
4. F5, F6 y F7 (el núcleo).
5. F10.

Un paquete cerrado y commiteado antes del siguiente en el mismo carril (regla del 2026-11-06).

## 6. Riesgos

| Riesgo | Mitigación |
|---|---|
| El documento de la ventana y el del trabajador quedan distintos | Cada pedido lleva la versión del estado; una respuesta vieja se descarta |
| La previa barata no coincide con el resultado | Siempre la reemplaza la exacta, y Aceptar usa solo la exacta |
| Memoria de la PC (13 GB) | Un solo trabajador; el segundo, condicionado a 8 GB libres |
| Números falsos del registro (suspensión, diálogos) | F0 los filtra antes de fijar metas |
| OpenCascade sigue siendo más lento que el kernel de Fusion | La meta es la fluidez que se siente, no igualar el kernel. La rosca tiene su propia meta (M5) |

## 7. Las 3 acciones de mayor impacto

1. **F1:** toda previa al proceso aparte. Termina con la ventana trabada.
2. **F2:** previa barata al teclear y con las flechas. El cambio se ve al instante.
3. **F0:** el banco. Sin él, cada «quedó más rápido» es una opinión.
