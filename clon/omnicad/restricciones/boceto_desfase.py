"""Boceto 2D: desfase."""
import math

import numpy as np

from .boceto_entidades import (
    Arco, ArcoElipse, Circulo, Elipse, ErrorBoceto, _exigir_radio_positivo, Linea, MEDIDA_MINIMA, _numero, Spline,
    validar_valor_cota,
)
from .boceto_geometria import (
    caja_primitiva, _cruces_circulos, _cruces_recta_circulo, dominio, evaluar_primitiva, interpolar_spline,
    parametros_cuerda, recta_interseccion,
)

# B-710: tolerancia de ajuste del desfase de una curva libre: resfit de ShapeManager (0,001 cm) que Fusion usa al
# aproximar la curva desfasada exacta (informe de ingeniería inversa, ~/coordinador/casos/desfase/).
TOL_DESFASE = 0.01      # mm


def _normales(prim, ts):
    """(C, N) de la primitiva en cada t: punto y normal unitaria a la izquierda del recorrido (arrays n×2)."""
    if prim[0] == "spline" and prim[5] is None:     # B-710: vectorizada; la de puntos sueltos tardaba ~65 µs por t
        from scipy.interpolate import BSpline
        b = BSpline(np.array(prim[3]), np.array(prim[2]), prim[4])
        C, D = b(ts), b(ts, 1)
    else:
        C, D = (np.array(v) for v in zip(*(evaluar_primitiva(prim, float(t), 1) for t in ts), strict=True))
    n = np.hypot(D[:, 0], D[:, 1])
    n[n == 0] = 1.0
    return C, np.column_stack([-D[:, 1] / n, D[:, 0] / n])


def _error_desfase(prim, nuevos, ext, cerrada, sd):
    """B-710: por tramo [ext[i], ext[i+1]] de la madre, cuánto se aleja de la quíntica de ajuste que pasa por `nuevos`
    (la de `agregar_spline`, B-463) la curva desfasada exacta C + sd·N, medido a ¼, ½ y ¾ del tramo (en una punta el
    mayor error no cae en el medio) con el pie sobre la quíntica buscado por Newton."""
    from scipy.interpolate import BSpline
    lista = [tuple(q) for q in nuevos]
    polos, nudos, p = interpolar_spline(lista, 5, cerrada)
    copia = BSpline(np.array(nudos), np.array(polos), p)
    ub = np.array(parametros_cuerda(lista + lista[:1] if cerrada else lista, 5))
    f = np.tile([0.25, 0.5, 0.75], len(ub) - 1)
    lo, hi = np.repeat(ub[:-1], 3), np.repeat(ub[1:], 3)
    u = lo + f * (hi - lo)
    C, N = _normales(prim, np.repeat(ext[:-1], 3) + f * np.repeat(np.diff(ext), 3))
    Q = C + sd * N
    for _ in range(3):
        r, F1, F2 = copia(u) - Q, copia(u, 1), copia(u, 2)
        h = np.sum(F1 * F1, axis=1) + np.sum(r * F2, axis=1)
        u = np.clip(u - np.sum(r * F1, axis=1) / np.where(h > 0, h, np.inf), lo, hi)
    return np.linalg.norm(copia(u) - Q, axis=1).reshape(-1, 3).max(axis=1)


def _puntos_desfase(prim, sd, cerrada, muestras=48):
    """(ts, puntos) de la copia de un desfase libre a distancia firmada `sd`: B-710, como Fusion (aproxima la curva
    desfasada exacta hasta su tolerancia), parte cada tramo que se aleja más de TOL_DESFASE mientras haya. Partir
    unos tramos y otros no puede alejar a los vecinos un rato: con 5 vueltas, a 4 o 5 mm quedaba a 0,012 mm (B-711)."""
    t0, t1, _ = dominio(prim)
    ts = np.linspace(t0, t1, muestras, endpoint=not cerrada)
    C, N = _normales(prim, ts)
    for _ in range(12):
        ext = np.append(ts, t1) if cerrada else ts
        partir = np.flatnonzero(_error_desfase(prim, C + sd * N, ext, cerrada, sd) > TOL_DESFASE)
        if not len(partir) or len(ts) + len(partir) > 8 * muestras:
            break
        ts = np.sort(np.concatenate([ts, (ext[partir] + ext[partir + 1]) / 2]))
        C, N = _normales(prim, ts)
    return ts, C + sd * N


def refinar_desfases(b):
    """B-711: tras resolver, la copia de un desfase de spline con sus t (B-231) que se aleja más de TOL_DESFASE de la
    curva desfasada exacta (la cota cambió y los puntos siguen siendo los de la distancia con que se creó) se rehace
    con los puntos de esa distancia, como Fusion (`postSolveOnOffsetChanges`). Las puntas y los primeros puntos
    conservan su id; no se rehace si otra cosa usa un punto del medio. Devuelve si cambió alguna copia."""
    cambio = False
    for r in list(b.restricciones.values()):
        par = r.datos.get("parametros")
        c = b.curvas.get(r.entidades[1]) if r.tipo == "desfase" and par and len(r.entidades) == 2 else None
        if not isinstance(c, Spline) or c.modo != "ajuste" or c.manijas or any(str(p) not in par for p in c.pts):
            continue
        prim = b.primitivas(r.entidades[0])[0]
        ts = np.array([par[str(p)] for p in c.pts])
        Q = np.array([b.coords(p) for p in c.pts])
        C, N = _normales(prim, ts)
        sd = float(np.median(np.sum((Q - C) * N, axis=1)))
        ext = np.append(ts, dominio(prim)[1]) if c.cerrada else ts
        if np.any(np.diff(ext) <= 0) or not np.any(_error_desfase(prim, Q, ext, c.cerrada, sd) > TOL_DESFASE):
            continue
        ts, nuevos = _puntos_desfase(prim, sd, c.cerrada)
        fin = [] if c.cerrada else c.pts[-1:]
        medio = c.pts[1:len(c.pts) - len(fin)]
        quedan = len(ts) - 1 - len(fin)
        usados = {e for x in (*b.restricciones.values(), *b.cotas.values()) for e in x.entidades}
        usados |= {p for k, otra in b.curvas.items() if k != c.id for p in otra.puntos()}
        if usados & set(medio):
            continue
        ids = c.pts[:1] + medio[:quedan] + [b.agregar_punto(0.0, 0.0) for _ in range(quedan - len(medio))] + fin
        for pid in medio[quedan:]:
            del b.puntos[pid]
        for pid, q in zip(ids, nuevos, strict=True):
            b.puntos[pid].x, b.puntos[pid].y = float(q[0]), float(q[1])
        c.pts = ids
        par.clear()
        par.update({str(p): float(t) for p, t in zip(ids, ts, strict=True)})
        cambio = True
    return cambio


class _Desfase:
    # ------------------------------------------------------------ MODIFICAR: desfase
    def desfasar(self, cid, distancia, punto_lado=None, expresion=None, direccion="un", distancia2=None,
                 expresion2=None, invertir=False, topologia=False, cadena=True, elipse=False, entre=None):
        """Comando Desfase de Fusion entero (Direction + Chain Selection + Match Topology): lo llaman igual la ventana
        (y su vista previa) y la API, así lo que se ve es lo que se crea. `distancia` lleva signo: negativa = al lado
        contrario del que da la positiva (el de `punto_lado`; sin él, afuera en una cadena cerrada y a la izquierda
        del recorrido en una abierta). `invertir` da vuelta todo. `direccion`: "un" lado, "dos" lados o "simetrico"
        (`distancia` a los dos lados, con las dos cotas ligadas: editar una mueve la otra). En "dos" las dos
        distancias llevan signo sobre la MISMA normal, como Fusion (video 2026-10-31: Distancia 1 = 21,35 afuera y
        Distancia 2 = -20,556 adentro): 20 y -10 dan una copia a 20 afuera y otra a 10 adentro; una de las dos
        puede ser 0 (no crea esa copia). `expresion`/`expresion2`: texto de cada distancia SIN signo, para la cota.
        `cadena`=False desfasa solo la curva `cid` (Fusion: sin Chain Selection). `topologia` limita la distancia
        a la mayor que conserva la curva madre. `elipse`: una elipse da otra elipse con los semiejes a ± d y b ± d
        (Fusion, al elegirla cerca de un eje; la distancia varía alrededor) en vez del óvalo a distancia constante.
        Devuelve (ids nuevos, avisos)."""
        if direccion == "dos" and distancia2 is None:
            raise ErrorBoceto("Falta la segunda distancia del desfase.")
        contrario = (distancia < 0) != bool(invertir)
        pasos = [(abs(distancia), contrario, expresion)]
        if direccion == "dos":
            pasos.append((abs(distancia2), (distancia2 < 0) != bool(invertir), expresion2))
            if any(math.isfinite(v) and v == 0 for v, *_r in pasos) and not all(v == 0 for v, *_r in pasos):
                pasos = [p for p in pasos if p[0] != 0]          # una distancia en 0: solo la otra copia
        elif direccion == "simetrico":
            pasos.append((abs(distancia), not contrario, expresion))
        nuevos, avisos, primera = [], [], None
        for valor, inv, texto in pasos:
            if not math.isfinite(valor):
                raise ErrorBoceto("La distancia de desfase no es válida.")
            if topologia:
                tope = self.desfase_con_topologia(cid, valor, punto_lado, inv, cadena, elipse, entre)
                if tope < valor:
                    avisos.append(f"Match Topology: la distancia se limitó de {valor:g} a {tope:.4g} mm para "
                                  "conservar todos los segmentos.")
                    valor, texto = round(tope, 6), None
            ligada = primera if direccion == "simetrico" and texto is not None and not avisos else None   # Match Topology
            nuevos += self.desfase(cid, valor, punto_lado, texto, invertir=inv, cadena=cadena, igual_a=ligada,   # la limitó: no
                                   elipse=elipse, entre=entre)
            if primera is None:
                primera = max(self.cotas)               # la cota que acaba de crear el primer lado
        return nuevos, avisos

    def desfasar_perfil(self, firma, distancia, **opciones):
        """Desfase de un perfil (región cerrada; `firma` = ids de las curvas de su borde, `Perfil.firma`): Fusion
        acepta "una curva, una cadena o un perfil". Se desfasan todos sus contornos, el exterior y los de sus
        huecos, de modo que la región crezca con una distancia positiva (el hueco se achica). `opciones` son las de
        `desfasar` (menos `cadena`, que aquí siempre es verdadera). Devuelve (ids nuevos, avisos)."""
        opciones["cadena"], opciones["entre"] = True, set(firma)       # el contorno no se corta donde otra figura lo toca
        contornos, vistas = [], set()
        for cid in sorted(firma):
            if cid in vistas or cid not in self.curvas:
                continue
            ids = [k for k, _ in self.cadena(cid, opciones["entre"])[0]]
            vistas.update(ids)
            cajas = [caja_primitiva(p) for k in ids for p in self.primitivas(k)]
            area = ((max(c[2] for c in cajas) - min(c[0] for c in cajas))
                    * (max(c[3] for c in cajas) - min(c[1] for c in cajas)))
            contornos.append((area, cid))
        if not contornos:
            raise ErrorBoceto("El perfil no tiene contornos que desfasar.")
        exterior = max(contornos)[1]
        invertir, nuevos, avisos = bool(opciones.pop("invertir", False)), [], []
        for _area, cid in sorted(contornos, key=lambda c: c[1] != exterior):
            n, a = self.desfasar(cid, distancia, invertir=invertir != (cid != exterior), **opciones)
            nuevos += n
            avisos += a
        return nuevos, avisos

    def desfase(self, cid, distancia, punto_lado=None, expresion=None, invertir=False, cadena=True, igual_a=None,
                elipse=False, entre=None):
        """Desfase (SKT-OFFSET) de la cadena conectada a `cid` (o solo de `cid` con `cadena`=False): curvas
        paralelas a `distancia`, con las esquinas resueltas por intersección, la restricción de desfase y su cota.
        Por defecto, una cadena cerrada se desfasa hacia afuera (y una abierta, a la izquierda de su recorrido);
        `punto_lado` elige el lado e `invertir` pasa al lado contrario del que tocaba, igual que una `distancia`
        negativa. `igual_a`: id de otra cota de desfase a la que queda ligada la nueva (el Simétrico). Rechaza,
        diciendo por qué, lo que deja un radio o un segmento en cero o al revés. Devuelve los ids nuevos."""
        if not math.isfinite(distancia):
            raise ErrorBoceto("La distancia de desfase no es válida.")
        if distancia == 0:
            raise ErrorBoceto("La distancia de desfase es cero.")
        validar_valor_cota("desfase", abs(distancia))
        if distancia < 0:
            distancia, invertir = -distancia, not invertir
        c0 = self.curvas[cid]
        datos = {} if igual_a is None else {"igual_a": igual_a}
        if isinstance(c0, Elipse) and elipse:
            return [self._desfase_elipse(cid, distancia, punto_lado, invertir, expresion, datos)]
        if isinstance(c0, (Spline, Elipse, ArcoElipse)):
            return [self._desfase_libre(cid, distancia, punto_lado, invertir, expresion=expresion, datos=datos)]
        cadena, cerrada = self.cadena(cid, entre) if cadena else ([(cid, False)], False)
        if len(cadena) == 1 and isinstance(c0, Circulo):
            r = c0.radio
            fuera = (punto_lado is None or math.dist(punto_lado, self.coords(c0.centro)) > r) != bool(invertir)
            if not fuera:
                _exigir_radio_positivo(r, distancia, "del círculo")
            nuevo = self.agregar_circulo(c0.centro, r + distancia if fuera else r - distancia, c0.construccion)
            self.agregar_cota("desfase", [cid, nuevo], expresion or _numero(distancia), datos)
            return [nuevo]
        if any(not isinstance(self.curvas[k], (Linea, Arco)) for k, _ in cadena):
            raise ErrorBoceto("El desfase funciona con curvas del boceto.")
        elems = []
        for k, inv in cadena:
            c = self.curvas[k]
            ini, fin = c.extremos()
            a, b = (fin, ini) if inv else (ini, fin)
            elems.append((k, inv, c, self.coords(a), self.coords(b), a, b))

        def izquierda_de(elem, q):
            k, inv, c, a, b, *_r = elem
            if isinstance(c, Linea):
                return (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0]) > 0
            dentro = math.dist(q, self.coords(c.centro)) < self.radio(k)
            return dentro != inv
        if punto_lado is not None:
            ref = next(e for e in elems if e[0] == cid)
            s = 1.0 if izquierda_de(ref, punto_lado) else -1.0
        elif cerrada:
            pts = []
            for k, inv, c, a, b, *_r in elems:
                pts.append(a)
                if isinstance(c, Arco):
                    prim = self.primitivas(k)[0]
                    pts.append(evaluar_primitiva(prim, dominio(prim)[1] / 2)[0])
            area = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, pts[1:] + pts[:1], strict=True))
            s = -1.0 if area > 0 else 1.0
        else:
            s = 1.0
        if invertir:
            s = -s
        dd = s * distancia
        portadoras = []      # (tipo, datos) de cada curva desfasada + sus extremos desfasados
        for k, inv, c, a, b, *_r in elems:
            if isinstance(c, Linea):
                L = math.dist(a, b)
                n = (-(b[1] - a[1]) / L, (b[0] - a[0]) / L)
                a2, b2 = (a[0] + n[0] * dd, a[1] + n[1] * dd), (b[0] + n[0] * dd, b[1] + n[1] * dd)
                portadoras.append((("recta", a2, ((b[0] - a[0]) / L, (b[1] - a[1]) / L)), a2, b2))
            else:
                C, R = self.coords(c.centro), self.radio(k)
                r2 = R + dd if inv else R - dd
                if r2 <= MEDIDA_MINIMA:
                    _exigir_radio_positivo(R, R - r2, "de un arco de la cadena")
                rad = lambda q, C=C, R=R, r2=r2: (C[0] + (q[0] - C[0]) * r2 / R, C[1] + (q[1] - C[1]) * r2 / R)  # noqa: E731
                portadoras.append((("circ", C, r2), rad(a), rad(b)))
        m = len(elems)
        esquinas = []
        for i in range(m if cerrada else m - 1):
            j = (i + 1) % m
            fin_i, ini_j = portadoras[i][2], portadoras[j][1]
            if math.dist(fin_i, ini_j) < 1e-9:
                esquinas.append(fin_i)
                continue
            g1, g2 = portadoras[i][0], portadoras[j][0]
            if g1[0] == "recta" and g2[0] == "recta":
                cands = [q for q in [recta_interseccion(g1[1], g1[2], g2[1], g2[2])] if q]
            elif g1[0] == "recta":
                cands = _cruces_recta_circulo(g1[1], g1[2], g2[1], g2[2])
            elif g2[0] == "recta":
                cands = _cruces_recta_circulo(g2[1], g2[2], g1[1], g1[2])
            else:
                cands = _cruces_circulos(g1[1], g1[2], g2[1], g2[2])
            J = elems[i][4]
            esquinas.append(min(cands, key=lambda q, J=J: math.dist(q, J)) if cands else
                            ((fin_i[0] + ini_j[0]) / 2, (fin_i[1] + ini_j[1]) / 2))
        for i, (_, _, c, *_r) in enumerate(elems):
            if isinstance(c, Linea):
                a2 = esquinas[i - 1] if cerrada or i > 0 else portadoras[0][1]
                b2 = esquinas[i] if cerrada or i < m - 1 else portadoras[-1][2]
                direccion = portadoras[i][0][2]  # unitaria, en el sentido de recorrido original
                largo = (b2[0] - a2[0]) * direccion[0] + (b2[1] - a2[1]) * direccion[1]
                if largo <= 1e-9:
                    raise ErrorBoceto(f"Con {distancia:g} mm, un segmento queda en cero.")
        pids = [self.agregar_punto(*q) for q in esquinas]
        if cerrada:
            extremos = [(pids[i - 1], pids[i]) for i in range(m)]
        else:
            ini_p, fin_p = self.agregar_punto(*portadoras[0][1]), self.agregar_punto(*portadoras[-1][2])
            todos = [ini_p] + pids + [fin_p]
            extremos = [(todos[i], todos[i + 1]) for i in range(m)]
        nuevos = []
        grupo = self._siguiente
        for (k, inv, c, *_r), (pa, pb) in zip(elems, extremos, strict=True):
            if isinstance(c, Linea):
                nid = self.agregar_linea(pb, pa, c.construccion) if inv else self.agregar_linea(pa, pb, c.construccion)
                self.agregar_restriccion("paralela", [k, nid])
            else:
                nid = (self.agregar_arco_centro(c.centro, pb, pa, c.construccion) if inv
                       else self.agregar_arco_centro(c.centro, pa, pb, c.construccion))
            nuevos.append(nid)
        # B-246: las tangencias entre curvas de la cadena (la ranura: línea con arco) pasan a la copia; sin ellas
        # sus esquinas quedaban libres de correrse por las líneas (dof 4), como Fusion no deja.
        nuevo_de = {k: nid for (k, *_r), nid in zip(elems, nuevos, strict=True)}
        for r in [r for r in self.restricciones.values() if r.tipo == "tangente" and set(r.entidades) <= set(nuevo_de)]:
            self.agregar_restriccion("tangente", [nuevo_de[e] for e in r.entidades])
        k0, n0 = elems[0][0], nuevos[0]
        for (k, *_r), nid in list(zip(elems, nuevos, strict=True))[1:]:
            self.agregar_restriccion("desfase", [k0, n0, k, nid], {"grupo": grupo})
        if not cerrada:
            self.agregar_restriccion("desfase", [elems[0][0], elems[0][5], extremos[0][0]], {"grupo": grupo})
            self.agregar_restriccion("desfase", [elems[-1][0], elems[-1][6], extremos[-1][1]], {"grupo": grupo})
        self.agregar_cota("desfase", [k0, n0], expresion or _numero(distancia), datos)
        return nuevos

    def desfase_con_topologia(self, cid, distancia, punto_lado=None, invertir=False, cadena=True, elipse=False,
                              entre=None):
        """Match Topology de Fusion: la mayor distancia ≤ `distancia` con la que el desfase conserva la topología de la
        curva madre (ningún segmento se anula o se invierte, ningún arco ni círculo llega a radio cero, la spline no
        se pliega). Busca el tope por bisección sobre copias y se queda un 0,1 % antes para no dejar un segmento
        de largo cero. Devuelve la distancia que hay que usar."""
        def sirve(d):
            try:
                self.copia().desfase(cid, d, punto_lado, invertir=invertir, cadena=cadena, elipse=elipse, entre=entre)
            except ErrorBoceto:
                return False
            return True
        if sirve(distancia):
            return distancia
        bajo, alto = 0.0, distancia
        for _ in range(40):
            medio = (bajo + alto) / 2
            bajo, alto = (medio, alto) if sirve(medio) else (bajo, medio)
        if bajo <= MEDIDA_MINIMA:
            raise ErrorBoceto("Ningún desfase deja la curva entera.")
        return bajo * 0.999

    def _desfase_libre(self, cid, d, punto_lado, invertir, muestras=48, expresion=None, datos=None):
        """Offset de Fusion para spline/elipse: spline de ajuste con cota asociativa sobre la normal de la madre.
        La cota restringe sus puntos de ajuste; entre ellos la spline interpola el desfase."""
        c = self.curvas[cid]
        prim = self.primitivas(cid)[0]
        t0, t1, _ = dominio(prim)
        cerrada = isinstance(c, Elipse) or (isinstance(c, Spline) and c.cerrada)

        ts = np.linspace(t0, t1, muestras, endpoint=not cerrada)
        C, N = _normales(prim, ts)
        if punto_lado is not None:
            i = int(np.argmin(np.hypot(*(C - punto_lado).T)))
            s = 1.0 if N[i] @ np.subtract(punto_lado, C[i]) > 0 else -1.0
        elif cerrada:
            s = -1.0 if np.sum(C[:, 0] * np.roll(C[:, 1], -1) - np.roll(C[:, 0], -1) * C[:, 1]) > 0 else 1.0
        else:
            s = 1.0
        if invertir:
            s = -s
        ts, nuevos = _puntos_desfase(prim, s * d, cerrada, muestras)    # la cota asociativa: un t por punto
        densos = _normales(prim, np.linspace(t0, t1, 4 * muestras, endpoint=not cerrada))[0]
        if np.any(np.linalg.norm(nuevos[:, None] - densos[None], axis=2).min(axis=1) < 0.9 * d):
            raise ErrorBoceto("Desfase mayor que el radio: se pliega.")
        nuevo = self.agregar_spline([tuple(map(float, q)) for q in nuevos], "ajuste", 3, cerrada,
                                    construccion=c.construccion)
        # B-231: cada punto de ajuste queda en su parámetro de la madre (clave texto: sobrevive al JSON). Absoluto y no
        # fracción: recortar la madre conserva su parametrización.
        ids = self.curvas[nuevo].pts
        parametros = {str(p): float(t) for p, t in zip(ids, ts, strict=True)} if len(ids) == len(ts) else None
        self._atar_desfase_libre(cid, nuevo, s, expresion or _numero(d), datos, parametros)
        return nuevo

    def _atar_desfase_libre(self, madre, copia, lado, expresion, datos, parametros=None):
        """BOC-72: la copia de una curva libre queda atada por una restricción de desfase (distancia común y libre) y
        además por su cota; borrar la cota (Fusion) conserva la relación y libera la distancia. `parametros`
        ({id de punto como texto: t de la madre}) ata cada punto de la copia a su lugar (B-231)."""
        self.agregar_restriccion("desfase", [madre, copia], {"grupo": self._siguiente, "lado": lado}
                                 | ({"parametros": parametros} if parametros else {}))
        self.agregar_cota("desfase", [madre, copia], expresion, {"lado": lado, **(datos or {})})

    def _desfase_elipse(self, cid, d, punto_lado, invertir, expresion, datos):
        """Desfase de una elipse que da otra elipse concéntrica de semiejes a ± d y b ± d (Fusion, elegida cerca de
        un eje). `lado` +1 = la mayor (afuera); `punto_lado` lo elige con un punto; `invertir` lo da vuelta."""
        c = self.curvas[cid]
        (cx, cy), (mx, my) = self.coords(c.centro), self.coords(c.mayor)
        a, b = math.hypot(mx - cx, my - cy), c.radio_menor
        if punto_lado is None:
            s = 1.0
        else:
            ca, sa = (mx - cx) / a, (my - cy) / a
            dx, dy = punto_lado[0] - cx, punto_lado[1] - cy
            s = 1.0 if (((dx * ca + dy * sa) / a) ** 2 + ((-dx * sa + dy * ca) / b) ** 2) > 1 else -1.0
        s = -s if invertir else s
        if min(a, b) + s * d <= MEDIDA_MINIMA:
            _exigir_radio_positivo(min(a, b), d, "menor de la elipse")
        u = ((mx - cx) / a, (my - cy) / a)
        mayor = self.agregar_punto(cx + u[0] * (a + s * d), cy + u[1] * (a + s * d))
        nuevo = self._agregar_curva(Elipse(self._nuevo_id(), c.centro, mayor, b + s * d, c.construccion))
        self._atar_desfase_libre(cid, nuevo, s, expresion or _numero(d), datos)
        return nuevo

    def soltar_desfase(self, cid, conservar_cota=False):
        """Suelta la asociación de un desfase (Fusion: borrar el glifo de desfase): quita las restricciones de
        desfase y de paralelismo entre la curva original y su copia, y la cota (salvo `conservar_cota`). Las
        curvas quedan. En curvas libres, conservar la cota la convierte en referencia para desligar la copia.
        `cid` puede ser la original o la copia; si la original tiene varios desfases, los suelta todos."""
        cotas = [k for k in self.cotas.values() if k.tipo == "desfase" and cid in k.entidades]
        semilla = {cid}.union(*(k.entidades for k in cotas))
        grupos = {r.datos.get("grupo") for r in self.restricciones.values()
                  if r.tipo == "desfase" and semilla & set(r.entidades)}
        viejas = [r for r in self.restricciones.values() if r.tipo == "desfase" and r.datos.get("grupo") in grupos]
        if not viejas and not cotas:
            raise ErrorBoceto(f"La entidad {cid} no es un desfase.")
        pares = {frozenset(k.entidades) for k in cotas}
        for r in viejas:
            if len(r.entidades) == 4:
                pares |= {frozenset(r.entidades[:2]), frozenset(r.entidades[2:])}
        borrar = [r.id for r in viejas] + [r.id for r in self.restricciones.values()
                                           if r.tipo == "paralela" and frozenset(r.entidades) in pares]
        borrar += [] if conservar_cota else [k.id for k in cotas]
        for i in borrar:
            self.eliminar(i)
        if conservar_cota:
            for k in cotas:
                if isinstance(self.curvas[k.entidades[0]], (Spline, Elipse, ArcoElipse)):
                    k.referencia = True
