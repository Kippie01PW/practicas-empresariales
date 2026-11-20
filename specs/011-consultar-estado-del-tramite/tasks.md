# Tareas: 011 Consultar estado del trámite

- [X] T-01 Crear DTOs inmutables para comando de consulta y respuesta del estado del trámite en autoservicio
      Archivos: aplicacion/dtos/estado_tramite_dto.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 12
      Depende de: ninguna

- [X] T-02 Extender puerto RepositorioPracticaPort con consulta de práctica activa o más reciente por estudiante
      Archivos: aplicacion/puertos/repositorio_practica.py
      Escenarios: 7, 8, 13
      Depende de: ninguna

- [X] T-03 Configurar regla de autorización RBAC exclusiva para el rol Estudiante y validación de pertenencia contextual en AutorizadorRBAC
      Archivos: aplicacion/seguridad/autorizador_rbac.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 9, 10, 11
      Depende de: ninguna

- [X] T-04 Implementar caso de uso ConsultarEstadoTramiteCasoUso en modo solo lectura con visibilidad contextual de evaluación y trazabilidad en bitácora
      Archivos: aplicacion/casos_uso/consultar_estado_tramite.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
      Depende de: T-01, T-02, T-03

- [X] T-05 Implementar búsqueda de práctica activa o más reciente por estudiante en InMemoryRepositorioPractica
      Archivos: infraestructura/adaptadores/repositorio_memoria.py
      Escenarios: 7, 8, 13
      Depende de: T-02

- [ ] T-06 Integrar ConsultarEstadoTramiteCasoUso en el punto de composición main.py
      Archivos: main.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
      Depende de: T-04, T-05

- [ ] T-07 Validar todos los escenarios de spec.md y generar validacion.md
      Archivos: specs/011-consultar-estado-del-tramite/validacion.md
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
      Depende de: T-06
