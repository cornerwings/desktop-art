from __future__ import division

import sys
import gobject
import gtk, cairo, pango
import gconf
import rsvg
from roundedrec import roundedrec

ROUNDNESS = 0.3 
REFLECTION_HIGHT = 0.4
REFLECTION_INTENSITY = 0.5
HOVER_SIZE = 0.7
BORDER = 0.06
UNKNOWN_COVER = -1
COLOR_R = 0
COLOR_G = 0
COLOR_B = 0

def get_icon_path(theme, name, size):
    icon = theme.lookup_icon(name, size, gtk.ICON_LOOKUP_FORCE_SVG)
    return (icon and icon.get_filename())

class DesktopControl(gtk.DrawingArea):
    def __init__(self, icons):
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.expose)

        self.cover_image = CoverImage(icons)
        self.song_info = SongInfo()
        self.desktop_buttons = DesktopButtons(icons)

        # Find and set up icon and font
        icon_theme = gtk.icon_theme_get_default()
        icon_theme.connect('changed', self.icon_theme_changed, [self.cover_image, self.desktop_buttons])
	gc = gconf.client_get_default()
	gc.add_dir('/apps/nautilus/preferences', gconf.CLIENT_PRELOAD_NONE)
	gc.notify_add('/apps/nautilus/preferences/desktop_font', self.font_changed, [self.song_info])

        self.add_events(gtk.gdk.ENTER_NOTIFY_MASK | gtk.gdk.LEAVE_NOTIFY_MASK | gtk.gdk.POINTER_MOTION_MASK )
        self.mouse_over = False
        self.hover_time_out = None
        self.connect('enter-notify-event', self.enter_leave)
        self.connect('leave-notify-event', self.enter_leave)
	self.connect('motion-notify-event', self.motion_event, self.desktop_buttons)

    def motion_event(self, w, e, db):
        if db.set_mouse_position(self, e.x, e.y):
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
        cover_area_size = min(rect.width, rect.height / (1 + REFLECTION_HIGHT))
        cc.scale(cover_area_size, cover_area_size)

        cc.push_group()
        self.song_info.draw(cc)
        if self.mouse_over:
            self.desktop_buttons.draw(cc)
            cc.save()
            cc.translate((1 - HOVER_SIZE) / 2, BORDER)
            cc.scale(HOVER_SIZE, HOVER_SIZE)
        self.cover_image.draw(cc)
        if self.mouse_over:
            cc.restore()
        graphics = cc.pop_group()

        # Draw main graphics
        cc.set_source(graphics)
        cc.set_operator(cairo.OPERATOR_OVER)
        cc.paint()

        # Draw reflections
        cc.translate(0, 2.02)
        cc.scale(1, -1)
        cc.set_source(graphics)
        shadow_mask = cairo.LinearGradient(0, 1 - REFLECTION_HIGHT, 0, 1)
        shadow_mask.add_color_stop_rgba(0, 0, 0, 0, 0)
        shadow_mask.add_color_stop_rgba(1, 0, 0, 0, REFLECTION_INTENSITY)
        cc.mask(shadow_mask)

        # Input mask, only the cover image is clickable
        # Will, (and should) only work if parent is gtk.Window
        pixmask = gtk.gdk.Pixmap(None, int(cover_area_size), int(cover_area_size), 1)
        ccmask = pixmask.cairo_create()
        roundedrec(ccmask, 0, 0, cover_area_size, cover_area_size, ROUNDNESS)
        ccmask.fill()
        self.get_parent().input_shape_combine_mask(pixmask, 0, 0)

    def set_song(self, cover_image=None, song_info=None):
        self.cover_image.set_image(cover_image)
        self.song_info.set_text(song_info)
        self.queue_draw()

class SongInfo():
    tags = {'title'  : ['<big><b>', '</b></big>'],
	    'artist' : ['<i>', '</i>'],
	    'album'  : ['', '']}
    font = gconf.client_get_default().get_string('/apps/nautilus/preferences/desktop_font')
	
    def __init__(self, song_info = None):
        self.set_text(song_info)

    def font_changed(self, font):
        self.font = font
    
    def set_text(self, song_info):
        self.text = ''
        if song_info:
            for key in ('title', 'artist', 'album'):
                if song_info[key]:
			self.text += '%s%s%s\n' % (self.tags[key][0], song_info[key], self.tags[key][1])
            self.text = self.text[:-1]

    def draw(self, cc):
        if self.text:
            cc.save()
            x_scale = cc.get_matrix()[0]
            cc.identity_matrix()
            layout = cc.create_layout()
            layout.set_markup(self.text)
            layout.set_font_description(pango.FontDescription(self.font))
            txw, txh = layout.get_size()
            cc.translate(x_scale * (1 + BORDER), x_scale * (1 - BORDER / 2) - txh / pango.SCALE)
            cc.set_source_rgb(COLOR_R, COLOR_G, COLOR_B)
            cc.show_layout(layout)
            cc.restore()

class DesktopButtons():
    icon_keys = ['previous', 'play', 'next']

    def __init__(self, icons):
        self.icons = icons
        self.idata = {}
        for k in self.icon_keys:
            self.idata[(k, 'cairo_path')] = None
            self.idata[(k, 'hover')] = False
        self.icon_theme_changed(gtk.icon_theme_get_default())

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
        cc.set_source_rgba(COLOR_R, COLOR_G, COLOR_B, 0.3)
        roundedrec(cc, 0, 0, 1, 1, ROUNDNESS)
        cc.fill()
        y = HOVER_SIZE + 1.8 * BORDER
        h = 1 - y - BORDER
        n = len(self.icon_keys)
        w = (1 - (2 + n - 1) * BORDER) / n
        cc.translate(BORDER, y)
        for k in self.icon_keys:
            self.draw_icon(cc, k, w, h, self.idata[(k, 'hover')])
            cc.fill()
            cc.translate(BORDER + w, 0)
        cc.restore()

    def draw_icon(self, cc, key, w, h, hover):
        cc.save()

        cc.save()
        cc.scale(w, h)
        roundedrec(cc, 0, 0, 1, 1, ROUNDNESS)

	cc.save()
	cc.identity_matrix()
	self.idata[(key, 'cairo_path')] = cc.copy_path()
	cc.restore()

	if hover:
	    cc.set_source_rgba(0, 0, 0, 0.5)
	else:
	    cc.set_source_rgba(0, 0, 0, 0.2)
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
        cc.scale(self.idata[(key, 'scale')], self.idata[(key, 'scale')])
        self.idata[(key, 'image')].render_cairo(cc)
        cc.set_source(cc.pop_group())
        roundedrec(cc, 0, 0, 1, 1, ROUNDNESS)
        cc.fill()
            
    def draw_pixbuf_icon(self, cc, key):
        cc.scale(self.idata[(key, 'scale')], self.idata[(key, 'scale')])
        cc.set_source_pixbuf(self.idata[(key, 'image')], 0, 0)
        roundedrec(cc, 0, 0, self.idata[(key, 'w')], self.idata[(key, 'h')], ROUNDNESS)
        cc.fill()

class CoverImage():
    def __init__(self, icons):
        self.icons = icons
        self.icon_theme_changed(gtk.icon_theme_get_default())

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
        cc.set_source_rgba(COLOR_R, COLOR_G, COLOR_B, 0.2)
        roundedrec(cc, 0, 0, 1, 1, ROUNDNESS)
        cc.fill()
        cc.restore()

    def draw_svg(self, cc):
        cc.save()
        cc.scale(self.scale, self.scale)
        cc.push_group()
        cc.set_source_rgba(COLOR_R, COLOR_G, COLOR_B, 0.2)
        cc.paint()
        self.image.render_cairo(cc)
        cc.set_source(cc.pop_group())
        roundedrec(cc, self.x, self.y, self.w, self.h, ROUNDNESS)
        cc.fill()
        cc.restore()

    def draw_pixbuf(self, cc):
        cc.save()
        cc.set_operator(cairo.OPERATOR_OVER)
        cc.scale(self.scale, self.scale)
        roundedrec(cc, self.x, self.y, self.w, self.h, ROUNDNESS)
        cc.set_source_rgba(COLOR_R, COLOR_G, COLOR_B, 0.2)
        cc.fill_preserve()
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
