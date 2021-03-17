#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
import logging

from sqlalchemy import MetaData, Table
from sqlalchemy import select, func


def get_db_connection(cfg_src, section):
    """
    Gets database connection parameters (usable for sqlalchemy) from specified
    section in a configuration file.
    """
    cfg_base = yaml.safe_load(open(cfg_src))
    cfg = cfg_base[section]

    user = cfg['user']
    password = cfg['password']
    host = cfg['host']
    if 'database' in cfg:
        database = cfg['database']
    else:
        database = ''

    if 'port' in cfg:
        port = str(cfg['port'])
    else:
        port = ''

    api_dialect = cfg['api_dialect']

    if password:
        conn_string = "%s://%s:%s@%s" % (api_dialect, user, password, host)
    else:
        conn_string = "%s://%s@%s" % (api_dialect, user, host)

    if port:
        conn_string = ":".join((conn_string, port))
    if database:
        conn_string = "/".join((conn_string, database))

    return conn_string


def get_table_definition_with_engine(table_name, engine, schema=None, custom_cols=None):
    """
    Retrieves table definition for given table name using specified database
    engine. Additionally allows for definition of customized columns to
    override reflected specifications.
    """
    meta = MetaData()

    # trying to retrieve optionally specified schema
    if schema is None:
        try:
            schema, table_name = table_name.split(".")
        except ValueError:
            schema = ''

    if custom_cols is None:
        return Table(table_name, meta, schema=schema, autoload_with=engine, autoload=True)
    else:
        return Table(table_name, meta, *custom_cols, schema=schema, autoload_with=engine, autoload=True)


def table_exists(engine, table_name, schema=None):
    """
    Checks whether specified table (optionally including schema) exists in
    database represented by provided engine.
    """
    if schema is None:
        try:
            schema, table_name = table_name.split(".")
        except ValueError:
            schema = ''
    with engine.connect() as connection:
        return engine.dialect.has_table(connection, table_name, schema=schema)


def drop_create_table_by_def(table_def, engine, drop=False, schema=None):
    """
    Drops and creates a table specified by the given definition and using the
    corresponding database engine.
    """
    table_name = table_def.name
    schema = table_def.schema

    if engine.dialect.has_table(engine.connect(), table_name, schema):
        logging.info("Table '%s' already exists" % table_name)
        if drop:
            logging.info("Dropping existing table '%s'" % table_name)
            try:
                table_def.drop(engine)
            except Exception as e:
                logging.error(e)
                return
        else:
            logging.info("Retaining existing table '%s'" % table_name)
            return

    logging.info("Creating table '%s'" % table_name)
    table_def.create(engine)


def get_most_recent_date(tbl, date_col, engine):
    """
    Gets most recent date stored in given column by querying via provided
    engine.
    """
    logging.info("Retrieving most recent date in table '%s' from column '%s'" % (tbl.name, date_col))
    date_col = getattr(tbl.c, date_col, None)
    if date_col is None:
        return
    max_date_select = select([func.max(date_col).label('max_date')])

    logging.info("Connecting to database to find most recent date")
    with engine.connect() as connection:
        rows = connection.execute(max_date_select)
        for row in rows:
            max_date = row.max_date
            logging.info("Most recent date found: %s" % max_date)

    return max_date
