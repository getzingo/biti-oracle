from utils.classes.Fortune import Fortune


def start_fortune_generation(sensor_val) -> Fortune:
        fortune = Fortune(sensor_val=sensor_val)
        fortune.start_generation()
        return fortune