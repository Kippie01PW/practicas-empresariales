# Tareas: 009 Generar acta final de la práctica

- [X] T-01 Incorporar excepciones de dominio para generación de acta final, requisitos de cierre y fallos de almacenamiento
      Archivos: dominio/errores.py
      Escenarios: 2, 3, 4, 5, 10
      Depende de: ninguna

- [X] T-02 Crear entidad de dominio ActaFinal con validación de número de acta consecutivo, ruta PDF, hash SHA-256 y estado de firmas
      Archivos: dominio/modelos/acta_final.py
      Escenarios: 1, 5, 6, 11
      Depende de: T-01

- [X] T-03 Actualizar entidad Practica con método de validación de requisitos para generación de acta final (estado Evaluada, horas requeridas, evaluación y unicidad)
      Archivos: dominio/modelos/practica.py
      Escenarios: 1, 2, 3, 4, 5, 6, 11
      Depende de: T-01

- [ ] T-04 Crear DTOs inmutables para comando de generación de acta, datos de renderizado de plantilla y respuesta de CU-09
      Archivos: aplicacion/dtos/acta_final_dto.py
      Escenarios: 1, 6, 11
      Depende de: ninguna

- [ ] T-05 Definir puerto RepositorioActaFinalPort para persistencia, consulta de unicidad por práctica y consecutivo anual de número de acta
      Archivos: aplicacion/puertos/repositorio_acta_final.py
      Escenarios: 1, 5, 6, 10
      Depende de: T-02

- [ ] T-06 Definir puerto ServicioGeneradorActaPdfPort para renderizado desde plantilla HTML/CSS a PDF, sellado SHA-256 y compensación de archivos
      Archivos: aplicacion/puertos/servicio_generador_acta_pdf.py
      Escenarios: 1, 6, 10, 11
      Depende de: T-04

- [ ] T-07 Configurar método de autorización RBAC deny-by-default para generación de acta final por DocenteAsesor
      Archivos: aplicacion/seguridad/autorizador_rbac.py
      Escenarios: 1, 7, 8, 12
      Depende de: ninguna

- [ ] T-08 Implementar caso de uso GenerarActaFinalCasoUso con verificación RBAC contextual, validación de máquina de estados, renderizado PDF con plantilla versionada, sellado SHA-256, compensación atómica y registro en bitácora
      Archivos: aplicacion/casos_uso/generar_acta_final.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
      Depende de: T-01, T-02, T-03, T-04, T-05, T-06, T-07

- [ ] T-09 Implementar adaptador AdaptadorPdfYHashSimulado para renderizado de plantilla HTML/CSS a PDF, cálculo de hash SHA-256 y almacenamiento en repositorio de actas
      Archivos: infraestructura/adaptadores/adaptador_pdf_hash_simulado.py
      Escenarios: 1, 6, 10, 11
      Depende de: T-04, T-06

- [ ] T-10 Implementar adaptador en memoria InMemoryRepositorioActaFinal con generación de consecutivo anual ACTA-AÑO-NNNN y soporte de compensación
      Archivos: infraestructura/adaptadores/repositorio_memoria.py
      Escenarios: 1, 5, 6, 10
      Depende de: T-02, T-05

- [ ] T-11 Integrar InMemoryRepositorioActaFinal, AdaptadorPdfYHashSimulado y GenerarActaFinalCasoUso en el punto de composición main.py
      Archivos: main.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
      Depende de: T-08, T-09, T-10

- [ ] T-12 Validar todos los escenarios de spec.md y generar validacion.md
      Archivos: specs/009-generar-acta-final-de-la-practica/validacion.md
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
      Depende de: T-11
