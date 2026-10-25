"""Conversación del asistente con proveedor falso y herramientas reales, sin red."""
import json
from pathlib import Path

import pytest

from omnicad import api
from omnicad.asistente import bucle
from omnicad.asistente.herramientas import NUCLEO, TOPE_BUSQUEDA, Herramientas
from omnicad.asistente.proveedores.base import PedidoHerramienta, Proveedor, ProveedorFalso, Respuesta


@pytest.fixture
def sesion():
    return api.Sesion()


def test_pedido_completo_crea_caja_y_adjunta_imagen(sesion):
    proveedor = ProveedorFalso([
        Respuesta(herramientas=[PedidoHerramienta("caja", "create_box", {"length": 40, "width": 40, "height": 40})]),
        Respuesta(herramientas=[PedidoHerramienta("vista", "get_viewport_image", {})]),
        Respuesta(texto="Listo"),
    ])
    mensajes = [{"rol": "usuario", "contenido": [{"tipo": "texto", "texto": "Creá una caja de 40 mm."}]}]
    eventos = []
    resultado = bucle.correr(proveedor, mensajes, lambda n, a: api.llamar(sesion, n, a),
                             al_evento=lambda t, d: eventos.append((t, d)))
    assert resultado == {"motivo": "fin", "vueltas": 3,
                         "uso": {"entrada": 0, "salida": 0, "costo_usd": None}}
    assert len(sesion.doc.estado_final.cuerpos) == 1
    imagenes = [d for t, d in eventos if t == "imagen"]
    assert len(imagenes) == 1 and isinstance(imagenes[0], api.Imagen)
    assert imagenes[0].png.startswith(b"\x89PNG\r\n\x1a\n")
    bloques = mensajes[4]["contenido"][0]["contenido"]
    assert bloques[1] == {"tipo": "imagen", "png": imagenes[0].png,
                          "ancho": imagenes[0].ancho, "alto": imagenes[0].alto}
    assert "Imagen(" not in bloques[0]["texto"] and "bytes" not in bloques[0]["texto"]
    assert "(imagen adjunta)" in bloques[0]["texto"]
    assert [d for t, d in eventos if t == "texto"] == ["Listo"]
    assert mensajes[-1] == {"rol": "asistente", "contenido": [{"tipo": "texto", "texto": "Listo"}]}
    assert proveedor.recibidos[2][0][-1] == mensajes[4]
    for tipo, datos in eventos:
        if tipo == "herramienta":
            json.dumps(datos["respuesta"])


def test_error_de_herramienta_vuelve_al_proveedor(sesion):
    proveedor = ProveedorFalso([Respuesta(herramientas=[PedidoHerramienta("empalme", "fillet", {"radius": 1})]),
                               Respuesta(texto="Falta indicar el cuerpo.")])
    assert bucle.correr(proveedor, [], lambda n, a: api.llamar(sesion, n, a))["motivo"] == "fin"
    bloque = proveedor.recibidos[1][0][-1]["contenido"][0]
    assert bloque["error"] is True
    texto = bloque["contenido"][0]["texto"]
    assert "INVALID_ARGUMENTS" in texto and "pistas" in texto
    assert json.loads(texto)["pistas"]


def test_tope_de_vueltas(sesion):
    proveedor = ProveedorFalso([Respuesta(herramientas=[PedidoHerramienta(str(i), "get_timeline", {})])
                               for i in range(30)])
    mensajes, eventos = [], []
    resultado = bucle.correr(proveedor, mensajes, lambda n, a: api.llamar(sesion, n, a), tope_vueltas=3,
                             al_evento=lambda t, d: eventos.append((t, d)))
    assert resultado["motivo"] == "tope" and resultado["vueltas"] == 3
    assert len(proveedor.recibidos) == 3 and len(mensajes) == 6
    assert ("error", "Se llegó al tope de 3 vueltas: el pedido se cortó.") in eventos


def test_buscar_herramientas_habilita_por_nombre_y_al_final(sesion):
    herramientas = Herramientas()
    chapa = {h["nombre"] for h in api.catalogo("chapa")}
    assert not chapa.intersection(h["nombre"] for h in herramientas.definiciones())
    antes = [h["nombre"] for h in herramientas.definiciones()]
    proveedor = ProveedorFalso([
        Respuesta(herramientas=[PedidoHerramienta("buscar", "buscar_herramientas",
                                                  {"nombres": ["create_flat_pattern", "create_box", "no_existe"]})]),
        Respuesta(texto="Herramientas disponibles."),
    ])
    resultado = bucle.correr(proveedor, [], lambda n, a: api.llamar(sesion, n, a), herramientas=herramientas)
    assert resultado["motivo"] == "fin"
    # la habilitada va AL FINAL: el prefijo que ya se mandó no cambia (caché del prompt)
    assert proveedor.recibidos[1][1] == [*antes, "create_flat_pattern"]
    bloque = proveedor.recibidos[1][0][-1]["contenido"][0]
    salida = json.loads(bloque["contenido"][0]["texto"])
    assert [h["name"] for h in salida["result"]["enabled"]] == ["create_flat_pattern", "create_box"]
    assert salida["result"]["unknown"] == ["no_existe"] and salida["ok"]


def test_buscar_por_consulta_y_por_grupo_con_tope():
    herramientas = Herramientas()
    r = herramientas.buscar(consulta="aspecto color apariencia")
    assert r["ok"] and "set_appearance" in [h["name"] for h in r["result"]["enabled"]]
    r = herramientas.buscar(grupo="solido")
    assert len(r["result"]["enabled"]) == TOPE_BUSQUEDA and r["result"]["more"]
    assert len(herramientas.habilitadas) == len(set(herramientas.habilitadas))


@pytest.mark.parametrize("args", [{}, {"grupo": "dev"}, {"grupo": "inexistente"}, {"nombres": []},
                                  {"nombres": "create_box"}, {"nombres": [1]}, {"consulta": ""}, {"consulta": 42}])
def test_buscar_rechaza_pedidos_invalidos(args):
    herramientas = Herramientas()
    resultado = herramientas.buscar(**args)
    assert resultado["ok"] is False and resultado["error_kind"] == "INVALID_ARGUMENTS"
    assert herramientas.habilitadas == []


@pytest.mark.parametrize("args", [{"tema": "chapa"}, {"grupo": "chapa", "extra": True}, [], {"grupo": []}])
def test_argumentos_malos_de_busqueda_vuelven_al_modelo(sesion, args):
    proveedor = ProveedorFalso([Respuesta(herramientas=[PedidoHerramienta("buscar", "buscar_herramientas", args)])])
    resultado = bucle.correr(proveedor, [], lambda n, a: api.llamar(sesion, n, a))
    assert resultado["motivo"] == "fin"
    bloque = proveedor.recibidos[1][0][-1]["contenido"][0]
    assert bloque["error"] is True
    assert json.loads(bloque["contenido"][0]["texto"])["error_kind"] == "INVALID_ARGUMENTS"


def test_seguridad_no_ofrece_ni_ejecuta_codigo_o_dev(sesion):
    herramientas = Herramientas()
    catalogo = {h["nombre"]: h for h in api.catalogo()}
    for tema in herramientas.temas:
        assert herramientas.buscar(nombres=[n for n, h in herramientas.catalogo.items() if h["grupo"] == tema])["ok"]
    nombres = [h["nombre"] for h in herramientas.definiciones()]
    assert len(nombres) == len(set(nombres))
    assert "execute_code" not in nombres
    assert all(catalogo[n]["grupo"] != "dev" for n in nombres if n != "buscar_herramientas")
    prohibidas = ["execute_code", next(h["nombre"] for h in api.catalogo("dev")), "no_existe"]
    proveedor = ProveedorFalso([Respuesta(herramientas=[PedidoHerramienta(str(i), n, {})
                                                       for i, n in enumerate(prohibidas)])])
    llamadas = []

    def ejecutar(nombre, args):
        llamadas.append(nombre)
        return api.llamar(sesion, nombre, args)

    assert bucle.correr(proveedor, [], ejecutar, herramientas=herramientas)["motivo"] == "fin"
    assert llamadas == []
    bloques = proveedor.recibidos[1][0][-1]["contenido"]
    assert len(bloques) == len(prohibidas)
    for bloque in bloques:
        assert bloque["error"] is True
        assert json.loads(bloque["contenido"][0]["texto"])["error_kind"] == "TOOL_NOT_AVAILABLE"


def test_nucleo_y_esquemas_originales():
    catalogo = {h["nombre"]: h for h in api.catalogo()}
    definiciones = Herramientas().definiciones()
    assert [h["nombre"] for h in definiciones] == [*NUCLEO, "buscar_herramientas"]
    for definicion in definiciones[:-1]:
        assert set(definicion) == {"nombre", "descripcion", "esquema"}
        original = catalogo[definicion["nombre"]]
        assert definicion["esquema"] is original["esquema"]
        assert definicion["descripcion"] == original["descripcion"]
    busqueda = definiciones[-1]
    esquema = busqueda["esquema"]
    temas = sorted({h["grupo"] for h in catalogo.values()} - {"dev", "asistente"})   # asistente: no se llama a sí mismo
    assert esquema["type"] == "object" and esquema["additionalProperties"] is False
    assert set(esquema["properties"]) == {"nombres", "consulta", "grupo"}
    assert esquema["properties"]["grupo"]["enum"] == temas


@pytest.mark.parametrize("ejecutadas", [0, 1])
def test_cancelado_completa_los_pedidos_pendientes(sesion, ejecutadas):
    proveedor = ProveedorFalso([Respuesta(herramientas=[PedidoHerramienta(str(i), "get_timeline", {})
                                                       for i in range(3)])])
    comprobaciones, llamadas, mensajes = [], [], []

    def cancelado():
        comprobaciones.append(True)
        return len(comprobaciones) > ejecutadas + 1

    def ejecutar(nombre, args):
        llamadas.append(nombre)
        return api.llamar(sesion, nombre, args)

    resultado = bucle.correr(proveedor, mensajes, ejecutar, cancelado=cancelado)
    assert resultado["motivo"] == "cancelado" and resultado["vueltas"] == 1
    assert len(llamadas) == ejecutadas and len(proveedor.recibidos) == 1
    assert len(mensajes) == 2 and mensajes[1]["rol"] == "usuario"
    bloques = mensajes[1]["contenido"]
    assert [b["id"] for b in bloques] == ["0", "1", "2"]
    for bloque in bloques[ejecutadas:]:
        assert bloque["error"] is True
        assert json.loads(bloque["contenido"][0]["texto"])["error_kind"] == "CANCELLED"


def test_cancelado_antes_de_responder(sesion):
    proveedor = ProveedorFalso([])
    mensajes = []
    resultado = bucle.correr(proveedor, mensajes, lambda n, a: api.llamar(sesion, n, a), cancelado=lambda: True)
    assert resultado["motivo"] == "cancelado" and resultado["vueltas"] == 0
    assert proveedor.recibidos == [] and mensajes == []


def test_excepcion_en_ejecutar_vuelve_al_modelo_y_continua(sesion):
    proveedor = ProveedorFalso([Respuesta(herramientas=[PedidoHerramienta("fallo", "get_timeline", {}),
                                                       PedidoHerramienta("siguiente", "get_parameters", {})]),
                               Respuesta(texto="Se recibió el error.")])

    def ejecutar(nombre, args):
        if nombre == "get_timeline":
            raise RuntimeError("Fallo de prueba")
        return api.llamar(sesion, nombre, args)

    resultado = bucle.correr(proveedor, [], ejecutar)
    assert resultado["motivo"] == "fin" and resultado["vueltas"] == 2
    bloques = proveedor.recibidos[1][0][-1]["contenido"]
    salida = json.loads(bloques[0]["contenido"][0]["texto"])
    assert bloques[0]["error"] is True and salida["error_kind"] == "INTERNAL_ERROR"
    assert salida["mensaje"] == "RuntimeError: Fallo de prueba"
    assert bloques[1]["error"] is False


@pytest.mark.parametrize("costos, esperado", [([None, None, None], None), ([None, 0.25, 0.5], 0.75),
                                          ([0.0, None, None], 0.0)])
def test_uso_se_acumula_y_emite_por_vuelta(sesion, costos, esperado):
    usos = [{"entrada": i + 1, "salida": 2 * i, "costo_usd": costo} for i, costo in enumerate(costos)]
    proveedor = ProveedorFalso([
        Respuesta(herramientas=[PedidoHerramienta("uno", "get_timeline", {})], uso=usos[0]),
        Respuesta(herramientas=[PedidoHerramienta("dos", "get_parameters", {})], uso=usos[1]),
        Respuesta(texto="Fin", uso=usos[2]),
    ])
    eventos = []
    resultado = bucle.correr(proveedor, [], lambda n, a: api.llamar(sesion, n, a),
                             al_evento=lambda t, d: eventos.append((t, d)))
    assert resultado["uso"] == {"entrada": 6, "salida": 6, "costo_usd": esperado}
    assert [d for t, d in eventos if t == "uso"] == usos


def test_imagenes_anidadas_se_separan_sin_modificar_respuesta():
    imagen = api.Imagen(b"contenido PNG de prueba", 2, 3)
    salida = {"ok": True, "result": {"capas": [imagen, {"otra": [imagen]}]}, "avisos": ["Aviso en español"]}
    proveedor = ProveedorFalso([Respuesta(herramientas=[PedidoHerramienta("anidada", "get_viewport_image", {})])])
    mensajes, eventos = [], []
    resultado = bucle.correr(proveedor, mensajes, lambda n, a: salida,
                             al_evento=lambda t, d: eventos.append((t, d)))
    assert resultado["motivo"] == "fin"
    bloques = mensajes[1]["contenido"][0]["contenido"]
    assert json.loads(bloques[0]["texto"]) == {
        "ok": True, "result": {"capas": ["(imagen adjunta)", {"otra": ["(imagen adjunta)"]}]},
        "avisos": ["Aviso en español"],
    }
    assert len(bloques) == 3 and all(b["tipo"] == "imagen" for b in bloques[1:])
    assert [d for t, d in eventos if t == "imagen"] == [imagen, imagen]
    assert salida["result"]["capas"][0] is imagen
    json.dumps(next(d for t, d in eventos if t == "herramienta"))


def test_respuesta_vacia_termina_sin_mensaje_vacio(sesion):
    mensajes = [{"rol": "usuario", "contenido": [{"tipo": "texto", "texto": "Hola"}]}]
    resultado = bucle.correr(ProveedorFalso([Respuesta()]), mensajes, lambda n, a: api.llamar(sesion, n, a))
    assert resultado["motivo"] == "fin" and resultado["vueltas"] == 1
    assert mensajes == [{"rol": "usuario", "contenido": [{"tipo": "texto", "texto": "Hola"}]}]


def test_error_del_proveedor_emite_evento_y_termina(sesion):
    class ProveedorFallido(Proveedor):
        def responder(self, sistema, mensajes, herramientas):
            raise RuntimeError("Proveedor no disponible")

    eventos, mensajes = [], []
    resultado = bucle.correr(ProveedorFallido(), mensajes, lambda n, a: api.llamar(sesion, n, a),
                             al_evento=lambda t, d: eventos.append((t, d)))
    assert resultado["motivo"] == "error" and resultado["vueltas"] == 1
    assert eventos == [("error", "Proveedor no disponible")] and mensajes == []


def test_proveedor_base_y_falso_respetan_el_contrato():
    with pytest.raises(NotImplementedError):
        Proveedor().responder("", [], [])
    mensajes = [{"rol": "usuario", "contenido": [{"tipo": "texto", "texto": "Original"}]}]
    proveedor = ProveedorFalso([])
    respuesta = proveedor.responder("", mensajes, [{"nombre": "get_timeline"}])
    mensajes[0]["contenido"][0]["texto"] = "Modificado"
    assert proveedor.recibidos == [([{"rol": "usuario", "contenido": [{"tipo": "texto", "texto": "Original"}]}],
                                   ["get_timeline"])]
    assert respuesta == Respuesta(texto="(fin del guion)")
    respuesta.herramientas.append(PedidoHerramienta("uno", "get_timeline", {}))
    respuesta.uso["entrada"] = 10
    assert proveedor.responder("", [], []) == Respuesta(texto="(fin del guion)")


def test_catalogo_vacio_no_se_reemplaza_por_el_real():
    herramientas = Herramientas(catalogo=[])
    assert [h["nombre"] for h in herramientas.definiciones()] == ["buscar_herramientas"]
    assert herramientas.buscar(grupo="solido")["error_kind"] == "INVALID_ARGUMENTS"


def test_sin_dependencias_de_interfaz():
    carpeta = Path(bucle.__file__).parent
    archivos = list(carpeta.rglob("*.py"))
    assert len(archivos) >= 5
    for archivo in archivos:
        contenido = archivo.read_text(encoding="utf-8")
        assert "PySide" not in contenido and "QtCore" not in contenido, archivo
