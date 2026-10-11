# -*- coding: utf-8 -*-
"""
Herramientas del grupo "material": materiales físicos (MODIFICAR › Material físico y Administrar materiales de
Fusion) y aspecto (MODIFICAR › Aspecto).

  - El MATERIAL FÍSICO da la densidad: con él, get_physical_properties calcula la masa. La tabla está en
    `nucleo/analisis.py` (TABLA_MATERIALES): los de fábrica más los propios del usuario, que define_material guarda en
    «materiales.json» de la carpeta de datos de la app (o en la ruta de la variable OMNICAD_MATERIALES) y se cargan
    en cada sesión, como la biblioteca de materiales del usuario en Fusion.
  - El ASPECTO es solo cómo se ve (color y acabado): no cambia la masa. Sin aspecto, el cuerpo se ve con el color
    de su material.
Los dos son propiedades de los cuerpos (no pasos del timeline), entran en deshacer y se guardan con el proyecto.
get_bill_of_materials da la lista de materiales (ADMINISTRAR › Lista de materiales) con cantidades y masas.
"""
import difflib

from ..nucleo import analisis as an
from ..nucleo import geometria as geo
from ..nucleo import render_cpu as rc
from .errores import error
from .registro import herramienta


def _r(x):
    return round(float(x), 4) + 0.0


def _hex(color):
    return "#" + "".join(f"{round(float(c) * 255):02x}" for c in color[:3])


def color_rgb(valor, que="color"):
    """[r, g, b] 0..1 de «#rrggbb» (o «rrggbb») o de una lista de 3 números: 0..1, o 0..255 si alguno pasa de 1."""
    if isinstance(valor, str):
        texto = valor.strip().lstrip("#")
        if len(texto) != 6:
            raise error("INVALID_ARGUMENTS", f"{que} va como «#rrggbb» (p. ej. «#d01010») o [r, g, b]: llegó {valor!r}.")
        try:
            return [int(texto[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        except ValueError:
            raise error("INVALID_ARGUMENTS", f"{que} va como «#rrggbb» (p. ej. «#d01010»): llegó {valor!r}.") from None
    if not isinstance(valor, (list, tuple)) or len(valor) != 3 or not all(
            isinstance(x, (int, float)) and not isinstance(x, bool) for x in valor):
        raise error("INVALID_ARGUMENTS", f"{que} va como «#rrggbb» o [r, g, b]: llegó {valor!r}.")
    escala = 255.0 if any(x > 1 for x in valor) else 1.0
    rgb = [float(x) / escala for x in valor]
    if not all(0.0 <= x <= 1.0 for x in rgb):
        raise error("INVALID_ARGUMENTS", f"{que}: cada componente va de 0 a 1 (o de 0 a 255): llegó {valor!r}.")
    return rgb


def nombre_material(nombre):
    """Nombre exacto del material de la tabla (sin distinguir mayúsculas) o MATERIAL_NOT_FOUND con sugerencias."""
    texto = str(nombre).strip()
    if texto in an.TABLA_MATERIALES:
        return texto
    hallados = [m for m in an.TABLA_MATERIALES if m.casefold() == texto.casefold()]
    if hallados:
        return hallados[0]
    parecidos = difflib.get_close_matches(texto, list(an.TABLA_MATERIALES), n=3, cutoff=0.4) or \
        [m for m in an.TABLA_MATERIALES if texto.casefold() in m.casefold()][:3]
    raise error("MATERIAL_NOT_FOUND", f"No existe el material «{texto}».",
                *([f"¿Quisiste decir: {', '.join(parecidos)}?"] if parecidos else []))


def _info(nombre):
    m = an.TABLA_MATERIALES[nombre]
    return {"name": nombre, "density_g_cm3": _r(m["densidad"]), "color": _hex(m["color"]),
            "custom": nombre not in an.MATERIALES_BASE}


def _cuerpos(sesion, bodies):
    if not bodies:
        raise error("INVALID_ARGUMENTS", "Falta elegir los cuerpos (ids o nombres).")
    salida = []
    for b in bodies:
        c = sesion.cuerpo(b)
        if c.id not in salida:
            salida.append(c.id)
    return salida


def _usos(sesion, nombre):
    doc = sesion.doc
    return [c.id for c in doc.estado_final.cuerpos.values()
            if (doc.propiedad(c.id, "material") or getattr(c, "material", None)) == nombre]


@herramienta("list_materials", "material", "Materiales físicos disponibles con su densidad (g/cm³) y su color: los de "
             "fábrica (metales, plásticos, gomas, silicona, TPU, madera, vidrio…) y los propios (define_material). "
             "Dice también qué material tiene cada cuerpo y la lista de aspectos (set_appearance).")
def list_materials(sesion, query: str | None = None):
    """
    query: texto a buscar en el nombre del material (sin distinguir mayúsculas); vacío = todos.
    """
    q = (query or "").strip().casefold()
    doc = sesion.doc
    cuerpos = []
    for c in doc.estado_final.cuerpos.values():
        material = doc.propiedad(c.id, "material") or getattr(c, "material", None)
        cuerpos.append({"id": c.id, "name": sesion.nombre_cuerpo(c), "material": material,
                        "density_g_cm3": _r(an.TABLA_MATERIALES[material]["densidad"])
                        if material in an.TABLA_MATERIALES else None,
                        "appearance": (doc.propiedad(c.id, "acabado") or {}).get("nombre") or
                        (_hex(doc.propiedad(c.id, "apariencia")) if doc.propiedad(c.id, "apariencia") else None)})
    aspectos = {}
    for nombre, a in rc.BIBLIOTECA_ASPECTOS.items():
        aspectos.setdefault(a["categoria"], []).append(nombre)
    return {"materials": [_info(m) for m in an.TABLA_MATERIALES if not q or q in m.casefold()],
            "bodies": cuerpos, "appearances": aspectos,
            "custom_library_file": str(an.ruta_materiales_propios())}


@herramienta("define_material", "material", "Define un material físico propio (nombre, densidad en g/cm³ y color) "
             "para usarlo con set_material. Queda en la biblioteca del usuario (save=true: materiales.json de la "
             "carpeta de datos de OmniCAD) y sirve en todos los documentos y sesiones de esta PC. No pisa los de "
             "fábrica; uno propio con el mismo nombre se reemplaza solo con overwrite=true. No cambia el documento.")
def define_material(sesion, name: str, density: float, color: str | list[float] | None = None,
                    overwrite: bool = False, save: bool = True):
    """
    name: nombre del material (p. ej. "Goma EPDM 70 Shore").
    density: densidad en g/cm³ (agua = 1; acero = 7,85), mayor que 0.
    color: color con que se ve: «#rrggbb» o [r, g, b] (0..1 o 0..255); vacío = gris.
    overwrite: true para reemplazar un material propio que ya existe con ese nombre.
    save: true lo guarda en la biblioteca del usuario para las próximas sesiones; false, solo en esta sesión.
    """
    texto = str(name).strip()
    existente = next((m for m in an.TABLA_MATERIALES if m.casefold() == texto.casefold()), None)
    if existente in an.MATERIALES_BASE:
        raise error("NAME_EXISTS", f"«{existente}» es un material de fábrica: no se puede redefinir.",
                    "Elegí otro nombre para el material propio.")
    if existente is not None and not overwrite:
        raise error("NAME_EXISTS", f"Ya existe el material propio «{existente}» "
                    f"({an.TABLA_MATERIALES[existente]['densidad']:g} g/cm³).")
    rgb = None if color is None else color_rgb(color)
    try:
        if existente is not None and existente != texto:
            an.quitar_material(existente, guardar=save)
        nombre, _datos = an.definir_material(texto, density, rgb, guardar=save)
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", str(e)) from e
    resultado = {"material": _info(nombre), "replaced": existente is not None, "saved": bool(save)}
    if save:
        resultado["library_file"] = str(an.ruta_materiales_propios())
    return resultado


@herramienta("delete_material", "material", "Borra un material propio de la biblioteca (los de fábrica no se borran). "
             "Los cuerpos que lo tenían conservan el nombre pero quedan sin densidad hasta que se vuelva a definir.")
def delete_material(sesion, name: str, save: bool = True):
    """
    name: nombre del material propio.
    save: true también lo saca del archivo de la biblioteca; false, solo de esta sesión.
    """
    nombre = nombre_material(name)
    if nombre in an.MATERIALES_BASE:
        raise error("INVALID_ARGUMENTS", f"«{nombre}» es un material de fábrica: no se borra.")
    usos = _usos(sesion, nombre)
    an.quitar_material(nombre, guardar=save)
    if usos:
        sesion.avisar(f"Lo usan {len(usos)} cuerpo(s) de este documento ({', '.join(usos)}): quedan sin densidad.")
    return {"deleted": nombre, "bodies_using_it": usos}


@herramienta("set_material", "material", "Asigna el material físico a cuerpos (MODIFICAR › Material físico): da la "
             "densidad para la masa (get_physical_properties) y, si el cuerpo no tiene aspecto, su color. "
             "material=null quita la asignación (vuelve al material que le dio su operación, p. ej. el de la regla de "
             "chapa). list_materials lista los nombres.", modifica=True)
def set_material(sesion, bodies: list[str], material: str | None):
    """
    bodies: ids o nombres de los cuerpos.
    material: nombre del material (sin distinguir mayúsculas), p. ej. "Aluminio 6061" o "Silicona"; null lo quita.
    """
    ids = _cuerpos(sesion, bodies)
    nombre = None if material is None or not str(material).strip() else nombre_material(material)
    sesion.doc.set_propiedad(ids, "material", nombre)
    doc = sesion.doc
    salida = []
    for cid in ids:
        c = doc.estado_final.cuerpos[cid]
        actual = doc.propiedad(cid, "material") or getattr(c, "material", None)
        densidad = an.TABLA_MATERIALES[actual]["densidad"] if actual in an.TABLA_MATERIALES else None
        vol = geo.volumen(c.forma) if getattr(c, "tipo", "solido") == "solido" else None
        salida.append({"id": cid, "name": sesion.nombre_cuerpo(c), "material": actual,
                       "density_g_cm3": None if densidad is None else _r(densidad),
                       "mass_g": None if densidad is None or vol is None else _r(vol * densidad * 1e-3)})
    return {"bodies": salida}


MATERIAL_POR_DEFECTO = "Acero"     # el de un cuerpo sin material en la lista de materiales (como en Fusion y la UI)


@herramienta("get_bill_of_materials", "material", "Lista de materiales (ADMINISTRAR › Lista de materiales): las piezas "
             "sólidas del modelo agrupadas (cuerpos iguales del mismo componente y material = una fila con su "
             "cantidad), con material, masa (g) y volumen (mm³) por unidad. Como en la ventana, un cuerpo sin "
             "material cuenta como Acero (default_material=true). El patrón plano de una chapa no es una pieza. Con "
             "csv_path, la escribe además en CSV.")
def get_bill_of_materials(sesion, csv_path: str | None = None, overwrite: bool = False):
    """
    csv_path: ruta de un .csv donde escribir la lista (columnas como la de la ventana); vacío = no escribe.
    overwrite: true para reemplazar el .csv si ya existe.
    """
    from ..timeline.ops_chapa import cuerpos_del_modelo
    doc = sesion.doc
    estado = doc.estado_final
    grupos = {}
    for c in cuerpos_del_modelo(estado):
        if getattr(c, "tipo", "solido") != "solido":
            continue
        asignado = doc.propiedad(c.id, "material") or getattr(c, "material", None)
        material = asignado or MATERIAL_POR_DEFECTO
        vol = geo.volumen(c.forma)
        comp = str(estado.componentes.get(c.componente, {}).get("nombre", "")) if c.componente else ""
        base = sesion.nombre_cuerpo(c).split(" (")[0]
        clave = (comp or base, round(vol, 3), round(geo.area(c.forma), 3), material)
        g = grupos.setdefault(clave, {"name": comp or base, "quantity": 0, "material": material,
                                      "default_material": asignado is None, "volume": vol, "component": comp,
                                      "bodies": []})
        g["quantity"] += 1
        g["bodies"].append(c.id)
    filas = []
    for i, g in enumerate(sorted(grupos.values(), key=lambda g: g["name"]), 1):
        densidad = an.TABLA_MATERIALES.get(g["material"], {}).get("densidad")
        masa = None if densidad is None else g["volume"] * densidad * 1e-3
        filas.append({"item": i, "name": g["name"], "quantity": g["quantity"], "material": g["material"],
                      "default_material": g["default_material"], "mass_g": None if masa is None else _r(masa),
                      "volume": _r(g["volume"]), "component": g["component"], "bodies": g["bodies"]})
    sin = [f["material"] for f in filas if f["mass_g"] is None]
    if sin:
        sesion.avisar(f"Materiales sin densidad (no están en la tabla): {', '.join(dict.fromkeys(sin))}.")
    total = sum(f["mass_g"] * f["quantity"] for f in filas if f["mass_g"] is not None)
    resultado = {"rows": filas, "pieces": sum(f["quantity"] for f in filas),
                 "total_mass_g": None if sin else _r(total), "units": {"mass": "g", "volume": "mm3"}}
    if csv_path is not None and str(csv_path).strip():
        import csv
        import io
        from pathlib import Path
        ruta = Path(csv_path)
        if ruta.exists() and not overwrite:
            raise error("FILE_EXISTS", f"Ya existe el archivo: {ruta}")
        if not ruta.parent.is_dir():
            raise error("FILE_NOT_FOUND", f"No existe la carpeta: {ruta.parent}")
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["N.º", "Nombre", "Cantidad", "Material", "Masa (g)", "Volumen (mm³)"])
        for f in filas:
            w.writerow([f["item"], f["name"], f["quantity"], f["material"],
                        "" if f["mass_g"] is None else f"{f['mass_g']:.3f}", f"{f['volume']:.3f}"])
        ruta.write_bytes(buf.getvalue().encode("utf-8"))   # bytes: en Windows write_text duplicaba el retorno de carro
        resultado["csv_path"] = str(ruta.resolve())
    return resultado


@herramienta("set_appearance", "material", "Cambia cómo se ven cuerpos (MODIFICAR › Aspecto): un aspecto de la "
             "biblioteca (appearance, p. ej. 'Aluminio - Anodizado (rojo)'; list_materials los lista por categoría) "
             "y/o un color propio (color «#rrggbb» o [r, g, b]). Con los dos, el acabado del aspecto con ese color. Sin "
             "ninguno, quita el aspecto (vuelve al color del material). No cambia la masa.", modifica=True)
def set_appearance(sesion, bodies: list[str], appearance: str | None = None, color: str | list[float] | None = None):
    """
    bodies: ids o nombres de los cuerpos.
    appearance: nombre de un aspecto de la biblioteca (sin distinguir mayúsculas); vacío = solo el color.
    color: color propio «#rrggbb» o [r, g, b] (0..1 o 0..255); vacío = el del aspecto.
    """
    ids = _cuerpos(sesion, bodies)
    acabado, rgb = None, None
    if appearance is not None and str(appearance).strip():
        texto = str(appearance).strip()
        nombre = next((a for a in rc.BIBLIOTECA_ASPECTOS if a.casefold() == texto.casefold()), None)
        if nombre is None:
            parecidos = difflib.get_close_matches(texto, list(rc.BIBLIOTECA_ASPECTOS), n=3, cutoff=0.4)
            raise error("NOT_FOUND", f"No existe el aspecto «{texto}».",
                        *([f"¿Quisiste decir: {', '.join(parecidos)}?"] if parecidos else []),
                        "list_materials devuelve los aspectos por categoría (appearances).")
        rgb, acabado = rc.aspecto(nombre)
    if color is not None:
        rgb = color_rgb(color)
    doc = sesion.doc
    doc.set_propiedad(ids, "apariencia", None if rgb is None else [float(x) for x in rgb])
    doc.set_propiedad(ids, "acabado", acabado)
    return {"bodies": [{"id": cid, "name": sesion.nombre_cuerpo(doc.estado_final.cuerpos[cid]),
                        "color": None if rgb is None else _hex(rgb),
                        "appearance": None if acabado is None else acabado.get("nombre")} for cid in ids],
            "cleared": rgb is None}
