#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Script to list data sources (feature classes paths) that are served by a map
service as well as map document that was used for publishing a service.

The script will report this information for all map services on the ArcGIS Server.
It is required to have an Administrator level user account to be able to log
in into the ArcGIS Server Administrator Directory.
'''
import os
import time
import logging
import urllib3
import datetime

import requests
from lxml import etree

from arcrest import AGSTokenSecurityHandler
from arcrest.manageags import AGSAdministration
from sqlalchemy import create_engine, and_

from table_defs.ags_service_layer_report import ags_service_layer_report_table_def

import utils.general_utils as utils
import utils.db_utils as db_utils

ENV = utils.get_environment(os.path.join(os.path.dirname(__file__), 'reports'))

# constants to be used throughout the process
STD_PORT = 443
TOKEN_URL = "https://%s/portal/sharing/rest/generateToken"


def query_ags_service_layers(args):
    """
    Collects information about published ArcGIS service layers by querying the
    server via JSON API.
    """
    # combining environment configuration and command line arguments
    cfg = utils.complete_configuration(ENV, args)

    t0 = time.time()

    logging.info("Extracting information about ArcGIS server layers to %s" % cfg['tgt_db'])

    # turning off notifications about insecure connections
    urllib3.disable_warnings()
    # retrieving current date
    date = datetime.date.today()

    # locating database configuration
    db_cfg_path = cfg['db_cfg']
    query_env = cfg['environments'][cfg['query_environment']]

    if 'ags_host' not in query_env:
        logging.warn(
            "No ArcGIS server hostname specified for current query environment '%s'" % cfg['query_environment'])
        return

    logging.info("Setting up connection to %s" % cfg['tgt_db'])
    tgt_conn_str = db_utils.get_db_connection(db_cfg_path, cfg['tgt_db'])
    tgt_engine = create_engine(tgt_conn_str)

    if cfg['initial']:
        db_utils.drop_create_table_by_def(ags_service_layer_report_table_def(cfg['ags_tgt_table']), tgt_engine, True)

    if not db_utils.table_exists(tgt_engine, cfg['ags_tgt_table']):
        db_utils.drop_create_table_by_def(ags_service_layer_report_table_def(cfg['ags_tgt_table']), tgt_engine)

    logging.info("Analyzing target table %s" % cfg['ags_tgt_table'])
    tgt_table = db_utils.get_table_definition_with_engine(cfg['ags_tgt_table'], tgt_engine)

    logging.info("Preparing target insert statement")
    tgt_insert_stmt = tgt_table.insert().values(dict())
    logging.info("Preparing deletion statement for entries previously created today")
    tgt_delete_stmt = tgt_table.delete().where(and_(
        tgt_table.c.reference_date == date, tgt_table.c.env == cfg['query_environment']))

    # setting up list for insert statements
    inserts = list()

    logging.info("Working on '%s' environment at '%s'" % (cfg['query_environment'], query_env['ags_host']))
    # retrieving server token
    token_url = TOKEN_URL % query_env['ags_host']
    token = get_token(
        query_env['ags_host'], query_env.get('port', STD_PORT), cfg['ags_user'], cfg['ags_pwd'], token_url)
    # retrieving current services
    services = get_services(
        cfg, query_env['ags_host'], query_env.get('port', STD_PORT), cfg['ags_user'], cfg['ags_pwd'], token_url)

    svc_cnt = 0
    # for each service collecting information about datasets and resources
    for service in services[:]:
        logging.info("Working on '%s'" % service['serviceName'])
        svc_cnt += 1
        # retrieving service manifest
        xml_string = get_service_manifest(token, service['URL'])
        # retrieving datasets and MXD resource
        datasets = get_datasets(xml_string)
        mxd_resource = get_resource(xml_string)
        # collecting information for each dataset
        if not datasets:
            logging.warning("No datasets found in '%s'" % service['serviceName'])
        for dataset in datasets:
            tokens = dataset.split('\\')
            sde_conn = tokens[-2]
            table_data = tokens[-1]
            table_tokens = table_data.split('.')
            if len(table_tokens) == 3:
                db, schema, table = table_tokens
            elif len(table_tokens) == 2:
                db = 'oracle'
                schema, table = table_tokens
            else:
                db = 'unknown',
                schema = 'unknown'
                table = table_tokens.pop(0)

            single_insert = dict()
            single_insert['svc_name'] = service['serviceName']
            single_insert['svc_folder'] = service['folderName']
            single_insert['env'] = cfg['query_environment']
            single_insert['reference_date'] = date
            single_insert['db'] = db
            single_insert['db_schema'] = schema.lower()
            single_insert['db_table'] = table.lower()
            single_insert['sde'] = sde_conn
            single_insert['mxd'] = mxd_resource
            inserts.append(single_insert)

        if 'limit' in cfg and cfg['limit']:
            if svc_cnt >= cfg['limit']:
                break

    logging.info("Information for %d service layer items collected" % len(inserts))

    if inserts:
        if cfg['dry_run']:
            logging.info("%d inserts would be made" % len(inserts))
        else:
            with tgt_engine.connect() as connection:
                logging.info("Deleting entries previously created today")
                connection.execute(tgt_delete_stmt)
                logging.info("Inserting new items")
                connection.execute(tgt_insert_stmt, inserts)

    t1 = time.time()
    logging.info("Information collection finished in %s" % (utils.format_interval(t1 - t0)))


def get_service_manifest(token, service_url):
    """
    Returns service manifest, based on this url
    http://localhost:6080/arcgis/admin/services/servicename.MapServer/iteminfo/manifest/manifest.xml
    a shorter version of it can be obtained from a JSON manifest,
    available via REST API:
    http://resources.arcgis.com/en/help/arcgis-rest-api/index.html#//02r3000001vt000000
    """
    metadata_url = '{0}/iteminfo/manifest/manifest.xml'.format(service_url)
    xml_data = requests.get(metadata_url, params={'token': token}, verify=False).content
    return xml_data


def get_datasets(data):
    """
    Returns a list of paths to datasets such as feature classes used by the
    current service.
    """
    doc = etree.fromstring(data)
    service_items = doc.xpath("//Datasets/SVCDataset/OnPremisePath/text()")
    return service_items


def get_resource(data):
    """
    Returns a map document path that was used during the publishing.
    """
    doc = etree.fromstring(data)
    mxd_resource = doc.xpath("//Resources/SVCResource/OnPremisePath/text()")
    try:
        return mxd_resource.pop(0)
    except IndexError:
        return


def get_services(cfg, server, port, user, pwd, token_url):
    """
    Returns a list of dictionaries with service name, folder, type and URL;
    the list is sorted by service name.
    """
    ags_admin_url = r'https://{0}/server/admin'.format(server)
    ags_security_handler = AGSTokenSecurityHandler(
        username=user, password=pwd, org_url=ags_admin_url, token_url=token_url)
    ags_security_handler.referer_url = ags_admin_url
    ags_obj = AGSAdministration(ags_admin_url, ags_security_handler)
    services = ags_obj.services.find_services(service_type='MAPSERVER')
    services = [
        s for s in services if s['serviceName'] not in cfg['services_to_skip']]
    return sorted(services, key=lambda s: s['serviceName'])


def get_token(server, port, user, pwd, token_url):
    """
    Returns token issued from AGS as string.
    """
    ags_admin_url = "https://{0}/server/admin".format(server)
    ags_security_handler = AGSTokenSecurityHandler(
        username=user, password=pwd, org_url=ags_admin_url, token_url=token_url)
    ags_security_handler.referer_url = ags_admin_url
    return ags_security_handler.token
