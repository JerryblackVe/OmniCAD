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
- P-78: la rosca crece con el documento (M20 sola 1,1 s; después de tres M8, 8,2 s).
- RS-X4: 72 pasos «combinar» son el 66,7 % del recálculo de `motor_impreso` (16,2 s); faltan `SetRunParallel`, OBB y Glue.
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
