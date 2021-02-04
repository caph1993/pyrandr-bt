# PyRandr-BT

Manage your screen brightness and temperature using randr. **(for linux systems)**

This script lets you modify the 'software' brightness and temperature manually from the command line (or a global shortcut).

For the 'hardware' brightness, also called backlight, check out `xbacklight`.

## Why?

 - We spend many hours on the screen.
 - Screens are too bright, even on 1% backlight.
 - `xrandr` supports brightness but not temperature (the gamma function is terrible)
 - `redshift` is too complex for such a simple problem. It does support temperature and brightness, but it does not let you read current values, and it has tons of dependencies and uses your location by default.
 - No other open source software is available.

## How to use?

Install `python3-xlib`, copy the script `pyrandr-bt.py` and run it with `python3 pyrandr-bt.py`. You will see the available commands.

The `-c` (combined) function makes it simple to make the screen

 - 'darker and less blue' (`-c -5`), or
 - 'lighter and more blue' (`-c +5`).

Assign them to some global hotkeys for the best experience.

## Video

![Showcase video](video.webp)

I wished I could record the screen from the screen recorder, but screen recorders can't see the screen filters that are applied.


