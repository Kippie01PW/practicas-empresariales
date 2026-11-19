"""Puerto de repositorio para la entidad TokenEvaluacion (CU-05).

Traza: CU-05, EAC-03, ADR-002 (Puertos y Adaptadores), ADR-004 (Autenticación
híbrida con enlaces criptográficos efímeros).

Define el contrato (Protocol) que deben implementar los adaptadores de
persistencia de tokens de evaluación efímeros. Este puerto vive en la capa
de aplicación; los adaptadores concretos residen en infraestructura/.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from dominio.modelos.token_evaluacion import TokenEvaluacion


@runtime_checkable
class RepositorioTokenEvaluacionPort(Protocol):
    """Contrato de acceso a datos para la entidad TokenEvaluacion.

    Traza: CU-05, ADR-002 (Puertos y Adaptadores), ADR-004.

    Los implementadores concretos (InMemoryRepositorioTokenEvaluacion y, en
    producción, el adaptador PostgreSQL) deben proveer las tres operaciones
    definidas aquí. El puerto no impone detalles de persistencia.
    """

    def guardar(self, token: TokenEvaluacion) -> None:
        """Persiste o actualiza un TokenEvaluacion en el almacén.

        Si el token ya existe (mismo id), actualiza su estado (e.g. marcado
        como usado). Si no existe, lo inserta.

        Args:
            token: Instancia de TokenEvaluacion a persistir.
        """
        ...

    def buscar_por_token(self, token: str) -> Optional[TokenEvaluacion]:
        """Recupera un TokenEvaluacion a partir de su cadena criptográfica.

        Se utiliza en el flujo de autenticación de Magic Links: el interceptor
        de identidad extrae la cadena del enlace y consulta este método para
        validar existencia, vigencia y estado de uso (ADR-004).

        Args:
            token: Cadena criptográfica (firma HMAC) del enlace efímero.

        Returns:
            La instancia de TokenEvaluacion si existe; None si no se encuentra.
        """
        ...

    def buscar_por_id(self, token_id: str) -> Optional[TokenEvaluacion]:
        """Recupera un TokenEvaluacion a partir de su identificador único.

        Args:
            token_id: Identificador único del token.

        Returns:
            La instancia de TokenEvaluacion si existe; None si no se encuentra.
        """
        ...
