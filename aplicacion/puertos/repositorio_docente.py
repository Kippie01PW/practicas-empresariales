"""Puerto de persistencia para la entidad DocenteAsesor.

Traza: CU-03, RT-01, ADR-002 (Clean Architecture y Puertos y Adaptadores), ADR-003, Vista Lógica §2.

Define el contrato formal (Protocol) que la capa de aplicación exige a los
adaptadores de persistencia para almacenar, consultar y actualizar tutores académicos,
sus cupos máximos y sus prácticas activas asignadas.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from dominio.modelos.docente_asesor import DocenteAsesor


@runtime_checkable
class RepositorioDocentePort(Protocol):
    """Puerto de persistencia para la entidad DocenteAsesor.

    Define las operaciones requeridas por el caso de uso AsignarDocenteAsesorCasoUso
    para verificar disponibilidad de cupo y persistir la carga académica de los tutores.
    """

    def guardar(self, docente: DocenteAsesor) -> None:
        """Persiste un nuevo docente asesor en el almacén de datos.

        Args:
            docente: Instancia de DocenteAsesor a persistir.
        """
        ...

    def actualizar(self, docente: DocenteAsesor) -> None:
        """Actualiza la carga y estado de un docente asesor existente.

        Args:
            docente: Instancia de DocenteAsesor con datos actualizados.
        """
        ...

    def buscar_por_id(self, docente_id: str) -> Optional[DocenteAsesor]:
        """Busca y retorna un docente asesor por su identificador único.

        Args:
            docente_id: Identificador único o UUID del docente asesor.

        Returns:
            La entidad DocenteAsesor si existe, o None si no se encuentra.
        """
        ...

    def buscar_por_documento(self, documento: str) -> Optional[DocenteAsesor]:
        """Busca y retorna un docente asesor por su documento de identidad.

        Args:
            documento: Documento de identidad del tutor académico.

        Returns:
            La entidad DocenteAsesor si existe, o None si no se encuentra.
        """
        ...

    def listar_disponibles(self) -> list[DocenteAsesor]:
        """Retorna todos los docentes asesores activos que cuenten con cupo disponible.

        Returns:
            Lista de tutores académicos con practicas_activas < cupo_maximo_practicas.
        """
        ...

    def listar_todos(self) -> list[DocenteAsesor]:
        """Retorna la lista completa de docentes asesores registrados.

        Returns:
            Lista de todas las entidades DocenteAsesor en el sistema.
        """
        ...
