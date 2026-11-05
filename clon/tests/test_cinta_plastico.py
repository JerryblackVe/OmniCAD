# -*- coding: utf-8 -*-
"""PLA-6: la pestaña PLÁSTICO de la cinta con los grupos de Fusion (CONFIGURACIÓN, CREAR de SÓLIDO completo,
«Duplicar con uniones» también en INSERTAR) y los nombres de Fusion en los comandos."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QAction  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton  # noqa: E402

from omnicad.ui.cinta import Cinta  # noqa: E402

PLASTICO, SOLIDO = 4, 0        # índices en PESTANAS


class _Acciones(dict):
    """Acciones al vuelo igual que en test_cinta_textos: la clave hace de texto."""

    def __missing__(self, clave):
        a = QAction(clave.replace("_", " ").capitalize())
        self[clave] = a
        return a


@pytest.fixture
def cinta():
    QApplication.instance() or QApplication([])
    c = Cinta(_Acciones())
    c.resize(4000, 160)
    c.show()
    QTest.qWaitForWindowExposed(c)
    yield c
    c.close()
    c.deleteLater()


def _pagina(c, n):
    c.pestanas[n].click()
    return c.pila.currentWidget()


def _grupo(pag, titulo):
    return next(b for b in pag.findChildren(QToolButton, "titulo_grupo") if b.text().startswith(titulo))


def _menu(pag, grupo):
    return [a for a in _grupo(pag, grupo).menu().actions() if not a.isSeparator()]


def test_configuracion_primero_con_las_dos_reglas(cinta):
    pag = _pagina(cinta, PLASTICO)
    titulos = [b.text() for b in pag.findChildren(QToolButton, "titulo_grupo")]
    assert titulos[:4] == ["CONFIGURACIÓN ▾", "CREAR ▾", "MODIFICAR ▾", "REVISAR ▾"]
    reglas = _menu(pag, "CONFIGURACIÓN")
    assert cinta.acciones["asignar_regla_plastico"] in reglas
    assert cinta.acciones["reglas_plastico"] in reglas
    assert cinta.acciones["reglas_plastico"] not in _menu(pag, "MODIFICAR")


def test_crear_de_plastico_es_el_de_solido_mas_los_de_plastico(cinta):
    pag_pl = _pagina(cinta, PLASTICO)
    pag_sol = _pagina(cinta, SOLIDO)
    sol = [a.text() for a in _menu(pag_sol, "CREAR")]
    plas = [a.text() for a in _menu(pag_pl, "CREAR")]
    i = sol.index("Repujado") + 1
    bloque = plas[i:i + 5]
    assert bloque == ["Saliente", "Grampa", "Labio", "Apoyo", "Patron geometrico"]
    assert plas[:i] + plas[i + 5:] == sol, "CREAR de PLÁSTICO debe tener los comandos de SÓLIDO, en el mismo orden"
    # los comandos reales son la misma QAction (los grisados son nuevas en cada menú)
    reales = [a for a in _menu(pag_sol, "CREAR") if a.isEnabled() and a.menu() is None]
    plas_obj = _menu(pag_pl, "CREAR")
    assert all(a in plas_obj for a in reales)


def test_duplicar_con_uniones_tambien_en_insertar(cinta):
    pag = _pagina(cinta, SOLIDO)
    a = cinta.acciones["duplicar_con_uniones"]
    assert a in _menu(pag, "ENSAMBLAR")
    ins = _menu(pag, "INSERTAR")
    assert a in ins
    textos = [x.text() for x in ins]
    assert textos.index("Fijacion") < textos.index("Duplicar con uniones") < textos.index("Insertar derivacion")


def _abrir_y_clic(cinta, grupo, clave, abiertos):
    a = cinta.acciones[clave]
    menu = grupo.menu()
    assert a in [x for x in menu.actions() if not x.isSeparator()], f"{clave} no está en {grupo.text()}"
    a.triggered.connect(lambda _=False, c=clave: abiertos.append(c))
    QTest.mouseClick(grupo, Qt.LeftButton)
    assert menu.isVisible()
    QTest.mouseClick(menu, Qt.LeftButton, Qt.NoModifier, menu.actionGeometry(a).center())
    return abiertos


def test_clic_como_usuario_en_los_botones_nuevos_del_plastico(cinta):
    pag = _pagina(cinta, PLASTICO)
    abiertos = []
    for titulo, claves in (("CONFIGURACIÓN", ["asignar_regla_plastico", "reglas_plastico"]),
                           ("CREAR", ["saliente", "labio", "patron_geometrico"])):
        for clave in claves:
            _abrir_y_clic(cinta, _grupo(pag, titulo), clave, abiertos)
    assert abiertos == ["asignar_regla_plastico", "reglas_plastico", "saliente", "labio", "patron_geometrico"]


def test_clic_en_el_boton_rapido_de_saliente(cinta):
    pag = _pagina(cinta, PLASTICO)
    b = next(b2 for b2 in pag.findChildren(QToolButton, "boton_cinta") if b2.defaultAction() is cinta.acciones["saliente"])
    abiertos = []
    cinta.acciones["saliente"].triggered.connect(lambda _=False: abiertos.append(True))
    QTest.mouseClick(b, Qt.LeftButton)
    assert abiertos == [True]


def test_nombres_de_fusion():
    from omnicad.ui.comandos.crear import Labio, Saliente, SolidoEnvolvente
    from omnicad.ui.comandos.fijacion import InsertarFijacion
    from omnicad.ui.comandos.modificar import ReticulaVolumetrica
    assert Saliente.TITULO == "Saliente de fijación"
    assert Labio.TITULO == "Labio"
    assert SolidoEnvolvente.TITULO == "Sólido delimitador"
    assert ReticulaVolumetrica.TITULO == "Entramado volumétrico"
    assert InsertarFijacion.TITULO == "Insertar fijador"
