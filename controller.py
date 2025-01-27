# rename this to main.py and drag to Pico

from pololu import IMU

# Constants for sensors
SENSITIVITY_baro = 4096 # (LSB/hPa)
SENSITIVITY_accel = 0.244 # (mg/LSB) - +- 8FS
SENSITIVITY_gyro = 17.5  # (mdps/LSB) - +- 500FS
SENSITIVITY_mag = 2281   # (LSB/gauss) - +- 12FS
SENSITIVITY_temp = 480  # (LSB/°C)

# Variable for the multi-sensor object
m_sense = None

#calibration global variables
zero_acceleration = [0,0,0]
zero_gyro = [0,0,0]
zero_set = False

#global for zero btn
accel_data = [0,9.81,0]

import machine
import time
import math
led = machine.Pin("LED", machine.Pin.OUT)

import network, socket, json
server = None

#GoPiGo ip in hotspot network
server_ip = "172.20.10.7"
server_port = 12345
def init():
    global m_sense, server, server_ip, server_port
    i2c = machine.I2C(0,
                  scl=machine.Pin(5),
                  sda=machine.Pin(4))
    m_sense = IMU(i2c)
    #m_sense.barometer_init(IMU.BAROMETER_FREQ_1HZ)
    m_sense.accelerometer_init(IMU.ACCELEROMETER_FREQ_208HZ, IMU.ACCELEROMETER_SCALE_8G)
    m_sense.gyroscope_init(IMU.GYROSCOPE_FREQ_13HZ, IMU.GYROSCOPE_SCALE_500DPS)
    #m_sense.magnetometer_init(IMU.MAGNETOMETER_FREQ_1_25HZ, IMU.MAGNETOMETER_SCALE_12GAUSS)

    ssid = "SSID"
    password = "PW"
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    wifi.connect(ssid, password)
    while not wifi.isconnected():
        print("Connecting to WiFi...")
        time.sleep(1)
    print("Connected to WiFi:", wifi.ifconfig())

    accel_raw = m_sense.accelerometer_raw_data() # is a dict with x, y, z
    accel = [x * 9.8 * (SENSITIVITY_accel/1000) for x in accel_raw.values()]
    setIMU_zero(accel)

    while not server:
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            #server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            # server.connect((server_ip, server_port))
        except:
            print("Robot not found, retrying...")
            server = None
            time.sleep(1)
    print("Ready to send to robot")

    time.sleep(1)

sensitivity = 1.0
last_changed = time.ticks_ms()
def adjust_sensitivity(gyro):
    global sensitivity, last_changed

    ## Method 1: using time
    if time.ticks_ms() - last_changed > 10000 or gyro[2] > 90 or gyro[2] < -90: # reset after 10s or if hand turning over
        last_changed = time.ticks_ms()
    if time.ticks_ms() - last_changed < 1000:
        return
    if gyro[0] < -50 and sensitivity > 0.2: # acceleration[2] < -5:
        sensitivity -= 0.2
        last_changed = time.ticks_ms()
    elif gyro[0] > 50 and sensitivity < 5: #acceleration[2] > 1:
        sensitivity += 0.2
        last_changed = time.ticks_ms()
    # print(f"adjusted sensitivity: {sensitivity}")
    return

adjust_pos = 0 # 0: neutral, -1: hand-away (lower sen), 1: hand-towards (higher sen)
# z->neg: increase, z->pos: decrease
def adjust_sensitivity_state(acceleration):
    global sensitivity, adjust_pos
    ## Method 2: using states
    if adjust_pos == 0:
        if acceleration[2] < -5:
            adjust_pos = 1
        elif acceleration[2] > 1:
            adjust_pos = -1
    elif adjust_pos == 1:
        if acceleration[2] > -2 and sensitivity != 0:
            adjust_pos = 0
            sensitivity += 0.2
    elif adjust_pos == -1:
        if acceleration[2] < -0.5 and sensitivity != 0:
            adjust_pos = 0
            sensitivity -= 0.2
    sensitivity = round(sensitivity, 1)
    print(f"adjusted sensitivity: {sensitivity}")
    print(f"adjust_pos: {adjust_pos}, acceleration[2]: {acceleration[2]}")

def steer_robot(acceleration):
    global sensitivity, server, server_ip, server_port
    message = json.dumps({"sensitivity": sensitivity, "acceleration": acceleration}) + "\n"
    print(message)
    server.sendto(message.encode(), (server_ip, server_port))

#IMU AND GLOVE POSITION CALIBRATION SCRIPT STUFF
#set zero_acceleration
def setIMU_zero(data):
    global zero_acceleration, zero_set
    current = data  # [accelX, accelY, accelZ]
    zero_acceleration = current
    print("Zeroed at:", zero_acceleration)
    zero_set = True

#this will give the calibrated data (used on GoPiGo)
def getRelativeData(data):
    if not zero_set:
        print("Zero position not set")
        return None

    current = data  # [accelX, accelY, accelZ]
    
    #find relative values
    relative_acceleration = [
        current[0] - zero_acceleration[0],
        current[1] - zero_acceleration[1],
        current[2] - zero_acceleration[2],
    ]
    

    return relative_acceleration

    

#Set button and its interrupt (INTERRUPT MIGHT MESS WITH THE WIFI STUFF O WE MIGHT NEED TO USE A CHECKPOINT IN THE MAIN LOOP INSTEAD)
zero_btn = machine.Pin(16, machine.Pin.IN, machine.Pin.PULL_UP)
off_btn = machine.Pin(20, machine.Pin.IN, machine.Pin.PULL_UP)


sensitivity_led = machine.Pin(18, machine.Pin.OUT, machine.Pin.PULL_DOWN)
sensitivity_period = 100


def main():
    global server, accel_data, sensitivity_period, sensitivity_led, sensitivity
    init()

    last_action_time = time.ticks_ms()  # Record the current time

    try:
        while True:
            led.toggle()
            
            
            
            if time.ticks_ms() - last_action_time >= 1/sensitivity_period:
                sensitivity_led.toggle()
                print(1/sensitivity_period)
                last_action_time = time.ticks_ms()  # Reset the last action time

            
            ## If pitch->lift: z->negative, if roll->right: x->positive
            accel_raw = m_sense.accelerometer_raw_data() # is a dict with x, y, z
            accel = [x * 9.8 * (SENSITIVITY_accel/1000) for x in accel_raw.values()]
            gyro_raw = m_sense.gyroscope_raw_data() # also dict
            gyro = [x * (SENSITIVITY_gyro/1000) for x in gyro_raw.values()] # pitch, yaw, roll


            if zero_btn.value() == 0:
                accel_data = accel
                sensitivity = 1
                setIMU_zero(accel_data)
                
            if off_btn.value() == 0:
                steer_robot({0,0,0,0})
                print("Turning Off")
                server.close()
                led.off()
                break
                
            if accel[1] < 0: # hand turned over
                adjust_sensitivity(gyro)
                sensitivity_period = 0.0001 / (10**(-(1 + sensitivity)))
            else:
                rel_accel = getRelativeData(accel)
                steer_robot(rel_accel)

            #print(f"acceleration: {accel}m/s²")
            #print(f"angular velocity: {gyro}dps")
            #print()

            time.sleep(0.1)
    except Exception as e:
        print(f"Error occured: {e}")
        print("Shutting down...")
    finally:
        server.close()
        print("Connection closed")

if __name__ == "__main__":
    #Run the main function
    main()
