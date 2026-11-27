# One Polar H10 heart rate notification (about 1 per second). Published by devices/h10_bridge on /h10/hr.
uint64 bridge_ns     # time the bridge received the notification, ns since the Unix epoch (bridge clock)
uint16 bpm           # heart rate computed by the strap
uint16[] rr_ms       # RR intervals ended since the previous notification, ms, oldest first (may be empty)
