# -*- coding: utf-8 -*-
"""Kernel de restricciones: modelo de boceto 2D + solver numérico."""
from .boceto import Boceto, ErrorBoceto, TIPOS_COTA, TIPOS_RESTRICCION, puntos_primitiva
from .solver import ResultadoSolver, auto_restringir, grados_de_libertad, resolver

__all__ = ["Boceto", "ErrorBoceto", "TIPOS_COTA", "TIPOS_RESTRICCION", "ResultadoSolver",
           "auto_restringir", "grados_de_libertad", "puntos_primitiva", "resolver"]
