#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import yaml
import string
import random
import logging

from datetime import datetime, timedelta


def get_environment(py_src):
    """
    Gets processing environment for specified script from accompanying
    configuration file.
    """
    env_src = ".".join((os.path.splitext(py_src)[0], 'env', 'yml'))
    print(env_src)
    return read_configuration_file(env_src)


def read_configuration_file(yaml_src):
    """
    Reads specified YAML configuration file and (if available) returns a
    dictionary.
    """
    if not yaml_src:
        return
    elif not os.path.isfile(yaml_src):
        return
    else:
        return yaml.safe_load(open(yaml_src, 'r'))


def complete_configuration(env, args):
    """
    Combines environment configuration and arguments specified on command line
    to prepare a complete process configuration.
    """
    cfg = dict()

    # combining previously defined environment and arguments from command line
    # to prepare process configuration
    for key in env:
        if key.lower() in args and args[key.lower()]:
            cfg[key.lower()] = args[key.lower()]
        else:
            cfg[key.lower()] = env[key]
    for key in args:
        if key not in cfg:
            cfg[key] = args[key]

    return cfg



def prepare_logging(code_file, suffix=None, screen_only=False):
    """
    Prepares logging for the spefified Python code file.
    """
    # retrieving current timestamp
    now = "%04d%02d%02d_%02d%02d%02d" % (
        datetime.now().year, datetime.now().month, datetime.now().day,
        datetime.now().hour, datetime.now().minute, datetime.now().second)

    # retrieving target directory foor log files (also works with UNC paths)
    logdir = os.path.join(os.path.dirname(code_file), 'log')

    if not suffix:
        logfile = "%s_%s.log" % (now, os.path.splitext(os.path.basename(code_file))[0])
    else:
        suffix = ''.join(c for c in str(suffix) if c.isalnum())
        logfile = "%s_%s_%s.log" % (now, os.path.splitext(os.path.basename(code_file))[0], suffix)

    # sending log output to dev/null if only screen output was configured
    if screen_only:
        logpath = os.devnull
    else:
        logpath = os.path.join(logdir, logfile)

    # preparing logging configuration for file output
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        filename=logpath,
        filemode='w')

    # adding console output
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('+ %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


def format_interval(seconds):
    """
    Formats the specified time interval in a human readable format.
    """
    d = datetime(1, 1, 1) + timedelta(seconds=seconds)

    human_readable = list()

    if d.day - 1:
        human_readable.append(
            "{0} day{1}".format(d.day - 1, "s" if d.day - 1 != 1 else ""))
    if d.hour:
        human_readable.append(
            "{0} hour{1}".format(d.hour, "s" if d.hour != 1 else ""))
    if d.minute:
        human_readable.append(
            "{0} minute{1}".format(d.minute, "s" if d.minute != 1 else ""))
    if d.second:
        human_readable.append(
            "{0} second{1}".format(d.second, "s" if d.second != 1 else ""))

    if not human_readable:
        human_readable.append("less than 1 second")

    return " ".join(human_readable)


def get_random_string(length=6, lower=False):
    """
    Get random string with the specified length optionally consisting of lower
    case letters only.
    """
    if lower:
        source_repo = string.ascii_lowercase
    else:
        source_repo = string.ascii_uppercase

    return ''.join(random.choices(source_repo + string.digits, k=length))
