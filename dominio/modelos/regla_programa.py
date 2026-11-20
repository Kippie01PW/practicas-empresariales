"""Entidad de dominio ReglaPrograma y enumeración EstadoVigenciaRegla.

Traza: CU-01, CU-12, EAC-01, OB-05, PA-01, ADR-002, ADR-007 (Reglas versionadas por programa).

Modela la configuración normativa versionada por programa académico
(horas requeridas, criterios de rúbrica, plantilla de acta y vigencia),
asegurando inmutabilidad normativa para prácticas activas o pasadas.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Optional, Sequence

from dominio.errores import (
    CriteriosRubricaInvalidosError,
    DatosReglaProgramaInvalidosError,
    ReglaProgramaInmutableError,
)


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
        - horasRequeridas: Cantidad de horas obligatorias de práctica (entero positivo > 0).
        - criteriosRubrica: Criterios o rúbrica de evaluación aplicables (lista simple sin peso o diccionario).
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
        programa_validado = self._validar_texto_obligatorio(
            programa_academico, campo="programaAcademico"
        )
        version_validada = self._validar_texto_obligatorio(
            version, campo="version"
        )
        plantilla_validada = self._validar_texto_obligatorio(
            plantilla_acta, campo="plantillaActa"
        )
        horas_validadas = self._validar_horas_requeridas(horas_requeridas)
        criterios_validados = self._validar_criterios_rubrica(
            criterios_rubrica,
            exigir_no_vacio=(criterios_rubrica is not None),
        )

        self._id: str = id.strip() if isinstance(id, str) and id.strip() else str(uuid.uuid4())
        self._programa_academico: str = programa_validado
        self._version: str = version_validada
        self._horas_requeridas: int = horas_validadas
        self._criterios_rubrica: dict[str, Any] | list[str] = criterios_validados
        self._plantilla_acta: str = plantilla_validada
        self._estado_vigencia: EstadoVigenciaRegla = estado_vigencia
        self._fecha_vigencia: datetime = fecha_vigencia or datetime.now()

    # -- Métodos de validación de invariantes normativas (CU-12) -----------

    @classmethod
    def _validar_texto_obligatorio(cls, valor: Any, *, campo: str) -> str:
        """Valida que un atributo textual obligatorio sea una cadena no vacía (Escenario 5)."""
        if not isinstance(valor, str) or not valor.strip():
            raise DatosReglaProgramaInvalidosError(campo=campo, valor=valor)
        return valor.strip()

    @classmethod
    def _validar_horas_requeridas(cls, horas_requeridas: Any) -> int:
        """Valida que horasRequeridas sea estrictamente un número entero positivo mayor a 0 (Escenario 5)."""
        if (
            isinstance(horas_requeridas, bool)
            or not isinstance(horas_requeridas, int)
            or horas_requeridas <= 0
        ):
            raise DatosReglaProgramaInvalidosError(
                campo="horasRequeridas",
                valor=horas_requeridas,
            )
        return horas_requeridas

    @classmethod
    def _es_peso_positivo_valido(cls, valor: Any) -> bool:
        """Verifica si un peso o ponderación numérica es un número positivo mayor a 0."""
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return False
        valor_float = float(valor)
        if math.isnan(valor_float) or math.isinf(valor_float):
            return False
        return valor_float > 0.0

    @classmethod
    def _validar_criterios_rubrica(
        cls,
        criterios_rubrica: Any,
        *,
        exigir_no_vacio: bool = True,
    ) -> dict[str, Any] | list[str]:
        """Valida que criteriosRubrica sea una lista simple no vacía de criterios sin peso o un diccionario válido.

        Traza: CU-12, Escenario 1, Escenario 2, Escenario 6, ADR-007.
        """
        if criterios_rubrica is None:
            if exigir_no_vacio:
                raise CriteriosRubricaInvalidosError(
                    detalle="No se proporcionaron criterios de rúbrica"
                )
            return {}

        if isinstance(criterios_rubrica, Mapping):
            if len(criterios_rubrica) == 0:
                raise CriteriosRubricaInvalidosError(
                    detalle="El diccionario de criterios de rúbrica no puede estar vacío"
                )

            diccionario_limpio: dict[str, Any] = {}
            for clave_raw, valor_raw in criterios_rubrica.items():
                if not isinstance(clave_raw, str) or not clave_raw.strip():
                    raise CriteriosRubricaInvalidosError(
                        detalle="Los nombres de criterio en la rúbrica no pueden estar vacíos o en blanco"
                    )
                nombre_criterio = clave_raw.strip()
                if nombre_criterio in diccionario_limpio:
                    raise CriteriosRubricaInvalidosError(
                        detalle=f"Criterio duplicado en la rúbrica: '{nombre_criterio}'"
                    )

                if isinstance(valor_raw, Mapping):
                    if "peso" in valor_raw and not cls._es_peso_positivo_valido(valor_raw["peso"]):
                        raise CriteriosRubricaInvalidosError(
                            detalle=(
                                f"La ponderación del criterio '{nombre_criterio}' debe ser mayor a 0 "
                                f"(recibido: {valor_raw['peso']!r})"
                            )
                        )
                    diccionario_limpio[nombre_criterio] = dict(valor_raw)
                else:
                    if not cls._es_peso_positivo_valido(valor_raw):
                        raise CriteriosRubricaInvalidosError(
                            detalle=(
                                f"La ponderación del criterio '{nombre_criterio}' debe ser un número "
                                f"positivo mayor a 0 (recibido: {valor_raw!r})"
                            )
                        )
                    diccionario_limpio[nombre_criterio] = valor_raw

            return diccionario_limpio

        if isinstance(criterios_rubrica, Sequence) and not isinstance(
            criterios_rubrica, (str, bytes, bytearray)
        ):
            if len(criterios_rubrica) == 0:
                raise CriteriosRubricaInvalidosError(
                    detalle="La lista de criterios de rúbrica no puede estar vacía"
                )

            lista_limpia: list[str] = []
            vistos: set[str] = set()
            for item in criterios_rubrica:
                if not isinstance(item, str) or not item.strip():
                    raise CriteriosRubricaInvalidosError(
                        detalle="Todos los criterios en la lista simple deben ser nombres no vacíos"
                    )
                nombre_criterio = item.strip()
                if nombre_criterio in vistos:
                    raise CriteriosRubricaInvalidosError(
                        detalle=f"El criterio '{nombre_criterio}' está duplicado en la lista de rúbrica"
                    )
                vistos.add(nombre_criterio)
                lista_limpia.append(nombre_criterio)

            return lista_limpia

        raise CriteriosRubricaInvalidosError(
            detalle="Formato inválido: debe ser una lista simple de criterios o un diccionario con ponderaciones"
        )

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
    def criterios_rubrica(self) -> dict[str, Any] | list[str]:
        if isinstance(self._criterios_rubrica, list):
            return list(self._criterios_rubrica)
        return dict(self._criterios_rubrica)

    @property
    def nombres_criterios(self) -> list[str]:
        """Retorna la lista de nombres de criterios tanto para lista simple como para diccionario."""
        if isinstance(self._criterios_rubrica, list):
            return list(self._criterios_rubrica)
        return list(self._criterios_rubrica.keys())

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

    def es_borrador(self) -> bool:
        """Determina si la regla de programa se encuentra en estado Borrador editable."""
        return self._estado_vigencia == EstadoVigenciaRegla.BORRADOR

    def actualizar_borrador(
        self,
        *,
        horas_requeridas: Optional[int] = None,
        criterios_rubrica: Optional[dict[str, Any] | list[str]] = None,
        plantilla_acta: Optional[str] = None,
        version: Optional[str] = None,
    ) -> None:
        """Edita los atributos normativos de la regla exclusivamente mientras permanezca en estado Borrador.

        Traza: CU-12, Escenario 2 (Edición exitosa en estado Borrador),
        Escenario 5 y 6 (Validación de invariantes), Escenario 8 (Bloqueo de edición en Activa o Inactiva).
        """
        if self._estado_vigencia != EstadoVigenciaRegla.BORRADOR:
            raise ReglaProgramaInmutableError(
                regla_id=self._id,
                version=self._version,
                estado_vigencia=self._estado_vigencia.value,
                operacion="editar",
            )

        nueva_version = (
            self._validar_texto_obligatorio(version, campo="version")
            if version is not None
            else self._version
        )
        nuevas_horas = (
            self._validar_horas_requeridas(horas_requeridas)
            if horas_requeridas is not None
            else self._horas_requeridas
        )
        nuevos_criterios = (
            self._validar_criterios_rubrica(criterios_rubrica, exigir_no_vacio=True)
            if criterios_rubrica is not None
            else self._criterios_rubrica
        )
        nueva_plantilla = (
            self._validar_texto_obligatorio(plantilla_acta, campo="plantillaActa")
            if plantilla_acta is not None
            else self._plantilla_acta
        )

        self._version = nueva_version
        self._horas_requeridas = nuevas_horas
        self._criterios_rubrica = nuevos_criterios
        self._plantilla_acta = nueva_plantilla

    def activar(self, fecha_vigencia: Optional[datetime] = None) -> None:
        """Activa oficialmente una regla en estado Borrador para nuevas prácticas del programa académico.

        Traza: CU-12, Escenario 4 (Activación oficial exitosa), Escenario 8 (Inmutabilidad de reglas), ADR-007.
        """
        if self._estado_vigencia == EstadoVigenciaRegla.INACTIVA:
            raise ReglaProgramaInmutableError(
                regla_id=self._id,
                version=self._version,
                estado_vigencia=self._estado_vigencia.value,
                operacion="activar",
            )
        self._estado_vigencia = EstadoVigenciaRegla.ACTIVA
        if fecha_vigencia is not None:
            self._fecha_vigencia = fecha_vigencia
        else:
            self._fecha_vigencia = datetime.now()

    def desactivar(self) -> None:
        """Transiciona la regla activa a estado Inactiva (histórica) para impedir su asignación a nuevas prácticas."""
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
