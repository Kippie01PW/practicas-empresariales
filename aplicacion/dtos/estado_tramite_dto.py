"""DTOs inmutables para consulta del estado del trámite en autoservicio (CU-11).

Traza: CU-11, OB-04, EAC-01, EAC-03, RT-01, RN-01, RN-02, RN-03, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007, ADR-008, ADR-010.

Define los objetos de transferencia de datos inmutables (dataclass con frozen=True y slots=True)
utilizados en las fronteras del caso de uso ConsultarEstadoTramiteCasoUso:
- ConsultarEstadoTramiteComando: DTO de entrada para consultar el estado del trámite de la práctica activa o más reciente.
- ResumenEvaluacionTramiteDTO: DTO con el estado de la evaluación de desempeño adaptado a la etapa del trámite.
- ResumenActaTramiteDTO: DTO con el estado de firmas electrónicas y metadatos del ActaFinal.
- EstadoTramitePracticaRespuestaDTO: DTO de salida con la proyección completa de solo lectura del estado del trámite.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True, slots=True)
class ConsultarEstadoTramiteComando:
    """Comando inmutable de entrada para consultar el estado del trámite de una práctica empresarial (CU-11).

    Atributos:
        actor_id: Identificador institucional del usuario autenticado que ejecuta la consulta.
        rol_actor: Rol institucional del usuario autenticado (uso exclusivo para 'Estudiante').
        estudiante_id: Identificador opcional del estudiante titular (si se omite, se asume actor_id).
        practica_id: Identificador opcional de la práctica a consultar (si se omite, se selecciona la activa o más reciente).
        ip_origen: Dirección IP del cliente para trazabilidad en la bitácora Append-Only (ADR-006).
    """

    actor_id: str
    rol_actor: str
    estudiante_id: Optional[str] = None
    practica_id: Optional[str] = None
    ip_origen: str = "127.0.0.1"

    def __post_init__(self) -> None:
        if not self.actor_id or not self.actor_id.strip():
            raise ValueError("El identificador del actor no puede estar vacío.")

        if not self.rol_actor or not self.rol_actor.strip():
            raise ValueError("El rol del actor no puede estar vacío.")

        if not self.ip_origen or not self.ip_origen.strip():
            raise ValueError("La dirección IP de origen no puede estar vacía.")

        object.__setattr__(self, "actor_id", self.actor_id.strip())
        object.__setattr__(self, "rol_actor", self.rol_actor.strip())
        object.__setattr__(self, "ip_origen", self.ip_origen.strip())

        if self.estudiante_id is not None:
            estudiante_limpio = self.estudiante_id.strip()
            object.__setattr__(self, "estudiante_id", estudiante_limpio if estudiante_limpio else None)

        if self.practica_id is not None:
            practica_limpia = self.practica_id.strip()
            object.__setattr__(self, "practica_id", practica_limpia if practica_limpia else None)


@dataclass(frozen=True, slots=True)
class ResumenEvaluacionTramiteDTO:
    """DTO inmutable con el estado de la evaluación de desempeño adaptado a la etapa de la práctica.

    Mientras la práctica se encuentre en estado distinto a 'Completada' (por ejemplo, en 'Evaluada'),
    únicamente informa si la evaluación fue realizada y su fecha, manteniendo ocultos la calificación
    cuantitativa, las respuestas de la rúbrica y las observaciones del supervisor hasta que el acta
    final esté en firme y la práctica alcance el estado 'Completada'.

    Atributos:
        evaluacion_realizada: Indica si ya existe una EvaluacionDesempeno registrada para la práctica.
        fecha_evaluacion: Fecha y hora en que el supervisor registró la evaluación (o None).
        calificacion_visible: Indica si el detalle de la calificación es visible para el estudiante.
        calificacion_cuantitativa: Nota definitiva calculada (solo presente cuando estado_actual == 'Completada').
        es_aprobatoria: Concepto de aprobación (solo presente cuando estado_actual == 'Completada').
        observaciones: Comentarios cualitativos del supervisor (solo presente cuando estado_actual == 'Completada').
        respuestas_rubrica: Desglose de calificaciones por criterio (solo presente cuando estado_actual == 'Completada').
    """

    evaluacion_realizada: bool
    fecha_evaluacion: Optional[datetime] = None
    calificacion_visible: bool = False
    calificacion_cuantitativa: Optional[float] = None
    es_aprobatoria: Optional[bool] = None
    observaciones: Optional[str] = None
    respuestas_rubrica: Optional[dict[str, float]] = None


@dataclass(frozen=True, slots=True)
class ResumenActaTramiteDTO:
    """DTO inmutable con el estado de firmas electrónicas y metadatos del ActaFinal en el estado del trámite.

    Atributos:
        acta_generada: Indica si ya se ha generado el documento ActaFinal para la práctica.
        aprobada_por_docente: Indica si cuenta con la aprobación electrónica del DocenteAsesor.
        aprobada_por_coordinador: Indica si cuenta con la aprobación electrónica del Coordinador de prácticas.
        acta_en_firme: Indica si ambas firmas electrónicas han sido asentadas.
        descarga_habilitada: Indica si el documento PDF oficial está habilitado para referencia o descarga.
        numero_acta: Código consecutivo oficial del acta final (o None).
        fecha_emision: Marca temporal de generación del acta (o None).
        ruta_archivo_pdf: Ruta o URI del archivo PDF oficial (expuesto para descarga en estado 'Completada').
        hash_integridad_sha256: Huella criptográfica SHA-256 del PDF (expuesta en estado 'Completada').
    """

    acta_generada: bool
    aprobada_por_docente: bool = False
    aprobada_por_coordinador: bool = False
    acta_en_firme: bool = False
    descarga_habilitada: bool = False
    numero_acta: Optional[str] = None
    fecha_emision: Optional[datetime] = None
    ruta_archivo_pdf: Optional[str] = None
    hash_integridad_sha256: Optional[str] = None


@dataclass(frozen=True, slots=True)
class EstadoTramitePracticaRespuestaDTO:
    """DTO inmutable de salida con la proyección completa de solo lectura del estado del trámite en autoservicio (CU-11).

    Atributos:
        practica_id: Identificador único de la práctica consultada.
        estudiante_id: Identificador del estudiante titular de la práctica.
        estado_actual: Estado formal actual del ciclo de vida en la máquina de estados (ADR-010).
        fecha_postulacion: Fecha y hora de radicación de la postulación.
        fecha_inicio: Fecha de inicio de la ejecución de la práctica (o None).
        fecha_fin: Fecha de cierre formal de la práctica al completarse (o None).
        regla_programa_id: Identificador de la versión de ReglaPrograma vinculada al iniciar (ADR-007).
        version_regla: Etiqueta de versión normativa de la ReglaPrograma vinculada.
        horas_requeridas: Total de horas exigidas por la ReglaPrograma vinculada (inmutable ante nuevas versiones).
        horas_acumuladas_aprobadas: Total de horas acumuladas en estado 'Aprobado'.
        horas_pendientes_validacion: Total de horas reportadas que se encuentran en estado 'Pendiente'.
        horas_restantes: Horas faltantes por aprobar para cumplir el requisito normativo.
        porcentaje_avance_horas: Porcentaje de avance de horas aprobadas frente a las horas requeridas.
        cantidad_reportes_pendientes: Número de reportes semanales en estado 'Pendiente' de validación.
        requisito_horas_cumplido: Indica si horas_acumuladas_aprobadas >= horas_requeridas.
        docente_asesor_id: Identificador del DocenteAsesor asignado (o None).
        nombre_docente_asesor: Nombre completo institucional del DocenteAsesor asignado (o None).
        correo_docente_asesor: Correo institucional de contacto del DocenteAsesor asignado (o None).
        supervisor_empresa_id: Identificador del SupervisorEmpresa vinculado a la práctica (o None).
        motivo_rechazo: Causal académica o justificación administrativa cuando estado_actual == 'Rechazada' (o None).
        evaluacion: Resumen inmutable del estado de la Evaluación de Desempeño.
        acta_final: Resumen inmutable del estado de firmas y metadatos del Acta Final.
        siguiente_paso: Descripción orientativa del siguiente hito esperado en el flujo de la práctica.
        mensaje: Mensaje descriptivo del resultado de la consulta en autoservicio.
    """

    practica_id: str
    estudiante_id: str
    estado_actual: str
    fecha_postulacion: datetime
    fecha_inicio: Optional[datetime]
    fecha_fin: Optional[datetime]
    regla_programa_id: str
    version_regla: str
    horas_requeridas: int
    horas_acumuladas_aprobadas: int
    horas_pendientes_validacion: int
    horas_restantes: int
    porcentaje_avance_horas: float
    cantidad_reportes_pendientes: int
    requisito_horas_cumplido: bool
    docente_asesor_id: Optional[str]
    nombre_docente_asesor: Optional[str]
    correo_docente_asesor: Optional[str]
    supervisor_empresa_id: Optional[str]
    motivo_rechazo: Optional[str]
    evaluacion: ResumenEvaluacionTramiteDTO
    acta_final: ResumenActaTramiteDTO
    siguiente_paso: str
    mensaje: str
