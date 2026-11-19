"""Puerto para el servicio de notificación por correo electrónico.

Traza: CU-01, EAC-02, ADR-001 (Resiliencia e integración asíncrona),
ADR-002 (Clean Architecture y Puertos y Adaptadores), ADR-004 (Autenticación híbrida),
Vista de Procesos §2, Vista de Desarrollo §2.

Define el contrato formal (Protocol) para enviar notificaciones por correo
electrónico a los estudiantes y demás actores del sistema (ej. confirmación
de validación exitosa de postulación tras recuperación del SIA, Escenario 6).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Excepciones del puerto de correo
# ---------------------------------------------------------------------------

class ErrorServicioCorreo(Exception):
    """Excepción base para fallos al enviar notificaciones por correo electrónico."""

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje: str = mensaje

    def __str__(self) -> str:
        return self.mensaje

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(mensaje={self.mensaje!r})"


# ---------------------------------------------------------------------------
# DTO inmutable de Mensaje de Correo
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class MensajeNotificacionCorreo:
    """Representación inmutable de un mensaje de correo electrónico a despachar.

    Atributos:
        - destinatario: Dirección de correo electrónico del receptor.
        - asunto: Asunto o título del mensaje.
        - cuerpo: Contenido textual o plantilla renderizada del mensaje.
        - es_html: Booleano que indica si el cuerpo posee formato HTML.
        - fecha_envio: Marca temporal de despacho (se asigna automáticamente si es None).
    """

    destinatario: str
    asunto: str
    cuerpo: str
    es_html: bool = False
    fecha_envio: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.destinatario or not self.destinatario.strip():
            raise ValueError("La dirección de correo del destinatario no puede estar vacía.")
        if not self.asunto or not self.asunto.strip():
            raise ValueError("El asunto del correo no puede estar vacío.")
        if not self.cuerpo or not self.cuerpo.strip():
            raise ValueError("El cuerpo del correo no puede estar vacío.")

        object.__setattr__(self, "destinatario", self.destinatario.strip())
        object.__setattr__(self, "asunto", self.asunto.strip())
        object.__setattr__(self, "cuerpo", self.cuerpo.strip())
        if self.fecha_envio is None:
            object.__setattr__(self, "fecha_envio", datetime.now())


# ---------------------------------------------------------------------------
# Puerto de Salida: Protocol ServicioCorreoPort
# ---------------------------------------------------------------------------

@runtime_checkable
class ServicioCorreoPort(Protocol):
    """Puerto de salida hacia el servicio de correo electrónico institucional (SMTP/API).

    Define la operación requerida para despachar notificaciones transaccionales
    asociadas a los eventos del ciclo de vida de la práctica empresarial.
    """

    def enviar_notificacion(
        self, destinatario: str, asunto: str, cuerpo: str
    ) -> None:
        """Envía una notificación por correo electrónico al destinatario indicado.

        Traza: CU-01, EAC-02, spec.md Escenario 6.

        Args:
            destinatario: Dirección de correo institucional del usuario receptor.
            asunto: Título o asunto del correo electrónico.
            cuerpo: Contenido del mensaje de notificación.

        Raises:
            ErrorServicioCorreo: Si ocurre un fallo en el servidor o transporte de correo.
        """
        ...
