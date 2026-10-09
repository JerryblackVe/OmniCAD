# -*- coding: utf-8 -*-
"""
Prueba de humo de la aplicación completa CON interfaz (sin intervención humana).

Abre la ventana real, carga el ejemplo y prueba la interfaz estilo Fusion: cinta, navegador, ViewCube,
barra de navegación (estilos, entornos, efectos, cámara, órbita, vistas múltiples), timeline,
preferencias y panel de datos. Crea un boceto DENTRO de la vista 3D como en Fusion (elegir el plano
con un clic, dibujar con clics simulados, cota con la entrada en pantalla, entrada dinámica, arco
tangente arrastrando, terminar), lo extruye, cambia un parámetro, edita el boceto (vista retrocedida),
mueve el marcador, guarda, exporta STL/OBJ/STEP, vuelve a abrir y comprueba que el visor dibuja.
Las preferencias van a un .ini temporal: la prueba no toca la configuración del usuario.
Devuelve 0 si todo pasa. Uso:  python OmniCAD.py --prueba-humo
"""
import tempfile
from pathlib import Path

from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from .io_archivos import exportar as ex
from .io_archivos import proyecto
from .nucleo import geometria as geo
from .timeline.operaciones import OpBoceto, OpExtrusion, OpPlano
from .ui.panel_timeline import MARCADOR
from .ui.preferencias import DialogoPreferencias, Preferencias
from .ui.ventana import VentanaPrincipal


class _Registro:
    def __init__(self):
        self.fallas = 0

    def check(self, condicion, texto):
        print(("OK    " if condicion else "FALLA ") + texto, flush=True)
        if not condicion:
            self.fallas += 1


def _colores_distintos(img, paso=7):
    vistos = set()
    for x in range(0, img.width(), paso):
        for y in range(0, img.height(), paso):
            vistos.add(img.pixel(x, y))
    return len(vistos)


def _interfaz(v, r):
    cinta = v.cinta
    r.check([b.text() for b in cinta.pestanas] == ["SÓLIDO", "SUPERFICIE", "MALLA", "CHAPA", "PLÁSTICO", "ADMINISTRAR",
                                                   "UTILIDADES"], "Cinta: las 7 pestañas de Fusion")
    r.check(all(not a.isEnabled() for a in cinta.no_disponibles), "Cinta: lo no implementado aparece grisado (sin botones muertos)")
    menu_crear = cinta.pila.widget(0).findChildren(__import__("PySide6.QtWidgets", fromlist=["QMenu"]).QMenu)[0]
    activos = [a.text().split("	")[0] for a in menu_crear.actions() if a.isEnabled() and a.text() and a.menu() is None]
    reales = {a.text().split("	")[0] for a in v.acciones.values()}
    r.check({"Crear boceto", "Extruir", "Revolución", "Prisma rectangular"} <= set(activos) <= reales,
            f"CREAR ▾ habilita solo comandos reales: {activos}")
    for i in range(len(cinta.pestanas)):
        cinta.pestanas[i].click()
    r.check(cinta.pestana_actual() == "UTILIDADES", "Las pestañas cambian el contenido de la cinta")
    cinta.pestanas[0].click()

    # Navegador: ojo de un cuerpo y de la carpeta Origen
    nav, cuerpo = v.navegador, next(iter(v.doc.estado_final.cuerpos))
    r.check(nav.item(cuerpo) is not None and nav.item("__origen__") is not None, "Navegador: cuerpos, bocetos y origen")
    antes = len(v.visor._mallas)
    nav.ojo.emit(cuerpo)
    r.check(len(v.visor._mallas) == antes - 1, "Navegador: el ojo oculta el cuerpo en el visor")
    nav.ojo.emit(cuerpo)
    nav.ojo.emit("__origen__")
    r.check(v.visor.config.origen.get("xy") and nav.item("__xy__") is not None,
            "Navegador: el ojo de Origen muestra O, X, Y, Z, XY, XZ, YZ")
    nav.ojo.emit("__xy__")
    r.check(not v.visor.config.origen.get("xy") and v.visor.config.origen.get("xz"),
            "Navegador: cada elemento del origen tiene su propio ojo")
    nav.ojo.emit("__xy__")
    nav.ojo.emit("__origen__")

    # ViewCube: clic en la cara SUPERIOR
    QTest.qWait(50)
    cubo = v.area.viewcube
    cubo.repaint()
    cara = next(((poli, vista) for poli, vista in cubo._poligonos if vista == "arriba"), None)
    if cara:
        c = cara[0].boundingRect().center()
        QTest.mouseClick(cubo, Qt.LeftButton, Qt.NoModifier, QPoint(int(c.x()), int(c.y())))
    r.check(cara is not None and v.visor.elevacion > 89, "ViewCube: clic en SUPERIOR pone la vista de arriba")
    QTest.mouseClick(cubo, Qt.LeftButton, Qt.NoModifier, QPoint(cubo.width() - 8, 8))
    r.check(abs(v.visor.elevacion - 35.264) < 0.01, "ViewCube: la casita vuelve a la vista inicial")

    # Barra de navegación: modo órbita con el botón izquierdo y Esc para salir
    v.barra_nav.modos["encuadre"].trigger()
    objetivo = v.visor.objetivo.copy()
    centro = v.visor.rect().center()
    QTest.mousePress(v.visor, Qt.LeftButton, Qt.NoModifier, centro)
    QTest.mouseMove(v.visor, centro + QPoint(40, 0))
    QTest.mouseRelease(v.visor, Qt.LeftButton, Qt.NoModifier, centro + QPoint(40, 0))
    r.check(v.visor.modo == "encuadre" and (v.visor.objetivo != objetivo).any(), "Barra de navegación: modo encuadre")
    QTest.keyClick(v.visor, Qt.Key_Escape)
    r.check(v.visor.modo is None and not v.barra_nav.modos["encuadre"].isChecked(), "Esc sale del modo y destilda el botón")
    for estilo in ("sombreado", "sombreado_ocultas", "alambrico", "alambrico_ocultas", "alambrico_visibles"):
        v.barra_nav.estilos[estilo].trigger()
        QTest.qWait(30)
        r.check(v.visor.config.estilo_visual == estilo and _colores_distintos(v.visor.grabFramebuffer()) > 20,
                f"Estilo visual «{estilo}» dibuja")
    v.barra_nav.estilos["sombreado_aristas"].trigger()
    v.cambiar_vista("entorno", "cielo_oscuro")
    r.check(v.visor.config.entorno == "cielo_oscuro" and v.prefs["vista/entorno"] == "cielo_oscuro",
            "Entorno «Cielo oscuro» (se guarda en las preferencias)")
    v.cambiar_vista("entorno", "tema")
    v.cambiar_vista("preset", "calidad")
    ef = v.visor.config.efectos
    QTest.qWait(30)
    r.check(ef["suelo"] and ef["sombra_suelo"] and ef["aa"] and _colores_distintos(v.visor.grabFramebuffer()) > 50,
            "Valor predefinido «Calidad»: plano y sombra en el suelo, anti-aliasing")
    v.cambiar_vista("preset", "rendimiento")
    r.check(not v.visor.config.efectos["aa"] and not v.visor.config.efectos["suelo"], "«Rendimiento» apaga los efectos")
    v.cambiar_vista("efecto:aa", True)
    r.check(v.prefs["graficos/preset"] == "personalizar", "Tocar un efecto pasa el valor predefinido a «Personalizar»")
    v.cambiar_vista("efecto:reflejo", True)
    QTest.qWait(30)
    r.check(_colores_distintos(v.visor.grabFramebuffer()) > 50, "Reflejo en el suelo dibuja")
    v.cambiar_vista("efecto:reflejo", False)

    # Cámara: perspectiva con caras ortográficas, órbita libre y restringida
    v.cambiar_vista("camara", "persp_orto_caras")
    v.visor.vista("frente")
    orto_cara = v.visor.ortografica
    v.visor.orbitar(30, 10)
    r.check(orto_cara and not v.visor.ortografica, "Perspectiva con caras ortográficas: orto de frente, perspectiva al orbitar")
    v.cambiar_vista("camara", "perspectiva")
    v.cambiar_vista("tipo_orbita", "restringida")
    v.visor.vista("iso")
    v.visor.orbitar(80, 60)
    r.check(abs(v.visor.R[0][2]) < 1e-9, "Órbita restringida: la vista nunca se inclina")
    v.cambiar_vista("tipo_orbita", "libre")
    v.visor.orbitar(80, 60)
    r.check(abs(float(v.visor.R[0] @ v.visor.R[1])) < 1e-9 and abs(v.visor.R[0][2]) > 1e-6,
            "Órbita libre: la vista puede inclinarse y el marco de la cámara sigue ortonormal")
    v.visor.vista("iso")

    # Vistas múltiples
    v.cambiar_vista("vistas_multiples", True)
    QTest.qWait(150)
    extras = v.area.extras
    r.check(v.area.multiples and len(extras) == 3 and all(e.isVisible() and e.ortografica for e in extras),
            "Vistas múltiples: superior, frontal y derecha (ortográficas) + la principal")
    r.check(all(_colores_distintos(e.grabFramebuffer()) > 20 for e in extras), "Las 4 vistas dibujan el modelo")
    v.cambiar_vista("vistas_multiples", False)

    # Vistas guardadas
    v.doc.vistas["Prueba"] = {"objetivo": [1.0, 2.0, 3.0], "distancia": 77.0, "R": v.visor.R.tolist(), "camara": "perspectiva"}
    v._actualizar()
    v.navegador.vista_ir.emit("Prueba")
    r.check(nav.item("vista:Prueba") is not None and abs(v.visor.distancia - 77.0) < 1e-9,
            "Vistas guardadas: aparece en el navegador y restaura la cámara")
    v._vista_borrar("Prueba")
    v.visor.encuadrar()

    # Timeline: soltar el marcador después del 2.º paso
    filas = v.timeline.claves()
    v.timeline._soltado(MARCADOR, filas.index(v.doc.operaciones[2].id))
    r.check(v.doc.marcador == 2, f"Timeline: arrastrar el marcador lo lleva al paso 2 ({v.doc.marcador})")
    v.doc.mover_marcador(len(v.doc.operaciones))

    # Preferencias: cambiar el aspecto de los cuerpos, aplicar y restablecer
    dlg = DialogoPreferencias(v.prefs, v)
    dlg.aplicado.connect(v.aplicar_preferencias)
    combo = dlg.controles["material/aspecto"]
    combo.setCurrentIndex(combo.findData("paleta"))
    dlg.b_aplicar.click()
    r.check(v.visor.config.aspecto == "paleta" and v.prefs["material/aspecto"] == "paleta",
            "Preferencias: Aplicar cambia el aspecto de los cuerpos")
    dlg.b_restablecer.click()
    r.check(v.visor.config.aspecto == "acero", "Preferencias: Restablecer vuelve a los valores por defecto")
    dlg.reject()


def _punto_del_plano(visor, nombre):
    """Un punto de pantalla donde el clic elige el plano de origen pedido (sin otro plano delante)."""
    L = visor._tam_planos()
    for fu in (0.5, 0.75, 0.9, 0.25, 0.1):
        for fv in (0.5, 0.75, 0.9, 0.25, 0.1):
            q = visor.proyectar(visor.planos_elegibles()[("XY", "XZ", "YZ").index(nombre)][1].a_3d(L * fu, L * fv))
            if q is not None:
                hit = visor.elegir(q)
                if hit and hit["ref"] == nombre:
                    return q.toPoint()
    return None


def _clic(lz, u, v):
    QTest.mouseMove(lz, lz.a_px(u, v).toPoint())
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, lz.a_px(u, v).toPoint())


def _boceto_en_3d(v, r):
    v.crear_boceto()
    r.check(v.visor.modo == "elegir_plano" and v.area.aviso.isVisible(),
            "Crear boceto pide elegir un plano o una cara plana (planos de origen visibles)")
    q = _punto_del_plano(v.visor, "XY")
    QTest.mouseClick(v.visor, Qt.LeftButton, Qt.NoModifier, q)
    QTest.qWait(150)
    mb = v.modo_boceto
    r.check(mb.activo and v.cinta.pestana_actual() == "BOCETO" and mb.paleta.isVisible() and mb.lienzo.isVisible(),
            "Clic en el plano XY: entra al boceto (pestaña BOCETO, paleta y lienzo sobre la vista 3D)")
    r.check(abs(float(v.visor.R[2] @ (0, 0, 1)) - 1) < 1e-9, "La cámara mira el plano del boceto («Mirar a» automático)")
    lz = mb.lienzo
    v.acciones["sk_rectangulo"].trigger()
    r.check(lz.herramienta == "rectangulo", "La cinta BOCETO elige la herramienta (Rectángulo de 2 puntos, R)")
    _clic(lz, 0, 0)
    _clic(lz, 30, 20)
    lineas = [c for c in lz.b.curvas.values() if c.tipo == "linea"]
    origen = [rr for rr in lz.b.restricciones.values() if rr.datos.get("origen")]
    r.check(len(lineas) == 4 and len(lz.b.restricciones) == 5 and len(origen) == 1,
            f"Rectángulo dibujado con el ratón EN LA VISTA 3D: 4 líneas + 2 H + 2 V + esquina pegada al origen "
            f"({len(lineas)})")
    mb.herramienta("circulo")
    _clic(lz, 15, 10)
    _clic(lz, 19, 10)
    r.check(any(c.tipo == "circulo" for c in lz.b.curvas.values()), "Círculo de centro y diámetro")
    abajo = min(lineas, key=lambda c: sum(lz.b.coords(p)[1] for p in c.puntos()))
    mb.herramienta("cota")
    _clic(lz, 15, 0)
    _clic(lz, 15, -8)
    r.check(lz.entrada is not None, "Cota de boceto (D): clic en la línea y clic para ubicar abre la entrada en pantalla")
    lz.entrada.campos[0].setText("ancho")
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    r.check(abs(lz.b.medir_cota("distancia", [abajo.id]) - 60) < 1e-6,
            "La cota con el parámetro «ancho» lleva la línea a 60 mm")
    derecha = max(lineas, key=lambda c: sum(lz.b.coords(p)[0] for p in c.puntos()))
    antes = len(lz.b.restricciones)
    ok = lz.aplicar_cambio(lambda: lz.b.agregar_restriccion("horizontal", [derecha.id]))
    r.check(not ok and len(lz.b.restricciones) == antes, "Una restricción en conflicto se rechaza y se deshace")
    # Entrada dinámica: escribir la longitud mientras se dibuja una línea
    mb.herramienta("linea")
    _clic(lz, 0, -40)
    QTest.mouseMove(lz, lz.a_px(20, -40).toPoint())
    QTest.keyClick(lz, Qt.Key_2)
    r.check(lz.entrada is not None, "Entrada dinámica: escribir un número abre el campo de longitud")
    lz.entrada.campos[0].setText("25")
    QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    nueva = max(lz.b.curvas)
    r.check(lz.b.tipo_de(nueva) == "linea" and abs(lz.b.medir_cota("distancia", [nueva]) - 25) < 1e-6
            and any(c.expresion == "25" for c in lz.b.cotas.values()),
            "…crea la línea de 25 mm con su cota (como Fusion)")
    # Arco tangente arrastrando desde el último punto
    fin = lz.b.curvas[nueva].p2
    p_fin = lz.a_px(*lz.b.coords(fin)).toPoint()
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, p_fin)
    QTest.mouseMove(lz, lz.a_px(35, -30).toPoint())
    QTest.mouseMove(lz, lz.a_px(40, -25).toPoint())
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, lz.a_px(40, -25).toPoint())
    arcos = [c for c in lz.b.curvas.values() if c.tipo == "arco"]
    tangente = any(rr.tipo == "tangente" and nueva in rr.entidades for rr in lz.b.restricciones.values())
    r.check(len(arcos) == 1 and tangente, "Arrastrar desde el final de la línea crea un arco tangente")
    QTest.keyClick(lz, Qt.Key_Escape)
    for _ in range(2):                          # se deshacen el arco y la línea con su cota (quedan fuera del perfil)
        lz.deshacer()
    r.check(not any(c.tipo == "arco" for c in lz.b.curvas.values()), "Ctrl+Z dentro del boceto deshace")
    deter = lz.resultado.determinadas
    arriba = max(lineas, key=lambda c: sum(lz.b.coords(p)[1] for p in c.puntos()))
    r.check(arriba.id not in deter and abajo.id in deter,
            "Colores: lo libre queda azul y lo determinado (pegado al origen + cota) cambia de color")
    mb.terminar()
    QTest.qWait(100)
    sk = v.doc.operaciones[-1]
    r.check(not mb.activo and isinstance(sk, OpBoceto) and sk.p["plano"] == "XY" and v.cinta.pestana_actual() == "SÓLIDO",
            "Terminar boceto: guarda el paso en el timeline y vuelve a SÓLIDO")
    return sk


def _editar_boceto(v, r, sk):
    indice = v.doc.indice(sk.id)
    v.navegador.editar.emit(sk.id)
    QTest.qWait(100)
    previo = v.doc.estado_en(indice)
    r.check(v.modo_boceto.activo and len(v.visor._mallas) == len(previo.cuerpos),
            "Editar boceto: el modelo se ve como estaba en ese paso (lo posterior se oculta)")
    v.modo_boceto.terminar()
    r.check(all(x.estado == "ok" for x in v.doc.resultados), "Al terminar la edición todo se recalcula OK")


def _fase3d(v, r):
    """Comandos estilo Fusion de la fase 3d en la ventana real: preselección + diálogo, selección por
    ventana, análisis, ensamblaje y espacio DIBUJO."""
    import numpy as np

    from .nucleo import referencias as refs
    estado = v.doc.estado_final
    cid = next(c for c, cu in estado.cuerpos.items() if cu.tipo == "solido")
    forma = estado.cuerpos[cid].forma
    v.visor.vista("iso")
    v.visor.encuadrar()
    QTest.qWait(150)
    hit = None
    for a in sorted(refs.subformas(forma, "arista"), key=lambda a: -refs.firma_arista(a)["largo"]):
        f = refs.firma_arista(a)
        q = v.visor.proyectar(np.array(f["medio"])) if f["geom"] == "linea" else None
        h = v.visor.elegir_entidad(q, {"arista"}) if q is not None else None
        if h is not None and h["ref"]["firma"]["medio"] == f["medio"]:
            hit = h
            break
    r.check(hit is not None, "Elegir una arista con el ratón en la vista 3D")
    v._clic_en_vista(hit)
    r.check(len(v.seleccion) == 1, "Clic sin comando: la arista queda preseleccionada")
    v.acciones["empalme_3d"].trigger()
    QTest.qWait(400)
    panel = v.panel
    r.check(panel is not None and len(panel.valores.get("aristas") or []) == 1,
            "Empalme (F) toma la arista preseleccionada en su diálogo")
    n = len(v.doc.operaciones)
    if panel is not None:
        panel.set_valor("radio", "1 mm")
        panel.aceptar()
        QTest.qWait(200)
    r.check(len(v.doc.operaciones) == n + 1 and v.doc.resultados[-1].estado == "ok" and v.panel is None,
            "Aceptar el diálogo agrega el empalme al timeline (OK)")
    v.acciones["sel_ventana"].trigger()
    w, h = v.visor.width(), v.visor.height()
    v._seleccion_region([(0, 0), (w, 0), (w, h), (0, h)], False)
    v.visor.set_modo(None)
    r.check(len(v.seleccion) == len(v.doc.estado_final.cuerpos), "Selección en ventana: elige todos los cuerpos")
    v._seleccionar([])
    v.doc.agregar_analisis("seccion", {"plano": {"tipo": "plano", "id": "XZ"}, "desfase_mm": 0.0})
    QTest.qWait(200)
    r.check(bool(v.visor.cortes) and v.navegador.item("analisis:Sección1") is not None,
            "Análisis de sección: corta la vista y aparece en el navegador")
    v.doc.quitar_analisis("Sección1")
    r.check(not v.visor.cortes, "Quitar el análisis restaura la vista")
    dibujo = v.abrir_espacio("dibujo", vista_base=False)   # sin el diálogo modal de vista base
    QTest.qWait(300)
    r.check(dibujo is not None and dibujo.isVisible(), "DISEÑO ▾ › DIBUJO abre el espacio de dibujo")
    if dibujo is not None:
        dibujo.close()


def _fase_interaccion(v, r):
    """Manipulación como en el video de Fusion: ventana al arrastrar, menú radial y gestos, "Seleccionar otro"
    manteniendo apretado, medidas de lo elegido, avisos flotantes y planos del origen ocultos."""
    v.set_documento(__import__("omnicad.ejemplo", fromlist=["x"]).crear_documento_ejemplo())
    v.visor.vista("iso")
    v.visor.encuadrar()
    QTest.qWait(200)
    w, h = v.visor.width(), v.visor.height()
    v._seleccionar([])
    QTest.mousePress(v.visor, Qt.LeftButton, Qt.NoModifier, QPoint(4, 4))
    for k in range(1, 6):
        QTest.mouseMove(v.visor, QPoint(4 + (w - 8) * k // 5, 4 + (h - 8) * k // 5))
    banda = v.visor._banda
    r.check(banda is not None and banda.isVisible() and not banda.cruce,
            "Arrastrar en la vista dibuja la ventana de selección (naranja, de izquierda a derecha)")
    QTest.mouseRelease(v.visor, Qt.LeftButton, Qt.NoModifier, QPoint(w - 4, h - 4))
    r.check(len(v.seleccion) == len(v.doc.estado_final.cuerpos),
            "La ventana elige los cuerpos que quedan adentro, sin elegir antes la herramienta")
    r.check("Volumen:" in v.timeline.estado.toolTip(), "Abajo a la derecha se ven las medidas de lo elegido")
    v._seleccionar([])
    hit = v.visor.elegir_entidad(v.visor.proyectar(__import__("numpy").array([2.0, 2.0, 0.0])), {"plano"})
    r.check(hit is None or hit["tipo"] != "plano", "Los planos del origen ocultos no se eligen con un clic suelto")
    menu = v._menu_vista(None, v.visor.mapToGlobal(QPoint(w // 2, h // 2)))
    QTest.qWait(200)
    textos = [i.texto if i else None for i in menu.items]
    r.check(menu.isVisible() and textos[2] == "Rehacer" and textos[4] == "Boceto" and textos[6] == "Deshacer",
            "Clic derecho abre el menú radial de Fusion (Repetir, Pulsar/tirar, Rehacer, Agujero, Boceto…)")
    menu.close()
    n = len(v.doc.operaciones)
    centro = QPoint(w // 2, h // 2)
    QTest.mousePress(v.visor, Qt.RightButton, Qt.NoModifier, centro)
    QTest.mouseMove(v.visor, centro + QPoint(-90, 0))
    QTest.mouseRelease(v.visor, Qt.RightButton, Qt.NoModifier, centro + QPoint(-90, 0))
    QTest.qWait(200)
    r.check(len(v.doc.operaciones) == n - 1, "Gesto: clic derecho y arrastrar a la izquierda = Deshacer")
    v.doc.rehacer()
    QTest.qWait(200)
    cid = next(iter(v.doc.estado_final.cuerpos))
    import numpy as np
    caja = geo.caja_envolvente(v.doc.estado_final.cuerpos[cid].forma)
    punto = v.visor.proyectar((np.array(caja[0]) + np.array(caja[1])) / 2)
    QTest.mousePress(v.visor, Qt.LeftButton, Qt.NoModifier, punto.toPoint())
    QTest.qWait(800)
    otro = getattr(v, "_menu_otro", None)
    r.check(otro is not None and otro.isVisible() and len(otro.actions()) >= 2,
            "Mantener apretado el clic abre «Seleccionar otro» con lo que hay bajo el cursor")
    if otro is not None:
        accion = [a for a in otro.actions() if not a.isSeparator()][-1]
        accion.trigger()
        otro.hide()
        QTest.qWait(100)
        r.check(len(v.seleccion) == 1, "Elegir una fila de «Seleccionar otro» la selecciona")
    QTest.mouseRelease(v.visor, Qt.LeftButton, Qt.NoModifier, punto.toPoint())
    v._seleccionar([])
    v.aviso_flotante("Las restricciones o las cotas se han eliminado durante la operación.")
    QTest.qWait(100)
    r.check(v.area.toast.isVisible() and "advertencia" in v.area.toast.titulo.text(),
            "Aviso flotante «1 advertencia(s)» abajo a la derecha")
    v.area.toast.hide()
    from PySide6.QtWidgets import QLineEdit
    cid = next(iter(v.doc.estado_final.cuerpos))
    item = v.navegador.item(cid)
    r.check(item is not None and v.navegador.renombrar_en_linea(item), "Doble clic / F2 renombra en el navegador")
    editor = v.navegador.arbol.findChild(QLineEdit)
    if editor is not None:
        editor.setText("Base")
        QTest.keyClick(editor, Qt.Key_Return)
        QTest.qWait(150)
    r.check(v.nombre_cuerpo(v.doc.estado_final.cuerpos[cid]) == "Base", "El nombre escrito en el lugar queda en el cuerpo")
    v.comentarios.agregar("Revisar el espesor")
    QTest.qWait(100)
    r.check(v.doc.comentarios and v.comentarios.isVisible() and v.comentarios.lista.count() == 1,
            "COMENTARIOS (abajo a la izquierda) agrega notas al diseño")
    from .restricciones import Boceto
    v._iniciar_boceto(Boceto(), geo.Plano("XY"), {"op": None, "plano": "XY", "marco": None})
    QTest.qWait(150)
    lz = v.modo_boceto.lienzo
    v.modo_boceto.acciones["sk_linea"].trigger()
    centro_lz = lz.rect().center()
    QTest.mouseClick(lz, Qt.RightButton, Qt.NoModifier, centro_lz)
    QTest.qWait(200)
    radial = v._menu_radial
    r.check(radial is not None and radial.isVisible() and radial.items[2].texto == "Aceptar"
            and radial.items[6].texto == "Cancelar" and lz.herramienta == "linea",
            "En el boceto, clic derecho abre el menú radial con Aceptar / Cancelar (no corta la herramienta)")
    if radial is not None:
        radial.close()
    v.modo_boceto.cancelar()
    QTest.qWait(100)
    caja = v.ayuda_comando(v.acciones["empalme_3d"])
    QTest.qWait(100)
    r.check(caja is not None and caja.isVisible() and "Empalme" in caja.windowTitle(),
            "Ctrl+/ sobre un comando muestra su ayuda")
    if caja is not None:
        caja.close()


def _fase_puente(v, r, carpeta):
    """Puente para agentes IA (MCP en vivo) con la ventana real: conectar, create_box aparece en el navegador,
    deshacer lo saca y un token incorrecto se rechaza. El puente.json va a la carpeta temporal de la prueba."""
    import json
    import os
    import time

    from PySide6.QtNetwork import QAbstractSocket, QHostAddress, QTcpSocket

    from .api import protocolo_puente as proto
    from .timeline.documento import Documento
    os.environ[proto.VARIABLE_CARPETA] = str(carpeta)
    v.set_documento(Documento())
    r.check(v.encender_puente() and proto.leer_info() is not None, "Puente IA: escucha en 127.0.0.1 y escribe puente.json")
    info = proto.leer_info() or {"port": 0, "token": ""}

    def conectar():
        s = QTcpSocket()
        s.connectToHost(QHostAddress(QHostAddress.SpecialAddress.LocalHost), info["port"])
        return s

    def pedir(s, tool, args=None, token=None):          # sin bloquear el hilo de Qt: espera procesando eventos
        s.write(proto.linea({"id": 1, "token": token or info["token"], "tool": tool, "args": args or {}}))
        buffer, limite = b"", time.time() + 20
        while b"\n" not in buffer and time.time() < limite:
            QTest.qWait(5)
            buffer += bytes(s.readAll())
        return json.loads(buffer.partition(b"\n")[0] or b"{}")

    s = conectar()
    r.check(pedir(s, "ping").get("ok") is True and "Agente IA conectado" in v.puente.indicador.text(),
            "Puente IA: el agente conecta y la barra muestra «Agente IA conectado»")
    creado = pedir(s, "create_box", {"length": 30, "width": 20, "height": 10})
    cid = next(iter(v.doc.estado_final.cuerpos), None)
    r.check(creado.get("ok") is True and cid is not None and v.navegador.item(cid) is not None,
            "Puente IA: create_box del agente aparece en el navegador de la ventana")
    r.check("Agente IA: create_box" in v.timeline.estado.toolTip(), "Puente IA: la barra de estado avisa «Agente IA: …»")
    deshecho = pedir(s, "undo")
    r.check(deshecho.get("ok") is True and not v.doc.estado_final.cuerpos and v.navegador.item(cid) is None,
            "Puente IA: undo del agente lo saca de la ventana")
    s.disconnectFromHost()
    malo = conectar()
    rechazo = pedir(malo, "get_scene_info", token="token-falso")
    limite = time.time() + 5
    while malo.state() != QAbstractSocket.SocketState.UnconnectedState and time.time() < limite:
        QTest.qWait(5)
    r.check(rechazo.get("error_kind") == "UNAUTHORIZED" and malo.state() == QAbstractSocket.SocketState.UnconnectedState,
            "Puente IA: un token incorrecto se rechaza y se cierra la conexión")
    v._puente_sesion = False
    v._aplicar_puente()
    r.check(proto.leer_info() is None, "Puente IA: al apagarlo se borra puente.json")
    os.environ.pop(proto.VARIABLE_CARPETA, None)


def ejecutar():
    _app = QApplication.instance() or QApplication([])  # noqa: F841 — mantiene viva la app
    r = _Registro()
    carpeta = Path(tempfile.mkdtemp(prefix="omnicad_humo_"))
    prefs = Preferencias(QSettings(str(carpeta / "preferencias.ini"), QSettings.IniFormat))
    v = VentanaPrincipal(prefs=prefs)
    v.show()
    QTest.qWait(300)
    r.check(v.isVisible(), "La ventana principal se muestra")

    # 1) Ejemplo completo + visor
    v.set_documento(__import__("omnicad.ejemplo", fromlist=["x"]).crear_documento_ejemplo())
    QTest.qWait(400)
    estados = [x.estado for x in v.doc.resultados]
    r.check(estados == ["ok"] * len(estados), f"Ejemplo: {len(estados)} pasos del timeline en OK")
    img = v.visor.grabFramebuffer()
    r.check(_colores_distintos(img) > 50, f"El visor 3D dibuja el modelo ({_colores_distintos(img)} colores distintos)")
    r.check(v.timeline.lista.count() == len(v.doc.operaciones) + 1, "La barra de timeline muestra todos los pasos + marcador")
    for vista in ("frente", "arriba", "derecha", "iso"):
        v.visor.vista(vista)
    v.visor.set_ortografica(True)
    QTest.qWait(100)
    r.check(_colores_distintos(v.visor.grabFramebuffer()) > 50, "Vista ortográfica y vistas estándar dibujan")
    v.visor.set_ortografica(False)

    # 2) Órbita / zoom / pan con el ratón (esquema de Fusion: Mayús + botón del medio orbita)
    az0, d0 = v.visor.azimut, v.visor.distancia
    centro = v.visor.rect().center()
    QTest.mousePress(v.visor, Qt.MiddleButton, Qt.ShiftModifier, centro)
    QTest.mouseMove(v.visor, centro + QPoint(60, 20))
    QTest.mouseRelease(v.visor, Qt.MiddleButton, Qt.ShiftModifier, centro + QPoint(60, 20))
    r.check(v.visor.azimut != az0, "Órbita con Mayús + botón del medio (como Fusion)")
    v.visor.distancia = d0 * 0.5
    v.visor.encuadrar()
    r.check(abs(v.visor.distancia - d0) / d0 < 0.5, "Encuadrar recupera la distancia de la cámara")

    # 2b) Interfaz estilo Fusion
    _interfaz(v, r)
    _fase3d(v, r)
    _fase_interaccion(v, r)
    _fase_puente(v, r, carpeta)
    v.set_documento(__import__("omnicad.ejemplo", fromlist=["x"]).crear_documento_ejemplo())
    QTest.qWait(200)

    # 3) Boceto dentro de la vista 3D, como en Fusion
    sk = _boceto_en_3d(v, r)

    # 4) Extrusión del anillo del boceto nuevo
    perfiles = v.doc.estado_final.bocetos[sk.id].perfiles
    r.check(len(perfiles) == 2, f"El boceto nuevo da 2 perfiles (anillo y disco): {len(perfiles)}")
    anillo = max(perfiles, key=lambda p: p.area)
    v._agregar(OpExtrusion(v.doc.nuevo_id(), "Extrusión humo", boceto=sk.id,
                           perfiles=[OpExtrusion.referencia_perfil(anillo)], distancia="5 mm"))
    r.check(v.doc.resultados[-1].estado == "ok", "Extrusión desde el boceto nuevo: OK")
    QTest.qWait(100)

    # 5) Parámetro → todo el modelo se recalcula
    tabla = type(v.doc.parametros).desde_lista(v.doc.parametros.a_lista())
    tabla.modificar("ancho", "80 mm")
    v.doc.aplicar_parametros(tabla)
    placa = v.doc.estado_final.cuerpos["op2.c1"]
    (x0, _, _), (x1, _, _) = geo.caja_envolvente(placa.forma)
    malos = [(o.nombre, x.estado, x.mensaje) for o, x in zip(v.doc.operaciones, v.doc.resultados, strict=True) if x.estado != "ok"]
    r.check(abs((x1 - x0) - 80) < 1e-3 and not malos,
            f"Cambiar «ancho» a 80 mm recalcula todo el timeline (ancho medido {x1 - x0:.3f}) {malos if malos else ''}")
    (n0, _, _), (n1, _, _) = geo.caja_envolvente(v.doc.estado_final.cuerpos[f"{v.doc.operaciones[-1].id}.c1"].forma)
    r.check(abs((n1 - n0) - 80) < 1e-3,
            f"…incluida la extrusión nueva, que usa el mismo parámetro (ancho {n1 - n0:.3f})")

    # 5b) Editar el boceto (vista retrocedida) y plano de construcción
    _editar_boceto(v, r, sk)
    v._agregar(OpPlano(v.doc.nuevo_id(), base="XY", distancia="40 mm"))
    plano_id = v.doc.operaciones[-1].id
    r.check(v.navegador.item(plano_id) is not None and any(p[0] == plano_id for p in v.visor.config.planos_usuario),
            "Plano de desfase: aparece en Construcción y en la vista")
    v.doc.eliminar(plano_id)

    # 6) Marcador, suprimir, deshacer
    v.doc.mover_marcador(2)
    QTest.qWait(50)
    r.check(len(v.doc.estado_final.cuerpos) == 1, "Marcador en el paso 2: solo queda la placa")
    v.doc.mover_marcador(len(v.doc.operaciones))
    n = len(v.doc.operaciones)
    v.doc.deshacer()
    r.check(len(v.doc.operaciones) == n + 1, "Deshacer revierte el último cambio (el plano borrado vuelve)")
    v.doc.rehacer()

    # 7) Guardar / exportar / reabrir
    ruta = carpeta / "humo.omnicad"
    r.check(v._guardar_en(str(ruta)) and ruta.exists(), "Guardar proyecto .omnicad")
    r.check(proyecto.leer_miniatura(ruta) is not None, "El proyecto incluye la miniatura del visor")
    r.check(v.panel_datos.lista.count() >= 1, "El proyecto guardado aparece en «Mis datos recientes»")
    for formato in ex.FORMATOS:
        destino = carpeta / f"humo.{formato}"
        ex.exportar(v.doc.estado_final.cuerpos.values(), destino)
        r.check(destino.exists() and destino.stat().st_size > 1000, f"Exportar {formato.upper()} ({destino.stat().st_size:,} bytes)")
    v.doc.modificado = False
    v.abrir_ruta(str(ruta))
    QTest.qWait(200)
    r.check(v.doc.ruta == str(ruta) and all(x.estado == "ok" for x in v.doc.resultados), "Reabrir el proyecto recalcula todo OK")
    r.check(_colores_distintos(v.visor.grabFramebuffer()) > 50, "El visor dibuja el proyecto reabierto")

    # 8) Autoguardado
    v.doc.modificado = True
    v.autoguardar()
    auto = proyecto.ruta_autoguardado(v.doc)
    r.check(auto.exists(), f"Autoguardado escrito: {auto.name}")
    proyecto.borrar_autoguardado(v.doc)
    v.doc.modificado = False
    v.close()
    print(f"\nResultado: {'TODO OK' if r.fallas == 0 else f'{r.fallas} FALLA(S)'} — archivos en {carpeta}")
    return 0 if r.fallas == 0 else 1
