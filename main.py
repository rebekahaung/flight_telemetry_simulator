import socket
import threading
import random
import time
import json
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

PORT = 5005
IP = "127.0.0.1"
PACKET_LOSS_RATE = 0.1

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

telemetry_data = {
    "altitude": 0,
    "velocity": 0,
    "timestamp": 0
}

@app.route("/")
def index():
    return render_template("dashboard.html")

@socketio.on("connect")
def on_connect():
    print("Client connected")

aircraft_state = {
    "altitude": 0,
    "velocity": 0,
    "timestamp": 0
}

def task_generate_data(interval):
    next_run = time.time()
    while True:
        if time.time() >= next_run:
            aircraft_state["altitude"] = random.randint(1000, 40000)
            aircraft_state["velocity"] = random.randint(200, 900)
            aircraft_state["timestamp"] = time.time()
            next_run += interval
        yield

def task_send_data(interval, sock):
    next_run = time.time()
    while True:
        if time.time() >= next_run:
            if random.random() > PACKET_LOSS_RATE:
                sock.sendto(json.dumps(aircraft_state).encode(), (IP, PORT))
            next_run += interval
        yield

def task_logger(interval):
    next_run = time.time()
    while True:
        if time.time() >= next_run:
            print(f"[{aircraft_state['timestamp']:.2f}] Sent: {aircraft_state}")
            next_run += interval
        yield

def aircraft_scheduler():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tasks = [
        task_generate_data(1),
        task_send_data(1, sock),
        task_logger(2)
    ]
    while True:
        for t in tasks:
            next(t)
        time.sleep(0.01)

def ground_station():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((IP, PORT))
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            packet = json.loads(data.decode())
            telemetry_data.update(packet)
            socketio.emit("telemetry", telemetry_data)
        except Exception as e:
            print("Error receiving data:", e)

aircraft_thread = threading.Thread(target=aircraft_scheduler)
aircraft_thread.daemon = True
aircraft_thread.start()

ground_station_thread = threading.Thread(target=ground_station)
ground_station_thread.daemon = True
ground_station_thread.start()

if __name__ == '__main__':
    socketio.run(app, host=IP, port=8000)