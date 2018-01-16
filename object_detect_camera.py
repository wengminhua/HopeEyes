import threading
import time
import copy
from camera import Camera

class ObjectDetectCamera(Camera):
    def __init__(self, device_index, capture_fps, capture_size, result_cache_size, detect_service):
        Camera.__init__(self, device_index, capture_fps, capture_size)
        self.__result_cache_size = result_cache_size
        self.__result_cache_lock = threading.Lock()
        self.__result_cache = []
        self.__detect_stop_flag = False
        self.__detect_thread = None
        self.__detect_service = detect_service

    def start(self):
        if self.__detect_thread:
            raise Exception('Detect thread has already been started')
        Camera.start(self)
        self.__detect_thread = threading.Thread(target=ObjectDetectCamera.__detect, args=(self, ))
        self.__detect_thread.start()

    def stop(self):
        if self.__detect_thread:
            self.__detect_stop_flag = True
            self.__detect_thread.join()
            self.__detect_thread = None
            Camera.stop(self)

    def __push_result_into_cache(self, result):
        if self.__result_cache_lock.acquire():
            temp_result = copy.deepcopy(result)
            index = -1
            if len(self.__result_cache) >= self.__result_cache_size:
                self.__result_cache = self.__result_cache[1:]
            self.__result_cache.append(temp_result)
            self.__result_cache_lock.release()

    def get_detect_result(self, size):
        temp_result = []
        if self.__result_cache_lock.acquire():
            for index in range(size):
                if len(self.__result_cache) > index:
                    temp_result.append(copy.deepcopy(self.__result_cache[-1 * (index + 1)]))
            self.__result_cache_lock.release()
        return temp_result

    def __detect(self):
        self.__detect_stop_flag = False
        while not self.__detect_stop_flag:
            frame = Camera.get_frame(self)
            if frame is not None:
                result = self.__detect_service.detect_objects(frame)
                if result is not None:
                    self.__push_result_into_cache(result)
            else:
                print 'Detector is waiting image...'
                time.sleep(1)

    def get_frame(self):
        frame = Camera.get_frame(self)
        result = self.get_detect_result(1)[0]
        for i in range(len(result)):
            pos = result[i]['position']
            p_tl = (int(pos['x']) - int(pos['width'] / 2), int(pos['y']) - int(pos['height'] / 2))
            p_txt = (int(pos['x']) - int(pos['width'] / 2), int(pos['y']) - int(pos['height'] / 2)-4)
            p_br = (int(pos['x']) + int(pos['width'] / 2), int(pos['y']) + int(pos['height'] / 2))
            cv2.putText(frame, result[i]['label'], p_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.rectangle(frame, p_tl, p_br, (0, 255, 0), 2)
        return frame
