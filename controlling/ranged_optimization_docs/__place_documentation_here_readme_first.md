**this file will be overwriten! **

 - Write documentation describing your app, files starting __ are ignored.

 - or add to `links.json`

## Settings

 - *activation*: <i>ranged_optimization</i>

 - *run_state*: None

 - *progress*: None

 - *profile*: Run a profile on the run to find performance problems

 - *f*: 
<p>Sweeps a setting z within a range, measures an optimization quantity f(z)
and calculates z0 such that:</p>
<p>f(z0) >= f(z) for all z</p>
<p>finally sets z = z0 + z_offset</p>


 - *N_samples*: None

 - *sampling_period*: time waited between sampling

 - *use_current_z_as_center*: instead of <b>z_center</b> the current value of <b>z</b> is used

 - *z_min*: defines a range over which <b>z</b> is varied

 - *z_max*: defines a range over which <b>z</b> is varied

 - *z_step*: defines a range over which <b>z</b> is varied

 - *z_num*: defines a range over which <b>z</b> is varied

 - *z_center*: defines a range over which <b>z</b> is varied

 - *z_span*: defines a range over which <b>z</b> is varied

 - *z_offset*: an offset that will be applied when moving to optimal <i>z</i> value after optimization

 - *use_fine_optimization*: optimization runs again around z0 from first run

 - *coarse_to_fine_span_ratio*: None

 - *z_span_travel_time*: None

 - *z*: path to a setting that can manipulate the sweep value z

 - *z_read*: if not <i>same_as_z</i> this setting will be used to get actual value of z

 - *post_processor*: e.g. fit gaussian to data and use the derived mean as optimized value

 - *take_post_process_value*: None

 - *save_h5*: None

