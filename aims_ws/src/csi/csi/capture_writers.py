"""ROS-independent capture logic: sources config, folder naming, writers, meta.

Kept free of rclpy so it can be unit tested with plain fake objects.
"""

import csv
import json
import os
import re
import threading
import time

import numpy as np
import yaml

FORMAT_VERSION = 1
CSI_PART_NS = 10 * 10**9

# Scalar fields of PktRxBasic with their msg dtypes. rxsbasic.pktid is the
# top-level pktid and rxsbasic.numrx is stored as basic_numrx, because the
# part already has pktid and numrx (from csimeta).
RXSBASIC_FIELDS = (
    ('devicetype', np.uint16), ('timestamp', np.uint64),
    ('systemns', np.uint64), ('centerfreq', np.int16),
    ('controlfreq', np.int16), ('cbw', np.uint16),
    ('packetformat', np.uint8), ('packetcbw', np.uint16),
    ('gi', np.uint16), ('mcs', np.uint8), ('numsts', np.uint8),
    ('numess', np.uint8), ('basic_numrx', np.uint8),
    ('noisefloor', np.int8), ('rssi', np.int8), ('rssi1', np.int8),
    ('rssi2', np.int8), ('rssi3', np.int8),
)
CSI_SCALARS = (
    ('host_ns', np.int64), ('pktid', np.uint64),
) + RXSBASIC_FIELDS + (
    ('agc', np.uint8), ('numtones', np.uint16),
    ('numtx', np.uint8), ('numrx', np.uint8),
)


def safe(value):
    """Keep only characters valid in file names (also on Windows mounts)."""
    return re.sub(r'[^A-Za-z0-9_-]', '_', str(value))


def match_parent_owner(path):
    """Chown path to its parent dir's owner (the container runs as root)."""
    try:
        st = os.stat(os.path.dirname(os.path.abspath(path)))
        os.chown(path, st.st_uid, st.st_gid)
    except (OSError, AttributeError):  # AttributeError: no os.chown on Windows
        pass


def load_sources(path):
    """Read and validate the sources YAML; return {name: config}."""
    with open(path) as f:
        sources = (yaml.safe_load(f) or {}).get('sources')
    if not isinstance(sources, dict) or not sources:
        raise ValueError(f'{path}: no sources defined')
    for name, cfg in sources.items():
        where = f'{path}: source {name!r}'
        if safe(name) != name:
            raise ValueError(f'{where}: name must match [A-Za-z0-9_-]+')
        if not isinstance(cfg, dict):
            raise ValueError(f'{where}: must be a mapping')
        for key in ('topic', 'type'):
            if not isinstance(cfg.get(key), str):
                raise ValueError(f'{where}: missing {key}')
        writer = cfg.setdefault('writer', 'csv')
        if writer not in WRITERS:
            raise ValueError(f'{where}: unknown writer {writer!r}')
        fields = cfg.get('fields')
        if writer == 'csv' and (not isinstance(fields, list) or not fields):
            raise ValueError(f'{where}: csv writer needs a fields list')
        explode = cfg.get('explode')
        if isinstance(explode, str):
            explode = cfg['explode'] = [explode]
        if explode is not None and (
                not isinstance(explode, list) or not explode
                or any(e not in (fields or []) for e in explode)):
            raise ValueError(f'{where}: explode must be one or more of fields')
        if cfg.get('qos') not in (None, 'latched'):
            raise ValueError(f'{where}: qos must be latched or absent')
    return sources


def make_capture_dir(root, request, now=None):
    """Create root/captures/<request parts>-<UTC stamp>Z[-N] and return it."""
    captures = os.path.join(root, 'captures')
    os.makedirs(captures, exist_ok=True)
    parts = [request['capture_name'], request['subject_id'],
             request['rx_nic_model'], request['tx_nic_model'],
             request['subject_position'],
             f"{request['antenna_distance_cm']}cm"]
    stamp = time.strftime('%Y%m%d-%H%M%S', time.gmtime(now))
    base = os.path.join(
        captures, '-'.join(safe(p) for p in parts) + f'-{stamp}Z')
    path, n = base, 1
    while True:
        try:
            os.mkdir(path)
            break
        except FileExistsError:
            n += 1
            path = f'{base}-{n}'
    match_parent_owner(path)
    return path


def get_field(obj, path):
    """Return obj.a.b.c for path 'a.b.c'."""
    for part in path.split('.'):
        obj = getattr(obj, part)
    return obj


def to_cell(value):
    """Format a CSV cell: bool as 0/1, arrays/bytes space-separated."""
    if isinstance(value, (bool, np.bool_)):
        return int(value)
    if isinstance(value, str):
        return value
    if hasattr(value, '__iter__'):
        return ' '.join(str(to_cell(v)) for v in value)
    return value


def build_rows(msg, fields, host_ns, explode=None):
    """Build rows for one message.

    explode: a field name or a list of same-length array fields; gives one
    row per element, the other fields repeated.
    """
    values = [get_field(msg, f) for f in fields]
    if explode is None:
        return [[host_ns] + [to_cell(v) for v in values]]
    if isinstance(explode, str):
        explode = [explode]
    idx = [fields.index(e) for e in explode]
    if len({len(values[i]) for i in idx}) > 1:
        raise ValueError(f'explode fields {explode} have different lengths')
    rows = []
    for k in range(len(values[idx[0]])):
        rows.append([host_ns] + [to_cell(v[k] if j in idx else v)
                                 for j, v in enumerate(values)])
    return rows


class CsvWriter:
    """<name>.csv with header host_ns,<fields>; flushed on every message."""

    def __init__(self, folder, name, cfg):
        self.fields = cfg['fields']
        self.explode = cfg.get('explode')
        self.files = [name + '.csv']
        self.rows = 0
        path = os.path.join(folder, self.files[0])
        self._file = open(path, 'w', newline='', encoding='utf-8')
        match_parent_owner(path)
        self._csv = csv.writer(self._file)
        self._csv.writerow(['host_ns'] + self.fields)
        self._file.flush()

    def write(self, msg, host_ns):
        rows = build_rows(msg, self.fields, host_ns, self.explode)
        self._csv.writerows(rows)
        self._file.flush()
        self.rows += len(rows)

    def close(self):
        self._file.close()


def csi_frame(msg):
    """Extract plain values of one PktCSI message for CsiPartWriter.add."""
    basic = msg.rxsbasic
    frame = {name: getattr(basic, 'numrx' if name == 'basic_numrx' else name)
             for name, _ in RXSBASIC_FIELDS}
    frame.update(
        pktid=msg.pktid,
        agc=msg.rxextrainfo.agc,
        numtones=msg.csimeta.numtones,
        numtx=msg.csimeta.numtx,
        numrx=msg.csimeta.numrx,
        csi=(np.asarray(msg.csi.csi_real, np.float64)
             + 1j * np.asarray(msg.csi.csi_imag, np.float64)),
        subcarrierindex=msg.csimeta.subcarrierindex,
    )
    return frame


class CsiPartWriter:
    """Buffers CSI frames into <name>/part-NNNN.npz, one per ~10 s host time.

    A part also closes early when the CSI length or the subcarrier index
    changes, so every part holds one rectangular csi array.
    """

    def __init__(self, folder, name, cfg):
        self.name = name
        self.folder = os.path.join(folder, name)
        os.makedirs(self.folder, exist_ok=True)
        match_parent_owner(self.folder)
        self.files = []
        self.rows = 0
        self._parts = 0
        self._reset()

    def _reset(self):
        self._buf = {name: [] for name, _ in CSI_SCALARS}
        self._csi = []
        self._index = None
        self._start_ns = None

    def write(self, msg, host_ns):
        self.add(host_ns, **csi_frame(msg))

    def add(self, host_ns, csi, subcarrierindex, **scalars):
        csi = np.asarray(csi, np.complex64)
        index = np.asarray(subcarrierindex, np.int16)
        scalars['host_ns'] = host_ns
        # Read every value before touching the buffer, so a bad frame
        # cannot leave the part's arrays with different lengths.
        values = [scalars[name] for name, _ in CSI_SCALARS]
        if self._csi and (
                host_ns - self._start_ns >= CSI_PART_NS
                or csi.shape != self._csi[0].shape
                or not np.array_equal(index, self._index)):
            self.flush()
        if not self._csi:
            self._start_ns, self._index = host_ns, index
        for (name, _), value in zip(CSI_SCALARS, values):
            self._buf[name].append(value)
        self._csi.append(csi)
        self.rows += 1

    def flush(self):
        """Write the current part, if any, and start an empty one."""
        if not self._csi:
            return
        arrays = {name: np.asarray(self._buf[name], dtype)
                  for name, dtype in CSI_SCALARS}
        arrays['csi'] = np.stack(self._csi)
        arrays['subcarrierindex'] = self._index
        part = f'part-{self._parts:04d}.npz'
        path = os.path.join(self.folder, part)
        self._parts += 1
        self._reset()
        np.savez(path, **arrays)
        match_parent_owner(path)
        self.files.append(f'{self.name}/{part}')

    def close(self):
        self.flush()


WRITERS = {'csv': CsvWriter, 'csi_npz': CsiPartWriter}


class Capture:
    """One capture folder: a writer per source plus meta.json.

    A failing writer is disabled and its error kept in meta; the rest go on.
    """

    def __init__(self, root, request, sources, log=print):
        self.request = request
        self.sources = sources
        self.log = log
        self.start_ns = time.time_ns()
        self.end_ns = None
        self.folder = make_capture_dir(root, request, self.start_ns / 1e9)
        self.writers = {}
        self.errors = {name: None for name in sources}
        self._lock = threading.Lock()
        self._closed = False
        for name, cfg in sources.items():
            try:
                self.writers[name] = WRITERS[cfg['writer']](
                    self.folder, name, cfg)
            except Exception as e:
                self._disable(name, e)

    def _disable(self, name, error):
        self.errors[name] = f'{type(error).__name__}: {error}'
        self.log(f'capture source {name} disabled: {self.errors[name]}')
        try:
            if name in self.writers:
                self.writers[name].close()
        except Exception:
            pass

    def fail(self, name, error):
        """Disable a source (e.g. its msg type could not be loaded)."""
        with self._lock:
            self._disable(name, error)

    def write(self, name, msg, host_ns):
        with self._lock:
            if self._closed or self.errors[name] or name not in self.writers:
                return
            try:
                self.writers[name].write(msg, host_ns)
            except Exception as e:
                self._disable(name, e)

    def rows(self, name):
        writer = self.writers.get(name)
        return writer.rows if writer else 0

    def close(self):
        """Flush every writer and mark the capture complete."""
        with self._lock:
            self._closed = True
            for name, writer in self.writers.items():
                if self.errors[name] is None:
                    try:
                        writer.close()
                    except Exception as e:
                        self._disable(name, e)
            self.end_ns = time.time_ns()
        self.write_meta('complete')

    def write_meta(self, status):
        """Write meta.json atomically."""
        with self._lock:
            sources = {
                name: {
                    'topic': cfg['topic'],
                    'type': cfg['type'],
                    'files': list(getattr(
                        self.writers.get(name), 'files', [])),
                    'rows': self.rows(name),
                    'error': self.errors[name],
                } for name, cfg in self.sources.items()}
        meta = {
            'format_version': FORMAT_VERSION,
            'status': status,
            'request': self.request,
            'start_ns': self.start_ns,
            'end_ns': self.end_ns,
            'timezone': 'UTC',
            'sources': sources,
        }
        path = os.path.join(self.folder, 'meta.json')
        with open(path + '.tmp', 'w') as f:
            json.dump(meta, f, indent=2)
        os.replace(path + '.tmp', path)
        match_parent_owner(path)
