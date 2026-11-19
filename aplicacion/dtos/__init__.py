"""DTOs (Data Transfer Objects) inmutables de la capa de aplicación.

Traza: ADR-002, AGENTS.md (Convenciones de código).
"""

from aplicacion.dtos.evaluacion_postulacion_dto import (
    DecisionEvaluacion,
    EvaluacionPostulacionRespuestaDTO,
    EvaluarPostulacionComando,
)
from aplicacion.dtos.postulacion_dto import (
    PostulacionRespuestaDTO,
    PostularEstudianteComando,
)

__all__ = [
    "PostularEstudianteComando",
    "PostulacionRespuestaDTO",
    "DecisionEvaluacion",
    "EvaluarPostulacionComando",
    "EvaluacionPostulacionRespuestaDTO",
]
