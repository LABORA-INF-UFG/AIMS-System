from h10_bridge import beat_times, replay_schedule, to_messages

NS = 1_000_000


def test_first_packet_anchors_last_beat_at_bridge_ns():
    times, last = beat_times(None, [800, 900], 10_000 * NS)
    assert last == 10_000 * NS
    assert times == [9_100 * NS, 10_000 * NS]


def test_continuation_keeps_exact_rr_spacing():
    t1, last = beat_times(None, [800, 900], 10_000 * NS)
    t2, last = beat_times(last, [850, 870], 11_700 * NS)  # 30 ms off the running clock
    assert t2 == [t1[-1] + 850 * NS, t1[-1] + 1_720 * NS]
    assert last == t2[-1]


def test_reanchor_after_gap():
    _, last = beat_times(None, [800], 10_000 * NS)
    times, last = beat_times(last, [800], 20_000 * NS)  # 9.2 s late
    assert last == 20_000 * NS and times == [20_000 * NS]


def test_empty_rr_keeps_state_and_emits_nothing():
    _, last = beat_times(None, [800], 10_000 * NS)
    assert beat_times(last, [], 10_500 * NS) == ([], last)
    assert beat_times(None, [], 10_500 * NS) == ([], 10_500 * NS)  # anchors at bridge_ns


def test_ecg_message():
    out, last = to_messages("ECG", 5, [1, -2, 3], 9, 200, 8, None)
    assert out == [("/h10/ecg", {"sensor_ns": 5, "bridge_ns": 9, "samples_uv": [1, -2, 3]})]
    assert last is None


def test_acc_message():
    out, _ = to_messages("ACC", 5, [(1, 2, 3), (4, 5, 6)], 9, 100, 4, None)
    assert out == [("/h10/acc", {"sensor_ns": 5, "bridge_ns": 9, "sample_rate_hz": 100, "range_g": 4,
                                 "x_mg": [1, 4], "y_mg": [2, 5], "z_mg": [3, 6]})]


def test_hr_message_and_heart_control_per_rr():
    out, last = to_messages("HR", 5, [74, [851, 838]], 10_000 * NS, 200, 8, None)
    assert out[0] == ("/h10/hr", {"bridge_ns": 10_000 * NS, "bpm": 74, "rr_ms": [851, 838]})
    assert out[1:] == [("/heart_control", {"timestamp": 10_000 * NS - 838 * NS, "source": "h10"}),
                       ("/heart_control", {"timestamp": 10_000 * NS, "source": "h10"})]
    assert last == 10_000 * NS


def test_hr_without_rr_only_hr_topic():
    out, _ = to_messages("HR", 5, [74, []], 1, 200, 8, None)
    assert [t for t, _ in out] == ["/h10/hr"]


def test_replay_schedule_shifts_sensor_ns_and_keeps_relative_delay():
    rec = {"host_ns": 1_000 * NS + 2_500 * NS, "sensor_ns": 1_000 * NS + 2_400 * NS}
    delay, sensor = replay_schedule(rec, 1_000 * NS, 50_000 * NS)
    assert delay == 2.5
    assert sensor == 50_000 * NS + 2_400 * NS  # sensor offset to host preserved, moved to now
