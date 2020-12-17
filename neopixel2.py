import math
import os
import zlib

from opcodes import Opcodes
from interpretor import NeoPixelInterpretor


class Neopixel:
    def __init__(self, num_px, filename, verbose=False):
        self.num_px = num_px
        self.filename = filename
        self.interpretor = NeoPixelInterpretor(None, num_px=num_px)
        self.warnings = set()
        self.verbose = verbose

        self.fd = open(self.filename, 'wb')
        self.data = b''
        self.stack_sleep = []
        self.section()

    def __process_color(self, color):
        if len(color) == 3:
            return color + (100,)
        return color

    def __validate_index(self, key):
        if isinstance(key, slice):
            if key.start < 0:
                key.start += self.num_px
            if key.stop < 0:
                key.stop += self.num_px
            if key.start < 0 or key.start >= self.num_px:
                raise IndexError(f"Slice start has invalid value {key.start}! Accepted values (-{self.num_px}, {self.num_px})")
            if key.stop < 1 or key.stop > self.num_px:
                raise IndexError(f"Slice stop has invalid value {key.stop}! Accepted values (-{self.num_px}, {self.num_px})")
        if key < 0:
            key += self.num_px
        if key < 0 or key >= self.num_px:
            raise IndexError(f"Out of bounds for index key ({key}! Accepted values (-{self.num_px}, {self.num_px})")

    def __validate_bounds(self, lower_bound, upper_bound, spaces, trail=False, rotate=False):
        if lower_bound < 0 or lower_bound >= self.num_px:
            raise ValueError(f"Wrong lower bound {lower_bound}, must be in interval [0, {self.num_px})")
        if upper_bound < 0 or upper_bound >= self.num_px:
            raise ValueError(f"Wrong upper bound {upper_bound}, must be in interval [0, {self.num_px})")
        if trail and rotate:
            raise ValueError("Cannot use trail and rotate simultaneously")
        if spaces < 0 or spaces > self.num_px:
            raise ValueError(f"Cannot move {spaces}, must be in interval [1, {self.num_px - 1}")

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            raise TypeError("Slices are not accepted")
        self.__validate_index(key)
        value = self.__process_color(value)
        self._w(Opcodes.SET, int.to_bytes(key, 1, byteorder='big'), self._rgb_to_bytes(value))

    def __getitem__(self, index):
        return self.interpretor.original_color[index]

    def _rgb_to_bytes(self, color):
        for index, b in enumerate(color[:3]):
            if b < 0 or b > 255:
                raise ValueError(f"Invalid color value {b} for index {index} in color. Range = [0, 255]")
        if color[3] < 0 or color[3] > 100:
            raise ValueError(f"Invalid brightness value {color[3]}. Range = [0, 255]")

        new_color = tuple(int(b) for b in color)
        if new_color != color:
            self.warnings.add('Implicit int conversion')

        return ((new_color[0] << 24) + (new_color[1] << 16) + (new_color[2] << 8) + new_color[3]).to_bytes(4, byteorder='big')

    def _w(self, *data):
        buffer = b''
        for d in data:
            if isinstance(d, tuple):
                buffer += self._rgb_to_bytes(d)
            elif isinstance(d, Opcodes):
                buffer += d.value.to_bytes(1, byteorder='big')
            else:
                buffer += d
        self.interpretor.interpret_and_mock_run(buffer, verbose=self.verbose)
        self.data += buffer

    def sleep(self, time):
        if time < 0 or time > 60:
            raise ValueError("Time to sleep should be in interval [0, 60]s")
        milliseconds = math.ceil(time * 1000 * self.interpretor.sleep_multipliers[-1])
        self.stack_sleep[-1] += milliseconds
        self._w(Opcodes.SLEEP, int.to_bytes(milliseconds & 0xffff, 2, byteorder='big'))

    def accelerate(self, delta_multiplier=0.005):
        if self.interpretor.sleep_multipliers[-1] - delta_multiplier <= 0:
            raise ValueError("Accelerates too much!")
        multiplier = self.interpretor.sleep_multipliers[-1] - delta_multiplier
        multi = math.ceil(multiplier * 1000)
        self._w(Opcodes.SET_SPEED, int.to_bytes(multi, 2, byteorder='big'))

    def decelerate(self, delta_multiplier=0.005):
        if self.interpretor.sleep_multipliers[-1] + delta_multiplier >= 100:
            raise ValueError("Decelerates too much")
        multiplier = self.interpretor.sleep_multipliers[-1] + delta_multiplier
        multi = math.ceil(multiplier * 1000)
        self._w(Opcodes.SET_SPEED, int.to_bytes(multi, 2, byteorder='big'))

    def set_multiplier(self, multiplier):
        if multiplier <= 0 or multiplier >= 100:
            raise ValueError("Multiplier should be in range [0, 100]")
        multi = math.ceil(multiplier * 1000)
        self._w(Opcodes.SET_SPEED, int.to_bytes(multi, 2, byteorder='big'))

    def reset_speed(self):
        self._w(Opcodes.RESET_SPEED)

    def get_speed(self):
        return 1 / self.interpretor.sleep_multipliers[-1] if self.interpretor.sleep_multipliers else 1

    def fill(self, color):
        color = self.__process_color(color)
        self._w(Opcodes.FILL, color)

    def show(self, sleep=None):
        if not sleep:
            self._w(Opcodes.SHOW)
            return

        if sleep < 0 or sleep > 60:
            raise ValueError("Time to sleep should be in interval [0, 60]")
        milliseconds = math.ceil(sleep * 1000 * self.interpretor.sleep_multipliers[-1])
        self.stack_sleep[-1] += milliseconds
        self._w(
            Opcodes.SHOW_AND_SLEEP,
            int.to_bytes(milliseconds & 0xffff, 2, byteorder='big')
        )

    def section(self):
        self.stack_sleep.append(0)
        self._w(Opcodes.SECTION)

    def _merge_sleep_time(self, times):
        if len(self.stack_sleep) > 1:
            top_stack_time = self.stack_sleep.pop() * (times + 1)
            self.stack_sleep[-1] += top_stack_time
        else:
            self.stack_sleep[0] *= times

    def repeat(self, times=1):
        if times < 1 or times > 0xffff:
            raise ValueError(f"Repeat times should be in interval [0, {0xffff}]")
        self._merge_sleep_time(times)
        self._w(Opcodes.REPEAT, int.to_bytes(times & 0xffff, 2, byteorder='big'))

    def _write_move_operation(self, opcode, spaces, lower_bound, upper_bound, trail, rotate, occupy):
        self._w(
            opcode,
            int.to_bytes(lower_bound, 1, byteorder='big'),
            int.to_bytes(upper_bound, 1, byteorder='big'),
            int.to_bytes(spaces, 1, byteorder='big'),
            int.to_bytes(
                (trail << 2) | (rotate << 1) | occupy,
                1, byteorder='big'
            )
        )

    def move_up(self, spaces=1, lower_bound=0, upper_bound=None, trail=False, rotate=False, show=False):
        if upper_bound is None:
            upper_bound = self.num_px - 1

        self.__validate_bounds(lower_bound, upper_bound, spaces, trail, rotate)

        self._write_move_operation(Opcodes.MOVE_UP, spaces, lower_bound, upper_bound, trail, rotate, show)

    def move_down(self, spaces=1, lower_bound=0, upper_bound=None, trail=False, rotate=False, show=False):
        if upper_bound is None:
            upper_bound = self.num_px - 1

        self.__validate_bounds(lower_bound, upper_bound, spaces, trail, rotate)

        self._write_move_operation(Opcodes.MOVE_DOWN, spaces, lower_bound, upper_bound, trail, rotate, show)

    def set_gradient(self, colors, lower_bound=0, upper_bound=None):
        if not upper_bound:
            upper_bound = self.num_px - 1

        self.__validate_bounds(lower_bound, upper_bound, 0)
        gradient = self.build_gradient(colors, upper_bound + 1 - lower_bound)

        self._w(
            Opcodes.SET_MULTIPLE,
            int.to_bytes(len(gradient), 1, byteorder='big')
        )
        for index in range(len(gradient)):
            self._w(
                int.to_bytes(lower_bound + index, 1, byteorder='big'),
                self._rgb_to_bytes(gradient[index])
            )

    def build_gradient(self, colors, length):
        colors = list(map(self.__process_color, colors))
        gradient = [(0, 0, 0, 0) for _ in range(length)]

        total_gradient_length = length - len(colors)
        spaces_per_gradient = (length - len(colors)) // (len(colors) - 1)
        bk_points = [0]
        bk_points_reverse = [length - 1]

        for k in range(0, len(colors) - 2, 2):
            bk_points.append(
                bk_points[-1] + spaces_per_gradient + (
                    k < total_gradient_length % (len(colors) - 1)
                )
            )
            k += 1
            if k >= len(colors) - 2:
                break

            bk_points_reverse.append(
                bk_points_reverse[-1] - spaces_per_gradient - (
                    k < total_gradient_length % (len(colors) - 1)
                )
            )

        bk_points += bk_points_reverse[::-1]

        for k in range(len(colors) - 1):
            gradient_space = bk_points[k + 1] - bk_points[k]
            for x in range(gradient_space + 1):
                gradient[bk_points[k] + x] = tuple([
                    int(colors[k][c] + (colors[k+1][c] - colors[k][c]) / gradient_space * x)
                    for c in range(4)
                ])

        gradient[-1] = colors[-1]

        return gradient

    def _set_brightness(self, key, value):
        self._w(
            Opcodes.SET_BRIGHTNESS,
            int.to_bytes(key, 1, byteorder='big'),
            int.to_bytes(value, 1, byteorder='big')
        )

    def dim(self, key, value):
        brightness = self.interpretor.original_color[key][3] - value
        if brightness < 0:
            raise ValueError("Resulted dim should be in range [0, 100]")
        if value <= 0:
            raise ValueError("Dim value should be an integer greater than zero")
        self._set_brightness(key, brightness)

    def brighten(self, key, value):
        brightness = self.interpretor.original_color[key][3] + value
        if brightness > 100:
            raise ValueError("Resulted dim should be in range [0, 100]")
        if value <= 0:
            raise ValueError("Dim value should be an integer greater than zero")
        self._set_brightness(key, brightness)

    def set_brightness(self, key, value):
        if value < 0 or value > 100:
            raise ValueError(f"Accepted value for brightness on index {key} is in range [0, 100]")
        self._set_brightness(key, value)

    def save(self):
        if len(self.stack_sleep) > 1:
            self.warnings.add('Sections started but not finished')

        total_sleep = sum(self.stack_sleep)
        if total_sleep == 0:
            self.warnings.add("Program time is zero!")
        print("Sequence length: ~{0} seconds.".format(total_sleep / 1000))
        print("Hint: use -v argument to see compiled program")
        if total_sleep // 1000 > 180:
            self.warnings.add('Animations are capped at 3 mins, while yours exceeds that threshold')
        self.fd.write(zlib.compress(self.data, 9))
        self.fd.close()
        print("Compressed {0} bytes in {1} - final size: {2} bytes.".format(
            len(self.data),
            self.filename,
            os.path.getsize(self.filename))
        )

        if self.warnings:
            print("==============Warning=================")
            for warning in self.warnings:
                print(warning)
            print("======================================")
            print()

