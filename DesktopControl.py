# -*- coding: utf-8 -*-
#
# This file is part of the Rhythmbox Desktop Art plug-in
#
# Copyright © 2008 Mathias Nedrebø < mathias at nedrebo dot org >
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from __future__ import division

import sys
import gobject
import gtk, cairo, pango
import gconf
import rsvg
from roundedrec import roundedrec
from ConfigDialog import ConfigDialog

# CONSTANTS

UNKNOWN_COVER = -1
POSITION_NW = 'nw'
POSITION_NE = 'ne'
POSITION_SW = 'sw'
POSITION_SE = 'se'

gconf_plugin_path = '/apps/rhythmbox/plugins/desktop-art'

def get_icon_path(theme, name, size):
    icon = theme.lookup_icon(name, size, gtk.ICON_LOOKUP_FORCE_SVG)
    return (icon and icon.get_filename())

def gconf_path(key):
    return '%s/%s' % (gconf_plugin_path, key)

def read_gconf_values(values, keys):
    gc = gconf.client_get_default()
    for key in keys:
        val = gc.get_without_default(gconf_path(key))
        if val.type == gconf.VALUE_FLOAT:
            values[key] = val.get_float()
        elif val.type == gconf.VALUE_INT:
            values[key] = val.get_int()
        elif val.type == gconf.VALUE_STRING:
            values[key] = val.get_string()
        elif val.type == gconf.VALUE_BOOL:
            values[key] = val.get_bool()
        # Parse color strings
        if 'color' in key:
            values['%s_r' % key] = int(values[key][ 1: 5], 16) / int('ffff', 16)
            values['%s_g' % key] = int(values[key][ 5: 9], 16) / int('ffff', 16)
            values['%s_b' % key] = int(values[key][ 9:13], 16) / int('ffff', 16)
            values['%s_a' % key] = int(values[key][13:17], 16) / int('ffff', 16)

def reread_gconf_value(conf, keys, key):
    if key in keys:
        read_gconf_values(conf, [key])

class _ContextMenu(gtk.Menu):
    def __init__(self, desktop_control, configure_glade_file, shell):
        gtk.Menu.__init__(self)
        self.shell = shell

        self.show_player = gtk.CheckMenuItem('_Show Music Player', True)
        self.show_player.connect('activate', self.toggle_player_visibility)
        self.add(self.show_player)

        self.add(gtk.SeparatorMenuItem())

        preferences = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        conf_dialog = ConfigDialog(configure_glade_file, gconf_plugin_path, self)
        preferences.connect('activate', self.show_preferences_dialog, desktop_control, configure_glade_file)
        self.add(preferences)

        self.show_all()

    def show(self, event):
        self.show_player.set_active(self.shell.props.visibility)
        self.popup(None, None, None, event.button, event.time)

    def toggle_player_visibility(self, menu_item):
        self.shell.props.visibility = menu_item.get_active()

    def show_preferences_dialog(self, menu_item, desktop_control, configure_glade_file):
        conf_dialog = ConfigDialog(configure_glade_file, gconf_plugin_path, desktop_control)
        conf_dialog.run()

class DesktopControl(gtk.DrawingArea):
    def __init__(self, icons, shell, player, conf_glade):
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.expose)

        self.shell = shell
        self.cover_image = CoverImage(icons)
        self.song_info = SongInfo()
        self.desktop_buttons = DesktopButtons(icons, player)
        self.context_menu = _ContextMenu(self, conf_glade, shell)

        self.draw_border = False

        # Find and set up icon and font
        icon_theme = gtk.icon_theme_get_default()
        icon_theme.connect('changed', self.icon_theme_changed, [self.cover_image, self.desktop_buttons])
        gc = gconf.client_get_default()
        gc.add_dir('/apps/nautilus/preferences', gconf.CLIENT_PRELOAD_NONE)
        gc.notify_add('/apps/nautilus/preferences/desktop_font', self.font_changed, [self.song_info])

        self.add_events(gtk.gdk.ENTER_NOTIFY_MASK | gtk.gdk.LEAVE_NOTIFY_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.BUTTON_PRESS_MASK)
        self.mouse_over = False
        self.hover_time_out = None
        self.connect('enter-notify-event', self.enter_leave)
        self.connect('leave-notify-event', self.enter_leave)
        self.connect('motion-notify-event', self.mouse_motion, self.desktop_buttons)
        self.connect('button-press-event', self.button_press, self.desktop_buttons)

        self.gconf_keys = ['background_color', 'roundness', 'hover_size', 'border', 'draw_reflection', 'reflection_height', 'reflection_intensity', 'blur', 'text_position']
        self.conf = {}
        read_gconf_values(self.conf, self.gconf_keys)

        self.set_gconf_callbacks([self, self.cover_image, self.song_info, self.desktop_buttons])

    def set_gconf_callbacks(self, affected):
        gc = gconf.client_get_default()
        for entry in gc.all_entries(gconf_plugin_path):
            path = entry.get_key()
            key = path.split('/')[-1]
            gc.notify_add(path, self.gconf_cb, {'key': key, 'affected': affected})

    def gconf_cb(self, client, cnxn_id, entry, ud):
        for af in ud['affected']:
            reread_gconf_value(af.conf, af.gconf_keys, ud['key'])
        self.queue_draw()

    def button_press(self, w, e, affected):
        if e.button == 1:
            if not affected.button_press():
                self.shell.props.visibility = not self.shell.props.visibility
        elif e.button == 3:
            self.context_menu.show(e)

    def mouse_motion(self, w, e, affected):
        if affected.set_mouse_position(self, e.x, e.y):
            self.queue_draw()

    def font_changed(self, client, cnxn_id, entry, affected):
        for a in affected:
            a.font_changed(entry.get_value().get_string())
        self.queue_draw()

    def icon_theme_changed(self, icon_theme, affected):
        for a in affected:
            a.icon_theme_changed(icon_theme)

    def enter_leave(self, w, e):
        if self.hover_time_out:
            gobject.source_remove(self.hover_time_out)
            self.hover_time_out = None
        hover = e.type == gtk.gdk.ENTER_NOTIFY
        self.hover_time_out = gobject.timeout_add(350, self.set_hover, hover)

    def set_hover(self, hover):
        tmp = self.mouse_over
        self.mouse_over = hover
        if tmp != hover:
            self.queue_draw()

    def expose(self, widget, event):
        cc = self.window.cairo_create()
        cc.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        cc.clip()
        self.draw(cc)

    def draw(self, cc):
        # Clear cairo context
        cc.set_source_rgba(0, 0, 0, 0)
        cc.set_operator(cairo.OPERATOR_SOURCE)
        cc.paint()

        # Scale the context so that the cover image area is 1 x 1
        rect = self.get_allocation()
        if self.conf['draw_reflection']:
            cover_area_size = min(rect.width - self.conf['blur']/2, (rect.height - self.conf['blur']/2) / (1 + self.conf['reflection_height']))
        else:
            cover_area_size = min(rect.width - self.conf['blur']/2, (rect.height - self.conf['blur']/2))

        if self.conf['text_position'] in [POSITION_SW, POSITION_NW]:
            x_trans = rect.width - cover_area_size - self.conf['blur']/2
        else:
            x_trans = self.conf['blur']/2

        cc.translate(x_trans, 0)
        cc.scale(cover_area_size, cover_area_size)

        cc.push_group()
        self.song_info.draw(cc)
        if self.mouse_over:
            self.desktop_buttons.draw(cc)
            cc.save()
            cc.translate((1 - self.conf['hover_size']) / 2, self.conf['border'])
            cc.scale(self.conf['hover_size'], self.conf['hover_size'])
        self.cover_image.draw(cc)
        if self.mouse_over:
            cc.restore()
        graphics = cc.pop_group()

        # Draw main graphics
        cc.set_source(graphics)
        cc.set_operator(cairo.OPERATOR_OVER)
        cc.paint()

        # Draw reflections
        if self.conf['draw_reflection']:
            cc.save()
            cc.set_operator(cairo.OPERATOR_ADD)
            cc.translate(0, 2.02)
            cc.scale(1, -1)
            cc.push_group()
            x_scale = cc.get_matrix()[0]
            r1 = int(self.conf['blur'] / 2 + 1.5)
            r0 = r1 - self.conf['blur'] - 1
            bn = (self.conf['blur'] + 1)**2
            for dx in xrange(r0, r1):
                for dy in xrange(r0, r1):
                    cc.save()
                    cc.translate(dx/x_scale, dy/x_scale)
                    cc.set_source(graphics)
                    cc.paint_with_alpha(1/bn)
                    cc.restore()
            graphics = cc.pop_group()
            cc.set_source(graphics)
            shadow_mask = cairo.LinearGradient(0, 1 - self.conf['reflection_height'], 0, 1)
            shadow_mask.add_color_stop_rgba(0, 0, 0, 0, 0)
            shadow_mask.add_color_stop_rgba(1, 0, 0, 0, self.conf['reflection_intensity'])
            cc.mask(shadow_mask)
            cc.restore()

        # Input mask, only the cover image is clickable
        # Will, (and should) only work if parent is gtk.Window
        pixmask = gtk.gdk.Pixmap(None, int(cover_area_size), int(cover_area_size), 1)
        ccmask = pixmask.cairo_create()
        roundedrec(ccmask, 0, 0, cover_area_size, cover_area_size, self.conf['roundness'])
        ccmask.fill()
        self.get_parent().input_shape_combine_mask(pixmask, int(x_trans), 0)

        # Draw border
        if self.draw_border:
            cc.identity_matrix()
            cc.rectangle(0, 0, rect.width, rect.height)
            cc.set_line_width(2)
            cc.set_source_rgba(1, 1, 1, 0.35)
            cc.set_dash([10,10], 0)
            cc.stroke_preserve()
            cc.set_source_rgba(0, 0, 0, 0.35)
            cc.set_dash([10,10], 10)
            cc.stroke()

    def set_song(self, playing=False, cover_image=None, song_info=None):
        self.cover_image.set_image(cover_image)
        self.song_info.set_text(song_info)
        self.desktop_buttons.set_playing(playing)
        self.queue_draw()

    def set_draw_border(self, val=False):
        self.draw_border = val
        self.queue_draw()

class SongInfo():
    tags = {'title'  : ['<big><b>', '</b></big>'],
            'artist' : ['<i>', '</i>'],
            'album'  : ['', '']}
    font = gconf.client_get_default().get_string('/apps/nautilus/preferences/desktop_font')

    def __init__(self, song_info=None):
        self.set_text(song_info)

        self.gconf_keys = ['border', 'text_position', 'text_color', 'text_shadow_color']
        self.conf = {}
        read_gconf_values(self.conf, self.gconf_keys)

    def font_changed(self, font):
        self.font = font

    def set_text(self, song_info):
        self.text = ''
        if song_info:
            for key in ('title', 'artist', 'album'):
                if song_info[key]:
                    self.text += '%s%s%s\n' % (self.tags[key][0], song_info[key].replace('&', '&amp;'), self.tags[key][1])
            self.text = self.text[:-1]

    def draw(self, cc):
        if self.text:
            cc.save()
            x_scale = cc.get_matrix()[0]
            x_trans = cc.get_matrix()[4]
            cc.identity_matrix()
            layout = cc.create_layout()
            layout.set_markup(self.text)
            layout.set_font_description(pango.FontDescription(self.font))
            txw, txh = layout.get_size()
            if self.conf['text_position'] in [POSITION_SW, POSITION_NW]:
                x_trans = x_trans - txw / pango.SCALE - x_scale * self.conf['border']
                layout.set_alignment(pango.ALIGN_RIGHT)
            else:
                x_trans = x_trans + x_scale * (1 + self.conf['border'])
                layout.set_alignment(pango.ALIGN_LEFT)
            if self.conf['text_position'] in [POSITION_NE, POSITION_NW]:
                y_trans = x_scale * self.conf['border'] / 2
            else:
                y_trans = x_scale * (1 - self.conf['border'] / 2) - txh / pango.SCALE
            cc.translate(x_trans, y_trans)
            # Draw text shadow
            cc.translate(1,1)
            cc.set_source_rgba(self.conf['text_shadow_color_r'], self.conf['text_shadow_color_g'], self.conf['text_shadow_color_b'], self.conf['text_shadow_color_a'])
            cc.show_layout(layout)
            # Draw text
            cc.translate(-1,-1)
            cc.set_source_rgba(self.conf['text_color_r'], self.conf['text_color_g'], self.conf['text_color_b'], self.conf['text_color_a'])
            cc.show_layout(layout)
            cc.restore()

class DesktopButtons():
    icon_keys = ['previous', 'play', 'next']

    def __init__(self, icons, player):
        self.icons = icons
        self.player = player
        self.idata = {}
        for k in self.icon_keys:
            self.idata[(k, 'cairo_path')] = None
            self.idata[(k, 'hover')] = False
        self.icon_theme_changed(gtk.icon_theme_get_default())
        self.playing = player.get_playing()

        self.gconf_keys = ['roundness', 'hover_size', 'border', 'background_color']
        self.conf = {}
        read_gconf_values(self.conf, self.gconf_keys)

    def set_playing(self, playing):
        self.playing = playing

    def button_press(self):
        if self.idata[('previous', 'hover')]:
            self.player.do_previous()
            return True
        elif self.idata[('play', 'hover')]:
            self.player.playpause()
            return True
        elif self.idata[('next', 'hover')]:
            self.player.do_next()
            return True
        return False

    def set_mouse_position(self, w, x, y):
        redraw = False
        for k in self.icon_keys:
            if self.idata[(k, 'cairo_path')]:
                cc = w.window.cairo_create()
                cc.append_path(self.idata[(k, 'cairo_path')])
                hover = cc.in_fill(x,y)
                if hover != self.idata[(k, 'hover')]:
                    self.idata[(k, 'hover')] = hover
                    redraw = True
        return redraw

    def icon_theme_changed(self, icon_theme):
        for k in self.icon_keys:
            self.idata[(k, 'icon_path')] = get_icon_path(icon_theme, self.icons[k], self.icons['size'])
            try:
                self.idata[(k, 'image')] = rsvg.Handle(file=self.idata[(k, 'icon_path')])
                self.idata[(k, 'w')]     = self.idata[(k, 'image')].props.width
                self.idata[(k, 'h')]     = self.idata[(k, 'image')].props.height
                self.idata[(k, 'draw')]  = self.draw_svg_icon
            except:
                try:
                    self.idata[(k, 'image')] = gtk.gdk.pixbuf_new_from_file(self.idata[(k, 'icon_path')])
                    self.idata[(k, 'w')]     = self.idata[(k, 'image')].get_width()
                    self.idata[(k, 'h')]     = self.idata[(k, 'image')].get_height()
                    self.idata[(k, 'draw')]  = self.draw_pixbuf_icon
                except:
                    sys.exit('ERROR: No media icons found.')
            self.idata[(k, 'dim')]   = max(self.idata[(k, 'w')], self.idata[(k, 'h')])
            self.idata[(k, 'scale')] = 1 / self.idata[(k, 'dim')]

    def draw(self, cc):
        cc.save()
        cc.set_operator(cairo.OPERATOR_OVER)
        cc.set_source_rgba(self.conf['background_color_r'], self.conf['background_color_g'], self.conf['background_color_b'], self.conf['background_color_a'] + 0.1)
        roundedrec(cc, 0, 0, 1, 1, self.conf['roundness'])
        cc.fill()
        y = self.conf['hover_size'] + 2 * self.conf['border']
        h = 1 - y - self.conf['border']
        n = len(self.icon_keys)
        w = (1 - (2 + n - 1) * self.conf['border']) / n
        cc.translate(self.conf['border'], y)
        for k in self.icon_keys:
            self.draw_icon(cc, k, w, h, self.idata[(k, 'hover')])
            cc.fill()
            cc.translate(self.conf['border'] + w, 0)
        cc.restore()

    def draw_icon(self, cc, key, w, h, hover):
        cc.save()

        cc.save()
        cc.scale(w, h)
        roundedrec(cc, 0, 0, 1, 1, self.conf['roundness'])

        cc.save()
        cc.identity_matrix()
        self.idata[(key, 'cairo_path')] = cc.copy_path()
        cc.restore()

        if hover:
            cc.set_source_rgba(1, 1, 1, 0.3)
        else:
            if self.playing and key == 'play':
                cc.set_source_rgba(0, 0, 0, 1)
            else:
                cc.set_source_rgba(0, 0, 0, 0.3)
        cc.fill()

        cc.restore()

        x = max(0, (w-h)/2)
        y = max(0, (h-w)/2)
        cc.translate(x, y)
        d = min(h, w)
        cc.scale(d, d)
        self.idata[(key, 'draw')](cc, key)
        cc.restore()

    def draw_svg_icon(self, cc, key):
        cc.push_group()
        cc.set_operator(cairo.OPERATOR_OVER)
        cc.scale(self.idata[(key, 'scale')], self.idata[(key, 'scale')])
        self.idata[(key, 'image')].render_cairo(cc)
        cc.set_source(cc.pop_group())
        roundedrec(cc, 0, 0, 1, 1, self.conf['roundness'])
        cc.fill()

    def draw_pixbuf_icon(self, cc, key):
        cc.scale(self.idata[(key, 'scale')], self.idata[(key, 'scale')])
        cc.set_source_pixbuf(self.idata[(key, 'image')], 0, 0)
        roundedrec(cc, 0, 0, self.idata[(key, 'w')], self.idata[(key, 'h')], self.conf['roundness'])
        cc.fill()

class CoverImage():
    def __init__(self, icons):
        self.icons = icons
        self.icon_theme_changed(gtk.icon_theme_get_default())

        self.gconf_keys = ['roundness', 'background_color']
        self.conf = {}
        read_gconf_values(self.conf, self.gconf_keys)

    def icon_theme_changed(self, icon_theme):
        not_playing_image = get_icon_path(icon_theme, self.icons['not_playing'], self.icons['size'])
        unknown_cover_image = get_icon_path(icon_theme, self.icons['unknown_cover'], self.icons['size'])

        # Check if shown image needs to be updated
        image = False
        if self.get_current_image() == self.get_not_playing_image():
            image = None
        elif self.get_current_image() == self.get_unknown_cover_image():
            image = UNKNOWN_COVER
        self.set_not_playing_image(not_playing_image)
        self.set_unknown_cover_image(unknown_cover_image)
        if image != False:
            self.set_image(image)

    def set_image(self, image=None):
        if not image:
            image = self.get_not_playing_image()
        if image == UNKNOWN_COVER:
            image = self.get_unknown_cover_image()
        if not image:
            self.draw = self.draw_background
        else:
            try:
                self.image = rsvg.Handle(file=image)
                self.w = self.image.props.width
                self.h = self.image.props.height
                self.draw = self.draw_svg
            except:
                try:
                    self.image = gtk.gdk.pixbuf_new_from_file(image)
                    self.w = self.image.get_width()
                    self.h = self.image.get_height()
                    self.draw = self.draw_pixbuf
                except:
                    pass

            dim = max(self.w, self.h)
            self.x = (dim - self.w) / 2
            self.y = dim - self.h
            self.scale = 1 / dim
        self.current_image = image

    def draw_background(self, cc):
        cc.save()
        cc.set_source_rgba(self.conf['background_color_r'], self.conf['background_color_g'], self.conf['background_color_b'], self.conf['background_color_a'])
        roundedrec(cc, 0, 0, 1, 1, self.conf['roundness'])
        cc.fill()
        cc.restore()

    def draw_svg(self, cc):
        cc.save()
        cc.scale(self.scale, self.scale)
        cc.push_group()
        cc.set_operator(cairo.OPERATOR_OVER)
        cc.set_source_rgba(self.conf['background_color_r'], self.conf['background_color_g'], self.conf['background_color_b'], self.conf['background_color_a'])
        cc.paint()
        cc.translate(self.x, self.y)
        self.image.render_cairo(cc)
        cc.set_source(cc.pop_group())
        roundedrec(cc, self.x, self.y, self.w, self.h, self.conf['roundness'])
        cc.fill()
        cc.restore()

    def draw_pixbuf(self, cc):
        cc.save()
        cc.set_operator(cairo.OPERATOR_SOURCE)
        cc.scale(self.scale, self.scale)
        roundedrec(cc, self.x, self.y, self.w, self.h, self.conf['roundness'])
        cc.set_source_rgba(self.conf['background_color_r'], self.conf['background_color_g'], self.conf['background_color_b'], self.conf['background_color_a'])
        cc.fill_preserve()
        cc.set_operator(cairo.OPERATOR_OVER)
        ##
        ## THE FOLLOWING IS JUST A SIMPLE HACK TO REMOVE A DARK BORDER THAT APPEAR ON THE PICTURES
        ##
        BH = 0.01
        cc.translate(-self.w * BH / 2, -self.h * BH / 2)
        cc.scale(1 + BH, 1 + BH)
        ##
        ## END HACK
        ##
        cc.set_source_pixbuf(self.image, self.x, self.y)
        cc.fill()
        cc.restore()

    def set_not_playing_image(self, image):
        self.not_playing_image = image

    def get_not_playing_image(self):
        try:
            return self.not_playing_image
        except:
            return None

    def set_unknown_cover_image(self, image):
        self.unknown_cover_image = image

    def get_unknown_cover_image(self):
        try:
            return self.unknown_cover_image
        except:
            return None

    def get_current_image(self):
        try:
            return self.current_image
        except:
            return None

    def set_current_image(self, image):
        self.current_image = image
