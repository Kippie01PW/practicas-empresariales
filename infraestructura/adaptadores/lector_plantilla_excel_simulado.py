"""Adaptador simulado de lectura de plantilla normalizada de Excel/CSV para migración (CU-15).

Traza: CU-15, OB-02, RT-02, PA-05, R-03,
ADR-002 (Clean Architecture y Puertos y Adaptadores),
ADR-003 (Plataforma tecnológica sin dependencias externas no aprobadas),
ADR-009 (Estrategia de migración inicial mediante plantilla normalizada y script CLI).

Implementa `LectorPlantillaExcelPort` permitiendo leer lotes deterministas en memoria
(listas de `FilaPlantillaMigracionDTO` o texto CSV) y archivos CSV normalizados en disco,
validando la existencia del origen, que no esté vacío y que incluya las columnas obligatorias.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Optional

from aplicacion.dtos.migracion_excel_dto import FilaPlantillaMigracionDTO
from aplicacion.puertos.lector_plantilla_excel import LectorPlantillaExcelPort
from dominio.errores import ArchivoMigracionInvalidoError


class LectorPlantillaExcelSimulado(LectorPlantillaExcelPort):
    """Adaptador determinista que implementa `LectorPlantillaExcelPort` (CU-15)."""

    COLUMNAS_OBLIGATORIAS: tuple[str, ...] = (
        "documento_estudiante",
        "programa_academico",
        "nombre_empresa",
        "supervisor_nombre",
        "docente_asesor_id",
        "horas_acumuladas",
        "estado_o_hito",
    )

    def __init__(
        self,
        lotes_iniciales: Optional[
            dict[str, list[FilaPlantillaMigracionDTO] | str]
        ] = None,
    ) -> None:
        """Inicializa el lector con lotes opcionales precargados en memoria."""
        self._lotes: dict[str, list[FilaPlantillaMigracionDTO] | str] = {}
        if lotes_iniciales:
            for origen, contenido in lotes_iniciales.items():
                self.registrar_lote(origen, contenido)

    def registrar_lote(
        self,
        origen_datos: str,
        contenido: list[FilaPlantillaMigracionDTO] | str,
    ) -> None:
        """Registra un lote de filas o contenido CSV en memoria bajo un identificador."""
        if not origen_datos or not str(origen_datos).strip():
            raise ValueError("El identificador del origen de datos no puede estar vacío.")
        self._lotes[str(origen_datos).strip()] = contenido

    def leer_filas(self, origen_datos: str) -> list[FilaPlantillaMigracionDTO]:
        """Lee y valida las filas de la plantilla normalizada desde memoria o archivo CSV."""
        if not origen_datos or not str(origen_datos).strip():
            raise ArchivoMigracionInvalidoError(
                origen_datos=origen_datos,
                detalle="El origen de datos de la plantilla no puede estar vacío.",
            )

        clave = str(origen_datos).strip()
        if clave in self._lotes:
            contenido = self._lotes[clave]
            if isinstance(contenido, str):
                return self._parsear_csv(contenido, origen_datos=clave)
            if not contenido:
                raise ArchivoMigracionInvalidoError(
                    origen_datos=clave,
                    detalle="El lote de migración no contiene registros para procesar.",
                )
            return list(contenido)

        ruta = Path(clave)
        if not ruta.exists() or not ruta.is_file():
            raise ArchivoMigracionInvalidoError(
                origen_datos=clave,
                detalle="El archivo o lote de plantilla normalizada no existe o no es legible.",
            )

        try:
            texto = ruta.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise ArchivoMigracionInvalidoError(
                origen_datos=clave,
                detalle=f"Error de lectura del archivo de plantilla: {exc}",
            ) from exc

        return self._parsear_csv(texto, origen_datos=clave)

    def _parsear_csv(
        self,
        contenido_csv: str,
        *,
        origen_datos: str,
    ) -> list[FilaPlantillaMigracionDTO]:
        """Parsea texto CSV normalizado validando encabezados obligatorios y filas no vacías."""
        if not contenido_csv or not contenido_csv.strip():
            raise ArchivoMigracionInvalidoError(
                origen_datos=origen_datos,
                detalle="La plantilla normalizada está vacía.",
            )

        lector = csv.DictReader(io.StringIO(contenido_csv.strip()))
        if not lector.fieldnames:
            raise ArchivoMigracionInvalidoError(
                origen_datos=origen_datos,
                detalle="La plantilla normalizada no contiene fila de encabezados.",
            )

        mapa_columnas = {
            col.strip().lower(): col
            for col in lector.fieldnames
            if col and col.strip()
        }
        faltantes = [
            col for col in self.COLUMNAS_OBLIGATORIAS if col not in mapa_columnas
        ]
        if faltantes:
            raise ArchivoMigracionInvalidoError(
                origen_datos=origen_datos,
                detalle=(
                    f"Faltan columnas obligatorias en la plantilla normalizada: "
                    f"{', '.join(faltantes)}."
                ),
            )

        filas: list[FilaPlantillaMigracionDTO] = []
        for numero_fila, fila_cruda in enumerate(lector, start=2):
            valores = {
                k.strip().lower(): (v.strip() if v is not None else "")
                for k, v in fila_cruda.items()
                if k and k.strip()
            }
            filas.append(
                FilaPlantillaMigracionDTO(
                    numero_fila=numero_fila,
                    documento_estudiante=valores.get("documento_estudiante", ""),
                    nombre_estudiante=valores.get("nombre_estudiante", ""),
                    correo_estudiante=valores.get("correo_estudiante", ""),
                    programa_academico=valores.get("programa_academico", ""),
                    nombre_empresa=valores.get("nombre_empresa", ""),
                    nit_empresa=valores.get("nit_empresa", ""),
                    supervisor_nombre=valores.get("supervisor_nombre", ""),
                    supervisor_correo=valores.get("supervisor_correo", ""),
                    docente_asesor_id=valores.get("docente_asesor_id", ""),
                    horas_acumuladas=valores.get("horas_acumuladas", ""),
                    estado_o_hito=valores.get("estado_o_hito", ""),
                    fecha_postulacion=valores.get("fecha_postulacion", ""),
                    fecha_inicio=valores.get("fecha_inicio", ""),
                    fecha_fin=valores.get("fecha_fin", ""),
                )
            )

        if not filas:
            raise ArchivoMigracionInvalidoError(
                origen_datos=origen_datos,
                detalle="La plantilla normalizada contiene encabezados pero ningún registro de datos.",
            )

        return filas
