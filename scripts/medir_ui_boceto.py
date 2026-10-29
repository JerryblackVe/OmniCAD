# -*- coding: utf-8 -*-
"""Escenario humano de B-111: editar un boceto grande (contorno de splines con tangentes) sobre un Lienzo con imagen y
medir el MAYOR HUECO del hilo de la ventana por acción (eventos simulados al widget, nunca el cursor real; no usar el
mouse ni el teclado mientras corre).

Uso, desde `clon/` (con turno; la prueba de UI abre OpenGL):
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/medir_ui_boceto.py <etiqueta> [splines] [conflicto]
Acciones: arrastrar un punto (×3), Ctrl+Z (×3), tocar «Seleccionar», dos rondas. El hueco es el mayor intervalo entre dos
latidos de un temporizador de 10 ms (más el tiempo que la propia acción deja la ventana sin atender). Con `conflicto`, el
boceto arranca con dos cotas incompatibles (hay que diagnosticar qué choca). Escribe evidencias/ui_boceto_<etiqueta>.json y
una captura (fuera de git)."""
import faulthandler
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts" / "prueba_ui"))
sys.path.insert(0, str(RAIZ / "clon" / "tests"))

import arnes as A  # noqa: E402
from _contornos import contorno_splines  # noqa: E402
from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QToolButton  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.restricciones import solver  # noqa: E402

etiqueta = sys.argv[1] if len(sys.argv) > 1 else "medida"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 60
CONFLICTO = "conflicto" in sys.argv[3:]
PLAZO_ACCION = 60      # s por acción
AR = "BOCETO·B-111"


def imagen_de_lienzo():
    """Un JPG de 2400×1500 como el trazo de una raqueta sobre su foto."""
    img = QImage(2400, 1500, QImage.Format_RGB32)
    p = QPainter(img)
    g = QLinearGradient(0, 0, 2400, 1500)
    g.setColorAt(0, QColor(230, 230, 220))
    g.setColorAt(1, QColor(120, 140, 160))
    p.fillRect(img.rect(), g)
    p.end()
    ruta = Path(tempfile.mkdtemp(prefix="omnicad_b111_")) / "paleta.jpg"
    img.save(str(ruta), "JPG")
    return ruta


s = api.Sesion()
for nombre, args in (("create_sketch", {"name": "S", "plane": "XY"}),
                     ("insert_canvas", {"path": str(imagen_de_lienzo()), "width": 300})):
    r = api.llamar(s, nombre, args)
    assert r["ok"], (nombre, r)
app, v = A.iniciar(s.doc)
v.editar_operacion(s.paso("S").id)
A.esperar(500)
lz = v.modo_boceto.lienzo
A.reg(AR, "entrar al boceto", v.modo_boceto.activo and lz is not None)

latidos = []
reloj = QTimer()
reloj.setInterval(10)
reloj.timeout.connect(lambda: latidos.append(time.perf_counter()))
reloj.start()

faulthandler.dump_traceback_later(PLAZO_ACCION, exit=True)
t0 = time.perf_counter()
_b, valores = contorno_splines(N, conflicto=CONFLICTO, boceto=lz.b)
lz.resolver()
armado_s = time.perf_counter() - t0
lz.set_herramienta("seleccionar")
lz.encuadrar()
A.esperar(600)
faulthandler.cancel_dump_traceback_later()
A.reg(AR, f"{N} splines con tangentes resueltas", True, f"{armado_s:.2f} s; ok={lz.resultado.ok}")

if CONFLICTO:
    # El diagnóstico de «qué choca» corre en otro hilo: la ventana (eventos + pintado del lienzo) no debe pasar de 100 ms.
    faulthandler.dump_traceback_later(PLAZO_ACCION, exit=True)
    del latidos[:]
    base_pintura = []
    for _ in range(8):                              # lo que cuesta pintar SIN diagnóstico corriendo (lo mínimo posible)
        t = time.perf_counter()
        lz._conflictos = []
        lz.grab()
        base_pintura.append(time.perf_counter() - t)
    lz._conflictos = None
    del latidos[:]
    pinturas, inicio = [], time.perf_counter()
    lz.conflictos_sin_esperar()
    while lz._conflictos is None and time.perf_counter() - inicio < 30:
        t = time.perf_counter()
        lz.grab()                                   # pinta el lienzo (minimizado no recibe paintEvent solo)
        pinturas.append(time.perf_counter() - t)
        QTest.qWait(10)
    llego = time.perf_counter() - inicio
    faulthandler.cancel_dump_traceback_later()
    huecos = sorted(b - a for a, b in zip(latidos, latidos[1:], strict=False))
    p95 = lambda xs: xs[int(0.95 * (len(xs) - 1))] if xs else None  # noqa: E731
    resumen = {"splines": N, "conflicto": True, "llego_s": round(llego, 2), "conflictos": len(lz._conflictos),
               "agotado": lz._diagnostico_agotado, "texto": lz.texto_conflictos(),
               "hueco_latidos_p95_s": p95(huecos), "hueco_latidos_max_s": max(huecos, default=None),
               "pintura_sin_diagnostico_mediana_s": statistics.median(base_pintura), "pintura_p95_s": p95(sorted(pinturas)), "pintura_max_s": max(pinturas, default=None), "excepciones": A.ERRORES}
    (RAIZ / "evidencias").mkdir(exist_ok=True)
    (RAIZ / "evidencias" / f"ui_boceto_{etiqueta}.json").write_text(json.dumps(resumen, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False))
    sys.exit(0)

INTENTOS = []       # cada sistema que resolvió el solver durante un evento: (incógnitas, error, ms)
_original = solver._resolver_grupo


def _anotar(sis, *args, **kw):
    antes = sis.b.a_dict() if not INTENTOS else None            # el estado al empezar el movimiento
    t = time.perf_counter()
    r = _original(sis, *args, **kw)
    INTENTOS.append((len(sis.x0), float(f"{r[1]:.2g}"), round(1000 * (time.perf_counter() - t))))
    if antes is not None and r[1] >= 1e-3 and args and not (RAIZ / "evidencias" / "b111_meseta.json").exists():
        # un movimiento que no cumple: se guarda tal cual para reproducirlo fuera de la ventana
        (RAIZ / "evidencias" / "b111_meseta.json").write_text(json.dumps({"boceto": antes, "punto": args[0]}), encoding="utf-8")
    return r


solver._resolver_grupo = _anotar
MEDIDAS = []
EVENTOS = []        # un arrastre: segundos que tarda cada evento del ratón en volver


def hueco(que, accion, asentar=1500):
    """Mayor hueco (s) del hilo de la ventana mientras dura `accion` y los `asentar` ms siguientes."""
    faulthandler.dump_traceback_later(PLAZO_ACCION, exit=True)      # si se cuelga: vuelca DÓNDE y sale solo
    inicio = time.perf_counter()
    accion()
    QTest.qWait(asentar)
    fin = time.perf_counter()
    faulthandler.cancel_dump_traceback_later()
    puntos = [inicio] + [t for t in latidos if inicio <= t <= fin] + [fin]
    h = max(b - a for a, b in zip(puntos, puntos[1:], strict=False))
    estado = f"ok={lz.resultado.ok} conflictos={'?' if lz._conflictos is None else len(lz._conflictos)} historial={len(lz.historial)}"
    MEDIDAS.append({"accion": que, "hueco_s": round(h, 3), "estado": estado})
    A.reg(AR, que, True, f"hueco {h:.3f} s · {estado}")
    del latidos[:max(0, len(latidos) - 500)]
    return h


ids_libres = [pid for pid in lz.b.puntos if pid not in {0}]


def arrastrar(k):
    """Un arrastre: cada evento (apretar, 8 movimientos, soltar) se mide por separado, como lo sufre una mano real."""
    pid = ids_libres[(5 + 7 * k) % len(ids_libres)]
    x, y = lz.b.coords(pid)
    p0 = lz.a_px(x, y).toPoint()
    punto = type(p0)

    def f():
        eventos = [("apretar", lambda: QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, p0))]
        eventos += [(f"mover {i}", lambda i=i: QTest.mouseMove(lz, p0 + punto(2 * i, -2 * i))) for i in range(1, 9)]
        eventos.append(("soltar", lambda: QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, p0 + punto(16, -16))))
        for nombre, ev in eventos:
            t = time.perf_counter()
            ev()
            EVENTOS.append({"arrastre": k + 1, "evento": nombre, "s": round(time.perf_counter() - t, 3), "intentos": INTENTOS[:]})
            INTENTOS.clear()
            QTest.qWait(30)
    return f


def deshacer():
    QTest.keyClick(lz, Qt.Key_Z, Qt.ControlModifier)


def tocar_seleccionar():
    botones = [b for b in v.cinta.findChildren(QToolButton) if b.isVisible() and b.text().strip() == "Seleccionar"]
    A.reg(AR, "botón «Seleccionar» en la cinta", bool(botones))
    if botones:
        botones[0].click()
    else:
        v.modo_boceto.set_herramienta("seleccionar")


for ronda in (1, 2):
    for k in range(3):
        hueco(f"[{ronda}] arrastrar un punto #{k + 1}", arrastrar(k))
    for k in range(3):
        hueco(f"[{ronda}] Ctrl+Z #{k + 1}", deshacer)
    hueco(f"[{ronda}] tocar «Seleccionar»", tocar_seleccionar)

lz.grab().save(str(A.SALIDA / f"b111_{etiqueta}.png"))
huecos = [m["hueco_s"] for m in MEDIDAS]
mov = sorted(e["s"] for e in EVENTOS if e["evento"].startswith("mover"))
resumen = {"mover_p95_s": mov[int(0.95 * (len(mov) - 1))] if mov else None, "mover_max_s": max(mov, default=None),
           "eventos": EVENTOS, "splines": N, "conflicto": CONFLICTO, "armado_s": round(armado_s, 2), "mediana_s": round(statistics.median(huecos), 3),
           "maximo_s": max(huecos), "acciones": MEDIDAS, "excepciones": A.ERRORES}
salida = RAIZ / "evidencias" / f"ui_boceto_{etiqueta}.json"
salida.parent.mkdir(exist_ok=True)
salida.write_text(json.dumps(resumen, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"mover p95 {resumen['mover_p95_s']} s · max {resumen['mover_max_s']} s · mediana {resumen['mediana_s']} s · máximo {resumen['maximo_s']} s · excepciones {len(A.ERRORES)} -> {salida}")
sys.exit(0)
