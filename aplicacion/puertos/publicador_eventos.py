"""Puerto para publicación de eventos y tareas asíncronas en el bróker de mensajería.

Traza: CU-01, EAC-02, RT-01, ADR-001 (Resiliencia e integración asíncrona),
ADR-002 (Clean Architecture y Puertos y Adaptadores), Vista de Procesos §2, Vista de Desarrollo §2.

Define el contrato formal (Protocol) para encolar tareas de validación asíncrona
frente al SIA tras fallos o timeouts en la verificación síncrona inicial, enrutar
mensajes agotados hacia la Dead-Letter Queue (DLQ) y emitir alertas operativas
al equipo de soporte técnico (TI).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Excepciones del puerto de publicación de eventos
# ---------------------------------------------------------------------------

class ErrorPublicacionEvento(Exception):
    """Excepción base para fallos al publicar mensajes o tareas en el bróker."""

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje: str = mensaje

    def __str__(self) -> str:
        return self.mensaje

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(mensaje={self.mensaje!r})"


# ---------------------------------------------------------------------------
# DTO inmutable para datos de la tarea de validación SIA
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DatosTareaValidacionSia:
    """Datos inmutables de la tarea asíncrona de verificación de requisitos con el SIA.

    Traza: CU-01, EAC-02, ADR-001, diagramas/secuencias/cu01-postularse.puml.

    Atributos:
        - practica_id: Identificador único de la práctica en estado 'PendienteVerificacion'.
        - documento_estudiante: Documento de identidad del estudiante para consulta al SIA.
        - correo_estudiante: Correo institucional del estudiante para notificación posterior.
        - numero_reintento: Número ordinal del intento de verificación (inicia en 1).
        - max_reintentos: Límite máximo de reintentos permitidos (5 según ADR-001).
        - fecha_creacion: Marca temporal en que se originó y encoló la tarea.
        - metadata: Metadatos o diagnóstico de fallos previos para trazabilidad.
    """

    practica_id: str
    documento_estudiante: str
    correo_estudiante: Optional[str] = None
    numero_reintento: int = 1
    max_reintentos: int = 5
    fecha_creacion: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.practica_id or not self.practica_id.strip():
            raise ValueError("El identificador de práctica no puede estar vacío.")
        if not self.documento_estudiante or not self.documento_estudiante.strip():
            raise ValueError("El documento del estudiante no puede estar vacío.")
        if self.numero_reintento < 1:
            raise ValueError("El número de reintento debe ser mayor o igual a 1.")
        if self.max_reintentos < 1:
            raise ValueError("El máximo de reintentos debe ser mayor o igual a 1.")

        object.__setattr__(self, "practica_id", self.practica_id.strip())
        object.__setattr__(self, "documento_estudiante", self.documento_estudiante.strip())
        if self.correo_estudiante is not None:
            object.__setattr__(self, "correo_estudiante", self.correo_estudiante.strip())
        if self.fecha_creacion is None:
            object.__setattr__(self, "fecha_creacion", datetime.now())

    def siguiente_reintento(self, metadata: Optional[dict[str, Any]] = None) -> DatosTareaValidacionSia:
        """Genera una nueva instancia inmutable incrementando el contador de reintento."""
        return DatosTareaValidacionSia(
            practica_id=self.practica_id,
            documento_estudiante=self.documento_estudiante,
            correo_estudiante=self.correo_estudiante,
            numero_reintento=self.numero_reintento + 1,
            max_reintentos=self.max_reintentos,
            fecha_creacion=self.fecha_creacion,
            metadata=metadata or self.metadata,
        )

    def ha_agotado_reintentos(self) -> bool:
        """Determina si la tarea ha alcanzado o superado el número máximo de reintentos."""
        return self.numero_reintento >= self.max_reintentos


# ---------------------------------------------------------------------------
# DTO inmutable para evento asíncrono de emisión y firmeza de ActaFinal (CU-10)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EventoActaFinalEmitida:
    """Evento inmutable publicado cuando un ActaFinal queda oficialmente en firme.

    Traza: CU-10, Escenario 2 (Aprobación electrónica final exitosa por el Coordinador
    de prácticas y transición a estado Completada), OB-05, ADR-001, ADR-008,
    diagramas/secuencias/cu10-aprobar-acta.puml.

    Atributos:
        - practica_id: Identificador único de la práctica completada.
        - acta_id: Identificador único del ActaFinal aprobada.
        - numero_acta: Número oficial consecutivo del acta final.
        - estudiante_id: Identificador del estudiante titular de la práctica.
        - ruta_archivo_pdf: Ruta o referencia del documento PDF del acta final.
        - hash_integridad_sha256: Huella criptográfica SHA-256 de 64 caracteres del PDF.
        - fecha_emision: Marca temporal de emisión/firmeza del evento.
    """

    practica_id: str
    acta_id: str
    numero_acta: str
    estudiante_id: str
    ruta_archivo_pdf: str
    hash_integridad_sha256: str
    fecha_emision: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.practica_id or not str(self.practica_id).strip():
            raise ValueError("El identificador de práctica es obligatorio en EventoActaFinalEmitida.")
        if not self.acta_id or not str(self.acta_id).strip():
            raise ValueError("El identificador del acta es obligatorio en EventoActaFinalEmitida.")
        if not self.numero_acta or not str(self.numero_acta).strip():
            raise ValueError("El número de acta es obligatorio en EventoActaFinalEmitida.")
        if not self.estudiante_id or not str(self.estudiante_id).strip():
            raise ValueError("El identificador del estudiante es obligatorio en EventoActaFinalEmitida.")
        if not self.ruta_archivo_pdf or not str(self.ruta_archivo_pdf).strip():
            raise ValueError("La ruta del archivo PDF es obligatoria en EventoActaFinalEmitida.")
        if not self.hash_integridad_sha256 or not str(self.hash_integridad_sha256).strip():
            raise ValueError("El hashIntegridadSha256 es obligatorio en EventoActaFinalEmitida.")

        object.__setattr__(self, "practica_id", str(self.practica_id).strip())
        object.__setattr__(self, "acta_id", str(self.acta_id).strip())
        object.__setattr__(self, "numero_acta", str(self.numero_acta).strip())
        object.__setattr__(self, "estudiante_id", str(self.estudiante_id).strip())
        object.__setattr__(self, "ruta_archivo_pdf", str(self.ruta_archivo_pdf).strip())
        object.__setattr__(
            self, "hash_integridad_sha256", str(self.hash_integridad_sha256).strip().lower()
        )
        if self.fecha_emision is None:
            object.__setattr__(self, "fecha_emision", datetime.now())


# ---------------------------------------------------------------------------
# Puerto de Salida: Protocol PublicadorEventosPort
# ---------------------------------------------------------------------------

@runtime_checkable
class PublicadorEventosPort(Protocol):
    """Puerto de salida hacia el bróker de mensajería para eventos y tareas asíncronas.

    Define las operaciones para despachar tareas al worker de integración,
    enrutar mensajes agotados a la cola de mensajes fallidos (Dead-Letter Queue),
    generar alertas operativas hacia soporte técnico (ADR-001, EAC-02) y publicar
    el evento de emisión en firme de un acta final (CU-10).
    """

    def publicar_tarea_validacion_sia(self, tarea: DatosTareaValidacionSia) -> None:
        """Encola una tarea de verificación asíncrona de requisitos frente al SIA.

        Traza: CU-01, EAC-02, ADR-001, spec.md Escenario 5.

        Args:
            tarea: Objeto DatosTareaValidacionSia con el identificador de la práctica,
                documento y contador de reintentos.

        Raises:
            ErrorPublicacionEvento: Si ocurre una falla irrecuperable en el bróker.
        """
        ...

    def publicar_en_cola_muerta(
        self, tarea: DatosTareaValidacionSia, motivo_fallo: str
    ) -> None:
        """Enruta una tarea a la Dead-Letter Queue (DLQ) tras agotar reintentos (ADR-001).

        Traza: CU-01, EAC-02, ADR-001, spec.md Escenario 7.

        Args:
            tarea: Objeto DatosTareaValidacionSia cuyo límite de reintentos fue alcanzado.
            motivo_fallo: Descripción del fallo persistente o causa técnica del descarte.

        Raises:
            ErrorPublicacionEvento: Si ocurre una falla al comunicar con la DLQ.
        """
        ...

    def publicar_alerta_soporte(
        self, asunto: str, mensaje: str, contexto: Optional[dict[str, Any]] = None
    ) -> None:
        """Emite una alerta operativa al equipo de soporte técnico (TI) para revisión.

        Traza: CU-01, EAC-02, ADR-001, spec.md Escenario 7.

        Args:
            asunto: Título o resumen de la alerta técnica.
            mensaje: Cuerpo detallado con la descripción de la anomalía operativa.
            contexto: Metadatos o variables de contexto asociadas a la alerta.

        Raises:
            ErrorPublicacionEvento: Si la emisión de la alerta no pudo ser entregada.
        """
        ...

    def publicar_acta_final_emitida(self, evento: EventoActaFinalEmitida) -> None:
        """Publica el evento asíncrono 'ActaFinalEmitida' al quedar un acta en firme.

        Traza: CU-10, Escenario 2, OB-05, ADR-001, ADR-008,
        diagramas/secuencias/cu10-aprobar-acta.puml.

        Args:
            evento: Instancia inmutable de EventoActaFinalEmitida con los datos del
                acta aprobada y de la práctica completada.

        Raises:
            ErrorPublicacionEvento: Si ocurre una falla al publicar el evento en el bróker.
        """
        ...
