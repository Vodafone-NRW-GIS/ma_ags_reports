#!/usr/bin/env python
# # -*- coding: utf-8 -*-


from sqlalchemy.schema import Column, Table, MetaData
from sqlalchemy.types import Integer, String, DateTime, Boolean, Date
from sqlalchemy.dialects.postgresql import ARRAY


def mapapps_service_table_def(table_name, schema=None):

    if schema is None:
        try:
            schema, table_name = table_name.split(".")
        except ValueError as e:
            schema = None

    meta = MetaData()

    mapapps_service_table_def = Table(
        table_name, meta,
        Column('objectid', Integer, primary_key=True, comment='Unique key.'),
        Column('app_id', String(255), comment='ID of the corresponding map.'),
        Column('app_title', String(512), comment='Title of the map.'),
        Column('env', String(32), comment='Environment of the corresponding map.'),
        Column('svc_id', String(100), comment='ID of the map service used in the map.'),
        Column('svc_title', String(100), comment=(
            'Title of the map service, if applicable, as specified in the map configuration')),
        Column('svc_type', String(25), comment='Type of the map service.'),
        Column('svc_url', String(512), comment=(
            'URL of the underlying map service, as specified in the map configuration.')),
        Column('svc_name', String(100), comment='Name of the underlying map service.'),
        Column('svc_env', String(32), comment='Environment of underlying map service.'),
        Column('valid', Boolean, comment='Indicates whether the service url is valid.'),
        Column('secured', Boolean, comment='Indicates whether the service is secured via Security Manager.'),
        Column('reference_date', Date, comment='Reference date of most recent data update.'),
        schema=schema,
        comment='Information about configured map services in maps.'
    )

    return mapapps_service_table_def


def mapapps_basemap_table_def(table_name, schema=None):

    if schema is None:
        try:
            schema, table_name = table_name.split(".")
        except ValueError as e:
            schema = None

    meta = MetaData()

    mapapps_basemap_table_def = Table(
        table_name, meta,
        Column('objectid', Integer, primary_key=True, comment='Unique key.'),
        Column('app_id', String(255), comment='ID of the corresponding map.'),
        Column('app_title', String(512), comment='Title of the map.'),
        Column('env', String(32), comment='Environment of the corresponding map.'),
        Column('svc_id', String(100), comment='ID of the map service used in the map.'),
        Column('svc_title', String(100), comment='Title of the map service, if applicable.'),
        Column('svc_type', String(25), comment='Type of the map service.'),
        Column('svc_description', String(1024), comment='Description of the map service, if applicable.'),
        Column('svc_url', String(512), comment='URL of the map service, as specified in the map configuration.'),
        Column('reference_date', Date, comment='Reference date of most recent data update.'),
        schema=schema,
        comment='Information about configured base map services in maps.'
    )

    return mapapps_basemap_table_def


def mapapps_search_table_def(table_name, schema=None):

    if schema is None:
        try:
            schema, table_name = table_name.split(".")
        except ValueError as e:
            schema = None

    meta = MetaData()

    mapapps_search_table_def = Table(
        table_name, meta,
        Column('objectid', Integer, primary_key=True, comment='Unique key'),
        Column('app_id', String(255), comment='ID of the corresponding map.'),
        Column('app_title', String(512), comment='Title of the map.'),
        Column('env', String(32), comment='Environment of the corresponding map.'),
        Column('search_id', String(255), comment='Unique ID of the the search store within the corresponding map.'),
        Column('title', String(512), comment='Title of the search store, shown in dropdown and selection UI.'),
        Column('description', String(2048), comment='Description of the search store.'),
        Column('url', String(2048), comment='URL of underlying map service.'),
        Column('svc_directory', String(512), comment='ArcGIS server directory of underlying map service.'),
        Column('svc_name', String(512), comment='Name of underlying map service.'),
        Column('svc_layer_id', Integer, comment=(
            'ID of the layer in the underlying map service the search is performed on.')),
        Column('svc_env', String(32), comment='Environment of underlying map service.'),
        Column('search_attribute', String(512), comment='Name of the attribute the search is performed on.'),
        Column('search_label_attribute', String(512), comment=(
            'Name of the attribute whose value is used for the result list.')),
        Column('search_priority', Integer, comment='Display priority for search store.'),
        Column('enable_pagination', Boolean, comment=(
            'Indicator whether search results are displayed on multiple pages.')),
        Column('search_pagesize', Integer, comment='Number of results in the result list per page.'),
        Column('search_typing_delay', Integer, comment=(
            'Milliseconds of delay between typing and displaying suggestions.')),
        Column('search_auto_activate', Boolean, comment='Indicator whether data store is selected when map starts.'),
        Column('search_label', String(512), comment='Placeholder text, shown in search input field on map.'),
        Column('fetch_id_property', Boolean, comment='Indicator whether ID property is automatically resolved.'),
        Column('id_property', String(512), comment='ID field (only used if fetch_id_property is False).'),
        Column('used_in_search', Boolean, comment='Indicator whether the store is used for searching.'),
        Column('used_in_selection', Boolean, comment='Indicator whether the store is used for selection.'),
        Column('reference_date', Date, comment='Reference date of most recent data update.'),
        schema=schema,
        comment='Information about configured search stores in maps.'
    )

    return mapapps_search_table_def


def mapapps_report_table_def(table_name, schema=None):

    if schema is None:
        try:
            schema, table_name = table_name.split(".")
        except ValueError as e:
            schema = None

    meta = MetaData()

    mapapps_report_table_def = Table(
        table_name, meta,
        Column('objectid', Integer, primary_key=True, comment='Unique key.'),
        Column('app_id', String(255), comment='Unique id for map.'),
        Column('env', String(32), comment='Environment of the corresponding map.'),
        Column('title', String(512), comment='Title of the map.'),
        Column('version', Integer, comment='MapApps version of the map, i.e. 3 or 4'),
        Column('description', String(2048), comment='Description of the map.'),
        Column('status', String(255), comment='Status of the map.'),
        Column('loaded_bundles', ARRAY(String), comment='Bundles loaded in the map.'),
        Column('configured_bundles', ARRAY(String), comment='Bundles configured in the map.'),
        Column('domain_bundles', ARRAY(String), comment='Domain bundles registered in the map.'),
        Column('domain_bundles_used', Boolean, comment='Indicator whether the map is currently using domain bundles.'),
        Column('enabled', Boolean, comment='Indicator whether the map is currently enabled.'),
        Column('created_at', DateTime, comment='Time of map creation.'),
        Column('created_by', String(512), comment='Name of the map creator.'),
        Column('modified_at', DateTime, comment='Time of last map modification.'),
        Column('modified_by', String(512), comment='Name of the one last modifiying the map.'),
        Column('sharedgroups_count', String(512), comment='Number of groups the map was made accessible to.'),
        Column('sharedgroups', ARRAY(String), comment='The groups the map was made accessible to.'),
        Column('url', String(512), comment='URL of the map.'),
        Column('reference_date', Date, comment='Reference date of most recent data update.'),
        schema=schema,
        comment='Information about configured maps.'
    )

    return mapapps_report_table_def
