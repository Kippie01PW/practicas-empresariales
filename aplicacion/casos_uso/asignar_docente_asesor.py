"""Caso de uso: Asignar docente asesor o tutor a una práctica aprobada.

Traza: CU-03, EAC-03, RT-01, RN-03, ADR-002, ADR-005, ADR-006, ADR-010.

Implementa la orquestación de la asignación formal de un tutor académico a una práctica:
1. Autorización RBAC centralizada con política deny-by-default (ADR-005, EAC-03):
   Solo usuarios con rol 'Coordinador' o 'Coordinador de prácticas' están autorizados.
   Accesos denegados se auditan de inmediato en la bitácora con 0 datos expuestos de la práctica,
   del estudiante y del docente.
2. Búsqueda y validación de existencia de la práctica en el repositorio.
3. Validación de precondiciones de la máquina de estados (ADR-010):
   Solo prácticas en estado 'Aprobada' y sin tutor previo pueden recibir asignación.
4. Búsqueda y validación de existencia y habilitación del DocenteAsesor en el repositorio.
5. Validación de cupo disponible del tutor académico (RT-01, CupoDocenteExcedidoError).
6. Transición formal en el dominio:
   - `practica.asignar_tutor(docente.id)` -> transiciona a `EstadoPractica.ASIGNADA`.
   - `docente.asignar_practica()` -> incrementa carga de tutorías activas.
7. Persistencia transaccional de la práctica y del docente actualizados (ADR-003).
8. Registro inmutable append-only del evento en la bitácora de auditoría (ADR-006).
9. Emisión de notificaciones por correo institucional tanto al estudiante titular como al docente asesor.
10. Retorno de `AsignacionDocenteRespuestaDTO`.
"""

from __future__ import annotations

from typing import Any, Optional

from aplicacion.dtos.asignacion_docente_dto import (
    AsignacionDocenteRespuestaDTO,
    AsignarDocenteComando,
)
from aplicacion.puertos.repositorio_docente import RepositorioDocentePort
from aplicacion.puertos.repositorio_practica import RepositorioPracticaPort
from aplicacion.puertos.servicio_correo import (
    ErrorServicioCorreo,
    ServicioCorreoPort,
)
from aplicacion.seguridad.autorizador_rbac import AccesoDenegadoError, AutorizadorRBAC
from dominio.errores import (
    CupoDocenteExcedidoError,
    DecisionPreviaEnFirmeError,
    DocenteAsesorNoEncontradoError,
    PracticaNoEncontradaError,
    PracticaYaTieneTutorAsignadoError,
    TransicionEstadoInvalidaError,
)
from dominio.modelos.docente_asesor import DocenteAsesor
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.practica import EstadoPractica, Practica


class AsignarDocenteAsesorCasoUso:
    """Caso de uso para asignar un docente asesor a una práctica en estado Aprobada.

    Permite al Coordinador de prácticas vincular al tutor académico responsable del
    seguimiento del estudiante, verificando disponibilidad de cupo y avanzando la
    práctica al estado Asignada.
    """

    def __init__(
        self,
        *,
        repositorio_practica: RepositorioPracticaPort,
        repositorio_docente: RepositorioDocentePort,
        servicio_correo: ServicioCorreoPort,
        autorizador_rbac: Optional[AutorizadorRBAC] = None,
        lanzar_excepciones_dominio: bool = True,
    ) -> None:
        """Inicializa el caso de uso con sus colaboradores requeridos.

        Args:
            repositorio_practica: Puerto de persistencia de prácticas y bitácora.
            repositorio_docente: Puerto de persistencia y consulta de tutores académicos.
            servicio_correo: Puerto para envío de notificaciones por correo electrónico.
            autorizador_rbac: Componente centralizado de control de acceso RBAC.
            lanzar_excepciones_dominio: Si es True (por defecto), eleva excepciones de
                dominio ante transiciones inválidas, cupo excedido o entidades inexistentes;
                si es False, retorna AsignacionDocenteRespuestaDTO.denegada.
        """
        self._repositorio_practica: RepositorioPracticaPort = repositorio_practica
        self._repositorio_docente: RepositorioDocentePort = repositorio_docente
        self._servicio_correo: ServicioCorreoPort = servicio_correo
        self._autorizador_rbac: AutorizadorRBAC = autorizador_rbac or AutorizadorRBAC()
        self._lanzar_excepciones_dominio: bool = lanzar_excepciones_dominio

    def __call__(
        self,
        comando: AsignarDocenteComando,
        *,
        lanzar_excepciones_dominio: Optional[bool] = None,
    ) -> AsignacionDocenteRespuestaDTO:
        """Permite invocar la instancia del caso de uso como función callable."""
        return self.ejecutar(
            comando,
            lanzar_excepciones_dominio=lanzar_excepciones_dominio,
        )

    def ejecutar(
        self,
        comando: AsignarDocenteComando,
        *,
        lanzar_excepciones_dominio: Optional[bool] = None,
    ) -> AsignacionDocenteRespuestaDTO:
        """Ejecuta la asignación de docente asesor a la práctica.

        Args:
            comando: DTO inmutable con identificadores de práctica, docente y contexto RBAC.
            lanzar_excepciones_dominio: Sobrescribe la política de excepciones del init.

        Returns:
            AsignacionDocenteRespuestaDTO confirmando la asignación o denegación.

        Raises:
            AccesoDenegadoError: Si el usuario no cuenta con rol de Coordinador (EAC-03).
            PracticaNoEncontradaError: Si la práctica especificada no existe.
            PracticaYaTieneTutorAsignadoError: Si la práctica ya cuenta con docente asesor asignado.
            TransicionEstadoInvalidaError: Si la práctica no se encuentra en estado 'Aprobada'.
            DocenteAsesorNoEncontradoError: Si el docente no existe o se encuentra inactivo.
            CupoDocenteExcedidoError: Si el docente ha alcanzado su cupo máximo de prácticas.
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
            self._autorizador_rbac.autorizar_comando_asignacion(comando)
        except AccesoDenegadoError as error_rbac:
            # EAC-03: Registrar de inmediato el intento no autorizado en la bitácora
            # con IP, fecha y hora, asegurando 0 datos expuestos de la práctica y tutor
            self._registrar_bitacora(
                actor_id=comando.actor_id,
                rol=comando.rol_actor,
                ip=comando.ip_origen,
                accion="Intento no autorizado de asignación de docente asesor",
                entidad="ModuloPostulaciones",
                detalles={
                    "operacion": "asignar_tutor",
                    "diagnostico": str(error_rbac),
                },
            )
            if debe_lanzar:
                raise error_rbac
            return AsignacionDocenteRespuestaDTO.denegada(
                practica_id=comando.practica_id,
                estado_actual="Desconocido",
                mensaje=str(error_rbac),
            )

        # -------------------------------------------------------------------
        # 2. Recuperación y validación de existencia de la práctica
        # -------------------------------------------------------------------
        practica: Optional[Practica] = self._repositorio_practica.buscar_por_id(
            comando.practica_id
        )
        if practica is None:
            if debe_lanzar:
                raise PracticaNoEncontradaError(practica_id=comando.practica_id)
            return AsignacionDocenteRespuestaDTO.denegada(
                practica_id=comando.practica_id,
                estado_actual="Inexistente",
                mensaje=f"No se encontró ninguna práctica con ID '{comando.practica_id}'.",
            )

        # -------------------------------------------------------------------
        # 3. Validación de precondiciones de estado en la Práctica (ADR-010)
        # -------------------------------------------------------------------
        if practica.docente_asesor_id is not None or practica.estado_actual == EstadoPractica.ASIGNADA:
            error_ya_asignada = PracticaYaTieneTutorAsignadoError(
                practica_id=practica.id,
                docente_asesor_id=practica.docente_asesor_id,
            )
            if debe_lanzar:
                raise error_ya_asignada
            return AsignacionDocenteRespuestaDTO.denegada(
                practica_id=practica.id,
                estado_actual=practica.estado_actual.value,
                mensaje=str(error_ya_asignada),
                docente_asesor_id=practica.docente_asesor_id,
            )

        if practica.estado_actual != EstadoPractica.APROBADA:
            error_estado = TransicionEstadoInvalidaError(
                estado_origen=practica.estado_actual.value,
                estado_destino=EstadoPractica.ASIGNADA.value,
                practica_id=practica.id,
                mensaje=(
                    f"Solo se puede asignar un docente asesor a prácticas que se encuentren "
                    f"en estado 'Aprobada' (estado actual: '{practica.estado_actual.value}')."
                ),
            )
            if debe_lanzar:
                raise error_estado
            return AsignacionDocenteRespuestaDTO.denegada(
                practica_id=practica.id,
                estado_actual=practica.estado_actual.value,
                mensaje=str(error_estado),
            )

        # -------------------------------------------------------------------
        # 4. Recuperación y validación del DocenteAsesor
        # -------------------------------------------------------------------
        docente: Optional[DocenteAsesor] = self._repositorio_docente.buscar_por_id(
            comando.docente_asesor_id
        )
        if docente is None or not docente.activo:
            error_docente = DocenteAsesorNoEncontradoError(docente_id=comando.docente_asesor_id)
            if debe_lanzar:
                raise error_docente
            return AsignacionDocenteRespuestaDTO.denegada(
                practica_id=practica.id,
                estado_actual=practica.estado_actual.value,
                mensaje=str(error_docente),
            )

        # -------------------------------------------------------------------
        # 5. Validación de disponibilidad de cupo (RT-01)
        # -------------------------------------------------------------------
        if not docente.tiene_cupo_disponible():
            error_cupo = CupoDocenteExcedidoError(
                docente_id=docente.id,
                cupo_maximo=docente.cupo_maximo_practicas,
                practicas_activas=docente.practicas_activas,
            )
            if debe_lanzar:
                raise error_cupo
            return AsignacionDocenteRespuestaDTO.denegada(
                practica_id=practica.id,
                estado_actual=practica.estado_actual.value,
                mensaje=str(error_cupo),
            )

        # -------------------------------------------------------------------
        # 6. Ejecución de la asignación en el Dominio (ADR-010)
        # -------------------------------------------------------------------
        practica.asignar_tutor(docente.id)
        docente.asignar_practica()

        # -------------------------------------------------------------------
        # 7. Persistencia transaccional de práctica y docente (ADR-003)
        # -------------------------------------------------------------------
        self._repositorio_practica.actualizar(practica)
        self._repositorio_docente.actualizar(docente)

        # -------------------------------------------------------------------
        # 8. Registro inmutable de auditoría en la Bitácora (ADR-006)
        # -------------------------------------------------------------------
        detalles_bitacora: dict[str, Any] = {
            "practica_id": practica.id,
            "estudiante_id": practica.estudiante_id,
            "docente_asesor_id": docente.id,
            "coordinador_id": comando.actor_id,
            "nuevo_estado": EstadoPractica.ASIGNADA.value,
            "practicas_activas_docente": docente.practicas_activas,
            "cupo_maximo_docente": docente.cupo_maximo_practicas,
        }

        self._registrar_bitacora(
            actor_id=comando.actor_id,
            rol=comando.rol_actor,
            ip=comando.ip_origen,
            accion="Asignación de docente asesor",
            entidad=f"Practica:{practica.id}",
            detalles=detalles_bitacora,
        )

        # -------------------------------------------------------------------
        # 9. Notificaciones por correo institucional a estudiante y docente
        # -------------------------------------------------------------------
        self._notificar_estudiante(practica=practica, docente=docente)
        self._notificar_docente(practica=practica, docente=docente)

        # -------------------------------------------------------------------
        # 10. Retorno de respuesta estructurada
        # -------------------------------------------------------------------
        return AsignacionDocenteRespuestaDTO.exitosa(
            practica_id=practica.id,
            docente_asesor_id=docente.id,
            mensaje=f"Docente asesor '{docente.nombre_completo}' asignado exitosamente a la práctica.",
            detalles=detalles_bitacora,
        )

    # -----------------------------------------------------------------------
    # Métodos privados de apoyo
    # -----------------------------------------------------------------------

    def _notificar_estudiante(
        self,
        *,
        practica: Practica,
        docente: DocenteAsesor,
    ) -> bool:
        """Despacha la notificación por correo institucional al estudiante titular."""
        destinatario = (
            practica.estudiante_id
            if "@" in practica.estudiante_id
            else f"{practica.estudiante_id}@universidad.edu.co"
        )
        asunto = f"Asignación de docente asesor - Práctica {practica.id}"
        cuerpo = (
            f"Estimado/a estudiante:\n\n"
            f"Nos complace informarle que le ha sido asignado formalmente su docente asesor "
            f"para la práctica empresarial con identificador '{practica.id}'.\n\n"
            f"Datos del tutor académico responsable:\n"
            f"- Nombre: {docente.nombre_completo}\n"
            f"- Correo institucional: {docente.correo_institucional}\n\n"
            f"La práctica se encuentra ahora en estado 'Asignada'. "
            f"Por favor contacte a su tutor para iniciar las coordinaciones iniciales.\n\n"
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

    def _notificar_docente(
        self,
        *,
        practica: Practica,
        docente: DocenteAsesor,
    ) -> bool:
        """Despacha la notificación por correo institucional al docente asesor."""
        asunto = f"Nueva práctica asignada bajo su tutoría - Práctica {practica.id}"
        cuerpo = (
            f"Estimado/a profesor/a {docente.nombre_completo}:\n\n"
            f"Le informamos que se le ha asignado una nueva práctica empresarial bajo su tutoría académica:\n"
            f"- Identificador de práctica: {practica.id}\n"
            f"- Identificador de estudiante: {practica.estudiante_id}\n"
            f"- Prácticas activas asignadas a la fecha: {docente.practicas_activas} de {docente.cupo_maximo_practicas}\n\n"
            f"Atentamente,\n"
            f"Coordinación de Prácticas Empresariales"
        )
        try:
            self._servicio_correo.enviar_notificacion(
                destinatario=docente.correo_institucional,
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
