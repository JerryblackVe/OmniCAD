"""Segunda tanda del editor 2D: controles con efectos reales y ratón simulado."""
import math
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QCheckBox, QDialog, QFormLayout, QMessageBox, QWidget  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.api.herramientas_boceto import op_boceto  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import cinta_boceto, dialogos_boceto, editor_boceto, modo_boceto  # noqa: E402


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def lienzo(app):
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar, plano=geo.Plano("XZ"))
    lz.resize(800, 600)
    lz.ajustar_grilla = False
    lz.show()
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


def _mover(lz, x, y):
    p = lz.a_px(x, y)
    QApplication.sendEvent(lz, QMouseEvent(QEvent.MouseMove, p, p, Qt.NoButton, Qt.NoButton, Qt.NoModifier))


def _clic(lz, x, y):
    _mover(lz, x, y)
    p = lz.a_px(x, y)
    for tipo, botones in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
        QApplication.sendEvent(lz, QMouseEvent(tipo, p, p, Qt.LeftButton, botones, Qt.NoModifier))


def _aceptar(lz, *valores):
    for campo, valor in zip(lz.entrada.campos, valores, strict=False):
        campo.setText(valor)
    lz.entrada.aceptado.emit([c.text() for c in lz.entrada.campos])


def _casilla(paleta, etiqueta):
    form = paleta.form_contexto
    for fila in range(form.rowCount()):
        nombre = form.itemAt(fila, QFormLayout.ItemRole.LabelRole)
        if nombre and nombre.widget().text() == etiqueta:
            return form.itemAt(fila, QFormLayout.ItemRole.FieldRole).widget()
    pytest.fail(f"Falta el control {etiqueta}")


@pytest.mark.parametrize("direccion", ["un", "dos", "simetrico"])
def test_match_topology_casilla_limita_y_avisa(lienzo, direccion):
    lz = lienzo
    lz.b.agregar_rectangulo((10, 20), (20, 24))
    lz.centro, lz.escala = [15.0, 22.0], 20.0
    lz.resolver()
    lz.set_herramienta("desfase")
    lz.opciones["direccion_desfase"] = direccion
    paleta = modo_boceto.PaletaBoceto(lz)
    paleta.ajuste.connect(lambda k, v: lz.opciones.__setitem__(k, v))
    paleta.set_herramienta("desfase", opciones=lz.opciones)
    casilla = _casilla(paleta, "Match Topology")
    assert isinstance(casilla, QCheckBox) and not casilla.isChecked()
    casilla.setChecked(True)
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    _clic(lz, 15, 20)
    _mover(lz, 15, 22)
    _aceptar(lz, "3", "1")
    assert lz.resultado.ok and len(lz.historial) == 1
    cotas = sorted(lz.evaluar(c.expresion) for c in lz.b.cotas.values() if c.tipo == "desfase")
    assert len(cotas) == (1 if direccion == "un" else 2)
    assert any(abs(c - 2) < 0.01 for c in cotas)
    assert any("Match Topology" in m and "limit" in m for m in mensajes)
    assert len(lz.b.curvas) == (8 if direccion == "un" else 12)


def test_patron_avisa_cotas_y_restricciones_perdidas(lienzo, monkeypatch):
    lz = lienzo
    c = lz.b.agregar_circulo((10, 20), 2)
    lz.b.patron_rectangular([c], 3, 20)
    registro = lz.b.patrones[0]
    copia = next(i for i in registro["copias"]["1"] if i in lz.b.curvas)
    cota = lz.b.agregar_cota("radio", [copia], "2")
    lz.b.cotas[cota].referencia = True
    fijo = lz.b.agregar_restriccion("fijo", [copia])
    lz.resolver()

    def ejecutar(d):
        d.n1.setValue(2)
        assert d.lista.count() == 1
        return QDialog.Accepted

    monkeypatch.setattr(dialogos_boceto.DialogoPatron, "exec", ejecutar)
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: avisos.append(a[2]))
    assert lz.editar_patron(registro["id"])
    assert sum(c.tipo == "circulo" for c in lz.b.curvas.values()) == 2
    assert cota not in lz.b.cotas and fijo not in lz.b.restricciones
    assert len(avisos) == 1 and f"cota {cota}" in avisos[0] and f"restricción {fijo}" in avisos[0]


REF = {"tipo": "cuerpo", "cuerpo": "op1.c1"}
OTRA = {"tipo": "cuerpo", "cuerpo": "op2.c1"}


@pytest.mark.parametrize("giro", [False, True])
def test_revincular_desde_dialogo_con_clic_en_cuerpo(lienzo, giro):
    lz = lienzo
    if giro:
        assert lz.perfil_giratorio_forma(geo.cilindro(5, 30), REF)
        nueva = geo.cilindro(7, 30)
    else:
        assert lz.proyectar_forma(geo.caja(20, 10, 10), ref=REF)
        nueva = geo.caja(20, 10, 10, (5, 0, 0))
    registro = lz.b.proyecciones[0]
    lz.perdidas = [registro["id"]]
    d = dialogos_boceto.DialogoPerdidas(lz)
    d.lista.setCurrentRow(0)
    assert d.b_revincular.isEnabled()
    d.b_revincular.click()
    assert d.result() == QDialog.Accepted
    filtros = []

    class Visor:
        def mapFromGlobal(self, p):
            return p

        def elegir_entidad(self, p, tipos):
            filtros.append(tipos)
            return {"forma": nueva, "ref": OTRA, "tipo": "cuerpo"}

    lz.visor = Visor()
    lz._clic_proyectar(QPointF(100, 100))
    lz.visor = None
    assert "cuerpo" in filtros[0]
    assert lz.perdidas == [] and registro["refs"] == [OTRA]
    assert max(p.x for p in lz.b.puntos.values()) == pytest.approx(7 if giro else 25, abs=0.1)
    if giro:
        assert registro["eje"] == {"tipo": "eje", "id": "Z"} and registro["modo"] == "giro"


@pytest.mark.parametrize("vinculo", [True, False])
def test_contorno_exterior_casilla_cambia_el_perfil(lienzo, vinculo):
    lz = lienzo
    paleta = modo_boceto.PaletaBoceto(lz)
    lz.opciones["vinculo_proyeccion"] = vinculo
    paleta.ajuste.connect(lambda k, v: lz.opciones.__setitem__(k, v))
    lz.set_herramienta("perfil_giratorio")
    paleta.set_herramienta("perfil_giratorio", opciones=lz.opciones)
    casilla = _casilla(paleta, "Solo contorno exterior")
    assert casilla.isChecked()
    forma = geo.booleano(geo.caja(20, 20, 10, (-10, -10, 0)), geo.cilindro(3, 10), "cortar")
    assert lz.perfil_giratorio_forma(forma, REF)
    assert min(abs(p.x) for p in lz.b.puntos.values()) > 9.9
    lz.deshacer()
    casilla.setChecked(False)
    assert lz.perfil_giratorio_forma(forma, REF)
    assert min(abs(p.x) for p in lz.b.puntos.values()) == pytest.approx(3, abs=0.1)
    assert bool(lz.b.proyecciones) is vinculo


def test_proyectar_eje_cinta_y_casilla(lienzo):
    lz = lienzo
    ventana = QWidget()
    modo = modo_boceto.ModoBoceto(ventana)
    modo.lienzo = lz
    accion = modo.acciones.get("sk_proyectar_eje")
    assert accion is not None and "sk_proyectar_eje" in repr(cinta_boceto.GRUPOS_BOCETO)
    accion.setEnabled(True)
    accion.trigger()
    assert len(lz.b.curvas) == 1
    linea = next(iter(lz.b.curvas.values()))
    assert linea.proyectada and math.dist(*map(lz.b.coords, linea.puntos())) == pytest.approx(200)
    assert lz.b.proyecciones[0]["refs"] == [{"tipo": "eje", "id": "Z"}]
    lz.deshacer()
    lz.set_herramienta("perfil_giratorio")
    paleta = modo_boceto.PaletaBoceto(lz)
    paleta.ajuste.connect(lambda k, v: lz.opciones.__setitem__(k, v))
    paleta.set_herramienta("perfil_giratorio", opciones=lz.opciones)
    casilla = _casilla(paleta, "Proyectar eje")
    assert not casilla.isChecked()
    casilla.setChecked(True)
    assert lz.perfil_giratorio_forma(geo.cilindro(5, 30), REF)
    assert len(lz.b.proyecciones) == 2 and len(lz.historial) == 1
    ventana.deleteLater()


def test_marco_texto_dibuja_cuatro_esquinas_y_lados_acotables(lienzo):
    lz = lienzo
    lz.mostrar.update(rejilla=False, restricciones=False)
    tid = lz.b.agregar_texto((10, 20), "I")
    lados = lz.b.agregar_marco_texto(tid, 40, 10)
    lz.resolver()
    img = lz.grab().toImage()
    fondo = img.pixelColor(5, 5)
    for xy in ((10, 20), (50, 20), (10, 30), (50, 30), (30, 20), (50, 25), (30, 30), (10, 25)):
        p = lz.a_px(*xy)
        assert any(img.pixelColor(int(p.x()) + dx, int(p.y()) + dy) != fondo
                   for dx in range(-3, 4) for dy in range(-3, 4)), xy
    lz.set_herramienta("cota")
    _clic(lz, 30, 20)
    _clic(lz, 30, 15)
    _aceptar(lz, "60")
    assert lz.resultado.ok
    assert math.dist(*map(lz.b.coords, lz.b.curvas[lados[0]].puntos())) == pytest.approx(60)


@pytest.mark.parametrize("esquina", ["tl", "tr", "bl", "br", "center"])
def test_pivote_del_panel_gira_marco_y_conserva_esquina(lienzo, esquina):
    lz = lienzo
    tid = lz.b.agregar_texto((10, 20), "I")
    lados = lz.b.agregar_marco_texto(tid, 40, 10)
    lz.resolver()
    lz.editar_texto(tid, lz.a_px(10, 20))
    panel = modo_boceto.PanelCaracter(lz)
    panel.cargar(lz.opciones)
    panel.cambio.connect(lambda k, v: lz.opciones.__setitem__(k, v))
    assert panel.pivote.isEnabled() and panel.pivote.count() == 6
    panel.pivote.setCurrentIndex(panel.pivote.findData(f"corner:{esquina}"))
    pivote = lz.b.esquina_marco(tid, esquina)
    antes = [q for poli in lz._previa_polis for q in poli]
    lz.entrada.campos[2].setText("90")
    despues = [q for poli in lz._previa_polis for q in poli]
    ancho = max(q[0] for q in despues) - min(q[0] for q in despues)
    alto_original = max(q[1] for q in antes) - min(q[1] for q in antes)
    assert ancho == pytest.approx(alto_original, abs=1e-6)
    _aceptar(lz, "I", "5", "90")
    assert lz.b.esquina_marco(tid, esquina) == pytest.approx(pivote, abs=1e-7)
    assert lz.b.curvas[tid].angulo == pytest.approx(90)
    assert sorted(math.dist(*map(lz.b.coords, lz.b.curvas[i].puntos())) for i in lados) == pytest.approx([10, 10, 40, 40])
    assert len(lz.historial) == 1


@pytest.fixture
def modo_texto(app):
    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {"plane": "XY"})["ok"]
    assert api.llamar(s, "add_text", {"text": "I", "x": 10, "y": 20, "frame": True,
                                     "box_width": 40, "frame_height": 10})["ok"]
    b = op_boceto(s, None).boceto.copia()
    tid = next(i for i, c in b.curvas.items() if c.tipo == "texto")
    ventana = QWidget()
    ventana.doc = s.doc
    ventana.area = SimpleNamespace(reubicar=lambda: None)
    ventana.mensaje = lambda *a: None
    modo = modo_boceto.ModoBoceto(ventana)
    lz = editor_boceto.Lienzo(b, lambda *a: ventana.doc.parametros.evaluar(*a))
    lz.editar_parametro_texto = modo._editar_parametro_texto
    lz.valores_parametros = lambda: ventana.doc.parametros.valores()
    modo.lienzo, modo.boceto = lz, b
    modo.paleta, modo.caracter = modo_boceto.PaletaBoceto(), modo_boceto.PanelCaracter()
    modo.caracter.cambio.connect(modo._ajuste)
    lz.texto_en_edicion.connect(modo._opciones_de_texto)
    yield modo, s, tid
    for w in (lz, modo.paleta, modo.caracter, ventana):
        w.close()
        w.deleteLater()
    app.processEvents()


def test_panel_text_muestra_y_edita_parametro_por_set_parameter(modo_texto, monkeypatch):
    modo, s, tid = modo_texto
    lz, b = modo.lienzo, modo.boceto
    llamadas = []
    llamar = api.llamar

    def registrar(sesion, nombre, argumentos):
        llamadas.append((nombre, argumentos))
        return llamar(sesion, nombre, argumentos)

    monkeypatch.setattr(api, "llamar", registrar)
    lz.editar_texto(tid, lz.a_px(10, 20))
    panel = modo.caracter
    assert panel.parametro_texto.text() == "Text"
    assert panel.valor_parametro_texto.isEnabled() and panel.valor_parametro_texto.text() == "I"
    inicial = len(lz._previa_polis)
    panel.valor_parametro_texto.setText("WWW")
    panel.valor_parametro_texto.editingFinished.emit()
    assert any(n == "set_parameter" and a == {"name": "Text", "expression": "WWW"} for n, a in llamadas)
    assert modo.v.doc.parametros.valores()["Text"] == "WWW"
    cantidad = len(lz._previa_polis)
    lz.entrada.aceptado.emit([c.text() for c in lz.entrada.campos])
    assert b.curvas[tid].parametro_texto == "Text" and b.curvas[tid].texto == "{Text}"
    assert cantidad > inicial and len(lz._polilineas(b.curvas[tid])) == cantidad
    assert len(op_boceto(s, None).boceto.curvas) == 5


def test_parametro_rechazado_conserva_boceto_y_valor_del_panel(modo_texto, monkeypatch):
    modo, s, tid = modo_texto
    lz, panel = modo.lienzo, modo.caracter
    lz.aplicar_cambio(lambda: lz.b.agregar_punto(80, 30))
    lz.deshacer()
    rehacer = lz.pila_rehacer[:]
    lz.editar_texto(tid, lz.a_px(10, 20))
    antes = s.doc.a_dict()
    mensajes = []
    modo.v.mensaje = lambda texto, *a: mensajes.append(texto)
    llamar_real = api.llamar
    monkeypatch.setattr(api, "llamar", lambda *a: {"ok": False, "error": "Cambio rechazado"})
    panel.valor_parametro_texto.setText("Otro")
    panel.valor_parametro_texto.editingFinished.emit()
    assert s.doc.a_dict() == antes and mensajes == ["Cambio rechazado"]
    assert panel.valor_parametro_texto.text() == "I" and lz.entrada.campos[0].text() == "I"
    boceto_antes = lz.b.a_dict()
    _aceptar(lz, "Otro", "5", "90")
    assert lz.b.a_dict() == boceto_antes and not lz.historial
    assert lz.pila_rehacer == rehacer
    monkeypatch.setattr(api, "llamar", llamar_real)
    _aceptar(lz, "II", "7", "90")
    assert lz.b.curvas[tid].angulo == pytest.approx(90) and s.doc.parametros.valores()["Text"] == "II"
    assert lz.b.curvas[tid].altura == pytest.approx(7)


def test_controles_de_texto_sin_marco_o_parametro_estan_deshabilitados(lienzo):
    lz = lienzo
    tid = lz.b.agregar_texto((10, 20), "Antiguo")
    lz.editar_texto(tid, lz.a_px(10, 20))
    panel = modo_boceto.PanelCaracter(lz)
    panel.cargar(lz.opciones)
    assert not panel.pivote.isEnabled() and not panel.valor_parametro_texto.isEnabled()
    assert panel.parametro_texto.text() == "Sin parámetro ligado"
