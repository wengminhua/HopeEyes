#coding=utf-8
import cv2
import threading
import time
import copy

class Camera:
    def __init__(self, device_index, capture_fps, capture_size):
        self.__device_index = device_index
        self.__current_frame_lock = threading.Lock()
        self.__current_frame = None
        self.__capture_fps = capture_fps
        self.__capture_size = capture_size
        self.__crop_rect = None
        self.__rotation = None
        self.__capture_stop_flag = False
        self.__capture_thread = None

    def set_crop_rect(self, x, y, width, height):
        if x is not None and y is not None and width is not None and height is not None:
            self.__crop_rect = (x, y, width, height)
        else:
            self.__crop_rect = None

    def set_rotation(self, angle):
        self.__rotation = angle

    def start(self):
        if self.__capture_thread:
            raise Exception('Capture thread has already been started')
        self.__capture_thread = threading.Thread(target=Camera.__capture, args=(self,))
        self.__capture_thread.start()

    def stop(self):
        if self.__capture_thread:
            self.__capture_stop_flag = True
            self.__capture_thread.join()
            self.__capture_thread = None

    def __set_frame(self, frame):
        if self.__current_frame_lock.acquire():
            self.__current_frame = copy.deepcopy(frame)
            self.__current_frame_lock.release()

    def get_frame(self):
        temp_frame = None
        if self.__current_frame_lock.acquire():
            if self.__current_frame is not None:
                temp_frame = copy.deepcopy(self.__current_frame)
            self.__current_frame_lock.release()
        return temp_frame

    def __capture(self):
        device = cv2.VideoCapture(self.__device_index)
        if not device.isOpened():
            raise Exception('Can not open device %d' % self.__device_index)
        original_size = (int(device.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)),
            int(device.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT)))
        self.__capture_stop_flag = False
        while not self.__capture_stop_flag:
            ret, frame = device.read()
            if ret:
                frame = self.__pre_process(frame)
                self.__set_frame(frame)
                time.sleep(float(1) / float(self.__capture_fps))
            else:
                raise Exception('Camera#%d read failed' % self.__device_index)

    def __pre_process(self, image):
        if self.__capture_size is not None:
            image = cv2.resize(image, self.__capture_size, interpolation=cv2.INTER_CUBIC)
        if self.__crop_rect is not None:
            rect_x = self.__crop_rect[0]
            rect_y = self.__crop_rect[1]
            rect_w = self.__crop_rect[2]
            rect_h = self.__crop_rect[3]
            image = image[rect_y:(rect_y+rect_h), rect_x:(rect_x+rect_w)]
        if self.__rotation is not None:
            (h, w) = image.shape[:2]
            center = (w/2, h/2)
            trans = cv2.getRotationMatrix2D(center, self.__rotation, scale=1.0)
            image = cv2.warpAffine(image, trans, (w, h))
        return image
