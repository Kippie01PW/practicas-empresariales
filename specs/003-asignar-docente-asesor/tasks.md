# Tareas: 003 Asignar docente asesor o tutor

- [X] T-01 Incorporar excepciones de dominio para asignación de tutor y control de cupos
      Archivos: dominio/errores.py
      Escenarios: 2, 3, 4, 5
      Depende de: ninguna

- [X] T-02 Crear modelo de dominio DocenteAsesor con control de cupos y carga de tutorías
      Archivos: dominio/modelos/docente_asesor.py
      Escenarios: 1, 2
      Depende de: T-01

- [X] T-03 Actualizar entidad de dominio Práctica con vinculación de tutor y transición a Asignada
      Archivos: dominio/modelos/practica.py
      Escenarios: 1, 4, 5
      Depende de: T-01

- [X] T-04 Crear DTOs inmutables para comando y respuestas de asignación de tutor
      Archivos: aplicacion/dtos/asignacion_docente_dto.py
      Escenarios: 1, 2, 3
      Depende de: ninguna

- [X] T-05 Definir puerto de repositorio para DocenteAsesor
      Archivos: aplicacion/puertos/repositorio_docente.py
      Escenarios: 1, 2, 3
      Depende de: T-02

- [ ] T-06 Configurar permisos y acciones RBAC para asignación de docente asesor
      Archivos: aplicacion/seguridad/autorizador_rbac.py
      Escenarios: 1, 6, 7
      Depende de: ninguna

- [ ] T-07 Implementar caso de uso AsignarDocenteAsesorCasoUso
      Archivos: aplicacion/casos_uso/asignar_docente_asesor.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7
      Depende de: T-01, T-02, T-03, T-04, T-05, T-06

- [ ] T-08 Implementar repositorio en memoria para DocenteAsesor y actualizar persistencia de Práctica
      Archivos: infraestructura/adaptadores/repositorio_memoria.py
      Escenarios: 1, 2, 3, 4, 5
      Depende de: T-02, T-03, T-05

- [ ] T-09 Integrar repositorio de docentes y caso de uso en main.py
      Archivos: main.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7
      Depende de: T-07, T-08

- [ ] T-10 Validar todos los escenarios de spec.md y generar validacion.md
      Archivos: specs/003-asignar-docente-asesor/validacion.md
      Escenarios: 1, 2, 3, 4, 5, 6, 7
      Depende de: T-09
