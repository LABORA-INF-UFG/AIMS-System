import rclpy
from rclpy.node import Node

from std_msgs.msg import String
from custom_interfaces.msg import BreathEstimate

import matplotlib.pyplot as plt

fig = plt.figure("AIMS - Breathing")
ax = fig.add_subplot()
fig.subplots_adjust(top=0.85)

class BreathPlotter(Node):

    def __init__(self):

        super().__init__('breath_plotter')

        self.subscription = self.create_subscription(
            BreathEstimate,
            'breath_estimate',
            self.listener_callback,
            10)
        self.subscription  # prevent unused variable warning

        #self.fig, self.ax = plt.subplots(1,2)

        plt.rcParams["figure.figsize"] = [8, 2]
        plt.rcParams["figure.autolayout"] = True

    def listener_callback(self, msg):

        plt.cla()
        
        ax.text(0, 0.5, "Breathing:", fontsize=20, bbox=dict(boxstyle = "square", facecolor = "white"))
        #ax.text(0.4, 0.5, "{:02d}".format(int(msg.breath_rate)), fontsize=20, bbox=dict(boxstyle = "square", facecolor = "white"))
        if not msg.apnea_detected:
            ax.text(0.4, 0.5, "{:02d}".format(int(msg.breath_rate)), fontsize=20, bbox=dict(boxstyle = "square", facecolor = "white"))
            ax.text(0.6, 0.5, "   Breathing   ", fontsize=20, bbox=dict(boxstyle = "square", facecolor = "green"))
        else:
            ax.text(0.4, 0.5, "{:02d}".format(0), fontsize=20, bbox=dict(boxstyle = "square", facecolor = "white"))
            ax.text(0.6, 0.5, "     Apnea     ", fontsize=20, bbox=dict(boxstyle = "square", facecolor = "red"))

        ax.grid(False)
        ax.axis('off')
        # self.ax[1].grid(False)
        # self.ax[1].axis('off')
        # plt.draw()
        # plt.show()
        
        # TODO subplots (amp and phase), split amplitude/phase to plot
        #splitted_phase = [msg.csi.phase[i * self.r:self.r + (i * self.r)] for i in range(self.n)]
        #plt.cla()
        #plt.plot(msg.breath_rate)
        #plt.text(0, 0.5, "Breathing:", fontsize=20, bbox=dict(boxstyle = "square", facecolor = "white"))
        #plt.tight_layout()
        plt.draw()
        plt.pause(0.01)
        
        #plt.show()
        plt.ioff()


def main(args=None):
    rclpy.init(args=args)
    minimal_subscriber = BreathPlotter() 

    #plt.ion()

    rclpy.spin(minimal_subscriber)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    minimal_subscriber.destroy_node()
    rclpy.shutdown()
    plt.ioff()

if __name__ == '__main__':
    main()