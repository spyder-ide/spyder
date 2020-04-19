# Copyright 2019 Palantir Technologies, Inc.
"""Linter pluging for flake8"""
import logging
from os import path
import re
from subprocess import Popen, PIPE
from pyls import hookimpl, lsp

log = logging.getLogger(__name__)


@hookimpl
def pyls_settings():
    # Default flake8 to disabled
    return {'plugins': {'flake8': {'enabled': False}}}


@hookimpl
def pyls_lint(config, document):
    settings = config.plugin_settings('flake8')
    log.debug("Got flake8 settings: %s", settings)

    opts = {
        'config': settings.get('config'),
        'exclude': settings.get('exclude'),
        'filename': settings.get('filename'),
        'hang-closing': settings.get('hangClosing'),
        'ignore': settings.get('ignore'),
        'max-line-length': settings.get('maxLineLength'),
        'select': settings.get('select'),
    }

    # flake takes only absolute path to the config. So we should check and
    # convert if necessary
    if opts.get('config') and not path.isabs(opts.get('config')):
        opts['config'] = path.abspath(path.expanduser(path.expandvars(
            opts.get('config')
        )))
        log.debug("using flake8 with config: %s", opts['config'])

    # Call the flake8 utility then parse diagnostics from stdout
    args = build_args(opts, document.path)
    output = run_flake8(args)
    return parse_stdout(document, output)


def run_flake8(args):
    """Run flake8 with the provided arguments, logs errors
    from stderr if any.
    """
    log.debug("Calling flake8 with args: '%s'", args)
    try:
        cmd = ['flake8']
        cmd.extend(args)
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    except IOError:
        log.debug("Can't execute flake8. Trying with 'python -m flake8'")
        cmd = ['python', '-m', 'flake8']
        cmd.extend(args)
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    stderr = p.stderr.read().decode()
    if stderr:
        log.error("Error while running flake8 '%s'", stderr)
    stdout = p.stdout
    return stdout.read().decode()


def build_args(options, doc_path):
    """Build arguments for calling flake8.

    Args:
        options: dictionary of argument names and their values.
        doc_path: path of the document to lint.
    """
    args = [doc_path]
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
        parsed_line = re.match(r'(.*):(\d*):(\d*): (\w*) (.*)', raw_line).groups()
        if not parsed_line or len(parsed_line) != 5:
            log.debug("Flake8 output parser can't parse line '%s'", raw_line)
            continue
        _, line, character, code, msg = parsed_line
        line = int(line) - 1
        character = int(character) - 1
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
