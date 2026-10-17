"""Menús del navegador: las mismas acciones de ventana y herramientas públicas."""
from PySide6.QtWidgets import QInputDialog, QMenu

from .. import api
from ..api.herramientas_navegador import datos_navegador
from .navegador import ROL_CLAVE, ROL_TIPO

CAPAS_BOCETO = {"profile": "perfil", "dimensions": "cotas", "projected": "proyectadas", "construction": "construccion"}


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
            v.vis["todo"] = v.vis["cuerpos"] = v.vis["bocetos"] = v.vis["calcomanias"] = True
        else:
            v.ocultos.update(ids)
    else:
        v.ocultos.clear()
        v.vis.update({k: True for k in v.vis})
    v._refrescar_visibilidad()


def menu(v, item):
    clave, tipo = item.data(0, ROL_CLAVE), item.data(0, ROL_TIPO)
    if tipo == "boceto":
        return menu_boceto(v, item)
    if tipo == "calcomania":
        return menu_calcomania(v, item)
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


def plano_boceto(v, clave):
    import numpy as np
    br = v.doc.estado_final.bocetos[clave]
    pl = br.plano
    esquinas = [pl.a_3d(x, y) for x, y in ((-20, -20), (20, -20), (20, 20), (-20, 20))]
    return {"tipo": "plano", "ref": {"tipo": "boceto", "boceto": clave}, "plano": pl,
            "dibujo": [("tris", np.array([esquinas[i] for i in (0, 1, 2, 0, 2, 3)]), None, 0.3)]}


def vista_boceto(v, clave, accion, visible=None):
    import numpy as np
    from ..api.errores import error
    br = v.doc.estado_final.bocetos[clave]
    if accion == "edit":
        v.editar_operacion(clave)
    elif accion == "select_plane":
        v._seleccionar([plano_boceto(v, clave)])
    elif accion == "look_at":
        v.visor.mirar_a_plano(br.plano)
    elif accion == "find_in_window":
        from .visor3d import polilineas_boceto
        curvas = polilineas_boceto(br)
        v.visor.encuadrar(np.concatenate(curvas) if curvas else np.array([br.plano.origen]))
    elif accion == "find_in_timeline":
        v.acciones["ver_timeline"].setChecked(True)
        v.timeline.show()
        v.timeline.resaltar(clave)
    elif accion in CAPAS_BOCETO:
        mb = v.modo_boceto
        if not mb.activo or getattr(mb.datos.get("op"), "id", None) != clave:
            raise error("INVALID_ARGUMENTS", "Esta capa solo está disponible al editar el boceto elegido.")
        control = mb.paleta.checks[CAPAS_BOCETO[accion]]
        control.setChecked(not control.isChecked() if visible is None else visible)
        return {"sketch": clave, "action": accion, "visible": control.isChecked()}
    return {"sketch": clave, "action": accion}


def extruir_boceto(v, clave):
    from ..timeline.operaciones import OpExtrusion
    from .comando import hit_desde_ref
    br = v.doc.estado_final.bocetos[clave]
    v._seleccionar([hit_desde_ref({"tipo": "perfil", "boceto": clave, **OpExtrusion.referencia_perfil(p)},
                                  v.doc.estado_final) for p in br.perfiles])
    v.acciones["extruir"].trigger()


def desfase_boceto(v, clave):
    v._seleccionar([plano_boceto(v, clave)])
    v.acciones["plano_desfase"].trigger()


def menu_boceto(v, item):
    clave = item.data(0, ROL_CLAVE)
    br = v.doc.estado_final.bocetos[clave]
    m = QMenu(v.navegador)
    m.setToolTipsVisible(True)
    grupos = m.addMenu("Desplazar al grupo")
    grupos.addAction("Carpeta original", lambda: organizar(v, "move", clave))
    for gid, fila in datos_navegador(v.doc)["grupos"].items():
        grupos.addAction(fila["nombre"], lambda _=False, g=gid: organizar(v, "move", clave, g))
    m.addAction("Crear conjunto de selección", lambda: organizar(v, "create_set", clave))
    extruir = m.addAction("Extruir\tE", lambda: extruir_boceto(v, clave))
    extruir.setEnabled(bool(br.perfiles))
    extruir.setToolTip("El boceto no tiene perfiles cerrados." if not br.perfiles else "Extruye los perfiles del boceto.")
    m.addAction("Plano de desfase", lambda: desfase_boceto(v, clave))
    m.addSeparator()
    m.addAction("Editar boceto", lambda: vista_boceto(v, clave, "edit"))
    m.addAction("Redefinir el plano de boceto", lambda: v._elegir_plano(f"redefinir:{clave}",
                "Seleccione el nuevo plano del boceto   (Esc: cancelar)"))
    m.addAction("Seleccionar el plano de boceto", lambda: vista_boceto(v, clave, "select_plane"))
    m.addAction("Configurar", v.acciones["configurar"].trigger)
    m.addSeparator()
    m.addAction("Exportar DXF", lambda: v.guardar_boceto_dxf(clave))
    borrar = m.addAction("Suprimir\tSuprimir", lambda: v._accion_navegador("borrar_paso", clave))
    dependientes = any(clave in op.dependencias() for op in v.doc.operaciones if op.id != clave)
    borrar.setEnabled(not dependientes)
    borrar.setToolTip("Otro paso usa este boceto; eliminá sus dependencias primero." if dependientes else "Suprime el boceto.")
    m.addAction("Cambiar nombre", lambda: v.navegador.renombrar_en_linea(item))
    m.addSeparator()
    m.addAction("Mirar a", lambda: vista_boceto(v, clave, "look_at"))
    m.addSeparator()
    mb = v.modo_boceto
    editando = mb.activo and getattr(mb.datos.get("op"), "id", None) == clave
    for texto, opcion in (("Ocultar perfil", "profile"), ("Mostrar cota", "dimensions"),
                           ("Ocultar las geometrías proyectadas", "projected"),
                           ("Ocultar geometrías de construcción", "construction")):
        a = m.addAction(texto, lambda _=False, k=opcion: vista_boceto(v, clave, k, k == "dimensions"))
        a.setEnabled(editando)
        a.setToolTip("Disponible al editar este boceto; el visor general todavía no dibuja todas sus capas."
                     if not editando else "Cambia la misma opción de la paleta de boceto.")
    m.addAction("Mostrar/ocultar\tV", lambda: mostrar(v, [clave], clave in v.ocultos))
    m.addSeparator()
    m.addAction("Buscar en la ventana", lambda: vista_boceto(v, clave, "find_in_window"))
    m.addAction("Buscar en la secuencia temporal", lambda: vista_boceto(v, clave, "find_in_timeline"))
    return m


def vista_calcomania(v, clave, accion, imagen=None):
    """Lo que hace el menú de una calcomanía del navegador (y la herramienta `decal_view`): editar (reabre su panel
    con sus valores), encuadrarla en la ventana, encontrarla en la secuencia temporal o cambiar su imagen."""
    import numpy as np

    from ..api.errores import error
    from ..timeline.ops_insertar import calcomanias_vigentes
    if accion == "edit":
        v.editar_operacion(clave)
    elif accion == "find_in_window":
        datos = dict(calcomanias_vigentes(v.doc, v.doc.estado_final)).get(clave)
        if datos is None:
            raise error("INVALID_ARGUMENTS", "La calcomanía no está sobre un cuerpo visible en este punto del timeline.")
        malla = datos.get("malla")
        puntos = np.asarray(malla["vertices"], float) if malla is not None else np.array(v.visor.esquinas_lienzo(datos))
        v.visor.encuadrar(puntos)
    elif accion == "find_in_timeline":
        v.acciones["ver_timeline"].setChecked(True)
        v.timeline.show()
        v.timeline.resaltar(clave)
    elif accion == "replace_image":
        if imagen is None:
            from PySide6.QtWidgets import QFileDialog
            imagen, _ = QFileDialog.getOpenFileName(v, "Reemplazar archivo de imagen", "",
                                                    "Imágenes (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
            if not imagen:
                return {"decal": clave, "action": accion}
        r = llamar(v, "set_decal", image=imagen, feature=clave)
        if not r["ok"]:
            raise error("OPERATION_FAILED", r["mensaje"])
    return {"decal": clave, "action": accion}


def menu_calcomania(v, item):
    """Menú de la calcomanía en el navegador, con las opciones de Fusion."""
    clave = item.data(0, ROL_CLAVE)
    m = QMenu(v.navegador)
    m.setToolTipsVisible(True)
    m.addAction("Crear conjunto de selección", lambda: organizar(v, "create_set", clave))
    m.addSeparator()
    editar = m.addAction("Editar calcomanía", lambda: vista_calcomania(v, clave, "edit"))
    editar.setToolTip("Reabre el panel de la calcomanía con sus valores.")
    m.addAction("Reemplazar archivo de imagen", lambda: vista_calcomania(v, clave, "replace_image"))
    m.addSeparator()
    m.addAction("Suprimir\tSuprimir", lambda: v._accion_navegador("borrar_paso", clave))
    m.addAction("Cambiar nombre", lambda: v.navegador.renombrar_en_linea(item))
    m.addAction("Mostrar/ocultar\tV", lambda: mostrar(v, [clave], clave in v.ocultos))
    m.addSeparator()
    m.addAction("Buscar en la ventana", lambda: vista_calcomania(v, clave, "find_in_window"))
    m.addAction("Buscar en la secuencia temporal", lambda: vista_calcomania(v, clave, "find_in_timeline"))
    return m
