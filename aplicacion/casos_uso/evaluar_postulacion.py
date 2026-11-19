"""Caso de uso: Evaluar postulación de práctica (Aprobar o rechazar).

Traza: CU-02, EAC-03, RN-02, RN-03, ADR-002, ADR-005, ADR-006, ADR-010.

Implementa la orquestación de la evaluación administrativa de postulaciones de práctica:
1. Autorización RBAC centralizada con política deny-by-default (ADR-005, EAC-03):
   Solo usuarios con rol 'Coordinador' o 'Coordinador de prácticas' están autorizados.
   Accesos denegados son registrados inmediatamente en la bitácora de auditoría
   con 0 datos expuestos de la práctica y del estudiante.
2. Búsqueda y existencia de la práctica en el repositorio.
3. Validación de precondiciones de la máquina de estados (ADR-010):
   Solo postulaciones en estado 'Solicitada' son evaluables.
   Rechazo de intentos de reevaluar decisiones en firme (Aprobada/Rechazada).
4. Validación de obligatoriedad de justificación en caso de rechazo (RN-02).
5. Transición en la entidad del dominio (Practica.aprobar() / Practica.rechazar(motivo)).
6. Persistencia transaccional de la práctica actualizada (ADR-003).
7. Registro inmutable append-only del evento en la bitácora de auditoría (ADR-006).
8. Emisión de notificación por correo electrónico al estudiante titular.
"""

from __future__ import annotations

from typing import Any, Optional

from aplicacion.dtos.evaluacion_postulacion_dto import (
    DecisionEvaluacion,
    EvaluacionPostulacionRespuestaDTO,
    EvaluarPostulacionComando,
)
from aplicacion.puertos.repositorio_practica import RepositorioPracticaPort
from aplicacion.puertos.servicio_correo import (
    ErrorServicioCorreo,
    ServicioCorreoPort,
)
from aplicacion.seguridad.autorizador_rbac import AccesoDenegadoError, AutorizadorRBAC
from dominio.errores import (
    DecisionPreviaEnFirmeError,
    MotivoRechazoRequeridoError,
    PracticaNoEncontradaError,
    TransicionEstadoInvalidaError,
)
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.practica import EstadoPractica, Practica


class EvaluarPostulacionCasoUso:
    """Caso de uso para evaluar administrativamente una postulación de práctica.

    Permite al Coordinador de prácticas aprobar o rechazar con justificación
    una postulación que se encuentra en estado 'Solicitada'.
    """

    def __init__(
        self,
        *,
        repositorio_practica: RepositorioPracticaPort,
        servicio_correo: ServicioCorreoPort,
        autorizador_rbac: Optional[AutorizadorRBAC] = None,
        lanzar_excepciones_dominio: bool = True,
    ) -> None:
        """Inicializa el caso de uso con sus colaboradores requeridos.

        Args:
            repositorio_practica: Puerto de persistencia de prácticas y bitácora.
            servicio_correo: Puerto para envío de notificaciones al estudiante.
            autorizador_rbac: Componente centralizado de control de acceso RBAC.
            lanzar_excepciones_dominio: Si es True (por defecto), eleva excepciones
                de dominio ante transiciones inválidas, falta de motivo o entidad inexistente;
                si es False, retorna EvaluacionPostulacionRespuestaDTO.denegada.
        """
        self._repositorio_practica: RepositorioPracticaPort = repositorio_practica
        self._servicio_correo: ServicioCorreoPort = servicio_correo
        self._autorizador_rbac: AutorizadorRBAC = autorizador_rbac or AutorizadorRBAC()
        self._lanzar_excepciones_dominio: bool = lanzar_excepciones_dominio

    def __call__(
        self,
        comando: EvaluarPostulacionComando,
        *,
        lanzar_excepciones_dominio: Optional[bool] = None,
    ) -> EvaluacionPostulacionRespuestaDTO:
        """Permite invocar la instancia del caso de uso como función callable."""
        return self.ejecutar(
            comando,
            lanzar_excepciones_dominio=lanzar_excepciones_dominio,
        )

    def ejecutar(
        self,
        comando: EvaluarPostulacionComando,
        *,
        lanzar_excepciones_dominio: Optional[bool] = None,
    ) -> EvaluacionPostulacionRespuestaDTO:
        """Ejecuta la evaluación administrativa de la postulación.

        Args:
            comando: DTO inmutable con la decisión, justificación y contexto de seguridad.
            lanzar_excepciones_dominio: Sobrescribe la política de excepciones del init.

        Returns:
            EvaluacionPostulacionRespuestaDTO con el nuevo estado y confirmación.

        Raises:
            AccesoDenegadoError: Si el usuario no cuenta con rol de Coordinador (EAC-03).
            PracticaNoEncontradaError: Si la práctica especificada no existe.
            MotivoRechazoRequeridoError: Si se rechaza sin justificación obligatoria.
            DecisionPreviaEnFirmeError: Si la práctica ya cuenta con una decisión en firme.
            TransicionEstadoInvalidaError: Si la práctica no está en estado 'Solicitada'.
        """
        debe_lanzar = (
            lanzar_excepciones_dominio
            if lanzar_excepciones_dominio is not None
            else self._lanzar_excepciones_dominio
        )

        # -------------------------------------------------------------------
        # 1. Autorización RBAC centralizada deny-by-default (ADR-005, EAC-03)
        # -------------------------------------------------------------------
        try:
            self._autorizador_rbac.autorizar_comando_evaluacion(comando)
        except AccesoDenegadoError as error_rbac:
            # EAC-03: Registrar de inmediato el intento no autorizado en la bitácora
            # con IP, fecha y hora, asegurando 0 datos expuestos de la postulación
            self._registrar_bitacora(
                actor_id=comando.actor_id,
                rol=comando.rol_actor,
                ip=comando.ip_origen,
                accion="Intento no autorizado de evaluación de postulación",
                entidad="ModuloPostulaciones",
                detalles={
                    "operacion": "evaluar_postulacion",
                    "decision": comando.decision,
                    "diagnostico": str(error_rbac),
                },
            )
            if debe_lanzar:
                raise error_rbac
            return EvaluacionPostulacionRespuestaDTO.denegada(
                practica_id=comando.practica_id,
                estado_actual="Desconocido",
                mensaje=str(error_rbac),
            )

        # -------------------------------------------------------------------
        # 2. Recuperación de la práctica en el repositorio
        # -------------------------------------------------------------------
        practica: Optional[Practica] = self._repositorio_practica.buscar_por_id(
            comando.practica_id
        )
        if practica is None:
            if debe_lanzar:
                raise PracticaNoEncontradaError(practica_id=comando.practica_id)
            return EvaluacionPostulacionRespuestaDTO.denegada(
                practica_id=comando.practica_id,
                estado_actual="Inexistente",
                mensaje=f"No se encontró ninguna práctica con ID '{comando.practica_id}'.",
            )

        # -------------------------------------------------------------------
        # 3. Validación de estado y ejecución de transición en el Dominio (ADR-010)
        # -------------------------------------------------------------------
        try:
            if comando.es_aprobacion:
                # Escenario 1: Aprobación exitosa
                practica.aprobar()
                nuevo_estado = EstadoPractica.APROBADA.value
                accion_bitacora = "Aprobación de postulación de práctica"
                mensaje_resultado = "Postulación aprobada exitosamente."
            else:
                # Escenario 2 y 3: Rechazo justificado u omisión de justificación
                practica.rechazar(motivo=comando.motivo_rechazo)
                nuevo_estado = EstadoPractica.RECHAZADA.value
                accion_bitacora = "Rechazo de postulación de práctica"
                mensaje_resultado = f"Postulación rechazada: {comando.motivo_rechazo}"

        except (
            MotivoRechazoRequeridoError,
            DecisionPreviaEnFirmeError,
            TransicionEstadoInvalidaError,
        ) as error_dominio:
            if debe_lanzar:
                raise error_dominio
            return EvaluacionPostulacionRespuestaDTO.denegada(
                practica_id=practica.id,
                estado_actual=practica.estado_actual.value,
                mensaje=str(error_dominio),
            )

        # -------------------------------------------------------------------
        # 4. Persistencia transaccional de la práctica actualizada (ADR-003)
        # -------------------------------------------------------------------
        self._repositorio_practica.actualizar(practica)

        # -------------------------------------------------------------------
        # 5. Registro inmutable de auditoría en la Bitácora (ADR-006)
        # -------------------------------------------------------------------
        detalles_bitacora: dict[str, Any] = {
            "practica_id": practica.id,
            "estudiante_id": practica.estudiante_id,
            "coordinador_id": comando.actor_id,
            "nuevo_estado": nuevo_estado,
        }
        if comando.es_rechazo:
            detalles_bitacora["motivo_rechazo"] = comando.motivo_rechazo

        self._registrar_bitacora(
            actor_id=comando.actor_id,
            rol=comando.rol_actor,
            ip=comando.ip_origen,
            accion=accion_bitacora,
            entidad=f"Practica:{practica.id}",
            detalles=detalles_bitacora,
        )

        # -------------------------------------------------------------------
        # 6. Notificación por correo electrónico al estudiante titular
        # -------------------------------------------------------------------
        self._notificar_estudiante(
            practica=practica,
            es_aprobacion=comando.es_aprobacion,
            motivo_rechazo=comando.motivo_rechazo,
        )

        # -------------------------------------------------------------------
        # 7. Respuesta estructurada al Coordinador / UI
        # -------------------------------------------------------------------
        if comando.es_aprobacion:
            return EvaluacionPostulacionRespuestaDTO.aprobada(
                practica_id=practica.id,
                mensaje=mensaje_resultado,
                detalles=detalles_bitacora,
            )
        else:
            return EvaluacionPostulacionRespuestaDTO.rechazada(
                practica_id=practica.id,
                motivo_rechazo=comando.motivo_rechazo or "",
                mensaje=mensaje_resultado,
                detalles=detalles_bitacora,
            )

    # -----------------------------------------------------------------------
    # Métodos privados de apoyo
    # -----------------------------------------------------------------------

    def _notificar_estudiante(
        self,
        *,
        practica: Practica,
        es_aprobacion: bool,
        motivo_rechazo: Optional[str] = None,
    ) -> bool:
        """Despacha la notificación por correo institucional al estudiante titular."""
        destinatario = (
            practica.estudiante_id
            if "@" in practica.estudiante_id
            else f"{practica.estudiante_id}@universidad.edu.co"
        )

        if es_aprobacion:
            asunto = f"Postulación a práctica empresarial aprobada - Práctica {practica.id}"
            cuerpo = (
                f"Estimado/a estudiante:\n\n"
                f"Nos complace informarle que su postulación a la práctica empresarial "
                f"con identificador '{practica.id}' ha sido APROBADA por la Coordinación de prácticas.\n\n"
                f"El siguiente paso en el proceso será la asignación de su docente tutor / asesor.\n\n"
                f"Atentamente,\n"
                f"Coordinación de Prácticas Empresariales"
            )
        else:
            asunto = f"Postulación a práctica empresarial: Notificación de rechazo - Práctica {practica.id}"
            cuerpo = (
                f"Estimado/a estudiante:\n\n"
                f"Le informamos que su postulación a la práctica empresarial con identificador "
                f"'{practica.id}' ha sido RECHAZADA por la Coordinación de prácticas.\n\n"
                f"Justificación administrativa registrada:\n"
                f"\"{motivo_rechazo}\"\n\n"
                f"Para mayor información, por favor contacte a la Coordinación de su programa.\n\n"
                f"Atentamente,\n"
                f"Coordinación de Prácticas Empresariales"
            )

        try:
            self._servicio_correo.enviar_notificacion(
                destinatario=destinatario,
                asunto=asunto,
                cuerpo=cuerpo,
            )
            return True
        except ErrorServicioCorreo:
            return False

    def _registrar_bitacora(
        self,
        *,
        actor_id: str,
        rol: str,
        ip: str,
        accion: str,
        entidad: str,
        detalles: Optional[dict[str, Any]] = None,
    ) -> None:
        """Registra un evento inmutable en la bitácora de auditoría append-only."""
        try:
            evento = EventoBitacora(
                actor_identificador=actor_id,
                rol_actor=rol,
                ip_origen=ip,
                accion_realizada=accion,
                entidad_afectada=entidad,
                detalles=detalles,
            )
            self._repositorio_practica.guardar_evento_bitacora(evento)
        except Exception:
            pass
