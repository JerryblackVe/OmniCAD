"""Fase 7 (parte B) del boceto: la interfaz de desfase de dos lados, patrones editables, vínculo de proyección,
perfil giratorio y texto ajustado a la curva (BOC-14, 16, 17, 18 y 20)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout  # noqa: E402

from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import cinta_boceto, dialogos_boceto, editor_boceto, modo_boceto  # noqa: E402


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def _lienzo(app, plano=None):
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar, plano=plano)
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    return lz


@pytest.fixture
def lienzo(app):
    lz = _lienzo(app)
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


def _aceptar(lz, *valores):
    for campo, valor in zip(lz.entrada.campos, valores, strict=False):
        campo.setText(valor)
    lz.entrada.aceptado.emit([c.text() for c in lz.entrada.campos])


def _xs(lz):
    return sorted({round(p.x, 6) for p in lz.b.puntos.values()})


# ---------------------------------------------------------------- BOC-14: desfase de dos lados y simétrico
@pytest.mark.parametrize("modo,valores,esperado", [
    ("dos", ("1", "3"), [-1, 0, 3, 7, 10, 11]),
    ("simetrico", ("2",), [-2, 0, 2, 8, 10, 12]),
    ("un", ("2",), [-2, 0, 10, 12]),
])
def test_boc14_desfase_por_lados_desde_el_editor(lienzo, modo, valores, esperado):
    lz = lienzo
    abajo = lz.b.agregar_rectangulo((0, 0), (10, 10))[0]
    lz.resolver()
    lz.set_herramienta("desfase")
    lz.opciones["direccion_desfase"] = modo
    lz.cursor = (5, -5)                                   # el lado de afuera
    lz.agregar_pick(abajo, (5, 0))
    assert [c.text() for c in lz.entrada.campos][:1] and len(lz.entrada.campos) == (2 if modo == "dos" else 1)
    _aceptar(lz, *valores)
    assert _xs(lz) == pytest.approx(esperado, abs=1e-6)
    assert lz.resultado.ok and len(lz.historial) == 1      # un solo paso de deshacer


def test_boc14_soltar_desfase_desde_la_seleccion(lienzo):
    lz = lienzo
    abajo = lz.b.agregar_rectangulo((0, 0), (10, 10))[0]
    nuevos = lz.b.desfase(abajo, 2, (5, -5))
    lz.resolver()
    lz.seleccion = [nuevos[0]]
    assert lz.soltar_desfase()
    assert not any(r.tipo == "desfase" for r in lz.b.restricciones.values())
    assert len(lz.b.curvas) == 8                          # las curvas quedan
    lz.seleccion = [abajo]
    assert not lz.soltar_desfase()                         # ya no es parte de un desfase


def test_boc14_paleta_ofrece_la_direccion_del_desfase(app):
    paleta = modo_boceto.PaletaBoceto()
    recibido = []
    paleta.ajuste.connect(lambda k, v: recibido.append((k, v)))
    paleta.set_herramienta("desfase", opciones={"direccion_desfase": "un"})
    combo = paleta.contexto.findChild(QComboBox)
    assert [combo.itemData(i) for i in range(combo.count())] == ["un", "dos", "simetrico"]
    combo.setCurrentIndex(2)
    assert recibido == [("direccion_desfase", "simetrico")]


# ---------------------------------------------------------------- BOC-16: patrones editables
def _patron(lz):
    c = lz.b.agregar_circulo((0, 0), 2)
    lz.b.patron_rectangular([c], 3, 20)
    lz.resolver()
    return lz.b.ultimo_patron


def _circulos(lz):
    return sum(1 for c in lz.b.curvas.values() if c.tipo == "circulo")


def test_boc16_dialogo_edita_cantidad_suprime_y_toma_una_linea(lienzo):
    lz = lienzo
    pid = _patron(lz)
    linea = lz.b.agregar_linea((0, 0), (0, 10))
    d = dialogos_boceto.DialogoPatron(lz.b, next(r for r in lz.b.patrones if r["id"] == pid), lz)
    assert d.lista.count() == 2                            # 3 instancias = 2 copias
    d.n1.setValue(4)
    assert d.lista.count() == 3
    d.lista.item(0).setCheckState(Qt.Unchecked)            # destildada = suprimida
    d.linea1.setCurrentIndex(d.linea1.findData(linea))
    cambios = d.cambios()
    assert cambios["cantidad1"] == 4 and cambios["suprimidos"] == [0] and cambios["linea1"] == linea
    d.deleteLater()


def test_boc16_doble_clic_en_el_glifo_edita_el_patron(lienzo, monkeypatch):
    lz = lienzo
    pid = _patron(lz)

    def exec_(self):
        self.n1.setValue(4)
        self.lista.item(0).setCheckState(Qt.Unchecked)
        return QDialog.Accepted
    monkeypatch.setattr(dialogos_boceto.DialogoPatron, "exec", exec_)
    lz.grab()                                              # dibuja: quedan las zonas de los glifos
    rid = next(r.id for r in lz.b.restricciones.values() if r.tipo == "patron")
    centro = lz._zonas_glifos[rid].center()
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseButtonDblClick, centro, centro, Qt.LeftButton,
                                           Qt.LeftButton, Qt.NoModifier))
    registro = next(r for r in lz.b.patrones if r["id"] == pid)
    assert registro["params"]["cantidad1"] == 4 and registro["suprimidos"] == [0]
    assert _circulos(lz) == 3 and len(lz.historial) == 1


def test_boc16_editar_patron_desde_la_seleccion(lienzo, monkeypatch):
    lz = lienzo
    _patron(lz)
    monkeypatch.setattr(dialogos_boceto.DialogoPatron, "exec", lambda self: QDialog.Rejected)
    lz.seleccion = []
    assert not lz.editar_patron()                          # sin selección: avisa
    lz.seleccion = [next(iter(lz.b.curvas))]
    assert not lz.editar_patron()                          # cancelar no cambia nada
    assert _circulos(lz) == 3 and not lz.historial


# ---------------------------------------------------------------- BOC-17: vínculo de proyección
@pytest.fixture
def lienzo_xy(app):
    lz = _lienzo(app, geo.Plano("XY"))
    yield lz
    lz.deleteLater()
    app.processEvents()


REF = {"tipo": "cuerpo", "cuerpo": "op1.c1"}


def test_boc17_interruptor_de_vinculo(lienzo_xy):
    lz = lienzo_xy
    lz.opciones["vinculo_proyeccion"] = False
    assert lz.proyectar_forma(geo.caja(20, 10, 10), "proyectar", REF)
    assert lz.b.proyecciones == [] and lz.b.curvas
    lz.opciones["vinculo_proyeccion"] = True
    assert lz.proyectar_forma(geo.caja(20, 10, 10, (50, 0, 0)), "proyectar", REF)
    assert len(lz.b.proyecciones) == 1


def test_boc17_paleta_tiene_el_interruptor_de_vinculo(app):
    paleta = modo_boceto.PaletaBoceto()
    recibido = []
    paleta.ajuste.connect(lambda k, v: recibido.append((k, v)))
    paleta.set_herramienta("proyectar", opciones={"vinculo_proyeccion": True, "filtro_proyectar": "entidades"})
    casilla = paleta.contexto.findChild(QCheckBox)
    assert casilla.isChecked()
    casilla.setChecked(False)
    assert recibido == [("vinculo_proyeccion", False)]


def test_boc17_romper_vinculo_desde_la_seleccion(lienzo_xy):
    lz = lienzo_xy
    lz.proyectar_forma(geo.caja(20, 10, 10), "proyectar", REF)
    lz.seleccion = []
    assert not lz.romper_vinculo()
    lz.seleccion = [lz.b.proyecciones[0]["ids"][0]]
    assert lz.romper_vinculo()
    assert lz.b.proyecciones == [] and not any(c.proyectada for c in lz.b.curvas.values())


@pytest.mark.parametrize("accion", ["break", "delete"])
def test_boc17_dialogo_de_proyecciones_perdidas(lienzo_xy, accion):
    lz = lienzo_xy
    lz.proyectar_forma(geo.caja(20, 10, 10), "proyectar", REF)
    pid = lz.b.proyecciones[0]["id"]
    lz.perdidas = [pid]
    d = dialogos_boceto.DialogoPerdidas(lz)
    assert d.lista.count() == 1
    d.lista.setCurrentRow(0)
    (d.b_romper if accion == "break" else d.b_borrar).click()
    assert lz.perdidas == [] and lz.b.proyecciones == [] and d.lista.count() == 0
    assert bool(lz.b.curvas) == (accion == "break")
    d.deleteLater()


def test_boc39_atenuar_el_resto_deja_brillar_solo_las_perdidas(lienzo_xy):
    lz = lienzo_xy
    suelta = lz.b.agregar_rectangulo((100, 100), (110, 110))[0]
    lz.proyectar_forma(geo.caja(20, 10, 10), "proyectar", REF)
    registro = lz.b.proyecciones[0]
    lz.perdidas = [registro["id"]]
    d = dialogos_boceto.DialogoPerdidas(lz)
    assert not d.atenuar.isChecked() and lz._brillantes is None            # como Fusion: la casilla arranca apagada
    d.atenuar.setChecked(True)
    assert lz._brillantes == set(registro["ids"]) and suelta not in lz._brillantes
    lz.grab()                                                              # dibujar atenuado no falla
    d.b_romper_todos.click()                                               # ya no hay perdidas: no se apaga nada
    assert lz._brillantes is None
    d.atenuar.setChecked(False)
    assert lz._brillantes is None
    d.atenuar.setChecked(True)
    d.reject()                                                             # al cerrar el diálogo el lienzo vuelve a lo normal
    assert lz._brillantes is None
    d.deleteLater()


def test_boc17_revincular_con_el_siguiente_clic(lienzo_xy):
    lz = lienzo_xy
    lz.proyectar_forma(geo.caja(20, 10, 10), "proyectar", REF)
    pid = lz.b.proyecciones[0]["id"]
    lz.perdidas = [pid]
    lz.revincular(pid)
    assert lz.herramienta == "proyectar"
    otra = {"tipo": "cuerpo", "cuerpo": "op2.c1"}
    lz._usar_entidad({"forma": geo.caja(20, 10, 10, (5, 0, 0)), "ref": otra, "tipo": "cuerpo"})
    assert lz.perdidas == [] and lz.b.proyecciones[0]["refs"] == [otra]
    assert max(p.x for p in lz.b.puntos.values()) == pytest.approx(25)


# ---------------------------------------------------------------- BOC-18: perfil giratorio
@pytest.fixture
def lienzo_xz(app):
    lz = _lienzo(app, geo.Plano("XZ"))
    yield lz
    lz.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("invertir,signo", [(False, 1), (True, -1)])
def test_boc18_perfil_giratorio_de_un_cilindro(lienzo_xz, invertir, signo):
    lz = lienzo_xz
    lz.set_herramienta("perfil_giratorio")
    lz.opciones.update(eje_giro="Z", tolerancia_giro=0.05, invertir_giro=invertir)
    lz._usar_entidad({"forma": geo.cilindro(5, 30), "ref": REF, "tipo": "cuerpo"})
    us = [p.x for p in lz.b.puntos.values()]
    assert max(us, key=abs) == pytest.approx(5 * signo, abs=0.06)
    registro = lz.b.proyecciones[0]
    assert registro["modo"] == "giro" and registro["eje"] == {"tipo": "eje", "id": "Z"}
    assert registro["invertir"] is invertir and registro["tolerancia"] == 0.05


def test_boc18_eje_por_arista_y_sin_vinculo(lienzo_xz):
    from omnicad.nucleo.perfiles import _aristas_unicas
    lz = lienzo_xz
    lz.set_herramienta("perfil_giratorio")
    lz.opciones.update(eje_giro="arista", vinculo_proyeccion=False)
    caja = geo.caja(10, 10, 10)
    aristas = list(_aristas_unicas(caja))
    vertical = next(a for a in aristas if abs(geo.caja_envolvente(a)[1][2] - geo.caja_envolvente(a)[0][2]) > 5)
    lz._usar_entidad({"forma": vertical, "ref": {"tipo": "arista"}, "tipo": "arista"})
    assert not lz.b.curvas                                 # el primer clic es el eje
    lz._usar_entidad({"forma": caja, "ref": REF, "tipo": "cuerpo"})
    assert lz.b.curvas and lz.b.proyecciones == []
    # volver a un eje del origen en la paleta deja de usar la arista elegida
    lz.opciones.update(eje_giro="Z", vinculo_proyeccion=True)
    lz._usar_entidad({"forma": geo.cilindro(5, 30, (0, 40, 0)), "ref": REF, "tipo": "cuerpo"})
    assert lz.b.proyecciones[0]["eje"] == {"tipo": "eje", "id": "Z"}


def test_boc18_paleta_y_cinta_del_perfil_giratorio(app):
    paleta = modo_boceto.PaletaBoceto()
    paleta.set_herramienta("perfil_giratorio", opciones={"eje_giro": "Z", "tolerancia_giro": 0.1,
                                                         "invertir_giro": False, "vinculo_proyeccion": True})
    assert paleta.contexto.findChild(QDoubleSpinBox).value() == pytest.approx(0.1)
    form = paleta.form_contexto
    etiquetas = {form.itemAt(f, QFormLayout.ItemRole.LabelRole).widget().text()
                 for f in range(form.rowCount()) if form.itemAt(f, QFormLayout.ItemRole.LabelRole)}
    assert {"Invertir", "Vínculo de proyección", "Solo contorno exterior", "Proyectar eje"} <= etiquetas
    claves = {a[0] for a in modo_boceto.ACCIONES_BOCETO}
    nuevas = {"sk_perfil_giratorio"}
    assert nuevas <= claves
    en_cinta = repr(cinta_boceto.GRUPOS_BOCETO)
    for clave in ("sk_perfil_giratorio", "sk_soltar_desfase", "sk_editar_patron", "sk_romper_vinculo",
                  "sk_proyecciones_perdidas"):
        assert clave in en_cinta


# ---------------------------------------------------------------- BOC-20: texto ajustado a la curva
def _clic(lz, x, y):
    pos = lz.a_px(x, y)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, pos, pos, Qt.NoButton, Qt.NoButton, Qt.NoModifier))
    for tipo, botones in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, pos, pos, Qt.LeftButton, botones, Qt.NoModifier))


def test_boc20_texto_en_curva_con_ajuste_y_desfase(lienzo):
    lz = lienzo
    lz.b.agregar_linea((0, 0), (60, 0))
    lz.resolver()
    lz.set_herramienta("texto")
    lz.opciones.update(camino_ajustar=True, camino_desfase=2.0)
    _clic(lz, 30, 0)
    _aceptar(lz, "Hola", "5", "0", "0", "1")
    t = next(c for c in lz.b.curvas.values() if c.tipo == "texto")
    assert t.camino is not None and t.camino_ajustar is True and t.camino_desfase == 2.0
    # editar: el panel cambia las opciones y aceptar las guarda en el texto
    lz.editar_texto(t.id, QPointF(lz.a_px(30, 2)))
    lz.opciones.update(camino_ajustar=False, camino_desfase=-1.0)
    lz.entrada.aceptado.emit([c.text() for c in lz.entrada.campos])
    assert t.camino_ajustar is False and t.camino_desfase == -1.0


def test_boc20_panel_caracter_tiene_ajustar_y_desfase(app):
    panel = modo_boceto.PanelCaracter()
    recibido = []
    panel.cambio.connect(lambda k, v: recibido.append((k, v)))
    panel.cargar({"camino_ajustar": True, "camino_desfase": 1.5})
    assert panel.camino_ajustar.isChecked() and panel.camino_desfase.value() == pytest.approx(1.5)
    assert recibido == []
    panel.camino_ajustar.setChecked(False)
    panel.camino_desfase.setValue(3.0)
    assert recibido == [("camino_ajustar", False), ("camino_desfase", 3.0)]


def test_las_acciones_nuevas_de_la_cinta_existen_en_el_modo_boceto(app):
    from PySide6.QtWidgets import QWidget
    ventana = QWidget()
    modo = modo_boceto.ModoBoceto(ventana)
    for clave in ("sk_perfil_giratorio", "sk_soltar_desfase", "sk_editar_patron", "sk_romper_vinculo",
                  "sk_proyecciones_perdidas"):
        assert clave in modo.acciones
        modo.acciones[clave].trigger()                     # sin boceto abierto no hace nada ni falla
    ventana.deleteLater()
