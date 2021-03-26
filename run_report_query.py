#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import argparse

from reports.query_ags_service_layers import query_ags_service_layers
from reports.query_mapapps_maps import query_mapapps_maps

import utils.general_utils as utils

env = utils.get_environment(os.path.join(".", 'reports', 'reports'))
query_environments = list(env['environments'].keys())
query_environments.append('all')

CHOICES = ['ags_service_layers', 'mapapps_maps', 'all']

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=("Query information about GIS configuration"))
    parser.add_argument(
        '--dry-run', dest='dry_run', required=False, default=False,
        action='store_true', help='Conduct a dry run only')
    parser.add_argument(
        '--initial', dest='initial', required=False, default=False,
        action='store_true', help='(Re-)Create target table initially')
    parser.add_argument(
        '-e', '--environment', dest='query_environment', required=False, default=query_environments[-1],
        choices=query_environments, help='Name of the environment to be queried')
    parser.add_argument(
        '-l', '--limit', dest='limit', default=0, type=int, nargs='?',
        help='Maximum number of source entries to be processed')
    parser.add_argument(
        dest='report_type', help='The kind of report to be created',
        choices=CHOICES)

    args = vars(parser.parse_args())

    utils.prepare_logging(__file__, screen_only=True)

    if args['report_type'] in ['ags_service_layers', 'all']:
        if args['query_environment'] == 'all':
            for e in query_environments:
                if e == 'all':
                    continue
                args['query_environment'] = e
                logging.info("Quering ArcGIS server layers for environment: %s\n" % e)
                query_ags_service_layers(args)
            else:
                # re-setting query_environment to make it work for all environments again below
                # TODO: this is somewhat dumb, have to think of something better later
                args['query_environment'] = 'all'
        else:
            logging.info("Querying ArcGIS server layers for single environment: %s\n" % args['query_environment'])
            query_ags_service_layers(args)
    if args['report_type'] in ['mapapps_maps', 'all']:
        if args['query_environment'] == 'all':
            for e in query_environments:
                if e == 'all':
                    continue
                args['query_environment'] = e
                logging.info("Quering map.apps for environment: %s\n" % e)
                query_mapapps_maps(args)
        else:
            logging.info("Querying map.apps for single environment: %s\n" % args['query_environment'])
            query_mapapps_maps(args)
