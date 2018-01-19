from mvnc import mvncapi as mvnc
import Queue
import threading
import numpy
import time

class Movidius:
    def __init__(self, device_index):
        mvnc.SetGlobalOption(mvnc.GlobalOption.LOG_LEVEL, 2)
        devices = mvnc.EnumerateDevices()
        if len(devices) <= 0:
            raise Exception('No Movidius device found.')
        if device_index > (len(devices) - 1):
            raise Exception('Movidius device %d does not exists' % device_index)
        self.__device_index = device_index
        self.__device = mvnc.Device(devices[device_index])
        self.__graph = None
        self.__predict_queue = Queue.Queue(50)
        self.__predict_event = None
        self.__predict_thread = None
        self.__stop_flag = False

    def open_device(self, graph_filename):
        if self.__predict_thread is not None:
            raise Exception('Movidius device %d is already opened' % device_index)
        self.__device.OpenDevice()
        with open(graph_filename, mode='rb') as f:
            graph_blob = f.read()
        self.__graph = self.__device.AllocateGraph(graph_blob)
        self.__predict_event = threading.Event()
        self.__predict_thread = threading.Thread(target=Movidius.__predict, args=(self,))
        self.__predict_thread.start()

    def close_device(self):
        if self.__predict_thread is not None:
            self.__stop_flag = True
            self.__predict_event.set()
            self.__predict_thread.join()
            self.__graph.DeallocateGraph()
            self.__device.CloseDevice()
            time.sleep(1)
            self.__graph = None
            self.__predict_thread = None

    def get_result(self, tensor):
        if self.__predict_thread is None:
            raise Exception('Movidius device %d has not been inited' % device_index)
        event = threading.Event()
        data = {
            'input': tensor,
            'output': None,
            'user_object': None
            }
        predict_handler = {
            'event': event,
            'data': data
            }
        self.__predict_queue.put(predict_handler)
        self.__predict_event.set()
        event.wait()
        event.clear()
        return (data['output'], data['user_object'])

    def __predict(self):
        self.__stop_flag = False
        while not self.__stop_flag:
            if self.__predict_queue.empty():
                self.__predict_event.wait()
                self.__predict_event.clear()
                continue
            predict_handler = self.__predict_queue.get()
            self.__graph.LoadTensor(predict_handler['data']['input'].astype(numpy.float16), 'user object')
            output, user_object = self.__graph.GetResult()
            predict_handler['data']['output'] = output
            predict_handler['data']['user_object'] = user_object
            predict_handler['event'].set()
