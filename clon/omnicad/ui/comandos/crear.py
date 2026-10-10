# -*- coding: utf-8 -*-
"""Comandos de SÓLIDO › CREAR con diálogo al estilo Fusion (Extruir y Revolución están en solido.py)."""
import numpy as np

from ...timeline.ops_solido import (OpAgujero, OpBarrido, OpBobina, OpLabio, OpNervio, OpPatron, OpRed,
                                    OpRellenoContorno, OpRepujado, OpRosca, OpSaliente, OpSimetria, OpSolevacion,
                                    OpSolidoEnvolvente, OpTuberia)
from ...timeline.parametros import ANGULO, ESCALAR
from ..comando import (Casilla, Comando, Entero, ErrorComando, Expresion, Info, Opciones, Seleccion, Texto, exigir,
                       hit_desde_ref, hits, ref1, refs)
from . import registrar
from .comunes import campo_objetivos, campo_operacion, objetivos

PERFIL = {"perfil", "cara_plana"}
CURVA = {"curva_boceto", "arista"}


def _h1(ref, estado):
    return [hit_desde_ref(ref, estado)] if ref else []


def _cuerpos(lista):
    return [h["ref"]["cuerpo"] for h in lista or [] if h["ref"].get("tipo") == "cuerpo"]


def _hits_cuerpos(ids, estado):
    if isinstance(ids, str):
        ids = [ids] if ids else []
    return hits([{"tipo": "cuerpo", "cuerpo": c} for c in ids], estado)


def _con_objetivos(op, ctx, v):
    v["objetivos"] = _hits_cuerpos(op.p.get("objetivos") or [], ctx.estado)
    return v


class Barrido(Comando):
    CLAVE, TITULO, ICONO = "barrido", "Barrido", "barrido"
    AYUDA = "Lleva un perfil a lo largo de una ruta (y opcionalmente un carril guía)."
    CLASE_OP = OpBarrido

    def campos(self, ctx):
        carril = lambda v: v.get("tipo") == "ruta_carril"  # noqa: E731
        return [Opciones("tipo", "Tipo", {"ruta": "Ruta única", "ruta_carril": "Ruta + carril guía"}),
                Seleccion("perfiles", "Perfil", PERFIL, maximo=None), Seleccion("ruta", "Ruta", CURVA, maximo=None),
                Seleccion("carril", "Carril guía", CURVA, maximo=None, visible_si=carril),
                Expresion("distancia", "Distancia", "1", ESCALAR),
                Opciones("orientacion", "Orientación", {"perpendicular": "Perpendicular", "paralela": "Paralela"},
                         visible_si=lambda v: not carril(v)),
                Opciones("escala_carril", "Escala del perfil", {"escalar": "Escalar", "ninguna": "Ninguna"},
                         visible_si=carril),
                Expresion("conicidad", "Ángulo de conicidad", "0 deg", ANGULO),
                Expresion("torsion", "Ángulo de torsión", "0 deg", ANGULO), campo_operacion(), campo_objetivos()]

    def construir(self, v, ctx):
        exigir(v, "perfiles", "Seleccioná el perfil.")
        exigir(v, "ruta", "Seleccioná la ruta.")
        return self.crear_op(OpBarrido, v, ctx, perfiles=refs(v, "perfiles"), ruta=refs(v, "ruta"),
                             carril=refs(v, "carril") if v.get("tipo") == "ruta_carril" else [],
                             **{k: v[k] for k in ("orientacion", "distancia", "torsion", "conicidad", "escala_carril",
                                                  "operacion")}, objetivos=objetivos(v))

    def desde_op(self, op, ctx):
        v = dict(op.p, tipo="ruta_carril" if op.p.get("carril") else "ruta")
        for k in ("perfiles", "ruta", "carril"):
            v[k] = hits(op.p[k], ctx.estado)
        return _con_objetivos(op, ctx, v)


class Solevacion(Comando):
    CLAVE, TITULO, ICONO = "solevacion", "Solevación", "solevacion"
    AYUDA = "Crea un sólido que pasa por varios perfiles en orden (opcional: carril o línea central)."
    CLASE_OP = OpSolevacion

    def campos(self, ctx):
        return [Seleccion("secciones", "Perfiles (en orden)", PERFIL | CURVA | {"vertice", "punto"}, maximo=None),
                Opciones("guia", "Tipo de guía", {"carriles": "Carriles", "linea_central": "Línea central"}),
                Seleccion("carriles", "Carriles", CURVA, minimo=0, maximo=1,
                          visible_si=lambda v: v.get("guia") == "carriles"),
                Seleccion("linea_central", "Línea central", CURVA, minimo=0, maximo=None,
                          visible_si=lambda v: v.get("guia") == "linea_central"),
                Casilla("cerrada", "Cerrado"), Casilla("reglada", "Tramos rectos"), campo_operacion(),
                campo_objetivos()]

    def construir(self, v, ctx):
        if len(v.get("secciones") or []) < 2:
            raise ErrorComando("Seleccioná al menos dos perfiles, en orden.")
        guia = v.get("guia")
        return self.crear_op(OpSolevacion, v, ctx, secciones=refs(v, "secciones"),
                             carriles=refs(v, "carriles") if guia == "carriles" else [],
                             linea_central=refs(v, "linea_central") if guia == "linea_central" else [],
                             cerrada=v["cerrada"], reglada=v["reglada"], operacion=v["operacion"],
                             objetivos=objetivos(v))

    def desde_op(self, op, ctx):
        v = dict(op.p, guia="linea_central" if op.p.get("linea_central") else "carriles")
        for k in ("secciones", "carriles", "linea_central"):
            v[k] = hits(op.p[k], ctx.estado)
        return _con_objetivos(op, ctx, v)


class _NervioRed(Comando):
    CLASE_OP = OpNervio

    def campos(self, ctx):
        return [Seleccion("curvas", "Curvas", {"curva_boceto"}, maximo=None),
                Expresion("espesor", "Grosor", "2 mm"),
                Opciones("extension", "Tipo de extensión", {"hasta_siguiente": "Hasta el siguiente",
                                                            "profundidad": "Profundidad"}),
                Expresion("profundidad", "Profundidad", "10 mm",
                          visible_si=lambda v: v.get("extension") == "profundidad"),
                Opciones("direccion", "Opciones de grosor", {"simetrica": "Simétrica", "lado1": "Un lado",
                                                             "lado2": "Otro lado"}),
                Casilla("invertir", "Invertir dirección"),
                Seleccion("objetivo", "Cuerpo", {"cuerpo"}, minimo=0, ayuda="Sin selección: el más cercano.")]

    def construir(self, v, ctx):
        exigir(v, "curvas", "Seleccioná las curvas del boceto.")
        ctx.evaluar(v["espesor"])
        obj = _cuerpos(v.get("objetivo"))
        return self.crear_op(self.CLASE_OP, v, ctx, curvas=refs(v, "curvas"), objetivo=obj[0] if obj else "",
                             **{k: v[k] for k in ("espesor", "extension", "profundidad", "direccion", "invertir")})

    def desde_op(self, op, ctx):
        return dict(op.p, curvas=hits(op.p["curvas"], ctx.estado), objetivo=_hits_cuerpos(op.p.get("objetivo"),
                                                                                         ctx.estado))


class Nervio(_NervioRed):
    CLAVE, TITULO, ICONO = "nervio", "Nervio", "nervio"
    AYUDA = "Pared de refuerzo desde una curva abierta del boceto hasta el cuerpo."
    CLASE_OP = OpNervio


class Red(_NervioRed):
    CLAVE, TITULO, ICONO = "red", "Red", "red"
    AYUDA = "Red de nervios desde varias curvas abiertas, perpendicular al boceto."
    CLASE_OP = OpRed


class Repujado(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "repujado", "Repujado", "repujado", "Shift+E"
    AYUDA = "Relieve o grabado de perfiles o texto sobre una cara (también envuelto en un cilindro)."
    CLASE_OP = OpRepujado

    def campos(self, ctx):
        return [Seleccion("perfiles", "Perfiles", PERFIL, maximo=None), Seleccion("cara", "Cara", {"cara"}),
                Opciones("tipo", "Tipo", {"relieve": "Relieve", "grabado": "Grabado"}),
                Expresion("profundidad", "Profundidad", "1 mm"), Casilla("envolver", "Envolver en la cara")]

    def construir(self, v, ctx):
        exigir(v, "perfiles", "Seleccioná los perfiles.")
        exigir(v, "cara", "Seleccioná la cara.")
        return self.crear_op(OpRepujado, v, ctx, perfiles=refs(v, "perfiles"), cara=ref1(v, "cara"),
                             profundidad=v["profundidad"], tipo=v["tipo"], envolver=v["envolver"])

    def desde_op(self, op, ctx):
        return dict(op.p, perfiles=hits(op.p["perfiles"], ctx.estado), cara=_h1(op.p["cara"], ctx.estado))


class Agujero(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "agujero", "Agujero", "agujero", "H"
    AYUDA = "Agujeros simples, abocardados o avellanados, pasantes o ciegos, lisos o roscados."
    CLASE_OP = OpAgujero

    def campos(self, ctx):
        t = lambda *x: (lambda v: v.get("tipo") in x)  # noqa: E731
        return [
            Seleccion("colocacion", "Puntos / cara", {"punto", "vertice", "cara_plana"}, maximo=None,
                      ayuda="Puntos de boceto (varios agujeros) o un clic sobre una cara plana."),
            Opciones("extension", "Extensión", {"distancia": "Distancia", "todo": "Todo"}),
            Opciones("tipo", "Tipo de agujero", {"simple": "Simple", "abocardado": "Abocardado",
                                                 "avellanado": "Avellanado"}),
            Opciones("rosca", "Tipo de rosca", {"simple": "Simple (sin rosca)", "cosmetica": "Roscado (cosmético)",
                                                "modelada": "Roscado (modelado)"}),
            Texto("designacion", "Tamaño de rosca", "M6",
                  visible_si=lambda v: v.get("rosca") != "simple"),
            Expresion("diametro", "Diámetro", "6 mm", visible_si=lambda v: v.get("rosca") != "modelada"),
            Expresion("profundidad", "Profundidad", "10 mm", visible_si=lambda v: v.get("extension") == "distancia"),
            Opciones("punta", "Punta del taladro", {"angulo": "En ángulo", "plana": "Plana"}),
            Expresion("angulo_punta", "Ángulo de la punta", "118 deg", ANGULO,
                      visible_si=lambda v: v.get("punta") == "angulo"),
            Expresion("diam_abocardado", "Diámetro de abocardado", "10 mm", visible_si=t("abocardado")),
            Expresion("prof_abocardado", "Profundidad de abocardado", "4 mm", visible_si=t("abocardado")),
            Expresion("diam_avellanado", "Diámetro de avellanado", "12 mm", visible_si=t("avellanado")),
            Expresion("angulo_avellanado", "Ángulo de avellanado", "90 deg", ANGULO, visible_si=t("avellanado")),
            Casilla("invertir", "Invertir dirección"), campo_objetivos(),
        ]

    def construir(self, v, ctx):
        sel = exigir(v, "colocacion", "Elegí puntos de boceto o hacé clic sobre una cara plana.")
        posiciones = [h["ref"] for h in sel if h["ref"]["tipo"] != "cara"]
        puntos_cara = [{"cara": h["ref"], "punto": [float(c) for c in np.asarray(h.get("punto"), float)]}
                       for h in sel if h["ref"]["tipo"] == "cara" and h.get("punto") is not None]
        if v.get("rosca") != "simple":
            from ...nucleo.solidos_crear import datos_rosca
            try:
                datos_rosca(v.get("designacion") or "")
            except Exception as e:  # noqa: BLE001
                raise ErrorComando(f"Tamaño de rosca desconocido: {v.get('designacion')}") from e
        params = {k: v[k] for k in ("tipo", "diametro", "extension", "profundidad", "punta", "angulo_punta",
                                     "diam_abocardado", "prof_abocardado", "diam_avellanado", "angulo_avellanado",
                                     "rosca", "designacion", "invertir")}
        return self.crear_op(OpAgujero, v, ctx, posiciones=posiciones, puntos_cara=puntos_cara, objetivos=objetivos(v),
                             **params)

    def manipuladores(self, ctx, v):
        """Flecha de profundidad en el primer agujero: sale del fondo y apunta hacia el material."""
        from .. import manipuladores as mp
        if v.get("extension") != "distancia" or not v.get("colocacion"):
            return []
        try:
            punto, direccion = self.construir(v, ctx)._colocaciones(ctx.estado)[0]
        except Exception:  # noqa: BLE001 — sin colocación válida no hay flecha
            return []
        return [mp.Flecha("profundidad", punto, direccion, minimo=0.0)]

    def previa_vista(self, ctx, v, op):
        """Como Fusion, el agujero se ve en ROJO mientras el diálogo está abierto (lo que se va a quitar)."""
        from ...nucleo import geometria as geo
        from ...nucleo import solidos_crear as sc
        from .. import manipuladores as mp
        p = op.p
        A = lambda k: ctx.evaluar(p[k], ANGULO)  # noqa: E731
        L = lambda k: ctx.evaluar(p[k])  # noqa: E731
        if p["rosca"] == "modelada":             # en la vista previa basta el diámetro menor (sin el surco)
            diametro = sc.datos_rosca(p["designacion"])["diametro_menor"]
        else:
            diametro = L("diametro")
        opciones = {"tipo": p["tipo"], "diametro": diametro, "punta": p["punta"], "angulo_punta": A("angulo_punta")}
        if p["tipo"] == "abocardado":
            opciones.update(diam_abocardado=L("diam_abocardado"), prof_abocardado=L("prof_abocardado"))
        elif p["tipo"] == "avellanado":
            opciones.update(diam_avellanado=L("diam_avellanado"), angulo_avellanado=A("angulo_avellanado"))
        if p["extension"] == "distancia":
            profundidad = L("profundidad")
        else:                                    # «Todo»: hasta atravesar todos los cuerpos
            cajas = [geo.caja_envolvente(c.forma) for c in ctx.estado.cuerpos.values()
                     if getattr(c, "tipo", "solido") == "solido"]
            cajas = [c for c in cajas if c]
            if not cajas:
                return None
            profundidad = max(float(np.linalg.norm(np.subtract(b, a))) for a, b in cajas) * 2
        herramientas = [sc.herramienta_agujero(punto, d, profundidad=profundidad, **opciones)
                        for punto, d in op._colocaciones(ctx.estado)]
        return mp.herramientas_rojas(herramientas)

    def desde_op(self, op, ctx):
        sel = hits(op.p["posiciones"], ctx.estado)
        for d in op.p.get("puntos_cara") or []:
            h = hit_desde_ref(d["cara"], ctx.estado)
            h["punto"] = np.asarray(d["punto"], float)
            sel.append(h)
        return _con_objetivos(op, ctx, dict(op.p, colocacion=sel))


class Rosca(Comando):
    CLAVE, TITULO, ICONO = "rosca", "Rosca", "rosca"
    AYUDA = "Rosca sobre caras cilíndricas (tamaño automático, cosmética o modelada)."
    CLASE_OP = OpRosca

    def campos(self, ctx):
        return [Seleccion("caras", "Caras", {"cara"}, maximo=None),
                Casilla("modelada", "Modelado", True),
                Casilla("largo_completo", "Longitud completa", True),
                Expresion("longitud", "Longitud", "10 mm", visible_si=lambda v: not v.get("largo_completo")),
                Expresion("desfase", "Desfase", "0 mm", visible_si=lambda v: not v.get("largo_completo")),
                Texto("designacion", "Tamaño (vacío = automático)", ""),
                Opciones("mano", "Dirección", {"derecha": "Derecha", "izquierda": "Izquierda"}),
                Casilla("invertir", "Invertir")]

    def construir(self, v, ctx):
        exigir(v, "caras", "Seleccioná las caras cilíndricas.")
        return self.crear_op(OpRosca, v, ctx, caras=refs(v, "caras"),
                             **{k: v[k] for k in ("designacion", "largo_completo", "longitud", "desfase", "modelada",
                                                  "mano", "invertir")})

    def desde_op(self, op, ctx):
        return dict(op.p, caras=hits(op.p["caras"], ctx.estado))


class Bobina(Comando):
    CLAVE, TITULO, ICONO = "bobina", "Bobina", "bobina"
    AYUDA = "Resorte o hélice con sección circular, cuadrada o triangular."
    CLASE_OP = OpBobina

    def campos(self, ctx):
        t = lambda *x: (lambda v: v.get("tipo") in x)  # noqa: E731
        return [Seleccion("plano", "Plano", {"plano", "cara_plana"}, minimo=0, ayuda="Sin selección: plano XY."),
                Seleccion("centro", "Centro", {"punto", "vertice"}, minimo=0, ayuda="Sin selección: el origen del plano."),
                Expresion("diametro", "Diámetro", "20 mm"),
                Opciones("tipo", "Tipo", {"rev_altura": "Revoluciones y altura", "rev_paso": "Revoluciones y paso",
                                          "altura_paso": "Altura y paso"}),
                Expresion("revoluciones", "Revoluciones", "5", ESCALAR, visible_si=t("rev_altura", "rev_paso")),
                Expresion("altura", "Altura", "30 mm", visible_si=t("rev_altura", "altura_paso")),
                Expresion("paso", "Paso", "6 mm", visible_si=t("rev_paso", "altura_paso")),
                Expresion("angulo", "Ángulo", "0 deg", ANGULO),
                Opciones("seccion", "Sección", {"circular": "Circular", "cuadrada": "Cuadrada",
                                                "triangular_externa": "Triangular (externa)",
                                                "triangular_interna": "Triangular (interna)"}),
                Opciones("posicion", "Posición de la sección", {"sobre": "Sobre", "dentro": "Dentro", "fuera": "Fuera"}),
                Expresion("tamano", "Tamaño de la sección", "3 mm"), Casilla("horario", "Sentido horario"),
                campo_operacion(), campo_objetivos()]

    def construir(self, v, ctx):
        ctx.evaluar(v["diametro"])
        return self.crear_op(OpBobina, v, ctx, plano=ref1(v, "plano"), centro=ref1(v, "centro"), objetivos=objetivos(v),
                             **{k: v[k] for k in ("diametro", "tipo", "revoluciones", "altura", "paso", "angulo",
                                                  "seccion", "tamano", "posicion", "horario", "operacion")})

    def desde_op(self, op, ctx):
        return _con_objetivos(op, ctx, dict(op.p, plano=_h1(op.p["plano"], ctx.estado),
                                            centro=_h1(op.p["centro"], ctx.estado)))


class Tuberia(Comando):
    CLAVE, TITULO, ICONO = "tuberia", "Tubería", "tuberia"
    AYUDA = "Caño de sección circular, cuadrada o triangular a lo largo de una ruta."
    CLASE_OP = OpTuberia

    def campos(self, ctx):
        return [Seleccion("ruta", "Ruta", CURVA, maximo=None), Expresion("distancia", "Distancia", "1", ESCALAR),
                Opciones("seccion", "Sección", {"circular": "Circular", "cuadrada": "Cuadrada",
                                                "triangular": "Triangular"}),
                Expresion("tamano", "Tamaño de la sección", "5 mm"), Casilla("hueca", "Hueco"),
                Expresion("espesor", "Grosor de pared", "0.5 mm", visible_si=lambda v: bool(v.get("hueca"))),
                campo_operacion(), campo_objetivos()]

    def construir(self, v, ctx):
        exigir(v, "ruta", "Seleccioná la ruta.")
        return self.crear_op(OpTuberia, v, ctx, ruta=refs(v, "ruta"), objetivos=objetivos(v),
                             **{k: v[k] for k in ("distancia", "seccion", "tamano", "hueca", "espesor", "operacion")})

    def desde_op(self, op, ctx):
        return _con_objetivos(op, ctx, dict(op.p, ruta=hits(op.p["ruta"], ctx.estado)))


class _Patron(Comando):
    CLASE_OP = OpPatron
    FORMA = "rectangular"

    def campos(self, ctx):
        base = [Seleccion("cuerpos", "Objetos (cuerpos)", {"cuerpo"}, maximo=None)]
        if self.FORMA == "rectangular":
            base += [Seleccion("dir1", "Dirección 1", {"eje", "arista_lineal", "plano", "cara_plana"}),
                     Opciones("distribucion", "Distribución", {"extension": "Extensión", "espaciado": "Espaciado"}),
                     Entero("n1", "Cantidad 1", 3, 1), Expresion("d1", "Distancia 1", "30 mm"),
                     Seleccion("dir2", "Dirección 2", {"eje", "arista_lineal", "plano", "cara_plana"}, minimo=0),
                     Entero("n2", "Cantidad 2", 1, 1), Expresion("d2", "Distancia 2", "30 mm")]
        elif self.FORMA == "circular":
            base += [Seleccion("eje", "Eje", {"eje"}),
                     Opciones("distribucion", "Tipo", {"extension": "Completo", "espaciado": "Ángulo entre copias"}),
                     Entero("n", "Cantidad", 6, 1), Expresion("angulo", "Ángulo total / entre copias", "360 deg", ANGULO)]
        else:
            base += [Seleccion("ruta", "Ruta", CURVA, maximo=None),
                     Opciones("distribucion", "Distribución", {"extension": "Extensión", "espaciado": "Espaciado"}),
                     Entero("n1", "Cantidad", 3, 1), Expresion("d1", "Distancia", "30 mm"),
                     Expresion("inicio", "Punto de inicio (0 a 1)", "0", ESCALAR),
                     Opciones("orientacion", "Orientación", {"identica": "Idéntica", "direccion_ruta": "Dirección de ruta"})]
        return base + [Casilla("simetrico", "Simétrico"), Texto("suprimir", "Suprimir copias (n.º, separados por coma)", ""),
                       Casilla("combinar", "Unir al original")]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos.")
        try:
            suprimir = [int(x) for x in str(v.get("suprimir") or "").replace(";", ",").split(",") if x.strip()]
        except ValueError as e:
            raise ErrorComando("En «Suprimir copias» van números separados por coma.") from e
        params = {k: v.get(k) for k in ("n1", "d1", "n2", "d2", "distribucion", "simetrico", "n", "angulo", "orientacion",
                                         "inicio", "combinar") if k in v}
        params.update(forma_patron=self.FORMA, cuerpos=_cuerpos(v["cuerpos"]), dir1=ref1(v, "dir1"),
                      dir2=ref1(v, "dir2"), eje=ref1(v, "eje"), ruta=refs(v, "ruta"), suprimir=suprimir)
        return self.crear_op(OpPatron, v, ctx, **params)

    def desde_op(self, op, ctx):
        v = dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado), ruta=hits(op.p.get("ruta"), ctx.estado),
                 suprimir=", ".join(str(i) for i in op.p.get("suprimir") or []))
        for k in ("dir1", "dir2", "eje"):
            v[k] = _h1(op.p.get(k), ctx.estado)
        return v


class PatronRectangular(_Patron):
    CLAVE, TITULO, ICONO, FORMA = "patron_rectangular_3d", "Patrón rectangular", "patron_rectangular_3d", "rectangular"
    AYUDA = "Copias en filas y columnas."
    VARIANTE = ("forma_patron", "rectangular")


class PatronCircular(_Patron):
    CLAVE, TITULO, ICONO, FORMA = "patron_circular_3d", "Patrón circular", "patron_circular_3d", "circular"
    AYUDA = "Copias alrededor de un eje."
    VARIANTE = ("forma_patron", "circular")


class PatronRuta(_Patron):
    CLAVE, TITULO, ICONO, FORMA = "patron_ruta", "Patrón en trayectoria", "patron_ruta", "ruta"
    AYUDA = "Copias a lo largo de una curva."
    VARIANTE = ("forma_patron", "ruta")


class Simetria(Comando):
    CLAVE, TITULO, ICONO = "simetria_3d", "Simetría", "simetria_3d"
    AYUDA = "Copia reflejada de cuerpos respecto de un plano."
    CLASE_OP = OpSimetria

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Objetos (cuerpos)", {"cuerpo"}, maximo=None),
                Seleccion("plano", "Plano de simetría", {"plano", "cara_plana"}), Casilla("combinar", "Unir al original")]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos.")
        exigir(v, "plano", "Seleccioná el plano de simetría.")
        return self.crear_op(OpSimetria, v, ctx, cuerpos=_cuerpos(v["cuerpos"]), plano=ref1(v, "plano"),
                             combinar=v["combinar"])

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado), plano=_h1(op.p["plano"], ctx.estado))


class RellenoContorno(Comando):
    CLAVE, TITULO, ICONO = "relleno_contorno", "Llenado de contorno", "relleno_contorno"
    AYUDA = "Rellena con sólido el volumen encerrado por cuerpos, superficies y planos."
    CLASE_OP = OpRellenoContorno

    def campos(self, ctx):
        return [Seleccion("herramientas", "Herramientas", {"cuerpo", "cara", "plano"}, maximo=None),
                Info("info", "Celdas", self._celdas), Texto("celdas", "Celdas a rellenar (n.º)", "1"),
                campo_operacion(), campo_objetivos()]

    def _celdas(self, v, ctx):
        if not v.get("herramientas"):
            return "Elegí las herramientas."
        op = OpRellenoContorno("tmp", herramientas=refs(v, "herramientas"))
        from ...nucleo import solidos_crear
        celdas = solidos_crear.relleno_contorno_celdas(op.formas_herramienta(ctx.estado))
        return "\n".join(f"{i}: {c['volumen']:.1f} mm³" for i, c in enumerate(celdas, 1)) or "No encierran volumen."

    def construir(self, v, ctx):
        exigir(v, "herramientas", "Seleccioná las herramientas.")
        try:
            celdas = [int(x) - 1 for x in str(v.get("celdas") or "1").replace(";", ",").split(",") if x.strip()]
        except ValueError as e:
            raise ErrorComando("Escribí los números de celda separados por coma.") from e
        return self.crear_op(OpRellenoContorno, v, ctx, herramientas=refs(v, "herramientas"), celdas=celdas,
                             operacion=v["operacion"], objetivos=objetivos(v))

    def desde_op(self, op, ctx):
        return _con_objetivos(op, ctx, dict(op.p, herramientas=hits(op.p["herramientas"], ctx.estado),
                                            celdas=", ".join(str(i + 1) for i in op.p["celdas"])))


class SolidoEnvolvente(Comando):
    CLAVE, TITULO, ICONO = "cuerpo_envolvente", "Sólido envolvente", "cuerpo_envolvente"
    AYUDA = "Caja o cilindro que encierra los cuerpos elegidos."
    CLASE_OP = OpSolidoEnvolvente

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, maximo=None),
                Opciones("tipo", "Forma", {"caja": "Caja", "cilindro": "Cilindro"}),
                Opciones("eje", "Eje del cilindro", {"z": "Z", "x": "X", "y": "Y"},
                         visible_si=lambda v: v.get("tipo") == "cilindro"),
                Expresion("margen", "Desfase", "0 mm"), campo_operacion(), campo_objetivos()]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos.")
        return self.crear_op(OpSolidoEnvolvente, v, ctx, cuerpos=_cuerpos(v["cuerpos"]), objetivos=objetivos(v),
                             **{k: v[k] for k in ("tipo", "margen", "eje", "operacion")})

    def desde_op(self, op, ctx):
        return _con_objetivos(op, ctx, dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado)))


class Saliente(Comando):
    CLAVE, TITULO, ICONO = "saliente", "Saliente", "saliente"
    AYUDA = "Columna para tornillo (plástico) en puntos de boceto."
    CLASE_OP = OpSaliente

    def campos(self, ctx):
        return [Seleccion("posiciones", "Puntos", {"punto", "vertice"}, maximo=None),
                Expresion("diametro_exterior", "Diámetro exterior", "8 mm"),
                Expresion("diametro_agujero", "Diámetro del agujero", "3 mm"),
                Expresion("altura", "Altura (vacío = hasta el cuerpo)", ""),
                Expresion("angulo_desmoldeo", "Ángulo de desmoldeo", "0 deg", ANGULO), Casilla("invertir", "Invertir")]

    def construir(self, v, ctx):
        exigir(v, "posiciones", "Seleccioná los puntos.")
        # El sentido no se elige (Fusion solo tiene «Invertir»): al editar se conserva el del paso (una receta
        # vieja sigue con "plano"); un saliente nuevo usa el automático.
        sentido = ctx.op.p.get("sentido", "plano") if ctx.op is not None else OpSaliente.PARAMS["sentido"]
        return self.crear_op(OpSaliente, v, ctx, posiciones=refs(v, "posiciones"), sentido=sentido,
                             **{k: v[k] for k in ("diametro_exterior", "diametro_agujero", "altura", "angulo_desmoldeo",
                                                  "invertir")})

    def desde_op(self, op, ctx):
        return dict(op.p, posiciones=hits(op.p["posiciones"], ctx.estado))


class Labio(Comando):
    CLAVE, TITULO, ICONO = "labio", "Labio y ranura", "labio"
    AYUDA = "Labio o ranura a lo largo del borde de una pared (carcasas de plástico)."
    CLASE_OP = OpLabio

    def campos(self, ctx):
        return [Seleccion("aristas", "Aristas del borde", {"arista"}, maximo=None),
                Opciones("tipo", "Tipo", {"labio": "Labio", "ranura": "Ranura"}),
                Expresion("ancho", "Ancho", "1 mm"), Expresion("alto", "Alto", "1.5 mm"),
                Expresion("holgura", "Holgura", "0.1 mm", visible_si=lambda v: v.get("tipo") == "ranura"),
                Seleccion("direccion", "Dirección de tirado", {"plano", "cara_plana", "eje", "arista_lineal"}, minimo=0),
                Casilla("invertir", "Invertir")]

    def construir(self, v, ctx):
        exigir(v, "aristas", "Seleccioná las aristas del borde.")
        return self.crear_op(OpLabio, v, ctx, aristas=refs(v, "aristas"), direccion=ref1(v, "direccion"),
                             **{k: v[k] for k in ("tipo", "ancho", "alto", "holgura", "invertir")})

    def desde_op(self, op, ctx):
        return dict(op.p, aristas=hits(op.p["aristas"], ctx.estado), direccion=_h1(op.p["direccion"], ctx.estado))


registrar(Barrido, Solevacion, Nervio, Red, Repujado, Agujero, Rosca, Bobina, Tuberia, PatronRectangular,
          PatronCircular, PatronRuta, Simetria, RellenoContorno, SolidoEnvolvente, Saliente, Labio)
