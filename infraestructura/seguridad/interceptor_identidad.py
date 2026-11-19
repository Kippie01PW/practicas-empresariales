"""Interceptor de identidad para verificación criptográfica HMAC de enlaces efímeros (ADR-004).

Traza: CU-05, EAC-03, RN-04, ADR-002, ADR-004 (Autenticación híbrida),
ADR-005 (Autorización RBAC), Vista de Seguridad §2.

Permite a supervisores de empresa externos acceder a la validación de horas mediante
enlaces criptográficos efímeros (Magic Links firmados con HMAC-SHA256) sin requerir
cuenta en el directorio activo institucional. Garantiza vigencia máxima de 15 días,
carácter de un solo uso y denegación con 0 datos expuestos ante cualquier alteración.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional

from aplicacion.puertos.repositorio_token_evaluacion import RepositorioTokenEvaluacionPort
from aplicacion.seguridad.autorizador_rbac import ContextoUsuario, RolUsuario
from dominio.errores import (
    TokenEvaluacionExpiradoError,
    TokenEvaluacionInvalidoError,
    TokenEvaluacionYaUsadoError,
)
from dominio.modelos.token_evaluacion import TokenEvaluacion


class InterceptorIdentidad:
    """Componente de infraestructura para gestión y validación de tokens HMAC efímeros.

    Traza: CU-05, EAC-03, ADR-004.
    """

    def __init__(
        self,
        *,
        clave_secreta: str = "clave-secreta-hmac-magic-links-practicas-2026",
        repositorio_token: Optional[RepositorioTokenEvaluacionPort] = None,
    ) -> None:
        if not clave_secreta or not clave_secreta.strip():
            raise ValueError("La clave secreta HMAC no puede estar vacía.")
        self._clave_secreta: str = clave_secreta.strip()
        self._repositorio_token: Optional[RepositorioTokenEvaluacionPort] = repositorio_token

    def calcular_firma(self, payload: str) -> str:
        """Genera la firma HMAC-SHA256 canónica para un payload dado."""
        return hmac.new(
            self._clave_secreta.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def generar_token(
        self,
        *,
        practica_id: str,
        supervisor_id: str,
        duracion_dias: int = 15,
        fecha_emision: Optional[datetime] = None,
    ) -> TokenEvaluacion:
        """Genera un nuevo TokenEvaluacion firmado con HMAC y lo persiste si hay repositorio.

        Args:
            practica_id: Identificador de la práctica asociada.
            supervisor_id: Identificador del supervisor de empresa.
            duracion_dias: Días de vigencia del enlace (15 días por defecto, ADR-004).
            fecha_emision: Fecha de emisión opcional (por defecto ahora en UTC).

        Returns:
            Instancia de TokenEvaluacion persistida y lista para su uso.
        """
        emision = fecha_emision or datetime.now(timezone.utc)
        expiracion = emision + timedelta(days=duracion_dias)
        payload = f"{practica_id.strip()}:{supervisor_id.strip()}:{int(emision.timestamp())}"
        firma = self.calcular_firma(payload)
        token_cadena = f"ml_{payload}_{firma}"

        token_entidad = TokenEvaluacion(
            token=token_cadena,
            practica_id=practica_id.strip(),
            supervisor_id=supervisor_id.strip(),
            fecha_emision=emision,
            fecha_expiracion=expiracion,
            usado=False,
        )

        if self._repositorio_token is not None:
            self._repositorio_token.guardar(token_entidad)

        return token_entidad

    def verificar_token(
        self,
        token_str: str,
        *,
        ahora: Optional[datetime] = None,
    ) -> TokenEvaluacion:
        """Verifica la integridad HMAC, vigencia y estado de uso de un token efímero.

        Traza: CU-05, EAC-03, Escenarios 7, 8, 9, 11.

        Args:
            token_str: Cadena criptográfica presentada por el cliente.
            ahora: Instante de verificación opcional.

        Returns:
            Instancia válida de TokenEvaluacion.

        Raises:
            TokenEvaluacionInvalidoError: Si la firma HMAC es inválida o el token está adulterado.
            TokenEvaluacionYaUsadoError: Si el token ya fue utilizado.
            TokenEvaluacionExpiradoError: Si el token ha superado su vigencia de 15 días.
        """
        if not token_str or not token_str.strip():
            raise TokenEvaluacionInvalidoError("Token de acceso ausente o vacío.")

        cadena = token_str.strip()

        # Validación estructural de formato HMAC si inicia con el prefijo canónico
        if cadena.startswith("ml_"):
            try:
                partes = cadena[3:].rsplit("_", 1)
                if len(partes) != 2:
                    raise TokenEvaluacionInvalidoError()
                payload, firma_recibida = partes
                firma_esperada = self.calcular_firma(payload)
                if not hmac.compare_digest(firma_recibida, firma_esperada):
                    raise TokenEvaluacionInvalidoError("Firma criptográfica HMAC no coincide.")
            except TokenEvaluacionInvalidoError:
                raise
            except Exception as e:
                raise TokenEvaluacionInvalidoError(f"Formato de token efímero alterado: {e}") from e

        # Verificación contra almacén / repositorio
        token_entidad: Optional[TokenEvaluacion] = None
        if self._repositorio_token is not None:
            token_entidad = self._repositorio_token.buscar_por_token(cadena)

        if token_entidad is None:
            raise TokenEvaluacionInvalidoError("Token no encontrado en el sistema o adulterado.")

        if token_entidad.usado:
            raise TokenEvaluacionYaUsadoError(token_id=token_entidad.id)

        instante = ahora or datetime.now(timezone.utc)
        if not token_entidad.es_valido(instante):
            raise TokenEvaluacionExpiradoError(token_id=token_entidad.id)

        return token_entidad

    def autenticar_supervisor(
        self,
        token_str: str,
        *,
        ip_origen: str = "127.0.0.1",
        ahora: Optional[datetime] = None,
    ) -> ContextoUsuario:
        """Autentica al supervisor de empresa y emite su ContextoUsuario.

        Args:
            token_str: Cadena del token efímero.
            ip_origen: IP del cliente.
            ahora: Instante de evaluación temporal.

        Returns:
            ContextoUsuario autenticado con rol SupervisorEmpresa.
        """
        token = self.verificar_token(token_str, ahora=ahora)
        return ContextoUsuario(
            usuario_id=token.supervisor_id,
            rol=RolUsuario.SUPERVISOR_EMPRESA.value,
            ip_origen=ip_origen,
        )
