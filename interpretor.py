import math
import threading
import time

from opcodes import Opcodes


class NeoPixelInterpretor:
    def __init__(self, pixels, test_time=40, runtime=180):
        self.stop_check = False
        self.go_sem = threading.Semaphore()
        self.cmd = [[Opcodes.SECTION.value]]
        self.sect_pos = []
        self.sleep_multipliers = []
        self.state_stack = []
        self.pixels = pixels
        self.original_color = [(0, 0, 0, 0) for _ in range(len(self.pixels))]
        self.test_time = test_time
        self.runtime = runtime

    def _bytes_to_rgb(self, byt):
        color = int.from_bytes(byt, 'big')
        r = color >> 24
        g = (color >> 16) & 0xff
        b = (color >> 8) & 0xff
        o = self.compute_brightness_multiplier(color & 0xff)
        return r, g, b, o

    def c2p(self, color):
        return tuple([
            c * color[3] / 255 for c in color[:3]
        ])

    def run(self, data, mock=False, verbose=False, test=False):
        self.go_sem.acquire()
        self.sect_pos = []
        self.sleep_multipliers = []
        self.cmd = [[Opcodes.SECTION.value]]
        self.original_color = [(0, 0, 0, 0) for _ in range(len(self.pixels))]
        self.stop_check = False
        self.build_cmd_q(data)
        self.go_sem.release()
        self.do(mock, verbose, test)

    def stop(self):
        self.go_sem.acquire()
        self.stop_check = True
        self.go_sem.release()

    def build_cmd_q(self, data):
        k = 0
        single_opcode = lambda buf: ([data[buf]], buf + 1)
        move_op = lambda buf: ([
            data[buf],
            data[buf+1],
            data[buf+2],
            data[buf+3],
            data[buf+4] >> 2,
            (data[buf+4] >> 1) & 1,
            data[buf+4] & 1
        ], buf + 5)
        opcode_with_float = lambda buf: ([
            data[buf],
            int.from_bytes(data[buf + 1:buf + 3], 'big') / 1000
        ], buf + 3)
        opcode_with_int = lambda buf: ([
            data[buf],
            int.from_bytes(data[buf + 1:buf + 3], 'big')
        ], buf + 3)

        opcodes = {
            Opcodes.SET.value: lambda buf: ([
                data[buf],
                int.from_bytes(data[buf + 1:buf + 2], 'big'),
                self._bytes_to_rgb(data[buf + 2:buf + 6])
            ], buf + 6),

            Opcodes.FILL.value: lambda buf: ([
                data[buf],
                self._bytes_to_rgb(data[buf + 1:buf + 5])
            ], buf + 5),

            Opcodes.SLEEP.value: opcode_with_float,
            Opcodes.SHOW.value: single_opcode,
            Opcodes.SHOW_AND_SLEEP.value: opcode_with_float,
            Opcodes.SECTION.value: single_opcode,
            Opcodes.REPEAT.value: lambda buf: ([
                [
                    data[buf],
                    int.from_bytes(data[buf + 1:buf + 3], 'big')
                ],
                [
                    Opcodes.END_SECTION.value
                ]
            ], buf + 3),

            Opcodes.MOVE_UP.value: move_op,
            Opcodes.MOVE_DOWN.value: move_op,

            Opcodes.SET_SPEED.value: opcode_with_float,
            Opcodes.RESET_SPEED.value: single_opcode,

            Opcodes.SET_MULTIPLE.value: lambda buf: ([
                data[buf],
                [(data[buf2], self._bytes_to_rgb(data[buf2 + 1:buf2 + 5]))
                 for buf2 in range(2, 5 * data[buf + 1] + 2, 5)
                 ]
            ], buf + data[buf + 1] * 5 + 2),
            Opcodes.SET_BRIGHTNESS.value: lambda buf: ([
                data[buf],
                data[buf+1],
                data[buf+2]
            ], buf + 3),

        }
        while k < len(data):
            opcode = data[k]
            cmd, k = opcodes[opcode](k)

            if isinstance(cmd[0], list):
                self.cmd += cmd
            else:
                self.cmd.append(cmd)

    def should_stop(self):
        self.go_sem.acquire()
        val = self.stop_check
        self.go_sem.release()
        return val

    def _log(self, tabs, message):
        print(f'{tabs}{message}')

    def compute_should_sleep(self, cmd, crt):
        sleep_value = cmd[1] * self.sleep_multipliers[-1]
        sleep_now = 0
        if sleep_value > 0:
            if sleep_value >= 1:
                self.cmd[crt][1] -= 1
                sleep_now = 1
            else:
                sleep_now = cmd[1]
                self.cmd[crt][1] = 0
        return sleep_now

    def compute_brightness_multiplier(self, o):
        return int(((o / 100) ** 1.25) * 255)

    def do(self, mock=False, verbose=False, test=False):
        tabs = ''
        start_time = time.time()
        crt = 0
        while crt < len(self.cmd):
            cmd = self.cmd[crt]
            if cmd[0] == Opcodes.SECTION.value:
                if verbose:
                    self._log(tabs, "===Section===")
                tabs += '\t'
                self.sect_pos.append(crt + 1)
                self.sleep_multipliers.append(
                    1 if not self.sleep_multipliers else self.sleep_multipliers[-1]
                )
                self.state_stack.append(
                    self.original_color.copy()
                )
                crt += 1
                continue
            elif cmd[0] == Opcodes.END_SECTION.value:
                if len(tabs):
                    tabs = tabs[:-1]
                if verbose:
                    self._log(tabs, "===End section===")
                self.sleep_multipliers.pop()
                self.state_stack.pop()
                self.sect_pos.pop()
                crt += 1
                continue

            if self.should_stop():
                break

            if test and time.time() - start_time > self.test_time:
                break

            if not test and time.time() - start_time > self.runtime:
                break

            if cmd[0] == Opcodes.SET.value:
                px_c = self.c2p(cmd[2])
                if not mock:
                    self.original_color[cmd[1]] = cmd[2]
                    self.pixels[cmd[1]] = px_c
                if verbose:
                    self._log(tabs, f"set[{cmd[1]}] = {px_c}")
            elif cmd[0] == Opcodes.FILL.value:
                px_c = self.c2p(cmd[1])
                if not mock:
                    self.original_color = [cmd[1] for _ in range(len(self.original_color))]
                    self.pixels.fill(px_c)
                if verbose:
                    self._log(tabs, f"fill({px_c})")
            elif cmd[0] == Opcodes.SLEEP.value:
                sleep_now = self.compute_should_sleep(cmd, crt)
                sleep_value = self.cmd[crt][1] * self.sleep_multipliers[-1]
                if sleep_now:
                    if verbose:
                        self._log(tabs, f"sleep({sleep_now}){f', left={sleep_value}' if sleep_value else ''}")
                    if not mock and sleep_now:
                        time.sleep(sleep_now)
                    continue
            elif cmd[0] == Opcodes.SHOW.value:
                if not mock:
                    self.pixels.show()
                if verbose:
                    self._log(tabs, "show()")
            elif cmd[0] == Opcodes.MOVE_UP.value:
                lb, ub, sp = cmd[1:4]
                trail, rotate, show = cmd[4:7]
                if not mock:
                    vector = self.original_color[lb:ub + 1].copy()
                    vector = (vector[-sp:] if rotate else (
                        [vector[0] for _ in range(sp)] if trail else [(0, 0, 0, 0) for _ in range(sp)]
                    )) + vector[:-sp]

                    for i in range(lb, ub + 1):
                        self.original_color[lb+i] = vector[i]
                        self.pixels[lb + i] = self.c2p(vector[i])

                    if show:
                        self.pixels.show()
                if verbose:
                    self._log(tabs, f"move_up([{lb}, {ub}], spaces={sp}"
                                    f"{', trail' if trail else ''}"
                                    f"{', rotate' if rotate else ''})"
                              )
                    if show:
                        self._log(tabs, "show()")
            elif cmd[0] == Opcodes.MOVE_DOWN.value:
                lb, ub, sp = cmd[1:4]
                trail, rotate, show = cmd[4:7]
                if not mock:
                    vector = self.original_color[lb:ub + 1].copy()

                    vector = vector[sp:] + (
                        vector[sp:] if rotate else (
                            [vector[ub] for _ in range(sp)] if trail else [(0, 0, 0, 0) for _ in range(sp)]
                        )
                    )

                    for i in range(lb, ub + 1):
                        self.original_color[lb + i] = vector[i]
                        self.pixels[lb + i] = self.c2p(vector[i])

                    if show:
                        self.pixels.show()
                if verbose:
                    self._log(tabs, f"move_down([{lb}, {ub}], spaces={sp}"
                                    f"{', trail' if trail else ''}"
                                    f"{', rotate' if rotate else ''})"
                              )
                    if show:
                        self._log(tabs, "show()")
            elif cmd[0] == Opcodes.REPEAT.value:
                if verbose:
                    self._log(tabs, f"> loop {cmd[1]} times")
                if not mock:
                    if cmd[1] - 1 > 0:
                        self.cmd[crt][1] -= 1
                        crt = self.sect_pos[-1]
                        for index in range(len(self.pixels)):
                            self.original_color[index] = self.state_stack[-1][index]
                            self.pixels[index] = self.c2p(self.original_color[index])
                        self.sleep_multipliers[-1] = 1 if len(self.sleep_multipliers) == 1 else self.sleep_multipliers[-2]
                        continue
            elif cmd[0] == Opcodes.SET_MULTIPLE.value:
                if verbose:
                    self._log(tabs, "===SET===")
                    tabs += '\t'
                    for s in cmd[1]:
                        self._log(tabs, f"set[{s[0]}] = {self.c2p(s[1])}")
                    tabs = tabs[:-1]
                    self._log(tabs, "===END=SET===")
                if not mock:
                    for index, color in cmd[1]:
                        self.original_color[index] = color
                        self.pixels[index] = self.c2p(self.original_color)
            elif cmd[0] == Opcodes.SHOW_AND_SLEEP.value:
                self.cmd[crt][0] = Opcodes.SLEEP.value
                if not mock:
                    self.pixels.show()
                if verbose:
                    self._log(tabs, f"show(sleep)")
                continue
            elif cmd[0] == Opcodes.RESET_SPEED.value:
                self.sleep_multipliers[-1] = 1
                if verbose:
                    self._log(tabs, f"reset_speed()")
            elif cmd[0] == Opcodes.SET_SPEED.value:
                self.sleep_multipliers[-1] = cmd[1]
                if verbose:
                    self._log(tabs, f"speed = {math.ceil(1 / cmd[1] * 100) / 100}")
            else:
                raise ValueError(f"Invalid opcode in command! Got {cmd[0]}")

            crt += 1

        if self.pixels and not isinstance(self.pixels, list):
            self.pixels.fill((0, 0, 0))
