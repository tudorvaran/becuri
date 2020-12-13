from enum import Enum


class Opcodes(Enum):
    SET = 0x01
    FILL = 0x02
    SLEEP = 0x03
    SHOW = 0x04
    SHOW_AND_SLEEP = 0x05
    SECTION = 0x06
    REPEAT = 0x07

    MOVE_UP = 0x08
    MOVE_DOWN = 0x09

    SET_SPEED = 0x0a
    RESET_SPEED = 0x0b

    SET_MULTIPLE = 0x0c
    SET_BRIGHTNESS = 0x0d


    # runtime opcodes
    END_SECTION = 0xff
