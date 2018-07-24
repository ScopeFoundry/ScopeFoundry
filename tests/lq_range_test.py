from ScopeFoundry import BaseApp
from qtpy import QtWidgets
import pyqtgraph as pg

import logging
logging.basicConfig(level='DEBUG')

class LQRangeTestApp(BaseApp):

    def __init__(self,argv):
        BaseApp.__init__(self,argv)

        ### LQ
        self.x_range = self.settings.New_Range('x', include_center_span=True, preserve_num=True)
        self.y_range = self.settings.New_Range('y', include_center_span=True, preserve_num=True)

        ### UI
            
        self.ui = QtWidgets.QScrollArea()
        self.ui.setWidgetResizable(True)
        self.ui.setLayout(QtWidgets.QHBoxLayout())

        self.lq_controls = self.settings.New_UI()
        self.ui.layout().addWidget(self.lq_controls)
        
        self.setup_figure()
        
        self.ui.layout().addWidget(self.console_widget)
        #self.plot.show()
        self.ui.show()
        #self.console_widget.show()
        
        self.ui.setGeometry(300,200,1200,600)
        
    def setup_figure(self):
        self.plot = pg.PlotWidget()
        self.ui.layout().addWidget(self.plot)
        self.plot.showGrid(x=True, y=True)
        self.plot.setAspectLocked(lock=True, ratio=1)

        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.plot.addItem(self.vLine, ignoreBounds=True)
        self.plot.addItem(self.hLine, ignoreBounds=True)


        self.scan_roi = pg.ROI([0,0],[1,1], movable=True)
        self.scan_roi.addScaleHandle([1, 1], [0, 0])
        self.scan_roi.addScaleHandle([0, 0], [1, 1])
        self.update_scan_roi()
        self.scan_roi.sigRegionChangeFinished.connect(self.mouse_update_scan_roi)
        self.plot.addItem(self.scan_roi)        

        #
        for lq in self.x_range.lq_dict.values():       
            lq.updated_value.connect(self.update_scan_roi)
        for lq in self.y_range.lq_dict.values():       
            lq.updated_value.connect(self.update_scan_roi)



    def update_scan_roi(self):
        self.log.debug("update_scan_roi")
        X = self.settings.ranges['x']
        Y = self.settings.ranges['y']
        self.imshow_extent = [X.min.val - 0.5*X.step.val,
                              X.max.val + 0.5*X.step.val,
                              Y.min.val - 0.5*Y.step.val,
                              Y.max.val + 0.5*Y.step.val]
        x0, x1, y0, y1 = self.imshow_extent
        
        self.vLine.setPos(X.center.val)
        self.hLine.setPos(Y.center.val)
        
        self.scan_roi.blockSignals(True)
        self.scan_roi.setPos( (x0, y0, 0))
        self.scan_roi.setSize( (x1-x0, y1-y0, 0))
        self.scan_roi.blockSignals(False)

    def mouse_update_scan_roi(self):
        x0,y0 =  self.scan_roi.pos()
        w, h =  self.scan_roi.size()
        
        self.x_range.center.update_value(x0 + w/2)
        self.y_range.center.update_value(y0 + h/2)
        self.x_range.span.update_value(w-self.x_range.step.val)
        self.y_range.span.update_value(h-self.y_range.step.val)
        #self.compute_scan_params()
        self.update_scan_roi()

        
if __name__ == '__main__':
    app = LQRangeTestApp([])
    app.exec_()