from __future__ import annotations


def test_port_verification_skips_disabled_services(monkeypatch):
    import start as start_module

    starter = start_module.AtlasStarter()
    env = {
        "SUPABASE_DB_PORT": "",
        "REDIS_PORT": "",
        "SUPABASE_META_PORT": "",
        "SUPABASE_STORAGE_PORT": "",
        "SUPABASE_AUTH_PORT": "",
        "SUPABASE_API_PORT": "",
        "SUPABASE_REALTIME_PORT": "",
        "SUPABASE_STUDIO_PORT": "",
        "GRAPH_DB_PORT": "",
        "WEAVIATE_PORT": "63020",
        "WEAVIATE_SOURCE": "disabled",
        "WEAVIATE_SCALE": "0",
        "LOCAL_DEEP_RESEARCHER_PORT": "",
        "OPEN_WEB_UI_PORT": "",
        "BACKEND_PORT": "",
        "KONG_HTTP_PORT": "",
        "KONG_HTTPS_PORT": "",
        "N8N_PORT": "",
        "SEARXNG_PORT": "",
        "JUPYTERHUB_PORT": "",
        "LITELLM_PORT": "",
        "COMFYUI_SCALE": "0",
    }
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(starter.config_parser, "parse_env_file", lambda: env)
    monkeypatch.setattr(
        starter.docker_manager,
        "get_service_port",
        lambda service, port: calls.append((service, port)) or "",
    )

    starter.show_container_status_and_verify_ports(on_line=lambda _msg, _level: None)

    assert ("weaviate", "8080") not in calls


def test_one_shot_init_failure_fails_startup(monkeypatch):
    import start as start_module

    starter = start_module.AtlasStarter()
    monkeypatch.setattr(
        starter.config_parser,
        "parse_env_file",
        lambda: {"N8N_INIT_SCALE": "1"},
    )
    monkeypatch.setattr(
        starter.docker_manager,
        "failed_one_shot_services",
        lambda services: [("n8n-init", "exit 1")],
    )

    assert starter.verify_one_shot_init_containers() is False


def test_one_shot_init_skipped_when_scale_zero(monkeypatch):
    import start as start_module

    starter = start_module.AtlasStarter()
    monkeypatch.setattr(
        starter.config_parser,
        "parse_env_file",
        lambda: {"N8N_INIT_SCALE": "0"},
    )

    def fail_if_called(_services):
        raise AssertionError("disabled init container should not be inspected")

    monkeypatch.setattr(starter.docker_manager, "failed_one_shot_services", fail_if_called)

    assert starter.verify_one_shot_init_containers() is True
