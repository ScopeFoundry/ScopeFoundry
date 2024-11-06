# Removed


## BaseMicroscopeApp

Prior to V1.0 there was a convenience function to add plot widgets:

```python
def add_pg_graphics_layout(self, name, widget):
    self.log.info("---adding pg GraphicsLayout figure {} {}".format(name, widget))
    if name in self.figs:
        return self.figs[name]
    else:
        disp = pg.GraphicsLayoutWidget(border=(100, 100, 100))
        widget.layout().addWidget(disp)            
        self.figs[name] = disp
        return disp
```

```python
def add_figure_mpl(self,name, widget):
    """creates a matplotlib figure attaches it to the qwidget specified
    (widget needs to have a layout set (preferably verticalLayout)
    adds a figure to self.figs"""
    print "---adding figure", name, widget
    if name in self.figs:
        return self.figs[name]
    else:
        fig = Figure()
        fig.patch.set_facecolor('w')
        canvas = FigureCanvas(fig)
        nav    = NavigationToolbar2(canvas, self.ui)
        widget.layout().addWidget(canvas)
        widget.layout().addWidget(nav)
        canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
        canvas.setFocus()
        self.figs[name] = fig
        return fig
```

```python
def add_figure(self, name, widget):
    # DEPRECATED
    return self.add_figure_mpl(name, widget)
```

Adding matplot (mpl) is discourage. Adding pyqtgraph plots can be done with a single line to a Measurement in a setup_figure(self) method

```
figure = pg.GraphicsLayoutWidget(border=(100, 100, 100))
figure.plot()

```

