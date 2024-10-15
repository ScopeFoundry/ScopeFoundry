import numpy as np


class LQ3Vector:

    def __init__(self, x_lq, y_lq, z_lq):
        self.x_lq = x_lq
        self.y_lq = y_lq
        self.z_lq = z_lq

    @property
    def values(self):
        return np.array([self.x_lq.val, self.y_lq.val, self.z_lq.val])

    @property
    def length(self):
        vec = self.values
        return np.sqrt(np.dot(vec, vec))

    @property
    def normed_values(self):
        return self.values / self.length

    def dot(self, _lq_vector):
        """
        returns the scalar product with _lq_vector
        """
        return np.dot(_lq_vector.values, self.values)

    def project_on(self, _lq_vector):
        return np.dot(_lq_vector.normed_values, self.values)

    def angle_to(self, _lq_vector):
        return np.arccos(np.dot(_lq_vector.normed_values, self.normed_values))

    def add_listener(self, func, argtype=(), **kwargs):
        self.x_lq.add_listener(func, argtype, **kwargs)
        self.y_lq.add_listener(func, argtype, **kwargs)
        self.z_lq.add_listener(func, argtype, **kwargs)
