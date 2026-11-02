**this file will be overwriten! **

 - Write documentation describing your app, files starting __ are ignored.

 - or add to `links.json`

## Settings

 - *activation*: <i>sweep_2d</i>

 - *run_state*: None

 - *progress*: None

 - *profile*: Run a profile on the run to find performance problems

 - *scan_mode*: <h3>Create new sweep:</h3><i>specify the values each actuator takes during the sweep (either by ranges or a list of positions). Use one of the following modes to define how the values are combined. </i>
<p><i>co-move:</i> all actuators co-move
<p><i>nested:</i> actuators move all combinations where 1st is slowest ...
<p><i>serpentine:</i> actuators move all combinations where 1st is slowest, 2nd is fastest and 2nd reverses direction every row.
<p><i>*_swap_order</i> modes are the same as above, but the fastest and slowest of the actuators is swapped.</p>
<p><i>position_list:</i> positions are defined by this Measurement's Position List.</p><br><h3>MODIFY or EXTEND previous sweep:</h3><i>never alters/deletes saved data files, always makes new files, reuses data in memory</i><p><i>RETAKE_POSITIONS:</i> Allows to retake (fix) inidiviual data points specified in Position List. To add positions ctrl click on data. Makes a new datafile with data in memory with retaken data points updated.</p><p><i>RETAKE_SLICE:</i> Retake a slice of data specified by start and stop indices. Makes a new datafile with data in memory with retaken data points updated.</p><p><i>ADD_REPS:</i> Adds more repetitions to existing scan data to improve signal-to-noise ratio through additional averaging. You can change the number of repetitions for collectors that are already active (i.e. have non-zero repetitions) and activate <i>re-sweep</i>. Makes a new datafile with data with more repetitions.</p>

 - *collection_delay*: after setting first actuator(s) position(s), data collection is delayed, allowing the system to reach steady state

 - *initial_delay*: additional delay added to collection_delay for the first point sweep. Useful when reaching first sweep point takes somwhat longer than the rest of the points.

 - *res_in_new_dir*: dumps data in a new subfolder. Intended for <i>any_measurement</i> where a file is stored per acquisition

 - *dataset*: set dataset to plot

 - *extent_control*: dataset to use for extent control

 - *average_over_repetitions*: None

 - *position_representation*: <p>flat: flattened data per sweep point flattend and aranged in order measured<p>map_vertical: data at positions is along vertical direction of a map

 - *dset_reducer*: <p>Reduce the data to a number at each sweep point:<p>None: no reduction<p>max: maximum<p>min: minimum<p>center_index: middle data point when data per point is flattened

 - *retake_slice_start*: start index of slice to retake (inclusive)

 - *retake_slice_stop*: stop index of slice to retake (EXCLUSIVE!)

 - *re-sweep*: after current sweep is completed the measurement restarts (indefinitely) to add more repetitions. Uncheck to stop the measurement after current sweep is completed.

 - *any_measurement_0*: None

 - *any_measurement_1*: None

 - *any_setting_0*: None

 - *any_setting_1*: None

 - *blaze_repetitions*: number of times data gets collected at each position

 - *blaze_always_collect_image*: None

 - *pump_probe_repetitions*: number of times data gets collected at each position

 - *lightfield_repetitions*: number of times data gets collected at each position

 - *pump_probe_SeNsR_repetitions*: number of times data gets collected at each position

 - *powermeter_monitoring_repetitions*: number of times data gets collected at each position

 - *power_slider_repetitions*: number of times data gets collected at each position

 - *pylon_repetitions*: number of times data gets collected at each position

 - *pylon_always_collect_image*: None

 - *flame_repetitions*: number of times data gets collected at each position

 - *correlation_repetitions*: number of times data gets collected at each position

 - *lockin_repetitions*: number of times data gets collected at each position

 - *const_power_PID_repetitions*: number of times data gets collected at each position

 - *const_power_PID_always_collect_image*: None

 - *any_measurement_0_repetitions*: number of times data gets collected at each position

 - *any_measurement_1_repetitions*: number of times data gets collected at each position

 - *any_setting_0_repetitions*: number of times data gets collected at each position

 - *any_setting_1_repetitions*: number of times data gets collected at each position

 - *actuator_1*: None

 - *from_list_1*: use a manual list instead of a parametric range. Put one number per line. Comments can be added after #

 - *range_1_min*: 

 - *range_1_max*: 

 - *range_1_step*: 

 - *range_1_num*: 

 - *range_1_center*: 

 - *range_1_span*: 

 - *actuator_2*: None

 - *from_list_2*: use a manual list instead of a parametric range. Put one number per line. Comments can be added after #

 - *range_2_min*: 

 - *range_2_max*: 

 - *range_2_step*: 

 - *range_2_num*: 

 - *range_2_center*: 

 - *range_2_span*: 

