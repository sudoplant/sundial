from pymodbus.client import ModbusTcpClient
from gpiozero import PWMLED
from time import sleep

# =============================================================================
# CONFIGURATION
# =============================================================================

# Network settings
INVERTER_HOST = '192.168.0.160'  # IP address of the SMA inverter
MODBUS_PORT = 502                # MODBUS TCP port (must enable MODBUS in inverter settings)

# Inverter settings
MAX_POWER = 5760                 # Maximum power output from inverter (watts)
POWER_REGISTER = 30775           # MODBUS register address for instantaneous power
POWER_REGISTER_COUNT = 2         # Number of registers to read for power value

# GPIO settings
GPIO_PIN = 23                    # GPIO pin for PWM output to ammeter

# Communication settings
POLL_INTERVAL = 1                # Seconds between power readings
CONNECTION_TIMEOUT = 3           # MODBUS connection timeout (seconds)
CONNECTION_RETRIES = 3           # Number of connection retry attempts

# =============================================================================


class SundialMonitor:
    """Monitors SMA inverter power output and displays on analog ammeter via PWM."""

    def __init__(self, host, port, gpio_pin, max_power, poll_interval):
        """
        Initialize the SundialMonitor.

        Args:
            host: IP address of the SMA inverter
            port: MODBUS TCP port
            gpio_pin: GPIO pin number for PWM output to ammeter
            max_power: Maximum power output from inverter (watts), used to scale ammeter
            poll_interval: Seconds between power readings
        """
        self.host = host
        self.port = port
        self.gpio_pin = gpio_pin
        self.max_power = max_power
        self.poll_interval = poll_interval
        self.client = None
        self.led = None

    def connect(self):
        """Initialize MODBUS client and GPIO output."""
        self.client = ModbusTcpClient(
            host=self.host,
            port=self.port,
            timeout=CONNECTION_TIMEOUT,
            retries=CONNECTION_RETRIES,
        )
        self.led = PWMLED(self.gpio_pin)

    def read_power(self):
        """Read instantaneous power from inverter. Returns power in watts or None on failure."""
        if not self.client.connect():
            return None
        power = self.client.read_holding_registers(
            address=POWER_REGISTER,
            count=POWER_REGISTER_COUNT,
        )
        power_value = self.client.convert_from_registers(
            power.registers,
            data_type=self.client.DATATYPE.INT32,
        )
        return power_value

    def update_ammeter(self, power_value):
        """Update ammeter PWM duty cycle based on power value."""
        self.led.value = power_value / self.max_power

    def run(self):
        """Main loop: poll inverter and update ammeter."""
        self.connect()
        try:
            while True:
                power_value = self.read_power()
                if power_value is not None:
                    print("kW:", power_value)
                    self.update_ammeter(power_value)
                else:
                    print("Connection failed")
                sleep(self.poll_interval)
        except KeyboardInterrupt:
            pass
        finally:
            if self.client:
                self.client.close()


# Run only when executed directly, not when imported as a module
if __name__ == "__main__":
    monitor = SundialMonitor(
        host=INVERTER_HOST,
        port=MODBUS_PORT,
        gpio_pin=GPIO_PIN,
        max_power=MAX_POWER,
        poll_interval=POLL_INTERVAL,
    )
    monitor.run()
