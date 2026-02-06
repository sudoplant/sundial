import argparse
import json
import numpy as np
from pathlib import Path
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

# Calibration settings
CALIBRATION_FILE = Path(__file__).parent / 'calibration.json'  # Path to calibration data
CALIBRATION_PERCENTAGES = [0, 25, 50, 75, 100]                 # PWM levels for calibration

# =============================================================================


def load_calibration(calibration_file, calibration_percentages):
    """Load calibration points from JSON file. Returns list of (pwm, dial) tuples."""
    default_points = [(p, p) for p in calibration_percentages]

    if not calibration_file.exists():
        print(f"Warning: {calibration_file} not found, using linear default")
        return default_points

    with open(calibration_file, 'r') as f:
        data = json.load(f)

    if not data.get('calibrated', False):
        print("Warning: Using uncalibrated default values. Run with --calibrate first.")

    return [tuple(point) for point in data['calibration_points']]


def run_calibration(gpio_pin, calibration_file, calibration_percentages):
    """Walk user through calibration process and save results."""
    print("=" * 60)
    print("SUNDIAL AMMETER CALIBRATION")
    print("=" * 60)
    print()
    print("This script will output known PWM percentages to the ammeter.")
    print("For each level, record the actual dial reading and enter it.")
    print()
    input("Press Enter to begin calibration...")
    print()

    led = PWMLED(gpio_pin)
    calibration_points = []

    try:
        for pwm_percent in calibration_percentages:
            led.value = pwm_percent / 100.0
            print(f"PWM output: {pwm_percent}%")
            print("Wait for dial to stabilize...")
            sleep(2)

            while True:
                try:
                    dial_reading = float(input("Enter dial reading (0-100): "))
                    if 0 <= dial_reading <= 100:
                        break
                    print("Value must be between 0 and 100")
                except ValueError:
                    print("Please enter a valid number")

            calibration_points.append([pwm_percent, dial_reading])
            print()
            if pwm_percent != calibration_percentages[-1]:
                input("Press Enter to continue to next point...")

    finally:
        led.value = 0
        led.close()

    calibration_data = {
        "calibration_points": calibration_points,
        "calibrated": True,
        "notes": "Calibrated using sundial.py --calibrate"
    }

    with open(calibration_file, 'w') as f:
        json.dump(calibration_data, f, indent=4)

    print("=" * 60)
    print("CALIBRATION COMPLETE")
    print("=" * 60)
    print()
    print("Saved calibration points:")
    for pwm, dial in calibration_points:
        print(f"  PWM {pwm:3}% -> Dial {dial}%")
    print()
    print(f"Calibration saved to: {calibration_file}")
    print("Run 'python sundial.py' to start monitoring with calibration applied.")


class SundialMonitor:
    """Monitors SMA inverter power output and displays on analog ammeter via PWM."""

    def __init__(self, host, port, gpio_pin, max_power, poll_interval, calibration_points):
        """
        Initialize the SundialMonitor.

        Args:
            host: IP address of the SMA inverter
            port: MODBUS TCP port
            gpio_pin: GPIO pin number for PWM output to ammeter
            max_power: Maximum power output from inverter (watts), used to scale ammeter
            poll_interval: Seconds between power readings
            calibration_points: List of (pwm%, dial%) tuples for ammeter linearization
        """
        self.host = host
        self.port = port
        self.gpio_pin = gpio_pin
        self.max_power = max_power
        self.poll_interval = poll_interval
        self.calibration_points = calibration_points
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

    def apply_calibration(self, desired_percent):
        """
        Convert desired dial reading to calibrated PWM output.

        Uses linear interpolation between calibration points.
        Given calibration data of (pwm%, dial%), this inverts the relationship
        to find: what PWM% produces the desired dial reading?

        Args:
            desired_percent: The dial reading we want to display (0-100)

        Returns:
            The PWM value (0-1) needed to achieve that dial reading
        """
        dial_values = [point[1] for point in self.calibration_points]
        pwm_values = [point[0] for point in self.calibration_points]
        pwm_percent = np.interp(desired_percent, dial_values, pwm_values)
        return pwm_percent / 100.0

    def update_ammeter(self, power_value):
        """Update ammeter PWM duty cycle based on power value with calibration."""
        power_percent = (power_value / self.max_power) * 100
        self.led.value = self.apply_calibration(power_percent)

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
    parser = argparse.ArgumentParser(
        description="Sundial: Solar inverter power monitor with analog ammeter display",
        epilog="""
Usage:
  python sundial.py              Run the monitor (reads power, updates ammeter)
  python sundial.py --calibrate  Calibrate the ammeter for accurate readings
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--calibrate',
        action='store_true',
        help='Run ammeter calibration wizard',
    )
    args = parser.parse_args()

    if args.calibrate:
        run_calibration(GPIO_PIN, CALIBRATION_FILE, CALIBRATION_PERCENTAGES)
    else:
        calibration_points = load_calibration(CALIBRATION_FILE, CALIBRATION_PERCENTAGES)
        monitor = SundialMonitor(
            host=INVERTER_HOST,
            port=MODBUS_PORT,
            gpio_pin=GPIO_PIN,
            max_power=MAX_POWER,
            poll_interval=POLL_INTERVAL,
            calibration_points=calibration_points,
        )
        monitor.run()
