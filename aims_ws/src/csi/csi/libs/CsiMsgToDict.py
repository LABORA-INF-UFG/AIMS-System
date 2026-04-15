from custom_interfaces.msg import PktCSI

def CsiMsgToDict(msg: PktCSI):
    d: dict = {}

    d['pktid'] = msg.pktid
    d['RxSBasic'] = {
        'pktid': msg.rxsbasic.pktid,
        'deviceType': msg.rxsbasic.devicetype,
        'timestamp': msg.rxsbasic.timestamp,
        'systemns': msg.rxsbasic.systemns,
        'centerFreq': msg.rxsbasic.centerfreq,
        'controlFreq': msg.rxsbasic.controlfreq,
        'CBW': msg.rxsbasic.cbw,
        'packetFormat': msg.rxsbasic.packetformat,
        'packetCBW': msg.rxsbasic.packetcbw,
        'GI': msg.rxsbasic.gi,
        'MCS': msg.rxsbasic.mcs,
        'numSTS': msg.rxsbasic.numsts,
        'numESS': msg.rxsbasic.numess,
        'numRx': msg.rxsbasic.numrx,
        'noiseFloor': msg.rxsbasic.noisefloor,
        'rssi': msg.rxsbasic.rssi,
        'rssi1': msg.rxsbasic.rssi1,
        'rssi2': msg.rxsbasic.rssi2,
        'rssi3': msg.rxsbasic.rssi3
    }
    d['RxExtraInfo'] = {
        'pktid': msg.rxextrainfo.pktid,
        'length': msg.rxextrainfo.length,
        'version': msg.rxextrainfo.version,
        'macaddr_cur': msg.rxextrainfo.macaddr_cur.tolist(),
        'macaddr_rom': msg.rxextrainfo.macaddr_rom.tolist(),
        'tx_chainmask': msg.rxextrainfo.tx_chainmask,
        'rx_chainmask': msg.rxextrainfo.rx_chainmask,
        'txpower': msg.rxextrainfo.txpower,
        'channel_flags': msg.rxextrainfo.channel_flags,
        'agc': msg.rxextrainfo.agc,
        'ant_sel': msg.rxextrainfo.ant_sel.tolist()
    }
    d['CSI'] = {
        'pktid': msg.csimeta.pktid,
        'DeviceType': msg.csimeta.devicetype,
        'PacketFormat': msg.csimeta.packetformat,
        'FirmwareVersion': msg.csimeta.firmwareversion,
        'CBW': msg.csimeta.cbw,
        'CarrierFreq': msg.csimeta.carrierfreq,
        'SamplingRate': msg.csimeta.samplingrate,
        'SubcarrierBandwidth': msg.csimeta.subcarrierbandwidth,
        'numTones': msg.csimeta.numtones,
        'numTx': msg.csimeta.numtx,
        'numRx': msg.csimeta.numrx,
        'numESS': msg.csimeta.numess,
        'numCSI': msg.csimeta.numcsi,
        'ant_sel': msg.csimeta.ant_sel,
        'SubcarrierIndex': msg.csimeta.subcarrierindex.tolist(),
        'csi_real': msg.csi.csi_real.tolist(),
        'csi_imag': msg.csi.csi_imag.tolist(),
        'Mag': msg.csi.amplitude.tolist(),
        'Phase': msg.csi.phase.tolist()
    }
    d['TxExtraInfo'] = {
        'pktid': msg.txextrainfo.pktid,
        'length': msg.txextrainfo.length,
        'version': msg.txextrainfo.version,
        'macaddr_cur': msg.txextrainfo.macaddr_cur.tolist(),
        'macaddr_rom': msg.txextrainfo.macaddr_rom.tolist(),
        'tx_chainmask': msg.txextrainfo.tx_chainmask,
        'rx_chainmask': msg.txextrainfo.rx_chainmask,
        'txpower': msg.txextrainfo.txpower,
        'cf': msg.txextrainfo.cf,
        'sf': msg.txextrainfo.sf
    }

    return d