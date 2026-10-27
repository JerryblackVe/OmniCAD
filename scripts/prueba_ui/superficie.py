# -*- coding: utf-8 -*-
"""Fase B · SUPERFICIE: cada comando en la ventana real, con selección por el visor."""
import math
import sys

import arnes as A
import corredor as C
import escena

s, ids = escena.construir()
app, v = A.iniciar(s.doc)
AR = "SUPERFICIE"
pi = math.pi
tubo, caja, cil, quilt, tapa = ids["tubo"], ids["caja"], ids["cil"], ids["quilt"], ids["tapa"]


def cur(nombre, i=0):
    return lambda: [A.hit_curva(v, s, nombre, i)]


def run(nombre, f):
    A.correr(f"{AR} · {nombre}", f)


# 1 Extruir superficie ------------------------------------------------------------------------------------------
run("sup_extruir", lambda: (
    C.caso(v, AR, "sup_extruir", {"curvas": cur("Circ")}, {"distancia": "15 mm"}, esperado=2 * pi * 5 * 15, foto="sup_extruir"),
    C.caso(v, AR, "sup_extruir", {"curvas": cur("Circ")}, {"distancia": "15 mm", "simetrica": True}, esperado=2 * pi * 5 * 15,
           etiqueta="sup_extruir simétrica"),
    C.caso(v, AR, "sup_extruir", {"curvas": lambda: [A.hit_curva(v, s, "Rect", i) for i in range(4)]}, {"distancia": "10 mm"}, esperado=2 * (20 + 10) * 10,
           etiqueta="sup_extruir rectángulo (4 lados)"),
    C.caso(v, AR, "sup_extruir", {"curvas": cur("Lin")}, {"distancia": "10 mm"}, esperado=200, etiqueta="sup_extruir línea abierta"),
    C.caso(v, AR, "sup_extruir", {"curvas": cur("Circ")}, {"distancia": "15 mm", "conicidad": "5 deg"}, etiqueta="sup_extruir conicidad 5°", rt=False),
    C.negativos(v, AR, "sup_extruir", {"curvas": cur("Circ")}, "distancia")))

# 2 Revolución ---------------------------------------------------------------------------------------------------
eje = lambda i: (lambda: [A.hit_eje(v, i)])  # noqa: E731
run("sup_revolucion", lambda: (
    C.caso(v, AR, "sup_revolucion", {"curvas": cur("RevL"), "eje": eje("Z")}, {"angulo": "360 deg"}, esperado=2 * pi * 30 * 20, foto="sup_revolucion"),
    C.caso(v, AR, "sup_revolucion", {"curvas": cur("RevL"), "eje": eje("Z")}, {"angulo": "90 deg"}, esperado=2 * pi * 30 * 20 / 4,
           etiqueta="sup_revolucion 90°"),
    C.negativos(v, AR, "sup_revolucion", {"curvas": cur("RevL"), "eje": eje("Z")}, "angulo", malos=("abc", "0 deg", "-90 deg"))))

# 3 Barrido -------------------------------------------------------------------------------------------------------
run("sup_barrido", lambda: (
    C.caso(v, AR, "sup_barrido", {"perfil": cur("Perf"), "ruta": cur("Ruta")}, {}, esperado=2 * pi * 2 * 30, foto="sup_barrido"),
    C.caso(v, AR, "sup_barrido", {"perfil": cur("Perf"), "ruta": cur("Ruta")}, {"orientacion": "paralela"}, etiqueta="sup_barrido paralela"),
    C.caso(v, AR, "sup_barrido", {"perfil": cur("Perf"), "ruta": cur("Ruta")}, {"torsion": "90 deg"}, etiqueta="sup_barrido torsión 90°", rt=False),
    C.negativos(v, AR, "sup_barrido", {"perfil": cur("Perf"), "ruta": cur("Ruta")}, "torsion", malos=("abc", "720 deg"))))

# 4 Solevación -----------------------------------------------------------------------------------------------------
cone = pi * (5 + 8) * math.hypot(20, 3)
run("sup_solevacion", lambda: (
    C.caso(v, AR, "sup_solevacion", {"secciones": lambda: [A.hit_curva(v, s, "Circ"), A.hit_curva(v, s, "Circ2")]}, {}, esperado=cone, foto="sup_solevacion"),
    C.caso(v, AR, "sup_solevacion", {"secciones": lambda: [A.hit_curva(v, s, "Circ"), A.hit_curva(v, s, "Circ2")]}, {"reglada": True},
           etiqueta="sup_solevacion reglada", rt=False),
    C.negativos(v, AR, "sup_solevacion")))

# 5 Parche ----------------------------------------------------------------------------------------------------------
arc = lambda: [A.hit_arista(v, tubo, lineal=False)]  # noqa: E731
for g in ("G0", "G1", "G2"):
    run(f"parche {g}", lambda g=g: C.caso(v, AR, "parche", {"contorno": arc}, {"continuidad": g}, esperado=pi * 25 if g == "G0" else None,
                                          etiqueta=f"parche {g}", foto="parche" if g == "G0" else None, rt=(g == "G0")))
run("parche negativos", lambda: C.negativos(v, AR, "parche"))

# 6 Reglada -----------------------------------------------------------------------------------------------------------
for tipo in ("normal", "tangente"):
    run(f"reglada {tipo}", lambda tipo=tipo: C.caso(v, AR, "reglada", {"aristas": arc}, {"tipo": tipo, "distancia": "5 mm"},
                                                    etiqueta=f"reglada {tipo}", foto="reglada" if tipo == "normal" else None, rt=(tipo == "normal")))
run("reglada dirección", lambda: C.caso(v, AR, "reglada", {"aristas": arc, "direccion": eje("X")}, {"tipo": "direccion", "distancia": "5 mm"},
                                        etiqueta="reglada dirección X", rt=False))
run("reglada negativos", lambda: C.negativos(v, AR, "reglada", {"aristas": arc}, "distancia"))

# 7 Desfase de superficie ----------------------------------------------------------------------------------------------
cara_tubo = lambda: [A.hit_cara(v, tubo)]  # noqa: E731
run("sup_desfase", lambda: (
    C.caso(v, AR, "sup_desfase", {"caras": cara_tubo}, {"distancia": "3 mm"}, foto="sup_desfase"),
    C.caso(v, AR, "sup_desfase", {"caras": cara_tubo}, {"distancia": "-2 mm"}, etiqueta="sup_desfase -2", rt=False),
    C.negativos(v, AR, "sup_desfase", {"caras": cara_tubo}, "distancia", malos=("abc", "0 mm", "-100 mm"))))

# 8 Extender ----------------------------------------------------------------------------------------------------------
for tipo in ("natural", "tangente", "perpendicular"):
    run(f"extender {tipo}", lambda tipo=tipo: C.caso(v, AR, "extender_sup", {"aristas": arc}, {"tipo": tipo, "distancia": "5 mm"},
                                                     esperado=2 * pi * 5 * 25 if tipo == "natural" else None, etiqueta=f"extender {tipo}",
                                                     foto="extender_sup" if tipo == "natural" else None, rt=(tipo == "natural")))
run("extender negativos", lambda: C.negativos(v, AR, "extender_sup", {"aristas": arc}, "distancia", malos=("abc", "0 mm", "-3 mm")))

# 9 Engrosar ------------------------------------------------------------------------------------------------------------
run("engrosar", lambda: (
    C.caso(v, AR, "engrosar", {"caras": lambda: [A.hit_cuerpo(v, tubo)]}, {"espesor": "2 mm"}, esperado=pi * (6 ** 2 - 5 ** 2) * 20 if False else None,
           foto="engrosar"),
    C.caso(v, AR, "engrosar", {"caras": lambda: [A.hit_cuerpo(v, tubo)]}, {"espesor": "2 mm", "direccion": "simetrica"}, etiqueta="engrosar simétrico", rt=False),
    C.negativos(v, AR, "engrosar", {"caras": lambda: [A.hit_cuerpo(v, tubo)]}, "espesor", malos=("abc", "0 mm", "-2 mm"))))

# 10 Coser / Descoser / Invertir normal ---------------------------------------------------------------------------------
cos = lambda: [A.hit_cuerpo(v, quilt), A.hit_cuerpo(v, tapa)]  # noqa: E731
run("coser", lambda: (
    C.caso(v, AR, "coser", {"cuerpos": cos}, {}, esperado=20 * 20 * 10, foto="coser"),
    C.caso(v, AR, "coser", {"cuerpos": cos}, {"tolerancia": "0 mm"}, etiqueta="coser tolerancia 0", rt=False),
    C.caso(v, AR, "coser", {"cuerpos": cos}, {"tolerancia": "-1 mm"}, etiqueta="coser tolerancia -1", rt=False),
    C.negativos(v, AR, "coser", {"cuerpos": cos}, "tolerancia", malos=("abc",))))
run("descoser", lambda: (
    C.caso(v, AR, "descoser", {"cuerpos": lambda: [A.hit_cuerpo(v, caja)]}, {}, foto="descoser"),
    C.negativos(v, AR, "descoser")))
run("invertir_normal", lambda: (
    C.caso(v, AR, "invertir_normal", {"cuerpos": lambda: [A.hit_cuerpo(v, tubo)]}, {}, foto="invertir_normal"),
    C.negativos(v, AR, "invertir_normal")))

# 11 Empalme de superficie ------------------------------------------------------------------------------------------------
compartida = lambda: [A.hit_arista(v, quilt, lineal=True, cerca=(110, -10, 5))]  # noqa: E731  (vertical, entre dos caras)
libre = lambda: [A.hit_arista(v, quilt, lineal=True, cerca=(110, 0, 10))]  # noqa: E731  (borde de arriba, sin vecina)
run("sup_empalme arista compartida", lambda: C.caso(v, AR, "sup_empalme", {"aristas": compartida}, {"medida": "1 mm"}, foto="sup_empalme"))
run("sup_empalme chaflán", lambda: C.caso(v, AR, "sup_empalme", {"aristas": compartida}, {"tipo": "chaflan", "medida": "1 mm"}, etiqueta="sup_empalme chaflán", rt=False))
run("sup_empalme arista libre", lambda: C.caso(v, AR, "sup_empalme", {"aristas": libre}, {"medida": "1 mm"}, etiqueta="sup_empalme sobre arista LIBRE"))
run("sup_empalme negativos", lambda: C.negativos(v, AR, "sup_empalme", {"aristas": compartida}, "medida", malos=("abc", "0 mm", "-1 mm", "500 mm")))

# 12 Recortar / Destrimar (encadenados: recortar queda) -----------------------------------------------------------------------
res = {}


def sup24():
    """SUP-24: previsualizar y CANCELAR una Reglada tangente no daña la superficie de origen: Recortar sigue
    encontrando las dos regiones y quita la mitad (área 314,16)."""
    p = A.abrir(v, "reglada")
    A.elegir(p, "aristas", *arc())
    p.set_valor("tipo", "tangente")
    p.set_valor("distancia", "5 mm")
    p._t_previa.stop()
    p._calcular_previa()
    st = A.estado_panel(p)
    A.reg(AR, "SUP-24 · reglada tangente: vista previa", st["op"] and st["previa_ok"], st["mensaje"])
    p.cancelar()
    A.esperar(120)
    capturado = {}
    panel = A.abrir(v, "recortar_sup")
    A.elegir(panel, "herramienta", A.hit_plano(v, "PM"))
    A.elegir(panel, "region", *cara_tubo())
    panel.previa.connect(lambda estado: capturado.__setitem__("estado", estado))
    panel._t_previa.stop()
    panel._calcular_previa()
    st = A.estado_panel(panel)
    estado = capturado.get("estado")
    area = None if estado is None else A.geo.area(estado.cuerpos[tubo].forma)
    A.reg(AR, "SUP-24 · recortar tras la previa tangente",
          st["previa_ok"] and area is not None and abs(area - 2 * pi * 5 * 10) <= 0.01,
          f"previa_ok={st['previa_ok']} area={area} mensaje=«{st['mensaje']}»")
    panel.cancelar()
    A.esperar(100)


run("SUP-24 reglada tangente + recortar", sup24)


def recortar():
    r = C.caso(v, AR, "recortar_sup", {"herramienta": lambda: [A.hit_plano(v, "PM")], "region": cara_tubo}, {}, deshacer=False, foto="recortar_sup")
    res["rec"] = r


run("recortar_sup", recortar)
run("recortar_sup negativos", lambda: C.negativos(v, AR, "recortar_sup"))

def destrimar():
    A.reg(AR, "destrimar: el recorte previo existe", bool(res.get("rec")), str((res.get("rec") or {}).get("det") or (res.get("rec") or {}).get("mensaje")))
    objetivo = tubo
    C.caso(v, AR, "destrimar", {"caras": lambda: [A.hit_cara(v, objetivo)]}, {}, foto="destrimar", rt=True)
    C.caso(v, AR, "destrimar", {"caras": lambda: [A.hit_cara(v, objetivo)]}, {"contornos": "interiores"}, etiqueta="destrimar interiores", rt=False)


run("destrimar", destrimar)
run("destrimar negativos", lambda: C.negativos(v, AR, "destrimar"))

A.guardar_registro("u1_superficie")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
print("modales vistos:", A.MODALES[-10:])
v.close()
sys.exit(0)
