#!/bin/sh
# apikey.sh - print the Speedscale API key for the current context and nothing
# else, so callers can use it inside a command substitution without the key
# ever appearing in a transcript:
#   kubectl create secret generic speedscale-apikey --from-literal=SPEEDSCALE_API_KEY="$(sh apikey.sh)"
# Order: $SPEEDSCALE_API_KEY, then ~/.speedscale/config.json, then config.yaml.
# Optional: SPEEDSCALE_CONTEXT=<name> selects a context other than current.
# With --app-url it prints the context's Speedscale host (app.speedscale.com
# for most tenants) instead of the key, for SPEEDSCALE_APP_URL / appUrl.
# Exit 1 with a message on stderr when nothing can be found.

field=apikey
[ "${1:-}" = "--app-url" ] && field=appurl

if [ "$field" = appurl ] && [ -n "${SPEEDSCALE_APP_URL:-}" ]; then printf '%s' "$SPEEDSCALE_APP_URL"; exit 0; fi
if [ "$field" = apikey ] && [ -n "${SPEEDSCALE_API_KEY:-}" ]; then printf '%s' "$SPEEDSCALE_API_KEY"; exit 0; fi

home="${SPEEDSCALE_HOME:-$HOME/.speedscale}"
want="${SPEEDSCALE_CONTEXT:-}"

if [ -f "$home/config.json" ]; then
  cfg="$home/config.json"
  if command -v python3 >/dev/null 2>&1; then
    key=$(python3 - "$cfg" "$want" "$field" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
name = sys.argv[2] or cfg.get("current-context", "")
ctx = next((c for c in cfg.get("contexts", []) if c.get("name") == name), None)
if ctx is None:
    sys.exit(1)
if sys.argv[3] == "appurl":
    print(ctx.get("app-url") or "app.speedscale.com", end="")
    sys.exit(0)
tenant = next((t for t in cfg.get("tenants", []) if t.get("name") == ctx.get("tenant")), None)
if not tenant or not tenant.get("apikey"):
    sys.exit(1)
print(tenant["apikey"], end="")
PY
)
  elif command -v jq >/dev/null 2>&1; then
    key=$(jq -r --arg want "$want" --arg field "$field" '
      (if $want == "" then .["current-context"] else $want end) as $n
      | (.contexts[] | select(.name == $n)) as $c
      | if $field == "appurl" then ($c["app-url"] // "app.speedscale.com")
        else (.tenants[] | select(.name == $c.tenant) | .apikey // empty) end' "$cfg" | head -n1)
  else
    echo "apikey.sh: need python3 or jq to read $cfg" >&2; exit 1
  fi
elif [ -f "$home/config.yaml" ]; then
  cfg="$home/config.yaml"
  # Minimal YAML walk: find the current context's tenant, then that tenant's apikey.
  key=$(awk -v want="$want" -v field="$field" '
    /^current-context:/ && want=="" { want=$2; gsub(/"/,"",want) }
    /^contexts:/ { sec="ctx"; next } /^tenants:/ { sec="ten"; next } /^[a-z]/ { sec="" }
    sec=="ctx" && /^- name:/ { cname=$3; gsub(/"/,"",cname) }
    sec=="ctx" && /^  app-url:/ && cname==want && field=="appurl" { u=$2; gsub(/"/,"",u); printf "%s", (u==""?"app.speedscale.com":u); exit }
    sec=="ctx" && /^  tenant:/ && cname==want { tenant=$2; gsub(/"/,"",tenant) }
    sec=="ten" && /^- / { tname=""; tkey="" }
    sec=="ten" && /name:/ { v=$NF; gsub(/"/,"",v); if ($1=="name:" || $2=="name:") tname=v }
    sec=="ten" && /^  apikey:/ { tkey=$2; gsub(/"/,"",tkey); if (tname==tenant && tkey!="") { printf "%s", tkey; exit } }
  ' "$cfg")
else
  echo "apikey.sh: no Speedscale config in $home; run 'speedctl init' first or export SPEEDSCALE_API_KEY" >&2; exit 1
fi

if [ -z "$key" ]; then echo "apikey.sh: no $field found for context '${want:-current}' in $cfg" >&2; exit 1; fi
printf '%s' "$key"
