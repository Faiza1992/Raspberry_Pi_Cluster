#!/bin/bash

# Run each Python file in the background
python3 send_city1.py &
python3 send_city2.py &
python3 send_city3.py &
python3 send_city4.py &
python3 send_city5.py &
python3 send_city6.py &
python3 send_city7.py &

# Wait for all background jobs to finish
wait

echo "All Python scripts have completed."
