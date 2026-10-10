# -*- coding: utf-8 -*-
"""
INSERTAR › Insertar fijación de Fusion [SLD-INSERT-FASTENER, SLD-REF-INSERT-FASTENER] como paso del
timeline: una fijación de la biblioteca (`nucleo.fijaciones`) en cada posición elegida — arista circular de
un agujero, cara cilíndrica o cónica, o punto (+ dirección). Como en Fusion, varias posiciones dan varias
copias en un solo paso, y «Seleccionar similares» agrega los agujeros iguales de la misma cara.
"""
import numpy as np

from ..nucleo import fijaciones as fj
from ..nucleo import geometria as geo
from ..nucleo.analisis import TABLA_MATERIALES
from . import entidades as ent
from .operaciones import ErrorOperacion, Operacion, _resolver, registrar_operacion

AUTO = "auto"


def _apoyos(p, estado):
    """[{"punto", "direccion", "diametro", "interior", "cuerpo"}] de las posiciones elegidas."""
    voltear = bool(p.get("voltear"))
    extra = ent.direccion(_resolver(p["direccion"], estado)) if p.get("direccion") else None
    salida = []
    for ref in p.get("posiciones") or []:
        e = _resolver(ref, estado)
        cuerpo = estado.cuerpo(e.cuerpo).forma if e.cuerpo else None
        if e.tipo == "arista" and cuerpo is not None and (ref.get("firma") or {}).get("geom") == "circulo":
            aristas = fj.aristas_similares(cuerpo, e.forma) if p.get("similares") else [e.forma]
            for a in aristas:
                ap = fj.apoyo_arista(cuerpo, a)
                if voltear:
                    ap["direccion"] = -ap["direccion"]
                salida.append(dict(ap, cuerpo=cuerpo))
        elif e.tipo == "cara" and cuerpo is not None:
            salida.append(dict(fj.apoyo_cara(cuerpo, e.forma, otro_extremo=voltear), cuerpo=cuerpo))
        elif e.tipo in ("vertice", "punto", "punto_boceto") and e.punto is not None:
            d = extra if extra is not None else (e.plano.normal if e.plano is not None else np.array([0.0, 0.0, 1.0]))
            d = np.asarray(d, float) * (-1 if voltear else 1)
            salida.append({"punto": np.asarray(e.punto, float), "direccion": d, "diametro": None, "interior": True,
                           "cuerpo": cuerpo})
        else:
            raise ErrorOperacion("Para colocar una fijación elegí una arista circular, una cara cilíndrica o cónica "
                                 "o un punto.")
    unicos = []
    for ap in salida:                              # la misma posición elegida dos veces da una sola fijación
        if not any(np.allclose(ap["punto"], u["punto"], atol=1e-6) and np.allclose(ap["direccion"], u["direccion"])
                   for u in unicos):
            unicos.append(ap)
    return unicos


def resolver_fijacion(p, estado):
    """Lo que la operación va a insertar: {"norma", "tamano", "largo", "apoyos", "avisos", "coincidencia"}.
    Resuelve el tamaño y el largo automáticos y corrige los que la norma no tiene (con aviso)."""
    familia, norma = p.get("familia", "tornillo"), p.get("norma", "")
    try:
        if norma not in fj.normas(familia):
            raise ErrorOperacion(f"{norma} no es una norma de {fj.FAMILIAS[familia].lower()}.")
    except geo.ErrorGeometria as e:
        raise ErrorOperacion(str(e)) from e
    apoyos = _apoyos(p, estado)
    avisos, coincidencia = [], None
    tamano = p.get("tamano") or AUTO
    if tamano == AUTO:
        con_diametro = next((a for a in apoyos if a["diametro"]), None)
        if con_diametro is None:
            tamano = "M6" if "M6" in fj.tamanos(norma) else fj.tamanos(norma)[0]
            if apoyos:
                avisos.append(f"Sin agujero de referencia para el tamaño automático: se usó {tamano}.")
        else:
            tamano, coincidencia = fj.tamano_para_agujero(norma, con_diametro["diametro"],
                                                          interior=con_diametro["interior"])
            if coincidencia is None:
                avisos.append(f"El agujero de Ø{con_diametro['diametro']:.4g} mm no coincide con ningún paso de "
                              f"{norma}: se usó {tamano}.")
    largo = p.get("largo") or AUTO
    if not fj.lleva_largo(norma):
        largo = None
    elif largo != AUTO:
        try:
            largo = float(largo)
        except (TypeError, ValueError):
            raise ErrorOperacion(f"Largo inválido: {largo}") from None
    tamano, largo_ok, corr = fj.corregir(norma, tamano, None if largo == AUTO else largo)
    avisos += corr
    if largo == AUTO:
        ap = apoyos[0] if apoyos else None
        espesor = None
        if ap is not None and ap["cuerpo"] is not None:
            espesor = fj.espesor_material(ap["cuerpo"], ap["punto"], ap["direccion"], (ap["diametro"] or 0) / 2)
        largo_ok = fj.largo_para_espesor(norma, tamano, espesor)
    return {"familia": familia, "norma": norma, "tamano": tamano, "largo": largo_ok, "apoyos": apoyos,
            "avisos": avisos, "coincidencia": coincidencia}


class OpFijacion(Operacion):
    """Insertar fijación de Fusion [SLD-INSERT-FASTENER]: posición (aristas circulares, caras cilíndricas o
    cónicas, puntos con dirección opcional), «Seleccionar similares», familia y norma, tamaño nominal y largo
    (automáticos o elegidos), rosca cosmética o modelada, voltear y material. Crea un cuerpo sólido por
    posición, con el nombre de la designación («ISO 4762 M6x20»)."""
    TIPO, ETIQUETA, ICONO = "fijacion", "Fijación", "⚲"
    PARAMS = {"posiciones": [], "direccion": None, "similares": True, "familia": "tornillo", "norma": "ISO 4762",
              "tamano": AUTO, "largo": AUTO, "rosca": "cosmetica", "voltear": False, "material": "Acero"}
    OPCIONES = {"familia": fj.FAMILIAS, "rosca": fj.TIPOS_ROSCA}    # norma, tamaño, largo y material: de la biblioteca

    def dependencias(self):
        return ent.dependencias_de(self.p.get("posiciones"), self.p.get("direccion")) - {self.id}

    def ejecutar(self, estado, ctx):
        if not self.p.get("posiciones"):
            raise ErrorOperacion("Elegí dónde va la fijación: una arista circular, una cara cilíndrica o un punto.")
        r = resolver_fijacion(self.p, estado)
        for a in r["avisos"]:
            ctx.aviso(a)
        canonica = fj.generar(r["familia"], r["norma"], r["tamano"], r["largo"], rosca=self.p.get("rosca", "cosmetica"))
        nombre = fj.designacion(r["norma"], r["tamano"], r["largo"])
        material = self.p.get("material") or None
        color = TABLA_MATERIALES.get(material, {}).get("color")
        varios = len(r["apoyos"]) > 1
        for i, ap in enumerate(r["apoyos"], 1):
            estado.nuevo_cuerpo(self.id, fj.colocar(canonica, ap["punto"], ap["direccion"]), "solido",
                                nombre=f"{nombre}:{i}" if varios else nombre, material=material,
                                apariencia=list(color) if color else None)


registrar_operacion(OpFijacion)
