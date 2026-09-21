# System Flows

1. **Onboarding (`US-01`):** a user signs up and can add a first endpoint.
2. **Endpoint registration (`US-02`):** the user supplies URL, expected status, interval, and later safe assertion settings. The API validates and stores the monitor.
3. **Scheduled check (`US-05`, `DR1`):** Beat selects due monitors and queues a monitoring task. The worker uses an explicit timeout, monitor user-agent, and rate limits.
4. **Evaluation (`US-06`, `US-07`):** deterministic code records status, timeout, connection/SSL, and later body assertion outcomes.
5. **Failure threshold (`FR5`, `DR5`):** one failure is recorded but does not create an incident. Consecutive failures crossing the configured threshold open one incident.
6. **Alert dispatch (`US-10`, `US-11`):** an incident state transition queues notification work. Repeated failures do not create duplicate alerts.
7. **Notification retry (`FR8`):** temporary delivery failures retry with bounded backoff, then record final delivery status.
8. **Recovery:** a successful check closes or resolves the active incident once and can queue one recovery notice.
9. **Maintenance (`US-04`):** checks still run. Incident and alert behavior is suppressed during an active maintenance window as required.
10. **History and uptime (`FR4`, `DR3`):** stored results support deterministic uptime: `(total time - downtime) / total time * 100`.
11. **Monthly report (`US-15`):** deterministic stored data produces a later report.
12. **AI analysis:** deterministic facts become small structured incident context, then an `ai` queue task requests advisory analysis. An unavailable provider cannot stop monitoring.
13. **Future RAG:** embeddings and approved runbooks or incident knowledge are searched in pgvector, then used as context for advisory answers.
14. **RBAC (`US-19`):** authentication identifies a user; backend authorization checks the team role and permission before protected work.
15. **Audit (`US-18`):** important configuration and permission changes create append-oriented audit records.
