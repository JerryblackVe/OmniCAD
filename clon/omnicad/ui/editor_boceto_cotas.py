"""LienzoCotasMixin: métodos del lienzo por tema."""

from .editor_boceto_comun import (
    ANGULARES,
    ANGULO,
    AZUL_CAJA,
    Boceto,
    COTA_CLARO,
    COTA_OSCURO,
    CampoVivo,
    Cota,
    ESCALAR,
    EntradaValor,
    ErrorBoceto,
    ErrorExpresion,
    FONDO_LIENZO,
    LONGITUD,
    Linea,
    QColor,
    QFontMetricsF,
    QInputDialog,
    QPen,
    QPointF,
    QRectF,
    QToolTip,
    Qt,
    RANURAS_RECTAS,
    TIPOS_COTA,
    VIVAS,
    _barrido,
    _es_numero,
    _numero,
    _rotar,
    _tipo_valor,
    _unitario,
    circunferencia_3_puntos,
    formato,
    math,
    replace,
    resolver,
    separar_nombre,
    temas,
    texto_valor,
    validar_lados_poligono,
    validar_nombre,
    validar_puntas_estrella,
    validar_valor_cota,
    warnings,
)
from ..timeline.parametros import acotar


def QMenu(*args, **kwargs):
    from . import editor_boceto
    return editor_boceto.QMenu(*args, **kwargs)


class LienzoCotasMixin:
    def _abrir_entrada(self, etiquetas, textos, pos, al_aceptar, asas=None):
        """Barra de valores de la herramienta. `asas`: (asas, tipos, previa) de `ui/asas_boceto.py`: se pueden tirar con
        el ratón y escriben en las cajas."""
        self._cerrar_entrada()
        self._texto_inicial = textos[0] if textos else None
        self.entrada = EntradaValor(etiquetas, textos, self)

        def aceptar(valores):
            try:
                ok = al_aceptar(valores)
            except (ErrorExpresion, ValueError, ErrorBoceto) as e:
                self.mensaje.emit(str(e))
                self.entrada.marcar_error()
                return
            if ok is not False:
                self._cerrar_entrada()
        self.entrada.aceptado.connect(aceptar)
        self.entrada.cancelado.connect(self._cancelar_entrada)
        if asas is not None:
            from .asas_boceto import GestorAsas2D
            self._asas = GestorAsas2D(self, self.entrada, *asas)
        self.entrada.abrir(pos)

    def _cancelar_entrada(self):
        """Esc o ✕ en la barra de valores. B-654: en el Desfase un solo Esc sale del comando, como Fusion."""
        salir = self.herramienta == "desfase"
        self._cerrar_entrada()
        if salir:
            self.set_herramienta("seleccionar")

    def _cerrar_entrada(self):
        self._previa_desfase_cache = None
        if self.herramienta == "desfase" and self.entrada is not None:
            self.seleccion = []                    # cerrar la barra del Desfase (Esc, ✕, Aceptar) suelta lo que resaltaba
        if self._asas is not None:
            self._asas.cerrar()
            self._asas = None
        if self.entrada is not None:
            entrada, self.entrada = self.entrada, None
            # Se sueltan antes las funciones conectadas (cierres que apuntan al Lienzo): con la caja
            # pendiente de deleteLater, ese ciclo hacía abortar a Qt si el Lienzo se borraba primero.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                for senal in [entrada.aceptado, entrada.tabulado, entrada.cancelado] + [c.textChanged for c in entrada.campos]:
                    try:
                        senal.disconnect()
                    except (RuntimeError, TypeError):
                        pass
            entrada.hide()
            entrada.deleteLater()
            self.setFocus()
            if self.herramienta == "texto":
                self.clics = []              # cancelar (Esc) también descarta la esquina del cuadro
            self.update()
        if self._previa_texto is not None:
            self._previa_texto, self._previa_polis, self._texto_oculto = None, [], None
            self._caret, self._sel_texto, self._arrastre_texto = None, [], False
            self._t_caret.stop()
            self.unsetCursor()
            self.update()
            self.objetos.notificar()             # P-188: vuelve el panel de objetos si hay uno elegido
        if self._paleta_texto:
            self._paleta_texto = False
            self.herramienta_cambiada.emit(self.herramienta)     # la paleta vuelve a las opciones de la herramienta
        self._editando = None
        self._cota_editada = self._cota_previa = self._cota_abierta = None
        self._cita_sobre = None

    def _entrada_dinamica(self, primera):
        """Entrada escrita de las herramientas sin cajas de valor (círculo de 2 tangentes, mover/copiar)."""
        h, pos = self.herramienta, self._pos_cursor
        if h == "circulo_2t":
            lineas = list(self.picks)

            def aceptar(v):
                r = self.evaluar(v[0])
                return self._aplicar_y_limpiar(lambda: self.b.agregar_circulo_tangente(lineas, self.cursor, r, None,
                                                                                       self.construccion))
            self._abrir_entrada(["R"], [primera], pos, aceptar)

    def _reiniciar_vivo(self):
        if self._editando is not None:
            self._cerrar_entrada()
        self._bloqueos, self._activo, self._editando, self._sentido_vivo = {}, 0, None, None

    def _claves_vivas(self):
        """Claves de las cajas del paso actual de la herramienta (sin depender del ratón)."""
        h, n = self.herramienta, len(self.clics)
        if h not in VIVAS or not n or self._tangente is not None:
            return []
        if h == "linea":
            return ["largo", "angulo"]
        if h in ("rectangulo", "rectangulo_centro"):
            return ["ancho", "alto"] if n == 1 else []
        if h == "rectangulo_3p":
            return {1: ["ancho"], 2: ["alto"]}.get(n, [])
        if h == "circulo":
            return ["diametro"] if n == 1 else []
        if h == "arco":
            return {1: ["cuerda"], 2: ["radio"]}.get(n, [])
        if h == "arco_centro":
            return {1: ["radio"], 2: ["barrido"]}.get(n, [])
        if h == "circulo_2p":
            return ["diametro"] if n == 1 else []
        if h == "linea_medio":
            return ["largo", "angulo"] if n == 1 else []
        if h == "elipse":
            return {1: ["radio_mayor", "angulo"], 2: ["radio_menor"]}.get(n, [])
        if h == "arco_tangente":
            return ["radio"] if n == 1 and self._tangente_de(self.clics[0][0]) is not None else []
        if h == "poligono_arista":
            return ["largo", "angulo", "lados"] if n == 1 else []
        if h.startswith("poligono_"):
            return ["radio", "lados"] if n == 1 else []
        if h == "estrella":
            return ["radio", "puntas"] if n == 1 else []
        if h in RANURAS_RECTAS:
            return {1: ["largo", "angulo"], 2: ["ancho"]}.get(n, [])
        return ["ancho"] if n == 3 else []                 # ranuras de arco: el ancho en el último paso

    def _tangente_de(self, pid):
        """(punto, dirección unitaria de salida) de la curva abierta que termina en `pid`; None si no hay."""
        curvas = self._curvas_con_extremo(pid) if pid is not None else []
        return self.b._salida_extremo(curvas[0], pid) if curvas else None

    def _evaluar_campo(self, clave, texto):
        if clave == "lados":
            return validar_lados_poligono(int(round(_numero(texto))))
        if clave == "puntas":
            return validar_puntas_estrella(int(round(_numero(texto))))
        valor = self.evaluar(texto, ANGULO if clave in ANGULARES else LONGITUD)
        if clave in ANGULARES:              # B-718/B-719: hasta ANGULO_MAXIMO, con un mensaje de 1 renglón
            acotar(valor, ANGULO)
        else:                               # lo escrito se vuelve cota: mayor que cero y hasta 1 km, igual que al editarla
            validar_valor_cota(clave if clave in ("radio", "diametro") else "distancia", valor)
        return valor

    def _radio_empalme(self, texto, picks):
        """Radio escrito del Empalme. Entre dos rectas paralelas lo manda la separación y el pedido se ignora con un
        aviso: pasarse del tope no lo rechaza."""
        from ..restricciones.boceto import MEDIDA_MAXIMA
        c1, c2 = picks
        if self.b.tipo_de(c1) == self.b.tipo_de(c2) == "linea":
            d1, d2 = self.b._direccion(c1), self.b._direccion(c2)
            if abs(d1[0] * d2[1] - d1[1] * d2[0]) < 1e-12:
                valor = self.evaluar(texto, LONGITUD)
                validar_valor_cota("radio", min(valor, MEDIDA_MAXIMA))
                return valor
        return self._evaluar_campo("radio", texto)

    def _valores_bloqueados(self):
        """Valores fijados (lo escrito); la caja que se está escribiendo ya manda mientras se escribe."""
        valores = {k: v for k, (_t, v) in self._bloqueos.items()}
        if self._editando is not None and self.entrada is not None:
            try:
                valores[self._editando] = self._evaluar_campo(self._editando, self.entrada.campos[0].text())
            except (ErrorExpresion, ErrorBoceto, ValueError, KeyError):
                pass
        return valores

    def _bloquear(self, clave, texto, valor):
        self._bloqueos[clave] = (texto.strip(), valor)
        if clave in ("lados", "puntas"):
            if clave == "lados":
                self.lados = int(valor)
            else:
                self.opciones["puntas_estrella"] = int(valor)
            self.herramienta_cambiada.emit(self.herramienta)      # la paleta muestra los lados nuevos

    def _linea_previa(self):
        """Línea anterior de la cadena (el ángulo se mide contra ella, como en Fusion)."""
        if self.herramienta != "linea" or not self.clics or self._ultima_linea not in self.b.curvas:
            return None
        junta = self.clics[-1][0]
        ln = self.b.curvas[self._ultima_linea]
        return self._ultima_linea if junta is not None and junta in (ln.p1, ln.p2) else None

    def _atras_previa(self):
        """Dirección (unitaria) que va de la unión hacia el otro extremo de la línea anterior."""
        previa = self._linea_previa()
        if previa is None:
            return None
        junta = self.clics[-1][0]
        ln = self.b.curvas[previa]
        a, o = self.b.coords(junta), self.b.coords(ln.p1 if ln.p2 == junta else ln.p2)
        return _unitario(o[0] - a[0], o[1] - a[1])

    def _sentido_barrido(self):
        """Arco de punto central: +1 antihorario / -1 horario, según hacia dónde va el ratón (arco corto)."""
        if len(self.clics) < 2 or self.cursor is None:
            return 1
        c, ini, cur = self.clics[0][1], self.clics[1][1], self.cursor
        a0 = math.atan2(ini[1] - c[1], ini[0] - c[0])
        a1 = math.atan2(cur[1] - c[1], cur[0] - c[0])
        return 1 if _barrido(a0, a1) <= math.pi else -1

    @staticmethod
    def _a_distancia_de_recta(cur, a, b, distancia):
        """Lleva `cur` a `distancia` de la recta ab, del lado en que está."""
        u = _unitario(b[0] - a[0], b[1] - a[1])
        n = (-u[1], u[0])
        d = (cur[0] - a[0]) * n[0] + (cur[1] - a[1]) * n[1]
        s = 1 if d >= 0 else -1
        return (cur[0] + (s * distancia - d) * n[0], cur[1] + (s * distancia - d) * n[1])

    @staticmethod
    def _punto_arco_radio(a, b, cur, radio):
        """Arco de 3 puntos con el radio escrito: el punto medio del arco, del lado del ratón."""
        c = math.dist(a, b)
        if c < 1e-9:
            return cur
        radio = max(radio, c / 2)
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        u = _unitario(b[0] - a[0], b[1] - a[1])
        n = (-u[1], u[0])
        lado = 1 if (cur[0] - m[0]) * n[0] + (cur[1] - m[1]) * n[1] >= 0 else -1
        h = math.sqrt(max(radio * radio - c * c / 4, 0.0))
        circ = circunferencia_3_puntos(a, cur, b)
        mayor = circ is not None and ((circ[0] - m[0]) * n[0] + (circ[1] - m[1]) * n[1]) * lado > 0
        k = h * (lado if mayor else -lado)
        centro = (m[0] + n[0] * k, m[1] + n[1] * k)
        return (centro[0] + n[0] * lado * radio, centro[1] + n[1] * lado * radio)

    def _direccion_angulo(self, u, grados):
        atras = self._atras_previa()
        t = math.radians(grados)
        if atras is None:
            return (math.cos(t), math.sin(t))
        return max((_rotar(atras, t), _rotar(atras, -t)), key=lambda d: d[0] * u[0] + d[1] * u[1])

    def _aplicar_bloqueos(self, cur):
        """El punto que manda el ratón, corregido para respetar los valores escritos del paso actual."""
        claves = self._claves_vivas()
        vals = {k: v for k, v in self._valores_bloqueados().items() if k in claves}
        if cur is None or not vals:
            return cur
        h = self.herramienta
        pts = [q for _, q in self.clics]
        a = pts[-1] if h == "linea" else pts[0]
        u = _unitario(cur[0] - a[0], cur[1] - a[1])

        def desde(base, d, largo):
            return (base[0] + d[0] * largo, base[1] + d[1] * largo)
        if h == "linea":
            if "angulo" in vals:
                d = self._direccion_angulo(u, vals["angulo"])
                largo = vals.get("largo", max((cur[0] - a[0]) * d[0] + (cur[1] - a[1]) * d[1], 0.0))
                return desde(a, d, largo)
            return desde(a, u, vals["largo"])
        if h in ("rectangulo", "rectangulo_centro"):
            k = 1.0 if h == "rectangulo" else 0.5
            x, y = cur
            if "ancho" in vals:
                x = a[0] + (1 if cur[0] >= a[0] else -1) * k * vals["ancho"]
            if "alto" in vals:
                y = a[1] + (1 if cur[1] >= a[1] else -1) * k * vals["alto"]
            return (x, y)
        if h == "rectangulo_3p":
            return desde(a, u, vals["ancho"]) if len(pts) == 1 else self._a_distancia_de_recta(cur, a, pts[1], vals["alto"])
        if h == "circulo":
            return desde(a, u, vals["diametro"] / 2)
        if h == "arco":
            return desde(a, u, vals["cuerda"]) if len(pts) == 1 else self._punto_arco_radio(a, pts[1], cur, vals["radio"])
        if h == "arco_centro":
            if len(pts) == 1:
                return desde(a, u, vals["radio"])
            ini = pts[1]
            t = math.atan2(ini[1] - a[1], ini[0] - a[0]) + self._sentido_barrido() * math.radians(vals["barrido"])
            return desde(a, (math.cos(t), math.sin(t)), math.dist(a, ini))
        d = self._direccion_angulo(u, vals["angulo"]) if "angulo" in vals else u

        def libre():
            return max((cur[0] - a[0]) * d[0] + (cur[1] - a[1]) * d[1], 0.0)
        if h == "circulo_2p":
            return desde(a, u, vals["diametro"])
        if h == "linea_medio":
            return desde(a, d, vals["largo"] / 2 if "largo" in vals else libre())
        if h == "elipse":
            if len(pts) == 2:
                return self._a_distancia_de_recta(cur, a, pts[1], vals["radio_menor"])
            return desde(a, d, vals["radio_mayor"] if "radio_mayor" in vals else libre())
        if h == "arco_tangente":                 # el final queda sobre el círculo de ese radio, tangente a la curva
            p, s = self._tangente_de(self.clics[0][0])
            n = (-s[1], s[0])
            lado = 1 if (cur[0] - p[0]) * n[0] + (cur[1] - p[1]) * n[1] >= 0 else -1
            c = (p[0] + n[0] * lado * vals["radio"], p[1] + n[1] * lado * vals["radio"])
            return desde(c, _unitario(cur[0] - c[0], cur[1] - c[1]), vals["radio"])
        if h == "poligono_arista":
            if vals.keys() & {"largo", "angulo"}:
                return desde(a, d, vals["largo"] if "largo" in vals else libre())
            return cur
        if h.startswith("poligono_") or h == "estrella":
            return desde(a, u, vals["radio"]) if "radio" in vals else cur
        if h in RANURAS_RECTAS:
            if len(pts) == 1:
                return desde(a, d, vals["largo"] / (2 if h == "ranura_punto" else 1) if "largo" in vals else libre())
            ini, fin = self._eje_ranura(h, pts)
            return self._a_distancia_de_recta(cur, ini, fin, vals["ancho"] / 2)
        centro, R = self._arco_ranura(h, pts)
        s = 1 if math.dist(cur, centro) >= R else -1
        return desde(centro, _unitario(cur[0] - centro[0], cur[1] - centro[1]), R + s * vals["ancho"] / 2)

    def _cursor_efectivo(self):
        cur = self.cursor
        if cur is None or not self.clics or self.herramienta not in VIVAS:
            return cur
        return self._aplicar_bloqueos(cur)

    def _campos_vivos(self, cur=None):
        """Las cajas de valor del paso actual, con lo que mide la vista previa (cursor ya corregido)."""
        claves = self._claves_vivas()
        cur = self._cursor_efectivo() if cur is None else cur
        if not claves or cur is None:
            return []
        h = self.herramienta
        pts = [q for _, q in self.clics]
        a = pts[-1] if h == "linea" else pts[0]
        u = _unitario(cur[0] - a[0], cur[1] - a[1])
        campos = []
        if h == "linea":
            campos.append(CampoVivo("largo", math.dist(a, cur), ("lineal", a, cur, None)))
            atras = self._atras_previa()
            if atras is not None:            # ángulo con la línea anterior de la cadena
                t0 = math.atan2(atras[1], atras[0])
                delta = math.atan2(atras[0] * u[1] - atras[1] * u[0], atras[0] * u[0] + atras[1] * u[1])
                campos.append(CampoVivo("angulo", math.degrees(abs(delta)),
                                        ("angular", a, min(t0, t0 + delta), max(t0, t0 + delta), False), True))
            else:                            # ángulo con el eje X del boceto
                ang = math.atan2(u[1], u[0]) % (2 * math.pi)
                campos.append(CampoVivo("angulo", math.degrees(ang), ("angular", a, 0.0, ang, True), True))
        elif h in ("rectangulo", "rectangulo_centro"):
            o = a if h == "rectangulo" else (2 * a[0] - cur[0], 2 * a[1] - cur[1])
            k = (cur[0], o[1])
            campos += [CampoVivo("ancho", abs(cur[0] - o[0]), ("lineal", o, k, cur)),
                       CampoVivo("alto", abs(cur[1] - o[1]), ("lineal", k, cur, o))]
        elif h == "rectangulo_3p":
            if len(pts) == 1:
                campos.append(CampoVivo("ancho", math.dist(a, cur), ("lineal", a, cur, None)))
            else:
                b = pts[1]
                ub = _unitario(b[0] - a[0], b[1] - a[1])
                n = (-ub[1], ub[0])
                d = (cur[0] - a[0]) * n[0] + (cur[1] - a[1]) * n[1]
                campos.append(CampoVivo("alto", abs(d), ("lineal", b, (b[0] + n[0] * d, b[1] + n[1] * d), a)))
        elif h == "circulo":
            r = math.dist(a, cur)
            campos.append(CampoVivo("diametro", 2 * r, ("radial", (a[0] - r * u[0], a[1] - r * u[1]), cur)))
        elif h == "arco":
            if len(pts) == 1:
                campos.append(CampoVivo("cuerda", math.dist(a, cur), ("lineal", a, cur, None)))
            else:
                circ = circunferencia_3_puntos(a, cur, pts[1])
                if circ is not None:
                    campos.append(CampoVivo("radio", circ[2], ("radial", (circ[0], circ[1]), cur)))
        elif h == "arco_centro":
            if len(pts) == 1:
                campos.append(CampoVivo("radio", math.dist(a, cur), ("radial", a, cur)))
            else:
                ini = pts[1]
                a0 = math.atan2(ini[1] - a[1], ini[0] - a[0])
                a1 = math.atan2(cur[1] - a[1], cur[0] - a[0])
                s = self._sentido_barrido()
                barrido = _barrido(a0, a1) if s > 0 else _barrido(a1, a0)
                t0, t1 = (a0, a0 + barrido) if s > 0 else (a0 - barrido, a0)
                campos.append(CampoVivo("barrido", math.degrees(barrido), ("angular", a, t0, t1, False), True))
        elif h == "circulo_2p":
            campos.append(CampoVivo("diametro", math.dist(a, cur), ("lineal", a, cur, None)))
        elif h == "linea_medio":
            ini = (2 * a[0] - cur[0], 2 * a[1] - cur[1])
            campos += [CampoVivo("largo", math.dist(ini, cur), ("lineal", ini, cur, None)), self._campo_angulo(a, u)]
        elif h == "elipse":
            if len(pts) == 1:
                campos += [CampoVivo("radio_mayor", math.dist(a, cur), ("radial", a, cur)), self._campo_angulo(a, u)]
            else:
                ue = _unitario(pts[1][0] - a[0], pts[1][1] - a[1])
                n = (-ue[1], ue[0])
                dn = (cur[0] - a[0]) * n[0] + (cur[1] - a[1]) * n[1]
                campos.append(CampoVivo("radio_menor", abs(dn), ("lineal", a, (a[0] + n[0] * dn, a[1] + n[1] * dn), pts[1])))
        elif h == "arco_tangente":
            p, s = self._tangente_de(self.clics[0][0])
            n = (-s[1], s[0])
            v = (cur[0] - p[0], cur[1] - p[1])
            alto = v[0] * n[0] + v[1] * n[1]
            if abs(alto) > 1e-9:
                r = (v[0] ** 2 + v[1] ** 2) / (2 * abs(alto))
                lado = 1 if alto > 0 else -1
                campos.append(CampoVivo("radio", r, ("radial", (p[0] + n[0] * lado * r, p[1] + n[1] * lado * r), cur)))
        elif h == "poligono_arista":
            campos += [CampoVivo("largo", math.dist(a, cur), ("lineal", a, cur, None)), self._campo_angulo(a, u),
                       CampoVivo("lados", self.lados, None, entero=True)]
        elif h.startswith("poligono_"):
            campos += [CampoVivo("radio", math.dist(a, cur), ("radial", a, cur)),
                       CampoVivo("lados", self.lados, None, entero=True)]
        elif h == "estrella":
            campos += [CampoVivo("radio", math.dist(a, cur), ("radial", a, cur)),
                       CampoVivo("puntas", self.opciones["puntas_estrella"], None, entero=True)]
        elif h in RANURAS_RECTAS:
            if len(pts) == 1:
                ini = (2 * a[0] - cur[0], 2 * a[1] - cur[1]) if h == "ranura_punto" else a
                campos += [CampoVivo("largo", math.dist(ini, cur), ("lineal", ini, cur, None)), self._campo_angulo(a, u)]
            else:
                ini, fin = self._eje_ranura(h, pts)
                ue = _unitario(fin[0] - ini[0], fin[1] - ini[1])
                n = (-ue[1], ue[0])
                d = (cur[0] - ini[0]) * n[0] + (cur[1] - ini[1]) * n[1]
                otro = (cur[0] - 2 * d * n[0], cur[1] - 2 * d * n[1])
                campos.append(CampoVivo("ancho", 2 * abs(d), ("lineal", otro, cur, None)))
        else:
            centro, R = self._arco_ranura(h, pts)
            rc = math.dist(cur, centro)
            uc = _unitario(cur[0] - centro[0], cur[1] - centro[1])
            otro = (centro[0] + (2 * R - rc) * uc[0], centro[1] + (2 * R - rc) * uc[1])
            campos.append(CampoVivo("ancho", 2 * abs(rc - R), ("lineal", otro, cur, None)))
        return [c for c in campos if c.clave in claves]

    @staticmethod
    def _campo_angulo(a, u):
        """Caja de ángulo absoluto (contra el eje X del boceto) de la dirección unitaria `u` desde `a`."""
        ang = math.atan2(u[1], u[0]) % (2 * math.pi)
        return CampoVivo("angulo", math.degrees(ang), ("angular", a, 0.0, ang, True), True)

    def _editar_campo_vivo(self, primera):
        """Escribir sobre la caja activa: se abre su campo con lo tecleado (Tab o Enter lo bloquean)."""
        campos = self._campos_vivos()
        if not campos:
            return
        campo = campos[self._activo % len(campos)]
        caja = next((r for c, _t, r, _z in self._disponer_campos(campos) if c.clave == campo.clave), None)
        self._cerrar_entrada()
        self._editando = campo.clave
        ed = self.entrada = EntradaValor([""], [primera], self)
        ed.tab_externo = True
        ed.aceptado.connect(lambda v: self._fin_edicion_viva(v[0], confirmar=True))
        ed.tabulado.connect(lambda texto, paso: self._fin_edicion_viva(texto, paso=paso))
        ed.cancelado.connect(self._cerrar_entrada)
        ed.campos[0].textChanged.connect(lambda _t: self.update())
        esquina = caja.topLeft() if caja is not None else self._pos_cursor + QPointF(14, 10)
        ed.move(int(esquina.x()), int(esquina.y()) - 3)
        ed.show()
        ed.raise_()
        ed.campos[0].setFocus()
        ed.campos[0].deselect()
        ed.campos[0].end(False)               # se sigue escribiendo después del primer dígito
        self.update()

    def _fin_edicion_viva(self, texto, confirmar=False, paso=0):
        """Tab / Enter / clic sobre la caja que se escribe: bloquea el valor (y Enter crea la geometría)."""
        clave = self._editando
        if clave is not None and not texto.strip() and confirmar and self.herramienta == "elipse":
            self.mensaje.emit("Expresión vacía.")        # B-717: Enter con la caja vacía no crea con el valor del ratón
            if self.entrada is not None:
                self.entrada.marcar_error()
            return False
        if clave is not None and texto.strip():
            try:
                valor = self._evaluar_campo(clave, texto)
            except (ErrorExpresion, ErrorBoceto, ValueError) as e:
                self.mensaje.emit(str(e))
                if self.entrada is not None:
                    self.entrada.marcar_error()
                return False
            self._bloquear(clave, texto, valor)
        self._cerrar_entrada()
        if confirmar:
            self._confirmar_vivo()
        elif paso:
            n = len(self._claves_vivas()) or 1
            self._activo = (self._activo + paso) % n
        self.update()
        return True

    def _confirmar_vivo(self):
        """Enter: crea con los valores escritos (y el ratón para lo que no se escribió)."""
        if not self.clics:
            return
        self._registrar_clic(None, self.cursor if self.cursor is not None else self.clics[-1][1])

    def _registrar_clic(self, pid, xy):
        """Suma un clic de la herramienta de dibujo, respetando los valores escritos en las cajas."""
        h = self.herramienta
        fase = [k for k in self._claves_vivas() if k in self._bloqueos]
        if fase:
            xy, pid = self._aplicar_bloqueos(xy), None
            if self.inf_actual is not None and math.dist(xy, self.inf_actual.xy) > 1e-9:
                self.inf_actual = None       # la cota escrita manda sobre el ajuste del ratón
            if h == "linea" and "angulo" in fase:
                self.inferencia = None          # el ángulo escrito manda (y da su propia cota o restricción)
            if h == "arco_centro" and "barrido" in fase:
                self._sentido_vivo = self._sentido_barrido() > 0
        bloqueos = dict(self._bloqueos) if h in VIVAS else {}
        previa = self._linea_previa()
        antes, n = set(self.b.curvas), len(self.clics)
        if n == 0:
            self._inf_inicio = self.inf_actual
            self._inf_clics = []
        self._guardar_inferencia_clic(pid, xy)
        if bloqueos:
            self._post_crear = lambda nuevas: self._cotas_de_lo_escrito(h, bloqueos, nuevas, previa)
        if h == "rectangulo_3p" and n == 1:
            self._inf_lado = self.inf_actual
            if self._inf_lado is not None and self._inf_lado.tipo in ("horizontal", "vertical") and not self.inferencia:
                self._inf_lado = None
        if h == "arco_centro" and n == 1:
            self._inf_radio = self.inf_actual          # el arco se crea en el tercer clic: se guarda la ayuda del radio
        if (h in ("linea_medio", "circulo") and n == 1) or (h in ("rectangulo_3p", "arco_centro") and n == 2):
            inf = self._inf_lado if h == "rectangulo_3p" else self._inf_radio if h == "arco_centro" else self.inf_actual
            if h in ("circulo", "arco_centro"):       # el radio perpendicular a una línea o tangente a otra circunferencia
                if inf is not None and inf.tipo == "perpendicular" and inf.restriccion:
                    inf = replace(inf, tipo="tangente", restriccion=("tangente", inf.objetivo))
                elif inf is None or inf.tipo not in ("tangente_circulo", "igual") or not inf.restriccion:
                    inf = None
            elif h == "linea_medio" and inf is not None and inf.tipo in ("horizontal", "vertical") and not self.inferencia:
                inf = None
            if inf is not None and inf.tipo in ("horizontal", "vertical", "tangente", "perpendicular", "paralela",
                                                "perpendicular_dir", "colineal", "tangente_circulo", "igual"):
                post_crear = self._post_crear

                def restringir(nuevas):
                    if post_crear is not None:
                        post_crear(nuevas)
                    curva = self.b.curvas[nuevas[0]]
                    self._restringir_inferencias(curva.id, [(curva.p2 if isinstance(curva, Linea) else None, inf)])

                self._post_crear = restringir
        self.clics.append((pid, xy))
        try:
            self._procesar_clics()
        finally:
            self._post_crear = None
            self._sentido_vivo = None
        if h in VIVAS:
            if set(self.b.curvas) != antes or len(self.clics) <= n:
                if set(self.b.curvas) != antes or not self.clics:
                    self._inf_inicio = None
                self._reiniciar_vivo()          # se creó la geometría (o se cortó): cajas nuevas
            else:
                self._activo = 0                # paso siguiente de la misma herramienta

    def _horizontal_o_vertical(self, lineas, bloqueos):
        """Un ángulo escrito de 0°/180° o 90°/270° se vuelve horizontal o vertical en la línea que lo cumple."""
        if "angulo" not in bloqueos:
            return
        ang = math.radians(bloqueos["angulo"][1])
        tipo = "horizontal" if abs(math.sin(ang)) < 1e-9 else "vertical" if abs(math.cos(ang)) < 1e-9 else None
        for lid in lineas:
            (x1, y1), (x2, y2) = self.b._extremos_linea(lid)
            fuera = abs(y2 - y1) if tipo == "horizontal" else abs(x2 - x1)     # lo que se aparta del eje pedido
            if tipo and fuera < 1e-6 * max(math.dist((x1, y1), (x2, y2)), 1.0):
                self.b.agregar_restriccion(tipo, [lid])
                return

    def _cotas_de_lo_escrito(self, h, bloqueos, nuevas, previa):
        """Lo escrito en las cajas se vuelve cota de boceto (como Fusion), sobre la geometría recién creada."""
        texto = {k: t for k, (t, _v) in bloqueos.items()}
        tipos = {k: self.b.curvas[k].tipo for k in nuevas}
        lineas = [k for k in nuevas if tipos[k] == "linea"]
        arcos = [k for k in nuevas if tipos[k] == "arco"]
        circulos = [k for k in nuevas if tipos[k] == "circulo"]
        cota = self.b.agregar_cota
        if h == "linea" and lineas:
            lid = lineas[0]
            if "largo" in texto:
                cota("distancia", [lid], texto["largo"])
            if "angulo" in texto:
                if previa in self.b.curvas:
                    ln, t = self.b.curvas[previa], texto["angulo"]
                    if ln.p2 == self.b.curvas[lid].p1:     # la cota mide el desvío entre las direcciones
                        t = formato.numero(180 - bloqueos["angulo"][1], True) if _es_numero(t) else f"180 - ({t})"
                    cota("angulo", [previa, lid], t)
                else:
                    ang = math.radians(bloqueos["angulo"][1])
                    if abs(math.sin(ang)) < 1e-9:
                        self.b.agregar_restriccion("horizontal", [lid])
                    elif abs(math.cos(ang)) < 1e-9:
                        self.b.agregar_restriccion("vertical", [lid])
                    else:                       # FU-3, como Fusion: la primera línea se acota contra el eje X
                        self.b.asegurar_referencias([Boceto.EJE_X])
                        medida, t = self.b.medir_cota("angulo", [lid, Boceto.EJE_X]), texto["angulo"]
                        if abs(medida - bloqueos["angulo"][1]) > 1e-6:      # 150° mide 150, pero 210° mide 150
                            t = formato.numero(medida, True)
                        cota("angulo", [lid, Boceto.EJE_X], t)
        elif h in ("rectangulo", "rectangulo_centro", "rectangulo_3p") and len(lineas) >= 2:
            if "ancho" in texto:
                cota("distancia", [lineas[0]], texto["ancho"])
            if "alto" in texto:
                cota("distancia", [lineas[1]], texto["alto"])
        elif h in ("circulo", "circulo_2p") and circulos and "diametro" in texto:
            cota("diametro", [circulos[0]], texto["diametro"])
        elif h == "linea_medio" and lineas:
            if "largo" in texto:
                cota("distancia", [lineas[0]], texto["largo"])
            self._horizontal_o_vertical(lineas, bloqueos)
        elif h == "elipse" and len(lineas) >= 2:        # los ejes de construcción: la cota es el eje entero
            for clave, lid in (("radio_mayor", lineas[0]), ("radio_menor", lineas[1])):
                if clave in texto:
                    t = texto[clave]
                    cota("distancia", [lid], formato.numero(2 * _numero(t)) if _es_numero(t) else f"2 * ({t})")
            self._horizontal_o_vertical(lineas[:1], bloqueos)
        elif h == "poligono_arista" and lineas:
            if "largo" in texto:
                cota("distancia", [lineas[0]], texto["largo"])
            self._horizontal_o_vertical(lineas, bloqueos)
        elif h == "arco" and arcos:
            arco = self.b.curvas[arcos[0]]
            if "cuerda" in texto:
                cota("distancia", [arco.inicio, arco.fin], texto["cuerda"])
            if "radio" in texto:
                cota("radio", [arcos[0]], texto["radio"])
        elif h in ("arco_centro", "arco_tangente") and arcos and "radio" in texto:
            cota("radio", [arcos[0]], texto["radio"])
        elif (h.startswith("poligono_") or h == "estrella") and circulos and "radio" in texto:
            cota("radio", [circulos[0]], texto["radio"])
        elif h.startswith("ranura_") and arcos:
            self._horizontal_o_vertical(lineas[-1:], bloqueos)
            tapa = min(arcos, key=self.b.radio)            # los extremos: los arcos de radio = medio ancho
            if "ancho" in texto:
                cota("diametro", [tapa], texto["ancho"])
            if "largo" in texto and lineas:
                largo = texto["largo"]
                if h == "ranura_total":                    # la cota va entre centros: largo total − ancho
                    ancho = texto.get("ancho") or formato.numero(2 * self.b.radio(tapa))
                    largo = (formato.numero(_numero(largo) - _numero(ancho)) if _es_numero(largo) and _es_numero(ancho)
                             else f"({largo}) - ({ancho})")
                cota("distancia", [lineas[-1]], largo)      # el eje de construcción, entre los centros

    def _color_cota(self):
        return COTA_OSCURO if self._oscuro() else COTA_CLARO

    def _color_fondo(self):
        """El color del lienzo detrás del texto de una cota: así el valor se lee sobre cualquier línea."""
        if self.visor is not None or self._oscuro():
            return QColor(temas.color("visor_arriba"))
        return QColor(FONDO_LIENZO)

    def _color_resalte(self):
        """Acento con el que se resalta la cota bajo el ratón (el mismo acento de la app)."""
        return QColor(temas.color("acento"))

    def _trazo_vivo(self, campo):
        """(segmentos, flechas [(punta, desde)], centro de la caja) en px de la cota provisional."""
        if campo.cota is None:
            return None
        tipo = campo.cota[0]
        if tipo == "lineal":
            _, a, b, lado = campo.cota
            pa, pb = self.a_px(*a), self.a_px(*b)
            dx, dy = pb.x() - pa.x(), pb.y() - pa.y()
            largo = math.hypot(dx, dy)
            if largo < 1:
                return [], [], pb + QPointF(36, -22)
            n = QPointF(-dy / largo, dx / largo)
            medio = (pa + pb) / 2
            if lado is not None:
                pl = self.a_px(*lado)
                if (pl.x() - medio.x()) * n.x() + (pl.y() - medio.y()) * n.y() > 0:
                    n = QPointF(-n.x(), -n.y())
            qa, qb = pa + n * 24, pb + n * 24
            return [(pa + n * 3, qa + n * 4), (pb + n * 3, qb + n * 4), (qa, qb)], [(qa, qb), (qb, qa)], (qa + qb) / 2
        if tipo == "angular":
            _, c, t0, t1, referencia = campo.cota
            r = 40 / max(self.px_por_mm(), 1e-9)
            pasos = max(4, int(abs(t1 - t0) / 0.08))
            arco = [self.a_px(c[0] + r * math.cos(t0 + (t1 - t0) * i / pasos), c[1] + r * math.sin(t0 + (t1 - t0) * i / pasos))
                    for i in range(pasos + 1)]
            segmentos = list(zip(arco, arco[1:], strict=False))
            if referencia:                   # el eje de referencia del ángulo (horizontal del boceto)
                segmentos.append((self.a_px(*c), self.a_px(c[0] + 1.4 * r, c[1])))
            tm, r2 = (t0 + t1) / 2, 66 / max(self.px_por_mm(), 1e-9)
            flechas = [(arco[-1], arco[-2]), (arco[0], arco[1])] if abs(t1 - t0) > 0.15 else []
            return segmentos, flechas, self.a_px(c[0] + r2 * math.cos(tm), c[1] + r2 * math.sin(tm))
        _, a, b = campo.cota
        pa, pb = self.a_px(*a), self.a_px(*b)
        dx, dy = pb.x() - pa.x(), pb.y() - pa.y()
        largo = math.hypot(dx, dy) or 1.0
        return [(pa, pb)], [(pb, pa)], pb + QPointF(dx / largo, dy / largo) * 40

    def _disponer_campos(self, campos):
        """[(campo, texto, caja QRectF, trazo)]: dónde va cada caja (sin pisarse)."""
        fm = QFontMetricsF(temas.qfont_cotas(9))
        cur = self._cursor_efectivo() or (0.0, 0.0)
        salida, ocupadas = [], []
        for campo in campos:
            trazo = self._trazo_vivo(campo)
            if trazo is not None:
                centro = trazo[2]
            elif ocupadas:
                centro = ocupadas[-1].center() + QPointF(0, 26)
            else:
                centro = self.a_px(*cur) + QPointF(50, 30)
            texto = texto_valor(campo.valor, campo.angular, campo.entero)
            ancho = fm.horizontalAdvance(texto) + 16 + (14 if campo.clave in self._bloqueos else 0)
            alto = fm.height() + 4              # el recuadro de agarre sigue al tamaño real del texto
            caja = QRectF(centro.x() - ancho / 2, centro.y() - alto / 2, ancho, alto)
            for _ in range(12):
                if not any(caja.intersects(o) for o in ocupadas):
                    break
                caja.translate(0, 24)
            ocupadas.append(caja)
            salida.append((campo, texto, caja, trazo))
        return salida

    @staticmethod
    def _candado(p, x, y):
        p.save()
        p.setPen(QPen(QColor(80, 80, 88), 1.3))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(x + 1.5, y, 6, 8), 0, 180 * 16)
        p.setBrush(QColor(80, 80, 88))
        p.drawRect(QRectF(x, y + 4, 9, 7))
        p.restore()

    def _dibujar_campos_vivos(self, p):
        campos = self._campos_vivos()
        self._cajas_vivas = []
        if not campos:
            return
        color = self._color_cota()
        activo = self._activo % len(campos)
        p.setFont(temas.qfont_cotas(9))
        fm = p.fontMetrics()
        for i, (campo, texto, caja, trazo) in enumerate(self._disponer_campos(campos)):
            self._cajas_vivas.append((campo.clave, caja))
            if trazo is not None:
                p.setPen(QPen(color, 1))
                p.setBrush(color)
                for a, b in trazo[0]:
                    p.drawLine(a, b)
                for punta, desde in trazo[1]:
                    self._flecha(p, punta, desde)
            if campo.clave == self._editando and self.entrada is not None:
                continue                      # encima está el campo donde se escribe
            p.setPen(QPen(AZUL_CAJA, 1.5) if i == activo else QPen(QColor(150, 150, 156), 1))
            p.setBrush(QColor(255, 255, 255))
            p.drawRect(caja)
            zona = QRectF(caja.x() + 7, caja.y() + 3, fm.horizontalAdvance(texto) + 1, 14)
            if i == activo:                   # texto seleccionado: lo que se escriba lo reemplaza
                p.fillRect(zona.adjusted(-2, -1, 2, 1), AZUL_CAJA)
                p.setPen(QColor(255, 255, 255))
            else:
                p.setPen(QColor(30, 30, 34))
            p.drawText(zona, Qt.AlignVCenter | Qt.AlignLeft, texto)
            if campo.clave in self._bloqueos:
                self._candado(p, caja.right() - 14, caja.y() + 4)
        p.setBrush(Qt.NoBrush)

    def _abrir_cota(self, tipo, entidades, pos):
        original = (tipo, list(entidades), pos)
        if tipo in ("radio", "diametro"):
            tipo = self._opc_cota.get("tipo", tipo)             # menú previo: Radio / Diámetro
        previa = Cota(-1, tipo, entidades, "", {})
        if tipo == "distancia" and sum(bool(getattr(self.b.curvas.get(i), "eje", False)) for i in entidades) == 1:
            previa.datos["diametral"] = True        # Fusion: una cota con la línea central es un diámetro
        if self.b.admite_modo(tipo, entidades) and "modo" in self._opc_cota:
            previa.datos["modo"] = self._opc_cota["modo"]       # menú previo: Centro / Tangente
        try:
            self.b._validar_cota(tipo, entidades)
            self.b.ubicar_cota(previa, self.a_mm(pos))  # el clic ubica la línea de cota y su texto (o el cuadrante)
            actual = self.b.medir(previa)
        except ErrorBoceto as e:
            self.mensaje.emit(str(e))
            self.picks = []
            return

        def aceptar(v):
            referencia = self._opc_cota.get("referencia", False)     # una cota de referencia mide: ignora el texto
            nombre, texto = separar_nombre(v[0])                    # «ANCHO=20mm» nombra el parámetro de la cota
            texto = texto or formato.numero(actual, angular=tipo == "angulo")
            self._comprobar_nombre_cota(nombre)
            if not referencia:
                validar_valor_cota(tipo, self.evaluar(texto, _tipo_valor(tipo), estricto=True))     # −5 o 0: la caja queda en rojo

            def crear():
                cota = self.b.cotas[self.b.agregar_cota(tipo, entidades, texto, previa.datos, referencia=referencia)]
                if nombre:
                    cota.nombre, self._nombradas[nombre] = nombre, cota.id
                if not referencia and self._sobre_restringe(cota.id):   # Fusion: la que sobra entra de referencia
                    cota.referencia, cota.expresion = True, repr(actual)
                    self.mensaje.emit("La cota sobre-restringiría el boceto: se creó como cota de referencia.")
            self.aplicar_cambio(crear)
            self.picks, self._opc_cota = [], {}
            self._esperando_ubicacion = False
        unidad = "°" if tipo == "angulo" else ""
        self._abrir_entrada([TIPOS_COTA[tipo] + (f" ({unidad})" if unidad else "")],
                            [f"{actual:.3f}".rstrip("0").rstrip(".")], pos, aceptar)
        self._cota_abierta = original
        # cota lineal, de radio o de diámetro (B-439, como Fusion): se dibuja con sus líneas mientras se escribe
        if self.b.ejes_cota(previa) is not None or tipo in ("radio", "diametro"):
            self._cota_previa, self._cota_editada = previa, -1

    def _opciones_cota_mantenido(self):
        """Clic derecho mantenido con una cota a medias: abre sus opciones (el clic rápido cancela)."""
        if self._derecho is not None and self.herramienta == "cota" and self.picks:
            _pos, global_ = self._derecho
            self._derecho = None
            self._menu_cota_previa().exec(global_)

    def _menu_cota_previa(self):
        """Clic derecho antes de ubicar la cota (Fusion, «Dimension sketch geometry» › Tips): Driven o Driving,
        Radio o Diámetro, Centro o Tangente. Lo elegido vale para la cota que se está poniendo."""
        m = QMenu(self)
        abierta, opc = self._cota_abierta, self._opc_cota

        def elegir(clave, valor):
            opc[clave] = valor
            if abierta is not None and clave != "referencia":       # tipo y modo cambian lo que se mide
                self._abrir_cota(*abierta)

        def grupo(clave, items, actual):
            for valor, texto in items:
                a = m.addAction(texto, lambda c=clave, x=valor: elegir(c, x))
                a.setCheckable(True)
                a.setChecked(actual == valor)
        grupo("referencia", ((False, "Cota conductora (driving)"), (True, "Cota de referencia (driven)")),
              opc.get("referencia", False))
        if abierta is not None:
            tipo, ents, _ = abierta
            if tipo in ("radio", "diametro"):
                m.addSeparator()
                grupo("tipo", (("radio", "Radio"), ("diametro", "Diámetro")), opc.get("tipo", tipo))
            if self.b.admite_modo(tipo, ents):
                m.addSeparator()
                grupo("modo", (("centro", "Centro"), ("tangente", "Tangente")), opc.get("modo", "centro"))
        return m

    def _nombre_libre(self):
        """Primer dN que ni el documento ni otra cota de este boceto usan (el documento lo respeta al nombrar)."""
        usados = {k.nombre for k in self.b.cotas.values()}
        n = 1
        while f"d{n}" in usados or self._existe_en_documento(f"d{n}"):
            n += 1
        return f"d{n}"

    def _comprobar_nombre_cota(self, nombre, cota=None):
        """El nombre tipeado en la caja («ANCHO=20») tiene que ser válido y estar libre (la caja queda en rojo)."""
        if not nombre or (cota is not None and nombre == cota.nombre):
            return
        validar_nombre(nombre)
        if any(k.nombre == nombre for k in self.b.cotas.values()) or self._existe_en_documento(nombre):
            raise ErrorExpresion(f"Ya existe el parámetro '{nombre}': elegí otro nombre.")

    def _existe_en_documento(self, nombre):
        for tipo in (LONGITUD, ANGULO, ESCALAR):      # el parámetro puede ser de cualquiera de los tres tipos
            try:
                self._evaluar_doc(nombre, tipo)
                return True
            except ErrorExpresion:
                pass
        return False

    def _actualizar_cita(self, pos):
        """Cota bajo el ratón: con una caja de valor abierta se resalta para citarla (Fusion); en Seleccionar, sin
        caja, muestra su cartel «nombre : valor unidad»."""
        citando = self.entrada is not None and (self._cota_abierta is not None or self._cota_editada is not None)
        cid = None
        if citando:
            zona = self._zona_en(pos)
            if zona in self.b.cotas and zona != self._cota_editada:
                cid = zona
        elif self.entrada is None and self.herramienta == "seleccionar" and self._arrastre is None:
            cid = self._zona_sobre if self._zona_sobre in self.b.cotas else None
        if cid == self._cita_sobre:
            return
        self._cita_sobre = cid
        if cid is None:
            QToolTip.hideText()
            if citando:
                self.unsetCursor()
        else:
            cota = self.b.cotas[cid]
            angular = cota.tipo == "angulo"
            try:
                valor = formato.numero(self.b.medir(cota), angular=angular)
            except (ErrorBoceto, KeyError, ZeroDivisionError):
                return
            QToolTip.showText(self.mapToGlobal(pos.toPoint()),
                              f"{cota.nombre or self._nombre_libre()} : {valor}{'°' if angular else ' mm'}")
            if citando:
                self.setCursor(Qt.PointingHandCursor)
        self.update()

    def _citar_cota(self, pos):
        """Fusion: con la caja de valor de una cota abierta, un clic en otra cota pone su nombre (dN) en la
        expresión, en lugar de lo seleccionado. True si el clic se usó así."""
        if self._cota_abierta is None and self._cota_editada is None:
            return False
        cid = self._zona_en(pos)
        cota = self.b.cotas.get(cid)
        if cota is None or cid == self._cota_editada:
            return False
        if not cota.nombre:                  # el documento nombra las cotas nuevas al terminar el boceto: se adelanta
            cota.nombre = self._nombre_libre()
            self._nombradas[cota.nombre] = cid
        campo = self.entrada.campos[0]
        if campo.text() == self._texto_inicial:      # el clic en el lienzo le quitó el foco y la selección al valor
            campo.selectAll()
        campo.insert(cota.nombre)
        campo.setFocus()
        return True

    def _arco_cota(self, c):
        """(vértice, t0, t1) del arco de una cota de ángulo, o None si las líneas son paralelas."""
        try:
            return self.b.arco_angulo(c)
        except (ErrorBoceto, KeyError, ZeroDivisionError):
            return None

    def _sobre_restringe(self, cid):
        """Criterio de la API (BOC-1): la cota driving `cid` debe bajar los GDL sin dejar el boceto en conflicto."""
        valores, sin = self.valores_cotas(), self.b.copia()
        del sin.cotas[cid]
        con = resolver(self.b.copia(), valores)
        return not con.ok or con.gdl >= resolver(sin, valores).gdl

    def alternar_referencia(self, cid):
        """Cota de referencia (driven) ↔ driving, con Mayús + doble clic (BOC-3 la suma al menú de la cota).
        Toma la medida actual; si volver a driving sobre-restringiría, sigue de referencia y avisa."""
        cota = self.b.cotas[cid]

        def cambiar():
            cota.referencia = not cota.referencia
            cota.expresion = repr(self.b.medir(cota))
            if not cota.referencia and self._sobre_restringe(cid):
                raise ErrorBoceto("La cota sobre-restringe: sigue de referencia.")
        self.aplicar_cambio(cambiar)

    def _menu_cota(self, cid, pos=None):
        """Clic derecho en una cota (Fusion): editar el valor, renombrar el parámetro, referencia,
        radio/diámetro, centro/tangente y borrar."""
        QToolTip.hideText()
        self._cita_sobre = None
        cota = self.b.cotas[cid]
        m = QMenu(self)
        centro = pos if pos is not None else (self._zonas_cotas.get(cid) or QRectF()).center()
        m.addAction("Editar valor…", lambda: self.editar_cota(cid, centro))
        m.addAction("Renombrar parámetro…", lambda: self.renombrar_cota(cid))
        m.addSeparator()
        a = m.addAction("Cota de referencia", lambda: self.alternar_referencia(cid))
        a.setCheckable(True)
        a.setChecked(cota.referencia)
        m.addSeparator()
        opciones = ((("radio", "Radio"), ("diametro", "Diámetro")) if cota.tipo in ("radio", "diametro") else ())
        for tipo, texto in opciones:
            a = m.addAction(texto, lambda t=tipo: self.aplicar_cambio(lambda: self.b.cambiar_cota(cid, tipo=t)))
            a.setCheckable(True)
            a.setChecked(cota.tipo == tipo)
        if self.b.admite_modo(cota.tipo, cota.entidades):
            for modo, texto in (("centro", "Centro"), ("tangente", "Tangente")):
                a = m.addAction(texto, lambda md=modo: self.aplicar_cambio(lambda: self.b.cambiar_cota(cid, modo=md)))
                a.setCheckable(True)
                a.setChecked(cota.datos.get("modo", "centro") == modo)
        m.addSeparator()
        m.addAction("Borrar", lambda: self.aplicar_cambio(lambda: self.b.eliminar(cid)))
        return m

    def renombrar_cota(self, cid):
        """Menú de la cota: le da un nombre propio (el parámetro que se cita en las expresiones). Un nombre
        inválido o ya usado muestra el error y no cambia nada; es un solo paso de deshacer."""
        cota = self.b.cotas[cid]
        nombre, ok = QInputDialog.getText(self, "Renombrar parámetro", "Nombre del parámetro:",
                                          text=cota.nombre or self._nombre_libre())
        if not ok:
            return
        nombre = nombre.strip()
        try:
            if not nombre:
                raise ErrorExpresion("El nombre del parámetro no puede estar vacío.")
            self._comprobar_nombre_cota(nombre, cota)
        except ErrorExpresion as e:
            self.mensaje.emit(str(e))
            return
        if nombre == cota.nombre:
            return

        def cambiar():
            cota.nombre = nombre
            self._nombradas[nombre] = cota.id
        self.aplicar_cambio(cambiar)

    def _tipo_dos_puntos(self, pos):
        """Tipo de la cota entre los dos puntos elegidos, según dónde esté `pos` (px)."""
        (x1, y1), (x2, y2) = self.b.coords(self.picks[0]), self.b.coords(self.picks[1])
        if self.opcion_cota == "alineada":
            return "distancia"
        if abs(y2 - y1) < 1e-6:
            return "distancia_h"
        if abs(x2 - x1) < 1e-6:
            return "distancia_v"
        medio = self.a_px((x1 + x2) / 2, (y1 + y2) / 2)
        return "distancia_h" if abs(pos.y() - medio.y()) > abs(pos.x() - medio.x()) else "distancia_v"

    def _tipo_linea(self, pos):
        """H-106: tipo de la cota de una línea sola según dónde esté `pos` (px). Con el cursor frente a la línea (su
        proyección cae dentro del largo), alineada; más allá de un extremo, horizontal o vertical como con dos puntos."""
        p1, p2 = (self.b.coords(p) for p in self.b.curvas[self.picks[0]].puntos())
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        largo = math.hypot(dx, dy)
        c = self.a_mm(pos)
        if (self.opcion_cota == "alineada" or abs(dx) < 1e-6 or abs(dy) < 1e-6
                or 0 <= ((c[0] - p1[0]) * dx + (c[1] - p1[1]) * dy) / largo <= largo):
            return "distancia"
        return "distancia_h" if abs(c[1] - (p1[1] + p2[1]) / 2) > abs(c[0] - (p1[0] + p2[0]) / 2) else "distancia_v"

    def _cota_viva(self):
        """Cota provisional que se dibuja: la que se está escribiendo o, con la herramienta Cota y una línea (o
        dos puntos) ya elegidos, la que sigue al cursor hasta el clic que la ubica."""
        if self._cota_previa is not None:
            return self._cota_previa
        if self.herramienta != "cota" or self.entrada is not None or not self.picks or self._pos_cursor is None:
            return None
        if self._esperando_ubicacion and self.b.tipo_de(self.picks[0]) == "linea":
            previa = Cota(-1, "angulo", list(self.picks), "", {})     # BOC-25: el ángulo del cuadrante del cursor
            self.b.ubicar_cota(previa, self.a_mm(self._pos_cursor))
            return previa
        if self._esperando_ubicacion:
            tipo = self._tipo_dos_puntos(self._pos_cursor)
        elif len(self.picks) == 1 and self.b.tipo_de(self.picks[0]) == "linea":
            tipo = self._tipo_linea(self._pos_cursor)
        else:
            return None
        previa = Cota(-1, tipo, list(self.picks), "", {})
        if self.b.ejes_cota(previa) is None:
            return None
        self.b.ubicar_cota(previa, self.a_mm(self._pos_cursor))
        return previa

    def _clic_cota(self, pos):
        ent = self.entidad_en(pos)
        if not self.picks:
            if ent is None:
                return
            t = self.b.tipo_de(ent)
            if t in ("circulo", "arco"):
                self.picks = [ent]
                self._abrir_cota("diametro" if t == "circulo" else "radio", [ent], pos)
            else:
                self.picks = [ent]
            return
        primero, t1 = self.picks[0], self.b.tipo_de(self.picks[0])
        if self._esperando_ubicacion:        # dos puntos: la ubicación decide horizontal / vertical; dos líneas, el ángulo
            tipo = "angulo" if t1 == "linea" else self._tipo_dos_puntos(pos)
            self._abrir_cota(tipo, list(self.picks), pos)
            return
        if ent is None or ent == primero:
            if t1 == "linea":
                self._abrir_cota(self._tipo_linea(pos), [primero], pos)
            return
        t2 = self.b.tipo_de(ent)
        if t1 == "punto" and t2 == "punto":
            self.picks = [primero, ent]
            self._esperando_ubicacion = True
            self.mensaje.emit("Clic para ubicar la cota (arriba/abajo: horizontal; a un costado: vertical).")
        elif {t1, t2} == {"punto", "linea"}:
            ents = [primero, ent] if t1 == "punto" else [ent, primero]
            self._abrir_cota("distancia", ents, pos)
        elif t1 == "linea" and t2 == "linea":
            d1, d2 = self.b._direccion(primero), self.b._direccion(ent)
            if abs(d1[0] * d2[1] - d1[1] * d2[0]) < 1e-6:
                self._abrir_cota("distancia", [primero, ent], pos)
            else:                            # Fusion: el ángulo sigue al cursor hasta el clic que elige el cuadrante
                self.picks = [primero, ent]
                self._esperando_ubicacion = True
                self.mensaje.emit("Clic para ubicar la cota de ángulo: se mide el ángulo del lado donde está el cursor.")
        elif {t1, t2} & {"circulo", "arco"} or {t1, t2} == {"punto", "spline"}:
            self._abrir_cota("distancia", [primero, ent], pos)    # al centro; el menú de la cota pasa a tangente
        else:
            self.mensaje.emit("Esa combinación no se puede acotar.")
            self.picks = []
