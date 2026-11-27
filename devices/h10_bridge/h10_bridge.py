"""Polar H10 -> ROS 2 bridge. Reads the strap over BLE (bleak + bleakheart) and publishes
to rosbridge with roslibpy. Not a ROS node: plain Python. See README.md."""
import argparse
import asyncio
import json
import logging
import os
import time
from urllib.parse import urlparse

log = logging.getLogger("h10_bridge")
BEAT_GAP_NS = 2_000_000_000  # re-anchor the beat clock when it drifts more than this from the host


# ---- pure functions (unit tested) -------------------------------------------------------------

def beat_times(last_beat, rr_ms, bridge_ns):
    """Cumulative beat times (ns) for one HR packet, plus the new last_beat.

    Consecutive beats are exactly the RR values apart. If there is no previous beat or the
    running clock is more than 2 s away from the packet time, the last beat is anchored at bridge_ns.
    """
    total = sum(rr_ms) * 1_000_000
    if last_beat is None or abs(last_beat + total - bridge_ns) > BEAT_GAP_NS:
        last_beat = bridge_ns - total
    times = []
    for rr in rr_ms:
        last_beat += rr * 1_000_000
        times.append(last_beat)
    return times, last_beat


def to_messages(kind, sensor_ns, data, bridge_ns, acc_rate, acc_range, last_beat):
    """One strap packet -> ([(topic, msg dict), ...], new last_beat)."""
    if kind == "ECG":
        return [("/h10/ecg", {"sensor_ns": sensor_ns, "bridge_ns": bridge_ns,
                              "samples_uv": [int(v) for v in data]})], last_beat
    if kind == "ACC":
        return [("/h10/acc", {"sensor_ns": sensor_ns, "bridge_ns": bridge_ns,
                              "sample_rate_hz": acc_rate, "range_g": acc_range,
                              "x_mg": [int(s[0]) for s in data],
                              "y_mg": [int(s[1]) for s in data],
                              "z_mg": [int(s[2]) for s in data]})], last_beat
    if kind == "HR":
        bpm, rr = data
        rr = [int(r) for r in rr]
        out = [("/h10/hr", {"bridge_ns": bridge_ns, "bpm": int(bpm), "rr_ms": rr})]
        times, last_beat = beat_times(last_beat, rr, bridge_ns)
        out += [("/heart_control", {"timestamp": t, "source": "h10"}) for t in times]
        return out, last_beat
    raise ValueError(f"unknown packet kind {kind!r}")


def replay_schedule(rec, rec_start_ns, replay_start_ns):
    """Recorded packet -> (delay_s after replay start, shifted sensor_ns)."""
    return (rec["host_ns"] - rec_start_ns) / 1e9, rec["sensor_ns"] + (replay_start_ns - rec_start_ns)


# ---- output (same path for live and replay) ---------------------------------------------------

class Bridge:
    def __init__(self, ros, dry_run, acc_rate, acc_range):
        self.ros, self.dry_run = ros, dry_run
        self.acc_rate, self.acc_range = acc_rate, acc_range
        self.last_beat = None
        self.counts = {}
        self.dropped = 0
        self.topics = {}
        if ros:
            import roslibpy
            for name, typ in (("/h10/ecg", "aims_msgs/msg/H10Ecg"), ("/h10/acc", "aims_msgs/msg/H10Acc"),
                              ("/h10/hr", "aims_msgs/msg/H10Hr"),
                              ("/heart_control", "aims_msgs/msg/ControlEvent")):
                t = roslibpy.Topic(ros, name, typ)
                t.advertise()  # publish() re-advertises after a reconnect
                self.topics[name] = t

    def handle(self, kind, sensor_ns, data):
        msgs, self.last_beat = to_messages(kind, sensor_ns, data, time.time_ns(),
                                           self.acc_rate, self.acc_range, self.last_beat)
        self.counts[kind] = self.counts.get(kind, 0) + 1
        for topic, msg in msgs:
            if self.dry_run:
                n = {k: len(v) if isinstance(v, list) else v for k, v in msg.items()}
                print(topic, n, flush=True)
            elif self.ros.is_connected:
                import roslibpy
                self.topics[topic].publish(roslibpy.Message(msg))
            else:
                self.dropped += 1  # rosbridge down: drop, do not queue

    async def status(self):
        while True:
            await asyncio.sleep(10)
            log.info("packets %s dropped %d", self.counts, self.dropped)


# ---- sources ----------------------------------------------------------------------------------

async def replay(bridge, path, loop):
    with open(path, encoding="utf-8") as f:
        header = json.loads(f.readline())
        recs = [json.loads(line) for line in f if line.strip()]
    rec_start = header["start_host_ns"]
    while True:
        replay_start = time.time_ns()
        t0 = time.monotonic()
        for rec in recs:
            delay, sensor_ns = replay_schedule(rec, rec_start, replay_start)
            await asyncio.sleep(max(0, delay - (time.monotonic() - t0)))
            bridge.handle(rec["kind"], sensor_ns, rec["data"])
        if not loop:
            return


async def live(bridge, address):
    from bleak import BleakClient, BleakScanner
    from bleakheart import HeartRate, PolarMeasurementData

    async def pump(q):
        while True:
            kind, sensor_ns, data, *_ = await q.get()
            bridge.handle(kind, sensor_ns, data)

    backoff = 2
    while True:
        tasks, client, pmd = [], None, None
        try:
            if address:
                dev = await BleakScanner.find_device_by_address(address, timeout=20)
            else:
                dev = await BleakScanner.find_device_by_filter(
                    lambda d, adv: "Polar H10" in (d.name or adv.local_name or ""), timeout=20)
            if dev is None:
                raise RuntimeError("H10 not found")
            gone = asyncio.Event()
            client = BleakClient(dev, timeout=30, disconnected_callback=lambda _c: gone.set())
            await client.connect()
            log.info("connected to %s (%s)", dev.name, dev.address)
            backoff = 2
            hrq, ecgq, accq = asyncio.Queue(), asyncio.Queue(), asyncio.Queue()
            hr = HeartRate(client, queue=hrq, instant_rate=False, unpack=False)
            pmd = PolarMeasurementData(client, ecg_queue=ecgq, acc_queue=accq)
            tasks = [asyncio.create_task(pump(q)) for q in (hrq, ecgq, accq)]
            await hr.start_notify()
            await pmd.start_streaming("ECG")
            await pmd.start_streaming("ACC", SAMPLE_RATE=bridge.acc_rate, RANGE=bridge.acc_range, RESOLUTION=16)
            log.info("streaming (ECG/ACC can take ~30 s to deliver the first packet)")
            await gone.wait()
            log.warning("BLE disconnected")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning("BLE error: %s: %s", type(e).__name__, e)
        finally:
            for t in tasks:
                t.cancel()
            if client and client.is_connected:
                for m in ("ECG", "ACC"):
                    try:
                        await pmd.stop_streaming(m)
                    except Exception:
                        pass
                try:
                    await client.disconnect()
                except Exception:
                    pass
        log.info("reconnecting in %d s", backoff)
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 30)


# ---- main -------------------------------------------------------------------------------------

def parse_args(argv=None):
    env = os.environ.get
    p = argparse.ArgumentParser(description="Polar H10 BLE -> rosbridge publisher")
    p.add_argument("--address", default=env("H10_ADDRESS"), help="BLE address (default: scan for 'Polar H10')")
    p.add_argument("--rosbridge", default=env("H10_ROSBRIDGE", "ws://localhost:9090"))
    p.add_argument("--acc-rate", type=int, default=int(env("H10_ACC_RATE", 200)), choices=(25, 50, 100, 200))
    p.add_argument("--acc-range", type=int, default=int(env("H10_ACC_RANGE", 8)), choices=(2, 4, 8))
    p.add_argument("--replay", default=env("H10_REPLAY"), metavar="PATH", help="replay a JSONL recording instead of BLE")
    p.add_argument("--loop", action="store_true", default=env("H10_LOOP", "") not in ("", "0"),
                   help="repeat the replay")
    p.add_argument("--dry-run", action="store_true", default=env("H10_DRY_RUN", "") not in ("", "0"),
                   help="print messages instead of publishing")
    return p.parse_args(argv)


async def run(args, bridge):
    src = replay(bridge, args.replay, args.loop) if args.replay else live(bridge, args.address)
    status = asyncio.create_task(bridge.status())
    try:
        await src
    finally:
        status.cancel()


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ros = None
    if not args.dry_run:
        import roslibpy
        u = urlparse(args.rosbridge)
        ros = roslibpy.Ros(u.hostname, u.port or 9090, is_secure=u.scheme == "wss")
        try:
            ros.run()
        except roslibpy.core.RosTimeoutError:  # the client keeps retrying in its thread
            log.warning("rosbridge %s not reachable, retrying in background", args.rosbridge)
    bridge = Bridge(ros, args.dry_run, args.acc_rate, args.acc_range)
    try:
        asyncio.run(run(args, bridge))
    except KeyboardInterrupt:
        log.info("stopped")
    finally:
        if ros:
            ros.terminate()


if __name__ == "__main__":
    main()
