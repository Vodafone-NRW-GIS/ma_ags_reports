#!/usr/bin/env python
# # -*- coding: utf-8 -*-

import os
import re
import logging
import urllib3
import simplejson.errors
from datetime import date

import requests
from sqlalchemy import create_engine, and_

import utils.general_utils as utils
import utils.db_utils as db_utils

from table_defs.mapapps_reports import mapapps_basemap_table_def
from table_defs.mapapps_reports import mapapps_report_table_def
from table_defs.mapapps_reports import mapapps_search_table_def
from table_defs.mapapps_reports import mapapps_service_table_def

ENV = utils.get_environment(os.path.join(os.path.dirname(__file__), 'reports'))

# constants to be used throughout the process
MAP_URL_SUFFIX = "resources/apps/%s"
MAP_CFG_FILE = 'app.json'
SERVICE_REGEX = R"/rest/services/(.+)/(.+)/(?:Map|Feature)Server/?(\d+)?"

SEARCH_STORE_MAPPING = {
    'title': 'title',
    'description': 'description',
    'url': 'url',
    'id': 'search_id',
    'omniSearchSearchAttr': 'search_attribute',
    'omniSearchLabelAttr': 'search_attribute_label',
    'omniSearchDefaultLabel': 'search_label',
    'omniSearchPriority': 'search_priority',
    'omniSearchPageSize': 'search_pagesize',
    'omniSearchTypingDelay': 'search_typing_delay',
    'omniSearchAutoActivate': 'search_auto_activate',
    'fetchIdProperty': 'fetch_id_property',
    'idProperty': 'id_property',
    'enablePagination': 'enable_pagination',
}


def query_mapapps_maps(args):

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    cfg = utils.complete_configuration(ENV, args)
    cfg['ref_date'] = date.today()
    # setting default arguments
    if 'limit' not in cfg:
        cfg['limit'] = 0

    logging.info("Querying information about configured maps in '%s' environment" % cfg['query_environment'])

    # locating database configuration
    db_cfg_path = cfg['db_cfg']
    query_env = cfg['environments'][cfg['query_environment']]
    base_url = query_env['ma_base_url']

    logging.info("Establishing databases")
    conn_str = db_utils.get_db_connection(db_cfg_path, query_env['ma_db'])
    src_engine = create_engine(conn_str)
    tgt_conn_str = db_utils.get_db_connection(db_cfg_path, cfg['tgt_db'])
    tgt_engine = create_engine(tgt_conn_str)

    apps_tbl = db_utils.get_table_definition_with_engine(cfg['ma_src_tbl'], src_engine)
    shared_groups_tbl = db_utils.get_table_definition_with_engine(cfg['ma_ref_group_tbl'], src_engine)

    if cfg['initial']:
        db_utils.drop_create_table_by_def(mapapps_report_table_def(cfg['ma_tgt_tbl']), tgt_engine, True)
        db_utils.drop_create_table_by_def(mapapps_search_table_def(cfg['ma_tgt_search_tbl']), tgt_engine, True)
        db_utils.drop_create_table_by_def(mapapps_basemap_table_def(cfg['ma_tgt_basemap_tbl']), tgt_engine, True)
        db_utils.drop_create_table_by_def(mapapps_service_table_def(cfg['ma_tgt_service_tbl']), tgt_engine, True)

    if not db_utils.table_exists(tgt_engine, cfg['ma_tgt_tbl']):
        db_utils.drop_create_table_by_def(mapapps_report_table_def(cfg['ma_tgt_tbl']), tgt_engine)
    if not db_utils.table_exists(tgt_engine, cfg['ma_tgt_search_tbl']):
        db_utils.drop_create_table_by_def(mapapps_search_table_def(cfg['ma_tgt_search_tbl']), tgt_engine)
    if not db_utils.table_exists(tgt_engine, cfg['ma_tgt_basemap_tbl']):
        db_utils.drop_create_table_by_def(mapapps_basemap_table_def(cfg['ma_tgt_basemap_tbl']), tgt_engine)
    if not db_utils.table_exists(tgt_engine, cfg['ma_tgt_service_tbl']):
        db_utils.drop_create_table_by_def(mapapps_service_table_def(cfg['ma_tgt_service_tbl']), tgt_engine)

    logging.info("Analyzing target tables")
    tgt_tbl = db_utils.get_table_definition_with_engine(cfg['ma_tgt_tbl'], tgt_engine)
    tgt_search_tbl = db_utils.get_table_definition_with_engine(cfg['ma_tgt_search_tbl'], tgt_engine)
    tgt_basemap_tbl = db_utils.get_table_definition_with_engine(cfg['ma_tgt_basemap_tbl'], tgt_engine)
    tgt_map_tbl = db_utils.get_table_definition_with_engine(cfg['ma_tgt_service_tbl'], tgt_engine)

    logging.info("Setting up target insert statements")
    tgt_insert_stmt = tgt_tbl.insert().values(dict())
    tgt_search_insert_stmt = tgt_search_tbl.insert().values(dict())
    tgt_basemap_insert_stmt = tgt_basemap_tbl.insert().values(dict())
    tgt_map_insert_stmt = tgt_map_tbl.insert().values(dict())

    logging.info("Connecting to database")
    with src_engine.connect() as connection:
        if cfg['limit']:
            logging.warn("Limiting results to %d rows" % cfg['limit'])
            rows = connection.execute(apps_tbl.select().limit(cfg['limit']))
        else:
            rows = connection.execute(apps_tbl.select())

        # preparing containers for table-specific inserts
        inserts = list()
        search_inserts = list()
        service_inserts = list()
        base_map_inserts = list()

        for row in rows:
            logging.info("Retrieving app information for '%s'" % row.id)

            # retrieving basic map information from current database row
            single_app_info = dict()
            single_app_info['app_id'] = row.id
            single_app_info['env'] = cfg['query_environment']
            single_app_info['title'] = row.title
            single_app_info['description'] = row.description
            single_app_info['status'] = row.editstate
            single_app_info['enabled'] = row.enabled
            single_app_info['created_at'] = row.created_at
            single_app_info['created_by'] = row.created_by
            single_app_info['modified_at'] = row.modified_at
            single_app_info['modified_by'] = row.modified_by
            single_app_info['sharedgroups_count'] = row.sharedgroups_count
            single_app_info['sharedgroups'] = get_shared_groups(shared_groups_tbl, row.id, connection)
            single_app_info['url'] = "/".join((base_url, MAP_URL_SUFFIX % row.id))
            single_app_info['reference_date'] = cfg['ref_date']

            # retrieving map configuration
            url = "/".join((single_app_info['url'], MAP_CFG_FILE))
            logging.info("Retrieving map configuration from:\n  %s" % url)
            r = requests.get(url, auth=(cfg['ma_user'], cfg['ma_pwd']), verify=False)
            try:
                app_json = r.json()
            except simplejson.errors.JSONDecodeError:
                logging.warn("+ Unable to retrieve JSON configuration for map '%s'" % row.id)
                continue

            # determining version of the current app by checking for
            # a parameter that is only known to be present in
            # maps of MapApps version 3
            if 'map' in app_json['bundles']:
                single_app_info['version'] = 3
            elif 'map-init' in app_json['bundles']:
                single_app_info['version'] = 4
            else:
                single_app_info['version'] = None

            # retrieving loaded and configured bundles
            single_app_info['loaded_bundles'] = sorted(app_json['load']['allowedBundles'])
            single_app_info['configured_bundles'] = sorted(list(app_json['bundles'].keys()))
            # retrieving utilized domain bundles
            single_app_info['domain_bundles'] = list(filter(
                lambda d: d.startswith('domain-'), single_app_info['loaded_bundles']))
            if single_app_info['domain_bundles']:
                single_app_info['domain_bundles_used'] = True
            else:
                single_app_info['domain_bundles_used'] = False

            # retrieving searches
            searches = retrieve_configured_search_stores(cfg, app_json, single_app_info)
            search_inserts.extend(searches)

            # retrieving basemaps
            basemaps = retrieve_configured_basemaps(cfg, app_json, single_app_info)
            base_map_inserts.extend(basemaps)

            # retrieving maps
            maps = retrieve_configured_maps(cfg, app_json, single_app_info)
            service_inserts.extend(maps)

            # checking whether there are configured bundles that aren't loaded
            check_loaded_configured_bundles(single_app_info)

            inserts.append(single_app_info)
        else:
            with tgt_engine.connect() as connection:

                # inserting collected data into table containing all configured maps
                if inserts:
                    if cfg['dry_run']:
                        logging.info("%d inserts would be made into %s" % (len(inserts), cfg['ma_tgt_tbl']))
                    else:
                        logging.info("Deleting entries previously created today")
                        tgt_delete_stmt = prepare_delete_statement(cfg, tgt_tbl)
                        connection.execute(tgt_delete_stmt)
                        logging.info("Inserting new items")
                        connection.execute(tgt_insert_stmt, inserts)

                # inserting collected data into table containing all searches configured in maps
                if search_inserts:
                    if cfg['dry_run']:
                        logging.info(
                            "%d inserts would be made into %s" % (len(search_inserts), cfg['ma_tgt_search_tbl']))
                    else:
                        mandatory_keys = set()
                        [mandatory_keys.update(insert_item.keys()) for insert_item in search_inserts]
                        # not sure why we're doing this here, should have laid out my thinking
                        # at the first implementation
                        for item in search_inserts:
                            [item.__setitem__(key, None) for key in mandatory_keys if key not in item.keys()]
                        logging.info("Deleting entries previously created today")
                        tgt_delete_stmt = prepare_delete_statement(cfg, tgt_search_tbl)
                        connection.execute(tgt_delete_stmt)
                        logging.info("Inserting new items")
                        connection.execute(tgt_search_insert_stmt, search_inserts)

                # inserting collected data into table containing all basemaps configured in maps
                if base_map_inserts:
                    if cfg['dry_run']:
                        logging.info(
                            "%d inserts would be made into %s" % (len(base_map_inserts), cfg['ma_tgt_basemap_tbl']))
                    else:
                        logging.info("Deleting entries previously created today")
                        tgt_delete_stmt = prepare_delete_statement(cfg, tgt_basemap_tbl)
                        connection.execute(tgt_delete_stmt)
                        logging.info("Inserting new items")
                        connection.execute(tgt_basemap_insert_stmt, base_map_inserts)

                # inserting collected data into table containing all services configured in maps
                if service_inserts:
                    if cfg['dry_run']:
                        logging.info(
                            "%d inserts would be made into %s" % (len(service_inserts), cfg['ma_tgt_service_tbl']))
                    else:
                        logging.info("Deleting entries previously created today")
                        tgt_delete_stmt = prepare_delete_statement(cfg, tgt_map_tbl)
                        connection.execute(tgt_delete_stmt)
                        logging.info("Inserting new items")
                        connection.execute(tgt_map_insert_stmt, service_inserts)


def prepare_delete_statement(cfg, tgt_table, tgt_date=None):
    """
    Prepares SQL statement to delete rows from specified table that had been created on
    provided date (today's date per default).
    """
    if not tgt_date:
        tgt_date = date.today()
    tgt_delete_stmt = tgt_table.delete().where(and_(
        tgt_table.c.reference_date == tgt_date, tgt_table.c.env == cfg['query_environment']))

    return tgt_delete_stmt


def get_shared_groups(shared_group_tbl, app_id, connection):
    """
    Retrieves groups shared by the identified map from the specified table
    using the given database connection.
    """
    shared_groups = list()
    shared_group_select_w_stmt = shared_group_tbl.select().where(shared_group_tbl.c.app_id == app_id)
    shared_groups_rows = connection.execute(shared_group_select_w_stmt)
    for shared_groups_row in shared_groups_rows:
        shared_groups.append(shared_groups_row.group_name)
    return shared_groups


def check_loaded_configured_bundles(single_app_info):
    """
    Checks whether a configured bundle hasn't been loaded previously and issues
    a corresponding warning.
    """
    l_bundles = set([bundle.split('@')[0] for bundle in single_app_info['loaded_bundles']])
    c_bundles = set(single_app_info['configured_bundles'])

    for bundle in sorted(list(c_bundles.difference(l_bundles))):
        if bundle == 'themes':
            continue
        logging.warn("Bundle configured, but not loaded: %s" % bundle)


def retrieve_configured_search_stores(cfg, app_json, single_app_info):
    """
    Retrieves searches defined in specied map configuration.
    """
    searches = list()
    orig_search_stores = dict()

    if 'agssearch' in app_json['bundles']:
        if 'AGSStore' in app_json['bundles']['agssearch']:
            orig_search_stores = app_json['bundles']['agssearch']['AGSStore']

    # bailing out if no searches were found to be defined
    if not orig_search_stores:
        return searches

    for search_store in orig_search_stores:
        single_store_info = dict()
        single_store_info['app_id'] = app_json['properties']['id']
        single_store_info['app_title'] = single_app_info['title']
        single_store_info['reference_date'] = cfg['ref_date']
        single_store_info['env'] = cfg['query_environment']
        single_store_info['used_in_search'] = False
        single_store_info['used_in_selection'] = False

        # retrieving environment of underlying service by
        # analyzing host name
        single_store_info['svc_env'] = None
        for svc_env in cfg['environments']:
            # skipping environment if no ArcGIS server has been configured for it
            if 'ags_host' not in cfg['environments'][svc_env]:
                continue
            if 'url' in search_store and cfg['environments'][svc_env]['ags_host'] in search_store['url']:
                single_store_info['svc_env'] = svc_env
                break

        for key in search_store:
            if key == 'url' and search_store[key].startswith("http"):
                match = re.search(SERVICE_REGEX, search_store[key])
                if match:
                    single_store_info['svc_directory'] = match.group(1)
                    single_store_info['svc_name'] = match.group(2)
                    single_store_info['svc_layer_id'] = int(match.group(3))
            if key == 'useIn':
                if 'omnisearch' in search_store[key]:
                    single_store_info['used_in_search'] = True
                if 'selection' in search_store[key]:
                    single_store_info['used_in_selection'] = True
                continue
            if key in SEARCH_STORE_MAPPING:
                single_store_info[SEARCH_STORE_MAPPING[key]] = search_store[key]
            else:
                logging.debug("Unmapped search store key '%s' with value: %s" % (key, search_store[key]))
        searches.append(single_store_info)

    return searches


def retrieve_configured_basemaps(cfg, app_json, single_app_info):
    """
    Retrieves basemaps from the specified map configuration.
    """
    base_maps = list()

    # retrieving basemaps configured in a map using map apps version 3
    if single_app_info['version'] == 3:
        if 'MappingResourceRegistryFactory' in app_json['bundles']['map']:
            mapping_resource_registry = app_json['bundles']['map']['MappingResourceRegistryFactory']
        else:
            mapping_resource_registry = dict()

        if (
            '_knownServices' in mapping_resource_registry and
            'services' in mapping_resource_registry['_knownServices']
        ):
            map_services = mapping_resource_registry['_knownServices']['services']
        else:
            map_services = list()

        for svc in map_services:
            svc_type = svc.get('type', '')
            if not svc_type or svc_type in ['AGS_DYNAMIC', 'AGS_FEATURE']:
                continue
            single_base_map = dict()
            single_base_map['app_id'] = single_app_info['app_id']
            single_base_map['app_title'] = single_app_info['title']
            single_base_map['reference_date'] = cfg['ref_date']
            single_base_map['svc_id'] = svc.get('id', None)
            single_base_map['svc_title'] = svc.get('title', None)
            single_base_map['svc_type'] = svc_type
            single_base_map['svc_url'] = svc.get('url', None)
            single_base_map['svc_description'] = None
            single_base_map['env'] = cfg['query_environment']
            base_maps.append(single_base_map)
    # retrieving basemaps configured in a map using map apps version 4
    elif single_app_info['version'] == 4:
        if 'basemaps' in app_json['bundles']['map-init']['Config']:
            config_basemaps = app_json['bundles']['map-init']['Config']['basemaps']
        else:
            config_basemaps = list()

        for svc in config_basemaps:
            single_base_map = dict()
            single_base_map['app_id'] = single_app_info['app_id']
            single_base_map['app_title'] = single_app_info['title']
            single_base_map['reference_date'] = cfg['ref_date']
            single_base_map['svc_id'] = svc.get('id', None)
            single_base_map['svc_title'] = svc.get('title', None)
            single_base_map['svc_description'] = svc.get('description', None)
            single_base_map['env'] = cfg['query_environment']
            if type(svc.get('basemap', '')) is str:
                if svc.get('basemap', None):
                    single_base_map['svc_type'] = 'INBUILT'
                    single_base_map['svc_url'] = None
            else:
                sub_dict = svc.get('basemap', dict())
                single_base_map['svc_type'] = sub_dict.get('type', None)
                single_base_map['svc_url'] = sub_dict.get('url', None)
            base_maps.append(single_base_map)
    else:
        logging.warn("Unable to retrieve basemaps for non-versioned map configuration: %s" % single_app_info['app_id'])

    return base_maps


def retrieve_configured_maps(cfg, app_json, single_app_info):
    """
    Retrieves maps from the specified map configuration.
    """
    maps = list()

    config_maps = list()

    # retrieving maps configured in a map using map apps version 4
    if single_app_info['version'] == 4:
        if 'map' in app_json['bundles']['map-init']['Config']:
            map_cfg = app_json['bundles']['map-init']['Config']['map']
            if 'layers' in map_cfg:
                config_maps = map_cfg['layers']

        for svc in config_maps:
            single_map = dict()
            single_map['app_id'] = single_app_info['app_id']
            single_map['app_title'] = single_app_info['title']
            single_map['reference_date'] = cfg['ref_date']
            single_map['svc_id'] = svc.get('id', None)
            single_map['svc_title'] = svc.get('title', None)
            single_map['svc_type'] = svc.get('type', None)
            single_map['svc_url'] = svc.get('url', None)
            single_map['env'] = cfg['query_environment']

            match = re.search(SERVICE_REGEX, svc.get('url', ''))
            if match:
                single_map['svc_name'] = match.group(2)
            else:
                single_map['svc_name'] = None

            check_service_status(cfg, single_map)

            maps.append(single_map)
    # retrieving maps configured in a map using map apps version 3
    elif single_app_info['version'] == 3:
        if 'MappingResourceRegistryFactory' in app_json['bundles']['map']:
            mapping_resource_registry = app_json['bundles']['map']['MappingResourceRegistryFactory']
        else:
            mapping_resource_registry = dict()

        if (
            '_knownServices' in mapping_resource_registry and
            'services' in mapping_resource_registry['_knownServices']
        ):
            map_services = mapping_resource_registry['_knownServices']['services']
        else:
            map_services = list()

        for svc in map_services:
            svc_type = svc.get('type', '')
            if not svc_type or svc_type not in ['AGS_DYNAMIC', 'AGS_FEATURE']:
                continue
            single_map = dict()
            single_map['app_id'] = single_app_info['app_id']
            single_map['app_title'] = single_app_info['title']
            single_map['reference_date'] = cfg['ref_date']
            single_map['svc_id'] = svc.get('id', None)
            single_map['svc_title'] = svc.get('title', None)
            single_map['svc_type'] = svc_type
            single_map['svc_url'] = svc.get('url', None)
            single_map['svc_description'] = None
            single_map['env'] = cfg['query_environment']

            match = re.search(SERVICE_REGEX, svc.get('url', ''))
            if match:
                single_map['svc_name'] = match.group(2)
            else:
                single_map['svc_name'] = None

            check_service_status(cfg, single_map)

            maps.append(single_map)
    else:
        logging.warn("Unable to retrieve basemaps for non-versioned map configuration: %s" % single_app_info['app_id'])

    return maps


def check_availability(cfg, url):
    """
    Checks whether specified service url is available.
    """
    url = url.split(": ")[-1]
    suffix = '?f=pjson'

    try:
        r = requests.get(url + suffix, auth=(cfg['ma_user'], cfg['ma_pwd']), verify=False)
        payload = r.json()

        if 'error' in payload.keys():
            return False
        else:
            return True
    except Exception as e:
        logging.warn("Unable to check availability of %s" % url)
        logging.warn(e)


def check_service_status(cfg, single_map):
    """
    Checks service status, i.e. availability and security status, of specified map service
    """
    single_map['valid'] = None
    single_map['secured'] = None
    single_map['svc_env'] = None

    # retrieving all existing ags hosts first
    available_ags_hosts = set()
    for svc_env in cfg['environments']:
        # skipping environment if no ArcGIS server has been configured for it
        if 'ags_host' not in cfg['environments'][svc_env]:
            continue
        available_ags_hosts.add(cfg['environments'][svc_env]['ags_host'])
        # identifying service environment for current map service
        if single_map['svc_url'] and cfg['environments'][svc_env]['ags_host'] in single_map['svc_url']:
            single_map['svc_env'] = svc_env

    if single_map['svc_url']:
        if any([sub in single_map['svc_url'] for sub in available_ags_hosts]):
            single_map['valid'] = check_availability(cfg, single_map['svc_url'])
            if 'ags-relay' in single_map['svc_url']:
                single_map['secured'] = True
            else:
                single_map['secured'] = False
