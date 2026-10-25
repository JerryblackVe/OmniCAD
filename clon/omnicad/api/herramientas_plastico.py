# -*- coding: utf-8 -*-
"""PLÁSTICO › Configuración › Asignar y Administrar reglas de plástico, sin Qt (nucleo/plastico.py guarda las reglas)."""
from ..nucleo import geometria as geo
from ..nucleo import plastico
from ..timeline.ops_solido import OpReglaPlastico
from . import herramientas_ensamble as ens
from .errores import error
from .herramientas_material import nombre_material
from .herramientas_solido import _agregar
from .registro import herramienta


def _info(regla, origen):
    return dict(regla, source=origen)


def _asignadas(sesion):
    return {k: d["regla_plastico"]["nombre"] for k, d in sesion.doc.estado_final.componentes.items()
            if d.get("regla_plastico")}


@herramienta("list_plastic_rules", "material", "Reglas de plástico (PLÁSTICO › Administrar reglas) con todos sus valores: "
             "material, espesor, ángulo de desmoldeo, radio nominal y los valores de Design Advice (rango de espesor, "
             "variación, ángulo mínimo, umbral de filo). Las de fábrica (builtin), las propias del usuario (user) y a qué "
             "componentes de este documento está asignada cada una.")
def list_plastic_rules(sesion):
    usos = {}
    for k, nombre in _asignadas(sesion).items():
        usos.setdefault(nombre, []).append(k)
    reglas = [dict(_info(d, "builtin"), assigned_to=usos.get(n, [])) for n, d in plastico.REGLAS.items()]
    reglas += [dict(_info(d, "user"), assigned_to=usos.get(n, [])) for n, d in plastico.REGLAS_USUARIO.items()]
    return {"rules": reglas, "default": plastico.REGLA_DEFECTO, "user_library_file": str(plastico.ruta_reglas_propias()),
            "units": {"length": "mm", "angle": "deg"}}


@herramienta("create_plastic_rule", "material", "Crea una regla de plástico propia (PLÁSTICO › Administrar reglas › Nueva "
             "regla) y la deja en la biblioteca del usuario. Lo que no se da sigue al espesor como en las de fábrica "
             "(radio nominal = espesor / 2, rango de espesor de 0,5 a 1,5 veces, umbral de filo = un cuarto). No pisa las "
             "de fábrica. No cambia el documento.")
def create_plastic_rule(sesion, name: str, thickness: float, material: str | None = None, draft_angle: float = 1.0,
                        nominal_radius: float | None = None, min_thickness: float | None = None,
                        max_thickness: float | None = None, thickness_variation: float = 25.0,
                        min_draft_angle: float = 0.5, knife_edge: float | None = None, overwrite: bool = False,
                        save: bool = True):
    """
    name: nombre de la regla (p. ej. "ABS 2.5 mm").
    thickness: espesor de pared en mm.
    material: material físico (list_materials); vacío = sin material.
    draft_angle: ángulo de desmoldeo en grados (0 a 45).
    nominal_radius: radio nominal de los empalmes en mm; vacío = espesor / 2.
    min_thickness: espesor mínimo que acepta Design Advice, en mm; vacío = la mitad del espesor.
    max_thickness: espesor máximo, en mm; vacío = 1,5 veces el espesor.
    thickness_variation: variación de espesor tolerada, en porcentaje.
    min_draft_angle: ángulo de desmoldeo mínimo, en grados.
    knife_edge: umbral de filo en mm; vacío = un cuarto del espesor.
    overwrite: true para reemplazar una regla propia que ya existe con ese nombre.
    save: true la guarda en la biblioteca del usuario para las próximas sesiones; false, solo en esta sesión.
    """
    texto = str(name).strip()
    existente = next((n for n in plastico.REGLAS_USUARIO if n.casefold() == texto.casefold()), None)
    if existente is not None and not overwrite:
        raise error("NAME_EXISTS", f"Ya existe la regla propia «{existente}».", "overwrite=true la reemplaza.")
    datos = {"nombre": texto, "espesor": thickness, "material": nombre_material(material) if material else None,
             "angulo_desmoldeo": draft_angle, "variacion_espesor": thickness_variation, "angulo_minimo": min_draft_angle}
    for clave, valor in (("radio_nominal", nominal_radius), ("espesor_min", min_thickness),
                         ("espesor_max", max_thickness), ("umbral_filo", knife_edge)):
        if valor is not None:
            datos[clave] = valor
    try:
        plastico.definicion(**datos)                           # valida antes de tocar la biblioteca
        if existente is not None and existente != texto:
            plastico.quitar_regla(existente, guardar=save)
        d = plastico.definir_regla(datos, guardar=save)
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", str(e)) from e
    usan = [k for k, n in _asignadas(sesion).items() if n == d["nombre"]]
    if usan and existente is not None:
        sesion.avisar(f"Los componentes {', '.join(usan)} tienen la versión anterior: asignales la regla de nuevo.")
    return {"rule": _info(d, "user"), "replaced": existente is not None, "saved": bool(save)}


@herramienta("delete_plastic_rule", "material", "Borra una regla de plástico propia de la biblioteca del usuario (las de "
             "fábrica no se borran). Los componentes que ya la tienen asignada conservan su copia.")
def delete_plastic_rule(sesion, name: str, save: bool = True):
    """
    name: nombre de la regla propia.
    save: true también la saca del archivo de la biblioteca; false, solo de esta sesión.
    """
    texto = str(name).strip()
    nombre = next((n for n in plastico.REGLAS_USUARIO if n.casefold() == texto.casefold()), None)
    if nombre is None:
        if any(texto.casefold() == n.casefold() for n in plastico.REGLAS):
            raise error("INVALID_ARGUMENTS", f"«{texto}» es una regla de fábrica: no se borra.")
        raise error("ENTITY_NOT_FOUND", f"No hay una regla propia llamada «{texto}» en la biblioteca.")
    plastico.quitar_regla(nombre, guardar=save)
    return {"deleted": nombre}


@herramienta("assign_plastic_rule", "solido", "Asigna una regla de plástico a un componente (PLÁSTICO › Asignar regla de "
             "plástico): el material físico de la regla pasa a todos sus cuerpos y la regla queda guardada en el "
             "componente (list_plastic_rules dice cuáles). Con create_parameters=true sus valores quedan además como "
             "parámetros del diseño (PlasticThickness, PlasticDraftAngle y PlasticNominalRadius) para usarlos en "
             "Extruir, Nervio, Red, Vaciado, Desmoldeo… Una regla distinta, asignada después al mismo componente, "
             "reemplaza a la anterior. delete_feature quita la asignación.", modifica=True)
def assign_plastic_rule(sesion, component: str, rule: str = plastico.REGLA_DEFECTO, name: str | None = None,
                        create_parameters: bool = False):
    """
    component: id o nombre del componente (get_assembly).
    rule: nombre de la regla (list_plastic_rules); vacío = "ABS 2 mm".
    name: nombre del paso; vacío = «Regla de plástico<n>».
    create_parameters: true crea (o actualiza) los parámetros PlasticThickness (mm), PlasticDraftAngle (deg) y PlasticNominalRadius (mm) con los valores de la regla.
    """
    from ..timeline.ops_ensamblar import componente_por_ref
    estado = sesion.doc.estado_final
    k = componente_por_ref(estado, component)
    if k is None:
        raise error("ENTITY_NOT_FOUND", f"No hay un componente «{component}».", "create_component lo crea; get_assembly lista.")
    try:
        r = plastico.regla(rule or plastico.REGLA_DEFECTO)
    except geo.ErrorGeometria as e:
        raise error("ENTITY_NOT_FOUND", str(e), "list_plastic_rules lista las reglas.") from e
    doc = sesion.doc
    op = OpReglaPlastico(doc.nuevo_id(), ens.nombre_paso(sesion, name, "Regla de plástico", OpReglaPlastico),
                         componente=k, regla=r)
    resultado = _agregar(sesion, op)
    if create_parameters:
        from . import llamar
        hay = {p["name"] for p in llamar(sesion, "get_parameters", {})["result"]["parameters"]}
        for nombre, valor, unidad in (("PlasticThickness", r["espesor"], "mm"), ("PlasticDraftAngle", r["angulo_desmoldeo"], "deg"),
                                      ("PlasticNominalRadius", r["radio_nominal"], "mm")):
            llamar(sesion, "set_parameter" if nombre in hay else "create_parameter",
                   {"name": nombre, "expression": f"{valor:g} {unidad}"})
    resultado["rule"] = r
    resultado["component"] = k
    return resultado
