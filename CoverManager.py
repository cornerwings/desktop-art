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

#
#
# This is just a mess, dont look any further
# I only look for localy stored cover images
#
#

import rhythmdb
import DesktopControl
import mimetypes

from os import path, listdir
from urllib import url2pathname

IMAGE_NAMES = ['cover', 'album', 'albumart', '.folder', 'folder']

class CoverManager():
    def __init__(self, db):
        self.db = db

    def get_cover_and_song_info(self, db_entry):
        return (self.get_cover(db_entry), self.get_song_info(db_entry))

    def get_cover(self, db_entry=None):
        # Find cover in music dir
        if db_entry:
            cover_dir = path.dirname(url2pathname(db_entry.get_playback_uri()).replace('file://', ''))
            if path.isdir(cover_dir):
                for f in listdir(cover_dir):
                    file_name = path.join(cover_dir, f)
                    mt = mimetypes.guess_type(file_name)[0]
                    if mt and mt.startswith('image/'):
                        if path.splitext(f)[0].lower() in IMAGE_NAMES:
                            return file_name

            # Find cover saved by artdisplay plugin
            song_info = self.get_song_info(db_entry)
            for file_type in ('jpg', 'png', 'jpeg', 'gif', 'svg'):
                cover_file = path.join(path.expanduser('~/.gnome2/rhythmbox/covers'),
                                       '%s - %s.%s' %
                                       (song_info['artist'],
                                        song_info['album'],
                                        file_type))
                if path.isfile(cover_file):
                    return cover_file

            # No cover found
            return DesktopControl.UNKNOWN_COVER
        # Not playing
        return None

    def get_song_info(self, db_entry=None):
        song_info = {}
        if db_entry:
            song_info['title'] = self.db.entry_get(db_entry, rhythmdb.PROP_TITLE)
            song_info['artist'] = self.db.entry_get(db_entry, rhythmdb.PROP_ARTIST)
            song_info['album'] = self.db.entry_get(db_entry, rhythmdb.PROP_ALBUM)
        return song_info
