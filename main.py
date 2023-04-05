import sacn
import time
import numpy as np
import pickle
import os

from config import haze_machines_config



class HazeMachine:
    def __init__(self, sacn_universe, sacn_address, bottle_size):
        self.sacn_universe = sacn_universe
        self.sacn_address = sacn_address
        self.bottle_size = bottle_size
        self.current_consumption = self.load_current_consumption()
        self.last_packet_time = None

    def haze_fluid_duration(self, pump_speed):
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
        pump_speeds = list(consumption_table.keys())
        consumption_rates = [entry[0] for entry in consumption_table.values()]
        consumption_rate = np.interp(pump_speed, pump_speeds, consumption_rates)
        return consumption_rate

    def save_current_consumption(self):
        file_name = f'current_consumption_{self.sacn_universe}_{self.sacn_address}.pkl'
        with open(file_name, 'wb') as f:
            pickle.dump(self.current_consumption, f)

    def load_current_consumption(self):
        file_name = f'current_consumption_{self.sacn_universe}_{self.sacn_address}.pkl'
        if os.path.exists(file_name):
            with open(file_name, 'rb') as f:
                return pickle.load(f)
        else:
            return 0

    def refill_haze_bottle(self):
        self.current_consumption = 0
        self.save_current_consumption()

    def on_data(self, packet):
        dmx_value = packet.dmxData[self.sacn_address - 1]
        pump_speed = (dmx_value / 255) * 100

        current_packet_time = time.time()
        if self.last_packet_time is not None:
            elapsed_time = current_packet_time - self.last_packet_time
        else:
            elapsed_time = 1
        self.last_packet_time = current_packet_time

        consumption_rate = self.haze_fluid_duration(pump_speed)
        self.current_consumption += (consumption_rate / 3600) * elapsed_time
        self.save_current_consumption()

        remaining_haze = self.bottle_size * 1000 - self.current_consumption
        if remaining_haze < 100:
            print(f"Warning: Haze fluid in machine {self.sacn_universe}-{self.sacn_address} is almost empty, please refill the bottle soon!")

        print(f"Machine {self.sacn_universe}-{self.sacn_address}: Pump speed: {pump_speed:.2f}%, Fluid consumption rate: {consumption_rate:.2f} ml/hour, Remaining haze: {remaining_haze:.2f} ml")



haze_machines = [HazeMachine(**config) for config in haze_machines_config]
haze_machine_dict = {(machine.sacn_universe, machine.sacn_address): machine for machine in haze_machines}

def on_data(packet):
    machine = haze_machine_dict.get((packet.universe, packet.sourceAddress))
    if machine:
        machine.on_data(packet)

receiver = sacn.sACNreceiver()
receiver.start()  # Start the receiving thread
receiver.listen_on('universe', callback=on_data)

unique_universes = set(machine.sacn_universe for machine in haze_machines)
for universe in unique_universes:
    receiver.join_multicast(universe)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping sACN receiver...")
    for universe in unique_universes:
        receiver.leave_multicast(universe)
    receiver.stop()  # Stop the receiving thread