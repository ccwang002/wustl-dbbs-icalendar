# WUSTL DBBS Calendar in iCalendar format

The script `gen_ical.py` parses the official WUSTL DBBS event calendar and generate a subscribable calendar file in the RFC standard format (RFC 5545 iCalendar) and generate an iCalendar at `output/DBBS.ics`.

```
python gen_ical.py
```

See [it runs in action](https://blog.liang2.tw/wustl-dbbs-icalendar/) which embeds an daily updated Google calendar.


## Dependencies

- Python version: 3.6+
- Async web scrapping:
    - aiodns
    - aiohttp
- Web parsing:
    - lxml
    - beautifulsoup4
    - html5lib
    - pyquery
- Datetime handling:
    - pytz
    - pendulum
- iCalendar generation:
    - vobject
    - recurrent
- Misc:
    - tqdm
    - ghp-import
    - [Fabric3 (Fabric py3k compat fork)](https://github.com/mathiasertl/fabric)


## Run periodically on Debian

Use systemd user unit and timer.

    sudo apt-get install libpam-systemd

Create the service unit and timer file under `~/.config/systemd/user/`.
For the service unit `update_wustl_dbbs_ical.service`:

```systemd
[Unit]
Description=Update WUSTL DBBS ical

[Service]
Environment="PATH=%h/ical_venv/bin:/usr/local/bin:/usr/bin"
WorkingDirectory=%h/wustl-dbbs-icalendar
ExecStart=/usr/bin/env fab update

[Install]
WantedBy=default.target
```

For the timer unit `update_wustl_dbbs_ical.timer`:

```systemd
[Unit]
Description=Update WUSTL DBBS ical everyday

[Timer]
OnCalendar=Mon..Fri,Sun 8:00:00
AccuracySec=10min

[Install]
WantedBy=timers.target
```

Enable the timer and check if the scheduled update is properly set:

    systemctl --user enable update_wustl_ddbs_ical.timer
    systemctl --user start update_wustl_ddbs_ical.timer
    systemctl --user list-timers
    journalctl --user-unit update_wustl_ddbs_ical


## Run periodically on macOS

Add `~/Library/LaunchAgents/local.update_ical`:

```plist
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
    <dict>
        <key>Label</key>
        <!-- The label should be the same as the filename without the extension -->
        <string>local.update_ical</string>
        <!-- Specify how to run your program here -->
        <key>ProgramArguments</key>
        <array>
            <string>/Users/liang/miniconda3/envs/ical/bin/fab</string>
            <string>update</string>
        </array>
        <key>EnvironmentVariables</key>
        <dict>
            <key>PATH</key>
            <string>/Users/liang/miniconda3/envs/ical/bin:/usr/local/bin:/usr/bin/:/bin</string>
        </dict>
        <key>WorkingDirectory</key>
        <string>/Users/liang/code/wustl-dbbs-icalendar</string>
        <key>StandardErrorPath</key>
        <string>/Users/liang/code/wustl-dbbs-icalendar/stderr.log</string>
        <key>StandardOutPath</key>
        <string>/Users/liang/code/wustl-dbbs-icalendar/stdout.log</string>
        <key>Nice</key>
        <integer>10</integer>
        <key>StartCalendarInterval</key>
        <array>
            <dict>
                <key>Hour</key>
                <integer>8</integer>
                <key>Minute</key>
                <integer>0</integer>
            </dict>
        </array>
    </dict>
</plist>
```
