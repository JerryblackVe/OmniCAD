"""Boceto 2D: patrones."""
import math
import copy

import numpy as np

from .boceto_entidades import (
    Arco, ArcoElipse, Circulo, distancia_punto_recta, Elipse, ErrorBoceto, _invertir_curvatura, Linea,
    MAX_COPIAS_PATRON, MAX_PUNTOS_PATRON, MEDIDA_MINIMA, Restriccion, Spline, Texto,
)
from .boceto_geometria import _rot


def _matriz_de(f):
    """Matriz afín 3×3 de una transformación de copia `f` (giro o traslación del patrón)."""
    o = np.asarray(f((0.0, 0.0)), float)
    ex, ey = np.asarray(f((1.0, 0.0)), float) - o, np.asarray(f((0.0, 1.0)), float) - o
    return np.array([[ex[0], ey[0], o[0]], [ex[1], ey[1], o[1]], [0.0, 0.0, 1.0]])


class _Patrones:
    # ------------------------------------------------------------ CREAR: simetría y patrones
    def simetria(self, ids, eje):
        """Simetría (SKT-CREATE-MIRROR): copia espejada respecto de la línea `eje`, con restricciones
        de simetría entre los puntos (los que están sobre el eje se comparten). Devuelve las curvas nuevas.
        Lo que ya es su propio reflejo (una línea sobre el eje, un círculo centrado en él) no se copia: la copia
        quedaría encimada. El eje puede estar entre los `ids`: se ignora. BOC-40: como en Fusion («line or axis»), el
        eje puede ser uno del origen (`EJE_X` o `EJE_Y`): se materializa como línea de construcción fija."""
        self.asegurar_referencias([eje])
        if self.tipo_de(eje) != "linea":
            raise ErrorBoceto("La línea de simetría tiene que ser una línea.")
        from . import objetos
        obj = [i for i in ids if i in self.objetos]
        if set(obj) - set(objetos.raices(self)):
            raise ErrorBoceto("Simetría: elegí el objeto vectorial entero, no una parte.")
        de_objetos = set(objetos.curvas(self, obj))     # B-660: el objeto se refleja entero, no sus curvas ni puntos
        de_objetos |= set(self.puntos_de(de_objetos))
        ids = [i for i in ids if i != eje and i not in self.objetos and i not in de_objetos
               and not isinstance(self.curvas.get(i), Texto)]
        if not ids and not obj:
            raise ErrorBoceto("Seleccioná la geometría a reflejar.")
        a, b = self._extremos_linea(eje)
        if math.dist(a, b) < MEDIDA_MINIMA:
            raise ErrorBoceto("Línea de simetría: no puede tener largo 0.")

        def reflejo(q):
            dx, dy = b[0] - a[0], b[1] - a[1]
            t = ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / (dx * dx + dy * dy)
            fx, fy = a[0] + t * dx, a[1] + t * dy
            return 2 * fx - q[0], 2 * fy - q[1]

        def sobre(q):
            return abs(distancia_punto_recta(q, a, b)) < MEDIDA_MINIMA

        def encimada(i):
            """Su copia quedaría exactamente sobre ella."""
            c, P = self.curvas.get(i), self.coords
            if isinstance(c, Linea):
                return sobre(P(c.p1)) and sobre(P(c.p2))
            if isinstance(c, Circulo):
                return sobre(P(c.centro))
            if isinstance(c, Arco):          # centrado en el eje y con los extremos espejados entre sí
                return sobre(P(c.centro)) and math.dist(reflejo(P(c.inicio)), P(c.fin)) < MEDIDA_MINIMA
            if isinstance(c, (Elipse, ArcoElipse)):     # centrada en el eje y con su eje mayor paralelo o perpendicular a él
                (cx, cy), (mx, my) = P(c.centro), P(c.mayor)
                m, d = (mx - cx, my - cy), (b[0] - a[0], b[1] - a[1])
                alineada = min(abs(m[0] * d[1] - m[1] * d[0]), abs(m[0] * d[0] + m[1] * d[1]))
                return (sobre((cx, cy)) and alineada < 1e-9 * math.hypot(*m) * math.hypot(*d)
                        and (isinstance(c, Elipse) or math.dist(reflejo(P(c.inicio)), P(c.fin)) < MEDIDA_MINIMA))
            return False         # shortcut: una spline o una cónica que ya es simétrica se copia encima; si molesta, comparar la curva con su reflejo
        ids = [i for i in ids if not encimada(i)]
        if not ids and not obj:
            raise ErrorBoceto("Ya está sobre el eje: nada que reflejar.")
        mapa = {}
        for p in self.puntos_de(ids):
            q = self.coords(p)
            if sobre(q):
                mapa[p] = p
            else:
                mapa[p] = self.agregar_punto(*reflejo(q))
                self.agregar_restriccion("simetrica", [p, mapa[p], eje])
        nuevos = []
        for i in ids:
            if i not in self.curvas:
                continue
            c = self.curvas[i].remapear(mapa, self._nuevo_id())
            c.proyectada = False
            if isinstance(c, (Arco, ArcoElipse)):
                c.inicio, c.fin = c.fin, c.inicio
            elif isinstance(c, Spline):
                _invertir_curvatura(c)
            self.curvas[c.id] = c
            nuevos.append(c.id)
            if isinstance(c, (Circulo, Elipse, ArcoElipse)):
                self.agregar_restriccion("igual", [i, c.id])
        if obj:
            # shortcut: la copia no sigue al original si este se mueve después (igual que en Patrón, B-599)
            obj = objetos.duplicar(self, obj, 0, 0)
            objetos.transformar(self, obj, _matriz_de(reflejo))
            nuevos += objetos.curvas(self, obj)
        return nuevos

    def _patron(self, ids, trans, tipo, params, suprimidos=(), pid=None):
        """Copia `ids` por cada transformación `(f, ángulo, extra, datos)` de `trans` (salvo las suprimidas, por
        índice) y registra el patrón para poder editarlo (`editar_patron`). Devuelve las curvas nuevas."""
        from . import objetos
        ids = [i for i in ids if i in self.curvas or i in self.puntos or i in self.objetos]
        if not ids:
            raise ErrorBoceto("Seleccioná la geometría del patrón.")
        grupo = self._siguiente
        nuevos, copias = [], {}
        for n, (f, angulo, extra, datos) in enumerate(trans):
            if n in suprimidos:
                continue
            # B-599: un objeto vectorial (SVG) se copia entero, con su matriz movida como en Mover/Copiar.
            # shortcut: sus copias no siguen al original si este se mueve después; atarlas pide restricciones por objeto
            obj = [i for i in ids if i in self.objetos]
            if obj:
                obj = objetos.duplicar(self, obj, 0, 0)
                objetos.transformar(self, obj, _matriz_de(f))
            mapa, mapa_c = self._copiar(ids, f, False, angulo, extra)
            for p, q in mapa.items():
                self.agregar_restriccion("patron", [p, q] + extra, {**datos, "grupo": grupo})
            for i, k in mapa_c.items():
                if isinstance(self.curvas[i], (Circulo, Elipse, ArcoElipse)):
                    self.agregar_restriccion("igual", [i, k])
            copias[str(n)] = list(mapa_c.values()) + list(mapa.values()) + obj
            nuevos += list(mapa_c.values())
        registro = {"id": pid if pid is not None else self._nuevo_id(), "tipo": tipo, "ids": list(ids),
                    "params": params, "suprimidos": sorted(suprimidos), "copias": copias}
        self.patrones = [r for r in self.patrones if r["id"] != registro["id"]] + [registro]
        self.ultimo_patron = registro["id"]
        return nuevos

    def _dir_patron(self, vector, linea):
        """Dirección de un patrón: la de la línea del boceto (de su inicio a su fin) o el vector dado."""
        if linea is None:
            return vector
        a, b = self._extremos_linea(linea)
        return b[0] - a[0], b[1] - a[1]

    def _trans_rectangular(self, p):
        """Una traslación por copia: P(i, j) = P0 + i·paso1·u + j·paso2·w, siempre desde el original (nada se acumula).
        u y w son las direcciones unitarias (de un vector o de una línea del boceto); con `modo` extensión el paso es
        distancia / (n - 1) y con espaciado la distancia misma; con n = 1 la distancia no se usa. Simétrico: el original
        queda en el medio (con cantidad par, una copia más de un lado). El índice de copia sigue el orden i, j sin el
        original."""
        self.validar_patron("rectangular", p)
        n1, n2 = p["cantidad1"], p["cantidad2"]
        dir1 = self._dir_patron(p["dir1"], p.get("linea1"))
        dir2 = self._dir_patron(p["dir2"], p.get("linea2"))
        largo1, largo2 = math.hypot(*dir1), math.hypot(*dir2)
        if largo1 < 1e-9 or largo2 < 1e-9:
            raise ErrorBoceto("La dirección del patrón es de largo 0.")

        def paso(n, d):
            if n <= 1:
                return 0.0
            return d / (n - 1) if p["modo"] == "extension" else d
        u, w = (dir1[0] / largo1, dir1[1] / largo1), (dir2[0] / largo2, dir2[1] / largo2)
        s1, s2 = paso(n1, p["distancia1"]), paso(n2, p["distancia2"])
        o1 = -(n1 - 1) // 2 if p["simetrico"] else 0
        o2 = -(n2 - 1) // 2 if p.get("simetrico2", p["simetrico"]) else 0
        trans = []
        for i in range(n1):
            for j in range(n2):
                if i + o1 == 0 and j + o2 == 0:
                    continue
                dx = (i + o1) * s1 * u[0] + (j + o2) * s2 * w[0]
                dy = (i + o1) * s1 * u[1] + (j + o2) * s2 * w[1]
                trans.append((lambda q, dx=dx, dy=dy: (q[0] + dx, q[1] + dy), 0.0, [], {"dx": dx, "dy": dy}))
        return trans

    def patron_rectangular(self, ids, cantidad1, distancia1, cantidad2=1, distancia2=0.0, dir1=(1.0, 0.0),
                           dir2=(0.0, 1.0), modo="extension", simetrico=False, linea1=None, linea2=None,
                           suprimir=(), simetrico2=None, expresiones=None):
        """Patrón rectangular (SKT-CREATE-RECTANGULAR-PATTERN). La cantidad cuenta el original. modo "extension": la
        distancia es la total (de la primera a la última copia); "espaciado": la de cada paso. `linea1` / `linea2`
        toman la dirección de una línea del boceto; las direcciones pueden ser cualquiera, no solo X e Y.
        `simetrico2` (por defecto igual a `simetrico`) es el de la dirección 2. Las copias quedan atadas al original
        (restricción de patrón); `suprimir` son índices de copia que no se crean. `expresiones` guarda los textos
        de distancia1/2 y angulo1/2 junto a sus valores evaluados, para el recálculo del boceto."""
        params = {"cantidad1": cantidad1, "distancia1": distancia1, "cantidad2": cantidad2, "distancia2": distancia2,
                  "dir1": list(dir1), "dir2": list(dir2), "modo": modo, "simetrico": simetrico,
                  "linea1": linea1, "linea2": linea2}
        if simetrico2 is not None:
            params["simetrico2"] = simetrico2
        if expresiones:
            params["expresiones"] = dict(expresiones)
        trans, _cp, ids = self.comprobar_patron("rectangular", params, ids)
        return self._patron(ids, trans, "rectangular", params, set(suprimir))

    @staticmethod
    def validar_patron(tipo, p):
        """Reglas de un patrón (ventana, MCP y CLI usan estas): cantidades enteras, números finitos, distancias y ángulo
        distintos de cero y las dos direcciones del rectangular no paralelas. Con una sola copia en una dirección su
        distancia no se usa (0 vale). Lo que tendría que ser otro valor lo dice el mensaje."""
        def entero(n, que, minimo):
            if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n < minimo:
                raise ErrorBoceto(f"{que}: entero desde {minimo} (llegó {n!r}).")

        def finito(x, que):
            if isinstance(x, bool) or not isinstance(x, (int, float, np.integer, np.floating)) or not math.isfinite(x):
                raise ErrorBoceto(f"{que}: número finito (llegó {x!r}).")
        if tipo == "rectangular":
            n1, n2 = p["cantidad1"], p["cantidad2"]
            entero(n1, "La cantidad en la dirección 1", 1)
            entero(n2, "La cantidad en la dirección 2", 1)
            if n1 * n2 < 2:
                raise ErrorBoceto("El patrón necesita al menos 2 ejemplares.")
            if n1 * n2 - 1 > MAX_COPIAS_PATRON:
                raise ErrorBoceto(f"Patrón: máx. {MAX_COPIAS_PATRON} copias (pediste {n1 * n2 - 1}).")
            if p["modo"] not in ("extension", "espaciado"):
                raise ErrorBoceto("Distancia: total o de cada paso.")
            for n, d, eje in ((n1, p["distancia1"], 1), (n2, p["distancia2"], 2)):
                finito(d, f"La distancia en la dirección {eje}")
                if n > 1 and d == 0:
                    raise ErrorBoceto(f"Distancia {eje} = 0: las copias se pisan.")
            vectores = [p["dir1"], p["dir2"]]
            for k, (v, linea) in enumerate(zip(vectores, (p.get("linea1"), p.get("linea2")), strict=True), 1):
                if linea is None:
                    finito(v[0], f"La dirección {k}")
                    finito(v[1], f"La dirección {k}")
                    if math.hypot(*v) < 1e-9:
                        raise ErrorBoceto(f"Dirección {k} del patrón: largo 0.")
            if n1 > 1 and n2 > 1 and p.get("linea1") is None and p.get("linea2") is None:
                (a, b), (c, d) = p["dir1"], p["dir2"]
                if abs(a * d - b * c) < 1e-9 * math.hypot(a, b) * math.hypot(c, d):
                    raise ErrorBoceto("Direcciones paralelas: cambiá la 2.")
        else:
            n, total = p["cantidad"], p["angulo_total"]
            entero(n, "La cantidad", 2)
            if n - 1 > MAX_COPIAS_PATRON:
                raise ErrorBoceto(f"Patrón: máx. {MAX_COPIAS_PATRON} copias (pediste {n - 1}).")
            finito(total, "El ángulo total")
            if not 0 < abs(total) <= 360:
                raise ErrorBoceto("Ángulo total: de -360 a 360, sin 0.")

    def exigir_tamano_patron(self, ids, copias, sin=()):
        """Cada copia queda atada al original y el solver resuelve todo junto: tope de puntos copiados (copias × puntos
        de la selección)."""
        puntos = len([q for q in self.puntos_de(ids) if q not in sin])
        if copias * puntos > MAX_PUNTOS_PATRON:
            raise ErrorBoceto(f"Patrón: máx. {MAX_PUNTOS_PATRON} puntos (pediste {copias * puntos}).")

    def comprobar_patron(self, tipo, params, ids):
        """Todo lo que puede rechazar un patrón antes de crearlo, sin tocar el boceto: reglas de `validar_patron`,
        tope de puntos y centro apartado de la geometría. Devuelve (transformaciones, punto del centro o None, ids
        sin ese punto): lo que usan la creación, la edición y la vista previa."""
        from . import objetos
        trans, cp = (self._trans_rectangular(params), None) if tipo == "rectangular" else self._trans_circular(params)
        obj = [i for i in ids if i in self.objetos]
        if set(obj) - set(objetos.raices(self)):
            raise ErrorBoceto("Patrón: elegí el objeto entero, no una parte.")
        de_objetos = set(self.puntos_de(objetos.curvas(self, obj)))
        ids = [i for i in ids if i != cp and i not in de_objetos]       # sus puntos viajan con el objeto (B-599)
        if tipo == "circular":
            self._exigir_centro_aparte(ids, params["centro"], cp)
        self.exigir_tamano_patron(ids, len(trans), sin=(cp,))
        return trans, cp, ids

    def previa_patron(self, tipo, params, polilineas, suprimidos=(), ids=()):
        """Polilíneas de TODAS las copias del patrón (sin crear nada): cada polilínea elegida pasa por la misma
        transformación que usa la creación, salvo las copias `suprimidos`. Es la vista previa de la ventana: no toca
        el boceto ni el solver. Con `ids` también aplica las comprobaciones de la creación."""
        trans = self.comprobar_patron(tipo, params, ids)[0] if ids else (
            self._trans_rectangular(params) if tipo == "rectangular" else self._trans_circular(params)[0])
        return [[[f(q) for q in poli] for poli in polilineas] for n, (f, *_r) in enumerate(trans) if n not in suprimidos]

    def _trans_circular(self, p):
        """Una rotación por copia, siempre desde el original: Q_k = C + R(k·paso)(Q − C). Con 360° el paso es
        total / cantidad (la última copia no repite al original); con otro ángulo, total / (cantidad − 1) (el original y
        la última copia quedan en los extremos). Negativo = sentido horario. Simétrico (solo si no es la vuelta
        entera): el original queda en el medio. El índice de copia es k − 1."""
        self.validar_patron("circular", p)
        centro = p["centro"]
        es_punto = isinstance(centro, (int, np.integer)) and not isinstance(centro, bool)
        cp = self._punto(centro) if es_punto else None
        c = self.coords(cp) if cp is not None else (float(centro[0]), float(centro[1]))
        cantidad, total = p["cantidad"], p["angulo_total"]
        completo = abs(abs(total) - 360.0) < 1e-9
        paso = total / cantidad if completo else total / (cantidad - 1)
        desde = -(cantidad - 1) // 2 if p["simetrico"] and not completo else 0
        trans = []
        for k in range(cantidad):
            if k + desde == 0:
                continue
            a = math.radians((k + desde) * paso)
            datos = {"angulo": a} if cp is not None else {"angulo": a, "centro": c}
            trans.append((lambda q, a=a: (lambda r: (r[0] + c[0], r[1] + c[1]))(_rot(q[0] - c[0], q[1] - c[1], a)),
                          math.degrees(a), [cp] if cp is not None else [], datos))
        return trans, cp

    def patron_circular(self, ids, centro, cantidad, angulo_total=360.0, simetrico=False, suprimir=(), expresiones=None):
        """Patrón circular (SKT-CREATE-CIRCULAR-PATTERN) alrededor de `centro` (id de punto o (u, v)). Con
        coordenadas NO se crea un punto en el centro (B-55): el giro queda atado a un centro fijo; con id de
        punto, las copias lo siguen si se mueve. `suprimir`: índices de copia que no se crean.
        `expresiones` conserva el texto de angulo_total junto a su valor evaluado."""
        es_punto = isinstance(centro, (int, np.integer)) and not isinstance(centro, bool)
        params = {"centro": int(centro) if es_punto else list(centro), "cantidad": cantidad,
                  "angulo_total": angulo_total, "simetrico": simetrico}
        if expresiones:
            params["expresiones"] = dict(expresiones)
        trans, _cp, ids = self.comprobar_patron("circular", params, ids)
        return self._patron(ids, trans, "circular", params, set(suprimir))

    def _exigir_centro_aparte(self, ids, centro, cp):
        """Si todo lo elegido está sobre el centro, girarlo lo deja donde está: las copias quedarían encimadas."""
        c = self.coords(cp) if cp is not None else (float(centro[0]), float(centro[1]))
        puntos = self.puntos_de(ids)
        if puntos and all(math.dist(self.coords(q), c) < MEDIDA_MINIMA for q in puntos):
            raise ErrorBoceto("El centro cae sobre la geometría.")

    def evaluar_patrones(self, evaluar):
        """Reevalúa los valores de los patrones de Fusion sin reemplazar entidades ni sus referencias.

        `evaluar(texto, tipo)` usa las mismas unidades y parámetros que las cotas del boceto.
        """
        for registro in self.patrones:
            p = registro["params"]
            if not p.get("expresiones"):
                continue
            nuevo = dict(p)
            for clave, texto in p.get("expresiones", {}).items():
                valor = evaluar(texto, "angulo" if clave.startswith("angulo") else "longitud")
                if clave in ("angulo1", "angulo2"):
                    a = math.radians(valor)
                    nuevo["dir" + clave[-1]] = [math.cos(a), math.sin(a)]
                else:
                    nuevo[clave] = valor
            if nuevo == p:
                continue
            trans, _cp, _ids = self.comprobar_patron(registro["tipo"], nuevo, registro["ids"])
            for n, copia in registro["copias"].items():
                f, angulo, _extra, datos = trans[int(n)]
                puntos = set(copia) & self.puntos.keys()
                for r in self.restricciones.values():
                    if r.tipo == "patron" and r.entidades[1] in puntos:
                        r.datos = {**datos, "grupo": r.datos["grupo"]}
                        q = self.puntos[r.entidades[1]]
                        q.x, q.y = f(self.coords(r.entidades[0]))
                for original, cid in zip((i for i in registro["ids"] if i in self.curvas),
                                         (i for i in copia if i in self.curvas), strict=False):
                    if isinstance(self.curvas[cid], Texto):
                        self.curvas[cid].angulo = self.curvas[original].angulo + angulo
                for original, oid in zip((i for i in registro["ids"] if i in self.objetos),
                                         (i for i in copia if i in self.objetos), strict=False):
                    self.objetos[oid]["matriz"] = (_matriz_de(f) @ np.asarray(self.objetos[original]["matriz"])).tolist()
            registro["params"] = nuevo
            from . import objetos
            objetos.invalidar(self)

    def editar_patron(self, pid, **cambios):
        """Edita un patrón ya hecho (cantidades, distancias, direcciones, `suprimidos`): borra sus copias y las
        regenera con los parámetros nuevos. Las restricciones y cotas puestas sobre las copias pasan a la copia
        equivalente (mismo índice de copia y mismo lugar dentro de ella), con su id y su nombre. Devuelve la
        descripción de las que se pierden porque su copia ya no existe (suprimida o fuera de la cantidad nueva)."""
        registro = next((r for r in self.patrones if r["id"] == pid), None)
        if registro is None:
            raise ErrorBoceto(f"No existe el patrón {pid}.")
        suprimidos = set(cambios.pop("suprimidos", registro["suprimidos"]))
        params = {**registro["params"], **cambios}
        ids = [i for i in registro["ids"] if i in self.curvas or i in self.puntos or i in self.objetos]
        if not ids:
            raise ErrorBoceto("El patrón ya no tiene geometría original.")
        trans, cp, _ids = self.comprobar_patron(registro["tipo"], params, ids)
        lugar = {i: (n, k) for n, lista in registro["copias"].items() for k, i in enumerate(lista)}
        viejos = [i for i in lugar if i in self.objetos]
        if viejos:
            from . import objetos
            objetos.eliminar(self, viejos)
        originales = set(registro["ids"])
        sobre_copias = [copy.deepcopy(v) for tabla in (self.restricciones, self.cotas) for v in tabla.values()
                        if set(v.entidades) & set(lugar) and not (isinstance(v, Restriccion) and (
                            v.tipo == "patron" or v.tipo == "igual" and v.entidades[0] in originales))]
        for i in [i for i in lugar if i in self.curvas] + [i for i in lugar if i in self.puntos]:
            if i in self.curvas or i in self.puntos:
                self.eliminar(i)
        self._patron([i for i in ids if i != cp], trans, registro["tipo"], params, suprimidos, pid)
        copias = next(r for r in self.patrones if r["id"] == pid)["copias"]
        perdidas = []
        for v in sobre_copias:
            nuevas = [copias.get(lugar[e][0], [])[lugar[e][1]:lugar[e][1] + 1] if e in lugar else [e]
                      for e in v.entidades]
            if all(nuevas) and all(e[0] in self.curvas or e[0] in self.puntos or e[0] <= 0 for e in nuevas):
                v.entidades = [e[0] for e in nuevas]
                (self.restricciones if isinstance(v, Restriccion) else self.cotas)[v.id] = v
            else:
                que = "restricción" if isinstance(v, Restriccion) else "cota"
                perdidas.append(f"{que} {v.id} ({v.tipo}{' ' + v.nombre if getattr(v, 'nombre', '') else ''})")
        return perdidas
