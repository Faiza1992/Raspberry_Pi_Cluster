import socket
import time
import csv
import re

def extract_temperature(data_str):
    temp_match = re.search(r'"v":"([\d.]+)",u:"far",n:"temperature"', data_str)
    if temp_match:
        return float(temp_match.group(1))
    return None

def extract_humidity(data_str):
    humidity_match = re.search(r'"v":"([\d.]+)",u:"per",n:"humidity"', data_str)
    if humidity_match:
        return float(humidity_match.group(1))
    return None

def extract_light(data_str):
    light_match = re.search(r'"v":"([\d.]+)",u:"per",n:"light"', data_str)
    if light_match:
        return float(light_match.group(1))
    return None

def receive_and_forward_packets(receive_ip, receive_port, forward_ip, forward_port):
    udp_receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #udp_receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 256 * 1024)
    udp_receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_receive_socket.bind((receive_ip, receive_port))

    udp_forward_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"Listening for packets on {receive_ip}:{receive_port}...")

    packet_count = 1  # The expected packet number (starting from 1)
    forwarded_packet_count = 1
    filtered_packet_count = 0  # Track the number of packets lost due to filters
    csv_filename = 'packet_latency_log_3.csv'
    rec_packets=0
    with open(csv_filename, mode='w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        # Added "Filtered Packets" column
        csv_writer.writerow(['Sender City','Receiving IP','Forwarding IP','Sender Timestamp', 'Receiver Timestamp', 'Forwarding Timestamp', 'Latency (ms)', 'Processing Delay (ms)', 'Dropped Packets', 'Filtered Packets'])

        try:
            while True:
                
                data, addr = udp_receive_socket.recvfrom(2048)  # Buffer size is 2048 bytes
                data_str = data.decode('utf-8')
                data_parts = data_str.split(',', 3)
                rec_packets +=1
                sent_PC = int(data_parts[0])  # Packet number sent by the sender
                print(f"Sent packet count:{rec_packets}, {sent_PC},{packet_count}")
                sender_city = data_parts[2]
                #packet_count = sent_PC + 1
                # Check if there was a packet drop
                if sent_PC > packet_count:
                    packet_drop = sent_PC - packet_count
                    print(f"Packet drop detected: {packet_drop} packets missed")
                else:
                    packet_drop = 0  # No packet drop

                # Print received data for debugging
                #print(f"Received data: {data_str}")

                receiving_timestamp = int(time.time() * 1000)
                print(f"reciving timestamp:{receiving_timestamp}")
                sender_timestamp = int(data_parts[1])
                print(f"sender_timestamp:{sender_timestamp}")
                temperature = extract_temperature(data_parts[3])
                humidity = extract_humidity(data_parts[3])
                light = extract_light(data_parts[3])

                # Check the filters
                if temperature is not None and 0 <= temperature <= 38:
                    if humidity is not None and 15 <= humidity <= 90:
                        if light is not None and 0 <= light <= 1500:
                            # Passed all filters, forward the packet
                            latency = receiving_timestamp - sender_timestamp
                            time.sleep(temperature / 5000)
                            forwarding_timestamp = int(time.time() * 1000)
                            print(f"forwarding timestamp:{forwarding_timestamp}")
                            f_data = f"{forwarded_packet_count},{forwarding_timestamp},{data_str}"
                            processing_delay = forwarding_timestamp - receiving_timestamp

                            udp_forward_socket.sendto(f_data.encode('utf-8'), (forward_ip, forward_port))
                            forwarded_packet_count += 1

                            #print(f"{forwarded_packet_count}: Forwarded packet to {forward_ip}:{forward_port}")

                            # Log forwarded packet (no filtering, so filtered_packets = 0)
                            csv_writer.writerow([sender_city,receive_ip,forward_ip,sender_timestamp, receiving_timestamp, forwarding_timestamp, latency, processing_delay, packet_drop, 0])
                            csvfile.flush()  # Ensure data is written to the file

                            print(f"Packet {packet_count}: Sender Timestamp={sender_timestamp}, Receiver Timestamp={receiving_timestamp}, Forwarding Timestamp={forwarding_timestamp}, Latency={latency}ms, Processing Delay={processing_delay}ms")
                        else:
                            print(f"Packet {packet_count} with light {light} filtered out (not in range 0-800)")
                            filtered_packet_count += 1
                            csv_writer.writerow([sender_city,receive_ip,forward_ip,sender_timestamp, receiving_timestamp, "Filtered", receiving_timestamp-sender_timestamp, 0, packet_drop, 1])  # Log filtered packet
                            csvfile.flush()  # Ensure data is written to the file
                    else:
                        print(f"Packet {packet_count} with humidity {humidity}% filtered out (not in range 15-90%)")
                        filtered_packet_count += 1
                        csv_writer.writerow([sender_city,receive_ip,forward_ip,sender_timestamp, receiving_timestamp, "Filtered", receiving_timestamp-sender_timestamp, 0, packet_drop, 1])  # Log filtered packet
                        csvfile.flush()  # Ensure data is written to the file
                else:
                    print(f"Packet {packet_count} with temperature {temperature}°C filtered out (not in range 0-38°C)")
                    filtered_packet_count += 1
                    csv_writer.writerow([sender_city,receive_ip,forward_ip,sender_timestamp, receiving_timestamp, "Filtered", receiving_timestamp-sender_timestamp, 0, packet_drop, 1]) 
                    #csv_writer.writerow([sender_timestamp, receiving_timestamp, "Filtered", receiving_timestamp-sender_timestamp, 0, packet_drop, 1])  # Log filtered packet
                    csvfile.flush()  # Ensure data is written to the file

                # Update expected packet count to the next packet
                packet_count = sent_PC + 1  # After processing, expect the next packet

        except KeyboardInterrupt:
            print("\nStopped by user.")

        finally:
            # Write summary row to CSV file
            csv_writer.writerow([])
            csv_writer.writerow(['Summary'])
            csv_writer.writerow(['Total Packets Sent', 'Total Packets Received', 
                                 'Total Packets Forwarded', 'Total Packets Filtered'])
            csv_writer.writerow([packet_count - 1, rec_packets, forwarded_packet_count - 1, filtered_packet_count])
            
            # Print summary to console
            print("\nSummary:")
            print(f"Total packets sent: {packet_count - 1}")
            print(f"Total packets received: {rec_packets}")
            print(f"Total packets forwarded: {forwarded_packet_count - 1}")
            print(f"Total packets filtered out: {filtered_packet_count}")

            udp_receive_socket.close()
            udp_forward_socket.close()

if __name__ == "__main__":
    listen_ip = "192.168.1.17"
    listen_port = 5000

    forward_ip = "192.168.1.6"
    forward_port = 5000

    receive_and_forward_packets(listen_ip, listen_port, forward_ip, forward_port)
