"""Boceto 2D: cortes."""
import math

from .boceto_entidades import Arco, ArcoElipse, Circulo, Elipse, ErrorBoceto, Linea, Spline, Texto
from .boceto_geometria import caja_primitiva, dominio, evaluar_primitiva, intersecciones, mas_cercano, tramo_bspline


class _Cortes:
    # ------------------------------------------------------------ cadenas y cortes
    def cadena(self, cid, entre=None):
        """Curvas (líneas y arcos) conectadas por sus extremos a `cid`, en orden de recorrido, como la
        selección de cadena de Fusion: ([(id, invertida), ...], cerrada). Con `entre` (ids), solo cuentan esas curvas:
        el contorno de un perfil que toca otras figuras no se corta en cada unión."""
        c = self.curvas[cid]
        if not isinstance(c, (Linea, Arco)):
            return [(cid, False)], isinstance(c, (Circulo, Elipse))
        por_punto = {}
        for k in self.curvas.values():
            if isinstance(k, (Linea, Arco)) and k.construccion == c.construccion and (entre is None or k.id in entre):
                for p in k.extremos():
                    por_punto.setdefault(p, []).append(k.id)

        def siguiente(pid, actual):
            otros = [k for k in por_punto.get(pid, []) if k != actual]
            return otros[0] if len(otros) == 1 else None

        def caminar(pid, actual, usados):
            salida = []
            while True:
                k = siguiente(pid, actual)
                if k is None or k in usados:
                    return salida, k == cid
                ini, fin = self.curvas[k].extremos()
                inv = fin == pid
                salida.append((k, inv))
                usados.add(k)
                pid, actual = (ini if inv else fin), k
        ini, fin = c.extremos()
        adelante, cerrada = caminar(fin, cid, {cid})
        if cerrada:
            return [(cid, False)] + adelante, True
        atras, _ = caminar(ini, cid, {cid} | {k for k, _ in adelante})
        return [(k, not inv) for k, inv in reversed(atras)] + [(cid, False)] + adelante, False

    def _cortes(self, cid, prim=None):
        """[(t, (x, y), id de la otra curva)] donde `cid` cruza o toca a otras curvas, ordenados."""
        prim = self.primitivas(cid)[0] if prim is None else prim
        t0, t1, per = dominio(prim)
        caja = caja_primitiva(prim)
        cortes = []
        for oid, otra in self.curvas.items():
            if oid == cid or isinstance(otra, Texto):
                continue
            for q in self.primitivas(oid):
                cq = caja_primitiva(q)
                if cq[0] > caja[2] + 1e-6 or cq[2] < caja[0] - 1e-6 or cq[1] > caja[3] + 1e-6 or cq[3] < caja[1] - 1e-6:
                    continue
                q0, q1, _ = dominio(q)
                for ta, tb, xy in intersecciones(prim, q):
                    # una curva de construcción corta solo si la cruza (p. ej. los ejes de una elipse, que
                    # terminan sobre ella, no la parten)
                    if otra.construccion and (abs(tb - q0) < 1e-9 * (q1 - q0) or abs(tb - q1) < 1e-9 * (q1 - q0)):
                        continue
                    cortes.append((ta, xy, oid))
            if otra.construccion:
                continue
            for p in otra.extremos() or ():
                xy = self.coords(p)
                t, d, _ = mas_cercano(prim, xy)
                if d < 1e-7:
                    cortes.append((t, xy, oid))
        eps = 1e-9 * (t1 - t0)
        salida = []
        for t, xy, oid in sorted(cortes):
            if not per and (t <= t0 + eps or t >= t1 - eps):
                continue
            if salida and abs(t - salida[-1][0]) < eps * 10:
                continue
            salida.append((t, xy, oid))
        if per and len(salida) > 1 and abs(salida[0][0] + (t1 - t0) - salida[-1][0]) < eps * 10:
            salida.pop()
        return salida

    def _punto_corte(self, corte, nuevos):
        """Punto en un corte: se reutiliza uno existente en ese lugar o se crea con su coincidencia."""
        _t, (x, y), otra = corte
        for p in self.puntos.values():
            if math.hypot(p.x - x, p.y - y) < 1e-6:
                return p.id
        pid = self.agregar_punto(x, y)
        nuevos.append((pid, otra))
        return pid

    def _coincidencias_de_corte(self, nuevos):
        for pid, otra in nuevos:
            if otra in self.curvas and pid in self.puntos and pid not in self.curvas[otra].puntos():
                try:
                    self.agregar_restriccion("coincidente", [pid, otra])
                except ErrorBoceto:
                    pass

    def _tramo(self, cid, prim, ini, fin, nuevo, nuevos, viejos):
        """Reemplaza `cid` por el pedazo [ini, fin] (cortes o None = extremo original); con `nuevo`,
        el pedazo es una entidad aparte. Devuelve su id."""
        c = self.curvas[cid]
        t0, t1, _ = dominio(prim)
        ext = c.extremos() or (None, None)
        pa = ext[0] if ini is None else self._punto_corte(ini, nuevos)
        pb = ext[1] if fin is None else self._punto_corte(fin, nuevos)
        ident = self._nuevo_id() if nuevo else cid
        estilo = dict(construccion=c.construccion, eje=c.eje, proyectada=c.proyectada)
        if isinstance(c, Linea):
            k = Linea(ident, pa, pb, **estilo)
        elif isinstance(c, (Arco, Circulo)):
            k = Arco(ident, c.centro, pa, pb, **estilo)
        elif isinstance(c, (Elipse, ArcoElipse)):
            k = ArcoElipse(ident, c.centro, c.mayor, c.radio_menor, pa, pb, **estilo)
        else:
            ta = t0 if ini is None else ini[0]
            tb = t1 if fin is None else fin[0]
            polos, nudos, pesos = tramo_bspline(prim[2], prim[3], prim[4], prim[5], ta, tb)
            internos = [self.agregar_punto(*q) for q in polos[1:-1]]
            k = Spline(ident, [pa] + internos + [pb], "control", prim[4], False, pesos, nudos, **estilo)
            viejos.extend(c.puntos())
        if not nuevo:
            viejos.extend(p for p in c.puntos() if p not in k.puntos())
        self.curvas[ident] = k
        return ident

    def _vincular_tramos(self, a, b):
        ta = self.tipo_de(a)
        try:
            if ta == "linea":
                self.agregar_restriccion("colineal", [a, b])
            elif ta in ("arco", "arco_elipse"):
                self.agregar_restriccion("igual", [a, b])
        except ErrorBoceto:
            pass

    def _atar_extremos_soltados(self, cid, viejos):
        """P-77: el extremo que `cid` soltó al recortarse o alargarse y que sigue en otra curva (la esquina de un
        rectángulo, el final del arco de una ranura) queda sobre `cid` (su recta o su círculo). Antes quedaba solo
        ahí: la esquina se corría y el boceto perdía el «totalmente restringido» que Fusion conserva."""
        if cid not in self.curvas:
            return
        for p in viejos:
            # El otro tramo del mismo corte (colineal o igual) ya está atado. Junto a una tangencia sí se ata: el
            # solver toma entonces la tangencia en ese punto (B-255), sin la raíz doble de «distancia = radio».
            atadas = {e for r in self.restricciones.values()
                      if r.tipo in ("colineal", "igual") and cid in r.entidades for e in r.entidades}
            if (p in self.puntos and p not in self.curvas[cid].puntos() and self._punto_en_uso(p)
                    and not any(p in k.puntos() for k in self.curvas.values() if k.id in atadas - {cid})):
                try:
                    self.agregar_restriccion("coincidente", [p, cid])
                except ErrorBoceto:
                    pass

    def _sin_cotas_de_largo(self, cid, extremos=None):
        """Al cambiar el largo de una curva se quitan sus cotas y restricciones de largo (como Fusion). P-77: con
        `extremos` (los dos puntos del lado entero, que siguen vivos en las esquinas) Recortar, Partir y Alargar no
        borran la cota de largo: pasa a medir entre esos puntos, como Fusion (medido el 2026-11-08: el rectángulo y
        la ranura acotados siguen totalmente restringidos y con su cota). Si un punto ya no existe, se borra."""
        for k in [k for k, v in self.cotas.items() if v.entidades == [cid] and v.tipo.startswith("distancia")]:
            if extremos and extremos[0] != extremos[1] and all(p in self.puntos for p in extremos):
                self.cotas[k].entidades = list(extremos)
            else:
                del self.cotas[k]
        for k in [k for k, v in self.restricciones.items()
                  if cid in v.entidades and ((v.tipo == "igual" and self.tipo_de(cid) == "linea") or v.tipo == "punto_medio")]:
            del self.restricciones[k]

    def _curva_modificable(self, cid):
        c = self.curvas.get(cid)
        if c is None:
            raise ErrorBoceto("Hacé clic en una curva.")
        if isinstance(c, Texto):
            raise ErrorBoceto("Un texto no se puede recortar ni partir.")
        if c.proyectada:
            raise ErrorBoceto("La geometría proyectada no se modifica.")
        return c

    # ------------------------------------------------------------ MODIFICAR: recortar, alargar, partir
    def recortar(self, cid, punto):
        """Recortar (SKT-TRIM-EXTEND): quita el tramo de `cid` donde se hizo clic, hasta las
        intersecciones más cercanas. Si no corta con nada, se borra la curva entera."""
        c = self._curva_modificable(cid)
        prim = self.primitivas(cid)[0]
        _t0, _t1, per = dominio(prim)
        tc = mas_cercano(prim, punto)[0]
        cortes = self._cortes(cid)
        nuevos, viejos = [], []
        if per:
            if len(cortes) < 2:
                self.eliminar(cid)
                return None
            antes = [k for k in cortes if k[0] < tc]
            despues = [k for k in cortes if k[0] > tc]
            lo = antes[-1] if antes else cortes[-1]
            hi = despues[0] if despues else cortes[0]
            self._tramo(cid, prim, hi, lo, False, nuevos, viejos)    # el radio no cambia: sus cotas siguen
        else:
            antes = [k for k in cortes if k[0] < tc]
            despues = [k for k in cortes if k[0] > tc]
            lo, hi = (antes[-1] if antes else None), (despues[0] if despues else None)
            if lo is None and hi is None:
                self.eliminar(cid)
                return None
            self._sin_cotas_de_largo(cid, c.extremos())
            if lo is not None and hi is not None:
                otro = self._tramo(cid, prim, hi, None, True, nuevos, viejos)
                self._tramo(cid, prim, None, lo, False, nuevos, viejos)
                self._vincular_tramos(cid, otro)
            elif lo is None:
                self._tramo(cid, prim, hi, None, False, nuevos, viejos)
            else:
                self._tramo(cid, prim, None, lo, False, nuevos, viejos)
        self._coincidencias_de_corte(nuevos)
        self._atar_extremos_soltados(cid, viejos)
        self._soltar_puntos_viejos(viejos)
        self._depurar(viejos)
        return c.id

    def _soltar_puntos_viejos(self, viejos, virtual=None, X=None):
        """B-233: un punto viejo que ya no usa ninguna curva no queda suelto con lo que tenía puesto (fijo, cotas,
        coincidencias). Si estaba en la esquina, eso pasa al vértice virtual; si era de un tramo que se fue, se va
        con él, como en Fusion."""
        for p in viejos:
            if p == virtual or p not in self.puntos or self._punto_en_uso(p):
                continue
            if virtual is not None and math.dist(self.coords(p), X) < 1e-9:
                self._fusionar_punto(virtual, p)
            else:
                del self.puntos[p]

    def partir(self, cid, punto):
        """Partir (SKT-BREAK): divide la curva en las intersecciones más cercanas al clic. Devuelve los ids."""
        self._curva_modificable(cid)
        prim = self.primitivas(cid)[0]
        _t0, _t1, per = dominio(prim)
        tc = mas_cercano(prim, punto)[0]
        cortes = self._cortes(cid)
        nuevos, viejos = [], []
        # B-512: un clic justo sobre el cruce cuenta como «después» (parte ahí), no queda en ningún lado
        antes = [k for k in cortes if k[0] < tc - 1e-9]
        despues = [k for k in cortes if k[0] >= tc - 1e-9]
        if per:
            if len(cortes) < 2:
                raise ErrorBoceto("Curva cerrada: hacen falta dos cortes.")
            lo = antes[-1] if antes else cortes[-1]
            hi = despues[0] if despues else cortes[0]
            otro = self._tramo(cid, prim, lo, hi, True, nuevos, viejos)
            self._tramo(cid, prim, hi, lo, False, nuevos, viejos)
            ids = [cid, otro]
        else:
            lo, hi = (antes[-1] if antes else None), (despues[0] if despues else None)
            if lo is None and hi is None:
                raise ErrorBoceto("La curva no cruza nada: no se puede partir.")
            self._sin_cotas_de_largo(cid, self.curvas[cid].extremos())
            ids = []
            if hi is not None:
                ids.append(self._tramo(cid, prim, hi, None, True, nuevos, viejos))
            if lo is not None:
                ids.append(self._tramo(cid, prim, lo, hi, True, nuevos, viejos))
                self._tramo(cid, prim, None, lo, False, nuevos, viejos)
            else:
                self._tramo(cid, prim, None, hi, False, nuevos, viejos)
            ids.insert(0, cid)
            for otro in ids[1:]:
                self._vincular_tramos(cid, otro)
            # B-255: la tangencia sigue con el tramo que toca la otra curva (comparte su extremo), no con el que
            # quedó lejos: si no, ese tramo pierde la tangencia y la unión queda libre.
            for r in [r for r in self.restricciones.values() if r.tipo == "tangente" and cid in r.entidades]:
                k = next(e for e in r.entidades if e != cid)
                tramo = next((t for t in ids if self.extremo_comun(t, k) is not None), None)
                if tramo is not None and tramo != cid and self.extremo_comun(cid, k) is None:
                    r.entidades = [tramo if e == cid else e for e in r.entidades]
        self._coincidencias_de_corte(nuevos)
        self._depurar(viejos)
        return ids

    def alargar(self, cid, punto):
        """Alargar (SKT-TRIM-EXTEND): extiende el extremo más cercano al clic hasta la próxima
        intersección. Una spline abierta se prolonga por su tangente, sin cambiar el tramo original;
        pasa a puntos de control. Un arco circular o elíptico continúa sobre su curva portadora."""
        c = self._curva_modificable(cid)
        if not isinstance(c, (Linea, Arco, ArcoElipse, Spline)) or not c.extremos():
            raise ErrorBoceto("Alargar: líneas, arcos y splines abiertas.")
        ini, fin = c.extremos()
        lado_fin = math.dist(self.coords(fin), punto) <= math.dist(self.coords(ini), punto)
        extremo = fin if lado_fin else ini
        if extremo in self.puntos_fijos():      # Fusion: lo fijo se suelta antes de editarlo (B-237)
            raise ErrorBoceto("Extremo fijo: quitá «Fijo» para alargar.")
        xs = [p.x for p in self.puntos.values()]
        ys = [p.y for p in self.puntos.values()]
        grande = 10 * (max(xs) - min(xs) + max(ys) - min(ys)) + 1000
        if isinstance(c, Linea):
            a, b = self.coords(ini), self.coords(fin)
            if not lado_fin:
                a, b = b, a
            L = math.dist(a, b)
            if L < 1e-9:
                raise ErrorBoceto("No se puede alargar una línea de largo 0.")
            d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            rayo = ("linea", None, b, (b[0] + d[0] * grande, b[1] + d[1] * grande))
        else:
            prim = self.primitivas(cid)[0]
            if isinstance(c, Spline):
                t0, t1, _ = dominio(prim)
                b, tangente = evaluar_primitiva(prim, t1 if lado_fin else t0, 1)
                rapidez = math.hypot(*tangente)
                if rapidez < 1e-12:
                    raise ErrorBoceto("La spline no tiene tangente en ese extremo.")
                signo = 1 if lado_fin else -1
                d = (signo * tangente[0] / rapidez, signo * tangente[1] / rapidez)
                rayo = ("linea", None, b, (b[0] + d[0] * grande, b[1] + d[1] * grande))
            else:
                # El complemento del arco, recorrido hacia adelante o hacia atrás según el extremo.
                rayo = prim[:4] + (prim[5], prim[4]) if isinstance(c, Arco) else prim[:6] + (prim[7], prim[6])
        mejor = None
        for t, xy, oid in self._cortes(cid, rayo):
            if math.dist(xy, self.coords(extremo)) < 1e-7:
                continue
            clave = t if (isinstance(c, (Linea, Spline)) or lado_fin) else -t
            if mejor is None or clave < mejor[0]:
                mejor = (clave, xy, oid)
        if mejor is None:
            raise ErrorBoceto("No hay curva para alcanzar en esa dirección.")
        _, xy, oid = mejor
        nuevos, viejos = [], []
        otras = [k for k in self.curvas.values() if k.id != cid and extremo in k.puntos()]
        if isinstance(c, Spline):
            polos, nudos, grado, pesos = prim[2:]
            ids = list(c.pts) if c.modo == "control" else (
                [ini] + [self.agregar_punto(*q) for q in polos[1:-1]] + [fin])
            viejos.extend(c.puntos())
            nuevo = self._punto_corte((0, xy, oid), nuevos)
            b = self.coords(extremo)
            internos = [self.agregar_punto(b[0] + (xy[0] - b[0]) * j / grado,
                                          b[1] + (xy[1] - b[1]) * j / grado) for j in range(1, grado)]
            delta = math.dist(b, xy) / rapidez
            # Un tramo Bézier recto, unido con multiplicidad grado: conserva exactamente la curva anterior.
            if lado_fin:
                ids += internos + [nuevo]
                nudos = list(nudos[:-1]) + [t1 + delta] * (grado + 1)
                pesos = None if pesos is None else list(pesos) + [pesos[-1]] * grado
            else:
                ids = [nuevo] + internos[::-1] + ids
                nudos = [t0 - delta] * (grado + 1) + list(nudos[1:])
                pesos = None if pesos is None else [pesos[0]] * grado + list(pesos)
            self.curvas[cid] = Spline(cid, ids, "control", grado, False, pesos, nudos,
                                      c.construccion, c.eje, c.proyectada)
        elif otras or self._punto_referenciado(extremo):
            nuevo = self._punto_corte((0, xy, oid), nuevos)
            for a in ("p1", "p2", "inicio", "fin"):
                if getattr(c, a, None) == extremo:
                    setattr(c, a, nuevo)
            viejos.append(extremo)
        else:
            self.puntos[extremo].x, self.puntos[extremo].y = xy
            nuevos.append((extremo, oid))
        # el extremo viejo sigue en la esquina (otra curva lo usa): la cota mide el lado entero, como Fusion
        self._sin_cotas_de_largo(cid, (ini, fin) if extremo not in c.puntos() else None)
        self._coincidencias_de_corte(nuevos)
        self._atar_extremos_soltados(cid, viejos)
        self._soltar_puntos_viejos(viejos)      # el extremo viejo no queda suelto con sus cotas (B-237)
        self._depurar(viejos)
        return cid
