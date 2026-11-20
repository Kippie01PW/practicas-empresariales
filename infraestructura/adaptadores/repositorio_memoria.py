"""Adaptadores de persistencia en memoria para Práctica, ReglaPrograma, DocenteAsesor, RegistroHoras, TokenEvaluacion, EvaluacionDesempeno, ActaFinal y Bitácora.

Traza: CU-01, CU-02, CU-03, CU-04, CU-05, CU-06, CU-07, CU-09, CU-10, CU-11, CU-12, EAC-01, EAC-02, EAC-03, RT-01, RN-01, RN-02, RN-03, RN-04, DT-02, ADR-001, ADR-002, ADR-003, ADR-004, ADR-006, ADR-007, ADR-008, ADR-010.
Vista Lógica §2, Vista de Desarrollo §2.

Implementa los puertos `RepositorioPracticaPort`, `RepositorioReglaProgramaPort`,
`RepositorioDocentePort`, `RepositorioRegistroHorasPort`, `RepositorioTokenEvaluacionPort`,
`RepositorioEvaluacionDesempenoPort` y `RepositorioActaFinalPort` utilizando estructuras en
memoria deterministas para pruebas y validación sin dependencias externas ni bases de datos
reales en esta etapa (ADR-002, ADR-003, ADR-004, ADR-008).
"""

from __future__ import annotations

from typing import Optional

from aplicacion.puertos.repositorio_acta_final import RepositorioActaFinalPort
from aplicacion.puertos.repositorio_docente import RepositorioDocentePort
from aplicacion.puertos.repositorio_evaluacion_desempeno import (
    RepositorioEvaluacionDesempenoPort,
)
from aplicacion.puertos.repositorio_practica import RepositorioPracticaPort
from aplicacion.puertos.repositorio_registro_horas import RepositorioRegistroHorasPort
from aplicacion.puertos.repositorio_regla import RepositorioReglaProgramaPort
from aplicacion.puertos.repositorio_token_evaluacion import RepositorioTokenEvaluacionPort
from dominio.errores import ErrorAlmacenamientoActaPdfError
from dominio.modelos.acta_final import ActaFinal
from dominio.modelos.docente_asesor import DocenteAsesor
from dominio.modelos.evaluacion_desempeno import EvaluacionDesempeno
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.intento_validacion import IntentoValidacion
from dominio.modelos.practica import EstadoPractica, Practica
from dominio.modelos.registro_horas import RegistroHoras
from dominio.modelos.regla_programa import EstadoVigenciaRegla, ReglaPrograma
from dominio.modelos.token_evaluacion import TokenEvaluacion


class InMemoryRepositorioPractica(RepositorioPracticaPort):
    """Implementación en memoria del puerto RepositorioPracticaPort.

    Almacena las instancias de Practica, Intentos de Validación y Eventos de Bitácora
    en estructuras de diccionario y listas en memoria.
    """

    def __init__(self) -> None:
        self._practicas: dict[str, Practica] = {}
        self._intentos: dict[str, list[IntentoValidacion]] = {}
        self._eventos: list[EventoBitacora] = []

    def guardar(self, practica: Practica) -> None:
        """Persiste una nueva práctica en el almacén en memoria."""
        self._practicas[practica.id] = practica

    def actualizar(self, practica: Practica) -> None:
        """Actualiza una práctica existente en el almacén en memoria."""
        self._practicas[practica.id] = practica

    def buscar_por_id(self, practica_id: str) -> Optional[Practica]:
        """Busca y retorna una práctica por su identificador único."""
        return self._practicas.get(practica_id)

    def buscar_activa_por_estudiante(self, estudiante_id: str) -> Optional[Practica]:
        """Busca si el estudiante cuenta con una práctica activa en curso.

        Estados considerados como práctica activa:
            Aprobada, Asignada, EnEjecucion, Evaluada (ADR-010, spec.md escenario 3).
        """
        for practica in self._practicas.values():
            if practica.estudiante_id == estudiante_id and practica.es_activa():
                return practica
        return None

    def buscar_mas_reciente_o_activa_por_estudiante(
        self, estudiante_id: str
    ) -> Optional[Practica]:
        """Busca la práctica activa en curso o la más reciente de un estudiante (CU-11).

        Traza: CU-11, Escenarios 7, 8 y 13, plan.md. ADR-002, ADR-003, ADR-010.

        Filtra todas las prácticas pertenecientes al estudiante:
        - Si el estudiante no cuenta con ninguna práctica registrada, retorna `None` (Escenario 8).
        - Si existe al menos una práctica activa en curso (`practica.es_activa() == True`),
          la prioriza sobre postulaciones previas rechazadas o históricas (Escenario 7).
        - Si existen varias prácticas en el grupo candidato, retorna la más reciente según
          `fecha_postulacion`, preservando el último registro insertado como desempate
          determinista en caso de empate de timestamp (Escenarios 7 y 13).
        """
        if not estudiante_id:
            return None
        estudiante_id_limpio = str(estudiante_id).strip()
        if not estudiante_id_limpio:
            return None

        candidatas: list[tuple[int, Practica]] = [
            (indice, practica)
            for indice, practica in enumerate(self._practicas.values())
            if practica.estudiante_id == estudiante_id_limpio
        ]
        if not candidatas:
            return None

        activas: list[tuple[int, Practica]] = [
            (indice, practica)
            for indice, practica in candidatas
            if practica.es_activa()
        ]
        grupo_seleccionado = activas if activas else candidatas
        _, practica_seleccionada = max(
            grupo_seleccionado,
            key=lambda par: (par[1].fecha_postulacion, par[0]),
        )
        return practica_seleccionada

    def listar_por_docente(self, docente_asesor_id: str) -> list[Practica]:
        """Retorna las prácticas asignadas al docente asesor indicado (CU-06, RN-01, RT-01).

        Filtra estrictamente aquellas prácticas cuyo tutor asignado coincide con el
        identificador solicitado, sin exponer prácticas asignadas a otros tutores.
        """
        docente_id_limpio = docente_asesor_id.strip()
        if not docente_id_limpio:
            return []
        return [
            p
            for p in self._practicas.values()
            if p.docente_asesor_id == docente_id_limpio
        ]

    def guardar_intento_validacion(self, intento: IntentoValidacion) -> None:
        """Registra un intento de validación frente al SIA (ADR-001, EAC-02)."""
        if intento.practica_id not in self._intentos:
            self._intentos[intento.practica_id] = []
        self._intentos[intento.practica_id].append(intento)

    def buscar_intentos_por_practica(self, practica_id: str) -> list[IntentoValidacion]:
        """Recupera el historial de intentos de validación de una práctica ordenados por fecha/intento."""
        intentos = self._intentos.get(practica_id, [])
        return sorted(intentos, key=lambda i: (i.numero_intento, i.fecha_intento))

    def guardar_evento_bitacora(self, evento: EventoBitacora) -> None:
        """Registra un evento inmutable en la bitácora append-only (ADR-006)."""
        self._eventos.append(evento)

    def buscar_eventos_por_entidad(self, entidad_afectada: str) -> list[EventoBitacora]:
        """Recupera los eventos de bitácora asociados a una entidad específica."""
        return [e for e in self._eventos if e.entidad_afectada == entidad_afectada]

    def listar_todas(self) -> list[Practica]:
        """Retorna todas las prácticas almacenadas."""
        return list(self._practicas.values())

    def listar_por_estado(self, estado: EstadoPractica | str) -> list[Practica]:
        """Retorna las prácticas que coincidan con un estado específico (ej. 'Solicitada')."""
        valor_estado = estado.value if isinstance(estado, EstadoPractica) else str(estado)
        return [p for p in self._practicas.values() if p.estado_actual.value == valor_estado]

    def listar_todos_eventos(self) -> list[EventoBitacora]:
        """Retorna todos los eventos de auditoría registrados."""
        return list(self._eventos)

    def limpiar(self) -> None:
        """Limpia el almacenamiento en memoria (útil para pruebas)."""
        self._practicas.clear()
        self._intentos.clear()
        self._eventos.clear()


class InMemoryRepositorioReglaPrograma(RepositorioReglaProgramaPort):
    """Implementación en memoria del puerto RepositorioReglaProgramaPort.

    Almacena y consulta las reglas normativas y plantillas versionadas por programa académico.
    """

    def __init__(self, reglas_iniciales: Optional[list[ReglaPrograma]] = None) -> None:
        self._reglas: dict[str, ReglaPrograma] = {}
        if reglas_iniciales:
            for regla in reglas_iniciales:
                self.guardar(regla)

    def guardar(self, regla: ReglaPrograma) -> None:
        """Persiste una regla de programa versionada."""
        self._reglas[regla.id] = regla

    def buscar_por_id(self, regla_id: str) -> Optional[ReglaPrograma]:
        """Recupera una regla de programa por su identificador único."""
        return self._reglas.get(regla_id)

    def buscar_activa_por_programa(
        self, programa_academico: str
    ) -> Optional[ReglaPrograma]:
        """Recupera la regla de programa actualmente activa y vigente para un programa.

        Si existen varias versiones activas, retorna la de vigencia más reciente.
        """
        candidatas = [
            r
            for r in self._reglas.values()
            if r.programa_academico == programa_academico and r.es_activa()
        ]
        if not candidatas:
            return None
        candidatas.sort(key=lambda r: r.fecha_vigencia, reverse=True)
        return candidatas[0]

    def listar_todas(self) -> list[ReglaPrograma]:
        """Retorna todas las reglas configuradas."""
        return list(self._reglas.values())

    def limpiar(self) -> None:
        """Limpia las reglas almacenadas."""
        self._reglas.clear()


class InMemoryRepositorioDocente(RepositorioDocentePort):
    """Implementación en memoria del puerto RepositorioDocentePort.

    Almacena los tutores académicos y gestiona la consulta de disponibilidad
    y actualización de cupos de prácticas empresariales (RT-01, CU-03).
    """

    def __init__(self, docentes_iniciales: Optional[list[DocenteAsesor]] = None) -> None:
        self._docentes: dict[str, DocenteAsesor] = {}
        if docentes_iniciales:
            for docente in docentes_iniciales:
                self.guardar(docente)

    def guardar(self, docente: DocenteAsesor) -> None:
        """Persiste un nuevo docente asesor en el almacén en memoria."""
        self._docentes[docente.id] = docente

    def actualizar(self, docente: DocenteAsesor) -> None:
        """Actualiza un docente asesor existente en el almacén en memoria."""
        self._docentes[docente.id] = docente

    def buscar_por_id(self, docente_id: str) -> Optional[DocenteAsesor]:
        """Busca y retorna un docente asesor por su identificador único."""
        return self._docentes.get(docente_id)

    def buscar_por_documento(self, documento: str) -> Optional[DocenteAsesor]:
        """Busca y retorna un docente asesor por su documento de identidad."""
        doc_limpio = documento.strip()
        for docente in self._docentes.values():
            if docente.documento == doc_limpio:
                return docente
        return None

    def listar_disponibles(self) -> list[DocenteAsesor]:
        """Retorna todos los docentes activos que cuentan con cupo libre."""
        return [d for d in self._docentes.values() if d.tiene_cupo_disponible()]

    def listar_todos(self) -> list[DocenteAsesor]:
        """Retorna todos los docentes asesores registrados."""
        return list(self._docentes.values())

    def limpiar(self) -> None:
        """Limpia los docentes almacenados (útil para pruebas)."""
        self._docentes.clear()


class InMemoryRepositorioRegistroHoras(RepositorioRegistroHorasPort):
    """Implementación en memoria del puerto RepositorioRegistroHorasPort.

    Almacena los reportes semanales de horas de práctica, asegurando consistencia
    transaccional, detección de reportes duplicados y consulta por práctica (RT-01, CU-04).
    """

    def __init__(self, registros_iniciales: Optional[list[RegistroHoras]] = None) -> None:
        self._registros: dict[str, RegistroHoras] = {}
        if registros_iniciales:
            for registro in registros_iniciales:
                self.guardar(registro)

    def guardar(self, registro: RegistroHoras) -> None:
        """Persiste un nuevo reporte de horas en memoria."""
        self._registros[registro.id] = registro

    def buscar_por_id(self, registro_id: str) -> Optional[RegistroHoras]:
        """Busca y retorna un reporte de horas por su identificador único."""
        return self._registros.get(registro_id)

    def buscar_por_practica_y_semana(
        self, practica_id: str, semana: int
    ) -> Optional[RegistroHoras]:
        """Busca si ya existe un reporte de horas para una práctica y semana determinadas."""
        for registro in self._registros.values():
            if registro.practica_id == practica_id and registro.semana == semana:
                return registro
        return None

    def listar_por_practica(self, practica_id: str) -> list[RegistroHoras]:
        """Retorna todos los reportes de horas de una práctica ordenados por semana."""
        registros = [r for r in self._registros.values() if r.practica_id == practica_id]
        return sorted(registros, key=lambda r: r.semana)

    def listar_todos(self) -> list[RegistroHoras]:
        """Retorna todos los reportes de horas almacenados."""
        return list(self._registros.values())

    def limpiar(self) -> None:
        """Limpia los registros almacenados (útil para pruebas)."""
        self._registros.clear()


class InMemoryRepositorioTokenEvaluacion(RepositorioTokenEvaluacionPort):
    """Implementación en memoria del puerto RepositorioTokenEvaluacionPort.

    Traza: CU-05, EAC-03, ADR-002, ADR-004.

    Almacena tokens efímeros para la validación de horas y evaluación de desempeño
    por parte de supervisores externos, permitiendo búsquedas por cadena de token y por id.
    """

    def __init__(self, tokens_iniciales: Optional[list[TokenEvaluacion]] = None) -> None:
        self._tokens_por_id: dict[str, TokenEvaluacion] = {}
        self._tokens_por_str: dict[str, TokenEvaluacion] = {}
        if tokens_iniciales:
            for token in tokens_iniciales:
                self.guardar(token)

    def guardar(self, token: TokenEvaluacion) -> None:
        """Persiste o actualiza un token en el almacén en memoria."""
        self._tokens_por_id[token.id] = token
        self._tokens_por_str[token.token] = token

    def buscar_por_token(self, token: str) -> Optional[TokenEvaluacion]:
        """Recupera un TokenEvaluacion a partir de su cadena criptográfica."""
        return self._tokens_por_str.get(token.strip())

    def buscar_por_id(self, token_id: str) -> Optional[TokenEvaluacion]:
        """Recupera un TokenEvaluacion a partir de su identificador único."""
        return self._tokens_por_id.get(token_id.strip())

    def listar_por_practica(self, practica_id: str) -> list[TokenEvaluacion]:
        """Recupera todos los TokenEvaluacion emitidos para una práctica ordenados por fecha_emision.

        Traza: CU-08, Escenarios 1, 2, 3, 6, 8 y 11, ADR-004.
        """
        if not practica_id:
            return []
        practica_id_limpio = practica_id.strip()
        tokens = [
            t
            for t in self._tokens_por_id.values()
            if t.practica_id == practica_id_limpio
        ]
        return sorted(tokens, key=lambda t: t.fecha_emision)

    def listar_todos(self) -> list[TokenEvaluacion]:
        """Retorna todos los tokens almacenados."""
        return list(self._tokens_por_id.values())

    def limpiar(self) -> None:
        """Limpia los tokens almacenados (útil para pruebas)."""
        self._tokens_por_id.clear()
        self._tokens_por_str.clear()


class InMemoryRepositorioEvaluacionDesempeno(RepositorioEvaluacionDesempenoPort):
    """Implementación en memoria del puerto RepositorioEvaluacionDesempenoPort.

    Traza: CU-07, EAC-01, EAC-03, RN-01, RN-02, RN-03, RN-04, ADR-002, ADR-003, ADR-010.

    Almacena en memoria las instancias de EvaluacionDesempeno indexadas por id y
    por practica_id, garantizando la relación 1 a 0..1 entre Practica y
    EvaluacionDesempeno según el modelo de dominio (01-logica.puml).
    """

    def __init__(
        self, evaluaciones_iniciales: Optional[list[EvaluacionDesempeno]] = None
    ) -> None:
        self._evaluaciones_por_id: dict[str, EvaluacionDesempeno] = {}
        self._evaluaciones_por_practica: dict[str, EvaluacionDesempeno] = {}
        if evaluaciones_iniciales:
            for evaluacion in evaluaciones_iniciales:
                self.guardar(evaluacion)

    def guardar(self, evaluacion: EvaluacionDesempeno) -> None:
        """Persiste o actualiza una evaluación de desempeño en el almacén en memoria."""
        self._evaluaciones_por_id[evaluacion.id] = evaluacion
        self._evaluaciones_por_practica[evaluacion.practica_id] = evaluacion

    def buscar_por_id(self, evaluacion_id: str) -> Optional[EvaluacionDesempeno]:
        """Busca y retorna una evaluación de desempeño por su identificador único."""
        if not evaluacion_id:
            return None
        return self._evaluaciones_por_id.get(evaluacion_id.strip())

    def buscar_por_practica(self, practica_id: str) -> Optional[EvaluacionDesempeno]:
        """Busca si ya existe una evaluación de desempeño asociada a la práctica indicada."""
        if not practica_id:
            return None
        return self._evaluaciones_por_practica.get(practica_id.strip())

    def listar_todas(self) -> list[EvaluacionDesempeno]:
        """Retorna todas las evaluaciones de desempeño almacenadas."""
        return list(self._evaluaciones_por_id.values())

    def limpiar(self) -> None:
        """Limpia las evaluaciones almacenadas (útil para pruebas)."""
        self._evaluaciones_por_id.clear()
        self._evaluaciones_por_practica.clear()


class InMemoryRepositorioActaFinal(RepositorioActaFinalPort):
    """Implementación en memoria del puerto RepositorioActaFinalPort.

    Traza: CU-09, CU-10, EAC-01, EAC-03, OB-01, OB-05, PA-03, RN-01, RN-02, RN-03, DT-02,
    ADR-002, ADR-003, ADR-008, ADR-010, Vista Lógica §2 (01-logica.puml).

    Almacena en memoria las instancias de ActaFinal indexadas por id, por practica_id
    (garantizando la relación 1 a 0..1 entre Practica y ActaFinal) y por numero_acta.
    Mantiene el contador consecutivo anual para siguiente_numero_acta(anio) con formato
    "ACTA-<AÑO>-<NNNN>" (ej. "ACTA-2026-0001") y soporta simulación determinista de
    fallo de persistencia junto con compensación transaccional (eliminar_por_id) para
    validar la consistencia atómica del Escenario 10 (DT-02).
    """

    def __init__(
        self, actas_iniciales: Optional[list[ActaFinal]] = None
    ) -> None:
        self._actas_por_id: dict[str, ActaFinal] = {}
        self._actas_por_practica: dict[str, ActaFinal] = {}
        self._actas_por_numero: dict[str, ActaFinal] = {}
        self._consecutivos_por_anio: dict[int, int] = {}
        self._fallo_guardado_activo: bool = False
        self._mensaje_fallo_guardado: str = (
            "Fallo simulado de persistencia al guardar el registro de ActaFinal."
        )
        if actas_iniciales:
            for acta in actas_iniciales:
                self.guardar(acta)

    def guardar(self, acta: ActaFinal) -> None:
        """Persiste una nueva instancia de ActaFinal en el almacén en memoria.

        Raises:
            ErrorAlmacenamientoActaPdfError: Si se encuentra activa la simulación de fallo
                de guardado para validar la compensación transaccional (Escenario 10, DT-02).
        """
        if self._fallo_guardado_activo:
            raise ErrorAlmacenamientoActaPdfError(
                practica_id=acta.practica_id,
                ruta_archivo_pdf=acta.ruta_archivo_pdf,
                causa=self._mensaje_fallo_guardado,
            )

        self._actas_por_id[acta.id] = acta
        self._actas_por_practica[acta.practica_id] = acta
        self._actas_por_numero[acta.numero_acta] = acta
        self._sincronizar_consecutivo_desde_numero(acta.numero_acta)

    def actualizar(self, acta: ActaFinal) -> None:
        """Actualiza el estado de firmas electrónicas y datos de un ActaFinal existente (CU-10)."""
        if self._fallo_guardado_activo:
            raise ErrorAlmacenamientoActaPdfError(
                practica_id=acta.practica_id,
                ruta_archivo_pdf=acta.ruta_archivo_pdf,
                causa=self._mensaje_fallo_guardado,
            )

        self._actas_por_id[acta.id] = acta
        self._actas_por_practica[acta.practica_id] = acta
        self._actas_por_numero[acta.numero_acta] = acta
        self._sincronizar_consecutivo_desde_numero(acta.numero_acta)

    def buscar_por_id(self, acta_id: str) -> Optional[ActaFinal]:
        """Busca y retorna un acta final por su identificador único."""
        if not acta_id:
            return None
        return self._actas_por_id.get(acta_id.strip())

    def buscar_por_practica(self, practica_id: str) -> Optional[ActaFinal]:
        """Busca si ya existe un acta final asociada a la práctica empresarial indicada.

        Garantiza la verificación de la invariante de multiplicidad 1 a 0..1 entre
        Practica y ActaFinal (CU-09 Escenario 5).
        """
        if not practica_id:
            return None
        return self._actas_por_practica.get(practica_id.strip())

    def buscar_por_numero_acta(self, numero_acta: str) -> Optional[ActaFinal]:
        """Busca y retorna un acta final por su número oficial consecutivo anual."""
        if not numero_acta:
            return None
        return self._actas_por_numero.get(numero_acta.strip())

    def siguiente_numero_acta(self, anio: int) -> str:
        """Genera el siguiente número oficial consecutivo anual con formato 'ACTA-<AÑO>-<NNNN>'.

        Traza: CU-09, Escenarios 1 y 6 (ej. 'ACTA-2026-0001').
        Calcula el siguiente consecutivo disponible para el año indicado a partir de las
        actas efectivamente persistidas y del contador anual.
        """
        anio_entero = int(anio)
        max_persistido = self._maximo_consecutivo_persistido(anio_entero)
        actual = max(self._consecutivos_por_anio.get(anio_entero, 0), max_persistido)
        siguiente = actual + 1
        self._consecutivos_por_anio[anio_entero] = siguiente
        return f"ACTA-{anio_entero:04d}-{siguiente:04d}"

    def eliminar_por_id(self, acta_id: str) -> None:
        """Elimina un registro de ActaFinal por su identificador para compensación transaccional (DT-02, Escenario 10)."""
        if not acta_id:
            return
        acta = self._actas_por_id.pop(acta_id.strip(), None)
        if acta is not None:
            self._actas_por_practica.pop(acta.practica_id, None)
            self._actas_por_numero.pop(acta.numero_acta, None)
            partes = acta.numero_acta.split("-")
            if len(partes) == 3 and partes[1].isdigit():
                anio = int(partes[1])
                self._consecutivos_por_anio[anio] = self._maximo_consecutivo_persistido(anio)

    def listar_todas(self) -> list[ActaFinal]:
        """Retorna todas las actas finales registradas en el almacén en memoria."""
        return list(self._actas_por_id.values())

    def configurar_fallo_guardado(
        self,
        activar: bool,
        mensaje: Optional[str] = None,
    ) -> None:
        """Activa o desactiva la simulación determinista de fallo de persistencia (Escenario 10, DT-02)."""
        self._fallo_guardado_activo = activar
        if mensaje is not None:
            self._mensaje_fallo_guardado = mensaje

    def limpiar(self) -> None:
        """Limpia las actas almacenadas, reinicia contadores y desactiva fallos simulados."""
        self._actas_por_id.clear()
        self._actas_por_practica.clear()
        self._actas_por_numero.clear()
        self._consecutivos_por_anio.clear()
        self._fallo_guardado_activo = False

    def _sincronizar_consecutivo_desde_numero(self, numero_acta: str) -> None:
        """Sincroniza el contador anual si el número de acta persistido supera el consecutivo actual."""
        partes = numero_acta.strip().split("-")
        if len(partes) == 3 and partes[0] == "ACTA" and partes[1].isdigit() and partes[2].isdigit():
            anio = int(partes[1])
            consecutivo = int(partes[2])
            if consecutivo > self._consecutivos_por_anio.get(anio, 0):
                self._consecutivos_por_anio[anio] = consecutivo

    def _maximo_consecutivo_persistido(self, anio: int) -> int:
        """Retorna el mayor consecutivo actualmente persistido para el año indicado."""
        prefijo = f"ACTA-{anio:04d}-"
        maximo = 0
        for numero in self._actas_por_numero:
            if numero.startswith(prefijo):
                sufijo = numero[len(prefijo):]
                if sufijo.isdigit():
                    maximo = max(maximo, int(sufijo))
        return maximo




