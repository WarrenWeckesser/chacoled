"""
This module defines the UnitMap class, and a few utility functions for working
with line segments.
"""

import numpy as np
from traits.api import HasTraits, List, Tuple


def sign(x):
    if x < 0:
        s = -1
    elif x == 0:
        s = 0
    else:
        s = 1
    return s


class UnitMap(HasTraits):
    """A set of points that define a map of the unit interval into itself."""

    # A list of 2-tuples of floats between 0 and 1.  The list of the first elements
    # must be nondecreasing, with points[0][0] = 0 and points[-1][0] = 1.
    # (So there must always be at least two points in the list.)
    points = List(Tuple)

    #-----------------------------------------------------------------------
    # Traits interface
    #-----------------------------------------------------------------------

    def _points_default(self):
        points = [(0.0,0.0), (1.0,1.0)]
        return points

    #-----------------------------------------------------------------------
    # UnitMap public methods
    #-----------------------------------------------------------------------    
    
    def reset(self):
        """Reset the list of points to the initial state."""
        self.points = self._points_default()

    def invert(self):
        self.points = [(x,1-y) for (x,y) in self.points]

    def flip(self):
        self.points = [(1-x,y) for (x,y) in reversed(self.points)]

    def add_point(self, point):
        """Add a point to the list of points."""

        x, y = point
        if x > 1 or x < 0:
            raise ValueError, "x = %f is not valid. x must be between 0 and 1." % x
        if y > 1 or y < 0:
            raise ValueError, "y = %f is not valid. y must be between 0 and 1." % y
        for k, p in enumerate(self.points[1:]):
            if x <= p[0]:
                self.points.insert(k+1, point)
                break
        return k+1

    def delete_point(self, point):
        # Not sure what the API should be.  Might not even need this--just work
        # directly with the list. (But a tightly controlled delete could prevent
        # the first or last points from being deleted.)
        raise NotImplementedError
    
    def is_monotonic(self):
        # Find the first nonzero sign.
        k = 1
        s1 = sign(self.points[k][1] - self.points[k-1][1])
        while s1 == 0 and k < len(self.points)-1:
            k += 1
            s1 = sign(self.points[k][1] - self.points[k-1][1])
        if k == len(self.points):
            return True

        for j in range(k, len(self.points)):
            s = sign(self.points[j][1] - self.points[j-1][1])
            if s != 0 and s != s1:
                mono = False
                break
        else:
            mono = True
        return mono

    def invertible(self):
        """Return a boolean that indicates if the map is invertible.
        
        To be invertible, the map must be monotonic and onto, so the y values at
        the ends must be 0 and 1 or 1 and 0.
        """

        if not self.is_monotonic():
            return False

        result = (self.points[0][1] == 0.0 and self.points[-1][1] == 1.0) \
                    or (self.points[0][1] == 1.0 and self.points[-1][1] == 0.0)
        return result

    def evaluate(self, x):
        # Note that a UnitMap can be multivalued at the ends of a segment,
        # but this function only returns one value.
        if x < 0.0 or x > 1.0:
            raise ValueError, ("x is %f, but evaluate(x) requires 0 <= x <= 1." % x)
        
        if x == 0.0:
            y = self.points[0][1]
        else:
            k = 0
            while x > self.points[k][0]:
                k += 1
            x1, y1 = self.points[k-1]
            x2, y2 = self.points[k]
            y = (y2 - y1)/(x2 - x1)*(x - x1) + y1
        return y

    def compose(self, um):
        """The composition of this unit map with another.
        
        If this map is f and `um` is g, `compose` returns the UnitMap corresponding
        to f(g(x)).
        """
        new_points = []
        # There are always at least two points in self.points, so we can start
        # at k=1 and use k-1 to access the previous point.
        for k in range(1, len(um.points)):
            x0, y0 = um.points[k-1]
            x1, y1 = um.points[k]
            pts = self._points_in_segment(y0, y1)
            pts2 = []
            for x, y in pts:
                if y0 == y1:
                    pts2.append((x0,y))
                    pts2.append((x1,y))
                else:
                    xi = (x - y0)*(x1 - x0)/(y1 - y0) + x0
                    pts2.append((xi,y))
            if new_points and close_enough(new_points[-1],pts2[0], tol=1e-6):
                pts2.pop(0)
            new_points.extend(pts2)
        new_points = clean2(new_points, tol=1e-6)
        composition = UnitMap(points=new_points)
        return composition

    def clean(self, tol=1e-6):
        old_len = len(self.points)
        self.points = clean2(self.points, tol)
        num_deleted = old_len - len(self.points)
        return num_deleted

    #-----------------------------------------------------------------------
    # UnitMap private methods
    #----------------------------------------------------------------------- 

    def _points_in_segment(self, x1, x2):
        decreasing = False
        if x2 < x1:
            x1, x2 = x2, x1
            decreasing = True
        pts = [p for p in self.points if x1 <= p[0] <= x2]
        if not pts or pts[0][0] != x1:
            pts.insert(0, (x1, self.evaluate(x1)))
        if pts[-1][0] != x2:
            pts.append((x2, self.evaluate(x2)))
        if decreasing:
            pts.reverse()
        return pts

    def __repr__(self):
        s = "UnitMap(points=%s)" % self.points
        return s

    def __str__(self):
        return repr(self)


#---------------------------------------------------------------------
# Point and line segment utility functions.
#---------------------------------------------------------------------

def eval_linear(x, p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    # Assume x1 != x2
    y = (y2 - y1)/(x2 - x1) * (x-x1) + y1
    return y

def sqdistance(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    sqdist = (x2 - x1)**2 +(y2 - y1)**2
    return sqdist

def in_segment(p, p1, p2, tol):
    """Is p in the line segment (p1, p2)?"""

    x, y = p
    x1, y1 = p1
    x2, y2 = p2

    # Edge cases.
    if x < min(x1,x2) or x > max(x1,x2) or y < min(y1,y2) or y > max(y1,y2):
        return False
    if y1 == y2 or x1 == x2:
        return True
    dist2 = sqdistance_to_closest(p, p1, p2)
    return dist2 < tol**2

def closest(p, p1, p2):
    """Find the point in the line defined by (p1,p2) that is closest to p."""
    x, y = p
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    dx2 = (x2 - x1)**2
    dy2 = (y2 - y1)**2
    m = dx2 + dy2
    xstar = ((y-y1)*dx*dy + x*dx2 + x1*dy2)/m
    ystar = (y1*dx2 + (x-x1)*dx*dy + y*dy2)/m
    return xstar, ystar

def sqdistance_to_closest(p, p1, p2):
    """
    Compute the square of the distance from the point p to the line defined by (p1,p2).
    """
    pc = closest(p, p1, p2)
    sqdist = sqdistance(p, pc)
    return sqdist

def close_enough(p1, p2, tol):
    """Is the distance from p1 to p2 less than tol?"""
    sqdist = sqdistance(p1, p2)
    return sqdist < tol**2

#---------------------------------------------------------------------
# Point list utility functions
#---------------------------------------------------------------------

def errors2(x, y, xorig, yorig):
    yi = np.interp(xorig, x, y)
    err = yi - yorig
    return err

def clean2(points, tol=1e-5):
    """
    Return a subset of points for which linear interpolation using the subset
    differs from interpolation using the original set by less than tol.
    """
    xlist = []
    ylist = []
    for point in points:
        xi, yi = point
        xlist.append(xi)
        ylist.append(yi)
    xorig = np.array(xlist)
    yorig = np.array(ylist)
    x = xorig
    y = yorig
    k = 1
    ndel = 0
    while k < len(x)-1:
        xnew = np.hstack((x[:k], x[k+1:]))
        ynew = np.hstack((y[:k], y[k+1:]))
        e2 = errors2(xnew, ynew, xorig, yorig)
        e2max = np.abs(e2).max()
        if e2max < tol:
            x = xnew
            y = ynew
            ndel += 1
        else:
            k += 1
    #if ndel > 0:
    #    e2 = errors2(x, y, xorig, yorig)
    #    e2max = np.abs(e2).max()
    #    print "Absolute value of max difference is %g" % e2max            
    new_points = zip(x,y)
    return new_points
