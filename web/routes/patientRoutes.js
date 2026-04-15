const {Router} = require('express');
const patientController = require('../controllers/patientController');

const router = Router();

router.get('/patients', patientController.patients_GET);

router.get('/registration', patientController.patient_registration_GET);
router.post('/registration', patientController.patient_registration_POST);

router.get('/getpatients', patientController.patient_query_GET);

router.put('/updatepatient', patientController.update_patient_PUT);

router.delete('/deletepatient', patientController.delete_patient_DELETE);

module.exports = router;
