# Tareas: 001 Postulación de estudiante a la práctica

- [X] T-01 Crear enumeraciones y modelo de dominio para Práctica
      Archivos: dominio/modelos/practica.py
      Escenarios: 1, 2, 3, 5, 6, 7
      Depende de: ninguna

- [X] T-02 Crear modelos de dominio para Estudiante y ReglaPrograma
      Archivos: dominio/modelos/estudiante.py, dominio/modelos/regla_programa.py
      Escenarios: 1, 2, 3, 4, 5
      Depende de: ninguna

- [X] T-03 Crear modelos de dominio para IntentoValidacion y EventoBitacora
      Archivos: dominio/modelos/intento_validacion.py, dominio/modelos/evento_bitacora.py
      Escenarios: 1, 2, 5, 6, 7
      Depende de: ninguna

- [X] T-04 Definir excepciones y errores de dominio
      Archivos: dominio/errores.py
      Escenarios: 1, 2, 3, 4, 5
      Depende de: ninguna

- [X] T-05 Crear DTOs inmutables para comando y respuesta de postulación
      Archivos: aplicacion/dtos/postulacion_dto.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7
      Depende de: T-01, T-02

- [X] T-06 Definir puertos de persistencia (RepositorioPracticaPort y RepositorioReglaProgramaPort)
      Archivos: aplicacion/puertos/repositorio_practica.py, aplicacion/puertos/repositorio_regla.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7
      Depende de: T-01, T-02, T-03

- [X] T-07 Definir puertos de servicios externos e integración (Registro Académico, Bróker y Correo)
      Archivos: aplicacion/puertos/servicio_registro_academico.py, aplicacion/puertos/publicador_eventos.py, aplicacion/puertos/servicio_correo.py
      Escenarios: 1, 2, 5, 6, 7
      Depende de: T-01, T-02, T-03

- [ ] T-08 Implementar componente de autorización RBAC en aplicación
      Archivos: aplicacion/seguridad/autorizador_rbac.py
      Escenarios: 1, 2, 3, 4, 5
      Depende de: T-02, T-04

- [ ] T-09 Implementar caso de uso principal PostularEstudianteCasoUso
      Archivos: aplicacion/casos_uso/postular_estudiante.py
      Escenarios: 1, 2, 3, 4, 5
      Depende de: T-01, T-02, T-03, T-04, T-05, T-06, T-07, T-08

- [ ] T-10 Implementar caso de uso de integración y reintento asíncrono ReintentarValidacionSiaCasoUso
      Archivos: aplicacion/casos_uso/reintentar_validacion_sia.py
      Escenarios: 6, 7
      Depende de: T-01, T-02, T-03, T-04, T-06, T-07

- [ ] T-11 Implementar repositorios en memoria para Práctica, Regla y Bitácora
      Archivos: infraestructura/adaptadores/repositorio_memoria.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7
      Depende de: T-06

- [ ] T-12 Implementar adaptador simulado para Servicio de Registro Académico (SIA) con Circuit Breaker y timeout
      Archivos: infraestructura/adaptadores/cliente_sia_simulado.py
      Escenarios: 1, 2, 5, 6, 7
      Depende de: T-07

- [ ] T-13 Implementar adaptador en memoria para Bróker de Mensajes (cola de tareas y DLQ)
      Archivos: infraestructura/adaptadores/broker_memoria.py
      Escenarios: 5, 6, 7
      Depende de: T-07

- [ ] T-14 Implementar adaptadores simulados de correo y contexto de identidad OIDC
      Archivos: infraestructura/adaptadores/servicio_correo_simulado.py, infraestructura/seguridad/proveedor_identidad_simulado.py
      Escenarios: 1, 2, 3, 4, 5, 6
      Depende de: T-07, T-08

- [ ] T-15 Configurar composición de dependencias y punto de entrada en main.py
      Archivos: main.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7
      Depende de: T-09, T-10, T-11, T-12, T-13, T-14

- [ ] T-16 Validar todos los escenarios de spec.md y generar validacion.md
      Archivos: specs/001-postulacion-estudiante/validacion.md
      Escenarios: 1, 2, 3, 4, 5, 6, 7
      Depende de: T-15
