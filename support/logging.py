import time

levels = 8

_context = []  # A stack of timestamps when each nested context is entered

INDENT1 = ' │  '
INDENT2 = ' ├─ '
INDENT3 = ' └─ '

def enter(label):
    level = len(_context)
    time_begin = time.time()
    _context.append((label, time_begin))
    if level < levels:
        if level > 1: print((level - 1) * INDENT1, end='')
        if level > 0: print(INDENT2, end='')
        print(label)
    elif level == levels:
        if level > 1: print((level - 1) * INDENT1, end='')
        if level > 0: print(INDENT2, end='')
        print(label, flush=True, end='')

def leave():
    time_end = time.time()
    label, time_begin = _context.pop()
    time_spent = time_end - time_begin
    level = len(_context)
    if level < levels:
        print(level * INDENT1, end='')
        print(INDENT3, end='')
        print('[{0:.3f} sec]'.format(time_spent))
    elif level == levels:
        print(' [{0:.3f} sec]'.format(time_spent))

def message(label):
    level = len(_context)
    if level <= levels:
        if level > 1: print((level - 1) * INDENT1, end='')
        if level > 0: print(INDENT2, end='')
        print(label)
