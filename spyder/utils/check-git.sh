#!/usr/bin/env bash

# This tests if git is properly installed in macOS computers.
# See docksal/docksal#1003 for the explanation.
xcode_tools_dir=$(xcode-select -p 2>/dev/null) && ls ${xcode_tools_dir}/usr/bin/git
