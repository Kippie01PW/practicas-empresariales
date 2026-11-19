# Tareas: 005 Validar horas registradas

- [X] T-01 Incorporar excepciones de dominio para validación de horas y credenciales tokenizadas
      Archivos: dominio/errores.py
      Escenarios: 3, 4, 5, 6, 7, 8, 9, 10, 11
      Depende de: ninguna

- [X] T-02 Crear modelo de dominio TokenEvaluacion con control de vigencia y un solo uso
      Archivos: dominio/modelos/token_evaluacion.py
      Escenarios: 1, 2, 7, 8, 9, 11
      Depende de: T-01

- [X] T-03 Actualizar entidad RegistroHoras con observaciones de rechazo y control de estado de validación
      Archivos: dominio/modelos/registro_horas.py
      Escenarios: 1, 2, 3, 4
      Depende de: T-01

- [X] T-04 Actualizar entidad Practica con acumulador de horas aprobadas y validación de estado EnEjecucion
      Archivos: dominio/modelos/practica.py
      Escenarios: 1, 2, 5
      Depende de: T-01

- [X] T-05 Crear DTOs inmutables para comando y respuesta de validación de horas
      Archivos: aplicacion/dtos/validacion_horas_dto.py
      Escenarios: 1, 2, 3
      Depende de: ninguna

- [X] T-06 Definir puerto de repositorio para TokenEvaluacion
      Archivos: aplicacion/puertos/repositorio_token_evaluacion.py
      Escenarios: 1, 2, 7, 8, 9, 11
      Depende de: T-02

- [X] T-07 Configurar reglas de autorización RBAC y pertenencia contextual supervisor-práctica
      Archivos: aplicacion/seguridad/autorizador_rbac.py
      Escenarios: 1, 6, 10, 11
      Depende de: ninguna

- [X] T-08 Implementar caso de uso principal ValidarHorasRegistradasCasoUso
      Archivos: aplicacion/casos_uso/validar_horas_registradas.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
      Depende de: T-01, T-02, T-03, T-04, T-05, T-06, T-07

- [X] T-09 Implementar interceptor de identidad para verificación criptográfica HMAC de enlaces efímeros
      Archivos: infraestructura/seguridad/interceptor_identidad.py
      Escenarios: 1, 2, 7, 8, 9, 11
      Depende de: T-01, T-02

- [ ] T-10 Implementar repositorio en memoria para TokenEvaluacion y actualizar persistencia de Practica y RegistroHoras
      Archivos: infraestructura/adaptadores/repositorio_memoria.py
      Escenarios: 1, 2, 4, 7, 8, 9, 11
      Depende de: T-02, T-03, T-04, T-06

- [ ] T-11 Integrar repositorios, interceptor de identidad y caso de uso en main.py
      Archivos: main.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
      Depende de: T-08, T-09, T-10

- [ ] T-12 Validar todos los escenarios de spec.md y generar validacion.md
      Archivos: specs/005-validar-horas-registradas/validacion.md
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
      Depende de: T-11
