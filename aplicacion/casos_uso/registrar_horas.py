"""Caso de uso: Registrar horas de práctica semanales.

Traza: CU-04, EAC-03, RT-01, RN-01, RN-02, RN-03, ADR-002, ADR-005, ADR-006, ADR-010.

Implementa la orquestación del reporte semanal de horas ejecutadas por el estudiante:
1. Autorización RBAC centralizada con política deny-by-default (ADR-005, EAC-03):
   Solo usuarios con rol 'Estudiante' están autorizados.
   Accesos no autorizados se auditan de inmediato en la bitácora con 0 datos expuestos.
2. Búsqueda y validación de existencia de la práctica en el repositorio.
3. Validación de pertenencia contextual de datos (RN-01):
   El estudiante autenticado solo puede reportar horas en su propia práctica.
4. Validación de precondiciones de la máquina de estados finitos (ADR-010):
   Solo prácticas en estado 'Asignada' o 'EnEjecucion' pueden registrar horas.
5. Validación de invariantes de dominio (semana >= 1, 0 < horas <= 60, descripción obligatoria).
6. Validación de no duplicidad de semana reportada.
7. Transición formal automática 'Asignada' -> 'EnEjecucion' ante el primer reporte de horas,
   con registro de EventoBitacora append-only (ADR-006) y persistencia del nuevo estado.
8. Creación y persistencia transaccional del RegistroHoras en estado 'Pendiente' (ADR-003, RT-01).
9. Retorno de RegistroHorasRespuestaDTO con la confirmación estructurada.
"""

from __future__ import annotations

from typing import Any, Optional

from aplicacion.dtos.registro_horas_dto import (
    RegistrarHorasComando,
    RegistroHorasRespuestaDTO,
)
from aplicacion.puertos.repositorio_practica import RepositorioPracticaPort
from aplicacion.puertos.repositorio_registro_horas import RepositorioRegistroHorasPort
from aplicacion.seguridad.autorizador_rbac import (
    AccesoDenegadoError,
    AutorizadorRBAC,
    ContextoUsuario,
)
from dominio.errores import (
    CantidadHorasInvalidaError,
    DescripcionActividadesRequeridaError,
    EstadoPracticaInvalidoParaRegistroHorasError,
    PracticaNoEncontradaError,
    SemanaHorasYaRegistradaError,
    SemanaInvalidaError,
)
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.practica import EstadoPractica, Practica
from dominio.modelos.registro_horas import EstadoValidacionHoras, RegistroHoras


class RegistrarHorasCasoUso:
    """Caso de uso para registrar el reporte semanal de horas de una práctica empresarial.

    Permite al estudiante titular reportar las horas trabajadas y actividades desarrolladas
    en una semana, iniciando formalmente la ejecución de la práctica si se encontraba en estado
    'Asignada', y dejando el reporte en estado 'Pendiente' de validación por el supervisor.
    """

    def __init__(
        self,
        *,
        repositorio_practica: RepositorioPracticaPort,
        repositorio_registro_horas: RepositorioRegistroHorasPort,
        autorizador_rbac: Optional[AutorizadorRBAC] = None,
        lanzar_excepciones_dominio: bool = True,
    ) -> None:
        """Inicializa el caso de uso con sus dependencias y puertos requeridos.

        Args:
            repositorio_practica: Puerto de persistencia de prácticas y bitácora.
            repositorio_registro_horas: Puerto de persistencia de registros semanales de horas.
            autorizador_rbac: Componente centralizado de control de acceso RBAC.
            lanzar_excepciones_dominio: Si es True (por defecto), eleva excepciones de dominio;
                si es False, retorna RegistroHorasRespuestaDTO.fallida.
        """
        self._repositorio_practica: RepositorioPracticaPort = repositorio_practica
        self._repositorio_registro_horas: RepositorioRegistroHorasPort = repositorio_registro_horas
        self._autorizador_rbac: AutorizadorRBAC = autorizador_rbac or AutorizadorRBAC()
        self._lanzar_excepciones_dominio: bool = lanzar_excepciones_dominio

    def __call__(
        self,
        comando: RegistrarHorasComando,
        *,
        lanzar_excepciones_dominio: Optional[bool] = None,
    ) -> RegistroHorasRespuestaDTO:
        """Permite invocar la instancia del caso de uso como función callable."""
        return self.ejecutar(
            comando,
            lanzar_excepciones_dominio=lanzar_excepciones_dominio,
        )

    def ejecutar(
        self,
        comando: RegistrarHorasComando,
        *,
        lanzar_excepciones_dominio: Optional[bool] = None,
    ) -> RegistroHorasRespuestaDTO:
        """Ejecuta el registro de horas de práctica semanales.

        Args:
            comando: DTO inmutable con los datos del reporte semanal y credenciales del actor.
            lanzar_excepciones_dominio: Sobrescribe la política de excepciones del init.

        Returns:
            RegistroHorasRespuestaDTO con el resultado de la operación.

        Raises:
            AccesoDenegadoError: Si el usuario no cuenta con rol Estudiante o no es titular (EAC-03, RN-01).
            PracticaNoEncontradaError: Si la práctica especificada no existe.
            EstadoPracticaInvalidoParaRegistroHorasError: Si la práctica no está en Asignada o EnEjecucion.
            SemanaInvalidaError: Si el número de semana es <= 0.
            CantidadHorasInvalidaError: Si las horas son <= 0 o > 60.
            DescripcionActividadesRequeridaError: Si la descripción está vacía.
            SemanaHorasYaRegistradaError: Si ya existe un reporte para esa misma semana.
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
            self._autorizador_rbac.autorizar_comando_registro_horas(comando)
        except AccesoDenegadoError as error_rbac:
            # EAC-03: Registrar de inmediato el intento no autorizado en la bitácora
            # con IP, fecha y hora, asegurando 0 datos expuestos
            self._registrar_bitacora(
                actor_id=comando.actor_id,
                rol=comando.rol_actor,
                ip=comando.ip_origen,
                accion="Intento no autorizado de registro de horas",
                entidad="ModuloSeguimiento",
                detalles={
                    "operacion": "registrar_horas",
                    "diagnostico": str(error_rbac),
                },
            )
            if debe_lanzar:
                raise error_rbac
            return RegistroHorasRespuestaDTO.fallida(
                practica_id=comando.practica_id,
                semana=comando.semana,
                cantidad_horas=comando.cantidad_horas,
                descripcion_actividades=comando.descripcion_actividades,
                estado_practica="Desconocido",
                mensaje=str(error_rbac),
            )

        # -------------------------------------------------------------------
        # 2. Recuperación y existencia de la práctica
        # -------------------------------------------------------------------
        practica: Optional[Practica] = self._repositorio_practica.buscar_por_id(
            comando.practica_id
        )
        if practica is None:
            if debe_lanzar:
                raise PracticaNoEncontradaError(practica_id=comando.practica_id)
            return RegistroHorasRespuestaDTO.fallida(
                practica_id=comando.practica_id,
                semana=comando.semana,
                cantidad_horas=comando.cantidad_horas,
                descripcion_actividades=comando.descripcion_actividades,
                estado_practica="Inexistente",
                mensaje=f"No se encontró ninguna práctica con ID '{comando.practica_id}'.",
            )

        # -------------------------------------------------------------------
        # 3. Validación de pertenencia contextual de datos (RN-01, EAC-03)
        # -------------------------------------------------------------------
        contexto = ContextoUsuario(
            usuario_id=comando.actor_id,
            rol=comando.rol_actor,
            ip_origen=comando.ip_origen,
        )
        try:
            self._autorizador_rbac.validar_pertenencia_estudiante(
                contexto=contexto,
                estudiante=practica.estudiante_id,
                operacion="registrar_horas",
            )
        except AccesoDenegadoError as error_pertenencia:
            self._registrar_bitacora(
                actor_id=comando.actor_id,
                rol=comando.rol_actor,
                ip=comando.ip_origen,
                accion="Intento de acceso a recurso ajeno al registrar horas",
                entidad=f"Practica:{practica.id}",
                detalles={
                    "practica_id": practica.id,
                    "estudiante_titular": practica.estudiante_id,
                    "usuario_solicitante": comando.actor_id,
                    "diagnostico": str(error_pertenencia),
                },
            )
            if debe_lanzar:
                raise error_pertenencia
            return RegistroHorasRespuestaDTO.fallida(
                practica_id=practica.id,
                semana=comando.semana,
                cantidad_horas=comando.cantidad_horas,
                descripcion_actividades=comando.descripcion_actividades,
                estado_practica=practica.estado_actual.value,
                mensaje=str(error_pertenencia),
            )

        # -------------------------------------------------------------------
        # 4. Validación de precondiciones de estado en la Práctica (ADR-010)
        # -------------------------------------------------------------------
        if not practica.puede_registrar_horas():
            error_estado = EstadoPracticaInvalidoParaRegistroHorasError(
                practica_id=practica.id,
                estado_actual=practica.estado_actual.value,
            )
            if debe_lanzar:
                raise error_estado
            return RegistroHorasRespuestaDTO.fallida(
                practica_id=practica.id,
                semana=comando.semana,
                cantidad_horas=comando.cantidad_horas,
                descripcion_actividades=comando.descripcion_actividades,
                estado_practica=practica.estado_actual.value,
                mensaje=str(error_estado),
            )

        # -------------------------------------------------------------------
        # 5. Validación de invariantes de dominio para el reporte
        # -------------------------------------------------------------------
        if comando.semana < 1:
            error_semana = SemanaInvalidaError(semana=comando.semana)
            if debe_lanzar:
                raise error_semana
            return RegistroHorasRespuestaDTO.fallida(
                practica_id=practica.id,
                semana=comando.semana,
                cantidad_horas=comando.cantidad_horas,
                descripcion_actividades=comando.descripcion_actividades,
                estado_practica=practica.estado_actual.value,
                mensaje=str(error_semana),
            )

        if comando.cantidad_horas <= 0 or comando.cantidad_horas > 60:
            error_horas = CantidadHorasInvalidaError(
                cantidad_horas=comando.cantidad_horas,
                limite_maximo=60,
            )
            if debe_lanzar:
                raise error_horas
            return RegistroHorasRespuestaDTO.fallida(
                practica_id=practica.id,
                semana=comando.semana,
                cantidad_horas=comando.cantidad_horas,
                descripcion_actividades=comando.descripcion_actividades,
                estado_practica=practica.estado_actual.value,
                mensaje=str(error_horas),
            )

        if not comando.descripcion_actividades or not comando.descripcion_actividades.strip():
            error_desc = DescripcionActividadesRequeridaError()
            if debe_lanzar:
                raise error_desc
            return RegistroHorasRespuestaDTO.fallida(
                practica_id=practica.id,
                semana=comando.semana,
                cantidad_horas=comando.cantidad_horas,
                descripcion_actividades=comando.descripcion_actividades,
                estado_practica=practica.estado_actual.value,
                mensaje=str(error_desc),
            )

        # -------------------------------------------------------------------
        # 6. Verificación de no duplicidad de semana reportada
        # -------------------------------------------------------------------
        reporte_existente = self._repositorio_registro_horas.buscar_por_practica_y_semana(
            practica_id=practica.id,
            semana=comando.semana,
        )
        if reporte_existente is not None:
            error_duplicado = SemanaHorasYaRegistradaError(
                practica_id=practica.id,
                semana=comando.semana,
            )
            if debe_lanzar:
                raise error_duplicado
            return RegistroHorasRespuestaDTO.fallida(
                practica_id=practica.id,
                semana=comando.semana,
                cantidad_horas=comando.cantidad_horas,
                descripcion_actividades=comando.descripcion_actividades,
                estado_practica=practica.estado_actual.value,
                mensaje=str(error_duplicado),
            )

        # -------------------------------------------------------------------
        # 7. Transición automática Asignada -> EnEjecucion con primer reporte
        # -------------------------------------------------------------------
        estaba_asignada = practica.estado_actual == EstadoPractica.ASIGNADA
        if estaba_asignada:
            practica.iniciar_ejecucion()
            self._repositorio_practica.actualizar(practica)

            self._registrar_bitacora(
                actor_id=comando.actor_id,
                rol=comando.rol_actor,
                ip=comando.ip_origen,
                accion="Cambio de estado de práctica de Asignada a EnEjecucion",
                entidad=f"Practica:{practica.id}",
                detalles={
                    "practica_id": practica.id,
                    "estudiante_id": practica.estudiante_id,
                    "estado_anterior": EstadoPractica.ASIGNADA.value,
                    "nuevo_estado": EstadoPractica.EN_EJECUCION.value,
                    "semana_inicio": comando.semana,
                    "cantidad_horas": comando.cantidad_horas,
                },
            )

        # -------------------------------------------------------------------
        # 8. Creación e inserción del RegistroHoras (RT-01, ADR-003)
        # -------------------------------------------------------------------
        registro = RegistroHoras(
            practica_id=practica.id,
            semana=comando.semana,
            cantidad_horas=comando.cantidad_horas,
            descripcion_actividades=comando.descripcion_actividades,
            estado_validacion=EstadoValidacionHoras.PENDIENTE,
        )
        self._repositorio_registro_horas.guardar(registro)

        # -------------------------------------------------------------------
        # 9. Retorno de respuesta estructurada
        # -------------------------------------------------------------------
        if estaba_asignada:
            mensaje = (
                f"La práctica inició su fase de ejecución formal y las {registro.cantidad_horas} "
                f"horas de la semana {registro.semana} quedaron registradas en estado 'Pendiente' de validación."
            )
        else:
            mensaje = (
                f"Reporte de horas de la semana {registro.semana} registrado exitosamente "
                f"en estado 'Pendiente' de validación."
            )

        return RegistroHorasRespuestaDTO.exitosa(
            registro_horas_id=registro.id,
            practica_id=practica.id,
            semana=registro.semana,
            cantidad_horas=registro.cantidad_horas,
            descripcion_actividades=registro.descripcion_actividades,
            estado_validacion=registro.estado_validacion.value,
            estado_practica=practica.estado_actual.value,
            mensaje=mensaje,
            fecha_registro=registro.fecha_registro,
            detalles={
                "transicion_automatica": estaba_asignada,
                "estado_anterior": EstadoPractica.ASIGNADA.value if estaba_asignada else EstadoPractica.EN_EJECUCION.value,
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
