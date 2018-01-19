import threading
import time
import copy
import cv2
from camera import Camera

class ClassifyCamera(Camera):
    def __init__(self, device_index, capture_fps, capture_size, classify_service):
        Camera.__init__(self, device_index, capture_fps, capture_size)
        self.__current_result_lock = threading.Lock()
        self.__current_result = None
        self.__classify_stop_flag = False
        self.__classify_thread = None
        self.__classify_service = classify_service

    def start(self):
        if self.__classify_thread:
            raise Exception('Classify thread has already been started')
        Camera.start(self)
        self.__classify_thread = threading.Thread(target=ClassifyCamera.__classify, args=(self, ))
        self.__classify_thread.start()

    def stop(self):
        if self.__classify_thread:
            self.__classify_stop_flag = True
            self.__classify_thread.join()
            self.__classify_thread = None
            Camera.stop(self)

    def __set_current_result(self, result):
        if self.__current_result_lock.acquire():
            self.__current_result = copy.deepcopy(result)
            self.__current_result_lock.release()

    def get_classify_result(self):
        if self.__current_result_lock.acquire():
            result = copy.deepcopy(self.__current_result)
            self.__current_result_lock.release()
            return result

    def __classify(self):
        self.__classify_stop_flag = False
        while not self.__classify_stop_flag:
            frame = Camera.get_frame(self)
            if frame is not None:
                result = self.__classify_service.classify(frame)
                if result is not None:
                    self.__set_current_result(result)
            else:
                print 'Classify is waiting image...'
                time.sleep(1)

    def get_frame(self):
        frame = Camera.get_frame(self)
        result = self.get_classify_result()
        cv2.putText(frame, result[0]['label'], (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        return frame
