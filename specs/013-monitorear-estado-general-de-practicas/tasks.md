# Tareas: 013 Monitorear estado general de prácticas

- [X] T-01 Crear DTOs inmutables para comandos de consulta, indicadores de carga docente y respuestas del tablero de monitoreo general
      Archivos: aplicacion/dtos/monitoreo_practicas_dto.py
      Escenarios: 1, 2, 3, 4, 6, 9, 10
      Depende de: ninguna

- [X] T-02 Extender puerto RepositorioPracticaPort declarando el contrato listar_todas para consulta consolidada
      Archivos: aplicacion/puertos/repositorio_practica.py
      Escenarios: 1, 2, 3, 6, 9, 10
      Depende de: ninguna

- [X] T-03 Configurar regla de autorización RBAC exclusiva para Coordinador de prácticas y pertenencia contextual por programa académico en AutorizadorRBAC
      Archivos: aplicacion/seguridad/autorizador_rbac.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8
      Depende de: ninguna

- [X] T-04 Implementar caso de uso MonitorearPracticasCasoUso en modo solo lectura con restricción automática al programa del coordinador, filtrado por documento del Estudiante y trazabilidad en bitácora
      Archivos: aplicacion/casos_uso/monitorear_practicas.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
      Depende de: T-01, T-02, T-03

- [ ] T-05 Integrar MonitorearPracticasCasoUso en el punto de composición main.py
      Archivos: main.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
      Depende de: T-04

- [ ] T-06 Validar todos los escenarios de spec.md y generar validacion.md
      Archivos: specs/013-monitorear-estado-general-de-practicas/validacion.md
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
      Depende de: T-05
