"""Puerto de persistencia para la entidad Práctica, Intentos de Validación y Eventos de Bitácora.

Traza: CU-01, EAC-02, ADR-001 (Resiliencia e integración asíncrona),
ADR-002 (Clean Architecture y Puertos y Adaptadores), ADR-003 (Persistencia transaccional),
ADR-006 (Bitácora Append-Only), ADR-010 (Máquina de estados finitos), Vista Lógica §2.

Define el contrato formal (Protocol) que la capa de aplicación exige a los
adaptadores de persistencia (PostgreSQL en producción o InMemory en pruebas/desarrollo)
para almacenar y consultar prácticas empresariales, trazas de validación con el SIA
y registros inmutables de auditoría.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.intento_validacion import IntentoValidacion
from dominio.modelos.practica import Practica


@runtime_checkable
class RepositorioPracticaPort(Protocol):
    """Puerto de persistencia para el agregado Práctica, sus intentos de validación y bitácora.

    Define las operaciones requeridas por los casos de uso PostularEstudianteCasoUso
    y ReintentarValidacionSiaCasoUso para la persistencia transaccional del ciclo
    de vida de la práctica empresarial.
    """

    def guardar(self, practica: Practica) -> None:
        """Persiste una nueva práctica en el almacén de datos.

        Args:
            practica: Instancia de la entidad Practica a persistir.
        """
        ...

    def actualizar(self, practica: Practica) -> None:
        """Actualiza el estado y datos de una práctica existente.

        Args:
            practica: Instancia de la entidad Practica con su nuevo estado.
        """
        ...

    def buscar_por_id(self, practica_id: str) -> Optional[Practica]:
        """Busca y retorna una práctica por su identificador único.

        Args:
            practica_id: Identificador único UUID de la práctica.

        Returns:
            La entidad Practica correspondiente si existe, o None si no se encuentra.
        """
        ...

    def buscar_activa_por_estudiante(self, estudiante_id: str) -> Optional[Practica]:
        """Busca si el estudiante cuenta con una práctica activa en curso.

        Estados considerados como práctica activa:
            Aprobada, Asignada, EnEjecucion, Evaluada (ADR-010, spec.md escenario 3).

        Args:
            estudiante_id: Identificador o documento del estudiante solicitante.

        Returns:
            La entidad Practica activa si existe, o None si el estudiante no tiene
            prácticas activas en curso.
        """
        ...

    def guardar_intento_validacion(self, intento: IntentoValidacion) -> None:
        """Registra un intento de validación frente al SIA (ADR-001, EAC-02).

        Args:
            intento: Instancia inmutable de IntentoValidacion a registrar.
        """
        ...

    def buscar_intentos_por_practica(self, practica_id: str) -> list[IntentoValidacion]:
        """Recupera el historial de intentos de validación asociados a una práctica.

        Args:
            practica_id: Identificador único de la práctica.

        Returns:
            Lista con los intentos de validación registrados para la práctica,
            ordenados cronológicamente por número de intento o fecha.
        """
        ...

    def guardar_evento_bitacora(self, evento: EventoBitacora) -> None:
        """Registra un evento inmutable de auditoría en la bitácora append-only (ADR-006).

        Args:
            evento: Instancia inmutable de EventoBitacora a insertar.
        """
        ...

    def buscar_eventos_por_entidad(self, entidad_afectada: str) -> list[EventoBitacora]:
        """Recupera los eventos de bitácora asociados a una entidad específica.

        Args:
            entidad_afectada: Identificador o referencia de la entidad (ej. "Practica:<id>").

        Returns:
            Lista de eventos de bitácora correspondientes a la entidad afectada.
        """
        ...
