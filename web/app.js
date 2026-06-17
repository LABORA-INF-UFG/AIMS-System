// AIMS Web Server
// Express.js backend for patient management and monitoring UI.
// Connects to MongoDB and serves static HTML views.

const express = require('express');
const path = require('path');
const mongoose = require('mongoose');

// Load .env file only in local development (Docker injects env vars directly)
if (!process.env.MONGO_URI) {
    require('dotenv').config();
}

const patientRoutes = require('./routes/patientRoutes');
const monitoringRoutes = require('./routes/monitoringRoutes');

const PORT = process.env.WEB_PORT || process.env.PORT || 3001;
const MONGO_URI = process.env.MONGO_URI || 'mongodb://localhost:27017/mycaredb';

const app = express();

// Middleware
app.use(express.static('public'));
app.use(express.json());

// Routes
app.use(patientRoutes);
app.use(monitoringRoutes);

// MongoDB connection options
const mongoOptions = {
    dbName: 'mycaredb',
    serverSelectionTimeoutMS: 5000,
};

/**
 * Start the server after connecting to MongoDB.
 * Uses async/await with proper error handling.
 */
const startServer = async () => {
    try {
        await mongoose.connect(MONGO_URI, mongoOptions);
        console.log(`Connected to MongoDB at ${MONGO_URI}`);

        app.listen(PORT, () => {
            console.log(`AIMS Web Server started at http://localhost:${PORT}`);
        });
    } catch (error) {
        console.error('Failed to connect to MongoDB:', error.message);
        console.error('Retrying in 5 seconds...');
        setTimeout(startServer, 5000);
    }
};

// Handle graceful shutdown
process.on('SIGTERM', async () => {
    console.log('SIGTERM received. Shutting down gracefully...');
    await mongoose.disconnect();
    process.exit(0);
});

process.on('SIGINT', async () => {
    console.log('SIGINT received. Shutting down gracefully...');
    await mongoose.disconnect();
    process.exit(0);
});

startServer();