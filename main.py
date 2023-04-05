import sacn
import time
import numpy as np
import pickle
import os

def haze_fluid_duration(pump_speed):

    consumption_table = {
        0: (0,),
        10: (11.976047904191617,),
        20: (24.096385542168676,),
        30: (41.666666666666664,),
        40: (60.60606060606061,),
        50: (95.23809523809524,),
        60: (153.84615384615384,),
        70: (240.96385542168673,),
        80: (363.6363636363636,),
        90: (606.0606060606061,),
        100: (952.3809523809523,),
    }

    # Extract pump speeds and consumption rates from the consumption_table
    pump_speeds = list(consumption_table.keys())
    consumption_rates = [entry[0] for entry in consumption_table.values()]

    # Perform linear interpolation
    consumption_rate = np.interp(pump_speed, pump_speeds, consumption_rates)
    
    return consumption_rate
    
def save_current_consumption(consumption):
    with open('current_consumption.pkl', 'wb') as f:
        pickle.dump(consumption, f)

def load_current_consumption():
    if os.path.exists('current_consumption.pkl'):
        with open('current_consumption.pkl', 'rb') as f:
            return pickle.load(f)
    else:
        return 0

def refill_haze_bottle():
    save_current_consumption(0)



# Modify these variables based on your setup
sacn_universe = 1
sacn_address = 100  # Specific address to monitor (1-512)
bottle_size = 2     # Fluid container size (2, 10, or 20 liters)

receiver = sacn.sACNreceiver()
receiver.start()  # Start the receiving thread

last_packet_time = None

# Define the callback function
@receiver.listen_on('universe', universe=sacn_universe)
def on_data(packet):  # packet type: sacn.DataPacket
    global last_packet_time

    dmx_value = packet.dmxData[sacn_address - 1]  # sACN address is 1-based
    pump_speed = (dmx_value / 255) * 100  # Convert DMX value to percentage

    # Calculate the elapsed time between packets
    current_packet_time = time.time()
    if last_packet_time is not None:
        elapsed_time = current_packet_time - last_packet_time
    else:
        elapsed_time = 1  # Default to 1 second for the first packet
    last_packet_time = current_packet_time

    try:
        consumption_rate = haze_fluid_duration(pump_speed)

        current_consumption = load_current_consumption()
        new_consumption = current_consumption + (consumption_rate / 3600) * elapsed_time  # ml/s
        save_current_consumption(new_consumption)

        remaining_haze = bottle_size * 1000 - new_consumption  # Convert to ml
        if remaining_haze < 100:  # Alert when remaining haze is less than 100 ml
            print("Warning: Haze fluid is almost empty, please refill the bottle soon!")
        
        print(f"Pump speed: {pump_speed:.2f}%, Fluid consumption rate: {consumption_rate:.2f} ml/hour, Remaining haze: {remaining_haze:.2f} ml")
    except ValueError as e:
        print(e)

receiver.join_multicast(sacn_universe)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping sACN receiver...")
    receiver.leave_multicast(sacn_universe)
    receiver.stop()  # Stop the receiving thread