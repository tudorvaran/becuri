import math
import threading
import time

from opcodes import Opcodes


class NeoPixelInterpretor:
    def __init__(self, pixels, num_px, test_time=40, runtime=180):
        self.stop_check = False
        self.num_px = num_px
        self.go_sem = threading.Semaphore()
        self.sect_pos = []
        self.sleep_multipliers = []
        self.state_stack = []
        self.pixels = pixels
        self.original_color = [(0, 0, 0, 0) for _ in range(num_px)]
        self.test_time = test_time
        self.runtime = runtime
        self._build_opcode_list()
        self.tabs = ''

    def _build_opcode_list(self):
        single_opcode = lambda args: ([args[0][args[1]]], args[1] + 1)
        move_op = lambda args: ([
                                   args[0][args[1]],
                                   args[0][args[1] + 1],
                                   args[0][args[1] + 2],
                                   args[0][args[1] + 3],
                                   args[0][args[1] + 4] >> 2,
                                   (args[0][args[1] + 4] >> 1) & 1,
                                   args[0][args[1] + 4] & 1
                               ], args[1] + 5)
        opcode_with_float = lambda args: ([
                                             args[0][args[1]],
                                             int.from_bytes(args[0][args[1] + 1:args[1] + 3], 'big') / 1000
                                         ], args[1] + 3)
        opcode_with_float_duplicate_value = lambda args: ([
            args[0][args[1]],
            int.from_bytes(args[0][args[1] + 1:args[1] + 3], 'big') / 1000,
            int.from_bytes(args[0][args[1] + 1:args[1] + 3], 'big') / 1000
        ], args[1] + 3)

        self.opcodes = {
            Opcodes.SET.value: lambda args: ([
                                                args[0][args[1]],
                                                int.from_bytes(args[0][args[1] + 1:args[1] + 2], 'big'),
                                                self._bytes_to_rgb(args[0][args[1] + 2:args[1] + 6])
                                            ], args[1] + 6),

            Opcodes.FILL.value: lambda args: ([
                                                 args[0][args[1]],
                                                 self._bytes_to_rgb(args[0][args[1] + 1:args[1] + 5])
                                             ], args[1] + 5),

            Opcodes.SLEEP.value: opcode_with_float_duplicate_value,
            Opcodes.SHOW.value: single_opcode,
            Opcodes.SHOW_AND_SLEEP.value: lambda args: ([
                [Opcodes.SHOW.value],
                opcode_with_float_duplicate_value(args)[0],
            ], args[1] + 3),
            Opcodes.SECTION.value: single_opcode,
            Opcodes.REPEAT.value: lambda args: ([
                                                   [
                                                       args[0][args[1]],
                                                       int.from_bytes(args[0][args[1] + 1:args[1] + 3], 'big'),
                                                       int.from_bytes(args[0][args[1] + 1:args[1] + 3], 'big')
                                                   ],
                                                   [
                                                       Opcodes.END_SECTION.value
                                                   ]
                                               ], args[1] + 3),

            Opcodes.MOVE_UP.value: move_op,
            Opcodes.MOVE_DOWN.value: move_op,

            Opcodes.SET_SPEED.value: opcode_with_float,
            Opcodes.RESET_SPEED.value: single_opcode,

            Opcodes.SET_MULTIPLE.value: lambda args: (
                [
                    args[0][args[1]],
                    [
                        (args[0][args[1] + buf2], self._bytes_to_rgb(args[0][args[1] + buf2 + 1:args[1] + buf2 + 5]))
                        for buf2 in range(2, 5 * args[0][args[1] + 1] + 2, 5)
                    ]
                ], args[1] + args[0][args[1] + 1] * 5 + 2
            ),
            Opcodes.SET_BRIGHTNESS.value: lambda args: ([
                                                           args[0][args[1]],
                                                           args[0][args[1] + 1],
                                                           args[0][args[1] + 2]
                                                       ], args[1] + 3),
            Opcodes.END_SECTION.value: single_opcode

        }

    def interpret_opcode(self, buffer, k=0):
        return self.opcodes[buffer[k]]((buffer, k))

    def reset_verbose(self):
        self.tabs = ''

    def interpret_and_mock_run(self, buffer, verbose=False):
        cmdlist, _ = self.interpret_opcode(buffer)
        self.do(cmdlist if isinstance(cmdlist[0], list) else [cmdlist], mock=True, verbose=verbose)

    def _bytes_to_rgb(self, byt):
        color = int.from_bytes(byt, 'big')
        r = color >> 24
        g = (color >> 16) & 0xff
        b = (color >> 8) & 0xff
        l = color & 0xff
        return r, g, b, l

    def c2p(self, color):
        brightness = self.compute_brightness_multiplier(color[3])
        return tuple([
            c * brightness / 255 for c in color[:3]
        ])

    def run(self, data, mock=False, verbose=False, test=False):
        self.go_sem.acquire()
        self.sect_pos = []
        self.sleep_multipliers = []
        self.original_color = [(0, 0, 0, 0) for _ in range(len(self.pixels))]
        if verbose:
            self.reset_verbose()
        self.stop_check = False
        cmdlist = self.build_cmd_q(data)
        self.go_sem.release()
        self.do(cmdlist, mock, verbose, test)

    def stop(self):
        self.go_sem.acquire()
        self.stop_check = True
        self.go_sem.release()

    def build_cmd_q(self, data):
        k = 0
        cmdlist = [[Opcodes.SECTION.value]]
        while k < len(data):
            cmd, k = self.interpret_opcode(data, k)

            if isinstance(cmd[0], list):
                cmdlist += cmd
            else:
                cmdlist.append(cmd)
        return cmdlist

    def should_stop(self):
        self.go_sem.acquire()
        val = self.stop_check
        self.go_sem.release()
        return val

    def _log(self, tabs, message):
        print(f'{tabs}{message}')

    def compute_should_sleep(self, cmdlist, crt):
        cmd = cmdlist[crt]
        sleep_value = cmd[1] * self.sleep_multipliers[-1]
        sleep_now = 0
        if sleep_value > 0:
            if sleep_value >= 1:
                cmdlist[crt][1] -= self.sleep_multipliers[-1]
                sleep_now = 1
            else:
                sleep_now = cmd[1]
                cmdlist[crt][1] = cmdlist[crt][2]
        return sleep_now

    def compute_brightness_multiplier(self, o):
        return int(((o / 100) ** 1.25) * 255)

    def do(self, cmdlist, mock=False, verbose=False, test=False):
        start_time = time.time()
        crt = 0
        while crt < len(cmdlist):
            cmd = cmdlist[crt]
            if cmd[0] == Opcodes.SECTION.value:
                if verbose:
                    self._log(self.tabs, "===Section===")
                self.tabs += '\t'
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
                if len(self.tabs):
                    self.tabs = self.tabs[:-1]
                if verbose:
                    self._log(self.tabs, "===End section===")
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
                self.original_color[cmd[1]] = cmd[2]
                if not mock:
                    self.pixels[cmd[1]] = px_c
                if verbose:
                    self._log(self.tabs, f"set[{cmd[1]}] = {px_c}")
            elif cmd[0] == Opcodes.FILL.value:
                px_c = self.c2p(cmd[1])
                self.original_color = [cmd[1] for _ in range(len(self.original_color))]
                if not mock:
                    self.pixels.fill(px_c)
                if verbose:
                    self._log(self.tabs, f"fill({px_c})")
            elif cmd[0] == Opcodes.SLEEP.value:
                sleep_now = self.compute_should_sleep(cmdlist, crt)
                sleep_value = cmdlist[crt][1] * self.sleep_multipliers[-1]
                if sleep_now:
                    if verbose:
                        if cmdlist[crt][1] != cmdlist[crt][2]:
                            self._log(self.tabs, f"sleep({sleep_now + sleep_value})")
                        else:
                            self._log(self.tabs, f"sleep({sleep_now})")
                    if not mock and sleep_now:
                        time.sleep(sleep_now)
                        if cmdlist[crt][1] != cmdlist[crt][2]:
                            continue
            elif cmd[0] == Opcodes.SHOW.value:
                if not mock:
                    self.pixels.show()
                if verbose:
                    self._log(self.tabs, "show()")
            elif cmd[0] == Opcodes.MOVE_UP.value:
                lb, ub, sp = cmd[1:4]
                trail, rotate, show = cmd[4:7]
                vector = self.original_color[lb:ub + 1].copy()
                vector = (vector[-sp:] if rotate else (
                    [vector[0] for _ in range(sp)] if trail else [(0, 0, 0, 0) for _ in range(sp)]
                )) + vector[:-sp]

                for i in range(lb, ub + 1):
                    self.original_color[lb + i] = vector[i]
                    if not mock and 0 <= lb + i < self.num_px:
                        self.pixels[lb + i] = self.c2p(vector[i])

                if not mock and show:
                    self.pixels.show()
                if verbose:
                    self._log(self.tabs, f"move_up([{lb}, {ub}], spaces={sp}"
                                    f"{', trail' if trail else ''}"
                                    f"{', rotate' if rotate else ''})"
                              )
                    if show:
                        self._log(self.tabs, "show()")
            elif cmd[0] == Opcodes.MOVE_DOWN.value:
                lb, ub, sp = cmd[1:4]
                trail, rotate, show = cmd[4:7]
                vector = self.original_color[lb:ub + 1].copy()

                vector = vector[sp:] + (
                    vector[sp:] if rotate else (
                        [vector[ub] for _ in range(sp)] if trail else [(0, 0, 0, 0) for _ in range(sp)]
                    )
                )

                for i in range(lb, ub + 1):
                    self.original_color[lb + i] = vector[i]
                    if not mock and 0 <= lb + i < self.num_px:
                        self.pixels[lb + i] = self.c2p(vector[i])

                if not mock and show:
                    self.pixels.show()
                if verbose:
                    self._log(self.tabs, f"move_down([{lb}, {ub}], spaces={sp}"
                                    f"{', trail' if trail else ''}"
                                    f"{', rotate' if rotate else ''})"
                              )
                    if show:
                        self._log(self.tabs, "show()")
            elif cmd[0] == Opcodes.REPEAT.value:
                if verbose:
                    self._log(self.tabs, f"> loop {cmd[1]} times")
                if not mock:
                    if cmd[1] - 1 > 0:
                        cmdlist[crt][1] -= 1
                        crt = self.sect_pos[-1]
                        for index in range(len(self.pixels)):
                            self.original_color[index] = self.state_stack[-1][index]
                            self.pixels[index] = self.c2p(self.original_color[index])
                        self.sleep_multipliers[-1] = 1 if len(self.sleep_multipliers) == 1 else self.sleep_multipliers[-2]
                        continue
                    else:
                        cmdlist[crt][1] = cmdlist[crt][2]
            elif cmd[0] == Opcodes.SET_MULTIPLE.value:
                if verbose:
                    self._log(self.tabs, "===SET===")
                    self.tabs += '\t'
                    for s in cmd[1]:
                        self._log(self.tabs, f"set[{s[0]}] = {self.c2p(s[1])}")
                    self.tabs = self.tabs[:-1]
                    self._log(self.tabs, "===END=SET===")

                for index, color in cmd[1]:
                    self.original_color[index] = color
                    if not mock:
                        self.pixels[index] = self.c2p(color)
            elif cmd[0] == Opcodes.SHOW_AND_SLEEP.value:
                cmdlist[crt][0] = Opcodes.SLEEP.value
                continue
            elif cmd[0] == Opcodes.RESET_SPEED.value:
                self.sleep_multipliers[-1] = 1
                if verbose:
                    self._log(self.tabs, f"reset_speed()")
            elif cmd[0] == Opcodes.SET_SPEED.value:
                self.sleep_multipliers[-1] = cmd[1]
                if verbose:
                    self._log(self.tabs, f"speed = {math.ceil(1 / cmd[1] * 100) / 100}")
            else:
                raise ValueError(f"Invalid opcode in command! Got {cmd[0]}")

            crt += 1

        if self.pixels and not isinstance(self.pixels, list):
            self.pixels.fill((0, 0, 0))
