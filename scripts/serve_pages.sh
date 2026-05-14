#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

bundle config set path 'vendor/bundle'
bundle install
bundle exec jekyll serve --source docs --livereload
