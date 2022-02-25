# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

"""Linter pluging for flake8"""
import logging
import os.path
import re
import sys
from pathlib import PurePath
from subprocess import PIPE, Popen

from pylsp import hookimpl, lsp

log = logging.getLogger(__name__)
FIX_IGNORES_RE = re.compile(r'([^a-zA-Z0-9_,]*;.*(\W+||$))')


@hookimpl
def pylsp_settings():
    # Default flake8 to disabled
    return {'plugins': {'flake8': {'enabled': False}}}


@hookimpl
def pylsp_lint(workspace, document):
    config = workspace._config
    settings = config.plugin_settings('flake8', document_path=document.path)
    log.debug("Got flake8 settings: %s", settings)

    ignores = settings.get("ignore", [])
    per_file_ignores = settings.get("perFileIgnores")

    if per_file_ignores:
        for path in per_file_ignores:
            file_pat, errors = path.split(":")
            if PurePath(document.path).match(file_pat):
                ignores.extend(errors.split(","))

    opts = {
        'config': settings.get('config'),
        'exclude': settings.get('exclude'),
        'filename': settings.get('filename'),
        'hang-closing': settings.get('hangClosing'),
        'ignore': ignores or None,
        'max-line-length': settings.get('maxLineLength'),
        'indent-size': settings.get('indentSize'),
        'select': settings.get('select'),
    }

    # flake takes only absolute path to the config. So we should check and
    # convert if necessary
    if opts.get('config') and not os.path.isabs(opts.get('config')):
        opts['config'] = os.path.abspath(os.path.expanduser(os.path.expandvars(
            opts.get('config')
        )))
        log.debug("using flake8 with config: %s", opts['config'])

    # Call the flake8 utility then parse diagnostics from stdout
    flake8_executable = settings.get('executable', 'flake8')

    args = build_args(opts)
    output = run_flake8(flake8_executable, args, document)
    return parse_stdout(document, output)


def run_flake8(flake8_executable, args, document):
    """Run flake8 with the provided arguments, logs errors
    from stderr if any.
    """
    # a quick temporary fix to deal with Atom
    args = [(i if not i.startswith('--ignore=') else FIX_IGNORES_RE.sub('', i))
            for i in args if i is not None]

    # if executable looks like a path resolve it
    if not os.path.isfile(flake8_executable) and os.sep in flake8_executable:
        flake8_executable = os.path.abspath(
            os.path.expanduser(os.path.expandvars(flake8_executable))
        )

    log.debug("Calling %s with args: '%s'", flake8_executable, args)
    try:
        cmd = [flake8_executable]
        cmd.extend(args)
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)  # pylint: disable=consider-using-with
    except IOError:
        log.debug("Can't execute %s. Trying with '%s -m flake8'", flake8_executable, sys.executable)
        cmd = [sys.executable, '-m', 'flake8']
        cmd.extend(args)
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)  # pylint: disable=consider-using-with
    (stdout, stderr) = p.communicate(document.source.encode())
    if stderr:
        log.error("Error while running flake8 '%s'", stderr.decode())
    return stdout.decode()


def build_args(options):
    """Build arguments for calling flake8.

    Args:
        options: dictionary of argument names and their values.
    """
    args = ['-']  # use stdin
    for arg_name, arg_val in options.items():
        if arg_val is None:
            continue
        arg = None
        if isinstance(arg_val, list):
            arg = '--{}={}'.format(arg_name, ','.join(arg_val))
        elif isinstance(arg_val, bool):
            if arg_val:
                arg = '--{}'.format(arg_name)
        else:
            arg = '--{}={}'.format(arg_name, arg_val)
        args.append(arg)
    return args


def parse_stdout(document, stdout):
    """
    Build a diagnostics from flake8's output, it should extract every result and format
    it into a dict that looks like this:
        {
            'source': 'flake8',
            'code': code, # 'E501'
            'range': {
                'start': {
                    'line': start_line,
                    'character': start_column,
                },
                'end': {
                    'line': end_line,
                    'character': end_column,
                },
            },
            'message': msg,
            'severity': lsp.DiagnosticSeverity.*,
        }

    Args:
        document: The document to be linted.
        stdout: output from flake8
    Returns:
        A list of dictionaries.
    """

    diagnostics = []
    lines = stdout.splitlines()
    for raw_line in lines:
        parsed_line = re.match(r'(.*):(\d*):(\d*): (\w*) (.*)', raw_line)
        if not parsed_line:
            log.debug("Flake8 output parser can't parse line '%s'", raw_line)
            continue

        parsed_line = parsed_line.groups()
        if len(parsed_line) != 5:
            log.debug("Flake8 output parser can't parse line '%s'", raw_line)
            continue

        _, line, character, code, msg = parsed_line
        line = int(line) - 1
        character = int(character) - 1
        # show also the code in message
        msg = code + ' ' + msg
        diagnostics.append(
            {
                'source': 'flake8',
                'code': code,
                'range': {
                    'start': {
                        'line': line,
                        'character': character
                    },
                    'end': {
                        'line': line,
                        # no way to determine the column
                        'character': len(document.lines[line])
                    }
                },
                'message': msg,
                'severity': lsp.DiagnosticSeverity.Warning,
            }
        )

    return diagnostics
