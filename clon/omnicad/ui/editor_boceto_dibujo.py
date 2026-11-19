"""LienzoDibujoMixin: métodos del lienzo por tema."""

from .editor_boceto_comun import (pasos_segun_zoom, 
    Boceto,
    COMANDO_PROYECCION,
    CONFLICTO,
    Conica,
    ErrorBoceto,
    ICONO_RESTRICCION,
    LADO_SIMBOLO,
    NOMBRES_ENTIDAD,
    PATRON,
    QColor,
    QFontMetricsF,
    QPainter,
    QPen,
    QPointF,
    QPolygonF,
    QRectF,
    Qt,
    REFERENCIA,
    RELACION_ENTRE_DOS,
    SPLINES,
    Spline,
    TRANSFORMAR,
    Texto,
    VIOLETA,
    _es_numero,
    _numero,
    _tenido,
    _unitario,
    _vertices_poligono,
    dibujar_casilla,
    dominio,
    evaluar_primitiva,
    formato,
    mas_cercano,
    math,
    np,
    puntos_primitiva,
    temas,
    vertices_estrella,
)


class _Ocupadas:
    """Cajas ya ocupadas por textos e íconos, en una grilla de celdas: `choca` mira solo las de las celdas que toca la
    caja (antes, todas contra todas: 1 millón de comparaciones por arrastre con 100 cotas)."""
    CELDA = 64.0                                       # px

    def __init__(self, cajas):
        self.celdas = {}
        for caja in cajas:
            self.agregar(caja)

    def _claves(self, caja):
        c = self.CELDA
        if not all(map(math.isfinite, (caja.left(), caja.right(), caja.top(), caja.bottom()))):
            return                                     # NaN o infinito: no ocupa ni choca (como `intersects`)
        for i in range(math.floor(caja.left() / c), math.floor(caja.right() / c) + 1):
            for j in range(math.floor(caja.top() / c), math.floor(caja.bottom() / c) + 1):
                yield i, j

    def agregar(self, caja):
        for k in self._claves(caja):
            self.celdas.setdefault(k, []).append(caja)

    def choca(self, caja):
        return any(caja.intersects(o) for k in self._claves(caja) for o in self.celdas.get(k, ()))


def icono(*args, **kwargs):
    from . import editor_boceto
    return editor_boceto.icono(*args, **kwargs)


class LienzoDibujoMixin:
    def _circulo_vista(self, centro, r):
        """Polilínea de la vista previa de un círculo, con las muestras que pide el zoom (B-661)."""
        n = pasos_segun_zoom(("circulo", None, centro, r), self.px_por_mm())
        return [(centro[0] + r * math.cos(2 * math.pi * i / n), centro[1] + r * math.sin(2 * math.pi * i / n))
                for i in range(n + 1)]

    def paintEvent(self, _):
        self._camara()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.visor is None:
            self._fondo_2d(p)
        elif self.mostrar["rejilla"]:
            self._numeros_rejilla(p)
        res = self.resultado
        determinadas = res.determinadas if res is not None else frozenset()
        fijos = self.b.puntos_fijos()
        # lo pegado al origen se ve como restringido (blanco), no como "fijo" (verde), igual que en Fusion
        en_origen = {e for r in self.b.restricciones.values() if r.tipo == "fijo" and r.datos.get("origen")
                     for e in r.entidades}
        fijos_verdes = fijos - en_origen
        en_conflicto = self.geometria_en_conflicto(esperar=False) if res is not None and not res.ok else set()
        self._dibujar_perfiles(p)
        ocultos = set()
        from ..restricciones import objetos
        internas = objetos.indice(self.b) if self.b.objetos else {}
        puntos_internos = {p for cid in internas for p in self.b.curvas[cid].puntos()}
        solo_auto, puntos_auto = self.b.ocultos_por_proyeccion_auto()    # no se dibujan (como Fusion)
        puntos_auto = puntos_auto | self._vertices_virtuales_estrella()
        quietas = determinadas | en_origen        # RS-X3: una vez (por curva era cuadrático con miles de curvas)
        capa = []                                 # lo que se dibuja de cada curva: ver `_dibujar_capa_curvas`
        for c in self.b.curvas.values():
            if c.id in internas:
                continue
            if c.id == self._texto_oculto or c.id in solo_auto:
                continue                     # se está editando: se ve la vista previa en vivo
            if not self._visible(c):
                ocultos.update(c.puntos())
                continue
            color, ancho = self._color_curva(c, quietas, fijos_verdes, en_conflicto)
            if self._brillantes is not None and c.id not in self._brillantes:
                color = QColor(color)
                color.setAlphaF(0.2)
            estilo = Qt.DashLine if c.construccion else Qt.DashDotLine if c.eje else Qt.SolidLine
            extra = None
            if isinstance(c, Spline) and c.modo == "control" and not c.proyectada:
                extra = ("marco", tuple(self.b.coords(q) for q in c.pts))
            elif isinstance(c, Conica) and c.id in self.seleccion:
                extra = ("guias", self.b.coords(c.inicio), self.b.coords(c.vertice), self.b.coords(c.fin))
            capa.append((c.id, color.rgba(), ancho, estilo, tuple(self._polilineas(c)), extra))
        cuadros = []                              # los puntos: (x, y, borde, relleno), en la misma imagen que las curvas
        if self.mostrar["puntos"]:
            visibles = {q for c in self.b.curvas.values() if self._visible(c) for q in c.puntos()}
            vivos = None if self._brillantes is None else self._brillantes | {
                q for c in self.b.curvas.values() if c.id in self._brillantes for q in c.puntos()}
            ancho, alto = self.width() + 8, self.height() + 8
            oscuro = self._oscuro()                # los colores, una vez (RS-X3: crearlos por punto costaba más que dibujar)
            celeste, verde = QColor(0, 180, 255).rgba(), QColor(70, 200, 100).rgba()
            quieto = (QColor(245, 245, 245) if oscuro else QColor(20, 20, 20)).rgba()
            libre = (QColor(90, 160, 255) if oscuro else QColor(25, 90, 200)).rgba()
            blanco, tenue = QColor(255, 255, 255).rgba(), round(0.2 * 255) << 24
            for pt in self.b.puntos.values():
                if pt.id in puntos_internos:
                    continue
                if pt.id in ocultos and pt.id not in visibles or (pt.proyectado and not self.mostrar["proyectadas"]) \
                        or pt.id in puntos_auto:
                    continue
                q = self.a_px(pt.x, pt.y)
                if not (-8 <= q.x() <= ancho and -8 <= q.y() <= alto):
                    continue                          # fuera de la pantalla: no se dibuja
                if pt.id in self.seleccion or pt.id in self.picks:
                    color = relleno = celeste
                elif pt.proyectado:
                    color = relleno = VIOLETA.rgba()
                elif pt.id in en_conflicto:
                    color = relleno = CONFLICTO.rgba()
                elif pt.id in fijos_verdes:
                    color = relleno = verde
                elif pt.id in determinadas or pt.id in en_origen:
                    color = relleno = quieto
                else:
                    color, relleno = libre, blanco
                if vivos is not None and pt.id not in vivos:          # el alfa de setAlphaF(0.2)
                    color, relleno = color & 0xFFFFFF | tenue, relleno & 0xFFFFFF | tenue
                cuadros.append((q.x(), q.y(), color, relleno))
        self._dibujar_capa_curvas(p, capa, cuadros)
        self._zonas_glifos = self._dibujar_glifos(p) if self.mostrar["restricciones"] else {}
        if not self.mostrar["restricciones"]:
            self._zonas_glifos_extra = []
        if self.herramienta == "seleccionar":
            self._dibujar_casillas_patron(p)
        self._trazos_cotas, self._fondos_cotas = {}, {}   # con las cotas ocultas no se agarra nada
        self._zonas_cotas = self._dibujar_cotas(p) if self.mostrar["cotas"] else {}
        self._dibujar_previa_auto(p)
        self._dibujar_marco(p)
        self.objetos.dibujar(p)
        if self._zona_sobre is not None:                # la cota ya se resalta al dibujarse; el glifo, acá
            cajas = [self._zonas_glifos[self._zona_sobre]] if self._zona_sobre in self._zonas_glifos else []
            cajas += [c for i, c in self._zonas_glifos_extra if i == self._zona_sobre]
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(255, 170, 40), 2))
            for rect in cajas:
                p.drawRect(rect.adjusted(-3, -3, 3, 3))
        p.save()
        if self._previa_texto is not None:
            p.setTransform(self.objetos.transformacion_texto(), True)
        self._dibujar_previa(p)
        p.restore()
        self._dibujar_campos_vivos(p)
        if self._ventana is not None:
            a, b = self._ventana
            relleno, borde = self.colores_ventana(a, b)
            p.setPen(QPen(borde, 1) if borde is not None else Qt.NoPen)
            p.setBrush(relleno)
            p.drawRect(QRectF(a, b).normalized())
        p.end()
        self._notificar_seleccion()          # lo elegido pudo cambiar de tamaño o desaparecer

    def _dibujar_perfiles(self, p):
        """BOC-23: los perfiles elegidos con clic, rellenos en celeste translúcido (como el resaltado de Fusion)."""
        if not self.perfiles_sel:
            return
        from ..nucleo import geometria as geo
        pl = self._plano_perfiles()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 180, 255, 70))
        for perfil in self.perfiles_seleccionados():
            tris = np.asarray(geo.teselar(perfil.cara)[0], float).reshape(-1, 3) - pl.origen
            uv = np.column_stack([tris @ pl.u, tris @ pl.v]).reshape(-1, 3, 2)
            for tri in uv:
                p.drawPolygon(QPolygonF(self._poli_px([tuple(q) for q in tri])))
        p.setBrush(Qt.NoBrush)

    def _casillas_patron(self):
        """[(id del patrón, índice de copia, rectángulo en px, suprimida)] de los patrones que tienen algo elegido: una
        casilla junto a cada copia, marcada si existe (Fusion: se desmarca para suprimir esa instancia). Las suprimidas
        no tienen geometría: su lugar sale de la transformación del patrón aplicada al centro de lo original."""
        from .asas_boceto import centro_de
        elegidas, casillas = set(self.seleccion), []
        for r in self.b.patrones:
            copias = {i for lista in r["copias"].values() for i in lista}
            if not elegidas & (set(r["ids"]) | copias):
                continue
            try:
                trans = self.b._trans_rectangular(r["params"]) if r["tipo"] == "rectangular" \
                    else self.b._trans_circular(r["params"])[0]
            except (ErrorBoceto, KeyError):         # una línea de dirección o un centro que ya no existe: sin casillas
                continue
            centro = centro_de(self, r["ids"])
            for i, (fn, *_) in enumerate(trans):
                q = self.a_px(*fn(centro))
                casillas.append((r["id"], i, QRectF(q.x() + 6, q.y() - 18, 12, 12), i in r["suprimidos"]))
        return casillas

    def _dibujar_casillas_patron(self, p):
        p.save()
        for _pid, _i, caja, suprimida in self._casillas_patron():
            dibujar_casilla(p, caja, suprimida, self._oscuro())
        p.restore()

    def _clic_casilla_patron(self, pos):
        """Clic en la casilla de una copia: la suprime o la vuelve a crear (un paso de deshacer). True si la tocó."""
        for pid, i, caja, _suprimida in self._casillas_patron():
            if not caja.adjusted(-3, -3, 3, 3).contains(pos):
                continue
            self._alternar_copia_patron(pid, i)
            return True
        return False

    def _alternar_copia_patron(self, pid, i):
        registro = next(r for r in self.b.patrones if r["id"] == pid)
        nuevos, perdidas = set(registro["suprimidos"]) ^ {i}, []
        ok = self.aplicar_cambio(lambda: perdidas.extend(self.b.editar_patron(pid, suprimidos=nuevos)), anclar=False)
        if ok and perdidas:
            self.mensaje.emit("Se borraron porque su copia ya no existe: " + ", ".join(perdidas))

    def _dibujar_glifos(self, p):
        """Un símbolo por restricción junto a su geometría (Fusion: uno en cada curva de una relación entre dos).
        Devuelve {id: caja} con el principal; los de la segunda curva quedan en `_zonas_glifos_extra`."""
        zonas, cuenta, grupos = {}, {}, set()
        self._zonas_glifos_extra = extras = []
        en_conflicto = set(self.conflictos_sin_esperar()) if self.resultado is not None and not self.resultado.ok else set()
        p.setPen(QPen(QColor(150, 150, 150), 1))
        from ..restricciones import objetos
        internas = set(objetos.indice(self.b))
        internas.update(p for cid in list(internas) for p in self.b.curvas[cid].puntos())
        for r in self.b.restricciones.values():
            if set(r.entidades) <= internas:
                continue
            if r.datos.get("origen"):                 # pegado al origen: Fusion no le dibuja ícono aparte
                continue
            grupo = r.datos.get("grupo")
            if grupo is not None and r.id not in en_conflicto:    # desfase, patrón y estrella: un glifo por grupo
                if (r.tipo, grupo) in grupos:
                    continue
                grupos.add((r.tipo, grupo))
            ent = r.entidades[-1] if r.tipo in ("coincidente", "punto_medio") else r.entidades[0]
            if r.tipo == "simetrica":
                ent = r.entidades[2]
            elif r.tipo == "desfase" and len(r.entidades) == 4:
                ent = r.entidades[1]
            elif r.tipo == "patron":
                ent = r.entidades[-1] if len(r.entidades) == 3 else r.entidades[1]
            destinos = [ent] + ([r.entidades[1]] if r.tipo in RELACION_ENTRE_DOS else [])
            for j, ent in enumerate(destinos):
                if ent not in self.b.puntos and ent not in self.b.curvas:
                    continue
                k = cuenta.get(ent, 0)
                cuenta[ent] = k + 1
                oscuro = self._oscuro()
                lado = LADO_SIMBOLO
                q = self._ancla(ent) + QPointF(8 + (lado + 2) * k, -18)
                caja = QRectF(round(q.x() - lado / 2), round(q.y() - lado / 2), lado, lado)    # en píxeles enteros: nítido
                seleccionada = r.id in self.seleccion
                if oscuro:
                    p.setPen(QPen(QColor(110, 116, 128), 1))
                    p.setBrush(QColor(0, 180, 255) if seleccionada else QColor(58, 63, 75, 210))
                else:
                    p.setPen(QPen(QColor(150, 150, 150), 1))
                    p.setBrush(QColor(0, 180, 255) if seleccionada else QColor(250, 250, 250, 230))
                if r.id in en_conflicto:                    # BOC-7: el glifo que choca, con borde rojo
                    p.setPen(QPen(CONFLICTO, 2))
                p.drawRoundedRect(caja, 2, 2)
                pm = icono(ICONO_RESTRICCION.get(r.tipo, "")).pixmap(lado - 4, lado - 4)    # al tamaño justo, sin achicar
                if oscuro and r.tipo not in ("fijo", "punto_medio"):
                    pm = _tenido(pm, QColor(225, 228, 235))     # sobre el fondo oscuro, glifo claro como Fusion
                p.drawPixmap(int(caja.x()) + 2, int(caja.y()) + 2, pm)
                if j == 0:
                    zonas[r.id] = caja
                else:
                    extras.append((r.id, caja))
        p.setBrush(Qt.NoBrush)
        return zonas

    def _dibujar_previa_auto(self, p):
        if not self.previa_auto:
            return
        cuenta = {}
        lado = LADO_SIMBOLO
        p.save()
        p.setPen(QPen(VIOLETA, 2))
        p.setBrush(Qt.NoBrush)
        p.setFont(temas.qfont_cotas(9))
        for s in self.previa_auto:
            if not s.entidades or any(e not in self.b.puntos and e not in self.b.curvas for e in s.entidades):
                continue
            ent = s.entidades[0]
            if s.clase == "restriccion":
                if s.tipo in ("coincidente", "punto_medio"):
                    ent = s.entidades[-1]
                elif s.tipo == "simetrica":
                    ent = s.entidades[2]
                elif s.tipo == "desfase" and len(s.entidades) == 4:
                    ent = s.entidades[1]
                elif s.tipo == "patron":
                    ent = s.entidades[-1] if len(s.entidades) == 3 else s.entidades[1]
            k = cuenta.get(ent, 0)
            cuenta[ent] = k + 1
            q = self._ancla(ent)
            if s.clase == "restriccion":
                q += QPointF(8 + (lado + 2) * k, -18)
                caja = QRectF(q.x() - lado / 2, q.y() - lado / 2, lado, lado)
                p.drawRoundedRect(caja, 2, 2)
                pm = _tenido(icono(ICONO_RESTRICCION.get(s.tipo, "")).pixmap(lado - 4, lado - 4), VIOLETA)
                p.drawPixmap(int(caja.x()) + 2, int(caja.y()) + 2, pm)
            elif s.clase == "cota":
                prefijo = {"radio": "R", "diametro": "⌀"}.get(s.tipo, "")
                unidad = "°" if s.tipo == "angulo" else ""
                texto = f"{prefijo}{formato.numero(s.valor, angular=s.tipo == 'angulo')}{unidad}"
                p.drawText(q + QPointF(10, 18 + 18 * k), texto)
        p.restore()

    def _flecha(self, p, punta, desde):
        ang = math.atan2(punta.y() - desde.y(), punta.x() - desde.x())
        p.drawPolygon(QPolygonF([punta, punta - QPointF(math.cos(ang - 0.35) * 7, math.sin(ang - 0.35) * 7),
                                 punta - QPointF(math.cos(ang + 0.35) * 7, math.sin(ang + 0.35) * 7)]))

    @staticmethod
    def _auxiliar_cota(desde, hasta):
        """Línea auxiliar como Fusion: 3 px de hueco desde la geometría y 4 px pasada la línea de cota."""
        dx, dy = hasta.x() - desde.x(), hasta.y() - desde.y()
        largo = math.hypot(dx, dy)
        if largo <= 4:
            return None
        ux, uy = dx / largo, dy / largo
        return (QPointF(desde.x() + ux * 3, desde.y() + uy * 3),
                QPointF(hasta.x() + ux * 4, hasta.y() + uy * 4))

    @staticmethod
    def _texto_cota(c, valor):
        """Lo que se lee en la cota: el valor con su prefijo; entre paréntesis si es de referencia (driven) y con
        «fx:» delante si sale de una expresión (Fusion). Con la unidad: «20 mm» (la del documento) o «90°»."""
        angular = c.tipo == "angulo"
        unidad = "°" if angular else f" {formato.sufijo()}"
        prefijo = {"radio": "R", "diametro": "⌀"}.get(c.tipo, "⌀" if c.datos.get("diametral") else "")
        texto = f"{prefijo}{formato.numero(valor if angular else formato.longitud(valor), angular=angular)}{unidad}"
        if c.referencia:
            return f"({texto})"
        return texto if _es_numero(c.expresion) else f"fx: {texto}"

    def _dibujar_cotas(self, p):
        """Cotas como las de Fusion: líneas y texto en verde oliva sobre fondo oscuro (gris oscuro sobre
        fondo claro), el valor SIN caja, al costado de la línea de cota, con un fondo redondeado del color
        del lienzo para que se lea sobre cualquier línea. La caja con borde aparece solo al editarla
        (doble clic). Los textos no se pisan (ni entre ellos ni con los íconos de restricción)."""
        zonas = {}
        ocupadas = _Ocupadas([*self._zonas_glifos.values(), *(c for _i, c in self._zonas_glifos_extra)])
        trazos = self._trazos_cotas = {}              # por cota, las rayas donde se puede agarrar (no el texto)
        fondos = self._fondos_cotas = {}              # por cota, la caja del fondo de su texto
        actual = []

        def raya(a, b):
            p.drawLine(a, b)
            actual.append((a, b))
        base = self._color_cota()
        en_conflicto = set(self.conflictos_sin_esperar()) if self.resultado is not None and not self.resultado.ok else set()
        desfase = 22 / max(self.px_por_mm(), 1e-9)       # 22 px expresados en mm del boceto
        p.setFont(temas.qfont_cotas(9))
        fm = p.fontMetrics()
        pts = [self.b.coords(k) for k in self.b.puntos]
        centroide = (sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)) if pts else (0.0, 0.0)
        viva = self._cota_viva()
        for c in [*self.b.cotas.values(), *([viva] if viva is not None else [])]:
            actual.clear()
            girar = None                             # ángulo del texto (grados) en las cotas lineales
            try:
                valor = self.b.medir(c)
            except (ErrorBoceto, KeyError, ZeroDivisionError):
                continue
            texto = self._texto_cota(c, valor)
            resaltada = c.id == self._zona_sobre and c.id >= 0
            color = (QColor(0, 180, 255) if c.id in self.seleccion or (c.id == self._cita_sobre and self.entrada is not None)
                     else CONFLICTO if c.id in en_conflicto
                     else self._color_resalte() if resaltada
                     else REFERENCIA if c.referencia else base)
            p.setPen(QPen(color, 1))
            p.setBrush(color)
            afuera = QPointF(0, -1)                  # hacia dónde se aleja el texto de la línea de cota
            marco = self.b.ejes_cota(c)
            if marco is not None:
                a, b, u, n, s0 = marco
                off = c.datos.get("desfase")        # si el usuario la movió, manda su posición guardada
                if off is None:
                    off = desfase
                    if c.tipo == "distancia":        # del lado de afuera de la figura, como Fusion
                        medio = ((a[0] + b[0]) / 2 - centroide[0], (a[1] + b[1]) / 2 - centroide[1])
                        if medio[0] * n[0] + medio[1] * n[1] < 0:
                            off = -off
                s = s0 + off
                ua, ub = a[0] * u[0] + a[1] * u[1], b[0] * u[0] + b[1] * u[1]
                da = (u[0] * ua + n[0] * s, u[1] * ua + n[1] * s)
                db = (u[0] * ub + n[0] * s, u[1] * ub + n[1] * s)
                um = (ua + ub) / 2 + c.datos.get("texto", 0.0)
                qa, qb, pa, pb = self.a_px(*da), self.a_px(*db), self.a_px(*a), self.a_px(*b)
                auxiliares = [self._auxiliar_cota(pa, qa), self._auxiliar_cota(pb, qb)]
                for aux in auxiliares:
                    if aux is not None:
                        p.drawLine(*aux)
                raya(qa, qb)
                actual.extend(aux for aux in auxiliares if aux is not None)
                self._flecha(p, qa, qb)
                self._flecha(p, qb, qa)
                q = self.a_px(u[0] * um + n[0] * s, u[1] * um + n[1] * s)
                d = (qa + qb) / 2 - (pa + pb) / 2
                largo = math.hypot(d.x(), d.y())
                if largo > 1e-6:
                    afuera = d / largo
                girar = math.degrees(math.atan2(qb.y() - qa.y(), qb.x() - qa.x()))
                if girar > 90:
                    girar -= 180
                elif girar <= -90:
                    girar += 180
            elif c.tipo in ("radio", "diametro"):
                cent = self.b.coords(self.b.curvas[c.entidades[0]].centro)
                r = self.b.radio(c.entidades[0])
                ubic = c.datos.get("ubic")              # arrastrada: la línea sale hacia donde se la dejó
                ang = math.atan2(ubic[1] - cent[1], ubic[0] - cent[0]) if ubic else math.pi / 4
                dx, dy = math.cos(ang), math.sin(ang)
                borde = self.a_px(cent[0] + r * dx, cent[1] + r * dy)
                q = self.a_px(*ubic) if ubic else borde + QPointF(26, -18)
                raya(self.a_px(*cent) if c.tipo == "radio" else self.a_px(cent[0] - r * dx, cent[1] - r * dy), borde)
                if q != borde:
                    raya(borde, q)
                self._flecha(p, borde, self.a_px(*cent))
                afuera = QPointF(dx, -dy) if ubic else QPointF(1, 0)
            elif c.tipo == "angulo" and self._arco_cota(c) is not None:
                o, t0, t1 = self._arco_cota(c)
                ubic = c.datos.get("ubic")              # arrastrada: el radio del arco llega hasta donde se la dejó
                r = max(math.dist(o, ubic), 1e-6) if ubic else 40 / max(self.px_por_mm(), 1e-9)
                pasos = max(4, int(abs(t1 - t0) / 0.08))
                arco = [self.a_px(o[0] + r * math.cos(t0 + (t1 - t0) * i / pasos),
                                  o[1] + r * math.sin(t0 + (t1 - t0) * i / pasos)) for i in range(pasos + 1)]
                for a, b in zip(arco, arco[1:], strict=False):
                    raya(a, b)
                if abs(t1 - t0) > 0.15:
                    self._flecha(p, arco[0], arco[1])
                    self._flecha(p, arco[-1], arco[-2])
                tm = (t0 + t1) / 2
                q = self.a_px(o[0] + r * math.cos(tm), o[1] + r * math.sin(tm))
                d = q - self.a_px(*o)
                afuera = d / (math.hypot(d.x(), d.y()) or 1.0)
            else:
                seg = self.b.segmento_cota(c)
                if seg is not None:                     # BOC-37: la línea de cota con sus flechas, entre lo que mide
                    qa, qb = self.a_px(*seg[0]), self.a_px(*seg[1])
                    raya(qa, qb)
                    self._flecha(p, qa, qb)
                    self._flecha(p, qb, qa)
                    q, afuera, d = (qa + qb) / 2, QPointF(0, -1), qb - qa
                    largo = math.hypot(d.x(), d.y())
                    if largo > 1e-6:
                        afuera = QPointF(d.y() / largo, -d.x() / largo)       # la normal que mira hacia arriba
                        if afuera.y() > 1e-9 or (abs(afuera.y()) <= 1e-9 and afuera.x() < 0):
                            afuera = -afuera
                    girar = math.degrees(math.atan2(d.y(), d.x()))
                    girar = girar - 180 if girar > 90 else girar + 180 if girar <= -90 else girar
                else:
                    anclas = [self._ancla(e) for e in c.entidades]
                    q = sum(anclas[1:], anclas[0]) / len(anclas) + QPointF(0, 12)
                    afuera = QPointF(0, 1)
                if "ubic" in c.datos:                   # arrastrada: el texto va donde se la dejó, con una guía fina
                    p.drawLine(q, self.a_px(*c.datos["ubic"]))
                    q, afuera, girar = self.a_px(*c.datos["ubic"]), QPointF(0, 0), None
            w, h = fm.horizontalAdvance(texto) + 4, fm.height()
            if girar is not None:                    # texto a lo largo de la línea: se aleja medio alto
                centro = q + afuera * (h / 2 + 1)
            else:
                centro = q + afuera * ((abs(afuera.x()) * w + abs(afuera.y()) * h) / 2 + 2)
            if girar is not None and abs(girar) > 1:     # el texto girado ocupa el rectángulo girado, no w × h
                cos, sin = abs(math.cos(math.radians(girar))), abs(math.sin(math.radians(girar)))
                caja = QRectF(0, 0, w * cos + h * sin, w * sin + h * cos)
                caja.moveCenter(centro)
            else:
                caja = QRectF(centro.x() - w / 2, centro.y() - h / 2, w, h)
            paso = QPointF(afuera.x() * (w + 4), afuera.y() * (h + 2))
            if math.hypot(paso.x(), paso.y()) < 1:
                paso = QPointF(0, h + 2)
            for _ in range(0 if "texto" in c.datos or "ubic" in c.datos else 20):   # un texto ubicado no se corre
                if not ocupadas.choca(caja):
                    break
                caja.translate(paso)
            ocupadas.agregar(caja)
            if c.id >= 0:
                zonas[c.id] = caja
                trazos[c.id] = list(actual)
            if c.id != self._cota_editada:
                girado = girar is not None and abs(girar) > 1
                fondo = QRectF(-w / 2 - 3, -h / 2 - 2, w + 6, h + 4) if girado else caja.adjusted(-3, -2, 3, 2)
                if c.id >= 0:
                    if girado:
                        cos, sin = abs(math.cos(math.radians(girar))), abs(math.sin(math.radians(girar)))
                        fondos[c.id] = QRectF(0, 0, (w + 6) * cos + (h + 4) * sin, (w + 6) * sin + (h + 4) * cos)
                        fondos[c.id].moveCenter(caja.center())
                    else:
                        fondos[c.id] = QRectF(fondo)
                p.save()
                if girado:
                    p.translate(caja.center())
                    p.rotate(girar)
                p.setPen(Qt.NoPen)
                p.setBrush(self._color_fondo())
                p.drawRoundedRect(fondo, 3, 3)
                if resaltada:
                    tinte = self._color_resalte()
                    tinte.setAlpha(32)
                    p.setBrush(tinte)
                    p.drawRoundedRect(fondo, 3, 3)
                p.setPen(color)
                p.setBrush(color)
                p.drawText(QRectF(-w / 2, -h / 2, w, h) if girado else caja, Qt.AlignCenter, texto)
                p.restore()
        p.setBrush(Qt.NoBrush)
        return zonas

    def _dibujar_guias_conica(self, p, inicio, vertice, fin):
        """Las rectas extremo–vértice son las tangentes de la cónica en sus extremos."""
        p.save()
        p.setPen(QPen(QColor(150, 150, 160), 1, Qt.DotLine))
        self._dibujar_polilinea(p, [inicio, vertice, fin])
        p.restore()

    def _tramo_a_recortar(self, pos):
        """Polilínea (u, v) del tramo que quitaría Recortar con el cursor en `pos` (para resaltarlo)."""
        cid = self._curva_cercana(pos)
        if cid is None or isinstance(self.b.curvas[cid], Texto) or self.b.curvas[cid].proyectada:
            return None
        clave = (cid, len(self.historial))
        if clave not in self._cache_cortes:
            try:
                self._cache_cortes[clave] = [t for t, _xy, _o in self.b._cortes(cid)]
            except (ErrorBoceto, ValueError, ZeroDivisionError):
                return None
        ts = self._cache_cortes[clave]
        prim = self.b.primitivas(cid)[0]
        t0, t1, per = dominio(prim)
        tc = mas_cercano(prim, self.a_mm(pos))[0]
        antes, despues = [t for t in ts if t < tc], [t for t in ts if t > tc]
        if per:
            if len(ts) < 2:
                lo, hi = t0, t1
            else:
                lo = antes[-1] if antes else ts[-1] - (t1 - t0)
                hi = despues[0] if despues else ts[0] + (t1 - t0)
        else:
            lo, hi = (antes[-1] if antes else t0), (despues[0] if despues else t1)
        n = 32
        return [evaluar_primitiva(prim, lo + (hi - lo) * i / n)[0] for i in range(n + 1)]

    def _temporal(self, construir):
        """Geometría de una vista previa: se arma en un boceto aparte (sin tocar el real)."""
        tmp = Boceto()
        try:
            construir(tmp)
        except (ErrorBoceto, ValueError, ZeroDivisionError, IndexError):
            return []
        return [puntos_primitiva(prim) for prim in tmp.geometria(incluir_construccion=True)]

    def _dibujar_previa(self, p):
        h, cur = self.herramienta, self._cursor_efectivo()      # con los valores escritos ya aplicados
        # Fusion dibuja la vista previa como geometría sin restringir: azul y continua
        acento = QColor(90, 160, 255) if self._oscuro() else QColor(25, 90, 200)
        if h == "simetria":
            self._dibujar_previa_simetria(p, acento)
        elif h in COMANDO_PROYECCION:
            self._dibujar_previa_proyeccion(p, acento)
        elif h in PATRON and self.patron.activo:
            self.patron.dibujar(p, acento)
        elif h in TRANSFORMAR and self.transformar.activo:
            self.transformar.dibujar(p, acento)
        if self._previa_polis or self._caret is not None or (self._previa_texto and self._previa_texto.get("caja")):
            if self._sel_texto:                    # lo seleccionado del texto que se escribe
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(acento.red(), acento.green(), acento.blue(), 80))
                for cuadro in self._sel_texto:
                    p.drawPolygon(QPolygonF([self.a_px(*q) for q in cuadro]))
                p.setBrush(Qt.NoBrush)
            p.setPen(QPen(acento, 2.0))
            for poli in self._previa_polis:
                self._dibujar_polilinea(p, poli)
            if self._caret is not None and self._caret_on and self.hasFocus():
                p.setPen(QPen(QColor(245, 245, 245) if self._oscuro() else QColor(20, 20, 20), 2.0))
                self._dibujar_polilinea(p, list(self._caret))     # el cursor parpadeante: acá se escribe
            esquinas = self._cuadro_texto_previa()
            if esquinas:                     # el cuadro dibujado con el ratón (o el que envuelve el texto), en trazos
                p.setPen(QPen(acento, 1, Qt.DashLine))
                self._dibujar_polilinea(p, esquinas + esquinas[:1])
        if h == "recortar" and self._previa_recorte:
            p.setPen(QPen(QColor(230, 60, 60), 3, Qt.DashLine))
            self._dibujar_polilinea(p, self._previa_recorte)
        if self._asas is not None:
            self._asas.dibujar(p)
        elif h in ("empalme", "chaflan", "chaflan_dist_angulo", "chaflan_dos_dist") and self.entrada is None:
            from .asas_boceto import asas_chaflan, asas_empalme
            try:
                esquina = self._esquina_en_vertice(self._pos_cursor)
                if esquina is not None:
                    vertice, curvas, lados = esquina
                    d = self._radio_sugerido(curvas)
                    valores = [d, 45 if h == "chaflan_dist_angulo" else d]
                    asas = (asas_empalme(self, curvas, lados, vertice=vertice) if h == "empalme" else
                            asas_chaflan(self, h, curvas, lados))
                    p.setPen(QPen(acento, 2.0))
                    for poli in asas[2](valores):
                        self._dibujar_polilinea(p, poli)
            except (ErrorBoceto, ValueError, ZeroDivisionError):
                pass                   # un vértice no válido no tiene vista previa
        if self.ayuda_3d is not None:
            self._dibujar_ayuda_3d(p, acento)
        if h == "desfase" and self.picks and self.entrada is not None:
            polis, nota, error = self._previa_desfase()
            p.setPen(QPen(acento, 2.0))
            for poli in polis:
                self._dibujar_polilinea(p, poli)
            self._dibujar_nota_desfase(p, nota, error)
        if cur is not None and self._tangente is not None:
            inicio, linea = self._tangente
            p.setPen(QPen(acento, 2.0))
            p.drawLine(self.a_px(*self.b.coords(inicio)), self.a_px(*cur))
        elif self.clics and cur is not None:
            p.setPen(QPen(acento, 2.0))
            a = self.clics[0][1]
            pts = [c[1] for c in self.clics]
            polis = []
            if h in ("linea", "linea_medio"):
                ini = self.clics[-1][1] if h == "linea" else (2 * a[0] - cur[0], 2 * a[1] - cur[1])
                if h == "linea" and self.inf_actual is not None and self.inf_actual.guias:
                    p.setPen(QPen(acento, 1.5, Qt.DashLine))
                p.drawLine(self.a_px(*ini), self.a_px(*cur))
            elif h == "rectangulo" or (h == "texto" and self.entrada is None):
                self._dibujar_polilinea(p, [a, (cur[0], a[1]), cur, (a[0], cur[1]), a])
            elif h == "rectangulo_centro":
                k = cur
                o = (2 * a[0] - k[0], 2 * a[1] - k[1])
                self._dibujar_polilinea(p, [o, (k[0], o[1]), k, (o[0], k[1]), o])
                p.setPen(QPen(QColor(205, 205, 210) if self._oscuro() else QColor(240, 150, 60), 1.2, Qt.DashLine))
                self._dibujar_polilinea(p, [o, k])                  # diagonales de construcción, como Fusion
                self._dibujar_polilinea(p, [(k[0], o[1]), (o[0], k[1])])
                p.setPen(QPen(acento, 2.0))
            elif h == "rectangulo_3p" and len(pts) == 2:
                ub = _unitario(pts[1][0] - a[0], pts[1][1] - a[1])
                d = (cur[0] - a[0]) * -ub[1] + (cur[1] - a[1]) * ub[0]
                n = (-ub[1] * d, ub[0] * d)
                self._dibujar_polilinea(p, [a, pts[1], (pts[1][0] + n[0], pts[1][1] + n[1]), (a[0] + n[0], a[1] + n[1]), a])
            elif h == "rectangulo_3p":
                self._dibujar_polilinea(p, pts + [cur])
            elif h in ("poligono_inscrito", "poligono_circunscrito") and math.dist(a, cur) > 1e-9:
                tipo = "inscrito" if h == "poligono_inscrito" else "circunscrito"
                r, esquinas = _vertices_poligono(a, cur, self.lados, tipo)
                self._dibujar_polilinea(p, esquinas + esquinas[:1])
                p.setPen(QPen(acento, 1, Qt.DotLine))           # el círculo de construcción
                self._dibujar_polilinea(p, self._circulo_vista(a, r))
            elif h == "estrella" and math.dist(a, cur) > 1e-9:
                r = math.dist(a, cur)
                try:
                    esquinas = vertices_estrella(a, r, int(self.opciones["puntas_estrella"]),
                                                 math.atan2(cur[1] - a[1], cur[0] - a[0]), self._interior_estrella(r))
                except ErrorBoceto:
                    esquinas = []                       # un salto que no entra: el clic lo dice; acá no hay previa
                self._dibujar_polilinea(p, esquinas + esquinas[:1])
                p.setPen(QPen(acento, 1, Qt.DotLine))           # el círculo de las puntas
                self._dibujar_polilinea(p, self._circulo_vista(a, r))
            elif h == "arco" and len(pts) == 2:
                polis = self._temporal(lambda t: t.agregar_arco_3_puntos(pts[0], cur, pts[1]))
            elif h == "arco_centro" and len(pts) == 2 and math.dist(a, pts[1]) > 1e-9:
                r = math.dist(a, pts[1])
                ang = math.atan2(cur[1] - a[1], cur[0] - a[0])
                fin = (a[0] + r * math.cos(ang), a[1] + r * math.sin(ang))
                if self._sentido_barrido() > 0:
                    polis = self._temporal(lambda t: t.agregar_arco_centro(a, pts[1], fin))
                else:
                    polis = self._temporal(lambda t: t.agregar_arco_centro(a, fin, pts[1]))
            elif h in ("circulo", "circulo_2p", "poligono_inscrito", "poligono_circunscrito", "estrella", "espiral"):
                if h == "circulo_2p":
                    centro, r = ((a[0] + cur[0]) / 2, (a[1] + cur[1]) / 2), math.dist(a, cur) / 2
                else:
                    centro, r = a, math.dist(a, cur)
                self._dibujar_polilinea(p, self._circulo_vista(centro, r))
            elif h == "elipse" and len(pts) == 2:
                m = pts[1]
                aa = math.dist(a, m) or 1e-9
                b = abs((m[0] - a[0]) * (cur[1] - a[1]) - (m[1] - a[1]) * (cur[0] - a[0])) / aa
                polis = self._temporal(lambda t: t.agregar_elipse(a, m, max(b, 1e-3), ejes=True))
            elif h.startswith("ranura_") and len(pts) >= (2 if h in ("ranura_centro", "ranura_total", "ranura_punto") else 3):
                tipo = h[len("ranura_"):]
                n = 2 if h in ("ranura_centro", "ranura_total", "ranura_punto") else 3
                ancho = 2 * self._ancho_ranura(h, self.clics[:n], cur)
                polis = self._temporal(lambda t: t.agregar_ranura(tipo, pts[:n], max(ancho, 1e-3)))
            elif h in SPLINES:
                todos = pts + [cur]
                if h == "spline_ajuste":
                    polis = self._temporal(lambda t: t.agregar_spline(todos, "ajuste"))
                else:
                    polis = self._temporal(lambda t: t.agregar_spline(todos, "control", self.opciones["grado_spline"]))
                    p.setPen(QPen(QColor(150, 150, 160), 1, Qt.DotLine))
                    self._dibujar_polilinea(p, todos)
                    p.setPen(QPen(acento, 1.5, Qt.DashLine))
            elif h == "conica" and len(pts) >= 2:
                vertice = pts[2] if len(pts) == 3 else cur
                rho = 0.5
                if len(pts) == 3 and self.entrada is not None:
                    try:
                        rho = _numero(self.entrada.campos[0].text() or "0.5")
                    except ValueError:
                        rho = 0.0
                self._dibujar_guias_conica(p, a, vertice, pts[1])
                if 0 < rho < 1:
                    polis = self._temporal(lambda t: t.agregar_conica(a, vertice, pts[1], rho))
                    if len(pts) == 3:
                        medio = ((a[0] + pts[1][0]) / 2, (a[1] + pts[1][1]) / 2)
                        p.setPen(QPen(acento, 1, Qt.DashLine))
                        self._dibujar_polilinea(p, [medio, vertice])
                        asa = self.a_px(medio[0] + rho * (vertice[0] - medio[0]),
                                        medio[1] + rho * (vertice[1] - medio[1]))
                        p.drawRect(QRectF(asa.x() - 4, asa.y() - 4, 8, 8))
                        p.setPen(QPen(acento, 2.0))
            elif h in ("circulo_3p", "arco", "arco_centro", "arco_tangente", "poligono_arista", "conica") \
                    or h.startswith("ranura_"):
                self._dibujar_polilinea(p, pts + [cur])
            for poli in polis:
                self._dibujar_polilinea(p, poli)
        if cur is not None and self.herramienta not in ("seleccionar",) and self.visor is not None \
                and self.entrada is None:
            q = self.a_px(*cur)
            p.setPen(QPen(acento, 1))
            p.drawEllipse(q, 4, 4)
        elif cur is not None and self.visor is None and self.herramienta != "seleccionar":
            q = self.a_px(*cur)
            p.setPen(QPen(acento, 1))
            p.drawEllipse(q, 4, 4)
            if not self._claves_vivas():           # con cajas de valor, las coordenadas estorban
                p.setPen(QPen(QColor(80, 80, 90), 1))
                p.drawText(q + QPointF(10, -8), f"({cur[0]:.2f}; {cur[1]:.2f})")
        if cur is not None and self.inf_actual is not None and h != "seleccionar" and self.entrada is None:
            self._dibujar_inferencia(p, acento, cur)

    def _dibujar_inferencia(self, p, acento, cur):
        """Guías temporales, marcador del ajuste, ícono de la restricción y etiqueta (cada cosa se apaga en los ajustes)."""
        inf, a, q = self.inf_actual, self.ajustes_inf, self.a_px(*cur)
        guia = QColor(acento)
        guia.setAlpha(210)
        if a["guias"]:
            p.setPen(QPen(guia, 1.2, Qt.DashLine))
            for tramo in inf.guias:
                self._dibujar_polilinea(p, tramo)
            p.setPen(QPen(guia, 1.4))
            for tramo in inf.guias:                       # el punto de referencia de cada guía (la base no)
                if tramo[0] != self._base_inferencia():
                    p.drawEllipse(self.a_px(*tramo[0]), 3.5, 3.5)
        if a["indicadores"]:
            p.setPen(QPen(guia, 1.8))
            p.setBrush(Qt.NoBrush)                       # solo contorno, sea cual sea el pincel que quedó puesto
            x, y = q.x(), q.y()
            if inf.tipo == "punto_medio":
                p.drawPolygon(QPolygonF([QPointF(x, y - 6), QPointF(x - 6, y + 5), QPointF(x + 6, y + 5)]))
            elif inf.tipo.startswith("interseccion"):
                p.drawLine(QPointF(x - 5, y - 5), QPointF(x + 5, y + 5))
                p.drawLine(QPointF(x - 5, y + 5), QPointF(x + 5, y - 5))
            elif inf.tipo.startswith("alineado"):
                p.drawPolygon(QPolygonF([QPointF(x, y - 6), QPointF(x + 6, y), QPointF(x, y + 6), QPointF(x - 6, y)]))
            elif inf.tipo == "sobre_curva":
                p.drawEllipse(q, 5, 5)
            if inf.restriccion:
                nombre = ICONO_RESTRICCION.get(inf.restriccion[0], "r_coincidente")
                p.drawPixmap(QRectF(x + 10, y + 6, 14, 14), icono(nombre).pixmap(28, 28), QRectF(0, 0, 28, 28))
        if a["etiquetas"] and inf.etiqueta:
            texto = inf.etiqueta + (" · bloqueada" if self._inf_bloqueo is not None else "")
            if len(self.inf_lista) > 1 and self._inf_bloqueo is None:
                texto += f" · Espacio: otra ({self._inf_alt % len(self.inf_lista) + 1}/{len(self.inf_lista)})"
            self._rotulo(p, q, texto, guia)

    def _rotulo(self, p, q, texto, color):
        """El cartelito de una ayuda de dibujo junto al cursor `q` (px): fondo, borde del color de la guía y texto."""
        fm = QFontMetricsF(p.font())
        caja = QRectF(q.x() + 12, q.y() + 24, fm.horizontalAdvance(texto) + 10, fm.height() + 4)
        if caja.right() > self.width():
            caja.moveRight(q.x() - 8)
        if caja.bottom() > self.height():
            caja.moveBottom(q.y() - 10)
        p.setPen(QPen(color, 1))
        p.setBrush(QColor(30, 30, 36, 215) if self._oscuro() else QColor(255, 255, 255, 225))
        p.drawRoundedRect(caja, 3, 3)
        p.setBrush(Qt.NoBrush)
        p.setPen(QColor(235, 235, 240) if self._oscuro() else QColor(30, 30, 40))
        p.drawText(caja.adjusted(5, 0, 0, 0), Qt.AlignVCenter | Qt.AlignLeft, texto)

    def _dibujar_ayuda_3d(self, p, acento):
        """Marcador y etiqueta de la ayuda de dibujo del Boceto 3D (`ui/triada3d.py`; las guías van en la vista 3D)."""
        q, tipo, texto = self.ayuda_3d
        guia = QColor(acento)
        guia.setAlpha(210)
        p.setPen(QPen(guia, 1.8))
        p.setBrush(Qt.NoBrush)
        x, y = q.x(), q.y()
        if tipo == "punto_medio":
            p.drawPolygon(QPolygonF([QPointF(x, y - 6), QPointF(x - 6, y + 5), QPointF(x + 6, y + 5)]))
        elif tipo.startswith("interseccion"):
            p.drawLine(QPointF(x - 5, y - 5), QPointF(x + 5, y + 5))
            p.drawLine(QPointF(x - 5, y + 5), QPointF(x + 5, y - 5))
        elif tipo.startswith("alineado"):
            p.drawPolygon(QPolygonF([QPointF(x, y - 6), QPointF(x + 6, y), QPointF(x, y + 6), QPointF(x - 6, y)]))
        else:
            p.drawEllipse(q, 5, 5)
        self._rotulo(p, q, texto, guia)

    def describir(self, ids):
        return ", ".join(f"{NOMBRES_ENTIDAD[self.b.tipo_de(i)]} {i}" for i in ids if i in self.b.puntos or i in self.b.curvas)
