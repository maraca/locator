#!/usr/bin/python2.6
"""Generates random gps coordinates, and stores them in elastic search.
The idea is to find which hot spots are near you.
"""

__author__ = 'cozzi.martin@gmail.com'


import jsonlib
import logging
import operator
import optparse
import random
import requests
import sys
import time
import yaml

top_left = (37.793508, -122.511978)
bottom_right = (37.742485, -122.369156)

magnolia = ((37.77024, -122.445245), (37.770439,-122.445164))
att_park = ((37.779042,-122.388489), (37.777838,-122.389927))

events = [magnolia, att_park]

def main():
    """Where the magic happens."""

    options = parse_args(sys.argv)
    # load configs
    config_file = open(options.config, 'r') 
    configs = yaml.load(config_file)
    config_file.close()

    search = Search(configs) 
    hotspot = 'http://%s' % configs.get('hotspot', 'localhost:8888')

    for i in range(options.count):
        if i % 10 == 0: # every 10 inserts, we add a pic to an event
            event = events[random.randint(0, len(events) - 1)]
            new_lat = random.uniform(event[0][0], event[1][0]) 
            new_lon = random.uniform(event[0][1], event[1][1]) 
            coords = (new_lat, new_lon)
            logging.debug('[random-event] %s', coords)
        else:
            coords = gen_random_coords()

        picture = {
            "pin": {
                "location": {
                    "lat": coords[0],
                    "lon": coords[1],
                    }
                }
            }

        res = search.post(picture, 'pin')
        data = {'lat': coords[0], 'lon': coords[1]}
        logging.debug('[insert] % s', picture)
        requests.post(hotspot, data)
        
        if i % 10 == 0:
            if is_a_hostpost(search, coords):
                data['hotspot'] = True
                requests.post(hotspot, data)
                logging.debug('[hotspot] %s', coords)


class Search:

    def __init__(self, config):
        """Configs"""
        self.config = config
        self.elasticsearch = 'http://%s' % self.config["elasticsearch"]["host"]

    def get(self, payload, object_type, index='pins'):
        return self._query(requests.get, payload, object_type, index)

    def post(self, payload, object_type, search=False, index='pins'):
        return self._query(requests.post, payload, object_type, search, index)

    def put(self, payload, object_type, index='pins'):
        return self._query(requests.put, payload, object_type, index)


    def _query(self, query_type, payload, object_type, search, index):
        """Sends a post or get query to ElasticSearcg.

        Object type should be made a list in the future.
        """
        url = '%s/%s/%s' % (self.elasticsearch, index, object_type)
        if search:
            url = '%s/_search' % url
        res = self._parse_response(query_type(url, jsonlib.write(payload)))

        logging.debug(res)
        if res is not None:
            return res 

    def _parse_response(self, req):
        """Parses a response."""

        if req.status_code not in [200, 201]:
            return None

        return jsonlib.read(req.content)
 

def is_a_hostpost(search, point):
    """Determines if something is going on around this point"""
    query = {
        "query": {
            "filtered" : {
                "query" : {
                    "match_all" : {},
                },
                "filter" : {
                    "geo_distance" : {
                        "distance" : "0.05km",
                        "pin.location" : {
                            "lat" : point[0],
                            "lon" : point[1]
                        }
                    }
                }
            }
        }
    } 

    results = search.post(query, 'pin', search=True)
    logging.debug('[query]: %s', jsonlib.write(query))
    if results:
        results = results.get('hits')
        logging.debug('[results] : %s', results)
        total = results.get('total')
        if total > 10:
            logging.info('[hotspot] %s', results)
            return True

    return False


def gen_random_coords():
    random_lat = random.uniform(top_left[0], bottom_right[0])
    random_long = random.uniform(top_left[1], bottom_right[1])

    return (random_lat, random_long)


def parse_args(argv):
    """Parses args from sys."""
    parser = optparse.OptionParser(usage='%prog [OPTIONS]', description=__doc__)
    parser.add_option('--config', dest='config', help='YAML config file')
    parser.add_option('--verbose', dest='verbose', action='store_true',
            default=False)
    parser.add_option('--stdin', dest='stdin', action='store_true',
            default=False)
    parser.add_option('--count', dest='count', type='int', default=5)


    options, args = parser.parse_args(argv)
    if len(args) > 1:
        parser.error('Unexpected argument: %s' % ', '.join(args[1:]))

    for opt in parser.option_list:
        if opt.dest:
            if getattr(options, opt.dest) is None:
                parser.error('%s is required!' % opt.get_opt_string())

    logger = logging.getLogger()
    logger.setLevel(options.verbose and logging.DEBUG or logging.INFO)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(
        logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s'))
    logger.addHandler(stream_handler)
    return options


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.error('Ctrl-C: Quitting early.')
