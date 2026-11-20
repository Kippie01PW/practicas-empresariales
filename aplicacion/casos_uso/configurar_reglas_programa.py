"""Caso de uso: Configurar reglas y plantillas por programa (CU-12).

Traza: CU-12, EAC-01, EAC-03, OB-05, PA-01, PA-03, RN-01, RN-02, RN-03,
ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores),
ADR-003 (Persistencia transaccional),
ADR-004 (Autenticación híbrida e identidad institucional),
ADR-005 (Control de acceso RBAC centralizado a nivel de casos de uso con política deny-by-default),
ADR-006 (Bitácora de auditoría transaccional de solo inserción - Append-Only),
ADR-007 (Configuración declarativa de reglas versionadas por programa),
ADR-008 (Generación y preservación del acta final mediante plantillas y sellado criptográfico SHA-256),
Vista de Desarrollo §2 (03-desarrollo.md) y Diagrama de Secuencia ESC-05 (cu12-configurar-reglas.puml).

Implementa la orquestación del Módulo Reglas en la capa de Aplicación para:
1. crear_borrador / ejecutar: Crear una nueva versión de ReglaPrograma en estado 'Borrador'
   conservando intacta la versión 'Activa' previa y las prácticas vinculadas a ella (Escenario 1).
2. editar_borrador: Editar los atributos normativos (horasRequeridas, criteriosRubrica,
   plantillaActa, version) exclusivamente mientras permanezca en estado 'Borrador', bloqueando
   cualquier modificación directa sobre reglas en estado 'Activa' o 'Inactiva' (Escenarios 2 y 8).
3. simular_previsualizacion: Renderizar en memoria una vista previa del documento PDF del
   ActaFinal y su rúbrica para una ReglaPrograma en estado 'Borrador' con datos de prueba,
   sin escribir ningún archivo en el Repositorio de actas PDF ni alterar prácticas existentes
   (Escenarios 3 y 10).
4. activar_regla: Publicar y activar oficialmente una ReglaPrograma en estado 'Borrador',
   transicionando atómicamente la versión anterior del mismo programa académico a 'Inactiva'
   (histórica), garantizando como máximo una única regla 'Activa' por programa y un 0% de
   alteración sobre prácticas en curso o actas previas (Escenarios 4 y 10).
5. eliminar_regla: Bloquear cualquier intento de eliminación de una ReglaPrograma en estado
   'Activa' o 'Inactiva' para preservar la integridad normativa de las cohortes históricas
   (Escenario 8).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Union

from aplicacion.dtos.acta_final_dto import (
    DatosRenderizadoActaDTO,
    ResultadoRenderizadoPdfDTO,
)
from aplicacion.dtos.regla_programa_dto import (
    ActivarReglaProgramaComando,
    CrearBorradorReglaComando,
    EditarBorradorReglaComando,
    EliminarReglaProgramaComando,
    ReglaProgramaRespuestaDTO,
    SimulacionReglaProgramaRespuestaDTO,
    SimularReglaProgramaComando,
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
    DatosReglaProgramaInvalidosError,
    ReglaProgramaInmutableError,
    ReglaProgramaNoEncontradaError,
    VersionReglaProgramaDuplicadaError,
)
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.regla_programa import EstadoVigenciaRegla, ReglaPrograma


class ConfigurarReglasProgramaCasoUso:
    """Caso de uso del Módulo Reglas para configurar reglas y plantillas versionadas por programa (CU-12)."""

    def __init__(
        self,
        *,
        repositorio_regla: RepositorioReglaProgramaPort,
        repositorio_practica: RepositorioPracticaPort,
        servicio_pdf: Optional[ServicioGeneradorActaPdfPort] = None,
        autorizador_rbac: Optional[AutorizadorRBAC] = None,
    ) -> None:
        self._repositorio_regla: RepositorioReglaProgramaPort = repositorio_regla
        self._repositorio_practica: RepositorioPracticaPort = repositorio_practica
        self._servicio_pdf: Optional[ServicioGeneradorActaPdfPort] = servicio_pdf
        self._autorizador_rbac: AutorizadorRBAC = autorizador_rbac or AutorizadorRBAC()

    def __call__(
        self,
        comando: Union[
            CrearBorradorReglaComando,
            EditarBorradorReglaComando,
            SimularReglaProgramaComando,
            ActivarReglaProgramaComando,
            EliminarReglaProgramaComando,
        ],
        contexto: Optional[ContextoUsuario] = None,
    ) -> Union[ReglaProgramaRespuestaDTO, SimulacionReglaProgramaRespuestaDTO, None]:
        """Permite invocar la instancia del caso de uso despachando según el tipo de comando."""
        return self.ejecutar(comando, contexto=contexto)

    def ejecutar(
        self,
        comando: Union[
            CrearBorradorReglaComando,
            EditarBorradorReglaComando,
            SimularReglaProgramaComando,
            ActivarReglaProgramaComando,
            EliminarReglaProgramaComando,
        ],
        contexto: Optional[ContextoUsuario] = None,
    ) -> Union[ReglaProgramaRespuestaDTO, SimulacionReglaProgramaRespuestaDTO, None]:
        """Despacha la operación de configuración de reglas según el comando inmutable recibido."""
        if isinstance(comando, CrearBorradorReglaComando):
            return self.crear_borrador(comando, contexto=contexto)
        if isinstance(comando, EditarBorradorReglaComando):
            return self.editar_borrador(comando, contexto=contexto)
        if isinstance(comando, SimularReglaProgramaComando):
            return self.simular_previsualizacion(comando, contexto=contexto)
        if isinstance(comando, ActivarReglaProgramaComando):
            return self.activar_regla(comando, contexto=contexto)
        if isinstance(comando, EliminarReglaProgramaComando):
            return self.eliminar_regla(comando, contexto=contexto)
        raise TypeError(f"Comando no soportado por ConfigurarReglasProgramaCasoUso: {type(comando)!r}")

    # -----------------------------------------------------------------------
    # 1. Creación de nueva versión en estado Borrador (Escenarios 1, 5, 6, 7, 9)
    # -----------------------------------------------------------------------

    def crear_borrador(
        self,
        comando: CrearBorradorReglaComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> ReglaProgramaRespuestaDTO:
        """Crea y persiste una nueva versión de ReglaPrograma en estadoVigencia 'Borrador'.

        Traza: CU-12, Escenario 1 (Creación exitosa en Borrador), Escenario 5 (Datos obligatorios
        y horasRequeridas > 0), Escenario 6 (criteriosRubrica válidos como lista simple o diccionario),
        Escenario 7 (Unicidad de versión por programa académico), Escenario 9 (Autorización RBAC).
        """
        entidad_objetivo = (
            f"ReglaPrograma:{comando.programa_academico.strip()}:{comando.version.strip()}"
            if isinstance(comando.programa_academico, str)
            and comando.programa_academico.strip()
            and isinstance(comando.version, str)
            and comando.version.strip()
            else "ReglaPrograma:BORRADOR"
        )
        actor_id, rol_actor, ip_origen = self._autorizar_o_auditar_rechazo(
            actor_id_raw=comando.actor_id,
            rol_actor_raw=comando.rol_actor,
            ip_origen_raw=comando.ip_origen,
            contexto=contexto,
            operacion="configurar_reglas",
            suboperacion="crear_borrador",
            entidad_afectada=entidad_objetivo,
        )

        # Validación de unicidad de versión por programa académico (Escenario 7)
        if (
            isinstance(comando.programa_academico, str)
            and comando.programa_academico.strip()
            and isinstance(comando.version, str)
            and comando.version.strip()
        ):
            regla_duplicada = self._repositorio_regla.buscar_por_programa_y_version(
                comando.programa_academico.strip(),
                comando.version.strip(),
            )
            if regla_duplicada is not None:
                raise VersionReglaProgramaDuplicadaError(
                    programa_academico=comando.programa_academico.strip(),
                    version=comando.version.strip(),
                    regla_existente_id=regla_duplicada.id,
                )

        # Exigir criteriosRubrica no nulos en la creación de reglas (Escenario 6)
        if comando.criterios_rubrica is None:
            ReglaPrograma._validar_criterios_rubrica(None, exigir_no_vacio=True)

        nueva_regla = ReglaPrograma(
            id=comando.regla_id,
            programa_academico=comando.programa_academico,
            version=comando.version,
            horas_requeridas=comando.horas_requeridas,
            criterios_rubrica=comando.criterios_rubrica,
            plantilla_acta=comando.plantilla_acta,
            estado_vigencia=EstadoVigenciaRegla.BORRADOR,
        )

        self._repositorio_regla.guardar(nueva_regla)

        evento = EventoBitacora(
            actor_identificador=actor_id,
            rol_actor=rol_actor,
            ip_origen=ip_origen,
            accion_realizada="Creación de borrador de ReglaPrograma",
            entidad_afectada=f"ReglaPrograma:{nueva_regla.id}",
            detalles={
                "regla_id": nueva_regla.id,
                "programa_academico": nueva_regla.programa_academico,
                "version": nueva_regla.version,
                "horas_requeridas": nueva_regla.horas_requeridas,
                "criterios_rubrica": nueva_regla.criterios_rubrica,
                "plantilla_acta": nueva_regla.plantilla_acta,
                "estado_vigencia": nueva_regla.estado_vigencia.value,
            },
        )
        self._repositorio_practica.guardar_evento_bitacora(evento)

        mensaje = (
            f"ReglaPrograma '{nueva_regla.id}' para '{nueva_regla.programa_academico}' "
            f"(versión '{nueva_regla.version}') creada exitosamente en estado "
            f"'{nueva_regla.estado_vigencia.value}'."
        )
        return self._construir_respuesta_regla(
            regla=nueva_regla,
            regla_anterior_inactivada_id=None,
            version_anterior_inactivada=None,
            mensaje=mensaje,
        )

    # -----------------------------------------------------------------------
    # 2. Edición controlada en estado Borrador (Escenarios 2, 5, 6, 7, 8, 9)
    # -----------------------------------------------------------------------

    def editar_borrador(
        self,
        comando: EditarBorradorReglaComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> ReglaProgramaRespuestaDTO:
        """Actualiza los atributos normativos de una ReglaPrograma mientras permanezca en estado Borrador.

        Traza: CU-12, Escenario 2 (Edición exitosa en Borrador), Escenarios 5 y 6 (Invariantes normativas),
        Escenario 7 (Unicidad de versión), Escenario 8 (Bloqueo de edición en estado Activa o Inactiva),
        Escenario 9 (Autorización RBAC).
        """
        entidad_objetivo = f"ReglaPrograma:{comando.regla_id}"
        actor_id, rol_actor, ip_origen = self._autorizar_o_auditar_rechazo(
            actor_id_raw=comando.actor_id,
            rol_actor_raw=comando.rol_actor,
            ip_origen_raw=comando.ip_origen,
            contexto=contexto,
            operacion="configurar_reglas",
            suboperacion="editar_borrador",
            entidad_afectada=entidad_objetivo,
        )

        regla = self._obtener_regla_o_error(comando.regla_id)

        # Si la regla ya no está en Borrador, lanza inmediatamente ReglaProgramaInmutableError (Escenario 8)
        if not regla.es_borrador():
            raise ReglaProgramaInmutableError(
                regla_id=regla.id,
                version=regla.version,
                estado_vigencia=regla.estado_vigencia.value,
                operacion="editar",
            )

        # Si se solicita cambiar la versión, verificar unicidad dentro del mismo programa (Escenario 7)
        if comando.version is not None:
            if not isinstance(comando.version, str) or not comando.version.strip():
                raise DatosReglaProgramaInvalidosError(
                    campo="version",
                    valor=comando.version,
                )
            version_limpia = comando.version.strip()
            if version_limpia.lower() != regla.version.lower():
                regla_duplicada = self._repositorio_regla.buscar_por_programa_y_version(
                    regla.programa_academico,
                    version_limpia,
                )
                if regla_duplicada is not None and regla_duplicada.id != regla.id:
                    raise VersionReglaProgramaDuplicadaError(
                        programa_academico=regla.programa_academico,
                        version=version_limpia,
                        regla_existente_id=regla_duplicada.id,
                    )

        regla.actualizar_borrador(
            horas_requeridas=comando.horas_requeridas,
            criterios_rubrica=comando.criterios_rubrica,
            plantilla_acta=comando.plantilla_acta,
            version=comando.version,
        )

        self._repositorio_regla.actualizar(regla)

        evento = EventoBitacora(
            actor_identificador=actor_id,
            rol_actor=rol_actor,
            ip_origen=ip_origen,
            accion_realizada="Actualización de borrador de ReglaPrograma",
            entidad_afectada=f"ReglaPrograma:{regla.id}",
            detalles={
                "regla_id": regla.id,
                "programa_academico": regla.programa_academico,
                "version": regla.version,
                "horas_requeridas": regla.horas_requeridas,
                "criterios_rubrica": regla.criterios_rubrica,
                "plantilla_acta": regla.plantilla_acta,
                "estado_vigencia": regla.estado_vigencia.value,
            },
        )
        self._repositorio_practica.guardar_evento_bitacora(evento)

        mensaje = (
            f"ReglaPrograma '{regla.id}' para '{regla.programa_academico}' "
            f"(versión '{regla.version}') actualizada exitosamente en estado "
            f"'{regla.estado_vigencia.value}'."
        )
        return self._construir_respuesta_regla(
            regla=regla,
            regla_anterior_inactivada_id=None,
            version_anterior_inactivada=None,
            mensaje=mensaje,
        )

    # -----------------------------------------------------------------------
    # 3. Simulación y previsualización en memoria (Escenarios 3, 9, 10)
    # -----------------------------------------------------------------------

    def simular_previsualizacion(
        self,
        comando: SimularReglaProgramaComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> SimulacionReglaProgramaRespuestaDTO:
        """Simula y previsualiza en memoria el ActaFinal en PDF y la rúbrica de una ReglaPrograma en Borrador.

        Traza: CU-12, Escenario 3 (Simulación y previsualización en memoria antes de activar),
        Escenario 9 (Autorización RBAC), Escenario 10 (EAC-01: Modificabilidad declarativa),
        ADR-007, ADR-008.
        """
        entidad_objetivo = f"ReglaPrograma:{comando.regla_id}"
        self._autorizar_o_auditar_rechazo(
            actor_id_raw=comando.actor_id,
            rol_actor_raw=comando.rol_actor,
            ip_origen_raw=comando.ip_origen,
            contexto=contexto,
            operacion="configurar_reglas",
            suboperacion="simular_previsualizacion",
            entidad_afectada=entidad_objetivo,
        )

        regla = self._obtener_regla_o_error(comando.regla_id)

        nombres_criterios = regla.nombres_criterios
        puntaje_prueba = float(comando.calificacion_prueba)
        respuestas_prueba: dict[str, float] = {
            criterio: puntaje_prueba for criterio in nombres_criterios
        }
        fecha_simulacion = datetime.now()
        numero_acta_simulacion = f"ACTA-SIMULACION-{regla.version}"
        practica_simulacion_id = f"PRAC-SIMULACION-{regla.id}"

        datos_simulacion = DatosRenderizadoActaDTO(
            numero_acta=numero_acta_simulacion,
            practica_id=practica_simulacion_id,
            estudiante_id=comando.estudiante_prueba_id,
            docente_asesor_id=comando.docente_prueba_id,
            nombre_docente_asesor=comando.nombre_docente_prueba,
            supervisor_empresa_id=comando.supervisor_prueba_id,
            regla_programa_id=regla.id,
            programa_academico=regla.programa_academico,
            version_regla=regla.version,
            plantilla_acta=regla.plantilla_acta,
            horas_requeridas=regla.horas_requeridas,
            horas_acumuladas_aprobadas=regla.horas_requeridas,
            calificacion_cuantitativa=puntaje_prueba,
            es_aprobatoria=(puntaje_prueba >= 3.0),
            observaciones_evaluacion=comando.observaciones_prueba,
            respuestas_rubrica=respuestas_prueba,
            fecha_emision=fecha_simulacion,
        )

        vista_previa_html = self._construir_html_simulacion(datos_simulacion, regla)

        if self._servicio_pdf is not None:
            resultado_pdf: ResultadoRenderizadoPdfDTO = (
                self._servicio_pdf.simular_acta_pdf_en_memoria(datos_simulacion)
            )
            contenido_pdf = resultado_pdf.contenido_pdf
            hash_sha256 = resultado_pdf.hash_integridad_sha256
            plantilla_utilizada = resultado_pdf.plantilla_utilizada
        else:
            import hashlib

            cuerpo_pdf = (
                "%PDF-1.4\n"
                f"% Simulacion ActaFinal: {numero_acta_simulacion}\n"
                f"% Plantilla: {regla.plantilla_acta} (Version: {regla.version})\n"
                f"{vista_previa_html}\n"
                "%%EOF\n"
            )
            contenido_pdf = cuerpo_pdf.encode("utf-8")
            hash_sha256 = hashlib.sha256(contenido_pdf).hexdigest().lower()
            plantilla_utilizada = regla.plantilla_acta

        mensaje = (
            f"Simulación en memoria generada exitosamente para la ReglaPrograma '{regla.id}' "
            f"('{regla.programa_academico}', versión '{regla.version}', estado '{regla.estado_vigencia.value}') "
            f"aplicando la plantilla '{plantilla_utilizada}', {regla.horas_requeridas} horas requeridas "
            f"y {len(nombres_criterios)} criterios de rúbrica. No se almacenó ningún ActaFinal oficial."
        )

        return SimulacionReglaProgramaRespuestaDTO(
            regla_id=regla.id,
            programa_academico=regla.programa_academico,
            version=regla.version,
            estado_vigencia=regla.estado_vigencia.value,
            horas_requeridas=regla.horas_requeridas,
            criterios_rubrica=regla.criterios_rubrica,
            nombres_criterios=tuple(nombres_criterios),
            plantilla_utilizada=plantilla_utilizada,
            contenido_pdf_simulacion=contenido_pdf,
            vista_previa_html=vista_previa_html,
            hash_sha256_simulacion=hash_sha256,
            persistido_en_repositorio=False,
            mensaje=mensaje,
        )

    # -----------------------------------------------------------------------
    # 4. Activación oficial de una nueva versión (Escenarios 4, 8, 9, 10)
    # -----------------------------------------------------------------------

    def activar_regla(
        self,
        comando: ActivarReglaProgramaComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> ReglaProgramaRespuestaDTO:
        """Publica y activa oficialmente una ReglaPrograma en Borrador e inactiva la versión anterior.

        Traza: CU-12, Escenario 4 (Activación oficial exitosa y transición de la versión anterior a Inactiva),
        Escenario 8 (Bloqueo si no está en Borrador), Escenario 9 (Autorización RBAC),
        Escenario 10 (EAC-01: 0% de alteración en prácticas activas y actas previas),
        ADR-003, ADR-006, ADR-007.
        """
        entidad_objetivo = f"ReglaPrograma:{comando.regla_id}"
        actor_id, rol_actor, ip_origen = self._autorizar_o_auditar_rechazo(
            actor_id_raw=comando.actor_id,
            rol_actor_raw=comando.rol_actor,
            ip_origen_raw=comando.ip_origen,
            contexto=contexto,
            operacion="configurar_reglas",
            suboperacion="activar_regla",
            entidad_afectada=entidad_objetivo,
        )

        regla = self._obtener_regla_o_error(comando.regla_id)

        if not regla.es_borrador():
            raise ReglaProgramaInmutableError(
                regla_id=regla.id,
                version=regla.version,
                estado_vigencia=regla.estado_vigencia.value,
                operacion="activar",
            )

        # Buscar todas las versiones del mismo programa académico y desactivar las que estén en estado Activa
        reglas_programa = self._repositorio_regla.listar_por_programa(
            regla.programa_academico
        )
        regla_anterior_id: Optional[str] = None
        version_anterior: Optional[str] = None

        for regla_existente in reglas_programa:
            if regla_existente.id != regla.id and regla_existente.es_activa():
                regla_anterior_id = regla_existente.id
                version_anterior = regla_existente.version
                regla_existente.desactivar()
                self._repositorio_regla.actualizar(regla_existente)

        # Fallback por si el repositorio tiene una activa que no vino en listar_por_programa
        if regla_anterior_id is None:
            regla_activa_actual = self._repositorio_regla.buscar_activa_por_programa(
                regla.programa_academico
            )
            if regla_activa_actual is not None and regla_activa_actual.id != regla.id:
                regla_anterior_id = regla_activa_actual.id
                version_anterior = regla_activa_actual.version
                regla_activa_actual.desactivar()
                self._repositorio_regla.actualizar(regla_activa_actual)

        fecha_activacion = comando.fecha_vigencia or datetime.now()
        regla.activar(fecha_vigencia=fecha_activacion)
        self._repositorio_regla.actualizar(regla)

        entidad_bitacora = (
            f"ReglaPrograma:{regla.id}|ReglaAnterior:{regla_anterior_id}"
            if regla_anterior_id
            else f"ReglaPrograma:{regla.id}"
        )
        evento = EventoBitacora(
            actor_identificador=actor_id,
            rol_actor=rol_actor,
            ip_origen=ip_origen,
            accion_realizada="Activación oficial de ReglaPrograma",
            entidad_afectada=entidad_bitacora,
            fecha_hora=fecha_activacion,
            detalles={
                "regla_activada_id": regla.id,
                "programa_academico": regla.programa_academico,
                "version_activada": regla.version,
                "horas_requeridas": regla.horas_requeridas,
                "criterios_rubrica": regla.criterios_rubrica,
                "plantilla_acta": regla.plantilla_acta,
                "estado_vigencia": regla.estado_vigencia.value,
                "regla_anterior_inactivada_id": regla_anterior_id,
                "version_anterior_inactivada": version_anterior,
            },
        )
        self._repositorio_practica.guardar_evento_bitacora(evento)

        detalle_anterior = (
            f" La versión anterior '{version_anterior}' (ID: '{regla_anterior_id}') pasó a estado 'Inactiva' "
            f"conservando un 0% de alteración en las prácticas y actas vinculadas a ella."
            if version_anterior
            else ""
        )
        mensaje = (
            f"ReglaPrograma '{regla.id}' para '{regla.programa_academico}' "
            f"(versión '{regla.version}') activada oficialmente en estado '{regla.estado_vigencia.value}'."
            f"{detalle_anterior}"
        )
        return self._construir_respuesta_regla(
            regla=regla,
            regla_anterior_inactivada_id=regla_anterior_id,
            version_anterior_inactivada=version_anterior,
            mensaje=mensaje,
        )

    # -----------------------------------------------------------------------
    # 5. Protección de inmutabilidad ante eliminación directa (Escenarios 8, 9)
    # -----------------------------------------------------------------------

    def eliminar_regla(
        self,
        comando: EliminarReglaProgramaComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> None:
        """Verifica las reglas de negocio ante una solicitud de eliminación de ReglaPrograma.

        Traza: CU-12, Escenario 8 (Intento de edición o eliminación directa de una regla de programa
        activa o histórica vinculada a prácticas existentes), Escenario 9 (Autorización RBAC).
        """
        entidad_objetivo = f"ReglaPrograma:{comando.regla_id}"
        self._autorizar_o_auditar_rechazo(
            actor_id_raw=comando.actor_id,
            rol_actor_raw=comando.rol_actor,
            ip_origen_raw=comando.ip_origen,
            contexto=contexto,
            operacion="configurar_reglas",
            suboperacion="eliminar_regla",
            entidad_afectada=entidad_objetivo,
        )

        regla = self._obtener_regla_o_error(comando.regla_id)

        if not regla.es_borrador():
            raise ReglaProgramaInmutableError(
                regla_id=regla.id,
                version=regla.version,
                estado_vigencia=regla.estado_vigencia.value,
                operacion="eliminar",
            )

    # -----------------------------------------------------------------------
    # Métodos privados auxiliares
    # -----------------------------------------------------------------------

    def _obtener_regla_o_error(self, regla_id: str) -> ReglaPrograma:
        """Recupera una ReglaPrograma por su identificador o lanza ReglaProgramaNoEncontradaError."""
        if not isinstance(regla_id, str) or not regla_id.strip():
            raise ReglaProgramaNoEncontradaError(regla_id=str(regla_id))
        regla = self._repositorio_regla.buscar_por_id(regla_id.strip())
        if regla is None:
            raise ReglaProgramaNoEncontradaError(regla_id=regla_id.strip())
        return regla

    def _autorizar_o_auditar_rechazo(
        self,
        *,
        actor_id_raw: Optional[str],
        rol_actor_raw: Optional[str],
        ip_origen_raw: Optional[str],
        contexto: Optional[ContextoUsuario],
        operacion: str,
        suboperacion: str,
        entidad_afectada: str,
    ) -> tuple[str, str, str]:
        """Valida identidad institucional y rol Coordinador de prácticas bajo política deny-by-default.

        Si la validación falla (rol Estudiante, DocenteAsesor, SupervisorEmpresa, vacío o sin sesión
        institucional válida), registra de inmediato un EventoBitacora inmutable en menos de 1 minuto
        y relanza AccesoDenegadoError asegurando 0 datos expuestos (Escenario 9, ADR-004, ADR-005,
        ADR-006, EAC-03).
        """
        actor_id = (
            contexto.usuario_id
            if contexto is not None
            else (actor_id_raw.strip() if isinstance(actor_id_raw, str) else "")
        )
        rol_actor = (
            contexto.rol
            if contexto is not None
            else (rol_actor_raw.strip() if isinstance(rol_actor_raw, str) else "")
        )
        ip_origen = (
            contexto.ip_origen
            if contexto is not None and contexto.ip_origen
            else (
                ip_origen_raw.strip()
                if isinstance(ip_origen_raw, str) and ip_origen_raw.strip()
                else "127.0.0.1"
            )
        )

        try:
            if not actor_id:
                raise AccesoDenegadoError(
                    "Acceso denegado: No se ha provisto una sesión o identidad institucional válida.",
                    rol_actor=rol_actor or None,
                    operacion=operacion,
                    usuario_id=actor_id or None,
                )
            self._autorizador_rbac.validar_configuracion_reglas(
                rol_actor=rol_actor,
                usuario_id=actor_id,
                operacion=operacion,
            )
        except AccesoDenegadoError as error_acceso:
            self._registrar_rechazo_bitacora(
                actor_id=actor_id or "ANONIMO",
                rol_actor=rol_actor or "SIN_ROL",
                ip_origen=ip_origen,
                entidad_afectada=entidad_afectada,
                suboperacion=suboperacion,
                motivo=str(error_acceso),
            )
            raise error_acceso

        return actor_id, rol_actor, ip_origen

    def _registrar_rechazo_bitacora(
        self,
        *,
        actor_id: str,
        rol_actor: str,
        ip_origen: str,
        entidad_afectada: str,
        suboperacion: str,
        motivo: str,
    ) -> None:
        """Inserta de inmediato un EventoBitacora inmutable por intento de configuración no autorizado (Escenario 9)."""
        evento = EventoBitacora(
            actor_identificador=actor_id,
            rol_actor=rol_actor,
            ip_origen=ip_origen,
            accion_realizada="Intento de configuración de reglas por rol no autorizado",
            entidad_afectada=entidad_afectada,
            detalles={
                "operacion": "configurar_reglas",
                "suboperacion": suboperacion,
                "motivo": motivo,
            },
        )
        self._repositorio_practica.guardar_evento_bitacora(evento)

    @staticmethod
    def _construir_respuesta_regla(
        *,
        regla: ReglaPrograma,
        regla_anterior_inactivada_id: Optional[str],
        version_anterior_inactivada: Optional[str],
        mensaje: str,
    ) -> ReglaProgramaRespuestaDTO:
        """Empaqueta una entidad ReglaPrograma en su DTO inmutable de respuesta."""
        return ReglaProgramaRespuestaDTO(
            regla_id=regla.id,
            programa_academico=regla.programa_academico,
            version=regla.version,
            horas_requeridas=regla.horas_requeridas,
            criterios_rubrica=regla.criterios_rubrica,
            nombres_criterios=tuple(regla.nombres_criterios),
            plantilla_acta=regla.plantilla_acta,
            estado_vigencia=regla.estado_vigencia.value,
            fecha_vigencia=regla.fecha_vigencia,
            regla_anterior_inactivada_id=regla_anterior_inactivada_id,
            version_anterior_inactivada=version_anterior_inactivada,
            mensaje=mensaje,
        )

    @staticmethod
    def _construir_html_simulacion(
        datos: DatosRenderizadoActaDTO,
        regla: ReglaPrograma,
    ) -> str:
        """Construye la vista previa HTML en memoria del acta final y rúbrica de la regla en Borrador."""
        concepto_desempeno = (
            "APROBATORIA" if datos.es_aprobatoria else "REPROBATORIA"
        )
        observaciones_texto = (
            datos.observaciones_evaluacion
            if datos.observaciones_evaluacion
            else "Sin observaciones adicionales."
        )
        criterios_detalle = "; ".join(
            f"{criterio}: {datos.respuestas_rubrica.get(criterio, datos.calificacion_cuantitativa):.2f}"
            for criterio in regla.nombres_criterios
        )
        return (
            "<!DOCTYPE html>\n"
            "<html lang=\"es\">\n"
            "<head>\n"
            "  <meta charset=\"UTF-8\">\n"
            f"  <meta name=\"template\" content=\"{datos.plantilla_acta}\">\n"
            f"  <meta name=\"regla-programa-id\" content=\"{datos.regla_programa_id}\">\n"
            f"  <meta name=\"regla-version\" content=\"{datos.version_regla}\">\n"
            f"  <meta name=\"estado-vigencia\" content=\"{regla.estado_vigencia.value}\">\n"
            f"  <title>Vista Previa Simulación Acta Final - {datos.numero_acta}</title>\n"
            "</head>\n"
            "<body>\n"
            f"  <h1>VISTA PREVIA SIMULACIÓN ACTA FINAL - {datos.numero_acta}</h1>\n"
            f"  <p><strong>Plantilla Aplicada:</strong> {datos.plantilla_acta} "
            f"(Regla: {datos.regla_programa_id}, Versión: {datos.version_regla}, "
            f"Estado: {regla.estado_vigencia.value})</p>\n"
            f"  <p><strong>Programa Académico:</strong> {datos.programa_academico}</p>\n"
            f"  <p><strong>Estudiante Prueba:</strong> {datos.estudiante_id}</p>\n"
            f"  <p><strong>Docente Asesor Prueba:</strong> {datos.docente_asesor_id} - {datos.nombre_docente_asesor}</p>\n"
            f"  <p><strong>Supervisor de Empresa Prueba:</strong> {datos.supervisor_empresa_id}</p>\n"
            f"  <p><strong>Horas Requeridas Configuradas:</strong> {datos.horas_requeridas}</p>\n"
            f"  <p><strong>Calificación Simulación:</strong> {datos.calificacion_cuantitativa:.2f} "
            f"({concepto_desempeno})</p>\n"
            f"  <p><strong>Criterios de Rúbrica Simulados:</strong> {criterios_detalle}</p>\n"
            f"  <p><strong>Observaciones:</strong> {observaciones_texto}</p>\n"
            "</body>\n"
            "</html>"
        )
