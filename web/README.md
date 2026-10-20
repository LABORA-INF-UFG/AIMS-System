# AIMS Web Interface

The AIMS web interface is an [Express.js](https://expressjs.com/) server that serves the monitoring dashboard for the AIMS ROS2 system. The browser talks to ROS2 directly through [roslibjs](https://github.com/RobotWebTools/roslibjs) and a rosbridge WebSocket server; the Express server does not use ROS and has no database.

## What it does

- `GET /` : landing page.
- `GET /monitoring` : dashboard with the live charts (breathing estimate, heatmap, ...) and the persistence panel to record CSI captures.
- `GET /config` : returns `{"rosbridgePort": <number>}`. The browser connects to `ws://<hostname that served the page>:<rosbridgePort>`, so the dashboard also works from another machine on the LAN.

Captures are identified by a free-text **Subject ID** typed in the persistence form (letters, digits, `_` and `-`). There is no login, patient registry or database.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `WEB_PORT` | `3001` | Port the server listens on (inside Docker it is fixed to 3001 and `WEB_PORT` in the root `.env` sets the published host port) |
| `ROSBRIDGE_PORT` | `9090` | Port returned by `GET /config` |
| `NODE_ENV` | `development` | Node.js environment |

See [.env.example](.env.example).

## Run with Docker (recommended)

From the repository root:

```bash
docker compose up -d --build
```

Open http://localhost:3001. The image compiles the Tailwind CSS during the build.

## Run locally (without Docker)

You need Node.js 20 and a running rosbridge server, for example from a ROS2 Humble installation:

```bash
sudo apt install ros-humble-rosbridge-server
source /opt/ros/humble/setup.bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

Then, in `web/`:

```bash
npm install
npm run build:css
npm run dev        # nodemon app.js; use `npm start` for plain node
```

Expected output: `AIMS Web Server started at http://localhost:3001`.

For the full system, start the ROS2 nodes too (`ros2 launch csi aims_launch.py`, see [aims_launch.py](../aims_ws/src/csi/launch/aims_launch.py)). The launch file does not start the web server.
