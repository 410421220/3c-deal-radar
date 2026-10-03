import json, os, time

_here = os.path.dirname(os.path.abspath(__file__))
log_file = os.environ.get('CPU_TEMP_LOG', os.path.join(_here, 'logs', 'cpu_temp.jsonl'))
try:
    with open('/sys/class/hwmon/hwmon2/temp1_input', 'r') as f:
        temp = int(f.read().strip()) / 1000.0
except (FileNotFoundError, ValueError):
    with open('/sys/class/thermal/thermal_zone2/temp', 'r') as f:
        temp = int(f.read().strip()) / 1000.0

entry = {'ts': int(time.time()), 'temp': temp}
os.makedirs(os.path.dirname(log_file), exist_ok=True)
with open(log_file, 'a') as f:
    f.write(json.dumps(entry) + '\n')
print(f'CPU temp: {temp:.1f}C')
