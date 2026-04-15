import numpy as np

from custom_interfaces.msg import PktCSI


class CsiWindow:
    """
    A class used to represent a window of CSI data.

    :param window_size: The size of the window
    :param n_subcarriers: The number of subcarriers
    """

    def __init__(self, window_size: int, subcarriers: int) -> None:
        self._window_size = window_size
        self._window = np.zeros((self._window_size, subcarriers),
                                dtype=np.float64)
        self._pointer = 0

    def insert(self, new_data: np.ndarray) -> None:
        """
        Insert new CSI data into the window and update the pointer position.

        :param new_data: The new CSI data, must have shape (subcarriers)
        """
        self._window[self._pointer] = new_data
        self._pointer = (self._pointer + 1) % self._window_size

    def get(self) -> np.ndarray:
        """
        Return the window of CSI data.

        :return: The window of CSI data, with the oldest data at the start of
                 the array, and newest data at the end.
        """
        return np.roll(self._window, self._window_size - self._pointer, axis=0)


class OctaveCardiofiWindow:
    """
    Class to handle the amplitude and phase signal windows.

    :param freq: The frequency CSI data is updated per second
    :param antennas: The number of antennas
    :param subcarriers: The number of subcarriers in each antenna
    :param size_seconds: The size of the window, in seconds
    """

    def __init__(self,
                 freq: int = 100,
                 antennas: int = 3,
                 subcarriers: int = 57,
                 size_seconds: int = 15) -> None:

        self._antennas = antennas
        self._subcarriers = subcarriers

        self.amplitude_windows = [CsiWindow(size_seconds * freq, subcarriers)
                                  for _ in range(antennas)]
        self.phase_windows = [CsiWindow(size_seconds * freq, subcarriers)
                              for _ in range(antennas)]

    def insert(self, pkt: PktCSI) -> None:
        """
        Update the windows with new data from a PktCSI object.

        :param pkt: The PktCSI object.
        """
        for i in range(self._antennas):
            self.amplitude_windows[i].insert(
                pkt.csi.amplitude[i*self._subcarriers:(i+1)*self._subcarriers])
            self.phase_windows[i].insert(
                pkt.csi.phase[i*self._subcarriers:(i+1)*self._subcarriers])
