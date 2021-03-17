#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from reports.publish_report import publish_report

import utils.general_utils as utils

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description=("Query information about ArcGIS server layers"))
    parser.add_argument(
        '--dry-run', dest='dry_run', required=False, default=False,
        action='store_true', help='Conduct a dry run only')
    parser.add_argument(
        dest='report_type', help='The kind of report to be created',
        choices=['ags_service_layers', 'mapapps_maps', 'all'])

    args = vars(parser.parse_args())

    utils.prepare_logging(__file__, screen_only=True)

    publish_report(args)
