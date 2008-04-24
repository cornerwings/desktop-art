import gtk, gconf

gconf_plugin_path = '/apps/rhythmbox/plugins/desktop-art/'

defaults = {'cover_roundness'      : 0.3,
            'background_color'     : '#0000000000004ccc',
            'text_color'           : '#ffffffffffffb332',
            'text_shadow_color'    : '#000000000000b332',
            'draw_reflection'      : True,
            'window_x'             : 50,
            'window_y'             : gtk.gdk.screen_height() - 190 - 40,
            'window_w'             : gtk.gdk.screen_width() - 100,
            'window_h'             : 190,
            'text_position'        : 'se',
            'blur'                 : 1,
            'reflection_height'    : 0.4,
            'reflection_intensity' : 0.4,
            'hover_size'           : 0.7,
            'roundness'            : 0.3,
            'border'               : 0.06}
            
def gconf_path(key):
    return '%s%s' % (gconf_plugin_path, key)

gc = gconf.client_get_default()

for key, val in defaults.items():
    path = gconf_path(key)
    if gc.get_without_default(path) == None:
        if isinstance(val, bool):
            gc.set_bool(path, val)
        elif isinstance(val, int):
            gc.set_int(path, val)
        elif isinstance(val, float):
            gc.set_float(path, val)
        elif isinstance(val, str):
            gc.set_string(path, val)
        else:
            print 'Datatype %s is not supported' % type(val)
