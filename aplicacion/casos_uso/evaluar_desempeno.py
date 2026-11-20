"""Caso de uso: Evaluar desempeño del practicante (CU-07).

Traza: CU-07, EAC-01, EAC-03, RN-01, RN-02, RN-03, RN-04, ADR-001, ADR-002, ADR-004,
ADR-005, ADR-006, ADR-007, ADR-010.

Implementa la orquestación de la consulta del formulario de rúbrica y el registro de la
evaluación de desempeño del practicante por parte del supervisor de empresa externo:
1. Autenticación híbrida mediante enlace criptográfico efímero con token HMAC (ADR-004)
   o contexto RBAC (ADR-005). Rechazo temprano e inmediato ante tokens alterados,
   expirados (> 15 días) o previamente utilizados, con 0 datos expuestos y registro
   en bitácora en menos de 1 minuto (EAC-03).
2. Autorización RBAC centralizada bajo política deny-by-default (ADR-005, RN-03):
   exclusivo para el rol SupervisorEmpresa (o Supervisor). Roles internos son rechazados
   con registro en bitácora.
3. Validación de pertenencia contextual de datos (RN-01): el supervisor solo puede
   consultar o evaluar la práctica que le fue asignada.
4. En la consulta del formulario (obtener_formulario_evaluacion): presenta los datos de
   identificación del estudiante y los criteriosRubrica de la ReglaPrograma vinculada a
   la práctica (ADR-007, EAC-01), manteniendo el TokenEvaluacion con usado = False.
5. En el envío de la evaluación (ejecutar):
   - Verifica unicidad de evaluación (máximo 1 EvaluacionDesempeno por práctica) y
     máquina de estados finitos (la práctica debe estar formalmente en estado EnEjecucion,
     ADR-010, RN-02), sin exigir el cumplimiento total de horasRequeridas (diferido a CU-09).
   - Valida e instancia EvaluacionDesempeno contra los criteriosRubrica de la versión de
     ReglaPrograma vinculada a la práctica (0% alteración ante cambios normativos, EAC-01),
     verificando escala 0.0 a 5.0 y observaciones obligatorias si la nota es reprobatoria (< 3.0).
   - Transiciona la práctica de EnEjecucion a Evaluada, marca el TokenEvaluacion con usado = True,
     persiste la evaluación y registra atómicamente el EventoBitacora (ADR-003, ADR-006).
   - Emite notificación por correo electrónico al DocenteAsesor asignado informando que la
     práctica fue evaluada y está lista para generar el ActaFinal (ADR-001).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from aplicacion.dtos.evaluacion_desempeno_dto import (
    ConsultarFormularioEvaluacionComando,
    EvaluacionDesempenoRespuestaDTO,
    EvaluarDesempenoComando,
    FormularioEvaluacionRespuestaDTO,
)
from aplicacion.puertos.repositorio_docente import RepositorioDocentePort
from aplicacion.puertos.repositorio_evaluacion_desempeno import (
    RepositorioEvaluacionDesempenoPort,
)
from aplicacion.puertos.repositorio_practica import RepositorioPracticaPort
from aplicacion.puertos.repositorio_regla import RepositorioReglaProgramaPort
from aplicacion.puertos.repositorio_token_evaluacion import (
    RepositorioTokenEvaluacionPort,
)
from aplicacion.puertos.servicio_correo import ServicioCorreoPort
from aplicacion.seguridad.autorizador_rbac import (
    AccesoDenegadoError,
    AutorizadorRBAC,
    ContextoUsuario,
    RolUsuario,
)
from dominio.errores import (
    CalificacionCuantitativaInvalidaError,
    EstadoPracticaInvalidoParaEvaluacionError,
    ObservacionesReprobatoriaRequeridasError,
    PracticaNoEncontradaError,
    PracticaYaEvaluadaError,
    ReglaProgramaNoConfiguradaError,
    RespuestasRubricaInvalidasError,
    SupervisorNoAsignadoAPracticaError,
    TokenEvaluacionExpiradoError,
    TokenEvaluacionInvalidoError,
    TokenEvaluacionYaUsadoError,
)
from dominio.modelos.docente_asesor import DocenteAsesor
from dominio.modelos.evaluacion_desempeno import EvaluacionDesempeno
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.practica import EstadoPractica, Practica
from dominio.modelos.regla_programa import ReglaPrograma
from dominio.modelos.token_evaluacion import TokenEvaluacion


class EvaluarDesempenoCasoUso:
    """Caso de uso del Módulo Seguimiento y Evaluación para evaluar el desempeño del practicante (CU-07)."""

    def __init__(
        self,
        *,
        repositorio_practica: RepositorioPracticaPort,
        repositorio_regla: RepositorioReglaProgramaPort,
        repositorio_evaluacion: RepositorioEvaluacionDesempenoPort,
        repositorio_token_evaluacion: Optional[RepositorioTokenEvaluacionPort] = None,
        repositorio_docente: Optional[RepositorioDocentePort] = None,
        servicio_correo: Optional[ServicioCorreoPort] = None,
        autorizador_rbac: Optional[AutorizadorRBAC] = None,
        interceptor_identidad: Optional[Any] = None,
    ) -> None:
        self._repositorio_practica: RepositorioPracticaPort = repositorio_practica
        self._repositorio_regla: RepositorioReglaProgramaPort = repositorio_regla
        self._repositorio_evaluacion: RepositorioEvaluacionDesempenoPort = (
            repositorio_evaluacion
        )
        self._repositorio_token_evaluacion: Optional[RepositorioTokenEvaluacionPort] = (
            repositorio_token_evaluacion
        )
        self._repositorio_docente: Optional[RepositorioDocentePort] = (
            repositorio_docente
        )
        self._servicio_correo: Optional[ServicioCorreoPort] = servicio_correo
        self._autorizador_rbac: AutorizadorRBAC = autorizador_rbac or AutorizadorRBAC()
        self._interceptor_identidad: Optional[Any] = interceptor_identidad

    def __call__(
        self,
        comando: EvaluarDesempenoComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> EvaluacionDesempenoRespuestaDTO:
        """Permite invocar la instancia como callable para registrar la evaluación de desempeño."""
        return self.ejecutar(comando, contexto=contexto)

    def obtener_formulario_evaluacion(
        self,
        comando: ConsultarFormularioEvaluacionComando,
    ) -> FormularioEvaluacionRespuestaDTO:
        """Consulta los datos del practicante y la rúbrica dinámica mediante un TokenEvaluacion válido.

        Traza: CU-07, Escenario 1 (Consulta exitosa de la rúbrica de evaluación mediante
        TokenEvaluacion válido y vigente), Escenarios 8, 9, 10, 13, 15 y 16 (EAC-01, EAC-03,
        ADR-004, ADR-006, ADR-007).

        Verifica la firma criptográfica HMAC, vigencia (<= 15 días) y disponibilidad de uso
        (usado == False) del TokenEvaluacion sin consumirlo.

        Args:
            comando: DTO inmutable con el token de acceso, práctica opcional e IP de origen.

        Returns:
            FormularioEvaluacionRespuestaDTO con los datos del estudiante y los criteriosRubrica
            de la versión de ReglaPrograma vinculada a la práctica.

        Raises:
            TokenEvaluacionInvalidoError: Si el enlace fue alterado o la firma HMAC es inválida.
            TokenEvaluacionExpiradoError: Si el enlace supera los 15 días calendario de emisión.
            TokenEvaluacionYaUsadoError: Si el enlace de un solo uso ya fue utilizado previamente.
            PracticaNoEncontradaError: Si la práctica vinculada no existe.
            SupervisorNoAsignadoAPracticaError: Si el supervisor no coincide con el de la práctica.
            ReglaProgramaNoConfiguradaError: Si la regla vinculada a la práctica no se encuentra.
        """
        # 1. Autenticación criptográfica del Magic Link (ADR-004, EAC-03)
        token_entidad = self._autenticar_token(
            token_str=comando.token_acceso,
            practica_id_esperada=comando.practica_id,
            ip_origen=comando.ip_origen,
        )

        # 2. Recuperación de la Práctica vinculada al token
        practica_id_objetivo = comando.practica_id or token_entidad.practica_id
        practica: Optional[Practica] = self._repositorio_practica.buscar_por_id(
            practica_id_objetivo
        )
        if practica is None:
            raise PracticaNoEncontradaError(practica_id=practica_id_objetivo)

        # 3. Validación de pertenencia contextual del supervisor (RN-01, ADR-005, Escenario 13)
        if (
            practica.supervisor_empresa_id
            and practica.supervisor_empresa_id != token_entidad.supervisor_id
        ):
            self._registrar_bitacora(
                actor_id=token_entidad.supervisor_id,
                rol=RolUsuario.SUPERVISOR_EMPRESA.value,
                ip=comando.ip_origen,
                accion="Intento de acceso a recurso ajeno",
                entidad=f"Practica:{practica.id}",
                detalles={
                    "supervisor_solicitante": token_entidad.supervisor_id,
                    "supervisor_asignado": practica.supervisor_empresa_id,
                    "practica_id": practica.id,
                    "operacion": "obtener_formulario_evaluacion",
                },
            )
            raise SupervisorNoAsignadoAPracticaError(
                supervisor_id=token_entidad.supervisor_id,
                practica_id=practica.id,
            )

        # 4. Recuperación de la ReglaPrograma vinculada a la práctica (ADR-007, EAC-01, Escenario 16)
        regla: Optional[ReglaPrograma] = self._repositorio_regla.buscar_por_id(
            practica.regla_programa_id
        )
        if regla is None:
            raise ReglaProgramaNoConfiguradaError(
                programa_academico=practica.regla_programa_id
            )

        criterios_dict = self._normalizar_criterios_rubrica_dict(regla.criterios_rubrica)

        # El TokenEvaluacion se mantiene con usado = False hasta el envío en firme
        return FormularioEvaluacionRespuestaDTO(
            practica_id=practica.id,
            estudiante_id=practica.estudiante_id,
            supervisor_id=token_entidad.supervisor_id,
            estado_practica=practica.estado_actual.value,
            regla_programa_id=regla.id,
            programa_academico=regla.programa_academico,
            version_regla=regla.version,
            criterios_rubrica=criterios_dict,
            escala_minima=EvaluacionDesempeno.CALIFICACION_MINIMA,
            escala_maxima=EvaluacionDesempeno.CALIFICACION_MAXIMA,
            umbral_aprobacion=EvaluacionDesempeno.UMBRAL_APROBACION,
            mensaje=(
                f"Formulario de evaluación cargado exitosamente para la práctica '{practica.id}' "
                f"(ReglaPrograma '{regla.id}' versión '{regla.version}')."
            ),
        )

    def ejecutar(
        self,
        comando: EvaluarDesempenoComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> EvaluacionDesempenoRespuestaDTO:
        """Registra la evaluación de desempeño del practicante y transiciona la práctica a Evaluada.

        Traza: CU-07, Escenarios 2 al 16, ADR-001, ADR-002, ADR-004, ADR-005, ADR-006,
        ADR-007, ADR-010.

        Args:
            comando: DTO inmutable con las respuestas de la rúbrica, nota cuantitativa,
                observaciones y credenciales.
            contexto: Contexto de identidad del usuario si se invoca mediante sesión autenticada.

        Returns:
            EvaluacionDesempenoRespuestaDTO con el resumen de la evaluación asentada y el nuevo
            estado 'Evaluada' de la práctica.

        Raises:
            TokenEvaluacionInvalidoError: Si el token HMAC es inválido, alterado o no corresponde.
            TokenEvaluacionExpiradoError: Si el token tiene más de 15 días de emisión.
            TokenEvaluacionYaUsadoError: Si el token de un solo uso ya fue consumido.
            AccesoDenegadoError: Si un rol interno no autorizado intenta registrar la evaluación.
            PracticaNoEncontradaError: Si la práctica indicada no existe.
            SupervisorNoAsignadoAPracticaError: Si el supervisor intenta evaluar una práctica ajena.
            PracticaYaEvaluadaError: Si la práctica ya cuenta con una EvaluacionDesempeno registrada.
            EstadoPracticaInvalidoParaEvaluacionError: Si la práctica no está en estado 'EnEjecucion'.
            CalificacionCuantitativaInvalidaError: Si la calificación está fuera de [0.0, 5.0].
            ObservacionesReprobatoriaRequeridasError: Si la calificación es < 3.0 y faltan observaciones.
            RespuestasRubricaInvalidasError: Si faltan criterios de la rúbrica o sus notas son inválidas.
        """
        token_entidad: Optional[TokenEvaluacion] = None
        supervisor_id: str = ""

        # -------------------------------------------------------------------
        # 1. Autenticación y Autorización (ADR-004, ADR-005, EAC-03, RN-03)
        # -------------------------------------------------------------------
        if contexto is not None:
            # Validación explícita de rol RBAC bajo política deny-by-default (Escenario 14)
            try:
                self._autorizador_rbac.validar_evaluacion_desempeno(
                    rol_actor=contexto.rol,
                    usuario_id=contexto.usuario_id,
                    operacion="evaluar_desempeno",
                )
            except AccesoDenegadoError as error_rbac:
                self._registrar_bitacora(
                    actor_id=contexto.usuario_id,
                    rol=contexto.rol,
                    ip=comando.ip_origen or contexto.ip_origen,
                    accion="Intento de operación por rol no autorizado",
                    entidad=f"Practica:{comando.practica_id}",
                    detalles={
                        "operacion": "evaluar_desempeno",
                        "diagnostico": str(error_rbac),
                    },
                )
                raise error_rbac
            supervisor_id = contexto.usuario_id

        if comando.token_acceso:
            # Autenticación vía enlace criptográfico efímero (Magic Link HMAC-SHA256)
            token_entidad = self._autenticar_token(
                token_str=comando.token_acceso,
                practica_id_esperada=comando.practica_id,
                ip_origen=comando.ip_origen,
                supervisor_id_solicitante=comando.supervisor_id or (supervisor_id or None),
            )
            if not supervisor_id:
                supervisor_id = (
                    comando.supervisor_id.strip()
                    if comando.supervisor_id and comando.supervisor_id.strip()
                    else token_entidad.supervisor_id
                )
        elif not supervisor_id:
            if comando.supervisor_id and comando.supervisor_id.strip():
                supervisor_id = comando.supervisor_id.strip()
            else:
                error_acceso = AccesoDenegadoError(
                    "No se proveyó credencial de acceso ni token efímero válido para evaluar desempeño.",
                    operacion="evaluar_desempeno",
                )
                self._registrar_bitacora(
                    actor_id="DESCONOCIDO",
                    rol="DESCONOCIDO",
                    ip=comando.ip_origen,
                    accion="Intento de acceso sin credenciales a evaluación de desempeño",
                    entidad=f"Practica:{comando.practica_id}",
                )
                raise error_acceso

        # -------------------------------------------------------------------
        # 2. Recuperación de la Práctica y pertenencia contextual (RN-01, ADR-005)
        # -------------------------------------------------------------------
        practica: Optional[Practica] = self._repositorio_practica.buscar_por_id(
            comando.practica_id
        )
        if practica is None:
            raise PracticaNoEncontradaError(practica_id=comando.practica_id)

        # Validación de pertenencia contextual entre el SupervisorEmpresa y la Práctica (Escenario 13)
        supervisor_evaluador_id = (
            comando.supervisor_id.strip()
            if comando.supervisor_id and comando.supervisor_id.strip()
            else supervisor_id
        )
        if (
            practica.supervisor_empresa_id
            and practica.supervisor_empresa_id != supervisor_evaluador_id
        ) or (
            practica.supervisor_empresa_id
            and token_entidad is not None
            and practica.supervisor_empresa_id != token_entidad.supervisor_id
        ):
            actor_rechazado = (
                supervisor_evaluador_id
                if practica.supervisor_empresa_id != supervisor_evaluador_id
                else token_entidad.supervisor_id  # type: ignore[union-attr]
            )
            self._registrar_bitacora(
                actor_id=actor_rechazado,
                rol=RolUsuario.SUPERVISOR_EMPRESA.value,
                ip=comando.ip_origen,
                accion="Intento de acceso a recurso ajeno",
                entidad=f"Practica:{practica.id}",
                detalles={
                    "supervisor_solicitante": actor_rechazado,
                    "supervisor_asignado": practica.supervisor_empresa_id,
                    "practica_id": practica.id,
                    "operacion": "evaluar_desempeno",
                },
            )
            raise SupervisorNoAsignadoAPracticaError(
                supervisor_id=actor_rechazado,
                practica_id=practica.id,
            )

        supervisor_id = supervisor_evaluador_id

        # -------------------------------------------------------------------
        # 3. Verificación de unicidad de evaluación y máquina de estados (ADR-010, RN-02)
        # -------------------------------------------------------------------
        evaluacion_existente: Optional[EvaluacionDesempeno] = (
            self._repositorio_evaluacion.buscar_por_practica(practica.id)
        )
        if evaluacion_existente is not None:
            raise PracticaYaEvaluadaError(
                practica_id=practica.id,
                evaluacion_id=evaluacion_existente.id,
            )

        if not practica.puede_evaluar_desempeno():
            raise EstadoPracticaInvalidoParaEvaluacionError(
                practica_id=practica.id,
                estado_actual=practica.estado_actual.value,
            )

        # -------------------------------------------------------------------
        # 4. Recuperación de la ReglaPrograma vinculada y validación de rúbrica
        #    y calificación en el dominio (ADR-007, EAC-01, Escenarios 4, 5, 6, 7, 16)
        # -------------------------------------------------------------------
        regla: Optional[ReglaPrograma] = self._repositorio_regla.buscar_por_id(
            practica.regla_programa_id
        )
        if regla is None:
            raise ReglaProgramaNoConfiguradaError(
                programa_academico=practica.regla_programa_id
            )

        ahora = datetime.now(timezone.utc)

        # Instanciar EvaluacionDesempeno valida:
        # - calificacion_cuantitativa en [0.0, 5.0] (Escenario 6)
        # - observaciones obligatorias si calificacion_cuantitativa < 3.0 (Escenarios 4 y 5)
        # - respuestas_rubrica contra criterios_rubrica de la ReglaPrograma vinculada (Escenarios 7 y 16)
        # Si falla cualquier validación, lanza excepción antes de mutar la práctica o consumir el token.
        evaluacion = EvaluacionDesempeno(
            practica_id=practica.id,
            supervisor_id=supervisor_id,
            calificacion_cuantitativa=comando.calificacion_cuantitativa,
            respuestas_rubrica=comando.respuestas_rubrica,
            observaciones=comando.observaciones,
            criterios_rubrica_esperados=regla.criterios_rubrica,
            fecha_evaluacion=ahora,
        )

        # -------------------------------------------------------------------
        # 5. Transición de estado, consumo de token y persistencia atómica
        #    (ADR-003, ADR-004, ADR-006, ADR-010)
        # -------------------------------------------------------------------
        practica.registrar_evaluacion_desempeno(fecha_fin=ahora)

        token_consumido = False
        if token_entidad is not None:
            token_entidad.marcar_usado(ahora)
            token_consumido = True
            if self._repositorio_token_evaluacion is not None:
                self._repositorio_token_evaluacion.guardar(token_entidad)

        self._repositorio_evaluacion.guardar(evaluacion)
        self._repositorio_practica.actualizar(practica)

        self._registrar_bitacora(
            actor_id=supervisor_id,
            rol=RolUsuario.SUPERVISOR_EMPRESA.value,
            ip=comando.ip_origen,
            accion="Evaluación de desempeño registrada",
            entidad=f"Practica:{practica.id}",
            detalles={
                "evaluacion_id": evaluacion.id,
                "practica_id": practica.id,
                "supervisor_id": supervisor_id,
                "calificacion_cuantitativa": evaluacion.calificacion_cuantitativa,
                "es_aprobatoria": evaluacion.es_aprobatoria,
                "observaciones": evaluacion.observaciones,
                "respuestas_rubrica": evaluacion.respuestas_rubrica,
                "estado_anterior": EstadoPractica.EN_EJECUCION.value,
                "nuevo_estado": practica.estado_actual.value,
                "regla_programa_id": regla.id,
                "version_regla": regla.version,
                "token_consumido": token_consumido,
            },
        )

        # -------------------------------------------------------------------
        # 6. Notificación por correo electrónico al DocenteAsesor (ADR-001)
        # -------------------------------------------------------------------
        self._notificar_docente_asesor(practica=practica, evaluacion=evaluacion)

        # -------------------------------------------------------------------
        # 7. Retorno del DTO inmutable de salida
        # -------------------------------------------------------------------
        tipo_resultado = "aprobatoria" if evaluacion.es_aprobatoria else "reprobatoria"
        mensaje_respuesta = (
            f"Evaluación de desempeño ({tipo_resultado}, nota {evaluacion.calificacion_cuantitativa:.1f}) "
            f"registrada exitosamente para la práctica '{practica.id}'. "
            f"La práctica ha cambiado a estado '{practica.estado_actual.value}'."
        )

        return EvaluacionDesempenoRespuestaDTO(
            evaluacion_id=evaluacion.id,
            practica_id=practica.id,
            supervisor_id=evaluacion.supervisor_id,
            calificacion_cuantitativa=evaluacion.calificacion_cuantitativa,
            es_aprobatoria=evaluacion.es_aprobatoria,
            observaciones=evaluacion.observaciones,
            respuestas_rubrica=evaluacion.respuestas_rubrica,
            estado_practica=practica.estado_actual.value,
            regla_programa_id=regla.id,
            version_regla=regla.version,
            token_consumido=token_consumido,
            fecha_evaluacion=evaluacion.fecha_evaluacion,
            mensaje=mensaje_respuesta,
        )

    # -----------------------------------------------------------------------
    # Métodos privados auxiliares
    # -----------------------------------------------------------------------

    def _autenticar_token(
        self,
        *,
        token_str: str,
        practica_id_esperada: Optional[str],
        ip_origen: str,
        supervisor_id_solicitante: Optional[str] = None,
    ) -> TokenEvaluacion:
        """Verifica la firma criptográfica HMAC, vigencia (15 días) y uso único del TokenEvaluacion.

        Traza: CU-07, Escenarios 1, 8, 9, 10, 13 y 15 (EAC-03, ADR-004, ADR-006).
        """
        entidad_ref = (
            f"Practica:{practica_id_esperada}"
            if practica_id_esperada
            else "ModuloEvaluacionDesempeno"
        )
        token: Optional[TokenEvaluacion] = None

        try:
            if self._interceptor_identidad is not None:
                token = self._interceptor_identidad.verificar_token(token_str)
            elif self._repositorio_token_evaluacion is not None:
                token = self._repositorio_token_evaluacion.buscar_por_token(token_str)
        except TokenEvaluacionInvalidoError as err:
            self._registrar_bitacora(
                actor_id="DESCONOCIDO",
                rol="DESCONOCIDO",
                ip=ip_origen,
                accion="Acceso rechazado por token inválido o adulterado",
                entidad=entidad_ref,
            )
            raise err
        except TokenEvaluacionYaUsadoError as err:
            actor_token = "DESCONOCIDO"
            if self._repositorio_token_evaluacion is not None and err.token_id:
                tok_prev = self._repositorio_token_evaluacion.buscar_por_id(err.token_id)
                if tok_prev is not None:
                    actor_token = tok_prev.supervisor_id
            self._registrar_bitacora(
                actor_id=actor_token,
                rol=RolUsuario.SUPERVISOR_EMPRESA.value,
                ip=ip_origen,
                accion="Intento de acceso con token ya utilizado",
                entidad=entidad_ref,
                detalles={"token_id": err.token_id},
            )
            raise err
        except TokenEvaluacionExpiradoError as err:
            actor_token = "DESCONOCIDO"
            if self._repositorio_token_evaluacion is not None and err.token_id:
                tok_exp = self._repositorio_token_evaluacion.buscar_por_id(err.token_id)
                if tok_exp is not None:
                    actor_token = tok_exp.supervisor_id
            self._registrar_bitacora(
                actor_id=actor_token,
                rol=RolUsuario.SUPERVISOR_EMPRESA.value,
                ip=ip_origen,
                accion="Acceso rechazado por token expirado",
                entidad=entidad_ref,
                detalles={"token_id": err.token_id},
            )
            raise err

        if token is None:
            self._registrar_bitacora(
                actor_id="DESCONOCIDO",
                rol="DESCONOCIDO",
                ip=ip_origen,
                accion="Acceso rechazado por token inválido o adulterado",
                entidad=entidad_ref,
            )
            raise TokenEvaluacionInvalidoError()

        entidad_token_ref = (
            f"Practica:{practica_id_esperada}"
            if practica_id_esperada
            else f"Practica:{token.practica_id}"
        )

        if token.usado:
            self._registrar_bitacora(
                actor_id=token.supervisor_id,
                rol=RolUsuario.SUPERVISOR_EMPRESA.value,
                ip=ip_origen,
                accion="Intento de acceso con token ya utilizado",
                entidad=entidad_token_ref,
                detalles={"token_id": token.id},
            )
            raise TokenEvaluacionYaUsadoError(token_id=token.id)

        ahora = datetime.now(timezone.utc)
        if not token.es_valido(ahora):
            self._registrar_bitacora(
                actor_id=token.supervisor_id,
                rol=RolUsuario.SUPERVISOR_EMPRESA.value,
                ip=ip_origen,
                accion="Acceso rechazado por token expirado",
                entidad=entidad_token_ref,
                detalles={
                    "token_id": token.id,
                    "fecha_expiracion": token.fecha_expiracion.isoformat(),
                },
            )
            raise TokenEvaluacionExpiradoError(token_id=token.id)

        if practica_id_esperada and token.practica_id != practica_id_esperada:
            # Si el token pertenece a un supervisor que intenta evaluar otra práctica ajena (Escenario 13)
            practica_objetivo = self._repositorio_practica.buscar_por_id(
                practica_id_esperada
            )
            if (
                practica_objetivo is not None
                and practica_objetivo.supervisor_empresa_id
                and practica_objetivo.supervisor_empresa_id != token.supervisor_id
            ):
                self._registrar_bitacora(
                    actor_id=token.supervisor_id,
                    rol=RolUsuario.SUPERVISOR_EMPRESA.value,
                    ip=ip_origen,
                    accion="Intento de acceso a recurso ajeno",
                    entidad=f"Practica:{practica_id_esperada}",
                    detalles={
                        "token_id": token.id,
                        "supervisor_solicitante": token.supervisor_id,
                        "supervisor_asignado": practica_objetivo.supervisor_empresa_id,
                        "practica_id": practica_id_esperada,
                    },
                )
                raise SupervisorNoAsignadoAPracticaError(
                    supervisor_id=token.supervisor_id,
                    practica_id=practica_id_esperada,
                )

            self._registrar_bitacora(
                actor_id=token.supervisor_id,
                rol=RolUsuario.SUPERVISOR_EMPRESA.value,
                ip=ip_origen,
                accion="Acceso rechazado por token inválido o adulterado",
                entidad=f"Practica:{practica_id_esperada}",
                detalles={
                    "token_id": token.id,
                    "token_practica_id": token.practica_id,
                },
            )
            raise TokenEvaluacionInvalidoError(
                "El enlace de evaluación no corresponde a la práctica indicada."
            )

        return token

    @staticmethod
    def _normalizar_criterios_rubrica_dict(
        criterios_rubrica: Any,
    ) -> dict[str, Any]:
        """Convierte los criteriosRubrica de la ReglaPrograma en un diccionario inmutable para el DTO."""
        if isinstance(criterios_rubrica, Mapping):
            return dict(criterios_rubrica)
        if isinstance(criterios_rubrica, (list, tuple, set)):
            resultado: dict[str, Any] = {}
            for item in criterios_rubrica:
                if isinstance(item, Mapping):
                    clave = (
                        item.get("id")
                        or item.get("codigo")
                        or item.get("criterio")
                        or item.get("nombre")
                    )
                    if clave and str(clave).strip():
                        resultado[str(clave).strip()] = dict(item)
                elif str(item).strip():
                    resultado[str(item).strip()] = {"nombre": str(item).strip()}
            return resultado
        return {}

    def _notificar_docente_asesor(
        self,
        *,
        practica: Practica,
        evaluacion: EvaluacionDesempeno,
    ) -> None:
        """Envía notificación por correo electrónico al DocenteAsesor asignado (Escenario 2, ADR-001)."""
        if self._servicio_correo is None or not practica.docente_asesor_id:
            return

        correo_docente: Optional[str] = None
        if self._repositorio_docente is not None:
            docente: Optional[DocenteAsesor] = self._repositorio_docente.buscar_por_id(
                practica.docente_asesor_id
            )
            if docente is not None:
                correo_docente = docente.correo_institucional

        if not correo_docente:
            correo_docente = (
                practica.docente_asesor_id
                if "@" in practica.docente_asesor_id
                else f"{practica.docente_asesor_id}@universidad.edu.co"
            )

        asunto = f"Práctica evaluada y lista para generar ActaFinal - Práctica {practica.id}"
        cuerpo = (
            f"Estimado/a docente asesor/a ({practica.docente_asesor_id}):\n\n"
            f"Le informamos que el supervisor de empresa '{evaluacion.supervisor_id}' ha registrado "
            f"la evaluación de desempeño para la práctica '{practica.id}' del estudiante "
            f"'{practica.estudiante_id}'.\n\n"
            f"- Calificación cuantitativa: {evaluacion.calificacion_cuantitativa:.1f}\n"
            f"- Nuevo estado de la práctica: {practica.estado_actual.value}\n\n"
            f"La práctica fue evaluada y se encuentra lista para generar el ActaFinal.\n\n"
            f"Atentamente,\n"
            f"Sistema de Gestión de Prácticas Empresariales"
        )

        try:
            self._servicio_correo.enviar_notificacion(
                destinatario=correo_docente,
                asunto=asunto,
                cuerpo=cuerpo,
            )
        except Exception:
            # ADR-001: un fallo en el despacho de correo no revierte la transacción atómica de la evaluación
            pass

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
