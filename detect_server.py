import time
import zmq
import json
from darknet import load_net
from darknet import load_meta
from darknet import detect

cfg_filename = '/home/wengmh1/hackathon/darknet/cfg/yolo.cfg'
weights_filename = '/home/wengmh1/hackathon/darknet/weights/yolo.weights'
meta_filename = '/home/wengmh1/hackathon/darknet/cfg/coco.data'
temp_image_filename = 'temp.jpg'

net = load_net(cfg_filename, weights_filename, 0)
meta = load_meta(meta_filename)

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

while True:
    image_bytes = socket.recv()
    image_file = open(temp_image_filename, 'wb')
    image_file.write(image_bytes)
    image_file.close()
    objects = detect(net, meta, temp_image_filename)
    result = []
    for i in range(len(objects)):
        category, match, position = objects[i]
        x, y, width, height = position
        one_item = {
            "category": category,
            "match": match,
            "position": {
                "x": x,
                "y": y,
                "width": width,
                "height": height
            }
        }
        result.append(one_item)
    #time.sleep(1)
    socket.send(json.dumps(result))
