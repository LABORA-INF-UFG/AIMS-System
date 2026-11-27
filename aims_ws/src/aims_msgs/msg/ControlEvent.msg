# One ground-truth event (a breath or a heartbeat) for the dashboard.
# Published on /breath_control and /heart_control. Not persisted: captures store each source's raw topics.
uint64 timestamp   # time of the event, ns since the Unix epoch
string source      # producer id, e.g. ui_button, h10, nk, mock
