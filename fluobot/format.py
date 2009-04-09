

def format(message, bold = False, underline = False, fg = False, bg = False, color = False):
    if isinstance(message, (list, tuple)):
        return [format(m, bold, underline, fg, bg) for m in message]
    color = str(fg) if fg is not False else ''
    if bg is not False: color += ',%s' % bg
    if bold:
        message = '$B%s$B' % message
    if underline:
        message = '$U%s$U' % message
    if color != '':
        message = '$C%s$X%s$C' % (color, message)
    message = message.replace('$B', '\002')
    message = message.replace('$C', '\003')
    message = message.replace('$U', '\037')
    message = message.replace('$X', '\002\002')
    return message

def bold(message):
    return format(message, bold = True)

def underline(message):
    return format(message, underline = True)

def strip(message):
    message = message.split('\n')
    return '\n'.join(map(str.strip, message))

def blockify(message):
    if not message:
        return ""
    rval = []
    rval.append('')
    for line in strip(message).split('\n'):
        if not line:
            if rval and rval[-1]:
                rval.append('')
        else:
            if rval[-1]:
                rval[-1] += ' ' + line
            else:
                rval[-1] = line
    return '\n'.join(rval).strip()

def prepjoin(l, prep = 'and', sep = ', '):
    if not l:
        return ""
    elif len(l) == 1:
        return l[0]
    else:
        return "%s %s %s" % (sep.join(l[:-1]), prep, l[-1])

def filter_command(s, prefixes):
    prefixes = prefixes.split(' ')
    for prefix in prefixes:
        if s.startswith(prefix):
            return s[len(prefix):]
    return None

def parse(message):
    message = message.split()
    def convert(s):
        for fn in (int, float):
            try:
                return fn(s)
            except:
                pass
        return s
    return map(convert, message)

