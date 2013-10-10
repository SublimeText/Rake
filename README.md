Description
===========
[Rake](http://rake.rubyforge.org/) is a simple ruby build program with capabilities similar to make. This package adds support to Sublime Text 3 for developing Ceedling applications.

Rake has the following features:
* Rakefiles (rake‘s version of Makefiles) are completely defined in standard Ruby syntax. No XML files to edit. No quirky Makefile syntax to worry about (is that a tab or a space?)
* Users can specify tasks with prerequisites.
* Rake supports rule patterns to synthesize implicit tasks.
* Flexible FileLists that act like arrays but know about manipulating file names and paths.
* A library of prepackaged tasks to make building rakefiles easier.

Package Installation
====================
Bring up a command line in a folder where you keep git projects, and execute the following:

> git clone https://github.com/SublimeText/Rake.git

> cd Rake

> git checkout sublime_text_3

Now use any `zip`-compatible tool to compress the folder `Rake` into a zip file (the built-in Windows compress utility and the Mac archive utility both work for this). Change the name of the file, including extension, to `Rake.sublime-package`. You may need to change settings in Windows to allow changing extensions. Move or copy `Rake.sublime-package` to your Sublime user `Installed Packages` folder.

When you launch Sublime Text 3, it will pick up the contents of this package so that you can consume the goodness that it provides.

Features
========
* Adds a Rake.sublime-build that will simply execute 'rake' with no arguments (default task)
* The rake.py Sublime Text 3 plugin adds a 'rake' Sublime Text command that can be used in any custom keybindings and/or menu items.
	* Automatically calls the proper flavor of rake per OS (e.g. 'rake' on OSX and Linux; 'rake.bat' on Windows)
	* The 'rake' command is based off of the 'exec' command, but takes different parameters
		* e.g. the "cmd" parameter is replaced by:
			* "prefix" - text/parameters to be tacked on prior to 'rake' on the command line (e.g. ["bundle", "exec"])
			* "tasks" - array of tasks to be executed in order (e.g. ["clobber", "test:all"])
			* "options" - array of extra parameters to be appended after the tasks (e.g ["--trace"])
		* Most of the other parameters supported by the 'exec' command are supported as well:
			* "file_regex"
			* "line_regex"
			* "working_dir"
			* "env"

Planned Features
================
* Dynamically create entries is the Command Pallette for described rake tasks

Example Usage
-------------
Key Binding:
{ "keys": ["f4"], "command": "rake", "args": {"tasks": ["clobber", test:all"] } }

Result: (pressing F4 wil execute the following):
rake clobber test:all
