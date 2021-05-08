from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg
from ScopeFoundry.graphics.zoomable_map.zoomable_map import ZoomableMapImageItem
import skimage.data
import matplotlib.pyplot as plt

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

app = QtGui.QApplication([])


graph_layout = pg.GraphicsLayoutWidget()

plot = pg.PlotItem()
graph_layout.addItem(plot)
plot.setAspectLocked(1)
vb  = plot.getViewBox()


zmi = ZoomableMapImageItem(plot_item=plot, 
                       image=skimage.data.immunohistochemistry().swapaxes(0,1), rect=(-1,-1,6,2),
                       tile_size=64, z_value=100)

zmi.setTransform(zmi.transform.rotate(10.))

M = np.identity(3)
M[0,0] = M[1,1] = 1/500
M[0,1] = 0.2/500
M[0,2] = 0.001/500
M[2,0] = 0
t = QtGui.QTransform()
t.setMatrix(*M.flat)
zmi.setTransform(t)


im = skimage.data.chelsea()
Nx,Ny,_ = im.shape
alpha = np.zeros((Nx,Ny,1),dtype=im.dtype) + 255
print(im.shape, alpha.shape, repr(im.dtype))
im = np.concatenate([im, alpha], axis=2)
fill = np.zeros( (1,1,4), dtype=im.dtype)
fill[0,0,3] = 0

zmi2 = ZoomableMapImageItem(plot_item=plot, image=im, rect=(3,-0.5,2,2), tile_size=64, z_value=200, fill=fill)

histlut2 = pg.HistogramLUTItem(image=zmi2 )
graph_layout.addItem(histlut2)


x = np.arange(-5, 5, 0.03)
y = np.arange(-5, 5, 0.03)

xx, yy = np.meshgrid(x, y)
z = np.sin(xx**2 + yy**2) / (xx**2 + yy**2)
z[::10,::10] = 1
print(z.shape, z.dtype)
colormap = plt.cm.get_cmap("RdBu")  # cm.get_cmap("CMRmap")
colormap._init()
lut = (colormap._lut * 255).view(np.ndarray)  # Convert matplotlib colormap from 0-1 to 0 -255 for Qt


zmi3 = ZoomableMapImageItem(plot_item=plot, image=z, rect=(3,3,4,4), 
                        tile_size=1024, z_value=300, fill=np.NaN, 
                        levels=(-1.1,1.1), lut=lut)
                        
                        
histlut = pg.HistogramLUTItem(image=zmi3)
graph_layout.addItem(histlut)

imitem3 = pg.ImageItem(z)
rect = (0,3,4,4)
imitem3.setRect(pg.QtCore.QRectF(*rect))
plot.addItem(imitem3)


plot.setTitle("Zoomable Map Test PyqtGraph")

graph_layout.show()



if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()

