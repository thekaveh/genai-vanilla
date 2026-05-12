# hermes-init — renders /opt/data/config.yaml from environment before
# the hermes service starts. Tiny alpine image with bash + jq + curl;
# yq is not required (we use envsubst from gettext).
FROM alpine:3.20

RUN apk add --no-cache bash gettext curl jq ca-certificates

# Templates and scripts are bind-mounted from the repo at runtime
# (see docker-compose.yml hermes-init service). The image stays
# generic so it doubles as the OPENCLAW_INIT_IMAGE-style fallback
# alpine.
ENTRYPOINT ["/scripts/init-hermes.sh"]
