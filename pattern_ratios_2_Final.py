# Pattern ratios and constants for harmonic pattern detection

# AB=CD pattern ratios
ABCD_PATTERN_RATIOS = {
    'AB=CD_bull_1a': {'retr': (42, 58), 'proj': (192, 208), 'type': 2},  # ±8% around 50, 200
    'AB=CD_bull_1b': {'retr': (92, 108), 'proj': (192, 208), 'type': 2},  # ±8% around 100, 200

    'AB=CD_bull_2': {'retr': (62.7, 78.7), 'proj': (133.4, 149.4), 'type': 2},  # ±8% around 70.7, 141.4
    'AB=CD_bull_3': {'retr': (80.6, 96.6), 'proj': (105.0, 121.0), 'type': 2},  # ±8% around 88.6, 113
    'AB=CD_bull_4': {'retr': (53.8, 69.8), 'proj': (153.8, 169.8), 'type': 2},  # ±8% around 61.8, 161.8
    'AB=CD_bull_5': {'retr': (70.6, 86.6), 'proj': (119.2, 135.2), 'type': 2},  # ±8% around 78.6, 127.2

    'AB=CD_bull_6a': {'retr': (30.2, 46.2), 'proj': (216.0, 232.0), 'type': 2}, #[38.2, 224] # 38.2, [161.8, 224,261.8,314,361.8]
    'AB=CD_bull_6b': {'retr': (30.2, 46.2), 'proj': (253.8, 269.8), 'type': 2}, #[38.2, 261.8] 
    'AB=CD_bull_6c': {'retr': (30.2, 46.2), 'proj': (306.0, 322.0), 'type': 2}, #[38.2, 314] 
    'AB=CD_bull_6d': {'retr': (30.2, 46.2), 'proj': (353.8, 369.8), 'type': 2}, #[38.2, 361.8] 
    'AB=CD_bull_6e': {'retr': (30.2, 46.2), 'proj': (153.8, 169.8), 'type': 2},  # ±8% around 38.2, 161.8
    #'AB=CD_bull_6f': {'retr': (30.2, 46.2), 'proj': (153.8, 169.8), 'type': 2},  # ±2% around 38.2, 161.8
}

# original AB=CD pattern ratios
# ABCD_PATTERN_RATIOS = {
#     'AB=CD_bull_1': {'retr': (73.5, 76.5), 'proj': (196, 204), 'type': 2},  # ±2% around 75, 200
#     'AB=CD_bull_2': {'retr': (69.3, 72.1), 'proj': (138.6, 144.2), 'type': 2},  # ±2% around 70.7, 141.4
#     'AB=CD_bull_3': {'retr': (86.8, 90.4), 'proj': (110.7, 115.3), 'type': 2},  # ±2% around 88.6, 113
#     'AB=CD_bull_4': {'retr': (60.6, 63.0), 'proj': (158.6, 165.0), 'type': 2},  # ±2% around 61.8, 161.8
#     'AB=CD_bull_5': {'retr': (77.0, 80.2), 'proj': (124.7, 129.7), 'type': 2},  # ±2% around 78.6, 127.2
#     'AB=CD_bull_6': {'retr': (37.4, 39.0), 'proj': (219.5, 368.0), 'type': 2},  # 38.2, [224,261.8,314,361.8]
#     'AB=CD_bull_7': {'retr': (37.4, 39.0), 'proj': (158.6, 165.0), 'type': 2},  # ±2% around 38.2, 161.8
#     # 'AB=CD_bull_7': {'retr': (50, 60), 'proj': (160, 165), 'type': 2},  # ±2% around 38.2, 161.8
# }

# Add bearish versions of AB=CD patterns
ABCD_PATTERN_RATIOS.update({
    name.replace('_bull', '_bear'): {**ratios, 'type': 1}
    for name, ratios in ABCD_PATTERN_RATIOS.items()
})

# XABCD pattern ratios
XABCD_PATTERN_RATIOS = {
    'Bat1_bull': {
        'ab_xa': (30.2, 58.0),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (80.6, 96.6),
        'type': 2
    },
      'Bat2_bull': {
        'ab_xa': (30.2, 58.0),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (80.6, 96.6),
        'type': 2
    },
    'MaxBat1_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (119.2, 135.2),
        'ad_xa': (80.6, 96.6),
        'type': 2
    },
     'MaxBat2_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (80.6, 96.6),
        'type': 2
    },
    'AntiBat1_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (104.8, 269.8),
        'cd_bc': (192.0, 208.0),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
    'AntiBat2_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (104.8, 269.8),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
    'AltBat1_bull': {
        'ab_xa': (30.2, 46.2),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (192.0, 208.0),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
     'AltBat2_bull': {
        'ab_xa': (30.2, 46.2),
        'bc_ab': (30.2, 98.6),
        'cd_bc': (353.8, 369.8),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
    'Butterfly1_bull': {
        'ab_xa': (70.6, 86.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (119.2, 135.2),
        'type': 2
    },
    'Butterfly2_bull': {
        'ab_xa': (70.6, 86.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (153.8, 169.8),
        'type': 2
    },
        'Butterfly3_bull': {
        'ab_xa': (70.6, 86.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (119.2, 135.2),
        'type': 2
    },
        'Butterfly4_bull': {
        'ab_xa': (70.6, 86.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (153.8, 169.8),
        'type': 2
    },
    'Butterfly113_1_bull': {
        'ab_xa': (70.6, 108.0),
        'bc_ab': (53.8, 108.0),
        'cd_bc': (104.8, 120.8),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
       'Butterfly113_2_bull': {
        'ab_xa': (78.6, 100.0),
        'bc_ab': (53.8, 100.0),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
    'MaxButterfly1_bull': {
        'ab_xa': (53.8, 96.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (119.2, 135.2),
        'ad_xa': (119.2, 135.2),
        'type': 2
    },
     'MaxButterfly2_bull': {
        'ab_xa': (53.8, 96.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (119.2, 135.2),
        'ad_xa': (153.8, 169.8),
        'type': 2
    },
     'MaxButterfly3_bull': {
        'ab_xa': (53.8, 96.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (119.2, 135.2),
        'type': 2
    },
     'MaxButterfly4_bull': {
        'ab_xa': (53.8, 96.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (153.8, 169.8),
        'type': 2
    },
    'AntiButterfly1_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (104.0, 269.8),
        'cd_bc': (119.2, 135.2),
        'ad_xa': (53.8, 69.8),
        'type': 2
    },
     'AntiButterfly2_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (104.0, 269.8),
        'cd_bc': (119.2, 135.2),
        'ad_xa': (70.8, 86.8),
        'type': 2
    },
    'Shark1_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (105.0, 169.8),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (80.6, 96.6),
        'type': 2
    },
     'Shark2_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (105.0, 169.8),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (105.0, 121.0),
        'type': 2
    },
     'Shark3_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (105.0, 169.8),
        'cd_bc': (216.0, 232.0),
        'ad_xa': (80.6, 96.6),
        'type': 2
    },
     'Shark4_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (105.0, 169.8),
        'cd_bc': (216.0, 232.0),
        'ad_xa': (105.0, 121.0),
        'type': 2
    },
    'AntiShark1_bull': {
        'ab_xa': (36.6, 69.8),
        'bc_ab': (53.8, 96.6),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (80.6, 96.6),
        'type': 2
    },
    'AntiShark2_bull': {
        'ab_xa': (36.6, 69.8),
        'bc_ab': (53.8, 96.6),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
    'AntiShark3_bull': {
        'ab_xa': (36.6, 69.8),
        'bc_ab': (53.8, 96.6),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (80.6, 96.6),
        'type': 2
    },
    'AntiShark4_bull': {
        'ab_xa': (36.6, 69.8),
        'bc_ab': (53.8, 96.6),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
    'Nenstar1_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (133.4, 222.0),
        'cd_bc': (119.2, 135.2),
        'ad_xa': (119.2, 135.2),
        'type': 2
    },
      'Nenstar2_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (133.4, 222.0),
        'cd_bc': (192.0, 208.0),
        'ad_xa': (119.2, 135.2),
        'type': 2
    },
    'AntiNenstar1_bull': {
        'ab_xa': (42.0, 86.6),
        'bc_ab': (38.7, 78.7),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (70.6, 86.6),
        'type': 2
    },
    'AntiNenstar2_bull': {
        'ab_xa': (42.0, 86.6),
        'bc_ab': (38.7, 78.7),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (70.6, 86.6),
        'type': 2
    },
    'Nevarro200_1_bull': {
        'ab_xa': (30.2, 86.6),
        'bc_ab': (80.6, 120.8),
        'cd_bc': (80.6, 96.6),
        'ad_xa': (80.6, 96.6),
        'type': 2
    },
       'Nevarro200_2_bull': {
        'ab_xa': (30.2, 86.6),
        'bc_ab': (80.6, 120.8),
        'cd_bc': (80.6, 96.6),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
       'Nevarro200_3_bull': {
        'ab_xa': (30.2, 86.6),
        'bc_ab': (80.6, 120.8),
        'cd_bc': (353.8, 369.8),
        'ad_xa': (80.6, 96.6),
        'type': 2
    },
       'Nevarro200_4_bull': {
        'ab_xa': (30.2, 86.6),
        'bc_ab': (80.6, 120.8),
        'cd_bc': (353.8, 369.8),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
       'Commander_bull': {
        'ab_xa': (42.0, 58.0),
        'bc_ab': (80.6, 96.6),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (70.6, 86.6),
        'type': 2
    },
    'Leonardo1_bull': {
        'ab_xa': (42.0, 58.0),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (104.8, 120.8),
        'ad_xa': (70.6, 86.6),
        'type': 2
    },
      'Leonardo2_bull': {
        'ab_xa': (42.0, 58.0),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (70.6, 86.6),
        'type': 2
    },
    'NewCypher1_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (133.4, 222.0),
        'cd_bc': (119.2, 135.2),
        'ad_xa': (70.6, 86.6),
        'type': 2
    },
      'NewCypher2_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (133.4, 222.0),
        'cd_bc': (192.0, 208.0),
        'ad_xa': (70.6, 86.6),
        'type': 2
    },
    'AntiCypher1_bull': {
        'ab_xa': (42.0, 86.6),
        'bc_ab': (38.7, 78.7),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (119.2, 135.2),
        'type': 2
    },
      'AntiCypher2_bull': {
        'ab_xa': (42.0, 86.6),
        'bc_ab': (38.7, 78.7),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (119.2, 135.2),
        'type': 2
    },
    'Cypher1_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (119.2, 149.4),
        'cd_bc': (119.2, 135.2),
        'ad_xa': (70.6, 86.6),
        'type': 2
    },
     'Cypher2_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (119.2, 149.4),
        'cd_bc': (192.0, 208.0),
        'ad_xa': (70.6, 86.6),
        'type': 2
    },
    'AntiGartley_bull': {
        'ab_xa': (53.8, 86.6),
        'bc_ab': (104.8, 269.8),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (119.2, 135.2),
        'type': 2
    },
    'MaxGartley1_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (104.8, 120.8),
        'ad_xa': (53.8, 69.8),
        'type': 2
    },
     'MaxGartley2_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (104.8, 120.8),
        'ad_xa': (70.6, 86.6),
        'type': 2
    },
     'MaxGartley3_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (216.0, 232.0),
        'ad_xa': (53.8, 69.8),
        'type': 2
    },
     'MaxGartley4_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (216.0, 232.0),
        'ad_xa': (70.6, 86.6),
        'type': 2
    },
    'Gartley1_bull': {
        'ab_xa': (53.8, 69.8),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (119.2, 135.2),
        'ad_xa': (70.6, 86.6),
        'type': 2
    },
    'Gartley2_bull': {
        'ab_xa': (53.8, 69.8),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (70.6, 86.6),
        'type': 2
    },
    'DeepCrab1_bull': {
        'ab_xa': (80.6, 96.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (153.8, 169.8),
        'type': 2
    },
      'DeepCrab2_bull': {
        'ab_xa': (80.6, 96.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (353.8, 369.8),
        'ad_xa': (153.8, 169.8),
        'type': 2
    },
    'AntiCrab1_bull': {
        'ab_xa': (19.6, 53.6),
        'bc_ab': (104.8, 269.8),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (53.8, 69.8),
        'type': 2
    },
      'AntiCrab2_bull': {
        'ab_xa': (19.6, 53.6),
        'bc_ab': (104.8, 269.8),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (53.8, 69.8),
        'type': 2
    },
    'Crab1_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (216.0, 232.0),
        'ad_xa': (153.8, 169.8),
        'type': 2
    },
    'Crab2_bull': {
        'ab_xa': (30.2, 69.8),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (353.8, 369.8),
        'ad_xa': (153.8, 169.8),
        'type': 2
    },
    'WobblyJohn1_bull': {
        'ab_xa': (19.6, 86.6),
        'bc_ab': (30.2, 269.8),
        'cd_bc': (119.2, 135.2),
        'ad_xa': (53.8, 69.8),
        'type': 2
    },
   'WobblyJohn2_bull': {
        'ab_xa': (19.6, 86.6),
        'bc_ab': (30.2, 269.8),
        'cd_bc': (119.2, 135.2),
        'ad_xa': (153.8, 169.8),
        'type': 2
    },
    'WobblyJohn3_bull': {
        'ab_xa': (19.6, 86.6),
        'bc_ab': (30.2, 269.8),
        'cd_bc': (353.8, 369.8),
        'ad_xa': (53.8, 69.8),
        'type': 2
    },
    'WobblyJohn4_bull': {
        'ab_xa': (19.6, 86.6),
        'bc_ab': (30.2, 269.8),
        'cd_bc': (353.8, 369.8),
        'ad_xa': (153.8, 169.8),
        'type': 2
    },
    'TheImperial_bull': {
        'ab_xa': (53.8, 69.8),
        'bc_ab': (104.8, 120.8),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (153.8, 169.8),
        'type': 2
    },
    'TheSwan1_bull': {
        'ab_xa': (53.8, 69.8),
        'bc_ab': (53.8, 69.8),
        'cd_bc': (216.0, 232.0),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
    'TheSwan2_bull': {
        'ab_xa': (53.8, 69.8),
        'bc_ab': (80.6, 96.6),
        'cd_bc': (216.0, 232.0),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
    '8_1_bull': {
        'ab_xa': (30.2, 86.6),
        'bc_ab': (104.8, 269.8),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
    '8_2_bull': {
        'ab_xa': (30.2, 86.6),
        'bc_ab': (104.8, 269.8),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (119.2, 135.2),
        'type': 2
    },
    '8_3_bull': {
        'ab_xa': (30.2, 86.6),
        'bc_ab': (104.8, 269.8),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
    '8_4_bull': {
        'ab_xa': (30.2, 86.6),
        'bc_ab': (104.8, 269.8),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (119.2, 135.2),
        'type': 2
    },
    'TheHitman1_bull': {
        'ab_xa': (4.8, 369.8),
        'bc_ab': (104.8, 120.8),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (53.8, 69.8),
        'type': 2
    },
    'TheHitman2_bull': {
        'ab_xa': (4.8, 369.8),
        'bc_ab': (104.8, 120.8),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (353.8, 369.8),
        'type': 2
    },
    'SFPL_1_bull': {
        'ab_xa': (19.6, 69.8),
        'bc_ab': (104.8, 269.8),
        'cd_bc': (119.2, 135.2),
        'ad_xa': (53.8, 69.8),
        'type': 2
    },
    'SFPL_2_bull': {
        'ab_xa': (19.6, 69.8),
        'bc_ab': (104.8, 269.8),
        'cd_bc': (119.2, 135.2),
        'ad_xa': (80.6, 96.6),
        'type': 2
    },
    'SFPL_3_bull': {
        'ab_xa': (19.6, 69.8),
        'bc_ab': (104.8, 269.8),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (53.8, 69.8),
        'type': 2
    },
    'SFPL_4_bull': {
        'ab_xa': (19.6, 69.8),
        'bc_ab': (104.8, 269.8),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (80.6, 96.6),
        'type': 2
    },
    'Mangles1_bull': {
        'ab_xa': (30.2, 86.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
    'Mangles2_bull': {
        'ab_xa': (30.2, 86.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (153.8, 169.8),
        'ad_xa': (153.8, 169.8),
        'type': 2
    },
    'Mangles3_bull': {
        'ab_xa': (30.2, 86.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (353.8, 369.8),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
    'Mangles4_bull': {
        'ab_xa': (30.2, 86.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (353.8, 369.8),
        'ad_xa': (153.8, 169.8),
        'type': 2
    },
    'BukuT1_bull': {
        'ab_xa': (30.2, 86.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (119.2, 135.2),
        'ad_xa': (70.6, 86.6),
        'type': 2
    },
    'BukuT2_bull': {
        'ab_xa': (30.2, 86.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (119.2, 135.2),
        'ad_xa': (80.6, 96.6),
        'type': 2
    },
    'BukuT3_bull': {
        'ab_xa': (30.2, 86.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (70.6, 86.6),
        'type': 2
    },
    'BukuT4_bull': {
        'ab_xa': (30.2, 86.6),
        'bc_ab': (30.2, 96.6),
        'cd_bc': (253.8, 269.8),
        'ad_xa': (80.6, 96.6),
        'type': 2
    },
    'BigRon_bull': {
        'ab_xa': (53.8, 69.8),
        'bc_ab': (80.6, 96.6),
        'cd_bc': (192.0, 208.0),
        'ad_xa': (119.2, 135.2),
        'type': 2
    },
    'AntiRon_bull': {
        'ab_xa': (53.8, 69.8),
        'bc_ab': (133.0, 149.0),
        'cd_bc': (192.0, 208.0),
        'ad_xa': (119.2, 135.2),
        'type': 2
    },
    'DSC1_bull': {
        'ab_xa': (53.8, 69.8),
        'bc_ab': (62.0, 78.0),
        'cd_bc': (192.0, 208.0),
        'ad_xa': (80.6, 96.6),
        'type': 2
    },
    'DSC2_bull': {
        'ab_xa': (53.8, 69.8),
        'bc_ab': (62.0, 78.0),
        'cd_bc': (192.0, 208.0),
        'ad_xa': (104.8, 120.8),
        'type': 2
    },
    'TheBFG_bull': {
        'ab_xa': (53.8, 69.8),
        'bc_ab': (92.0, 108.0),
        'cd_bc': (133.0, 149.0),
        'ad_xa': (70.6, 86.6),
        'type': 2
    },
    'Fandango1_bull': {
        'ab_xa': (53.8, 69.8),
        'bc_ab': (53.8, 69.8),
        'cd_bc': (192.0, 208.0),
        'ad_xa': (92.0, 108.0),
        'type': 2
    },
    'Fandango1_bull': {
        'ab_xa': (53.8, 69.8),
        'bc_ab': (53.8, 69.8),
        'cd_bc': (216.0, 232.0),
        'ad_xa': (92.0, 108.0),
        'type': 2
    },
}

# Add bearish versions of XABCD patterns
XABCD_PATTERN_RATIOS.update({
    name.replace('_bull', '_bear'): {**ratios, 'type': 1}
    for name, ratios in XABCD_PATTERN_RATIOS.items()
})

# Pattern colors for visualization
PATTERN_COLORS = {
    'AB=CD_bull_1': '#FF0000',  # Red
    'AB=CD_bull_2': '#00FF00',  # Green
    'AB=CD_bull_3': '#0000FF',  # Blue
    'AB=CD_bull_4': '#FFA500',  # Orange
    'AB=CD_bull_5': '#800080',  # Purple
    'AB=CD_bull_6': '#008080',  # Teal
    'AB=CD_bull_7': '#FFD700',  # Gold
    'Bat_bull': '#4169E1',      # Royal Blue
    'MaxBat_bull': '#32CD32',   # Lime Green
    'AntiBat_bull': '#FF1493',  # Deep Pink
}

# Add bearish versions of colors (same colors but will be dotted)
PATTERN_COLORS.update({
    name.replace('_bull', '_bear'): color
    for name, color in PATTERN_COLORS.items()
})

# PRZ projection pairs for enhanced potential reversal zone calculation
# Each tuple represents (proj_low%, proj_high%) for Fibonacci-based PRZ levels
PRZ_PROJECTION_PAIRS = [
    (19.6, 35.6),
    (30.2, 46.2),
    (42.0, 58.0),
    (53.8, 69.8),
    (62.0, 78.0),
    (70.6, 86.6),
    (80.6, 96.6),
    (104.8, 120.8),
    (119.2, 135.2),
    (133.4, 149.4),
    (153.8, 169.8),
    (192.0, 208.0),
    (216.0, 232.0),
    (253.8, 269.8),
    (353.8, 369.8)
] 