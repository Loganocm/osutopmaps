# Define bitwise flags for mods based on the provided enum
MODS = {
    0: "None",
    1: "NoFail",
    2: "Easy",
    4: "TouchDevice",
    8: "Hidden",
    16: "HardRock",
    32: "SuddenDeath",
    64: "DoubleTime",
    128: "Relax",
    256: "HalfTime",
    512: "Nightcore",  # NC only gives 576 when combined with DoubleTime
    1024: "Flashlight",
    2048: "Autoplay",
    4096: "SpunOut",
    8192: "Relax2",
    16384: "Perfect",  # PF only gives 16416 when combined with SuddenDeath
    32768: "Key4",
    65536: "Key5",
    131072: "Key6",
    262144: "Key7",
    524288: "Key8",
    1048576: "FadeIn",
    2097152: "Random",
    4194304: "Cinema",
    8388608: "Target",
    16777216: "Key9",
    33554432: "KeyCoop",
    67108864: "Key1",
    134217728: "Key3",
    268435456: "Key2",
    536870912: "ScoreV2",
    1073741824: "Mirror",
}

def get_mods_from_bitwise(enabled_mods):
    mods = []
    for mod_value, mod_name in MODS.items():
        if enabled_mods & mod_value:
            mods.append(mod_name)
    return mods