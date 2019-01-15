'''
Created on Jul 20, 2018

@author: lab
'''

from qtpy import  QtCore, QtWidgets

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