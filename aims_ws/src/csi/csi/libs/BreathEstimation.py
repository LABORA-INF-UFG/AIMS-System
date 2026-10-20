import numpy as np
from scipy import signal
from sklearn.decomposition import PCA
from numba import jit
import time


def process(estimator, apnea, pkts_recv):
    
    start = time.time_ns()
    # compute the phase difference
    phase_diff = estimator.phase_difference(estimator.get_csi())

    # Hampel filter
    estimator.hampel_jit(phase_diff, 10)

    # remove outliers following the general trend of the subcarriers
    CSI_clean = estimator.outlier_channel_removal(phase_diff)
    del phase_diff

    # apply low-pass filter
    CSI_filtered = estimator.low_pass(CSI_clean)
    del CSI_clean

    # apply PCA
    CSI_pca = estimator.pca(CSI_filtered)

    # find the FFT peaks
    freq_resp_hz = estimator.find_fft_peaks(CSI_pca)
    del CSI_pca

    estimate = float(freq_resp_hz) * (estimator.buffer_seconds * 2)
    apnea.register_estimate(estimate)
    occurrence = apnea.detect_apnea()

    print(f"\n\033[92mEstimated breathing: {estimate}\033[0m")
    print(f"Execution time {pkts_recv}: {(time.time_ns() - start)/1000000}ms")
    print(f"Apnea: {occurrence}")
    return occurrence, estimate


@jit(nopython=True)
def _for_hampel_jit(array_copy, windowsize, n):
    k = 1.4826
    for idx in range(windowsize // 2, len(array_copy) - windowsize // 2):
        window = array_copy[idx - windowsize // 2:idx + windowsize // 2 + 1]
        median = np.median(window)  # calculate window median
        sigma = k * np.median(np.abs(window - median))  # calculate window Median Absolute Deviation (MAD)
        if np.abs(array_copy[idx] - median) > n * sigma:  # if the value at "idx" index is an outlier...
            array_copy[idx] = median  # replace it with the median of the window


class BreathEstimation:
    def __init__(self):

        # Sampling frequency
        self.fs = 100
        self.buffer_seconds = 30

        # Storage buffer
        self._buffer = np.zeros((self.buffer_seconds * self.fs, 171))
        self.pkt_count = 0
        self.buffer_filled = False

        # ---- Parameter definitions ----
        # Number of PCA signals
        self.signals = 20

        # Frequency range where the signal is searched (Hz)
        self.FminBreath = 0.1
        self.FmaxBreath = 1.5

        # Frequency range where the signal is searched (Hz)
        self.FminHeart = 50/60
        self.FmaxHeart = 2

        # PCA series before this one are ignored:
        self.firstPCA = 1  # python counts from 0

        self.pca_powers = []

    def save_pca_powers(self, title):
        self.pca_powers = np.array(self.pca_powers).reshape(-1, self.signals - self.firstPCA)
        np.savetxt(f'{title}.txt', self.pca_powers, delimiter=',')

    def get_csi(self):
        return self._buffer

    def receive_csi_packet(self, msg):
        # Receive a CSI data packet and store it in the buffer
        csi = msg.csi.phase
        if self.pkt_count == self._buffer.shape[0]:
            self._buffer = np.roll(self._buffer, -1, axis=0)  # shift the buffer elements, depends on row/column order
            self._buffer[-1, :] = csi
            if not self.buffer_filled:
                self.buffer_filled = True

        else:
            self._buffer[self.pkt_count, :] = csi
            self.pkt_count += 1

    def phase_difference(self, csi):
        """
        Compute the phase difference between subcarriers.
        Subtracts homologous subcarriers on different antennas.
        Also unwraps the phases and centers the values at zero (mean subtraction).
        :param csi: numpy array of shape: (packets, subcarriers)
        :return: numpy array of shape: (packets, num_tones)
        """
        phase1 = csi[:, :57]
        phase2 = csi[:, 57:114]
        CSIiDiff = phase1 - phase2
        CSIiDiff = np.unwrap(CSIiDiff, axis=0)
        return CSIiDiff - np.mean(CSIiDiff, axis=0)

    def outlier_channel_removal(self, csi):
        """
        Remove subcarrier outliers following the general trend of the subcarriers; they are replaced by the
        mean of the previous and following values (20 neighbors).
        Unlike the Hampel filter, where each subcarrier is considered individually, here the tolerated maximum
        and minimum values are defined from the median of the maxima and minima of all subcarriers.
        :param csi: shape: (packets, subcarriers)
        :return: outlier-free filtered CSI of shape (packets, subcarriers)
        """
        # although Hampel is already applied, this filter keeps all subcarriers' values close together,
        # since Hampel analyzes subcarriers individually, not jointly.
        CSIclean = csi.copy()

        maxCSI = np.max(csi, axis=0)
        minCSI = np.min(csi, axis=0)

        # define the maximum limit of the values across subcarriers
        maxCSIthreshold = np.median(maxCSI) + 0.5 * (np.median(maxCSI) - np.median(minCSI))

        # define the minimum limit of the values across subcarriers
        minCSIthreshold = np.median(minCSI) - 0.5 * (np.median(maxCSI) - np.median(minCSI))

        ############## possible bottleneck here ################
        # find values outside the limits and replace them with the neighborhood mean
        outliers = np.where((csi > maxCSIthreshold) | (csi < minCSIthreshold))
        for idx, subcarrier in zip(outliers[0], outliers[1]):
            if idx - 10 < 0:
                CSIclean[idx, subcarrier] = np.mean(np.concatenate([csi[0:idx, subcarrier], csi[idx + 1:idx + 11, subcarrier]]))
            elif idx + 10 > csi.shape[0]:
                CSIclean[idx, subcarrier] = np.mean(np.concatenate([csi[idx - 10:idx, subcarrier], csi[idx + 1:, subcarrier]]))
            else:
                CSIclean[idx, subcarrier] = np.mean(np.concatenate([csi[idx - 10:idx, subcarrier], csi[idx + 1:idx + 11, subcarrier]]))

        return CSIclean

    def low_pass(self, csi):
        ################### not using 3 / (100/2), since fs is already declared in the function ############
        filter = signal.butter(2, 3, 'low', fs=self.fs, output='sos')
        CSI_filtered = signal.sosfilt(filter, csi)
        self.buffer_plot = CSI_filtered.copy()
        return CSI_filtered

    def pca(self, csi):
        """
        Reduce the dimensionality of the input data using scikit-learn's PCA (Principal Component Analysis).
        :param csi: numpy array of shape: (packets, subcarriers)
        :return: clean CSI of shape (packets, signals)
        """
        pca = PCA(n_components=self.signals)
        CSImPCA = pca.fit_transform(csi)
        return CSImPCA

    def find_fft_peaks(self, csi_pca):
        """
        Find the frequency peaks of interest, which is directly the person's breathing frequency, in Hz.
        :param csi_pca: numpy array of shape (packets, signals)
        :return: breathing frequency in Hz (float)
        """
        dt = 1 / self.fs  # period, inverse of the frequency
        T = csi_pca.shape[0] * dt  # total capture time
        df = 1 / T
        fNQ = (1 / dt) / 2
        fftFreq = np.arange(0, fNQ, df)
        interval_min = np.where(fftFreq >= self.FminBreath)[0][0]
        interval_max = np.where(fftFreq <= self.FmaxBreath)[0][-1]

        maxFFT = -1000
        maxIndex = 0

        for pca_component in range(self.firstPCA, self.signals):
            fftPCA = np.fft.fft(csi_pca[:, pca_component])
            fftPCA = np.abs(fftPCA[interval_min:interval_max + 1])
            max_tmp = fftPCA.max()
            self.pca_powers.append(max_tmp)
            max_idx_tmp = np.where(fftPCA == max_tmp)

            if max_tmp > maxFFT:
                maxFFT = max_tmp
                maxIndex = max_idx_tmp + interval_min

        # estimating the respiratory rate:
        freq_resp = fftFreq[maxIndex]
        #print(fftFreq[interval_min:interval_max])
        return freq_resp

    def hampel_jit(self, array, windowsize, n=3):
        array_copy = np.zeros((array.shape[0] + ((windowsize // 2) * 2), array.shape[1]))
        if array_copy.ndim > 1:
            for subcarrier in range(array_copy.shape[1]):
                array_copy[:, subcarrier] = np.pad(array[:, subcarrier], windowsize // 2, mode='edge')
                _for_hampel_jit(array_copy[:, subcarrier], windowsize, n)

        else:
            array_copy = np.pad(array_copy, windowsize // 2, mode='edge')
            _for_hampel_jit(array_copy, windowsize, n)
        return array_copy[windowsize // 2:-windowsize // 2]


class Apnea:
    def __init__(self, num_estimates: int = 20):
        self.buffer = []  # estimate accumulator (static: only the first N estimates, does not change)
        self.len_buffer = 0
        self.current_estimates = np.zeros(5)
        self.median_estimates = -1
        self.num_estimates = num_estimates

    def register_estimate(self, estimate: float):
        """
        Store the breathing frequency estimate in a buffer until it is full.
        Once the buffer is full, the estimate is stored in a vector that always holds the 5 most recent estimates.
        :param estimate: float with the breathing frequency estimate
        :return: None
        """
        if self.len_buffer < self.num_estimates:
            self.buffer.append(estimate)
            self.len_buffer = len(self.buffer)
            if self.num_estimates - len(self.buffer) <= 5:
                self.current_estimates = np.roll(self.current_estimates, -1)
                self.current_estimates[-1] = estimate

        else:
            self.current_estimates = np.roll(self.current_estimates, -1)
            self.buffer = np.roll(self.buffer, -1)
            self.current_estimates[-1] = estimate
            self.buffer[-1] = estimate

    def detect_apnea(self):
        """
        Compute whether there is an indication of apnea. It uses the buffer of stored estimates and computes
        their median. If more than three recent estimates differ from the median, possible apnea is reported.
        :return: boolean indicating the presence or absence of apnea
        """
        if len(self.buffer) < self.num_estimates:  # if the buffer does not yet hold the required number of estimates
            print('Waiting for more data...')
            return False
        else:
            self.median_estimates = np.median(self.buffer)  # compute the median of the buffered estimates
            result = np.logical_or(self.current_estimates > self.median_estimates + 0.1,
                                      self.current_estimates < self.median_estimates - 0.1)
            print(f"Median of stored estimates: {self.median_estimates}")
            result = np.where(result == True)[0]
            if len(result) > 3:
                print('\033[1;31;40mApnea detected!\033[0m')
                return True
            else:
                return False