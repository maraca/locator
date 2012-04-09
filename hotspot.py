#!/usr/bin/python2.6
"""Web server that displays the hotspots around you."""


__author__ = 'cozzi.martin@gmail.com'


import math

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.template
import tornado.web

from tornado.options import define
from tornado.options import options

from pymaps import Icon
from pymaps import Map
from pymaps import PyMap

define('port', default=8888, help='Port number', type=int)
define('prod', default=True, help='set to false for debug', type=bool)

class MainHandler(tornado.web.RequestHandler):


    def get(self):
        t = tornado.template.Template('<html><head>%s</head><body onload="load()" onunload="GUnload()">\
                    <div id="map" style="width: 760px; height: 460px"></div>\
                    </body></html>' % self.get_map())
        t = tornado.template.Template(self.get_map())
        self.write(t.generate())
        self.finish()

    def post(self):
        hotspot = self.get_argument('hotspot', default=False)
        lat = float(self.get_argument('lat'))
        lon = float(self.get_argument('lon'))
        if hotspot:
            self._add_hotspot((lat, lon))
        else:
            self.application.pins.append((lat, lon))

        self.finish()

    
    def _add_hotspot(self, pin):
        exists = False
        if self.application.hotspots:
            for location in self.application.hotspots:
                if math.fabs(location[0] - pin[0]) < 0.001 and\
                        math.fabs(location[1] - pin[1]) < 0.001:
                    exists = True

        if exists is False:
            self.application.hotspots.append(pin)


    def get_map(self):
        """Displays a google map oO"""
        tmap = Map()
        tmap.zoom = 12

        # San Francisco 
        top_left = (37.793508, -122.511978)
        bottom_right = (37.742485, -122.369156)
        tmap.center = ((top_left[0] + bottom_right[0]) / 2,
                (top_left[1] + bottom_right[1]) / 2)

        pin_icon = Icon(id='pin',
                image="http://gmaps-samples.googlecode.com/svn/trunk/markers/blue/blank.png"
                )

        for gps in self.application.pins:
            point = (gps[0], gps[1], 'derp', pin_icon.id)
            tmap.setpoint(point)

        
        for gps in self.application.hotspots:
            point = (gps[0], gps[1], 'derp')
            tmap.setpoint(point)

        gmap = PyMap(key='AIzaSyA59m0VtN62qf7Gu_c-_PSX_Eiw_t2vzBA', maplist=[tmap])
        gmap.addicon(pin_icon)

        mapcode = gmap.showhtml()

        return mapcode


class BaseApplication(tornado.web.Application):

    def __init__(self):
        handlers = [(r'/', MainHandler),]

        settings = dict()
        if options.prod is not True:
            settings['debug'] = 'debug'

        tornado.web.Application.__init__(self, handlers, **settings)

        self.pins = list()
        self.hotspots = list()

def main():
    tornado.options.parse_command_line()

    tornado.options.enable_pretty_logging()
    http_server = tornado.httpserver.HTTPServer(BaseApplication())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
