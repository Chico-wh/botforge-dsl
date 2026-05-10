"""
BotForge Example: Obstacle Avoidance

Mini rover with ultrasonic sensor. Drives forward, turns left when
an obstacle is detected within 20 cm.

    botforge build examples/obstacle_avoidance.py --target arduino
"""

from botforge import Bot, Wheels, Ultrasonic

bot = Bot("mini_rover")

bot.use(Wheels(left=(5, 6), right=(9, 10)))
front = bot.use(Ultrasonic("front", trigger=7, echo=8))


@bot.loop
def main():
    if front.distance < 20:
        bot.turn_left(speed=50)
    else:
        bot.forward(speed=80)
