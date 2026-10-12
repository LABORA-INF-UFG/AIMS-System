import cv2
import numpy as np
import tensorflow as tf
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from std_msgs.msg import Bool
from cv_bridge import CvBridge
import os

class Pose_Estimation(Node):
    def __init__(self):
        super().__init__('Pose_Estimation')
        self.get_logger().info('Pose Etimation node initialized.')
        self.publisher_ = self.create_publisher(Bool, 'there_is_person', 10)
        # Create a message object
        self.msg = Bool()
        self.msg.data = False
        self.timer_ = self.create_timer(0.1, self.estimation_pose)
        self.articulation_names = ['nose', 'left eye', 'right eye', 'left ear', 'right ear', 'left shoulder',
                                'right shoulder', 'left elbow', 'right elbow', 'left wrist', 'right wrist',
                                'left hip', 'right hip', 'left knee', 'right knee', 'left ankle', 'right ankle']
        
        if 'AIMS' in os.environ:
            self.aims_var = os.environ['AIMS']
            
        
        self.interpreter = tf.lite.Interpreter(model_path=f"{self.aims_var}/resources/lite-model_movenet_singlepose_thunder_tflite_float16_4.tflite")
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        # Initialize the webcam video capture
        self.cap = cv2.VideoCapture(0)

        # Set the buffer size to 1
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    def estimation_pose(self):
        # Read a video frame
        ret, frame = self.cap.read()
        #frame = cv2.resize(frame, (self.screen_width, self.screen_height))

        # Resize the frame to the model input
        input_shape = self.input_details[0]['shape'][1:3]

        #input_shape = (256, 256)
        frame_resized = cv2.resize(frame, input_shape, interpolation=cv2.INTER_AREA)

        # Normalize the frame pixel values to the range [-1, 1]
        input_data = np.expand_dims(frame_resized, axis=0)
        input_data = (np.float32(input_data) - 127.5) / 127.5

        # Convert the normalized pixel values to UINT8
        input_data = np.uint8(input_data * 255)

        # Feed the normalized frame to the model and get the output
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])

        # Get the coordinates of the 17 pose keypoints and the measurement confidence
        keypoints = np.squeeze(output_data)

        Articulation_points = []
        # Keep only the "important" points to detect the person  
        # 'left shoulder', 'right shoulder', 'left elbow', 'right elbow', 
        # 'left wrist', 'right wrist','left hip', 'right hip', 'left knee', 'right knee'
        for point, i in zip(keypoints, range(0, 17)):
            if i >= 5 and i <= 14:
                aux = Point()
                y, x, confidence = point[0], point[1], point[2]
                if confidence >= 0.4:
                    aux.x = float(x)
                    aux.y = float(y)
                    Articulation_points.append(aux)


        # Adjust the camera so the frame can be plotted
        bridge = CvBridge()
        image_msg = bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        frame = np.array(image_msg.data, dtype=np.uint8).reshape((image_msg.height, image_msg.width, -1))
        height = image_msg.height
        width = image_msg.width

        # Mark the joint points on the frame
        for i in range(len(Articulation_points)):
            x, y = int(Articulation_points[i].x * width), int(Articulation_points[i].y * height)
            cv2.circle(frame, (x, y), 8, (0, 255, 0), -1)

        cv2.imshow('Pose Detection', frame)
        cv2.waitKey(1)

        is_person = None
        if len(Articulation_points) >= 7:
            is_person = True
        else:
            is_person = False

        if self.msg.data != is_person:
            self.msg.data = is_person
            self.publisher_.publish(self.msg)



def main(args=None):

    rclpy.init(args=args)
    node = Pose_Estimation()
    rclpy.spin(node)
    
    node.destroy_node()
    rclpy.shutdown()

    node.self.cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
