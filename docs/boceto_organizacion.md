# Organización de objetos en el boceto

Cómo se organizan geometrías, textos, SVG/DXF y grupos dentro de un boceto, y cómo seguirlo. Pendientes: solo en
`docs/seguimiento/` (H-69, H-70, H-71). Pedido original: [plan_boceto_organizar.md](plan_boceto_organizar.md).

## Modelo de datos (sin Qt)

- Todo vive en `Boceto.objetos` (`clon/omnicad/restricciones/objetos.py`): `{id: {"id", "nombre", "entidades",
  "matriz", "pivote", "visible", "bloqueado", "proporciones", ...}}`. Un objeto contiene curvas u otros objetos.
  Las curvas siguen siendo la única geometría; la matriz se aplica al consultar primitivas (ver el docstring del módulo).
- No hay estructura nueva: un **grupo personalizado** es un objeto cuyas entidades son objetos y que no vino de
  un archivo ni de un texto. Los grupos no son pasos del timeline: viajan dentro del boceto.
- **Categoría** (`categoria(b, oid)`), calculada, nunca guardada:
  `vectores` si tiene `tipo_origen` (SVG, DXF); `textos` si tiene `texto_automatico`, `clase="texto"` (texto
  convertido) o una curva `Texto`; `grupos` si contiene objetos; `geometrias` el resto. Las curvas que no están en
  ningún objeto (`geometria_suelta`) también son Geometrías.
- **Unidad** (`unidades(b)`): lo que se maneja como una pieza: objetos raíz y miembros de un grupo personalizado. Un
  miembro conserva su categoría (un texto dentro de «Composición1» sigue en Textos). Lo interno de un SVG o de un
  texto no es una unidad.
- **Tres propiedades independientes**: `visible` (se dibuja), `bloqueado` (no se transforma, desagrupa, cambia de
  grupo ni borra) y `perfiles` (sus curvas forman perfiles CAD; si falta vale `True`, así los proyectos viejos no
  cambian). `curvas_sin_perfil(b)` hereda el apagado a lo que contiene; `nucleo/perfiles.detectar_boceto` saltea esas
  curvas. Ocultar no excluye de los perfiles.
- **Aislar** (`aislar` / `restaurar_aislamiento`): marca `aislado` en lo elegido y `oculto_por_aislar` en lo que
  oculta; restaurar muestra solo eso. Se guarda en el archivo. Mientras dure, la geometría suelta tampoco se ve ni se
  captura (`curvas_visibles` y `Lienzo._visible`). `aislamiento_activo` tiene caché: quien toque esas claves llama
  `invalidar(b)`.
- **Cambiar de grupo** (`mover_a_grupo`): recalcula la matriz local contra el grupo nuevo, así nada se mueve en
  pantalla; un grupo que queda vacío desaparece. La historia paramétrica de un objeto que cambia de padre queda como
  valor fijo (era relativa al padre anterior).
- **Eliminar** (`eliminar`): con contenido borra las curvas (`Boceto.eliminar`); sin contenido solo quita el
  contenedor de un grupo personalizado (= desagrupar).

## Solver, perfiles y timeline

- Las curvas de un objeto que no es texto quedan fijas para el solver (`Boceto`, puntos fijos por objeto): un objeto
  es rígido. Por eso la geometría suelta no se convierte sola en objeto (H-69).
- Los perfiles de un objeto transformado se calculan una vez en sus coordenadas locales y se les aplica la matriz
  (`detectar_boceto`, B-194): transformar no cambia cuántas regiones hay ni su área.
- Cada cambio es un paso de deshacer: en la API por `Sesion.transaccion` (`modifica=True`), en el editor por
  `Lienzo.aplicar_cambio`. El recálculo del timeline actualiza extrusiones y referencias a perfiles.

## API, MCP y CLI (grupo `vectores`)

| Herramienta | Qué hace |
|---|---|
| `get_sketch_organization` | Categorías con contadores, objetos (id, nombre, categoría, visible, bloqueado, en perfiles, padre, hijos) y curvas sueltas |
| `get_vector_objects` | Detalle de cada objeto (matriz, caja, pivote, `in_profiles`, `category`) |
| `set_vector_object` | Nombre, `visible`, `locked`, `in_profiles`, proporciones, pivote |
| `group_vector_objects` / `ungroup_vector_object` | Crear y desarmar grupos |
| `move_vector_objects_to_group` | Cambiar la pertenencia (sin grupo = a la raíz) |
| `delete_vector_objects` | Eliminar con contenido o solo el contenedor (`keep_contents`) |
| `isolate_vector_objects` | Aislar; sin objetos, restaurar |
| `transform_vector_objects` | Mover, girar, escalar y reflejar (`scale_x=-1`); acepta miembros de un grupo |
| `duplicate_vector_objects`, `select_vector_objects`, `align_vector_objects` | Ya existían; se reutilizan |

## Interfaz

- `ui/navegador.py` (`_ramas_boceto`, `actualizar_boceto`): al editar un boceto, su fila dice «— En edición» y
  muestra las cuatro categorías con contador; un grupo lista a sus miembros (clave `bg:<grupo>:<id>`). Fuera del
  boceto la rama desaparece. El buscador ahora filtra en todos los niveles.
- `ui/navegador_boceto.py`: selección sincronizada en los dos sentidos, ojo, renombrar en el lugar y los menús del
  clic derecho (objeto, grupo, curva suelta, categoría y área vacía). Las acciones que no aplican quedan grisadas con
  su motivo. Llama a las mismas funciones de `objetos.py` que la API.
- Visor del boceto: Alt+clic elige el objeto de abajo entre superpuestos (en ciclo); el clic derecho conserva su menú
  radial.

## Agregar un tipo de objeto nuevo

1. Que el importador o la herramienta cree el objeto con `objetos.crear` y una marca propia (como `tipo_origen`).
2. Sumar la regla en `categoria()` (y, si es una categoría nueva, en `CATEGORIAS` y el ícono en `_ramas_boceto`).
3. Si sus curvas no deben quedar rígidas, revisar los puntos fijos por objeto en `Boceto` (como el texto).
4. Pruebas: núcleo y API en `clon/tests/test_boceto_organizar.py`, ventana en `clon/tests/test_boceto_organizar_ui.py`.
