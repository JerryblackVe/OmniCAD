"""Reporte local y borrador de GitHub: codificación, privacidad y gestos reales del diálogo."""
import platform
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

import pytest
from PySide6.QtCore import QPoint, QRect, QSettings, Qt, QTimer
from PySide6.QtGui import QDesktopServices
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QLineEdit, QPlainTextEdit, QPushButton)

from omnicad import VERSION, api, registro_uso as ru
from omnicad.registro_uso import almacen
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.mark.parametrize("tipo,etiqueta", [("Problema", "bug"), ("Sugerencia", "enhancement")])
def test_url_issue_codifica_texto_y_entorno(tipo, etiqueta):
    titulo = "Extrusión & sección #2"
    nota = "La unión no cierra & cambia #3.\nSegunda línea: ¿por qué?"
    url = ru.url_issue(tipo, titulo, nota, "0.2.0", "Windows")
    partes = urlsplit(url)
    campos = parse_qs(partes.query)
    assert (partes.scheme, partes.netloc, partes.path, partes.fragment) == (
        "https", "github.com", "/JerryblackVe/OmniCAD/issues/new", "")
    assert campos["title"] == [titulo]
    assert campos["labels"] == [etiqueta]
    assert campos["body"][0].startswith(nota + "\n\n")
    assert "Versión de OmniCAD: 0.2.0" in campos["body"][0]
    assert "Sistema operativo: Windows" in campos["body"][0]
    assert "arrastrala" not in campos["body"][0]


def test_url_issue_solo_agrega_la_captura_elegida():
    captura = "C:/Users/Persona/registro/marca_á & #1.png"
    campos = parse_qs(urlsplit(ru.url_issue("Problema", "Título", "Nota", "0.2.0", "Linux", captura)).query)
    assert campos["body"][0].endswith("Si marcaste captura, arrastrala acá: " + captura)


@pytest.mark.parametrize("nota", ["a" * 100_000, "á & #\n😀" * 20_000], ids=["ascii", "unicode"])
def test_url_issue_recorta_segun_la_longitud_codificada(nota):
    captura = "C:/registro/marca.png"
    url = ru.url_issue("Sugerencia", "Mejorar sección & #1", nota, "0.2.0", "Windows", captura)
    assert len(url) <= 7000
    campos = parse_qs(urlsplit(url).query)
    assert "recortad" in campos["body"][0].lower()
    assert campos["title"] == ["Mejorar sección & #1"]
    assert campos["labels"] == ["enhancement"]
    assert "Versión de OmniCAD: 0.2.0" in campos["body"][0]
    assert campos["body"][0].endswith("Si marcaste captura, arrastrala acá: " + captura)
    assert "�" not in campos["body"][0]


@pytest.mark.parametrize("titulo", ["", " \t\n"])
def test_url_issue_rechaza_titulo_vacio(titulo):
    with pytest.raises(ValueError, match="[Tt]ítulo"):
        ru.url_issue("Problema", titulo, "nota", "0.2.0", "Windows")


def test_url_issue_rechaza_tipo_y_titulo_imposibles():
    with pytest.raises(ValueError, match="[Tt]ipo"):
        ru.url_issue("Otro", "Título", "", "0.2.0", "Windows")
    with pytest.raises(ValueError, match="[Tt]ítulo"):
        ru.url_issue("Problema", "á" * 10_000, "", "0.2.0", "Windows")


def test_url_issue_no_importa_qt():
    codigo = ("import sys; from omnicad.registro_uso import url_issue; "
              "assert url_issue('Problema', 'Titulo', '', '0.2.0', 'Linux'); "
              "assert not any(k.startswith('PySide') for k in sys.modules)")
    subprocess.run([sys.executable, "-W", "error", "-c", codigo], check=True)


def test_report_issue_url_por_api_no_modifica_ni_abre_navegador(monkeypatch):
    abiertas = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: abiertas.append(url))
    s = api.Sesion()
    resultado = api.llamar(s, "report_issue_url", {
        "title": "Sección & #2", "note": "Primera línea\nSegunda", "type": "Sugerencia"})
    assert resultado["ok"], resultado
    assert resultado["result"]["url"].startswith("https://github.com/JerryblackVe/OmniCAD/issues/new?")
    assert resultado["result"]["url"] == ru.url_issue(
        "Sugerencia", "Sección & #2", "Primera línea\nSegunda", VERSION, platform.system())
    herramienta = next(h for h in api.catalogo() if h["nombre"] == "report_issue_url")
    assert not herramienta["modifica"] and not herramienta["transaccion"]
    assert abiertas == []
    malo = api.llamar(s, "report_issue_url", {"title": " "})
    assert not malo["ok"] and malo["error_kind"] == "INVALID_ARGUMENTS"
    assert "título" in malo["mensaje"].lower()


@pytest.fixture
def ventana(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    ru.configurar(False)
    ru.ultimo = None
    monkeypatch.setenv("OMNICAD_REGISTRO_DIR", str(tmp_path / "registro"))
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)))
    abiertas, mensajes = [], []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: abiertas.append(bytes(url.toEncoded()).decode()) or True)
    monkeypatch.setattr(v, "mensaje", lambda texto, *args: mensajes.append(texto))
    v.resize(800, 520)
    v.show()
    v.registro_uso.configurar(True)
    v.registro_uso.reloj.stop()
    app.processEvents()
    try:
        yield v, abiertas, mensajes
    finally:
        v.registro_uso.configurar(False)
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
        ru.ultimo = None


def _dialogo(ventana, hacer, *, accion=False):
    """El timer entra en exec(); los errores se afirman afuera del slot para que Qt no los trague."""
    fallos = []

    def interactuar():
        d = QApplication.activeModalWidget()
        try:
            assert isinstance(d, QDialog)
            hacer(d)
        except BaseException as e:
            fallos.append(e)
        finally:
            if isinstance(d, QDialog) and d.isVisible():
                d.reject()

    QTimer.singleShot(0, interactuar)
    if accion:
        ventana.registro_uso.accion.trigger()
    else:
        QTest.mouseClick(ventana.registro_uso.boton, Qt.LeftButton)
    if fallos:
        raise fallos[0]


def _campos(d):
    return (d.findChild(QComboBox), d.findChild(QLineEdit), d.findChild(QPlainTextEdit),
            d.findChild(QCheckBox, "abrir_issue_github"), d.findChild(QDialogButtonBox))


def _marcas():
    ru.activo.cola.join()
    return almacen.eventos(ru.activo.id, tipos=["marca"])


def test_boton_compacto_y_dialogo_entero_en_800x520(ventana):
    v, abiertas, _ = ventana
    c = v.registro_uso
    assert c.boton.text() == "Reportar"
    assert c.boton.objectName() == "marcar_problema"
    assert c.boton.toolTip() == "Reportar problema y sugerencia"
    assert c.boton.accessibleName() == "Reportar problema y sugerencia"
    assert c.accion.text() == c.accion.toolTip() == "Reportar problema y sugerencia"
    assert not c.boton.icon().pixmap(16, 16).isNull()
    vecino = QPushButton("Vecino", v)
    vecino.ensurePolished()
    assert c.boton.height() == vecino.sizeHint().height()
    assert c.boton.width() < 130

    def mirar(d):
        assert d.windowTitle() == "Reportar problema y sugerencia"
        tipo, titulo, nota, github, botones = _campos(d)
        assert [tipo.itemText(i) for i in range(tipo.count())] == ["Problema", "Sugerencia"]
        assert titulo is not None and nota is not None and not github.isChecked()
        captura = d.findChild(QCheckBox, "adjuntar_captura")
        assert captura.text() == "Adjuntar captura" and not captura.isChecked()
        aceptar = botones.button(QDialogButtonBox.Ok)
        assert aceptar.text() == "Aceptar" and botones.button(QDialogButtonBox.Cancel).text() == "Cancelar"
        assert aceptar.isVisible() and aceptar.isEnabled()
        assert d.rect().contains(QRect(aceptar.mapTo(d, QPoint(0, 0)), aceptar.size()))
        assert d.frameGeometry().width() <= 800 and d.frameGeometry().height() <= 520
        assert QRect(v.mapToGlobal(QPoint(0, 0)), v.size()).contains(d.frameGeometry())
        QTest.keyClick(titulo, Qt.Key_Escape)

    _dialogo(v, mirar)
    assert _marcas() == [] and abiertas == []


@pytest.mark.parametrize("github", [False, True])
def test_aceptar_guarda_tipo_titulo_nota_y_github_optativo(ventana, github):
    v, abiertas, _ = ventana

    def escribir(d):
        tipo, titulo, nota, casilla, botones = _campos(d)
        tipo.setFocus()
        QTest.keyClick(tipo, Qt.Key_Down)
        QTest.mouseClick(titulo, Qt.LeftButton)
        QTest.keyClicks(titulo, "Mejorar & #1")
        QTest.mouseClick(nota, Qt.LeftButton)
        QTest.keyClicks(nota, "Primera & #2")
        QTest.keyClick(nota, Qt.Key_Return)
        QTest.keyClicks(nota, "Segunda")
        assert d.isVisible() and nota.toPlainText() == "Primera & #2\nSegunda"
        if github:
            QTest.mouseClick(casilla, Qt.LeftButton, pos=QPoint(8, casilla.height() // 2))
            assert casilla.isChecked()
        QTest.mouseClick(botones.button(QDialogButtonBox.Ok), Qt.LeftButton)

    _dialogo(v, escribir)
    marca, = _marcas()
    assert marca["datos"]["tipo"] == "Sugerencia"
    assert marca["datos"]["titulo"] == "Mejorar & #1"
    assert marca["datos"]["nota"] == "Primera & #2\nSegunda"
    esperadas = [ru.url_issue("Sugerencia", "Mejorar & #1", "Primera & #2\nSegunda", VERSION, platform.system())]
    assert abiertas == (esperadas if github else [])
    if abiertas:
        cuerpo = parse_qs(urlsplit(abiertas[0]).query)["body"][0]
        assert str(ru.activo.carpeta) not in cuerpo and v.doc.nombre not in cuerpo
        assert ru.activo.id not in cuerpo and "proyecto" not in cuerpo.lower()


def test_titulo_obligatorio_solo_para_github_y_enter_solo_desde_titulo(ventana):
    v, abiertas, _ = ventana

    def escribir(d):
        _, titulo, nota, github, botones = _campos(d)
        aceptar = botones.button(QDialogButtonBox.Ok)
        assert aceptar.isEnabled()
        QTest.mouseClick(github, Qt.LeftButton, pos=QPoint(8, github.height() // 2))
        assert not aceptar.isEnabled()
        QTest.keyClick(titulo, Qt.Key_Return)
        assert d.isVisible()
        QTest.keyClicks(titulo, "Titulo")
        assert aceptar.isEnabled()
        for control in (github, d.findChild(QComboBox), aceptar, botones.button(QDialogButtonBox.Cancel)):
            control.setFocus()
            QTest.keyClick(control, Qt.Key_Return)
            assert d.isVisible()
        nota.setFocus()
        QTest.keyClick(nota, Qt.Key_Return)
        assert d.isVisible() and nota.toPlainText() == "\n"
        titulo.setFocus()
        QTest.keyClick(titulo, Qt.Key_Return)
        assert not d.isVisible()

    _dialogo(v, escribir)
    assert len(_marcas()) == len(abiertas) == 1


def test_esc_desde_la_nota_no_guarda_y_accion_abre_el_dialogo(ventana):
    v, abiertas, _ = ventana

    def cancelar(d):
        assert d.windowTitle() == "Reportar problema y sugerencia"
        _, titulo, nota, _, _ = _campos(d)
        QTest.keyClicks(titulo, "Cancelar")
        nota.setFocus()
        QTest.keyClicks(nota, "No guardar")
        QTest.keyClick(nota, Qt.Key_Escape)

    _dialogo(v, cancelar, accion=True)
    assert _marcas() == [] and abiertas == []


def test_nota_pegada_se_limita_a_2000_y_se_puede_guardar_sin_titulo(ventana):
    v, abiertas, _ = ventana

    def pegar(d):
        _, _, nota, _, botones = _campos(d)
        QApplication.clipboard().setText("á" * 2005)
        nota.setFocus()
        QTest.keyClick(nota, Qt.Key_V, Qt.ControlModifier)
        assert nota.toPlainText() == "á" * 2000
        QTest.mouseClick(botones.button(QDialogButtonBox.Ok), Qt.LeftButton)

    _dialogo(v, pegar)
    marca, = _marcas()
    assert marca["datos"]["titulo"] == "" and marca["datos"]["tipo"] == "Problema"
    assert marca["datos"]["nota"] == "á" * 2000 and abiertas == []


def test_captura_optativa_llega_a_la_url_con_su_ruta_real(ventana, monkeypatch):
    v, abiertas, _ = ventana
    monkeypatch.setattr(v.visor, "captura_png", lambda: b"captura de prueba")

    def escribir(d):
        _, titulo, _, github, botones = _campos(d)
        QTest.keyClicks(titulo, "Captura")
        for casilla in (github, d.findChild(QCheckBox, "adjuntar_captura")):
            QTest.mouseClick(casilla, Qt.LeftButton, pos=QPoint(8, casilla.height() // 2))
            assert casilla.isChecked()
        QTest.mouseClick(botones.button(QDialogButtonBox.Ok), Qt.LeftButton)

    _dialogo(v, escribir)
    marca, = _marcas()
    png = ru.activo.carpeta / f"marca_{ru.activo.id}_{marca['seq']}.png"
    assert png.read_bytes() == b"captura de prueba"
    assert abiertas == [ru.url_issue("Problema", "Captura", "", VERSION, platform.system(), str(png))]


def test_si_no_abre_el_navegador_la_marca_queda_guardada_y_avisa(ventana, monkeypatch):
    v, abiertas, mensajes = ventana
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: False)

    def escribir(d):
        _, titulo, _, github, botones = _campos(d)
        QTest.keyClicks(titulo, "Reporte local")
        QTest.mouseClick(github, Qt.LeftButton, pos=QPoint(8, github.height() // 2))
        QTest.mouseClick(botones.button(QDialogButtonBox.Ok), Qt.LeftButton)

    _dialogo(v, escribir)
    assert len(_marcas()) == 1 and abiertas == []
    assert any("navegador" in m.lower() and "guard" in m.lower() for m in mensajes)
