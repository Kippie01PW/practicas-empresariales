"""Entidad de dominio IntentoValidacion y enumeración ResultadoValidacionSia.

Traza: CU-01, EAC-02, RT-01, RT-03, ADR-001 (Resiliencia e integración asíncrona),
Vista Lógica §2, §3.

Modela el registro inmutable de cada intento de validación de requisitos
académicos frente al servicio del Sistema de Información Académica (SIA),
garantizando trazabilidad y tolerancia a fallos ante caídas o timeouts.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional


class ResultadoValidacionSia(Enum):
    """Resultados posibles de la consulta al servicio de Registro Académico (SIA)."""

    CUMPLE_REQUISITOS = "CumpleRequisitos"
    REQUISITOS_INCUMPLIDOS = "RequisitosIncumplidos"
    ERROR_COMUNICACION = "ErrorComunicacion"
    TIMEOUT = "Timeout"


class IntentoValidacion:
    """Entidad de dominio que modela un intento de verificación frente al SIA.

    Atributos del diagrama UML (01-logica.puml):
        - numeroIntento: Posición ordinal del intento (1 para sincrónico inicial, 2..5 para reintentos).
        - fechaIntento: Marca temporal del intento de verificación.
        - resultadoSia: Resultado retornado por el SIA o diagnóstico del fallo de comunicación.
        - detalleEstado: Descripción o causal detallada de incumplimiento o fallo técnico.

    Atributos de trazabilidad técnica (plan.md):
        - id: Identificador único del intento de validación.
        - practica_id: Identificador de la práctica asociada a la postulación.
        - exitoso: Indica si el intento concluyó con cumplimiento satisfactorio de requisitos.
    """

    __slots__ = (
        "_id",
        "_practica_id",
        "_numero_intento",
        "_fecha_intento",
        "_resultado_sia",
        "_exitoso",
        "_detalle_estado",
    )

    def __init__(
        self,
        *,
        practica_id: str,
        numero_intento: int = 1,
        resultado_sia: ResultadoValidacionSia | str,
        exitoso: bool,
        detalle_estado: Optional[str] = None,
        fecha_intento: Optional[datetime] = None,
        id: str | None = None,
    ) -> None:
        if not practica_id or not practica_id.strip():
            raise ValueError("El identificador de práctica no puede estar vacío.")
        if numero_intento < 1:
            raise ValueError("El número de intento debe ser mayor o igual a 1.")

        valor_resultado = (
            resultado_sia.value
            if isinstance(resultado_sia, ResultadoValidacionSia)
            else str(resultado_sia).strip()
        )
        if not valor_resultado:
            raise ValueError("El resultado del SIA no puede estar vacío.")

        self._id: str = id or str(uuid.uuid4())
        self._practica_id: str = practica_id.strip()
        self._numero_intento: int = numero_intento
        self._fecha_intento: datetime = fecha_intento or datetime.now()
        self._resultado_sia: str = valor_resultado
        self._exitoso: bool = exitoso
        self._detalle_estado: Optional[str] = detalle_estado.strip() if detalle_estado else None

    # -- Propiedades de solo lectura ----------------------------------------

    @property
    def id(self) -> str:
        return self._id

    @property
    def practica_id(self) -> str:
        return self._practica_id

    @property
    def numero_intento(self) -> int:
        return self._numero_intento

    @property
    def fecha_intento(self) -> datetime:
        return self._fecha_intento

    @property
    def resultado_sia(self) -> str:
        return self._resultado_sia

    @property
    def exitoso(self) -> bool:
        return self._exitoso

    @property
    def detalle_estado(self) -> Optional[str]:
        return self._detalle_estado

    # -- Métodos de negocio y fábrica ---------------------------------------

    def es_exitoso(self) -> bool:
        """Determina si la validación concluyó con cumplimiento de requisitos."""
        return self._exitoso

    @classmethod
    def crear_exitoso(
        cls,
        *,
        practica_id: str,
        numero_intento: int = 1,
        detalle_estado: Optional[str] = None,
        fecha_intento: Optional[datetime] = None,
    ) -> IntentoValidacion:
        """Fábrica para crear un intento exitoso que cumple requisitos académicos."""
        return cls(
            practica_id=practica_id,
            numero_intento=numero_intento,
            resultado_sia=ResultadoValidacionSia.CUMPLE_REQUISITOS,
            exitoso=True,
            detalle_estado=detalle_estado or "Requisitos académicos cumplidos satisfactoriamente.",
            fecha_intento=fecha_intento,
        )

    @classmethod
    def crear_rechazado(
        cls,
        *,
        practica_id: str,
        causal_incumplimiento: str,
        numero_intento: int = 1,
        fecha_intento: Optional[datetime] = None,
    ) -> IntentoValidacion:
        """Fábrica para registrar un intento donde no se cumplen los requisitos académicos."""
        if not causal_incumplimiento or not causal_incumplimiento.strip():
            raise ValueError("La causal de incumplimiento no puede estar vacía.")
        return cls(
            practica_id=practica_id,
            numero_intento=numero_intento,
            resultado_sia=ResultadoValidacionSia.REQUISITOS_INCUMPLIDOS,
            exitoso=False,
            detalle_estado=causal_incumplimiento.strip(),
            fecha_intento=fecha_intento,
        )

    @classmethod
    def crear_fallido(
        cls,
        *,
        practica_id: str,
        motivo_falla: str,
        numero_intento: int = 1,
        es_timeout: bool = False,
        fecha_intento: Optional[datetime] = None,
    ) -> IntentoValidacion:
        """Fábrica para registrar un fallo de comunicación o timeout con el SIA."""
        if not motivo_falla or not motivo_falla.strip():
            raise ValueError("El motivo de falla no puede estar vacío.")
        resultado = (
            ResultadoValidacionSia.TIMEOUT
            if es_timeout
            else ResultadoValidacionSia.ERROR_COMUNICACION
        )
        return cls(
            practica_id=practica_id,
            numero_intento=numero_intento,
            resultado_sia=resultado,
            exitoso=False,
            detalle_estado=motivo_falla.strip(),
            fecha_intento=fecha_intento,
        )

    # -- Representación e igualdad -----------------------------------------

    def __repr__(self) -> str:
        return (
            f"IntentoValidacion(id={self._id!r}, "
            f"practica_id={self._practica_id!r}, "
            f"intento={self._numero_intento}, "
            f"resultado={self._resultado_sia!r}, "
            f"exitoso={self._exitoso})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IntentoValidacion):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)
