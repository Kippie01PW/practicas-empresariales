"""Entidad de dominio RegistroHoras.

Traza: CU-04, EAC-03, RT-01, RN-01, RN-02, RN-03, ADR-002, ADR-010, Vista Lógica §2.

Modela el reporte semanal de horas ejecutadas y actividades desarrolladas
por el estudiante durante su práctica empresarial.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from dominio.errores import (
    CantidadHorasInvalidaError,
    DescripcionActividadesRequeridaError,
    SemanaInvalidaError,
)


class EstadoValidacionHoras(str, Enum):
    """Estados del ciclo de vida y validación de un reporte semanal de horas."""

    PENDIENTE = "Pendiente"
    APROBADO = "Aprobado"
    RECHAZADO = "Rechazado"


class RegistroHoras:
    """Entidad de dominio que representa un reporte de horas semanal de una práctica.

    Atributos del diagrama UML (01-logica.puml) y del plan técnico:
        - id: Identificador único del reporte semanal.
        - practica_id: Identificador de la práctica a la que pertenece el reporte.
        - semana: Número ordinal de la semana ejecutada (entero >= 1).
        - cantidad_horas: Cantidad de horas reportadas en la semana (1 a 60 horas).
        - descripcion_actividades: Detalle descriptivo de las tareas y logros semanales.
        - estado_validacion: Estado de revisión por parte del supervisor (Pendiente/Aprobado/Rechazado).
        - fecha_registro: Marca temporal del momento en que se registró el reporte.
    """

    __slots__ = (
        "_id",
        "_practica_id",
        "_semana",
        "_cantidad_horas",
        "_descripcion_actividades",
        "_estado_validacion",
        "_fecha_registro",
    )

    def __init__(
        self,
        *,
        practica_id: str,
        semana: int,
        cantidad_horas: int,
        descripcion_actividades: str,
        estado_validacion: EstadoValidacionHoras = EstadoValidacionHoras.PENDIENTE,
        fecha_registro: Optional[datetime] = None,
        id: Optional[str] = None,
    ) -> None:
        if not practica_id or not practica_id.strip():
            raise ValueError("El identificador de la práctica es obligatorio.")

        if semana < 1:
            raise SemanaInvalidaError(semana=semana)

        if cantidad_horas <= 0 or cantidad_horas > 60:
            raise CantidadHorasInvalidaError(
                cantidad_horas=cantidad_horas,
                limite_maximo=60,
            )

        if not descripcion_actividades or not descripcion_actividades.strip():
            raise DescripcionActividadesRequeridaError()

        self._id: str = id or str(uuid.uuid4())
        self._practica_id: str = practica_id.strip()
        self._semana: int = semana
        self._cantidad_horas: int = cantidad_horas
        self._descripcion_actividades: str = descripcion_actividades.strip()
        self._estado_validacion: EstadoValidacionHoras = estado_validacion
        self._fecha_registro: datetime = fecha_registro or datetime.now(timezone.utc)

    # -- Propiedades de lectura ----------------------------------------------

    @property
    def id(self) -> str:
        return self._id

    @property
    def practica_id(self) -> str:
        return self._practica_id

    @property
    def semana(self) -> int:
        return self._semana

    @property
    def cantidad_horas(self) -> int:
        return self._cantidad_horas

    @property
    def descripcion_actividades(self) -> str:
        return self._descripcion_actividades

    @property
    def estado_validacion(self) -> EstadoValidacionHoras:
        return self._estado_validacion

    @property
    def fecha_registro(self) -> datetime:
        return self._fecha_registro

    # -- Métodos de mutación y transición de validación ----------------------

    def aprobar(self) -> None:
        """Marca el reporte de horas como Aprobado por el supervisor."""
        self._estado_validacion = EstadoValidacionHoras.APROBADO

    def rechazar(self) -> None:
        """Marca el reporte de horas como Rechazado por el supervisor."""
        self._estado_validacion = EstadoValidacionHoras.RECHAZADO

    def __repr__(self) -> str:
        return (
            f"RegistroHoras(id={self._id!r}, "
            f"practica_id={self._practica_id!r}, "
            f"semana={self._semana!r}, "
            f"cantidad_horas={self._cantidad_horas!r}, "
            f"estado_validacion={self._estado_validacion.value!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RegistroHoras):
            return False
        return self._id == other._id
