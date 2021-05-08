from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg
from ScopeFoundry.graphics.zoomable_map.zoomable_map import ZoomableMapImageItem
import skimage.data
import h5py

f = h5py.File("/Users/esbarnard/gdal_pyramid_test/210304_131725_survey_scan.h5", 'r')
M = f['measurement/survey_scan']
im = np.array(M['image_strips'][0])
rect = M['strip_rects'][0]

im = np.hstack([im,]*100)

app = QtGui.QApplication([])

plot = pg.PlotWidget()
plot.setAspectLocked(1)
vb  = plot.getViewBox()


zmi = ZoomableMapImageItem(plot_item=plot, image=im, rect=None)

plot.setTitle("Zoomable Map Test PyqtGraph")
plot.show()




if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
