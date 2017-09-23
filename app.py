#coding=utf-8
import cv2
import time
import os
import datetime
import sys
import zmq
import threading
import copy
import json
import math
from flask import Flask, jsonify

VIDEO_TYPE = ''
VIDEO_URI = 'rtmp://121.41.5.1:443/ipc/149543576858286335?device_id=149543576858286335&a=&s=0&c=0&x=&i=&d=&u=&l=&r=&t=&y=&z=&e=0&v=80&p=1&h=0&q=&m=0&o=&w=&g=&j=&k=&n=&wh=&ct=2&my_url=http%3A%2F%2Flelink.lenovo.com.cn%2Ffront%2Frtmp.php%3Furl%3Drtmp%253A%252F%252F121.41.5.1%253A443%252Fipc%252F149543576858286335%253Fdevice_id%253D149543576858286335'
DETECT_SERVER_URI = 'tcp://10.245.55.97:6666'
SNAPSHOT_DIR = 'D:/projects/Hackathon/training'
RESULT_CACHE_SIZE = 500

g_current_frame_lock = threading.Lock()
g_current_frame = None
g_current_result_lock = threading.Lock()
g_current_result = None
g_exit = False
g_app = Flask('HopeEyes')
g_result_cache_lock = threading.Lock()
g_result_cache = []

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


def push_result_into_cache(result):
    global g_result_cache_lock, g_result_cache
    if g_result_cache_lock.acquire():
        temp_result = copy.deepcopy(result)
        if len(g_result_cache) >= 500:
            g_result_cache = g_result_cache[1:]
        g_result_cache.append(temp_result)
        g_result_cache_lock.release()


def find_object_from_cache(object_code):
    global g_result_cache_lock, g_result_cache
    if g_result_cache_lock.acquire():
        for num in range(1, len(g_result_cache)):
            detect_result = g_result_cache[len(g_result_cache) - num]
            for detect_obj in detect_result:
                if detect_obj['category'] == object_code:
                    pos_x = detect_obj['position']['x']
                    image_width = 720
                    if pos_x <= (image_width / 3):
                        g_result_cache_lock.release()
                        return 'left'
                    if pos_x <= (image_width * 2 / 3):
                        g_result_cache_lock.release()
                        return 'middle'
                    g_result_cache_lock.release()
                    return 'right'
        g_result_cache_lock.release()
        return ''


def detect_moving_object_from_cache():
    global g_result_cache_lock, g_result_cache
    if g_result_cache_lock.acquire():
        # Clear result cache
        g_result_cache = []
        g_result_cache_lock.release()
    total_try_seconds = 20
    try_seconds = 2
    while try_seconds > 0:
        time.sleep(try_seconds)
        try_seconds -= try_seconds
        if g_result_cache_lock.acquire():
            object_move_ranges = []
            for index in range(1, len(g_result_cache)):
                result = g_result_cache[index]
                found = False
                for m_index in range(1, len(object_move_ranges)):
                    if object_move_ranges[m_index]['category'] == result['category']:
                        x = result['position']['x']
                        y = result['position']['y']
                        start_x = object_move_ranges[m_index]['start_x']
                        start_y = object_move_ranges[m_index]['start_y']
                        position_change = int(math.sqrt(math.pow((x - start_x), 2) + math.pow((y - start_y), 2)))
                        start_size = object_move_ranges[m_index]['start_size']
                        size = result['position']['width'] * result['position']['height']
                        size_change = math.abs(size - start_size)
                        if position_change > object_move_ranges[m_index]['max_position_change']:
                            object_move_ranges[m_index]['max_position_change'] = position_change
                        if size_change > object_move_ranges[m_index]['max_size_change']:
                            object_move_ranges[m_index]['max_size_change'] = size_change
                        found = True
                    if not found:
                        object_move_ranges.append({
                            'category': result['category'],
                            'start_x': result['position']['x'],
                            'start_y': result['position']['y'],
                            'start_size': result['position']['width'] * result['position']['height'],
                            'max_position_change': 0,
                            'max_size_change': 0
                        })
            # Sort
            object_move_ranges.sort(moving_compare)
            g_result_cache_lock.release()
            # Filter max
            if object_move_ranges[0]['max_position_change'] >= 150 or object_move_ranges[0]['max_size_change'] >= (50 * 50):
                return object_move_ranges['category']
    return ''


def moving_compare(objA, objB):
    position_weight = 0.7
    size_weight = 0.3
    a = objA['max_position_change'] * position_weight + objA['max_size_change'] * size_weight
    b = objB['max_position_change'] * position_weight + objB['max_size_change'] * size_weight
    if a >= b:
        return 1
    return -1


def detect():
    global g_exit
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(DETECT_SERVER_URI)
    while not g_exit:
        current_frame = get_current_frame()
        if current_frame is not None:
            #print 'got frame'
            req = cv2.imencode('.jpg', current_frame)[1].tobytes()
            socket.send(req)
            resp = socket.recv()
            detect_result = json.loads(resp)
            set_current_result(detect_result)
            push_result_into_cache(detect_result)
        else:
            time.sleep(1)


def snapshot():
    global g_exit
    index = 0
    while not g_exit:
        current_frame = get_current_frame()
        if current_frame is not None:
            #print 'snapshot got frame'
            index += 1
            snapshot_filename = os.path.join(SNAPSHOT_DIR, str(index)+'.jpg')
            cv2.imwrite(snapshot_filename, current_frame)
        time.sleep(2)


def play():
    global g_exit
    if VIDEO_TYPE == 'camera':
        cap = cv2.VideoCapture(0)
    else:
        cap = cv2.VideoCapture(VIDEO_URI)
    if not cap.isOpened():
        print "Open video source failed."
        return
    fps = cap.get(cv2.cv.CV_CAP_PROP_FPS)
    size = (int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)),
            int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT)))
    interval = int(fps)
    if interval == 0:
        interval = 15
    print fps
    print size
    while not g_exit:
        ret, frame = cap.read()
        if ret:
            current_frame = pre_process(frame)
            set_current_frame(current_frame)
            current_result = get_current_result()
            if current_result is not None:
                draw_detect_result(current_frame, current_result)
            cv2.imshow('capture', current_frame)
            cv2.waitKey(1000/interval)
        else:
            print 'No frame, wait 1s'
            time.sleep(1)


def pre_process(image):
    image = cv2.resize(image, (1280, 720), interpolation=cv2.INTER_CUBIC)
    image = image[0:720, 280:(280+720)]
    return image


def draw_detect_result(frame, result):
    for i in range(len(result)):
        pos = result[i]['position']
        p_tl = (int(pos['x']) - int(pos['width'] / 2), int(pos['y']) - int(pos['height'] / 2))
        p_br = (int(pos['x']) + int(pos['width'] / 2), int(pos['y']) + int(pos['height'] / 2))
        cv2.putText(frame, result[i]['category'], p_tl, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.rectangle(frame, p_tl, p_br, (0, 255, 0), 2)


def get_object_name(object_code):
    with open('objects.json') as objects_file:
        objects = json.load(objects_file)
    for index in range(0, len(objects)):
        print object_code + '/' + objects[index - 1]['code']
        if objects[index - 1]['code'] == object_code:
            return objects[index - 1]['keyword']
    return ''


@g_app.route('/api/objects', methods=['GET'])
def get_objects():
    with open('objects.json') as objects_file:
        objects = json.load(objects_file)
    return jsonify(objects)


@g_app.route('/api/objects/find/<code>', methods=['GET'])
def find_object(code):
    object_name = get_object_name(code)
    print object_name
    if object_name == '':
        find_result_speaking = '无法识别的物品'
    else:
        find_result = find_object_from_cache(code)
        find_result_speaking = ''
        if find_result == 'left':
            find_result_speaking = object_name + u'在您左前方'
        if find_result == 'middle':
            find_result_speaking = object_name + u'在您正前方'
        if find_result == 'right':
            find_result_speaking = object_name + u'在您右前方'
    return jsonify([{
        'result': find_result_speaking
    }])


@g_app.route('/api/objects/detect', methods=['GET'])
def detect_object():
    object_code = detect_moving_object_from_cache()
    if object_code == '':
        find_result_speaking = '没有检测到物品'
    else:
        object_name = get_object_name(object_code)
        find_result_speaking = '这是' + object_name
    return jsonify([{
        'result': find_result_speaking
    }])


if __name__ == '__main__':
    play_thread = threading.Thread(target=play)
    detect_thread = threading.Thread(target=detect)
    snapshot_thread = threading.Thread(target=snapshot)
    play_thread.start()
    detect_thread.start()
    snapshot_thread.start()
    g_app.run(host='0.0.0.0', port=5999)
    g_exit = True
    play_thread.join()
    detect_thread.join()
    snapshot_thread.join()
