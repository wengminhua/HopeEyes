import time
import zmq
import json

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:6666")

while True:
    image_bytes = socket.recv()
    print "recv req"
    print image_bytes
    socket.send('bbbb')
