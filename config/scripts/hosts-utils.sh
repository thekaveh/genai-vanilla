#!/usr/bin/env bash
# Shared utilities for hosts file management

# Detect operating system
detect_os() {
  case "$OSTYPE" in
    darwin*)  echo "macos" ;;
    linux*)   echo "linux" ;;
    msys*|cygwin*|mingw*) echo "windows" ;;
    *)        echo "unknown" ;;
  esac
}

# Get hosts file path based on OS
get_hosts_file() {
  local os=$(detect_os)
  case "$os" in
    macos|linux) echo "/etc/hosts" ;;
    windows) echo "C:/Windows/System32/drivers/etc/hosts" ;;
    *) echo "" ;;
  esac
}

# Check if running with elevated privileges
is_elevated() {
  local os=$(detect_os)
  if [[ "$os" == "windows" ]]; then
    # Windows: check if running as administrator
    net session >/dev/null 2>&1
    return $?
  else
    # Unix: check if running as root
    [[ $EUID -eq 0 ]]
    return $?
  fi
}

# Define GenAI Stack hosts
get_genai_hosts() {
  echo "n8n.localhost api.localhost search.localhost comfyui.localhost chat.localhost"
}

# Check which hosts entries are missing  
check_missing_hosts() {
  local hosts_file=$(get_hosts_file)
  local missing=()
  
  if [[ -z "$hosts_file" || ! -f "$hosts_file" ]]; then
    echo "  • ⚠️  Cannot access hosts file: $hosts_file"
    return 1
  fi
  
  for host in $(get_genai_hosts); do
    if ! grep -q "^[[:space:]]*127\.0\.0\.1[[:space:]]\+.*$host" "$hosts_file" 2>/dev/null; then
      missing+=("$host")
    fi
  done
  
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "  • Missing hosts entries: ${missing[*]}"
    echo "    Run with --setup-hosts to add them automatically"
  else
    echo "  • ✅ All required hosts entries are present"
  fi
}

# Add hosts entries (removes old ones first to prevent duplicates)
add_hosts_entries() {
  local hosts_file=$1
  local backup_file="${hosts_file}.backup.$(date +%Y%m%d%H%M%S)"
  
  # Create backup
  cp "$hosts_file" "$backup_file" || return 1
  echo "  • Created backup: $backup_file"
  
  # Remove existing GenAI entries (cleanup)
  remove_hosts_entries_silent "$hosts_file"
  
  # Add new entries
  {
    echo ""
    echo "# GenAI Stack subdomains (added by start.sh)"
    for host in $(get_genai_hosts); do
      echo "127.0.0.1 $host"
    done
  } >> "$hosts_file"
  
  return 0
}

# Remove hosts entries (silent version for internal use)
remove_hosts_entries_silent() {
  local hosts_file=$1
  
  # Remove the comment line and all GenAI localhost entries
  if [[ "$(detect_os)" == "macos" ]]; then
    # macOS sed requires different syntax
    sed -i '' '/# GenAI Stack subdomains/d' "$hosts_file" 2>/dev/null
    for host in $(get_genai_hosts); do
      sed -i '' "/127\.0\.0\.1.*$host/d" "$hosts_file" 2>/dev/null
    done
  else
    # Linux/Windows sed
    sed -i '/# GenAI Stack subdomains/d' "$hosts_file" 2>/dev/null
    for host in $(get_genai_hosts); do
      sed -i "/127\.0\.0\.1.*$host/d" "$hosts_file" 2>/dev/null
    done
  fi
}

# Remove hosts entries (with backup)
remove_hosts_entries() {
  local hosts_file=$1
  local backup_file="${hosts_file}.backup.$(date +%Y%m%d%H%M%S)"
  
  # Create backup
  cp "$hosts_file" "$backup_file" || return 1
  echo "  • Created backup: $backup_file"
  
  # Remove entries
  remove_hosts_entries_silent "$hosts_file"
  
  return 0
}

# Setup hosts entries (main function called from start.sh)
setup_hosts_entries() {
  local hosts_file=$(get_hosts_file)
  
  if [[ -z "$hosts_file" ]]; then
    echo "  • ❌ Cannot determine hosts file location for OS: $(detect_os)"
    return 1
  fi
  
  if [[ ! -f "$hosts_file" ]]; then
    echo "  • ❌ Hosts file not found: $hosts_file"
    return 1
  fi
  
  # Check if we have elevated privileges
  if ! is_elevated; then
    echo "  • ❌ Administrative privileges required to modify hosts file"
    echo "    Please run with sudo (Linux/macOS) or as Administrator (Windows)"
    return 1
  fi
  
  echo "  • Setting up GenAI Stack hosts entries..."
  echo "  • Hosts file: $hosts_file"
  
  # Check which entries are missing first
  local missing=()
  for host in $(get_genai_hosts); do
    if ! grep -q "^[[:space:]]*127\.0\.0\.1[[:space:]]\+.*$host" "$hosts_file" 2>/dev/null; then
      missing+=("$host")
    fi
  done
  
  if [[ ${#missing[@]} -eq 0 ]]; then
    echo "  • ✅ All GenAI hosts entries already exist"
    return 0
  fi
  
  echo "  • Adding missing entries: ${missing[*]}"
  
  # Use the existing add_hosts_entries function
  if add_hosts_entries "$hosts_file"; then
    echo "  • ✅ Hosts entries added successfully"
    echo "  • You can now access services via:"
    for host in $(get_genai_hosts); do
      echo "    - http://$host"
    done
    return 0
  else
    echo "  • ❌ Failed to add hosts entries"
    return 1
  fi
}