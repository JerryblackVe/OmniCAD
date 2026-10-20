# -*- coding: utf-8 -*-
"""Cobertura UI → API (MCP-0a, docs/brechas_mcp.md): cada clave de la cinta de DISEÑO (ui/cinta.py, incluida la
pestaña contextual BOCETO) y cada ítem con comando real de los espacios DIBUJO, RENDER y ANIMACIÓN tiene una
herramienta del catálogo (`api.catalogo()`) o una excusa escrita acá. Si aparece una clave nueva sin ninguna de
las dos, el test falla: es lo que dejó pasar el bug B-80 (todo ANIMACIÓN sin herramientas).

Las excusas «pendiente MCP-n» citan el plan de docs/brechas_mcp.md (el ID de la herramienta que falta); las que
dicen que algo no le sirve a un agente son las que ese documento descarta (selección con el ratón, prioridad,
tema…). Los botones grisados («no disponible en OmniCAD») no son comandos: se anotan para que no se pierdan.
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
    "Calcomanía": "set_decal",
}

# clave → motivo por el que no tiene herramienta. «pendiente MCP-n» = el ID del plan docs/brechas_mcp.md.
_RATON = "se elige con el ratón en la vista: un agente elige por id y no por clic (docs/brechas_mcp.md › Ola 4)"
_GRISADO = "comando no implementado en la ventana (botón grisado, regla de honestidad de la cinta)"
EXCUSAS = {
    # --- cinta DISEÑO: análisis, configuraciones y operaciones sin herramienta propia (olas 4 y 5)
    "accesibilidad": "pendiente MCP-26", "angulo_desmoldeo": "pendiente MCP-26", "cebra": "pendiente MCP-26",
    "curvatura_peine": "pendiente MCP-26", "mapa_entorno": "pendiente MCP-26", "mapa_curvatura": "pendiente MCP-26",
    "isocurva": "pendiente MCP-26", "radio_minimo": "pendiente MCP-26", "seccion": "pendiente MCP-26",
    "colores_componente": "pendiente MCP-31", "calcular": "pendiente MCP-28",
    "configurar": "pendiente MCP-27", "mostrar_configuracion": "pendiente MCP-27",
    "alinear": "pendiente MCP-37", "escala_3d": "pendiente MCP-37",
    "bobina": "pendiente MCP-32", "tuberia": "pendiente MCP-32",
    "nervio": "pendiente MCP-33", "red": "pendiente MCP-33", "repujado": "pendiente MCP-33",
    "saliente": "pendiente MCP-33", "labio": "pendiente MCP-33",
    "relleno_contorno": "pendiente MCP-34", "cuerpo_envolvente": "pendiente MCP-34", "engrosar": "pendiente MCP-34",
    "sup_extruir": "pendiente MCP-35", "sup_revolucion": "pendiente MCP-35", "sup_barrido": "pendiente MCP-35",
    "sup_solevacion": "pendiente MCP-35", "sup_desfase": "pendiente MCP-35", "sup_empalme": "pendiente MCP-35",
    "parche": "pendiente MCP-35", "reglada": "pendiente MCP-35",
    "recortar_sup": "pendiente MCP-36", "extender_sup": "pendiente MCP-36", "coser": "pendiente MCP-36",
    "descoser": "pendiente MCP-36", "destrimar": "pendiente MCP-36", "invertir_normal": "pendiente MCP-36",
    "reemplazar_cara": "pendiente MCP-38", "dividir_cara": "pendiente MCP-38", "dividir_cuerpo": "pendiente MCP-38",
    "division_silueta": "pendiente MCP-38", "quitar": "pendiente MCP-38",
    "scu": "pendiente MCP-40", "eje_cilindro": "pendiente MCP-40", "eje_perpendicular": "pendiente MCP-40",
    "eje_dos_planos": "pendiente MCP-40", "eje_dos_puntos": "pendiente MCP-40", "eje_arista": "pendiente MCP-40",
    "punto_vertice": "pendiente MCP-40", "punto_dos_aristas": "pendiente MCP-40",
    "punto_tres_planos": "pendiente MCP-40", "punto_centro": "pendiente MCP-40",
    "punto_arista_plano": "pendiente MCP-40", "punto_ruta": "pendiente MCP-40",
    "plano_angulo": "pendiente MCP-39", "plano_tangente": "pendiente MCP-39", "plano_medio": "pendiente MCP-39",
    "plano_perpendicular": "pendiente MCP-39", "plano_dos_aristas": "pendiente MCP-39",
    "plano_tres_puntos": "pendiente MCP-39", "plano_ruta": "pendiente MCP-39",
    "fijacion": "pendiente MCP-41", "lienzo": "pendiente MCP-41 (insertar lienzo); el render en el lienzo es "
                                               "pendiente MCP-22", "operacion_base": "pendiente MCP-41",
    "activar_patron_plano": "pendiente MCP-53", "impresion3d": "prepara un archivo para la impresora 3D; export "
                                                              "(.stl) alcanza para obtener la malla",
    "secuencias": "la cubre execute_code (docs/brechas_mcp.md › Ola 7, «Se descartan»)",
    "biblioteca_roscas": "la cubre thread_info (docs/brechas_mcp.md › Ola 7, «Se descartan»)",
    "pulsar_tirar": "la cubren offset_faces (caras) y fillet (aristas): es lo que hace el comando",
    # --- selección: un agente no necesita el ratón
    "seleccionar": _RATON, "sel_ventana": _RATON, "sel_libre": _RATON, "sel_pintura": _RATON,
    "seleccionar_todo": "un agente elige por id: get_scene_info lista todos los cuerpos",
    "invertir_seleccion": "pendiente MCP-50 (invert en select_bodies)",
    "seleccion_nombre": "pendiente MCP-50 (by_name en select_bodies)",
    "seleccion_tamano": "pendiente MCP-50 (by_size en select_bodies)",
    "prioridad_cuerpo": _RATON, "prioridad_cara": _RATON, "prioridad_arista": _RATON,
    "prioridad_componente": _RATON,
    "filtro_caras": _RATON, "filtro_aristas": _RATON, "filtro_vertices": _RATON, "filtro_cuerpos": _RATON,
    "filtro_bocetos": _RATON, "filtro_construccion": _RATON,
    # --- boceto: opciones que la herramienta todavía no tiene (ola 7 y huecos parciales de la 4)
    "sk_linea_medio": "pendiente MCP-74", "sk_rectangulo_3p": "pendiente MCP-74",
    "sk_rectangulo_centro": "pendiente MCP-74", "sk_circulo_2p": "pendiente MCP-72",
    "sk_circulo_3p": "pendiente MCP-72", "sk_poligono_arista": "pendiente MCP-73",
    "sk_espiral": "pendiente MCP-29", "sk_r_poligono": "pendiente MCP-30", "sk_terminar": "pendiente MCP-77",
    "sk_intersecar": "pendiente MCP-75", "sk_incluir_3d": "pendiente MCP-75",
    "sk_arco_tangente": "draw_arc no tiene la forma tangente (docs/brechas_mcp.md › Ola 4, huecos parciales)",
    "sk_alargar": "sin herramienta (alargar curvas); no figura en docs/brechas_mcp.md: pendiente de auditar",
    "sk_partir": "sin herramienta (partir curvas); no figura en docs/brechas_mcp.md: pendiente de auditar",
    # --- espacio DIBUJO (ola 2)
    "vista_base": "pendiente MCP-13", "vista_proyectada": "pendiente MCP-13", "vista_seccion": "pendiente MCP-13",
    "vista_detalle": "pendiente MCP-13", "girar": "pendiente MCP-14", "mover": "pendiente MCP-15",
    "borrar": "pendiente MCP-15", "linea_centro": "pendiente MCP-17", "marca_centro": "pendiente MCP-17",
    "cota": "pendiente MCP-16", "cota_ordenadas": "pendiente MCP-16", "cota_lineal": "pendiente MCP-16",
    "cota_alineada": "pendiente MCP-16", "cota_angular": "pendiente MCP-16", "cota_radial": "pendiente MCP-16",
    "cota_radio": "pendiente MCP-16", "cota_diametro": "pendiente MCP-16",
    "texto": "pendiente MCP-18", "nota": "pendiente MCP-18", "tabla": "pendiente MCP-18", "globo": "pendiente MCP-18",
    "exportar_pdf": "pendiente MCP-20", "exportar_dxf": "pendiente MCP-20", "exportar_svg": "pendiente MCP-20",
    "hoja": "pendiente MCP-12",
    "Vista de rotura": _GRISADO, "Vista de sección parcial": _GRISADO, "Vista recortada": _GRISADO,
    "Crear boceto": _GRISADO, "Patrón de marcas de centro": _GRISADO, "Extensión de arista": _GRISADO,
    "Cota de línea base": _GRISADO, "Cota en cadena": _GRISADO, "Corte de cota": _GRISADO,
    "Renumerar": _GRISADO, "Exportar DWG": _GRISADO, "Exportar CSV": _GRISADO,
    # --- espacio RENDER (ola 3)
    "escena": "pendiente MCP-22", "config_lienzo": "pendiente MCP-22", "capturar": "pendiente MCP-46",
    "renderizar": "pendiente MCP-25", "galeria": "pendiente MCP-25",
    "terminar": "cierra el espacio RENDERIZAR de la ventana: no aplica a un agente",
    "Mapeo de texturas": _GRISADO,
    # --- espacio ANIMACIÓN (ola 1): lo que queda fuera de las herramientas
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


def test_hay_herramientas_de_animacion():
    """B-80: el espacio ANIMACIÓN queda cubierto por las herramientas de la ola 1."""
    grupo = {h["nombre"] for h in api.catalogo("animacion")}
    assert {"create_storyboard", "list_storyboards", "get_storyboard", "rename_storyboard", "copy_storyboard",
            "delete_storyboard", "reverse_storyboard", "add_animation_action", "edit_animation_action",
            "delete_animation_action", "auto_explode", "set_animation_camera", "add_animation_annotation",
            "get_animation_frame", "export_animation_video"} <= grupo
