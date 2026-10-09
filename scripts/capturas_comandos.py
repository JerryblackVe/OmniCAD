# -*- coding: utf-8 -*-
"""
Capturas de los diálogos de comando estilo Fusion (Fase 3d) en evidencias/capturas/comandos/:
abre el modelo de ejemplo, ejecuta cada comando pedido con una selección hecha en la vista 3D y guarda
la ventana con el panel y la vista previa. Uso: python capturas_comandos.py [clave ...]
Usa preferencias en un .ini temporal (no toca la configuración real).
"""
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "clon"))

from PySide6.QtCore import QPoint, QSettings  # noqa: E402
from PySide6.QtGui import QSurfaceFormat  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton  # noqa: E402


def _arista_visible(v, cid, lineal=True):
    """Selección de una arista del cuerpo que se vea en pantalla (la más larga)."""
    import numpy as np
    from omnicad.nucleo import referencias as refs
    forma = v.doc.estado_final.cuerpos[cid].forma
    aristas = sorted(refs.subformas(forma, "arista"), key=lambda a: -refs.firma_arista(a)["largo"])
    for a in aristas:
        f = refs.firma_arista(a)
        if lineal and f["geom"] != "linea":
            continue
        q = v.visor.proyectar(np.array(f["medio"]))
        if q is None:
            continue
        hit = v.visor.elegir_entidad(q, {"arista"})
        if hit and hit["ref"]["firma"]["medio"] == f["medio"]:
            return hit
    return None


def _cara_visible(v, cid, normal=(0, 0, 1)):
    import numpy as np
    from omnicad.nucleo import referencias as refs
    forma = v.doc.estado_final.cuerpos[cid].forma
    for c in sorted(refs.subformas(forma, "cara"), key=lambda c: -refs.firma_cara(c)["area"]):
        f = refs.firma_cara(c)
        if "normal" in f and np.dot(f["normal"], normal) > 0.99:
            q = v.visor.proyectar(np.array(f["centro"]))
            hit = v.visor.elegir_entidad(q, {"cara"}) if q is not None else None
            if hit:
                return hit
    return None


def main():
    fmt = QSurfaceFormat()
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    fmt.setSamples(4)
    QSurfaceFormat.setDefaultFormat(fmt)
    _app = QApplication([])  # noqa: F841
    from omnicad.ejemplo import crear_documento_ejemplo
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    from omnicad.ui.comandos import CATALOGO

    destino = RAIZ / "evidencias" / "capturas" / "comandos"
    destino.mkdir(parents=True, exist_ok=True)
    temporal = Path(tempfile.mkdtemp(prefix="omnicad_cmd_"))
    prefs = Preferencias(QSettings(str(temporal / "prefs.ini"), QSettings.IniFormat))
    v = VentanaPrincipal(crear_documento_ejemplo(), prefs=prefs)
    v.resize(1900, 1000)
    v.show()
    QTest.qWait(600)
    v.visor.encuadrar()
    QTest.qWait(200)
    cid = next(iter(v.doc.estado_final.cuerpos))
    pedidos = sys.argv[1:] or ["empalme_3d", "chaflan_3d", "vaciado", "mover_copiar", "plano_medio", "extruir"]
    for clave in pedidos:
        panel = v.ejecutar_comando(CATALOGO[clave]())
        QTest.qWait(150)
        if panel is not None and panel.activa is not None:
            f = panel.activa.filtros
            hit = (_arista_visible(v, cid) if "arista" in f else _cara_visible(v, cid) if f & {"cara", "cara_plana"}
                   else None)
            if hit is not None:
                panel._elegida(hit)
            if clave == "plano_medio":
                hit2 = _cara_visible(v, cid, (0, 0, -1)) or _cara_visible(v, cid, (1, 0, 0))
                if hit2:
                    panel._elegida(hit2)
            QTest.qWait(700)
        v.grab().save(str(destino / f"{clave}.png"))
        if panel is not None:
            panel.cancelar()
        QTest.qWait(100)
    for titulo, archivo in (("MODIFICAR", "menu_modificar.png"), ("CONSTRUIR", "menu_construir.png")):
        fila = v.cinta.pila.widget(0)
        boton = next(b for b in fila.findChildren(QToolButton) if b.text().startswith(titulo) and b.menu())
        boton.menu().popup(boton.mapToGlobal(QPoint(0, boton.height())))
        QTest.qWait(250)
        boton.menu().grab().save(str(destino / archivo))
        boton.menu().hide()
    v.doc.modificado = False
    v.close()
    print("Capturas en", destino)


if __name__ == "__main__":
    main()
