
from traits.api import HasTraits, Instance
from traitsui.api import View, Item, HGroup
from enable.api import ComponentEditor

from unit_map_editor import UnitMapEditor


class Foo(HasTraits):
    
    red_um = Instance(UnitMapEditor)
    green_um = Instance(UnitMapEditor)
    blue_um = Instance(UnitMapEditor)

    
    def trait_view(self, parent=None):
        view = View(
                HGroup(
                    Item('red_um',editor=ComponentEditor(size=(200,200)),
                            show_label=False),
                    Item('green_um',editor=ComponentEditor(size=(200,200)),
                            show_label=False),
                    Item('blue_um',editor=ComponentEditor(size=(200,200)),
                            show_label=False),
                    ),
                resizable=True,
                #width=250,
                #height=250,
                )
        return view

    def _red_um_default(self):
        um = UnitMapEditor(background_color=(1.0,0.2,0.2))
        return um

    def _green_um_default(self):
        um = UnitMapEditor(background_color=(0.2,1.0,0.2))
        return um

    def _blue_um_default(self):
        um = UnitMapEditor(background_color=(0.2,0.2,1.0))
        return um

if __name__ == "__main__":
    f = Foo()
    f.edit_traits()
