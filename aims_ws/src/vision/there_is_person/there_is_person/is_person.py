import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from interfaces.msg import ArticulationPoints
import numpy as np

class Person_Detection(Node):
    def __init__(self):
        super().__init__('Person_Detection')
        self.get_logger().info('Person Detection node initialized.')

        self.Hz = 30
        self.publisher_ = self.create_publisher(Bool, 'there_is_person', self.Hz)
        self.callback = self.create_subscription(ArticulationPoints, '/estimation_points', self.person_detection, self.Hz)
        self.msg = Bool()
        self.msg.data = False

    def person_detection(self, msg):
        """
        Function description.

        This function receivs a message from the /estimation_points topic 
        and checks whether a person has been detected. This verification is
        done throught numbers of points detected and standard deviation.
        
        
        Args:
            msg (interfaces.msg.ArticulationPoints): Has the obtained a list
            of points containing tuples with the join points
            
        Returns:
            /there_is_person (std_msgs.msg.Bool): it publishes a boolean message in
            "/there_is_person" topic if a person was detected 

        """

        points = []
        
        Articulation_points = 0
        # Pega somente os pontos "importantes" para fazer a deteção da pessoa  
        # 'left shoulder', 'right shoulder', 'left elbow', 'right elbow', 
        # 'left wrist', 'right wrist','left hip', 'right hip', 'left knee', 'right knee'
        for i in range(0, 17):
            if i >= 5 and i <= 14:
                x, y = msg.coordinates[i].x, msg.coordinates[i].y

                if x != 0.0 or y != 0.0:
                    point = (x,y)
                    points.append(point)
                    Articulation_points+=1

        std_y = 0.0
        std_x = 0.0
        if Articulation_points >= 6:
            x_array = np.array([x for x, y in points])
            y_array = np.array([y for x, y in points])
            
            std_x = np.std(x_array)
            std_y = np.std(y_array)



        is_person = None
        if Articulation_points >= 6 and std_x >= 0.045 and std_y >= 0.045:
            is_person = True
        else:
            is_person = False

        if self.msg.data != is_person:
            self.msg.data = is_person
            self.publisher_.publish(self.msg)



def main(args=None):

    rclpy.init(args=args)
    node = Person_Detection()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()



if __name__ == '__main__':
    main()