# -*- coding: utf-8 -*-
"""Mide previas en la ventana real, sin modificar OmniCAD ni mover el cursor real.

Desde clon/, con la ventana destapada:
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/medir_previa_comandos.py --modelo chico
    .venv/Scripts/python.exe -m ruff check ../scripts/medir_previa_comandos.py

Patrón: medir_fluidez.py (cronómetros y QMouseEvent). No importa ese script porque ejecuta main al importarse.
Cada caso abre un documento y panel nuevos; registra la primera previa por separado y arrastra 3 s, tres veces.
Guarda resultados reanudables en evidencias/previa_comandos_<fecha>.json y las tablas en el informe Markdown.
--resumir reproduce el informe por stdout; --fecha permite consultar mediciones anteriores.
--comprobar prueba el análisis y coteja las tablas con el JSON; las trazas de prueba nunca se guardan.
"""
import argparse
from bisect import bisect_right
from collections import defaultdict
from contextlib import ExitStack
from datetime import date
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "clon"))
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

import numpy as np  # noqa: E402
from PySide6.QtCore import QEvent, QPointF, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent, QSurfaceFormat  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.nucleo import analisis, aislado, geometria as geo, referencias as refs  # noqa: E402
from omnicad.nucleo import solidos_modificar as sm  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402
from omnicad.timeline.operaciones import OpPrimitiva  # noqa: E402
from omnicad.ui import comando as com, manipuladores as mp, visor3d as vis  # noqa: E402
from omnicad.ui.comandos import CATALOGO  # noqa: E402
from omnicad.ui.preferencias import Preferencias  # noqa: E402
from omnicad.ui.ventana import VentanaPrincipal  # noqa: E402

CASOS = {
    "empalme": ("empalme_3d", "radio", 1.0, 0.35),
    "chaflan": ("chaflan_3d", "distancia", 1.0, 0.35),
    "cortar": ("caja", "alto", 12.0, 3.0),
    "unir": ("caja", "alto", 12.0, 3.0),
    "intersecar": ("caja", "alto", 12.0, 3.0),
    "vaciar": ("vaciado", "espesor_interior", 0.5, 0.12),
    "patron_rectangular": ("patron_rectangular_3d", "d1", 120.0, 12.0),
    "patron_circular": ("patron_circular_3d", "angulo", 240.0, 25.0),
}
MODELOS = ("chico", "mediano", "grande", "placa200")


def _llamar(sesion, nombre, **datos):
    respuesta = api.llamar(sesion, nombre, datos)
    assert respuesta["ok"], (nombre, respuesta)
    return respuesta["result"]


def _modelo(nombre):
    sesion = api.Sesion()
    if nombre == "placa200":
        _llamar(sesion, "create_sketch", name="R", plane="XY")
        _llamar(sesion, "draw_rectangle", sketch="R", x1=0, y1=0, x2=400, y2=400)
        for i in range(200):
            _llamar(sesion, "draw_circle", sketch="R", center_x=10 + i % 25 * 15.5,
                    center_y=10 + i // 25 * 15.5, radius=3)
        _llamar(sesion, "extrude", sketch="R", profile="largest", distance=20)
    else:
        _llamar(sesion, "create_box", length=100, width=60, height=20)
        if nombre == "mediano":
            for i in range(19):
                _llamar(sesion, "create_box", length=16, width=16, height=16,
                        x=-100 + i % 7 * 30, y=-70 - i // 7 * 30)
                if i < 10:
                    cid = list(sesion.doc.estado_final.cuerpos)[-1]
                    aristas = _llamar(sesion, "find_edges", body=cid)["edges"]
                    _llamar(sesion, "fillet", body=cid, edges=[a["id"] for a in aristas], radius=1)
        elif nombre == "grande":
            # Cargar la receta y calcular UNA vez evita 11 prevuelos de alta durante la preparación.
            doc = sesion.doc
            for i in range(69):
                doc.operaciones.append(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10",
                    x=str(-100 + i % 10 * 20), y=str(-70 - i // 10 * 20), z="0", operacion="nuevo"))
            doc.marcador = len(doc.operaciones)
            doc.recalcular(0)
    estado = sesion.doc.estado_final
    medidas = {"pasos": len(sesion.doc.operaciones), "cuerpos": len(estado.cuerpos),
               "caras": sum(len(geo.caras(c.forma)) for c in estado.cuerpos.values())}
    assert medidas["cuerpos"] == (20 if nombre == "mediano" else 70 if nombre == "grande" else 1), medidas
    assert nombre != "mediano" or 270 <= medidas["caras"] <= 340, medidas
    assert nombre != "grande" or medidas["pasos"] >= 70, medidas
    return sesion.doc.a_dict(), medidas


def _resumen(valores):
    if not valores:
        return {"n": 0, "p50": None, "p95": None, "max": None}
    return {"n": len(valores), "p50": round(float(np.percentile(valores, 50)), 3),
            "p95": round(float(np.percentile(valores, 95)), 3), "max": round(max(valores), 3)}


def _latencias(movimientos, cuadros):
    """Edad de la generación al presentarse, incluso si el kernel impidió recibir movimientos nuevos."""
    tiempos = [m[0] for m in movimientos]
    edades, edades_eventos, diferencias, presentacion, vistas = [], [], [], [], set()
    for ahora, generacion in cuadros:
        ultimo = bisect_right(tiempos, ahora) - 1
        if generacion < 0 or ultimo < 0:
            continue
        usado = movimientos[generacion]
        edades.append(max(0.0, (ahora - usado[0]) * 1000))
        edades_eventos.append(max(0.0, (tiempos[ultimo] - usado[0]) * 1000))
        diferencias.append(abs(movimientos[ultimo][1] - usado[1]))
        if generacion not in vistas:
            presentacion.append((ahora - usado[0]) * 1000)
            vistas.add(generacion)
    return {"retraso_ms": _resumen(edades), "edad_eventos_ms": _resumen(edades_eventos),
            "desfase_valor": _resumen(diferencias),
            "entrada_a_cuadro_ms": _resumen(presentacion)}


class _Relojes:
    def __init__(self):
        self.datos = defaultdict(list)
        self.activo = False
        self.generacion = -1
        self.calculando = -1
        self.mostrada = -1
        self.fallos = []

    def envolver(self, pila, objeto, nombre, etiqueta):
        original = getattr(objeto, nombre)

        def medir(*args, **kwargs):
            if not self.activo:
                return original(*args, **kwargs)
            generacion = self.generacion
            if etiqueta == "previa":
                self.calculando = generacion
            cortes = {k: len(self.datos[k]) for k in ("teselado", "aristas")} if etiqueta == "modelo" else {}
            inicio = time.perf_counter()
            try:
                resultado = original(*args, **kwargs)
                if etiqueta == "modelo":
                    self.mostrada = self.calculando
                return resultado
            finally:
                self.datos[etiqueta].append((inicio, time.perf_counter(), generacion))
                if etiqueta == "previa" and not args[0]._previa_ok:
                    self.fallos.append(args[0].mensaje.text())
                for k, corte in cortes.items():
                    duracion = sum(b - a for a, b, _ in self.datos[k][corte:])
                    self.datos[k + "_por_modelo"].append((inicio, inicio + duracion, generacion))
        pila.enter_context(patch.object(objeto, nombre, medir))

    def instalar(self, pila):
        for objeto, nombre, etiqueta in (
            (com.PanelComando, "_calcular_previa", "previa"),
            (Documento, "previsualizar", "kernel"), (aislado, "correr_json", "hijo"),
            (vis.Visor3D, "set_modelo", "modelo"), (vis.Visor3D, "paintGL", "dibujo"),
            (vis, "teselar_cuerpo", "teselado"), (vis, "aristas_cuerpo", "aristas"),
            (geo, "BRepMesh_IncrementalMesh", "mallador"), (analisis, "_props_nodos", "normales"),
            (geo, "booleano", "booleana_total"), (geo, "_booleana", "booleana_occ"),
            (geo, "_problema_booleana", "validacion_booleana"),
            (sm, "_validar", "validacion_modificar"), (sm, "empalme", "empalme_kernel"),
            (sm, "chaflan", "chaflan_kernel"), (sm, "vaciado", "vaciado_kernel"),
        ):
            self.envolver(pila, objeto, nombre, etiqueta)

    def resumir(self):
        return {k: _resumen([(b - a) * 1000 for a, b, _ in valores]) for k, valores in self.datos.items()}


def _evento(visor, tipo, punto, boton, botones):
    QApplication.sendEvent(visor, QMouseEvent(tipo, punto, visor.mapToGlobal(punto), boton, botones, Qt.NoModifier))


def _seleccionar(panel, clave, referencias):
    campo = next(c for c in panel.campos if c.clave == clave)
    panel._activar(campo)
    for ref in referencias:
        panel._elegida(com.hit_desde_ref(ref, panel.ctx.estado))


def _preparar(ventana, caso, modelo):
    clave, campo, inicial, amplitud = CASOS[caso]
    panel = ventana.ejecutar_comando(CATALOGO[clave]())
    assert panel is not None, clave
    panel._t_previa.stop()
    cid, cuerpo = next(iter(ventana.doc.estado_final.cuerpos.items()))
    ref_cuerpo = {"tipo": "cuerpo", "cuerpo": cid}
    if caso in ("empalme", "chaflan"):
        # La arista exterior más larga no confunde un agujero con la costura cilíndrica.
        arista = max(refs.subformas(cuerpo.forma, "arista"), key=lambda a: refs.firma_arista(a)["largo"])
        _seleccionar(panel, "aristas", [refs.referencia(cid, arista, cuerpo.forma)])
    elif caso == "vaciar":
        _seleccionar(panel, "caras", [ref_cuerpo])
    elif caso in ("cortar", "unir", "intersecar"):
        x, y = (395, 300) if modelo == "placa200" else (45, 0)
        for k, valor in {"ancho": "20", "largo": "30", "x": str(x), "y": str(y), "z": "5",
                         "operacion": caso}.items():
            panel.set_valor(k, valor)
        _seleccionar(panel, "objetivo", [ref_cuerpo])
    else:
        _seleccionar(panel, "cuerpos", [ref_cuerpo])
        if caso == "patron_rectangular":
            _seleccionar(panel, "dir1", [{"tipo": "eje", "id": "X"}])
            panel.set_valor("n1", 3)
        else:
            _seleccionar(panel, "eje", [{"tipo": "eje", "id": "Z"}])
            panel.set_valor("n", 3)
    widget = panel.widgets[campo]
    widget.setFocus()
    QTest.keyClick(widget, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(widget, str(inicial))
    panel._t_previa.stop()
    return panel, campo, inicial, amplitud


def _corrida(app, receta, caso, modelo, temporal, reloj):
    reloj.activo = False
    reloj.datos.clear()
    reloj.fallos.clear()
    reloj.generacion = reloj.calculando = reloj.mostrada = -1
    doc = Documento.desde_dict(receta)
    doc.recalcular(0)
    doc.modificado = False
    ajustes = QSettings(str(Path(temporal) / "preferencias.ini"), QSettings.IniFormat)
    ventana = VentanaPrincipal(doc, prefs=Preferencias(ajustes))
    ventana.resize(1900, 1000)
    ventana.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    ventana.show()
    ventana.raise_()
    ventana.activateWindow()
    QTest.qWait(500)
    visor = ventana.visor
    visor.encuadrar()
    QTest.qWait(200)
    cuadros = []

    def presentado():
        cuadros.append((time.perf_counter(), reloj.mostrada))

    visor.frameSwapped.connect(presentado)
    try:
        panel, campo, inicial, amplitud = _preparar(ventana, caso, modelo)
        reloj.activo = True
        panel._calcular_previa()
        reloj.activo = False
        primera = reloj.resumir()
        assert panel._previa_ok, panel.mensaje.text()
        QTest.qWait(100)
        gestor = panel.manipuladores
        asa = next(m for m in gestor.manips if isinstance(m, (mp.Flecha, mp.Angulo)) and m.clave == campo)
        if isinstance(asa, mp.Flecha):
            a, b = asa.puntos(gestor)
            origen = (a + b) / 2

            def punto(valor):
                return origen + asa.direccion * (valor - inicial) * asa.factor
        else:
            def punto(valor):
                angulo = math.radians(valor * asa.factor)
                return asa.centro + (asa.u * math.cos(angulo) + asa.v * math.sin(angulo)) * asa._r(gestor)
        xy, visible = gestor.pantalla([punto(inicial)])
        assert visible[0], "El asa queda fuera del visor"
        posicion = QPointF(*xy[0])
        _evento(visor, QEvent.MouseMove, posicion, Qt.NoButton, Qt.NoButton)
        _evento(visor, QEvent.MouseButtonPress, posicion, Qt.LeftButton, Qt.LeftButton)
        assert gestor.arrastrando, "El evento no tomó el asa"
        assert gestor._arrastre["m"].clave == campo, "Se tomó otra asa"
        reloj.datos.clear()
        reloj.activo = True
        inicio = time.perf_counter()
        movimientos = [(inicio, gestor.valor(campo))]
        reloj.generacion = 0
        cuadros.clear()
        while (transcurrido := time.perf_counter() - inicio) < 3.0:
            valor = inicial + amplitud * (0.7 * math.sin(2 * math.pi * transcurrido / 0.7)
                                         + 0.3 * math.sin(2 * math.pi * transcurrido / 0.23))
            xy, visible = gestor.pantalla([punto(valor)])
            assert visible[0], "El gesto salió del visor"
            posicion = QPointF(*xy[0])
            reloj.generacion = len(movimientos)
            cuando = time.perf_counter()
            _evento(visor, QEvent.MouseMove, posicion, Qt.NoButton, Qt.LeftButton)
            movimientos.append((cuando, gestor.valor(campo)))
            QTest.qWait(8)
        fin_gesto = time.perf_counter()
        # La suelta y su última previa no se cuentan como trabajo durante el arrastre.
        reloj.activo = False
        panel._t_previa.stop()
        _evento(visor, QEvent.MouseButtonRelease, posicion, Qt.LeftButton, Qt.NoButton)
        panel._t_previa.stop()
        QTest.qWait(100)
        activos = [(t, g) for t, g in cuadros if inicio <= t <= inicio + 3.0]
        # La cola de presentación expone un bloqueo que cruza el borde de los 3 s.
        observados = [(t, g) for t, g in cuadros if inicio <= t <= fin_gesto + 0.1]
        intervalos = np.diff([inicio, *(t for t, _ in observados)]) * 1000
        assert max(v for _, v in movimientos) - min(v for _, v in movimientos) > amplitud / 4, movimientos
        r = {"primera": primera, "etapas": reloj.resumir(), "movimientos": len(movimientos) - 1,
             "gesto_s": round(fin_gesto - inicio, 3), "fps": round(len(activos) / 3, 3),
             "previas_s": round(len(reloj.datos["previa"]) / (fin_gesto - inicio), 3),
             "intervalos_ms": _resumen(list(intervalos)), "cuadros_33": int(sum(intervalos > 33)),
             "cuadros_100": int(sum(intervalos > 100)),
             "hijo_arrastre": len(reloj.datos["hijo"]), "hijo_primera": primera.get("hijo", {}).get("n", 0),
             "valida": bool(activos), "previa_ok": panel._previa_ok, "mensaje": panel.mensaje.text(),
             "gl": visor.info_gl}
        r.update(_latencias(movimientos, observados))
        assert not reloj.fallos, reloj.fallos
        assert reloj.datos["dibujo"] or not activos, "Qt no está llamando al cronómetro de paintGL"
        # Sin trazas crudas enormes: conservar los tiempos por cálculo para recalcular percentiles conjuntos.
        r["muestras_ms"] = {k: [round((b - a) * 1000, 4) for a, b, _ in vals]
                            for k, vals in reloj.datos.items()}
        panel.cancelar()
        return r
    finally:
        visor.frameSwapped.disconnect(presentado)
        doc.modificado = False
        ventana.close()
        ventana.deleteLater()
        app.processEvents()


def _inventario():
    grupos = defaultdict(list)
    for clave, clase in sorted(CATALOGO.items()):
        if clase.PREVIA:
            grupos[clase.__module__.rsplit(".", 1)[-1]].append(clave + ("*" if clase.SIN_OP else ""))
    return dict(grupos)


def _numero(n):
    return "—" if n is None else f"{n:.1f}"


def _informe(datos):
    lineas = [f"# Vista previa de comandos · {datos['fecha']}", "", "## Alcance y reproducción", "",
        "Medición de la ventana real en el commit " + datos["commit"] + ". No modifica producción ni tests.",
        "Desde `clon/`: `.venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe "
        "../scripts/medir_previa_comandos.py --modelo chico` (repetir con mediano, grande y placa200).", "",
        "Arrastre rápido de 3 s con QMouseEvent, sin mover el cursor real; tres corridas válidas por caso. "
        "Primer cálculo con documento/panel nuevo separado del arrastre. Espera adaptativa y protección aislada originales.",
        "Ventana 1900 × 1000, con la bandera siempre encima. FPS cuenta frameSwapped dentro de los 3 s; "
        "una corrida con FPS 0 se descarta. Previas/s usa la duración real del gesto: un cálculo nativo puede "
        "sobrepasar los 3 s pedidos y se registra gesto_s.",
        "Los intervalos incluyen hasta 100 ms de presentación posterior al gesto para no esconder un bloqueo al final. "
        "paintGL mide CPU/envío de GL, no GPU aislada.", "", "## Catálogo con PREVIA=True", "",
        "Inventario efectivo de CATALOGO (incluye PREVIA heredado). * = SIN_OP: usa mostrar, no Documento.previsualizar.", ""]
    for modulo, claves in datos["catalogo"].items():
        lineas.append(f"- **{modulo}:** " + ", ".join(f"`{c}`" for c in claves))
    lineas += ["", "## Selección", "",
        "Empalme y Chaflán cambian una arista exterior; Vaciado ahueca el cuerpo cerrado; "
        "Patrón rectangular y circular repiten el cuerpo tres veces, sin copias ligeras ni unión. "
        "Cortar/Unir/Intersecar son los tres modos booleanos del panel `caja`, variando alto. "
        "Así el modelo chico mantiene un único cuerpo de entrada. `combinar` no tiene cotas ni asas: "
        "no se midió su interfaz ni se supone equivalente su costo total.", "",
        "La placa replica el contorno 400 × 400 y los 200 círculos r3 de medir_costos_previa.py, extruidos 20 mm "
        "solo para preparar el modelo; no se vuelve a medir Extruir. Mediano: caja objetivo y 19 cajas, "
        "10 redondeadas en sus 12 aristas. Grande: caja objetivo y 69 cajas independientes.", "",
        "## Tabla comando × modelo", "",
        "Milisegundos. Previa = p50 / p95 / máximo de las llamadas de las tres corridas reunidas. "
        "K/M/T/D = p50 de previsualizar / set_modelo / teselado acumulado por set_modelo / paintGL. "
        "M incluye T y aristas: no sumarlos. p95 y máximos de cada etapa y repetición quedan en el JSON.", "",
        "| Comando | Modelo (pasos/cuerpos/caras) | Reps | Previa p50/p95/máx | K / M / T / D | Previas/s | FPS | Retraso p50/p95 | Cuadros >33/>100 | Hijo primera/arrastre |",
        "|---|---|---|---|---|---|---|---|---|---|"]
    for caso, modelos in datos["casos"].items():
        for modelo, corridas in modelos.items():
            validas = [r for r in corridas if r["valida"]]
            if not validas:
                continue
            etapas = {k: _resumen([x for r in validas for x in r["muestras_ms"].get(k, [])])
                      for k in ("previa", "kernel", "modelo", "teselado_por_modelo", "dibujo")}
            previa = etapas["previa"]
            m = datos["modelos"][modelo]
            rango = lambda k, rs=validas: f"{min(r[k] for r in rs):.1f}–{max(r[k] for r in rs):.1f}"  # noqa: E731
            retrasos = [r["retraso_ms"] for r in validas if r["retraso_ms"]["n"]]
            retraso = (f"{min(r['p50'] for r in retrasos):.1f}–{max(r['p50'] for r in retrasos):.1f} / "
                       f"{min(r['p95'] for r in retrasos):.1f}–{max(r['p95'] for r in retrasos):.1f}" if retrasos else "—")
            lineas.append(f"| {caso} | {modelo} ({m['pasos']}/{m['cuerpos']}/{m['caras']}) | {len(validas)} | "
                + "/".join(_numero(previa[k]) for k in ("p50", "p95", "max")) + " | "
                + " / ".join(_numero(etapas[k]["p50"]) for k in ("kernel", "modelo", "teselado_por_modelo", "dibujo"))
                + f" | {rango('previas_s')} | {rango('fps')} | {retraso} | "
                + f"{sum(r['cuadros_33'] for r in validas)}/{sum(r['cuadros_100'] for r in validas)} | "
                + f"{sum(r['hijo_primera'] for r in validas)}/{sum(r['hijo_arrastre'] for r in validas)} |")
    lineas += ["", "## Reparto en la placa de 200 agujeros", "",
        "Medias por cálculo durante el gesto, en ms (suma de tiempos / cantidad de previas). "
        "Los porcentajes tienen como denominador el tiempo total de _calcular_previa. "
        "Dibujo va aparte, por cuadro: se presenta más de un cuadro por previa y no se suma dos veces. "
        "Booleana OCC cronometra _booleana completa, incluida la unificación de caras y limpieza; "
        "no es solo op.Build de C++.", "",
        "| Comando | Kernel | Teselado | Aristas | Resto previa | paintGL p50/p95/máx | OCC mallador / normales | Booleana OCC / revisión booleana / validar modificar |",
        "|---|---|---|---|---|---|---|---|"]
    for caso, modelos in datos["casos"].items():
        rs = [r for r in modelos.get("placa200", []) if r["valida"]]
        if not rs:
            continue
        muestras = {k: [x for r in rs for x in r["muestras_ms"].get(k, [])]
                    for k in ("previa", "kernel", "teselado_por_modelo", "aristas_por_modelo", "dibujo",
                              "mallador", "normales", "booleana_occ", "validacion_booleana", "validacion_modificar")}
        n = len(muestras["previa"])
        total = sum(muestras["previa"])
        sumas = [sum(muestras[k]) for k in ("kernel", "teselado_por_modelo", "aristas_por_modelo")]
        sumas.append(total - sum(sumas))
        partes = " | ".join(f"{t / n:.1f} ({100 * t / total:.1f} %)" for t in sumas)
        dibujo = _resumen(muestras["dibujo"])
        finos = [_numero(sum(muestras[k]) / n) if muestras[k] else "—" for k in
                 ("mallador", "normales", "booleana_occ", "validacion_booleana", "validacion_modificar")]
        lineas.append(f"| {caso} | {partes} | " + "/".join(_numero(dibujo[k]) for k in ("p50", "p95", "max"))
                      + f" | {finos[0]} / {finos[1]} | {finos[2]} / {finos[3]} / {finos[4]} |")
    lineas += ["", "## Primera previa: costo de abrir el cálculo (fuera del arrastre)", "",
        "Rangos de las tres corridas; documentos nuevos. previsualizar incluye el proceso y transporte si hubo hijo. "
        "Las etapas internas del hijo no heredan estos cronómetros.", "",
        "| Comando | Modelo | _calcular_previa | previsualizar | set_modelo | Hijos | Teselados/previas en arrastre |",
        "|---|---|---|---|---|---|---|"]
    for caso, modelos in datos["casos"].items():
        for modelo, rs in modelos.items():
            rs = [r for r in rs if r["valida"]]
            if not rs:
                continue
            valores = []
            for k in ("previa", "kernel", "modelo"):
                ts = [r["primera"][k]["p50"] for r in rs]
                valores.append(f"{min(ts):.1f}–{max(ts):.1f}")
            lineas.append(f"| {caso} | {modelo} | " + " | ".join(valores)
                          + f" | {sum(r['hijo_primera'] for r in rs)} | "
                          + f"{sum(r['etapas']['teselado']['n'] for r in rs)}/"
                          + f"{sum(r['etapas']['previa']['n'] for r in rs)} |")
    lineas += ["", "## Datos por corrida", "",
        "Incluyen descartes, tiempos de la primera previa, muestras por etapa, latencia entrada→cuadro y desfase "
        "en unidades del campo. El retraso es cuadro presentado menos instante del evento que generó el sólido. "
        "edad_eventos_ms informa por separado la distancia temporal entre los eventos de asa y sólido; "
        "no se usa como latencia porque da cero cuando el kernel bloquea los dos. "
        "Los porcentajes de etapas anidadas no se suman.", "",
        f"Datos: `evidencias/previa_comandos_{datos['fecha']}.json` (fuera de git). "
        "Para regenerar las tablas desde `clon/`: `.venv/Scripts/python.exe ../scripts/medir_previa_comandos.py "
        f"--resumir --fecha {datos['fecha']}`.", "",
        "## Límites: qué no se pudo medir", "",
        "GPU por separado, mouse físico y cada variante de los comandos. El inventario no implica que todos "
        "los comandos hayan sido medidos. El modelo de 70 pasos usa cajas simples.", ""]
    return "\n".join(lineas)


def _guardar(ruta, datos):
    ruta_datos = RAIZ / "evidencias" / f"previa_comandos_{datos['fecha']}.json"
    ruta_datos.parent.mkdir(parents=True, exist_ok=True)
    ruta_datos.write_bytes((json.dumps(datos, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8"))
    ruta.write_bytes(_informe(datos).encode("utf-8"))


def _comprobar():
    assert _resumen([])["p50"] is None
    assert _resumen([1, 2, 3])["p50"] == 2
    latencia = _latencias([(0.0, 1), (0.1, 2), (0.2, 3)], [(0.25, 1), (0.3, 1), (0.4, 2)])
    assert latencia["retraso_ms"]["p50"] == 200
    assert latencia["edad_eventos_ms"]["p50"] == 100
    assert latencia["entrada_a_cuadro_ms"]["n"] == 2
    assert latencia["entrada_a_cuadro_ms"]["max"] == 200
    reloj = _Relojes()
    with ExitStack() as pila:
        reloj.envolver(pila, time, "sleep", "prueba")
        time.sleep(0)
        assert not reloj.datos
        reloj.activo = True
        time.sleep(0)
        assert len(reloj.datos["prueba"]) == 1
    assert time.sleep.__name__ == "sleep"
    print("Autocomprobación: percentiles, generaciones y restauración de cronómetros OK.")


def main():
    """Corre los casos pedidos o reproduce sus tablas desde el JSON separado."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modelo", choices=MODELOS, default="chico")
    parser.add_argument("--comandos", nargs="+", choices=CASOS, default=list(CASOS))
    parser.add_argument("--comprobar", action="store_true")
    parser.add_argument("--resumir", action="store_true", help="Consulta los datos guardados sin modificar el informe")
    parser.add_argument("--fecha", type=date.fromisoformat, default=date.today(), help="Fecha de las mediciones (AAAA-MM-DD)")
    args = parser.parse_args()
    fecha = args.fecha.isoformat()
    ruta = RAIZ / "docs" / "auditorias" / f"previa-comandos-{fecha}.md"
    ruta_datos = RAIZ / "evidencias" / f"previa_comandos_{fecha}.json"
    assert ruta.parent.is_dir()
    if ruta_datos.exists():
        try:
            datos = json.loads(ruta_datos.read_bytes())
        except (OSError, ValueError) as e:
            parser.error(f"No pude leer los datos de {ruta_datos}: {e}")
    elif args.resumir or args.comprobar or ruta.exists():
        parser.error(f"Faltan los datos: {ruta_datos}. Recuperá ese JSON para conservar las mediciones; "
                     "para medir de cero, elegí una fecha nueva con --fecha.")
    else:
        datos = {"fecha": fecha, "commit": subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, text=True).strip(),
            "plataforma": platform.platform(), "python": sys.version, "catalogo": _inventario(),
            "modelos": {}, "casos": {}, "version": 2}
    assert datos["fecha"] == fecha, "La fecha del JSON no coincide con la pedida"
    if args.comprobar:
        _comprobar()
        assert datos["version"] == 2, "Las mediciones usan un formato anterior"
        if not ruta.exists():
            parser.error(f"Falta el informe: {ruta}. Regeneralo con --resumir --fecha {fecha}.")
        texto = ruta.read_text(encoding="utf-8")
        for bloque in _informe(datos).split("\n\n"):
            if bloque.startswith("|"):
                assert bloque in texto, "Una tabla del informe no coincide con el JSON"
        print("Autocomprobación: JSON separado y tablas del informe OK.")
        return
    if args.resumir:
        if not datos["casos"]:
            parser.error("Todavía no hay corridas guardadas para resumir")
        print(_informe(datos))
        return
    if datos.get("version") != 2:
        anteriores = [r for modelos in datos["casos"].values() for rs in modelos.values() for r in rs]
        datos["preliminares_descartadas"] = {
            "motivo": "paintGL se envolvía después de crear la ventana; edad de eventos no medía el bloqueo",
            "corridas": len(anteriores), "fps_cero": sum(not r["valida"] for r in anteriores)}
        datos["casos"] = {}
    datos["version"] = 2
    actual = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, text=True).strip()
    assert datos["commit"] == actual, "El informe pertenece a otro commit: no se mezclan las corridas"
    ruta_datos.parent.mkdir(parents=True, exist_ok=True)
    receta, medidas = _modelo(args.modelo)
    datos["modelos"][args.modelo] = medidas
    print(f"Modelo {args.modelo}: {medidas}", flush=True)
    formato = QSurfaceFormat()
    formato.setDepthBufferSize(24)
    formato.setStencilBufferSize(8)
    formato.setSamples(4)
    QSurfaceFormat.setDefaultFormat(formato)
    app = QApplication.instance() or QApplication([])
    errores = []
    anterior = sys.excepthook
    sys.excepthook = lambda tipo, valor, traza: errores.append(f"{tipo.__name__}: {valor}")
    try:
        with tempfile.TemporaryDirectory(prefix="previa_", dir=RAIZ / "evidencias") as temporal, ExitStack() as pila:
            reloj = _Relojes()
            # Qt registra la sobreescritura virtual al crear el widget: instalar ANTES de la primera ventana.
            reloj.instalar(pila)
            with patch.dict(os.environ, {"OMNICAD_ASISTENTE_DIR": temporal}):
                for caso in args.comandos:
                    corridas = datos["casos"].setdefault(caso, {}).setdefault(args.modelo, [])
                    intentos = 0
                    while sum(r["valida"] for r in corridas) < 3 and intentos < 6:
                        r = _corrida(app, receta, caso, args.modelo, temporal, reloj)
                        assert not errores, errores
                        assert r["previa_ok"], r["mensaje"]
                        corridas.append(r)
                        intentos += 1
                        _guardar(ruta, datos)
                        print(f"{caso}/{args.modelo} intento {intentos}: fps={r['fps']}, "
                              f"previas/s={r['previas_s']}, previa={r['etapas'].get('previa')}, "
                              f"hijo={r['hijo_primera']}/{r['hijo_arrastre']}", flush=True)
                    assert sum(r["valida"] for r in corridas) == 3, "No hubo tres corridas con cuadros presentados"
    finally:
        sys.excepthook = anterior
    print(f"Informe: {ruta}")


if __name__ == "__main__":
    main()
