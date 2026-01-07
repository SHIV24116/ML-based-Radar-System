import serial
import time

ser = serial.Serial('COM5', 115200)  # adjust COM port
time.sleep(2)

samples = []

start_time = time.time()
while time.time() - start_time < 10:  # 10 seconds
    line = ser.readline().decode().strip()
    if line.isdigit():
        samples.append(int(line))

ser.close()

with open("recording.csv", "w") as f:
    for s in samples:
        f.write(f"{s}\n")
