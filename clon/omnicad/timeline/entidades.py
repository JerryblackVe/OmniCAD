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
import json
import numbers

import numpy as np

from ..nucleo import geometria as geo
from ..nucleo import referencias as refs
from ..nucleo.perfiles import aristas_boceto, buscar_por_firma

EJES_ORIGEN = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}
NOMBRES_ORIGEN = {"XY": "Plano XY", "XZ": "Plano XZ", "YZ": "Plano YZ", "X": "Eje X", "Y": "Eje Y", "Z": "Eje Z",
                  "O": "Origen"}


class ErrorReferencia(RuntimeError):
    pass


class ReferenciaMalFormada(ErrorReferencia):
    """La referencia no tiene la forma de la tabla de arriba (texto, None, dict sin «tipo» o sin sus claves).
    `valor` es lo que llegó: las operaciones lo usan para nombrar el campo del paso que está mal."""

    def __init__(self, valor, detalle):
        self.valor, self.detalle = valor, detalle
        super().__init__(f"Referencia mal formada: llegó {describir_valor(valor)}; {detalle}")


def describir_valor(valor):
    """Texto corto de un valor recibido, para los mensajes de error («el texto 'x'», JSON si no)."""
    if isinstance(valor, str):
        return f"el texto {valor[:40]!r}"
    try:
        texto = json.dumps(valor, ensure_ascii=False)
    except (TypeError, ValueError):
        texto = repr(valor)
    return texto if len(texto) <= 70 else texto[:69] + "…"


# Claves obligatorias de cada tipo de referencia (con su tipo) y un ejemplo para los mensajes de error.
_CLAVES = {
    "cara": (("cuerpo", str), ("firma", dict)), "arista": (("cuerpo", str), ("firma", dict)),
    "vertice": (("cuerpo", str), ("firma", dict)), "cuerpo": (("cuerpo", str),),
    "plano": (("id", str),), "eje": (("id", str),), "punto": (("id", str),),
    "perfil": (("boceto", str), ("firma", (list, tuple))), "curva_boceto": (("boceto", str), ("curva", int)),
    "punto_boceto": (("boceto", str), ("punto", int)), "boceto": (("boceto", str),),
}
_EJEMPLOS = {
    "cara": '{"tipo": "cara", "cuerpo": "op1.c1", "firma": {"geom": "plano", …}}',
    "arista": '{"tipo": "arista", "cuerpo": "op1.c1", "firma": {"geom": "linea", …}}',
    "vertice": '{"tipo": "vertice", "cuerpo": "op1.c1", "firma": {"geom": "punto", …}}',
    "cuerpo": '{"tipo": "cuerpo", "cuerpo": "op1.c1"}', "plano": '{"tipo": "plano", "id": "XY"}',
    "eje": '{"tipo": "eje", "id": "Z"}', "punto": '{"tipo": "punto", "id": "O"}',
    "perfil": '{"tipo": "perfil", "boceto": "op1", "firma": […]}',
    "curva_boceto": '{"tipo": "curva_boceto", "boceto": "op1", "curva": 1}',
    "punto_boceto": '{"tipo": "punto_boceto", "boceto": "op1", "punto": 1}',
    "boceto": '{"tipo": "boceto", "boceto": "op1"}',
}
_NOMBRE_TIPO = {str: "texto", dict: "un dict", int: "un entero"}


def validar(ref):
    """Comprueba la FORMA de una referencia (no que exista lo que nombra). Lanza ReferenciaMalFormada."""
    tipos = ", ".join(_CLAVES)
    if not isinstance(ref, dict):
        raise ReferenciaMalFormada(ref, f"se esperaba una referencia como {_EJEMPLOS['punto']} o "
                                        f"{_EJEMPLOS['cuerpo']} (tipos: {tipos})")
    t = ref.get("tipo")
    if not isinstance(t, str) or t not in _CLAVES:
        raise ReferenciaMalFormada(ref, f"«tipo» tiene que ser uno de: {tipos}")
    for clave, tipo in _CLAVES[t]:
        if not isinstance(ref.get(clave), tipo):
            raise ReferenciaMalFormada(ref, f"a la referencia «{t}» le falta «{clave}» "
                                            f"({_NOMBRE_TIPO.get(tipo, 'una lista')}): se esperaba como {_EJEMPLOS[t]}")
    if t in _FIRMA:
        detalle = _problema_firma(t, ref["firma"])
    elif t == "perfil":
        detalle = problema_perfil(ref)
    else:
        detalle = None
    if detalle:
        raise ReferenciaMalFormada(ref, detalle)


def _es_numero(v):
    return isinstance(v, numbers.Real) and not isinstance(v, bool)


def _es_lista_de_numeros(v, n):
    return isinstance(v, (list, tuple, np.ndarray)) and len(v) == n and all(_es_numero(x) for x in v)


_FORMAS_FIRMA = {
    "numero": ("un número", _es_numero),
    "punto": ("[x, y, z]", lambda v: _es_lista_de_numeros(v, 3)),
    "extremos": ("[[x, y, z], [x, y, z]]",
                 lambda v: isinstance(v, (list, tuple)) and len(v) == 2 and all(_es_lista_de_numeros(p, 3) for p in v)),
}
# Claves de la firma de una subforma que lee nucleo/referencias._distancia: las obligatorias por tipo y las que
# solo algunas geometrías tienen (normal de un plano, eje y radio de un cilindro, «rel» de la caja…).
_FIRMA = {"cara": (("centro", "punto"), ("area", "numero")),
          "arista": (("medio", "punto"), ("largo", "numero"), ("extremos", "extremos")),
          "vertice": (("punto", "punto"),)}
_FIRMA_OPCIONAL = (("rel", "punto"), ("normal", "punto"), ("eje", "punto"), ("radio", "numero"), ("centro", "punto"))


def _problema_firma(t, firma):
    """Qué le falta a la firma de una cara, arista o vértice (None si está completa)."""
    if not isinstance(firma.get("geom"), str):
        return f"la «firma» de la referencia «{t}» no tiene «geom» (texto): se esperaba como {_EJEMPLOS[t]}"
    for clave, forma in _FIRMA[t]:
        if not _FORMAS_FIRMA[forma][1](firma.get(clave)):
            return (f"a la «firma» de la referencia «{t}» le falta «{clave}» ({_FORMAS_FIRMA[forma][0]}); conviene "
                    "copiar la referencia entera de find_faces / find_edges o de la selección, no armarla a mano")
    for clave, forma in _FIRMA_OPCIONAL:
        if clave in firma and not _FORMAS_FIRMA[forma][1](firma[clave]):
            return f"en la «firma» de la referencia «{t}», «{clave}» tiene que ser {_FORMAS_FIRMA[forma][0]}"
    return None


def problema_perfil(ref):
    """Qué está mal en un perfil de boceto ({"firma": [ids de curva], "centroide": [u, v]}; None si nada)."""
    if not isinstance(ref, dict):
        return 'se esperaba un perfil del boceto como {"firma": [1, 2, 3], "centroide": [u, v]}'
    firma = ref.get("firma")
    if not isinstance(firma, (list, tuple)) or not all(isinstance(c, numbers.Integral) and not isinstance(c, bool)
                                                       for c in firma):
        return 'la «firma» del perfil tiene que ser la lista de ids de sus curvas (enteros), p. ej. [1, 2, 3]'
    if ref.get("centroide") is not None and not _es_lista_de_numeros(ref["centroide"], 2):
        return "el «centroide» del perfil tiene que ser [u, v] (dos números)"
    return None


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
    validar(ref)
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
    """Resuelve una lista de referencias (None = vacía). Las subformas del mismo cuerpo no se repiten."""
    if lista is not None and not isinstance(lista, (list, tuple)):
        raise ReferenciaMalFormada(lista, "se esperaba una lista de referencias")
    salida = []
    for ref in lista or []:
        ent = resolver(ref, estado)
        if ent.forma is not None and ent.tipo in ("cara", "arista", "vertice") and any(
                e.forma is not None and e.forma.IsSame(ent.forma) for e in salida):
            continue
        salida.append(ent)
    return salida


def dependencias(ref):
    """Ids de operaciones de las que depende la referencia. Con un valor mal formado devuelve lo que se pueda
    (o nada): el error con el campo lo da la ejecución del paso, no esto."""
    if not isinstance(ref, dict):
        return set()
    t = ref.get("tipo")
    if t in ("cara", "arista", "vertice", "cuerpo"):
        cid = ref.get("cuerpo")
        return {cid.split(".c")[0]} if cid and isinstance(cid, str) else set()
    if t in ("plano", "eje", "punto"):
        i = ref.get("id")
        if not i or not isinstance(i, str):
            return set()
        # los planos/ejes/puntos de un SCU llevan sufijo: "op7_xy" depende de "op7"
        return set() if i in geo.Plano.DEFINICIONES or i in EJES_ORIGEN or i == "O" else {i.split("_")[0]}
    if t in ("perfil", "curva_boceto", "punto_boceto", "boceto"):
        b = ref.get("boceto")
        return {b} if b and isinstance(b, str) else set()
    return set()


def dependencias_de(*listas):
    deps = set()
    for lista in listas:
        if isinstance(lista, dict):
            lista = [lista]
        if not isinstance(lista, (list, tuple)):
            continue
        for ref in lista:
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
