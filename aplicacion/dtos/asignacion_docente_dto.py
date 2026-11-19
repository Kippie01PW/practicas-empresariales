"""DTOs inmutables para comando y respuestas de asignación de docente asesor.

Traza: CU-03, EAC-03, RT-01, RN-03, ADR-002, ADR-005, ADR-006, ADR-010.

Define los objetos de transferencia de datos inmutables (dataclass con frozen=True y slots=True)
utilizados en las fronteras del caso de uso AsignarDocenteAsesorCasoUso:
- AsignarDocenteComando: DTO de entrada con los identificadores de la práctica y del docente,
  más el contexto de seguridad RBAC y auditoría.
- AsignacionDocenteRespuestaDTO: DTO de salida entregado al coordinador / UI con el nuevo estado
  de la práctica, docente vinculado, mensaje descriptivo y marcas temporales.
- DocenteAsesorResumenDTO: DTO de consulta para consultar la carga y disponibilidad de tutores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from dominio.modelos.practica import EstadoPractica


# ---------------------------------------------------------------------------
# DTO de Entrada: Comando de Asignación de Docente Asesor
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AsignarDocenteComando:
    """Comando inmutable con los datos requeridos para asignar un docente asesor.

    Atributos:
        - practica_id: Identificador único de la práctica a asignar.
        - docente_asesor_id: Identificador único del docente asesor seleccionado.
        - actor_id: Identificador del usuario que ejecuta la asignación (Coordinador).
        - rol_actor: Rol autenticado del actor (debe ser Coordinador / Coordinador de prácticas).
        - ip_origen: Dirección IP desde la cual se emite la solicitud (para auditoría).
    """

    practica_id: str
    docente_asesor_id: str
    actor_id: str = "coordinador_001"
    rol_actor: str = "Coordinador de prácticas"
    ip_origen: str = "127.0.0.1"

    def __post_init__(self) -> None:
        if not self.practica_id or not self.practica_id.strip():
            raise ValueError("El identificador de la práctica no puede estar vacío.")

        if not self.docente_asesor_id or not self.docente_asesor_id.strip():
            raise ValueError("El identificador del docente asesor no puede estar vacío.")

        if not self.actor_id or not self.actor_id.strip():
            raise ValueError("El identificador del actor no puede estar vacío.")

        if not self.rol_actor or not self.rol_actor.strip():
            raise ValueError("El rol del actor no puede estar vacío.")

        if not self.ip_origen or not self.ip_origen.strip():
            raise ValueError("La dirección IP de origen no puede estar vacía.")

        object.__setattr__(self, "practica_id", self.practica_id.strip())
        object.__setattr__(self, "docente_asesor_id", self.docente_asesor_id.strip())
        object.__setattr__(self, "actor_id", self.actor_id.strip())
        object.__setattr__(self, "rol_actor", self.rol_actor.strip())
        object.__setattr__(self, "ip_origen", self.ip_origen.strip())


# ---------------------------------------------------------------------------
# DTO de Salida: Respuesta de Asignación de Docente Asesor
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AsignacionDocenteRespuestaDTO:
    """DTO inmutable con la confirmación tras la asignación de un docente asesor.

    Atributos:
        - exito: Indica si la asignación fue completada satisfactoriamente.
        - practica_id: Identificador de la práctica intervenida.
        - docente_asesor_id: Identificador del docente asesor asignado (o None si falló).
        - nuevo_estado: Estado resultante de la práctica ('Asignada' o estado previo).
        - mensaje: Mensaje descriptivo para la interfaz de usuario.
        - fecha_asignacion: Fecha y hora en que se asentó la asignación.
        - detalles: Diccionario opcional para metadatos o diagnósticos adicionales.
    """

    exito: bool
    practica_id: str
    docente_asesor_id: Optional[str]
    nuevo_estado: str
    mensaje: str
    fecha_asignacion: datetime = field(default_factory=datetime.now)
    detalles: Optional[dict[str, Any]] = None

    @classmethod
    def exitosa(
        cls,
        *,
        practica_id: str,
        docente_asesor_id: str,
        mensaje: str = "Docente asesor asignado exitosamente a la práctica.",
        detalles: Optional[dict[str, Any]] = None,
    ) -> AsignacionDocenteRespuestaDTO:
        """Crea una respuesta exitosa de asignación (Escenario 1)."""
        return cls(
            exito=True,
            practica_id=practica_id,
            docente_asesor_id=docente_asesor_id,
            nuevo_estado=EstadoPractica.ASIGNADA.value,
            mensaje=mensaje,
            fecha_asignacion=datetime.now(),
            detalles=detalles,
        )

    @classmethod
    def denegada(
        cls,
        *,
        practica_id: str,
        estado_actual: str,
        mensaje: str,
        docente_asesor_id: Optional[str] = None,
        detalles: Optional[dict[str, Any]] = None,
    ) -> AsignacionDocenteRespuestaDTO:
        """Crea una respuesta denegada ante cupo excedido, docente inexistente o error de estado."""
        return cls(
            exito=False,
            practica_id=practica_id,
            docente_asesor_id=docente_asesor_id,
            nuevo_estado=estado_actual,
            mensaje=mensaje,
            fecha_asignacion=datetime.now(),
            detalles=detalles,
        )


# ---------------------------------------------------------------------------
# DTO de Consulta: Resumen de Docente Asesor y Disponibilidad
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DocenteAsesorResumenDTO:
    """DTO inmutable para consulta de capacidad y tutorías activas de tutores."""

    id: str
    documento: str
    nombre_completo: str
    correo_institucional: str
    cupo_maximo: int
    practicas_activas: int
    cupo_disponible: int
    activo: bool
