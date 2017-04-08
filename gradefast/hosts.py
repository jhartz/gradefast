"""
GradeFast Hosts - Handles interaction between the grader and the operating system.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import errno
import io
import os
import shutil
import subprocess
import threading
import zipfile
from typing import Dict, List, Optional, Tuple

from iochannels import Channel, Msg
from pyprovide import inject

from gradefast.models import LocalPath, Path, Settings


class BackgroundCommand:
    """
    A command that may or may not have finished running.
    """
    def __init__(self):
        self._output = io.StringIO()
        self._output_lock = threading.Lock()
        self._error: Optional[str] = None

    def get_description(self) -> str:
        """
        Return a description of the background command.
        """
        raise NotImplementedError()

    def wait(self):
        """
        Either wait for the command to finish, or return immediately if it is already finished.
        """
        raise NotImplementedError()

    def kill(self):
        """
        Kill the command if it is still running.
        """
        raise NotImplementedError()

    def _add_output(self, output: str):
        """
        Add more output to the output that we have seen thus far. This should be called in the
        wait() and kill() implementations.
        """
        with self._output_lock:
            self._output.write(output)

    def _set_error(self, error_message: str):
        """
        Set an error message. If necessary, this should be called in the wait() and kill()
        implementations.
        """
        self._error = error_message

    def get_output(self) -> str:
        """
        Get all the output from the command.

        This method will call wait() to wait until the command is finished.
        """
        self.wait()
        with self._output_lock:
            self._output.seek(0)
            return self._output.read()

    def get_error(self) -> Optional[str]:
        """
        Get an error message, if the command did not finish successfully.

        This will call wait() to wait until the command is finished.
        """
        self.wait()
        return self._error


class CommandStartError(Exception):
    """
    Represents an error in starting a command.
    """
    def __init__(self, message):
        self.message = message


class CommandRunError(Exception):
    """
    Represents an error in running a command.
    """
    def __init__(self, message):
        self.message = message


class Host:
    """
    Abstract class for interactions between the grader and an operating system host.

    Any method that takes in a file path as an argument or returns one deals exclusively with Path
    (or, occasionally, LocalPath) objects. For more, see Path and LocalPath in models.py.
    """

    @inject()
    def __init__(self, channel: Channel, settings: Settings):
        self.channel = channel
        self.settings = settings

    def run_command(self, command: str, path: Path, environment: Dict[str, str],
                    stdin: Optional[str] = None, print_output: bool = True) -> str:
        """
        Execute a command on this host.

        If print_output is true, the output of the command will be written using self.channel.print
        as it comes in. Regardless of print_output, the output of the command will also be
        returned after the command has finished.

        If input is needed and "stdin" is None, then self.channel.input will be used.

        If there is an error when starting the command (e.g. command not found), a
        CommandStartError will be raised. If there is an error running the command (e.g. the
        command exited with a nonzero return code), a CommandRunError will be raised.

        :param command: The command to run.
        :param path: The working directory for the command.
        :param environment: Any environmental variables for this command.
        :param stdin: Any input to use as stdin. If not provided, self.channel.input will be used.
        :param print_output: Whether to print the output using self.channel.print as it comes in.
        """
        raise NotImplementedError()

    def start_background_command(self, command: str, path: Path, environment: Dict[str, str],
                                 stdin: Optional[str] = None) -> BackgroundCommand:
        """
        Start a command executing in the background.

        If there is an error when starting the command (e.g. command not found), a
        CommandStartError will be raised. However, unlike the "run_command" method, this one will
        never raise a CommandRunError, since it returns before the command has finished.

        To determine if there was an error when running the command, examine the returned
        BackgroundCommand object.

        :param command: The command to run.
        :param path: The working directory for the command.
        :param environment: Any environmental variables for this command.
        :param stdin: Any input to use as stdin.

        :return: A BackgroundCommand representing the executing command.
        """
        raise NotImplementedError()

    def exists(self, path: Path) -> bool:
        """
        Determine whether a path exists (i.e. is a file or a folder) and is accessible.
        """
        raise NotImplementedError()

    def folder_exists(self, path: Path) -> bool:
        """
        Determine whether a folder exists (i.e. the path exists and it is an accessible folder).
        """
        raise NotImplementedError()

    def move_to_folder(self, path: Path, folder_path: Path):
        """
        Move a file into a destination folder. The destination folder will be created if it doesn't
        already exist.
        """
        raise NotImplementedError()

    def unzip(self, path: Path, folder_path: Path):
        """
        Unzip a zipfile into a destination folder. The destination folder may already exist.
        """
        raise NotImplementedError()

    def get_home_folder(self) -> Path:
        """
        Get the path to a "home folder", or equivalent.
        """
        raise NotImplementedError()

    def list_folder(self, path: Path) -> List[Tuple[str, str, bool]]:
        """
        Get the contents of a folder. If the folder cannot be found, raise a FileNotFoundError with
        a detailed error message.

        :param path: The path of the folder to list. This will be based on values returned from the
            get_home_folder, list_folder, and choose_folder methods.
        :return: A list of tuples of the form (name, type, is_link). The type should be one of:
            "file", "folder", or some other string for a special or inaccessible file. If the type
            is unknown, use None.
        """
        raise NotImplementedError()

    def print_folder(self, path: Path, base_path: Optional[Path] = None):
        """
        Print a listing of the contents of a folder.

        :param path: The path to the folder.
        :param base_path: The path to a base folder that "folder" is relative to (only used when
            printing the folder path to the user).
        """
        files = []
        folders = []
        other = []
        for name, type, is_link in self.list_folder(path):
            if type == "file":
                files.append((name, is_link))
            elif type == "folder":
                folders.append((name, is_link))
            else:
                other.append((name, type, is_link))

        self.channel.status("{}", path.relative_str(base_path))
        listings: List[Msg] = [Msg(end="").accent("../")]

        for name, is_link in sorted(folders, key=lambda f: f[0]):
            listing = Msg(end="")
            listing.accent("{}/", name)
            if is_link:
                listing.bright("(link)")
            listings.append(listing)

        for name, is_link in sorted(files, key=lambda f: f[0]):
            listing = Msg(end="")
            listing.print("{}", name)
            if is_link:
                listing.bright("(link)")
            listings.append(listing)

        for name, type, is_link in sorted(other, key=lambda f: f[0]):
            listings.append(listing)
            listing.print("{}", name)
            if is_link:
                listing.bright("(link")
                if type is not None:
                    listing.print(" to {}", type)
                listing.print(")")
            elif type is not None:
                listing.print("({})", type)
            listings.append(listing)

        self.channel.output_list(listings)

    def _choose_folder_cli(self, start_path: Optional[Path] = None) -> Optional[Path]:
        """
        Interactively choose a folder. This implementation makes use of the other Host methods and
        Channel methods to prompt the user for a folder through the command line. For details, see
        the choose_folder documentation.
        """
        if start_path is not None and not self.folder_exists(start_path):
            self.channel.output(Msg().error("Start folder not found:").print(start_path))
            start_path = None
        if start_path is None:
            start_path = self.get_home_folder()

        old_path = None
        path = start_path
        while True:
            try:
                folder_listing = self.list_folder(path)
            except FileNotFoundError:
                self.channel.output(Msg().error("Folder not found:").print(path))
                if old_path is None:
                    # list_dir must have failed on the results from get_home_folder()
                    # Let's just give up :(
                    return None
                else:
                    # Go back to a known existing folder
                    path = old_path
                    continue

            self.channel.print()
            self.print_folder(path, start_path)
            choice = self.channel.input(
                "Choose a folder (or \"Enter\" to stop):",
                [name for name, type, _ in folder_listing if type == "folder"]).strip()
            if not choice:
                choice = self.channel.prompt("Satisfied? (\"c\" to cancel)", ["Y", "n", "c"], "y")
                if choice == "y":
                    break
                elif choice == "n":
                    continue
                elif choice == "c":
                    return None
            old_path = path
            path = path.append(choice)

        return path

    def _choose_folder_gui(self, start_path: Optional[Path] = None) -> Optional[Path]:
        """
        Interactively choose a folder via a graphical interface. This should be overridden by
        subclasses if it is possible to show the user a GUI file chooser window. Otherwise,
        _choose_folder_cli is used. For details, see the choose_folder documentation.
        """
        return self._choose_folder_cli(start_path)

    def choose_folder(self, start_path: Optional[Path] = None) -> Optional[Path]:
        """
        Interactively choose a folder, using either a CLI implementation or a subclass's GUI
        implementation (if available, and if the user doesn't explicitly prefer the CLI).

        :param start_path: The path of the folder to start in. If not provided, it will default
            to get_home_folder().
        :return: The path to the chosen folder. If the user downright refuses to choose something,
            then None will be returned, in which case feel free to blow up.
        """
        if self.settings.prefer_cli_file_chooser:
            return self._choose_folder_cli(start_path)
        else:
            return self._choose_folder_gui(start_path)

    def read_text_file(self, path: Path) -> str:
        """
        Read the contents of a file. If the file does not exist, raise FileNotFoundError.

        :param path: The path to the file to read.
        :return: The contents of the file, as a string.
        """
        raise NotImplementedError()

    def open_shell(self, path: Path, environment: Dict[str, str]):
        """
        Open a shell or terminal window, initialized to the provided path. This method should
        return immediately after opening the shell; it should not wait for the shell window to be
        closed.

        This may not be available for all types of hosts.

        :param path: The initial working directory.
        :param environment: Any environmental variables to pass to the shell.
        """
        raise NotImplementedError("Not implemented for this host type")

    def open_folder(self, path: Path):
        """
        Open a GUI view of a folder (e.g. Windows Explorer, Finder, Nautilus, Nemo, PCManFM, etc.)
        at the provided folder path. This method should return immediately after opening the folder
        window; it should not wait for the window to be closed.

        This may not be available for all types of hosts.

        :param path: The path to the folder to open, based on a value returned from the
            choose_folder method.
        """
        raise NotImplementedError("Not implemented for this host type")


class LocalHost(Host):
    """
    Host implementation for a local operating system.

    Note that anything handling filesystem paths will have to be dealt with very carefully, since
    GradeFast paths follow POSIX style (see Path in "models.py"), but the functions in the "os" and
    "os.path" modules expect native OS paths. The implementations of the methods
    "gradefast_path_to_local_path" and "local_path_to_gradefast_path" in LocalHost assume a POSIX
    operating system, so they should be overridden if this is not the case (*cough* Windows).

    The implementations of "gradefast_path_to_local_path" and "local_path_to_gradefast_path" rely
    on the guarantees stated in the Path class.
    """

    class LocalBackgroundCommand(BackgroundCommand):
        def __init__(self, process: subprocess.Popen, command_str: str, path: Path):
            super().__init__()
            self._process: subprocess.Popen = process
            self._done = False
            self._lock = threading.Lock()
            self._command_str = command_str
            self._path = path

        def get_description(self) -> str:
            return "{} (in {})".format(self._command_str, self._path)

        def _we_are_done(self):
            self._done = True
            output: str = self._process.communicate()[0]
            self._add_output(output)
            if self._process.returncode != 0:
                self._set_error("Command had nonzero return code: {}"
                                .format(self._process.returncode))

        def wait(self):
            with self._lock:
                if self._done:
                    return
                try:
                    self._process.communicate()
                except (InterruptedError, KeyboardInterrupt):
                    self._set_error("Command interrupted")
                self._we_are_done()

        def kill(self):
            with self._lock:
                if self._done:
                    return
                self._process.kill()
                self._set_error("Command killed")
                self._we_are_done()

    def _start_process(self, command: str, path: Path, environment: Dict[str, str],
                       **kwargs) -> subprocess.Popen:
        if self.settings.shell_command:
            # Use the user-provided shell
            command = [self.settings.shell_command, command]
        else:
            # Let the platform default shell parse the command
            kwargs["shell"] = True

        try:
            return subprocess.Popen(command, cwd=self.gradefast_path_to_local_path(path).path,
                                    env=environment, universal_newlines=True, stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
        except (NotADirectoryError, FileNotFoundError) as ex:
            raise CommandStartError("File or directory not found: " + str(ex))

    @staticmethod
    def _try_stdin_write(process: subprocess.Popen, stdin: str = None):
        if stdin is not None:
            try:
                process.stdin.write(stdin)
            except BrokenPipeError:
                pass
            except OSError as e:
                if e.errno == errno.EINVAL and process.poll() is not None:
                    # On Windows, stdin.write() fails with EINVAL if the process already exited
                    # before the write
                    pass
                else:
                    raise

    @staticmethod
    def _try_stdin_close(process: subprocess.Popen):
        try:
            process.stdin.close()
        except BrokenPipeError:
            pass
        except OSError as e:
            if e.errno == errno.EINVAL and process.poll() is not None:
                pass
            else:
                raise

    def _stdout_reader_thread(self, process: subprocess.Popen, buffer: io.StringIO,
                              print_output: bool):
        while True:
            data = None
            try:
                data = process.stdout.read(1)
            except BrokenPipeError:
                pass
            if not data:
                break
            buffer.write(data)
            if print_output:
                self.channel._output_nosync(Msg(end="").print(data))
        if print_output:
            self.channel._output_nosync(
                Msg(sep="", end="").print("\n").status("Press Enter to continue..."))

    def run_command(self, command: str, path: Path, environment: Dict[str, str],
                    stdin: Optional[str] = None, print_output: bool = True) -> str:
        process = self._start_process(command, path, environment, bufsize=0)

        # Start a thread to handle the command's output
        output = io.StringIO()
        t = threading.Thread(target=self._stdout_reader_thread,
                             args=(process, output, print_output))
        t.daemon = True
        t.start()

        # If we have predetermined input, write it to stdin
        if stdin is not None:
            self._try_stdin_write(process, stdin)

        # While running the process, we use Channel::blocking_input to block all synchronous I/O
        # (and to get input to send to the process, if necessary)
        with self.channel.blocking_input() as input_func:
            try:
                if print_output:
                    # Until the process is done, read our stdin and write it to the process's stdin
                    while process.poll() is None:
                        stdin = input_func()
                        self._try_stdin_write(process, stdin)
                    self._try_stdin_close(process)
                else:
                    # Wait for the process to complete, without sending it more standard input
                    self._try_stdin_close(process)
                    if process.poll() is None:
                        process.wait()
            except (InterruptedError, KeyboardInterrupt):
                if process.poll() is None:
                    # Stop the process gracefully (with a "SIGTERM")
                    process.terminate()
                    # We won't leave until the process is actually dead
                    while process.poll() is None:
                        try:
                            process.wait()
                        except (InterruptedError, KeyboardInterrupt):
                            if process.poll() is None:
                                # We tried being peaceful; this time, go for the "SIGKILL"
                                process.kill()
            self._try_stdin_close(process)
            t.join()

        if process.returncode != 0:
            raise CommandRunError("Command had nonzero return code: {}".format(process.returncode))
        output.seek(0)
        return output.read()

    def start_background_command(self, command: str, path: Path, environment: Dict[str, str],
                                 stdin: Optional[str] = None) -> BackgroundCommand:
        process = self._start_process(command, path, environment, bufsize=0)
        self._try_stdin_write(process, stdin)
        self._try_stdin_close(process)
        return LocalHost.LocalBackgroundCommand(process, command, path)

    def gradefast_path_to_local_path(self, path: Path) -> LocalPath:
        # Overridden for Windows in LocalWindowsHost
        path_str = path.get_gradefast_path()
        if path_str.startswith("~"):
            path_str = os.path.expanduser(path_str)
        if not path_str.startswith("/"):
            raise ValueError("Invalid path: " + str(path))
        return LocalPath(os.path.normpath(path_str))

    def local_path_to_gradefast_path(self, local_path: LocalPath) -> Path:
        # Overridden for Windows in LocalWindowsHost
        home_dir = os.path.expanduser("~")
        path_str = local_path.path
        if path_str.startswith(home_dir):
            return Path("~" + path_str[len(home_dir):])
        return Path(os.path.normpath(path_str))

    def exists(self, path: Path) -> bool:
        return os.path.exists(self.gradefast_path_to_local_path(path))

    def folder_exists(self, path: Path) -> bool:
        return os.path.isdir(self.gradefast_path_to_local_path(path))

    def move_to_folder(self, path: Path, folder_path: Path):
        local_path = self.gradefast_path_to_local_path(path)
        folder_local_path = self.gradefast_path_to_local_path(folder_path)
        file_local_path = LocalPath(os.path.join(folder_local_path, path.basename()))
        if not os.path.exists(folder_local_path):
            os.mkdir(folder_local_path)
        os.rename(local_path, file_local_path)

    def unzip(self, path: Path, folder_path: Path):
        local_path = self.gradefast_path_to_local_path(path)
        folder_local_path = self.gradefast_path_to_local_path(folder_path)
        if not os.path.exists(folder_local_path):
            os.mkdir(folder_local_path)
        zipfile.ZipFile(local_path.path, "r").extractall(folder_local_path.path)

    def get_home_folder(self) -> Path:
        return self.local_path_to_gradefast_path(LocalPath(os.path.expanduser("~")))

    def list_folder(self, path: Path = None) -> List[Tuple[str, str, bool]]:
        with os.scandir(self.gradefast_path_to_local_path(path)) as it:
            results = []
            for entry in it:
                entry: os.DirEntry = entry
                type = None
                if entry.is_dir():
                    type = "folder"
                elif entry.is_file():
                    type = "file"
                results.append((entry.name, type, entry.is_symlink()))
            return results

    def read_text_file(self, path: Path) -> str:
        with open(self.gradefast_path_to_local_path(path).path) as f:
            return f.read()

    def open_shell(self, path: Path, environment: Dict[str, str]):
        if self.settings.terminal_command:
            local_path = self.gradefast_path_to_local_path(path)
            _open_in_background([self.settings.terminal_command, local_path.path], environment)
        else:
            raise NotImplementedError()


def _open_in_background(args, env=None):
    subprocess.Popen(args, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)


class LocalWindowsHost(LocalHost):
    """
    Extension of LocalHost for Windows.
    """

    def gradefast_path_to_local_path(self, path: Path) -> LocalPath:
        # Overrides LocalHost's POSIX-specific implementation
        path_str = path.get_gradefast_path()
        if path_str.startswith("~"):
            path_str = os.path.expanduser(path_str)
        return LocalPath(os.path.normpath(path_str))

    def local_path_to_gradefast_path(self, local_path: LocalPath) -> Path:
        # Overrides LocalHost's POSIX-specific implementation
        home_path = os.path.expanduser("~")
        local_path_str = local_path.path
        if local_path_str.startswith(home_path):
            local_path_str = "~" + local_path_str[len(home_path):]
        return Path(local_path_str.replace("\\", "/"))

    def _choose_folder_gui(self, start_path: Optional[Path] = None) -> Optional[Path]:
        if start_path and not os.path.isdir(self.gradefast_path_to_local_path(start_path)):
            start_path = None
        if not start_path:
            start_path = self.get_home_folder()

        # TODO: TEST THIS
        # This is a "hacky af" PowerShell script to show a file selection window that allows folder
        # selection while still showing files. Turns out this isn't built in to Windows (well,
        # except for the horribly ugly "folder selection" dialog that's just a glorified treeview).
        # This is based on:
        # https://www.codeproject.com/articles/44914/select-file-or-folder-from-the-same-dialog
        # There's a better solution at http://www.lyquidity.com/devblog/?p=136 (but it's written in
        # C# and uses reflection, so it's beyond my porting-C#-to-PowerShell skillz)
        script = """
            Add-Type -AssemblyName System.Windows.Forms
            $f = new-object Windows.Forms.OpenFileDialog
            $f.Title = "GradeFast"
            $f.InitialDirectory = pwd
            $f.ShowHelp = $true
            $f.Multiselect = $false
            # This needs to be "false" to allow us to put "Folder Selection" in the box
            $f.ValidateNames = $false
            $f.CheckFileExists = $false
            $f.CheckPathExists = $true
            $f.FileName = "Folder Selection."
            [void]$f.ShowDialog()
            $f.FileName
            """
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", "-"],
            cwd=self.gradefast_path_to_local_path(start_path).path,
            universal_newlines=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL)
        local_path_str: str = process.communicate(script)[0]
        if process.returncode == 0:
            if local_path_str.endswith("Folder Selection.") or not os.path.exists(local_path_str):
                local_path_str = os.path.dirname(local_path_str)
            if os.path.isdir(local_path_str):
                return self.local_path_to_gradefast_path(LocalPath(local_path_str))
        return None

    def open_shell(self, path: Path, environment: Dict[str, str]):
        if self.settings.terminal_command:
            super().open_shell(path, environment)
            return

        local_path_str = self.gradefast_path_to_local_path(path).path
        if local_path_str.find('"') != -1:
            # Just get rid of parts with double-quotes
            local_path_str = local_path_str[0:local_path_str.find('"')]
            # Make sure we don't have a dangling bit of folder name on the end
            local_path_str = local_path_str[0:local_path_str.rfind("\\")]
        _open_in_background(["start", "cmd", "/K", 'cd "{}"'.format(local_path_str)],
                            env=environment)

    def open_folder(self, path: Path):
        os.startfile(self.gradefast_path_to_local_path(path).path)


class LocalMacHost(LocalHost):
    """
    Extension of LocalHost for Mac OS X.
    """

    def _choose_folder_gui(self, start_path: Optional[Path] = None) -> Optional[Path]:
        if start_path and not os.path.isdir(self.gradefast_path_to_local_path(start_path)):
            start_path = None

        args = ["osascript", "-"]
        if start_path is None:
            stdin = "return POSIX path of (choose folder)"
        else:
            args += [self.gradefast_path_to_local_path(start_path).path]
            stdin = "return POSIX path of " + \
                    "(choose folder default location POSIX path of item 1 of argv)"
        process = subprocess.Popen(args, universal_newlines=True, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        local_path_str: str = process.communicate(stdin)[0].strip()
        if process.returncode == 0 and local_path_str:
            return self.local_path_to_gradefast_path(LocalPath(local_path_str))
        else:
            return None

    def open_shell(self, path: Path, environment: Dict[str, str]):
        if self.settings.terminal_command:
            super().open_shell(path, environment)
            return

        _open_in_background([
            "open",
            "-a",
            "Terminal",
            self.gradefast_path_to_local_path(path).path
        ], env=environment)

    def open_folder(self, path: Path):
        _open_in_background(["open", self.gradefast_path_to_local_path(path).path])


class LocalLinuxHost(LocalHost):
    """
    Extension of LocalHost for Linux.
    """

    def open_shell(self, path: Path, environment: Dict[str, str]):
        if self.settings.terminal_command:
            super().open_shell(path, environment)
            return

        if shutil.which("exo-open"):
            # Use the system's default terminal emulator
            _open_in_background([
                "exo-open",
                "--launch",
                "TerminalEmulator",
                "--working-directory",
                self.gradefast_path_to_local_path(path).path
            ], env=environment)
        elif shutil.which("gnome-terminal"):
            # We have gnome-terminal
            _open_in_background([
                "gnome-terminal",
                "--working-directory=" + self.gradefast_path_to_local_path(path).path
            ], env=environment)
        elif shutil.which("xfce4-terminal"):
            # We have xfce4-terminal
            _open_in_background([
                "xfce4-terminal",
                "--default-working-directory=" + self.gradefast_path_to_local_path(path).path
            ], env=environment)
        else:
            raise NotImplementedError("No terminal emulator found")

    def open_folder(self, path: Path):
        _open_in_background(["xdg-open", self.gradefast_path_to_local_path(path).path])