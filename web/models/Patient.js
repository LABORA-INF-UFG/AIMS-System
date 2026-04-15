const mongoose = require('mongoose');

const patientSchema = new mongoose.Schema({
    nome: {
        type: String,
        required: true
    },
    data_nascimento: {
        type: Date,
        required: true
    },
    altura: {
        type: Number,
        required: true
    },
    peso: {
        type: Number,
        required: true
    },
    sexo: {
        type: String,
        required: true
    }
});

const Patient = mongoose.model('patient', patientSchema);

module.exports = Patient;