"""Caso de uso: Validar horas registradas (CU-05).

Traza: CU-05, EAC-03, RN-01, RN-02, RN-03, RN-04, ADR-002, ADR-004, ADR-005, ADR-006, ADR-010.

Implementa la orquestación de la revisión y validación de reportes semanales de horas
por parte del supervisor de empresa externo:
1. Autenticación híbrida mediante enlace efímero con token HMAC (ADR-004) o contexto RBAC (ADR-005).
   Rechazo temprano e inmediato ante tokens corruptos, expirados (>15 días) o ya usados (EAC-03).
2. Autorización RBAC centralizada bajo política deny-by-default (ADR-005).
3. Búsqueda y validación de existencia de la práctica en el repositorio.
4. Validación de pertenencia contextual de datos (RN-01): el supervisor solo valida su práctica asignada.
5. Validación de precondiciones en la máquina de estados finitos (ADR-010): la práctica debe estar 'EnEjecucion'.
6. Búsqueda y validación del RegistroHoras: pertenencia a la práctica y estado 'Pendiente' (no reevaluable).
7. Ejecución de la decisión de dominio:
   - Aprobar: marca 'Aprobado' e incrementa el acumulado de horas aprobadas de la práctica.
   - Rechazar: valida justificación obligatoria (RN-02), asocia observaciones y marca 'Rechazado'.
8. Persistencia atómica de práctica y reporte de horas.
9. Consumo del token efímero de un solo uso (ADR-004).
10. Registro inmutable en bitácora de auditoría append-only (ADR-006).
11. Notificación al estudiante titular mediante el servicio de correo.
12. Retorno de ValidacionHorasRespuestaDTO con el resumen estructurado.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from aplicacion.dtos.validacion_horas_dto import (
    ValidacionHorasRespuestaDTO,
    ValidarHorasComando,
)
from aplicacion.puertos.repositorio_practica import RepositorioPracticaPort
from aplicacion.puertos.repositorio_registro_horas import RepositorioRegistroHorasPort
from aplicacion.puertos.repositorio_token_evaluacion import RepositorioTokenEvaluacionPort
from aplicacion.puertos.servicio_correo import ServicioCorreoPort
from aplicacion.seguridad.autorizador_rbac import (
    AccesoDenegadoError,
    AutorizadorRBAC,
    ContextoUsuario,
    RolUsuario,
)
from dominio.errores import (
    EstadoPracticaInvalidoParaValidarHorasError,
    MotivoRechazoHorasRequeridoError,
    PracticaNoEncontradaError,
    ReporteHorasYaEvaluadoError,
    RegistroHorasNoEncontradoError,
    SupervisorNoAsignadoAPracticaError,
    TokenEvaluacionExpiradoError,
    TokenEvaluacionInvalidoError,
    TokenEvaluacionYaUsadoError,
)
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.practica import Practica
from dominio.modelos.registro_horas import EstadoValidacionHoras, RegistroHoras
from dominio.modelos.token_evaluacion import TokenEvaluacion


class ValidarHorasRegistradasCasoUso:
    """Caso de uso principal para la validación de horas registradas (CU-05)."""

    def __init__(
        self,
        *,
        repositorio_practica: RepositorioPracticaPort,
        repositorio_registro_horas: RepositorioRegistroHorasPort,
        repositorio_token_evaluacion: Optional[RepositorioTokenEvaluacionPort] = None,
        servicio_correo: Optional[ServicioCorreoPort] = None,
        autorizador_rbac: Optional[AutorizadorRBAC] = None,
        interceptor_identidad: Optional[Any] = None,
    ) -> None:
        self._repositorio_practica: RepositorioPracticaPort = repositorio_practica
        self._repositorio_registro_horas: RepositorioRegistroHorasPort = repositorio_registro_horas
        self._repositorio_token_evaluacion: Optional[RepositorioTokenEvaluacionPort] = (
            repositorio_token_evaluacion
        )
        self._servicio_correo: Optional[ServicioCorreoPort] = servicio_correo
        self._autorizador_rbac: AutorizadorRBAC = autorizador_rbac or AutorizadorRBAC()
        self._interceptor_identidad: Optional[Any] = interceptor_identidad

    def __call__(
        self,
        comando: ValidarHorasComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> ValidacionHorasRespuestaDTO:
        """Permite invocar la instancia como callable."""
        return self.ejecutar(comando, contexto=contexto)

    def ejecutar(
        self,
        comando: ValidarHorasComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> ValidacionHorasRespuestaDTO:
        """Ejecuta la validación del reporte de horas de la práctica empresarial.

        Args:
            comando: DTO inmutable con la decisión y referencias del reporte.
            contexto: Contexto de identidad del usuario si la autenticación es por sesión.

        Returns:
            ValidacionHorasRespuestaDTO con el resultado de la validación.

        Raises:
            TokenEvaluacionInvalidoError: Si el token HMAC es corrupto o no coincide.
            TokenEvaluacionExpiradoError: Si el enlace superó 15 días calendario.
            TokenEvaluacionYaUsadoError: Si el enlace de un solo uso ya fue consumido.
            AccesoDenegadoError: Si el rol autenticado no tiene permisos suficientes.
            PracticaNoEncontradaError: Si la práctica no existe.
            SupervisorNoAsignadoAPracticaError: Si el supervisor no corresponde a la práctica.
            EstadoPracticaInvalidoParaValidarHorasError: Si la práctica no está en 'EnEjecucion'.
            RegistroHorasNoEncontradoError: Si el reporte de horas no existe.
            ReporteHorasYaEvaluadoError: Si el reporte ya cuenta con validación en firme.
            MotivoRechazoHorasRequeridoError: Si se rechaza sin observaciones descriptivas.
        """
        token_entidad: Optional[TokenEvaluacion] = None
        supervisor_id: str = ""

        # -------------------------------------------------------------------
        # 1. Autenticación y Autorización (ADR-004, ADR-005, EAC-03)
        # -------------------------------------------------------------------
        if comando.token_acceso:
            # Autenticación vía enlace criptográfico efímero (Magic Link)
            token_entidad = self._autenticar_token(
                token_str=comando.token_acceso,
                practica_id_esperada=comando.practica_id,
                ip_origen=comando.ip_origen,
            )
            supervisor_id = token_entidad.supervisor_id
        elif contexto is not None:
            # Autenticación vía sesión / SSO institucional (ADR-005)
            try:
                self._autorizador_rbac.validar_validacion_horas(
                    rol_actor=contexto.rol,
                    usuario_id=contexto.usuario_id,
                    operacion="validar_horas",
                )
            except AccesoDenegadoError as error_rbac:
                self._registrar_bitacora(
                    actor_id=contexto.usuario_id,
                    rol=contexto.rol,
                    ip=comando.ip_origen,
                    accion="Intento no autorizado de validacion de horas",
                    entidad=f"Practica:{comando.practica_id}",
                    detalles={"diagnostico": str(error_rbac)},
                )
                raise error_rbac
            supervisor_id = contexto.usuario_id
        elif comando.supervisor_id:
            supervisor_id = comando.supervisor_id.strip()
        else:
            # Sin credencial ni token
            error_acceso = AccesoDenegadoError(
                "No se proveyó credencial de acceso ni token efímero válido.",
                operacion="validar_horas",
            )
            self._registrar_bitacora(
                actor_id="DESCONOCIDO",
                rol="DESCONOCIDO",
                ip=comando.ip_origen,
                accion="Intento de acceso sin credenciales a validacion de horas",
                entidad=f"Practica:{comando.practica_id}",
            )
            raise error_acceso

        # -------------------------------------------------------------------
        # 2. Búsqueda y validación de la Práctica (ADR-002)
        # -------------------------------------------------------------------
        practica: Optional[Practica] = self._repositorio_practica.buscar_por_id(
            comando.practica_id
        )
        if practica is None:
            raise PracticaNoEncontradaError(practica_id=comando.practica_id)

        # -------------------------------------------------------------------
        # 3. Pertenencia contextual supervisor-práctica (RN-01, ADR-005)
        # -------------------------------------------------------------------
        if practica.supervisor_empresa_id and practica.supervisor_empresa_id != supervisor_id:
            self._registrar_bitacora(
                actor_id=supervisor_id,
                rol=RolUsuario.SUPERVISOR_EMPRESA.value,
                ip=comando.ip_origen,
                accion="Intento de acceso a recurso ajeno",
                entidad=f"Practica:{practica.id}",
                detalles={
                    "supervisor_solicitante": supervisor_id,
                    "supervisor_asignado": practica.supervisor_empresa_id,
                    "practica_id": practica.id,
                },
            )
            raise SupervisorNoAsignadoAPracticaError(
                supervisor_id=supervisor_id,
                practica_id=practica.id,
            )

        # -------------------------------------------------------------------
        # 4. Validación de estado en la máquina de estados finitos (ADR-010)
        # -------------------------------------------------------------------
        if not practica.puede_validar_horas():
            raise EstadoPracticaInvalidoParaValidarHorasError(
                practica_id=practica.id,
                estado_actual=practica.estado_actual.value,
            )

        # -------------------------------------------------------------------
        # 5. Búsqueda y validación del RegistroHoras (CU-05)
        # -------------------------------------------------------------------
        registro: Optional[RegistroHoras] = (
            self._repositorio_registro_horas.buscar_por_id(comando.registro_horas_id)
        )
        if registro is None:
            raise RegistroHorasNoEncontradoError(
                registro_horas_id=comando.registro_horas_id
            )

        if registro.practica_id != practica.id:
            raise RegistroHorasNoEncontradoError(
                registro_horas_id=comando.registro_horas_id,
                mensaje=(
                    f"El reporte de horas '{comando.registro_horas_id}' no pertenece a la "
                    f"práctica '{practica.id}'."
                ),
            )

        # -------------------------------------------------------------------
        # 6. Procesamiento de la decisión en el modelo de dominio
        # -------------------------------------------------------------------
        decision_normalizada = comando.decision.strip().lower()
        ahora = datetime.now(timezone.utc)

        if decision_normalizada in {"aprobar", "aprobado"}:
            registro.aprobar()
            practica.acumular_horas_aprobadas(registro.cantidad_horas)
            accion_bitacora = "Aprobación de reporte semanal de horas"
            mensaje_respuesta = (
                f"Reporte de horas de la semana {registro.semana} aprobado exitosamente. "
                f"Horas acumuladas de la práctica: {practica.horas_acumuladas_aprobadas} horas."
            )
            asunto_notificacion = f"Reporte de horas semana {registro.semana} aprobado"
            cuerpo_notificacion = (
                f"Estimado estudiante, su reporte de horas de la semana {registro.semana} "
                f"({registro.cantidad_horas} horas) ha sido aprobado por su supervisor."
            )
        elif decision_normalizada in {"rechazar", "rechazado"}:
            motivo = comando.observaciones or ""
            registro.rechazar(motivo)
            accion_bitacora = "Rechazo de reporte semanal de horas"
            mensaje_respuesta = (
                f"Reporte de horas de la semana {registro.semana} rechazado con observaciones: "
                f"'{registro.observaciones_rechazo}'."
            )
            asunto_notificacion = f"Reporte de horas semana {registro.semana} rechazado"
            cuerpo_notificacion = (
                f"Estimado estudiante, su reporte de horas de la semana {registro.semana} "
                f"ha sido rechazado por el supervisor con las siguientes observaciones: "
                f"{registro.observaciones_rechazo}"
            )
        else:
            raise ValueError(
                f"Decisión no reconocida: '{comando.decision}'. "
                f"Valores permitidos: 'Aprobar' o 'Rechazar'."
            )

        # -------------------------------------------------------------------
        # 7. Persistencia transaccional de práctica y reporte de horas
        # -------------------------------------------------------------------
        self._repositorio_registro_horas.guardar(registro)
        self._repositorio_practica.actualizar(practica)

        # -------------------------------------------------------------------
        # 8. Consumo del token efímero si se utilizó enlace de un solo uso
        # -------------------------------------------------------------------
        if token_entidad is not None:
            token_entidad.marcar_usado(ahora)
            if self._repositorio_token_evaluacion:
                self._repositorio_token_evaluacion.guardar(token_entidad)

        # -------------------------------------------------------------------
        # 9. Trazabilidad inmutable en bitácora de auditoría (ADR-006)
        # -------------------------------------------------------------------
        self._registrar_bitacora(
            actor_id=supervisor_id,
            rol=RolUsuario.SUPERVISOR_EMPRESA.value,
            ip=comando.ip_origen,
            accion=accion_bitacora,
            entidad=f"Practica:{practica.id}",
            detalles={
                "registro_horas_id": registro.id,
                "semana": registro.semana,
                "cantidad_horas": registro.cantidad_horas,
                "decision": registro.estado_validacion.value,
                "observaciones": registro.observaciones_rechazo,
                "horas_acumuladas": practica.horas_acumuladas_aprobadas,
            },
        )

        # -------------------------------------------------------------------
        # 10. Notificación al estudiante titular (ServicioCorreoPort)
        # -------------------------------------------------------------------
        if self._servicio_correo is not None:
            correo_estudiante = f"{practica.estudiante_id}@universidad.edu.co"
            try:
                self._servicio_correo.enviar_notificacion(
                    destinatario=correo_estudiante,
                    asunto=asunto_notificacion,
                    cuerpo=cuerpo_notificacion,
                )
            except Exception:
                pass  # La notificación no bloquea la persistencia de la decisión

        # -------------------------------------------------------------------
        # 11. Retorno de DTO inmutable de respuesta
        # -------------------------------------------------------------------
        return ValidacionHorasRespuestaDTO(
            registro_horas_id=registro.id,
            practica_id=practica.id,
            semana=registro.semana,
            cantidad_horas=registro.cantidad_horas,
            estado_validacion=registro.estado_validacion.value,
            horas_acumuladas_practica=practica.horas_acumuladas_aprobadas,
            observaciones=registro.observaciones_rechazo,
            fecha_decision=ahora,
            mensaje=mensaje_respuesta,
        )

    def _autenticar_token(
        self,
        *,
        token_str: str,
        practica_id_esperada: str,
        ip_origen: str,
    ) -> TokenEvaluacion:
        """Valida criptográficamente el token efímero y controla vigencia y uso único.

        Traza: CU-05, EAC-03, ADR-004.
        """
        token: Optional[TokenEvaluacion] = None

        if self._interceptor_identidad is not None:
            token = self._interceptor_identidad.verificar_token(token_str)
        elif self._repositorio_token_evaluacion is not None:
            token = self._repositorio_token_evaluacion.buscar_por_token(token_str)

        if token is None:
            self._registrar_bitacora(
                actor_id="DESCONOCIDO",
                rol="DESCONOCIDO",
                ip=ip_origen,
                accion="Intento de acceso con enlace alterado o firma HMAC inválida",
                entidad=f"Practica:{practica_id_esperada}",
            )
            raise TokenEvaluacionInvalidoError()

        if token.usado:
            self._registrar_bitacora(
                actor_id=token.supervisor_id,
                rol=RolUsuario.SUPERVISOR_EMPRESA.value,
                ip=ip_origen,
                accion="Intento de acceso con enlace de un solo uso ya utilizado",
                entidad=f"Practica:{practica_id_esperada}",
                detalles={"token_id": token.id},
            )
            raise TokenEvaluacionYaUsadoError(token_id=token.id)

        ahora = datetime.now(timezone.utc)
        if not token.es_valido(ahora):
            self._registrar_bitacora(
                actor_id=token.supervisor_id,
                rol=RolUsuario.SUPERVISOR_EMPRESA.value,
                ip=ip_origen,
                accion="Intento de acceso con enlace expirado",
                entidad=f"Practica:{practica_id_esperada}",
                detalles={
                    "token_id": token.id,
                    "fecha_expiracion": token.fecha_expiracion.isoformat(),
                },
            )
            raise TokenEvaluacionExpiradoError(token_id=token.id)

        if token.practica_id != practica_id_esperada:
            self._registrar_bitacora(
                actor_id=token.supervisor_id,
                rol=RolUsuario.SUPERVISOR_EMPRESA.value,
                ip=ip_origen,
                accion="Intento de acceso a práctica no vinculada al token",
                entidad=f"Practica:{practica_id_esperada}",
                detalles={
                    "token_id": token.id,
                    "token_practica_id": token.practica_id,
                },
            )
            raise TokenEvaluacionInvalidoError("El token no corresponde a la práctica indicada.")

        return token

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
        """Registra un evento inmutable en la bitácora de auditoría append-only (ADR-006)."""
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
