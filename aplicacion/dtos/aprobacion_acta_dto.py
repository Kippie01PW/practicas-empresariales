"""DTOs inmutables para el caso de uso AprobarActaElectronicamenteCasoUso (CU-10).

Traza: CU-10, EAC-03, PA-03, RN-01, RN-02, RN-03, ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-008, ADR-010.

Define los objetos de transferencia de datos inmutables (dataclass con frozen=True y slots=True)
utilizados en las fronteras del caso de uso AprobarActaElectronicamenteCasoUso:
- AprobarActaComando: DTO de entrada para registrar la firma y aprobación electrónica del ActaFinal
  por parte del DocenteAsesor (Paso 1) o del Coordinador de prácticas (Paso 2).
- AprobacionActaRespuestaDTO: DTO de salida con el resumen formal de la aprobación electrónica,
  el estado de integridad SHA-256, el estado actual de la Práctica y la liberación de cupo docente.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True, slots=True)
class AprobarActaComando:
    """Comando inmutable de entrada para aprobar electrónicamente el acta final (CU-10).

    Encapsula los parámetros requeridos para que el DocenteAsesor asignado (Paso 1)
    o el Coordinador de prácticas (Paso 2) asiente su aprobación electrónica sobre
    el ActaFinal generada de una Práctica en estado 'Evaluada', previa verificación
    de su huella de integridad SHA-256 (ADR-008).

    Atributos:
        practica_id: Identificador único de la práctica empresarial a la que pertenece el acta.
        actor_id: Identificador institucional del usuario que ejecuta la aprobación.
        rol_actor: Rol institucional del usuario ('DocenteAsesor' o 'Coordinador de prácticas').
        acta_id: Identificador opcional del ActaFinal a aprobar.
        ip_origen: Dirección IP del cliente para trazabilidad en la bitácora Append-Only (ADR-006).
    """

    practica_id: str
    actor_id: str
    rol_actor: str
    acta_id: Optional[str] = None
    ip_origen: str = "127.0.0.1"


@dataclass(frozen=True, slots=True)
class AprobacionActaRespuestaDTO:
    """DTO inmutable de salida tras asentar una aprobación electrónica sobre el ActaFinal (CU-10).

    Resume el estado resultante del ActaFinal, la verificación del hash SHA-256 (ADR-008),
    el estado actual de la Práctica ('Evaluada' tras el Paso 1 o 'Completada' tras el Paso 2,
    ADR-010) y el estado del cupo activo del DocenteAsesor asignado.

    Atributos:
        acta_id: Identificador único del ActaFinal aprobada.
        numero_acta: Número o código consecutivo oficial del acta final.
        practica_id: Identificador único de la práctica empresarial asociada.
        estado_practica: Estado formal resultante de la práctica ('Evaluada' o 'Completada').
        aprobada_por_docente: Indica si cuenta con la firma electrónica del DocenteAsesor.
        aprobada_por_coordinador: Indica si cuenta con la firma electrónica del Coordinador de prácticas.
        acta_en_firme: Indica si ambas firmas electrónicas han sido asentadas en orden secuencial.
        hash_integridad_sha256: Huella criptográfica SHA-256 verificada del archivo PDF del acta.
        ruta_archivo_pdf: Ruta o URI del archivo PDF oficial en el repositorio de actas.
        actor_aprobador_id: Identificador del actor que asentó la aprobación en esta operación.
        rol_aprobador: Rol del actor que asentó la aprobación en esta operación.
        cupo_docente_liberado: Indica si se decrementó en 1 el contador practicasActivas del DocenteAsesor.
        practicas_activas_docente: Cantidad resultante de prácticas activas del DocenteAsesor (o None).
        fecha_aprobacion: Marca temporal en que se asentó la aprobación electrónica.
        mensaje: Descripción legible del resultado de la operación.
    """

    acta_id: str
    numero_acta: str
    practica_id: str
    estado_practica: str
    aprobada_por_docente: bool
    aprobada_por_coordinador: bool
    acta_en_firme: bool
    hash_integridad_sha256: str
    ruta_archivo_pdf: str
    actor_aprobador_id: str
    rol_aprobador: str
    cupo_docente_liberado: bool
    practicas_activas_docente: Optional[int]
    fecha_aprobacion: datetime
    mensaje: str
