"""Adaptadores de persistencia en memoria para Práctica, ReglaPrograma y Bitácora.

Traza: CU-01, CU-12, EAC-01, EAC-02, ADR-001, ADR-002, ADR-003, ADR-006, ADR-007, ADR-010.
Vista Lógica §2, Vista de Desarrollo §2.

Implementa los puertos `RepositorioPracticaPort` y `RepositorioReglaProgramaPort`
utilizando estructuras en memoria deterministas para pruebas y validación sin dependencias
externas ni bases de datos reales en esta etapa (ADR-002, ADR-003).
"""

from __future__ import annotations

from typing import Optional

from aplicacion.puertos.repositorio_practica import RepositorioPracticaPort
from aplicacion.puertos.repositorio_regla import RepositorioReglaProgramaPort
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.intento_validacion import IntentoValidacion
from dominio.modelos.practica import Practica
from dominio.modelos.regla_programa import EstadoVigenciaRegla, ReglaPrograma


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
