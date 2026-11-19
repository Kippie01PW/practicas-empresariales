# Tareas: 004 Registrar horas de práctica semanales

- [X] T-01 Incorporar excepciones de dominio para registro y validación de horas
      Archivos: dominio/errores.py
      Escenarios: 3, 4, 5, 6, 7, 8
      Depende de: ninguna

- [X] T-02 Crear modelo de dominio RegistroHoras con validaciones de invariantes y estados de validación
      Archivos: dominio/modelos/registro_horas.py
      Escenarios: 1, 4, 5, 6, 7
      Depende de: T-01

- [X] T-03 Actualizar entidad Practica con transición a EnEjecucion y validación de estado para registro de horas
      Archivos: dominio/modelos/practica.py
      Escenarios: 1, 2, 3
      Depende de: T-01

- [X] T-04 Crear DTOs inmutables para comando y respuesta de registro de horas
      Archivos: aplicacion/dtos/registro_horas_dto.py
      Escenarios: 1, 2
      Depende de: ninguna

- [X] T-05 Definir puerto de repositorio para RegistroHoras
      Archivos: aplicacion/puertos/repositorio_registro_horas.py
      Escenarios: 1, 2, 8, 12
      Depende de: T-02

- [X] T-06 Configurar y verificar reglas de autorización RBAC y pertenencia para registro de horas
      Archivos: aplicacion/seguridad/autorizador_rbac.py
      Escenarios: 1, 9, 10, 11
      Depende de: ninguna

- [ ] T-07 Implementar caso de uso principal RegistrarHorasCasoUso
      Archivos: aplicacion/casos_uso/registrar_horas.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
      Depende de: T-01, T-02, T-03, T-04, T-05, T-06

- [ ] T-08 Implementar repositorio en memoria para RegistroHoras y actualizar persistencia de Practica
      Archivos: infraestructura/adaptadores/repositorio_memoria.py
      Escenarios: 1, 2, 8, 12
      Depende de: T-02, T-03, T-05

- [ ] T-09 Integrar repositorio de horas y caso de uso en main.py
      Archivos: main.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
      Depende de: T-07, T-08

- [ ] T-10 Validar todos los escenarios de spec.md y generar validacion.md
      Archivos: specs/004-registrar-horas-practica/validacion.md
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
      Depende de: T-09
