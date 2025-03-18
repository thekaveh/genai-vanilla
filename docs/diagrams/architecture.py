#!/usr/bin/env python3
"""
Architecture diagram generator for Vanilla GenAI Stack.
This script generates an architecture diagram based on the current Docker Compose configuration.
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.onprem.database import PostgreSQL
from diagrams.generic.storage import Storage
from diagrams.generic.compute import Rack
from diagrams.onprem.network import Nginx
import os
import re
import subprocess
import yaml
import sys

# Define the output path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "..", "docs", "images")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_services_from_docker_compose(file_path):
    """Extract services and their dependencies from a Docker Compose file."""
    with open(file_path, 'r') as file:
        docker_compose = yaml.safe_load(file)
    
    services = {}
    for service_name, service_config in docker_compose.get('services', {}).items():
        dependencies = []
        if 'depends_on' in service_config:
            depends_on = service_config['depends_on']
            if isinstance(depends_on, list):
                dependencies.extend(depends_on)
            elif isinstance(depends_on, dict):
                dependencies.extend(depends_on.keys())
        
        # Extract image name or build context
        if 'image' in service_config:
            image = service_config['image']
        elif 'build' in service_config:
            if isinstance(service_config['build'], dict) and 'context' in service_config['build']:
                image = f"build:{service_config['build']['context']}"
            else:
                image = f"build:{service_config['build']}"
        else:
            image = "unknown"
        
        services[service_name] = {
            'dependencies': dependencies,
            'image': image,
            'ports': service_config.get('ports', []),
            'volumes': service_config.get('volumes', []),
            'environment': service_config.get('environment', {}),
        }
    
    return services

def get_service_icon(service_name, image):
    """Determine the appropriate icon for a service based on its name and image."""
    # Custom icon paths relative to the script
    custom_icons = {
        "supabase-db": "../images/icons/supabase.png",
        "supabase-meta": "../images/icons/supabase.png",
        "supabase-studio": "../images/icons/supabase.png",
        "graph-db": "../images/icons/neo4j.png",
        "ollama": "../images/icons/ollama.png",
        "ollama-pull": "../images/icons/ollama.png",
    }
    
    # Check if there's a custom icon for this service
    if service_name in custom_icons and os.path.exists(os.path.join(SCRIPT_DIR, custom_icons[service_name])):
        return Custom(service_name, os.path.join(SCRIPT_DIR, custom_icons[service_name]))
    
    # Default icons based on service type
    if "postgres" in image.lower() or "supabase" in service_name.lower() or "sql" in service_name.lower():
        return PostgreSQL(service_name)
    elif "neo4j" in image.lower() or "graph" in service_name.lower():
        return Custom(service_name, os.path.join(SCRIPT_DIR, "../images/icons/neo4j.png"))
    elif "jupyter" in image.lower() or "notebook" in service_name.lower():
        return Custom(service_name, os.path.join(SCRIPT_DIR, "../images/icons/jupyter.png"))
    elif "nginx" in image.lower():
        return Nginx(service_name)
    else:
        return Rack(service_name)

def create_architecture_diagram(services, output_file):
    """Create an architecture diagram using the Diagrams library."""
    graph_attr = {
        "fontsize": "20",
        "bgcolor": "white",
        "rankdir": "TB",
        "splines": "spline",
        "compound": "true",
    }
    
    with Diagram("Vanilla GenAI Stack Architecture", filename=output_file, outformat="png", 
                 show=False, direction="TB", graph_attr=graph_attr):
        
        with Cluster("Docker Compose"):
            service_nodes = {}
            
            # Create all service nodes first
            for service_name, service_config in services.items():
                service_nodes[service_name] = get_service_icon(service_name, service_config['image'])
            
            # Then create edges between services
            for service_name, service_config in services.items():
                for dependency in service_config['dependencies']:
                    if dependency in service_nodes:
                        service_nodes[dependency] >> Edge(label="depends on") >> service_nodes[service_name]
            
            # Add volume connections
            with Cluster("Volumes"):
                volumes = {}
                for service_name, service_config in services.items():
                    for volume in service_config['volumes']:
                        if isinstance(volume, str) and ':' in volume:
                            vol_name = volume.split(':')[0]
                            if vol_name not in volumes:
                                volumes[vol_name] = Storage(vol_name)
                            service_nodes[service_name] << Edge(label="mounts") << volumes[vol_name]

def ensure_icons_directory():
    """Ensure the icons directory exists and contains necessary icons."""
    icons_dir = os.path.join(SCRIPT_DIR, "..", "images", "icons")
    os.makedirs(icons_dir, exist_ok=True)
    
    # List of icon URLs to download if they don't exist
    icons = {
        "supabase.png": "https://seeklogo.com/images/S/supabase-logo-DCC676FFE2-seeklogo.com.png",
        "neo4j.png": "https://dist.neo4j.com/wp-content/uploads/20210423072428/neo4j-logo-2020-1.svg",
        "ollama.png": "https://ollama.ai/public/ollama.png",
        "jupyter.png": "https://jupyter.org/assets/homepage/main-logo.svg"
    }
    
    # Download missing icons
    for icon_name, icon_url in icons.items():
        icon_path = os.path.join(icons_dir, icon_name)
        if not os.path.exists(icon_path):
            try:
                subprocess.run(["curl", "-s", "-o", icon_path, icon_url], check=True)
                print(f"Downloaded {icon_name}")
            except subprocess.CalledProcessError:
                print(f"Failed to download {icon_name} from {icon_url}")

def main():
    """Main function to generate the architecture diagram."""
    # Ensure we have the icons
    ensure_icons_directory()
    
    # Path to the Docker Compose file
    compose_file = os.path.join(SCRIPT_DIR, "..", "..", "docker-compose.yml")
    
    # Extract services from Docker Compose
    services = extract_services_from_docker_compose(compose_file)
    
    # Create the architecture diagram
    output_file = os.path.join(OUTPUT_DIR, "architecture")
    create_architecture_diagram(services, output_file)
    
    print(f"Architecture diagram generated at {output_file}.png")
    
    # Return the relative path for inclusion in README.md
    return "docs/images/architecture.png"

if __name__ == "__main__":
    main()