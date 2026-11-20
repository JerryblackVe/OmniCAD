# -*- coding: utf-8 -*-
"""Arrastrar una curva resuelve solo la parte del boceto que la contiene (como arrastrar un punto); si la curva une dos
partes, resuelve todo. Antes resolvía el boceto entero en cada evento del ratón (140 ms con 100 piezas)."""
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.nucleo import geometria as g  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui.editor_boceto import Lienzo  # noqa: E402


def _lienzo(b):
    QApplication.instance() or QApplication([])
    lz = Lienzo(b, TablaParametros().evaluar, plano=g.Plano("XY"))
    lz.resolver()
    llamadas = []
    original = lz.resolver
    lz.resolver = lambda arrastrado=None, rapido=False: (llamadas.append(rapido), original(arrastrado, rapido))[1]
    return lz, llamadas


def _mover(lz, cid, pasos=5):
    lz._ultimo = (0.0, 0.0)
    for i in range(1, pasos + 1):
        lz._mover_curva(cid, "mover", (0.7 * i, 0.4 * i))


def test_arrastrar_una_linea_resuelve_solo_su_parte_y_respeta_las_restricciones():
    b = Boceto()
    lados = b.agregar_rectangulo((0, 0), (20, 10))
    b.agregar_cota("distancia", [lados[0]], "20")
    otra = b.agregar_rectangulo((40, 0), (50, 10))          # otra parte: no se toca
    lz, llamadas = _lienzo(b)
    antes = {p: lz.b.coords(p) for c in otra for p in lz.b.curvas[c].puntos()}
    _mover(lz, lados[1])                                      # el lado derecho (vertical)
    assert llamadas == [True] * 5
    assert lz.resultado.ok
    a, c = (lz.b.coords(p) for p in lz.b.curvas[lados[0]].puntos())
    assert a[1] == pytest.approx(c[1], abs=1e-7) and abs(c[0] - a[0]) == pytest.approx(20, abs=1e-7)
    a, c = (lz.b.coords(p) for p in lz.b.curvas[lados[1]].puntos())
    assert a[0] == pytest.approx(c[0], abs=1e-7)              # sigue vertical
    assert {p: lz.b.coords(p) for c in otra for p in lz.b.curvas[c].puntos()} == antes
    lz.resolver()                                             # soltar: resolver todo da lo mismo
    assert lz.resultado.ok and lz.resultado.residuo_max < 1e-7


def test_una_linea_que_une_dos_partes_resuelve_todo():
    b = Boceto()
    r1 = b.agregar_rectangulo((0, 0), (10, 10))
    r2 = b.agregar_rectangulo((30, 0), (40, 10))
    puente = b.agregar_linea(b.curvas[r1[1]].p2, b.curvas[r2[3]].p2)   # sin restricciones propias
    lz, llamadas = _lienzo(b)
    _mover(lz, puente, 3)
    assert llamadas == [False] * 3
    assert lz.resultado.ok and lz.resultado.residuo_max < 1e-7


def test_la_grilla_de_textos_ocupados_da_lo_mismo_que_mirar_todas():
    import random

    from PySide6.QtCore import QRectF

    from omnicad.ui.editor_boceto_dibujo import _Ocupadas
    azar = random.Random(7)
    cajas = [QRectF(azar.uniform(-300, 300), azar.uniform(-300, 300), azar.uniform(1, 150), azar.uniform(1, 40))
             for _ in range(300)]
    ocupadas = _Ocupadas(cajas[:150])
    for caja in cajas[150:]:
        assert ocupadas.choca(caja) == any(caja.intersects(o) for o in cajas[:150])
    ocupadas.agregar(QRectF(1000, 1000, 5, 5))
    assert ocupadas.choca(QRectF(1003, 1003, 1, 1))
    assert not ocupadas.choca(QRectF(float("nan"), 0, 5, 5))      # no rompe el pintado


def test_a_px_con_visor_da_lo_mismo_que_proyectar():
    """P-182: `a_px` con la matriz plano × cámara en floats es `visor.proyectar` (planos girados y desplazados, puntos
    detrás de la cámara) y se rehace al cambiar la cámara."""
    import numpy as np

    from omnicad.ui.editor_boceto_base import LienzoBaseMixin
    from omnicad.ui.visor3d import Visor3D

    class _Visor:
        proyectar = Visor3D.proyectar

        def width(self):
            return 1500

        def height(self):
            return 950

    class _Lienzo(LienzoBaseMixin):
        pass

    azar = np.random.default_rng(3)
    detras = 0
    for plano in (g.Plano("XY"), g.Plano("YZ", 12.5), g.Plano("XZ", -4)):
        lz = _Lienzo()
        lz.visor, lz.plano = _Visor(), plano
        for _camara in range(3):                                   # cámara nueva: no se usa la matriz vieja
            lz._mvp = azar.normal(size=(4, 4))
            for x, y in azar.uniform(-200, 200, size=(40, 2)):
                w = (lz._mvp @ np.append(plano.a_3d(x, y), 1.0))[3]
                if abs(w) < 1e-6:
                    continue
                q, r = lz.visor.proyectar(plano.a_3d(x, y), lz._mvp), lz.a_px(x, y)
                if q is None:
                    detras += 1
                    assert (r.x(), r.y()) == (-1e5, -1e5)
                else:
                    assert r.x() == pytest.approx(q.x(), rel=1e-9, abs=1e-6)
                    assert r.y() == pytest.approx(q.y(), rel=1e-9, abs=1e-6)
    assert detras > 0


def _zonas_arrastrando(lz, pid, destinos):
    """Arrastra `pid` por `destinos` pintando cada cuadro; devuelve las zonas de las cotas del último cuadro."""
    lz._arrastre = pid
    for cur in destinos:
        lz._mover_punto(pid, cur)
        lz.grab()
    return {i: c.getRect() for i, c in lz._zonas_cotas.items()}


def _zonas_normales(lz):
    arrastre, lz._arrastre = lz._arrastre, None
    lz.grab()
    lz._arrastre = arrastre
    return {i: c.getRect() for i, c in lz._zonas_cotas.items()}


def _dos_piezas_acotadas():
    b = Boceto()
    a = b.agregar_rectangulo((0, 0), (20, 10))
    otra = b.agregar_rectangulo((60, 0), (90, 15))
    for lado, valor in ((a[0], "20"), (a[1], "10"), (otra[0], "30"), (otra[1], "15")):
        b.agregar_cota("distancia", [lado], valor)
    QApplication.instance() or QApplication([])
    lz = Lienzo(b, TablaParametros().evaluar, plano=g.Plano("XY"))
    lz.resolver()
    lz.resize(900, 500)
    return lz, a, otra


def test_cotas_quietas_desde_la_imagen_mientras_se_arrastra():
    """P-182: arrastrando, las cotas que no se mueven salen de la imagen guardada y las zonas son las del camino
    normal; con el boceto ya modificado por un arrastre y una cota cambiada, la imagen vieja no se usa."""
    lz, a, otra = _dos_piezas_acotadas()
    pid = lz.b.curvas[a[1]].p2                                    # esquina de arriba a la derecha (libre en Y)
    destinos = [(20.0, 10.0 + 0.3 * i) for i in range(1, 5)]
    zonas = _zonas_arrastrando(lz, pid, destinos)
    assert lz._cache_cotas is not None                           # el último cuadro copió la imagen
    quietas = {c.id for c in lz.b.cotas.values() if c.entidades[0] in otra}
    assert quietas <= lz._cache_cotas["ids"]
    assert _igual_que_sin_arrastrar(lz)                          # B-741: con el texto (también el girado) igual
    assert zonas == _zonas_normales(lz)
    lz._arrastre = None                                          # soltar: sin imagen
    lz.grab()
    assert lz._cache_cotas is None
    cid = next(c.id for c in lz.b.cotas.values() if c.entidades[0] == otra[0])
    lz.b.cotas[cid].expresion = "40"                              # ya modificado: otra pieza, otro largo
    lz.resolver()
    zonas = _zonas_arrastrando(lz, pid, [(20.0, 12.0 + 0.3 * i) for i in range(1, 5)])
    assert lz._cache_cotas["firmas"][cid] == lz._firma_cota(lz.b.cotas[cid])     # la imagen es de la cota nueva
    assert _igual_que_sin_arrastrar(lz)
    assert zonas == _zonas_normales(lz)


def test_cotas_arrastrando_si_la_via_rapida_falla_dibuja_todo(monkeypatch):
    lz, a, _otra = _dos_piezas_acotadas()

    def falla(*_a):
        raise RuntimeError("caché rota")
    monkeypatch.setattr(type(lz), "_plan_cotas_arrastre", falla)
    pid = lz.b.curvas[a[1]].p2
    zonas = _zonas_arrastrando(lz, pid, [(20.0, 10.0 + 0.3 * i) for i in range(1, 4)])
    assert len(zonas) == 4 and _igual_que_sin_arrastrar(lz) and zonas == _zonas_normales(lz)


def _imagen(lz, arrastrando):
    arrastre = lz._arrastre
    lz._arrastre = arrastre if arrastrando else None
    imagen = lz.grab().toImage().convertToFormat(QImage.Format_RGB32)
    lz._arrastre = arrastre
    return np.frombuffer(imagen.constBits(), np.uint8).reshape(imagen.height(), imagen.width(), 4).astype(int)


def _igual_que_sin_arrastrar(lz):
    """El cuadro arrastrando es el del camino normal, cotas e íconos (B-741: también el texto de las cotas); hasta
    2 niveles por el redondeo de lo semitransparente (bordes suavizados, fondo de los íconos) al copiarlo de la imagen."""
    return np.abs(_imagen(lz, True) - _imagen(lz, False)).max() <= 2


def test_iconos_quietos_desde_la_imagen_mientras_se_arrastra():
    """P-182c: arrastrando, los íconos de restricción que no se mueven salen de una imagen y el cuadro queda igual al
    del camino normal; con el boceto ya modificado (arrastrado y con un ícono elegido), la imagen vieja no se usa."""
    lz, a, otra = _dos_piezas_acotadas()
    pid = lz.b.curvas[a[1]].p2
    _zonas_arrastrando(lz, pid, [(20.0, 10.0 + 0.3 * i) for i in range(1, 5)])
    quietos = {r.id for r in lz.b.restricciones.values() if r.entidades[0] in otra}
    assert quietos and quietos <= {rid for rid, _j in lz._cache_glifos["firmas"]}
    assert _igual_que_sin_arrastrar(lz)
    lz._arrastre = None
    lz.grab()
    assert lz._cache_glifos is None
    rid = min(quietos)
    _zonas_arrastrando(lz, pid, [(20.0, 12.0 + 0.3 * i) for i in range(1, 4)])
    lz.seleccion = [rid]                                          # ya modificado: a mitad del arrastre, un ícono quieto
    _zonas_arrastrando(lz, pid, [(20.0, 13.0 + 0.3 * i) for i in range(1, 4)])     # pasa a elegido
    firmas = lz._cache_glifos["firmas"]                           # el elegido va encima o en una imagen nueva
    assert (rid, 0) not in firmas or firmas[(rid, 0)][3] is True
    assert _igual_que_sin_arrastrar(lz)


def test_iconos_arrastrando_si_la_via_rapida_falla_dibuja_todo(monkeypatch):
    lz, a, _otra = _dos_piezas_acotadas()

    def falla(*_a):
        raise RuntimeError("caché rota")
    monkeypatch.setattr(type(lz), "_glifos_quietos_desde_imagen", falla)
    pid = lz.b.curvas[a[1]].p2
    _zonas_arrastrando(lz, pid, [(20.0, 10.0 + 0.3 * i) for i in range(1, 4)])
    assert lz._cache_glifos is None and _igual_que_sin_arrastrar(lz)
