"""Caso de uso: Migrar prácticas en curso desde Excel (CU-15).

Traza: CU-15, OB-02, RT-02, RN-01, RN-02, RN-03, PA-05, R-03, R-04, DT-04,
ADR-002 (Clean Architecture), ADR-003, ADR-005 (RBAC), ADR-006 (Bitácora Append-Only),
ADR-007 (Reglas versionadas), ADR-009 (Migración inicial CLI), ADR-010 (Máquina de estados).

Implementa en el Módulo Postulaciones el proceso único de validación e importación
desde una plantilla normalizada de Excel:
1. Autorización RBAC centralizada bajo política *deny-by-default* exclusiva para
   el rol `Administrador DBA` (Escenario 8, ADR-005). Todo intento no autorizado
   registra un `EventoBitacora` de rechazo en < 1 minuto y lanza `AccesoDenegadoError`
   sin modificar registros.
2. Lectura de filas mediante `LectorPlantillaExcelPort`.
3. Validación independiente por fila (Escenarios 1, 3, 4, 5, 6, 7):
   - Campos obligatorios y formatos de horas y fechas.
   - Detección de duplicados dentro del lote y frente al repositorio (omisión sin sobrescribir).
   - Verificación de `ReglaPrograma` activa vigente para el `programaAcademico`.
   - Mapeo determinista de hitos a `EstadoPractica` (incluso sin `fechaInicio`, DT-04).
   - Verificación de `DocenteAsesor` y control estricto de cupo máximo (10 prácticas activas).
4. Soporte de modo solo validación (`dry_run=True`, Escenario 2) y carga definitiva
   (`dry_run=False`, Escenario 1) con registro inmutable en `EventoBitacora`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from aplicacion.dtos.migracion_excel_dto import (
    FilaPlantillaMigracionDTO,
    MigrarPracticasExcelComando,
    MigrarPracticasExcelRespuestaDTO,
    ResultadoFilaMigracionDTO,
)
from aplicacion.puertos.lector_plantilla_excel import LectorPlantillaExcelPort
from aplicacion.puertos.repositorio_docente import RepositorioDocentePort
from aplicacion.puertos.repositorio_practica import RepositorioPracticaPort
from aplicacion.puertos.repositorio_regla import RepositorioReglaProgramaPort
from aplicacion.seguridad.autorizador_rbac import (
    AccesoDenegadoError,
    AutorizadorRBAC,
    ContextoUsuario,
)
from dominio.modelos.docente_asesor import DocenteAsesor
from dominio.modelos.estudiante import Estudiante
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.practica import ESTADOS_PRACTICA_ACTIVA, EstadoPractica, Practica
from dominio.modelos.regla_programa import ReglaPrograma


class MigrarPracticasExcelCasoUso:
    """Caso de uso del Módulo Postulaciones para migrar prácticas desde Excel (CU-15)."""

    def __init__(
        self,
        *,
        lector_plantilla: LectorPlantillaExcelPort,
        repositorio_practica: RepositorioPracticaPort,
        repositorio_docente: RepositorioDocentePort,
        repositorio_regla: RepositorioReglaProgramaPort,
        autorizador_rbac: Optional[AutorizadorRBAC] = None,
    ) -> None:
        """Inicializa el caso de uso con sus puertos de entrada/persistencia y RBAC."""
        self._lector_plantilla: LectorPlantillaExcelPort = lector_plantilla
        self._repositorio_practica: RepositorioPracticaPort = repositorio_practica
        self._repositorio_docente: RepositorioDocentePort = repositorio_docente
        self._repositorio_regla: RepositorioReglaProgramaPort = repositorio_regla
        self._autorizador_rbac: AutorizadorRBAC = autorizador_rbac or AutorizadorRBAC()

    def __call__(
        self,
        comando: MigrarPracticasExcelComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> MigrarPracticasExcelRespuestaDTO:
        """Permite invocar la instancia del caso de uso como un objeto callable."""
        return self.ejecutar(comando=comando, contexto=contexto)

    def ejecutar(
        self,
        comando: MigrarPracticasExcelComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> MigrarPracticasExcelRespuestaDTO:
        """Ejecuta la validación (dry-run) o carga definitiva de la plantilla normalizada."""
        actor_id = (
            contexto.usuario_id if contexto is not None else comando.actor_id
        )
        rol_actor = contexto.rol if contexto is not None else comando.rol_actor
        ip_origen = (
            (
                contexto.ip_origen
                if contexto is not None and contexto.ip_origen
                else comando.ip_origen
            )
            or "127.0.0.1"
        ).strip()

        self._validar_autorizacion(
            actor_id=actor_id,
            rol_actor=rol_actor,
            ip_origen=ip_origen,
        )

        filas = self._lector_plantilla.leer_filas(comando.origen_datos)

        resultados: list[ResultadoFilaMigracionDTO] = []
        documentos_lote: set[str] = set()
        carga_simulada_docentes: dict[str, int] = {}
        practicas_a_persistir: list[tuple[Practica, Optional[DocenteAsesor]]] = []

        total_validas = 0
        total_importadas = 0
        total_omitidas_duplicadas = 0
        total_rechazadas = 0

        for fila in filas:
            resultado_fila, entidad_preparada = self._procesar_fila(
                fila=fila,
                dry_run=comando.dry_run,
                documentos_lote=documentos_lote,
                carga_simulada_docentes=carga_simulada_docentes,
            )
            resultados.append(resultado_fila)

            if resultado_fila.estado_resultado in {"VALIDA", "IMPORTADA"}:
                total_validas += 1
                if entidad_preparada is not None:
                    practicas_a_persistir.append(entidad_preparada)
            elif resultado_fila.estado_resultado == "OMITIDA_DUPLICADA":
                total_omitidas_duplicadas += 1
            else:
                total_rechazadas += 1

        if not comando.dry_run:
            for practica, docente in practicas_a_persistir:
                self._repositorio_practica.guardar(practica)
                if docente is not None and practica.es_activa():
                    docente.asignar_practica()
                    self._repositorio_docente.actualizar(docente)
                total_importadas += 1

            self._registrar_bitacora(
                actor_id=actor_id.strip(),
                rol=rol_actor.strip(),
                ip=ip_origen,
                accion="Migración definitiva de prácticas desde Excel",
                entidad=f"LoteMigracion:{comando.origen_datos}",
                detalles={
                    "origen_datos": comando.origen_datos,
                    "dry_run": False,
                    "total_filas": len(filas),
                    "total_importadas": total_importadas,
                    "total_omitidas_duplicadas": total_omitidas_duplicadas,
                    "total_rechazadas": total_rechazadas,
                },
            )

        modo_texto = "solo validación (dry-run)" if comando.dry_run else "carga definitiva"
        mensaje = (
            f"Migración en modo {modo_texto} finalizada: "
            f"{len(filas)} filas procesadas, {total_validas} válidas, "
            f"{total_importadas} importadas, {total_omitidas_duplicadas} omitidas por duplicidad, "
            f"{total_rechazadas} rechazadas."
        )

        return MigrarPracticasExcelRespuestaDTO(
            dry_run=comando.dry_run,
            total_filas=len(filas),
            total_validas=total_validas,
            total_importadas=total_importadas,
            total_omitidas_duplicadas=total_omitidas_duplicadas,
            total_rechazadas=total_rechazadas,
            resultados_filas=tuple(resultados),
            mensaje=mensaje,
        )

    def _validar_autorizacion(
        self,
        *,
        actor_id: str,
        rol_actor: str,
        ip_origen: str,
    ) -> None:
        """Valida que el operador posea rol exclusivo Administrador DBA (ADR-005, EAC-03)."""
        try:
            if not actor_id or not str(actor_id).strip():
                raise AccesoDenegadoError(
                    "Acceso denegado: No se ha provisto una identidad de Administrador DBA válida.",
                    rol_actor=rol_actor,
                    operacion="migrar_practicas_excel",
                    usuario_id=actor_id,
                )
            self._autorizador_rbac.validar_migracion_excel(
                rol_actor=rol_actor,
                usuario_id=actor_id,
                operacion="migrar_practicas_excel",
            )
        except AccesoDenegadoError as error_rbac:
            self._registrar_bitacora(
                actor_id=(actor_id or "DESCONOCIDO").strip() or "DESCONOCIDO",
                rol=(rol_actor or "DESCONOCIDO").strip() or "DESCONOCIDO",
                ip=ip_origen,
                accion="Intento no autorizado de migración de prácticas desde Excel",
                entidad="ModuloPostulaciones",
                detalles={
                    "operacion": "migrar_practicas_excel",
                    "diagnostico": str(error_rbac),
                },
            )
            raise

    def _procesar_fila(
        self,
        *,
        fila: FilaPlantillaMigracionDTO,
        dry_run: bool,
        documentos_lote: set[str],
        carga_simulada_docentes: dict[str, int],
    ) -> tuple[ResultadoFilaMigracionDTO, Optional[tuple[Practica, Optional[DocenteAsesor]]]]:
        """Valida una fila de la plantilla y construye la entidad Practica si es válida."""
        doc_est = (fila.documento_estudiante or "").strip()

        error_formato = self._validar_datos_basicos(fila)
        if error_formato is not None:
            return (
                ResultadoFilaMigracionDTO(
                    numero_fila=fila.numero_fila,
                    documento_estudiante=doc_est,
                    estado_resultado="RECHAZADA",
                    estado_practica_asignado=None,
                    mensaje=error_formato,
                ),
                None,
            )

        if self._es_duplicado(doc_est=doc_est, documentos_lote=documentos_lote):
            return (
                ResultadoFilaMigracionDTO(
                    numero_fila=fila.numero_fila,
                    documento_estudiante=doc_est,
                    estado_resultado="OMITIDA_DUPLICADA",
                    estado_practica_asignado=None,
                    mensaje=(
                        f"Fila {fila.numero_fila}: Registro omitido por duplicidad para el "
                        f"estudiante '{doc_est}' (ya existe en el lote o en el sistema)."
                    ),
                ),
                None,
            )

        programa = fila.programa_academico.strip()
        regla = self._repositorio_regla.buscar_activa_por_programa(programa)
        if regla is None:
            return (
                ResultadoFilaMigracionDTO(
                    numero_fila=fila.numero_fila,
                    documento_estudiante=doc_est,
                    estado_resultado="RECHAZADA",
                    estado_practica_asignado=None,
                    mensaje=(
                        f"Fila {fila.numero_fila}: No existe una ReglaPrograma vigente "
                        f"configurada para el programa académico '{programa}'."
                    ),
                ),
                None,
            )

        horas_acumuladas, error_horas = self._parsear_horas(fila.horas_acumuladas)
        if error_horas is not None:
            return (
                ResultadoFilaMigracionDTO(
                    numero_fila=fila.numero_fila,
                    documento_estudiante=doc_est,
                    estado_resultado="RECHAZADA",
                    estado_practica_asignado=None,
                    mensaje=f"Fila {fila.numero_fila}: {error_horas}",
                ),
                None,
            )

        fecha_post, fecha_inicio, fecha_fin, error_fechas = self._parsear_fechas(fila)
        if error_fechas is not None:
            return (
                ResultadoFilaMigracionDTO(
                    numero_fila=fila.numero_fila,
                    documento_estudiante=doc_est,
                    estado_resultado="RECHAZADA",
                    estado_practica_asignado=None,
                    mensaje=f"Fila {fila.numero_fila}: {error_fechas}",
                ),
                None,
            )

        estado_destino = self._determinar_estado_practica(
            fila=fila,
            horas_acumuladas=horas_acumuladas,
        )

        docente, error_docente = self._validar_docente_y_cupo(
            fila=fila,
            estado_destino=estado_destino,
            carga_simulada_docentes=carga_simulada_docentes,
        )
        if error_docente is not None:
            return (
                ResultadoFilaMigracionDTO(
                    numero_fila=fila.numero_fila,
                    documento_estudiante=doc_est,
                    estado_resultado="RECHAZADA",
                    estado_practica_asignado=None,
                    mensaje=f"Fila {fila.numero_fila}: {error_docente}",
                ),
                None,
            )

        try:
            estudiante = Estudiante(
                documento=doc_est,
                nombre_completo=fila.nombre_estudiante.strip(),
                correo_institucional=fila.correo_estudiante.strip(),
                programa_academico=programa,
            )
            practica = self._construir_practica(
                estudiante=estudiante,
                regla=regla,
                docente=docente,
                supervisor_correo=fila.supervisor_correo.strip(),
                estado_destino=estado_destino,
                horas_acumuladas=horas_acumuladas,
                fecha_postulacion=fecha_post,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
            )
        except Exception as exc:
            return (
                ResultadoFilaMigracionDTO(
                    numero_fila=fila.numero_fila,
                    documento_estudiante=doc_est,
                    estado_resultado="RECHAZADA",
                    estado_practica_asignado=None,
                    mensaje=f"Fila {fila.numero_fila}: Error de dominio al construir práctica: {exc}",
                ),
                None,
            )

        documentos_lote.add(doc_est)
        if docente is not None and estado_destino in ESTADOS_PRACTICA_ACTIVA:
            carga_actual = carga_simulada_docentes.get(docente.id, docente.practicas_activas)
            carga_simulada_docentes[docente.id] = carga_actual + 1

        estado_res = "VALIDA" if dry_run else "IMPORTADA"
        return (
            ResultadoFilaMigracionDTO(
                numero_fila=fila.numero_fila,
                documento_estudiante=doc_est,
                estado_resultado=estado_res,
                estado_practica_asignado=practica.estado_actual.value,
                mensaje=(
                    f"Fila {fila.numero_fila}: Práctica válida con estado formal "
                    f"'{practica.estado_actual.value}'."
                ),
            ),
            (practica, docente),
        )

    @staticmethod
    def _validar_datos_basicos(fila: FilaPlantillaMigracionDTO) -> Optional[str]:
        """Verifica que los campos mínimos obligatorios estén presentes y no vacíos."""
        campos_obligatorios = (
            ("documento_estudiante", fila.documento_estudiante),
            ("nombre_estudiante", fila.nombre_estudiante),
            ("correo_estudiante", fila.correo_estudiante),
            ("programa_academico", fila.programa_academico),
            ("nombre_empresa", fila.nombre_empresa),
            ("nit_empresa", fila.nit_empresa),
            ("supervisor_nombre", fila.supervisor_nombre),
            ("supervisor_correo", fila.supervisor_correo),
        )
        faltantes = [
            nombre for nombre, valor in campos_obligatorios if not valor or not str(valor).strip()
        ]
        if faltantes:
            return (
                f"Fila {fila.numero_fila}: Faltan campos obligatorios: "
                f"{', '.join(faltantes)}."
            )
        if "@" not in fila.correo_estudiante:
            return f"Fila {fila.numero_fila}: Correo del estudiante con formato inválido."
        if "@" not in fila.supervisor_correo:
            return f"Fila {fila.numero_fila}: Correo del supervisor con formato inválido."
        return None

    def _es_duplicado(self, *, doc_est: str, documentos_lote: set[str]) -> bool:
        """Determina si el estudiante ya fue procesado en el lote o ya tiene práctica."""
        if doc_est in documentos_lote:
            return True
        if self._repositorio_practica.buscar_activa_por_estudiante(doc_est) is not None:
            return True
        if self._repositorio_practica.buscar_mas_reciente_o_activa_por_estudiante(doc_est) is not None:
            return True
        return False

    @staticmethod
    def _parsear_horas(horas_raw: str) -> tuple[int, Optional[str]]:
        """Convierte y valida las horas acumuladas como entero no negativo."""
        texto = (horas_raw or "").strip()
        if not texto:
            return 0, None
        try:
            valor = int(texto)
        except ValueError:
            return 0, f"Formato de horas acumuladas inválido ('{horas_raw}')."
        if valor < 0:
            return 0, f"Las horas acumuladas no pueden ser negativas ('{horas_raw}')."
        return valor, None

    @staticmethod
    def _parsear_fechas(
        fila: FilaPlantillaMigracionDTO,
    ) -> tuple[Optional[datetime], Optional[datetime], Optional[datetime], Optional[str]]:
        """Parsea las fechas opcionales en formato ISO o DD/MM/YYYY."""
        def _parsear_una(raw: str, campo: str) -> tuple[Optional[datetime], Optional[str]]:
            texto = (raw or "").strip()
            if not texto:
                return None, None
            for formato in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"):
                try:
                    return datetime.strptime(texto, formato), None
                except ValueError:
                    continue
            try:
                return datetime.fromisoformat(texto), None
            except ValueError:
                return None, f"Formato de fecha inválido en '{campo}' ('{raw}')."

        f_post, err = _parsear_una(fila.fecha_postulacion, "fecha_postulacion")
        if err:
            return None, None, None, err
        f_ini, err = _parsear_una(fila.fecha_inicio, "fecha_inicio")
        if err:
            return None, None, None, err
        f_fin, err = _parsear_una(fila.fecha_fin, "fecha_fin")
        if err:
            return None, None, None, err

        if f_ini is not None and f_fin is not None and f_fin < f_ini:
            return None, None, None, "La fecha_fin no puede ser anterior a la fecha_inicio."

        return f_post, f_ini, f_fin, None

    @staticmethod
    def _determinar_estado_practica(
        *,
        fila: FilaPlantillaMigracionDTO,
        horas_acumuladas: int,
    ) -> EstadoPractica:
        """Asigna el estado formal de forma determinista según hitos completados (DT-04)."""
        hito = (fila.estado_o_hito or "").strip().lower()
        hito_compacto = hito.replace("_", "").replace(" ", "")
        tiene_tutor = bool((fila.docente_asesor_id or "").strip())
        tiene_fecha_inicio = bool((fila.fecha_inicio or "").strip())

        if "completada" in hito or "actafirmada" in hito_compacto:
            return EstadoPractica.COMPLETADA
        if "evaluada" in hito or "evaluacion" in hito or "evaluación" in hito:
            return EstadoPractica.EVALUADA
        if "enejecucion" in hito_compacto or "enejecución" in hito_compacto or (
            tiene_tutor and (tiene_fecha_inicio or horas_acumuladas > 0)
        ):
            return EstadoPractica.EN_EJECUCION
        if "asignada" in hito or tiene_tutor:
            return EstadoPractica.ASIGNADA
        if "aprobada" in hito or "aprobado" in hito:
            return EstadoPractica.APROBADA
        return EstadoPractica.SOLICITADA

    def _validar_docente_y_cupo(
        self,
        *,
        fila: FilaPlantillaMigracionDTO,
        estado_destino: EstadoPractica,
        carga_simulada_docentes: dict[str, int],
    ) -> tuple[Optional[DocenteAsesor], Optional[str]]:
        """Verifica existencia, habilitación y cupo máximo (10) del DocenteAsesor (R-04)."""
        docente_ref = (fila.docente_asesor_id or "").strip()
        requiere_tutor = estado_destino in {
            EstadoPractica.ASIGNADA,
            EstadoPractica.EN_EJECUCION,
            EstadoPractica.EVALUADA,
            EstadoPractica.COMPLETADA,
        }

        if not docente_ref:
            if requiere_tutor:
                return None, (
                    f"El estado '{estado_destino.value}' requiere un DocenteAsesor asignado."
                )
            return None, None

        docente = (
            self._repositorio_docente.buscar_por_id(docente_ref)
            or self._repositorio_docente.buscar_por_documento(docente_ref)
        )
        if docente is None or not docente.activo:
            return None, (
                f"El DocenteAsesor '{docente_ref}' no existe o no se encuentra habilitado."
            )

        if estado_destino in ESTADOS_PRACTICA_ACTIVA:
            carga_actual = carga_simulada_docentes.get(docente.id, docente.practicas_activas)
            if carga_actual >= docente.cupo_maximo_practicas:
                return None, (
                    f"El DocenteAsesor '{docente_ref}' superaría el cupo máximo de "
                    f"{docente.cupo_maximo_practicas} prácticas activas "
                    f"(actual: {carga_actual})."
                )

        return docente, None

    @staticmethod
    def _construir_practica(
        *,
        estudiante: Estudiante,
        regla: ReglaPrograma,
        docente: Optional[DocenteAsesor],
        supervisor_correo: str,
        estado_destino: EstadoPractica,
        horas_acumuladas: int,
        fecha_postulacion: Optional[datetime],
        fecha_inicio: Optional[datetime],
        fecha_fin: Optional[datetime],
    ) -> Practica:
        """Construye la entidad Practica transitando formalmente su máquina de estados (ADR-010)."""
        practica = Practica(
            estudiante_id=estudiante.documento,
            regla_programa_id=regla.id,
            estado_inicial=EstadoPractica.SOLICITADA,
            fecha_postulacion=fecha_postulacion,
            supervisor_empresa_id=supervisor_correo,
            horas_acumuladas_aprobadas=0,
        )

        if estado_destino == EstadoPractica.SOLICITADA:
            return practica

        practica.aprobar()
        if estado_destino == EstadoPractica.APROBADA:
            return practica

        assert docente is not None
        practica.asignar_tutor(docente.id)
        if estado_destino == EstadoPractica.ASIGNADA:
            return practica

        practica.iniciar_ejecucion(fecha_inicio=fecha_inicio)
        if horas_acumuladas > 0:
            practica.acumular_horas_aprobadas(horas_acumuladas)
        if estado_destino == EstadoPractica.EN_EJECUCION:
            return practica

        practica.registrar_evaluacion_desempeno(fecha_fin=fecha_fin)
        if estado_destino == EstadoPractica.EVALUADA:
            return practica

        practica.completar(acta_en_firme=True, fecha_fin=fecha_fin)
        return practica

    def _registrar_bitacora(
        self,
        *,
        actor_id: str,
        rol: str,
        ip: str,
        accion: str,
        entidad: str,
        detalles: Optional[dict[str, object]] = None,
    ) -> None:
        """Inserta un EventoBitacora inmutable en la bitácora append-only (ADR-006)."""
        evento = EventoBitacora(
            actor_identificador=actor_id,
            rol_actor=rol,
            ip_origen=ip,
            accion_realizada=accion,
            entidad_afectada=entidad,
            detalles=detalles,
        )
        self._repositorio_practica.guardar_evento_bitacora(evento)
