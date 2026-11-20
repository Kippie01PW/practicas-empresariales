"""DTOs inmutables para el monitoreo del estado general de prácticas (CU-13).

Traza: CU-13, OB-01, OB-02, EAC-01, EAC-03, RT-01, RN-01, RN-02, RN-03, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007, ADR-008, ADR-010.

Define los objetos de transferencia de datos inmutables (dataclass con frozen=True y slots=True)
utilizados en las fronteras del caso de uso MonitorearPracticasCasoUso:
- ConsultarMonitoreoPracticasComando: DTO de entrada para consultar el tablero general de prácticas del programa académico del coordinador.
- ConsultarDetallePracticaMonitoreoComando: DTO de entrada para consultar la trazabilidad detallada de una práctica específica desde el tablero de monitoreo.
- IndicadorCargaDocenteDTO: DTO con el resumen de ocupación de cupo de un DocenteAsesor.
- ItemPracticaMonitoreoDTO: DTO con la fila consolidada de una Practica dentro del listado del tablero de monitoreo.
- TableroMonitoreoPracticasRespuestaDTO: DTO de salida con el tablero consolidado del monitoreo general de prácticas.
- DetallePracticaMonitoreoRespuestaDTO: DTO de salida con la trazabilidad completa de una práctica consultada desde el monitoreo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True, slots=True)
class ConsultarMonitoreoPracticasComando:
    """Comando inmutable de entrada para consultar el tablero de monitoreo general de prácticas (CU-13).

    Atributos:
        actor_id: Identificador institucional del coordinador autenticado que ejecuta la consulta.
        rol_actor: Rol institucional del usuario autenticado (uso exclusivo para 'Coordinador de prácticas').
        programa_academico_coordinador: Programa académico al que pertenece el coordinador autenticado.
        filtro_documento_estudiante: Filtro opcional por documento o identificador del Estudiante (Escenario 2).
        filtro_estado_actual: Filtro opcional por valor de EstadoPractica (Escenario 3).
        filtro_docente_asesor_id: Filtro opcional por identificador del DocenteAsesor (Escenario 3).
        filtro_programa_academico: Filtro opcional de programa académico (si difiere del programa del coordinador, se rechaza por pertenencia contextual, Escenario 5).
        ip_origen: Dirección IP del cliente para trazabilidad en la bitácora Append-Only (ADR-006).
    """

    actor_id: str
    rol_actor: str
    programa_academico_coordinador: str
    filtro_documento_estudiante: Optional[str] = None
    filtro_estado_actual: Optional[str] = None
    filtro_docente_asesor_id: Optional[str] = None
    filtro_programa_academico: Optional[str] = None
    ip_origen: str = "127.0.0.1"

    def __post_init__(self) -> None:
        actor_limpio = self.actor_id.strip() if self.actor_id else ""
        rol_limpio = self.rol_actor.strip() if self.rol_actor else ""
        programa_limpio = (
            self.programa_academico_coordinador.strip()
            if self.programa_academico_coordinador
            else ""
        )
        ip_limpia = self.ip_origen.strip() if self.ip_origen else "127.0.0.1"

        object.__setattr__(self, "actor_id", actor_limpio)
        object.__setattr__(self, "rol_actor", rol_limpio)
        object.__setattr__(self, "programa_academico_coordinador", programa_limpio)
        object.__setattr__(self, "ip_origen", ip_limpia if ip_limpia else "127.0.0.1")

        if self.filtro_documento_estudiante is not None:
            doc_limpio = self.filtro_documento_estudiante.strip()
            object.__setattr__(
                self,
                "filtro_documento_estudiante",
                doc_limpio if doc_limpio else None,
            )

        if self.filtro_estado_actual is not None:
            estado_limpio = self.filtro_estado_actual.strip()
            object.__setattr__(
                self,
                "filtro_estado_actual",
                estado_limpio if estado_limpio else None,
            )

        if self.filtro_docente_asesor_id is not None:
            docente_limpio = self.filtro_docente_asesor_id.strip()
            object.__setattr__(
                self,
                "filtro_docente_asesor_id",
                docente_limpio if docente_limpio else None,
            )

        if self.filtro_programa_academico is not None:
            prog_filtro_limpio = self.filtro_programa_academico.strip()
            object.__setattr__(
                self,
                "filtro_programa_academico",
                prog_filtro_limpio if prog_filtro_limpio else None,
            )


@dataclass(frozen=True, slots=True)
class ConsultarDetallePracticaMonitoreoComando:
    """Comando inmutable de entrada para consultar el detalle de una práctica desde el tablero de monitoreo (CU-13).

    Atributos:
        practica_id: Identificador único de la práctica a consultar.
        actor_id: Identificador institucional del coordinador autenticado.
        rol_actor: Rol institucional del actor (uso exclusivo para 'Coordinador de prácticas').
        programa_academico_coordinador: Programa académico al que pertenece el coordinador autenticado.
        ip_origen: Dirección IP del cliente para trazabilidad en la bitácora Append-Only (ADR-006).
    """

    practica_id: str
    actor_id: str
    rol_actor: str
    programa_academico_coordinador: str
    ip_origen: str = "127.0.0.1"

    def __post_init__(self) -> None:
        if not self.practica_id or not self.practica_id.strip():
            raise ValueError("El identificador de la práctica no puede estar vacío.")

        practica_limpia = self.practica_id.strip()
        actor_limpio = self.actor_id.strip() if self.actor_id else ""
        rol_limpio = self.rol_actor.strip() if self.rol_actor else ""
        programa_limpio = (
            self.programa_academico_coordinador.strip()
            if self.programa_academico_coordinador
            else ""
        )
        ip_limpia = self.ip_origen.strip() if self.ip_origen else "127.0.0.1"

        object.__setattr__(self, "practica_id", practica_limpia)
        object.__setattr__(self, "actor_id", actor_limpio)
        object.__setattr__(self, "rol_actor", rol_limpio)
        object.__setattr__(self, "programa_academico_coordinador", programa_limpio)
        object.__setattr__(self, "ip_origen", ip_limpia if ip_limpia else "127.0.0.1")


@dataclass(frozen=True, slots=True)
class IndicadorCargaDocenteDTO:
    """DTO inmutable con el resumen de ocupación de cupo de un DocenteAsesor en el tablero de monitoreo.

    Atributos:
        docente_asesor_id: Identificador único del docente asesor.
        documento: Documento de identidad del docente asesor.
        nombre_completo: Nombre institucional completo del docente asesor.
        correo_institucional: Correo electrónico institucional del docente asesor.
        cupo_maximo_practicas: Límite máximo de prácticas activas simultáneas (por defecto 10, RT-01).
        practicas_activas: Cantidad de prácticas activas asignadas actualmente.
        cupos_disponibles: Cupos restantes disponibles (cupo_maximo_practicas - practicas_activas).
        activo: Indica si el docente asesor se encuentra habilitado para asignaciones.
    """

    docente_asesor_id: str
    documento: str
    nombre_completo: str
    correo_institucional: str
    cupo_maximo_practicas: int
    practicas_activas: int
    cupos_disponibles: int
    activo: bool


@dataclass(frozen=True, slots=True)
class ItemPracticaMonitoreoDTO:
    """DTO inmutable con la fila consolidada de una Practica dentro del listado del tablero de monitoreo (CU-13).

    Atributos:
        practica_id: Identificador único de la práctica.
        documento_estudiante: Documento o identificador del Estudiante titular de la práctica.
        programa_academico: Programa académico de la ReglaPrograma vinculada.
        regla_programa_id: Identificador de la versión de ReglaPrograma vinculada al iniciar (ADR-007).
        version_regla: Etiqueta de versión normativa de la ReglaPrograma vinculada.
        estado_actual: Estado formal actual del ciclo de vida en la máquina de estados (ADR-010).
        fecha_postulacion: Fecha y hora de radicación de la postulación.
        fecha_inicio: Fecha de inicio de la ejecución de la práctica (o None).
        fecha_fin: Fecha de cierre formal de la práctica al completarse (o None).
        docente_asesor_id: Identificador del DocenteAsesor asignado (o None).
        nombre_docente_asesor: Nombre completo institucional del DocenteAsesor asignado (o None).
        supervisor_empresa_id: Identificador del SupervisorEmpresa vinculado a la práctica (o None).
        horas_requeridas: Total de horas exigidas por la ReglaPrograma vinculada (inmutable ante nuevas versiones, EAC-01).
        horas_acumuladas_aprobadas: Total de horas acumuladas en estado 'Aprobado'.
        horas_pendientes_validacion: Total de horas reportadas en estado 'Pendiente'.
        horas_restantes: Horas faltantes por aprobar para cumplir el requisito normativo.
        porcentaje_avance_horas: Porcentaje de avance de horas aprobadas frente a las horas requeridas.
        requisito_horas_cumplido: Indica si horas_acumuladas_aprobadas >= horas_requeridas.
        evaluacion_realizada: Indica si ya existe una EvaluacionDesempeno registrada.
        calificacion_cuantitativa: Calificación cuantitativa de la EvaluacionDesempeno (o None).
        acta_generada: Indica si ya se ha generado el ActaFinal de la práctica.
        numero_acta: Código consecutivo oficial del ActaFinal (o None).
        aprobada_por_docente: Indica si el ActaFinal cuenta con la firma electrónica del DocenteAsesor.
        aprobada_por_coordinador: Indica si el ActaFinal cuenta con la firma electrónica del Coordinador.
        acta_en_firme: Indica si ambas firmas electrónicas han sido asentadas en el ActaFinal.
    """

    practica_id: str
    documento_estudiante: str
    programa_academico: str
    regla_programa_id: str
    version_regla: str
    estado_actual: str
    fecha_postulacion: datetime
    fecha_inicio: Optional[datetime]
    fecha_fin: Optional[datetime]
    docente_asesor_id: Optional[str]
    nombre_docente_asesor: Optional[str]
    supervisor_empresa_id: Optional[str]
    horas_requeridas: int
    horas_acumuladas_aprobadas: int
    horas_pendientes_validacion: int
    horas_restantes: int
    porcentaje_avance_horas: float
    requisito_horas_cumplido: bool
    evaluacion_realizada: bool
    calificacion_cuantitativa: Optional[float]
    acta_generada: bool
    numero_acta: Optional[str]
    aprobada_por_docente: bool
    aprobada_por_coordinador: bool
    acta_en_firme: bool


@dataclass(frozen=True, slots=True)
class TableroMonitoreoPracticasRespuestaDTO:
    """DTO inmutable de salida con el tablero consolidado del monitoreo general de prácticas (CU-13).

    Atributos:
        programa_academico: Programa académico del coordinador al cual está restringido el monitoreo.
        total_practicas_programa: Total de prácticas registradas en el programa académico del coordinador.
        total_practicas_filtradas: Total de prácticas que coinciden con los filtros aplicados.
        resumen_por_estado: Conteo de prácticas agrupadas por cada uno de los 8 valores de EstadoPractica.
        carga_docentes: Tupla inmutable con los indicadores de ocupación de cupo de los docentes asesores.
        practicas: Tupla inmutable con las filas consolidadas de las prácticas del programa académico.
        mensaje: Mensaje descriptivo del resultado de la consulta de monitoreo.
    """

    programa_academico: str
    total_practicas_programa: int
    total_practicas_filtradas: int
    resumen_por_estado: dict[str, int]
    carga_docentes: tuple[IndicadorCargaDocenteDTO, ...]
    practicas: tuple[ItemPracticaMonitoreoDTO, ...]
    mensaje: str


@dataclass(frozen=True, slots=True)
class DetallePracticaMonitoreoRespuestaDTO:
    """DTO inmutable de salida con la trazabilidad completa de una práctica consultada desde el monitoreo (CU-13).

    Atributos:
        practica_id: Identificador único de la práctica consultada.
        documento_estudiante: Documento o identificador del Estudiante titular de la práctica.
        programa_academico: Programa académico de la ReglaPrograma vinculada.
        regla_programa_id: Identificador de la versión de ReglaPrograma vinculada al iniciar (ADR-007).
        version_regla: Etiqueta de versión normativa de la ReglaPrograma vinculada.
        estado_actual: Estado formal actual del ciclo de vida en la máquina de estados (ADR-010).
        fecha_postulacion: Fecha y hora de radicación de la postulación.
        fecha_inicio: Fecha de inicio de la ejecución de la práctica (o None).
        fecha_fin: Fecha de cierre formal de la práctica al completarse (o None).
        docente_asesor_id: Identificador del DocenteAsesor asignado (o None).
        nombre_docente_asesor: Nombre completo institucional del DocenteAsesor asignado (o None).
        correo_docente_asesor: Correo institucional de contacto del DocenteAsesor asignado (o None).
        supervisor_empresa_id: Identificador del SupervisorEmpresa vinculado a la práctica (o None).
        horas_requeridas: Total de horas exigidas por la ReglaPrograma vinculada (inmutable ante nuevas versiones).
        horas_acumuladas_aprobadas: Total de horas acumuladas en estado 'Aprobado'.
        horas_pendientes_validacion: Total de horas reportadas en estado 'Pendiente'.
        horas_restantes: Horas faltantes por aprobar para cumplir el requisito normativo.
        porcentaje_avance_horas: Porcentaje de avance de horas aprobadas frente a las horas requeridas.
        cantidad_reportes_pendientes: Número de reportes semanales en estado 'Pendiente' de validación.
        requisito_horas_cumplido: Indica si horas_acumuladas_aprobadas >= horas_requeridas.
        motivo_rechazo: Causal académica o justificación administrativa cuando estado_actual == 'Rechazada' (o None).
        evaluacion_realizada: Indica si ya existe una EvaluacionDesempeno registrada.
        calificacion_cuantitativa: Calificación cuantitativa de la EvaluacionDesempeno (o None).
        es_aprobatoria: Concepto de aprobación de la evaluación de desempeño (o None).
        observaciones_evaluacion: Observaciones cualitativas de la evaluación de desempeño (o None).
        fecha_evaluacion: Fecha y hora en que el supervisor registró la evaluación (o None).
        acta_generada: Indica si ya se ha generado el ActaFinal de la práctica.
        numero_acta: Código consecutivo oficial del ActaFinal (o None).
        fecha_emision_acta: Fecha y hora de generación del ActaFinal (o None).
        aprobada_por_docente: Indica si el ActaFinal cuenta con la firma electrónica del DocenteAsesor.
        aprobada_por_coordinador: Indica si el ActaFinal cuenta con la firma electrónica del Coordinador.
        acta_en_firme: Indica si ambas firmas electrónicas han sido asentadas en el ActaFinal.
        hash_integridad_sha256: Huella criptográfica SHA-256 del PDF del ActaFinal (o None).
        ultimo_resultado_sia: Resultado del último IntentoValidacion frente al SIA (o None).
        ultimo_detalle_sia: Detalle del último IntentoValidacion frente al SIA (o None).
        mensaje: Mensaje descriptivo del resultado de la consulta de detalle en monitoreo.
    """

    practica_id: str
    documento_estudiante: str
    programa_academico: str
    regla_programa_id: str
    version_regla: str
    estado_actual: str
    fecha_postulacion: datetime
    fecha_inicio: Optional[datetime]
    fecha_fin: Optional[datetime]
    docente_asesor_id: Optional[str]
    nombre_docente_asesor: Optional[str]
    correo_docente_asesor: Optional[str]
    supervisor_empresa_id: Optional[str]
    horas_requeridas: int
    horas_acumuladas_aprobadas: int
    horas_pendientes_validacion: int
    horas_restantes: int
    porcentaje_avance_horas: float
    cantidad_reportes_pendientes: int
    requisito_horas_cumplido: bool
    motivo_rechazo: Optional[str]
    evaluacion_realizada: bool
    calificacion_cuantitativa: Optional[float]
    es_aprobatoria: Optional[bool]
    observaciones_evaluacion: Optional[str]
    fecha_evaluacion: Optional[datetime]
    acta_generada: bool
    numero_acta: Optional[str]
    fecha_emision_acta: Optional[datetime]
    aprobada_por_docente: bool
    aprobada_por_coordinador: bool
    acta_en_firme: bool
    hash_integridad_sha256: Optional[str]
    ultimo_resultado_sia: Optional[str]
    ultimo_detalle_sia: Optional[str]
    mensaje: str
