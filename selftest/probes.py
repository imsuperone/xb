# -*- coding: utf-8 -*-
"""探针表组装：各系统探针分文件存放，此处只组装套件名→探针表。"""
try:
    from .probes_sign import SUITE as S_SIGN, SINGLES as T_SIGN
    from .probes_spirit import SUITE as S_SPIRIT, SINGLES as T_SPIRIT
    from .probes_ent import SUITE as S_ENT, SINGLES as T_ENT
    from .probes_bank import SUITE as S_BANK, SINGLES as T_BANK
    from .probes_slave import SUITE as S_SLAVE, SINGLES as T_SLAVE
    from .probes_ride import SUITE as S_RIDE, SINGLES as T_RIDE
    from .probes_guild import SUITE as S_GUILD, SINGLES as T_GUILD
    from .probes_adv import SUITE as S_ADV, SINGLES as T_ADV
except ImportError:
    from selftest.probes_sign import SUITE as S_SIGN, SINGLES as T_SIGN
    from selftest.probes_spirit import SUITE as S_SPIRIT, SINGLES as T_SPIRIT
    from selftest.probes_ent import SUITE as S_ENT, SINGLES as T_ENT
    from selftest.probes_bank import SUITE as S_BANK, SINGLES as T_BANK
    from selftest.probes_slave import SUITE as S_SLAVE, SINGLES as T_SLAVE
    from selftest.probes_ride import SUITE as S_RIDE, SINGLES as T_RIDE
    from selftest.probes_guild import SUITE as S_GUILD, SINGLES as T_GUILD
    from selftest.probes_adv import SUITE as S_ADV, SINGLES as T_ADV

SUITES = {
    "测试testxb 2": S_SIGN, "测试testxb 3": S_SPIRIT, "测试testxb 4": S_ENT,
    "测试testxb 5": S_BANK, "测试testxb 6": S_SLAVE, "测试testxb 7": S_RIDE,
    "测试testxb 8": S_GUILD, "测试testxb 9": S_ADV,
    "测试testxb1": T_SIGN, "测试testxb2": T_SPIRIT, "测试testxb3": T_ENT,
    "测试testxb4": T_BANK, "测试testxb5": T_SLAVE, "测试testxb6": T_RIDE,
    "测试testxb7": T_GUILD, "测试testxb8": T_ADV,
}

SUITE_MODS = {
    "测试testxb 2": "sign", "测试testxb 3": "spirit", "测试testxb 4": "ent",
    "测试testxb 5": "bank", "测试testxb 6": "slave", "测试testxb 7": "ride",
    "测试testxb 8": "guild", "测试testxb 9": "adventure",
    "测试testxb1": "sign", "测试testxb2": "spirit", "测试testxb3": "ent",
    "测试testxb4": "bank", "测试testxb5": "slave", "测试testxb6": "ride",
    "测试testxb7": "guild", "测试testxb8": "adventure",
}
