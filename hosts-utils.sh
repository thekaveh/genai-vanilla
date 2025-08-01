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
  local hosts_file=$1
  local missing=()
  
  for host in $(get_genai_hosts); do
    if ! grep -q "^[[:space:]]*127\.0\.0\.1[[:space:]]\+.*$host" "$hosts_file" 2>/dev/null; then
      missing+=("$host")
    fi
  done
  
  echo "${missing[@]}"
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