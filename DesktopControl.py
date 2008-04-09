from __future__ import division

import gtk, cairo, pango
import rsvg
from roundedrec import roundedrec

class CoverImage():
    def __init__(self, path):
        try:
            self.cover = rsvg.Handle(file=path)
            self.w = self.cover.props.width
            self.h = self.cover.props.height
            self.draw = self.draw_svg
        except:
            try:
                self.cover = gtk.gdk.pixbuf_new_from_file(path)
                self.w = self.cover.get_width()
                self.h = self.cover.get_height()
                self.draw = self.draw_pixbuf
            except:
                pass

        self.r = min(self.w, self.h) / 3
        dim = max(self.w, self.h)
        self.x = dim - self.w
        self.y = dim - self.h
        self.scale = 1 / dim
        self.path = path

    def draw_svg(self, cc):
        cc.save()
        cc.scale(self.scale, self.scale)
        cc.push_group()
        cc.set_source_rgba(0,0,0,0.2)
        cc.paint()
        self.cover.render_cairo(cc)
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
        cc.set_source_pixbuf(self.cover, self.x, self.y)
        cc.fill()
        cc.restore()

    def get_path(self):
        return self.path

class SongInfo():
    def __init__(self, song_info = None):
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

class DesktopControl(gtk.DrawingArea):
    def __init__(self, default_art):
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.expose)

        self.shadow_height = 0.4

        self.default_art = default_art
        self.image = CoverImage(self.default_art)
        self.text = SongInfo()

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
        cover_area_size = min(rect.width, rect.height / (1 + self.shadow_height))
        cc.scale(cover_area_size, cover_area_size)

        cc.push_group()
        self.image.draw(cc)
        self.text.draw(cc)
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

    def set_song_info(self, cover_path=None, song_info=None):
        if self.image.get_path() != cover_path:
            self.image = CoverImage(cover_path or self.default_art)
        self.text = SongInfo(song_info)
        self.queue_draw()
