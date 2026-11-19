"""DTOs inmutables para comando y respuestas de registro de horas de práctica.

Traza: CU-04, EAC-03, RT-01, RN-01, RN-02, RN-03, ADR-002, ADR-005, ADR-006, ADR-010.

Define los objetos de transferencia de datos inmutables (dataclass con frozen=True y slots=True)
utilizados en las fronteras del caso de uso RegistrarHorasCasoUso:
- RegistrarHorasComando: DTO de entrada con los datos del reporte semanal y contexto de seguridad.
- RegistroHorasRespuestaDTO: DTO de salida entregado al estudiante con el estado del reporte y la práctica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class RegistrarHorasComando:
    """Comando inmutable con los datos requeridos para registrar horas semanales.

    Atributos:
        - practica_id: Identificador único de la práctica a la que se reportan horas.
        - semana: Número de semana ordinal del reporte.
        - cantidad_horas: Cantidad de horas dedicadas en la semana.
        - descripcion_actividades: Descripción detallada de actividades realizadas.
        - actor_id: Identificador del usuario que ejecuta la acción (Estudiante).
        - rol_actor: Rol autenticado del actor (debe ser Estudiante).
        - ip_origen: Dirección IP desde la cual se emite la solicitud (para auditoría).
    """

    practica_id: str
    semana: int
    cantidad_horas: int
    descripcion_actividades: str
    actor_id: str = "estudiante_001"
    rol_actor: str = "Estudiante"
    ip_origen: str = "127.0.0.1"

    def __post_init__(self) -> None:
        if not self.practica_id or not self.practica_id.strip():
            raise ValueError("El identificador de la práctica no puede estar vacío.")

        if not self.actor_id or not self.actor_id.strip():
            raise ValueError("El identificador del actor no puede estar vacío.")

        if not self.rol_actor or not self.rol_actor.strip():
            raise ValueError("El rol del actor no puede estar vacío.")

        if not self.ip_origen or not self.ip_origen.strip():
            raise ValueError("La dirección IP de origen no puede estar vacía.")

        object.__setattr__(self, "practica_id", self.practica_id.strip())
        object.__setattr__(self, "actor_id", self.actor_id.strip())
        object.__setattr__(self, "rol_actor", self.rol_actor.strip())
        object.__setattr__(self, "ip_origen", self.ip_origen.strip())


@dataclass(frozen=True, slots=True)
class RegistroHorasRespuestaDTO:
    """DTO inmutable con la confirmación tras el registro de horas semanales.

    Atributos:
        - exito: Indica si el reporte fue registrado satisfactoriamente.
        - registro_horas_id: Identificador del reporte semanal creado (o None si falló).
        - practica_id: Identificador de la práctica intervenida.
        - semana: Número de semana reportada.
        - cantidad_horas: Cantidad de horas reportadas.
        - descripcion_actividades: Descripción de actividades reportadas.
        - estado_validacion: Estado del reporte (e.g. 'Pendiente', 'Aprobado', 'Rechazado').
        - estado_practica: Estado actual de la práctica (e.g. 'EnEjecucion', 'Asignada').
        - mensaje: Mensaje descriptivo para la interfaz de usuario / estudiante.
        - fecha_registro: Fecha y hora en que se asentó el registro.
        - detalles: Diccionario opcional para metadatos o diagnósticos adicionales.
    """

    exito: bool
    registro_horas_id: Optional[str]
    practica_id: str
    semana: int
    cantidad_horas: int
    descripcion_actividades: str
    estado_validacion: str
    estado_practica: str
    mensaje: str
    fecha_registro: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    detalles: Optional[dict[str, Any]] = None

    @classmethod
    def exitosa(
        cls,
        *,
        registro_horas_id: str,
        practica_id: str,
        semana: int,
        cantidad_horas: int,
        descripcion_actividades: str,
        estado_validacion: str,
        estado_practica: str,
        mensaje: str,
        fecha_registro: Optional[datetime] = None,
        detalles: Optional[dict[str, Any]] = None,
    ) -> RegistroHorasRespuestaDTO:
        return cls(
            exito=True,
            registro_horas_id=registro_horas_id,
            practica_id=practica_id,
            semana=semana,
            cantidad_horas=cantidad_horas,
            descripcion_actividades=descripcion_actividades,
            estado_validacion=estado_validacion,
            estado_practica=estado_practica,
            mensaje=mensaje,
            fecha_registro=fecha_registro or datetime.now(timezone.utc),
            detalles=detalles,
        )

    @classmethod
    def fallida(
        cls,
        *,
        practica_id: str,
        semana: int,
        cantidad_horas: int,
        descripcion_actividades: str,
        estado_practica: str,
        mensaje: str,
        detalles: Optional[dict[str, Any]] = None,
    ) -> RegistroHorasRespuestaDTO:
        return cls(
            exito=False,
            registro_horas_id=None,
            practica_id=practica_id,
            semana=semana,
            cantidad_horas=cantidad_horas,
            descripcion_actividades=descripcion_actividades,
            estado_validacion="",
            estado_practica=estado_practica,
            mensaje=mensaje,
            detalles=detalles,
        )
