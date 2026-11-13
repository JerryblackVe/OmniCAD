# ViewCube: zona → qué hace

Comportamiento tomado de Fusion (ayuda oficial `fusion-getstarted` › «ViewCube reference» y los dos videos de
`evidencias/reportes_pc/2026-11-12_viewcube/`, vistos cuadro a cuadro). El diseño visual es el de OmniCAD (gris claro mate,
biseles, cian al pasar el cursor, tema oscuro); el comportamiento es el de Fusion. Código: `clon/omnicad/ui/superposiciones.py`
› `ViewCube`; cámara en `ui/visor3d.py` (`vista`, `vista_direccion`, `poner_rotacion`, `vista_inicio`).

Tomamos el eje Z hacia arriba; «ojo» es de dónde mira la cámara.

| Zona | Qué hace | Resaltado al pasar el cursor |
|---|---|---|
| **6 caras** (centro de la cara) | Vista estándar de esa cara, con Z arriba (arriba: X a la derecha, Y arriba). Si se eligió otra vista para esa cara (menú), usa esa. Cámara con caras ortográficas si la preferencia lo pide. | El cuadrado central, en cian |
| **12 aristas** (franja entre dos caras) | Vista a 45° con el ojo en la diagonal de las dos caras (p. ej. frente-derecha: ojo en (1, −1, 0)), con Z arriba. | La franja completa, sobre las dos caras, con halo cian |
| **8 vértices** (rincón de tres caras) | Vista isométrica de esa esquina (ojo en (±1, ±1, ±1)). La esquina frente-derecha-arriba es la vista Inicio de fábrica. | El rincón, en cian |
| **Arrastre** (botón izquierdo sobre el cubo) | Orbita la escena como el resto del visor (libre o restringida, según la órbita elegida). No dispara ninguna zona. | — |
| **◁ (borde derecho)** | Solo en una vista de cara. Gira 90° y trae al frente la cara de la derecha. Conserva el zoom y el giro de la pantalla (puede dejar texto dado vuelta, como Fusion). | Triángulo cian |
| **▷ (borde izquierdo)** | Trae al frente la cara de la izquierda. | idem |
| **▽ (borde de arriba)** | Trae al frente la cara de arriba (el ojo sube 90°). | idem |
| **△ (borde de abajo)** | Trae al frente la cara de abajo. | idem |
| **Flecha curva de arriba (↶)** | Solo en una vista de cara. Gira la escena 90° contra el reloj sobre el eje de la pantalla; el ojo no cambia. | Flecha cian |
| **Flecha curva de la derecha (↷)** | Gira la escena 90° con el reloj. | idem |
| **Casita (arriba a la izquierda)** | Vuelve a la vista Inicio: la isométrica de fábrica, o la que se eligió en el menú (ajustada a la escena o a distancia fija). | Fondo cian |
| **▽ doble (abajo a la derecha)** y **clic derecho** | Abre el menú del ViewCube (abajo). | ▽ cian |
| **Ejes X, Y, Z** | Líneas rojas, verdes y azules desde la esquina (−1, −1, −1) del cubo, con su letra afuera; giran con el cubo. Las que corren por detrás se ven solo donde sobresalen. | — |

## Menú del ViewCube (clic derecho o ▽)

| Opción | Qué hace |
|---|---|
| Ir al inicio | Igual que la casita |
| Cámara › Ortográfica / Perspectiva / Perspectiva con caras ortográficas | Cambia la proyección (la misma opción de la barra de navegación) |
| Establecer la vista actual como Inicio › Ajustar a la vista / Distancia fija | Guarda la cámara actual como Inicio. «Ajustar» encuadra la escena al volver; «Distancia fija» vuelve al mismo objetivo y zoom. Se guarda en el documento |
| Restablecer Inicio | Vuelve al Inicio de fábrica (activo solo si se eligió otro) |
| Establecer la vista actual como [Cara] | Mirando de frente una cara, esa pasa a ser la vista de la cara (p. ej. con el giro de la pantalla que tiene ahora). El nombre cambia con la cara; grisada si no se mira una |
| Restablecer [Cara] | Devuelve la cara a su vista de fábrica |
| Tamaño de ViewCube › Automático / Grande / Normal / Pequeño / Diminuto | Cambia el tamaño (preferencia `general/tamano_viewcube`) |

## Animación

Cada cambio de vista pedido con el cubo se anima ~250 ms (preferencia «Animar las transiciones de vista»); sin ella,
salta. El arrastre y la rueda cortan la animación donde está.

## API y MCP

| Herramienta | Cubre |
|---|---|
| `set_view` (`view`, `direction`, `roll`) | Las 26 vistas (`direction` con aristas y vértices, p. ej. [1, −1, 0]) y los giros de las flechas curvas (`roll`: 90 = ↶) |
| `set_home_view` (`view`, `direction`, `roll`, `mode`, `face`, `reset`) | «Establecer / Restablecer» el Inicio o la vista de una cara |

Los triángulos son giros de 90° del marco de la cámara: se piden con `set_view` y `direction` de la cara vecina.
