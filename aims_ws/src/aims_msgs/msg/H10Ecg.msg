# One Polar H10 ECG packet (130 Hz, about 73 samples). Published by devices/h10_bridge on /h10/ecg.
uint64 sensor_ns     # strap time of the last sample, ns since the Unix epoch (strap clock, drifts)
uint64 bridge_ns     # time the bridge received the packet, ns since the Unix epoch (bridge clock)
int32[] samples_uv   # ECG samples in microvolts, oldest first
