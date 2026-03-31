Backlog WSFE (Comprobantes CAE) - Proyecto Facturador
 Objetivo
Implementar y actualizar la integracion ARCA WSFEv1 enfocada exclusivamente en comprobantes:
- 001 Factura A
- 002 Nota de Debito A
- 003 Nota de Credito A
- 006 Factura B
- 007 Nota de Debito B
- 008 Nota de Credito B
- 009 Recibo B
- 011 Factura C
- 012 Nota de Debito C
- 013 Nota de Credito C
- 015 Recibo C
 Alcance
 In scope
- Flujo CAE: `FECAESolicitar`
- Consultas: `FECompConsultar`, `FECompUltimoAutorizado`
- Validaciones y datos necesarios para los tipos de comprobante listados arriba
 Out of scope (por ahora)
- CAEA completo
- FCE MiPyMEs (201+)
- Comprobante 49 (Bienes Usados)
- Compradores multiples, Actividades, PeriodoAsoc, CbteFchHsGen
- Opcionales de regimenes especiales fuera del alcance acordado
---
 Estados y convenciones
- `BACKLOG`: pendiente
- `NEXT`: siguiente a implementar
- `IN_PROGRESS`: en desarrollo
- `BLOCKED`: bloqueado
- `DONE`: finalizado
- `CANCELLED`: descartado
Prioridad:
- `P0` Critico
- `P1` Alto
- `P2` Medio
Esfuerzo (estimado):
- `S` (<= 1 dia)
- `M` (2-4 dias)
- `L` (5+ dias)
---
 Board de seguimiento
| ID | Feature | Prioridad | Estado | Esfuerzo | Owner | Dependencias |
|---|---|---:|---|---:|---|---|
| ARCA-001 | Canon de tipos permitidos (1,2,3,6,7,8,9,11,12,13,15) | P0 | BACKLOG | S | - | - |
| ARCA-002 | Soporte integral Recibo B (9) y Recibo C (15) | P0 | BACKLOG | M | - | ARCA-001 |
| ARCA-003 | RG5616 robusta (`CondicionIVAReceptorId` por clase) | P0 | BACKLOG | L | - | ARCA-001 |
| ARCA-004 | Modelo de importes completo (`ImpTotConc`, `ImpOpEx`, `ImpTrib`) | P0 | BACKLOG | L | - | ARCA-001 |
| ARCA-005 | Pre-validaciones locales por tipo para evitar rechazos ARCA | P0 | BACKLOG | L | - | ARCA-001, ARCA-004 |
| ARCA-006 | Reglas RG4444 para B/C (doc y umbral) | P1 | BACKLOG | M | - | ARCA-005 |
| ARCA-007 | Robustez de secuencia por `PtoVta/CbteTipo` | P1 | BACKLOG | M | - | ARCA-005 |
| ARCA-008 | Parseo completo de `FECompConsultar` (incl. observaciones y emision) | P1 | BACKLOG | M | - | ARCA-001 |
| ARCA-009 | Normalizacion de nomenclatura y retiro de clase M del alcance | P1 | BACKLOG | S | - | ARCA-001 |
| ARCA-010 | Catalogos ARCA vivos para dominio usado (`FEParamGet*`) | P1 | BACKLOG | L | - | ARCA-001 |
| ARCA-011 | Multimoneda real (si se habilita) | P2 | BACKLOG | M | - | ARCA-010 |
| ARCA-012 | Observabilidad por codigos ARCA | P2 | BACKLOG | M | - | ARCA-008 |
---
 Detalle funcional por feature
 ARCA-001 - Canon de tipos permitidos
**Objetivo**
Unificar un unico set de tipos soportados en backend, frontend, renderer y constantes.
**Entregables**
- Lista central unica de tipos permitidos
- Rechazo de tipos fuera de alcance en API/importacion/UI
- Tests de regresion de tipos permitidos/no permitidos
**DoD**
- No se puede crear/facturar tipos fuera del set objetivo
- UI muestra solo tipos objetivo
- Tests verdes
---
 ARCA-002 - Soporte Recibos B/C (009/015)
**Objetivo**
Cerrar gaps para tipos 9 y 15 en formularios, render, consulta y reglas.
**Entregables**
- Tipos 9/15 en selects, labels, renderer, utils de formato
- Validaciones especificas donde aplique
**DoD**
- Factura/consulta/render de 9 y 15 funciona de punta a punta
---
 ARCA-003 - RG 5616 y Condicion IVA Receptor
**Objetivo**
Resolver y validar `CondicionIVAReceptorId` correctamente por clase de comprobante.
**Entregables**
- Fuente de verdad por `FEParamGetCondicionIvaReceptor`
- Mapping robusto receptor textual -> ID ARCA
- Validacion previa por clase A/B/C
- Manejo de errores 10242/10243/10246
**DoD**
- No salen requests con combinaciones invalidas
- Errores de condicion IVA se reducen de forma visible
---
 ARCA-004 - Modelo de importes completo
**Objetivo**
Persistir y procesar todos los importes requeridos por WSFE para estos comprobantes.
**Entregables**
- Campos: `ImpTotConc`, `ImpOpEx`, `ImpTrib`
- API + CSV + UI + builder ajustados
- Reglas de sumatoria consistentes con manual
**DoD**
- Request ARCA reflejable 1:1 desde datos persistidos
- Sumatorias y redondeos validados por tests
---
 ARCA-005 - Pre-validaciones locales por tipo
**Objetivo**
Validar localmente lo critico antes de enviar a ARCA para bajar rechazo operativo.
**Entregables**
- Validaciones por tipo y documento
- Reglas de notas (comprobante asociado obligatorio)
- Reglas de fechas por concepto
- Reglas C (sin IVA discriminado)
**DoD**
- Mensajes de error de negocio claros
- Menos rechazos evitables en ARCA
---
 ARCA-006 - Reglas RG4444 para B/C
**Objetivo**
Aplicar validaciones de umbral/identificacion para B/C segun monto.
**Entregables**
- Validacion local parametrizable de umbral
- Cobertura de casos unitarios (menor/mayor umbral)
**DoD**
- Casos B/C cumplen reglas de identificacion previas a envio
---
 ARCA-007 - Secuencia de comprobantes robusta
**Objetivo**
Reducir riesgo de colision de numeracion en ejecucion concurrente.
**Entregables**
- Estrategia de asignacion segura por `PtoVta/CbteTipo`
- Reintentos idempotentes ante timeout
**DoD**
- Sin errores de secuencia por concurrencia en pruebas controladas
---
 ARCA-008 - Parseo completo de FECompConsultar
**Objetivo**
Exponer mas datos utiles para soporte y trazabilidad.
**Entregables**
- Parseo y serializacion completa de respuesta relevante
- UI de consulta con datos enriquecidos
**DoD**
- Operacion soporte puede diagnosticar un comprobante sin revisar logs crudos
---
 ARCA-009 - Limpieza clase M y nomenclatura
**Objetivo**
Alinear discurso y comportamiento al alcance actual (sin M).
**Entregables**
- Ajuste de labels/tipos visibles
- Consistencia en renderer y utilidades
**DoD**
- Ningun flujo de negocio ofrece M si no esta en alcance
---
 ARCA-010 - Catalogos ARCA vivos
**Objetivo**
Evitar drift normativo por hardcode.
**Entregables**
- Integracion cacheada de metodos `FEParamGet*` necesarios para este alcance
- Estrategia de refresh y fallback
**DoD**
- Cambios de catalogo no implican hotfix inmediato de codigo
---
 ARCA-011 - Multimoneda (condicional)
**Objetivo**
Cubrir completamente moneda != PES si negocio lo requiere.
**Entregables**
- Cotizacion oficial con fecha
- Reglas `MonId/MonCotiz` consistentes
**DoD**
- Emision multimoneda sin rechazos de cotizacion evitables
---
 ARCA-012 - Observabilidad por codigos ARCA
**Objetivo**
Priorizar mejoras con datos reales de rechazos/observaciones.
**Entregables**
- Metricas por codigo ARCA
- Top errores por periodo/tenant/facturador
**DoD**
- Backlog de mejora guiado por datos, no por percepcion
---
 Plan de ejecucion sugerido
 Sprint 1 (P0)
- ARCA-001
- ARCA-002
- ARCA-003 (fase 1: resolver ID y validar clase)
- ARCA-004 (fase 1: modelo + backend)
- ARCA-005 (fase 1: reglas criticas)
 Sprint 2 (P0/P1)
- ARCA-003 (fase 2: ajustes UX + padron)
- ARCA-004 (fase 2: frontend/CSV completo)
- ARCA-005 (fase 2: cobertura completa)
- ARCA-006
- ARCA-009
 Sprint 3 (P1/P2)
- ARCA-007
- ARCA-008
- ARCA-010
- ARCA-012
- ARCA-011 (solo si aplica)
---
 Registro de decisiones
- [YYYY-MM-DD] Se define alcance solo comprobantes 1,2,3,6,7,8,9,11,12,13,15.
- [YYYY-MM-DD] Se excluye CAEA/FCE/49 de esta etapa.
- [YYYY-MM-DD] ...
 Registro de avances
- [YYYY-MM-DD] ARCA-001 iniciado.
- [YYYY-MM-DD] ARCA-001 finalizado.
- [YYYY-MM-DD] ...