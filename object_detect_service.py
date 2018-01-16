import numpy

class ObjectDetectService:
    def __init__(self, movidius):
        self.__movidius = movidius

    def load_model(self, graph_filename, label_filename, means, dim):
        self.__labels = numpy.loadtxt(label_filename, str, delimiter='\t')
        self.__movidius.close_device()
        self.__movidius.open_device(graph_filename)
        self.__dim = dim
        self.__means = means

    def detect_objects(self, image):
        tensor = image.astype(numpy.float32)
        tensor[:,:,0] = (tensor[:,:,0] - self.__means[0])
        tensor[:,:,1] = (tensor[:,:,1] - self.__means[1])
        tensor[:,:,2] = (tensor[:,:,2] - self.__means[2])
        # adjust values to range between -1.0 and + 1.0
        tensor = tensor * 0.007843
        output, user_object = self.__movidius.get_result(tensor)
        # number of boxes returned
        num_valid_boxes = int(output[0])
        # print('total num boxes: ' + str(num_valid_boxes))
        objects = []
        for box_index in range(num_valid_boxes):
            base_index = 7 + box_index * 7
            if (not numpy.isfinite(output[base_index]) or
                    not numpy.isfinite(output[base_index + 1]) or
                    not numpy.isfinite(output[base_index + 2]) or
                    not numpy.isfinite(output[base_index + 3]) or
                    not numpy.isfinite(output[base_index + 4]) or
                    not numpy.isfinite(output[base_index + 5]) or
                    not numpy.isfinite(output[base_index + 6])):
                # boxes with non infinite (inf, nan, etc) numbers must be ignored
                # print('box at index: ' + str(box_index) + ' has nonfinite data, ignoring it')
                continue

            x1 = int(output[base_index + 3] * tensor.shape[0])
            y1 = int(output[base_index + 4] * tensor.shape[1])
            x2 = int(output[base_index + 5] * tensor.shape[0])
            y2 = int(output[base_index + 6] * tensor.shape[1])

            if (x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0):
                # print('box at index: ' + str(box_index) + ' has coordinate < 0, ignoring it')
                continue

            if (x1 > tensor.shape[0] or y1 > tensor.shape[1] or
                x2 > tensor.shape[0] or y2 > tensor.shape[1] ):
                # print('box at index: ' + str(box_index) + ' has coordinate out of bounds, ignoring it')
                continue

            label = self.__labels[int(output[base_index + 1])]
            prob = str(output[base_index + 2] * 100)
            position = {
                'x': x1,
                'y': y1,
                'width': x2 - x1,
                'height': y2 - y1
                }
            # print('box at index: ' + str(box_index) + ' : ClassID: ' + label + '  '
            #       'Confidence: ' + prob + '%  ' +
            #       'Top Left: (' + x1_ + ', ' + y1_ + ')  Bottom Right: (' + x2_ + ', ' + y2_ + ')')
            objects.append({
                'label': label,
                'position': position,
                'prob': prob
                })
        return objects
