import cv2
import time
import os
import datetime
import sys
import zmq
import threading
import copy
import json


VIDEO_URI = 'Please use your RTMP server link'
DETECT_SERVER_URI = 'tcp://10.245.55.97:5555'


g_current_frame_lock = threading.Lock()
g_current_frame = None
g_current_result_lock = threading.Lock()
g_current_result = None
g_exit = False


def set_current_frame(frame):
    global g_current_frame_lock, g_current_frame
    if g_current_frame_lock.acquire():
        g_current_frame = copy.deepcopy(frame)
        g_current_frame_lock.release()


def get_current_frame():
    global g_current_frame_lock, g_current_frame
    if g_current_frame_lock.acquire():
        if g_current_frame is None:
            temp_frame = None
        else:
            temp_frame = copy.deepcopy(g_current_frame)
        g_current_frame_lock.release()
        return temp_frame


def set_current_result(result):
    global g_current_result_lock, g_current_result
    if g_current_result_lock.acquire():
        g_current_result = copy.deepcopy(result)
        g_current_result_lock.release()


def get_current_result():
    global g_current_result_lock, g_current_result
    if g_current_result_lock.acquire():
        if g_current_result is None:
            temp_result = None
        else:
            temp_result = copy.deepcopy(g_current_result)
        g_current_result_lock.release()
        return temp_result


def detect():
    global g_exit
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(DETECT_SERVER_URI)
    while not g_exit:
        current_frame = get_current_frame()
        if current_frame is not None:
            req = cv2.imencode('.jpg', current_frame)[1].tobytes()
            socket.send(req)
            resp = socket.recv()
            set_current_result(json.loads(resp))
        else:
            time.sleep(1)


def play():
    global g_exit
    cap = cv2.VideoCapture(VIDEO_URI)
    if not cap.isOpened():
        print "Open video source failed."
        sys.exit(-1)
    fps = cap.get(cv2.cv.CV_CAP_PROP_FPS)
    size = (int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)),
            int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT)))
    interval = int(fps)
    print fps
    print size
    while True:
        ret, frame = cap.read()
        if ret:
            current_frame = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_CUBIC)
            set_current_frame(current_frame)
            current_result = get_current_result()
            if current_result is not None:
                draw_detect_result(current_frame, current_result)
            cv2.imshow('capture', current_frame)
            if cv2.waitKey(1000/int(fps)) & 0xFF == ord('q'):
                g_exit = True
                break
        else:
            print 'No frame, wait 1s'
            time.sleep(1)


def draw_detect_result(frame, result):
    for i in range(len(result)):
        pos = result[i]['position']
        p_tl = (int(pos['x']) - int(pos['width'] / 2), int(pos['y']) - int(pos['height'] / 2))
        p_br = (int(pos['x']) + int(pos['width'] / 2), int(pos['y']) + int(pos['height'] / 2))
        cv2.putText(frame, result[i]['category'], p_tl, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.rectangle(frame, p_tl, p_br, (0, 255, 0), 2)


if __name__ == '__main__':
    play_thread = threading.Thread(target=play)
    detect_thread = threading.Thread(target=detect)
    play_thread.start()
    detect_thread.start()
    play_thread.join()
    detect_thread.join()
