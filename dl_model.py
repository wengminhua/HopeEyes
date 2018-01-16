from mvnc import mvncapi as mvnc
import cv2
import numpy
import time

class DLModel(object):
    def __init__(self):
        mvnc.SetGlobalOption(mvnc.GlobalOption.LOG_LEVEL, 2)
        devices = mvnc.EnumerateDevices()
        if len(devices) == 0:
            print('No device found')
            quit()
        self.device = mvnc.Device(devices[0])
        self.graph = None

        # traffic light
        # read mean file
        self.traffic_dim = (227, 227)
        self.traffic_mean = (81.1, 88.5, 90.3)
        # read label file
        traffic_labelfile = 'traffic_label.txt'
        self.traffic_labels = numpy.loadtxt(traffic_labelfile, str, delimiter='\t')
        # Load graph
        self.traffic_light_model = 'traffic_light_graph'


        # object detection
        # read mean file
        self.detection_dim = (300, 300)
        self.detection_mean = (127.5, 127.5, 127.5)
        # read label file
        detection_labelfile = 'detection_label.txt'
        self.detection_labels = numpy.loadtxt(detection_labelfile, str, delimiter='\t')
        # Load graph
        self.object_detection_model = 'object_deteciton_graph'
        
    def init_traffic_light_mode(self):
        self.init_device()
        with open(self.traffic_light_model, mode='rb') as f:
            traffic_blob = f.read()
        self.graph = self.device.AllocateGraph(traffic_blob)
    
    def init_object_detection_mode(self):
        self.init_device()
        with open(self.object_detection_model, mode='rb') as f:
            detection_blob = f.read()
        self.graph = self.device.AllocateGraph(detection_blob)

    def predict_traffic_light(self, pic):
        img = self.read_image(pic, self.traffic_dim, self.traffic_mean)
        self.graph.LoadTensor(img.astype(numpy.float16), 'user object')
        output, userobj = self.graph.GetResult()
        order = output.argsort()[::-1]
        results = []
        for i in range(3):
            label = self.traffic_labels[order[i]]
            prob = output[order[i]]
            results.append((label, prob))
        print(results)
        # 3 classes
        return results

    def object_detection(self, pic):
        img = self.read_image(pic, self.detection_dim, self.detection_mean)
        # adjust values to range between -1.0 and + 1.0
        img = img * 0.007843
        self.graph.LoadTensor(img.astype(numpy.float16), 'user object')
        output, userobj = self.graph.GetResult()
        # number of boxes returned
        num_valid_boxes = int(output[0])
        print('total num boxes: ' + str(num_valid_boxes))
        objects = []
        for box_index in range(num_valid_boxes):
            base_index = 7+ box_index * 7
            if (not numpy.isfinite(output[base_index]) or
                    not numpy.isfinite(output[base_index + 1]) or
                    not numpy.isfinite(output[base_index + 2]) or
                    not numpy.isfinite(output[base_index + 3]) or
                    not numpy.isfinite(output[base_index + 4]) or
                    not numpy.isfinite(output[base_index + 5]) or
                    not numpy.isfinite(output[base_index + 6])):
                # boxes with non infinite (inf, nan, etc) numbers must be ignored
                #print('box at index: ' + str(box_index) + ' has nonfinite data, ignoring it')
                continue

            x1 = int(output[base_index + 3] * img.shape[0])
            y1 = int(output[base_index + 4] * img.shape[1])
            x2 = int(output[base_index + 5] * img.shape[0])
            y2 = int(output[base_index + 6] * img.shape[1])

            if (x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0):
                #print('box at index: ' + str(box_index) + ' has coordinate < 0, ignoring it')
                continue

            if (x1 > img.shape[0] or y1 > img.shape[1] or
                x2 > img.shape[0] or y2 > img.shape[1] ):
                #print('box at index: ' + str(box_index) + ' has coordinate out of bounds, ignoring it')
                continue

            x1_ = str(x1)
            y1_ = str(y1)
            x2_ = str(x2)
            y2_ = str(y2)

            label = self.detection_labels[int(output[base_index + 1])]
            prob = str(output[base_index + 2]*100)

            print('box at index: ' + str(box_index) + ' : ClassID: ' + label + '  '
                  'Confidence: ' + prob + '%  ' +
                  'Top Left: (' + x1_ + ', ' + y1_ + ')  Bottom Right: (' + x2_ + ', ' + y2_ + ')')
            objects.append((label, (x1_, y1_, x2_, y2_)))
        return objects


    def read_image(self, pic, dim, mean):
        img = cv2.imread(pic)
        img = cv2.resize(img, dim)
        img = img.astype(numpy.float32)
        img[:,:,0] = (img[:,:,0] - mean[0])
        img[:,:,1] = (img[:,:,1] - mean[1])
        img[:,:,2] = (img[:,:,2] - mean[2])
        return img
    
    def init_device(self):
        if self.graph:
            self.close_device()
        time.sleep(0.7)
        self.device.OpenDevice()

    def close_device(self):
        self.graph.DeallocateGraph()
        self.device.CloseDevice()



if __name__ == '__main__':
    model = DLModel()

    model.init_traffic_light_mode()
    model.predict_traffic_light('red2.PNG')
    
    model.init_object_detection_mode()
    model.object_detection('../../data/images/nps_chair.png')

    model.close_device()


