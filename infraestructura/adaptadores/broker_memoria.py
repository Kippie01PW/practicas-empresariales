"""Adaptador en memoria para el Bróker de Mensajería (cola de tareas, eventos y Dead-Letter Queue).

Traza: CU-01, CU-10, EAC-02, OB-05, RT-01, ADR-001 (Resiliencia e integración asíncrona),
ADR-002 (Clean Architecture y Puertos y Adaptadores), ADR-008 (Preservación de actas),
Vista de Procesos §2, Vista de Desarrollo §2.

Implementa el puerto `PublicadorEventosPort` proveyendo colas en memoria deterministas para:
1. Encolar tareas de validación asíncrona frente al SIA (CU-01, Escenario 5).
2. Derivar mensajes agotados a la Dead-Letter Queue (DLQ) (CU-01, Escenario 7).
3. Registrar alertas operativas para el equipo de soporte técnico (TI) (CU-01, Escenario 7).
4. Publicar el evento asíncrono 'ActaFinalEmitida' al quedar un acta en firme (CU-10, Escenario 2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from aplicacion.puertos.publicador_eventos import (
    DatosTareaValidacionSia,
    ErrorPublicacionEvento,
    EventoActaFinalEmitida,
    PublicadorEventosPort,
)


@dataclass(frozen=True, slots=True)
class MensajeColaMuerta:
    """Registro inmutable de un mensaje descartado en la Dead-Letter Queue (DLQ)."""

    tarea: DatosTareaValidacionSia
    motivo_fallo: str
    fecha_enrutado: datetime


@dataclass(frozen=True, slots=True)
class AlertaSoporteRegistro:
    """Registro inmutable de una alerta operativa emitida a TI."""

    asunto: str
    mensaje: str
    contexto: Optional[dict[str, Any]]
    fecha_emision: datetime


class InMemoryBrokerMensajes(PublicadorEventosPort):
    """Implementación en memoria del puerto PublicadorEventosPort.

    Simula el bróker de mensajería (RabbitMQ / SQS) manteniendo colas FIFO, almacenes
    de alertas y registro de eventos de dominio para pruebas de integración y
    procesamiento en segundo plano (ADR-001).
    """

    def __init__(self) -> None:
        self._cola_tareas: list[DatosTareaValidacionSia] = []
        self._cola_muerta: list[MensajeColaMuerta] = []
        self._alertas_soporte: list[AlertaSoporteRegistro] = []
        self._eventos_acta_emitida: list[EventoActaFinalEmitida] = []
        self._simular_fallo: bool = False

    # -- Implementación del contrato PublicadorEventosPort ------------------

    def publicar_tarea_validacion_sia(self, tarea: DatosTareaValidacionSia) -> None:
        """Encola una tarea de verificación asíncrona de requisitos frente al SIA."""
        if self._simular_fallo:
            raise ErrorPublicacionEvento("Fallo simulado al encolar tarea en el bróker de mensajería.")
        self._cola_tareas.append(tarea)

    def publicar_en_cola_muerta(
        self, tarea: DatosTareaValidacionSia, motivo_fallo: str
    ) -> None:
        """Enruta una tarea agotada a la Dead-Letter Queue (DLQ) (ADR-001, Escenario 7)."""
        if self._simular_fallo:
            raise ErrorPublicacionEvento("Fallo simulado al derivar mensaje a la Dead-Letter Queue.")
        registro = MensajeColaMuerta(
            tarea=tarea,
            motivo_fallo=motivo_fallo,
            fecha_enrutado=datetime.now(),
        )
        self._cola_muerta.append(registro)

    def publicar_alerta_soporte(
        self, asunto: str, mensaje: str, contexto: Optional[dict[str, Any]] = None
    ) -> None:
        """Emite una alerta operativa para el equipo de soporte técnico (TI)."""
        if self._simular_fallo:
            raise ErrorPublicacionEvento("Fallo simulado al publicar alerta operativa a TI.")
        alerta = AlertaSoporteRegistro(
            asunto=asunto,
            mensaje=mensaje,
            contexto=contexto,
            fecha_emision=datetime.now(),
        )
        self._alertas_soporte.append(alerta)

    def publicar_acta_final_emitida(self, evento: EventoActaFinalEmitida) -> None:
        """Publica el evento asíncrono 'ActaFinalEmitida' al quedar un acta en firme (CU-10, Escenario 2)."""
        if self._simular_fallo:
            raise ErrorPublicacionEvento(
                "Fallo simulado al publicar el evento ActaFinalEmitida en el bróker de mensajería."
            )
        if not isinstance(evento, EventoActaFinalEmitida):
            raise ErrorPublicacionEvento(
                "El evento a publicar debe ser una instancia válida de EventoActaFinalEmitida."
            )
        self._eventos_acta_emitida.append(evento)

    # -- Métodos de consumo e inspección para el Worker y validaciones ------

    def desencolar_tarea(self) -> Optional[DatosTareaValidacionSia]:
        """Extrae la siguiente tarea de la cola en orden FIFO (o None si está vacía)."""
        if self._cola_tareas:
            return self._cola_tareas.pop(0)
        return None

    def desencolar_evento_acta_emitida(self) -> Optional[EventoActaFinalEmitida]:
        """Extrae el siguiente evento ActaFinalEmitida en orden FIFO (o None si no hay)."""
        if self._eventos_acta_emitida:
            return self._eventos_acta_emitida.pop(0)
        return None

    def obtener_tareas(self) -> list[DatosTareaValidacionSia]:
        """Retorna una copia de las tareas actualmente encoladas."""
        return list(self._cola_tareas)

    def obtener_cola_muerta(self) -> list[MensajeColaMuerta]:
        """Retorna todos los mensajes depositados en la Dead-Letter Queue."""
        return list(self._cola_muerta)

    def obtener_alertas(self) -> list[AlertaSoporteRegistro]:
        """Retorna todas las alertas operativas emitidas."""
        return list(self._alertas_soporte)

    def obtener_eventos_acta_emitida(self) -> list[EventoActaFinalEmitida]:
        """Retorna una copia de los eventos ActaFinalEmitida publicados en el bróker."""
        return list(self._eventos_acta_emitida)

    @property
    def cantidad_tareas(self) -> int:
        return len(self._cola_tareas)

    @property
    def cantidad_cola_muerta(self) -> int:
        return len(self._cola_muerta)

    @property
    def cantidad_alertas(self) -> int:
        return len(self._alertas_soporte)

    @property
    def cantidad_eventos_acta_emitida(self) -> int:
        return len(self._eventos_acta_emitida)

    def simular_fallo_publicacion(self, activar: bool = True) -> None:
        """Activa o desactiva la simulación de errores de comunicación con el bróker."""
        self._simular_fallo = activar

    def limpiar(self) -> None:
        """Limpia las colas y registros en memoria."""
        self._cola_tareas.clear()
        self._cola_muerta.clear()
        self._alertas_soporte.clear()
        self._eventos_acta_emitida.clear()
        self._simular_fallo = False
