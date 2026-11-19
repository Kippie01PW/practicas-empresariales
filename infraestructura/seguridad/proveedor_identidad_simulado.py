"""Proveedor simulado de identidad institucional y autenticación OIDC/SSO.

Traza: CU-01, RN-01, RN-03, ADR-002, ADR-004 (Autenticación híbrida),
ADR-005 (Autorización RBAC centralizada), Vista Lógica §2, Vista de Seguridad §2.

Simula el proveedor de identidad institucional (OpenID Connect / SSO institucional)
para emitir y verificar contextos de usuario (`ContextoUsuario`) utilizados por la
capa de aplicación para autorización RBAC y trazabilidad de identidad (ADR-004, ADR-005).
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any, Optional

from aplicacion.seguridad.autorizador_rbac import ContextoUsuario, RolUsuario


class ErrorAutenticacionOidc(Exception):
    """Excepción lanzada cuando un token OIDC o credencial institucional es inválido."""

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje: str = mensaje


class ProveedorIdentidadSimulado:
    """Simulador de OpenID Connect (OIDC) y proveedor de identidad institucional (IdP).

    Permite generar contextos de identidad auténticos para estudiantes, docentes,
    coordinadores y supervisores de empresa, así como simular la decodificación y
    validación de tokens JWT institucionales emitidos por el SSO.
    """

    def __init__(self, emisor: str = "https://sso.universidad.edu.co") -> None:
        self._emisor: str = emisor

    @property
    def emisor(self) -> str:
        return self._emisor

    # -- Métodos de autenticación directa y fábrica de contextos -----------

    def autenticar_estudiante(
        self,
        documento: str,
        correo_institucional: str,
        *,
        ip_origen: str = "127.0.0.1",
        usuario_id: Optional[str] = None,
    ) -> ContextoUsuario:
        """Emite un ContextoUsuario autenticado para un estudiante regular."""
        uid = (usuario_id or documento).strip()
        return ContextoUsuario(
            usuario_id=uid,
            rol=RolUsuario.ESTUDIANTE.value,
            documento=documento.strip(),
            correo=correo_institucional.strip(),
            ip_origen=ip_origen.strip(),
        )

    def autenticar_coordinador(
        self,
        usuario_id: str,
        correo: str,
        *,
        ip_origen: str = "127.0.0.1",
    ) -> ContextoUsuario:
        """Emite un ContextoUsuario autenticado para un Coordinador de Prácticas."""
        return ContextoUsuario(
            usuario_id=usuario_id.strip(),
            rol=RolUsuario.COORDINADOR_PRACTICAS.value,
            correo=correo.strip(),
            ip_origen=ip_origen.strip(),
        )

    def autenticar_docente(
        self,
        usuario_id: str,
        correo: str,
        *,
        documento: Optional[str] = None,
        ip_origen: str = "127.0.0.1",
    ) -> ContextoUsuario:
        """Emite un ContextoUsuario autenticado para un Docente Asesor."""
        return ContextoUsuario(
            usuario_id=usuario_id.strip(),
            rol=RolUsuario.DOCENTE_ASESOR.value,
            documento=documento.strip() if documento else None,
            correo=correo.strip(),
            ip_origen=ip_origen.strip(),
        )

    def autenticar_supervisor(
        self,
        usuario_id: str,
        correo: str,
        *,
        ip_origen: str = "127.0.0.1",
    ) -> ContextoUsuario:
        """Emite un ContextoUsuario autenticado para un Supervisor de Empresa."""
        return ContextoUsuario(
            usuario_id=usuario_id.strip(),
            rol=RolUsuario.SUPERVISOR_EMPRESA.value,
            correo=correo.strip(),
            ip_origen=ip_origen.strip(),
        )

    def crear_contexto(
        self,
        *,
        usuario_id: str,
        rol: str,
        documento: Optional[str] = None,
        correo: Optional[str] = None,
        ip_origen: str = "127.0.0.1",
    ) -> ContextoUsuario:
        """Crea un contexto personalizado con validaciones formales."""
        return ContextoUsuario(
            usuario_id=usuario_id,
            rol=rol,
            documento=documento,
            correo=correo,
            ip_origen=ip_origen,
        )

    # -- Simulación de tokens JWT OIDC (ADR-004) -----------------------------

    def generar_token_simulado(self, contexto: ContextoUsuario) -> str:
        """Genera una representación codificada (formato payload base64) de un token OIDC.

        Útil para simular el intercambio de cabeceras Authorization: Bearer <token>.
        """
        payload: dict[str, Any] = {
            "iss": self._emisor,
            "sub": contexto.usuario_id,
            "role": contexto.rol,
            "document": contexto.documento,
            "email": contexto.correo,
            "ip": contexto.ip_origen,
            "iat": int(datetime.now(timezone.utc).timestamp()),
        }
        raw_json = json.dumps(payload)
        return base64.urlsafe_b64encode(raw_json.encode("utf-8")).decode("utf-8")

    def validar_token_simulado(self, token: str) -> ContextoUsuario:
        """Decodifica un token OIDC simulado y retorna el ContextoUsuario verificado.

        Raises:
            ErrorAutenticacionOidc: Si el token está mal formado o no puede decodificarse.
        """
        try:
            raw_bytes = base64.urlsafe_b64decode(token.encode("utf-8"))
            payload: dict[str, Any] = json.loads(raw_bytes.decode("utf-8"))
        except Exception as e:
            raise ErrorAutenticacionOidc(f"Token OIDC simulado inválido o corrupto: {e}") from e

        if payload.get("iss") != self._emisor:
            raise ErrorAutenticacionOidc(
                f"Emisor del token '{payload.get('iss')}' no coincide con el IdP '{self._emisor}'."
            )

        return ContextoUsuario(
            usuario_id=str(payload.get("sub", "")),
            rol=str(payload.get("role", "")),
            documento=payload.get("document"),
            correo=payload.get("email"),
            ip_origen=str(payload.get("ip", "127.0.0.1")),
        )
