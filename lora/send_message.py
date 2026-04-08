import digitalio
import board
import busio
import adafruit_rfm9x

RADIO_FREQ_MHZ = 915.0
CS = digitalio.DigitalInOut(board.CE1)
RESET = digitalio.DigitalInOut(board.D17)
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ, baudrate=115200)
rfm9x.signal_bandwidth = 125000
# rfm9x.spreading_factor = 7
# rfm9x.coding_rate = 5
# rfm9x.preamble_length = 8
# rfm9x.enable_crc = False

rfm9x.send(b"What's up?")