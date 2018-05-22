things2taskwarrior
===

Convert Things tasks to TaskWarrior tasks.

Uses standalone Things database on macOS. Doesn't use HTTP API aka "Cloud sync".

**WARNING**

Use at your own risk. Not everything can be converted in the same format into TW. After successful import consider to review your task list and update tasks accordingly.

# Requirements 

1. You need to run it on macOS where you have installed Things 3 standalone.
2. If you're using Things on iOS you need to enable cloud sync, so Things on your macOS would pull it down.
3. After successful sync you can safely back up your Things database located at `~/Library/Containers/com.culturedcode.ThingsMac/Data/Library/Application Support/Cultured Code/Things/Things.sqlite3`.

# How to run

```sh
python things.py | task import
```

# Authors

* Michał Papierski

This script is based on excellent gist `https://gist.github.com/AlexanderWillner/dad8bb7cead74eb7679b553e8c37f477` and `https://github.com/AlexanderWillner/things.sh`.

