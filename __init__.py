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

import rb
import gtk, gtk.glade
import gconf
import time
import gobject

from DesktopControl import DesktopControl
from CoverManager import CoverManager
from ConfigDialog import ConfigDialog
import DefaultGConfValues

icons = {'previous'      : 'gtk-media-previous-ltr',
         'play'          : 'gtk-media-play-ltr',
         'next'          : 'gtk-media-next-ltr',
         'not_playing'   : 'rhythmbox-notplaying',
         'unknown_cover' : 'rhythmbox',
         'size'          : 500}

gconf_plugin_path = '/apps/rhythmbox/plugins/desktop-art'
POLL_TIMEOUT = 1000

class DesktopArt(rb.Plugin):
    def __init__ (self):
        rb.Plugin.__init__ (self)

    def activate (self, shell):
        window =  gtk.glade.XML(self.find_file('desktop-art.glade')).get_widget('window')
        self.composited = window.is_composited()
        if self.composited:
            player = shell.get_player()

            desktop_control = DesktopControl(icons, shell, player, self.find_file('configure-art.glade'))
            cover_manager = CoverManager(player.props.db)
            player.props.db.connect_after("entry-extra-metadata-notify::rb:coverArt-uri", self.notify_metadata)

            gc = gconf.client_get_default()
            window_props = self.get_gconf_window_props(gc)

            window.set_colormap(window.get_screen().get_rgba_colormap())
            window.stick()
            window.set_keep_below(True)
            window.add(desktop_control)
            window

            self.gc_notify_ids = [gc.notify_add(self.gconf_path('window_x'), self.gconf_cb, window_props),
                                  gc.notify_add(self.gconf_path('window_y'), self.gconf_cb, window_props),
                                  gc.notify_add(self.gconf_path('window_w'), self.gconf_cb, window_props),
                                  gc.notify_add(self.gconf_path('window_h'), self.gconf_cb, window_props)]

            self.player = player
            self.cb = player.connect('playing-changed', self.playing_changed, desktop_control, cover_manager)
            self.playing_changed(player, player.get_playing(), desktop_control, cover_manager)

            self.gc = gc
            self.window = window
            self.window_props = window_props
            self.desktop_control = desktop_control
            self.cover_manager = cover_manager

            print "Adding timeout"
            ret = gobject.timeout_add(POLL_TIMEOUT, self.poll_for_coverart)
            print "integer id returned: " + str(ret)

            self.position_window(self.window_props)
            self.window.show_all()
        else:
            # We don't have compisiting
            md = gtk.MessageDialog(type=gtk.MESSAGE_ERROR,
                                   buttons=gtk.BUTTONS_OK,
                                   message_format='You are not running under a composited desktop-environment. The Desktop Art Plugin cannot work without one.')
            md.run()
            md.destroy()

    def deactivate(self, shell):
        if self.composited:
            for i in self.gc_notify_ids:
                self.gc.notify_remove(i)
            self.set_gconf_window_props(self.gc, self.window)
            self.window.destroy()
            self.player.disconnect(self.cb)
            del self.desktop_control
            del self.cover_manager
            del self.window
            del self.gc
            del self.cb
            del self.player
            del self.gc_notify_ids
        del self.composited

    def create_configure_dialog(self, dialog=None):
        if not dialog:
            dialog =  ConfigDialog(self.find_file('configure-art.glade'), gconf_plugin_path, self.desktop_control)
            dialog.present()
        return dialog

    # Add the poll object for new track
    def playing_changed(self, player, playing, desktop_control, cover_manager):
        gobject.timeout_add(POLL_TIMEOUT, self.poll_for_coverart)
        c, s = cover_manager.get_cover_and_song_info(player.get_playing_entry())
        desktop_control.set_song(playing, c, s)

    # An ugly poll method which repeatedly wastes system resources
    def poll_for_coverart(self):
        print "Polling for coverart"
        c, s = self.cover_manager.get_cover_and_song_info(self.player.get_playing_entry())
        print "Cover art found: " + str(c)
        if c==-1 or c is None:
            return True
        else:
            self.desktop_control.set_song(self.player.get_playing(), c, s)
            return False          

    # Subscribe to metadata notification
    # TODO: Not working - notification coming too soon
    def notify_metadata(self, db, entry, field=None,metadata=None):
        print "Metadata changed changed"
        if entry:
            c, s = self.cover_manager.get_cover_and_song_info(entry)
            self.desktop_control.set_song(self.player.get_playing(), c, s)

    def gconf_path(self, key):
        return '%s/%s' % (gconf_plugin_path, key)

    def get_gconf_window_props(self, gc):
        return {'x' : gc.get_int(self.gconf_path('window_x')),
                'y' : gc.get_int(self.gconf_path('window_y')),
                'w' : gc.get_int(self.gconf_path('window_w')),
                'h' : gc.get_int(self.gconf_path('window_h'))}

    def set_gconf_window_props(self, gc, window):
        x, y = window.get_position()
        w, h = window.get_size()
        gc.set_int(self.gconf_path('window_x'), x)
        gc.set_int(self.gconf_path('window_y'), y)
        gc.set_int(self.gconf_path('window_w'), w)
        gc.set_int(self.gconf_path('window_h'), h)

    def gconf_cb(self, client, cnxn_id, entry, wp):
        k = entry.get_key().split('_')[-1]
        wp[k] = entry.get_value().get_int()
        self.position_window(wp)

    def position_window(self, wp):
        self.window.resize(wp['w'], wp['h'])
        self.window.move(wp['x'], wp['y'])
