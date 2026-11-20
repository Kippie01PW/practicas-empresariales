"""Caso de uso: Consultar estado del trámite (CU-11).

Traza: CU-11, OB-04, EAC-01, EAC-03, RT-01, RN-01, RN-02, RN-03,
ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores),
ADR-003 (Persistencia transaccional),
ADR-004 (Autenticación híbrida),
ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso),
ADR-006 (Bitácora de auditoría transaccional Append-Only),
ADR-007 (Configuración declarativa de reglas versionadas por programa),
ADR-008 (Generación y preservación del acta final con sellado criptográfico SHA-256),
ADR-010 (Máquina de estados finitos),
Vista Lógica §2 (01-logica.md) y Vista de Desarrollo §3 (03-desarrollo.md).

Implementa la consulta en modo de autoservicio y estrictamente de solo lectura
del estado actual del trámite de práctica empresarial más reciente o activo de un
estudiante titular:
1. Autorización RBAC centralizada bajo política *deny-by-default* (ADR-004, ADR-005):
   - Operación exclusiva para el rol `Estudiante` (`RolUsuario.ESTUDIANTE`).
   - Cualquier intento de invocación por roles distintos (`DocenteAsesor`, `Coordinador de prácticas`,
     `SupervisorEmpresa`, `SISTEMA` o usuarios sin sesión válida) es rechazado de inmediato con
     0 datos expuestos y registro de un único `EventoBitacora` (Escenarios 10 y 11, EAC-03).
2. Validación estricta de pertenencia contextual de datos (*Context-Based Access Control*, RN-01):
   - El estudiante autenticado únicamente puede consultar el estado del trámite de su propia
     `Practica` (`practica.estudiante_id == contexto.usuario_id`).
   - Si especifica un `practica_id` ajeno o un `estudiante_id` distinto al suyo, se deniega
     la operación con 0 datos expuestos y se registra un único `EventoBitacora` de intento
     de acceso a recurso ajeno (Escenario 9, EAC-03).
   - Si no especifica `practica_id`, se selecciona automáticamente su práctica activa en curso
     o, en su defecto, la más reciente por `fechaPostulacion` (Escenario 7). Si aún no registra
     ninguna postulación o práctica, lanza `PracticaNoEncontradaError` (Escenario 8).
3. Proyección de datos en modo solo lectura (ADR-007, ADR-008, ADR-010):
   - Calcula el progreso frente a las `horasRequeridas` inmutables de la versión de `ReglaPrograma`
     vinculada a la práctica al momento de su postulación (Escenario 12, EAC-01).
   - Expone los datos institucionales del `DocenteAsesor` asignado, el `SupervisorEmpresa`,
     el avance de horas aprobadas y pendientes, y la causal o justificación en caso de rechazo
     (Escenarios 1, 2, 3 y 6).
   - Visibilidad contextual de la `EvaluacionDesempeno`: mientras la `Practica` no haya alcanzado
     el estado `Completada` (ej. en estado `Evaluada`), únicamente informa que la evaluación ya fue
     realizada junto con su `fechaEvaluacion`, ocultando `calificacionCuantitativa`,
     `respuestasRubrica` y `observaciones` (Escenario 4). Una vez la práctica alcanza el estado
     `Completada` con su `ActaFinal` en firme, expone la calificación cuantitativa, observaciones,
     rúbrica y los metadatos de descarga y hash SHA-256 del PDF oficial del acta (Escenario 5).
4. Trazabilidad en bitácora Append-Only (ADR-006):
   - Registra un único `EventoBitacora` inmutable por cada consulta exitosa o intento rechazado.
"""

from __future__ import annotations

from typing import Any, Optional

from aplicacion.dtos.estado_tramite_dto import (
    ConsultarEstadoTramiteComando,
    EstadoTramitePracticaRespuestaDTO,
    ResumenActaTramiteDTO,
    ResumenEvaluacionTramiteDTO,
)
from aplicacion.puertos.repositorio_acta_final import RepositorioActaFinalPort
from aplicacion.puertos.repositorio_docente import RepositorioDocentePort
from aplicacion.puertos.repositorio_evaluacion_desempeno import (
    RepositorioEvaluacionDesempenoPort,
)
from aplicacion.puertos.repositorio_practica import RepositorioPracticaPort
from aplicacion.puertos.repositorio_registro_horas import RepositorioRegistroHorasPort
from aplicacion.puertos.repositorio_regla import RepositorioReglaProgramaPort
from aplicacion.seguridad.autorizador_rbac import (
    AccesoDenegadoError,
    AutorizadorRBAC,
    ContextoUsuario,
)
from dominio.errores import PracticaNoEncontradaError
from dominio.modelos.acta_final import ActaFinal
from dominio.modelos.docente_asesor import DocenteAsesor
from dominio.modelos.evaluacion_desempeno import EvaluacionDesempeno
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.intento_validacion import IntentoValidacion
from dominio.modelos.practica import EstadoPractica, Practica
from dominio.modelos.registro_horas import EstadoValidacionHoras, RegistroHoras
from dominio.modelos.regla_programa import ReglaPrograma


class ConsultarEstadoTramiteCasoUso:
    """Caso de uso del Módulo Postulaciones para consultar el estado del trámite en autoservicio (CU-11)."""

    def __init__(
        self,
        *,
        repositorio_practica: RepositorioPracticaPort,
        repositorio_regla: RepositorioReglaProgramaPort,
        repositorio_docente: Optional[RepositorioDocentePort] = None,
        repositorio_registro_horas: Optional[RepositorioRegistroHorasPort] = None,
        repositorio_evaluacion: Optional[RepositorioEvaluacionDesempenoPort] = None,
        repositorio_acta_final: Optional[RepositorioActaFinalPort] = None,
        autorizador_rbac: Optional[AutorizadorRBAC] = None,
    ) -> None:
        """Inicializa el caso de uso con sus puertos de lectura y autorizador RBAC inyectados.

        Args:
            repositorio_practica: Puerto de persistencia de prácticas, intentos SIA y bitácora Append-Only.
            repositorio_regla: Puerto de consulta de reglas normativas versionadas por programa.
            repositorio_docente: Puerto opcional de consulta de docentes asesores asignados.
            repositorio_registro_horas: Puerto opcional de consulta de reportes semanales de horas.
            repositorio_evaluacion: Puerto opcional de consulta de evaluaciones de desempeño.
            repositorio_acta_final: Puerto opcional de consulta de actas finales y firmas electrónicas.
            autorizador_rbac: Componente centralizado de autorización RBAC (deny-by-default).
        """
        self._repositorio_practica: RepositorioPracticaPort = repositorio_practica
        self._repositorio_regla: RepositorioReglaProgramaPort = repositorio_regla
        self._repositorio_docente: Optional[RepositorioDocentePort] = repositorio_docente
        self._repositorio_registro_horas: Optional[RepositorioRegistroHorasPort] = (
            repositorio_registro_horas
        )
        self._repositorio_evaluacion: Optional[RepositorioEvaluacionDesempenoPort] = (
            repositorio_evaluacion
        )
        self._repositorio_acta_final: Optional[RepositorioActaFinalPort] = (
            repositorio_acta_final
        )
        self._autorizador_rbac: AutorizadorRBAC = autorizador_rbac or AutorizadorRBAC()

    def __call__(
        self,
        comando: ConsultarEstadoTramiteComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> EstadoTramitePracticaRespuestaDTO:
        """Permite invocar la instancia del caso de uso como un objeto callable."""
        return self.ejecutar(comando=comando, contexto=contexto)

    def ejecutar(
        self,
        comando: ConsultarEstadoTramiteComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> EstadoTramitePracticaRespuestaDTO:
        """Consulta en modo solo lectura el estado del trámite de la práctica activa o más reciente.

        Args:
            comando: DTO inmutable `ConsultarEstadoTramiteComando` con las credenciales del actor
                y el identificador opcional de la práctica o estudiante.
            contexto: Contexto opcional de sesión institucional `ContextoUsuario`.

        Returns:
            `EstadoTramitePracticaRespuestaDTO` con la proyección completa de solo lectura del trámite.

        Raises:
            AccesoDenegadoError: Si el actor no tiene sesión válida, posee un rol distinto a
                `Estudiante` (Escenarios 10 y 11) o intenta consultar una práctica ajena (Escenario 9).
            PracticaNoEncontradaError: Si el estudiante aún no registra ninguna postulación o práctica
                en el sistema (Escenario 8) o el `practica_id` consultado no existe.
        """
        actor_id_raw = (
            contexto.usuario_id
            if contexto is not None
            else (comando.actor_id if comando.actor_id is not None else "")
        )
        rol_actor_raw = (
            contexto.rol
            if contexto is not None
            else (comando.rol_actor if comando.rol_actor is not None else "")
        )
        ip_origen = (
            contexto.ip_origen
            if contexto is not None and contexto.ip_origen
            else (comando.ip_origen or "127.0.0.1")
        )
        entidad_referencia = (
            f"Practica:{comando.practica_id.strip()}"
            if comando.practica_id and str(comando.practica_id).strip()
            else (
                f"Estudiante:{comando.estudiante_id.strip()}"
                if comando.estudiante_id and str(comando.estudiante_id).strip()
                else (
                    f"Estudiante:{str(actor_id_raw).strip()}"
                    if actor_id_raw and str(actor_id_raw).strip()
                    else "ModuloPostulaciones"
                )
            )
        )

        # -------------------------------------------------------------------
        # 1. Verificación de rol exclusivo Estudiante (deny-by-default, ADR-004, ADR-005, EAC-03)
        # -------------------------------------------------------------------
        try:
            if not actor_id_raw or not str(actor_id_raw).strip():
                raise AccesoDenegadoError(
                    "Acceso denegado: No se ha provisto una sesión o identificador de usuario institucional válido.",
                    rol_actor=rol_actor_raw,
                    operacion="consultar_estado_tramite",
                    usuario_id=actor_id_raw,
                )

            self._autorizador_rbac.validar_consulta_estado_tramite(
                rol_actor=rol_actor_raw,
                usuario_id=str(actor_id_raw).strip(),
                operacion="consultar_estado_tramite",
            )
            contexto_efectivo = contexto or ContextoUsuario(
                usuario_id=str(actor_id_raw).strip(),
                rol=str(rol_actor_raw).strip(),
                ip_origen=str(ip_origen).strip() or "127.0.0.1",
            )
        except (AccesoDenegadoError, ValueError) as error_auth:
            error_denegado = (
                error_auth
                if isinstance(error_auth, AccesoDenegadoError)
                else AccesoDenegadoError(
                    str(error_auth),
                    rol_actor=rol_actor_raw,
                    operacion="consultar_estado_tramite",
                    usuario_id=actor_id_raw,
                )
            )
            self._registrar_bitacora(
                actor_id=(
                    str(actor_id_raw).strip()
                    if actor_id_raw and str(actor_id_raw).strip()
                    else "ANONIMO"
                ),
                rol=(
                    str(rol_actor_raw).strip()
                    if rol_actor_raw and str(rol_actor_raw).strip()
                    else "SIN_ROL"
                ),
                ip=(
                    str(ip_origen).strip()
                    if ip_origen and str(ip_origen).strip()
                    else "127.0.0.1"
                ),
                accion="ACCESO_DENEGADO_ROL_NO_AUTORIZADO_ESTADO_TRAMITE",
                entidad=entidad_referencia,
                detalles={
                    "operacion": "consultar_estado_tramite",
                    "practica_id": comando.practica_id,
                    "estudiante_id": comando.estudiante_id,
                    "motivo": str(error_denegado),
                },
            )
            raise error_denegado

        # -------------------------------------------------------------------
        # 2. Validación de pertenencia contextual y resolución de la Práctica (RN-01, ADR-005)
        # -------------------------------------------------------------------
        practica: Optional[Practica] = None

        if comando.practica_id and str(comando.practica_id).strip():
            practica_id_limpio = str(comando.practica_id).strip()
            practica = self._repositorio_practica.buscar_por_id(practica_id_limpio)
            if practica is None:
                raise PracticaNoEncontradaError(practica_id=practica_id_limpio)

            try:
                self._autorizador_rbac.validar_pertenencia_estudiante(
                    contexto=contexto_efectivo,
                    estudiante=practica.estudiante_id,
                    operacion="consultar_estado_tramite",
                )
                if comando.estudiante_id and str(comando.estudiante_id).strip():
                    self._autorizador_rbac.validar_pertenencia_estudiante(
                        contexto=contexto_efectivo,
                        estudiante=str(comando.estudiante_id).strip(),
                        operacion="consultar_estado_tramite",
                    )
            except AccesoDenegadoError as error_pertenencia:
                self._registrar_bitacora(
                    actor_id=contexto_efectivo.usuario_id,
                    rol=contexto_efectivo.rol,
                    ip=contexto_efectivo.ip_origen,
                    accion="ACCESO_DENEGADO_RECURSO_AJENO_ESTADO_TRAMITE",
                    entidad=f"Practica:{practica.id}",
                    detalles={
                        "operacion": "consultar_estado_tramite",
                        "practica_id": practica.id,
                        "motivo": str(error_pertenencia),
                    },
                )
                raise error_pertenencia
        else:
            if comando.estudiante_id and str(comando.estudiante_id).strip():
                estudiante_objetivo = str(comando.estudiante_id).strip()
                try:
                    self._autorizador_rbac.validar_pertenencia_estudiante(
                        contexto=contexto_efectivo,
                        estudiante=estudiante_objetivo,
                        operacion="consultar_estado_tramite",
                    )
                except AccesoDenegadoError as error_pertenencia:
                    practica_ajena = (
                        self._repositorio_practica.buscar_mas_reciente_o_activa_por_estudiante(
                            estudiante_objetivo
                        )
                    )
                    entidad_ajena = (
                        f"Practica:{practica_ajena.id}"
                        if practica_ajena is not None
                        else f"Estudiante:{estudiante_objetivo}"
                    )
                    self._registrar_bitacora(
                        actor_id=contexto_efectivo.usuario_id,
                        rol=contexto_efectivo.rol,
                        ip=contexto_efectivo.ip_origen,
                        accion="ACCESO_DENEGADO_RECURSO_AJENO_ESTADO_TRAMITE",
                        entidad=entidad_ajena,
                        detalles={
                            "operacion": "consultar_estado_tramite",
                            "estudiante_objetivo": estudiante_objetivo,
                            "motivo": str(error_pertenencia),
                        },
                    )
                    raise error_pertenencia

            practica = (
                self._repositorio_practica.buscar_mas_reciente_o_activa_por_estudiante(
                    contexto_efectivo.usuario_id
                )
            )
            if practica is None:
                raise PracticaNoEncontradaError(
                    practica_id=contexto_efectivo.usuario_id,
                    mensaje=(
                        f"El estudiante '{contexto_efectivo.usuario_id}' aún no cuenta con ninguna "
                        f"postulación o práctica registrada en el sistema."
                    ),
                )

        # -------------------------------------------------------------------
        # 3. Proyección de datos en modo solo lectura (ADR-007, ADR-008, ADR-010)
        # -------------------------------------------------------------------
        # 3.1. ReglaPrograma versionada vinculada a la práctica (EAC-01)
        regla: Optional[ReglaPrograma] = self._repositorio_regla.buscar_por_id(
            practica.regla_programa_id
        )
        horas_requeridas: int = regla.horas_requeridas if regla is not None else 320
        version_regla: str = str(regla.version) if regla is not None else "1"

        # 3.2. DocenteAsesor asignado (si existe)
        nombre_docente: Optional[str] = None
        correo_docente: Optional[str] = None
        if practica.docente_asesor_id and self._repositorio_docente is not None:
            docente: Optional[DocenteAsesor] = self._repositorio_docente.buscar_por_id(
                practica.docente_asesor_id
            )
            if docente is not None:
                nombre_docente = docente.nombre_completo
                correo_docente = docente.correo_institucional

        # 3.3. Progreso de horas y reportes pendientes de validación
        horas_acumuladas_aprobadas: int = practica.horas_acumuladas_aprobadas
        horas_pendientes_validacion: int = 0
        cantidad_reportes_pendientes: int = 0
        if self._repositorio_registro_horas is not None:
            registros: list[RegistroHoras] = (
                self._repositorio_registro_horas.listar_por_practica(practica.id)
            )
            for registro in registros:
                if registro.estado_validacion == EstadoValidacionHoras.PENDIENTE:
                    horas_pendientes_validacion += registro.cantidad_horas
                    cantidad_reportes_pendientes += 1

        horas_restantes: int = max(0, horas_requeridas - horas_acumuladas_aprobadas)
        porcentaje_avance_horas: float = (
            round((horas_acumuladas_aprobadas / horas_requeridas) * 100.0, 2)
            if horas_requeridas > 0
            else 0.0
        )
        requisito_horas_cumplido: bool = horas_acumuladas_aprobadas >= horas_requeridas

        # 3.4. Causal académica o justificación administrativa en caso de rechazo (Escenario 6)
        motivo_rechazo: Optional[str] = practica.motivo_rechazo
        if (
            practica.estado_actual == EstadoPractica.RECHAZADA
            and not motivo_rechazo
        ):
            intentos: list[IntentoValidacion] = (
                self._repositorio_practica.buscar_intentos_por_practica(practica.id)
            )
            if intentos:
                ultimo_intento = intentos[-1]
                motivo_rechazo = (
                    ultimo_intento.detalle_estado or ultimo_intento.resultado_sia
                )

        # 3.5. Visibilidad contextual de la Evaluación de Desempeño (Escenarios 4 y 5)
        evaluacion_entidad: Optional[EvaluacionDesempeno] = None
        if self._repositorio_evaluacion is not None:
            evaluacion_entidad = self._repositorio_evaluacion.buscar_por_practica(
                practica.id
            )

        es_completada: bool = practica.estado_actual == EstadoPractica.COMPLETADA
        if evaluacion_entidad is None:
            resumen_evaluacion = ResumenEvaluacionTramiteDTO(
                evaluacion_realizada=False,
                fecha_evaluacion=None,
                calificacion_visible=False,
                calificacion_cuantitativa=None,
                es_aprobatoria=None,
                observaciones=None,
                respuestas_rubrica=None,
            )
        elif not es_completada:
            # Escenario 4: En estado Evaluada (o previo a Completada), solo se informa que
            # la evaluación ya fue realizada junto con su fecha, ocultando calificación y observaciones.
            resumen_evaluacion = ResumenEvaluacionTramiteDTO(
                evaluacion_realizada=True,
                fecha_evaluacion=evaluacion_entidad.fecha_evaluacion,
                calificacion_visible=False,
                calificacion_cuantitativa=None,
                es_aprobatoria=None,
                observaciones=None,
                respuestas_rubrica=None,
            )
        else:
            # Escenario 5: En estado Completada, la evaluación es completamente visible.
            resumen_evaluacion = ResumenEvaluacionTramiteDTO(
                evaluacion_realizada=True,
                fecha_evaluacion=evaluacion_entidad.fecha_evaluacion,
                calificacion_visible=True,
                calificacion_cuantitativa=evaluacion_entidad.calificacion_cuantitativa,
                es_aprobatoria=evaluacion_entidad.es_aprobatoria,
                observaciones=evaluacion_entidad.observaciones,
                respuestas_rubrica=evaluacion_entidad.respuestas_rubrica,
            )

        # 3.6. Resumen de firmas electrónicas y metadatos del ActaFinal (Escenarios 4 y 5)
        acta_entidad: Optional[ActaFinal] = None
        if self._repositorio_acta_final is not None:
            acta_entidad = self._repositorio_acta_final.buscar_por_practica(practica.id)

        if acta_entidad is None:
            resumen_acta = ResumenActaTramiteDTO(
                acta_generada=False,
                aprobada_por_docente=False,
                aprobada_por_coordinador=False,
                acta_en_firme=False,
                descarga_habilitada=False,
                numero_acta=None,
                fecha_emision=None,
                ruta_archivo_pdf=None,
                hash_integridad_sha256=None,
            )
        elif es_completada and acta_entidad.esta_en_firme:
            # Escenario 5: Práctica completada con acta final en firme y descarga habilitada.
            resumen_acta = ResumenActaTramiteDTO(
                acta_generada=True,
                aprobada_por_docente=acta_entidad.aprobada_por_docente,
                aprobada_por_coordinador=acta_entidad.aprobada_por_coordinador,
                acta_en_firme=True,
                descarga_habilitada=True,
                numero_acta=acta_entidad.numero_acta,
                fecha_emision=acta_entidad.fecha_emision,
                ruta_archivo_pdf=acta_entidad.ruta_archivo_pdf,
                hash_integridad_sha256=acta_entidad.hash_integridad_sha256,
            )
        else:
            # Escenario 4: Acta generada en proceso de firmas electrónicas (sin descarga habilitada aún).
            resumen_acta = ResumenActaTramiteDTO(
                acta_generada=True,
                aprobada_por_docente=acta_entidad.aprobada_por_docente,
                aprobada_por_coordinador=acta_entidad.aprobada_por_coordinador,
                acta_en_firme=acta_entidad.esta_en_firme,
                descarga_habilitada=False,
                numero_acta=acta_entidad.numero_acta,
                fecha_emision=acta_entidad.fecha_emision,
                ruta_archivo_pdf=None,
                hash_integridad_sha256=None,
            )

        # 3.7. Determinación del siguiente paso y mensaje descriptivo según la máquina de estados (ADR-010)
        siguiente_paso, mensaje = self._construir_orientacion_tramite(
            practica=practica,
            horas_requeridas=horas_requeridas,
            horas_acumuladas_aprobadas=horas_acumuladas_aprobadas,
            horas_pendientes_validacion=horas_pendientes_validacion,
            porcentaje_avance_horas=porcentaje_avance_horas,
            motivo_rechazo=motivo_rechazo,
            resumen_evaluacion=resumen_evaluacion,
            resumen_acta=resumen_acta,
        )

        # -------------------------------------------------------------------
        # 4. Registro de un único EventoBitacora en modo solo lectura (ADR-006)
        # -------------------------------------------------------------------
        self._registrar_bitacora(
            actor_id=contexto_efectivo.usuario_id,
            rol=contexto_efectivo.rol,
            ip=contexto_efectivo.ip_origen,
            accion="CONSULTA_ESTADO_TRAMITE",
            entidad=f"Practica:{practica.id}",
            detalles={
                "practica_id": practica.id,
                "estudiante_id": practica.estudiante_id,
                "estado_actual": practica.estado_actual.value,
                "horas_acumuladas_aprobadas": horas_acumuladas_aprobadas,
                "horas_requeridas": horas_requeridas,
                "evaluacion_realizada": resumen_evaluacion.evaluacion_realizada,
                "acta_generada": resumen_acta.acta_generada,
            },
        )

        # -------------------------------------------------------------------
        # 5. Retorno del DTO inmutable de respuesta sin mutar ninguna entidad
        # -------------------------------------------------------------------
        return EstadoTramitePracticaRespuestaDTO(
            practica_id=practica.id,
            estudiante_id=practica.estudiante_id,
            estado_actual=practica.estado_actual.value,
            fecha_postulacion=practica.fecha_postulacion,
            fecha_inicio=practica.fecha_inicio,
            fecha_fin=practica.fecha_fin,
            regla_programa_id=practica.regla_programa_id,
            version_regla=version_regla,
            horas_requeridas=horas_requeridas,
            horas_acumuladas_aprobadas=horas_acumuladas_aprobadas,
            horas_pendientes_validacion=horas_pendientes_validacion,
            horas_restantes=horas_restantes,
            porcentaje_avance_horas=porcentaje_avance_horas,
            cantidad_reportes_pendientes=cantidad_reportes_pendientes,
            requisito_horas_cumplido=requisito_horas_cumplido,
            docente_asesor_id=practica.docente_asesor_id,
            nombre_docente_asesor=nombre_docente,
            correo_docente_asesor=correo_docente,
            supervisor_empresa_id=practica.supervisor_empresa_id,
            motivo_rechazo=motivo_rechazo,
            evaluacion=resumen_evaluacion,
            acta_final=resumen_acta,
            siguiente_paso=siguiente_paso,
            mensaje=mensaje,
        )

    # -----------------------------------------------------------------------
    # Métodos privados auxiliares
    # -----------------------------------------------------------------------

    def _construir_orientacion_tramite(
        self,
        *,
        practica: Practica,
        horas_requeridas: int,
        horas_acumuladas_aprobadas: int,
        horas_pendientes_validacion: int,
        porcentaje_avance_horas: float,
        motivo_rechazo: Optional[str],
        resumen_evaluacion: ResumenEvaluacionTramiteDTO,
        resumen_acta: ResumenActaTramiteDTO,
    ) -> tuple[str, str]:
        """Construye la orientación del siguiente paso y el mensaje de estado según la máquina de estados (ADR-010)."""
        estado = practica.estado_actual

        if estado == EstadoPractica.PENDIENTE_VERIFICACION:
            siguiente_paso = (
                "Pendiente de confirmación automática de requisitos académicos con el sistema "
                "académico (SIA) y posterior evaluación administrativa por el Coordinador de prácticas. "
                "Aún no cuenta con DocenteAsesor asignado."
            )
            mensaje = (
                f"Trámite de práctica '{practica.id}' en estado '{estado.value}': "
                f"{siguiente_paso} Horas requeridas por la regla del programa: {horas_requeridas}."
            )
            return siguiente_paso, mensaje

        if estado == EstadoPractica.SOLICITADA:
            siguiente_paso = (
                "Pendiente de evaluación administrativa (aprobación o rechazo) por el Coordinador "
                "de prácticas. Aún no cuenta con DocenteAsesor asignado."
            )
            mensaje = (
                f"Trámite de práctica '{practica.id}' en estado '{estado.value}': "
                f"{siguiente_paso} Horas requeridas por la regla del programa: {horas_requeridas}."
            )
            return siguiente_paso, mensaje

        if estado == EstadoPractica.APROBADA:
            siguiente_paso = (
                "Postulación aprobada por la Coordinación de prácticas. El siguiente paso del flujo "
                "es la asignación formal de un DocenteAsesor como tutor académico."
            )
            mensaje = (
                f"Trámite de práctica '{practica.id}' en estado '{estado.value}': {siguiente_paso}"
            )
            return siguiente_paso, mensaje

        if estado == EstadoPractica.ASIGNADA:
            siguiente_paso = (
                "DocenteAsesor asignado. El siguiente paso del flujo es el inicio de ejecución "
                "mediante el registro de reportes semanales de horas."
            )
            mensaje = (
                f"Trámite de práctica '{practica.id}' en estado '{estado.value}': "
                f"DocenteAsesor '{practica.docente_asesor_id}' asignado. "
                f"Avance actual: {horas_acumuladas_aprobadas}/{horas_requeridas} horas aprobadas. "
                f"{siguiente_paso}"
            )
            return siguiente_paso, mensaje

        if estado == EstadoPractica.EN_EJECUCION:
            detalle_pendientes = (
                f" Cuenta con {horas_pendientes_validacion} hora(s) en reportes pendientes de "
                f"validación por el SupervisorEmpresa."
                if horas_pendientes_validacion > 0
                else ""
            )
            siguiente_paso = (
                f"Continuar el registro y validación de horas semanales hasta completar las "
                f"{horas_requeridas} horas requeridas y posteriormente registrar la Evaluación "
                f"de Desempeño por el SupervisorEmpresa.{detalle_pendientes}"
            )
            mensaje = (
                f"Trámite de práctica '{practica.id}' en estado '{estado.value}': "
                f"{horas_acumuladas_aprobadas}/{horas_requeridas} horas aprobadas "
                f"({porcentaje_avance_horas}% de avance).{detalle_pendientes} "
                f"Aún no se ha registrado la EvaluacionDesempeno ni se ha emitido el ActaFinal."
            )
            return siguiente_paso, mensaje

        if estado == EstadoPractica.EVALUADA:
            if not resumen_acta.acta_generada:
                siguiente_paso = (
                    "Evaluación de desempeño registrada. El siguiente paso es la generación del "
                    "ActaFinal por el DocenteAsesor asignado y su aprobación electrónica secuencial."
                )
            elif not resumen_acta.aprobada_por_docente:
                siguiente_paso = (
                    "ActaFinal generada. Pendiente de la aprobación electrónica del DocenteAsesor "
                    "asignado y posteriormente del Coordinador de prácticas."
                )
            elif not resumen_acta.aprobada_por_coordinador:
                siguiente_paso = (
                    "ActaFinal con aprobación electrónica del DocenteAsesor registrada. "
                    "Pendiente de la aprobación electrónica final del Coordinador de prácticas."
                )
            else:
                siguiente_paso = "Pendiente de cierre formal de la práctica al estado 'Completada'."

            mensaje = (
                f"Trámite de práctica '{practica.id}' en estado '{estado.value}': "
                f"Horas cumplidas ({horas_acumuladas_aprobadas}/{horas_requeridas}). "
                f"La EvaluacionDesempeno ya fue realizada (el detalle de calificación se habilitará "
                f"una vez la práctica alcance el estado 'Completada'). {siguiente_paso}"
            )
            return siguiente_paso, mensaje

        if estado == EstadoPractica.COMPLETADA:
            siguiente_paso = (
                "Ciclo de vida de la práctica empresarial completado al 100% de los hitos de la "
                "máquina de estados. El documento PDF oficial del ActaFinal se encuentra en firme "
                "y habilitado para su descarga."
            )
            mensaje = (
                f"Trámite de práctica '{practica.id}' en estado '{estado.value}': "
                f"100% de los hitos completados ({horas_acumuladas_aprobadas}/{horas_requeridas} horas). "
                f"ActaFinal '{resumen_acta.numero_acta}' en firme con ambas firmas electrónicas y "
                f"evaluación de desempeño visible."
            )
            return siguiente_paso, mensaje

        # EstadoPractica.RECHAZADA
        detalle_causal = (
            f"Causal o justificación registrada: {motivo_rechazo}"
            if motivo_rechazo
            else "Revise los requisitos académicos o administrativos con la Coordinación de prácticas."
        )
        siguiente_paso = (
            f"Postulación en estado 'Rechazada'. {detalle_causal} "
            f"Puede subsanar los requisitos y radicar una nueva postulación."
        )
        mensaje = (
            f"Trámite de práctica '{practica.id}' en estado '{estado.value}'. {detalle_causal}"
        )
        return siguiente_paso, mensaje

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
        """Inserta un único registro inmutable EventoBitacora sellado con SHA-256 (ADR-006, EAC-03)."""
        evento = EventoBitacora(
            actor_identificador=actor_id or "ANONIMO",
            rol_actor=rol or "SIN_ROL",
            ip_origen=ip or "127.0.0.1",
            accion_realizada=accion,
            entidad_afectada=entidad,
            detalles=detalles,
        )
        self._repositorio_practica.guardar_evento_bitacora(evento)
