"""
BotForge Example: Servo Sweep

Bot with a servo arm that reacts to an ultrasonic sensor.

    botforge build examples/servo_sweep.py --target arduino
"""

from botforge import Bot, Ultrasonic, Servo

bot = Bot("servo_bot")

front = bot.use(Ultrasonic("front", trigger=7, echo=8))
arm   = bot.use(Servo("arm", pin=3))


@bot.loop
def main():
    if front.distance < 15:
        arm.write(angle=0)
    else:
        arm.write(angle=90)
