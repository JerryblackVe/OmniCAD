# Auditoría de mensajes de los paneles (P-158)

Regla 14 de `CLAUDE.md`: el mensaje de un panel es **1 renglón**, con ícono (⚠ o ✖) y una palabra clave; el detalle va a la ayuda. Límite medido: **45 caracteres** (el panel «simple» mide 320 px; con la fuente por defecto entran unos 44). Un valor `{}` cuenta como 6 caracteres. El test `tests/test_p158_mensajes_cortos.py` falla si un archivo del alcance suma un mensaje que pasa del límite (trinquete: el tope por archivo solo baja).

Alcance de esta entrega: Bocetos y Sólido (`nucleo/solidos_crear.py`, `nucleo/solidos_modificar.py`, `timeline/ops_solido.py`, `restricciones/boceto.py`, `ui/comandos/{crear,modificar,solido,primitivas,patrones}.py`, `ui/manipuladores.py`). Superficie y el resto van en la próxima entrega. No entran todavía los textos de `Info(...)` ni los que arman las clases de los paneles (`ui/comando.py`).

## Hecho: antes → después

| Dónde | Antes | Después |
|---|---|---|
| `nucleo/solidos_modificar.py:407` | El empalme de {} mm se come justo una cara vecina entera (la deja de ancho cero) y el núcleo no lo resuelve. Probá un… | Empalme de {radio:g} mm: borra una cara. |
| `nucleo/solidos_modificar.py:482` | Una arista del empalme ya no existe: los empalmes de radio asimétrico o G2 no pueden compartir vértice con otro empal… | Empalme asimétrico: hacelos en pasos aparte. |
| `nucleo/solidos_modificar.py:733` | El empalme falló: el radio es demasiado grande para las caras vecinas (no entra). Achicalo. Si el timeline tiene otro… | El radio no entra: achicalo. |
| `nucleo/solidos_modificar.py:741` | El empalme falló: el radio supera el grosor de la pared o el espacio disponible. El resultado tiene caras cruzadas o … | Empalme: el radio no entra. |
| `nucleo/solidos_modificar.py:915` | La arista elegida es tangente (lisa): sus dos caras ya se unen sin esquina y no hay nada que {}. Elegí una arista con… | Arista tangente: no hay nada que {que}. |
| `nucleo/solidos_modificar.py:997` | El chaflán falló: la distancia supera el grosor de la pared o el espacio disponible. El resultado tiene caras cruzada… | Chaflán: la distancia no entra. |
| `nucleo/solidos_modificar.py:1178` | El vaciado hacia afuera falló con {} mm: el kernel no pudo construir una pared válida sobre estas caras B-spline. No … | Vaciado hacia afuera: {espesor:g} mm no entra. |
| `nucleo/solidos_modificar.py:1183` | El vaciado falló: la cara quitada tiene un chaflán o un empalme en su borde más angosto que el espesor ({} mm) y el k… | Vaciado: chaflán o empalme muy angosto. |
| `nucleo/solidos_modificar.py:1269` | Vaciado: un cuerpo con una rosca modelada no se puede vaciar (el kernel tarda minutos y falla). Vaciá el cuerpo antes… | Rosca modelada: no se puede vaciar. |
| `nucleo/solidos_modificar.py:1277` | Quitaste todas las caras: no queda pared que dejar. Elegí menos caras (o ninguna, para un hueco cerrado dentro del cu… | No quedó pared: elegí menos caras. |
| `nucleo/solidos_modificar.py:1301` | Vaciado: el espesor no cabe en la pieza: la pared se cruza consigo misma ({} autointersecciones). Probá un espesor me… | Vaciado: el espesor no cabe ({n} cruces). |
| `nucleo/solidos_modificar.py:1313` | El modo relativo no sabe medir un cilindro inclinado respecto de la dirección de extracción: usá el modo absoluto. | Cilindro inclinado: usá el modo absoluto. |
| `nucleo/solidos_modificar.py:1337` | Una arista recta solo sirve de línea de partición si es perpendicular a la dirección de extracción; elegí un plano, u… | Línea de partición: no es perpendicular. |
| `nucleo/solidos_modificar.py:1341` | La línea de partición tiene que ser una curva plana: elegí un plano, una cara o una curva que quede en un plano. | La línea de partición debe ser plana. |
| `nucleo/solidos_modificar.py:1714` | Desfase de caras: el filete helicoidal de una rosca modelada no se puede desfasar (el kernel tarda minutos y falla). … | Una rosca modelada no se puede desfasar. |
| `nucleo/solidos_modificar.py:1721` | Desfase de caras: en un cuerpo con una rosca modelada, el kernel tarda minutos y falla con las caras curvas. Desfasá … | Con rosca modelada no se puede desfasar. |
| `nucleo/solidos_modificar.py:1733` | Desfase de caras: con {} mm la cara se da vuelta: la distancia es igual o mayor que su radio de curvatura (un cilindr… | Desfase de {abs(dist):g} mm: da vuelta la cara. |
| `nucleo/solidos_modificar.py:1868` | Este tipo de división necesita curvas de boceto, aristas o una cara como herramienta (un plano no se puede proyectar). | Esa división pide curvas, aristas o una cara. |
| `nucleo/solidos_modificar.py:1900` | «Punto más cercano» solo divide caras planas: sobre una cara curva las cuerdas rectas no caen en la superficie. Usá «… | «Punto más cercano» solo en caras planas. |
| `nucleo/solidos_modificar.py:1941` | Dividir cuerpo: las partes suman {} mm³ y el cuerpo tiene {} mm³: el cuerpo tiene la cáscara abierta o al revés. Revi… | Dividir: el cuerpo tiene la cáscara abierta. |
| `nucleo/solidos_modificar.py:2165` | No se pueden borrar esas caras: las caras vecinas no alcanzan a cerrar el hueco (por ejemplo, la tapa de una caja). | Esas caras no se pueden borrar: no cierran. |
| `nucleo/solidos_crear.py:1125` | Con {}° de inclinación el perfil crece hasta {} mm y no entra en la curva de la ruta (radio {} mm, al {} del recorrid… | Inclinación máx. {maximo:.1f}° en esta ruta. |
| `nucleo/solidos_crear.py:1300` | El barrido con {}° de torsión no se pudo resolver en esta ruta. Donde el cálculo exacto falla, la torsión admite como… | Torsión máx. ±{TORSION_MAXIMA_CURVILINEA:g}° en esta ruta. |
| `nucleo/solidos_crear.py:1339` | El cuerpo mide {} mm y la ruta {} mm: con el tope de {} copias quedarían separadas, sin formar un barrido. Acortá la … | Ruta muy larga: {MUESTRAS_BARRIDO_CUERPO} copias no alcanzan. |
| `nucleo/solidos_crear.py:1364` | La torsión del barrido necesita una ruta sin esquinas: la ruta quiebra {} entre dos aristas (admite hasta {}). Redond… | Torsión: la ruta quiebra {} (máx. {}).".format(*grados) |
| `nucleo/solidos_crear.py:1660` | El ángulo de la condición de borde, medido desde la normal, tiene que quedar entre −90 y 90 grados, y el peso es posi… | Ángulo de borde entre −90° y 90°; peso > 0. |
| `nucleo/solidos_crear.py:1799` | Solevado: el sólido se autointersecta; la dirección del flujo de la solevación no es válida. Bajá el peso o cambiá el… | Solevado: el sólido se autointersecta. |
| `nucleo/solidos_crear.py:1810` | Solevado: las secciones son solo puntos. Un punto sirve de extremo (punta) de un perfil: elegí al menos un perfil. | Solevado: elegí al menos un perfil. |
| `nucleo/solidos_crear.py:1826` | Solevado: el punto elegido está en el plano del perfil (suele ser su centro, tomado por error): la solevación quedarí… | Solevado: punto en el plano del perfil. |
| `nucleo/solidos_crear.py:1841` | Solevado: las secciones van y vuelven (la {} queda detrás de la {} en el camino de la primera a la última) y la solev… | Solevado: la sección {i + 2} va hacia atrás. |
| `nucleo/solidos_crear.py:2180` | Los perfiles no caen sobre las caras elegidas: se proyectan en su lugar, así que hay que moverlos en el boceto para q… | Perfiles fuera de las caras: movelos encima. |
| `nucleo/solidos_crear.py:2771` | El agujero queda tangente a una pared y deja el material con espesor cero: cambiá el diámetro o la posición unas déci… | Agujero tangente: cambiá la posición. |
| `nucleo/solidos_crear.py:3054` | El kernel no pudo barrer el perfil por la hélice: probá otro tamaño o menos largo; si es una rosca, probá la cosmética. | No se pudo barrer la hélice. |
| `nucleo/solidos_crear.py:3083` | La holgura de la rosca es demasiado grande para su paso: la clase y la holgura juntas corren los flancos {} mm y el m… | La holgura de la rosca es demasiado grande. |
| `nucleo/solidos_crear.py:3434` | El paso de la rosca ({} mm) supera el largo roscado ({} mm): Ø de la cara {} mm y Ø de la rosca {} mm. Elegí otro tam… | Paso {paso:g} mm > largo roscado {largo:g} mm. |
| `nucleo/solidos_crear.py:3644` | La bobina no se pudo construir con esas medidas: el sólido sale dado vuelta. Probá con menos altura o menos ángulo. | Bobina inválida: menos altura o ángulo. |
| `nucleo/solidos_crear.py:3946` | Las direcciones 1 y 2 son paralelas: elegí una segunda dirección que no sea la misma recta (o dejá la cantidad 2 en 1). | Direcciones 1 y 2 paralelas: cambiá la 2. |
| `nucleo/solidos_crear.py:4013` | El ángulo del patrón circular tiene que ser distinto de cero y no dar más de una vuelta: con ese valor las copias que… | Ángulo: distinto de 0 y menor que 360°. |
| `nucleo/solidos_crear.py:4367` | Una parte del perfil, al girar, nunca llega a ese plano: el ángulo no queda definido. Elegí un plano que todo el perf… | El perfil no llega a ese plano: elegí otro. |
| `nucleo/solidos_crear.py:4576` | El diseño no encierra un volumen interior. Tapá las aberturas con superficies (parche o plano) y elegílas como tapas. | Sin volumen interior: tapá las aberturas. |
| `nucleo/solidos_crear.py:4853` | El gancho tiene que tocar el cuerpo del gancho: los puntos tienen que estar sobre el cuerpo o la base tiene que alcan… | El gancho debe tocar el cuerpo. |
| `timeline/ops_solido.py:295` | La solevación no encierra volumen: los perfiles no pueden estar todos en el mismo plano y una solevación cerrada no p… | La solevación no encierra volumen. |
| `timeline/ops_solido.py:480` | Elegí dónde van los agujeros (puntos de boceto, un punto sobre una cara o una cara con dos aristas de referencia). | Elegí dónde van los agujeros. |
| `timeline/ops_solido.py:867` | El paso «{}» no dejó una herramienta que se pueda repetir: tiene que estar antes de este paso, activo y sin error, y … | El paso «{pid}» no se puede repetir. |
| `timeline/ops_solido.py:873` | El paso «{}» interseca: repetirlo dejaría solo lo común a todas las copias. Se repiten los pasos que cortan, unen o c… | El paso «{pid}» interseca: no se repite. |
| `timeline/ops_solido.py:1066` | Elegí los puntos del patrón (puntos de boceto, vértices, puntos de construcción, un boceto con puntos sueltos o coord… | Elegí los puntos del patrón. |
| `restricciones/boceto.py:391` | El desfase de {} mm hacia adentro deja el radio {} en cero ({} mm de radio): usá una distancia menor que {} mm. | Desfase {achica:g} mm: el radio queda en cero. |
| `restricciones/boceto.py:393` | El desfase de {} mm hacia adentro deja el radio {} negativo ({} mm de radio): hacia adentro el máximo es menos de {} mm. | Desfase {achica:g} mm: el radio queda negativo. |
| `restricciones/boceto.py:2103` | Lo que elegiste no se proyecta con la misma forma que la proyección original (otra cantidad o tipo de curvas): usá Ro… | La proyección cambió: rompé el vínculo. |
| `restricciones/boceto.py:4379` | Un patrón de boceto admite hasta {} copias (pidió {}): para más, usá un patrón de cuerpos (Sólido › Crear › Patrón › … | Patrón: máx. {MAX_COPIAS_PATRON} copias (pediste {n1 * n2 - 1}). |
| `restricciones/boceto.py:4397` | Las dos direcciones son paralelas: las copias de una fila caerían sobre las de la otra. Cambiá el ángulo de la direcc… | Direcciones paralelas: cambiá la 2. |
| `restricciones/boceto.py:4403` | Un patrón de boceto admite hasta {} copias (pidió {}): para más, usá un patrón de cuerpos (Sólido › Crear › Patrón › … | Patrón: máx. {MAX_COPIAS_PATRON} copias (pediste {n - 1}). |
| `restricciones/boceto.py:4414` | El patrón copiaría {} puntos ({} copias × {}): un patrón de boceto admite hasta {}, porque cada copia queda atada al … | Patrón: máx. {MAX_PUNTOS_PATRON} puntos (pediste {copias * puntos}). |
| `restricciones/boceto.py:4479` | El centro del patrón coincide con la geometría elegida: al girarla quedaría en el mismo lugar y las copias saldrían e… | El centro cae sobre la geometría. |
| `ui/manipuladores.py` (aviso del asa) | «Radio: el asa frena en 36.26 mm. Con más: <error de 5 renglones>» | «Radio máx. 36.26 mm» |

55 mensajes acortados.

## Pendiente: pasan de 45 caracteres

Lista generada de la fuente al cerrar esta entrega; la versión corta de cada uno se escribe al acortarlo (el tope del test baja con cada uno).

### `nucleo/solidos_crear.py` (145)

| Línea | Largo | Texto |
|---|---|---|
| 3411 | 107 | Demasiadas vueltas para una rosca modelada ({} vueltas): usá la rosca cosmética o un tamaño más g… |
| 1360 | 105 | En una ruta cerrada la torsión del barrido admite como máximo ±{}° ({} vueltas); recibió {}°. |
| 3406 | 105 | {} es una rosca cónica: sobre una cara cilíndrica solo va cosmética (o con Agujero › Roscado cóni… |
| 1204 | 103 | La ruta tiene que estar sobre la superficie guía (cada arista de la ruta, apoyada en una de sus c… |
| 3275 | 94 | El kernel armó mal el surco de la rosca: probá otro tamaño, menos largo o una rosca cosmética. |
| 820 | 90 | El desfase ({} mm) deja el final del otro lado del perfil: el objeto está a {} mm. |
| 3915 | 89 | Una copia a suprimir del patrón rectangular es un entero i o un par [i, j]: llegó {}. |
| 3912 | 89 | Una copia a suprimir del patrón rectangular es un entero i o un par [i, j]: llegó {}. |
| 1864 | 88 | El sentido invertido no llega al cuerpo: desactivá «Cambiar dirección» o mové el boceto. |
| 4056 | 87 | La distancia del patrón en ruta no puede ser cero: las copias quedarían una sobre otra. |
| 3646 | 86 | Las distancias deben ser finitas: el inicio debe estar entre cero y el fin de la ruta. |
| 3943 | 86 | La distancia {} del patrón no puede ser cero: las copias quedarían una sobre otra. |
| 1021 | 85 | La torsión del barrido admite como máximo ±{}° ({} vueltas); recibió {}°. |
| 1724 | 85 | OpenCascade no admite solevado con varios carriles: usá uno solo o una línea central. |
| 4722 | 85 | El perfil del apoyo tiene que quedar dentro del cuerpo (ni por encima ni por debajo). |
| 3685 | 84 | Un patrón admite como máximo {} instancias (el original cuenta); pediste {}. |
| 1640 | 83 | La condición «Punto tangente» es de un perfil que es un punto, junto a un contorno. |
| 611 | 82 | La inclinación cierra una parte del perfil: probá una distancia o un ángulo menor. |
| 1532 | 82 | Con ese ángulo la sección auxiliar de la condición de borde se achica a casi nada. |
| 3605 | 82 | Con ese ángulo la bobina llega al eje antes del final: bajá el ángulo o la altura. |
| 597 | 82 | La inclinación cierra una parte del perfil: probá una distancia o un ángulo menor. |
| 2708 | 82 | El avellanado necesita diámetro mayor que el del agujero y ángulo entre 0° y 180°. |
| 2701 | 80 | El abocardado necesita diámetro mayor que el del agujero y profundidad positiva. |
| 2602 | 79 | La cara «hasta» queda detrás del inicio del agujero (o el desfase la deja ahí). |
| 4362 | 79 | El objeto está en el mismo plano que el perfil: elegí uno que esté a un ángulo. |
| 4754 | 79 | El apoyo tiene que tocar el cuerpo: el perfil es un agujero dentro de la pared. |
| 3580 | 78 | Las revoluciones de la bobina tienen que ser mayores que cero; recibió {}. |
| 4113 | 78 | El punto de referencia del patrón tiene que ser [x, y, z] con números finitos. |
| 249 | 76 | La distancia sobre la ruta va de 0 a 1 (fracción del total); recibió {}. |
| 2983 | 76 | La holgura de impresión 3D no puede ser negativa: usá 0 o un valor positivo. |
| 4610 | 76 | La arista del labio no tiene largo: elegí una arista del borde de una pared. |
| 1595 | 76 | La superficie de la cara no se prolonga hasta donde pide la condición Suave. |
| 4612 | 75 | La arista del labio es de costura: elegí una arista del borde de una pared. |
| 4751 | 75 | El apoyo no pasa por las caras superiores elegidas: están fuera del perfil. |
| 2682 | 74 | Las roscas cónicas (R, NPT) no se modelan: usá Roscado cónico (cosmético). |
| 3308 | 73 | Las roscas cónicas no tienen tamaño automático sobre una cara cilíndrica. |
| 725 | 73 | La inclinación no se admite en la extrusión delgada de un perfil abierto. |
| 2511 | 73 | El boceto a envolver debe estar en un plano paralelo al eje del cilindro. |
| 4706 | 72 | El grosor del apoyo tiene que ser {} mm: la suma de los lados 1 y 2. |
| 3660 | 72 | El espesor de la tubería hueca debe ser positivo y menor que la sección. |
| 1669 | 72 | La condición {} necesita la cara a la que la superficie es tangente. |
| 426 | 71 | Con inclinación, el perfil debe ser plano y transversal a la extrusión. |
| 1567 | 70 | La sección no está sobre el borde de la cara de la condición Tangente. |
| 924 | 70 | La extrusión no llega a la cara objetivo (la cara no la corta entera). |
| 1218 | 70 | La inclinación del barrido hace desaparecer el perfil antes del final. |
| 640 | 69 | El desfase del contorno se partió en varios lazos: reducí el espesor. |
| 1911 | 69 | {}: no llega al cuerpo (revisá el sentido o usá una profundidad). |
| 1925 | 69 | {}: no llega al cuerpo (revisá el sentido o usá una profundidad). |
| 2634 | 69 | Las dos aristas de referencia son paralelas: elegí dos que se crucen. |
| 3583 | 69 | El paso de la bobina tiene que ser mayor que cero; recibió {} mm. |
| 860 | 69 | La cara y sus caras adyacentes no cubren todo el perfil de extrusión. |
| 923 | 69 | La cara y sus caras adyacentes no cubren todo el perfil de extrusión. |
| 2578 | 68 | ISO 273 no tiene el tamaño «{}»: hay M1.6 a M64 (solo métricos). |
| 1633 | 68 | No hay una sección en la posición {} para la condición de borde. |
| 965 | 67 | Los perfiles abiertos solo se revolucionan como revolución delgada. |
| 2615 | 66 | La posición por referencias necesita dos aristas y dos distancias. |
| 4115 | 66 | Cada punto del patrón tiene que ser [x, y, z] con números finitos. |
| 4415 | 66 | Los dos ejes de la orientación son paralelos: elegí dos distintos. |
| 4703 | 66 | El apoyo necesita material del lado 1: el lado 2 es el del perfil. |
| 604 | 66 | No se pudo crear el lateral curvo de la extrusión con inclinación. |
| 2397 | 65 | Los perfiles deben estar en un plano paralelo a la cara objetivo. |
| 4511 | 65 | La pared del tubo tiene que estar entre 0 y el radio ({} mm). |
| 1648 | 65 | La condición de borde necesita secciones con contorno, no puntos. |
| 1663 | 65 | La condición de borde necesita secciones con contorno, no puntos. |
| 1285 | 65 | La fracción del carril va de 0 (sin incluir) a 1; recibió {}. |
| 1655 | 64 | La condición {} solo vale en la primera y la última sección. |
| 4333 | 64 | El vértice está sobre el eje de revolución: no define un ángulo. |
| 812 | 64 | Hasta caras adyacentes necesita una cara o un plano como límite. |
| 338 | 63 | {}: el kernel produjo un sólido inválido con estos valores. |
| 2598 | 63 | El agujero no llega a la cara o cuerpo «hasta» en su dirección. |
| 866 | 63 | La extensión 'Al objeto' no se combina con dirección simétrica. |
| 776 | 62 | Los perfiles abiertos solo se extruyen como extrusión delgada. |
| 1736 | 62 | El solevado cerrado no se combina con línea central ni carril. |
| 3608 | 62 | El paso es menor que la sección: las espiras se superpondrían. |
| 4584 | 62 | El diámetro exterior del saliente debe superar al del agujero. |
| 4701 | 62 | Las distancias de los lados del apoyo no pueden ser negativas. |
| 1164 | 62 | La torsión y la inclinación no se combinan con un carril guía. |
| 1274 | 62 | La superficie guía no se combina con un carril ni con torsión. |
| 4242 | 62 | No se pudo desfasar la superficie para el engrosado simétrico. |
| 1613 | 62 | No se pudo armar la sección auxiliar de la condición Tangente. |
| 3591 | 61 | Diámetro, sección, revoluciones y altura deben ser positivos. |
| 693 | 61 | No se pudieron unir los perfiles vecinos en una región plana. |
| 4163 | 60 | La multitransformación necesita al menos una transformación. |
| 4790 | 60 | La extensión por distancia necesita la distancia de la base. |
| 3072 | 60 | El cilindro es más grueso que el diámetro mayor de la rosca. |
| 637 | 59 | No se pudo desfasar el contorno (espesor demasiado grande). |
| 4262 | 59 | No se pudieron calcular las celdas del relleno de contorno. |
| 4699 | 59 | El apoyo necesita al menos la distancia de los lados 1 o 2. |
| 2593 | 59 | El plano «hasta» es paralelo al agujero: no lo corta nunca. |
| 3069 | 59 | El agujero es más grande que el diámetro mayor de la rosca. |
| 746 | 58 | El plano objetivo es paralelo a la dirección de extrusión. |
| 3402 | 58 | La longitud y el desfase de la rosca no entran en la cara. |
| 4053 | 58 | El giro del patrón en ruta tiene que ser un ángulo finito. |
| 4647 | 58 | Ancho y alto deben ser positivos y la holgura no negativa. |
| 4663 | 58 | Ancho y alto deben ser positivos y la holgura no negativa. |
| 1239 | 58 | El barrido no cierra un sólido (¿el perfil está abierto?). |
| 2486 | 58 | No se pudo proyectar el boceto sobre la cara del repujado. |
| 2621 | 58 | Las referencias del agujero tienen que ser aristas rectas. |
| 4832 | 58 | La ranura no corta el cuerpo: el gancho no llega hasta él. |
| 3340 | 57 | «{}» es una rosca solo exterior: no va en un agujero. |
| 3714 | 57 | La unión de las instancias del patrón falló en el kernel. |
| 2684 | 57 | «{}» es una rosca solo exterior: no va en un agujero. |
| 3344 | 57 | «{}» es una rosca solo exterior: no va en un agujero. |
| 4167 | 57 | Una transformación de la lista no dejó ninguna instancia. |
| 1643 | 56 | El peso de la condición de borde tiene que ser positivo. |
| 1716 | 55 | Un punto solo puede ser la primera o la última sección. |
| 1859 | 55 | Desde la curva no se llega al cuerpo en ningún sentido. |
| 2071 | 55 | No se encontraron las caras de la red para empalmarlas. |
| 2544 | 55 | No se pudo recortar el repujado sobre la cara tangente. |
| 1316 | 54 | La orientación alineada necesita la dirección del eje. |
| 2116 | 54 | La alineación del repujado debe tener valores finitos. |
| 4716 | 54 | El apoyo necesita perfiles cerrados de boceto o caras. |
| 1270 | 54 | La orientación alineada necesita la dirección del eje. |
| 1954 | 54 | Nervio: no se pudo ajustar la cara de llegada oblicua. |
| 217 | 53 | La ruta debe ser una sola cadena continua de aristas. |
| 422 | 53 | El ángulo de inclinación debe estar entre -89° y 89°. |
| 4697 | 53 | Las caras superiores del apoyo tienen que ser planas. |
| 1960 | 53 | Nervio: el kernel no pudo ajustar la llegada oblicua. |
| 2612 | 52 | La posición por referencias va sobre una cara plana. |
| 3576 | 52 | La espiral necesita revoluciones y paso, sin altura. |
| 4545 | 52 | No se pudo calcular el volumen de fluido del diseño. |
| 2625 | 52 | Una arista de referencia es perpendicular a la cara. |
| 919 | 52 | No se pudo cortar la extrusión con la cara objetivo. |
| 2703 | 52 | La profundidad del abocardado supera la del agujero. |
| 254 | 51 | La distancia sobre la ruta debe ser mayor que cero. |
| 3578 | 51 | Dá exactamente dos de: revoluciones, altura y paso. |
| 2686 | 51 | Un agujero cónico no lleva rosca modelada paralela. |
| 3020 | 51 | El ángulo de la bobina debe estar entre -89° y 89°. |
| 1718 | 50 | Un solevado cerrado no admite puntos como sección. |
| 3074 | 50 | El cilindro es más fino que el núcleo de la rosca. |
| 2534 | 50 | No se pudo envolver el contorno sobre el cilindro. |
| 2720 | 49 | El ángulo de la punta debe estar entre 0° y 180°. |
| 3322 | 49 | El cuerpo no tiene caras cilíndricas para roscar. |
| 1759 | 48 | El kernel no pudo solevar con esa línea central. |
| 3526 | 47 | El kernel no pudo cortar la rosca en el cuerpo. |
| 1722 | 47 | Elegí carriles o una línea central, no los dos. |
| 2693 | 47 | La conicidad cierra el agujero antes del fondo. |
| 3603 | 47 | La sección no entra: cruza el eje de la bobina. |
| 4117 | 47 | El patrón en puntos necesita al menos un punto. |
| 208 | 47 | No se pudo encadenar las aristas en un alambre. |
| 1233 | 47 | El kernel no pudo barrer el perfil por la ruta. |
| 4590 | 47 | El cuerpo no está en la dirección del saliente. |
| 1358 | 46 | Torsión: la ruta quiebra {} (máx. {}). |
| 2737 | 46 | El cuerpo no está en la dirección del agujero. |
| 1149 | 46 | El carril guía no puede empezar sobre la ruta. |

### `nucleo/solidos_modificar.py` (51)

| Línea | Largo | Texto |
|---|---|---|
| 1673 | 109 | Desfase de caras: no queda material: la cara entra hasta atravesar todo el cuerpo. Probá una dist… |
| 2114 | 107 | La línea de partición no es plana: «Cuerpo sólido» y «Cuerpo vaciado» la necesitan plana. Usá «So… |
| 530 | 107 | El radio asimétrico y la continuidad G2 necesitan caras planas perpendiculares a la arista en sus… |
| 895 | 103 | La esquina «Mezcla» no pudo redondear la unión de los chaflanes: probá «Inglete» o una distancia … |
| 1784 | 99 | {}: no queda material: la cara entra hasta atravesar todo el cuerpo. Probá una distancia menor. |
| 1377 | 98 | Una cara no admite desmoldeo (solo planas, cilíndricas o cónicas, y no paralelas al plano neutro). |
| 493 | 95 | El radio asimétrico y la continuidad G2 solo se hacen en aristas rectas entre dos caras planas. |
| 979 | 94 | El chaflán abrió el sólido: la distancia es demasiado grande para las caras vecinas. Achicala. |
| 870 | 93 | No hay esquinas donde se junten tres chaflanes: la esquina «Inglete» no tiene nada que hacer. |
| 862 | 92 | La esquina «Inglete» solo funciona con chaflanes planos (aristas rectas entre caras planas). |
| 522 | 91 | El empalme falló: el radio es demasiado grande para las caras vecinas (no entra). Achicalo. |
| 2097 | 91 | «Cuerpo vaciado» necesita un cuerpo vaciado: aplicale Vaciado antes, o usá «Cuerpo sólido». |
| 544 | 91 | El empalme falló: el radio es demasiado grande para las caras vecinas (no entra). Achicalo. |
| 769 | 90 | Las aristas del redondeo completo tienen que ser rectas y paralelas a las caras laterales. |
| 649 | 88 | La continuidad G2 va con radio constante o asimétrico, y los radios deben ser positivos. |
| 751 | 85 | Las dos caras laterales del redondeo completo tienen que ser paralelas y enfrentadas. |
| 975 | 84 | El chaflán falló: la distancia es demasiado grande para las caras vecinas. Achicala. |
| 1522 | 82 | El giro necesita un destino plano o eje: un punto no tiene alrededor de qué girar. |
| 1371 | 82 | Con el ángulo que ya tiene la cara, el desmoldeo relativo llega a 90 grados o más. |
| 1301 | 81 | El modo relativo solo sirve con caras planas o cilíndricas: usá el modo absoluto. |
| 748 | 78 | El redondeo completo necesita tres caras planas (una central y dos laterales). |
| 673 | 78 | La esquina Setback va con radio constante y una distancia de setback positiva. |
| 1778 | 75 | {}: la cara ya está sobre el plano destino, no hay nada que reemplazar. |
| 1514 | 74 | Solo se alinea plano con plano, eje con eje o un punto con cualquier cosa. |
| 264 | 70 | Herramienta de división no reconocida (plano, cara, aristas o cuerpo). |
| 760 | 70 | La cara central tiene que compartir una arista con la primera lateral. |
| 465 | 69 | Las caras no tienen vértices de donde sacar el borde que no se mueve. |
| 753 | 69 | Las caras laterales tienen que ser perpendiculares a la cara central. |
| 1728 | 69 | El destino es perpendicular a la cara: no se puede extender hasta él. |
| 1451 | 68 | La matriz de transformación debe ser 4x4 afín (última fila 0 0 0 1). |
| 1779 | 68 | El destino no corta por completo la extensión de las caras elegidas. |
| 710 | 68 | El radio variable necesita ≥ 2 puntos con posición 0..1 y radio > 0. |
| 509 | 66 | La arista no tiene esquina que empalmar (las caras son tangentes). |
| 2134 | 66 | No se pudieron quitar esas caras: las vecinas no cierran el hueco. |
| 1380 | 65 | El ángulo de desmoldeo no cambia ninguna cara: no puede ser cero. |
| 1847 | 65 | Elegí la dirección de proyección (un eje, una arista o una cara). |
| 2182 | 63 | No se encontraron empalmes con radio <= {} mm en el cuerpo. |
| 702 | 62 | La cuerda debe ser positiva y la arista no puede ser tangente. |
| 1386 | 59 | El desmoldeo falló en el kernel (ángulo demasiado grande?). |
| 1350 | 53 | El desmoldeo de dos lados necesita el segundo ángulo. |
| 964 | 53 | El ángulo del chaflán debe estar entre 0 y 90 grados. |
| 1402 | 52 | Indicá un factor uniforme o tres factores, no ambos. |
| 959 | 51 | La segunda distancia del chaflán debe ser positiva. |
| 787 | 49 | La regla 'entre' necesita dos conjuntos de caras. |
| 1315 | 49 | La curva de la línea de partición no tiene largo. |
| 1412 | 48 | Los tres factores de escala deben ser positivos. |
| 2073 | 48 | No se pudo partir una cara libre por su silueta. |
| 1768 | 48 | El destino no corta la normal de la cara origen. |
| 766 | 47 | La arista del redondeo completo no tiene largo. |
| 925 | 47 | Tipo de esquina del chaflán desconocido: {} |
| 1255 | 46 | Los espesores del vaciado deben ser positivos. |

### `timeline/ops_solido.py` (46)

| Línea | Largo | Texto |
|---|---|---|
| 593 | 104 | El agujero deja sin material a {}: es más grande que el cuerpo. Achicá el diámetro o la profundidad. |
| 1091 | 103 | «suprimir» tiene que ser una lista de números enteros (o pares [i, j] en el rectangular): llegó {}. |
| 1297 | 102 | «factor» {} con {} instancias da una escala fuera de 1e-6 a 1e6: bajá la cantidad o el factor. |
| 164 | 100 | El eje de la orientación alineada tiene que ser un eje, una arista recta, un plano o una cara plana. |
| 1255 | 92 | Agregá al menos una transformación (rectangular, circular, ruta, puntos, simetria o escala). |
| 951 | 92 | El componente «{}» ya fue movido por una unión: copiá sus cuerpos o volvé a su posición. |
| 1118 | 90 | La distribución «{}» solo existe en el patrón circular: usá «extension» o «espaciado». |
| 1288 | 85 | «n» (instancias con el original) tiene que ser un entero de al menos 2; llegó {}. |
| 209 | 84 | El barrido no encierra volumen: el plano del perfil no puede ser paralelo a la ruta. |
| 160 | 82 | Elegí el eje de la orientación alineada (un eje, una arista, un plano o una cara). |
| 267 | 82 | La condición Tangente o Suave necesita la cara a la que la superficie es tangente. |
| 1448 | 81 | El desfase y la mezcla no son negativos y la solidez del desfase va de 0 a 100 %. |
| 496 | 80 | Extensión «Hasta»: elegí la cara, el plano o el cuerpo donde termina el agujero. |
| 1423 | 80 | La ruta y las zonas de la retícula son puntos, aristas, curvas, caras o cuerpos. |
| 180 | 77 | El barrido de un cuerpo no usa carril, superficie guía, torsión ni conicidad. |
| 1294 | 77 | «factor» no puede ser 1: todas las copias quedarían encimadas en el original. |
| 1261 | 73 | Transformación {}: «tipo» tiene que ser uno de: {}; llegó {}. |
| 1577 | 72 | «Reemplazar con primitivas» solo hace caja, cilindro o esfera (no tubo). |
| 527 | 70 | Roscado cónico: {} no es una rosca de tubería cónica (R/Rc o NPT). |
| 185 | 69 | «{}» no es un cuerpo sólido: el barrido de un cuerpo lo necesita. |
| 489 | 67 | La posición por referencias necesita dos aristas rectas de la cara. |
| 1751 | 67 | El cuerpo de la ranura tiene que ser distinto del cuerpo del labio. |
| 1431 | 64 | Elegí el sólido o la malla cerrada que se llena con la retícula. |
| 1837 | 64 | El cuerpo del gancho y el de la ranura tienen que ser distintos. |
| 1083 | 63 | «suprimir» tiene que ser una lista de instancias: llegó {}. |
| 1434 | 63 | La retícula se aplica a un cuerpo sólido o a una malla cerrada. |
| 59 | 62 | {} se autointerseca (encierra un volumen negativo): {} |
| 1544 | 61 | Elegí el sistema de coordenadas de usuario de la orientación. |
| 1796 | 61 | El apoyo necesita perfiles cerrados de boceto o caras planas. |
| 1800 | 60 | Los perfiles del apoyo tienen que estar en planos paralelos. |
| 1446 | 59 | El tamaño de celda es positivo y la solidez va de 1 a 99 %. |
| 857 | 58 | Elegí las operaciones (pasos del timeline) que se repiten. |
| 963 | 58 | Elegí las operaciones (pasos del timeline) que se repiten. |
| 1651 | 58 | Elegí el componente: ENSAMBLAR › Nuevo componente lo crea. |
| 1367 | 53 | Elegí el cuerpo que se repite (objeto personalizado). |
| 486 | 52 | La posición por referencias va sobre una cara plana. |
| 1292 | 52 | «factor» tiene que ser mayor que cero; llegó {}. |
| 1748 | 51 | Elegí el cuerpo de la ranura del labio y acanalado. |
| 1830 | 49 | Elegí los puntos de boceto donde van las grampas. |
| 513 | 49 | {} es una rosca cónica: usá «Roscado cónico». |
| 914 | 48 | Elegí los planos, ejes o puntos de construcción. |
| 1488 | 48 | Elegí las herramientas que encierran el volumen. |
| 1549 | 48 | La orientación necesita dos ejes: eje_a y eje_b. |
| 69 | 47 | {} se autointerseca ({} {}): {} |
| 1687 | 47 | Elegí puntos de boceto donde van los salientes. |
| 122 | 46 | No hay un cuerpo sólido sobre el que trabajar. |

### `restricciones/boceto.py` (95)

| Línea | Largo | Texto |
|---|---|---|
| 382 | 122 | La cota de {} no puede pasar de {} mm (1 km; vale {} mm): más grande, el núcleo geométrico ya no … |
| 3726 | 112 | Con {} mm hacia ese lado, un segmento de la cadena queda con largo cero o al revés: usá una dista… |
| 4248 | 106 | Lo elegido ya está sobre la línea de simetría (o es simétrico respecto de ella): no hay nada que … |
| 1777 | 98 | El barrido de la ranura de arco es cero: el tercer punto está en la dirección del extremo inicial. |
| 4147 | 94 | Hay geometría fija (o proyectada) en la selección que no está en la base: no se puede escalar. |
| 372 | 85 | La cota de ángulo tiene que estar entre 0 y 180 grados, sin incluirlos (vale {}). |
| 123 | 84 | El ángulo de barrido del arco tiene que estar entre 0 y 360 grados (sin incluirlos). |
| 3810 | 84 | El desfase es mayor que el radio de curvatura de la curva: se pliega sobre sí mismo. |
| 4382 | 82 | La distancia en la dirección {} es 0: las copias quedarían una encima de otra. |
| 214 | 80 | El radio interior de la estrella tiene que ser positivo y menor que el exterior. |
| 3654 | 79 | El desfase funciona con cadenas de líneas y arcos, círculos, elipses y splines. |
| 4782 | 79 | Ese texto no tiene marco: agregalo (frame) para girar alrededor de una esquina. |
| 2206 | 78 | La restricción «{}» no se puede cambiar por «{}» sobre esas entidades. |
| 2298 | 78 | Centro o tangente solo vale en una cota de distancia con un círculo o un arco. |
| 1730 | 77 | El camino del texto tiene que ser una curva del boceto (no un texto): {}. |
| 3173 | 77 | Alargar funciona con líneas, arcos circulares o elípticos y splines abiertas. |
| 2255 | 77 | El modo tangente solo vale en una cota de distancia con un círculo o un arco. |
| 2307 | 75 | El origen y los ejes del boceto son referencias fijas: no se pueden borrar. |
| 2839 | 75 | La curvatura se aplica a dos curvas encadenadas (que compartan un extremo). |
| 1527 | 74 | La capitalización es ninguno, mayusculas, minusculas, titulo o versalitas. |
| 4374 | 73 | El patrón necesita al menos dos ejemplares (cantidad 1 × cantidad 2 ≥ 2). |
| 4126 | 71 | Hay geometría fija (o proyectada) en la selección: no se puede espejar. |
| 4615 | 71 | Las manijas se activan en una spline de ajuste abierta: abrila primero. |
| 1772 | 70 | El tercer punto de la ranura de arco no puede coincidir con el centro. |
| 3881 | 69 | Seleccioná la geometría a copiar (el origen y los ejes no se copian). |
| 3959 | 69 | Hay geometría fija (o proyectada) en la selección: no se puede mover. |
| 4364 | 68 | {} tiene que ser un entero de {} en adelante (llegó {}). |
| 4378 | 67 | La distancia es la total (extensión) o la de cada paso (espaciado). |
| 257 | 65 | El redondeo de {} ({} mm) no entra en la estrella: {} |
| 3066 | 64 | La geometría proyectada no se modifica (es una referencia fija). |
| 3778 | 64 | Ninguna distancia de desfase conserva la topología de esa curva. |
| 4805 | 64 | No se pudo generar la geometría del texto (¿fuente disponible?). |
| 3269 | 64 | El vértice debe unir dos curvas abiertas con extremos distintos. |
| 354 | 62 | La espiral admite hasta {} vueltas (200 puntos de ajuste). |
| 4685 | 62 | El punto nuevo tiene que caer entre los extremos de la spline. |
| 379 | 61 | La cota de {} tiene que ser mayor que cero (vale {}). |
| 3400 | 61 | Las líneas son colineales: no hay separación para un empalme. |
| 4318 | 61 | La dirección del patrón no puede ser una línea de largo cero. |
| 4617 | 61 | El punto {} no es un punto de ajuste de la spline {}. |
| 3134 | 61 | Para partir una curva cerrada hacen falta dos intersecciones. |
| 2453 | 61 | La curva {} está bloqueada: desbloqueala antes de {}. |
| 3064 | 60 | Un texto no se puede recortar ni partir: desglosalo primero. |
| 3406 | 60 | Elegí el mismo lado a conservar en las dos líneas paralelas. |
| 1525 | 59 | El grosor del subrayado y el tachado no puede ser negativo. |
| 1595 | 59 | Las coordenadas de un punto tienen que ser números finitos. |
| 3634 | 58 | La distancia de desfase es cero: no hay nada que desfasar. |
| 2835 | 58 | La igualdad necesita dos segmentos con extremos distintos. |
| 4401 | 58 | El ángulo total va de -360 a 360 grados, distinto de cero. |
| 1880 | 57 | Ubicá el círculo dentro del ángulo que forman las líneas. |
| 4389 | 57 | La dirección {} del patrón no puede tener largo cero. |
| 348 | 56 | La espiral necesita coordenadas, vueltas y paso finitos. |
| 1538 | 56 | Los ajustes de kerning son pares [posición desde 0, mm]. |
| 1688 | 56 | Los puntos de la spline coinciden: no definen una curva. |
| 2791 | 56 | Las líneas del polígono deben formar una cadena cerrada. |
| 4869 | 56 | Hay identificadores de objetos repetidos en el proyecto. |
| 2786 | 56 | Las líneas del polígono deben formar una cadena cerrada. |
| 3198 | 56 | La spline no tiene una tangente definida en ese extremo. |
| 152 | 55 | Los tres puntos están alineados: no definen un círculo. |
| 2867 | 55 | Una cota de distancia necesita dos entidades distintas. |
| 3178 | 54 | El extremo es fijo: quitale «Fijo» antes de alargarlo. |
| 3262 | 54 | El vértice debe ser extremo de exactamente dos curvas. |
| 4787 | 54 | Esquina desconocida: {} (bl, br, tl, tr o center). |
| 1807 | 53 | El ancho de la ranura es mayor que el radio del arco. |
| 2251 | 53 | Modo de cota desconocido: {} (centro o tangente). |
| 4724 | 53 | El grado de una spline de puntos de control es 3 o 5. |
| 2296 | 53 | Modo de cota desconocido: {} (centro o tangente). |
| 4368 | 53 | {} tiene que ser un número finito (llegó {}). |
| 352 | 52 | La espiral necesita al menos una fracción de vuelta. |
| 1647 | 52 | Los tres puntos están alineados: no definen un arco. |
| 1704 | 52 | El vértice no puede estar alineado con los extremos. |
| 3213 | 52 | No hay ninguna curva para alcanzar en esa dirección. |
| 3387 | 52 | El empalme necesita dos líneas de longitud positiva. |
| 1764 | 52 | Los tres puntos están alineados: no definen un arco. |
| 2241 | 52 | Las líneas no son paralelas. Usá una cota de ángulo. |
| 2286 | 52 | Solo una cota de radio pasa a diámetro (o al revés). |
| 1510 | 51 | El anclaje vertical es base, arriba, medio o abajo. |
| 1514 | 51 | La colocación del texto en curva es arriba o abajo. |
| 3481 | 51 | No entra un empalme de ese radio entre esas curvas. |
| 4763 | 51 | El marco del texto necesita ancho y alto positivos. |
| 4561 | 51 | La curva de fusión une extremos de curvas abiertas. |
| 3529 | 50 | La distancia es demasiado grande para esas líneas. |
| 3143 | 50 | La curva no cruza con nada: no hay dónde partirla. |
| 2865 | 49 | Una cota de ángulo necesita dos líneas distintas. |
| 3443 | 49 | El empalme funciona con líneas, arcos y círculos. |
| 4670 | 49 | Una spline cerrada necesita al menos tres puntos. |
| 3281 | 48 | Las líneas son paralelas: no forman una esquina. |
| 4664 | 48 | Desactivá las manijas antes de cerrar la spline. |
| 1622 | 47 | El rectángulo no puede tener ancho o alto cero. |
| 3632 | 47 | La distancia de desfase no es un número válido. |
| 3860 | 47 | La entidad {} no forma parte de un desfase. |
| 4219 | 47 | La línea de simetría no puede tener largo cero. |
| 3188 | 47 | No se puede alargar una línea de longitud cero. |
| 3583 | 47 | La distancia de desfase no es un número válido. |
| 1877 | 46 | No hay un círculo tangente a esas tres líneas. |
| 3363 | 46 | El radio es demasiado grande para esas líneas. |

### `ui/comandos/crear.py` (9)

| Línea | Largo | Texto |
|---|---|---|
| 283 | 85 | «{}»: escribí n.º:ángulo:peso, con el n.º entre 2 y {} (hay {} perfiles). |
| 1182 | 77 | Escribí las operaciones a repetir (nombres del timeline, separados por coma). |
| 1275 | 72 | En «Copias suprimidas» van {} separados por coma; «{}» no sirve. |
| 1202 | 70 | Escribí los componentes a repetir (nombres o ids, separados por coma). |
| 1744 | 61 | Escribí el id del paso del sistema de coordenadas de usuario. |
| 806 | 61 | Elegí la cara, el plano o el cuerpo donde termina el agujero. |
| 272 | 57 | Seleccioná la cara a la que es tangente el {} perfil. |
| 1277 | 55 | El original no se puede suprimir (es el cuerpo fuente). |
| 1175 | 53 | No hay un paso «{}» antes de este en el timeline. |

### `ui/comandos/modificar.py` (12)

| Línea | Largo | Texto |
|---|---|---|
| 620 | 86 | La distancia de desfase no puede ser cero: arrastrá la flecha o escribí una distancia. |
| 727 | 86 | La distancia de desfase no puede ser cero: arrastrá la flecha o escribí una distancia. |
| 653 | 81 | La distancia o el radio no puede ser cero: arrastrá la flecha o escribí un valor. |
| 725 | 80 | Elegí solo caras (desfase de cara) o solo aristas y curvas (desfase de aristas). |
| 928 | 77 | La traslación no puede ser cero: arrastrá una flecha o escribí una distancia. |
| 1048 | 75 | «Desde» no es de un cuerpo: elegí los cuerpos a alinear en «Otros cuerpos». |
| 534 | 73 | Cada barra son 6 números de 0 a 1 (x1 y1 z1 x2 y2 z2), separadas con «;». |
| 932 | 71 | Indicá una distancia o un ángulo distinto de cero para mover el objeto. |
| 1280 | 69 | Elegí al menos un tipo de operación (empalmes, chaflanes o agujeros). |
| 151 | 69 | La posición de un punto intermedio está entre 0 y 1 (sin incluirlos). |
| 148 | 60 | Cada punto es posición:radio (p. ej. 0.5:3 mm), no «{}». |
| 1078 | 54 | El cuerpo de destino no puede ser también herramienta. |

### `ui/comandos/solido.py` (6)

| Línea | Largo | Texto |
|---|---|---|
| 187 | 88 | La distancia de extrusión no puede ser cero: arrastrá la flecha o escribí una distancia. |
| 190 | 86 | La distancia del lado 2 no puede ser cero: arrastrá su flecha o escribí una distancia. |
| 182 | 61 | Las curvas abiertas solo se extruyen con «Extrusión delgada». |
| 194 | 60 | Elegí el objeto hasta donde llega el lado 2 de la extrusión. |
| 501 | 58 | Seleccioná el eje de revolución (una línea, arista o eje). |
| 192 | 47 | Elegí el objeto hasta donde llega la extrusión. |

### `ui/comandos/primitivas.py` (2)

| Línea | Largo | Texto |
|---|---|---|
| 195 | 69 | El diámetro del toroide tiene que ser menor que el diámetro interior. |
| 119 | 54 | Elegí un plano, una cara plana, un punto o un vértice. |

### `ui/comandos/patrones.py` (2)

| Línea | Largo | Texto |
|---|---|---|
| 172 | 120 | Falta completar la transformación {} ({}): elegí {}. Mientras tanto no hay vista previa ni se pue… |
| 163 | 61 | Una multitransformación admite hasta {} transformaciones. |

Total pendiente: 368.

## Pendiente fuera del alcance de esta entrega

| Dónde | Hoy | Versión corta propuesta |
|---|---|---|
| `nucleo/vectores.py:105` (B-517, en main; este worktree todavía no lo tiene) | «El desfase de -0.5 mm no se pudo calcular (¿la región desaparece?).» | «−0,5 mm se come el trazo: probá con menos» (se acorta al integrar, para no pisar a B-517) |
| `nucleo/superficies.py:1380` (caso de Gerardo; E10 trabaja ahí con H-91) | «Una solevación cerrada no tiene perfiles extremos: no admite condiciones de borde, y OpenCascade no la arma con línea central. Con rieles sí se puede.» | «Solevación cerrada: sin condiciones de borde ni línea central.» (Superficie, próxima entrega) |

Los números de línea de «Hecho» son los de `bd8d4430`. ⚠ Aviso: algunos textos ya empiezan con «⚠ »; `poner_mensaje` pone su propio símbolo, así que podría verse doble. Sin verificar en pantalla: queda anotado, no se tocó.
