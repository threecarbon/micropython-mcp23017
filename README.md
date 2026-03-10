# micropython-mcp23017

MicroPython driver for the MCP23017 16-bit I/O expander.

Single file. No dependencies. MicroPython, not CircuitPython.

Based on [micropython-mcp23017](https://github.com/mcauser/micropython-mcp23017) by **Mike Causer**. This fork adds VirtualPin (machine.Pin-compatible interface), interrupt configuration, bank mode support, and diagnostic helpers.

[Datasheet (PDF)](https://ww1.microchip.com/downloads/en/devicedoc/20001952c.pdf)

## Features

- 16 GPIO pins across two 8-bit ports (A and B)
- `VirtualPin` class mimics `machine.Pin` API for drop-in use
- Input with optional 100k pull-up resistors
- Interrupt-on-change with configurable trigger modes
- Bank 0 and Bank 1 register addressing
- Mirrored or independent INTA/INTB outputs
- `test()` diagnostic summary

## Usage

### Setup

```python
from machine import I2C, Pin
from mcp23017 import MCP23017

i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400_000)
mcp = MCP23017(i2c)           # default address 0x20
mcp = MCP23017(i2c, 0x27)     # custom address (A0-A2 all high)
```

### Pin Access

```python
# Configure a single pin
mcp.pin(0, mode=1, pullup=1)     # pin 0: input with pull-up
mcp.pin(8, mode=0, value=1)      # pin 8: output, high

# Read a pin
val = mcp.pin(0)                  # returns True/False

# VirtualPin — works like machine.Pin
led = mcp[8]                      # get VirtualPin for pin 8
led.output(1)                     # configure as output, set high
led.off()                         # set low
led.toggle()                      # toggle

btn = mcp[0]                      # get VirtualPin for pin 0
btn.input(pull=btn.PULL_UP)       # configure as input with pull-up
print(btn.value())                # read value
```

### Bulk Port Access

All 16-bit register properties combine port A (low byte) and port B (high byte):

```python
mcp.mode = 0x00FF            # port A: all inputs, port B: all outputs
mcp.pullup = 0x00FF          # pull-ups on port A inputs
mcp.gpio = 0xFF00            # port B outputs all high

# Read all pins at once
print(f"GPIO: 0x{mcp.gpio:04X}")

# Access ports individually
mcp.porta.mode = 0xFF        # port A: all inputs
mcp.portb.gpio = 0x0F        # port B: lower 4 pins high
```

### Interrupts

```python
# Enable interrupt on pin 3, trigger on change from previous value
mcp.pin(3, mode=1, pullup=1, interrupt_enable=1)

# Or compare against a default value
mcp.pin(3, mode=1, pullup=1,
        interrupt_enable=1,
        interrupt_compare_default=1,  # compare to DEFVAL
        default_value=1)              # trigger when pin goes low

# Mirror INTA and INTB (both fire for either port)
mcp.config(interrupt_mirror=1)

# In your external IRQ handler:
flags = mcp.interrupt_triggered_gpio(0)    # which pin(s) on port A
captured = mcp.interrupt_captured_gpio(0)  # pin states at interrupt time
```

### Configuration

```python
mcp.config(
    interrupt_polarity=1,       # INT pins active high (default: active low)
    interrupt_open_drain=1,     # INT pins open-drain (overrides polarity)
    interrupt_mirror=1,         # mirror INTA/INTB
    sda_slew=1,                 # disable SDA slew rate control
    sequential_operation=1,     # disable address pointer auto-increment
    bank=1,                     # bank 1 register layout
)
```

### Diagnostics

```python
mcp.test()
# MCP23017
#   address: 0x20
#   iocon: 0x00 [default]
#   port A: dir=0b11111111 pullup=0b0 gpio=0b0
#   port B: dir=0b11111111 pullup=0b0 gpio=0b0
```

## Pin Numbering

| Pin | Port | Bit | Chip Pin |
|-----|------|-----|----------|
| 0-7 | A | 0-7 | GPA0-GPA7 |
| 8-15 | B | 0-7 | GPB0-GPB7 |

## I2C Address

Base address is `0x20`. Pins A0, A1, A2 set the lower 3 bits:

| A2 | A1 | A0 | Address |
|----|----|----|---------|
| 0 | 0 | 0 | 0x20 |
| 0 | 0 | 1 | 0x21 |
| 0 | 1 | 0 | 0x22 |
| ... | ... | ... | ... |
| 1 | 1 | 1 | 0x27 |

## Credits

Originally by [Mike Causer](https://github.com/mcauser/micropython-mcp23017). This version is a clean up and update with VirtualPin support, interrupt helpers, and diagnostic output.

## License

MIT License. See [LICENSE](LICENSE) for details.
