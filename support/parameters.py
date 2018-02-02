from . import logging as LOG

import pathlib
import re

keys = []  # Remember whichs keys are read, so we can clear them later

def read(dir):
    LOG.enter('reading parameters')
    # Clear the key-value pair from a previous read()
    for key in keys:
        if key in globals():  # Hack: why is this necessary?
            del globals()[key]
    # Read new keys from param.txt in the specified directory
    regex = re.compile('\s*([^\d\W]\w*)\s*=\s*(.*)')  # key = value
    filename = str(pathlib.Path(dir) / 'param.txt')
    LOG.message('from {}'.format(filename))
    with open(filename) as source:
        for line in source.read().splitlines():
            match = regex.fullmatch(line)
            if match:
                key, value = match.group(1, 2)
                value = eval(value, None, globals())
                globals()[key] = value
                keys.append(key)
                LOG.message('{} = {}'.format(key, value))
    LOG.leave()
