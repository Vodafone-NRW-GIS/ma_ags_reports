#!/usr/bin/env python
# # -*- coding: utf-8 -*-

from sqlalchemy.schema import Column, Table, Index, MetaData
from sqlalchemy.types import Integer, String, Date

import utils.general_utils as utils


def ags_service_layer_report_table_def(table_name, schema=None):

    if schema is None:
        try:
            schema, table_name = table_name.split(".")
        except ValueError as e:
            schema = None

    meta = MetaData()

    ags_service_layer_report_table_def = Table(
        table_name, meta,
        Column('objectid', Integer, primary_key=True, comment='Unique key.'),
        Column('svc_name', String(100), comment='Name of the map service.'),
        Column('svc_folder', String(100), comment='Directory of the map service.'),
        Column('env', String(10), comment='Service environment.'),
        Column('db', String(50), comment='Source database for service layer.'),
        Column('db_schema', String(50), comment='Source database schema for service layer.'),
        Column('db_table', String(50), comment='Source database table for service layer.'),
        Column('sde', String(100), comment='SDE connection file used to import layer.'),
        Column('mxd', String(200), comment='Path to map document containing layer definition.'),
        Column('reference_date', Date, comment='Reference date for information retrieval.'),
        Index("ref_date_idx_%s" % utils.get_random_string().lower(), 'reference_date'),
        schema=schema,
        comment='Information about layers in ArcGIS server services.'
    )

    return ags_service_layer_report_table_def
