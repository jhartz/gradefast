"""
PyProvide module to run GradeFast locally.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import platform

import iochannels
from pyprovide import InjectableClass, Module, class_provider, provider

from gradefast import hosts
from gradefast.models import Settings


class GradeFastLocalModule(Module):
    """
    A PyProvide module that includes the providers necessary to run GradeFast locally.
    """

    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings

    @provider()
    def provide_settings(self) -> Settings:
        return self._settings

    @provider("Submission Log")
    def provide_submission_log(self) -> iochannels.MemoryLog:
        return iochannels.HTMLMemoryLog()

    @provider(submission_log="Submission Log")
    def provide_cli_channel(self, settings: Settings, submission_log: iochannels.MemoryLog) -> \
            iochannels.Channel:
        if settings.use_color:
            return iochannels.ColorCLIChannel(submission_log,
                                              application_name_for_error="GradeFast")
        else:
            return iochannels.CLIChannel(submission_log)

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
