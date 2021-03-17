#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging

from sqlalchemy import create_engine

import utils.general_utils as utils
import utils.db_utils as db_utils

from confluence.confluence_publisher import ConfluencePublisher

ENV = utils.get_environment(os.path.join(os.path.dirname(__file__), 'reports'))

TPL_DIR = os.path.join('confluence', 'templates')


def publish_report(args):
    """
    Publishes report.
    """
    cfg = utils.complete_configuration(ENV, args)

    for key in cfg:
        print("%s: %s" % (key, cfg[key]))

    cfl_cfg = cfg['cfl_cfg'][cfg['report_type']]

    engine = create_engine(db_utils.get_db_connection(cfg['db_cfg'], cfg['tgt_db']))
    publisher = ConfluencePublisher(cfg)

    raw_content = prepare_report(cfl_cfg, engine)

    logging.info("%d rows retrieved to be published" % len(raw_content))

    # rendering content
    content = publisher.render(template=os.path.join(TPL_DIR, cfl_cfg['report_tpl']), data=raw_content)

    if 'dry_run' in cfg and cfg['dry_run']:
        logging.info("The following content would be published: %s..." % content[:5000])
    else:
        publisher.create_or_update_page(parent_id=cfl_cfg['page_id'], title=cfl_cfg['title'], content=content)


def prepare_report(cfl_cfg, engine):
    """
    Prepares ArcGIS service report by retrieving corresponding rows from
    database.
    """
    sort_cols = [sc.strip() for sc in cfl_cfg['sort_cols'].split(',')]

    src_tbl = db_utils.get_table_definition_with_engine(cfl_cfg['src_tbl'], engine)
    sort_cols = [getattr(src_tbl.c, sc, src_tbl.c.objectid) for sc in sort_cols]
    # retrieving most recent entry date in service report table
    most_recent_entry_date = db_utils.get_most_recent_date(src_tbl, 'reference_date', engine)
    # preparing statement to select most recent entries from service report table
    select_stmt = src_tbl.select().where(src_tbl.c.reference_date == most_recent_entry_date).order_by(*sort_cols)
    # executing select statement
    rows = None
    with engine.connect() as connection:
        rows = connection.execute(select_stmt).fetchall()

    return rows
