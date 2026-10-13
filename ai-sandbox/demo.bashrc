if [[ "${SANDBOX_SHELL_READY:-}" != 1 && -f /etc/sandbox-persistent.sh ]]; then
    source /etc/sandbox-persistent.sh
fi
export SANDBOX_SHELL_READY=1
export SPEEDSCALE_APP_URL="${SPEEDSCALE_APP_URL:-dev.speedscale.com}"
export NODE_USE_ENV_PROXY=1
export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/certs/ca-certificates.crt}"
export NO_PROXY="${NO_PROXY-localhost,127.0.0.1,::1}"
export no_proxy="${no_proxy-$NO_PROXY}"
for proxy_name in HTTP_PROXY HTTPS_PROXY ALL_PROXY; do
    if [[ -n "${!proxy_name:-}" ]]; then
        export "${proxy_name,,}=${!proxy_name}"
        unset "$proxy_name"
    fi
done
if [[ -f /usr/local/share/ca-certificates/proxy-ca.crt ]]; then
    export NODE_EXTRA_CA_CERTS=/usr/local/share/ca-certificates/proxy-ca.crt
fi
speedscale_home="${SPEEDSCALE_HOME:-$HOME/.speedscale}"
if [[ -f "$speedscale_home/certs/tls.crt" ]]; then
    cat "$speedscale_home/certs/tls.crt" /usr/local/share/ca-certificates/proxy-ca.crt > "$speedscale_home/demo-ca.pem"
    export NODE_EXTRA_CA_CERTS="$speedscale_home/demo-ca.pem"
fi
export HISTCONTROL=ignoreboth
export HISTFILE="$HOME/.bash_history"
export PS1='\[\e[32m\]sandbox\[\e[0m\]:\[\e[36m\]\w\[\e[0m\] $ '
alias ll='ls -lah'
alias cls='clear'
