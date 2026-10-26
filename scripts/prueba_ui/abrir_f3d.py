# -*- coding: utf-8 -*-
"""Abrir un .f3d de Fusion como una persona: Archivo › Abrir (el archivo se elige en el diálogo), el aviso de espera con
la etapa en que va, y lo que queda en la ventana: los 10 bocetos de BINCHA.f3d en el navegador, en el historial y dibujados
en el visor, y sus 5 mallas ocultas con el ojo cerrado. Después: clic en un boceto del navegador, doble clic (editar),
deshacer, guardar y reabrir el .omnicad. El archivo vive en el escritorio de la PC de desarrollo (`~/Desktop/f3z`); sin
él la pieza no comprueba nada."""
import sys
import tempfile
import time
from pathlib import Path

import arnes as A
from omnicad.timeline.documento import Documento
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QProgressDialog

AR = "ABRIR F3D"
RUTA = Path.home() / "Desktop" / "f3z" / "BINCHA.f3d"

app, v = A.iniciar(Documento())
ETAPAS = []                                    # lo que dice el aviso de espera mientras abre
_poner = QProgressDialog.setLabelText
QProgressDialog.setLabelText = lambda self, t: (ETAPAS.append(t), _poner(self, t))[1]


def pasos_de_boceto():
    return [o for o in v.doc.operaciones if o.TIPO == "boceto"]


def prueba():
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(RUTA), ""))
    A.MODALES.clear()
    t0 = time.perf_counter()
    v.acciones["abrir"].trigger()                # Archivo › Abrir… → el diálogo devuelve BINCHA.f3d (abre en otro hilo
    segundos = time.perf_counter() - t0          # mientras la ventana sigue viva, y vuelve cuando terminó)
    A.esperar(600)
    A.reg(AR, "se abre en menos de un minuto (antes: 5 minutos)", 0 < segundos < 60, f"{segundos:.1f} s")
    A.reg(AR, "el aviso de espera fue diciendo la etapa", len(ETAPAS) >= 3 and any("Descomprimiendo" in e for e in ETAPAS),
          " › ".join(ETAPAS))
    bocetos = pasos_de_boceto()
    A.reg(AR, "el historial trae la importación y 10 pasos Boceto", len(v.doc.operaciones) == 11 and len(bocetos) == 10
          and v.doc.marcador == 11, f"{len(v.doc.operaciones)} pasos, marcador {v.doc.marcador}")
    nav = v.navegador
    en_navegador = [o.id for o in bocetos if nav.item(o.id) is not None]
    A.reg(AR, "los 10 bocetos están en la carpeta Bocetos del navegador", len(en_navegador) == 10
          and nav.item("__bocetos__") is not None, f"{len(en_navegador)} de 10")
    segmentos = len(v.visor._bocetos)
    A.reg(AR, "el visor dibuja los bocetos", segmentos > 1000, f"{segmentos} puntos de segmento")
    cuerpos = list(v.doc.estado_final.cuerpos.values())
    ocultos = set(v.doc.propiedad("__navegador__", "ocultos", []))
    A.reg(AR, "6 cuerpos: el sólido visible y 5 mallas ocultas", len(cuerpos) == 6 and len(ocultos) == 5
          and sum(1 for c in cuerpos if c.tipo == "solido" and c.id not in ocultos) == 1, f"{len(cuerpos)} cuerpos, "
          f"{len(ocultos)} ocultos")
    A.reg(AR, "el informe de apertura se mostró (mallas sin reparar)", any("sin reparar" in m[1] for m in A.MODALES),
          str(A.MODALES)[:200])
    A.foto(v, "f3d_abierto")

    # --- tocar un boceto como una persona
    b = bocetos[5]                                                       # el contorno de la bincha
    item = nav.item(b.id)
    nav.arbol.scrollToItem(item)
    A.esperar(150)
    caja = nav.arbol.visualItemRect(item)
    QTest.mouseClick(nav.arbol.viewport(), Qt.LeftButton, Qt.NoModifier, QPoint(caja.x() + 60, caja.center().y()))
    A.esperar(250)
    A.reg(AR, "un clic en el boceto del navegador lo elige", item.isSelected(), f"{b.nombre}")
    lista = v.timeline.lista                                             # editar un boceto: doble clic en su paso del timeline
    fila = next(lista.item(i) for i in range(lista.count()) if lista.item(i).data(Qt.UserRole) == b.id)
    lista.scrollToItem(fila)
    A.esperar(100)
    centro = lista.visualItemRect(fila).center()
    QTest.mouseClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, centro)
    A.esperar(60)
    QTest.mouseDClick(lista.viewport(), Qt.LeftButton, Qt.NoModifier, centro)
    A.esperar(700)
    A.reg(AR, "el doble clic en el paso del timeline abre el boceto para editarlo", v.modo_boceto.activo,
          f"modo boceto: {v.modo_boceto.activo}")
    A.foto(v, "f3d_boceto_editando")
    if v.modo_boceto.activo:
        v._salir_de_boceto()
        A.esperar(300)

    # --- guardar y reabrir
    carpeta = Path(tempfile.mkdtemp(prefix="omnicad_f3d_"))
    destino = carpeta / "bincha.omnicad"
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(destino), ""))
    v.acciones["guardar"].trigger()
    A.esperar(800)
    A.reg(AR, "se guarda como .omnicad", destino.is_file(), f"{destino.stat().st_size / 1e6:.1f} MB" if destino.is_file() else "")
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(destino), ""))
    v.doc.modificado = False
    v.acciones["abrir"].trigger()
    A.esperar(2500)
    A.reg(AR, "al reabrir siguen los 10 bocetos y los 5 ocultos", len(pasos_de_boceto()) == 10
          and len(v.doc.propiedad("__navegador__", "ocultos", [])) == 5, f"{len(pasos_de_boceto())} bocetos")
    A.foto(v, "f3d_reabierto")


if RUTA.is_file():
    n_err = len(A.ERRORES)
    A.correr(AR, prueba)
    A.reg(AR, "ninguna excepción escapada en slots de Qt", len(A.ERRORES) == n_err, "\n".join(A.ERRORES[n_err:])[-600:])
else:
    print(f"(falta {RUTA}: no hay nada que comprobar)")
A.guardar_registro("abrir_f3d")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.doc.modificado = False
v.close()
QApplication.processEvents()
sys.exit(0)
