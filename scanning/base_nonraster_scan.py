from ScopeFoundry import Measurement
from ScopeFoundry.scanning.base_raster_scan import BaseRaster2DScan
import time
import numpy as np

class BaseNonRaster2DScan(BaseRaster2DScan):
    name = "base_non_raster_2Dscan"

    def gen_raster_scan(self, gen_arrays=True):
        self.Npixels = self.Nh.val*self.Nv.val
        self.scan_shape = (1, self.Nv.val, self.Nh.val)
        
        if gen_arrays:
            #print "t0", time.time() - t0
            self.create_empty_scan_arrays()            
            #print "t1", time.time() - t0
            
#             t0 = time.time()
#             pixel_i = 0
#             for jj in range(self.Nv.val):
#                 #print "tjj", jj, time.time() - t0
#                 self.scan_slow_move[pixel_i] = True
#                 for ii in range(self.Nh.val):
#                     self.scan_v_positions[pixel_i] = self.v_array[jj]
#                     self.scan_h_positions[pixel_i] = self.h_array[ii]
#                     self.scan_index_array[pixel_i,:] = [0, jj, ii] 
#                     pixel_i += 1
#             print "for loop raster gen", time.time() - t0
             
            t0 = time.time()
             
            H, V = np.meshgrid(self.h_array, self.v_array)
            self.scan_h_positions[:] = H.flat
            self.scan_v_positions[:] = V.flat
            
            II,JJ = np.meshgrid(np.arange(self.Nh.val), np.arange(self.Nv.val))
            self.scan_index_array[:,1] = JJ.flat
            self.scan_index_array[:,2] = II.flat
            #self.scan_v_positions
            print("array flatten raster gen", time.time() - t0)
            
            
    def gen_spiral_scan(self, gen_arrays=True):
        #self.Npixels = self.Nh.val*self.Nv.val
        self.scan_shape = (1, Npixels)
        
        if gen_arrays:
            #print "t0", time.time() - t0
            self.create_empty_scan_arrays()            
            #print "t1", time.time() - t0
            
#             t0 = time.time()
#             pixel_i = 0
#             for jj in range(self.Nv.val):
#                 #print "tjj", jj, time.time() - t0
#                 self.scan_slow_move[pixel_i] = True
#                 for ii in range(self.Nh.val):
#                     self.scan_v_positions[pixel_i] = self.v_array[jj]
#                     self.scan_h_positions[pixel_i] = self.h_array[ii]
#                     self.scan_index_array[pixel_i,:] = [0, jj, ii] 
#                     pixel_i += 1
#             print "for loop raster gen", time.time() - t0
            
            h = ix * np.cos(ix)
            v = ix * np.sin(ix)
            
            t0 = time.time()
             
            H, V = np.meshgrid(self.h_array, self.v_array)
            self.scan_h_positions[:] = H.flat
            self.scan_v_positions[:] = V.flat
            
            II,JJ = np.meshgrid(np.arange(self.Nh.val), np.arange(self.Nv.val))
            self.scan_index_array[:,1] = JJ.flat
            self.scan_index_array[:,2] = II.flat
            #self.scan_v_positions
            print("array flatten raster gen", time.time() - t0)
