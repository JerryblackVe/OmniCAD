# Auditoría de mensajes de los paneles (P-158)

Regla 14 de `CLAUDE.md`: el mensaje de un panel es **1 renglón**, con ícono (⚠ o ✖) y una palabra clave; el detalle va a la ayuda. Límite medido: **45 caracteres** (el panel «simple» mide 320 px; con la fuente por defecto entran unos 44). Un valor `{}` cuenta como 6 caracteres. El test `tests/test_p158_mensajes_cortos.py` falla si un archivo del alcance suma un mensaje que pasa del límite (trinquete: el tope por archivo solo baja).

Alcance de la entrega 1: Bocetos y Sólido (`nucleo/solidos_crear.py`, `nucleo/solidos_modificar.py`, `timeline/ops_solido.py`, `restricciones/boceto.py`, `ui/comandos/{crear,modificar,solido,primitivas,patrones}.py`, `ui/manipuladores.py`). **Entrega 2 (2026-11-15): Superficie** (`nucleo/superficies.py`, `timeline/ops_superficie.py`, `ui/comandos/superficie.py`): 102 mensajes acortados a 45 caracteres o menos; ya están en el test con tope 0 (el antes→después está en la tabla «Hecho en la entrega 2»). El resto (Malla, Chapa, Ensamblar, Inspeccionar…) va en la próxima entrega. No entran todavía los textos de `Info(...)` ni los que arman las clases de los paneles (`ui/comando.py`).

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
| `nucleo/solidos_modificar.py:1714` | Desfase de caras: el filete helicoidal de una rosca modelada no se puede desfasar (el kernel tarda minutos y falla). … | Una rosca no se desfasa: usá Holgura de impresión al editar la rosca. |
| `nucleo/solidos_modificar.py:1721` | Desfase de caras: en un cuerpo con una rosca modelada, el kernel tarda minutos y falla con las caras curvas. Desfasá … | Una rosca no se desfasa: usá Holgura de impresión al editar la rosca. |
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

Ninguno en Bocetos y Sólido: P-158d y P-158f los acortaron y `tests/test_p158_mensajes_cortos.py` (topes en 0) lo comprueba.

## Hecho en la entrega 2: Superficie (antes → después)

Los números de línea son los de `main` al empezar la entrega (70643f37).

| Dónde | Antes | Después |
|---|---|---|
| `superficies.py:100` | El kernel no devolvió ninguna forma con estos valores. | El kernel no devolvió ninguna forma. |
| `superficies.py:212` | No se pudieron encadenar las aristas en un alambre. | No se pudo armar un alambre con las aristas. |
| `superficies.py:222` | {} tiene que ser una sola cadena de aristas conectadas (hay {}). | {que}: una sola cadena (hay {len(ws)}). |
| `superficies.py:349` | No se pudo crear la extrusión de superficie con conicidad con estas curvas: probá con conicidad 0. | Conicidad imposible acá: probá con 0. |
| `superficies.py:374` | La conicidad tiene que estar entre -89° y 89°. | Conicidad: entre -89° y 89°. |
| `superficies.py:396` | La extensión «A objeto» no se combina con la dirección simétrica. | «A objeto» no va con dirección simétrica. |
| `superficies.py:407` | El objeto está del otro lado de las curvas: invertí la distancia o elegí otro. | Objeto del otro lado: invertí la distancia. |
| `superficies.py:412` | La extrusión no llega al objeto elegido: no lo corta. | La extrusión no llega al objeto. |
| `superficies.py:445` | La curva es paralela a la dirección de extrusión: no se puede extruir. | La curva es paralela a la extrusión. |
| `superficies.py:475` | El cuerpo ya toca el perfil: elegí uno que esté a un ángulo. | El cuerpo ya toca el perfil: elegí otro. |
| `superficies.py:492` | «A objeto» gira hasta el objeto de cada lado: usá «Un lado» o «Dos lados». | «A objeto»: usá «Un lado» o «Dos lados». |
| `superficies.py:496` | Elegí el objeto hasta donde gira el perfil en el lado 2. | Elegí el objeto del lado 2. |
| `superficies.py:501` | Los dos lados juntos pasan de una vuelta (360°): elegí objetos que no se crucen. | Los dos lados pasan de 360°. |
| `superficies.py:507` | El ángulo de revolución no puede pasar de 360° (en total): más de una vuelta se pisa a sí misma. | El ángulo no puede pasar de 360°. |
| `superficies.py:520` | No se pudo girar el perfil alrededor del eje: el perfil tiene que quedar de un solo lado del eje, sin cruzarlo ni apoyarse sobr… | El perfil debe quedar de un lado del eje. |
| `superficies.py:628` | El riel guía no acompaña a la ruta: no se pudo cortar el barrido en un plano perpendicular a la ruta. Probá con «Extensión comp… | El riel no sigue la ruta: probá «Completa». |
| `superficies.py:646` | La ruta tiene que estar sobre la superficie guía: cada arista de la ruta, apoyada en una de sus caras. | La ruta debe apoyarse en la superficie guía. |
| `superficies.py:679` | El riel guía toca la ruta: con «Estirar» tiene que ir separado de ella. | «Estirar»: el riel no puede tocar la ruta. |
| `superficies.py:695` | No se pudo estirar el perfil entre la ruta y el riel: probá con «Escalar». | No se pudo estirar: probá «Escalar». |
| `superficies.py:725` | La torsión del barrido de superficie admite como máximo ±{}° ({} vueltas); recibió {}°. | Torsión máx. ±{TORSION_MAXIMA_SUPERFICIE:g}° (pediste {torsion:g}°). |
| `superficies.py:729` | La torsión solo existe con orientación perpendicular. | La torsión pide orientación perpendicular. |
| `superficies.py:731` | La conicidad del barrido tiene que estar entre -89° y 89°; recibió {}°. | Conicidad entre -89° y 89° (pediste {conicidad:g}°). |
| `superficies.py:733` | La conicidad solo existe con orientación perpendicular. | La conicidad pide orientación perpendicular. |
| `superficies.py:736` | La distancia del barrido sobre la ruta va de 0 (sin incluir) a 1; recibió {}. | Distancia: más de 0 hasta 1 (pediste {valor:g}). |
| `superficies.py:738` | Elegí un riel guía o una superficie guía, no los dos. | Riel o superficie guía, no los dos. |
| `superficies.py:741` | La torsión y la conicidad son del tipo «Ruta individual»: no se combinan con un riel ni con una superficie guía. | Torsión y conicidad no van con riel ni guía. |
| `superficies.py:777` | Con esa conicidad el perfil desaparece antes del final de la ruta: probá con un ángulo menor. | Con esa conicidad el perfil desaparece. |
| `superficies.py:864` | La superficie de la cara no se prolonga hasta donde pide la condición Suave. | La cara no se prolonga para «Suave». |
| `superficies.py:928` | La alineación de bordes es de los perfiles abiertos: uno cerrado no tiene extremos. | Solo los perfiles abiertos se alinean. |
| `superficies.py:987` | El peso de la condición de borde tiene que ser positivo. | El peso debe ser positivo. |
| `superficies.py:1014` | La cúpula del punto tangente no cerró un sólido: el perfil tiene que ser cerrado. | Perfil cerrado necesario para la cúpula. |
| `superficies.py:1025` | El peso de la condición de borde tiene que ser positivo. | El peso debe ser positivo. |
| `superficies.py:1032` | La condición «Punto tangente» es de un perfil que es un punto, junto a un contorno. | «Punto tangente» pide punto y contorno. |
| `superficies.py:1035` | La condición de borde necesita un perfil con contorno; un punto es agudo o tangente. | La condición pide un perfil con contorno. |
| `superficies.py:1043` | El ángulo de la condición de borde, medido desde la normal, tiene que quedar entre −90 y 90 grados. | El ángulo de borde va entre −90° y 90°. |
| `superficies.py:1057` | La condición Tangente o Suave necesita la cara a la que la superficie es tangente. | Tangente o Suave: elegí la cara vecina. |
| `superficies.py:1073` | No hay un perfil en la posición {} para la condición de borde. | No hay perfil en la posición {pos + 1}. |
| `superficies.py:1076` | Entre el primer perfil y el último solo vale la condición Dirección. | Primero a último: solo Dirección. |
| `superficies.py:1141` | Con rieles hace falta al menos un perfil que sea una curva, no solo puntos. | Con rieles falta un perfil que sea curva. |
| `superficies.py:1144` | Con rieles, los perfiles tienen que ser todos abiertos o todos cerrados. | Perfiles todos abiertos o todos cerrados. |
| `superficies.py:1146` | En una solevación cerrada los rieles tienen que ser lazos cerrados que pasen por todos los perfiles. | Los rieles deben ser lazos que cruzan todo. |
| `superficies.py:1159` | El riel {} no toca el perfil {}: un riel tiene que cruzar todos los perfiles. | El riel {j + 1} no toca el perfil {i + 1}. |
| `superficies.py:1167` | En una solevación cerrada cada riel tiene que dar la vuelta pasando por todos los perfiles. | Cada riel debe pasar por todos los perfiles. |
| `superficies.py:1208` | Los rieles se cruzan: tienen que seguir el mismo orden en todos los perfiles. | Los rieles se cruzan: mantené el orden. |
| `superficies.py:1324` | No se pudo crear la superficie con esos rieles: revisá que toquen todos los perfiles y que no se crucen entre sí. | No se pudo crear con esos rieles. |
| `superficies.py:1365` | Un punto solo puede ser la primera o la última sección de un solevado abierto. | Un punto solo va al inicio o al final. |
| `superficies.py:1374` | Un solevado cerrado necesita al menos tres secciones. | Un solevado cerrado pide 3 secciones o más. |
| `superficies.py:1385` | Las condiciones de borde, los rieles y la línea central no se combinan con tramos rectos. | Tramos rectos: sin rieles ni condiciones. |
| `superficies.py:1387` | Una solevación cerrada no tiene perfiles extremos: no admite condiciones de borde, y OpenCascade no la arma con línea central. … | Cerrada: sin condiciones ni línea central. |
| `superficies.py:1409` | No se pudo crear la superficie entre las secciones: revisá que estén en el orden en que se recorren, que no se crucen y que ten… | No se pudo crear: revisá orden y forma. |
| `superficies.py:1420` | No se pudo construir el parche con continuidad {}: el kernel no encuentra una superficie que cumpla esa continuidad con las car… | Parche {que}: no se pudo armar. |
| `superficies.py:1439` | Continuidad desconocida: {} (G0, G1 o G2). | Continuidad desconocida: {c} (G0, G1, G2). |
| `superficies.py:1441` | Tangente (G1) y curvatura (G2) necesitan aristas de un cuerpo con caras vecinas: elegí las aristas del contorno sobre el cuerpo… | G1 y G2 piden aristas de un cuerpo. |
| `superficies.py:1445` | El contorno no es cerrado: el parche tapa un contorno cerrado (uní los extremos o elegí las aristas que lo cierran). | El contorno debe ser cerrado. |
| `superficies.py:1464` | ? | {cont}: falta la cara vecina de una arista. |
| `superficies.py:1540` | ? | Ingletes: usá una distancia menor. |
| `superficies.py:1549` | ? | Ingletes: usá una distancia menor. |
| `superficies.py:1608` | ? | Tipo reglado desconocido: {tipo} |
| `superficies.py:1610` | ? | La distancia no puede ser cero. |
| `superficies.py:1628` | ? | Normal/tangente: indicá la referencia. |
| `superficies.py:1694` | ? | Reglada inválida: cambiá distancia o ángulo. |
| `superficies.py:1699` | ? | La reglada se cruza: reducí la distancia. |
| `superficies.py:1702` | ? | No se pudo comprobar: menos aristas. |
| `superficies.py:1774` | ? | Desfase: la distancia no entra. |
| `superficies.py:1780` | ? | Desfase de {abs(distancia):g} mm: se cruza sola. |
| `superficies.py:1803` | ? | Para el {sustantivo}: arista de dos caras. |
| `superficies.py:1816` | La arista es libre (la toca una sola cara): el {} necesita una arista compartida por dos caras. | El {sustantivo} falló: ¿{parametro} muy grande? |
| `superficies.py:1851` | ? | No se pudo partir la superficie. |
| `superficies.py:1943` | ? | La distancia no puede ser negativa. |
| `superficies.py:1953` | ? | Modo manual: elegí las aristas a destrimar. |
| `superficies.py:1961` | ? | Ninguna arista elegida es borde de la cara. |
| `superficies.py:2041` | ? | No se pudo prolongar la superficie. |
| `superficies.py:2089` | ? | No se pudo extender: probá menos distancia. |
| `superficies.py:2106` | ? | Alineación desconocida: {alineacion}. |
| `superficies.py:2123` | ? | Solo se extienden aristas libres. |
| `superficies.py:2137` | ? | La cara no se extiende en forma natural. |
| `superficies.py:2162` | ? | La extensión pasa de una vuelta. |
| `superficies.py:2180` | ? | No se pudo extender: probá otra extensión. |
| `superficies.py:2190` | ? | Tolerancia: mayor que 0 mm (pediste {tolerancia:g}). |
| `superficies.py:2214` | ? | Sin caras tras coser: menos tolerancia. |
| `superficies.py:2314` | ? | Invertir normal: solo superficies. |
| `superficies.py:2395` | ? | No se pudo engrosar: ¿espesor muy grande? |
| `superficies.py:2403` | ? | Espesor {abs(espesor):g} mm: probá menos. |
| `superficies.py:2409` | ? | No se pudo engrosar: probá menos espesor. |
| `ops_superficie.py:38` | Un texto solo se extruye como superficie con una fuente de una línea (p. ej. «OmniCAD Trazo SHX» o una .shx): este usa «{}». Pa… | Solo fuentes de una línea en superficie. |
| `ops_superficie.py:96` | La operación generó una superficie degenerada (sin área o inválida): revisá las curvas, la distancia y el ángulo. | Superficie degenerada: revisá las curvas. |
| `ops_superficie.py:130` | Elegí una cara plana o un plano como inicio de la extrusión. | Elegí una cara plana o un plano de inicio. |
| `ops_superficie.py:141` | Elegí la cara, el plano o el cuerpo hasta donde llega la extrusión. | Elegí hasta dónde llega la extrusión. |
| `ops_superficie.py:145` | El objeto elegido no sirve como límite de la extrusión. | Ese objeto no limita la extrusión. |
| `ops_superficie.py:181` | El objeto de la revolución tiene que ser un vértice, un plano, una cara plana o un cuerpo. | Elegí vértice, plano, cara plana o cuerpo. |
| `ops_superficie.py:272` | La condición Tangente o Suave necesita un perfil que sea el borde de una cara, o elegir esa cara. | Tangente o Suave: elegí el borde de una cara. |
| `ops_superficie.py:409` | En el modo manual elegí las aristas a destrimar. | Modo manual: elegí las aristas a destrimar. |
| `ops_superficie.py:414` | Destrimar solo se aplica a cuerpos de superficie: «{}» no es una superficie. | Destrimar: «{c.nombre}» no es superficie. |
| `ops_superficie.py:446` | Extender solo se aplica a cuerpos de superficie: «{}» no es una superficie. | Extender: «{c.nombre}» no es superficie. |
| `superficie.py:73` | Elegí el objeto hasta donde llega la extrusión. | Elegí hasta dónde llega la extrusión. |
| `superficie.py:75` | Elegí la cara plana o el plano donde empieza la extrusión. | Elegí la cara o el plano de inicio. |
| `superficie.py:80` | La distancia de extrusión no puede ser cero: arrastrá la flecha o escribí una distancia. | La distancia no puede ser cero. |
| `superficie.py:82` | La distancia del lado 2 no puede ser cero: arrastrá su flecha o escribí una distancia. | La distancia del lado 2 no puede ser cero. |
| `superficie.py:129` | Elegí el objeto hasta donde gira el perfil en el lado 2. | Elegí el objeto del lado 2. |
| `superficie.py:257` | La continuidad de cada arista es G0, G1 o G2; «{}» no vale. | Continuidad G0, G1 o G2; «{malas[0]}» no vale. |
| `superficie.py:259` | Hay {} continuidades y solo {} aristas elegidas. | {len(partes)} continuidades y {cuantas} aristas. |
| `superficie.py:342` | La distancia de desfase no puede ser cero: arrastrá la flecha o escribí una distancia. | La distancia de desfase no puede ser cero. |

102 mensajes acortados. Después de la tabla: «El kernel no devolvió ninguna forma» pasó a «No salió ninguna forma con estos valores.», «Primero a último» a «Del primero al último: solo «Dirección».» y el parche G1/G2 conserva la pista «probá G0».

## Pendiente fuera del alcance de esta entrega

| Dónde | Hoy | Versión corta propuesta |
|---|---|---|
| `nucleo/vectores.py:105` (B-517, en main; este worktree todavía no lo tiene) | «El desfase de -0.5 mm no se pudo calcular (¿la región desaparece?).» | «−0,5 mm se come el trazo: probá con menos» (se acorta al integrar, para no pisar a B-517) |
| `nucleo/superficies.py:1380` (caso de Gerardo; E10 trabaja ahí con H-91) | «Una solevación cerrada no tiene perfiles extremos: no admite condiciones de borde, y OpenCascade no la arma con línea central. Con rieles sí se puede.» | «Solevación cerrada: sin condiciones de borde ni línea central.» (Superficie, próxima entrega) |

Los números de línea de «Hecho» son los de `bd8d4430`. ⚠ Aviso: algunos textos ya empiezan con «⚠ »; `poner_mensaje` pone su propio símbolo, así que podría verse doble. Sin verificar en pantalla: queda anotado, no se tocó.

De main (B-506, B-503): «El agujero toca justo una pared: espesor cero.» (46) y «No se pudo desfasar estas caras …» quedan como están: tests con el texto exacto; se acortan en la próxima entrega.
