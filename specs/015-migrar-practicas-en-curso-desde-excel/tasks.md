# Tareas: 015 Migrar prácticas en curso desde Excel

- [ ] T-01 Incorporar excepción de dominio ArchivoMigracionInvalidoError para plantillas ilegibles, vacías o sin columnas obligatorias
      Archivos: dominio/errores.py
      Escenarios: 1, 2, 3
      Depende de: ninguna

- [X] T-02 Crear DTOs inmutables para fila de plantilla normalizada, comando de migración, resultado por fila y respuesta consolidada
      Archivos: aplicacion/dtos/migracion_excel_dto.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7
      Depende de: ninguna

- [X] T-03 Definir puerto LectorPlantillaExcelPort para lectura de filas desde la plantilla normalizada de Excel
      Archivos: aplicacion/puertos/lector_plantilla_excel.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7
      Depende de: T-02

- [ ] T-04 Incorporar rol Administrador DBA, permiso migrar_practicas_excel y método validar_migracion_excel en AutorizadorRBAC bajo política deny-by-default
      Archivos: aplicacion/seguridad/autorizador_rbac.py
      Escenarios: 8
      Depende de: ninguna

- [ ] T-05 Implementar caso de uso MigrarPracticasExcelCasoUso con modo dry-run y carga definitiva, validación por fila, omisión de duplicados, mapeo determinista de hitos a EstadoPractica, control de cupo docente, verificación de ReglaPrograma y registro en EventoBitacora
      Archivos: aplicacion/casos_uso/migrar_practicas_excel.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8
      Depende de: T-01, T-02, T-03, T-04

- [ ] T-06 Implementar adaptador LectorPlantillaExcelSimulado para lectura de plantilla normalizada y validación de columnas obligatorias
      Archivos: infraestructura/adaptadores/lector_plantilla_excel_simulado.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7
      Depende de: T-01, T-02, T-03

- [ ] T-07 Integrar MigrarPracticasExcelCasoUso y LectorPlantillaExcelSimulado en el punto de composición main.py
      Archivos: main.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8
      Depende de: T-05, T-06

- [ ] T-08 Validar todos los escenarios de spec.md y generar validacion.md
      Archivos: specs/015-migrar-practicas-en-curso-desde-excel/validacion.md
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8
      Depende de: T-07
