var graficoHistogramaAtivo = false;
var graficoSinalAtivo = false;
var graficoMapaAtivo = false;
var graficoSinalAtivo2 = false;
var graficoMapaMmWAtivo = false;

var buffer1 = []; //for subcarrier 1
var buffer2 = []; //for subcarrier 2
var bufferSamples = 100; //buffer length

//sinusoidal signal frequency
var frequency = 10;

function decodeMessage(message) {
  msg = String(message.data).replace(/["]/g, '*');
  msg = msg.replace(/[']/g, '"');
  msg = msg.replace(/[*]/g, "'");
  //return msg;
  return JSON.parse(msg);
}

//Some control variables
receivedFirstMessage = false;

// Connecting to ROS
// -----------------
let ros = new ROSLIB.Ros();

// If there is an error on the backend, an 'error' emit will be emitted.
ros.on('error', function(error) {
  document.getElementById('loading').style.display = 'none';
  document.getElementById('connecting').style.display = 'none';
  document.getElementById('error').style.display = 'inline';
  console.log(error);
});

// Find out exactly when we made a connection.
ros.on('connection', function() {
  console.log('Connection made!!');
  document.getElementById('error').style.display = 'none';
  document.getElementById('connecting').style.display = 'none';
});

ros.on('close', function() {
  //console.log('Connection closed.');
  document.getElementById('connecting').style.display = 'none';
});

// Create a connection to the rosbridge WebSocket server.
ros.connect('ws://localhost:9090');

// AIMS Vision person detection
let listenerThereIsPerson = new ROSLIB.Topic({
  ros: ros,
  name: '/there_is_person',
  messageType: 'std_msgs/msg/Bool'
});

// var atualizada pelo nó da there_is_person, com default em 'true'
let is_person = true;
let equipments = {
  camera: false,
  mmwave: false,
  none: true
}

// Verifica se os nós da visão e da mmwave estão conectados
setInterval(() => {
  ros.getNodes((res) => {
    //console.log(res)
    if(searchStringInArray('/Pose_Estimation', res) != -1){
      equipments.camera = true;
      equipments.none = false;
    }
    if(searchStringInArray('/pkt_mmw_publisher', res) != -1){
      equipments.mmwave = true;
      equipments.none = false;
    }
    if(!equipments.mmwave && !equipments.camera){
      equipments.none = true
      console.log("Câmera e MMwave desconectadas.")
    }
    
  });
}, 5000);


/**
 * Seta o valor da var global is_person.
 *
 * @param {string} issuer - Nome do callback do equipamento que está setando o valor de is_person.
 * Podendo ser 'camera' ou 'mmwave'.
 * @param {boolean} status - Status da detecção da pessoa pelo equipamento.
 */
function setIs_person(issuer, status) {
  if (equipments.camera && equipments.mmwave){
    if(issuer === 'camera') {
      is_person = status
    }
  }
  else {
    is_person = status
  }
}

function toggle_no_person_div(){
  const no_person_div = document.getElementById('no_person_div');
  const results_div = document.getElementById('results');
  const debug = document.getElementById('debug').checked;
  
  if(debug || is_person && !equipments.none){
    no_person_div.style.display = 'none'
    results_div.style.display = 'inline'
  }
  else{
    no_person_div.style.display = 'inline'
    results_div.style.display = 'none'
  }
}

setInterval(toggle_no_person_div, 2000);


listenerThereIsPerson.subscribe((message)=>{
  console.log('Received from /there_is_person: ' + String(message.data))
  if (message.data){
    setIs_person('camera', true)
  }
  else{
    setIs_person('camera', false)
  }
});

//Subscribing to a Topic for the heatmap image
//----------------------
let listenerHeatmap = new ROSLIB.Topic({
  ros: ros,
  name: '/heatmap',
  messageType: 'sensor_msgs/msg/Image'
});
// Função callback, chamada sempre que uma nova mensagem é recebida do tópico.
listenerHeatmap.subscribe(function(message) {
  //console.log('Received image on ' + listenerHeatmap.name + ': ' + message);
  //calling the atualization function
  if (graficoMapaAtivo)
      atualizaMapaImg(message);
});

//Subscribing to a Topic for the camera image from Vision Team
let listenerVisionCameraImage = new ROSLIB.Topic({
  ros: ros,
  name: '/vision_image',
  messageType: 'sensor_msgs/msg/Image'
});
listenerVisionCameraImage.subscribe((message)=>{
  const img = 'data:image/png;base64,' + message.data; // TODO: adequar para o formato enviado pelo código da Visão
  document.getElementById('img-camera-visao').src = img
});

//Subscribing to a Topic for the mmWave heatmap image
let listenerHeatmapMmW = new ROSLIB.Topic({
  ros: ros,
  name: '/heatmapmmw',
  messageType: 'sensor_msgs/msg/Image'
});
let showOnce = 0;
// Função callback
listenerHeatmapMmW.subscribe(function(message) {
   const imgData = 'data:image/png;base64,' + message.data;
   if (graficoMapaMmWAtivo){
   	showOnce = showOnce + 1;   	
	if (showOnce % 1 == 0) {
	   	const imgElement = document.getElementById('heatmapMmWImg');
	   	imgElement.src = imgData;	
	   	document.getElementById("loadingHeatmapMmW").style.display = 'none';	   	
	}
   }
});

//Subscribing to a Topic for the mmWave breathing estimation
let listenerBRMmW = new ROSLIB.Topic({
  ros : ros,
  name : '/brmmw',
  messageType : 'custom_interfaces/msg/MmWVitalSignal'
});
// Função callback, chamada sempre que uma nova mensagem é recebida do tópico.
listenerBRMmW.subscribe(function(message) {
  console.log('Received message on ' + listenerBRMmW.name + ': ' + message.rate);
  
  if(message.rate > 0.0){
    setIs_person('mmwave', true)
  }
  else{
    setIs_person('mmwave', false)
  }

});
//Subscribing to a Topic for the mmWave heart estimation
let listenerHRMmW = new ROSLIB.Topic({
  ros : ros,
  name : '/hrmmw',
  messageType : 'custom_interfaces/msg/MmWVitalSignal'
});
// Função callback, chamada sempre que uma nova mensagem é recebida do tópico.
listenerHRMmW.subscribe(function(message) {
  console.log('Received message on ' + listenerHRMmW.name + ': ' + message.rate);
  //let decoded = decodeMessage(message);
  let decoded = message;
});


//Subscribing to a Topic for the cardiofi breathing estimation
let listenerBRCardiofi = new ROSLIB.Topic({
  ros : ros,
  name : '/breath_estimate_cardiofi',
  messageType : 'std_msgs/msg/Float32'
});
// Função callback, chamada sempre que uma nova mensagem é recebida do tópico.
listenerBRCardiofi.subscribe(function(message) {
  console.log('Received message on ' + listenerBRCardiofi.name + ': ' + message.data);
  //var decoded = decodeMessage(message);
  var decoded = message;
});

//Subscribing to a Topic for the cardiofi heart estimation
let listenerHRCardiofi = new ROSLIB.Topic({
  ros : ros,
  name : '/heart_estimate_cardiofi',
  messageType : 'std_msgs/msg/Float32'
});
// Função callback, chamada sempre que uma nova mensagem é recebida do tópico.
listenerHRCardiofi.subscribe(function(message) {
  console.log('Received message on ' + listenerBRCardiofi.name + ': ' + message.data);
  //var decoded = decodeMessage(message);
  var decoded = parseInt(Math.floor(message.data));
  document.getElementById("hr_value").innerHTML = decoded;
});

//Subscribing to a Topic for heart control (heart observations from the monitoring device)
let listenerHeartControl = new ROSLIB.Topic({
    ros : ros,
    name : '/heart_control',
    messageType : 'custom_interfaces/msg/HeartControl'
});

let heart_beats_buffer = []
listenerHeartControl.subscribe(function(message) {
  heart_beats_buffer.push(message.timestamp)

  let last_element = message.timestamp
  // Windows_size in seconds
  let window_size = 30
  let window_size_ns = window_size * 1000000000
  while (heart_beats_buffer.length > 1) {
    if ( (last_element - heart_beats_buffer[0]) >= window_size_ns) {
      heart_beats_buffer.shift()
    }
    else {
      let bpm_ground_truth_estimave = heart_beats_buffer.length * (60/window_size)
      document.getElementById("hr_ground_truth").innerText = String(bpm_ground_truth_estimave);
      break;
    }
  }
  document.getElementById("hr_ground_truth").style.display = 'inline-block';

  console.log('Received message on ' + listenerHeartControl.name + ': ' + message.timestamp);
  document.getElementById("heart-beat").style.display = 'inline-block';
  setTimeout(hideHeartBeat, 500);
});

//Subscribing to a Topic for heart control (heart observations from the monitoring device)
let listenerBreathControl = new ROSLIB.Topic({
    ros : ros,
    name : '/breath_control',
    messageType : 'custom_interfaces/msg/BreathControl'
});

let breath_buffer = []
// Windows_size in seconds
let window_time = 30
let breath_control_started = false
let time_no_breath = 0
listenerBreathControl.subscribe(function(message) {
  breath_buffer.push(message.timestamp)
  time_no_breath = 0;
  //starting the timer for breathing control
  if (!breath_control_started){
    setInterval(function() {
        let currentTimeInSeconds = Math.floor(Date.now() / 1000);
        let firstTimestamp = breath_buffer[0] / 1000000000; // Convert timestamp to seconds
        let time_diff =  (currentTimeInSeconds - firstTimestamp);
        if (time_diff >= window_time) {
            // Remove the first element from breath_buffer
            breath_buffer.shift();
            brpm_ground_truth_estimave = breath_buffer.length * (60 / window_time)
            document.getElementById("br_ground_truth").innerText = String(brpm_ground_truth_estimave);
        }
        if (time_no_breath >= 20){
            document.getElementById("br_ground_truth").innerText = "Apneia";
        }
        time_no_breath++;
    }, 1000);
    breath_control_started = true;
  }
  document.getElementById("br_ground_truth").style.display = 'inline-block';
  console.log('Received message on ' + listenerBreathControl.name + ': ' + message.timestamp);
  document.getElementById("lung-beat").style.display = 'inline-block';
  setTimeout(hideLungBeat, 500);
});

function hideHeartBeat() {
    var heartBeat = document.getElementById('heart-beat');
    heartBeat.style.display = 'none';
  }
function hideLungBeat() {
    var lungBeat = document.getElementById('lung-beat');
    lungBeat.style.display = 'none';
  }

// Like when publishing a topic, we first create a Topic object with details of the topic's name
// and message type. Note that we can call publish or subscribe on the same topic object.
let listenerBR = new ROSLIB.Topic({
  ros : ros,
  name : '/breath_estimate',
  messageType : 'custom_interfaces/msg/BreathEstimate'
});

// Função callback, chamada sempre que uma nova mensagem é recebida do tópico.
listenerBR.subscribe(function(message) {
  //console.log('Received message on ' + listenerBR.name + ': ' + message);
  //var decoded = decodeMessage(message);
  var decoded = message;
  //console.log(message.apnea_detected);
  if (! receivedFirstMessage){
      receivedFirstMessage = true
  }

  if(is_person){
    document.getElementById('loading').style.display = 'none';
    document.getElementById("container-resultados").style.display = 'inline';
    //document.getElementById('results').style.display = 'inline';
    let brValue = document.getElementById('br_value');

    if (decoded.apnea_detected == 1){
      brValue.classList.add('apneia-value');
      brValue.classList.remove('normal-value');
      decoded.breath_rate = "Apneia";
    }else{
      brValue.classList.remove('apneia-value');
      brValue.classList.add('normal-value');
    }
    document.getElementById("br_value").innerHTML = decoded.breath_rate;
  }

  if (graficoHistogramaAtivo)
      atualizaHistograma(decoded.breath_rate);
  if (graficoSinalAtivo)
      atualizaSinal(decoded.breath_rate);
  if (graficoSinalAtivo2)
      atualizaSinal2(decoded.breath_rate);
});

//controle das abas de navegação
function ativaGrafico(tpGrafico){
  switch (tpGrafico) {
    case "nav-histograma-tab":
      graficoHistogramaAtivo = true;
      graficoMapaAtivo = false;
      graficoMapaMmWAtivo = false;
      break;
    case "nav-sinal-tab":
      graficoSinalAtivo = true;
      graficoMapaAtivo = false;
      break;
    case "nav-sinal-tabb":
      graficoSinalAtivo2 = true;
      graficoMapaAtivo = false;
      break;
    case "nav-mapa-tab":
      graficoMapaAtivo = true;
      graficoMapaMmWAtivo = false;
      break;
    case "nav-mapa-mmw-tab":
      graficoMapaMmWAtivo = true;
      break;
  }

}

let persistence_request_publisher = new ROSLIB.Topic({
  ros: ros,
  name: '/persistence_bridge/request',
  messageType: 'custom_interfaces/msg/PersistenceRequest'
});

const form = document.getElementById('metadados_form');
const form_btn = document.getElementById('btn_persistencia');
let num_frames = null;
form.addEventListener('submit', (event) => {
  event.preventDefault();

  console.log("Botao apertado")
  if (form.btn_status.value === '0'){
    // The subject ID becomes part of the capture file name
    const subject_id = form.subject_id.value.trim();
    const subject_id_valid = /^[A-Za-z0-9_-]+$/.test(subject_id);
    document.getElementById('subject_id_error').style.display = subject_id_valid ? 'none' : 'block';
    if (!subject_id_valid) return;

    num_frames = Number(form.num_frames.value);

    let request_message = new ROSLIB.Message({
      capture_name: form.capture_name.value,
      subject_id: subject_id,
      rx_nic_model: 'Intel 5300',
      tx_nic_model: 'Intel 5300',
      subject_position: form.subject_position.value,
      antenna_distance_cm: Number(form.antenna_distance_cm.value),
      num_frames: num_frames
    });
    
    persistence_request_publisher.publish(request_message);

    form_btn.innerText = 'Cancelar'
    form_btn.value = '1'

    document.getElementById('barra_progresso').setAttribute('max', form.num_frames.value);
    document.getElementById('progress_div').style.display = 'block';
  }
  // else {
  //   form_btn.innerText = 'Persistir'
  //   form_btn.value = '0'
  // }

});

let persistence_response_listener = new ROSLIB.Topic({
  ros: ros,
  name: 'persistence_bridge/response',
  messageType: 'std_msgs/msg/String'
});

persistence_response_listener.subscribe((message) => {
  form_btn.innerText = 'Persistir'
  form_btn.value = '0'
  document.getElementById('progress_div').style.display = 'none';
});

let persistence_feedback_listener = new ROSLIB.Topic({
  ros: ros,
  name: 'persistence_bridge/feedback',
  messageType: 'custom_interfaces/msg/PersistenceFeedback'
});

persistence_feedback_listener.subscribe((message) => {
  document.getElementById('barra_progresso').setAttribute('value', message.captured_frames);
  document.getElementById('texto_progresso').innerText = `Pacotes: ${message.captured_frames}/${num_frames}`;
});

// ===================
function searchStringInArray (str, strArray) {
  for (var j=0; j<strArray.length; j++) {
      if (strArray[j].match(str)) return j;
  }
  return -1;
}