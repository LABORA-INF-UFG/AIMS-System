import cv2
import numpy as np


DISPLAY_TYPE = "adaptive"


class Plotter:
    def __init__(self, window_size: int, num_subcarriers: int):
        self.window_size = window_size
        self.nsub = num_subcarriers
        self.buffer_img = np.zeros((570, window_size, 3))

    def __del__(self):
        cv2.destroyAllWindows()

    def put_text(self, img):
        img = cv2.rectangle(img, (0,0), (25, 57*10), (0,0,0), -1)
        for i in range(self.nsub):
            img = cv2.putText(img, text=str(i), org=(5, 10*(i+1)), fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                              fontScale=0.4, color=(255,255,255), thickness=1, bottomLeftOrigin=False)
        return img

    def expand_image(self, image):
        new_img = np.zeros((self.nsub * 10, self.window_size), np.uint8)
        chunks = self.nsub  # number of subcarriers
        for i in range(chunks):  # expanding the size of each subcarrier -> each one 10 pixels high
            new_img[i*10:(i+1)*10, :] = image[i, :]
        return new_img

    def vec2image(self, vector, type:str = "mean"):
        """
        Transform a vector of arbitrary values into an image within the range [0, 255].
        It is a MinMax scaler operation at the end of the day.
        :param vector: np.ndarray
        :param type: str in ["mean", "abs", "iqr", "adaptive"]
        :return: np.ndarray
        """
        #print(f"Vector minimum {np.min(vector)}, vector maximum: {np.max(vector)}")

        if type == "mean":
            min = -38
            max = 38
        elif type == "abs":
            min = -70
            max = 68
        elif type == "iqr":
            min = -35
            max = 35
        elif type == "adaptive":
            Q1, Q3 = np.quantile(vector, [0.25, 0.75])
            IQR = Q3 - Q1
            min = (Q1 - 1.5 * IQR)
            max = Q3 + 1.5 * IQR
        else:
            raise ValueError(f"Invalid min/max type value: {type}")

        #################################################
        #array_min_max = [[max, min]] * vector.shape[0]  # this vector forces the min and max limits to appear in the values vector
        #vector = np.concatenate((vector, array_min_max), axis=1)  # note that the last 2 columns must be removed when plotting
        ###########################################################

        vector = (vector - min) / (max - min)
        vector = vector * 255
        return vector.astype(np.uint8)

    def update(self, phase_diff: np.ndarray, invariant=True):
        phase_diff = phase_diff.T[:, -1 * self.window_size:]
        img = self.vec2image(phase_diff, type=DISPLAY_TYPE)
        img = self.expand_image(img)  # expanding the number of image pixels along axis 0
        heatmap = cv2.applyColorMap(img, cv2.COLORMAP_HSV)
        if invariant:
            self.buffer_img = np.roll(self.buffer_img, (0, -20, 0), axis=(0, 1, 2))
            self.buffer_img[:, -20:, :] = heatmap[:, -22:, :]
            heatmap = self.put_text(self.buffer_img)

        else:
            heatmap = self.put_text(heatmap[:, :, :])

        # image = cv2.imread("/home/lffo/Pictures/Screenshots/1.png")
        # cv2.startWindowThread()
        # cv2.namedWindow('Heatmap')
        # cv2.imshow('Heatmap', heatmap)
        # cv2.waitKey(20)

        return heatmap