import rb
import gtk, gtk.glade

from DesktopControl import DesktopControl
from CoverManager import CoverManager

icons = {'previous'      : 'gtk-media-previous-ltr',
         'play'          : 'gtk-media-play-ltr',
	 'next'          : 'gtk-media-next-ltr',
	 'not_playing'   : 'rhythmbox-notplaying',
	 'unknown_cover' : 'rhythmbox',
	 'size'          : 500}

class DesktopArt(rb.Plugin):
	def __init__ (self):
		rb.Plugin.__init__ (self)

	def activate (self, shell):
		window =  gtk.glade.XML(self.find_file('desktop-art.glade')).get_widget('window')
		self.composited = window.is_composited()
		if self.composited:
			player = shell.get_player()

			desktop_control = DesktopControl(icons, shell, player)
			cover_manager = CoverManager(player.props.db)

			window.set_colormap(window.get_screen().get_rgba_colormap())
			window.stick()
			window.set_keep_below(True)
			window.add(desktop_control)
			width, height = window.get_size()
			window.move(50, gtk.gdk.screen_height() - height - 40)
			
			self.player = player
			self.cb = player.connect('playing-changed', self.playing_changed, desktop_control, cover_manager)
			self.playing_changed(player, player.get_playing(), desktop_control, cover_manager)
			
			self.window = window
			self.desktop_control = desktop_control
			self.cover_manager = cover_manager
			window.show_all()
		else:
			# We don't have compisiting
			md = gtk.MessageDialog(type=gtk.MESSAGE_ERROR,
					       buttons=gtk.BUTTONS_OK,
					       message_format='You are not running under a composited desktop-environment. The Desktop Art Plugin cannot work without one.')
			md.run()
			md.destroy()
			
	def deactivate(self, shell):
		if self.composited:
			self.window.destroy()
			self.player.disconnect(self.cb)
			del self.desktop_control
			del self.cover_manager
			del self.window
			del self.cb
			del self.player
		del self.composited

	def playing_changed(self, player, playing, desktop_control, cover_manager):
		desktop_control.set_playing(playing)
		if playing:
			c, s = cover_manager.get_cover_and_song_info(player.get_playing_entry())
			desktop_control.set_song(c, s)
		else:
			desktop_control.set_song()
