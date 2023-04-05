import sacn
import time

def simple_on_data(packet):
    print(f"Packet received: Universe {packet.universe}, Address {packet.sourceAddress}")

receiver = sacn.sACNreceiver()
receiver.start()
receiver.listen_on('universe', callback=simple_on_data)

try:
    receiver.join_multicast(1)
    receiver.join_multicast(2)
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping sACN receiver...")
    receiver.leave_multicast(1)
    receiver.leave_multicast(2)
    receiver.stop()