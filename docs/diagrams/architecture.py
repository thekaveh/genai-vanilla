#!/usr/bin/env python3
"""
Architecture diagram generator for GenAI Vanilla Stack.
This script generates an architecture diagram based on the current Docker Compose configuration.
Displays a left-to-right DAG flow starting from the database services.
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.client import User
from diagrams.onprem.compute import Server
from diagrams.onprem.network import Nginx
from diagrams.onprem.ci import Jenkins
from diagrams.programming.framework import FastAPI
import os
import re
import subprocess
import yaml
import sys

# Define the output path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "images")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_services_from_docker_compose(file_path):
    """Extract services and their dependencies from a Docker Compose file."""
    with open(file_path, 'r') as file:
        docker_compose = yaml.safe_load(file)
    
    services = {}
    for service_name, service_config in docker_compose.get('services', {}).items():
        # Skip volume entries
        if service_name.endswith("-data"):
            continue
            
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
    # Set display names for services (to make them prettier in the diagram)
    display_names = {
        "supabase-db": "Supabase DB",
        "supabase-meta": "Supabase Meta",
        "supabase-auth": "Supabase Auth",
        "supabase-studio": "Supabase Studio",
        "graph-db": "Neo4j DB",
        "ollama": "Ollama LLM",
        "ollama-pull": "Model Puller",
        "open-web-ui": "OpenWebUI",
        "backend": "FastAPI Backend"
    }
    
    # Get the display name or use the original
    display_name = display_names.get(service_name, service_name)
    
    # Custom icon paths relative to the script
    icon_path = os.path.join(SCRIPT_DIR, "..", "images", "icons")
    
    # Check if icon files exist
    def icon_exists(name):
        path = os.path.join(icon_path, name)
        return os.path.exists(path) and os.path.getsize(path) > 0
    
    # Map services to icons
    icons = {
        "supabase-db": "supabase.png",
        "supabase-meta": "supabase.png",
        "supabase-auth": "supabase.png",
        "supabase-studio": "supabase.png",
        "graph-db": "neo4j.png",
        "ollama": "ollama.png",
        "ollama-pull": "ollama.png",
        "open-web-ui": "open-webui.png"
    }
    
    # If service has a custom icon and the icon file exists, use it
    if service_name in icons and icon_exists(icons[service_name]):
        return Custom(display_name, os.path.join(icon_path, icons[service_name]))
    
    # Use appropriate built-in icons for specific services
    if "backend" == service_name:
        return FastAPI(display_name)
    else:
        return Server(display_name)

def create_architecture_diagram(services, output_file):
    """Create an architecture diagram using the Diagrams library."""
    graph_attr = {
        "fontsize": "24",
        "bgcolor": "white",
        "rankdir": "LR",  # Left to Right layout for DAG flow
        "splines": "ortho",  # Orthogonal edges for cleaner look
        "nodesep": "1.0",
        "ranksep": "2.0",
        "pad": "0.5",
        "dpi": "300",
    }
    
    node_attr = {
        "fontsize": "16",
        "fontname": "Arial",
        "shape": "box",
        "style": "filled,rounded",
        "fillcolor": "#f5f5f5",
        "width": "2.0",
        "height": "1.5",
        "penwidth": "2.0",
    }
    
    edge_attr = {
        "fontsize": "12",
        "fontname": "Arial",
        "penwidth": "1.5",
        "color": "#555555",
    }
    
    with Diagram("GenAI Vanilla Stack", filename=output_file, outformat="png", 
                 show=False, direction="LR", graph_attr=graph_attr, 
                 node_attr=node_attr, edge_attr=edge_attr):
        
        # Define the services in order of the DAG flow (left to right)
        service_order = [
            "supabase-db",
            "supabase-meta",
            "supabase-auth",
            "supabase-studio",
            "graph-db",
            "ollama",
            "ollama-pull",
            "open-web-ui",
            "backend"
        ]
        
        service_nodes = {}
        
        # Create nodes for all services in the defined order
        for service_name in service_order:
            if service_name in services:
                service_config = services[service_name]
                service_nodes[service_name] = get_service_icon(service_name, service_config['image'])
        
        # Map dependencies explicitly based on actual dependencies in docker-compose
        # Add edges for all dependencies as per Docker Compose
        for service_name, node in service_nodes.items():
            for dep in services[service_name]['dependencies']:
                if dep in service_nodes:
                    service_nodes[dep] >> Edge(color="#4285F4") >> node
        
        # Add explicit connections for backend to clarify architecture
        if "backend" in service_nodes:
            if "supabase-db" in service_nodes:
                service_nodes["supabase-db"] >> Edge(label="data", color="#4285F4") >> service_nodes["backend"]
            if "graph-db" in service_nodes:
                service_nodes["graph-db"] >> Edge(label="graph data", color="#4285F4") >> service_nodes["backend"]
            if "ollama" in service_nodes:
                service_nodes["ollama"] >> Edge(label="AI models", color="#4285F4") >> service_nodes["backend"]

def ensure_icons_directory():
    """Ensure the icons directory exists and contains necessary icons."""
    icons_dir = os.path.join(SCRIPT_DIR, "..", "images", "icons")
    os.makedirs(icons_dir, exist_ok=True)
    
    # Use basic drawing if we can't download or find icons
    # Note: This function will be called when running the diagram generation, 
    # but we're only checking for the existence of the icon files
    
    # Print a message if any required icon is missing
    icons = ["supabase.png", "neo4j.png", "ollama.png", "open-webui.png"]
    for icon_name in icons:
        icon_path = os.path.join(icons_dir, icon_name)
        if not os.path.exists(icon_path):
            print(f"WARNING: Icon {icon_name} is missing. Using built-in icons as fallback.")

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