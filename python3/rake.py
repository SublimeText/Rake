import sublime
import sublime_plugin
import os
import sys
#import _thread as thread
import threading
import subprocess
import functools
import re
import time


class ProcessListener(object):

    def on_data(self, proc, data):
        pass

    def on_finished(self, proc):
        pass

# Encapsulates subprocess.Popen, forwarding stdout to a supplied
# ProcessListener (on a separate thread)


class AsyncProcess(object):

    def __init__(self, arg_list, env, listener,
                 path="",       # "path" is an option in build systems
                 shell=False):  # "shell" is an options in build systems
        self.listener = listener
        self.killed = False

        self.start_time = time.time()

        # Hide the console window on Windows
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Set temporary PATH to locate executable in arg_list
        if path:
            old_path = os.environ["PATH"]
            # The user decides in the build system whether he wants to append $PATH
            # or tuck it at the front: "$PATH;C:\\new\\path", "C:\\new\\path;$PATH"
            os.environ["PATH"] = os.path.expandvars(path)

        proc_env = os.environ.copy()
        proc_env.update(env)
        for k, v in proc_env.items():
            proc_env[k] = os.path.expandvars(v)

        self.proc = subprocess.Popen(arg_list, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     startupinfo=startupinfo, env=proc_env,
                                     shell=shell)

        if path:
            os.environ["PATH"] = old_path

        if self.proc.stdout:
            threading.Thread(target=self.read_stdout).start()

        if self.proc.stderr:
            threading.Thread(self.read_stderr).start()

    def kill(self):
        if not self.killed:
            self.killed = True
            if sys.platform == "win32":
                # terminate would not kill process opened by the shell cmd.exe, it will only kill
                # cmd.exe leaving the child running
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.Popen("taskkill /PID " + str(self.proc.pid), startupinfo=startupinfo)
            else:
                self.proc.terminate()
            self.listener = None

    def poll(self):
        return self.proc.poll() is None

    def exit_code(self):
        return self.proc.poll()

    def read_stdout(self):
        while True:
            data = os.read(self.proc.stdout.fileno(), 2**15)

            if len(data) > 0:
                if self.listener:
                    self.listener.on_data(self, data)
            else:
                self.proc.stdout.close()
                if self.listener:
                    self.listener.on_finished(self)
                break

    def read_stderr(self):
        while True:
            data = os.read(self.proc.stderr.fileno(), 2**15)
            if len(data) > 0:
                if self.listener:
                    self.listener.on_data(self, data)
            else:
                self.proc.stderr.close()
                break


class RakeSetSelectionToStartCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(0, 0))


class RakeCommand(sublime_plugin.WindowCommand, ProcessListener):

    def run(self, tasks=[], options=[], prefix=[],
            file_regex="^(...*?):([0-9]*):?([0-9]*)", line_regex="",
            working_dir="",
            encoding="utf-8", env={}, quiet=False, kill=False,
            **kwargs):  # Catches "path" and "shell"

        if kill:
            if self.proc:
                self.proc.kill()
                self.proc = None
                self.append_data(None, "[Cancelled]")
            return

        if not hasattr(self, 'output_view'):
            # Try not to call get_output_panel until the regexes are assigned
            self.output_view = self.window.create_output_panel("exec")
        # Default to the current files directory if no working directory was given
        if (working_dir == "" and self.window.active_view()
                        and self.window.active_view().file_name()):
            # working_dir = os.path.dirname(self.window.active_view().file_name())
            working_dir = os.path.dirname(self.window.active_view().file_name())

        self.output_view.settings().set("result_file_regex", file_regex)
        self.output_view.settings().set("result_line_regex", line_regex)
        self.output_view.settings().set("result_base_dir", working_dir)

        current_file = self.window.active_view().file_name()
        current_file_name = os.path.basename(current_file)

        flattened_tasks = ""

        for task in tasks:
            task = task.replace("$file_name", current_file_name)
            task = task.replace("$file", current_file)
            flattened_tasks += task + " "
        flattened_tasks = re.sub(r" $", "", flattened_tasks)

        # Call create_output_panel a second time after assigning the above
        # settings, so that it'll be picked up as a result buffer
        self.window.create_output_panel("exec")
        self.encoding = encoding
        self.quiet = quiet

        self.proc = None

        # Build up the command line
        cmd = []
        cmd += prefix
        if os.name == "nt":
            cmd += ["rake.bat"]
        else:
            cmd += ["rake"]
        cmd += [flattened_tasks] + options

        self.append_data(None, "> " + " ".join(cmd) + "\n")
        self.window.run_command("show_panel", {"panel": "output.exec"})

        merged_env = env.copy()
        if self.window.active_view():
            user_env = self.window.active_view().settings().get('build_env')
            if user_env:
                merged_env.update(user_env)

        # Change to the working dir, rather than spawning the process with it,
        # so that emitted working dir relative path names make sense
        if working_dir != "":
            os.chdir(working_dir)

        self.debug_text = ""
        self.debug_text += "[dir: " + str(os.getcwd()) + "]\n"

        if "PATH" in merged_env:
            self.debug_text += "[path: " + str(merged_env["PATH"]) + "]"
        else:
            self.debug_text += "[path: " + str(os.environ["PATH"]) + "]"

        err_type = OSError

        if os.name == "nt":
            err_type = WindowsError
        try:
            # Forward kwargs to AsyncProcess
            self.proc = AsyncProcess(cmd, merged_env, self, **kwargs)
        except err_type as e:
            self.append_data(None, str(e) + "\n")
            if not self.quiet:
                self.append_data(None, "[Finished]")

    def is_enabled(self, kill=False):
        if kill:
            return hasattr(self, 'proc') and self.proc and self.proc.poll()
        else:
            return True

    def append_data(self, proc, data):
        if proc != self.proc:
            # a second call to exec has been made before the first one
            # finished, ignore it instead of intermingling the output.
            if proc:
                proc.kill()
            return

        try:
            if type(data) is str:
                text = data
            elif type(data) is type(b"test"):
                text = data.decode(self.encoding)
        except Exception as e:
            text = "[Decode error - output not " + self.encoding + "]"
            text += "\n Error: " + str(e) + "\n"
            proc = None

        # Normalize newlines, Sublime Text always uses a single \n separator
        # in memory.
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        self.output_view.run_command('append', {'characters': text, 'force': True, 'scroll_to_end': True})

    def append_string(self, proc, text):
        self.append_data(proc, text.encode(self.encoding))

    def finish(self, proc):
        if not self.quiet:
            elapsed = time.time() - proc.start_time
            exit_code = proc.exit_code()
            if exit_code == 0 or exit_code is None:
                self.append_string(proc,
                                   ("[Finished in %.1fs]" % (elapsed)))
            else:
                self.append_string(proc, ("[Finished in %.1fs with exit code %d]\n"
                                   % (elapsed, exit_code)))
                self.append_string(proc, self.debug_text)

        if proc != self.proc:
            return

        errs = self.output_view.find_all_results()
        if len(errs) == 0:
            sublime.status_message("Build finished")
        else:
            sublime.status_message(("Build finished with %d errors") % len(errs))

        # Set the selection to the start, so that next_result will work as expected
        self.output_view.run_command("rake_set_selection_to_start")

    def on_data(self, proc, data):
        sublime.set_timeout(functools.partial(self.append_data, proc, data), 0)

    def on_finished(self, proc):
        sublime.set_timeout(functools.partial(self.finish, proc), 0)
