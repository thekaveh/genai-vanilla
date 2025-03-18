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
    # Set display names for services (to make them prettier in the diagram)
    display_names = {
        "supabase-db": "Supabase\nDatabase",
        "supabase-meta": "Supabase\nMeta",
        "supabase-studio": "Supabase\nStudio",
        "graph-db": "Neo4j\nGraph Database",
        "ollama": "Ollama\nAI Models",
    }
    
    # Get the display name or use the original
    display_name = display_names.get(service_name, service_name)
    
    # Custom icon paths relative to the script
    icon_path = os.path.join(SCRIPT_DIR, "../images/icons")
    
    # Return custom icons for specific services
    if "supabase" in service_name:
        return Custom(display_name, os.path.join(icon_path, "supabase.png"))
    elif "graph-db" in service_name:
        return Custom(display_name, os.path.join(icon_path, "neo4j.png"))
    elif "ollama" in service_name:
        return Custom(display_name, os.path.join(icon_path, "ollama.png"))
    elif "postgres" in image.lower():
        return PostgreSQL(display_name)
    elif "nginx" in image.lower():
        return Nginx(display_name)
    else:
        return Rack(display_name)

def create_architecture_diagram(services, output_file):
    """Create an architecture diagram using the Diagrams library."""
    graph_attr = {
        "fontsize": "24",
        "bgcolor": "white",
        "rankdir": "TB",  # Top to Bottom layout
        "splines": "spline",  # Curved edges for nicer look
        "nodesep": "1.0",
        "ranksep": "1.5",
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
        "fontsize": "14",
        "fontname": "Arial",
        "penwidth": "2.0",
        "color": "#555555",
    }
    
    with Diagram("Vanilla GenAI Stack", filename=output_file, outformat="png", 
                 show=False, direction="TB", graph_attr=graph_attr, 
                 node_attr=node_attr, edge_attr=edge_attr):
        
        # Define the services we care about and their positions in the graph
        main_services = [
            "supabase-db",
            "supabase-meta",
            "supabase-studio",
            "graph-db",
            "ollama"
        ]
        
        service_nodes = {}
        
        # Create nodes for main services
        for service_name in main_services:
            if service_name in services:
                service_config = services[service_name]
                service_nodes[service_name] = get_service_icon(service_name, service_config['image'])
        
        # Manually create edges to control the layout better
        if "supabase-db" in service_nodes and "supabase-meta" in service_nodes:
            service_nodes["supabase-db"] >> Edge(label="provides data", color="#4285F4") >> service_nodes["supabase-meta"]
        
        if "supabase-meta" in service_nodes and "supabase-studio" in service_nodes:
            service_nodes["supabase-meta"] >> Edge(label="connects to", color="#4285F4") >> service_nodes["supabase-studio"]
        
        if "supabase-db" in service_nodes and "ollama" in service_nodes:
            service_nodes["supabase-db"] >> Edge(label="provides models", color="#4285F4") >> service_nodes["ollama"]
            
        # Add connection from graph-db to potential applications
        if "graph-db" in service_nodes and "ollama" in service_nodes:
            service_nodes["graph-db"] - Edge(style="dashed", label="available for\nconnections", color="#4285F4") - service_nodes["ollama"]

def ensure_icons_directory():
    """Ensure the icons directory exists and contains necessary icons."""
    icons_dir = os.path.join(SCRIPT_DIR, "..", "images", "icons")
    os.makedirs(icons_dir, exist_ok=True)
    
    # List of high-quality icon URLs to download if they don't exist
    icons = {
        "supabase.png": "https://seeklogo.com/images/S/supabase-logo-DCC676FFE2-seeklogo.com.png",
        "neo4j.png": "https://neo4j.com/wp-content/themes/neo4jweb/assets/images/neo4j-logo-2015.png",
        "ollama.png": "https://ollama.com/public/ollama.png"
    }
    
    # Download missing icons
    for icon_name, icon_url in icons.items():
        icon_path = os.path.join(icons_dir, icon_name)
        if not os.path.exists(icon_path) or os.path.getsize(icon_path) < 5000:  # Ensure icon is substantial
            try:
                subprocess.run(["curl", "-s", "-L", "-o", icon_path, icon_url], check=True)
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