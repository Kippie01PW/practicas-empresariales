# Tareas: 007 Evaluar desempeño del practicante

- [X] T-01 Incorporar excepciones de dominio para evaluación de desempeño, escala cuantitativa y rúbrica
      Archivos: dominio/errores.py
      Escenarios: 5, 6, 7, 11, 12
      Depende de: ninguna

- [X] T-02 Crear entidad de dominio EvaluacionDesempeno con validación de escala 0.0 a 5.0, observaciones para reprobatoria y respuestas de rúbrica
      Archivos: dominio/modelos/evaluacion_desempeno.py
      Escenarios: 2, 3, 4, 5, 6, 7, 16
      Depende de: T-01

- [X] T-03 Actualizar entidad Practica con transición de estado EnEjecucion a Evaluada al registrar evaluación de desempeño
      Archivos: dominio/modelos/practica.py
      Escenarios: 2, 3, 4, 11, 12
      Depende de: T-01

- [X] T-04 Crear DTOs inmutables para consulta de formulario de rúbrica, comando de evaluación y respuestas de CU-07
      Archivos: aplicacion/dtos/evaluacion_desempeno_dto.py
      Escenarios: 1, 2, 3, 4, 16
      Depende de: ninguna

- [X] T-05 Definir puerto de repositorio RepositorioEvaluacionDesempenoPort para persistencia y consulta por práctica
      Archivos: aplicacion/puertos/repositorio_evaluacion_desempeno.py
      Escenarios: 2, 3, 4, 12
      Depende de: T-02

- [ ] T-06 Configurar método de autorización RBAC deny-by-default para evaluar desempeño por SupervisorEmpresa
      Archivos: aplicacion/seguridad/autorizador_rbac.py
      Escenarios: 13, 14, 15
      Depende de: ninguna

- [ ] T-07 Implementar caso de uso EvaluarDesempenoCasoUso con consulta de rúbrica versionada, validación de Magic Link, registro atómico y notificación al docente
      Archivos: aplicacion/casos_uso/evaluar_desempeno.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
      Depende de: T-01, T-02, T-03, T-04, T-05, T-06

- [ ] T-08 Implementar adaptador en memoria InMemoryRepositorioEvaluacionDesempeno
      Archivos: infraestructura/adaptadores/repositorio_memoria.py
      Escenarios: 2, 3, 4, 12
      Depende de: T-02, T-05

- [ ] T-09 Integrar InMemoryRepositorioEvaluacionDesempeno y EvaluarDesempenoCasoUso en el punto de composición main.py
      Archivos: main.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
      Depende de: T-07, T-08

- [ ] T-10 Validar todos los escenarios de spec.md y generar validacion.md
      Archivos: specs/007-evaluar-desempeno-del-practicante/validacion.md
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
      Depende de: T-09
