"""Entidad raíz Practica y enumeración EstadoPractica.

Traza: CU-01, ADR-010 (Máquina de Estados Finitos), ADR-007 (Reglas versionadas).

La entidad ``Practica`` encapsula el ciclo de vida completo de una práctica
empresarial mediante una máquina de estados finitos interna.  Solo se exponen
las transiciones definidas en el ADR-010 y los escenarios de spec.md;
cualquier transición no declarada es rechazada.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enumeración de estados del ciclo de vida (ADR-010, Vista Lógica §3)
# ---------------------------------------------------------------------------

class EstadoPractica(Enum):
    """Estados formales del ciclo de vida de una práctica empresarial.

    Orden conceptual del flujo principal:
        PendienteVerificacion → Solicitada → Aprobada → Asignada
        → EnEjecucion → Evaluada → Completada

    Estados terminales / alternativos:
        Rechazada (desde PendienteVerificacion o Solicitada)
    """

    PENDIENTE_VERIFICACION = "PendienteVerificacion"
    SOLICITADA = "Solicitada"
    APROBADA = "Aprobada"
    ASIGNADA = "Asignada"
    EN_EJECUCION = "EnEjecucion"
    EVALUADA = "Evaluada"
    COMPLETADA = "Completada"
    RECHAZADA = "Rechazada"


# Estados que representan una práctica "activa en curso" (spec.md, escenario 3).
ESTADOS_PRACTICA_ACTIVA: frozenset[EstadoPractica] = frozenset({
    EstadoPractica.APROBADA,
    EstadoPractica.ASIGNADA,
    EstadoPractica.EN_EJECUCION,
    EstadoPractica.EVALUADA,
})

# ---------------------------------------------------------------------------
# Transiciones válidas de la máquina de estados (ADR-010)
# ---------------------------------------------------------------------------

_TRANSICIONES_VALIDAS: dict[EstadoPractica, frozenset[EstadoPractica]] = {
    EstadoPractica.PENDIENTE_VERIFICACION: frozenset({
        EstadoPractica.SOLICITADA,
        EstadoPractica.RECHAZADA,
    }),
    EstadoPractica.SOLICITADA: frozenset({
        EstadoPractica.APROBADA,
        EstadoPractica.RECHAZADA,
    }),
    EstadoPractica.APROBADA: frozenset({
        EstadoPractica.ASIGNADA,
    }),
    EstadoPractica.ASIGNADA: frozenset({
        EstadoPractica.EN_EJECUCION,
    }),
    EstadoPractica.EN_EJECUCION: frozenset({
        EstadoPractica.EVALUADA,
    }),
    EstadoPractica.EVALUADA: frozenset({
        EstadoPractica.COMPLETADA,
    }),
    # Completada y Rechazada son estados finales: sin transiciones de salida.
    EstadoPractica.COMPLETADA: frozenset(),
    EstadoPractica.RECHAZADA: frozenset(),
}


# ---------------------------------------------------------------------------
# Entidad de dominio: Practica
# ---------------------------------------------------------------------------

class Practica:
    """Entidad raíz del agregado Práctica empresarial.

    Atributos del diagrama UML (01-logica.puml):
        - fechaPostulacion
        - estadoActual
        - horasAcumuladasAprobadas
        - fechaInicio
        - fechaFin

    Atributos de trazabilidad (plan.md):
        - id: identificador único de la práctica.
        - estudiante_id: referencia al Estudiante titular.
        - regla_programa_id: referencia a la ReglaPrograma activa vigente
          al momento de la postulación (ADR-007).
    """

    __slots__ = (
        "_id",
        "_estudiante_id",
        "_regla_programa_id",
        "_estado_actual",
        "_fecha_postulacion",
        "_horas_acumuladas_aprobadas",
        "_fecha_inicio",
        "_fecha_fin",
    )

    def __init__(
        self,
        *,
        estudiante_id: str,
        regla_programa_id: str,
        estado_inicial: EstadoPractica,
        fecha_postulacion: datetime | None = None,
        id: str | None = None,
    ) -> None:
        self._id: str = id or str(uuid.uuid4())
        self._estudiante_id: str = estudiante_id
        self._regla_programa_id: str = regla_programa_id
        self._estado_actual: EstadoPractica = estado_inicial
        self._fecha_postulacion: datetime = fecha_postulacion or datetime.now()
        self._horas_acumuladas_aprobadas: int = 0
        self._fecha_inicio: Optional[datetime] = None
        self._fecha_fin: Optional[datetime] = None

    # -- Propiedades de solo lectura ----------------------------------------

    @property
    def id(self) -> str:
        return self._id

    @property
    def estudiante_id(self) -> str:
        return self._estudiante_id

    @property
    def regla_programa_id(self) -> str:
        return self._regla_programa_id

    @property
    def estado_actual(self) -> EstadoPractica:
        return self._estado_actual

    @property
    def fecha_postulacion(self) -> datetime:
        return self._fecha_postulacion

    @property
    def horas_acumuladas_aprobadas(self) -> int:
        return self._horas_acumuladas_aprobadas

    @property
    def fecha_inicio(self) -> Optional[datetime]:
        return self._fecha_inicio

    @property
    def fecha_fin(self) -> Optional[datetime]:
        return self._fecha_fin

    # -- Métodos de transición de estado (spec.md, plan.md) -----------------

    def solicitar(self) -> None:
        """Transición a ``Solicitada`` (escenarios 1 y 6).

        Válida desde ``PendienteVerificacion``.
        """
        self._transicionar(EstadoPractica.SOLICITADA)

    def marcar_pendiente_verificacion(self) -> None:
        """Marca la práctica como ``PendienteVerificacion``.

        Nota: este estado es asignado normalmente al momento de creación
        (escenario 5); este método existe por completitud y para el caso de
        reconstrucción de estado.
        """
        # Solo permitido si ya está en PendienteVerificacion (idempotente).
        if self._estado_actual != EstadoPractica.PENDIENTE_VERIFICACION:
            raise ValueError(
                f"Transición inválida: no se puede marcar como "
                f"PendienteVerificacion desde '{self._estado_actual.value}'."
            )

    def rechazar(self) -> None:
        """Transición a ``Rechazada`` (escenarios 2 y derivados).

        Válida desde ``PendienteVerificacion`` o ``Solicitada``.
        """
        self._transicionar(EstadoPractica.RECHAZADA)

    # -- Consultas de dominio -----------------------------------------------

    def es_activa(self) -> bool:
        """Indica si la práctica se encuentra en un estado activo en curso.

        Los estados activos son: Aprobada, Asignada, EnEjecucion, Evaluada
        (spec.md, escenario 3).
        """
        return self._estado_actual in ESTADOS_PRACTICA_ACTIVA

    # -- Mecanismo interno de máquina de estados ----------------------------

    def _transicionar(self, nuevo_estado: EstadoPractica) -> None:
        """Ejecuta una transición validada entre estados.

        Lanza ``ValueError`` si la transición no está declarada en el grafo
        de transiciones válidas (ADR-010).  Este error será formalizado como
        ``TransicionEstadoInvalidaError`` en T-04.
        """
        estados_destino = _TRANSICIONES_VALIDAS.get(
            self._estado_actual, frozenset()
        )
        if nuevo_estado not in estados_destino:
            raise ValueError(
                f"Transición inválida: '{self._estado_actual.value}' "
                f"→ '{nuevo_estado.value}' no está permitida."
            )
        self._estado_actual = nuevo_estado

    # -- Representación -----------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Practica(id={self._id!r}, "
            f"estudiante_id={self._estudiante_id!r}, "
            f"estado={self._estado_actual.value!r})"
        )
