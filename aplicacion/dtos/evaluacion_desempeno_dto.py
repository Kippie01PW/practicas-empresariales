"""DTOs inmutables para el caso de uso EvaluarDesempenoCasoUso (CU-07).

Traza: CU-07, EAC-01, EAC-03, RN-01, RN-02, RN-03, RN-04, ADR-001, ADR-002, ADR-004, ADR-005, ADR-006, ADR-007, ADR-010.

Define los objetos de transferencia de datos inmutables (dataclass con frozen=True y slots=True)
utilizados en las fronteras del caso de uso EvaluarDesempenoCasoUso:
- ConsultarFormularioEvaluacionComando: DTO de entrada para abrir el enlace de evaluación y consultar la rúbrica.
- FormularioEvaluacionRespuestaDTO: DTO de salida con los datos del practicante y la rúbrica dinámica vinculada.
- EvaluarDesempenoComando: DTO de entrada para enviar la evaluación de desempeño del practicante.
- EvaluacionDesempenoRespuestaDTO: DTO de salida con el resumen formal de la evaluación asentada.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class ConsultarFormularioEvaluacionComando:
    """Comando inmutable de entrada para abrir el enlace de evaluación y consultar la rúbrica (CU-07).

    Encapsula el token criptográfico efímero (Magic Link HMAC-SHA256) presentado por el
    supervisor de empresa externo para consultar los datos del estudiante y los criterios
    de la rúbrica de la ReglaPrograma vinculada a la práctica, sin consumir el token.

    Atributos:
        token_acceso: Cadena criptográfica del Magic Link efímero (TokenEvaluacion).
        practica_id: Identificador opcional de la práctica a evaluar.
        ip_origen: Dirección IP del cliente para trazabilidad y bitácora (ADR-006).
    """

    token_acceso: str
    practica_id: Optional[str] = None
    ip_origen: str = "127.0.0.1"


@dataclass(frozen=True, slots=True)
class FormularioEvaluacionRespuestaDTO:
    """DTO inmutable de salida con los datos del practicante y la rúbrica dinámica (CU-07).

    Devuelve la estructura de la rúbrica correspondiente a la versión de ReglaPrograma
    vinculada a la práctica al momento de su postulación (ADR-007, EAC-01), manteniendo
    el TokenEvaluacion con usado=False hasta que se envíe la evaluación en firme.

    Atributos:
        practica_id: Identificador único de la práctica empresarial.
        estudiante_id: Identificador del estudiante titular de la práctica.
        supervisor_id: Identificador del supervisor de empresa asignado.
        estado_practica: Estado actual de la práctica (ej. 'EnEjecucion').
        regla_programa_id: Identificador de la regla de programa vinculada a la práctica.
        programa_academico: Nombre del programa académico asociado a la regla.
        version_regla: Versión normativa de la regla de programa vinculada.
        criterios_rubrica: Criterios de la rúbrica de evaluación definidos en la regla.
        escala_minima: Nota mínima permitida en la escala cuantitativa (0.0).
        escala_maxima: Nota máxima permitida en la escala cuantitativa (5.0).
        umbral_aprobacion: Nota mínima requerida para considerar la evaluación aprobatoria (3.0).
        mensaje: Descripción legible del resultado de la consulta.
    """

    practica_id: str
    estudiante_id: str
    supervisor_id: str
    estado_practica: str
    regla_programa_id: str
    programa_academico: str
    version_regla: str
    criterios_rubrica: dict[str, Any]
    escala_minima: float
    escala_maxima: float
    umbral_aprobacion: float
    mensaje: str


@dataclass(frozen=True, slots=True)
class EvaluarDesempenoComando:
    """Comando inmutable de entrada para registrar la evaluación de desempeño (CU-07).

    Encapsula las calificaciones por criterio de la rúbrica, la calificación cuantitativa
    global (escala 0.0 a 5.0), las observaciones cualitativas (obligatorias cuando la
    nota es reprobatoria < 3.0) y las credenciales del supervisor de empresa.

    Atributos:
        practica_id: Identificador único de la práctica a evaluar.
        calificacion_cuantitativa: Calificación cuantitativa global en la escala de 0.0 a 5.0.
        respuestas_rubrica: Diccionario con la calificación (0.0 a 5.0) para cada criterio de la rúbrica.
        observaciones: Concepto cualitativo u observaciones del supervisor (obligatorio si < 3.0).
        token_acceso: Cadena criptográfica del Magic Link efímero (ADR-004).
        supervisor_id: Identificador del supervisor de empresa que ejecuta la acción.
        ip_origen: Dirección IP del cliente para registro en bitácora Append-Only (ADR-006).
    """

    practica_id: str
    calificacion_cuantitativa: float
    respuestas_rubrica: dict[str, float]
    observaciones: Optional[str] = None
    token_acceso: Optional[str] = None
    supervisor_id: Optional[str] = None
    ip_origen: str = "127.0.0.1"


@dataclass(frozen=True, slots=True)
class EvaluacionDesempenoRespuestaDTO:
    """DTO inmutable de salida tras registrar la evaluación de desempeño en firme (CU-07).

    Resume la evaluación asentada, la transición formal de la práctica al estado
    'Evaluada' (ADR-010) y el consumo definitivo del TokenEvaluacion de un solo uso (ADR-004).

    Atributos:
        evaluacion_id: Identificador único de la EvaluacionDesempeno registrada.
        practica_id: Identificador único de la práctica evaluada.
        supervisor_id: Identificador del supervisor de empresa que asentó la calificación.
        calificacion_cuantitativa: Nota cuantitativa global registrada (0.0 a 5.0).
        es_aprobatoria: Indica si la calificación cuantitativa es mayor o igual a 3.0.
        observaciones: Observaciones cualitativas registradas (o None si no se incluyeron).
        respuestas_rubrica: Calificaciones registradas por cada criterio de la rúbrica.
        estado_practica: Nuevo estado formal de la práctica ('Evaluada').
        regla_programa_id: Identificador de la regla de programa contra la cual se validó la rúbrica.
        version_regla: Versión de la regla de programa aplicada (EAC-01).
        token_consumido: Indica si el TokenEvaluacion fue marcado con usado=True.
        fecha_evaluacion: Marca temporal en que se asentó la evaluación de desempeño.
        mensaje: Descripción legible del resultado de la operación.
    """

    evaluacion_id: str
    practica_id: str
    supervisor_id: str
    calificacion_cuantitativa: float
    es_aprobatoria: bool
    observaciones: Optional[str]
    respuestas_rubrica: dict[str, float]
    estado_practica: str
    regla_programa_id: str
    version_regla: str
    token_consumido: bool
    fecha_evaluacion: datetime
    mensaje: str
