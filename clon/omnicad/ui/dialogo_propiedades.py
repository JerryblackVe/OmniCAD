"""Diálogo «Propiedades» (clic derecho › Propiedades de Fusion): datos y medidas físicas de un cuerpo o componente."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout

from .. import api
from . import formato

N = formato.numero


def filas(r):
    """Filas (etiqueta, valor) de un resultado de `get_properties`, con las unidades del documento."""
    f = r["physical"]["total"]
    u, u2, u3 = formato.sufijo(), formato.sufijo(2), formato.sufijo(3)
    punto = lambda p: " ; ".join(N(formato.longitud(x)) for x in p) + f" {u}"  # noqa: E731
    datos = [("Nombre", r["name"])]
    if r["kind"] == "body":
        datos += [("Componente", r["component"] or "(raíz)"), ("Material físico", r["material"] or "(ninguno)")]
    else:
        datos += [("Ruta", r["path"]), ("Fijo", "sí" if r["grounded"] else "no"), ("Cuerpos", str(r["bodies_count"]))]
    datos += [("Masa", f"{N(formato.masa(f['mass_g']))} {formato.unidad_masa()}" if f["mass_g"] is not None
               else "(sin densidad: asigná un material físico)"),
              ("Volumen", f"{N(formato.longitud(f['volume'], 3), miles=True)} {u3}"),
              ("Área", f"{N(formato.longitud(f['area'], 2), miles=True)} {u2}")]
    if f["center_of_mass"]:
        datos.append(("Centro de masa", punto(f["center_of_mass"])))
    if f["bounding_box"]:
        datos.append(("Caja envolvente", " × ".join(N(formato.longitud(x)) for x in f["bounding_box"]["size"]) + f" {u}"))
    return datos


def abrir(v, item):
    """Abre el diálogo para un cuerpo o componente (id); sin cuerpos o con error, lo dice en la barra."""
    r = api.llamar(api.Sesion(v.doc), "get_properties", {"item": item})
    if not r["ok"]:
        v.mensaje(f"Propiedades: {r['mensaje']}", 6000)
        return None
    datos = filas(r["result"])
    d = QDialog(v)
    d.setWindowTitle(f"Propiedades — {r['result']['name']}")
    d.setObjectName("dialogo_propiedades")
    t = QTableWidget(len(datos), 2, d)
    t.setHorizontalHeaderLabels(["Propiedad", "Valor"])
    t.verticalHeader().hide()
    t.setEditTriggers(QTableWidget.NoEditTriggers)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    t.horizontalHeader().setStretchLastSection(True)
    for i, (k, valor) in enumerate(datos):
        t.setItem(i, 0, QTableWidgetItem(k))
        t.setItem(i, 1, QTableWidgetItem(valor))
    botones = QDialogButtonBox(QDialogButtonBox.Close, d)
    botones.rejected.connect(d.close)
    lay = QVBoxLayout(d)
    lay.addWidget(t)
    lay.addWidget(botones)
    d.resize(460, 120 + 30 * len(datos))
    d.setAttribute(Qt.WA_DeleteOnClose)
    v._dialogo_propiedades = d
    d.show()
    return d
