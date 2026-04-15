const { userInfo } = require('os');
const path = require('path');
const Patient = require('../models/Patient');
const mongoose = require('mongoose');

module.exports.patients_GET = (req, res) => {
    res.status(200).sendFile( path.join(__dirname, '../views/patients.html') );
}

module.exports.patient_registration_GET = (req, res) => {
    res.status(200).sendFile( path.join(__dirname, '../views/registration.html') );
}

module.exports.patient_registration_POST = async (req, res) => {

    const {nome, data_nascimento, altura, peso, sexo} = req.body;
    try {
        
        const patient = await Patient.create({nome, data_nascimento, altura, peso, sexo});
        console.log(`Paciente ${nome} registrado com sucesso!`);
        res.status(201).json("{msg: 'Paciente registrado com sucesso.'}");

    } catch (error) {
        console.log(error);
        res.status(400).json("{msg: 'Paciente não registrado.'}");
    }
    
}

module.exports.patient_query_GET = async (req, res) => {
    try {
        if(req.query.nome != '')
        {
            const matching_patients = await Patient.find(
                {nome: {'$regex' : `^${req.query.nome}`, '$options' : 'i'}}
            ).sort({nome: 1});
        
            if(matching_patients.length > 0){
                res.status(200).json(matching_patients);
            }
            else if(matching_patients == 0)
            {
                res.status(200).json({});
            }
        }
        else
        {
            res.status(200).json({});
        }
        
    }
    catch (error) {
        console.log(error);
    }

}

module.exports.update_patient_PUT = async (req, res) => {

    const {nome, data_nascimento, altura, peso, sexo} = req.body;

    //console.log(req.body._id)

    try {
        const updated_patient = await Patient.findByIdAndUpdate(req.body._id, 
            {nome, data_nascimento, altura, peso, sexo});

        console.log(`Paciente ${nome} atualizado com sucesso!`);

        res.status(200).json(updated_patient);

    } catch (error) {
        console.log(error);
    }
}

module.exports.delete_patient_DELETE = async (req, res) => {
  try {
    const id = req.query.id;
    if (!id)
    {
      return res.status(400).json({ error: "missing id parameter" });
    } else if (!mongoose.Types.ObjectId.isValid(id))
    {
      return res.status(400).json({ error: "invalid id" });
    }

    const patient = await Patient.findByIdAndDelete(id);
    if (!patient)
    {
      res.status(404).end();
    } else
    {
      res.status(204).end();
    }
  } catch (error) {
    console.log(error);
    res.status(500).json({ error: "server error" });
  }
}
