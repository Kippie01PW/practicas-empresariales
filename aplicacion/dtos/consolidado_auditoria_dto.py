"""DTOs inmutables para el caso de uso GenerarConsolidadosAuditoriaCasoUso (CU-14).

Traza: CU-14, EAC-03, OB-02, PA-03, RN-01, RN-03, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-008.

Define los objetos de transferencia de datos inmutables (dataclass con frozen=True y slots=True)
utilizados en las fronteras del caso de uso GenerarConsolidadosAuditoriaCasoUso y sus puertos:
- GenerarConsolidadoAuditoriaComando: Comando de entrada con los filtros obligatorios y opcionales.
- RegistroConsolidadoPracticaDTO: Resumen histórico inmutable de una Practica y su ActaFinal asociada.
- DatosRenderizadoConsolidadoPdfDTO: Metadatos, totales y registros enviados al adaptador PDF y Hash.
- ConsolidadoAuditoriaRespuestaDTO: Respuesta formal de salida con el PDF sellado SHA-256 y los totales.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True, slots=True)
class GenerarConsolidadoAuditoriaComando:
    """Comando inmutable de entrada para generar y exportar un consolidado de auditoría (CU-14).

    Atributos:
        programa_academico: Programa académico obligatorio para filtrar el consolidado histórico.
        periodo: Período académico obligatorio (ej. '2026-1').
        actor_id: Identificador institucional del usuario autenticado (Coordinador de prácticas).
        rol_actor: Rol del usuario autenticado para validación RBAC centralizada (ADR-005).
        fecha_inicio: Fecha inicial opcional del rango de filtro sobre fecha_postulacion.
        fecha_fin: Fecha final opcional del rango de filtro sobre fecha_postulacion.
        estado_practica: Estado de práctica opcional para filtrar (debe corresponder a EstadoPractica).
        ip_origen: Dirección IP del cliente para registro en bitácora Append-Only (ADR-006).
    """

    programa_academico: str
    periodo: str
    actor_id: str
    rol_actor: str = "Coordinador de prácticas"
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    estado_practica: Optional[str] = None
    ip_origen: str = "127.0.0.1"


@dataclass(frozen=True, slots=True)
class RegistroConsolidadoPracticaDTO:
    """Resumen histórico inmutable de una Practica y su ActaFinal asociada para auditoría (CU-14).

    No incluye el listado detallado de eventos individuales de EventoBitacora.

    Atributos:
        practica_id: Identificador único de la práctica empresarial.
        estudiante_id: Identificador del estudiante titular de la práctica.
        programa_academico: Nombre del programa académico asociado a la práctica.
        periodo: Período académico asociado al registro de la práctica.
        estado_actual: Estado formal actual de la práctica en la máquina de estados (ADR-010).
        fecha_postulacion: Marca temporal de postulación inicial.
        fecha_inicio: Marca temporal de inicio de ejecución (si aplica).
        fecha_fin: Marca temporal de finalización o cierre (si aplica).
        docente_asesor_id: Identificador del docente asesor asignado (si aplica).
        nombre_docente_asesor: Nombre completo del docente asesor asignado (si aplica).
        supervisor_empresa_id: Identificador del supervisor de empresa vinculado (si aplica).
        horas_acumuladas_aprobadas: Total de horas acumuladas en estado 'Aprobado'.
        horas_requeridas: Horas mínimas exigidas por la ReglaPrograma vinculada (si aplica).
        calificacion_cuantitativa: Calificación cuantitativa de EvaluacionDesempeno (si aplica).
        es_aprobatoria: Indica si la evaluación de desempeño fue aprobatoria (si aplica).
        numero_acta: Número oficial del ActaFinal asociada (si existe).
        fecha_emision_acta: Fecha de emisión del ActaFinal asociada (si existe).
        aprobada_por_docente: Estado de firma electrónica del DocenteAsesor (si existe acta).
        aprobada_por_coordinador: Estado de firma electrónica del Coordinador (si existe acta).
        acta_en_firme: Indica si el ActaFinal cuenta con ambas firmas electrónicas (si existe acta).
        hash_integridad_sha256: Huella SHA-256 de integridad del ActaFinal (si existe acta).
    """

    practica_id: str
    estudiante_id: str
    programa_academico: str
    periodo: str
    estado_actual: str
    fecha_postulacion: datetime
    fecha_inicio: Optional[datetime]
    fecha_fin: Optional[datetime]
    docente_asesor_id: Optional[str]
    nombre_docente_asesor: Optional[str]
    supervisor_empresa_id: Optional[str]
    horas_acumuladas_aprobadas: int
    horas_requeridas: Optional[int]
    calificacion_cuantitativa: Optional[float]
    es_aprobatoria: Optional[bool]
    numero_acta: Optional[str]
    fecha_emision_acta: Optional[datetime]
    aprobada_por_docente: Optional[bool]
    aprobada_por_coordinador: Optional[bool]
    acta_en_firme: Optional[bool]
    hash_integridad_sha256: Optional[str]


@dataclass(frozen=True, slots=True)
class DatosRenderizadoConsolidadoPdfDTO:
    """DTO inmutable con los metadatos de filtro, totales y registros enviados al adaptador PDF (CU-14).

    Atributos:
        programa_academico: Programa académico consultado.
        periodo: Período académico consultado.
        fecha_inicio: Fecha inicial del filtro aplicado (o None).
        fecha_fin: Fecha final del filtro aplicado (o None).
        estado_practica_filtro: Estado de práctica filtrado (o None).
        total_practicas: Cantidad total de prácticas coincidentes.
        total_completadas: Cantidad de prácticas coincidentes en estado 'Completada'.
        total_con_acta_en_firme: Cantidad de prácticas coincidentes con ActaFinal en firme.
        registros: Tupla inmutable de registros históricos proyectados.
        fecha_generacion: Marca temporal de generación del consolidado.
        actor_id: Identificador institucional del Coordinador de prácticas solicitante.
    """

    programa_academico: str
    periodo: str
    fecha_inicio: Optional[datetime]
    fecha_fin: Optional[datetime]
    estado_practica_filtro: Optional[str]
    total_practicas: int
    total_completadas: int
    total_con_acta_en_firme: int
    registros: tuple[RegistroConsolidadoPracticaDTO, ...]
    fecha_generacion: datetime
    actor_id: str


@dataclass(frozen=True, slots=True)
class ConsolidadoAuditoriaRespuestaDTO:
    """DTO inmutable de salida tras generar y sellar el consolidado histórico en PDF (CU-14).

    Atributos:
        programa_academico: Programa académico consultado.
        periodo: Período académico consultado.
        fecha_inicio: Fecha inicial del filtro aplicado (o None).
        fecha_fin: Fecha final del filtro aplicado (o None).
        estado_practica_filtro: Estado de práctica filtrado (o None).
        total_practicas: Cantidad total de prácticas coincidentes.
        total_completadas: Cantidad de prácticas coincidentes en estado 'Completada'.
        total_con_acta_en_firme: Cantidad de prácticas coincidentes con ActaFinal en firme.
        registros: Tupla inmutable de registros históricos incluidos en el consolidado.
        contenido_pdf: Contenido binario del documento PDF exportado.
        hash_sha256_pdf: Huella criptográfica SHA-256 del documento PDF consolidado.
        nombre_archivo_pdf: Nombre sugerido del archivo PDF exportado.
        fecha_generacion: Marca temporal oficial de generación del consolidado.
        mensaje: Mensaje descriptivo del resultado (incluyendo aviso explícito cuando total_practicas == 0).
    """

    programa_academico: str
    periodo: str
    fecha_inicio: Optional[datetime]
    fecha_fin: Optional[datetime]
    estado_practica_filtro: Optional[str]
    total_practicas: int
    total_completadas: int
    total_con_acta_en_firme: int
    registros: tuple[RegistroConsolidadoPracticaDTO, ...]
    contenido_pdf: bytes
    hash_sha256_pdf: str
    nombre_archivo_pdf: str
    fecha_generacion: datetime
    mensaje: str
