const path = require('path');

module.exports.monitoring_get = (req, res) => {
    res.status(200).sendFile( path.join(__dirname, '../views/monitoring.html') );
}
