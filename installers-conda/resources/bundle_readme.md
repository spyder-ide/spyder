Welcome to the Spyder installation contents
-------------------------------------------

This is the base installation of Spyder, the Scientific Python Development Environment.

## How do I run Spyder?

In most cases, you would run it through the platform-specific shortcut we created for your
convenience. In other words, _not_ through this directory!

* Linux: Check your desktop launcher.
* MacOS: Check `~/Applications` or the Launchpad.
* Windows: Check the Start Menu or the Desktop.

We generally recommend using the shortcut because it will pre-activate the `conda` environment for
you! That said, you can also execute the `spyder` executable directly from these locations:

* Linux and macOS: find it under `bin`, next to this file.
* Windows: navigate to `Scripts`, next to this file.

In unmodified installations, this _should_ be enough to launch `spyder`, but sometimes you will
need to activate the `conda` environment to ensure all dependencies are importable.

## What does `conda` have to do with `spyder`?

The Spyder installer uses `conda` packages to bundle all its dependencies (Python, Qt, etc).
This directory is actually a full `conda` installation! If you have used `conda` before, this
is equivalent to what you usually call the `base` environment.

## Can I modify the `spyder` installation?

Yes, but it is not recommended (see below). In practice, you can consider it a `conda` environment. You can even activate it as usual,
provided you specify the full path to the location, instead of the _name_.

```
# macOS
$ conda activate ~/Library/spyder-x.y.z
# Linux
$ conda activate ~/.local/spyder-x.y.z
# Windows
$ conda activate %LOCALAPPDATA%/spyder-x.y.z
```

Then you will be able to run `conda` and `pip` as usual. That said, we advise against this advanced
manipulation. It can render `spyder` unusable if not done carefully! You might need to reinstall it
in that case.

## What is `_conda.exe`?

This executable is a full `conda` installation, condensed in a single file. It allows us to handle
the installation in a more robust way. It also provides a way to restore destructive changes without
reinstalling anything. Again, consider this an advanced tool only meant for expert debugging.

## More information

Check our online documentation at https://www.spyder-ide.org/
