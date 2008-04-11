from __future__ import division

import gobject
import gtk, cairo, pango
import rsvg
from roundedrec import roundedrec

UNKNOWN_COVER = -1
RADIUS = 0.3

class DesktopControl(gtk.DrawingArea):
    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.expose)

        self.shadow_height = 0.4
        self.cover_image = CoverImage()
        self.song_info = SongInfo()
        self.desktop_buttons = DesktopButtons()

        self.add_events(gtk.gdk.ENTER_NOTIFY_MASK | gtk.gdk.LEAVE_NOTIFY_MASK)
        self.mouse_over = False
        self.hover_time_out = None
        self.connect('enter-notify-event', self.enter_leave)
        self.connect('leave-notify-event', self.enter_leave)

    def enter_leave(self, w, e):
        if self.hover_time_out:
            gobject.source_remove(self.hover_time_out)
            self.hover_time_out = None
        hover = e.type == gtk.gdk.ENTER_NOTIFY
        self.hover_time_out = gobject.timeout_add(500, self.set_hover, hover)

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
    
    def set_default_cover_images(self, not_playing_image=None, unknown_cover_image=None):
        self.cover_image.set_default_images(not_playing_image, unknown_cover_image)

    def draw(self, cc):
        # Clear cairo context
        cc.set_source_rgba(0, 0, 0, 0)
        cc.set_operator(cairo.OPERATOR_SOURCE)
        cc.paint()

        # Scale the context so that the cover image area is 1 x 1
        rect = self.get_allocation()
        cover_area_size = min(rect.width, rect.height / (1 + self.shadow_height))
        cc.scale(cover_area_size, cover_area_size)

        cc.push_group()
        self.song_info.draw(cc)
        if self.mouse_over:
            self.desktop_buttons.draw(cc)
            cc.save()
            cc.translate(0.19, 0.06)
            cc.scale(0.62, 0.62)
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
        shadow_mask = cairo.LinearGradient(0, 1 - self.shadow_height, 0, 1)
        shadow_mask.add_color_stop_rgba(0, 0, 0, 0, 0)
        shadow_mask.add_color_stop_rgba(1, 0, 0, 0, 0.4)
        cc.mask(shadow_mask)

        # Input mask, only the cover image is clickable
        # Will, (and should) only work if parent is gtk.Window
        pixmask = gtk.gdk.Pixmap(None, int(cover_area_size), int(cover_area_size), 1)
        ccmask = pixmask.cairo_create()
        roundedrec(ccmask, 0, 0, cover_area_size, cover_area_size, cover_area_size * RADIUS)
        ccmask.fill()
        self.get_parent().input_shape_combine_mask(pixmask, 0, 0)

    def set_song(self, cover_image=None, song_info=None):
        self.cover_image.set_image(cover_image)
        self.song_info.set_text(song_info)
        self.queue_draw()

class SongInfo():
    def __init__(self, song_info = None):
        self.set_text(song_info)

    def set_text(self, song_info):
        self.text = ''
        if song_info:
            for key in ('title', 'artist', 'album'):
                if song_info[key]:
                    self.text += '%s\n' % song_info[key]
            self.text = self.text[:-1]

    def draw(self, cc):
        if self.text:
            cc.save()
            x_scale = cc.get_matrix()[0]
            cc.identity_matrix()
            font = "Bitstream Vera Sans Bold 11"
            layout = cc.create_layout()
            layout.set_text(self.text)
            layout.set_font_description(pango.FontDescription(font))
            txw, txh = layout.get_size()
            cc.translate(x_scale * 1.07, x_scale * 0.97 - txh / pango.SCALE)
            cc.set_source_rgb(0, 0, 0)
            cc.show_layout(layout)
            cc.restore()

class DesktopButtons():
    def __init__(self):
        pass

    def draw(self, cc):
        cc.save()
        cc.set_operator(cairo.OPERATOR_OVER)
        cc.set_source_rgba(0, 0, 0, 0.3)
        roundedrec(cc, 0, 0, 1, 1, RADIUS)
        cc.fill()
        cc.set_source_rgba(0, 0, 0, 0.2)
        cc.translate(0.08, 0.74)
        path = '/usr/share/icons/gnome/scalable/actions/'
        for b in ['gtk-media-previous-ltr.svg',
                  'gtk-media-play-ltr.svg',
                  'gtk-media-next-ltr.svg']:
            self.draw_icon(cc, '%s/%s' % (path, b), 0.24, 0.20, RADIUS)
            cc.translate(0.3, 0)
        cc.restore()

    def draw_icon(self, cc, svg, w, h, r):
        cc.save()
        cc.set_operator(cairo.OPERATOR_OVER)

        cc.save()
        cc.scale(w, h)
        cc.set_source_rgba(0,0,0,0.2)
        roundedrec(cc, 0, 0, 1, 1, RADIUS)
        cc.fill()
        cc.restore()

        cc.translate((w-h)/2, 0)
        cc.scale(h, h)

        cc.push_group()
        image = rsvg.Handle(file=svg)
        iw = image.props.width
        ih = image.props.height

        dim = max(iw, ih)
        scale = 1 / dim
        
        cc.scale(scale, scale)
        image.render_cairo(cc)
        cc.set_source(cc.pop_group())
        roundedrec(cc, 0, 0, 1, 1, RADIUS)
        cc.fill()
        cc.restore()


class CoverImage():
    def __init__(self):
        self.set_default_images()

    def set_default_images(self, not_playing_image=None, unknown_cover_image=None):
        # Check if shown image needs to be updated
        image = False
        if self.get_current_image() == self.get_not_playing_image():
            image = None
        elif self.get_current_image() == self.get_unknown_cover_image():
            image = UNKNOWN_COVER
        self.not_playing_image = not_playing_image
        self.unknown_cover_image = unknown_cover_image
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

            self.r = min(self.w, self.h) * RADIUS
            dim = max(self.w, self.h)
            self.x = dim - self.w
            self.y = dim - self.h
            self.scale = 1 / dim
        self.current_image = image

    def draw_background(self, cc):
        cc.save()
        cc.set_source_rgba(0,0,0,0.2)
        roundedrec(cc, 0, 0, 1, 1, RADIUS)
        cc.fill()
        cc.restore()

    def draw_svg(self, cc):
        cc.save()
        cc.scale(self.scale, self.scale)
        cc.push_group()
        cc.set_source_rgba(0,0,0,0.2)
        cc.paint()
        self.image.render_cairo(cc)
        cc.set_source(cc.pop_group())
        roundedrec(cc, self.x, self.y, self.w, self.h, self.r)
        cc.fill()
        cc.restore()

    def draw_pixbuf(self, cc):
        cc.save()
        cc.set_operator(cairo.OPERATOR_OVER)
        cc.scale(self.scale, self.scale)
        roundedrec(cc, self.x, self.y, self.w, self.h, self.r)
        cc.set_source_rgba(0,0,0,0.2)
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
