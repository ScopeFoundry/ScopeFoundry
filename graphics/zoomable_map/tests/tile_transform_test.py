from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg
import skimage.data
import math

def printTransform(t):
    print(f"[ {t.m11()} {t.m12()} {t.m13()} ]")
    print(f"[ {t.m21()} {t.m22()} {t.m23()} ]")
    print(f"[ {t.m31()} {t.m32()} {t.m33()} ]")



pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

app = QtGui.QApplication([])
plot = pg.PlotWidget()
plot.setAspectLocked(1)
vb  = plot.getViewBox()
plot.show()

x = np.arange(-5, 5, 0.1)
y = np.arange(-5, 5, 0.1)

xx, yy = np.meshgrid(x, y)
sin_im = np.sin(xx**2 + yy**2) / (xx**2 + yy**2)
sin_im = skimage.data.camera()[:500,:500]
#sin_im = np.random.random(sin_im.shape)
imitem = pg.ImageItem(sin_im)
rect = (0,3,4,4)
imitem.setRect(pg.QtCore.QRectF(*rect))
#imitem.setPos()

#imitem.resetTransform()
t = imitem.transform()
#t.set
printTransform(t)

M = np.identity(3)
M[0,0] = M[1,1] = 3
M[0,1] = 0.2
M[0,2] = 0.001
M[2,0] = -1000
t.setMatrix(*M.flat)
imitem.setTransform(t)


t = QtGui.QTransform()
t.scale(1/512., 1/512.)
t.rotate(5.)
imitem.setTransform(t)


    
printTransform(t)

print("transform", imitem.transform())
print("transform", imitem.transform())
plot.addItem(imitem)


#x0, y0, w, h = self.zmi.rect
#0,0, 1, 1

#orig_pixel_size_x = 1 / zmi.image.shape[0]
#orig_pixel_size_y = 1 / zmi.image.shape[1]
#print("orig_pixel_size", orig_pixel_size_x, orig_pixel_size_y)


def tile_transform(im, tile_size, z,ii,jj):
    zf = 2**z
    
    Nx, Ny = im.shape
    
    
    Nt = tile_size 
    
    x = ii*zf* Nt
    y = jj*zf* Nt

    tr = QtGui.QTransform()
    
    sx = zf#*Nt/Nx * Nt
    sy = zf#*Nt/Ny * Nt
    tr.translate(x, y)
    tr.scale(sx, sy)
    
    

    print(f"Nt={Nt}, z={z}, zf={zf}, ii={ii}, jj={jj}, x={x}, y={y}, scale {sx} {sy}")

    return tr

Nt = 32

for (zoom,ii,jj) in [(0,0,0),(0,1,1),(1,1,1),(2,1,1),(3,1,1)]:#, (1,1,1),(1,0,1)]:
    t_img = np.random.random((Nt,Nt))
    t_imitem = pg.ImageItem(t_img)
    tr = tile_transform(sin_im, Nt,zoom,ii,jj)*imitem.transform()
    printTransform(tr)
    t_imitem.setTransform(tr)
    plot.addItem(t_imitem)


def on_range_changed(src, new_range=None):
    if new_range is None:
            new_range = vb.viewRange()
    (xl,xr), (yb, yt) = new_range

    print('on_range_changed', new_range)
    print('vb.viewPixelSize()', vb.viewPixelSize())
    tI = imitem.transform().inverted()[0]
    print('converted_new_range BL', tI.map(xl,yb))
    print('converted_new_range TR', tI.map(xr,yt))
    #print('viewPixelSize --> orig', t.inverted()[0].map(*vb.viewPixelSize()))
    #print('vb.viewRect', vb.viewRect())
    
    px, py = vb.viewPixelSize()
    
    #distances_in_orig_pixel_space
    x0, y0 = tI.map(xl,yb)
    x1, y1 = tI.map(xr,yt)
    
    bl_tr_dist_view = np.sqrt( (xr-xl)**2 + (yt-yb)**2)
    bl_tr_dist_view_px = np.sqrt( ((xr-xl)/px)**2 + ((yt-yb)/py)**2)
    bl_tr_dist_orig = np.sqrt( (x1-x0)**2 + (y1-y0)**2)

    print("bl_tr_dist_view", bl_tr_dist_view)
    print("bl_tr_dist_view_px", bl_tr_dist_view_px)
    print("bl_tr_dist_orig", bl_tr_dist_orig)
    
        
    screen_pixels_in_view_x = abs(xr-xl)/px
    screen_pixels_in_view_y = abs(yt-yb)/py
    
    print('screen_pixels_in_view', screen_pixels_in_view_x, screen_pixels_in_view_y)
    
    #distances_in_orig_pixel_space
    x0, y0 = tI.map(xl,yb)
    x1, y1 = tI.map(xr,yt)
    print("distances_in_orig_pixel_space", x1-x0, y1-y0)
    
    print("approx zoom factors", screen_pixels_in_view_x/(x1-x0), screen_pixels_in_view_x/(y1-y0))
    zf = bl_tr_dist_orig/bl_tr_dist_view_px
    print("zoom factor", zf)
    
    z_max = 10 # temporary
    zoom = min(max(int(np.floor(np.log2(zf))),0), z_max)
    zfi = 2**zoom # integer power of two zoom factor    

    
    # tile position for a given zoom in original pixel coords
    #x = ii*zf* Nt
    #y = jj*zf* Nt
    # flipping this formula
    #ii = x / (zf*Nt)
    #jj = y / (zf*Nt)

    Nt = 32
    
    Nx_tiles = int(np.ceil(sin_im.shape[0]/zfi/Nt))
    Ny_tiles = int(np.ceil(sin_im.shape[1]/zfi/Nt))
    
    print("zoom", zoom,'zfi', zfi, "Tiles at zoom", Nx_tiles, Ny_tiles )
    
    
    ii0 = x0 / (zf*Nt)
    ii0 = max(0, math.floor(ii0)) # clip at zero
    ii1 = x1 / (zf*Nt)
    ii1 = min(math.ceil(ii1), Nx_tiles)

    jj0 = y0 / (zf*Nt)
    jj0 = max(0, math.floor(jj0)) # clip at zero
    jj1 = y1 / (zf*Nt)
    jj1 = min(math.ceil(jj1), Ny_tiles)    
    
    
    print(f"x tiles {Nt} within view {ii0} to {ii1}")
    print(f"y tiles {Nt} within view {jj0} to {jj1}")
    
    def tiles_at_zoom(z):
        zfi = 2**z
        Nt = tile_size = 32
        #Nx_tiles = int(np.ceil(self.image.shape[0]/zfi/Nt))
        #Ny_tiles = int(np.ceil(self.image.shape[1]/zfi/Nt))
        Nx_tiles = (sin_im.shape[0]/zfi/Nt)
        Ny_tiles = (sin_im.shape[1]/zfi/Nt)
        
        return (Nx_tiles, Ny_tiles)
        
    print("tiles_at_zoom", zoom, tiles_at_zoom(zoom))
    
sigprox = pg.SignalProxy(
                    signal=plot.sigRangeChanged,
                    #delay=0.1,
                    rateLimit=30,
                    slot=on_range_changed)


if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
