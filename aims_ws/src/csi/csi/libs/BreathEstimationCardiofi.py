import numpy as np
from numba import jit
import time
from scipy.signal import butter, filtfilt, find_peaks
import scipy.signal
from scipy.signal import medfilt
from sklearn.preprocessing import MinMaxScaler
from scipy.stats import variation

def process(estimator):
    
    start = time.time_ns()

    # compute the phase difference and unwrap the signal
    CSIiDiff = estimator.phase_difference(estimator.get_csii())
    # also decimate the signal to 10 Hz
    CSIiDiff = estimator.decimator(CSIiDiff)
    #low-pass is missing
    CSIi_filtered= estimator.low_pass_filter(CSIiDiff)  # phase
    CSIr_filtered= estimator.low_pass_filter(estimator.get_csir())  # amplitude

    del CSIiDiff

    breathBPMResults = []
    heartBPMResults = []
    #TODO: put inside a loop, to evaluate all 6 signals (3 for phase and 3 for amplitude)
    for i in range(6):
        if i<3:
            CSIm = CSIi_filtered[i]
        else:
            CSIm = CSIr_filtered[i-3]

        #TODO: evaluate whether convolution needs to be applied

        # Hampel Filter 0.5s window, 0.4* std threshold
        #CSIm = estimator.hampel_jit(CSIm,round(0.5*estimator.get_fs()),0.4)

        CSI_var_threshold = estimator.mean_variance(CSIm)

        CSI_window = estimator.analyze_window(CSIm, CSI_var_threshold)

        CSI_tendency = estimator.compute_trend(CSIm, CSI_window)

        #CSI_filt = estimator.hampel_jit(CSIm-CSI_tendency,round(0.5*estimator.fs),0.1)
        CSI_filt = CSIm-CSI_tendency

        # Defining the number of analyzed samples
        #analyzedLength = len(CSI_filt)

        # Searching for the breathing peak in each subcarrier
        # find the FFT peaks
        #TODO: review the search in Gustavo's algorithm
        freq_resp_hz = estimator.find_fft_peaks_old(CSI_filt) * (estimator.buffer_seconds * 2)

        # save the breathing rate found
        breathBPMResults.append(freq_resp_hz)

        # ################################################################################
        # Heart rate estimation
        estimator.set_fmin_heart(max(2 * freq_resp_hz / 60, 50 / 60))
        estimator.set_fmax_heart(max(2, estimator.get_fmin_heart() + 1))

        # Bandpass filtering between FminHeart and FmaxHeart
        CSIm = estimator.band_pass_filter(CSIm, estimator.get_fmin_heart(), estimator.get_fmax_heart())
        # Subcarrier selection
        #selected_carriers = estimator.select_subcarriers(CSIm)
        selected_carriers = estimator.select_subcarriers_b(CSIm)

        csi = []
        for sc in selected_carriers:
            csi.append(CSI_filt[:, sc])

        heartbeat_freq_hz = estimator.find_fft_peaks_heart_b(np.array(csi)) * (estimator.buffer_seconds * 2)

        # process heartbeats
        #heartbeat_freq_hz = estimator.process_heartbeats(CSI_filt, selected_carriers)

        heartBPMResults.append(heartbeat_freq_hz)
        break
    return np.median(breathBPMResults), np.median(heartBPMResults)


@jit(nopython=True)
def _for_hampel_jit(array_copy, windowsize, n):
    k = 1.4826
    for idx in range(windowsize // 2, len(array_copy) - windowsize // 2):
        window = array_copy[idx - windowsize // 2:idx + windowsize // 2 + 1]
        median = np.median(window)  # calculate window median
        sigma = k * np.median(np.abs(window - median))  # calculate window Median Absolute Deviation (MAD)
        if np.abs(array_copy[idx] - median) > n * sigma:  # if the value at "idx" index is an outlier...
            array_copy[idx] = median  # replace it with the median of the window


class BreathEstimationCardioFI:
    def __init__(self):

        # Sampling frequency
        self.fs = 100
        self.buffer_seconds = 30

        # Storage buffer - phase
        self._buffer_CSIi = np.zeros((self.buffer_seconds * self.fs, 171))
        # Storage buffer - amplitude
        self._buffer_CSIr = np.zeros((self.buffer_seconds * self.fs, 171))
        self.pkt_count = 0
        self.buffer_filled = False

        # ---- Parameter definitions ----
        # Frequency range where the signal is searched (Hz)
        self.FminBreath = 0.1
        self.FmaxBreath = 1.5

        # Frequency range where the signal is searched (Hz)
        self.fmin_heart = 50/60
        self.fmax_heart = 2
        #TODO: old data
        # Number of PCA signals
        self.signals = 20
        # PCA series before this one are ignored:
        self.firstPCA = 1  # python counts from 0
        self.pca_powers = []

    def set_fmin_heart(self, value):
        self.fmin_heart = value
    def set_fmax_heart(self, value):
        self.fmax_heart = value
    def get_fmin_heart(self):
        return self.fmin_heart
    def get_fmax_heart(self):
        return self.fmax_heart


    def get_fs(self):
        return self.fs

    def get_csii(self):
        '''
        Imaginary part of the CSI = signal phase
        :return: vector with dimensions window size x number of subcarriers
        '''
        return self._buffer_CSIi

    def get_csir(self):
        '''
        Real part of the CSI = signal amplitude
        :return: vector with dimensions window size x number of subcarriers
        '''
        p1, p2, p3 = np.array_split(self._buffer_CSIr, 3, axis=1)
        CSIr = [p1, p2, p3]
        return CSIr

    def receive_csi_packet(self, msg):
        # Receive a CSI data packet and store it in the buffer
        CSIr = msg.csi.amplitude
        CSIi = msg.csi.phase

        if self.pkt_count == self._buffer_CSIi.shape[0]:
            #phase
            self._buffer_CSIi = np.roll(self._buffer_CSIi, -1, axis=0)  # shift the buffer elements, depends on row/column order
            self._buffer_CSIi[-1, :] = CSIi
            #amplitude
            self._buffer_CSIr = np.roll(self._buffer_CSIr, -1, axis=0)  # shift the buffer elements, depends on row/column order
            self._buffer_CSIr[-1, :] = CSIr
            if not self.buffer_filled:
                self.buffer_filled = True
        else:
            #phase
            self._buffer_CSIi[self.pkt_count, :] = CSIi
            #amplitude
            self._buffer_CSIr[self.pkt_count, :] = CSIr
            self.pkt_count += 1

    def hampel_filter(self, CSIm, window_size, threshold):
        n_sigma = threshold
        for i in range(CSIm.shape[1]):
            CSIm[:, i] = medfilt(CSIm[:, i], kernel_size=window_size * 2 + 1)
            residuals = np.abs(CSIm[:, i] - medfilt(CSIm[:, i], kernel_size=window_size * 2 + 1))
            MAD = np.median(residuals)
            threshold = n_sigma * MAD
            CSIm[:, i][residuals > threshold] = np.nan
        return CSIm

    def decimator(self, csi):
        # decimating the signals to 10 Hz
        # Calculate the decimation factor
        fs_new = 10
        decimation_factor = self.fs // fs_new
        # Decimate the signal along the first axis
        p1p2 = scipy.signal.decimate(csi[0], decimation_factor, axis=0)
        p2p3 = scipy.signal.decimate(csi[1], decimation_factor, axis=0)
        p3p1 = scipy.signal.decimate(csi[2], decimation_factor, axis=0)
        # defining the new fs
        self.fs = 10
        CSIiDiff = [p1p2, p2p3, p3p1]
        return CSIiDiff

    def phase_difference(self, csi):
        """
        Compute the phase difference between subcarriers.
        Subtracts homologous subcarriers on different antennas.
        Also unwraps the phases and centers the values at zero (mean subtraction).
        :param csi: numpy array of shape: (packets, subcarriers)
        :return: numpy array of shape: (packets, num_tones)
        """
        p1, p2, p3 = np.array_split(csi, 3, axis=1)

        p1p2 = p1 - p2
        p1p2 = np.unwrap(p1p2, axis=0)
        p2p3 = p2 - p3
        p2p3 = np.unwrap(p2p3, axis=0)
        p3p1 = p3 - p1
        p3p1 = np.unwrap(p3p1, axis=0)

        # defining the new fs
        #self.fs = 10
        # stacking the arrays
        #using Cheby 1 filter
        #R = 10  # Decimation factor
        #Wn = 0.8 / R
        #cutoff = 0.8 * (self.fs / 2) / R  # Cutoff frequency
        #b, a = scipy.signal.cheby1(8, 0.05, cutoff/self.fs, 'lowpass')  # Design filter
        #y = scipy.signal.filtfilt(b, a, p1p2)  # Apply filter
        #y_dec = scipy.signal.decimate(y, R, axis=0, zero_phase=True)  # Decimate signal

        CSIiDiff = [p1p2, p2p3, p3p1]
        return CSIiDiff

    def low_pass(self, csi):
        fc = 4  # cutoff frequency
        order = 4  # filter order
        filter = scipy.signal.butter(order, fc, 'low', fs=self.fs, output='sos')
        p1p2 = scipy.signal.sosfilt(filter, csi[0])
        p2p3 = scipy.signal.sosfilt(filter, csi[1])
        p3p1 = scipy.signal.sosfilt(filter, csi[2])
        CSI_filtered = [p1p2, p2p3, p3p1]
        return CSI_filtered

    def low_pass_filter(self, csi):
        """
        Filter that removes high frequencies from the signal
        Butterworth filter of order 2, cutoff frequency = 4 Hz
        :param csi: numpy array of shape: (packets, subcarriers)
        :return: numpy array of shape: (packets, num_tones)
        """
        # Define the filter parameters
        fc = 4  # cutoff frequency
        order = 4  # filter order
        # Compute the filter coefficients
        b, a = butter(order, fc / (self.fs / 2), 'low')

        # Apply the filter to the signal
        #b_csi = filtfilt(b, a, csi)
        p1p2 = filtfilt(b, a, csi[0])
        p2p3 = filtfilt(b, a, csi[1])
        p3p1 = filtfilt(b, a, csi[2])

        return [p1p2, p2p3, p3p1]

    def band_pass_filter(self, csi, fmin_heart, fmax_heart):
        order = 1
        b, a = butter(order, [fmin_heart/(self.fs/2), fmax_heart/(self.fs/2)], btype='bandpass')
        # Apply the filter to the signal
        filtered_data = np.zeros_like(csi)
        for i in range(csi.shape[1]):
            line = csi[:, i]
            filtered_segment = filtfilt(b, a, line)
            filtered_data[:, i] = filtered_segment

        return filtered_data

    def low_pass_filter_decimate(self, csi):
        """
        Filter that removes high frequencies from the signal
        Butterworth filter of order 2, cutoff frequency = 4 Hz
        :param csi: numpy array of shape: (packets, subcarriers)
        :return: numpy array of shape: (packets, num_tones)
        """
        # Define the filter parameters
        fc = 4  # cutoff frequency
        order = 4  # filter order
        # Compute the filter coefficients
        b, a = butter(order, fc / (self.fs / 2), 'low')

        # Apply the filter to the signal
        #b_csi = filtfilt(b, a, csi)
        p1p2 = filtfilt(b, a, csi[0])
        p2p3 = filtfilt(b, a, csi[1])
        p3p1 = filtfilt(b, a, csi[2])

        ## decimating using 'Chebyshev Type I filter'
        # Define filter parameters
        N = 4  # Filter order
        # Define the decimation factor
        dec_factor = 5
        # Compute filter coefficients
        b, a = scipy.signal.cheby1(N, 3, self.fs / 2 * dec_factor / (self.fs / 2), btype='lowpass')
        p1p2 = scipy.signal.decimate(csi[1], dec_factor, ftype=b, axis=0)
        p2p3 = filtfilt(b, a, csi[1])
        p3p1 = filtfilt(b, a, csi[2])
        p1p2b = scipy.signal.decimate(filtfilt(b, a, csi[0]), dec_factor, ftype=b, axis=0)
        p2p3b = filtfilt(b, a, p2p3)
        p3p1b = filtfilt(b, a, p3p1)

        # stacking the arrays
        CSI_filt = [p1p2, p2p3, p3p1]
        return CSI_filt

    def mean_variance(self,csi):

        varianceThreshold = 1.2;            # Variance threshold 20% above the mean
        defaultWindowAmount = 5;            # Uses 5 windows
        windowDuration = round(3 * self.fs) # of 300 samples each (3 seconds)
        Ev = np.zeros((defaultWindowAmount, csi.shape[1]))
        for subCarrier in range(0, np.size(csi, 1)):
            sub_arrays = np.array_split(csi[:, subCarrier], defaultWindowAmount)
            Ev[:, subCarrier] = [np.var(sub_array) for sub_array in sub_arrays]
        thresholdEv = np.mean(Ev, axis=0)*varianceThreshold
        return thresholdEv

    def analyze_window(self, CSIm, thresholdEv):
        num_subcarriers = CSIm.shape[1]
        windowEv = [[] for _ in range(num_subcarriers)]

        for subCarrier in range(num_subcarriers):
            windowIndex = 0
            windowEv[subCarrier].append(1)
            for i in range(1, CSIm.shape[0]):
                csi_sc = CSIm[:, subCarrier]
                w_ev = windowEv[subCarrier]
                wi = w_ev[windowIndex]
                csi = csi_sc[wi:i]
                EvScan = np.var(csi)
                if EvScan > thresholdEv[subCarrier]:
                    windowIndex += 1
                    windowEv[subCarrier].append(i)

            windowEv[subCarrier].append(0)
        return windowEv

    def analyze_window_array(self,CSIm,thresholdEv):
        num_subcarriers = CSIm.shape[1]
        window_size = 10
        windowEv = np.zeros((window_size, num_subcarriers), dtype=int)

        for subCarrier in range(num_subcarriers):
            windowIndex = 0
            windowEv[windowIndex, subCarrier] = 1
            for i in range(1, CSIm.shape[0]):
                EvScan = np.var(CSIm[windowEv[windowIndex, subCarrier]:i + 1, subCarrier])
                if EvScan > thresholdEv[subCarrier]:
                    windowIndex += 1
                    if windowIndex == window_size:
                        # Resize windowEv if it's too small
                        window_size *= 2
                        windowEv.resize((window_size, num_subcarriers))
                    windowEv[windowIndex, subCarrier] = i + 1
            windowEv[windowIndex + 1, subCarrier] = 0
            windowEv[windowIndex + 2:, subCarrier] = 0

        # Trim excess zeros from windowEv
        windowEv = windowEv[:windowIndex + 2, :]
        return windowEv

    def compute_trend(self, CSIm, windowEv):
        trendDW = np.zeros_like(CSIm)
        for subCarrier in range(CSIm.shape[1]):
            for i in range(1, np.size(windowEv[subCarrier])):
                if windowEv[subCarrier][i] > 0:
                    trendDW[windowEv[subCarrier][i-1]:windowEv[subCarrier][i]-1,subCarrier] = np.mean(CSIm[windowEv[subCarrier][i-1]:windowEv[subCarrier][i]-1,subCarrier])
                else:
                    trendDW[windowEv[subCarrier][i-1]:,subCarrier] = np.mean(CSIm[windowEv[subCarrier][i-1]:,subCarrier])
                    break
        return trendDW

    def calc_fft(self, signal):
        fftX = np.fft.fft(signal)
        P2 = np.abs(fftX/len(signal))
        faxis = P2[0:int(len(signal)/2)]
        faxis[1:] *= 2
        Sxx = self.fs * np.arange(1, int(len(signal)/2)+1) / len(signal)
        return Sxx, faxis

    def find_fft_peaks_old(self, csi):
        """
        Find the frequency peaks of interest, which is directly the person's breathing frequency, in Hz.
        :param csi_pca: numpy array of shape (packets, signals)
        :return: breathing frequency in Hz (float)
        """
        dt = 1 / self.fs  # period, inverse of the frequency
        T = csi.shape[0] * dt  # total capture time
        df = 1 / T
        fNQ = (1 / dt) / 2
        fftFreq = np.arange(0, fNQ, df)
        interval_min = np.where(fftFreq >= self.FminBreath)[0][0]
        interval_max = np.where(fftFreq <= self.FmaxBreath)[0][-1]
        breathBPMResultsSub = []

        for subCarrier in range(csi.shape[1]):
            maxFFT = -1000
            maxIndex = 0
            fft = np.fft.fft(csi[:, subCarrier])
            fft = np.abs(fft[interval_min:interval_max + 1])
            max_tmp = fft.max()
            max_idx_tmp = np.where(fft == max_tmp)

            if max_tmp > maxFFT:
                maxFFT = max_tmp
                maxIndex = max_idx_tmp + interval_min

            # estimating the respiratory rate:
            breathBPMResultsSub.append(fftFreq[maxIndex])
        return np.median(breathBPMResultsSub)

    def find_fft_peaks_heart_b(self, csi):

        dt = 1 / self.fs  # period, inverse of the frequency
        T = csi.shape[1] * dt  # total capture time
        df = 1 / T
        fNQ = (1 / dt) / 2
        fftFreq = np.arange(0, fNQ, df)
        interval_min = np.where(fftFreq >= self.get_fmin_heart())[0][0]
        interval_max = np.where(fftFreq <= self.get_fmax_heart())[0][-1]
        breathBPMResultsSub = []

        for subCarrier in range(csi.shape[0]):
            maxFFT = -1000
            maxIndex = 0
            fft = np.fft.fft(csi[subCarrier,:])
            fft = np.abs(fft[interval_min:interval_max + 1])
            max_tmp = fft.max()
            max_idx_tmp = np.where(fft == max_tmp)

            if max_tmp > maxFFT:
                maxFFT = max_tmp
                maxIndex = max_idx_tmp + interval_min

            # estimating the respiratory rate:
            breathBPMResultsSub.append(fftFreq[maxIndex])
        return np.max(breathBPMResultsSub)

    def find_fft_peaks_heart(self, csi):
        """
        Find the frequency peaks of interest.
        :return: heartbeat frequency in Hz (float)
        """
        dt = 1 / self.fs  # period, inverse of the frequency
        T = csi.shape[0] * dt  # total capture time
        df = 1 / T
        fNQ = (1 / dt) / 2
        fftFreq = np.arange(0, fNQ, df)
        interval_min = np.where(fftFreq >= self.get_fmin_heart())[0][0]
        interval_max = np.where(fftFreq <= self.get_fmax_heart())[0][-1]

        maxFFT = -1000
        maxIndex = 0
        fft = np.fft.fft(csi)
        fft = np.abs(fft[interval_min:interval_max + 1])
        max_tmp = fft.max()
        max_idx_tmp = np.where(fft == max_tmp)

        if max_tmp > maxFFT:
            maxFFT = max_tmp
            maxIndex = max_idx_tmp + interval_min
        a = fftFreq[maxIndex][0]
        return a[0]

    def find_fft_peaks(self, csi):
        fftAmp = []
        breathBPMResultsSub = []
        carrierIndex = 0
        for subCarrier in range(csi.shape[1]):
            cs = csi[:, subCarrier]
            fftFreq, famp = self.calc_fft(csi[:, subCarrier])
            fftAmp.append(famp)
            freq_mask = np.logical_and(fftFreq > self.FminBreath, fftFreq < self.FmaxBreath)
            freqIndex = find_peaks(famp[freq_mask])
            #findpeaks(fftAmp(
            #                   and(fftFreq>FminBreath,fftFreq<FmaxBreath),carrierIndex
            #                 ),
            #           fftFreq(
            #                   and(fftFreq>FminBreath,fftFreq<FmaxBreath)
            #                   )
            #           )

    def find_fft_peaks2(self, csi):
        """
        Find the frequency peaks of interest, which is directly the person's breathing frequency, in Hz.
        :param csi: numpy array of the signal per subcarrier
        :return: breathing frequency in Hz (float)
        """
        fftAmp = []
        breathBPMResultsSub = []
        carrierIndex = 0
        for subCarrier in range(csi.shape[1]):
            fftFreq, famp = self.calc_fft(csi[:,subCarrier])
            fftAmp.append(famp)
            freq_mask = np.logical_and(fftFreq > self.FminBreath, fftFreq < self.FmaxBreath)
            freq_amp = fftAmp[carrierIndex][freq_mask]
            freq_index, _ = find_peaks(freq_amp)
            freq_amp = freq_amp[freq_index]
            freq_index = freq_index[freq_amp.argsort()[::-1]]
            freq_index = freq_index[freq_index.argsort()]
            freq_amp = freq_amp[freq_index.argsort()]

            if len(freq_amp) == 0:
                # If there are no peaks in this range, use the frequency of the FFT maximum in the range
                # Find the maximum value and index within the specified frequency range
                mask = np.logical_and(fftFreq > self.FminBreath, fftFreq < self.FmaxBreath)
                amp_masked = fftAmp[mask, carrierIndex]
                max_idx = np.argmax(amp_masked)
                max_val = amp_masked[max_idx]

                # Get the corresponding frequency value
                freq_masked = fftFreq[mask]
                freq_val = freq_masked[max_idx]

                # Assign values to output variables
                #a = max_val
                breathBPMResultsSub.append(freq_val)
            else:
                breathBPMResultsSub.append(freq_index[np.argmax(freq_amp)])

        return np.median(breathBPMResultsSub)

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

    def select_subcarriers(self, CSIm):
        # Subcarrier selection
        # split the signal into 20 s windows, with a 1 s step
        # for each subcarrier, compute the peak frequency R between fmin_heart and fmax_heart
        # compute psi = 1/(var(R))
        window_size = round(20 * self.fs)
        window_step = round(1 * self.fs)
        window_index = 0
        peak_freq = [[] for i in range(np.size(CSIm, 1))]
        for subcarrier in range(np.size(CSIm, 1)):
            window_start = 1
            while window_start < CSIm.shape[0]:
                if (window_start + window_size) < np.size(CSIm, 0):
                    peak_freq[subcarrier].append(
                        self.find_fft_peaks_heart(CSIm[window_start:window_start + window_size, subcarrier]))
                else:
                    peak_freq[subcarrier].append(self.find_fft_peaks_heart(CSIm[window_start:, subcarrier]))
                window_index += 1
                window_start += window_step

        spectral_variability = [np.var(sublist) for sublist in peak_freq]
        spectral_stability = 1.0 / np.array(spectral_variability)
        # For a score between 1 and 100, we use a normalization between 0.01 and 1
        spectral_stability_normalized = 1 / np.array(
            np.interp(spectral_variability, (min(spectral_variability), max(spectral_variability)), (0.01, 1)))

        selected_carriers = np.where(spectral_stability_normalized > 20)[0]

        return selected_carriers

    def select_subcarriers_b(self, CSIm):
        # Subcarrier selection
        # split the signal into 20 s windows, with a 1 s step
        # for each subcarrier, compute the peak frequency R between fmin_heart and fmax_heart
        # compute psi = 1/(var(R))
        window_size = round(20 * self.fs)
        window_step = round(1 * self.fs)
        window_index = 0
        peak_freq = [[] for i in range(np.size(CSIm, 1))]
        for subcarrier in range(np.size(CSIm, 1)):
            window_start = 1
            while window_start < CSIm.shape[0]:
                if (window_start + window_size) < np.size(CSIm, 0):
                    fft_freq, fft_a = self.calc_fft(CSIm[window_start:window_start + window_size, subcarrier])
                    # define frequency range to search for peaks
                    mask = (fft_freq > self.get_fmin_heart()) & (fft_freq < self.get_fmax_heart())
                    # find peaks in fftAmp
                    peaks, _ = find_peaks(fft_a[mask], distance=1)
                    # extract peak amplitudes and frequencies
                    freqAmp = fft_a[mask][peaks]
                    freqIndex = fft_freq[mask][peaks]
                    if len(freqAmp) == 0:
                        pf = 0
                    else:
                        pf = freqIndex[np.argmax(freqAmp)]
                    peak_freq[subcarrier].append(pf)
                else:
                    #peak_freq[subcarrier].append(self.find_fft_peaks_heart(CSIm[window_start:, subcarrier]))
                    fft_freq, fft_a = self.calc_fft(CSIm[window_start:, subcarrier])
                    # define frequency range to search for peaks
                    mask = (fft_freq > self.get_fmin_heart()) & (fft_freq < self.get_fmax_heart())
                    # find peaks in fftAmp
                    peaks, _ = find_peaks(fft_a[mask], distance=1)
                    # extract peak amplitudes and frequencies
                    freqAmp = fft_a[mask][peaks]
                    freqIndex = fft_freq[mask][peaks]
                    if len(freqAmp) == 0:
                        pf = 0
                    else:
                        pf = freqIndex[np.argmax(freqAmp)]
                    peak_freq[subcarrier].append(pf)
                window_index += 1
                window_start += window_step

        spectral_variability = [np.var(sublist) for sublist in peak_freq]
        spectral_stability = 1.0 / np.array(spectral_variability)
        # For a score between 1 and 100, we use a normalization between 0.01 and 1
        spectral_stability_normalized = 1 / np.array(
            np.interp(spectral_variability, (min(spectral_variability), max(spectral_variability)), (0.01, 1)))

        selected_carriers = np.where(spectral_stability_normalized > 20)[0]

        if np.size(selected_carriers) == 0:
            selected_carriers = [np.max(spectral_stability)]

        return selected_carriers


    def process_heartbeats(self, CSI_filt, selected_carriers):
        carrier_index = 0
        fft_amp = []
        for sc in selected_carriers:
            fft_freq, fft_a = self.calc_fft(CSI_filt[:, sc])
            fft_amp.append(fft_a)
            carrier_index += 1

        fft_amp = np.mean(fft_amp, axis=0)
        # compute the indices of the frequency values between FminHeart and FmaxHeart
        freq_indices = np.where((fft_freq > self.get_fmin_heart()) & (fft_freq < self.get_fmax_heart()))[0]
        # extract the amplitude values for the frequency range of interest
        amp_range = fft_amp[freq_indices]
        # find peaks in the amplitude range using the `find_peaks` function
        peaks, peak_properties = find_peaks(amp_range)
        # extract the frequency values corresponding to the peak indices
        freqAmp = fft_freq[freq_indices][peaks]
        freqIndex = freq_indices[peaks]
        max_freq_index = np.argmax(freqAmp)
        return freqAmp[max_freq_index] * 60

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
