#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from reports.query_ags_service_layers import query_ags_service_layers
from reports.query_mapapps_maps import query_mapapps_maps

import utils.general_utils as utils

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=("Query information about GIS configuration"))
    parser.add_argument(
        '--dry-run', dest='dry_run', required=False, default=False,
        action='store_true', help='Conduct a dry run only')
    parser.add_argument(
        '--initial', dest='initial', required=False, default=False,
        action='store_true', help='(Re-)Create target table initially')
    parser.add_argument(
        '-e', '--environment', dest='query_environment', required=False, default='dev',
        help='Name of the environment to be queried')
    parser.add_argument(
        '-l', '--limit', dest='limit', default=0, type=int, nargs='?',
        help='Maximum number of source entries to be processed')
    parser.add_argument(
        dest='report_type', help='The kind of report to be created',
        choices=['ags_service_layers', 'mapapps_maps', 'all'])

    args = vars(parser.parse_args())

    utils.prepare_logging(__file__, screen_only=True)

    if args['report_type'] == 'ags_service_layers':
        query_ags_service_layers(args)
    elif args['report_type'] == 'mapapps_maps':
        query_mapapps_maps(args)
    elif args['report_type'] == 'all':
        query_ags_service_layers(args)
        query_mapapps_maps(args)
