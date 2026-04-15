import os
import serial
import time
import numpy as np


# Change the configuration file name
configFileName = os.getenv('AIMS') + f'/aims_ws/src/csi/csi/resource/xwr1642_profile_VitalSigns_20fps_Front.cfg'
CLIport = serial.Serial('/dev/ttyACM0', 115200)
Dataport = serial.Serial('/dev/ttyACM1', 921600)
byteBuffer = np.zeros(2**15,dtype = 'uint8')
byteBufferLength = 0

def serialConfig(configFileName):
    
    global CLIport
    global Dataport
    # Open the serial ports for the configuration and the data ports
    
    # Raspberry pi
    
    
    # Windows
    #CLIport = serial.Serial('COM3', 115200)
    #Dataport = serial.Serial('COM4', 921600)

    # Read the configuration file and send it to the board
    config = [line.rstrip('\r\n') for line in open(configFileName)]
    for i in config:
        CLIport.write((i+'\n').encode())
        print(i)
        time.sleep(0.01)
        
    return CLIport, Dataport


CLIport, Dataport = serialConfig(configFileName)
