# -*- coding: utf-8 -*-
"""PLÁSTICO: Asignar regla de plástico y Administrar reglas (la biblioteca vive en `nucleo/plastico.py`) y el Apoyo
(Rest), que es una operación de sólido como el Saliente y el Labio."""
from ...nucleo import geometria as geo
from ...nucleo import plastico
from ...timeline.ops_solido import OpApoyo, OpGrampa, OpPatronGeometrico, OpReglaPlastico
from ...timeline.parametros import ESCALAR
from ..comando import (ANGULO, Casilla, Comando, Entero, ErrorComando, Expresion, Info, Opciones, Seleccion, Texto, exigir,
                       hits, refs)
from . import registrar
from .comunes import campo_objetivos, campo_operacion, objetivos
from .crear import PERFIL


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
    TITULOS_MODO = ("accion", {"crear": ("Crear regla de plástico", "reglas_plastico"),
                               "borrar": ("Borrar regla de plástico", "reglas_plastico")})

    def campos(self, ctx):
        crear = lambda v: v.get("accion") == "crear"  # noqa: E731
        return [Opciones("accion", "Acción", {"crear": "Crear regla", "borrar": "Borrar regla propia"}),
                Texto("nombre", "Nombre", etiqueta_si=lambda v: "Nombre" if crear(v) else "Regla a borrar"),
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
                Expresion("tamano1", "Tamaño en el centro", "2 mm", grupo="Tamaño"),
                Expresion("tamano2", "Tamaño en la esquina", "4 mm", grupo="Tamaño"),
                Expresion("dispersion", "Dispersión", "1", ESCALAR, grupo="Tamaño"),
                Opciones("distribucion", "Distribución", {"rectangular": "Rectangular", "triangular": "Triangular",
                                                          "hexagonal": "Hexagonal", "circular": "Circular",
                                                          "radial": "Radial"}, grupo="Distribución"),
                Opciones("separacion", "Tipo de separación", {"incremento": "Incremento", "extension": "Extensión"},
                         visible_si=es("rectangular"), grupo="Distribución"),
                Expresion("distancia", "Distancia entre objetos", "6 mm",
                          visible_si=lambda v: rejilla(v) and v.get("separacion") != "extension", grupo="Distribución"),
                Entero("cantidad_u", "Cantidad en U", 5, 1, 1000,
                       visible_si=lambda v: rejilla(v) and v.get("separacion") == "extension", grupo="Distribución"),
                Entero("cantidad_v", "Cantidad en V", 5, 1, 1000,
                       visible_si=lambda v: es("rectangular")(v) and v.get("separacion") == "extension",
                       grupo="Distribución"),
                Expresion("distancia_radial", "Distancia radial", "6 mm", visible_si=es("circular", "radial"),
                          grupo="Distribución"),
                Entero("rayos", "Rayos", 8, 1, 1000, visible_si=es("radial"), grupo="Distribución"),
                campo_operacion("cortar"), campo_objetivos(),
                Opciones("orientacion", "Orientación", {"cara": "Dirección de la cara", "paralela": "Dirección paralela"},
                         avanzado=True),
                Opciones("alineacion_u", "Alineación en U", {"izquierda": "Izquierda", "centro": "Centro", "derecha": "Derecha"},
                         "centro", visible_si=rejilla, grupo="Dirección U", avanzado=True),
                Expresion("desfase_u", "Desfase en U", "0 mm", grupo="Dirección U", avanzado=True),
                Opciones("alineacion_v", "Alineación en V", {"abajo": "Abajo", "medio": "Medio", "arriba": "Arriba"},
                         "medio", visible_si=rejilla, grupo="Dirección V", avanzado=True),
                Expresion("desfase_v", "Desfase en V", "0 mm", grupo="Dirección V", avanzado=True),
                Casilla("limpiar_perimetro", "Limpiar perímetro", True, grupo="Perímetro", avanzado=True),
                Expresion("desfase_perimetro", "Desfase del perímetro", "0 mm", grupo="Perímetro", avanzado=True)]

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


class Apoyo(Comando):
    CLAVE, TITULO, ICONO = "apoyo", "Apoyo", "apoyo"
    AYUDA = ("Pared de apoyo (plástico) desde un perfil cerrado: deja un área plana en la cara del cuerpo. "
             "El grosor es la suma de los lados 1 y 2.")
    CLASE_OP = OpApoyo

    def campos(self, ctx):
        return [Seleccion("perfiles", "Perfiles", PERFIL, maximo=None),
                Seleccion("cuerpo", "Cuerpo", {"cuerpo"}),
                Expresion("desfase", "Desfase de posición", "0 mm",
                          ayuda="Desde el plano del boceto; el signo es hacia el cuerpo."),
                Expresion("grosor", "Grosor", "2 mm", ayuda="Tiene que ser la suma de los lados 1 y 2."),
                Expresion("lado1", "Lado 1", "2 mm", ayuda="0 = sin pared de ese lado."),
                Expresion("lado2", "Lado 2", "0 mm", ayuda="0 = sin pared de ese lado."),
                Expresion("angulo_desmoldeo", "Ángulo de desmoldeo", "0 deg", ANGULO),
                Casilla("invertir", "Invertir"),
                Opciones("extension", "Tipo de extensión", {"todo": "Todo", "objeto": "Hasta objeto"}),
                Seleccion("caras_superiores", "Caras superiores", {"cara"}, minimo=0, grupo="Avanzado",
                          ayuda="El apoyo solo se crea bajo las caras elegidas y termina en ellas."),
                Casilla("recortar", "Recortar", True, grupo="Avanzado",
                        ayuda="Quita el área del apoyo que sobresale del cuerpo.")]

    def construir(self, v, ctx):
        exigir(v, "perfiles", "Seleccioná los perfiles cerrados del apoyo.")
        exigir(v, "cuerpo", "Elegí el cuerpo del apoyo.")
        for k in ("desfase", "grosor", "lado1", "lado2"):
            ctx.evaluar(v[k])
        cuerpo = [h["ref"]["cuerpo"] for h in v["cuerpo"] if h["ref"].get("tipo") == "cuerpo"][0]
        return self.crear_op(OpApoyo, v, ctx, perfiles=refs(v, "perfiles"), cuerpo={"tipo": "cuerpo", "cuerpo": cuerpo},
                             caras_superiores=refs(v, "caras_superiores"),
                             **{k: v[k] for k in ("desfase", "grosor", "lado1", "lado2", "angulo_desmoldeo", "invertir",
                                                  "extension", "recortar")})

    def desde_op(self, op, ctx):
        return dict(op.p, perfiles=hits(op.p["perfiles"], ctx.estado), cuerpo=hits([op.p["cuerpo"]], ctx.estado),
                    caras_superiores=hits(op.p.get("caras_superiores", []), ctx.estado))


class Grampa(Comando):
    CLAVE, TITULO, ICONO = "grampa", "Grampa de fijación", "encaje_presion"
    AYUDA = ("Gancho en voladizo (plástico) en puntos de boceto que encaja en una ranura con holgura copiada en el "
             "otro cuerpo. El giro es uniforme para todos los puntos.")
    CLASE_OP = OpGrampa

    def campos(self, ctx):
        return [Seleccion("posiciones", "Puntos", {"punto", "vertice"}, maximo=None),
                Opciones("tipo", "Tipo", {"paralelo": "Gancho y ranurado paralelos",
                                          "perpendicular": "Gancho y ranurado perpendiculares",
                                          "contorno": "Gancho y contorno"}),
                Seleccion("cuerpo_gancho", "Cuerpo del gancho", {"cuerpo"}),
                Seleccion("cuerpo_ranura", "Cuerpo de la ranura", {"cuerpo"}, minimo=0),
                Expresion("largo", "Largo del brazo", "10 mm", grupo="Gancho"),
                Expresion("ancho", "Ancho", "4 mm", grupo="Gancho"),
                Expresion("espesor", "Espesor", "1.5 mm", grupo="Gancho"),
                Expresion("alto_gancho", "Alto del gancho", "1 mm", grupo="Gancho"),
                Expresion("holgura", "Holgura de la ranura", "0.1 mm", grupo="Ranura"),
                Expresion("angulo", "Ángulo de giro", "0 deg", ANGULO),
                Opciones("extension", "Tipo de extensión", {"siguiente": "Hasta el siguiente",
                                                            "distancia": "Distancia"}),
                Expresion("distancia", "Distancia", "12 mm",
                          visible_si=lambda v: v.get("extension") == "distancia"),
                Casilla("invertir", "Invertir")]

    def construir(self, v, ctx):
        exigir(v, "posiciones", "Seleccioná los puntos donde van las grampas.")
        exigir(v, "cuerpo_gancho", "Elegí el cuerpo del gancho.")
        cuerpo = lambda k: ([h["ref"]["cuerpo"] for h in v[k] if h["ref"].get("tipo") == "cuerpo"] or [None])[0]  # noqa: E731
        ranura = cuerpo("cuerpo_ranura")
        return self.crear_op(OpGrampa, v, ctx, posiciones=refs(v, "posiciones"),
                             cuerpo_gancho={"tipo": "cuerpo", "cuerpo": cuerpo("cuerpo_gancho")},
                             cuerpo_ranura={"tipo": "cuerpo", "cuerpo": ranura} if ranura else None,
                             **{k: v[k] for k in ("tipo", "largo", "ancho", "espesor", "alto_gancho", "holgura",
                                                  "angulo", "extension", "distancia", "invertir")})

    def desde_op(self, op, ctx):
        return dict(op.p, posiciones=hits(op.p["posiciones"], ctx.estado),
                    cuerpo_gancho=hits([op.p["cuerpo_gancho"]], ctx.estado),
                    cuerpo_ranura=hits([op.p["cuerpo_ranura"]], ctx.estado) if op.p.get("cuerpo_ranura") else [])


registrar(AsignarReglaPlastico, AdministrarReglasPlastico, ConsejosDiseno, PatronGeometrico, Apoyo, Grampa)
