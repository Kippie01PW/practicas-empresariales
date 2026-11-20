# Tareas: 008 Enviar recordatorios de plazos

- [X] T-01 Incorporar excepción de dominio para bloqueo por período de enfriamiento de recordatorios
      Archivos: dominio/errores.py
      Escenarios: 7
      Depende de: ninguna

- [X] T-02 Extender entidad de dominio TokenEvaluacion con método de invalidación explícita al renovar enlaces expirados
      Archivos: dominio/modelos/token_evaluacion.py
      Escenarios: 2, 3, 6, 11
      Depende de: ninguna

- [ ] T-03 Crear DTOs inmutables para comando de ejecución de recordatorios, detalle de envíos y métricas consolidadas
      Archivos: aplicacion/dtos/recordatorio_plazos_dto.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 10
      Depende de: ninguna

- [ ] T-04 Ampliar puerto RepositorioTokenEvaluacionPort con consulta de tokens emitidos por práctica
      Archivos: aplicacion/puertos/repositorio_token_evaluacion.py
      Escenarios: 1, 2, 3, 6, 8, 11
      Depende de: T-02

- [ ] T-05 Configurar rol SISTEMA y método de autorización RBAC deny-by-default para envío automático y disparo manual de recordatorios por Coordinador de prácticas
      Archivos: aplicacion/seguridad/autorizador_rbac.py
      Escenarios: 6, 9, 11
      Depende de: ninguna

- [ ] T-06 Implementar caso de uso EnviarRecordatoriosPlazosCasoUso con evaluación en días calendario, renovación de tokens, escalamiento tras 3 recordatorios, cooldown de 1 hora y tolerancia a fallos de correo
      Archivos: aplicacion/casos_uso/enviar_recordatorios_plazos.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
      Depende de: T-01, T-02, T-03, T-04, T-05

- [ ] T-07 Implementar consulta listar_por_practica en adaptador InMemoryRepositorioTokenEvaluacion
      Archivos: infraestructura/adaptadores/repositorio_memoria.py
      Escenarios: 1, 2, 3, 6, 8, 11
      Depende de: T-02, T-04

- [ ] T-08 Integrar EnviarRecordatoriosPlazosCasoUso en el punto de composición main.py con demostración CLI
      Archivos: main.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
      Depende de: T-06, T-07

- [ ] T-09 Validar todos los escenarios de spec.md y generar validacion.md
      Archivos: specs/008-enviar-recordatorios-plazos/validacion.md
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
      Depende de: T-08

