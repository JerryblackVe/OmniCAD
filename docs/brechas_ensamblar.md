# ENSAMBLAR: capturas de Fusion contra OmniCAD

Especificación de ASM-17 a ASM-20, y detalle de SC6 y P-25e2. El estado vive solo en `docs/seguimiento/`.

**Fuentes:** 26 capturas de `analisis/capturas_fusion (solo quedan las pendientes; ver su INDICE.md)`, los artículos de `fusion-assemble` y una prueba
por API. Se comparó el 2026-11-01.

**Límite:** no se probó en la ventana.

## Estado por herramienta

| Herramienta | Estado | Qué falta |
|---|---|---|
| Insertar componente | Existe | Pasarlo primero en el menú |
| Nuevo componente | **A medias** | ASM-18 |
| Duplicar con uniones | Existe | Comprobar en la ventana |
| Restricción de componentes | **A medias** (Alinear, Ángulo y Centro) | Tangente y la tabla de filas: ASM-17 |
| Unión · Unión conforme a obra | Casi | Pestañas y nombres: ASM-19 |
| Grupo rígido | Casi | Incluir hijos encendido: ASM-19 |
| Relación de tangente | **No existe** | ASM-17 |
| Origen de la unión | Completo | Nada |
| Uniones de animación · Vínculo · Estudio | Existen | Nombre: ASM-19 |
| Conjuntos de contacto | **No existen** | SC6 y P-25e2 |

OmniCAD suma Fijar, Anclar, Editar posición inicial, Capturar posición y Revertir posición. Se quedan.

## ASM-17 · Restricción de componentes

Ayuda: `Constraints reference`, `Assembly Constraints` y `Constrain Components`. La ayuda aclara que Tangent reemplaza a Tangent
Relationship y que se recrea con All Faces, por eso va en una sola fila.

| Fila | Control |
|---|---|
| Tipo | Alinear · Ángulo · Centro · Tangente, con tooltips de las capturas |
| Componente 1 y 2 | Geometría: selección de caras, aristas o vértices |
| Referencia de ángulo | Solo Ángulo: arista o línea como eje |
| Todas las caras | Solo Tangente, encendida en la captura |
| Tabla | Nombre · Tipo · Geometría · Desfase · Cambiar, con + y × |
| Geometría de la tabla | `Sin definir`, o el par elegido, como Cara-Arista |
| Límites de desfase | Mínimo, Máximo y Utilizar desfase como apoyo |
| Vista preliminar al pasar el cursor | Casilla |
| Resolver todas las restricciones | Casilla encendida |

Crea un paso del timeline, reduce grados de libertad y convive con uniones. Hace falta un resolvedor con las uniones ya existentes.
Tiene que decir cuándo hay un conflicto. Va con herramienta en la API.

## ASM-18 · Nuevo componente

| Fila | Control |
|---|---|
| Padre | Selección, con el nombre debajo |
| Externo | Casilla |
| Tipo de diseño | Pieza · Ensamblaje · Híbrido · PCB; solo con Externo |
| Tipo de componente | Estándar · Chapa |
| Nombre del componente | Componente1 |
| A partir de cuerpos | Casilla apagada |
| Activar | Casilla encendida |

Hoy no se puede crear un componente vacío: `create_component` exige cuerpos. Activar depende de ASM-9. Externo crea otro archivo:
decidir el alcance al programarlo.

## ASM-19 · Menú y paneles

**Menú:** Insertar componente · Nuevo componente · Duplicar con uniones · Restricción de componentes · Unión (J) · Unión conforme a obra
(Mayús+J) · Grupo rígido · Relación de tangente · Origen de la unión · Uniones de animación · Vínculo de movimiento · Estudio de
movimiento · Activar conjuntos de contactos · Activar todos los contactos.

**Nombres de movimiento:** Rígida · Revolución · Corredera · Cilíndrica · Polo-ranura · Plana · Bola.

**Unión:** pestañas Posición y Movimiento. Componente 1 y 2 plegables, con Modo de origen en tres botones y Forzar.

**Unión conforme a obra:** Componentes y Movimiento › Tipo.

**Grupo rígido:** Incluir componentes hijo encendido.

## ASM-20 · Estado de los paneles

`create_joint` y los paneles de unión tienen muchos campos sueltos. Revisar que respeten el orden de la captura y el `visible_si`.

## Conjuntos de contacto: detalle de SC6 y P-25e2

- Navegador: nodo Contacto: conjuntos, con botones.
- Comandos: Activar conjuntos de contactos · Activar todos los contactos · Desactivar contacto · Nuevo conjunto de contactos.
- Los componentes no se atraviesan al moverse. Es más lento que una unión: necesita medir rendimiento.

Su prompt viejo se borró el 2026-11-08: estos ítems los toma la auditoría de ENSAMBLAR
([auditoria_ensamblar.md](auditoria_ensamblar.md), agenda AG-5).
