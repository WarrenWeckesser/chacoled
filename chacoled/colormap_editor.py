
import numpy as np

# Enthought library imports
from enable.api import ComponentEditor

from traits.api import HasTraits, Instance, Property, Event, Enum, Str, \
        Float, Range, on_trait_change
from traitsui.api import Item, HGroup, VGroup, View, EnumEditor, RangeEditor
from traitsui.menu import Action, Menu, MenuBar
from pyface.action.api import Group as ActionGroup

# Chaco imports
from chaco.api import ColorMapper, ColorBar, LinearMapper, DataRange1D

# Local imports
from unit_map import UnitMap
from unit_map_editor import UnitMapEditor, UnitMapPlotter


red_bg = (1.0,0.8,0.8)
green_bg = (0.8,1.0,0.8)
blue_bg = (0.8,0.8,1.0)


class ColormapChannel(UnitMap):
    """
    Extends UnitMap with a method to convert the points to a list of segments
    formatted for use by the Chaco ColorMapper class.
    """

    def _convert_to_segments(self):
        points = self.points
        point = points[0]
        segs = [ (point[0], point[1], point[1]) ]
        for k in range(1,len(points)):
            point = points[k]
            if point[0] == segs[-1][0]:
                seg = segs.pop()
                seg = (seg[0], seg[1], point[1])
            else:
                seg = (point[0], point[1], point[1])
            segs.append(seg)
        return segs


class ColormapEditor(HasTraits):

    red_channel = Instance(UnitMapEditor)
    green_channel = Instance(UnitMapEditor)
    blue_channel = Instance(UnitMapEditor)

    show = Enum('all','red','green','blue')

    rgb_background = Enum('RGB tint', 'white', 'black')
    rgb_line_color = Enum('black', 'RGB', 'white')
    grid_color = Enum('black', 'white')

    luminance = Instance(UnitMapPlotter)
    luminance_red = Range(low=0.0, high=1.0, value=0.3)
    luminance_green = Range(low=0.0, high=1.0, value=0.59)
    luminance_blue = Property(Float, depends_on=['luminance_red','luminance_green'])

    colormapper = Property(Instance(ColorMapper))

    colorbar = Instance(ColorBar)
    
    color_range = Instance(DataRange1D)

    status_text = Str('')

    updated = Event

    def trait_view(self, parent=None):
        file_group = ActionGroup(
                        Action(name='Import', action='import_colormap'),
                        Action(name='Export', action='export_colormap'))
        app_group = ActionGroup(
                        Action(name='Exit', action='exit'))
        file_menu = Menu(file_group, app_group, name='File')
        menu_bar = MenuBar(file_menu)
        view = View(
                    VGroup(
                        Item('red_channel', editor=ComponentEditor(size=(200,125)),
                                show_label=False,
                                visible_when='show == "all" or show == "red"'),
                        Item('green_channel', editor=ComponentEditor(size=(200,125)),
                                show_label=False,
                                visible_when='show == "all" or show == "green"'),
                        Item('blue_channel', editor=ComponentEditor(size=(200,125)),
                                show_label=False,
                                visible_when='show == "all" or show == "blue"'),
                        Item('luminance', editor=ComponentEditor(size=(200,100)),
                                show_label=False),
                        Item('colorbar', editor=ComponentEditor(size=(200,100)), 
                                show_label=False, springy=False, resizable=False),
                        ),
                    resizable=True,
                    # title="Colormap Editor",
                    )
        return view

    #-----------------------------------------------------------------------
    # Traits defaults
    #-----------------------------------------------------------------------
    
    def _red_channel_default(self):
        um = ColormapChannel()
        ume = UnitMapEditor(unit_map=um, background_color=red_bg, label="Red")
        return ume

    def _green_channel_default(self):
        um = ColormapChannel()
        ume = UnitMapEditor(unit_map=um, background_color=green_bg, label="Green")
        return ume

    def _blue_channel_default(self):
        um = ColormapChannel()
        ume = UnitMapEditor(unit_map=um, background_color=blue_bg, label="Blue")
        return ume

    def _luminance_default(self):
        um = UnitMap()
        ump = UnitMapPlotter(unit_map=um, label="Luminance")
        return ump

    def _color_range_default(self):
        rng = DataRange1D(low=0, high=1.0)
        return rng

    def _colorbar_default(self):
        # Create the colorbar
        colorbar = ColorBar(index_mapper=LinearMapper(range=self.color_range),
                            color_mapper=self.colormapper,
                            orientation='h',
                            # resizable='v',
                            width=100,
                            padding_left=3,
                            padding_right=3,
                            padding_top=5,
                            padding_bottom=30,
                            )
        return colorbar

    #-----------------------------------------------------------------------
    # Traits property methods
    #-----------------------------------------------------------------------

    def _get_colormapper(self):
        segment_map = self._segment_map()
        colormapper = ColorMapper.from_segment_map(segment_map, range=self.color_range)
        return colormapper

    def _get_luminance_blue(self):
        blue = 1.0 - (self.luminance_red + self.luminance_green)
        return blue

    #-----------------------------------------------------------------------
    # Trait change handlers
    #-----------------------------------------------------------------------

    @on_trait_change('red_channel.updated, green_channel.updated, blue_channel.updated')
    def _update_image(self, obj, name, value):
        # Update the colorbar.
        if self.colorbar is not None:
            self.colorbar.color_mapper = self.colormapper
            self.colorbar.request_redraw()

        # Update the status text.
        self.status_text = obj.status_text

        # Propagate the updated event.
        self.updated = True

    @on_trait_change('red_channel.updated, green_channel.updated, blue_channel.updated, luminance_red, luminance_green')
    def _update_luminance(self, obj, name, value):    
        # Update the luminance unit map.
        xvals = sorted(set([x for x,y in self.red_channel.unit_map.points])
                        | set([x for x,y in self.green_channel.unit_map.points])
                        | set([x for x,y in self.blue_channel.unit_map.points]))
        r = np.array([self.red_channel.unit_map.evaluate(x) for x in xvals])
        g = np.array([self.green_channel.unit_map.evaluate(x) for x in xvals])
        b = np.array([self.blue_channel.unit_map.evaluate(x) for x in xvals])
        lum = list(self.luminance_red * r + self.luminance_green * g + self.luminance_blue * b)
        self.luminance.unit_map.points = zip(xvals, lum)

    def _rgb_background_changed(self):
        if self.rgb_background == 'RGB tint':
            self.red_channel.background_color = red_bg
            self.green_channel.background_color = green_bg
            self.blue_channel.background_color = blue_bg
        elif self.rgb_background == 'white':
            self.red_channel.background_color = (1,1,1)
            self.green_channel.background_color = (1,1,1)
            self.blue_channel.background_color = (1,1,1)
        else:
            self.red_channel.background_color = (0,0,0)
            self.green_channel.background_color = (0,0,0)
            self.blue_channel.background_color = (0,0,0)

    def _rgb_line_color_changed(self):
        if self.rgb_line_color == 'RGB':
            self.red_channel.line_color = (1,0,0)
            self.green_channel.line_color = (0,1,0)
            self.blue_channel.line_color = (0,0,1)
        elif self.rgb_line_color == 'white':
            self.red_channel.line_color = (1,1,1)
            self.green_channel.line_color = (1,1,1)
            self.blue_channel.line_color = (1,1,1)
        else:
            self.red_channel.line_color = (0,0,0)
            self.green_channel.line_color = (0,0,0)
            self.blue_channel.line_color = (0,0,0)

    def _grid_color_changed(self):
        if self.grid_color == 'black':
            self.red_channel.grid_color = (0,0,0)
            self.green_channel.grid_color = (0,0,0)
            self.blue_channel.grid_color = (0,0,0)
        elif self.grid_color == 'white':
            self.red_channel.grid_color = (1,1,1)
            self.green_channel.grid_color = (1,1,1)
            self.blue_channel.grid_color = (1,1,1)

    #-----------------------------------------------------------------------
    # Public methods
    #-----------------------------------------------------------------------

    def reset_arrays(self):
        self.red_channel.unit_map.reset()
        self.green_channel.unit_map.reset()
        self.blue_channel.unit_map.reset()

    #-----------------------------------------------------------------------
    # Private methods
    #-----------------------------------------------------------------------

    def _segment_map(self):
        red_list = self.red_channel.unit_map._convert_to_segments()
        green_list = self.green_channel.unit_map._convert_to_segments()
        blue_list = self.blue_channel.unit_map._convert_to_segments()
        segment_map = dict(red=red_list, green=green_list, blue=blue_list)
        return segment_map


if __name__ == "__main__":
    
    colormap_editor = ColormapEditor()
    colormap_editor.configure_traits()
