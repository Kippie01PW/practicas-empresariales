# Tareas: 010 Aprobar el acta electrónicamente

- [X] T-01 Incorporar excepciones de dominio para aprobación electrónica de acta final, orden secuencial de firmas e integridad SHA-256
      Archivos: dominio/errores.py
      Escenarios: 3, 4, 5, 6
      Depende de: ninguna

- [X] T-02 Crear entidad de dominio ActaFinal con verificación de huella SHA-256 y aprobación secuencial por DocenteAsesor y Coordinador de prácticas
      Archivos: dominio/modelos/acta_final.py
      Escenarios: 1, 2, 3, 4, 6
      Depende de: T-01

- [X] T-03 Actualizar entidad Practica con consulta puede_aprobar_acta y transición formal Evaluada a Completada
      Archivos: dominio/modelos/practica.py
      Escenarios: 2, 3, 5, 6
      Depende de: T-01

- [X] T-04 Crear DTOs inmutables para comando de aprobación electrónica de acta y respuesta de CU-10
      Archivos: aplicacion/dtos/aprobacion_acta_dto.py
      Escenarios: 1, 2
      Depende de: ninguna

- [X] T-05 Definir puerto RepositorioActaFinalPort para persistencia y consulta de ActaFinal por identificador y por práctica
      Archivos: aplicacion/puertos/repositorio_acta_final.py
      Escenarios: 1, 2, 3, 4, 5, 6
      Depende de: T-02

- [X] T-06 Definir puerto ServicioPdfHashPort para lectura de binario PDF y recálculo de huella de integridad SHA-256
      Archivos: aplicacion/puertos/servicio_pdf_hash.py
      Escenarios: 1, 2, 4
      Depende de: ninguna

- [X] T-07 Ampliar puerto PublicadorEventosPort con DTO EventoActaFinalEmitida y método publicar_acta_final_emitida
      Archivos: aplicacion/puertos/publicador_eventos.py
      Escenarios: 2
      Depende de: ninguna

- [X] T-08 Configurar método validar_aprobacion_acta en AutorizadorRBAC bajo política deny-by-default para DocenteAsesor y Coordinador de prácticas
      Archivos: aplicacion/seguridad/autorizador_rbac.py
      Escenarios: 7, 8, 9
      Depende de: ninguna

- [X] T-09 Implementar caso de uso AprobarActaElectronicamenteCasoUso con validación RBAC contextual, verificación SHA-256, transición a Completada, liberación de cupo docente, bitácora y notificación
      Archivos: aplicacion/casos_uso/aprobar_acta_electronicamente.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9
      Depende de: T-01, T-02, T-03, T-04, T-05, T-06, T-07, T-08

- [ ] T-10 Implementar adaptador en memoria InMemoryRepositorioActaFinal
      Archivos: infraestructura/adaptadores/repositorio_memoria.py
      Escenarios: 1, 2, 3, 4, 5, 6
      Depende de: T-02, T-05

- [ ] T-11 Implementar adaptador simulado AdaptadorPdfHashSimulado para almacenamiento en memoria de binarios PDF y cálculo de hash SHA-256
      Archivos: infraestructura/adaptadores/adaptador_pdf_hash_simulado.py
      Escenarios: 1, 2, 4
      Depende de: T-06

- [ ] T-12 Implementar publicación del evento ActaFinalEmitida en adaptador InMemoryBrokerMensajes
      Archivos: infraestructura/adaptadores/broker_memoria.py
      Escenarios: 2
      Depende de: T-07

- [ ] T-13 Integrar InMemoryRepositorioActaFinal, AdaptadorPdfHashSimulado y AprobarActaElectronicamenteCasoUso en el punto de composición main.py
      Archivos: main.py
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9
      Depende de: T-09, T-10, T-11, T-12

- [ ] T-14 Validar todos los escenarios de spec.md y generar validacion.md
      Archivos: specs/010-aprobar-acta-electronicamente/validacion.md
      Escenarios: 1, 2, 3, 4, 5, 6, 7, 8, 9
      Depende de: T-13

