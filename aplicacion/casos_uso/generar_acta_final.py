"""Caso de uso: Generar acta final de la práctica (CU-09).

Traza: CU-09, EAC-01, EAC-03, OB-01, OB-05, PA-03, RN-01, RN-02, RN-03, DT-02,
ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores),
ADR-003 (Persistencia transaccional y compensación atómica),
ADR-005 (Control de acceso RBAC centralizado a nivel de casos de uso),
ADR-006 (Bitácora de auditoría transaccional de solo inserción - Append-Only),
ADR-007 (Configuración declarativa de reglas versionadas por programa),
ADR-008 (Generación y preservación del acta final mediante plantillas y sellado criptográfico SHA-256),
ADR-010 (Patrón Máquina de Estados Finitos para control del flujo de prácticas).

Implementa la orquestación de la generación oficial del ActaFinal en formato PDF y su sellado
criptográfico SHA-256 por parte del DocenteAsesor asignado a la práctica empresarial:
1. Autorización RBAC centralizada bajo política deny-by-default (ADR-005, RN-03):
   exclusivamente el rol DocenteAsesor (o Docente) puede invocar la generación del acta final.
   Cualquier intento por Estudiante, SupervisorEmpresa o Coordinador de prácticas es denegado
   con 0 datos expuestos y registro inmediato en bitácora (< 1 minuto, EAC-03, Escenarios 8 y 12).
2. Recuperación de la Práctica y validación estricta de pertenencia contextual (RN-01, ADR-005):
   si la práctica no existe, lanza PracticaNoEncontradaError (Escenario 9).
   El DocenteAsesor autenticado debe coincidir exactamente con el docente_asesor_id asignado
   a la Práctica. Cualquier intento sobre una práctica ajena o sin tutor asignado es denegado
   con 0 datos expuestos y registro inmediato en bitácora (< 1 minuto, EAC-03, Escenarios 7 y 12).
3. Verificación de unicidad del ActaFinal (relación 1 a 0..1), estado formal 'Evaluada',
   existencia de EvaluacionDesempeno y cumplimiento de horasRequeridas frente a la versión
   vinculada de ReglaPrograma (ADR-007, ADR-010, RN-02, EAC-01, Escenarios 1, 2, 3, 4, 5, 6 y 11).
4. Renderizado dinámico desde la plantilla HTML/CSS (plantillaActa) de la ReglaPrograma vinculada
   hacia binario PDF, cálculo del hashIntegridadSha256 (64 caracteres hexadecimales) y
   almacenamiento en el repositorio de actas PDF (ADR-007, ADR-008).
5. Persistencia atómica con compensación transaccional (ADR-003, ADR-006, DT-02, Escenario 10):
   persiste el ActaFinal (con numeroActa consecutivo anual "ACTA-<AÑO>-<NNNN>", aprobadaPorDocente=False
   y aprobadaPorCoordinador=False) y el EventoBitacora sellado con el hashIntegridadSha256.
   Si ocurre un fallo al almacenar el archivo PDF, persistir el ActaFinal o registrar en bitácora,
   ejecuta la compensación eliminando cualquier archivo PDF huérfano o registro parcial de ActaFinal.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from aplicacion.dtos.acta_final_dto import (
    ActaFinalRespuestaDTO,
    DatosRenderizadoActaDTO,
    GenerarActaFinalComando,
    ResultadoRenderizadoPdfDTO,
)
from aplicacion.puertos.repositorio_acta_final import RepositorioActaFinalPort
from aplicacion.puertos.repositorio_docente import RepositorioDocentePort
from aplicacion.puertos.repositorio_evaluacion_desempeno import (
    RepositorioEvaluacionDesempenoPort,
)
from aplicacion.puertos.repositorio_practica import RepositorioPracticaPort
from aplicacion.puertos.repositorio_regla import RepositorioReglaProgramaPort
from aplicacion.puertos.servicio_generador_acta_pdf import (
    ServicioGeneradorActaPdfPort,
)
from aplicacion.seguridad.autorizador_rbac import (
    AccesoDenegadoError,
    AutorizadorRBAC,
    ContextoUsuario,
)
from dominio.errores import (
    ActaFinalYaGeneradaError,
    ErrorAlmacenamientoActaPdfError,
    EstadoPracticaInvalidoParaActaError,
    EvaluacionDesempenoFaltanteParaActaError,
    HorasInsuficientesParaActaError,
    PracticaNoEncontradaError,
    ReglaProgramaNoConfiguradaError,
)
from dominio.modelos.acta_final import ActaFinal
from dominio.modelos.docente_asesor import DocenteAsesor
from dominio.modelos.evaluacion_desempeno import EvaluacionDesempeno
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.practica import Practica
from dominio.modelos.regla_programa import ReglaPrograma


class GenerarActaFinalCasoUso:
    """Caso de uso del Módulo Actas para generar el acta final de la práctica en PDF (CU-09)."""

    def __init__(
        self,
        *,
        repositorio_practica: RepositorioPracticaPort,
        repositorio_regla: RepositorioReglaProgramaPort,
        repositorio_evaluacion: RepositorioEvaluacionDesempenoPort,
        repositorio_acta: RepositorioActaFinalPort,
        servicio_pdf: ServicioGeneradorActaPdfPort,
        autorizador_rbac: Optional[AutorizadorRBAC] = None,
        repositorio_docente: Optional[RepositorioDocentePort] = None,
    ) -> None:
        self._repositorio_practica: RepositorioPracticaPort = repositorio_practica
        self._repositorio_regla: RepositorioReglaProgramaPort = repositorio_regla
        self._repositorio_evaluacion: RepositorioEvaluacionDesempenoPort = (
            repositorio_evaluacion
        )
        self._repositorio_acta: RepositorioActaFinalPort = repositorio_acta
        self._servicio_pdf: ServicioGeneradorActaPdfPort = servicio_pdf
        self._autorizador_rbac: AutorizadorRBAC = autorizador_rbac or AutorizadorRBAC()
        self._repositorio_docente: Optional[RepositorioDocentePort] = (
            repositorio_docente
        )

    def __call__(
        self,
        comando: GenerarActaFinalComando,
    ) -> ActaFinalRespuestaDTO:
        """Permite invocar la instancia del caso de uso como callable."""
        return self.ejecutar(comando)

    def ejecutar(
        self,
        comando: GenerarActaFinalComando,
    ) -> ActaFinalRespuestaDTO:
        """Genera el ActaFinal en PDF desde la plantilla versionada, la sella con SHA-256 y la persiste.

        Traza: CU-09, Escenarios 1 al 12, ADR-002, ADR-003, ADR-005, ADR-006, ADR-007, ADR-008, ADR-010.

        Args:
            comando: DTO inmutable con el identificador de la práctica y las credenciales del actor.

        Returns:
            ActaFinalRespuestaDTO con los datos del ActaFinal generada, su huella SHA-256
            y disponibilidad de previsualización lista para las firmas electrónicas de CU-10.

        Raises:
            AccesoDenegadoError: Si el actor no posee rol DocenteAsesor o no es el tutor asignado (Escenarios 7, 8, 12).
            PracticaNoEncontradaError: Si el identificador de la práctica no existe en el sistema (Escenario 9).
            ActaFinalYaGeneradaError: Si la práctica ya cuenta con un ActaFinal emitida (Escenario 5).
            EstadoPracticaInvalidoParaActaError: Si la práctica no se encuentra en estado 'Evaluada' (Escenario 2).
            EvaluacionDesempenoFaltanteParaActaError: Si la práctica carece de EvaluacionDesempeno (Escenario 4).
            HorasInsuficientesParaActaError: Si las horas acumuladas aprobadas son menores a las requeridas (Escenario 3).
            ReglaProgramaNoConfiguradaError: Si la regla de programa vinculada no existe.
            ErrorAlmacenamientoActaPdfError: Si falla la escritura del PDF o la persistencia del acta (Escenario 10).
        """
        contexto = ContextoUsuario(
            usuario_id=comando.actor_id,
            rol=comando.rol_actor,
            ip_origen=comando.ip_origen,
        )

        # -------------------------------------------------------------------
        # 1. Autorización de rol RBAC bajo política deny-by-default (ADR-005, RN-03, EAC-03)
        # -------------------------------------------------------------------
        try:
            self._autorizador_rbac.validar_generacion_acta(
                rol_actor=contexto.rol,
                usuario_id=contexto.usuario_id,
                operacion="generar_acta",
            )
        except AccesoDenegadoError as error_rol:
            self._registrar_bitacora_segura(
                actor_id=contexto.usuario_id,
                rol=contexto.rol,
                ip=contexto.ip_origen,
                accion="Intento de operación por rol no autorizado",
                entidad=f"Practica:{comando.practica_id}",
                detalles={
                    "operacion": "generar_acta",
                    "motivo": str(error_rol),
                },
            )
            raise error_rol

        # -------------------------------------------------------------------
        # 2. Recuperación de la Práctica y validación de pertenencia contextual (RN-01, ADR-005, EAC-03)
        # -------------------------------------------------------------------
        practica: Optional[Practica] = self._repositorio_practica.buscar_por_id(
            comando.practica_id
        )
        if practica is None:
            raise PracticaNoEncontradaError(practica_id=comando.practica_id)

        try:
            self._autorizador_rbac.validar_pertenencia_docente(
                contexto=contexto,
                docente_asignado_id=practica.docente_asesor_id,
                operacion="generar_acta",
            )
        except AccesoDenegadoError as error_pertenencia:
            self._registrar_bitacora_segura(
                actor_id=contexto.usuario_id,
                rol=contexto.rol,
                ip=contexto.ip_origen,
                accion="Intento de acceso a recurso ajeno",
                entidad=f"Practica:{practica.id}",
                detalles={
                    "operacion": "generar_acta",
                    "docente_solicitante": contexto.usuario_id,
                    "motivo": str(error_pertenencia),
                },
            )
            raise error_pertenencia

        # -------------------------------------------------------------------
        # 3. Verificación de unicidad del ActaFinal, estado Evaluada,
        #    Evaluación de Desempeño y Horas Requeridas (ADR-007, ADR-010, RN-02, EAC-01)
        # -------------------------------------------------------------------
        acta_existente: Optional[ActaFinal] = (
            self._repositorio_acta.buscar_por_practica(practica.id)
        )
        if acta_existente is not None:
            raise ActaFinalYaGeneradaError(
                practica_id=practica.id,
                acta_id=acta_existente.id,
                numero_acta=acta_existente.numero_acta,
            )

        regla: Optional[ReglaPrograma] = self._repositorio_regla.buscar_por_id(
            practica.regla_programa_id
        )
        if regla is None:
            raise ReglaProgramaNoConfiguradaError(
                programa_academico=practica.regla_programa_id
            )

        evaluacion: Optional[EvaluacionDesempeno] = (
            self._repositorio_evaluacion.buscar_por_practica(practica.id)
        )

        # Valida en el agregado Practica:
        # 1. Estado formal == Evaluada (Escenario 2)
        # 2. Existencia de EvaluacionDesempeno (Escenario 4)
        # 3. horasAcumuladasAprobadas >= regla.horas_requeridas (Escenario 3)
        practica.validar_requisitos_generacion_acta(
            horas_requeridas=regla.horas_requeridas,
            tiene_evaluacion=(evaluacion is not None),
            tiene_acta_previa=False,
        )

        assert evaluacion is not None
        assert practica.docente_asesor_id is not None

        # -------------------------------------------------------------------
        # 4. Renderizado desde plantilla HTML/CSS a PDF, sellado SHA-256 y
        #    persistencia atómica con compensación (ADR-003, ADR-006, ADR-008, DT-02)
        # -------------------------------------------------------------------
        fecha_emision: datetime = comando.fecha_emision or datetime.now(timezone.utc)
        numero_acta: str = self._repositorio_acta.siguiente_numero_acta(
            fecha_emision.year
        )

        nombre_docente = self._resolver_nombre_docente(practica.docente_asesor_id)
        supervisor_id = (
            practica.supervisor_empresa_id
            if practica.supervisor_empresa_id
            else evaluacion.supervisor_id
        )

        datos_renderizado = DatosRenderizadoActaDTO(
            numero_acta=numero_acta,
            practica_id=practica.id,
            estudiante_id=practica.estudiante_id,
            docente_asesor_id=practica.docente_asesor_id,
            nombre_docente_asesor=nombre_docente,
            supervisor_empresa_id=supervisor_id,
            regla_programa_id=regla.id,
            programa_academico=regla.programa_academico,
            version_regla=regla.version,
            plantilla_acta=regla.plantilla_acta,
            horas_requeridas=regla.horas_requeridas,
            horas_acumuladas_aprobadas=practica.horas_acumuladas_aprobadas,
            calificacion_cuantitativa=evaluacion.calificacion_cuantitativa,
            es_aprobatoria=evaluacion.es_aprobatoria,
            observaciones_evaluacion=evaluacion.observaciones,
            respuestas_rubrica=evaluacion.respuestas_rubrica,
            fecha_emision=fecha_emision,
        )

        try:
            resultado_pdf: ResultadoRenderizadoPdfDTO = (
                self._servicio_pdf.generar_y_guardar_acta_pdf(datos_renderizado)
            )
        except ErrorAlmacenamientoActaPdfError:
            raise
        except Exception as error_pdf:
            raise ErrorAlmacenamientoActaPdfError(
                practica_id=practica.id,
                causa=str(error_pdf),
            ) from error_pdf

        acta = ActaFinal(
            practica_id=practica.id,
            numero_acta=numero_acta,
            ruta_archivo_pdf=resultado_pdf.ruta_archivo_pdf,
            hash_integridad_sha256=resultado_pdf.hash_integridad_sha256,
            fecha_emision=fecha_emision,
            aprobada_por_docente=False,
            aprobada_por_coordinador=False,
        )

        acta_guardada = False
        try:
            self._repositorio_acta.guardar(acta)
            acta_guardada = True

            evento_bitacora = EventoBitacora(
                actor_identificador=contexto.usuario_id,
                rol_actor=contexto.rol,
                ip_origen=contexto.ip_origen,
                accion_realizada="Generación de acta final de la práctica",
                entidad_afectada=f"Practica:{practica.id}|ActaFinal:{acta.id}",
                fecha_hora=fecha_emision,
                huella_digital=acta.hash_integridad_sha256,
                detalles={
                    "acta_id": acta.id,
                    "numero_acta": acta.numero_acta,
                    "practica_id": practica.id,
                    "estudiante_id": practica.estudiante_id,
                    "docente_asesor_id": practica.docente_asesor_id,
                    "supervisor_empresa_id": supervisor_id,
                    "regla_programa_id": regla.id,
                    "version_regla": regla.version,
                    "plantilla_acta": regla.plantilla_acta,
                    "horas_requeridas": regla.horas_requeridas,
                    "horas_acumuladas_aprobadas": practica.horas_acumuladas_aprobadas,
                    "calificacion_cuantitativa": evaluacion.calificacion_cuantitativa,
                    "es_aprobatoria": evaluacion.es_aprobatoria,
                    "observaciones_evaluacion": evaluacion.observaciones,
                    "ruta_archivo_pdf": acta.ruta_archivo_pdf,
                    "hash_integridad_sha256": acta.hash_integridad_sha256,
                    "aprobada_por_docente": acta.aprobada_por_docente,
                    "aprobada_por_coordinador": acta.aprobada_por_coordinador,
                    "estado_practica": practica.estado_actual.value,
                },
            )
            self._repositorio_practica.guardar_evento_bitacora(evento_bitacora)
        except Exception as error_persistencia:
            # Compensación transaccional atómica (DT-02, Escenario 10):
            # 1. Si el registro de ActaFinal alcanzó a guardarse, se revierte.
            if acta_guardada:
                try:
                    self._repositorio_acta.eliminar_por_id(acta.id)
                except Exception:
                    pass
            # 2. Se elimina el archivo binario PDF del repositorio de actas para evitar PDFs huérfanos.
            try:
                self._servicio_pdf.eliminar_archivo_pdf(resultado_pdf.ruta_archivo_pdf)
            except Exception:
                pass

            if isinstance(error_persistencia, ErrorAlmacenamientoActaPdfError):
                raise error_persistencia
            raise ErrorAlmacenamientoActaPdfError(
                practica_id=practica.id,
                ruta_archivo_pdf=resultado_pdf.ruta_archivo_pdf,
                causa=str(error_persistencia),
            ) from error_persistencia

        # -------------------------------------------------------------------
        # 5. Retorno del DTO inmutable de respuesta manteniendo la Práctica en Evaluada
        # -------------------------------------------------------------------
        tipo_calificacion = (
            "aprobatoria" if evaluacion.es_aprobatoria else "reprobatoria"
        )
        mensaje_respuesta = (
            f"ActaFinal '{acta.numero_acta}' generada y sellada exitosamente para la práctica "
            f"'{practica.id}' utilizando la plantilla '{regla.plantilla_acta}' "
            f"(ReglaPrograma '{regla.id}' versión '{regla.version}', calificación {tipo_calificacion} "
            f"{evaluacion.calificacion_cuantitativa:.1f}, hash SHA-256: {acta.hash_integridad_sha256}). "
            f"La práctica permanece en estado '{practica.estado_actual.value}' a la espera de las "
            f"aprobaciones electrónicas."
        )

        return ActaFinalRespuestaDTO(
            acta_id=acta.id,
            numero_acta=acta.numero_acta,
            practica_id=practica.id,
            estudiante_id=practica.estudiante_id,
            docente_asesor_id=practica.docente_asesor_id,
            supervisor_empresa_id=supervisor_id,
            regla_programa_id=regla.id,
            programa_academico=regla.programa_academico,
            version_regla=regla.version,
            plantilla_acta=regla.plantilla_acta,
            horas_requeridas=regla.horas_requeridas,
            horas_acumuladas_aprobadas=practica.horas_acumuladas_aprobadas,
            calificacion_cuantitativa=evaluacion.calificacion_cuantitativa,
            es_aprobatoria=evaluacion.es_aprobatoria,
            observaciones_evaluacion=evaluacion.observaciones,
            ruta_archivo_pdf=acta.ruta_archivo_pdf,
            hash_integridad_sha256=acta.hash_integridad_sha256,
            aprobada_por_docente=acta.aprobada_por_docente,
            aprobada_por_coordinador=acta.aprobada_por_coordinador,
            estado_practica=practica.estado_actual.value,
            fecha_emision=acta.fecha_emision,
            previsualizacion_disponible=True,
            mensaje=mensaje_respuesta,
        )

    # -----------------------------------------------------------------------
    # Métodos privados auxiliares
    # -----------------------------------------------------------------------

    def _resolver_nombre_docente(self, docente_asesor_id: str) -> str:
        """Obtiene el nombre completo del DocenteAsesor si el repositorio está disponible."""
        if self._repositorio_docente is not None:
            docente: Optional[DocenteAsesor] = self._repositorio_docente.buscar_por_id(
                docente_asesor_id
            )
            if docente is not None:
                return docente.nombre_completo
        return f"Docente Asesor ({docente_asesor_id})"

    def _registrar_bitacora_segura(
        self,
        *,
        actor_id: str,
        rol: str,
        ip: str,
        accion: str,
        entidad: str,
        detalles: Optional[dict[str, Any]] = None,
    ) -> None:
        """Registra de inmediato un evento de rechazo de seguridad en la bitácora append-only (ADR-006, EAC-03)."""
        evento = EventoBitacora(
            actor_identificador=actor_id,
            rol_actor=rol,
            ip_origen=ip,
            accion_realizada=accion,
            entidad_afectada=entidad,
            detalles=detalles,
        )
        self._repositorio_practica.guardar_evento_bitacora(evento)
