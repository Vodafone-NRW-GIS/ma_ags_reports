#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import yaml
import logging

from jinja2 import Template
from atlassian import Confluence


class ConfluencePublisher:

    config = dict()

    def __init__(self, config):
        if type(config) is dict:
            self.config = config
        elif os.path.isfile(config):
            self.config = yaml.safe_load(open(config))
        self.basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.confluence = Confluence(
            url=self.config['cfl_base_url'], username=self.config['cfl_user'], password=self.config['cfl_pwd'])
        # self.redirect_rest_logging_to_logfile()

    def redirect_rest_logging_to_logfile(self):
        logger = logging.getLogger("atlassian.rest_client")
        ch = logging.FileHandler(os.path.join(self.basepath, 'log/rest_client.log'))
        logger.addHandler(ch)

    def set_page_label(self, page_id, label):
        self.confluence.set_page_label(page_id, label)

    def create_or_update_page(self, parent_id: int, title: str, content: str,  minor_edit: bool=True):
        space = self.confluence.get_page_space(parent_id)
        if self.confluence.page_exists(space, title):
            page_id = self.confluence.get_page_id(space, title)
            response = self.confluence.update_page(
                parent_id=parent_id, page_id=page_id, title=title, body=content, minor_edit=minor_edit)
        else:
            response = self.confluence.create_page(space=space, parent_id=parent_id, title=title, body=content)

        if ('statusCode' in response) and (response['statusCode'] == 400):
            print(
                "This did not work, response code = 400, which usually " +
                "means that the content is not parseable by Confluence")
        elif ('id' in response) and (response['status'] == "current"):
            print("Response looks good, check: %s%s" % (self.config['cfl_base_url'], response['_links']['webui']))
        else:
            print("unhandled status, pls review response")
            print(response)
        return response

    def render(self, template: str, data: dict) -> str:
        with open(template, encoding='utf-8') as file_:
            template = Template(file_.read())
        return template.render(data=data)

    def get_page_by_id(self, page_id: int, expand='body.storage'):
        return self.confluence.get_page_by_id(page_id, expand)
