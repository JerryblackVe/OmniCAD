# -*- coding: utf-8 -*-
"""SÓLIDO › INSERTAR › Insertar fijación de Fusion [SLD-INSERT-FASTENER, SLD-REF-INSERT-FASTENER] con diálogo."""
from ...nucleo import fijaciones as fj
from ...nucleo.analisis import TABLA_MATERIALES
from ...timeline.ops_fijacion import AUTO, OpFijacion, resolver_fijacion
from ..comando import Casilla, Comando, Info, Opciones, Seleccion, exigir, hit_desde_ref, hits, ref1, refs
from . import registrar

_PUNTOS = ("vertice", "punto", "punto_boceto")
_LARGOS = sorted({float(x) for x in fj.SERIE_LARGOS} | {float(x) for x in fj.SERIE_VARILLA})
_MATERIALES = [m for m in ("Acero", "Acero inoxidable", "Latón", "Aluminio 6061", "Titanio", "Nylon")
               if m in TABLA_MATERIALES]


def _hay_punto(v):
    return any(h.get("tipo") in _PUNTOS for h in v.get("posiciones") or [])


def _con_largo(v):
    return v.get("familia") in ("tornillo", "varilla", "esparrago")


def _de_familia(familia):
    return lambda v: v.get("familia") == familia


def _params(v):
    """Valores del diálogo → parámetros de OpFijacion (la norma sale del campo de la familia elegida)."""
    familia = v.get("familia") or "tornillo"
    return {"posiciones": refs(v, "posiciones"), "direccion": ref1(v, "direccion") if _hay_punto(v) else None,
            "similares": bool(v.get("similares")), "familia": familia,
            "norma": v.get(f"norma_{familia}") or fj.normas(familia)[0], "tamano": v.get("tamano") or AUTO,
            "largo": (v.get("largo") or AUTO) if _con_largo(v) else AUTO, "rosca": v.get("rosca") or "cosmetica",
            "voltear": bool(v.get("voltear")), "material": v.get("material") or "Acero"}


def _propiedades(v, ctx):
    """Texto del campo «Propiedades»: designación resuelta (tamaño y largo automáticos), medidas y cantidad."""
    r = resolver_fijacion(_params(v), ctx.estado)
    texto = fj.propiedades(r["norma"], r["tamano"], r["largo"])
    if r["coincidencia"]:
        texto += f" · agujero: {r['coincidencia']}"
    n = len(r["apoyos"])
    return texto + (f" · {n} copias" if n > 1 else "")


class InsertarFijacion(Comando):
    CLAVE, TITULO, ICONO = "fijacion", "Insertar fijación", "fijacion"
    AYUDA = ("Inserta tornillos, tuercas, arandelas, varilla roscada o espárragos normalizados (ISO/DIN) en "
             "agujeros, caras cilíndricas o puntos; el tamaño se propone según el agujero.")
    CLASE_OP = OpFijacion

    def campos(self, ctx):
        campos = [
            Seleccion("posiciones", "Posición", {"arista_circular", "eje", "punto", "vertice"}, maximo=None,
                      ayuda="Aristas circulares de agujeros, caras cilíndricas o cónicas, o puntos: una fijación por "
                            "cada una."),
            Casilla("similares", "Seleccionar similares", True,
                    ayuda="Agrega los agujeros iguales de la misma cara (aristas del mismo radio en el mismo plano)."),
            Seleccion("direccion", "Dirección", {"eje", "arista_lineal", "cara_plana", "plano"}, minimo=0,
                      visible_si=_hay_punto, ayuda="Eje de la fijación en los puntos. Sin selección: la normal del "
                                                   "boceto o +Z."),
            Opciones("familia", "Familia", fj.FAMILIAS),
        ]
        for familia in fj.FAMILIAS:
            campos.append(Opciones(f"norma_{familia}", "Norma",
                                   {n: f"{n} — {fj.NORMAS[n]['descripcion']}" for n in fj.normas(familia)},
                                   visible_si=_de_familia(familia)))
        campos += [
            Opciones("tamano", "Tamaño nominal", {AUTO: "Automático", **{t: t for t in fj.TAMANOS}},
                     ayuda="Automático: según el diámetro del agujero (paso libre, broca de roscar o rosca). Un "
                           "tamaño que la norma no tiene se corrige al más cercano."),
            Opciones("largo", "Largo nominal", {AUTO: "Automático", **{f"{x:g}": f"{x:g} mm" for x in _LARGOS}},
                     visible_si=_con_largo,
                     ayuda="Automático: el menor largo de la norma que atraviesa el material. Un largo fuera de la "
                           "norma se corrige al más cercano."),
            Opciones("rosca", "Rosca", fj.TIPOS_ROSCA, visible_si=lambda v: v.get("familia") != "arandela",
                     ayuda="Modelada: corta el filete helicoidal real (más lento)."),
            Casilla("voltear", "Voltear", ayuda="Invierte el sentido de la fijación (en una cara, usa el otro "
                                                "extremo)."),
            Opciones("material", "Material", {m: m for m in _MATERIALES}),
            Info("propiedades", "Propiedades", _propiedades),
        ]
        return campos

    def construir(self, v, ctx):
        exigir(v, "posiciones", "Seleccioná dónde va la fijación: una arista circular, una cara cilíndrica o un "
                                "punto.")
        return self.crear_op(OpFijacion, v, ctx, **_params(v))

    def desde_op(self, op, ctx):
        v = dict(op.p)
        v["posiciones"] = hits(op.p.get("posiciones"), ctx.estado)
        v["direccion"] = [hit_desde_ref(op.p["direccion"], ctx.estado)] if op.p.get("direccion") else []
        v[f"norma_{op.p.get('familia', 'tornillo')}"] = op.p.get("norma")
        return v


registrar(InsertarFijacion)
