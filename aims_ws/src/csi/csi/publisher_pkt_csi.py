from numpy import uint32
import rclpy
from rclpy.node import Node
import time, socket, sys, os

#from std_msgs.msg import String
import custom_interfaces.msg as PktCSI

sys.path.append(os.getenv('AIMS', '/app'))
try:
    from PicoscenesToolbox.picoscenes import Picoscenes
except ImportError as e:
    sys.exit(f'csi_publisher: cannot import the PicoScenes parser from $AIMS/PicoscenesToolbox ({e}). '
             'It is built into the ros2 Docker image; rebuild it with "docker compose build".')

localIP = os.getenv('CSI_UDP_HOST', '0.0.0.0')
localPort = int(os.getenv('CSI_UDP_PORT', '1025'))
bufferSize = 65535  # max UDP datagram, so large frames are never truncated
recvTimeout = 1.0  # seconds; keeps the executor responsive when no frames arrive

class PktCSIPublisher(Node):

    def __init__(self):
        super().__init__('pkt_csi_publisher')
        self._publisher = self.create_publisher(PktCSI.PktCSI, 'pktcsi', 10)
        timer_period = (1/100) # 1/(100 hz)
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.i = 0

        self.UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.UDPServerSocket.bind((localIP, localPort))
        self.UDPServerSocket.settimeout(recvTimeout)
        self.get_logger().info(f'Waiting for PicoScenes UDP frames on {localIP}:{localPort}')

    def timer_callback(self):
        try:
            frame_in_bytes = self.UDPServerSocket.recv(bufferSize)
        except socket.timeout:
            self.get_logger().warn(f'No PicoScenes UDP frames on {localIP}:{localPort} yet',
                                   throttle_duration_sec=10)
            return

        try:
            self.publish_frame(Picoscenes(frame_in_bytes))
        except Exception as e:
            # A malformed or incomplete frame must not kill the node; skip it.
            self.get_logger().error(f'Could not parse PicoScenes frame ({len(frame_in_bytes)} bytes): {e!r}',
                                    throttle_duration_sec=5)

    def publish_frame(self, frames):

        # ============ Frame ==============
        
        # RxSBasic
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

        # RxExtraInfo (can have empty fields since it's optional in the frame)
        rx_extra_info_structure = frames.raw[0].get("RxExtraInfo")

        pkt_rx_extra_info = PktCSI.PktRxExtraInfo()

        pkt_rx_extra_info.pktid = self.i
        #pkt_rx_extra_info.haslength = rx_extra_info_structure.get("haslength")
        #pkt_rx_extra_info.hasversion = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.hasmacaddr = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.hasmacaddr = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.haschansel = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.hasbmode = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.hasevm = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.hastxchainmask = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.hasrxchainmask = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.hastxpower = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.hascf = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.hastxtsf = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.haslasthwtxtsf = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.haschannelflags = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.hastxness = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.hastuningpolicy = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.haspllrate = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.haspllclksel = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.haspllrefdiv = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.hasagc = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.hasantennaselection = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.hassamplingrate = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.hascfo = rx_extra_info_structure.get("")
        #pkt_rx_extra_info.hassfo = rx_extra_info_structure.get("")
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

        # CSI Meta (part from 'CSI' structure of the frame)
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

        # CSI (rest of 'CSI' structure information)
        pkt_csi_signal = PktCSI.PktCSISignal()

        pkt_csi_signal.pktid = self.i
        pkt_csi_signal.csi_real = list(map(lambda x:x.real, csi_structure.get('CSI')))
        pkt_csi_signal.csi_imag = list(map(lambda x:x.imag, csi_structure.get('CSI')))
        pkt_csi_signal.amplitude = csi_structure.get("Mag")
        pkt_csi_signal.phase = csi_structure.get("Phase")
        
        #pkt_csi_signal.timestamp = time.time_ns()

        # TXEntraInfo (can have empty fields since it's optional in the frame)
        tx_extra_info_structure = frames.raw[0].get("TxExtraInfo")

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

        # ==========================
        # Complete package 
        pkt_csi = PktCSI.PktCSI()

        pkt_csi.pktid = self.i
        pkt_csi.rxsbasic = pkt_rx_basic
        pkt_csi.rxextrainfo = pkt_rx_extra_info
        pkt_csi.csimeta = pkt_csi_meta
        pkt_csi.csi = pkt_csi_signal
        pkt_csi.txextrainfo = pkt_tx_extra_info

        # ==========================
        self._publisher.publish(pkt_csi)
        #self.get_logger().info('Publishing pkt CSI: "%d"' % self.i)
        self.i += 1

def main(args=None):
    rclpy.init(args=args)

    minimal_publisher = PktCSIPublisher()

    rclpy.spin(minimal_publisher)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    minimal_publisher.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
