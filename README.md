# lightAlarm

An alarm application that uses your smart lighting and has Slack integration, because getting out of bed is a lot easier when a message is about to be sent out to your entire team if you don't. Only tested on Linux.

It works as an API, to be used with Tasker (Android) or Shortcuts (iOS). If using Tasker, the use of AutoAlarm is highly recommended as it can programmatically obtain the next alarm time.

## Usage

- Clone this repository.

- Install all the requirements by running `pip3 install -r requirements.txt`.

- Rename `config.dist.json` to `config.json`.

- Open `config.json` in any text editor and change variables as necessary. All times are in seconds.

    - **lights**: Define groups of lights here. `brand` is the device file to be used to talk to this device, `multizone` is not used in the Yeelight plug-in, and mac/ip should be self-explanatory.

    - **colors**: Colors to shift through during alarm. Each color is a list of four integers of [hue, saturation, brightness, kelvin].

    - **slack**: Optional field, used for Slack support.

        - **webhook**: The incoming webhook to use for Slack.

        - **delay**: The delay in seconds before the Slack message is sent out.

        - **messages**: A list of messages. A random message will be picked out and sent to the webhook if the alarm is not shut off on time.

    - **duration**: The total duration of alarm in seconds. If not disabled in this period, the alarm will turn itself off.

    - **colorChangeFrequency**: How often in seconds each color shift should happen. Ignored if insane mode is enabled.

    - **initialFadeIn**: The amount of time in seconds cyan light initially fades in to gently wake you up.

    - **insaneMode**: Make the alarm as annoying as possible. Do not enable if you have any form of sensitivity to flashing lights.

    - **soundPath**: Optional field, sound will be disabled if not specified. The path of a sound file to be played. ffmpeg will be used to repeatedly play it, and the volume will gradually increase until it gets to 200%.

    - **passwordHash**: SHA-512 hash of the password needed to turn off the alarm.

    - **myIP**: The IP address of the interface to listen to incoming connections from. `0.0.0.0` will listen from all interfaces, and `127.0.0.1` will only listen through the loopback interface.

    - **hostIP**: Optional field only used for Yeelight bulbs with insane mode enabled. Yeelight bulbs connect back to the host when "music mode" is activated to bypass the rate limit, and due to namespace isolation in Docker containers the host IP visible to the Docker container will always be the Docker internal network IP. In this specific case, you can provide the host IP in order to bypass what is reported to the `socket` library.

    - **hosts**: Optional field, must be an array of strings if used. If the "Host" header does not match one of the hosts provided here (don't include http:// or the port), the connection will be rejected. `localhost` and `127.0.0.1` are whitelisted by default. Useful against DNS rebinding attacks.

- If you'd like to have alarm support, run `alarm/main.py`. The only endpoints are `/set/<year>/<month>/<day>/<hour>/<minute>/<second>` and `/stop/<password>` and settings are read as documented above.

- Run `api/main.py`, or use the `docker-compose.yml` file included for your convenience.

## Endpoints

- http://<span></span>my.ip.goes.here:3000/ (GET)

    Returns the timestamp of the next scheduled alarm, or HTTP204 if there is none set.

- http://<span></span>my.ip.goes.here:5000/set (POST)

    Sets an alarm.

    - year: The year to set the alarm for.

    - month: The month to set the alarm for.

    - day: The day to set the alarm for.

    - hour: The hour to set the alarm for.

    - minute: The minute to set the alarm for.

    - second: The second to set the alarm for.

- http://<span></span>my.ip.goes.here:5000/stop (POST)

    Disarms the currently running alarm.

    - password: The password defined in the configuration file.