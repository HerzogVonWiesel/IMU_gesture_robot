# File for GoPiGo
import easygopigo3 as go
import socket
import json
import time

conn = None
server = None

def init():
    global conn, server
    server_ip = "0.0.0.0" # Listen on all interfaces
    server_port = 12345

    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.settimeout(0.2)
    server.bind((server_ip, server_port))
    # server.listen(1)

    #conn, addr = server.accept()
    #print(f"Connected to controller @ {addr}")

def steer(acc_x, acc_z, sensitivity):
    global myRobot

    #positive roll gets added to left wheel to make robot turn RIGHT!
    left_wheel_steer = 0
    right_wheel_steer = 0    
                     
    # if acc_z > 0 and acc_z < 1:
    #     if acc_x > 0.1 and acc_x < 0.16: 
    #         left_wheel_steer = 0
    #         right_wheel_steer = 0
    #     else:
    #         if acc_x > 0.16:
    #             right_wheel_steer = 0
    #             left_wheel_steer = 25
    #         elif acc_x < 0.1:
    #             turning_speed = right_wheel_steer
    #             right_wheel_steer = 10
    #             left_wheel_steer = 25
    dead_zone = 2.0
    if abs(acc_x) < dead_zone and abs(acc_z) < dead_zone:
        left_wheel_steer = 0
        right_wheel_steer = 0
    else:
        left_wheel_steer = acc_z*10*sensitivity+ acc_x*3*sensitivity
        right_wheel_steer = acc_z*10*sensitivity- acc_x*3*sensitivity


    # else:
    #     if acc_x < 0:
    #         left_wheel_steer = acc_z*10*sensitivity/wheel_dif
    #         right_wheel_steer = acc_z*10*sensitivity
    #     elif acc_x > 0:
    #         left_wheel_steer = acc_z*10*sensitivity
    #         right_wheel_steer = acc_z*10*sensitivity/wheel_dif 
    myRobot.steer(left_wheel_steer,right_wheel_steer)

def main():
    global server, myRobot
    init()
    myRobot = go.EasyGoPiGo3()
    myRobot.set_speed(500)
    try:
        # last_packet = time.time()
        while True:
            
            # Receive data from the client
            try:
                data, addr = server.recvfrom(1024)
            except TimeoutError:
                data = None
            if not data:
                print("NO DATA")
                steer(0.0, 0.0, 0.0)
            try:
                # last_packet = time.time()
                myRobot.led_on(1)
                data, _ = data.decode().split("\n", 1)
                data_obj = json.loads(data)
                print(f"Received: {data_obj}")
                sensitivity = data_obj["sensitivity"]
                acc_x = round(data_obj["acceleration"][0],2)
                acc_z = round(data_obj["acceleration"][2],2)
                steer(acc_x, acc_z, sensitivity)
                
            # except json.JSONDecodeError:
            #     print(f"Failed to parse JSON: {data}")
            except Exception as e:
                print(f"Got exception {e}")
    except Exception as e:
        print(f"Error occured: {e}")
        print("Server shutting down.")
    except KeyboardInterrupt:
        myRobot.stop()
    finally:
        pass
        #conn.close()
    server.close()
    myRobot.stop()

if __name__ == "__main__":
    #Run the main function
    main()