// Node.js deve ter versão 10.23 - 17.x. por causa do rclnodejs

const express = require('express');
const path = require('path');
const mongoose = require('mongoose');
require('dotenv').config();

const patientRoutes = require('./routes/patientRoutes');
const monitoringRoutes = require('./routes/monitoringRoutes');

const PORT = process.env.PORT || 3001;
const app = express();

// middleware
app.use(express.static('public'));
app.use(express.json());

let dbURI = ''
switch (process.argv[2]) {
    case 'development':
        dbURI = process.env.DB_CONNECTION_STRING_LOCAL
        break;

    default:
        dbURI = process.env.DB_CONNECTION_STRING_PROD
        break;
}

const options = {
    dbName: 'mycaredb',
    useNewUrlParser: true,
    serverSelectionTimeoutMS: 5000
};

mongoose.connect(dbURI, options)
    .then(() => app.listen(PORT, () => {console.log(`Server started at ${PORT}`);}))
    .catch((error) => console.log(error));

// defining bootstrap routes
app.use('/css', express.static(path.join(__dirname, 'node_modules/bootstrap/dist/css')))
app.use('/js', express.static(path.join(__dirname, 'node_modules/bootstrap/dist/js')))
app.use('/js', express.static(path.join(__dirname, 'node_modules/jquery/dist')))


// routes
app.use(patientRoutes);
app.use(monitoringRoutes);