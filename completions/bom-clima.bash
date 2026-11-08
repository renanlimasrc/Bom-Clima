# bash completion for bom-clima
# Install for the current user:
#   source completions/bom-clima.bash        # once per session, or
#   copy to ~/.bash_completion.d/ and source it from ~/.bashrc
# System-wide:
#   cp completions/bom-clima.bash /etc/bash_completion.d/bom-clima
#
# Kept next to build_parser(): tests/test_completions.py fails when a flag is
# added to the parser but not to the word lists here.

_bom_clima() {
    local cur prev
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    case "$prev" in
        --days|-D)
            COMPREPLY=( $(compgen -W "1 3 5 7 10 15" -- "$cur") )
            return ;;
        --hours|-H)
            COMPREPLY=( $(compgen -W "6 12 24" -- "$cur") )
            return ;;
        --lang|-l)
            COMPREPLY=( $(compgen -W "pt en es" -- "$cur") )
            return ;;
        --export|-e)
            COMPREPLY=( $(compgen -W "json csv yaml xml" -- "$cur") )
            return ;;
        --at)
            COMPREPLY=( $(compgen -W "06:00 12:00 18:00" -- "$cur") )
            return ;;
        --output|-o)
            COMPREPLY=( $(compgen -f -- "$cur") )
            return ;;
        --config-set|-s)
            COMPREPLY=( $(compgen -W "unit_system city_default forecast_days forecast_hours color history_limit lang" -- "$cur") )
            return ;;
    esac

    if [[ "$cur" == -* ]]; then
        # Both short and long spellings; order doesn't matter for completion.
        COMPREPLY=( $(compgen -W "
            --detect -d --compare -c
            --days -D --hours -H --aqi -q --at --rain --line
            --imperial -i --no-color -n
            --history -y --no-cache --verbose -V
            --best-day --vs-yesterday
            --export -e --output -o
            --lang -l --config-set -s --config-show -S
            --help -h --version -v
        " -- "$cur") )
        return
    fi

    COMPREPLY=()
}

complete -F _bom_clima bom-clima
