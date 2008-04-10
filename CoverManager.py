import rhythmdb
import DesktopControl

from os import path
from urllib import url2pathname

class CoverManager():
    def __init__(self, db):
        self.db = db

    def get_cover_and_song_info(self, db_entry):
        return (self.get_cover(db_entry), self.get_song_info(db_entry))

    def get_cover(self, db_entry):
        cover_dir = path.dirname(url2pathname(db_entry.get_playback_uri()).replace('file://', ''))
        for file_type in ('jpg', 'png', 'jpeg', 'gif', 'svg'):
            cover_file = path.join(cover_dir, 'cover.%s' % file_type)
            if path.isfile(cover_file):
                return cover_file
        # No cover found
        return DesktopControl.UNKNOWN_COVER

    def get_song_info(self, db_entry):
        song_info = {}
        song_info['title'] = self.db.entry_get(db_entry, rhythmdb.PROP_TITLE)
        song_info['artist'] = self.db.entry_get(db_entry, rhythmdb.PROP_ARTIST)
        song_info['album'] = self.db.entry_get(db_entry, rhythmdb.PROP_ALBUM)
        return song_info
