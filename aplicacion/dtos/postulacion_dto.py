"""DTOs inmutables para comando y respuesta de postulación de estudiante a práctica.

Traza: CU-01, EAC-02, RT-01, RT-03, ADR-001, ADR-002, ADR-004, ADR-005, ADR-006, ADR-007, ADR-010.

Define los objetos de transferencia de datos inmutables (dataclass con frozen=True)
utilizados en las fronteras de la capa de aplicación:
- PostularEstudianteComando: DTO de entrada con datos del estudiante solicitante,
  contexto de identidad OIDC/SSO (rol y actor) y metadatos de auditoría (IP de origen).
- PostulacionRespuestaDTO: DTO de salida entregado al usuario/UI con el estado
  de la práctica, confirmación, causal de rechazo o indicación de verificación asíncrona.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from dominio.modelos.practica import EstadoPractica


# ---------------------------------------------------------------------------
# DTO de Entrada: Comando de Postulación
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PostularEstudianteComando:
    """Comando inmutable con los datos requeridos para registrar una postulación.

    Atributos del estudiante (dominio/modelos/estudiante.py):
        - documento: Documento de identidad del estudiante solicitante.
        - nombre_completo: Nombre completo del estudiante.
        - correo_institucional: Dirección de correo institucional de la universidad.
        - programa_academico: Programa académico al que pertenece el estudiante.
        - estudiante_id: Identificador interno o del usuario (opcional; si se omite
          se asume el documento).

    Atributos de contexto de seguridad y auditoría (ADR-004, ADR-005, ADR-006):
        - rol_actor: Rol autenticado del solicitante (por defecto 'Estudiante').
        - ip_origen: Dirección IP desde la cual se emite la solicitud (por defecto '127.0.0.1').
    """

    documento: str
    nombre_completo: str
    correo_institucional: str
    programa_academico: str
    estudiante_id: Optional[str] = None
    rol_actor: str = "Estudiante"
    ip_origen: str = "127.0.0.1"

    def __post_init__(self) -> None:
        if not self.documento or not self.documento.strip():
            raise ValueError("El documento del estudiante no puede estar vacío.")
        if not self.nombre_completo or not self.nombre_completo.strip():
            raise ValueError("El nombre completo del estudiante no puede estar vacío.")
        if not self.correo_institucional or not self.correo_institucional.strip():
            raise ValueError("El correo institucional del estudiante no puede estar vacío.")
        if not self.programa_academico or not self.programa_academico.strip():
            raise ValueError("El programa académico del estudiante no puede estar vacío.")
        if not self.rol_actor or not self.rol_actor.strip():
            raise ValueError("El rol del actor no puede estar vacío.")
        if not self.ip_origen or not self.ip_origen.strip():
            raise ValueError("La dirección IP de origen no puede estar vacía.")

        # Normalización y asignación por defecto de estudiante_id si no fue provisto
        id_asignado = (
            self.estudiante_id.strip()
            if self.estudiante_id and self.estudiante_id.strip()
            else self.documento.strip()
        )

        object.__setattr__(self, "documento", self.documento.strip())
        object.__setattr__(self, "nombre_completo", self.nombre_completo.strip())
        object.__setattr__(self, "correo_institucional", self.correo_institucional.strip())
        object.__setattr__(self, "programa_academico", self.programa_academico.strip())
        object.__setattr__(self, "estudiante_id", id_asignado)
        object.__setattr__(self, "rol_actor", self.rol_actor.strip())
        object.__setattr__(self, "ip_origen", self.ip_origen.strip())


# ---------------------------------------------------------------------------
# DTO de Salida: Respuesta de Postulación
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PostulacionRespuestaDTO:
    """DTO inmutable con la respuesta al estudiante tras procesar su postulación.

    Atributos:
        - exito: Indica si la solicitud fue aceptada (como 'Solicitada' o 'PendienteVerificacion')
          o rechazada/bloqueada.
        - mensaje: Mensaje descriptivo legible en pantalla para el estudiante.
        - practica_id: Identificador único de la práctica creada (None si fue bloqueada previamente).
        - estado: Estado actual de la práctica ('Solicitada', 'PendienteVerificacion', 'Rechazada', o None).
        - regla_programa_id: Identificador de la ReglaPrograma vinculada (ADR-007).
        - causal_rechazo: Detalle o motivo académico del rechazo (si aplica).
        - requiere_verificacion_asincrona: Indica si la postulación quedó encolada
          para verificación asíncrona en segundo plano debido a fallo/timeout del SIA (EAC-02).
        - fecha_registro: Marca temporal en que se procesó la respuesta.
        - detalles: Diccionario opcional para metadatos o diagnósticos adicionales.
    """

    exito: bool
    mensaje: str
    practica_id: Optional[str] = None
    estado: Optional[str] = None
    regla_programa_id: Optional[str] = None
    causal_rechazo: Optional[str] = None
    requiere_verificacion_asincrona: bool = False
    fecha_registro: Optional[datetime] = None
    detalles: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.mensaje or not self.mensaje.strip():
            raise ValueError("El mensaje de respuesta no puede estar vacío.")

        # Normalizar estado si se pasa como enum EstadoPractica
        if isinstance(self.estado, EstadoPractica):
            object.__setattr__(self, "estado", self.estado.value)
        elif self.estado is not None:
            object.__setattr__(self, "estado", str(self.estado).strip())

        # Asignar fecha_registro actual si no fue provista
        if self.fecha_registro is None:
            object.__setattr__(self, "fecha_registro", datetime.now())

        object.__setattr__(self, "mensaje", self.mensaje.strip())
        if self.causal_rechazo is not None:
            object.__setattr__(self, "causal_rechazo", self.causal_rechazo.strip())

    # -- Fábricas semánticas (escenarios spec.md) -----------------------------

    @classmethod
    def solicitada(
        cls,
        *,
        practica_id: str,
        regla_programa_id: str,
        mensaje: str = "Postulación registrada exitosamente en estado 'Solicitada'.",
        fecha_registro: Optional[datetime] = None,
        detalles: Optional[dict[str, Any]] = None,
    ) -> PostulacionRespuestaDTO:
        """Crea una respuesta para una postulación aprobada de inmediato (Escenario 1)."""
        return cls(
            exito=True,
            mensaje=mensaje,
            practica_id=practica_id,
            estado=EstadoPractica.SOLICITADA.value,
            regla_programa_id=regla_programa_id,
            requiere_verificacion_asincrona=False,
            fecha_registro=fecha_registro,
            detalles=detalles,
        )

    @classmethod
    def pendiente_verificacion(
        cls,
        *,
        practica_id: str,
        regla_programa_id: str,
        mensaje: str = (
            "Solicitud recibida. Su postulación quedó en estado 'Pendiente de verificación' "
            "debido a indisponibilidad temporal del servicio de Registro Académico. "
            "Se verificará automáticamente en segundo plano."
        ),
        fecha_registro: Optional[datetime] = None,
        detalles: Optional[dict[str, Any]] = None,
    ) -> PostulacionRespuestaDTO:
        """Crea una respuesta cuando el SIA está caído o excede 5 s (EAC-02, Escenario 5)."""
        return cls(
            exito=True,
            mensaje=mensaje,
            practica_id=practica_id,
            estado=EstadoPractica.PENDIENTE_VERIFICACION.value,
            regla_programa_id=regla_programa_id,
            requiere_verificacion_asincrona=True,
            fecha_registro=fecha_registro,
            detalles=detalles,
        )

    @classmethod
    def rechazada(
        cls,
        *,
        practica_id: str,
        causal_rechazo: str,
        regla_programa_id: Optional[str] = None,
        mensaje: Optional[str] = None,
        fecha_registro: Optional[datetime] = None,
        detalles: Optional[dict[str, Any]] = None,
    ) -> PostulacionRespuestaDTO:
        """Crea una respuesta cuando no se cumplen los requisitos académicos (Escenario 2)."""
        msg = (
            mensaje.strip()
            if mensaje and mensaje.strip()
            else f"Postulación rechazada: {causal_rechazo.strip()}"
        )
        return cls(
            exito=False,
            mensaje=msg,
            practica_id=practica_id,
            estado=EstadoPractica.RECHAZADA.value,
            regla_programa_id=regla_programa_id,
            causal_rechazo=causal_rechazo.strip(),
            requiere_verificacion_asincrona=False,
            fecha_registro=fecha_registro,
            detalles=detalles,
        )

    @classmethod
    def bloqueada(
        cls,
        *,
        mensaje: str,
        causal_rechazo: Optional[str] = None,
        detalles: Optional[dict[str, Any]] = None,
    ) -> PostulacionRespuestaDTO:
        """Crea una respuesta cuando la postulación es denegada antes de persistir (Escenarios 3 y 4)."""
        return cls(
            exito=False,
            mensaje=mensaje,
            practica_id=None,
            estado=None,
            regla_programa_id=None,
            causal_rechazo=causal_rechazo,
            requiere_verificacion_asincrona=False,
            detalles=detalles,
        )
