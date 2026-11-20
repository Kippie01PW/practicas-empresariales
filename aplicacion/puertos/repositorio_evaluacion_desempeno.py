"""Puerto de persistencia para la entidad EvaluacionDesempeno.

Traza: CU-07, EAC-01, EAC-03, RN-01, RN-02, RN-03, RN-04,
ADR-002 (Clean Architecture y Puertos y Adaptadores), ADR-003 (Persistencia transaccional),
ADR-010 (Máquina de estados finitos), Vista Lógica §2 (01-logica.puml).

Define el contrato formal (Protocol) que la capa de aplicación exige a los
adaptadores de persistencia para almacenar y consultar la evaluación de desempeño
asociada a una práctica empresarial (relación 1 a 0..1 entre Practica y EvaluacionDesempeno).
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from dominio.modelos.evaluacion_desempeno import EvaluacionDesempeno


@runtime_checkable
class RepositorioEvaluacionDesempenoPort(Protocol):
    """Puerto de persistencia para la entidad EvaluacionDesempeno.

    Define las operaciones requeridas por EvaluarDesempenoCasoUso para verificar
    la unicidad de evaluación por práctica (Escenario 12) y persistir la calificación
    cualitativa y cuantitativa emitida por el supervisor de empresa (Escenarios 2, 3 y 4).
    """

    def guardar(self, evaluacion: EvaluacionDesempeno) -> None:
        """Persiste una nueva evaluación de desempeño en el almacén de datos.

        Args:
            evaluacion: Instancia de EvaluacionDesempeno a persistir.
        """
        ...

    def buscar_por_id(self, evaluacion_id: str) -> Optional[EvaluacionDesempeno]:
        """Busca y retorna una evaluación de desempeño por su identificador único.

        Args:
            evaluacion_id: Identificador único o UUID de la evaluación.

        Returns:
            La entidad EvaluacionDesempeno si existe, o None si no se encuentra.
        """
        ...

    def buscar_por_practica(self, practica_id: str) -> Optional[EvaluacionDesempeno]:
        """Busca si ya existe una evaluación de desempeño asociada a la práctica indicada.

        Garantiza la verificación de la invariante de multiplicidad 1 a 0..1 entre
        Practica y EvaluacionDesempeno (Escenario 12).

        Args:
            practica_id: Identificador único de la práctica empresarial.

        Returns:
            La entidad EvaluacionDesempeno asociada a la práctica si existe,
            o None si la práctica aún no cuenta con evaluación registrada.
        """
        ...
