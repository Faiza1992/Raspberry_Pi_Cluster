import socket
import time
import csv  # Ensure csv is imported

def receive_and_log_packets(receive_ip, receive_port):
    udp_receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 512 * 1024)
    udp_receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_receive_socket.bind((receive_ip, receive_port))

    print(f"Listening for packets on {receive_ip}:{receive_port}...")

    # Initialize packet counts
    packet_counts = {
        "b1": 1,
        "b2": 1,
    }
    rec_packets = 0
    csv_filename = 'packet_latency_log_sink.csv'
    total_dropped_packets = 0
    # Create and write header to CSV file
    with open(csv_filename, mode='w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['Sender City', 'Receiving IP', 'Sender Timestamp', 
                             'Receiver Timestamp', 'Latency (ms)', 
                             'End Latency (ms)', 'Dropped Packets'])

        try:
            while True:
                # Receive data from the sender
                data, addr = udp_receive_socket.recvfrom(2048)
                data_str = data.decode('utf-8')
                print(f"{data_str}")
                data_parts = data_str.split(',', 8)
                sender_city = data_parts[1]
                print(f"Received: {data_str}")
                rec_packets += 1
                receiving_timestamp = int(time.time() * 1000)
                sender_timestamp = int(data_parts[2])

                # Initialize packet_drop for every packet received
                packet_drop = 0  # Default value for packet drop

                # Check if the sender city is one of the expected cities
                if sender_city in packet_counts:
                    sent_PC = int(data_parts[0])
                    if sent_PC > packet_counts[sender_city]:
                        # Calculate packet drops
                        packet_drop = sent_PC - packet_counts[sender_city]
                    # Always update the packet count regardless of drops
                    packet_counts[sender_city] = sent_PC + 1
                else:
                    print(f"Unknown city: {sender_city}")
                    continue
                time.sleep(0.01)
                latency = receiving_timestamp - sender_timestamp
                end_latency = receiving_timestamp - int(data_parts[6])
                
                # Log the packet in the CSV file
                csv_writer.writerow([sender_city, receive_ip, 
                                     sender_timestamp, receiving_timestamp, 
                                     latency, end_latency, packet_drop])
                csvfile.flush()

        except KeyboardInterrupt:
            print("\nStopped by user.")
        finally:
            udp_receive_socket.close()

            # Write summary to CSV
            csv_writer.writerow([])  # Blank line for separation
            csv_writer.writerow(['Summary'])
            csv_writer.writerow(['Total Packets Received', rec_packets])
            csv_writer.writerow(['Total Expected Packets', sum(packet_counts.values())])
            csv_writer.writerow(['Total Dropped Packets', total_dropped_packets])
            print(f"Total packets received: {rec_packets}")
            print(f"Total expected received: {sum(packet_counts.values())}")
            print(f"Total dropped packets: {total_dropped_packets}")



if __name__ == "__main__":
    listen_ip = "192.168.1.4"
    listen_port = 5000
    receive_and_log_packets(listen_ip, listen_port)
