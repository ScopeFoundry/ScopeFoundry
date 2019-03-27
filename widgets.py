'''
Created on Jul 20, 2018

@author: lab
'''

from qtpy import  QtCore, QtWidgets, QtGui
import pyqtgraph as pg
import numpy as np

class MinMaxQSlider(QtWidgets.QWidget):
    """
    Costume QSlider widget designed to work with logged_quantities.
    Two spin boxes allow to dynamically update the min and max value of the slider.
    """
    
    #Signals
    updated_value = QtCore.Signal((float,),(int,))
    
    def __init__(self, name="", spinbox_decimals = 2, **QSlider_kwargs):

        self.name = name
        
        #Setup widget
        QtWidgets.QWidget.__init__(self)
        
        #slider
        self.slider = QtWidgets.QSlider(orientation = QtCore.Qt.Horizontal, **QSlider_kwargs)
        self.slider.valueChanged.connect(self.on_slider_value_changed)
        self.slider.setSingleStep(1)
        self.slider.sliderMoved[int].connect(self.set_title)
        
        #min and max spinbox
        self.min_double_spinbox = QtWidgets.QDoubleSpinBox()
        self.min_double_spinbox.setRange(-1e12, 1e12)
        self.max_double_spinbox = QtWidgets.QDoubleSpinBox()
        self.max_double_spinbox.setRange(-1e12, 1e12)
        
        self.min_double_spinbox.valueChanged[float].connect(self.update_slider_minimum)
        self.max_double_spinbox.valueChanged[float].connect(self.update_slider_maximum)
        
        self.setDecimals(spinbox_decimals)

        #title label
        self.title_label = QtWidgets.QLabel()
        
        #Setup layout
        self.layout_ = QtWidgets.QGridLayout()
        self.layout_.addWidget(self.min_double_spinbox, 0,0, alignment=QtCore.Qt.AlignLeft)
        self.layout_.addWidget(self.title_label, 0,1, alignment = QtCore.Qt.AlignHCenter)
        self.layout_.addWidget(self.max_double_spinbox, 0,2, alignment=QtCore.Qt.AlignRight)    
        self.layout_.addWidget(self.slider, 1,0, 1,3)
        
        self.setLayout(self.layout_)


    def set_name(self,name):
        self.name = name
        val = self.transform_from_slider(self.slider.value())
        self.set_title(val)
        
    @property
    def vmin(self):
        return self.min_double_spinbox.value()
    @property
    def vmax(self):
        return self.max_double_spinbox.value()
    @property
    def vrange(self):
        return self.vmax-self.vmin
        
    def transform_to_slider(self,x):
        pct = 100*(x-self.vmin)/self.vrange
        return int(pct)
    
    def transform_from_slider(self,x):
        val = self.vmin + (x*self.vrange/100)
        return val
        
    def update_min_double_spinbox(self, vmin):
        try:
            self.min_double_spinbox.blockSignals(True)
            self.min_double_spinbox.setValue(vmin)
        finally:
            self.min_double_spinbox.blockSignals(False)   
                     
    def update_max_double_spinbox(self, vmax):        
        try:
            self.max_double_spinbox.blockSignals(True)
            self.max_double_spinbox.setValue(vmax)
        finally:
            self.max_double_spinbox.blockSignals(False)
        
    def update_slider_minimum(self, vmin):
        val = self.slider.sliderPosition()
        self.slider.setMinimum(self.transform_to_slider(vmin))
        self.slider.setSliderPosition(val)
    def update_slider_maximum(self, vmax):
        self.slider.setMaximum(self.transform_to_slider(vmax))
        
    def update_value(self,x):
        try:
            self.slider.blockSignals(True)
            self.slider.setValue(self.transform_to_slider(x))
        finally:
            self.slider.blockSignals(False) 
        
    def on_slider_value_changed(self):
        val = self.transform_from_slider(self.slider.value())
        self.updated_value.emit(val)

    def setRange(self, vmin, vmax):
        # as it is currently used in LoggedQuantity.change_min_max()
        self.update_min_double_spinbox(vmin)
        self.update_max_double_spinbox(vmax)
        
    def setDecimals(self,decimals):
        self.min_double_spinbox.setDecimals(decimals)
        self.max_double_spinbox.setDecimals(decimals)
        
    def setSuffix(self,unit):
        self.min_double_spinbox.setSuffix(" "+unit)
        self.max_double_spinbox.setSuffix(" "+unit)

    def setSingleStep(self, spinbox_step):
        self.min_double_spinbox.setSingleStep(spinbox_step)
        self.max_double_spinbox.setSingleStep(spinbox_step)
        
    def set_title(self, val):
        val = self.transform_from_slider(val)
        text =self.name+" "+str(val)
        self.title_label.setText(text)
        
        
        
        
class RegionSlicer(object):
    '''
    adds a movable pyqtgraph.LinearRegionItem to 'parent_plot' and provides
    a numpy slice that would slice specified x_array according to the region.
    Note: The x_array from which the indexes are calculated has to be specified.
          at initialization or using set_x_array(x_array) method
            
    parent_plot            <pyqtgraph.PlotItem>
    name                   <str>
    x_array                array-like 
    slicer_updated_func    gets called when region is updated
    brush,ZValue,font      are passed to the LinearRegionItem
    initial                [start_idx, stop_idx] of the slice
    '''
    
    def __init__(self, parent_plot,  x_array=None, name='array_slicer_name',
                 slicer_updated_func=lambda:None,  
                 brush=QtGui.QColor(0,255,0,70), ZValue=10, font=QtGui.QFont("Times", 12), initial=[0,100]):
        self.name = name
        from ScopeFoundry.logged_quantity import LQCollection
        self.settings = LQCollection()
        self.start = self.settings.New('start', int, initial=initial[0], vmin = 0)
        self.stop = self.settings.New('stop', int, initial=initial[1], vmin = 0)
        self.activated = self.settings.New('activated', bool, initial = False)
        
        self.start.add_listener(self.on_change_start_stop)
        self.stop.add_listener(self.on_change_start_stop)
        self.activated.add_listener(self.on_change_activated)
        
        self.linear_region_item = pg.LinearRegionItem(brush = brush)
        self.linear_region_item.setZValue(ZValue)        
        parent_plot.addItem(self.linear_region_item)
        
        self.linear_region_item.sigRegionChangeFinished.connect(self.on_change_region)
        self.inf_line_label = pg.InfLineLabel(self.linear_region_item.lines[1], self.name, 
                                               position=0.78, anchor=(0.5, 0.5))
        self.inf_line_label.setFont(font)
        if x_array == None:
            x_array = np.arange(512)
        self.set_x_array(x_array)
        self.slicer_updated = slicer_updated_func
    
    @QtCore.Slot(object)
    def set_x_array(self, x_array):
        self.x_array = np.array(x_array)
        self.linear_region_item.setBounds( [self.x_array.min(), self.x_array.max()] )
        kk_max = len(self.x_array)
        self.start.change_min_max(0, kk_max)
        self.stop.change_min_max(0, kk_max)
        if self.start.val > kk_max:
            self.start.update_value(kk_max)
        if self.stop.val > kk_max:
            self.stop.update_value(kk_max)
        self.on_change_start_stop()
        
    @property
    def slice(self):
        return np.s_[ self.settings['start'] : self.settings['stop'] ]
            
    def on_change_region(self):
        '''
        updates settings based on region 
        '''
        print(self.name, 'on_change_region')
        mn,mx = self.linear_region_item.getRegion()
        self.settings['start'] = np.argmin( (self.x_array - mn)**2 )
        self.settings['stop'] = np.argmin( (self.x_array - mx)**2 )
        self.slicer_updated()
    
    def on_change_start_stop(self):
        '''
        updates linear_region_item based on settings 
        '''
        rgn = [0,0]
        rgn[0] = self.x_array[ self.settings['start'] ]
        rgn[1] = self.x_array[ self.settings['stop'] ]
        self.linear_region_item.setRegion(rgn)    
        
    def on_change_activated(self):
        activated = self.activated.val
        self.linear_region_item.setEnabled(activated)
        self.linear_region_item.setAcceptHoverEvents(activated)
        self.linear_region_item.setAcceptTouchEvents(activated)
        if activated:
            opacity = 1
        else:
            opacity = 0
        self.linear_region_item.setOpacity(opacity)
        print('on_change_activated', activated)
        self.slicer_updated()
        
    def New_UI(self):
        ui_widget = self.settings.New_UI()
        ui_widget.layout().insertRow(0, QtWidgets.QLabel("<b>{}</b>".format(self.name)) )        
        return ui_widget
        