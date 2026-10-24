# -*- coding: utf-8 -*-
"""Kernel de restricciones: modelo de boceto 2D + solver numérico."""
from .boceto import Boceto, ErrorBoceto, TIPOS_COTA, TIPOS_RESTRICCION, puntos_primitiva
from .solver import (TIPOS_AUTO, TOPE_TERMINAR_AUTO, ResultadoAuto, ResultadoSolver, Sugerencia, auto_restringir,
                     contar_entidades, grados_de_libertad, resolver, sugerir_auto_restricciones)

__all__ = ["Boceto", "ErrorBoceto", "TIPOS_COTA", "TIPOS_RESTRICCION", "TIPOS_AUTO", "TOPE_TERMINAR_AUTO",
           "ResultadoAuto", "ResultadoSolver", "Sugerencia", "auto_restringir", "contar_entidades",
           "grados_de_libertad", "puntos_primitiva", "resolver", "sugerir_auto_restricciones"]
