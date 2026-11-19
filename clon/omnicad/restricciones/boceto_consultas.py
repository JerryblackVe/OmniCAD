"""Boceto 2D: consultas."""
import math

from .. import deshabilitado
from .boceto_entidades import (
    Arco, ArcoElipse, CAMBIABLES, CIRCULARES, Circulo, CON_CENTRO, Cota, distancia_con_circulo,
    distancia_punto_recta, Elipse, ELIPTICAS, ErrorBoceto, GEOMETRICAS, LIBRES, Linea, ORDEN_RESTRICCION, Punto,
    Restriccion, signos_cuadrante, Spline, TIPOS_COTA, TIPOS_RESTRICCION, _validar_cuadrante, validar_valor_cota,
)
from .boceto_geometria import dominio, evaluar_primitiva, mas_cercano, pie_normal
from .boceto_primitivas import primitivas_entidad


class _Consultas:
    def agregar_restriccion(self, tipo, entidades, datos=None):
        primero = ORDEN_RESTRICCION.get(tipo)
        if primero:          # la ventana, la API y el MCP aceptan cualquier orden de selección (B-224)
            entidades = sorted(entidades, key=lambda e: self.tipo_de(e) != primero)
        self._validar_restriccion(tipo, entidades)
        if tipo == "fijo":
            for r in self.restricciones.values():
                if r.tipo == tipo and set(r.entidades) == set(entidades):
                    return r.id
        r = Restriccion(self._nuevo_id(), tipo, entidades, datos)
        self.restricciones[r.id] = r
        return r.id

    def girar_a_perpendicular(self, a, b):
        """Antes de agregar Perpendicular línea–spline con el comando (B-586): gira la línea alrededor de su punto medio
        hasta dejarla normal a la spline, como Fusion (no la mueve a tocarla). Si no, el solver deformaba la spline.
        No toca una línea con un punto fijo."""
        l, s = (a, b) if self.tipo_de(a) == "linea" else (b, a)
        if self.tipo_de(l) != "linea" or self.tipo_de(s) != "spline":
            return
        extremos = self.curvas[l].puntos()
        if self.puntos_fijos().intersection(extremos):
            return
        (x1, y1), (x2, y2) = (self.coords(p) for p in extremos)
        m, medio = ((x1 + x2) / 2, (y1 + y2) / 2), math.hypot(x2 - x1, y2 - y1) / 2
        _t, _c, d = pie_normal(self.primitivas(s)[0], m)
        n = math.hypot(*d) or 1e-12
        u = (-d[1] / n, d[0] / n)
        if u[0] * (x2 - x1) + u[1] * (y2 - y1) < 0:      # conserva hacia dónde apuntaba la línea
            u = (-u[0], -u[1])
        for p, k in zip(extremos, (-1, 1), strict=True):
            self.puntos[p].x, self.puntos[p].y = m[0] + k * medio * u[0], m[1] + k * medio * u[1]

    def tipos_compatibles(self, rid):
        """Tipos por los que se puede cambiar la restricción `rid` sin cambiar sus entidades (`CAMBIABLES`)."""
        r = self.restricciones[rid]
        if r.tipo not in CAMBIABLES:
            return []
        salida = []
        for tipo in CAMBIABLES:
            try:
                if tipo != r.tipo:
                    self._validar_restriccion(tipo, r.entidades)
                    self.exigir_disponible(tipo, r.entidades)
                    salida.append(tipo)
            except ErrorBoceto:
                pass
        return salida

    def reemplazar_restriccion(self, rid, tipo):
        """Cambia la restricción `rid` por otra de tipo `tipo` sobre las mismas entidades y con el mismo id (así el
        símbolo y la selección siguen siendo los mismos). No resuelve: si choca con las demás lo ve el solver."""
        if tipo not in self.tipos_compatibles(rid):
            r = self.restricciones[rid]
            raise ErrorBoceto(f"No se puede cambiar «{TIPOS_RESTRICCION[r.tipo]}» por «{TIPOS_RESTRICCION.get(tipo, tipo)}».")
        self.restricciones[rid] = Restriccion(rid, tipo, self.restricciones[rid].entidades)
        return rid

    def anclar_al_origen(self, puntos_nuevos):
        """Fija el primer punto nuevo dibujado sobre (0, 0), como el editor de Fusion."""
        for pid in sorted(puntos_nuevos):
            x, y = self.coords(pid)
            if abs(x) < 1e-9 and abs(y) < 1e-9:
                return self.agregar_restriccion("fijo", [pid], {"origen": True})
        return None

    def asegurar_referencias(self, ids):
        """Materializa solo las referencias citadas: origen 0, eje X -1 y eje Y -2.

        Son geometría de construcción fija (proyectada); sus puntos auxiliares -3/-4
        no consumen ids de usuario ni aportan grados de libertad o perfiles.
        """
        if any(i in (self.ORIGEN, self.EJE_X, self.EJE_Y) for i in ids):
            self.puntos.setdefault(self.ORIGEN, Punto(self.ORIGEN, 0, 0, proyectado=True))
        for eje, pid, x, y in ((self.EJE_X, -3, 1, 0), (self.EJE_Y, -4, 0, 1)):
            if eje in ids:
                self.puntos.setdefault(pid, Punto(pid, x, y, proyectado=True))
                self.curvas.setdefault(eje, Linea(eje, self.ORIGEN, pid, construccion=True, proyectada=True))

    def agregar_cota(self, tipo, entidades, expresion, datos=None, referencia=False):
        """Crea una cota (Sketch Dimension); una referencia mide sin restringir la geometría. `datos["modo"]`
        ("centro" o "tangente") vale en una distancia con un círculo o arco; ahí se guarda siempre (falta = centro)."""
        datos = dict(datos or {})
        self._validar_cota(tipo, entidades)
        # Solo al crear: una cota guardada puede haber perdido el paralelismo (no se descarta al cargar).
        if tipo == "distancia" and [self.tipo_de(e) for e in entidades] == ["linea", "linea"]:
            d1, d2 = (self._direccion(e) for e in entidades)
            if abs(d1[0] * d2[1] - d1[1] * d2[0]) >= 1e-6:  # mismo umbral que la herramienta Cota de la ventana
                raise ErrorBoceto("No son paralelas: usá cota de ángulo.")
        if tipo == "angulo" and not referencia:
            try:
                valor = float(expresion.replace(",", "."))
            except ValueError:                          # las expresiones se validan al evaluarlas en el documento/editor
                pass
            else:
                validar_valor_cota(tipo, valor)
        modo = datos.pop("modo", "centro")
        if modo not in ("centro", "tangente"):
            raise ErrorBoceto(f"Modo de cota desconocido: {modo}.")
        if self.admite_modo(tipo, entidades):
            datos["modo"] = modo
        elif modo == "tangente":
            raise ErrorBoceto("Tangente solo vale en cota de distancia.")
        if tipo in ("distancia_h", "distancia_v") and "signo" not in datos:
            (x1, y1), (x2, y2) = self._extremos_cota(entidades)
            d = (x2 - x1) if tipo == "distancia_h" else (y2 - y1)
            datos["signo"] = 1.0 if d >= 0 else -1.0
        if "cuadrante" in datos:
            _validar_cuadrante(tipo, datos["cuadrante"])
        if referencia:
            expresion = repr(self.medir_cota(tipo, entidades, modo, datos.get("cuadrante"))
                             * (2 if datos.get("diametral") else 1))
        c = Cota(self._nuevo_id(), tipo, entidades, expresion, datos, referencia=referencia)
        self.cotas[c.id] = c
        return c.id

    def admite_modo(self, tipo, entidades):
        """True si la cota mide al centro o tangente: una distancia con un círculo o un arco (BOC-3)."""
        return tipo == "distancia" and any(self.tipo_de(e) in CIRCULARES for e in entidades)

    def cambiar_cota(self, cid, tipo=None, modo=None, cuadrante=None):
        """Menú de la cota (BOC-3). `tipo`: radio ↔ diámetro conservando el valor equivalente (la expresión se
        multiplica o divide por 2: la geometría no cambia). `modo`: centro ↔ tangente; la expresión queda y la
        geometría la cumple al resolver (una cota de referencia vuelve a medir). `cuadrante` (0..3, BOC-25): qué
        ángulo mide una cota de ángulo; igual que `modo`, la expresión queda."""
        k = self.cotas[cid]
        if cuadrante is not None:
            _validar_cuadrante(k.tipo, cuadrante)
            k.datos["cuadrante"] = cuadrante
            if k.referencia:
                k.expresion = repr(self.medir(k))
        if tipo is not None:
            if not {tipo, k.tipo} <= {"radio", "diametro"}:
                raise ErrorBoceto("Solo radio pasa a diámetro (o al revés).")
            if tipo != k.tipo:
                try:
                    v = float(k.expresion.replace(",", "."))      # como en escalar: el editor admite "6,5"
                    k.expresion = repr(v * 2 if tipo == "diametro" else v / 2)
                except ValueError:
                    k.expresion = f"({k.expresion}) {'* 2' if tipo == 'diametro' else '/ 2'}"
                k.tipo = tipo
        if modo is not None:
            if modo not in ("centro", "tangente"):
                raise ErrorBoceto(f"Modo de cota desconocido: {modo}.")
            if not self.admite_modo(k.tipo, k.entidades):
                raise ErrorBoceto("Centro/tangente: solo en cota de distancia.")
            k.datos["modo"] = modo
            if k.referencia:
                k.expresion = repr(self.medir(k))

    # ------------------------------------------------------------ consultas
    def coords(self, pid):
        p = self.puntos[pid]
        return (p.x, p.y)

    def radio(self, cid):
        c = self.curvas[cid]
        if isinstance(c, Circulo):
            return c.radio
        if isinstance(c, (Elipse, ArcoElipse)):
            return c.radio_menor
        (cx, cy), (sx, sy) = self.coords(c.centro), self.coords(c.inicio)
        return math.hypot(sx - cx, sy - cy)

    def tipo_de(self, id):
        return self.entidad(id).tipo

    def extremos(self, cid):
        return self.curvas[cid].extremos()

    def puntos_fijos(self, origen=True):
        """Puntos inmóviles: por una restricción 'fijo' (sobre el punto o su curva) o por ser proyectados. `origen=False`
        no cuenta el anclaje al origen que pone dibujar desde (0, 0): mover la selección lo suelta, como Fusion (B-538)."""
        fijos = {p.id for p in self.puntos.values() if p.proyectado}
        if self.objetos:
            from . import objetos
            fijos.update(p for cid, (raiz, _hoja, _m) in objetos.indice(self).items()
                         if not self.objetos[raiz].get("texto_automatico") for p in self.curvas[cid].puntos())
        for c in self.curvas.values():
            if c.proyectada:
                fijos.update(c.puntos())
        for r in self.restricciones.values():
            if r.tipo == "fijo" and (origen or not r.datos.get("origen")):
                for e in r.entidades:
                    fijos.update([e] if e in self.puntos else self.curvas[e].puntos())
        return fijos

    def curva_bloqueada(self, cid):
        return self.props_curvas.get(cid, {}).get("bloqueado", False)

    def exigir_desbloqueadas(self, ids, verbo):
        """H-69: ErrorBoceto si `ids` tiene una curva bloqueada, o un punto de una (borrarlo se llevaría la curva)."""
        if not any(c.get("bloqueado") for c in self.props_curvas.values()):
            return
        for i in ids:
            curvas = [i] if i in self.curvas else [c.id for c in self.curvas.values() if i in c.puntos()]
            for cid in curvas:
                if self.curva_bloqueada(cid):
                    raise ErrorBoceto(f"Curva {cid}: desbloqueala para {verbo}.")

    def puntos_de(self, ids):
        """Puntos usados por las curvas de `ids` más los puntos sueltos de `ids`."""
        salida = []
        for i in ids:
            for p in ([i] if i in self.puntos else self.curvas[i].puntos() if i in self.curvas else []):
                if p not in salida:
                    salida.append(p)
        return salida

    def _con_vertices_virtuales(self, ids, pts):
        """`pts` más los puntos sueltos (de ninguna curva) atados solo a lo elegido, como el vértice virtual de un
        chaflán o un empalme: si quedaran quietos, sus cotas tirarían de la figura al moverla o escalarla (B-232)."""
        en_curvas = {p for c in self.curvas.values() for p in c.puntos()}
        elegidos = set(ids) | set(pts)
        otros = {}
        for t in (self.restricciones, self.cotas):
            for r in t.values():
                for e in r.entidades:
                    if e in self.puntos and e not in en_curvas and e not in elegidos:
                        otros.setdefault(e, set()).update(set(r.entidades) - {e})
        return list(pts) + [p for p, ents in otros.items() if ents and ents <= elegidos]

    def _extremos_cota(self, entidades):
        if len(entidades) == 2:
            return self.coords(entidades[0]), self.coords(entidades[1])
        ln = self.curvas[entidades[0]]
        return self.coords(ln.p1), self.coords(ln.p2)

    def ejes_cota(self, c):
        """Marco de una cota lineal (línea sola o dos puntos): (a, b, u, n, s0) —extremos medidos, eje a lo largo
        de la cota, eje normal y coordenada normal de la referencia—. None si la cota no se puede ubicar."""
        if c.tipo not in ("distancia", "distancia_h", "distancia_v"):
            return None
        if [self.tipo_de(e) for e in c.entidades] not in (["linea"], ["punto", "punto"]):
            return None
        a, b = self._extremos_cota(c.entidades)
        if c.tipo == "distancia_h":
            u, n = (1.0, 0.0), (0.0, 1.0)
        elif c.tipo == "distancia_v":
            u, n = (0.0, 1.0), (1.0, 0.0)
        else:
            largo = math.dist(a, b)
            if largo < 1e-12:
                return None
            u = ((b[0] - a[0]) / largo, (b[1] - a[1]) / largo)
            n = (-u[1], u[0])
        return a, b, u, n, max(a[0] * n[0] + a[1] * n[1], b[0] * n[0] + b[1] * n[1])

    def segmento_cota(self, c):
        """BOC-37: el segmento ((x, y), (x, y)) que mide una cota de distancia o de desfase que no es la lineal de una
        línea o dos puntos (esas tienen su `ejes_cota`): punto–línea, línea–línea paralelas, con círculo o arco (hasta el
        centro o de borde a borde, según su `modo`), punto–spline y el desfase de una curva. La interfaz dibuja ahí la
        línea de cota con sus flechas. None si no hay nada que dibujar (cota de otro tipo, medida cero o geometría
        a medio borrar: dibujar nunca debe fallar)."""
        try:
            return self._segmento_cota(c)
        except (KeyError, IndexError, ValueError, ZeroDivisionError, ErrorBoceto):
            return None

    def _segmento_cota(self, c):
        P, t = self.coords, [self.tipo_de(e) for e in c.entidades]

        def pie(q, linea):
            a, b = self._extremos_linea(linea)
            d = distancia_punto_recta(q, a, b)
            largo = math.dist(a, b) or 1.0
            n = (-(b[1] - a[1]) / largo, (b[0] - a[0]) / largo)
            return q[0] - d * n[0], q[1] - d * n[1]

        def hacia(centro, radio, q):
            """Punto del borde del círculo en la dirección de `q`."""
            d = math.dist(centro, q) or 1.0
            return centro[0] + radio * (q[0] - centro[0]) / d, centro[1] + radio * (q[1] - centro[1]) / d
        seg = None
        if c.tipo == "desfase":
            madre, copia = (self.curvas[e] for e in c.entidades)
            if isinstance(madre, Linea):
                seg = pie(P(copia.p1), madre.id), P(copia.p1)
            elif isinstance(madre, Elipse) and isinstance(copia, Elipse):
                seg = P(madre.mayor), P(copia.mayor)
            elif isinstance(madre, (Circulo, Arco)):
                centro, prim = P(madre.centro), self.primitivas(madre.id)[0]
                un = (math.cos(math.pi / 4), math.sin(math.pi / 4)) if isinstance(madre, Circulo) else None
                if un is None:                       # el arco: en la dirección de su punto medio
                    medio = evaluar_primitiva(prim, dominio(prim)[1] / 2)[0]
                    d = math.dist(centro, medio) or 1.0
                    un = ((medio[0] - centro[0]) / d, (medio[1] - centro[1]) / d)
                r1, r2 = self.radio(madre.id), self.radio(copia.id)
                seg = (centro[0] + r1 * un[0], centro[1] + r1 * un[1]), (centro[0] + r2 * un[0], centro[1] + r2 * un[1])
            elif isinstance(copia, Spline):
                q = P(copia.pts[0])
                seg = mas_cercano(self.primitivas(madre.id)[0], q)[2], q
        elif c.tipo == "distancia":
            tangente = c.datos.get("modo", "centro") == "tangente"
            circ = [e for e, x in zip(c.entidades, t, strict=True) if x in CIRCULARES]
            if circ:
                otro = next((e for e in c.entidades if e != circ[0]), circ[0])
                centro, radio = P(self.curvas[circ[0]].centro), self.radio(circ[0])
                if t[c.entidades.index(otro)] in CIRCULARES and otro != circ[0]:
                    c2, r2 = P(self.curvas[otro].centro), self.radio(otro)
                    d = math.dist(centro, c2)
                    if tangente and d > 1e-12:
                        grande = radio >= r2
                        u = ((c2[0] - centro[0]) / d, (c2[1] - centro[1]) / d)
                        if d < abs(radio - r2):          # uno adentro del otro: el borde más cercano de cada uno
                            s = 1.0 if grande else -1.0
                            seg = ((centro[0] + s * radio * u[0], centro[1] + s * radio * u[1]),
                                   (c2[0] + s * r2 * u[0], c2[1] + s * r2 * u[1]))
                        else:
                            seg = ((centro[0] + radio * u[0], centro[1] + radio * u[1]),
                                   (c2[0] - r2 * u[0], c2[1] - r2 * u[1]))
                    else:
                        seg = centro, c2
                else:
                    q = P(otro) if t[c.entidades.index(otro)] == "punto" else pie(centro, otro)
                    seg = (hacia(centro, radio, q) if tangente else centro), q
            elif sorted(t) == ["punto", "spline"]:
                punto = c.entidades[t.index("punto")]
                seg = mas_cercano(self.primitivas(c.entidades[t.index("spline")])[0], P(punto))[2], P(punto)
            elif sorted(t) == ["linea", "punto"]:
                punto = c.entidades[t.index("punto")]
                seg = pie(P(punto), c.entidades[t.index("linea")]), P(punto)
            elif t == ["linea", "linea"]:
                a = P(self.curvas[c.entidades[1]].p1)
                seg = pie(a, c.entidades[0]), a
        return seg if seg is not None and math.dist(*seg) > 1e-9 else None

    def ubicar_cota(self, c, punto, con_texto=True):
        """Guarda dónde van la línea de cota y su texto (datos «desfase» y «texto», en mm): la línea pasa por
        `punto` (x, y) y el texto queda a su altura (con `con_texto` falso, el texto no se corre). No cambia el
        valor ni la geometría."""
        if c.tipo == "angulo":                # BOC-25: el cuadrante bajo el cursor elige qué ángulo se mide
            c.datos["cuadrante"] = self.cuadrante_angulo(*c.entidades, punto)
            return
        marco = self.ejes_cota(c)
        if marco is not None:
            a, b, u, n, s0 = marco
            c.datos["desfase"] = round(punto[0] * n[0] + punto[1] * n[1] - s0, 6)
            if con_texto:
                medio = ((a[0] + b[0]) * u[0] + (a[1] + b[1]) * u[1]) / 2
                c.datos["texto"] = round(punto[0] * u[0] + punto[1] * u[1] - medio, 6)

    def mover_cota(self, c, punto, con_texto=True):
        """Arrastrar una cota ya creada (Fusion: todas se pueden mover): no cambia su valor ni la geometría. Las
        lineales mueven su línea y su texto (`ubicar_cota`; agarrada de la línea, `con_texto` falso, solo la línea);
        las demás guardan en «ubic» el punto (x, y) en mm donde va el texto (en un ángulo, además, fija el radio del
        arco y elige el cuadrante que se mide, como `near`: la expresión queda y la geometría la cumple al resolver;
        en un radio o diámetro, hacia dónde sale la línea)."""
        if self.ejes_cota(c) is not None:
            self.ubicar_cota(c, punto, con_texto)
        else:
            if c.tipo == "angulo":              # arrastrarla a otro cuadrante cambia el ángulo que mide (Fusion)
                self.cambiar_cota(c.id, cuadrante=self.cuadrante_angulo(*c.entidades, punto))
            c.datos["ubic"] = [round(punto[0], 6), round(punto[1], 6)]

    def arco_angulo(self, c):
        """(vértice, t0, t1) del arco de una cota de ángulo: el cruce de las dos rectas y los ángulos (radianes) de
        las semirrectas del cuadrante elegido, con t1 − t0 entre −π y π."""
        l1, l2 = c.entidades
        (a, _), (b, _) = self._extremos_linea(l1), self._extremos_linea(l2)
        d1, d2 = self._direccion(l1), self._direccion(l2)
        det = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(det) < 1e-9:
            raise ErrorBoceto("Las líneas son paralelas: no forman ángulo.")
        s = ((b[0] - a[0]) * d2[1] - (b[1] - a[1]) * d2[0]) / det
        s1, s2 = signos_cuadrante(c.datos.get("cuadrante"))
        t0, t1 = math.atan2(s1 * d1[1], s1 * d1[0]), math.atan2(s2 * d2[1], s2 * d2[0])
        return (a[0] + s * d1[0], a[1] + s * d1[1]), t0, t0 + (t1 - t0 + math.pi) % (2 * math.pi) - math.pi

    def separacion(self, original, desfasada):
        """Distancia entre una curva y su desfase; en curvas libres mide el primer punto de ajuste."""
        return abs(self.separacion_con_lado(original, desfasada))

    def separacion_con_lado(self, original, desfasada):
        """`separacion` con el signo de `Sistema.separacion` y del «lado» de las curvas libres."""
        o, d = self.curvas[original], self.curvas[desfasada]
        if isinstance(o, Linea):
            return distancia_punto_recta(self.coords(d.p1), *self._extremos_linea(o.id))
        if isinstance(o, Elipse) and isinstance(d, Elipse):         # la elipse del desfase con eje: difieren los semiejes
            semieje = lambda e: math.dist(self.coords(e.centro), self.coords(e.mayor))  # noqa: E731
            return semieje(d) - semieje(o)
        if isinstance(o, (Spline, Elipse, ArcoElipse)):
            prim, p = self.primitivas(original)[0], self.coords(d.pts[0])
            t, distancia, q = mas_cercano(prim, p)
            tangente = evaluar_primitiva(prim, t, 1)[1]
            return math.copysign(distancia, tangente[0] * (p[1] - q[1]) - tangente[1] * (p[0] - q[0]))
        return self.radio(d.id) - self.radio(o.id)

    def medir(self, cota):
        """Valor actual de una cota existente (con su modo). Una cota de desfase con «lado» sale negativa si la copia
        pasó al otro lado (BOC-50)."""
        if cota.tipo == "desfase" and (lado := cota.datos.get("lado")):
            return lado * self.separacion_con_lado(*cota.entidades)
        medida = self.medir_cota(cota.tipo, cota.entidades, cota.datos.get("modo", "centro"), cota.datos.get("cuadrante"))
        return medida * 2 if cota.datos.get("diametral") else medida     # cota con la línea central: diámetro

    def cuadrante_angulo(self, l1, l2, punto):
        """Cuadrante (0..3) entre las rectas de l1 y l2 que contiene `punto` (x, y), como Fusion elige el ángulo
        con el cursor: 0 entre +d1 y +d2, 1 entre −d1 y +d2, 2 entre −d1 y −d2, 3 entre +d1 y −d2 (d = p1→p2)."""
        (a, _), (c, _) = self._extremos_linea(l1), self._extremos_linea(l2)
        d1, d2 = self._direccion(l1), self._direccion(l2)
        det = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(det) < 1e-9:
            raise ErrorBoceto("Las líneas son paralelas: no forman ángulo.")
        # Cruce de las rectas: a + s·d1 = c + t·d2. Después, el punto en la base (d1, d2) desde el cruce.
        s = ((c[0] - a[0]) * d2[1] - (c[1] - a[1]) * d2[0]) / det
        o = (a[0] + s * d1[0], a[1] + s * d1[1])
        v = (punto[0] - o[0], punto[1] - o[1])
        k1 = (v[0] * d2[1] - v[1] * d2[0]) / det
        k2 = (d1[0] * v[1] - d1[1] * v[0]) / det
        return (0, 3, 1, 2)[(k1 < 0) * 2 + (k2 < 0)]

    def medir_cota(self, tipo, entidades, modo="centro", cuadrante=None):
        """Valor actual (mm o grados) de una cota sobre la geometría actual: sirve de valor por defecto. `modo`
        ("centro" o "tangente") vale en una distancia con un círculo o arco; `cuadrante` (0..3) en un ángulo."""
        t = [self.tipo_de(e) for e in entidades]
        if tipo == "distancia" and set(t) & set(CIRCULARES):
            return abs(distancia_con_circulo(t, entidades, modo, self.coords, lambda c: self.coords(self.curvas[c].centro),
                                             self.radio, self._extremos_linea))
        if tipo == "distancia" and sorted(t) == ["punto", "spline"]:
            p, s = entidades if t[0] == "punto" else entidades[::-1]
            return mas_cercano(self.primitivas(s)[0], self.coords(p))[1]
        if tipo in ("radio", "diametro"):
            r = self.radio(entidades[0])
            return r if tipo == "radio" else 2 * r
        if tipo == "desfase":
            return self.separacion(*entidades)
        if tipo == "angulo":
            d1, d2 = (self._direccion(e) for e in entidades)
            s1, s2 = signos_cuadrante(cuadrante)
            d1, d2 = (s1 * d1[0], s1 * d1[1]), (s2 * d2[0], s2 * d2[1])
            return math.degrees(math.atan2(abs(d1[0] * d2[1] - d1[1] * d2[0]), d1[0] * d2[0] + d1[1] * d2[1]))
        if tipo == "distancia" and t == ["punto", "linea"]:
            return abs(distancia_punto_recta(self.coords(entidades[0]), *self._extremos_linea(entidades[1])))
        if tipo == "distancia" and t == ["linea", "punto"]:
            return abs(distancia_punto_recta(self.coords(entidades[1]), *self._extremos_linea(entidades[0])))
        if tipo == "distancia" and t == ["linea", "linea"]:
            a = self.coords(self.curvas[entidades[1]].p1)
            return abs(distancia_punto_recta(a, *self._extremos_linea(entidades[0])))
        (x1, y1), (x2, y2) = self._extremos_cota(entidades)
        if tipo == "distancia_h":
            return abs(x2 - x1)
        if tipo == "distancia_v":
            return abs(y2 - y1)
        return math.hypot(x2 - x1, y2 - y1)

    def _extremos_linea(self, lid):
        ln = self.curvas[lid]
        return self.coords(ln.p1), self.coords(ln.p2)

    def _direccion(self, lid):
        (x1, y1), (x2, y2) = self._extremos_linea(lid)
        n = math.hypot(x2 - x1, y2 - y1) or 1.0
        return ((x2 - x1) / n, (y2 - y1) / n)

    def extremo_comun(self, a, b):
        """(punto de a, punto de b) donde se tocan dos curvas por sus extremos (el mismo punto o dos puntos
        con restricción coincidente); None si no comparten un extremo."""
        ea, eb = self.curvas[a].extremos(), self.curvas[b].extremos()
        if not ea or not eb:
            return None
        for p in ea:
            if p in eb:
                return p, p
        for r in self.restricciones.values():
            if r.tipo == "coincidente" and len(r.entidades) == 2:
                p, q = r.entidades
                if p in ea and q in eb:
                    return p, q
                if q in ea and p in eb:
                    return q, p
        return None

    def exigir_disponible(self, tipo, entidades):
        """B-690 (P-169): Perpendicular o Tangente entre una línea y una spline de ajuste sin ningún punto en común están
        apagadas, como en Fusion (las deja en gris). Lo llaman el editor, la API y «Cambiar a», no `agregar_restriccion`:
        copiar, el patrón y el desfase repiten las ya guardadas, que siguen y se resuelven."""
        apagada = deshabilitado.entrada("restriccion.linea_spline")
        if apagada is None or tipo not in ("perpendicular", "tangente") or len(entidades) != 2:
            return
        tipos = [self.tipo_de(e) for e in entidades]
        if sorted(tipos) != ["linea", "spline"]:
            return
        l, s = entidades if tipos[0] == "linea" else entidades[::-1]
        if self.curvas[s].modo != "ajuste":
            return
        extremos, de_spline = set(self.curvas[l].extremos()), set(self.curvas[s].puntos()) | {s}
        if extremos & de_spline or any(r.tipo == "coincidente" and {r.entidades[0]} & extremos and set(r.entidades[1:]) & de_spline
                                       for r in self.restricciones.values()):
            return                              # con un punto en común Fusion no se probó: queda como estaba
        raise ErrorBoceto(f"No disponible: {apagada[0]} ({apagada[1]}).")

    def _contacto_tangente(self, a, b):
        """Punto donde se tocan, tangentes, una línea y una circunferencia o dos circunferencias; None con otras curvas."""
        pa, pb = self.primitivas(a)[0], self.primitivas(b)[0]
        tipos = {pa[0], pb[0]}
        if tipos == {"linea"} or not tipos <= {"linea", *CIRCULARES}:
            return None
        if "linea" in tipos:
            recta, circ = (pa, pb) if pa[0] == "linea" else (pb, pa)
            (x1, y1), (x2, y2), (cx, cy) = recta[2], recta[3], circ[2]
            dx, dy = x2 - x1, y2 - y1
            t = ((cx - x1) * dx + (cy - y1) * dy) / (dx * dx + dy * dy or 1e-18)
            return x1 + t * dx, y1 + t * dy
        (cg, rg), (cc, _r) = sorted((pa[2:4], pb[2:4]), key=lambda p: -p[1])
        d = math.dist(cg, cc)
        return None if d < 1e-12 else (cg[0] + rg * (cc[0] - cg[0]) / d, cg[1] + rg * (cc[1] - cg[1]) / d)

    def deslizar_a_tangente(self, a, b):
        """Antes de agregar una tangente línea-circunferencia con el comando: desliza la línea, sin girarla, hasta tocarla.
        Si no, el solver reparte el salto entre las dos y cambia el radio; en la figura de la ayuda de Fusion el círculo
        no cambia y se mueven las líneas (BOC-52). No toca una línea con un punto fijo ni dos curvas ya encadenadas."""
        l, c = (a, b) if self.tipo_de(a) == "linea" else (b, a)
        if self.tipo_de(l) != "linea" or self.tipo_de(c) not in CIRCULARES or self.extremo_comun(a, b) is not None:
            return
        extremos = self.curvas[l].puntos()
        if self.puntos_fijos().intersection(extremos):
            return
        (x1, y1), (x2, y2) = (self.coords(p) for p in extremos)
        largo = math.hypot(x2 - x1, y2 - y1) or 1e-12
        nx, ny = -(y2 - y1) / largo, (x2 - x1) / largo
        centro = self.primitivas(c)[0][2]
        d = (centro[0] - x1) * nx + (centro[1] - y1) * ny
        paso = d - math.copysign(self.radio(c), d)
        for p in extremos:
            self.puntos[p].x += paso * nx
            self.puntos[p].y += paso * ny

    def tangencias_fuera_del_arco(self):
        """[[a, b]] de las tangentes cuyo contacto cae fuera del tramo dibujado de un arco. El solver las resuelve contra
        el círculo entero: acotar el contacto al barrido movería arcos de bocetos que hoy resuelven bien (BOC-52), así
        que se avisa. Fusion pide que se toquen."""
        salida = []
        for r in self.restricciones.values():
            if r.tipo != "tangente" or self.extremo_comun(*r.entidades) is not None:
                continue
            arcos = [k for k in r.entidades if self.curvas[k].tipo == "arco"]
            contacto = self._contacto_tangente(*r.entidades) if arcos else None
            if contacto is not None and any(mas_cercano(self.primitivas(k)[0], contacto)[1] > 1e-6 for k in arcos):
                salida.append(list(r.entidades))
        return salida

    def vertices_cadena(self, lineas):
        """Vértices en orden de una cadena CERRADA de líneas (para la restricción de polígono)."""
        lados = [tuple(self.curvas[k].puntos()) for k in lineas]
        orden = [lados[0][0], lados[0][1]]
        usados = {0}
        while len(usados) < len(lados):
            sig = next((i for i, (p, q) in enumerate(lados) if i not in usados and orden[-1] in (p, q)), None)
            if sig is None:
                raise ErrorBoceto("Las líneas del polígono no forman cadena.")
            p, q = lados[sig]
            orden.append(q if p == orden[-1] else p)
            usados.add(sig)
        if orden[-1] != orden[0]:
            raise ErrorBoceto("Polígono: las líneas deben cerrar.")
        return orden[:-1]

    # ------------------------------------------------------------ validación
    def _validar_restriccion(self, tipo, entidades):
        if tipo not in TIPOS_RESTRICCION:
            raise ErrorBoceto(f"Tipo de restricción desconocido: {tipo}")
        t = [self.tipo_de(e) for e in entidades]
        abiertas = ("linea", "arco", "arco_elipse", "spline", "conica")
        validas = {
            "coincidente": lambda: len(t) == 2 and t[0] == "punto" and t[1] in ("punto",) + GEOMETRICAS,
            "horizontal": lambda: (t == ["linea"] or t == ["punto", "punto"]),
            "vertical": lambda: (t == ["linea"] or t == ["punto", "punto"]),
            "paralela": lambda: t == ["linea", "linea"],
            # B-586: también línea–spline, como Fusion (la línea queda normal a la spline); arco o círculo no
            "perpendicular": lambda: t == ["linea", "linea"] or sorted(t) == ["linea", "spline"],
            "igual": lambda: (t in (["linea", "linea"], ["punto"] * 4) or (len(t) == 2 and t[0] in CIRCULARES and t[1] in CIRCULARES)
                              or (len(t) == 2 and t[0] in ELIPTICAS and t[1] in ELIPTICAS)),
            "tangente": lambda: (len(t) == 2 and t[0] in GEOMETRICAS and t[1] in GEOMETRICAS and t != ["linea", "linea"]),
            "concentrica": lambda: len(t) == 2 and t[0] in CON_CENTRO and t[1] in CON_CENTRO,
            "punto_medio": lambda: t in (["punto", "linea"], ["punto", "arco"], ["punto"] * 3),
            "fijo": lambda: len(t) >= 1,
            "colineal": lambda: t == ["linea", "linea"],
            # Simetría (como en Fusion): dos puntos, líneas, círculos/arcos, elipses, cónicas o splines
            # (con la misma cantidad de puntos) respecto de una línea.
            "simetrica": lambda: (len(t) == 3 and t[2] == "linea" and
                                  (t[:2] in (["punto", "punto"], ["linea", "linea"], ["conica", "conica"])
                                   or (t[0] in CIRCULARES and t[1] in CIRCULARES)
                                   or (t[0] in ELIPTICAS and t[0] == t[1])
                                   or (t[:2] == ["spline", "spline"] and
                                       len(self.curvas[entidades[0]].pts) == len(self.curvas[entidades[1]].pts)))),
            # Curvatura (G2): una spline (o cónica) y otra curva encadenada (SKT-CONSTRAIN-CURVATURE).
            "curvatura": lambda: (len(t) == 2 and t[0] in abiertas and t[1] in abiertas
                                  and (t[0] in LIBRES or t[1] in LIBRES)),
            "poligono": lambda: len(t) >= 3 and all(x == "linea" for x in t),
            "desfase": lambda: ((len(t) == 4 and all(x in GEOMETRICAS for x in t))
                                or (len(t) == 3 and t[0] in GEOMETRICAS and t[1:] == ["punto", "punto"])
                                or (len(t) == 2 and ((t[0] in ("spline", "elipse", "arco_elipse") and t[1] == "spline")
                                                     or t == ["elipse", "elipse"]))),            # BOC-72: curvas libres
            "patron": lambda: t in (["punto", "punto"], ["punto", "punto", "punto"]),
        }
        if not validas[tipo]():
            raise ErrorBoceto(f"La restricción '{TIPOS_RESTRICCION[tipo]}' no aplica a: {', '.join(t) or 'nada'}.")
        if tipo == "igual" and t == ["punto"] * 4:
            if entidades[0] == entidades[1] or entidades[2] == entidades[3]:
                raise ErrorBoceto("La igualdad pide dos segmentos distintos.")
        elif len(set(entidades)) != len(entidades):
            raise ErrorBoceto("Seleccioná entidades distintas.")
        if tipo == "tangente" and "linea" in t:
            l, c = entidades if t[0] == "linea" else entidades[::-1]
            sobre = {r.entidades[0] for r in self.restricciones.values() if r.tipo == "coincidente" and r.entidades[1:] == [c]}
            if set(self.curvas[l].extremos()) <= sobre:          # B-563: una cuerda no puede ser tangente (colapsaba)
                raise ErrorBoceto("Tangente: soltá un extremo de la línea.")
        if tipo == "curvatura" and self.extremo_comun(*entidades) is None:
            raise ErrorBoceto("Curvatura: dos curvas con un extremo común.")
        if tipo == "poligono":
            self.vertices_cadena(entidades)

    def _validar_cota(self, tipo, entidades):
        if tipo not in TIPOS_COTA:
            raise ErrorBoceto(f"Tipo de cota desconocido: {tipo}")
        t = [self.tipo_de(e) for e in entidades]
        validas = {
            "distancia": lambda: (t in (["punto", "punto"], ["linea"], ["punto", "linea"], ["linea", "punto"],
                                        ["linea", "linea"]) or sorted(t) == ["punto", "spline"]
                                  or (len(t) == 2 and set(t) & set(CIRCULARES)
                                      and set(t) <= {"punto", "linea", *CIRCULARES})),
            "distancia_h": lambda: t in (["punto", "punto"], ["linea"]),
            "distancia_v": lambda: t in (["punto", "punto"], ["linea"]),
            "radio": lambda: t in (["circulo"], ["arco"]),
            "diametro": lambda: t in (["circulo"], ["arco"]),
            "angulo": lambda: t == ["linea", "linea"],
            "desfase": lambda: (t == ["linea", "linea"] or
                                (len(t) == 2 and t[0] in CIRCULARES and t[1] in CIRCULARES) or
                                (len(t) == 2 and t[0] in ("spline", *ELIPTICAS) and t[1] == "spline") or
                                t == ["elipse", "elipse"]),
        }
        if not validas[tipo]():
            raise ErrorBoceto(f"La cota '{TIPOS_COTA[tipo]}' no aplica a: {', '.join(t) or 'nada'}.")
        if tipo == "angulo" and entidades[0] == entidades[1]:
            raise ErrorBoceto("Cota de ángulo: dos líneas distintas.")
        if tipo == "distancia" and len(entidades) == 2 and entidades[0] == entidades[1]:
            raise ErrorBoceto("Cota de distancia: dos entidades distintas.")

    # ------------------------------------------------------------ geometría para perfiles y dibujo
    def primitivas(self, cid):
        """Primitivas 2D de una curva (un texto da varias; las demás, una)."""
        prims = primitivas_entidad(self.curvas[cid], self.coords, curvas=self.curvas)
        if self.objetos:
            from . import objetos
            return objetos.aplicar_a_primitivas(self, cid, prims)
        return prims

    def geometria(self, incluir_construccion=False):
        """Lista de primitivas 2D (formato de cada tupla):
          ('linea', id, (x1, y1), (x2, y2))
          ('circulo', id, (cx, cy), r)
          ('arco', id, (cx, cy), r, ang_ini, ang_fin)                 antihorario, radianes
          ('elipse', id, (cx, cy), a, b, ang)                          a: semieje de `mayor`, ang: su giro
          ('arco_elipse', id, (cx, cy), a, b, ang, t_ini, t_fin)       antihorario en el parámetro t
          ('spline', id, polos, nudos, grado, pesos)                   B-spline sujeta; pesos None = no racional
        Las splines de ajuste, las cónicas y los textos salen como 'spline' (y 'linea'); un texto da
        varias primitivas con el mismo id. La construcción se omite salvo que se pida; los ejes
        (líneas centrales) y la geometría proyectada sí forman perfiles."""
        salida = []
        for c in self.curvas.values():
            if c.construccion and not incluir_construccion:
                continue
            salida.extend(self.primitivas(c.id))
        return salida
