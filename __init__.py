import rhythmdb, rb
import gtk

from os import path
from urllib import url2pathname
from DesktopControl import DesktopControl

not_playing_artwork = '/usr/share/rhythmbox/icons/hicolor/scalable/status/rhythmbox-notplaying.svg'
unknown_artwork = '/usr/share/icons/hicolor/scalable/apps/rhythmbox.svg'

class DesktopArt(rb.Plugin):
	def __init__ (self):
		rb.Plugin.__init__ (self)

	def activate (self, shell):
		dc = DesktopControl(not_playing_artwork)
		window =  gtk.glade.XML(self.find_file('desktop-art.glade')).get_widget('window')
		window.set_colormap(window.get_screen().get_rgba_colormap())
		window.stick()
		window.set_keep_below(True)
		window.add(dc)
		width, height = window.get_size()
		window.move(40, gtk.gdk.screen_height() - height)

		self.player = shell.get_player()
		self.cb = self.player.connect('playing-changed', self.playing_changed, dc)
		self.playing_changed(self.player, self.player.get_playing(), dc)

		self.window = window
		self.dc = dc
		window.show_all()

	def deactivate(self, shell):
		self.window.destroy()
		self.player.disconnect(self.cb)
		del self.dc
		del self.window
		del self.cb
		del self.player

	def playing_changed(self, player, playing, dc):
		if playing:
			db_entry = player.get_playing_entry()
			song_info = {}
			song_info['title'] = player.props.db.entry_get(db_entry, rhythmdb.PROP_TITLE)
			song_info['artist'] = player.props.db.entry_get(db_entry, rhythmdb.PROP_ARTIST)
			song_info['album'] = player.props.db.entry_get(db_entry, rhythmdb.PROP_ALBUM)
			cover_dir = path.dirname(url2pathname(db_entry.get_playback_uri()).replace('file://', ''))
			for file_type in ('jpg', 'png', 'jpeg', 'gif', 'svg'):
				cover_file = path.join(cover_dir, 'cover.%s' % file_type)
				if path.isfile(cover_file):
					dc.set_song_info(cover_file, song_info)
					return
			# No cover found
			dc.set_song_info(unknown_artwork, song_info)
		else:
			# Not playing
			dc.set_song_info()
