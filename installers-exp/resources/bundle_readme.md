Welcome to the napari installation contents
-------------------------------------------

This is the base installation of napari, a fast n-dimensional image viewer written in Python.

## How do I run napari?

In most cases, you would run it through the platform-specific shortcut we created for your
convenience. In other words, _not_ through this directory! You should be able to see a
`napari (x.y.z)` menu item, where `x.y.z` is the installed version.

* Linux: check your desktop launcher.
* MacOS: check `~/Applications` or the Launchpad.
* Windows: check the Start Menu or the Desktop.

We generally recommend using the shortcut because it will pre-activate the `conda` environment for
you! That said, you can also execute the `napari` executable directly from these locations:

* Linux and macOS: find it under `bin`, next to this file.
* Windows: navigate to `Scripts`, next to this file.

In unmodified installations, this _should_ be enough to launch `napari`, but sometimes you will
need to activate the `conda` environment to ensure all dependencies are importable.

## What does `conda` have to do with `napari`?

The `napari` installer uses `conda` packages to bundle all its dependencies (Python, qt, etc).
This directory is actually a full `conda` installation! If you have used `conda` before, this
is equivalent to what you usually call the `base` environment.

## Can I modify the `napari` installation?

Yes. In practice, you can consider it a `conda` environment. You can even activate it as usual,
provided you specify the full path to the location, instead of the _name_.

```
# macOS
$ conda activate ~/Library/napari-x.y.z
# Linux
$ conda activate ~/.local/napari-x.y.z
# Windows
$ conda activate %LOCALAPPDATA%/napari-x.y.z
```

Then you will be able to run `conda` and `pip` as usual. That said, we advise against this advanced
manipulation. It can render `napari` unusable if not done carefully! You might need to reinstall it
in that case.

## What is `_conda.exe`?

This executable is a full `conda` installation, condensed in a single file. It allows us to handle
the installation in a more robust way. It also provides a way to restore destructive changes without
reinstalling anything. Again, consider this an advanced tool only meant for expert debugging.

## More information

Check our online documentation at https://napari.org/
