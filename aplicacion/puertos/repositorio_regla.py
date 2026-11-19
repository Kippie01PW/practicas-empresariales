"""Puerto de persistencia para ReglaPrograma versionada.

Traza: CU-01, CU-12, EAC-01, ADR-002 (Clean Architecture y Puertos y Adaptadores),
ADR-007 (Reglas declarativas versionadas por programa), Vista Lógica §2.

Define el contrato formal (Protocol) para consultar las reglas normativas
y plantillas activas por programa académico al momento de postular una práctica,
garantizando inmutabilidad normativa en prácticas activas o pasadas.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from dominio.modelos.regla_programa import ReglaPrograma


@runtime_checkable
class RepositorioReglaProgramaPort(Protocol):
    """Puerto de persistencia para la configuración declarativa de reglas de programa.

    Define las operaciones requeridas para recuperar la regla activa vigente
    asociada al programa académico del estudiante al momento de postularse.
    """

    def buscar_activa_por_programa(
        self, programa_academico: str
    ) -> Optional[ReglaPrograma]:
        """Recupera la regla de programa actualmente activa y vigente para un programa.

        Args:
            programa_academico: Nombre o código identificador del programa académico.

        Returns:
            La entidad ReglaPrograma activa vigente si existe, o None si no hay
            ninguna regla activa configurada para dicho programa (spec.md escenario 4).
        """
        ...

    def guardar(self, regla: ReglaPrograma) -> None:
        """Persiste una regla de programa en el almacén de datos.

        Args:
            regla: Instancia de ReglaPrograma a registrar.
        """
        ...

    def buscar_por_id(self, regla_id: str) -> Optional[ReglaPrograma]:
        """Recupera una regla de programa por su identificador único.

        Args:
            regla_id: Identificador único UUID de la regla versionada.

        Returns:
            La entidad ReglaPrograma correspondiente si existe, o None si no se encuentra.
        """
        ...
