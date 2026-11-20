"""Puerto de persistencia para la entidad ActaFinal.

Traza: CU-09, CU-10, EAC-01, EAC-03, OB-01, OB-05, PA-03, RN-01, RN-02, RN-03, DT-02,
ADR-002 (Clean Architecture y Puertos y Adaptadores), ADR-003 (Persistencia transaccional),
ADR-008 (Generación y preservación del acta final con sellado SHA-256),
ADR-010 (Máquina de estados finitos), Vista Lógica §2 (01-logica.puml).

Define el contrato formal (Protocol) que la capa de aplicación exige a los
adaptadores de persistencia para almacenar, actualizar, consultar la unicidad
por práctica (relación 1 a 0..1 entre Practica y ActaFinal), generar el consecutivo
anual de número de acta ("ACTA-<AÑO>-<NNNN>") y ejecutar compensaciones transaccionales
ante fallos de almacenamiento (DT-02, Escenario 10).
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from dominio.modelos.acta_final import ActaFinal


@runtime_checkable
class RepositorioActaFinalPort(Protocol):
    """Puerto de persistencia para la entidad ActaFinal.

    Define las operaciones requeridas por GenerarActaFinalCasoUso (CU-09) y
    AprobarActaElectronicamenteCasoUso (CU-10) para verificar la unicidad
    del acta por práctica (Escenario 5), asignar el número consecutivo anual
    (Escenarios 1 y 6), persistir y actualizar el registro sellado con hash SHA-256
    y revertir registros parciales mediante compensación atómica (Escenario 10, DT-02).
    """

    def guardar(self, acta: ActaFinal) -> None:
        """Persiste una nueva instancia de ActaFinal en el almacén de datos.

        Args:
            acta: Instancia de la entidad ActaFinal a persistir.
        """
        ...

    def actualizar(self, acta: ActaFinal) -> None:
        """Actualiza el estado de firmas electrónicas y datos de un ActaFinal existente.

        Args:
            acta: Instancia de ActaFinal con sus atributos y firmas actualizadas (CU-10).
        """
        ...

    def buscar_por_id(self, acta_id: str) -> Optional[ActaFinal]:
        """Busca y retorna un acta final por su identificador único.

        Args:
            acta_id: Identificador único o UUID del ActaFinal.

        Returns:
            La entidad ActaFinal correspondiente si existe, o None si no se encuentra.
        """
        ...

    def buscar_por_practica(self, practica_id: str) -> Optional[ActaFinal]:
        """Busca si ya existe un acta final asociada a la práctica empresarial indicada.

        Garantiza la verificación de la invariante de multiplicidad 1 a 0..1 entre
        Practica y ActaFinal (CU-09 Escenario 5 y CU-10 Escenarios 1 a 6).

        Args:
            practica_id: Identificador único de la práctica empresarial.

        Returns:
            La entidad ActaFinal asociada a la práctica si existe,
            o None si la práctica aún no tiene un ActaFinal emitida.
        """
        ...

    def buscar_por_numero_acta(self, numero_acta: str) -> Optional[ActaFinal]:
        """Busca y retorna un acta final por su número oficial consecutivo anual.

        Args:
            numero_acta: Número oficial del acta (ej. "ACTA-2026-0001").

        Returns:
            La entidad ActaFinal correspondiente si existe, o None si no se encuentra.
        """
        ...

    def siguiente_numero_acta(self, anio: int) -> str:
        """Genera el siguiente número oficial consecutivo anual para un acta final.

        Cumple el formato institucional "ACTA-<AÑO>-<NNNN>" (ej. "ACTA-2026-0001")
        definido en CU-09 (Escenarios 1 y 6).

        Args:
            anio: Año calendario de emisión del acta (ej. 2026).

        Returns:
            Cadena con el número de acta consecutivo formateado ("ACTA-<AÑO>-<NNNN>").
        """
        ...

    def eliminar_por_id(self, acta_id: str) -> None:
        """Elimina un registro de ActaFinal por su identificador para compensación transaccional.

        Permite revertir la operación cuando ocurre un fallo posterior en la transacción
        evitando inconsistencias entre el repositorio de actas PDF y la base de datos
        (DT-02, CU-09 Escenario 10).

        Args:
            acta_id: Identificador único del ActaFinal a revertir.
        """
        ...

    def listar_todas(self) -> list[ActaFinal]:
        """Retorna todas las actas finales registradas en el almacén de datos.

        Returns:
            Lista de instancias de ActaFinal almacenadas.
        """
        ...
