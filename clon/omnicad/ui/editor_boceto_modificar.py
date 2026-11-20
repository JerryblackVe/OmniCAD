"""LienzoModificarMixin: métodos del lienzo por tema."""

from .editor_boceto_comun import (
    ANGULO,
    Boceto,
    ErrorBoceto,
    ErrorExpresion,
    PEDIR_DISTANCIA,
    PICKS,
    PISTA_DESFASE,
    QColor,
    QDialog,
    QEventLoop,
    QFontMetricsF,
    QPoint,
    QPointF,
    QRectF,
    QToolButton,
    Qt,
    TOL_PX,
    auto_restringir,
    aviso_radio_empalme,
    expresion_sin_signo,
    formato,
    mas_cercano,
    math,
    puntos_primitiva,
)


class LienzoModificarMixin:
    def _clic_pick(self, pos):
        if self.herramienta in ("empalme", "chaflan", "chaflan_dist_angulo", "chaflan_dos_dist"):
            try:
                esquina = self._esquina_en_vertice(pos)
            except ErrorBoceto as e:
                self.mensaje.emit(str(e))
                return True
            if esquina is not None:
                vertice, curvas, lados = esquina
                self.picks, self.picks_xy = [], []
                for cid, xy in zip(curvas, lados, strict=True):
                    self.agregar_pick(cid, xy, pos, vertice=vertice)
                return True
        tipos = ("linea",) if self.fase == "eje" else PICKS[self.herramienta][1]
        cid = self._curva_cercana(pos, tipos=tipos)
        if cid is None and self.fase == "eje" and (eje := self._eje_origen_cerca(pos)) is not None:
            self.agregar_pick(eje, self.a_mm(pos), pos)       # BOC-40: el eje X o Y del origen sirve de línea de simetría
            return True
        if cid is None and self.herramienta == "desfase" and (de_perfil := self._pick_de_perfil(pos)) is not None:
            self.agregar_pick(de_perfil[0], self.a_mm(pos), pos, perfil=de_perfil[1])
            return True
        if cid is None and self.herramienta == "curva_fusion" and self.visor is not None:
            elegir = getattr(self.visor, "elegir_entidad", None)
            if elegir is not None:
                q = self.visor.mapFromGlobal(self.mapToGlobal(QPoint(int(pos.x()), int(pos.y()))))
                info = elegir(QPointF(q), {"arista"})
                if info and info.get("forma") is not None:
                    antes = set(self.b.curvas)
                    if self.proyectar_forma(info["forma"], "proyectar", info.get("ref"), "arista"):
                        nuevas = set(self.b.curvas) - antes
                        if len(nuevas) == 1 and self.b.curvas[next(iter(nuevas))].extremos():
                            cid = nuevas.pop()
                            self._proy_fusion += 1
                        else:      # True = dejó un paso; p. ej. el borde de un agujero: la fusión no lo usa
                            self._quitar_proyecciones(self._proy_fusion + 1)
                            self.picks, self.picks_xy = [], []
                            self.mensaje.emit("La arista debe dar una curva abierta.")
                            return True
        if cid is None:
            if self.herramienta == "circulo_2t" and len(self.picks) == 2:
                return False          # el clic ubica el círculo (lo procesa la herramienta de puntos)
            texto = "Hacé clic sobre " + ("una línea." if tipos == ("linea",) else
                                          "un texto." if tipos == ("texto",) else "una curva.")
            if self.herramienta == "simetria":
                texto = ("La línea de simetría tiene que ser recta: elegí una línea del boceto."
                         if self._curva_cercana(pos) is not None else
                         "Ahí no hay ninguna línea: hacé clic sobre la línea de simetría.")
                self._error_simetria = texto
                self._emitir_simetria()
            self.mensaje.emit(texto)
            return True
        self.agregar_pick(cid, self.a_mm(pos), pos)
        return True

    def _cerca_de_eje(self, cid, xy, tol_px=12.0):
        """BOC-71: ¿el clic `xy` (mm) sobre una elipse cae a menos de `tol_px` de su eje mayor o menor? (Fusion: cerca
        de un eje el desfase es otra elipse; lejos, un óvalo a distancia constante.)"""
        c = self.b.curvas.get(cid)
        if c is None or c.tipo != "elipse":
            return False
        (cx, cy), (mx, my) = self.b.coords(c.centro), self.b.coords(c.mayor)
        a = math.hypot(mx - cx, my - cy)
        if a < 1e-9:
            return False
        ux, uy, dx, dy = (mx - cx) / a, (my - cy) / a, xy[0] - cx, xy[1] - cy
        return min(abs(-dx * uy + dy * ux), abs(dx * ux + dy * uy)) * self.px_por_mm() <= tol_px

    def _eje_origen_cerca(self, pos):
        """Id del eje del origen (X o Y) a menos de `TOL_PX` píxeles de `pos`, o None."""
        o = self.a_px(0.0, 0.0)
        for eje, distancia in ((Boceto.EJE_X, abs(pos.y() - o.y())), (Boceto.EJE_Y, abs(pos.x() - o.x()))):
            if distancia <= TOL_PX:
                return eje
        return None

    def _pick_de_perfil(self, pos):
        """BOC-70: (curva del borde más cercana al clic, ids del borde) del perfil (región cerrada) bajo `pos`, o None.
        Fusion acepta en Desfase una curva, una cadena o un perfil."""
        i = self.perfil_en(pos)
        if i is None:
            return None
        firma = self._perfiles()[i].firma
        xy = self.a_mm(pos)
        cercana = min((k for k in firma if k in self.b.curvas),
                      key=lambda k: min(mas_cercano(p, xy)[1] for p in self.b.primitivas(k)), default=None)
        return None if cercana is None else (cercana, frozenset(firma))

    def agregar_pick(self, cid, xy, pos=None, perfil=None, vertice=None):
        """Suma una curva elegida (con el lugar del clic, en mm) a la herramienta actual. `perfil`: en Desfase, el
        borde del perfil del que sale (se desfasan todos sus contornos)."""
        h = self.herramienta
        self._desfase_perfil = perfil if h == "desfase" else None
        self._desfase_elipse = h == "desfase" and perfil is None and self._cerca_de_eje(cid, xy)
        pos = pos if pos is not None else self._pos_cursor
        if h == "simetria" and self.fase == "eje":
            self._eje_simetria = cid                # no crea nada: lo hace Aceptar, después de la vista previa
            self._emitir_simetria()
            self.update()
            return
        n, _ = PICKS[h]
        if len(self.picks) >= n:
            self.picks, self.picks_xy = [], []
        if cid in self.picks:
            return
        self.picks.append(cid)
        self.picks_xy.append(xy)
        if len(self.picks) < n:
            self.update()
            return
        picks, xys = list(self.picks), list(self.picks_xy)
        listo = True
        if h == "recortar":
            if self.aplicar_cambio(lambda: self.b.recortar(cid, xy), operacion=True):
                if self._recorte_arrastre is True:
                    self.historial.pop()          # conserva solo la foto anterior al primer recorte del gesto
                elif self._recorte_arrastre is False:
                    self._recorte_arrastre = True
        elif h == "alargar":
            self.aplicar_cambio(lambda: self.b.alargar(cid, xy), operacion=True)
        elif h == "partir":
            self.aplicar_cambio(lambda: self.b.partir(cid, xy), operacion=True)
        elif h == "manija":                         # B-739: la del punto de ajuste más cercano al clic; si ya la tiene, la quita
            pid = min(self.b.curvas[cid].pts, key=lambda q: math.dist(self.b.coords(q), xy))
            quitar = any(m[0] == pid for m in self.b.curvas[cid].manijas)
            self.aplicar_cambio(lambda: (self.b.desactivar_manija if quitar else self.b.activar_manija)(cid, pid), operacion=True)
        elif h == "desglosar_texto":
            self.aplicar_cambio(lambda: self.b.desglosar_texto(cid), operacion=True)
        elif h == "circulo_3t":
            self.aplicar_cambio(lambda: self.b.agregar_circulo_tangente(picks, None, None, xys, self.construccion))
        elif h == "circulo_2t":
            listo = False
            self.mensaje.emit("Clic para ubicar el círculo (o escribí el radio).")
        elif h == "curva_fusion":
            n = self._proy_fusion
            if self.aplicar_cambio(lambda: self.b.curva_fusion(picks[0], xys[0], picks[1], xys[1],
                                                               self.opciones["continuidad"]), operacion=True):
                del self.historial[len(self.historial) - n:]    # la fusión y sus proyecciones: un solo deshacer
                self._proy_fusion = 0
            elif n:
                self._quitar_proyecciones(n)
        elif h == "empalme":
            listo = False
            from .asas_boceto import asas_empalme

            def aceptar(v):
                radio, aviso = self._radio_empalme(v[0], picks), ""

                def empalmar():
                    nonlocal aviso
                    arco = self.b.empalme(picks[0], picks[1], radio, xys[0], xys[1], v[0], vertice=vertice)
                    aviso = aviso_radio_empalme(radio, self.b.radio(arco))
                ok = self._aplicar_y_limpiar(empalmar)
                if ok and aviso:
                    self.aviso.emit(aviso)
                return ok
            self._abrir_entrada(["Radio"], [formato.numero(self._radio_sugerido(picks))], pos,
                                aceptar, asas_empalme(self, picks, xys, vertice=vertice))

            def validar_radio(texto):
                error = ""
                try:
                    self._radio_empalme(texto, picks)
                except (ErrorExpresion, ValueError, ErrorBoceto) as e:
                    error = str(e)
                self.entrada.marcar_error(malo=bool(error))
                self.entrada.campos[0].setToolTip(error)
                if error:
                    self.mensaje.emit(error)
            self.entrada.campos[0].textChanged.connect(validar_radio)
        elif h in ("chaflan", "chaflan_dist_angulo", "chaflan_dos_dist"):
            listo = False
            d = formato.numero(self._radio_sugerido(picks))
            if h == "chaflan":
                etiquetas, textos = ["Distancia"], [d]
            elif h == "chaflan_dos_dist":
                etiquetas, textos = ["Distancia 1", "Distancia 2"], [d, d]
            else:
                etiquetas, textos = ["Distancia", "∠"], [d, "45"]

            def aceptar(v):
                d1 = self.evaluar(v[0])
                d2 = self.evaluar(v[1]) if h == "chaflan_dos_dist" else None
                ang = self.evaluar(v[1], ANGULO) if h == "chaflan_dist_angulo" else None
                return self._aplicar_y_limpiar(lambda: self.b.chaflan(picks[0], picks[1], d1, d2, ang, xys[0], xys[1],
                                                                      v[0], v[1] if h != "chaflan" else None))
            from .asas_boceto import asas_chaflan
            self._abrir_entrada(etiquetas, textos, pos, aceptar, asas_chaflan(self, h, picks, xys))
        elif h == "desfase":
            listo = False
            conservar, self._desfase_conservar = self._desfase_conservar, None
            self._abrir_desfase(cid, pos, *(conservar or (None, False)))
        if listo:
            self.picks, self.picks_xy = [], []
        self.update()

    def _abrir_desfase(self, cid, pos, textos=None, invertido=False, modo=None):
        """Abre (o rearma) la barra del Desfase sobre la cadena de `cid` (Fusion: diálogo Desfase con el asa en la
        vista). Con `textos`, conserva lo ya escrito; si no, propone una distancia que entra para los dos lados."""
        modo = self._desfase_modo = modo or self.opciones["direccion_desfase"]     # un lado, dos lados o simétrico
        self._desfase_invertido = invertido
        self._previa_desfase_cache = None
        if self._desfase_perfil:
            self.seleccion = sorted(self._desfase_perfil)
        elif self.opciones["seleccion_cadena"]:
            self.seleccion = [k for k, _ in self.b.cadena(cid)[0]]
        else:
            self.seleccion = [cid]
        base = self._base_desfase()                 # (punto de la curva, normal de la distancia positiva)
        dos = modo == "dos"
        if textos is None:
            d = formato.numero(self._distancia_inicial_desfase())
            textos = [d, "0"] if dos else [d]

        def aceptar(v):
            _polis, nota, error = self._previa_desfase()
            if error:                     # la causa y el campo que hay que corregir; la barra sigue abierta
                self._marcar_campos_desfase(error)
                self.mensaje.emit(nota)
                return False
            avisos = []
            ok = self._aplicar_y_limpiar(lambda: avisos.extend(self._desfasar_en(self.b, cid, **self._args_desfase(v))[1]))
            if ok:
                self.seleccion = []
                if avisos:
                    self.mensaje.emit(" ".join(avisos))
            return ok
        from .asas_boceto import asas_desfase
        elegidas = self.seleccion
        self._abrir_entrada(["Distancia 1", "Distancia 2"] if dos else ["Distancia"], textos, pos, aceptar,
                            asas_desfase(self, base))
        self.seleccion = elegidas                 # cerrar la barra anterior soltó lo resaltado: vuelve a quedar elegido
        self._armar_barra_desfase()

    def _desfasar_en(self, b, cid, **args):
        """`desfasar` de la curva elegida (con su cadena) o, si se eligió un perfil, `desfasar_perfil`: lo mismo en la
        vista previa y en Aceptar."""
        return b.desfasar_perfil(self._desfase_perfil, **args) if self._desfase_perfil else b.desfasar(cid, **args)

    def _base_desfase(self):
        """(P, n) del asa del Desfase: P = punto de lo elegido más cercano al clic y n = hacia dónde va una distancia
        positiva (sin Invertir). La normal sale de probar el mismo `desfasar` de Aceptar con una distancia chica."""
        from .asas_boceto import polilineas_de, punto_mas_cercano
        cid = self.picks[0]
        punto, tangente = punto_mas_cercano(polilineas_de(self, self.seleccion), self.picks_xy[0])
        d0 = self._distancia_inicial_desfase()
        for k in (1.0, 0.1, 0.01):
            copia = self.b.copia()
            try:
                nuevos, _ = self._desfasar_en(copia, cid, distancia=d0 * k, cadena=self.opciones["seleccion_cadena"],
                                              elipse=self._desfase_elipse)
            except (ErrorBoceto, ErrorExpresion, ValueError, ZeroDivisionError):
                continue
            hacia, _t = punto_mas_cercano([puntos_primitiva(prim) for n in nuevos for prim in copia.primitivas(n)],
                                          punto)
            normal = (-tangente[1], tangente[0])
            signo = (hacia[0] - punto[0]) * normal[0] + (hacia[1] - punto[1]) * normal[1]
            if abs(signo) > 1e-9:
                return punto, (normal if signo > 0 else (-normal[0], -normal[1]))
        return None

    def _distancia_inicial_desfase(self):
        """Distancia redonda con la que arranca el Desfase (Fusion la saca de donde queda el asa): unos 48 px de
        pantalla, sin pasar de la cuarta parte de lo elegido, así tampoco da un valor imposible al invertir."""
        from .asas_boceto import polilineas_de
        pts = [q for poli in polilineas_de(self, self.seleccion) for q in poli]
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        ancho, alto = (max(xs) - min(xs), max(ys) - min(ys)) if pts else (0.0, 0.0)
        tam = min(ancho, alto) if min(ancho, alto) > 1e-9 else max(ancho, alto)
        v = max(min(48 / max(self.px_por_mm(), 1e-9), tam / 4), 1e-3)
        e = 10 ** math.floor(math.log10(v))
        return e * (5 if v / e >= 5 else 2 if v / e >= 2 else 1)

    def _desfase_con_seleccion(self):
        """Con una curva ya elegida al pulsar Desfase (Fusion, video 2026-10-31: el diálogo abre con «1 seleccionada» y
        la vista previa a la vista), arranca sin pedir otro clic."""
        from .asas_boceto import _medio, polilineas_de
        admitidas = ("linea", "arco", "circulo", "elipse", "arco_elipse", "spline")
        curvas = [i for i in self.seleccion if i in self.b.curvas and self.b.curvas[i].tipo in admitidas]
        if curvas:
            xy = _medio(max(polilineas_de(self, curvas[:1]), key=len))
            self.agregar_pick(curvas[0], xy, self.a_px(*xy))

    def _clic_con_desfase_abierto(self, pos):
        """Un clic en el lienzo con el Desfase abierto no lo cierra (Fusion: el diálogo sigue): sobre otra curva pasa
        el desfase a ella con los mismos valores; en el vacío no hace nada. Enter acepta y Esc cancela."""
        if self._citar_cota(pos):
            return
        cid = self._curva_cercana(pos, tipos=PICKS["desfase"][1])
        de_perfil = self._pick_de_perfil(pos) if cid is None else None
        if de_perfil is not None and de_perfil[1] != self._desfase_perfil:       # otro perfil, con los mismos valores
            self._desfase_conservar = ([c.text() for c in self.entrada.campos], self._desfase_invertido)
            self.picks, self.picks_xy = [], []
            self.agregar_pick(de_perfil[0], self.a_mm(pos), self.entrada.pos() - QPoint(14, 10), perfil=de_perfil[1])
        elif cid is not None and cid not in self.seleccion:
            self._desfase_conservar = ([c.text() for c in self.entrada.campos], self._desfase_invertido)
            self.picks, self.picks_xy = [], []
            self.agregar_pick(cid, self.a_mm(pos), self.entrada.pos() - QPoint(14, 10))
        elif cid is None and de_perfil is None:
            self.mensaje.emit("Desfase abierto: Enter lo acepta, Esc lo cancela (el boceto sigue abierto).")
        self.entrada.campos[0].setFocus()

    def cambiar_opcion_desfase(self, clave, valor):
        """Una opción de la paleta (dirección, selección de cadena, Match Topology) cambia con el Desfase abierto:
        la barra, las asas, la vista previa y lo que va a crear Aceptar se rearman ya, con lo ya escrito."""
        self.opciones[clave] = valor
        if self.herramienta != "desfase" or not self.picks or self.entrada is None:
            return
        previos = [c.text().strip() for c in self.entrada.campos]
        textos = self._textos_para_modo(previos, valor) if clave == "direccion_desfase" else previos
        pos = self.entrada.pos() - QPoint(14, 10)
        self.picks, self.picks_xy = self.picks[:1], self.picks_xy[:1]
        self._abrir_desfase(self.picks[0], pos, textos, self._desfase_invertido, self.opciones["direccion_desfase"])
        self.entrada.campos[0].setFocus()
        self.update()

    def _textos_para_modo(self, previos, nuevo):
        """Los valores de la barra al pasar a otra dirección, sin perder lo escrito: Un lado y Simétrico comparten
        la distancia; Dos lados es (d, 0) desde Un lado y (d, -d) desde Simétrico."""
        antes, d = self._desfase_modo, previos[0]
        if nuevo == antes:
            return previos
        try:
            positivo = expresion_sin_signo(d, self.evaluar(d), self.evaluar)
        except (ErrorExpresion, ValueError, ZeroDivisionError):
            positivo = d
        if nuevo == "simetrico":
            return [positivo]
        if nuevo == "dos":
            if antes == "un":
                return [d, "0"]
            return [positivo, "-" + positivo if positivo.replace(".", "", 1).isdigit() else f"-({positivo})"]
        return [d]

    def _marcar_campos_desfase(self, error):
        for i in range(len(self.entrada.campos)):
            self.entrada.marcar_error(i, bool(error) and i in error)

    def _marco_nota_desfase(self, nota, letra):
        """(rectángulo, texto) de la nota del Desfase: bajo la barra de la distancia (o sobre ella si abajo no entra),
        partida en líneas y dentro de la zona útil del lienzo, sin la paleta."""
        caja, zona = self.entrada.geometry(), self._zona_util()
        texto = f"{nota}\n{PISTA_DESFASE}"
        ancho = max(min(zona.width() - 16, 420), 120)
        cuadro = QFontMetricsF(letra).boundingRect(QRectF(0, 0, ancho - 12, 4000),
                                                   int(Qt.AlignLeft | Qt.TextWordWrap), texto)
        w, h = cuadro.width() + 12, cuadro.height() + 8
        x = max(zona.left() + 4, min(caja.left(), zona.right() - w - 4))
        y = caja.bottom() + 4
        if y + h > zona.bottom() - 4:
            y = max(zona.top() + 4, caja.top() - h - 4)
        return QRectF(x, y, w, h), texto

    def _dibujar_nota_desfase(self, p, nota, error):
        """La nota del Desfase (qué lado y, si no se puede, por qué), siempre a la vista."""
        letra = p.font()
        letra.setPointSizeF(max(letra.pointSizeF() - 1, 7.0))
        p.setFont(letra)
        marco, texto = self._marco_nota_desfase(nota, letra)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(92, 42, 45, 235) if error else QColor(20, 30, 45, 220))
        p.drawRoundedRect(marco, 4, 4)
        p.setPen(QColor(255, 190, 190) if error else QColor(200, 225, 255))
        p.drawText(marco.adjusted(6, 4, -6, -4), int(Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap), texto)
        p.setBrush(Qt.NoBrush)

    def _zona_util(self):
        """Rectángulo del lienzo que no tapan la paleta ni los paneles de la derecha."""
        zona = self.rect()
        area = self.parentWidget()
        for w in [getattr(area, "paleta", None), *getattr(area, "laterales", [])]:
            if w is not None and w.isVisible():
                izquierda = self.mapFromParent(w.geometry().topLeft()).x()
                if zona.width() / 3 < izquierda < zona.right():
                    zona.setRight(izquierda - 8)
        return zona

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.entrada is not None:
            self.entrada.reubicar()           # al achicar la ventana la barra de valores no se queda afuera

    def _aplicar_y_limpiar(self, funcion):
        ok = self.aplicar_cambio(funcion, operacion=True)
        if ok:
            self.picks, self.picks_xy = [], []
        return ok

    def _args_desfase(self, textos):
        """Argumentos de `Boceto.desfasar` para lo escrito en la barra: los mismos en la vista previa y en Aceptar.
        El lado lo da el signo (como Fusion: positiva = el lado del asa, afuera en una cadena cerrada) y «Invertir»;
        el cursor no interviene, así lo que se ve es lo que se crea. En Dos lados, las dos distancias llevan
        signo sobre la misma normal."""
        dos = self._desfase_modo == "dos"
        d = [self.evaluar(t) for t in textos[:2 if dos else 1]]
        return {"distancia": d[0], "expresion": expresion_sin_signo(textos[0], d[0], self.evaluar),
                "direccion": self._desfase_modo, "distancia2": d[1] if dos else None,
                "expresion2": expresion_sin_signo(textos[1], d[1], self.evaluar) if dos else None,
                "invertir": self._desfase_invertido, "topologia": self.opciones["match_topology"],
                "cadena": self.opciones["seleccion_cadena"], "elipse": self._desfase_elipse}

    def _previa_desfase(self):
        """(curvas de la vista previa, nota, error) de lo escrito ahora en la barra del Desfase. `error` es False o
        la tupla de los campos que hay que corregir. Arma el desfase sobre una copia con el mismo `desfasar` de
        Aceptar; si no se puede, no devuelve curvas (nunca queda una vista previa vieja) y la nota dice por qué.
        Se recuerda el último resultado: repintar sin cambiar nada no vuelve a calcular."""
        textos = [c.text().strip() for c in self.entrada.campos]
        clave = (tuple(textos), self._desfase_invertido, self._desfase_modo, self.opciones["match_topology"],
                 self.opciones["seleccion_cadena"], tuple(self.picks), self._desfase_perfil, self._desfase_elipse,
                 (len(self.b.curvas), len(self.b.puntos), len(self.b.cotas)))     # el boceto cambió: se recalcula
        if self._previa_desfase_cache is not None and self._previa_desfase_cache[0] == clave:
            return self._previa_desfase_cache[1]
        resultado = self._calcular_previa_desfase(textos)
        self._previa_desfase_cache = (clave, resultado)
        return resultado

    def _calcular_previa_desfase(self, textos):
        etiquetas = ["Distancia 1", "Distancia 2"] if self._desfase_modo == "dos" else ["Distancia"]
        for i, t in enumerate(textos):          # errores de lo escrito: cada campo por su lado
            try:
                if not t:
                    return [], PEDIR_DISTANCIA, (i,)
                self.evaluar(t)
            except (ErrorExpresion, ValueError, ZeroDivisionError) as e:
                return [], f"{etiquetas[i]}: {e}" if len(textos) > 1 else str(e), (i,)
        try:
            args = self._args_desfase(textos)
            copia = self.b.copia()
            nuevos, avisos = self._desfasar_en(copia, self.picks[0], **args)
        except (ErrorBoceto, ErrorExpresion, ValueError, ZeroDivisionError) as e:
            return [], str(e), self._campos_que_fallan(textos) or tuple(range(len(textos)))
        polis = [puntos_primitiva(prim) for k in nuevos for prim in copia.primitivas(k)]
        nota = {"dos": "Dos lados", "simetrico": "Simétrico"}.get(self._desfase_modo) or self._lado_desfase(polis)
        if self.b.curvas[self.picks[0]].tipo == "elipse" and not self._desfase_perfil:
            nota += " · " + ("Elipse (cerca de un eje)" if self._desfase_elipse else "Óvalo (lejos de los ejes)")
        return polis, " · ".join([nota, *avisos]), False

    def _campos_que_fallan(self, textos):
        """En Dos lados, cuáles de las dos distancias no se pueden hacer por sí solas (vacío si falla el conjunto)."""
        if self._desfase_modo != "dos":
            return ()
        malos, args = [], self._args_desfase(textos)
        for i, valor in enumerate((args["distancia"], args["distancia2"])):
            if valor == 0:
                continue
            try:
                self._desfasar_en(self.b.copia(), self.picks[0], distancia=valor, direccion="un",
                                  invertir=args["invertir"], topologia=args["topologia"], cadena=args["cadena"],
                                  elipse=args["elipse"])
            except ErrorBoceto:
                malos.append(i)
        return tuple(malos)

    def _lado_desfase(self, polis):
        """«Hacia afuera» o «Hacia adentro» si la cadena es cerrada (el resultado crece o se achica); si no, «Hacia un
        lado» (la distancia negativa o «Invertir» pasan al otro)."""
        cadena, cerrada = ([(k, False) for k in sorted(self._desfase_perfil)], True) if self._desfase_perfil             else self.b.cadena(self.picks[0])
        if not cerrada or not (self.opciones["seleccion_cadena"] or self._desfase_perfil):
            return "Hacia un lado"

        def caja(lista):
            xs, ys = [q[0] for poli in lista for q in poli], [q[1] for poli in lista for q in poli]
            return (max(xs) - min(xs)) * (max(ys) - min(ys))
        antes = caja([puntos_primitiva(prim) for k, _ in cadena for prim in self.b.primitivas(k)])
        despues = caja(polis)
        return "Hacia afuera" if despues > antes else "Hacia adentro" if despues < antes else "Hacia un lado"

    def _armar_barra_desfase(self):
        """Junto al campo: «Invertir», Aceptar (✓) y Cancelar (✕) a la vista, y la vista previa viva: cada tecla
        repinta y marca en rojo el campo que no se puede."""
        barra = self.entrada
        invertir = QToolButton(barra)
        invertir.setText("⇄")
        invertir.setCheckable(True)
        invertir.setChecked(self._desfase_invertido)
        invertir.setFocusPolicy(Qt.NoFocus)
        invertir.setToolTip("Invertir dirección: pasa el desfase al otro lado, sin cambiar la distancia")
        invertir.toggled.connect(self._invertir_desfase)
        aceptar = QToolButton(barra)
        aceptar.setText("✓")
        aceptar.setFocusPolicy(Qt.NoFocus)
        aceptar.setToolTip("Aceptar el desfase (Enter). El boceto sigue abierto: se cierra con «Terminar boceto»")
        aceptar.clicked.connect(lambda: barra.aceptado.emit([c.text().strip() for c in barra.campos]))
        cancelar = QToolButton(barra)
        cancelar.setText("✕")
        cancelar.setFocusPolicy(Qt.NoFocus)
        cancelar.setToolTip("Cancelar el desfase (Esc) sin tocar el boceto")
        cancelar.clicked.connect(barra.cancelado.emit)
        for campo in barra.campos:
            campo.setFixedWidth(84)           # cuatro dígitos con decimales: la barra entera cabe en una ventana chica
        for boton in (invertir, aceptar, cancelar):
            barra.layout().addWidget(boton)
        barra.adjustSize()
        barra.reubicar()
        for campo in barra.campos:
            campo.textChanged.connect(self._al_cambiar_desfase)
        self._al_cambiar_desfase()

    def _invertir_desfase(self, marcado):
        self._desfase_invertido = marcado
        self._al_cambiar_desfase()
        self.entrada.campos[0].setFocus()

    def _al_cambiar_desfase(self, *_):
        if self.entrada is None or not self.picks:
            return
        _polis, nota, error = self._previa_desfase()
        self._marcar_campos_desfase(error)
        self.mensaje.emit(nota)
        self.update()

    def _radio_sugerido(self, ids):
        """Valor inicial (como Fusion: proporcional a la más chica de las curvas elegidas)."""
        largos = []
        for i in ids:
            pts = puntos_primitiva(self.b.primitivas(i)[0], 32)
            largos.append(sum(math.dist(a, b) for a, b in zip(pts, pts[1:], strict=False)))
        v = min(largos) / 5 if largos else 1.0
        e = 10 ** math.floor(math.log10(max(v, 1e-6)))
        return max(round(v / e) * e, 1e-3)

    def soltar_desfase(self):
        """Suelta la asociación de los desfases de lo seleccionado (Fusion: borrar el glifo de desfase)."""
        curvas = [i for i in self.seleccion if i in self.b.curvas]

        def soltar():
            hechos = 0
            for i in curvas:
                try:
                    self.b.soltar_desfase(i)
                    hechos += 1
                except ErrorBoceto:          # no es desfase, o ya lo soltó otra curva del mismo desfase
                    pass
            if not hechos:
                raise ErrorBoceto("Soltar desfase: elegí una curva del desfase.")
        return self.aplicar_cambio(soltar, anclar=False)

    def patron_de(self, ids):
        """Id del patrón que tiene alguna de las entidades `ids` (original o copia), o None."""
        ids = set(ids)
        return next((r["id"] for r in self.b.patrones
                     if ids & set(r["ids"]) or any(ids & set(c) for c in r["copias"].values())), None)

    def editar_patron(self, pid=None):
        """Edita un patrón ya hecho en su panel (cantidades, distancias, direcciones, centro y copias excluidas); Cancelar
        lo deja como estaba. Sin `pid`, el patrón de lo seleccionado."""
        pid = self.patron_de(self.seleccion) if pid is None else pid
        if pid is None:
            self.mensaje.emit("Editar patrón: seleccioná una curva del patrón (o doble clic en su glifo).")
            return False
        registro = next(r for r in self.b.patrones if r["id"] == pid)
        self.set_herramienta("patron_" + registro["tipo"])
        self.patron.cargar(registro)
        self.update()
        return True

    def auto_restringir(self, **opciones):
        """Restringir automáticamente: agrega restricciones y cotas hasta dejarlo totalmente restringido.
        `opciones`: las de `auto_restringir` del solver (tipos, tolerancias, límite, datum, excluir)."""
        agregado = {}

        def hacer():
            agregado["lista"] = auto_restringir(self.b, self.valores_cotas(), **opciones)
        if self.aplicar_cambio(hacer):
            n = len(agregado.get("lista", []))
            estado = "totalmente restringido" if self.resultado.gdl == 0 else f"quedan {self.resultado.gdl} GDL"
            self.mensaje.emit(f"Restringir automáticamente: {n} restricciones/cotas agregadas ({estado}).")
            return agregado["lista"]
        return []

    def set_previa_auto(self, lista):
        """Actualiza las restricciones y cotas sugeridas que se dibujan en violeta."""
        self.previa_auto = lista
        self.update()

    def auto_restringir_dialogo(self, datum=None):
        """AutoConstrain con el diálogo de resultados (BOC-5); `datum` (Restricciones automáticas desde
        referencia) manda sobre el punto seleccionado, si hay uno."""
        from .dialogo_autorestringir import ELEGIR_DATUM, DialogoAutoRestringir
        if not self.b.curvas and not self.b.puntos:
            self.mensaje.emit("Restringir automáticamente: el boceto está vacío.")
            return []
        if datum is None:
            puntos = [i for i in self.seleccion if i in self.b.puntos]
            datum = puntos[0] if len(puntos) == 1 else None
        try:
            dialogo = DialogoAutoRestringir(self.b, self.valores_cotas(), datum, self)
            if datum is not None and dialogo.datum.currentData() != datum:
                dialogo.fijar_datum(datum)   # punto fuera de los 200 más cercanos: se agrega y se elige
        except (ErrorBoceto, ErrorExpresion) as e:
            self.mensaje.emit(str(e))
            return []
        dialogo.previa.connect(self.set_previa_auto)
        try:
            resultado = dialogo.resultado()
            self.set_previa_auto(resultado.sugerencias[:dialogo.cantidad.value()] if resultado is not None else [])
            codigo = dialogo.exec()
            while codigo == ELEGIR_DATUM:            # «Elegir en el lienzo»: el diálogo vuelve con el punto elegido
                pid = self.elegir_punto_en_lienzo("AutoConstrain: hacé clic en el punto datum (Esc cancela).")
                if pid is not None:
                    dialogo.fijar_datum(pid)
                codigo = dialogo.exec()
            aceptado = codigo == QDialog.Accepted
        finally:
            self.set_previa_auto([])
        return self.auto_restringir(**dialogo.opciones()) if aceptado else []

    def elegir_punto_en_lienzo(self, aviso="Hacé clic en un punto del boceto (Esc cancela)."):
        """Espera el próximo clic sobre un punto del boceto y devuelve su id (None con Esc, clic derecho o si el
        lienzo se oculta). Lo usa AutoConstrain para el datum, con su diálogo cerrado mientras tanto."""
        self._eligiendo_punto = {"lazo": QEventLoop(), "pid": None}
        self.mensaje.emit(aviso)
        self.setFocus()
        try:
            self._eligiendo_punto["lazo"].exec()
            return self._eligiendo_punto["pid"]
        finally:
            self._eligiendo_punto = None

    def _terminar_eleccion(self, pid=None):
        if self._eligiendo_punto is not None:
            self._eligiendo_punto["pid"] = pid
            self._eligiendo_punto["lazo"].quit()

    def hideEvent(self, e):
        self._terminar_eleccion()                    # salir del boceto no deja colgada la espera del clic
        super().hideEvent(e)
