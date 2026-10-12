# ADR-0006: Remove MongoDB and Patient Management; Subjects Identified by a Free-Text ID

- **Status**: Accepted
- **Date**: 2026-10-12
- **Deciders**: Luiz Fernando de Freitas Oliveira
- **Technical context**: Simplification of the web application before the public release of the repository

---

## Context

The web application had a patient registry (create, list, search) backed by MongoDB. There was no login or user feature. The monitoring dashboard stayed hidden until a patient was selected, and the patient's name was sent to ROS and ended up in the capture file names.

For a research reference repository this had three problems:
- A database service had to be running just to open the dashboard, so a plain `docker compose up` was not enough to see the system working.
- Storing patient names is unnecessary for the experiments and is a privacy liability in a public repository. Captures only need a label that identifies the subject.
- The registry was unrelated to the sensing pipeline the article describes.

## Decision

Remove MongoDB and the whole patient feature (model, controller, routes, registration and patients pages, `mongo` service and volume, `MONGO_URI`). The monitoring page is available immediately, and the persistence form takes a **free-text Subject ID** (allowed characters `A-Za-z0-9_-`, required), validated in the browser, sent in the ROS field `subject_id` and used as part of the capture file name.

## Alternatives Considered

| Alternative | Why it was rejected |
|---|---|
| Keep MongoDB but make it optional | Two code paths (with and without a database) to maintain for a feature the research does not need. |
| Replace MongoDB with a file or SQLite store | Still a patient registry nobody asked for; adds code and a persistence format to document. |
| Keep patient names as free text | Personal names in file names are a privacy risk; an opaque ID is enough. |

## Consequences

### Positive
- One service less: the stack is `ros2-nodes`, `rosbridge` and `web`.
- The dashboard works right after `docker compose up`.
- No personal data is stored by the system; subjects are identified by IDs chosen by the researcher.
- Smaller web image and dependency list (`mongoose` removed).

### Negative / Trade-offs
- There is no list of subjects or history of captures in the UI; the files in `captures/` are the only record.
- Researchers who need a subject registry must keep it outside AIMS, and mapping an ID to a person is their responsibility.
- Breaking change for existing data: the ROS field `nome_paciente` is now `subject_id` (see the v0.3.0 entry in the [changelog](../CHANGELOG.md)).

## Related Links
- [ADR-0001](./ADR-0001-docker-compose-for-orchestration.md) — Docker Compose for orchestration
- [ADR-0004](./ADR-0004-rosbridge-as-web-ros2-integration-layer.md) — Rosbridge as integration layer
