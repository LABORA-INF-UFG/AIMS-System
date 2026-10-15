import os
import cv2
import numpy as np
from ultralytics import YOLO
import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Point
from interfaces.msg import ArticulationPoints
from cv_bridge import CvBridge

class Pose_Estimation(Node):
    def __init__(self):
        super().__init__('Pose_Estimation')
        self.get_logger().info('Pose Estimation node initialized (YOLOv8n-pose version).')

        package_path = get_package_share_directory('weights')
        engine_path = os.path.join(package_path, 'models', 'yolov8n-pose.engine')
        pt_path = os.path.join(package_path, 'models', 'yolov8n-pose.pt')
        
        if os.path.exists(engine_path):
            model_path = engine_path
            self.get_logger().info(f'Using TensorRT engine: {model_path}')
        else:
            model_path = pt_path
            self.get_logger().info(f'TensorRT engine not found, using PyTorch model: {model_path}')
        
        # Load YOLO model
        self.model = YOLO(model_path, task='pose')
        
        self.Hz = 30
        self.publisher_ = self.create_publisher(ArticulationPoints, 'estimation_points', self.Hz)
        
        # Criação de um objeto da mensagem personalizada
        self.msg = ArticulationPoints()
        self.timer_ = self.create_timer(1./self.Hz, self.run_inference)
        
        self.articulation_names = ['nose', 'left eye', 'right eye', 'left ear', 'right ear', 'left shoulder',
                                'right shoulder', 'left elbow', 'right elbow', 'left wrist', 'right wrist',
                                'left hip', 'right hip', 'left knee', 'right knee', 'left ankle', 'right ankle']
            
        self.msg.name = [''] * len(self.articulation_names)
        self.msg.coordinates = [Point() for _ in range(len(self.articulation_names))]

        # Inicializa a captura de vídeo da webcam
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

        # Usa o formato MJPG
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        
        # Muda alguns parametros da camera
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 352)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 288)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        # Definir o tamanho do buffer como 1
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def run_inference(self):
        # Lê um frame do vídeo
        ret, frame = self.cap.read()

        if not ret or frame is None:
            self.get_logger().warn("Falha ao capturar frame da câmera!")
            return
            
        # Run inference using YOLOv8n-pose with imgsz=320 for performance
        # Explicitly set device=0 (GPU) to ensure TensorRT context is correctly created
        results = self.model(frame, verbose=False, imgsz=320, device=0)

        # Initialize points to zero
        for i in range(len(self.articulation_names)):
            self.msg.name[i] = self.articulation_names[i]
            p = Point()
            p.x = 0.0
            p.y = 0.0
            self.msg.coordinates[i] = p

        if results and len(results[0].keypoints.data) > 0:
            # Get boxes and keypoints
            boxes = results[0].boxes
            kpts_all_norm = results[0].keypoints.xyn # [N, 17, 2]
            confidences_all = results[0].keypoints.conf # [N, 17]

            principal_index = 0
            if len(boxes) > 1:
                # Find the box with the largest area (principal person)
                areas = boxes.xywh[:, 2] * boxes.xywh[:, 3]
                principal_index = int(np.argmax(areas.cpu().numpy()))
            
            # Select keypoints for the principal person
            kpts_norm = kpts_all_norm[principal_index].cpu().numpy()
            confidences = confidences_all[principal_index].cpu().numpy()

            for i in range(len(self.articulation_names)):
                x, y = kpts_norm[i]
                conf = confidences[i]
                
                aux = Point()
                if conf >= 0.4:
                    aux.x = float(x)
                    aux.y = float(y)
                else:
                    aux.x = 0.0
                    aux.y = 0.0
                
                self.msg.coordinates[i] = aux

        # Converter o frame para o formato sensor_msgs/Image
        bridge = CvBridge()
        image_msg = bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        
        self.msg.image = image_msg
        self.publisher_.publish(self.msg)
        

def main(args=None):
    rclpy.init(args=args)
    node = Pose_Estimation()
    rclpy.spin(node)
    
    node.destroy_node()
    rclpy.shutdown()

    node.cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()