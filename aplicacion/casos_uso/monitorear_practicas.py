"""Caso de uso: Monitorear estado general de prácticas (CU-13).

Traza: CU-13, OB-01, OB-02, EAC-01, EAC-03, RT-01, RN-01, RN-02, RN-03,
ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores),
ADR-003 (Persistencia transaccional),
ADR-004 (Autenticación híbrida),
ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso),
ADR-006 (Bitácora de auditoría transaccional Append-Only),
ADR-007 (Configuración declarativa de reglas versionadas por programa),
ADR-008 (Generación y preservación del acta final con sellado criptográfico SHA-256),
ADR-010 (Máquina de estados finitos),
Vista Lógica §2 (01-logica.md) y Vista de Desarrollo §3 (03-desarrollo.md).

Implementa la consulta en un tablero de control centralizado y estrictamente de solo lectura
de los indicadores consolidados por estado del ciclo de vida, la ocupación de cupos de los
docentes asesores y el listado/detalle de prácticas restringido automáticamente al programa
académico del Coordinador de prácticas autenticado:
1. Autorización RBAC centralizada bajo política *deny-by-default* (ADR-004, ADR-005):
   - Operación exclusiva para el rol `Coordinador de prácticas` (`RolUsuario.COORDINADOR` / `RolUsuario.COORDINADOR_PRACTICAS`).
   - Cualquier intento de invocación por roles distintos (`Estudiante`, `DocenteAsesor`,
     `SupervisorEmpresa`, `SISTEMA` o usuarios sin sesión válida) es rechazado de inmediato
     con 0 datos expuestos y registro de un único `EventoBitacora` (Escenarios 7 y 8, EAC-03).
2. Validación estricta de pertenencia contextual por programa académico (*Context-Based Access Control*, RN-01):
   - El monitoreo general restringe automáticamente las prácticas consultadas únicamente al
     `programaAcademico` al que pertenece el coordinador autenticado, omitiendo cualquier
     práctica de otros programas académicos (Escenario 1).
   - Si el coordinador intenta consultar el detalle de una práctica perteneciente a un
     `programaAcademico` distinto al suyo o filtrar por un programa ajeno, el sistema deniega
     la operación con 0 datos expuestos y registra un único `EventoBitacora` (Escenario 5, EAC-03).
3. Filtrado y consolidación en modo solo lectura (ADR-007, ADR-008, ADR-010):
   - Permite filtrar dentro del programa académico del coordinador por documento del `Estudiante`
     (Escenario 2), `estadoActual` y/o `DocenteAsesor` asignado (Escenario 3), o retornar lista
     vacía con contadores en 0 cuando no existen coincidencias (Escenario 6).
   - Calcula el progreso individual de cada práctica frente a las `horasRequeridas` inmutables
     de la versión específica de `ReglaPrograma` vinculada al momento de su postulación,
     garantizando un 0% de alteración cuando coexisten prácticas del mismo programa bajo
     distintas versiones de regla (Escenario 9, EAC-01).
   - Consolida los indicadores de ocupación de cupo (`cupoMaximoPracticas`, `practicasActivas`
     y `cuposDisponibles`) de hasta 50 tutores y 500 estudiantes en concurrencia sin bloqueos
     transaccionales (Escenarios 1 y 10, RT-01).
4. Trazabilidad en bitácora Append-Only (ADR-006):
   - Registra un único `EventoBitacora` inmutable por cada consulta del tablero, consulta de
     detalle o intento de acceso denegado.
"""

from __future__ import annotations

from typing import Any, Optional

from aplicacion.dtos.monitoreo_practicas_dto import (
    ConsultarDetallePracticaMonitoreoComando,
    ConsultarMonitoreoPracticasComando,
    DetallePracticaMonitoreoRespuestaDTO,
    IndicadorCargaDocenteDTO,
    ItemPracticaMonitoreoDTO,
    TableroMonitoreoPracticasRespuestaDTO,
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


class MonitorearPracticasCasoUso:
    """Caso de uso del Módulo Postulaciones para monitorear el estado general de prácticas (CU-13)."""

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
            repositorio_docente: Puerto opcional de consulta de docentes asesores y disponibilidad de cupos.
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
        comando: ConsultarMonitoreoPracticasComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> TableroMonitoreoPracticasRespuestaDTO:
        """Permite invocar la instancia del caso de uso como un objeto callable."""
        return self.ejecutar(comando=comando, contexto=contexto)

    def ejecutar(
        self,
        comando: ConsultarMonitoreoPracticasComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> TableroMonitoreoPracticasRespuestaDTO:
        """Consulta en modo solo lectura el tablero de monitoreo general del programa académico del coordinador.

        Args:
            comando: DTO inmutable `ConsultarMonitoreoPracticasComando` con las credenciales del coordinador,
                su programa académico adscrito y los filtros opcionales de búsqueda.
            contexto: Contexto opcional de sesión institucional `ContextoUsuario`.

        Returns:
            `TableroMonitoreoPracticasRespuestaDTO` con el resumen cuantitativo por estado,
            indicadores de carga docente y listado consolidado de prácticas del programa.

        Raises:
            AccesoDenegadoError: Si el actor no tiene sesión válida, posee un rol distinto a
                `Coordinador de prácticas` (Escenarios 7 y 8) o intenta filtrar prácticas de
                un programa académico distinto al suyo (Escenario 5).
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
        programa_coordinador = (
            str(comando.programa_academico_coordinador).strip()
            if comando.programa_academico_coordinador
            else ""
        )
        entidad_referencia = (
            f"ProgramaAcademico:{programa_coordinador}"
            if programa_coordinador
            else "ModuloPostulaciones:MonitoreoPracticas"
        )

        # -------------------------------------------------------------------
        # 1. Verificación de rol exclusivo Coordinador de prácticas (deny-by-default, ADR-004, ADR-005, EAC-03)
        # -------------------------------------------------------------------
        try:
            if not actor_id_raw or not str(actor_id_raw).strip():
                raise AccesoDenegadoError(
                    "Acceso denegado: No se ha provisto una sesión o identificador de usuario institucional válido.",
                    rol_actor=rol_actor_raw,
                    operacion="monitorear_practicas",
                    usuario_id=actor_id_raw,
                )

            self._autorizador_rbac.validar_monitoreo_practicas(
                rol_actor=rol_actor_raw,
                usuario_id=str(actor_id_raw).strip(),
                operacion="monitorear_practicas",
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
                    operacion="monitorear_practicas",
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
                accion="ACCESO_DENEGADO_ROL_NO_AUTORIZADO_MONITOREO",
                entidad=entidad_referencia,
                detalles={
                    "operacion": "monitorear_practicas",
                    "programa_academico_coordinador": programa_coordinador,
                    "motivo": str(error_denegado),
                },
            )
            raise error_denegado

        # -------------------------------------------------------------------
        # 2. Validación de pertenencia contextual al programaAcademico del coordinador (RN-01, ADR-005, Escenario 5)
        # -------------------------------------------------------------------
        programa_objetivo_filtro = (
            comando.filtro_programa_academico
            if comando.filtro_programa_academico is not None
            else programa_coordinador
        )
        try:
            self._autorizador_rbac.validar_pertenencia_programa_coordinador(
                contexto=contexto_efectivo,
                programa_coordinador=programa_coordinador,
                programa_objetivo=programa_objetivo_filtro,
                operacion="monitorear_practicas",
            )
        except AccesoDenegadoError as error_programa:
            entidad_ajena = (
                f"ProgramaAcademico:{comando.filtro_programa_academico}"
                if comando.filtro_programa_academico
                else entidad_referencia
            )
            self._registrar_bitacora(
                actor_id=contexto_efectivo.usuario_id,
                rol=contexto_efectivo.rol,
                ip=contexto_efectivo.ip_origen,
                accion="ACCESO_DENEGADO_PROGRAMA_AJENO_MONITOREO",
                entidad=entidad_ajena,
                detalles={
                    "operacion": "monitorear_practicas",
                    "programa_academico_coordinador": programa_coordinador,
                    "filtro_programa_academico": comando.filtro_programa_academico,
                    "motivo": str(error_programa),
                },
            )
            raise error_programa

        # -------------------------------------------------------------------
        # 3. Filtrado automático por el programaAcademico del coordinador y criterios de búsqueda
        # -------------------------------------------------------------------
        todas_las_practicas: list[Practica] = self._repositorio_practica.listar_todas()
        cache_reglas: dict[str, Optional[ReglaPrograma]] = {}
        practicas_programa: list[tuple[Practica, ReglaPrograma]] = []

        programa_coord_norm = programa_coordinador.lower()
        for practica in todas_las_practicas:
            regla_id = practica.regla_programa_id
            if regla_id not in cache_reglas:
                cache_reglas[regla_id] = self._repositorio_regla.buscar_por_id(regla_id)
            regla = cache_reglas[regla_id]
            if regla is None:
                continue
            if regla.programa_academico.strip().lower() == programa_coord_norm:
                practicas_programa.append((practica, regla))

        total_practicas_programa: int = len(practicas_programa)

        # Aplicación de filtros opcionales dentro del programa del coordinador (Escenarios 2, 3 y 6)
        filtro_doc_est = (
            comando.filtro_documento_estudiante.strip()
            if comando.filtro_documento_estudiante
            else None
        )
        filtro_estado = (
            comando.filtro_estado_actual.strip()
            if comando.filtro_estado_actual
            else None
        )
        filtro_docente = (
            comando.filtro_docente_asesor_id.strip()
            if comando.filtro_docente_asesor_id
            else None
        )

        practicas_filtradas: list[tuple[Practica, ReglaPrograma]] = []
        for practica, regla in practicas_programa:
            if (
                filtro_doc_est is not None
                and practica.estudiante_id.strip() != filtro_doc_est
            ):
                continue
            if (
                filtro_estado is not None
                and practica.estado_actual.value.lower() != filtro_estado.lower()
            ):
                continue
            if filtro_docente is not None:
                tutor_actual = (
                    practica.docente_asesor_id.strip()
                    if practica.docente_asesor_id
                    else ""
                )
                if tutor_actual != filtro_docente:
                    continue
            practicas_filtradas.append((practica, regla))

        # -------------------------------------------------------------------
        # 4. Construcción de indicadores consolidados en modo solo lectura (ADR-007, ADR-008, ADR-010)
        # -------------------------------------------------------------------
        # 4.1. Resumen cuantitativo por los 8 estados formales de EstadoPractica
        resumen_por_estado: dict[str, int] = {
            estado.value: 0 for estado in EstadoPractica
        }
        for practica, _ in practicas_filtradas:
            resumen_por_estado[practica.estado_actual.value] += 1

        # 4.2. Indicadores de ocupación de cupo de DocenteAsesor (Escenarios 1 y 10, RT-01)
        mapa_docentes: dict[str, DocenteAsesor] = {}
        indicadores_docentes: list[IndicadorCargaDocenteDTO] = []
        if self._repositorio_docente is not None:
            for docente in self._repositorio_docente.listar_todos():
                mapa_docentes[docente.id] = docente
                if filtro_docente is not None and docente.id.strip() != filtro_docente:
                    continue
                indicadores_docentes.append(
                    IndicadorCargaDocenteDTO(
                        docente_asesor_id=docente.id,
                        documento=docente.documento,
                        nombre_completo=docente.nombre_completo,
                        correo_institucional=docente.correo_institucional,
                        cupo_maximo_practicas=docente.cupo_maximo_practicas,
                        practicas_activas=docente.practicas_activas,
                        cupos_disponibles=docente.cupo_disponible(),
                        activo=docente.activo,
                    )
                )

        # 4.3. Construcción de cada ItemPracticaMonitoreoDTO (Escenarios 1, 2, 3 y 9, EAC-01)
        items_monitoreo: list[ItemPracticaMonitoreoDTO] = []
        for practica, regla in practicas_filtradas:
            horas_requeridas: int = regla.horas_requeridas
            version_regla: str = str(regla.version)
            horas_acumuladas_aprobadas: int = practica.horas_acumuladas_aprobadas

            horas_pendientes_validacion: int = 0
            if self._repositorio_registro_horas is not None:
                registros: list[RegistroHoras] = (
                    self._repositorio_registro_horas.listar_por_practica(practica.id)
                )
                for reg in registros:
                    if reg.estado_validacion == EstadoValidacionHoras.PENDIENTE:
                        horas_pendientes_validacion += reg.cantidad_horas

            horas_restantes: int = max(0, horas_requeridas - horas_acumuladas_aprobadas)
            porcentaje_avance_horas: float = (
                round((horas_acumuladas_aprobadas / horas_requeridas) * 100.0, 2)
                if horas_requeridas > 0
                else 0.0
            )
            requisito_horas_cumplido: bool = (
                horas_acumuladas_aprobadas >= horas_requeridas
            )

            nombre_docente: Optional[str] = None
            if practica.docente_asesor_id:
                docente_asignado = mapa_docentes.get(practica.docente_asesor_id)
                if (
                    docente_asignado is None
                    and self._repositorio_docente is not None
                ):
                    docente_asignado = self._repositorio_docente.buscar_por_id(
                        practica.docente_asesor_id
                    )
                if docente_asignado is not None:
                    nombre_docente = docente_asignado.nombre_completo

            evaluacion_entidad: Optional[EvaluacionDesempeno] = None
            if self._repositorio_evaluacion is not None:
                evaluacion_entidad = self._repositorio_evaluacion.buscar_por_practica(
                    practica.id
                )

            acta_entidad: Optional[ActaFinal] = None
            if self._repositorio_acta_final is not None:
                acta_entidad = self._repositorio_acta_final.buscar_por_practica(
                    practica.id
                )

            items_monitoreo.append(
                ItemPracticaMonitoreoDTO(
                    practica_id=practica.id,
                    documento_estudiante=practica.estudiante_id,
                    programa_academico=regla.programa_academico,
                    regla_programa_id=regla.id,
                    version_regla=version_regla,
                    estado_actual=practica.estado_actual.value,
                    fecha_postulacion=practica.fecha_postulacion,
                    fecha_inicio=practica.fecha_inicio,
                    fecha_fin=practica.fecha_fin,
                    docente_asesor_id=practica.docente_asesor_id,
                    nombre_docente_asesor=nombre_docente,
                    supervisor_empresa_id=practica.supervisor_empresa_id,
                    horas_requeridas=horas_requeridas,
                    horas_acumuladas_aprobadas=horas_acumuladas_aprobadas,
                    horas_pendientes_validacion=horas_pendientes_validacion,
                    horas_restantes=horas_restantes,
                    porcentaje_avance_horas=porcentaje_avance_horas,
                    requisito_horas_cumplido=requisito_horas_cumplido,
                    evaluacion_realizada=(evaluacion_entidad is not None),
                    calificacion_cuantitativa=(
                        evaluacion_entidad.calificacion_cuantitativa
                        if evaluacion_entidad is not None
                        else None
                    ),
                    acta_generada=(acta_entidad is not None),
                    numero_acta=(
                        acta_entidad.numero_acta if acta_entidad is not None else None
                    ),
                    aprobada_por_docente=(
                        acta_entidad.aprobada_por_docente
                        if acta_entidad is not None
                        else False
                    ),
                    aprobada_por_coordinador=(
                        acta_entidad.aprobada_por_coordinador
                        if acta_entidad is not None
                        else False
                    ),
                    acta_en_firme=(
                        acta_entidad.esta_en_firme
                        if acta_entidad is not None
                        else False
                    ),
                )
            )

        total_practicas_filtradas: int = len(items_monitoreo)
        if total_practicas_filtradas == 0:
            mensaje = (
                f"No se encontraron prácticas registradas para los criterios consultados "
                f"en el programa académico '{programa_coordinador}'."
            )
        else:
            mensaje = (
                f"Tablero de monitoreo general de prácticas para el programa académico "
                f"'{programa_coordinador}': {total_practicas_filtradas} práctica(s) presentada(s) "
                f"de {total_practicas_programa} registrada(s) en el programa."
            )

        # -------------------------------------------------------------------
        # 5. Registro de un único EventoBitacora en modo solo lectura (ADR-006)
        # -------------------------------------------------------------------
        self._registrar_bitacora(
            actor_id=contexto_efectivo.usuario_id,
            rol=contexto_efectivo.rol,
            ip=contexto_efectivo.ip_origen,
            accion="CONSULTA_MONITOREO_PRACTICAS",
            entidad=f"ProgramaAcademico:{programa_coordinador}",
            detalles={
                "programa_academico": programa_coordinador,
                "total_practicas_programa": total_practicas_programa,
                "total_practicas_filtradas": total_practicas_filtradas,
                "filtro_documento_estudiante": filtro_doc_est,
                "filtro_estado_actual": filtro_estado,
                "filtro_docente_asesor_id": filtro_docente,
            },
        )

        # -------------------------------------------------------------------
        # 6. Retorno del DTO inmutable sin alterar ninguna entidad del dominio
        # -------------------------------------------------------------------
        return TableroMonitoreoPracticasRespuestaDTO(
            programa_academico=programa_coordinador,
            total_practicas_programa=total_practicas_programa,
            total_practicas_filtradas=total_practicas_filtradas,
            resumen_por_estado=resumen_por_estado,
            carga_docentes=tuple(indicadores_docentes),
            practicas=tuple(items_monitoreo),
            mensaje=mensaje,
        )

    def consultar_detalle_practica(
        self,
        comando: ConsultarDetallePracticaMonitoreoComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> DetallePracticaMonitoreoRespuestaDTO:
        """Consulta en modo solo lectura la trazabilidad completa de una práctica desde el tablero de monitoreo.

        Traza: CU-13, Escenarios 4, 5, 7 y 8, RN-01, RN-03, ADR-005, ADR-006, ADR-007, ADR-008, EAC-03.

        Args:
            comando: DTO inmutable `ConsultarDetallePracticaMonitoreoComando` con el identificador
                de la práctica, credenciales del coordinador y su programa académico adscrito.
            contexto: Contexto opcional de sesión institucional `ContextoUsuario`.

        Returns:
            `DetallePracticaMonitoreoRespuestaDTO` con la trazabilidad completa de la práctica.

        Raises:
            AccesoDenegadoError: Si el actor no posee rol `Coordinador de prácticas` (Escenarios 7 y 8)
                o si la práctica consultada pertenece a otro `programaAcademico` (Escenario 5).
            PracticaNoEncontradaError: Si el identificador de la práctica no existe en el sistema.
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
        programa_coordinador = (
            str(comando.programa_academico_coordinador).strip()
            if comando.programa_academico_coordinador
            else ""
        )
        practica_id_limpio = str(comando.practica_id).strip()
        entidad_referencia = f"Practica:{practica_id_limpio}"

        # -------------------------------------------------------------------
        # 1. Verificación de rol exclusivo Coordinador de prácticas (deny-by-default, ADR-004, ADR-005, EAC-03)
        # -------------------------------------------------------------------
        try:
            if not actor_id_raw or not str(actor_id_raw).strip():
                raise AccesoDenegadoError(
                    "Acceso denegado: No se ha provisto una sesión o identificador de usuario institucional válido.",
                    rol_actor=rol_actor_raw,
                    operacion="monitorear_practicas",
                    usuario_id=actor_id_raw,
                )

            self._autorizador_rbac.validar_monitoreo_practicas(
                rol_actor=rol_actor_raw,
                usuario_id=str(actor_id_raw).strip(),
                operacion="monitorear_practicas",
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
                    operacion="monitorear_practicas",
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
                accion="ACCESO_DENEGADO_ROL_NO_AUTORIZADO_MONITOREO",
                entidad=entidad_referencia,
                detalles={
                    "operacion": "consultar_detalle_practica_monitoreo",
                    "practica_id": practica_id_limpio,
                    "motivo": str(error_denegado),
                },
            )
            raise error_denegado

        # -------------------------------------------------------------------
        # 2. Búsqueda de la Práctica en el repositorio
        # -------------------------------------------------------------------
        practica: Optional[Practica] = self._repositorio_practica.buscar_por_id(
            practica_id_limpio
        )
        if practica is None:
            raise PracticaNoEncontradaError(practica_id=practica_id_limpio)

        # -------------------------------------------------------------------
        # 3. Validación de pertenencia contextual de la Práctica al programa del coordinador (RN-01, Escenario 5)
        # -------------------------------------------------------------------
        regla: Optional[ReglaPrograma] = self._repositorio_regla.buscar_por_id(
            practica.regla_programa_id
        )
        programa_practica: str = (
            regla.programa_academico.strip() if regla is not None else ""
        )

        try:
            self._autorizador_rbac.validar_pertenencia_programa_coordinador(
                contexto=contexto_efectivo,
                programa_coordinador=programa_coordinador,
                programa_objetivo=programa_practica,
                operacion="monitorear_practicas",
            )
        except AccesoDenegadoError as error_programa:
            self._registrar_bitacora(
                actor_id=contexto_efectivo.usuario_id,
                rol=contexto_efectivo.rol,
                ip=contexto_efectivo.ip_origen,
                accion="ACCESO_DENEGADO_PROGRAMA_AJENO_MONITOREO",
                entidad=f"Practica:{practica.id}",
                detalles={
                    "operacion": "consultar_detalle_practica_monitoreo",
                    "practica_id": practica.id,
                    "programa_academico_coordinador": programa_coordinador,
                    "programa_academico_practica": programa_practica,
                    "motivo": str(error_programa),
                },
            )
            raise error_programa

        # -------------------------------------------------------------------
        # 4. Recopilación en modo solo lectura de la trazabilidad completa de la Práctica (Escenario 4)
        # -------------------------------------------------------------------
        horas_requeridas: int = regla.horas_requeridas if regla is not None else 320
        version_regla: str = str(regla.version) if regla is not None else "1"
        horas_acumuladas_aprobadas: int = practica.horas_acumuladas_aprobadas

        nombre_docente: Optional[str] = None
        correo_docente: Optional[str] = None
        if practica.docente_asesor_id and self._repositorio_docente is not None:
            docente: Optional[DocenteAsesor] = self._repositorio_docente.buscar_por_id(
                practica.docente_asesor_id
            )
            if docente is not None:
                nombre_docente = docente.nombre_completo
                correo_docente = docente.correo_institucional

        horas_pendientes_validacion: int = 0
        cantidad_reportes_pendientes: int = 0
        if self._repositorio_registro_horas is not None:
            registros: list[RegistroHoras] = (
                self._repositorio_registro_horas.listar_por_practica(practica.id)
            )
            for reg in registros:
                if reg.estado_validacion == EstadoValidacionHoras.PENDIENTE:
                    horas_pendientes_validacion += reg.cantidad_horas
                    cantidad_reportes_pendientes += 1

        horas_restantes: int = max(0, horas_requeridas - horas_acumuladas_aprobadas)
        porcentaje_avance_horas: float = (
            round((horas_acumuladas_aprobadas / horas_requeridas) * 100.0, 2)
            if horas_requeridas > 0
            else 0.0
        )
        requisito_horas_cumplido: bool = horas_acumuladas_aprobadas >= horas_requeridas

        evaluacion_entidad: Optional[EvaluacionDesempeno] = None
        if self._repositorio_evaluacion is not None:
            evaluacion_entidad = self._repositorio_evaluacion.buscar_por_practica(
                practica.id
            )

        acta_entidad: Optional[ActaFinal] = None
        if self._repositorio_acta_final is not None:
            acta_entidad = self._repositorio_acta_final.buscar_por_practica(practica.id)

        intentos_sia: list[IntentoValidacion] = (
            self._repositorio_practica.buscar_intentos_por_practica(practica.id)
        )
        ultimo_resultado_sia: Optional[str] = (
            intentos_sia[-1].resultado_sia if intentos_sia else None
        )
        ultimo_detalle_sia: Optional[str] = (
            intentos_sia[-1].detalle_estado if intentos_sia else None
        )

        mensaje = (
            f"Detalle consolidado de la práctica '{practica.id}' en monitoreo general "
            f"(programa '{programa_practica}', estado '{practica.estado_actual.value}', "
            f"{horas_acumuladas_aprobadas}/{horas_requeridas} horas aprobadas)."
        )

        # -------------------------------------------------------------------
        # 5. Registro de un único EventoBitacora en modo solo lectura (ADR-006)
        # -------------------------------------------------------------------
        self._registrar_bitacora(
            actor_id=contexto_efectivo.usuario_id,
            rol=contexto_efectivo.rol,
            ip=contexto_efectivo.ip_origen,
            accion="CONSULTA_DETALLE_PRACTICA_MONITOREO",
            entidad=f"Practica:{practica.id}",
            detalles={
                "practica_id": practica.id,
                "documento_estudiante": practica.estudiante_id,
                "programa_academico": programa_practica,
                "estado_actual": practica.estado_actual.value,
                "horas_acumuladas_aprobadas": horas_acumuladas_aprobadas,
                "horas_requeridas": horas_requeridas,
                "evaluacion_realizada": (evaluacion_entidad is not None),
                "acta_generada": (acta_entidad is not None),
            },
        )

        return DetallePracticaMonitoreoRespuestaDTO(
            practica_id=practica.id,
            documento_estudiante=practica.estudiante_id,
            programa_academico=programa_practica,
            regla_programa_id=practica.regla_programa_id,
            version_regla=version_regla,
            estado_actual=practica.estado_actual.value,
            fecha_postulacion=practica.fecha_postulacion,
            fecha_inicio=practica.fecha_inicio,
            fecha_fin=practica.fecha_fin,
            docente_asesor_id=practica.docente_asesor_id,
            nombre_docente_asesor=nombre_docente,
            correo_docente_asesor=correo_docente,
            supervisor_empresa_id=practica.supervisor_empresa_id,
            horas_requeridas=horas_requeridas,
            horas_acumuladas_aprobadas=horas_acumuladas_aprobadas,
            horas_pendientes_validacion=horas_pendientes_validacion,
            horas_restantes=horas_restantes,
            porcentaje_avance_horas=porcentaje_avance_horas,
            cantidad_reportes_pendientes=cantidad_reportes_pendientes,
            requisito_horas_cumplido=requisito_horas_cumplido,
            motivo_rechazo=practica.motivo_rechazo,
            evaluacion_realizada=(evaluacion_entidad is not None),
            calificacion_cuantitativa=(
                evaluacion_entidad.calificacion_cuantitativa
                if evaluacion_entidad is not None
                else None
            ),
            es_aprobatoria=(
                evaluacion_entidad.es_aprobatoria
                if evaluacion_entidad is not None
                else None
            ),
            observaciones_evaluacion=(
                evaluacion_entidad.observaciones
                if evaluacion_entidad is not None
                else None
            ),
            fecha_evaluacion=(
                evaluacion_entidad.fecha_evaluacion
                if evaluacion_entidad is not None
                else None
            ),
            acta_generada=(acta_entidad is not None),
            numero_acta=(
                acta_entidad.numero_acta if acta_entidad is not None else None
            ),
            fecha_emision_acta=(
                acta_entidad.fecha_emision if acta_entidad is not None else None
            ),
            aprobada_por_docente=(
                acta_entidad.aprobada_por_docente
                if acta_entidad is not None
                else False
            ),
            aprobada_por_coordinador=(
                acta_entidad.aprobada_por_coordinador
                if acta_entidad is not None
                else False
            ),
            acta_en_firme=(
                acta_entidad.esta_en_firme if acta_entidad is not None else False
            ),
            hash_integridad_sha256=(
                acta_entidad.hash_integridad_sha256
                if acta_entidad is not None
                else None
            ),
            ultimo_resultado_sia=ultimo_resultado_sia,
            ultimo_detalle_sia=ultimo_detalle_sia,
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
