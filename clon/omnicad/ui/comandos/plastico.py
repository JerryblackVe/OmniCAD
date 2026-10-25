# -*- coding: utf-8 -*-
"""PLÁSTICO › Configuración: Asignar regla de plástico y Administrar reglas (la biblioteca vive en `nucleo/plastico.py`)."""
from ...nucleo import geometria as geo
from ...nucleo import plastico
from ...timeline.ops_solido import OpPatronGeometrico, OpReglaPlastico
from ...timeline.parametros import ESCALAR
from ..comando import (ANGULO, Casilla, Comando, Entero, ErrorComando, Expresion, Info, Opciones, Seleccion, Texto, exigir,
                       hits, refs)
from . import registrar
from .comunes import campo_objetivos, campo_operacion, objetivos


def _reglas():
    return {**plastico.REGLAS, **plastico.REGLAS_USUARIO}


class AsignarReglaPlastico(Comando):
    CLAVE, TITULO, ICONO = "asignar_regla_plastico", "Asignar regla de plástico", "regla_plastico"
    AYUDA = ("Asigna una regla de plástico (material, espesor, ángulo de desmoldeo y radio) a un componente: "
             "su material pasa a todos sus cuerpos.")
    CLASE_OP = OpReglaPlastico

    def campos(self, ctx):
        comps = {k: d.get("nombre") or k for k, d in ctx.estado.componentes.items()}
        return [Opciones("componente", "Componente", comps or {"": "(no hay componentes)"}),
                Opciones("regla", "Regla de plástico", {n: n for n in _reglas()}, plastico.REGLA_DEFECTO)]

    def construir(self, v, ctx):
        exigir(v, "componente", "Creá un componente (ENSAMBLAR › Nuevo componente) y elegilo.")
        return self.crear_op(OpReglaPlastico, v, ctx, componente=v["componente"], regla=dict(_reglas()[v["regla"]]))

    def desde_op(self, op, ctx):
        return {"componente": op.p["componente"], "regla": (op.p.get("regla") or {}).get("nombre", plastico.REGLA_DEFECTO)}


class AdministrarReglasPlastico(Comando):
    CLAVE, TITULO, ICONO = "reglas_plastico", "Administrar reglas de plástico", "reglas_plastico"
    AYUDA = ("Crea una regla de plástico propia (queda guardada en tu biblioteca) o borra una propia. "
             "Las de fábrica no se pisan ni se borran.")
    SIN_OP, TEXTO_ACEPTAR = True, "Aplicar"

    def campos(self, ctx):
        crear = lambda v: v.get("accion") == "crear"  # noqa: E731
        return [Opciones("accion", "Acción", {"crear": "Crear regla", "borrar": "Borrar regla propia"}),
                Texto("nombre", "Nombre"),
                Expresion("espesor", "Espesor de pared", "2 mm", visible_si=crear),
                Expresion("angulo", "Ángulo de desmoldeo", "1 deg", tipo=ANGULO, visible_si=crear),
                Texto("material", "Material físico (opcional)", visible_si=crear)]

    def aplicar(self, v, ctx):
        nombre = str(exigir(v, "nombre", "Escribí el nombre de la regla.")).strip()
        try:
            if v["accion"] == "borrar":
                propio = next((n for n in plastico.REGLAS_USUARIO if n.casefold() == nombre.casefold()), None)
                if propio is None:
                    raise ErrorComando(f"No hay una regla propia llamada «{nombre}».")
                plastico.quitar_regla(propio)
                return
            if any(n.casefold() == nombre.casefold() for n in _reglas()):
                raise ErrorComando(f"Ya existe una regla llamada «{nombre}».")
            plastico.definir_regla({"nombre": nombre, "espesor": ctx.evaluar(v["espesor"]),
                                    "angulo_desmoldeo": ctx.evaluar(v["angulo"], ANGULO),
                                    "material": (v.get("material") or "").strip() or None})
        except geo.ErrorGeometria as e:
            raise ErrorComando(str(e)) from e


class PatronGeometrico(Comando):
    CLAVE, TITULO, ICONO = "patron_geometrico", "Patrón geométrico", "patron_geometrico"
    AYUDA = ("Reparte esferas, cilindros, cajas u objetos a medida sobre una cara plana con un gradiente de tamaño: "
             "del tamaño 1 en el centro al tamaño 2 en la esquina de la cara.")
    CLASE_OP = OpPatronGeometrico

    def campos(self, ctx):
        es = lambda *d: (lambda v: v.get("distribucion") in d)  # noqa: E731
        rejilla = es("rectangular", "triangular", "hexagonal")
        return [Seleccion("caras", "Caras", {"cara_plana"}, maximo=None),
                Opciones("objeto", "Tipo de objeto", {"esfera": "Esfera", "cilindro": "Cilindro", "caja": "Caja",
                                                      "personalizado": "A medida"}),
                Seleccion("personalizado", "Cuerpo a repetir", {"cuerpo"}, minimo=0,
                          visible_si=lambda v: v.get("objeto") == "personalizado"),
                Expresion("tamano1", "Límite de tamaño 1 (centro)", "2 mm"),
                Expresion("tamano2", "Límite de tamaño 2 (esquina)", "4 mm"),
                Expresion("dispersion", "Dispersión", "1", ESCALAR),
                Opciones("distribucion", "Distribución", {"rectangular": "Rectangular", "triangular": "Triangular",
                                                          "hexagonal": "Hexagonal", "circular": "Circular",
                                                          "radial": "Radial"}),
                Opciones("separacion", "Tipo de separación", {"incremento": "Incremento", "extension": "Extensión"},
                         visible_si=es("rectangular")),
                Expresion("distancia", "Distancia", "6 mm", visible_si=lambda v: rejilla(v) and v.get("separacion") != "extension"),
                Entero("cantidad_u", "Cantidad en U", 5, 1, 1000,
                       visible_si=lambda v: rejilla(v) and v.get("separacion") == "extension"),
                Entero("cantidad_v", "Cantidad en V", 5, 1, 1000,
                       visible_si=lambda v: es("rectangular")(v) and v.get("separacion") == "extension"),
                Expresion("distancia_radial", "Distancia radial", "6 mm", visible_si=es("circular", "radial")),
                Entero("rayos", "Rayos", 8, 1, 1000, visible_si=es("radial")),
                Opciones("orientacion", "Orientación", {"cara": "Dirección de la cara", "paralela": "Dirección paralela"}),
                Opciones("alineacion_u", "Alineación en U", {"izquierda": "Izquierda", "centro": "Centro", "derecha": "Derecha"},
                         "centro", visible_si=rejilla),
                Expresion("desfase_u", "Desfase en U", "0 mm"),
                Opciones("alineacion_v", "Alineación en V", {"abajo": "Abajo", "medio": "Medio", "arriba": "Arriba"},
                         "medio", visible_si=rejilla),
                Expresion("desfase_v", "Desfase en V", "0 mm"),
                Casilla("limpiar_perimetro", "Limpiar perímetro", True),
                Expresion("desfase_perimetro", "Desfase del perímetro", "0 mm"),
                campo_operacion("cortar"), campo_objetivos()]

    def construir(self, v, ctx):
        exigir(v, "caras", "Seleccioná las caras planas donde va el patrón.")
        if v.get("objeto") == "personalizado":
            exigir(v, "personalizado", "Seleccioná el cuerpo que se repite.")
        for k in ("tamano1", "tamano2", "distancia", "distancia_radial", "desfase_u", "desfase_v", "desfase_perimetro"):
            ctx.evaluar(v[k])
        ctx.evaluar(v["dispersion"], ESCALAR)
        cuerpo = [h["ref"] for h in v.get("personalizado") or []][:1]
        return self.crear_op(OpPatronGeometrico, v, ctx, caras=refs(v, "caras"), personalizado=cuerpo[0] if cuerpo else None,
                             objetivos=objetivos(v),
                             **{k: v[k] for k in ("objeto", "tamano1", "tamano2", "dispersion", "distribucion", "separacion",
                                                  "distancia", "cantidad_u", "cantidad_v", "distancia_radial", "rayos",
                                                  "orientacion", "alineacion_u", "desfase_u", "alineacion_v", "desfase_v",
                                                  "limpiar_perimetro", "desfase_perimetro", "operacion")})

    def desde_op(self, op, ctx):
        v = dict(op.p, caras=hits(op.p["caras"], ctx.estado),
                 personalizado=hits([op.p["personalizado"]], ctx.estado) if op.p.get("personalizado") else [])
        v["objetivos"] = hits([{"tipo": "cuerpo", "cuerpo": c} for c in op.p.get("objetivos") or []], ctx.estado)
        return v


class ConsejosDiseno(Comando):
    CLAVE, TITULO, ICONO = "consejos_diseno", "Consejos de diseño", "consejos_diseno"
    AYUDA = ("Revisa un cuerpo para moldeo por inyección contra su regla de plástico y la dirección de extracción: "
             "espesor, contrasalidas, desmoldeo y filos, con un consejo para cada alerta.")
    SIN_OP, TEXTO_ACEPTAR = True, "Cerrar"
    _NOMBRES = {"too_thin": "Pared muy fina", "too_thick": "Pared muy gruesa", "variation": "Variación de espesor",
                "undercut": "Contrasalida", "draft": "Desmoldeo insuficiente", "knife_edge": "Filo"}

    def campos(self, ctx):
        return [Seleccion("cuerpo", "Cuerpo sólido", {"cuerpo"}),
                Opciones("eje", "Dirección de extracción", {"Z": "Eje Z", "Y": "Eje Y", "X": "Eje X"}),
                Casilla("invertir", "Invertir dirección"),
                Casilla("analizar", "Analizar ahora", False, ayuda="Revisar tarda en cuerpos grandes: se hace al marcarla."),
                Info("resultado", "Resultado", self._resultado)]

    def _resultado(self, v, ctx):
        from ... import api
        if not v.get("cuerpo"):
            return "Elegí un cuerpo sólido."
        if not v.get("analizar"):
            return "Marcá «Analizar ahora» para revisar el cuerpo."
        ses = api.Sesion(ctx.doc)
        r = api.llamar(ses, "design_advice", {"body": v["cuerpo"][0]["ref"]["cuerpo"], "pull_direction": v["eje"],
                                              "flip": bool(v.get("invertir"))})
        if not r["ok"]:
            return r["mensaje"]
        r = r["result"]
        lineas = [f"Regla: {r['rule']}"]
        for tipo, n in r["summary"].items():
            if n:
                consejo = next(a["advice"] for a in r["alerts"] if a["type"] == tipo)
                lineas.append(f"{self._NOMBRES[tipo]}: {n} cara(s). {consejo}")
        if len(lineas) == 1:
            lineas.append("Sin alertas.")
        return "\n".join(lineas)

    def construir(self, v, ctx):
        return None


registrar(AsignarReglaPlastico, AdministrarReglasPlastico, ConsejosDiseno, PatronGeometrico)
