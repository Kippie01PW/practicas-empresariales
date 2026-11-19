"""Entidad de dominio ReglaPrograma y enumeración EstadoVigenciaRegla.

Traza: CU-01, CU-12, EAC-01, ADR-007 (Reglas versionadas por programa).

Modela la configuración normativa versionada por programa académico
(horas requeridas, criterios de rúbrica, plantilla de acta y vigencia),
asegurando inmutabilidad normativa para prácticas activas o pasadas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class EstadoVigenciaRegla(Enum):
    """Estados de vigencia de una regla de programa (ADR-007)."""

    ACTIVA = "Activa"
    BORRADOR = "Borrador"
    INACTIVA = "Inactiva"


class ReglaPrograma:
    """Entidad de dominio que representa las reglas y plantillas versionadas por programa.

    Atributos del diagrama UML (01-logica.puml):
        - programaAcademico: Nombre o código del programa académico.
        - version: Versión de la regla (e.g. "1.0", "2026-1").
        - horasRequeridas: Cantidad de horas obligatorias de práctica.
        - criteriosRubrica: Criterios o rúbrica de evaluación aplicables.
        - plantillaActa: Nombre o identificador de la plantilla HTML/CSS para acta final.
        - estadoVigencia: Estado de vigencia (Activa, Borrador, Inactiva).
        - fechaVigencia: Fecha en la cual entra o entró en vigor la regla.

    Atributos de trazabilidad técnica (plan.md):
        - id: Identificador único de la regla versionada.
    """

    __slots__ = (
        "_id",
        "_programa_academico",
        "_version",
        "_horas_requeridas",
        "_criterios_rubrica",
        "_plantilla_acta",
        "_estado_vigencia",
        "_fecha_vigencia",
    )

    def __init__(
        self,
        *,
        programa_academico: str,
        version: str,
        horas_requeridas: int,
        criterios_rubrica: Optional[dict[str, Any] | list[Any]] = None,
        plantilla_acta: str = "plantilla_acta_default.html",
        estado_vigencia: EstadoVigenciaRegla = EstadoVigenciaRegla.ACTIVA,
        fecha_vigencia: Optional[datetime] = None,
        id: str | None = None,
    ) -> None:
        if not programa_academico or not programa_academico.strip():
            raise ValueError("El programa académico no puede estar vacío.")
        if not version or not version.strip():
            raise ValueError("La versión de la regla no puede estar vacía.")
        if horas_requeridas <= 0:
            raise ValueError("Las horas requeridas deben ser mayores a cero.")

        self._id: str = id or str(uuid.uuid4())
        self._programa_academico: str = programa_academico.strip()
        self._version: str = version.strip()
        self._horas_requeridas: int = horas_requeridas
        self._criterios_rubrica: dict[str, Any] | list[Any] = (
            criterios_rubrica if criterios_rubrica is not None else {}
        )
        self._plantilla_acta: str = plantilla_acta.strip()
        self._estado_vigencia: EstadoVigenciaRegla = estado_vigencia
        self._fecha_vigencia: datetime = fecha_vigencia or datetime.now()

    # -- Propiedades de lectura --------------------------------------------

    @property
    def id(self) -> str:
        return self._id

    @property
    def programa_academico(self) -> str:
        return self._programa_academico

    @property
    def version(self) -> str:
        return self._version

    @property
    def horas_requeridas(self) -> int:
        return self._horas_requeridas

    @property
    def criterios_rubrica(self) -> dict[str, Any] | list[Any]:
        return self._criterios_rubrica

    @property
    def plantilla_acta(self) -> str:
        return self._plantilla_acta

    @property
    def estado_vigencia(self) -> EstadoVigenciaRegla:
        return self._estado_vigencia

    @property
    def fecha_vigencia(self) -> datetime:
        return self._fecha_vigencia

    # -- Métodos de negocio y transiciones (ADR-007) -----------------------

    def es_activa(self) -> bool:
        """Determina si la regla de programa se encuentra activa y vigente."""
        return self._estado_vigencia == EstadoVigenciaRegla.ACTIVA

    def activar(self) -> None:
        """Activa la regla para nuevas prácticas del programa académico."""
        self._estado_vigencia = EstadoVigenciaRegla.ACTIVA

    def desactivar(self) -> None:
        """Desactiva la regla para impedir su asignación a nuevas prácticas."""
        self._estado_vigencia = EstadoVigenciaRegla.INACTIVA

    # -- Representación e igualdad -----------------------------------------

    def __repr__(self) -> str:
        return (
            f"ReglaPrograma(id={self._id!r}, "
            f"programa_academico={self._programa_academico!r}, "
            f"version={self._version!r}, "
            f"estado_vigencia={self._estado_vigencia.value!r}, "
            f"horas_requeridas={self._horas_requeridas})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ReglaPrograma):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)
