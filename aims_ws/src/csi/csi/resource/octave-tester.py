import json
from pathlib import Path
import statistics
from typing import Dict

from oct2py import Oct2Py

from OctaveCardiofiFree import OctaveCardiofiWindow

DIR = Path(__file__).resolve().parent
TIME = 15
FREQ = 100
ANT = 3
SUBC = 57


def filename_to_dict(filename: str, results: Dict[str, Dict]) -> str:
    parts = filename.split('-')
    key = parts[0]
    results[key] = {
        'name': parts[0],
        'patient': parts[3],
        'position': parts[6],
        'capture_device': parts[4],
        'heart_control': parts[1],
        'heart_pred': None,
        'breath_control': parts[2],
        'breath_pred': None,
    }
    return key



def process_file(file: Path, results: Dict[str, Dict]) -> None:
    cardiofi_windows = OctaveCardiofiWindow(freq=FREQ, size_seconds=TIME,
                                            antennas=ANT, subcarriers=SUBC)
    oc = Oct2Py()
    oc.addpath(str(Path.joinpath(DIR.parent, 'libs')))

    breath_all = []
    heart_all = []

    key = filename_to_dict(file.stem, results)

    with file.open() as f:
        breath_last6 = [0] * 6
        heart_last6 = [0] * 6

        freq_counter = 0
        proc_counter = 0
        for pkt_counter, pkt in enumerate(f):
            pkt = json.loads(pkt.replace("\'", "\""))
            cardiofi_windows.insert(pkt)

            if freq_counter == 0 and pkt_counter >= FREQ * TIME:
                if proc_counter == 0:
                    window = cardiofi_windows.amplitude_windows[0].get()
                elif proc_counter == 1:
                    window = cardiofi_windows.amplitude_windows[1].get()
                elif proc_counter == 2:
                    window = cardiofi_windows.amplitude_windows[2].get()
                elif proc_counter == 3:
                    window = (cardiofi_windows.phase_windows[0].get()
                              - cardiofi_windows.phase_windows[1].get())
                elif proc_counter == 4:
                    window = (cardiofi_windows.phase_windows[1].get()
                              - cardiofi_windows.phase_windows[2].get())
                elif proc_counter == 5:
                    window = (cardiofi_windows.phase_windows[2].get()
                              - cardiofi_windows.phase_windows[0].get())
                else:
                    raise RuntimeError(f'Unexpected value for proc_counter: '
                                       f'{proc_counter}')

                breath_rate, heart_rate = oc.slidingEstimateVital(
                    TIME,
                    window,
                    proc_counter + 1,
                    breath_last6,
                    heart_last6,
                    nout=2
                )
                breath_all.append(breath_rate)
                breath_last6[proc_counter] = breath_rate
                heart_all.append(heart_rate)
                heart_last6[proc_counter] = heart_rate

                proc_counter = (proc_counter + 1) % 6
            freq_counter = (freq_counter + 1) % FREQ

    results[key]['breath_pred'] = statistics.mean(breath_all)
    results[key]['heart_pred'] = statistics.mean(heart_all)
    oc.exit()


def main() -> None:
    results: Dict[str, Dict] = {}
    files = Path(Path.joinpath(DIR, 'full-readings')).glob('*.txt')
    for file in files:
        process_file(file, results)

    with open('results.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
