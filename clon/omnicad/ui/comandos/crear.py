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


# ---------------------------------------------------------------- roscas en los diálogos (Agujero y Rosca)
# Como Fusion: Tipo (familia de normas) → Tamaño (lista según el tipo) → Designación (cuando el tamaño tiene varios
# pasos) → Clase. Un campo de tamaño por familia y uno de designación por tamaño con varios pasos, que se muestran
# según lo elegido (el panel no cambia las listas en vivo: cada lista es un campo propio).
def _sc():
    from ...nucleo import solidos_crear
    return solidos_crear


def _tol():
    from ...nucleo import tolerancias
    return tolerancias


_CLASES = {"iso_metrica": {"auto": "Automática (6H agujero / 6g eje)", "": "Sin clase (perfil básico)",
                           "6g": "6g (exterior)", "6h": "6h (exterior)", "6H": "6H (interior)", "6G": "6G (interior)"},
           "unificada": {"auto": "Automática (2B agujero / 2A eje)", "": "Sin clase (perfil básico)",
                         "2A": "2A (exterior)", "3A": "3A (exterior)", "2B": "2B (interior)", "3B": "3B (interior)"}}


_TAMANO_INICIAL = {"iso_metrica": "M6", "unificada": "1/4", "trapezoidal": "Tr12", "acme": "1/2",
                   "bsp_paralela": "1/2", "bsp_conica": "1/2", "npt": "1/2"}


def _tamano_inicial(fam, tams):
    t = _TAMANO_INICIAL.get(fam)
    return t if t in tams else tams[0]


def _familias(conicas=None):
    return {k: f["nombre"] for k, f in _sc().FAMILIAS_ROSCA.items() if conicas is None or f["conica"] == conicas}


def _campos_rosca(clave_tipo, familias, visible, defectos, automatico=False, clases=True):
    """Tipo, Tamaño (uno por familia), Designación (uno por tamaño con varios pasos) y Clase (si la familia tiene).
    `defectos`: valores iniciales (lo recordado); `automatico`: el tamaño puede ser «Automático» (según la cara)."""
    sc = _sc()
    campos = [Opciones(clave_tipo, "Tipo", familias, defecto=defectos.get(clave_tipo) or next(iter(familias)),
                       visible_si=visible)]
    for fam in familias:
        tams = sc.tamanos_rosca(fam)
        de_fam = lambda v, fam=fam: visible(v) and v.get(clave_tipo) == fam  # noqa: E731
        opciones = ({"auto": "Automático (según la cara)"} if automatico else {}) | {t: t for t in tams}
        defecto = defectos.get(f"tam_{fam}") or ("auto" if automatico else _tamano_inicial(fam, tams))
        campos.append(Opciones(f"tam_{fam}", "Tamaño", opciones, defecto=defecto, visible_si=de_fam))
        for i, t in enumerate(tams):
            des = sc.designaciones_rosca(fam, t)
            if len(des) > 1:
                campos.append(Opciones(f"des_{fam}_{i}", "Designación", {d: d for d in des},
                                       defecto=defectos.get(f"des_{fam}_{i}") or des[0],
                                       visible_si=lambda v, fam=fam, t=t, de_fam=de_fam: de_fam(v) and
                                       v.get(f"tam_{fam}") == t))
        if clases and fam in _CLASES:
            campos.append(Opciones(f"clase_{fam}", "Clase", _CLASES[fam], defecto=defectos.get(f"clase_{fam}", "auto"),
                                   visible_si=lambda v, fam=fam, de_fam=de_fam: de_fam(v) and clases(v)
                                   if callable(clases) else de_fam(v)))
    return campos


def _designacion(v, clave_tipo, automatico=False):
    """Designación elegida en el diálogo ("" = tamaño automático)."""
    sc = _sc()
    fam = v.get(clave_tipo)
    if fam not in sc.FAMILIAS_ROSCA:
        fam = "iso_metrica"
    tams = sc.tamanos_rosca(fam)
    tam = v.get(f"tam_{fam}")
    if automatico and tam in (None, "", "auto"):
        return ""
    if tam not in tams:
        tam = _tamano_inicial(fam, tams)
    des = sc.designaciones_rosca(fam, tam)
    elegida = v.get(f"des_{fam}_{tams.index(tam)}")
    return elegida if elegida in des else des[0]


def _clase(v, clave_tipo):
    fam = v.get(clave_tipo)
    return (v.get(f"clase_{fam}") or "") if fam in _CLASES else ""


def _valores_rosca(designacion, clave_tipo, clase=""):
    """Valores del diálogo que muestran una designación guardada (para editar el paso)."""
    sc = _sc()
    try:
        datos = sc.datos_rosca(designacion)
    except Exception:  # noqa: BLE001 — una designación vieja que ya no se reconoce deja el diálogo por defecto
        return {}
    fam, tam = datos["familia"], datos["tamano"]
    v = {clave_tipo: fam, f"tam_{fam}": tam, f"des_{fam}_{sc.tamanos_rosca(fam).index(tam)}": datos["designacion"]}
    if fam in _CLASES:
        v[f"clase_{fam}"] = clase or ""
    return v


def _texto_limites(fam, datos, clase, interna=None):
    """«6g: Ø mayor 9.732–9.968 · Ø flancos 8.862–8.994 mm (ISO 965-1)» o por qué no hay límites."""
    tol = _tol()
    if not clase:
        return "perfil básico (sin clase)"
    if clase == "auto":
        if fam not in tol.CLASE_AUTOMATICA:
            return "sin clases cargadas para este tipo: perfil básico"
        if interna is None:
            a, b = tol.CLASE_AUTOMATICA[fam]
            return f"clase automática: {a} en agujeros, {b} en ejes"
        clase = tol.CLASE_AUTOMATICA[fam][0 if interna else 1]
    try:
        lim = tol.limites_rosca(fam, datos["diametro"], datos["paso"], clase)
    except Exception as e:  # noqa: BLE001 — sin datos para el tamaño: se dice por qué
        return f"{clase}: {e}"

    def rango(par):
        a, b = par
        if a is None and b is None:
            return "—"
        return f"{a:.3f}–{b:.3f}" if a is not None and b is not None else (f"≥ {a:.3f}" if a is not None else
                                                                           f"≤ {b:.3f}")
    partes = [f"Ø mayor {rango(lim['diametro_mayor'])}", f"Ø flancos {rango(lim['diametro_flancos'])}"]
    if lim["interna"]:
        partes.append(f"Ø menor {rango(lim['diametro_menor'])}")
    return f"{clase}: " + " · ".join(partes) + f" mm ({lim['norma']})"


def _texto_rosca_basica(datos):
    fam = _sc().FAMILIAS_ROSCA[datos["familia"]]
    texto = (f"{datos['designacion']} ({fam['norma']}, {fam['angulo']:g}°): Ø {datos['diametro']:.3f}, paso "
             f"{datos['paso']:.4g}, Ø menor {datos['diametro_menor']:.3f} mm")
    if datos["conica"]:
        texto += " en el plano de calibre, conicidad 1:16"
    return texto


def _interna_de(v, ctx):
    """¿La primera cara elegida es un agujero? None si no se puede saber."""
    try:
        h = (v.get("caras") or [])[0]
        e = _ent_resuelta(h, ctx)
        return _sc().analizar_rosca(ctx.estado.cuerpo(e.cuerpo).forma, e.forma)["interna"]
    except Exception:  # noqa: BLE001
        return None


def _ent_resuelta(hit, ctx):
    from ...timeline import entidades as ent
    return ent.resolver(hit["ref"], ctx.estado)


class Agujero(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "agujero", "Agujero", "agujero", "H"
    AYUDA = ("Agujeros simples, abocardados o avellanados; pasantes, ciegos o hasta una cara; lisos, con holgura "
             "(ISO 273), roscados (con tipo, tamaño, designación y clase) o con rosca cónica de tubería.")
    CLASE_OP = OpAgujero

    def campos(self, ctx):
        sc = _sc()
        t = lambda *x: (lambda v: v.get("tipo") in x)  # noqa: E731
        r = lambda *x: (lambda v: v.get("rosca") in x)  # noqa: E731
        pos = lambda *x: (lambda v: (v.get("posicion") or "punto") in x)  # noqa: E731
        hasta = lambda v: v.get("extension") == "hasta"  # noqa: E731
        return [
            Opciones("posicion", "Posición", {"punto": "Punto único", "boceto": "Desde boceto",
                                              "referencias": "Referencias"},
                     ayuda="Punto único: un clic sobre una cara plana (o un punto). Desde boceto: un agujero en cada "
                           "punto del boceto. Referencias: una cara y dos aristas con su distancia."),
            Seleccion("colocacion", "Puntos / cara", {"punto", "vertice", "cara_plana"}, maximo=None,
                      visible_si=pos("punto"), ayuda="Un clic sobre una cara plana (o un punto o vértice)."),
            Seleccion("puntos_boceto", "Puntos de boceto", {"punto_boceto"}, maximo=None, visible_si=pos("boceto"),
                      ayuda="Cada punto del boceto es un agujero: si el boceto cambia, los agujeros lo siguen."),
            Seleccion("ref_cara", "Cara", {"cara_plana"}, visible_si=pos("referencias")),
            Seleccion("ref_arista1", "Referencia 1", {"arista_lineal"}, visible_si=pos("referencias"),
                      ayuda="Arista recta desde la que se mide la distancia 1."),
            Expresion("ref_distancia1", "Distancia 1", "10 mm", visible_si=pos("referencias")),
            Seleccion("ref_arista2", "Referencia 2", {"arista_lineal"}, visible_si=pos("referencias"),
                      ayuda="Otra arista recta, no paralela a la primera."),
            Expresion("ref_distancia2", "Distancia 2", "10 mm", visible_si=pos("referencias")),
            Opciones("extension", "Extensión", {"distancia": "Distancia", "todo": "Todo", "hasta": "Hasta"}),
            Seleccion("hasta", "Hasta", {"cara", "plano", "cuerpo"}, visible_si=hasta,
                      ayuda="Cara (si es plana, su plano extendido), plano de construcción o cuerpo donde termina."),
            Expresion("desfase_hasta", "Desfase", "0 mm", visible_si=hasta),
            Opciones("tipo", "Tipo de agujero", {"simple": "Simple", "abocardado": "Abocardado",
                                                 "avellanado": "Avellanado"}),
            Opciones("rosca", "Tipo de rosca", {"simple": "Simple (sin rosca)", "holgura": "Con holgura",
                                                "cosmetica": "Roscado (cosmético)", "modelada": "Roscado (modelado)",
                                                "conico": "Roscado cónico"}),
            Opciones("tam_holgura", "Tamaño", {k: k for k in sc.PASO_LIBRE_ISO273}, defecto="M6",
                     visible_si=r("holgura")),
            Opciones("ajuste", "Ajuste", {"fino": "Cercano (serie fina)", "normal": "Normal (serie media)",
                                          "grueso": "Holgado (serie gruesa)"}, defecto="normal",
                     visible_si=r("holgura"), ayuda="Diámetro del agujero de paso según ISO 273."),
            *_campos_rosca("tipo_rosca", _familias(conicas=False), r("cosmetica", "modelada"), {},
                           clases=lambda v: v.get("rosca") == "modelada"),
            Expresion("holgura_3d", "Holgura impresión 3D", "0 mm", visible_si=r("modelada"),
                      ayuda="Desfase radial extra de los flancos y del agujero, para que el tornillo entre en una "
                            "pieza impresa."),
            Opciones("mano", "Dirección", {"derecha": "Derecha", "izquierda": "Izquierda"}, visible_si=r("modelada")),
            *_campos_rosca("tipo_conica", _familias(conicas=True), r("conico"), {}, clases=False),
            Info("info_rosca", "Rosca", self._info, visible_si=r("holgura", "cosmetica", "modelada", "conico")),
            Expresion("diametro", "Diámetro", "6 mm", visible_si=r("simple", "cosmetica")),
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

    @staticmethod
    def _rosca_elegida(v):
        """(designación, clase) que guarda el paso según el tipo de rosca del diálogo."""
        rosca = v.get("rosca")
        if rosca == "holgura":
            return v.get("tam_holgura") or "M6", ""
        if rosca == "conico":
            return _designacion(v, "tipo_conica"), ""
        return _designacion(v, "tipo_rosca"), (_clase(v, "tipo_rosca") if rosca == "modelada" else "")

    def _info(self, v, ctx):
        sc = _sc()
        designacion, clase = self._rosca_elegida(v)
        rosca = v.get("rosca")
        if rosca == "holgura":
            d = sc.diametro_paso_libre(designacion, v.get("ajuste") or "normal")
            return f"Agujero de paso para {designacion}: Ø {d:g} mm (ISO 273, serie {v.get('ajuste') or 'normal'})"
        datos = sc.datos_rosca(designacion)
        texto = _texto_rosca_basica(datos)
        if rosca == "modelada":
            clase_r, aviso = _tol().resolver_clase(datos["familia"], datos["diametro"], datos["paso"], clase, True)
            holgura = ctx.evaluar(v.get("holgura_3d") or "0 mm")
            texto += (f" · {_texto_limites(datos['familia'], datos, clase_r) if clase_r else (aviso or 'perfil básico')}"
                      f" · Ø taladro {sc.diametro_taladro_rosca(designacion, clase_r, holgura):.3f} mm")
        elif rosca == "cosmetica" and datos.get("broca"):
            texto += f" · broca para roscar {datos['broca']:g} mm"
        return texto

    def construir(self, v, ctx):
        posicion = v.get("posicion") or "punto"
        posiciones, puntos_cara, ref_cara, ref_aristas = [], [], None, []
        if posicion == "boceto":
            posiciones = [h["ref"] for h in exigir(v, "puntos_boceto", "Elegí los puntos del boceto (un agujero por "
                                                                       "punto).")]
        elif posicion == "referencias":
            exigir(v, "ref_cara", "Elegí la cara plana donde va el agujero.")
            exigir(v, "ref_arista1", "Elegí la primera arista de referencia.")
            exigir(v, "ref_arista2", "Elegí la segunda arista de referencia.")
            ctx.evaluar(v["ref_distancia1"])
            ctx.evaluar(v["ref_distancia2"])
            ref_cara, ref_aristas = ref1(v, "ref_cara"), [ref1(v, "ref_arista1"), ref1(v, "ref_arista2")]
        else:
            sel = exigir(v, "colocacion", "Elegí puntos de boceto o hacé clic sobre una cara plana.")
            posiciones = [h["ref"] for h in sel if h["ref"]["tipo"] != "cara"]
            puntos_cara = [{"cara": h["ref"], "punto": [float(c) for c in np.asarray(h.get("punto"), float)]}
                           for h in sel if h["ref"]["tipo"] == "cara" and h.get("punto") is not None]
        hasta = None
        if v.get("extension") == "hasta":
            hasta = ref1(v, "hasta")
            if hasta is None:
                raise ErrorComando("Elegí la cara, el plano o el cuerpo donde termina el agujero.")
        designacion, clase = self._rosca_elegida(v)
        params = {k: v[k] for k in ("tipo", "diametro", "extension", "profundidad", "punta", "angulo_punta",
                                     "diam_abocardado", "prof_abocardado", "diam_avellanado", "angulo_avellanado",
                                     "rosca", "invertir", "holgura_3d", "mano", "ajuste", "desfase_hasta",
                                     "ref_distancia1", "ref_distancia2") if k in v}
        return self.crear_op(OpAgujero, v, ctx, posiciones=posiciones, puntos_cara=puntos_cara, objetivos=objetivos(v),
                             designacion=designacion, clase_rosca=clase, hasta=hasta, ref_cara=ref_cara,
                             ref_aristas=ref_aristas, **params)

    def manipuladores(self, ctx, v):
        """Flecha de profundidad en el primer agujero: sale del fondo y apunta hacia el material."""
        from .. import manipuladores as mp
        posicion = v.get("posicion") or "punto"
        if not v.get({"punto": "colocacion", "boceto": "puntos_boceto", "referencias": "ref_cara"}[posicion]):
            return []
        try:
            cols = self.construir(v, ctx)._colocaciones(ctx.estado, ctx)
        except Exception:  # noqa: BLE001 — sin colocación válida no hay flecha ni asas
            return []
        asas = []
        if v.get("extension") == "distancia":
            asas.append(mp.Flecha("profundidad", cols[0][0], cols[0][1], minimo=0.0))
        if v.get("rosca") in ("simple", "cosmetica"):
            # como Fusion: asa en el borde del agujero que se tira para agrandarlo (el valor es el diámetro)
            radial, _ = mp.perpendiculares(cols[0][1])
            asas.append(mp.AsaRadial("diametro", cols[0][0], radial, factor=0.5, minimo=0.1))
        if posicion != "punto":
            return asas
        # un aro por cada agujero puesto con un clic sobre una cara: se arrastra por la cara
        sel = v["colocacion"]
        n_fijos = sum(1 for h in sel if h["ref"]["tipo"] != "cara")
        por_cara = [i for i, h in enumerate(sel) if h["ref"]["tipo"] == "cara" and h.get("punto") is not None]
        for k, i in enumerate(por_cara):
            if n_fijos + k >= len(cols):
                break
            punto, direccion = cols[n_fijos + k]

            forma_cara = self._forma_cara(sel[i], ctx)

            def al_mover(q, i=i, forma_cara=forma_cara):
                if forma_cara is not None and not mp.punto_en_cara(forma_cara, q):
                    return {}                      # el agujero no sale de la cara
                actual = list(v["colocacion"])
                actual[i] = dict(actual[i], punto=np.asarray(q, float))
                return {"colocacion": actual}
            asas.append(mp.Posicion(f"agujero{i}", punto, direccion, al_mover,
                                    candidatos=self._enganches(sel[i], ctx)))
        return asas

    @staticmethod
    def _forma_cara(hit, ctx):
        from .. import manipuladores as mp
        e = mp.entidad(hit, ctx.estado)
        return e.forma if e is not None else None

    @staticmethod
    def _enganches(hit, ctx):
        """Puntos de enganche de la cara del hit: su centro, esquinas, puntos medios y centros de arcos."""
        from .. import manipuladores as mp
        e = mp.entidad(hit, ctx.estado)
        if e is None or e.forma is None:
            return []
        try:
            return mp.puntos_enganche_cara(e.forma)
        except Exception:  # noqa: BLE001 — sin candidatos, el agujero se mueve libre
            return []

    def ajustar_hit(self, campo, hit, ctx, visor):
        """Al hacer clic en una cara, el punto se engancha al centro de la cara (o a una esquina, un punto
        medio…) si queda a menos de ENGANCHE_PX píxeles, como Fusion."""
        from .. import manipuladores as mp
        if campo.clave != "colocacion" or hit["ref"].get("tipo") != "cara" or hit.get("punto") is None:
            return None
        cands = self._enganches(hit, ctx)
        if not cands:
            return None
        click = np.asarray(hit["punto"], float)
        s, ok = visor.puntos_pantalla(np.array([c[0] for c in cands] + [click], float))
        s, ok = np.asarray(s, float), np.asarray(ok, bool)
        if not ok[-1]:
            return None
        d = np.linalg.norm(s[:-1] - s[-1], axis=1)
        d[~ok[:-1]] = np.inf
        i = int(np.argmin(d))
        if d[i] > mp.ENGANCHE_PX:
            return None
        return dict(hit, punto=np.asarray(cands[i][0], float))

    def previa_vista(self, ctx, v, op):
        """Como Fusion, el agujero se ve en ROJO mientras el diálogo está abierto (lo que se va a quitar). La rosca
        modelada se dibuja con su agujero liso (sin el surco: es lo lento)."""
        from .. import manipuladores as mp
        return mp.herramientas_rojas(op.herramientas(ctx.estado, ctx, rapido=True))

    def desde_op(self, op, ctx):
        p = op.p
        v = dict(p)
        if p.get("ref_cara"):
            v["posicion"] = "referencias"
        elif p.get("posiciones") and not p.get("puntos_cara") and all(
                isinstance(r, dict) and r.get("tipo") == "punto_boceto" for r in p["posiciones"]):
            v["posicion"] = "boceto"
        else:
            v["posicion"] = "punto"
        sel = hits(p["posiciones"], ctx.estado)
        if v["posicion"] == "boceto":
            v["puntos_boceto"], sel = sel, []
        for d in p.get("puntos_cara") or []:
            h = hit_desde_ref(d["cara"], ctx.estado)
            h["punto"] = np.asarray(d["punto"], float)
            sel.append(h)
        v["colocacion"] = sel
        v["ref_cara"] = _h1(p.get("ref_cara"), ctx.estado)
        aristas = list(p.get("ref_aristas") or []) + [None, None]
        v["ref_arista1"], v["ref_arista2"] = _h1(aristas[0], ctx.estado), _h1(aristas[1], ctx.estado)
        v["hasta"] = _h1(p.get("hasta"), ctx.estado)
        rosca = p.get("rosca")
        if rosca == "holgura":
            v["tam_holgura"] = p.get("designacion")
        elif rosca == "conico":
            v.update(_valores_rosca(p.get("designacion"), "tipo_conica"))
        else:
            v.update(_valores_rosca(p.get("designacion"), "tipo_rosca", p.get("clase_rosca") or ""))
        return _con_objetivos(op, ctx, v)


class Rosca(Comando):
    CLAVE, TITULO, ICONO = "rosca", "Rosca", "rosca"
    AYUDA = ("Rosca sobre caras cilíndricas: tipo (métrica, unificada, trapezoidal, ACME, tubería), tamaño "
             "(automático o de la lista), designación, clase de tolerancia y holgura para impresión 3D; cosmética o "
             "modelada. «Recordar tamaño» vuelve a proponer el último tipo y tamaño elegidos.")
    CLASE_OP = OpRosca
    _recuerdo = {}           # «Recordar tamaño»: lo último elegido con la casilla marcada (vale en la sesión)

    def campos(self, ctx):
        modelada = lambda v: bool(v.get("modelada"))  # noqa: E731
        recuerdo = dict(Rosca._recuerdo)
        return [Seleccion("caras", "Caras", {"cara"}, maximo=None),
                Casilla("modelada", "Modelado", True),
                Casilla("largo_completo", "Longitud completa", True),
                Expresion("longitud", "Longitud", "10 mm", visible_si=lambda v: not v.get("largo_completo")),
                Expresion("desfase", "Desfase", "0 mm", visible_si=lambda v: not v.get("largo_completo")),
                *_campos_rosca("tipo_rosca", _familias(), lambda v: True, recuerdo, automatico=True),
                Expresion("holgura_3d", "Holgura impresión 3D", "0 mm", visible_si=modelada,
                          ayuda="Desfase radial extra de los flancos, para que la rosca impresa enrosque."),
                Opciones("mano", "Dirección", {"derecha": "Derecha", "izquierda": "Izquierda"}),
                Casilla("invertir", "Invertir"),
                Casilla("recordar", "Recordar tamaño", bool(recuerdo)),
                Info("info_rosca", "Rosca", self._info)]

    def _info(self, v, ctx):
        designacion = _designacion(v, "tipo_rosca", automatico=True)
        fam = v.get("tipo_rosca") or "iso_metrica"
        if not designacion:
            return "Tamaño automático: el de la lista más cercano al diámetro de la cara."
        datos = _sc().datos_rosca(designacion)
        texto = _texto_rosca_basica(datos)
        if datos["conica"]:
            return texto + " · sobre una cara cilíndrica va cosmética"
        return texto + " · " + _texto_limites(fam, datos, _clase(v, "tipo_rosca"), _interna_de(v, ctx))

    def construir(self, v, ctx):
        exigir(v, "caras", "Seleccioná las caras cilíndricas.")
        fam = v.get("tipo_rosca") or "iso_metrica"
        if v.get("recordar"):
            Rosca._recuerdo = {k: x for k, x in v.items() if k == "tipo_rosca" or k.startswith(("tam_", "des_",
                                                                                                    "clase_"))}
        return self.crear_op(OpRosca, v, ctx, caras=refs(v, "caras"), designacion=_designacion(v, "tipo_rosca", True),
                             familia=fam, clase_rosca=_clase(v, "tipo_rosca"), holgura_3d=v.get("holgura_3d") or "0 mm",
                             **{k: v[k] for k in ("largo_completo", "longitud", "desfase", "modelada", "mano",
                                                  "invertir")})

    def desde_op(self, op, ctx):
        v = dict(op.p, caras=hits(op.p["caras"], ctx.estado))
        fam = op.p.get("familia") or "iso_metrica"
        if op.p.get("designacion"):
            v.update(_valores_rosca(op.p["designacion"], "tipo_rosca", op.p.get("clase_rosca") or ""))
        else:
            v.update({"tipo_rosca": fam, f"tam_{fam}": "auto"})
            if fam in _CLASES:
                v[f"clase_{fam}"] = op.p.get("clase_rosca") or ""
        return v


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
