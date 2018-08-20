from ScopeFoundry import LQCollection, BaseApp

class LQConnectionTestApp(BaseApp):
    
    name = 'LQConnectionTestApp'

    def __init__(self,argv):
        BaseApp.__init__(self,argv)
        
        lq0 = self.settings.New('lq0', dtype=float,ro=False, initial=5)
        lq1 = self.settings.New('lq1', dtype=float,ro=False, initial=5)
        lq2 = self.settings.New('lq2', dtype=float,ro=False, initial=35)
        lq3 = self.settings.New('lq3', dtype=float,ro=True, initial=35)
        lq4 = self.settings.New('lq4', dtype=float,ro=False, initial=35)
        lq_sum = self.settings.New('lq_sum', dtype=float,ro=True, initial=35)
        lq_sum_bidir = self.settings.New('lq_sum_bidir', dtype=float,ro=False, initial=35)
        
        lq_scale = self.settings.New('lq_scale', dtype=float, ro=False)
        lq_scale2 = self.settings.New('lq_scale2', dtype=float, ro=False)
        
        
        lq_array = self.settings.New('lq_array', dtype=float, array=True, initial=[1.0,2.0,3.0,4.0])
        lq_array_element = self.settings.New('lq_array_element', dtype=float)
        
        lq_array_element.connect_lq_math( (lq_array,), lambda arr: arr[1])
        

        lq1.connect_to_lq(lq2)
        
        lq3.connect_lq_math(lq1, lambda x1: x1 + 1 )
        

        lq4.connect_lq_math(lq1,
                     func=lambda x: x + 5,
                     reverse_func= lambda y: y - 5, 
                     )


        def sum_lq(*vals):
            return sum(vals)

        lq_sum.connect_lq_math((lq1,lq2, lq3, lq4),
                        func=lambda a,b,c,d: a+b+c+d)
        
        
        
        def lq_sum_reverse(new_val, old_vals):
            a,b = old_vals
            return new_val - b, b
        lq_sum_bidir.connect_lq_math((lq0,lq1),
                              func=sum_lq,
                              reverse_func=lq_sum_reverse)
        
        
        lq_scale.connect_lq_math((lq0,), func=lambda x: 10*x,
                          reverse_func=lambda y, : [0.1*y,])
        
        lq_scale2.connect_lq_scale(lq0, 25.0)
        
        
        
        test_array = self.settings.New('test_array', dtype=float, array=True,  ro=False, fmt="%1.2f",
          initial=[[147, 111 , 100]])

        array_follower = self.settings.New('array_follower', dtype=float)
        
        test_array.connect_element_follower_lq( array_follower, index=(0,1), bidir=True )
        
        
        
        self.ui = self.settings.New_UI()
        
        self.console_widget.show()
        self.ui.show()
        
        
if __name__ == '__main__':
    app = LQConnectionTestApp([])
    app.exec_()