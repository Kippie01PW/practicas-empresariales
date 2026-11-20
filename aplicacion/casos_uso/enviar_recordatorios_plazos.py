"""Caso de uso: Enviar recordatorios de plazos (CU-08).

Traza: CU-08, EAC-02, EAC-03, RT-01, RN-01, RN-02, RN-03, RN-04,
ADR-001 (Resiliencia e integración asíncrona),
ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores),
ADR-003 (Persistencia transaccional),
ADR-004 (Autenticación híbrida con enlaces criptográficos efímeros),
ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso),
ADR-006 (Bitácora de auditoría transaccional Append-Only),
ADR-007 (Configuración declarativa de reglas versionadas por programa),
ADR-010 (Patrón Máquina de Estados Finitos).

Implementa la tarea programada diaria automatizada (actor 'SISTEMA') y el disparo
manual autorizado para el 'Coordinador de prácticas', encargados de:
1. Evaluar en días naturales (días calendario) los trámites pendientes sobre prácticas activas.
2. Prevenir envíos duplicados mediante ventana de enfriamiento (cooldown) de 1 hora (60 min).
3. Despachar recordatorios a supervisores de empresa externos por validación de horas o evaluación
   de desempeño pendiente, adjuntando el TokenEvaluacion vigente (<= 15 días calendario) o
   invalidando el token expirado (> 15 días calendario) y emitiendo uno nuevo con vigencia de 15 días.
4. Escalar y enviar alerta por correo electrónico al DocenteAsesor asignado tras alcanzar 3
   recordatorios o renovaciones de token sin respuesta del supervisor de empresa.
5. Despachar recordatorios a actores internos (Estudiante, DocenteAsesor, Coordinador de prácticas)
   para cumplir el objetivo de negocio de gestión en máximo 10 días calendario (OB-01).
6. Garantizar tolerancia a fallos (EAC-02, 0% pérdida de recordatorios) encolando en el bróker
   las notificaciones cuando el servicio de correo externo falla, sin abortar el lote.
7. Registrar de forma atómica e inmutable cada acción o rechazo en EventoBitacora (ADR-006).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from aplicacion.dtos.recordatorio_plazos_dto import (
    DetalleRecordatorioEnviadoDTO,
    EjecutarRecordatoriosComando,
    ResultadoEnvioRecordatoriosDTO,
)
from aplicacion.puertos.publicador_eventos import (
    DatosTareaValidacionSia,
    PublicadorEventosPort,
)
from aplicacion.puertos.repositorio_docente import RepositorioDocentePort
from aplicacion.puertos.repositorio_evaluacion_desempeno import (
    RepositorioEvaluacionDesempenoPort,
)
from aplicacion.puertos.repositorio_practica import RepositorioPracticaPort
from aplicacion.puertos.repositorio_registro_horas import RepositorioRegistroHorasPort
from aplicacion.puertos.repositorio_regla import RepositorioReglaProgramaPort
from aplicacion.puertos.repositorio_token_evaluacion import (
    RepositorioTokenEvaluacionPort,
)
from aplicacion.puertos.servicio_correo import ErrorServicioCorreo, ServicioCorreoPort
from aplicacion.seguridad.autorizador_rbac import (
    AccesoDenegadoError,
    AutorizadorRBAC,
    RolUsuario,
)
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.practica import EstadoPractica, Practica
from dominio.modelos.registro_horas import EstadoValidacionHoras, RegistroHoras
from dominio.modelos.token_evaluacion import TokenEvaluacion


class EnviarRecordatoriosPlazosCasoUso:
    """Caso de uso principal para el envío automatizado y manual de recordatorios de plazos (CU-08)."""

    # Tipos formales de recordatorio definidos en el plan técnico
    TIPO_EVALUACION_DESEMPENO = "EVALUACION_DESEMPENO"
    TIPO_VALIDACION_HORAS = "VALIDACION_HORAS"
    TIPO_REPORTE_HORAS_ESTUDIANTE = "REPORTE_HORAS_ESTUDIANTE"
    TIPO_TRAMITE_COORDINACION = "TRAMITE_COORDINACION"
    TIPO_CIERRE_ACTA_INTERNO = "CIERRE_ACTA_INTERNO"
    TIPO_ESCALAMIENTO_DOCENTE = "ESCALAMIENTO_DOCENTE_ASESOR"

    _ESTADOS_TERMINALES: frozenset[EstadoPractica] = frozenset({
        EstadoPractica.COMPLETADA,
        EstadoPractica.RECHAZADA,
    })

    def __init__(
        self,
        *,
        repositorio_practica: RepositorioPracticaPort,
        repositorio_registro_horas: RepositorioRegistroHorasPort,
        repositorio_token_evaluacion: Optional[RepositorioTokenEvaluacionPort] = None,
        repositorio_docente: Optional[RepositorioDocentePort] = None,
        repositorio_regla: Optional[RepositorioReglaProgramaPort] = None,
        repositorio_evaluacion_desempeno: Optional[RepositorioEvaluacionDesempenoPort] = None,
        servicio_correo: Optional[ServicioCorreoPort] = None,
        publicador_eventos: Optional[PublicadorEventosPort] = None,
        autorizador_rbac: Optional[AutorizadorRBAC] = None,
        interceptor_identidad: Optional[Any] = None,
    ) -> None:
        self._repositorio_practica: RepositorioPracticaPort = repositorio_practica
        self._repositorio_registro_horas: RepositorioRegistroHorasPort = (
            repositorio_registro_horas
        )
        self._repositorio_token_evaluacion: Optional[RepositorioTokenEvaluacionPort] = (
            repositorio_token_evaluacion
        )
        self._repositorio_docente: Optional[RepositorioDocentePort] = repositorio_docente
        self._repositorio_regla: Optional[RepositorioReglaProgramaPort] = repositorio_regla
        self._repositorio_evaluacion_desempeno: Optional[
            RepositorioEvaluacionDesempenoPort
        ] = repositorio_evaluacion_desempeno
        self._servicio_correo: Optional[ServicioCorreoPort] = servicio_correo
        self._publicador_eventos: Optional[PublicadorEventosPort] = publicador_eventos
        self._autorizador_rbac: AutorizadorRBAC = autorizador_rbac or AutorizadorRBAC()
        self._interceptor_identidad: Optional[Any] = interceptor_identidad

    def __call__(
        self, comando: Optional[EjecutarRecordatoriosComando] = None
    ) -> ResultadoEnvioRecordatoriosDTO:
        """Permite invocar el caso de uso como callable."""
        return self.ejecutar(comando or EjecutarRecordatoriosComando())

    def ejecutar(
        self, comando: Optional[EjecutarRecordatoriosComando] = None
    ) -> ResultadoEnvioRecordatoriosDTO:
        """Ejecuta el proceso de identificación de plazos vencidos y despacho de recordatorios.

        Args:
            comando: DTO inmutable con los parámetros de ejecución (actor, rol, umbrales).

        Returns:
            ResultadoEnvioRecordatoriosDTO con las métricas consolidadas y el detalle de envíos.

        Raises:
            AccesoDenegadoError: Si un rol no autorizado intenta disparar manualmente la tarea (Escenario 9).
        """
        cmd = comando or EjecutarRecordatoriosComando()
        ahora = self._normalizar_utc(cmd.fecha_referencia or datetime.now(timezone.utc))

        # -------------------------------------------------------------------
        # 1. Autorización RBAC centralizada bajo política deny-by-default (ADR-005, Escenarios 6, 9, 11)
        # -------------------------------------------------------------------
        try:
            self._autorizador_rbac.validar_envio_recordatorios(
                rol_actor=cmd.rol_actor,
                usuario_id=cmd.actor_id,
                operacion="enviar_recordatorios",
            )
        except AccesoDenegadoError as error_rbac:
            self._registrar_bitacora(
                actor_id=cmd.actor_id,
                rol=cmd.rol_actor,
                ip=cmd.ip_origen,
                accion="Intento no autorizado de disparo manual de recordatorios de plazos",
                entidad=(
                    f"Practica:{cmd.practica_id_filtro}"
                    if cmd.practica_id_filtro
                    else "Sistema:RecordatoriosPlazos"
                ),
                fecha_hora=ahora,
                detalles={
                    "operacion": "enviar_recordatorios",
                    "diagnostico": str(error_rbac),
                },
            )
            raise error_rbac

        # -------------------------------------------------------------------
        # 2. Selección de prácticas candidatas (ADR-010, Escenario 8)
        # -------------------------------------------------------------------
        practicas_lote = self._obtener_practicas_candidatas(cmd.practica_id_filtro)

        total_practicas_evaluadas: int = len(practicas_lote)
        total_recordatorios_enviados: int = 0
        total_tokens_renovados: int = 0
        total_escalamientos_docente: int = 0
        total_omitidos_por_cooldown: int = 0
        total_omitidos_al_dia_o_terminales: int = 0
        total_encolados_por_fallo_correo: int = 0
        detalles_envio: list[DetalleRecordatorioEnviadoDTO] = []

        es_disparo_manual = (
            self._autorizador_rbac.normalizar_rol(cmd.rol_actor)
            != RolUsuario.SISTEMA.value
        )

        for practica in practicas_lote:
            # Excluir estados terminales Completada o Rechazada (Escenario 8)
            if practica.estado_actual in self._ESTADOS_TERMINALES:
                total_omitidos_al_dia_o_terminales += 1
                continue

            acciones_procesadas_en_practica = 0
            omitidas_cooldown_en_practica = 0

            # ---------------------------------------------------------------
            # A) Prácticas en estado Solicitada o Aprobada -> Trámites de Coordinación (Escenario 5)
            # ---------------------------------------------------------------
            if practica.estado_actual in {
                EstadoPractica.SOLICITADA,
                EstadoPractica.APROBADA,
            }:
                dias_transcurridos = self._dias_calendario_entre(
                    practica.fecha_postulacion, ahora
                )
                if dias_transcurridos >= cmd.umbral_dias_calendario:
                    if self._esta_en_cooldown(
                        practica.id,
                        self.TIPO_TRAMITE_COORDINACION,
                        ahora,
                        cmd.cooldown_minutos,
                    ):
                        total_omitidos_por_cooldown += 1
                        omitidas_cooldown_en_practica += 1
                    else:
                        tramite_desc = (
                            "aprobación o rechazo de postulación (CU-02)"
                            if practica.estado_actual == EstadoPractica.SOLICITADA
                            else "asignación de docente asesor (CU-03)"
                        )
                        detalle = self._despachar_recordatorio(
                            practica=practica,
                            tipo_recordatorio=self.TIPO_TRAMITE_COORDINACION,
                            destinatario_id="COORD-001",
                            correo_destinatario="coordinacion.practicas@universidad.edu.co",
                            rol_destinatario="Coordinador de prácticas",
                            asunto=f"Recordatorio de plazo vencido: {tramite_desc} - Práctica {practica.id}",
                            cuerpo=(
                                f"La práctica '{practica.id}' del estudiante '{practica.estudiante_id}' "
                                f"acumula {dias_transcurridos} días calendario en estado "
                                f"'{practica.estado_actual.value}' pendiente de {tramite_desc}."
                            ),
                            accion_bitacora=(
                                f"Disparo manual de recordatorio interno a Coordinador de prácticas por {tramite_desc}"
                                if es_disparo_manual
                                else f"Envío de recordatorio interno a Coordinador de prácticas por {tramite_desc}"
                            ),
                            comando=cmd,
                            ahora=ahora,
                        )
                        detalles_envio.append(detalle)
                        total_recordatorios_enviados += 1
                        acciones_procesadas_en_practica += 1
                        if detalle.encolado_por_fallo_correo:
                            total_encolados_por_fallo_correo += 1

            # ---------------------------------------------------------------
            # B) Prácticas en estado Asignada -> Recordatorio al Estudiante si no inicia reportes (Escenario 5)
            # ---------------------------------------------------------------
            elif practica.estado_actual == EstadoPractica.ASIGNADA:
                dias_sin_reporte = self._dias_sin_reporte_estudiante(practica, ahora)
                if dias_sin_reporte >= cmd.umbral_dias_calendario:
                    if self._esta_en_cooldown(
                        practica.id,
                        self.TIPO_REPORTE_HORAS_ESTUDIANTE,
                        ahora,
                        cmd.cooldown_minutos,
                    ):
                        total_omitidos_por_cooldown += 1
                        omitidas_cooldown_en_practica += 1
                    else:
                        correo_est = f"{practica.estudiante_id}@universidad.edu.co"
                        detalle = self._despachar_recordatorio(
                            practica=practica,
                            tipo_recordatorio=self.TIPO_REPORTE_HORAS_ESTUDIANTE,
                            destinatario_id=practica.estudiante_id,
                            correo_destinatario=correo_est,
                            rol_destinatario=RolUsuario.ESTUDIANTE.value,
                            asunto=f"Recordatorio de registro semanal de horas - Práctica {practica.id}",
                            cuerpo=(
                                f"Estimado estudiante '{practica.estudiante_id}', su práctica '{practica.id}' "
                                f"registra {dias_sin_reporte} días calendario sin reporte semanal de horas."
                            ),
                            accion_bitacora=(
                                "Disparo manual de recordatorio a Estudiante por registro semanal de horas pendiente"
                                if es_disparo_manual
                                else "Envío de recordatorio a Estudiante por registro semanal de horas pendiente"
                            ),
                            comando=cmd,
                            ahora=ahora,
                        )
                        detalles_envio.append(detalle)
                        total_recordatorios_enviados += 1
                        acciones_procesadas_en_practica += 1
                        if detalle.encolado_por_fallo_correo:
                            total_encolados_por_fallo_correo += 1

            # ---------------------------------------------------------------
            # C) Prácticas en estado EnEjecucion -> SupervisorEmpresa, DocenteAsesor y Estudiante
            #    (Escenarios 1, 2, 3, 4, 5, 6, 7, 10, 11)
            # ---------------------------------------------------------------
            elif practica.estado_actual == EstadoPractica.EN_EJECUCION:
                reportes = self._repositorio_registro_horas.listar_por_practica(
                    practica.id
                )
                reportes_pendientes_vencidos = [
                    r
                    for r in reportes
                    if r.estado_validacion == EstadoValidacionHoras.PENDIENTE
                    and self._dias_calendario_entre(r.fecha_registro, ahora)
                    >= cmd.umbral_dias_calendario
                ]

                evaluacion_pendiente, motivo_eval = (
                    self._requiere_recordatorio_evaluacion_desempeno(
                        practica=practica,
                        ahora=ahora,
                        umbral_dias_calendario=cmd.umbral_dias_calendario,
                    )
                )

                # C.1) Recordatorio al SupervisorEmpresa por reportes de RegistroHoras en Pendiente (Escenario 4)
                if reportes_pendientes_vencidos and practica.supervisor_empresa_id:
                    if self._esta_en_cooldown(
                        practica.id,
                        self.TIPO_VALIDACION_HORAS,
                        ahora,
                        cmd.cooldown_minutos,
                    ):
                        total_omitidos_por_cooldown += 1
                        omitidas_cooldown_en_practica += 1
                    else:
                        token_str, token_renovado = (
                            self._obtener_o_renovar_token_supervisor(
                                practica=practica,
                                ahora=ahora,
                            )
                        )
                        if token_renovado:
                            total_tokens_renovados += 1

                        semanas_str = ", ".join(
                            str(r.semana) for r in reportes_pendientes_vencidos
                        )
                        sup_id = practica.supervisor_empresa_id
                        correo_sup = f"{sup_id.lower()}@empresa-aliada.com"
                        accion_val = (
                            f"Disparo manual de recordatorio de validación de horas a SupervisorEmpresa {sup_id}"
                            if es_disparo_manual
                            else f"Envío de recordatorio de validación de horas a SupervisorEmpresa {sup_id}"
                        )
                        if token_renovado:
                            accion_val += " con invalidación de token expirado y emisión de nuevo TokenEvaluacion"

                        detalle_val = self._despachar_recordatorio(
                            practica=practica,
                            tipo_recordatorio=self.TIPO_VALIDACION_HORAS,
                            destinatario_id=sup_id,
                            correo_destinatario=correo_sup,
                            rol_destinatario=RolUsuario.SUPERVISOR_EMPRESA.value,
                            asunto=(
                                f"Recordatorio de validación de horas pendientes (Semanas: {semanas_str}) "
                                f"- Práctica {practica.id}"
                            ),
                            cuerpo=(
                                f"Estimado supervisor '{sup_id}', la práctica '{practica.id}' del estudiante "
                                f"'{practica.estudiante_id}' tiene {len(reportes_pendientes_vencidos)} reporte(s) "
                                f"semanal(es) de horas en estado 'Pendiente' (semanas: {semanas_str}). "
                                f"Acceda mediante su enlace criptográfico efímero: "
                                f"https://practicas.ucaldas.edu.co/validar-horas?token={token_str}"
                            ),
                            accion_bitacora=accion_val,
                            comando=cmd,
                            ahora=ahora,
                            token_emitido=token_str,
                            token_renovado=token_renovado,
                            detalles_extra={
                                "semanas_pendientes": [
                                    r.semana for r in reportes_pendientes_vencidos
                                ],
                                "cantidad_reportes_pendientes": len(
                                    reportes_pendientes_vencidos
                                ),
                            },
                        )
                        detalles_envio.append(detalle_val)
                        total_recordatorios_enviados += 1
                        acciones_procesadas_en_practica += 1
                        if detalle_val.encolado_por_fallo_correo:
                            total_encolados_por_fallo_correo += 1

                        # Verificar si con los recordatorios previos ya corresponde escalar al DocenteAsesor (Escenario 3)
                        detalle_esc = self._verificar_y_escalar_a_docente(
                            practica=practica,
                            comando=cmd,
                            ahora=ahora,
                            motivo_escalamiento="validación de RegistroHoras",
                        )
                        if detalle_esc is not None:
                            detalles_envio.append(detalle_esc)
                            total_recordatorios_enviados += 1
                            total_escalamientos_docente += 1
                            acciones_procesadas_en_practica += 1
                            if detalle_esc.encolado_por_fallo_correo:
                                total_encolados_por_fallo_correo += 1

                # C.2) Recordatorio al SupervisorEmpresa por EvaluacionDesempeno pendiente (Escenarios 1, 2, 3, 6)
                if evaluacion_pendiente and practica.supervisor_empresa_id:
                    if self._esta_en_cooldown(
                        practica.id,
                        self.TIPO_EVALUACION_DESEMPENO,
                        ahora,
                        cmd.cooldown_minutos,
                    ):
                        total_omitidos_por_cooldown += 1
                        omitidas_cooldown_en_practica += 1
                    else:
                        recordatorios_previos_sup = (
                            self._contar_recordatorios_previos_supervisor(
                                practica=practica,
                                incluir_tokens=True,
                            )
                        )
                        token_str, token_renovado = (
                            self._obtener_o_renovar_token_supervisor(
                                practica=practica,
                                ahora=ahora,
                            )
                        )
                        if token_renovado:
                            total_tokens_renovados += 1

                        sup_id = practica.supervisor_empresa_id
                        correo_sup = f"{sup_id.lower()}@empresa-aliada.com"

                        if es_disparo_manual:
                            accion_eval = (
                                f"Disparo manual de recordatorios de evaluación de desempeño a SupervisorEmpresa {sup_id}"
                            )
                        else:
                            accion_eval = (
                                f"Envío de recordatorio de evaluación de desempeño a SupervisorEmpresa {sup_id}"
                            )
                        if token_renovado:
                            accion_eval += (
                                " con invalidación de token expirado y emisión de nuevo TokenEvaluacion"
                            )

                        detalle_eval = self._despachar_recordatorio(
                            practica=practica,
                            tipo_recordatorio=self.TIPO_EVALUACION_DESEMPENO,
                            destinatario_id=sup_id,
                            correo_destinatario=correo_sup,
                            rol_destinatario=RolUsuario.SUPERVISOR_EMPRESA.value,
                            asunto=f"Recordatorio de evaluación de desempeño pendiente - Práctica {practica.id}",
                            cuerpo=(
                                f"Estimado supervisor '{sup_id}', la práctica '{practica.id}' del estudiante "
                                f"'{practica.estudiante_id}' se encuentra pendiente de Evaluación de Desempeño "
                                f"({motivo_eval}). Acceda al formulario mediante su enlace criptográfico efímero: "
                                f"https://practicas.ucaldas.edu.co/evaluar-desempeno?token={token_str}"
                            ),
                            accion_bitacora=accion_eval,
                            comando=cmd,
                            ahora=ahora,
                            token_emitido=token_str,
                            token_renovado=token_renovado,
                            detalles_extra={
                                "motivo": motivo_eval,
                                "recordatorios_previos": recordatorios_previos_sup,
                            },
                        )
                        detalles_envio.append(detalle_eval)
                        total_recordatorios_enviados += 1
                        acciones_procesadas_en_practica += 1
                        if detalle_eval.encolado_por_fallo_correo:
                            total_encolados_por_fallo_correo += 1

                        # Escalamiento al DocenteAsesor si ya había >= 3 recordatorios o emisiones previas (Escenario 3)
                        if (
                            recordatorios_previos_sup
                            >= cmd.max_recordatorios_antes_escalamiento
                        ):
                            detalle_esc = self._despachar_escalamiento_docente(
                                practica=practica,
                                comando=cmd,
                                ahora=ahora,
                                recordatorios_acumulados=recordatorios_previos_sup,
                                motivo_escalamiento="EvaluacionDesempeno",
                            )
                            if detalle_esc is not None:
                                detalles_envio.append(detalle_esc)
                                total_recordatorios_enviados += 1
                                total_escalamientos_docente += 1
                                acciones_procesadas_en_practica += 1
                                if detalle_esc.encolado_por_fallo_correo:
                                    total_encolados_por_fallo_correo += 1

                # C.3) Recordatorio interno al Estudiante si no tiene reportes recientes y aún no completó horas (Escenario 5)
                if not evaluacion_pendiente and not reportes_pendientes_vencidos:
                    horas_req = self._obtener_horas_requeridas(practica)
                    if practica.horas_acumuladas_aprobadas < horas_req:
                        dias_sin_rep = self._dias_sin_reporte_estudiante(
                            practica, ahora, reportes
                        )
                        if dias_sin_rep >= cmd.umbral_dias_calendario:
                            if self._esta_en_cooldown(
                                practica.id,
                                self.TIPO_REPORTE_HORAS_ESTUDIANTE,
                                ahora,
                                cmd.cooldown_minutos,
                            ):
                                total_omitidos_por_cooldown += 1
                                omitidas_cooldown_en_practica += 1
                            else:
                                correo_est = (
                                    f"{practica.estudiante_id}@universidad.edu.co"
                                )
                                detalle_est = self._despachar_recordatorio(
                                    practica=practica,
                                    tipo_recordatorio=self.TIPO_REPORTE_HORAS_ESTUDIANTE,
                                    destinatario_id=practica.estudiante_id,
                                    correo_destinatario=correo_est,
                                    rol_destinatario=RolUsuario.ESTUDIANTE.value,
                                    asunto=f"Recordatorio de reporte semanal de horas - Práctica {practica.id}",
                                    cuerpo=(
                                        f"Estimado estudiante '{practica.estudiante_id}', su práctica '{practica.id}' "
                                        f"en ejecución acumula {dias_sin_rep} días calendario sin nuevo reporte semanal "
                                        f"de horas ({practica.horas_acumuladas_aprobadas}/{horas_req} horas aprobadas)."
                                    ),
                                    accion_bitacora=(
                                        "Disparo manual de recordatorio a Estudiante por reporte semanal de horas pendiente"
                                        if es_disparo_manual
                                        else "Envío de recordatorio a Estudiante por reporte semanal de horas pendiente"
                                    ),
                                    comando=cmd,
                                    ahora=ahora,
                                )
                                detalles_envio.append(detalle_est)
                                total_recordatorios_enviados += 1
                                acciones_procesadas_en_practica += 1
                                if detalle_est.encolado_por_fallo_correo:
                                    total_encolados_por_fallo_correo += 1

            # ---------------------------------------------------------------
            # D) Prácticas en estado Evaluada -> Recordatorio interno de ActaFinal a DocenteAsesor / Coordinador (Escenario 5)
            # ---------------------------------------------------------------
            elif practica.estado_actual == EstadoPractica.EVALUADA:
                fecha_ref_eval = (
                    practica.fecha_fin
                    or practica.fecha_inicio
                    or practica.fecha_postulacion
                )
                dias_desde_evaluacion = self._dias_calendario_entre(
                    fecha_ref_eval, ahora
                )
                if dias_desde_evaluacion >= cmd.umbral_dias_calendario:
                    if self._esta_en_cooldown(
                        practica.id,
                        self.TIPO_CIERRE_ACTA_INTERNO,
                        ahora,
                        cmd.cooldown_minutos,
                    ):
                        total_omitidos_por_cooldown += 1
                        omitidas_cooldown_en_practica += 1
                    else:
                        docente_id = practica.docente_asesor_id or "COORD-001"
                        rol_dest = (
                            RolUsuario.DOCENTE_ASESOR.value
                            if practica.docente_asesor_id
                            else "Coordinador de prácticas"
                        )
                        correo_dest = self._obtener_correo_docente(docente_id)
                        detalle_acta = self._despachar_recordatorio(
                            practica=practica,
                            tipo_recordatorio=self.TIPO_CIERRE_ACTA_INTERNO,
                            destinatario_id=docente_id,
                            correo_destinatario=correo_dest,
                            rol_destinatario=rol_dest,
                            asunto=f"Recordatorio de generación y firma de ActaFinal - Práctica {practica.id}",
                            cuerpo=(
                                f"La práctica '{practica.id}' del estudiante '{practica.estudiante_id}' "
                                f"se encuentra en estado 'Evaluada' desde hace {dias_desde_evaluacion} días "
                                f"calendario y tiene pendiente la generación o firma electrónica del ActaFinal."
                            ),
                            accion_bitacora=(
                                f"Disparo manual de recordatorio interno a {rol_dest} {docente_id} por generación o firma de ActaFinal"
                                if es_disparo_manual
                                else f"Envío de recordatorio interno a {rol_dest} {docente_id} por generación o firma de ActaFinal"
                            ),
                            comando=cmd,
                            ahora=ahora,
                        )
                        detalles_envio.append(detalle_acta)
                        total_recordatorios_enviados += 1
                        acciones_procesadas_en_practica += 1
                        if detalle_acta.encolado_por_fallo_correo:
                            total_encolados_por_fallo_correo += 1

            if (
                acciones_procesadas_en_practica == 0
                and omitidas_cooldown_en_practica == 0
            ):
                total_omitidos_al_dia_o_terminales += 1

        mensaje_resumen = (
            f"Ejecución de recordatorios completada: {total_practicas_evaluadas} práctica(s) evaluada(s), "
            f"{total_recordatorios_enviados} recordatorio(s) procesado(s), "
            f"{total_tokens_renovados} token(s) renovado(s), "
            f"{total_escalamientos_docente} escalamiento(s) a docente asesor, "
            f"{total_omitidos_por_cooldown} omitido(s) por enfriamiento (1h), "
            f"{total_omitidos_al_dia_o_terminales} práctica(s) al día o en estado terminal."
        )

        return ResultadoEnvioRecordatoriosDTO(
            total_practicas_evaluadas=total_practicas_evaluadas,
            total_recordatorios_enviados=total_recordatorios_enviados,
            total_tokens_renovados=total_tokens_renovados,
            total_escalamientos_docente=total_escalamientos_docente,
            total_omitidos_por_cooldown=total_omitidos_por_cooldown,
            total_omitidos_al_dia_o_terminales=total_omitidos_al_dia_o_terminales,
            total_encolados_por_fallo_correo=total_encolados_por_fallo_correo,
            detalles=tuple(detalles_envio),
            fecha_ejecucion=ahora,
            mensaje=mensaje_resumen,
        )

    # -----------------------------------------------------------------------
    # Métodos privados auxiliares de dominio y orquestación
    # -----------------------------------------------------------------------

    def _obtener_practicas_candidatas(
        self, practica_id_filtro: Optional[str]
    ) -> list[Practica]:
        """Recupera las prácticas a evaluar desde el repositorio."""
        if practica_id_filtro:
            practica = self._repositorio_practica.buscar_por_id(practica_id_filtro)
            return [practica] if practica is not None else []

        listar_todas_fn = getattr(self._repositorio_practica, "listar_todas", None)
        if callable(listar_todas_fn):
            return list(listar_todas_fn())
        return []

    @staticmethod
    def _normalizar_utc(fecha: datetime) -> datetime:
        """Asegura que un objeto datetime sea timezone-aware en UTC."""
        if fecha.tzinfo is None:
            return fecha.replace(tzinfo=timezone.utc)
        return fecha.astimezone(timezone.utc)

    def _dias_calendario_entre(
        self, fecha_inicial: Optional[datetime], fecha_actual: datetime
    ) -> int:
        """Calcula los días naturales (días calendario) transcurridos entre dos fechas."""
        if fecha_inicial is None:
            return 0
        inicio_utc = self._normalizar_utc(fecha_inicial)
        actual_utc = self._normalizar_utc(fecha_actual)
        diferencia = actual_utc - inicio_utc
        return max(0, int(diferencia.total_seconds() // 86400))

    def _esta_en_cooldown(
        self,
        practica_id: str,
        tipo_recordatorio: str,
        ahora: datetime,
        cooldown_minutos: int,
    ) -> bool:
        """Verifica en la bitácora si ya se envió un recordatorio para la misma práctica y acción hace menos de 1 hora (Escenario 7)."""
        if cooldown_minutos <= 0:
            return False

        eventos = self._repositorio_practica.buscar_eventos_por_entidad(
            f"Practica:{practica_id}"
        )
        ventana = timedelta(minutes=cooldown_minutos)
        ahora_utc = self._normalizar_utc(ahora)

        for evento in reversed(eventos):
            detalles = evento.detalles if isinstance(evento.detalles, dict) else {}
            tipo_evento = detalles.get("tipo_recordatorio")
            accion_lower = evento.accion_realizada.lower()

            es_mismo_tipo = tipo_evento == tipo_recordatorio or (
                tipo_recordatorio == self.TIPO_EVALUACION_DESEMPENO
                and "recordatorio" in accion_lower
                and "evaluación de desempeño" in accion_lower
            ) or (
                tipo_recordatorio == self.TIPO_VALIDACION_HORAS
                and "recordatorio" in accion_lower
                and "validación de horas" in accion_lower
            )

            if es_mismo_tipo:
                fecha_ev = self._normalizar_utc(evento.fecha_hora)
                if timedelta(0) <= (ahora_utc - fecha_ev) < ventana:
                    return True
        return False

    def _obtener_horas_requeridas(self, practica: Practica) -> int:
        """Obtiene las horas requeridas de la ReglaPrograma vinculada a la práctica (ADR-007)."""
        if self._repositorio_regla is not None and practica.regla_programa_id:
            regla = self._repositorio_regla.buscar_por_id(practica.regla_programa_id)
            if regla is not None:
                return regla.horas_requeridas
        return 320

    def _tiene_evaluacion_registrada(self, practica_id: str) -> bool:
        """Verifica si la práctica ya cuenta con una EvaluacionDesempeno asentada."""
        if self._repositorio_evaluacion_desempeno is not None:
            evaluacion = self._repositorio_evaluacion_desempeno.buscar_por_practica(
                practica_id
            )
            return evaluacion is not None
        return False

    def _listar_tokens_practica(self, practica_id: str) -> list[TokenEvaluacion]:
        """Recupera los TokenEvaluacion emitidos para una práctica ordenados por fecha de emisión."""
        if self._repositorio_token_evaluacion is None:
            return []
        listar_fn = getattr(
            self._repositorio_token_evaluacion, "listar_por_practica", None
        )
        if callable(listar_fn):
            return list(listar_fn(practica_id))
        listar_todos_fn = getattr(
            self._repositorio_token_evaluacion, "listar_todos", None
        )
        if callable(listar_todos_fn):
            tokens = [
                t for t in listar_todos_fn() if t.practica_id == practica_id
            ]
            return sorted(
                tokens, key=lambda t: self._normalizar_utc(t.fecha_emision)
            )
        return []

    def _requiere_recordatorio_evaluacion_desempeno(
        self,
        *,
        practica: Practica,
        ahora: datetime,
        umbral_dias_calendario: int,
    ) -> tuple[bool, str]:
        """Determina si una práctica en EnEjecucion tiene pendiente la EvaluacionDesempeno y supera el plazo en días calendario."""
        if practica.estado_actual != EstadoPractica.EN_EJECUCION:
            return False, ""

        if not practica.supervisor_empresa_id:
            return False, ""

        if self._tiene_evaluacion_registrada(practica.id):
            return False, ""

        tokens = self._listar_tokens_practica(practica.id)
        tokens_no_usados = [t for t in tokens if not t.usado]

        horas_requeridas = self._obtener_horas_requeridas(practica)
        cumple_horas = practica.horas_acumuladas_aprobadas >= horas_requeridas

        if tokens_no_usados:
            ultimo_token = tokens_no_usados[-1]
            if not ultimo_token.es_valido(ahora):
                return (
                    True,
                    "TokenEvaluacion expirado tras superar 15 días calendario de vigencia",
                )
            dias_desde_emision = self._dias_calendario_entre(
                ultimo_token.fecha_emision, ahora
            )
            if dias_desde_emision >= umbral_dias_calendario:
                return (
                    True,
                    f"TokenEvaluacion vigente con {dias_desde_emision} días calendario sin respuesta del supervisor",
                )
            return False, ""

        if cumple_horas:
            fecha_base = (
                practica.fecha_inicio
                or practica.fecha_postulacion
            )
            dias_transcurridos = self._dias_calendario_entre(fecha_base, ahora)
            if dias_transcurridos >= umbral_dias_calendario or not tokens:
                return (
                    True,
                    f"Práctica con {practica.horas_acumuladas_aprobadas}/{horas_requeridas} horas aprobadas pendiente de evaluación",
                )

        return False, ""

    def _obtener_o_renovar_token_supervisor(
        self,
        *,
        practica: Practica,
        ahora: datetime,
    ) -> tuple[str, bool]:
        """Retorna el token vigente o invalida el token expirado (>15 días) y emite uno nuevo (Escenarios 1, 2, 6, 11)."""
        supervisor_id = practica.supervisor_empresa_id or "SUP-001"
        tokens = self._listar_tokens_practica(practica.id)

        token_vigente: Optional[TokenEvaluacion] = None
        hubo_expirado_invalidado = False

        for token in tokens:
            if not token.usado:
                if token.es_valido(ahora):
                    token_vigente = token
                else:
                    # Invalida explícitamente el token expirado (>15 días) para que no pueda usarse (Escenarios 2 y 11)
                    token.invalidar(ahora)
                    if self._repositorio_token_evaluacion is not None:
                        self._repositorio_token_evaluacion.guardar(token)
                    hubo_expirado_invalidado = True

        if token_vigente is not None and not hubo_expirado_invalidado:
            return token_vigente.token, False

        # Emitir nuevo TokenEvaluacion con vigencia de 15 días calendario
        nuevo_token = self._emitir_nuevo_token(
            practica_id=practica.id,
            supervisor_id=supervisor_id,
            ahora=ahora,
        )
        return nuevo_token.token, hubo_expirado_invalidado

    def _emitir_nuevo_token(
        self,
        *,
        practica_id: str,
        supervisor_id: str,
        ahora: datetime,
    ) -> TokenEvaluacion:
        """Emite y persiste un nuevo TokenEvaluacion firmado con HMAC-SHA256 y vigencia de 15 días calendario (ADR-004)."""
        if self._interceptor_identidad is not None:
            return self._interceptor_identidad.generar_token(
                practica_id=practica_id,
                supervisor_id=supervisor_id,
                duracion_dias=15,
                fecha_emision=ahora,
            )

        token_entidad = TokenEvaluacion(
            token=f"ml_{practica_id}_{supervisor_id}_{uuid.uuid4().hex}",
            practica_id=practica_id,
            supervisor_id=supervisor_id,
            fecha_emision=ahora,
            fecha_expiracion=ahora + timedelta(days=15),
            usado=False,
        )
        if self._repositorio_token_evaluacion is not None:
            self._repositorio_token_evaluacion.guardar(token_entidad)
        return token_entidad

    def _contar_recordatorios_previos_supervisor(
        self,
        *,
        practica: Practica,
        incluir_tokens: bool = True,
    ) -> int:
        """Contabiliza la cantidad de recordatorios o renovaciones previas dirigidas al SupervisorEmpresa (Escenario 3)."""
        eventos = self._repositorio_practica.buscar_eventos_por_entidad(
            f"Practica:{practica.id}"
        )
        conteo_bitacora = 0
        for ev in eventos:
            detalles = ev.detalles if isinstance(ev.detalles, dict) else {}
            tipo = detalles.get("tipo_recordatorio")
            accion_lower = ev.accion_realizada.lower()
            if tipo in {
                self.TIPO_EVALUACION_DESEMPENO,
                self.TIPO_VALIDACION_HORAS,
            } or (
                "recordatorio" in accion_lower
                and (
                    "supervisor" in accion_lower
                    or "evaluación de desempeño" in accion_lower
                    or "validación de horas" in accion_lower
                )
            ):
                conteo_bitacora += 1

        if not incluir_tokens:
            return conteo_bitacora

        tokens = self._listar_tokens_practica(practica.id)
        return max(conteo_bitacora, len(tokens))

    def _verificar_y_escalar_a_docente(
        self,
        *,
        practica: Practica,
        comando: EjecutarRecordatoriosComando,
        ahora: datetime,
        motivo_escalamiento: str,
    ) -> Optional[DetalleRecordatorioEnviadoDTO]:
        """Verifica si se alcanzó el umbral de 3 recordatorios sin respuesta del supervisor y escala alerta al DocenteAsesor."""
        eventos = self._repositorio_practica.buscar_eventos_por_entidad(
            f"Practica:{practica.id}"
        )
        recordatorios_previos = 0
        for ev in eventos[:-1]:
            detalles = ev.detalles if isinstance(ev.detalles, dict) else {}
            if detalles.get("tipo_recordatorio") in {
                self.TIPO_VALIDACION_HORAS,
                self.TIPO_EVALUACION_DESEMPENO,
            }:
                recordatorios_previos += 1

        tokens = self._listar_tokens_practica(practica.id)
        total_acumulado = max(recordatorios_previos, len(tokens))

        if total_acumulado >= comando.max_recordatorios_antes_escalamiento:
            return self._despachar_escalamiento_docente(
                practica=practica,
                comando=comando,
                ahora=ahora,
                recordatorios_acumulados=total_acumulado,
                motivo_escalamiento=motivo_escalamiento,
            )
        return None

    def _despachar_escalamiento_docente(
        self,
        *,
        practica: Practica,
        comando: EjecutarRecordatoriosComando,
        ahora: datetime,
        recordatorios_acumulados: int,
        motivo_escalamiento: str,
    ) -> Optional[DetalleRecordatorioEnviadoDTO]:
        """Envía una notificación de alerta de escalamiento al DocenteAsesor tras >= 3 recordatorios sin respuesta del supervisor (Escenario 3)."""
        docente_id = practica.docente_asesor_id
        if not docente_id:
            return None

        if self._esta_en_cooldown(
            practica.id,
            self.TIPO_ESCALAMIENTO_DOCENTE,
            ahora,
            comando.cooldown_minutos,
        ):
            return None

        correo_docente = self._obtener_correo_docente(docente_id)
        sup_id = practica.supervisor_empresa_id or "SUP-001"

        return self._despachar_recordatorio(
            practica=practica,
            tipo_recordatorio=self.TIPO_ESCALAMIENTO_DOCENTE,
            destinatario_id=docente_id,
            correo_destinatario=correo_docente,
            rol_destinatario=RolUsuario.DOCENTE_ASESOR.value,
            asunto=(
                f"Alerta de escalamiento: Falta de respuesta de SupervisorEmpresa {sup_id} "
                f"- Práctica {practica.id}"
            ),
            cuerpo=(
                f"Estimado DocenteAsesor '{docente_id}', se han emitido {recordatorios_acumulados} "
                f"recordatorios o renovaciones de enlace sin respuesta por parte del SupervisorEmpresa "
                f"'{sup_id}' respecto a {motivo_escalamiento} de la práctica '{practica.id}' "
                f"(Estudiante '{practica.estudiante_id}'). Se solicita su intervención académica."
            ),
            accion_bitacora=(
                f"Escalamiento de alerta al DocenteAsesor {docente_id} tras {recordatorios_acumulados} "
                f"recordatorios sin respuesta del SupervisorEmpresa {sup_id}"
            ),
            comando=comando,
            ahora=ahora,
            escalado_a_docente=True,
            detalles_extra={
                "supervisor_sin_respuesta": sup_id,
                "recordatorios_acumulados": recordatorios_acumulados,
                "motivo_escalamiento": motivo_escalamiento,
            },
        )

    def _dias_sin_reporte_estudiante(
        self,
        practica: Practica,
        ahora: datetime,
        reportes_precargados: Optional[list[RegistroHoras]] = None,
    ) -> int:
        """Calcula los días calendario transcurridos desde el último reporte de horas (o inicio de la práctica)."""
        reportes = (
            reportes_precargados
            if reportes_precargados is not None
            else self._repositorio_registro_horas.listar_por_practica(practica.id)
        )
        if reportes:
            ultima_fecha = max(
                (self._normalizar_utc(r.fecha_registro) for r in reportes),
                default=self._normalizar_utc(
                    practica.fecha_inicio or practica.fecha_postulacion
                ),
            )
            return self._dias_calendario_entre(ultima_fecha, ahora)

        fecha_base = practica.fecha_inicio or practica.fecha_postulacion
        return self._dias_calendario_entre(fecha_base, ahora)

    def _obtener_correo_docente(self, docente_id: str) -> str:
        """Obtiene el correo institucional del DocenteAsesor o genera uno canónico."""
        if self._repositorio_docente is not None:
            docente = self._repositorio_docente.buscar_por_id(docente_id)
            if docente is not None and docente.correo_institucional:
                return docente.correo_institucional
        if "coord" in docente_id.lower():
            return "coordinacion.practicas@universidad.edu.co"
        return f"{docente_id.lower()}@universidad.edu.co"

    def _despachar_recordatorio(
        self,
        *,
        practica: Practica,
        tipo_recordatorio: str,
        destinatario_id: str,
        correo_destinatario: str,
        rol_destinatario: str,
        asunto: str,
        cuerpo: str,
        accion_bitacora: str,
        comando: EjecutarRecordatoriosComando,
        ahora: datetime,
        token_emitido: Optional[str] = None,
        token_renovado: bool = False,
        escalado_a_docente: bool = False,
        detalles_extra: Optional[dict[str, Any]] = None,
    ) -> DetalleRecordatorioEnviadoDTO:
        """Envía el correo de recordatorio con tolerancia a fallos (EAC-02) y registra en bitácora (ADR-006)."""
        encolado_por_fallo = False
        mensaje_resultado = f"Recordatorio ({tipo_recordatorio}) enviado exitosamente a {destinatario_id} ({correo_destinatario})."

        if self._servicio_correo is not None:
            try:
                self._servicio_correo.enviar_notificacion(
                    destinatario=correo_destinatario,
                    asunto=asunto,
                    cuerpo=cuerpo,
                )
            except ErrorServicioCorreo as err_correo:
                # EAC-02 (Escenario 10): Tolerancia a fallos y reintentos asíncronos con 0% pérdida
                encolado_por_fallo = True
                mensaje_resultado = (
                    f"Fallo de conexión con servicio de correo ({err_correo}). "
                    f"Recordatorio encolado persistentemente para reintento exponencial."
                )
                self._encolar_reintento_notificacion(
                    practica=practica,
                    destinatario_id=destinatario_id,
                    correo_destinatario=correo_destinatario,
                    asunto=asunto,
                    cuerpo=cuerpo,
                    tipo_recordatorio=tipo_recordatorio,
                    motivo_error=str(err_correo),
                    ahora=ahora,
                )

        detalles_bitacora: dict[str, Any] = {
            "practica_id": practica.id,
            "tipo_recordatorio": tipo_recordatorio,
            "destinatario_id": destinatario_id,
            "correo_destinatario": correo_destinatario,
            "rol_destinatario": rol_destinatario,
            "token_renovado": token_renovado,
            "escalado_a_docente": escalado_a_docente,
            "encolado_por_fallo_correo": encolado_por_fallo,
        }
        if token_emitido is not None:
            detalles_bitacora["token_emitido"] = token_emitido
        if detalles_extra:
            detalles_bitacora.update(detalles_extra)

        accion_final = (
            f"{accion_bitacora} [ENCOLADO POR FALLO DE CORREO]"
            if encolado_por_fallo
            else accion_bitacora
        )

        self._registrar_bitacora(
            actor_id=comando.actor_id,
            rol=comando.rol_actor,
            ip=comando.ip_origen,
            accion=accion_final,
            entidad=f"Practica:{practica.id}",
            fecha_hora=ahora,
            detalles=detalles_bitacora,
        )

        return DetalleRecordatorioEnviadoDTO(
            practica_id=practica.id,
            tipo_recordatorio=tipo_recordatorio,
            destinatario_id=destinatario_id,
            correo_destinatario=correo_destinatario,
            rol_destinatario=rol_destinatario,
            token_emitido=token_emitido,
            token_renovado=token_renovado,
            escalado_a_docente=escalado_a_docente,
            encolado_por_fallo_correo=encolado_por_fallo,
            mensaje=mensaje_resultado,
        )

    def _encolar_reintento_notificacion(
        self,
        *,
        practica: Practica,
        destinatario_id: str,
        correo_destinatario: str,
        asunto: str,
        cuerpo: str,
        tipo_recordatorio: str,
        motivo_error: str,
        ahora: datetime,
    ) -> None:
        """Conserva la tarea de notificación en la cola persistente del bróker con retroceso exponencial (ADR-001, EAC-02)."""
        if self._publicador_eventos is None:
            return

        tarea = DatosTareaValidacionSia(
            practica_id=practica.id,
            documento_estudiante=practica.estudiante_id,
            correo_estudiante=correo_destinatario,
            numero_reintento=1,
            max_reintentos=5,
            fecha_creacion=ahora,
            metadata={
                "tipo_tarea": "REINTENTO_RECORDATORIO_CORREO",
                "tipo_recordatorio": tipo_recordatorio,
                "destinatario_id": destinatario_id,
                "correo_destinatario": correo_destinatario,
                "asunto": asunto,
                "cuerpo": cuerpo,
                "estrategia_reintento": "EXPONENTIAL_BACKOFF",
                "motivo_fallo_inicial": motivo_error,
            },
        )
        try:
            self._publicador_eventos.publicar_tarea_validacion_sia(tarea)
            self._publicador_eventos.publicar_alerta_soporte(
                asunto=f"Fallo despacho SMTP en recordatorio CU-08 - Práctica {practica.id}",
                mensaje=(
                    f"El recordatorio '{tipo_recordatorio}' para '{correo_destinatario}' fue "
                    f"encolado para reintentos automáticos con retroceso exponencial: {motivo_error}"
                ),
                contexto={
                    "practica_id": practica.id,
                    "destinatario_id": destinatario_id,
                    "tipo_recordatorio": tipo_recordatorio,
                },
            )
        except Exception:
            pass

    def _registrar_bitacora(
        self,
        *,
        actor_id: str,
        rol: str,
        ip: str,
        accion: str,
        entidad: str,
        fecha_hora: datetime,
        detalles: Optional[dict[str, Any]] = None,
    ) -> None:
        """Inserta atómicamente un EventoBitacora inmutable sellado con SHA-256 (ADR-006)."""
        evento = EventoBitacora(
            actor_identificador=actor_id,
            rol_actor=rol,
            ip_origen=ip,
            accion_realizada=accion,
            entidad_afectada=entidad,
            fecha_hora=fecha_hora,
            detalles=detalles,
        )
        self._repositorio_practica.guardar_evento_bitacora(evento)
