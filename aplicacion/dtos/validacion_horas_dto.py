"""DTOs inmutables para el caso de uso ValidarHorasRegistradas (CU-05).

Traza: CU-05, EAC-03, RN-01, RN-02, ADR-002, ADR-004, ADR-005.

Define el comando de entrada (ValidarHorasComando) y el DTO de respuesta
(ValidacionHorasRespuestaDTO) del caso de uso ValidarHorasRegistradasCasoUso.
Ambos son estructuras inmutables (frozen dataclass) conforme a las convenciones
de AGENTS.md y al plan técnico de CU-05.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class ValidarHorasComando:
    """Comando inmutable de entrada para el caso de uso de validación de horas (CU-05).

    Encapsula todos los parámetros necesarios para que el supervisor de empresa
    apruebe o rechace un reporte semanal de horas de su practicante.

    Atributos:
        practica_id: Identificador de la práctica a la que pertenece el reporte.
        registro_horas_id: Identificador del reporte semanal de horas a validar.
        decision: Decisión del supervisor: ``"Aprobar"`` o ``"Rechazar"``.
        observaciones: Observaciones descriptivas del rechazo (obligatorio si
            decision=="Rechazar", RN-02). None si la decisión es Aprobar.
        token_acceso: Cadena criptográfica del Magic Link efímero presentado por
            el supervisor externo (ADR-004). None si se usa contexto RBAC.
        supervisor_id: Identificador del supervisor que ejerce la acción.
            Puede provenir del token (ADR-004) o del contexto RBAC (ADR-005).
        ip_origen: Dirección IP del cliente para trazabilidad y bitácora (ADR-006).
    """

    practica_id: str
    registro_horas_id: str
    decision: str
    observaciones: Optional[str] = None
    token_acceso: Optional[str] = None
    supervisor_id: Optional[str] = None
    ip_origen: str = "127.0.0.1"


@dataclass(frozen=True)
class ValidacionHorasRespuestaDTO:
    """DTO inmutable de respuesta del caso de uso de validación de horas (CU-05).

    Devuelve el resumen formal de la decisión de validación asentada por el
    supervisor de empresa, conforme al plan técnico (plan.md, 005).

    Atributos:
        registro_horas_id: Identificador del reporte semanal de horas evaluado.
        practica_id: Identificador de la práctica a la que pertenece el reporte.
        semana: Número ordinal de la semana evaluada.
        cantidad_horas: Cantidad de horas del reporte evaluado.
        estado_validacion: Estado resultante del reporte (``"Aprobado"`` o ``"Rechazado"``).
        horas_acumuladas_practica: Total de horas aprobadas acumuladas en la práctica
            tras la decisión (inalterado si la decisión fue Rechazar).
        observaciones: Observaciones de rechazo (None si fue aprobado).
        fecha_decision: Marca temporal de la decisión de validación.
        mensaje: Descripción legible del resultado de la operación.
    """

    registro_horas_id: str
    practica_id: str
    semana: int
    cantidad_horas: int
    estado_validacion: str
    horas_acumuladas_practica: int
    observaciones: Optional[str]
    fecha_decision: datetime
    mensaje: str
