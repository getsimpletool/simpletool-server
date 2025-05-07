#!/usr/bin/env bash
PORT="${ST_PORT:-8000}"
HOST="${ST_HOST:-0.0.0.0}"
VENV="${ST_VENV:-False}"
VENV_AUTOUPGRADE="${ST_VENV_AUTOUPGRADE:-False}"
VENV_PATH="${ST_VENV_PATH:-/app/venv}"
REQUIREMENTS_PATH="${ST_REQUIREMENTS_PATH:-/app/requirements.txt}"
PRELOAD_TOOLS="${ST_PRELOAD_TOOLS:-false}"  # Default to lazy loading

# FUNCTION to parse and install requirements from frontmatter
install_server_requirements() {
  local file=$1
  local file_content=$(cat "$1")
  # Extract the first triple-quoted block
  local first_block=$(echo "$file_content" | awk '/"""/{flag=!flag; if(flag) count++; if(count == 2) {exit}} flag' )

  # Check if the block contains requirements
  local requirements=$(echo "$first_block" | grep -i 'requirements:')

  if [ -n "$requirements" ]; then
    # Print file name
    echo "+ Installing requirements for uset tools $file:"

    # Extract the requirements list
    requirements=$(echo "$requirements" | awk -F': ' '{print $2}' | tr ',' ' ' | tr -d '\r')

    # Construct and echo the pip install command
    local pip_command="pip install $requirements"
    echo "$pip_command"
    pip install $requirements
  else
    echo "- No requirements found in frontmatter of $file."
  fi
}

# FUNCTION to install requirements on demand if requirements.txt is provided by user
install_requirements() {
  if [[ -f "$1" ]]; then
    echo "requirements.txt found at $1. Installing requirements..."
    pip install -r "$1"
  else
    echo "requirements.txt not found at $1. Skipping installation of requirements."
  fi
}


# FUNCTION to download a single file
download_file() {
  local url="$1"
  local folder_path="$2"

  # Extract filename from URL
  local filename=$(basename "${url}")
  local filepath="${folder_path}/${filename}"

  # Check if local file exists
  if [ -f "${filepath}" ]; then
    echo "File exists: ${filepath}"
    local tmp_file="/tmp/${filename}"

    # Download file to /tmp
    wget -q -O "${tmp_file}" "${url}"

    # Calculate MD5 checksums
    local existing_md5=$(md5sum "${filepath}" | awk '{print $1}')
    local new_md5=$(md5sum "${tmp_file}" | awk '{print $1}')

    echo "   - MD5 downloaded: ${new_md5}"
    echo "   - MD5 existing:   ${existing_md5}"

    # Compare checksums
    if [ "${existing_md5}" != "${new_md5}" ]; then
      echo "File has changed. Backing up..."
      local backup_suffix=$(date +"%Y%m%d%H%M%S")
      local backup_file="${filepath}_backup_${backup_suffix}"
      mv "${filepath}" "${backup_file}"
      mv "${tmp_file}" "${filepath}"
      echo "File updated: ${filepath}"
    else
      echo "File is the same. Removing tmp file."
      rm "${tmp_file}"
    fi
  else
    echo "File does not exist: ${filepath}"
    wget -q -O "${filepath}" "${url}"
    echo "File downloaded: ${filepath}"
  fi
}


# -------------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------
# -- MAIN ---
# Actiavte venv if needed
if [ "$VENV" = True ]; then
  echo "VENV is ACTIVE"
  echo "VENV_PATH: /app/venv"
  echo "VENV_AUTOUPGRADE: $VENV_AUTOUPGRADE"

  # Init venv if not installed
  if [ ! -d "/app/venv" ]; then
    echo "Creating virtual environment at /app/venv"
    python3 -m venv /app/venv
  fi

  # Activate venv
  echo "Activated virtual environment at /app/venv"
  source /app/venv/bin/activate

  # Upgrade pip if ST_VENV_AUTOUPGRADE is True and venv is active
  if [ "$ST_VENV_AUTOUPGRADE" = True ]; then
    echo "Upgrading pip..."
    pip install --upgrade pip

    echo "Checking for outdated packages."
    pip install --upgrade -r /app/requirements.txt
  else
    echo "Installing base system requirements /app/requirements.txt"
    pip install --upgrade -r /app/requirements.txt
  fi
fi

# Check if the REQUIREMENTS_PATH environment variable is set and non-empty
if [[ -n "$REQUIREMENTS_PATH" ]]; then
  # Install requirements from the specified requirements.txt file on demand
  install_requirements "$REQUIREMENTS_PATH"
else
  echo "REQUIREMENTS_PATH not specified. Skipping installation of requirements."
fi


echo "Starting simple-tool-server..."
python3 -m mcpo_simple_server
