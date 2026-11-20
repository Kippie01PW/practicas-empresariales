"""Entidad de dominio EvaluacionDesempeno.

Traza: CU-07, EAC-01, EAC-03, RN-01, RN-02, RN-03, RN-04, ADR-002, ADR-007, ADR-010,
Vista Lógica §2 (01-logica.puml).

Modela la calificación cualitativa y cuantitativa asentada por el supervisor de
empresa externo según la rúbrica vigente de la ReglaPrograma vinculada a la práctica.
Encapsula las invariantes de escala cuantitativa (0.0 a 5.0), obligatoriedad de
observaciones en calificaciones reprobatorias (< 3.0) y validación completa de
respuestas frente a los criterios de la rúbrica del programa académico.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Any, Mapping, Optional, Sequence

from dominio.errores import (
    CalificacionCuantitativaInvalidaError,
    ObservacionesReprobatoriaRequeridasError,
    RespuestasRubricaInvalidasError,
)


class EvaluacionDesempeno:
    """Entidad de dominio que representa la evaluación de desempeño de un practicante.

    Atributos del diagrama UML (01-logica.puml) y del plan técnico (plan.md):
        - id: Identificador único de la evaluación de desempeño.
        - practica_id: Identificador de la práctica empresarial evaluada (relación 1 a 0..1).
        - supervisor_id: Identificador del supervisor de empresa que emite la calificación.
        - calificacion_cuantitativa: Nota numérica en la escala de 0.0 a 5.0.
        - observaciones: Concepto cualitativo (obligatorio si calificacion_cuantitativa < 3.0).
        - respuestas_rubrica: Calificaciones numéricas por cada criterio de la rúbrica del programa.
        - fecha_evaluacion: Marca temporal del registro de la evaluación.
    """

    CALIFICACION_MINIMA: float = 0.0
    CALIFICACION_MAXIMA: float = 5.0
    UMBRAL_APROBACION: float = 3.0

    __slots__ = (
        "_id",
        "_practica_id",
        "_supervisor_id",
        "_calificacion_cuantitativa",
        "_observaciones",
        "_respuestas_rubrica",
        "_fecha_evaluacion",
    )

    def __init__(
        self,
        *,
        practica_id: str,
        supervisor_id: str,
        calificacion_cuantitativa: float,
        respuestas_rubrica: Mapping[str, float],
        observaciones: Optional[str] = None,
        criterios_rubrica_esperados: Optional[Mapping[str, Any] | Sequence[str] | set[str]] = None,
        fecha_evaluacion: Optional[datetime] = None,
        id: Optional[str] = None,
    ) -> None:
        if not practica_id or not practica_id.strip():
            raise ValueError("El identificador de la práctica es obligatorio.")
        if not supervisor_id or not supervisor_id.strip():
            raise ValueError("El identificador del supervisor de empresa es obligatorio.")

        nota_validada = self._validar_calificacion_cuantitativa(calificacion_cuantitativa)
        observaciones_validadas = self._validar_observaciones(nota_validada, observaciones)
        respuestas_validadas = self.validar_respuestas_rubrica(
            respuestas_rubrica=respuestas_rubrica,
            criterios_esperados=criterios_rubrica_esperados,
        )

        self._id: str = id.strip() if id and id.strip() else str(uuid.uuid4())
        self._practica_id: str = practica_id.strip()
        self._supervisor_id: str = supervisor_id.strip()
        self._calificacion_cuantitativa: float = nota_validada
        self._observaciones: Optional[str] = observaciones_validadas
        self._respuestas_rubrica: dict[str, float] = respuestas_validadas
        self._fecha_evaluacion: datetime = fecha_evaluacion or datetime.now()

    # -- Métodos de validación de invariantes de dominio -------------------

    @classmethod
    def _es_numero_valido(cls, valor: Any) -> bool:
        """Verifica que el valor sea numérico (int o float, excluyendo bool, NaN e Inf)."""
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return False
        return not (math.isnan(float(valor)) or math.isinf(float(valor)))

    @classmethod
    def _validar_calificacion_cuantitativa(cls, calificacion: Any) -> float:
        """Valida que la calificación cuantitativa esté dentro de la escala [0.0, 5.0].

        Traza: CU-07, Escenario 6 (Rechazo de evaluación por calificación cuantitativa
        fuera de la escala permitida de 0.0 a 5.0).
        """
        if not cls._es_numero_valido(calificacion):
            raise CalificacionCuantitativaInvalidaError(
                calificacion=float("nan"),
                escala_minima=cls.CALIFICACION_MINIMA,
                escala_maxima=cls.CALIFICACION_MAXIMA,
            )

        valor = float(calificacion)
        if valor < cls.CALIFICACION_MINIMA or valor > cls.CALIFICACION_MAXIMA:
            raise CalificacionCuantitativaInvalidaError(
                calificacion=valor,
                escala_minima=cls.CALIFICACION_MINIMA,
                escala_maxima=cls.CALIFICACION_MAXIMA,
            )
        return valor

    @classmethod
    def _validar_observaciones(
        cls,
        calificacion_cuantitativa: float,
        observaciones: Optional[str],
    ) -> Optional[str]:
        """Valida que las observaciones estén presentes cuando la calificación es reprobatoria (< 3.0).

        Traza: CU-07, Escenario 3 (observaciones opcionales en aprobatoria),
        Escenario 4 (evaluación reprobatoria con observaciones obligatorias),
        Escenario 5 (rechazo de evaluación reprobatoria por ausencia de observaciones obligatorias).
        """
        texto_limpio: Optional[str] = None
        if observaciones is not None and isinstance(observaciones, str):
            stripped = observaciones.strip()
            if stripped:
                texto_limpio = stripped

        if calificacion_cuantitativa < cls.UMBRAL_APROBACION and not texto_limpio:
            raise ObservacionesReprobatoriaRequeridasError(
                calificacion=calificacion_cuantitativa,
                umbral_aprobacion=cls.UMBRAL_APROBACION,
            )

        return texto_limpio

    @classmethod
    def _extraer_claves_criterios(
        cls,
        criterios_esperados: Optional[Mapping[str, Any] | Sequence[str] | set[str]],
    ) -> Optional[list[str]]:
        """Normaliza los criteriosRubrica de una ReglaPrograma en una lista ordenada de claves."""
        if criterios_esperados is None:
            return None

        if isinstance(criterios_esperados, Mapping):
            claves = [str(k).strip() for k in criterios_esperados.keys() if str(k).strip()]
            return claves

        if isinstance(criterios_esperados, (Sequence, set)) and not isinstance(
            criterios_esperados, (str, bytes)
        ):
            claves_lista: list[str] = []
            for item in criterios_esperados:
                if isinstance(item, Mapping):
                    nombre = (
                        item.get("id")
                        or item.get("codigo")
                        or item.get("criterio")
                        or item.get("nombre")
                    )
                    if nombre and str(nombre).strip():
                        claves_lista.append(str(nombre).strip())
                elif str(item).strip():
                    claves_lista.append(str(item).strip())
            return claves_lista

        return None

    @classmethod
    def validar_respuestas_rubrica(
        cls,
        respuestas_rubrica: Any,
        criterios_esperados: Optional[Mapping[str, Any] | Sequence[str] | set[str]] = None,
    ) -> dict[str, float]:
        """Valida que respuestas_rubrica cubra todos los criterios con notas en [0.0, 5.0].

        Traza: CU-07, Escenario 7 (Rechazo de evaluación por respuestas incompletas o inválidas
        respecto a los criterios de la rúbrica del programa) y Escenario 16 (EAC-01 -
        Inmutabilidad de la rúbrica de evaluación frente a cambios normativos posteriores).
        """
        if not isinstance(respuestas_rubrica, Mapping) or len(respuestas_rubrica) == 0:
            claves_req = cls._extraer_claves_criterios(criterios_esperados) or []
            raise RespuestasRubricaInvalidasError(
                criterios_faltantes=claves_req,
            )

        respuestas_limpias: dict[str, float] = {}
        criterios_fuera_rango: dict[str, float] = {}

        for clave_raw, valor_raw in respuestas_rubrica.items():
            clave = str(clave_raw).strip()
            if not clave:
                continue

            if not cls._es_numero_valido(valor_raw):
                criterios_fuera_rango[clave] = float("nan")
                continue

            nota_criterio = float(valor_raw)
            if nota_criterio < cls.CALIFICACION_MINIMA or nota_criterio > cls.CALIFICACION_MAXIMA:
                criterios_fuera_rango[clave] = nota_criterio
            else:
                respuestas_limpias[clave] = nota_criterio

        claves_esperadas = cls._extraer_claves_criterios(criterios_esperados)
        criterios_faltantes: list[str] = []
        criterios_desconocidos: list[str] = []

        if claves_esperadas is not None and len(claves_esperadas) > 0:
            conjunto_esperado = set(claves_esperadas)
            conjunto_recibido = {
                str(k).strip() for k in respuestas_rubrica.keys() if str(k).strip()
            }

            criterios_faltantes = [c for c in claves_esperadas if c not in conjunto_recibido]
            criterios_desconocidos = [
                str(k).strip()
                for k in respuestas_rubrica.keys()
                if str(k).strip() and str(k).strip() not in conjunto_esperado
            ]

        if not respuestas_limpias and not criterios_fuera_rango and not criterios_faltantes:
            raise RespuestasRubricaInvalidasError()

        if criterios_faltantes or criterios_fuera_rango or criterios_desconocidos:
            raise RespuestasRubricaInvalidasError(
                criterios_faltantes=criterios_faltantes,
                criterios_fuera_rango=criterios_fuera_rango,
                criterios_desconocidos=criterios_desconocidos,
            )

        return respuestas_limpias

    # -- Propiedades de lectura --------------------------------------------

    @property
    def id(self) -> str:
        return self._id

    @property
    def practica_id(self) -> str:
        return self._practica_id

    @property
    def supervisor_id(self) -> str:
        return self._supervisor_id

    @property
    def calificacion_cuantitativa(self) -> float:
        return self._calificacion_cuantitativa

    @property
    def observaciones(self) -> Optional[str]:
        return self._observaciones

    @property
    def respuestas_rubrica(self) -> dict[str, float]:
        return dict(self._respuestas_rubrica)

    @property
    def fecha_evaluacion(self) -> datetime:
        return self._fecha_evaluacion

    @property
    def es_aprobatoria(self) -> bool:
        """Indica si la calificación cuantitativa alcanza el umbral aprobatorio (>= 3.0)."""
        return self._calificacion_cuantitativa >= self.UMBRAL_APROBACION

    # -- Representación e igualdad -----------------------------------------

    def __repr__(self) -> str:
        return (
            f"EvaluacionDesempeno(id={self._id!r}, "
            f"practica_id={self._practica_id!r}, "
            f"supervisor_id={self._supervisor_id!r}, "
            f"calificacion_cuantitativa={self._calificacion_cuantitativa!r}, "
            f"es_aprobatoria={self.es_aprobatoria!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EvaluacionDesempeno):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)
