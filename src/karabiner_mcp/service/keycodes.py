"""Karabiner-Elements key codes and modifier names.

Static data used by IR validators and exposed to the frontend for autocomplete.
Source: https://karabiner-elements.pqrs.org/docs/json/
"""

MODIFIERS: list[str] = [
    "left_control",
    "left_shift",
    "left_option",
    "left_command",
    "right_control",
    "right_shift",
    "right_option",
    "right_command",
    "fn",
    "caps_lock",
    # Aliases accepted by Karabiner
    "control",
    "shift",
    "option",
    "command",
    "any",
]

KEY_CODES: dict[str, list[str]] = {
    "Letters": [
        "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
        "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    ],
    "Numbers": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
    "Function Keys": [
        "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10",
        "f11", "f12", "f13", "f14", "f15", "f16", "f17", "f18", "f19",
        "f20", "f21", "f22", "f23", "f24",
    ],
    "Modifiers": [
        "caps_lock", "left_control", "left_shift", "left_option",
        "left_command", "right_control", "right_shift", "right_option",
        "right_command", "fn",
    ],
    "Navigation": [
        "return_or_enter", "escape", "delete_or_backspace", "delete_forward",
        "tab", "spacebar", "up_arrow", "down_arrow", "left_arrow",
        "right_arrow", "home", "end", "page_up", "page_down",
    ],
    "Punctuation": [
        "hyphen", "equal_sign", "open_bracket", "close_bracket", "backslash",
        "non_us_pound", "semicolon", "quote", "grave_accent_and_tilde",
        "comma", "period", "slash", "non_us_backslash",
    ],
    "Keypad": [
        "keypad_num_lock", "keypad_slash", "keypad_asterisk",
        "keypad_hyphen", "keypad_plus", "keypad_enter", "keypad_period",
        "keypad_1", "keypad_2", "keypad_3", "keypad_4", "keypad_5",
        "keypad_6", "keypad_7", "keypad_8", "keypad_9", "keypad_0",
        "keypad_equal_sign",
    ],
    "Media": [
        "display_brightness_decrement", "display_brightness_increment",
        "mission_control", "launchpad", "dashboard",
        "illumination_decrement", "illumination_increment",
        "rewind", "play_or_pause", "fastforward",
        "mute", "volume_decrement", "volume_increment", "eject",
    ],
    "International": [
        "international1", "international2", "international3",
        "international4", "international5",
        "lang1", "lang2", "lang3", "lang4", "lang5",
    ],
    "System": [
        "print_screen", "scroll_lock", "pause", "insert", "application",
        "help", "power", "execute", "menu", "select", "stop", "again",
        "undo", "cut", "copy", "paste", "find",
    ],
}

ALL_KEY_CODES: frozenset[str] = frozenset(
    code for group in KEY_CODES.values() for code in group
)

POINTING_BUTTONS: list[str] = [f"button{i}" for i in range(1, 33)]

ALL_POINTING_BUTTONS: frozenset[str] = frozenset(POINTING_BUTTONS)
