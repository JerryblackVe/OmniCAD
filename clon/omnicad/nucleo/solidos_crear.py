# -*- coding: utf-8 -*-
"""
Comandos SÓLIDO › CREAR de Fusion 360 en el núcleo: extrusión y revolución completas, barrido,
solevado, nervio, red, repujado, agujero, rosca, bobina, tubería, patrones y simetría, engrosar,
relleno de contorno y sólido envolvente; más saliente y labio de la pestaña PLÁSTICO (simplificados).

Funciones puras: reciben formas OCC, arrays o números y devuelven formas OCC (los patrones devuelven
listas de gp_Trsf). La booleana contra los cuerpos del documento la hace la capa de operaciones, salvo
donde el comando de Fusion entrega el cuerpo ya modificado (repujado, rosca, saliente, labio).
Unidades: mm y grados. Ayuda de cada comando: analisis/fusion_doc/paginas/<ID>.txt.
"""
import sys as _sys
from types import ModuleType as _Modulo

import functools as functools
import itertools as itertools
import math as math
import re as re

import numpy as np  # noqa: F401
from . import motor as _motor  # noqa: F401
from . import tablas_rosca as tablas_rosca
from . import geometria as geo  # noqa: F401
from . import revision as rv  # noqa: F401
from .solidos_crear_comun import (  # noqa: F401
    _MARGEN, _alambre, _aristas_de, _cadenas, _caja_proyectada, _cara, _caras_de, _engrosar_lamina, _es_cerrado,
    _explorar, _extremos, _gdir, _gvec, _lista, _longitud, _marcos, _normal_superficie, _perpendicular,
    _piezas_que_tocan, _pnt, _poligono, _proyectar_caja, _punto_en, _rayo, _recortar_alambre, _tipado, _trasladar,
    _unificar, _unir, _unit, _validar, _xyz, cara_de_plano, lado_todo,
)
from .solidos_crear_extrusion import (  # noqa: F401
    _CIERRES, _bandas_cerradas, _cara_poligonal_conicidad, _cierre, _cierre_adentro, _conicidad_sin_draft,
    _desfasado, _desfase_alambre, _distancia_a_plano, _extruir_perfiles_vecinos, _firma, _herramienta_extrusion,
    _limite_adyacente, _prisma, _prisma_curvo_inclinado, _recortar_hasta, _recorte_en_vertice, _sentido_alambre,
    extruir_avanzado, radios_conicidad,
)
from .solidos_crear_revolucion import _angulos_de_cruce, _girar, _marco_giro, revolver_avanzado, revolver_hasta  # noqa: F401
from .solidos_crear_barrido import (  # noqa: F401
    MUESTRAS_BARRIDO_CUERPO, QUIEBRE_MAXIMO_TORSION, TORSION_MAXIMA, TORSION_MAXIMA_CURVILINEA, _QUIEBRE_LISO,
    _barrer, _barrido_alambre, _curvaturas, _exigir_conicidad_en_curvas, _exigir_ruta_para_torsion,
    _guia_plana_posible, _guia_torsion, _ley_escala_carril, _punto_en_cara, _quiebre_maximo, _radio_referencia,
    barrer, barrer_cuerpo, validar_torsion,
)
from .solidos_crear_solevacion import (  # noqa: F401
    _TOL_CANONICA, _auxiliar_direccion, _auxiliar_tangente, _canonizar, _centro_alambre, _con_condiciones,
    _curva_canonica, _exigir_ida, _exigir_puntos_utiles, _hacia_afuera_de_la_cara, _loft, _plano_canonico,
    _plegada, _seccion, solevar,
)
from .solidos_crear_nervios import (  # noqa: F401
    _desmoldear_pared, _diagonal, _engrosar_nervio, _extender_extremos, _hasta_el_cuerpo, _lamina_hasta_el_cuerpo,
    _sentido_curva, _sentido_hacia_cuerpo, nervio, red, sentido_crecimiento, unir_con_empalme,
)
from .solidos_crear_repujado import (  # noqa: F401
    _alinear_repujado, _aplicar_a_cuerpo, _aristas_envueltas, _booleana_caras, _caja_2d, _cajas_se_tocan,
    _comun_rapido, _dentro_de_cara, _envolver_en_cilindro, _estados_en_cara, _lista_de_formas, _matriz_giro,
    _normal_orientada, _perfiles_en_zona, _proyectar_en_cara, _puntos_2d, _repujado_en_grupo, _segmento2d,
    _ubicar_en_zona, _zona_convexa, repujado, repujado_en_cuerpos,
)
from .solidos_crear_agujeros import (  # noqa: F401
    AJUSTES_PASO_LIBRE, PASO_LIBRE_ISO273, _herramienta_agujero, _perfil_agujero, _rosca_en_origen, agujero,
    agujero_sin_pellizco, diametro_paso_libre, exigir_agujero_sin_pellizco, exigir_agujeros_separados,
    exigir_profundidad_agujero, herramienta_agujero, profundidad_hasta, punto_por_referencias,
)
from .solidos_crear_roscas import (  # noqa: F401
    FAMILIAS_ROSCA, TABLA_ROSCAS, _ACME, _ANCHO_LIMITE, _ANCHO_TOPE, _ANCHO_TORNO, _BSP, _BSP_CONICA, _EPS_ROSCA,
    _EXTRAS, _FRACCION, _GRUESA_POR_D, _ISO_FINA, _ISO_GRUESA, _MUESTRAS_HELICE, _NPT, _ORDEN_FAMILIAS,
    _POR_FAMILIA, _POR_TEXTO, _SUMADAS, _TRAPEZOIDAL, _UNC, _UNF, _WHITWORTH_H, _armar_surco, _armar_tabla,
    _barrer_surco, _barrido_helicoidal, _candidatas_auto, _caras_cilindricas, _clave, _clave_rosca,
    _cortar_helicoidal, _desfases_clase, _en_tramos, _exigir_volumen, _f, _fase_rosca, _fila, _helice,
    _holgura_rosca, _ordenar_familias, _perfil_clase, _perfil_surco, _primera, _radio_cilindro, _radio_hueco,
    _rosca_directa, _surco_en_origen, _surco_rosca, _torno_surco, _tramo_axial, _trapecio_surco, _varilla_roscada,
    _volumen_ok, _volumen_surco, analizar_rosca, caras_sobre_cilindro, datos_rosca, designaciones_rosca,
    diametro_taladro_rosca, familia_de, rosca, tamanos_rosca,
)
from .solidos_crear_bobina_tuberia import _espiral, _seccion_bobina, _seccion_tuberia, bobina, tuberia  # noqa: F401
from .solidos_crear_patrones import (  # noqa: F401
    INSTANCIAS_MAXIMAS, _cajas, _cantidad, _cara_con_huecos, _clave_trsf, _componer, _copias_intercambiables,
    _exigir_instancias, _huecos_de, _id_rectangular, _identidad, _indices, _mapa, _miles, _paso, _rotacion,
    _solapa, _traslacion, _trsf_de_marcos, a_matriz, aplicar, componer_transformaciones,
    exigir_cantidad_patron_ruta, exigir_no_paralelas, instanciar, instancias_circulares, instancias_en_puntos,
    instancias_en_ruta, instancias_rectangulares, paso_angular, patronear_caras, perfil_ruta, recorrido_ruta,
    simetria, transformacion_escala, transformacion_simetria, transformaciones_circulares,
    transformaciones_en_puntos, transformaciones_en_ruta, transformaciones_rectangulares, unir_instancias,
)
from .solidos_crear_volumenes import (  # noqa: F401
    _caja_en_marco, _cilindro_en_eje, _circulo_minimo, _es_material, _marco_automatico, engrosar,
    marco_ortonormal, relleno_contorno, relleno_contorno_celdas, solido_envolvente, volumen_fluido,
)
from .solidos_crear_plastico import (  # noqa: F401
    _caja_local, _fuera, _marco_labio, _recortar_semiespacio, _sector_labio, _validar_aristas_labio, apoyo,
    grampa, labio_ranura, labio_y_ranura, saliente,
)


from .solidos_crear_occ import _espacios, _iniciar_opencascade as _iniciar_opencascade, _vincular


class _Fachada(_Modulo):
    # Una sustitución por la ruta histórica debe llegar también a los temas que importaron ese nombre.
    def __setattr__(self, nombre, valor):
        if not nombre.startswith("__"):
            for espacio in _espacios:
                if nombre in espacio:
                    espacio[nombre] = valor
        super().__setattr__(nombre, valor)


_vincular(globals())
_sys.modules[__name__].__class__ = _Fachada
