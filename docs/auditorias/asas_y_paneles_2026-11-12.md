# Asas y paneles de las demás herramientas, contra los problemas de Extruir (2026-11-12)

Pedido de Gerardo a partir de B-343, B-344, P-139 y P-140 (Extruir). Esta auditoría mira si pasan también en otras herramientas. Solo lectura y comparación: no se tocó código.

Cómo se probó: ventana real en Linux (`xvfb-run`), eventos de mouse simulados sobre el visor (sonda de E7 con el arnés `scripts/prueba_ui/arnes.py`). Cada asa se arrastró **muy pasado** el límite, hacia los dos lados (flechas: ±400 mm; arcos: ±170°), y se anotó el valor, la vista previa y el mensaje. Escena de `scripts/prueba_ui/escena.py` (caja 30×30×20, cilindro, tubo, caja hueca).

## Qué dice la ayuda de Fusion (`docs/fusion_docs/`)

- **Topes (A) y operación por defecto (B):** la ayuda no los documenta en ninguna herramienta. Solo lista Join / Cut / Intersect / New Body. La única evidencia de que Fusion frena el asa en el límite válido y abre en «Unir» sobre una cara es el reporte de Gerardo con Extruir (B-343, B-344). En las otras herramientas queda **a confirmar en Fusion**.
- **Forma del gizmo del ángulo (C):** la ayuda no describe cómo se dibuja. Solo el reporte de Gerardo (anillo punteado en Extruir).
- **Campos a la vista (D):** la ayuda lista los campos en un orden y no habla de «Más opciones». Lo que figura como sección propia de la herramienta (Rotation Angle de Emboss, Draft Angle de Rib / Web, Taper y Twist de Sweep) se marca como **a confirmar**.
- **Asas en el lienzo:** Emboss («distance manipulator» horizontal y vertical, «angle manipulator» del giro), Draft («angle manipulator»), Revolve («drag the manipulator handle» del ángulo), Shell, Press Pull, Thicken y Offset Faces («manipulator»).

## Tabla (una fila por herramienta)

Leyenda: ✓ igual que Fusion o sin problema; ✗ diferencia; ? a confirmar en Fusion. «Rojo» = la previa queda en rojo con el asa pasada del límite. «Tope fijo» = el asa solo frena en un número fijo (`minimo` / `maximo` de la clase), no en lo que admite la pieza.

| Herramienta | A) Topes al arrastrar | B) Operación por defecto | C) Gizmo del ángulo | D) Campos escondidos |
|---|---|---|---|---|
| Extruir (referencia) | ✗ B-343. Conicidad: tope fijo ±89°, a 89° queda rojo («debe estar entre -89° y 89°»). Distancia sin tope | ✗ B-344: «Cuerpo nuevo» | ✗ P-139: arco con asa suelta | ✗ P-140: Conicidad en «Más opciones» |
| Revolución | ✓ Tope ±360° (ángulo arrastrado de 90° a 260° y a −80°, previa sana). ? si Fusion frena en 360° | ✗ «Cuerpo nuevo» (misma fuente: `campo_operacion()`) | ✗ mismo arco con asa suelta | ✓ sin campos escondidos |
| Barrido | ✓ Torsión ±360°, previa sana. La conicidad no tiene asa | ✗ «Cuerpo nuevo» | ✗ torsión: mismo arco | ✗ Conicidad y Torsión en «Más opciones». ? en Fusion (la ayuda los lista en el diálogo) |
| Solevación | ✗ **sin asas**: ninguna flecha ni arco en la vista. ? si Fusion las tiene | ✗ «Cuerpo nuevo» | — | ✓ solo «Tramos rectos» escondido |
| Nervio | ✗ Grosor: la flecha baja a 0,01 mm y sube a 402 mm sin error de la previa (el mensaje de la previa no se mide acá) | — no tiene campo Operación (Fusion tampoco lo lista) | — | ✗ «Ángulo de desmoldeo» en «Más opciones». En la ayuda es una sección propia («Draft Angle») |
| Red | ídem Nervio | — | — | ✗ «Ángulo de desmoldeo» y «Radio del empalme» en «Más opciones» |
| Repujado | ✓ Profundidad sin tope y previa sana a ±400 mm | — no tiene campo Operación | — | ✗ Desfase horizontal, vertical y Ángulo de giro en «Más opciones», **y sin asas**. La ayuda de Emboss los trae con «distance manipulator» y «angle manipulator» |
| Engrosar | ✗ hacia adentro (−398 mm) queda rojo («398 mm es igual o mayor que el radio de curvatura») | ✗ «Cuerpo nuevo» | — | ✓ |
| Empalme | ✗ radio hacia afuera: sin tope, a 402 mm queda rojo («el radio es demasiado grande para las caras vecinas») | — | — | ✗ Continuidad, Cadena tangente y Esquina en «Más opciones». ? en Fusion |
| Chaflán | ✗ igual que Empalme (distancia 402 mm, rojo) | — | — | ✗ Cadena tangente y Esquina en «Más opciones». ? en Fusion |
| Vaciado | ✗ espesor a 402 mm: rojo («demasiado grande para la pieza») | — | — | ✓ |
| Pulsar/tirar | ✗ hacia adentro (−397 mm): rojo («no queda material») | — | — | ✓ |
| Desfase de caras | ✗ igual que Pulsar/tirar | — | — | ✓ |
| Inclinación (Desmoldeo) | ✗ el arco llega a +175° y −165° (tope fijo ±360°): rojo («el desmoldeo relativo llega a 90 grados o más») | — | ✗ mismo arco | ✗ «Modo de ángulo» y «Invertir dirección de extracción» en «Más opciones». En la ayuda de Draft, Angle Mode es un campo del diálogo |
| Agujero | ✗ **Diámetro** arrastrado a 406 mm: la previa queda **en verde** con el aviso «Cuerpo2 quedó vacío y se eliminó». Profundidad sin tope (408 mm, sana) | — (corta siempre) | — | ✓ |
| Mover/copiar | no se probó el arrastre de la tríada y del arco de giro (la sonda no maneja tríadas). Por código: tríada de ejes y `Angulo` sin tope geométrico | — | ✗ el giro usa el mismo arco (`modificar.py:974`) | ✓ |
| Plano desfasado | ✓ sin tope y previa sana (±400 mm), como cualquier plano | — | — | ✓ |
| Plano en ángulo | ✓ ±360° y previa sana | — | ✗ mismo arco | ✓ |
| Superficie › Extruir | ✓ conicidad ±89° con previa sana | — (siempre superficie nueva) | ✗ mismo arco | ✗ Conicidad en «Más opciones» |
| Superficie › Revolución | ✓ ±360°, sana | — | ✗ mismo arco | ✓ solo «Eje de proyecto» |
| Superficie › Desfase | ✗ hacia adentro (−397 mm): rojo («la superficie se cruza consigo misma») | — | — | ✓ |
| Superficie › Extender | ✓ sin tope y sana; la distancia baja a 0,01 mm | — | — | ✓ |

## Lo que se cargó en `docs/seguimiento/`

| ID | Qué |
|---|---|
| B-345 | Topes fijos, no geométricos: Empalme, Chaflán, Vaciado, Engrosar, Pulsar/tirar, Desfase de caras, Desfase de superficie, Inclinación y la conicidad de Extruir dejan pasar el asa y la previa queda en rojo (misma causa que B-343) |
| B-346 | Agujero: el asa del diámetro llega a 406 mm y la previa queda en verde con «Cuerpo vacío»; al aceptar borra el cuerpo |
| P-141 | «Más opciones» esconde Conicidad y Torsión (Barrido), Ángulo de desmoldeo (Nervio, Red), Modo de ángulo (Inclinación) y la conicidad de Extruir de superficie; ? a confirmar en Fusion |
| P-142 | Repujado: Desfase horizontal, vertical y Ángulo de giro no tienen asa, y Fusion trae un manipulador para cada uno |
| B-344, P-139 | Se les sumó la lista de herramientas que repiten el problema (operación por defecto: Revolución, Barrido, Solevación, Engrosar; arco con asa suelta: seis herramientas más) |

## Lo que no se pudo confirmar

- Si Fusion frena el asa en el límite de cada herramienta, qué hace Fusion con el asa de Solevación y si el Barrido muestra Conicidad y Torsión a la vista: la ayuda no lo dice. Hace falta mirar Fusion (túnel de la PC).
- Mover/copiar: tríada y arco de giro sin probar en la ventana.
- Plano desfasado / en ángulo: la sonda cubre solo el tipo «desfase» y «ángulo» con una selección.
- Nervio y Red: la sonda mide el valor, no el mensaje de la previa con grosores enormes.
