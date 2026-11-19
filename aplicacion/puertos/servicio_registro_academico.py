"""Puerto de integración para el servicio externo de Registro Académico (SIA).

Traza: CU-01, EAC-02, RT-01, RT-03, ADR-001 (Resiliencia e integración asíncrona),
ADR-002 (Clean Architecture y Puertos y Adaptadores), Vista Lógica §2, Vista de Procesos §2.

Define el contrato formal (Protocol) para consultar los requisitos académicos de los
estudiantes solicitantes al Sistema de Información Académica (SIA), junto con las
estructuras de datos inmutables de resultado y las excepciones especializadas para
timeout (> 5 s) e indisponibilidad del servicio externo (Circuit Breaker).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Excepciones del puerto de Registro Académico (ADR-001, RT-03, EAC-02)
# ---------------------------------------------------------------------------

class ErrorRegistroAcademico(Exception):
    """Excepción base para fallos en la comunicación con el servicio de Registro Académico."""

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje: str = mensaje

    def __str__(self) -> str:
        return self.mensaje

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(mensaje={self.mensaje!r})"


class TimeoutRegistroAcademicoError(ErrorRegistroAcademico):
    """Lanzada cuando el SIA excede la ventana de tiempo de espera máxima (5 segundos).

    Traza: CU-01, EAC-02, RT-03, ADR-001, spec.md Escenario 5.
    """

    def __init__(
        self,
        documento_estudiante: str,
        timeout_segundos: float = 5.0,
        mensaje: Optional[str] = None,
    ) -> None:
        self.documento_estudiante: str = documento_estudiante
        self.timeout_segundos: float = timeout_segundos
        if mensaje is None:
            mensaje = (
                f"Tiempo de espera agotado ({timeout_segundos}s) al consultar requisitos "
                f"académicos para el estudiante con documento '{documento_estudiante}'."
            )
        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"TimeoutRegistroAcademicoError("
            f"documento_estudiante={self.documento_estudiante!r}, "
            f"timeout_segundos={self.timeout_segundos})"
        )


class IndisponibilidadRegistroAcademicoError(ErrorRegistroAcademico):
    """Lanzada cuando el SIA responde con error 5xx, caída de red o Circuit Breaker abierto.

    Traza: CU-01, EAC-02, ADR-001, spec.md Escenario 5.
    """

    def __init__(
        self,
        documento_estudiante: str,
        causa: Optional[str] = None,
        circuit_breaker_abierto: bool = False,
        mensaje: Optional[str] = None,
    ) -> None:
        self.documento_estudiante: str = documento_estudiante
        self.causa: Optional[str] = causa
        self.circuit_breaker_abierto: bool = circuit_breaker_abierto
        if mensaje is None:
            detalle_cb = " (Circuit Breaker ABIERTO)" if circuit_breaker_abierto else ""
            detalle_causa = f": {causa}" if causa else ""
            mensaje = (
                f"Servicio de Registro Académico no disponible{detalle_cb} al consultar "
                f"estudiante '{documento_estudiante}'{detalle_causa}."
            )
        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"IndisponibilidadRegistroAcademicoError("
            f"documento_estudiante={self.documento_estudiante!r}, "
            f"circuit_breaker_abierto={self.circuit_breaker_abierto!r}, "
            f"causa={self.causa!r})"
        )


# ---------------------------------------------------------------------------
# DTO de Resultado de Validación Académica
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ResultadoRequisitosAcademicos:
    """Resultado inmutable de la consulta de requisitos académicos al SIA.

    Atributos:
        - cumple_requisitos: True si el estudiante satisface todos los requisitos
          académicos reglamentarios para realizar la práctica empresarial.
        - causal_incumplimiento: Descripción o motivo académico específico cuando no cumple
          (ej. "Porcentaje de avance insuficiente: 65% requerido 80%", "Asignaturas previas pendientes").
        - creditos_aprobados: Cantidad de créditos cursados y aprobados reportados por el SIA.
        - porcentaje_avance: Porcentaje de avance de carrera reportado (0.0 a 100.0).
        - detalles: Metadatos o información adicional retornada por el SIA.
    """

    cumple_requisitos: bool
    causal_incumplimiento: Optional[str] = None
    creditos_aprobados: Optional[int] = None
    porcentaje_avance: Optional[float] = None
    detalles: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.cumple_requisitos and (
            not self.causal_incumplimiento or not self.causal_incumplimiento.strip()
        ):
            raise ValueError(
                "Debe indicarse una causal de incumplimiento cuando cumple_requisitos es False."
            )
        if self.causal_incumplimiento is not None:
            object.__setattr__(self, "causal_incumplimiento", self.causal_incumplimiento.strip())

    @classmethod
    def cumple(
        cls,
        *,
        creditos_aprobados: Optional[int] = None,
        porcentaje_avance: Optional[float] = None,
        detalles: Optional[dict[str, Any]] = None,
    ) -> ResultadoRequisitosAcademicos:
        """Crea un resultado exitoso de cumplimiento de requisitos académicos (Escenario 1)."""
        return cls(
            cumple_requisitos=True,
            causal_incumplimiento=None,
            creditos_aprobados=creditos_aprobados,
            porcentaje_avance=porcentaje_avance,
            detalles=detalles,
        )

    @classmethod
    def no_cumple(
        cls,
        *,
        causal: str,
        creditos_aprobados: Optional[int] = None,
        porcentaje_avance: Optional[float] = None,
        detalles: Optional[dict[str, Any]] = None,
    ) -> ResultadoRequisitosAcademicos:
        """Crea un resultado donde no se cumplen los requisitos académicos (Escenario 2)."""
        return cls(
            cumple_requisitos=False,
            causal_incumplimiento=causal,
            creditos_aprobados=creditos_aprobados,
            porcentaje_avance=porcentaje_avance,
            detalles=detalles,
        )


# ---------------------------------------------------------------------------
# Puerto de Salida: Protocol ServicioRegistroAcademicoPort
# ---------------------------------------------------------------------------

@runtime_checkable
class ServicioRegistroAcademicoPort(Protocol):
    """Puerto de salida hacia el Sistema de Información Académica (SIA).

    Define la operación requerida para verificar el cumplimiento de los
    requisitos académicos del estudiante (CU-01, spec.md Escenarios 1, 2, 5, 6, 7).
    """

    def consultar_requisitos_academicos(
        self, documento_estudiante: str
    ) -> ResultadoRequisitosAcademicos:
        """Consulta si un estudiante cumple los requisitos académicos para iniciar práctica.

        Args:
            documento_estudiante: Documento de identidad del estudiante a consultar.

        Returns:
            ResultadoRequisitosAcademicos indicando si cumple o la causal de incumplimiento.

        Raises:
            TimeoutRegistroAcademicoError: Si la consulta excede la ventana de 5 segundos (RT-03).
            IndisponibilidadRegistroAcademicoError: Si el SIA responde con error 5xx, fallo de red
                o si el Circuit Breaker se encuentra en estado abierto (ADR-001).
        """
        ...
