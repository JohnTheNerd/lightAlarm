import yeelight, time

class Bulb(object):
    def __init__(self, ip, mac, multizone=False):
        self.bulb = yeelight.Bulb(ip)

    def supports_multizone(self):
        return False    # this lib does not support multizone afaik

    def set_power(self, power, duration=150):
        if power:
            result = self.bulb.turn_on(duration=duration)
        else:
            result = self.bulb.turn_off(duration=duration)
        time.sleep(0.1)
        return result

    def get_power(self):
        result = self.bulb.get_properties(requested_properties=['power'])
        if result['power'] == 'on':
            return True
        else:
            return False

    def set_color(self, color, duration=150):
        hue = int((color[0] * 360) / 65535)
        sat = int((color[1] * 100) / 65535)
        bright = int((color[2] * 100) / 65535)
        if bright == 0:
            bright = 1
        result = self.bulb.set_hsv(hue, sat, bright, duration=duration)
        time.sleep(0.1)
        return result

    def get_color(self):
        result = self.bulb.get_properties(requested_properties=['hue', 'sat', 'bright', 'ct'])
        hue = int((int(result['hue']) * 65535) / 360)
        sat = int((int(result['sat']) * 65535) / 100)
        bright = int((int(result['bright']) * 65535) / 100)
        temp = result['ct']
        return [int(hue), int(sat), int(bright), int(temp)]

    def get_label(self):
        result = self.bulb.get_properties(requested_properties=['name'])
        return str(result['name'])

    def get_brightness(self):
        result = self.bulb.get_properties(requested_properties=['bright'])
        return (int(result['bright']) / 100) * 65535

    def set_brightness(self, brightness, duration=100):
        bright = (brightness * 100) / 65535
        if bright == 0:
            bright = 1
        return self.bulb.set_brightness(bright, duration=duration)

    def fast_mode(self, port = 55443, hostIP = None):
        return self.bulb.start_music(port, ip=hostIP)

    def slow_mode(self):
        return self.bulb.stop_music()
