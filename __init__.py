import rb
import gtk

from DesktopControl import DesktopControl
from CoverManager import CoverManager

not_playing_image = 'rhythmbox-notplaying'
unknown_cover_image = 'rhythmbox'
min_icon_size = 500

class DesktopArt(rb.Plugin):
	def __init__ (self):
		rb.Plugin.__init__ (self)

	def activate (self, shell):
		player = shell.get_player()

		desktop_control = DesktopControl()
		cover_manager = CoverManager(player.props.db)

		# Find and set up icon
		icon_theme = gtk.icon_theme_get_default()
		icon_theme.connect('changed', self.icon_theme_changed, desktop_control, cover_manager)
		icon_theme.emit('changed')

		window =  gtk.glade.XML(self.find_file('desktop-art.glade')).get_widget('window')
		window.set_colormap(window.get_screen().get_rgba_colormap())
		window.stick()
		window.set_keep_below(True)
		window.add(desktop_control)
		width, height = window.get_size()
		window.move(40, gtk.gdk.screen_height() - height)

		self.player = player
		self.cb = player.connect('playing-changed', self.playing_changed, desktop_control, cover_manager)

		self.window = window
		self.desktop_control = desktop_control
		self.cover_manager = cover_manager
		window.show_all()

	def deactivate(self, shell):
		self.window.destroy()
		self.player.disconnect(self.cb)
		del self.desktop_control
		del self.cover_manager
		del self.window
		del self.cb
		del self.player

	def playing_changed(self, player, playing, desktop_control, cover_manager):
		if playing:
			c, s = cover_manager.get_cover_and_song_info(player.get_playing_entry())
			desktop_control.set_song(c, s)
		else:
			desktop_control.set_song()

	def icon_theme_changed(self, icon_theme, desktop_control, cover_manager):
		not_playing_icon = icon_theme.lookup_icon(not_playing_image, min_icon_size, gtk.ICON_LOOKUP_FORCE_SVG)
		unknown_cover_icon = icon_theme.lookup_icon(unknown_cover_image, min_icon_size, gtk.ICON_LOOKUP_FORCE_SVG)
		not_playing_icon_file = not_playing_icon and not_playing_icon.get_filename()
		unknown_cover_icon_file = unknown_cover_icon and unknown_cover_icon.get_filename()
		desktop_control.set_default_cover_images(not_playing_icon_file, unknown_cover_icon_file)
