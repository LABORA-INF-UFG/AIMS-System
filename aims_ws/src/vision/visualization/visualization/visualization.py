import rclpy
from rclpy.node import Node
from interfaces.msg import ArticulationPoints
from sensor_msgs.msg import Image
import cv2
import numpy as np
import time
from cv_bridge import CvBridge

class Visualization(Node):
    def __init__(self):
        super().__init__('Visualization')
        self.get_logger().info('Pose Etimation node initialized.')
        self.Hz = 30

        self.subscriber = self.create_subscription(ArticulationPoints, '/estimation_points', self.callback, self.Hz)
        self.publisher_ = self.create_publisher(Image, 'visao_image', self.Hz)
        
        self.bridge = CvBridge()
        self.msg = Image()
        self.frame = None


    def plot_lines(self, points, beginning, end, step, increment):
        for i in range(beginning, end, step):
                point1 = points[i]
                point2 = points[i + increment]
                
                if point1[0] != 0 and point1[1] != 0 and point2[0] != 0 and point2[1] != 0:
                    cv2.line(self.frame, point1, point2, (0, 255, 0), 2)

    def callback(self, msg):

        """
        Function description.

        This function receivs a message from the /estimation_points topic 
        and aims to place the join points within the obtained frame.
        
        
        Args:
            msg (interfaces.msg.ArticulationPoints): Has the obtained a list
            of points containing tuples with the join points
            
        Returns:
            /visao_image (std_msgs.msg.Image): it publishes the frame in /visao_image 
            topic

        """

        # Obtém o frame, a largura e a altura do quadro de captura
        self.frame = self.bridge.imgmsg_to_cv2(msg.image, desired_encoding="bgr8")
        
        if self.frame is None:
            return
            
        height = msg.image.height
        width = msg.image.width
        

        points = []
        size = len(msg.name)
        for i in range(size):
            if i >= 5 and i <= 14:
                x, y = int(msg.coordinates[i].x * width), int(msg.coordinates[i].y * height)
                
                points.append((x,y))
                if x != 0 or y != 0:
                    # Desenha um círculo em cada ponto de referência na imagem original
                    cv2.circle(self.frame, (x, y), 8, (0, 255, 0), -1)

        # Traça as linhas entre os pontos da cabeça
        #self.plot_lines(frame, points, 0, 4, 1, 1)
        # Traça as linhas entre a parte esquerda do corpo
        self.plot_lines(points, 0, len(points) - 2, 2, 2)
        # Traça as linhas entre a parte direta do corpo
        self.plot_lines(points, 1, len(points) -2 , 2, 2)
        # Traça algumas linhas entre a parte direta-esquerda do corpo
        self.plot_lines(points, 0, 7, 2, 1)
        
        image_msg = self.bridge.cv2_to_imgmsg(self.frame, encoding="bgr8")
        self.publisher_.publish(image_msg)

        cv2.imshow('Pose Detection', self.frame)
        cv2.waitKey(1)

def main(args=None):
    rclpy.init(args=args)
    node = Visualization()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__== '__main__':
    main()