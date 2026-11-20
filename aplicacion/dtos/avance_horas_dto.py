"""DTOs inmutables para consulta individual y consolidada de avances de horas (CU-06).

Traza: CU-06, EAC-01, EAC-03, RT-01, RN-01, RN-02, RN-03, ADR-002, ADR-004, ADR-005, ADR-006, ADR-007, ADR-010.

Define los objetos de transferencia de datos inmutables (dataclass con frozen=True y slots=True)
utilizados en las fronteras del caso de uso RevisarAvancesHorasCasoUso:
- ConsultarAvanceHorasComando: DTO de entrada para consultar el detalle de avance de una práctica.
- ConsultarAvancesDocenteComando: DTO de entrada para la consulta consolidada del docente asesor.
- DetalleReporteHorasDTO: DTO con el detalle de cada reporte semanal en modo solo lectura.
- AvanceHorasPracticaRespuestaDTO: DTO de salida con el resumen y desglose del avance de una práctica.
- ResumenAvancePracticaDTO: DTO con el resumen de una práctica dentro del listado consolidado.
- ListadoAvancesDocenteRespuestaDTO: DTO de salida para la consulta consolidada del docente asesor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True, slots=True)
class ConsultarAvanceHorasComando:
    """Comando inmutable de entrada para consultar el detalle de avance de horas de una práctica.

    Atributos:
        practica_id: Identificador único de la práctica a consultar.
        actor_id: Identificador del usuario que ejecuta la consulta (DocenteAsesor o Estudiante).
        rol_actor: Rol autenticado del actor.
        ip_origen: Dirección IP desde la cual se emite la solicitud (para auditoría en bitácora).
    """

    practica_id: str
    actor_id: str
    rol_actor: str
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
class ConsultarAvancesDocenteComando:
    """Comando inmutable de entrada para la consulta consolidada de prácticas de un docente asesor.

    Atributos:
        docente_asesor_id: Identificador único del docente asesor cuyas prácticas se consultan.
        actor_id: Identificador del usuario autenticado que ejecuta la consulta.
        rol_actor: Rol autenticado del actor (debe ser DocenteAsesor / Docente).
        ip_origen: Dirección IP desde la cual se emite la solicitud (para auditoría en bitácora).
    """

    docente_asesor_id: str
    actor_id: str
    rol_actor: str
    ip_origen: str = "127.0.0.1"

    def __post_init__(self) -> None:
        if not self.docente_asesor_id or not self.docente_asesor_id.strip():
            raise ValueError("El identificador del docente asesor no puede estar vacío.")

        if not self.actor_id or not self.actor_id.strip():
            raise ValueError("El identificador del actor no puede estar vacío.")

        if not self.rol_actor or not self.rol_actor.strip():
            raise ValueError("El rol del actor no puede estar vacío.")

        if not self.ip_origen or not self.ip_origen.strip():
            raise ValueError("La dirección IP de origen no puede estar vacía.")

        object.__setattr__(self, "docente_asesor_id", self.docente_asesor_id.strip())
        object.__setattr__(self, "actor_id", self.actor_id.strip())
        object.__setattr__(self, "rol_actor", self.rol_actor.strip())
        object.__setattr__(self, "ip_origen", self.ip_origen.strip())


@dataclass(frozen=True, slots=True)
class DetalleReporteHorasDTO:
    """DTO inmutable con el detalle de cada reporte semanal de horas en modo solo lectura.

    Atributos:
        registro_horas_id: Identificador único del registro semanal de horas.
        semana: Número ordinal de la semana reportada.
        cantidad_horas: Cantidad de horas registradas en la semana.
        descripcion_actividades: Descripción de las actividades ejecutadas.
        estado_validacion: Estado de validación del reporte ('Pendiente', 'Aprobado' o 'Rechazado').
        observaciones_rechazo: Observaciones del supervisor cuando el reporte fue rechazado (o None).
        fecha_registro: Fecha y hora en que el estudiante registró el reporte.
    """

    registro_horas_id: str
    semana: int
    cantidad_horas: int
    descripcion_actividades: str
    estado_validacion: str
    observaciones_rechazo: Optional[str]
    fecha_registro: datetime


@dataclass(frozen=True, slots=True)
class AvanceHorasPracticaRespuestaDTO:
    """DTO inmutable de salida con el resumen y desglose completo del avance de horas de una práctica.

    Atributos:
        practica_id: Identificador único de la práctica consultada.
        estudiante_id: Identificador del estudiante titular de la práctica.
        docente_asesor_id: Identificador del docente asesor asignado (o None).
        estado_practica: Estado actual del ciclo de vida de la práctica.
        regla_programa_id: Identificador de la regla de programa vinculada a la práctica.
        version_regla: Versión normativa de la regla de programa vinculada.
        horas_requeridas: Cantidad total de horas exigidas por la regla de programa vinculada.
        horas_acumuladas_aprobadas: Total de horas en estado 'Aprobado'.
        horas_pendientes_validacion: Total de horas en estado 'Pendiente' de validación.
        horas_rechazadas: Total de horas en estado 'Rechazado'.
        horas_restantes: Cantidad de horas faltantes por aprobar para cumplir el requisito.
        porcentaje_avance: Porcentaje de progreso respecto a las horas requeridas (0.0 a 100.0+).
        requisito_horas_cumplido: Indica si horas_acumuladas_aprobadas >= horas_requeridas.
        reportes_semanales: Tupla inmutable con el desglose cronológico de los reportes semanales.
        mensaje: Mensaje descriptivo del resultado de la consulta.
    """

    practica_id: str
    estudiante_id: str
    docente_asesor_id: Optional[str]
    estado_practica: str
    regla_programa_id: str
    version_regla: str
    horas_requeridas: int
    horas_acumuladas_aprobadas: int
    horas_pendientes_validacion: int
    horas_rechazadas: int
    horas_restantes: int
    porcentaje_avance: float
    requisito_horas_cumplido: bool
    reportes_semanales: tuple[DetalleReporteHorasDTO, ...]
    mensaje: str


@dataclass(frozen=True, slots=True)
class ResumenAvancePracticaDTO:
    """DTO inmutable con el resumen de una práctica dentro del listado consolidado del docente asesor.

    Atributos:
        practica_id: Identificador único de la práctica.
        estudiante_id: Identificador del estudiante titular.
        estado_actual: Estado actual de la práctica.
        horas_acumuladas_aprobadas: Total de horas aprobadas acumuladas.
        horas_requeridas: Total de horas exigidas por la regla del programa vinculada.
        horas_restantes: Horas restantes por aprobar.
        porcentaje_avance: Porcentaje de avance frente a las horas requeridas.
        cantidad_reportes_pendientes: Número de reportes semanales en estado 'Pendiente'.
        requisito_horas_cumplido: Indica si la práctica alcanzó las horas requeridas.
    """

    practica_id: str
    estudiante_id: str
    estado_actual: str
    horas_acumuladas_aprobadas: int
    horas_requeridas: int
    horas_restantes: int
    porcentaje_avance: float
    cantidad_reportes_pendientes: int
    requisito_horas_cumplido: bool


@dataclass(frozen=True, slots=True)
class ListadoAvancesDocenteRespuestaDTO:
    """DTO inmutable de salida para la consulta consolidada de prácticas del docente asesor.

    Atributos:
        docente_asesor_id: Identificador del docente asesor consultado.
        total_practicas_asignadas: Cantidad total de prácticas bajo su tutoría.
        practicas: Tupla inmutable con los resúmenes de avance de cada práctica asignada.
        mensaje: Mensaje descriptivo del resultado de la consulta consolidada.
    """

    docente_asesor_id: str
    total_practicas_asignadas: int
    practicas: tuple[ResumenAvancePracticaDTO, ...]
    mensaje: str
