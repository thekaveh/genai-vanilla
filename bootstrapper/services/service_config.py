"""
Service configuration generation based on YAML and SOURCE values.

Python implementation of generate_service_environment() and related functions from start.sh.
"""

import re
from typing import Dict, Any, Optional
from core.config_parser import ConfigParser
from utils.system import get_localhost_host, resolve_host_gateway_ip


class ServiceConfig:
    """Generates service configurations based on YAML and SOURCE values."""
    
    def __init__(self, config_parser: Optional[ConfigParser] = None):
        """
        Initialize service configuration manager.
        
        Args:
            config_parser: ConfigParser instance (creates new one if None)
        """
        self.config_parser = config_parser or ConfigParser()
        self.yaml_config = None
        self.service_sources = {}
        self.localhost_host = get_localhost_host()
        
    def load_config(self) -> bool:
        """
        Load YAML configuration and service sources.
        
        Returns:
            bool: True if loaded successfully
        """
        try:
            self.yaml_config = self.config_parser.load_yaml_config()
            self.service_sources = self.config_parser.parse_service_sources()
            return True
        except Exception as e:
            print(f"❌ Failed to load configuration: {e}")
            return False
    
    def get_service_config(self, service_key: str, source_value: str) -> Dict[str, Any]:
        """
        Get configuration for a specific service and source.
        
        Args:
            service_key: Service key in YAML (e.g., "llm_provider")
            source_value: SOURCE value (e.g., "ollama-container-cpu")
            
        Returns:
            dict: Service configuration from YAML
        """
        if not self.yaml_config:
            return {}
            
        source_configurable = self.yaml_config.get('source_configurable', {})
        service_configs = source_configurable.get(service_key, {})
        return service_configs.get(source_value, {})
    
    def generate_service_environment(self) -> Dict[str, str]:
        """
        Generate all service environment variables based on YAML configuration.
        Replicates the generate_service_environment() function from start.sh.
        
        Returns:
            dict: Dictionary of environment variables to set
        """
        if not self.load_config():
            return {}
            
        env_vars = {}

        # Resolve host gateway IP for extra_hosts compatibility (Docker vs Podman)
        env_vars['HOST_GATEWAY_IP'] = resolve_host_gateway_ip()

        # Generate LLM Provider (Ollama) configuration
        llm_config = self._generate_llm_provider_config()
        env_vars.update(llm_config)

        # Generate cloud-provider toggles for the LiteLLM gateway
        cloud_config = self._generate_cloud_providers_config()
        env_vars.update(cloud_config)

        # Generate ComfyUI configuration
        comfyui_config = self._generate_comfyui_config()
        env_vars.update(comfyui_config)
        
        # Generate MinIO configuration
        minio_config = self._generate_minio_config()
        env_vars.update(minio_config)

        # Generate Weaviate configuration
        weaviate_config = self._generate_weaviate_config()
        env_vars.update(weaviate_config)
        
        # Generate Multi2Vec CLIP configuration
        clip_config = self._generate_clip_config()
        env_vars.update(clip_config)

        # Generate STT and TTS Provider configuration.
        # We pass the running env_vars dict through both so the TTS pass sees
        # any SPEACHES_SCALE / COMPOSE_PROFILES that STT already set — this is
        # how the speaches dedup avoids double-adding profile or scale.
        stt_config = self._generate_stt_provider_config(shared_env=env_vars)
        env_vars.update(stt_config)

        tts_config = self._generate_tts_provider_config(shared_env=env_vars)
        env_vars.update(tts_config)

        # Generate Document Processor configuration
        doc_config = self._generate_doc_processor_config()
        env_vars.update(doc_config)

        # Generate OpenClaw configuration
        openclaw_config = self._generate_openclaw_config()
        env_vars.update(openclaw_config)

        # Generate Hermes Agent configuration
        hermes_config = self._generate_hermes_config()
        env_vars.update(hermes_config)

        # Generate Ray cluster configuration
        ray_source = self.service_sources.get("RAY_SOURCE", "disabled")
        ray_config = self._generate_ray_config(
            source_value=ray_source,
            shared_env=env_vars,
        )
        env_vars.update(ray_config)

        # Generate other service configurations
        other_configs = self._generate_other_services_config()
        env_vars.update(other_configs)
        
        # Generate adaptive service configurations (pass accumulated vars for endpoint lookups)
        adaptive_configs = self._generate_adaptive_services_config(all_env_vars=env_vars)
        env_vars.update(adaptive_configs)
        
        return env_vars
    
    def _generate_llm_provider_config(self) -> Dict[str, str]:
        """Generate LLM engine (Ollama upstream) configuration.

        Emits LITELLM_OLLAMA_UPSTREAM (consumed by the LiteLLM config template
        only) plus LITELLM_BASE_URL (consumed by every LLM-using service).
        OLLAMA_SCALE / OLLAMA_NVIDIA_VISIBLE_DEVICES / OLLAMA_DEPLOY_RESOURCES
        still gate the upstream Ollama service block in compose.
        """
        source_value = self.service_sources.get('LLM_PROVIDER_SOURCE', 'ollama-container-cpu')
        config = self.get_service_config('llm_provider', source_value)

        env_vars = {}

        # LiteLLM is mandatory and listens on a fixed internal address.
        env_vars['LITELLM_BASE_URL'] = 'http://litellm:4000'

        # Set scale (Ollama upstream service replicas)
        scale = config.get('scale', 1)
        env_vars['OLLAMA_SCALE'] = str(scale)

        # Resolve the upstream URL (LiteLLM consumes this when LLM_PROVIDER_SOURCE
        # is one of the ollama-* values). Empty string when source=none.
        endpoint = config.get('environment', {}).get('OLLAMA_ENDPOINT', 'http://ollama:11434')
        endpoint = endpoint.replace('host.docker.internal', self.localhost_host)
        env_vars['LITELLM_OLLAMA_UPSTREAM'] = endpoint

        # Set GPU devices if specified
        gpu_devices = config.get('environment', {}).get('NVIDIA_VISIBLE_DEVICES')
        if gpu_devices:
            env_vars['OLLAMA_NVIDIA_VISIBLE_DEVICES'] = gpu_devices
        else:
            env_vars['OLLAMA_NVIDIA_VISIBLE_DEVICES'] = 'null'

        # Set deployment resources
        deploy_resources = config.get('deploy', {})
        if deploy_resources:
            env_vars['OLLAMA_DEPLOY_RESOURCES'] = str(deploy_resources)
        else:
            env_vars['OLLAMA_DEPLOY_RESOURCES'] = '~'

        return env_vars

    def _generate_cloud_providers_config(self) -> Dict[str, str]:
        """Generate cloud-provider toggle env vars consumed by
        ``llm-catalog-init`` (which gates the active rows it writes
        per-provider). Each cloud_* SOURCE is a binary enabled/disabled
        selector. Tuple list lives in utils/cloud_providers.py.
        """
        from utils.cloud_providers import CLOUD_PROVIDERS

        env_vars: Dict[str, str] = {}
        enabled_providers = []
        for provider in CLOUD_PROVIDERS:
            source_value = self.service_sources.get(provider.source_var, 'disabled')
            is_enabled = source_value == 'enabled'
            env_vars[provider.enabled_flag_var] = 'true' if is_enabled else 'false'
            if is_enabled:
                enabled_providers.append(provider.key)

        env_vars['LITELLM_ENABLED_PROVIDERS'] = ','.join(enabled_providers)
        return env_vars
    
    def _generate_comfyui_config(self) -> Dict[str, str]:
        """Generate ComfyUI configuration."""
        source_value = self.service_sources.get('COMFYUI_SOURCE', 'container-cpu')
        config = self.get_service_config('comfyui', source_value)
        
        env_vars = {}
        
        # Set scale
        scale = config.get('scale', 1)
        env_vars['COMFYUI_SCALE'] = str(scale)
        
        # Set endpoint
        endpoint = config.get('environment', {}).get('COMFYUI_ENDPOINT', 'http://comfyui:18188')
        endpoint = endpoint.replace('host.docker.internal', self.localhost_host)
        env_vars['COMFYUI_ENDPOINT'] = endpoint
        
        # Set deployment resources
        deploy_resources = config.get('deploy', {})
        if deploy_resources:
            env_vars['COMFYUI_DEPLOY_RESOURCES'] = str(deploy_resources)
        else:
            env_vars['COMFYUI_DEPLOY_RESOURCES'] = '~'
            
        # Set local ComfyUI flag
        is_local = config.get('environment', {}).get('IS_LOCAL_COMFYUI', 'false')
        env_vars['IS_LOCAL_COMFYUI'] = is_local
        
        return env_vars
    
    def _generate_minio_config(self) -> Dict[str, str]:
        """Generate MinIO env vars from the minio manifest's runtime_sc block."""
        source_value = self.service_sources.get('MINIO_SOURCE', 'container')
        config = self.get_service_config('minio', source_value)
        env_vars: Dict[str, str] = {}

        # Scale follows the source variant directly.
        env_vars['MINIO_SCALE'] = str(config.get('scale', 1))

        # MINIO_ENDPOINT — internal Compose-network URL; written as-is from YAML.
        env_vars['MINIO_ENDPOINT'] = config.get('environment', {}).get('MINIO_ENDPOINT', '')

        # MINIO_PUBLIC_ENDPOINT — host S3 API URL; may contain a ${MINIO_PORT} token
        # from the manifest's runtime_sc block. Expand against the current .env value.
        current_env = self.config_parser.parse_env_file()
        public_template = config.get('environment', {}).get('MINIO_PUBLIC_ENDPOINT', '')
        if public_template:
            minio_port = current_env.get('MINIO_PORT', '63030')
            env_vars['MINIO_PUBLIC_ENDPOINT'] = public_template.replace('${MINIO_PORT}', minio_port)
        else:
            env_vars['MINIO_PUBLIC_ENDPOINT'] = ''

        # MINIO_PUBLIC_CONSOLE_ENDPOINT — host console URL; may contain a
        # ${MINIO_CONSOLE_PORT} token from the manifest. Used by MinIO's
        # MINIO_BROWSER_REDIRECT_URL — must point at the console (port 9001 / host
        # MINIO_CONSOLE_PORT), NOT the S3 API.
        console_template = config.get('environment', {}).get('MINIO_PUBLIC_CONSOLE_ENDPOINT', '')
        if console_template:
            console_port = current_env.get('MINIO_CONSOLE_PORT', '63018')
            env_vars['MINIO_PUBLIC_CONSOLE_ENDPOINT'] = console_template.replace('${MINIO_CONSOLE_PORT}', console_port)
        else:
            env_vars['MINIO_PUBLIC_CONSOLE_ENDPOINT'] = ''

        return env_vars

    def _generate_weaviate_config(self) -> Dict[str, str]:
        """Generate Weaviate configuration."""
        source_value = self.service_sources.get('WEAVIATE_SOURCE', 'container')
        config = self.get_service_config('weaviate', source_value)
        
        env_vars = {}
        
        # Set scale
        scale = config.get('scale', 1)
        env_vars['WEAVIATE_SCALE'] = str(scale)
        
        # Set URL
        weaviate_url = config.get('environment', {}).get('WEAVIATE_URL', 'http://weaviate:8080')
        weaviate_url = weaviate_url.replace('host.docker.internal', self.localhost_host)
        env_vars['WEAVIATE_URL'] = weaviate_url
        
        # Weaviate's text2vec-openai / generative-openai modules talk to LiteLLM.
        # The base URL goes into per-collection module configs (set by
        # weaviate-init), not into Weaviate's startup env.
        env_file_vars = self.config_parser.parse_env_file()
        env_vars['WEAVIATE_LITELLM_BASE_URL'] = 'http://litellm:4000/v1'
        env_vars['WEAVIATE_LITELLM_API_KEY'] = env_file_vars.get('LITELLM_MASTER_KEY', '')

        # Multi2Vec CLIP is optional. If its service is disabled/scaled to zero,
        # Weaviate must not enable the multi2vec-clip module or it will block
        # startup waiting for a missing remote inference API. Start from the
        # configured module list so advanced users keep any extra modules while
        # the CLIP module is toggled to match MULTI2VEC_CLIP_SOURCE.
        clip_source = self.service_sources.get('MULTI2VEC_CLIP_SOURCE', 'container-cpu')
        default_modules = (
            'text2vec-openai,text2vec-ollama,multi2vec-clip,'
            'generative-openai,generative-ollama'
        )
        configured_modules = env_file_vars.get('WEAVIATE_ENABLE_MODULES', default_modules)
        weaviate_modules = [
            module.strip()
            for module in configured_modules.split(',')
            if module.strip()
        ]

        if clip_source == 'disabled':
            weaviate_modules = [
                module for module in weaviate_modules if module != 'multi2vec-clip'
            ]
            env_vars['CLIP_INFERENCE_API'] = ''
        else:
            if 'multi2vec-clip' not in weaviate_modules:
                insert_after = 'text2vec-ollama'
                insert_index = (
                    weaviate_modules.index(insert_after) + 1
                    if insert_after in weaviate_modules
                    else len(weaviate_modules)
                )
                weaviate_modules.insert(insert_index, 'multi2vec-clip')
            env_vars['CLIP_INFERENCE_API'] = env_file_vars.get(
                'CLIP_INFERENCE_API', 'http://multi2vec-clip:8080'
            ) or 'http://multi2vec-clip:8080'

        env_vars['WEAVIATE_ENABLE_MODULES'] = ','.join(weaviate_modules)

        return env_vars
    
    def _generate_clip_config(self) -> Dict[str, str]:
        """Generate Multi2Vec CLIP configuration."""
        source_value = self.service_sources.get('MULTI2VEC_CLIP_SOURCE', 'container-cpu')
        config = self.get_service_config('multi2vec-clip', source_value)
        
        env_vars = {}
        
        # Set scale
        scale = config.get('scale', 1)  
        env_vars['CLIP_SCALE'] = str(scale)
        
        # Set CUDA enable flag
        cuda_flag = config.get('environment', {}).get('ENABLE_CUDA', '0')
        env_vars['CLIP_ENABLE_CUDA'] = cuda_flag
        
        # Set deployment resources
        deploy_resources = config.get('deploy', {})
        if deploy_resources:
            env_vars['CLIP_DEPLOY_RESOURCES'] = str(deploy_resources)
        else:
            env_vars['CLIP_DEPLOY_RESOURCES'] = '~'
            
        return env_vars

    def _add_compose_profile(self, env_vars: Dict[str, str], profile: str) -> None:
        """Append a docker-compose profile to COMPOSE_PROFILES idempotently.

        Reads the running tally from ``env_vars`` first (so multiple generators
        in a single pass can stack additions) and falls back to whatever the
        user pre-seeded in .env. Skips the add if ``profile`` is already
        present. Used by the speaches dedup path — if both TTS and STT pick
        speaches, both generators try to add the same profile and we don't
        want it duplicated in COMPOSE_PROFILES.
        """
        current = env_vars.get('COMPOSE_PROFILES',
                               self.service_sources.get('COMPOSE_PROFILES', '')) or ''
        existing = [p for p in current.split(',') if p]
        if profile in existing:
            return
        existing.append(profile)
        env_vars['COMPOSE_PROFILES'] = ','.join(existing)

    def _generate_stt_provider_config(self, shared_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate STT Provider configuration.

        ``shared_env`` carries env vars accumulated by earlier generators so
        we can stack COMPOSE_PROFILES additions correctly (and so the TTS
        generator, when it runs next, sees that SPEACHES_SCALE is already 1).
        """
        source_value = self.service_sources.get('STT_PROVIDER_SOURCE', 'disabled')
        config = self.get_service_config('stt_provider', source_value)

        env_vars: Dict[str, str] = dict(shared_env or {})

        # Default: STT not running (zero scale, blank endpoint). Each
        # branch below flips the bits it owns. The provider-level scale
        # is consumed by the wizard ServiceTable to colour the row.
        env_vars.setdefault('STT_PROVIDER_SCALE', '0')

        # Endpoint comes from the YAML entry; for ``http://host.docker.internal``
        # URLs we swap in the platform-correct gateway hostname.
        endpoint = config.get('environment', {}).get('STT_ENDPOINT', '')
        endpoint = endpoint.replace('host.docker.internal', self.localhost_host)
        env_vars['STT_ENDPOINT'] = endpoint

        if source_value.startswith('speaches-container'):
            env_vars['SPEACHES_SCALE'] = '1'
            profile = 'speaches-gpu' if source_value.endswith('-gpu') else 'speaches-cpu'
            self._add_compose_profile(env_vars, profile)
            # Mirror the speaches external port into the wizard's STT slot
            # so the row shows the right :port without resorting to a
            # per-source port_var in state_builder.
            speaches_port = self._resolved_env('SPEACHES_PORT', env_vars)
            if speaches_port:
                env_vars['STT_PROVIDER_PORT'] = speaches_port
            env_vars['STT_PROVIDER_SCALE'] = '1'
            # Parakeet stays off in this branch.
            env_vars.setdefault('PARAKEET_GPU_SCALE', '0')
        elif source_value == 'parakeet-container-gpu':
            env_vars['PARAKEET_GPU_SCALE'] = '1'
            self._add_compose_profile(env_vars, 'parakeet-gpu')
            env_vars['STT_PROVIDER_SCALE'] = '1'
            env_vars.setdefault('SPEACHES_SCALE', '0')
        elif source_value in ('parakeet-localhost', 'whisper-cpp-localhost'):
            env_vars['PARAKEET_GPU_SCALE'] = '0'
            env_vars.setdefault('SPEACHES_SCALE', '0')
            # STT_PROVIDER_SCALE stays 0 — wizard reads port from URL
        else:  # disabled
            env_vars['PARAKEET_GPU_SCALE'] = '0'
            env_vars.setdefault('SPEACHES_SCALE', '0')
            env_vars['STT_ENDPOINT'] = ''

        return env_vars

    def _generate_tts_provider_config(self, shared_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate TTS Provider configuration.

        See ``_generate_stt_provider_config`` for the role of ``shared_env``;
        same dedup pattern, applied symmetrically.
        """
        source_value = self.service_sources.get('TTS_PROVIDER_SOURCE', 'disabled')
        config = self.get_service_config('tts_provider', source_value)

        env_vars: Dict[str, str] = dict(shared_env or {})
        env_vars.setdefault('TTS_PROVIDER_SCALE', '0')

        endpoint = config.get('environment', {}).get('TTS_ENDPOINT', '')
        endpoint = endpoint.replace('host.docker.internal', self.localhost_host)
        env_vars['TTS_ENDPOINT'] = endpoint

        if source_value.startswith('speaches-container'):
            # If STT also picked speaches, SPEACHES_SCALE is already 1 and
            # the profile is already in COMPOSE_PROFILES — both adds are
            # idempotent. If STT picked something else, this is the only
            # place speaches gets activated.
            env_vars['SPEACHES_SCALE'] = '1'
            wanted_profile = 'speaches-gpu' if source_value.endswith('-gpu') else 'speaches-cpu'
            stt_source = self.service_sources.get('STT_PROVIDER_SOURCE', 'disabled')
            if stt_source.startswith('speaches-container'):
                # Mixed cpu/gpu: GPU wins. Remove cpu profile if present;
                # add gpu. Either source value already added its own profile,
                # so we only re-add when the resolved winner differs.
                stt_is_gpu = stt_source.endswith('-gpu')
                tts_is_gpu = source_value.endswith('-gpu')
                if stt_is_gpu != tts_is_gpu:
                    wanted_profile = 'speaches-gpu'
                    self._remove_compose_profile(env_vars, 'speaches-cpu')
                    print(
                        "ℹ️  Speaches CPU/GPU mismatch between TTS_PROVIDER_SOURCE "
                        f"({source_value}) and STT_PROVIDER_SOURCE ({stt_source}); "
                        "using speaches-gpu for both."
                    )
            self._add_compose_profile(env_vars, wanted_profile)
            speaches_port = self._resolved_env('SPEACHES_PORT', env_vars)
            if speaches_port:
                env_vars['TTS_PROVIDER_PORT'] = speaches_port
            env_vars['TTS_PROVIDER_SCALE'] = '1'
            env_vars.setdefault('CHATTERBOX_SCALE', '0')
        elif source_value == 'chatterbox-container-gpu':
            env_vars['CHATTERBOX_SCALE'] = '1'
            self._add_compose_profile(env_vars, 'chatterbox-gpu')
            chatterbox_port = self._resolved_env('CHATTERBOX_PORT', env_vars)
            if chatterbox_port:
                env_vars['TTS_PROVIDER_PORT'] = chatterbox_port
            env_vars['TTS_PROVIDER_SCALE'] = '1'
            env_vars.setdefault('SPEACHES_SCALE', '0')
        elif source_value == 'chatterbox-localhost':
            env_vars['CHATTERBOX_SCALE'] = '0'
            env_vars.setdefault('SPEACHES_SCALE', '0')
        else:  # disabled
            env_vars['CHATTERBOX_SCALE'] = '0'
            env_vars.setdefault('SPEACHES_SCALE', '0')
            env_vars['TTS_ENDPOINT'] = ''

        return env_vars

    def _remove_compose_profile(self, env_vars: Dict[str, str], profile: str) -> None:
        """Drop a profile from COMPOSE_PROFILES if present (no-op otherwise)."""
        current = env_vars.get('COMPOSE_PROFILES',
                               self.service_sources.get('COMPOSE_PROFILES', '')) or ''
        existing = [p for p in current.split(',') if p and p != profile]
        env_vars['COMPOSE_PROFILES'] = ','.join(existing)

    def _resolved_env(self, var: str, env_vars: Dict[str, str]) -> str:
        """Look up ``var`` in this run's accumulated env, then .env, then ''.

        Used by the TTS/STT generators to read the speaches/chatterbox port
        slots that the port allocator wrote earlier in the pipeline.
        """
        if var in env_vars:
            return env_vars[var]
        return self.config_parser.parse_env_file().get(var, '')

    def _generate_doc_processor_config(self) -> Dict[str, str]:
        """Generate Document Processor (Docling) configuration."""
        source_value = self.service_sources.get('DOC_PROCESSOR_SOURCE', 'disabled')
        config = self.get_service_config('doc_processor', source_value)

        env_vars = {}

        # Set DOCLING_ENDPOINT with localhost replacement (matching STT/TTS pattern)
        if source_value == 'disabled':
            env_vars['DOCLING_ENDPOINT'] = ''
        else:
            endpoint = config.get('environment', {}).get('DOCLING_ENDPOINT', 'http://host.docker.internal:63021')
            # For localhost mode, dynamically replace port with actual DOC_PROCESSOR_PORT from .env
            if source_value == 'docling-localhost':
                current_env = self.config_parser.parse_env_file()
                doc_port = current_env.get('DOC_PROCESSOR_PORT', '63021')
                endpoint = f'http://{self.localhost_host}:{doc_port}'
            else:
                # For container mode, just apply localhost_host replacement
                endpoint = endpoint.replace('host.docker.internal', self.localhost_host)
            env_vars['DOCLING_ENDPOINT'] = endpoint

        # Set scale and activate profile based on SOURCE
        if source_value == 'docling-container-gpu':
            env_vars['DOCLING_GPU_SCALE'] = '1'
            # Activate docling-gpu and doc-gpu profiles to enable building the GPU service
            current_profiles = self.service_sources.get('COMPOSE_PROFILES', '')
            new_profiles = 'docling-gpu,doc-gpu' if not current_profiles else f"{current_profiles},docling-gpu,doc-gpu"
            env_vars['COMPOSE_PROFILES'] = new_profiles
        elif source_value == 'docling-localhost':
            env_vars['DOCLING_GPU_SCALE'] = '0'
        else:  # disabled
            env_vars['DOCLING_GPU_SCALE'] = '0'

        return env_vars

    def _generate_hermes_config(self) -> Dict[str, str]:
        """Generate Hermes Agent (programmable AI agent runtime) configuration.

        Mirrors _generate_openclaw_config(): drives HERMES_SCALE and
        HERMES_ENDPOINT from HERMES_SOURCE, with localhost replacement
        for cross-platform host-gateway addressing. HERMES_INIT_SCALE
        is set in _generate_other_services_config() to keep init-scale
        logic centralized.
        """
        source_value = self.service_sources.get('HERMES_SOURCE', 'container')
        config = self.get_service_config('hermes', source_value)

        env_vars: Dict[str, str] = {}

        if source_value == 'disabled':
            env_vars['HERMES_ENDPOINT'] = ''
            env_vars['HERMES_SCALE'] = '0'
        elif source_value == 'localhost':
            current_env = self.config_parser.parse_env_file()
            hermes_port = current_env.get('HERMES_API_PORT', '63028')
            endpoint = f'http://{self.localhost_host}:{hermes_port}'
            env_vars['HERMES_ENDPOINT'] = endpoint
            env_vars['HERMES_SCALE'] = '0'
        else:  # container
            endpoint = config.get('environment', {}).get(
                'HERMES_ENDPOINT', 'http://hermes:8642')
            endpoint = endpoint.replace('host.docker.internal', self.localhost_host)
            env_vars['HERMES_ENDPOINT'] = endpoint
            env_vars['HERMES_SCALE'] = '1'

        return env_vars

    def _generate_ray_config(self, source_value: str, shared_env: dict) -> dict:
        """Resolve Ray's auto-managed env vars from RAY_SOURCE + RAY_WORKER_COUNT.

        Sets four env vars based on the active source:
          - RAY_IMAGE — CPU or GPU image tag (compose interpolates this)
          - RAY_HEAD_SCALE — 1 when container source, 0 otherwise
          - RAY_WORKER_SCALE — RAY_WORKER_COUNT when container source, 0 otherwise
          - RAY_ADDRESS — `ray://ray-head:10001` for container sources,
            `${RAY_EXTERNAL_ADDRESS}` value for ray-external, empty otherwise

        Args:
            source_value: Current RAY_SOURCE value (one of `ray-container-cpu`,
                `ray-container-gpu`, `ray-external`, `disabled`).
            shared_env: Env vars accumulated by earlier generators + manifest
                defaults. We read `RAY_WORKER_COUNT`, `RAY_IMAGE`,
                `RAY_GPU_IMAGE`, `RAY_EXTERNAL_ADDRESS` from here.

        Returns:
            Dict of resolved env-var assignments. The caller merges this into
            the .env-example output.
        """
        cpu_image = shared_env.get("RAY_IMAGE", "rayproject/ray:2.55.1") or "rayproject/ray:2.55.1"
        gpu_image = shared_env.get("RAY_GPU_IMAGE", "rayproject/ray:2.55.1-gpu") or "rayproject/ray:2.55.1-gpu"
        external_addr = (shared_env.get("RAY_EXTERNAL_ADDRESS", "") or "").strip()

        # Parse RAY_WORKER_COUNT with safe fallback to the manifest default (2).
        raw_count = shared_env.get("RAY_WORKER_COUNT", "2")
        try:
            worker_count = int(raw_count)
            if worker_count < 0:
                worker_count = 2
        except (ValueError, TypeError):
            worker_count = 2

        if source_value == "ray-container-cpu":
            return {
                "RAY_IMAGE": cpu_image,
                "RAY_HEAD_SCALE": "1",
                "RAY_WORKER_SCALE": str(worker_count),
                "RAY_ADDRESS": "ray://ray-head:10001",
            }
        if source_value == "ray-container-gpu":
            return {
                "RAY_IMAGE": gpu_image,
                "RAY_HEAD_SCALE": "1",
                "RAY_WORKER_SCALE": str(worker_count),
                "RAY_ADDRESS": "ray://ray-head:10001",
            }
        if source_value == "ray-external":
            return {
                "RAY_IMAGE": cpu_image,  # irrelevant (scale=0) but must be set
                "RAY_HEAD_SCALE": "0",
                "RAY_WORKER_SCALE": "0",
                "RAY_ADDRESS": external_addr,
            }
        # disabled (or any unknown source value): everything off, no address
        return {
            "RAY_IMAGE": cpu_image,
            "RAY_HEAD_SCALE": "0",
            "RAY_WORKER_SCALE": "0",
            "RAY_ADDRESS": "",
        }

    def _generate_openclaw_config(self) -> Dict[str, str]:
        """Generate OpenClaw AI Agent configuration."""
        source_value = self.service_sources.get('OPENCLAW_SOURCE', 'disabled')
        config = self.get_service_config('openclaw', source_value)

        env_vars = {}

        # Set OPENCLAW_ENDPOINT with localhost replacement
        if source_value == 'disabled':
            env_vars['OPENCLAW_ENDPOINT'] = ''
            env_vars['OPENCLAW_SCALE'] = '0'
        elif source_value == 'localhost':
            current_env = self.config_parser.parse_env_file()
            openclaw_port = current_env.get('OPENCLAW_GATEWAY_PORT', '63024')
            endpoint = f'http://{self.localhost_host}:{openclaw_port}'
            env_vars['OPENCLAW_ENDPOINT'] = endpoint
            env_vars['OPENCLAW_SCALE'] = '0'
        else:  # container
            endpoint = config.get('environment', {}).get(
                'OPENCLAW_ENDPOINT', 'http://openclaw-gateway:18789')
            endpoint = endpoint.replace('host.docker.internal', self.localhost_host)
            env_vars['OPENCLAW_ENDPOINT'] = endpoint
            env_vars['OPENCLAW_SCALE'] = '1'

        return env_vars

    def _generate_other_services_config(self) -> Dict[str, str]:
        """Generate configuration for other services."""
        env_vars = {}
        
        # N8N configuration
        n8n_source = self.service_sources.get('N8N_SOURCE', 'container')
        n8n_config = self.get_service_config('n8n', n8n_source)
        
        # Check if N8N_SCALE was already set (e.g., by dependency manager)
        current_env = self.config_parser.parse_env_file()
        n8n_scale = current_env.get('N8N_SCALE', str(n8n_config.get('scale', 1)))
        
        env_vars['N8N_SCALE'] = n8n_scale
        env_vars['N8N_WORKER_SCALE'] = n8n_scale  # Worker follows main N8N scale
        env_vars['N8N_INIT_SCALE'] = n8n_scale    # Init follows main N8N scale
        
        # SearxNG configuration  
        searxng_source = self.service_sources.get('SEARXNG_SOURCE', 'container')
        searxng_config = self.get_service_config('searxng', searxng_source)
        env_vars['SEARXNG_SCALE'] = str(searxng_config.get('scale', 1))
        
        # Neo4j configuration
        neo4j_source = self.service_sources.get('NEO4J_GRAPH_DB_SOURCE', 'container')
        neo4j_config = self.get_service_config('neo4j-graph-db', neo4j_source)
        env_vars['NEO4J_SCALE'] = str(neo4j_config.get('scale', 1))
        
        # Set Neo4j URI
        neo4j_uri = neo4j_config.get('environment', {}).get('NEO4J_URI', 'bolt://neo4j-graph-db:7687')
        neo4j_uri = neo4j_uri.replace('host.docker.internal', self.localhost_host)
        env_vars['NEO4J_URI'] = neo4j_uri
        
        # Initialization service scales - conditional based on parent service sources
        
        # WEAVIATE_INIT_SCALE follows WEAVIATE_SCALE 
        weaviate_source = self.service_sources.get('WEAVIATE_SOURCE', 'container')
        if weaviate_source == 'disabled':
            env_vars['WEAVIATE_INIT_SCALE'] = '0'
        else:
            weaviate_config = self.get_service_config('weaviate', weaviate_source)
            env_vars['WEAVIATE_INIT_SCALE'] = str(weaviate_config.get('scale', 1))
        
        # OLLAMA_PULL_SCALE: 1 only for in-stack ollama-container-* sources.
        # Host-side Ollama (ollama-localhost / ollama-external) is not
        # pull-controllable from the stack — sending /api/pull at the
        # user's host Ollama would surprise them and is what
        # llm-catalog-init's apply_ollama_selection refuses to register
        # custom rows for. Source=none has no upstream at all.
        llm_source = self.service_sources.get('LLM_PROVIDER_SOURCE', 'ollama-container-cpu')
        if llm_source.startswith('ollama-container-'):
            env_vars['OLLAMA_PULL_SCALE'] = '1'
        else:
            env_vars['OLLAMA_PULL_SCALE'] = '0'
            
        # COMFYUI_CATALOG_INIT_SCALE: 1 for ALL non-disabled sources.
        # The catalog-init container UPSERTs public.comfyui_models so the
        # backend /comfyui/db/models endpoint (consumed by Open WebUI +
        # n8n) sees the user's picks regardless of whether ComfyUI is
        # in-stack or host-side.
        #
        # COMFYUI_INIT_SCALE: 1 only for container sources. For localhost
        # / external the named-volume `comfyui-models` isn't mounted into
        # the user's host ComfyUI install, so running the wget-based init
        # would write into a volume nothing reads. The user pulls models
        # into their host install themselves — exact mirror of how
        # OLLAMA_PULL_SCALE behaves for ollama-localhost / ollama-external.
        comfyui_source = self.service_sources.get('COMFYUI_SOURCE', 'container-cpu')
        if comfyui_source == 'disabled':
            env_vars['COMFYUI_INIT_SCALE'] = '0'
            env_vars['COMFYUI_CATALOG_INIT_SCALE'] = '0'
        elif comfyui_source.startswith('container-'):
            env_vars['COMFYUI_INIT_SCALE'] = '1'
            env_vars['COMFYUI_CATALOG_INIT_SCALE'] = '1'
        else:
            # localhost / external — DB populated, but no wget-into-volume.
            env_vars['COMFYUI_INIT_SCALE'] = '0'
            env_vars['COMFYUI_CATALOG_INIT_SCALE'] = '1'

        # OPENCLAW_INIT_SCALE: follows OPENCLAW_SCALE (1 when container, 0 otherwise)
        openclaw_source = self.service_sources.get('OPENCLAW_SOURCE', 'disabled')
        if openclaw_source == 'container':
            env_vars['OPENCLAW_INIT_SCALE'] = '1'
        else:
            env_vars['OPENCLAW_INIT_SCALE'] = '0'

        # HERMES_INIT_SCALE: follows HERMES_SCALE (1 when container, 0 otherwise).
        # Localhost and disabled both skip the init container — for localhost,
        # the operator owns the on-host config file; for disabled, there's
        # nothing to initialize.
        hermes_source = self.service_sources.get('HERMES_SOURCE', 'container')
        if hermes_source == 'container':
            env_vars['HERMES_INIT_SCALE'] = '1'
        else:
            env_vars['HERMES_INIT_SCALE'] = '0'

        # MINIO_INIT_SCALE: follows MINIO_SOURCE (1 when container, 0 when disabled)
        # Critical: without this, minio-init blocks on a never-healthy minio when
        # MinIO is disabled, hanging compose-up indefinitely.
        minio_source = self.service_sources.get('MINIO_SOURCE', 'container')
        if minio_source == 'container':
            env_vars['MINIO_INIT_SCALE'] = '1'
        else:
            env_vars['MINIO_INIT_SCALE'] = '0'

        return env_vars
    
    def _generate_adaptive_services_config(self, all_env_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate configuration for adaptive services."""
        env_vars = {}
        sources = self.config_parser.parse_service_sources()

        # Backend always enabled (no SOURCE check - always runs)
        env_vars['BACKEND_SCALE'] = '1'

        # Open WebUI - check SOURCE variable
        webui_source = sources.get('OPEN_WEB_UI_SOURCE', 'container')
        env_vars['OPEN_WEB_UI_SCALE'] = '0' if webui_source == 'disabled' else '1'
        env_vars['OPEN_WEB_UI_INIT_SCALE'] = '0' if webui_source == 'disabled' else '1'

        # Open WebUI adaptive TTS/STT (set engine and API base URL when provider is enabled)
        # Read endpoints from already-generated env vars (STT/TTS configs run before adaptive).
        # All current TTS/STT engines (Speaches, Chatterbox, Parakeet, whisper.cpp) expose
        # an OpenAI-compatible /v1/audio/{speech,transcriptions} surface, so the engine name
        # is uniformly 'openai' — only the API base URL differs.
        parent_vars = all_env_vars or {}
        tts_source = sources.get('TTS_PROVIDER_SOURCE', 'disabled')
        env_vars['OPEN_WEB_UI_TTS_ENGINE'] = 'openai' if tts_source != 'disabled' else ''
        tts_endpoint = parent_vars.get('TTS_ENDPOINT', '')
        env_vars['OPEN_WEB_UI_TTS_API_URL'] = f'{tts_endpoint}/v1' if tts_endpoint else ''
        stt_source = sources.get('STT_PROVIDER_SOURCE', 'disabled')
        env_vars['OPEN_WEB_UI_STT_ENGINE'] = 'openai' if stt_source != 'disabled' else ''
        stt_endpoint = parent_vars.get('STT_ENDPOINT', '')
        env_vars['OPEN_WEB_UI_STT_API_URL'] = f'{stt_endpoint}/v1' if stt_endpoint else ''
        # Open WebUI's default TTS model — depends on which engine is active.
        # service_sources only carries ``*_SOURCE`` vars (see parse_service_sources),
        # so we read the model knob directly from .env with a hard-coded fallback.
        if tts_source.startswith('speaches-container'):
            speaches_env = self.config_parser.parse_env_file()
            env_vars['OPEN_WEB_UI_TTS_MODEL'] = speaches_env.get(
                'SPEACHES_TTS_MODEL', 'hexgrad/Kokoro-82M'
            )
            env_vars['OPEN_WEB_UI_TTS_VOICE'] = 'af_heart'
        elif tts_source.startswith('chatterbox'):
            # Chatterbox's /v1/audio/speech accepts any model string; the
            # server uses the loaded checkpoint regardless. "chatterbox-tts-1"
            # is what its /v1/models endpoint advertises.
            env_vars['OPEN_WEB_UI_TTS_MODEL'] = 'chatterbox-tts-1'
            env_vars['OPEN_WEB_UI_TTS_VOICE'] = 'alloy'
        else:
            env_vars['OPEN_WEB_UI_TTS_MODEL'] = ''
            env_vars['OPEN_WEB_UI_TTS_VOICE'] = ''

        # Local Deep Researcher - check SOURCE variable
        researcher_source = sources.get('LOCAL_DEEP_RESEARCHER_SOURCE', 'container')
        env_vars['LOCAL_DEEP_RESEARCHER_SCALE'] = '0' if researcher_source == 'disabled' else '1'

        # JupyterHub - check SOURCE variable
        jupyterhub_source = sources.get('JUPYTERHUB_SOURCE', 'container')
        env_vars['JUPYTERHUB_SCALE'] = '0' if jupyterhub_source == 'disabled' else '1'

        return env_vars
    
    def update_env_file(self, env_vars: Dict[str, str], create_backup: bool = True) -> bool:
        """
        Update .env file with computed environment variables.
        Replicates the update_env_file() function from start.sh.
        
        Args:
            env_vars: Dictionary of environment variables to set
            create_backup: Whether to create backup before updating
            
        Returns:
            bool: True if successful
        """
        env_file_path = self.config_parser.env_file_path
        
        if not env_file_path.exists():
            print(f"❌ .env file not found: {env_file_path}")
            return False
        
        try:
            # Create backup if requested
            if create_backup:
                self.config_parser.create_env_backup()
            
            # Read current .env content
            with open(env_file_path, 'r', encoding="utf-8") as f:
                content = f.read()
            
            updated_content = content
            
            # Update each environment variable
            for var_name, var_value in env_vars.items():
                # Use regex to find and replace the variable assignment
                pattern = rf'^{re.escape(var_name)}=.*$'
                replacement = f'{var_name}={var_value}'

                if re.search(pattern, updated_content, re.MULTILINE):
                    # Variable exists, replace it. Lambda bypasses re.sub's
                    # backslash interpretation in the replacement string
                    # (matches the source_override_manager.py pattern —
                    # env values may contain literal backslashes).
                    updated_content = re.sub(
                        pattern, lambda _m, r=replacement: r, updated_content, flags=re.MULTILINE
                    )
                else:
                    # Variable doesn't exist, append it
                    updated_content += f'\n{replacement}'
            
            # Write updated content back
            with open(env_file_path, 'w', encoding="utf-8") as f:
                f.write(updated_content)
                
            return True
            
        except Exception as e:
            print(f"❌ Failed to update .env file: {e}")
            return False
    
    def check_comfyui_local_models(self) -> None:
        """
        Check ComfyUI local models directory.
        Replicates the ComfyUI local models check from start.sh.
        """
        comfyui_source = self.service_sources.get('COMFYUI_SOURCE', 'container-cpu')
        is_local = comfyui_source == 'localhost'
        
        if is_local:
            from pathlib import Path
            
            # Get local models path from env
            env_vars = self.config_parser.parse_env_file()
            models_path = env_vars.get('COMFYUI_LOCAL_MODELS_PATH', '~/Documents/ComfyUI/models')
            
            # Expand user home directory
            models_path = Path(models_path).expanduser()
            
            if models_path.exists():
                print(f"  • ✅ ComfyUI local models found: {models_path}")
            else:
                print(f"  • ⚠️  ComfyUI local models directory not found: {models_path}")
                print("    Please ensure your local ComfyUI models are in the correct location")
    
    def generate_and_update_env(self, create_backup: bool = True) -> bool:
        """
        Generate service environment and update .env file.
        
        Args:
            create_backup: Whether to create backup before updating
            
        Returns:
            bool: True if successful
        """
        env_vars = self.generate_service_environment()
        
        if not env_vars:
            print("❌ Failed to generate service environment variables")
            return False
            
        return self.update_env_file(env_vars, create_backup)