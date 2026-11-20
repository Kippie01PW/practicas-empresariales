"""Caso de uso: Aprobar el acta electrónicamente (CU-10).

Traza: CU-10, EAC-03, OB-05, PA-03, RN-01, RN-02, RN-03,
ADR-001 (Resiliencia e integración asíncrona),
ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores),
ADR-003 (Persistencia transaccional),
ADR-004 (Autenticación híbrida),
ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso),
ADR-006 (Bitácora de auditoría transaccional Append-Only),
ADR-008 (Generación y preservación del acta final con sellado criptográfico SHA-256),
ADR-010 (Máquina de estados finitos),
Vista Lógica §2 (01-logica.md), Vista de Desarrollo §3 (03-desarrollo.md)
y Escenario +1 ESC-04 (docs/diagramas/secuencias/cu10-aprobar-acta.puml).

Orquesta el proceso secuencial de firma y aprobación electrónica del ActaFinal:
1. Paso 1 (`DocenteAsesor` asignado):
   - Valida identidad institucional y rol `DocenteAsesor` bajo política *deny-by-default* (ADR-004, ADR-005).
   - Verifica la pertenencia contextual del docente frente a la práctica (`practica.docente_asesor_id`, RN-01).
   - Comprueba que la `Practica` esté en estado `Evaluada`, cuente con un `ActaFinal` generada y que la firma
     del docente no haya sido asentada previamente (ADR-010, RN-02).
   - Recalcula la huella criptográfica SHA-256 del documento PDF almacenado y verifica que coincida con
     `acta.hash_integridad_sha256` (ADR-008, PA-03). Si hay discrepancia, registra alerta en bitácora y bloquea.
   - Marca `aprobadaPorDocente = True`, mantiene la `Practica` en estado `Evaluada` e inserta atómicamente
     el `EventoBitacora` inmutable con huella digital SHA-256 (ADR-003, ADR-006).
2. Paso 2 (`Coordinador de prácticas`):
   - Valida identidad institucional y rol `Coordinador de prácticas` bajo política *deny-by-default* (ADR-004, ADR-005).
   - Comprueba que la `Practica` esté en estado `Evaluada`, cuente con un `ActaFinal` generada, que el
     `DocenteAsesor` ya haya firmado previamente (`aprobadaPorDocente == True`, RN-02) y que el coordinador
     no haya firmado antes.
   - Verifica la integridad criptográfica SHA-256 del binario PDF frente a `acta.hash_integridad_sha256` (ADR-008).
   - En una operación atómica: marca `aprobadaPorCoordinador = True` (quedando el acta en firme), transiciona
     la `Practica` de `Evaluada` a `Completada` (ADR-010), decrementa en 1 el contador `practicasActivas`
     del `DocenteAsesor` asignado liberando su cupo disponible, e inserta el `EventoBitacora` inmutable de cierre.
   - Publica de forma asíncrona el evento `ActaFinalEmitida` en el bróker y despacha la notificación por correo
     electrónico al `Estudiante` titular adjuntando/enlazando el `ActaFinal` en PDF (ADR-001, OB-05).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from aplicacion.dtos.aprobacion_acta_dto import (
    AprobacionActaRespuestaDTO,
    AprobarActaComando,
)
from aplicacion.puertos.publicador_eventos import (
    ErrorPublicacionEvento,
    EventoActaFinalEmitida,
    PublicadorEventosPort,
)
from aplicacion.puertos.repositorio_acta_final import RepositorioActaFinalPort
from aplicacion.puertos.repositorio_docente import RepositorioDocentePort
from aplicacion.puertos.repositorio_practica import RepositorioPracticaPort
from aplicacion.puertos.servicio_correo import (
    ErrorServicioCorreo,
    ServicioCorreoPort,
)
from aplicacion.puertos.servicio_pdf_hash import ServicioPdfHashPort
from aplicacion.seguridad.autorizador_rbac import (
    AccesoDenegadoError,
    AutorizadorRBAC,
    ContextoUsuario,
)
from dominio.errores import (
    ActaFinalNoEncontradaError,
    ActaYaAprobadaPorActorError,
    EstadoPracticaInvalidoParaAprobarActaError,
    FaltaAprobacionDocentePreviaError,
    IntegridadActaInvalidaError,
    PracticaNoEncontradaError,
)
from dominio.modelos.acta_final import ActaFinal
from dominio.modelos.docente_asesor import DocenteAsesor
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.practica import EstadoPractica, Practica


class AprobarActaElectronicamenteCasoUso:
    """Caso de uso para aprobar y firmar electrónicamente en orden secuencial el ActaFinal (CU-10).

    Pertenece al `Módulo Actas` en la capa de Aplicación (`docs/vistas/03-desarrollo.md`).
    """

    def __init__(
        self,
        *,
        repositorio_practica: RepositorioPracticaPort,
        repositorio_acta_final: RepositorioActaFinalPort,
        repositorio_docente: RepositorioDocentePort,
        servicio_pdf_hash: ServicioPdfHashPort,
        autorizador_rbac: Optional[AutorizadorRBAC] = None,
        publicador_eventos: Optional[PublicadorEventosPort] = None,
        servicio_correo: Optional[ServicioCorreoPort] = None,
    ) -> None:
        """Inicializa el caso de uso con sus puertos y colaboradores inyectados.

        Args:
            repositorio_practica: Puerto de persistencia de prácticas y bitácora Append-Only.
            repositorio_acta_final: Puerto de persistencia y consulta de entidades ActaFinal.
            repositorio_docente: Puerto de persistencia y consulta de DocenteAsesor (liberación de cupo).
            servicio_pdf_hash: Puerto para lectura de binarios PDF y recálculo de huella SHA-256.
            autorizador_rbac: Componente centralizado de control de acceso RBAC (deny-by-default).
            publicador_eventos: Puerto opcional hacia el bróker de mensajería para publicar ActaFinalEmitida.
            servicio_correo: Puerto opcional hacia el servidor SMTP para notificar al Estudiante.
        """
        self._repositorio_practica: RepositorioPracticaPort = repositorio_practica
        self._repositorio_acta_final: RepositorioActaFinalPort = repositorio_acta_final
        self._repositorio_docente: RepositorioDocentePort = repositorio_docente
        self._servicio_pdf_hash: ServicioPdfHashPort = servicio_pdf_hash
        self._autorizador_rbac: AutorizadorRBAC = autorizador_rbac or AutorizadorRBAC()
        self._publicador_eventos: Optional[PublicadorEventosPort] = publicador_eventos
        self._servicio_correo: Optional[ServicioCorreoPort] = servicio_correo

    def __call__(
        self,
        comando: AprobarActaComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> AprobacionActaRespuestaDTO:
        """Permite invocar la instancia del caso de uso como un objeto callable."""
        return self.ejecutar(comando=comando, contexto=contexto)

    def ejecutar(
        self,
        comando: AprobarActaComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> AprobacionActaRespuestaDTO:
        """Ejecuta la aprobación electrónica del ActaFinal por DocenteAsesor o Coordinador de prácticas.

        Args:
            comando: DTO inmutable `AprobarActaComando` con `practica_id`, `actor_id`, `rol_actor`,
                `acta_id` opcional e `ip_origen`.
            contexto: Contexto opcional de sesión institucional `ContextoUsuario`. Si no se provee,
                se construye y valida a partir de los atributos del comando.

        Returns:
            `AprobacionActaRespuestaDTO` con el estado resultante del `ActaFinal`, de la `Practica`
            y del cupo del `DocenteAsesor`.

        Raises:
            AccesoDenegadoError: Si el actor carece de identidad institucional válida, tiene un rol
                no autorizado (Escenarios 8 y 9) o es un DocenteAsesor no asignado a la práctica (Escenario 7).
            PracticaNoEncontradaError: Si la práctica indicada no existe.
            ActaYaAprobadaPorActorError: Si la firma electrónica del rol ya fue asentada previamente
                o la práctica ya se encuentra en estado Completada (Escenario 6).
            EstadoPracticaInvalidoParaAprobarActaError: Si la práctica no se encuentra en estado
                Evaluada (Escenario 5).
            ActaFinalNoEncontradaError: Si la práctica no cuenta con un ActaFinal generada (Escenario 5).
            FaltaAprobacionDocentePreviaError: Si el Coordinador de prácticas intenta aprobar antes
                de que el DocenteAsesor asignado haya firmado el acta (Escenario 3).
            IntegridadActaInvalidaError: Si el hash SHA-256 recalculado del archivo PDF no coincide
                con el hashIntegridadSha256 registrado o el archivo fue alterado/corrompido (Escenario 4).
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
                f"ActaFinal:{comando.acta_id.strip()}"
                if comando.acta_id and str(comando.acta_id).strip()
                else "ModuloActas"
            )
        )

        # -------------------------------------------------------------------
        # 1. Autenticación y Autorización RBAC deny-by-default (ADR-004, ADR-005, EAC-03)
        # -------------------------------------------------------------------
        try:
            if not actor_id_raw or not str(actor_id_raw).strip():
                raise AccesoDenegadoError(
                    "Acceso denegado: No se ha provisto una sesión o identificador de usuario institucional válido.",
                    rol_actor=rol_actor_raw,
                    operacion="aprobar_acta",
                    usuario_id=actor_id_raw,
                )

            operacion_autorizada = self._autorizador_rbac.validar_aprobacion_acta(
                rol_actor=rol_actor_raw,
                usuario_id=str(actor_id_raw).strip(),
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
                    operacion="aprobar_acta",
                    usuario_id=actor_id_raw,
                )
            )
            self._registrar_bitacora(
                actor_id=str(actor_id_raw).strip() if actor_id_raw and str(actor_id_raw).strip() else "ANONIMO",
                rol=str(rol_actor_raw).strip() if rol_actor_raw and str(rol_actor_raw).strip() else "SIN_ROL",
                ip=str(ip_origen).strip() if ip_origen and str(ip_origen).strip() else "127.0.0.1",
                accion="Intento de aprobación electrónica de acta por rol o sesión no autorizada",
                entidad=entidad_referencia,
                detalles={
                    "operacion": "aprobar_acta",
                    "practica_id": comando.practica_id,
                    "acta_id": comando.acta_id,
                    "motivo": str(error_denegado),
                },
            )
            raise error_denegado

        # -------------------------------------------------------------------
        # 2. Recuperación de la Práctica y validación de pertenencia contextual (RN-01, ADR-005)
        # -------------------------------------------------------------------
        practica: Optional[Practica] = None
        acta_por_id: Optional[ActaFinal] = None

        if comando.practica_id and str(comando.practica_id).strip():
            practica = self._repositorio_practica.buscar_por_id(str(comando.practica_id).strip())

        if practica is None and comando.acta_id and str(comando.acta_id).strip():
            acta_por_id = self._repositorio_acta_final.buscar_por_id(str(comando.acta_id).strip())
            if acta_por_id is not None:
                practica = self._repositorio_practica.buscar_por_id(acta_por_id.practica_id)

        if practica is None:
            raise PracticaNoEncontradaError(
                practica_id=str(comando.practica_id).strip() if comando.practica_id else (comando.acta_id or "")
            )

        if operacion_autorizada == "aprobar_acta_docente":
            try:
                self._autorizador_rbac.validar_pertenencia_docente(
                    contexto=contexto_efectivo,
                    docente_asignado_id=practica.docente_asesor_id,
                    operacion="aprobar_acta_docente",
                )
            except AccesoDenegadoError as error_pertenencia:
                self._registrar_bitacora(
                    actor_id=contexto_efectivo.usuario_id,
                    rol=contexto_efectivo.rol,
                    ip=contexto_efectivo.ip_origen,
                    accion="Intento de acceso y aprobación electrónica de acta sobre práctica ajena",
                    entidad=f"Practica:{practica.id}",
                    detalles={
                        "operacion": "aprobar_acta_docente",
                        "practica_id": practica.id,
                        "motivo": str(error_pertenencia),
                    },
                )
                raise error_pertenencia

        # -------------------------------------------------------------------
        # 3. Verificación de existencia de ActaFinal, duplicidad y máquina de estados (ADR-010, RN-02)
        # -------------------------------------------------------------------
        acta: Optional[ActaFinal] = self._repositorio_acta_final.buscar_por_practica(practica.id)
        if acta is None and acta_por_id is not None and acta_por_id.practica_id == practica.id:
            acta = acta_por_id

        # Escenario 6: Si la firma del actor ya fue asentada previamente o la práctica ya está Completada
        if practica.estado_actual == EstadoPractica.COMPLETADA:
            raise ActaYaAprobadaPorActorError(
                rol_actor=contexto_efectivo.rol,
                actor_id=contexto_efectivo.usuario_id,
                practica_id=practica.id,
                acta_id=acta.id if acta is not None else comando.acta_id,
                estado_actual=practica.estado_actual.value,
            )

        if acta is not None:
            if operacion_autorizada == "aprobar_acta_docente" and acta.aprobada_por_docente:
                raise ActaYaAprobadaPorActorError(
                    rol_actor=contexto_efectivo.rol,
                    actor_id=contexto_efectivo.usuario_id,
                    practica_id=practica.id,
                    acta_id=acta.id,
                    estado_actual=practica.estado_actual.value,
                )
            if operacion_autorizada == "aprobar_acta_coordinador" and acta.aprobada_por_coordinador:
                raise ActaYaAprobadaPorActorError(
                    rol_actor=contexto_efectivo.rol,
                    actor_id=contexto_efectivo.usuario_id,
                    practica_id=practica.id,
                    acta_id=acta.id,
                    estado_actual=practica.estado_actual.value,
                )

        # Escenario 5: La práctica debe estar en estado Evaluada y contar con ActaFinal generada
        if not practica.puede_aprobar_acta():
            raise EstadoPracticaInvalidoParaAprobarActaError(
                practica_id=practica.id,
                estado_actual=practica.estado_actual.value,
            )

        if acta is None:
            raise ActaFinalNoEncontradaError(
                practica_id=practica.id,
                acta_id=comando.acta_id,
            )

        # Si se especificó acta_id en el comando, validar que corresponda al acta de la práctica
        if comando.acta_id and str(comando.acta_id).strip() and acta.id != str(comando.acta_id).strip():
            raise ActaFinalNoEncontradaError(
                practica_id=practica.id,
                acta_id=str(comando.acta_id).strip(),
            )

        # Escenario 3: Si es Coordinador de prácticas y el DocenteAsesor aún no ha firmado,
        # denegar por incumplimiento de secuencia obligatoria de firmas (break en cu10-aprobar-acta.puml)
        if operacion_autorizada == "aprobar_acta_coordinador" and not acta.aprobada_por_docente:
            raise FaltaAprobacionDocentePreviaError(
                practica_id=practica.id,
                acta_id=acta.id,
                docente_asesor_id=practica.docente_asesor_id,
            )

        # -------------------------------------------------------------------
        # 4. Verificación de integridad criptográfica SHA-256 del binario PDF (ADR-008, PA-03)
        # -------------------------------------------------------------------
        try:
            hash_recalculado = self._servicio_pdf_hash.recalcular_hash_archivo(acta.ruta_archivo_pdf)
            acta.verificar_integridad_hash(hash_recalculado)
        except IntegridadActaInvalidaError as error_integridad:
            self._registrar_bitacora(
                actor_id=contexto_efectivo.usuario_id,
                rol=contexto_efectivo.rol,
                ip=contexto_efectivo.ip_origen,
                accion="Alerta de seguridad por fallo de integridad SHA-256 del ActaFinal",
                entidad=f"Practica:{practica.id}",
                detalles={
                    "acta_id": acta.id,
                    "numero_acta": acta.numero_acta,
                    "practica_id": practica.id,
                    "ruta_archivo_pdf": acta.ruta_archivo_pdf,
                    "hash_esperado": error_integridad.hash_esperado,
                    "hash_recalculado": error_integridad.hash_recalculado,
                    "motivo": str(error_integridad),
                },
            )
            raise error_integridad
        except Exception as error_lectura_pdf:
            error_integridad = IntegridadActaInvalidaError(
                acta_id=acta.id,
                practica_id=practica.id,
                hash_esperado=acta.hash_integridad_sha256,
                hash_recalculado=None,
            )
            self._registrar_bitacora(
                actor_id=contexto_efectivo.usuario_id,
                rol=contexto_efectivo.rol,
                ip=contexto_efectivo.ip_origen,
                accion="Alerta de seguridad por fallo de integridad SHA-256 del ActaFinal",
                entidad=f"Practica:{practica.id}",
                detalles={
                    "acta_id": acta.id,
                    "numero_acta": acta.numero_acta,
                    "practica_id": practica.id,
                    "ruta_archivo_pdf": acta.ruta_archivo_pdf,
                    "hash_esperado": acta.hash_integridad_sha256,
                    "hash_recalculado": None,
                    "causa": str(error_lectura_pdf),
                    "motivo": str(error_integridad),
                },
            )
            raise error_integridad from error_lectura_pdf

        # -------------------------------------------------------------------
        # 5. Ejecución del Paso 1 (DocenteAsesor) o Paso 2 (Coordinador de prácticas)
        # -------------------------------------------------------------------
        ahora = datetime.now()

        if operacion_autorizada == "aprobar_acta_docente":
            # Paso 1 (Escenario 1): Aprobación electrónica por el Docente asesor asignado
            acta.aprobar_por_docente(
                docente_id=contexto_efectivo.usuario_id,
                fecha_aprobacion=ahora,
            )
            self._repositorio_acta_final.actualizar(acta)

            docente_actual: Optional[DocenteAsesor] = None
            if practica.docente_asesor_id:
                docente_actual = self._repositorio_docente.buscar_por_id(practica.docente_asesor_id)

            self._registrar_bitacora(
                actor_id=contexto_efectivo.usuario_id,
                rol=contexto_efectivo.rol,
                ip=contexto_efectivo.ip_origen,
                accion="Aprobación electrónica de acta por docente asesor",
                entidad=f"Practica:{practica.id}",
                fecha_hora=ahora,
                detalles={
                    "acta_id": acta.id,
                    "numero_acta": acta.numero_acta,
                    "practica_id": practica.id,
                    "estudiante_id": practica.estudiante_id,
                    "docente_asesor_id": contexto_efectivo.usuario_id,
                    "hash_integridad_sha256": acta.hash_integridad_sha256,
                    "aprobada_por_docente": acta.aprobada_por_docente,
                    "aprobada_por_coordinador": acta.aprobada_por_coordinador,
                    "estado_practica": practica.estado_actual.value,
                },
            )

            return AprobacionActaRespuestaDTO(
                acta_id=acta.id,
                numero_acta=acta.numero_acta,
                practica_id=practica.id,
                estado_practica=practica.estado_actual.value,
                aprobada_por_docente=acta.aprobada_por_docente,
                aprobada_por_coordinador=acta.aprobada_por_coordinador,
                acta_en_firme=acta.esta_en_firme,
                hash_integridad_sha256=acta.hash_integridad_sha256,
                ruta_archivo_pdf=acta.ruta_archivo_pdf,
                actor_aprobador_id=contexto_efectivo.usuario_id,
                rol_aprobador=contexto_efectivo.rol,
                cupo_docente_liberado=False,
                practicas_activas_docente=(
                    docente_actual.practicas_activas if docente_actual is not None else None
                ),
                fecha_aprobacion=ahora,
                mensaje=(
                    f"Aprobación electrónica del DocenteAsesor '{contexto_efectivo.usuario_id}' "
                    f"registrada exitosamente sobre el acta '{acta.numero_acta}'. "
                    f"La práctica permanece en estado 'Evaluada' a la espera de la aprobación final "
                    f"del Coordinador de prácticas."
                ),
            )

        # Paso 2 (Escenario 2): Aprobación electrónica final por el Coordinador de prácticas
        acta.aprobar_por_coordinador(
            coordinador_id=contexto_efectivo.usuario_id,
            fecha_aprobacion=ahora,
        )
        practica.completar(
            acta_en_firme=acta.esta_en_firme,
            fecha_fin=ahora,
        )

        cupo_liberado = False
        practicas_activas_docente: Optional[int] = None
        if practica.docente_asesor_id:
            docente_asignado = self._repositorio_docente.buscar_por_id(practica.docente_asesor_id)
            if docente_asignado is not None:
                cupo_previo = docente_asignado.practicas_activas
                docente_asignado.liberar_practica()
                self._repositorio_docente.actualizar(docente_asignado)
                practicas_activas_docente = docente_asignado.practicas_activas
                cupo_liberado = docente_asignado.practicas_activas < cupo_previo

        self._repositorio_acta_final.actualizar(acta)
        self._repositorio_practica.actualizar(practica)

        self._registrar_bitacora(
            actor_id=contexto_efectivo.usuario_id,
            rol=contexto_efectivo.rol,
            ip=contexto_efectivo.ip_origen,
            accion="Aprobación electrónica final de acta y cierre de práctica",
            entidad=f"Practica:{practica.id}",
            fecha_hora=ahora,
            detalles={
                "acta_id": acta.id,
                "numero_acta": acta.numero_acta,
                "practica_id": practica.id,
                "estudiante_id": practica.estudiante_id,
                "docente_asesor_id": practica.docente_asesor_id,
                "coordinador_id": contexto_efectivo.usuario_id,
                "hash_integridad_sha256": acta.hash_integridad_sha256,
                "aprobada_por_docente": acta.aprobada_por_docente,
                "aprobada_por_coordinador": acta.aprobada_por_coordinador,
                "acta_en_firme": acta.esta_en_firme,
                "nuevo_estado_practica": practica.estado_actual.value,
                "cupo_docente_liberado": cupo_liberado,
                "practicas_activas_docente": practicas_activas_docente,
            },
        )

        # Publicación de evento asíncrono ActaFinalEmitida y notificación por correo al Estudiante (ADR-001, OB-05)
        self._publicar_evento_acta_emitida(practica=practica, acta=acta, fecha_emision=ahora)
        self._notificar_estudiante_cierre(practica=practica, acta=acta)

        return AprobacionActaRespuestaDTO(
            acta_id=acta.id,
            numero_acta=acta.numero_acta,
            practica_id=practica.id,
            estado_practica=practica.estado_actual.value,
            aprobada_por_docente=acta.aprobada_por_docente,
            aprobada_por_coordinador=acta.aprobada_por_coordinador,
            acta_en_firme=acta.esta_en_firme,
            hash_integridad_sha256=acta.hash_integridad_sha256,
            ruta_archivo_pdf=acta.ruta_archivo_pdf,
            actor_aprobador_id=contexto_efectivo.usuario_id,
            rol_aprobador=contexto_efectivo.rol,
            cupo_docente_liberado=cupo_liberado,
            practicas_activas_docente=practicas_activas_docente,
            fecha_aprobacion=ahora,
            mensaje=(
                f"Aprobación electrónica final del Coordinador de prácticas '{contexto_efectivo.usuario_id}' "
                f"registrada exitosamente. El acta '{acta.numero_acta}' ha quedado oficialmente en firme "
                f"y la práctica '{practica.id}' ha culminado en estado 'Completada'."
            ),
        )

    # -----------------------------------------------------------------------
    # Métodos privados de apoyo (Bitácora Append-Only, Bróker y Correo)
    # -----------------------------------------------------------------------

    def _publicar_evento_acta_emitida(
        self,
        *,
        practica: Practica,
        acta: ActaFinal,
        fecha_emision: datetime,
    ) -> bool:
        """Publica de forma resiliente el evento ActaFinalEmitida en el bróker (ADR-001)."""
        if self._publicador_eventos is None:
            return False
        try:
            evento = EventoActaFinalEmitida(
                practica_id=practica.id,
                acta_id=acta.id,
                numero_acta=acta.numero_acta,
                estudiante_id=practica.estudiante_id,
                ruta_archivo_pdf=acta.ruta_archivo_pdf,
                hash_integridad_sha256=acta.hash_integridad_sha256,
                fecha_emision=fecha_emision,
            )
            self._publicador_eventos.publicar_acta_final_emitida(evento)
            return True
        except (ErrorPublicacionEvento, Exception):
            # ADR-001: La transacción atómica de aprobación y cierre no se revierte por fallas transitorias del bróker
            return False

    def _notificar_estudiante_cierre(
        self,
        *,
        practica: Practica,
        acta: ActaFinal,
    ) -> bool:
        """Despacha la notificación asíncrona por correo electrónico al Estudiante titular (OB-05, ADR-001)."""
        if self._servicio_correo is None:
            return False

        destinatario = (
            practica.estudiante_id
            if "@" in practica.estudiante_id
            else f"{practica.estudiante_id}@universidad.edu.co"
        )
        asunto = f"Culminación oficial de práctica empresarial - Acta Final {acta.numero_acta}"
        cuerpo = (
            f"Estimado/a estudiante ({practica.estudiante_id}):\n\n"
            f"Le informamos que su práctica empresarial '{practica.id}' ha culminado exitosamente "
            f"y ha cambiado formalmente al estado 'Completada'.\n\n"
            f"Detalles del Acta Final oficial en firme:\n"
            f"- Número de acta: {acta.numero_acta}\n"
            f"- Identificador de acta: {acta.id}\n"
            f"- Documento PDF oficial: {acta.ruta_archivo_pdf}\n"
            f"- Huella criptográfica SHA-256: {acta.hash_integridad_sha256}\n"
            f"- Aprobada electrónicamente por Docente Asesor: {acta.docente_aprobador_id}\n"
            f"- Aprobada electrónicamente por Coordinador de Prácticas: {acta.coordinador_aprobador_id}\n\n"
            f"Atentamente,\n"
            f"Coordinación de Prácticas Empresariales - Universidad de Caldas"
        )
        try:
            self._servicio_correo.enviar_notificacion(
                destinatario=destinatario,
                asunto=asunto,
                cuerpo=cuerpo,
            )
            return True
        except (ErrorServicioCorreo, Exception):
            return False

    def _registrar_bitacora(
        self,
        *,
        actor_id: str,
        rol: str,
        ip: str,
        accion: str,
        entidad: str,
        fecha_hora: Optional[datetime] = None,
        detalles: Optional[dict[str, Any]] = None,
    ) -> None:
        """Inserta un registro inmutable EventoBitacora sellado con SHA-256 (ADR-006, EAC-03)."""
        evento = EventoBitacora(
            actor_identificador=actor_id or "ANONIMO",
            rol_actor=rol or "SIN_ROL",
            ip_origen=ip or "127.0.0.1",
            accion_realizada=accion,
            entidad_afectada=entidad,
            fecha_hora=fecha_hora,
            detalles=detalles,
        )
        self._repositorio_practica.guardar_evento_bitacora(evento)
