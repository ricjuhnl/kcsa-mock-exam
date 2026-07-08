#!/bin/bash

# Generate .htpasswd file for nginx basic auth
# Usage: ./generate_htpasswd.sh [username] [password]

USERNAME=${1:-kcsa_admin}
PASSWORD=${2:-$(openssl rand -base64 12)}

echo "Generating .htpasswd for user: $USERNAME"
docker run --rm --entrypoint sh nginx:alpine -c \
  "echo '${USERNAME}:$(openssl passwd -apr1 '${PASSWORD}')'" > frontend/.htpasswd

echo "Password: $PASSWORD"
echo ".htpasswd file generated successfully"
