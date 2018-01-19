import numpy
import cv2

class ClassifyService:
    def __init__(self, movidius):
        self.__movidius = movidius

    def load_model(self, graph_filename, label_filename, means, dim):
        self.__labels = numpy.loadtxt(label_filename, str, delimiter='\t')
        self.__movidius.close_device()
        self.__movidius.open_device(graph_filename)
        self.__dim = dim
        self.__means = means

    def classify(self, image):
        tensor = cv2.resize(image, self.__dim)
        tensor = tensor.astype(numpy.float32)
        tensor[:,:,0] = (tensor[:,:,0] - self.__means[0])
        tensor[:,:,1] = (tensor[:,:,1] - self.__means[1])
        tensor[:,:,2] = (tensor[:,:,2] - self.__means[2])
        output, user_object = self.__movidius.get_result(tensor)
        sorted_output = output.argsort()[::-1]
        results = []
        for i in range(len(sorted_output)):
            label = self.__labels[sorted_output[i]]
            prob = output[sorted_output[i]]
            result = {
                'label': label,
                'prob': prob
                }
            results.append(result)
        return results

    def classify_by_file(self, image_filename):
        image = cv2.imread(image_filename)
        return self.classify(image)
