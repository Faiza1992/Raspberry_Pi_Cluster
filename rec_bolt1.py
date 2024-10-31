import socket
import time
import csv
import re

def extract_air_quality(data_str):
    # Extract air quality value from the data string
    air_quality_match = re.search(r'"v":"([\d.]+)",u:"per",n:"airquality_raw"', data_str)
    return float(air_quality_match.group(1)) if air_quality_match else None

def receive_and_forward_packets(receive_ip, receive_port, forward_ip, forward_port):
    udp_receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 128 * 1024)
    udp_receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_receive_socket.bind((receive_ip, receive_port))

    udp_forward_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"Listening for packets on {receive_ip}:{receive_port}...")

    # Initialize packet counts and filters
    packet_counts = {
        "city1": 1,
        "city2": 1,
        "city6": 1,
        "city7": 1,
    }
    forwarded_packet_count = 1
    filtered_packet_count = 0
    csv_filename = 'packet_latency_log_b1.csv'
    rec_packets = 0

    # Create and write header to CSV file
    with open(csv_filename, mode='w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['Sender City', 'Receiving IP', 'Forwarding IP', 
                             'Sender Timestamp', 'Receiver Timestamp', 
                             'Forwarding Timestamp', 'Latency (ms)', 
                             'Processing Delay (ms)', 'Dropped Packets', 
                             'Filtered Packets'])

        try:
            while True:
                # Receive data from the sender
                data, addr = udp_receive_socket.recvfrom(2048)
                data_str = data.decode('utf-8')
                data_parts = data_str.split(',', 6)
                sender_city = data_parts[4]
                print(f"{data_str}")
                rec_packets += 1
                receiving_timestamp = int(time.time() * 1000)
                sender_timestamp = int(data_parts[1])

                # Initialize packet_drop for every packet received
                packet_drop = 0  # Default value for packet drop

                # Check if the sender city is one of the expected cities
                if sender_city in packet_counts:
                    sent_PC = int(data_parts[0])
                    #print(f"@@@@@{sender_city}:{sent_PC},{packet_counts[sender_city]}")
                    if sent_PC > packet_counts[sender_city]:
                        #print(f"****{sender_city}:{sent_PC},{packet_counts[sender_city]}")
                        # Calculate packet drops
                        packet_drop = sent_PC - packet_counts[sender_city]
                        #print(f"dropped packet from {sender_city}:{packet_drop}, sent:{sent_PC}")
                    # Always update the packet count regardless of drops
                    packet_counts[sender_city] = sent_PC + 1

                else:
                    print(f"Unknown city: {sender_city}")
                    continue

                air_quality = extract_air_quality(data_parts[6])

                if air_quality is not None and air_quality > 15:
                    latency = receiving_timestamp - sender_timestamp
                    time.sleep(air_quality / 5000)
                    forwarding_timestamp = int(time.time() * 1000)

                    f_data = f"{forwarded_packet_count},b1,{forwarding_timestamp},{data_str}"
                    processing_delay = forwarding_timestamp - receiving_timestamp

                    udp_forward_socket.sendto(f_data.encode('utf-8'), (forward_ip, forward_port))
                    forwarded_packet_count += 1

                    csv_writer.writerow([sender_city, receive_ip, forward_ip, 
                                         sender_timestamp, receiving_timestamp, 
                                         forwarding_timestamp, latency, 
                                         processing_delay, packet_drop, 0])
                    csvfile.flush()

                    print(f"Forwarded packet: {sender_city}, Sender Timestamp={sender_timestamp}, "
                          f"Receiver Timestamp={receiving_timestamp}, "
                          f"Forwarding Timestamp={forwarding_timestamp}, "
                          f"Latency={latency}ms, Processing Delay={processing_delay}ms")
                else:
                    print(f"Packet from {sender_city} filtered out: Air Quality {air_quality} (<= 15)")
                    filtered_packet_count += 1
                    latency = receiving_timestamp - sender_timestamp
                    csv_writer.writerow([sender_city, receive_ip, forward_ip, 
                                         sender_timestamp, receiving_timestamp, 
                                         "Filtered", latency, 0, 
                                         0, 1])
                    csvfile.flush()

        except KeyboardInterrupt:
            print("\nStopped by user.")
        finally:
            # Write summary row to CSV file
            csv_writer.writerow([])
            csv_writer.writerow(['Summary'])
            csv_writer.writerow(['Total Packets Sent', 'Total Packets Received', 
                                 'Total Packets Forwarded', 'Total Packets Filtered'])
            total_packet_count = sum(packet_counts.values()) - 4
            csv_writer.writerow([total_packet_count, rec_packets, forwarded_packet_count - 1, filtered_packet_count])
            
            # Print summary to console
            print("\nSummary:")
            print(f"Total packets sent: {total_packet_count}")
            print(f"Total packets received: {rec_packets}")
            print(f"Total packets forwarded: {forwarded_packet_count - 1}")
            print(f"Total packets filtered out: {filtered_packet_count}")

            udp_receive_socket.close()
            udp_forward_socket.close()




if __name__ == "__main__":
    listen_ip = "192.168.1.9"
    listen_port = 5000

    forward_ip = "192.168.1.4"
    forward_port = 5000

    receive_and_forward_packets(listen_ip, listen_port, forward_ip, forward_port)
