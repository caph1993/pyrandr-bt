'''
PyRandr-BT - Manage your screen brightness and temperature using randr 

Author: Carlos Pinzón «caph1993@gmail.com»
Date: 2021


Documentation is scarce. These were my sources:
    Ref 1 (stc.c)
        https://flak.tedunangst.com/post/sct-set-color-temperature
    Ref 2 (Xlib example).
        https://stackoverflow.com/questions/8705814
    For self exploring:
        d = dpy.Display()
        print(d.display_extension_methods.keys())
'''

# sudo apt install python3-xlib

from Xlib import display as dpy
from Xlib.ext import randr
import json, time, sys

# Randr functions


def get_outputs(d: dpy.Display):  # based on refs 1 and 2
    global info
    screen = d.get_default_screen()
    info = d.screen(screen)
    window = info.root
    res = randr.get_screen_resources(window)
    outputs = {}
    for output in res.outputs:
        params = d.xrandr_get_output_info(output, res.config_timestamp)
        if params.crtc:
            outputs[params.name] = get_output(d, params.crtc)
    return outputs


MAX = 65535.0  # grabbed from ref 1


def get_output(d: dpy.Display, crtc):
    cg = d.xrandr_get_crtc_gamma(crtc)
    # Ugly fix: after october 2021, cg.blue and cg.green are empty :(
    # probably a bug in the Xlib library for Python
    print(cg.red[-10:])
    print(cg.blue[-10:])
    print(cg.green[-10:])
    alt = 1.0
    alt = raw_red = cg.red[-1] / MAX if cg.red else alt
    alt = raw_blue = cg.blue[-1] / MAX if cg.blue else alt
    alt = raw_green = cg.green[-1] / MAX if cg.green else alt
    gamma = (
        round(raw_red, 3),
        round(raw_green, 3),
        round(raw_blue, 3),
    )
    return dict(crtc=crtc, gamma=gamma)


def ugly_randr_patch(d):
    # Ugly fix: after october 2021, the red, blue and green arguments where removed
    # it is a bug actually, because if they are not provided, the initializer of
    # SetCrtcGamma will complain

    from Xlib.ext.randr import SetCrtcGamma, extname

    def patched_set_crtc_gamma(self, crtc, size, **kwargs):
        return SetCrtcGamma(display=self.display,
                            opcode=self.display.get_extension_major(extname),
                            crtc=crtc, size=size, **kwargs)

    del d.display_extension_methods['xrandr_set_crtc_gamma']
    d.extension_add_method('display', 'xrandr_set_crtc_gamma',
                           patched_set_crtc_gamma)
    return


def set_gamma(d: dpy.Display, output, gamma):
    crtc = output['crtc']
    n = d.xrandr_get_crtc_gamma_size(crtc).size
    data = [[int(MAX * i * v / (n - 1)) for i in range(n)] for v in gamma]
    rgb = {'red': data[0], 'green': data[1], 'blue': data[2]}
    try:
        d.xrandr_set_crtc_gamma(crtc, n, **rgb)
        use_patch = False
    except:
        use_patch = True
    if use_patch:
        ugly_randr_patch(d)
        d.xrandr_set_crtc_gamma(crtc, n, **rgb)
    output.update(**get_output(d, crtc))
    return


# RGB vs brightness-temperature functions

RGB = [
    [1.000, 0.323, 0.000],
    [1.000, 0.423, 0.086],
    [1.000, 0.543, 0.166],
    [1.000, 0.643, 0.288],
    [1.000, 0.719, 0.428],
    [1.000, 0.779, 0.546],
    [1.000, 0.828, 0.648],
    [1.000, 0.868, 0.736],
    [1.000, 0.901, 0.814],
    [1.000, 0.938, 0.881],
    [1.000, 0.971, 0.943],
    [1.000, 1.000, 1.000],
]


def bt_to_rgb(brightness, temperature):
    n = len(RGB)
    i = min(int(temperature * (n - 1)), n - 2)
    d = temperature * (n - 1) - i
    rgb = [RGB[i][c] * (1 - d) + RGB[i + 1][c] * d for c in range(3)]
    rgb = [round(v * brightness, 3) for v in rgb]
    return rgb


def rgb_to_bt(red, green, blue):
    rgb = [red, green, blue]
    b = max(max(rgb), 1e-5)
    rgb = [v / b for v in rgb]

    def dist2(t):
        rgbt = bt_to_rgb(1, t)
        return sum((b - a)**2 for a, b in zip(rgb, rgbt))

    tlo, thi, n = 0, 1, 10
    for repeat in range(3):
        trange = [tlo + (thi - tlo) * i / n for i in range(n + 1)]
        tlo, thi = sorted(sorted(trange, key=dist2)[:2])
    b = round(b, 3)
    t = round((tlo + thi) / 2, 3)
    return b, t


# User functions
VERSION = 'v1.0.0'
USAGE = f'PyRandr-BT {VERSION}\n' + """
Usage:
    d - demo:
        run a small demo of different combinations
        of brightnesses and temperatures.
        
    b - brightness [+num | -num | num] :
        Increase, decrease or set software brightness.
        100 is the maximum and the default.
        50 is comfortable.
        0 is the completely dark. Use responsibly.
    
    t - temperature [+num | -num | num] :
        Increase, decrease or set software temperature.
        100 is the maximum and the default.
        50 is comfortable and redish/yellowish.
        0 is very redish.
    
    c - combined [+num | -num | num] :
        applies the same change to brightness and temperature
    
    l - list:
        list all available screens and their current values.
        JSON format is used for software compatibility.
    
    s - screen [screen_name]:
        Apply the effects only to a specific screen.
        All available screens are affected if unspecified.
    
    h - help:
        print this message
    
    v - version:
        print version
    

Examples tl;dr:
    python3 pyrandr-bt.py --list
    python3 pyrandr-bt.py --demo
    python3 pyrandr-bt.py --temperature -10
    python3 pyrandr-bt.py --brightness -5 --temperature +10 --screen eDP-1
    python3 pyrandr-bt.py -t 50 -b -10 -l
    python3 pyrandr-bt.py -c +10
""".strip()


def get_bts(d: dpy.Display, name):
    outs = get_outputs(d)
    if name is None:
        outs = outs.values()
    else:
        outs = [v for k, v in outs.items() if k == name]
        assert outs, f'Screen "{name}" not found'
    return [(out, rgb_to_bt(*out['gamma'])) for out in outs]


def short_if(value, if_none):
    return if_none if value is None else value


def user_modify_bt(brightness=None, temperature=None, inc_brightness=None,
                   inc_temperature=None, name=None):
    d = dpy.Display()
    for out, (b, t) in get_bts(d, name):
        b = short_if(brightness, b * 100) / 100
        t = short_if(temperature, t * 100) / 100
        b += short_if(inc_brightness, 0) / 100
        t += short_if(inc_temperature, 0) / 100
        b = max(0, min(1, b))
        t = max(0, min(1, t))
        set_gamma(d, out, bt_to_rgb(b, t))
    return


def user_list():
    d = dpy.Display()
    outs = get_outputs(d)
    for out in outs.values():
        b, t = rgb_to_bt(*out['gamma'])
        out['brightness'] = b
        out['temperature'] = t
    return print(json.dumps(outs, indent='  '))


def user_demo():
    print('Running demo...')
    for db, dt in [(20, 20), (-10, 0), (0, -12), (10, 0), (0, 12)]:
        for i in range(5):
            start = time.time()
            user_modify_bt(inc_brightness=db, inc_temperature=dt)
            time.sleep(max(0, 0.05 - (time.time() - start)))
    return


def parse_num(s):
    sign = int(s.startswith('+')) - int(s.startswith('-'))
    value = float(s[abs(sign):])
    return (value, None) if sign == 0 else (None, sign * value)


def run(args):
    a = d = l = b = ib = t = it = name = None
    try:
        assert args, 'No arguments provided'
        args_iter = iter(args)
        for a in args_iter:
            if a == '--list' or a == '-l':
                l = True
            elif a == '--demo' or a == '-d':
                d = True
            elif a == '--brightness' or a == '-b':
                b, ib = parse_num(next(args_iter))
            elif a == '--temperature' or a == '-t':
                t, it = parse_num(next(args_iter))
            elif a == '--combined' or a == '-c':
                b, ib = t, it = parse_num(next(args_iter))
            elif a == '--screen' or a == '-s':
                name = next(args_iter)
            elif a == '--help' or a == '-h':
                return print(USAGE)
            elif a == '--version' or a == '-v':
                return print(VERSION)
            else:
                raise Exception(f'argument {a} not understood')
    except Exception as e:
        print(USAGE)
        print('------\nError parsing arguments')
        if isinstance(e, StopIteration):
            print(f'Expected argument after {a}')
        else:
            print(e)
        return
    if d:
        user_demo()
    if any(x != None for x in [b, ib, t, it]):
        user_modify_bt(b, t, ib, it, name)
    if l:
        user_list()
    return


if __name__ == '__main__':
    run(sys.argv[1:])
