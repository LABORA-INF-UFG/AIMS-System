const {Router} = require('express');
const monitoringController = require('../controllers/monitoringController');

const router = Router();

router.get('/monitoring', monitoringController.monitoring_get);

module.exports = router;