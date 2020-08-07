#!/usr/bin/python3

import time, subprocess, json, random, os, signal, sys, importlib, importlib.util, os.path, traceback, atexit, datetime, hashlib
import multiprocessing.dummy as multiprocessing
from functools import partial
import requests
from flask import Flask, request, abort
from flask_apscheduler import APScheduler
from retry.api import retry_call

app = Flask(__name__)
scheduler = APScheduler()

scriptPath = os.path.dirname(os.path.realpath(__file__))
skipPath = os.path.join(scriptPath, 'skip-next')
pidPath = os.path.join(scriptPath, 'alarm.pid')
soundPidPath = os.path.join(scriptPath, 'sound.pid')
configPath = os.path.join(scriptPath, 'config.json')

config = open(configPath).read()
config = json.loads(config)
lightsDict = config['lights']
colorDict = config['colors']
myIP = config['myIP']

slackDone = True
if 'slack' in config:
  slackDelay = datetime.timedelta(seconds=config['slack']['delay'])
  slackDone = False
  if os.path.exists('/var/run/secrets/lightalarm'):
      secretFile = open('/var/run/secrets/lightalarm', 'r')
      secretContents = secretFile.read()
      config['slack']['webhook'] = secretContents
      secretFile.close()

alarmRunning = False
lights = []

def module_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

for group in lightsDict:
  if 'skipGroups' not in config or group not in config['skipGroups']:
    for light in lightsDict[group]:
      module = module_from_file(light['brand'], os.path.join(scriptPath, os.path.join('devices', light['brand'] + '.py')))
      if light['multizone']:
        lights.append(module.Bulb(light['ip'], light['mac'], multizone=True))
      else:
        lights.append(module.Bulb(light['ip'], light['mac']))

@app.before_request
def beforeRequest():
  # print actual host
  print(request.url + ' - ', end='', file=sys.stderr)
  # optionally mitigate against DNS rebinding
  if 'hosts' in config:
    splitHost = request.host
    if ':' in splitHost:
      splitHost = request.host.split(':')[0]
    if splitHost != "localhost" and splitHost != "127.0.0.1":
      if splitHost not in config['hosts']:
        abort(403)

@app.route('/')
def getAlarms():
  currentJob = app.apscheduler.get_jobs()
  if len(currentJob) == 0:
    return ("No alarms found!", 204)
  return datetime.datetime.isoformat(currentJob[0].next_run_time)

@app.route('/set', methods=['POST'])
def setAlarm():
  result = "Alarm successfully set!"
  year = int(request.json['year'])
  month = int(request.json['month'])
  day = int(request.json['day'])
  hour = int(request.json['hour'])
  minute = int(request.json['minute'])
  second = int(request.json['second'])
  try:
    app.apscheduler.remove_job('alarm')
  except:
    pass
  app.apscheduler.add_job('alarm', runAlarm, run_date=datetime.datetime(year, month, day, hour, minute, second))
  return datetime.datetime(year, month, day, hour, minute, second).isoformat()

@app.route('/stop', methods=['POST'])
def stopAlarm():
  global alarmRunning
  password = request.json['password']
  try:
    sha = hashlib.sha512()
    sha.update(password.encode('utf-8'))

    if sha.hexdigest() == config['passwordHash']:
      alarmRunning = False
      try:
        pidFile = open(soundPidPath, 'r')
        pid = pidFile.read()
        pidFile.close()
        os.kill(int(pid), signal.SIGTERM)
        os.remove(soundPidPath)
      except:
        pass
      for light in lights:
        try:
          retry_call(light.set_power, fargs=[False], tries=5, delay=0.1, backoff=1.1)
        except Exception as err:
          sys.stderr.write(traceback.format_exc())
      return "Alarm successfully stopped!"
    return ("Invalid password!", 401)
  except Exception as err:
    return str(traceback.format_exc()).replace('\n', '<br>\n')

def loopSound(filePath):
  global alarmRunning
  volume = 1
  while True:
    if not (os.path.exists(pidPath)) or not alarmRunning:
      break
    p = subprocess.Popen(['ffplay', '-nodisp', '-autoexit', '-af', 'volume=' + str(volume), filePath])
    try:
      pidFile = open(soundPidPath, 'w')
      pid = p.pid
      pidFile.write(str(pid))
      pidFile.close()
      p.wait()
    except KeyboardInterrupt:
      try:
        p.kill()
      except OSError:
        pass
      p.wait()
    time.sleep(0.1) # so we don't overload the CPU on failure
    if volume < 2:
      volume = volume + 0.1

def cleanup(soundPool):
  soundPool.terminate()

def runAlarm():
  global slackDone
  global alarmRunning

  if not os.path.exists(skipPath):

    alarmRunning = True
    slackDone = False
    pidFile = open(pidPath, 'w')
    pid = os.getpid()
    pidFile.write(str(pid))
    pidFile.close()

    for light in lights:
      try:
        color = [29814, 65535, 1, 3500]
        retry_call(light.set_color, fargs=[color], tries=5, delay=0.1, backoff=1.1)
        retry_call(light.set_power, fargs=[True], tries=5, delay=0.1, backoff=1.1)
        color = [29814, 65535, 65535, 3500]
        retry_call(light.set_color, fargs=[color, config['initialFadeIn'] * 1000], tries=5, delay=0.1, backoff=1.1)
      except Exception as err:
        sys.stderr.write(traceback.format_exc())

    time.sleep(config['initialFadeIn'])

    if not alarmRunning:
      return

    startTime = datetime.datetime.now()

    soundPool = None

    if 'soundPath' in config and os.path.isfile(config['soundPath']):
      soundPool = multiprocessing.Pool(1)
      soundPool.apply_async(loopSound, [config['soundPath']])
      soundPool.close()
      atexit.register(partial(cleanup, soundPool))

    if config['insaneMode'] == True:
      hostIP = None
      if 'hostIP' in config:
        hostIP = config['hostIP']
      for light in lights:
        light.fast_mode(hostIP = hostIP)

      count = 0

      while True:
        try:
          if not (os.path.exists(pidPath)) or not alarmRunning:
            break
          count = count + 1
          if count > 6:
            for light in lights:
              light.set_power(False)

            if 'slack' in config and not slackDone:
              currentTime = datetime.datetime.now()
              if currentTime - startTime > slackDelay:
                for i in range(0, 30):
                  for light in lights:
                    try:
                      retry_call(light.set_power, fargs=[False, 500], tries=5, delay=0.1, backoff=1.1)
                    except Exception:
                      pass
                  time.sleep(0.5)
                  if not alarmRunning:
                    return
                  for light in lights:
                    try:
                      retry_call(light.set_power, fargs=[True, 500], tries=5, delay=0.1, backoff=1.1)
                    except Exception:
                      pass
                  time.sleep(0.5)
                if alarmRunning:
                  message = {
                    'payload': json.dumps({
                      'text': random.choice(config['slack']['messages'])
                    })
                  }
                  requests.post(config['slack']['webhook'], data=message)
                  slackDone = True

            time.sleep(0.1)
            for light in lights:
              light.set_power(True)
            count = 0

          for light in lights:
            color = colorDict[random.choice(list(colorDict.keys()))]
            try:
              retry_call(light.set_color, fargs=[color], tries=5, delay=0.1, backoff=1.1)
              retry_call(light.set_power, fargs=[True], tries=5, delay=0.1, backoff=1.1)
            except Exception:
              sys.stderr.write(traceback.format_exc())
        except Exception as err:
          sys.stderr.write(traceback.format_exc())
    else:
      milliseconds = config['colorChangeFrequency'] * 1000
      for i in range(0, int(config['duration'] / config['colorChangeFrequency'])):
        if not (os.path.exists(pidPath)) or not alarmRunning:
          break

        try:
          if not slackDone and 'slack' in config:
              currentTime = datetime.datetime.now()
              if currentTime - startTime > slackDelay:
                for i in range(0, 30):
                  for light in lights:
                    try:
                      retry_call(light.set_power, fargs=[False, 1000], tries=5, delay=0.1, backoff=1.1)
                    except Exception:
                      pass
                  time.sleep(1)
                  if not alarmRunning:
                    return
                  for light in lights:
                    try:
                      retry_call(light.set_power, fargs=[True, 1000], tries=5, delay=0.1, backoff=1.1)
                    except Exception:
                      pass
                  time.sleep(1)
                if alarmRunning:
                  message = {
                    'payload': json.dumps({
                    'text': random.choice(config['slack']['messages'])
                    })
                  }
                  requests.post(config['slack']['webhook'], data=message)
                  slackDone = True


          for light in lights:
            if light.supports_multizone():
              numZones = len(light.get_color_zones())
              prevColor = [-1, -1, -1, -1]
              randomColors = []
              for i in range(0, numZones):
                randomColor = colorDict[random.choice(list(colorDict.keys()))]
                while randomColor[0] == prevColor[0]:
                  randomColor = colorDict[random.choice(list(colorDict.keys()))]
                randomColor[2] = 65535
                prevColor = randomColor
                randomColors.append(randomColor)
                light.set_power(True)

              try:
                retry_call(light.set_zone_colors, fargs=[randomColors, milliseconds], tries=5, delay=0.1, backoff=1.1)
              except Exception:
                pass
            else:
              try:
                retry_call(light.set_color, fargs=[colorDict[random.choice(list(colorDict.keys()))], milliseconds], tries=5, delay=0.1, backoff=1.1)
              except:
                pass

        except Exception as err:
          sys.stderr.write(traceback.format_exc())

        finally:
          time.sleep(milliseconds / 1000)
    os.remove(pidPath)
    for light in lights:
      light.set_power(False)

  else:
    os.remove(skipPath)

if __name__ == '__main__':
  scheduler.init_app(app)
  scheduler.start()
  app.run(myIP, port=3000, threaded=False)
