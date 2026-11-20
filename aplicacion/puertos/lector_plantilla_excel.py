"""Puerto de lectura de la plantilla normalizada de Excel para migración inicial (CU-15).

Traza: CU-15, OB-02, RT-02, PA-05, R-03,
ADR-002 (Clean Architecture y Puertos y Adaptadores),
ADR-009 (Estrategia de migración inicial mediante plantilla normalizada y script CLI).

Define el contrato formal (Protocol) que la capa de aplicación exige al adaptador de
lectura de plantillas normalizadas de Excel/CSV para extraer las filas crudas de
migración sin acoplar el caso de uso a formatos de archivo o librerías concretas.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from aplicacion.dtos.migracion_excel_dto import FilaPlantillaMigracionDTO


@runtime_checkable
class LectorPlantillaExcelPort(Protocol):
    """Puerto de salida para leer filas desde la plantilla normalizada de migración (CU-15)."""

    def leer_filas(self, origen_datos: str) -> list[FilaPlantillaMigracionDTO]:
        """Lee las filas de la plantilla normalizada de Excel o lote en memoria.

        Args:
            origen_datos: Ruta al archivo normalizado (CSV/Excel) o identificador del lote.

        Returns:
            Lista de DTOs inmutables `FilaPlantillaMigracionDTO` con los datos crudos
            de cada fila leída, preservando el número de fila original.

        Raises:
            ArchivoMigracionInvalidoError: Si el origen no existe, está vacío o carece
                de las columnas obligatorias requeridas por la plantilla normalizada.
        """
        ...
