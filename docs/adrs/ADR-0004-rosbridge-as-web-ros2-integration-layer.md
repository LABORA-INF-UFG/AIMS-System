# ADR-0004: Rosbridge as the Integration Layer between ROS2 and the Web

- **Status**: Accepted
- **Date**: 2026-06-17 (updated 2026-10-12)
- **Deciders**: Luiz Fernando de Freitas Oliveira
- **Technical context**: Communication strategy between the web frontend and the ROS2 ecosystem

---

## Context

The web frontend (Express.js + HTML) must consume ROS2 topic data in real time (heart rate, breathing rate, heatmaps, etc.) to show it in the monitoring interface.

There are two main ways to integrate a web application with ROS2:

1. **Direct**: use a library such as `rclnodejs` to connect the Node.js process to DDS as a ROS2 node.
2. **Through a bridge**: use `rosbridge_suite`, which exposes a WebSocket server (`rosbridge_server`) that any web client can reach with the `roslib.js` JavaScript library.

The project originally listed `rclnodejs` as a dependency in `web/package.json`, but it was **not used by any backend file**. Real communication with ROS2 already happened through the rosbridge WebSocket on the client side (browser).

## Decision

Keep and formalize **`rosbridge_suite`** as the only integration layer between the web frontend and ROS2 topics, running as a separate service (`rosbridge`) in Docker Compose. The `rclnodejs` dependency was **removed** from `web/package.json`.

Communication in the frontend happens entirely through **`roslib.js`** (browser side), which opens a WebSocket connection to rosbridge.

## Alternatives Considered

| Alternative | Why it was rejected |
|---|---|
| **`rclnodejs` in the Node.js backend** | Needs native C++ extensions (`int64-napi`), incompatible with Alpine Linux without build tools. Greatly increases image size and build complexity. It would also make the web server a ROS2 node, mixing responsibilities. |
| **gRPC-Web** | Adds infrastructure complexity (Envoy or similar proxy) with no clear benefit over the WebSocket + JSON already supported by `roslib.js`. |
| **MQTT bridge** | Needs an extra MQTT broker and custom serialization libraries for ROS2 message types. |

## Consequences

### Positive
- **Clear separation of responsibilities**: the web server (`web`) only serves HTML/CSS/JS and a small `GET /config` endpoint. ROS2 access is done by the browser directly over WebSocket.
- **Isolated, restartable service**: `rosbridge` can be restarted independently of the processing nodes without affecting the web server.
- **No native dependency in the Node.js build**: removing `rclnodejs` eliminated build errors (`int64-napi`) and reduced the web image from ~450 MB to ~180 MB.
- **Universal compatibility**: any WebSocket-capable client (browser, Jupyter, Python scripts with `roslibpy`) can consume the data.

### Negative / Trade-offs
- The browser needs **direct network access to rosbridge** on its port (default `9090`). Behind a reverse proxy (e.g. nginx) the proxy must be configured to upgrade WebSocket connections.

### Update (2026-10-12): rosbridge URL no longer hardcoded
The URL used to be hardcoded as `ws://localhost:9090` in `rosControllerMonitoring.js`, which broke access from another machine. The frontend now calls `GET /config` on the web server to get `rosbridgePort` (from `ROSBRIDGE_PORT`, default 9090) and connects to `ws://<hostname that served the page>:<rosbridgePort>`. Accessing the dashboard from another machine on the LAN therefore works as long as the rosbridge port is reachable.

The web server no longer manages patient data (see [ADR-0006](./ADR-0006-remove-mongodb-and-patient-management.md)).

## Related Links
- [ADR-0001](./ADR-0001-docker-compose-for-orchestration.md) — Docker Compose for orchestration
- [ADR-0003](./ADR-0003-host-networking-for-ros2-dds.md) — Host networking for ROS2 DDS (superseded)
- [ADR-0008](./ADR-0008-bridge-networking-as-default.md) — Bridge networking as default
