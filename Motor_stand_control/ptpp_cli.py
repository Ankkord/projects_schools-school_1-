import sys
import threading
import time
from serial.tools import list_ports
from serial_controller import SerialPortController

def receive_callback(unpacked_data):
    if len(unpacked_data) < 4:
        return
    group = unpacked_data[0]
    command = unpacked_data[1]
    seq = unpacked_data[2]
    len_payload = unpacked_data[3]
    if len(unpacked_data) != 4 + len_payload:
        return
    payload = unpacked_data[4:4 + len_payload]
    print(f"group: {group:02X}, command: {command:02X}, payload: {' '.join(f'{b:02X}' for b in payload)}")

def on_error_callback():
    print("Serial error occurred.")
    sys.exit(1)

def main():
    available_ports = list(list_ports.comports())
    if not available_ports:
        print("No serial ports found.")
        sys.exit(1)
    if len(available_ports) == 1:
        port_name = available_ports[0].device
        print(f"Connecting to {port_name}")
    else:
        print("Available ports:")
        for i, port in enumerate(available_ports):
            print(f"{i+1}: {port.device} - {port.description}")
        try:
            choice = int(input("Choose port number: ")) - 1
            if 0 <= choice < len(available_ports):
                port_name = available_ports[choice].device
            else:
                print("Invalid choice.")
                sys.exit(1)
        except ValueError:
            print("Invalid input.")
            sys.exit(1)

    controller = SerialPortController(port=port_name, baudrate=115200, echo_plain_text=True, on_error_callback=on_error_callback)
    controller.add_callback(receive_callback)

    print("Interactive serial interface. Enter hex bytes separated by space: first group, then command, then payload bytes.")
    print("Example: 01 01 48 65 6C 6C 6F")
    print("To exit, type 'exit'")

    while True:
        try:
            line = input("> ")
            if line.strip().lower() == 'exit':
                break
            parts = line.strip().split()
            if len(parts) < 2:
                print("Need at least group and command.")
                continue
            group = int(parts[0], 16)
            command = int(parts[1], 16)
            payload_list = [int(p, 16) for p in parts[2:]] if len(parts) > 2 else []
            payload = bytes(payload_list)
            controller.send_data(group, command, payload)
        except ValueError as e:
            print(f"Invalid input: {e}")
        except Exception as e:
            print(f"Error: {e}")

    controller.close()
    print("Exited.")

if __name__ == "__main__":
    main()