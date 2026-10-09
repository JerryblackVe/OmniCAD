# -*- coding: utf-8 -*-
"""
Referencias de las operaciones a lo que el usuario elige en la vista 3D (las "selecciones" de los
diálogos de Fusion) y su resolución en cada recálculo.

Tipos de referencia (dicts serializables):
  - {"tipo": "cara"|"arista"|"vertice", "cuerpo": id, "firma": {...}}   subforma de un cuerpo
  - {"tipo": "cuerpo", "cuerpo": id}
  - {"tipo": "plano", "id": "XY"|"XZ"|"YZ"|id de operación}             plano de origen o de construcción
  - {"tipo": "eje", "id": "X"|"Y"|"Z"|id}                               eje de origen o de construcción
  - {"tipo": "punto", "id": "O"|id}                                     punto de origen o de construcción
  - {"tipo": "perfil", "boceto": id, "firma": [...], "centroide": [u, v]}
  - {"tipo": "curva_boceto", "boceto": id, "curva": n}
  - {"tipo": "punto_boceto", "boceto": id, "punto": n}
  - {"tipo": "boceto", "boceto": id}
`resolver` devuelve una `Entidad` con lo que cada operación necesita (forma OCC, plano, eje o
punto) y `dependencias` dice de qué pasos del timeline depende la referencia.
"""
import numpy as np

from ..nucleo import geometria as geo
from ..nucleo import referencias as refs
from ..nucleo.perfiles import aristas_boceto, buscar_por_firma

EJES_ORIGEN = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}
NOMBRES_ORIGEN = {"XY": "Plano XY", "XZ": "Plano XZ", "YZ": "Plano YZ", "X": "Eje X", "Y": "Eje Y", "Z": "Eje Z",
                  "O": "Origen"}


class ErrorReferencia(RuntimeError):
    pass


class Entidad:
    """Resultado de resolver una referencia. Solo se llenan los campos que tienen sentido."""

    def __init__(self, tipo, forma=None, cuerpo=None, plano=None, eje=None, punto=None, boceto=None, perfil=None):
        self.tipo, self.forma, self.cuerpo = tipo, forma, cuerpo
        self.plano, self.eje, self.punto, self.boceto, self.perfil = plano, eje, punto, boceto, perfil

    def __repr__(self):
        return f"Entidad({self.tipo})"


def _cuerpo(estado, cid):
    if cid not in estado.cuerpos:
        raise ErrorReferencia(f"El cuerpo «{cid}» ya no existe en este punto del timeline.")
    return estado.cuerpos[cid]


def _boceto(estado, bid):
    br = estado.bocetos.get(bid)
    if br is None:
        raise ErrorReferencia("El boceto de referencia no está disponible (¿borrado, suprimido o después del marcador?).")
    return br


def resolver(ref, estado):
    t = ref["tipo"]
    if t in ("cara", "arista", "vertice"):
        cuerpo = _cuerpo(estado, ref["cuerpo"])
        sub = refs.resolver(cuerpo.forma, ref)
        if sub is None:
            raise ErrorReferencia(f"Se perdió la referencia a una {t} de {cuerpo.nombre}: la geometría cambió "
                                  "demasiado. Editá la operación y volvé a elegirla.")
        ent = Entidad(t, forma=sub, cuerpo=cuerpo.id)
        if t == "cara":
            ent.plano = geo.plano_de_cara(sub)
        elif t == "vertice":
            ent.punto = refs.punto_de_vertice(sub)
        elif t == "arista" and ref["firma"]["geom"] == "linea":
            a, b = (np.array(p) for p in refs.firma_arista(sub)["extremos"])
            ent.eje = (a, geo_dir(b - a))
        return ent
    if t == "cuerpo":
        c = _cuerpo(estado, ref["cuerpo"])
        return Entidad(t, forma=c.forma, cuerpo=c.id)
    if t == "plano":
        i = ref["id"]
        if i in geo.Plano.DEFINICIONES:
            return Entidad(t, plano=geo.Plano(i))
        if i not in estado.planos:
            raise ErrorReferencia("El plano de construcción de referencia no está disponible.")
        return Entidad(t, plano=estado.planos[i])
    if t == "eje":
        i = ref["id"]
        if i in EJES_ORIGEN:
            return Entidad(t, eje=(np.zeros(3), np.array(EJES_ORIGEN[i])))
        if i not in estado.ejes:
            raise ErrorReferencia("El eje de construcción de referencia no está disponible.")
        p, d, _ = estado.ejes[i]
        return Entidad(t, eje=(np.asarray(p, float), np.asarray(d, float)))
    if t == "punto":
        i = ref["id"]
        if i == "O":
            return Entidad(t, punto=np.zeros(3))
        if i not in estado.puntos:
            raise ErrorReferencia("El punto de construcción de referencia no está disponible.")
        return Entidad(t, punto=np.asarray(estado.puntos[i][0], float))
    if t == "perfil":
        br = _boceto(estado, ref["boceto"])
        perfil = buscar_por_firma(br.perfiles, ref["firma"], ref.get("centroide"))
        if perfil is None:
            raise ErrorReferencia("Un perfil seleccionado ya no existe en el boceto (cambió su contorno).")
        return Entidad(t, forma=perfil.cara, plano=br.plano, boceto=br, perfil=perfil)
    if t == "curva_boceto":
        br = _boceto(estado, ref["boceto"])
        geom = [g for g in br.boceto.geometria(incluir_construccion=True) if g[1] == ref["curva"]]
        aristas = aristas_boceto(geom, br.plano)
        if not aristas:
            raise ErrorReferencia("La curva del boceto ya no existe.")
        ent = Entidad(t, forma=aristas[0][1], plano=br.plano, boceto=br)
        if geom[0][0] == "linea":
            a, b = br.plano.a_3d(*geom[0][2]), br.plano.a_3d(*geom[0][3])
            ent.eje = (a, geo_dir(b - a))
        return ent
    if t == "punto_boceto":
        br = _boceto(estado, ref["boceto"])
        if ref["punto"] not in br.boceto.puntos:
            raise ErrorReferencia("El punto del boceto ya no existe.")
        return Entidad(t, punto=br.plano.a_3d(*br.boceto.coords(ref["punto"])), plano=br.plano, boceto=br)
    if t == "boceto":
        br = _boceto(estado, ref["boceto"])
        return Entidad(t, plano=br.plano, boceto=br)
    raise ErrorReferencia(f"Tipo de referencia desconocido: {t}")


def geo_dir(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise ErrorReferencia("La dirección elegida tiene largo cero.")
    return v / n


def resolver_todas(lista, estado):
    """Resuelve una lista de referencias. Las subformas del mismo cuerpo no se repiten."""
    salida = []
    for ref in lista or []:
        ent = resolver(ref, estado)
        if ent.forma is not None and ent.tipo in ("cara", "arista", "vertice") and any(
                e.forma is not None and e.forma.IsSame(ent.forma) for e in salida):
            continue
        salida.append(ent)
    return salida


def dependencias(ref):
    """Ids de operaciones de las que depende la referencia."""
    t = ref.get("tipo")
    if t in ("cara", "arista", "vertice", "cuerpo"):
        cid = ref.get("cuerpo") or ""
        return {cid.split(".c")[0]} if cid else set()
    if t in ("plano", "eje", "punto"):
        i = ref.get("id")
        # los planos/ejes/puntos de un SCU llevan sufijo: "op7_xy" depende de "op7"
        return set() if i in geo.Plano.DEFINICIONES or i in EJES_ORIGEN or i == "O" or not i else {i.split("_")[0]}
    if t in ("perfil", "curva_boceto", "punto_boceto", "boceto"):
        return {ref["boceto"]}
    return set()


def dependencias_de(*listas):
    deps = set()
    for lista in listas:
        if isinstance(lista, dict):
            lista = [lista]
        for ref in lista or []:
            if ref:
                deps |= dependencias(ref)
    return deps


# ---------------------------------------------------------------- conversiones útiles para las operaciones
def como_plano(ent):
    if ent.plano is not None and ent.tipo in ("plano", "cara", "boceto"):
        return ent.plano
    raise ErrorReferencia("Se esperaba un plano o una cara plana.")


def como_eje(ent):
    """(punto, dirección) de un eje, una arista lineal, una línea de boceto o una cara cilíndrica/cónica."""
    if ent.eje is not None:
        return ent.eje
    if ent.tipo == "cara" and ent.forma is not None:
        f = refs.firma_cara(ent.forma)
        if "eje" in f:
            from OCP.BRepAdaptor import BRepAdaptor_Surface
            s = BRepAdaptor_Surface(ent.forma)
            ax = s.Cylinder().Axis() if f["geom"] == "cilindro" else s.Cone().Axis()
            p, d = ax.Location(), ax.Direction()
            return np.array([p.X(), p.Y(), p.Z()]), np.array([d.X(), d.Y(), d.Z()])
        if ent.plano is not None:
            return ent.plano.origen, ent.plano.normal
    if ent.tipo == "plano" and ent.plano is not None:
        return ent.plano.origen, ent.plano.normal
    raise ErrorReferencia("Se esperaba un eje, una arista recta, una línea o una cara cilíndrica.")


def como_punto(ent):
    if ent.punto is not None:
        return np.asarray(ent.punto, float)
    if ent.forma is not None:
        return np.array(geo.centro_masa(ent.forma, superficie=ent.tipo != "cuerpo") if ent.tipo != "arista"
                        else refs.firma_arista(ent.forma)["medio"])
    if ent.plano is not None:
        return ent.plano.origen
    raise ErrorReferencia("Se esperaba un punto.")


def direccion(ent):
    """Dirección de un eje, arista recta, normal de una cara plana o de un plano."""
    if ent.eje is not None:
        return ent.eje[1]
    if ent.plano is not None:
        return ent.plano.normal
    return como_eje(ent)[1]
