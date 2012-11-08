
from __future__ import with_statement

from math import sqrt

from traits.api import List, Tuple, Int, Instance, Enum, Float, \
            Bool, Property, Event, Str, Trait, on_trait_change
from enable.api import Component, KeySpec, BasicEvent
from kiva.trait_defs.api import KivaFont
from pyface.action.api import Action, MenuManager, Separator

from unit_map import UnitMap


point_fmt = "(%.3f,%.3f)"


class UnitMapPlotter(Component):

    unit_map = Instance(UnitMap, ())

    font = KivaFont("modern 10")

    # A text label drawn in the upper left corner.
    label = Trait(None, None, Str)

    marker_size = Int(7)

    background_color = Tuple((1.0, 1.0, 1.0))  # FIXME: Use a Color trait?
    line_color = Tuple((0.0, 0.0, 0.0))
    grid_color = Tuple((0.0, 0.0, 0.0))

    grid_resolutions = List([1, 2, 4, 5, 8, 10, 16, 20, 40, 50])
    grid_resolution_index = Int(5)

    _points = Property(List(Tuple),
                       depends_on=['unit_map.points', 'width', 'height'])

    def draw(self, gc, view_bounds=None, mode="default"):
        delta = self.marker_size / 2
        w = self.width - 2 * delta
        h = self.height - 2 * delta
        with gc:
            gc.translate_ctm(self.x + delta, self.y + delta)
            # Background color.
            gc.set_fill_color(self.background_color)
            gc.move_to(0, 0)
            gc.line_to(w, 0)
            gc.line_to(w, h)
            gc.line_to(0, h)
            gc.line_to(0, 0)
            gc.fill_path()
            # Draw the border of the grid.
            gc.set_fill_color((0.1, 0.1, 0.1))
            gc.move_to(0, 0)
            gc.line_to(w, 0)
            gc.line_to(w, h)
            gc.line_to(0, h)
            gc.line_to(0, 0)
            gc.stroke_path()

            if self.label:
                gc.set_font(self.font)
                gc.set_fill_color(self.grid_color + (0.5,))
                gc.show_text(self.label, (5, h - 15))

            # Draw the grid.
            res = self.grid_resolutions[self.grid_resolution_index]
            # Vertical grid lines:
            for k in range(1, res):
                if 2 * k == res:
                    gc.set_line_width(1.5)
                    gc.set_stroke_color(self.grid_color + (0.85,))
                else:
                    gc.set_line_width(1.0)
                    gc.set_stroke_color(self.grid_color + (0.5,))
                r = k * w / float(res)
                gc.move_to(r, 0)
                gc.line_to(r, h)
                gc.stroke_path()
            # Horizontal grid lines:
            for k in range(1, res):
                if 2 * k == res:
                    gc.set_line_width(1.5)
                    gc.set_stroke_color(self.grid_color + (0.85,))
                else:
                    gc.set_line_width(1.0)
                    gc.set_stroke_color(self.grid_color + (0.5,))
                r = k * h / float(res)
                gc.move_to(0, r)
                gc.line_to(w, r)
                gc.stroke_path()

            # Draw the lines.
            gc.set_stroke_color(self.line_color)
            gc.set_line_width(3.0)
            gc.move_to(*self._points[0])
            for point in self._points[1:]:
                gc.line_to(*point)
            gc.stroke_path()
            # Draw the point markers.
            gc.set_line_width(1.0)
            for k, point in enumerate(self._points):
                x = point[0] - delta
                y = point[1] - delta
                gc.set_fill_color(self.line_color)
                gc.rect(x, y, 2 * delta, 2 * delta)
                gc.draw_path()

    # @cached_property
    def _get__points(self):
        delta = self.marker_size / 2
        w = self.width - 2 * delta
        h = self.height - 2 * delta
        _points = [(p[0] * w, p[1] * h) for p in self.unit_map.points]
        return _points

    @on_trait_change('unit_map, unit_map.points')
    def data_changed(self):
        # self._compute_screen_points()
        self.request_redraw()
        self.updated = True

    @on_trait_change('background_color, line_color, grid_color')
    def color_changed(self):
        self.request_redraw()

    def _grid_resolution_index_changed(self):
        self.request_redraw()


# FIXME: UnitMapEditor should be a subclass of UnitMapPlotter.

class UnitMapEditor(Component):

    event_state = Enum('normal', 'over', 'drag')

    reset_key = Instance(KeySpec, args=("r",))
    delete_key = Instance(KeySpec, args=("Delete",))
    add_key = Instance(KeySpec, args=("Enter",))
    invert_key = Instance(KeySpec, args=("v",))
    flip_key = Instance(KeySpec, args=("h",))
    power_key = Instance(KeySpec, args=("p",))
    log_key = Instance(KeySpec, args=("l",))
    increase_grid_key = Instance(KeySpec, args=("g",))
    decrease_grid_key = Instance(KeySpec, args=("G", "Shift",))
    snap_enable_key = Instance(KeySpec, args=("s",))
    snap_disable_key = Instance(KeySpec, args=("S", "Shift"))
    transpose_key = Instance(KeySpec, args=("t",))

    menu = Instance(MenuManager)
    selected_menu = Instance(MenuManager)

    menu_event = Instance(BasicEvent)

    unit_map = Instance(UnitMap, ())

    font = KivaFont("modern 10")

    # A text label drawn in the upper left corner.
    label = Trait(None, None, Str)

    marker_size = Int(7)

    background_color = Tuple  # FIXME: Use a Color trait?
    selected_color = Tuple((0.0, 1.0, 1.0))
    line_color = Tuple((0.0, 0.0, 0.0))
    grid_color = Tuple((0.0, 0.0, 0.0))

    grid_resolutions = List([1, 2, 4, 5, 8, 10, 16, 20, 40, 50])
    grid_resolution_index = Int(5)

    snap_to_grid = Bool(False)

    clean_tol = Float(1e-5)

    loglike_scale = Float(sqrt(2.0))
    power = Float(2.0)

    status_text = Str('')

    updated = Event

    _points = Property(List(Tuple),
                       depends_on=['unit_map.points', 'width', 'height'])

    _near_threshold = Int(10)

    _drag_index = Int(0)
    _over_index = Int(-1)

    def make_loglike(self):
        beta = self.loglike_scale
        n = len(self.unit_map.points) - 1
        if beta == 1.0:
            points = [(float(k) / n, float(k) / n) for k in range(n + 1)]
        else:
            b = beta ** n - 1.0
            points = []
            x = 0.0
            for k in range(0, n + 1):
                y = float(k) / n
                x = (beta ** k - 1) / b
                points.append((x, y))
        self.unit_map.points = points
        self.set_status_text("Made log-like")
        self.updated = True

    def make_power(self):
        self.unit_map.points = [(x, x ** self.power)
                                for (x, y) in self.unit_map.points]
        self.set_status_text("Made power")
        self.updated = True

    def do_transpose(self):
        if self.unit_map.invertible():
            if self.unit_map.points[0][1] == 1.0:
                pts = reversed(self.unit_map.points)
            else:
                pts = self.unit_map.points
            self.unit_map.points = [(y, x) for (x, y) in pts]
            self.set_status_text("Transposed")
        else:
            self.set_status_text("Can't transpose, not invertible")
        self.updated = True

    def do_vertical_flip(self):
        self.unit_map.invert()
        self.set_status_text("Vertically flipped")
        self.updated = True

    def do_horizontal_flip(self):
        self.unit_map.flip()
        self.set_status_text("Horizontally flipped")
        self.updated = True

    def do_clean(self):
        num_deleted = self.unit_map.clean(tol=self.clean_tol)
        if num_deleted > 0:
            s = 's' * (num_deleted > 1)
            self.set_status_text("%d point%s deleted" % (num_deleted, s))
        else:
            self.set_status_text("No points deleted")
        self.updated = True

    def use_next_grid_size(self, increment=1):
        self.grid_resolution_index = \
                ((self.grid_resolution_index + increment) %
                 len(self.grid_resolutions))
        self.request_redraw()

    def draw(self, gc, view_bounds=None, mode="default"):
        delta = self.marker_size / 2
        w = self.width - 2 * delta
        h = self.height - 2 * delta
        with gc:
            gc.translate_ctm(self.x + delta, self.y + delta)
            # Background color.
            gc.set_fill_color(self.background_color)
            gc.move_to(0, 0)
            gc.line_to(w, 0)
            gc.line_to(w, h)
            gc.line_to(0, h)
            gc.line_to(0, 0)
            gc.fill_path()
            # Draw the border of the grid.
            gc.set_fill_color((0.1, 0.1, 0.1))
            gc.move_to(0, 0)
            gc.line_to(w, 0)
            gc.line_to(w, h)
            gc.line_to(0, h)
            gc.line_to(0, 0)
            gc.stroke_path()

            if self.label:
                gc.set_font(self.font)
                gc.set_fill_color(self.grid_color + (0.5,))
                gc.show_text(self.label, (5, h - 15))

            # Draw the grid.
            res = self.grid_resolutions[self.grid_resolution_index]
            # Vertical grid lines:
            for k in range(1, res):
                if 2 * k == res:
                    gc.set_line_width(1.5)
                    gc.set_stroke_color(self.grid_color + (0.85,))
                else:
                    gc.set_line_width(1.0)
                    gc.set_stroke_color(self.grid_color + (0.5,))
                r = k * w / float(res)
                gc.move_to(r, 0)
                gc.line_to(r, h)
                gc.stroke_path()
            # Horizontal grid lines:
            for k in range(1, res):
                if 2 * k == res:
                    gc.set_line_width(1.5)
                    gc.set_stroke_color(self.grid_color + (0.85,))
                else:
                    gc.set_line_width(1.0)
                    gc.set_stroke_color(self.grid_color + (0.5,))
                r = k * h / float(res)
                gc.move_to(0, r)
                gc.line_to(w, r)
                gc.stroke_path()

            # Draw the lines.
            gc.set_stroke_color(self.line_color)
            gc.set_line_width(3.0)
            gc.move_to(*self._points[0])
            for point in self._points[1:]:
                gc.line_to(*point)
            gc.stroke_path()
            # Draw the point markers.
            gc.set_line_width(1.0)
            for k, point in enumerate(self._points):
                x = point[0] - delta
                y = point[1] - delta
                if k == self._over_index:
                    gc.set_fill_color(self.selected_color)
                else:
                    gc.set_fill_color(self.line_color)
                gc.rect(x, y, 2 * delta, 2 * delta)
                gc.draw_path()

    def normal_mouse_move(self, event):
        #over = self._over_point(event)
        over = self._closest_within_threshold(event)
        if over is not None:
            self._over_index = over
            self.event_state = 'over'
            self.request_redraw()

    def normal_key_pressed(self, event):
        if self.add_key.match(event):
            delta = self.marker_size / 2
            x = event.x - delta
            w = self.width - 2 * delta
            xx = float(x) / w
            if 0.0 <= xx <= 1.0:
                yy = self.unit_map.evaluate(xx)
                self.unit_map.add_point((xx, yy))
            self.updated = True
        elif self.invert_key.match(event):
            self.do_vertical_flip()
        elif self.flip_key.match(event):
            self.do_horizontal_flip()
        elif self.power_key.match(event):
            self.make_power()
        elif self.log_key.match(event):
            self.make_loglike()
        elif self.reset_key.match(event):
            self.unit_map.reset()
            self.over_index = -1
            self.event_state = 'normal'
            self.updated = True
        elif self.increase_grid_key.match(event):
            self.use_next_grid_size()
        elif self.decrease_grid_key.match(event):
            self.use_next_grid_size(increment=-1)
        elif self.snap_enable_key.match(event):
            self.snap_to_grid = True
        elif self.snap_disable_key.match(event):
            self.snap_to_grid = False
        elif self.transpose_key.match(event):
            self.do_transpose()

    def normal_left_dclick(self, event):
        """Left double click: add a point."""
        # FIXME: Duplicated code here and in the key press handler.
        delta = self.marker_size / 2
        x = event.x - delta
        w = self.width - 2 * delta
        xx = float(x) / w
        if 0.0 <= xx <= 1.0:
            yy = self.unit_map.evaluate(xx)
            self.unit_map.add_point((xx, yy))
            self.set_status_text("Added a point at " + point_fmt % (xx, yy))
        self.updated = True

    def normal_right_up(self, event):
        """Activate the menu."""
        self.menu_event = event
        menu = self.menu.create_menu(event.window.control)
        menu.show(event.x, event.window._flip_y(event.y))

    def over_mouse_move(self, event):
        # over = self._over_point(event)
        over = self._closest_within_threshold(event)
        if over is None:
            self._over_index = -1
            self.event_state = 'normal'
            self.request_redraw()
        elif over != self._over_index:
            # Not likely, but just in case...
            self._over_index = over
            self.request_redraw()

    def over_left_down(self, event):
        self._drag_index = self._over_index
        self.event_state = 'drag'

    def over_right_up(self, event):
        """Activate the selected menu."""
        self.menu_event = event
        menu = self.selected_menu.create_menu(event.window.control)
        menu.show(event.x, event.window._flip_y(event.y))

    def do_delete_selected_point(self):
        if 0 < self._over_index < len(self._points) - 1:
            self.unit_map.points.pop(self._over_index)
            self._over_index = -1
            self.event_state = 'normal'
            self.set_status_text('Deleted the selected point')
            self.updated = True

    def over_key_pressed(self, event):
        # FIXME: Code duplication in this function and normal_key_pressed.
        if self.delete_key.match(event):
            self.do_delete_selected_point()
        elif self.invert_key.match(event):
            self.do_vertical_flip()
            self.event_state = 'normal'
        elif self.flip_key.match(event):
            self.do_horizontal_flip()
            self.over_index = -1
            self.event_state = 'normal'
        elif self.power_key.match(event):
            self.make_power()
            self._over_index = -1
            self.event_state = 'normal'
        elif self.log_key.match(event):
            self.make_loglike()
            self._over_index = -1
            self.event_state = 'normal'
        elif self.reset_key.match(event):
            self.unit_map.reset()
            self.over_index = -1
            self.event_state = 'normal'
        elif self.increase_grid_key.match(event):
            self.use_next_grid_size()
        elif self.decrease_grid_key.match(event):
            self.use_next_grid_size(increment=-1)
        elif self.snap_enable_key.match(event):
            self.snap_to_grid = True
        elif self.snap_disable_key.match(event):
            self.snap_to_grid = False
        elif self.transpose_key.match(event):
            self.do_transpose()

    def over_mouse_leave(self, event):
        self.event_state = 'normal'
        self._over_index = -1
        self.request_redraw()

    def drag_mouse_move(self, event):
        k = self._drag_index
        delta = self.marker_size / 2
        x = event.x - delta - 1
        y = event.y - delta - 1
        if k == 0:
            left_bound = self._points[0][0]
            right_bound = left_bound
        elif k == len(self._points) - 1:
            right_bound = self._points[-1][0]
            left_bound = right_bound
        else:
            left_bound = self._points[k - 1][0]
            right_bound = self._points[k + 1][0]

        if x < left_bound:
            x = left_bound
        if x > right_bound:
            x = right_bound
        if y < 0:
            y = 0
        h = self.height - 2 * delta
        if y > h:
            y = h

        self._points[k] = (x, y)
        w = self.width - 2 * delta
        h = self.height - 2 * delta
        xx = float(x) / w
        yy = float(y) / h
        self.unit_map.points[k] = (xx, yy)
        self.request_redraw()
        self.set_status_text("Moved point to " + point_fmt %
                             self.unit_map.points[k])
        self.updated = True

    def drag_mouse_leave(self, event):

        i = self._drag_index
        self.release_dragged_point(i)

        self.event_state = 'normal'
        self._drag_index = -1
        self._over_index = -1
        self.request_redraw()

    def drag_left_up(self, event):

        i = self._drag_index
        self.release_dragged_point(i)

        over = self._over_point(event)
        if over is not None:
            self.event_state = 'over'
            self._over_index = over
        else:
            self.event_state = 'normal'
            self._over_index = -1
        self._drag_index = -1
        self.request_redraw()

    def release_dragged_point(self, i):
        if self.snap_to_grid:
            i = self._drag_index
            x, y = self.unit_map.points[i]
            res = self.grid_resolutions[self.grid_resolution_index]
            xx = round(x * res) / res
            yy = round(y * res) / res
            if (i < len(self.unit_map.points) - 1 and
                    xx > self.unit_map.points[i + 1][0]):
                xx = self.unit_map.points[i + 1][0]
            if i > 0 and xx < self.unit_map.points[i - 1][0]:
                xx = self.unit_map.points[i - 1][0]
            self.unit_map.points[i] = (xx, yy)
        self.set_status_text("Moved point to " + point_fmt %
                             self.unit_map.points[i])
        self.updated = True

    def set_status_text(self, text):
        if self.label is not None:
            prefix = "%s: " % self.label
        else:
            prefix = ""
        self.status_text = prefix + text

    # @cached_property
    def _get__points(self):
        delta = self.marker_size / 2
        w = self.width - 2 * delta
        h = self.height - 2 * delta
        _points = [(p[0] * w, p[1] * h) for p in self.unit_map.points]
        return _points

    @on_trait_change('unit_map, unit_map.points')
    def data_changed(self):
        # self._compute_screen_points()
        self.request_redraw()
        self.updated = True

    @on_trait_change('background_color, line_color, grid_color')
    def color_changed(self):
        self.request_redraw()

    def _grid_resolution_index_changed(self):
        self.request_redraw()

    def _menu_default(self):
        root = MenuManager(
            Action(name="Vertical flip",
                   on_perform=self.do_vertical_flip),
            Action(name="Horizontal flip",
                   on_perform=self.do_horizontal_flip),
            Action(name="Transpose (flip around y=x)",
                   on_perform=self.do_transpose),
            Separator(),
            Action(name="Make log-like", on_perform=self.make_loglike),
            Action(name="Make power function", on_perform=self.make_power),
            Action(name="Clean", on_perform=self.do_clean),
            )
        return root

    def _selected_menu_default(self):
        root = MenuManager(name="selected_menu")
        actions = [
            Action(name="Delete point",
                   on_perform=self.do_delete_selected_point),
            ]
        for a in actions:
            root.append(a)
        return root

    def _is_near_point(self, point, event):
        delta = self.marker_size / 2
        event_point = (event.x - delta, event.y - delta)
        near = max(abs(point[0] - event_point[0]),
                    abs(point[1] - event_point[1])) \
                        <= self._near_threshold
        return near

    def _over_point(self, event):
        # This stops at the first point within the threshold.
        # This is not correct when the points are close together.
        for i, point in enumerate(self._points):
            if self._is_near_point(point, event):
                result = i
                break
        else:
            result = None
        return result

    def _closest_within_threshold(self, event):
        """
        Of all the points within self.threshold of the event, return the
        closest.
        Returns None if no points are within self.threshold.
        """
        delta = self.marker_size / 2
        closest = None
        for i, point in enumerate(self._points):
            dist2 = ((point[0] - (event.x - delta)) ** 2 +
                     (point[1] - (event.y - delta)) ** 2)
            if dist2 < self._near_threshold ** 2:
                if closest is None or dist2 < closest_dist2:
                    closest = i
                    closest_dist2 = dist2
        return closest
