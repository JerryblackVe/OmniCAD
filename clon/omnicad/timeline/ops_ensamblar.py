# -*- coding: utf-8 -*-
"""
ENSAMBLAR de Fusion [Fusion-Assemble]: componentes, uniones (las 7 de Fusion), uniones «como está»,
orígenes de unión, grupos rígidos, vínculos de movimiento e insertar otro diseño como componente.

Modelo: cada cuerpo pertenece a un componente (`Cuerpo.componente`, "" = la raíz). Una unión calcula un
marco (origen + ejes) sobre la geometría del componente 1 y otro sobre la del componente 2 y MUEVE los
cuerpos del componente 1 para que los marcos coincidan (caras enfrentadas, como en Fusion; dos ejes, como
un perno en un agujero, en el mismo sentido; «Voltear» invierte eso), con ángulo y desfases. Después aplica el movimiento de la unión (giro,
deslizamiento…) según sus valores, que se cambian con «Accionar uniones». Cada unión deja en
`estado.uniones` lo necesario para accionarla o animarla sin recalcular.
"""
import math
import re

import numpy as np

from ..nucleo import geometria as geo
from ..nucleo import referencias as refs
from . import entidades as ent
from .operaciones import ANGULO, ErrorOperacion, Operacion, _deps_objetivo, _resolver, registrar_operacion

TIPOS_UNION = {"rigida": "Rígida", "revolucion": "Revolución", "deslizante": "Deslizante", "cilindrica": "Cilíndrica",
               "pasador_ranura": "Pasador-ranura", "planar": "Planar", "bola": "Bola"}
# grados de libertad: (giros, desplazamientos) por tipo
MOVIMIENTOS = {"rigida": ([], []), "revolucion": (["giro"], []), "deslizante": ([], ["desliz"]),
               "cilindrica": (["giro"], ["desliz"]), "pasador_ranura": (["giro"], ["desliz"]),
               "planar": (["giro"], ["desliz", "desliz2"]), "bola": (["giro", "giro2", "giro3"], [])}
EJES = {"X": 0, "Y": 1, "Z": 2}
PUNTOS_CLAVE = ("centro", "inicio", "fin")      # punto de ajuste («Snap») del origen de unión, ver `_marco`


# ---------------------------------------------------------------- marcos (orígenes de unión)
def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise ErrorOperacion("Dirección nula en el origen de la unión.")
    return v / n


def marco_desde(origen, z, x=None):
    """Matriz 4x4 (columnas: X, Y, Z, origen) de un marco ortonormal derecho."""
    z = _unit(z)
    if x is None or abs(float(np.dot(_unit(x), z))) > 0.999:
        x = np.cross((0, 0, 1.0), z) if abs(z[2]) < 0.9 else np.cross(z, (0, 1.0, 0))
        x = np.cross(z, np.cross(x, z))
    x = _unit(np.asarray(x, float) - z * float(np.dot(x, z)))
    y = np.cross(z, x)
    m = np.identity(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, y, z, np.asarray(origen, float)
    return m


def marco_de(e, punto_clave="centro", version=1):
    """Origen de unión «simple» sobre una entidad resuelta (como el «Snap» del diálogo Unión).
    `version` es la «version_marco» de la unión: 1 = el marco de las recetas viejas (se conserva para que
    abran igual), 2 = el de ahora (ver `_marco`)."""
    return _marco(e, punto_clave, version)[0]


def _eje_canonico(d):
    """El eje con su componente mayor positiva (empates: Z, luego Y, luego X): no depende de si la cara es
    un agujero o un saliente ni de cómo se construyó."""
    d = _unit(d)
    i = max(range(3), key=lambda k: (round(abs(float(d[k])), 9), k))
    return d if d[i] > 0 else -d


def _x_del_mundo(z):
    """El eje del mundo menos alineado con `z` (empates: X, luego Y, luego Z): la X del marco de un eje."""
    i = min(range(3), key=lambda k: (round(abs(float(z[k])), 9), k))
    return np.identity(3)[i]


def _marco_de_eje(origen, d):
    z = _eje_canonico(d)
    return marco_desde(origen, z, _x_del_mundo(z))


def _marco(e, punto_clave="centro", version=1):
    """(marco, es_eje). Con versión 2: el origen de una cara plana es el centro de su contorno exterior (no
    el centroide de área, que se corre con los agujeros) y los marcos de eje (cara cilíndrica o cónica,
    arista circular) son deterministas: eje canónico, X del mundo y origen en el eje, en el centro de la
    arista circular o, en una cara, en el medio (o el inicio o el fin) de su largo, como el Snap de Fusion."""
    nuevo = (version or 1) >= 2
    if e.tipo == "plano" or (e.tipo == "boceto" and e.plano is not None):
        # Un «Origen de unión» puesto sobre un cilindro o una arista circular sigue siendo un marco de eje.
        eje = e.tipo == "plano" and bool(getattr(e.plano, "eje_de_union", False))
        return marco_desde(e.plano.origen, e.plano.normal, e.plano.u), eje
    if e.tipo == "cara":
        f = refs.firma_cara(e.forma)
        if e.plano is not None:
            if nuevo:
                return marco_desde(_centro_contorno_exterior(e.forma), e.plano.normal, e.plano.u), False
            centro = np.array(f["centro"])
            circ = _centro_circular(e.forma)
            return marco_desde(circ if circ is not None else centro, e.plano.normal, e.plano.u), False
        if "eje" in f:
            p, d = ent.como_eje(e)
            if nuevo:
                return _marco_de_eje(_punto_del_eje(e.forma, p, _eje_canonico(d), punto_clave), d), True
            c = np.array(f["centro"])
            pie = p + d * float((c - p) @ d)
            return marco_desde(pie, d), False
        return marco_desde(f["centro"], (0, 0, 1)), False
    if e.tipo in ("arista", "curva_boceto") and e.forma is not None:
        f = refs.firma_arista(e.forma)
        if f["geom"] == "circulo":
            from ..nucleo.consultas import eje_circulo
            eje = eje_circulo(e.forma)
            if nuevo:
                return _marco_de_eje(f["centro"], eje), True
            return marco_desde(f["centro"], eje), False
        return _marco_resto(e, f, punto_clave), False
    if nuevo and e.tipo == "eje":
        # Eje de construcción: marco de eje como el del cilindro del que suele salir.
        p, d = e.eje
        return _marco_de_eje(p, d), True
    return _marco_resto(e, None, punto_clave), False


def _punto_del_eje(cara, p, z, punto_clave):
    """Punto del eje (p, z) en el medio, el inicio o el fin del largo de la cara cilíndrica o cónica: los
    centros de sus aristas circulares extremas. El largo sale de los límites de la cara en el parámetro
    axial de la superficie."""
    from ..nucleo.consultas import punto_del_eje
    return punto_del_eje(cara, p, z, punto_clave)


def _marco_resto(e, f, punto_clave):
    """Aristas no circulares, ejes y puntos (igual en las dos versiones del marco)."""
    if f is not None:
        a, b = (np.array(p) for p in f["extremos"])
        p = {"inicio": a, "fin": b}.get(punto_clave, np.array(f["medio"]))
        if f["geom"] == "linea":
            return marco_desde(p, b - a)
        return marco_desde(p, e.plano.normal if e.plano is not None else (0, 0, 1))
    if e.tipo == "eje":
        p, d = e.eje
        return marco_desde(p, d)
    if e.punto is not None:
        return marco_desde(e.punto, e.plano.normal if e.plano is not None else (0, 0, 1))
    raise ErrorOperacion("No se puede poner un origen de unión en esa selección.")


def _centro_circular(cara):
    """Centro del contorno circular de una cara plana (agujero o disco), si lo tiene."""
    circulos = [refs.firma_arista(a) for a in refs.subformas(cara, "arista")]
    circulos = [c for c in circulos if c["geom"] == "circulo"]
    if len(circulos) == 1 or (circulos and all(np.allclose(c["centro"], circulos[0]["centro"]) for c in circulos)):
        return np.array(circulos[0]["centro"])
    return None


def _centro_contorno_exterior(cara):
    """Centro del contorno exterior de una cara plana, sin contar sus agujeros: el centro del círculo si el
    contorno es circular (disco, arandela) o radial partido (semicírculos concéntricos + radios: el agujero
    pasante partido en dos tapas) y, si no, el centroide de la región que encierra."""
    from ..nucleo.consultas import cara_del_contorno, contorno_exterior
    exterior = contorno_exterior(cara)
    if exterior is None:
        return np.array(refs.firma_cara(cara)["centro"])
    aristas = [refs.firma_arista(a) for a in refs.subformas(exterior, "arista")]
    circulos = [a for a in aristas if a["geom"] == "circulo"]
    if circulos and all(np.allclose(c["centro"], circulos[0]["centro"], atol=1e-6) for c in circulos):
        centro = np.array(circulos[0]["centro"], float)
        if len(circulos) == len(aristas):
            return centro
        radios = [c["radio"] for c in circulos]
        rmin, rmax = min(radios), max(radios)

        def _radial(h):  # línea con los extremos entre rmin y rmax y la dirección apuntando al centro
            a, b = (np.array(p, float) for p in h["extremos"])
            d = b - a
            medio = (a + b) / 2 - centro
            n_m = np.linalg.norm(medio)
            return (rmin - 1e-6 <= np.linalg.norm(a - centro) <= rmax + 1e-6 and
                    rmin - 1e-6 <= np.linalg.norm(b - centro) <= rmax + 1e-6 and
                    (n_m < 1e-9 or float(np.linalg.norm(np.cross(d, medio))) < 1e-6 * np.linalg.norm(d) * n_m))

        if all(_radial(a) for a in aristas if a["geom"] != "circulo"):
            return centro
    return np.array(refs.firma_cara(cara_del_contorno(exterior, cara))["centro"])


def _rot(eje, grados):
    a = math.radians(grados)
    c, s = math.cos(a), math.sin(a)
    m = np.identity(4)
    i, j = {0: (1, 2), 1: (2, 0), 2: (0, 1)}[eje]
    m[i, i], m[i, j], m[j, i], m[j, j] = c, -s, s, c
    return m


def _tras(v):
    m = np.identity(4)
    m[:3, 3] = v
    return m


def movimiento(tipo, valores, eje_giro="Z", eje_desliz="X"):
    """Transformación (en el marco de la unión) que produce el movimiento con esos valores."""
    g, d = MOVIMIENTOS[tipo]
    m = np.identity(4)
    if tipo in ("deslizante", "cilindrica"):
        m = _tras(np.identity(3)[EJES[eje_giro if tipo == "cilindrica" else eje_desliz]] * valores.get("desliz", 0.0))
    elif tipo == "pasador_ranura":
        m = _tras(np.identity(3)[EJES[eje_desliz]] * valores.get("desliz", 0.0))
    elif tipo == "planar":
        normal = EJES[eje_giro]
        a, b = [i for i in range(3) if i != normal]
        m = _tras(np.identity(3)[a] * valores.get("desliz", 0.0) + np.identity(3)[b] * valores.get("desliz2", 0.0))
    if "giro" in g:
        m = m @ _rot(EJES[eje_giro] if tipo != "bola" else 2, valores.get("giro", 0.0))
    if tipo == "bola":
        m = m @ _rot(1, valores.get("giro2", 0.0)) @ _rot(0, valores.get("giro3", 0.0))
    return m


# ---------------------------------------------------------------- operaciones
def _componente_de(estado, e):
    if e.cuerpo is None:
        return None
    return estado.cuerpo(e.cuerpo).componente or ""


def _mover_componentes(estado, comps, m):
    for c in estado.cuerpos.values():
        if (c.componente or "") in comps:
            if getattr(c, "tipo", "solido") == "malla":
                nueva = c.forma.copia()
                nueva.vertices = (np.c_[nueva.vertices, np.ones(len(nueva.vertices))] @ m.T)[:, :3]
                c.forma = nueva
            else:
                c.forma = geo.transformar(c.forma, m)
    for k in comps:
        if k in estado.componentes:
            actual = np.asarray(estado.componentes[k].get("matriz", np.identity(4).tolist()), float)
            estado.componentes[k]["matriz"] = (m @ actual).tolist()


def grupo_rigido(estado, comp):
    """El componente más todos los que caen en su grupo rígido, encadenando grupos que comparten componentes
    (A+B y B+C mueven A, B y C juntos)."""
    salida = {comp}
    creció = True
    while creció:
        creció = False
        for g in estado.grupos_rigidos:
            if salida & set(g) and not set(g) <= salida:
                salida |= set(g)
                creció = True
    return salida


class OpComponente(Operacion):
    """ENSAMBLAR › Nuevo componente [GUID-5966BF6B]: crea un componente y le pasa los cuerpos elegidos
    («Desde cuerpos»). `fijo` es «Fijar» (Ground): una unión no puede moverlo."""
    TIPO, ETIQUETA, ICONO = "componente", "Componente", "▣"
    PARAMS = {"cuerpos": [], "fijo": False}

    def dependencias(self):
        return _deps_objetivo(self.p["cuerpos"]) - {self.id}

    def ejecutar(self, estado, ctx):
        estado.componentes[self.id] = {"nombre": self.nombre, "padre": "", "fijo": bool(self.p["fijo"]),
                                       "matriz": np.identity(4).tolist()}
        for cid in self.p["cuerpos"]:
            estado.cuerpo(cid).componente = self.id


def _migrador(clave):
    """`migrar_receta` de una operación cuyo cálculo cambió: las recetas viejas (sin `clave`) reciben
    `clave` = 1 y conservan el cálculo de antes, así un ensamblaje compensado a mano (ángulo 180°, Voltear,
    dz) abre igual. Las operaciones nuevas toman el valor de PARAMS (2)."""
    def migrar(d):
        params = d.get("params", {})
        if isinstance(params, dict) and clave not in params:
            d = dict(d, params=dict(params, **{clave: 1}))
        return d
    return staticmethod(migrar)


def _version_de(p, clave):
    """La versión de cálculo guardada en `clave` (1 o 2). Otro valor (texto, lista, None, 3…) es un error que
    nombra el campo."""
    v = p.get(clave)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v not in (1, 2):
        raise ErrorOperacion(f"Parámetro mal formado «{clave}»: llegó {v!r}; tiene que ser 1 (el cálculo de las "
                             "recetas viejas) o 2 (el actual).")
    return int(v)


def _matriz_de(estado, comp):
    return np.asarray(estado.componentes.get(comp, {}).get("matriz", np.identity(4).tolist()), float)


def _camino_lazo(estado, comp1, comp2):
    """Camino previo entre los componentes; raíz y componentes fijos son tierra."""
    if not any(comp1 == u["comp1"] or comp1 in u["componentes"] for u in estado.uniones.values()):
        return []

    def nodo(comp):
        return "" if not comp or estado.componentes.get(comp, {}).get("fijo") else comp

    grafo = {}
    for uid, u in estado.uniones.items():
        a, b = nodo(u["comp1"]), nodo(u["comp2"])
        grafo.setdefault(a, []).append((b, uid))
        grafo.setdefault(b, []).append((a, uid))
    pendientes = [(nodo(comp2), [])]
    vistos = {nodo(comp2)}
    for actual, camino in pendientes:
        if actual == nodo(comp1):
            return camino
        for vecino, uid in grafo.get(actual, []):
            if vecino not in vistos:
                vistos.add(vecino)
                pendientes.append((vecino, camino + [uid]))
    return []


def _marco_local(estado, comp, marco, canonico):
    return {"local": (np.linalg.inv(_matriz_de(estado, comp)) @ marco).tolist(), "canonico": canonico}


def _marco_en_pose(datos, matriz):
    marco = matriz @ np.asarray(datos["local"], float)
    return _marco_de_eje(marco[:3, 3], marco[:3, 2]) if datos["canonico"] else marco


def _resolver_lazo(estado, ctx, cierre, camino):
    """Resuelve en matrices, sin transformar OCC durante las iteraciones."""
    from scipy.optimize import least_squares
    from scipy.spatial.transform import Rotation

    uniones = [(uid, u) for uid, u in estado.uniones.items() if uid in camino] + [(None, cierre)]
    if any(not u.get("reaplicar") or u.get("cierra_lazo") for _, u in uniones):
        ctx.aviso(f"Lazo cerrado no resuelto: «{cierre['nombre']}» incluye una unión como está sobre una pieza "
                  "ya movida o un lazo previo que no se puede re-aplicar como cadena.")
        return False
    accionada = max(range(len(uniones)), key=lambda i: uniones[i][1]["accionada"])
    if not uniones[accionada][1]["accionada"] or not any(MOVIMIENTOS[uniones[accionada][1]["tipo"]]):
        accionada = 0
    variables = [(i, k) for i, (_, u) in enumerate(uniones) if i != accionada
                 for k in sum(MOVIMIENTOS[u["tipo"]], [])]
    inicial = np.array([uniones[i][1]["valores"][k] for i, k in variables], float)
    poses = {k: _matriz_de(estado, k) for k in estado.componentes}
    poses[""] = np.identity(4)
    escala = max(1.0, *(np.linalg.norm(np.asarray(u["reaplicar"][lado]["local"])[:3, 3])
                        for _, u in uniones for lado in ("marco1", "marco2")))
    factores = np.array([180.0 if k.startswith("giro") else escala for _, k in variables])

    def probar(x):
        valores = [dict(u["valores"]) for _, u in uniones]
        for (i, k), v in zip(variables, x, strict=True):
            valores[i][k] = float(v)
        nuevas = dict(poses)
        for i, (_, u) in enumerate(uniones[:-1]):
            datos = u["reaplicar"]
            base = np.asarray(datos["bases"][u["comp1"]], float)
            f1 = _marco_en_pose(datos["marco1"], base)
            f2 = _marco_en_pose(datos["marco2"], nuevas[u["comp2"]])
            delta = (f2 @ movimiento(u["tipo"], valores[i], u["eje_giro"], u["eje_desliz"])
                     @ np.asarray(datos["alinear"]) @ np.linalg.inv(f1))
            for comp, matriz in datos["bases"].items():
                nuevas[comp] = delta @ np.asarray(matriz)
        datos = cierre["reaplicar"]
        f1 = _marco_en_pose(datos["marco1"], nuevas[cierre["comp1"]])
        f2 = _marco_en_pose(datos["marco2"], nuevas[cierre["comp2"]])
        objetivo = (f2 @ movimiento(cierre["tipo"], valores[-1], cierre["eje_giro"], cierre["eje_desliz"])
                    @ np.asarray(datos["alinear"]))
        error = np.r_[f1[:3, 3] - objetivo[:3, 3],
                      Rotation.from_matrix(objetivo[:3, :3].T @ f1[:3, :3]).as_rotvec() * escala]
        return error, nuevas, valores

    def residual(x):
        return probar(x)[0]

    def distancia(x):
        diferencia = x - inicial
        for j, (_, k) in enumerate(variables):
            if k.startswith("giro"):
                diferencia[j] = (diferencia[j] + 180) % 360 - 180
        return np.linalg.norm(diferencia)

    solucion = None
    # shortcut: pocas semillas angulares, no búsqueda global de todas las ramas de un mecanismo espacial.
    for giro in (0, 90, -90, 180):
        semilla = inicial.copy()
        for j, (_, k) in enumerate(variables):
            if k.startswith("giro"):
                semilla[j] += giro
        if variables:
            resultado = least_squares(residual, semilla, x_scale=factores, max_nfev=160,
                                      xtol=1e-14, ftol=1e-14, gtol=1e-14)
            candidato = resultado.x if resultado.success else None
        else:
            candidato = semilla
        if candidato is not None and np.linalg.norm(residual(candidato)) < 1e-7:
            if solucion is None or distancia(candidato) < distancia(solucion):
                solucion = candidato
            if distancia(solucion) < 1e-10:
                break
    mensaje = (f"Lazo cerrado sin solución: la unión «{cierre['nombre']}» cierra el lazo pero la geometría "
               "no alcanza la posición pedida (por ejemplo, una biela más corta que la manivela).")
    if solucion is None:
        raise ErrorOperacion(mensaje)
    for j, (_, k) in enumerate(variables):
        if k.startswith("giro"):
            solucion[j] = inicial[j] + (solucion[j] - inicial[j] + 180) % 360 - 180
    _, nuevas, valores = probar(solucion)
    movidos = {comp for _, u in uniones[:-1] for comp in u["componentes"]}
    # Las ramas colgadas conservan su pose relativa al padre, incluso fuera del camino del lazo.
    pendientes = set(movidos)
    while pendientes:
        padre = pendientes.pop()
        delta = nuevas[padre] @ np.linalg.inv(poses[padre])
        for uid, u in estado.uniones.items():
            if uid not in camino and u["comp2"] == padre:
                for comp in u["componentes"]:
                    if comp not in movidos and comp and not estado.componentes[comp].get("fijo"):
                        nuevas[comp] = delta @ poses[comp]
                        movidos.add(comp)
                        pendientes.add(comp)
    for comp in movidos:
        _mover_componentes(estado, {comp}, nuevas[comp] @ np.linalg.inv(poses[comp]))
    # Verificación independiente con la geometría real, no solo con los marcos guardados.
    datos = cierre["reaplicar"]
    if datos.get("como_esta"):
        f1 = _marco_en_pose(datos["marco1"], _matriz_de(estado, cierre["comp1"]))
        f2 = _marco_en_pose(datos["marco2"], _matriz_de(estado, cierre["comp2"]))
    else:
        f1 = _marco(_resolver(datos["origen1"], estado), datos["clave1"], datos["version"])[0]
        f2 = _marco(_resolver(datos["origen2"], estado), datos["clave2"], datos["version"])[0]
    objetivo = (f2 @ movimiento(cierre["tipo"], valores[-1], cierre["eje_giro"], cierre["eje_desliz"])
                @ np.asarray(datos["alinear"]))
    if (np.linalg.norm(f1[:3, 3] - objetivo[:3, 3]) >= 1e-6 or
            np.linalg.norm(Rotation.from_matrix(objetivo[:3, :3].T @ f1[:3, :3]).as_rotvec()) >= 1e-6):
        raise ErrorOperacion(mensaje)
    for i, (uid, u) in enumerate(uniones):
        datos = u["reaplicar"]
        marco = _marco_en_pose(datos["marco2"], nuevas[u["comp2"]])
        actualizado = dict(u, valores=valores[i], marco=marco.tolist())
        if uid is None:
            cierre.update(actualizado)  # cierre todavía no pertenece a ningún estado anterior
        else:
            estado.uniones[uid] = actualizado
        if i != accionada and any(MOVIMIENTOS[u["tipo"]]):
            clave = "giro" if MOVIMIENTOS[u["tipo"]][0] else "desliz"
            v = valores[i][clave]
            minimo, maximo = datos["limites"]
            if (minimo is not None and v < minimo) or (maximo is not None and v > maximo):
                ctx.aviso(f"La unión «{u['nombre']}» resuelta en el lazo ({v:g}) viola sus límites de movimiento.")
    return True


class OpUnion(Operacion):
    """ENSAMBLAR › Unión [ASM-CREATE-JOINT] y Unión como está [ASM-CREATE-AS-BUILT-JOINT].

    `version_marco` (2 en las uniones nuevas; 1 en las recetas viejas, ver `_migrador`): con 2
    el marco es el de `_marco` y dos marcos de eje (perno en agujero, rueda en eje, también a través de un
    «Origen de unión» puesto sobre ellos) quedan con los ejes en el mismo sentido; «Voltear» los opone. La unión «como está» con `origen2` (un cuerpo del componente 2)
    liga el componente 1 al 2: conserva la posición modelada respecto de él y lo sigue cuando se mueve.
    Al cerrar un lazo, la última unión accionada conserva su movimiento (por defecto, la primera del timeline);
    se resuelven numéricamente los giros y deslizamientos de las demás. Los lazos superpuestos y las uniones
    como está sobre piezas ya movidas conservan el comportamiento secuencial con un aviso."""
    TIPO, ETIQUETA, ICONO = "union", "Unión", "⚙"
    PARAMS = {"tipo": "rigida", "origen1": None, "origen2": None, "clave1": "centro", "clave2": "centro",
              "angulo": "0 deg", "dx": "0 mm", "dy": "0 mm", "dz": "0 mm", "voltear": False, "como_esta": False,
              "eje_giro": "Z", "eje_desliz": "X", "giro": "0 deg", "giro2": "0 deg", "giro3": "0 deg",
              "desliz": "0 mm", "desliz2": "0 mm", "minimo": "", "maximo": "", "version_marco": 2, "accionada": 0}
    EXPRESIONES = ("angulo", "dx", "dy", "dz", "giro", "giro2", "giro3", "desliz", "desliz2")
    OPCIONES = {"tipo": TIPOS_UNION, "clave1": PUNTOS_CLAVE, "clave2": PUNTOS_CLAVE, "eje_giro": EJES,
                "eje_desliz": EJES}
    migrar_receta = _migrador("version_marco")

    def dependencias(self):
        return (super().dependencias() | ent.dependencias_de(self.p["origen1"], self.p["origen2"])) - {self.id}

    def valores(self, ctx, aviso=None):
        """Valores del movimiento. Los límites (Joint Motion Limits) recortan el movimiento principal; con
        `aviso` se avisa cuando lo hacen."""
        g = {k: ctx.evaluar(self.p[k], ANGULO) for k in ("giro", "giro2", "giro3")}
        g.update({k: ctx.evaluar(self.p[k]) for k in ("desliz", "desliz2")})
        gira = bool(MOVIMIENTOS[self.p["tipo"]][0])
        clave, tipo = ("giro", ANGULO) if gira else ("desliz", "longitud")
        que, unidad = ("El giro pedido", "°") if gira else ("La distancia pedida", " mm")
        for lim, cual, recorta in (("minimo", "es menor que el límite mínimo", max),
                                   ("maximo", "supera el límite máximo", min)):
            if not str(self.p.get(lim) or "").strip():
                continue
            valor = ctx.evaluar(self.p[lim], tipo)
            if recorta(g[clave], valor) != g[clave]:
                if aviso is not None:
                    aviso(f"{que} ({g[clave]:g}{unidad}) {cual} ({valor:g}{unidad}): la unión quedó en "
                          f"{valor:g}{unidad}.")
                g[clave] = valor
        return g

    def ejecutar(self, estado, ctx):
        p = self.p
        self._usados = set()
        version = _version_de(p, "version_marco")
        accionada = self.entero("accionada", minimo=0)
        if not p["origen1"]:
            raise ErrorOperacion("Elegí el origen de la unión en el componente 1.")
        e1 = _resolver(p["origen1"], estado)
        comp1 = _componente_de(estado, e1)
        if not comp1:
            raise ErrorOperacion("El componente 1 tiene que ser un componente (no la raíz): creá uno con "
                                 "ENSAMBLAR › Nuevo componente.")
        if estado.componentes.get(comp1, {}).get("fijo"):
            raise ErrorOperacion("El componente 1 está fijo: no se puede mover con una unión.")
        F1, eje1 = _marco(e1, p["clave1"], version)
        valores = self.valores(ctx, ctx.aviso)
        mov = movimiento(p["tipo"], valores, p["eje_giro"], p["eje_desliz"])
        reaplicar = None
        comps = grupo_rigido(estado, comp1)
        fijos = [c for c in comps if estado.componentes.get(c, {}).get("fijo")]
        if fijos:
            nombre = estado.componentes[fijos[0]].get("nombre") or fijos[0]
            raise ErrorOperacion(f"El componente 1 está en un grupo rígido con «{nombre}», que está fijo: no se "
                                 "puede mover con una unión.")
        tipo_limite = ANGULO if MOVIMIENTOS[p["tipo"]][0] else "longitud"
        if p["como_esta"]:
            comp2, seguir = "", np.identity(4)
            if p["origen2"]:
                comp2 = _componente_de(estado, _resolver(p["origen2"], estado)) or ""
                if comp2 == comp1:
                    raise ErrorOperacion("Los dos orígenes están en el mismo componente.")
            camino = _camino_lazo(estado, comp1, comp2)
            ya_movida = not np.allclose(_matriz_de(estado, comp1), np.identity(4), atol=1e-9)
            if comp2 and ya_movida and not camino:
                # Otra unión anterior ya movió el componente 1: se queda donde está (no se pisa ese movimiento).
                ctx.aviso("Otra unión ya mueve el componente 1: la unión como está lo deja donde está. Para que "
                          "siga al componente 2, elegí como componente 1 la pieza que no tiene otra unión.")
            elif comp2 and not ya_movida:
                # Posición modelada respecto del componente 2: lo que él se movió, el 1 también.
                seguir = _matriz_de(estado, comp2) @ np.linalg.inv(_matriz_de(estado, comp1))
            F2 = seguir @ F1
            m = F2 @ mov @ np.linalg.inv(F2) @ seguir
            if not (comp2 and ya_movida) or camino:
                marco = _marco_local(estado, comp1, F1, False)
                if version >= 2 and eje1 and e1.tipo != "plano":
                    local = np.asarray(marco["local"], float)
                    marco["local"] = _marco_de_eje(local[:3, 3], local[:3, 2]).tolist()
                # El marco modelado es compartido y rígido: el movimiento es relativo al componente 2.
                reaplicar = {"marco1": marco, "marco2": marco, "alinear": np.identity(4).tolist(),
                             "como_esta": True}
        else:
            if not p["origen2"]:
                raise ErrorOperacion("Elegí el origen de la unión en el componente 2.")
            e2 = _resolver(p["origen2"], estado)
            comp2 = _componente_de(estado, e2) or ""
            if comp2 == comp1:
                raise ErrorOperacion("Los dos orígenes están en el mismo componente.")
            F2, eje2 = _marco(e2, p["clave2"], version)
            opuestos = not (version >= 2 and eje1 and eje2)       # caras enfrentadas; dos ejes: mismo sentido
            enfrentar = _rot(0, 180.0) if opuestos != bool(p["voltear"]) else np.identity(4)
            desfase = _tras([ctx.evaluar(p[k]) for k in ("dx", "dy", "dz")])
            alinear = desfase @ _rot(2, ctx.evaluar(p["angulo"], ANGULO)) @ enfrentar
            m0 = F2 @ alinear @ np.linalg.inv(F1)
            z1 = F1[:3, 2]
            if version >= 2 and not p["voltear"] and float((m0[:3, :3] @ z1) @ z1) < -0.99:
                ctx.aviso("La unión dejó el componente 1 dado vuelta respecto de cómo está modelado; si no es lo "
                          "que querías, marcá «Voltear».")
            m = F2 @ mov @ alinear @ np.linalg.inv(F1)
            reaplicar = {"marco1": _marco_local(estado, comp1, F1, version >= 2 and eje1 and e1.tipo != "plano"),
                         "marco2": _marco_local(estado, comp2, F2, version >= 2 and eje2 and e2.tipo != "plano"),
                         "alinear": alinear.tolist()}
        # ASM-3: cuenta el componente resuelto aquí, también en cuerpos divididos, copiados o reasignados.
        self._usados = (comps | {comp2}) - {"", self.id}
        if reaplicar is not None:
            reaplicar.update(bases={c: _matriz_de(estado, c).tolist() for c in comps},
                             origen1=p["origen1"], origen2=p["origen2"], clave1=p["clave1"], clave2=p["clave2"],
                             version=version,
                             limites=[ctx.evaluar(p[k], tipo_limite) if str(p.get(k) or "").strip() else None
                                      for k in ("minimo", "maximo")])
        union = {"nombre": self.nombre, "tipo": p["tipo"], "comp1": comp1, "comp2": comp2,
                 "componentes": sorted(comps), "marco": F2.tolist(), "eje_giro": p["eje_giro"],
                 "eje_desliz": p["eje_desliz"], "valores": valores, "reaplicar": reaplicar, "accionada": accionada}
        camino = _camino_lazo(estado, comp1, comp2)
        if camino:
            if _resolver_lazo(estado, ctx, union, camino):
                estado.uniones[self.id] = dict(union, cierra_lazo=True)
                return
        _mover_componentes(estado, comps, m)
        estado.uniones[self.id] = union


def siguiente_accion(operaciones):
    """Prioridad de la próxima unión accionada en el documento; conserva el orden entre recálculos."""
    return 1 + max((o.entero("accionada", minimo=0) for o in operaciones if isinstance(o, OpUnion)), default=0)


class OpOrigenUnion(Operacion):
    """ENSAMBLAR › Origen de la unión [ASM-CREATE-JOINT-ORIGIN]: un marco guardado que después sirve para
    unir. Se guarda como plano de construcción (su plano XY) con el ángulo pedido. `version_marco` como en
    `OpUnion`."""
    TIPO, ETIQUETA, ICONO = "origen_union", "Origen de unión", "⌖"
    PARAMS = {"origen": None, "clave": "centro", "angulo": "0 deg", "dx": "0 mm", "dy": "0 mm", "dz": "0 mm",
              "version_marco": 2}
    EXPRESIONES = ("angulo", "dx", "dy", "dz")
    OPCIONES = {"clave": PUNTOS_CLAVE}
    migrar_receta = _migrador("version_marco")

    def dependencias(self):
        return ent.dependencias_de(self.p["origen"]) - {self.id}

    def ejecutar(self, estado, ctx):
        version = _version_de(self.p, "version_marco")
        if not self.p["origen"]:
            raise ErrorOperacion("Elegí dónde va el origen.")
        F, eje = _marco(_resolver(self.p["origen"], estado), self.p["clave"], version)
        F = F @ _tras([ctx.evaluar(self.p[k]) for k in ("dx", "dy", "dz")]) @ _rot(2, ctx.evaluar(self.p["angulo"], ANGULO))
        plano = geo.Plano.desde_marco(F[:3, 3], F[:3, 2], F[:3, 0], self.nombre)
        plano.eje_de_union = eje        # una unión lo trata como el cilindro o la arista de donde salió
        estado.planos[self.id] = plano


def componente_por_ref(estado, ref):
    """Componente que nombra `ref`: su id (el del paso que lo creó, p. ej. "op5"), su nombre sin importar
    mayúsculas o el id de uno de sus cuerpos ("op2.c1"). None si no hay ninguno."""
    if not isinstance(ref, str) or not ref.strip():
        return None
    if ref in estado.componentes:
        return ref
    nombre = ref.strip().casefold()
    hallados = [k for k, c in estado.componentes.items() if str(c.get("nombre") or "").casefold() == nombre]
    if len(hallados) > 1:
        raise ErrorOperacion(f"Hay varios componentes llamados «{ref}»: usá el id.")
    if hallados:
        return hallados[0]
    cuerpo = estado.cuerpos.get(ref)
    return cuerpo.componente if cuerpo is not None and cuerpo.componente else None


class OpGrupoRigido(Operacion):
    """ENSAMBLAR › Grupo rígido [ASM-CREATE-RIGID-GROUP]: los componentes se mueven juntos. Cada componente
    se nombra por id, por nombre o por el id de uno de sus cuerpos (`componente_por_ref`)."""
    TIPO, ETIQUETA, ICONO = "grupo_rigido", "Grupo rígido", "⛓"
    PARAMS = {"componentes": []}

    def dependencias(self):
        lista = self.p["componentes"] if isinstance(self.p["componentes"], (list, tuple)) else []
        ids = {c.split(".")[0] for c in lista if isinstance(c, str) and re.fullmatch(r"op\d+(\..*)?", c)}
        return (super().dependencias() | ids) - {self.id}

    def ejecutar(self, estado, ctx):
        if not estado.componentes:
            raise ErrorOperacion("Todavía no hay componentes en este punto del timeline: creá uno con "
                                 "ENSAMBLAR › Nuevo componente.")
        ids, faltan = [], []
        for ref in self.p["componentes"]:
            comp = componente_por_ref(estado, ref)
            if comp is None:
                faltan.append(ref)
            elif comp not in ids:
                ids.append(comp)
        self._usados = set(ids) - {self.id}
        if faltan or len(ids) < 2:
            no_hay = f" No encontré: {', '.join(f'«{r}»' for r in faltan)}." if faltan else ""
            hay = ", ".join(f"{c.get('nombre') or k} ({k})" for k, c in estado.componentes.items())
            raise ErrorOperacion(f"Elegí al menos dos componentes existentes.{no_hay} Componentes disponibles: {hay}.")
        estado.grupos_rigidos = estado.grupos_rigidos + [ids]


class OpVinculoMovimiento(Operacion):
    """ENSAMBLAR › Vínculo de movimiento [GUID-074622A9]: la unión 2 se mueve en proporción a la 1.

    El valor vinculado REEMPLAZA al de la unión 2 (`version_vinculo` 2). Las recetas viejas (1) lo sumaban
    sobre la posición ya calculada de la unión 2 y abren igual que antes."""
    TIPO, ETIQUETA, ICONO = "vinculo_movimiento", "Vínculo de movimiento", "⇄"
    PARAMS = {"union1": "", "union2": "", "factor": "1", "invertir": False, "version_vinculo": 2}
    EXPRESIONES = ("factor",)
    migrar_receta = _migrador("version_vinculo")

    def dependencias(self):
        return {self.p["union1"], self.p["union2"]} - {"", self.id}

    def ejecutar(self, estado, ctx):
        version = _version_de(self.p, "version_vinculo")
        u1, u2 = estado.uniones.get(self.p["union1"]), estado.uniones.get(self.p["union2"])
        if not u1 or not u2:
            raise ErrorOperacion("Las dos uniones tienen que existir antes del vínculo.")
        clave1 = "giro" if MOVIMIENTOS[u1["tipo"]][0] else "desliz"
        clave2 = "giro" if MOVIMIENTOS[u2["tipo"]][0] else "desliz"
        if self.p["union2"] in estado.vinculos:
            otro = estado.uniones.get(estado.vinculos[self.p["union2"]], {})
            raise ErrorOperacion(f"La unión «{u2['nombre']}» ya la mueve el vínculo «{otro.get('nombre', 'otro')}»: "
                                 "una unión solo puede seguir a un vínculo.")
        actual, vistos = self.p["union1"], set()
        while actual in estado.vinculos and actual not in vistos:
            vistos.add(actual)
            actual = estado.vinculos[actual]
            if actual == self.p["union2"]:
                raise ErrorOperacion(f"El vínculo «{u1['nombre']}» → «{u2['nombre']}» armaría un círculo: "
                                     f"«{u2['nombre']}» ya mueve a «{u1['nombre']}».")
        factor = ctx.evaluar(self.p["factor"], "escalar") * (-1 if self.p["invertir"] else 1)
        if not math.isfinite(factor) or factor == 0:
            raise ErrorOperacion("La relación del vínculo no puede ser cero: la unión 2 no se movería.")
        estado.vinculos[self.p["union2"]] = self.p["union1"]
        F2 = np.asarray(u2["marco"], float)
        if version < 2:
            extra = dict.fromkeys(MOVIMIENTOS[u2["tipo"]][0] + MOVIMIENTOS[u2["tipo"]][1], 0.0)
            extra[clave2] = u1["valores"][clave1] * factor
            m = F2 @ movimiento(u2["tipo"], extra, u2["eje_giro"], u2["eje_desliz"]) @ np.linalg.inv(F2)
            _mover_componentes(estado, set(u2["componentes"]), m)
            return
        # Se deshace el movimiento propio de la unión 2 y se aplica el vinculado (exacto también en planar y
        # pasador-ranura, donde giro y desplazamiento no conmutan).
        viejos = u2["valores"]
        nuevos = dict(viejos, **{clave2: u1["valores"][clave1] * factor})
        m = (F2 @ movimiento(u2["tipo"], nuevos, u2["eje_giro"], u2["eje_desliz"])
             @ np.linalg.inv(movimiento(u2["tipo"], viejos, u2["eje_giro"], u2["eje_desliz"])) @ np.linalg.inv(F2))
        _mover_componentes(estado, set(u2["componentes"]), m)
        estado.uniones[self.p["union2"]] = dict(u2, valores=nuevos)   # dict nuevo: la copia del estado es superficial


class OpInsertarDiseno(Operacion):
    """INSERTAR › Insertar componente / derivación [ASM-INSERT-FUSION-DESIGN]: los cuerpos finales de otro
    diseño (.omnicad) entran como un componente nuevo. La receta se guarda adentro (copia independiente). `fijo`
    como en `OpComponente` (Fijar)."""
    TIPO, ETIQUETA, ICONO = "insertar_diseno", "Insertar diseño", "⇩"
    PARAMS = {"archivo": "", "receta": None, "fijo": False}

    def ejecutar(self, estado, ctx):
        from .documento import Documento
        if not self.p["receta"]:
            raise ErrorOperacion("La inserción no tiene el diseño.")
        otro = Documento.desde_dict(self.p["receta"])
        estado.componentes[self.id] = {"nombre": self.p["archivo"] or self.nombre, "padre": "",
                                       "fijo": bool(self.p.get("fijo")), "matriz": np.identity(4).tolist()}
        for c in otro.estado_final.cuerpos.values():
            estado.nuevo_cuerpo(self.id, c.forma, c.tipo, nombre=c.nombre, apariencia=c.apariencia,
                                material=c.material, componente=self.id)


registrar_operacion(OpComponente, OpUnion, OpOrigenUnion, OpGrupoRigido, OpVinculoMovimiento, OpInsertarDiseno)
