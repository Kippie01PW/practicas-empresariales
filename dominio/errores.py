"""Excepciones y errores de la capa de dominio.

Traza: CU-01, CU-02, CU-03, CU-04, CU-05, CU-07, CU-08, ADR-002, ADR-004, ADR-005,
ADR-006, ADR-007, ADR-010.

Define las excepciones del modelo de dominio del sistema de gestión de prácticas
empresariales. Estas excepciones encapsulan violaciones a invariantes y reglas
fundamentales de negocio (e.g. prácticas activas simultáneas, falta de reglas
normativas vigentes, transiciones no permitidas en el ciclo de vida, justificación
obligatoria de rechazo, cupos de tutores excedidos, registros de horas inválidos,
credenciales tokenizadas efímeras, validación contextual de horas registradas y
evaluación de desempeño del practicante).
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


# ---------------------------------------------------------------------------
# CU-05: Excepciones para validación de horas registradas y credenciales
#        tokenizadas (ADR-004, ADR-005, ADR-006, ADR-010)
# ---------------------------------------------------------------------------


class TokenEvaluacionInvalidoError(ErrorDominio):
    """Excepción lanzada cuando un token presenta firma inválida, parámetros adulterados o formato erróneo.

    Traza: CU-05, Escenario 8 (Intento de acceso mediante enlace criptográfico alterado o firma HMAC
    inválida), EAC-03, ADR-004 (Autenticación híbrida con enlaces criptográficos efímeros).

    Se activa cuando el interceptor de identidad detecta que la firma HMAC del enlace no coincide
    con los parámetros provistos, garantizando 0 datos expuestos (EAC-03).
    """

    def __init__(
        self,
        mensaje: Optional[str] = None,
    ) -> None:
        if mensaje is None:
            mensaje = (
                "El token de acceso presentado no es válido: la firma criptográfica HMAC es incorrecta "
                "o los parámetros del enlace han sido adulterados. Acceso denegado."
            )
        super().__init__(mensaje)

    def __repr__(self) -> str:
        return "TokenEvaluacionInvalidoError()"


class TokenEvaluacionExpiradoError(ErrorDominio):
    """Excepción lanzada cuando el enlace o token supera los 15 días de emisión.

    Traza: CU-05, Escenario 7 (Intento de acceso mediante enlace criptográfico con más de 15 días
    de emisión), EAC-03, ADR-004.

    Se activa cuando la fecha de emisión del token supera el límite de 15 días calendario.
    El evento de acceso expirado debe registrarse en bitácora en menos de 1 minuto (EAC-03).
    """

    def __init__(
        self,
        token_id: Optional[str] = None,
        mensaje: Optional[str] = None,
    ) -> None:
        self.token_id: Optional[str] = token_id

        if mensaje is None:
            detalle = f" (token '{token_id}')" if token_id else ""
            mensaje = (
                f"El enlace criptográfico{detalle} ha expirado: su fecha de emisión supera "
                f"los 15 días calendario permitidos. Solicite un nuevo enlace."
            )
        super().__init__(mensaje)

    def __repr__(self) -> str:
        return f"TokenEvaluacionExpiradoError(token_id={self.token_id!r})"


class TokenEvaluacionYaUsadoError(ErrorDominio):
    """Excepción lanzada al intentar reutilizar un enlace de un solo uso consumido.

    Traza: CU-05, Escenario 9 (Intento de acceso mediante enlace criptográfico de un solo uso
    previamente utilizado), ADR-004.

    Los tokens de Magic Link son de un solo uso: una vez consumidos para asentar una validación
    en firme, no pueden ser reutilizados.
    """

    def __init__(
        self,
        token_id: Optional[str] = None,
        mensaje: Optional[str] = None,
    ) -> None:
        self.token_id: Optional[str] = token_id

        if mensaje is None:
            detalle = f" (token '{token_id}')" if token_id else ""
            mensaje = (
                f"El enlace criptográfico{detalle} ya ha sido utilizado previamente para asentar "
                f"una validación en firme. No es posible reutilizar un enlace de un solo uso."
            )
        super().__init__(mensaje)

    def __repr__(self) -> str:
        return f"TokenEvaluacionYaUsadoError(token_id={self.token_id!r})"


class ReporteHorasYaEvaluadoError(ErrorDominio):
    """Excepción lanzada cuando se intenta evaluar un reporte de horas que ya fue aprobado o rechazado.

    Traza: CU-05, Escenario 4 (Intento de validación sobre un reporte de horas que ya fue evaluado
    previamente), ADR-010.

    La entidad RegistroHoras controla las transiciones de su estado de validación;
    no se permite reevaluar un reporte que ya cuenta con una decisión en firme.
    """

    def __init__(
        self,
        registro_horas_id: Optional[str] = None,
        estado_actual: Optional[str] = None,
        semana: Optional[int] = None,
        mensaje: Optional[str] = None,
    ) -> None:
        self.registro_horas_id: Optional[str] = registro_horas_id
        self.estado_actual: Optional[str] = estado_actual
        self.semana: Optional[int] = semana

        if mensaje is None:
            detalle_semana = f" de la semana {semana}" if semana is not None else ""
            detalle_estado = f" (estado actual: '{estado_actual}')" if estado_actual else ""
            detalle_id = f" '{registro_horas_id}'" if registro_horas_id else ""
            mensaje = (
                f"El reporte de horas{detalle_id}{detalle_semana} ya cuenta con una validación "
                f"en firme{detalle_estado}. No se permite reevaluar un reporte previamente resuelto."
            )
        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"ReporteHorasYaEvaluadoError("
            f"registro_horas_id={self.registro_horas_id!r}, "
            f"estado_actual={self.estado_actual!r}, "
            f"semana={self.semana!r})"
        )


class MotivoRechazoHorasRequeridoError(ErrorDominio):
    """Excepción lanzada cuando se intenta rechazar un reporte de horas sin observaciones descriptivas.

    Traza: CU-05, Escenario 3 (Rechazo fallido por ausencia de justificación u observaciones
    obligatorias), RN-02.

    El rechazo de un reporte semanal de horas requiere obligatoriamente una observación
    descriptiva no vacía (RN-02).
    """

    def __init__(
        self,
        registro_horas_id: Optional[str] = None,
        mensaje: Optional[str] = None,
    ) -> None:
        self.registro_horas_id: Optional[str] = registro_horas_id

        if mensaje is None:
            detalle = f" para el reporte '{registro_horas_id}'" if registro_horas_id else ""
            mensaje = (
                f"La justificación u observación de rechazo es obligatoria{detalle}. "
                f"No se permite rechazar un reporte de horas sin indicar el motivo."
            )
        super().__init__(mensaje)

    def __repr__(self) -> str:
        return f"MotivoRechazoHorasRequeridoError(registro_horas_id={self.registro_horas_id!r})"


class EstadoPracticaInvalidoParaValidarHorasError(ErrorDominio):
    """Excepción lanzada cuando la práctica se encuentra en un estado que no admite validación de horas.

    Traza: CU-05, Escenario 5 (Intento de validación sobre una práctica en estado no permitido por
    la máquina de estados), ADR-010.

    Solo se pueden validar reportes de horas en prácticas formalizadas en estado 'EnEjecucion'.
    """

    def __init__(
        self,
        practica_id: Optional[str] = None,
        estado_actual: Optional[str] = None,
        mensaje: Optional[str] = None,
    ) -> None:
        self.practica_id: Optional[str] = practica_id
        self.estado_actual: Optional[str] = estado_actual

        if mensaje is None:
            detalle_id = f" '{practica_id}'" if practica_id else ""
            detalle_estado = f" (estado actual: '{estado_actual}')" if estado_actual else ""
            mensaje = (
                f"Solo se pueden validar reportes de horas en prácticas formalizadas en estado "
                f"'EnEjecucion'. La práctica{detalle_id} no se encuentra en dicho estado{detalle_estado}."
            )
        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"EstadoPracticaInvalidoParaValidarHorasError("
            f"practica_id={self.practica_id!r}, "
            f"estado_actual={self.estado_actual!r})"
        )


class RegistroHorasNoEncontradoError(ErrorDominio):
    """Excepción lanzada cuando el identificador del reporte de horas no existe en el sistema.

    Traza: CU-05, ADR-002.
    """

    def __init__(
        self,
        registro_horas_id: str,
        mensaje: Optional[str] = None,
    ) -> None:
        self.registro_horas_id: str = registro_horas_id

        if mensaje is None:
            mensaje = (
                f"No se encontró ningún reporte de horas registrado con el identificador "
                f"'{registro_horas_id}'."
            )
        super().__init__(mensaje)

    def __repr__(self) -> str:
        return f"RegistroHorasNoEncontradoError(registro_horas_id={self.registro_horas_id!r})"


class SupervisorNoAsignadoAPracticaError(ErrorDominio):
    """Excepción lanzada ante violación de pertenencia contextual del supervisor a la práctica.

    Traza: CU-05, Escenario 6 (Intento de validación sobre un reporte de horas de una práctica
    ajena al supervisor), RN-01, ADR-005 (Control de acceso RBAC centralizado).

    Un supervisor solo puede validar reportes de horas de la práctica que le fue asignada
    formalmente. El intento de acceder a prácticas ajenas es bloqueado sin exponer datos.
    """

    def __init__(
        self,
        supervisor_id: Optional[str] = None,
        practica_id: Optional[str] = None,
        mensaje: Optional[str] = None,
    ) -> None:
        self.supervisor_id: Optional[str] = supervisor_id
        self.practica_id: Optional[str] = practica_id

        if mensaje is None:
            detalle_sup = f" '{supervisor_id}'" if supervisor_id else ""
            detalle_prac = f" a la práctica '{practica_id}'" if practica_id else ""
            mensaje = (
                f"Violación de pertenencia contextual: El supervisor{detalle_sup} no está asignado "
                f"{detalle_prac}. Acceso denegado bajo la regla de pertenencia contextual (RN-01)."
            )
        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"SupervisorNoAsignadoAPracticaError("
            f"supervisor_id={self.supervisor_id!r}, "
            f"practica_id={self.practica_id!r})"
        )


# ---------------------------------------------------------------------------
# CU-07: Excepciones para evaluación de desempeño del practicante, escala
#        cuantitativa y rúbrica (ADR-007, ADR-010, EAC-01, RN-02)
# ---------------------------------------------------------------------------


class EstadoPracticaInvalidoParaEvaluacionError(ErrorDominio):
    """Excepción lanzada cuando se intenta evaluar una práctica en estado distinto a EnEjecucion.

    Traza: CU-07, Escenario 11 (Intento de evaluar desempeño sobre una práctica en estado
    distinto a EnEjecucion), RN-02, ADR-010 (Máquina de estados finitos).

    Solo se puede evaluar el desempeño de prácticas que se encuentren formalmente en
    estado 'EnEjecucion'.
    """

    def __init__(
        self,
        practica_id: Optional[str] = None,
        estado_actual: Optional[str] = None,
        mensaje: Optional[str] = None,
    ) -> None:
        self.practica_id: Optional[str] = practica_id
        self.estado_actual: Optional[str] = estado_actual

        if mensaje is None:
            detalle_id = f" '{practica_id}'" if practica_id else ""
            detalle_estado = f" (estado actual: '{estado_actual}')" if estado_actual else ""
            mensaje = (
                f"Solo se puede evaluar el desempeño de prácticas que se encuentren formalmente "
                f"en estado 'EnEjecucion'. La práctica{detalle_id} no se encuentra en dicho "
                f"estado{detalle_estado}."
            )
        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"EstadoPracticaInvalidoParaEvaluacionError("
            f"practica_id={self.practica_id!r}, "
            f"estado_actual={self.estado_actual!r})"
        )


class PracticaYaEvaluadaError(DecisionPreviaEnFirmeError):
    """Excepción lanzada cuando se intenta evaluar una práctica que ya cuenta con una evaluación registrada.

    Traza: CU-07, Escenario 11 y Escenario 12 (Intento de evaluar una práctica que ya cuenta con
    una EvaluacionDesempeno registrada), RN-02, ADR-010.

    Cada práctica puede recibir como máximo una única EvaluacionDesempeno en firme.
    """

    def __init__(
        self,
        practica_id: Optional[str] = None,
        evaluacion_id: Optional[str] = None,
        mensaje: Optional[str] = None,
    ) -> None:
        self.evaluacion_id: Optional[str] = evaluacion_id

        if mensaje is None:
            detalle_id = f" '{practica_id}'" if practica_id else ""
            detalle_eval = f" (evaluación ID: '{evaluacion_id}')" if evaluacion_id else ""
            mensaje = (
                f"La práctica{detalle_id} ya cuenta con una EvaluacionDesempeno registrada en firme"
                f"{detalle_eval}. Cada práctica solo puede recibir como máximo una única evaluación."
            )
        super().__init__(
            estado_actual="Evaluada",
            practica_id=practica_id,
            mensaje=mensaje,
        )

    def __repr__(self) -> str:
        return (
            f"PracticaYaEvaluadaError("
            f"practica_id={self.practica_id!r}, "
            f"evaluacion_id={self.evaluacion_id!r})"
        )


class CalificacionCuantitativaInvalidaError(ErrorDominio):
    """Excepción lanzada cuando la calificación cuantitativa está fuera de la escala de 0.0 a 5.0.

    Traza: CU-07, Escenario 6 (Rechazo de evaluación por calificación cuantitativa fuera de la
    escala permitida de 0.0 a 5.0), ADR-007.
    """

    def __init__(
        self,
        calificacion: float,
        escala_minima: float = 0.0,
        escala_maxima: float = 5.0,
        mensaje: Optional[str] = None,
    ) -> None:
        self.calificacion: float = calificacion
        self.escala_minima: float = escala_minima
        self.escala_maxima: float = escala_maxima

        if mensaje is None:
            mensaje = (
                f"La calificación cuantitativa debe encontrarse en la escala de "
                f"{escala_minima:.1f} a {escala_maxima:.1f} (recibido: {calificacion})."
            )
        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"CalificacionCuantitativaInvalidaError("
            f"calificacion={self.calificacion!r}, "
            f"escala_minima={self.escala_minima!r}, "
            f"escala_maxima={self.escala_maxima!r})"
        )


class ObservacionesReprobatoriaRequeridasError(ErrorDominio):
    """Excepción lanzada cuando una evaluación reprobatoria (< 3.0) carece de observaciones obligatorias.

    Traza: CU-07, Escenario 5 (Rechazo de evaluación reprobatoria por ausencia de observaciones
    obligatorias), RN-02.
    """

    def __init__(
        self,
        calificacion: Optional[float] = None,
        umbral_aprobacion: float = 3.0,
        mensaje: Optional[str] = None,
    ) -> None:
        self.calificacion: Optional[float] = calificacion
        self.umbral_aprobacion: float = umbral_aprobacion

        if mensaje is None:
            detalle_nota = f" (nota recibida: {calificacion})" if calificacion is not None else ""
            mensaje = (
                f"Las observaciones son obligatorias cuando la calificación cuantitativa es "
                f"reprobatoria (inferior a {umbral_aprobacion:.1f}){detalle_nota}."
            )
        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"ObservacionesReprobatoriaRequeridasError("
            f"calificacion={self.calificacion!r}, "
            f"umbral_aprobacion={self.umbral_aprobacion!r})"
        )


class RespuestasRubricaInvalidasError(ErrorDominio):
    """Excepción lanzada cuando las respuestas de la rúbrica son incompletas o inválidas respecto a la regla.

    Traza: CU-07, Escenario 7 (Rechazo de evaluación por respuestas incompletas o inválidas respecto
    a los criterios de la rúbrica del programa), EAC-01, ADR-007.
    """

    def __init__(
        self,
        criterios_faltantes: Optional[list[str]] = None,
        criterios_fuera_rango: Optional[dict[str, float]] = None,
        criterios_desconocidos: Optional[list[str]] = None,
        mensaje: Optional[str] = None,
    ) -> None:
        self.criterios_faltantes: list[str] = list(criterios_faltantes or [])
        self.criterios_fuera_rango: dict[str, float] = dict(criterios_fuera_rango or {})
        self.criterios_desconocidos: list[str] = list(criterios_desconocidos or [])

        if mensaje is None:
            detalles: list[str] = []
            if self.criterios_faltantes:
                detalles.append(
                    f"criterios faltantes: {', '.join(repr(c) for c in self.criterios_faltantes)}"
                )
            if self.criterios_fuera_rango:
                items = ", ".join(f"{k!r}={v}" for k, v in self.criterios_fuera_rango.items())
                detalles.append(
                    f"criterios fuera del rango permitido (0.0 a 5.0): {items}"
                )
            if self.criterios_desconocidos:
                detalles.append(
                    f"criterios no definidos en la rúbrica del programa: "
                    f"{', '.join(repr(c) for c in self.criterios_desconocidos)}"
                )
            if detalles:
                mensaje = (
                    f"Las respuestas de la rúbrica de evaluación son inválidas ({'; '.join(detalles)})."
                )
            else:
                mensaje = (
                    "Las respuestas de la rúbrica de evaluación son incompletas o presentan "
                    "valores fuera de la escala permitida de 0.0 a 5.0."
                )
        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"RespuestasRubricaInvalidasError("
            f"criterios_faltantes={self.criterios_faltantes!r}, "
            f"criterios_fuera_rango={self.criterios_fuera_rango!r}, "
            f"criterios_desconocidos={self.criterios_desconocidos!r})"
        )


# ---------------------------------------------------------------------------
# CU-08: Excepciones para envío de recordatorios de plazos y control de
#        ventana de enfriamiento (ADR-001, ADR-004, ADR-006)
# ---------------------------------------------------------------------------


class RecordatorioEnEnfriamientoError(ErrorDominio):
    """Excepción lanzada cuando se intenta despachar un recordatorio dentro del período de enfriamiento.

    Traza: CU-08, Escenario 7 (Prevención de envío duplicado de recordatorios dentro del período
    de enfriamiento de 1 hora), ADR-006 (Bitácora de auditoría transaccional Append-Only).

    Garantiza la idempotencia del despacho de recordatorios evitando correos duplicados cuando
    ya se ha emitido un recordatorio para la misma práctica y acción pendiente hace menos de
    la ventana de enfriamiento configurada (por defecto 60 minutos / 1 hora).
    """

    def __init__(
        self,
        practica_id: Optional[str] = None,
        tipo_recordatorio: Optional[str] = None,
        cooldown_minutos: int = 60,
        mensaje: Optional[str] = None,
    ) -> None:
        self.practica_id: Optional[str] = practica_id
        self.tipo_recordatorio: Optional[str] = tipo_recordatorio
        self.cooldown_minutos: int = cooldown_minutos

        if mensaje is None:
            detalle_practica = f" para la práctica '{practica_id}'" if practica_id else ""
            detalle_tipo = f" (acción: '{tipo_recordatorio}')" if tipo_recordatorio else ""
            mensaje = (
                f"Ya se despachó un recordatorio{detalle_practica}{detalle_tipo} dentro de la "
                f"ventana de enfriamiento de {cooldown_minutos} minutos. Se omite el envío duplicado."
            )
        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"RecordatorioEnEnfriamientoError("
            f"practica_id={self.practica_id!r}, "
            f"tipo_recordatorio={self.tipo_recordatorio!r}, "
            f"cooldown_minutos={self.cooldown_minutos!r})"
        )



