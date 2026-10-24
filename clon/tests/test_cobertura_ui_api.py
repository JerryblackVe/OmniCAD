# -*- coding: utf-8 -*-
"""Cobertura UI → API (MCP-0a, docs/brechas_mcp.md): cada clave de la cinta de DISEÑO (ui/cinta.py, incluida la
pestaña contextual BOCETO) y cada ítem con comando real de los espacios DIBUJO, RENDER y ANIMACIÓN tiene una
herramienta del catálogo (`api.catalogo()`) o una excusa escrita acá. Si aparece una clave nueva sin ninguna de
las dos, el test falla: es lo que dejó pasar el bug B-80 (todo ANIMACIÓN sin herramientas).

Las excusas dicen que algo no le sirve a un agente (selección con el ratón, prioridad, tema…, lo que
docs/brechas_mcp.md descarta). No queda ninguna «pendiente MCP-n»: B-80 está cerrado. Los botones grisados («no disponible en OmniCAD») no son comandos: se anotan para que no se pierdan.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api                                    # noqa: E402
from omnicad.ui import cinta                               # noqa: E402
from omnicad.ui import animacion, dibujo, render           # noqa: E402

# clave de la cinta/spacio → herramienta del catálogo que hace lo mismo.
HERRAMIENTAS = {
    # --- cinta DISEÑO › SÓLIDO y SUPERFICIE
    "extruir": "extrude", "revolucion": "revolve", "barrido": "sweep", "solevacion": "loft",
    "agujero": "create_hole", "rosca": "create_thread", "caja": "create_box", "cilindro": "create_cylinder",
    "esfera": "create_sphere", "toroide": "create_torus", "engranaje": "create_gear",
    "eje_escalonado": "create_shaft", "patron_rectangular_3d": "rectangular_pattern",
    "patron_circular_3d": "circular_pattern", "patron_ruta": "path_pattern", "patron_puntos": "point_pattern",
    "multitransformar": "multi_transform", "simetria_3d": "mirror", "empalme_3d": "fillet",
    "chaflan_3d": "chamfer", "quitar_empalmes": "remove_fillets", "vaciado": "shell", "desmoldeo": "draft",
    "combinar": "boolean_operation", "desfase": "offset_faces", "desfase_cara": "offset_faces",
    "mover_copiar": "move_body", "apoyar": "drop_to_plane", "suprimir": "suppress_feature",
    "material_fisico": "set_material", "aspecto": "set_appearance", "parametros": "set_parameter",
    "lista_materiales": "get_bill_of_materials", "boceto": "create_sketch", "medir": "measure_distance",
    "interferencia": "check_interference", "revisar_geometria": "check_geometry", "reparar_cuerpo": "repair_body",
    "centro_masa": "get_physical_properties", "calcomania": "set_decal", "insertar_svg": "insert_svg",
    "vectorizar_imagen": "trace_image", "insertar_dxf": "insert_dxf", "insertar_malla": "insert_file",
    "importar_step": "insert_file", "insertar_diseno": "insert_file", "insertar_derivacion": "insert_derive",
    "nuevo_componente": "create_component",
    "union": "create_joint", "union_construida": "create_as_built_joint", "origen_union": "create_joint_origin",
    "grupo_rigido": "create_rigid_group", "accionar_uniones": "drive_joint",
    "vinculo_movimiento": "create_motion_link", "fijar_componente": "ground_component",
    "estudio_movimiento": "motion_study", "plano_desfase": "create_construction_plane",
    "exportar_malla": "export_mesh", "exportar_stl": "export", "exportar_obj": "export",
    # --- cinta DISEÑO › MALLA
    "malla_teselar": "tessellate", "reparar_malla": "repair_mesh", "limpiar_malla": "clean_mesh",
    "grupos_caras": "generate_face_groups", "reducir_malla": "reduce_mesh", "remallar": "remesh",
    "cortar_plano": "plane_cut_mesh", "combinar_mallas": "combine_meshes", "suavizar_malla": "smooth_mesh",
    "invertir_normal_malla": "reverse_mesh_normals", "separar_malla": "separate_mesh", "escalar_malla": "scale_mesh",
    "convertir_malla": "convert_mesh", "vaciado_malla": "shell_mesh",
    # --- cinta DISEÑO › CHAPA
    "pestana": "create_base_flange", "pestana_contorno": "create_contour_flange", "dobladillo": "create_hem",
    "convertir_chapa": "convert_to_sheet_metal", "plegar": "fold", "desplegar": "unfold", "replegar": "refold",
    "desgarro": "rip", "unir_plegando": "join_by_bend", "patron_plano": "create_flat_pattern",
    "exportar_dxf_chapa": "export_flat_pattern_dxf", "reglas_chapa": "list_sheet_metal_rules",
    # --- pestaña contextual BOCETO
    "sk_linea": "draw_line", "sk_rectangulo": "draw_rectangle", "sk_circulo": "draw_circle",
    "sk_circulo_2t": "draw_tangent_circle", "sk_circulo_3t": "draw_tangent_circle", "sk_arco": "draw_arc",
    "sk_arco_centro": "draw_arc", "sk_poligono_circunscrito": "create_polygon",
    "sk_poligono_inscrito": "create_polygon", "sk_elipse": "draw_ellipse", "sk_ranura_centro": "draw_slot",
    "sk_ranura_total": "draw_slot", "sk_ranura_punto": "draw_slot", "sk_ranura_arco_3p": "draw_slot",
    "sk_ranura_arco_centro": "draw_slot", "sk_spline_ajuste": "draw_spline", "sk_spline_control": "draw_spline",
    "sk_conica": "draw_conic", "sk_punto": "draw_point", "sk_texto": "add_text",
    "sk_desglosar_texto": "explode_text", "sk_simetria": "mirror_sketch", "sk_patron_circular": "sketch_circular_pattern",
    "sk_patron_rectangular": "sketch_rectangular_pattern", "sk_proyectar": "project_to_sketch",
    "sk_cota": "add_dimension", "sk_empalme": "sketch_fillet", "sk_chaflan": "sketch_chamfer",
    "sk_chaflan_dist_angulo": "sketch_chamfer", "sk_chaflan_dos_dist": "sketch_chamfer",
    "sk_curva_fusion": "draw_blend_curve", "sk_desfase": "offset_sketch_curves", "sk_recortar": "trim_sketch_curve",
    "sk_escala": "transform_sketch", "sk_mover": "transform_sketch", "sk_autorestringir": "auto_constrain",
    "sk_r_horizontal_vertical": "add_constraint", "sk_r_coincidente": "add_constraint",
    "sk_r_tangente": "add_constraint", "sk_r_igual": "add_constraint", "sk_r_paralela": "add_constraint",
    "sk_r_perpendicular": "add_constraint", "sk_r_fijo": "add_constraint", "sk_r_punto_medio": "add_constraint",
    "sk_r_concentrica": "add_constraint", "sk_r_colineal": "add_constraint", "sk_r_simetria": "add_constraint",
    "sk_r_curvatura": "add_constraint",
    # --- espacios: ANIMACIÓN (ola 1, api/herramientas_animacion.py) y RENDER ya cubierto
    "nuevo_guion": "create_storyboard", "copiar_guion": "copy_storyboard", "eliminar_guion": "delete_storyboard",
    "invertir_guion": "reverse_storyboard", "transformar": "add_animation_action",
    "restaurar": "add_animation_action", "explosion_uno": "auto_explode", "explosion_todos": "auto_explode",
    "visibilidad": "add_animation_action", "anotacion": "add_animation_annotation",
    "vista": "set_animation_camera", "publicar": "export_animation_video",
    # --- espacio DIBUJO (api/herramientas_dibujo*.py) y RENDER (api/herramientas_render.py)
    "vista_base": "add_drawing_view", "vista_proyectada": "add_drawing_view", "vista_seccion": "add_drawing_view",
    "vista_detalle": "add_drawing_view", "girar": "edit_drawing_view", "mover": "move_drawing_element",
    "borrar": "delete_drawing_element", "linea_centro": "add_drawing_centerline",
    "marca_centro": "add_drawing_center_mark", "cota": "add_drawing_dimension",
    "cota_ordenadas": "add_drawing_dimension", "cota_lineal": "add_drawing_dimension",
    "cota_alineada": "add_drawing_dimension", "cota_angular": "add_drawing_dimension",
    "cota_radial": "add_drawing_dimension", "cota_radio": "add_drawing_dimension",
    "cota_diametro": "add_drawing_dimension", "texto": "add_drawing_text", "nota": "add_drawing_note",
    "tabla": "add_drawing_table", "globo": "add_drawing_balloon", "exportar_pdf": "export_drawing",
    "exportar_dxf": "export_drawing", "exportar_svg": "export_drawing", "hoja": "set_drawing_sheet",
    "escena": "set_render_scene", "config_lienzo": "set_render_scene", "renderizar": "render_image",
    "galeria": "render_image",             # las imágenes vuelven en la respuesta (o a path); no hay galería de sesión
    "Calcomanía": "set_decal",
    "calcular": "recompute_all",
    # --- B-80, olas 4 a 7: análisis, configuraciones, construcción, superficies, división, visor y boceto
    "accesibilidad": "manage_analysis", "angulo_desmoldeo": "manage_analysis", "cebra": "manage_analysis",
    "curvatura_peine": "manage_analysis", "mapa_entorno": "manage_analysis", "mapa_curvatura": "manage_analysis",
    "isocurva": "manage_analysis", "radio_minimo": "manage_analysis", "seccion": "section_view",
    "colores_componente": "get_viewport_image", "configurar": "manage_configurations",
    "mostrar_configuracion": "manage_configurations", "alinear": "align_bodies", "escala_3d": "scale_body",
    "bobina": "create_coil", "tuberia": "create_pipe", "nervio": "create_rib", "red": "create_web",
    "repujado": "create_emboss", "saliente": "create_boss", "labio": "create_lip_groove",
    "relleno_contorno": "create_boundary_fill", "cuerpo_envolvente": "create_bounding_solid", "engrosar": "thicken",
    "sup_extruir": "create_surface_extrude", "sup_revolucion": "create_surface_revolve",
    "sup_barrido": "create_surface_sweep", "sup_solevacion": "create_surface_loft", "sup_desfase": "offset_surface",
    "sup_empalme": "fillet_surface", "parche": "create_patch", "reglada": "create_ruled_surface",
    "recortar_sup": "trim_surface", "extender_sup": "extend_surface", "coser": "stitch_surfaces",
    "descoser": "unstitch_surfaces", "destrimar": "untrim_surface", "invertir_normal": "reverse_surface_normal",
    "reemplazar_cara": "replace_face", "dividir_cara": "split_face", "dividir_cuerpo": "split_body",
    "division_silueta": "silhouette_split", "quitar": "remove_bodies", "scu": "create_ucs",
    "eje_cilindro": "create_construction_axis", "eje_perpendicular": "create_construction_axis",
    "eje_dos_planos": "create_construction_axis", "eje_dos_puntos": "create_construction_axis",
    "eje_arista": "create_construction_axis", "punto_vertice": "create_construction_point",
    "punto_dos_aristas": "create_construction_point", "punto_tres_planos": "create_construction_point",
    "punto_centro": "create_construction_point", "punto_arista_plano": "create_construction_point",
    "punto_ruta": "create_construction_point", "plano_angulo": "create_construction_plane",
    "plano_tangente": "create_construction_plane", "plano_medio": "create_construction_plane",
    "plano_perpendicular": "create_construction_plane", "plano_dos_aristas": "create_construction_plane",
    "plano_tres_puntos": "create_construction_plane", "plano_ruta": "create_construction_plane",
    "fijacion": "insert_fastener", "lienzo": "insert_canvas", "operacion_base": "create_base_feature",
    "activar_patron_plano": "set_flat_pattern_view", "invertir_seleccion": "select_bodies",
    "seleccion_nombre": "select_bodies", "seleccion_tamano": "select_bodies",
    "sk_linea_medio": "draw_line", "sk_rectangulo_3p": "draw_rectangle", "sk_rectangulo_centro": "draw_rectangle",
    "sk_circulo_2p": "draw_circle", "sk_circulo_3p": "draw_circle", "sk_poligono_arista": "create_polygon",
    "sk_espiral": "draw_spiral", "sk_r_poligono": "add_constraint", "sk_terminar": "sketch_view", "sk_terminar_auto": "sketch_view",
    "sk_intersecar": "project_to_sketch", "sk_incluir_3d": "project_to_sketch", "sk_arco_tangente": "draw_arc",
    "sk_perfil_giratorio": "project_spun_profile", "sk_romper_vinculo": "break_projection_link",
    "sk_proyecciones_perdidas": "manage_lost_projections", "sk_editar_patron": "edit_sketch_pattern",
    "sk_soltar_desfase": "release_offset",
    "sk_alargar": "extend_sketch_curve", "sk_partir": "split_sketch_curve", "capturar": "capture_viewport",
}

# clave → motivo por el que no tiene herramienta.
_RATON = "se elige con el ratón en la vista: un agente elige por id y no por clic (docs/brechas_mcp.md › Ola 4)"
_GRISADO = "comando no implementado en la ventana (botón grisado, regla de honestidad de la cinta)"
EXCUSAS = {
    "impresion3d": "prepara un archivo para la impresora 3D; export (.stl) alcanza para obtener la malla",
    "secuencias": "la cubre execute_code (docs/brechas_mcp.md › Ola 7, «Se descartan»)",
    "biblioteca_roscas": "la cubre thread_info (docs/brechas_mcp.md › Ola 7, «Se descartan»)",
    "pulsar_tirar": "la cubren offset_faces (caras) y fillet (aristas): es lo que hace el comando",
    # --- selección: un agente no necesita el ratón
    "seleccionar": _RATON, "sel_ventana": _RATON, "sel_libre": _RATON, "sel_pintura": _RATON,
    "seleccionar_todo": "un agente elige por id: get_scene_info lista todos los cuerpos",
    "prioridad_cuerpo": _RATON, "prioridad_cara": _RATON, "prioridad_arista": _RATON,
    "prioridad_componente": _RATON,
    "filtro_caras": _RATON, "filtro_aristas": _RATON, "filtro_vertices": _RATON, "filtro_cuerpos": _RATON,
    "filtro_bocetos": _RATON, "filtro_construccion": _RATON,
    # --- espacio DIBUJO: lo que no se puede o no hace falta (el resto está en HERRAMIENTAS)
    "Vista de rotura": _GRISADO, "Vista de sección parcial": _GRISADO, "Vista recortada": _GRISADO,
    "Crear boceto": _GRISADO, "Patrón de marcas de centro": _GRISADO, "Extensión de arista": _GRISADO,
    "Cota de línea base": _GRISADO, "Cota en cadena": _GRISADO, "Corte de cota": _GRISADO,
    "Renumerar": _GRISADO, "Exportar DWG": _GRISADO, "Exportar CSV": _GRISADO,
    # --- espacio RENDER
    "terminar": "cierra el espacio RENDERIZAR de la ventana: no aplica a un agente",
    "Mapeo de texturas": _GRISADO,
    # --- espacio ANIMACIÓN: lo que queda fuera de las herramientas
    "grabar_vista": "grabación interactiva de la cámara (agrega acciones mientras se orbita); set_animation_camera "
                    "agrega la misma acción Vista",
    "Explosión manual": _GRISADO, "Mostrar trayectorias": _GRISADO,
    "Aspecto": "botón grisado en ANIMACIÓN; el aspecto se cambia con set_appearance",
}


# ---------------------------------------------------------------- claves de las cintas
def _claves_items(items):
    """Claves de acción reales de una lista de ítems («item» de _i, «sub», o texto de un grisado)."""
    salida = []
    for it in items:
        if isinstance(it, str):
            if it != "-":                      # "-" es el separador SEP
                salida.append(it)
        elif it and it[0] == "item" and it[2]:
            salida.append(it[2])
        elif it and it[0] == "sub":
            salida.extend(_claves_items(it[2]))
        elif it and len(it) == 1:            # ("Texto",) = comando grisado: se controla igual
            salida.append(it[0])
    return salida


def _claves_de(grupos):
    salida = set()
    for _titulo, rapidos, items in grupos:
        salida |= set(_claves_items(list(rapidos) + list(items)))
    return salida


def _todas():
    """{clave: de dónde sale} en la cinta de DISEÑO y los espacios DIBUJO, RENDER y ANIMACIÓN."""
    claves = {}
    for nombre, grupos in cinta.PESTANAS + cinta.CONTEXTUALES:
        for c in _claves_de(grupos):
            claves.setdefault(c, f"cinta DISEÑO › {nombre}")
    for espacio, grupos in (("DIBUJO", dibujo.GRUPOS), ("RENDERIZAR", render.GRUPOS_RENDER),
                            ("ANIMACIÓN", animacion.GRUPOS_ANIMACION)):
        for c in _claves_de(grupos):
            claves.setdefault(c, f"espacio {espacio}")
    return claves


@pytest.fixture(scope="module")
def catalogo():
    return {h["nombre"] for h in api.catalogo()}


@pytest.mark.parametrize("clave, origen", sorted(_todas().items()))
def test_cada_clave_tiene_herramienta_o_excusa(clave, origen, catalogo):
    h, excusa = HERRAMIENTAS.get(clave), EXCUSAS.get(clave)
    assert h is not None or excusa is not None, (
        f"«{clave}» ({origen}) no tiene herramienta en el catálogo ni excusa en este test: "
        "creala (docs/brechas_mcp.md) o anotá por qué no hace falta.")
    if h is not None:
        assert h in catalogo, f"«{clave}» apunta a la herramienta «{h}», que no existe en el catálogo."


def test_los_diccionarios_no_tienen_entradas_viejas():
    claves = set(_todas())
    sobran = sorted((set(HERRAMIENTAS) | set(EXCUSAS)) - claves)
    assert not sobran, f"Claves que ya no existen en la interfaz: {', '.join(sobran)}."


def test_hay_herramientas_de_dibujo_y_render():
    """B-80: los espacios DIBUJO y RENDERIZAR quedan cubiertos por sus herramientas."""
    dibujo = {h["nombre"] for h in api.catalogo("dibujo")}
    assert {"create_drawing", "get_drawing", "set_drawing_sheet", "add_drawing_view", "edit_drawing_view",
            "move_drawing_element", "delete_drawing_element", "add_drawing_dimension", "add_drawing_centerline",
            "add_drawing_center_mark", "add_drawing_text", "add_drawing_note", "add_drawing_balloon",
            "add_drawing_table", "edit_drawing_annotation", "get_drawing_geometry", "export_drawing",
            "get_drawing_image"} <= dibujo
    render = {h["nombre"] for h in api.catalogo("render")}
    assert {"list_render_environments", "get_render_scene", "set_render_scene", "set_render_camera",
            "render_image"} <= render


def test_hay_herramientas_de_animacion():
    """B-80: el espacio ANIMACIÓN queda cubierto por las herramientas de la ola 1."""
    grupo = {h["nombre"] for h in api.catalogo("animacion")}
    assert {"create_storyboard", "list_storyboards", "get_storyboard", "rename_storyboard", "copy_storyboard",
            "delete_storyboard", "reverse_storyboard", "add_animation_action", "edit_animation_action",
            "delete_animation_action", "auto_explode", "set_animation_camera", "add_animation_annotation",
            "get_animation_frame", "export_animation_video"} <= grupo
