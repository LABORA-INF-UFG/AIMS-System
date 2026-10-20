// AIMS Web Server
// Express.js backend that serves the monitoring UI.

const express = require('express');

const monitoringRoutes = require('./routes/monitoringRoutes');

const PORT = process.env.WEB_PORT || process.env.PORT || 3001;

const app = express();

// Middleware
app.use(express.static('public'));
app.use(express.json());

// Routes
app.use(monitoringRoutes);

// Runtime config for the browser (rosbridge runs on the same host as this page)
app.get('/config', (req, res) => {
    res.json({ rosbridgePort: Number(process.env.ROSBRIDGE_PORT) || 9090 });
});

const server = app.listen(PORT, () => {
    console.log(`AIMS Web Server started at http://localhost:${PORT}`);
});

// Handle graceful shutdown
for (const signal of ['SIGTERM', 'SIGINT']) {
    process.on(signal, () => {
        console.log(`${signal} received. Shutting down gracefully...`);
        server.close(() => process.exit(0));
    });
}
