"""Puerto de persistencia para la entidad ActaFinal.

Traza: CU-09, CU-10, EAC-03, OB-05, PA-03, RN-01, RN-02, RN-03,
ADR-002 (Clean Architecture y Puertos y Adaptadores), ADR-003 (Persistencia transaccional),
ADR-008 (Generación y preservación de actas en PDF con sellado SHA-256),
ADR-010 (Máquina de estados finitos), Vista Lógica §2 (01-logica.puml).

Define el contrato formal (Protocol) que la capa de aplicación exige a los
adaptadores de persistencia para almacenar, actualizar y consultar el acta final
asociada a una práctica empresarial (relación 1 a 0..1 entre Practica y ActaFinal).
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from dominio.modelos.acta_final import ActaFinal


@runtime_checkable
class RepositorioActaFinalPort(Protocol):
    """Puerto de persistencia para la entidad ActaFinal.

    Define las operaciones requeridas por los casos de uso de gestión y aprobación
    electrónica de actas (CU-10) para almacenar, actualizar y consultar instancias
    de ActaFinal por su identificador único o por el identificador de la práctica.
    """

    def guardar(self, acta: ActaFinal) -> None:
        """Persiste una nueva acta final en el almacén de datos.

        Args:
            acta: Instancia de ActaFinal a persistir.
        """
        ...

    def actualizar(self, acta: ActaFinal) -> None:
        """Actualiza el estado de firmas electrónicas y datos de un acta final existente.

        Args:
            acta: Instancia de ActaFinal con sus atributos actualizados.
        """
        ...

    def buscar_por_id(self, acta_id: str) -> Optional[ActaFinal]:
        """Busca y retorna un acta final por su identificador único.

        Args:
            acta_id: Identificador único del acta final.

        Returns:
            La entidad ActaFinal correspondiente si existe, o None si no se encuentra.
        """
        ...

    def buscar_por_practica(self, practica_id: str) -> Optional[ActaFinal]:
        """Busca el acta final asociada a una práctica empresarial específica.

        Garantiza la consulta sobre la relación 1 a 0..1 entre Practica y ActaFinal
        (Escenarios 1 a 6 de CU-10).

        Args:
            practica_id: Identificador único de la práctica empresarial.

        Returns:
            La entidad ActaFinal asociada a la práctica si existe,
            o None si la práctica aún no cuenta con un acta final generada.
        """
        ...
