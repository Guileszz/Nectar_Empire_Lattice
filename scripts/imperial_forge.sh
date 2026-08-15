#!/bin/bash
################################################################################
# ⚜️ imperial_forge.sh - Phase 5: Automated Satellite Repository Generation
# Spawn all Nectar Empire satellite nodes with zero-friction scaffolding
# Uses GitHub CLI (gh) for programmatic repository creation
################################################################################

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

OWNER="guitriloco"
REPOS=("Nectar_Wealth" "Nectar_Health" "Nectar_Dev" "Nectar_Pets")
PRIVATE_MODE=true
GITHUB_HOST="${GITHUB_HOST:-github.com}"

# Domain-specific configuration
declare -A DOMAIN_DESCRIPTION=(
    ["Nectar_Wealth"]="Financial distillation and void-finance grid synthesis"
    ["Nectar_Health"]="Bio-performance scaling and wellness optimization"
    ["Nectar_Dev"]="Technical sovereignty and code automation"
    ["Nectar_Pets"]="Pet market loyalty intelligence and companion synthesis"
)

declare -A DOMAIN_PORTS=(
    ["Nectar_Wealth"]="8001"
    ["Nectar_Health"]="8003"
    ["Nectar_Dev"]="8002"
    ["Nectar_Pets"]="8004"
)

# ============================================================================
# LOGGING & OUTPUT
# ============================================================================

log_header() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════════════════════╗"
    echo "║ ⚜️  $1"
    echo "╚════════════════════════════════════════════════════════════════════════════════╝"
    echo ""
}

log_info() {
    echo "   🔱 $1"
}

log_success() {
    echo "   ✅ $1"
}

log_error() {
    echo "   ❌ ERROR: $1" >&2
}

log_warn() {
    echo "   ⚠️  $1"
}

# ============================================================================
# VALIDATION & PREREQUISITES
# ============================================================================

validate_environment() {
    log_header "VALIDATING IMPERIAL FORGE ENVIRONMENT"
    
    # Check if gh is installed
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) is not installed"
        echo "   Install via: brew install gh (macOS) or https://cli.github.com"
        exit 1
    fi
    log_success "GitHub CLI (gh) installed"
    
    # Check if gh is authenticated
    if ! gh auth status &> /dev/null; then
        log_error "GitHub CLI is not authenticated"
        echo "   Run: gh auth login"
        exit 1
    fi
    log_success "GitHub CLI authenticated"
    
    # Check if git is installed
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed"
        exit 1
    fi
    log_success "Git installed"
    
    # Verify we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_warn "Not in a git repository. Continuing without local sync."
    else
        log_success "Running from git repository"
    fi
    
    log_success "All prerequisites validated"
}

# ============================================================================
# REPOSITORY CREATION & SCAFFOLDING
# ============================================================================

scaffold_repository() {
    local repo_name=$1
    local description=${DOMAIN_DESCRIPTION[$repo_name]}
    local port=${DOMAIN_PORTS[$repo_name]}
    
    log_header "FORGING SATELLITE NODE: $repo_name"
    
    # Create temporary directory for scaffolding
    local temp_dir="/tmp/nectar_${repo_name}_$$"
    mkdir -p "$temp_dir"
    cd "$temp_dir"
    
    log_info "Scaffolding directory structure..."
    
    # Create directory structure
    mkdir -p core/sync
    mkdir -p core/logic
    mkdir -p prompts/core
    mkdir -p prompts/specialized
    mkdir -p docs
    mkdir -p state
    mkdir -p logs
    
    log_success "Created core directories"
    
    # Create .gitkeep files to preserve empty directories
    touch core/sync/.gitkeep
    touch core/logic/.gitkeep
    touch prompts/core/.gitkeep
    touch prompts/specialized/.gitkeep
    touch state/.gitkeep
    touch logs/.gitkeep
    
    # Create README.md
    create_readme "$repo_name" "$description" > README.md
    log_success "Generated README.md"
    
    # Create .env.example
    create_env_example "$repo_name" "$port" > .env.example
    log_success "Generated .env.example"
    
    # Create base personality-matrix.md
    create_personality_matrix "$repo_name" > prompts/personality-matrix.md
    log_success "Generated prompts/personality-matrix.md"
    
    # Create ARCHITECTURE.md
    create_architecture "$repo_name" > docs/ARCHITECTURE.md
    log_success "Generated docs/ARCHITECTURE.md"
    
    # Create .gitignore
    create_gitignore > .gitignore
    log_success "Generated .gitignore"
    
    # Initialize git repository
    log_info "Initializing git repository..."
    git init
    git config user.name "Nectar Empire"
    git config user.email "empire@nectar.local"
    
    # Add all files
    git add -A
    git commit -m "chore: initial Imperial scaffold for $repo_name"
    log_success "Initial commit created"
    
    # Create repository on GitHub
    log_info "Creating repository on GitHub: $OWNER/$repo_name"
    
    if gh repo create "$OWNER/$repo_name" \
        --source=. \
        --remote=origin \
        --push \
        $([ "$PRIVATE_MODE" = true ] && echo "--private" || echo "--public") \
        --description "$description" 2>&1; then
        log_success "Repository created and pushed: $OWNER/$repo_name"
    else
        log_error "Failed to create repository $repo_name"
        cd /
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Clean up temporary directory
    cd /
    rm -rf "$temp_dir"
    
    log_success "Satellite node $repo_name forged successfully"
}

# ============================================================================
# FILE GENERATION FUNCTIONS
# ============================================================================

create_readme() {
    local repo_name=$1
    local description=$2
    
    cat <<EOF
# 🏛️ $repo_name (Nectar Empire Satellite Node)

Bem-vindo ao **$repo_name**, um nó satélite do império **Nectar Divino**.

## 🌌 Visão Geral
Este repositório é responsável por: **$description**

## 📂 Estrutura do Repositório
- **/core/sync:** Sincronização de dados com o nó central (Nectar_Empire_Lattice)
- **/core/logic:** Lógica de negócio específica do domínio
- **/prompts:** Matrizes de personalidade e templates de IA
- **/docs:** Documentação técnica e estratégica
- **/state:** Arquivo de estado persistente
- **/logs:** Registros de execução

## 🛰️ Conectividade do Mesh
**Nó Central:** [Nectar_Empire_Lattice](https://github.com/guitriloco/Nectar_Empire_Lattice)

Protocolo de Sincronização: **lattice_v13**

## 🚀 Quick Start

### 1. Clone o repositório
\`\`\`bash
git clone https://github.com/$OWNER/$repo_name.git
cd $repo_name
\`\`\`

### 2. Setup de ambiente
\`\`\`bash
cp .env.example .env
# Customize .env com valores de produção
\`\`\`

### 3. Sincronize com o nó central
\`\`\`bash
python3 -m core.sync.lattice_sync
\`\`\`

## 📊 Status do Nó
**Estado Atual:** VIVOS (ALIVE)
**Conectividade:** Global / Soberana
**Governança:** IA Autônoma & Agent Lead

---

*Este repositório é imutável e soberano dentro de sua esfera de operação.*

EOF
}

create_env_example() {
    local repo_name=$1
    local port=$2
    
    cat <<EOF
# Environment Configuration for $repo_name

# Deployment environment
NECTAR_ENV=production
NODE_NAME=$repo_name
API_PORT=$port

# Central mesh node configuration
NECTAR_EMPIRE_LATTICE_URL=http://localhost:8000/api/sync
MESH_SYNC_PROTOCOL=lattice_v13
MESH_SYNC_INTERVAL_MS=5000

# State management
NECTAR_STATE_DIR=./state
NECTAR_LOG_DIR=./logs
NECTAR_LOG_LEVEL=INFO

# Performance tuning
MAX_CONCURRENT_TASKS=4
DEFAULT_TIMEOUT_SECONDS=60

# Domain-specific configuration
# (Customize per domain)

EOF
}

create_personality_matrix() {
    local repo_name=$1
    
    cat <<EOF
# 🎭 Personality Matrix: $repo_name

## Core Traits
cognition: recursive_self_deepening
execution_mode: autonomous_optimization
latency_target: zero_latency
failure_handling: graceful_degradation
output_style: actionable_metric_driven

## Domain Override
node_domain: $(echo "$repo_name" | sed 's/Nectar_//' | tr '[:upper:]' '[:lower:]')

This matrix is loaded and injected into all AI prompts.

EOF
}

create_architecture() {
    local repo_name=$1
    
    cat <<EOF
# Architecture: $repo_name

## Component Overview

### Core Modules
- **core/sync/:** Lattice synchronization with central node
- **core/logic/:** Domain-specific business logic

### State Management
- Persistent state stored in \`state/empire_state.json\`
- Atomic writes to prevent corruption

### Communication
- HTTP/gRPC API exposed on configured port
- Mesh synchronization protocol: lattice_v13

## Data Flow
1. Receive sync request from Nectar_Empire_Lattice
2. Execute local domain logic
3. Persist state atomically
4. Return metrics and status to central node

## Integration Points
- **Parent Node:** Nectar_Empire_Lattice (central orchestrator)
- **Sibling Nodes:** Nectar_Wealth, Nectar_Health, Nectar_Dev, Nectar_Pets
- **Mesh Protocol:** lattice_v13

EOF
}

create_gitignore() {
    cat <<'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Environment
.env
.env.local
.env.*.local

# State & Logs
state/
logs/
*.log

# Temporary files
*.tmp
*.bak
/tmp/

EOF
}

# ============================================================================
# MAIN EXECUTION FLOW
# ============================================================================

main() {
    log_header "⚜️  NECTAR EMPIRE FORGE - SATELLITE NODE GENERATION ⚜️"
    
    # Validate environment
    validate_environment
    
    # Track success/failure
    local success_count=0
    local failed_repos=()
    
    # Scaffold each repository
    for repo in "${REPOS[@]}"; do
        if scaffold_repository "$repo"; then
            ((success_count++))
        else
            failed_repos+=("$repo")
        fi
    done
    
    # Print summary
    log_header "⚜️  FORGE EXECUTION SUMMARY ⚜️"
    echo ""
    echo "   Total Repositories: ${#REPOS[@]}"
    echo "   Successfully Forged: $success_count"
    echo "   Failed: ${#failed_repos[@]}"
    echo ""
    
    if [ ${#failed_repos[@]} -eq 0 ]; then
        log_success "ALL SATELLITE NODES SUCCESSFULLY FORGED"
        echo ""
        echo "   🛰️  Repositories created:"
        for repo in "${REPOS[@]}"; do
            echo "       - https://github.com/$OWNER/$repo"
        done
        echo ""
        log_success "TOTAL AFIRMAÇÃO. TOTAL CONQUISTA. TOTAL RESULTADO."
        return 0
    else
        log_error "Failed to forge: ${failed_repos[*]}"
        return 1
    fi
}

# ============================================================================
# EXECUTION
# ============================================================================

main "$@"
