from pymodbus.client import ModbusTcpClient
#These modules are for GPIO out to ammeter
from signal import pause 
from gpiozero import PWMLED
from time import sleep

# Create client
client = ModbusTcpClient(
    host='192.168.0.160',  # Inverter IP address
    port=502,            # Default Modbus port. Must enable MODBUS in inverter settings!
    timeout=3,              # Socket timeout
    retries=3,              # Retry count
)

#Configure output GPIO pin
led = PWMLED(23)

# Connect to inverter and update GPIO output
try:
    while (True):
        if client.connect():
    #       print("Connected")
            power= client.read_holding_registers(address=30775, count=2) #get P>
            power_value=client.convert_from_registers(power.registers,data_type>
            print("kW:",power_value)
    #print(32768-power.registers[0]) #subtract power_value from 32768
            led.value = power_value/5760 #Update GPIO pin to ammeter. Change 5760 to inverter max output.
            sleep(1)
        else:
            print("Connection failed")
except:
    client.close()


