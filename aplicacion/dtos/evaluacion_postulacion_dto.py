"""DTOs inmutables para comando y respuesta de evaluación de postulación a práctica.

Traza: CU-02, EAC-03, RN-02, RN-03, ADR-002, ADR-005, ADR-006, ADR-010.

Define los objetos de transferencia de datos inmutables (dataclass con frozen=True y slots=True)
utilizados en las fronteras del caso de uso EvaluarPostulacionCasoUso:
- EvaluarPostulacionComando: DTO de entrada con la práctica a evaluar, la decisión (APROBAR/RECHAZAR),
  justificación obligatoria ante rechazo, e información de contexto para RBAC y auditoría.
- EvaluacionPostulacionRespuestaDTO: DTO de salida entregado al coordinador / UI con el nuevo estado
  de la práctica, mensaje descriptivo y marcas temporales.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from dominio.modelos.practica import EstadoPractica


# ---------------------------------------------------------------------------
# Enumeración de decisiones administrativas soportadas
# ---------------------------------------------------------------------------

class DecisionEvaluacion(str, Enum):
    """Decisiones administrativas formales que puede tomar la Coordinación de prácticas."""

    APROBAR = "APROBAR"
    RECHAZAR = "RECHAZAR"


# ---------------------------------------------------------------------------
# DTO de Entrada: Comando de Evaluación de Postulación
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EvaluarPostulacionComando:
    """Comando inmutable con los datos requeridos para evaluar una postulación.

    Atributos:
        - practica_id: Identificador único de la práctica a evaluar.
        - decision: Decisión tomada ("APROBAR" o "RECHAZAR").
        - motivo_rechazo: Justificación del rechazo (obligatoria si decision es RECHAZAR).
        - actor_id: Identificador del usuario que ejecuta la evaluación (Coordinador).
        - rol_actor: Rol autenticado del actor (debe ser Coordinador / Coordinador de prácticas).
        - ip_origen: Dirección IP desde la cual se emite la solicitud (para auditoría).
    """

    practica_id: str
    decision: str
    motivo_rechazo: Optional[str] = None
    actor_id: str = "coordinador_001"
    rol_actor: str = "Coordinador de prácticas"
    ip_origen: str = "127.0.0.1"

    def __post_init__(self) -> None:
        if not self.practica_id or not self.practica_id.strip():
            raise ValueError("El identificador de la práctica no puede estar vacío.")

        if not self.decision or not self.decision.strip():
            raise ValueError("La decisión de evaluación no puede estar vacía.")

        decision_upper = self.decision.strip().upper()
        if decision_upper not in {DecisionEvaluacion.APROBAR.value, DecisionEvaluacion.RECHAZAR.value}:
            raise ValueError(
                f"Decisión inválida '{self.decision}'. "
                f"Las decisiones permitidas son 'APROBAR' o 'RECHAZAR'."
            )

        if not self.actor_id or not self.actor_id.strip():
            raise ValueError("El identificador del actor no puede estar vacío.")

        if not self.rol_actor or not self.rol_actor.strip():
            raise ValueError("El rol del actor no puede estar vacío.")

        if not self.ip_origen or not self.ip_origen.strip():
            raise ValueError("La dirección IP de origen no puede estar vacía.")

        motivo_limpio = self.motivo_rechazo.strip() if self.motivo_rechazo else None

        object.__setattr__(self, "practica_id", self.practica_id.strip())
        object.__setattr__(self, "decision", decision_upper)
        object.__setattr__(self, "motivo_rechazo", motivo_limpio)
        object.__setattr__(self, "actor_id", self.actor_id.strip())
        object.__setattr__(self, "rol_actor", self.rol_actor.strip())
        object.__setattr__(self, "ip_origen", self.ip_origen.strip())

    @property
    def es_aprobacion(self) -> bool:
        """Indica si el comando representa una aprobación."""
        return self.decision == DecisionEvaluacion.APROBAR.value

    @property
    def es_rechazo(self) -> bool:
        """Indica si el comando representa un rechazo."""
        return self.decision == DecisionEvaluacion.RECHAZAR.value


# ---------------------------------------------------------------------------
# DTO de Salida: Respuesta de Evaluación de Postulación
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EvaluacionPostulacionRespuestaDTO:
    """DTO inmutable con la respuesta tras la evaluación de una postulación.

    Atributos:
        - exito: Indica si la operación de evaluación fue aplicada satisfactoriamente.
        - practica_id: Identificador de la práctica evaluada.
        - nuevo_estado: Estado resultante de la práctica ('Aprobada', 'Rechazada' o estado actual).
        - mensaje: Mensaje descriptivo para la interfaz de usuario.
        - fecha_evaluacion: Fecha y hora en que se asentó la decisión.
        - motivo_rechazo: Justificación registrada en caso de rechazo.
        - detalles: Diccionario opcional para metadatos o diagnósticos adicionales.
    """

    exito: bool
    practica_id: str
    nuevo_estado: str
    mensaje: str
    fecha_evaluacion: datetime = field(default_factory=datetime.now)
    motivo_rechazo: Optional[str] = None
    detalles: Optional[dict[str, Any]] = None

    @classmethod
    def aprobada(
        cls,
        *,
        practica_id: str,
        mensaje: str = "Postulación aprobada exitosamente.",
        detalles: Optional[dict[str, Any]] = None,
    ) -> EvaluacionPostulacionRespuestaDTO:
        """Crea una respuesta exitosa de aprobación (Escenario 1)."""
        return cls(
            exito=True,
            practica_id=practica_id,
            nuevo_estado=EstadoPractica.APROBADA.value,
            mensaje=mensaje,
            fecha_evaluacion=datetime.now(),
            motivo_rechazo=None,
            detalles=detalles,
        )

    @classmethod
    def rechazada(
        cls,
        *,
        practica_id: str,
        motivo_rechazo: str,
        mensaje: Optional[str] = None,
        detalles: Optional[dict[str, Any]] = None,
    ) -> EvaluacionPostulacionRespuestaDTO:
        """Crea una respuesta de rechazo justificado (Escenario 2)."""
        mensaje_final = mensaje or f"Postulación rechazada: {motivo_rechazo}"
        return cls(
            exito=True,
            practica_id=practica_id,
            nuevo_estado=EstadoPractica.RECHAZADA.value,
            mensaje=mensaje_final,
            fecha_evaluacion=datetime.now(),
            motivo_rechazo=motivo_rechazo,
            detalles=detalles,
        )

    @classmethod
    def denegada(
        cls,
        *,
        practica_id: str,
        estado_actual: str,
        mensaje: str,
        detalles: Optional[dict[str, Any]] = None,
    ) -> EvaluacionPostulacionRespuestaDTO:
        """Crea una respuesta denegada ante violaciones de negocio o máquina de estados."""
        return cls(
            exito=False,
            practica_id=practica_id,
            nuevo_estado=estado_actual,
            mensaje=mensaje,
            fecha_evaluacion=datetime.now(),
            motivo_rechazo=None,
            detalles=detalles,
        )
