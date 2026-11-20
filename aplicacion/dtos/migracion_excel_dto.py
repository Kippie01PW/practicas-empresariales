"""DTOs inmutables para el caso de uso MigrarPracticasExcelCasoUso (CU-15).

Traza: CU-15, OB-02, RT-02, RN-01, RN-02, RN-03, PA-05, R-03, R-04, DT-04,
ADR-002, ADR-003, ADR-005, ADR-006, ADR-007, ADR-009, ADR-010.

Define los objetos de transferencia de datos inmutables (dataclass con frozen=True y slots=True)
utilizados en las fronteras del caso de uso MigrarPracticasExcelCasoUso y su puerto
LectorPlantillaExcelPort:
- FilaPlantillaMigracionDTO: Representa una fila leída desde la plantilla normalizada de Excel.
- MigrarPracticasExcelComando: Comando de entrada con origen de datos, modo dry-run y actor DBA.
- ResultadoFilaMigracionDTO: Resultado detallado de validación/importación por cada fila.
- MigrarPracticasExcelRespuestaDTO: Reporte consolidado de la ejecución de migración.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class FilaPlantillaMigracionDTO:
    """Representa una fila cruda leída de la plantilla normalizada de Excel (CU-15).

    Atributos:
        numero_fila: Número de fila en la plantilla (base 1 o índice de datos) para reporte de errores.
        documento_estudiante: Documento de identidad del estudiante.
        nombre_estudiante: Nombre completo del estudiante.
        correo_estudiante: Correo electrónico institucional o de contacto del estudiante.
        programa_academico: Nombre del programa académico de la práctica.
        nombre_empresa: Razón social o nombre de la empresa receptora.
        nit_empresa: NIT o identificador tributario de la empresa receptora.
        supervisor_nombre: Nombre completo del supervisor de empresa.
        supervisor_correo: Correo electrónico del supervisor de empresa.
        docente_asesor_id: Identificador o documento del docente asesor asignado (si aplica).
        horas_acumuladas: Cadena con las horas acumuladas reportadas en la plantilla.
        estado_o_hito: Cadena con el estado o hitos completados reportados en la plantilla.
        fecha_postulacion: Fecha de postulación en formato ISO/texto (opcional).
        fecha_inicio: Fecha de inicio formal de la práctica en formato ISO/texto (opcional).
        fecha_fin: Fecha de finalización en formato ISO/texto (opcional).
    """

    numero_fila: int
    documento_estudiante: str
    nombre_estudiante: str
    correo_estudiante: str
    programa_academico: str
    nombre_empresa: str
    nit_empresa: str
    supervisor_nombre: str
    supervisor_correo: str
    docente_asesor_id: str
    horas_acumuladas: str
    estado_o_hito: str
    fecha_postulacion: str
    fecha_inicio: str
    fecha_fin: str


@dataclass(frozen=True, slots=True)
class MigrarPracticasExcelComando:
    """Comando inmutable de entrada para ejecutar la migración desde Excel (CU-15).

    Atributos:
        origen_datos: Ruta del archivo CSV/Excel normalizado o identificador del lote en memoria.
        dry_run: Si es True, ejecuta solo validación sin persistir cambios en el almacenamiento.
        actor_id: Identificador institucional del Administrador DBA autenticado.
        rol_actor: Rol del operador para validación RBAC centralizada (ADR-005).
        ip_origen: Dirección IP u origen de ejecución CLI para registro en bitácora (ADR-006).
    """

    origen_datos: str
    dry_run: bool = True
    actor_id: str = ""
    rol_actor: str = "Administrador DBA"
    ip_origen: str = "127.0.0.1"


@dataclass(frozen=True, slots=True)
class ResultadoFilaMigracionDTO:
    """DTO inmutable con el resultado de validación o importación de una fila (CU-15).

    Atributos:
        numero_fila: Número de fila evaluada en la plantilla normalizada.
        documento_estudiante: Documento del estudiante reportado en la fila.
        estado_resultado: Clasificación del resultado ('VALIDA', 'IMPORTADA',
            'OMITIDA_DUPLICADA' o 'RECHAZADA').
        estado_practica_asignado: Estado formal asignado en EstadoPractica (o None si rechazada/omitida).
        mensaje: Descripción detallada del resultado, advertencia o motivo de rechazo.
    """

    numero_fila: int
    documento_estudiante: str
    estado_resultado: str
    estado_practica_asignado: Optional[str]
    mensaje: str


@dataclass(frozen=True, slots=True)
class MigrarPracticasExcelRespuestaDTO:
    """DTO inmutable de salida con el informe consolidado del proceso de migración (CU-15).

    Atributos:
        dry_run: Indica si la ejecución fue en modo solo validación (True) o carga definitiva (False).
        total_filas: Cantidad total de filas procesadas de la plantilla.
        total_validas: Cantidad de filas válidas listas para importación (en dry-run o definitivo).
        total_importadas: Cantidad de prácticas efectivamente persistidas (0 cuando dry_run=True).
        total_omitidas_duplicadas: Cantidad de filas omitidas por duplicidad en lote o sistema.
        total_rechazadas: Cantidad de filas rechazadas por inconsistencias o reglas de dominio.
        resultados_filas: Tupla inmutable con el detalle fila por fila.
        mensaje: Resumen legible del resultado de la ejecución.
    """

    dry_run: bool
    total_filas: int
    total_validas: int
    total_importadas: int
    total_omitidas_duplicadas: int
    total_rechazadas: int
    resultados_filas: tuple[ResultadoFilaMigracionDTO, ...]
    mensaje: str
