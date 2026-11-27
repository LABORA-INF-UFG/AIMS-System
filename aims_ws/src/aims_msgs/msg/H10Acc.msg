# One Polar H10 accelerometer packet. Published by devices/h10_bridge on /h10/acc.
uint64 sensor_ns     # strap time of the last sample, ns since the Unix epoch (strap clock, drifts)
uint64 bridge_ns     # time the bridge received the packet, ns since the Unix epoch (bridge clock)
uint16 sample_rate_hz  # configured rate: 25, 50, 100 or 200
uint8 range_g          # configured range: 2, 4 or 8
int16[] x_mg         # samples in milli-g, oldest first; x_mg, y_mg and z_mg have the same length
int16[] y_mg
int16[] z_mg
