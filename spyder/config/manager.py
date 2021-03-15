# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Configuration manager providing access to user/site/project configuration.
"""

# Standard library imports
import logging
import os
import os.path as osp
from typing import Optional, Any
import weakref

# Local imports
from spyder.api.utils import PrefixedTuple
from spyder.config.base import _, get_conf_paths, get_conf_path, get_home_dir
from spyder.config.main import CONF_VERSION, DEFAULTS, NAME_MAP
from spyder.config.types import ConfigurationKey, ConfigurationObserver
from spyder.config.user import UserConfig, MultiUserConfig, NoDefault, cp
from spyder.utils.programs import check_version


logger = logging.getLogger(__name__)

EXTRA_VALID_SHORTCUT_CONTEXTS = [
    '_',
    'array_builder',
    'console',
    'find_replace',
]


class ConfigurationManager(object):
    """
    Configuration manager to provide access to user/site/project config.
    """

    def __init__(self, parent=None, active_project_callback=None):
        """
        Configuration manager to provide access to user/site/project config.
        """
        path = self.get_user_config_path()
        if not osp.isdir(path):
            os.makedirs(path)

        # Site configuration defines the system defaults if a file
        # is found in the site location
        conf_paths = get_conf_paths()
        site_defaults = DEFAULTS
        for conf_path in reversed(conf_paths):
            conf_fpath = os.path.join(conf_path, 'spyder.ini')
            if os.path.isfile(conf_fpath):
                site_config = UserConfig(
                    'spyder',
                    path=conf_path,
                    defaults=site_defaults,
                    load=False,
                    version=CONF_VERSION,
                    backup=False,
                    raw_mode=True,
                    remove_obsolete=False,
                )
                site_defaults = site_config.to_list()

        self._parent = parent
        self._active_project_callback = active_project_callback
        self._user_config = MultiUserConfig(
            NAME_MAP,
            path=path,
            defaults=site_defaults,
            load=True,
            version=CONF_VERSION,
            backup=True,
            raw_mode=True,
            remove_obsolete=False,
        )

        # Store plugin configurations when CONF_FILE = True
        self._plugin_configs = {}

        # TODO: To be implemented in following PR
        self._project_configs = {}  # Cache project configurations

        # Object observer map
        # This dict maps from a configuration key (str/tuple) to a set
        # of objects that should be notified on changes to the corresponding
        # subscription key per section. The observer objects must be hashable.
        #
        # type: Dict[ConfigurationKey, Dict[str, Set[ConfigurationObserver]]]
        self._observers = {}

        # Set of suscription keys per observer object
        # This dict maps from a observer object to the set of configuration
        # keys that the object is subscribed to per section.
        #
        # type: Dict[ConfigurationObserver, Dict[str, Set[ConfigurationKey]]]
        self._observer_map_keys = weakref.WeakKeyDictionary()

        # Setup
        self.remove_deprecated_config_locations()

    def register_plugin(self, plugin_class):
        """Register plugin configuration."""
        conf_section = plugin_class.CONF_SECTION
        if plugin_class.CONF_FILE and conf_section:
            path = self.get_plugin_config_path(conf_section)
            version = plugin_class.CONF_VERSION
            version = version if version else '0.0.0'
            name_map = plugin_class._CONF_NAME_MAP
            name_map = name_map if name_map else {'spyder': []}
            defaults = plugin_class.CONF_DEFAULTS

            if conf_section in self._plugin_configs:
                raise RuntimeError('A plugin with section "{}" already '
                                   'exists!'.format(conf_section))

            plugin_config = MultiUserConfig(
                name_map,
                path=path,
                defaults=defaults,
                load=True,
                version=version,
                backup=True,
                raw_mode=True,
                remove_obsolete=False,
                external_plugin=True
            )

            # Recreate external plugin configs to deal with part two
            # (the shortcut conflicts) of spyder-ide/spyder#11132
            spyder_config = self._user_config._configs_map['spyder']
            if check_version(spyder_config._old_version, '54.0.0', '<'):
                # Remove all previous .ini files
                try:
                    plugin_config.cleanup()
                except EnvironmentError:
                    pass

                # Recreate config
                plugin_config = MultiUserConfig(
                    name_map,
                    path=path,
                    defaults=defaults,
                    load=True,
                    version=version,
                    backup=True,
                    raw_mode=True,
                    remove_obsolete=False,
                    external_plugin=True
                )

            self._plugin_configs[conf_section] = (plugin_class, plugin_config)

    def remove_deprecated_config_locations(self):
        """Removing old .spyder.ini location."""
        old_location = osp.join(get_home_dir(), '.spyder.ini')
        if osp.isfile(old_location):
            os.remove(old_location)

    def get_active_conf(self, section=None):
        """
        Return the active user or project configuration for plugin.
        """
        # Add a check for shortcuts!
        if section is None:
            config = self._user_config
        elif section in self._plugin_configs:
            _, config = self._plugin_configs[section]
        else:
            # TODO: implement project configuration on the following PR
            config = self._user_config

        return config

    def get_user_config_path(self):
        """Return the user configuration path."""
        base_path = get_conf_path()
        path = osp.join(base_path, 'config')
        if not osp.isdir(path):
            os.makedirs(path)

        return path

    def get_plugin_config_path(self, plugin_folder):
        """Return the plugin configuration path."""
        base_path = get_conf_path()
        path = osp.join(base_path, 'plugins')
        if plugin_folder is None:
            raise RuntimeError('Plugin needs to define `CONF_SECTION`!')
        path = osp.join(base_path, 'plugins', plugin_folder)
        if not osp.isdir(path):
            os.makedirs(path)

        return path

    # --- Observer pattern
    # ------------------------------------------------------------------------
    def observe_configuration(self,
                              observer: ConfigurationObserver,
                              section: str,
                              option: Optional[ConfigurationKey] = None):
        """
        Register an `observer` object to listen for changes in the option
        `option` on the configuration `section`.

        Parameters
        ----------
        observer: ConfigurationObserver
            Object that conforms to the `ConfigurationObserver` protocol.
        section: str
            Name of the configuration section that contains the option
            :param:`option`
        option: Optional[ConfigurationKey]
            Name of the option on the configuration section :param:`section`
            that the object is going to suscribe to. If None, the observer
            will observe any changes on any of the options of the configuration
            section.
        """
        section_sets = self._observers.get(section, {})
        option = option if option is not None else '__section'

        option_set = section_sets.get(option, weakref.WeakSet())
        option_set |= {observer}

        section_sets[option] = option_set
        self._observers[section] = section_sets

        observer_section_sets = self._observer_map_keys.get(observer, {})
        section_set = observer_section_sets.get(section, set({}))
        section_set |= {option}

        observer_section_sets[section] = section_set
        self._observer_map_keys[observer] = observer_section_sets

    def unobserve_configuration(self,
                                observer: ConfigurationObserver,
                                section: Optional[str] = None,
                                option: Optional[ConfigurationKey] = None):
        """
        Remove an observer to prevent it to receive further changes
        on the values of the option `option` of the configuration section
        `section`.

        Parameters
        ----------
        observer: ConfigurationObserver
            Object that conforms to the `ConfigurationObserver` protocol.
        section: Optional[str]
            Name of the configuration section that contains the option
            :param:`option`. If None, the observer is unregistered from all
            options for all sections that it has registered to.
        option: Optional[ConfigurationKey]
            Name of the configuration option on the configuration
            :param:`section` that the observer is going to be unsubscribed
            from. If None, the observer is unregistered from all the options of
            the section `section`.
        """
        if observer not in self._observer_map_keys:
            return

        observer_sections = self._observer_map_keys[observer]
        if section is not None:
            section_options = observer_sections[section]
            section_observers = self._observers[section]
            if option is None:
                for option in section_options:
                    option_observers = section_observers[option]
                    option_observers.remove(observer)
                observer_sections.pop(section)
            else:
                option_observers = section_observers[option]
                option_observers.remove(observer)
        else:
            for section in observer_sections:
                section_options = observer_sections[section]
                section_observers = self._observers[section]
                for option in section_options:
                    option_observers = section_observers[option]
                    option_observers.remove(observer)
            self._observer_map_keys.pop(observer)

    def notify_all_observers(self):
        """
        Notify all the observers subscribed to all the sections and options.
        """
        for section in self._observers:
            self.notify_section_all_observers(section)

    def notify_observers(self,
                         section: str,
                         option: ConfigurationKey,
                         recursive_notification: bool = True):
        """
        Notify observers of a change in the option `option` of configuration
        section `section`.

        Parameters
        ----------
        section: str
            Name of the configuration section whose option did changed.
        option: ConfigurationKey
            Name/Path to the option that did changed.
        recursive_notification: bool
            If True, all objects that observe all changes on the
            configuration section and objects that observe partial tuple paths
            are notified. For example if the option `opt` of section `sec`
            changes, then the observers for section `sec` are notified.
            Likewise, if the option `(a, b, c)` changes, then observers for
            `(a, b, c)`, `(a, b)` and a are notified as well.
        """
        if recursive_notification:
            # Notify to section listeners
            self._notify_section(section)

        if isinstance(option, tuple) and recursive_notification:
            # Notify to partial tuple observers
            # e.g., If the option is (a, b, c), observers subscribed to
            # (a, b, c), (a, b) and a are notified
            option_list = list(option)
            while option_list != []:
                tuple_option = tuple(option_list)
                if len(option_list) == 1:
                    tuple_option = tuple_option[0]

                value = self.get(section, tuple_option)
                self._notify_option(section, tuple_option, value)
                option_list.pop(-1)
        else:
            if option == '__section':
                self._notify_section(section)
            else:
                value = self.get(section, option)
                self._notify_option(section, option, value)

    def _notify_option(self, section: str, option: ConfigurationKey,
                       value: Any):
        section_observers = self._observers.get(section, {})
        option_observers = section_observers.get(option, set({}))
        if len(option_observers) > 0:
            logger.debug('Sending notification to observers of '
                         f'{option} in configuration section {section}')
        for observer in list(option_observers):
            try:
                observer.on_configuration_change(option, section, value)
            except RuntimeError:
                # Prevent errors when Qt Objects are destroyed
                self.unobserve_configuration(observer)

    def _notify_section(self, section: str):
        section_values = dict(self.items(section) or [])
        self._notify_option(section, '__section', section_values)

    def notify_section_all_observers(self, section: str):
        """Notify all the observers subscribed to any option of a section."""
        option_observers = self._observers[section]
        section_prefix = PrefixedTuple()
        # Notify section observers
        CONF.notify_observers(section, '__section')
        for option in option_observers:
            if isinstance(option, tuple):
                section_prefix.add_path(option)
            else:
                try:
                    self.notify_observers(section, option)
                except cp.NoOptionError:
                    # Skip notification if the option/section does not exist.
                    # This prevents unexpected errors in the test suite.
                    pass
        # Notify prefixed observers
        for prefix in section_prefix:
            try:
                self.notify_observers(section, prefix)
            except cp.NoOptionError:
                # See above explanation.
                pass

    # --- Projects
    # ------------------------------------------------------------------------
    def register_config(self, root_path, config):
        """
        Register configuration with `root_path`.

        Useful for registering project configurations as they are opened.
        """
        if self.is_project_root(root_path):
            if root_path not in self._project_configs:
                self._project_configs[root_path] = config
        else:
            # Validate which are valid site config locations
            self._site_config = config

    def get_active_project(self):
        """Return the `root_path` of the current active project."""
        callback = self._active_project_callback
        if self._active_project_callback:
            return callback()

    def is_project_root(self, root_path):
        """Check if `root_path` corresponds to a valid spyder project."""
        return False

    def get_project_config_path(self, project_root):
        """Return the project configuration path."""
        path = osp.join(project_root, '.spyproj', 'config')
        if not osp.isdir(path):
            os.makedirs(path)

    # MultiUserConf/UserConf interface
    # ------------------------------------------------------------------------
    def items(self, section):
        """Return all the items option/values for the given section."""
        config = self.get_active_conf(section)
        return config.items(section)

    def options(self, section):
        """Return all the options for the given section."""
        config = self.get_active_conf(section)
        return config.options(section)

    def get(self, section, option, default=NoDefault):
        """
        Get an `option` on a given `section`.

        If section is None, the `option` is requested from default section.
        """
        config = self.get_active_conf(section)
        if isinstance(option, tuple) and len(option) == 1:
            option = option[0]

        if isinstance(option, tuple):
            base_option = option[0]
            intermediate_options = option[1:-1]
            last_option = option[-1]

            base_conf = config.get(
                section=section, option=base_option, default={})
            next_ptr = base_conf
            for opt in intermediate_options:
                next_ptr = next_ptr.get(opt, {})

            value = next_ptr.get(last_option, None)
            if value is None:
                value = default
                if default is NoDefault:
                    raise cp.NoOptionError(option, section)
        else:
            value = config.get(section=section, option=option, default=default)
        return value

    def set(self, section, option, value, verbose=False, save=True,
            recursive_notification=True, notification=True):
        """
        Set an `option` on a given `section`.

        If section is None, the `option` is added to the default section.
        """
        original_option = option
        if isinstance(option, tuple):
            base_option = option[0]
            intermediate_options = option[1:-1]
            last_option = option[-1]

            base_conf = self.get(section, base_option, {})
            conf_ptr = base_conf
            for opt in intermediate_options:
                next_ptr = conf_ptr.get(opt, {})
                conf_ptr[opt] = next_ptr
                conf_ptr = next_ptr

            conf_ptr[last_option] = value
            value = base_conf
            option = base_option

        config = self.get_active_conf(section)
        config.set(section=section, option=option, value=value,
                   verbose=verbose, save=save)
        if notification:
            self.notify_observers(
                section, original_option, recursive_notification)

    def get_default(self, section, option):
        """
        Get Default value for a given `section` and `option`.

        This is useful for type checking in `get` method.
        """
        config = self.get_active_conf(section)
        if isinstance(option, tuple):
            base_option = option[0]
            intermediate_options = option[1:-1]
            last_option = option[-1]

            base_default = config.get_default(section, base_option)
            conf_ptr = base_default
            for opt in intermediate_options:
                conf_ptr = conf_ptr[opt]

            return conf_ptr[last_option]

        return config.get_default(section, option)

    def remove_section(self, section):
        """Remove `section` and all options within it."""
        config = self.get_active_conf(section)
        config.remove_section(section)

    def remove_option(self, section, option):
        """Remove `option` from `section`."""
        config = self.get_active_conf(section)
        if isinstance(option, tuple):
            base_option = option[0]
            intermediate_options = option[1:-1]
            last_option = option[-1]

            base_conf = self.get(section, base_option)
            conf_ptr = base_conf
            for opt in intermediate_options:
                conf_ptr = conf_ptr[opt]
            conf_ptr.pop(last_option)
            self.set(section, base_option)
            self.notify_observers(section, base_option)
        else:
            config.remove_option(section, option)

    def reset_to_defaults(self, section=None, notification=True):
        """Reset config to Default values."""
        config = self.get_active_conf(section)
        config.reset_to_defaults(section=section)
        if notification:
            if section is not None:
                self.notify_section_all_observers(section)
            else:
                self.notify_all_observers()

    # Shortcut configuration management
    # ------------------------------------------------------------------------
    def _get_shortcut_config(self, context, plugin_name=None):
        """
        Return the shortcut configuration for global or plugin configs.

        Context must be either '_' for global or the name of a plugin.
        """
        context = context.lower()
        config = self._user_config

        if plugin_name in self._plugin_configs:
            plugin_class, config = self._plugin_configs[plugin_name]

            # Check if plugin has a separate file
            if not plugin_class.CONF_FILE:
                config = self._user_config

        elif context in self._plugin_configs:
            plugin_class, config = self._plugin_configs[context]

            # Check if plugin has a separate file
            if not plugin_class.CONF_FILE:
                config = self._user_config

        elif context in (self._user_config.sections()
                         + EXTRA_VALID_SHORTCUT_CONTEXTS):
            config = self._user_config
        else:
            raise ValueError(_("Shortcut context must match '_' or the "
                               "plugin `CONF_SECTION`!"))

        return config

    def get_shortcut(self, context, name, plugin_name=None):
        """
        Get keyboard shortcut (key sequence string).

        Context must be either '_' for global or the name of a plugin.
        """
        config = self._get_shortcut_config(context, plugin_name)
        return config.get('shortcuts', context + '/' + name.lower())

    def set_shortcut(self, context, name, keystr, plugin_name=None):
        """
        Set keyboard shortcut (key sequence string).

        Context must be either '_' for global or the name of a plugin.
        """
        config = self._get_shortcut_config(context, plugin_name)
        config.set('shortcuts', context + '/' + name, keystr)

    def config_shortcut(self, action, context, name, parent):
        """
        Create a Shortcut namedtuple for a widget.

        The data contained in this tuple will be registered in our shortcuts
        preferences page.
        """
        # We only import on demand to avoid loading Qt modules
        from spyder.config.gui import _config_shortcut

        keystr = self.get_shortcut(context, name)
        sc = _config_shortcut(action, context, name, keystr, parent)
        return sc

    def iter_shortcuts(self):
        """Iterate over keyboard shortcuts."""
        for context_name, keystr in self._user_config.items('shortcuts'):
            context, name = context_name.split('/', 1)
            yield context, name, keystr

        for _, (_, plugin_config) in self._plugin_configs.items():
            items = plugin_config.items('shortcuts')
            if items:
                for context_name, keystr in items:
                    context, name = context_name.split('/', 1)
                    yield context, name, keystr

    def reset_shortcuts(self):
        """Reset keyboard shortcuts to default values."""
        self._user_config.reset_to_defaults(section='shortcuts')
        for _, (_, plugin_config) in self._plugin_configs.items():
            # TODO: check if the section exists?
            plugin_config.reset_to_defaults(section='shortcuts')


CONF = ConfigurationManager()
