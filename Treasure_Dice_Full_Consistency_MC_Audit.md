# Treasure Dice Full Consistency and Monte Carlo Audit

- Generated at: 2026-06-03T10:38:59.216580+00:00
- Monte Carlo rounds per mode: 1,000,000

## Overall Result

- Pass: True
- All mode consistency checks: True
- Monte Carlo within 5 sigma for all modes: True
- Required docs present: True
- Broken markdown links: False

## Structure Consistency

- mapping_config_mode_match: True
- index_config_mode_match: True
- publish_books_match: True
- publish_lookups_match: True
- lookup_tables_match: True
- force_files_match: True

## Mode Consistency

| Mode | Theoretical RTP | Lookup RTP | Delta | Drift Sigma | MaxWin Config | MaxWin Mapping | MaxWin Observed | Weights | Books | Pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| safe_shore | 0.960000 | 0.979200 | 1.920000e-02 | 1.789 | 1.2000 | 1.2000 | 1.2000 | 2000 | 2000 | True |
| hidden_bay | 0.960000 | 1.003200 | 4.320000e-02 | 1.743 | 1.6000 | 1.6000 | 1.6000 | 1000 | 1000 | True |
| coral_reef | 0.960000 | 0.993600 | 3.360000e-02 | 0.904 | 2.4000 | 2.4000 | 2.4000 | 1000 | 1000 | True |
| storm_route | 0.960000 | 1.044480 | 8.448000e-02 | 1.607 | 3.8400 | 3.8400 | 3.8400 | 1000 | 1000 | True |
| skull_island | 0.960000 | 1.056000 | 9.600000e-02 | 1.054 | 9.6000 | 9.6000 | 9.6000 | 1000 | 1000 | True |
| kraken_waters | 0.960000 | 1.113600 | 1.536000e-01 | 1.161 | 19.2000 | 19.2000 | 19.2000 | 1000 | 1000 | True |
| lost_treasure | 0.960000 | 0.864000 | -9.600000e-02 | -0.449 | 96.0000 | 96.0000 | 96.0000 | 2000 | 2000 | True |
| treasure_hunt_buy | 0.960000 | 0.934100 | -2.590000e-02 | -1.090 | 275.0000 | 275.0000 | 275.0000 | 1000 | 1000 | True |

## Monte Carlo by Mode

| Mode | Rounds | Theoretical RTP | Simulated RTP | Drift | Std Error | Z-Score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| safe_shore | 1000000 | 0.960000 | 0.959904 | -9.600001e-05 | 4.800000e-04 | -0.200 |
| hidden_bay | 1000000 | 0.960000 | 0.960866 | 8.656000e-04 | 7.838367e-04 | 1.104 |
| coral_reef | 1000000 | 0.960000 | 0.962734 | 2.733600e-03 | 1.175755e-03 | 2.325 |
| storm_route | 1000000 | 0.960000 | 0.960557 | 5.568000e-04 | 1.662769e-03 | 0.335 |
| skull_island | 1000000 | 0.960000 | 0.953482 | -6.518400e-03 | 2.880000e-03 | -2.263 |
| kraken_waters | 1000000 | 0.960000 | 0.958637 | -1.363200e-03 | 4.184543e-03 | -0.326 |
| lost_treasure | 1000000 | 0.960000 | 0.964224 | 4.224000e-03 | 9.551879e-03 | 0.442 |
| treasure_hunt_buy | 1000000 | 0.960000 | 0.959944 | -5.610000e-05 | 7.513987e-04 | -0.075 |

