#!/usr/bin/python3
# -*- coding: utf-8 -*-

# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import atexit
import os
from jtop import jtop, JtopException
from prometheus_client.core import InfoMetricFamily, GaugeMetricFamily, REGISTRY, CounterMetricFamily
from prometheus_client import make_wsgi_app
from wsgiref.simple_server import make_server
from base64 import b64encode

class CustomCollector(object):
    def __init__(self):
        atexit.register(self.cleanup)
        self._jetson = jtop()
        self._jetson.start()

    def cleanup(self):
        print("Closing jetson-stats connection...")
        self._jetson.close()

    def collect(self):
        if self._jetson.ok():
            #
            # Board info
            #
            i = InfoMetricFamily('gpu_info_board', 'Board sys info', labels=['board_info'])
            i.add_metric(['info'], {
                'machine': self._jetson.board['info']['machine'] if 'machine' in self._jetson.board.get('info', {}) else self._jetson.board['hardware']['Module'],
                'jetpack': self._jetson.board['info']['jetpack'] if 'jetpack' in self._jetson.board.get('info', {}) else self._jetson.board['hardware']['Jetpack'],
                'l4t':  self._jetson.board['info']['L4T'] if 'L4T' in self._jetson.board.get('info', {}) else self._jetson.board['hardware']['L4T']
                })
            yield i

            i = InfoMetricFamily('gpu_info_hardware', 'Board hardware info', labels=['board_hw'])
            i.add_metric(['hardware'], {
                'codename': self._jetson.board['hardware'].get('Codename', self._jetson.board['hardware'].get('CODENAME', 'unknown')),
                'soc': self._jetson.board['hardware'].get('SoC', self._jetson.board['hardware'].get('SOC', 'unknown')),
                'module': self._jetson.board['hardware'].get('P-Number', self._jetson.board['hardware'].get('MODULE', 'unknown')),
                'board': self._jetson.board['hardware'].get('699-level Part Number', self._jetson.board['hardware'].get('BOARD', 'unknown')),
                'cuda_arch_bin': self._jetson.board['hardware'].get('CUDA Arch BIN', self._jetson.board['hardware'].get('CUDA_ARCH_BIN', 'unknown')),
                'serial_number': self._jetson.board['hardware'].get('Serial Number', self._jetson.board['hardware'].get('SERIAL_NUMBER', 'unknown')),
                })
            yield i

            #
            # NV power mode
            #
            i = InfoMetricFamily('gpu_nvpmode', 'NV power mode', labels=['nvpmode'])
            i.add_metric(['mode'], {'mode': self._jetson.nvpmodel.name})
            yield i

            #
            # System uptime
            #
            g = GaugeMetricFamily('gpu_uptime', 'System uptime', labels=['uptime'])
            days = self._jetson.uptime.days
            seconds = self._jetson.uptime.seconds
            hours = seconds//3600
            minutes = (seconds//60) % 60
            g.add_metric(['days'], days)
            g.add_metric(['hours'], hours)
            g.add_metric(['minutes'], minutes)
            yield g

            #
            # CPU usage
            #
            g = GaugeMetricFamily('gpu_usage_cpu', 'CPU % schedutil', labels=['cpu'])
            g.add_metric(['cpu_1'], self._jetson.stats['CPU1'] if 'CPU1' in self._jetson.stats else 0)
            g.add_metric(['cpu_2'], self._jetson.stats['CPU2'] if 'CPU2' in self._jetson.stats else 0)
            g.add_metric(['cpu_3'], self._jetson.stats['CPU3'] if 'CPU3' in self._jetson.stats else 0)
            g.add_metric(['cpu_4'], self._jetson.stats['CPU4'] if 'CPU4' in self._jetson.stats else 0)
            g.add_metric(['cpu_5'], self._jetson.stats['CPU5'] if 'CPU5' in self._jetson.stats else 0)
            g.add_metric(['cpu_6'], self._jetson.stats['CPU6'] if 'CPU6' in self._jetson.stats else 0)
            g.add_metric(['cpu_7'], self._jetson.stats['CPU7'] if 'CPU7' in self._jetson.stats else 0)
            g.add_metric(['cpu_8'], self._jetson.stats['CPU8'] if 'CPU8' in self._jetson.stats else 0)
            yield g

            # 
            # RAM usage
            #
            g = GaugeMetricFamily('gpu_usage_ram', 'Memory usage', labels=['ram'])
            g.add_metric(['used'], self._jetson.memory['RAM']['used'])
            g.add_metric(['shared'], self._jetson.memory['RAM']['shared'])
            g.add_metric(['total'], self._jetson.memory['RAM']['tot'])
            g.add_metric(['free'], self._jetson.memory['RAM']['free'])
            yield g

            # 
            # Disk usage
            #
            g = GaugeMetricFamily('gpu_usage_disk', 'Disk space usage', labels=['disk'])
            g.add_metric(['used'], self._jetson.disk['used'])
            g.add_metric(['total'], self._jetson.disk['total'])
            g.add_metric(['available'], self._jetson.disk['available'])
            g.add_metric(['available_no_root'], self._jetson.disk['available_no_root'])
            yield g

            #
            # GPU usage
            #
            g = GaugeMetricFamily('gpu_usage_gpu', 'GPU % schedutil', labels=['gpu'])
            g.add_metric(['val'], self._jetson.stats['GPU'])
            yield g

            #
            # Fan usage
            #
            g = GaugeMetricFamily('gpu_usage_fan', 'Fan usage', labels=['fan'])
            g.add_metric(['speed'], self._jetson.fan.get('speed', self._jetson.fan.get('pwmfan', {'speed': [0] })['speed'][0]))
            yield g

            #
            # Sensor temperatures
            #
            g = GaugeMetricFamily('gpu_temperatures', 'Sensor temperatures', labels=['temperature'])
            keys = ['gpu', 'cpu', 'soc0', 'tj']
            for key in keys:
                if key in self._jetson.temperature:
                    g.add_metric([key.lower()], self._jetson.temperature[key]['temp'] if isinstance(self._jetson.temperature[key], dict) else self._jetson.temperature.get(key, 0))
            yield g
            #
            # Power
            #
            g = GaugeMetricFamily('gpu_usage_power', 'Power usage', labels=['power'])
            if isinstance(self._jetson.power, dict):
                g.add_metric(['cpu_gpu_cv'], self._jetson.power['rail']['VDD_CPU_GPU_CV']['avg'])
                g.add_metric(['soc'], self._jetson.power['rail']['VDD_SOC']['avg'])
                g.add_metric(['total'], self._jetson.power['tot']['avg'])
            yield g

            #
            # Processes
            #
            try:
                processes = self._jetson.processes
                # key exists in dict
                i = InfoMetricFamily('gpu_processes', 'Process usage', labels=['process'])
                for index in range(len(processes)):
                    i.add_metric(['info'], {
                        'pid': str(processes[index][0]),
                        'user': processes[index][1],
                        'gpu': processes[index][2],
                        'type': processes[index][3],
                        'priority': str(processes[index][4]),
                        'state': processes[index][5],
                        'cpu': str(processes[index][6]),
                        'memory': str(processes[index][7]),
                        'gpu_memory': str(processes[index][8]),
                        'name': processes[index][9],
                    })
                yield i
            except AttributeError:
                # key doesn't exist in dict
                i = 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=9998, help='Metrics collector port number')
    args = parser.parse_args()

    REGISTRY.register(CustomCollector())
    app = make_wsgi_app()
    httpd = make_server('', int(args.port), app)
    print('Serving on port: ', args.port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('Goodbye!')
