# Tareas: 014 Generar consolidados para auditoría

- [ ] T-01 Incorporar excepción de dominio FiltrosConsolidadoInvalidosError para validación de filtros obligatorios y rango de fechas
      Archivos: dominio/errores.py
      Escenarios: 5
      Depende de: ninguna

- [ ] T-02 Crear DTOs inmutables para comando de consulta, registro consolidado, datos de renderizado PDF y respuesta de consolidado de auditoría
      Archivos: aplicacion/dtos/consolidado_auditoria_dto.py
      Escenarios: 1, 2, 3, 4
      Depende de: ninguna

- [ ] T-03 Ampliar puerto RepositorioPracticaPort con el método listar_todas para consultas históricas consolidadas
      Archivos: aplicacion/puertos/repositorio_practica.py
      Escenarios: 1, 2, 3, 4
      Depende de: ninguna

- [ ] T-04 Ampliar puerto ServicioGeneradorActaPdfPort con el método generar_consolidado_auditoria_pdf para exportación en PDF con sellado SHA-256
      Archivos: aplicacion/puertos/servicio_generador_acta_pdf.py
      Escenarios: 1, 2, 3, 4
      Depende de: T-02

- [ ] T-05 Configurar permiso y método validar_generacion_consolidados_auditoria en AutorizadorRBAC bajo política deny-by-default
      Archivos: aplicacion/seguridad/autorizador_rbac.py
      Escenarios: 6
      Depende de: ninguna

- [ ] T-06 Implementar caso de uso GenerarConsolidadosAuditoriaCasoUso con filtrado, proyección inmutable de prácticas y actas finales, y registro en bitácora Append-Only
      Archivos: aplicacion/casos_uso/generar_consolidados_auditoria.py
      Escenarios: 1, 2, 3, 4, 5, 6
      Depende de: T-01, T-02, T-03, T-04, T-05

- [ ] T-07 Implementar generar_consolidado_auditoria_pdf en el adaptador AdaptadorPdfHashSimulado
      Archivos: infraestructura/adaptadores/adaptador_pdf_hash_simulado.py
      Escenarios: 1, 2, 3, 4
      Depende de: T-02, T-04

- [ ] T-08 Integrar GenerarConsolidadosAuditoriaCasoUso en el punto de composición main.py
      Archivos: main.py
      Escenarios: 1, 2, 3, 4, 5, 6
      Depende de: T-06, T-07

- [ ] T-09 Validar todos los escenarios de spec.md y generar validacion.md
      Archivos: specs/014-generar-consolidados-auditoria/validacion.md
      Escenarios: 1, 2, 3, 4, 5, 6
      Depende de: T-08

