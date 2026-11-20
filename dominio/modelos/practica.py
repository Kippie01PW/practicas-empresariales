"""Entidad raíz Practica y enumeración EstadoPractica.

Traza: CU-01, CU-02, CU-03, CU-04, CU-05, CU-07, CU-09, CU-10, ADR-010 (Máquina de Estados Finitos), ADR-007 (Reglas versionadas).

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

from dominio.errores import (
    ActaFinalYaGeneradaError,
    ActaYaAprobadaPorActorError,
    DecisionPreviaEnFirmeError,
    EstadoPracticaInvalidoParaActaError,
    EstadoPracticaInvalidoParaAprobarActaError,
    EstadoPracticaInvalidoParaEvaluacionError,
    EstadoPracticaInvalidoParaRegistroHorasError,
    EstadoPracticaInvalidoParaValidarHorasError,
    EvaluacionDesempenoFaltanteParaActaError,
    FaltaAprobacionDocentePreviaError,
    HorasInsuficientesParaActaError,
    MotivoRechazoRequeridoError,
    PracticaYaEvaluadaError,
    PracticaYaTieneTutorAsignadoError,
    TransicionEstadoInvalidaError,
)


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
        "_motivo_rechazo",
        "_docente_asesor_id",
        "_supervisor_empresa_id",
    )

    def __init__(
        self,
        *,
        estudiante_id: str,
        regla_programa_id: str,
        estado_inicial: EstadoPractica,
        fecha_postulacion: datetime | None = None,
        id: str | None = None,
        motivo_rechazo: Optional[str] = None,
        docente_asesor_id: Optional[str] = None,
        supervisor_empresa_id: Optional[str] = None,
        horas_acumuladas_aprobadas: int = 0,
    ) -> None:
        self._id: str = id or str(uuid.uuid4())
        self._estudiante_id: str = estudiante_id
        self._regla_programa_id: str = regla_programa_id
        self._estado_actual: EstadoPractica = estado_inicial
        self._fecha_postulacion: datetime = fecha_postulacion or datetime.now()
        self._horas_acumuladas_aprobadas: int = horas_acumuladas_aprobadas
        self._fecha_inicio: Optional[datetime] = None
        self._fecha_fin: Optional[datetime] = None
        self._motivo_rechazo: Optional[str] = motivo_rechazo
        self._docente_asesor_id: Optional[str] = docente_asesor_id
        self._supervisor_empresa_id: Optional[str] = supervisor_empresa_id

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

    @property
    def motivo_rechazo(self) -> Optional[str]:
        return self._motivo_rechazo

    @property
    def docente_asesor_id(self) -> Optional[str]:
        return self._docente_asesor_id

    @property
    def supervisor_empresa_id(self) -> Optional[str]:
        """Identificador del supervisor de empresa asignado a la práctica (ADR-004, CU-05)."""
        return self._supervisor_empresa_id

    # -- Métodos de transición de estado (spec.md, plan.md) -----------------

    def solicitar(self) -> None:
        """Transición a ``Solicitada`` (CU-01, escenarios 1 y 6).

        Válida desde ``PendienteVerificacion``.
        """
        self._asegurar_sin_decision_en_firme()
        self._transicionar(EstadoPractica.SOLICITADA)

    def aprobar(self) -> None:
        """Transición a ``Aprobada`` (CU-02, escenario 1).

        Válida únicamente desde ``Solicitada``.
        """
        self._asegurar_sin_decision_en_firme()
        if self._estado_actual != EstadoPractica.SOLICITADA:
            raise TransicionEstadoInvalidaError(
                estado_origen=self._estado_actual.value,
                estado_destino=EstadoPractica.APROBADA.value,
                practica_id=self._id,
                mensaje=(
                    f"Transición inválida para la práctica '{self._id}': "
                    f"la postulación solo puede ser evaluada cuando se encuentra en estado 'Solicitada' "
                    f"(estado actual: '{self._estado_actual.value}')."
                ),
            )
        self._transicionar(EstadoPractica.APROBADA)

    def marcar_pendiente_verificacion(self) -> None:
        """Marca la práctica como ``PendienteVerificacion``.

        Nota: este estado es asignado normalmente al momento de creación
        (escenario 5); este método existe por completitud y para el caso de
        reconstrucción de estado.
        """
        # Solo permitido si ya está en PendienteVerificacion (idempotente).
        if self._estado_actual != EstadoPractica.PENDIENTE_VERIFICACION:
            raise TransicionEstadoInvalidaError(
                estado_origen=self._estado_actual.value,
                estado_destino=EstadoPractica.PENDIENTE_VERIFICACION.value,
                practica_id=self._id,
                mensaje=(
                    f"Transición inválida: no se puede marcar como "
                    f"PendienteVerificacion desde '{self._estado_actual.value}'."
                ),
            )

    def rechazar(self, motivo: Optional[str] = None) -> None:
        """Transición a ``Rechazada`` (CU-01 escenarios 2 y derivados; CU-02 escenario 2).

        Válida desde ``PendienteVerificacion`` o ``Solicitada``.
        Para evaluaciones administrativas desde ``Solicitada``, la justificación de rechazo
        es obligatoria (CU-02, RN-02, Escenarios 2 y 3).
        """
        self._asegurar_sin_decision_en_firme()

        if self._estado_actual == EstadoPractica.SOLICITADA:
            if not motivo or not motivo.strip():
                raise MotivoRechazoRequeridoError(practica_id=self._id)
            self._motivo_rechazo = motivo.strip()
        elif motivo and motivo.strip():
            self._motivo_rechazo = motivo.strip()

        self._transicionar(EstadoPractica.RECHAZADA)

    def asignar_tutor(self, docente_asesor_id: str) -> None:
        """Transición a ``Asignada`` vinculando al docente asesor (CU-03, escenarios 1, 4 y 5).

        Válida únicamente cuando la práctica se encuentra en estado ``Aprobada`` y aún
        no cuenta con un docente asesor asignado en firme.

        Args:
            docente_asesor_id: Identificador del DocenteAsesor a vincular.

        Raises:
            PracticaYaTieneTutorAsignadoError: Si la práctica ya cuenta con tutor asignado o está en Asignada.
            TransicionEstadoInvalidaError: Si la práctica se encuentra en un estado distinto a Aprobada.
            ValueError: Si el identificador del docente asesor es vacío.
        """
        if self._docente_asesor_id is not None or self._estado_actual == EstadoPractica.ASIGNADA:
            raise PracticaYaTieneTutorAsignadoError(
                practica_id=self._id,
                docente_asesor_id=self._docente_asesor_id,
            )

        if self._estado_actual != EstadoPractica.APROBADA:
            raise TransicionEstadoInvalidaError(
                estado_origen=self._estado_actual.value,
                estado_destino=EstadoPractica.ASIGNADA.value,
                practica_id=self._id,
                mensaje=(
                    f"Solo se puede asignar un docente asesor a prácticas que se encuentren "
                    f"en estado 'Aprobada' (estado actual: '{self._estado_actual.value}')."
                ),
            )

        if not docente_asesor_id or not docente_asesor_id.strip():
            raise ValueError("El identificador del docente asesor no puede estar vacío.")

        self._docente_asesor_id = docente_asesor_id.strip()
        self._transicionar(EstadoPractica.ASIGNADA)

    def iniciar_ejecucion(self, fecha_inicio: Optional[datetime] = None) -> None:
        """Transición a ``EnEjecucion`` (CU-04, escenario 2).

        Válida únicamente cuando la práctica se encuentra en estado ``Asignada``
        con docente asesor previamente asignado.

        Args:
            fecha_inicio: Fecha y hora de inicio de ejecución (default: ahora).

        Raises:
            TransicionEstadoInvalidaError: Si la práctica no se encuentra en estado Asignada.
        """
        if self._estado_actual != EstadoPractica.ASIGNADA:
            raise TransicionEstadoInvalidaError(
                estado_origen=self._estado_actual.value,
                estado_destino=EstadoPractica.EN_EJECUCION.value,
                practica_id=self._id,
                mensaje=(
                    f"Solo se puede iniciar la ejecución de prácticas que se encuentren "
                    f"en estado 'Asignada' (estado actual: '{self._estado_actual.value}')."
                ),
            )
        self._fecha_inicio = fecha_inicio or datetime.now()
        self._transicionar(EstadoPractica.EN_EJECUCION)

    def registrar_evaluacion_desempeno(self, fecha_fin: Optional[datetime] = None) -> None:
        """Transición de ``EnEjecucion`` a ``Evaluada`` al asentar la evaluación de desempeño.

        Traza: CU-07, Escenarios 2, 3, 4, 11 y 12, plan.md. ADR-010 (Máquina de estados finitos), RN-02.

        Válida únicamente cuando la práctica se encuentra en estado ``EnEjecucion``.
        Si ya se encuentra en estado ``Evaluada``, lanza ``PracticaYaEvaluadaError``.
        Si se encuentra en cualquier otro estado distinto a ``EnEjecucion``, lanza
        ``EstadoPracticaInvalidoParaEvaluacionError``.

        Args:
            fecha_fin: Fecha y hora de evaluación / cierre de ejecución (default: ahora).

        Raises:
            PracticaYaEvaluadaError: Si la práctica ya se encuentra en estado Evaluada.
            EstadoPracticaInvalidoParaEvaluacionError: Si la práctica no está en EnEjecucion.
        """
        if self._estado_actual == EstadoPractica.EVALUADA:
            raise PracticaYaEvaluadaError(practica_id=self._id)

        if self._estado_actual != EstadoPractica.EN_EJECUCION:
            raise EstadoPracticaInvalidoParaEvaluacionError(
                practica_id=self._id,
                estado_actual=self._estado_actual.value,
            )

        self._transicionar(EstadoPractica.EVALUADA)
        self._fecha_fin = fecha_fin or datetime.now()

    def completar(
        self,
        acta_en_firme: bool = True,
        fecha_fin: Optional[datetime] = None,
    ) -> None:
        """Transición formal de ``Evaluada`` a ``Completada`` al quedar el ActaFinal en firme.

        Traza: CU-10, Escenarios 2, 3, 5 y 6, plan.md. ADR-010 (Máquina de estados finitos), RN-02.

        Válida únicamente cuando la práctica se encuentra en estado ``Evaluada`` y el
        ``ActaFinal`` cuenta con ambas aprobaciones electrónicas asentadas (``acta_en_firme=True``).

        Args:
            acta_en_firme: Indica si el ActaFinal cuenta con ambas firmas electrónicas
                (DocenteAsesor y Coordinador de prácticas) asentadas en firme.
            fecha_fin: Fecha y hora opcional de culminación oficial de la práctica.

        Raises:
            ActaYaAprobadaPorActorError: Si la práctica ya se encuentra en estado Completada.
            EstadoPracticaInvalidoParaAprobarActaError: Si la práctica no se encuentra en estado Evaluada.
            FaltaAprobacionDocentePreviaError: Si acta_en_firme es False.
        """
        if self._estado_actual == EstadoPractica.COMPLETADA:
            raise ActaYaAprobadaPorActorError(
                practica_id=self._id,
                estado_actual=self._estado_actual.value,
            )

        if self._estado_actual != EstadoPractica.EVALUADA:
            raise EstadoPracticaInvalidoParaAprobarActaError(
                practica_id=self._id,
                estado_actual=self._estado_actual.value,
            )

        if not acta_en_firme:
            raise FaltaAprobacionDocentePreviaError(
                practica_id=self._id,
                docente_asesor_id=self._docente_asesor_id,
            )

        self._transicionar(EstadoPractica.COMPLETADA)
        if fecha_fin is not None:
            self._fecha_fin = fecha_fin
        elif self._fecha_fin is None:
            self._fecha_fin = datetime.now()

    # -- Consultas de dominio -----------------------------------------------

    def puede_generar_acta(
        self,
        horas_requeridas: int,
        tiene_evaluacion: bool = True,
        tiene_acta_previa: bool = False,
    ) -> bool:
        """Indica si la práctica cumple todos los requisitos para generar el acta final.

        Traza: CU-09, Escenarios 1, 2, 3, 4, 5, 6 y 11, plan.md. ADR-007, ADR-008, ADR-010, RN-02.

        Args:
            horas_requeridas: Horas mínimas exigidas por la ReglaPrograma vinculada.
            tiene_evaluacion: Indica si existe una EvaluacionDesempeno registrada.
            tiene_acta_previa: Indica si la práctica ya tiene un ActaFinal emitida.

        Returns:
            True si la práctica está en Evaluada, no tiene acta previa, cuenta con evaluación
            y acumula al menos las horas requeridas; False en caso contrario.
        """
        if tiene_acta_previa:
            return False
        if self._estado_actual != EstadoPractica.EVALUADA:
            return False
        if not tiene_evaluacion:
            return False
        if self._horas_acumuladas_aprobadas < horas_requeridas:
            return False
        return True

    def validar_requisitos_generacion_acta(
        self,
        *,
        horas_requeridas: int,
        tiene_evaluacion: bool,
        tiene_acta_previa: bool = False,
    ) -> None:
        """Valida los requisitos de la máquina de estados e invariantes para generar el ActaFinal.

        Traza: CU-09, Escenarios 1, 2, 3, 4, 5, 6 y 11, plan.md. ADR-007, ADR-008, ADR-010, RN-02.

        Args:
            horas_requeridas: Horas mínimas exigidas por la ReglaPrograma vinculada a la práctica.
            tiene_evaluacion: Indica si la práctica cuenta con una EvaluacionDesempeno registrada.
            tiene_acta_previa: Indica si la práctica ya cuenta con un ActaFinal previamente generada.

        Raises:
            ActaFinalYaGeneradaError: Si la práctica ya cuenta con un ActaFinal emitida (Escenario 5).
            EstadoPracticaInvalidoParaActaError: Si la práctica no está en estado Evaluada (Escenario 2).
            EvaluacionDesempenoFaltanteParaActaError: Si falta la Evaluación de Desempeño (Escenario 4).
            HorasInsuficientesParaActaError: Si las horas acumuladas aprobadas son menores a las
                horas requeridas por la ReglaPrograma vinculada (Escenario 3).
        """
        if tiene_acta_previa:
            raise ActaFinalYaGeneradaError(practica_id=self._id)

        if self._estado_actual != EstadoPractica.EVALUADA:
            raise EstadoPracticaInvalidoParaActaError(
                estado_actual=self._estado_actual.value,
                practica_id=self._id,
            )

        if not tiene_evaluacion:
            raise EvaluacionDesempenoFaltanteParaActaError(practica_id=self._id)

        if self._horas_acumuladas_aprobadas < horas_requeridas:
            raise HorasInsuficientesParaActaError(
                horas_acumuladas_aprobadas=self._horas_acumuladas_aprobadas,
                horas_requeridas=horas_requeridas,
                practica_id=self._id,
            )

    def puede_aprobar_acta(self) -> bool:
        """Indica si la práctica se encuentra en el estado formal para aprobar electrónicamente el acta.

        Traza: CU-10, Escenarios 1, 2 y 5, plan.md. ADR-010 (Máquina de estados finitos), RN-02.

        Solo las prácticas que se encuentren formalmente en estado ``Evaluada``
        admiten la aprobación electrónica del ``ActaFinal``.

        Returns:
            True si la práctica está en estado Evaluada; False en cualquier otro caso.
        """
        return self._estado_actual == EstadoPractica.EVALUADA

    def puede_evaluar_desempeno(self) -> bool:
        """Indica si la práctica se encuentra habilitada para registrar la evaluación de desempeño.

        Traza: CU-07, Escenarios 2, 3, 4, 11 y 12, plan.md. ADR-010 (Máquina de estados finitos).

        Solo las prácticas que se encuentren formalmente en estado ``EnEjecucion``
        pueden recibir la evaluación de desempeño del supervisor de empresa.

        Returns:
            True si la práctica está en estado EnEjecucion; False en cualquier otro caso.
        """
        return self._estado_actual == EstadoPractica.EN_EJECUCION

    def puede_registrar_horas(self) -> bool:
        """Indica si la práctica se encuentra habilitada para registrar horas semanales.

        Los estados habilitados son ``Asignada`` (que transiciona a ``EnEjecucion``
        con el primer reporte) y ``EnEjecucion`` (CU-04, escenarios 1, 2 y 3).
        """
        return self._estado_actual in {EstadoPractica.ASIGNADA, EstadoPractica.EN_EJECUCION}

    def puede_validar_horas(self) -> bool:
        """Indica si la práctica se encuentra habilitada para validar reportes de horas.

        Traza: CU-05, Escenario 5, plan.md. ADR-010 (Máquina de estados finitos).

        Solo las prácticas en estado formal ``EnEjecucion`` admiten validación de horas
        por parte del supervisor de empresa.

        Returns:
            True si la práctica está en estado EnEjecucion; False en cualquier otro caso.
        """
        return self._estado_actual == EstadoPractica.EN_EJECUCION

    def acumular_horas_aprobadas(self, cantidad_horas: int) -> None:
        """Suma al acumulado de horas aprobadas la cantidad indicada.

        Traza: CU-05, Escenario 1 (Aprobación exitosa de un reporte semanal de horas),
        plan.md. ADR-010 (Máquina de estados finitos).

        Precondición: la práctica debe estar en estado ``EnEjecucion``. Si se encuentra
        en cualquier otro estado, lanza EstadoPracticaInvalidoParaValidarHorasError
        (Escenario 5). La cantidad de horas debe ser mayor a 0.

        Args:
            cantidad_horas: Número de horas aprobadas a acumular (entero positivo).

        Raises:
            EstadoPracticaInvalidoParaValidarHorasError: Si la práctica no está en EnEjecucion.
            ValueError: Si cantidad_horas es menor o igual a 0.
        """
        if self._estado_actual != EstadoPractica.EN_EJECUCION:
            raise EstadoPracticaInvalidoParaValidarHorasError(
                practica_id=self._id,
                estado_actual=self._estado_actual.value,
            )
        if cantidad_horas <= 0:
            raise ValueError(
                f"La cantidad de horas a acumular debe ser un valor positivo mayor a 0 "
                f"(recibido: {cantidad_horas})."
            )
        self._horas_acumuladas_aprobadas += cantidad_horas

    def es_activa(self) -> bool:
        """Indica si la práctica se encuentra en un estado activo en curso.

        Los estados activos son: Aprobada, Asignada, EnEjecucion, Evaluada
        (spec.md, escenario 3).
        """
        return self._estado_actual in ESTADOS_PRACTICA_ACTIVA

    # -- Mecanismo interno de máquina de estados ----------------------------

    def _asegurar_sin_decision_en_firme(self) -> None:
        """Valida que la postulación no cuente ya con una decisión administrativa en firme.

        Traza: CU-02, Escenario 5 (ADR-010).
        """
        if self._estado_actual in {
            EstadoPractica.APROBADA,
            EstadoPractica.RECHAZADA,
            EstadoPractica.ASIGNADA,
            EstadoPractica.EN_EJECUCION,
            EstadoPractica.EVALUADA,
            EstadoPractica.COMPLETADA,
        }:
            raise DecisionPreviaEnFirmeError(
                estado_actual=self._estado_actual.value,
                practica_id=self._id,
            )

    def _transicionar(self, nuevo_estado: EstadoPractica) -> None:
        """Ejecuta una transición validada entre estados.

        Lanza ``TransicionEstadoInvalidaError`` si la transición no está declarada en el grafo
        de transiciones válidas (ADR-010).
        """
        estados_destino = _TRANSICIONES_VALIDAS.get(
            self._estado_actual, frozenset()
        )
        if nuevo_estado not in estados_destino:
            raise TransicionEstadoInvalidaError(
                estado_origen=self._estado_actual.value,
                estado_destino=nuevo_estado.value,
                practica_id=self._id,
            )
        self._estado_actual = nuevo_estado

    # -- Representación -----------------------------------------------------

    def __repr__(self) -> str:
        tutor_repr = f", tutor={self._docente_asesor_id!r}" if self._docente_asesor_id else ""
        return (
            f"Practica(id={self._id!r}, "
            f"estudiante_id={self._estudiante_id!r}, "
            f"estado={self._estado_actual.value!r}"
            f"{tutor_repr})"
        )
