import socket
import openpyxl
import time

def send_data(file_path, ip, port, duration):
    # Load the workbook and select the active sheet
    workbook = openpyxl.load_workbook(file_path)
    sheet = workbook.active

    # Create a UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Initialize packet counter
    packet_count = 1

    # Get the start time
    start_time = time.time()
    #seq_num=1
    # Loop to send data for the specified duration
    while time.time() - start_time < duration:
        # Iterate through each row in the sheet
        for row in sheet.iter_rows(values_only=True):
            timestamp = int(time.time()*1000)  # Current time in milli-seconds since the epoch
            
            # Prepare the data to send, including the timestamp
            data_to_send = f"{packet_count},{timestamp}," + ','.join(str(value) for value in row if value is not None)
            
            #print(f"Sending: {data_to_send}")
            #if packet_count == 10 or packet_count == 15 or packet_count == 17 or packet_count == 18 or packet_count == 19:
                #packet_count += 1
                #continue
            # Send the data
            udp_socket.sendto(data_to_send.encode('utf-8'), (ip, port))

            # Increment the packet count
            packet_count += 1
            #seq_num += 1
            # Sleep for a short time to avoid overwhelming the network
            time.sleep(0.004)  # Adjust this delay as necessary

    # Close the socket
    udp_socket.close()

    # Print the total number of packets sent
    print(f"city 1, {packet_count-1}")

if __name__ == "__main__":
    xlsx_file_path = "/home/cc/City_1.xlsx"  # Replace with your actual file path
    target_ip = "192.168.1.5"
    target_port = 5000
    duration_in_seconds = 900  # Send packets for 1 minute

    send_data(xlsx_file_path, target_ip, target_port, duration_in_seconds) 
