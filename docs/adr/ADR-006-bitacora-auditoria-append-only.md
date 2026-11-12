# ADR-006: Bitácora de auditoría transaccional de solo inserción (Append-Only)

## Estado

Aceptado

## Contexto

El sistema debe asegurar el no repudio de la aprobación de actas finales (CU-10, PA-03), registrar intentos fallidos de acceso por motivos de seguridad en menos de un minuto (EAC-03), y permitir generar consolidados para procesos de acreditación (CU-14) respondiendo a consultas históricas cruzadas (OB-02). Las acciones de los usuarios no pueden ser borradas de los registros históricos.

## Alternativas consideradas

- **A) Archivos planos de logs de la aplicación:**
  - *Ventaja:* Viene de fábrica en cualquier framework.
  - *Desventaja:* Carece de estructura para consultas rápidas de reportes (CU-14) y son susceptibles de pérdida por rotación de almacenamiento en servidores locales.
- **B) Tabla relacional "Bitácora" de solo inserción (Append-Only) en la BD principal:**
  - *Ventaja:* Guarda el evento junto con la transacción (atomicidad); se consulta fácilmente mediante SQL para armar el tablero de control del coordinador y los consolidados.
  - *Desventaja:* Crece permanentemente y requiere gestión de espacio de almacenamiento.
- **C) Servicio de auditoría WORM (Write Once Read Many) externo:**
  - *Ventaja:* Total inmutabilidad.
  - *Desventaja:* Inviable presupuestalmente (RN-05).

## Decisión

Se elige la opción B porque garantiza la atomicidad y trazabilidad requerida por PA-03 y EAC-03 sin incorporar herramientas comerciales ajenas al ecosistema institucional.

## Consecuencias

### Positivas

- Trazabilidad irrefutable de quién aprobó el acta y cuándo (CU-10).
- Facilidad total para exportar historiales mediante consultas SQL (CU-14).
- Respuesta casi inmediata (< 1 minuto) para registro de fallos de seguridad (EAC-03).

### Negativas y costos aceptados

- Impacto ligero en el rendimiento de escritura por transacción (doble inserción).
- Requerimiento continuo de espacio en la base de datos a lo largo del tiempo.

### Riesgos asumidos y sus respectivas mitigaciones

- **Manipulación directa de la bitácora por un DBA mediante SQL:** Mitigación configurando el usuario de la base de datos asignado a la aplicación con permisos exclusivos de `INSERT` (sin privilegios de `UPDATE` ni `DELETE` sobre dicha tabla), delegando los controles a nivel de motor (RT-04).


## Vistas arquitectónicas afectadas

* [Vista Lógica](../vistas/01-logica.md) (`../diagramas/01-logica.puml`): Entidad `EventoBitacora`.
* [Vista de Procesos](../vistas/02-procesos.md) (`../diagramas/02-procesos.puml`): Almacenamiento transaccional en `PostgreSQL`.
* [Vista de Desarrollo](../vistas/03-desarrollo.md) (`../diagramas/03-desarrollo.puml`): Escritura desde `Adaptador PostgreSQL`.
* [Vista Física](../vistas/04-fisica.md) (`../diagramas/04-fisica.puml`): Restricción de permisos a solo `INSERT`/`SELECT` sobre `EventoBitacora` en el `Servidor de Base de Datos Institucional`.
* [Escenario ESC-02](../diagramas/secuencias/cu07-evaluar-desempeno.puml) y [Escenario ESC-04](../diagramas/secuencias/cu10-aprobar-acta.puml).
