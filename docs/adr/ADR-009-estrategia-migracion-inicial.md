# ADR-009: Estrategia de migración inicial mediante plantilla normalizada y script CLI

## Estado

Aceptado

## Contexto

Es estrictamente obligatorio migrar las cohortes actualmente registradas en múltiples Excels dispares hacia el nuevo sistema (RT-02, CU-15). Los Excels de origen vienen con inconsistencias (RI-01), lo cual representa un riesgo de ensuciar la nueva base de datos. Esta funcionalidad es temporal y de un solo uso (PA-05).

## Alternativas consideradas

- **A) Módulo web interno con motor de importación dinámico:** Se construye una interfaz en la aplicación para mapear columnas.
  - *Ventaja:* Altamente reutilizable para los usuarios.
  - *Desventaja:* Representa un gran esfuerzo de desarrollo (PA-05) que quedará inútil y obsoleto al día siguiente del despliegue en producción.
- **B) Digitación manual transaccional:**
  - *Ventaja:* No requiere desarrollo de software.
  - *Desventaja:* Cuello de botella inasumible con cientos de registros (OB-01); alto riesgo de error de tipeo.
- **C) Plantilla de consolidación oficial de Excel y script de importación programática de un solo uso:** Se entrega un Excel estandarizado a los docentes con listas predefinidas para consolidar previo al despliegue. Luego, un script independiente procesa, valida, reporta errores y carga todo a la nueva BD consumiendo los mismos casos de uso del sistema.
  - *Ventaja:* Minimiza errores de entrada, no contamina el código de producción con un submódulo muerto y mitiga eficientemente RI-01.
  - *Desventaja:* Traspasa trabajo administrativo a los docentes asesores semanas antes del lanzamiento.

## Decisión

Se elige la opción C porque es la única que respeta la priorización de esfuerzo-valor de PA-05, asegurando la calidad de los datos sin afectar la arquitectura a largo plazo de la solución.

## Consecuencias

### Positivas

- Los datos entran al sistema pasando por todas las validaciones lógicas de dominio ya construidas (ADR-005, ADR-007).
- El código de la aplicación de producción se mantiene ligero y libre de utilidades desechables.

### Negativas y costos aceptados

- Los coordinadores y tutores deben realizar un esfuerzo administrativo excepcional antes de salir a producción para adaptar sus datos previos al formato requerido.

### Riesgos asumidos y sus respectivas mitigaciones

- **Rechazo de registros el día del paso a producción por inconsistencias:** Mitigación ejecutando el script CLI en modo "Dry Run" (solo validación, sin guardar) semanas previas, emitiendo reportes de advertencia a los docentes para que realicen las correcciones pertinentes con anticipación.


## Vistas arquitectónicas afectadas

* [Contexto del Sistema](../contexto.md) (`../diagramas/contexto.puml`): Actor `Administrador DBA` interactuando vía CLI.
* [Vista de Procesos](../vistas/02-procesos.md) (`../diagramas/02-procesos.puml`): Contenedor `Script CLI de migración`.
* [Vista de Desarrollo](../vistas/03-desarrollo.md) (`../diagramas/03-desarrollo.puml`): Reutilización de casos de uso en `Módulo Postulaciones`.
* [Vista Física](../vistas/04-fisica.md) (`../diagramas/04-fisica.puml`): Ejecución del `Script CLI de migración` dentro del contenedor `api-practicas`.
