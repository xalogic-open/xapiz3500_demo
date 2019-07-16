import time
import spidev
from gpiozero import LED



k210_reset = LED(27)

k210_reset.off()
time.sleep(1)
k210_reset.on()

