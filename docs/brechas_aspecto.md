# Aspecto, materiales y colores: Fusion contra OmniCAD

Especificación. El estado vive solo en `docs/seguimiento/`.

**Fuentes:** ayuda oficial en `docs/fusion_docs/` (`fusion-model`: «Apply appearances to components, bodies, and faces»,
«Physical materials and appearances», «Apply physical materials…», «Manage materials», «Selection in Fusion», «Color code
components»; `fusion-render`: «Modify the appearance of the design», «Edit appearances using the Material Editor»;
`fusion-drawing`: «Drawing views»). El video de Gerardo del 2026-11-05, su registro de uso y lo que aclaró después. Prueba
por API y en la ventana real (arnés `scripts/prueba_ui/`, minimizada) el 2026-11-05.

## Lo que pasó en el video

Placa «abanico standar» con «@dibbujando» en relieve: las letras d, i, u, j, o están unidas a la placa (son caras del
mismo cuerpo); @, bb y «and» son cuerpos sueltos. Gerardo quería pintar las caras de las letras y después la placa entera.

| Qué vio | Causa | Arreglo |
|---|---|---|
| En «Caras», algunas caras elegidas no se pintaron | Hace doble clic. Qt manda el segundo clic como otro clic: la cara se elegía y se soltaba (11 pares en el registro, seq 640–767) | B-200: el segundo clic de un doble clic no suelta nada |
| En «Cuerpos», la placa no quedó entera del color | Las caras pintadas antes tapaban al cuerpo | H-73: «Cuerpos» pinta el cuerpo ENTERO, también sus caras pintadas (regla pedida por Gerardo) |
| ~30 clics para cinco letras | Con un comando abierto no andaban la ventana, la forma libre ni la pintura | H-72: una ventana elige todas las caras de las letras (27 caras de 5 letras) |
| El primer intento se trabó | Las caras elegidas antes de abrir quedaban escondidas en «Cuerpos» | B-198 |
| No se sabía qué color se usó | El registro guardaba `"aspecto": null` | B-199 |

Se descartó: que las caras de letras de texto se pierdan al recalcular. Pintadas de a una, 286 de 286 caras de
«@dibbujando» resuelven a caras distintas, también al guardar y reabrir (`evidencias/color_materiales_2026-11-05/caras_texto.py`).

## Tabla Fusion contra OmniCAD

| Opción de Fusion | Comportamiento en Fusion | OmniCAD | Estado |
|---|---|---|---|
| Aplicar a: Cuerpos/componentes · Caras | Radio arriba del diálogo | Igual | Hecho |
| Aplicar a: Todos los guiones · Guion actual | Solo en ANIMACIÓN | No | ANI-3 |
| En este diseño | Los aspectos que usa el diseño | Igual, con miniaturas | Hecho |
| Menú de En este diseño: Editar, Duplicar, Suprimir, Añadir a Favoritos, Copiar en Mis aspectos | Clic derecho | Igual | Hecho |
| «Unassign and Delete» | Saca el aspecto de todos y lo borra | Solo por API (`manage_appearance` con `remove_users`); en el menú Suprimir queda gris si se usa | H-74 |
| Biblioteca: Aspectos de Fusion, Mis aspectos, Favoritos, buscador | Pestañas y familias | Igual | Hecho |
| «Show downloadable materials» | Muestra los que se bajan | No aplica (todo local) | No aplica |
| **Arrastrar la muestra** a un cuerpo, cara o componente en la vista o el navegador | Es LA forma de aplicar: cada suelta se aplica al instante | No existe: se elige el objetivo y se acepta | KS5 |
| Elegir antes y abrir después | «Preselect… to apply a new appearance to them all at once» | Igual, con cuerpos o caras | Hecho (B-198) |
| Ventana, forma libre y pintura dentro del comando | «Selection is always active» | Igual, para el campo de caras o cuerpos | Hecho (H-72) |
| Doble clic sobre una cara | La ayuda no lo dice | Elige la cara una vez | Hecho (B-200) |
| Pintar un cuerpo con caras pintadas | Al soltar sobre un componente padre pregunta si conserva o quita las anulaciones; para un cuerpo la ayuda no dice | El cuerpo queda entero (regla de Gerardo); la API conserva las caras con `clear_face_overrides=false` | Hecho (H-73) |
| Prioridad cara > cuerpo > componente > material | La anulación más específica gana | Igual | Hecho |
| Editor de materiales (Avanzado) | Propiedades por tipo, texturas, Aplicar/Aceptar | Igual en lo básico; el render ignora parte | KS3 |
| Números del selector rápido y del Editor | — | Aceptan «0.25» y «0,25» tecleando | Hecho (B-202) |
| Ajustar la proyección de la textura | Herramienta Texture Map Controls | No | Sin fila (pedir si hace falta) |
| Aspecto por defecto (Preferencias › Material) y soltar en el componente raíz | Cambia el de los objetos nuevos | No | CF-7 |
| Material físico: En este diseño, biblioteca, arrastrar | Igual que Aspecto, sin caras | Lista desplegable con densidad; masa y color andan | SUP-30, CF-10 |
| Administrar materiales (Material Browser) | Bibliotecas, crear, duplicar, propiedades | Botón gris; por API `define_material` y `delete_material` | P-25d, CF-10 |
| Masa con el material | Propiedades físicas | `get_physical_properties` y la lista de materiales | Hecho |
| Mostrar colores de componente (Mayús+N) y Color del componente de ciclo | Canvas, navegador y timeline | Igual (`cycle_component_color`) | Hecho |
| Guardar, reabrir, deshacer y rehacer | — | Aspectos del diseño y caras pintadas viajan en el `.omnicad`; cada Aceptar es un paso | Hecho |
| Render (lienzo y CPU) | Usa los aspectos | Cuerpos y caras pintadas con su color y acabado | Hecho |
| DIBUJO: vistas sombreadas | Estilos Sombreado y Sombreado con aristas | No hay vistas sombreadas | CF-2 |
| Exportar glTF con color | — | Cuerpos y caras pintadas, cada una con su material | Hecho (B-201) |
| Exportar 3MF con color | Impresión multicolor | 3MF sin color | P-27-11 |
| Exportar STEP y OBJ con color | — | Sin color | H-76 |
| Cómo se ve un negro | Ilumina con el entorno: un negro brillante muestra reflejos (inferido, la ayuda no lo dice) | Negro plano: arriba y costados del mismo negro | H-75 |

## Herramientas de la API

`set_appearance` (cuerpos o caras, aspecto o color; `clear_face_overrides`), `edit_appearance`, `manage_appearance`,
`list_appearances`, `set_material`, `define_material`, `delete_material`, `list_materials`, `get_physical_properties`,
`get_bill_of_materials`, `cycle_component_color`, `export` (glTF con color) y `render_image`. Probadas el 2026-11-05:
guardar y reabrir conserva todo, deshacer vuelve un paso, el render dibuja las caras pintadas.
