"""Menús del navegador: las mismas acciones de ventana y herramientas públicas."""
from PySide6.QtWidgets import QInputDialog, QMenu

from .. import api
from ..api.herramientas_navegador import datos_navegador
from .navegador import ROL_CLAVE, ROL_TIPO


def elementos(v, clave):
    datos = datos_navegador(v.doc)
    if clave in datos["grupos"]:
        estado = v.doc.estado_final
        return [i for i in datos["grupos"][clave]["miembros"] if i in estado.cuerpos or i in estado.bocetos]
    elegidos = [it.data(0, ROL_CLAVE) for it in v.navegador.arbol.selectedItems()
                if it.data(0, ROL_TIPO) in ("cuerpo", "boceto")]
    return elegidos if clave in elegidos else [clave]


def llamar(v, herramienta, **args):
    r = api.llamar(api.Sesion(v.doc), herramienta, args)
    if not r["ok"]:
        v.mensaje(r["mensaje"], 10000)
    return r


def organizar(v, accion, clave, grupo=None):
    ids = elementos(v, clave)
    nombre = ""
    if accion in ("create_group", "create_set", "rename_group"):
        nombre, ok = QInputDialog.getText(v, "Navegador", "Nombre:")
        if not ok:
            return
    return llamar(v, "manage_browser", action=accion, items=ids if accion != "rename_group" else [],
                  name=nombre, group=grupo)


def mostrar(v, ids, visible):
    if ids:
        if visible:
            v.ocultos.difference_update(ids)
            v.vis["todo"] = v.vis["cuerpos"] = v.vis["bocetos"] = True
        else:
            v.ocultos.update(ids)
    else:
        v.ocultos.clear()
        v.vis.update({k: True for k in v.vis})
    v._refrescar_visibilidad()


def menu(v, item):
    clave, tipo = item.data(0, ROL_CLAVE), item.data(0, ROL_TIPO)
    ids = elementos(v, clave)
    m = QMenu(v.navegador)
    m.setToolTipsVisible(True)
    mover = m.addMenu("Desplazar al grupo")
    mover.addAction("Carpeta original", lambda: organizar(v, "move", clave))
    for gid, fila in datos_navegador(v.doc)["grupos"].items():
        mover.addAction(fila["nombre"], lambda _=False, g=gid: organizar(v, "move", clave, g))
    if tipo == "grupo":
        mover.setEnabled(False)
        mover.menuAction().setToolTip("Los grupos anidados todavía no están disponibles.")
    m.addSeparator()
    m.addAction("Nuevo grupo", lambda: organizar(v, "create_group", clave))
    conjunto = m.addAction("Crear conjunto de selección", lambda: organizar(v, "create_set", clave))
    conjunto.setEnabled(bool(ids))
    conjunto.setToolTip("Elegí al menos un cuerpo o boceto." if not ids else "Guarda y permite reutilizar esta selección.")
    m.addSeparator()
    prop = m.addAction("Propiedades", lambda: propiedades(v, ids))
    prop.setEnabled(bool(ids))
    prop.setToolTip("El grupo está vacío." if not ids else "Mide las propiedades de los elementos elegidos.")
    m.addSeparator()
    for texto in ("Copiar\tControl+C", "Cortar\tControl+X"):
        a = m.addAction(texto)
        a.setEnabled(False)
        a.setToolTip("El portapapeles de cuerpos con referencias paramétricas todavía no está implementado.")
    m.addAction("Suprimir\tSuprimir", lambda: suprimir(v, clave, tipo))
    m.addAction("Cambiar nombre", lambda: (organizar(v, "rename_group", clave, clave) if tipo == "grupo"
                                           else v.navegador.renombrar_en_linea(item)))
    m.addSeparator()
    ojo = m.addAction("Mostrar/ocultar\tV", lambda: mostrar(v, ids, any(i in v.ocultos for i in ids)))
    ojo.setEnabled(bool(ids))
    ojo.setToolTip("El grupo está vacío." if not ids else "Alterna la visibilidad de los elementos elegidos.")
    m.addAction("Mostrar todo", lambda: mostrar(v, [], True))
    return m


def propiedades(v, ids):
    cuerpos = [k for k in ids if k in v.doc.estado_final.cuerpos]
    if cuerpos:
        r = llamar(v, "get_physical_properties", bodies=cuerpos)
        if r["ok"]:
            total = r["result"]["total"]
            v.info_seleccion(f"{len(cuerpos)} cuerpo(s) | Volumen: {total['volume']:g} mm³ | "
                            f"Área: {total['area']:g} mm²")
    elif ids:
        v._propiedades(ids[0])


def suprimir(v, clave, tipo):
    if tipo == "grupo":
        return llamar(v, "manage_browser", action="delete_group", group=clave)
    v._seleccion_desde_navegador(elementos(v, clave))
    v.acciones["suprimir"].trigger()
