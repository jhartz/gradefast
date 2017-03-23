"""
Handles interaction between the grader and the operating system.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import errno
import io
import os
import posixpath
import subprocess
import threading

from typing import Dict, List, Optional, Tuple

from .graderio import GraderIO, Msg


class BackgroundCommand:
    """
    A command that may or may not have finished running.
    """
    def __init__(self):
        self._output = io.StringIO()
        self._output_lock = threading.Lock()
        self._error: Optional[str] = None

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


class GraderOS:
    """
    Abstract class for interactions between the grader and the operating system.
    """

    def __init__(self, grader_io: GraderIO, shell_command: Optional[str] = None,
                 terminal_command: Optional[str] = None):
        self._io = grader_io
        self.shell_command = shell_command
        self.terminal_command = terminal_command

    def run_command(self, command: str, path: str, environment: Dict[str, str],
                    stdin: Optional[str] = None, print_output: bool = True) -> str:
        """
        Execute a command.

        If print_output is true, the output of the command will be written using self._io.print
        as it comes in. Regardless of print_output, the output of the command will also be
        returned after the command has finished.

        If input is needed and "stdin" is None, then self._io.input will be used.

        If there is an error when starting the command (e.g. command not found), a
        CommandStartError will be raised. If there is an error running the command (e.g. the
        command exited with a nonzero return code), a CommandRunError will be raised.

        :param command: The command to run.
        :param path: The working directory for the command.
        :param environment: Any environmental variables for this command.
        :param stdin: Any input to use as stdin. If not provided, self._io.input will be used.
        :param print_output: Whether to print the output using self._io.print as it comes in.
        """
        raise NotImplementedError()

    def start_background_command(self, command: str, path: str, environment: Dict[str, str],
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

    def get_home_folder(self) -> str:
        """
        Get the absolute path to a "home folder", or equivalent.
        """
        raise NotImplementedError()

    def list_folder(self, path: str) -> List[Tuple[str, str, bool]]:
        """
        Get the contents of a folder. If the folder cannot be found, raise a FileNotFoundError with
        a detailed error message.

        :param path: The absolute path of the folder to list. This will be based on values
            returned from the get_home_folder, list_folder, and choose_folder methods.
        :return: A list of tuples of the form (name, type, is_link). The type should be one of:
            "file", "folder", or some other string for a special or inaccessible file. If the type
            is unknown, use None.
        """
        raise NotImplementedError()

    def choose_folder(self, base_folder: Optional[str] = None) -> Optional[str]:
        """
        Interactively choose a folder. This should be overridden by subclasses if it is possible
        to show the user a GUI file chooser window. Otherwise, the default implementation makes use
        of the other GraderOS methods and GraderIO methods to prompt the user for a directory.

        :param base_folder: The absolute path of the folder to start in. If provided, this will be
            based on a previous return value from the same choose_folder method. If not provided,
            it will default to get_home_folder().
        :return: The absolute path to the chosen folder. This must start with a forward slash ("/")
            and it must use forward slashes (NOT backslashes, colons, etc.) to separate parts of
            the path. (Sorry, Windows.) If the user downright refuses to choose something, then
            None will be returned, in which case feel free to blow up.
        """
        if base_folder is not None:
            try:
                self.list_folder(base_folder)
            except FileNotFoundError:
                self._io.output(Msg().error("Base folder not found:").print(base_folder))
                base_folder = None
        if base_folder is None:
            base_folder = self.get_home_folder()

        old_folder = None
        folder = base_folder
        while True:
            try:
                folder_listing = self.list_folder(folder)
            except FileNotFoundError:
                self._io.output(Msg().error("Directory not found:").print(folder))
                if old_folder is None:
                    # list_dir must have failed on the results from get_home_folder()
                    # Let's just give up :(
                    return None
                else:
                    # Go back to a known existing folder
                    folder = old_folder
                    continue

            files = []
            folders = []
            other = []
            for name, type, is_link in folder_listing:
                if type == "file":
                    files.append((name, is_link))
                elif type == "folder":
                    folders.append((name, is_link))
                else:
                    other.append((name, type, is_link))

            listing = Msg(sep="")
            listing.print("{}", posixpath.relpath(folder, base_folder)).status(": ")
            listing.print("..")
            for name, is_link in sorted(folders, key=lambda f: f[0]):
                listing.status(", ")
                listing.bright("{}/", name)
                if is_link:
                    listing.print(" (link)")
            for name, is_link in sorted(files, key=lambda f: f[0]):
                listing.status(", ")
                listing.print("{}", name)
                if is_link:
                    listing.print(" (link)")
            for name, type, is_link in sorted(other, key=lambda f: f[0]):
                listing.status(", ")
                listing.print("{}", name)
                if is_link:
                    listing.print(" (link")
                    if type is not None:
                        listing.print(" to {}", type)
                    listing.print(")")
                elif type is not None:
                    listing.print(" ({})", type)
            self._io.output(listing)

            choice = self._io.input("Choose a folder (or \"Enter\" if you're satisfied with this "
                                    "one):", [name for name, is_link in folders]).strip()
            if not choice:
                break
            old_folder = folder
            folder = posixpath.normpath(folder + "/" + choice)

        return folder

    def open_shell(self, path: str, environment: Dict[str, str]):
        """
        Open a shell or terminal window, initialized to the provided path. This method should
        return immediately after opening the shell; it should not wait for the shell window to be
        closed.

        This may not be available on all platforms.

        :param path: The initial working directory.
        :param environment: Any environmental variables to pass to the shell.
        """
        raise NotImplementedError("Not implemented for this OS")

    def open_folder(self, path: str):
        """
        Open a GUI view of a folder (e.g. Windows Explorer, Finder, Nautilus, Nemo, PCManFM, etc.)
        at the provided folder path. This method should return immediately after opening the folder
        window; it should not wait for the window to be closed.

        This may not be available on all platforms.

        :param path: The absolute path to the folder to open, based on a value returned from the
            choose_folder method.
        """
        raise NotImplementedError("Not implemented for this OS")


class LocalOS(GraderOS):
    """
    GraderOS implementation for a local operating system.
    """

    class LocalBackgroundCommand(BackgroundCommand):
        def __init__(self, process: subprocess.Popen):
            super().__init__()
            self._process: subprocess.Popen = process
            self._done = False
            self._lock = threading.Lock()

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
                    stdout, _ = self._process.communicate()
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

    def _start_process(self, command: str, path: str, environment: Dict[str, str],
                       **kwargs) -> subprocess.Popen:
        if self.shell_command is None:
            # Let the platform default shell parse the command
            kwargs["shell"] = True
        else:
            # Use the user-provided shell
            command = [command if arg is None else arg for arg in self.shell_command]

        try:
            return subprocess.Popen(command, cwd=path, env=environment, universal_newlines=True,
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, **kwargs)
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
                self._io.print(data)
        if print_output:
            self._io.print("\n")
            self._io.status("Press Enter to continue...")

    def run_command(self, command: str, path: str, environment: Dict[str, str],
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

        try:
            if print_output:
                # Until the process is done, read our stdin and write it to the process's stdin
                while process.poll() is None:
                    stdin = self._io.input()
                    self._try_stdin_write(process, stdin)
                self._try_stdin_close(process)
            else:
                # Wait for the process to complete, without sending it more standard input
                self._try_stdin_close(process)
                if process.poll() is None:
                    process.wait()
        except (InterruptedError, KeyboardInterrupt):
            self._try_stdin_close(process)
            if process.poll() is None:
                process.kill()
                raise CommandRunError("Command interrupted")

        t.join()
        if process.returncode != 0:
            raise CommandRunError("Command had nonzero return code: {}".format(process.returncode))
        output.seek(0)
        return output.read()

    def start_background_command(self, command: str, path: str, environment: Dict[str, str],
                                 stdin: Optional[str] = None) -> BackgroundCommand:
        process = self._start_process(command, path, environment, bufsize=0)
        self._try_stdin_write(process, stdin)
        self._try_stdin_close(process)
        return LocalOS.LocalBackgroundCommand(process)

    def get_home_folder(self) -> str:
        return os.path.expanduser("~")

    def list_folder(self, path: Optional[str] = None) -> List[Tuple[str, str, bool]]:
        with os.scandir(path) as it:
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


def _open_in_background(args, env=None):
    subprocess.Popen(args, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)


class LocalWindowsOS(LocalOS):
    """
    Extension of LocalOS for Windows.
    """

    def choose_folder(self, base_folder: Optional[str] = None) -> Optional[str]:
        if base_folder is not None and not os.path.isdir(base_folder):
            base_folder = None

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
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", "-"], cwd=base_folder,
            universal_newlines=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL)
        directory: str = process.communicate(script)[0]
        if process.returncode == 0:
            if directory.endswith("Folder Selection.") or not os.path.exists(directory):
                directory = os.path.dirname(directory)
            if os.path.isdir(directory):
                return "/" + directory.replace("\\", "/")
        return None

    def open_shell(self, path: str, environment: Dict[str, str]):
        # Replace forward slashes with backslashes
        path = os.path.normpath(path)
        if path.find('"') != -1:
            # Just get rid of parts with double-quotes
            path = path[0:path.find('"')]
            # Make sure we don't have a dangling bit of folder name on the end
            path = path[0:path.rfind("\\")]
        _open_in_background(["start", "cmd", "/K", 'cd "{}"'.format(path)], env=environment)

    def open_folder(self, path: str):
        os.startfile(path)


class LocalMacOS(LocalOS):
    """
    Extension of LocalOS for Mac OS X.
    """

    def choose_folder(self, base_folder: Optional[str] = None) -> Optional[str]:
        if base_folder is not None and not os.path.isdir(base_folder):
            base_folder = None

        # TODO: Test This
        args = ["osascript", "-"]
        if base_folder is None:
            stdin = "return POSIX path of (choose folder)"
        else:
            args += [base_folder]
            stdin = "return POSIX path of " + \
                    "(choose folder default location POSIX path of item 1 of argv)"
        process = subprocess.Popen(args, universal_newlines=True, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        directory: str = process.communicate(stdin)[0]
        if process.returncode == 0:
            return directory
        else:
            return None

    def open_shell(self, path: str, environment: Dict[str, str]):
        _open_in_background([
            "open",
            "-a",
            "Terminal",
            path
        ], env=environment)

    def open_folder(self, path: str):
        _open_in_background(["open", path])


class LocalLinuxOS(LocalOS):
    """
    Extension of LocalOS for Linux.
    """

    @staticmethod
    def _cmd_exists(cmd: str) -> bool:
        return subprocess.call(["which", cmd], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL) == 0

    def open_shell(self, path: str, environment: Dict[str, str]):
        if self._cmd_exists("exo-open"):
            # Use the system's default terminal emulator
            _open_in_background([
                "exo-open",
                "--launch",
                "TerminalEmulator",
                "--working-directory",
                path
            ], env=environment)
        elif self._cmd_exists("gnome-terminal"):
            # We have gnome-terminal
            _open_in_background([
                "gnome-terminal",
                "--working-directory=" + path
            ], env=environment)
        elif self._cmd_exists("xfce4-terminal"):
            # We have xfce4-terminal
            _open_in_background([
                "xfce4-terminal",
                "--default-working-directory=" + path
            ], env=environment)
        else:
            raise NotImplementedError("No terminal emulator found")

    def open_folder(self, path: str):
        _open_in_background(["xdg-open", path])
