"""
An application for creating and editing colormaps.

Warren Weckesser
Enthought, Inc.
December, 2009
"""

from __future__ import with_statement

from math import sqrt

import types
from os.path import basename

from enthought.traits.api import HasTraits, Instance, Float, Property, Str, Dict, \
        List, Bool, Int, HTML, on_trait_change, cached_property
from enthought.traits.ui.api import Item, VGroup, HGroup, View, Handler, Label, \
        InstanceEditor, EnumEditor, RangeEditor, UItem, spring

from enthought.traits.ui.menu import Action, Menu, MenuBar
from enthought.pyface.action.api import Group as ActionGroup
from enthought.pyface.api import FileDialog, OK, error


from enthought.chaco.api import DataRange1D, ColorMapper
from enthought.chaco.ticks import ShowAllTickGenerator
from enthought.chaco.default_colormaps import color_map_name_dict

import chacoled
from colormap_editor import ColormapEditor


def segments_to_points(segs):
    points = []
    for seg in segs:
        points.append((seg[0],seg[1]))
        if seg[1] != seg[2]:
            points.append((seg[0],seg[2]))
    return points


class HelpDialog(HasTraits):
    """
    A Help Dialog for the Colormap Editor application.  Creating an instance of this
    class will open a new window containing a description of the program.
    
    """

    help_text = r"""
    <html>
    <body text="#000830" bgcolor="white">
    <center><b>chacoled %(version)s</b></center><br />
    <center><b>Chaco Colormap Editor</b></center>
    <p>This program is a tool for creating and editing Chaco colormaps.
    </p>
    <p>
    Click on a plot to make it the active plot.
    </p>
    <p>
    Click and drag points to change the shape of the curve.
    </p>
    <p>
    <i>Keys</i>
    <table border="1">
    <tr><td>Enter</td>
        <td>Add a point to the curve.</td>
    </tr>
    <tr>
        <td>Delete</td>
        <td>Delete the currently selected point (i.e. the point over which the mouse
        pointer is currently hovering).</td>
    </tr>
    <tr>
        <td>h</td>
        <td>Flip the curve horizontally: x -> 1 - x.</td>
    </tr>
    <tr>
        <td>v</td>
        <td>Invert the curve vertically: y -> 1 - y.</td>
    </tr>
    <tr>
        <td>t</td>
        <td>Transpose the curve about y = x: (x,y) -> (y,x).
            Only valid if the transposed curve is still a valid unit map.</td>
    </tr>
    <tr>
        <td>p</td>
        <td>Change shape to a parabola; all current points are modified
            to<br /> y = x<sup>2</sup>.</td>
    </tr>
    <tr>
        <td>l</td>
        <td>Change shape to "log-like": all current points are modified
            so that the vertical spacing is uniform while the ratio of the
            lengths of adjacent horizontal intervals is constant. 
            </td>
    </tr>
    <tr>
        <td>r</td>
        <td>Reset the curve to the identity: y = x.</td>
    </tr>
    <tr>
        <td>g, G</td>
        <td>Cycle thought the predefined grid levels.</td>
    </tr>
    <tr>
        <td>s, S</td>
        <td>Set and unset (resp.) the 'snap to grid' mode.
            When set, points released at the end of a drag
            will move to the nearest vertex of the current grid.</td>
    <tr>
    </table>
    </p>
    </body>
    </html>
    """ % dict(version=chacoled.__version__)
    t1 = HTML(help_text)
    
    view = View(
               Item('t1',show_label=False,width=540,height=500),
               title='chacoled - Help',
               resizable=True,
               buttons=['OK'])
    
    def __init__(self,**kwargs):
        super(HelpDialog,self).__init__(**kwargs)
        self.configure_traits()


class Preferences(HasTraits):
    """
    This class provides a UI that changes some setting for a list of UnitMapEditors.
    """

    colormap_editor = Instance(ColormapEditor)
    
    unit_map_editors = Property(List, depends_on=['colormap_editor'])

    snap_to_grid = Bool
    
    # This is the comment displayed to the right of the snap-to-grid check box.
    # A Label in the view would be simpler, but Label objects have vertical
    # alignment issues--they don't align the text baseline with Item labels.
    snap_to_grid_comment = Str("(Only when a dragged point is released.)")

    clean_tol = Float(0.005)

    loglike_scale = Float(sqrt(2.0))
    power = Float(2.0)

    grid_resolutions = List

    grid_resolution = Int

    grid_spacing = Float
    
    # A Str Traits, because 'Label' UI elements don't work quite right.
    lum_coeff_label = Str('Luminance coefficients:')

    green_max = Property(Float, depends_on=['colormap_editor.luminance_red'])

    def trait_view(self, parent=None):
        view = \
            View(
                HGroup(
                    Item('snap_to_grid', label="Snap-to-grid"),
                    Item('snap_to_grid_comment', show_label=False, style='readonly'),
                    ),
                HGroup(
                    Item('grid_resolution', editor=EnumEditor(name='grid_resolutions')),
                    Item('grid_spacing', style='readonly'),
                    ),
                '_',
                VGroup(
                    Item('clean_tol', label='Tolerance for clean'),
                    Item('loglike_scale', label='Log-like scale',
                            editor=RangeEditor(low=0.5, high=2.0, format="%5.3f")),
                    Item('power', label='Power',
                            editor=RangeEditor(low=0.125, high=8.0, format="%5.3f")),
                ),
                '_',
                VGroup(
                    Item('object.colormap_editor.rgb_background', label='Background color'),
                    Item('object.colormap_editor.rgb_line_color', label='Line color'),
                    Item('object.colormap_editor.grid_color', label='Grid color'),
                    Item('object.colormap_editor.show', label='Show'),
                ),
                '_',
                VGroup(
                    UItem('lum_coeff_label', style='readonly'),
                    VGroup(
                        Item('object.colormap_editor.luminance_red', label='Red',
                                editor=RangeEditor(low=0.0, label_width=50)),
                        Item('object.colormap_editor.luminance_green', label='Green',
                                enabled_when='green_max != 0',
                                editor=RangeEditor(low=0.0, high_name='green_max',
                                                            label_width=50)),
                        Item('object.colormap_editor.luminance_blue', label='Blue',
                                enabled_when='False'),
                    ),
                ),
                title='Preferences',
                buttons=['OK'],
            )
        return view

    #-----------------------------------------------------------------------
    # Trait change handlers
    #-----------------------------------------------------------------------

    @on_trait_change('clean_tol')
    def changed_clean_tol(self):
        for ume in self.unit_map_editors:
            ume.clean_tol = self.clean_tol

    @on_trait_change('snap_to_grid')
    def changed_snap_to_grid(self):
        for ume in self.unit_map_editors:
            ume.snap_to_grid = self.snap_to_grid   

    @on_trait_change('loglike_scale')
    def changed_loglike_scale(self):
        for ume in self.unit_map_editors:
            ume.loglike_scale = self.loglike_scale

    @on_trait_change('power')
    def changed_power(self):
        for ume in self.unit_map_editors:
            ume.power = self.power

    @on_trait_change('grid_resolution')
    def changed_grid_resolution(self):
        self.grid_spacing = 1.0/self.grid_resolution
        for ume in self.unit_map_editors:
            ume.grid_resolution_index = \
                ume.grid_resolutions.index(self.grid_resolution)
        lum = self.colormap_editor.luminance
        lum.grid_resolution_index = lum.grid_resolutions.index(self.grid_resolution)

        # FIXME: The ColorMapEditor's API should be extended to make the following
        # more concise.
        self.colormap_editor.colorbar._grid.grid_interval = self.grid_spacing
        if self.grid_resolution % 5 == 0 or self.grid_resolution == 1:
            self.colormap_editor.colorbar._axis.tick_generator =\
                ShowAllTickGenerator(positions=[0,0.2, 0.4, 0.6, 0.8, 1.0])
        else:
            self.colormap_editor.colorbar._axis.tick_generator =\
                ShowAllTickGenerator(positions=[0,0.25, 0.5, 0.75, 1.0])
        self.colormap_editor.colorbar._axis.updated = True

    #-----------------------------------------------------------------------
    # Traits property methods
    #-----------------------------------------------------------------------

    @cached_property
    def _get_unit_map_editors(self):
        unit_map_editors = [self.colormap_editor.red_channel,
                            self.colormap_editor.green_channel,
                            self.colormap_editor.blue_channel]
        return unit_map_editors

    def _get_green_max(self):
        green_max = 1.0 - self.colormap_editor.luminance_red
        return green_max
    

class ColormapAppHandler(Handler):

    def import_colormap(self, info):
        """Implements the "File / Import" menu item."""

        dialog = FileDialog(parent=info.ui.control,
                            action='open',
                            title='Import colormap file')
        if dialog.open() == OK:
            if dialog.path.endswith('.cmap'):
                # Read the colormap data file.
                # First read the name from the first line, then use ColorMap.from_file()
                # to actually load the color map.
                with open(dialog.path, 'r') as f:
                    name = f.readline().strip()
                color_mapper = ColorMapper.from_file(dialog.path)
                info.object._load_color_mapper(name, color_mapper)
            elif dialog.path.endswith('.py'):
                # Look for a function that is a color map factory that was
                # created by this application; these are functions with the
                # attribute `_colormap_data`.
                
                # Get the basename, and chop off '.py'.
                name = basename(dialog.path)[:-3]

                # Try to read the python file.
                try:
                    f = open(dialog.path, 'r')
                except IOError:
                    error(None, 'Unable to read "%s"' % dialog.path, 'File Error')
                    return
                # Try to import the script.
                module = types.ModuleType(str(name))
                module.__file__ = dialog.path
                try:
                    exec f in module.__dict__
                except Exception, e:
                    error(None,'An error occurred while importing "%s".\n\n%s' %
                                (dialog.path,e), 'Import Error')
                    return
                finally:
                    f.close()
                for name, obj in module.__dict__.items():
                    if isinstance(obj, types.FunctionType) and \
                                                hasattr(obj, '_colormap_data'):
                        # Found the function.  Call it, and load the ColorMapper
                        # that it generates. 
                        cm = obj(range=DataRange1D(low=0, high=1))
                        info.object._load_color_mapper(name, cm)
                        break
                else:
                    msg1 = 'A ColorMapper factory function was not found in "%s".\n\n' % \
                                dialog.path
                    msg2 = 'Such a function has the attribute "_colormap_data".'
                    error(None, msg1 + msg2, 'Not found')
            else:
                msg = 'The file "%s" has an unknown file extension.\n\n' % dialog.path
                msg = msg + 'Known extensions are:\n'
                msg = msg + '  .cmap\n        A Chaco-format colormap file\n'
                msg = msg + '  .py \n        The python file must contain a function'
                msg = msg + ' that was created by this program.'   
                error(None, msg, 'Unknown file extension')                


    def export_chaco_file(self, info):
        """Implements the "File / Export / Chaco file format" menu item."""

        dialog  = FileDialog(parent=info.ui.control,
                                default_filename=info.object.name + ".cmap",
                                action='save as',
                                title='Chaco colormap data file')
        if dialog.open() == OK:
            f = open(dialog.path,'w')
            f.write('%s\n' % info.object.name)

            # Small value used to ensure that the offset values (i.e. the `t`
            # values in the loop below) are strictly increasing.
            eps = 1e-8

            # The colormap editor's UnitMaps.
            red_um = info.object.colormap_editor.red_channel.unit_map
            green_um = info.object.colormap_editor.green_channel.unit_map
            blue_um = info.object.colormap_editor.blue_channel.unit_map

            channels = [(red_um.points[:],   red_um),
                        (green_um.points[:], green_um),
                        (blue_um.points[:],  blue_um)]

            # Build a list of 4-tuples of the form (t,r,g,b), where t increases
            # from 0 to 1.  tstar and eps are used to add small perturbations that
            # convert discontinuities into very steep segments. (Actually, I'm not
            # sure this is necessary; I don't know if Chaco handles discontinuities
            # in the file format.)
            tprev = None
            while len(channels[0][0]) > 0:
                t = min(channel[0][0][0] for channel in channels)
                if tprev and t <= tprev:
                    tstar = tprev + eps
                else:
                    tstar = t
                values = [tstar]
                for k in range(len(channels)):
                    points, um = channels[k]
                    if points[0][0] == t:
                        point = points.pop(0)
                        values.append(point[1])
                    else:
                        value = um.evaluate(tstar)
                        values.append(value)
                fmt =' '.join(["%.12f"]*len(values)) + '\n'
                s = fmt % tuple(values)
                f.write(s)
                tprev = tstar

            f.close()

    def export_chaco_python(self, info):
        """Implements the "File / Export / Chaco python code" menu item."""

        dialog  = FileDialog(parent=info.ui.control, 
                                default_filename=info.object.name + ".py",
                                action='save as',
                                title='Chaco python file')
        if dialog.open() == OK:
            # The data is attached to the function as an attribute.  This will allow a
            # program to import a module, look for functions in the module that have
            # the _colormap_data attribute and recover the data without having to
            # call the function.
            f = open(dialog.path,'w')
            f.write('\n')
            f.write('from enthought.chaco.api import ColorMapper\n\n')
            f.write('def %s(range, **traits):\n' % info.object.name)
            f.write('    """Generator for the colormap "%s"."""\n' % info.object.name)
            f.write('    return ColorMapper.from_segment_map(%s._colormap_data, range=range, **traits)\n\n' % info.object.name)
            f.write('%s._colormap_data = ' % info.object.name)
            segment_map = info.object.colormap_editor._segment_map()
            seg_code = '%r' % segment_map
            seg_code = seg_code.replace("'red'","\n        'red'")
            seg_code = seg_code.replace("'green'","\n        'green'")
            seg_code = seg_code.replace("'blue'","\n        'blue'")
            seg_code = seg_code.replace("}","\n        }")
            f.write(seg_code)
            f.close()

    def preferences(self, info):
        """Implements the "File / Preferences" menu item."""
        info.object.preferences.edit_traits()


    def exit(self, info):
        info.ui.dispose()

    def help(self, info):
        HelpDialog()


class ColormapApp(HasTraits):
    """Application for creating and editing colormaps."""

    # User-defined name of the color map.
    name = Str

    # Dictionary of colormap names and corresponding functions, imported from Chaco.
    colormap_dict = Dict

    # The list of the keys in colormap_dict.
    colormap_names = Property(List(Str), depends_on=['colormap_dict'])
    
    # Name of the Chaco colormap selected by the user.
    colormap_name = Str

    # The editor of the color map.
    colormap_editor = Instance(ColormapEditor, ())

    preferences = Instance(Preferences)
    
    status_text = Str('')

    def trait_view(self, parent=None):
        file_group = ActionGroup(
                        Action(name='Import', action='import_colormap'),
                        Menu(
                            ActionGroup(
                                Action(name='Chaco file format', action='export_chaco_file'),
                                Action(name='Chaco python code', action='export_chaco_python'),
                                ),
                            name='Export',
                            )
                        )
        pref_group = ActionGroup(
                        Action(name='Preferences', action='preferences'))
        app_group = ActionGroup(
                        Action(name='Exit', action='exit'))
        help_group = ActionGroup(
                        Action(name='Help', action='help'))
        file_menu = Menu(file_group, pref_group, app_group, name='File')
        help_menu = Menu(help_group, name='Help')
        menu_bar = MenuBar(file_menu, help_menu)
        view = View(
                    VGroup(
                        HGroup(
                            Item('name'),
                            spring,
                            Item('colormap_name', label='Load Chaco colormap',
                                    editor=EnumEditor(name='colormap_names')),
                            ),
                        Item('colormap_editor', editor=InstanceEditor(),
                                style='custom',
                                show_label=False),
                        ),
                    resizable=True,
                    handler=ColormapAppHandler(),
                    menubar=menu_bar,
                    statusbar='status_text',
                    title="chacoled %s" % chacoled.__version__,
                    )
        return view


    #------------------------------------------------------------------
    # Trait defaults
    #------------------------------------------------------------------
    
    def _name_default(self):
        return "Untitled"

    def _colormap_dict_default(self):
        return color_map_name_dict

    def _preferences_default(self):
        pref = Preferences(colormap_editor=self.colormap_editor)
        tmp = self.colormap_editor.red_channel
        pref.grid_resolutions = tmp.grid_resolutions
        pref.grid_resolution = tmp.grid_resolutions[tmp.grid_resolution_index]
        return pref

    #------------------------------------------------------------------
    # Trait Property methods
    #------------------------------------------------------------------

    def _get_colormap_names(self):
        names = sorted(self.colormap_dict.keys())
        names.insert(0, 'none')
        return names

    #------------------------------------------------------------------
    # Trait change handlers
    #------------------------------------------------------------------

    def _colormap_name_changed(self):
        if self.colormap_name not in ['','none']:
            func = self.colormap_dict[self.colormap_name]

            # Create the ColorMapper object.
            cm = func(range=DataRange1D(low=0, high=1))
            
            self._load_color_mapper(self.colormap_name, cm)

    @on_trait_change('colormap_editor.updated')
    def colormap_editor_changed(self):
        # The user has changed the colormap, so set `colormap_name` to 'none',
        # since it is no longer the same as the map that was loaded.
        self.colormap_name = 'none'
        # Hmmm... why doesn't this update the displayed name (at least on a Mac)?

        self.status_text = self.colormap_editor.status_text

    #------------------------------------------------------------------
    # Private methods
    #------------------------------------------------------------------

    def _load_color_mapper(self, name, color_mapper):
        """Load a ColorMapper instance into the editor."""
        self.name = name
        # Get the dictionary of segment data.
        segs = color_mapper._segmentdata
        # Convert the RGB segments to point lists.
        red_list = segments_to_points(segs['red'])
        green_list = segments_to_points(segs['green'])
        blue_list = segments_to_points(segs['blue'])
        # Assign the lists to the colormap editor's channels.
        self.colormap_editor.red_channel.unit_map.points = red_list
        self.colormap_editor.green_channel.unit_map.points = green_list
        self.colormap_editor.blue_channel.unit_map.points = blue_list
        # This will trigger an update of the color bar.
        # FIXME: This should not be necessary.  Changing `points` in any of the
        # unit maps should propagate up to an event that causes the color bar
        # to update. 
        self.colormap_editor.blue_channel.updated = True
        self.status_text = "Loaded %s" % name


def main():
    app = ColormapApp()
    app.configure_traits()


if __name__ == "__main__":
    main()
