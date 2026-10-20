import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import custom_interfaces.msg as PktMmW
from csi.libs.VitalSignRead import update
import numpy as np
import cv2

class MmWPublisher(Node):

	def __init__(self):
		super().__init__('pkt_mmw_publisher')
		self.publisher_br = self.create_publisher(PktMmW.MmWVitalSignal, 'brmmw', 10)
		self.publisher_hr = self.create_publisher(PktMmW.MmWVitalSignal, 'hrmmw', 10)
		self.publisher_heatmap = self.create_publisher(Image, 'heatmapmmw', 10)
		timer_period = 0.03 #0.03  # seconds
		self.timer = self.create_timer(timer_period, self.timer_callback)
		self.i = 0
		

	def timer_callback(self):
		#config = parseConfigFile(configFileName)
		#vitalsignsobj, dataOK = readAndParseVitalSigns(Dataport,config)
		# ==========================
		
		vitalsignsobj, dataOk, heatmap  = update()

		#self.get_logger().info('Got heatmap: "%s"' % dataOk)
		
		if dataOk:
			pkthr = PktMmW.MmWVitalSignal()
			pktbr = PktMmW.MmWVitalSignal()
			hr = float(vitalsignsobj["heart1"])
			pkthr.rate = hr
			br = float(vitalsignsobj["breath1"])
			pktbr.rate = br
			self.publisher_hr.publish(pkthr)
			self.publisher_br.publish(pktbr)
			#self.get_logger().info('Heart rate: "%s"' % hr)
			#self.get_logger().info('Breathing rate: "%s"' % br)

			make_figure = True
			if make_figure:
				normed = cv2.normalize(heatmap[:, ::-1], None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)		
				color = cv2.applyColorMap(normed, cv2.COLORMAP_JET)

				# GREEN or RED represented as BGR tuples
				box_color = (0, 255, 0) if hr > 0.0 else (0, 0, 255)
				# Box starting points : (col, row)
				#box1 = np.array([11, 17])
				box2 = np.array([30, 17])
				#heatmap_w_rect = cv2.rectangle(color, box1-1, box1+7+1, box_color, 1)
				heatmap_w_rect = cv2.rectangle(color, box2-1, box2+7+1, box_color, 1)

				scale_factor = 4
				heatmap_w_rect = cv2.resize(heatmap_w_rect, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)

				success, encoded_image = cv2.imencode('.png', heatmap_w_rect)
				if success:
					image_msg = Image()
					image_msg.header.frame_id = str(self.i)
					image_msg.encoding = 'bgr8'
					image_msg.height = 64 * scale_factor
					image_msg.width = 48 * scale_factor
					image_msg.data = encoded_image.tobytes()
					self.publisher_heatmap.publish(image_msg)
					#self.get_logger().info('MMWave heatmap published.')
				else:
					self.get_logger().error('Failed to encode image.')

				# === Offline visualization ===
				# cv2.namedWindow("w", cv2.WINDOW_NORMAL)
			
				# # Using resizeWindow()
				# #cv2.resizeWindow("w", 384, 512)
				# # Displaying the image
				# cv2.imshow("w", heatmap_w_rect)
				# cv2.waitKey(0)
				# cv2.destroyAllWindows()
		
				#self.get_logger().info('Publishing MmW signal: "%s"' % self.i)
				self.i += 1


def main(args=None):
	
	rclpy.init(args=args)
	minimal_publisher = MmWPublisher()

	rclpy.spin(minimal_publisher)

	minimal_publisher.destroy_node()
	rclpy.shutdown()


if __name__ == '__main__':
	main()
