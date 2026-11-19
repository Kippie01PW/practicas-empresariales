"""Excepciones y errores de la capa de dominio.

Traza: CU-01, CU-02, CU-03, CU-04, ADR-002, ADR-005, ADR-007, ADR-010.

Define las excepciones del modelo de dominio del sistema de gestión de prácticas
empresariales. Estas excepciones encapsulan violaciones a invariantes y reglas
fundamentales de negocio (e.g. prácticas activas simultáneas, falta de reglas
normativas vigentes, transiciones no permitidas en el ciclo de vida, justificación
obligatoria de rechazo, cupos de tutores excedidos, registros de horas inválidos
y entidades no encontradas).
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


class CupoDocenteExcedidoError(ErrorDominio):
    """Excepción lanzada cuando un docente asesor ha alcanzado el límite de su cupo de tutorías.

    Traza: CU-03, Escenario 2 (Intento de asignación a docente asesor que alcanzó su cupo máximo),
    RT-01 (Capacidad máxima de tutorías por docente asesor).
    """

    def __init__(
        self,
        docente_id: str,
        cupo_maximo: Optional[int] = None,
        practicas_activas: Optional[int] = None,
        mensaje: Optional[str] = None,
    ) -> None:
        self.docente_id: str = docente_id
        self.cupo_maximo: Optional[int] = cupo_maximo
        self.practicas_activas: Optional[int] = practicas_activas

        if mensaje is None:
            detalle_cupo = (
                f" ({practicas_activas}/{cupo_maximo} prácticas activas)"
                if cupo_maximo is not None and practicas_activas is not None
                else ""
            )
            mensaje = (
                f"El docente asesor '{docente_id}' ha alcanzado el límite máximo de su cupo disponible"
                f"{detalle_cupo}. No se le pueden asignar más prácticas empresariales."
            )

        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"CupoDocenteExcedidoError("
            f"docente_id={self.docente_id!r}, "
            f"cupo_maximo={self.cupo_maximo!r}, "
            f"practicas_activas={self.practicas_activas!r})"
        )


class DocenteAsesorNoEncontradoError(ErrorDominio):
    """Excepción lanzada cuando el docente asesor no existe o no se encuentra habilitado.

    Traza: CU-03, Escenario 3 (Intento de asignación a docente asesor inexistente o inactivo).
    """

    def __init__(
        self,
        docente_id: str,
        mensaje: Optional[str] = None,
    ) -> None:
        self.docente_id: str = docente_id

        if mensaje is None:
            mensaje = (
                f"El docente asesor especificado '{docente_id}' no existe o no se encuentra "
                f"habilitado para asignación en el sistema."
            )

        super().__init__(mensaje)

    def __repr__(self) -> str:
        return f"DocenteAsesorNoEncontradoError(docente_id={self.docente_id!r})"


class PracticaYaTieneTutorAsignadoError(DecisionPreviaEnFirmeError):
    """Excepción lanzada cuando se intenta asignar tutor a una práctica que ya cuenta con uno.

    Traza: CU-03, Escenario 5 (Intento de asignación sobre práctica que ya cuenta con docente asesor asignado).
    """

    def __init__(
        self,
        practica_id: str,
        docente_asesor_id: Optional[str] = None,
        mensaje: Optional[str] = None,
    ) -> None:
        self.docente_asesor_id: Optional[str] = docente_asesor_id

        if mensaje is None:
            detalle_tutor = f" (docente asesor actual: '{docente_asesor_id}')" if docente_asesor_id else ""
            mensaje = (
                f"La práctica '{practica_id}' ya cuenta con un docente asesor asignado en firme"
                f"{detalle_tutor}. No se permite realizar una nueva asignación."
            )

        super().__init__(
            estado_actual="Asignada",
            practica_id=practica_id,
            mensaje=mensaje,
        )

    def __repr__(self) -> str:
        return (
            f"PracticaYaTieneTutorAsignadoError("
            f"practica_id={self.practica_id!r}, "
            f"docente_asesor_id={self.docente_asesor_id!r})"
        )


class CantidadHorasInvalidaError(ErrorDominio):
    """Excepción lanzada cuando la cantidad de horas reportada es inválida.

    Traza: CU-04, Escenario 4 (Intento de registro con cantidad de horas no permitida o no positiva),
    Escenario 5 (Intento de registro con exceso sobre el límite máximo de horas semanales permitido).
    """

    def __init__(
        self,
        cantidad_horas: int,
        limite_maximo: int = 60,
        mensaje: Optional[str] = None,
    ) -> None:
        self.cantidad_horas: int = cantidad_horas
        self.limite_maximo: int = limite_maximo

        if mensaje is None:
            if cantidad_horas <= 0:
                mensaje = (
                    f"La cantidad de horas reportada debe ser un valor positivo mayor a 0 "
                    f"(recibido: {cantidad_horas})."
                )
            else:
                mensaje = (
                    f"La cantidad de horas semanales ({cantidad_horas}) no puede superar "
                    f"el límite reglamentario de {limite_maximo} horas."
                )

        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"CantidadHorasInvalidaError("
            f"cantidad_horas={self.cantidad_horas!r}, "
            f"limite_maximo={self.limite_maximo!r})"
        )


class DescripcionActividadesRequeridaError(ErrorDominio):
    """Excepción lanzada cuando la descripción de actividades está vacía o en blanco.

    Traza: CU-04, Escenario 6 (Intento de registro con descripción de actividades vacía o en blanco).
    """

    def __init__(
        self,
        mensaje: Optional[str] = None,
    ) -> None:
        if mensaje is None:
            mensaje = "La descripción de actividades realizadas es obligatoria y no puede estar vacía."

        super().__init__(mensaje)

    def __repr__(self) -> str:
        return "DescripcionActividadesRequeridaError()"


class SemanaInvalidaError(ErrorDominio):
    """Excepción lanzada cuando el número de semana es menor o igual a cero.

    Traza: CU-04, Escenario 7 (Intento de registro con número de semana inválido menor o igual a cero).
    """

    def __init__(
        self,
        semana: int,
        mensaje: Optional[str] = None,
    ) -> None:
        self.semana: int = semana

        if mensaje is None:
            mensaje = (
                f"El número de semana debe ser un entero positivo mayor o igual a 1 "
                f"(recibido: {semana})."
            )

        super().__init__(mensaje)

    def __repr__(self) -> str:
        return f"SemanaInvalidaError(semana={self.semana!r})"


class SemanaHorasYaRegistradaError(ErrorDominio):
    """Excepción lanzada cuando ya existe un reporte de horas para la misma semana en la práctica.

    Traza: CU-04, Escenario 8 (Intento de registro duplicado para una misma semana ya reportada).
    """

    def __init__(
        self,
        practica_id: str,
        semana: int,
        mensaje: Optional[str] = None,
    ) -> None:
        self.practica_id: str = practica_id
        self.semana: int = semana

        if mensaje is None:
            mensaje = (
                f"La semana {semana} ya cuenta con un reporte de horas registrado para la "
                f"práctica '{practica_id}'."
            )

        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"SemanaHorasYaRegistradaError("
            f"practica_id={self.practica_id!r}, "
            f"semana={self.semana!r})"
        )


class EstadoPracticaInvalidoParaRegistroHorasError(ErrorDominio):
    """Excepción lanzada cuando la práctica se encuentra en un estado que no permite registrar horas.

    Traza: CU-04, Escenario 3 (Intento de registro de horas en una práctica en estado no permitido).
    ADR-010 (Máquina de estados finitos).
    """

    def __init__(
        self,
        practica_id: str,
        estado_actual: str,
        mensaje: Optional[str] = None,
    ) -> None:
        self.practica_id: str = practica_id
        self.estado_actual: str = estado_actual

        if mensaje is None:
            mensaje = (
                f"Solo se pueden registrar horas cuando la práctica se encuentra formalizada en "
                f"estado 'Asignada' o 'EnEjecucion'. Estado actual de la práctica '{practica_id}': '{estado_actual}'."
            )

        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"EstadoPracticaInvalidoParaRegistroHorasError("
            f"practica_id={self.practica_id!r}, "
            f"estado_actual={self.estado_actual!r})"
        )

