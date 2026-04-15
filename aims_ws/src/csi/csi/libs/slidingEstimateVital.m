function [breathRate, heartRate] = slidingEstimateVital(signalLength, window, counter, prevBreathRate, prevHeartRate)
    %slidingEstimateVital: Estimate breath and heart rates from wifi CSI signals
    %   This function calculates the breath and heart rates based on a sliding window of wifi CSI signals.
    %   We only calculate part of the signal each time we call the function, and then use the previous estimates
    %   to calculate the new values. We do this because processing the entire signal everytime is too slow.
    %
    %   INPUTS:
    %   signalLength   - Size of the window, in seconds.
    %   window         - Matrix of wifi CSI signals.
    %   counter        - Counter to keep track which part of the signal we are processing.
    %   prevBreathRate - The last 6 calculated breath rates.
    %   prevHeartRate  - The last 6 calculated heart rate.
    %
    %   OUTPUTS:
    %   breathRate     - Calculated breath rate.
    %   heartRate      - Calculated heart rate.

	% Carregando valores aferidos anteriormente em um vetor de 1 coluna. Ao longo do código, o valor no slot "counter" será atualizado com a medição atual.
	breathBPMResults(:,1) = prevBreathRate;
	heartBPMResults(:,1) = prevHeartRate;

	% Intervalo de frequência onde buscará sinal (Hz)
	% Algoritmo de sintonizar busca em torno da mediana encontrada (CardioFi)
	FminBreath = 0.1;
	FmaxBreath = 1.5;

	% Intervalo de frequência onde buscará sinal (Hz)
	FminHeart = 50/60;
	FmaxHeart = 2;

	% Taxa de amostragem padrão dos sinais coletados
    Fs = 100;

	currentAnt = counter;

    decimatedSize = ceil(size(window, 1)/10)
	CSIm = zeros(decimatedSize, size(window, 2));

	% Tamanho do sinal de acordo com window
    [dataLength, subCarriers, antennaMax] = size(CSIm);

    % Decimando sinais a 10 Hz
	for subCarrier=1:size(CSIm,2)
		CSIm(:,subCarrier) = decimate(window(:,subCarrier),10);
	end

    % Sobrescrevendo taxa de amostragem do sinal decimado em 10 Hz.
    Fs = 10;

    % <--------------------------------
    % Removendo frequências altas do sinal:
    % Filtro passa-baixas butterworth de ordem 2, frequência de corte de 4 Hz
	FClow = 4;
	order = 2;
	[b,a]=butter(order,FClow/(Fs/2),'low');

    CSImFilt = filtfilt(b, a, CSIm);
    % --------------------------------

	CSImCopy = CSImFilt;
    % CardioFi Preprocessing ---->


    % <----- Seleção de subportadoras para respiração :

    % Split signal in moving window of 20 seconds, step by 1 second
    % For each subcarrier, each time window calculate peak frequency R
    % between FminBreath and FmaxBreath.
    % Calculate psi = 1/(var(R))

    windowSize = round(20*Fs);
    windowStep = round(1*Fs);
    windowIndex = 0;
    clear fftFreq fftAmp peakFreq
    for subCarrier=1:size(CSIm,2)
        for windowStart=1:windowStep:size(CSIm,1)
            windowIndex = windowIndex + 1;
            if (windowStart+windowSize) < size(CSIm,1)
                [fftFreq, fftAmp] = calcFFT(CSIm(windowStart:windowStart+windowSize,subCarrier),Fs);
                [freqAmp, freqIndex] = findpeaks(fftAmp(and(fftFreq>FminBreath,fftFreq<FmaxBreath)));
				fftFreqTemp = fftFreq(and(fftFreq>FminBreath,fftFreq<FmaxBreath));
				freqIndex = fftFreqTemp(freqIndex)';
                [~, maxFreqIndex] = max(freqAmp);
                if ~isempty(freqIndex(maxFreqIndex))
                    peakFreq(windowIndex,subCarrier) = freqIndex(maxFreqIndex);
                else
                    peakFreq(windowIndex,subCarrier) = 0;
                end
            else
                [fftFreq, fftAmp] = calcFFT(CSIm(windowStart:end,subCarrier),Fs);
                [freqAmp, freqIndex] = findpeaks(fftAmp(and(fftFreq>FminBreath,fftFreq<FmaxBreath)));
				fftFreqTemp = fftFreq(and(fftFreq>FminBreath,fftFreq<FmaxBreath));
				freqIndex = fftFreqTemp(freqIndex)';
                [~, maxFreqIndex] = max(freqAmp);
                if ~isempty(freqIndex(maxFreqIndex))
                    peakFreq(windowIndex,subCarrier) = freqIndex(maxFreqIndex);
                else
                    peakFreq(windowIndex,subCarrier) = 0;
                end
                windowIndex = 0;
                break;
            end
        end
    end

    spectralVariability = var(peakFreq(:,:));
    spectralStability = 1./spectralVariability;
    %normSS = normalize(spectralStability,'range',[0,1]);

    % Para um score entre 1 e 100, usamos uma normalização entre 0.01 e 1
    spectralStabilityNormalized = 1./normalize(var(peakFreq(:,:)),'range',[0.01,1]);
    % Seleciona somente a melhor portadora
    %[~, selectedCarriers] = max(spectralStability);

    % Selecionando as subportadoras com score acima de 20
    selectedCarriers = find(spectralStabilityNormalized>20);

    % Selecionando somente subportadoras com variabilidade < 0.001
    %selectedCarriers = find(spectralStabilityNormalized>80);

    if isempty(selectedCarriers)
        [~, selectedCarriers] = max(spectralStability);
    end
    % Seleção de subportadoras para respiração ----->

    clear fftFreq fftAmp peakFreq spectralVariability spectralStability spectralStabilityNormalized
    % Definindo número de amostras analisadas
    analyzedLength = length(CSImFilt);

    %Número de amostras para o alarme de apneia
    apneiaMaxSamples = 1;

    %Limiar do desvio padrão para o alarme de apneia
    apneiaTH = 0.25;

    % Buscando pico de respiração em cada subportadora
    carrierIndex = 0;
    clear breathBPMResultsSub fftFreq fftAmp
    breathBPMResultsSub = zeros(1, size(CSImFilt, 2));

    for subCarrier = 1:size(CSImFilt,2)
        carrierIndex = carrierIndex + 1;
        [fftFreq, fftAmp(:,carrierIndex)] = calcFFT(CSImFilt(:,subCarrier),Fs);
        [freqAmp, freqIndex] = findpeaks(fftAmp(and(fftFreq>FminBreath,fftFreq<FmaxBreath),carrierIndex));
		fftFreqTemp = fftFreq(and(fftFreq>FminBreath,fftFreq<FmaxBreath));
		freqIndex = fftFreqTemp(freqIndex)';
        [~, freqBreath] = max(freqAmp);

        if isempty(freqBreath)
            if median(breathBPMResultsSub) == 0
                % Caso não hajam picos nesse intervalo, use a mediana dos
                % resultados já encontrados nas outras subportadoras
                [a,b] = max(fftAmp(and(fftFreq>FminBreath,fftFreq<FmaxBreath),carrierIndex));
                fftFreqTemp = fftFreq(and(fftFreq>FminBreath,fftFreq<FmaxBreath));
                breathBPMResultsSub(carrierIndex) = fftFreqTemp(b);
                clear a b fftFreqTemp
            else
                % Caso não hajam resultados ainda, use a frequência do máximo
                % da FFT nesse intervalo
                breathBPMResultsSub(carrierIndex) = median(breathBPMResultsSub);
                clear a b fftFreqTemp
            end
        else
            % Caso haja picos nesse intervalo, use a frequência do pico da FFT.
            breathBPMResultsSub(carrierIndex) = freqIndex(freqBreath)*60;
        end
    end

    breathBPMResults(currentAnt,1) = median(breathBPMResultsSub);
	
    % Heart rate estimation:
    FminHeart = max(2*breathBPMResults(currentAnt,1)/60,50/60);
    FmaxHeart = max(2,FminHeart+1);

    % Bandpass filtering between FminHeart and FmaxHeart
    order = 1;
    [b,a]=butter(order,[FminHeart/(Fs/2) FmaxHeart/(Fs/2)],'bandpass');
    CSIm = filtfilt(b, a, CSImCopy);

    % <----- Seleção de subportadoras:

    % Split signal in moving window of 20 seconds, step by 1 second
    % For each subcarrier, each time window calculate peak frequency R
    % between FminHeart and FmaxHeart.
    % Calculate psi = 1/(var(R))

    windowSize = round(20*Fs);
    windowStep = round(1*Fs);
    windowIndex = 0;
    clear fftFreq fftAmp peakFreq
    for subCarrier=1:size(CSIm,2)
        for windowStart=1:windowStep:size(CSIm,1)
            windowIndex = windowIndex + 1;
            if (windowStart+windowSize) < size(CSIm,1)
                [fftFreq, fftAmp] = calcFFT(CSIm(windowStart:windowStart+windowSize,subCarrier),Fs);
                [freqAmp, freqIndex] = findpeaks(fftAmp(and(fftFreq>FminHeart,fftFreq<FmaxHeart)));
				fftFreqTemp = fftFreq(and(fftFreq>FminHeart,fftFreq<FmaxHeart));
				freqIndex = fftFreqTemp(freqIndex)';
                [~, maxFreqIndex] = max(freqAmp);
                if ~isempty(freqIndex(maxFreqIndex))
                    peakFreq(windowIndex,subCarrier) = freqIndex(maxFreqIndex);
                else
                    peakFreq(windowIndex,subCarrier) = 0;
                end
            else
                [fftFreq, fftAmp] = calcFFT(CSIm(windowStart:end,subCarrier),Fs);
                [freqAmp, freqIndex] = findpeaks(fftAmp(and(fftFreq>FminHeart,fftFreq<FmaxHeart)));
				fftFreqTemp = fftFreq(and(fftFreq>FminHeart,fftFreq<FmaxHeart));
				freqIndex = fftFreqTemp(freqIndex)';
                [~, maxFreqIndex] = max(freqAmp);
                if ~isempty(freqIndex(maxFreqIndex))
                    peakFreq(windowIndex,subCarrier) = freqIndex(maxFreqIndex);
                else
                    peakFreq(windowIndex,subCarrier) = 0;
                end
                windowIndex = 0;
                break;
            end
        end
    end

    spectralVariability = var(peakFreq(:,:));
    spectralStability = 1./spectralVariability;
    %normSS = normalize(spectralStability,'range',[0,1]);

    % Para um score entre 1 e 100, usamos uma normalização entre 0.01 e 1
    spectralStabilityNormalized = 1./normalize(var(peakFreq(:,:)),'range',[0.01,1]);
    % Seleciona somente a melhor portadora
    %[~, selectedCarriers] = max(spectralStability);

    % Selecionando as subportadoras com score acima de 20
    selectedCarriers = find(spectralStabilityNormalized>20);

    % Selecionando somente subportadoras com variabilidade < 0.001
    %selectedCarriers = find(spectralStabilityNormalized>80);

    if isempty(selectedCarriers)
        [~, selectedCarriers] = max(spectralStability);
    end
    % Seleção de subportadoras ----->

    clear fftFreq fftAmp
    carrierIndex = 0;
    for subCarrier = selectedCarriers
        carrierIndex = carrierIndex + 1;
        [fftFreq, fftAmp(:,carrierIndex)] = calcFFT(CSImFilt(:,subCarrier),Fs);
    end

    fftAmp = mean(fftAmp,2);
    %fftAmp = fftAmp - hampel(fftAmp,10,0.01);
    [freqAmp, freqIndex] = findpeaks(fftAmp(and(fftFreq>FminHeart,fftFreq<FmaxHeart)));
	fftFreqTemp = fftFreq(and(fftFreq>FminHeart,fftFreq<FmaxHeart));
	freqIndex = fftFreqTemp(freqIndex)';
    if isempty(freqAmp)
        if median(heartBPMResults) == 0
            [~, maxFreqIndex] = max(fftAmp(and(fftFreq>FminHeart,fftFreq<FmaxHeart)));
            [freqIndex] = fftFreq(and(fftFreq>FminHeart,fftFreq<FmaxHeart));
            heartBPMResults(currentAnt,1) = freqIndex(maxFreqIndex)*60;
        else
            heartBPMResults(currentAnt,1) = median(heartBPMResults);
        end
    else
        [~, maxFreqIndex] = max(freqAmp);
        heartBPMResults(currentAnt,1) = freqIndex(maxFreqIndex)*60;
    end
	
    breathRate = breathBPMResults(currentAnt,1); % Respiração estimada para essa antena.
    heartRate = heartBPMResults(currentAnt,1); % Batimentos cardíacos estimados para essa antena.

end

function [ Sxx, faxis ] = calcFFT(x, Fs)
    fftX = fft(x);
    P2 = abs(fftX/length(x));
    faxis = P2(1:round(length(x)/2)+1);
    faxis(2:end-1) = 2*faxis(2:end-1);
    Sxx = Fs*(0:round(length(x)/2))/length(x);
    %plot(Sxx,faxis);
    %title('Single-Sided Amplitude Spectrum of X(t)');
    %xlabel('f (Hz)');
    %ylabel('|P1(f)|');
end

function normArray = normalize(array, method, range)
    if nargin < 3
        range = [0, 1];  % Default range is [0, 1] if not specified
    end

    if strcmp(method, 'range')
        minValue = min(array(:));
        maxValue = max(array(:));
        normArray = (array - minValue) ./ (maxValue - minValue);
        normArray = normArray .* (range(2) - range(1)) + range(1);
    else
        error('Currently, only range normalization is supported.');
    end
end

