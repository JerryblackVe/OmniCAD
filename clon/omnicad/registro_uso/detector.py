"""Reglas del registro local. Sin Qt: recibe la lista de eventos y devuelve hallazgos y resumen.

Los hallazgos son sugerencias para el informe; nada se escribe en docs/seguimiento/ automáticamente.
"""
from datetime import date

UMBRALES = {
    "operacion_lenta_s": 2.0,
    "apertura_lenta_s": 10.0,
    "bloqueo_ui_ms": 250.0,
    "fps_minimo": 15.0,
    "fallas_seguidas": 2,
    "cancelaciones_confusion": 3,
    "deshacer_inmediato_s": 3.0,
    "duda_larga_s": 20.0,
    "clics_repetidos": 4,
    "clics_ventana_s": 2.0,
    "memoria_crecimiento": 0.30,
    "memoria_ventana_s": 300.0,
}
_SEVERIDAD = {"alta": 0, "media": 1, "baja": 2}


def _datos(evento):
    d = evento.get("datos")
    return d if isinstance(d, dict) else {}


def _ts(evento):
    return str(evento.get("ts") or "")


def _que(evento, texto):
    d = _datos(evento)
    comando = d.get("comando") or ""
    paso = d.get("paso") or ""
    return texto + (f" · comando {comando}" if comando else "") + (f" · paso {paso}" if paso else "")


def _fila(tabla, que, dificultad, evidencia, fecha):
    """Borrador de fila con las columnas de docs/seguimiento/README.md (el ID lo asigna quien la cargue)."""
    prefijo = "B-?" if tabla == "bugs.md" else "P-?"
    return f"| {prefijo} | {que} | Abierto | {dificultad} | | {evidencia} | {fecha} |"


def _hallazgo(regla, severidad, evento, que, tabla, dificultad, evidencia):
    return {"regla": regla, "severidad": severidad, "t": round(float(evento.get("t", 0)), 3),
            "ts": _ts(evento), "que": que, "tabla": tabla,
            "sugerencia": _fila(tabla, que, dificultad, evidencia, date.today().isoformat()),
            "contexto": _datos(evento)}


def _agregar(salida, vistos, clave, hallazgo):
    if clave not in vistos:
        vistos.add(clave)
        salida.append(hallazgo)


def analizar(eventos, umbrales=None):
    """Lista de hallazgos ordenada por momento. `umbrales` pisa solo las claves indicadas de UMBRALES."""
    u = {**UMBRALES, **(umbrales or {})}
    salida, vistos = [], set()
    canceladas = {}
    fallas = {}
    clics = {}
    ultima_op = None
    memoria = []
    for evento in eventos:
        tipo, d = evento.get("tipo"), _datos(evento)
        t = float(evento.get("t", 0))
        if tipo == "op_ejecutada":
            duracion = float(d.get("duracion_ms") or 0) / 1000
            if duracion > u["operacion_lenta_s"]:
                sev = "alta" if duracion >= 10 else "media"
                que = _que(evento, f"Operación lenta ({duracion:.1f} s)")
                _agregar(salida, vistos, ("operacion_lenta", d.get("paso")),
                         _hallazgo("operacion_lenta", sev, evento, que, "mejoras.md", "Media",
                                   "informe de sesión: operaciones lentas"))
            ultima_op = evento
        elif tipo == "archivo_abrir":
            duracion = float(d.get("duracion_ms") or 0) / 1000
            if d.get("exito") and duracion > u["apertura_lenta_s"]:
                que = f"Apertura de proyecto lenta ({duracion:.1f} s)"
                _agregar(salida, vistos, ("apertura_lenta", int(t // 60)),
                         _hallazgo("apertura_lenta", "alta", evento, que, "mejoras.md", "Alta",
                                   "informe de sesión: aperturas lentas"))
        elif tipo == "bloqueo_ui":
            ms = float(d.get("duracion_ms") or 0)
            if ms > u["bloqueo_ui_ms"]:
                sev = "alta" if ms >= 1000 else "media"
                que = _que(evento, f"Interfaz detenida {ms:.0f} ms")
                _agregar(salida, vistos, ("bloqueo_ui", int(t // 2)),
                         _hallazgo("bloqueo_ui", sev, evento, que, "bugs.md", "Media",
                                   "informe de sesión: bloqueos de interfaz"))
        elif tipo == "visor_cuadros":
            fps = float(d.get("fps_p95") or d.get("fps_promedio") or 0)
            if int(d.get("cuadros") or 0) >= 5 and fps < u["fps_minimo"]:
                que = f"Visor por debajo de {u['fps_minimo']:.0f} FPS (p95 {fps:.1f})"
                _agregar(salida, vistos, ("visor_lento", int(t // 30)),
                         _hallazgo("visor_lento", "media", evento, que, "mejoras.md", "Media",
                                   "informe de sesión: cuadros del visor"))
        elif tipo == "comando_resultado" and d.get("exito") is False:
            clave = d.get("comando") or "sin_comando"
            fallas[clave] = fallas.get(clave, 0) + 1
            if fallas[clave] >= u["fallas_seguidas"]:
                que = _que(evento, f"El comando falla {fallas[clave]} veces seguidas")
                _agregar(salida, vistos, ("falla_repetida", clave, fallas[clave]),
                         _hallazgo("falla_repetida", "alta", evento, que, "bugs.md", "Media",
                                   "informe de sesión: comandos con fallas"))
        elif tipo in ("comando_aceptado", "comando_cancelado"):
            clave = d.get("comando") or "sin_comando"
            fallas[clave] = 0
            if tipo == "comando_cancelado":
                canceladas[clave] = canceladas.get(clave, 0) + 1
                if canceladas[clave] >= u["cancelaciones_confusion"]:
                    que = _que(evento, f"El comando se canceló {canceladas[clave]} veces seguidas")
                    _agregar(salida, vistos, ("cancelaciones", clave, canceladas[clave]),
                             _hallazgo("cancelaciones", "media", evento, que, "mejoras.md", "Media",
                                       "informe de sesión: comandos cancelados"))
            else:
                canceladas[clave] = 0
        elif tipo == "deshacer" and ultima_op is not None:
            espera = t - float(ultima_op.get("t", 0))
            if 0 <= espera < u["deshacer_inmediato_s"]:
                que = _que(ultima_op, f"Deshacer {espera:.1f} s después de la operación (¿resultado inesperado?)")
                _agregar(salida, vistos, ("deshacer_inmediato", _datos(ultima_op).get("paso"), int(t)),
                         _hallazgo("deshacer_inmediato", "baja", ultima_op, que, "mejoras.md", "Alta",
                                   "informe de sesión: deshacer inmediato"))
        elif tipo == "dialogo_inactivo":
            segundos = float(d.get("duracion_s") or 0)
            if segundos > u["duda_larga_s"]:
                que = _que(evento, f"Diálogo sin actividad durante {segundos:.0f} s")
                _agregar(salida, vistos, ("duda_larga", d.get("comando"), int(t // 60)),
                         _hallazgo("duda_larga", "baja", evento, que, "mejoras.md", "Media",
                                   "informe de sesión: dudas largas"))
        elif tipo == "clic":
            objetivo = d.get("objetivo")
            ventana = u["clics_ventana_s"]
            lista = [x for x in clics.get(objetivo, []) if t - x <= ventana]
            lista.append(t)
            clics[objetivo] = lista
            if len(lista) > u["clics_repetidos"]:
                que = "Clics repetidos sin respuesta sobre el mismo control"
                _agregar(salida, vistos, ("clics_repetidos", objetivo, int(t // ventana)),
                         _hallazgo("clics_repetidos", "media", evento, que, "bugs.md", "Media",
                                   "informe de sesión: clics repetidos"))
        elif tipo == "memoria":
            rss = d.get("rss")
            if isinstance(rss, (int, float)) and rss > 0:
                memoria.append((t, float(rss), evento))
                limite = u["memoria_ventana_s"]
                base = next((m for m in memoria if t - m[0] >= limite * 0.8), None)
                if base is not None and base[1] > 0 and rss / base[1] - 1 > u["memoria_crecimiento"]:
                    abiertos = [e for e in eventos
                                if e.get("tipo") == "archivo_abrir" and base[0] < float(e.get("t", 0)) <= t]
                    if not abiertos:
                        que = f"Memoria crece {((rss / base[1]) - 1) * 100:.0f} % en {t - base[0]:.0f} s sin abrir un proyecto"
                        _agregar(salida, vistos, ("memoria", int(t // limite)),
                                 _hallazgo("memoria", "media", evento, que, "bugs.md", "Alta",
                                           "informe de sesión: memoria"))
                memoria = [(x, y, e) for x, y, e in memoria if t - x <= limite]
        elif tipo == "error":
            origen, categoria = d.get("origen"), d.get("excepcion") or d.get("categoria") or "error"
            aviso = categoria.lower() == "aviso" or categoria == "AvisoOperacion"
            sev = "baja" if aviso else "alta"
            que = _que(evento, f"{'Aviso' if aviso else 'Error'} de {origen or 'la app'} ({categoria})")
            _agregar(salida, vistos, ("error", origen, categoria, d.get("comando"), int(t // 60)),
                     _hallazgo("error", sev, evento, que, "bugs.md" if sev == "alta" else "mejoras.md",
                               "Media", "informe de sesión: errores"))
    return sorted(salida, key=lambda h: (h["t"], _SEVERIDAD.get(h["severidad"], 9)))


def resumir(eventos, hallazgos=None, umbrales=None):
    """Tiempo por comando, top 10 de operaciones lentas, cantidad de errores y hallazgos."""
    comandos = {}
    operaciones, errores, recalculos, selecciones = [], 0, [], []
    fin = 0.0
    for evento in eventos:
        tipo, d = evento.get("tipo"), _datos(evento)
        t = float(evento.get("t", 0))
        fin = max(fin, t)
        if tipo in ("comando_abierto", "comando_aceptado", "comando_cancelado", "comando_editado"):
            clave = d.get("comando") or "sin_comando"
            c = comandos.setdefault(clave, {"abiertos": 0, "aceptados": 0, "cancelados": 0,
                                            "cambios": 0, "tiempo_s": 0.0})
            if tipo == "comando_abierto":
                c["abiertos"] += 1
            elif tipo == "comando_aceptado":
                c["aceptados"] += 1
                c["tiempo_s"] += float(d.get("duracion_s") or 0)
            elif tipo == "comando_cancelado":
                c["cancelados"] += 1
                c["tiempo_s"] += float(d.get("duracion_s") or 0)
            else:
                c["cambios"] += 1
        elif tipo == "op_ejecutada":
            operaciones.append({"paso": d.get("paso"), "tipo_op": d.get("tipo_op"),
                                "duracion_ms": round(float(d.get("duracion_ms") or 0), 1),
                                "exito": bool(d.get("exito")), "t": round(t, 3),
                                "despues": d.get("despues")})
        elif tipo == "error":
            errores += 1
        elif tipo == "recalculo":
            recalculos.append(round(float(d.get("duracion_ms") or 0), 1))
        elif tipo == "seleccion":
            selecciones.append(float(d.get("duracion_ms") or 0))
    for c in comandos.values():
        c["tiempo_s"] = round(c["tiempo_s"], 2)
    hallazgos = analizar(eventos, umbrales) if hallazgos is None else hallazgos
    return {"duracion_s": round(fin, 3), "eventos": len(eventos), "comandos": comandos,
            "operaciones_lentas": sorted(operaciones, key=lambda o: o["duracion_ms"], reverse=True)[:10],
            "errores": errores, "recalculos": {"cantidad": len(recalculos), "total_ms": round(sum(recalculos), 1)},
            "picking_ms_promedio": round(sum(selecciones) / len(selecciones), 2) if selecciones else None,
            "hallazgos": hallazgos,
            "hallazgos_por_severidad": {s: sum(1 for h in hallazgos if h["severidad"] == s)
                                        for s in ("alta", "media", "baja")}}
