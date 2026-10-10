# Ciclo de trabajo

Trabajá en vueltas cortas. Después de cada cambio, mirá el resultado: no avances a ciegas.

1. **Mirar.** `get_scene_info` (cuerpos, bocetos, parámetros) y `get_timeline` (pasos y su estado).
2. **Hacer.** Un cambio por vez: una herramienta específica o, si no hay, `run_operation`
   (`describe_operation` dice sus parámetros). Las medidas conviene dejarlas como parámetros
   (`create_parameter`) para poder cambiarlas después con `set_parameter`.
3. **Ver la imagen.** `get_viewport_image` (vistas `iso`, `front`, `top`…; probá 2 o 3 ángulos).
   Comparala con lo que se pidió antes de seguir.
4. **Medir.** `get_physical_properties` (volumen, masa, caja), `measure_distance`,
   `check_interference` si hay varias piezas.
5. **Guardar.** `save_document` con una ruta absoluta. Si algo sale mal: `undo`.

## Unidades y nombres

- Longitudes en mm y ángulos en grados. En campos de tipo expresión se puede escribir `"10 mm"`,
  `"ancho / 2"` o `"45 deg"` (los nombres son parámetros existentes).
- Cuerpos y pasos se nombran por id (`op2.c1`, `op3`) o por nombre exacto, sin importar mayúsculas.
  Si el nombre se repite, usá el id. `get_scene_info` y `get_timeline` los muestran.

## Cómo leer los errores

Toda falla vuelve como `{"ok": false, "error_kind", "mensaje", "pistas"}`. Decidí con `error_kind`
(no cambia entre versiones), leé `mensaje` para el detalle y probá lo que dicen las `pistas`.

- `INVALID_ARGUMENTS`: nombres o tipos mal puestos; la pista trae la firma correcta.
- `FEATURE_NOT_FOUND`, `BODY_NOT_FOUND`: la referencia no existe; la pista sugiere nombres parecidos.
- `OPERATION_FAILED`: el paso no se pudo calcular con esos valores. El documento NO cambió.
- `CODE_ERROR`: falló tu código de `execute_code`; el mensaje trae la línea. El documento NO cambió.
- `CODE_TIMEOUT`: tu código de `execute_code` pasó su `timeout` (60 s por defecto) y se cortó; el documento
  NO cambió. Subí `timeout` o partí el trabajo en llamadas más cortas.

Los `avisos` de una respuesta correcta no son fallas, pero conviene leerlos.

## Agujeros, roscas y ajustes

- `create_hole` con `hole_tap="clearance"` (paso libre ISO 273 para `thread="M8"`, `fit="close"`/normal/loose),
  `hole_tap="modeled"` (rosca real; `thread_class="6H"`, "2B" o "auto"; `print_clearance=0.2` en mm para imprimir
  en 3D) o `hole_tap="taper"` (R/NPT, agujero cónico 1:16). `to="<Z"` lleva el agujero hasta una cara, plano o
  cuerpo; `reference_edges=[...]` con `reference_distances=[...]` lo ubica a distancia de dos aristas (paramétrico).
- `create_thread`: rosca sobre caras cilíndricas (eje o agujero); sin `thread="..."`, tamaño automático del tipo.
- `thread_info` (tipos, tamaños, diámetros límite de una clase) y `fit_tolerance` (ajuste ISO 286, p. ej. H7/g6)
  solo consultan: no cambian el documento.

## Atajos

- `get_recipe` / `apply_recipe`: foto y restauración de todo el documento en JSON.
- `execute_code`: varias herramientas en una sola llamada (`llamar("nombre", {...})`); un solo paso
  de deshacer para todo.
