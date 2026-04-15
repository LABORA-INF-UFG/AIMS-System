from array import array
import os

from keras.models import load_model
import numpy as np
from scipy import signal
from scipy.signal import butter, lfilter
from sklearn.preprocessing import MinMaxScaler

from custom_interfaces.msg import PktCSI


class ApneaDetectionAI():
    def __init__(self,
                 freq: int = 100,
                 antennas: int = 3,
                 subcarriers: int = 57,
                 buffer_seconds: int = 15) -> None:
        self.freq = freq  # Readings per second
        self.buffer_seconds = buffer_seconds  # Buffer size in seconds
        self.antennas = antennas
        self.subcarriers = subcarriers
        self.is_buffer_full = False

        self.pkt_pos: int = 0

        # The algorithm needs the window to be transposed
        self.buffer = np.zeros((self.antennas * self.subcarriers,
                                self.buffer_seconds * self.freq),
                               dtype=np.complex128)

    def parse_pkt(self, raw_pkt: PktCSI) -> np.ndarray:
        """
        Parse a packet of CSI and return it as numpy array of complex numbers.

        Parameters:
            raw_pkt (PktCSI): The raw packet of CSI data.

        Returns:
            np.ndarray: The CSI data as a numpy array of complex numbers.
        """
        pkt = np.array([complex(real, imag) for real, imag in
                       zip(raw_pkt.csi.csi_real, raw_pkt.csi.csi_imag)])
        return pkt

    def add_to_buffer(self, pkt: np.ndarray) -> None:
        """
        Add a packet of CSI data to the buffer.

        If the buffer is not full, add the packet at the current position
        pointed by `self.pkt_pos`. Otherwise, shift the elements of the buffer
        to the left by one position and replace the oldest data with the new
        incoming data.

        Parameters:
            pkt (np.ndarray): A numpy array of complex numbers representing
                a packet of CSI data.

        Returns:
            None
        """
        if self.pkt_pos < self.buffer_seconds * self.freq:
            self.buffer[:, self.pkt_pos] = pkt
            self.pkt_pos += 1
        else:
            self.buffer[:, :-1] = self.buffer[:, 1:]  # Shift all to the left
            self.buffer[:, -1] = pkt  # Last position gets the new pkt
            self.is_buffer_full = True

    def applyConv(self, w, kernel) -> np.ndarray:
        # Pad the input array with zeros to ensure the output has the same
        # shape as the input array.
        pad_width = len(kernel) - 1
        padded_w = np.pad(w, ((0, 0), (pad_width, pad_width)), mode='constant')

        # Apply the convolution operation to the padded input array.
        output_matrix = np.apply_along_axis(
            lambda row: np.convolve(row, kernel, mode='valid'),
            axis=1,
            arr=padded_w)

        # Pad the output array with zeros to match the shape of the input array.
        pad_width_output = (0, 0), (0, 1)
        padded_output = np.pad(output_matrix, pad_width_output, mode='constant')

        return padded_output

    def diffPhaseCorrected(self,
                           buffer,
                           fix_val=True,
                           alpha=0.2,
                           sum=False,
                           conv=None,
                           takes_abs=False):
        """
        Input: data loaded like np.load(path + f)
        Ouput: data preprocessed for the difference of phases
        """
        a1, a2, a3 = buffer[:57], buffer[57:114], buffer[114:]

        # Phase difference
        diff1 = np.angle(np.conj(a1) * a2)
        diff2 = np.angle(np.conj(a2) * a3)
        diff3 = np.angle(np.conj(a1) * a3)

        # Unwrap it
        diff1 = np.unwrap(diff1, axis=0)
        diff2 = np.unwrap(diff2, axis=0)
        diff3 = np.unwrap(diff3, axis=0)

        # Scale
        scaler = MinMaxScaler()

        diff1 = scaler.fit_transform(diff1)
        diff2 = scaler.fit_transform(diff2)
        diff3 = scaler.fit_transform(diff3)

        # Fix the value problem
        if fix_val:
            def normalize(x): return (1 - (np.exp(-(x-0.5)**2)/0.2)/2)
            diff1 = normalize(diff1)
            diff2 = normalize(diff2)
            diff3 = normalize(diff3)

        # Subtract the mean
        diff1 = diff1 - np.mean(diff1, axis=0)
        diff2 = diff2 - np.mean(diff2, axis=0)
        diff3 = diff3 - np.mean(diff3, axis=0)

        # Apply convolution
        if conv is not None:
            kernel = [-1]*conv + [1]*conv
            diff1 = self.applyConv(diff1, kernel)
            diff2 = self.applyConv(diff2, kernel)
            diff3 = self.applyConv(diff3, kernel)

        # Concatenate and return
        if takes_abs:
            diff1 = abs(diff1)
            diff2 = abs(diff2)
            diff3 = abs(diff3)

        if sum:
            final = diff1 + diff2 + diff3
        else:
            final = np.concatenate((diff1, diff2, diff3), axis=0)
        return final

    def low_pass_filter(self, buffer, fc, fs):
        # Normalize the cutoff frequency
        w = fc / (fs / 2)

        # Create a first-order Butterworth low pass filter
        b, a = butter(1, w, 'low')

        # Apply the filter to the input signal
        filtered_signal = lfilter(b, a, buffer)
        return filtered_signal

    def process(self, buffer):
        '''
        First step:
        - Split first 15 seconds into 3 second window
        - Find the standard deviation for each window
        - Find the mean of the stds of the windows
        - Calculate threshold
        '''
        stds = []
        for small_window in np.array_split(buffer, 5):  # Get the 5 small 3 seconds of data windows
            stds.append(np.std(small_window))
        threshold = 1.2 * np.mean(stds)  # Find threshold

        '''
        Second step:
        - Create a moving windows
        - As it "grows", calculate the current standard deviation (curr_std) of the values in the window
        - If the curr_std passes the threshold, save the index,then "restart" the window at the next index
        '''
        curr_idx = 0
        cut_threshold_indices = []
        for i in range(1, len(buffer)):
            std = np.std(buffer[curr_idx:i])
            if std > threshold:
                curr_idx = i
                cut_threshold_indices.append(i)

        ''''
        Third step:
        - Split the array according to the indices found (if there were any)
        - Subtract from each value the mean of the window it was in
        - Concatenate every window
        '''
        # Split the array into windows based on the cut-off indices
        windows = np.split(buffer, cut_threshold_indices)

        # Subtract the mean of each window from the values in the window
        for i, window in enumerate(windows):
            windows[i] = window - np.mean(window)

        # Concatenate the windows into a final array of the same length
        final_array = np.concatenate(windows)
        return final_array

    def cardioFIPreProcessing(self, buffer):
        q = 10
        decimated = np.apply_along_axis(
            lambda x: signal.decimate(x, q),
            axis=1,
            arr=buffer)

        low_pass = np.apply_along_axis(
            lambda x: self.low_pass_filter(x, 2, 10),
            axis=1,
            arr=decimated)

        processed = np.apply_along_axis(
            lambda x: self.process(x),
            axis=1,
            arr=low_pass)

        return processed

    def pipeline(self, model):
        buffer = np.copy(self.buffer)
        buffer = self.diffPhaseCorrected(buffer)
        buffer = self.cardioFIPreProcessing(buffer)

        pred = model(np.array([buffer]), training=False)
        pred = pred.numpy()[0][0]
        return pred > 0.5


if __name__ == "__main__":
    test_pkt = PktCSI()
    test_pkt.csi.csi_real = array('d', [3.9999999999999933, 9.678325381427044, 11.999999999999998, 12.529279961717249, 10.000000000000005, 4.228522327246116, -1.9999999999999918, -5.253965813819814, -6.999999999999997, -8.27479476449793, -8.0, -8.138406967103169, -8.000000000000004, -6.8693759343559195, -4.000000000000016, -0.1645077205295024, 3.99999999999999, 6.9455585438999154, 8.999999999999995, 12.806740580371596, 15.0, 14.56544789129911, 12.000000000000009, 6.134274941073851, 1.5190572154519885e-14, -6.695714005218544, -13.999999999999988, -16.0, -18.200234752743462, -18.000000000000007, -16.960435082065526, -13.000000000000004, -5.223827135470437, 4.9999999999999805, 14.980926354592235, 23.999999999999964, 27.512675329261253, 26.000000000000004, 24.11618248620785, 17.000000000000014, 5.443948037076239, -10.000000000000025, -21.529316902628313, -29.999999999999947, -42.278996528434995, -47.00000000000001, -32.858340974453505, -14.000000000000083, 6.007264923381816, 25.99999999999995, 46.86641701015579, 59.0, 41.57495379188789, 16.000000000000032, -7.132590762023236, -33.00000000000001, -42.0, -28.0, -7.389817227521461, 13.000000000000004, 30.335582030507375, 41.99999999999999, 38.509871280556624, 24.99999999999998, 6.854763065249793, -8.000000000000007, -18.105919653108938, -23.000000000000004, -23.30769853083825, -20.0, -15.425850149426996, -8.000000000000012, -0.4646390685428799, 6.000000000000002, 10.315590098584977, 11.999999999999998, 15.17839761064522, 17.0, 15.180014311449986, 12.000000000000005, 8.234235426619097, 4.000000000000003, -0.924505544372351, -6.999999999999996, -10.000000000000007, -13.927863860104116, -15.999999999999998, -17.457165769627476, -16.000000000000004, -10.950273417660746, -4.000000000000007, 4.270163085442132, 11.999999999999988, 16.281009983166513, 16.999999999999996, 17.46358827768817, 15.000000000000009, 9.84513352489925, 2.999999999999987, -3.3851917307818464, -7.999999999999992, -14.019473781650916, -19.0, -17.213634350976903, -12.000000000000018, -6.571433881441528, -0.9999999999999923, 4.08488165579183, 8.999999999999998, 11.645801540005445, 11.000000000000004, 10.952590217971279, 8.999999999999991, 2.0000000000000204, -11.999999999999988, 0.5555211621736986, 12.000000000000004, 23.87397848835588, 30.0, 22.737883386946738, 7.9999999999999964, -7.280035926053317, -18.000000000000014, -25.05988497598397, -25.999999999999996, -19.893195358174353, -9.999999999999991, 1.5160534174048552, 15.000000000000004, 23.92576096058124, 28.000000000000004, 24.410114385886406, 16.999999999999996, 10.215606824649182, -4.95981953654678e-15, -11.395570380758803, -20.000000000000007, -22.582430604742953, -19.999999999999996, -16.55083792082408, -10.000000000000002, -1.0000000000000016, 6.262142625615772, 11.999999999999995, 15.506498303364076, 17.0, 14.772555690454217, 10.000000000000004, 3.132906880268835, -3.9999999999999964, -8.435980457160856, -10.000000000000004, -10.295546745027652, -7.999999999999994, -5.384453142671009, -2.0000000000000013, 1.777230585221041, 5.00000000000001, 7.809118602974204, 6.999999999999999, 3.648960223219672, 1.0000000000000009, -1.4607818031736246, -4.000000000000001, -4.6069164705183825, -1.9999999999999936, 1.7515465202097187, 4.000000000000001, 5.697075829613201, 4.999999999999998, -8.57686045848759e-15])
    test_pkt.csi.csi_imag = array('d', [14.000000000000004, 9.361089890074066, 3.0000000000000084, -3.1182067171793797, -8.999999999999996, -12.091517654051543, -11.999999999999998, -9.312687195350893, -6.000000000000003, -2.488562531610145, 0.9999999999999923, 2.464111359587161, 3.9999999999999942, 7.707573132037175, 10.999999999999995, 12.175793990667435, 12.000000000000005, 9.81683462336708, 7.000000000000004, 3.4651581409452508, -1.9999999999999818, -7.563764315797917, -12.999999999999991, -15.689331376796986, -16.0, -16.987162511431563, -15.000000000000014, -8.000000000000004, -1.7590462014036468, 4.9999999999999805, 12.129894296749924, 18.999999999999996, 24.693909212502227, 27.000000000000004, 24.871449947332746, 19.000000000000043, 7.274639570827075, -3.9999999999999667, -15.532185225414302, -25.99999999999999, -34.26624173751659, -36.99999999999999, -30.671799908414116, -21.000000000000075, -6.84947585160514, 13.999999999999956, 31.094595057756994, 38.99999999999997, 42.4994916302098, 36.00000000000003, 21.995653171957816, -4.0000000000000275, -30.517843985521836, -40.99999999999998, -48.18740693694089, -41.999999999999986, -13.000000000000005, 29.000000000000007, 37.16217103384205, 33.0, 24.54813095233166, 6.999999999999992, -14.648982570243922, -31.000000000000007, -33.78412907929759, -28.0, -19.906947891403473, -8.999999999999991, 0.5812536810331919, 8.999999999999998, 16.613165170742946, 21.999999999999996, 21.662146802248408, 19.0, 13.730214905939025, 8.000000000000004, 4.113015613540694, -1.0000000000000016, -6.005907495919294, -10.0, -12.645802416044901, -14.000000000000002, -16.446534021831344, -17.000000000000007, -11.999999999999996, -7.612562001445705, -2.0000000000000058, 4.636002400529761, 11.999999999999995, 17.553264520959967, 21.0, 21.077223614466995, 18.00000000000001, 10.637345052369861, 3.000000000000014, -4.071272119766702, -10.999999999999984, -16.154651310253495, -19.000000000000004, -16.914436860023685, -13.000000000000005, -10.399648038165596, -4.999999999999996, 3.8259445507474816, 9.999999999999984, 12.733791803176702, 13.000000000000002, 12.998808289122639, 11.000000000000004, 4.885421609602231, -0.9999999999999778, -5.485511353731791, -10.00000000000001, -9.999999999999996, 19.000000000000007, 21.633297115468483, 17.0, 9.518104835015507, -6.000000000000006, -21.51705115951177, -31.0, -28.168520980306166, -18.999999999999986, -8.060960004745835, 5.000000000000018, 15.666090524279468, 22.0, 26.617285382092323, 24.999999999999993, 15.886111072848907, 3.999999999999996, -7.298678408148245, -15.0, -22.637525185420692, -27.0, -23.709906885488742, -15.999999999999991, -4.928631009808944, 5.000000000000022, 12.99564713067995, 19.0, 16.0, 14.53421470076088, 10.000000000000009, 5.104142407215241, -1.0000000000000016, -7.821313825640616, -12.999999999999995, -15.652239219905773, -15.000000000000002, -10.349734707467096, -4.999999999999993, 0.4891574340363462, 5.00000000000001, 7.61552155682783, 9.000000000000002, 8.731907670420684, 6.999999999999993, 2.185027540558845, -3.0000000000000044, -3.9656883221142007, -3.0, -3.5266392408895886, -1.999999999999998, 1.751546520209711, 5.0000000000000036, 4.60691647051838, 1.9999999999999984, -0.924508135431461, -5.000000000000002, -7.0])

    apn = ApneaDetectionAI()
    model = load_model(os.getenv('KERAS_APNEA_MODEL'))
    for i in range(1550):
        parsed_data = apn.parse_pkt(test_pkt)
        apn.add_to_buffer(parsed_data)
        if apn.is_buffer_full:
            print(apn.pipeline(model))
