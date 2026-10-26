"""Menús del navegador: las mismas acciones de ventana y herramientas públicas."""
from PySide6.QtWidgets import QInputDialog, QMenu

from .. import api
from ..api.herramientas_navegador import datos_navegador
from .iconos import icono
from .navegador import ROL_CLAVE, ROL_TIPO

CAPAS_BOCETO = {"profile": "perfil", "dimensions": "cotas", "projected": "proyectadas", "construction": "construccion",
                "grid": "rejilla", "snap": "forzar", "cut": "corte", "points": "puntos", "constraints": "restricciones"}
ICONOS_MENU = {
    "Desplazar al grupo": "carpeta",
    "Carpeta original": "carpeta",
    "Nuevo grupo": "carpeta",
    "Crear conjunto de selección": "seleccionar",
    "Mover/copiar": "mover_copiar",
    "Crear componentes a partir de cuerpos": "nuevo_componente",
    "Configurar": "configurar",
    "Activar conjuntos de contactos": "conjunto_contacto",
    "Material físico…": "material_fisico",
    "Material físico": "material_fisico",
    "Aspecto…": "aspecto",
    "Aspecto": "aspecto",
    "Controles de mapa de textura": "aspecto",
    "Eliminar anulación de aspecto": "aspecto",
    "Propiedades": "medir",
    "Guardar como malla": "exportar_malla",
    "Suprimir": "suprimir",
    "Quitar": "quitar",
    "Cambiar nombre": "texto",
    "Control de detalles de visualización": "visualizacion",
    "Mostrar/ocultar": "ojo",
    "Mostrar todo": "ojo",
    "Control de opacidad": "aspecto",
    "Seleccionable/no seleccionable": "seleccionar",
    "Aislar": "encuadre",
    "Desaislar": "ojo",
    "Buscar en la ventana": "buscar",
    "Buscar en la secuencia temporal": "buscar",
    "Añadir a ensamblaje": "insertar_componente",
    "Crear dibujo": "dibujo",
    "Grupo rígido": "grupo_rigido",
    "Exportar…": "exportar",
    "Guardar copia como": "guardar",
    "Mostrar en ubicación": "carpeta",
    "Historial": "secuencias",
    "Mostrar todos los componentes": "ojo",
    "Mostrar todos los cuerpos": "ojo",
    "Cambiar al modelado directo": "operacion_base",
    "Extruir": "extruir",
    "Plano de desfase": "plano_desfase",
    "Editar boceto": "boceto",
    "Redefinir el plano de boceto": "plano",
    "Seleccionar el plano de boceto": "plano",
    "Exportar DXF": "exportar",
    "Mirar a": "mirar_a",
    "Ocultar perfil": "ojo_no",
    "Mostrar cota": "cota",
    "Ocultar las geometrías proyectadas": "ojo_no",
    "Ocultar geometrías de construcción": "ojo_no",
    "Editar calcomanía": "calcomania",
    "Reemplazar archivo de imagen": "importar",
}


def con_iconos(menu):
    """Asigna los dibujos existentes por texto, también a los submenús, sin cambiar las acciones."""
    for accion in menu.actions():
        nombre = ICONOS_MENU.get(accion.text().split("\t")[0])
        if nombre:
            accion.setIcon(icono(nombre))
        if accion.menu() is not None:
            con_iconos(accion.menu())
    return menu


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
    if tipo == "raiz":
        return con_iconos(menu_raiz(v))
    if tipo == "boceto":
        return con_iconos(menu_boceto(v, item))
    if tipo == "calcomania":
        return con_iconos(menu_calcomania(v, item))
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
    if tipo == "cuerpo":
        m.addAction("Mover/copiar", lambda: v._accion_navegador("mover", clave))
        m.addAction("Crear componentes a partir de cuerpos", lambda: v._accion_navegador("nuevo_componente", clave))
        m.addAction("Configurar", v.acciones["configurar"].trigger)
        no_disponible(m, "Activar conjuntos de contactos")
        m.addAction("Material físico…", lambda: v._accion_navegador("material", clave))
        m.addAction("Aspecto…", lambda: v._accion_navegador("aspecto", clave))
        no_disponible(m, "Controles de mapa de textura")
        m.addAction("Eliminar anulación de aspecto", lambda: llamar(v, "set_appearance", bodies=ids))
    prop = m.addAction("Propiedades", lambda: propiedades(v, ids))
    prop.setEnabled(bool(ids))
    prop.setToolTip("El grupo está vacío." if not ids else "Mide las propiedades de los elementos elegidos.")
    m.addSeparator()
    if tipo == "cuerpo":
        m.addAction("Guardar como malla", lambda: v._accion_navegador("exportar_malla", clave))
        m.addSeparator()
    for texto in ("Copiar\tControl+C", "Cortar\tControl+X"):
        no_disponible(m, texto, "El portapapeles de cuerpos con referencias paramétricas todavía no está implementado.")
    m.addAction("Suprimir\tSuprimir", lambda: suprimir(v, clave, tipo))
    if tipo == "cuerpo":
        m.addAction("Quitar", lambda: v._accion_navegador("quitar", clave))
    m.addAction("Cambiar nombre", lambda: (organizar(v, "rename_group", clave, clave) if tipo == "grupo"
                                           else v.navegador.renombrar_en_linea(item)))
    m.addSeparator()
    if tipo == "cuerpo":
        no_disponible(m, "Control de detalles de visualización")
    ojo = m.addAction("Mostrar/ocultar\tV", lambda: mostrar(v, ids, any(i in v.ocultos for i in ids)))
    ojo.setEnabled(bool(ids))
    ojo.setToolTip("El grupo está vacío." if not ids else "Alterna la visibilidad de los elementos elegidos.")
    m.addAction("Mostrar todo", lambda: mostrar(v, [], True))
    if tipo == "cuerpo":
        menu_opacidad(v, m, clave)
        no_disponible(m, "Seleccionable/no seleccionable")
        m.addAction("Aislar", lambda: v._accion_navegador("aislar", clave))
        m.addAction("Desaislar", lambda: v._accion_navegador("desaislar", clave))
        m.addSeparator()
        m.addAction("Buscar en la ventana", lambda: v._accion_navegador("buscar_ventana", clave))
        m.addAction("Buscar en la secuencia temporal", lambda: v._accion_navegador("buscar_timeline", clave.split(".c")[0]))
    return con_iconos(m)


def no_disponible(m, texto, ayuda=""):
    a = m.addAction(texto)
    a.setEnabled(False)
    a.setToolTip("Todavía no disponible" + (f": {ayuda}" if ayuda else ""))


def menu_opacidad(v, m, clave):
    opacidad = m.addMenu("Control de opacidad")
    opacidad.setEnabled(bool(v.doc.estado_final.cuerpos))
    for pct in (100, 70, 50, 30, 10):
        opacidad.addAction(f"{pct} %", lambda _=False, p=pct: v._accion_navegador(f"opacidad:{p}", clave))


def menu_raiz(v):
    m = QMenu(v.navegador)
    m.setToolTipsVisible(True)
    no_disponible(m, "Añadir a ensamblaje")
    m.addAction("Crear dibujo", v.acciones["nuevo_dibujo"].trigger)
    m.addAction("Configurar", v.acciones["configurar"].trigger)
    m.addAction("Grupo rígido", v.acciones["grupo_rigido"].trigger)
    no_disponible(m, "Activar conjuntos de contactos")
    m.addSeparator()
    for texto, clave in (("Material físico", "material"), ("Aspecto", "aspecto")):
        a = m.addAction(texto, lambda _=False, c=clave: v._accion_navegador(c, "__raiz__"))
        a.setEnabled(bool(v.doc.estado_final.cuerpos))
    no_disponible(m, "Controles de mapa de textura")
    prop = m.addAction("Propiedades", lambda: propiedades(v, list(v.doc.estado_final.cuerpos)))
    prop.setEnabled(bool(v.doc.estado_final.cuerpos))
    m.addSeparator()
    no_disponible(m, "Solo lectura para mí")
    m.addAction("Exportar…", lambda: v._accion_navegador("exportar", "__raiz__"))
    no_disponible(m, "Guardar copia como")
    m.addAction("Guardar como malla", lambda: v._accion_navegador("exportar_malla", "__raiz__"))
    no_disponible(m, "Mostrar en ubicación")
    no_disponible(m, "Historial")
    m.addSeparator()
    no_disponible(m, "Control de detalles de visualización")
    for texto, ids in (("Mostrar todos los componentes", list(v.doc.estado_final.componentes)),
                       ("Mostrar todos los cuerpos", list(v.doc.estado_final.cuerpos))):
        a = m.addAction(texto, lambda _=False, elegidos=ids: mostrar(v, elegidos, True))
        a.setEnabled(bool(ids))
    menu_opacidad(v, m, "__raiz__")
    m.addSeparator()
    buscar = m.addAction("Buscar en la ventana", lambda: v._accion_navegador("buscar_ventana", "__raiz__"))
    buscar.setEnabled(bool(v.doc.estado_final.cuerpos))
    m.addSeparator()
    no_disponible(m, "Cambiar al modelado directo")
    return m


def buscar_en_ventana(v, ids):
    """Fusion › Find in Window: selecciona, encuadra y resalta el paso creador."""
    import numpy as np
    v.seleccionar_cuerpos(ids)
    puntos = [p[1] for h in v.seleccion for p in h["dibujo"] if len(p[1])]
    if puntos:
        v.visor.encuadrar(np.concatenate(puntos))
    if ids:
        v.timeline.resaltar(v.doc.estado_final.cuerpos[ids[-1]].op_id)
    return {"bodies": ids}


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
    elif accion in ("finish", "finish_with_auto_constrain"):
        mb = v.modo_boceto
        if not mb.activo or getattr(mb.datos.get("op"), "id", None) != clave:
            raise error("INVALID_ARGUMENTS", "Terminar solo se puede mientras se edita el boceto elegido.")
        r = mb.lienzo.resultado
        if r is not None and not r.ok:         # la ventana preguntaría «¿Terminar igual?»: un agente no contesta diálogos
            raise error("OPERATION_FAILED", "El boceto tiene restricciones en conflicto: resolvelas antes de terminarlo.")
        if accion == "finish":
            mb.terminar()
        else:
            _terminado, agregado = mb.terminar_con_autorestringir()
            return {"sketch": clave, "action": accion, "added": [s.descripcion for s in agregado]}
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
