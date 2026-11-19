# Tareas: 002 Aprobar o rechazar postulación

- [X] T-01 Incorporar excepciones de dominio para evaluación de postulaciones
      Archivos: dominio/errores.py
      Escenarios: 2, 3, 4, 5
      Depende de: ninguna

- [X] T-02 Actualizar entidad de dominio Práctica con transiciones de aprobación y rechazo justificado
      Archivos: dominio/modelos/practica.py
      Escenarios: 1, 2, 3, 4, 5
      Depende de: T-01

- [ ] T-03 Crear DTOs inmutables para comando y respuesta de evaluación de postulación
      Archivos: aplicacion/dtos/evaluacion_postulacion_dto.py
      Escenarios: 1, 2, 3
      Depende de: ninguna

- [ ] T-04 Configurar reglas y permisos de RBAC para Coordinador de prácticas
      Archivos: aplicacion/seguridad/autorizador_rbac.py
      Escenarios: 1, 2, 6, 7
      Depende de: ninguna

- [ ] T-05 Implementar caso de uso principal EvaluarPostulacionCasoUso
      Archivos: aplicacion/casos_uso/evaluar_postulacion.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7
      Depende de: T-01, T-02, T-03, T-04

- [ ] T-06 Actualizar adaptadores en memoria para soporte de actualización de prácticas y consulta por id
      Archivos: infraestructura/adaptadores/repositorio_memoria.py
      Escenarios: 1, 2, 4, 5
      Depende de: T-02

- [ ] T-07 Registrar e inyectar el caso de uso EvaluarPostulacionCasoUso en main.py
      Archivos: main.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7
      Depende de: T-05, T-06

- [ ] T-08 Validar todos los escenarios de spec.md y generar validacion.md
      Archivos: specs/002-aprobar-rechazar-postulacion/validacion.md
      Escenarios: 1, 2, 3, 4, 5, 6, 7
      Depende de: T-07
