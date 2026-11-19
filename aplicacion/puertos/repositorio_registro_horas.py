"""Puerto de persistencia para la entidad RegistroHoras.

Traza: CU-04, EAC-03, RT-01, ADR-002 (Clean Architecture y Puertos y Adaptadores), ADR-003, Vista Lógica §2.

Define el contrato formal (Protocol) que la capa de aplicación exige a los
adaptadores de persistencia para almacenar, consultar y listar reportes semanales
de horas ejecutadas por los practicantes.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from dominio.modelos.registro_horas import RegistroHoras


@runtime_checkable
class RepositorioRegistroHorasPort(Protocol):
    """Puerto de persistencia para la entidad RegistroHoras.

    Define las operaciones requeridas por el caso de uso RegistrarHorasCasoUso
    para verificar duplicados de semana y almacenar reportes semanales.
    """

    def guardar(self, registro: RegistroHoras) -> None:
        """Persiste un nuevo reporte semanal de horas en el almacén de datos.

        Args:
            registro: Instancia de RegistroHoras a persistir.
        """
        ...

    def buscar_por_id(self, registro_id: str) -> Optional[RegistroHoras]:
        """Busca y retorna un reporte de horas por su identificador único.

        Args:
            registro_id: Identificador único o UUID del reporte.

        Returns:
            La entidad RegistroHoras si existe, o None si no se encuentra.
        """
        ...

    def buscar_por_practica_y_semana(
        self, practica_id: str, semana: int
    ) -> Optional[RegistroHoras]:
        """Busca si ya existe un reporte de horas para una práctica y semana determinadas.

        Args:
            practica_id: Identificador de la práctica.
            semana: Número ordinal de la semana a consultar.

        Returns:
            La entidad RegistroHoras si ya existe reporte para esa semana, o None en caso contrario.
        """
        ...

    def listar_por_practica(self, practica_id: str) -> list[RegistroHoras]:
        """Retorna todos los reportes de horas asociados a una práctica, ordenados por semana.

        Args:
            practica_id: Identificador de la práctica.

        Returns:
            Lista de entidades RegistroHoras pertenecientes a la práctica.
        """
        ...
