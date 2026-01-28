**this file will be overwriten! **

 - Write documentation describing your app, files starting __ are ignored.

 - or add to `links.json`

## Settings

 - *activation*: <i>sweep_1d</i>

 - *run_state*: None

 - *progress*: None

 - *profile*: Run a profile on the run to find performance problems

 - *scan_mode*: <h3>Create new sweep:</h3>specify the values each actuator takes during the sweep (either by ranges or a list of positions). Use one of the following modes to define how the values are combined.
<p><i>nested:</i> Single actuator sweep. Somewhat a trivial case - I know :-)</p>
<p><i>position_list:</i> positions are defined by this Measurement's Position List.</p><br><h3>MODIFY or EXTEND previous sweep:</h3><i>never alters/deletes saved data files, always makes new files, reuses data in memory</i><p><i>RETAKE_POSITIONS:</i>: Allows to retake (fix) inidiviual data points specified in Position List. To add positions ctrl click on data. Makes a new datafile with data in memory with retaken data points updated.</p><p><i>RETAKE_SLICE:</i>: Retake a slice of data specified by start and stop indices. Makes a new datafile with data in memory with retaken data points updated.</p><p><i>ADD_REPS:</i>: Adds more repetitions to existing scan data to improve signal-to-noise ratio through additional averaging. Makes a new datafile with data with more repetitions.</p>

 - *collection_delay*: after setting the wheel position, data collection is delayed, allowing the system to reach steady state

 - *res_in_new_dir*: dumps data in a new subfolder. Intended for <i>any_measurement</i> where a file is stored per acquisition

 - *dataset*: set dataset to plot

 - *extent_control*: dataset to use for extent control

 - *average_over_repetitions*: None

 - *position_representation*: <p>flat: flattened data per sweep point flattend and aranged in order measured<p>map_vertical: data at positions is along vertical direction of a map

 - *retake_slice_start*: start index of slice to retake (inclusive)

 - *retake_slice_stop*: stop index of slice to retake (EXCLUSIVE!)

 - *re-sweep*: after current sweep is completed the measurement restarts (indefinitely) to add more repetitions. Uncheck to stop the measurement after current sweep is completed.

 - *any_measurement_0*: None

 - *any_measurement_1*: None

 - *any_setting_0*: None

 - *any_setting_1*: None

 - *any_measurement_0_repetitions*: number of times data gets collected at each position

 - *any_measurement_1_repetitions*: number of times data gets collected at each position

 - *any_setting_0_repetitions*: number of times data gets collected at each position

 - *any_setting_1_repetitions*: number of times data gets collected at each position

 - *actuator_1*: None

 - *from_list_1*: use a manual list instead of a parametric range. Put one number per line. Comments can be added after #

 - *range_1_0_min*: 

 - *range_1_0_max*: 

 - *range_1_0_step*: 

 - *range_1_0_num*: 

 - *range_1_1_min*: 

 - *range_1_1_max*: 

 - *range_1_1_step*: 

 - *range_1_1_num*: 

 - *range_1_2_min*: 

 - *range_1_2_max*: 

 - *range_1_2_step*: 

 - *range_1_2_num*: 

 - *range_1_3_min*: 

 - *range_1_3_max*: 

 - *range_1_3_step*: 

 - *range_1_3_num*: 

 - *range_1_4_min*: 

 - *range_1_4_max*: 

 - *range_1_4_step*: 

 - *range_1_4_num*: 

 - *range_1_0_is_active*: None

 - *range_1_1_is_active*: None

 - *range_1_2_is_active*: None

 - *range_1_3_is_active*: None

 - *range_1_4_is_active*: None

 - *range_1_sweep_type*: None

 - *range_1_no_duplicates*: Remove adjacent duplicates from *up* and *down* sweep ranges

