"""
PyProvide module to run GradeFast locally.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import platform
import time

import iochannels
from pyprovide import InjectableClass, InjectableClassType, Module, class_provider, provider

from gradefast import hosts
from gradefast.models import Settings
from gradefast.persister import Persister, ShelvePersister, SqlitePersister


class GradeFastLocalModule(Module):
    """
    A PyProvide module that includes the providers necessary to run GradeFast locally.
    """

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings

    @provider()
    def provide_settings(self) -> Settings:
        return self._settings

    @provider("Output Log")
    def provide_output_log(self, settings: Settings) -> iochannels.Log:
        if not settings.log_file:
            return iochannels.NullLog()

        file = open(settings.log_file.get_local_path(), "a", encoding="utf8")
        if settings.log_as_html:
            file.write("<h1>\n")
        else:
            file.write("=" * 79 + "\n")
        file.write("GradeFast Log -- ")
        file.write(time.asctime())
        file.write("\n")
        if settings.log_as_html:
            file.write("</h1>\n")
            return iochannels.HTMLFileLog(file)
        else:
            file.write("=" * 79 + "\n")
            return iochannels.FileLog(file)

    @provider(output_log="Output Log")
    def provide_cli_channel(self, settings: Settings, output_log: iochannels.Log) -> \
            iochannels.Channel:
        if settings.use_color:
            return iochannels.ColorCLIChannel(output_log, use_readline=settings.use_readline,
                                              application_name_for_error="GradeFast")
        else:
            return iochannels.CLIChannel(output_log, use_readline=settings.use_readline)

    @provider()
    def provide_host(self, local_host: hosts.LocalHost) -> hosts.Host:
        return local_host

    @class_provider()
    def provide_local_host(self) -> InjectableClass[hosts.LocalHost]:
        if platform.system() == "Windows":
            return hosts.LocalWindowsHost
        elif platform.system() == "Darwin":
            return hosts.LocalMacHost
        elif platform.system() == "Linux":
            return hosts.LocalLinuxHost
        else:
            return hosts.LocalHost

    @class_provider()
    def provide_persister(self, settings: Settings) -> InjectableClass[Persister]:
        if settings.use_legacy_save_file_format:
            return ShelvePersister
        else:
            return SqlitePersister
