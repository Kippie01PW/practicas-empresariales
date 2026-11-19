"""Entidad de dominio EventoBitacora.

Traza: CU-01, CU-10, CU-14, EAC-03, PA-03, ADR-006 (Bitácora Append-Only),
Vista Lógica §2, §3.

Modela el registro transaccional inmutable (append-only) de auditoría
para cada cambio de estado, aprobación de actas o acceso registrado en el sistema,
garantizando el no repudio e integridad mediante sellado criptográfico SHA-256.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Any, Optional


class EventoBitacora:
    """Entidad de auditoría inmutable de solo inserción (Append-Only).

    Atributos del diagrama UML (01-logica.puml):
        - fechaHora: Marca de tiempo exacta del suceso registrado.
        - actorIdentificador: Identificador del actor (documento, correo o ID de usuario).
        - rolActor: Rol del actor al momento de la acción (Estudiante, DocenteAsesor, etc.).
        - ipOrigen: Dirección IP desde la cual se originó la petición.
        - accionRealizada: Verbo o código de la acción auditada.
        - entidadAfectada: Referencia a la entidad impactada (e.g. "Practica:<id>").
        - huellaDigital: Hash SHA-256 generado para garantizar la integridad y no repudio.

    Atributos de trazabilidad técnica (plan.md):
        - id: Identificador único del evento en bitácora.
        - detalles: Metadatos o información complementaria del suceso (opcional).
    """

    __slots__ = (
        "_id",
        "_fecha_hora",
        "_actor_identificador",
        "_rol_actor",
        "_ip_origen",
        "_accion_realizada",
        "_entidad_afectada",
        "_huella_digital",
        "_detalles",
    )

    def __init__(
        self,
        *,
        actor_identificador: str,
        rol_actor: str,
        ip_origen: str,
        accion_realizada: str,
        entidad_afectada: str,
        fecha_hora: Optional[datetime] = None,
        huella_digital: Optional[str] = None,
        detalles: Optional[dict[str, Any] | str] = None,
        id: str | None = None,
    ) -> None:
        if not actor_identificador or not actor_identificador.strip():
            raise ValueError("El identificador del actor no puede estar vacío.")
        if not rol_actor or not rol_actor.strip():
            raise ValueError("El rol del actor no puede estar vacío.")
        if not ip_origen or not ip_origen.strip():
            raise ValueError("La IP de origen no puede estar vacía.")
        if not accion_realizada or not accion_realizada.strip():
            raise ValueError("La acción realizada no puede estar vacía.")
        if not entidad_afectada or not entidad_afectada.strip():
            raise ValueError("La entidad afectada no puede estar vacía.")

        self._id: str = id or str(uuid.uuid4())
        self._fecha_hora: datetime = fecha_hora or datetime.now()
        self._actor_identificador: str = actor_identificador.strip()
        self._rol_actor: str = rol_actor.strip()
        self._ip_origen: str = ip_origen.strip()
        self._accion_realizada: str = accion_realizada.strip()
        self._entidad_afectada: str = entidad_afectada.strip()
        self._detalles: Optional[dict[str, Any] | str] = detalles

        self._huella_digital: str = (
            huella_digital.strip()
            if huella_digital and huella_digital.strip()
            else self._calcular_hash(
                fecha_hora=self._fecha_hora,
                actor_identificador=self._actor_identificador,
                rol_actor=self._rol_actor,
                ip_origen=self._ip_origen,
                accion_realizada=self._accion_realizada,
                entidad_afectada=self._entidad_afectada,
            )
        )

    # -- Propiedades de solo lectura (Append-Only) --------------------------

    @property
    def id(self) -> str:
        return self._id

    @property
    def fecha_hora(self) -> datetime:
        return self._fecha_hora

    @property
    def actor_identificador(self) -> str:
        return self._actor_identificador

    @property
    def rol_actor(self) -> str:
        return self._rol_actor

    @property
    def ip_origen(self) -> str:
        return self._ip_origen

    @property
    def accion_realizada(self) -> str:
        return self._accion_realizada

    @property
    def entidad_afectada(self) -> str:
        return self._entidad_afectada

    @property
    def huella_digital(self) -> str:
        return self._huella_digital

    @property
    def detalles(self) -> Optional[dict[str, Any] | str]:
        return self._detalles

    # -- Integridad y seguridad (ADR-006) -----------------------------------

    @staticmethod
    def _calcular_hash(
        *,
        fecha_hora: datetime,
        actor_identificador: str,
        rol_actor: str,
        ip_origen: str,
        accion_realizada: str,
        entidad_afectada: str,
    ) -> str:
        """Calcula el hash SHA-256 canónico para sellar la inmutabilidad del evento."""
        mensaje = (
            f"{fecha_hora.isoformat()}|"
            f"{actor_identificador}|"
            f"{rol_actor}|"
            f"{ip_origen}|"
            f"{accion_realizada}|"
            f"{entidad_afectada}"
        )
        return hashlib.sha256(mensaje.encode("utf-8")).hexdigest()

    def verificar_integridad(self) -> bool:
        """Verifica que los atributos del evento coincidan con su huella digital criptográfica."""
        hash_esperado = self._calcular_hash(
            fecha_hora=self._fecha_hora,
            actor_identificador=self._actor_identificador,
            rol_actor=self._rol_actor,
            ip_origen=self._ip_origen,
            accion_realizada=self._accion_realizada,
            entidad_afectada=self._entidad_afectada,
        )
        return self._huella_digital == hash_esperado

    # -- Representación e igualdad -----------------------------------------

    def __repr__(self) -> str:
        return (
            f"EventoBitacora(id={self._id!r}, "
            f"accion={self._accion_realizada!r}, "
            f"entidad={self._entidad_afectada!r}, "
            f"actor={self._actor_identificador!r}, "
            f"fecha={self._fecha_hora.isoformat()})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EventoBitacora):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)
