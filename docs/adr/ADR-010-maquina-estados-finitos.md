# ADR-010: Patrón Máquina de Estados Finitos para control del flujo de prácticas

## Estado

Aceptado

## Contexto

El sistema debe cumplir estrictamente el flujo operativo secuencial de las prácticas empresariales desde su postulación hasta generar el acta final (RN-02), sin permitir saltos o transiciones indebidas (por ejemplo, validar horas antes de tener un tutor asignado, o emitir actas sin horas completas). Esto impacta directamente la fiabilidad (OB-01, CU-11).

## Alternativas consideradas

- **A) Atributos booleanos o cadenas de texto sueltas manipuladas procedimentalmente:** (ejemplo: `if (!practice.isHoursApproved && practice.hasTutor)`).
  - *Ventaja:* Muy fácil de implementar inicialmente.
  - *Desventaja:* Resulta en código frágil ("código espagueti"); es fácil omitir una validación en algún caso de uso, posibilitando flujos ilegales y violando gravemente RN-02.
- **B) Patrón "State Machine" (Máquina de Estados Finitos) encapsulado en el dominio:** La entidad "Práctica" gestiona su estado (Solicitada, Asignada, En Ejecución, Evaluada, Completada) e internamente valida todas las transiciones válidas.
  - *Ventaja:* Concentra toda la lógica del ciclo de vida en un solo lugar, haciendo imposible realizar una transición no declarada (cumple RN-02). Facilita exponer el estado al estudiante para consulta (CU-11).
  - *Desventaja:* Curva de abstracción un poco mayor al implementar los estados y disparadores de eventos.

## Decisión

Se elige la opción B porque garantiza por diseño el rigor operativo requerido en RN-02, eliminando posibles vulnerabilidades o corrupción de datos que impedirían la finalización exitosa (OB-05).

## Consecuencias

### Positivas

- Imposibilidad de alterar el flujo de negocio saltando pasos (ejemplo: emitir un acta de una práctica rechazada).
- Extrema facilidad para consultar y renderizar un tracker de avance (CU-11) basado en los nodos del flujo actual.

### Negativas y costos aceptados

- Alterar la secuencia general (ejemplo: incorporar un nuevo paso oficial intermedio) requiere actualizar los grafos de transición permitidos en la máquina de estados, exigiendo nuevas pruebas unitarias.

### Riesgos asumidos y sus respectivas mitigaciones

- **Bloqueos operativos (Deadlocks) si un actor omite un paso externamente o ante errores atípicos:** Mitigación modelando estados de excepción (ejemplo: "Cancelada por fuerza mayor", "Prórroga") e instrumentando acciones compensatorias disponibles únicamente para el rol de Administrador.


## Vistas arquitectónicas afectadas

* [Vista Lógica](../vistas/01-logica.md) (`../diagramas/01-logica.puml`): Entidad `Practica` y su atributo `estadoActual`.
* [Vista de Desarrollo](../vistas/03-desarrollo.md) (`../diagramas/03-desarrollo.puml`): Máquina de Estados Finitos encapsulada en el `Núcleo de Dominio`.
* [Escenario ESC-03](../diagramas/secuencias/cu09-generar-acta.puml) y [Escenario ESC-04](../diagramas/secuencias/cu10-aprobar-acta.puml): Guardas `break` que impiden saltar estados del flujo.
