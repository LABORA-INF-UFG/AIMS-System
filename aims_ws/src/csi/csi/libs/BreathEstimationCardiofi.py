import numpy as np
from numba import jit
import time
from scipy.signal import butter, filtfilt, find_peaks
import scipy.signal
from scipy.signal import medfilt
from sklearn.preprocessing import MinMaxScaler
from scipy.stats import variation

def processamento(estimador):
    
    start = time.time_ns()

    # calculando a diferença de fase e desembrulha o sinal
    CSIiDiff = estimador.diferenca_de_fase(estimador.get_csii())
    # também decima o sinal a 10 Hz
    CSIiDiff = estimador.decimador(CSIiDiff)
    #falta o passa baixa
    CSIi_filtered= estimador.filtro_passa_baixa(CSIiDiff)  # fase
    CSIr_filtered= estimador.filtro_passa_baixa(estimador.get_csir())  # amplitude

    del CSIiDiff

    breathBPMResults = []
    heartBPMResults = []
    #TODO: colocar dentro de laço, para avaliar todos os 6 sinais (3 para fase e 3 para amplitude)
    for i in range(6):
        if i<3:
            CSIm = CSIi_filtered[i]
        else:
            CSIm = CSIr_filtered[i-3]

        #TODO: avaliar necessidade de aplicar convolução

        # Hampel Filter 0.5s window, 0.4* std threshold
        #CSIm = estimador.hampel_jit(CSIm,round(0.5*estimador.get_fs()),0.4)

        CSI_var_threshold = estimador.varianca_media(CSIm)

        CSI_window = estimador.analisa_janela(CSIm, CSI_var_threshold)

        CSI_tendency = estimador.calcular_tendencia(CSIm, CSI_window)

        #CSI_filt = estimador.hampel_jit(CSIm-CSI_tendency,round(0.5*estimador.fs),0.1)
        CSI_filt = CSIm-CSI_tendency

        # Definindo o número de amostras analisadas
        #analyzedLength = len(CSI_filt)

        # Buscando pico de respiração em cada subportadora
        # buscando os picos da fft
        #TODO: rever a busca no algoritmo do gustavo
        freq_resp_hz = estimador.busca_picos_fft_old(CSI_filt) * (estimador.segundos_buffer * 2)

        # salvando a taxa de respiração encontrada
        breathBPMResults.append(freq_resp_hz)

        # ################################################################################
        # Heart rate estimation
        estimador.set_fmin_heart(max(2 * freq_resp_hz / 60, 50 / 60))
        estimador.set_fmax_heart(max(2, estimador.get_fmin_heart() + 1))

        # Bandpass filtering between FminHeart and FmaxHeart
        CSIm = estimador.filtro_passa_banda(CSIm, estimador.get_fmin_heart(), estimador.get_fmax_heart())
        # Seleção de subportadoras
        #selected_carriers = estimador.seleciona_subportadoras(CSIm)
        selected_carriers = estimador.seleciona_subportadoras_b(CSIm)

        csi = []
        for sc in selected_carriers:
            csi.append(CSI_filt[:, sc])

        freq_batimentos_hz = estimador.busca_picos_fft_heart_b(np.array(csi)) * (estimador.segundos_buffer * 2)

        # processa batimentos cardíacos
        #freq_batimentos_hz = estimador.processa_batimentos(CSI_filt, selected_carriers)

        heartBPMResults.append(freq_batimentos_hz)
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

        # Frequência de amostragem
        self.fs = 100
        self.segundos_buffer = 30

        # Buffer de armazenamento - fase
        self._buffer_CSIi = np.zeros((self.segundos_buffer * self.fs, 171))
        # Buffer de armazenamento - amplitude
        self._buffer_CSIr = np.zeros((self.segundos_buffer * self.fs, 171))
        self.pkt_count = 0
        self.buffer_preenchido = False

        # ---- Definição de parâmetros ----
        # Intervalo de frequência onde buscará sinal (Hz)
        self.FminBreath = 0.1
        self.FmaxBreath = 1.5

        # Intervalo de frequência onde buscará sinal (Hz)
        self.fmin_heart = 50/60
        self.fmax_heart = 2
        #TODO: dados antigos
        # Número de sinais do PCA
        self.signals = 20
        # Séries da PCA anteriores a esta serão ignoradas:
        self.firstPCA = 1  # python começa a contar do 0
        self.potenciasPCA = []

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
        Parte imaginária do CSI = fase do sinal
        :return: vector nas dimensões tamanho janela x nro de subportadoras
        '''
        return self._buffer_CSIi

    def get_csir(self):
        '''
        Parte real do CSI = amplitude do sinal
        :return: vector nas dimensões tamanho janela x nro de subportadoras
        '''
        p1, p2, p3 = np.array_split(self._buffer_CSIr, 3, axis=1)
        CSIr = [p1, p2, p3]
        return CSIr

    def recebe_pacote_csi(self, msg):
        # Recebe um pacote de dados CSI e armazena no buffer
        CSIr = msg.csi.amplitude
        CSIi = msg.csi.phase

        if self.pkt_count == self._buffer_CSIi.shape[0]:
            #fase
            self._buffer_CSIi = np.roll(self._buffer_CSIi, -1, axis=0)  # desloca os elementos do buffer, depende da ordem linha coluna
            self._buffer_CSIi[-1, :] = CSIi
            #amplitude
            self._buffer_CSIr = np.roll(self._buffer_CSIr, -1, axis=0)  # desloca os elementos do buffer, depende da ordem linha coluna
            self._buffer_CSIr[-1, :] = CSIr
            if not self.buffer_preenchido:
                self.buffer_preenchido = True
        else:
            #fase
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

    def decimador(self, csi):
        # decimando os sinais a 10 Hz
        # Calculate the decimation factor
        fs_new = 10
        decimation_factor = self.fs // fs_new
        # Decimate the signal along the first axis
        p1p2 = scipy.signal.decimate(csi[0], decimation_factor, axis=0)
        p2p3 = scipy.signal.decimate(csi[1], decimation_factor, axis=0)
        p3p1 = scipy.signal.decimate(csi[2], decimation_factor, axis=0)
        # definindo o novo fs
        self.fs = 10
        CSIiDiff = [p1p2, p2p3, p3p1]
        return CSIiDiff

    def diferenca_de_fase(self, csi):
        """
        Essa função tem como objetivo calcular a diferença de fase entre as subportadoras.
        Executa o cálculo de subtração entre subportadoras homólogas em antenas diferentes.
        Também executa o unwrap (desembrulhar) das fases e a centralização em zero dos valores (subtração da média).
        :param csi: numpy array de formato ou shape: (pacotes, subportadoras)
        :return: numpy array de shape: (pacotes, num_tones)
        """
        p1, p2, p3 = np.array_split(csi, 3, axis=1)

        p1p2 = p1 - p2
        p1p2 = np.unwrap(p1p2, axis=0)
        p2p3 = p2 - p3
        p2p3 = np.unwrap(p2p3, axis=0)
        p3p1 = p3 - p1
        p3p1 = np.unwrap(p3p1, axis=0)

        # definindo o novo fs
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

    def passa_baixas(self, csi):
        fc = 4  # cutoff frequency
        order = 4  # filter order
        filter = scipy.signal.butter(order, fc, 'low', fs=self.fs, output='sos')
        p1p2 = scipy.signal.sosfilt(filter, csi[0])
        p2p3 = scipy.signal.sosfilt(filter, csi[1])
        p3p1 = scipy.signal.sosfilt(filter, csi[2])
        CSI_filtered = [p1p2, p2p3, p3p1]
        return CSI_filtered

    def filtro_passa_baixa(self, csi):
        """
        Filtro que remove frequências altas no sinal
        Filtro butterworth de ordem 2, frequência de corte = 4 Hz
        :param csi: numpy array de formato ou shape: (pacotes, subportadoras)
        :return: numpy array de shape: (pacotes, num_tones)
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

    def filtro_passa_banda(self, csi, fmin_heart, fmax_heart):
        order = 1
        b, a = butter(order, [fmin_heart/(self.fs/2), fmax_heart/(self.fs/2)], btype='bandpass')
        # Apply the filter to the signal
        filtered_data = np.zeros_like(csi)
        for i in range(csi.shape[1]):
            line = csi[:, i]
            filtered_segment = filtfilt(b, a, line)
            filtered_data[:, i] = filtered_segment

        return filtered_data

    def filtro_passa_baixa_decima(self, csi):
        """
        Filtro que remove frequências altas no sinal
        Filtro butterworth de ordem 2, frequência de corte = 4 Hz
        :param csi: numpy array de formato ou shape: (pacotes, subportadoras)
        :return: numpy array de shape: (pacotes, num_tones)
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

    def varianca_media(self,csi):

        varianceThreshold = 1.2;            # Limiar de variância de 20% acima da média
        defaultWindowAmount = 5;            # Usa 5 janelas
        windowDuration = round(3 * self.fs) # de 300 amostras cada (3 segundos)
        Ev = np.zeros((defaultWindowAmount, csi.shape[1]))
        for subCarrier in range(0, np.size(csi, 1)):
            sub_arrays = np.array_split(csi[:, subCarrier], defaultWindowAmount)
            Ev[:, subCarrier] = [np.var(sub_array) for sub_array in sub_arrays]
        thresholdEv = np.mean(Ev, axis=0)*varianceThreshold
        return thresholdEv

    def analisa_janela(selfself, CSIm, thresholdEv):
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

    def analisa_janelaa(self,CSIm,thresholdEv):
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

    def calcular_tendencia(self, CSIm, windowEv):
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

    def busca_picos_fft_old(self, csi):
        """
        Essa função tem como objetivo buscar os picos de frequência de interesse, que é diretamente a frequência
        de respiração da pessoa, em Hz.
        :param csi_pca: numpy array de forma (pacotes, signals)
        :return: frequencia de respiração em Hz (float)
        """
        dt = 1 / self.fs  # período, inverso da frequencia
        T = csi.shape[0] * dt  # tempo total de captura
        df = 1 / T
        fNQ = (1 / dt) / 2
        fftFreq = np.arange(0, fNQ, df)
        intervaloMin = np.where(fftFreq >= self.FminBreath)[0][0]
        intervaloMax = np.where(fftFreq <= self.FmaxBreath)[0][-1]
        breathBPMResultsSub = []

        for subCarrier in range(csi.shape[1]):
            maxFFT = -1000
            maxIndex = 0
            fft = np.fft.fft(csi[:, subCarrier])
            fft = np.abs(fft[intervaloMin:intervaloMax + 1])
            max_tmp = fft.max()
            max_idx_tmp = np.where(fft == max_tmp)

            if max_tmp > maxFFT:
                maxFFT = max_tmp
                maxIndex = max_idx_tmp + intervaloMin

            # estimando taxa respiratória:
            breathBPMResultsSub.append(fftFreq[maxIndex])
        return np.median(breathBPMResultsSub)

    def busca_picos_fft_heart_b(self, csi):

        dt = 1 / self.fs  # período, inverso da frequencia
        T = csi.shape[1] * dt  # tempo total de captura
        df = 1 / T
        fNQ = (1 / dt) / 2
        fftFreq = np.arange(0, fNQ, df)
        intervaloMin = np.where(fftFreq >= self.get_fmin_heart())[0][0]
        intervaloMax = np.where(fftFreq <= self.get_fmax_heart())[0][-1]
        breathBPMResultsSub = []

        for subCarrier in range(csi.shape[0]):
            maxFFT = -1000
            maxIndex = 0
            fft = np.fft.fft(csi[subCarrier,:])
            fft = np.abs(fft[intervaloMin:intervaloMax + 1])
            max_tmp = fft.max()
            max_idx_tmp = np.where(fft == max_tmp)

            if max_tmp > maxFFT:
                maxFFT = max_tmp
                maxIndex = max_idx_tmp + intervaloMin

            # estimando taxa respiratória:
            breathBPMResultsSub.append(fftFreq[maxIndex])
        return np.max(breathBPMResultsSub)

    def busca_picos_fft_heart(self, csi):
        """
        Essa função tem como objetivo buscar os picos de frequência de interesse.
        :return: frequencia de batimentos cardíacos em Hz (float)
        """
        dt = 1 / self.fs  # período, inverso da frequencia
        T = csi.shape[0] * dt  # tempo total de captura
        df = 1 / T
        fNQ = (1 / dt) / 2
        fftFreq = np.arange(0, fNQ, df)
        intervaloMin = np.where(fftFreq >= self.get_fmin_heart())[0][0]
        intervaloMax = np.where(fftFreq <= self.get_fmax_heart())[0][-1]

        maxFFT = -1000
        maxIndex = 0
        fft = np.fft.fft(csi)
        fft = np.abs(fft[intervaloMin:intervaloMax + 1])
        max_tmp = fft.max()
        max_idx_tmp = np.where(fft == max_tmp)

        if max_tmp > maxFFT:
            maxFFT = max_tmp
            maxIndex = max_idx_tmp + intervaloMin
        a = fftFreq[maxIndex][0]
        return a[0]

    def busca_picos_fft(self, csi):
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

    def busca_picos_fft2(self, csi):
        """
        Essa função tem como objetivo buscar os picos de frequência de interesse, que é diretamente a frequência
        de respiração da pessoa, em Hz.
        :param csi: numpy array do sinal por subportadora
        :return: frequencia de respiração em Hz (float)
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
                # Caso não hajam picos nesse intervalo, use a frequência  do máximo da FFT no intervalo
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
            for subport in range(array_copy.shape[1]):
                array_copy[:, subport] = np.pad(array[:, subport], windowsize // 2, mode='edge')
                _for_hampel_jit(array_copy[:, subport], windowsize, n)

        else:
            array_copy = np.pad(array_copy, windowsize // 2, mode='edge')
            _for_hampel_jit(array_copy, windowsize, n)
        return array_copy[windowsize // 2:-windowsize // 2]

    def seleciona_subportadoras(self, CSIm):
        # Seleção de subportadoras
        # divide o sinal em janelas de 20 s, com step de 1 s
        # para cada subportadora, calcular a frequência de pico R entre fmin_heart e fmax_heart
        # calcula psi = 1/(var(R))
        window_size = round(20 * self.fs)
        window_step = round(1 * self.fs)
        window_index = 0
        peak_freq = [[] for i in range(np.size(CSIm, 1))]
        for subcarrier in range(np.size(CSIm, 1)):
            window_start = 1
            while window_start < CSIm.shape[0]:
                if (window_start + window_size) < np.size(CSIm, 0):
                    peak_freq[subcarrier].append(
                        self.busca_picos_fft_heart(CSIm[window_start:window_start + window_size, subcarrier]))
                else:
                    peak_freq[subcarrier].append(self.busca_picos_fft_heart(CSIm[window_start:, subcarrier]))
                window_index += 1
                window_start += window_step

        spectral_variability = [np.var(sublist) for sublist in peak_freq]
        spectral_stability = 1.0 / np.array(spectral_variability)
        # Para um score entre 1 e 100, usamos uma normalização entre 0.01 e 1
        spectral_stability_normalized = 1 / np.array(
            np.interp(spectral_variability, (min(spectral_variability), max(spectral_variability)), (0.01, 1)))

        selected_carriers = np.where(spectral_stability_normalized > 20)[0]

        return selected_carriers

    def seleciona_subportadoras_b(self, CSIm):
        # Seleção de subportadoras
        # divide o sinal em janelas de 20 s, com step de 1 s
        # para cada subportadora, calcular a frequência de pico R entre fmin_heart e fmax_heart
        # calcula psi = 1/(var(R))
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
                    #peak_freq[subcarrier].append(self.busca_picos_fft_heart(CSIm[window_start:, subcarrier]))
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
        # Para um score entre 1 e 100, usamos uma normalização entre 0.01 e 1
        spectral_stability_normalized = 1 / np.array(
            np.interp(spectral_variability, (min(spectral_variability), max(spectral_variability)), (0.01, 1)))

        selected_carriers = np.where(spectral_stability_normalized > 20)[0]

        if np.size(selected_carriers) == 0:
            selected_carriers = [np.max(spectral_stability)]

        return selected_carriers


    def processa_batimentos(self, CSI_filt, selected_carriers):
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

class Apneia:
    def __init__(self, qtd_de_estimativas: int = 20):
        self.buffer = []  # acumulador de estimativas (estático, ou seja, apenas das N primeiras estimativas, não muda)
        self.len_buffer = 0
        self.estimativas_atuais = np.zeros(5)
        self.medianaEstimativas = -1
        self.qtd_de_estimativas = qtd_de_estimativas

    def registra_estimativa(self, estimativa: float):
        """
        Essa função registra a estimativa de frequência de respiração e registra em um buffer até enchê-lo.
        Caso o buffer esteja cheio, a estimativa é armazenada em um vetor que guarda sempre as 5 estimativas mais recentes.
        :param estimativa: float com a estimativa de frequência de respiração
        :return: None
        """
        if self.len_buffer < self.qtd_de_estimativas:
            self.buffer.append(estimativa)
            self.len_buffer = len(self.buffer)
            if self.qtd_de_estimativas - len(self.buffer) <= 5:
                self.estimativas_atuais = np.roll(self.estimativas_atuais, -1)
                self.estimativas_atuais[-1] = estimativa

        else:
            self.estimativas_atuais = np.roll(self.estimativas_atuais, -1)
            self.buffer = np.roll(self.buffer, -1)
            self.estimativas_atuais[-1] = estimativa
            self.buffer[-1] = estimativa

    def apneia(self):
        """
        Essa função calcula se há indício de uma apneia ou não. Para isso, ela usa o buffer de estimativas armazenadas
        e calcula a mediana delas. Caso mais de três estimativas recentes estejam diferentes da mediana, é acusado como
        possível apneia.
        :return: boolean indicando a presença ou não de apneia
        """
        if len(self.buffer) < self.qtd_de_estimativas:  # se o buffer ainda não está com a qtd necessária de estimativas
            print('Aguardando mais dados...')
            return False
        else:
            self.medianaEstimativas = np.median(self.buffer)  # calcula a mediana das estimativas do buffer
            resultado = np.logical_or(self.estimativas_atuais > self.medianaEstimativas + 0.1,
                                      self.estimativas_atuais < self.medianaEstimativas - 0.1)
            print(f"Mediana das estimativas armazenadas: {self.medianaEstimativas}")
            resultado = np.where(resultado == True)[0]
            if len(resultado) > 3:
                print('\033[1;31;40mApneia detectada!\033[0m')
                return True
            else:
                return False
