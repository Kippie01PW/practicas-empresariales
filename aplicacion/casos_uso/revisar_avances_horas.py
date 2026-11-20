"""Caso de uso: Revisar avances de horas (CU-06).

Traza: CU-06, EAC-01, EAC-03, RT-01, RN-01, RN-02, RN-03, ADR-002, ADR-004, ADR-005, ADR-006, ADR-007, ADR-010.

Implementa la consulta estrictamente de solo lectura de los reportes semanales de horas
y el acumulado de horas aprobadas de una práctica empresarial frente a las horas exigidas
por la regla del programa vinculada (ADR-007, EAC-01), así como la consulta consolidada
de las prácticas asignadas a un docente asesor:
1. Autorización RBAC centralizada bajo política deny-by-default (ADR-005):
   Solo los roles DocenteAsesor (Docente) y Estudiante están autorizados para la consulta
   individual, y exclusivamente DocenteAsesor (Docente) para la consulta consolidada.
   El Coordinador de prácticas (quien utiliza CU-13) y el SupervisorEmpresa son rechazados
   con 0 datos expuestos y registro inmediato en bitácora (EAC-03).
2. Búsqueda de la Práctica en el repositorio. Si no existe, lanza PracticaNoEncontradaError.
3. Validación estricta de pertenencia contextual de datos (RN-01, ADR-005):
   - Un DocenteAsesor solo puede consultar prácticas donde figure como tutor asignado.
   - Un Estudiante solo puede consultar la práctica de la cual es titular.
   Todo intento de acceso sin pertenencia contextual es denegado con 0 datos expuestos
   y registro de un único EventoBitacora (EAC-03).
4. Recuperación de la ReglaPrograma vinculada a la práctica al momento de su postulación
   para calcular el progreso sobre sus horasRequeridas inmutables (ADR-007, EAC-01).
5. Recuperación de los reportes semanales de RegistroHoras y cálculo en modo solo lectura
   de horas acumuladas aprobadas, pendientes, rechazadas, restantes, porcentaje de avance
   y cumplimiento del requisito, sin alterar la práctica ni sus registros (ADR-010).
6. Registro de un único EventoBitacora inmutable en la bitácora de auditoría (ADR-006).
"""

from __future__ import annotations

from typing import Any, Optional

from aplicacion.dtos.avance_horas_dto import (
    AvanceHorasPracticaRespuestaDTO,
    ConsultarAvanceHorasComando,
    ConsultarAvancesDocenteComando,
    DetalleReporteHorasDTO,
    ListadoAvancesDocenteRespuestaDTO,
    ResumenAvancePracticaDTO,
)
from aplicacion.puertos.repositorio_practica import RepositorioPracticaPort
from aplicacion.puertos.repositorio_registro_horas import RepositorioRegistroHorasPort
from aplicacion.puertos.repositorio_regla import RepositorioReglaProgramaPort
from aplicacion.seguridad.autorizador_rbac import (
    AccesoDenegadoError,
    AutorizadorRBAC,
    ContextoUsuario,
    RolUsuario,
)
from dominio.errores import PracticaNoEncontradaError
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.practica import Practica
from dominio.modelos.registro_horas import EstadoValidacionHoras, RegistroHoras
from dominio.modelos.regla_programa import ReglaPrograma


class RevisarAvancesHorasCasoUso:
    """Caso de uso del Módulo Seguimiento y Evaluación para revisar avances de horas (CU-06)."""

    def __init__(
        self,
        *,
        repositorio_practica: RepositorioPracticaPort,
        repositorio_registro_horas: RepositorioRegistroHorasPort,
        repositorio_regla: RepositorioReglaProgramaPort,
        autorizador_rbac: Optional[AutorizadorRBAC] = None,
    ) -> None:
        self._repositorio_practica: RepositorioPracticaPort = repositorio_practica
        self._repositorio_registro_horas: RepositorioRegistroHorasPort = (
            repositorio_registro_horas
        )
        self._repositorio_regla: RepositorioReglaProgramaPort = repositorio_regla
        self._autorizador_rbac: AutorizadorRBAC = autorizador_rbac or AutorizadorRBAC()

    def __call__(
        self,
        comando: ConsultarAvanceHorasComando,
    ) -> AvanceHorasPracticaRespuestaDTO:
        """Permite invocar la instancia como callable para la consulta individual."""
        return self.ejecutar(comando)

    def ejecutar(
        self,
        comando: ConsultarAvanceHorasComando,
    ) -> AvanceHorasPracticaRespuestaDTO:
        """Consulta en modo solo lectura el avance de horas y reportes semanales de una práctica.

        Args:
            comando: DTO inmutable con el identificador de la práctica y credenciales del actor.

        Returns:
            AvanceHorasPracticaRespuestaDTO con el resumen de progreso y desglose cronológico.

        Raises:
            AccesoDenegadoError: Si el rol no está autorizado o se viola la pertenencia contextual.
            PracticaNoEncontradaError: Si el identificador de la práctica no existe en el sistema.
        """
        contexto = ContextoUsuario(
            usuario_id=comando.actor_id,
            rol=comando.rol_actor,
            ip_origen=comando.ip_origen,
        )

        # -------------------------------------------------------------------
        # 1. Verificación de rol RBAC bajo política deny-by-default (ADR-005)
        # -------------------------------------------------------------------
        try:
            self._autorizador_rbac.validar_revision_avances_horas(
                rol_actor=contexto.rol,
                usuario_id=contexto.usuario_id,
                operacion="revisar_avances_horas",
            )
        except AccesoDenegadoError as error_rol:
            self._registrar_bitacora(
                actor_id=contexto.usuario_id,
                rol=contexto.rol,
                ip=contexto.ip_origen,
                accion="ACCESO_DENEGADO_ROL_NO_AUTORIZADO_AVANCE_HORAS",
                entidad=f"Practica:{comando.practica_id}",
                detalles={
                    "motivo": str(error_rol),
                    "operacion": "revisar_avances_horas",
                },
            )
            raise error_rol

        # -------------------------------------------------------------------
        # 2. Recuperación de la Práctica (Escenario 10)
        # -------------------------------------------------------------------
        practica: Optional[Practica] = self._repositorio_practica.buscar_por_id(
            comando.practica_id
        )
        if practica is None:
            raise PracticaNoEncontradaError(practica_id=comando.practica_id)

        # -------------------------------------------------------------------
        # 3. Validación de pertenencia contextual (RN-01, ADR-005, EAC-03)
        # -------------------------------------------------------------------
        rol_normalizado = self._autorizador_rbac.normalizar_rol(contexto.rol)
        try:
            if rol_normalizado in {
                RolUsuario.DOCENTE.value,
                RolUsuario.DOCENTE_ASESOR.value,
            }:
                self._autorizador_rbac.validar_pertenencia_docente(
                    contexto=contexto,
                    docente_asignado_id=practica.docente_asesor_id,
                    operacion="revisar_avances_horas",
                )
            elif rol_normalizado == RolUsuario.ESTUDIANTE.value:
                self._autorizador_rbac.validar_pertenencia_estudiante(
                    contexto=contexto,
                    estudiante=practica.estudiante_id,
                    operacion="revisar_avances_horas",
                )
        except AccesoDenegadoError as error_pertenencia:
            accion_rechazo = (
                "ACCESO_DENEGADO_PRACTICA_SIN_DOCENTE_ASIGNADO"
                if (
                    rol_normalizado
                    in {RolUsuario.DOCENTE.value, RolUsuario.DOCENTE_ASESOR.value}
                    and not practica.docente_asesor_id
                )
                else "ACCESO_DENEGADO_RECURSO_AJENO_AVANCE_HORAS"
            )
            self._registrar_bitacora(
                actor_id=contexto.usuario_id,
                rol=contexto.rol,
                ip=contexto.ip_origen,
                accion=accion_rechazo,
                entidad=f"Practica:{practica.id}",
                detalles={
                    "motivo": str(error_pertenencia),
                    "operacion": "revisar_avances_horas",
                },
            )
            raise error_pertenencia

        # -------------------------------------------------------------------
        # 4. Recuperación de la ReglaPrograma versionada vinculada (ADR-007, EAC-01)
        # -------------------------------------------------------------------
        regla: Optional[ReglaPrograma] = self._repositorio_regla.buscar_por_id(
            practica.regla_programa_id
        )
        horas_requeridas: int = regla.horas_requeridas if regla is not None else 320
        version_regla: str = regla.version if regla is not None else "1.0"

        # -------------------------------------------------------------------
        # 5. Recuperación de reportes semanales y cálculo en modo solo lectura
        # -------------------------------------------------------------------
        registros: list[RegistroHoras] = (
            self._repositorio_registro_horas.listar_por_practica(practica.id)
        )
        registros_ordenados = sorted(registros, key=lambda r: r.semana)

        horas_acumuladas_aprobadas: int = practica.horas_acumuladas_aprobadas
        horas_pendientes_validacion: int = sum(
            r.cantidad_horas
            for r in registros_ordenados
            if r.estado_validacion == EstadoValidacionHoras.PENDIENTE
        )
        horas_rechazadas: int = sum(
            r.cantidad_horas
            for r in registros_ordenados
            if r.estado_validacion == EstadoValidacionHoras.RECHAZADO
        )
        horas_restantes: int = max(0, horas_requeridas - horas_acumuladas_aprobadas)
        porcentaje_avance: float = (
            round((horas_acumuladas_aprobadas / horas_requeridas) * 100.0, 2)
            if horas_requeridas > 0
            else 0.0
        )
        requisito_horas_cumplido: bool = horas_acumuladas_aprobadas >= horas_requeridas

        reportes_dto: tuple[DetalleReporteHorasDTO, ...] = tuple(
            DetalleReporteHorasDTO(
                registro_horas_id=r.id,
                semana=r.semana,
                cantidad_horas=r.cantidad_horas,
                descripcion_actividades=r.descripcion_actividades,
                estado_validacion=r.estado_validacion.value,
                observaciones_rechazo=r.observaciones_rechazo,
                fecha_registro=r.fecha_registro,
            )
            for r in registros_ordenados
        )

        if not reportes_dto:
            mensaje = (
                f"El estudiante titular aún no ha registrado reportes de horas para la práctica "
                f"'{practica.id}'. Avance actual: 0/{horas_requeridas} horas (0.0%)."
            )
        elif requisito_horas_cumplido:
            mensaje = (
                f"La práctica '{practica.id}' cumple la totalidad de horas exigidas por su "
                f"ReglaPrograma vinculada (versión {version_regla}): "
                f"{horas_acumuladas_aprobadas}/{horas_requeridas} horas aprobadas "
                f"({porcentaje_avance}% de avance, 0 horas restantes)."
            )
        else:
            mensaje = (
                f"Avance de horas de la práctica '{practica.id}': "
                f"{horas_acumuladas_aprobadas}/{horas_requeridas} horas aprobadas "
                f"({porcentaje_avance}% de avance, {horas_restantes} horas restantes por aprobar)."
            )

        # -------------------------------------------------------------------
        # 6. Registro de un único EventoBitacora en modo solo lectura (ADR-006)
        # -------------------------------------------------------------------
        self._registrar_bitacora(
            actor_id=contexto.usuario_id,
            rol=contexto.rol,
            ip=contexto.ip_origen,
            accion="CONSULTA_AVANCE_HORAS",
            entidad=f"Practica:{practica.id}",
            detalles={
                "horas_acumuladas_aprobadas": horas_acumuladas_aprobadas,
                "horas_requeridas": horas_requeridas,
                "horas_pendientes_validacion": horas_pendientes_validacion,
                "horas_rechazadas": horas_rechazadas,
                "porcentaje_avance": porcentaje_avance,
                "total_reportes": len(reportes_dto),
            },
        )

        # -------------------------------------------------------------------
        # 7. Retorno del DTO inmutable de respuesta
        # -------------------------------------------------------------------
        return AvanceHorasPracticaRespuestaDTO(
            practica_id=practica.id,
            estudiante_id=practica.estudiante_id,
            docente_asesor_id=practica.docente_asesor_id,
            estado_practica=practica.estado_actual.value,
            regla_programa_id=practica.regla_programa_id,
            version_regla=version_regla,
            horas_requeridas=horas_requeridas,
            horas_acumuladas_aprobadas=horas_acumuladas_aprobadas,
            horas_pendientes_validacion=horas_pendientes_validacion,
            horas_rechazadas=horas_rechazadas,
            horas_restantes=horas_restantes,
            porcentaje_avance=porcentaje_avance,
            requisito_horas_cumplido=requisito_horas_cumplido,
            reportes_semanales=reportes_dto,
            mensaje=mensaje,
        )

    def listar_por_docente(
        self,
        comando: ConsultarAvancesDocenteComando,
    ) -> ListadoAvancesDocenteRespuestaDTO:
        """Consulta consolidada en modo solo lectura del avance de las prácticas asignadas a un docente asesor.

        Traza: CU-06, Escenario 6 (Consulta consolidada del avance de horas de todas las prácticas
        asignadas al docente asesor), RN-01, ADR-005, ADR-006, EAC-03.

        Args:
            comando: DTO inmutable con el identificador del docente asesor y credenciales del actor.

        Returns:
            ListadoAvancesDocenteRespuestaDTO con los resúmenes de las prácticas asignadas al docente.

        Raises:
            AccesoDenegadoError: Si el actor no tiene rol DocenteAsesor o intenta consultar otro docente.
        """
        contexto = ContextoUsuario(
            usuario_id=comando.actor_id,
            rol=comando.rol_actor,
            ip_origen=comando.ip_origen,
        )

        # -------------------------------------------------------------------
        # 1. Verificación de rol RBAC y pertenencia del docente asesor (ADR-005)
        # -------------------------------------------------------------------
        try:
            self._autorizador_rbac.validar_revision_avances_horas(
                rol_actor=contexto.rol,
                usuario_id=contexto.usuario_id,
                operacion="listar_avances_docente",
            )
            self._autorizador_rbac.validar_pertenencia_docente(
                contexto=contexto,
                docente_asignado_id=comando.docente_asesor_id,
                operacion="listar_avances_docente",
            )
        except AccesoDenegadoError as error_acceso:
            self._registrar_bitacora(
                actor_id=contexto.usuario_id,
                rol=contexto.rol,
                ip=contexto.ip_origen,
                accion="ACCESO_DENEGADO_CONSULTA_CONSOLIDADA_DOCENTE",
                entidad=f"DocenteAsesor:{comando.docente_asesor_id}",
                detalles={
                    "motivo": str(error_acceso),
                    "operacion": "listar_avances_docente",
                },
            )
            raise error_acceso

        # -------------------------------------------------------------------
        # 2. Recuperación de las prácticas asignadas al docente asesor
        # -------------------------------------------------------------------
        practicas_asignadas: list[Practica] = (
            self._repositorio_practica.listar_por_docente(comando.docente_asesor_id)
        )

        # -------------------------------------------------------------------
        # 3. Construcción de resúmenes de progreso en modo solo lectura
        # -------------------------------------------------------------------
        resumenes: list[ResumenAvancePracticaDTO] = []
        for practica in practicas_asignadas:
            regla: Optional[ReglaPrograma] = self._repositorio_regla.buscar_por_id(
                practica.regla_programa_id
            )
            horas_requeridas: int = regla.horas_requeridas if regla is not None else 320
            horas_acumuladas: int = practica.horas_acumuladas_aprobadas
            horas_restantes: int = max(0, horas_requeridas - horas_acumuladas)
            porcentaje_avance: float = (
                round((horas_acumuladas / horas_requeridas) * 100.0, 2)
                if horas_requeridas > 0
                else 0.0
            )
            requisito_cumplido: bool = horas_acumuladas >= horas_requeridas

            registros: list[RegistroHoras] = (
                self._repositorio_registro_horas.listar_por_practica(practica.id)
            )
            cantidad_pendientes: int = sum(
                1
                for r in registros
                if r.estado_validacion == EstadoValidacionHoras.PENDIENTE
            )

            resumenes.append(
                ResumenAvancePracticaDTO(
                    practica_id=practica.id,
                    estudiante_id=practica.estudiante_id,
                    estado_actual=practica.estado_actual.value,
                    horas_acumuladas_aprobadas=horas_acumuladas,
                    horas_requeridas=horas_requeridas,
                    horas_restantes=horas_restantes,
                    porcentaje_avance=porcentaje_avance,
                    cantidad_reportes_pendientes=cantidad_pendientes,
                    requisito_horas_cumplido=requisito_cumplido,
                )
            )

        resumenes_tupla = tuple(resumenes)
        mensaje = (
            f"Consulta consolidada de avances de horas para el docente asesor "
            f"'{comando.docente_asesor_id}': {len(resumenes_tupla)} práctica(s) asignada(s)."
        )

        # -------------------------------------------------------------------
        # 4. Registro de un único EventoBitacora por la consulta consolidada
        # -------------------------------------------------------------------
        self._registrar_bitacora(
            actor_id=contexto.usuario_id,
            rol=contexto.rol,
            ip=contexto.ip_origen,
            accion="CONSULTA_CONSOLIDADA_AVANCES_DOCENTE",
            entidad=f"DocenteAsesor:{comando.docente_asesor_id}",
            detalles={
                "total_practicas_asignadas": len(resumenes_tupla),
            },
        )

        return ListadoAvancesDocenteRespuestaDTO(
            docente_asesor_id=comando.docente_asesor_id,
            total_practicas_asignadas=len(resumenes_tupla),
            practicas=resumenes_tupla,
            mensaje=mensaje,
        )

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
        """Registra un único evento inmutable en la bitácora de auditoría append-only (ADR-006)."""
        evento = EventoBitacora(
            actor_identificador=actor_id,
            rol_actor=rol,
            ip_origen=ip,
            accion_realizada=accion,
            entidad_afectada=entidad,
            detalles=detalles,
        )
        self._repositorio_practica.guardar_evento_bitacora(evento)
