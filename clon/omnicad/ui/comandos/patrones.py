# -*- coding: utf-8 -*-
"""Patrones de SÓLIDO › CREAR que se agregan a los de `crear.py`: Patrón en puntos y Multitransformación (patrón +
simetría + patrón en un solo paso, como el MultiTransform de FreeCAD). Los dos repiten cuerpos u operaciones."""
from ...timeline.ops_solido import OpMultitransformar
from ...timeline.parametros import ANGULO
from ..comando import Casilla, Comando, Entero, ErrorComando, Expresion, Info, Opciones, Seleccion, ref1
from . import registrar
from .crear import _h1, _Patron, _de_cuerpos, campos_objeto, objeto_params, objeto_valores

RANURAS = 4                                     # transformaciones apilables en el diálogo
TIPOS_RANURA = {"ninguna": "—", "rectangular": "Patrón rectangular", "circular": "Patrón circular",
                "simetria": "Simetría"}
DISTRIBUCIONES = {"extension": "Extensión / completo", "espaciado": "Espaciado / entre copias"}
DIRECCION = {"eje", "arista_lineal", "plano", "cara_plana"}


class PatronPuntos(_Patron):
    CLAVE, TITULO, ICONO, FORMA = "patron_puntos", "Patrón en puntos", "patron_puntos", "puntos"
    AYUDA = "Copias de cuerpos u operaciones en cada punto elegido (puntos de boceto, vértices o puntos de construcción)."
    VARIANTE = ("forma_patron", "puntos")


def _es(k, *tipos):
    return lambda v: v.get(f"t{k}_tipo", "ninguna") in tipos


def _ranura_desde(t):
    """Valores de una ranura del diálogo desde una transformación guardada; None si el diálogo no la puede mostrar
    (en ruta, en puntos o rectangular en dos direcciones: se crean desde la API)."""
    tipo = t.get("tipo")
    if tipo == "rectangular" and not t.get("dir2"):
        return {"tipo": tipo, "dir": t.get("dir1"), "n": t.get("n1", 3), "d": t.get("d1", "30 mm"),
                "distribucion": t.get("distribucion", "extension")}
    if tipo == "circular":
        return {"tipo": tipo, "eje": t.get("eje"), "n": t.get("n", 6), "angulo": t.get("angulo", "360 deg"),
                "distribucion": t.get("distribucion", "extension")}
    if tipo == "simetria":
        return {"tipo": tipo, "plano": t.get("plano")}
    return None


class Multitransformar(Comando):
    CLAVE, TITULO, ICONO = "multitransformar", "Multitransformación", "multitransformar"
    AYUDA = ("Patrones y simetrías encadenados en un solo paso: cada transformación se aplica a todas las copias de "
             "las anteriores (patrón de 3 + simetría = 6).")
    CLASE_OP = OpMultitransformar

    def campos(self, ctx):
        campos = campos_objeto()
        fijas = Info("fijas", "Transformaciones", lambda v, c: (
            f"{len(v['_fijas'])} transformaciones creadas desde la API (en ruta, en puntos o en dos direcciones): el "
            "diálogo no las edita y Aceptar las conserva." if v.get("_fijas") else ""),
            visible_si=lambda v: bool(v.get("_fijas")))
        campos.append(fijas)
        for k in range(1, RANURAS + 1):
            libre = (lambda v, k=k: not v.get("_fijas") and (k == 1 or v.get(f"t{k - 1}_tipo", "ninguna") != "ninguna"))
            campos += [
                Opciones(f"t{k}_tipo", f"Transformación {k}", TIPOS_RANURA, "rectangular" if k == 1 else "ninguna",
                         visible_si=libre),
                Seleccion(f"t{k}_dir", "   Dirección", DIRECCION,
                          visible_si=lambda v, k=k, f=_es(k, "rectangular"): f(v) and not v.get("_fijas")),
                Seleccion(f"t{k}_eje", "   Eje", {"eje"},
                          visible_si=lambda v, k=k, f=_es(k, "circular"): f(v) and not v.get("_fijas")),
                Seleccion(f"t{k}_plano", "   Plano de simetría", {"plano", "cara_plana"},
                          visible_si=lambda v, k=k, f=_es(k, "simetria"): f(v) and not v.get("_fijas")),
                Opciones(f"t{k}_distribucion", "   Distribución", DISTRIBUCIONES,
                         visible_si=lambda v, k=k, f=_es(k, "rectangular", "circular"): f(v) and not v.get("_fijas")),
                Entero(f"t{k}_n", "   Cantidad", 3, 1,
                       visible_si=lambda v, k=k, f=_es(k, "rectangular", "circular"): f(v) and not v.get("_fijas")),
                Expresion(f"t{k}_d", "   Distancia", "30 mm",
                          visible_si=lambda v, k=k, f=_es(k, "rectangular"): f(v) and not v.get("_fijas")),
                Expresion(f"t{k}_angulo", "   Ángulo", "360 deg", ANGULO,
                          visible_si=lambda v, k=k, f=_es(k, "circular"): f(v) and not v.get("_fijas"))]
        return campos + [Casilla("combinar", "Unir al original", visible_si=_de_cuerpos)]

    def construir(self, v, ctx):
        objeto = objeto_params(v, ctx)
        lista = list(v.get("_fijas") or [])
        if not lista:
            for k in range(1, RANURAS + 1):
                tipo = v.get(f"t{k}_tipo", "ninguna")
                if tipo == "ninguna":
                    break
                if tipo == "rectangular":
                    if not v.get(f"t{k}_dir"):
                        raise ErrorComando(f"Transformación {k}: seleccioná la dirección.")
                    lista.append({"tipo": tipo, "dir1": ref1(v, f"t{k}_dir"), "n1": v.get(f"t{k}_n", 3),
                                  "d1": v.get(f"t{k}_d", "30 mm"),
                                  "distribucion": v.get(f"t{k}_distribucion", "extension")})
                elif tipo == "circular":
                    if not v.get(f"t{k}_eje"):
                        raise ErrorComando(f"Transformación {k}: seleccioná el eje.")
                    lista.append({"tipo": tipo, "eje": ref1(v, f"t{k}_eje"), "n": v.get(f"t{k}_n", 3),
                                  "angulo": v.get(f"t{k}_angulo", "360 deg"),
                                  "distribucion": v.get(f"t{k}_distribucion", "extension")})
                else:
                    if not v.get(f"t{k}_plano"):
                        raise ErrorComando(f"Transformación {k}: seleccioná el plano de simetría.")
                    lista.append({"tipo": "simetria", "plano": ref1(v, f"t{k}_plano")})
        if not lista:
            raise ErrorComando("Elegí al menos una transformación.")
        return self.crear_op(OpMultitransformar, v, ctx, transformaciones=lista, combinar=bool(v.get("combinar")),
                             **objeto)

    def desde_op(self, op, ctx):
        v = dict(objeto_valores(op, ctx), combinar=op.p.get("combinar", False))
        lista = op.p.get("transformaciones") or []
        ranuras = [_ranura_desde(t) for t in lista]
        if len(lista) > RANURAS or any(r is None for r in ranuras):
            v["_fijas"] = [dict(t) for t in lista]
            return v
        for k in range(1, RANURAS + 1):
            r = ranuras[k - 1] if k <= len(ranuras) else {"tipo": "ninguna"}
            v[f"t{k}_tipo"] = r["tipo"]
            for clave in ("dir", "eje", "plano"):
                v[f"t{k}_{clave}"] = _h1(r.get(clave), ctx.estado)
            for clave in ("n", "d", "angulo", "distribucion"):
                if clave in r:
                    v[f"t{k}_{clave}"] = r[clave]
        return v


registrar(PatronPuntos, Multitransformar)
