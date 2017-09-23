import cv2
import time
import os
import datetime
import sys
import zmq
import threading
import copy
import json
from flask import Flask, jsonify

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://10.245.55.97:6666")
while True:
    time.sleep(1)
    socket.send('aaa')
    resp = socket.recv()
    print resp
