# Avance de la selección entre campos, contra Fusion (2026-11-12)

Pedido de Gerardo a partir de B-338: en el Extruir de Fusion el clic siguiente no siempre se suma al campo activo; pasa al campo que sigue o cambia de rol. Esta auditoría mira qué otros comandos funcionan así y qué hace OmniCAD. Solo lectura y comparación: no se tocó código. El mecanismo común lo arma E4 con B-338.

## Cómo reparte OmniCAD un clic

`ui/comando.py` › `_elegida` (línea ~1420), `_activar` (~1338) y `_siguiente_seleccion` (~1458):

- Hay UN campo `Seleccion` activo. El visor solo deja elegir lo que su `filtros` acepta (`set_filtro`); un clic de otro tipo se descarta sin aviso.
- Si el campo tiene `maximo` y se llena, el activo pasa solo al siguiente campo vacío y visible. Con `maximo=None` (varios) el campo nunca se llena: el clic siguiente se suma, y para pasar al otro campo hay que tocar su fila en el panel.
- No hay regla «este clic es de otro rol, mandalo al campo que lo acepta». El único cambio automático de campo por modo es `_revisar_selecciones_visibles` (cuando el campo activo se oculta) y, en Agujero, el cambio de Posición.

## Qué dice la ayuda de Fusion (`docs/fusion_docs/`)

La ayuda da el **orden** de los pasos y las reglas de qué se acepta (coplanar, etc.), pero **no documenta cuándo el foco salta solo** de un campo al siguiente. Una sola frase habla de eso, y va en contra del salto: en Dividir cara, «click the **Splitting Tool** field, and then select…» (hay que tocar el campo). Todo salto automático que no esté citado abajo queda «a confirmar en Fusion» (el MCP `fusion360` no está disponible en la VPS).

## Prueba en la ventana (Linux, `xvfb-run`, 2026-11-12)

Con el panel abierto y el clic simulado sobre el visor (arnés `scripts/prueba_ui/arnes.py`). «Acepta» = el filtro del campo activo deja elegir esa entidad.

| Comando | 1.er clic | Campo activo después | 2.º clic (otro rol) | Resultado |
|---|---|---|---|---|
| Extruir | cara superior | `perfiles` | cara lateral (otro plano) | acepta y la SUMA (`perfiles`=2): es B-338 |
| Revolución | perfil | `perfiles` | eje X | NO acepta, sin aviso; hay que tocar la fila «Eje» |
| Barrido | perfil | `perfiles` | curva de ruta | NO acepta, sin aviso; hay que tocar la fila «Ruta» |
| Combinar | cuerpo | `herramientas` (salta solo) | otro cuerpo | entra a herramientas |
| Dividir cuerpo | cuerpo | `herramienta` (salta solo) | plano | entra a la herramienta |
| Repujado | perfil | `perfiles` | cara de un cuerpo | acepta y la mete en **Perfiles** (`perfiles`=2, `caras`=0) |
| Simetría | cuerpo | `cuerpos` | plano YZ | NO acepta, sin aviso |
| Mover/copiar | cuerpo | `cuerpos` | eje Z | NO acepta, sin aviso |
| Cara de desfase | cara | `caras` | otra cara | se suma (como Fusion: es el mismo rol) |
| Agujero (por puntos) | cara | `colocacion` | otra cara | se suma como otro punto |

Cambios de modo (misma prueba): en Extruir y Revolución, poner la Extensión en «Hasta objeto» (y el Inicio en «Objeto») deja el foco en `perfiles`: el campo «Objeto límite» aparece pero no se activa. En Agujero, pasar la Posición a «Referencias» sí activa `ref_cara`.

## Tabla por comando

Orden de los campos de selección de OmniCAD según `campos()`; «→» es el orden en que se eligen. `=` quiere decir que OmniCAD y la ayuda coinciden en lo que se pudo comprobar.

| Comando | Campos de selección en orden (OmniCAD) | Qué dice Fusion | Qué hace OmniCAD | Diferencia |
|---|---|---|---|---|
| Extruir | Perfiles (varios) → Objeto de inicio → Objeto límite (`solido.py:34-57`) | «Extrude a solid body» p. 2: «one or more **coplanar** sketch profiles or planar faces»; «Extrude reference › Profiles»: «coplanar»; p. 4 y 6: Objeto de inicio / To Object se eligen después | Cualquier perfil o cara plana se suma a Perfiles; Objeto no se activa solo al elegir «Hasta objeto» (prueba) | **B-338** (cara de otro plano se suma en vez de ser el destino). Foco al cambiar a «Hasta objeto»: P-138 |
| Revolución | Perfil (varios) → Eje → Objeto límite (`solido.py:314-317`) | «Revolve a solid body» p. 2-3: «a coplanar sketch profile or face», luego «a linear sketch curve, edge, cylindrical face, or axis»; «Revolve reference › Profile»: «coplanar» | Perfiles y caras de otros planos se suman; el eje no se puede elegir con el campo Perfil activo (prueba) | Coplanaridad: B-339. Salto Perfil → Eje: P-138 (salto «a confirmar en Fusion») |
| Barrido | Perfil → Ruta → Rail guía → Superficie guía → Eje (`crear.py:61-74`) | «Sweep a solid body» p. 3-5: Profile, Path, Guide Rail, en ese orden | Todos con `maximo=None`: ningún campo salta solo; la ruta no se puede elegir con Perfil activo (prueba) | P-138 (salto «a confirmar en Fusion») |
| Solevación | Perfiles (lista) → Caras tangentes → Raíles / Línea central (`crear.py:166-183`) | «Loft a solid body» p. 2-6: perfiles, luego **Guide Type** y recién ahí rails o centerline | Lista de filas con + y ✕; los raíles se eligen después de elegir el tipo de guía | = |
| Agujero | Puntos/cara; o Cara → Referencia 1 → Referencia 2; Hasta (`crear.py:657-671`) | «Hole reference»: Face/Point, luego «References: select edges» | Cada referencia tiene `maximo=1` y salta sola; el cambio de Posición activa el primer campo (prueba) | = en las referencias. Con puntos, una segunda cara se suma como otro punto: a confirmar en Fusion |
| Repujado | Perfiles (varios) → Caras (varias) (`crear.py:363-364`) | «Emboss a solid body» p. 2-3: Sketch **Profiles**, y «on a solid body select the **Faces**» (dos roles) | `PERFIL` acepta `cara_plana`: la cara del cuerpo entra como perfil (prueba) | **B-340** |
| Nervio y Red | Perfil (curvas, varias) → Dirección (opc.) → Cuerpo (opc.) (`crear.py:307-324`) | «Create a rib / web» p. 2: solo «an open sketch profile»; no hay campo Cuerpo | Cuerpo y Dirección son extras de OmniCAD, ambos opcionales | Sin diferencia de avance (campo extra de OmniCAD) |
| Simetría (3D) | Objetos → Plano (`crear.py:1536`, `comunes.py:125`) | «Mirror across a plane» p. 3-4: objetos, luego «click **Mirror Plane**, then select the plane» (hay que tocar el campo) | `objetivos` varios; el plano no se elige con Objetos activo (prueba) | = según la ayuda (hay que tocar el campo); el rechazo sin aviso entra en P-138 |
| Patrón rectangular / circular / en trayectoria | Objetos → Ejes / Eje / Trayectoria (`campos_objeto`, `campos_patron`) | «Create a rectangular / circular pattern / pattern on a path»: objetos, luego eje o trayectoria, en ese orden | Igual que Simetría (campo de objetos varios) | A confirmar en Fusion si el foco salta; el rechazo sin aviso, P-138 |
| Dividir cuerpo | Cuerpo → Herramienta (`modificar.py:799-800`) | «Split a solid body» p. 2-3: Body to Split, luego Splitting Tool(s) | El cuerpo tiene `maximo=1`: salta solo a la herramienta (prueba) | = |
| Dividir cara | Caras (varias) → Herramienta (`modificar.py:768-769`) | «Divide a face» p. 2-3: «select a face… **click the Splitting Tool field**, and then select» | Caras `maximo=None`: hay que tocar la fila de la herramienta | = (la ayuda también pide tocar el campo) |
| Combinar | Cuerpo de destino → Cuerpos de herramienta (`modificar.py:1039-1040`) | «Combine solid bodies» p. 2-3: Target Body, luego Tool Bodies | Destino `maximo=1` salta solo a Herramientas (prueba) | = |
| Mover/copiar | Selección (varios) → Dirección / Eje / Origen / Destino según el tipo (`modificar.py:868-897`) | «Move/Copy reference»: seleccionar, tipo de movimiento, y por tipo Direction, eje, From/To | Selección `maximo=None`; el eje no se elige con Selección activa (prueba) | P-138 (salto «a confirmar en Fusion») |
| Cara de desfase | Caras (varias) (`modificar.py:605`) | Un solo rol | Las caras se suman | = |
| Planos y ejes de construcción | Filas `r0`…`rN` con `maximo=1`, por tipo (`construir.py:173-193`) | «Plane at angle» p. 2: arista o eje, luego ángulo; «Tangent plane» p. 3-4: cara cilíndrica o cónica, luego objeto de referencia (opcional) | Cada fila se llena y salta a la siguiente (misma regla de `maximo`); no se probó cada plano en la ventana | A confirmar en la ventana, por tipo de plano |
| Unión (Ensamblar) | Componente 1: ajuste (+ segundo) → Componente 2 → ajuste (`ensamblar.py:190-199`) | «Create a joint» p. 2-3: modo y Snap del Componente 1; «Repeat step 2» para el Componente 2 | Todos `maximo=1`: saltan solos al siguiente | = en el orden; no se probó el salto en la ventana |
| Extruir con «Inicio: Objeto» | Perfiles → Objeto de inicio (`solido.py:41`) | «Extrude reference › Start»: Object se elige tras fijar Start = Object | El campo aparece al elegir «Objeto» pero no se activa (prueba) | P-138 |

## Diferencias que se cargaron

Filas en `docs/seguimiento/`:

| ID | Dónde | Qué |
|---|---|---|
| B-339 | `bugs.md` | Revolución (y sus gemelos de perfil): la cara o el perfil de otro plano se suma; la ayuda pide «coplanar» |
| B-340 | `bugs.md` | Repujado: una cara de cuerpo entra como Perfil; en Fusion es el rol «Faces» |
| P-138 | `mejoras.md` | Avance de rol: el clic de otro rol se descarta sin aviso (eje, ruta, plano) y «Hasta objeto» / «Inicio: Objeto» no activan su campo. Mecanismo común, junto con B-338 |

## Lo que no se pudo confirmar

- Si Fusion pasa solo el foco de Perfil a Eje (Revolución) o de Perfil a Ruta (Barrido), y de Objetos al plano (Simetría): la ayuda no lo dice. Hay que mirar Fusion (túnel de la PC) antes de copiar ese salto.
- Qué hace Fusion con una cara no coplanar en Revolución: la ayuda solo dice «coplanar».
- Planos de construcción y Uniones: no se probó cada variante en la ventana.
