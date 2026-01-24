# Readme

This is a python application that polls SMA Sunny Boy inverters via MODBUS TCP and updates an an analog ammeter with the instantaneous active power. It was developed and tested on a Raspberry Pi Zero W, but it should work on all Pi models after verifying the GPIO pinout. This code can be modified to publish the data to a web server or even update other pins with statuses or measurements from the inverter. 

## Prerequisites

Before running this code, please install the following prerequisites. 

`sudo apt install python3 python3-pip`

`pip install pymodbus`

`pip install gpiozero` or `sudo apt install python3-gpiozero`

`pip install numpy`

The SMA inverter needs to have its MODBUS TCP server enabled (Parameter.Mb.TcpSrv.IsOn). I highly recommend changing the default port from `502` to something different (Parameter.Mb.TcpSrv.Port). 

## Configuration

All configuration parameters are centralized at the top of `sundial.py`. Edit the following constants to match your setup:

1. `INVERTER_HOST` - IP address of the SMA inverter
2. `MODBUS_PORT` - MODBUS TCP port (the number that you changed from default earlier!)
3. `GPIO_PIN` - GPIO pin for PWM output (for example, `23` corresponds to pin 16 on a Pi Zero W)
4. `MAX_POWER` - Maximum inverter output in watts (for example, my inverter has a full load capacity of 5760 watts. By dividing instantaneous power by this number, a dimensionless ratio between 0 and 1 is established to adjust the PWM output duty cycle).

The code can be modified to pull other quantities from the inverter. A list of quantities with their MODBUS addresses (e.g. 30775) and data types (e.g. INT32) can be found here: https://files.sma.de/downloads/EDMx-Modbus-TI-en-16.pdf

## Hardware

First, start by identifying a GPIO pin and ground pin to be used with your ammeter. The Pi Zero W pinout and pre-defined output for this code (GPIO23) are shown below. 
<img width="743" height="447" alt="image" src="https://github.com/user-attachments/assets/4232dd27-54ab-441d-8207-7460d8bf4455" />

Next, we need to wire up a basic analog circuit. It includes a current limiting resistor, chosen specifically for our ammeter, a capacitor to form a basic RC filter to smooth out the PWM signal, and an optional potentiometer for fine tuning the sweep.
<img width="600" height="400" alt="image" src="https://github.com/user-attachments/assets/1127b99e-efb0-40c9-8522-fa26c66e2a37" />

When choosing your resistor, you must consider the full-scale current of your ammeter. My Jewell Model 55 ammeter has a full-scale current of 500μA. Since the Pi GPIO output pins operate at 3.3V, we'll use Ohm's law to calculate the resistance that would restrict current to 500μA at this voltage. 

$R = \frac{3.3V}{500μA}$ = 6.6kΩ

To account for slight errors in the pi's output voltage and the ammeter's calibration, wiring the middle and outside lead of a similarly sized potentiometer enables you to "dial in" the full-scale current so 50% truly shows halfway on the meter, and 100% at full scale.

Lastly, the capacitor can be installed to smooth out the choppy pulse-width modulation signal into a constant voltage. You can choose anything from 5μF up to 100μF, electrolytic or ceramic. I honestly didn't see a lot of difference in the "jumpiness" of my ammeter after including the capacitor, as the inductance of the meter did a good enough job of smoothing the PWM by itself. Please feel free to suggest a better circuit to smooth the output. 

## Calibration

Analog ammeters often have non-linear response, meaning 50% PWM output may not display exactly 50% on the dial. The calibration feature corrects for this by measuring the actual dial readings at known PWM levels and interpolating between them.

To calibrate your ammeter:

1. Run `python sundial.py --calibrate`
2. The script will output PWM at each calibration level (0%, 25%, 50%, 75%, 100% by default)
3. For each level, read the dial and enter the actual reading
4. Calibration data is saved to `calibration.json`

You can customize the calibration points by editing `CALIBRATION_PERCENTAGES` in the configuration section.

## Running

From the folder containing the script, simply type `python sundial.py` to run the code. If your pi successfully connects to your inverter, you'll see the instantaneous power update in your terminal every second. The calibration from `calibration.json` is automatically applied if present.

Run `python sundial.py --help` to see all available options.

Run `nohup python sundial.py &` if you want the code to stay alive after you disconnect your terminal session. 
