"""Componente centralizado de autorización basada en roles (RBAC) en la capa de Aplicación.

Traza: CU-01, CU-02, CU-03, CU-04, CU-05, CU-06, CU-07, RN-01, RN-03, PA-02, ADR-002, ADR-004, ADR-005,
Vista Lógica §2, Vista de Desarrollo §2.

Implementa la política de autorización RBAC centralizada y contextual (Context-Based Access Control)
bajo la regla 'deny-by-default' (ADR-005). Valida tanto el rol del actor autenticado como la
pertenencia de los recursos según la identidad del usuario (e.g. un estudiante solo puede postularse
a sí mismo y ver sus datos, RN-01; un supervisor solo puede validar horas y evaluar desempeño de su
práctica asignada, RN-01, CU-05, CU-07; un docente asesor solo puede revisar avances de horas de sus
practicantes asignados, RN-01, CU-06).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Optional, Union

from dominio.errores import ErrorDominio
from dominio.modelos.estudiante import Estudiante


class RolUsuario(str, Enum):
    """Roles formales definidos en el sistema de prácticas empresariales (RN-03, ADR-005)."""

    ESTUDIANTE = "Estudiante"
    DOCENTE = "Docente"
    DOCENTE_ASESOR = "DocenteAsesor"
    COORDINADOR = "Coordinador"
    COORDINADOR_PRACTICAS = "CoordinadorPracticas"
    SUPERVISOR = "Supervisor"
    SUPERVISOR_EMPRESA = "SupervisorEmpresa"


@dataclass(frozen=True, slots=True)
class ContextoUsuario:
    """Contexto inmutable de identidad del usuario autenticado (ADR-004, ADR-005).

    Atributos:
        usuario_id: Identificador único del usuario o sujeto autenticado.
        rol: Rol autenticado del usuario (ej. 'Estudiante', 'Docente', 'Coordinador').
        documento: Documento de identidad (opcional, aplicable a estudiantes y docentes).
        correo: Correo electrónico institucional o corporativo.
        ip_origen: Dirección IP del cliente para trazabilidad y bitácora (ADR-006).
    """

    usuario_id: str
    rol: str
    documento: Optional[str] = None
    correo: Optional[str] = None
    ip_origen: str = "127.0.0.1"

    def __post_init__(self) -> None:
        if not self.usuario_id or not self.usuario_id.strip():
            raise ValueError("El identificador de usuario no puede estar vacío.")
        if not self.rol or not self.rol.strip():
            raise ValueError("El rol del usuario no puede estar vacío.")
        object.__setattr__(self, "usuario_id", self.usuario_id.strip())
        object.__setattr__(self, "rol", self.rol.strip())
        if self.documento is not None:
            object.__setattr__(self, "documento", self.documento.strip())
        if self.correo is not None:
            object.__setattr__(self, "correo", self.correo.strip())
        if self.ip_origen is not None:
            object.__setattr__(self, "ip_origen", self.ip_origen.strip())


class AccesoDenegadoError(ErrorDominio):
    """Excepción lanzada cuando una operación o recurso es denegado por el Autorizador RBAC (ADR-005).

    Se arroja ante violaciones de roles, operaciones no permitidas o quebrantamiento
    del contexto de pertenencia de datos (política deny-by-default, RN-01, RN-03).
    """

    def __init__(
        self,
        mensaje: str,
        *,
        rol_actor: Optional[str] = None,
        operacion: Optional[str] = None,
        usuario_id: Optional[str] = None,
    ) -> None:
        self.rol_actor: Optional[str] = rol_actor
        self.operacion: Optional[str] = operacion
        self.usuario_id: Optional[str] = usuario_id
        super().__init__(mensaje)

    def __repr__(self) -> str:
        return (
            f"AccesoDenegadoError("
            f"mensaje={self.mensaje!r}, "
            f"rol_actor={self.rol_actor!r}, "
            f"operacion={self.operacion!r}, "
            f"usuario_id={self.usuario_id!r})"
        )


class AutorizadorRBAC:
    """Componente transversal de autorización RBAC centralizado en la capa de Aplicación.

    Aplica una política estricta de *deny-by-default* (ADR-005): cualquier operación
    no registrada explícitamente o cualquier actor sin el rol requerido es denegado.
    Asimismo, valida el contexto de pertenencia (un estudiante solo accede a sus propios
    datos, previniendo suplantaciones y cumpliendo la Ley 1581 / RN-01).
    """

    # Matriz canónica de operaciones y roles permitidos (deny-by-default)
    _MATRIZ_PERMISOS: dict[str, set[str]] = {
        "postular_practica": {
            RolUsuario.ESTUDIANTE.value,
        },
        "consultar_postulacion": {
            RolUsuario.ESTUDIANTE.value,
            RolUsuario.COORDINADOR.value,
            RolUsuario.COORDINADOR_PRACTICAS.value,
        },
        "evaluar_postulacion": {
            RolUsuario.COORDINADOR.value,
            RolUsuario.COORDINADOR_PRACTICAS.value,
        },
        "aprobar_postulacion": {
            RolUsuario.COORDINADOR.value,
            RolUsuario.COORDINADOR_PRACTICAS.value,
        },
        "rechazar_postulacion": {
            RolUsuario.COORDINADOR.value,
            RolUsuario.COORDINADOR_PRACTICAS.value,
        },
        "asignar_tutor": {
            RolUsuario.COORDINADOR.value,
            RolUsuario.COORDINADOR_PRACTICAS.value,
        },
        "registrar_horas": {
            RolUsuario.ESTUDIANTE.value,
        },
        "aprobar_horas": {
            RolUsuario.SUPERVISOR.value,
            RolUsuario.SUPERVISOR_EMPRESA.value,
            RolUsuario.DOCENTE.value,
            RolUsuario.DOCENTE_ASESOR.value,
        },
        "validar_horas": {
            RolUsuario.SUPERVISOR.value,
            RolUsuario.SUPERVISOR_EMPRESA.value,
        },
        "revisar_avances_horas": {
            RolUsuario.DOCENTE.value,
            RolUsuario.DOCENTE_ASESOR.value,
            RolUsuario.ESTUDIANTE.value,
        },
        "listar_avances_docente": {
            RolUsuario.DOCENTE.value,
            RolUsuario.DOCENTE_ASESOR.value,
        },
        "evaluar_desempeno": {
            RolUsuario.SUPERVISOR.value,
            RolUsuario.SUPERVISOR_EMPRESA.value,
        },
        "generar_acta": {
            RolUsuario.DOCENTE.value,
            RolUsuario.DOCENTE_ASESOR.value,
        },
        "aprobar_acta_docente": {
            RolUsuario.DOCENTE.value,
            RolUsuario.DOCENTE_ASESOR.value,
        },
        "aprobar_acta_coordinador": {
            RolUsuario.COORDINADOR.value,
            RolUsuario.COORDINADOR_PRACTICAS.value,
        },
        "configurar_reglas": {
            RolUsuario.COORDINADOR.value,
            RolUsuario.COORDINADOR_PRACTICAS.value,
        },
    }

    # Alias reconocidos para normalización flexible de roles
    _ALIAS_ROLES: dict[str, str] = {
        "estudiante": RolUsuario.ESTUDIANTE.value,
        "docente": RolUsuario.DOCENTE.value,
        "docenteasesor": RolUsuario.DOCENTE_ASESOR.value,
        "docente_asesor": RolUsuario.DOCENTE_ASESOR.value,
        "coordinador": RolUsuario.COORDINADOR.value,
        "coordinadorpracticas": RolUsuario.COORDINADOR_PRACTICAS.value,
        "coordinador_practicas": RolUsuario.COORDINADOR_PRACTICAS.value,
        "coordinador de prácticas": RolUsuario.COORDINADOR_PRACTICAS.value,
        "coordinador de practicas": RolUsuario.COORDINADOR_PRACTICAS.value,
        "supervisor": RolUsuario.SUPERVISOR.value,
        "supervisorempresa": RolUsuario.SUPERVISOR_EMPRESA.value,
        "supervisor_empresa": RolUsuario.SUPERVISOR_EMPRESA.value,
    }

    @classmethod
    def normalizar_rol(cls, rol: str) -> str:
        """Normaliza el nombre de un rol al formato estándar."""
        if not rol or not rol.strip():
            return ""
        clave = rol.strip().lower()
        return cls._ALIAS_ROLES.get(clave, rol.strip())

    def validar_rol(
        self,
        rol_actor: str,
        roles_permitidos: Iterable[str],
        operacion: Optional[str] = None,
        usuario_id: Optional[str] = None,
    ) -> None:
        """Verifica que el rol del actor pertenezca al conjunto de roles permitidos.

        Política deny-by-default: si roles_permitidos está vacío o None, deniega el acceso.

        Args:
            rol_actor: Rol presentado por el usuario autenticado.
            roles_permitidos: Colección de roles que tienen autorización.
            operacion: Nombre de la operación (opcional, para diagnóstico y trazabilidad).
            usuario_id: Identificador del usuario (opcional).

        Raises:
            AccesoDenegadoError: Si el rol del actor no está entre los permitidos.
        """
        if not rol_actor or not rol_actor.strip():
            raise AccesoDenegadoError(
                "Acceso denegado: No se ha provisto un rol de usuario válido.",
                rol_actor=rol_actor,
                operacion=operacion,
                usuario_id=usuario_id,
            )

        rol_normalizado = self.normalizar_rol(rol_actor)
        permitidos_normalizados = {self.normalizar_rol(r) for r in roles_permitidos if r}

        if not permitidos_normalizados or rol_normalizado not in permitidos_normalizados:
            detalle_op = f" para la operación '{operacion}'" if operacion else ""
            raise AccesoDenegadoError(
                f"Acceso denegado{detalle_op}: El rol '{rol_actor}' no tiene permisos suficientes. "
                f"Roles permitidos: {sorted(permitidos_normalizados)}.",
                rol_actor=rol_actor,
                operacion=operacion,
                usuario_id=usuario_id,
            )

    def validar_operacion(
        self,
        contexto: ContextoUsuario,
        operacion: str,
    ) -> None:
        """Valida una operación contra la matriz de permisos bajo política deny-by-default.

        Args:
            contexto: Contexto de identidad del usuario autenticado.
            operacion: Nombre de la operación a ejecutar.

        Raises:
            AccesoDenegadoError: Si la operación no existe en la matriz o el rol no está autorizado.
        """
        if operacion not in self._MATRIZ_PERMISOS:
            raise AccesoDenegadoError(
                f"Acceso denegado: Operación '{operacion}' no autorizada o no configurada "
                f"(política deny-by-default).",
                rol_actor=contexto.rol,
                operacion=operacion,
                usuario_id=contexto.usuario_id,
            )

        roles_permitidos = self._MATRIZ_PERMISOS[operacion]
        self.validar_rol(
            rol_actor=contexto.rol,
            roles_permitidos=roles_permitidos,
            operacion=operacion,
            usuario_id=contexto.usuario_id,
        )

    def validar_pertenencia_estudiante(
        self,
        contexto: ContextoUsuario,
        estudiante: Union[Estudiante, str],
        operacion: Optional[str] = None,
    ) -> None:
        """Valida que un estudiante solo interactúe con sus propios recursos (RN-01, ADR-005).

        Si el rol del usuario autenticado es 'Estudiante', debe coincidir su identificador
        o documento con el del estudiante involucrado en la solicitud.

        Args:
            contexto: Contexto de identidad del usuario autenticado.
            estudiante: Instancia de Estudiante o identificador/documento del estudiante objetivo.
            operacion: Operación invocada (opcional).

        Raises:
            AccesoDenegadoError: Si el estudiante autenticado intenta acceder a datos de otro estudiante.
        """
        rol_normalizado = self.normalizar_rol(contexto.rol)
        if rol_normalizado == RolUsuario.ESTUDIANTE.value:
            if isinstance(estudiante, Estudiante):
                coincide = (
                    contexto.usuario_id == estudiante.id
                    or contexto.usuario_id == estudiante.documento
                    or (contexto.documento is not None and contexto.documento == estudiante.documento)
                )
                identificador_objetivo = estudiante.documento or estudiante.id
            else:
                target_str = str(estudiante).strip()
                coincide = (
                    contexto.usuario_id == target_str
                    or (contexto.documento is not None and contexto.documento == target_str)
                )
                identificador_objetivo = target_str

            if not coincide:
                detalle_op = f" para la operación '{operacion}'" if operacion else ""
                raise AccesoDenegadoError(
                    f"Violación de contexto de identidad{detalle_op}: El estudiante autenticado "
                    f"'{contexto.usuario_id}' no está autorizado para acceder o gestionar la práctica "
                    f"del estudiante '{identificador_objetivo}' (RN-01).",
                    rol_actor=contexto.rol,
                    operacion=operacion,
                    usuario_id=contexto.usuario_id,
                )

    def validar_postulacion(
        self,
        rol_actor: str,
        estudiante_id: Optional[str] = None,
        usuario_id: Optional[str] = None,
    ) -> None:
        """Valida las autorizaciones específicas para el caso de uso de postulación (CU-01).

        Asegura que:
        1. El actor posea estrictamente el rol 'Estudiante'.
        2. Si se proporciona usuario_id y estudiante_id, que pertenezcan al mismo titular (RN-01).

        Args:
            rol_actor: Rol autenticado del solicitante.
            estudiante_id: Identificador o documento del estudiante para el cual se postula.
            usuario_id: Identificador del usuario autenticado (opcional).

        Raises:
            AccesoDenegadoError: Si no cuenta con rol Estudiante o no coincide la identidad.
        """
        # 1. Validación de rol
        self.validar_rol(
            rol_actor=rol_actor,
            roles_permitidos=[RolUsuario.ESTUDIANTE.value],
            operacion="postular_practica",
            usuario_id=usuario_id,
        )

        # 2. Validación de pertenencia contextual si ambos identificadores están presentes
        if usuario_id and estudiante_id:
            uid = usuario_id.strip()
            eid = estudiante_id.strip()
            if uid != eid:
                raise AccesoDenegadoError(
                    f"Violación de contexto de identidad: El usuario autenticado '{uid}' "
                    f"no puede registrar una postulación a nombre de '{eid}' (RN-01).",
                    rol_actor=rol_actor,
                    operacion="postular_practica",
                    usuario_id=usuario_id,
                )

    def autorizar_comando_postulacion(
        self,
        comando: Any,
    ) -> None:
        """Valida un comando de postulación (PostularEstudianteComando) de la capa de aplicación.

        Verifica el rol_actor y la coincidencia entre estudiante_id / documento y el solicitante.
        """
        rol = getattr(comando, "rol_actor", None)
        estudiante_id = getattr(comando, "estudiante_id", None) or getattr(comando, "documento", None)
        usuario_id = getattr(comando, "estudiante_id", None) or getattr(comando, "documento", None)
        self.validar_postulacion(
            rol_actor=rol,
            estudiante_id=estudiante_id,
            usuario_id=usuario_id,
        )

    def validar_evaluacion_postulacion(
        self,
        rol_actor: str,
        usuario_id: Optional[str] = None,
        operacion: str = "evaluar_postulacion",
    ) -> None:
        """Valida las autorizaciones específicas para el caso de uso de evaluación de postulación (CU-02).

        Asegura que el actor posea estrictamente el rol 'Coordinador' o 'CoordinadorPracticas'
        bajo política deny-by-default (ADR-005, EAC-03).

        Args:
            rol_actor: Rol presentado por el usuario autenticado.
            usuario_id: Identificador del usuario (opcional).
            operacion: Nombre de la operación evaluada ('evaluar_postulacion', 'aprobar_postulacion', 'rechazar_postulacion').

        Raises:
            AccesoDenegadoError: Si el rol del actor no pertenece a los roles de Coordinador autorizados.
        """
        self.validar_rol(
            rol_actor=rol_actor,
            roles_permitidos=[
                RolUsuario.COORDINADOR.value,
                RolUsuario.COORDINADOR_PRACTICAS.value,
            ],
            operacion=operacion,
            usuario_id=usuario_id,
        )

    def autorizar_comando_evaluacion(
        self,
        comando: Any,
    ) -> None:
        """Valida un comando de evaluación de postulación (EvaluarPostulacionComando).

        Aplica política deny-by-default verificando que rol_actor sea de Coordinador.
        """
        rol = getattr(comando, "rol_actor", None)
        actor_id = getattr(comando, "actor_id", None)
        operacion = (
            "aprobar_postulacion"
            if getattr(comando, "es_aprobacion", False)
            else "rechazar_postulacion"
            if getattr(comando, "es_rechazo", False)
            else "evaluar_postulacion"
        )
        self.validar_evaluacion_postulacion(
            rol_actor=rol,
            usuario_id=actor_id,
            operacion=operacion,
        )

    def validar_asignacion_tutor(
        self,
        rol_actor: str,
        usuario_id: Optional[str] = None,
        operacion: str = "asignar_tutor",
    ) -> None:
        """Valida las autorizaciones específicas para asignación de docente asesor (CU-03).

        Asegura que el actor posea estrictamente el rol 'Coordinador' o 'CoordinadorPracticas'
        bajo política deny-by-default (ADR-005, EAC-03).

        Args:
            rol_actor: Rol presentado por el usuario autenticado.
            usuario_id: Identificador del usuario (opcional).
            operacion: Nombre de la operación evaluada ('asignar_tutor').

        Raises:
            AccesoDenegadoError: Si el rol del actor no pertenece a los roles de Coordinador autorizados.
        """
        self.validar_rol(
            rol_actor=rol_actor,
            roles_permitidos=[
                RolUsuario.COORDINADOR.value,
                RolUsuario.COORDINADOR_PRACTICAS.value,
            ],
            operacion=operacion,
            usuario_id=usuario_id,
        )

    def autorizar_comando_asignacion(
        self,
        comando: Any,
    ) -> None:
        """Valida un comando de asignación de tutor (AsignarDocenteComando).

        Aplica política deny-by-default verificando que rol_actor sea de Coordinador.
        """
        rol = getattr(comando, "rol_actor", None)
        actor_id = getattr(comando, "actor_id", None)
        self.validar_asignacion_tutor(
            rol_actor=rol,
            usuario_id=actor_id,
            operacion="asignar_tutor",
        )

    def validar_registro_horas(
        self,
        rol_actor: str,
        usuario_id: Optional[str] = None,
        operacion: str = "registrar_horas",
    ) -> None:
        """Valida las autorizaciones específicas para el registro de horas semanales (CU-04).

        Asegura que el actor posea estrictamente el rol 'Estudiante'
        bajo política deny-by-default (ADR-005, EAC-03).

        Args:
            rol_actor: Rol presentado por el usuario autenticado.
            usuario_id: Identificador del usuario (opcional).
            operacion: Nombre de la operación evaluada ('registrar_horas').

        Raises:
            AccesoDenegadoError: Si el rol del actor no pertenece a los roles autorizados.
        """
        self.validar_rol(
            rol_actor=rol_actor,
            roles_permitidos=[RolUsuario.ESTUDIANTE.value],
            operacion=operacion,
            usuario_id=usuario_id,
        )

    def autorizar_comando_registro_horas(
        self,
        comando: Any,
    ) -> None:
        """Valida un comando de registro de horas (RegistrarHorasComando).

        Aplica política deny-by-default verificando que rol_actor sea de Estudiante.
        """
        rol = getattr(comando, "rol_actor", None)
        actor_id = getattr(comando, "actor_id", None)
        self.validar_registro_horas(
            rol_actor=rol,
            usuario_id=actor_id,
            operacion="registrar_horas",
        )

    def validar_validacion_horas(
        self,
        rol_actor: str,
        usuario_id: Optional[str] = None,
        operacion: str = "validar_horas",
    ) -> None:
        """Valida las autorizaciones específicas para el caso de uso de validación de horas (CU-05).

        Asegura que el actor posea el rol ``SupervisorEmpresa`` o ``Supervisor``
        bajo política deny-by-default (ADR-005, EAC-03, plan.md CU-05).

        Args:
            rol_actor: Rol presentado por el usuario autenticado.
            usuario_id: Identificador del usuario (opcional).
            operacion: Nombre de la operación evaluada ('validar_horas').

        Raises:
            AccesoDenegadoError: Si el rol del actor no es Supervisor o SupervisorEmpresa.
        """
        self.validar_rol(
            rol_actor=rol_actor,
            roles_permitidos=[
                RolUsuario.SUPERVISOR.value,
                RolUsuario.SUPERVISOR_EMPRESA.value,
            ],
            operacion=operacion,
            usuario_id=usuario_id,
        )

    def validar_pertenencia_supervisor(
        self,
        contexto: ContextoUsuario,
        supervisor_asignado_id: str,
        operacion: Optional[str] = None,
    ) -> None:
        """Valida que el supervisor opere exclusivamente sobre su propia práctica asignada.

        Traza: CU-05, Escenario 6 (Intento de validación sobre reporte de práctica ajena),
        RN-01 (Pertenencia contextual de datos), ADR-005 (RBAC centralizado).

        Si el rol del actor es Supervisor o SupervisorEmpresa, verifica que su
        ``usuario_id`` coincida con el ``supervisor_asignado_id`` de la práctica.
        El intento de acceder a prácticas ajenas es bloqueado sin exponer datos.

        Args:
            contexto: Contexto de identidad del actor autenticado.
            supervisor_asignado_id: Identificador del supervisor registrado en la práctica.
            operacion: Operación invocada (opcional, para diagnóstico).

        Raises:
            AccesoDenegadoError: Si el supervisor no coincide con el asignado a la práctica.
        """
        from dominio.errores import SupervisorNoAsignadoAPracticaError  # evita ciclo

        rol_normalizado = self.normalizar_rol(contexto.rol)
        roles_supervisor = {
            self.normalizar_rol(RolUsuario.SUPERVISOR.value),
            self.normalizar_rol(RolUsuario.SUPERVISOR_EMPRESA.value),
        }

        if rol_normalizado in roles_supervisor:
            if contexto.usuario_id != supervisor_asignado_id.strip():
                detalle_op = f" para la operación '{operacion}'" if operacion else ""
                raise AccesoDenegadoError(
                    f"Violación de pertenencia contextual{detalle_op}: El supervisor "
                    f"'{contexto.usuario_id}' no está asignado a la práctica del supervisor "
                    f"'{supervisor_asignado_id}' (RN-01). Acceso denegado.",
                    rol_actor=contexto.rol,
                    operacion=operacion,
                    usuario_id=contexto.usuario_id,
                )

    def validar_revision_avances_horas(
        self,
        rol_actor: str,
        usuario_id: Optional[str] = None,
        operacion: str = "revisar_avances_horas",
    ) -> None:
        """Valida las autorizaciones específicas para el caso de uso de revisión de avances de horas (CU-06).

        Asegura que el actor posea estrictamente el rol ``DocenteAsesor`` (o ``Docente``) o ``Estudiante``
        para la consulta individual (``revisar_avances_horas``), o exclusivamente ``DocenteAsesor`` (o ``Docente``)
        para la consulta consolidada (``listar_avances_docente``), bajo política deny-by-default (ADR-005, EAC-03).
        El rol ``Coordinador de prácticas`` (quien utiliza CU-13) y ``SupervisorEmpresa`` están excluidos.

        Args:
            rol_actor: Rol presentado por el usuario autenticado.
            usuario_id: Identificador del usuario (opcional).
            operacion: Nombre de la operación evaluada ('revisar_avances_horas' o 'listar_avances_docente').

        Raises:
            AccesoDenegadoError: Si el rol del actor no está autorizado para la operación en CU-06.
        """
        roles_permitidos = self._MATRIZ_PERMISOS.get(
            operacion,
            {
                RolUsuario.DOCENTE.value,
                RolUsuario.DOCENTE_ASESOR.value,
                RolUsuario.ESTUDIANTE.value,
            },
        )
        self.validar_rol(
            rol_actor=rol_actor,
            roles_permitidos=roles_permitidos,
            operacion=operacion,
            usuario_id=usuario_id,
        )

    def validar_pertenencia_docente(
        self,
        contexto: ContextoUsuario,
        docente_asignado_id: Optional[str],
        operacion: Optional[str] = None,
    ) -> None:
        """Valida que un docente asesor solo consulte prácticas donde figure como tutor asignado (CU-06).

        Traza: CU-06, Escenarios 1, 6, 7 y 9 (Pertenencia contextual docente-práctica y práctica sin tutor),
        RN-01 (Pertenencia contextual de datos), ADR-005 (RBAC centralizado), EAC-03 (0 datos expuestos).

        Si el actor autenticado tiene rol ``Docente`` o ``DocenteAsesor``, verifica que:
        1. La práctica cuente con un ``docente_asignado_id`` no nulo ni vacío.
        2. El ``docente_asignado_id`` coincida exactamente con ``contexto.usuario_id``.

        Args:
            contexto: Contexto de identidad del usuario autenticado.
            docente_asignado_id: Identificador del docente asesor asignado a la práctica (puede ser None).
            operacion: Operación invocada (opcional, para diagnóstico y bitácora).

        Raises:
            AccesoDenegadoError: Si la práctica no tiene docente asignado o está asignada a otro docente asesor.
        """
        rol_normalizado = self.normalizar_rol(contexto.rol)
        roles_docente = {
            self.normalizar_rol(RolUsuario.DOCENTE.value),
            self.normalizar_rol(RolUsuario.DOCENTE_ASESOR.value),
        }

        if rol_normalizado in roles_docente:
            detalle_op = f" para la operación '{operacion}'" if operacion else ""
            if not docente_asignado_id or not str(docente_asignado_id).strip():
                raise AccesoDenegadoError(
                    f"Violación de pertenencia contextual{detalle_op}: La práctica consultada aún no "
                    f"tiene un docente asesor asignado. El docente '{contexto.usuario_id}' no tiene "
                    f"tutoría vigente sobre esta práctica (RN-01).",
                    rol_actor=contexto.rol,
                    operacion=operacion,
                    usuario_id=contexto.usuario_id,
                )

            docente_objetivo = str(docente_asignado_id).strip()
            if contexto.usuario_id != docente_objetivo:
                raise AccesoDenegadoError(
                    f"Violación de pertenencia contextual{detalle_op}: El docente asesor autenticado "
                    f"'{contexto.usuario_id}' no está autorizado para acceder a la práctica asignada "
                    f"al docente '{docente_objetivo}' (RN-01).",
                    rol_actor=contexto.rol,
                    operacion=operacion,
                    usuario_id=contexto.usuario_id,
                )

    def validar_evaluacion_desempeno(
        self,
        rol_actor: str,
        usuario_id: Optional[str] = None,
        operacion: str = "evaluar_desempeno",
    ) -> None:
        """Valida las autorizaciones específicas para el caso de uso de evaluación de desempeño (CU-07).

        Asegura que el actor posea estrictamente el rol ``SupervisorEmpresa`` o ``Supervisor``
        bajo política deny-by-default (ADR-005, EAC-03, RN-03). Cualquier intento por roles
        internos (Estudiante, DocenteAsesor, Coordinador de prácticas) es denegado.

        Args:
            rol_actor: Rol presentado por el usuario autenticado.
            usuario_id: Identificador del usuario (opcional).
            operacion: Nombre de la operación evaluada ('evaluar_desempeno').

        Raises:
            AccesoDenegadoError: Si el rol del actor no es Supervisor o SupervisorEmpresa.
        """
        self.validar_rol(
            rol_actor=rol_actor,
            roles_permitidos=[
                RolUsuario.SUPERVISOR.value,
                RolUsuario.SUPERVISOR_EMPRESA.value,
            ],
            operacion=operacion,
            usuario_id=usuario_id,
        )



