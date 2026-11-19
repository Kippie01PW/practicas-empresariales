"""Excepciones y errores de la capa de dominio.

Traza: CU-01, CU-02, Escenarios 2, 3, 4 y 5 de spec.md, ADR-002, ADR-007, ADR-010.

Define las excepciones del modelo de dominio del sistema de gestión de prácticas
empresariales. Estas excepciones encapsulan violaciones a invariantes y reglas
fundamentales de negocio (e.g. prácticas activas simultáneas, falta de reglas
normativas vigentes, transiciones no permitidas en el ciclo de vida, justificación
obligatoria de rechazo y entidades no encontradas).
"""

from __future__ import annotations

from typing import Optional


class ErrorDominio(Exception):
    """Clase base para todas las excepciones del dominio empresarial.

    Garantiza que la capa de aplicación pueda capturar y manejar de manera
    uniforme cualquier violación a las reglas de negocio e invariantes del dominio.
    """

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje: str = mensaje

    def __str__(self) -> str:
        return self.mensaje

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(mensaje={self.mensaje!r})"


class PracticaActivaExistenteError(ErrorDominio):
    """Excepción lanzada cuando un estudiante ya posee una práctica activa en curso.

    Traza: CU-01, Escenario 3 (Bloqueo de postulación por práctica activa en curso), ADR-010.

    Un estudiante solo puede tener una práctica en curso simultáneamente. Los estados
    considerados activos en curso son: Aprobada, Asignada, EnEjecucion y Evaluada.
    """

    def __init__(
        self,
        estudiante_id: str,
        practica_id: Optional[str] = None,
        estado_actual: Optional[str] = None,
        mensaje: Optional[str] = None,
    ) -> None:
        self.estudiante_id: str = estudiante_id
        self.practica_id: Optional[str] = practica_id
        self.estado_actual: Optional[str] = estado_actual

        if mensaje is None:
            detalle_estado = f" en estado '{estado_actual}'" if estado_actual else ""
            detalle_practica = f" (práctica ID: {practica_id})" if practica_id else ""
            mensaje = (
                f"El estudiante '{estudiante_id}' ya cuenta con una práctica activa en curso"
                f"{detalle_estado}{detalle_practica}. No se permite registrar una nueva postulación."
            )

        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"PracticaActivaExistenteError("
            f"estudiante_id={self.estudiante_id!r}, "
            f"practica_id={self.practica_id!r}, "
            f"estado_actual={self.estado_actual!r})"
        )


class ReglaProgramaNoConfiguradaError(ErrorDominio):
    """Excepción lanzada cuando no existe una regla activa para el programa académico.

    Traza: CU-01, Escenario 4 (Bloqueo de postulación por inexistencia de ReglaPrograma activa),
    ADR-007 (Configuración declarativa de reglas versionadas).

    Toda postulación requiere estar vinculada obligatoriamente a una regla de programa
    en estado 'Activa' vigente al momento del registro.
    """

    def __init__(
        self,
        programa_academico: str,
        mensaje: Optional[str] = None,
    ) -> None:
        self.programa_academico: str = programa_academico

        if mensaje is None:
            mensaje = (
                f"El programa académico '{programa_academico}' no tiene configurada una "
                f"ReglaPrograma activa vigente. Consulte con la Coordinación de prácticas."
            )

        super().__init__(mensaje)

    def __repr__(self) -> str:
        return f"ReglaProgramaNoConfiguradaError(programa_academico={self.programa_academico!r})"


class TransicionEstadoInvalidaError(ErrorDominio):
    """Excepción lanzada ante un intento de transición no permitida en la máquina de estados.

    Traza: CU-01, ADR-010 (Máquina de estados finitos en la entidad Práctica).

    El ciclo de vida de la entidad Practica es gobernado por transiciones formales estrictas.
    Cualquier transición fuera del grafo permitido genera este error de dominio.
    """

    def __init__(
        self,
        estado_origen: str,
        estado_destino: str,
        practica_id: Optional[str] = None,
        mensaje: Optional[str] = None,
    ) -> None:
        self.estado_origen: str = estado_origen
        self.estado_destino: str = estado_destino
        self.practica_id: Optional[str] = practica_id

        if mensaje is None:
            detalle_practica = f" para la práctica '{practica_id}'" if practica_id else ""
            mensaje = (
                f"Transición de estado inválida{detalle_practica}: "
                f"no se permite cambiar de '{estado_origen}' a '{estado_destino}'."
            )

        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"TransicionEstadoInvalidaError("
            f"estado_origen={self.estado_origen!r}, "
            f"estado_destino={self.estado_destino!r}, "
            f"practica_id={self.practica_id!r})"
        )


class MotivoRechazoRequeridoError(ErrorDominio):
    """Excepción lanzada cuando se intenta rechazar una postulación sin justificación.

    Traza: CU-02, Escenario 3 (Rechazo fallido por ausencia de justificación obligatoria).
    RN-02: Todo rechazo administrativo debe contener una justificación no vacía.
    """

    def __init__(
        self,
        practica_id: Optional[str] = None,
        mensaje: Optional[str] = None,
    ) -> None:
        self.practica_id: Optional[str] = practica_id

        if mensaje is None:
            detalle_practica = f" para la práctica '{practica_id}'" if practica_id else ""
            mensaje = (
                f"La justificación de rechazo es obligatoria{detalle_practica}. "
                f"No se permite rechazar una postulación sin indicar el motivo."
            )

        super().__init__(mensaje)

    def __repr__(self) -> str:
        return f"MotivoRechazoRequeridoError(practica_id={self.practica_id!r})"


class PracticaNoEncontradaError(ErrorDominio):
    """Excepción lanzada cuando el identificador de la práctica no existe en el sistema.

    Traza: CU-02, ADR-002.
    """

    def __init__(
        self,
        practica_id: str,
        mensaje: Optional[str] = None,
    ) -> None:
        self.practica_id: str = practica_id

        if mensaje is None:
            mensaje = f"No se encontró ninguna práctica registrada con el identificador '{practica_id}'."

        super().__init__(mensaje)

    def __repr__(self) -> str:
        return f"PracticaNoEncontradaError(practica_id={self.practica_id!r})"


class DecisionPreviaEnFirmeError(TransicionEstadoInvalidaError):
    """Excepción lanzada cuando se intenta reevaluar una postulación con decisión en firme.

    Traza: CU-02, Escenario 5 (Intento de evaluar postulación con decisión previa ya asentada).
    """

    def __init__(
        self,
        estado_actual: str,
        practica_id: Optional[str] = None,
        mensaje: Optional[str] = None,
    ) -> None:
        self.estado_actual: str = estado_actual
        if mensaje is None:
            detalle_practica = f" '{practica_id}'" if practica_id else ""
            mensaje = (
                f"La postulación{detalle_practica} ya cuenta con una decisión administrativa en firme "
                f"(estado '{estado_actual}'). No se permite reevaluar una postulación finalizada."
            )

        super().__init__(
            estado_origen=estado_actual,
            estado_destino="Evaluacion",
            practica_id=practica_id,
            mensaje=mensaje,
        )

    def __repr__(self) -> str:
        return (
            f"DecisionPreviaEnFirmeError("
            f"estado_actual={self.estado_actual!r}, "
            f"practica_id={self.practica_id!r})"
        )
