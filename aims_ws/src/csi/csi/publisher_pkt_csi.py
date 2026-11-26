import struct
import numpy as np
import rclpy
from rclpy.node import Node
import time, socket, sys, os

import custom_interfaces.msg as PktCSI

sys.path.append(os.getenv('AIMS', '/app'))
try:
    from PicoscenesToolbox.picoscenes import Picoscenes
except ImportError as e:
    sys.exit(f'csi_publisher: cannot import the PicoScenes parser from $AIMS/PicoscenesToolbox ({e}). '
             'It is built into the ros2 Docker image; rebuild it with "docker compose build".')

localIP = os.getenv('CSI_UDP_HOST', '0.0.0.0')
localPort = int(os.getenv('CSI_UDP_PORT', '1025'))
bufferSize = 65535
recvTimeout = 1.0


def parse_mac_filter(mac_str: str):
    """Converte string MAC (ex: 'C4:23:60:76:36:03') em bytes (6 bytes) e lista de inteiros."""
    cleaned = mac_str.strip().replace(':', '').replace('-', '')
    if not cleaned:
        return None, None
    if len(cleaned) != 12:
        raise ValueError(f'CSI_MAC_FILTER inválido: "{mac_str}". Esperado 12 dígitos hexadecimais.')
    mac_bytes = bytes.fromhex(cleaned)
    return mac_bytes, list(mac_bytes)


class PktCSIPublisher(Node):

    def __init__(self):
        super().__init__('pkt_csi_publisher')
        self._publisher = self.create_publisher(PktCSI.PktCSI, 'pktcsi', 10)
        timer_period = (1 / 100)  # 100 Hz
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.i = 0

        raw_mac = os.getenv('CSI_MAC_FILTER', '')
        self.target_mac_bytes, self.target_mac_list = parse_mac_filter(raw_mac)

        self.UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.UDPServerSocket.bind((localIP, localPort))
        self.UDPServerSocket.settimeout(recvTimeout)

        filter_msg = f' (MAC filter: {raw_mac.strip()})' if self.target_mac_bytes else ' (no MAC filter)'
        self.get_logger().info(f'Waiting for PicoScenes UDP frames on {localIP}:{localPort}{filter_msg}')

    def timer_callback(self):
        try:
            frame_in_bytes = self.UDPServerSocket.recv(bufferSize)
        except socket.timeout:
            self.get_logger().warn(f'No PicoScenes UDP frames on {localIP}:{localPort} yet',
                                   throttle_duration_sec=10)
            return

        try:
            frames = Picoscenes(frame_in_bytes)
            if getattr(frames, 'raw', None) and len(frames.raw[0]) > 0:
                self.publish_iwl5300_frame(frames)
            else:
                self.publish_ax210_raw_bytes(frame_in_bytes)
        except Exception as e:
            self.get_logger().error(f'Could not parse PicoScenes frame ({len(frame_in_bytes)} bytes): {e!r}',
                                    throttle_duration_sec=5)

    def publish_ax210_raw_bytes(self, payload: bytes):
        # Filtro de MAC no cabeçalho 802.11 encapsulado no datagrama UDP (AX210)
        if self.target_mac_bytes is not None and self.target_mac_bytes not in payload:
            return

        csi_tag_idx = payload.find(b"CSI\x00")
        if csi_tag_idx == -1:
            return

        # Pula o cabeçalho do segmento CSI (48 bytes) para ler os pares I/Q int16
        data_start = csi_tag_idx + 48
        if data_start >= len(payload):
            return

        raw_csi_bytes = payload[data_start:]
        usable_len = (len(raw_csi_bytes) // 4) * 4
        if usable_len < 104 * 4:
            return

        iq_int16 = np.frombuffer(raw_csi_bytes[:usable_len], dtype=np.int16).astype(np.float64)
        csi_complex = iq_int16[0::2] + 1j * iq_int16[1::2]

        # Separa Antena 1 (0..52) e Antena 2 (52..104)
        rx1_raw = csi_complex[0:52]
        rx2_raw = csi_complex[52:104]

        if (np.max(np.abs(rx1_raw)) == 0 or np.max(np.abs(rx2_raw)) == 0 or
                not np.all(np.isfinite(rx1_raw)) or not np.all(np.isfinite(rx2_raw))):
            return

        # Preenche cada antena de 52 para 57 tons para alinhar exatamente com
        # phase1 = csi[:, :57] e phase2 = csi[:, 57:114] do BreathEstimation.py
        rx1_57 = np.pad(rx1_raw, (0, 5), mode='edge')
        rx2_57 = np.pad(rx2_raw, (0, 5), mode='edge')
        rx3_57 = rx1_57.copy()  # Terceira antena virtual (114..171)

        csi_chain = np.concatenate([rx1_57, rx2_57, rx3_57])  # Exatos 171 elementos

        now_ns = time.time_ns()

        pkt_rx_basic = PktCSI.PktRxBasic()
        pkt_rx_basic.pktid = self.i
        pkt_rx_basic.devicetype = 210
        pkt_rx_basic.timestamp = int(now_ns // 1000)
        pkt_rx_basic.systemns = int(now_ns)
        pkt_rx_basic.centerfreq = int(os.getenv('PICOSCENES_FREQ', '5680'))
        pkt_rx_basic.controlfreq = int(os.getenv('PICOSCENES_FREQ', '5680'))
        pkt_rx_basic.cbw = 20
        pkt_rx_basic.numsts = 1
        pkt_rx_basic.numrx = 3

        pkt_rx_extra_info = PktCSI.PktRxExtraInfo()
        pkt_rx_extra_info.pktid = self.i

        pkt_csi_meta = PktCSI.PktCSIMeta()
        pkt_csi_meta.pktid = self.i
        pkt_csi_meta.devicetype = 210
        pkt_csi_meta.cbw = 20
        pkt_csi_meta.carrierfreq = int(os.getenv('PICOSCENES_FREQ', '5680'))
        pkt_csi_meta.numtones = 57
        pkt_csi_meta.numtx = 1
        pkt_csi_meta.numrx = 3
        pkt_csi_meta.numcsi = 1
        pkt_csi_meta.subcarrierindex = list(range(-28, 29))

        pkt_csi_signal = PktCSI.PktCSISignal()
        pkt_csi_signal.pktid = self.i
        pkt_csi_signal.csi_real = [float(x.real) for x in csi_chain]
        pkt_csi_signal.csi_imag = [float(x.imag) for x in csi_chain]
        pkt_csi_signal.amplitude = [float(x) for x in np.abs(csi_chain)]
        pkt_csi_signal.phase = [float(x) for x in np.angle(csi_chain)]

        pkt_tx_extra_info = PktCSI.PktTxExtraInfo()
        pkt_tx_extra_info.pktid = self.i
        if self.target_mac_list is not None:
            pkt_tx_extra_info.macaddr_cur = self.target_mac_list

        pkt_csi = PktCSI.PktCSI()
        pkt_csi.pktid = self.i
        pkt_csi.rxsbasic = pkt_rx_basic
        pkt_csi.rxextrainfo = pkt_rx_extra_info
        pkt_csi.csimeta = pkt_csi_meta
        pkt_csi.csi = pkt_csi_signal
        pkt_csi.txextrainfo = pkt_tx_extra_info

        self._publisher.publish(pkt_csi)
        self.i += 1	

    def publish_ax210_raw_bytes__(self, payload: bytes):
        # Filtro de MAC no cabeçalho 802.11 encapsulado no datagrama UDP (AX210)
        if self.target_mac_bytes is not None and self.target_mac_bytes not in payload:
            return

        csi_tag_idx = payload.find(b"CSI\x00")
        if csi_tag_idx == -1:
            return

        data_start = csi_tag_idx + 28
        if data_start >= len(payload):
            return

        raw_csi_bytes = payload[data_start:]
        usable_len = (len(raw_csi_bytes) // 4) * 4
        if usable_len < 30 * 4:
            return

        iq_int16 = np.frombuffer(raw_csi_bytes[:usable_len], dtype=np.int16).astype(np.float64)
        csi_complex = iq_int16[0::2] + 1j * iq_int16[1::2]

        if csi_complex.size == 0 or np.max(np.abs(csi_complex)) == 0 or not np.all(np.isfinite(csi_complex)):
            return

        num_tones = min(len(csi_complex), 52)
        csi_chain = csi_complex[:num_tones]

        now_ns = time.time_ns()

        pkt_rx_basic = PktCSI.PktRxBasic()
        pkt_rx_basic.pktid = self.i
        pkt_rx_basic.devicetype = 210
        pkt_rx_basic.timestamp = int(now_ns // 1000)
        pkt_rx_basic.systemns = int(now_ns)
        pkt_rx_basic.centerfreq = int(os.getenv('PICOSCENES_FREQ', '5680'))
        pkt_rx_basic.controlfreq = int(os.getenv('PICOSCENES_FREQ', '5680'))
        pkt_rx_basic.cbw = 20
        pkt_rx_basic.numsts = 1
        pkt_rx_basic.numrx = 2

        pkt_rx_extra_info = PktCSI.PktRxExtraInfo()
        pkt_rx_extra_info.pktid = self.i

        pkt_csi_meta = PktCSI.PktCSIMeta()
        pkt_csi_meta.pktid = self.i
        pkt_csi_meta.devicetype = 210
        pkt_csi_meta.cbw = 20
        pkt_csi_meta.carrierfreq = int(os.getenv('PICOSCENES_FREQ', '5680'))
        pkt_csi_meta.numtones = num_tones
        pkt_csi_meta.numtx = 1
        pkt_csi_meta.numrx = 2
        pkt_csi_meta.numcsi = 1
        pkt_csi_meta.subcarrierindex = list(range(-num_tones // 2, num_tones // 2))

        pkt_csi_signal = PktCSI.PktCSISignal()
        pkt_csi_signal.pktid = self.i
        pkt_csi_signal.csi_real = [float(x.real) for x in csi_chain]
        pkt_csi_signal.csi_imag = [float(x.imag) for x in csi_chain]
        pkt_csi_signal.amplitude = [float(x) for x in np.abs(csi_chain)]
        pkt_csi_signal.phase = [float(x) for x in np.angle(csi_chain)]

        pkt_tx_extra_info = PktCSI.PktTxExtraInfo()
        pkt_tx_extra_info.pktid = self.i
        if self.target_mac_list is not None:
            pkt_tx_extra_info.macaddr_cur = self.target_mac_list

        pkt_csi = PktCSI.PktCSI()
        pkt_csi.pktid = self.i
        pkt_csi.rxsbasic = pkt_rx_basic
        pkt_csi.rxextrainfo = pkt_rx_extra_info
        pkt_csi.csimeta = pkt_csi_meta
        pkt_csi.csi = pkt_csi_signal
        pkt_csi.txextrainfo = pkt_tx_extra_info

        self._publisher.publish(pkt_csi)
        self.i += 1

    def publish_iwl5300_frame(self, frames):
        rx_extra_info_structure = frames.raw[0].get("RxExtraInfo") or {}
        tx_extra_info_structure = frames.raw[0].get("TxExtraInfo") or {}

        # Filtro de MAC para IWL5300 (verifica MAC do transmissor ou receptor)
        if self.target_mac_list is not None:
            tx_mac = list(tx_extra_info_structure.get("macaddr_cur") or [])
            rx_mac = list(rx_extra_info_structure.get("macaddr_cur") or [])
            if self.target_mac_list != tx_mac and self.target_mac_list != rx_mac:
                return

        rx_basic_structure = frames.raw[0].get("RxSBasic")

        pkt_rx_basic = PktCSI.PktRxBasic()
        pkt_rx_basic.pktid = self.i
        pkt_rx_basic.devicetype = rx_basic_structure.get("deviceType")
        pkt_rx_basic.timestamp = rx_basic_structure.get("timestamp")
        pkt_rx_basic.systemns = rx_basic_structure.get("systemns")
        pkt_rx_basic.centerfreq = rx_basic_structure.get("centerFreq")
        pkt_rx_basic.controlfreq = rx_basic_structure.get("controlFreq")
        pkt_rx_basic.cbw = rx_basic_structure.get("CBW")
        pkt_rx_basic.packetformat = rx_basic_structure.get("packetFormat")
        pkt_rx_basic.packetcbw = rx_basic_structure.get("packetCBW")
        pkt_rx_basic.gi = rx_basic_structure.get("GI")
        pkt_rx_basic.mcs = rx_basic_structure.get("MCS")
        pkt_rx_basic.numsts = rx_basic_structure.get("numSTS")
        pkt_rx_basic.numess = rx_basic_structure.get("numESS")
        pkt_rx_basic.numrx = rx_basic_structure.get("numRx")
        pkt_rx_basic.noisefloor = rx_basic_structure.get("noiseFloor")
        pkt_rx_basic.rssi = rx_basic_structure.get("rssi")
        pkt_rx_basic.rssi1 = rx_basic_structure.get("rssi1")
        pkt_rx_basic.rssi2 = rx_basic_structure.get("rssi2")
        pkt_rx_basic.rssi3 = rx_basic_structure.get("rssi3")

        pkt_rx_extra_info = PktCSI.PktRxExtraInfo()
        pkt_rx_extra_info.pktid = self.i
        pkt_rx_extra_info.length = rx_extra_info_structure.get("length")
        pkt_rx_extra_info.version = rx_extra_info_structure.get("version")
        pkt_rx_extra_info.macaddr_cur = rx_extra_info_structure.get("macaddr_cur")
        pkt_rx_extra_info.macaddr_rom = rx_extra_info_structure.get("macaddr_rom")
        pkt_rx_extra_info.tx_chainmask = rx_extra_info_structure.get("tx_chainmask")
        pkt_rx_extra_info.rx_chainmask = rx_extra_info_structure.get("rx_chainmask")
        pkt_rx_extra_info.txpower = rx_extra_info_structure.get("txpower")
        pkt_rx_extra_info.channel_flags = rx_extra_info_structure.get("channel_flags")
        pkt_rx_extra_info.agc = rx_extra_info_structure.get("agc")
        pkt_rx_extra_info.ant_sel = rx_extra_info_structure.get("ant_sel")

        csi_structure = frames.raw[0].get("CSI")

        pkt_csi_meta = PktCSI.PktCSIMeta()
        pkt_csi_meta.pktid = self.i
        pkt_csi_meta.devicetype = csi_structure.get("DeviceType")
        pkt_csi_meta.packetformat = csi_structure.get("PacketFormat")
        pkt_csi_meta.firmwareversion = csi_structure.get("FirmwareVersion")
        pkt_csi_meta.cbw = csi_structure.get("CBW")
        pkt_csi_meta.carrierfreq = csi_structure.get("CarrierFreq")
        pkt_csi_meta.samplingrate = csi_structure.get("SamplingRate")
        pkt_csi_meta.subcarrierbandwidth = csi_structure.get("SubcarrierBandwidth")
        pkt_csi_meta.numtones = csi_structure.get("numTones")
        pkt_csi_meta.numtx = csi_structure.get("numTx")
        pkt_csi_meta.numrx = csi_structure.get("numRx")
        pkt_csi_meta.numess = csi_structure.get("numESS")
        pkt_csi_meta.numcsi = csi_structure.get("numCSI")
        pkt_csi_meta.ant_sel = csi_structure.get("ant_sel")
        pkt_csi_meta.subcarrierindex = csi_structure.get("SubcarrierIndex")

        pkt_csi_signal = PktCSI.PktCSISignal()
        pkt_csi_signal.pktid = self.i
        pkt_csi_signal.csi_real = list(map(lambda x: x.real, csi_structure.get('CSI')))
        pkt_csi_signal.csi_imag = list(map(lambda x: x.imag, csi_structure.get('CSI')))
        pkt_csi_signal.amplitude = csi_structure.get("Mag")
        pkt_csi_signal.phase = csi_structure.get("Phase")

        pkt_tx_extra_info = PktCSI.PktTxExtraInfo()
        pkt_tx_extra_info.pktid = self.i
        pkt_tx_extra_info.length = tx_extra_info_structure.get("length")
        pkt_tx_extra_info.version = tx_extra_info_structure.get("version")
        pkt_tx_extra_info.macaddr_cur = tx_extra_info_structure.get("macaddr_cur")
        pkt_tx_extra_info.macaddr_rom = tx_extra_info_structure.get("macaddr_rom")
        pkt_tx_extra_info.tx_chainmask = tx_extra_info_structure.get("tx_chainmask")
        pkt_tx_extra_info.rx_chainmask = tx_extra_info_structure.get("rx_chainmask")
        pkt_tx_extra_info.txpower = tx_extra_info_structure.get("txpower")
        pkt_tx_extra_info.cf = tx_extra_info_structure.get("cf")
        pkt_tx_extra_info.sf = tx_extra_info_structure.get("sf")

        pkt_csi = PktCSI.PktCSI()
        pkt_csi.pktid = self.i
        pkt_csi.rxsbasic = pkt_rx_basic
        pkt_csi.rxextrainfo = pkt_rx_extra_info
        pkt_csi.csimeta = pkt_csi_meta
        pkt_csi.csi = pkt_csi_signal
        pkt_csi.txextrainfo = pkt_tx_extra_info

        self._publisher.publish(pkt_csi)
        self.i += 1


def main(args=None):
    rclpy.init(args=args)
    minimal_publisher = PktCSIPublisher()
    rclpy.spin(minimal_publisher)
    minimal_publisher.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
