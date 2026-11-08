# fish completion for bom-clima — install:
#   cp completions/bom-clima.fish ~/.config/fish/completions/bom-clima.fish
#
# Kept next to build_parser(): tests/test_completions.py fails when a flag is
# added to the parser but not to this file.

complete -c bom-clima -s d -l detect -d 'Auto-detect location via IP'
complete -c bom-clima -s c -l compare -d 'Compare cities side by side'
complete -c bom-clima -s D -l days -d 'Days of forecast to show' -xa '1 3 5 7 10 15'
complete -c bom-clima -s H -l hours -d 'Hours of forecast to show' -xa '6 12 24'
complete -c bom-clima -s q -l aqi -d 'Include air quality'
complete -c bom-clima -l at -d 'Specific time of day, e.g. 14 or 14:30' -x
complete -c bom-clima -l rain -d 'Show the next 24h rain windows'
complete -c bom-clima -l line -d 'One-line output for tmux/i3status/prompts'
complete -c bom-clima -s i -l imperial -d 'Imperial units (°F, mph, in)'
complete -c bom-clima -s n -l no-color -d 'Disable colored output'
complete -c bom-clima -s y -l history -d 'Show query history'
complete -c bom-clima -l no-cache -d 'Bypass cache'
complete -c bom-clima -s V -l verbose -d 'Show debug information'
complete -c bom-clima -l best-day -d 'Best day for outdoor activities'
complete -c bom-clima -l vs-yesterday -d 'Compare with yesterday'
complete -c bom-clima -s e -l export -d 'Export data' -xa 'json csv yaml xml'
complete -c bom-clima -s o -l output -d 'Output file (- streams to stdout)' -rF
complete -c bom-clima -s l -l lang -d 'Interface language' -xa 'pt en es'
complete -c bom-clima -s s -l config-set -d 'Persist a config value KEY=VALUE' -x
complete -c bom-clima -s S -l config-show -d 'Show persistent configuration'
complete -c bom-clima -s h -l help -d 'Show help'
complete -c bom-clima -s v -l version -d 'Show version'
