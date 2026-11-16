"""B-572: en el panel Boceto 3D, teclear los puntos en «Puntos» y dar Intro dibuja (como «Agregar»); un texto que no
se entiende avisa en un renglón, sin jerga, y pinta el campo de rojo."""
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from test_p23_navegador import v as v, ventana as ventana  # noqa: F401  (fixtures de la ventana en vivo)

from omnicad.restricciones import Boceto
from omnicad.timeline.operaciones import OpBoceto


def _paleta(v, tmp_path):
    from omnicad.ui.puente import PuenteAgentes
    ident = v.doc.nuevo_id()
    v.doc.agregar(OpBoceto(ident, "Ruta 3D", plano="XY", boceto=Boceto()))
    assert PuenteAgentes(v, archivo=tmp_path / "puente.json").ejecutar("sketch_view", {"sketch": ident, "action": "edit"})["ok"]
    paleta = v.modo_boceto.paleta
    paleta.checks["boceto3d"].setChecked(True)
    return paleta


def _teclear(campo, texto):
    campo.setFocus()
    campo.selectAll()
    QTest.keyClicks(campo, texto)
    QTest.keyClick(campo, Qt.Key_Return)


def test_b572_intro_en_puntos_dibuja_la_linea_por_puntos(v, tmp_path):
    paleta = _paleta(v, tmp_path)
    lz = v.modo_boceto.lienzo
    _teclear(paleta.puntos3d, "0,0,0; 0,0,20; 20,0,20; 20,0,40")
    assert len(lz.b.geo3d["curvas"]) == 3 and v.modo_boceto.activo
    _teclear(paleta.puntos3d, " 0 , 0 , 50 ;  0 , 10 , 50 ")          # con espacios también
    assert len(lz.b.geo3d["curvas"]) == 4
    g = lz.b.geo3d
    assert sorted(map(tuple, g["puntos"].values())) == sorted(
        [(0, 0, 0), (0, 0, 20), (20, 0, 20), (20, 0, 40), (0, 0, 50), (0, 10, 50)])


def test_b572_texto_que_no_se_entiende_avisa_y_pinta_el_campo(v, tmp_path, monkeypatch):
    paleta = _paleta(v, tmp_path)
    lz = v.modo_boceto.lienzo
    avisos = []
    monkeypatch.setattr(v, "mensaje", lambda texto, ms=5000: avisos.append(texto))
    for malo in ("0,0,0; 0,a,20", "0,0,0; 0,0"):
        avisos.clear()
        _teclear(paleta.puntos3d, malo)
        assert not lz.b.geo3d.get("curvas")
        (aviso,) = avisos
        assert "\n" not in aviso and "float" not in aviso and "zip" not in aviso and "x, y, z" in aviso, aviso
        assert paleta.puntos3d.styleSheet(), "el campo tiene que quedar en rojo"
    QTest.keyClick(paleta.puntos3d, Qt.Key_Backspace)                   # al corregir, vuelve al color normal
    assert not paleta.puntos3d.styleSheet()
    paleta.bloqueo3d.setCurrentIndex(paleta.bloqueo3d.findData("z"))    # con un eje: el largo vacío pinta «Largo»
    paleta.puntos3d.setText("1, 2, 0")
    _teclear(paleta.largo3d, "")
    assert not lz.b.geo3d.get("curvas") and paleta.largo3d.styleSheet() and not paleta.puntos3d.styleSheet()
    assert "largo" in avisos[-1]
    paleta.h3d.setCurrentIndex(paleta.h3d.findData("spline"))          # error de herramienta: pinta «Puntos»
    paleta.largo3d.setText("15")
    QTest.keyClick(paleta.largo3d, Qt.Key_Return)
    assert paleta.puntos3d.styleSheet()
    paleta.h3d.setCurrentIndex(paleta.h3d.findData("linea"))            # corregido el combo, el rojo se va al agregar
    QTest.keyClick(paleta.largo3d, Qt.Key_Return)
    assert len(lz.b.geo3d["curvas"]) == 1 and not paleta.puntos3d.styleSheet() and not paleta.largo3d.styleSheet()
