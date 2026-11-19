"""Adaptador simulado para el servicio de notificaciones por correo electrónico.

Traza: CU-01, EAC-02, ADR-001 (Resiliencia e integración asíncrona),
ADR-002 (Clean Architecture y Puertos y Adaptadores), Vista de Procesos §2, Vista de Desarrollo §2.

Implementa el puerto `ServicioCorreoPort` almacenando las notificaciones transaccionales
en una bandeja en memoria para validación determinista de envíos (e.g. Escenario 6 tras
recuperación del SIA).
"""

from __future__ import annotations

from typing import Optional

from aplicacion.puertos.servicio_correo import (
    ErrorServicioCorreo,
    MensajeNotificacionCorreo,
    ServicioCorreoPort,
)


class AdaptadorCorreoSimulado(ServicioCorreoPort):
    """Implementación simulada en memoria del puerto ServicioCorreoPort.

    Registra los correos despachados para inspección y aserciones en pruebas sin
    requerir un servidor SMTP o API de terceros real.
    """

    def __init__(self) -> None:
        self._bandeja_enviados: list[MensajeNotificacionCorreo] = []
        self._simular_fallo: bool = False

    # -- Implementación del contrato ServicioCorreoPort --------------------

    def enviar_notificacion(
        self, destinatario: str, asunto: str, cuerpo: str
    ) -> None:
        """Registra un mensaje de correo en la bandeja de enviados en memoria.

        Raises:
            ErrorServicioCorreo: Si se ha configurado la simulación de caída de transporte SMTP.
        """
        if self._simular_fallo:
            raise ErrorServicioCorreo("Fallo simulado al enviar notificación por correo electrónico.")

        mensaje = MensajeNotificacionCorreo(
            destinatario=destinatario,
            asunto=asunto,
            cuerpo=cuerpo,
        )
        self._bandeja_enviados.append(mensaje)

    # -- Métodos de inspección y apoyo para pruebas -------------------------

    @property
    def bandeja_enviados(self) -> list[MensajeNotificacionCorreo]:
        """Retorna una copia inmutable de todos los correos enviados."""
        return list(self._bandeja_enviados)

    @property
    def cantidad_enviados(self) -> int:
        return len(self._bandeja_enviados)

    def buscar_por_destinatario(
        self, destinatario: str
    ) -> list[MensajeNotificacionCorreo]:
        """Retorna todos los correos enviados a una dirección específica."""
        dest = destinatario.strip().lower()
        return [m for m in self._bandeja_enviados if m.destinatario.lower() == dest]

    def ultimo_correo_a(
        self, destinatario: str
    ) -> Optional[MensajeNotificacionCorreo]:
        """Retorna el último correo despachado al destinatario indicado o None si no hay."""
        enviados = self.buscar_por_destinatario(destinatario)
        return enviados[-1] if enviados else None

    def simular_fallo_envio(self, activar: bool = True) -> None:
        """Activa o desactiva la simulación de fallos en el servicio de correo."""
        self._simular_fallo = activar

    def limpiar(self) -> None:
        """Vacía la bandeja de correos enviados."""
        self._bandeja_enviados.clear()
        self._simular_fallo = False
