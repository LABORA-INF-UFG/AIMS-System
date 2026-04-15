import os
import serial
import numpy as np
import struct


# Change the configuration file name
configFileName = os.getenv('AIMS') + f'/aims_ws/src/csi/csi/resource/xwr1642_profile_VitalSigns_20fps_Front.cfg'
CLIport = {}
Dataport = serial.Serial('/dev/ttyACM1', 921600)
byteBuffer = np.zeros(2**15,dtype = 'uint8')
byteBufferLength = 0



# Function to parse the data inside the configuration file

def parseConfigFile(configFileName):
    configParameters = {} # Initialize an empty dictionary to store the configuration parameters
    
    # Read the configuration file and send it to the board
    config = [line.rstrip('\r\n') for line in open(configFileName)]
    for i in config:
        
        # Split the line
        splitWords = i.split(" ")
        
        # Hard code the number of antennas, change if other configuration is used
        numRxAnt = 4
        numTxAnt = 3
        
        # Get the information about the profile configuration
        if "profileCfg" in splitWords[0]:
            startFreq = int(float(splitWords[2]))
            idleTime = int(splitWords[3])
            rampEndTime = float(splitWords[5])
            freqSlopeConst = float(splitWords[8])
            numAdcSamples = int(splitWords[10])
            numAdcSamplesRoundTo2 = 1;
            
            while numAdcSamples > numAdcSamplesRoundTo2:
                numAdcSamplesRoundTo2 = numAdcSamplesRoundTo2 * 2;

            digOutSampleRate = int(splitWords[11])
            
        # Get the information about the frame configuration    
        elif "frameCfg" in splitWords[0]:
            
            chirpStartIdx = int(splitWords[1])
            chirpEndIdx = int(splitWords[2])
            numLoops = int(splitWords[3])
            framePeriodicity = int(splitWords[5])

        # Get the information about the GUI configuration   
        elif "guiMonitor" in splitWords[0]:
            guiMonitor_flag1 =  int(splitWords[1])
            guiMonitor_flag2 = int(splitWords[2])  
            guiMonitor_rangeAzimuthHeatMap = int(splitWords[3])
            #guiMonitor_rangeDopplerHeatMap = int(splitWords[4])

        # Get the information about the GUI configuration   
        elif "vitalSignsCfg" in splitWords[0]:
            rangeStartMeters =  float(splitWords[1])
            rangeEndMeters = float(splitWords[2])  
            winLenBreath = int(splitWords[3])
            winLenHeart = int(splitWords[4])
            
    # Combine the read data to obtain the configuration parameters           
    numChirpsPerFrame = (chirpEndIdx - chirpStartIdx + 1) * numLoops
    configParameters["numDopplerBins"] = numChirpsPerFrame / numTxAnt
    configParameters["numRangeBins"] = numAdcSamplesRoundTo2
    configParameters["rangeResolutionMeters"] = (3e8 * digOutSampleRate * 1e3) / (2 * freqSlopeConst * 1e12 * numAdcSamples)
    configParameters["rangeIdxToMeters"] = (3e8 * digOutSampleRate * 1e3) / (2 * freqSlopeConst * 1e12 * configParameters["numRangeBins"])
    configParameters["dopplerResolutionMps"] = 3e8 / (2 * startFreq * 1e9 * (idleTime + rampEndTime) * 1e-6 * configParameters["numDopplerBins"] * numTxAnt)
    configParameters["chirpDuration_us"] = (1e3*numAdcSamples)/(digOutSampleRate)
    freqSlopeConst_temp = 48*freqSlopeConst* 2**26 * 1e3/((3.6*1e9)*900);  # To match the C-code 

    configParameters["chirpBandwidth_kHz"] = (freqSlopeConst_temp)*(configParameters["chirpDuration_us"])
    numTemp = (configParameters["chirpDuration_us"])*(digOutSampleRate)*(3e8)
    denTemp = 2*(configParameters["chirpBandwidth_kHz"])
    configParameters["rangeMaximum"] =  numTemp/(denTemp*1e9)
    configParameters["rangeBinSize_meter"] = configParameters["rangeMaximum"]/(configParameters["numRangeBins"])
    rangeStart_Index = int(rangeStartMeters/configParameters["rangeBinSize_meter"])
    rangeEnd_Index   = int(rangeEndMeters/configParameters["rangeBinSize_meter"])
    configParameters["lambdaCenter_mm"] = (3e8/(startFreq))/1e6
    configParameters["rangeStart_Index"] = rangeStart_Index
    configParameters["rangeEnd_Index"] = rangeEnd_Index
    configParameters["numRangeBinProcessed"] = rangeEnd_Index - rangeStart_Index + 1
    
    return configParameters
   
# ------------------------------------------------------------------

# Funtion to read and parse the incoming data
def readAndParseVitalSigns(Dataport, configParameters):
    global byteBuffer, byteBufferLength,vitalSignsObj

    # Constants
    magicWord = [2, 1, 4, 3, 6, 5, 8, 7]
    maxBufferSize = 2**15

    heatmap_size = (64, 48)
    heatmap = np.zeros((heatmap_size[0], heatmap_size[1]), dtype=np.int16)
    
    VITAL_SIGNS_VECTOR = 10

    LENGTH_HEADER_BYTES                  = 32   # Header + Magic Word
    LENGTH_TLV_MESSAGE_HEADER_BYTES      = 8
    LENGTH_DEBUG_DATA_OUT_BYTES          = 40   # VitalSignsDemo_OutputStats size
    MMWDEMO_OUTPUT_MSG_SEGMENT_LEN       = 32   # The data sent out through the UART has Extra Padding to make it a multiple of MMWDEMO_OUTPUT_MSG_SEGMENT_LEN
    LENGTH_OFFSET_BYTES                  = LENGTH_HEADER_BYTES  - len(magicWord) + LENGTH_TLV_MESSAGE_HEADER_BYTES
    LENGTH_OFFSET_NIBBLES                = 2*LENGTH_OFFSET_BYTES

    

    totalPayloadSize_bytes = LENGTH_HEADER_BYTES;
    totalPayloadSize_bytes += LENGTH_TLV_MESSAGE_HEADER_BYTES + (4*configParameters["numRangeBinProcessed"]);
    totalPayloadSize_bytes += LENGTH_TLV_MESSAGE_HEADER_BYTES +  LENGTH_DEBUG_DATA_OUT_BYTES;
    
    # Initialize variables
    magicOK = 0 # Checks if magic number has been read
    dataOK = 0 # Checks if the data has been read correctly
    frameNumber = 0
    vitalSignsObj = {}
    tlv_type = 0
    
    readBuffer = Dataport.read(Dataport.in_waiting)
    byteVec = np.frombuffer(readBuffer, dtype = 'uint8')
    byteCount = len(byteVec)
    
    # Check that the buffer is not full, and then add the data to the buffer
    if (byteBufferLength + byteCount) < maxBufferSize:
        byteBuffer[byteBufferLength:byteBufferLength + byteCount] = byteVec[:byteCount]
        byteBufferLength = byteBufferLength + byteCount
        
    # Check that the buffer has some data
    if byteBufferLength > 16:
        
        # Check for all possible locations of the magic word
        possibleLocs = np.where(byteBuffer == magicWord[0])[0]

        # Confirm that is the beginning of the magic word and store the index in startIdx
        startIdx = []
        for loc in possibleLocs:
            check = byteBuffer[loc:loc+8]
            if np.all(check == magicWord):
                startIdx.append(loc)
               
        # Check that startIdx is not empty
        if startIdx:
            
            # Remove the data before the first start index
            if startIdx[0] > 0 and startIdx[0] < byteBufferLength:
                byteBuffer[:byteBufferLength-startIdx[0]] = byteBuffer[startIdx[0]:byteBufferLength]
                byteBuffer[byteBufferLength-startIdx[0]:] = np.zeros(len(byteBuffer[byteBufferLength-startIdx[0]:]),dtype = 'uint8')
                byteBufferLength = byteBufferLength - startIdx[0]
                
            # Check that there have no errors with the byte buffer length
            if byteBufferLength < 0:
                byteBufferLength = 0
                
            # word array to convert 4 bytes to a 32 bit number
            word = [1, 2**8, 2**16, 2**24]
            
            # Read the total packet length
            totalPacketLen = np.matmul(byteBuffer[8:8+4],word)
            
            # Check that all the packet has been read
            if (byteBufferLength >= totalPacketLen) and (byteBufferLength != 0):
                magicOK = 1
    
    
    # If magicOK is equal to 1 then process the message
    if magicOK:
        # word array to convert 4 bytes to a 32 bit number
        word = [1, 2**8, 2**16, 2**24]
        
        # Initialize the pointer index
        idX = 0
        
        # Read the header
        sync = byteBuffer[idX:idX+8]
        idX += 8
        totalPacketLen = np.matmul(byteBuffer[idX:idX+4],word)
        idX += 4
        platform = np.matmul(byteBuffer[idX:idX+4],word)
        idX += 4
        frameNumber = np.matmul(byteBuffer[idX:idX+4],word)
        idX += 4
        timeCpuCycles = np.matmul(byteBuffer[idX:idX+4],word)
        idX += 4
        numDetectedObj = np.matmul(byteBuffer[idX:idX+4],word)
        idX += 4
        numTLVs = np.matmul(byteBuffer[idX:idX+4],word)
        idX += 4
        
        # Read the TLV messages
        
            
            # word array to convert 4 bytes to a 32 bit number
        word = [1, 2**8, 2**16, 2**24]

            # Check the header of the TLV message
        
        tlv_type = np.matmul(byteBuffer[idX:idX+4],word)
        idX += 4
        tlv_length = np.matmul(byteBuffer[idX:idX+4],word)
        idX += 4
        if tlv_type == 8:
            i = 0
            v8s = []
            l = 0
            c = 0
            #range = getOccupDemoShortHeatMap(byteBuffer,idX,64,48)
            while(i < 6144):
                v8 = struct.unpack("h",byteBuffer[idX:idX + 2])
                v8s.append(v8[0])
                heatmap[l, c] = v8[0]
                idX += 2
                i +=2
                c += 1
                if c == heatmap_size[1]:
                    c = 0
                    l += 1
            tlv_type = np.matmul(byteBuffer[idX:idX+4],word)
        if tlv_type == 9:
            idX+=8
            decisionValue = byteBuffer[idX:idX + 2]
            idX+=2
            tlv_type = np.matmul(byteBuffer[idX:idX+4],word)       
        if tlv_type == 10:
                idX+=8
                unwrapped_waveform1 = struct.unpack("f",byteBuffer[idX:idX + 4])
                idX += 4
                heart_waveform1 = struct.unpack("f",byteBuffer[idX:idX + 4])
                idX += 4
                breathing_waveform1 = struct.unpack("f",byteBuffer[idX:idX + 4])
                idX += 4
                heart_rate1 = struct.unpack("f",byteBuffer[idX:idX + 4])
                idX += 4
                breathing_rate1 = struct.unpack("f",byteBuffer[idX:idX + 4])
                idX += 4
                unwrapped_waveform2 = struct.unpack("f",byteBuffer[idX:idX + 4])
                idX += 4
                heart_waveform2 = struct.unpack("f",byteBuffer[idX:idX + 4])
                idX += 4
                breathing_waveform2 = struct.unpack("f",byteBuffer[idX:idX + 4])
                idX += 4
                heart_rate2 = struct.unpack("f",byteBuffer[idX:idX + 4])
                idX += 4
                breathing_rate2 = struct.unpack("f",byteBuffer[idX:idX + 4])
                idX += 4
                dataOK = 1

                #print("HR1:{:.0f} BR1:{:.0f} HR2:{:.0f} BR2:{:.0f}".format(heart_rate1[0],breathing_rate1[0],heart_rate2[0],breathing_rate2[0]))
                if decisionValue[0] == 0 and decisionValue[1] == 0:
                    vitalSignsObj = {"heart1": 0, "breath1":0,
                    "unwrapped1":0,"heartwaveform1":0,"breathwaveform1":0,
                     "heart2":0,"breath2":0,
                     "unwrapped2":0,"heartwaveform2":0,"breathwaveform2":0}
                elif decisionValue[0] == 0 and decisionValue[1] == 1:
                    vitalSignsObj = {"heart1": 0, "breath1":0,
                    "unwrapped1":0,"heartwaveform1":0,"breathwaveform1":0,
                     "heart2":heart_rate2[0],"breath2":breathing_rate2[0],
                     "unwrapped2":unwrapped_waveform2[0],"heartwaveform2":heart_waveform2[0],
                     "breathwaveform2":breathing_waveform2[0]}                
                elif decisionValue[0] == 1 and decisionValue[1] == 0:
                    vitalSignsObj = {"heart1": heart_rate1[0], "breath1":breathing_rate1[0],
                    "unwrapped1":unwrapped_waveform1[0],"heartwaveform1":heart_waveform1[0],
                    "breathwaveform1":breathing_rate1[0],
                     "heart2":0,"breath2":0,
                     "unwrapped2":0,"heartwaveform2":0,"breathwaveform2":0}
                else:
                    vitalSignsObj = {"heart1": heart_rate1[0], "breath1":breathing_rate1[0],
                    "unwrapped1":unwrapped_waveform1[0],"heartwaveform1":heart_waveform1[0],
                    "breathwaveform1":breathing_rate1[0],
                    "heart2":heart_rate2[0],"breath2":breathing_rate2[0],
                    "unwrapped2":unwrapped_waveform2[0],"heartwaveform2":heart_waveform2[0],
                    "breathwaveform2":breathing_waveform2[0]} 
        
                
                
        # Remove already processed data
        if idX > 0 and byteBufferLength >= idX:
            shiftSize = totalPayloadSize_bytes
                    
            byteBuffer[:byteBufferLength - shiftSize] = byteBuffer[shiftSize:byteBufferLength]
            byteBuffer[byteBufferLength - shiftSize:] = np.zeros(len(byteBuffer[byteBufferLength - shiftSize:]),dtype = 'uint8')
            byteBufferLength = byteBufferLength - shiftSize
            
            # Check that there are no errors with the buffer length
            if byteBufferLength < 0:
                byteBufferLength = 0
                
    return vitalSignsObj, dataOK, heatmap
    
def update():
     
    dataOk = 0
    
      
    # Read and parse the received data
    vitalSignsObj, dataOk, heatmap = readAndParseVitalSigns(Dataport, configParameters)
    
    return vitalSignsObj, dataOk, heatmap   


# -------------------------    MAIN   -----------------------------------------  


# Get the configuration parameters from the configuration file
configParameters = parseConfigFile(configFileName)

   

    
    

  
    





