var histogramChartActive = false;
var signalChartActive = false;
var heatmapChartActive = false;
var signalChartActive2 = false;
var mmwaveHeatmapChartActive = false;

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
  breathBtn.disabled = false;
  document.getElementById('error').style.display = 'none';
  document.getElementById('connecting').style.display = 'none';
});

const breathBtn = document.getElementById('breath_btn');
breathBtn.disabled = true;

ros.on('close', function() {
  breathBtn.disabled = true;
  //console.log('Connection closed.');
  document.getElementById('connecting').style.display = 'none';
});

// Create a connection to the rosbridge WebSocket server on the host that served
// this page (so it also works from other machines on the LAN). Port comes from /config.
fetch('/config')
  .then((res) => res.json())
  .then((cfg) => cfg.rosbridgePort, () => 9090)
  .then((port) => ros.connect(`ws://${window.location.hostname}:${port || 9090}`));

// AIMS Vision person detection
let listenerPersonPresent = new ROSLIB.Topic({
  ros: ros,
  name: '/person_present',
  messageType: 'std_msgs/msg/Bool'
});

// Updated by the presence node; defaults to 'true'
let is_person = true;
let equipments = {
  camera: false,
  mmwave: false,
  none: true
}

// AIMS Vision movement detection (latched Bool)
let listenerIsMoving = new ROSLIB.Topic({
  ros: ros,
  name: '/is_moving',
  messageType: 'std_msgs/msg/Bool'
});
let is_moving = null; // null until the first /is_moving message

// Check whether the vision and mmWave nodes are connected
setInterval(() => {
  ros.getNodes((res) => {
    //console.log(res)
    equipments.camera = searchStringInArray('/pose_estimation', res) != -1;
    equipments.mmwave = searchStringInArray('/pkt_mmw_publisher', res) != -1;
    equipments.none = !equipments.camera && !equipments.mmwave;
    if(!equipments.camera) is_moving = null; // back to "Waiting for camera"
    
  });
}, 5000);


/**
 * Sets the value of the global is_person variable.
 *
 * @param {string} issuer - Name of the equipment callback that is setting is_person.
 * Can be 'camera' or 'mmwave'.
 * @param {boolean} status - Person detection status reported by the equipment.
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

// Single place that decides between the "Subject not detected" card and the
// vitals. '' restores the stylesheet display (block / grid): 'inline' breaks both.
function toggle_no_person_div(){
  const debug = document.getElementById('debug').checked;
  const show_results = debug || (is_person && !equipments.none);
  document.getElementById('no_person_div').style.display = show_results ? 'none' : '';
  document.getElementById('results-container').style.display = show_results ? '' : 'none';
  document.querySelectorAll('.ground-truth').forEach(el => el.style.display = debug ? '' : 'none');

  document.getElementById('movement_div').style.display = show_results ? '' : 'none';
  document.getElementById('movement_waiting').style.display = is_moving === null ? '' : 'none';
  document.getElementById('movement_moving').style.display = is_moving === true ? '' : 'none';
  document.getElementById('movement_still').style.display = is_moving === false ? '' : 'none';
}

toggle_no_person_div();
setInterval(toggle_no_person_div, 2000);
document.getElementById('debug').addEventListener('change', toggle_no_person_div);


listenerPersonPresent.subscribe((message)=>{
  console.log('Received from /person_present: ' + String(message.data))
  if (message.data){
    setIs_person('camera', true)
  }
  else{
    setIs_person('camera', false)
  }
});

listenerIsMoving.subscribe((message)=>{
  is_moving = message.data;
  toggle_no_person_div();
});

//Subscribing to a Topic for the heatmap image
//----------------------
let listenerHeatmap = new ROSLIB.Topic({
  ros: ros,
  name: '/heatmap',
  messageType: 'sensor_msgs/msg/Image'
});
// Callback, called whenever a new message is received on the topic.
listenerHeatmap.subscribe(function(message) {
  //console.log('Received image on ' + listenerHeatmap.name + ': ' + message);
  //calling the update function
  if (heatmapChartActive)
      updateHeatmapImage(message);
});

//Subscribing to a Topic for the camera image from Vision Team
let listenerVisionCameraImage = new ROSLIB.Topic({
  ros: ros,
  name: '/vision_image',
  messageType: 'sensor_msgs/msg/CompressedImage'
});
listenerVisionCameraImage.subscribe((message)=>{
  document.getElementById('img-camera-vision').src = 'data:image/jpeg;base64,' + message.data;
});

//Subscribing to a Topic for the mmWave heatmap image
let listenerHeatmapMmW = new ROSLIB.Topic({
  ros: ros,
  name: '/heatmapmmw',
  messageType: 'sensor_msgs/msg/Image'
});
let showOnce = 0;
// Callback
listenerHeatmapMmW.subscribe(function(message) {
   const imgData = 'data:image/png;base64,' + message.data;
   if (mmwaveHeatmapChartActive){
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
// Callback, called whenever a new message is received on the topic.
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
// Callback, called whenever a new message is received on the topic.
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
// Callback, called whenever a new message is received on the topic.
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
// Callback, called whenever a new message is received on the topic.
listenerHRCardiofi.subscribe(function(message) {
  console.log('Received message on ' + listenerBRCardiofi.name + ': ' + message.data);
  //var decoded = decodeMessage(message);
  var decoded = parseInt(Math.floor(message.data));
  document.getElementById("hr_value").innerHTML = decoded;
});

// Control events (ground truth). Each source keeps its own state; sources are never mixed.
const CONTROL_SOURCES = {
  ui_button: { icon: 'bi-hand-index', label: 'Button' },
  h10: { icon: 'bi-heart-pulse', label: 'Polar H10' },
  nk: { icon: 'bi-display', label: 'Nihon Kohden' },
  mock: { icon: 'bi-robot', label: 'Mock' },
};
const RATE_WINDOW_MS = 30000;
const APNEA_MS = 20000;
const HIDE_MS = 60000;

// Per-topic state: source -> { timestamps ([{event ms, arrival ms}]), lastSeen, chip, valueEl }
const control_state = { breath: {}, heart: {} };
const control_container_id = { breath: 'br_ground_truth', heart: 'hr_ground_truth' };

function getControlSource(kind, source) {
  let s = control_state[kind][source];
  if (s) return s;
  const info = CONTROL_SOURCES[source] || { icon: 'bi-broadcast', label: source };
  const chip = document.createElement('span');
  chip.className = 'inline-flex items-center gap-1 font-bold text-gray-800 bg-gray-100 px-2 py-0.5 rounded transition-colors';
  chip.style.display = 'none';
  const icon = document.createElement('i');
  icon.className = 'bi ' + info.icon;
  icon.setAttribute('aria-hidden', 'true');
  const valueEl = document.createElement('span');
  chip.append(icon, valueEl);
  document.getElementById(control_container_id[kind]).appendChild(chip);
  s = control_state[kind][source] = { timestamps: [], lastSeen: 0, chip, valueEl, label: info.label };
  return s;
}

function onControlEvent(kind, message) {
  const now = Date.now();
  const s = getControlSource(kind, message.source || 'unknown');
  // Intervals use the event's own time (sources may deliver in bursts or correct for latency);
  // arrival time only drives the window, apnea and hiding. ns -> ms as a double loses < 1 us.
  s.timestamps.push({ event: Number(message.timestamp) / 1e6, arrival: now });
  s.lastSeen = now;
  renderControlSource(kind, s, now);
  s.chip.classList.add('bg-primary', 'text-white');
  s.chip.classList.remove('bg-gray-100', 'text-gray-800');
  setTimeout(() => {
    s.chip.classList.remove('bg-primary', 'text-white');
    s.chip.classList.add('bg-gray-100', 'text-gray-800');
  }, 300);
}

function renderControlSource(kind, s, now) {
  while (s.timestamps.length && now - s.timestamps[0].arrival > RATE_WINDOW_MS) s.timestamps.shift();
  if (now - s.lastSeen > HIDE_MS) { s.chip.style.display = 'none'; return; }
  let value = '--';
  if (kind === 'breath' && now - s.lastSeen >= APNEA_MS) {
    value = 'Apnea';
  } else if (s.timestamps.length >= 2) {
    const t = s.timestamps.map(e => e.event).sort((a, b) => a - b);
    const mean = (t[t.length - 1] - t[0]) / (t.length - 1);
    value = mean > 0 ? (60000 / mean).toFixed(1) : '--';
  }
  s.valueEl.innerText = value;
  s.chip.title = s.chip.ariaLabel = `${s.label}: ${value}`;
  s.chip.style.display = 'inline-flex';
}

// One shared timer refreshes decay, apnea and hiding for both cards
setInterval(() => {
  const now = Date.now();
  for (const kind in control_state)
    for (const source in control_state[kind]) renderControlSource(kind, control_state[kind][source], now);
}, 1000);

// Heart observations from the monitoring devices
let listenerHeartControl = new ROSLIB.Topic({
    ros : ros,
    name : '/heart_control',
    messageType : 'aims_msgs/msg/ControlEvent'
});

listenerHeartControl.subscribe(function(message) {
  onControlEvent('heart', message);
  document.getElementById("heart-beat").style.visibility = 'visible';
  setTimeout(hideHeartBeat, 500);
});

// Breath observations (button, monitoring devices, ...)
let listenerBreathControl = new ROSLIB.Topic({
    ros : ros,
    name : '/breath_control',
    messageType : 'aims_msgs/msg/ControlEvent'
});

// Raw annotation topic: captures persist this one; /breath_control feeds the UI only
let breathAnnotationPublisher = new ROSLIB.Topic({
    ros : ros,
    name : '/ui/breath_annotation',
    messageType : 'aims_msgs/msg/ControlEvent'
});

// Operator annotation: one event per exhale
let breath_count = 0;
breathBtn.addEventListener('click', () => {
  const event = { timestamp: Date.now() * 1000000, source: 'ui_button' };
  breathAnnotationPublisher.publish(event);
  listenerBreathControl.publish(event);
  document.getElementById('breath_count').innerText = ++breath_count;
});

listenerBreathControl.subscribe(function(message) {
  onControlEvent('breath', message);
  document.getElementById("lung-beat").style.visibility = 'visible';
  setTimeout(hideLungBeat, 500);
});

function hideHeartBeat() {
    var heartBeat = document.getElementById('heart-beat');
    heartBeat.style.visibility = 'hidden';
  }
function hideLungBeat() {
    var lungBeat = document.getElementById('lung-beat');
    lungBeat.style.visibility = 'hidden';
  }

// Like when publishing a topic, we first create a Topic object with details of the topic's name
// and message type. Note that we can call publish or subscribe on the same topic object.
let listenerBR = new ROSLIB.Topic({
  ros : ros,
  name : '/breath_estimate',
  messageType : 'custom_interfaces/msg/BreathEstimate'
});

// Callback, called whenever a new message is received on the topic.
listenerBR.subscribe(function(message) {
  //console.log('Received message on ' + listenerBR.name + ': ' + message);
  //var decoded = decodeMessage(message);
  var decoded = message;
  //console.log(message.apnea_detected);
  if (! receivedFirstMessage){
      receivedFirstMessage = true
      // Buffers are full once the first estimate arrives, with or without a subject
      document.getElementById('loading').style.display = 'none';
  }

  if(is_person){
    let brValue = document.getElementById('br_value');

    if (decoded.apnea_detected == 1){
      brValue.classList.add('apnea-value');
      brValue.classList.remove('normal-value');
      decoded.breath_rate = "Apnea";
    }else{
      brValue.classList.remove('apnea-value');
      brValue.classList.add('normal-value');
    }
    document.getElementById("br_value").innerHTML = decoded.breath_rate;
  }

  if (histogramChartActive)
      updateHistogram(decoded.breath_rate);
  if (signalChartActive)
      updateSignal(decoded.breath_rate);
  if (signalChartActive2)
      updateSignal2(decoded.breath_rate);
});

// Navigation tab control
function activateChart(chartType){
  switch (chartType) {
    case "nav-histogram-tab":
      histogramChartActive = true;
      heatmapChartActive = false;
      mmwaveHeatmapChartActive = false;
      break;
    case "nav-signal-tab":
      signalChartActive = true;
      heatmapChartActive = false;
      break;
    case "nav-signal-tab2":
      signalChartActive2 = true;
      heatmapChartActive = false;
      break;
    case "nav-heatmap-tab":
      heatmapChartActive = true;
      mmwaveHeatmapChartActive = false;
      break;
    case "nav-heatmap-mmw-tab":
      mmwaveHeatmapChartActive = true;
      break;
  }

}

let persistence_request_publisher = new ROSLIB.Topic({
  ros: ros,
  name: '/persistence_bridge/request',
  messageType: 'custom_interfaces/msg/PersistenceRequest'
});

const form = document.getElementById('metadata-form');
const form_btn = document.getElementById('btn-persistence');
form.addEventListener('submit', (event) => {
  event.preventDefault();

  console.log("Button pressed")
  if (form.btn_status.value === '0'){
    // The subject ID becomes part of the capture file name
    const subject_id = form.subject_id.value.trim();
    const subject_id_valid = /^[A-Za-z0-9_-]+$/.test(subject_id);
    document.getElementById('subject_id_error').style.display = subject_id_valid ? 'none' : 'block';
    if (!subject_id_valid) return;

    let request_message = new ROSLIB.Message({
      capture_name: form.capture_name.value,
      subject_id: subject_id,
      rx_nic_model: 'Intel 5300',
      tx_nic_model: 'Intel 5300',
      subject_position: form.subject_position.value,
      antenna_distance_cm: Number(form.antenna_distance_cm.value),
      duration_s: Number(form.duration_s.value)
    });
    
    persistence_request_publisher.publish(request_message);

    form_btn.innerText = 'Cancel'
    form_btn.value = '1'

    document.getElementById('progress-bar').setAttribute('max', form.duration_s.value);
    document.getElementById('progress_div').style.display = 'block';
  }
  // else {
  //   form_btn.innerText = 'Start Persistence'
  //   form_btn.value = '0'
  // }

});

let persistence_response_listener = new ROSLIB.Topic({
  ros: ros,
  name: 'persistence_bridge/response',
  messageType: 'std_msgs/msg/String'
});

persistence_response_listener.subscribe((message) => {
  form_btn.innerText = 'Start Persistence'
  form_btn.value = '0'
  document.getElementById('progress_div').style.display = 'none';
});

let persistence_feedback_listener = new ROSLIB.Topic({
  ros: ros,
  name: 'persistence_bridge/feedback',
  messageType: 'custom_interfaces/msg/PersistenceFeedback'
});

persistence_feedback_listener.subscribe((message) => {
  document.getElementById('progress-bar').setAttribute('value', message.elapsed_s);
  document.getElementById('progress-text').innerText = `${message.elapsed_s}/${document.getElementById('progress-bar').getAttribute('max')} s · ${message.csi_frames} CSI frames`;
});

// ===================
function searchStringInArray (str, strArray) {
  for (var j=0; j<strArray.length; j++) {
      if (strArray[j].match(str)) return j;
  }
  return -1;
}