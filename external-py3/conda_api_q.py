# -*- coding: utf-8 -*-
#
# Copyright © 2014 Gonzalo Peña (@goanpeca)
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Conda Process based on conda-api and QProcess"""

from spyderlib.qt.QtGui import QVBoxLayout, QHBoxLayout, QPushButton, QWidget
from spyderlib.qt.QtCore import QObject, QProcess, QByteArray
from spyderlib.py3compat import to_text_string

import re
import os
import sys
import json
from os.path import basename, isdir, join

__version__ = '1.2.1'

# global
ROOT_PREFIX = None

def handle_qbytearray(obj, encoding):
    """ """
    if isinstance(obj, QByteArray):
        obj = obj.data()
    
    return to_text_string(obj, encoding=encoding)

# functions not calling a QProcess, outside of the class
# these could also be implemented as static methods...
def linked(prefix):
    """
    Return the (set of canonical names) of linked packages in `prefix`.
    """
    if not isdir(prefix):
        raise Exception('no such directory: %r' % prefix)
    meta_dir = join(prefix, 'conda-meta')
    if not isdir(meta_dir):
        # we might have nothing in linked (and no conda-meta directory)
        return set()
    return set(fn[:-5] for fn in os.listdir(meta_dir)
               if fn.endswith('.json'))


def split_canonical_name(cname):
    """
    Split a canonical package name into (name, version, build) strings.
    """
    return tuple(cname.rsplit('-', 2))


class CondaError(Exception):
    "General Conda error"
    pass


class CondaEnvExistsError(CondaError):
    "Conda environment already exists"
    pass


class CondaProcess(QObject):
    """conda-api modified to work with QProcess"""
    ENCODING = 'ascii'

    def __init__(self, parent, on_finished=None, on_partial=None):
        QObject.__init__(self, parent)
        self._parent = parent
        self.output = None
        self.partial = None
        self.stdout = None
        self.error = None
        self._parse = False
        self._function_called = ''
        self._name = None
        self._process = QProcess()
        self._on_finished = on_finished

        self._process.finished.connect(self._call_conda_ready)
        self._process.readyReadStandardOutput.connect(self._call_conda_partial)

        if on_finished is not None:
            self._process.finished.connect(on_finished)
        if on_partial is not None:
            self._process.readyReadStandardOutput.connect(on_partial)

        self.set_root_prefix()

    def _call_conda_partial(self):
        """ """
        stdout = self._process.readAllStandardOutput()
        stdout = handle_qbytearray(stdout, CondaProcess.ENCODING)
        
        stderr = self._process.readAllStandardError()
        stderr = handle_qbytearray(stderr, CondaProcess.ENCODING)

        if self._parse:
            self.output = json.loads(stdout)
        else:
            self.output = stdout

        self.partial = self.output
        self.stdout = self.output
        self.error = stderr
        
#        print(self.partial)
#        print(self.error)

    def _call_conda_ready(self):
        """function called when QProcess in _call_conda finishes task"""
        function = self._function_called
        
        if self.stdout is None:
            stdout = to_text_string(self._process.readAllStandardOutput(),
                                    encoding=CondaProcess.ENCODING)
        else:
            stdout = self.stdout

        if self.error is None:
            stderr = to_text_string(self._process.readAllStandardError(),
                                    encoding=CondaProcess.ENCODING)
        else:
            stderr = self.error

        if function == 'get_conda_version':
            pat = re.compile(r'conda:?\s+(\d+\.\d\S+|unknown)')
            m = pat.match(stderr.strip())
            if m is None:
                m = pat.match(stdout.strip())
            if m is None:
                raise Exception('output did not match: %r' % stderr)
            self.output = m.group(1)
        elif function == 'get_envs':
            info = self.output
            self.output = info['envs']
        elif function == 'get_prefix_envname':
            name = self._name
            envs = self.output
            self.output = self._get_prefix_envname_helper(name, envs)
            self._name = None
        elif function == 'config_path':
            result = self.output
            self.output = result['rc_path']
        elif function == 'config_get':
            result = self.output
            self.output = result['get']
        elif (function == 'config_delete' or function == 'config_add' or
                function == 'config_set' or function == 'config_remove'):
            result = self.output
            self.output = result.get('warnings', [])
        elif function == 'pip':
            result = []
            lines = self.output.split('\n')
            for line in lines:
                if '<pip>' in line:
                    temp = line.split()[:-1] + ['pip']
                    result.append('-'.join(temp))
            self.output = result

        if stderr.strip():
            self.error = stderr
#            raise Exception('conda %r:\nSTDERR:\n%s\nEND' % (extra_args,
#                                                             stderr.decode()))
        self._parse = False

    def _get_prefix_envname_helper(self, name, envs):
        """ """
        global ROOTPREFIX
        if name == 'root':
            return ROOT_PREFIX
        for prefix in envs:
            if basename(prefix) == name:
                return prefix
        return None

    def _call_conda(self, extra_args, abspath=True):
        """ """
        # call conda with the list of extra arguments, and return the tuple
        # stdout, stderr
        global ROOT_PREFIX
        if abspath:
            if sys.platform == 'win32':
                python = join(ROOT_PREFIX, 'python.exe')
                conda = join(ROOT_PREFIX,
                             'Scripts', 'conda-script.py')
            else:
                python = join(ROOT_PREFIX, 'bin/python')
                conda = join(ROOT_PREFIX, 'bin/conda')
            cmd_list = [python, conda]
        else:  # just use whatever conda is on the path
            cmd_list = ['conda']

        cmd_list.extend(extra_args)

#        try:
#            p = Popen(cmd_list, stdout=PIPE, stderr=PIPE)
#        except OSError:
#            raise Exception("could not invoke %r\n" % args)
#        return p.communicate()

        # adapted code
        # ------------
        self.error, self.output = None, None
        self._process.start(cmd_list[0], cmd_list[1:])

    def _call_and_parse(self, extra_args, abspath=True):
        """ """
#        stdout, stderr = _call_conda(extra_args, abspath=abspath)
#        if stderr.decode().strip():
#            raise Exception('conda %r:\nSTDERR:\n%s\nEND' % (extra_args,
#                                                             stderr.decode()))
#    return json.loads(stdout.decode())

        # adapted code
        # ------------
        self._parse = True
        self._call_conda(extra_args, abspath=abspath)

    def _setup_install_commands_from_kwargs(self, kwargs, keys=tuple()):
        """ """
        cmd_list = []
        if kwargs.get('override_channels', False) and 'channel' not in kwargs:
            raise TypeError('conda search: override_channels requires channel')

        if 'env' in kwargs:
            cmd_list.extend(['--name', kwargs.pop('env')])
        if 'prefix' in kwargs:
            cmd_list.extend(['--prefix', kwargs.pop('prefix')])
        if 'channel' in kwargs:
            channel = kwargs.pop('channel')
            if isinstance(channel, str):
                cmd_list.extend(['--channel', channel])
            else:
                cmd_list.append('--channel')
                cmd_list.extend(channel)

        for key in keys:
            if key in kwargs and kwargs[key]:
                cmd_list.append('--' + key.replace('_', '-'))

        return cmd_list

    def set_root_prefix(self, prefix=None):
        """
        Set the prefix to the root environment (default is /opt/anaconda).
        This function should only be called once (right after importing
        conda_api).
        """
        global ROOT_PREFIX

        if prefix:
            ROOT_PREFIX = prefix
        # find *some* conda instance, and then use info() to get 'root_prefix'
        else:
            pass
#            i = self.info(abspath=False)
#            self.ROOT_PREFIX = i['root_prefix']
            '''
            plat = 'posix'
            if sys.platform.lower().startswith('win'):
                listsep = ';'
                plat = 'win'
            else:
                listsep = ':'

            for p in os.environ['PATH'].split(listsep):
                if (os.path.exists(os.path.join(p, 'conda')) or
                    os.path.exists(os.path.join(p, 'conda.exe')) or
                    os.path.exists(os.path.join(p, 'conda.bat'))):

                    # TEMPORARY:
                    ROOT_PREFIX = os.path.dirname(p) # root prefix is 1 dir up
                    i = info()
                    # REAL:
                    ROOT_PREFIX = i['root_prefix']
                    break
            else: # fall back to standard install location, which may be wrong
                if plat == 'win':
                    ROOT_PREFIX = 'C:\Anaconda'
                else:
                    ROOT_PREFIX = '/opt/anaconda'
            '''
            # adapted code
            # ------------
            if ROOT_PREFIX is None:
                qprocess = QProcess()
                cmd_list = ['conda', 'info', '--json']
                qprocess.start(cmd_list[0], cmd_list[1:])
                qprocess.waitForFinished()

                output = qprocess.readAllStandardOutput()
                output = handle_qbytearray(output, CondaProcess.ENCODING)
                info = json.loads(output)                
                ROOT_PREFIX = info['root_prefix']

    def get_conda_version(self):
        """
        return the version of conda being used (invoked) as a string
        """
#        pat = re.compile(r'conda:?\s+(\d+\.\d\S+|unknown)')
#        stdout, stderr = self._call_conda(['--version'])
#        # argparse outputs version to stderr in Python < 3.4.
#        # http://bugs.python.org/issue18920
#        m = pat.match(stderr.decode().strip())
#        if m is None:
#            m = pat.match(stdout.decode().strip())
#
#        if m is None:
#            raise Exception('output did not match: %r' % stderr)
#        return m.group(1)

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'get_conda_version'
            self._call_conda(['--version'])

    def get_envs(self):
        """
        Return all of the (named) environment (this does not include the root
        environment), as a list of absolute path to their prefixes.
        """
#        info = self._call_and_parse(['info', '--json'])
#        return info['envs']

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'get_envs'
            self._call_and_parse(['info', '--json'])

    def get_prefix_envname(self, name):
        """
        Given the name of an environment return its full prefix path, or None
        if it cannot be found.
        """
#        if name == 'root':
#            return self.ROOT_PREFIX
#        for prefix in self.get_envs():
#            if basename(prefix) == name:
#                return prefix
#        return None

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._name = name
            self._function_called = 'get_prefix_envname'
            self._call_and_parse(['info', '--json'])

    def info(self, abspath=True):
        """
        Return a dictionary with configuration information.
        No guarantee is made about which keys exist.  Therefore this function
        should only be used for testing and debugging.
        """
#        return self._call_and_parse(['info', '--json'], abspath=abspath)

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'info'
            self._call_and_parse(['info', '--json'], abspath=abspath)

    def package_info(self, package, abspath=True):
        """
        Return a dictionary with package information.

        Structure is {
            'package_name': [{
                'depends': list,
                'version': str,
                'name': str,
                'license': str,
                'fn': ...,
                ...
            }]
        }
        """
#        return self._call_and_parse(['info', package, '--json'],
#                                    abspath=abspath)

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'package_info'
            self._call_and_parse(['info', package, '--json'], abspath=abspath)

    def search(self, regex=None, spec=None, **kwargs):
        """
        Search for packages.
        """
        cmd_list = ['search', '--json']

        if regex and spec:
            raise TypeError('conda search: only one of regex or spec allowed')

        if regex:
            cmd_list.append(regex)

        if spec:
            cmd_list.extend(['--spec', spec])

        if 'platform' in kwargs:
            platform = kwargs.pop('platform')
            platforms = ('win-32', 'win-64', 'osx-64', 'linux-32', 'linux-64')
            if platform not in platforms:
                raise TypeError('conda search: platform must be one of ' +
                                ', '.join(platforms))
            cmd_list.extend(['--platform', platform])

        cmd_list.extend(
            self._setup_install_commands_from_kwargs(
                kwargs,
                ('canonical', 'unknown', 'use_index_cache', 'outdated',
                 'override_channels')))

#        return self._call_and_parse(cmd_list,
#                                    abspath=kwargs.get('abspath', True))
        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'search'
            self._call_and_parse(cmd_list, abspath=kwargs.get('abspath', True))

    def share(self, prefix):
        """
        Create a "share package" of the environment located in `prefix`,
        and return a dictionary with (at least) the following keys:
          - 'path': the full path to the created package
          - 'warnings': a list of warnings

        This file is created in a temp directory, and it is the callers
        responsibility to remove this directory (after the file has been
        handled in some way).
        """
#        return self._call_and_parse(['share', '--json', '--prefix', prefix])

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'share'
            self._call_and_parse(['share', '--json', '--prefix', prefix])

    def create(self, name=None, path=None, pkgs=None):
        """
        Create an environment either by name or path with a specified set of
        packages
        """
        if not pkgs or not isinstance(pkgs, (list, tuple)):
            raise TypeError('must specify a list of one or more packages to '
                            'install into new environment')

        cmd_list = ['create', '--yes', '--quiet']
        if name:
            ref = name
            search = [os.path.join(d, name) for d in self.info()['envs_dirs']]
            cmd_list = ['create', '--yes', '--quiet', '--name', name]
        elif path:
            ref = path
            search = [path]
            cmd_list = ['create', '--yes', '--quiet', '--prefix', path]
        else:
            raise TypeError('must specify either an environment name or a path'
                            ' for new environment')

        if any(os.path.exists(path) for path in search):
            raise CondaEnvExistsError('Conda environment [%s] already exists'
                                      % ref)

        cmd_list.extend(pkgs)
#        (out, err) = self._call_conda(cmd_list)
#        if err.decode().strip():
#            raise CondaError('conda %s: %s' % (" ".join(cmd_list),
#                                               err.decode()))
#        return out

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'create'
            self._call_conda(cmd_list)

    def install(self, name=None, path=None, pkgs=None, dep=True):
        """
        Install packages into an environment either by name or path with a
        specified set of packages
        """
        if not pkgs or not isinstance(pkgs, (list, tuple)):
            raise TypeError('must specify a list of one or more packages to '
                            'install into existing environment')

        cmd_list = ['install', '--yes', '--json', '--force-pscheck']
#        cmd_list = ['install', '--yes', '--quiet']        
        if name:
            cmd_list.extend(['--name', name])
        elif path:
            cmd_list.extend(['--prefix', path])
        else:  # just install into the current environment, whatever that is
            pass

        cmd_list.extend(pkgs)

#        (out, err) = self._call_conda(cmd_list)
#        if err.decode().strip():
#            raise CondaError('conda %s: %s' % (" ".join(cmd_list),
#                                               err.decode()))
#        return out

        # adapted code
        # ------------
        if not dep:
            cmd_list.extend(['--no-deps'])

        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'install'
            self._call_conda(cmd_list)

    def update(self, *pkgs, **kwargs):
        """
        Update package(s) (in an environment) by name.
        """
        cmd_list = ['update', '--json', '--quiet', '--yes']

        if not pkgs and not kwargs.get('all'):
            raise TypeError("Must specify at least one package to update, \
                            or all=True.")

        cmd_list.extend(
            self._setup_install_commands_from_kwargs(
                kwargs,
                ('dry_run', 'no_deps', 'override_channels',
                 'no_pin', 'force', 'all', 'use_index_cache', 'use_local',
                 'alt_hint')))

        cmd_list.extend(pkgs)

#        result = self._call_and_parse(cmd_list,
#                                      abspath=kwargs.get('abspath', True))
#
#        if 'error' in result:
#            raise CondaError('conda %s: %s' % (" ".join(cmd_list),
#                                               result['error']))
#
#        return result

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'update'
            self._call_and_parse(cmd_list, abspath=kwargs.get('abspath', True))

    def remove(self, *pkgs, **kwargs):
        """
        Remove a package (from an environment) by name.

        Returns {
            success: bool, (this is always true),
            (other information)
        }
        """
        cmd_list = ['remove', '--json', '--quiet', '--yes', '--force-pscheck']
#        cmd_list = ['remove', '--json', '--quiet', '--yes']

        if not pkgs and not kwargs.get('all'):
            raise TypeError("Must specify at least one package to remove, \
                            or all=True.")

        if kwargs.get('name') and kwargs.get('path'):
            raise TypeError('conda remove: At most one of name, path allowed')

        if kwargs.get('name'):
            cmd_list.extend(['--name', kwargs.pop('name')])

        if kwargs.get('path'):
            cmd_list.extend(['--prefix', kwargs.pop('path')])

        cmd_list.extend(
            self._setup_install_commands_from_kwargs(
                kwargs,
                ('dry_run', 'features', 'override_channels',
                 'no_pin', 'force', 'all')))

        cmd_list.extend(pkgs)

#        result = self._call_and_parse(cmd_list,
#                                      abspath=kwargs.get('abspath', True))
#
#        if 'error' in result:
#            raise CondaError('conda %s: %s' % (" ".join(cmd_list),
#                                               result['error']))
#
#        return result

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'remove'
            self._call_and_parse(cmd_list,
                                 abspath=kwargs.get('abspath', True))

    def remove_environment(self, name=None, path=None, **kwargs):
        """
        Remove an environment entirely.

        See ``remove``.
        """
#        return self.remove(name=name, path=path, all=True, **kwargs)

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'remove_environment'
            self.remove(name=name, path=path, all=True, **kwargs)

    def clone_environment(self, clone, name=None, path=None, **kwargs):
        """
        Clone the environment ``clone`` into ``name`` or ``path``.
        """
        cmd_list = ['create', '--json', '--quiet']

        if (name and path) or not (name or path):
            raise TypeError("conda clone_environment: exactly one of name or \
                            path required")

        if name:
            cmd_list.extend(['--name', name])

        if path:
            cmd_list.extend(['--prefix', path])

        cmd_list.extend(['--clone', clone])

        cmd_list.extend(
            self._setup_install_commands_from_kwargs(
                kwargs,
                ('dry_run', 'unknown', 'use_index_cache', 'use_local',
                 'no_pin', 'force', 'all', 'channel', 'override_channels',
                 'no_default_packages')))

#        result = self._call_and_parse(cmd_list,
#                                      abspath=kwargs.get('abspath', True))
#
#        if 'error' in result:
#            raise CondaError('conda %s: %s' % (" ".join(cmd_list),
#                                               result['error']))
#
#        return result

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'clone_environment'
            self._call_and_parse(cmd_list, abspath=kwargs.get('abspath', True))

#    def process(self, name=None, path=None, cmd=None, args=None, stdin=None,
#                stdout=None, stderr=None, timeout=None):
#        """
#        Create a Popen process for cmd using the specified args but in the
#        conda environment specified by name or path.
#
#        The returned object will need to be invoked with p.communicate() or
#        similar.
#
#        :param name: name of conda environment
#        :param path: path to conda environment (if no name specified)
#        :param cmd:  command to invoke
#        :param args: argument
#        :param stdin: stdin
#        :param stdout: stdout
#        :param stderr: stderr
#        :return: Popen object
#        """
#
#        if bool(name) == bool(path):
#            raise TypeError('exactly one of name or path must be specified')
#
#        if not cmd:
#            raise TypeError('cmd to execute must be specified')
#
#        if not args:
#            args = []
#
#        if name:
#            path = self.get_prefix_envname(name)
#
#        plat = 'posix'
#        if sys.platform.lower().startswith('win'):
#            listsep = ';'
#            plat = 'win'
#        else:
#            listsep = ':'
#
#        conda_env = dict(os.environ)
#
#        if plat == 'posix':
#            conda_env['PATH'] = path + os.path.sep + 'bin' + listsep + \
#                conda_env['PATH']
#        else: # win
#            conda_env['PATH'] = path + os.path.sep + 'Scripts' + listsep + \
#                conda_env['PATH']
#
#        conda_env['PATH'] = path + listsep + conda_env['PATH']
#
#        cmd_list = [cmd]
#        cmd_list.extend(args)
#
#        try:
#            p = Popen(cmd_list, env=conda_env, stdin=stdin, stdout=stdout,
#                      stderr=stderr)
#        except OSError:
#            raise Exception("could not invoke %r\n" % cmd_list)
#        return p

    def clone(self, path, prefix):
        """
        Clone a "share package" (located at `path`) by creating a new
        environment at `prefix`, and return a dictionary with (at least) the
        following keys:
          - 'warnings': a list of warnings

        The directory `path` is located in, should be some temp directory or
        some other directory OUTSIDE /opt/anaconda.  After calling this
        function, the original file (at `path`) may be removed (by the caller
        of this function).
        The return object is a list of warnings.
        """
#        return self._call_and_parse(['clone', '--json', '--prefix', prefix,
#                                     path])
        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'clone'
            self._call_and_parse(['clone', '--json', '--prefix', prefix, path])

    def _setup_config_from_kwargs(kwargs):
        cmd_list = ['--json', '--force']

        if 'file' in kwargs:
            cmd_list.extend(['--file', kwargs['file']])

        if 'system' in kwargs:
            cmd_list.append('--system')

        return cmd_list

    def config_path(self, **kwargs):
        """
        Get the path to the config file.
        """
        cmd_list = ['config', '--get']
        cmd_list.extend(self._setup_config_from_kwargs(kwargs))

#        result = self._call_and_parse(cmd_list,
#                                      abspath=kwargs.get('abspath', True))
#
#        if 'error' in result:
#            raise CondaError('conda %s: %s' % (" ".join(cmd_list),
#                                               result['error']))
#        return result['rc_path']

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'config_path'
            self._call_and_parse(cmd_list, abspath=kwargs.get('abspath', True))

    def config_get(self, *keys, **kwargs):
        """
        Get the values of configuration keys.

        Returns a dictionary of values. Note, the key may not be in the
        dictionary if the key wasn't set in the configuration file.
        """
        cmd_list = ['config', '--get']
        cmd_list.extend(keys)
        cmd_list.extend(self._setup_config_from_kwargs(kwargs))

#        result = self._call_and_parse(cmd_list,
#                                      abspath=kwargs.get('abspath', True))
#
#        if 'error' in result:
#            raise CondaError('conda %s: %s' % (" ".join(cmd_list),
#                                               result['error']))
#        return result['get']

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'config_get'
            self._call_and_parse(cmd_list, abspath=kwargs.get('abspath', True))

    def config_set(self, key, value, **kwargs):
        """
        Set a key to a (bool) value.

        Returns a list of warnings Conda may have emitted.
        """
        cmd_list = ['config', '--set', key, str(value)]
        cmd_list.extend(self._setup_config_from_kwargs(kwargs))

#        result = self._call_and_parse(cmd_list,
#                                      abspath=kwargs.get('abspath', True))
#
#        if 'error' in result:
#            raise CondaError('conda %s: %s' % (" ".join(cmd_list),
#                                               result['error']))
#        return result.get('warnings', [])

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'config_set'
            self._call_and_parse(cmd_list, abspath=kwargs.get('abspath', True))

    def config_add(self, key, value, **kwargs):
        """
        Add a value to a key.

        Returns a list of warnings Conda may have emitted.
        """
        cmd_list = ['config', '--add', key, value]
        cmd_list.extend(self._setup_config_from_kwargs(kwargs))

#        result = self._call_and_parse(cmd_list,
#                                      abspath=kwargs.get('abspath', True))
#
#        if 'error' in result:
#            raise CondaError('conda %s: %s' % (" ".join(cmd_list),
#                                               result['error']))
#        return result.get('warnings', [])

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'config_add'
            self._call_and_parse(cmd_list, abspath=kwargs.get('abspath', True))

    def config_remove(self, key, value, **kwargs):
        """
        Remove a value from a key.

        Returns a list of warnings Conda may have emitted.
        """
        cmd_list = ['config', '--remove', key, value]
        cmd_list.extend(self._setup_config_from_kwargs(kwargs))

#        result = self._call_and_parse(cmd_list,
#                                      abspath=kwargs.get('abspath', True))
#
#        if 'error' in result:
#            raise CondaError('conda %s: %s' % (" ".join(cmd_list),
#                                               result['error']))
#        return result.get('warnings', [])

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'config_remove'
            self._call_and_parse(cmd_list, abspath=kwargs.get('abspath', True))

    def config_delete(self, key, **kwargs):
        """
        Remove a key entirely.

        Returns a list of warnings Conda may have emitted.
        """
        cmd_list = ['config', '--remove-key', key]
        cmd_list.extend(self._setup_config_from_kwargs(kwargs))

#        result = self._call_and_parse(cmd_list,
#                                      abspath=kwargs.get('abspath', True))
#
#        if 'error' in result:
#            raise CondaError('conda %s: %s' % (" ".join(cmd_list),
#                                               result['error']))
#        return result.get('warnings', [])

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'config_delete'
            self._call_and_parse(cmd_list, abspath=kwargs.get('abspath', True))

    def run(self, command, abspath=True):
        """
        Launch the specified app by name or full package name.

        Returns a dictionary containing the key "fn", whose value is the full
        package (ending in ``.tar.bz2``) of the app.
        """
        cmd_list = ['run', '--json', command]

#        result = self._call_and_parse(cmd_list, abspath=abspath)
#
#        if 'error' in result:
#            raise CondaError('conda %s: %s' % (" ".join(cmd_list),
#                                               result['error']))
#        return result

        # adapted code
        # ------------
        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'run'
            self._call_and_parse(cmd_list, abspath=abspath)

#    def test():
#        """
#        Self-test function, which prints useful debug information.
#        This function returns None on success, and will crash the interpreter
#        on failure.
#        """
#        print('sys.version: %r' % sys.version)
#        print('sys.prefix : %r' % sys.prefix)
#        print('conda_api.__version__: %r' % __version__)
#        print('conda_api.ROOT_PREFIX: %r' % ROOT_PREFIX)
#        if isdir(ROOT_PREFIX):
#            conda_version = get_conda_version()
#            print('conda version: %r' % conda_version)
#            print('conda info:')
#            d = info()
#            for kv in d.items():
#                print('\t%s=%r' % kv)
#            assert d['conda_version'] == conda_version
#        else:
#            print('Warning: no such directory: %r' % ROOT_PREFIX)
#        print('OK')

    # ---- Additional methods not in conda-api
    def pip(self, name):
        """ """
        cmd_list = ['list', '-n', name]

        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'pip'
            self._call_conda(cmd_list)

    def dependencies(self, name=None, path=None, pkgs=None, dep=True):
        """
        Install packages into an environment either by name or path with a
        specified set of packages
        """
        if not pkgs or not isinstance(pkgs, (list, tuple)):
            raise TypeError('must specify a list of one or more packages to '
                            'install into existing environment')

        cmd_list = ['install', '--dry-run', '--json']
        cmd_list = ['install', '--dry-run', '--json', '--force-pscheck']

        if not dep:
            cmd_list.extend(['--no-deps'])

        if name:
            cmd_list.extend(['--name', name])
        elif path:
            cmd_list.extend(['--prefix', path])
        else:  # just install into the current environment, whatever that is
            pass

        cmd_list.extend(pkgs)

        if self._process.state() == QProcess.NotRunning:
            self._function_called = 'install_dry'
            self._call_and_parse(cmd_list)


class TestWidget(QWidget):
    """ """
    def __init__(self, parent):
        QWidget.__init__(self, parent)

        self._parent = parent
        self.cp = CondaProcess(self, self.on_finished)

        # widgets
        self.button_get_conda_version = QPushButton('get_conda_version')
        self.button_info = QPushButton('info')
        self.button_get_envs = QPushButton('get envs')
        self.button_install = QPushButton('install')
        self.button_package_info = QPushButton('package info')

        self.button_linked = QPushButton('linked')

        self.button_pip = QPushButton('pip')

        self.widgets_queue = [self.button_get_conda_version, self.button_info,
                              self.button_get_envs, self.button_install,
                              self.button_package_info, self.button_pip]

        self.widgets = [self.button_linked]

        # layout setup
        layout_top = QHBoxLayout()
        layout_top.addWidget(self.button_get_conda_version)
        layout_top.addWidget(self.button_get_envs)
        layout_top.addWidget(self.button_info)
        layout_top.addWidget(self.button_install)
        layout_top.addWidget(self.button_package_info)

        layout_middle = QHBoxLayout()
        layout_middle.addWidget(self.button_linked)

        layout_bottom = QHBoxLayout()
        layout_bottom.addWidget(self.button_pip)

        layout = QVBoxLayout()
        layout.addLayout(layout_top)
        layout.addLayout(layout_middle)
        layout.addLayout(layout_bottom)

        self.setLayout(layout)

        # signals
        self.button_get_conda_version.clicked.connect(
            self.cp.get_conda_version)
        self.button_get_envs.clicked.connect(self.cp.get_envs)
        self.button_info.clicked.connect(self.cp.info)
        self.button_install.clicked.connect(self.cp.install)
        self.button_package_info.clicked.connect(
            lambda: self.cp.package_info('spyder'))
        self.button_linked.clicked.connect(
            lambda: linked(ROOT_PREFIX))
        self.button_pip.clicked.connect(lambda: self.cp.pip('root'))

        for widget in self.widgets_queue:
            widget.clicked.connect(lambda: self._set_gui_disabled(True))

    def _set_gui_disabled(self, value):
        """ """
        for widget in self.widgets + self.widgets_queue:
            widget.setDisabled(value)

    def on_finished(self):
        """ """
        self._set_gui_disabled(False)
        output = self.cp.output
        error = self.cp.error
        function_called = self.cp._function_called
        print('stdout:\t' + str(output))
        print('stderr:\t' + str(error))
        print('function:\t' + str(function_called))
        print('')


def test():
    """Run conda packages widget test"""
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    widget = TestWidget(None)
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()

