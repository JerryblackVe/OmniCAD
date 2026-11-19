"""LienzoProyeccionMixin: métodos del lienzo por tema."""

from .editor_boceto_comun import (
    Boceto,
    CAPA_PREVIA_ISO,
    CAPA_PROYECCION,
    COLOR_PREVIA_ISO,
    COMANDO_PROYECCION,
    ErrorBoceto,
    HERRAMIENTAS,
    PROYECCION,
    QPen,
    QPoint,
    QPointF,
    Qt,
    YA_PROYECTADA,
    np,
    puntos_primitiva,
    texto_proyeccion,
)


class LienzoProyeccionMixin:
    def _tanda_proyeccion(self, forma, modo, ref, tipo=None):
        """Argumentos de `Boceto.agregar_proyeccion` para una forma OCC, con el tipo de línea y el vínculo actuales.
        Un cuerpo entero (`tipo` "cuerpo", filtro Cuerpos) se proyecta como su silueta cerrada (B-119)."""
        from ..timeline import entidades as ent
        if self.plano is None:
            raise ErrorBoceto("El boceto no tiene plano.")
        clave = "intersect" if modo == "intersecar" else "silueta" if tipo == "cuerpo" else "project"
        prims, puntos = ent.proyectar_entidad(ent.Entidad(tipo or "forma", forma=forma), self.plano, clave)
        origen = {"modo": clave, "refs": [ref]} if ref else None
        if not self.opciones["vinculo_proyeccion"]:          # Projection Link apagado: queda congelada
            origen = None
        return prims, puntos, self.construccion, origen

    def _aplicar_proyecciones(self, tandas):
        """Agrega `tandas` en un solo paso de deshacer y dice qué pasó de verdad. Si no cambiaría nada, no deja paso."""
        resumen = self.b.simular_proyecciones(tandas)
        if not resumen["cambia"]:
            self.mensaje.emit(YA_PROYECTADA)
            return False
        if not self.aplicar_cambio(lambda: [self.b.agregar_proyeccion(*t) for t in tandas], anclar=False):
            return False
        nombre = HERRAMIENTAS[self.herramienta][0] if self.herramienta in PROYECCION else "Proyectar"
        self.mensaje.emit(f"{nombre}: {texto_proyeccion(resumen)}")
        return True

    def proyectar_forma(self, forma, modo="proyectar", ref=None, tipo=None):
        """Agrega al boceto la proyección (o la intersección) de una forma OCC sobre su plano, sin pasar por la tarjeta.
        Con `ref` (la referencia persistente de lo elegido) la proyección sigue al modelo cuando este cambia (B-09)."""
        tanda = self._tanda_proyeccion(forma, modo, ref, tipo)
        if not tanda[0] and not tanda[1]:
            self.mensaje.emit("Eso no deja nada sobre el plano del boceto.")
            return False
        return self._aplicar_proyecciones([tanda])

    def _hay_tarjeta_proyeccion(self):
        return self.herramienta in COMANDO_PROYECCION and self._revincular is None

    def _elegir_proyeccion(self, info):
        """Clic en el modelo: suma lo elegido a la selección de la tarjeta; otro clic en lo mismo lo saca. El boceto no
        cambia: eso lo hace Aceptar."""
        ref, forma = info.get("ref"), info.get("forma")
        repetido = next((e for e in self._elegidos_proy
                         if (e["ref"] == ref if ref else e["forma"].IsSame(forma))), None)
        if repetido is not None:
            self._elegidos_proy.remove(repetido)
        else:
            self._elegidos_proy.append(info)
        self._nota_proy = ""
        self._emitir_proyeccion()

    def quitar_proyeccion(self, indice):
        """Tarjeta: la ✕ de una referencia la saca de la selección."""
        del self._elegidos_proy[indice]
        self._nota_proy = ""
        self._emitir_proyeccion()

    def cambiar_opcion_proyeccion(self):
        """Cambió el filtro o el vínculo. Lo que el filtro nuevo no admite sale de la selección y se dice cuánto: nunca se
        proyecta algo que la tarjeta no muestra."""
        admitidos = self._filtros_proyeccion()
        quedan = [e for e in self._elegidos_proy if e.get("tipo") in admitidos]
        sacados = len(self._elegidos_proy) - len(quedan)
        self._elegidos_proy = quedan
        self._nota_proy = (f"El filtro sacó {sacados} {'referencia' if sacados == 1 else 'referencias'} de la selección."
                           if sacados else "")
        self._emitir_proyeccion()

    def _calcular_proyeccion(self):
        """(tandas, resumen, error) de lo elegido. Cada referencia se comprueba y se calcula acá: un fallo se dice en la
        tarjeta, no aparece recién al aceptar."""
        from ..nucleo import geometria as geo
        from ..timeline import entidades as ent
        tandas, sin_nada = [], 0
        estado = self.estado_referencias()
        for e in self._elegidos_proy:
            try:
                if estado is not None and e.get("ref"):
                    entidad = ent.resolver(e["ref"], estado)
                else:
                    entidad = None
                if e.get("tipo") in ("plano", "eje", "punto", "punto_boceto"):
                    # H-54: planos, ejes y puntos de trabajo o de boceto: la proyección sale de la entidad
                    # resuelta (como la API); sus líneas son infinitas y al recalcular se recortan al modelo
                    if self.plano is None:
                        raise ErrorBoceto("El boceto no tiene plano.")
                    if entidad is None:
                        raise ent.ErrorReferencia("La referencia de trabajo no se puede resolver.")
                    prims, puntos = ent.proyectar_entidad(entidad, self.plano)
                    origen = {"modo": "project", "refs": [e["ref"]]} if self.opciones["vinculo_proyeccion"] else None
                    if origen is not None and prims:
                        origen["infinitas"] = {str(k): 0.0 for k in range(len(prims))}
                    tanda = (prims, puntos, self.construccion, origen)
                else:
                    tanda = self._tanda_proyeccion(e["forma"], self.herramienta, e.get("ref"), e.get("tipo"))
            except (ent.ErrorReferencia, ent.ReferenciaMalFormada):
                return [], None, f"La referencia de «{self._nombre_elegido(e)}» ya no es válida: sacala y elegila de nuevo."
            except (geo.ErrorGeometria, ErrorBoceto) as error:
                return [], None, f"No se pudo calcular «{self._nombre_elegido(e)}»: {error}"
            sin_nada += not tanda[0] and not tanda[1]
            tandas.append(tanda)
        if sin_nada == len(tandas):
            return [], None, "Eso no deja nada sobre el plano del boceto."
        return tandas, self.b.simular_proyecciones(tandas), ""

    def _nombre_elegido(self, e):
        """Cómo se lee una referencia en la tarjeta: qué es y de qué cuerpo («Arista circular · Cuerpo1»)."""
        ref = e.get("ref") or {}
        estado = self.estado_referencias()
        cuerpo = getattr(getattr(estado, "cuerpos", {}).get(ref.get("cuerpo")), "nombre", ref.get("cuerpo") or "")
        geom = (ref.get("firma") or {}).get("geom")
        tipo = {"cuerpo": "Cuerpo", "vertice": "Vértice", "cara": "Cara plana" if geom == "plano" else "Cara",
                "curva_boceto": "Curva de boceto", "plano": "Plano", "eje": "Eje",
                "punto": "Punto de trabajo", "punto_boceto": "Punto de boceto",
                "arista": {"linea": "Arista recta", "circulo": "Arista circular"}.get(geom, "Arista")}.get(e.get("tipo"), "Geometría")
        return cuerpo if tipo == "Cuerpo" and cuerpo else f"{tipo} · {cuerpo}" if cuerpo else tipo

    def estado_proyeccion(self):
        """Lo que muestra la tarjeta: las referencias elegidas, el resultado provisional y si se puede aceptar."""
        vacio = "Elegí cuerpos en el modelo." if self.opciones["filtro_proyectar"] == "cuerpos" else (
            "Elegí caras, aristas, vértices, planos, ejes o puntos en el modelo.")
        e = {"elegidos": [self._nombre_elegido(x) for x in self._elegidos_proy], "valido": False, "nota": self._nota_proy,
             "resultado": vacio, "error": "", "prims": [], "puntos": []}
        if not self._elegidos_proy:
            return e
        tandas, resumen, error = self._calcular_proyeccion()
        e["tandas"] = tandas
        if error:
            e.update(resultado="", error=error)
        elif not resumen["cambia"]:
            e["resultado"] = YA_PROYECTADA
        else:
            e.update(resultado=texto_proyeccion(resumen), valido=True)
        e["prims"] = [p for t in tandas for p in t[0]]
        e["puntos"] = [q for t in tandas for q in t[1]]
        return e

    def _emitir_proyeccion(self):
        """Le manda el estado a la tarjeta, marca lo elegido en el modelo y repinta la vista previa."""
        self._previa_proy = {"prims": [], "puntos": []}
        if self._hay_tarjeta_proyeccion():
            estado = self.estado_proyeccion()
            self._previa_proy = estado
            self.proyeccion_estado.emit(estado)
        if self.visor is not None and hasattr(self.visor, "set_capa"):
            capas = [capa for e in self._elegidos_proy for capa in e.get("dibujo") or []]
            self.visor.set_capa(CAPA_PROYECCION, capas or None)
        self.update()

    def aceptar_proyeccion(self):
        """Aceptar (botón o Enter): todo lo elegido entra en una sola transacción y la herramienta termina; el boceto
        sigue abierto."""
        e = self.estado_proyeccion()
        if not e["valido"]:
            self.mensaje.emit(e["error"] or e["resultado"])
            return False
        if not self._aplicar_proyecciones(e["tandas"]):
            return False
        self._elegidos_proy = []
        nombre, texto = HERRAMIENTAS[self.herramienta][0], e["resultado"]
        self.set_herramienta("seleccionar")
        self.mensaje.emit(f"{nombre}: {texto}")
        return True

    def cancelar_proyeccion(self):
        """Cancelar (botón, ✕ o Esc): descarta lo provisional, sin tocar el boceto, y sale de la herramienta."""
        self._elegidos_proy = []
        self.set_herramienta("seleccionar")

    def descartar_proyeccion(self):
        """Cambiar de herramienta o terminar el boceto con una selección sin aceptar: se descarta. Devuelve lo que hay que
        decirle a la persona ("" si no había nada), para que quien llama lo muestre en la barra de estado."""
        if self._proy_fusion:                     # B-256: tampoco queda la arista de una Curva de fusión a medias
            self._quitar_proyecciones(self._proy_fusion)
        if not self._elegidos_proy:
            return ""
        nota = f"{HERRAMIENTAS[self.herramienta][0]}: la selección sin aceptar se descartó."
        self._elegidos_proy = []
        self._emitir_proyeccion()
        return nota

    def _dibujar_previa_proyeccion(self, p, acento):
        """Lo que quedaría al aceptar, en el plano del boceto y en azul: todavía no es geometría."""
        p.setPen(QPen(acento, 2.0))
        for prim in self._previa_proy["prims"]:
            self._dibujar_polilinea(p, puntos_primitiva(prim))
        p.setBrush(acento)
        for xy in self._previa_proy["puntos"]:
            q = self.a_px(*xy)
            p.drawEllipse(q, 3.5, 3.5)
        p.setBrush(Qt.NoBrush)

    def _eje_perfil_giratorio(self):
        from ..timeline import entidades as ent
        if self.opciones["eje_giro"] == "arista":
            if self._eje_giro is None:
                raise ErrorBoceto("Elegí una arista recta como eje del giro.")
            return self._eje_giro
        ref = {"tipo": "eje", "id": self.opciones["eje_giro"]}
        return ent.como_eje(ent.resolver(ref, self.estado_referencias())), ref

    def _tanda_eje(self, eje, ref):
        from ..timeline import entidades as ent
        prims, puntos = ent.proyectar_entidad(ent.Entidad("eje", eje=eje), self.plano)
        datos = {"modo": "project", "refs": [ref], "infinitas": {str(k): 0.0 for k in range(len(prims))}}
        if not self.opciones["vinculo_proyeccion"] or ref is None:
            prims, datos = self.b.derivar_proyeccion(datos, prims), None
        return prims, puntos, self.construccion, datos

    def proyectar_eje(self):
        """Fusion: Project Axis; proyecta el eje elegido en la paleta, como línea o punto si es perpendicular."""
        from ..timeline import entidades as ent
        try:
            if self.plano is None:
                raise ErrorBoceto("Falta el plano para proyectar el eje.")
            eje, ref = self._eje_perfil_giratorio()
        except (ErrorBoceto, ent.ErrorReferencia) as e:
            self.mensaje.emit(str(e))
            return False
        return self._aplicar_proyecciones([self._tanda_eje(eje, ref)])

    def perfil_giratorio_forma(self, forma, ref=None):
        """Perfil giratorio (Fusion: Proyectar › Spun Profile) de una forma OCC alrededor del eje de la paleta
        (X, Y o Z del origen, o la arista elegida), con la tolerancia, el lado y el vínculo de la paleta."""
        from ..nucleo import geometria as geo
        from ..nucleo.perfiles import proyectar_giro_forma
        from ..timeline import entidades as ent
        o = self.opciones
        try:
            eje, ref_eje = self._eje_perfil_giratorio()
            prims, puntos = proyectar_giro_forma(forma, self.plano, eje, o["tolerancia_giro"], o["invertir_giro"])
        except (geo.ErrorGeometria, ErrorBoceto, ent.ErrorReferencia) as e:
            self.mensaje.emit(str(e))
            return False
        if not prims and not puntos:
            self.mensaje.emit("Eso no deja ningún perfil sobre el plano del boceto.")
            return False
        origen = {"modo": "giro", "refs": [ref], "eje": ref_eje, "tolerancia": o["tolerancia_giro"],
                  "invertir": bool(o["invertir_giro"])}
        if o["contorno_exterior"]:
            from ..api.herramientas_boceto import _eje_en_plano
            origen["contorno"] = _eje_en_plano(self.plano, eje)

        datos = origen if ref and o["vinculo_proyeccion"] else None
        curvas = prims if datos is not None else self.b.derivar_proyeccion(origen, prims)
        tandas = [(curvas, puntos, self.construccion, datos)]
        if o["proyectar_eje"]:
            tandas.append(self._tanda_eje(eje, ref_eje))
        return self._aplicar_proyecciones(tandas)

    def isoparametrica_forma(self, forma, ref, punto):
        """Curva isoparamétrica (Fusion: Proyectar/Incluir › Isoparametric Curve) de la cara `forma` por `punto`, con la
        dirección, el tipo y el vínculo de la paleta. Quedan como curvas 3D del boceto; con vínculo siguen a la cara."""
        from ..nucleo import geometria as geo
        from ..restricciones import boceto3d as b3
        o = self.opciones
        if punto is None:
            self.mensaje.emit("Hacé clic sobre la cara: el punto del clic da dónde va la curva.")
            return False
        p = [float(x) for x in punto]
        self._borrar_previa_iso()
        try:
            curvas, tipo, distancia, cantidad = self._curvas_iso(forma, p)
        except geo.ErrorGeometria as e:
            self.mensaje.emit(str(e))
            return False
        origen = {"tool": "isoparametric_curve", "refs": [ref], "point": p, "direction": o["iso_direccion"],
                  "type": tipo, "distance": distancia, "quantity": cantidad}
        vinculo = bool(ref) and bool(o["vinculo_proyeccion"])

        def agregar():
            for i, d in enumerate(curvas):
                b3.agregar_desde_mundo(self.b, d, self.plano, self.construccion, {**origen, "index": i} if vinculo else None)
        return self.aplicar_cambio(agregar, anclar=False)

    def incluir_3d_forma(self, forma, ref):
        """Incluir geometría 3D (Fusion: Project/Include › Include 3D Geometry): la arista queda DONDE ESTÁ, como curva
        3D del boceto; un vértice, como punto 3D. Con vínculo los dos siguen al modelo, como `include_3d_geometry`."""
        from ..nucleo import curvas3d
        from ..nucleo import geometria as geo
        from ..restricciones import boceto3d as b3
        origen = {"tool": "include_3d", "refs": [ref]} if ref and self.opciones["vinculo_proyeccion"] else None
        if forma.ShapeType() == geo.TopAbs_VERTEX:
            from ..nucleo import referencias as refs
            p = refs.firma_vertice(forma)["punto"]

            def agregar_punto():
                pid = b3.agregar_punto(self.b, b3.a_boceto(self.plano, p), unir=False)
                if origen:
                    b3.vincular_punto(self.b, pid, origen)
            ok = self.aplicar_cambio(agregar_punto, anclar=False)
        else:
            curvas = [curvas3d.describir(a) for a in geo._aristas_unicas(forma)]
            ok = self.aplicar_cambio(lambda: [b3.agregar_desde_mundo(self.b, d, self.plano, self.construccion,
                                                                     {**origen, "index": i} if origen else None)
                                              for i, d in enumerate(curvas)], anclar=False)
        if ok:
            self.mensaje.emit(f"{HERRAMIENTAS['incluir_3d'][0]}: listo. Seguí eligiendo o Esc.")
        return ok

    def _curvas_iso(self, forma, punto):
        """(curvas, tipo, distancia, cantidad) de la isoparamétrica de `forma` por `punto` con las opciones de la paleta;
        `ErrorGeometria` si no sale ninguna."""
        from ..nucleo import curvas3d
        o = self.opciones
        tipo = "single" if o["iso_tipo"] == "unica" else "distributed"
        distancia = float(o["iso_distancia"]) if o["iso_tipo"] == "distancia" else None
        cantidad = int(o["iso_cantidad"]) if o["iso_tipo"] == "cantidad" else None
        return curvas3d.isoparametricas(forma, punto, o["iso_direccion"], tipo, distancia, cantidad), tipo, distancia, cantidad

    def programar_previa_iso(self, pos=None):
        """Isoparamétrica: pide la vista previa en `pos` (o donde estaba el cursor, p. ej. al cambiar una opción de la
        paleta). Se arma con el cursor quieto (80 ms): las distribuidas cuestan y no se recalculan en cada movimiento."""
        if pos is not None:
            self._iso_pos = pos
        self._t_iso.start(80)

    def _previa_iso(self):
        """Dibuja en la vista 3D las curvas que saldrían con un clic donde está el cursor (Fusion muestra la curva antes
        de aceptar). Sin cara bajo el cursor, o con un valor que no sirve, no dibuja nada; el motivo va al mensaje."""
        from ..nucleo import geometria as geo
        from ..restricciones import boceto3d as b3
        elegir = getattr(self.visor, "elegir_entidad", None) if self.visor is not None else None
        if self.herramienta != "isoparametrica" or self._iso_pos is None or elegir is None:
            return self._borrar_previa_iso()
        pos = self._iso_pos
        info = elegir(QPointF(self.visor.mapFromGlobal(self.mapToGlobal(QPoint(int(pos.x()), int(pos.y()))))), {"cara"})
        if not info or info.get("forma") is None or info.get("punto") is None:
            return self._borrar_previa_iso()
        try:
            curvas = self._curvas_iso(info["forma"], [float(x) for x in info["punto"]])[0]
        except geo.ErrorGeometria as e:
            self._borrar_previa_iso()
            if str(e) != self._iso_texto:                  # el motivo se dice una vez, no en cada pausa del cursor
                self._iso_texto = str(e)
                self.mensaje.emit(self._iso_texto)
            return
        previa = Boceto()
        try:
            for d in curvas:
                b3.agregar_desde_mundo(previa, d, self.plano)
        except ErrorBoceto:                                # un arco casi recto del recorte: sin vista previa, no una excepción en el timer
            return self._borrar_previa_iso()
        from .visor3d import _segmentos
        self._iso_texto, self._iso_dibujada = None, True
        self.visor.set_capa(CAPA_PREVIA_ISO, [("lineas", _segmentos(b3.polilineas(previa, self.plano)), COLOR_PREVIA_ISO, 2.5)])

    def _borrar_previa_iso(self):
        self._t_iso.stop()
        if self.visor is not None and self._iso_dibujada:
            self.visor.set_capa(CAPA_PREVIA_ISO, None)
        self._iso_dibujada = False

    def leaveEvent(self, e):
        if self.herramienta == "isoparametrica":
            self._iso_pos = None
            self._borrar_previa_iso()
        super().leaveEvent(e)

    def _filtros_proyeccion(self):
        """Tipos de entidad que elige el próximo clic con la herramienta y el filtro actuales."""
        h = self.herramienta
        if self._revincular is not None:
            return {"cuerpo", "cara", "arista", "vertice"}
        if h == "incluir_3d" or (h == "perfil_giratorio" and self.opciones["eje_giro"] == "arista"
                                 and self._eje_giro is None):
            return {"arista", "vertice"} if h == "incluir_3d" else {"arista"}
        if h == "isoparametrica":
            return {"cara"}
        if self.opciones["filtro_proyectar"] == "cuerpos" and h != "perfil_giratorio":
            return {"cuerpo"}
        comunes = {"cara", "arista", "vertice"}
        if h in COMANDO_PROYECCION:
            comunes.add("curva_boceto")
        if h == "proyectar":                       # H-54: Proyectar también elige planos, ejes y puntos
            comunes |= {"plano", "eje", "punto", "punto_boceto"}
        return comunes | ({"cuerpo"} if h in ("intersecar", "perfil_giratorio") else set())

    def _clic_proyectar(self, pos):
        elegir = getattr(self.visor, "elegir_entidad", None) if self.visor is not None else None
        if elegir is None:
            self.mensaje.emit("La vista 3D todavía no permite elegir aristas, caras o cuerpos.")
            return
        q = self.visor.mapFromGlobal(self.mapToGlobal(QPoint(int(pos.x()), int(pos.y()))))
        filtros = self._filtros_proyeccion()
        info = elegir(QPointF(q), filtros)
        if info and info.get("tipo") == "curva_boceto" and info["ref"]["boceto"] == self.op_boceto:
            info = elegir(QPointF(q), filtros - {"curva_boceto"})        # este boceto no se proyecta sobre sí mismo
        if info and info.get("tipo") == "curva_boceto":                  # el visor da la referencia; la forma la da el documento
            from ..timeline import entidades as ent
            info["forma"] = ent.resolver(info["ref"], self.estado_referencias()).forma
        if not info or (info.get("forma") is None
                        and info.get("tipo") not in ("plano", "eje", "punto", "punto_boceto")):
            if (self.herramienta == "perfil_giratorio"
                    and self.opciones.get("eje_giro") == "arista"
                    and self._eje_giro is None):
                self.mensaje.emit("Hacé clic en una arista recta del modelo.")
            else:
                self.mensaje.emit("Hacé clic en una arista, una cara o un cuerpo del modelo.")
            return
        if self._hay_tarjeta_proyeccion():
            self._elegir_proyeccion(info)
        else:
            self._usar_entidad(info)

    def _usar_entidad(self, info):
        """Lo elegido en el modelo (dict de `elegir_entidad`) según la herramienta: re-vincular una proyección
        perdida, el eje o el perfil giratorio, o proyectar / intersecar sin pasar por la tarjeta."""
        h, forma, ref = self.herramienta, info["forma"], info.get("ref")
        if self._revincular is not None:
            return self._revincular_con(forma, ref)
        if h == "perfil_giratorio" and self.opciones["eje_giro"] == "arista" and self._eje_giro is None:
            from ..nucleo import referencias as refs
            firma = refs.firma_arista(forma) if info.get("tipo", "arista") == "arista" else {}
            if firma.get("geom") != "linea":
                self.mensaje.emit("Perfil giratorio: el eje tiene que ser una arista recta.")
                return False
            a, b = (np.array(p, float) for p in firma["extremos"])
            self._eje_giro = ((a, (b - a) / np.linalg.norm(b - a)), ref)
            self.mensaje.emit("Perfil giratorio: eje elegido. Ahora clic en lo que se gira.")
            return True
        if h == "isoparametrica":
            ok = self.isoparametrica_forma(forma, ref, info.get("punto"))
            if ok:
                self.mensaje.emit(f"{HERRAMIENTAS[h][0]}: listo ({info.get('tipo', 'geometría')}). Seguí eligiendo o Esc.")
            return ok
        if h == "perfil_giratorio":
            return self.perfil_giratorio_forma(forma, ref)
        if h == "incluir_3d":
            return self.incluir_3d_forma(forma, ref)
        return self.proyectar_forma(forma, "intersecar" if h == "intersecar" else "proyectar", ref, info.get("tipo"))

    def _proyecciones_de(self, ids):
        """Ids de las proyecciones asociativas que tienen alguna de las entidades `ids`. Lo que tiene una proyección
        explícita no arrastra al contorno automático con el que comparte la curva."""
        ids, explicitas = set(ids), self.b._explicitas()
        return [r["id"] for r in self.b.proyecciones if (ids - explicitas if r.get("auto") else ids) & set(r["ids"])]

    def romper_vinculo(self):
        """Romper vínculo (Fusion: Break Link) de las proyecciones de lo seleccionado."""
        pids = self._proyecciones_de(self.seleccion)
        if not pids:
            self.mensaje.emit("Romper vínculo: seleccioná geometría proyectada con vínculo.")
            return False
        return self.tratar_perdidas("break", pids)

    def tratar_perdidas(self, accion, pids):
        """Manage Lost Projections: "break" rompe el vínculo y "delete" borra la geometría de las proyecciones
        `pids` (un solo paso de deshacer)."""
        funcion = self.b.romper_vinculo if accion == "break" else self.b.eliminar_proyeccion
        ok = self.aplicar_cambio(lambda: [funcion(i) for i in pids], anclar=False)
        if ok:
            self.perdidas = [i for i in self.perdidas if i not in pids]
            self.seleccion = [i for i in self.seleccion if i in self.b.curvas or i in self.b.puntos]
        return ok

    def revincular(self, pid):
        """Re-vincular (Manage Lost Projections › Re-Link): el próximo clic en el modelo da la geometría nueva."""
        modo = next(r["modo"] for r in self.b.proyecciones if r["id"] == pid)
        self.set_herramienta("intersecar" if modo == "intersect" else "proyectar")
        self._revincular = pid
        self.mensaje.emit("Re-vincular: clic en la geometría del modelo que reemplaza a la perdida (misma forma).")

    def _revincular_con(self, forma, ref):
        from ..nucleo import geometria as geo
        from ..timeline import entidades as ent
        pid = self._revincular
        reg = next(r for r in self.b.proyecciones if r["id"] == pid)
        try:
            if ref is None:
                raise ErrorBoceto("Sin referencia no se puede re-vincular.")
            giro = None
            if reg["modo"] == "giro":
                giro = {"eje": ent.como_eje(ent.resolver(reg["eje"], self.estado_referencias())),
                        "tolerancia": reg["tolerancia"], "invertir": reg["invertir"]}
            prims, puntos = ent.proyectar_entidad(ent.Entidad(ref.get("tipo", "cuerpo"), forma=forma), self.plano,
                                                  reg["modo"], giro)
        except (geo.ErrorGeometria, ent.ErrorReferencia, ErrorBoceto) as e:
            self.mensaje.emit(str(e))
            return False
        if not self.aplicar_cambio(lambda: self.b.revincular(pid, [ref], prims, puntos), anclar=False):
            return False
        self.perdidas = [i for i in self.perdidas if i != pid]
        self._revincular = None
        self.mensaje.emit("Re-vincular: la proyección sigue ahora a la geometría elegida.")
        return True

    def atenuar_resto(self, activo):
        """«Atenuar el resto» de Administrar proyecciones perdidas: lo que no es una proyección perdida se dibuja
        apagado para ver mejor las perdidas (Fusion: Fade Other Geometry)."""
        self._brillantes = None
        if activo:
            self._brillantes = set(self.seleccion)
            for r in self.b.proyecciones:
                if r["id"] in self.perdidas:
                    self._brillantes.update(r["ids"])
            self._brillantes = self._brillantes or None          # sin perdidas que resaltar no se apaga nada
        self.update()

    def administrar_perdidas(self):
        """Diálogo Manage Lost Projections (lista, re-vincular, romper vínculo, borrar)."""
        from .dialogos_boceto import DialogoPerdidas
        if not self.perdidas:
            self.mensaje.emit("El boceto no tiene proyecciones perdidas.")
            return
        DialogoPerdidas(self).exec()
