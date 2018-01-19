#coding=utf-8
import cv2
import time
import os
import datetime
import sys
import threading
import copy
import json
import math
from movidius import Movidius
from object_detect_camera import ObjectDetectCamera
from object_detect_service import ObjectDetectService
from classify_camera import ClassifyCamera
from classify_service import ClassifyService
from flask import Flask, jsonify, render_template, Response

g_app = Flask('Hopeye')
g_left_camera = None
g_right_camera = None

@g_app.route('/')
def index():
    return render_template('index.html')

def video_stream(camera):
    while True:
        frame = camera.get_frame()
        binary_frame = cv2.imencode('.jpg', frame)[1].tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + binary_frame + b'\r\n')
        time.sleep(float(1) / float(24))

@g_app.route('/camera/stream/left')
def camera_stream_left():
    global g_left_camera
    return Response(video_stream(g_left_camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@g_app.route('/camera/stream/right')
def camera_stream_right():
    global g_right_camera
    return Response(video_stream(g_right_camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@g_app.route('/api/traffic_light')
def get_traffic_light():
    camera = get_working_camera()
    result = camera.get_classify_result()
    return jsonify({
        'result': result[0]['label']
    })

def get_working_camera():
    global g_left_camera, g_right_camera
    if g_left_camera is not None:
        return g_left_camera
    if g_right_camera is not None:
        return g_right_camera

if __name__ == '__main__':
    movidius = Movidius(0)
    # object_detect_service = ObjectDetectService(movidius)
    # object_detect_service.load_model('./models/object_detect.graph',
    #     './models/object_detect_labels.txt',
    #     (127.5, 127.5, 127.5),
    #     (300, 300))
    # g_left_camera = ObjectDetectCamera(0, 24, (640, 480), 500, object_detect_service)
    # g_left_camera.start()
    classify_service = ClassifyService(movidius)
    classify_service.load_model('./models/traffic_light.graph',
        './models/traffic_light_labels.txt',
        (81.1, 88.5, 90.3),
        (227, 227))
    g_left_camera = ClassifyCamera(0, 24, (640, 480), classify_service)
    # g_left_camera.set_rotation(90)
    g_left_camera.start()
    # g_right_camera = ObjectDetectCamera(0, 24, (640, 480), 500)
    # g_right_camera.start()
    g_app.run(host='0.0.0.0', port=5999, threaded=True)
    # while True:
    #     frame = camera.get_current_frame()
    #     if frame is not None:
    #         cv2.imshow('test', frame)
    #     if cv2.waitKey(1000 / 24) > 0:
    #         break
    g_left_camera.stop()
    movidius.close_device()
    # g_right_camera.stop()
    #play_thread = threading.Thread(target=play)
    #detect_thread = threading.Thread(target=detect,args=())
    #snapshot_thread = threading.Thread(target=snapshot)
    #play_thread.start()
    #detect_thread.start()
    #snapshot_thread.start()

    #g_exit = True
    #play_thread.join()
    #detect_thread.join()
    #snapshot_thread.join()
