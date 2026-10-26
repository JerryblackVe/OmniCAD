# -*- coding: utf-8 -*-
"""
Operaciones de SÓLIDO › CREAR (además de Extruir, Revolución y las primitivas de `operaciones.py`):
barrido, solevación, nervio, red, repujado, agujero, rosca, bobina, tubería, patrones (rectangular,
circular, en ruta con giro y en puntos; de cuerpos o de operaciones), multitransformación, simetría, relleno de
contorno, sólido envolvente y las de plástico (saliente, labio).
El núcleo geométrico está en `nucleo/solidos_crear.py`.
"""
import math
import re

import numpy as np

from ..nucleo import geometria as geo
from . import entidades as ent
from .operaciones import (ANGULO, OPERACIONES_CUERPO, ErrorOperacion, Operacion, ParametroMalFormado, _deps_objetivo, _resolver,
                          _resolver_todas, aplicar_resultado, atributos_copia, registrar_operacion)

ESPESORES = ("simetrica", "lado1", "lado2")     # dirección del espesor de nervio y red (nucleo.solidos_crear)


def _sc():
    from ..nucleo import solidos_crear
    return solidos_crear


def _sm():
    from ..nucleo import solidos_modificar
    return solidos_modificar


def _pg():
    from ..nucleo import patron_geometrico
    return patron_geometrico


def _caras(refs, estado, que="perfiles"):
    """(plano, caras) de perfiles de boceto y caras planas."""
    ents = _resolver_todas(refs, estado)
    caras = [e.forma for e in ents if e.forma is not None and e.tipo in ("perfil", "cara")]
    if not caras:
        raise ErrorOperacion(f"Elegí {que}.")
    plano = next((e.plano for e in ents if e.plano is not None), None)
    return plano, caras


def _aristas(refs, estado, que="curvas"):
    ents = _resolver_todas(refs, estado)
    aristas = [e.forma for e in ents if e.forma is not None]
    if not aristas:
        raise ErrorOperacion(f"Elegí {que}.")
    return ents, aristas


def _cuerpo_objetivo(estado, ents, p):
    """El cuerpo sobre el que trabaja un nervio/red/repujado: el elegido o el sólido más cercano a la curva."""
    if p.get("objetivo"):
        return estado.cuerpo(p["objetivo"])
    solidos = [c for c in estado.cuerpos.values() if getattr(c, "tipo", "solido") == "solido"]
    if not solidos:
        raise ErrorOperacion("No hay un cuerpo sólido sobre el que trabajar.")
    from ..nucleo.consultas import distancia
    forma = ents[0].forma
    return min(solidos, key=lambda c: distancia(c.forma, forma))


class _OpCrear(Operacion):
    REFS = ()

    def dependencias(self):
        p = self.p
        return (ent.dependencias_de(*(p.get(k) for k in self.REFS)) | _deps_objetivo(p.get("objetivos")) |
                _deps_objetivo(p.get("objetivo")) | _deps_objetivo(p.get("cuerpos"))) - {self.id}

    def _aplicar(self, estado, ctx, forma, operacion=None):
        self._registrar_usados(aplicar_resultado(estado, ctx, self.id, forma, operacion or self.p.get("operacion", "nuevo"),
                                                 self.p.get("objetivos") or ""))


class OpBarrido(_OpCrear):
    """Barrido de Fusion [SLD-SWEEP-SOLID]: tipo ruta única o ruta + carril guía; distancia, orientación,
    ángulo de torsión y de conicidad. `orientacion` "alineada" mantiene `eje_alineado` (eje, arista, plano o cara) como
    binormal; `superficie_guia` (caras sobre las que va la ruta) es el tipo Ruta + Superficie guía."""
    TIPO, ETIQUETA, ICONO = "barrido", "Barrido", "↝"
    PARAMS = {"perfiles": [], "ruta": [], "carril": [], "orientacion": "perpendicular", "distancia": "1",
              "torsion": "0 deg", "conicidad": "0 deg", "escala_carril": "escalar", "operacion": "nuevo",
              "objetivos": [], "eje_alineado": None, "superficie_guia": [], "cuerpos": [], "cadena": False}
    EXPRESIONES = ("distancia", "torsion", "conicidad")
    OPCIONES = {"orientacion": ("perpendicular", "paralela", "alineada"), "escala_carril": ("escalar", "estirar", "ninguna"),
                "operacion": OPERACIONES_CUERPO}
    REFS = ("perfiles", "ruta", "carril", "eje_alineado", "superficie_guia")

    def _eje_alineado(self, estado):
        if not self.p.get("eje_alineado"):
            raise ErrorOperacion("Elegí el eje de la orientación alineada (un eje, una arista, un plano o una cara).")
        e = _resolver(self.p["eje_alineado"], estado)
        eje = e.eje[1] if e.eje is not None else e.plano.normal if e.plano is not None else None
        if eje is None:
            raise ErrorOperacion("El eje de la orientación alineada tiene que ser un eje, una arista recta, un plano o una cara plana.")
        return eje

    def _ruta(self, estado, ctx):
        """Las aristas de la ruta; con `cadena` (Chain Selection), cada arista de un cuerpo suma las que siguen tangentes."""
        ents, ruta = _aristas(self.p["ruta"], estado, "la ruta")
        if not self.p.get("cadena"):
            return ruta
        sm, salida = _sm(), []
        if any(not (e.tipo == "arista" and e.cuerpo) for e in ents):
            ctx.aviso("La selección de cadena solo suma aristas de cuerpos: las curvas de boceto se usan tal cual.")
        for e in ents:
            tramo = sm._ampliar_tangentes(estado.cuerpo(e.cuerpo).forma, [e.forma], True) if (
                e.tipo == "arista" and e.cuerpo) else [e.forma]
            salida += [a for a in tramo if not any(a.IsSame(x) for x in salida)]
        return salida

    def _barrer_cuerpos(self, estado, ctx, ruta, eje):
        """Solid Sweep: el volumen que recorre cada cuerpo elegido a lo largo de la ruta."""
        orientacion = self.p["orientacion"]
        if self.p["carril"] or self.p.get("superficie_guia") or abs(ctx.evaluar(self.p["torsion"], ANGULO)) > 1e-9 or abs(
                ctx.evaluar(self.p["conicidad"], ANGULO)) > 1e-9:
            raise ErrorOperacion("El barrido de un cuerpo no usa carril, superficie guía, torsión ni conicidad.")
        distancia = ctx.evaluar(self.p["distancia"], "escalar")
        for cid in self.p["cuerpos"]:
            c = estado.cuerpo(cid)
            if getattr(c, "tipo", "solido") != "solido":
                raise ErrorOperacion(f"«{c.nombre}» no es un cuerpo sólido: el barrido de un cuerpo lo necesita.")
            forma = _sc().barrer_cuerpo(c.forma, ruta, orientacion=orientacion, distancia=distancia, eje_alineado=eje)
            self._aplicar(estado, ctx, forma)

    def ejecutar(self, estado, ctx):
        if self.p.get("cuerpos"):
            ruta = self._ruta(estado, ctx)
            eje = self._eje_alineado(estado) if self.p["orientacion"] == "alineada" else None
            return self._barrer_cuerpos(estado, ctx, ruta, eje)
        _, caras = _caras(self.p["perfiles"], estado)
        ruta = self._ruta(estado, ctx)
        carril = _aristas(self.p["carril"], estado)[1] if self.p["carril"] else None
        eje = self._eje_alineado(estado) if self.p["orientacion"] == "alineada" else None
        superficie = geo.compuesto([e.forma for e in _resolver_todas(self.p["superficie_guia"], estado)])             if self.p.get("superficie_guia") else None
        forma = _sc().barrer(caras, ruta, carril=carril, orientacion=self.p["orientacion"],
                             distancia=ctx.evaluar(self.p["distancia"], "escalar"),
                             torsion=ctx.evaluar(self.p["torsion"], ANGULO),
                             conicidad=ctx.evaluar(self.p["conicidad"], ANGULO), escala_carril=self.p["escala_carril"],
                             eje_alineado=eje, superficie_guia=superficie)
        if geo.sin_volumen(forma):
            raise ErrorOperacion("El barrido no encierra volumen: el plano del perfil no puede ser paralelo a la ruta.")
        self._aplicar(estado, ctx, forma)


class OpSolevacion(_OpCrear):
    """Solevación de Fusion [SLD-LOFT-SOLID]: perfiles en orden (o un punto en los extremos), carril o
    línea central, cerrada y tramos rectos."""
    TIPO, ETIQUETA, ICONO = "solevacion", "Solevación", "⌓"
    PARAMS = {"secciones": [], "carriles": [], "linea_central": [], "cerrada": False, "reglada": False,
              "operacion": "nuevo", "objetivos": [], "condicion_inicio": None, "condicion_fin": None,
              "fusionar_tangentes": False, "condiciones_medias": {}}
    OPCIONES = {"operacion": OPERACIONES_CUERPO}
    REFS = ("secciones", "carriles", "linea_central")

    def dependencias(self):
        caras = [c.get("cara") for c in (self.p.get("condicion_inicio"), self.p.get("condicion_fin")) if c]
        return super().dependencias() | ent.dependencias_de(*caras)

    def _condicion(self, clave, ctx, estado=None, cond=None):
        """La condición de borde guardada {"tipo", "angulo", "peso", "cara"} con el ángulo (expresión) evaluado y la cara
        resuelta (Tangente), o None."""
        c = cond if cond is not None else self.p.get(clave)
        if not c:
            return None
        salida = {"tipo": c.get("tipo", "libre"), "angulo": ctx.evaluar(str(c.get("angulo", "90 deg")), ANGULO),
                  "peso": ctx.evaluar(str(c.get("peso", "1")), "escalar")}
        if salida["tipo"] in ("tangente", "suave"):
            if not c.get("cara"):
                raise ErrorOperacion("La condición Tangente o Suave necesita la cara a la que la superficie es tangente.")
            cara = _resolver(c["cara"], estado)
            if cara.tipo != "cara":
                raise ErrorOperacion("La condición Tangente se apoya en una cara.")
            salida["cara"] = cara.forma
        return salida

    def ejecutar(self, estado, ctx):
        secciones = []
        for e in _resolver_todas(self.p["secciones"], estado):
            secciones.append(e.forma if e.forma is not None and e.tipo != "vertice" else ent.como_punto(e))
        if len(secciones) < 2:
            raise ErrorOperacion("Elegí al menos dos perfiles, en orden.")
        carriles = [_aristas([r], estado)[1] for r in self.p["carriles"]]
        central = _aristas(self.p["linea_central"], estado)[1] if self.p["linea_central"] else None
        forma = _sc().solevar(secciones, carriles=[c[0] if len(c) == 1 else c for c in carriles], linea_central=central,
                              cerrada=self.p["cerrada"], reglada=self.p["reglada"],
                              condicion_inicio=self._condicion("condicion_inicio", ctx, estado),
                              condicion_fin=self._condicion("condicion_fin", ctx, estado),
                              condiciones_medias={int(k): self._condicion(None, ctx, estado, cond)
                                                  for k, cond in (self.p.get("condiciones_medias") or {}).items()},
                              fusionar_tangentes=bool(self.p.get("fusionar_tangentes")))
        if geo.sin_volumen(forma):
            raise ErrorOperacion("La solevación no encierra volumen: los perfiles no pueden estar todos en el mismo "
                                 "plano y una solevación cerrada no puede volver sobre sí misma.")
        self._aplicar(estado, ctx, forma)


class OpNervio(_OpCrear):
    """Nervio de Fusion [SLD-RIB]: pared desde una curva abierta del boceto hasta el cuerpo. `direccion` es la
    Direction y el Start de Fusion juntos: simétrica, o a un lado empezando abajo («lado1») o arriba («lado2»).
    `angulo_desmoldeo` y `direccion_desmoldeo` (referencia a un plano, cara o eje) son Draft Angle y Draft Pull
    Direction; `radio_empalme` y `extender` (Fillet Radius y Extend Curves) solo valen en la Red."""
    TIPO, ETIQUETA, ICONO = "nervio", "Nervio", "⊥"
    PARAMS = {"curvas": [], "espesor": "2 mm", "extension": "hasta_siguiente", "profundidad": "10 mm",
              "direccion": "simetrica", "invertir": False, "objetivo": "", "angulo_desmoldeo": "0 deg",
              "direccion_desmoldeo": None, "radio_empalme": "0 mm", "extender": True}
    EXPRESIONES = ("espesor", "profundidad", "angulo_desmoldeo", "radio_empalme")
    OPCIONES = {"extension": ("hasta_siguiente", "profundidad"), "direccion": ESPESORES}
    REFS = ("curvas", "direccion_desmoldeo")

    def ejecutar(self, estado, ctx):
        ents, aristas = _aristas(self.p["curvas"], estado)
        plano = next((e.plano for e in ents if e.plano is not None), None)
        if plano is None:
            raise ErrorOperacion("El nervio se dibuja con curvas de un boceto.")
        cuerpo = _cuerpo_objetivo(estado, ents, self.p)
        prof = ctx.evaluar(self.p["profundidad"]) if self.p["extension"] == "profundidad" else None
        pull = ent.direccion(_resolver(self.p["direccion_desmoldeo"], estado)) if self.p.get("direccion_desmoldeo") else None
        forma = _sc().nervio(cuerpo.forma, aristas, plano.normal, ctx.evaluar(self.p["espesor"]), profundidad=prof,
                             direccion=self.p["direccion"], invertir=self.p["invertir"], extender=self.p["extender"],
                             angulo_desmoldeo=ctx.evaluar(self.p["angulo_desmoldeo"], ANGULO), direccion_desmoldeo=pull)
        cuerpo.forma = geo.booleano(cuerpo.forma, forma, "unir")
        self._registrar_usados([cuerpo.id])


class OpRed(OpNervio):
    """Red de Fusion [SLD-WEB]: varias curvas abiertas extruidas perpendiculares al boceto hasta el cuerpo."""
    TIPO, ETIQUETA, ICONO = "red", "Red", "#"

    def ejecutar(self, estado, ctx):
        ents, aristas = _aristas(self.p["curvas"], estado)
        plano = next((e.plano for e in ents if e.plano is not None), None)
        if plano is None:
            raise ErrorOperacion("La red se dibuja con curvas de un boceto.")
        cuerpo = _cuerpo_objetivo(estado, ents, self.p)
        prof = ctx.evaluar(self.p["profundidad"]) if self.p["extension"] == "profundidad" else None
        n = -plano.normal if self.p["invertir"] else plano.normal
        forma = _sc().red(cuerpo.forma, aristas, n, ctx.evaluar(self.p["espesor"]), prof, direccion=self.p["direccion"],
                          extender=self.p["extender"], angulo_desmoldeo=ctx.evaluar(self.p["angulo_desmoldeo"], ANGULO))
        cuerpo.forma = _sc().unir_con_empalme(cuerpo.forma, forma, ctx.evaluar(self.p["radio_empalme"]))
        self._registrar_usados([cuerpo.id])


class OpRepujado(_OpCrear):
    """Repujado de Fusion [SLD-EMBOSS]: relieve o grabado de perfiles (o texto) sobre una o VARIAS caras (también de
    cuerpos distintos) a la vez: el texto se reparte entre las caras paralelas (cada una recibe lo que le cae
    encima); o envuelto en un cilindro."""
    TIPO, ETIQUETA, ICONO = "repujado", "Repujado", "Ⓐ"
    PARAMS = {"perfiles": [], "cara": None, "caras": [], "profundidad": "1 mm", "tipo": "relieve",
              "envolver": False, "cadena_tangente": False, "desfase_h": "0 mm", "desfase_v": "0 mm",
              "giro": "0 deg", "invertir": False}
    EXPRESIONES = ("profundidad", "desfase_h", "desfase_v", "giro")
    OPCIONES = {"tipo": ("relieve", "grabado")}
    REFS = ("perfiles", "cara", "caras")

    def ejecutar(self, estado, ctx):
        _, caras = _caras(self.p["perfiles"], estado)
        # «caras» (varias a la vez) y «cara» (una sola: los documentos viejos)
        cara = self.p.get("cara")
        refs_cara = [r for r in list(self.p.get("caras") or []) + (cara if isinstance(cara, list) else [cara]) if r]
        if not refs_cara:
            raise ErrorOperacion("Elegí la cara sobre la que va el repujado.")
        por_cuerpo = {}
        for r in refs_cara:
            e = _resolver(r, estado, ("cara",))
            por_cuerpo.setdefault(e.cuerpo, []).append(e.forma)
        # todas las caras a la vez (aunque sean de cuerpos distintos): el texto se reparte entre ellas
        cuerpos = [estado.cuerpo(cid) for cid in por_cuerpo]
        nuevas = _sc().repujado_en_cuerpos([(c.forma, f) for c, f in zip(cuerpos, por_cuerpo.values(), strict=True)],
                                           caras,
                                           ctx.evaluar(self.p["profundidad"]), tipo=self.p["tipo"],
                                           envolver=self.p["envolver"], cadena_tangente=self.p["cadena_tangente"],
                                           desfase_h=ctx.evaluar(self.p["desfase_h"]),
                                           desfase_v=ctx.evaluar(self.p["desfase_v"]),
                                           giro=ctx.evaluar(self.p["giro"], ANGULO), invertir=self.p["invertir"])
        for c, forma in zip(cuerpos, nuevas, strict=True):
            c.forma = forma
        self._registrar_usados(list(por_cuerpo))


# Tipos de rosca: las claves de nucleo.solidos_crear.FAMILIAS_ROSCA (acá sin cargar el núcleo; un test las compara)
FAMILIAS_ROSCA = ("iso_metrica", "unificada", "trapezoidal", "acme", "bsp_paralela", "bsp_conica", "npt")


def _tol():
    from ..nucleo import tolerancias
    return tolerancias


class OpAgujero(_OpCrear):
    """Agujero de Fusion [GUID-0DFCBD4F, GUID-3A76B269]: posición en puntos de boceto, vértices, puntos sobre una
    cara o por referencias (dos aristas y dos distancias); simple, abocardado o avellanado; extensión distancia,
    todo o hasta (cara, plano o cuerpo); punta plana o en ángulo; rosca simple, con holgura (ISO 273), roscado
    cosmético o modelado (con clase y holgura para impresión 3D) o roscado cónico (tubería R/NPT)."""
    TIPO, ETIQUETA, ICONO = "agujero", "Agujero", "◎"
    # Las claves que siguen a "objetivos" son nuevas: una receta vieja que no las tiene se calcula igual que antes.
    PARAMS = {"posiciones": [], "puntos_cara": [], "tipo": "simple", "diametro": "6 mm", "extension": "distancia",
              "profundidad": "10 mm", "punta": "angulo", "angulo_punta": "118 deg", "diam_abocardado": "10 mm",
              "prof_abocardado": "4 mm", "diam_avellanado": "12 mm", "angulo_avellanado": "90 deg",
              "rosca": "simple", "designacion": "M6", "invertir": False, "objetivos": [],
              "clase_rosca": "", "holgura_3d": "0 mm", "mano": "derecha", "ajuste": "normal", "hasta": None,
              "desfase_hasta": "0 mm", "ref_cara": None, "ref_aristas": [], "ref_distancia1": "10 mm",
              "ref_distancia2": "10 mm"}
    EXPRESIONES = ("diametro", "profundidad", "angulo_punta", "diam_abocardado", "prof_abocardado", "diam_avellanado",
                   "angulo_avellanado", "holgura_3d", "desfase_hasta", "ref_distancia1", "ref_distancia2")
    OPCIONES = {"tipo": ("simple", "abocardado", "avellanado"), "extension": ("distancia", "todo", "hasta"),
                "punta": ("angulo", "plana"), "rosca": ("simple", "holgura", "cosmetica", "modelada", "conico"),
                "ajuste": ("fino", "normal", "grueso"), "mano": ("derecha", "izquierda")}
    REFS = ("posiciones", "hasta", "ref_cara", "ref_aristas")

    def dependencias(self):
        return super().dependencias() | ent.dependencias_de([d["cara"] for d in self.p.get("puntos_cara") or [] if isinstance(d, dict) and "cara" in d])

    def _colocaciones(self, estado, ctx=None):
        """[(punto, dirección hacia el material)] de cada agujero. La posición por referencias necesita `ctx`
        para evaluar sus distancias (sin él no se incluye)."""
        salida = []
        for e in _resolver_todas(self.p["posiciones"], estado):
            n = e.plano.normal if e.plano is not None else np.array([0.0, 0.0, 1.0])
            salida.append((ent.como_punto(e), -n))
        for d in self.p.get("puntos_cara") or []:
            if not isinstance(d, dict) or "cara" not in d:
                raise ParametroMalFormado(d, 'se esperaba {"cara": <referencia de cara>, "punto": [x, y, z]}', "puntos_cara")
            e = _resolver(d["cara"], estado, ("cara",))
            if e.plano is None:
                raise ErrorOperacion("El agujero va sobre una cara plana.")
            p = np.asarray(d["punto"], float)
            salida.append((e.plano.origen + (p - e.plano.origen) - e.plano.normal * float((p - e.plano.origen) @
                                                                                          e.plano.normal),
                           -e.plano.normal))
        if self.p.get("ref_cara") and ctx is not None:
            salida.append(self._por_referencias(estado, ctx))
        if not salida:
            raise ErrorOperacion("Elegí dónde van los agujeros (puntos de boceto, un punto sobre una cara o una cara "
                                 "con dos aristas de referencia).")
        return [(p, -d if self.p["invertir"] else d) for p, d in salida]

    def _por_referencias(self, estado, ctx):
        """Posición «Referencias»: el punto de la cara a las dos distancias de las dos aristas."""
        e = _resolver(self.p["ref_cara"], estado, ("cara",))
        if e.plano is None:
            raise ErrorOperacion("La posición por referencias va sobre una cara plana.")
        aristas = _resolver_todas(self.p.get("ref_aristas") or [], estado, ("arista",))
        if len(aristas) != 2:
            raise ErrorOperacion("La posición por referencias necesita dos aristas rectas de la cara.")
        distancias = [ctx.evaluar(self.p["ref_distancia1"]), ctx.evaluar(self.p["ref_distancia2"])]
        punto = _sc().punto_por_referencias(e.forma, [a.forma for a in aristas], distancias)
        return punto, -e.plano.normal

    def _objetivo_hasta(self, estado):
        if not self.p.get("hasta"):
            raise ErrorOperacion("Extensión «Hasta»: elegí la cara, el plano o el cuerpo donde termina el agujero.")
        e = _resolver(self.p["hasta"], estado, ("cara", "plano", "cuerpo"))
        if e.tipo == "plano":
            return e.plano
        return e.forma

    def opciones_herramienta(self, ctx, rapido=False):
        """Argumentos de `herramienta_agujero` (sin la profundidad) según el tipo de rosca. `rapido`: la rosca
        modelada se reemplaza por su agujero liso (vista previa)."""
        p, sc = self.p, _sc()
        A = lambda k: ctx.evaluar(p[k], ANGULO)  # noqa: E731
        L = lambda k: ctx.evaluar(p[k])  # noqa: E731
        opciones = {"tipo": p["tipo"], "punta": p["punta"], "angulo_punta": A("angulo_punta")}
        rosca = p["rosca"]
        if rosca == "modelada":
            datos = sc.datos_rosca(p["designacion"])
            if datos["conica"]:
                raise ErrorOperacion(f"{datos['designacion']} es una rosca cónica: usá «Roscado cónico».")
            clase, _ = _tol().resolver_clase(datos["familia"], datos["diametro"], datos["paso"],
                                             p.get("clase_rosca") or "", True)
            if rapido:
                opciones["diametro"] = sc.diametro_taladro_rosca(p["designacion"], clase, L("holgura_3d"))
            else:
                opciones.update(diametro=L("diametro"), roscado=p["designacion"], clase=clase,
                                holgura=L("holgura_3d"), mano=p.get("mano") or "derecha")
        elif rosca == "holgura":
            opciones["diametro"] = sc.diametro_paso_libre(p["designacion"], p.get("ajuste") or "normal")
        elif rosca == "conico":
            datos = sc.datos_rosca(p["designacion"])
            if not datos["conica"]:
                raise ErrorOperacion(f"Roscado cónico: {datos['designacion']} no es una rosca de tubería cónica "
                                     "(R/Rc o NPT).")
            opciones.update(diametro=datos["diametro_menor"], conicidad=datos["conicidad"])
        else:
            opciones["diametro"] = L("diametro")
        if p["tipo"] == "abocardado":
            opciones.update(diam_abocardado=L("diam_abocardado"), prof_abocardado=L("prof_abocardado"))
        elif p["tipo"] == "avellanado":
            opciones.update(diam_avellanado=L("diam_avellanado"), angulo_avellanado=A("angulo_avellanado"))
        return opciones

    def herramientas(self, estado, ctx, rapido=False):
        """Sólidos a restar, uno por agujero."""
        p, sc = self.p, _sc()
        if p["objetivos"]:
            # Solo sus objetivos: el pasante los abarca (cuerpos ajenos no deben alargar el barrido de la rosca) y el
            # paso no lee los demás cuerpos, así la memoria del documento lo reusa si otro cuerpo cambia.
            solidos = [estado.cuerpo(cid).forma for cid in p["objetivos"]]
        else:
            solidos = [c.forma for c in estado.cuerpos.values() if getattr(c, "tipo", "solido") == "solido"]
        if not solidos:
            raise ErrorOperacion("No hay cuerpos sólidos para agujerear.")
        opciones = self.opciones_herramienta(ctx, rapido)
        todo = geo.compuesto(solidos) if p["extension"] == "todo" else None
        hasta = self._objetivo_hasta(estado) if p["extension"] == "hasta" else None
        herramientas = []
        for punto, direccion in self._colocaciones(estado, ctx):
            if p["extension"] == "todo":
                herramientas.append(sc.agujero(todo, punto, direccion, profundidad=None, **opciones))
            elif p["extension"] == "hasta":
                prof = sc.profundidad_hasta(punto, direccion, hasta, ctx.evaluar(p.get("desfase_hasta") or "0 mm"))
                herramientas.append(sc.herramienta_agujero(punto, direccion, profundidad=prof, **opciones))
            else:
                herramientas.append(sc.herramienta_agujero(punto, direccion, profundidad=ctx.evaluar(p["profundidad"]),
                                                           **opciones))
        return herramientas

    def ejecutar(self, estado, ctx):
        p = self.p
        herramientas = self.herramientas(estado, ctx)
        if p["rosca"] == "cosmetica":
            ctx.aviso(f"Rosca cosmética {p['designacion']}: no cambia la geometría.")
        elif p["rosca"] == "conico":
            ctx.aviso(f"Roscado cónico {p['designacion']}: el agujero se angosta 1:16 desde la boca (diámetro menor "
                      "en el plano de calibre); la rosca es cosmética.")
        elif p["rosca"] == "modelada" and p.get("clase_rosca"):
            datos = _sc().datos_rosca(p["designacion"])
            _, aviso = _tol().resolver_clase(datos["familia"], datos["diametro"], datos["paso"], p["clase_rosca"],
                                             True)
            if aviso:
                ctx.aviso(aviso)
        self._aplicar(estado, ctx, geo.unir_todos(herramientas), "cortar")


class OpRosca(_OpCrear):
    """Rosca de Fusion [GUID-7BD8CD24, GUID-C37E8172]: sobre una cara cilíndrica; tipo (familia: métrica ISO,
    unificada, trapezoidal, ACME, tubería BSP/NPT), tamaño automático o elegido, clase de tolerancia (6g/6H,
    2A/2B…) y holgura para impresión 3D; largo completo o con desfase; cosmética o modelada; mano derecha o
    izquierda."""
    TIPO, ETIQUETA, ICONO = "rosca", "Rosca", "⌇"
    PARAMS = {"caras": [], "designacion": "", "largo_completo": True, "longitud": "10 mm", "desfase": "0 mm",
              "modelada": True, "mano": "derecha", "invertir": False,
              "familia": "iso_metrica", "clase_rosca": "", "holgura_3d": "0 mm"}   # nuevas: «familia» y siguientes
    EXPRESIONES = ("longitud", "desfase", "holgura_3d")
    OPCIONES = {"mano": ("derecha", "izquierda"), "familia": FAMILIAS_ROSCA}
    REFS = ("caras",)

    def ejecutar(self, estado, ctx):
        ents = _resolver_todas(self.p["caras"], estado, ("cara",))
        if not ents:
            raise ErrorOperacion("Elegí las caras cilíndricas a roscar.")
        p, sc = self.p, _sc()
        holgura = ctx.evaluar(p.get("holgura_3d") or "0 mm")
        self.roscas = []                     # lo que quedó en cada cara (designación y clase): para informar
        for e in ents:
            cuerpo = estado.cuerpo(e.cuerpo)
            info = sc.analizar_rosca(cuerpo.forma, e.forma, designacion=p["designacion"] or None,
                                     familia=p.get("familia") or None)
            datos, modelada = info["datos"], p["modelada"]
            if modelada and datos["conica"]:
                ctx.aviso(f"{datos['designacion']} es una rosca cónica: sobre una cara cilíndrica queda cosmética.")
                modelada = False
            clase, aviso = _tol().resolver_clase(datos["familia"], datos["diametro"], datos["paso"],
                                                 p.get("clase_rosca") or "", info["interna"])
            if aviso and modelada:
                ctx.aviso(aviso)
            cuerpo.forma = sc.rosca(cuerpo.forma, e.forma, designacion=datos["designacion"],
                                    longitud=None if p["largo_completo"] else ctx.evaluar(p["longitud"]),
                                    desfase=ctx.evaluar(p["desfase"]), modelada=modelada, mano=p["mano"],
                                    invertir=p["invertir"], clase=clase, holgura=holgura)
            self.roscas.append({"cuerpo": cuerpo.id, "designacion": datos["designacion"], "clase": clase,
                                "interna": info["interna"], "modelada": modelada})
            if not modelada:
                ctx.aviso("Rosca cosmética: la geometría no cambia (como la rosca no modelada de Fusion).")


class OpBobina(_OpCrear):
    """Bobina de Fusion [SLD-COIL-SOLID]: plano/cara + centro, diámetro, tipo (revoluciones y altura,
    revoluciones y paso, altura y paso o espiral plana), ángulo, sección, su posición y giro de 90° en Y local."""
    TIPO, ETIQUETA, ICONO = "bobina", "Bobina", "➰"
    PARAMS = {"plano": None, "centro": None, "diametro": "20 mm", "tipo": "rev_altura", "revoluciones": "5",
              "altura": "30 mm", "paso": "6 mm", "angulo": "0 deg", "seccion": "circular", "tamano": "3 mm",
              "posicion": "sobre", "horario": False, "girar": False, "operacion": "nuevo", "objetivos": []}
    EXPRESIONES = ("diametro", "revoluciones", "altura", "paso", "angulo", "tamano")
    DATOS = {"rev_altura": ("revoluciones", "altura"), "rev_paso": ("revoluciones", "paso"),
             "altura_paso": ("altura", "paso"), "espiral": ("revoluciones", "paso")}  # tipo → los dos datos
    OPCIONES = {"tipo": DATOS, "seccion": ("circular", "cuadrada", "triangular_externa", "triangular_interna"),
                "posicion": ("dentro", "sobre", "fuera"), "operacion": OPERACIONES_CUERPO}
    REFS = ("plano", "centro")

    def ejecutar(self, estado, ctx):
        p = self.p
        plano = ent.como_plano(_resolver(p["plano"], estado)) if p["plano"] else geo.Plano("XY")
        centro = ent.como_punto(_resolver(p["centro"], estado)) if p["centro"] else plano.origen
        datos = {"revoluciones": None, "altura": None, "paso": None}
        for k in self.DATOS[p["tipo"]]:
            datos[k] = ctx.evaluar(p[k], "escalar" if k == "revoluciones" else "longitud")
        angulo = 0.0 if p["tipo"] == "espiral" else ctx.evaluar(p["angulo"], ANGULO)
        forma = _sc().bobina(centro, plano.normal, diametro=ctx.evaluar(p["diametro"]), angulo=angulo,
                             seccion=p["seccion"], tamano_seccion=ctx.evaluar(p["tamano"]), posicion_seccion=p["posicion"],
                             horario=p["horario"], eje_x=plano.u, tipo=p["tipo"], girar=p["girar"], **datos)
        self._aplicar(estado, ctx, forma)


class OpTuberia(_OpCrear):
    """Tubería de Fusion [SLD-PIPE-SOLID]: cadena tangente, límites fraccionales distancia2 (inicio) y
    distancia (fin), sección y tamaño, hueca con espesor. Sin cadena se conserva solo la ruta elegida."""
    TIPO, ETIQUETA, ICONO = "tuberia", "Tubería", "⊃"
    PARAMS = {"ruta": [], "distancia": "1", "seccion": "circular", "tamano": "5 mm", "hueca": False,
              "espesor": "0.5 mm", "operacion": "nuevo", "objetivos": [], "cadena": False, "distancia2": "0"}
    EXPRESIONES = ("distancia", "distancia2", "tamano", "espesor")
    OPCIONES = {"seccion": ("circular", "cuadrada", "triangular"), "operacion": OPERACIONES_CUERPO}
    REFS = ("ruta",)

    def ejecutar(self, estado, ctx):
        ents, ruta = _aristas(self.p["ruta"], estado, "la ruta")
        if self.p["cadena"]:
            from ..nucleo import referencias
            from ..nucleo.perfiles import aristas_boceto
            from ..nucleo.solidos_modificar import aristas_cadena_tangente
            ruta = []
            formas_boceto = {}
            for e in ents:
                arista = e.forma
                if e.cuerpo:
                    forma = estado.cuerpo(e.cuerpo).forma
                elif e.boceto:
                    br = e.boceto
                    if br.op_id not in formas_boceto:
                        aristas = [a for _, a in aristas_boceto(br.boceto.geometria(), br.plano)]
                        # MakeWire comparte los vértices coincidentes de las curvas independientes del boceto.
                        formas_boceto[br.op_id] = geo.compuesto(_sc()._cadenas(aristas))
                    forma = formas_boceto[br.op_id]
                    arista = referencias.resolver(forma, {"tipo": "arista", "firma": referencias.firma_arista(arista)})
                    if arista is None:
                        raise ErrorOperacion("No se encontró la curva en la cadena del boceto.")
                else:
                    forma = arista
                for a in aristas_cadena_tangente(forma, arista):
                    if not any(a.IsSame(otra) for otra in ruta):
                        ruta.append(a)
        forma = _sc().tuberia(ruta, seccion=self.p["seccion"], tamano=ctx.evaluar(self.p["tamano"]),
                              hueca=self.p["hueca"], espesor=ctx.evaluar(self.p["espesor"]),
                              distancia=ctx.evaluar(self.p["distancia"], "escalar"),
                              distancia2=ctx.evaluar(self.p["distancia2"], "escalar"))
        self._aplicar(estado, ctx, forma)


# Tipos de paso que dejan su herramienta (el sólido que cortan, unen o crean, vía `aplicar_resultado`) y por eso se
# pueden repetir con un patrón de operaciones; también los patrones y multitransformaciones de operaciones. Es la
# lista que muestran los errores (la API y el diálogo la controlan antes de crear el paso).
TIPOS_REPETIBLES = ("extrusion", "revolucion", "agujero", "primitiva", "barrido", "solevacion", "bobina", "tuberia",
                    "relleno_contorno", "solido_envolvente", "patron", "multitransformar")
OBJETOS_PATRON = ("cuerpos", "operaciones", "caras", "componentes", "construccion")
CALCULOS_PATRON = ("identico", "optimizado", "ajustar")      # «Compute Type» del patrón de operaciones de Fusion


def _ids_pasos(p):
    pasos = p.get("pasos") or []
    if not isinstance(pasos, (list, tuple)):
        raise ParametroMalFormado(pasos, "tiene que ser una lista de ids de pasos", "pasos")
    return [str(x) for x in pasos if x]


def _pasos_y_componentes(p):
    """Ids de los pasos que un patrón o una simetría repite y de los pasos que crearon sus componentes."""
    try:
        pasos = set(_ids_pasos(p))
    except ErrorOperacion:
        pasos = set()
    comps = {str(c).split(".")[0] for c in p.get("componentes") or [] if isinstance(c, str) and re.fullmatch(r"op\d+(\..*)?", c)}
    return pasos | comps


def _xyz(ctx, valores, que):
    """[x, y, z] de números o expresiones (mm) → array de 3 floats."""
    if not isinstance(valores, (list, tuple)) or len(valores) != 3:
        raise ErrorOperacion(f"{que} tiene que ser [x, y, z]: llegó {ent.describir_valor(valores)}.")
    return np.array([ctx.evaluar(v) if isinstance(v, str) else float(v) for v in valores], float)


def _puntos_de(entidad):
    """Puntos 3D de una entidad del patrón en puntos: un boceto entero da sus puntos sueltos (los que no son de
    ninguna curva); lo demás, su punto (punto de boceto, vértice, punto de construcción, centro de una curva)."""
    if entidad.tipo == "boceto":
        b = entidad.boceto.boceto
        en_curvas = {i for c in b.curvas.values() for i in c.puntos()}
        return [entidad.plano.a_3d(pt.x, pt.y) for pid, pt in sorted(b.puntos.items()) if pid not in en_curvas]
    return [ent.como_punto(entidad)]


def _eje_pasante(herramienta, cuerpos):
    """Eje de coordenadas (0, 1 o 2) sobre el que la herramienta es un prisma recto que atraviesa el cuerpo de lado a
    lado (agujero «Todo», corte pasante: sus dos extremos quedan fuera del material, sobre su eje central), o None. Un
    escalón, un avellanado o una herramienta que termina dentro del cuerpo no son pasantes: se copian tal cual."""
    if not any(geo.se_tocan(c.forma, herramienta) for c in cuerpos):
        return None
    h = geo.caja_envolvente(herramienta)
    centro = [(h[0][i] + h[1][i]) / 2 for i in range(3)]
    for eje in range(3):
        extremos = []
        for valor, signo in ((h[0][eje], -1), (h[1][eje], 1)):
            p = list(centro)
            p[eje] = valor + signo * 1e-3
            extremos.append(tuple(p))
        if any(geo.punto_toca(c.forma, p, 1e-9) for c in cuerpos for p in extremos):
            continue
        otros = [i for i in range(3) if i != eje]          # una caja corrida un 10 % sobre cualquier eje deja el 90 %: la herramienta
        if any(h[0][i] < min(geo.caja_envolvente(c.forma)[0][i] for c in cuerpos) - 1e-6   # tiene que caber en el cuerpo a lo ancho
               or h[1][i] > max(geo.caja_envolvente(c.forma)[1][i] for c in cuerpos) + 1e-6 for i in otros):
            continue
        largo, v = h[1][eje] - h[0][eje], np.zeros(3)
        v[eje] = 0.1 * largo
        comun = geo.booleano(herramienta, _sc().aplicar(herramienta, _sc()._traslacion(v)), "intersecar")
        if geo.volumen(comun) > 0.9 * geo.volumen(herramienta) - 1e-6 * max(1.0, geo.volumen(herramienta)):
            return eje
    return None


def _prolongar_pasante(copia, eje, cuerpos, t):
    """La copia (con el gp_Trsf `t`) de un prisma pasante sobre el eje de coordenadas `eje`, prolongada a lo largo de ese eje
    ya girado por `t` hasta cubrir `cuerpos` (su copia pudo caer sobre una zona más gruesa: «Ajustar» recalcula el alcance
    de cada instancia). Une corrimientos de la misma copia que se pisan."""
    v = _sc().a_matriz(t)[:3, :3] @ np.eye(3)[eje]
    v = v / np.linalg.norm(v)

    def rango(caja):                      # intervalo de la proyección de una caja sobre v
        puntos = [(x, y, z) for x in (caja[0][0], caja[1][0]) for y in (caja[0][1], caja[1][1]) for z in (caja[0][2], caja[1][2])]
        k = [float(np.dot(p, v)) for p in puntos]
        return min(k), max(k)
    lo = min(rango(geo.caja_envolvente(c.forma))[0] for c in cuerpos)
    hi = max(rango(geo.caja_envolvente(c.forma))[1] for c in cuerpos)
    h0, h1 = rango(geo.caja_envolvente(copia))
    largo = h1 - h0
    faltan_abajo, faltan_arriba = max(0.0, h0 - lo), max(0.0, hi - h1)
    if faltan_abajo <= 1e-6 and faltan_arriba <= 1e-6:
        return copia
    piezas = [copia]
    for sentido, falta in ((-1, faltan_abajo), (1, faltan_arriba)):
        for k in range(1, int(math.ceil(falta / (0.9 * largo))) + 1):
            piezas.append(_sc().aplicar(copia, _sc()._traslacion(sentido * k * 0.9 * largo * v)))
    return _sc().unir_instancias(piezas)


def repetir_pasos(op, estado, ctx, trsfs):
    """Patrón de operaciones (el de features de Fusion, con cálculo «Idéntico»): la herramienta que dejó cada paso
    de `op.p["pasos"]` (la extrusión que corta, el agujero…) se copia con cada gp_Trsf de `trsfs` (sin el original)
    y se aplica con la MISMA operación (cortar, unir o cuerpo nuevo) a los mismos cuerpos que el paso original.
    Con «identico» las extensiones no se recalculan por copia: un agujero «Todo» copiado a una zona más gruesa no la atraviesa.
    `calculo`: "identico" y "optimizado" (el mismo resultado) copian la herramienta tal cual; "ajustar" recalcula cada
    copia: un corte pasante (prisma que cruza el cuerpo de lado a lado) se prolonga hasta cubrir el cuerpo en su
    nueva zona, y las copias que ya no tocan al cuerpo se omiten. Devuelve los ids de los cuerpos afectados."""
    pasos = _ids_pasos(op.p)
    if not pasos:
        raise ErrorOperacion("Elegí las operaciones (pasos del timeline) que se repiten.")
    if not trsfs:
        ctx.aviso("El patrón no tiene copias: no cambió nada.")
        return []
    sc, afectados = _sc(), []
    for pid in pasos:
        registros = estado.herramientas.get(pid)
        if not registros:
            raise ErrorOperacion(
                f"El paso «{pid}» no dejó una herramienta que se pueda repetir: tiene que estar antes de este paso, "
                f"activo y sin error, y ser de un tipo que corta, une o crea con una herramienta. Tipos que se pueden "
                f"repetir: {', '.join(TIPOS_REPETIBLES)} (los dos últimos, de operaciones).")
        for forma, operacion, objetivo, tipo in registros:
            if operacion == "intersecar":
                raise ErrorOperacion(f"El paso «{pid}» interseca: repetirlo dejaría solo lo común a todas las copias. "
                                     "Se repiten los pasos que cortan, unen o crean un cuerpo nuevo.")
            copias = [sc.aplicar(forma, t) for t in trsfs]
            if op.p.get("calculo") == "ajustar" and operacion in ("cortar", "unir") and tipo == "solido":
                # Ajustar (Compute Type › Adjust): cada instancia se calcula por su cuenta; la que ya no toca al cuerpo
                # no hace nada, así que se omite en vez de dejar una herramienta suelta
                lista = list(objetivo) if isinstance(objetivo, (list, tuple)) else [objetivo] if objetivo else []
                cuerpos = [estado.cuerpo(o) for o in lista] or [c for c in estado.cuerpos.values()
                                                                if getattr(c, "tipo", "solido") == "solido"]
                if operacion == "cortar" and cuerpos and (eje := _eje_pasante(forma, cuerpos)) is not None:
                    copias = [_prolongar_pasante(c, eje, cuerpos, t) for c, t in zip(copias, trsfs, strict=True)]   # el «Todo» llega al fondo
                tocan = [c for c in copias if any(geo.se_tocan(cu.forma, c) for cu in cuerpos)]
                if len(tocan) < len(copias):
                    ctx.aviso(f"Ajustar: {len(copias) - len(tocan)} copia(s) no tocan al cuerpo y se omitieron.")
                copias = tocan
                if not copias:
                    continue
            if operacion == "nuevo":              # cada copia, su propio cuerpo (aunque se toquen)
                for copia in copias:
                    afectados += aplicar_resultado(estado, ctx, op.id, copia, operacion, objetivo, tipo)
                continue
            herramienta = sc.unir_instancias(copias) if tipo == "solido" else geo.compuesto(copias)
            afectados += aplicar_resultado(estado, ctx, op.id, herramienta, operacion, objetivo, tipo)
    return afectados


def copiar_caras(op, estado, trsfs):
    """Patrón o simetría de CARAS (Object Type › Faces): cada cara de `op.p["caras"]`, transformada con cada gp_Trsf de
    `trsfs`, queda como un cuerpo de superficie nuevo (el cuerpo del que salen no cambia)."""
    caras = [e.forma for e in _resolver_todas(op.p.get("caras"), estado, ("cara",))]
    if not caras:
        raise ErrorOperacion("Elegí las caras.")
    for cara in caras:
        for t in trsfs:
            estado.nuevo_cuerpo(op.id, _sc().aplicar(cara, t), "superficie")


def copiar_construccion(op, estado, trsfs):
    """Patrón o simetría de GEOMETRÍA DE CONSTRUCCIÓN (Object Type › Construction Geometry): cada plano, eje o punto de
    `op.p["construccion"]`, transformado con cada gp_Trsf de `trsfs`, queda como una entidad de construcción nueva
    (`<paso>_k<n>`, nombre « (copia)»)."""
    entidades = _resolver_todas(op.p.get("construccion"), estado, ("plano", "eje", "punto"))
    if not entidades:
        raise ErrorOperacion("Elegí los planos, ejes o puntos de construcción.")
    n = 0
    for ref, e in zip(op.p["construccion"], entidades, strict=True):
        for t in trsfs:
            n += 1
            m = _sc().a_matriz(t)
            r, v = m[:3, :3], m[:3, 3]
            nuevo = f"{op.id}_k{n}"
            if e.tipo == "plano":
                estado.planos[nuevo] = geo.Plano.desde_marco(r @ e.plano.origen + v, r @ e.plano.normal, r @ e.plano.u,
                                                              estado.nombre_de_copia(e.plano.nombre or "Plano"))
            elif e.tipo == "eje":
                d = r @ np.asarray(e.eje[1], float)
                nombre = estado.ejes.get(ref["id"], (None, None, f"Eje {ref['id']}"))[2]
                estado.ejes[nuevo] = (r @ np.asarray(e.eje[0], float) + v, d / np.linalg.norm(d), estado.nombre_de_copia(nombre))
            else:
                nombre = estado.puntos.get(ref["id"], (None, f"Punto {ref['id']}"))[1]
                estado.puntos[nuevo] = (r @ np.asarray(e.punto, float) + v, estado.nombre_de_copia(nombre))


def copiar_componentes(op, estado, trsfs):
    """Patrón o simetría de COMPONENTES (Object Type › Components): cada componente de `op.p["componentes"]` (id o
    nombre) se copia con cada gp_Trsf de `trsfs` como un componente nuevo con copias de todos sus cuerpos. Solo
    componentes en su lugar de modelado (si una unión los movió, la copia no sabría dónde ir)."""
    from .ops_ensamblar import componente_por_ref
    ids = []
    for ref in op.p.get("componentes") or []:
        k = componente_por_ref(estado, ref)
        if k is None:
            raise ErrorOperacion(f"No encuentro el componente «{ref}».")
        ids.append(k)
    if not ids:
        raise ErrorOperacion("Elegí los componentes.")
    n = 0
    for k in ids:
        if not np.allclose(np.asarray(estado.componentes[k].get("matriz", np.identity(4)), float), np.identity(4)):
            raise ErrorOperacion(f"El componente «{estado.componentes[k].get('nombre') or k}» ya fue movido por una "
                                 "unión: copiá sus cuerpos o volvé a su posición.")
        if any(d.get("padre") == k for d in estado.componentes.values()):
            raise ErrorOperacion(f"El componente «{estado.componentes[k].get('nombre') or k}» tiene subcomponentes: "
                                 "copiarlos todavía no está. Repetí cada subcomponente por separado.")
        cuerpos = [c for c in estado.cuerpos.values() if (c.componente or "") == k]
        for t in trsfs:
            n += 1
            nuevo = f"{op.id}.k{n}"
            estado.componentes[nuevo] = {"nombre": estado.nombre_de_copia(estado.componentes[k].get("nombre") or k),
                                         "padre": "", "fijo": False, "matriz": np.identity(4).tolist(),
                                         **({"origen": estado.componentes[k]["origen"]} if "origen" in estado.componentes[k] else {})}
            for c in cuerpos:
                cid = estado.nuevo_cuerpo(op.id, _sc().aplicar(c.forma, t), c.tipo,
                                          nombre=estado.nombre_de_copia(c.nombre), **atributos_copia(c))
                estado.cuerpo(cid).componente = nuevo


def copiar_objetos(op, estado, ctx, trsfs, sin_cuerpos):
    """Lo que repiten el Patrón y la Simetría según su «Tipo de objeto»; `trsfs` NO incluye el original."""
    objeto = op.p.get("objeto", "cuerpos")
    if objeto == "operaciones":
        if not _ids_pasos(op.p):
            raise ErrorOperacion("Elegí las operaciones (pasos del timeline) que se repiten.")
        op._registrar_usados(repetir_pasos(op, estado, ctx, trsfs))
    elif objeto == "caras":
        copiar_caras(op, estado, trsfs)
    elif objeto == "componentes":
        copiar_componentes(op, estado, trsfs)
    elif objeto == "construccion":
        copiar_construccion(op, estado, trsfs)
    else:
        if not op.p["cuerpos"]:
            raise ErrorOperacion(sin_cuerpos)
        copiar_cuerpos(op, estado, trsfs)


def copiar_cuerpos(op, estado, trsfs):
    """Copias de los cuerpos de `op.p["cuerpos"]` con cada gp_Trsf de `trsfs`: cuerpos nuevos (heredan aspecto,
    material y nombre, con « (copia)») o, con `combinar`, unidas al original. Con `ligeras` las copias son instancias
    (`solidos_crear.instanciar`: comparten la geometría del original); al combinar se unen de verdad."""
    copiar = _sc().instanciar if op.p.get("ligeras") and not op.p["combinar"] else _sc().aplicar
    for cid in op.p["cuerpos"]:
        c = estado.cuerpo(cid)
        copias = [copiar(c.forma, t) for t in trsfs]
        if op.p["combinar"]:
            c.forma = geo.unir_todos([c.forma] + copias)
        else:
            for forma in copias:
                estado.nuevo_cuerpo(op.id, forma, c.tipo, nombre=estado.nombre_de_copia(c.nombre), **atributos_copia(c))


class OpPatron(_OpCrear):
    """Patrón rectangular, circular, en ruta o en puntos de Fusion [SLD-PATTERNS] (el «en puntos» es el Point Pattern
    de FreeCAD; el giro en ruta, su Twisted Path Array).
    `objeto` es el «Tipo de objeto» de Fusion: "cuerpos" (`cuerpos`: cada instancia es un cuerpo nuevo, o se une al
    original con «Combinar») u "operaciones" (`pasos`: ids de pasos anteriores —una extrusión que corta, un
    agujero…—; su herramienta se repite transformada y se aplica con la misma operación a los mismos cuerpos: ver
    `repetir_pasos`).
    `ligeras` (PL8, copias ligeras): las copias de cuerpos son instancias que comparten la geometría del original
    (no se duplica), cada una con su ubicación; con `combinar` no se usan.
    `distribucion` es el «Tipo de distancia» de Fusion: con "extension" (por defecto) d1/d2 son la distancia TOTAL
    entre la primera y la última instancia y, en el circular, `angulo` es el ángulo total; con "espaciado" son la
    separación (o el ángulo) entre instancias consecutivas.
    En ruta, `giro` hace girar cada copia alrededor de la ruta, progresivo hasta ese ángulo total en la última.
    En puntos: `puntos` (puntos de boceto, vértices, puntos de construcción o un boceto entero = sus puntos sueltos)
    y `coordenadas` ([x, y, z], números o expresiones); cada copia lleva el punto de referencia (`referencia`, o
    `referencia_xyz` [x, y, z]; por defecto el origen) a uno de los puntos."""
    TIPO, ETIQUETA, ICONO = "patron", "Patrón", "⁂"
    PARAMS = {"forma_patron": "rectangular", "cuerpos": [], "dir1": None, "n1": 3, "d1": "30 mm", "dir2": None,
              "n2": 1, "d2": "30 mm", "distribucion": "extension", "simetrico": False, "eje": None, "n": 6,
              "angulo": "360 deg", "ruta": [], "orientacion": "identica", "inicio": "0", "suprimir": [],
              "combinar": False, "giro": "0 deg", "puntos": [], "coordenadas": [], "referencia": None,
              "referencia_xyz": [], "objeto": "cuerpos", "pasos": [], "ligeras": False, "caras": [],
              "componentes": [], "construccion": [], "calculo": "identico"}
    EXPRESIONES = ("d1", "d2", "angulo", "inicio", "giro")
    OPCIONES = {"forma_patron": ("rectangular", "circular", "ruta", "puntos"), "distribucion": ("extension", "espaciado"),
                "orientacion": ("identica", "direccion_ruta"), "objeto": OBJETOS_PATRON, "calculo": CALCULOS_PATRON}
    REFS = ("dir1", "dir2", "eje", "ruta", "puntos", "referencia", "caras", "construccion")

    def dependencias(self):
        return (super().dependencias() | _pasos_y_componentes(self.p)) - {self.id}

    def pasos_repetidos(self):
        """Pasos cuya herramienta repite (objeto = "operaciones"); [] con cuerpos."""
        try:
            return _ids_pasos(self.p) if self.p.get("objeto") == "operaciones" else []
        except ErrorOperacion:
            return []

    def expresiones(self):
        xyz = list(self.p.get("coordenadas") or []) + [self.p.get("referencia_xyz") or []]
        return super().expresiones() + [v for c in xyz if isinstance(c, (list, tuple)) for v in c if isinstance(v, str)]

    def puntos_patron(self, estado, ctx):
        """(puntos, referencia) del patrón en puntos, en 3D."""
        p = self.p
        coordenadas = p.get("coordenadas") or []
        if not isinstance(coordenadas, (list, tuple)):
            raise ParametroMalFormado(coordenadas, "tiene que ser una lista de [x, y, z]", "coordenadas")
        puntos = [q for e in _resolver_todas(p.get("puntos"), estado) for q in _puntos_de(e)]
        puntos += [_xyz(ctx, c, "Cada coordenada") for c in coordenadas]
        if not puntos:
            raise ErrorOperacion("Elegí los puntos del patrón (puntos de boceto, vértices, puntos de construcción, un "
                                 "boceto con puntos sueltos o coordenadas [x, y, z]).")
        if p.get("referencia"):
            ref = ent.como_punto(_resolver(p["referencia"], estado))
        elif p.get("referencia_xyz"):
            ref = _xyz(ctx, p["referencia_xyz"], "«referencia_xyz»")
        else:
            ref = np.zeros(3)
        return puntos, ref

    def aclaracion_distancias(self):
        """Frase que dice cómo se leen las distancias (o el ángulo) con la `distribucion` actual."""
        forma = self.p["forma_patron"]
        campo = {"circular": "angulo", "ruta": "d1"}.get(forma, "d1/d2")
        if self.p["distribucion"] == "espaciado":
            return f"{campo} es la separación entre instancias consecutivas (distribucion = \"espaciado\")."
        return (f"{campo} es la distancia TOTAL entre la primera y la última instancia (distribucion = \"extension\", "
                "como «Extensión» de Fusion); para dar la separación entre instancias usá distribucion = \"espaciado\".")

    def transformaciones(self, estado, ctx):
        p, sc = self.p, _sc()
        try:
            sup = tuple(int(i) for i in p.get("suprimir") or [])
        except (TypeError, ValueError):
            raise ErrorOperacion(f"«suprimir» tiene que ser una lista de números enteros (índices de copia): llegó "
                                 f"{ent.describir_valor(p.get('suprimir'))}.") from None
        if p["forma_patron"] == "rectangular":
            if not p["dir1"]:
                raise ErrorOperacion("Elegí la dirección 1.")
            d1 = ent.direccion(_resolver(p["dir1"], estado))
            d2 = ent.direccion(_resolver(p["dir2"], estado)) if p["dir2"] else None
            return sc.transformaciones_rectangulares(d1, self.entero("n1"), ctx.evaluar(p["d1"]), d2, self.entero("n2") if d2 is not None else 1,
                                                     ctx.evaluar(p["d2"]), distribucion=p["distribucion"],
                                                     simetrico1=p["simetrico"], simetrico2=p["simetrico"], suprimir=sup)
        if p["forma_patron"] == "circular":
            if not p["eje"]:
                raise ErrorOperacion("Elegí el eje.")
            punto, eje = ent.como_eje(_resolver(p["eje"], estado))
            return sc.transformaciones_circulares(punto, eje, self.entero("n"),
                                                  angulo_total=ctx.evaluar(p["angulo"], ANGULO),
                                                  distribucion="completa" if p["distribucion"] == "extension"
                                                  else "espaciado", simetrico=p["simetrico"], suprimir=sup)
        if p["forma_patron"] == "puntos":
            puntos, ref = self.puntos_patron(estado, ctx)
            return sc.transformaciones_en_puntos(puntos, ref, suprimir=sup)
        _, ruta = _aristas(p["ruta"], estado, "la ruta")
        return sc.transformaciones_en_ruta(ruta, self.entero("n1"), ctx.evaluar(p["d1"]), orientacion=p["orientacion"],
                                           inicio=ctx.evaluar(p["inicio"], "escalar"), distribucion=p["distribucion"],
                                           simetrico=p["simetrico"], suprimir=sup,
                                           giro=ctx.evaluar(p.get("giro") or "0", ANGULO))

    def ejecutar(self, estado, ctx):
        _ejecutar_patron(self, estado, ctx, "Elegí los cuerpos del patrón.")


def _ejecutar_patron(op, estado, ctx, sin_cuerpos):
    """`ejecutar` común del Patrón y la Multitransformación: repite pasos, caras o componentes, o copia cuerpos."""
    copiar_objetos(op, estado, ctx, op.transformaciones(estado, ctx)[1:], sin_cuerpos)    # la primera es el original


TIPOS_TRANSFORMACION = ("rectangular", "circular", "ruta", "puntos", "simetria")


class OpMultitransformar(_OpCrear):
    """Multitransformación (PartDesign › MultiTransform de FreeCAD; en Fusion se encadenan patrones y simetrías):
    una lista de transformaciones apilables en un solo paso. Cada una se aplica a TODAS las instancias que dejaron
    las anteriores: patrón rectangular de 3 + simetría = 6 instancias.

    `transformaciones`: lista de dicts con "tipo" ("rectangular", "circular", "ruta", "puntos" o "simetria") y los
    campos de ese tipo con las mismas claves que el Patrón (dir1, n1, d1, dir2, n2, d2, distribucion, simetrico,
    eje, n, angulo, ruta, orientacion, inicio, giro, puntos, coordenadas, referencia, referencia_xyz, suprimir) o,
    en la simetría, "plano". `objeto`, `cuerpos`, `pasos` y `combinar`, como en el Patrón."""
    TIPO, ETIQUETA, ICONO = "multitransformar", "Multitransformación", "✣"
    PARAMS = {"objeto": "cuerpos", "cuerpos": [], "pasos": [], "transformaciones": [], "combinar": False,
              "ligeras": False, "caras": [], "componentes": [], "construccion": [], "calculo": "identico"}
    OPCIONES = {"objeto": OBJETOS_PATRON, "calculo": CALCULOS_PATRON}
    REFS = ("caras", "construccion")

    def _lista(self):
        lista = self.p.get("transformaciones") or []
        if not isinstance(lista, (list, tuple)) or not all(isinstance(t, dict) for t in lista):
            raise ParametroMalFormado(lista, 'se esperaba una lista de dicts como {"tipo": "rectangular", …}',
                                      "transformaciones")
        return list(lista)

    def _patron(self, t):
        return OpPatron(self.id, forma_patron=t.get("tipo"), **{k: v for k, v in t.items() if k != "tipo"})

    def dependencias(self):
        deps = super().dependencias()
        try:
            lista, pasos = self._lista(), _pasos_y_componentes(self.p)
        except ErrorOperacion:
            return deps
        for t in lista:
            deps |= ent.dependencias_de(*(t.get(k) for k in OpPatron.REFS + ("plano",)))
        return (deps | pasos) - {self.id}

    pasos_repetidos = OpPatron.pasos_repetidos

    def expresiones(self):
        try:
            lista = self._lista()
        except ErrorOperacion:
            return []
        return [e for t in lista if t.get("tipo") in TIPOS_TRANSFORMACION and t.get("tipo") != "simetria"
                for e in self._patron(t).expresiones()]

    def transformaciones(self, estado, ctx):
        """Lista compuesta de gp_Trsf (la primera, la identidad = el original)."""
        lista = self._lista()
        if not lista:
            raise ErrorOperacion("Agregá al menos una transformación (rectangular, circular, ruta, puntos o simetria).")
        from ..nucleo.consultas import transformacion_identidad
        sc, listas = _sc(), []
        for i, t in enumerate(lista, start=1):
            tipo = t.get("tipo")
            if tipo not in TIPOS_TRANSFORMACION:
                raise ErrorOperacion(f"Transformación {i}: «tipo» tiene que ser uno de: {', '.join(TIPOS_TRANSFORMACION)}; "
                                     f"llegó {ent.describir_valor(tipo)}.")
            try:
                if tipo == "simetria":
                    if not t.get("plano"):
                        raise ErrorOperacion("elegí el plano de simetría.")
                    plano = ent.como_plano(_resolver(t["plano"], estado))
                    listas.append([transformacion_identidad(), sc.transformacion_simetria(plano)])
                    continue
                patron = self._patron(t)
                patron.revisar_parametros()
                patron.validar_opciones()
                listas.append(patron.transformaciones(estado, ctx))
            except ParametroMalFormado:
                raise
            except (ErrorOperacion, ent.ErrorReferencia, geo.ErrorGeometria) as e:
                raise ErrorOperacion(f"Transformación {i} ({tipo}): {e}") from e
        return sc.componer_transformaciones(listas)

    def ejecutar(self, estado, ctx):
        _ejecutar_patron(self, estado, ctx, "Elegí los cuerpos de la multitransformación.")


class OpSimetria(_OpCrear):
    """Simetría de Fusion [GUID-77CE43FF]: copia reflejada en un plano de cuerpos (nuevos o unidos), de caras (queda una
    superficie por cara), de componentes (copias reflejadas) o de operaciones del timeline (`pasos`: su herramienta se
    refleja y se aplica con la misma operación). `objeto` elige cuál."""
    TIPO, ETIQUETA, ICONO = "simetria", "Simetría", "⇋"
    PARAMS = {"cuerpos": [], "plano": None, "combinar": False, "objeto": "cuerpos", "caras": [], "componentes": [],
              "pasos": [], "construccion": [], "calculo": "identico"}
    OPCIONES = {"objeto": OBJETOS_PATRON, "calculo": CALCULOS_PATRON}
    REFS = ("plano", "caras", "construccion")

    def dependencias(self):
        return (super().dependencias() | _pasos_y_componentes(self.p)) - {self.id}

    def ejecutar(self, estado, ctx):
        if not self.p["plano"]:
            raise ErrorOperacion("Elegí el plano de simetría.")
        plano = ent.como_plano(_resolver(self.p["plano"], estado))
        if self.p.get("objeto", "cuerpos") != "cuerpos":
            copiar_objetos(self, estado, ctx, [_sc().transformacion_simetria(plano)], "Elegí los cuerpos.")
            return
        if not self.p["cuerpos"]:
            raise ErrorOperacion("Elegí los cuerpos y el plano de simetría.")
        for cid in self.p["cuerpos"]:
            c = estado.cuerpo(cid)
            reflejo = _sc().simetria(c.forma, plano)
            if self.p["combinar"]:
                c.forma = geo.booleano(c.forma, reflejo, "unir")
            else:
                estado.nuevo_cuerpo(self.id, reflejo, c.tipo, nombre=estado.nombre_de_copia(c.nombre), **atributos_copia(c))


class OpPatronGeometrico(_OpCrear):
    """Patrón geométrico de Fusion [Plastic > Create > Geometric Pattern]: esferas, cilindros, cajas u objetos a medida
    repartidos sobre las caras planas `caras` con un gradiente de tamaño (`nucleo/patron_geometrico.py` explica cada
    opción). `operacion`: unir, cortar, intersecar o cuerpo nuevo."""
    TIPO, ETIQUETA, ICONO = "patron_geometrico", "Patrón geométrico", "⁘"
    PARAMS = {"caras": [], "objeto": "esfera", "personalizado": None, "tamano1": "2 mm", "tamano2": "4 mm",
              "dispersion": "1", "distribucion": "rectangular", "separacion": "incremento", "distancia": "6 mm",
              "cantidad_u": 5, "cantidad_v": 5, "distancia_radial": "6 mm", "rayos": 8, "orientacion": "cara",
              "alineacion_u": "centro", "desfase_u": "0 mm", "alineacion_v": "medio", "desfase_v": "0 mm",
              "limpiar_perimetro": True, "desfase_perimetro": "0 mm", "operacion": "cortar", "objetivos": []}
    EXPRESIONES = ("tamano1", "tamano2", "dispersion", "distancia", "distancia_radial", "desfase_u", "desfase_v",
                   "desfase_perimetro")
    OPCIONES = {"objeto": ("esfera", "cilindro", "caja", "personalizado"), "operacion": OPERACIONES_CUERPO,
                "distribucion": ("rectangular", "triangular", "hexagonal", "circular", "radial"),
                "separacion": ("incremento", "extension"), "orientacion": ("paralela", "cara"),
                "alineacion_u": ("izquierda", "centro", "derecha"), "alineacion_v": ("abajo", "medio", "arriba")}
    REFS = ("caras", "personalizado")

    def ejecutar(self, estado, ctx):
        p = self.p
        if not p["caras"]:
            raise ErrorOperacion("Elegí las caras planas donde va el patrón.")
        L = lambda k: ctx.evaluar(p[k])  # noqa: E731
        custom = None
        if p["objeto"] == "personalizado":
            if not p["personalizado"]:
                raise ErrorOperacion("Elegí el cuerpo que se repite (objeto personalizado).")
            custom = _resolver(p["personalizado"], estado).forma
        formas = []
        for e in _resolver_todas(p["caras"], estado):
            try:
                formas.append(_pg().patron_geometrico(
                    e.forma, p["objeto"], L("tamano1"), L("tamano2"), dispersion=ctx.evaluar(p["dispersion"], "escalar"),
                    distribucion=p["distribucion"], sobre_la_cara=p["operacion"] in ("unir", "nuevo"), personalizado=custom,
                    separacion=p["separacion"], distancia=L("distancia"), cantidad_u=int(p["cantidad_u"]),
                    cantidad_v=int(p["cantidad_v"]), distancia_radial=L("distancia_radial"), rayos=int(p["rayos"]),
                    orientacion=p["orientacion"], alineacion_u=p["alineacion_u"], desfase_u=L("desfase_u"),
                    alineacion_v=p["alineacion_v"], desfase_v=L("desfase_v"),
                    limpiar_perimetro=bool(p["limpiar_perimetro"]), desfase_perimetro=L("desfase_perimetro")))
            except geo.ErrorGeometria as err:
                raise ErrorOperacion(str(err)) from err
        self._aplicar(estado, ctx, geo.compuesto(formas))


class OpReticulaVolumetrica(Operacion):
    """Retícula volumétrica de Fusion [Solid > Modify > Volumetric Lattice]: llena el sólido `cuerpo` con una estructura
    interna por celdas (`nucleo/reticula.py` explica las formas); también una malla cerrada. El cuerpo queda reemplazado
    por la retícula (sólido para las barras; cuerpo de malla para las superficies mínimas). `tamano` es la celda;
    `tamano_y` y `tamano_z` (vacíos = el mismo) la hacen no uniforme. `barras`: celda a medida, [x1,y1,z1,x2,y2,z2] en
    fracciones de la celda. `solidez` es el porcentaje de material (1 a 99); con `solidez_final` y `ruta` (una arista o
    curva, o puntos) va en gradiente por la ruta. `desfase`/`mezcla` > 0 arman la zona de desfase alrededor de `zonas`
    (vacío = todas las caras del cuerpo), con `solidez_desfase` (0 a 100). `mover_*` y `girar_*` mueven y giran las
    celdas."""
    TIPO, ETIQUETA, ICONO = "reticula_volumetrica", "Retícula volumétrica", "▦"
    PARAMS = {"cuerpo": "", "forma_celda": "gyroid", "tamano": "5 mm", "tamano_y": "", "tamano_z": "", "solidez": "30",
              "resolucion": 8, "barras": [], "solidez_final": "", "ruta": [], "zonas": [], "desfase": "0 mm",
              "solidez_desfase": "100", "mezcla": "0 mm", "mover_x": "0 mm", "mover_y": "0 mm", "mover_z": "0 mm",
              "girar_x": "0 deg", "girar_y": "0 deg", "girar_z": "0 deg"}
    EXPRESIONES = ("tamano", "tamano_y", "tamano_z", "solidez", "solidez_final", "desfase", "solidez_desfase", "mezcla",
                   "mover_x", "mover_y", "mover_z", "girar_x", "girar_y", "girar_z")
    OPCIONES = {"forma_celda": ("cross", "x_cell", "x_cell_25d", "custom", "gyroid", "schwarz_p", "schwarz_d")}

    def dependencias(self):
        p = self.p
        return (_deps_objetivo(p.get("cuerpo")) | ent.dependencias_de(p.get("ruta"), p.get("zonas"))) - {self.id}

    def _puntos(self, refs, estado, paso):
        """Polilínea/nube de puntos de las referencias: un punto o vértice da su punto; una arista o curva, su
        polilínea; una cara o cuerpo, puntos sobre su superficie."""
        from ..nucleo import reticula
        salida = []
        for e in _resolver_todas(refs, estado):
            if e.punto is not None:
                salida.append(np.reshape(e.punto, (1, 3)))
            elif e.forma is not None and e.tipo in ("cara", "cuerpo"):
                salida.append(reticula.muestrear(e.forma, paso))
            elif e.forma is not None:
                salida.extend(p for p in geo.polilineas_aristas(e.forma, paso / 4) if len(p))
            else:
                raise ErrorOperacion("La ruta y las zonas de la retícula son puntos, aristas, curvas, caras o cuerpos.")
        return np.concatenate(salida).astype(float) if salida else np.zeros((0, 3))

    def ejecutar(self, estado, ctx):
        from ..nucleo import reticula
        from .parametros import ESCALAR, LONGITUD
        p = self.p
        if not p["cuerpo"]:
            raise ErrorOperacion("Elegí el sólido o la malla cerrada que se llena con la retícula.")
        c = estado.cuerpo(p["cuerpo"])
        if getattr(c, "tipo", "solido") not in ("solido", "malla"):
            raise ErrorOperacion("La retícula se aplica a un cuerpo sólido o a una malla cerrada.")

        def opcional(clave, tipo=LONGITUD):
            texto = str(p.get(clave) or "").strip()
            return ctx.evaluar(texto, tipo) if texto else None
        s = ctx.evaluar(p["tamano"])
        tam = (s, *(s if (v := opcional(k)) is None else v for k in ("tamano_y", "tamano_z")))
        solidez = ctx.evaluar(p["solidez"], ESCALAR) / 100.0
        final = opcional("solidez_final", ESCALAR)
        desfase, mezcla = opcional("desfase") or 0.0, opcional("mezcla") or 0.0
        en_zona = (100.0 if opcional("solidez_desfase", ESCALAR) is None else opcional("solidez_desfase", ESCALAR)) / 100
        if min(tam) <= 0 or not 0.01 <= solidez <= 0.99 or (final is not None and not 1 <= final <= 99):
            raise ErrorOperacion("El tamaño de celda es positivo y la solidez va de 1 a 99 %.")
        if desfase < 0 or mezcla < 0 or not 0 <= en_zona <= 1:
            raise ErrorOperacion("El desfase y la mezcla no son negativos y la solidez del desfase va de 0 a 100 %.")
        paso = min(tam) / 8
        ruta = self._puntos(p.get("ruta") or [], estado, paso) if final is not None else None
        zona = None
        if desfase > 0 or mezcla > 0:
            zona = self._puntos(p["zonas"], estado, paso) if p.get("zonas") else reticula.muestrear(c.forma, paso)
        try:
            rejilla = reticula.Rejilla(reticula.caja(c.forma)[0], tam, [opcional(f"mover_{e}") or 0.0 for e in "xyz"],
                                       [opcional(f"girar_{e}", ANGULO) or 0.0 for e in "xyz"])
            solidez_en = reticula.campo_solidez(solidez, None if final is None else final / 100, ruta, zona, desfase,
                                                en_zona, mezcla)
            if p["forma_celda"] in reticula.FORMAS_BARRAS:
                c.forma = reticula.reticula_barras(c.forma, p["forma_celda"], solidez_en, rejilla, p.get("barras"))
                c.tipo = "solido"
            else:
                c.forma = reticula.reticula_malla(c.forma, p["forma_celda"], solidez_en, rejilla, int(p["resolucion"]))
                c.tipo = "malla"
        except geo.ErrorGeometria as err:
            raise ErrorOperacion(str(err)) from err


class OpRellenoContorno(_OpCrear):
    """Relleno de contorno de Fusion [GUID-575E005F]: las herramientas (cuerpos, caras, planos) forman celdas
    cerradas y las elegidas pasan a ser sólido.

    `herramientas`: lista de referencias: cuerpo {"tipo": "cuerpo", "cuerpo": "op1.c1"}, plano {"tipo": "plano",
    "id": "XY"} (o el id de un plano de construcción) o cara {"tipo": "cara", "cuerpo": …, "firma": …} (copiada de
    find_faces). `celdas`: índices de las regiones cerradas, ordenadas por centroide (x, y, z); [] = la celda 0.
    `operacion`: nuevo/unir/cortar/intersecar; `objetivos`: ids de los cuerpos a unir, cortar o intersecar."""
    TIPO, ETIQUETA, ICONO = "relleno_contorno", "Relleno de contorno", "▩"
    PARAMS = {"herramientas": [], "celdas": [], "operacion": "nuevo", "objetivos": []}
    OPCIONES = {"operacion": OPERACIONES_CUERPO}
    REFS = ("herramientas",)

    def formas_herramienta(self, estado):
        formas = []
        for e in _resolver_todas(self.p["herramientas"], estado):
            formas.append(e.plano if e.tipo == "plano" else e.forma)
        if len(formas) < 1:
            raise ErrorOperacion("Elegí las herramientas que encierran el volumen.")
        return formas

    def ejecutar(self, estado, ctx):
        celdas = self.p["celdas"] or [0]
        forma = _sc().relleno_contorno(self.formas_herramienta(estado), [int(i) for i in celdas])
        self._aplicar(estado, ctx, forma)


def _en_componente(estado, op, creados):
    """Deja los cuerpos recién creados en un componente nuevo con el id y el nombre del paso (como Fusion)."""
    estado.componentes[op.id] = {"nombre": op.nombre, "padre": "", "fijo": False, "matriz": np.identity(4).tolist()}
    for cid in creados:
        estado.cuerpo(cid).componente = op.id


class OpSolidoEnvolvente(_OpCrear):
    """Sólido envolvente de Fusion [SLD-CREATE-BOUNDING-SOLID]: caja, cilindro o tubo que contiene los cuerpos.

    `orientacion` (Coordinate System de Fusion): "modelo" (ejes del modelo; `eje` fija el del cilindro),
    "automatica" (la menor), "z_x" / "z_y" / "x_y" (dos ejes en `eje_a` y `eje_b`, el primero manda) o "scu"
    (un sistema de coordenadas de usuario en `scu`). `componente` deja el sólido en un componente nuevo (como
    Fusion) y `grupo_rigido` lo liga a los componentes de los cuerpos envueltos. `origen` (Origin Mode) es dónde queda
    el origen del componente: "modelo" (el del documento), "centro" del sólido o su "esquina" mínima; la geometría no
    cambia y el origen acompaña al componente cuando se mueve (get_assembly › origin)."""
    TIPO, ETIQUETA, ICONO = "solido_envolvente", "Sólido envolvente", "⬚"
    PARAMS = {"cuerpos": [], "tipo": "caja", "margen": "0 mm", "eje": "z", "operacion": "nuevo", "objetivos": [],
              "orientacion": "modelo", "eje_a": None, "eje_b": None, "scu": None, "espesor_tubo": "",
              "componente": False, "grupo_rigido": False, "origen": "modelo"}
    EXPRESIONES = ("margen", "espesor_tubo")        # espesor_tubo "" = la décima parte del radio
    OPCIONES = {"tipo": ("caja", "cilindro", "tubo"), "operacion": OPERACIONES_CUERPO,
                "orientacion": ("modelo", "automatica", "z_x", "z_y", "x_y", "scu"),    # eje: "x", "y", "z" o un vector
                "origen": ("modelo", "centro", "esquina")}
    REFS = ("eje_a", "eje_b")

    def dependencias(self):
        extra = {self.p["scu"]} if self.p.get("scu") else set()
        return super().dependencias() | extra

    def _marco(self, estado):
        o = self.p["orientacion"]
        if o == "modelo":
            return None
        if o == "automatica":
            return "automatica"
        sc = _sc()
        if o == "scu":
            sid = self.p["scu"]
            if f"{sid}_x" not in estado.ejes:
                raise ErrorOperacion("Elegí el sistema de coordenadas de usuario de la orientación.")
            return sc.marco_ortonormal(z=estado.ejes[f"{sid}_z"][1], x=estado.ejes[f"{sid}_x"][1])

        def direccion(clave):
            if not self.p[clave]:
                raise ErrorOperacion("La orientación necesita dos ejes: eje_a y eje_b.")
            return np.asarray(ent.como_eje(_resolver(self.p[clave], estado))[1], float)
        a, b = direccion("eje_a"), direccion("eje_b")
        n1, n2 = o.split("_")
        return sc.marco_ortonormal(**{n1: a, n2: b})

    def ejecutar(self, estado, ctx):
        if not self.p["cuerpos"]:
            raise ErrorOperacion("Elegí los cuerpos.")
        formas = [estado.cuerpo(c).forma for c in self.p["cuerpos"]]
        espesor = self.p["espesor_tubo"]
        forma = _sc().solido_envolvente(formas, tipo=self.p["tipo"], margen=ctx.evaluar(self.p["margen"]),
                                        eje=self.p["eje"], marco=self._marco(estado),
                                        espesor_tubo=ctx.evaluar(espesor) if str(espesor).strip() else None)
        creados = aplicar_resultado(estado, ctx, self.id, forma, self.p["operacion"], self.p.get("objetivos") or "")
        self._registrar_usados(creados)
        if self.p["operacion"] != "nuevo" or not (self.p["componente"] or self.p["grupo_rigido"]):
            if self.p.get("origen", "modelo") != "modelo":
                ctx.aviso("El origen solo vale con «En un componente nuevo»: no se cambió.")
            return
        envueltos = {estado.cuerpo(c).componente for c in self.p["cuerpos"]} - {"", None}
        _en_componente(estado, self, creados)
        if self.p.get("origen", "modelo") != "modelo":
            marco = self._marco(estado)             # esquina y centro en el marco de la orientación, no el del mundo
            if isinstance(marco, str):
                marco = _sc()._marco_automatico(geo.compuesto(formas))
            r = np.identity(3) if marco is None else np.asarray(marco, float)
            a_marco = np.identity(4)
            a_marco[:3, :3] = r.T
            caja = geo.caja_envolvente(geo.transformar(
                geo.compuesto([estado.cuerpo(c).forma for c in creados]), a_marco))
            estado.componentes[self.id]["origen"] = [float(x) for x in r @ (
                np.mean(caja, axis=0) if self.p["origen"] == "centro" else caja[0])]
        if self.p["grupo_rigido"]:
            if not envueltos:
                ctx.aviso("«Grupo rígido» solo vale cuando el sólido envuelve componentes: no se creó el grupo.")
            else:
                estado.grupos_rigidos = estado.grupos_rigidos + [[self.id, *sorted(envueltos)]]


class OpVolumenFluido(_OpCrear):
    """Volumen de fluido de Fusion [SLD-FLUID-VOLUME]: el sólido del interior o del exterior de un diseño, en un
    componente nuevo. `tapas` son superficies que cubren las aberturas; `separar_caras` es «Split Result»."""
    TIPO, ETIQUETA, ICONO = "volumen_fluido", "Volumen de fluido", "≋"
    PARAMS = {"cuerpos": [], "tapas": [], "tipo": "interno", "forma_externa": "caja", "margen": "10 mm",
              "separar_caras": False}
    EXPRESIONES = ("margen",)
    OPCIONES = {"tipo": ("interno", "externo"), "forma_externa": ("caja", "cilindro", "semiesfera")}

    def dependencias(self):
        return (_deps_objetivo(self.p["cuerpos"]) | _deps_objetivo(self.p["tapas"])) - {self.id}

    def ejecutar(self, estado, ctx):
        if not self.p["cuerpos"]:
            raise ErrorOperacion("Elegí los cuerpos del diseño.")
        solidos = [estado.cuerpo(c).forma for c in self.p["cuerpos"]]
        tapas = [estado.cuerpo(c).forma for c in self.p["tapas"]]
        forma = _sc().volumen_fluido(solidos, tapas, tipo=self.p["tipo"], forma_externa=self.p["forma_externa"],
                                     margen=ctx.evaluar(self.p["margen"]), separar_caras=self.p["separar_caras"])
        creados = aplicar_resultado(estado, ctx, self.id, forma, "nuevo", "")
        self._registrar_usados(creados)
        _en_componente(estado, self, creados)


class OpReglaPlastico(_OpCrear):
    """Asignar regla de plástico [Plastic > Setup > Assign Plastic Rule]: la regla (una COPIA en la receta: queda
    «en este diseño») pasa al componente `componente` y su material físico a todos sus cuerpos. Los valores
    físicos quedan en `estado.componentes[componente]["regla_plastico"]`. Una regla distinta, asignada después al
    mismo componente, reemplaza a esta."""
    TIPO, ETIQUETA, ICONO = "regla_plastico", "Regla de plástico", "◈"
    PARAMS = {"componente": "", "regla": None}

    def dependencias(self):
        return {str(self.p["componente"]).split(".")[0]} - {"", self.id}

    def ejecutar(self, estado, ctx):
        from .ops_ensamblar import componente_por_ref
        k = componente_por_ref(estado, self.p["componente"])
        if k is None:
            raise ErrorOperacion("Elegí el componente: ENSAMBLAR › Nuevo componente lo crea.")
        regla = self.p["regla"]
        if not isinstance(regla, dict) or "espesor" not in regla:
            raise ErrorOperacion("Elegí la regla de plástico.")
        estado.componentes[k]["regla_plastico"] = dict(regla)
        if regla.get("material"):
            for c in estado.cuerpos.values():
                if (c.componente or "") == k:
                    c.material = regla["material"]


class OpSaliente(_OpCrear):
    """Saliente (Boss) de PLÁSTICO [SLD-BOSS], simplificado: columna con agujero que nace en un punto.

    `sentido` (hacia dónde crece, sobre la normal del plano del boceto): "auto" (como Fusion) = hacia afuera del
    material si el punto está sobre una cara del cuerpo, y hacia el cuerpo si está en el aire; "plano" = siempre
    −normal del plano (el cálculo de las recetas guardadas antes del automático, ver `migrar_receta`).
    `invertir` (Flip) da vuelta el sentido elegido."""
    TIPO, ETIQUETA, ICONO = "saliente", "Saliente", "⌾"
    PARAMS = {"posiciones": [], "diametro_exterior": "8 mm", "diametro_agujero": "3 mm", "altura": "",
              "profundidad_agujero": "", "angulo_desmoldeo": "0 deg", "invertir": False, "sentido": "auto"}
    EXPRESIONES = ("diametro_exterior", "diametro_agujero", "angulo_desmoldeo")
    OPCIONES = {"sentido": ("auto", "plano")}
    REFS = ("posiciones",)

    @staticmethod
    def migrar_receta(d):
        """Un saliente guardado sin «sentido» (antes del automático) conserva el cálculo de antes: "plano"."""
        params = d.get("params", {})
        if isinstance(params, dict) and "sentido" not in params:
            d = dict(d, params=dict(params, sentido="plano"))
        return d

    def ejecutar(self, estado, ctx):
        ents = _resolver_todas(self.p["posiciones"], estado)
        if not ents:
            raise ErrorOperacion("Elegí puntos de boceto donde van los salientes.")
        L = lambda k: ctx.evaluar(self.p[k]) if str(self.p.get(k) or "").strip() else None  # noqa: E731
        for e in ents:
            n = e.plano.normal if e.plano is not None else np.array([0.0, 0.0, 1.0])
            cuerpo = _cuerpo_objetivo(estado, [e] if e.forma is not None else
                                      [ent.Entidad("punto", forma=_vertice(ent.como_punto(e)))], self.p)
            d = _sentido_saliente(cuerpo.forma, ent.como_punto(e), n) if self.p["sentido"] == "auto" else -n
            if self.p["invertir"]:
                d = -d
            cuerpo.forma = _sc().saliente(cuerpo.forma, ent.como_punto(e), d, diametro_exterior=L("diametro_exterior"),
                                          diametro_agujero=L("diametro_agujero"), altura=L("altura"),
                                          profundidad_agujero=L("profundidad_agujero"),
                                          angulo_desmoldeo=ctx.evaluar(self.p["angulo_desmoldeo"], ANGULO))
            self._registrar_usados([cuerpo.id])


def _sentido_saliente(forma, punto, normal):
    """Sentido automático del saliente sobre `normal`: si `punto` está sobre una cara de `forma` (material de un
    solo lado), hacia afuera del material; si está en el aire (o dentro), hacia el cuerpo: +normal cuando el cuerpo
    entero queda de ese lado y −normal si no (lo de antes)."""
    from ..nucleo.consultas import dentro_solidos
    n = np.asarray(normal, float) / np.linalg.norm(normal)
    p = np.asarray(punto, float)
    solidos = geo.solidos(forma) or [forma]

    def dentro(q):
        return dentro_solidos(solidos, q)

    arriba, abajo = dentro(p + 1e-3 * n), dentro(p - 1e-3 * n)
    if arriba != abajo:
        return -n if arriba else n
    (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(forma)
    esquinas = np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])
    return n if float(((esquinas - p) @ n).min()) >= -1e-6 else -n


def _vertice(p):
    from ..nucleo.consultas import vertice
    return vertice(p)


class OpLabio(_OpCrear):
    """Labio / ranura de PLÁSTICO [SLD-LIP], simplificado: sección rectangular a lo largo del borde."""
    TIPO, ETIQUETA, ICONO = "labio", "Labio", "⊓"
    PARAMS = {"aristas": [], "tipo": "labio", "ancho": "1 mm", "alto": "1.5 mm", "holgura": "0.1 mm",
              "direccion": None, "invertir": False}
    EXPRESIONES = ("ancho", "alto", "holgura")
    OPCIONES = {"tipo": ("labio", "ranura")}
    REFS = ("aristas", "direccion")

    def ejecutar(self, estado, ctx):
        ents, aristas = _aristas(self.p["aristas"], estado, "las aristas del borde")
        cuerpo = estado.cuerpo(ents[0].cuerpo)
        d = ent.direccion(_resolver(self.p["direccion"], estado)) if self.p["direccion"] else np.array([0, 0, 1.0])
        antes = geo.volumen(cuerpo.forma)
        cuerpo.forma = _sc().labio_ranura(cuerpo.forma, aristas, -d if self.p["invertir"] else d, tipo=self.p["tipo"],
                                          ancho=ctx.evaluar(self.p["ancho"]), alto=ctx.evaluar(self.p["alto"]),
                                          holgura=ctx.evaluar(self.p["holgura"]))
        dv = geo.volumen(cuerpo.forma) - antes
        if abs(dv) <= max(antes, 1.0) * 1e-9:   # un labio que quedó entero dentro no avisa solo (B-62)
            ctx.aviso(f"{cuerpo.nombre}: el {self.p['tipo']} no cambió el volumen "
                      "(¿la dirección o el lado lo dejaron dentro de la pared? Probá «Invertir»).")
        self._registrar_usados([cuerpo.id])


registrar_operacion(OpBarrido, OpSolevacion, OpNervio, OpRed, OpRepujado, OpAgujero, OpRosca, OpBobina, OpTuberia,
                    OpPatron, OpSimetria, OpRellenoContorno, OpSolidoEnvolvente, OpVolumenFluido, OpReglaPlastico, OpSaliente, OpLabio)
registrar_operacion(OpMultitransformar, OpPatronGeometrico, OpReticulaVolumetrica)
