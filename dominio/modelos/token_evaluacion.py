"""Entidad de dominio TokenEvaluacion.

Traza: CU-05, EAC-03, ADR-002, ADR-004 (Autenticación híbrida con enlaces
criptográficos efímeros), Vista Lógica §2.

Modela la credencial criptográfica efímera utilizada por los supervisores de empresa
externos para acceder al formulario de validación de horas sin requerir una cuenta
en el directorio activo universitario. Implementa control de vigencia (15 días
calendario) y de un solo uso (el token queda consumido al asentar una validación
en firme).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from dominio.errores import TokenEvaluacionYaUsadoError


class TokenEvaluacion:
    """Credencial criptográfica efímera para supervisores de empresa externos.

    Atributos del plan técnico (plan.md, 005-validar-horas-registradas):
        - id: Identificador único del token.
        - token: Cadena criptográfica (firma HMAC) del enlace efímero.
        - practica_id: Identificador de la práctica a la que está vinculado el token.
        - supervisor_id: Identificador del supervisor de empresa al que se emitió.
        - fecha_emision: Marca temporal de creación del token.
        - fecha_expiracion: Marca temporal de expiración (fecha_emision + 15 días, ADR-004).
        - usado: Bandera que indica si el token fue consumido para asentar una validación.
        - fecha_uso: Fecha y hora en que fue consumido (None si aún no fue usado).

    Invariantes de dominio:
        - Un token es válido si y solo si no fue usado Y la fecha actual es anterior
          o igual a fecha_expiracion (es_valido).
        - Un token no puede ser marcado como usado más de una vez (marcar_usado).
    """

    __slots__ = (
        "_id",
        "_token",
        "_practica_id",
        "_supervisor_id",
        "_fecha_emision",
        "_fecha_expiracion",
        "_usado",
        "_fecha_uso",
    )

    _DIAS_EXPIRACION: int = 15

    def __init__(
        self,
        *,
        token: str,
        practica_id: str,
        supervisor_id: str,
        fecha_emision: Optional[datetime] = None,
        fecha_expiracion: Optional[datetime] = None,
        usado: bool = False,
        fecha_uso: Optional[datetime] = None,
        id: Optional[str] = None,
    ) -> None:
        if not token or not token.strip():
            raise ValueError("El token criptográfico no puede estar vacío.")
        if not practica_id or not practica_id.strip():
            raise ValueError("El identificador de la práctica es obligatorio.")
        if not supervisor_id or not supervisor_id.strip():
            raise ValueError("El identificador del supervisor es obligatorio.")

        ahora: datetime = datetime.now(timezone.utc)

        self._id: str = id or str(uuid.uuid4())
        self._token: str = token.strip()
        self._practica_id: str = practica_id.strip()
        self._supervisor_id: str = supervisor_id.strip()
        self._fecha_emision: datetime = fecha_emision or ahora
        self._fecha_expiracion: datetime = fecha_expiracion or (
            self._fecha_emision + timedelta(days=self._DIAS_EXPIRACION)
        )
        self._usado: bool = usado
        self._fecha_uso: Optional[datetime] = fecha_uso

    # -- Propiedades de solo lectura ----------------------------------------

    @property
    def id(self) -> str:
        return self._id

    @property
    def token(self) -> str:
        return self._token

    @property
    def practica_id(self) -> str:
        return self._practica_id

    @property
    def supervisor_id(self) -> str:
        return self._supervisor_id

    @property
    def fecha_emision(self) -> datetime:
        return self._fecha_emision

    @property
    def fecha_expiracion(self) -> datetime:
        return self._fecha_expiracion

    @property
    def usado(self) -> bool:
        return self._usado

    @property
    def fecha_uso(self) -> Optional[datetime]:
        return self._fecha_uso

    # -- Métodos de dominio --------------------------------------------------

    def es_valido(self, ahora: Optional[datetime] = None) -> bool:
        """Verifica si el token es válido en el momento indicado.

        Un token es válido si:
        1. No ha sido utilizado previamente (Escenario 9).
        2. La fecha actual no supera la fecha de expiración (15 días, Escenario 7).

        Args:
            ahora: Instante de verificación (default: datetime.now en UTC).

        Returns:
            True si el token es válido; False en cualquier otro caso.
        """
        instante: datetime = ahora or datetime.now(timezone.utc)

        # Normalizar a timezone-aware para comparaciones seguras
        if instante.tzinfo is None:
            instante = instante.replace(tzinfo=timezone.utc)

        fecha_exp = self._fecha_expiracion
        if fecha_exp.tzinfo is None:
            fecha_exp = fecha_exp.replace(tzinfo=timezone.utc)

        return not self._usado and instante <= fecha_exp

    def marcar_usado(self, fecha_uso: Optional[datetime] = None) -> None:
        """Marca el token como consumido tras asentar una validación en firme.

        Solo puede marcarse como usado una vez. Intentar marcarlo por segunda vez
        lanza TokenEvaluacionYaUsadoError (Escenario 9).

        Args:
            fecha_uso: Fecha y hora del consumo (default: datetime.now en UTC).

        Raises:
            TokenEvaluacionYaUsadoError: Si el token ya fue utilizado previamente.
        """
        if self._usado:
            raise TokenEvaluacionYaUsadoError(token_id=self._id)

        self._usado = True
        self._fecha_uso = fecha_uso or datetime.now(timezone.utc)

    def invalidar(self, fecha_invalidacion: Optional[datetime] = None) -> None:
        """Invalida explícitamente el token al ser reemplazado o renovado por expiración.

        Traza: CU-08, Escenarios 2, 3, 6 y 11, ADR-004, EAC-03.
        Cuando la tarea de recordatorios emite un nuevo TokenEvaluacion para reemplazar
        uno que superó los 15 días calendario de vigencia, este método deja el token
        anterior explícitamente consumido/invalidado de forma idempotente para impedir
        su uso futuro.

        Args:
            fecha_invalidacion: Instante de invalidación (default: datetime.now en UTC).
        """
        instante: datetime = fecha_invalidacion or datetime.now(timezone.utc)
        if not self._usado:
            self._usado = True
            self._fecha_uso = instante
        elif self._fecha_uso is None:
            self._fecha_uso = instante

    # -- Representación e igualdad ------------------------------------------

    def __repr__(self) -> str:
        return (
            f"TokenEvaluacion(id={self._id!r}, "
            f"practica_id={self._practica_id!r}, "
            f"supervisor_id={self._supervisor_id!r}, "
            f"usado={self._usado!r}, "
            f"expira={self._fecha_expiracion.isoformat()})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TokenEvaluacion):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)
