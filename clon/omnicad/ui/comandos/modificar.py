# -*- coding: utf-8 -*-
"""Comandos de SÓLIDO › MODIFICAR con diálogo al estilo Fusion."""
from ...nucleo.analisis import TABLA_MATERIALES as MATERIALES
from ...timeline.operaciones import OPERACIONES_COMBINAR, OpCombinar
from ...timeline.ops_modificar import (TIPOS_MOVIMIENTO, OpAlinear, OpApoyar, OpBorrarCaras, OpChaflan, OpDesfaseAristas,
                                       OpDesfaseCara,
                                       OpQuitar, OpQuitarEmpalmes,
                                       OpDesmoldeo, OpDivisionSilueta, OpDividirCara, OpDividirCuerpo, OpEmpalme,
                                       OpEscala, OpMover, OpReemplazarCara, OpVaciado)
from ...timeline.ops_solido import OpReticulaVolumetrica
from ...timeline.parametros import ANGULO, ESCALAR
from ..comando import (Casilla, Comando, Entero, ErrorComando, Expresion, Info, Opciones, Seleccion, Texto, exigir, hit_desde_ref,
                       hits, hits_cuerpos as _hits_cuerpos, ref1, refs)
from . import registrar
from .aspecto import Aspecto  # noqa: F401  (el comando vive en aspecto.py; se sigue pudiendo importar desde acá)
from .comunes import evaluar_o_cero


def _cuerpos(v, clave="cuerpos"):
    """Ids de los cuerpos elegidos (`v` es el dict de valores o directamente la lista de selección)."""
    lista = v if isinstance(v, list) else (v.get(clave) or [])
    return [h["ref"]["cuerpo"] for h in lista if h["ref"].get("tipo") == "cuerpo"]


def _hit1(ref, estado):
    return [hit_desde_ref(ref, estado)] if ref else []


def _con_cuerpos(ctx):
    return None if ctx.estado.cuerpos else "Este comando necesita al menos un cuerpo."


# ---------------------------------------------------------------- manipuladores en la vista
def _flecha_arista(ctx, seleccion, clave, chaflan=False):
    """Flecha de radio/distancia en el punto medio de la primera arista: arranca donde queda la superficie
    del empalme (o del chaflán) y avanza hacia donde crece, así la punta sigue al cursor."""
    import math

    from .. import manipuladores as mp
    arista = next((h for h in seleccion or [] if h["ref"].get("tipo") == "arista"), None)
    e = mp.entidad(arista, ctx.estado) if arista is not None else None
    if e is None or e.cuerpo not in ctx.estado.cuerpos:
        return []
    medio, hacia, fi = mp.datos_arista(e.forma, ctx.estado.cuerpos[e.cuerpo].forma)
    factor = math.sin(fi / 2) if chaflan else 1 / max(math.cos(fi / 2), 1e-3) - 1
    return [mp.Flecha(clave, medio, hacia, factor=max(factor, 0.15), minimo=0.0)]


def _cara_y_normal(ctx, seleccion):
    """(punto, normal hacia afuera) de la primera cara elegida o, si se eligió un cuerpo, de su cara más grande."""
    from ...nucleo import geometria as geo
    from .. import manipuladores as mp
    for h in seleccion or []:
        e = mp.entidad(h, ctx.estado)
        if e is None or e.forma is None:
            continue
        if e.tipo == "cara":
            return mp.punto_normal_cara(e.forma)
        if e.tipo == "cuerpo":
            caras = geo.caras(e.forma)
            if caras:
                return mp.punto_normal_cara(max(caras, key=geo.area))
    return None


class Empalme(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "empalme_3d", "Empalme", "empalme_3d", "F"
    AYUDA = "Redondea aristas (quita material en las exteriores y agrega en las interiores)."
    CLASE_OP = OpEmpalme
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        empalme = lambda v: v.get("tipo") not in ("reglas", "completo")  # noqa: E731
        reglas = lambda v: v.get("tipo") == "reglas"  # noqa: E731
        completo = lambda v: v.get("tipo") == "completo"  # noqa: E731
        return [
            Opciones("tipo", "Tipo", {"empalme": "Empalme", "reglas": "Empalme de reglas",
                                      "completo": "Redondeo completo"}),
            Seleccion("central", "Cara central", {"cara_plana"}, visible_si=completo,
                      ayuda="La cara que se vuelve una media caña entre las dos laterales."),
            Seleccion("laterales", "Caras laterales", {"cara_plana"}, minimo=2, maximo=2, visible_si=completo,
                      ayuda="Dos caras planas, paralelas y perpendiculares a la central."),
            Seleccion("aristas", "Aristas", {"arista"}, maximo=None, visible_si=empalme),
            Opciones("tipo_radio", "Tipo de radio", {"constante": "Constante", "cuerda": "Longitud de cuerda",
                                                     "variable": "Variable"}, visible_si=empalme),
            Expresion("radio", "Radio", "1 mm", visible_si=lambda v: not completo(v) and (
                v.get("tipo_radio") != "cuerda" or v.get("tipo") == "reglas")),
            Expresion("radio_fin", "Radio final", "2 mm",
                      visible_si=lambda v: empalme(v) and v.get("tipo_radio") == "variable"),
            Texto("puntos_radio", "Puntos intermedios", "", visible_si=lambda v: empalme(v) and v.get("tipo_radio") == "variable",
                  ayuda="Posición (0 a 1) y radio separados por «:», uno por punto y separados por «;», p. ej. 0.5:3 mm; 0.8:2 mm."),
            Expresion("cuerda", "Longitud de cuerda", "1 mm",
                      visible_si=lambda v: empalme(v) and v.get("tipo_radio") == "cuerda"),
            Seleccion("caras_a", "Caras/operaciones", {"cara"}, maximo=None, visible_si=reglas),
            Opciones("regla", "Regla", {"todas": "Todas las aristas", "entre": "Entre caras/operaciones"},
                     visible_si=reglas),
            Seleccion("caras_b", "Caras/operaciones 2", {"cara"}, maximo=None,
                      visible_si=lambda v: reglas(v) and v.get("regla") == "entre"),
            Opciones("redondeos", "Topología", {"ambos": "Redondeos y empalmes", "redondeos": "Solo redondeos",
                                                "empalmes": "Solo empalmes"}, visible_si=reglas),
            Casilla("cadena_tangente", "Cadena tangente", True, visible_si=empalme),
            Seleccion("aristas_2", "Aristas del conjunto 2", {"arista"}, minimo=0, maximo=None, visible_si=empalme,
                      ayuda="Otro conjunto de aristas con su propio radio, en el mismo paso (el «+» de Fusion)."),
            Opciones("tipo_radio_2", "Tipo de radio 2", {"constante": "Constante", "cuerda": "Longitud de cuerda",
                                                         "variable": "Variable"},
                     visible_si=lambda v: empalme(v) and bool(v.get("aristas_2"))),
            Expresion("radio_2", "Radio 2", "1 mm", visible_si=lambda v: empalme(v) and bool(v.get("aristas_2"))
                      and v.get("tipo_radio_2") != "cuerda"),
            Expresion("radio_fin_2", "Radio final 2", "2 mm", visible_si=lambda v: empalme(v) and bool(v.get("aristas_2"))
                      and v.get("tipo_radio_2") == "variable"),
            Expresion("cuerda_2", "Longitud de cuerda 2", "1 mm", visible_si=lambda v: empalme(v) and bool(v.get("aristas_2"))
                      and v.get("tipo_radio_2") == "cuerda"),
        ]

    @staticmethod
    def _puntos_radio(texto, ctx):
        """«0.5:3 mm; 0.8:2 mm» → [{"posicion": "0.5", "radio": "3 mm"}…] (las expresiones se validan acá, en rojo)."""
        puntos = []
        for parte in (texto or "").split(";"):
            if not parte.strip():
                continue
            if parte.count(":") != 1:
                raise ErrorComando(f"Cada punto es posición:radio (p. ej. 0.5:3 mm), no «{parte.strip()}».")
            pos, rad = (x.strip() for x in parte.split(":"))
            if not 0 < ctx.evaluar(pos, ESCALAR) < 1:
                raise ErrorComando("La posición de un punto intermedio está entre 0 y 1 (sin incluirlos).")
            ctx.evaluar(rad)
            puntos.append({"posicion": pos, "radio": rad})
        return puntos

    def construir(self, v, ctx):
        if v.get("tipo") == "completo":
            exigir(v, "central", "Seleccioná la cara central.")
            exigir(v, "laterales", "Seleccioná las dos caras laterales.")
            if len(v["laterales"]) != 2:
                raise ErrorComando("Hacen falta exactamente dos caras laterales.")
            return self.crear_op(OpEmpalme, v, ctx, tipo="completo", central=ref1(v, "central"),
                                 laterales=refs(v, "laterales"))
        if v.get("tipo") == "reglas":
            exigir(v, "caras_a", "Seleccioná las caras para la regla.")
        else:
            exigir(v, "aristas", "Seleccioná las aristas a empalmar.")
        ctx.evaluar(v["radio"])
        puntos = self._puntos_radio(v.get("puntos_radio"), ctx) if v.get("tipo_radio") == "variable" else []
        previos = list(ctx.op.p.get("conjuntos") or []) if ctx.op else []
        conjuntos = previos[1:]            # el primero lo edita «conjunto 2» (vaciarlo lo quita); los demás se conservan
        if v.get("aristas_2") and v.get("tipo") == "empalme":
            tipo2 = v.get("tipo_radio_2", "constante")
            for clave in ("cuerda_2" if tipo2 == "cuerda" else "radio_2", *(("radio_fin_2",) if tipo2 == "variable" else ())):
                ctx.evaluar(v[clave])
            conjuntos.insert(0, {"aristas": refs(v, "aristas_2"), "tipo_radio": tipo2, "radio": v["radio_2"],
                                 "radio_fin": v["radio_fin_2"], "cuerda": v["cuerda_2"]})
        return self.crear_op(OpEmpalme, v, ctx, tipo=v["tipo"], aristas=refs(v, "aristas"), tipo_radio=v["tipo_radio"],
                             radio=v["radio"], radio_fin=v["radio_fin"], cuerda=v["cuerda"],
                             cadena_tangente=v["cadena_tangente"], caras_a=refs(v, "caras_a"),
                             caras_b=refs(v, "caras_b"), regla=v["regla"], redondeos=v["redondeos"],
                             puntos_radio=puntos, conjuntos=conjuntos)

    def manipuladores(self, ctx, v):
        if v.get("tipo") == "reglas":
            return []
        return _flecha_arista(ctx, v.get("aristas"), "cuerda" if v.get("tipo_radio") == "cuerda" else "radio")

    def desde_op(self, op, ctx):
        v = dict(op.p)
        for k in ("aristas", "caras_a", "caras_b", "laterales"):
            v[k] = hits(op.p.get(k) or [], ctx.estado)
        v["central"] = _hit1(op.p["central"], ctx.estado) if op.p.get("central") else []
        v["puntos_radio"] = "; ".join(f"{q['posicion']}: {q['radio']}" for q in op.p.get("puntos_radio") or [])
        for c in (op.p.get("conjuntos") or [])[:1]:     # el primer conjunto adicional va a los campos «2»
            v.update(aristas_2=hits(c.get("aristas") or [], ctx.estado), tipo_radio_2=c.get("tipo_radio", "constante"),
                     radio_2=c.get("radio", "1 mm"), radio_fin_2=c.get("radio_fin", "2 mm"), cuerda_2=c.get("cuerda", "1 mm"))
        return v


class Chaflan(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "chaflan_3d", "Chaflán", "chaflan_3d", "Ctrl+\\"
    AYUDA = "Bisela aristas con una distancia, dos distancias o distancia y ángulo."
    CLASE_OP = OpChaflan
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [
            Seleccion("aristas", "Aristas", {"arista"}, maximo=None),
            Opciones("tipo", "Tipo de chaflán", {"distancia_igual": "Distancia igual", "dos_distancias": "Dos distancias",
                                                 "distancia_angulo": "Distancia y ángulo"}),
            Expresion("distancia", "Distancia", "1 mm"),
            Expresion("distancia2", "Distancia 2", "1 mm", visible_si=lambda v: v.get("tipo") == "dos_distancias"),
            Expresion("angulo", "Ángulo", "45 deg", ANGULO, visible_si=lambda v: v.get("tipo") == "distancia_angulo"),
            Casilla("voltear", "Voltear", visible_si=lambda v: v.get("tipo") != "distancia_igual"),
            Casilla("cadena_tangente", "Cadena tangente", True),
            Opciones("esquina", "Tipo de esquina", {"chaflan": "Chaflán", "inglete": "Inglete"}),
        ]

    def construir(self, v, ctx):
        exigir(v, "aristas", "Seleccioná las aristas.")
        ctx.evaluar(v["distancia"])
        return self.crear_op(OpChaflan, v, ctx, aristas=refs(v, "aristas"),
                             **{k: v[k] for k in ("tipo", "distancia", "distancia2", "angulo", "voltear",
                                                  "cadena_tangente", "esquina")})

    def manipuladores(self, ctx, v):
        return _flecha_arista(ctx, v.get("aristas"), "distancia", chaflan=True)

    def desde_op(self, op, ctx):
        return dict(op.p, aristas=hits(op.p["aristas"], ctx.estado))


class Vaciado(Comando):
    CLAVE, TITULO, ICONO = "vaciado", "Vaciado", "vaciado"
    AYUDA = "Ahueca un cuerpo dejando paredes de espesor constante; las caras elegidas quedan abiertas."
    CLASE_OP = OpVaciado
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [
            Seleccion("caras", "Caras/cuerpo", {"cara", "cuerpo"}, maximo=None),
            Casilla("tangente", "Cadena tangente", True),
            Opciones("direccion", "Dirección", {"interior": "Interior", "exterior": "Exterior", "ambos": "Ambos"}),
            Expresion("espesor_interior", "Espesor interior", "1 mm",
                      visible_si=lambda v: v.get("direccion") != "exterior"),
            Expresion("espesor_exterior", "Espesor exterior", "1 mm",
                      visible_si=lambda v: v.get("direccion") != "interior"),
            Opciones("tipo", "Tipo de vaciado", {"afilado": "Desfase afilado", "redondeado": "Desfase redondeado"}),
        ]

    def construir(self, v, ctx):
        sel = exigir(v, "caras", "Seleccioná las caras a quitar o un cuerpo.")
        return self.crear_op(OpVaciado, v, ctx, caras=[h["ref"] for h in sel if h["ref"]["tipo"] == "cara"],
                             cuerpos=[h["ref"]["cuerpo"] for h in sel if h["ref"]["tipo"] == "cuerpo"],
                             **{k: v[k] for k in ("espesor_interior", "espesor_exterior", "direccion", "tangente",
                                                  "tipo")})

    def manipuladores(self, ctx, v):
        """Flecha de espesor sobre la cara elegida: hacia adentro (interior) y/o hacia afuera (exterior)."""
        from .. import manipuladores as mp
        base = _cara_y_normal(ctx, v.get("caras"))
        if base is None:
            return []
        punto, n = base
        salida = []
        if v.get("direccion") != "exterior":
            salida.append(mp.Flecha("espesor_interior", punto, -n, minimo=0.0))
        if v.get("direccion") != "interior":
            salida.append(mp.Flecha("espesor_exterior", punto, n, minimo=0.0))
        return salida

    def desde_op(self, op, ctx):
        return dict(op.p, caras=hits(op.p["caras"], ctx.estado) + _hits_cuerpos(op.p["cuerpos"], ctx.estado))


class Desmoldeo(Comando):
    CLAVE, TITULO, ICONO = "desmoldeo", "Desmoldeo", "desmoldeo"
    AYUDA = "Inclina caras un ángulo respecto de la dirección de extracción del molde."
    CLASE_OP = OpDesmoldeo
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        particion = lambda v: v.get("tipo") == "linea_particion"  # noqa: E731
        return [
            Opciones("tipo", "Tipo", {"plano_fijo": "Plano fijo", "linea_particion": "Línea de partición"}),
            Seleccion("plano", "Plano fijo o dirección de extracción", {"cara_plana", "plano", "eje", "arista_lineal"},
                      ayuda="Con «Línea de partición» define la dirección de extracción."),
            Seleccion("herramienta_particion", "Herramienta de partición", {"cara_plana", "plano", "arista", "curva_boceto"},
                      visible_si=particion, ayuda="Plano, cara plana o curva plana por donde pasa la línea de partición."),
            Seleccion("caras", "Caras", {"cara"}, maximo=None),
            Opciones("modo_angulo", "Modo de ángulo", {"relativo": "Relativo", "absoluto": "Absoluto"}, "relativo",
                     ayuda="Relativo suma el ángulo al desmoldeo que la cara ya tiene; absoluto lo mide desde la dirección."),
            Casilla("voltear", "Invertir dirección de extracción"),
            Opciones("lados", "Tipo de desmoldeo", {"uno": "Un lado", "dos": "Dos lados", "simetrico": "Simétrico"}),
            Expresion("angulo", "Ángulo", "3 deg", ANGULO),
            Expresion("angulo2", "Ángulo 2", "3 deg", ANGULO, visible_si=lambda v: v.get("lados") == "dos"),
        ]

    def construir(self, v, ctx):
        particion = v.get("tipo") == "linea_particion"
        exigir(v, "plano", "Seleccioná la dirección de extracción." if particion else "Seleccioná el plano fijo.")
        if particion:
            exigir(v, "herramienta_particion", "Seleccioná la herramienta de partición.")
        exigir(v, "caras", "Seleccioná las caras a inclinar.")
        return self.crear_op(OpDesmoldeo, v, ctx, plano=ref1(v, "plano"), caras=refs(v, "caras"),
                             herramienta_particion=ref1(v, "herramienta_particion") if particion else None,
                             **{k: v[k] for k in ("angulo", "lados", "angulo2", "voltear", "tipo", "modo_angulo")})

    def desde_op(self, op, ctx):
        herramienta = op.p.get("herramienta_particion")
        return dict(op.p, plano=_hit1(op.p["plano"], ctx.estado), caras=hits(op.p["caras"], ctx.estado),
                    herramienta_particion=_hit1(herramienta, ctx.estado) if herramienta else [])


class ReticulaVolumetrica(Comando):
    CLAVE, TITULO, ICONO = "reticula_volumetrica", "Retícula volumétrica", "reticula_volumetrica"
    AYUDA = ("Llena un sólido o una malla cerrada con una estructura interna por celdas: barras (cruz, celda X, celda X "
             "2.5D, a medida) o superficies mínimas (gyroid, Schwarz P y D, que quedan como cuerpo de malla). La solidez "
             "es el porcentaje de material; puede ir en gradiente por una ruta y cambiar cerca de las paredes (desfase).")
    CLASE_OP = OpReticulaVolumetrica
    verificar = staticmethod(_con_cuerpos)
    MOVER = ("mover_x", "mover_y", "mover_z", "girar_x", "girar_y", "girar_z")

    def campos(self, ctx):
        no_uniforme = lambda v: bool(v.get("no_uniforme"))  # noqa: E731
        gradiente = lambda v: v.get("distribucion") == "gradiente"  # noqa: E731
        desfase = lambda v: bool(v.get("con_desfase"))  # noqa: E731
        mover = lambda v: bool(v.get("mover_celdas"))  # noqa: E731
        return [Seleccion("cuerpo", "Cuerpo sólido o malla cerrada", {"cuerpo"}),
                Opciones("forma_celda", "Forma de la celda", {"gyroid": "Gyroid", "cross": "Cruz", "x_cell": "Celda X",
                                                              "x_cell_25d": "Celda X 2.5D", "schwarz_p": "Schwarz P",
                                                              "schwarz_d": "Schwarz D", "custom": "A medida"}),
                Texto("barras", "Barras (x1 y1 z1 x2 y2 z2; …, de 0 a 1)", "0 0 0 1 1 1; 1 0 0 0 1 1",
                      visible_si=lambda v: v.get("forma_celda") == "custom"),
                Expresion("tamano", "Tamaño de celda (X)", "5 mm"),
                Casilla("no_uniforme", "Proporciones no uniformes"),
                Expresion("tamano_y", "Tamaño en Y", "5 mm", visible_si=no_uniforme),
                Expresion("tamano_z", "Tamaño en Z", "5 mm", visible_si=no_uniforme),
                Casilla("mover_celdas", "Mover / girar las celdas"),
                *(Expresion(k, f"{'Mover' if k[0] == 'm' else 'Girar'} en {k[-1].upper()}",
                            "0 mm" if k[0] == "m" else "0 deg", visible_si=mover, **({} if k[0] == "m" else {"tipo": ANGULO}))
                  for k in self.MOVER),
                Opciones("distribucion", "Distribución", {"uniforme": "Uniforme", "gradiente": "Gradiente por una ruta"}),
                Expresion("solidez", "Solidez (%)", "30", ESCALAR),
                Expresion("solidez_final", "Solidez al final (%)", "60", ESCALAR, visible_si=gradiente),
                Seleccion("ruta", "Ruta", {"arista", "curva_boceto", "vertice", "punto", "punto_boceto"}, maximo=None,
                          visible_si=gradiente),
                Casilla("con_desfase", "Zona de desfase"),
                Seleccion("zonas", "Zona (vacío = todas las caras)", {"cara", "arista", "vertice", "punto"}, minimo=0,
                          maximo=None, visible_si=desfase),
                Expresion("desfase", "Desfase", "1 mm", visible_si=desfase),
                Expresion("solidez_desfase", "Solidez del desfase (%)", "100", ESCALAR, visible_si=desfase),
                Expresion("mezcla", "Distancia de mezcla", "1 mm", visible_si=desfase),
                Entero("resolucion", "Muestras por celda", 8, 4, 40,
                       visible_si=lambda v: v.get("forma_celda") in ("gyroid", "schwarz_p", "schwarz_d"))]

    @staticmethod
    def _barras(texto):
        try:
            barras = [[float(x) for x in b.replace(",", ".").split()] for b in texto.split(";") if b.strip()]
        except ValueError:
            barras = []
        if not barras or any(len(b) != 6 or not all(0 <= x <= 1 for x in b) for b in barras):
            raise ErrorComando("Cada barra son 6 números de 0 a 1 (x1 y1 z1 x2 y2 z2), separadas con «;».")
        return barras

    def construir(self, v, ctx):
        exigir(v, "cuerpo", "Seleccioná el sólido o la malla que se llena.")
        gradiente, desfase, mover = v.get("distribucion") == "gradiente", bool(v.get("con_desfase")), bool(v.get("mover_celdas"))
        for k in ("tamano", "tamano_y", "tamano_z") if v.get("no_uniforme") else ("tamano",):
            ctx.evaluar(v[k])
        for k in ("solidez",) + (("solidez_final",) if gradiente else ()) + (("solidez_desfase",) if desfase else ()):
            ctx.evaluar(v[k], ESCALAR)
        for k in (("desfase", "mezcla") if desfase else ()) + (self.MOVER[:3] if mover else ()):
            ctx.evaluar(v[k])
        for k in self.MOVER[3:] if mover else ():
            ctx.evaluar(v[k], ANGULO)
        if gradiente:
            exigir(v, "ruta", "Elegí la ruta del gradiente: una arista o curva, o dos puntos.")
        extra = {k: v[k] if mover else ("0 mm" if k[0] == "m" else "0 deg") for k in self.MOVER}
        return self.crear_op(OpReticulaVolumetrica, v, ctx, cuerpo=v["cuerpo"][0]["ref"]["cuerpo"],
                             tamano_y=v["tamano_y"] if v.get("no_uniforme") else "",
                             tamano_z=v["tamano_z"] if v.get("no_uniforme") else "",
                             barras=self._barras(v["barras"]) if v["forma_celda"] == "custom" else [],
                             solidez_final=v["solidez_final"] if gradiente else "",
                             ruta=refs(v, "ruta") if gradiente else [], zonas=refs(v, "zonas") if desfase else [],
                             desfase=v["desfase"] if desfase else "0 mm", mezcla=v["mezcla"] if desfase else "0 mm",
                             solidez_desfase=v["solidez_desfase"], **extra,
                             **{k: v[k] for k in ("forma_celda", "tamano", "solidez", "resolucion")})

    def desde_op(self, op, ctx):
        p = op.p
        v = dict(p, cuerpo=_hits_cuerpos([p["cuerpo"]], ctx.estado), no_uniforme=bool(p.get("tamano_y") or p.get("tamano_z")))
        v["tamano_y"], v["tamano_z"] = p.get("tamano_y") or p["tamano"], p.get("tamano_z") or p["tamano"]
        v["barras"] = "; ".join(" ".join(f"{x:g}" for x in b) for b in p.get("barras") or []) or "0 0 0 1 1 1"
        v["distribucion"] = "gradiente" if p.get("solidez_final") else "uniforme"
        v["solidez_final"] = p.get("solidez_final") or "60"
        v["ruta"], v["zonas"] = hits(p.get("ruta") or [], ctx.estado), hits(p.get("zonas") or [], ctx.estado)
        v["con_desfase"] = any(str(p.get(k) or "0").split()[0] not in ("0", "0.0") for k in ("desfase", "mezcla"))
        v["mover_celdas"] = any(str(p.get(k) or "0").split()[0] not in ("0", "0.0") for k in self.MOVER)
        for k in self.MOVER:
            v[k] = p.get(k) or ("0 mm" if k[0] == "m" else "0 deg")
        return v


class Escala(Comando):
    CLAVE, TITULO, ICONO = "escala_3d", "Escala", "escala_3d"
    AYUDA = "Agranda o achica cuerpos respecto de un punto (uniforme o con un factor por eje)."
    CLASE_OP = OpEscala
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        no_uniforme = lambda v: v.get("tipo") == "no_uniforme"  # noqa: E731
        return [
            Seleccion("cuerpos", "Entidades", {"cuerpo"}, maximo=None),
            Seleccion("punto", "Punto", {"vertice", "punto"}, minimo=0,
                      ayuda="Punto base. Sin selección: el origen."),
            Opciones("tipo", "Tipo de escala", {"uniforme": "Uniforme", "no_uniforme": "No uniforme"}),
            Expresion("factor", "Factor de escala", "1", ESCALAR, visible_si=lambda v: not no_uniforme(v)),
            Expresion("fx", "Escala X", "1", ESCALAR, visible_si=no_uniforme),
            Expresion("fy", "Escala Y", "1", ESCALAR, visible_si=no_uniforme),
            Expresion("fz", "Escala Z", "1", ESCALAR, visible_si=no_uniforme),
        ]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos.")
        return self.crear_op(OpEscala, v, ctx, cuerpos=_cuerpos(v), punto=ref1(v, "punto"),
                             **{k: v[k] for k in ("tipo", "factor", "fx", "fy", "fz")})

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado), punto=_hit1(op.p["punto"], ctx.estado))


class CaraDesfase(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "desfase_cara", "Cara de desfase", "desfase_cara", "Shift+D"
    AYUDA = "Mueve caras del cuerpo a lo largo de su normal (agrega o quita material)."
    CLASE_OP = OpDesfaseCara
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("caras", "Caras", {"cara"}, maximo=None), Expresion("distancia", "Distancia", "1 mm"),
                Casilla("tangente", "Cadena tangente", True)]

    def construir(self, v, ctx):
        exigir(v, "caras", "Seleccioná las caras.")
        ctx.evaluar(v["distancia"])
        return self.crear_op(OpDesfaseCara, v, ctx, caras=refs(v, "caras"), distancia=v["distancia"],
                             tangente=v["tangente"])

    def manipuladores(self, ctx, v):
        from .. import manipuladores as mp
        base = _cara_y_normal(ctx, v.get("caras"))
        return [mp.Flecha("distancia", base[0], base[1])] if base is not None else []

    def desde_op(self, op, ctx):
        return dict(op.p, caras=hits(op.p["caras"], ctx.estado))


class PulsarTirar(Comando):
    """Pulsar/tirar (Q): sobre una cara hace un desfase de cara; sobre una arista, un empalme."""
    CLAVE, TITULO, ICONO, ATAJO = "pulsar_tirar", "Pulsar/tirar", "pulsar_tirar", "Q"
    AYUDA = "Clic en una cara para desplazarla, o en una arista para redondearla."
    CLASE_OP = OpDesfaseCara                 # el paso de cara se vuelve a abrir con este mismo diálogo (ver VARIANTE)
    VARIANTE = ("origen", "pulsar_tirar")
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("objetos", "Cara o arista", {"cara", "arista"}, maximo=None),
                Expresion("distancia", "Distancia / radio", "1 mm")]

    def construir(self, v, ctx):
        sel = exigir(v, "objetos", "Seleccioná una cara o una arista.")
        tipos = {h["ref"]["tipo"] for h in sel}
        if len(tipos) > 1:
            raise ErrorComando("Elegí solo caras o solo aristas.")
        ctx.evaluar(v["distancia"])
        if tipos == {"cara"}:
            op = self.crear_op(OpDesfaseCara, v, ctx, caras=refs(v, "objetos"), distancia=v["distancia"],
                               origen="pulsar_tirar")
            base = "Pulsar/tirar"
        else:
            op = self.crear_op(OpEmpalme, v, ctx, aristas=refs(v, "objetos"), radio=v["distancia"])
            base = "Empalme"
        if ctx.op is None:
            op.nombre = _siguiente(ctx, base)
        return op

    def desde_op(self, op, ctx):
        return {"objetos": hits(op.p["caras"], ctx.estado), "distancia": op.p["distancia"]}

    def manipuladores(self, ctx, v):
        """Sobre una cara: flecha de desfase por su normal (negativo = quita material); sobre una arista:
        la flecha del radio del empalme."""
        from .. import manipuladores as mp
        sel = v.get("objetos") or []
        if not sel:
            return []
        if sel[0]["ref"].get("tipo") == "arista":
            return _flecha_arista(ctx, sel, "distancia")
        base = _cara_y_normal(ctx, sel)
        return [mp.Flecha("distancia", base[0], base[1])] if base is not None else []


def _tipos_elegidos(v):
    return {h["ref"].get("tipo") for h in v.get("objetos") or []}


def _con_caras(v):
    return "cara" in _tipos_elegidos(v)


def _con_aristas(v):
    return bool(_tipos_elegidos(v) & {"arista", "curva_boceto"})


class Desfase(Comando):
    """Desfase (PL1, «un comando según lo elegido» de Plasticity): con caras las mueve a lo largo de su normal (el
    desfase de cara de siempre); con aristas o curvas de boceto crea curvas nuevas a esa distancia (PL7)."""
    CLAVE, TITULO, ICONO = "desfase", "Desfase", "desfase_cara"
    AYUDA = ("Un solo comando para desfasar. Con caras: las mueve a lo largo de su normal (agrega o quita material). "
             "Con aristas o curvas de un boceto: crea un boceto nuevo con curvas a esa distancia, sin cortar el cuerpo.")
    CLASE_OP = OpDesfaseAristas          # al editar un paso «Desfase de aristas»; el de cara lo edita «Cara de desfase»

    def verificar(self, ctx):
        return None if ctx.estado.cuerpos or ctx.estado.bocetos else "Este comando necesita un cuerpo o un boceto."

    def campos(self, ctx):
        return [Seleccion("objetos", "Caras, aristas o curvas", {"cara", "arista", "curva_boceto"}, maximo=None),
                Seleccion("plano", "Plano (opcional)", {"cara", "plano"}, minimo=0, visible_si=_con_aristas,
                          ayuda="Dónde se hace el desfase; sin elegir, el plano que contiene a todas las aristas."),
                Expresion("distancia", "Distancia", "1 mm"),
                Casilla("tangente", "Cadena tangente", True, visible_si=_con_caras),
                Casilla("simetrico", "Simétrico", False, visible_si=_con_aristas),
                Opciones("esquinas", "Esquinas", {"redondas": "Redondas", "vivas": "Vivas"}, visible_si=_con_aristas),
                Info("modo", "Qué hace", self._modo)]

    @staticmethod
    def _modo(v, ctx):
        if _con_caras(v):
            return "Desfase de cara: mueve las caras elegidas a lo largo de su normal."
        if _con_aristas(v):
            return "Desfase de aristas: crea un boceto nuevo con curvas a esa distancia; no corta el cuerpo."
        return "Elegí caras (las mueve), aristas o curvas de un boceto (crea curvas nuevas)."

    def construir(self, v, ctx):
        exigir(v, "objetos", "Seleccioná caras, aristas o curvas.")
        if _con_caras(v) and _con_aristas(v):
            raise ErrorComando("Elegí solo caras (desfase de cara) o solo aristas y curvas (desfase de aristas).")
        ctx.evaluar(v["distancia"])
        if _con_caras(v):
            op = self.crear_op(OpDesfaseCara, v, ctx, caras=refs(v, "objetos"), distancia=v["distancia"],
                               tangente=v["tangente"])
            base = "Desfase de cara"
        else:
            op = self.crear_op(OpDesfaseAristas, v, ctx, referencias=refs(v, "objetos"), plano=ref1(v, "plano"),
                               distancia=v["distancia"], simetrico=v["simetrico"], esquinas=v["esquinas"])
            base = "Desfase de aristas"
        if ctx.op is None or ctx.op.TIPO != op.TIPO:          # al editar y pasar de aristas a caras cambia el paso
            op.nombre = _siguiente(ctx, base)
        return op

    def manipuladores(self, ctx, v):
        from .. import manipuladores as mp
        if not _con_caras(v):
            return []
        base = _cara_y_normal(ctx, v.get("objetos"))
        return [mp.Flecha("distancia", base[0], base[1])] if base is not None else []

    def desde_op(self, op, ctx):
        return dict(op.p, objetos=hits(op.p["referencias"], ctx.estado), plano=_hit1(op.p["plano"], ctx.estado))


class ReemplazarCara(Comando):
    CLAVE, TITULO, ICONO = "reemplazar_cara", "Reemplazar cara", "reemplazar_cara"
    AYUDA = "Lleva caras del cuerpo hasta otra cara o un plano."
    CLASE_OP = OpReemplazarCara
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("caras", "Caras de origen", {"cara"}, maximo=None),
                Seleccion("destino", "Caras de destino", {"cara", "plano"})]

    def construir(self, v, ctx):
        exigir(v, "caras", "Seleccioná las caras de origen.")
        exigir(v, "destino", "Seleccioná la cara o el plano de destino.")
        return self.crear_op(OpReemplazarCara, v, ctx, caras=refs(v, "caras"), destino=ref1(v, "destino"))

    def desde_op(self, op, ctx):
        return dict(op.p, caras=hits(op.p["caras"], ctx.estado), destino=_hit1(op.p["destino"], ctx.estado))


class DividirCara(Comando):
    CLAVE, TITULO, ICONO = "dividir_cara", "Dividir cara", "dividir_cara"
    AYUDA = "Parte caras con una cara, un plano o curvas: con la superficie, según un vector o al punto más cercano."
    CLASE_OP = OpDividirCara
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        proyecta = lambda v: v.get("tipo") in ("vector", "cercano")  # noqa: E731
        return [Seleccion("caras", "Caras para dividir", {"cara"}, maximo=None),
                Seleccion("herramienta", "Herramienta de división", {"cara", "plano", "arista", "curva_boceto"}),
                Opciones("tipo", "Tipo de división", {"superficie": "Dividir con superficie", "vector": "Según vector",
                                                      "cercano": "Punto más cercano"}),
                Seleccion("direccion", "Dirección de proyección", {"plano", "cara_plana", "eje", "arista_lineal"},
                          visible_si=lambda v: v.get("tipo") == "vector"),
                Casilla("extender", "Extender herramienta de división", True,
                        visible_si=lambda v: not proyecta(v))]

    def construir(self, v, ctx):
        exigir(v, "caras", "Seleccioná las caras a dividir.")
        exigir(v, "herramienta", "Seleccioná la herramienta.")
        if v.get("tipo") == "vector":
            exigir(v, "direccion", "Seleccioná la dirección de proyección.")
        return self.crear_op(OpDividirCara, v, ctx, caras=refs(v, "caras"), herramienta=ref1(v, "herramienta"),
                             extender=v["extender"], tipo=v.get("tipo", "superficie"),
                             direccion=ref1(v, "direccion") if v.get("tipo") == "vector" else None)

    def desde_op(self, op, ctx):
        return dict(op.p, caras=hits(op.p["caras"], ctx.estado), herramienta=_hit1(op.p["herramienta"], ctx.estado),
                    direccion=_hit1(op.p.get("direccion"), ctx.estado))


class DividirCuerpo(Comando):
    CLAVE, TITULO, ICONO = "dividir_cuerpo", "Dividir cuerpo", "dividir_cuerpo"
    AYUDA = "Parte un cuerpo en varios con un plano, una cara o otro cuerpo."
    CLASE_OP = OpDividirCuerpo
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("cuerpo", "Cuerpo para dividir", {"cuerpo"}),
                Seleccion("herramienta", "Herramientas de división", {"cara", "plano", "cuerpo"}),
                Casilla("extender", "Extender herramienta de división", True)]

    def construir(self, v, ctx):
        exigir(v, "cuerpo", "Seleccioná el cuerpo.")
        exigir(v, "herramienta", "Seleccioná la herramienta.")
        return self.crear_op(OpDividirCuerpo, v, ctx, cuerpo=_cuerpos(v, "cuerpo")[0],
                             herramienta=ref1(v, "herramienta"), extender=v["extender"])

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpo=_hits_cuerpos(op.p["cuerpo"], ctx.estado),
                    herramienta=_hit1(op.p["herramienta"], ctx.estado))


class DivisionSilueta(Comando):
    CLAVE, TITULO, ICONO = "division_silueta", "División de silueta", "division_silueta"
    AYUDA = "Parte las caras de un cuerpo por su silueta vista desde una dirección."
    CLASE_OP = OpDivisionSilueta
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("direccion", "Dirección de vista", {"plano", "cara_plana", "eje", "arista_lineal"}),
                Seleccion("cuerpo", "Cuerpo de destino", {"cuerpo"}),
                Opciones("operacion", "Operación", {"caras": "Dividir solo las caras", "vaciado": "Dividir cuerpo vaciado",
                                                    "solido": "Dividir cuerpo sólido"})]

    def construir(self, v, ctx):
        exigir(v, "direccion", "Seleccioná la dirección.")
        exigir(v, "cuerpo", "Seleccioná el cuerpo.")
        return self.crear_op(OpDivisionSilueta, v, ctx, cuerpo=_cuerpos(v, "cuerpo")[0], direccion=ref1(v, "direccion"),
                             operacion=v.get("operacion", "caras"))

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpo=_hits_cuerpos(op.p["cuerpo"], ctx.estado),
                    direccion=_hit1(op.p["direccion"], ctx.estado))


class MoverCopiar(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "mover_copiar", "Mover/copiar", "mover_copiar", "M"
    AYUDA = ("Mueve, gira o copia cuerpos o caras planas: libre, trasladar, girar, punto a punto o punto a "
             "posición.")
    CLASE_OP = OpMover
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        t = lambda *tipos: (lambda v: v.get("tipo") in tipos)  # noqa: E731
        caras = lambda v: v.get("objeto") == "caras"  # noqa: E731
        return [
            Opciones("objeto", "Mover objeto", {"cuerpos": "Cuerpos", "caras": "Caras"}),
            Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, maximo=None, visible_si=lambda v: not caras(v)),
            Seleccion("caras", "Caras", {"cara"}, maximo=None, visible_si=caras,
                      ayuda="Caras planas: las vecinas se extienden o se recortan. «Crear copia» deja superficies."),
            Opciones("tipo", "Tipo de movimiento", TIPOS_MOVIMIENTO),
            Seleccion("pivote", "Pivote", {"vertice", "punto"}, minimo=0, visible_si=t("libre"),
                      ayuda="Centro de giro. Sin selección: el centro de los cuerpos."),
            Seleccion("direccion", "Dirección", {"eje", "arista_lineal", "cara_plana", "plano"}, minimo=0,
                      visible_si=t("traslacion"), ayuda="Sin selección: ejes X, Y, Z del diseño."),
            Expresion("distancia", "Distancia", "10 mm", visible_si=lambda v: v.get("tipo") == "traslacion"
                      and bool(v.get("direccion"))),
            Expresion("dx", "Distancia X", "0 mm", visible_si=lambda v: v.get("tipo") == "libre" or (
                v.get("tipo") == "traslacion" and not v.get("direccion"))),
            Expresion("dy", "Distancia Y", "0 mm", visible_si=lambda v: v.get("tipo") == "libre" or (
                v.get("tipo") == "traslacion" and not v.get("direccion"))),
            Expresion("dz", "Distancia Z", "0 mm", visible_si=lambda v: v.get("tipo") == "libre" or (
                v.get("tipo") == "traslacion" and not v.get("direccion"))),
            Expresion("rx", "Ángulo X", "0 deg", ANGULO, visible_si=t("libre")),
            Expresion("ry", "Ángulo Y", "0 deg", ANGULO, visible_si=t("libre")),
            Expresion("rz", "Ángulo Z", "0 deg", ANGULO, visible_si=t("libre")),
            Seleccion("eje", "Eje", {"eje"}, visible_si=t("rotacion")),
            Expresion("angulo", "Ángulo", "90 deg", ANGULO, visible_si=t("rotacion")),
            Seleccion("origen", "Punto de origen", {"vertice", "punto"},
                      visible_si=t("punto_a_punto", "punto_a_posicion")),
            Seleccion("destino", "Punto de destino", {"vertice", "punto"}, visible_si=t("punto_a_punto")),
            Expresion("x", "X", "0 mm", visible_si=t("punto_a_posicion")),
            Expresion("y", "Y", "0 mm", visible_si=t("punto_a_posicion")),
            Expresion("z", "Z", "0 mm", visible_si=t("punto_a_posicion")),
            Casilla("copiar", "Crear copia"),
            Casilla("ligera", "Copia ligera (comparte la geometría)",
                    visible_si=lambda v: bool(v.get("copiar")) and not caras(v),
                    ayuda="La copia es la MISMA geometría con otra ubicación: editar el original la cambia también."),
        ]

    def construir(self, v, ctx):
        por_caras = v.get("objeto") == "caras"
        exigir(v, "caras" if por_caras else "cuerpos", "Seleccioná las caras a mover." if por_caras
               else "Seleccioná los cuerpos a mover.")
        p = {k: v.get(k) for k in ("tipo", "dx", "dy", "dz", "rx", "ry", "rz", "distancia", "angulo", "x", "y", "z",
                                    "copiar", "ligera")}
        p.update(cuerpos=[] if por_caras else _cuerpos(v), caras=refs(v, "caras") if por_caras else [],
                 ligera=bool(v.get("ligera")) and not por_caras, pivote=ref1(v, "pivote"), direccion=ref1(v, "direccion"), eje=ref1(v, "eje"),
                 origen=ref1(v, "origen"), destino=ref1(v, "destino"))
        return self.crear_op(OpMover, v, ctx, **p)

    def manipuladores(self, ctx, v):
        """La tríada de Fusion en el pivote (libre: flechas, arcos de giro, planos y esfera), la flecha de
        «Trasladar» con dirección, el arco de «Girar» y la tríada de «Punto a posición»."""
        import numpy as np

        from ...nucleo import geometria as geo
        from ...timeline import entidades as ent
        from .. import manipuladores as mp
        ids = [c for c in _cuerpos(v) if c in ctx.estado.cuerpos]
        if not ids:
            return []
        L = lambda k: evaluar_o_cero(ctx, v.get(k))  # noqa: E731
        centros = []
        for c in ids:
            try:
                caja = geo.caja_envolvente(ctx.estado.cuerpos[c].forma)
            except Exception:  # noqa: BLE001 — cuerpos de malla: sin caja exacta
                caja = None
            if caja:
                centros.append((np.array(caja[0]) + np.array(caja[1])) / 2)
        centro = np.mean(centros, axis=0) if centros else np.zeros(3)
        tipo = v.get("tipo")
        if tipo == "libre":
            e = mp.entidad(v["pivote"][0], ctx.estado) if v.get("pivote") else None
            pivote = ent.como_punto(e) if e is not None else centro
            return [mp.Triada(np.asarray(pivote, float) + [L("dx"), L("dy"), L("dz")])]
        if tipo == "traslacion":
            if v.get("direccion"):
                try:
                    d = ent.direccion(mp.entidad(v["direccion"][0], ctx.estado))
                except Exception:  # noqa: BLE001
                    return []
                return [mp.Flecha("distancia", centro, d)]
            return [mp.Triada(centro + [L("dx"), L("dy"), L("dz")], giros=None)]
        if tipo == "rotacion" and v.get("eje"):
            try:
                punto, d = ent.como_eje(mp.entidad(v["eje"][0], ctx.estado))
            except Exception:  # noqa: BLE001
                return []
            d = mp.unitario(d)
            pie = np.asarray(punto, float) + d * float((centro - punto) @ d)
            radio = float(np.linalg.norm(centro - pie))
            return [mp.Angulo("angulo", pie, d, centro - pie, radio if radio > 1e-6 else None)]
        if tipo == "punto_a_posicion":
            return [mp.Triada([L("x"), L("y"), L("z")], claves=("x", "y", "z"), giros=None)]
        return []

    def desde_op(self, op, ctx):
        v = dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado), caras=hits(op.p.get("caras") or [], ctx.estado),
                 objeto="caras" if op.p.get("caras") else "cuerpos")
        for k in ("pivote", "direccion", "eje", "origen", "destino"):
            v[k] = _hit1(op.p.get(k), ctx.estado)
        return v


class ApoyarEnPlano(Comando):
    CLAVE, TITULO, ICONO = "apoyar", "Apoyar en el plano", "alinear"
    AYUDA = "Baja o sube los cuerpos hasta que lo más bajo toque el plano Z = 0. Sin selección: todos."
    CLASE_OP = OpApoyar
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Cuerpos (vacío = todos)", {"cuerpo"}, minimo=0, maximo=None),
                Casilla("juntos", "Mantener posición relativa", True)]

    def construir(self, v, ctx):
        return self.crear_op(OpApoyar, v, ctx, cuerpos=_cuerpos(v), juntos=bool(v.get("juntos", True)))

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado))


class Alinear(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "alinear", "Alinear", "alinear", "Alt+Shift+A"
    AYUDA = "Lleva un punto, plano o eje de los cuerpos sobre otro (las caras quedan enfrentadas)."
    CLASE_OP = OpAlinear
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        geom = {"vertice", "punto", "cara", "plano", "eje", "arista_lineal"}
        return [Seleccion("cuerpos", "Objetos", {"cuerpo"}, maximo=None), Seleccion("origen", "Desde", geom),
                Seleccion("destino", "Hasta", geom), Casilla("voltear", "Voltear"), Casilla("copiar", "Crear copia")]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos.")
        exigir(v, "origen", "Seleccioná la geometría de origen.")
        exigir(v, "destino", "Seleccioná la geometría de destino.")
        return self.crear_op(OpAlinear, v, ctx, cuerpos=_cuerpos(v), origen=ref1(v, "origen"),
                             destino=ref1(v, "destino"), voltear=v["voltear"], copiar=v["copiar"])

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado),
                    origen=_hit1(op.p["origen"], ctx.estado), destino=_hit1(op.p["destino"], ctx.estado))


class Combinar(Comando):
    CLAVE, TITULO, ICONO = "combinar", "Combinar", "combinar"
    AYUDA = "Une, corta o interseca cuerpos (operaciones booleanas)."
    CLASE_OP = OpCombinar

    def verificar(self, ctx):
        return None if len(ctx.estado.cuerpos) >= 2 else "Hacen falta al menos dos cuerpos para combinar."

    def campos(self, ctx):
        return [Seleccion("objetivo", "Cuerpo de destino", {"cuerpo"}),
                Seleccion("herramientas", "Cuerpos de herramienta", {"cuerpo"}, maximo=None),
                Opciones("operacion", "Operación", OPERACIONES_COMBINAR), Casilla("mantener", "Mantener herramientas")]

    def construir(self, v, ctx):
        exigir(v, "objetivo", "Seleccioná el cuerpo de destino.")
        exigir(v, "herramientas", "Seleccioná los cuerpos de herramienta.")
        obj, herr = _cuerpos(v, "objetivo")[0], _cuerpos(v, "herramientas")
        if obj in herr:
            raise ErrorComando("El cuerpo de destino no puede ser también herramienta.")
        return self.crear_op(OpCombinar, v, ctx, objetivo=obj, herramientas=herr, operacion=v["operacion"],
                             mantener=v["mantener"])

    def desde_op(self, op, ctx):
        return dict(op.p, objetivo=_hits_cuerpos(op.p["objetivo"], ctx.estado),
                    herramientas=_hits_cuerpos(op.p["herramientas"], ctx.estado))


class Quitar(Comando):
    CLAVE, TITULO, ICONO = "quitar", "Quitar", "quitar"
    AYUDA = "Saca cuerpos del diseño dejando el paso en el timeline."
    CLASE_OP = OpQuitar
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Objetos", {"cuerpo"}, maximo=None)]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos a quitar.")
        return self.crear_op(OpQuitar, v, ctx, cuerpos=_cuerpos(v))

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado))


class Suprimir(Comando):
    """Suprimir (Supr) de Fusion: borra lo elegido. Caras → «Borrar caras» en el timeline. Un cuerpo
    cuyo paso creador no lo usa nadie más se borra junto con ese paso; si no, se quita con un paso
    «Quitar» (así el resto del timeline sigue funcionando)."""
    CLAVE, TITULO, ICONO, ATAJO = "suprimir", "Suprimir", "suprimir", "Del"
    AYUDA = "Borra cuerpos o caras elegidos."
    SIN_OP = True
    PREVIA = False

    def campos(self, ctx):
        return [Seleccion("objetos", "Objetos", {"cuerpo", "cara"}, maximo=None)]

    def construir(self, v, ctx):
        exigir(v, "objetos", "Seleccioná lo que querés borrar.")
        return None

    def aplicar(self, v, ctx):
        sel = exigir(v, "objetos", "Seleccioná lo que querés borrar.")
        doc, ventana = ctx.doc, ctx.ventana
        caras = [h["ref"] for h in sel if h["ref"]["tipo"] == "cara"]
        cuerpos = [h["ref"]["cuerpo"] for h in sel if h["ref"]["tipo"] == "cuerpo"]
        if caras:
            op = OpBorrarCaras(doc.nuevo_id(), _siguiente(ctx, "Borrar caras"), caras=caras)
            (ventana._agregar if ventana else doc.agregar)(op)
        quitar = []
        for cid in cuerpos:
            op_id = cid.split(".c")[0]
            hermanos = [c for c in doc.estado_final.cuerpos if c.split(".c")[0] == op_id]
            try:
                creador = doc.operacion(op_id)
            except ValueError:
                creador = None
            if creador is not None and len(hermanos) == 1 and not doc.dependientes(op_id):
                doc.eliminar(op_id)
            else:
                quitar.append(cid)
        if quitar:
            op = OpQuitar(doc.nuevo_id(), _siguiente(ctx, "Quitar"), cuerpos=quitar)
            (ventana._agregar if ventana else doc.agregar)(op)


def _siguiente(ctx, base):
    usados = {o.nombre for o in ctx.doc.operaciones}
    n = 1
    while f"{base}{n}" in usados:
        n += 1
    return f"{base}{n}"


# ---------------------------------------------------------------- propiedades (no son pasos del timeline)
class MaterialFisico(Comando):
    CLAVE, TITULO, ICONO = "material_fisico", "Material físico", "material_fisico"
    AYUDA = "Asigna el material (densidad para la masa y su aspecto) a los cuerpos."
    SIN_OP, PREVIA = True, False
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Aplicar a", {"cuerpo"}, maximo=None),
                Opciones("material", "Material", {k: f"{k} ({m['densidad']:g} g/cm³)" for k, m in MATERIALES.items()},
                         "Acero")]

    def construir(self, v, ctx):
        return None

    def aplicar(self, v, ctx):
        ids = _cuerpos(exigir(v, "cuerpos", "Seleccioná los cuerpos."))
        ctx.doc.set_propiedad(ids, "material", v["material"])


class QuitarEmpalmes(Comando):
    """PL6 (Remove Fillets de Plasticity): quita de una vez todos los redondeos de los cuerpos
    elegidos, con filtro por radio máximo; las caras que se van a quitar se resaltan en la vista."""
    CLAVE, TITULO, ICONO = "quitar_empalmes", "Quitar empalmes", "quitar_empalmes"
    AYUDA = ("Saca todos los redondeos (radio <= Radio máximo) de los cuerpos elegidos y une la "
             "topología que queda. Los agujeros taladrados no se tocan.")
    CLASE_OP = OpQuitarEmpalmes
    verificar = staticmethod(_con_cuerpos)
    MODIFICADORES = {}          # el pie del panel muestra Enter/Esc (PL2)

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, maximo=None),
                Expresion("radio_max", "Radio máximo", "5 mm")]

    def previa_vista(self, ctx, v, op):
        """PL6: en la vista se resaltan las caras de empalme que el radio actual detecta."""
        from ...nucleo import geometria as geo
        from ...nucleo.solidos_modificar import caras_de_empalme
        prims = []
        try:
            radio = ctx.evaluar(v["radio_max"])
        except Exception:                       # noqa: BLE001 — expresión a medias: sin resaltado
            return None
        for h in v["cuerpos"]:
            try:
                forma = ctx.estado.cuerpos[h["ref"]["cuerpo"]].forma
            except KeyError:
                continue
            for cara, _radio in caras_de_empalme(forma, radio):
                tris, _norm = geo.teselar(cara)
                prims.append(("tris", tris, None, 0.6))
        return prims or None

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos con empalmes a quitar.")
        return self.crear_op(OpQuitarEmpalmes, v, ctx, cuerpos=_cuerpos(v))

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado))


registrar(ReticulaVolumetrica, CaraDesfase, PulsarTirar, Desfase, Empalme, Chaflan, Vaciado, Desmoldeo, Escala, Combinar, ReemplazarCara,
          DividirCara, DividirCuerpo, DivisionSilueta, MoverCopiar, Alinear, ApoyarEnPlano, Suprimir, Quitar, Aspecto,
          MaterialFisico, QuitarEmpalmes)
