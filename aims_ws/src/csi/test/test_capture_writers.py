import csv
import json
import os
from types import SimpleNamespace as NS

from csi import capture_writers as cw
import numpy as np

REQUEST = {'capture_name': 'run 1', 'subject_id': 's/01',
           'rx_nic_model': 'AX210', 'tx_nic_model': 'AX210',
           'subject_position': 'sitting', 'antenna_distance_cm': 150,
           'duration_s': 5}


def csi_msg(pktid, length=4, index=(-1, 1)):
    basic = NS(**{name: 1 for name, _ in cw.RXSBASIC_FIELDS
                  if name != 'basic_numrx'}, numrx=2)
    return NS(pktid=pktid, rxsbasic=basic, rxextrainfo=NS(agc=30),
              csimeta=NS(numtones=2, numtx=1, numrx=2,
                         subcarrierindex=list(index)),
              csi=NS(csi_real=[1.0] * length, csi_imag=[2.0] * length))


def test_capture_dir_name_suffix_and_sanitize(tmp_path):
    first = cw.make_capture_dir(str(tmp_path), REQUEST, now=0)
    second = cw.make_capture_dir(str(tmp_path), REQUEST, now=0)
    name = 'run_1-s_01-AX210-AX210-sitting-150cm-19700101-000000Z'
    assert os.path.basename(first) == name
    assert os.path.basename(second) == name + '-2'


def test_dotted_field_and_explode():
    msg = NS(header=NS(stamp=NS(sec=7)), vals=[1, 2, 3], ok=True,
             raw=b'\x01\x02')
    assert cw.get_field(msg, 'header.stamp.sec') == 7
    assert cw.build_rows(msg, ['ok', 'raw'], 5) == [[5, 1, '1 2']]
    rows = cw.build_rows(msg, ['header.stamp.sec', 'vals'], 5, 'vals')
    assert rows == [[5, 7, 1], [5, 7, 2], [5, 7, 3]]


def test_csv_header_without_rows(tmp_path):
    writer = cw.CsvWriter(str(tmp_path), 'b', {'fields': ['data']})
    writer.close()
    with open(tmp_path / 'b.csv') as f:
        assert list(csv.reader(f)) == [['host_ns', 'data']]
    assert writer.rows == 0


def test_csi_parts_split_on_time_and_length(tmp_path):
    writer = cw.CsiPartWriter(str(tmp_path), 'csi', {})
    writer.write(csi_msg(1), 0)
    writer.write(csi_msg(2), 1)
    writer.write(csi_msg(3), cw.CSI_PART_NS)       # time boundary
    writer.write(csi_msg(4, length=6), cw.CSI_PART_NS + 1)  # L changes
    writer.close()
    assert writer.files == ['csi/part-0000.npz', 'csi/part-0001.npz',
                            'csi/part-0002.npz']
    assert writer.rows == 4
    part = np.load(tmp_path / 'csi' / 'part-0000.npz')
    assert part['csi'].dtype == np.complex64
    assert part['csi'].shape == (2, 4)
    assert part['csi'][0, 0] == 1 + 2j
    assert part['subcarrierindex'].dtype == np.int16
    assert part['host_ns'].dtype == np.int64
    assert part['pktid'].dtype == np.uint64
    assert part['rssi'].dtype == np.int8
    assert part['basic_numrx'][0] == 2
    assert np.load(tmp_path / 'csi' / 'part-0002.npz')['csi'].shape == (1, 6)


def test_meta_recording_then_complete(tmp_path):
    sources = {
        'csi': {'topic': '/pktcsi', 'type': 't/msg/C', 'writer': 'csi_npz'},
        'flag': {'topic': '/f', 'type': 't/msg/B', 'writer': 'csv',
                 'fields': ['data']},
    }
    capture = cw.Capture(str(tmp_path), REQUEST, sources, log=lambda m: None)
    capture.write_meta('recording')
    with open(os.path.join(capture.folder, 'meta.json')) as f:
        assert json.load(f)['status'] == 'recording'
    capture.write('csi', csi_msg(1), 1)
    capture.write('flag', NS(), 2)  # no .data: disables only this writer
    capture.close()
    with open(os.path.join(capture.folder, 'meta.json')) as f:
        meta = json.load(f)
    assert meta['status'] == 'complete'
    assert meta['end_ns'] is not None
    assert meta['sources']['csi']['rows'] == 1
    assert meta['sources']['flag']['error'].startswith('AttributeError')
