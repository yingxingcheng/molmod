# MolMod is a collection of molecular modelling tools for python.
# Copyright (C) 2007 - 2008 Toon Verstraelen <Toon.Verstraelen@UGent.be>
#
# This file is part of MolMod.
#
# MolMod is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# MolMod is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>
#
# --
"""Data structures to handle 3D rotations and translations

In addition to Translation, Rotation and Complete classes, two utility
functions are provided: rotation_around_center and superpose. The latter is an
implementation of the Kabsch algorithm.
"""

from utils import cached, cached_writable, ReadOnly, rmsd
from molmod.unit_cells import UnitCell

import numpy


__all__ = [
    "Translation", "Rotation", "Complete", "rotation_about_axis", "superpose",
]


eps = 1.0e-6

def check_matrix(m):
    """Check the sanity of the given 4x4 transformation matrix"""
    if m.shape != (4, 4):
        raise ValueError("The argument must be a 4x4 array.")
    z = m[3, 0:3]
    if max(abs(m[3, 0:3])) > eps:
        raise ValueError("The given matrix does not have correct translational part")
    if abs(m[3, 3] - 1.0) > eps:
        raise ValueError("The lower right element of the given matrix must be 1.0.")


def check_translation_vector(t):
    """Check the sanity of a translation vector"""
    if t.shape != (3,):
        raise ValueError("The translation vector must contain three elements.")


def check_rotation_matrix(r):
    """Check the sanity of a rotation matrix"""
    if r.shape != (3, 3):
        raise ValueError("The rotation matrix must be a 3 by 3 array.")
    if abs(numpy.dot(r[:,0], r[:,0]) - 1) > eps or \
        abs(numpy.dot(r[:,0], r[:,0]) - 1) > eps or \
        abs(numpy.dot(r[:,0], r[:,0]) - 1) > eps or \
        numpy.dot(r[:,0], r[:,1]) > eps or \
        numpy.dot(r[:,1], r[:,2]) > eps or \
        numpy.dot(r[:,2], r[:,0]) > eps:
        raise ValueError("The rotation matrix is significantly non-orthonormal.")


class Translation(ReadOnly):
    """Represents a translation in 3D

       The attribute t contains the actual translation vector, which is a numpy
       array with three elements.
    """
    def __init__(self, t):
        """Initialize a translation object

           The first argument must be a list-like object with three numbers.
        """
        ReadOnly.__init__(self)
        self._init_attributes({"t": numpy.array(t, float)}, {})
        check_translation_vector(self.t)

    @classmethod
    def from_matrix(cls, m):
        """Initialize a translation from a 4x4 matrix"""
        check_matrix(m)
        return cls(m[0:3, 3])

    @classmethod
    def identity(cls):
        return cls(numpy.zeros(3,float))

    @cached
    def matrix(self):
        """The 4x4 matrix representation of this translation"""
        result = numpy.identity(4, float)
        result[0:3, 3] = self.t
        return result

    @cached_writable
    def inv(self):
        """The inverse translation"""
        result = Translation(-self.t)
        result.inv = self
        return result

    def apply_to(self, x):
        """Apply this translation to the given object

           The argument can be several sorts of objects:
             * numpy array with shape (3,)
             * numpy array with shape (N,3)
             * Translation
             * Rotation
             * Complete
             * UnitCell

           In case of arrays, the 3D vectors are translated. In case of trans-
           formations, a new transformation is returned that consists of this
           translation applied AFTER the given translation. In case of a unit
           cell, the original object is returned.

           This method is equivalent to self*x.
        """
        if isinstance(x, numpy.ndarray) and (x.shape == (3,) or (len(x.shape) == 2 and x.shape[1] == 3)):
            return x + self.t
        elif isinstance(x, Complete):
            return Complete(x.r, x.t + self.t)
        elif isinstance(x, Translation):
            return Translation(x.t + self.t)
        elif isinstance(x, Rotation):
            return Complete(x.r, self.t)
        elif isinstance(x, UnitCell):
            return x
        else:
            raise ValueError("Can not apply this translation to %s" % x)

    __mul__ = apply_to

    def compare(self, other, t_threshold=1e-3):
        """Compare two translations

           The RMSD of the translation vectors is computed. The return value
           is True when the RMSD is below the threshold, i.e. when the two
           translations are almost identical.
        """
        return rmsd(self.t, other.t) < t_threshold


class Rotation(ReadOnly):
    """Represents a rotation in 3D about the origin

       The attribute r contains the actual rotation matrix, which is a numpy
       array with shape (3,3).
    """

    def __init__(self, r):
        """Initialize a rotation object.

           The first argument must be a 3 by 3 array-like object.
        """
        ReadOnly.__init__(self)
        self._init_attributes({"r": numpy.array(r, float)}, {})
        check_rotation_matrix(self.r)

    @classmethod
    def from_matrix(cls, m):
        """Initialize a rotation from a 4x4 matrix"""
        check_matrix(m)
        return cls(m[0:3, 0:3])

    @classmethod
    def identity(cls):
        return cls(numpy.identity(3, float))

    @classmethod
    def from_properties(cls, angle, axis, invert):
        """Initialize a rotation based on the properties"""
        norm = numpy.linalg.norm(axis)
        if norm > 0:
            x = axis[0] / norm
            y = axis[1] / norm
            z = axis[2] / norm
            c = numpy.cos(angle)
            s = numpy.sin(angle)
            r = (1-2*invert) * numpy.array([
                [x*x*(1-c)+c  , x*y*(1-c)-z*s, x*z*(1-c)+y*s],
                [x*y*(1-c)+z*s, y*y*(1-c)+c  , y*z*(1-c)-x*s],
                [x*z*(1-c)-y*s, y*z*(1-c)+x*s, z*z*(1-c)+c  ]
            ])
        else:
            r = numpy.identity(3) * (1-2*invert)
        return cls(r)

    @classmethod
    def cast(cls, c):
        """Convert the first argument into a Complete object"""
        if isinstance(c, Complete):
            return c
        elif isinstance(c, Translation):
            return Complete(numpy.identity(3, float), c.t)
        elif isinstance(c, Rotation):
            return Complete(c.r, numpy.zeros(3, float))

    @cached
    def properties(self):
        """Rotation properties: angle, axis, invert"""
        # determine wether an inversion rotation has been applied
        invert = (numpy.linalg.det(self.r) < 0)
        factor = {True: -1, False: 1}[invert]
        # get the rotation data
        # trace(r) = 1+2*cos(angle)
        cos_angle = 0.5*(factor*numpy.trace(self.r) - 1)
        if cos_angle > 1: cos_angle = 1.0
        if cos_angle < -1: cos_angle = -1.0
        # the antisymmetric part of the non-diagonal vector tell us something
        # about sin(angle) and n.
        axis = 0.5*factor*numpy.array([-self.r[1, 2] + self.r[2, 1], self.r[0, 2] - self.r[2, 0], -self.r[0, 1] + self.r[1, 0]])
        sin_angle = numpy.linalg.norm(axis)
        # look for the best way to normalize the
        if (sin_angle == 0.0) and (cos_angle > 0):
            axis[2] = 1.0
        elif abs(sin_angle) < (1-cos_angle):
            for index in range(3):
                axis[index] = {True: -1, False: 1}[axis[index] < 0] * numpy.sqrt(abs((factor*self.r[index, index] - cos_angle) / (1 - cos_angle)))
        else:
            axis = axis / sin_angle

        # Finally calculate the angle:
        angle = numpy.arctan2(sin_angle, cos_angle)
        return angle, axis, invert

    @cached
    def matrix(self):
        """The 4x4 matrix representation of this rotation"""
        result = numpy.identity(4, float)
        result[0:3, 0:3] = self.r
        return result

    @cached_writable
    def inv(self):
        """The inverse rotation"""
        result = Rotation(self.r.transpose())
        result.inv = self
        return result

    def apply_to(self, x):
        """Apply this rotation to the given object

           The argument can be several sorts of objects:
             * numpy array with shape (3,)
             * numpy array with shape (N,3)
             * Translation
             * Rotation
             * Complete

           In case of arrays, the 3D vectors are rotated. In case of trans-
           formations, a transformation is returned that consists of this
           rotation applied AFTER the given translation. In case of a unit cell,
           a unit cell with rotated cell vectors is returned.

           This method is equivalent to self*x.
        """
        if isinstance(x, numpy.ndarray) and (x.shape == (3,) or (len(x.shape) == 2 and x.shape[1] == 3)):
            return numpy.dot(x, self.r.transpose())
        elif isinstance(x, Complete):
            return Complete(numpy.dot(self.r, x.r), numpy.dot(self.r, x.t))
        elif isinstance(x, Translation):
            return Complete(self.r, numpy.dot(self.r, x.t))
        elif isinstance(x, Rotation):
            return Rotation(numpy.dot(self.r, x.r))
        elif isinstance(x, UnitCell):
            return UnitCell(numpy.dot(self.r, x.matrix), x.active)
        else:
            raise ValueError("Can not apply this rotation to %s" % x)

    __mul__ = apply_to

    def compare(self, other, r_threshold=1e-3):
        """Compare two rotations

           The RMSD of the rotation matrices is computed. The return value
           is True when the RMSD is below the threshold, i.e. when the two
           rotations are almost identical.
        """
        return rmsd(self.r, other.r) < r_threshold


class Complete(Translation, Rotation):
    def __init__(self, r, t):
        """Initialize a complete transformation object, i.e. rotation & translation

           The first argument must be a 3 by 3 orthonormal array-like object.
           The second argument must be a list-like object with three numbers.

           Internally the translation part is always applied after the rotation
           part.
        """
        ReadOnly.__init__(self)
        self._init_attributes({"r": numpy.array(r, float), "t": numpy.array(t, float)}, {})
        check_translation_vector(self.t)
        check_rotation_matrix(self.r)

    @classmethod
    def from_matrix(cls, m):
        """Initialize a complete transformation from a 4x4 matrix"""
        check_matrix(m)
        return cls(m[0:3, 0:3], m[0:3, 3])

    @classmethod
    def identity(cls):
        return cls(numpy.identity(3,float), numpy.zeros(3, float))

    @classmethod
    def from_properties(cls, angle, axis, invert, translation):
        """Initialize a transformation based on the properties"""
        rot = Rotation.from_properties(angle, axis, invert)
        return Complete(rot.r, translation)

    @cached
    def matrix(self):
        """The 4x4 matrix representation of this transformation"""
        result = numpy.identity(4, float)
        result[0:3, 3] = self.t
        result[0:3, 0:3] = self.r
        return result

    @cached
    def properties(self):
        """Transformation properties: angle, axis, invert, translation"""
        rot = Rotation(self.r)
        angle, axis, invert = rot.properties
        return angle, axis, invert, self.t

    @cached_writable
    def inv(self):
        """The inverse transformation"""
        result = Complete(self.r.transpose(), numpy.dot(self.r.transpose(), -self.t))
        result.inv = self
        return result

    def apply_to(self, x):
        """Apply this transformation to the given object

           The argument can be several sorts of objects:
             * numpy array with shape (3,)
             * numpy array with shape (N,3)
             * Translation
             * Rotation
             * Complete

           In case of arrays, the 3D vectors are transformed. In case of trans-
           formations, a transformation is returned that consists of this
           transformation applied AFTER the given translation. In case of a unit
           cell, a unit cell with rotated cell vectors is returned. (The
           translational part does not affect the unit cell.)

           This method is equivalent to self*x.
        """
        if isinstance(x, numpy.ndarray) and (x.shape == (3,) or (len(x.shape) == 2 and x.shape[1] == 3)):
            return numpy.dot(x, self.r.transpose()) + self.t
        elif isinstance(x, Complete):
            return Complete(numpy.dot(self.r, x.r), numpy.dot(self.r, x.t) + self.t)
        elif isinstance(x, Translation):
            return Complete(self.r, numpy.dot(self.r, x.t) + self.t)
        elif isinstance(x, Rotation):
            return Complete(numpy.dot(self.r, x.r), self.t)
        elif isinstance(x, UnitCell):
            return UnitCell(numpy.dot(self.r, x.matrix), x.active)
        else:
            raise ValueError("Can not apply this rotation to %s" % x)

    __mul__ = apply_to

    def compare(self, other, t_threshold=1e-3, r_threshold=1e-3):
        """Compare two transformations

           The RMSD values of the rotation matrices and the translation vectors
           are computed. The return value is True when the RMSD values are below
           the thresholds, i.e. when the two transformations are almost
           identical.
        """
        return rmsd(self.t, other.t) < t_threshold and rmsd(self.r, other.r) < r_threshold


def rotation_about_axis(center, angle, axis, invert=False):
    """Compute the transformation object that represents a rotation about an axis

       Arguments:
         center  --  Point on the axis
         angle  --  Rotation angle
         axis  --  Rotation axis
         invert  --  When True, an inversion rotation is constructed
                     [default=False]
    """
    return Translation(center)*Rotation.from_properties(angle, axis, invert)*Translation(-center)


def superpose(ras, rbs, weights=None):
    """Compute the transformation that minimizes the RMSD between the points ras and rbs

    Both ras and rbs are Nx3 numpy arrays. Each row corresponds to a 3D
    coordinate. Corresponding rows contain the points that are brought
    into overlap. The implementation is based on the Kabsch Algorithm:

    http://dx.doi.org/10.1107%2FS0567739476001873

    The returned transformation projects B onto A.
    """
    if weights is None:
        ma = ras.mean(axis=0)
        mb = rbs.mean(axis=0)
    else:
        total_weight = weights.sum()
        ma = numpy.dot(weights, ras)/total_weight
        mb = numpy.dot(weights, rbs)/total_weight


    # Kabsch
    if weights is None:
        A = numpy.dot((rbs-mb).transpose(), ras-ma)
    else:
        weights = weights.reshape((-1,1))
        A = numpy.dot(((rbs-mb)*weights).transpose(), (ras-ma)*weights)
    B = numpy.dot(A.transpose(), A)
    evals, evecs = numpy.linalg.eigh(B)
    evals = numpy.clip(evals, 0, evals.max())
    Bhalf = numpy.dot(evecs*numpy.sqrt(evals), evecs.transpose())
    # safe inverse of A
    U, W, Vt = numpy.linalg.svd(A)
    Winv = 1/W
    Winv[abs(W)<1e-10] = 0
    Ainv = numpy.dot(Vt.transpose()*Winv, U.transpose())
    r = numpy.dot(Bhalf, Ainv)

    # fix degeneracies
    U, W, Vt = numpy.linalg.svd(r)
    r = numpy.dot(U, Vt)

    return Complete(r, numpy.dot(r, -mb) + ma)


