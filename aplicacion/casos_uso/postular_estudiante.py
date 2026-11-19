"""Caso de uso principal: Postulación de estudiante a la práctica empresarial.

Traza: CU-01, EAC-02, RT-01, RT-03, RN-01, RN-03, PA-02, PA-03,
ADR-001 (Resiliencia e integración asíncrona),
ADR-002 (Clean Architecture y Puertos y Adaptadores),
ADR-004 (Autenticación híbrida),
ADR-005 (Autorización RBAC centralizada deny-by-default),
ADR-006 (Bitácora Append-Only),
ADR-007 (Reglas versionadas por programa),
ADR-010 (Máquina de estados finitos),
Vista Lógica §2, §3, Vista de Procesos §2, Vista de Desarrollo §2,
diagramas/secuencias/cu01-postularse.puml.

Implementa la orquestación del flujo principal y los escenarios alternativos y de calidad
del caso de uso CU-01 (Escenarios 1, 2, 3, 4 y 5 de spec.md):
1. Validación de autorización y pertenencia contextual RBAC (ADR-005, RN-01).
2. Verificación de invariantes de dominio: no tener práctica activa en curso (Escenario 3, ADR-010).
3. Verificación de regla de programa activa y vigente (Escenario 4, ADR-007).
4. Consulta síncrona al Sistema de Información Académica (SIA) con timeout de 5s (RT-03).
   - Caso 4.1: SIA responde OK y cumple requisitos -> Práctica 'Solicitada' (Escenario 1).
   - Caso 4.2: SIA responde OK y no cumple requisitos -> Práctica 'Rechazada' (Escenario 2).
   - Caso 4.3: Fallo, timeout (> 5s) o Circuit Breaker abierto en SIA -> Práctica 'PendienteVerificacion',
     encolamiento de tarea asíncrona en el bróker y respuesta inmediata al estudiante (Escenario 5, EAC-02, ADR-001).
5. Registro inmutable de trazabilidad (IntentoValidacion) y auditoría (EventoBitacora) (ADR-006).
"""

from __future__ import annotations

from typing import Optional

from aplicacion.dtos.postulacion_dto import (
    PostulacionRespuestaDTO,
    PostularEstudianteComando,
)
from aplicacion.puertos.publicador_eventos import (
    DatosTareaValidacionSia,
    PublicadorEventosPort,
)
from aplicacion.puertos.repositorio_practica import RepositorioPracticaPort
from aplicacion.puertos.repositorio_regla import RepositorioReglaProgramaPort
from aplicacion.puertos.servicio_registro_academico import (
    ErrorRegistroAcademico,
    IndisponibilidadRegistroAcademicoError,
    ResultadoRequisitosAcademicos,
    ServicioRegistroAcademicoPort,
    TimeoutRegistroAcademicoError,
)
from aplicacion.seguridad.autorizador_rbac import AccesoDenegadoError, AutorizadorRBAC
from dominio.errores import (
    PracticaActivaExistenteError,
    ReglaProgramaNoConfiguradaError,
)
from dominio.modelos.estudiante import Estudiante
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.intento_validacion import (
    IntentoValidacion,
    ResultadoValidacionSia,
)
from dominio.modelos.practica import EstadoPractica, Practica
from dominio.modelos.regla_programa import EstadoVigenciaRegla, ReglaPrograma


class PostularEstudianteCasoUso:
    """Caso de uso principal para gestionar la postulación general de un estudiante a la práctica.

    Orquesta las reglas de autorización RBAC, las precondiciones normativas del dominio,
    la consulta de requisitos académicos al SIA y la persistencia transaccional del
    ciclo de vida de la práctica.
    """

    def __init__(
        self,
        *,
        repositorio_practica: RepositorioPracticaPort,
        repositorio_regla: RepositorioReglaProgramaPort,
        servicio_registro_academico: ServicioRegistroAcademicoPort,
        publicador_eventos: PublicadorEventosPort,
        autorizador_rbac: Optional[AutorizadorRBAC] = None,
        lanzar_excepciones_dominio: bool = False,
    ) -> None:
        """Inicializa el caso de uso con sus puertos y componentes colaboradores.

        Args:
            repositorio_practica: Puerto de persistencia de prácticas, intentos y bitácora.
            repositorio_regla: Puerto de persistencia de reglas de programa versionadas.
            servicio_registro_academico: Puerto de integración con el SIA institucional.
            publicador_eventos: Puerto de publicación hacia el bróker de mensajería asíncrona.
            autorizador_rbac: Componente centralizado de control de acceso RBAC.
            lanzar_excepciones_dominio: Si es True, eleva excepciones de dominio ante violaciones
                de precondiciones (e.g. PracticaActivaExistenteError, ReglaProgramaNoConfiguradaError);
                si es False (por defecto), retorna un PostulacionRespuestaDTO bloqueado para la UI.
        """
        self._repositorio_practica: RepositorioPracticaPort = repositorio_practica
        self._repositorio_regla: RepositorioReglaProgramaPort = repositorio_regla
        self._servicio_registro_academico: ServicioRegistroAcademicoPort = servicio_registro_academico
        self._publicador_eventos: PublicadorEventosPort = publicador_eventos
        self._autorizador_rbac: AutorizadorRBAC = autorizador_rbac or AutorizadorRBAC()
        self._lanzar_excepciones_dominio: bool = lanzar_excepciones_dominio

    def __call__(
        self,
        comando: PostularEstudianteComando,
        *,
        lanzar_excepciones_dominio: Optional[bool] = None,
    ) -> PostulacionRespuestaDTO:
        """Permite invocar la instancia del caso de uso como función callable."""
        return self.ejecutar(
            comando,
            lanzar_excepciones_dominio=lanzar_excepciones_dominio,
        )

    def ejecutar(
        self,
        comando: PostularEstudianteComando,
        *,
        lanzar_excepciones_dominio: Optional[bool] = None,
    ) -> PostulacionRespuestaDTO:
        """Ejecuta el flujo completo de postulación de un estudiante a la práctica.

        Args:
            comando: DTO inmutable con los datos del solicitante y contexto de seguridad.
            lanzar_excepciones_dominio: Sobrescribe la política de excepciones configurada en el init.

        Returns:
            PostulacionRespuestaDTO con el resultado de la operación ('Solicitada',
            'PendienteVerificacion', 'Rechazada' o denegada/bloqueada).

        Raises:
            AccesoDenegadoError: Si el actor no tiene rol Estudiante o viola la pertenencia de identidad.
            PracticaActivaExistenteError: Si el estudiante ya tiene una práctica activa y lanzar_excepciones_dominio es True.
            ReglaProgramaNoConfiguradaError: Si no hay regla activa vigente y lanzar_excepciones_dominio es True.
        """
        debe_lanzar = (
            lanzar_excepciones_dominio
            if lanzar_excepciones_dominio is not None
            else self._lanzar_excepciones_dominio
        )

        # -------------------------------------------------------------------
        # 1. Autorización RBAC centralizada y validación de contexto (ADR-005, RN-01)
        # -------------------------------------------------------------------
        # Se asegura política deny-by-default: rol debe ser 'Estudiante' y corresponder al solicitante.
        self._autorizador_rbac.autorizar_comando_postulacion(comando)

        # Creación / validación de invariantes de la entidad Estudiante
        estudiante = Estudiante(
            documento=comando.documento,
            nombre_completo=comando.nombre_completo,
            correo_institucional=comando.correo_institucional,
            programa_academico=comando.programa_academico,
            id=comando.estudiante_id,
        )

        # -------------------------------------------------------------------
        # 2. Validación de precondición: Práctica activa en curso (Escenario 3, ADR-010)
        # -------------------------------------------------------------------
        practica_activa = self._repositorio_practica.buscar_activa_por_estudiante(estudiante.id)
        if practica_activa is None and estudiante.documento != estudiante.id:
            practica_activa = self._repositorio_practica.buscar_activa_por_estudiante(estudiante.documento)

        if practica_activa is not None and practica_activa.es_activa():
            # Auditoría append-only del bloqueo (ADR-006)
            self._registrar_bitacora(
                actor_id=estudiante.documento,
                rol=comando.rol_actor,
                ip=comando.ip_origen,
                accion="Postulación bloqueada: Práctica activa en curso",
                entidad=f"Practica:{practica_activa.id}",
                detalles={
                    "estudiante_id": estudiante.id,
                    "practica_activa_id": practica_activa.id,
                    "estado_actual": practica_activa.estado_actual.value,
                },
            )

            if debe_lanzar:
                raise PracticaActivaExistenteError(
                    estudiante_id=estudiante.documento,
                    practica_id=practica_activa.id,
                    estado_actual=practica_activa.estado_actual.value,
                )

            return PostulacionRespuestaDTO.bloqueada(
                mensaje=(
                    f"No puede postularse mientras tenga una práctica activa en curso "
                    f"(práctica ID: {practica_activa.id}, estado: '{practica_activa.estado_actual.value}')."
                ),
                causal_rechazo=f"Práctica activa en curso en estado '{practica_activa.estado_actual.value}'",
                detalles={
                    "practica_activa_id": practica_activa.id,
                    "estado_actual": practica_activa.estado_actual.value,
                },
            )

        # -------------------------------------------------------------------
        # 3. Validación de precondición: ReglaPrograma activa vigente (Escenario 4, ADR-007)
        # -------------------------------------------------------------------
        regla_programa = self._repositorio_regla.buscar_activa_por_programa(
            estudiante.programa_academico
        )

        if regla_programa is None or regla_programa.estado_vigencia != EstadoVigenciaRegla.ACTIVA:
            # Auditoría append-only del bloqueo (ADR-006)
            self._registrar_bitacora(
                actor_id=estudiante.documento,
                rol=comando.rol_actor,
                ip=comando.ip_origen,
                accion="Postulación bloqueada: Inexistencia de ReglaPrograma activa",
                entidad=f"Programa:{estudiante.programa_academico}",
                detalles={
                    "programa_academico": estudiante.programa_academico,
                    "estudiante_id": estudiante.id,
                },
            )

            if debe_lanzar:
                raise ReglaProgramaNoConfiguradaError(
                    programa_academico=estudiante.programa_academico
                )

            return PostulacionRespuestaDTO.bloqueada(
                mensaje=(
                    f"Su programa académico '{estudiante.programa_academico}' no tiene reglas "
                    f"activas configuradas y debe consultar con la Coordinación de prácticas."
                ),
                causal_rechazo="Inexistencia de ReglaPrograma activa vigente",
                detalles={"programa_academico": estudiante.programa_academico},
            )

        # -------------------------------------------------------------------
        # 4. Consulta síncrona al servicio de Registro Académico (SIA) (ADR-001, RT-03)
        # -------------------------------------------------------------------
        # Nota: La consulta está sujeta a timeout de 5 segundos y Circuit Breaker.
        # Ante fallo o timeout, se asegura 0% pérdida preservando en 'PendienteVerificacion' (EAC-02).
        try:
            resultado_sia: ResultadoRequisitosAcademicos = (
                self._servicio_registro_academico.consultar_requisitos_academicos(
                    estudiante.documento
                )
            )
        except (
            TimeoutRegistroAcademicoError,
            IndisponibilidadRegistroAcademicoError,
            ErrorRegistroAcademico,
        ) as error_sia:
            # Escenario 5: Indisponibilidad o timeout (> 5 s) de Registro Académico (EAC-02)
            return self._manejar_fallo_servicio_academico(
                estudiante=estudiante,
                regla=regla_programa,
                comando=comando,
                error=error_sia,
            )
        except Exception as error_inesperado:
            # Fallback de resiliencia ante cualquier error imprevisto de comunicación con el SIA
            return self._manejar_fallo_servicio_academico(
                estudiante=estudiante,
                regla=regla_programa,
                comando=comando,
                error=error_inesperado,
            )

        # -------------------------------------------------------------------
        # 5. Procesamiento del resultado emitido por el SIA (< 5 s)
        # -------------------------------------------------------------------
        if resultado_sia.cumple_requisitos:
            # Escenario 1: Postulación exitosa con verificación inmediata de requisitos
            return self._procesar_postulacion_exitosa(
                estudiante=estudiante,
                regla=regla_programa,
                comando=comando,
                resultado_sia=resultado_sia,
            )
        else:
            # Escenario 2: Rechazo de postulación por incumplimiento de requisitos académicos
            return self._procesar_postulacion_rechazada(
                estudiante=estudiante,
                regla=regla_programa,
                comando=comando,
                resultado_sia=resultado_sia,
            )

    # -----------------------------------------------------------------------
    # Métodos privados de procesamiento de escenarios
    # -----------------------------------------------------------------------

    def _procesar_postulacion_exitosa(
        self,
        *,
        estudiante: Estudiante,
        regla: ReglaPrograma,
        comando: PostularEstudianteComando,
        resultado_sia: ResultadoRequisitosAcademicos,
    ) -> PostulacionRespuestaDTO:
        """Procesa una postulación exitosa cumpliendo requisitos académicos (Escenario 1)."""
        # Creación de la entidad Practica en estado 'Solicitada' vinculada a la regla activa (ADR-007, ADR-010)
        practica = Practica(
            estudiante_id=estudiante.id,
            regla_programa_id=regla.id,
            estado_inicial=EstadoPractica.SOLICITADA,
        )
        self._repositorio_practica.guardar(practica)

        # Registro inmutable del IntentoValidacion exitoso (ADR-001)
        intento = IntentoValidacion(
            practica_id=practica.id,
            numero_intento=1,
            resultado_sia=ResultadoValidacionSia.CUMPLE_REQUISITOS,
            exitoso=True,
            detalle_estado="Cumple con los requisitos académicos exigidos en Registro Académico.",
        )
        self._repositorio_practica.guardar_intento_validacion(intento)

        # Registro de auditoría append-only (ADR-006)
        self._registrar_bitacora(
            actor_id=estudiante.documento,
            rol=comando.rol_actor,
            ip=comando.ip_origen,
            accion="Postulación registrada en estado 'Solicitada'",
            entidad=f"Practica:{practica.id}",
            detalles={
                "regla_programa_id": regla.id,
                "creditos_aprobados": resultado_sia.creditos_aprobados,
                "porcentaje_avance": resultado_sia.porcentaje_avance,
            },
        )

        return PostulacionRespuestaDTO.solicitada(
            practica_id=practica.id,
            regla_programa_id=regla.id,
            mensaje="Postulación registrada exitosamente en estado 'Solicitada'.",
            detalles={
                "creditos_aprobados": resultado_sia.creditos_aprobados,
                "porcentaje_avance": resultado_sia.porcentaje_avance,
            },
        )

    def _procesar_postulacion_rechazada(
        self,
        *,
        estudiante: Estudiante,
        regla: ReglaPrograma,
        comando: PostularEstudianteComando,
        resultado_sia: ResultadoRequisitosAcademicos,
    ) -> PostulacionRespuestaDTO:
        """Procesa el rechazo de postulación por incumplimiento académico (Escenario 2)."""
        causal = (
            resultado_sia.causal_incumplimiento
            if resultado_sia.causal_incumplimiento
            else "Incumplimiento de requisitos académicos según Registro Académico."
        )

        # Creación de la entidad Practica en estado 'Rechazada' vinculada a la regla activa
        practica = Practica(
            estudiante_id=estudiante.id,
            regla_programa_id=regla.id,
            estado_inicial=EstadoPractica.RECHAZADA,
        )
        self._repositorio_practica.guardar(practica)

        # Registro del intento de validación fallido con el detalle del incumplimiento
        intento = IntentoValidacion(
            practica_id=practica.id,
            numero_intento=1,
            resultado_sia=ResultadoValidacionSia.REQUISITOS_INCUMPLIDOS,
            exitoso=False,
            detalle_estado=causal,
        )
        self._repositorio_practica.guardar_intento_validacion(intento)

        # Registro de auditoría append-only (ADR-006)
        self._registrar_bitacora(
            actor_id=estudiante.documento,
            rol=comando.rol_actor,
            ip=comando.ip_origen,
            accion="Postulación rechazada por requisitos académicos",
            entidad=f"Practica:{practica.id}",
            detalles={
                "regla_programa_id": regla.id,
                "causal_rechazo": causal,
                "creditos_aprobados": resultado_sia.creditos_aprobados,
                "porcentaje_avance": resultado_sia.porcentaje_avance,
            },
        )

        return PostulacionRespuestaDTO.rechazada(
            practica_id=practica.id,
            causal_rechazo=causal,
            regla_programa_id=regla.id,
            mensaje=f"Postulación rechazada: {causal}",
            detalles={
                "creditos_aprobados": resultado_sia.creditos_aprobados,
                "porcentaje_avance": resultado_sia.porcentaje_avance,
            },
        )

    def _manejar_fallo_servicio_academico(
        self,
        *,
        estudiante: Estudiante,
        regla: ReglaPrograma,
        comando: PostularEstudianteComando,
        error: Exception,
    ) -> PostulacionRespuestaDTO:
        """Maneja la indisponibilidad o timeout del SIA según ADR-001 y EAC-02 (Escenario 5).

        Garantiza un 0% de postulaciones perdidas persistiendo de inmediato la Práctica
        en estado 'PendienteVerificacion', registrando el IntentoValidacion fallido,
        encolando la tarea en el bróker y retornando confirmación en pantalla en < 3 s.
        """
        es_timeout = isinstance(error, TimeoutRegistroAcademicoError)
        resultado_sia = (
            ResultadoValidacionSia.TIMEOUT
            if es_timeout
            else ResultadoValidacionSia.ERROR_COMUNICACION
        )
        detalle_diagnostico = str(error) or error.__class__.__name__

        # 1. Preservar la práctica en estado 'PendienteVerificacion' (0% postulaciones perdidas)
        practica = Practica(
            estudiante_id=estudiante.id,
            regla_programa_id=regla.id,
            estado_inicial=EstadoPractica.PENDIENTE_VERIFICACION,
        )
        self._repositorio_practica.guardar(practica)

        # 2. Registrar el intento de validación inicial indicando el fallo de comunicación
        intento = IntentoValidacion(
            practica_id=practica.id,
            numero_intento=1,
            resultado_sia=resultado_sia,
            exitoso=False,
            detalle_estado=detalle_diagnostico,
        )
        self._repositorio_practica.guardar_intento_validacion(intento)

        # 3. Encolar tarea en el bróker para verificación asíncrona en segundo plano
        tarea = DatosTareaValidacionSia(
            practica_id=practica.id,
            documento_estudiante=estudiante.documento,
            correo_estudiante=estudiante.correo_institucional,
            numero_reintento=1,
            metadata={
                "causa_original": detalle_diagnostico,
                "tipo_fallo": error.__class__.__name__,
                "regla_programa_id": regla.id,
            },
        )
        self._publicador_eventos.publicar_tarea_validacion_sia(tarea)

        # 4. Auditoría append-only del evento (ADR-006)
        self._registrar_bitacora(
            actor_id=estudiante.documento,
            rol=comando.rol_actor,
            ip=comando.ip_origen,
            accion="Postulación registrada en estado 'PendienteVerificacion' por fallo SIA",
            entidad=f"Practica:{practica.id}",
            detalles={
                "regla_programa_id": regla.id,
                "tipo_fallo": error.__class__.__name__,
                "diagnostico": detalle_diagnostico,
            },
        )

        # 5. Confirmación inmediata al estudiante (< 3 segundos, EAC-02)
        return PostulacionRespuestaDTO.pendiente_verificacion(
            practica_id=practica.id,
            regla_programa_id=regla.id,
            mensaje=(
                "Solicitud recibida. Su postulación quedó en estado 'Pendiente de verificación' "
                "debido a indisponibilidad temporal del servicio de Registro Académico. "
                "Se verificará automáticamente en segundo plano."
            ),
            detalles={
                "motivo_espera": detalle_diagnostico,
                "tipo_fallo": error.__class__.__name__,
            },
        )

    def _registrar_bitacora(
        self,
        *,
        actor_id: str,
        rol: str,
        ip: str,
        accion: str,
        entidad: str,
        detalles: Optional[dict] = None,
    ) -> None:
        """Registra un evento inmutable en la bitácora de auditoría sin interrumpir el flujo."""
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
            # La falla en la bitácora no debe enmascarar transacciones críticas
            pass
