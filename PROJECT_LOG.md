## Registro

- **2026-11-19 · Exploración ver_grupos_caras.** Explorado códigobase OmniCAD-PREP-TEST-ver-grupos-caras. Hallazgos: `ver_grupos_caras` es un atajo Shift+F que muestra grupos de caras en mallas mediante `get_viewport_image(mesh_face_groups=True)`. No existe `test_prep_cmd_ver_grupos_caras.py`. Operaciones timeline: `OpGruposCaras`, `OpCombinarGruposCaras`, `OpCrearGrupoCaras` en `ops_malla.py`. UI: `cinta.py`, `ventana.py`, `iconos_extra.py`. API: `herramientas_inspeccion.py`. Cobertura UI→API en `test_cobertura_ui_api.py` línea 109.

## Lecciones aprendidas

- `ver_grupos_caras` no es un comando de creación/edición geométrica, sino un modo de visualización de grupos existentes en mallas.
- La conexión UI→API está mapeada en `test_cobertura_ui_api.py`: `ver_grupos_caras` → `get_viewport_image`.
- Los tests de API (`test_api_malla.py`) siguen patrón: `api.llamar(s, "operacion", args)` con afirmaciones numéricas y un paso de deshacer.
- No existe test dedicado a `ver_grupos_caras`; sería nuevo test siguiendo patrón `test_api_malla.py`.