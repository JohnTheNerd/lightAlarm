from lifxlan import LifxLAN, Light, MultiZoneLight

class Bulb(object):
    def __init__(self, ip, mac, multizone=False):
        self.rapid = False
        if multizone:
            self.bulb = MultiZoneLight(mac, ip)
        else:
            self.bulb = Light(mac, ip)

    def supports_multizone(self):
        return self.bulb.supports_multizone()

    def get_color_zones(self):
        return self.bulb.get_color_zones()

    def set_zone_color(self, startZone, endZone, color, duration=5):
        return self.bulb.set_zone_color(startZone, endZone, color, duration=duration, rapid=self.rapid)

    def set_zone_colors(self, colors, duration=5):
        return self.bulb.set_zone_colors(colors, duration=duration, rapid=self.rapid)

    def set_power(self, power, duration=5):
        if duration:
            self.bulb.set_power(power, duration=duration, rapid=self.rapid)
        else:
            self.bulb.set_power(power)

    def get_power(self):
        return self.bulb.get_power()

    def set_color(self, color, duration=5):
        if duration:
            self.bulb.set_color(color, duration=duration, rapid=self.rapid)
        else:
            self.bulb.set_color(color)

    def get_color(self):
        return self.bulb.get_color()

    def get_label(self):
        return self.bulb.get_label()

    def get_brightness(self):
        return self.bulb.get_color()[2]

    def set_brightness(self, brightness, duration=5):
        return self.bulb.set_brightness(brightness, duration, rapid=self.rapid)

    def fast_mode(self, hostIP = None):
        self.rapid = True

    def slow_mode(self):
        self.rapid = False
