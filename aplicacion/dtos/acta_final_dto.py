"""DTOs inmutables para el caso de uso GenerarActaFinalCasoUso (CU-09).

Traza: CU-09, EAC-01, EAC-03, OB-01, OB-05, PA-03, RN-01, RN-02, RN-03, ADR-002, ADR-003, ADR-005, ADR-006, ADR-007, ADR-008, ADR-010.

Define los objetos de transferencia de datos inmutables (dataclass con frozen=True y slots=True)
utilizados en las fronteras del caso de uso GenerarActaFinalCasoUso y sus puertos:
- DatosRenderizadoActaDTO: Datos consolidados de la práctica que se inyectan en la plantilla HTML/CSS de la ReglaPrograma vinculada.
- ResultadoRenderizadoPdfDTO: Resultado devuelto por el puerto ServicioGeneradorActaPdfPort tras renderizar el PDF y calcular su huella SHA-256.
- GenerarActaFinalComando: Comando de entrada para solicitar la generación del acta final por el DocenteAsesor.
- ActaFinalRespuestaDTO: Respuesta formal de salida con los metadatos del ActaFinal generada y su huella criptográfica SHA-256.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True, slots=True)
class DatosRenderizadoActaDTO:
    """DTO inmutable con los datos consolidados de la práctica para renderizar la plantilla del acta (CU-09).

    Contiene la información del Estudiante, DocenteAsesor, SupervisorEmpresa, versión original de
    ReglaPrograma vinculada a la práctica (ADR-007, EAC-01), horas acumuladas aprobadas y
    EvaluacionDesempeno (aprobatoria o reprobatoria con observaciones justificativas).

    Atributos:
        numero_acta: Consecutivo anual del acta con formato 'ACTA-<AÑO>-<NNNN>'.
        practica_id: Identificador único de la práctica empresarial.
        estudiante_id: Identificador del estudiante titular de la práctica.
        docente_asesor_id: Identificador del docente asesor asignado a la práctica.
        nombre_docente_asesor: Nombre completo del docente asesor asignado.
        supervisor_empresa_id: Identificador del supervisor de empresa que evaluó al practicante.
        regla_programa_id: Identificador de la versión de ReglaPrograma vinculada a la práctica.
        programa_academico: Nombre del programa académico asociado a la regla.
        version_regla: Versión normativa de la ReglaPrograma vinculada (EAC-01).
        plantilla_acta: Nombre o contenido de la plantilla HTML/CSS configurada en la regla (ADR-007, ADR-008).
        horas_requeridas: Horas mínimas exigidas por la ReglaPrograma vinculada.
        horas_acumuladas_aprobadas: Total de horas acumuladas en estado 'Aprobado' por la práctica.
        calificacion_cuantitativa: Calificación cuantitativa de la EvaluacionDesempeno (0.0 a 5.0).
        es_aprobatoria: Indica si la calificación cuantitativa es mayor o igual a 3.0.
        observaciones_evaluacion: Observaciones o concepto cualitativo de la evaluación de desempeño.
        respuestas_rubrica: Diccionario con las calificaciones registradas por criterio de la rúbrica.
        fecha_emision: Marca temporal oficial de emisión del acta final.
    """

    numero_acta: str
    practica_id: str
    estudiante_id: str
    docente_asesor_id: str
    nombre_docente_asesor: str
    supervisor_empresa_id: str
    regla_programa_id: str
    programa_academico: str
    version_regla: str
    plantilla_acta: str
    horas_requeridas: int
    horas_acumuladas_aprobadas: int
    calificacion_cuantitativa: float
    es_aprobatoria: bool
    observaciones_evaluacion: Optional[str]
    respuestas_rubrica: dict[str, float]
    fecha_emision: datetime


@dataclass(frozen=True, slots=True)
class ResultadoRenderizadoPdfDTO:
    """DTO inmutable con el resultado del renderizado HTML/CSS a PDF y su sellado SHA-256 (ADR-008).

    Atributos:
        ruta_archivo_pdf: Ruta confirmada donde quedó almacenado el binario PDF en el repositorio de actas.
        contenido_pdf: Contenido binario del documento PDF renderizado.
        hash_integridad_sha256: Huella criptográfica SHA-256 de 64 caracteres hexadecimales calculada sobre contenido_pdf.
        plantilla_utilizada: Identificador o nombre de la plantilla HTML/CSS empleada en el renderizado.
    """

    ruta_archivo_pdf: str
    contenido_pdf: bytes
    hash_integridad_sha256: str
    plantilla_utilizada: str


@dataclass(frozen=True, slots=True)
class GenerarActaFinalComando:
    """Comando inmutable de entrada para generar el ActaFinal de una práctica empresarial (CU-09).

    Atributos:
        practica_id: Identificador único de la práctica en estado 'Evaluada'.
        actor_id: Identificador del usuario autenticado que solicita la generación (DocenteAsesor).
        rol_actor: Rol del usuario autenticado para validación RBAC centralizada (ADR-005).
        ip_origen: Dirección IP del cliente para registro en bitácora Append-Only (ADR-006).
        fecha_emision: Marca temporal opcional de emisión (por defecto UTC actual).
    """

    practica_id: str
    actor_id: str
    rol_actor: str = "DocenteAsesor"
    ip_origen: str = "127.0.0.1"
    fecha_emision: Optional[datetime] = None


@dataclass(frozen=True, slots=True)
class ActaFinalRespuestaDTO:
    """DTO inmutable de salida tras generar y sellar el ActaFinal en PDF (CU-09).

    Presenta al DocenteAsesor los metadatos oficiales del ActaFinal generada, su huella
    criptográfica hashIntegridadSha256, el estado de las firmas electrónicas pendientes
    (aprobadaPorDocente=False, aprobadaPorCoordinador=False) y la disponibilidad de
    previsualización para proceder a CU-10.

    Atributos:
        acta_id: Identificador único de la entidad ActaFinal registrada.
        numero_acta: Número oficial consecutivo anual del acta ('ACTA-<AÑO>-<NNNN>').
        practica_id: Identificador único de la práctica empresarial asociada.
        estudiante_id: Identificador del estudiante titular de la práctica.
        docente_asesor_id: Identificador del docente asesor asignado.
        supervisor_empresa_id: Identificador del supervisor de empresa que evaluó la práctica.
        regla_programa_id: Identificador de la versión de ReglaPrograma aplicada (EAC-01).
        programa_academico: Nombre del programa académico asociado a la regla.
        version_regla: Versión de la ReglaPrograma vinculada a la práctica.
        plantilla_acta: Plantilla HTML/CSS utilizada para renderizar el PDF.
        horas_requeridas: Horas mínimas exigidas por la ReglaPrograma vinculada.
        horas_acumuladas_aprobadas: Horas acumuladas aprobadas acreditadas por el estudiante.
        calificacion_cuantitativa: Calificación cuantitativa registrada en la EvaluacionDesempeno.
        es_aprobatoria: Indica si la calificación cuantitativa es aprobatoria (>= 3.0).
        observaciones_evaluacion: Observaciones registradas en la EvaluacionDesempeno.
        ruta_archivo_pdf: Ruta de almacenamiento del archivo binario PDF en el repositorio de actas.
        hash_integridad_sha256: Huella criptográfica SHA-256 de 64 caracteres hexadecimales del PDF.
        aprobada_por_docente: Estado de aprobación electrónica del DocenteAsesor (False en CU-09).
        aprobada_por_coordinador: Estado de aprobación electrónica del Coordinador (False en CU-09).
        estado_practica: Estado actual de la práctica ('Evaluada', a la espera de firmas en CU-10).
        fecha_emision: Marca temporal de emisión del ActaFinal.
        previsualizacion_disponible: Indica si el PDF está disponible para previsualización.
        mensaje: Mensaje descriptivo del resultado de la generación del acta final.
    """

    acta_id: str
    numero_acta: str
    practica_id: str
    estudiante_id: str
    docente_asesor_id: str
    supervisor_empresa_id: Optional[str]
    regla_programa_id: str
    programa_academico: str
    version_regla: str
    plantilla_acta: str
    horas_requeridas: int
    horas_acumuladas_aprobadas: int
    calificacion_cuantitativa: float
    es_aprobatoria: bool
    observaciones_evaluacion: Optional[str]
    ruta_archivo_pdf: str
    hash_integridad_sha256: str
    aprobada_por_docente: bool
    aprobada_por_coordinador: bool
    estado_practica: str
    fecha_emision: datetime
    previsualizacion_disponible: bool
    mensaje: str
