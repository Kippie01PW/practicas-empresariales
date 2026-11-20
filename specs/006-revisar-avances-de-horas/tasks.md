# Tareas: 006 Revisar avances de horas

- [X] T-01 Crear DTOs inmutables para consulta individual y consolidada de avances de horas
      Archivos: aplicacion/dtos/avance_horas_dto.py
      Escenarios: 1, 2, 3, 4, 5, 6, 13
      Depende de: ninguna

- [X] T-02 Extender puerto RepositorioPracticaPort con listado de prácticas por docente asesor
      Archivos: aplicacion/puertos/repositorio_practica.py
      Escenarios: 6, 14
      Depende de: ninguna

- [X] T-03 Configurar reglas de autorización RBAC y pertenencia contextual docente-práctica y estudiante-práctica para CU-06
      Archivos: aplicacion/seguridad/autorizador_rbac.py
      Escenarios: 1, 2, 6, 7, 8, 9, 11, 12
      Depende de: ninguna

- [X] T-04 Implementar caso de uso RevisarAvancesHorasCasoUso en modo solo lectura con trazabilidad en bitácora
      Archivos: aplicacion/casos_uso/revisar_avances_horas.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14
      Depende de: T-01, T-02, T-03

- [X] T-05 Implementar consulta de prácticas por docente asesor en InMemoryRepositorioPractica
      Archivos: infraestructura/adaptadores/repositorio_memoria.py
      Escenarios: 6, 14
      Depende de: T-02

- [X] T-06 Integrar RevisarAvancesHorasCasoUso en el punto de composición main.py
      Archivos: main.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14
      Depende de: T-04, T-05

- [X] T-07 Validar todos los escenarios de spec.md y generar validacion.md
      Archivos: specs/006-revisar-avances-de-horas/validacion.md
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14
      Depende de: T-06

