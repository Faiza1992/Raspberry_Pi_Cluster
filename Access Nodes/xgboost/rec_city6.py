import socket
import time
import csv
import re
import random
import numpy as np
import joblib
import json
import xgboost as xgb
# Load your trained model
#model = joblib.load('aggregation_node_model_resampled.pkl')
#model = joblib.load('xgboost_model.json')
model = xgb.XGBClassifier()
model.load_model('xgboost_model.json')
# Load PDF values from a JSON file
def load_pdf_values(filename='pdf_storage.json'):
    with open(filename, 'r') as file:
        return json.load(file)

pdf_values = load_pdf_values()
#print(f"PDF values loaded: {pdf_values}")

def sample_from_pdf(parameter):
    # Ensure parameter is a dictionary
    if not isinstance(parameter, dict):
        print("Error: parameter should be a dictionary.")
        return None, None

    # Access the correct structure for latency data
    latency_data_b1 = parameter.get("0.004_128KB_b1", {}).get("Latency (ms)",{})
    latency_data_b2 = parameter.get("0.004_128KB_b2", {}).get("Latency (ms)",{})
    #print(f"latency b1:{latency_data_b1}")
    #print(f"latency b2:{latency_data_b2}")    
    # Combine x_values and pdf_values across b1 and b2
    x_values = latency_data_b1.get("x_values", []) + latency_data_b2.get("x_values", [])
    pdf_values = latency_data_b1.get("pdf_values", []) + latency_data_b2.get("pdf_values", [])
    #print(f"X value:{x_values}")
    #print(f"pdf values:{pdf_values}")
    # Sample multiple latency values and take the average
    if len(x_values) == len(pdf_values) and len(x_values) > 0:
        #sampled_latencies = random.choices(x_values, weights=pdf_values, k=3)
        #sampled_latency = sum(sampled_latencies) / len(sampled_latencies)
        sampled_latency = random.choices(x_values, weights=pdf_values, k=1)[0]
    else:
        sampled_latency = None
        print("Error: x_values and pdf_values must have the same length and cannot be empty.")

    # Similar structure for dropped packets
    dropped_packet_data_b1 = parameter.get("0.004_128KB_b1", {}).get("Dropped Packets", {})
    dropped_packet_data_b2 = parameter.get("0.004_128KB_b2", {}).get("Dropped Packets", {})
    dropped_packet_values = dropped_packet_data_b1.get("x_values", []) + dropped_packet_data_b2.get("x_values", [])
    dropped_packet_pdf_values = dropped_packet_data_b1.get("pdf_values", []) + dropped_packet_data_b2.get("pdf_values", [])
    
    # Sample a single dropped packet value
    if len(dropped_packet_values) == len(dropped_packet_pdf_values) and len(dropped_packet_values) > 0:
        sampled_dropped_packets = random.choices(dropped_packet_values, weights=dropped_packet_pdf_values, k=1)[0]
    else:
        sampled_dropped_packets = None
        print("Error: dropped_packet_values and pdf_values must have the same length and cannot be empty.")
    
    return sampled_latency, sampled_dropped_packets


# Data extraction functions
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

# Packet receiving and forwarding function
def receive_and_forward_packets(receive_ip, receive_port):
    udp_receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_receive_socket.bind((receive_ip, receive_port))

    udp_forward_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"Listening for packets on {receive_ip}:{receive_port}...")

    packet_count = 1
    forwarded_packet_count = 1
    filtered_packet_count = 0
    csv_filename = 'packet_latency_log_6.csv'
    rec_packets = 0

    with open(csv_filename, mode='w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['Sender City', 'Receiving IP', 'Forwarding IP', 'Sender Timestamp', 'Receiver Timestamp', 'Forwarding Timestamp', 'Latency (ms)', 'Sampled Latency (ms)', 'Processing Delay (ms)', 'Dropped Packets', 'Sampled Dropped Packets', 'Filtered Packets'])

        try:
            while True:
                data, addr = udp_receive_socket.recvfrom(2048)
                data_str = data.decode('utf-8')
                data_parts = data_str.split(',', 3)
                rec_packets += 1
                sent_PC = int(data_parts[0])
                sender_city = data_parts[2]

                # Check for packet drop
                packet_drop = 0
                if sent_PC > packet_count:
                    packet_drop = sent_PC - packet_count

                receiving_timestamp = int(time.time() * 1000)
                sender_timestamp = int(data_parts[1])
                temperature = extract_temperature(data_parts[3])
                humidity = extract_humidity(data_parts[3])
                light = extract_light(data_parts[3])

                # Check filters
                if temperature is not None and 0 <= temperature <= 38:
                    if humidity is not None and 15 <= humidity <= 90:
                        if light is not None and 0 <= light <= 1500:
                            # Sample from PDF for latency and dropped packets
                            time.sleep(temperature / 5000)  # Simulate impact based on sampled latency
                            
                            latency = receiving_timestamp - sender_timestamp
                            forwarding_timestamp = int(time.time() * 1000)
                            processing_delay = (forwarding_timestamp - receiving_timestamp)
                            
                            # Prepare features for prediction
                            input_frequency = 0.004
                            buffer_size_kb1 = 128
                            buffer_size_kb2 = 128
                            # Prepare the parameter to match JSON structure
                            #parameter = f"{input_frequency}_{buffer_size_kb1}KB_b1"
                            #print(f"Generated parameter: {parameter}")
                            #print(f"PDF values: {pdf_values}")  # Debugging output to confirm the content of pdf_values

                            # Attempt to sample from the PDF values
                            sampled_latency, sampled_dropped_packets = sample_from_pdf(pdf_values)
                            print(f"Sampled Latency: {sampled_latency}")
                            print(f"Sampled Dropped Packets: {sampled_dropped_packets}")

                            feature_values = np.array([[input_frequency, buffer_size_kb1, buffer_size_kb2, sampled_latency, processing_delay, sampled_dropped_packets]])

                            # Predict which bolt to forward to
                            predicted_node = model.predict(feature_values)
                            print(f"Predicted node: {predicted_node}")
                            forward_ip = "192.168.1.9" if predicted_node[0] == 0 else "192.168.1.6"
                            f_data = f"{forwarded_packet_count},{forwarding_timestamp},{data_str}"
                            udp_forward_socket.sendto(f_data.encode('utf-8'), (forward_ip, 5000))
                            forwarded_packet_count += 1

                            # Log forwarded packet
                            csv_writer.writerow([sender_city, receive_ip, forward_ip, sender_timestamp, receiving_timestamp, forwarding_timestamp, receiving_timestamp - sender_timestamp, sampled_latency, processing_delay, packet_drop, sampled_dropped_packets, 0])
                            csvfile.flush()
                        else:
                            filtered_packet_count += 1
                            csv_writer.writerow([sender_city, receive_ip, "Filtered", sender_timestamp, receiving_timestamp, "Filtered", receiving_timestamp - sender_timestamp, "N/A", "N/A", packet_drop, "N/A", 1])
                            csvfile.flush()
                    else:
                        filtered_packet_count += 1
                        csv_writer.writerow([sender_city, receive_ip, "Filtered", sender_timestamp, receiving_timestamp, "Filtered", receiving_timestamp - sender_timestamp, "N/A", "N/A", packet_drop, "N/A", 1])
                        csvfile.flush()
                else:
                    filtered_packet_count += 1
                    csv_writer.writerow([sender_city, receive_ip, "Filtered", sender_timestamp, receiving_timestamp, "Filtered", receiving_timestamp - sender_timestamp, "N/A", "N/A", packet_drop, "N/A", 1])
                    csvfile.flush()

                packet_count = sent_PC + 1

        except KeyboardInterrupt:
            print("\nStopped by user.")
        finally:
            csv_writer.writerow([])
            csv_writer.writerow(['Summary'])
            csv_writer.writerow(['Total Packets Sent', 'Total Packets Received', 'Total Packets Forwarded', 'Total Packets Filtered'])
            csv_writer.writerow([packet_count - 1, rec_packets, forwarded_packet_count - 1, filtered_packet_count])

            print("\nSummary:")
            print(f"Total packets sent: {packet_count - 1}")
            print(f"Total packets received: {rec_packets}")
            print(f"Total packets forwarded: {forwarded_packet_count - 1}")
            print(f"Total packets filtered out: {filtered_packet_count}")

            udp_receive_socket.close()
            udp_forward_socket.close()

if __name__ == "__main__":
    listen_ip = "192.168.1.3"
    listen_port = 5000

    receive_and_forward_packets(listen_ip, listen_port)
