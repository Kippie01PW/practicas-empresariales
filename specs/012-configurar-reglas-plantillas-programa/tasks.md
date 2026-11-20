# Tareas: 012 Configurar reglas y plantillas por programa

- [X] T-01 Incorporar excepciones de dominio para validación normativa, criterios de rúbrica, duplicidad de versión e inmutabilidad de reglas de programa
      Archivos: dominio/errores.py
      Escenarios: 5, 6, 7, 8
      Depende de: ninguna

- [X] T-02 Ampliar entidad de dominio ReglaPrograma con validación de lista simple o diccionario de criterios, edición controlada en estado Borrador y transición formal a Activa
      Archivos: dominio/modelos/regla_programa.py
      Escenarios: 1, 2, 3, 4, 5, 6, 8, 10
      Depende de: T-01

- [X] T-03 Crear DTOs inmutables para comandos de creación, edición, simulación, activación y eliminación de ReglaPrograma y sus respuestas en CU-12
      Archivos: aplicacion/dtos/regla_programa_dto.py
      Escenarios: 1, 2, 3, 4
      Depende de: ninguna

- [X] T-04 Ampliar puerto RepositorioReglaProgramaPort con métodos de actualización y consulta por programa y versión
      Archivos: aplicacion/puertos/repositorio_regla.py
      Escenarios: 1, 2, 3, 4, 7, 8, 10
      Depende de: T-02

- [X] T-05 Ampliar puerto ServicioGeneradorActaPdfPort con método simular_acta_pdf_en_memoria para previsualización de reglas en estado Borrador
      Archivos: aplicacion/puertos/servicio_generador_acta_pdf.py
      Escenarios: 3, 10
      Depende de: ninguna

- [X] T-06 Configurar método validar_configuracion_reglas en AutorizadorRBAC bajo política deny-by-default para Coordinador de prácticas
      Archivos: aplicacion/seguridad/autorizador_rbac.py
      Escenarios: 9
      Depende de: ninguna

- [X] T-07 Implementar caso de uso ConfigurarReglasProgramaCasoUso con creación y edición de borrador, simulación de vista previa en memoria, activación atómica y bitácora Append-Only
      Archivos: aplicacion/casos_uso/configurar_reglas_programa.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
      Depende de: T-01, T-02, T-03, T-04, T-05, T-06

- [X] T-08 Ampliar adaptador en memoria InMemoryRepositorioReglaPrograma con actualización y búsqueda por programa y versión
      Archivos: infraestructura/adaptadores/repositorio_memoria.py
      Escenarios: 1, 2, 3, 4, 7, 8, 10
      Depende de: T-02, T-04

- [X] T-09 Implementar método simular_acta_pdf_en_memoria en adaptador AdaptadorPdfHashSimulado para previsualización sin persistencia en repositorio oficial
      Archivos: infraestructura/adaptadores/adaptador_pdf_hash_simulado.py
      Escenarios: 3, 10
      Depende de: T-05

- [X] T-10 Integrar ConfigurarReglasProgramaCasoUso y simulación en memoria de plantillas en el punto de composición main.py
      Archivos: main.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
      Depende de: T-07, T-08, T-09

- [ ] T-11 Validar todos los escenarios de spec.md y generar validacion.md
      Archivos: specs/012-configurar-reglas-plantillas-programa/validacion.md
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
      Depende de: T-10

