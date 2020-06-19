# zwave-scene-dimmer
This is a custom component for Home Assistant that allows for dimming or
brightening lights using a zwave controller that sends a scene when a button
is held and another scene when the button is released.

In theory this can be accomplished through the automation and script interface
of Home Assistant, but the results were unsatisfactory - dimming and brightening
continued after the button was released as back-logged commands were sent.

This custom component avoids that problem by using blocking calls to
`light.brightness_step`. If the zwave network is congested (for example on
startup) or there is some other delay, the light will be slower to
brighten or dim, but the change will stop immediately on release of the
button.

# Configuration
To configure the component, you will need to know the `scene_id` and optional
`scene_data` for the button press (to start) and release (to stop). Set these
for both `bright` (increasing brightness) and `dim` (decreasing brightness).

You may also set optional parameters for each zwave controller. `step` is the
integer value from 0..255 to step the light. `delay` is how quickly (in seconds)
to run the next step after the previous update completes if the button is still 
being depressed. The default `step` is 12 and `delay` is 0.1.

```yaml
zwave_scene_dimmer: # example configuration.yaml entry
  zwave.reading_light_switch: # name of zwave device to monitor
    light_id: light.reading # name of light to control
    bright:
      start_scene_id: 2
      start_scene_data: 7800
      stop_scene_id: 2
      stop_scene_data: 7740
    dim:
      start_scene_id: 1
      start_scene_data: 7800
      stop_scene_id: 1
      stop_scene_data: 7740
```
